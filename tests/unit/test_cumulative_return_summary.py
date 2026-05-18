import ast
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.cumulative_return_summary import (
    CumulativeReturnPathSummary,
    summarize_cumulative_return_path,
)
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


MODULE_PATH = Path("src/algotrader/research/cumulative_return_summary.py")

_MISSING = object()

_REQUIRED_NON_CLAIMS = (
    "not validated evidence",
    "not a strategy approval",
    "not a trading recommendation",
    "not an approved signal",
    "not paper/live trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
)

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


def valid_summary(**overrides: object) -> CumulativeReturnPathSummary:
    values = {
        "first_observation_date": date(2025, 1, 1),
        "last_observation_date": date(2025, 1, 3),
        "observation_count": 3,
        "available_return_count": 2,
        "unavailable_return_count": 1,
        "final_asset_cumulative_return": Decimal("0.045"),
        "final_exposure_cumulative_return": Decimal("0.045"),
        "has_available_returns": True,
        "limitations": (" research-only caveat ",),
        "non_claims": _REQUIRED_NON_CLAIMS,
    }
    values.update(overrides)
    return CumulativeReturnPathSummary(**values)


def cumulative_observation(
    index: int = 0,
    *,
    asset_return: object = _MISSING,
    exposure_return: object = _MISSING,
    asset_cumulative_return: object = Decimal("0"),
    exposure_cumulative_return: object = Decimal("0"),
    return_available: bool = False,
    observation_date: object = _MISSING,
    reason: str = "initial_cumulative_return_baseline",
) -> CumulativeReturnObservation:
    if observation_date is _MISSING:
        observation_date = date(2025, 1, 1) + timedelta(days=index)

    if return_available:
        checked_asset_return = (
            Decimal("0") if asset_return is _MISSING else asset_return
        )
        checked_exposure_return = (
            checked_asset_return if exposure_return is _MISSING else exposure_return
        )
    else:
        checked_asset_return = None
        checked_exposure_return = None

    return CumulativeReturnObservation(
        observation_date=observation_date,
        asset_return=checked_asset_return,
        exposure_return=checked_exposure_return,
        asset_cumulative_return=asset_cumulative_return,
        exposure_cumulative_return=exposure_cumulative_return,
        return_available=return_available,
        reason=reason,
    )


