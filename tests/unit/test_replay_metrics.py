import ast
from dataclasses import FrozenInstanceError, fields
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.asof import AsofObservation
from algotrader.research.fixture_manifest import ResearchFixtureManifest
from algotrader.research.replay import (
    SyntheticReplayPoint,
    SyntheticReplaySnapshot,
    build_synthetic_replay_snapshot,
)
from algotrader.research.replay_metrics import (
    SyntheticReplaySummary,
    summarize_synthetic_replay_snapshot,
)


MODULE_PATH = Path("src/algotrader/research/replay_metrics.py")

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
    "ValidatedResearchArtifact",
    "ValidatedSignalDefinition",
    "alpaca",
    "benchmark",
    "broker",
    "cash",
    "download",
    "evaluator",
    "execution",
    "execution_plan",
    "fill",
    "portfolio",
    "ranking",
    "request",
    "runtime",
    "signal_definition",
    "strategy",
    "submit_order",
    "symbol",
    "trading_ready",
    "validated",
    "validation_status",
    "vectorbt",
    "vendor",
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


def manifest(**overrides: object) -> ResearchFixtureManifest:
    values: dict[str, object] = {
        "fixture_id": "synthetic-replay-metrics-fixture-001",
        "fixture_kind": "synthetic",
        "description": "Tiny deterministic synthetic replay metrics example.",
        "source_name": "project synthetic fixture",
        "source_type": "synthetic",
        "retrieval_date": None,
        "data_start": date(2026, 1, 1),
        "data_end": date(2026, 1, 3),
        "fields": ("observation_date", "synthetic_close"),
        "checksum": "sha256:synthetic-replay-metrics-fixture-001",
        "normal_pytest_eligible": True,
        "redistribution_safe": True,
        "limitations": ("synthetic values only",),
        "non_claims": ("does not validate any trading result",),
    }
    values.update(overrides)
    return ResearchFixtureManifest(**values)


def obs(
    observation_date: date,
    available_after: date | None = None,
) -> AsofObservation:
    return AsofObservation(
        observation_date=observation_date,
        available_after=available_after or observation_date,
    )


def replay_point(
    observation_date: date,
    value: Decimal,
    available_after: date | None = None,
) -> SyntheticReplayPoint:
    return SyntheticReplayPoint(
        observation=obs(observation_date, available_after),
        value=value,
    )


def replay_snapshot(
    points: tuple[SyntheticReplayPoint, ...],
    asof_date: date,
) -> SyntheticReplaySnapshot:
    return build_synthetic_replay_snapshot(
        manifest(),
        points,
        asof_date,
    )


def summary(**overrides: object) -> SyntheticReplaySummary:
    values: dict[str, object] = {
        "point_count": 1,
        "return_count": 0,
        "starting_value": Decimal("100"),
        "ending_value": Decimal("100"),
        "cumulative_simple_return": None,
        "min_return": None,
        "max_return": None,
        "mean_return": None,
    }
    values.update(overrides)
    return SyntheticReplaySummary(**values)


def test_summary_from_zero_available_points() -> None:
    first = replay_point(date(2026, 1, 1), Decimal("100"), date(2026, 1, 2))
    snapshot = replay_snapshot((first,), date(2026, 1, 1))

    result = summarize_synthetic_replay_snapshot(snapshot)

    assert result == SyntheticReplaySummary(
        point_count=0,
        return_count=0,
        starting_value=None,
        ending_value=None,
        cumulative_simple_return=None,
        min_return=None,
        max_return=None,
        mean_return=None,
    )


def test_summary_from_one_available_point() -> None:
    first = replay_point(date(2026, 2, 1), Decimal("100.25"))
    snapshot = replay_snapshot((first,), date(2026, 2, 1))

    result = summarize_synthetic_replay_snapshot(snapshot)

    assert result.point_count == 1
    assert result.return_count == 0
    assert result.starting_value == Decimal("100.25")
    assert result.ending_value == Decimal("100.25")
    assert result.cumulative_simple_return is None
    assert result.min_return is None
    assert result.max_return is None
    assert result.mean_return is None


def test_summary_from_multiple_available_points() -> None:
    first = replay_point(date(2026, 3, 1), Decimal("100.00"))
    second = replay_point(date(2026, 3, 2), Decimal("110.00"))
    third = replay_point(date(2026, 3, 3), Decimal("99.00"))
    snapshot = replay_snapshot((first, second, third), date(2026, 3, 3))

    result = summarize_synthetic_replay_snapshot(snapshot)

    assert result.point_count == 3
    assert result.return_count == 2
    assert result.starting_value == Decimal("100.00")
    assert result.ending_value == Decimal("99.00")
    assert result.cumulative_simple_return == Decimal("-0.01")
    assert result.min_return == Decimal("-0.1")
    assert result.max_return == Decimal("0.1")
    assert result.mean_return == Decimal("0.0")


