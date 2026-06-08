from __future__ import annotations

import ast
import json
import socket
from datetime import date, timedelta
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_preview import (
    ETF_SMA_DAILY_PREVIEW_LABELS,
    EtfSmaDailyPreviewConfig,
    build_etf_sma_daily_preview,
    write_etf_sma_daily_preview_jsonl,
)


MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_preview.py")
FIXED_GENERATED_AT = "2026-06-04T14:00:00+00:00"
BAR_START_DATE = date(2025, 1, 1)
CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
QUANTITY = "0.033172072"
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


def test_daily_preview_preserves_m376_nonterminal_open_blocker(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m383_m376_spy_close_order_reconciliation.jsonl",
        _m383_nonterminal_reconciliation_record(),
    )

    payload = build_etf_sma_daily_preview(_config(reconciliation_log))

    assert payload["daily_preview_status"] == "blocked"
    assert payload["cycle_decision"] == "blocked/open_order_present"
    assert "m376_order_nonterminal" in payload["blockers"]
    assert "open_order_present" in payload["blockers"]
    assert payload["cycle_blockers"].count("open_order_present") == 1
    assert payload["m376_client_order_id"] == CLIENT_ORDER_ID
    assert payload["m376_broker_order_id"] == BROKER_ORDER_ID
    assert payload["m376_terminal_state"] == "nonterminal"
    assert payload["m376_terminal_reason"] == "status_accepted_active"
    assert payload["open_order_present"] is True
    assert payload["open_spy_order_present"] is True
    assert payload["non_spy_position_present"] is False
    assert payload["spy_position_qty"] == QUANTITY
    assert payload["next_allowed_action"] == "offline_work_or_read_only_reconciliation"
    assert "spy_submit_until_m376_terminal" in payload["next_forbidden_action"]
    assert payload["labels"] == list(ETF_SMA_DAILY_PREVIEW_LABELS)
    _assert_never_mutates(payload)


def test_daily_preview_writes_exactly_one_jsonl_record(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "reconciliation.jsonl",
        _m383_nonterminal_reconciliation_record(),
    )
    run_log = tmp_path / "runs" / "paper_lab" / "daily_preview.jsonl"
    run_log.parent.mkdir(parents=True)
    run_log.write_text('{"old":1}\n{"old":2}\n', encoding="utf-8")
    payload = build_etf_sma_daily_preview(_config(reconciliation_log))

    result = write_etf_sma_daily_preview_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]


def test_safety_booleans_are_always_false(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "reconciliation.jsonl",
        _m383_nonterminal_reconciliation_record(),
    )

    payload = build_etf_sma_daily_preview(_config(reconciliation_log))

    _assert_never_mutates(payload)


def test_missing_or_malformed_reconciliation_fails_closed(tmp_path) -> None:  # noqa: ANN001
    missing_payload = build_etf_sma_daily_preview(
        _config(tmp_path / "missing_reconciliation.jsonl")
    )
    malformed_log = tmp_path / "malformed_reconciliation.jsonl"
    malformed_log.write_text("{not-json}\n", encoding="utf-8")
    malformed_payload = build_etf_sma_daily_preview(_config(malformed_log))

    for payload in (missing_payload, malformed_payload):
        assert payload["daily_preview_status"] == "blocked"
        assert "missing_or_invalid_order_reconciliation" in payload["blockers"]
        assert "missing_or_invalid_order_reconciliation" in payload["cycle_blockers"]
        assert payload["submitted"] is False
        assert payload["mutated"] is False
        assert payload["broker_action_performed"] is False
        assert payload["next_allowed_action"] == (
            "read_only_reconciliation_before_any_spy_submit"
        )


def test_non_spy_position_evidence_fails_closed(tmp_path) -> None:  # noqa: ANN001
    record = _terminal_reconciliation_record()
    record["non_spy_positions"] = ["MSFT"]
    reconciliation_log = _write_jsonl(tmp_path / "reconciliation.jsonl", record)

    payload = build_etf_sma_daily_preview(
        _config(reconciliation_log, market_data_csv=tmp_path / "missing_bars.csv")
    )

    assert payload["daily_preview_status"] == "blocked"
    assert payload["non_spy_position_present"] is True
    assert "unexpected_non_spy_position" in payload["blockers"]
    assert payload["preview_order_authorized"] is False
    assert "non_spy_action" in payload["next_forbidden_action"]
    _assert_never_mutates(payload)


