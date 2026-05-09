import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.signals import SignalEvaluationInputSnapshot


MODULE_PATH = Path("src/algotrader/signals/signal_evaluation_input.py")

AS_OF = datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc)
EASTERN_TIME = datetime(2026, 5, 9, 10, 30, tzinfo=timezone(timedelta(hours=-4)))

_FORBIDDEN_SIGNAL_EVALUATION_INPUT_FIELD_NAMES = {
    "account_id",
    "alpaca",
    "approved",
    "broker_order_id",
    "buying_power",
    "cash",
    "client_order_id",
    "confidence",
    "execution_intent",
    "execution_plan",
    "fill_id",
    "limit_price",
    "llm",
    "notional",
    "order_type",
    "portfolio",
    "position_id",
    "priority",
    "quantity",
    "rank",
    "rejected",
    "risk_approved",
    "score",
    "side",
    "signal_direction",
    "stop_price",
    "symbol",
    "time_in_force",
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
    "account_id",
    "alpaca",
    "approved",
    "broker",
    "broker_order_id",
    "buying_power",
    "cash",
    "client_order_id",
    "confidence",
    "execution_intent",
    "execution_plan",
    "fill",
    "fill_id",
    "limit_price",
    "llm",
    "ml_model",
    "notional",
    "order",
    "order_type",
    "portfolio",
    "position_id",
    "priority",
    "quantity",
    "rank",
    "rejected",
    "risk_approved",
    "score",
    "scheduler",
    "side",
    "signal_direction",
    "stop_price",
    "strategy",
    "submit_order",
    "symbol",
    "time_in_force",
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


def signal_evaluation_input_snapshot(
    **overrides: object,
) -> SignalEvaluationInputSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "snapshot:ask-momentum:20260509T143000Z",
        "as_of": AS_OF,
        "required_input_names": ("bar.close", "quote.ask"),
        "source_ids": ("bars.synthetic.v1", "quotes.synthetic.v1"),
    }
    values.update(overrides)
    return SignalEvaluationInputSnapshot(**values)


def test_signal_evaluation_input_snapshot_exists() -> None:
    snapshot = signal_evaluation_input_snapshot()

    assert isinstance(snapshot, SignalEvaluationInputSnapshot)


def test_signal_evaluation_input_snapshot_is_frozen_and_slotted() -> None:
    snapshot = signal_evaluation_input_snapshot()

    assert hasattr(SignalEvaluationInputSnapshot, "__slots__")
    assert not hasattr(snapshot, "__dict__")
    with pytest.raises(FrozenInstanceError):
        snapshot.snapshot_id = "changed"


def test_signal_evaluation_input_snapshot_has_exact_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(SignalEvaluationInputSnapshot))

    assert field_names == (
        "snapshot_id",
        "as_of",
        "required_input_names",
        "source_ids",
    )
    assert set(field_names).isdisjoint(_FORBIDDEN_SIGNAL_EVALUATION_INPUT_FIELD_NAMES)


def test_valid_construction_preserves_metadata() -> None:
    snapshot = signal_evaluation_input_snapshot()

    assert snapshot.snapshot_id == "snapshot:ask-momentum:20260509T143000Z"
    assert snapshot.as_of is AS_OF
    assert snapshot.required_input_names == ("bar.close", "quote.ask")
    assert snapshot.source_ids == ("bars.synthetic.v1", "quotes.synthetic.v1")


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValidationError, match="as_of"):
        signal_evaluation_input_snapshot(as_of=datetime(2026, 5, 9, 14, 30))


def test_non_utc_aware_as_of_is_rejected() -> None:
    with pytest.raises(ValidationError, match="as_of"):
        signal_evaluation_input_snapshot(as_of=EASTERN_TIME)


def test_as_of_identity_is_preserved_exactly() -> None:
    as_of = datetime(2026, 5, 9, 15, 45, tzinfo=timezone.utc)

    snapshot = signal_evaluation_input_snapshot(as_of=as_of)

    assert snapshot.as_of is as_of


def test_required_input_names_are_coerced_to_tuple() -> None:
    snapshot = signal_evaluation_input_snapshot(
        required_input_names=["bar.close", "quote.ask"],
    )

    assert isinstance(snapshot.required_input_names, tuple)
    assert snapshot.required_input_names == ("bar.close", "quote.ask")


def test_source_ids_are_coerced_to_tuple() -> None:
    snapshot = signal_evaluation_input_snapshot(
        source_ids=["bars.synthetic.v1", "quotes.synthetic.v1"],
    )

    assert isinstance(snapshot.source_ids, tuple)
    assert snapshot.source_ids == ("bars.synthetic.v1", "quotes.synthetic.v1")


def test_tuple_input_ordering_is_preserved() -> None:
    snapshot = signal_evaluation_input_snapshot(
        required_input_names=[
            "minute_bar.close",
            "quote.ask",
            "prior_session.close",
        ],
        source_ids=[
            "source.first",
            "source.second",
            "source.third",
        ],
    )

    assert snapshot.required_input_names == (
        "minute_bar.close",
        "quote.ask",
        "prior_session.close",
    )
    assert snapshot.source_ids == (
        "source.first",
        "source.second",
        "source.third",
    )


def test_tuple_fields_are_immutable_after_construction() -> None:
    snapshot = signal_evaluation_input_snapshot()

    with pytest.raises(FrozenInstanceError):
        snapshot.required_input_names = ()
    with pytest.raises(FrozenInstanceError):
        snapshot.source_ids = ()
    with pytest.raises(TypeError):
        snapshot.required_input_names[0] = "changed"
    with pytest.raises(TypeError):
        snapshot.source_ids[0] = "changed"


