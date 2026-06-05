from __future__ import annotations

import ast
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import socket

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_cycle_unified_preview import (
    EtfSmaCycleUnifiedPreviewConfig,
    build_etf_sma_cycle_unified_preview,
)
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    load_local_daily_bars_csv,
)
from algotrader.research.local_daily_bars_checkpoint import (
    LocalDailyBarsCheckpointConfig,
    build_local_daily_bars_checkpoint,
)
from algotrader.research.local_daily_bars_intake import (
    LocalDailyBarsIntakeConfig,
    build_local_daily_bars_intake_manifest,
    write_local_daily_bars_intake_manifest_jsonl,
)


MODULE_PATH = Path("src/algotrader/research/local_daily_bars_intake.py")
AS_OF = "2026-06-05"
AS_OF_DATE = date.fromisoformat(AS_OF)
GENERATED_AT = "2026-06-05T00:00:00+00:00"
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
    "subprocess",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
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


def test_199_accepted_spy_bars_write_insufficient_history_manifest(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_199.csv",
        _daily_rows(199),
    )
    output_csv = tmp_path / "canonical" / "spy_daily_bars.csv"
    run_log = tmp_path / "m400_199.jsonl"

    payload = build_local_daily_bars_intake_manifest(
        _config(input_csv, output_csv=output_csv)
    )
    result = write_local_daily_bars_intake_manifest_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["record_type"] == "local_daily_bars_intake_manifest"
    assert payload["command"] == "local-daily-bars-intake"
    assert payload["run_id"] == "unit_m400_local_daily_bars_intake"
    assert payload["symbol"] == "SPY"
    assert payload["as_of"] == AS_OF
    assert payload["input_csv"] == str(input_csv)
    assert payload["output_csv"] == str(output_csv)
    assert payload["csv_schema"] == list(LOCAL_DAILY_BARS_CSV_COLUMNS)
    assert payload["required_columns"] == list(LOCAL_DAILY_BARS_CSV_COLUMNS)
    assert payload["observed_columns"] == list(LOCAL_DAILY_BARS_CSV_COLUMNS)
    assert payload["input_sha256"] == _sha256(input_csv)
    assert payload["output_sha256"] == _sha256(output_csv)
    assert payload["input_row_count"] == 199
    assert payload["accepted_row_count"] == 199
    assert payload["wrong_symbol_row_count"] == 0
    assert payload["future_bar_count_excluded"] == 0
    assert payload["duplicate_date_count"] == 0
    assert payload["first_bar_date"] == "2025-11-19"
    assert payload["last_bar_date"] == AS_OF
    assert payload["required_usable_bars"] == 200
    assert payload["usable_bar_count"] == 199
    assert payload["missing_usable_bars"] == 1
    assert payload["readiness_state"] == "insufficient_history"
    assert payload["readiness_reason"] == "sma_insufficient_history"
    assert payload["blockers"] == ["missing_usable_bars"]
    assert _read_csv_rows(output_csv)[0] == list(LOCAL_DAILY_BARS_CSV_COLUMNS)
    assert len(_read_csv_rows(output_csv)) == 200
    _assert_safety_booleans_false(payload)


def test_200_accepted_spy_bars_write_ready_manifest(tmp_path) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_200.csv",
        _daily_rows(200),
    )
    output_csv = tmp_path / "canonical" / "spy_daily_bars.csv"
    run_log = tmp_path / "m400_200.jsonl"

    payload = build_local_daily_bars_intake_manifest(
        _config(input_csv, output_csv=output_csv)
    )
    result = write_local_daily_bars_intake_manifest_jsonl(payload, run_log)

    assert result.record_count == 1
    assert _read_jsonl(run_log) == [payload]
    assert payload["input_row_count"] == 200
    assert payload["accepted_row_count"] == 200
    assert payload["usable_bar_count"] == 200
    assert payload["missing_usable_bars"] == 0
    assert payload["first_bar_date"] == "2025-11-18"
    assert payload["last_bar_date"] == AS_OF
    assert payload["readiness_state"] == "ready"
    assert payload["readiness_reason"] == "sma_usable_bars_ready"
    assert payload["blockers"] == []
    _assert_safety_booleans_false(payload)


def test_wrong_symbol_rows_are_ignored_and_counted(tmp_path) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_mixed_symbols.csv",
        [
            _row("QQQ", "2026-06-04", 400),
            *_daily_rows(200),
            _row("IWM", "2026-06-05", 500),
        ],
    )
    output_csv = tmp_path / "spy_daily_bars.csv"

    payload = build_local_daily_bars_intake_manifest(
        _config(input_csv, output_csv=output_csv)
    )

    assert payload["input_row_count"] == 202
    assert payload["accepted_row_count"] == 200
    assert payload["wrong_symbol_row_count"] == 2
    assert payload["readiness_state"] == "ready"
    assert {row[0] for row in _read_csv_rows(output_csv)[1:]} == {"SPY"}
    _assert_safety_booleans_false(payload)


