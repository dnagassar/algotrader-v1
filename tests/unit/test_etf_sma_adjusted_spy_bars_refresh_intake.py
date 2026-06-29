from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import socket
import sys

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_adjusted_spy_bars_refresh_intake import (
    EtfSmaAdjustedSpyBarsRefreshIntakeConfig,
    build_etf_sma_adjusted_spy_bars_refresh_intake,
    render_etf_sma_adjusted_spy_bars_refresh_intake_json,
    write_etf_sma_adjusted_spy_bars_refresh_intake_jsonl,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_adjusted_spy_bars_refresh_intake.py")

CANONICAL_COLUMNS = (
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)

SAFETY_FALSE_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "live_authorized",
    "network_access_attempted",
    "credential_access_attempted",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
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
    "retry",
    "socket",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


def test_config_requires_expected_latest_bar_date(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError, match="expected_latest_bar_date is required"):
        EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
            expected_latest_bar_date="",
            input_csv=tmp_path / "in.csv",
            canonical_csv=tmp_path / "out.csv",
            run_log=tmp_path / "log.jsonl",
        )


def test_config_requires_iso_date(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError, match="expected_latest_bar_date must be a YYYY-MM-DD date"):
        EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
            expected_latest_bar_date="2026-6-7",
            input_csv=tmp_path / "in.csv",
            canonical_csv=tmp_path / "out.csv",
            run_log=tmp_path / "log.jsonl",
        )


