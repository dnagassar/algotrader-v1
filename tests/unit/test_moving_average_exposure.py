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
from algotrader.research.moving_average_exposure import (
    MovingAverageExposureState,
    build_previous_exposure_states,
)


MODULE_PATH = Path("src/algotrader/research/moving_average_exposure.py")

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
    "market_data",
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


def observations_from_values(
    values: tuple[str, ...],
    *,
    window: int,
) -> tuple[MovingAverageObservation, ...]:
    return build_simple_moving_average_observations(
        (
            moving_average_input(index, Decimal(value))
            for index, value in enumerate(values)
        ),
        window=window,
    )


def exposure_state(**overrides: object) -> MovingAverageExposureState:
    values = {
        "observation_date": date(2025, 1, 3),
        "window": 3,
        "moving_average_available": True,
        "is_above_moving_average": True,
        "current_exposure": 0,
        "next_exposure": 1,
        "reason": "above_moving_average",
    }
    values.update(overrides)
    return MovingAverageExposureState(**values)


def observation(
    observation_date: date,
    *,
    window: int = 3,
    moving_average_available: bool = True,
    is_above_moving_average: bool | None = False,
) -> MovingAverageObservation:
    return MovingAverageObservation(
        observation_date=observation_date,
        value=Decimal("100"),
        window=window,
        moving_average=Decimal("100") if moving_average_available else None,
        moving_average_available=moving_average_available,
        is_above_moving_average=is_above_moving_average,
    )


def test_exposure_state_is_frozen_and_slotted() -> None:
    state = exposure_state()

    assert is_dataclass(MovingAverageExposureState)
    assert not hasattr(state, "__dict__")
    with pytest.raises(FrozenInstanceError):
        state.next_exposure = 0


@pytest.mark.parametrize(
    "bad_value",
    (datetime(2025, 1, 3), "2025-01-03", True),
)
def test_exposure_state_rejects_non_plain_observation_dates(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="plain date"):
        exposure_state(observation_date=bad_value)


@pytest.mark.parametrize("bad_window", (0, -1, True, "3", Decimal("3")))
def test_exposure_state_rejects_malformed_windows(bad_window: object) -> None:
    with pytest.raises(ValidationError, match="window"):
        exposure_state(window=bad_window)


@pytest.mark.parametrize("bad_value", (None, 1, "true"))
def test_exposure_state_rejects_malformed_availability_values(
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match="moving_average_available"):
        exposure_state(moving_average_available=bad_value)


@pytest.mark.parametrize("bad_value", ("true", 1, Decimal("0")))
def test_exposure_state_rejects_malformed_above_average_values(
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match="is_above_moving_average"):
        exposure_state(is_above_moving_average=bad_value)


