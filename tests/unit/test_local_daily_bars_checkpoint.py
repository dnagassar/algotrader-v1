from __future__ import annotations

import ast
from datetime import date, timedelta
import json
from pathlib import Path
import socket

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import LOCAL_DAILY_BARS_CSV_COLUMNS
from algotrader.research.local_daily_bars_checkpoint import (
    LOCAL_DAILY_BARS_CHECKPOINT_LABELS,
    LocalDailyBarsCheckpointConfig,
    build_local_daily_bars_checkpoint,
    render_local_daily_bars_checkpoint_json,
    write_local_daily_bars_checkpoint_jsonl,
)


MODULE_PATH = Path("src/algotrader/research/local_daily_bars_checkpoint.py")
AS_OF = "2026-06-05"
AS_OF_DATE = date.fromisoformat(AS_OF)
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


def test_valid_199_bar_csv_writes_insufficient_history_checkpoint(
    tmp_path,
) -> None:  # noqa: ANN001
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_199_daily_bars.csv",
        _daily_rows(199),
    )
    run_log = tmp_path / "m399_199.jsonl"

    payload = build_local_daily_bars_checkpoint(_config(daily_bars_csv))
    result = write_local_daily_bars_checkpoint_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["record_type"] == "local_daily_bars_checkpoint"
    assert payload["command"] == "local-daily-bars-checkpoint"
    assert payload["run_id"] == "unit_m399_local_daily_bars_checkpoint"
    assert payload["symbol"] == "SPY"
    assert payload["as_of"] == AS_OF
    assert payload["daily_bars_csv"] == str(daily_bars_csv)
    assert payload["csv_schema"] == list(LOCAL_DAILY_BARS_CSV_COLUMNS)
    assert payload["required_columns"] == list(LOCAL_DAILY_BARS_CSV_COLUMNS)
    assert payload["observed_columns"] == list(LOCAL_DAILY_BARS_CSV_COLUMNS)
    assert payload["labels"] == list(LOCAL_DAILY_BARS_CHECKPOINT_LABELS)
    assert payload["row_count_for_symbol"] == 199
    assert payload["usable_bar_count"] == 199
    assert payload["first_bar_date"] == "2025-11-19"
    assert payload["last_bar_date"] == AS_OF
    assert payload["future_bar_count_excluded"] == 0
    assert payload["duplicate_date_count"] == 0
    assert payload["required_usable_bars"] == 200
    assert payload["missing_usable_bars"] == 1
    assert payload["readiness_state"] == "insufficient_history"
    assert payload["readiness_reason"] == "sma_insufficient_history"
    assert payload["blockers"] == ["missing_usable_bars"]
    _assert_safety_booleans_false(payload)


def test_valid_200_bar_csv_writes_ready_checkpoint(tmp_path) -> None:  # noqa: ANN001
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_200_daily_bars.csv",
        _daily_rows(200),
    )
    run_log = tmp_path / "m399_200.jsonl"

    payload = build_local_daily_bars_checkpoint(_config(daily_bars_csv))
    result = write_local_daily_bars_checkpoint_jsonl(payload, run_log)

    assert result.record_count == 1
    assert _read_jsonl(run_log) == [payload]
    assert payload["row_count_for_symbol"] == 200
    assert payload["usable_bar_count"] == 200
    assert payload["first_bar_date"] == "2025-11-18"
    assert payload["last_bar_date"] == AS_OF
    assert payload["required_usable_bars"] == 200
    assert payload["missing_usable_bars"] == 0
    assert payload["readiness_state"] == "ready"
    assert payload["readiness_reason"] == "sma_usable_bars_ready"
    assert payload["blockers"] == []
    _assert_safety_booleans_false(payload)


def test_future_dated_requested_symbol_bars_are_excluded_and_counted(
    tmp_path,
) -> None:  # noqa: ANN001
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_199_plus_future_daily_bars.csv",
        [
            *_daily_rows(199),
            _row("SPY", "2026-06-06", 300),
        ],
    )

    payload = build_local_daily_bars_checkpoint(_config(daily_bars_csv))

    assert payload["row_count_for_symbol"] == 200
    assert payload["usable_bar_count"] == 199
    assert payload["future_bar_count_excluded"] == 1
    assert payload["last_bar_date"] == AS_OF
    assert payload["missing_usable_bars"] == 1
    assert payload["readiness_state"] == "insufficient_history"
    _assert_safety_booleans_false(payload)


