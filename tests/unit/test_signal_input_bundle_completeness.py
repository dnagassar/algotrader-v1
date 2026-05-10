import ast
import random
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.signals import (
    SignalEvaluationInputSnapshot,
    SignalInputBundle,
    SignalInputBundleCompletenessResult,
    SignalInputValue,
    validate_signal_input_bundle_completeness,
)


MODULE_PATH = Path("src/algotrader/signals/signal_input_bundle_completeness.py")

AS_OF = datetime(2026, 5, 10, 14, 30, tzinfo=timezone.utc)
BUNDLE_AS_OF = datetime(2026, 5, 10, 14, 29, tzinfo=timezone.utc)
EARLIER = datetime(2026, 5, 10, 14, 28, tzinfo=timezone.utc)

_FORBIDDEN_COMPLETENESS_RESULT_FIELD_NAMES = {
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
    "feature",
    "feature_value",
    "fill",
    "fill_id",
    "fired",
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
    "signal_direction",
    "side",
    "strategy",
    "submit_order",
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
    "feature",
    "features",
    "fill",
    "fired",
    "llm",
    "llm_output",
    "ml",
    "model",
    "order",
    "output_value",
    "persistence",
    "portfolio",
    "position",
    "prediction",
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
    "signal_direction",
    "side",
    "strategy",
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


def signal_input_snapshot(**overrides: object) -> SignalEvaluationInputSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "snapshot:ask-momentum:20260510T143000Z",
        "as_of": AS_OF,
        "required_input_names": ("bar.close", "quote.ask"),
        "source_ids": ("bars.synthetic.v1", "quotes.synthetic.v1"),
    }
    values.update(overrides)
    return SignalEvaluationInputSnapshot(**values)


def signal_input_bundle(**overrides: object) -> SignalInputBundle:
    values: dict[str, object] = {
        "snapshot_id": "bundle:ask-momentum:20260510T143000Z",
        "as_of": AS_OF,
        "values": (
            signal_input_value(name="bar.close"),
            signal_input_value(name="quote.ask"),
        ),
    }
    values.update(overrides)
    return SignalInputBundle(**values)


def completeness_result(**overrides: object) -> SignalInputBundleCompletenessResult:
    values: dict[str, object] = {
        "snapshot_id": "snapshot:ask-momentum:20260510T143000Z",
        "bundle_snapshot_id": "bundle:ask-momentum:20260510T143000Z",
        "is_complete": False,
        "missing_input_names": ("bar.close",),
        "extra_input_names": ("market.is_open",),
    }
    values.update(overrides)
    return SignalInputBundleCompletenessResult(**values)


def test_completeness_result_contract_exists() -> None:
    result = completeness_result()

    assert isinstance(result, SignalInputBundleCompletenessResult)


def test_completeness_result_has_exact_minimal_fields_only() -> None:
    field_names = tuple(
        field.name for field in fields(SignalInputBundleCompletenessResult)
    )

    assert field_names == (
        "snapshot_id",
        "bundle_snapshot_id",
        "is_complete",
        "missing_input_names",
        "extra_input_names",
    )
    assert set(field_names).isdisjoint(_FORBIDDEN_COMPLETENESS_RESULT_FIELD_NAMES)


def test_completeness_result_is_frozen_and_slotted() -> None:
    result = completeness_result()

    assert hasattr(SignalInputBundleCompletenessResult, "__slots__")
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.is_complete = True


def test_completeness_result_tuple_fields_are_immutable() -> None:
    result = completeness_result()

    assert isinstance(result.missing_input_names, tuple)
    assert isinstance(result.extra_input_names, tuple)
    with pytest.raises(FrozenInstanceError):
        result.missing_input_names = ()
    with pytest.raises(FrozenInstanceError):
        result.extra_input_names = ()
    with pytest.raises(TypeError):
        result.missing_input_names[0] = "changed"
    with pytest.raises(TypeError):
        result.extra_input_names[0] = "changed"


def test_validation_function_exists() -> None:
    assert callable(validate_signal_input_bundle_completeness)


def test_complete_bundle_returns_complete_result() -> None:
    snapshot = signal_input_snapshot()
    bundle = signal_input_bundle()

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.is_complete is True
    assert result.missing_input_names == ()
    assert isinstance(result.missing_input_names, tuple)
    assert isinstance(result.extra_input_names, tuple)


def test_missing_required_input_returns_incomplete_result() -> None:
    snapshot = signal_input_snapshot()
    bundle = signal_input_bundle(
        values=(signal_input_value(name="quote.ask"),),
    )

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.is_complete is False
    assert result.missing_input_names == ("bar.close",)