@pytest.mark.parametrize("field_name", ("current_exposure", "next_exposure"))
@pytest.mark.parametrize("bad_value", (-1, 2, True, Decimal("1"), "1"))
def test_exposure_state_rejects_invalid_exposure_values(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        exposure_state(**{field_name: bad_value})


def test_exposure_state_rejects_next_exposure_that_does_not_match_metadata() -> None:
    with pytest.raises(ValidationError, match="next_exposure"):
        exposure_state(next_exposure=0)


@pytest.mark.parametrize("bad_reason", ("", "   ", None, 1))
def test_exposure_state_rejects_non_string_or_empty_reason(
    bad_reason: object,
) -> None:
    with pytest.raises(ValidationError, match="reason"):
        exposure_state(reason=bad_reason)


def test_builder_rejects_empty_observations() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        build_previous_exposure_states(())


def test_builder_rejects_non_moving_average_observation_entries() -> None:
    source = observations_from_values(("10", "10", "30"), window=3)

    with pytest.raises(ValidationError, match="MovingAverageObservation"):
        build_previous_exposure_states((source[0], object()))


def test_builder_rejects_duplicate_dates() -> None:
    source = (
        observation(
            date(2025, 1, 1),
            moving_average_available=False,
            is_above_moving_average=None,
        ),
        observation(date(2025, 1, 1)),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        build_previous_exposure_states(source)


def test_builder_rejects_unordered_dates() -> None:
    source = (
        observation(
            date(2025, 1, 2),
            moving_average_available=False,
            is_above_moving_average=None,
        ),
        observation(date(2025, 1, 1)),
    )

    with pytest.raises(ValidationError, match="strictly increasing"):
        build_previous_exposure_states(source)


def test_builder_rejects_mixed_windows() -> None:
    source = (
        observation(
            date(2025, 1, 1),
            window=3,
            moving_average_available=False,
            is_above_moving_average=None,
        ),
        observation(date(2025, 1, 2), window=4),
    )

    with pytest.raises(ValidationError, match="single moving-average window"):
        build_previous_exposure_states(source)


def test_builder_accepts_any_iterable_and_returns_immutable_tuple_output() -> None:
    source = (
        observation
        for observation in observations_from_values(("10", "10", "30", "30"), window=3)
    )

    result = build_previous_exposure_states(source)

    assert isinstance(result, tuple)
    assert tuple(state.observation_date for state in result) == (
        date(2025, 1, 1),
        date(2025, 1, 2),
        date(2025, 1, 3),
        date(2025, 1, 4),
    )
    with pytest.raises(TypeError):
        result[0] = result[0]


def test_previous_exposure_mechanics_are_pinned() -> None:
    source = observations_from_values(
        ("10", "10", "30", "30", "5", "5", "5"),
        window=3,
    )

    result = build_previous_exposure_states(source)

    assert tuple(state.moving_average_available for state in result[:2]) == (
        False,
        False,
    )
    assert tuple(state.next_exposure for state in result[:2]) == (0, 0)
    assert result[2].is_above_moving_average is True
    assert result[2].current_exposure == 0
    assert result[2].next_exposure == 1
    assert result[3].current_exposure == 1
    assert result[3].next_exposure == 1
    assert result[4].is_above_moving_average is False
    assert result[4].current_exposure == 1
    assert result[4].next_exposure == 0
    assert source[6].value == source[6].moving_average
    assert result[6].current_exposure == 0
    assert result[6].next_exposure == 0
    assert result[6].reason == "not_above_moving_average"


def test_flat_series_produces_all_zero_exposures() -> None:
    result = build_previous_exposure_states(
        observations_from_values(("10", "10", "10", "10", "10"), window=3)
    )

    assert tuple(state.current_exposure for state in result) == (0, 0, 0, 0, 0)
    assert tuple(state.next_exposure for state in result) == (0, 0, 0, 0, 0)


def test_changing_future_value_does_not_change_prior_exposure_states() -> None:
    base = build_previous_exposure_states(
        observations_from_values(("10", "10", "30", "30", "5", "5", "5"), window=3)
    )
    revised_future = build_previous_exposure_states(
        observations_from_values(("10", "10", "30", "30", "5", "5", "500"), window=3)
    )

    assert base[:6] == revised_future[:6]
    assert base[6] != revised_future[6]


def test_breakout_does_not_create_same_row_current_exposure() -> None:
    result = build_previous_exposure_states(
        observations_from_values(("10", "10", "30", "30"), window=3)
    )

    assert result[2].current_exposure == 0
    assert result[2].next_exposure == 1
    assert result[3].current_exposure == 1


def test_repeated_calls_are_equal_and_source_observations_are_not_mutated() -> None:
    source = observations_from_values(("10", "10", "30", "30", "5"), window=3)
    original_values = tuple(observation.value for observation in source)
    original_average_metadata = tuple(
        (
            observation.moving_average,
            observation.moving_average_available,
            observation.is_above_moving_average,
        )
        for observation in source
    )

    first = build_previous_exposure_states(source)
    second = build_previous_exposure_states(tuple(source))

    assert first == second
    assert tuple(observation.value for observation in source) == original_values
    assert tuple(
        (
            observation.moving_average,
            observation.moving_average_available,
            observation.is_above_moving_average,
        )
        for observation in source
    ) == original_average_metadata


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


def test_exposure_state_contract_has_no_trading_or_discovery_fields() -> None:
    field_names = {field.name for field in fields(MovingAverageExposureState)}

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
