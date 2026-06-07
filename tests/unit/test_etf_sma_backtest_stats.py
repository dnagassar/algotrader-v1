from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.research.etf_sma_backtest_stats import (
    ETF_SMA_BACKTEST_STATS_LABELS,
    ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY,
    EtfSmaBacktestStatsBar,
    EtfSmaBacktestStatsConfig,
    build_etf_sma_backtest_stats,
    build_etf_sma_backtest_stats_from_bars,
    render_etf_sma_backtest_stats_json,
    write_etf_sma_backtest_stats_jsonl,
)
from algotrader.research.local_daily_bars import LOCAL_DAILY_BARS_CSV_COLUMNS


MODULE_PATH = Path("src/algotrader/research/etf_sma_backtest_stats.py")
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
    "openai",
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
    "submit_path_allowed",
    "paper_submit_approved",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "credential_access",
    "credential_access_attempted",
    "broker_network_access",
    "network_access_attempted",
    "broker_action_performed",
    "broker_actions_performed",
    "market_data_fetch_performed",
)


def test_sma50_above_sma200_posture_is_risk_on() -> None:
    payload = _payload_for(150 * ("100",) + 50 * ("200",))

    final_posture = payload["posture_history"][-1]
    assert final_posture["posture"] == "risk_on"
    assert final_posture["short_sma"] == "200"
    assert final_posture["long_sma"] == "125"
    assert payload["final_posture"] == "risk_on"


def test_below_200_usable_bars_is_insufficient_history() -> None:
    payload = _payload_for(199 * ("100",))

    assert payload["backtest_state"] == "blocked_insufficient_history"
    assert payload["performance_evidence_state"] == "insufficient_history"
    assert payload["usable_bar_count"] == 199
    assert payload["insufficient_history_count"] == 199
    assert payload["evaluated_return_count"] == 0
    assert payload["trade_count"] == 0
    assert payload["final_posture"] == "insufficient_history"
    assert payload["final_exposure"] == 0


def test_one_bar_delay_prevents_same_bar_signal_return_capture() -> None:
    exact_200 = _payload_for(150 * ("100",) + 50 * ("200",))
    with_next_return = _payload_for(150 * ("100",) + 50 * ("200",) + ("220",))

    assert exact_200["equity_curve"][-1]["exposure"] == 0
    assert exact_200["ending_equity"] == "25.00"
    assert exact_200["total_return"] == "0"
    assert exact_200["evaluated_return_count"] == 0
    assert exact_200["final_decision"] == "pending_entry_next_bar"

    assert with_next_return["equity_curve"][199]["exposure"] == 0
    assert with_next_return["equity_curve"][200]["exposure"] == 1
    assert with_next_return["equity_curve"][200]["asset_return"] == "0.1"
    assert with_next_return["ending_equity"] == "27.500"
    assert with_next_return["total_return"] == "0.1"


def test_long_only_exposure_transitions_are_clean_buy_sell_or_hold_noop() -> None:
    payload = _payload_for(150 * ("100",) + 50 * ("200",) + 55 * ("50",))

    trade_actions = [
        event["action"]
        for event in payload["events"]
        if event["action"] in ("buy", "sell")
    ]
    exposures = [point["exposure"] for point in payload["equity_curve"]]

    assert trade_actions == ["buy", "sell"]
    assert payload["entry_count"] == 1
    assert payload["exit_count"] == 1
    assert payload["trade_count"] == 2
    assert set(exposures).issubset({0, 1})
    assert {event["action"] for event in payload["events"]}.issubset(
        {"buy", "sell", "hold", "noop"}
    )


def test_deterministic_equity_curve_and_summary_statistics() -> None:
    payload = _payload_for(150 * ("100",) + 50 * ("200",) + ("220",))

    assert payload["backtest_state"] == "completed"
    assert payload["performance_evidence_state"] == "offline_statistics_available"
    assert payload["starting_equity"] == "25.00"
    assert payload["ending_equity"] == "27.500"
    assert payload["total_return"] == "0.1"
    assert payload["max_drawdown"] == "0"
    assert payload["exposure_fraction"] == "1"
    assert payload["evaluated_return_count"] == 1
    assert payload["trade_count"] == 1
    assert payload["entry_count"] == 1
    assert payload["exit_count"] == 0
    assert payload["final_exposure"] == 1
    assert payload["final_posture"] == "risk_on"
    assert payload["final_decision"] == "hold_long"


