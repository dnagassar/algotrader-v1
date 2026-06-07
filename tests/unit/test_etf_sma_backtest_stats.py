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
_OPERATOR_DAILY_BARS_CSV = Path("runs/paper_lab/m411_spy_strict_local_daily_bars.csv")
_ANTIGRAVITY_SLICE_CONTRACT = {
    "stress_2022": (
        "2022-03-21",
        "2022-12-30",
        197,
        Decimal("0"),
        Decimal("-0.1394270798172776"),
        Decimal("0"),
        Decimal("0.2274726465171704"),
        0,
        [],
    ),
    "recovery_2023": (
        "2022-12-30",
        "2023-12-29",
        250,
        Decimal("0.1403197586256538"),
        Decimal("0.2428679758387156"),
        Decimal("0.102907446645842"),
        Decimal("0.102907446645842"),
        1,
        ["2023-02-03"],
    ),
    "bull_2024": (
        "2023-12-29",
        "2024-12-31",
        252,
        Decimal("0.2330479055774126"),
        Decimal("0.2330479055774126"),
        Decimal("0.0840562263215664"),
        Decimal("0.0840562263215664"),
        0,
        [],
    ),
    "whipsaw_2025": (
        "2024-12-31",
        "2025-12-31",
        250,
        Decimal("0.0153894835597699"),
        Decimal("0.1635271635271635"),
        Decimal("0.1899890688985692"),
        Decimal("0.1899890688985692"),
        2,
        ["2025-04-15", "2025-07-02"],
    ),
    "ytd_2026": (
        "2025-12-31",
        "2026-06-05",
        106,
        Decimal("0.0815784842796809"),
        Decimal("0.0815784842796809"),
        Decimal("0.0913312916073560"),
        Decimal("0.0913312916073560"),
        0,
        [],
    ),
}


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


def test_default_regime_slices_are_deterministic_and_evaluated_window_bound() -> None:
    values = 150 * ("100",) + 1830 * ("200",)
    payload = _regime_payload_for(values, start=date(2021, 1, 1))
    rendered = render_etf_sma_backtest_stats_json(payload)

    assert render_etf_sma_backtest_stats_json(
        _regime_payload_for(values, start=date(2021, 1, 1))
    ) == rendered
    assert payload["record_type"] == "etf_sma_regime_slice_evidence"
    assert payload["schema_version"] == "1"
    assert payload["milestone"] == "M417"
    assert payload["verdict_scope"] == "raw_close_regime_risk_profile_only"
    assert payload["regime_slice_count"] == 6
    assert payload["omitted_regime_slices"] == []

    slices = payload["regime_slices"]
    assert [item["slice_name"] for item in slices] == [
        "full_evaluated_window",
        "stress_2022",
        "recovery_2023",
        "bull_2024",
        "whipsaw_2025",
        "ytd_2026",
    ]
    full_slice = _slice(payload, "full_evaluated_window")
    assert full_slice["slice_start_date"] == payload["evaluated_start_date"]
    assert full_slice["slice_end_date"] == payload["evaluated_end_date"]

    evaluated_start = date.fromisoformat(str(payload["evaluated_start_date"]))
    evaluated_end = date.fromisoformat(str(payload["evaluated_end_date"]))
    for item in slices:
        slice_start = date.fromisoformat(str(item["slice_start_date"]))
        slice_end = date.fromisoformat(str(item["slice_end_date"]))
        assert evaluated_start <= slice_start <= slice_end <= evaluated_end
        assert item["strategy_start_date"] == item["benchmark_start_date"]
        assert item["strategy_end_date"] == item["benchmark_end_date"]


def test_regime_slices_use_prior_close_boundary_for_calendar_year_starts() -> None:
    dates = [date(2022, 6, 14) + timedelta(days=index) for index in range(200)]
    dates.extend((date(2023, 1, 3), date(2023, 1, 4)))
    payload = build_etf_sma_backtest_stats_from_bars(
        _bars_from_dates(150 * ("100",) + 50 * ("200",) + ("200", "220"), dates),
        _config(cost_bps="1", regime_slices="default"),
    )

    recovery_2023 = _slice(payload, "recovery_2023")

    assert recovery_2023["slice_start_date"] == "2022-12-30"
    assert recovery_2023["slice_end_date"] == "2023-01-04"
    assert recovery_2023["evaluated_return_count"] == 2


def test_regime_slice_rebase_uses_boundary_exposure_without_extra_cost() -> None:
    dates = [date(2025, 1, 1) + timedelta(days=index) for index in range(199)]
    dates.extend(
        (
            date(2025, 12, 29),
            date(2025, 12, 30),
            date(2025, 12, 31),
            date(2026, 1, 2),
        )
    )
    payload = build_etf_sma_backtest_stats_from_bars(
        _bars_from_dates(
            150 * ("100",) + 50 * ("200",) + ("200", "210", "220"),
            dates,
        ),
        _config(cost_bps="100", regime_slices="default"),
    )

    ytd_2026 = _slice(payload, "ytd_2026")

    assert ytd_2026["slice_start_date"] == "2025-12-31"
    assert ytd_2026["trade_count"] == 0
    assert ytd_2026["transition_event_dates"] == []
    assert ytd_2026["strategy_total_return"] == ytd_2026["benchmark_total_return"]


