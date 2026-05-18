import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.exposure_returns import (
    ExposureReturnObservation,
    build_exposure_applied_returns,
)
from algotrader.research.moving_average import (
    MovingAverageInput,
    build_simple_moving_average_observations,
)
from algotrader.research.moving_average_exposure import (
    MovingAverageExposureState,
    build_previous_exposure_states,
)


MODULE_PATH = Path("src/algotrader/research/exposure_returns.py")

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


def value_series(values: tuple[str, ...]) -> tuple[MovingAverageInput, ...]:
    return tuple(
        moving_average_input(index, Decimal(value))
        for index, value in enumerate(values)
    )


def exposure_state(
    index: int = 0,
    *,
    current_exposure: int = 0,
    moving_average_available: bool = True,
    is_above_moving_average: bool | None = False,
) -> MovingAverageExposureState:
    if not moving_average_available:
        next_exposure = 0
        reason = "moving_average_unavailable"
    elif is_above_moving_average is True:
        next_exposure = 1
        reason = "above_moving_average"
    else:
        next_exposure = 0
        reason = "not_above_moving_average"

    return MovingAverageExposureState(
        observation_date=date(2025, 1, 1) + timedelta(days=index),
        window=3,
        moving_average_available=moving_average_available,
        is_above_moving_average=is_above_moving_average,
        current_exposure=current_exposure,
        next_exposure=next_exposure,
        reason=reason,
    )


def exposure_states(
    current_exposures: tuple[int, ...],
) -> tuple[MovingAverageExposureState, ...]:
    return tuple(
        exposure_state(index, current_exposure=current_exposure)
        for index, current_exposure in enumerate(current_exposures)
    )


def exposure_return_observation(
    **overrides: object,
) -> ExposureReturnObservation:
    values = {
        "observation_date": date(2025, 1, 2),
        "value": Decimal("110"),
        "current_exposure": 1,
        "asset_return": Decimal("0.1"),
        "exposure_return": Decimal("0.1"),
        "return_available": True,
        "reason": "above_moving_average",
    }
    values.update(overrides)
    return ExposureReturnObservation(**values)


def test_exposure_return_observation_is_frozen_and_slotted() -> None:
    observation = exposure_return_observation()

    assert is_dataclass(ExposureReturnObservation)
    assert not hasattr(observation, "__dict__")
    with pytest.raises(FrozenInstanceError):
        observation.exposure_return = Decimal("0")


def test_exposure_return_observation_accepts_valid_first_unavailable_row() -> None:
    observation = ExposureReturnObservation(
        observation_date=date(2025, 1, 1),
        value=Decimal("100"),
        current_exposure=0,
        asset_return=None,
        exposure_return=None,
        return_available=False,
        reason="moving_average_unavailable",
    )

    assert observation.asset_return is None
    assert observation.exposure_return is None
    assert observation.return_available is False


def test_exposure_return_observation_accepts_valid_available_return_row() -> None:
    observation = exposure_return_observation()

    assert observation.asset_return == Decimal("0.1")
    assert observation.exposure_return == Decimal("0.1")
    assert observation.return_available is True


@pytest.mark.parametrize(
    "bad_value",
    (datetime(2025, 1, 1), "2025-01-01", True),
)
def test_observation_rejects_non_plain_observation_dates(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="plain date"):
        exposure_return_observation(observation_date=bad_value)


@pytest.mark.parametrize("bad_value", ("100", 100, 100.0, True, False))
def test_observation_rejects_non_decimal_values(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="value"):
        exposure_return_observation(value=bad_value)


