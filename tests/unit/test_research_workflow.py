import ast
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
from algotrader.research.replay_metrics import summarize_synthetic_replay_snapshot
from algotrader.research.replay_result import (
    SyntheticResearchResult,
    build_synthetic_research_result,
)
from algotrader.research.workflow import build_synthetic_research_workflow_result


MODULE_PATH = Path("src/algotrader/research/workflow.py")

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

_FORBIDDEN_RESULT_FIELDS = {
    "account",
    "approval",
    "backtest",
    "benchmark",
    "broker",
    "cash",
    "credential",
    "fill",
    "order",
    "portfolio",
    "profit",
    "profitability",
    "runtime",
    "strategy",
    "trade",
    "trading",
    "validation",
}


class CustomDate(date):
    pass


def manifest(**overrides: object) -> ResearchFixtureManifest:
    values: dict[str, object] = {
        "fixture_id": "synthetic-research-workflow-fixture-001",
        "fixture_kind": "synthetic",
        "description": "Tiny deterministic synthetic research workflow example.",
        "source_name": "project synthetic fixture",
        "source_type": "synthetic",
        "retrieval_date": None,
        "data_start": date(2026, 1, 1),
        "data_end": date(2026, 1, 4),
        "fields": ("observation_date", "synthetic_close"),
        "checksum": "sha256:synthetic-research-workflow-fixture-001",
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


def workflow_points() -> tuple[SyntheticReplayPoint, ...]:
    return (
        replay_point(date(2026, 1, 1), Decimal("100.00")),
        replay_point(date(2026, 1, 2), Decimal("110.00")),
        replay_point(date(2026, 1, 3), Decimal("121.00")),
        replay_point(date(2026, 1, 4), Decimal("999.00"), date(2026, 1, 9)),
    )


def test_workflow_builds_synthetic_research_result() -> None:
    fixture = manifest()
    points = workflow_points()

    result = build_synthetic_research_workflow_result(
        fixture,
        points,
        date(2026, 1, 3),
    )

    assert isinstance(result, SyntheticResearchResult)
    assert isinstance(result.snapshot, SyntheticReplaySnapshot)
    assert result.snapshot.manifest is fixture
    assert result.snapshot.asof_date == date(2026, 1, 3)
    assert result.snapshot.available_points == points[:3]
    assert result.snapshot.available_points[0] is points[0]
    assert result.snapshot.available_points[1] is points[1]
    assert result.snapshot.available_points[2] is points[2]
    assert result.snapshot.returns == (Decimal("0.1"), Decimal("0.1"))


def test_workflow_matches_existing_snapshot_and_result_builders() -> None:
    fixture = manifest()
    points = workflow_points()
    expected_snapshot = build_synthetic_replay_snapshot(
        fixture,
        points,
        date(2026, 1, 3),
    )
    expected_result = build_synthetic_research_result(expected_snapshot)

    result = build_synthetic_research_workflow_result(
        fixture,
        points,
        date(2026, 1, 3),
    )

    assert result == expected_result
    assert result.snapshot == expected_snapshot
    assert result.summary == summarize_synthetic_replay_snapshot(result.snapshot)
    assert result.summary.point_count == 3
    assert result.summary.return_count == 2
    assert result.summary.starting_value == Decimal("100.00")
    assert result.summary.ending_value == Decimal("121.00")
    assert result.summary.cumulative_simple_return == Decimal("0.21")
    assert result.summary.mean_return == Decimal("0.1")


def test_asof_filtering_and_returns_use_available_points_only() -> None:
    fixture = manifest(data_start=date(2026, 2, 1), data_end=date(2026, 2, 4))
    first = replay_point(date(2026, 2, 1), Decimal("100"), date(2026, 2, 3))
    second = replay_point(date(2026, 2, 2), Decimal("110"), date(2026, 2, 2))
    third = replay_point(date(2026, 2, 3), Decimal("121"), date(2026, 2, 3))
    hidden = replay_point(date(2026, 2, 4), Decimal("200"), date(2026, 2, 9))

    early_result = build_synthetic_research_workflow_result(
        fixture,
        (first, second, third, hidden),
        date(2026, 2, 2),
    )
    later_result = build_synthetic_research_workflow_result(
        fixture,
        (first, second, third, hidden),
        date(2026, 2, 3),
    )

    assert early_result.snapshot.available_points == (second,)
    assert early_result.snapshot.returns == ()
    assert early_result.summary.point_count == 1
    assert early_result.summary.return_count == 0
    assert later_result.snapshot.available_points == (first, second, third)
    assert later_result.snapshot.returns == (Decimal("0.1"), Decimal("0.1"))
    assert later_result.summary.point_count == 3
    assert later_result.summary.return_count == 2


def test_empty_point_sequence_produces_zero_point_result() -> None:
    result = build_synthetic_research_workflow_result(
        manifest(data_start=None, data_end=None),
        (),
        date(2026, 3, 1),
    )

    assert result.snapshot.available_points == ()
    assert result.snapshot.returns == ()
    assert result.summary.point_count == 0
    assert result.summary.return_count == 0
    assert result.summary.starting_value is None
    assert result.summary.ending_value is None
    assert result.summary.cumulative_simple_return is None


def test_zero_available_points_produces_empty_returns_and_empty_summary_values() -> None:
    first = replay_point(date(2026, 4, 1), Decimal("100"), date(2026, 4, 2))
    second = replay_point(date(2026, 4, 2), Decimal("101"), date(2026, 4, 3))

    result = build_synthetic_research_workflow_result(
        manifest(data_start=date(2026, 4, 1), data_end=date(2026, 4, 2)),
        (first, second),
        date(2026, 4, 1),
    )

    assert result.snapshot.available_points == ()
    assert result.snapshot.returns == ()
    assert result.summary.point_count == 0
    assert result.summary.return_count == 0
    assert result.summary.starting_value is None
    assert result.summary.ending_value is None


def test_one_available_point_produces_empty_returns_and_value_summary() -> None:
    first = replay_point(date(2026, 5, 1), Decimal("100.25"), date(2026, 5, 1))
    second = replay_point(date(2026, 5, 2), Decimal("105.00"), date(2026, 5, 3))

    result = build_synthetic_research_workflow_result(
        manifest(data_start=date(2026, 5, 1), data_end=date(2026, 5, 2)),
        (first, second),
        date(2026, 5, 1),
    )

    assert result.snapshot.available_points == (first,)
    assert result.snapshot.returns == ()
    assert result.summary.point_count == 1
    assert result.summary.return_count == 0
    assert result.summary.starting_value == Decimal("100.25")
    assert result.summary.ending_value == Decimal("100.25")
    assert result.summary.cumulative_simple_return is None
    assert result.summary.min_return is None
    assert result.summary.max_return is None
    assert result.summary.mean_return is None


def test_to_dict_uses_nested_result_serializers() -> None:
    fixture = manifest(retrieval_date=date(2026, 5, 14))
    first = replay_point(date(2026, 6, 1), Decimal("100.00"))
    second = replay_point(date(2026, 6, 2), Decimal("102.50"))

    result = build_synthetic_research_workflow_result(
        fixture,
        (first, second),
        date(2026, 6, 2),
    )
    payload = result.to_dict()

    assert tuple(payload) == ("snapshot", "summary")
    assert payload["snapshot"] == result.snapshot.to_dict()
    assert payload["summary"] == result.summary.to_dict()
    assert payload["snapshot"]["manifest"] == fixture.to_dict()
    assert payload["snapshot"]["available_points"] == [
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
    assert payload["snapshot"]["returns"] == ["0.025"]
    assert payload["summary"]["starting_value"] == "100.00"
    assert payload["summary"]["ending_value"] == "102.50"
    assert payload["summary"]["cumulative_simple_return"] == "0.025"
    assert payload["summary"]["min_return"] == "0.025"
    assert payload["summary"]["max_return"] == "0.025"
    assert payload["summary"]["mean_return"] == "0.025"


def test_serialized_output_has_no_approval_backtest_or_trading_fields() -> None:
    payload = build_synthetic_research_workflow_result(
        manifest(),
        workflow_points(),
        date(2026, 1, 3),
    ).to_dict()

    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_RESULT_FIELDS)


def test_malformed_manifest_is_rejected() -> None:
    with pytest.raises(ValidationError, match="manifest"):
        build_synthetic_research_workflow_result(
            object(),
            (),
            date(2026, 7, 1),
        )


@pytest.mark.parametrize(
    "points",
    (
        (object(),),
        "not replay points",
        None,
    ),
)
def test_malformed_points_are_rejected(points: object) -> None:
    with pytest.raises(ValidationError):
        build_synthetic_research_workflow_result(
            manifest(),
            points,
            date(2026, 7, 1),
        )


@pytest.mark.parametrize(
    "asof_date",
    (
        datetime(2026, 8, 1, 12, 0),
        True,
        CustomDate(2026, 8, 1),
        "2026-08-01",
    ),
)
def test_invalid_asof_dates_are_rejected(asof_date: object) -> None:
    with pytest.raises(ValidationError, match="asof_date"):
        build_synthetic_research_workflow_result(
            manifest(data_start=date(2026, 8, 1), data_end=date(2026, 8, 1)),
            (replay_point(date(2026, 8, 1), Decimal("100")),),
            asof_date,
        )


@pytest.mark.parametrize(
    "points,error_match",
    (
        (
            (
                replay_point(date(2026, 9, 1), Decimal("100")),
                replay_point(date(2026, 9, 1), Decimal("101")),
            ),
            "duplicate",
        ),
        (
            (
                replay_point(date(2026, 9, 2), Decimal("100")),
                replay_point(date(2026, 9, 1), Decimal("101")),
            ),
            "ordered",
        ),
    ),
)
def test_duplicate_or_unordered_observations_are_rejected(
    points: tuple[SyntheticReplayPoint, ...],
    error_match: str,
) -> None:
    with pytest.raises(ValidationError, match=error_match):
        build_synthetic_research_workflow_result(
            manifest(data_start=date(2026, 9, 1), data_end=date(2026, 9, 2)),
            points,
            date(2026, 9, 2),
        )


def test_invalid_values_are_rejected_through_return_construction() -> None:
    first = replay_point(date(2026, 10, 1), Decimal("0"))
    second = replay_point(date(2026, 10, 2), Decimal("101"))

    with pytest.raises(ValidationError, match="previous_value"):
        build_synthetic_research_workflow_result(
            manifest(data_start=date(2026, 10, 1), data_end=date(2026, 10, 2)),
            (first, second),
            date(2026, 10, 2),
        )


def test_workflow_does_not_mutate_manifest_points_or_result_payloads() -> None:
    fixture = manifest()
    first = replay_point(date(2026, 11, 1), Decimal("100.00"))
    second = replay_point(date(2026, 11, 2), Decimal("105.00"))
    hidden = replay_point(date(2026, 11, 3), Decimal("120.00"))
    point_items = [first, second]
    original_manifest_payload = fixture.to_dict()
    original_items = list(point_items)
    original_first_observation = first.observation
    original_first_value = first.value

    result = build_synthetic_research_workflow_result(
        fixture,
        point_items,
        date(2026, 11, 2),
    )
    point_items.append(hidden)
    payload = result.to_dict()
    payload["snapshot"]["available_points"].append(
        {
            "observation_date": "2026-11-09",
            "available_after": "2026-11-09",
            "value": "999",
        }
    )
    payload["snapshot"]["returns"].append("9.99")
    payload["snapshot"]["manifest"]["fields"].append("late_field")
    payload["summary"]["point_count"] = 99

    assert fixture.to_dict() == original_manifest_payload
    assert original_items == [first, second]
    assert point_items == [first, second, hidden]
    assert first.observation is original_first_observation
    assert first.value is original_first_value
    assert result.snapshot.manifest is fixture
    assert result.snapshot.available_points == (first, second)
    assert result.snapshot.returns == (Decimal("0.05"),)
    assert result.summary.point_count == 2
    assert result.summary.return_count == 1
    assert fixture.fields == ("observation_date", "synthetic_close")


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


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set()
        for key, nested_value in value.items():
            keys.add(str(key))
            keys.update(_payload_keys(nested_value))
        return keys

    if isinstance(value, list):
        keys = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()


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
