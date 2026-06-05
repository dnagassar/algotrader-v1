from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import algotrader.cli as cli_module
from algotrader.execution.etf_sma_cycle_operator_brief import (
    ETF_SMA_CYCLE_OPERATOR_BRIEF_LABELS,
    EtfSmaCycleOperatorBriefConfig,
    build_etf_sma_cycle_operator_brief,
    render_etf_sma_cycle_operator_brief_json,
    write_etf_sma_cycle_operator_brief_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
MODULE_PATH = Path("src/algotrader/execution/etf_sma_cycle_operator_brief.py")
GENERATED_AT = "2026-06-05T00:00:00+00:00"
M394_RUN_ID = "m394_etf_sma_cycle_unified_offline_preview"
QUANTITY = "0.033172072"
SCRUBBED_ENV_VARS = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_PAPER_BASE_URL",
)
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
    "socket",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


def test_etf_sma_cycle_brief_help_and_parser_registration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "algotrader.cli",
            "etf-sma-cycle-brief",
            "--help",
        ],
        cwd=PROJECT_ROOT,
        env=_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "etf-sma-cycle-brief" in result.stdout
    assert "--run-id" in result.stdout
    assert "--run-log" in result.stdout
    assert "--cycle-log" in result.stdout
    assert "--generated-at" in result.stdout

    parser = _etf_sma_cycle_brief_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }
    assert options["run_id"].required is True
    assert options["run_log"].required is True
    assert options["cycle_log"].required is True
    assert options["generated_at"].required is True


def test_valid_m394_cycle_artifact_writes_exactly_one_m395_brief(
    tmp_path,
) -> None:  # noqa: ANN001
    cycle_log = _write_jsonl(tmp_path / "m394_cycle.jsonl", _m394_cycle_record())
    run_log = tmp_path / "runs" / "paper_lab" / "m395_brief.jsonl"
    run_log.parent.mkdir(parents=True)
    run_log.write_text('{"old":1}\n{"old":2}\n', encoding="utf-8")

    payload = build_etf_sma_cycle_operator_brief(_config(cycle_log))
    result = write_etf_sma_cycle_operator_brief_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]
    assert payload["record_type"] == "etf_sma_cycle_operator_brief"
    assert payload["command"] == "etf-sma-cycle-brief"
    assert payload["run_id"] == "unit_m395_brief"
    assert payload["generated_at"] == GENERATED_AT
    assert payload["source_cycle_log"] == str(cycle_log)
    assert payload["source_artifacts"]["cycle_log"]["path"] == str(cycle_log)
    assert payload["cycle_record_found"] is True
    assert payload["cycle_record_parsed"] is True
    assert payload["cycle_record_type"] == "etf_sma_cycle_unified_preview"
    assert payload["cycle_run_id"] == M394_RUN_ID
    assert payload["labels"] == list(ETF_SMA_CYCLE_OPERATOR_BRIEF_LABELS)
    _assert_m394_state_preserved(payload)
    _assert_safety_booleans_false(payload)


