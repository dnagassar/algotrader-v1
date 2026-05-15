import ast
from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime
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


MODULE_PATH = Path("src/algotrader/research/replay.py")

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


class CustomDate(date):
    pass


def manifest(**overrides: object) -> ResearchFixtureManifest:
    values: dict[str, object] = {
        "fixture_id": "synthetic-replay-fixture-001",
        "fixture_kind": "synthetic",
        "description": "Tiny deterministic synthetic replay example.",
        "source_name": "project synthetic fixture",
        "source_type": "synthetic",
        "retrieval_date": None,
        "data_start": date(2026, 1, 1),
        "data_end": date(2026, 1, 3),
        "fields": ("observation_date", "synthetic_close"),
        "checksum": "sha256:synthetic-replay-fixture-001",
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


def test_replay_contracts_are_frozen_slotted_and_metadata_only() -> None:
    item = replay_point(date(2026, 1, 1), Decimal("100"))
    snapshot = build_synthetic_replay_snapshot(
        manifest(),
        (item,),
        date(2026, 1, 1),
    )

    assert tuple(field.name for field in fields(SyntheticReplayPoint)) == (
        "observation",
        "value",
    )
    assert tuple(field.name for field in fields(SyntheticReplaySnapshot)) == (
        "manifest",
        "asof_date",
        "available_points",
        "returns",
    )
    assert hasattr(SyntheticReplayPoint, "__slots__")
    assert hasattr(SyntheticReplaySnapshot, "__slots__")
    assert not hasattr(item, "__dict__")
    assert not hasattr(snapshot, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.value = Decimal("101")
    with pytest.raises(FrozenInstanceError):
        snapshot.asof_date = date(2026, 1, 2)


def test_build_synthetic_replay_snapshot_filters_and_returns_metadata() -> None:
    fixture = manifest()
    first = replay_point(date(2026, 1, 1), Decimal("100"))
    second = replay_point(date(2026, 1, 2), Decimal("110"))
    hidden = replay_point(date(2026, 1, 3), Decimal("121"), date(2026, 1, 5))

    snapshot = build_synthetic_replay_snapshot(
        fixture,
        (first, second, hidden),
        date(2026, 1, 2),
    )

    assert isinstance(snapshot, SyntheticReplaySnapshot)
    assert snapshot.manifest is fixture
    assert snapshot.asof_date == date(2026, 1, 2)
    assert snapshot.available_points == (first, second)
    assert snapshot.available_points[0] is first
    assert snapshot.available_points[1] is second
    assert snapshot.returns == (Decimal("0.1"),)


def test_asof_filtering_uses_available_after_without_lookahead() -> None:
    first = replay_point(date(2026, 2, 1), Decimal("100"), date(2026, 2, 3))
    second = replay_point(date(2026, 2, 2), Decimal("110"), date(2026, 2, 2))
    third = replay_point(date(2026, 2, 3), Decimal("121"), date(2026, 2, 3))

    early_snapshot = build_synthetic_replay_snapshot(
        manifest(data_start=date(2026, 2, 1), data_end=date(2026, 2, 3)),
        (first, second, third),
        date(2026, 2, 2),
    )
    later_snapshot = build_synthetic_replay_snapshot(
        manifest(data_start=date(2026, 2, 1), data_end=date(2026, 2, 3)),
        (first, second, third),
        date(2026, 2, 3),
    )

    assert early_snapshot.available_points == (second,)
    assert early_snapshot.returns == ()
    assert later_snapshot.available_points == (first, second, third)
    assert later_snapshot.returns == (Decimal("0.1"), Decimal("0.1"))


def test_returns_are_constructed_from_available_values_only() -> None:
    first = replay_point(date(2026, 3, 1), Decimal("100"))
    second = replay_point(date(2026, 3, 2), Decimal("125"))
    third = replay_point(date(2026, 3, 3), Decimal("100"))
    hidden = replay_point(date(2026, 3, 4), Decimal("200"), date(2026, 3, 9))

    snapshot = build_synthetic_replay_snapshot(
        manifest(data_start=date(2026, 3, 1), data_end=date(2026, 3, 4)),
        (first, second, third, hidden),
        date(2026, 3, 4),
    )

    assert snapshot.available_points == (first, second, third)
    assert snapshot.returns == (Decimal("0.25"), Decimal("-0.2"))


def test_zero_or_one_available_point_produces_empty_returns() -> None:
    first = replay_point(date(2026, 4, 1), Decimal("100"), date(2026, 4, 2))
    second = replay_point(date(2026, 4, 2), Decimal("101"), date(2026, 4, 3))
    fixture = manifest(data_start=date(2026, 4, 1), data_end=date(2026, 4, 2))

    zero_snapshot = build_synthetic_replay_snapshot(
        fixture,
        (first, second),
        date(2026, 4, 1),
    )
    one_snapshot = build_synthetic_replay_snapshot(
        fixture,
        (first, second),
        date(2026, 4, 2),
    )

    assert zero_snapshot.available_points == ()
    assert zero_snapshot.returns == ()
    assert one_snapshot.available_points == (first,)
    assert one_snapshot.returns == ()


def test_snapshot_outputs_are_immutable_tuples() -> None:
    first = replay_point(date(2026, 5, 1), Decimal("100"))
    second = replay_point(date(2026, 5, 2), Decimal("105"))
    snapshot = build_synthetic_replay_snapshot(
        manifest(data_start=date(2026, 5, 1), data_end=date(2026, 5, 2)),
        [first, second],
        date(2026, 5, 2),
    )

    assert isinstance(snapshot.available_points, tuple)
    assert isinstance(snapshot.returns, tuple)
    with pytest.raises(TypeError):
        snapshot.available_points[0] = second
    with pytest.raises(TypeError):
        snapshot.returns[0] = Decimal("0")


def test_to_dict_returns_deterministic_json_compatible_metadata() -> None:
    fixture = manifest(retrieval_date=date(2026, 5, 14))
    first = replay_point(date(2026, 6, 1), Decimal("100.00"))
    second = replay_point(date(2026, 6, 2), Decimal("102.50"))
    snapshot = build_synthetic_replay_snapshot(
        fixture,
        (first, second),
        date(2026, 6, 2),
    )

    payload = snapshot.to_dict()

    assert tuple(payload) == (
        "manifest",
        "asof_date",
        "available_points",
        "returns",
    )
    assert payload["manifest"] == fixture.to_dict()
    assert payload["asof_date"] == "2026-06-02"
    assert payload["available_points"] == [
        {
            "observation_date": "2026-06-01",
            "available_after": "2026-06-01",
            "value": "100.00",
        },
        {
            "observation_date": "2026-06-02",
            "available_after": "2026-06-02",
            "value": "102.50",
        },
    ]
    assert tuple(payload["available_points"][0]) == (
        "observation_date",
        "available_after",
        "value",
    )
    assert payload["returns"] == ["0.025"]
    assert isinstance(payload["available_points"][0]["value"], str)
    assert isinstance(payload["returns"][0], str)


def test_to_dict_lists_do_not_mutate_snapshot_or_manifest() -> None:
    fixture = manifest()
    first = replay_point(date(2026, 7, 1), Decimal("100"))
    second = replay_point(date(2026, 7, 2), Decimal("110"))
    snapshot = build_synthetic_replay_snapshot(
        fixture,
        (first, second),
        date(2026, 7, 2),
    )

    payload = snapshot.to_dict()
    payload["available_points"].append(
        {
            "observation_date": "2026-07-03",
            "available_after": "2026-07-03",
            "value": "999",
        }
    )
    payload["returns"].append("9.99")
    payload["manifest"]["fields"].append("late_field")

    assert snapshot.available_points == (first, second)
    assert snapshot.returns == (Decimal("0.1"),)
    assert fixture.fields == ("observation_date", "synthetic_close")


def test_malformed_manifest_is_rejected() -> None:
    with pytest.raises(ValidationError, match="manifest"):
        build_synthetic_replay_snapshot(
            object(),
            (),
            date(2026, 8, 1),
        )


@pytest.mark.parametrize(
    "points",
    (
        (object(),),
        "not replay points",
        None,
    ),
)
def test_malformed_point_sequences_are_rejected(points: object) -> None:
    with pytest.raises(ValidationError):
        build_synthetic_replay_snapshot(
            manifest(),
            points,
            date(2026, 8, 1),
        )


def test_point_observation_must_be_asof_observation() -> None:
    with pytest.raises(ValidationError, match="observation"):
        SyntheticReplayPoint(
            observation=object(),
            value=Decimal("100"),
        )


@pytest.mark.parametrize("value", (100, 100.0, "100", True))
def test_non_decimal_values_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError, match="Decimal"):
        SyntheticReplayPoint(
            observation=obs(date(2026, 9, 1)),
            value=value,
        )


def test_return_construction_validation_is_reused_for_available_values() -> None:
    first = replay_point(date(2026, 10, 1), Decimal("0"))
    second = replay_point(date(2026, 10, 2), Decimal("101"))

    with pytest.raises(ValidationError, match="previous_value"):
        build_synthetic_replay_snapshot(
            manifest(data_start=date(2026, 10, 1), data_end=date(2026, 10, 2)),
            (first, second),
            date(2026, 10, 2),
        )


@pytest.mark.parametrize(
    "points,error_match",
    (
        (
            (
                replay_point(date(2026, 11, 1), Decimal("100")),
                replay_point(date(2026, 11, 1), Decimal("101")),
            ),
            "duplicate",
        ),
        (
            (
                replay_point(date(2026, 11, 2), Decimal("100")),
                replay_point(date(2026, 11, 1), Decimal("101")),
            ),
            "ordered",
        ),
    ),
)
def test_duplicate_or_unordered_observation_dates_are_rejected(
    points: tuple[SyntheticReplayPoint, ...],
    error_match: str,
) -> None:
    with pytest.raises(ValidationError, match=error_match):
        build_synthetic_replay_snapshot(
            manifest(data_start=date(2026, 11, 1), data_end=date(2026, 11, 2)),
            points,
            date(2026, 11, 2),
        )


@pytest.mark.parametrize(
    "asof_date",
    (
        datetime(2026, 12, 1, 12, 0),
        True,
        CustomDate(2026, 12, 1),
        "2026-12-01",
    ),
)
def test_invalid_asof_dates_are_rejected(asof_date: object) -> None:
    with pytest.raises(ValidationError, match="asof_date"):
        build_synthetic_replay_snapshot(
            manifest(data_start=date(2026, 12, 1), data_end=date(2026, 12, 1)),
            (replay_point(date(2026, 12, 1), Decimal("100")),),
            asof_date,
        )


def test_input_identity_is_preserved_where_available() -> None:
    fixture = manifest(data_start=date(2027, 1, 1), data_end=date(2027, 1, 2))
    first_observation = obs(date(2027, 1, 1), date(2027, 1, 1))
    first = SyntheticReplayPoint(first_observation, Decimal("100"))
    second = replay_point(date(2027, 1, 2), Decimal("103"))

    snapshot = build_synthetic_replay_snapshot(
        fixture,
        (first, second),
        date(2027, 1, 2),
    )

    assert snapshot.manifest is fixture
    assert snapshot.available_points[0] is first
    assert snapshot.available_points[0].observation is first_observation
    assert snapshot.available_points[1] is second


def test_input_sequences_are_not_mutated_or_shared() -> None:
    first = replay_point(date(2027, 2, 1), Decimal("100"))
    second = replay_point(date(2027, 2, 2), Decimal("110"))
    late = replay_point(date(2027, 2, 3), Decimal("120"))
    point_items = [first, second]
    original_items = list(point_items)

    snapshot = build_synthetic_replay_snapshot(
        manifest(data_start=date(2027, 2, 1), data_end=date(2027, 2, 3)),
        point_items,
        date(2027, 2, 2),
    )
    point_items.append(late)

    assert original_items == [first, second]
    assert point_items == [first, second, late]
    assert snapshot.available_points == (first, second)


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
