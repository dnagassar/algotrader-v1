import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.signals import (
    SignalEvaluationInputSnapshot,
    SignalInputBundle,
    SignalInputValue,
)


MODULE_PATH = Path("src/algotrader/signals/signal_input_bundle.py")

AS_OF = datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc)
EARLIER = datetime(2026, 5, 9, 14, 29, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 9, 14, 31, tzinfo=timezone.utc)
EASTERN_TIME = datetime(2026, 5, 9, 10, 30, tzinfo=timezone(timedelta(hours=-4)))

_FORBIDDEN_SIGNAL_INPUT_BUNDLE_FIELD_NAMES = {
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
    "rank",
    "recommendation",
    "rejected",
    "result_kind",
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
    "is_noop",
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
    "algotrader.signals.base",
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
    "SignalEvaluationInputSnapshot",
    "SignalEvaluationResult",
    "SignalRiskEvaluation",
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
    "evaluator",
    "evaluator_kind",
    "execution",
    "execution_intent",
    "execution_plan",
    "fill",
    "fired",
    "feature",
    "features",
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
    "rank",
    "rejected",
    "result_kind",
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
    "is_noop",
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
        "observed_at": EARLIER,
        "source_id": "quotes.synthetic.v1",
    }
    values.update(overrides)
    return SignalInputValue(**values)


def signal_input_bundle(**overrides: object) -> SignalInputBundle:
    values: dict[str, object] = {
        "snapshot_id": "snapshot:ask-momentum:20260509T143000Z",
        "as_of": AS_OF,
        "values": (signal_input_value(),),
    }
    values.update(overrides)
    return SignalInputBundle(**values)


def test_signal_input_bundle_exists() -> None:
    bundle = signal_input_bundle()

    assert isinstance(bundle, SignalInputBundle)


def test_signal_input_bundle_is_frozen_and_slotted() -> None:
    bundle = signal_input_bundle()

    assert hasattr(SignalInputBundle, "__slots__")
    assert not hasattr(bundle, "__dict__")
    with pytest.raises(FrozenInstanceError):
        bundle.snapshot_id = "changed"


def test_signal_input_bundle_fields_cannot_be_reassigned() -> None:
    bundle = signal_input_bundle()

    with pytest.raises(FrozenInstanceError):
        bundle.snapshot_id = "changed"
    with pytest.raises(FrozenInstanceError):
        bundle.as_of = datetime(2026, 5, 9, 15, 0, tzinfo=timezone.utc)
    with pytest.raises(FrozenInstanceError):
        bundle.values = ()


def test_signal_input_bundle_has_exact_minimal_fields_only() -> None:
    field_names = tuple(field.name for field in fields(SignalInputBundle))

    assert field_names == ("snapshot_id", "as_of", "values")
    assert set(field_names).isdisjoint(_FORBIDDEN_SIGNAL_INPUT_BUNDLE_FIELD_NAMES)


def test_valid_construction_preserves_metadata_and_values() -> None:
    as_of = datetime(2026, 5, 9, 15, 45, tzinfo=timezone.utc)
    first = signal_input_value(name="bar.close", observed_at=as_of)
    second = signal_input_value(name="quote.ask", observed_at=EARLIER)

    bundle = signal_input_bundle(
        snapshot_id=" snapshot.raw:AskMomentum:2026-05-09T15:45:00Z ",
        as_of=as_of,
        values=[first, second],
    )

    assert bundle.snapshot_id == " snapshot.raw:AskMomentum:2026-05-09T15:45:00Z "
    assert bundle.as_of is as_of
    assert bundle.values == (first, second)
    assert bundle.values[0] is first
    assert bundle.values[1] is second


