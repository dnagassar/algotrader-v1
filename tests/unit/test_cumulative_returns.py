import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.cumulative_returns import (
    CumulativeReturnObservation,
    build_cumulative_return_path,
)
from algotrader.research.exposure_returns import (
    ExposureReturnObservation,
    build_exposure_applied_returns,
)
from algotrader.research.moving_average import (
    MovingAverageInput,
    build_simple_moving_average_observations,
)
from algotrader.research.moving_average_exposure import (
    build_previous_exposure_states,
)


MODULE_PATH = Path("src/algotrader/research/cumulative_returns.py")

_ZERO = Decimal("0")
_MISSING = object()

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
    "alpha",
    "alpaca",
    "api",
    "benchmark",
    "beta",
    "broker",
    "cagr",
    "candidate",
    "cash",
    "client_order_id",
    "connect",
    "create_order",
    "download",
    "drawdown",
    "equity",
    "evaluator",
    "execution",
    "fill",
    "ingestion",
    "llm",
    "market_data",
    "ml",
    "notebook",
    "order",
    "pnl",
    "portfolio",
    "position",
    "rank",
    "ranking",
    "recommendation",
    "request",
    "runtime",
    "scheduler",
    "score",
    "sharpe",
    "signal",
    "submit_order",
    "target_weight",
    "vectorbt",
    "volatility",
    "win_rate",
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
    "alpha",
    "benchmark",
    "beta",
    "cagr",
    "candidate",
    "drawdown",
    "equity",
    "execution",
    "fill",
    "order",
    "pnl",
    "portfolio",
    "position",
    "rank",
    "recommendation",
    "score",
    "sharpe",
    "target_weight",
    "volatility",
    "win_rate",
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


def exposure_return_observation(
    index: int = 1,
    *,
    current_exposure: int = 1,
    asset_return: object = _MISSING,
    exposure_return: object = _MISSING,
    return_available: bool = True,
    observation_date: object = _MISSING,
    reason: str = "above_moving_average",
) -> ExposureReturnObservation:
    if observation_date is _MISSING:
        observation_date = date(2025, 1, 1) + timedelta(days=index)

    if return_available:
        checked_asset_return = (
            Decimal("0") if asset_return is _MISSING else asset_return
        )
        if exposure_return is not _MISSING:
            checked_exposure_return = exposure_return
        elif current_exposure == 0:
            checked_exposure_return = _ZERO
        else:
            checked_exposure_return = checked_asset_return
    else:
        checked_asset_return = None
        checked_exposure_return = None

    return ExposureReturnObservation(
        observation_date=observation_date,
        value=Decimal("100") + Decimal(index),
        current_exposure=current_exposure,
        asset_return=checked_asset_return,
        exposure_return=checked_exposure_return,
        return_available=return_available,
        reason=reason,
    )


def baseline_exposure_return(index: int = 0) -> ExposureReturnObservation:
    return exposure_return_observation(
        index,
        current_exposure=0,
        return_available=False,
        reason="moving_average_unavailable",
    )


def cumulative_return_observation(
    **overrides: object,
) -> CumulativeReturnObservation:
    values = {
        "observation_date": date(2025, 1, 2),
        "asset_return": Decimal("0.1"),
        "exposure_return": Decimal("0.1"),
        "asset_cumulative_return": Decimal("0.1"),
        "exposure_cumulative_return": Decimal("0.1"),
        "return_available": True,
        "reason": "return_compounded",
    }
    values.update(overrides)
    return CumulativeReturnObservation(**values)


def malformed_source_return(**overrides: object) -> ExposureReturnObservation:
    values = {
        "observation_date": date(2025, 1, 2),
        "value": Decimal("101"),
        "current_exposure": 1,
        "asset_return": Decimal("0.1"),
        "exposure_return": Decimal("0.1"),
        "return_available": True,
        "reason": "above_moving_average",
    }
    values.update(overrides)
    observation = object.__new__(ExposureReturnObservation)
    for field_name, value in values.items():
        object.__setattr__(observation, field_name, value)

    return observation


def test_cumulative_return_observation_is_frozen_and_slotted() -> None:
    observation = cumulative_return_observation()

    assert is_dataclass(CumulativeReturnObservation)
    assert not hasattr(observation, "__dict__")
    with pytest.raises(FrozenInstanceError):
        observation.exposure_cumulative_return = Decimal("0")