def test_missing_input_file_emits_blocked_missing_manifest(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "missing.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    write_etf_sma_adjusted_spy_bars_refresh_intake_jsonl(payload, run_log)

    assert payload["refresh_state"] == "blocked_missing_operator_input_csv"
    assert "missing_operator_input_csv" in payload["refresh_blockers"]
    assert payload["latest_local_bar_date"] == ""
    assert payload["accepted_row_count"] == 0
    assert not canonical_csv.exists()
    _assert_safety_false(payload)

    # Verify JSONL content
    lines = run_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == payload


def test_malformed_csv_is_rejected(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "malformed.csv"
    input_csv.write_text("date,open,high,low,close,adjusted_close,volume\n2026-06-06,100,101,99,100\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "blocked_invalid_adjusted_bars"
    assert "malformed_csv_row" in payload["refresh_blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_missing_required_columns_is_rejected(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "missing_cols.csv"
    input_csv.write_text("date,open,high,low,adjusted_close,volume\n2026-06-06,100,101,99,100,1000\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "blocked_invalid_adjusted_bars"
    assert "missing_required_columns:close" in payload["refresh_blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_missing_adjusted_close_is_rejected(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "missing_adj.csv"
    # Even if total_return_close exists, M446 correction 1 requires adjusted_close specifically
    input_csv.write_text("date,open,high,low,close,total_return_close,volume\n2026-06-06,100,101,99,100,101,1000\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "blocked_invalid_adjusted_bars"
    assert "missing_adjusted_close" in payload["refresh_blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_duplicate_dates_is_rejected(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "duplicate_dates.csv"
    rows = [
        "date,open,high,low,close,adjusted_close,volume",
        "2026-06-05,100,101,99,100,100,1000",
        "2026-06-05,100,101,99,100,100,1000",
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "blocked_invalid_adjusted_bars"
    assert "duplicate_dates" in payload["refresh_blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_invalid_ohlcv_values_is_rejected(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "invalid_ohlcv.csv"
    rows = [
        "date,open,high,low,close,adjusted_close,volume",
        "2026-06-05,0,101,99,100,100,1000",  # open is 0
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "blocked_invalid_adjusted_bars"
    assert "invalid_ohlcv_values" in payload["refresh_blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_zero_valid_rows_is_rejected(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "zero_rows.csv"
    input_csv.write_text("date,open,high,low,close,adjusted_close,volume\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "blocked_invalid_adjusted_bars"
    assert "zero_valid_rows" in payload["refresh_blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_non_spy_symbol_rejected_if_symbol_column_exists(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "non_spy.csv"
    rows = [
        "symbol,date,open,high,low,close,adjusted_close,volume",
        "AAPL,2026-06-05,100,101,99,100,100,1000",
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "blocked_invalid_adjusted_bars"
    assert "symbol_scope_must_be_spy" in payload["refresh_blockers"]
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_approved_non_spy_symbol_can_be_validated_offline(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "qqq.csv"
    rows = [
        "symbol,date,open,high,low,close,adjusted_close,volume",
        "QQQ,2026-06-06,100,101,99,100,100.25,1000",
        "QQQ,2026-06-07,101,102,100,101,101.25,2000",
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
        symbol="QQQ",
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)

    assert payload["symbol"] == "QQQ"
    assert payload["refresh_state"] == "accepted_current_adjusted_bars"
    assert payload["accepted_row_count"] == 2
    out_rows = canonical_csv.read_text(encoding="utf-8").splitlines()
    assert out_rows[1].startswith("QQQ,2026-06-06,")
    _assert_safety_false(payload)


def test_accepted_current_date(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "current.csv"
    rows = [
        "date,open,high,low,close,adjusted_close,volume",
        "2026-06-06,100,101,99,100,100.25,1000",
        "2026-06-07,101,102,100,101,101.25,2000",
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "accepted_current_adjusted_bars"
    assert payload["latest_local_bar_date"] == "2026-06-07"
    assert payload["accepted_row_count"] == 2
    assert payload["date_range_start"] == "2026-06-06"
    assert payload["date_range_end"] == "2026-06-07"
    assert payload["refresh_blockers"] == []
    assert payload["refresh_warnings"] == []
    assert canonical_csv.exists()
    _assert_safety_false(payload)


def test_accepted_ahead_date_warning(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "ahead.csv"
    rows = [
        "date,open,high,low,close,adjusted_close,volume",
        "2026-06-06,100,101,99,100,100.25,1000",
        "2026-06-08,101,102,100,101,101.25,2000",
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "accepted_adjusted_bars_ahead_of_expected"
    assert payload["latest_local_bar_date"] == "2026-06-08"
    assert "latest_local_bar_date_after_expected" in payload["refresh_warnings"]
    assert payload["refresh_blockers"] == []
    assert canonical_csv.exists()
    _assert_safety_false(payload)


def test_stale_date_blocker(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "stale.csv"
    rows = [
        "date,open,high,low,close,adjusted_close,volume",
        "2026-06-05,100,101,99,100,100.25,1000",
        "2026-06-06,101,102,100,101,101.25,2000",
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "blocked_stale_adjusted_bars"
    assert payload["latest_local_bar_date"] == "2026-06-06"
    assert "latest_local_bar_date_before_expected" in payload["refresh_blockers"]
    assert payload["refresh_warnings"] == []
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_deterministic_ascending_sorting_in_canonical_csv(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "unsorted.csv"
    # Input has date unsorted
    rows = [
        "date,open,high,low,close,adjusted_close,volume",
        "2026-06-07,101,102,100,101,101.25,2000",
        "2026-06-05,99,100,98,99,99.25,500",
        "2026-06-06,100,101,99,100,100.25,1000",
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    config = EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
        expected_latest_bar_date="2026-06-07",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
    )

    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(config)
    assert payload["refresh_state"] == "accepted_current_adjusted_bars"
    assert canonical_csv.exists()

    # Read output and check order
    out_rows = canonical_csv.read_text(encoding="utf-8").splitlines()
    assert out_rows[0] == "symbol,date,open,high,low,close,adjusted_close,volume"
    assert out_rows[1].startswith("SPY,2026-06-05,")
    assert out_rows[2].startswith("SPY,2026-06-06,")
    assert out_rows[3].startswith("SPY,2026-06-07,")


def test_cli_dispatch_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M446 command must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("M446 command must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("M446 command must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    input_csv = tmp_path / "in.csv"
    rows = [
        "date,open,high,low,close,adjusted_close,volume",
        "2026-06-07,100,101,99,100,100.25,1000",
    ]
    input_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-adjusted-spy-bars-refresh-intake",
            "--expected-latest-bar-date",
            "2026-06-07",
            "--input-csv",
            str(input_csv),
            "--canonical-csv",
            str(canonical_csv),
            "--run-log",
            str(run_log),
            "--format",
            "json",
        )
    )
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert printed["refresh_state"] == "accepted_current_adjusted_bars"
    assert printed["latest_local_bar_date"] == "2026-06-07"
    assert run_log.exists()
    assert json.loads(run_log.read_text(encoding="utf-8").strip()) == printed


def test_command_imports_no_forbidden_packages() -> None:
    imports = _import_references(MODULE_PATH)
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _assert_safety_false(payload: dict[str, object]) -> None:
    for field_name in SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["profit_claim"] == "none"


def _import_references(path: Path) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefix = "." * node.level
            imports.add(f"{prefix}{node.module}")
    return imports


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
