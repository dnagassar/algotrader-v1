import ast
import random
from dataclasses import FrozenInstanceError, fields, is_dataclass
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
    "account",
    "actionable",
    "agent",
    "alpaca",
    "approved",
    "broker",
    "buy",
    "buying_power",
    "cache",
    "cash",
    "confidence",
    "database",
    "direction",
    "evaluator_kind",
    "execution",
    "execution_intent",
    "execution_plan",
    "fill",
    "fire",
    "fired",
    "is_noop",
    "llm",
    "llm_decision",
    "llm_output",
    "long",
    "ml",
    "ml_model",
    "model",
    "no_op",
    "no_op_marker",
    "noop",
    "order",
    "persistence",
    "portfolio",
    "position",
    "prediction",
    "priority",
    "probability",
    "prompt",
    "rank",
    "rejected",
    "result_kind",
    "risk",
    "risk_approved",
    "runtime",
    "scheduler",
    "score",
    "sell",
    "short",
    "should_trade",
    "signal_direction",
    "side",
)

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.agent",
    "algotrader.agents",
    "algotrader.broker",
    "algotrader.brokers",
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
    "diskcache",
    "duckdb",
    "httpx",
    "joblib",
    "langchain",
    "langgraph",
    "lightgbm",
    "llm",
    "mlflow",
    "numpy",
    "os",
    "openai",
    "pandas",
    "random",
    "redis",
    "requests",
    "scipy",
    "shutil",
    "socket",
    "sklearn",
    "sqlite3",
    "sqlalchemy",
    "sqlmodel",
    "statsmodels",
    "tensorflow",
    "time",
    "torch",
    "transformers",
    "urllib",
    "uuid",
    "websocket",
    "websockets",
    "xgboost",
)

_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    "AlpacaPaperBroker",
    "Agent",
    "Broker",
    "BrokerOrderResult",
    "Execution",
    "ExecutionIntent",
    "ExecutionPlan",
    "LocalBroker",
    "Model",
    "Prediction",
    "PlanningPolicyResult",
    "PortfolioState",
    "ProposedOrder",
    "Prompt",
    "Risk",
    "RiskEngine",
    "RiskVerdict",
    "SignalRiskEvaluation",
    "account",
    "account_id",
    "actionable",
    "agent",
    "alpaca",
    "alpaca_trade_api",
    "approved",
    "broker",
    "buying_power",
    "buy",
    "cache",
    "cash",
    "client_order_id",
    "confidence",
    "database",
    "direction",
    "evaluator_kind",
    "execution",
    "execution_intent",
    "execution_plan",
    "fill",
    "fire",
    "fired",
    "long",
    "llm",
    "ml",
    "ml_model",
    "model",
    "order",
    "output",
    "portfolio",
    "position",
    "prediction",
    "priority",
    "probability",
    "prompt",
    "rank",
    "rejected",
    "result_kind",
    "risk",
    "risk_approved",
    "runtime",
    "scheduler",
    "score",
    "sell",
    "short",
    "should_trade",
    "signal_direction",
    "side",
    "submit_order",
}

