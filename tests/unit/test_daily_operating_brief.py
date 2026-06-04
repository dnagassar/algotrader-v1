from __future__ import annotations

import ast
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.research.daily_operating_brief import (
    DAILY_OPERATING_BRIEF_LABELS,
    DailyOperatingBriefConfig,
    build_daily_operating_brief,
    write_daily_operating_brief_jsonl,
)


MODULE_PATH = Path("src/algotrader/research/daily_operating_brief.py")
FIXED_GENERATED_AT = "2026-06-04T13:30:00+00:00"
CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
QUANTITY = "0.033172072"
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "liquidate",
    "replace_order",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_m379_style_reconciliation_blocks_spy_submit(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m379_reconciliation.jsonl",
        _m379_nonterminal_reconciliation_record(),
    )

    payload = build_daily_operating_brief(
        _config(order_reconciliation_log=reconciliation_log)
    )

    assert payload["source_artifacts"]["order_reconciliation_log"]["parsed"] is True
    assert payload["m376_order_summary"]["state"] == "nonterminal_open"
    assert payload["m376_order_summary"]["client_order_id"] == CLIENT_ORDER_ID
    assert payload["m376_order_summary"]["broker_order_id"] == BROKER_ORDER_ID
    assert payload["m376_order_summary"]["observed_status"] == "accepted"
    assert payload["m376_order_summary"]["observed_qty"] == QUANTITY
    assert payload["m376_order_summary"]["observed_filled_qty"] == "0"
    assert payload["paper_state_summary"]["spy_position_qty"] == QUANTITY
    assert payload["paper_state_summary"]["open_order_count"] == 1
    assert payload["paper_state_summary"]["next_spy_submit_blocked"] is True
    assert "m376_order_nonterminal" in payload["blockers"]
    assert "open_order_present" in payload["blockers"]
    assert payload["next_allowed_action"] == "offline_work_or_read_only_reconciliation"
    assert "spy_submit_until_m376_terminal" in payload["next_forbidden_action"]
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["live_authorized"] is False


def test_missing_optional_cycle_and_backtest_logs_still_write_valid_brief(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m379_reconciliation.jsonl",
        _m379_nonterminal_reconciliation_record(),
    )
    output_path = tmp_path / "runs" / "paper_lab" / "daily.jsonl"

    payload = build_daily_operating_brief(
        _config(order_reconciliation_log=reconciliation_log)
    )
    result = write_daily_operating_brief_jsonl(payload, output_path)
    records = _read_jsonl(output_path)

    assert result.record_count == 1
    assert records == [payload]
    assert "cycle_preview_summary" not in payload
    assert "backtest_summary" not in payload
    assert payload["source_artifacts"]["cycle_preview_log"] == {
        "path": None,
        "supplied": False,
        "found": False,
        "parsed": False,
        "record_count": 0,
        "latest_run_id": "",
        "latest_record_type": "",
        "error": "not_supplied",
    }
    assert payload["source_artifacts"]["backtest_log"]["supplied"] is False


def test_missing_reconciliation_marks_order_state_unknown_and_never_authorizes_submit() -> None:
    payload = build_daily_operating_brief(_config())

    assert payload["m376_order_summary"]["state"] == "unknown"
    assert payload["paper_state_summary"]["order_state"] == "unknown"
    assert "order_state_unknown" in payload["blockers"]
    assert (
        payload["next_allowed_action"]
        == "read_only_reconciliation_before_any_spy_submit"
    )
    assert "spy_submit_until_order_state_known" in payload["next_forbidden_action"]
    assert payload["paper_state_summary"]["next_spy_submit_blocked"] is True
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["live_authorized"] is False