def test_future_dated_requested_symbol_rows_are_excluded_and_counted(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_with_future.csv",
        [
            *_daily_rows(199),
            _row("SPY", "2026-06-06", 400),
        ],
    )
    output_csv = tmp_path / "spy_daily_bars.csv"

    payload = build_local_daily_bars_intake_manifest(
        _config(input_csv, output_csv=output_csv)
    )

    assert payload["input_row_count"] == 200
    assert payload["accepted_row_count"] == 199
    assert payload["future_bar_count_excluded"] == 1
    assert payload["last_bar_date"] == AS_OF
    assert _read_csv_rows(output_csv)[-1][1] == AS_OF
    assert "2026-06-06" not in [row[1] for row in _read_csv_rows(output_csv)[1:]]
    _assert_safety_booleans_false(payload)


def test_unsorted_input_is_canonicalized_into_ascending_date_order(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_unsorted_spy.csv",
        [
            _row("SPY", "2026-06-03", 103),
            _row("SPY", "2026-06-01", 101),
            _row("SPY", "2026-06-02", 102),
        ],
    )
    output_csv = tmp_path / "spy_daily_bars.csv"

    payload = build_local_daily_bars_intake_manifest(
        _config(input_csv, output_csv=output_csv)
    )
    dates = [row[1] for row in _read_csv_rows(output_csv)[1:]]

    assert payload["input_sorted_by_date"] is False
    assert payload["canonical_sorted_by_date"] is True
    assert dates == ["2026-06-01", "2026-06-02", "2026-06-03"]


def test_duplicate_requested_symbol_dates_fail_closed(tmp_path) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_duplicate_spy.csv",
        [
            _row("SPY", "2026-06-04", 100),
            _row("SPY", "2026-06-04", 101),
        ],
    )
    output_csv = tmp_path / "spy_daily_bars.csv"

    with pytest.raises(ValidationError, match="duplicates date 2026-06-04"):
        build_local_daily_bars_intake_manifest(
            _config(input_csv, output_csv=output_csv)
        )

    assert not output_csv.exists()


