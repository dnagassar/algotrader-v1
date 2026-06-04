from __future__ import annotations

import ast
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.execution.paper_lab_state_rollup import (
    PAPER_LAB_STATE_ROLLUP_LABELS,
    PaperLabStateRollupConfig,
    build_paper_lab_state_rollup,
    write_paper_lab_state_rollup_jsonl,
)


MODULE_PATH = Path("src/algotrader/execution/paper_lab_state_rollup.py")
CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
QUANTITY = "0.033172072"
GENERATED_AT = "2026-06-04T12:38:23+00:00"
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "os",
    "requests",
    "socket",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "delete",
    "getenv",
    "liquidate",
    "load_config",
    "replace_order",
    "request",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


def test_rollup_preserves_m376_nonterminal_open_block(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m385_m376_spy_close_order_reconciliation.jsonl",
        _nonterminal_reconciliation_record(),
    )
    daily_preview_log = _write_jsonl(
        tmp_path / "m385_paper_lab_daily_preview.jsonl",
        _blocked_daily_preview_record(),
    )

    payload = build_paper_lab_state_rollup(
        _config(reconciliation_log, daily_preview_log)
    )

    assert payload["state_rollup_status"] == "blocked"
    assert payload["m376_status"] == "accepted"
    assert payload["m376_terminal_state"] == "nonterminal"
    assert payload["m376_nonterminal"] is True
    assert payload["m376_order_nonterminal"] is True
    assert payload["spy_position_qty"] == QUANTITY
    assert payload["open_order_count"] == 1
    assert payload["open_order_present"] is True
    assert payload["open_spy_order_present"] is True
    assert payload["daily_preview_status"] == "blocked"
    assert payload["cycle_decision"] == "blocked/open_order_present"
    assert "m376_order_nonterminal" in payload["blockers"]
    assert "open_order_present" in payload["blockers"]
    assert payload["next_allowed_action"] == "offline_work_or_read_only_reconciliation"
    assert "spy_submit_until_m376_terminal" in payload["forbidden_actions"]
    assert payload["next_forbidden_action"] == payload["forbidden_actions"]
    assert payload["labels"] == list(PAPER_LAB_STATE_ROLLUP_LABELS)
    _assert_safety_booleans_false(payload)


def test_rollup_writes_exactly_one_jsonl_record(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "reconciliation.jsonl",
        _nonterminal_reconciliation_record(),
    )
    daily_preview_log = _write_jsonl(
        tmp_path / "daily_preview.jsonl",
        _blocked_daily_preview_record(),
    )
    output_path = tmp_path / "runs" / "paper_lab" / "state_rollup.jsonl"
    output_path.parent.mkdir(parents=True)
    output_path.write_text('{"old":1}\n{"old":2}\n', encoding="utf-8")
    payload = build_paper_lab_state_rollup(
        _config(reconciliation_log, daily_preview_log)
    )

    result = write_paper_lab_state_rollup_jsonl(payload, output_path)
    records = _read_jsonl(output_path)

    assert result.record_count == 1
    assert result.submitted is False
    assert result.mutated is False
    assert result.broker_action_performed is False
    assert records == [payload]


def test_missing_or_malformed_inputs_fail_closed(tmp_path) -> None:  # noqa: ANN001
    missing_reconciliation = tmp_path / "missing_reconciliation.jsonl"
    malformed_daily_preview = tmp_path / "malformed_daily_preview.jsonl"
    malformed_daily_preview.write_text("{not-json}\n", encoding="utf-8")

    payload = build_paper_lab_state_rollup(
        _config(missing_reconciliation, malformed_daily_preview)
    )

    assert payload["state_rollup_status"] == "blocked"
    assert payload["m376_terminal_state"] == "unknown"
    assert "missing_or_invalid_order_reconciliation" in payload["blockers"]
    assert "missing_or_invalid_daily_preview" in payload["blockers"]
    assert payload["next_allowed_action"] == (
        "read_only_reconciliation_before_any_spy_submit"
    )
    assert "spy_submit_until_order_state_known" in payload["forbidden_actions"]
    assert "spy_submit_until_daily_preview_valid" in payload["forbidden_actions"]
    assert payload["source_artifacts"]["order_reconciliation_log"]["found"] is False
    assert payload["source_artifacts"]["daily_preview_log"]["parsed"] is False
    _assert_safety_booleans_false(payload)