def test_terminal_m376_no_spy_open_order_removes_open_order_blocker(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )

    payload = build_etf_sma_daily_preview(
        _config(reconciliation_log, market_data_csv=tmp_path / "missing_bars.csv")
    )

    assert payload["m376_terminal_state"] == "terminal"
    assert payload["open_order_present"] is False
    assert payload["open_spy_order_present"] is False
    assert "m376_order_nonterminal" not in payload["blockers"]
    assert "open_order_present" not in payload["blockers"]
    assert "m376_order_nonterminal" not in payload["cycle_blockers"]
    assert "open_order_present" not in payload["cycle_blockers"]
    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["preview_order_authorized"] is False
    _assert_never_mutates(payload)


def test_daily_preview_with_less_than_200_usable_as_of_bars_is_insufficient_history(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "terminal_position_reconciliation.jsonl",
        _terminal_position_reconciliation_record(),
    )
    bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_daily_bars.csv",
        *(199 * ("10",) + ("1000",)),
    )

    payload = build_etf_sma_daily_preview(
        _config(
            reconciliation_log,
            generated_at=_generated_at_for_bar_index(198),
            daily_bars_csv=bars_csv,
        )
    )

    assert payload["market_data_basis"] == "adjusted_close"
    assert payload["bars_input_available"] is True
    assert payload["total_spy_bar_count"] == 200
    assert payload["usable_spy_bar_count"] == 199
    assert payload["ignored_future_spy_bar_count"] == 1
    assert payload["sma_status"] == "insufficient_history"
    assert payload["sma_posture"] == "insufficient_history"
    assert payload["sma50"] == "10"
    assert payload["sma200"] == ""
    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["cycle_decision_reason"] == "sma_insufficient_history"
    assert payload["preview_order"] is None
    _assert_never_mutates(payload)


def test_daily_preview_with_200_usable_bars_computes_sma_without_lookahead(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "terminal_reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )
    bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_daily_bars.csv",
        *(150 * ("10",) + 50 * ("20",) + ("1000",)),
    )

    payload = build_etf_sma_daily_preview(
        _config(
            reconciliation_log,
            generated_at=_generated_at_for_bar_index(199),
            daily_bars_csv=bars_csv,
        )
    )

    assert payload["total_spy_bar_count"] == 201
    assert payload["usable_spy_bar_count"] == 200
    assert payload["ignored_future_spy_bar_count"] == 1
    assert payload["latest_close"] == "20"
    assert payload["sma50"] == "20"
    assert payload["sma200"] == "12.5"
    assert payload["sma_status"] == "evaluated"
    assert payload["sma_posture"] == "risk_on"
    assert payload["cycle_decision"] == "buy_preview"
    assert payload["cycle_decision_reason"] == "risk_on_no_position"
    assert payload["preview_order"]["side"] == "buy"
    assert payload["preview_order"]["preview_only"] is True
    _assert_never_mutates(payload)


def test_daily_preview_risk_on_spy_position_produces_hold_noop(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "terminal_position_reconciliation.jsonl",
        _terminal_position_reconciliation_record(),
    )
    bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_daily_bars.csv",
        *(150 * ("10",) + 50 * ("20",)),
    )

    payload = build_etf_sma_daily_preview(
        _config(
            reconciliation_log,
            generated_at=_generated_at_for_bar_index(199),
            daily_bars_csv=bars_csv,
        )
    )

    assert payload["sma_posture"] == "risk_on"
    assert payload["cycle_decision"] == "hold/noop"
    assert payload["cycle_decision_reason"] == "risk_on_existing_position"
    assert payload["spy_position_qty"] == QUANTITY
    assert payload["preview_order"] is None
    _assert_never_mutates(payload)


def test_daily_preview_risk_off_spy_position_produces_sell_preview_only(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "terminal_position_reconciliation.jsonl",
        _terminal_position_reconciliation_record(),
    )
    bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_daily_bars.csv",
        *(200 * ("10",)),
    )

    payload = build_etf_sma_daily_preview(
        _config(
            reconciliation_log,
            generated_at=_generated_at_for_bar_index(199),
            daily_bars_csv=bars_csv,
        )
    )

    assert payload["sma50"] == "10"
    assert payload["sma200"] == "10"
    assert payload["sma_posture"] == "risk_off"
    assert payload["cycle_decision"] == "sell_preview"
    assert payload["cycle_decision_reason"] == "risk_off_existing_position"
    assert payload["preview_order"] == {
        "asset_class": "equity",
        "symbol": "SPY",
        "side": "sell",
        "order_type": "market",
        "time_in_force": "day",
        "quantity": QUANTITY,
        "preview_only": True,
    }
    assert payload["preview_order_authorized"] is False
    _assert_never_mutates(payload)


