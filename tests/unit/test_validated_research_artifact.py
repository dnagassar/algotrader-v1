import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.validated_artifact import (
    ResearchMetric,
    ValidatedResearchArtifact,
)


NOW = datetime(2026, 5, 9, tzinfo=timezone.utc)
MODULE_PATH = Path("src/algotrader/research/validated_artifact.py")

_FORBIDDEN_ARTIFACT_FIELD_NAMES = {
    "account",
    "account_id",
    "alpaca",
    "alpaca_order",
    "broker",
    "broker_name",
    "broker_order_id",
    "buying_power",
    "buying_power_reserved",
    "cash",
    "cash_reserved",
    "client_order_id",
    "execution",
    "execution_plan",
    "fill",
    "fill_price",
    "fill_quantity",
    "filled",
    "filled_at",
    "idempotency_key",
    "native_order",
    "order",
    "order_id",
    "orders",
    "portfolio",
    "portfolio_state",
    "position",
    "priority",
    "quantity",
    "rank",
    "ranking",
    "reservation",
    "risk",
    "risk_approval",
    "risk_approved",
    "score",
    "side",
    "signal",
    "status",
    "submit_order",
    "submitted_at",
    "symbol",
    "venue",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "algotrader.ml",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.runtime",
    "algotrader.persistence",
    "algotrader.database",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "openai",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
)

_FORBIDDEN_REFERENCE_NAMES = {
    "AlpacaPaperBroker",
    "BrokerOrderResult",
    "ExecutionIntent",
    "ExecutionPlan",
    "LocalBroker",
    "PlanningPolicyResult",
    "PortfolioState",
    "ProposedOrder",
    "RiskEngine",
    "RiskVerdict",
    "ScreenerSignalEvaluation",
    "SignalRiskEvaluation",
    "client_order_id",
    "create_client_order_id",
    "execution_plan",
    "fill",
    "idempotency",
    "portfolio",
    "ranking",
    "submit_order",
}

_FORBIDDEN_CALL_NAMES = {
    "connect",
    "create_order",
    "get",
    "open",
    "post",
    "read_csv",
    "request",
    "submit_order",
    "to_sql",
    "write",
}


def metric(name: str = "walk_forward_sharpe", value: str = "1.23") -> ResearchMetric:
    return ResearchMetric(name=name, value=value)


def artifact(**overrides: object) -> ValidatedResearchArtifact:
    values: dict[str, object] = {
        "artifact_id": "research-artifact-001",
        "name": "Ask Momentum Walk Forward Validation",
        "version": "2026.05.09",
        "description": "Reviewed evidence for an advisory research result.",
        "validated_at": NOW,
        "metrics": (metric("walk_forward_sharpe", "1.23"),),
        "assumptions": ("uses adjusted historical bars only",),
        "limitations": ("not approved for live execution",),
        "approved_for": ("deterministic-contract-design",),
    }
    values.update(overrides)
    return ValidatedResearchArtifact(**values)


def test_research_metric_is_frozen_and_slotted() -> None:
    item = metric()

    assert hasattr(ResearchMetric, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.value = "changed"


def test_validated_research_artifact_is_frozen_and_slotted() -> None:
    item = artifact()

    assert hasattr(ValidatedResearchArtifact, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.name = "changed"


def test_validated_research_artifact_has_exact_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(ValidatedResearchArtifact))

    assert field_names == (
        "artifact_id",
        "name",
        "version",
        "description",
        "validated_at",
        "metrics",
        "assumptions",
        "limitations",
        "approved_for",
    )
    assert set(field_names).isdisjoint(_FORBIDDEN_ARTIFACT_FIELD_NAMES)


def test_research_metric_has_exact_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(ResearchMetric))

    assert field_names == ("name", "value")
    assert set(field_names).isdisjoint(_FORBIDDEN_ARTIFACT_FIELD_NAMES)


def test_tuple_fields_are_stored_as_tuples() -> None:
    item = artifact(
        metrics=[metric("win_rate", "54%")],
        assumptions=["first assumption"],
        limitations=["first limitation"],
        approved_for=["contract-review"],
    )

    assert isinstance(item.metrics, tuple)
    assert isinstance(item.assumptions, tuple)
    assert isinstance(item.limitations, tuple)
    assert isinstance(item.approved_for, tuple)


def test_tuple_fields_are_immutable() -> None:
    item = artifact()

    with pytest.raises(FrozenInstanceError):
        item.metrics = ()
    with pytest.raises(TypeError):
        item.assumptions[0] = "changed"


def test_input_order_is_preserved() -> None:
    first_metric = metric("validation_return", "8.1%")
    second_metric = metric("max_drawdown", "3.4%")

    item = artifact(
        metrics=[first_metric, second_metric],
        assumptions=["first assumption", "second assumption"],
        limitations=["first limitation", "second limitation"],
        approved_for=["feature-contract", "signal-contract"],
    )

    assert item.metrics == (first_metric, second_metric)
    assert item.assumptions == ("first assumption", "second assumption")
    assert item.limitations == ("first limitation", "second limitation")
    assert item.approved_for == ("feature-contract", "signal-contract")


def test_metric_identity_is_preserved_inside_artifact_metrics() -> None:
    first_metric = metric("validation_return", "8.1%")
    second_metric = metric("max_drawdown", "3.4%")

    item = artifact(metrics=[first_metric, second_metric])

    assert item.metrics[0] is first_metric
    assert item.metrics[1] is second_metric


def test_metrics_preserve_deterministic_order() -> None:
    first_metric = metric("walk_forward_sharpe", "1.23")
    second_metric = metric("max_drawdown", "3.4%")
    third_metric = metric("holdout_return", "8.1%")

    item = artifact(metrics=[first_metric, second_metric, third_metric])

    assert item.metrics == (first_metric, second_metric, third_metric)