@pytest.mark.parametrize("snapshot_id", ("", " "))
def test_empty_or_blank_snapshot_id_is_rejected(snapshot_id: str) -> None:
    with pytest.raises(ValidationError, match="snapshot_id"):
        signal_evaluation_input_snapshot(snapshot_id=snapshot_id)


@pytest.mark.parametrize(
    "required_input_names",
    (
        ("bar.close", ""),
        ("bar.close", " "),
    ),
)
def test_empty_or_blank_required_input_names_are_rejected(
    required_input_names: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError, match="required_input_names"):
        signal_evaluation_input_snapshot(required_input_names=required_input_names)


@pytest.mark.parametrize(
    "source_ids",
    (
        ("bars.synthetic.v1", ""),
        ("bars.synthetic.v1", " "),
    ),
)
def test_empty_or_blank_source_ids_are_rejected(
    source_ids: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError, match="source_ids"):
        signal_evaluation_input_snapshot(source_ids=source_ids)


@pytest.mark.parametrize("field_name", ("required_input_names", "source_ids"))
def test_tuple_fields_reject_single_string_values(field_name: str) -> None:
    with pytest.raises(ValidationError):
        signal_evaluation_input_snapshot(**{field_name: "single value"})


def test_input_collections_are_copied_to_immutable_tuples() -> None:
    required_input_names = ["bar.close"]
    source_ids = ["bars.synthetic.v1"]

    snapshot = signal_evaluation_input_snapshot(
        required_input_names=required_input_names,
        source_ids=source_ids,
    )
    required_input_names.append("quote.ask")
    source_ids.append("quotes.synthetic.v1")

    assert snapshot.required_input_names == ("bar.close",)
    assert snapshot.source_ids == ("bars.synthetic.v1",)


def test_traceability_string_values_are_preserved_exactly() -> None:
    snapshot = signal_evaluation_input_snapshot(
        snapshot_id=" snapshot.raw:AskMomentum:2026-05-09T14:30:00Z ",
        required_input_names=[
            " Input:BAR.close ",
            "Input:QUOTE.ask",
        ],
        source_ids=[
            " Source:bars.synthetic.v1 ",
            "Source:quotes.synthetic.v1",
        ],
    )

    assert snapshot.snapshot_id == " snapshot.raw:AskMomentum:2026-05-09T14:30:00Z "
    assert snapshot.required_input_names == (
        " Input:BAR.close ",
        "Input:QUOTE.ask",
    )
    assert snapshot.source_ids == (
        " Source:bars.synthetic.v1 ",
        "Source:quotes.synthetic.v1",
    )


def test_contract_exposes_only_metadata_reference_surface_area() -> None:
    snapshot = signal_evaluation_input_snapshot()

    assert snapshot.snapshot_id == "snapshot:ask-momentum:20260509T143000Z"
    assert snapshot.as_of is AS_OF
    assert snapshot.required_input_names == ("bar.close", "quote.ask")
    assert snapshot.source_ids == ("bars.synthetic.v1", "quotes.synthetic.v1")
    for field_name in _FORBIDDEN_SIGNAL_EVALUATION_INPUT_FIELD_NAMES:
        assert not hasattr(snapshot, field_name)


def test_contract_exposes_no_signal_output_fields() -> None:
    snapshot = signal_evaluation_input_snapshot()

    for field_name in (
        "output_value",
        "reason_code",
        "diagnostics",
        "assumptions",
        "limitations",
        "signal",
        "signal_output",
        "buy_signal",
        "sell_signal",
        "hold_signal",
        "recommendation",
        "score",
        "confidence",
        "signal_direction",
    ):
        assert not hasattr(snapshot, field_name)


def test_contract_exposes_no_order_risk_execution_or_broker_fields() -> None:
    snapshot = signal_evaluation_input_snapshot()

    for field_name in (
        "symbol",
        "side",
        "quantity",
        "notional",
        "order_type",
        "limit_price",
        "stop_price",
        "time_in_force",
        "broker_order_id",
        "client_order_id",
        "account_id",
        "position_id",
        "fill_id",
        "risk_approved",
        "approved",
        "rejected",
        "rank",
        "priority",
        "execution_intent",
        "execution_plan",
        "portfolio",
        "cash",
        "buying_power",
        "alpaca",
        "llm",
    ):
        assert not hasattr(snapshot, field_name)


def test_contract_has_no_signal_feature_or_strategy_behavior() -> None:
    snapshot = signal_evaluation_input_snapshot()

    for method_name in (
        "evaluate",
        "compute_signal",
        "generate_signal",
        "compute_feature",
        "build_features",
        "apply_strategy",
        "allocate",
        "size_position",
        "rank",
        "prioritize",
    ):
        assert not hasattr(snapshot, method_name)


def test_contract_has_no_runtime_persistence_ml_or_llm_behavior() -> None:
    snapshot = signal_evaluation_input_snapshot()

    for method_name in (
        "schedule",
        "run",
        "persist",
        "save",
        "write",
        "to_sql",
        "predict",
        "fit",
        "train",
        "llm",
        "prompt",
    ):
        assert not hasattr(snapshot, method_name)


def test_contract_module_imports_no_downstream_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_references_no_trading_path_runtime_or_external_types() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_creating_snapshot_performs_no_hidden_io_network_runtime_or_broker_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)

    snapshot = signal_evaluation_input_snapshot()

    assert snapshot.snapshot_id == "snapshot:ask-momentum:20260509T143000Z"


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
