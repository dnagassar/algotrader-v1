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
    "agent",
    "alpaca",
    "approved",
    "broker",
    "buy",
    "buying_power",
    "cash",
    "confidence",
    "direction",
    "evaluator",
    "evaluator_kind",
    "execution_intent",
    "execution_plan",
    "fill",
    "fill_id",
    "fired",
    "long",
    "llm",
    "llm_output",
    "ml",
    "ml_model",
    "model",
    "order",
    "order_type",
    "output",
    "output_value",
    "persistence",
    "portfolio",
    "position",
    "prediction",
    "position_id",
    "priority",
    "probability",
    "prompt",
    "reason_code",
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
    "short",
    "signal_direction",
    "side",
    "strategy",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.agent",
    "algotrader.agents",
    "algotrader.broker",
    "algotrader.brokers",
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
    "algotrader.signals.signal_evaluation_input",
    "algotrader.signals.signal_evaluation_result",
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
    "sqlalchemy",
    "sqlite3",
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
    "agent",
    "alpaca",
    "approved",
    "as_of",
    "broker",
    "buy",
    "buying_power",
    "cache",
    "cash",
    "confidence",
    "database",
    "direction",
    "evaluator",
    "evaluator_kind",
    "execution",
    "execution_intent",
    "execution_plan",
    "fill",
    "fired",
    "long",
    "llm",
    "llm_output",
    "ml",
    "model",
    "order",
    "output",
    "output_value",
    "persistence",
    "portfolio",
    "position",
    "prediction",
    "priority",
    "probability",
    "prompt",
    "reason_code",
    "rank",
    "rejected",
    "risk",
    "risk_approved",
    "runtime",
    "scheduler",
    "score",
    "sell",
    "should_trade",
    "short",
    "signal_direction",
    "side",
    "strategy",
    "submit_order",
}

