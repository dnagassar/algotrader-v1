from __future__ import annotations

import ast
from datetime import date, timedelta
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_local_bars_backtest_refresh import (
    ETF_SMA_LOCAL_BARS_BACKTEST_REFRESH_LABELS,
    EtfSmaLocalBarsBacktestRefreshConfig,
    build_etf_sma_local_bars_backtest_refresh,
    render_etf_sma_local_bars_backtest_refresh_json,
    write_etf_sma_local_bars_backtest_refresh_jsonl,
)
from algotrader.research.local_daily_bars import LOCAL_DAILY_BARS_CSV_COLUMNS


MODULE_PATH = Path("src/algotrader/research/etf_sma_local_bars_backtest_refresh.py")
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "http",
    "httpx",
    "requests",
    "socket",
    "urllib",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "download",
    "getenv",
    "liquidate",
    "os.getenv",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "submit_authorized",
    "paper_submit_approved",
    "broker_mutation_authorized",
    "live_authorized",
    "credential_access_attempted",
    "network_access_attempted",
    "broker_action_performed",
    "broker_actions_performed",
    "market_data_fetch_performed",
)


def test_clean_201_plus_local_csv_refreshes_post_signal_evidence(tmp_path) -> None:  # noqa: ANN001
    payload = _payload_for(tmp_path, 150 * ("100",) + 50 * ("200",) + ("220",))

    assert payload["record_type"] == "etf_sma_local_bars_backtest_refresh"
    assert payload["refresh_state"] == "backtest_evidence_refreshed"
    assert payload["backtest_state"] == "completed"
    assert payload["performance_evidence_state"] == "post_signal_returns_evaluated"
    assert payload["usable_bar_count"] == 201
    assert payload["minimum_usable_bars_for_post_signal_evidence"] == 201
    assert payload["evaluated_return_count"] == 1
    assert payload["ending_equity"] == "27.500"
    assert payload["total_return"] == "0.1"
    assert payload["profit_claim"] == "none"


def test_exactly_200_usable_bars_blocks_as_insufficient_extended_bars(tmp_path) -> None:  # noqa: ANN001
    payload = _payload_for(tmp_path, 150 * ("100",) + 50 * ("200",))

    assert payload["refresh_state"] == "blocked_insufficient_extended_daily_bars"
    assert payload["backtest_state"] == "blocked_insufficient_post_signal_returns"
    assert payload["performance_evidence_state"] == "insufficient_post_signal_returns"
    assert payload["usable_bar_count"] == 200
    assert payload["evaluated_return_count"] == 0
    assert payload["blockers"] == [
        "blocked_insufficient_extended_daily_bars",
        "insufficient_post_signal_returns",
    ]


def test_fewer_than_200_usable_bars_blocks_as_insufficient_history(tmp_path) -> None:  # noqa: ANN001
    payload = _payload_for(tmp_path, 199 * ("100",))

    assert payload["refresh_state"] == "blocked_insufficient_extended_daily_bars"
    assert payload["backtest_state"] == "blocked_insufficient_history"
    assert payload["performance_evidence_state"] == "insufficient_history"
    assert payload["usable_bar_count"] == 199
    assert payload["evaluated_return_count"] == 0
    assert "insufficient_history" in payload["blockers"]


def test_no_lookahead_policy_preserves_one_bar_signal_delay(tmp_path) -> None:  # noqa: ANN001
    exact_200 = _payload_for(tmp_path, 150 * ("100",) + 50 * ("200",))
    with_next_return = _payload_for(
        tmp_path,
        150 * ("100",) + 50 * ("200",) + ("220",),
    )

    assert exact_200["equity_curve"][-1]["exposure"] == 0
    assert exact_200["ending_equity"] == "25.00"
    assert exact_200["evaluated_return_count"] == 0
    assert exact_200["final_decision"] == "pending_entry_next_bar"

    assert with_next_return["equity_curve"][199]["exposure"] == 0
    assert with_next_return["equity_curve"][200]["exposure"] == 1
    assert with_next_return["equity_curve"][200]["asset_return"] == "0.1"
    assert with_next_return["evaluated_return_count"] == 1
    assert with_next_return["ending_equity"] == "27.500"


