from __future__ import annotations

import ast
from datetime import date, timedelta
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import algotrader.cli as cli_module
import pytest
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_cycle_unified_preview import (
    ETF_SMA_CYCLE_UNIFIED_PREVIEW_LABELS,
    EtfSmaCycleUnifiedPreviewConfig,
    build_etf_sma_cycle_unified_preview,
    write_etf_sma_cycle_unified_preview_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
MODULE_PATH = Path("src/algotrader/execution/etf_sma_cycle_unified_preview.py")
GENERATED_AT = "2026-06-05T00:00:00+00:00"
CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
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
    "retry",
    "socket",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


def test_etf_sma_cycle_help_includes_unified_preview_options() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "algotrader.cli",
            "etf-sma-cycle",
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
    assert "etf-sma-cycle" in result.stdout
    assert "--order-reconciliation-log" in result.stdout
    assert "--generated-at" in result.stdout
    assert "--daily-bars-csv" in result.stdout
    assert "--run-log" in result.stdout


def test_terminal_filled_m376_fixture_lifts_open_order_blocker(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m391_m376_spy_close_order_reconciliation_retry.jsonl",
        _terminal_reconciliation_record(),
    )
    run_log = tmp_path / "m394_unified_preview.jsonl"

    payload = build_etf_sma_cycle_unified_preview(
        _config(reconciliation_log, market_data_csv=tmp_path / "missing_bars.csv")
    )
    result = write_etf_sma_cycle_unified_preview_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]
    assert payload["record_type"] == "etf_sma_cycle_unified_preview"
    assert payload["command"] == "etf-sma-cycle"
    assert payload["daily_preview_status"] == "review_only"
    assert payload["state_rollup_status"] == "review_only"
    assert payload["m376_terminal"] is True
    assert payload["m376_status"] == "filled"
    assert payload["m376_terminal_state"] == "terminal"
    assert payload["m376_terminal_reason"] == "status_filled"
    assert payload["open_order_count"] == 0
    assert payload["open_order_present"] is False
    assert payload["open_spy_order_present"] is False
    assert payload["spy_position_qty"] == ""
    assert payload["blockers"] == []
    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["cycle_decision_reason"] == "sma_insufficient_history"
    assert payload["cycle_next_allowed_action"] == (
        "offline_research_or_operator_review_only"
    )
    assert payload["next_allowed_action"] == (
        "offline_research_or_operator_review_only"
    )
    assert payload["labels"] == list(ETF_SMA_CYCLE_UNIFIED_PREVIEW_LABELS)
    assert "paper_lab_only" in payload["labels"]
    assert "not_live_authorized" in payload["labels"]
    assert "profit_claim=none" in payload["labels"]
    assert payload["source_order_reconciliation"]["path"] == str(reconciliation_log)
    readiness = payload["data_readiness"]
    assert readiness["sma_short_window"] == 50
    assert readiness["sma_long_window"] == 200
    assert readiness["required_usable_bars"] == 200
    assert readiness["observed_usable_bars"] is None
    assert readiness["missing_usable_bars"] is None
    assert readiness["readiness_state"] == "unknown_from_cycle_artifact"
    assert readiness["readiness_reason"] == "observed_usable_bars_missing"
    assert "local_market_data_bars" in readiness["missing_evidence"]
    assert "observed_usable_bars" in readiness["missing_evidence"]
    assert readiness["source"] == "offline_etf_sma_cycle_evidence"
    assert readiness["source_market_data"]["input_available"] is False
    _assert_never_mutates(payload)


