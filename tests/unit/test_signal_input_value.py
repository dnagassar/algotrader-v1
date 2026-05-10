import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.signals import SignalInputValue


MODULE_PATH = Path("src/algotrader/signals/signal_input_value.py")

OBSERVED_AT = datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc)
EASTERN_TIME = datetime(2026, 5, 9, 10, 30, tzinfo=timezone(timedelta(hours=-4)))

_FORBIDDEN_SIGNAL_INPUT_VALUE_FIELD_NAMES = {
    "account",
    "account_id",
    "actionable",
    "alpaca",
    "approved",
    "broker",
    "buy",
    "buying_power",
    "cash",
    "confidence",
    "direction",
    "execution_intent",
    "execution_plan",
    "fill",
    "fill_id",
    "llm",
    "ml",
    "ml_model",
    "order",
    "order_type",
    "persistence",
    "portfolio",
    "position",
    "position_id",
    "priority",
    "probability",
    "rank",
    "recommendation",
    "rejected",
    "risk",
    "risk_approved",
    "runtime",
    "scheduler",
    "score",
    "sell",
    "should_trade",
    "signal_direction",
    "side",
    "strategy",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.runtime",
    "algotrader.persistence",
    "algotrader.database",
    "algotrader.ml",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.signals.noop_signal_evaluator",
    "algotrader.signals.signal_evaluation_result",
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
    "NoOpSignalEvaluator",
    "PlanningPolicyResult",
    "PortfolioState",
    "ProposedOrder",
    "RiskEngine",
    "RiskVerdict",
    "SignalEvaluationResult",
    "SignalRiskEvaluation",
    "account",
    "actionable",
    "alpaca",
    "approved",
    "broker",
    "buy",
    "buying_power",
    "cash",
    "confidence",
    "direction",
    "execution_intent",
    "execution_plan",
    "fill",
    "llm",
    "ml",
    "order",
    "persistence",
    "portfolio",
    "position",
    "priority",
    "probability",
    "rank",
    "rejected",
    "risk",
    "risk_approved",
    "runtime",
    "scheduler",
    "score",
    "sell",
    "should_trade",
    "signal_direction",
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


def signal_input_value(**overrides: object) -> SignalInputValue:
    values: dict[str, object] = {
        "name": "quote.ask",
        "value": Decimal("101.23"),
        "observed_at": OBSERVED_AT,
        "source_id": "quotes.synthetic.v1",
    }
    values.update(overrides)
    return SignalInputValue(**values)


def test_signal_input_value_exists() -> None:
    value = signal_input_value()

    assert isinstance(value, SignalInputValue)


def test_signal_input_value_is_frozen_and_slotted() -> None:
    value = signal_input_value()

    assert hasattr(SignalInputValue, "__slots__")
    assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        value.name = "changed"


def test_signal_input_value_has_exact_minimal_fields_only() -> None:
    field_names = tuple(field.name for field in fields(SignalInputValue))

    assert field_names == ("name", "value", "observed_at", "source_id")
    assert set(field_names).isdisjoint(_FORBIDDEN_SIGNAL_INPUT_VALUE_FIELD_NAMES)


def test_valid_construction_preserves_input_metadata_and_value() -> None:
    observed_at = datetime(2026, 5, 9, 15, 45, tzinfo=timezone.utc)
    value = Decimal("101.2300")

    input_value = signal_input_value(
        name=" quote.ask ",
        value=value,
        observed_at=observed_at,
        source_id=" source.quotes.synthetic ",
    )

    assert input_value.name == " quote.ask "
    assert input_value.value is value
    assert input_value.observed_at is observed_at
    assert input_value.source_id == " source.quotes.synthetic "


def test_naive_observed_at_is_rejected() -> None:
    with pytest.raises(ValidationError, match="observed_at"):
        signal_input_value(observed_at=datetime(2026, 5, 9, 14, 30))


def test_non_utc_observed_at_is_rejected() -> None:
    with pytest.raises(ValidationError, match="observed_at"):
        signal_input_value(observed_at=EASTERN_TIME)


def test_observed_at_identity_is_preserved_exactly() -> None:
    observed_at = datetime(2026, 5, 9, 16, 0, tzinfo=timezone.utc)

    value = signal_input_value(observed_at=observed_at)

    assert value.observed_at is observed_at


@pytest.mark.parametrize("name", ("", " "))
def test_empty_or_blank_name_is_rejected(name: str) -> None:
    with pytest.raises(ValidationError, match="name"):
        signal_input_value(name=name)


@pytest.mark.parametrize("source_id", ("", " "))
def test_empty_or_blank_source_id_is_rejected(source_id: str) -> None:
    with pytest.raises(ValidationError, match="source_id"):
        signal_input_value(source_id=source_id)


def test_name_source_id_and_string_value_are_preserved_exactly() -> None:
    name = " Input:QUOTE.ask "
    string_value = " Value:OPEN "
    source_id = " Source:quotes.synthetic.v1 "

    value = signal_input_value(name=name, value=string_value, source_id=source_id)

    assert value.name is name
    assert value.value is string_value
    assert value.source_id is source_id


@pytest.mark.parametrize(
    "observed_value",
    (
        Decimal("101.23"),
        42,
        "CLOSED",
        True,
        False,
    ),
)
def test_accepts_deterministic_scalar_values(observed_value: object) -> None:
    value = signal_input_value(value=observed_value)

    assert value.value is observed_value


@pytest.mark.parametrize(
    "observed_value",
    (
        ["mutable"],
        {"mutable": "mapping"},
        ("tuple", "would need a later contract"),
        1.23,
        None,
    ),
)
def test_rejects_unsupported_or_mutable_values(observed_value: object) -> None:
    with pytest.raises(ValidationError, match="value"):
        signal_input_value(value=observed_value)


def test_value_is_stored_without_computation_or_interpretation() -> None:
    decimal_value = Decimal("001.2300")
    string_value = "001.2300"

    decimal_input = signal_input_value(value=decimal_value)
    string_input = signal_input_value(value=string_value)

    assert decimal_input.value is decimal_value
    assert decimal_input.value == Decimal("1.2300")
    assert string_input.value is string_value
    assert string_input.value == "001.2300"


def test_contract_exposes_no_signal_output_behavior() -> None:
    value = signal_input_value()

    for field_name in (
        "output_value",
        "reason_code",
        "diagnostics",
        "assumptions",
        "limitations",
        "signal",
        "signal_output",
        "recommendation",
    ):
        assert not hasattr(value, field_name)


def test_contract_exposes_no_score_direction_confidence_or_actionability_fields() -> None:
    value = signal_input_value()

    for field_name in (
        "score",
        "rank",
        "priority",
        "confidence",
        "probability",
        "direction",
        "signal_direction",
        "actionable",
        "should_trade",
        "approved",
        "risk_approved",
    ):
        assert not hasattr(value, field_name)


def test_contract_exposes_no_trading_path_fields() -> None:
    value = signal_input_value()

    for field_name in (
        "risk",
        "execution_intent",
        "execution_plan",
        "order",
        "broker",
        "alpaca",
        "account",
        "position",
        "fill",
        "portfolio",
        "cash",
        "buying_power",
        "runtime",
        "scheduler",
        "persistence",
        "ml_model",
        "llm",
        "prompt",
    ):
        assert not hasattr(value, field_name)


def test_contract_has_no_signal_feature_strategy_or_trading_methods() -> None:
    value = signal_input_value()

    for method_name in (
        "evaluate",
        "compute_signal",
        "generate_signal",
        "compute_feature",
        "build_features",
        "apply_strategy",
        "rank",
        "prioritize",
        "approve_risk",
        "create_execution_intent",
        "submit_order",
        "persist",
        "predict",
        "prompt",
    ):
        assert not hasattr(value, method_name)


def test_contract_module_imports_no_forbidden_downstream_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_references_no_trading_path_runtime_or_external_types() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_contract_module_makes_no_hidden_io_network_time_random_or_broker_calls() -> None:
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