@pytest.mark.parametrize(
    "case_name",
    (
        "missing_date",
        "missing_close",
        "missing_adjusted_close",
        "duplicate_dates",
        "descending_dates",
        "invalid_close",
        "non_spy_symbol",
    ),
)
def test_malformed_candidate_csv_blocks_with_valid_artifact(
    tmp_path,
    case_name: str,
) -> None:  # noqa: ANN001
    source_log = _write_source_log(tmp_path / "m406.jsonl")
    csv_path = _write_malformed_csv(tmp_path / f"{case_name}.csv", case_name)

    payload = build_etf_sma_local_bars_backtest_refresh(
        _config(
            source_backtest_log=source_log,
            candidate_daily_bars_csv=csv_path,
        )
    )

    assert payload["refresh_state"] == "blocked_malformed_candidate_daily_bars_csv"
    assert payload["backtest_state"] == "blocked_malformed_candidate_daily_bars_csv"
    assert payload["performance_evidence_state"] == "malformed_candidate_daily_bars_csv"
    assert payload["evaluated_return_count"] == 0
    assert payload["submitted"] is False
    assert payload["network_access_attempted"] is False


@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_blocker"),
    (
        ("submitted", True, "source_backtest_log_submitted_not_false"),
        ("mutated", True, "source_backtest_log_mutated_not_false"),
        ("live_authorized", True, "source_backtest_log_live_authorized_not_false"),
        (
            "network_access_attempted",
            True,
            "source_backtest_log_network_access_attempted_not_false",
        ),
        (
            "credential_access_attempted",
            True,
            "source_backtest_log_credential_access_attempted_not_false",
        ),
        ("symbol", "QQQ", "source_backtest_log_symbol_invalid"),
        ("profit_claim", "profit", "source_backtest_log_profit_claim_not_none"),
    ),
)
def test_invalid_source_m406_log_blocks(
    tmp_path,
    field_name: str,
    field_value: object,
    expected_blocker: str,
) -> None:  # noqa: ANN001
    source_record = _source_record()
    source_record[field_name] = field_value
    source_log = _write_source_log(tmp_path / "m406.jsonl", source_record)
    csv_path = _write_csv(
        tmp_path / "spy_daily.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )

    payload = build_etf_sma_local_bars_backtest_refresh(
        _config(
            source_backtest_log=source_log,
            candidate_daily_bars_csv=csv_path,
        )
    )

    assert payload["refresh_state"] == "blocked_invalid_source_backtest_log"
    assert payload["backtest_state"] == "blocked_invalid_source_backtest_log"
    assert payload["performance_evidence_state"] == "invalid_source_backtest_log"
    assert expected_blocker in payload["blockers"]
    assert payload["evaluated_return_count"] == 0
    assert payload["submitted"] is False


def test_json_rendering_dict_and_jsonl_writes_are_deterministic(tmp_path) -> None:  # noqa: ANN001
    config = _config(
        source_backtest_log=_write_source_log(tmp_path / "m406.jsonl"),
        candidate_daily_bars_csv=_write_csv(
            tmp_path / "spy_daily.csv",
            150 * ("100",) + 50 * ("200",) + ("220",),
        ),
    )
    payload_a = build_etf_sma_local_bars_backtest_refresh(config)
    payload_b = build_etf_sma_local_bars_backtest_refresh(config)
    output_a = tmp_path / "a.jsonl"
    output_b = tmp_path / "b.jsonl"

    first = render_etf_sma_local_bars_backtest_refresh_json(payload_a)
    second = render_etf_sma_local_bars_backtest_refresh_json(payload_b)
    write_etf_sma_local_bars_backtest_refresh_jsonl(payload_a, output_a)
    write_etf_sma_local_bars_backtest_refresh_jsonl(payload_b, output_b)

    assert payload_a == payload_b
    assert first == second
    assert output_a.read_bytes() == output_b.read_bytes()
    assert json.loads(output_a.read_text(encoding="utf-8")) == json.loads(first)


def test_all_safety_booleans_are_false_and_labels_are_conservative(tmp_path) -> None:  # noqa: ANN001
    payload = _payload_for(tmp_path, 150 * ("100",) + 50 * ("200",) + ("220",))

    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["profit_claim"] == "none"
    assert payload["labels"] == list(ETF_SMA_LOCAL_BARS_BACKTEST_REFRESH_LABELS)


def test_synthetic_unit_fixture_is_not_marked_as_operator_evidence(tmp_path) -> None:  # noqa: ANN001
    payload = _payload_for(tmp_path, 150 * ("100",) + 50 * ("200",) + ("220",))

    assert payload["data_provenance"]["local_csv_only"] is True
    assert payload["data_provenance"]["operator_evidence_synthetic"] is False
    assert payload["data_provenance"]["network_access_attempted"] is False
    assert payload["data_provenance"]["credential_access_attempted"] is False


def test_m407_research_module_imports_no_broker_sdk_or_network_dependencies() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_cli_smoke_writes_refresh_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "spy_daily.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    source_log = _write_source_log(tmp_path / "m406.jsonl")
    run_log = tmp_path / "m407.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("offline refresh command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            "etf-sma-local-bars-backtest-refresh",
            "--symbol",
            "SPY",
            "--candidate-daily-bars-csv",
            str(csv_path),
            "--source-backtest-log",
            str(source_log),
            "--run-id",
            "unit_m407",
            "--run-log",
            str(run_log),
            "--format",
            "json",
        ]
    ) == 0

    stdout = capsys.readouterr().out
    payload = json.loads(run_log.read_text(encoding="utf-8"))
    assert json.loads(stdout) == payload
    assert payload["record_type"] == "etf_sma_local_bars_backtest_refresh"
    assert payload["run_id"] == "unit_m407"
    assert payload["refresh_state"] == "backtest_evidence_refreshed"