def test_insufficient_history_emits_sma_data_readiness_counts(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m391_m376_spy_close_order_reconciliation_retry.jsonl",
        _terminal_reconciliation_record(),
    )
    market_data_csv = _write_bars_csv(tmp_path / "spy_150_daily_bars.csv", 150)
    run_log = tmp_path / "m397_unified_preview.jsonl"

    payload = build_etf_sma_cycle_unified_preview(
        _config(reconciliation_log, market_data_csv=market_data_csv)
    )
    result = write_etf_sma_cycle_unified_preview_jsonl(payload, run_log)
    records = _read_jsonl(run_log)
    readiness = payload["data_readiness"]

    assert result.record_count == 1
    assert records == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["cycle_decision_reason"] == "sma_insufficient_history"
    assert readiness["sma_short_window"] == 50
    assert readiness["sma_long_window"] == 200
    assert readiness["required_usable_bars"] == 200
    assert readiness["observed_usable_bars"] == 150
    assert readiness["missing_usable_bars"] == 50
    assert readiness["readiness_state"] == "insufficient_history"
    assert readiness["readiness_reason"] == "sma_insufficient_history"
    assert readiness["missing_evidence"] == []
    assert readiness["source"] == "offline_etf_sma_cycle_evidence"
    assert readiness["source_record_type"] == "etf_sma_cycle"
    assert readiness["source_market_data"] == {
        "source": str(market_data_csv),
        "input_available": True,
        "total_bar_count": 150,
        "usable_bar_count": 150,
        "ignored_future_bar_count": 0,
    }
    _assert_never_mutates(payload)


def test_ready_history_non_insufficient_cycle_remains_offline_and_non_mutating(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m391_m376_spy_close_order_reconciliation_retry.jsonl",
        _terminal_reconciliation_record(),
    )
    market_data_csv = _write_bars_csv(tmp_path / "spy_220_daily_bars.csv", 220)

    payload = build_etf_sma_cycle_unified_preview(
        _config(reconciliation_log, market_data_csv=market_data_csv)
    )
    readiness = payload["data_readiness"]

    assert payload["cycle_decision"] != "insufficient_history"
    assert payload["cycle_decision_reason"] != "sma_insufficient_history"
    assert readiness["observed_usable_bars"] == 220
    assert readiness["missing_usable_bars"] == 0
    assert readiness["readiness_state"] == "ready_from_cycle_artifact"
    assert readiness["readiness_reason"] == "sma_usable_bars_ready"
    _assert_never_mutates(payload)


def test_daily_bars_csv_199_usable_bars_marks_insufficient_history(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m391_m376_spy_close_order_reconciliation_retry.jsonl",
        _terminal_reconciliation_record(),
    )
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_199_daily_bars.csv",
        _daily_rows(199),
    )
    run_log = tmp_path / "m398_local_bars_199.jsonl"

    payload = build_etf_sma_cycle_unified_preview(
        _config(reconciliation_log, daily_bars_csv=daily_bars_csv)
    )
    result = write_etf_sma_cycle_unified_preview_jsonl(payload, run_log)
    readiness = payload["data_readiness"]

    assert result.record_count == 1
    assert _read_jsonl(run_log) == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert readiness["required_usable_bars"] == 200
    assert readiness["observed_usable_bars"] == 199
    assert readiness["missing_usable_bars"] == 1
    assert readiness["readiness_state"] == "insufficient_history"
    assert readiness["readiness_reason"] == "sma_insufficient_history"
    assert readiness["missing_evidence"] == []
    assert readiness["source"]["type"] == "local_daily_bars_csv"
    assert readiness["source"]["path"] == str(daily_bars_csv)
    assert readiness["source_market_data"] == {
        "source": str(daily_bars_csv),
        "input_available": True,
        "total_bar_count": 199,
        "usable_bar_count": 199,
        "ignored_future_bar_count": 0,
        "total_row_count": 199,
        "ignored_wrong_symbol_row_count": 0,
    }
    _assert_never_mutates(payload)


def test_daily_bars_csv_200_usable_bars_marks_ready(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m391_m376_spy_close_order_reconciliation_retry.jsonl",
        _terminal_reconciliation_record(),
    )
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_200_daily_bars.csv",
        _daily_rows(200),
    )
    run_log = tmp_path / "m398_local_bars_200.jsonl"

    payload = build_etf_sma_cycle_unified_preview(
        _config(reconciliation_log, daily_bars_csv=daily_bars_csv)
    )
    result = write_etf_sma_cycle_unified_preview_jsonl(payload, run_log)
    readiness = payload["data_readiness"]

    assert result.record_count == 1
    assert _read_jsonl(run_log) == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert readiness["required_usable_bars"] == 200
    assert readiness["observed_usable_bars"] == 200
    assert readiness["missing_usable_bars"] == 0
    assert readiness["readiness_state"] == "ready"
    assert readiness["readiness_reason"] == "sma_usable_bars_ready"
    assert readiness["missing_evidence"] == []
    assert readiness["source"]["type"] == "local_daily_bars_csv"
    assert readiness["source_market_data"]["input_available"] is True
    assert readiness["source_market_data"]["ignored_future_bar_count"] == 0
    _assert_never_mutates(payload)


