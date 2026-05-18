import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.moving_average import (
    MovingAverageInput,
    MovingAverageObservation,
    build_simple_moving_average_observations,
)


MODULE_PATH = Path("src/algotrader/research/moving_average.py")

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
    "ipynb",
    "json",
    "langchain",
    "langgraph",
    "llm",
    "notebook",
    "numpy",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "persistence",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "sqlmodel",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
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
    "allocation",
    "alpaca",
    "api",
    "benchmark",
    "broker",
    "candidate",
    "cash",
    "client_order_id",
    "connect",
    "create_order",
    "download",
    "evaluator",
    "execution",
    "fill",
    "ingestion",
    "llm",
    "market_data",
    "ml",
    "notebook",
    "order",
    "portfolio",
    "position",
    "rank",
    "ranking",
    "recommendation",
    "request",
    "runtime",
    "scheduler",
    "score",
    "signal",
    "submit_order",
    "target_weight",
    "vectorbt",
}

_FORBIDDEN_CALL_NAMES = {
    "DictReader",
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

_FORBIDDEN_FIELD_PARTS = (
    "account",
    "allocation",
    "candidate",
    "execution",
    "fill",
    "order",
    "portfolio",
    "position",
    "rank",
    "recommendation",
    "score",
    "target_weight",
)


def moving_average_input(index: int, value: Decimal) -> MovingAverageInput:
    return MovingAverageInput(
        observation_date=date(2025, 1, 1) + timedelta(days=index),
        value=value,
    )


def series(values: tuple[str, ...]) -> tuple[MovingAverageInput, ...]:
    return tuple(
        moving_average_input(index, Decimal(value))
        for index, value in enumerate(values)
    )


def test_valid_input_accepts_plain_date_and_decimal() -> None:
    observation = MovingAverageInput(
        observation_date=date(2025, 1, 1),
        value=Decimal("100.25"),
    )

    assert observation.observation_date == date(2025, 1, 1)
    assert observation.value == Decimal("100.25")


def test_input_rejects_datetime() -> None:
    with pytest.raises(ValidationError, match="plain date"):
        MovingAverageInput(datetime(2025, 1, 1), Decimal("100"))


def test_input_rejects_non_date() -> None:
    with pytest.raises(ValidationError, match="plain date"):
        MovingAverageInput("2025-01-01", Decimal("100"))


def test_input_rejects_bool_date() -> None:
    with pytest.raises(ValidationError, match="plain date"):
        MovingAverageInput(True, Decimal("100"))


@pytest.mark.parametrize("bad_value", ("100", 100, 100.0, True, False))
def test_input_rejects_non_decimal_and_bool_values(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="Decimal"):
        MovingAverageInput(date(2025, 1, 1), bad_value)


@pytest.mark.parametrize("bad_value", (Decimal("0"), Decimal("-0.01")))
def test_input_rejects_zero_and_negative_values(bad_value: Decimal) -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        MovingAverageInput(date(2025, 1, 1), bad_value)


def test_dataclasses_are_frozen_and_slotted() -> None:
    input_observation = moving_average_input(0, Decimal("100"))
    moving_average_observation = build_simple_moving_average_observations(
        (input_observation,),
        window=1,
    )[0]

    assert is_dataclass(MovingAverageInput)
    assert is_dataclass(MovingAverageObservation)
    assert not hasattr(input_observation, "__dict__")
    assert not hasattr(moving_average_observation, "__dict__")

    with pytest.raises(FrozenInstanceError):
        input_observation.value = Decimal("101")
    with pytest.raises(FrozenInstanceError):
        moving_average_observation.window = 2


@pytest.mark.parametrize("bad_window", (True, False))
def test_window_rejects_bool_values(bad_window: bool) -> None:
    with pytest.raises(ValidationError, match="window"):
        build_simple_moving_average_observations(series(("100",)), window=bad_window)


@pytest.mark.parametrize("bad_window", ("1", Decimal("1"), 1.0, None))
def test_window_rejects_non_int_values(bad_window: object) -> None:
    with pytest.raises(ValidationError, match="window"):
        build_simple_moving_average_observations(series(("100",)), window=bad_window)


def test_window_rejects_zero() -> None:
    with pytest.raises(ValidationError, match="window"):
        build_simple_moving_average_observations(series(("100",)), window=0)


def test_window_rejects_negative() -> None:
    with pytest.raises(ValidationError, match="window"):
        build_simple_moving_average_observations(series(("100",)), window=-1)


@pytest.mark.parametrize("window", (1, 200))
def test_window_accepts_supported_positive_values(window: int) -> None:
    observations = series(tuple("100" for _ in range(window)))

    result = build_simple_moving_average_observations(observations, window=window)

    assert result[-1].window == window
    assert result[-1].moving_average_available is True


def test_rejects_empty_observations() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        build_simple_moving_average_observations((), window=2)


def test_rejects_duplicate_dates() -> None:
    observations = (
        MovingAverageInput(date(2025, 1, 1), Decimal("100")),
        MovingAverageInput(date(2025, 1, 1), Decimal("101")),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        build_simple_moving_average_observations(observations, window=2)


def test_rejects_unordered_dates() -> None:
    observations = (
        MovingAverageInput(date(2025, 1, 2), Decimal("100")),
        MovingAverageInput(date(2025, 1, 1), Decimal("101")),
    )

    with pytest.raises(ValidationError, match="strictly increasing"):
        build_simple_moving_average_observations(observations, window=2)


def test_rejects_malformed_entries() -> None:
    with pytest.raises(ValidationError, match="MovingAverageInput"):
        build_simple_moving_average_observations(
            (moving_average_input(0, Decimal("100")), object()),
            window=2,
        )


def test_accepts_any_iterable_and_returns_immutable_tuple_output() -> None:
    observations = (observation for observation in series(("100", "101", "102")))

    result = build_simple_moving_average_observations(observations, window=2)

    assert isinstance(result, tuple)
    assert tuple(observation.value for observation in result) == (
        Decimal("100"),
        Decimal("101"),
        Decimal("102"),
    )
    with pytest.raises(TypeError):
        result[0] = result[0]


def test_flat_series_produces_sma_and_not_above_after_window() -> None:
    result = build_simple_moving_average_observations(
        series(("10", "10", "10", "10", "10")),
        window=3,
    )

    assert tuple(observation.moving_average for observation in result) == (
        None,
        None,
        Decimal("10"),
        Decimal("10"),
        Decimal("10"),
    )
    assert tuple(observation.moving_average_available for observation in result) == (
        False,
        False,
        True,
        True,
        True,
    )
    assert tuple(observation.is_above_moving_average for observation in result) == (
        None,
        None,
        False,
        False,
        False,
    )


def test_increasing_series_uses_expected_trailing_arithmetic_means() -> None:
    result = build_simple_moving_average_observations(
        series(("1", "2", "3", "4", "5")),
        window=3,
    )

    assert tuple(observation.moving_average for observation in result) == (
        None,
        None,
        Decimal("2"),
        Decimal("3"),
        Decimal("4"),
    )
    assert tuple(observation.is_above_moving_average for observation in result) == (
        None,
        None,
        True,
        True,
        True,
    )


def test_equality_to_sma_is_not_above() -> None:
    result = build_simple_moving_average_observations(
        series(("1", "3", "2")),
        window=3,
    )

    assert result[-1].moving_average == Decimal("2")
    assert result[-1].is_above_moving_average is False


def test_first_window_minus_one_rows_have_unavailable_sma_fields() -> None:
    result = build_simple_moving_average_observations(
        series(("1", "2", "3", "4")),
        window=4,
    )

    for observation in result[:3]:
        assert observation.moving_average is None
        assert observation.moving_average_available is False
        assert observation.is_above_moving_average is None


def test_window_one_behavior_is_pinned() -> None:
    result = build_simple_moving_average_observations(
        series(("2", "3", "5")),
        window=1,
    )

    assert tuple(observation.moving_average for observation in result) == (
        Decimal("2"),
        Decimal("3"),
        Decimal("5"),
    )
    assert tuple(observation.moving_average_available for observation in result) == (
        True,
        True,
        True,
    )
    assert tuple(observation.is_above_moving_average for observation in result) == (
        False,
        False,
        False,
    )


def test_window_200_behavior_is_pinned_on_synthetic_205_row_input() -> None:
    observations = tuple(
        moving_average_input(index, Decimal(index + 1))
        for index in range(205)
    )

    result = build_simple_moving_average_observations(observations, window=200)

    assert len(result) == 205
    assert result[198].moving_average is None
    assert result[198].moving_average_available is False
    assert result[199].moving_average == Decimal("100.5")
    assert result[199].moving_average_available is True
    assert result[199].is_above_moving_average is True
    assert result[204].moving_average == Decimal("105.5")
    assert sum(
        observation.moving_average_available for observation in result
    ) == 6


def test_future_jump_does_not_leak_into_earlier_moving_average() -> None:
    result = build_simple_moving_average_observations(
        series(("10", "10", "10", "10", "10", "1000")),
        window=3,
    )

    assert result[2].moving_average == Decimal("10")
    assert result[3].moving_average == Decimal("10")
    assert result[4].moving_average == Decimal("10")
    assert result[5].moving_average == Decimal("340")


def test_changing_future_value_does_not_change_prior_observations() -> None:
    base = build_simple_moving_average_observations(
        series(("10", "10", "10", "10", "10", "1000")),
        window=3,
    )
    revised_future = build_simple_moving_average_observations(
        series(("10", "10", "10", "10", "10", "9999")),
        window=3,
    )

    assert base[:5] == revised_future[:5]
    assert base[5].moving_average != revised_future[5].moving_average


def test_decimal_precision_is_preserved_without_float_coercion() -> None:
    result = build_simple_moving_average_observations(
        series(("0.1", "0.2", "0.3")),
        window=3,
    )

    assert result[-1].moving_average == Decimal("0.2")
    assert isinstance(result[-1].moving_average, Decimal)
    assert result[-1].moving_average != Decimal(str((0.1 + 0.2 + 0.3) / 3))


def test_repeated_calls_are_equal_and_inputs_are_not_mutated() -> None:
    observations = series(("1.1", "2.2", "3.3", "4.4"))
    original_dates = tuple(observation.observation_date for observation in observations)
    original_values = tuple(observation.value for observation in observations)

    first = build_simple_moving_average_observations(observations, window=2)
    second = build_simple_moving_average_observations(observations, window=2)

    assert first == second
    assert tuple(observation.observation_date for observation in observations) == original_dates
    assert tuple(observation.value for observation in observations) == original_values


def test_module_imports_no_vendor_network_runtime_or_trading_path_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_module_references_no_broker_order_signal_scoring_or_runtime_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_module_makes_no_file_network_clock_vendor_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_moving_average_contracts_have_no_trading_or_discovery_fields() -> None:
    field_names = {
        field.name
        for contract in (MovingAverageInput, MovingAverageObservation)
        for field in fields(contract)
    }

    assert all(
        forbidden_part not in field_name
        for field_name in field_names
        for forbidden_part in _FORBIDDEN_FIELD_PARTS
    )


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