_FORBIDDEN_CALL_NAMES = {
    "assert_not_after_as_of",
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
    "read",
    "read_bytes",
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

_FORBIDDEN_WALL_CLOCK_CALL_NAMES = {
    "date.today",
    "datetime.date.today",
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "datetime.now",
    "datetime.utcnow",
    "time.monotonic",
    "time.perf_counter",
    "time.time",
}

_FORBIDDEN_RANDOM_CALL_NAMES = {
    "random",
    "random.choice",
    "random.choices",
    "random.randint",
    "random.random",
    "secrets.randbelow",
    "secrets.token_hex",
    "uuid.uuid1",
    "uuid.uuid4",
    "uuid4",
}

_FORBIDDEN_ENVIRONMENT_CALL_NAMES = {
    "environ.get",
    "getenv",
    "os.environ.get",
    "os.getenv",
}

_FORBIDDEN_NETWORK_CALL_NAMES = {
    "connect",
    "get",
    "httpx.get",
    "httpx.post",
    "post",
    "request",
    "requests.get",
    "requests.post",
    "socket.socket",
    "urlopen",
    "urllib.request.urlopen",
}

_FORBIDDEN_FILESYSTEM_WRITE_CALL_NAMES = {
    "mkdir",
    "open",
    "Path.write_bytes",
    "Path.write_text",
    "remove",
    "rename",
    "replace",
    "rmdir",
    "shutil.copy",
    "shutil.copyfile",
    "to_sql",
    "unlink",
    "write",
    "write_bytes",
    "write_text",
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


def test_signal_input_value_fields_cannot_be_reassigned() -> None:
    value = signal_input_value()

    with pytest.raises(FrozenInstanceError):
        value.name = "changed"
    with pytest.raises(FrozenInstanceError):
        value.value = Decimal("999")
    with pytest.raises(FrozenInstanceError):
        value.observed_at = datetime(2026, 5, 9, 15, 0, tzinfo=timezone.utc)
    with pytest.raises(FrozenInstanceError):
        value.source_id = "changed"


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


def test_traceability_fields_preserve_exact_identity_and_case() -> None:
    name = " Input:Quote.ASK "
    source_id = " Source:Quotes.Synthetic.V1 "
    observed_at = datetime(2026, 5, 9, 17, 0, tzinfo=timezone.utc)

    value = signal_input_value(
        name=name,
        source_id=source_id,
        observed_at=observed_at,
    )

    assert value.name is name
    assert value.name == " Input:Quote.ASK "
    assert value.source_id is source_id
    assert value.source_id == " Source:Quotes.Synthetic.V1 "
    assert value.observed_at is observed_at


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


def test_utc_observed_at_is_accepted_without_as_of_or_lookahead_check() -> None:
    future_observed_at = datetime(2099, 1, 1, 0, 0, tzinfo=timezone.utc)

    value = signal_input_value(observed_at=future_observed_at)

    assert value.observed_at is future_observed_at
    assert not hasattr(value, "as_of")
    assert "as_of" not in _referenced_names()
    assert "assert_not_after_as_of" not in _call_names()


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


def test_decimal_value_is_preserved_exactly_without_rounding_or_conversion() -> None:
    observed_value = Decimal("001.2300")

    value = signal_input_value(value=observed_value)

    assert value.value is observed_value
    assert isinstance(value.value, Decimal)
    assert value.value.as_tuple() == observed_value.as_tuple()
    assert str(value.value) == "1.2300"


def test_int_value_is_preserved_exactly_without_bool_conversion() -> None:
    observed_value = 1

    value = signal_input_value(value=observed_value)

    assert value.value is observed_value
    assert type(value.value) is int
    assert value.value == 1


def test_bool_values_are_preserved_as_bool_and_distinct_from_int() -> None:
    true_value = signal_input_value(value=True)
    false_value = signal_input_value(value=False)
    one_value = signal_input_value(value=1)
    zero_value = signal_input_value(value=0)

    assert true_value.value is True
    assert false_value.value is False
    assert type(true_value.value) is bool
    assert type(false_value.value) is bool
    assert type(one_value.value) is int
    assert type(zero_value.value) is int
    assert true_value.value == one_value.value
    assert type(true_value.value) is not type(one_value.value)
    assert false_value.value == zero_value.value
    assert type(false_value.value) is not type(zero_value.value)


def test_string_value_is_preserved_exactly_without_timestamp_or_numeric_parsing() -> None:
    observed_value = " 2026-05-09T14:30:00Z "

    value = signal_input_value(value=observed_value)

    assert value.value is observed_value
    assert value.value == " 2026-05-09T14:30:00Z "
    assert isinstance(value.value, str)


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
        {"mutable"},
        ("tuple", "would need a later contract"),
        1.23,
        None,
        object(),
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


def test_values_are_not_computed_from_strings_or_timestamps() -> None:
    observed_at = datetime(2026, 5, 9, 18, 30, tzinfo=timezone.utc)
    numeric_string = "42"
    timestamp_string = observed_at.isoformat()

    numeric_input = signal_input_value(value=numeric_string, observed_at=observed_at)
    timestamp_input = signal_input_value(value=timestamp_string, observed_at=observed_at)

    assert numeric_input.value is numeric_string
    assert numeric_input.value == "42"
    assert timestamp_input.value is timestamp_string
    assert timestamp_input.value == "2026-05-09T18:30:00+00:00"
    assert numeric_input.observed_at is observed_at
    assert timestamp_input.observed_at is observed_at


def test_rejected_mutable_values_cannot_be_mutated_through_contract() -> None:
    mutable_values: tuple[object, ...] = (
        ["mutable"],
        {"mutable": "mapping"},
        {"mutable"},
    )

    for mutable_value in mutable_values:
        with pytest.raises(ValidationError, match="value"):
            signal_input_value(value=mutable_value)


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
        "fired",
        "long",
        "short",
        "buy",
        "sell",
        "side",
        "approved",
        "rejected",
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
        "database",
        "cache",
        "ml_model",
        "model",
        "prediction",
        "llm",
        "agent",
        "prompt",
        "output",
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


def test_contract_module_has_no_hidden_wall_clock_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_WALL_CLOCK_CALL_NAMES)


def test_contract_module_has_no_hidden_random_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_RANDOM_CALL_NAMES)


def test_contract_module_has_no_hidden_environment_variable_reads() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_ENVIRONMENT_CALL_NAMES)


def test_contract_module_has_no_hidden_network_or_socket_access() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_NETWORK_CALL_NAMES)
    assert not any(
        _matches_forbidden_prefix(
            module,
            ("aiohttp", "httpx", "requests", "socket", "urllib", "websocket"),
        )
        for module in _import_references()
    )


def test_contract_module_has_no_hidden_filesystem_database_cache_or_persistence_writes() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_FILESYSTEM_WRITE_CALL_NAMES)
    assert not any(
        _matches_forbidden_prefix(
            module,
            (
                "algotrader.database",
                "algotrader.persistence",
                "database",
                "diskcache",
                "duckdb",
                "redis",
                "sqlalchemy",
                "sqlite3",
                "sqlmodel",
            ),
        )
        for module in _import_references()
    )


def test_contract_module_has_no_hidden_broker_ml_llm_or_agent_imports() -> None:
    assert not any(
        _matches_forbidden_prefix(
            module,
            (
                "algotrader.broker",
                "algotrader.brokers",
                "algotrader.execution",
                "algotrader.llm",
                "algotrader.llms",
                "algotrader.ml",
                "alpaca",
                "alpaca_trade_api",
                "anthropic",
                "langchain",
                "langgraph",
                "llm",
                "openai",
                "sklearn",
                "tensorflow",
                "torch",
                "transformers",
            ),
        )
        for module in _import_references()
    )


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