def test_cli_brief_dispatch_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("operator brief must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("operator brief must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("operator brief must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    cycle_log = _write_jsonl(tmp_path / "m394_cycle.jsonl", _m394_cycle_record())
    run_log = tmp_path / "m395_brief.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-cycle-brief",
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m395_brief",
            "--run-log",
            str(run_log),
            "--cycle-log",
            str(cycle_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    records = _read_jsonl(run_log)
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert records == [payload]
    _assert_m394_state_preserved(payload)
    _assert_safety_booleans_false(payload)


def test_missing_cycle_artifact_fails_closed(tmp_path) -> None:  # noqa: ANN001
    payload = build_etf_sma_cycle_operator_brief(
        _config(tmp_path / "missing_m394_cycle.jsonl")
    )

    assert payload["operator_brief_status"] == "blocked"
    assert payload["cycle_record_found"] is False
    assert payload["cycle_record_parsed"] is False
    assert payload["source_cycle_artifact"]["error"] == "path_not_found"
    assert "missing_or_invalid_cycle_artifact" in payload["blockers"]
    assert payload["recommended_next_action"] == (
        "rebuild_or_validate_cycle_artifact_before_operator_review"
    )
    assert "submit" not in payload["recommended_next_action"]
    _assert_safety_booleans_false(payload)


def test_malformed_cycle_artifact_fails_closed(tmp_path) -> None:  # noqa: ANN001
    malformed_log = tmp_path / "malformed_m394_cycle.jsonl"
    malformed_log.write_text("{not-json}\n", encoding="utf-8")

    payload = build_etf_sma_cycle_operator_brief(_config(malformed_log))

    assert payload["operator_brief_status"] == "blocked"
    assert payload["cycle_record_found"] is True
    assert payload["cycle_record_parsed"] is False
    assert payload["source_cycle_artifact"]["error"] == "invalid_jsonl_line_1"
    assert "missing_or_invalid_cycle_artifact" in payload["blockers"]
    assert "submit" not in payload["recommended_next_action"]
    _assert_safety_booleans_false(payload)


def test_nonterminal_open_order_cycle_artifact_blocks_and_never_recommends_submit(
    tmp_path,
) -> None:  # noqa: ANN001
    cycle_log = _write_jsonl(
        tmp_path / "nonterminal_cycle.jsonl",
        _nonterminal_open_order_cycle_record(),
    )

    payload = build_etf_sma_cycle_operator_brief(_config(cycle_log))

    assert payload["operator_brief_status"] == "blocked"
    assert payload["m376_terminal"] is False
    assert payload["m376_status"] == "accepted"
    assert payload["m376_terminal_state"] == "nonterminal"
    assert payload["open_order_count"] == 1
    assert payload["open_order_present"] is True
    assert payload["open_spy_order_present"] is True
    assert payload["spy_position_qty"] == QUANTITY
    assert "m376_order_nonterminal" in payload["blockers"]
    assert "open_order_present" in payload["blockers"]
    assert payload["recommended_next_action"] == (
        "offline_work_or_read_only_reconciliation"
    )
    assert "submit" not in payload["recommended_next_action"]
    assert payload["submitted"] is False
    _assert_safety_booleans_false(payload)


def test_same_input_and_generated_at_produce_deterministic_output(
    tmp_path,
) -> None:  # noqa: ANN001
    cycle_log = _write_jsonl(tmp_path / "m394_cycle.jsonl", _m394_cycle_record())

    first = build_etf_sma_cycle_operator_brief(_config(cycle_log))
    second = build_etf_sma_cycle_operator_brief(_config(cycle_log))

    assert first == second
    assert render_etf_sma_cycle_operator_brief_json(first) == (
        render_etf_sma_cycle_operator_brief_json(second)
    )


def test_operator_brief_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(
    cycle_log: Path,
    **overrides: object,
) -> EtfSmaCycleOperatorBriefConfig:
    values = {
        "run_id": "unit_m395_brief",
        "symbol": "SPY",
        "generated_at": GENERATED_AT,
        "cycle_log": cycle_log,
    }
    values.update(overrides)
    return EtfSmaCycleOperatorBriefConfig(**values)


def _m394_cycle_record() -> dict[str, object]:
    return {
        "record_type": "etf_sma_cycle_unified_preview",
        "command": "etf-sma-cycle",
        "run_id": M394_RUN_ID,
        "generated_at": GENERATED_AT,
        "as_of": GENERATED_AT,
        "symbol": "SPY",
        "labels": [
            "paper_lab_only",
            "signal_evaluation_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "cycle_decision": "insufficient_history",
        "cycle_decision_reason": "sma_insufficient_history",
        "cycle_next_allowed_action": "offline_research_or_operator_review_only",
        "next_allowed_action": "offline_research_or_operator_review_only",
        "blockers": [],
        "m376_terminal": True,
        "m376_status": "filled",
        "m376_observed_status": "filled",
        "m376_terminal_state": "terminal",
        "m376_terminal_reason": "status_filled",
        "m376_terminal_state_conflict": False,
        "m376_nonterminal": False,
        "m376_order_nonterminal": False,
        "open_order_count": 0,
        "open_order_present": False,
        "open_spy_order_present": False,
        "spy_position_qty": "",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "not_live_authorized": True,
        "forbidden_actions": [
            "broker_mutation_from_etf_sma_cycle_unified_preview",
            "live_trading",
            "submit_cancel_replace_close_liquidate_from_etf_sma_cycle",
        ],
        "next_forbidden_action": [
            "broker_mutation_from_etf_sma_cycle_unified_preview",
            "live_trading",
            "submit_cancel_replace_close_liquidate_from_etf_sma_cycle",
        ],
    }


def _nonterminal_open_order_cycle_record() -> dict[str, object]:
    record = _m394_cycle_record()
    record.update(
        {
            "cycle_decision": "blocked/open_order_present",
            "cycle_decision_reason": "open_order_present",
            "cycle_next_allowed_action": (
                "offline_work_or_read_only_reconciliation"
            ),
            "next_allowed_action": "offline_work_or_read_only_reconciliation",
            "blockers": ["m376_order_nonterminal", "open_order_present"],
            "m376_terminal": False,
            "m376_status": "accepted",
            "m376_observed_status": "accepted",
            "m376_terminal_state": "nonterminal",
            "m376_terminal_reason": "status_accepted_active",
            "m376_nonterminal": True,
            "m376_order_nonterminal": True,
            "open_order_count": 1,
            "open_order_present": True,
            "open_spy_order_present": True,
            "spy_position_qty": QUANTITY,
        }
    )
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


def _assert_m394_state_preserved(payload: dict[str, object]) -> None:
    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["cycle_decision_reason"] == "sma_insufficient_history"
    assert payload["cycle_next_allowed_action"] == (
        "offline_research_or_operator_review_only"
    )
    assert payload["recommended_next_action"] == (
        "offline_research_or_operator_review_only"
    )
    assert payload["m376_terminal"] is True
    assert payload["m376_status"] == "filled"
    assert payload["m376_terminal_state"] == "terminal"
    assert payload["open_order_count"] == 0
    assert payload["open_order_present"] is False
    assert payload["open_spy_order_present"] is False
    assert payload["spy_position_qty"] == ""
    assert payload["blockers"] == []


def _assert_safety_booleans_false(payload: dict[str, object]) -> None:
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_actions_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["not_live_authorized"] is True


def _etf_sma_cycle_brief_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "etf-sma-cycle-brief" in choices:
            return choices["etf-sma-cycle-brief"]
    raise AssertionError("etf-sma-cycle-brief parser not found")


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in SCRUBBED_ENV_VARS:
        env.pop(name, None)
    env["PYTHONPATH"] = str(SRC_ROOT)
    return env


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