def test_observation_accepts_valid_first_baseline_row() -> None:
    observation = CumulativeReturnObservation(
        observation_date=date(2025, 1, 1),
        asset_return=None,
        exposure_return=None,
        asset_cumulative_return=Decimal("0"),
        exposure_cumulative_return=Decimal("0"),
        return_available=False,
        reason="initial cumulative return baseline",
    )

    assert observation.asset_return is None
    assert observation.exposure_return is None
    assert observation.asset_cumulative_return == Decimal("0")
    assert observation.exposure_cumulative_return == Decimal("0")


def test_observation_accepts_valid_available_cumulative_row() -> None:
    observation = cumulative_return_observation(
        asset_return=Decimal("-0.05"),
        exposure_return=Decimal("0"),
        asset_cumulative_return=Decimal("0.045"),
        exposure_cumulative_return=Decimal("0.1"),
    )

    assert observation.asset_return == Decimal("-0.05")
    assert observation.exposure_return == Decimal("0")
    assert observation.return_available is True


def test_observation_rejects_datetime_observation_date() -> None:
    with pytest.raises(ValidationError, match="plain date"):
        cumulative_return_observation(observation_date=datetime(2025, 1, 1))


@pytest.mark.parametrize("bad_value", ("2025-01-01", True))
def test_observation_rejects_non_date_observation_date(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="plain date"):
        cumulative_return_observation(observation_date=bad_value)


@pytest.mark.parametrize("bad_value", (None, 1, "true"))
def test_observation_rejects_non_bool_return_available(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="return_available"):
        cumulative_return_observation(return_available=bad_value)


@pytest.mark.parametrize(
    ("asset_return", "exposure_return", "return_available", "match"),
    (
        (Decimal("0"), None, False, "asset_return"),
        (None, Decimal("0"), False, "exposure_return"),
        (None, Decimal("0"), True, "asset_return"),
        (Decimal("0"), None, True, "exposure_return"),
        ("0", Decimal("0"), True, "asset_return"),
        (Decimal("0"), "0", True, "exposure_return"),
        (True, Decimal("0"), True, "asset_return"),
        (Decimal("0"), False, True, "exposure_return"),
        (Decimal("NaN"), Decimal("0"), True, "asset_return"),
        (Decimal("0"), Decimal("NaN"), True, "exposure_return"),
        (Decimal("-1"), Decimal("0"), True, "asset_return"),
        (Decimal("0"), Decimal("-1"), True, "exposure_return"),
    ),
)
def test_observation_rejects_malformed_return_field_combinations(
    asset_return: object,
    exposure_return: object,
    return_available: object,
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        cumulative_return_observation(
            asset_return=asset_return,
            exposure_return=exposure_return,
            return_available=return_available,
        )


@pytest.mark.parametrize(
    "field_name",
    ("asset_cumulative_return", "exposure_cumulative_return"),
)
@pytest.mark.parametrize("bad_value", ("0", 0, 0.0, None))
def test_observation_rejects_non_decimal_cumulative_returns(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        cumulative_return_observation(**{field_name: bad_value})


@pytest.mark.parametrize(
    "field_name",
    ("asset_cumulative_return", "exposure_cumulative_return"),
)
@pytest.mark.parametrize("bad_value", (True, False))
def test_observation_rejects_bool_cumulative_returns(
    field_name: str,
    bad_value: bool,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        cumulative_return_observation(**{field_name: bad_value})


@pytest.mark.parametrize(
    "field_name",
    ("asset_cumulative_return", "exposure_cumulative_return"),
)
@pytest.mark.parametrize("bad_value", (Decimal("NaN"), Decimal("Infinity")))
def test_observation_rejects_non_finite_cumulative_returns(
    field_name: str,
    bad_value: Decimal,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        cumulative_return_observation(**{field_name: bad_value})


@pytest.mark.parametrize("bad_reason", ("", "   ", None, 1))
def test_observation_rejects_empty_or_non_string_reason(bad_reason: object) -> None:
    with pytest.raises(ValidationError, match="reason"):
        cumulative_return_observation(reason=bad_reason)


def test_builder_rejects_empty_returns() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        build_cumulative_return_path(())


def test_builder_rejects_non_exposure_return_observation_entries() -> None:
    with pytest.raises(ValidationError, match="ExposureReturnObservation"):
        build_cumulative_return_path((baseline_exposure_return(), object()))


def test_builder_rejects_duplicate_dates() -> None:
    returns = (
        baseline_exposure_return(0),
        exposure_return_observation(0, asset_return=Decimal("0.1")),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        build_cumulative_return_path(returns)


def test_builder_rejects_unordered_dates() -> None:
    returns = (
        exposure_return_observation(1, asset_return=Decimal("0.1")),
        baseline_exposure_return(0),
    )

    with pytest.raises(ValidationError, match="strictly increasing"):
        build_cumulative_return_path(returns)


def test_builder_rejects_malformed_available_source_rows() -> None:
    returns = (
        baseline_exposure_return(0),
        malformed_source_return(asset_return=Decimal("-1")),
    )

    with pytest.raises(ValidationError, match="asset_return"):
        build_cumulative_return_path(returns)


def test_builder_accepts_any_iterable_and_returns_immutable_tuple_output() -> None:
    returns = (
        observation
        for observation in (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=Decimal("0.1")),
            exposure_return_observation(2, asset_return=Decimal("0.05")),
        )
    )

    result = build_cumulative_return_path(returns)

    assert isinstance(result, tuple)
    assert tuple(observation.observation_date for observation in result) == (
        date(2025, 1, 1),
        date(2025, 1, 2),
        date(2025, 1, 3),
    )
    with pytest.raises(TypeError):
        result[0] = result[0]


def test_flat_zero_return_path_keeps_cumulative_returns_at_zero() -> None:
    result = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=Decimal("0")),
            exposure_return_observation(2, asset_return=Decimal("0")),
            exposure_return_observation(3, asset_return=Decimal("0")),
        )
    )

    assert tuple(observation.asset_cumulative_return for observation in result) == (
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
    )
    assert tuple(observation.exposure_cumulative_return for observation in result) == (
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
    )


def test_simple_two_return_path_compounds_asset_and_exposure_returns() -> None:
    result = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=Decimal("0.10")),
            exposure_return_observation(2, asset_return=Decimal("-0.05")),
        )
    )

    assert result[1].asset_cumulative_return == Decimal("0.10")
    assert result[2].asset_cumulative_return == Decimal("0.045")
    assert result[2].exposure_cumulative_return == Decimal("0.045")


