import ast
from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.daily_backtest import (
    DailyBacktestAssumptions,
    DailyBacktestPoint,
    DailyBacktestResult,
    DailyExposure,
    run_daily_backtest,
)
from algotrader.research.price_snapshot import (
    HistoricalPriceBar,
    HistoricalPriceSnapshot,
)


MODULE_PATH = Path("src/algotrader/research/daily_backtest.py")

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "csv",
    "database",
    "duckdb",
    "httpx",
    "json",
    "langchain",
    "langgraph",
    "llm",
    "numpy",
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_REFERENCE_NAMES = {
    "AlpacaPaperBroker",
    "ExecutionIntent",
    "ExecutionPlan",
    "LocalBroker",
    "PortfolioState",
    "ProposedOrder",
    "RiskEngine",
    "RiskVerdict",
    "ValidatedSignalDefinition",
    "account",
    "account_id",
    "alpaca",
    "api",
    "benchmark",
    "broker",
    "cash",
    "download",
    "evaluator",
    "execution",
    "execution_plan",
    "fill",
    "glob",
    "ingestion",
    "llm",
    "ml",
    "order",
    "portfolio",
    "ranking",
    "request",
    "rglob",
    "scheduler",
    "signal_definition",
    "submit_order",
    "vectorbt",
}

_FORBIDDEN_CALL_NAMES = {
    "DictReader",
    "DictWriter",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "dump",
    "dumps",
    "environ.get",
    "fit",
    "get",
    "getenv",
    "glob",
    "iterdir",
    "load",
    "loads",
    "makedirs",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "read",
    "read_csv",
    "read_text",
    "request",
    "rglob",
    "scandir",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}


def price_bar(on_date: date, adjusted_close: Decimal) -> HistoricalPriceBar:
    return HistoricalPriceBar(
        symbol="SPY",
        date=on_date,
        open=adjusted_close,
        high=adjusted_close,
        low=adjusted_close,
        close=adjusted_close,
        adjusted_close=adjusted_close,
        volume=1000,
    )


def snapshot(
    prices: tuple[Decimal, ...] = (
        Decimal("100"),
        Decimal("110"),
        Decimal("99"),
    ),
) -> HistoricalPriceSnapshot:
    start_dates = (
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
    )
    return HistoricalPriceSnapshot(
        symbol="SPY",
        bars=tuple(
            price_bar(on_date, adjusted_close)
            for on_date, adjusted_close in zip(start_dates, prices)
        ),
    )


def assumptions(**overrides: object) -> DailyBacktestAssumptions:
    values: dict[str, object] = {
        "initial_equity": Decimal("1000"),
        "fee_bps": Decimal("0"),
        "slippage_bps": Decimal("0"),
    }
    values.update(overrides)
    return DailyBacktestAssumptions(**values)


def exposure(on_date: date, value: Decimal) -> DailyExposure:
    return DailyExposure(date=on_date, exposure=value)


def aligned_exposures(
    source_snapshot: HistoricalPriceSnapshot,
    values: tuple[Decimal, ...],
) -> tuple[DailyExposure, ...]:
    return tuple(
        exposure(bar.date, value)
        for bar, value in zip(source_snapshot.bars, values)
    )


def point(**overrides: object) -> DailyBacktestPoint:
    values: dict[str, object] = {
        "date": date(2026, 1, 2),
        "adjusted_close": Decimal("100"),
        "exposure": Decimal("1"),
        "asset_return": Decimal("0"),
        "strategy_return_before_costs": Decimal("0"),
        "transaction_cost": Decimal("0"),
        "strategy_return_after_costs": Decimal("0"),
        "equity": Decimal("1000"),
    }
    values.update(overrides)
    return DailyBacktestPoint(**values)


def test_backtest_dataclasses_are_frozen_slotted_and_minimal() -> None:
    assert tuple(field.name for field in fields(DailyBacktestAssumptions)) == (
        "initial_equity",
        "fee_bps",
        "slippage_bps",
    )
    assert tuple(field.name for field in fields(DailyExposure)) == (
        "date",
        "exposure",
    )
    assert tuple(field.name for field in fields(DailyBacktestPoint)) == (
        "date",
        "adjusted_close",
        "exposure",
        "asset_return",
        "strategy_return_before_costs",
        "transaction_cost",
        "strategy_return_after_costs",
        "equity",
    )
    assert tuple(field.name for field in fields(DailyBacktestResult)) == (
        "symbol",
        "assumptions",
        "points",
    )

    for item in (
        assumptions(),
        exposure(date(2026, 1, 2), Decimal("1")),
        point(),
        DailyBacktestResult("SPY", assumptions(), (point(),)),
    ):
        assert hasattr(type(item), "__slots__")
        assert not hasattr(item, "__dict__")

    with pytest.raises(FrozenInstanceError):
        point().equity = Decimal("1")