def test_omitted_daily_bars_csv_preserves_unknown_data_readiness(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m391_m376_spy_close_order_reconciliation_retry.jsonl",
        _terminal_reconciliation_record(),
    )

    payload = build_etf_sma_cycle_unified_preview(_config(reconciliation_log))
    readiness = payload["data_readiness"]

    assert readiness["required_usable_bars"] == 200
    assert readiness["observed_usable_bars"] is None
    assert readiness["missing_usable_bars"] is None
    assert readiness["readiness_state"] == "unknown_from_cycle_artifact"
    assert readiness["readiness_reason"] == "observed_usable_bars_missing"
    assert "local_market_data_bars" in readiness["missing_evidence"]
    assert "observed_usable_bars" in readiness["missing_evidence"]
    assert readiness["source_market_data"]["input_available"] is False
    _assert_never_mutates(payload)


def test_supplied_missing_daily_bars_csv_fails_closed(
    tmp_path,
) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m391_m376_spy_close_order_reconciliation_retry.jsonl",
        _terminal_reconciliation_record(),
    )

    with pytest.raises(ValidationError, match="daily_bars_csv"):
        build_etf_sma_cycle_unified_preview(
            _config(
                reconciliation_log,
                daily_bars_csv=tmp_path / "missing_spy_daily_bars.csv",
            )
        )


def test_nonterminal_open_m376_fixture_remains_blocked(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m376_open_reconciliation.jsonl",
        _nonterminal_reconciliation_record(),
    )

    payload = build_etf_sma_cycle_unified_preview(
        _config(reconciliation_log, market_data_csv=tmp_path / "missing_bars.csv")
    )

    assert payload["state_rollup_status"] == "blocked"
    assert payload["m376_terminal"] is False
    assert payload["m376_status"] == "accepted"
    assert payload["m376_terminal_state"] == "nonterminal"
    assert payload["open_order_count"] == 1
    assert payload["open_order_present"] is True
    assert payload["open_spy_order_present"] is True
    assert "m376_order_nonterminal" in payload["blockers"]
    assert "open_order_present" in payload["blockers"]
    assert payload["cycle_decision"] == "blocked/open_order_present"
    assert payload["next_allowed_action"] == "offline_work_or_read_only_reconciliation"
    assert "spy_submit_until_m376_terminal" in payload["forbidden_actions"]
    assert payload["preview_order_authorized"] is False
    _assert_never_mutates(payload)


def test_missing_reconciliation_artifact_fails_closed(tmp_path) -> None:  # noqa: ANN001
    missing_log = tmp_path / "missing_reconciliation.jsonl"

    payload = build_etf_sma_cycle_unified_preview(
        _config(missing_log, market_data_csv=tmp_path / "missing_bars.csv")
    )

    assert payload["state_rollup_status"] == "blocked"
    assert payload["daily_preview_status"] == "blocked"
    assert "missing_or_invalid_order_reconciliation" in payload["blockers"]
    assert payload["source_order_reconciliation"]["found"] is False
    assert payload["source_order_reconciliation"]["parsed"] is False
    assert payload["source_order_reconciliation"]["error"] == "path_not_found"
    assert payload["next_allowed_action"] == (
        "read_only_reconciliation_before_any_spy_submit"
    )
    _assert_never_mutates(payload)


def test_malformed_reconciliation_artifact_fails_closed(tmp_path) -> None:  # noqa: ANN001
    malformed_log = tmp_path / "malformed_reconciliation.jsonl"
    malformed_log.write_text("{not-json}\n", encoding="utf-8")

    payload = build_etf_sma_cycle_unified_preview(
        _config(malformed_log, market_data_csv=tmp_path / "missing_bars.csv")
    )

    assert payload["state_rollup_status"] == "blocked"
    assert payload["daily_preview_status"] == "blocked"
    assert "missing_or_invalid_order_reconciliation" in payload["blockers"]
    assert payload["source_order_reconciliation"]["found"] is True
    assert payload["source_order_reconciliation"]["parsed"] is False
    assert payload["source_order_reconciliation"]["error"] == "invalid_jsonl_line_1"
    _assert_never_mutates(payload)


