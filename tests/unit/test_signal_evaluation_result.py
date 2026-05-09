import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.signals import SignalEvaluationResult


MODULE_PATH = Path("src/algotrader/signals/signal_evaluation_result.py")

AS_OF = datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc)
EVALUATED_AT = datetime(2026, 5, 9, 14, 31, tzinfo=timezone.utc)
EASTERN_TIME = datetime(2026, 5, 9, 10, 30, tzinfo=timezone(timedelta(hours=-4)))

_FORBIDDEN_SIGNAL_EVALUATION_RESULT_FIELD_NAMES = {
    "account",
    "account_id",
    "alpaca",
    "alpaca_order",
    "broker",
    "broker_name",
    "broker_order_id",
    "buying_power",
    "buying_power_reserved",
    "bucket",
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
    "strategy",
    "strategy_id",
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
    "RiskEngine",
    "RiskVerdict",
    "ScreenerSignalEvaluation",
    "SignalRiskEvaluation",
    "alpaca",
    "broker",
    "buying_power",
    "cash",
    "client_order_id",
    "llm_decision",
    "ml_model",
    "execution_intent",
    "execution_plan",
    "fill",
    "idempotency",
    "order",
    "portfolio",
    "priority",
    "quantity",
    "rank",
    "reservation",
    "risk_approved",
    "scheduler",
    "side",
    "strategy",
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
    "read",
    "read_csv",
    "request",
    "schedule",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_sql",
    "write",
}


def signal_evaluation_result(**overrides: object) -> SignalEvaluationResult:
    values: dict[str, object] = {
        "evaluation_id": "eval-ask-momentum-001",
        "signal_id": "validated-signal-001",
        "signal_version": "2026.05.09",
        "source_artifact_id": "research-artifact-001",
        "source_artifact_version": "2026.05.09",
        "as_of": AS_OF,
        "evaluated_at": EVALUATED_AT,
        "input_fingerprint": "sha256:explicit-input-snapshot",
        "output_value": "candidate",
        "reason_code": "ask_above_previous_close",
        "diagnostics": ("ask=101.25", "previous_close=100.00"),
        "assumptions": ("inputs are aligned by timestamp",),
        "limitations": ("advisory only",),
    }
    values.update(overrides)
    return SignalEvaluationResult(**values)


def test_signal_evaluation_result_is_frozen_and_slotted() -> None:
    result = signal_evaluation_result()

    assert hasattr(SignalEvaluationResult, "__slots__")
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.output_value = "changed"


def test_signal_evaluation_result_has_exact_advisory_fields_only() -> None:
    field_names = tuple(field.name for field in fields(SignalEvaluationResult))

    assert field_names == (
        "evaluation_id",
        "signal_id",
        "signal_version",
        "source_artifact_id",
        "source_artifact_version",
        "as_of",
        "evaluated_at",
        "input_fingerprint",
        "output_value",
        "reason_code",
        "diagnostics",
        "assumptions",
        "limitations",
    )
    assert set(field_names).isdisjoint(_FORBIDDEN_SIGNAL_EVALUATION_RESULT_FIELD_NAMES)


def test_tuple_fields_are_stored_as_tuples() -> None:
    result = signal_evaluation_result(
        diagnostics=["first diagnostic"],
        assumptions=["first assumption"],
        limitations=["first limitation"],
    )

    assert isinstance(result.diagnostics, tuple)
    assert isinstance(result.assumptions, tuple)
    assert isinstance(result.limitations, tuple)


def test_tuple_fields_are_immutable() -> None:
    result = signal_evaluation_result()

    with pytest.raises(FrozenInstanceError):
        result.diagnostics = ()
    with pytest.raises(FrozenInstanceError):
        result.assumptions = ()
    with pytest.raises(FrozenInstanceError):
        result.limitations = ()
    with pytest.raises(TypeError):
        result.diagnostics[0] = "changed"
    with pytest.raises(TypeError):
        result.assumptions[0] = "changed"
    with pytest.raises(TypeError):
        result.limitations[0] = "changed"


def test_tuple_input_ordering_is_preserved() -> None:
    result = signal_evaluation_result(
        diagnostics=["first diagnostic", "second diagnostic", "third diagnostic"],
        assumptions=["first assumption", "second assumption"],
        limitations=["first limitation", "second limitation"],
    )

    assert result.diagnostics == (
        "first diagnostic",
        "second diagnostic",
        "third diagnostic",
    )
    assert result.assumptions == ("first assumption", "second assumption")
    assert result.limitations == ("first limitation", "second limitation")