def test_successful_backtest_with_all_zero_exposure_stays_flat() -> None:
    source_snapshot = snapshot()

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("0"), Decimal("0"), Decimal("0"))),
        assumptions(fee_bps=Decimal("10"), slippage_bps=Decimal("5")),
    )

    assert tuple(point.exposure for point in result.points) == (
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
    )
    assert tuple(point.strategy_return_after_costs for point in result.points) == (
        Decimal("0"),
        Decimal("0.0"),
        Decimal("-0.0"),
    )
    assert tuple(point.equity for point in result.points) == (
        Decimal("1000"),
        Decimal("1000.0"),
        Decimal("1000.00"),
    )
    assert result.total_return == Decimal("0.00")
    assert result.max_drawdown == Decimal("0")
    assert result.exposure_ratio == Decimal("0")
    assert result.turnover == Decimal("0")


def test_successful_backtest_with_all_one_exposure_tracks_adjusted_close_returns() -> None:
    source_snapshot = snapshot()

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("1"), Decimal("1"), Decimal("1"))),
        assumptions(),
    )

    assert tuple(point.asset_return for point in result.points) == (
        Decimal("0"),
        Decimal("0.1"),
        Decimal("-0.1"),
    )
    assert tuple(point.equity for point in result.points) == (
        Decimal("1000"),
        Decimal("1100.0"),
        Decimal("990.00"),
    )
    assert result.starting_equity == Decimal("1000")
    assert result.ending_equity == Decimal("990.00")
    assert result.total_return == Decimal("-0.01")
    assert result.max_drawdown == Decimal("0.1")
    assert result.exposure_ratio == Decimal("1")
    assert result.turnover == Decimal("1")


def test_first_bar_asset_return_is_zero() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("105.25")))

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("1"), Decimal("1"))),
        assumptions(),
    )

    assert result.points[0].asset_return == Decimal("0")


def test_adjusted_close_return_math_uses_decimal_arithmetic() -> None:
    source_snapshot = snapshot((Decimal("100.0000"), Decimal("105.2500")))

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("1"), Decimal("1"))),
        assumptions(),
    )

    assert result.points[1].asset_return == Decimal("0.0525")
    assert isinstance(result.points[1].asset_return, Decimal)


def test_no_lookahead_uses_previous_exposure_for_todays_asset_return() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("200"), Decimal("100")))

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("0"), Decimal("1"), Decimal("1"))),
        assumptions(),
    )

    assert result.points[1].asset_return == Decimal("1")
    assert result.points[1].strategy_return_before_costs == Decimal("0")
    assert result.points[1].equity == Decimal("1000")
    assert result.points[2].asset_return == Decimal("-0.5")
    assert result.points[2].strategy_return_before_costs == Decimal("-0.5")
    assert result.points[2].equity == Decimal("500.0")


def test_first_day_cost_is_charged_from_zero_to_initial_exposure() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("1"), Decimal("1"))),
        assumptions(fee_bps=Decimal("10"), slippage_bps=Decimal("5")),
    )

    assert result.points[0].transaction_cost == Decimal("0.0015")
    assert result.points[0].strategy_return_before_costs == Decimal("0")
    assert result.points[0].strategy_return_after_costs == Decimal("-0.0015")
    assert result.points[0].equity == Decimal("998.5000")


def test_exposure_change_costs_and_equity_compounding_are_deterministic() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110"), Decimal("121")))

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(
            source_snapshot,
            (Decimal("0"), Decimal("1"), Decimal("0.5")),
        ),
        assumptions(fee_bps=Decimal("75"), slippage_bps=Decimal("25")),
    )

    assert result.points[1].transaction_cost == Decimal("0.01")
    assert result.points[1].strategy_return_after_costs == Decimal("-0.01")
    assert result.points[1].equity == Decimal("990.00")
    assert result.points[2].strategy_return_before_costs == Decimal("0.1")
    assert result.points[2].transaction_cost == Decimal("0.005")
    assert result.points[2].strategy_return_after_costs == Decimal("0.095")
    assert result.points[2].equity == Decimal("1084.05000")
    assert result.exposure_ratio == Decimal("0.5")
    assert result.turnover == Decimal("1.5")