def test_bundle_preserves_full_value_traceability_without_interpretation() -> None:
    close_payload = Decimal("00101.2300")
    market_state_payload = " OPEN "
    close_observed_at = datetime(2026, 5, 9, 14, 28, tzinfo=timezone.utc)
    market_state_observed_at = datetime(2026, 5, 9, 14, 29, tzinfo=timezone.utc)
    close_source_id = " Source:bars.synthetic.v1 "
    market_state_source_id = " Source:market_state.synthetic.v1 "
    close = signal_input_value(
        name=" Input:BAR.close ",
        value=close_payload,
        observed_at=close_observed_at,
        source_id=close_source_id,
    )
    market_state = signal_input_value(
        name=" Input:MARKET.state ",
        value=market_state_payload,
        observed_at=market_state_observed_at,
        source_id=market_state_source_id,
    )

    bundle = signal_input_bundle(values=[close, market_state])

    assert bundle.values == (close, market_state)
    assert bundle.values[0] is close
    assert bundle.values[1] is market_state
    assert bundle.values[0].name == " Input:BAR.close "
    assert bundle.values[0].source_id is close_source_id
    assert bundle.values[0].observed_at is close_observed_at
    assert bundle.values[0].value is close_payload
    assert bundle.values[0].value.as_tuple() == close_payload.as_tuple()
    assert bundle.values[1].name == " Input:MARKET.state "
    assert bundle.values[1].source_id is market_state_source_id
    assert bundle.values[1].observed_at is market_state_observed_at
    assert bundle.values[1].value is market_state_payload


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValidationError, match="as_of"):
        signal_input_bundle(as_of=datetime(2026, 5, 9, 14, 30))


def test_non_utc_aware_as_of_is_rejected() -> None:
    with pytest.raises(ValidationError, match="as_of"):
        signal_input_bundle(as_of=EASTERN_TIME)


def test_as_of_identity_is_preserved_exactly() -> None:
    as_of = datetime(2026, 5, 9, 15, 45, tzinfo=timezone.utc)

    bundle = signal_input_bundle(as_of=as_of)

    assert bundle.as_of is as_of


@pytest.mark.parametrize("snapshot_id", ("", " "))
def test_empty_or_blank_snapshot_id_is_rejected(snapshot_id: str) -> None:
    with pytest.raises(ValidationError, match="snapshot_id"):
        signal_input_bundle(snapshot_id=snapshot_id)


def test_snapshot_id_string_is_preserved_exactly() -> None:
    snapshot_id = " snapshot.raw:AskMomentum:2026-05-09T14:30:00Z "

    bundle = signal_input_bundle(snapshot_id=snapshot_id)

    assert bundle.snapshot_id is snapshot_id
    assert bundle.snapshot_id == snapshot_id


def test_values_are_coerced_to_tuple_from_iterable() -> None:
    first = signal_input_value(name="bar.close")
    second = signal_input_value(name="quote.ask")

    bundle = signal_input_bundle(values=(value for value in [first, second]))

    assert isinstance(bundle.values, tuple)
    assert bundle.values == (first, second)


def test_list_values_are_coerced_to_tuple() -> None:
    values = [
        signal_input_value(name="bar.close"),
        signal_input_value(name="quote.ask"),
    ]

    bundle = signal_input_bundle(values=values)

    assert isinstance(bundle.values, tuple)
    assert bundle.values == tuple(values)


def test_tuple_values_remain_tuple_ordered_values() -> None:
    values = (
        signal_input_value(name="bar.close"),
        signal_input_value(name="quote.ask"),
    )

    bundle = signal_input_bundle(values=values)

    assert isinstance(bundle.values, tuple)
    assert bundle.values == values


def test_values_ordering_is_preserved_exactly() -> None:
    values = [
        signal_input_value(name="input.03.prior_session_close"),
        signal_input_value(name="input.01.minute_bar_close"),
        signal_input_value(name="input.02.quote_ask"),
    ]

    bundle = signal_input_bundle(values=values)

    assert bundle.values == tuple(values)


def test_multiple_bundles_from_same_values_in_same_order_compare_equal() -> None:
    values = (
        signal_input_value(name="bar.close"),
        signal_input_value(name="quote.ask"),
    )

    first_bundle = signal_input_bundle(values=values)
    second_bundle = signal_input_bundle(values=values)

    assert first_bundle == second_bundle
    assert first_bundle.values == second_bundle.values
    assert first_bundle.values[0] is second_bundle.values[0]
    assert first_bundle.values[1] is second_bundle.values[1]


def test_bundles_from_same_values_in_different_orders_preserve_different_order() -> None:
    first = signal_input_value(name="bar.close")
    second = signal_input_value(name="quote.ask")

    original_order = signal_input_bundle(values=(first, second))
    reversed_order = signal_input_bundle(values=(second, first))

    assert original_order.values == (first, second)
    assert reversed_order.values == (second, first)
    assert original_order != reversed_order


def test_input_value_object_identity_is_preserved() -> None:
    first = signal_input_value(name="bar.close")
    second = signal_input_value(name="quote.ask")

    bundle = signal_input_bundle(values=[first, second])

    assert bundle.values[0] is first
    assert bundle.values[1] is second


