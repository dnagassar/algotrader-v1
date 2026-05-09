import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.signals import ValidatedSignalDefinition


MODULE_PATH = Path("src/algotrader/signals/validated_signal_definition.py")

_FORBIDDEN_SIGNAL_DEFINITION_FIELD_NAMES = {
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
    "execution_intent",
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
    "order_type",
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
    "algotrader.research",
    "algotrader.risk",
    "algotrader.scheduler",
    "algotrader.runtime",
    "algotrader.persistence",
    "algotrader.database",
    "algotrader.ml",
    "algotrader.llm",
    "algotrader.llms",
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
    "ResearchMetric",
    "RiskEngine",
    "RiskVerdict",
    "ScreenerSignalEvaluation",
    "SignalRiskEvaluation",
    "ValidatedResearchArtifact",
    "client_order_id",
    "create_client_order_id",
    "execution_intent",
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
    "schedule",
    "submit_order",
    "to_sql",
    "write",
}


def signal_definition(**overrides: object) -> ValidatedSignalDefinition:
    values: dict[str, object] = {
        "signal_id": "validated-signal-001",
        "name": "Ask Momentum Above Close",
        "version": "2026.05.09",
        "description": "Reviewed metadata for a future deterministic signal rule.",
        "source_artifact_id": "research-artifact-001",
        "source_artifact_version": "2026.05.09",
        "required_inputs": ("previous_bar.close", "quote.ask"),
        "output_type": "proposed_order_or_none",
        "evaluation_rule_ref": "ask_momentum_threshold_v1",
        "approved_for": ("deterministic-signal-evaluator-design",),
        "assumptions": ("inputs are aligned by timestamp before evaluation",),
        "limitations": ("not approved for live execution",),
    }
    values.update(overrides)
    return ValidatedSignalDefinition(**values)


def test_validated_signal_definition_is_frozen_and_slotted() -> None:
    definition = signal_definition()

    assert hasattr(ValidatedSignalDefinition, "__slots__")
    assert not hasattr(definition, "__dict__")
    with pytest.raises(FrozenInstanceError):
        definition.name = "changed"


def test_validated_signal_definition_has_exact_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(ValidatedSignalDefinition))

    assert field_names == (
        "signal_id",
        "name",
        "version",
        "description",
        "source_artifact_id",
        "source_artifact_version",
        "required_inputs",
        "output_type",
        "evaluation_rule_ref",
        "approved_for",
        "assumptions",
        "limitations",
    )
    assert set(field_names).isdisjoint(_FORBIDDEN_SIGNAL_DEFINITION_FIELD_NAMES)


def test_tuple_fields_are_stored_as_tuples() -> None:
    definition = signal_definition(
        required_inputs=["bar.close", "quote.ask"],
        approved_for=["signal-evaluator-design"],
        assumptions=["first assumption"],
        limitations=["first limitation"],
    )

    assert isinstance(definition.required_inputs, tuple)
    assert isinstance(definition.approved_for, tuple)
    assert isinstance(definition.assumptions, tuple)
    assert isinstance(definition.limitations, tuple)


def test_tuple_fields_are_immutable() -> None:
    definition = signal_definition()

    with pytest.raises(FrozenInstanceError):
        definition.required_inputs = ()
    with pytest.raises(FrozenInstanceError):
        definition.approved_for = ()
    with pytest.raises(FrozenInstanceError):
        definition.assumptions = ()
    with pytest.raises(FrozenInstanceError):
        definition.limitations = ()
    with pytest.raises(TypeError):
        definition.required_inputs[0] = "changed"


def test_input_ordering_is_preserved() -> None:
    definition = signal_definition(
        required_inputs=["previous_bar.close", "quote.bid", "quote.ask"],
        approved_for=["contract-design", "fixture-design"],
        assumptions=["first assumption", "second assumption"],
        limitations=["first limitation", "second limitation"],
    )

    assert definition.required_inputs == (
        "previous_bar.close",
        "quote.bid",
        "quote.ask",
    )
    assert definition.approved_for == ("contract-design", "fixture-design")
    assert definition.assumptions == ("first assumption", "second assumption")
    assert definition.limitations == ("first limitation", "second limitation")