def test_exposure_cumulative_return_uses_exposure_return_not_asset_return() -> None:
    result = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(
                1,
                current_exposure=0,
                asset_return=Decimal("0.10"),
            ),
            exposure_return_observation(2, asset_return=Decimal("0.10")),
        )
    )

    assert result[1].asset_cumulative_return == Decimal("0.10")
    assert result[1].exposure_cumulative_return == Decimal("0")
    assert result[2].asset_cumulative_return == Decimal("0.21")
    assert result[2].exposure_cumulative_return == Decimal("0.10")


def test_zero_current_exposure_keeps_exposure_cumulative_return_unchanged() -> None:
    result = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(
                1,
                current_exposure=0,
                asset_return=Decimal("0.25"),
            ),
        )
    )

    assert result[1].asset_cumulative_return == Decimal("0.25")
    assert result[1].exposure_return == Decimal("0")
    assert result[1].exposure_cumulative_return == Decimal("0")


def test_first_row_remains_cumulative_baseline() -> None:
    source = baseline_exposure_return(0)

    result = build_cumulative_return_path((source,))

    assert result[0].return_available is source.return_available
    assert result[0].asset_return is source.asset_return
    assert result[0].exposure_return is source.exposure_return
    assert result[0].asset_cumulative_return == Decimal("0")
    assert result[0].exposure_cumulative_return == Decimal("0")
    assert "baseline" in result[0].reason


def test_return_unavailable_rows_preserve_prior_cumulative_values() -> None:
    result = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=Decimal("0.10")),
            exposure_return_observation(
                2,
                return_available=False,
                reason="return_unavailable",
            ),
        )
    )

    assert result[2].asset_return is None
    assert result[2].exposure_return is None
    assert result[2].asset_cumulative_return == result[1].asset_cumulative_return
    assert result[2].exposure_cumulative_return == (
        result[1].exposure_cumulative_return
    )