def test_assumptions_preserve_deterministic_order() -> None:
    item = artifact(
        assumptions=[
            "uses adjusted historical bars only",
            "records spread assumptions separately",
            "keeps final holdout untouched",
        ]
    )

    assert item.assumptions == (
        "uses adjusted historical bars only",
        "records spread assumptions separately",
        "keeps final holdout untouched",
    )


def test_limitations_preserve_deterministic_order() -> None:
    item = artifact(
        limitations=[
            "not approved for live execution",
            "not connected to broker routing",
            "not a risk approval",
        ]
    )

    assert item.limitations == (
        "not approved for live execution",
        "not connected to broker routing",
        "not a risk approval",
    )


def test_approved_advisory_uses_preserve_deterministic_order() -> None:
    item = artifact(
        approved_for=[
            "feature-contract-design",
            "signal-contract-design",
            "documentation-traceability",
        ]
    )

    assert item.approved_for == (
        "feature-contract-design",
        "signal-contract-design",
        "documentation-traceability",
    )


def test_input_collections_are_copied_to_immutable_tuples() -> None:
    metrics = [metric("validation_return", "8.1%")]
    assumptions = ["first assumption"]
    limitations = ["first limitation"]
    approved_for = ["feature-contract"]

    item = artifact(
        metrics=metrics,
        assumptions=assumptions,
        limitations=limitations,
        approved_for=approved_for,
    )
    metrics.append(metric("late_metric", "999"))
    assumptions.append("late assumption")
    limitations.append("late limitation")
    approved_for.append("late approval")

    assert item.metrics == (metric("validation_return", "8.1%"),)
    assert item.assumptions == ("first assumption",)
    assert item.limitations == ("first limitation",)
    assert item.approved_for == ("feature-contract",)


def test_all_tuple_fields_cannot_be_reassigned_after_construction() -> None:
    item = artifact()

    with pytest.raises(FrozenInstanceError):
        item.metrics = ()
    with pytest.raises(FrozenInstanceError):
        item.assumptions = ()
    with pytest.raises(FrozenInstanceError):
        item.limitations = ()
    with pytest.raises(FrozenInstanceError):
        item.approved_for = ()


def test_tuple_entries_cannot_be_mutated_after_construction() -> None:
    item = artifact(
        metrics=[metric("validation_return", "8.1%")],
        assumptions=["first assumption"],
        limitations=["first limitation"],
        approved_for=["feature-contract"],
    )

    with pytest.raises(TypeError):
        item.metrics[0] = metric("changed", "0")
    with pytest.raises(TypeError):
        item.assumptions[0] = "changed"
    with pytest.raises(TypeError):
        item.limitations[0] = "changed"
    with pytest.raises(TypeError):
        item.approved_for[0] = "changed"


@pytest.mark.parametrize(
    "field_name",
    ("artifact_id", "name", "version", "description"),
)
def test_empty_required_artifact_strings_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError):
        artifact(**{field_name: " "})


@pytest.mark.parametrize("field_name", ("name", "value"))
def test_empty_required_metric_strings_are_rejected(field_name: str) -> None:
    values = {"name": "walk_forward_sharpe", "value": "1.23"}
    values[field_name] = " "

    with pytest.raises(ValidationError):
        ResearchMetric(**values)


@pytest.mark.parametrize(
    "field_name",
    ("assumptions", "limitations", "approved_for"),
)
def test_empty_tuple_string_entries_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError):
        artifact(**{field_name: ("valid entry", " ")})


def test_validated_at_must_be_datetime() -> None:
    with pytest.raises(ValidationError):
        artifact(validated_at="2026-05-09T00:00:00Z")


def test_metrics_must_contain_research_metric_values() -> None:
    with pytest.raises(ValidationError):
        artifact(metrics=("walk_forward_sharpe=1.23",))


def test_string_tuple_fields_reject_single_string_values() -> None:
    with pytest.raises(ValidationError):
        artifact(assumptions="single assumption")


def test_artifact_exposes_no_forbidden_trading_path_attributes() -> None:
    item = artifact()

    for field_name in _FORBIDDEN_ARTIFACT_FIELD_NAMES:
        assert not hasattr(item, field_name)


def test_artifact_does_not_infer_trading_decisions() -> None:
    item = artifact()

    assert not hasattr(item, "symbol")
    assert not hasattr(item, "side")
    assert not hasattr(item, "quantity")
    assert not hasattr(item, "order")
    assert not hasattr(item, "risk")
    assert not hasattr(item, "execution_plan")
    assert not hasattr(item, "approved_trade")


def test_artifact_remains_advisory_metadata_only() -> None:
    item = artifact()

    assert item.approved_for == ("deterministic-contract-design",)
    assert not hasattr(item, "create_signal")
    assert not hasattr(item, "approve_trade")
    assert not hasattr(item, "approve_order")
    assert not hasattr(item, "mutate_execution_plan")
    assert not hasattr(item, "submit_order")
    assert not hasattr(item, "persist")


def test_artifact_is_independent_from_execution_plan_intent_policy_and_risk_types() -> None:
    item = artifact()
    forbidden_names = {
        "execution_intent",
        "execution_plan",
        "planning_policy_result",
        "risk_evaluation",
        "risk_verdict",
        "signal_risk_evaluation",
    }

    for field_name in forbidden_names:
        assert not hasattr(item, field_name)


def test_contract_module_imports_no_trading_path_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_references_no_trading_path_or_runtime_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_creating_artifact_performs_no_io_network_broker_or_ingestion_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)

    item = artifact()

    assert item.artifact_id == "research-artifact-001"


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