def test_summary_uses_available_points_and_returns_only() -> None:
    first = replay_point(date(2026, 4, 1), Decimal("100"))
    second = replay_point(date(2026, 4, 2), Decimal("125"))
    hidden = replay_point(date(2026, 4, 3), Decimal("999"), date(2026, 4, 9))
    snapshot = replay_snapshot((first, second, hidden), date(2026, 4, 2))

    result = summarize_synthetic_replay_snapshot(snapshot)

    assert snapshot.available_points == (first, second)
    assert result.point_count == 2
    assert result.return_count == 1
    assert result.ending_value == Decimal("125")
    assert result.cumulative_simple_return == Decimal("0.25")
    assert result.min_return == Decimal("0.25")
    assert result.max_return == Decimal("0.25")
    assert result.mean_return == Decimal("0.25")


def test_decimal_precision_is_preserved() -> None:
    first = replay_point(date(2026, 5, 1), Decimal("100.0000"))
    second = replay_point(date(2026, 5, 2), Decimal("100.0100"))
    snapshot = replay_snapshot((first, second), date(2026, 5, 2))

    result = summarize_synthetic_replay_snapshot(snapshot)

    assert result.cumulative_simple_return == Decimal("0.0001")
    assert result.min_return == Decimal("0.0001")
    assert result.max_return == Decimal("0.0001")
    assert result.mean_return == Decimal("0.0001")
    assert result.mean_return.as_tuple().exponent == -4


def test_summary_is_frozen_slotted_and_minimal() -> None:
    item = summary()

    assert tuple(field.name for field in fields(SyntheticReplaySummary)) == (
        "point_count",
        "return_count",
        "starting_value",
        "ending_value",
        "cumulative_simple_return",
        "min_return",
        "max_return",
        "mean_return",
    )
    assert hasattr(SyntheticReplaySummary, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.return_count = 2


def test_to_dict_returns_deterministic_json_compatible_metadata() -> None:
    item = SyntheticReplaySummary(
        point_count=3,
        return_count=2,
        starting_value=Decimal("100.00"),
        ending_value=Decimal("99.00"),
        cumulative_simple_return=Decimal("-0.01"),
        min_return=Decimal("-0.1"),
        max_return=Decimal("0.1"),
        mean_return=Decimal("0.0"),
    )

    payload = item.to_dict()

    assert tuple(payload) == (
        "point_count",
        "return_count",
        "starting_value",
        "ending_value",
        "cumulative_simple_return",
        "min_return",
        "max_return",
        "mean_return",
    )
    assert payload == {
        "point_count": 3,
        "return_count": 2,
        "starting_value": "100.00",
        "ending_value": "99.00",
        "cumulative_simple_return": "-0.01",
        "min_return": "-0.1",
        "max_return": "0.1",
        "mean_return": "0.0",
    }


def test_to_dict_serializes_none_values_as_none() -> None:
    payload = summary(
        point_count=0,
        starting_value=None,
        ending_value=None,
    ).to_dict()

    assert payload["starting_value"] is None
    assert payload["ending_value"] is None
    assert payload["cumulative_simple_return"] is None
    assert payload["min_return"] is None
    assert payload["max_return"] is None
    assert payload["mean_return"] is None


@pytest.mark.parametrize(
    "field_name,value,error_match",
    (
        ("point_count", True, "integer"),
        ("return_count", False, "integer"),
        ("point_count", -1, "zero or greater"),
        ("return_count", -1, "zero or greater"),
        ("point_count", Decimal("1"), "integer"),
    ),
)
def test_direct_summary_rejects_malformed_counts(
    field_name: str,
    value: object,
    error_match: str,
) -> None:
    with pytest.raises(ValidationError, match=error_match):
        summary(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    (
        "starting_value",
        "ending_value",
        "cumulative_simple_return",
        "min_return",
        "max_return",
        "mean_return",
    ),
)
def test_direct_summary_rejects_invalid_decimal_fields(field_name: str) -> None:
    with pytest.raises(ValidationError, match=field_name):
        summary(**{field_name: "0.1"})


def test_malformed_snapshot_is_rejected() -> None:
    with pytest.raises(ValidationError, match="snapshot"):
        summarize_synthetic_replay_snapshot(object())


def test_inconsistent_snapshot_returns_without_points_are_rejected() -> None:
    snapshot = SyntheticReplaySnapshot(
        manifest=manifest(),
        asof_date=date(2026, 6, 1),
        available_points=(),
        returns=(Decimal("0.1"),),
    )

    with pytest.raises(ValidationError, match="available point"):
        summarize_synthetic_replay_snapshot(snapshot)


def test_snapshot_and_points_are_not_mutated() -> None:
    first = replay_point(date(2026, 7, 1), Decimal("100"))
    second = replay_point(date(2026, 7, 2), Decimal("105"))
    snapshot = replay_snapshot((first, second), date(2026, 7, 2))
    original_available_points = snapshot.available_points
    original_returns = snapshot.returns

    result = summarize_synthetic_replay_snapshot(snapshot)

    assert result.point_count == 2
    assert snapshot.available_points is original_available_points
    assert snapshot.returns is original_returns
    assert snapshot.available_points[0] is first
    assert snapshot.available_points[1] is second
    assert first.value == Decimal("100")
    assert second.value == Decimal("105")


def test_module_imports_no_trading_path_vendor_network_or_data_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_module_references_no_strategy_signal_evaluator_or_trading_path_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_module_makes_no_io_network_broker_vendor_or_ingestion_calls() -> None:
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