def test_operator_m417_regime_slices_match_antigravity_verifier_contract() -> None:
    if not _OPERATOR_DAILY_BARS_CSV.exists():
        pytest.skip("operator SPY local bars CSV is not present in this workspace")
    payload = build_etf_sma_backtest_stats(
        _config(
            daily_bars_csv=_OPERATOR_DAILY_BARS_CSV,
            cost_bps="1",
            regime_slices="default",
        )
    )

    assert payload["record_type"] == "etf_sma_regime_slice_evidence"
    assert payload["evaluated_return_count"] == 1055
    assert payload["evaluated_start_date"] == "2022-03-21"
    assert payload["evaluated_end_date"] == "2026-06-05"
    assert payload["data_basis"] == "raw_close_price_return"
    assert payload["fill_model"] == "next_close"
    assert payload["cost_bps"] == "1"
    assert payload["benchmark"] == "buy_and_hold"
    assert payload["profit_claim"] == "none"
    for field_name in (
        "submitted",
        "mutated",
        "broker_action_performed",
        "network_access_attempted",
        "credential_access_attempted",
    ):
        assert payload[field_name] is False

    slices = {item["slice_name"]: item for item in payload["regime_slices"]}
    assert set(_ANTIGRAVITY_SLICE_CONTRACT).issubset(slices)
    assert (
        sum(
            int(slices[name]["evaluated_return_count"])
            for name in _ANTIGRAVITY_SLICE_CONTRACT
        )
        == 1055
    )

    for name, expected in _ANTIGRAVITY_SLICE_CONTRACT.items():
        (
            start_date,
            end_date,
            return_count,
            strategy_return,
            benchmark_return,
            strategy_drawdown,
            benchmark_drawdown,
            trade_count,
            transition_dates,
        ) = expected
        item = slices[name]
        assert item["slice_start_date"] == start_date
        assert item["slice_end_date"] == end_date
        assert item["strategy_starting_equity"] == "25.00"
        assert item["benchmark_starting_equity"] == "25.00"
        assert item["evaluated_return_count"] == return_count
        assert item["trade_count"] == trade_count
        assert item["transition_event_dates"] == transition_dates
        _assert_decimal_close(item["strategy_total_return"], strategy_return)
        _assert_decimal_close(item["benchmark_total_return"], benchmark_return)
        _assert_decimal_close(item["strategy_max_drawdown"], strategy_drawdown)
        _assert_decimal_close(item["benchmark_max_drawdown"], benchmark_drawdown)


def test_regime_slice_metrics_normalize_starting_equity_consistently() -> None:
    payload = _regime_payload_for(
        150 * ("100",) + 50 * ("200",) + ("220",),
        start=date(2026, 1, 1),
    )

    full_slice = _slice(payload, "full_evaluated_window")

    assert full_slice["strategy_starting_equity"] == payload["starting_equity"]
    assert full_slice["benchmark_starting_equity"] == payload["starting_equity"]
    assert full_slice["strategy_ending_equity"] == payload["strategy_ending_equity"]
    assert full_slice["benchmark_ending_equity"] == payload["benchmark_ending_equity"]
    assert full_slice["strategy_total_return"] == payload["strategy_total_return"]
    assert full_slice["benchmark_total_return"] == payload["benchmark_total_return"]
    assert full_slice["evaluated_return_count"] == payload["evaluated_return_count"]


def test_regime_slice_max_drawdown_uses_sliced_equity_path_not_endpoints() -> None:
    payload = _regime_payload_for(
        150 * ("100",) + 50 * ("200",) + ("100", "150"),
        start=date(2026, 1, 1),
    )

    full_slice = _slice(payload, "full_evaluated_window")

    assert full_slice["strategy_starting_equity"] == "25.00"
    assert full_slice["strategy_ending_equity"] == "18.7500"
    assert full_slice["strategy_total_return"] == "-0.25"
    assert full_slice["strategy_max_drawdown"] == "0.5"
    assert full_slice["benchmark_max_drawdown"] == "0.5"
    assert full_slice["drawdown_delta"] == "0.0"