def test_missing_required_columns_fail_closed(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "operator_missing_columns.csv"
    input_csv.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "SPY,2026-06-04,100,101,99,100,1000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="adjusted_close"):
        build_local_daily_bars_intake_manifest(
            _config(input_csv, output_csv=tmp_path / "spy_daily_bars.csv")
        )


@pytest.mark.parametrize(
    ("column", "value", "match"),
    (
        ("date", "2026/06/04", "YYYY-MM-DD"),
        ("close", "0", "greater than zero"),
        ("volume", "-1", "zero or greater"),
    ),
)
def test_invalid_price_volume_or_date_values_fail_closed(
    tmp_path,
    column: str,
    value: str,
    match: str,
) -> None:  # noqa: ANN001
    row = _row("SPY", "2026-06-04", 100)
    row[column] = value
    input_csv = _write_daily_bars_csv(tmp_path / "operator_invalid.csv", [row])

    with pytest.raises(ValidationError, match=match):
        build_local_daily_bars_intake_manifest(
            _config(input_csv, output_csv=tmp_path / "spy_daily_bars.csv")
        )


def test_missing_input_path_fails_closed(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError, match="existing local CSV"):
        LocalDailyBarsIntakeConfig(
            run_id="unit_m400_local_daily_bars_intake",
            symbol="SPY",
            input_csv=tmp_path / "missing_operator_input.csv",
            output_csv=tmp_path / "spy_daily_bars.csv",
            as_of=AS_OF,
        )


def test_canonical_csv_can_be_consumed_by_m399_checkpoint(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_200.csv",
        _daily_rows(200),
    )
    output_csv = tmp_path / "spy_daily_bars.csv"
    build_local_daily_bars_intake_manifest(_config(input_csv, output_csv=output_csv))

    payload = build_local_daily_bars_checkpoint(
        LocalDailyBarsCheckpointConfig(
            run_id="unit_m399_local_daily_bars_checkpoint",
            symbol="SPY",
            daily_bars_csv=output_csv,
            as_of=AS_OF,
        )
    )

    assert payload["record_type"] == "local_daily_bars_checkpoint"
    assert payload["usable_bar_count"] == 200
    assert payload["missing_usable_bars"] == 0
    assert payload["readiness_state"] == "ready"
    _assert_safety_booleans_false(payload)


def test_canonical_csv_can_be_consumed_by_unified_cycle_readiness_path(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_200.csv",
        _daily_rows(200),
    )
    output_csv = tmp_path / "spy_daily_bars.csv"
    reconciliation_log = _write_jsonl(
        tmp_path / "m391_reconciliation.jsonl",
        _terminal_reconciliation_record(),
    )
    build_local_daily_bars_intake_manifest(_config(input_csv, output_csv=output_csv))

    payload = build_etf_sma_cycle_unified_preview(
        EtfSmaCycleUnifiedPreviewConfig(
            run_id="unit_m400_cycle_readiness",
            symbol="SPY",
            generated_at=GENERATED_AT,
            order_reconciliation_log=reconciliation_log,
            daily_bars_csv=output_csv,
        )
    )
    readiness = payload["data_readiness"]

    assert readiness["source_record_type"] == "local_daily_bars_csv"
    assert readiness["observed_usable_bars"] == 200
    assert readiness["missing_usable_bars"] == 0
    assert readiness["readiness_state"] == "ready"
    _assert_safety_booleans_false(payload)


def test_cli_local_daily_bars_intake_smoke_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("local daily-bars intake must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("local daily-bars intake must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("local daily-bars intake must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_200.csv",
        _daily_rows(200),
    )
    output_csv = tmp_path / "canonical" / "spy_daily_bars.csv"
    run_log = tmp_path / "m400_intake.jsonl"

    exit_code = cli_module.main(
        (
            "local-daily-bars-intake",
            "--symbol",
            "SPY",
            "--input-csv",
            str(input_csv),
            "--output-csv",
            str(output_csv),
            "--as-of",
            AS_OF,
            "--run-id",
            "unit_m400_local_daily_bars_intake",
            "--run-log",
            str(run_log),
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
    assert output_csv.is_file()
    assert payload["record_type"] == "local_daily_bars_intake_manifest"
    assert payload["readiness_state"] == "ready"
    assert payload["usable_bar_count"] == 200
    assert load_local_daily_bars_csv(output_csv, symbol="SPY", as_of=AS_OF).observed_usable_bars == 200
    _assert_safety_booleans_false(payload)


def test_local_daily_bars_intake_parser_registration() -> None:
    parser = _local_daily_bars_intake_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["symbol"].required is False
    assert options["input_csv"].required is True
    assert options["output_csv"].required is True
    assert options["as_of"].required is True
    assert options["run_id"].required is True
    assert options["run_log"].required is True


def test_intake_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(
    input_csv: Path,
    *,
    output_csv: Path,
    **overrides: object,
) -> LocalDailyBarsIntakeConfig:
    values = {
        "run_id": "unit_m400_local_daily_bars_intake",
        "symbol": "SPY",
        "input_csv": input_csv,
        "output_csv": output_csv,
        "as_of": AS_OF,
    }
    values.update(overrides)
    return LocalDailyBarsIntakeConfig(**values)


def _write_daily_bars_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)]
    lines.extend(
        ",".join(row[column] for column in LOCAL_DAILY_BARS_CSV_COLUMNS)
        for row in rows
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _daily_rows(count: int) -> list[dict[str, str]]:
    first_day = AS_OF_DATE - timedelta(days=count - 1)
    return [
        _row("SPY", (first_day + timedelta(days=index)).isoformat(), 100 + index)
        for index in range(count)
    ]


def _row(symbol: str, day: str, price: int) -> dict[str, str]:
    parsed = date.fromisoformat(day)
    assert parsed.isoformat() == day
    return {
        "symbol": symbol,
        "date": day,
        "open": str(price),
        "high": str(price + 1),
        "low": str(price - 1),
        "close": str(price),
        "adjusted_close": str(price),
        "volume": "1000",
    }


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


def _read_csv_rows(path: Path) -> list[list[str]]:
    return [
        line.split(",")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _terminal_reconciliation_record() -> dict[str, object]:
    return {
        "run_id": "m391_m376_spy_close_order_reconciliation_retry",
        "symbol": "SPY",
        "client_order_id": "paper-order-close-m376_spy_paper_close_submit",
        "broker_order_id": "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d",
        "expected_side": "sell",
        "expected_qty": "0.033172072",
        "observed_status": "filled",
        "observed_symbol": "SPY",
        "observed_side": "sell",
        "observed_qty": "0.033172072",
        "observed_filled_qty": "0.033172072",
        "observed_remaining_qty": "0E-9",
        "exact_order_found": True,
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
        "non_spy_positions": [],
        "blockers": [],
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


def _assert_safety_booleans_false(payload: dict[str, object]) -> None:
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_actions_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload.get("not_live_authorized") is True
    if "broker_action_flags" in payload:
        assert payload["broker_action_flags"] == {
            "submit": False,
            "cancel": False,
            "replace": False,
            "close": False,
            "liquidate": False,
            "mutation": False,
        }


def _local_daily_bars_intake_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "local-daily-bars-intake" in choices:
            return choices["local-daily-bars-intake"]
    raise AssertionError("local-daily-bars-intake parser not found")


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