def test_no_missing_names_returns_empty_tuple() -> None:
    result = validate_signal_input_bundle_completeness(
        signal_input_snapshot(required_input_names=("bar.close", "quote.ask")),
        signal_input_bundle(
            values=(
                signal_input_value(name="quote.ask"),
                signal_input_value(name="bar.close"),
            ),
        ),
    )

    assert result.is_complete is True
    assert result.missing_input_names == ()
    assert isinstance(result.missing_input_names, tuple)


def test_missing_input_names_preserve_snapshot_required_order() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=(
            "input.03.prior_close",
            "input.01.minute_close",
            "input.02.quote_ask",
            "input.04.market_state",
        ),
    )
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="input.01.minute_close"),
            signal_input_value(name="input.04.market_state"),
        ),
    )

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.missing_input_names == (
        "input.03.prior_close",
        "input.02.quote_ask",
    )


def test_repeated_calls_return_equal_missing_name_tuples() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("required.03", "required.01", "required.02"),
    )
    bundle = signal_input_bundle(values=(signal_input_value(name="required.02"),))

    results = tuple(
        validate_signal_input_bundle_completeness(snapshot, bundle)
        for _ in range(4)
    )

    assert tuple(result.missing_input_names for result in results) == (
        ("required.03", "required.01"),
        ("required.03", "required.01"),
        ("required.03", "required.01"),
        ("required.03", "required.01"),
    )


def test_missing_name_reporting_does_not_inspect_bundle_value_payloads() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("bar.close", "quote.ask", "market.is_open"),
    )
    first_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close", value=Decimal("101.2300")),
            signal_input_value(name="quote.ask", value="unexpected text payload"),
        ),
    )
    second_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close", value=False),
            signal_input_value(name="quote.ask", value=999),
        ),
    )

    first_result = validate_signal_input_bundle_completeness(snapshot, first_bundle)
    second_result = validate_signal_input_bundle_completeness(snapshot, second_bundle)

    assert first_result.missing_input_names == ("market.is_open",)
    assert second_result.missing_input_names == ("market.is_open",)
    assert first_result == second_result


def test_extra_input_names_preserve_bundle_value_order() -> None:
    snapshot = signal_input_snapshot(required_input_names=("bar.close",))
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="extra.02.market_state"),
            signal_input_value(name="bar.close"),
            signal_input_value(name="extra.01.volume"),
        ),
    )

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.extra_input_names == (
        "extra.02.market_state",
        "extra.01.volume",
    )


def test_repeated_calls_return_equal_extra_name_tuples() -> None:
    snapshot = signal_input_snapshot(required_input_names=("required",))
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="extra.03"),
            signal_input_value(name="required"),
            signal_input_value(name="extra.01"),
            signal_input_value(name="extra.02"),
        ),
    )

    results = tuple(
        validate_signal_input_bundle_completeness(snapshot, bundle)
        for _ in range(4)
    )

    assert tuple(result.extra_input_names for result in results) == (
        ("extra.03", "extra.01", "extra.02"),
        ("extra.03", "extra.01", "extra.02"),
        ("extra.03", "extra.01", "extra.02"),
        ("extra.03", "extra.01", "extra.02"),
    )


def test_extra_name_reporting_does_not_inspect_observed_values() -> None:
    snapshot = signal_input_snapshot(required_input_names=("bar.close",))
    first_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close", value=Decimal("101.2300")),
            signal_input_value(name="extra.value", value="not interpreted"),
        ),
    )
    second_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close", value=False),
            signal_input_value(name="extra.value", value=999),
        ),
    )

    first_result = validate_signal_input_bundle_completeness(snapshot, first_bundle)
    second_result = validate_signal_input_bundle_completeness(snapshot, second_bundle)

    assert first_result.extra_input_names == ("extra.value",)
    assert second_result.extra_input_names == ("extra.value",)
    assert first_result == second_result


def test_extra_input_names_do_not_make_result_incomplete_in_this_phase() -> None:
    snapshot = signal_input_snapshot(required_input_names=("bar.close",))
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close"),
            signal_input_value(name="extra.market_state"),
        ),
    )

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.is_complete is True
    assert result.missing_input_names == ()
    assert result.extra_input_names == ("extra.market_state",)


def test_missing_required_input_with_extras_remains_incomplete() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("bar.close", "quote.ask", "market.is_open"),
    )
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="quote.ask"),
            signal_input_value(name="extra.volume"),
            signal_input_value(name="extra.market_state"),
        ),
    )

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.is_complete is False
    assert result.missing_input_names == ("bar.close", "market.is_open")
    assert result.extra_input_names == ("extra.volume", "extra.market_state")