def test_regime_slice_event_counts_only_selected_transition_dates() -> None:
    payload = _regime_payload_for(
        150 * ("100",) + 50 * ("200",) + 80 * ("50",),
        start=date(2025, 6, 1),
    )

    whipsaw_2025 = _slice(payload, "whipsaw_2025")
    ytd_2026 = _slice(payload, "ytd_2026")

    assert whipsaw_2025["entry_count"] == 1
    assert whipsaw_2025["exit_count"] == 0
    assert whipsaw_2025["trade_count"] == 1
    assert all(
        str(event_date).startswith("2025")
        for event_date in whipsaw_2025["transition_event_dates"]
    )
    assert ytd_2026["entry_count"] == 0
    assert ytd_2026["exit_count"] == 1
    assert ytd_2026["trade_count"] == 1
    assert all(
        str(event_date).startswith("2026")
        for event_date in ytd_2026["transition_event_dates"]
    )


def test_regime_slice_artifact_preserves_raw_basis_profit_claim_and_safety() -> None:
    payload = _regime_payload_for(
        150 * ("100",) + 1830 * ("200",),
        start=date(2021, 1, 1),
        cost_bps="1",
    )

    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["data_basis"] == "raw_close_price_return"
    assert payload["profit_claim"] == "none"
    assert payload["labels"] == list(ETF_SMA_BACKTEST_STATS_LABELS)
    assert payload["source_input_command_fields"]["regime_slices"] == "default"

    for item in payload["regime_slices"]:
        assert item["data_basis"] == "raw_close_price_return"
        assert item["fill_model"] == "next_close"
        assert item["lookahead_policy"] == ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY
        assert item["cost_bps"] == "1"
        assert item["benchmark"] == "buy_and_hold"
        assert item["profit_claim"] == "none"
        assert item["verdict_scope"] == "raw_close_regime_risk_profile_only"


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


def test_cli_smoke_writes_regime_slice_evidence_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "spy_daily.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    run_log = tmp_path / "m417.jsonl"

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
            "unit_m417",
            "--benchmark",
            "buy_and_hold",
            "--fill-model",
            "next_close",
            "--cost-bps",
            "1",
            "--regime-slices",
            "default",
            "--run-log",
            str(run_log),
            "--format",
            "json",
        ]
    ) == 0

    stdout = capsys.readouterr().out
    payload = json.loads(run_log.read_text(encoding="utf-8"))
    assert json.loads(stdout) == payload
    assert payload["record_type"] == "etf_sma_regime_slice_evidence"
    assert payload["run_id"] == "unit_m417"
    assert payload["milestone"] == "M417"
    assert payload["regime_slice_count"] == 2
    assert [item["slice_name"] for item in payload["regime_slices"]] == [
        "full_evaluated_window",
        "ytd_2026",
    ]


def _payload_for(
    values: tuple[str, ...],
    *,
    cost_bps: Decimal | str = Decimal("0"),
) -> dict[str, object]:
    return build_etf_sma_backtest_stats_from_bars(
        _bars(values),
        _config(cost_bps=cost_bps),
    )


def _regime_payload_for(
    values: tuple[str, ...],
    *,
    start: date,
    cost_bps: Decimal | str = Decimal("0"),
) -> dict[str, object]:
    return build_etf_sma_backtest_stats_from_bars(
        _bars_from(start, values),
        _config(cost_bps=cost_bps, regime_slices="default"),
    )


def _config(
    *,
    daily_bars_csv: Path | str = "unit_spy_daily_bars.csv",
    cost_bps: Decimal | str = Decimal("0"),
    regime_slices: str | None = None,
) -> EtfSmaBacktestStatsConfig:
    return EtfSmaBacktestStatsConfig(
        run_id="unit_m406",
        symbol="SPY",
        daily_bars_csv=daily_bars_csv,
        starting_equity=Decimal("25.00"),
        cost_bps=cost_bps,
        regime_slices=regime_slices,
    )


def _bars(values: tuple[str, ...]) -> tuple[EtfSmaBacktestStatsBar, ...]:
    return _bars_from(date(2026, 1, 1), values)


def _bars_from(
    start: date,
    values: tuple[str, ...],
) -> tuple[EtfSmaBacktestStatsBar, ...]:
    return _bars_from_dates(
        values,
        tuple(start + timedelta(days=index) for index in range(len(values))),
    )


def _bars_from_dates(
    values: tuple[str, ...],
    dates: tuple[date, ...] | list[date],
) -> tuple[EtfSmaBacktestStatsBar, ...]:
    assert len(values) == len(dates)
    return tuple(
        EtfSmaBacktestStatsBar(
            date=dates[index],
            adjusted_close=Decimal(value),
        )
        for index, value in enumerate(values)
    )


def _slice(payload: dict[str, object], name: str) -> dict[str, object]:
    for item in payload["regime_slices"]:
        if item["slice_name"] == name:
            return item
    raise AssertionError(f"missing slice {name}")


def _assert_decimal_close(
    actual: object,
    expected: Decimal,
    *,
    tolerance: Decimal = Decimal("0.000000000000001"),
) -> None:
    assert abs(Decimal(str(actual)) - expected) <= tolerance


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