def test_points_are_stored_as_an_immutable_tuple() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("1"), Decimal("1"))),
        assumptions(),
    )

    assert isinstance(result.points, tuple)
    with pytest.raises(TypeError):
        result.points[0] = point()


def test_exposures_must_align_exactly_with_snapshot_bar_dates() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("0"), Decimal("1"))),
        assumptions(),
    )

    assert tuple(item.date for item in result.points) == tuple(
        bar.date for bar in source_snapshot.bars
    )


def test_missing_exposure_date_is_rejected() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))

    with pytest.raises(ValidationError, match="missing"):
        run_daily_backtest(
            source_snapshot,
            (exposure(date(2026, 1, 2), Decimal("1")),),
            assumptions(),
        )


def test_extra_exposure_date_is_rejected() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))

    with pytest.raises(ValidationError, match="outside snapshot"):
        run_daily_backtest(
            source_snapshot,
            (
                exposure(date(2026, 1, 2), Decimal("1")),
                exposure(date(2026, 1, 5), Decimal("1")),
                exposure(date(2026, 1, 6), Decimal("1")),
            ),
            assumptions(),
        )


def test_duplicate_exposure_dates_are_rejected() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))

    with pytest.raises(ValidationError, match="duplicate"):
        run_daily_backtest(
            source_snapshot,
            (
                exposure(date(2026, 1, 2), Decimal("1")),
                exposure(date(2026, 1, 2), Decimal("0")),
            ),
            assumptions(),
        )


def test_unordered_exposures_are_rejected() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))

    with pytest.raises(ValidationError, match="strictly increasing"):
        run_daily_backtest(
            source_snapshot,
            (
                exposure(date(2026, 1, 5), Decimal("1")),
                exposure(date(2026, 1, 2), Decimal("0")),
            ),
            assumptions(),
        )


def test_malformed_snapshot_is_rejected() -> None:
    with pytest.raises(ValidationError, match="HistoricalPriceSnapshot"):
        run_daily_backtest(
            "not a snapshot",
            (exposure(date(2026, 1, 2), Decimal("1")),),
            assumptions(),
        )


def test_malformed_snapshot_bar_values_are_rejected() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))
    object.__setattr__(source_snapshot.bars[1], "adjusted_close", 110)

    with pytest.raises(ValidationError, match="snapshot adjusted_close"):
        run_daily_backtest(
            source_snapshot,
            aligned_exposures(source_snapshot, (Decimal("1"), Decimal("1"))),
            assumptions(),
        )