def test_cli_unified_preview_dispatch_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("unified preview must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("unified preview must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("unified preview must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    reconciliation_log = _write_jsonl(
        tmp_path / "m391_reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )
    run_log = tmp_path / "m394_cycle.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-cycle",
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m394_cycle",
            "--run-log",
            str(run_log),
            "--order-reconciliation-log",
            str(reconciliation_log),
            "--market-data-csv",
            str(tmp_path / "missing_bars.csv"),
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
    assert payload["record_type"] == "etf_sma_cycle_unified_preview"
    assert payload["m376_terminal"] is True
    assert payload["open_order_present"] is False
    _assert_never_mutates(payload)


def test_cli_daily_bars_csv_emits_ready_readiness_without_broker_network_or_credentials(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("unified preview must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("unified preview must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("unified preview must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    reconciliation_log = _write_jsonl(
        tmp_path / "m391_reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_200_daily_bars.csv",
        _daily_rows(200),
    )
    run_log = tmp_path / "m398_cycle.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-cycle",
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m398_cycle",
            "--run-log",
            str(run_log),
            "--order-reconciliation-log",
            str(reconciliation_log),
            "--daily-bars-csv",
            str(daily_bars_csv),
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
    assert payload["data_readiness"]["observed_usable_bars"] == 200
    assert payload["data_readiness"]["missing_usable_bars"] == 0
    assert payload["data_readiness"]["readiness_state"] == "ready"
    _assert_never_mutates(payload)


def test_unified_preview_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def test_research_and_signal_layers_do_not_import_unified_cycle_module() -> None:
    for package in (Path("src/algotrader/research"), Path("src/algotrader/signals")):
        for path in package.rglob("*.py"):
            assert (
                "algotrader.execution.etf_sma_cycle_unified_preview"
                not in _import_references(path)
            )


def _config(
    reconciliation_log: Path,
    **overrides: object,
) -> EtfSmaCycleUnifiedPreviewConfig:
    values = {
        "run_id": "unit_m394_cycle",
        "symbol": "SPY",
        "generated_at": GENERATED_AT,
        "order_reconciliation_log": reconciliation_log,
    }
    values.update(overrides)
    return EtfSmaCycleUnifiedPreviewConfig(**values)


def _nonterminal_reconciliation_record() -> dict[str, object]:
    return {
        "run_id": "m376_spy_close_order_reconciliation",
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
        "account_observation_available": True,
        "positions_observation_available": True,
        "orders_observation_available": True,
    }


def _terminal_reconciliation_record() -> dict[str, object]:
    record = _nonterminal_reconciliation_record()
    record.update(
        {
            "run_id": "m391_m376_spy_close_order_reconciliation_retry",
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


def _write_bars_csv(path: Path, count: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = date(2025, 1, 1)
    lines = ["timestamp,symbol,open,high,low,close,volume"]
    for index in range(count):
        day = start + timedelta(days=index)
        price = 100 + index
        lines.append(
            f"{day.isoformat()}T00:00:00+00:00,SPY,"
            f"{price},{price},{price},{price},1000"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_daily_bars_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
    )
    lines = [",".join(columns)]
    lines.extend(",".join(row[column] for column in columns) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _daily_rows(count: int) -> list[dict[str, str]]:
    start = date(2025, 1, 1)
    return [
        _daily_row("SPY", start + timedelta(days=index), 100 + index)
        for index in range(count)
    ]


def _daily_row(symbol: str, day: date, price: int) -> dict[str, str]:
    return {
        "symbol": symbol,
        "date": day.isoformat(),
        "open": str(price),
        "high": str(price),
        "low": str(price),
        "close": str(price),
        "adjusted_close": str(price),
        "volume": "1000",
    }


def _assert_never_mutates(payload: dict[str, object]) -> None:
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_actions_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["preview_order_authorized"] is False


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in SCRUBBED_ENV_VARS:
        env.pop(name, None)
    env["PYTHONPATH"] = str(SRC_ROOT)
    return env


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
