import ast
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.signals.noop_signal_evaluator import NoOpSignalEvaluator
from algotrader.signals.signal_evaluation_input import SignalEvaluationInputSnapshot
from algotrader.signals.signal_evaluation_result import SignalEvaluationResult
from algotrader.signals.validated_signal_definition import ValidatedSignalDefinition


MODULE_PATH = Path("src/algotrader/signals/noop_signal_evaluator.py")

AS_OF = datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 5, 9, 14, 31, tzinfo=timezone.utc)
EASTERN_TIME = datetime(2026, 5, 9, 10, 30, tzinfo=timezone(timedelta(hours=-4)))

_FORBIDDEN_RESULT_FIELDS = (
    "score",
    "confidence",
    "probability",
    "direction",
    "signal_direction",
    "rank",
    "priority",
    "actionable",
    "should_trade",
    "result_kind",
    "evaluator_kind",
    "is_noop",
    "no_op",
    "noop",
    "no_op_marker",
    "risk",
    "risk_approved",
    "execution_intent",
    "execution_plan",
    "order",
    "broker",
    "alpaca",
    "portfolio",
    "runtime",
    "scheduler",
    "persistence",
    "ml_model",
    "llm",
    "llm_decision",
)

_FORBIDDEN_IMPORT_PREFIXES = (
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
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
    "Account",
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
    "SignalRiskEvaluation",
    "account",
    "actionable",
    "alpaca",
    "broker",
    "buying_power",
    "cash",
    "client_order_id",
    "confidence",
    "direction",
    "evaluator_kind",
    "execution_intent",
    "execution_plan",
    "fill",
    "llm",
    "ml_model",
    "order",
    "portfolio",
    "priority",
    "probability",
    "rank",
    "result_kind",
    "risk_approved",
    "runtime",
    "scheduler",
    "score",
    "should_trade",
    "signal_direction",
    "side",
    "submit_order",
}

_FORBIDDEN_CALL_NAMES = {
    "connect",
    "create_order",
    "datetime.now",
    "datetime.utcnow",
    "environ.get",
    "get",
    "getenv",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "random",
    "random.random",
    "read",
    "read_csv",
    "request",
    "schedule",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_sql",
    "uuid.uuid4",
    "uuid4",
    "write",
}


def signal_definition(**overrides: object) -> ValidatedSignalDefinition:
    values: dict[str, object] = {
        "signal_id": "validated-signal-001",
        "name": "Metadata Only Boundary",
        "version": "2026.05.09",
        "description": "Reviewed metadata for a future no-op evaluator boundary.",
        "source_artifact_id": "research-artifact-001",
        "source_artifact_version": "2026.05.09",
        "required_inputs": ("previous_bar.close", "quote.ask"),
        "output_type": "advisory_metadata_only",
        "evaluation_rule_ref": "noop_signal_evaluator_boundary_v1",
        "approved_for": ("deterministic-noop-evaluator-contract",),
        "assumptions": ("inputs are explicit metadata references",),
        "limitations": ("not approved for trading decisions",),
    }
    values.update(overrides)
    return ValidatedSignalDefinition(**values)


def input_snapshot(**overrides: object) -> SignalEvaluationInputSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "snapshot:explicit-inputs-001",
        "as_of": AS_OF,
        "required_input_names": ("previous_bar.close", "quote.ask"),
        "source_ids": ("synthetic-bars-fixture", "synthetic-quotes-fixture"),
    }
    values.update(overrides)
    return SignalEvaluationInputSnapshot(**values)


def evaluate_noop(
    *,
    definition: ValidatedSignalDefinition | None = None,
    snapshot: SignalEvaluationInputSnapshot | None = None,
    as_of: datetime = AS_OF,
    evaluated_at: datetime = EVALUATED_AT,
) -> SignalEvaluationResult:
    return NoOpSignalEvaluator().evaluate(
        definition or signal_definition(),
        snapshot or input_snapshot(),
        as_of=as_of,
        evaluated_at=evaluated_at,
    )


def test_noop_signal_evaluator_exists_and_is_frozen_and_slotted() -> None:
    evaluator = NoOpSignalEvaluator()

    assert hasattr(NoOpSignalEvaluator, "__slots__")
    assert not hasattr(evaluator, "__dict__")
    with pytest.raises((FrozenInstanceError, TypeError)):
        evaluator.new_attribute = "changed"


def test_valid_evaluation_returns_signal_evaluation_result() -> None:
    result = evaluate_noop()

    assert isinstance(result, SignalEvaluationResult)


def test_returned_result_is_advisory_metadata_only() -> None:
    result = evaluate_noop()

    assert result.output_value == "NO_SIGNAL_COMPUTED"
    assert result.reason_code == "NOOP_SIGNAL_EVALUATOR"
    assert result.diagnostics == (
        "no signal computation performed",
        "no feature values inspected",
        "no actionability implied",
    )
    assert "not a signal firing" in result.limitations
    assert "not a recommendation" in result.limitations
    assert "not risk approval" in result.limitations
    assert "not execution-ready" in result.limitations


def test_returned_result_preserves_signal_definition_identity_and_version() -> None:
    definition = signal_definition(
        signal_id="signal.noop.boundary.v1",
        version="2026.05.09+noop",
    )

    result = evaluate_noop(definition=definition)

    assert result.signal_id == "signal.noop.boundary.v1"
    assert result.signal_version == "2026.05.09+noop"