def _payload_for(tmp_path, values: tuple[str, ...]) -> dict[str, object]:  # noqa: ANN001
    return build_etf_sma_local_bars_backtest_refresh(
        _config(
            source_backtest_log=_write_source_log(tmp_path / "m406.jsonl"),
            candidate_daily_bars_csv=_write_csv(tmp_path / "spy_daily.csv", values),
        )
    )


def _config(
    *,
    source_backtest_log: Path,
    candidate_daily_bars_csv: Path,
) -> EtfSmaLocalBarsBacktestRefreshConfig:
    return EtfSmaLocalBarsBacktestRefreshConfig(
        run_id="unit_m407",
        symbol="SPY",
        source_backtest_log=source_backtest_log,
        candidate_daily_bars_csv=candidate_daily_bars_csv,
    )


def _source_record() -> dict[str, object]:
    record: dict[str, object] = {
        "record_type": "etf_sma_backtest_stats",
        "command": "etf-sma-backtest-stats",
        "run_id": "unit_m406",
        "symbol": "SPY",
        "profit_claim": "none",
        "starting_equity": "25.00",
    }
    for field_name in (
        "submitted",
        "mutated",
        "submit_authorized",
        "paper_submit_approved",
        "broker_mutation_authorized",
        "live_authorized",
        "credential_access_attempted",
        "network_access_attempted",
    ):
        record[field_name] = False
    return record


def _write_source_log(path: Path, record: dict[str, object] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record or _source_record(), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _write_csv(path: Path, values: tuple[str, ...]) -> Path:
    start = date(2026, 1, 1)
    rows = [
        _csv_row("SPY", start + timedelta(days=index), value)
        for index, value in enumerate(values)
    ]
    return _write_csv_rows(path, rows)


def _write_malformed_csv(path: Path, case_name: str) -> Path:
    if case_name == "missing_date":
        return _write_csv_with_columns(path, ("symbol", "close", "adjusted_close"))
    if case_name == "missing_close":
        columns = tuple(
            column for column in LOCAL_DAILY_BARS_CSV_COLUMNS if column != "close"
        )
        return _write_csv_with_columns(path, columns)
    if case_name == "missing_adjusted_close":
        columns = tuple(
            column
            for column in LOCAL_DAILY_BARS_CSV_COLUMNS
            if column != "adjusted_close"
        )
        return _write_csv_with_columns(path, columns)
    if case_name == "duplicate_dates":
        day = date(2026, 1, 1)
        return _write_csv_rows(path, [_csv_row("SPY", day, "100"), _csv_row("SPY", day, "101")])
    if case_name == "descending_dates":
        return _write_csv_rows(
            path,
            [
                _csv_row("SPY", date(2026, 1, 2), "101"),
                _csv_row("SPY", date(2026, 1, 1), "100"),
            ],
        )
    if case_name == "invalid_close":
        row = _csv_row("SPY", date(2026, 1, 1), "100")
        row["close"] = "bad"
        return _write_csv_rows(path, [row])
    if case_name == "non_spy_symbol":
        return _write_csv_rows(path, [_csv_row("QQQ", date(2026, 1, 1), "100")])
    raise AssertionError(f"Unhandled malformed CSV case: {case_name}")


def _write_csv_with_columns(path: Path, columns: tuple[str, ...]) -> Path:
    row = _csv_row("SPY", date(2026, 1, 1), "100")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        ",".join(columns) + "\n" + ",".join(row[column] for column in columns) + "\n",
        encoding="utf-8",
    )
    return path


def _write_csv_rows(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)]
    lines.extend(
        ",".join(row[column] for column in LOCAL_DAILY_BARS_CSV_COLUMNS)
        for row in rows
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _csv_row(symbol: str, day: date, price: str) -> dict[str, str]:
    value = int(price)
    high = str(value + 1)
    low = str(value - 1 if value > 1 else value)
    return {
        "symbol": symbol,
        "date": day.isoformat(),
        "open": price,
        "high": high,
        "low": low,
        "close": price,
        "adjusted_close": price,
        "volume": "1000",
    }


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