@pytest.mark.parametrize(
    "field_name,bad_value",
    (
        ("initial_equity", Decimal("0")),
        ("initial_equity", Decimal("-1")),
        ("fee_bps", Decimal("-0.01")),
        ("slippage_bps", Decimal("-1")),
        ("initial_equity", 1000),
        ("fee_bps", 1),
        ("slippage_bps", True),
        ("slippage_bps", "0"),
    ),
)
def test_malformed_assumptions_are_rejected(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        assumptions(**{field_name: bad_value})


@pytest.mark.parametrize(
    "bad_date",
    (
        datetime(2026, 1, 2, 12, 0),
        True,
        "2026-01-02",
    ),
)
def test_exposure_rejects_non_plain_dates(bad_date: object) -> None:
    with pytest.raises(ValidationError, match="date"):
        DailyExposure(date=bad_date, exposure=Decimal("1"))


def test_exposure_rejects_date_subclasses() -> None:
    class CustomDate(date):
        pass

    with pytest.raises(ValidationError, match="date"):
        DailyExposure(date=CustomDate(2026, 1, 2), exposure=Decimal("1"))


@pytest.mark.parametrize(
    "bad_exposure",
    (
        Decimal("-0.1"),
        Decimal("1.1"),
        1,
        0.5,
        "1",
        True,
    ),
)
def test_exposure_rejects_invalid_non_decimal_or_out_of_range_values(
    bad_exposure: object,
) -> None:
    with pytest.raises(ValidationError, match="exposure"):
        DailyExposure(date=date(2026, 1, 2), exposure=bad_exposure)


@pytest.mark.parametrize(
    "field_name,bad_value",
    (
        ("date", datetime(2026, 1, 2, 12, 0)),
        ("date", True),
        ("adjusted_close", Decimal("0")),
        ("adjusted_close", 100),
        ("exposure", Decimal("1.1")),
        ("asset_return", "0"),
        ("strategy_return_before_costs", 0),
        ("transaction_cost", Decimal("-0.0001")),
        ("strategy_return_after_costs", False),
        ("equity", Decimal("0")),
        ("equity", "1000"),
    ),
)
def test_backtest_point_rejects_malformed_dates_decimals_and_ranges(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        point(**{field_name: bad_value})


@pytest.mark.parametrize(
    "points,error_match",
    (
        ((), "at least one"),
        ((object(),), "DailyBacktestPoint"),
        (
            (
                point(date=date(2026, 1, 5)),
                point(date=date(2026, 1, 2)),
            ),
            "strictly increasing",
        ),
    ),
)
def test_backtest_result_rejects_malformed_points(
    points: tuple[object, ...],
    error_match: str,
) -> None:
    with pytest.raises(ValidationError, match=error_match):
        DailyBacktestResult("SPY", assumptions(), points)


def test_backtest_result_rejects_malformed_assumptions() -> None:
    with pytest.raises(ValidationError, match="DailyBacktestAssumptions"):
        DailyBacktestResult("SPY", object(), (point(),))


def test_backtest_result_symbol_is_normalized_and_non_empty() -> None:
    item = DailyBacktestResult(" spy ", assumptions(), (point(),))

    assert item.symbol == "SPY"
    with pytest.raises(ValidationError, match="symbol"):
        DailyBacktestResult(" ", assumptions(), (point(),))


def test_to_dict_serializes_primitives_dates_decimals_points_and_metrics() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))

    result = run_daily_backtest(
        source_snapshot,
        aligned_exposures(source_snapshot, (Decimal("1"), Decimal("1"))),
        assumptions(fee_bps=Decimal("10"), slippage_bps=Decimal("5")),
    )

    payload = result.to_dict()

    assert tuple(payload) == (
        "symbol",
        "assumptions",
        "starting_equity",
        "ending_equity",
        "total_return",
        "max_drawdown",
        "exposure_ratio",
        "turnover",
        "points",
    )
    assert payload["symbol"] == "SPY"
    assert payload["assumptions"] == {
        "initial_equity": "1000",
        "fee_bps": "10",
        "slippage_bps": "5",
    }
    assert payload["starting_equity"] == "1000"
    assert payload["ending_equity"] == "1098.35000000"
    assert payload["total_return"] == "0.09835000"
    assert payload["max_drawdown"] == "0.0015"
    assert payload["exposure_ratio"] == "1"
    assert payload["turnover"] == "1"
    assert isinstance(payload["points"], list)
    assert tuple(payload["points"][0]) == (
        "date",
        "adjusted_close",
        "exposure",
        "asset_return",
        "strategy_return_before_costs",
        "transaction_cost",
        "strategy_return_after_costs",
        "equity",
    )
    assert payload["points"][0]["date"] == "2026-01-02"
    assert payload["points"][0]["adjusted_close"] == "100"
    assert payload["points"][0]["transaction_cost"] == "0.0015"
    assert payload["points"][0]["equity"] == "998.5000"
    assert payload["points"][1]["date"] == "2026-01-05"
    assert payload["points"][1]["asset_return"] == "0.1"
    assert payload["points"][1]["equity"] == "1098.35000000"
    assert all(
        field_name not in payload
        for field_name in (
            "account_id",
            "broker_order_id",
            "fill_price",
            "portfolio_state",
            "strategy_approved",
        )
    )


def test_run_does_not_mutate_snapshot_bars_assumptions_or_exposures() -> None:
    source_snapshot = snapshot((Decimal("100"), Decimal("110")))
    original_bars = source_snapshot.bars
    original_first_bar = source_snapshot.bars[0]
    assumption_values = assumptions()
    exposure_values = list(
        aligned_exposures(source_snapshot, (Decimal("1"), Decimal("1")))
    )
    original_first_exposure = exposure_values[0]

    result = run_daily_backtest(source_snapshot, exposure_values, assumption_values)
    exposure_values[0] = exposure(date(2026, 1, 2), Decimal("0"))

    assert source_snapshot.bars is original_bars
    assert source_snapshot.bars[0] is original_first_bar
    assert assumption_values.initial_equity == Decimal("1000")
    assert original_first_exposure.exposure == Decimal("1")
    assert result.assumptions is assumption_values
    assert result.points[0].exposure == Decimal("1")
    assert result.points[1].equity == Decimal("1100.0")


def test_module_imports_no_vendor_network_runtime_or_trading_path_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_module_references_no_broker_order_signal_evaluator_or_runtime_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_module_makes_no_file_network_vendor_ingestion_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


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


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


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