def test_labels_and_safety_booleans_are_fixed_false() -> None:
    payload = build_daily_operating_brief(_config())

    assert payload["labels"] == list(DAILY_OPERATING_BRIEF_LABELS)
    assert "paper_lab_only" in payload["labels"]
    assert "not_live_authorized" in payload["labels"]
    assert "profit_claim=none" in payload["labels"]
    assert payload["profit_claim"] == "none"
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["live_authorized"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False


def test_cycle_preview_open_order_blocker_is_preserved(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "terminal_reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )
    cycle_preview_log = _write_jsonl(
        tmp_path / "cycle_preview.jsonl",
        {
            "run_id": "unit_cycle_preview",
            "record_type": "etf_sma_cycle_preview",
            "symbol": "SPY",
            "decision": "blocked",
            "decision_reason": "open_order_present",
            "sma_status": "evaluated",
            "sma_posture": "bullish_risk_on",
            "spy_position_quantity": QUANTITY,
            "open_order_count": 1,
            "open_order_symbols": ["SPY"],
            "blockers": ["open_order_present"],
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
        },
    )

    payload = build_daily_operating_brief(
        _config(
            order_reconciliation_log=reconciliation_log,
            cycle_preview_log=cycle_preview_log,
        )
    )

    assert payload["m376_order_summary"]["state"] == "terminal"
    assert payload["cycle_preview_summary"]["blockers"] == ["open_order_present"]
    assert "open_order_present" in payload["blockers"]
    assert payload["paper_state_summary"]["next_spy_submit_blocked"] is True
    assert payload["next_allowed_action"] == "offline_work_or_read_only_reconciliation"


def test_backtest_summary_is_research_evidence_only(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m379_reconciliation.jsonl",
        _m379_nonterminal_reconciliation_record(),
    )
    backtest_log = _write_jsonl(
        tmp_path / "backtest.jsonl",
        {
            "run_id": "unit_backtest",
            "record_type": "etf_sma_backtest_artifact",
            "symbol": "SPY",
            "status": "completed",
            "blocked": False,
            "block_reason": "",
            "bars_input_available": True,
            "bar_count": 201,
            "fast_window": 50,
            "slow_window": 200,
            "posture_history": [{"posture": "risk_on"}],
            "stats": {
                "start_date": "2026-01-01",
                "end_date": "2026-07-20",
                "total_return": "0.10",
                "max_drawdown": "0.02",
                "trade_count": 1,
                "final_position_state": "long",
                "commission_model": "zero",
                "slippage_model": "zero",
            },
            "profit_claim": "none",
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "live_authorized": False,
        },
    )

    payload = build_daily_operating_brief(
        _config(order_reconciliation_log=reconciliation_log, backtest_log=backtest_log)
    )

    assert payload["backtest_summary"]["research_evidence_only"] is True
    assert payload["backtest_summary"]["submit_authorization"] is False
    assert payload["backtest_summary"]["profit_claim"] == "none"
    assert payload["backtest_summary"]["latest_posture"] == "risk_on"
    assert "submit_based_on_backtest_stats" in payload["next_forbidden_action"]


def test_cli_writes_brief_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m379_reconciliation.jsonl",
        _m379_nonterminal_reconciliation_record(),
    )
    run_log = tmp_path / "daily.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("daily brief must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    exit_code = cli_module.main(
        [
            "daily-operating-brief",
            "--run-id",
            "unit_daily_operating_brief",
            "--run-log",
            str(run_log),
            "--order-reconciliation-log",
            str(reconciliation_log),
            "--generated-at",
            FIXED_GENERATED_AT,
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == _read_jsonl(run_log)[0]
    assert _read_jsonl(run_log)[0]["run_id"] == "unit_daily_operating_brief"


def test_daily_operating_brief_command_has_no_stale_run_log_defaults() -> None:
    parser = _daily_operating_brief_parser()
    defaults = {
        action.dest: action.default
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert defaults["run_id"] is None
    assert defaults["run_log"] is None
    assert defaults["order_reconciliation_log"] is None
    assert defaults["cycle_preview_log"] is None
    assert defaults["backtest_log"] is None
    for dest in (
        "run_log",
        "order_reconciliation_log",
        "cycle_preview_log",
        "backtest_log",
    ):
        assert "m37" not in str(defaults[dest]).lower()
        assert "runs/paper_lab/" not in str(defaults[dest]).lower()


def test_daily_operating_brief_module_imports_no_broker_sdk_network_or_runtime_deps() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(**overrides: object) -> DailyOperatingBriefConfig:
    values = {
        "run_id": "unit_daily_operating_brief",
        "symbol": "SPY",
        "generated_at": FIXED_GENERATED_AT,
    }
    values.update(overrides)
    return DailyOperatingBriefConfig(**values)


def _m379_nonterminal_reconciliation_record() -> dict[str, object]:
    return {
        "run_id": "m379_m376_spy_close_order_reconciliation",
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
        "open_order_symbols": ["SPY"],
        "open_order_client_order_ids": [CLIENT_ORDER_ID],
        "open_order_broker_order_ids": [BROKER_ORDER_ID],
        "open_order_statuses": ["accepted"],
        "open_order_sides": ["sell"],
        "open_order_quantities": [QUANTITY],
        "open_order_filled_quantities": ["0"],
        "blockers": ["m376_order_nonterminal", "open_order_present"],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }


def _terminal_reconciliation_record() -> dict[str, object]:
    record = _m379_nonterminal_reconciliation_record()
    record.update(
        {
            "observed_status": "filled",
            "observed_filled_qty": QUANTITY,
            "observed_remaining_qty": "0E-9",
            "exact_order_source": "all",
            "terminal_state": "terminal",
            "terminal_reason": "status_filled",
            "reconciliation_decision": "m376_terminal_filled",
            "next_spy_submit_blocked": False,
            "reason": "status_filled",
            "open_order_count": 0,
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


def _daily_operating_brief_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "daily-operating-brief" in choices:
            return choices["daily-operating-brief"]
    raise AssertionError("daily-operating-brief parser not found")


def _import_references() -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
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
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in prefixes
    )