def test_buy_and_hold_benchmark_math_uses_same_evaluated_return_window() -> None:
    payload = _payload_for(150 * ("100",) + 50 * ("200",) + ("220",))

    assert payload["benchmark"] == "buy_and_hold"
    assert payload["benchmark_start_date"] == payload["strategy_start_date"]
    assert payload["benchmark_end_date"] == payload["strategy_end_date"]
    assert payload["benchmark_start_date"] == payload["equity_curve"][199]["date"]
    assert payload["benchmark_end_date"] == payload["equity_curve"][-1]["date"]
    assert payload["benchmark_equity_curve"] == [
        {
            "date": payload["equity_curve"][-1]["date"],
            "start_date": payload["equity_curve"][199]["date"],
            "close": "220",
            "asset_return": "0.1",
            "equity": "27.500",
            "drawdown": "0",
        }
    ]
    assert payload["benchmark_total_return"] == "0.1"
    assert payload["strategy_total_return"] == "0.1"
    assert payload["excess_return"] == "0.0"


def test_cost_bps_changes_strategy_result_without_changing_benchmark() -> None:
    values = 150 * ("100",) + 50 * ("200",) + ("220",)
    no_cost = _payload_for(values)
    with_cost = _payload_for(values, cost_bps="100")

    assert no_cost["strategy_total_return"] == "0.1"
    assert no_cost["total_cost"] == "0"
    assert with_cost["cost_bps"] == "100"
    assert with_cost["strategy_ending_equity"] == "27.22500"
    assert with_cost["strategy_total_return"] == "0.089"
    assert with_cost["total_cost"] == "0.27500"
    assert with_cost["benchmark_total_return"] == no_cost["benchmark_total_return"]
    assert with_cost["excess_return"] == "-0.011"


def test_strategy_and_benchmark_max_drawdown_are_deterministic() -> None:
    payload = _payload_for(150 * ("100",) + 50 * ("200",) + ("100", "150"))

    assert payload["strategy_max_drawdown"] == "0.5"
    assert payload["benchmark_max_drawdown"] == "0.5"
    assert payload["benchmark_equity_curve"][0]["drawdown"] == "-0.5"
    assert payload["benchmark_equity_curve"][1]["drawdown"] == "-0.25"


def test_exact_200_bar_edge_case_is_valid_but_insufficient_performance_evidence() -> None:
    payload = _payload_for(150 * ("100",) + 50 * ("200",))

    assert payload["usable_bar_count"] == 200
    assert payload["backtest_state"] == "blocked_insufficient_post_signal_returns"
    assert payload["performance_evidence_state"] == "insufficient_post_signal_returns"
    assert payload["blockers"] == ["insufficient_post_signal_returns"]
    assert payload["profit_claim"] == "none"


def test_missing_csv_writes_blocked_valid_offline_artifact(tmp_path) -> None:  # noqa: ANN001
    config = _config(daily_bars_csv=tmp_path / "missing.csv")

    payload = build_etf_sma_backtest_stats(config)

    assert payload["backtest_state"] == "blocked_missing_daily_bars_csv"
    assert payload["performance_evidence_state"] == "missing_daily_bars_csv"
    assert payload["blockers"] == ["missing_daily_bars_csv"]
    assert payload["source_bar_count"] == 0
    assert payload["usable_bar_count"] == 0
    assert payload["network_access_attempted"] is False


def test_missing_required_columns_are_malformed_csv(tmp_path) -> None:  # noqa: ANN001
    csv_path = tmp_path / "missing_columns.csv"
    csv_path.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "SPY,2026-01-01,100,101,99,100,1000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="adjusted_close"):
        build_etf_sma_backtest_stats(_config(daily_bars_csv=csv_path))


def test_duplicate_dates_are_malformed_csv(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_csv(tmp_path / "duplicate.csv", ("100", "101"))
    rows = csv_path.read_text(encoding="utf-8").splitlines()
    rows[2] = rows[1].replace("100", "101")
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="duplicates date"):
        build_etf_sma_backtest_stats(_config(daily_bars_csv=csv_path))


def test_descending_dates_are_malformed_csv(tmp_path) -> None:  # noqa: ANN001
    csv_path = tmp_path / "descending.csv"
    rows = [_csv_row("SPY", date(2026, 1, 2), "101")]
    rows.append(_csv_row("SPY", date(2026, 1, 1), "100"))
    _write_csv_rows(csv_path, rows)

    with pytest.raises(ValidationError, match="ascending date"):
        build_etf_sma_backtest_stats(_config(daily_bars_csv=csv_path))


def test_non_spy_symbol_rows_are_malformed_csv(tmp_path) -> None:  # noqa: ANN001
    csv_path = tmp_path / "qqq.csv"
    _write_csv_rows(csv_path, [_csv_row("QQQ", date(2026, 1, 1), "100")])

    with pytest.raises(ValidationError, match="only SPY"):
        build_etf_sma_backtest_stats(_config(daily_bars_csv=csv_path))