def test_input_collections_are_copied_to_immutable_tuples() -> None:
    required_inputs = ["previous_bar.close"]
    approved_for = ["contract-design"]
    assumptions = ["first assumption"]
    limitations = ["first limitation"]

    definition = signal_definition(
        required_inputs=required_inputs,
        approved_for=approved_for,
        assumptions=assumptions,
        limitations=limitations,
    )
    required_inputs.append("quote.ask")
    approved_for.append("late approval")
    assumptions.append("late assumption")
    limitations.append("late limitation")

    assert definition.required_inputs == ("previous_bar.close",)
    assert definition.approved_for == ("contract-design",)
    assert definition.assumptions == ("first assumption",)
    assert definition.limitations == ("first limitation",)


@pytest.mark.parametrize(
    "field_name",
    (
        "signal_id",
        "name",
        "version",
        "description",
        "source_artifact_id",
        "source_artifact_version",
        "output_type",
        "evaluation_rule_ref",
    ),
)
def test_empty_required_strings_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError):
        signal_definition(**{field_name: " "})


@pytest.mark.parametrize(
    "field_name",
    ("required_inputs", "approved_for", "assumptions", "limitations"),
)
def test_empty_tuple_string_entries_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError):
        signal_definition(**{field_name: ("valid entry", " ")})


@pytest.mark.parametrize(
    "field_name",
    ("required_inputs", "approved_for", "assumptions", "limitations"),
)
def test_tuple_fields_reject_single_string_values(field_name: str) -> None:
    with pytest.raises(ValidationError):
        signal_definition(**{field_name: "single value"})


def test_object_exposes_only_definition_metadata() -> None:
    definition = signal_definition()

    assert definition.signal_id == "validated-signal-001"
    assert definition.source_artifact_id == "research-artifact-001"
    assert definition.source_artifact_version == "2026.05.09"
    assert definition.evaluation_rule_ref == "ask_momentum_threshold_v1"
    for field_name in _FORBIDDEN_SIGNAL_DEFINITION_FIELD_NAMES:
        assert not hasattr(definition, field_name)


def test_signal_definition_does_not_compute_or_recommend_trades() -> None:
    definition = signal_definition()

    assert not hasattr(definition, "evaluate")
    assert not hasattr(definition, "compute_signal")
    assert not hasattr(definition, "generate_signal")
    assert not hasattr(definition, "recommendation")
    assert not hasattr(definition, "buy")
    assert not hasattr(definition, "sell")
    assert not hasattr(definition, "hold")


def test_signal_definition_is_independent_from_execution_risk_and_runtime_types() -> None:
    definition = signal_definition()
    forbidden_names = {
        "execution_intent",
        "execution_plan",
        "planning_policy_result",
        "risk_evaluation",
        "risk_verdict",
        "signal_risk_evaluation",
        "broker",
        "runtime",
    }

    for field_name in forbidden_names:
        assert not hasattr(definition, field_name)


def test_research_artifact_reference_is_stable_id_and_version_strings_only() -> None:
    definition = signal_definition()

    assert definition.source_artifact_id == "research-artifact-001"
    assert definition.source_artifact_version == "2026.05.09"
    assert isinstance(definition.source_artifact_id, str)
    assert isinstance(definition.source_artifact_version, str)
    assert not hasattr(definition, "source_artifact")
    assert not hasattr(definition, "validated_research_artifact")


def test_contract_module_imports_no_trading_path_or_research_behavior_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_references_no_trading_path_runtime_or_research_types() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_creating_signal_definition_performs_no_io_network_broker_ingestion_or_scheduling() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)

    definition = signal_definition()

    assert definition.signal_id == "validated-signal-001"


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