def test_tuple_fields_preserve_deterministic_order_after_construction() -> None:
    result = signal_evaluation_result(
        diagnostics=[
            "input_snapshot=sha256:abc",
            "rule_ref=ask_momentum_threshold_v1",
            "output_value=candidate",
        ],
        assumptions=[
            "snapshot is closed at as_of",
            "definition version is immutable",
            "evaluation context is explicit",
        ],
        limitations=[
            "not a risk approval",
            "not an execution instruction",
            "not a broker request",
        ],
    )

    assert result.diagnostics == (
        "input_snapshot=sha256:abc",
        "rule_ref=ask_momentum_threshold_v1",
        "output_value=candidate",
    )
    assert result.assumptions == (
        "snapshot is closed at as_of",
        "definition version is immutable",
        "evaluation context is explicit",
    )
    assert result.limitations == (
        "not a risk approval",
        "not an execution instruction",
        "not a broker request",
    )


def test_input_collections_are_copied_to_immutable_tuples() -> None:
    diagnostics = ["first diagnostic"]
    assumptions = ["first assumption"]
    limitations = ["first limitation"]

    result = signal_evaluation_result(
        diagnostics=diagnostics,
        assumptions=assumptions,
        limitations=limitations,
    )
    diagnostics.append("late diagnostic")
    assumptions.append("late assumption")
    limitations.append("late limitation")

    assert result.diagnostics == ("first diagnostic",)
    assert result.assumptions == ("first assumption",)
    assert result.limitations == ("first limitation",)


@pytest.mark.parametrize(
    "field_name",
    (
        "evaluation_id",
        "signal_id",
        "signal_version",
        "source_artifact_id",
        "source_artifact_version",
        "input_fingerprint",
        "output_value",
        "reason_code",
    ),
)
def test_empty_required_strings_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError):
        signal_evaluation_result(**{field_name: " "})


@pytest.mark.parametrize(
    "field_name",
    ("diagnostics", "assumptions", "limitations"),
)
def test_empty_tuple_string_entries_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError):
        signal_evaluation_result(**{field_name: ("valid entry", " ")})


@pytest.mark.parametrize(
    "field_name",
    ("diagnostics", "assumptions", "limitations"),
)
def test_tuple_fields_reject_single_string_values(field_name: str) -> None:
    with pytest.raises(ValidationError):
        signal_evaluation_result(**{field_name: "single value"})


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValidationError, match="as_of"):
        signal_evaluation_result(as_of=datetime(2026, 5, 9, 14, 30))


def test_naive_evaluated_at_is_rejected() -> None:
    with pytest.raises(ValidationError, match="evaluated_at"):
        signal_evaluation_result(evaluated_at=datetime(2026, 5, 9, 14, 31))


@pytest.mark.parametrize("field_name", ("as_of", "evaluated_at"))
def test_non_utc_aware_datetimes_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError, match=field_name):
        signal_evaluation_result(**{field_name: EASTERN_TIME})


def test_utc_aware_datetimes_are_accepted_and_identity_is_preserved() -> None:
    as_of = datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc)
    evaluated_at = datetime(2026, 5, 9, 14, 31, tzinfo=timezone.utc)

    result = signal_evaluation_result(as_of=as_of, evaluated_at=evaluated_at)

    assert result.as_of is as_of
    assert result.evaluated_at is evaluated_at


def test_as_of_identity_is_preserved_exactly() -> None:
    as_of = datetime(2026, 5, 9, 15, 45, tzinfo=timezone.utc)

    result = signal_evaluation_result(as_of=as_of)

    assert result.as_of is as_of


def test_evaluated_at_identity_is_preserved_exactly() -> None:
    evaluated_at = datetime(2026, 5, 9, 15, 46, tzinfo=timezone.utc)

    result = signal_evaluation_result(evaluated_at=evaluated_at)

    assert result.evaluated_at is evaluated_at


def test_as_of_and_evaluated_at_are_independently_utc_valid_for_now() -> None:
    later_as_of = datetime(2026, 5, 9, 14, 31, tzinfo=timezone.utc)
    earlier_evaluated_at = datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc)

    result = signal_evaluation_result(
        as_of=later_as_of,
        evaluated_at=earlier_evaluated_at,
    )

    assert result.as_of is later_as_of
    assert result.evaluated_at is earlier_evaluated_at


def test_object_exposes_only_advisory_signal_evaluation_metadata() -> None:
    result = signal_evaluation_result()

    assert result.evaluation_id == "eval-ask-momentum-001"
    assert result.signal_id == "validated-signal-001"
    assert result.signal_version == "2026.05.09"
    assert result.source_artifact_id == "research-artifact-001"
    assert result.source_artifact_version == "2026.05.09"
    assert result.input_fingerprint == "sha256:explicit-input-snapshot"
    assert result.output_value == "candidate"
    assert result.reason_code == "ask_above_previous_close"
    for field_name in _FORBIDDEN_SIGNAL_EVALUATION_RESULT_FIELD_NAMES:
        assert not hasattr(result, field_name)