@pytest.mark.parametrize(
    ("field_name", "field_value", "match"),
    (
        ("close", "bad", "close"),
        ("adjusted_close", "0", "adjusted_close"),
    ),
)
def test_invalid_close_or_adjusted_close_values_are_malformed_csv(
    tmp_path,
    field_name: str,
    field_value: str,
    match: str,
) -> None:  # noqa: ANN001
    row = _csv_row("SPY", date(2026, 1, 1), "100")
    row[field_name] = field_value
    csv_path = tmp_path / f"bad_{field_name}.csv"
    _write_csv_rows(csv_path, [row])

    with pytest.raises(ValidationError, match=match):
        build_etf_sma_backtest_stats(_config(daily_bars_csv=csv_path))


def test_non_spy_command_symbol_is_rejected(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError, match="SPY"):
        EtfSmaBacktestStatsConfig(
            run_id="unit",
            symbol="QQQ",
            daily_bars_csv=tmp_path / "bars.csv",
        )


def test_json_rendering_and_jsonl_writes_are_deterministic(tmp_path) -> None:  # noqa: ANN001
    payload = _payload_for(150 * ("100",) + 50 * ("200",) + ("220",))
    output_a = tmp_path / "a.jsonl"
    output_b = tmp_path / "b.jsonl"

    first = render_etf_sma_backtest_stats_json(payload)
    second = render_etf_sma_backtest_stats_json(payload)
    write_etf_sma_backtest_stats_jsonl(payload, output_a)
    write_etf_sma_backtest_stats_jsonl(payload, output_b)

    assert first == second
    assert output_a.read_bytes() == output_b.read_bytes()
    assert json.loads(output_a.read_text(encoding="utf-8")) == json.loads(first)


def test_all_safety_booleans_are_false_and_labels_are_conservative() -> None:
    payload = _payload_for(150 * ("100",) + 50 * ("200",) + ("220",))

    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["profit_claim"] == "none"
    assert payload["labels"] == list(ETF_SMA_BACKTEST_STATS_LABELS)
    assert payload["lookahead_policy"] == ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY
    assert payload["data_basis"] == "raw_close_price_return"
    assert payload["price_field"] == "close"
    assert payload["raw_close_price_return_evidence_only"] is True
    assert payload["fill_model"] == "next_close"
    assert payload["cost_bps"] == "0"
    assert payload["benchmark"] == "buy_and_hold"


def test_research_module_imports_no_broker_sdk_or_network_dependencies() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_cli_smoke_writes_stats_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "spy_daily.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    run_log = tmp_path / "m406.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("offline stats command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            "etf-sma-backtest-stats",
            "--symbol",
            "SPY",
            "--daily-bars-csv",
            str(csv_path),
            "--run-id",
            "unit_m406",
            "--benchmark",
            "buy_and_hold",
            "--fill-model",
            "next_close",
            "--cost-bps",
            "100",
            "--run-log",
            str(run_log),
            "--format",
            "json",
        ]
    ) == 0

    stdout = capsys.readouterr().out
    payload = json.loads(run_log.read_text(encoding="utf-8"))
    assert json.loads(stdout) == payload
    assert payload["record_type"] == "etf_sma_backtest_stats"
    assert payload["run_id"] == "unit_m406"
    assert payload["backtest_state"] == "completed"
    assert payload["fill_model"] == "next_close"
    assert payload["cost_bps"] == "100"
    assert payload["strategy_total_return"] == "0.089"


def _payload_for(
    values: tuple[str, ...],
    *,
    cost_bps: Decimal | str = Decimal("0"),
) -> dict[str, object]:
    return build_etf_sma_backtest_stats_from_bars(
        _bars(values),
        _config(cost_bps=cost_bps),
    )


def _config(
    *,
    daily_bars_csv: Path | str = "unit_spy_daily_bars.csv",
    cost_bps: Decimal | str = Decimal("0"),
) -> EtfSmaBacktestStatsConfig:
    return EtfSmaBacktestStatsConfig(
        run_id="unit_m406",
        symbol="SPY",
        daily_bars_csv=daily_bars_csv,
        starting_equity=Decimal("25.00"),
        cost_bps=cost_bps,
    )


def _bars(values: tuple[str, ...]) -> tuple[EtfSmaBacktestStatsBar, ...]:
    start = date(2026, 1, 1)
    return tuple(
        EtfSmaBacktestStatsBar(
            date=start + timedelta(days=index),
            adjusted_close=Decimal(value),
        )
        for index, value in enumerate(values)
    )


def _write_csv(path: Path, values: tuple[str, ...]) -> Path:
    start = date(2026, 1, 1)
    rows = [
        _csv_row("SPY", start + timedelta(days=index), value)
        for index, value in enumerate(values)
    ]
    return _write_csv_rows(path, rows)


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
    value = Decimal(price)
    high = value + Decimal("1")
    low = value - Decimal("1") if value > Decimal("1") else value
    return {
        "symbol": symbol,
        "date": day.isoformat(),
        "open": price,
        "high": str(high),
        "low": str(low),
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