def exposure_return_observation(
    index: int,
    *,
    current_exposure: int = 1,
    asset_return: object = Decimal("0"),
    return_available: bool = True,
    reason: str = "above_moving_average",
) -> ExposureReturnObservation:
    if return_available:
        exposure_return = Decimal("0") if current_exposure == 0 else asset_return
    else:
        asset_return = None
        exposure_return = None

    return ExposureReturnObservation(
        observation_date=date(2025, 1, 1) + timedelta(days=index),
        value=Decimal("100") + Decimal(index),
        current_exposure=current_exposure,
        asset_return=asset_return,
        exposure_return=exposure_return,
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


def value_series(values: tuple[str, ...]) -> tuple[MovingAverageInput, ...]:
    return tuple(
        MovingAverageInput(
            observation_date=date(2025, 1, 1) + timedelta(days=index),
            value=Decimal(value),
        )
        for index, value in enumerate(values)
    )


def test_summary_is_frozen_and_slotted() -> None:
    summary = valid_summary()

    assert is_dataclass(CumulativeReturnPathSummary)
    assert not hasattr(summary, "__dict__")
    with pytest.raises(FrozenInstanceError):
        summary.observation_count = 4


def test_summary_accepts_valid_summary_and_normalizes_text_tuples() -> None:
    summary = valid_summary(
        limitations=[" research-only summary "],
        non_claims=[" not validated evidence "],
    )

    assert summary.limitations == ("research-only summary",)
    assert summary.non_claims == ("not validated evidence",)
    assert summary.final_asset_cumulative_return == Decimal("0.045")


@pytest.mark.parametrize(
    "field_name",
    ("first_observation_date", "last_observation_date"),
)
def test_summary_rejects_datetime_dates(field_name: str) -> None:
    with pytest.raises(ValidationError, match="plain date"):
        valid_summary(**{field_name: datetime(2025, 1, 1)})


def test_summary_rejects_inverted_date_range() -> None:
    with pytest.raises(ValidationError, match="last_observation_date"):
        valid_summary(
            first_observation_date=date(2025, 1, 3),
            last_observation_date=date(2025, 1, 1),
        )


@pytest.mark.parametrize("bad_value", (0, -1, True, Decimal("1")))
def test_summary_rejects_non_positive_observation_count(bad_value: object) -> None:
    with pytest.raises(ValidationError, match="observation_count"):
        valid_summary(observation_count=bad_value)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("available_return_count", -1),
        ("available_return_count", True),
        ("unavailable_return_count", -1),
        ("unavailable_return_count", False),
    ),
)
def test_summary_rejects_negative_or_bool_return_counts(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        valid_summary(**{field_name: bad_value})


def test_summary_rejects_mismatched_count_totals() -> None:
    with pytest.raises(ValidationError, match="observation_count"):
        valid_summary(
            observation_count=3,
            available_return_count=1,
            unavailable_return_count=1,
        )


@pytest.mark.parametrize(
    ("available_return_count", "unavailable_return_count", "has_available_returns"),
    (
        (2, 1, False),
        (0, 3, True),
    ),
)
def test_summary_rejects_inconsistent_has_available_returns(
    available_return_count: int,
    unavailable_return_count: int,
    has_available_returns: bool,
) -> None:
    with pytest.raises(ValidationError, match="has_available_returns"):
        valid_summary(
            available_return_count=available_return_count,
            unavailable_return_count=unavailable_return_count,
            has_available_returns=has_available_returns,
        )


@pytest.mark.parametrize(
    "field_name",
    ("final_asset_cumulative_return", "final_exposure_cumulative_return"),
)
@pytest.mark.parametrize(
    "bad_value",
    ("0", 0, 0.0, True, Decimal("NaN"), Decimal("Infinity")),
)
def test_summary_rejects_non_decimal_final_cumulative_values(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        valid_summary(**{field_name: bad_value})


@pytest.mark.parametrize("field_name", ("limitations", "non_claims"))
@pytest.mark.parametrize(
    "bad_value",
    ("text", (), ("",), ("   ",), (1,), {"x": "y"}, {"x"}),
)
def test_summary_rejects_malformed_limitations_and_non_claims(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        valid_summary(**{field_name: bad_value})


def test_summary_to_dict_returns_json_compatible_primitives() -> None:
    payload = valid_summary().to_dict()

    assert payload == {
        "first_observation_date": "2025-01-01",
        "last_observation_date": "2025-01-03",
        "observation_count": 3,
        "available_return_count": 2,
        "unavailable_return_count": 1,
        "final_asset_cumulative_return": "0.045",
        "final_exposure_cumulative_return": "0.045",
        "has_available_returns": True,
        "limitations": ["research-only caveat"],
        "non_claims": list(_REQUIRED_NON_CLAIMS),
    }
    _assert_json_primitive(payload)


def test_builder_rejects_empty_path() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        summarize_cumulative_return_path(())


def test_builder_rejects_non_cumulative_return_observation_entries() -> None:
    with pytest.raises(ValidationError, match="CumulativeReturnObservation"):
        summarize_cumulative_return_path((cumulative_observation(), object()))


def test_builder_rejects_duplicate_dates() -> None:
    path = (
        cumulative_observation(0),
        cumulative_observation(0),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        summarize_cumulative_return_path(path)


def test_builder_rejects_unordered_dates() -> None:
    path = (
        cumulative_observation(1),
        cumulative_observation(0),
    )

    with pytest.raises(ValidationError, match="strictly increasing"):
        summarize_cumulative_return_path(path)


def test_builder_accepts_any_iterable() -> None:
    path = (
        observation
        for observation in (
            cumulative_observation(0),
            cumulative_observation(
                1,
                asset_return=Decimal("0.1"),
                exposure_return=Decimal("0.1"),
                asset_cumulative_return=Decimal("0.1"),
                exposure_cumulative_return=Decimal("0.1"),
                return_available=True,
                reason="return_compounded",
            ),
        )
    )

    summary = summarize_cumulative_return_path(path)

    assert summary.observation_count == 2
    assert summary.final_asset_cumulative_return == Decimal("0.1")


def test_builder_does_not_mutate_source_observations() -> None:
    path = (
        cumulative_observation(0),
        cumulative_observation(
            1,
            asset_return=Decimal("0.1"),
            exposure_return=Decimal("0.1"),
            asset_cumulative_return=Decimal("0.1"),
            exposure_cumulative_return=Decimal("0.1"),
            return_available=True,
            reason="return_compounded",
        ),
    )
    original_fields = tuple(
        (
            observation.observation_date,
            observation.asset_return,
            observation.exposure_return,
            observation.asset_cumulative_return,
            observation.exposure_cumulative_return,
            observation.return_available,
            observation.reason,
        )
        for observation in path
    )

    first = summarize_cumulative_return_path(path)
    second = summarize_cumulative_return_path(tuple(path))

    assert first == second
    assert tuple(
        (
            observation.observation_date,
            observation.asset_return,
            observation.exposure_return,
            observation.asset_cumulative_return,
            observation.exposure_cumulative_return,
            observation.return_available,
            observation.reason,
        )
        for observation in path
    ) == original_fields


def test_flat_zero_return_path_summarizes_zero_final_cumulative_returns() -> None:
    path = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=Decimal("0")),
            exposure_return_observation(2, asset_return=Decimal("0")),
        )
    )

    summary = summarize_cumulative_return_path(path)

    assert summary.final_asset_cumulative_return == Decimal("0")
    assert summary.final_exposure_cumulative_return == Decimal("0")


def test_mixed_return_path_summarizes_counts_dates_and_last_row_values() -> None:
    path = build_cumulative_return_path(
        (
            baseline_exposure_return(0),
            exposure_return_observation(1, asset_return=Decimal("0.10")),
            exposure_return_observation(2, asset_return=Decimal("-0.05")),
            exposure_return_observation(
                3,
                return_available=False,
                reason="return_unavailable",
            ),
        )
    )

    summary = summarize_cumulative_return_path(path)

    assert summary.first_observation_date == date(2025, 1, 1)
    assert summary.last_observation_date == date(2025, 1, 4)
    assert summary.observation_count == 4
    assert summary.available_return_count == 2
    assert summary.unavailable_return_count == 2
    assert summary.has_available_returns is True
    assert summary.final_asset_cumulative_return == path[-1].asset_cumulative_return
    assert summary.final_exposure_cumulative_return == (
        path[-1].exposure_cumulative_return
    )
    assert summary.final_asset_cumulative_return == Decimal("0.045")


def test_has_available_returns_is_false_when_no_rows_have_available_returns() -> None:
    path = (
        cumulative_observation(0),
        cumulative_observation(1, reason="return_unavailable"),
    )

    summary = summarize_cumulative_return_path(path)

    assert summary.available_return_count == 0
    assert summary.unavailable_return_count == 2
    assert summary.has_available_returns is False


def test_has_available_returns_is_true_when_any_row_has_available_returns() -> None:
    path = (
        cumulative_observation(0),
        cumulative_observation(
            1,
            asset_return=Decimal("0"),
            exposure_return=Decimal("0"),
            return_available=True,
            reason="return_compounded",
        ),
    )

    summary = summarize_cumulative_return_path(path)

    assert summary.available_return_count == 1
    assert summary.has_available_returns is True


def test_summary_integration_preserves_previous_exposure_convention() -> None:
    values = value_series(("10", "10", "30", "33"))
    moving_average_observations = build_simple_moving_average_observations(
        values,
        window=3,
    )
    states = build_previous_exposure_states(moving_average_observations)
    exposure_returns = build_exposure_applied_returns(values, states)
    path = build_cumulative_return_path(exposure_returns)

    summary = summarize_cumulative_return_path(path)

    assert summary.final_asset_cumulative_return == path[-1].asset_cumulative_return
    assert summary.final_exposure_cumulative_return == (
        path[-1].exposure_cumulative_return
    )
    assert moving_average_observations[2].is_above_moving_average is True
    assert exposure_returns[2].asset_return == Decimal("2")
    assert exposure_returns[2].exposure_return == Decimal("0")
    assert path[2].exposure_cumulative_return == Decimal("0")
    assert exposure_returns[3].current_exposure == states[2].next_exposure
    assert summary.final_exposure_cumulative_return == Decimal("0.1")


def test_builder_adds_required_research_only_caveats_and_non_claims() -> None:
    summary = summarize_cumulative_return_path((cumulative_observation(),))

    assert any("research-only" in item for item in summary.limitations)
    assert all(claim in summary.non_claims for claim in _REQUIRED_NON_CLAIMS)


def test_to_dict_is_deterministic_and_json_round_trips_byte_identically() -> None:
    summary = valid_summary()
    first_payload = summary.to_dict()
    second_payload = summary.to_dict()

    assert first_payload == second_payload
    first_encoded = json.dumps(first_payload, separators=(",", ":"))
    second_encoded = json.dumps(second_payload, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(first_encoded), separators=(",", ":"))

    assert first_encoded == second_encoded
    assert round_tripped == first_encoded
    assert " at 0x" not in first_encoded
    assert "Decimal(" not in first_encoded
    assert "datetime." not in first_encoded


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


def test_summary_contract_has_only_metadata_fields_and_no_forbidden_metrics() -> None:
    field_names = {field.name for field in fields(CumulativeReturnPathSummary)}

    assert field_names == {
        "first_observation_date",
        "last_observation_date",
        "observation_count",
        "available_return_count",
        "unavailable_return_count",
        "final_asset_cumulative_return",
        "final_exposure_cumulative_return",
        "has_available_returns",
        "limitations",
        "non_claims",
    }
    assert all(
        forbidden_part not in field_name
        for field_name in field_names
        for forbidden_part in _FORBIDDEN_FIELD_PARTS
    )


def _assert_json_primitive(value: object) -> None:
    if isinstance(value, dict):
        assert all(type(key) is str for key in value)
        for item in value.values():
            _assert_json_primitive(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_json_primitive(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


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