_FORBIDDEN_CALL_NAMES = {
    "connect",
    "create_order",
    "date.today",
    "datetime.date.today",
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "datetime.now",
    "datetime.utcnow",
    "environ.get",
    "execute",
    "executemany",
    "fit",
    "get",
    "getenv",
    "httpx.get",
    "httpx.post",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "Path.write_bytes",
    "Path.write_text",
    "persist",
    "post",
    "predict",
    "predict_proba",
    "random",
    "random.choice",
    "random.choices",
    "random.randint",
    "random.random",
    "read_bytes",
    "read",
    "read_csv",
    "read_text",
    "remove",
    "rename",
    "replace",
    "request",
    "requests.get",
    "requests.post",
    "rmdir",
    "schedule",
    "secrets.randbelow",
    "secrets.token_hex",
    "shutil.copy",
    "shutil.copyfile",
    "socket.socket",
    "submit_order",
    "time.monotonic",
    "time.perf_counter",
    "time.sleep",
    "time.time",
    "to_sql",
    "unlink",
    "urlopen",
    "urllib.request.urlopen",
    "uuid.uuid1",
    "uuid.uuid4",
    "uuid4",
    "write",
    "write_bytes",
    "write_text",
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


def test_returned_result_preserves_complete_traceability_without_actionability() -> None:
    definition = signal_definition(
        signal_id="signal.noop.traceability.001",
        version="2026.05.09+trace",
        source_artifact_id="validated-artifact.traceability.001",
        source_artifact_version="2026.05.09+artifact",
    )
    as_of = datetime(2026, 5, 9, 16, 0, tzinfo=timezone.utc)
    evaluated_at = datetime(2026, 5, 9, 16, 2, tzinfo=timezone.utc)
    snapshot = input_snapshot(
        snapshot_id="snapshot:traceability:001",
        as_of=as_of,
    )

    result = evaluate_noop(
        definition=definition,
        snapshot=snapshot,
        as_of=as_of,
        evaluated_at=evaluated_at,
    )

    assert result.signal_id == definition.signal_id
    assert result.signal_version == definition.version
    assert result.source_artifact_id == definition.source_artifact_id
    assert result.source_artifact_version == definition.source_artifact_version
    assert result.input_fingerprint == snapshot.snapshot_id
    assert result.as_of is as_of
    assert result.evaluated_at is evaluated_at
    assert result.output_value == "NO_SIGNAL_COMPUTED"
    assert result.reason_code == "NOOP_SIGNAL_EVALUATOR"
    assert result.diagnostics == (
        "no signal computation performed",
        "no feature values inspected",
        "no actionability implied",
    )
    assert result.assumptions == (
        "definition and input snapshot were supplied explicitly",
        "result is advisory metadata only",
    )
    assert result.limitations == (
        "not a signal firing",
        "not a recommendation",
        "not risk approval",
        "not execution-ready",
    )


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


def test_input_snapshot_at_result_as_of_is_accepted() -> None:
    as_of = datetime(2026, 5, 9, 15, 0, tzinfo=timezone.utc)
    evaluated_at = datetime(2026, 5, 9, 15, 2, tzinfo=timezone.utc)
    snapshot = input_snapshot(
        snapshot_id="snapshot:exact-as-of",
        as_of=as_of,
    )

    result = evaluate_noop(snapshot=snapshot, as_of=as_of, evaluated_at=evaluated_at)

    assert result.input_fingerprint == "snapshot:exact-as-of"
    assert result.as_of is as_of
    assert result.evaluated_at is evaluated_at


def test_input_snapshot_before_result_as_of_is_accepted() -> None:
    snapshot_as_of = datetime(2026, 5, 9, 14, 55, tzinfo=timezone.utc)
    as_of = datetime(2026, 5, 9, 15, 0, tzinfo=timezone.utc)
    evaluated_at = datetime(2026, 5, 9, 15, 2, tzinfo=timezone.utc)
    snapshot = input_snapshot(
        snapshot_id="snapshot:before-as-of",
        as_of=snapshot_as_of,
    )

    result = evaluate_noop(snapshot=snapshot, as_of=as_of, evaluated_at=evaluated_at)

    assert result.input_fingerprint == "snapshot:before-as-of"
    assert result.as_of is as_of
    assert result.evaluated_at is evaluated_at


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


def test_repeated_calls_preserve_deterministic_advisory_tuple_ordering() -> None:
    evaluator = NoOpSignalEvaluator()
    definition = signal_definition()
    snapshot = input_snapshot()

    results = tuple(
        evaluator.evaluate(
            definition,
            snapshot,
            as_of=AS_OF,
            evaluated_at=EVALUATED_AT,
        )
        for _ in range(3)
    )

    expected_tuple_fields = (
        (
            "no signal computation performed",
            "no feature values inspected",
            "no actionability implied",
        ),
        (
            "definition and input snapshot were supplied explicitly",
            "result is advisory metadata only",
        ),
        (
            "not a signal firing",
            "not a recommendation",
            "not risk approval",
            "not execution-ready",
        ),
    )
    observed_tuple_fields = tuple(
        (result.diagnostics, result.assumptions, result.limitations)
        for result in results
    )

    assert observed_tuple_fields == (expected_tuple_fields,) * 3


def test_result_does_not_depend_on_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluator = NoOpSignalEvaluator()
    definition = signal_definition()
    snapshot = input_snapshot()

    monkeypatch.setenv("ALGO_TRADER_NOOP_EVALUATOR_MODE", "first")
    monkeypatch.setenv("ALPACA_API_KEY", "ignored-fake-key")
    first = evaluator.evaluate(
        definition,
        snapshot,
        as_of=AS_OF,
        evaluated_at=EVALUATED_AT,
    )
    monkeypatch.setenv("ALGO_TRADER_NOOP_EVALUATOR_MODE", "second")
    monkeypatch.setenv("ALPACA_API_KEY", "different-ignored-fake-key")
    second = evaluator.evaluate(
        definition,
        snapshot,
        as_of=AS_OF,
        evaluated_at=EVALUATED_AT,
    )

    assert first == second


def test_result_does_not_depend_on_random_state() -> None:
    evaluator = NoOpSignalEvaluator()
    definition = signal_definition()
    snapshot = input_snapshot()

    random.seed(1)
    for _ in range(5):
        random.random()
    first = evaluator.evaluate(
        definition,
        snapshot,
        as_of=AS_OF,
        evaluated_at=EVALUATED_AT,
    )
    random.seed(999)
    for _ in range(5):
        random.randint(0, 1_000_000)
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


def test_evaluator_preserves_input_objects_and_tuple_field_identities() -> None:
    definition = signal_definition()
    snapshot = input_snapshot()
    definition_id = id(definition)
    snapshot_id = id(snapshot)
    definition_values = _field_values(definition)
    snapshot_values = _field_values(snapshot)
    definition_tuple_fields = {
        "required_inputs": definition.required_inputs,
        "approved_for": definition.approved_for,
        "assumptions": definition.assumptions,
        "limitations": definition.limitations,
    }
    snapshot_tuple_fields = {
        "required_input_names": snapshot.required_input_names,
        "source_ids": snapshot.source_ids,
    }

    result = evaluate_noop(definition=definition, snapshot=snapshot)

    assert id(definition) == definition_id
    assert id(snapshot) == snapshot_id
    assert _field_values(definition) == definition_values
    assert _field_values(snapshot) == snapshot_values
    for name, value in definition_tuple_fields.items():
        assert getattr(definition, name) is value
    for name, value in snapshot_tuple_fields.items():
        assert getattr(snapshot, name) is value
    assert result.input_fingerprint == snapshot.snapshot_id


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
    evaluator = NoOpSignalEvaluator()

    result_violations = sorted(_contract_field_names(result) & set(_FORBIDDEN_RESULT_FIELDS))
    evaluator_violations = sorted(
        _contract_field_names(evaluator) & set(_FORBIDDEN_RESULT_FIELDS)
    )

    assert result_violations == []
    assert evaluator_violations == []


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


def _field_values(instance: object) -> tuple[tuple[str, object], ...]:
    return tuple((field.name, getattr(instance, field.name)) for field in fields(instance))


def _contract_field_names(instance: object) -> set[str]:
    cls = type(instance)
    names: set[str] = set()

    if is_dataclass(cls):
        names.update(field.name for field in fields(cls))

    names.update(getattr(cls, "__annotations__", ()))

    slots = getattr(cls, "__slots__", ())
    if isinstance(slots, str):
        names.add(slots)
    else:
        names.update(slots)

    return names


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