def test_previous_exposure_integration_preserves_breakout_row_exposure_baseline() -> None:
    values = value_series(("10", "10", "30", "33"))
    moving_average_observations = build_simple_moving_average_observations(
        values,
        window=3,
    )
    states = build_previous_exposure_states(moving_average_observations)
    exposure_returns = build_exposure_applied_returns(values, states)

    result = build_cumulative_return_path(exposure_returns)

    assert moving_average_observations[2].is_above_moving_average is True
    assert exposure_returns[2].asset_return == Decimal("2")
    assert exposure_returns[2].exposure_return == Decimal("0")
    assert result[2].exposure_cumulative_return == result[1].exposure_cumulative_return
    assert exposure_returns[3].current_exposure == states[2].next_exposure
    assert exposure_returns[3].exposure_return == Decimal("0.1")
    assert result[3].exposure_cumulative_return == (
        (Decimal("1") + result[2].exposure_cumulative_return)
        * (Decimal("1") + exposure_returns[3].exposure_return)
        - Decimal("1")
    )


def test_changing_future_loss_does_not_change_prior_cumulative_observations() -> None:
    base = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=Decimal("0.10")),
            exposure_return_observation(2, asset_return=Decimal("0.05")),
            exposure_return_observation(3, asset_return=Decimal("-0.10")),
        )
    )
    revised_future = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=Decimal("0.10")),
            exposure_return_observation(2, asset_return=Decimal("0.05")),
            exposure_return_observation(3, asset_return=Decimal("-0.50")),
        )
    )

    assert base[:3] == revised_future[:3]
    assert base[3] != revised_future[3]


def test_future_breakout_does_not_affect_earlier_cumulative_rows() -> None:
    flat_values = value_series(("10", "10", "10", "10", "10"))
    breakout_values = value_series(("10", "10", "10", "10", "30"))
    flat_states = build_previous_exposure_states(
        build_simple_moving_average_observations(flat_values, window=3)
    )
    breakout_states = build_previous_exposure_states(
        build_simple_moving_average_observations(breakout_values, window=3)
    )
    flat_returns = build_exposure_applied_returns(flat_values, flat_states)
    breakout_returns = build_exposure_applied_returns(
        breakout_values,
        breakout_states,
    )

    flat = build_cumulative_return_path(flat_returns)
    breakout = build_cumulative_return_path(breakout_returns)

    assert flat[:4] == breakout[:4]
    assert breakout_returns[4].current_exposure == 0
    assert breakout_returns[4].exposure_return == Decimal("0")
    assert breakout[4].exposure_cumulative_return == breakout[3].exposure_cumulative_return


def test_decimal_cumulative_returns_are_preserved_without_float_coercion() -> None:
    one_third = Decimal("1") / Decimal("3")
    expected = (Decimal("1") + Decimal("0")) * (Decimal("1") + one_third) - Decimal(
        "1"
    )

    result = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=one_third),
        )
    )

    assert result[1].asset_cumulative_return == expected
    assert isinstance(result[1].asset_cumulative_return, Decimal)
    assert isinstance(result[1].exposure_cumulative_return, Decimal)
    assert result[1].asset_cumulative_return != Decimal(str((4 - 3) / 3))


def test_repeated_calls_are_equal_and_source_return_observations_are_not_mutated() -> None:
    returns = (
        baseline_exposure_return(0),
        exposure_return_observation(1, asset_return=Decimal("0.10")),
        exposure_return_observation(2, asset_return=Decimal("-0.05")),
    )
    original_fields = tuple(
        (
            observation.observation_date,
            observation.value,
            observation.current_exposure,
            observation.asset_return,
            observation.exposure_return,
            observation.return_available,
            observation.reason,
        )
        for observation in returns
    )

    first = build_cumulative_return_path(returns)
    second = build_cumulative_return_path(tuple(returns))

    assert first == second
    assert tuple(
        (
            observation.observation_date,
            observation.value,
            observation.current_exposure,
            observation.asset_return,
            observation.exposure_return,
            observation.return_available,
            observation.reason,
        )
        for observation in returns
    ) == original_fields


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


def test_cumulative_return_contract_has_no_trading_or_performance_fields() -> None:
    field_names = {field.name for field in fields(CumulativeReturnObservation)}

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