def test_wrong_symbol_rows_are_ignored(tmp_path) -> None:  # noqa: ANN001
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "mixed_symbol_daily_bars.csv",
        [
            _row("QQQ", "2026-06-04", 400),
            *_daily_rows(200),
            _row("IWM", "2026-06-05", 500),
        ],
    )

    payload = build_local_daily_bars_checkpoint(_config(daily_bars_csv))

    assert payload["total_row_count"] == 202
    assert payload["row_count_for_symbol"] == 200
    assert payload["wrong_symbol_row_count_ignored"] == 2
    assert payload["usable_bar_count"] == 200
    assert payload["readiness_state"] == "ready"
    _assert_safety_booleans_false(payload)


def test_duplicate_requested_symbol_dates_fail_closed(tmp_path) -> None:  # noqa: ANN001
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "duplicate_spy_daily_bars.csv",
        [
            _row("SPY", "2026-06-04", 100),
            _row("SPY", "2026-06-04", 101),
        ],
    )

    with pytest.raises(ValidationError, match="duplicates date 2026-06-04"):
        build_local_daily_bars_checkpoint(_config(daily_bars_csv))


def test_missing_required_columns_fail_closed(tmp_path) -> None:  # noqa: ANN001
    daily_bars_csv = tmp_path / "missing_columns.csv"
    daily_bars_csv.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "SPY,2026-06-04,100,101,99,100,1000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="adjusted_close"):
        build_local_daily_bars_checkpoint(_config(daily_bars_csv))


@pytest.mark.parametrize(
    ("column", "value", "match"),
    (
        ("close", "0", "greater than zero"),
        ("volume", "-1", "zero or greater"),
    ),
)
def test_invalid_price_or_volume_values_fail_closed(
    tmp_path,
    column: str,
    value: str,
    match: str,
) -> None:  # noqa: ANN001
    row = _row("SPY", "2026-06-04", 100)
    row[column] = value
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / f"invalid_{column}_daily_bars.csv",
        [row],
    )

    with pytest.raises(ValidationError, match=match):
        build_local_daily_bars_checkpoint(_config(daily_bars_csv))


def test_missing_csv_path_fails_closed(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError, match="existing local CSV"):
        build_local_daily_bars_checkpoint(
            _config(tmp_path / "missing_spy_daily_bars.csv")
        )


def test_same_input_and_as_of_produce_deterministic_json(tmp_path) -> None:  # noqa: ANN001
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_200_daily_bars.csv",
        _daily_rows(200),
    )

    first = build_local_daily_bars_checkpoint(_config(daily_bars_csv))
    second = build_local_daily_bars_checkpoint(_config(daily_bars_csv))

    assert first == second
    assert render_local_daily_bars_checkpoint_json(first) == (
        render_local_daily_bars_checkpoint_json(second)
    )


def test_cli_local_daily_bars_checkpoint_smoke_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("local daily-bars checkpoint must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("local daily-bars checkpoint must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("local daily-bars checkpoint must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_200_daily_bars.csv",
        _daily_rows(200),
    )
    run_log = tmp_path / "m399_checkpoint.jsonl"

    exit_code = cli_module.main(
        (
            "local-daily-bars-checkpoint",
            "--symbol",
            "SPY",
            "--daily-bars-csv",
            str(daily_bars_csv),
            "--as-of",
            AS_OF,
            "--run-id",
            "unit_m399_local_daily_bars_checkpoint",
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
    assert payload["record_type"] == "local_daily_bars_checkpoint"
    assert payload["readiness_state"] == "ready"
    assert payload["usable_bar_count"] == 200
    _assert_safety_booleans_false(payload)


def test_local_daily_bars_checkpoint_parser_registration() -> None:
    parser = _local_daily_bars_checkpoint_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["symbol"].required is False
    assert options["daily_bars_csv"].required is True
    assert options["as_of"].required is True
    assert options["run_id"].required is True
    assert options["run_log"].required is True


def test_checkpoint_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(
    daily_bars_csv: Path,
    **overrides: object,
) -> LocalDailyBarsCheckpointConfig:
    values = {
        "run_id": "unit_m399_local_daily_bars_checkpoint",
        "symbol": "SPY",
        "daily_bars_csv": daily_bars_csv,
        "as_of": AS_OF,
    }
    values.update(overrides)
    return LocalDailyBarsCheckpointConfig(**values)


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
    assert payload["not_live_authorized"] is True
    assert payload["broker_action_flags"] == {
        "submit": False,
        "cancel": False,
        "replace": False,
        "close": False,
        "liquidate": False,
        "mutation": False,
    }


def _local_daily_bars_checkpoint_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "local-daily-bars-checkpoint" in choices:
            return choices["local-daily-bars-checkpoint"]
    raise AssertionError("local-daily-bars-checkpoint parser not found")


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