@pytest.mark.parametrize(
    "bad_value",
    (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")),
)
def test_observation_rejects_non_positive_or_non_finite_values(
    bad_value: Decimal,
) -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        exposure_return_observation(value=bad_value)


@pytest.mark.parametrize("bad_value", (True, False))
def test_observation_rejects_bool_current_exposure(bad_value: bool) -> None:
    with pytest.raises(ValidationError, match="current_exposure"):
        exposure_return_observation(current_exposure=bad_value)


@pytest.mark.parametrize("bad_value", (-1, 2, Decimal("1"), "1"))
def test_observation_rejects_current_exposure_values_other_than_zero_or_one(
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match="current_exposure"):
        exposure_return_observation(current_exposure=bad_value)


@pytest.mark.parametrize("bad_value", (None, 1, "true"))
def test_observation_rejects_malformed_return_available_values(
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match="return_available"):
        exposure_return_observation(return_available=bad_value)


@pytest.mark.parametrize(
    ("asset_return", "exposure_return", "return_available", "match"),
    (
        (Decimal("0"), None, False, "asset_return"),
        (None, Decimal("0"), False, "exposure_return"),
        (None, Decimal("0"), True, "asset_return"),
        (Decimal("0"), None, True, "exposure_return"),
        ("0", Decimal("0"), True, "asset_return"),
        (Decimal("0"), "0", True, "exposure_return"),
        (Decimal("NaN"), Decimal("0"), True, "asset_return"),
        (Decimal("0"), Decimal("NaN"), True, "exposure_return"),
    ),
)
def test_observation_rejects_malformed_return_field_combinations(
    asset_return: object,
    exposure_return: object,
    return_available: object,
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        exposure_return_observation(
            asset_return=asset_return,
            exposure_return=exposure_return,
            return_available=return_available,
        )


def test_observation_rejects_exposure_return_that_does_not_match_exposure() -> None:
    with pytest.raises(ValidationError, match="exposure_return"):
        exposure_return_observation(
            current_exposure=0,
            asset_return=Decimal("0.1"),
            exposure_return=Decimal("0.1"),
        )


@pytest.mark.parametrize("bad_reason", ("", "   ", None, 1))
def test_observation_rejects_empty_or_non_string_reason(bad_reason: object) -> None:
    with pytest.raises(ValidationError, match="reason"):
        exposure_return_observation(reason=bad_reason)


def test_builder_rejects_empty_values() -> None:
    with pytest.raises(ValidationError, match="values"):
        build_exposure_applied_returns((), (exposure_state(),))


def test_builder_rejects_empty_exposure_states() -> None:
    with pytest.raises(ValidationError, match="exposure_states"):
        build_exposure_applied_returns((moving_average_input(0, Decimal("100")),), ())


def test_builder_rejects_non_moving_average_input_entries() -> None:
    with pytest.raises(ValidationError, match="MovingAverageInput"):
        build_exposure_applied_returns(
            (moving_average_input(0, Decimal("100")), object()),
            exposure_states((0, 0)),
        )


def test_builder_rejects_non_moving_average_exposure_state_entries() -> None:
    with pytest.raises(ValidationError, match="MovingAverageExposureState"):
        build_exposure_applied_returns(
            value_series(("100", "101")),
            (exposure_state(0), object()),
        )


def test_builder_rejects_length_mismatch() -> None:
    with pytest.raises(ValidationError, match="same length"):
        build_exposure_applied_returns(
            value_series(("100", "101")),
            (exposure_state(0),),
        )


def test_builder_rejects_date_mismatch_between_values_and_exposure_states() -> None:
    with pytest.raises(ValidationError, match="matching observation dates"):
        build_exposure_applied_returns(
            value_series(("100", "101")),
            (exposure_state(0), exposure_state(2)),
        )


def test_builder_rejects_duplicate_value_dates() -> None:
    values = (
        MovingAverageInput(date(2025, 1, 1), Decimal("100")),
        MovingAverageInput(date(2025, 1, 1), Decimal("101")),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        build_exposure_applied_returns(values, exposure_states((0, 0)))


def test_builder_rejects_duplicate_exposure_state_dates() -> None:
    states = (
        exposure_state(0),
        MovingAverageExposureState(
            observation_date=date(2025, 1, 1),
            window=3,
            moving_average_available=True,
            is_above_moving_average=False,
            current_exposure=0,
            next_exposure=0,
            reason="not_above_moving_average",
        ),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        build_exposure_applied_returns(value_series(("100", "101")), states)


def test_builder_rejects_unordered_value_dates() -> None:
    values = (
        MovingAverageInput(date(2025, 1, 2), Decimal("100")),
        MovingAverageInput(date(2025, 1, 1), Decimal("101")),
    )

    with pytest.raises(ValidationError, match="strictly increasing"):
        build_exposure_applied_returns(values, exposure_states((0, 0)))


def test_builder_rejects_unordered_exposure_state_dates() -> None:
    states = (exposure_state(1), exposure_state(0))

    with pytest.raises(ValidationError, match="strictly increasing"):
        build_exposure_applied_returns(value_series(("100", "101")), states)


def test_builder_accepts_any_iterable_and_returns_immutable_tuple_output() -> None:
    values = (value for value in value_series(("100", "101", "102")))
    states = (state for state in exposure_states((0, 1, 1)))

    result = build_exposure_applied_returns(values, states)

    assert isinstance(result, tuple)
    assert tuple(observation.value for observation in result) == (
        Decimal("100"),
        Decimal("101"),
        Decimal("102"),
    )
    with pytest.raises(TypeError):
        result[0] = result[0]


def test_flat_series_produces_zero_asset_and_exposure_returns_after_first_row() -> None:
    result = build_exposure_applied_returns(
        value_series(("10", "10", "10", "10")),
        exposure_states((0, 1, 0, 1)),
    )

    assert tuple(observation.asset_return for observation in result) == (
        None,
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
    )
    assert tuple(observation.exposure_return for observation in result) == (
        None,
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
    )


def test_zero_current_exposure_forces_zero_exposure_return_on_positive_return() -> None:
    result = build_exposure_applied_returns(
        value_series(("100", "110")),
        exposure_states((0, 0)),
    )

    assert result[1].asset_return == Decimal("0.1")
    assert result[1].current_exposure == 0
    assert result[1].exposure_return == Decimal("0")


def test_one_current_exposure_makes_exposure_return_equal_asset_return() -> None:
    result = build_exposure_applied_returns(
        value_series(("100", "110")),
        exposure_states((0, 1)),
    )

    assert result[1].asset_return == Decimal("0.1")
    assert result[1].current_exposure == 1
    assert result[1].exposure_return == result[1].asset_return


def test_first_row_has_no_return_and_is_marked_unavailable() -> None:
    result = build_exposure_applied_returns(
        value_series(("100", "110")),
        exposure_states((0, 1)),
    )

    assert result[0].asset_return is None
    assert result[0].exposure_return is None
    assert result[0].return_available is False
    assert result[1].return_available is True


def test_decimal_return_values_are_preserved_without_float_coercion() -> None:
    result = build_exposure_applied_returns(
        value_series(("3", "4")),
        exposure_states((0, 1)),
    )

    expected = (Decimal("4") - Decimal("3")) / Decimal("3")
    assert result[1].asset_return == expected
    assert result[1].exposure_return == expected
    assert isinstance(result[1].asset_return, Decimal)
    assert isinstance(result[1].exposure_return, Decimal)
    assert result[1].asset_return != Decimal(str((4 - 3) / 3))


def test_negative_asset_returns_are_allowed_for_positive_declining_values() -> None:
    result = build_exposure_applied_returns(
        value_series(("100", "80")),
        exposure_states((0, 1)),
    )

    assert result[1].asset_return == Decimal("-0.2")
    assert result[1].exposure_return == Decimal("-0.2")


def test_exposure_return_uses_current_exposure_not_next_exposure() -> None:
    states = (
        exposure_state(0, current_exposure=0, is_above_moving_average=True),
        exposure_state(1, current_exposure=0, is_above_moving_average=True),
        exposure_state(2, current_exposure=1, is_above_moving_average=False),
    )

    result = build_exposure_applied_returns(value_series(("100", "110", "121")), states)

    assert states[1].next_exposure == 1
    assert result[1].current_exposure == 0
    assert result[1].asset_return == Decimal("0.1")
    assert result[1].exposure_return == Decimal("0")
    assert result[2].current_exposure == 1
    assert result[2].asset_return == Decimal("0.1")
    assert result[2].exposure_return == Decimal("0.1")


def test_previous_exposure_breakout_does_not_create_same_row_return_exposure() -> None:
    values = value_series(("10", "10", "30", "33"))
    moving_average_observations = build_simple_moving_average_observations(
        values,
        window=3,
    )
    states = build_previous_exposure_states(moving_average_observations)

    result = build_exposure_applied_returns(values, states)

    assert moving_average_observations[2].is_above_moving_average is True
    assert states[2].current_exposure == 0
    assert states[2].next_exposure == 1
    assert result[2].asset_return == Decimal("2")
    assert result[2].exposure_return == Decimal("0")
    assert result[3].current_exposure == states[2].next_exposure
    assert result[3].asset_return == Decimal("0.1")
    assert result[3].exposure_return == Decimal("0.1")


def test_changing_future_value_does_not_change_earlier_exposure_applied_returns() -> None:
    base_values = value_series(("10", "10", "30", "33", "5"))
    revised_values = value_series(("10", "10", "30", "33", "500"))
    base_states = build_previous_exposure_states(
        build_simple_moving_average_observations(base_values, window=3)
    )
    revised_states = build_previous_exposure_states(
        build_simple_moving_average_observations(revised_values, window=3)
    )

    base = build_exposure_applied_returns(base_values, base_states)
    revised = build_exposure_applied_returns(revised_values, revised_states)

    assert base[:4] == revised[:4]
    assert base[4] != revised[4]


def test_future_breakout_does_not_affect_earlier_exposure_applied_returns() -> None:
    flat_values = value_series(("10", "10", "10", "10", "10"))
    breakout_values = value_series(("10", "10", "10", "10", "30"))
    flat_states = build_previous_exposure_states(
        build_simple_moving_average_observations(flat_values, window=3)
    )
    breakout_states = build_previous_exposure_states(
        build_simple_moving_average_observations(breakout_values, window=3)
    )

    flat = build_exposure_applied_returns(flat_values, flat_states)
    breakout = build_exposure_applied_returns(breakout_values, breakout_states)

    assert flat[:4] == breakout[:4]
    assert breakout[4].current_exposure == 0
    assert breakout[4].exposure_return == Decimal("0")


def test_repeated_calls_are_equal_and_source_objects_are_not_mutated() -> None:
    values = value_series(("100", "110", "121"))
    states = exposure_states((0, 1, 1))
    original_value_fields = tuple(
        (value.observation_date, value.value)
        for value in values
    )
    original_state_fields = tuple(
        (
            state.observation_date,
            state.current_exposure,
            state.next_exposure,
            state.reason,
        )
        for state in states
    )

    first = build_exposure_applied_returns(values, states)
    second = build_exposure_applied_returns(tuple(values), tuple(states))

    assert first == second
    assert tuple((value.observation_date, value.value) for value in values) == (
        original_value_fields
    )
    assert tuple(
        (
            state.observation_date,
            state.current_exposure,
            state.next_exposure,
            state.reason,
        )
        for state in states
    ) == original_state_fields


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


def test_exposure_return_contract_has_no_trading_or_discovery_fields() -> None:
    field_names = {field.name for field in fields(ExposureReturnObservation)}

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