def test_cli_dispatch_runs_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m383_reconciliation.jsonl",
        _m383_nonterminal_reconciliation_record(),
    )
    bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_daily_bars.csv",
        *(150 * ("10",) + 50 * ("20",)),
    )
    run_log = tmp_path / "daily_preview.jsonl"

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("daily preview must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("daily preview must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("daily preview must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    exit_code = cli_module.main(
        (
            "paper-lab-daily-preview",
            "--symbol",
            "SPY",
            "--run-id",
            "unit_daily_preview",
            "--run-log",
            str(run_log),
            "--order-reconciliation-log",
            str(reconciliation_log),
            "--daily-bars-csv",
            str(bars_csv),
            "--generated-at",
            _generated_at_for_bar_index(199),
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    records = _read_jsonl(run_log)

    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == records[0]
    assert records[0]["run_id"] == "unit_daily_preview"
    assert records[0]["source_daily_bars_csv"] == str(bars_csv)
    assert records[0]["sma_status"] == "evaluated"


def test_daily_preview_command_has_no_stale_run_log_defaults() -> None:
    parser = _paper_lab_daily_preview_parser()
    defaults = {
        action.dest: action.default
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert defaults["run_id"] is None
    assert defaults["run_log"] is None
    assert defaults["order_reconciliation_log"] is None
    assert defaults["daily_bars_csv"] is None
    assert defaults["market_data_csv"] is None
    assert "runs/paper_lab/" not in str(defaults["run_log"]).lower()
    assert "m38" not in str(defaults["order_reconciliation_log"]).lower()


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


def test_conflicting_reconciliation_records_fail_closed(tmp_path) -> None:  # noqa: ANN001
    terminal = _terminal_reconciliation_record()
    reconciliation_log = _write_jsonl(
        tmp_path / "conflicting_reconciliation.jsonl",
        _m383_nonterminal_reconciliation_record(),
        terminal,
    )

    payload = build_etf_sma_daily_preview(_config(reconciliation_log))

    assert payload["daily_preview_status"] == "blocked"
    assert "missing_or_invalid_order_reconciliation" in payload["blockers"]
    assert (
        "multiple_conflicting_order_reconciliation_records"
        in payload["source_order_reconciliation"]["blockers"]
    )
    _assert_never_mutates(payload)


def _config(
    reconciliation_log: Path,
    **overrides: object,
) -> EtfSmaDailyPreviewConfig:
    values = {
        "run_id": "unit_daily_preview",
        "symbol": "SPY",
        "generated_at": FIXED_GENERATED_AT,
        "order_reconciliation_log": reconciliation_log,
    }
    values.update(overrides)
    return EtfSmaDailyPreviewConfig(**values)


def _m383_nonterminal_reconciliation_record() -> dict[str, object]:
    return {
        "run_id": "m383_m376_spy_close_order_reconciliation",
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
        "observed_submitted_at": "2026-06-03T23:57:14.030265+00:00",
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
        "non_spy_positions": [],
        "blockers": ["m376_order_nonterminal", "open_order_present"],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "account_observation_available": True,
        "positions_observation_available": True,
        "orders_observation_available": True,
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }


def _terminal_reconciliation_record() -> dict[str, object]:
    record = _m383_nonterminal_reconciliation_record()
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
            "spy_position_qty": "",
            "open_order_count": 0,
            "open_order_symbols": [],
            "open_order_client_order_ids": [],
            "open_order_broker_order_ids": [],
            "open_order_statuses": [],
            "open_order_sides": [],
            "open_order_quantities": [],
            "open_order_filled_quantities": [],
            "non_spy_positions": [],
            "blockers": [],
        }
    )
    return record


def _terminal_position_reconciliation_record() -> dict[str, object]:
    record = _terminal_reconciliation_record()
    record["spy_position_qty"] = QUANTITY
    return record


def _write_daily_bars_csv(path: Path, *adjusted_closes: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["symbol,date,open,high,low,close,adjusted_close,volume\n"]
    for index, adjusted_close in enumerate(adjusted_closes):
        bar_date = BAR_START_DATE + timedelta(days=index)
        lines.append(
            "SPY,"
            f"{bar_date.isoformat()},"
            f"{adjusted_close},"
            f"{adjusted_close},"
            f"{adjusted_close},"
            f"{adjusted_close},"
            f"{adjusted_close},"
            "100\n"
        )
    path.write_text("".join(lines), encoding="utf-8")
    return path


def _generated_at_for_bar_index(index: int) -> str:
    return f"{(BAR_START_DATE + timedelta(days=index)).isoformat()}T12:00:00+00:00"


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


def _assert_never_mutates(payload: dict[str, object]) -> None:
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False


def _paper_lab_daily_preview_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "paper-lab-daily-preview" in choices:
            return choices["paper-lab-daily-preview"]
    raise AssertionError("paper-lab-daily-preview parser not found")


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
