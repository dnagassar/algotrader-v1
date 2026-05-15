import ast
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.daily_backtest import (
    DailyBacktestAssumptions,
    DailyBacktestResult,
    DailyExposure,
    run_daily_backtest,
)
from algotrader.research.price_snapshot import (
    HistoricalPriceBar,
    HistoricalPriceSnapshot,
)
from algotrader.research.sma_exposure import build_sma_200_daily_exposures


MODULE_PATH = Path("src/algotrader/research/sma_exposure.py")

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


def snapshot_from_prices(
    prices: tuple[Decimal, ...],
) -> HistoricalPriceSnapshot:
    start = date(2025, 1, 1)
    return HistoricalPriceSnapshot(
        symbol="SPY",
        bars=tuple(
            price_bar(start + timedelta(days=index), adjusted_close)
            for index, adjusted_close in enumerate(prices)
        ),
    )


def assumptions() -> DailyBacktestAssumptions:
    return DailyBacktestAssumptions(
        initial_equity=Decimal("1000"),
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )


def test_fewer_than_200_bars_returns_all_zero_exposure() -> None:
    source_snapshot = snapshot_from_prices(tuple(Decimal("100") for _ in range(199)))

    exposures = build_sma_200_daily_exposures(source_snapshot)

    assert isinstance(exposures, tuple)
    assert len(exposures) == len(source_snapshot.bars)
    assert tuple(item.date for item in exposures) == tuple(
        bar.date for bar in source_snapshot.bars
    )
    assert all(isinstance(item, DailyExposure) for item in exposures)
    assert tuple(item.exposure for item in exposures) == tuple(
        Decimal("0") for _ in source_snapshot.bars
    )
    assert {item.exposure for item in exposures} == {Decimal("0")}
    with pytest.raises(TypeError):
        exposures[0] = DailyExposure(source_snapshot.bars[0].date, Decimal("1"))


def test_exactly_200_bars_computes_first_possible_sma_exposure() -> None:
    source_snapshot = snapshot_from_prices(
        tuple(Decimal("100") for _ in range(199)) + (Decimal("201"),)
    )

    exposures = build_sma_200_daily_exposures(source_snapshot)

    assert tuple(item.exposure for item in exposures[:199]) == tuple(
        Decimal("0") for _ in range(199)
    )
    assert exposures[199].exposure == Decimal("1")


def test_more_than_200_bars_uses_rolling_200_day_window() -> None:
    source_snapshot = snapshot_from_prices(
        (Decimal("10000"),)
        + tuple(Decimal("1") for _ in range(199))
        + (Decimal("2"),)
    )

    exposures = build_sma_200_daily_exposures(source_snapshot)

    assert exposures[199].exposure == Decimal("0")
    assert exposures[200].exposure == Decimal("1")


@pytest.mark.parametrize(
    "prices,expected_exposure",
    (
        (tuple(Decimal("100") for _ in range(199)) + (Decimal("201"),), Decimal("1")),
        (tuple(Decimal("100") for _ in range(200)), Decimal("0")),
        (tuple(Decimal("100") for _ in range(199)) + (Decimal("50"),), Decimal("0")),
    ),
)
def test_sma_comparison_uses_strict_greater_than(
    prices: tuple[Decimal, ...],
    expected_exposure: Decimal,
) -> None:
    source_snapshot = snapshot_from_prices(prices)

    exposures = build_sma_200_daily_exposures(source_snapshot)

    assert exposures[-1].exposure == expected_exposure
    assert exposures[-1].exposure in (Decimal("0"), Decimal("1"))


def test_generation_does_not_mutate_snapshot_or_bars() -> None:
    source_snapshot = snapshot_from_prices(
        tuple(Decimal("100") for _ in range(199)) + (Decimal("201"),)
    )
    original_bars = source_snapshot.bars
    original_first_bar = source_snapshot.bars[0]
    original_values = tuple(bar.adjusted_close for bar in source_snapshot.bars)

    build_sma_200_daily_exposures(source_snapshot)

    assert source_snapshot.bars is original_bars
    assert source_snapshot.bars[0] is original_first_bar
    assert tuple(bar.adjusted_close for bar in source_snapshot.bars) == original_values


def test_repeated_generation_is_deterministic() -> None:
    source_snapshot = snapshot_from_prices(
        tuple(Decimal("100") for _ in range(199)) + (Decimal("201"),)
    )

    assert build_sma_200_daily_exposures(source_snapshot) == (
        build_sma_200_daily_exposures(source_snapshot)
    )


def test_malformed_snapshot_is_rejected() -> None:
    with pytest.raises(ValidationError, match="HistoricalPriceSnapshot"):
        build_sma_200_daily_exposures("not a snapshot")


def test_mutated_snapshot_bars_collection_is_rejected() -> None:
    source_snapshot = snapshot_from_prices((Decimal("100"),))
    object.__setattr__(source_snapshot, "bars", list(source_snapshot.bars))

    with pytest.raises(ValidationError, match="immutable tuple"):
        build_sma_200_daily_exposures(source_snapshot)


def test_empty_snapshot_is_rejected_by_existing_snapshot_validation() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        HistoricalPriceSnapshot(symbol="SPY", bars=())


def test_malformed_adjusted_close_is_rejected_without_coercion() -> None:
    source_snapshot = snapshot_from_prices((Decimal("100"),))
    object.__setattr__(source_snapshot.bars[0], "adjusted_close", "100")

    with pytest.raises(ValidationError, match="adjusted_close"):
        build_sma_200_daily_exposures(source_snapshot)


def test_mutated_snapshot_duplicate_dates_are_rejected() -> None:
    source_snapshot = snapshot_from_prices((Decimal("100"), Decimal("101")))
    object.__setattr__(source_snapshot.bars[1], "date", source_snapshot.bars[0].date)

    with pytest.raises(ValidationError, match="duplicate"):
        build_sma_200_daily_exposures(source_snapshot)


def test_generated_exposures_feed_daily_backtest_with_previous_exposure_rule() -> None:
    source_snapshot = snapshot_from_prices(
        tuple(Decimal("100") for _ in range(199))
        + (Decimal("300"), Decimal("330"))
    )
    exposures = build_sma_200_daily_exposures(source_snapshot)

    result = run_daily_backtest(source_snapshot, exposures, assumptions())

    assert isinstance(result, DailyBacktestResult)
    assert exposures[198].exposure == Decimal("0")
    assert exposures[199].exposure == Decimal("1")
    assert result.points[199].asset_return == Decimal("2")
    assert result.points[199].strategy_return_before_costs == Decimal("0")
    assert result.points[199].equity == Decimal("1000")
    assert result.points[200].asset_return == Decimal("0.1")
    assert result.points[200].strategy_return_before_costs == Decimal("0.1")
    assert result.points[200].equity == Decimal("1100.0")


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