def test_all_required_inputs_present_plus_extras_returns_complete_with_extras() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("bar.close", "quote.ask"),
    )
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="extra.market_state"),
            signal_input_value(name="bar.close"),
            signal_input_value(name="quote.ask"),
            signal_input_value(name="extra.volume"),
        ),
    )

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.is_complete is True
    assert result.missing_input_names == ()
    assert result.extra_input_names == ("extra.market_state", "extra.volume")


def test_empty_extra_tuple_when_no_extras_exist() -> None:
    snapshot = signal_input_snapshot()
    bundle = signal_input_bundle()

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.extra_input_names == ()


def test_completeness_depends_only_on_names_not_values_sources_or_timestamps() -> None:
    snapshot = signal_input_snapshot(required_input_names=("bar.close", "quote.ask"))
    first_bundle = signal_input_bundle(
        values=(
            signal_input_value(
                name="bar.close",
                value=Decimal("101.2300"),
                observed_at=EARLIER,
                source_id="source.alpha",
            ),
            signal_input_value(
                name="quote.ask",
                value=True,
                observed_at=AS_OF,
                source_id="source.beta",
            ),
        ),
    )
    second_bundle = signal_input_bundle(
        values=(
            signal_input_value(
                name="bar.close",
                value="not a price",
                observed_at=AS_OF,
                source_id="source.gamma",
            ),
            signal_input_value(
                name="quote.ask",
                value=0,
                observed_at=EARLIER,
                source_id="source.delta",
            ),
        ),
    )

    first_result = validate_signal_input_bundle_completeness(snapshot, first_bundle)
    second_result = validate_signal_input_bundle_completeness(snapshot, second_bundle)

    assert first_result == second_result
    assert first_result.is_complete is True
    assert first_result.missing_input_names == ()
    assert first_result.extra_input_names == ()


def test_validation_preserves_snapshot_id_exactly() -> None:
    snapshot_id = " snapshot.raw:AskMomentum:2026-05-10T14:30:00Z "
    snapshot = signal_input_snapshot(snapshot_id=snapshot_id)
    bundle = signal_input_bundle()

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.snapshot_id is snapshot.snapshot_id
    assert result.snapshot_id == snapshot_id


def test_validation_preserves_bundle_snapshot_id_exactly() -> None:
    bundle_snapshot_id = " bundle.raw:AskMomentum:2026-05-10T14:30:00Z "
    snapshot = signal_input_snapshot()
    bundle = signal_input_bundle(snapshot_id=bundle_snapshot_id)

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.bundle_snapshot_id is bundle.snapshot_id
    assert result.bundle_snapshot_id == bundle_snapshot_id


def test_validation_does_not_require_snapshot_id_equality() -> None:
    snapshot = signal_input_snapshot(snapshot_id="snapshot:required-inputs")
    bundle = signal_input_bundle(snapshot_id="bundle:observed-values")

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.is_complete is True
    assert result.snapshot_id == "snapshot:required-inputs"
    assert result.bundle_snapshot_id == "bundle:observed-values"


def test_validation_does_not_require_as_of_equality() -> None:
    snapshot = signal_input_snapshot(as_of=AS_OF)
    bundle = signal_input_bundle(
        as_of=BUNDLE_AS_OF,
        values=(
            signal_input_value(name="bar.close", observed_at=EARLIER),
            signal_input_value(name="quote.ask", observed_at=EARLIER),
        ),
    )

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.is_complete is True
    assert result.missing_input_names == ()
    assert result.extra_input_names == ()


def test_validation_does_not_perform_lookahead_validation_against_snapshot_as_of() -> None:
    snapshot = signal_input_snapshot(
        as_of=EARLIER,
        required_input_names=("bar.close", "quote.ask"),
    )
    bundle = signal_input_bundle(
        as_of=AS_OF,
        values=(
            signal_input_value(name="bar.close", observed_at=AS_OF),
            signal_input_value(name="quote.ask", observed_at=AS_OF),
        ),
    )

    result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert result.is_complete is True
    assert result.missing_input_names == ()
    assert result.extra_input_names == ()


def test_validation_does_not_compare_source_ids() -> None:
    snapshot = signal_input_snapshot(required_input_names=("bar.close", "quote.ask"))
    first_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close", source_id="source.alpha"),
            signal_input_value(name="quote.ask", source_id="source.beta"),
        ),
    )
    second_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close", source_id="source.gamma"),
            signal_input_value(name="quote.ask", source_id="source.delta"),
        ),
    )

    first_result = validate_signal_input_bundle_completeness(snapshot, first_bundle)
    second_result = validate_signal_input_bundle_completeness(snapshot, second_bundle)

    assert first_result == second_result