def test_terminal_m376_without_open_order_does_not_invent_submit_permission(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "terminal_reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )
    daily_preview_log = _write_jsonl(
        tmp_path / "terminal_daily_preview.jsonl",
        _terminal_daily_preview_record(),
    )

    payload = build_paper_lab_state_rollup(
        _config(reconciliation_log, daily_preview_log)
    )

    assert payload["state_rollup_status"] == "review_only"
    assert payload["m376_status"] == "filled"
    assert payload["m376_terminal_state"] == "terminal"
    assert payload["m376_terminal"] is True
    assert payload["m376_terminal_state_conflict"] is False
    assert payload["m376_nonterminal"] is False
    assert payload["open_order_present"] is False
    assert payload["open_spy_order_present"] is False
    assert "m376_order_nonterminal" not in payload["blockers"]
    assert "open_order_present" not in payload["blockers"]
    assert payload["preview_order_authorized"] is False
    assert payload["submitted"] is False
    _assert_safety_booleans_false(payload)


def test_conflicting_m376_terminal_evidence_fails_closed(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "terminal_reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )
    daily_record = _terminal_daily_preview_record()
    daily_record["m376_terminal_state"] = "nonterminal"
    daily_record["m376_order_summary"]["terminal_state"] = "nonterminal"
    daily_preview_log = _write_jsonl(
        tmp_path / "conflicting_daily_preview.jsonl",
        daily_record,
    )

    payload = build_paper_lab_state_rollup(
        _config(reconciliation_log, daily_preview_log)
    )

    assert payload["state_rollup_status"] == "blocked"
    assert payload["m376_terminal_state_conflict"] is True
    assert payload["m376_terminal"] is False
    assert payload["m376_nonterminal"] is True
    assert "conflicting_local_artifact_state" in payload["blockers"]
    assert "m376_order_nonterminal" in payload["blockers"]
    assert "spy_submit_until_m376_terminal" in payload["forbidden_actions"]
    _assert_safety_booleans_false(payload)


def test_source_plural_broker_action_flag_fails_closed(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "terminal_reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )
    daily_record = _terminal_daily_preview_record()
    daily_record["broker_actions_performed"] = True
    daily_preview_log = _write_jsonl(
        tmp_path / "unsafe_daily_preview.jsonl",
        daily_record,
    )

    payload = build_paper_lab_state_rollup(
        _config(reconciliation_log, daily_preview_log)
    )

    assert payload["state_rollup_status"] == "blocked"
    assert "source_artifact_safety_flags_not_false" in payload["blockers"]
    assert payload["broker_actions_performed"] is False
    _assert_safety_booleans_false(payload)


def test_cli_dispatch_runs_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m385_reconciliation.jsonl",
        _nonterminal_reconciliation_record(),
    )
    daily_preview_log = _write_jsonl(
        tmp_path / "m385_daily_preview.jsonl",
        _blocked_daily_preview_record(),
    )
    run_log = tmp_path / "rollup.jsonl"

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("state rollup must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("state rollup must not build a broker")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)

    exit_code = cli_module.main(
        (
            "paper-lab-state-rollup",
            "--run-id",
            "unit_state_rollup",
            "--run-log",
            str(run_log),
            "--order-reconciliation-log",
            str(reconciliation_log),
            "--daily-preview-log",
            str(daily_preview_log),
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    records = _read_jsonl(run_log)

    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == records[0]
    assert records[0]["run_id"] == "unit_state_rollup"
    assert records[0]["cycle_decision"] == "blocked/open_order_present"


def test_state_rollup_command_requires_explicit_artifact_paths() -> None:
    parser = _paper_lab_state_rollup_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["run_id"].required is True
    assert options["run_log"].required is True
    assert options["order_reconciliation_log"].required is True
    assert options["daily_preview_log"].required is True
    assert options["run_id"].default is None
    assert options["run_log"].default is None
    assert options["order_reconciliation_log"].default is None
    assert options["daily_preview_log"].default is None


def test_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(FORBIDDEN_CALL_NAMES)
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert CLIENT_ORDER_ID not in source
    assert BROKER_ORDER_ID not in source
    assert QUANTITY not in source


def _config(
    reconciliation_log: Path,
    daily_preview_log: Path,
    **overrides: object,
) -> PaperLabStateRollupConfig:
    values = {
        "run_id": "unit_state_rollup",
        "symbol": "SPY",
        "order_reconciliation_log": reconciliation_log,
        "daily_preview_log": daily_preview_log,
    }
    values.update(overrides)
    return PaperLabStateRollupConfig(**values)


def _nonterminal_reconciliation_record() -> dict[str, object]:
    return {
        "run_id": "m385_m376_spy_close_order_reconciliation",
        "symbol": "SPY",
        "client_order_id": CLIENT_ORDER_ID,
        "broker_order_id": BROKER_ORDER_ID,
        "expected_side": "sell",
        "expected_qty": QUANTITY,
        "observed_status": "accepted",
        "observed_symbol": "SPY",
        "observed_side": "sell",
        "observed_qty": QUANTITY,
        "observed_filled_qty": "0",
        "observed_remaining_qty": QUANTITY,
        "exact_order_found": True,
        "exact_order_source": "open",
        "terminal_state": "nonterminal",
        "terminal_reason": "status_accepted_active",
        "reconciliation_decision": "m376_nonterminal_open",
        "next_spy_submit_blocked": True,
        "reason": "status_accepted_active",
        "spy_position_qty": QUANTITY,
        "open_order_count": 1,
        "spy_open_order_count": 1,
        "open_order_symbols": ["SPY"],
        "open_order_client_order_ids": [CLIENT_ORDER_ID],
        "open_order_broker_order_ids": [BROKER_ORDER_ID],
        "open_order_statuses": ["accepted"],
        "open_order_sides": ["sell"],
        "open_order_quantities": [QUANTITY],
        "open_order_filled_quantities": ["0"],
        "non_spy_positions": [],
        "blockers": ["m376_order_nonterminal", "open_order_present"],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _blocked_daily_preview_record() -> dict[str, object]:
    return {
        "run_id": "m385_paper_lab_daily_preview",
        "record_type": "paper_lab_daily_preview",
        "command": "paper-lab-daily-preview",
        "generated_at": GENERATED_AT,
        "as_of": GENERATED_AT,
        "symbol": "SPY",
        "daily_preview_status": "blocked",
        "cycle_decision": "blocked/open_order_present",
        "cycle_decision_reason": "open_order_present",
        "cycle_next_allowed_action": "offline_work_or_read_only_reconciliation",
        "m376_client_order_id": CLIENT_ORDER_ID,
        "m376_broker_order_id": BROKER_ORDER_ID,
        "m376_terminal_state": "nonterminal",
        "m376_terminal_reason": "status_accepted_active",
        "m376_order_summary": {
            "run_id": "m385_m376_spy_close_order_reconciliation",
            "symbol": "SPY",
            "client_order_id": CLIENT_ORDER_ID,
            "broker_order_id": BROKER_ORDER_ID,
            "observed_status": "accepted",
            "observed_side": "sell",
            "observed_qty": QUANTITY,
            "observed_filled_qty": "0",
            "terminal_state": "nonterminal",
            "terminal_reason": "status_accepted_active",
            "reconciliation_decision": "m376_nonterminal_open",
            "spy_position_qty": QUANTITY,
            "open_order_count": 1,
            "blockers": ["m376_order_nonterminal", "open_order_present"],
        },
        "open_order_present": True,
        "open_spy_order_present": True,
        "spy_position_qty": QUANTITY,
        "blockers": ["m376_order_nonterminal", "open_order_present"],
        "next_allowed_action": "offline_work_or_read_only_reconciliation",
        "next_forbidden_action": [
            "broker_mutation_from_daily_preview",
            "live_trading",
            "submit_cancel_replace_close_liquidate_from_daily_preview",
            "spy_submit_until_m376_terminal",
        ],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _terminal_reconciliation_record() -> dict[str, object]:
    record = _nonterminal_reconciliation_record()
    record.update(
        {
            "observed_status": "filled",
            "observed_filled_qty": QUANTITY,
            "observed_remaining_qty": "0",
            "exact_order_source": "all",
            "terminal_state": "terminal",
            "terminal_reason": "status_filled",
            "reconciliation_decision": "m376_terminal_filled",
            "next_spy_submit_blocked": False,
            "reason": "status_filled",
            "spy_position_qty": "",
            "open_order_count": 0,
            "spy_open_order_count": 0,
            "open_order_symbols": [],
            "open_order_client_order_ids": [],
            "open_order_broker_order_ids": [],
            "open_order_statuses": [],
            "open_order_sides": [],
            "open_order_quantities": [],
            "open_order_filled_quantities": [],
            "blockers": [],
        }
    )
    return record


def _terminal_daily_preview_record() -> dict[str, object]:
    record = _blocked_daily_preview_record()
    record.update(
        {
            "daily_preview_status": "review_only",
            "cycle_decision": "flat/no_submit_authorized",
            "cycle_decision_reason": "review_only",
            "cycle_next_allowed_action": "offline_research_or_operator_review_only",
            "m376_terminal_state": "terminal",
            "m376_terminal_reason": "status_filled",
            "open_order_present": False,
            "open_spy_order_present": False,
            "spy_position_qty": "",
            "blockers": [],
            "next_allowed_action": "offline_research_or_operator_review_only",
            "next_forbidden_action": [
                "broker_mutation_from_daily_preview",
                "live_trading",
                "submit_cancel_replace_close_liquidate_from_daily_preview",
            ],
        }
    )
    record["m376_order_summary"] = {
        "run_id": "m385_m376_spy_close_order_reconciliation",
        "symbol": "SPY",
        "client_order_id": CLIENT_ORDER_ID,
        "broker_order_id": BROKER_ORDER_ID,
        "observed_status": "filled",
        "observed_side": "sell",
        "observed_qty": QUANTITY,
        "observed_filled_qty": QUANTITY,
        "terminal_state": "terminal",
        "terminal_reason": "status_filled",
        "reconciliation_decision": "m376_terminal_filled",
        "spy_position_qty": "",
        "open_order_count": 0,
        "blockers": [],
    }
    return record


def _write_jsonl(path: Path, *records: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_safety_booleans_false(payload: dict[str, object]) -> None:
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_actions_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["preview_order_authorized"] is False


def _paper_lab_state_rollup_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "paper-lab-state-rollup" in choices:
            return choices["paper-lab-state-rollup"]
    raise AssertionError("paper-lab-state-rollup parser not found")


def _import_references() -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefix = "." * node.level
            imports.add(f"{prefix}{node.module}")
    return imports


def _call_names() -> set[str]:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    return {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _matches_forbidden_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    cleaned = module.lstrip(".")
    return any(
        cleaned == prefix or cleaned.startswith(f"{prefix}.")
        for prefix in prefixes
    )