def test_traceability_string_fields_are_preserved_exactly() -> None:
    result = signal_evaluation_result(
        evaluation_id="eval.ask-momentum.20260509T143000Z.v1",
        signal_id="signal.ask-momentum.close-ask.v1",
        signal_version="2026.05.09+reviewed",
        source_artifact_id="artifact.walk-forward.ask-momentum.001",
        source_artifact_version="2026.05.09+holdout",
        input_fingerprint="sha256:7f83b1657ff1fc53b92dc18148a1d65d",
        output_value="advisory_candidate",
        reason_code="ASK_ABOVE_PREVIOUS_CLOSE",
    )

    assert result.evaluation_id == "eval.ask-momentum.20260509T143000Z.v1"
    assert result.signal_id == "signal.ask-momentum.close-ask.v1"
    assert result.signal_version == "2026.05.09+reviewed"
    assert result.source_artifact_id == "artifact.walk-forward.ask-momentum.001"
    assert result.source_artifact_version == "2026.05.09+holdout"
    assert result.input_fingerprint == "sha256:7f83b1657ff1fc53b92dc18148a1d65d"
    assert result.output_value == "advisory_candidate"
    assert result.reason_code == "ASK_ABOVE_PREVIOUS_CLOSE"


def test_object_exposes_no_explicit_trading_path_fields() -> None:
    result = signal_evaluation_result()

    for field_name in (
        "ProposedOrder",
        "order",
        "order_id",
        "client_order_id",
        "broker",
        "alpaca",
        "submit_order",
        "symbol_order_instruction",
        "side",
        "quantity",
        "cash",
        "buying_power",
        "reservation",
        "portfolio",
        "position",
        "risk_approved",
        "execution_intent",
        "execution_plan",
        "fill",
        "score",
        "bucket",
        "strategy",
        "scheduler",
        "runtime",
        "persistence",
        "ml_model",
        "llm_decision",
        "priority",
        "rank",
    ):
        assert not hasattr(result, field_name)


def test_signal_evaluation_result_has_no_signal_output_behavior() -> None:
    result = signal_evaluation_result()

    assert not hasattr(result, "evaluate")
    assert not hasattr(result, "compute_signal")
    assert not hasattr(result, "generate_signal")
    assert not hasattr(result, "signal")
    assert not hasattr(result, "signal_output")
    assert not hasattr(result, "buy_signal")
    assert not hasattr(result, "sell_signal")
    assert not hasattr(result, "hold_signal")
    assert not hasattr(result, "recommendation")
    assert not hasattr(result, "score")
    assert not hasattr(result, "bucket")


def test_signal_evaluation_result_has_no_strategy_behavior() -> None:
    result = signal_evaluation_result()

    assert not hasattr(result, "strategy")
    assert not hasattr(result, "strategy_id")
    assert not hasattr(result, "apply_strategy")
    assert not hasattr(result, "allocate")
    assert not hasattr(result, "size_position")
    assert not hasattr(result, "rebalance")


def test_signal_evaluation_result_has_no_risk_execution_or_broker_behavior() -> None:
    result = signal_evaluation_result()

    assert not hasattr(result, "approve_trade")
    assert not hasattr(result, "risk_approved")
    assert not hasattr(result, "risk_verdict")
    assert not hasattr(result, "create_execution_intent")
    assert not hasattr(result, "execution_intent")
    assert not hasattr(result, "build_execution_plan")
    assert not hasattr(result, "execution_plan")
    assert not hasattr(result, "mutate_execution_plan")
    assert not hasattr(result, "submit")
    assert not hasattr(result, "submit_order")
    assert not hasattr(result, "route_order")
    assert not hasattr(result, "broker")
    assert not hasattr(result, "account")
    assert not hasattr(result, "order")
    assert not hasattr(result, "fill")


def test_signal_evaluation_result_has_no_runtime_persistence_ml_or_llm_behavior() -> None:
    result = signal_evaluation_result()

    assert not hasattr(result, "scheduler")
    assert not hasattr(result, "runtime")
    assert not hasattr(result, "persist")
    assert not hasattr(result, "persistence")
    assert not hasattr(result, "save")
    assert not hasattr(result, "ml_model")
    assert not hasattr(result, "predict")
    assert not hasattr(result, "llm")
    assert not hasattr(result, "llm_decision")
    assert not hasattr(result, "prompt")


def test_signal_evaluation_result_remains_independent_from_runtime_contracts() -> None:
    result = signal_evaluation_result()

    for field_name in (
        "validated_research_artifact",
        "validated_signal_definition",
        "execution_plan",
        "execution_intent",
        "planning_policy_result",
        "risk_evaluation",
        "risk_verdict",
        "broker",
        "scheduler",
        "runtime",
        "persistence",
        "ml_model",
        "llm_decision",
    ):
        assert not hasattr(result, field_name)


def test_contract_module_imports_no_downstream_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_references_no_trading_path_runtime_or_external_types() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_creating_signal_evaluation_result_performs_no_io_network_broker_ingestion_or_scheduling() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)

    result = signal_evaluation_result()

    assert result.evaluation_id == "eval-ask-momentum-001"


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
