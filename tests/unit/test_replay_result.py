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
from algotrader.research.replay_result import (
    SyntheticResearchResult,
    build_synthetic_research_result,
)


MODULE_PATH = Path("src/algotrader/research/replay_result.py")

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


def manifest(**overrides: object) -> ResearchFixtureManifest:
    values: dict[str, object] = {
        "fixture_id": "synthetic-replay-result-fixture-001",
        "fixture_kind": "synthetic",
        "description": "Tiny deterministic synthetic replay result example.",
        "source_name": "project synthetic fixture",
        "source_type": "synthetic",
        "retrieval_date": None,
        "data_start": date(2026, 1, 1),
        "data_end": date(2026, 1, 3),
        "fields": ("observation_date", "synthetic_close"),
        "checksum": "sha256:synthetic-replay-result-fixture-001",
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


def result_snapshot() -> SyntheticReplaySnapshot:
    first = replay_point(date(2026, 1, 1), Decimal("100.00"))
    second = replay_point(date(2026, 1, 2), Decimal("102.50"))
    hidden = replay_point(date(2026, 1, 3), Decimal("999"), date(2026, 1, 9))
    return replay_snapshot((first, second, hidden), date(2026, 1, 2))


def test_result_contract_is_frozen_slotted_and_minimal() -> None:
    snapshot = result_snapshot()
    item = build_synthetic_research_result(snapshot)

    assert tuple(field.name for field in fields(SyntheticResearchResult)) == (
        "snapshot",
        "summary",
    )
    assert hasattr(SyntheticResearchResult, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.summary = summary()


def test_build_synthetic_research_result_from_snapshot() -> None:
    snapshot = result_snapshot()

    item = build_synthetic_research_result(snapshot)

    assert isinstance(item, SyntheticResearchResult)
    assert item.snapshot is snapshot
    assert isinstance(item.summary, SyntheticReplaySummary)


def test_summary_is_computed_from_snapshot() -> None:
    snapshot = result_snapshot()

    item = build_synthetic_research_result(snapshot)

    assert item.summary == summarize_synthetic_replay_snapshot(snapshot)
    assert item.summary.point_count == 2
    assert item.summary.return_count == 1
    assert item.summary.cumulative_simple_return == Decimal("0.025")


def test_direct_construction_accepts_valid_snapshot_and_summary() -> None:
    snapshot = result_snapshot()
    replay_summary = summarize_synthetic_replay_snapshot(snapshot)

    item = SyntheticResearchResult(snapshot=snapshot, summary=replay_summary)

    assert item.snapshot is snapshot
    assert item.summary is replay_summary


@pytest.mark.parametrize(
    "value",
    (
        object(),
        None,
        "not a snapshot",
    ),
)
def test_malformed_snapshot_is_rejected(value: object) -> None:
    with pytest.raises(ValidationError, match="snapshot"):
        build_synthetic_research_result(value)

    with pytest.raises(ValidationError, match="snapshot"):
        SyntheticResearchResult(snapshot=value, summary=summary())


@pytest.mark.parametrize(
    "value",
    (
        object(),
        None,
        "not a summary",
    ),
)
def test_malformed_summary_is_rejected_for_direct_construction(value: object) -> None:
    with pytest.raises(ValidationError, match="summary"):
        SyntheticResearchResult(snapshot=result_snapshot(), summary=value)


def test_snapshot_and_summary_are_not_mutated() -> None:
    snapshot = result_snapshot()
    replay_summary = summarize_synthetic_replay_snapshot(snapshot)
    original_manifest = snapshot.manifest
    original_available_points = snapshot.available_points
    original_returns = snapshot.returns
    original_summary_payload = replay_summary.to_dict()

    item = SyntheticResearchResult(snapshot=snapshot, summary=replay_summary)
    payload = item.to_dict()
    payload["snapshot"]["available_points"].append(
        {
            "observation_date": "2026-01-09",
            "available_after": "2026-01-09",
            "value": "999",
        }
    )
    payload["snapshot"]["returns"].append("9.99")
    payload["snapshot"]["manifest"]["fields"].append("late_field")
    payload["summary"]["point_count"] = 99

    assert item.snapshot is snapshot
    assert item.summary is replay_summary
    assert snapshot.manifest is original_manifest
    assert snapshot.available_points is original_available_points
    assert snapshot.returns is original_returns
    assert snapshot.manifest.fields == ("observation_date", "synthetic_close")
    assert snapshot.available_points[0].value == Decimal("100.00")
    assert snapshot.available_points[1].value == Decimal("102.50")
    assert snapshot.returns == (Decimal("0.025"),)
    assert replay_summary.to_dict() == original_summary_payload


def test_to_dict_returns_deterministic_json_compatible_metadata() -> None:
    snapshot = result_snapshot()
    item = build_synthetic_research_result(snapshot)

    payload = item.to_dict()

    assert tuple(payload) == ("snapshot", "summary")
    assert payload == {
        "snapshot": snapshot.to_dict(),
        "summary": item.summary.to_dict(),
    }
    assert tuple(payload["snapshot"]) == (
        "manifest",
        "asof_date",
        "available_points",
        "returns",
    )
    assert tuple(payload["summary"]) == (
        "point_count",
        "return_count",
        "starting_value",
        "ending_value",
        "cumulative_simple_return",
        "min_return",
        "max_return",
        "mean_return",
    )


def test_nested_snapshot_and_summary_serialization_are_included() -> None:
    snapshot = result_snapshot()
    item = build_synthetic_research_result(snapshot)

    payload = item.to_dict()

    assert payload["snapshot"]["asof_date"] == "2026-01-02"
    assert payload["snapshot"]["available_points"] == [
        {
            "observation_date": "2026-01-01",
            "available_after": "2026-01-01",
            "value": "100.00",
        },
        {
            "observation_date": "2026-01-02",
            "available_after": "2026-01-02",
            "value": "102.50",
        },
    ]
    assert payload["snapshot"]["returns"] == ["0.025"]
    assert payload["summary"]["point_count"] == 2
    assert payload["summary"]["return_count"] == 1


def test_decimal_values_remain_string_serialized_through_nested_serializers() -> None:
    payload = build_synthetic_research_result(result_snapshot()).to_dict()

    assert payload["snapshot"]["available_points"][0]["value"] == "100.00"
    assert payload["snapshot"]["available_points"][1]["value"] == "102.50"
    assert payload["snapshot"]["returns"] == ["0.025"]
    assert payload["summary"]["starting_value"] == "100.00"
    assert payload["summary"]["ending_value"] == "102.50"
    assert payload["summary"]["cumulative_simple_return"] == "0.025"
    assert payload["summary"]["min_return"] == "0.025"
    assert payload["summary"]["max_return"] == "0.025"
    assert payload["summary"]["mean_return"] == "0.025"


def test_serialized_output_has_no_approval_backtest_or_trading_fields() -> None:
    payload = build_synthetic_research_result(result_snapshot()).to_dict()

    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_RESULT_FIELDS)


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