def test_values_tuple_is_immutable_after_construction() -> None:
    bundle = signal_input_bundle()

    with pytest.raises(FrozenInstanceError):
        bundle.values = ()
    with pytest.raises(TypeError):
        bundle.values[0] = signal_input_value(name="changed")


def test_original_input_list_mutation_does_not_affect_constructed_bundle() -> None:
    first = signal_input_value(name="bar.close")
    second = signal_input_value(name="quote.ask")
    values = [first, second]

    bundle = signal_input_bundle(values=values)
    values[0] = signal_input_value(name="mutated.input")
    values.append(signal_input_value(name="late.input"))

    assert bundle.values == (first, second)
    assert bundle.values[0] is first
    assert bundle.values[1] is second


def test_empty_values_are_rejected() -> None:
    with pytest.raises(ValidationError, match="values"):
        signal_input_bundle(values=())


def test_duplicate_signal_input_value_names_are_rejected() -> None:
    first = signal_input_value(name="quote.ask", source_id="quotes.first")
    second = signal_input_value(name="quote.ask", source_id="quotes.second")

    with pytest.raises(ValidationError, match="duplicate"):
        signal_input_bundle(values=(first, second))


def test_duplicate_names_are_rejected_even_when_observed_values_differ() -> None:
    first = signal_input_value(name="quote.ask", value=Decimal("101.23"))
    second = signal_input_value(name="quote.ask", value=Decimal("102.34"))

    with pytest.raises(ValidationError, match="duplicate"):
        signal_input_bundle(values=(first, second))


def test_duplicate_names_are_rejected_even_when_observed_at_differs() -> None:
    first = signal_input_value(name="quote.ask", observed_at=EARLIER)
    second = signal_input_value(name="quote.ask", observed_at=AS_OF)

    with pytest.raises(ValidationError, match="duplicate"):
        signal_input_bundle(values=(first, second))


def test_duplicate_name_detection_preserves_exact_case_and_whitespace_contract() -> None:
    lowercase = signal_input_value(name="quote.ask")
    uppercase = signal_input_value(name="QUOTE.ASK")
    padded = signal_input_value(name=" quote.ask ")

    bundle = signal_input_bundle(values=(lowercase, uppercase, padded))

    assert bundle.values == (lowercase, uppercase, padded)
    assert tuple(value.name for value in bundle.values) == (
        "quote.ask",
        "QUOTE.ASK",
        " quote.ask ",
    )


def test_accepts_value_observed_at_before_bundle_as_of() -> None:
    value = signal_input_value(observed_at=EARLIER)

    bundle = signal_input_bundle(values=(value,))

    assert bundle.values == (value,)


def test_accepts_all_values_observed_before_bundle_as_of() -> None:
    first = signal_input_value(
        name="bar.close",
        observed_at=datetime(2026, 5, 9, 14, 27, tzinfo=timezone.utc),
    )
    second = signal_input_value(
        name="quote.ask",
        observed_at=datetime(2026, 5, 9, 14, 28, tzinfo=timezone.utc),
    )

    bundle = signal_input_bundle(values=(first, second))

    assert bundle.values == (first, second)


def test_accepts_value_observed_at_equal_to_bundle_as_of() -> None:
    value = signal_input_value(observed_at=AS_OF)

    bundle = signal_input_bundle(values=(value,))

    assert bundle.values == (value,)


def test_accepts_all_values_observed_equal_to_bundle_as_of() -> None:
    first = signal_input_value(name="bar.close", observed_at=AS_OF)
    second = signal_input_value(name="quote.ask", observed_at=AS_OF)

    bundle = signal_input_bundle(values=(first, second))

    assert bundle.values == (first, second)


def test_rejects_value_observed_at_after_bundle_as_of() -> None:
    value = signal_input_value(observed_at=LATER)

    with pytest.raises(ValidationError, match="observed_at"):
        signal_input_bundle(values=(value,))


def test_rejects_one_future_value_among_otherwise_valid_values() -> None:
    valid_before = signal_input_value(name="bar.close", observed_at=EARLIER)
    future = signal_input_value(name="quote.ask", observed_at=LATER)
    valid_equal = signal_input_value(name="market.is_open", observed_at=AS_OF)

    with pytest.raises(ValidationError, match="observed_at"):
        signal_input_bundle(values=(valid_before, future, valid_equal))