def test_returned_result_preserves_source_artifact_identity_and_version() -> None:
    definition = signal_definition(
        source_artifact_id="artifact.noop.review.001",
        source_artifact_version="2026.05.09+reviewed",
    )

    result = evaluate_noop(definition=definition)

    assert result.source_artifact_id == "artifact.noop.review.001"
    assert result.source_artifact_version == "2026.05.09+reviewed"


def test_returned_result_preserves_input_snapshot_id_as_input_fingerprint() -> None:
    snapshot = input_snapshot(snapshot_id="snapshot:exact-reference-ABC")

    result = evaluate_noop(snapshot=snapshot)

    assert result.input_fingerprint == "snapshot:exact-reference-ABC"
    assert result.input_fingerprint == snapshot.snapshot_id


def test_returned_result_preserves_as_of_identity() -> None:
    as_of = datetime(2026, 5, 9, 15, 0, tzinfo=timezone.utc)
    evaluated_at = datetime(2026, 5, 9, 15, 1, tzinfo=timezone.utc)
    snapshot = input_snapshot(as_of=as_of)

    result = evaluate_noop(snapshot=snapshot, as_of=as_of, evaluated_at=evaluated_at)

    assert result.as_of is as_of


def test_returned_result_preserves_evaluated_at_identity() -> None:
    evaluated_at = datetime(2026, 5, 9, 15, 1, tzinfo=timezone.utc)

    result = evaluate_noop(evaluated_at=evaluated_at)

    assert result.evaluated_at is evaluated_at


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValidationError, match="as_of"):
        evaluate_noop(as_of=datetime(2026, 5, 9, 14, 30))


def test_naive_evaluated_at_is_rejected() -> None:
    with pytest.raises(ValidationError, match="evaluated_at"):
        evaluate_noop(evaluated_at=datetime(2026, 5, 9, 14, 31))


def test_non_utc_as_of_is_rejected() -> None:
    with pytest.raises(ValidationError, match="as_of"):
        evaluate_noop(as_of=EASTERN_TIME)


def test_non_utc_evaluated_at_is_rejected() -> None:
    with pytest.raises(ValidationError, match="evaluated_at"):
        evaluate_noop(evaluated_at=EASTERN_TIME)


def test_evaluated_at_before_as_of_is_rejected() -> None:
    as_of = datetime(2026, 5, 9, 15, 0, tzinfo=timezone.utc)
    evaluated_at = datetime(2026, 5, 9, 14, 59, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="evaluated_at"):
        evaluate_noop(as_of=as_of, evaluated_at=evaluated_at)


def test_input_snapshot_after_as_of_is_rejected() -> None:
    as_of = datetime(2026, 5, 9, 15, 0, tzinfo=timezone.utc)
    evaluated_at = datetime(2026, 5, 9, 15, 2, tzinfo=timezone.utc)
    snapshot = input_snapshot(as_of=datetime(2026, 5, 9, 15, 1, tzinfo=timezone.utc))

    with pytest.raises(ValidationError, match="input_snapshot.as_of"):
        evaluate_noop(snapshot=snapshot, as_of=as_of, evaluated_at=evaluated_at)


def test_repeated_calls_with_identical_inputs_produce_equal_results() -> None:
    evaluator = NoOpSignalEvaluator()
    definition = signal_definition()
    snapshot = input_snapshot()

    first = evaluator.evaluate(
        definition,
        snapshot,
        as_of=AS_OF,
        evaluated_at=EVALUATED_AT,
    )
    second = evaluator.evaluate(
        definition,
        snapshot,
        as_of=AS_OF,
        evaluated_at=EVALUATED_AT,
    )

    assert first == second


def test_evaluator_does_not_mutate_signal_definition() -> None:
    definition = signal_definition()
    before = definition

    evaluate_noop(definition=definition)

    assert definition == before
    assert definition.required_inputs == ("previous_bar.close", "quote.ask")
    assert definition.approved_for == ("deterministic-noop-evaluator-contract",)


def test_evaluator_does_not_mutate_input_snapshot() -> None:
    snapshot = input_snapshot()
    before = snapshot

    evaluate_noop(snapshot=snapshot)

    assert snapshot == before
    assert snapshot.required_input_names == ("previous_bar.close", "quote.ask")
    assert snapshot.source_ids == ("synthetic-bars-fixture", "synthetic-quotes-fixture")


def test_evaluator_does_not_copy_input_payload_metadata_into_result() -> None:
    snapshot = input_snapshot(
        required_input_names=("payload.value.that.must.not.be.computed",),
        source_ids=("live-source-name-that-must-not-be-opened",),
    )

    result = evaluate_noop(snapshot=snapshot)
    result_text = " ".join(
        (
            result.output_value,
            result.reason_code,
            *result.diagnostics,
            *result.assumptions,
            *result.limitations,
        )
    )

    assert "payload.value.that.must.not.be.computed" not in result_text
    assert "live-source-name-that-must-not-be-opened" not in result_text


def test_returned_result_has_no_score_confidence_direction_or_actionability_fields() -> None:
    result = evaluate_noop()

    for field_name in _FORBIDDEN_RESULT_FIELDS:
        assert not hasattr(result, field_name)


def test_evaluator_module_imports_no_forbidden_downstream_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_evaluator_module_references_no_trading_path_runtime_or_external_types() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_evaluator_module_makes_no_hidden_io_network_time_random_or_broker_calls() -> None:
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