def test_validation_does_not_compare_observed_at_values() -> None:
    snapshot = signal_input_snapshot(required_input_names=("bar.close", "quote.ask"))
    first_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close", observed_at=EARLIER),
            signal_input_value(name="quote.ask", observed_at=AS_OF),
        ),
    )
    second_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="bar.close", observed_at=AS_OF),
            signal_input_value(name="quote.ask", observed_at=EARLIER),
        ),
    )

    first_result = validate_signal_input_bundle_completeness(snapshot, first_bundle)
    second_result = validate_signal_input_bundle_completeness(snapshot, second_bundle)

    assert first_result == second_result


def test_validation_does_not_inspect_or_interpret_input_values() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("raw.decimal", "raw.text", "raw.flag"),
    )
    first_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="raw.decimal", value=Decimal("00101.2300")),
            signal_input_value(name="raw.text", value=" OPEN "),
            signal_input_value(name="raw.flag", value=True),
        ),
    )
    second_bundle = signal_input_bundle(
        values=(
            signal_input_value(name="raw.decimal", value=Decimal("999.9900")),
            signal_input_value(name="raw.text", value=" CLOSED "),
            signal_input_value(name="raw.flag", value=False),
        ),
    )

    first_result = validate_signal_input_bundle_completeness(snapshot, first_bundle)
    second_result = validate_signal_input_bundle_completeness(snapshot, second_bundle)

    assert first_result == second_result
    assert first_bundle.values[0].value == Decimal("00101.2300")
    assert first_bundle.values[1].value == " OPEN "
    assert first_bundle.values[2].value is True
    assert second_bundle.values[0].value == Decimal("999.9900")
    assert second_bundle.values[1].value == " CLOSED "
    assert second_bundle.values[2].value is False


def test_validation_does_not_mutate_input_snapshot() -> None:
    snapshot = signal_input_snapshot()
    original_required_input_names = snapshot.required_input_names
    original_source_ids = snapshot.source_ids

    validate_signal_input_bundle_completeness(snapshot, signal_input_bundle())

    assert snapshot.required_input_names is original_required_input_names
    assert snapshot.required_input_names == ("bar.close", "quote.ask")
    assert snapshot.source_ids is original_source_ids
    assert snapshot.source_ids == ("bars.synthetic.v1", "quotes.synthetic.v1")


def test_validation_does_not_mutate_input_bundle() -> None:
    first = signal_input_value(name="bar.close")
    second = signal_input_value(name="quote.ask")
    bundle = signal_input_bundle(values=(first, second))
    original_values = bundle.values

    validate_signal_input_bundle_completeness(signal_input_snapshot(), bundle)

    assert bundle.values is original_values
    assert bundle.values == (first, second)
    assert bundle.values[0] is first
    assert bundle.values[1] is second


def test_validation_does_not_mutate_underlying_signal_input_values() -> None:
    payload = Decimal("101.2300")
    observed_at = EARLIER
    value = signal_input_value(
        name="bar.close",
        value=payload,
        observed_at=observed_at,
        source_id="bars.synthetic.v1",
    )
    bundle = signal_input_bundle(values=(value, signal_input_value(name="quote.ask")))

    validate_signal_input_bundle_completeness(signal_input_snapshot(), bundle)

    assert value.name == "bar.close"
    assert value.value is payload
    assert value.observed_at is observed_at
    assert value.source_id == "bars.synthetic.v1"
    assert bundle.values[0] is value


def test_repeated_validation_leaves_all_inputs_unchanged() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("bar.close", "quote.ask", "market.is_open"),
    )
    first = signal_input_value(name="bar.close", value=Decimal("101.2300"))
    second = signal_input_value(name="quote.ask", value=" OPEN ")
    bundle = signal_input_bundle(values=(first, second))
    original_required_input_names = snapshot.required_input_names
    original_source_ids = snapshot.source_ids
    original_bundle_values = bundle.values

    for _ in range(5):
        validate_signal_input_bundle_completeness(snapshot, bundle)

    assert snapshot.required_input_names is original_required_input_names
    assert snapshot.source_ids is original_source_ids
    assert bundle.values is original_bundle_values
    assert bundle.values == (first, second)
    assert first.value == Decimal("101.2300")
    assert second.value == " OPEN "