def test_rejecting_future_value_does_not_mutate_input_values_or_list() -> None:
    valid = signal_input_value(name="bar.close", observed_at=EARLIER)
    future = signal_input_value(name="quote.ask", observed_at=LATER)
    values = [valid, future]

    with pytest.raises(ValidationError, match="observed_at"):
        signal_input_bundle(values=values)

    assert values == [valid, future]
    assert values[0] is valid
    assert values[1] is future
    assert valid.observed_at is EARLIER
    assert future.observed_at is LATER


def test_does_not_perform_completeness_validation_against_input_snapshot() -> None:
    snapshot = SignalEvaluationInputSnapshot(
        snapshot_id="snapshot:ask-momentum:20260509T143000Z",
        as_of=AS_OF,
        required_input_names=("bar.close", "quote.ask"),
        source_ids=("bars.synthetic.v1", "quotes.synthetic.v1"),
    )
    value = signal_input_value(name="quote.ask")

    bundle = signal_input_bundle(
        snapshot_id=snapshot.snapshot_id,
        as_of=snapshot.as_of,
        values=(value,),
    )

    assert bundle.snapshot_id == snapshot.snapshot_id
    assert bundle.as_of is snapshot.as_of
    assert bundle.values == (value,)
    assert not hasattr(bundle, "required_input_names")
    assert not hasattr(bundle, "source_ids")


def test_bundle_does_not_require_signal_evaluation_input_snapshot() -> None:
    bundle = signal_input_bundle()

    assert isinstance(bundle, SignalInputBundle)
    assert bundle.snapshot_id == "snapshot:ask-momentum:20260509T143000Z"


def test_bundle_does_not_check_required_input_names_or_reject_extra_inputs() -> None:
    value = signal_input_value(name="unexpected.extra.input")

    bundle = signal_input_bundle(values=(value,))

    assert bundle.values == (value,)
    assert not hasattr(bundle, "required_input_names")
    assert not hasattr(bundle, "extra_input_names")
    assert not hasattr(bundle, "missing_input_names")


def test_contract_exposes_no_completeness_result_surface() -> None:
    bundle = signal_input_bundle()

    for field_name in (
        "complete",
        "is_complete",
        "completeness",
        "completeness_status",
        "missing_inputs",
        "missing_input_names",
        "extra_inputs",
        "extra_input_names",
        "required_input_names",
        "source_ids",
    ):
        assert not hasattr(bundle, field_name)

    for method_name in (
        "validate_against_snapshot",
        "check_required_inputs",
        "missing_inputs",
        "extra_inputs",
        "is_complete",
    ):
        assert not hasattr(bundle, method_name)


def test_contract_exposes_no_signal_output_behavior() -> None:
    bundle = signal_input_bundle()

    for field_name in (
        "output_value",
        "reason_code",
        "diagnostics",
        "assumptions",
        "limitations",
        "signal",
        "signal_output",
        "recommendation",
        "result_kind",
        "evaluator_kind",
        "is_noop",
    ):
        assert not hasattr(bundle, field_name)


def test_contract_exposes_no_score_direction_confidence_or_actionability_fields() -> None:
    bundle = signal_input_bundle()

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
        "result_kind",
        "evaluator_kind",
        "is_noop",
    ):
        assert not hasattr(bundle, field_name)


def test_contract_has_no_evaluated_at_or_current_time_availability_surface() -> None:
    bundle = signal_input_bundle()

    for field_name in (
        "evaluated_at",
        "current_time",
        "clock",
        "now",
        "available_at",
    ):
        assert not hasattr(bundle, field_name)


def test_contract_exposes_no_trading_path_fields() -> None:
    bundle = signal_input_bundle()

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
        "feature",
        "features",
        "signal_result",
        "evaluator",
    ):
        assert not hasattr(bundle, field_name)


def test_contract_has_no_signal_feature_strategy_or_trading_methods() -> None:
    bundle = signal_input_bundle()

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
        assert not hasattr(bundle, method_name)


def test_contract_module_imports_no_forbidden_downstream_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_does_not_depend_on_input_snapshot_or_evaluator_modules() -> None:
    assert "algotrader.signals.signal_evaluation_input" not in _import_references()
    assert "algotrader.signals.noop_signal_evaluator" not in _import_references()
    assert "SignalEvaluationInputSnapshot" not in _referenced_names()
    assert "NoOpSignalEvaluator" not in _referenced_names()


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
