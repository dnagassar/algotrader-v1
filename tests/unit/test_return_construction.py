import ast
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.return_construction import (
    close_to_close_returns,
    lagged_signal_action_pairs,
    simple_return,
)


MODULE_PATH = Path("src/algotrader/research/return_construction.py")

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
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "numpy",
    "openai",
    "pandas",
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
    "ValidatedResearchArtifact",
    "ValidatedSignalDefinition",
    "alpaca",
    "benchmark",
    "broker",
    "cash",
    "dividend",
    "download",
    "evaluator",
    "execution",
    "execution_plan",
    "fill",
    "portfolio",
    "ranking",
    "request",
    "signal_definition",
    "strategy",
    "submit_order",
    "total_return",
    "vectorbt",
}

_FORBIDDEN_CALL_NAMES = {
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "environ.get",
    "fit",
    "get",
    "getenv",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "read_csv",
    "request",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "uuid4",
    "write",
}


def test_simple_return_calculates_arithmetic_return_from_synthetic_values() -> None:
    result = simple_return(Decimal("100.00"), Decimal("105.25"))

    assert result == Decimal("0.0525")


def test_close_to_close_returns_builds_immutable_tuple() -> None:
    returns = close_to_close_returns(
        (Decimal("100"), Decimal("110"), Decimal("99"))
    )

    assert returns == (Decimal("0.1"), Decimal("-0.1"))
    assert isinstance(returns, tuple)
    with pytest.raises(TypeError):
        returns[0] = Decimal("0")


def test_decimal_precision_is_preserved_without_float_conversion() -> None:
    result = simple_return(Decimal("100.0000"), Decimal("100.0100"))

    assert result == Decimal("0.0001")
    assert isinstance(result, Decimal)
    assert result.as_tuple().exponent == -4


@pytest.mark.parametrize(
    "previous_value",
    (Decimal("0"), Decimal("-1")),
)
def test_zero_or_negative_prior_values_are_rejected(previous_value: Decimal) -> None:
    with pytest.raises(ValidationError, match="previous_value"):
        simple_return(previous_value, Decimal("101"))


@pytest.mark.parametrize(
    "previous_value,current_value",
    (
        (100, Decimal("101")),
        (Decimal("100"), 101),
        (1.0, Decimal("1.1")),
    ),
)
def test_non_decimal_numeric_inputs_are_rejected(
    previous_value: object,
    current_value: object,
) -> None:
    with pytest.raises(ValidationError, match="Decimal"):
        simple_return(previous_value, current_value)


@pytest.mark.parametrize(
    "values",
    (
        (),
        (Decimal("100"),),
        (Decimal("100"), 101),
        "100,101",
        None,
    ),
)
def test_malformed_return_sequences_are_rejected(values: object) -> None:
    with pytest.raises(ValidationError):
        close_to_close_returns(values)


def test_close_to_close_rejects_invalid_prior_values_inside_sequence() -> None:
    with pytest.raises(ValidationError, match="previous_value"):
        close_to_close_returns((Decimal("100"), Decimal("0"), Decimal("101")))


def test_lagged_signal_action_pairs_returns_observation_and_action_dates() -> None:
    pairs = lagged_signal_action_pairs(
        (
            date(2026, 1, 2),
            date(2026, 1, 5),
            date(2026, 1, 6),
        ),
        lag_days=2,
    )

    assert pairs == (
        (date(2026, 1, 2), date(2026, 1, 4)),
        (date(2026, 1, 5), date(2026, 1, 7)),
        (date(2026, 1, 6), date(2026, 1, 8)),
    )


def test_positive_lag_never_returns_same_day_action_dates() -> None:
    pairs = lagged_signal_action_pairs(
        (date(2026, 2, 2), date(2026, 2, 3)),
        lag_days=1,
    )

    assert all(action_date > observation_date for observation_date, action_date in pairs)


def test_zero_lag_is_allowed_for_mechanical_same_day_examples() -> None:
    pairs = lagged_signal_action_pairs((date(2026, 3, 2),), lag_days=0)

    assert pairs == ((date(2026, 3, 2), date(2026, 3, 2)),)


def test_lagged_action_outputs_are_immutable_tuples() -> None:
    pairs = lagged_signal_action_pairs((date(2026, 4, 1),), lag_days=1)

    assert isinstance(pairs, tuple)
    assert isinstance(pairs[0], tuple)
    with pytest.raises(TypeError):
        pairs[0] = (date(2026, 4, 1), date(2026, 4, 3))
    with pytest.raises(TypeError):
        pairs[0][1] = date(2026, 4, 3)


@pytest.mark.parametrize(
    "observation_dates",
    (
        (),
        (date(2026, 1, 2), date(2026, 1, 2)),
        (date(2026, 1, 3), date(2026, 1, 2)),
        (datetime(2026, 1, 2, 12, 0),),
        "2026-01-02",
        None,
    ),
)
def test_malformed_observation_date_sequences_are_rejected(
    observation_dates: object,
) -> None:
    with pytest.raises(ValidationError):
        lagged_signal_action_pairs(observation_dates)


@pytest.mark.parametrize("lag_days", (-1, 1.5, True))
def test_negative_or_non_integer_lag_values_are_rejected(lag_days: object) -> None:
    with pytest.raises(ValidationError, match="lag_days"):
        lagged_signal_action_pairs((date(2026, 1, 2),), lag_days=lag_days)


def test_module_imports_no_trading_path_vendor_network_or_data_library_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_module_references_no_strategy_signal_evaluator_or_trading_path_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_module_makes_no_io_network_broker_vendor_or_data_file_calls() -> None:
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