def test_repeated_validation_calls_produce_equal_results() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("bar.close", "quote.ask", "market.is_open"),
    )
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="extra.volume"),
            signal_input_value(name="quote.ask"),
            signal_input_value(name="bar.close"),
            signal_input_value(name="extra.market_state"),
        ),
    )

    first_result = validate_signal_input_bundle_completeness(snapshot, bundle)
    second_result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert first_result == second_result
    assert first_result.missing_input_names == second_result.missing_input_names
    assert first_result.extra_input_names == second_result.extra_input_names


def test_deterministic_ordering_is_stable_across_repeated_calls() -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("required.c", "required.a", "required.b"),
    )
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="extra.z"),
            signal_input_value(name="required.b"),
            signal_input_value(name="extra.a"),
        ),
    )

    results = tuple(
        validate_signal_input_bundle_completeness(snapshot, bundle)
        for _ in range(3)
    )

    assert tuple(result.missing_input_names for result in results) == (
        ("required.c", "required.a"),
        ("required.c", "required.a"),
        ("required.c", "required.a"),
    )
    assert tuple(result.extra_input_names for result in results) == (
        ("extra.z", "extra.a"),
        ("extra.z", "extra.a"),
        ("extra.z", "extra.a"),
    )


def test_output_does_not_depend_on_environment_variables_or_random_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = signal_input_snapshot(
        required_input_names=("bar.close", "quote.ask", "market.is_open"),
    )
    bundle = signal_input_bundle(
        values=(
            signal_input_value(name="quote.ask"),
            signal_input_value(name="extra.volume"),
            signal_input_value(name="bar.close"),
        ),
    )

    monkeypatch.setenv("ALGOTRADER_COMPLETENESS_TEST_MODE", "before")
    random.seed(1)
    first_result = validate_signal_input_bundle_completeness(snapshot, bundle)

    monkeypatch.setenv("ALGOTRADER_COMPLETENESS_TEST_MODE", "after")
    random.seed(999)
    second_result = validate_signal_input_bundle_completeness(snapshot, bundle)

    assert first_result == second_result
    assert first_result.missing_input_names == ("market.is_open",)
    assert first_result.extra_input_names == ("extra.volume",)


def test_result_contract_has_no_signal_output_or_scoring_fields() -> None:
    field_names = {field.name for field in fields(SignalInputBundleCompletenessResult)}

    assert field_names.isdisjoint(
        {
            "actionable",
            "approved",
            "assumptions",
            "buy",
            "confidence",
            "diagnostics",
            "direction",
            "evaluator_kind",
            "fired",
            "is_noop",
            "limitations",
            "long",
            "output",
            "output_value",
            "priority",
            "probability",
            "rank",
            "reason_code",
            "rejected",
            "recommendation",
            "result_kind",
            "risk_approved",
            "score",
            "signal_direction",
            "should_trade",
            "short",
            "side",
            "sell",
        }
    )


def test_result_contract_has_no_risk_execution_broker_or_runtime_fields() -> None:
    field_names = {field.name for field in fields(SignalInputBundleCompletenessResult)}

    assert field_names.isdisjoint(
        {
            "account",
            "alpaca",
            "approved",
            "broker",
            "cash",
            "execution_intent",
            "execution_plan",
            "feature",
            "fill",
            "llm",
            "llm_output",
            "ml",
            "model",
            "order",
            "output",
            "persistence",
            "portfolio",
            "position",
            "prediction",
            "risk",
            "risk_approved",
            "runtime",
            "scheduler",
            "submit_order",
        }
    )


def test_contract_module_has_no_forbidden_downstream_or_external_imports() -> None:
    assert not any(
        _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
        for module in _import_references()
    )


def test_contract_module_has_no_forbidden_trading_path_references() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_contract_module_has_no_forbidden_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_contract_module_does_not_reference_signal_input_value_payload_attr() -> None:
    assert "value" not in _attribute_names()


def test_contract_module_has_no_hidden_wall_clock_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_WALL_CLOCK_CALL_NAMES)


def test_contract_module_has_no_hidden_random_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_RANDOM_CALL_NAMES)


def test_contract_module_has_no_hidden_environment_variable_reads() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_ENVIRONMENT_CALL_NAMES)


def test_contract_module_has_no_hidden_network_or_socket_access() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_NETWORK_CALL_NAMES)


def test_contract_module_has_no_hidden_filesystem_database_or_persistence_writes() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_FILESYSTEM_WRITE_CALL_NAMES)


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


def _attribute_names() -> set[str]:
    return {
        node.attr
        for node in ast.walk(_tree())
        if isinstance(node, ast.Attribute)
    }


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
