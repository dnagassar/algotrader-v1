import ast
import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.orchestration.execution_planning_flow import (
    ExecutionPlan,
    build_execution_plan,
)
from algotrader.orchestration.risk_execution_flow import ExecutionIntent
from algotrader.orchestration.signal_risk_flow import SignalRiskEvaluation
from algotrader.risk.state import RiskVerdict


NOW = datetime(2026, 5, 6, tzinfo=timezone.utc)
MODULE_PATH = Path("src/algotrader/orchestration/execution_planning_flow.py")

_FORBIDDEN_PLAN_FIELD_NAMES = {
    "accepted_intents",
    "account_id",
    "alpaca_order",
    "broker",
    "broker_name",
    "broker_order_id",
    "broker_order_ids",
    "buying_power_reserved",
    "cash_reserved",
    "client_order_id",
    "client_order_ids",
    "fill",
    "fill_price",
    "fill_quantity",
    "filled_at",
    "idempotency_key",
    "idempotency_keys",
    "native_order",
    "order",
    "orders",
    "persisted_at",
    "priorities",
    "priority",
    "quantities",
    "quantity",
    "rank",
    "ranks",
    "rejected_intents",
    "risk",
    "risks",
    "sdk_order",
    "selected_intents",
    "side",
    "sides",
    "skipped_intents",
    "status",
    "statuses",
    "submitted_at",
    "symbol",
    "symbols",
    "venue",
}


def bar(symbol: str, close: str = "100") -> Bar:
    return Bar(symbol, NOW, close, close, close, close, "1000")


def quote(symbol: str, ask: str = "100.10") -> Quote:
    return Quote(symbol, NOW, bid=ask, ask=ask)


def order(symbol: str, quantity: str = "1") -> ProposedOrder:
    return ProposedOrder(symbol, OrderSide.BUY, OrderType.MARKET, quantity)


def risk_approved(
    symbol: str,
    quantity: str = "1",
    order_notional: str = "100.10",
) -> SignalRiskEvaluation:
    return SignalRiskEvaluation(
        symbol=symbol,
        previous_bar=bar(symbol),
        quote=quote(symbol),
        order=order(symbol, quantity),
        risk=RiskVerdict.allow(Decimal(order_notional)),
        status="risk_approved",
    )


def intent(
    symbol: str,
    quantity: str = "1",
    order_notional: str = "100.10",
) -> ExecutionIntent:
    return ExecutionIntent(
        source_evaluation=risk_approved(symbol, quantity, order_notional)
    )


def test_empty_input_returns_execution_plan_with_empty_intents_tuple() -> None:
    plan = build_execution_plan(())

    assert plan == ExecutionPlan(intents=())
    assert plan.intents == ()
    assert isinstance(plan.intents, tuple)


def test_one_intent_is_preserved() -> None:
    original = intent("MSFT")

    plan = build_execution_plan((original,))

    assert plan.intents == (original,)
    assert plan.intents[0] is original


def test_multiple_intents_preserve_order() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    third = intent("NVDA")

    plan = build_execution_plan((first, second, third))

    assert plan.intents == (first, second, third)


def test_each_plan_intent_entry_preserves_original_identity() -> None:
    first = intent("MSFT")
    second = intent("AAPL")

    plan = build_execution_plan([first, second])

    assert plan.intents[0] is first
    assert plan.intents[1] is second
    assert plan.intents[0].source_evaluation is first.source_evaluation
    assert plan.intents[1].source_evaluation is second.source_evaluation


def test_output_intents_are_a_tuple() -> None:
    plan = build_execution_plan([intent("MSFT")])

    assert isinstance(plan.intents, tuple)


def test_execution_plan_is_frozen() -> None:
    plan = build_execution_plan([intent("MSFT")])

    with pytest.raises(FrozenInstanceError):
        plan.intents = ()


def test_input_collection_is_not_mutated() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    intents = [first, second]
    snapshot = tuple(intents)

    plan = build_execution_plan(intents)

    assert intents == list(snapshot)
    assert intents[0] is first
    assert intents[1] is second
    assert plan.intents == snapshot


def test_builder_accepts_any_iterable() -> None:
    first = intent("MSFT")
    second = intent("AAPL")

    plan = build_execution_plan(item for item in (first, second))

    assert plan.intents == (first, second)
    assert plan.intents[0] is first
    assert plan.intents[1] is second


def test_same_symbol_intents_are_preserved_without_conflict_resolution() -> None:
    first = intent("MSFT", quantity="1")
    second = intent("MSFT", quantity="2")

    plan = build_execution_plan((first, second))

    assert plan.intents == (first, second)
    assert plan.intents[0] is first
    assert plan.intents[1] is second


def test_multiple_intents_are_not_batch_cash_reserved_or_affordability_checked() -> None:
    batch_cash = Decimal("100")
    first = intent("MSFT", order_notional="80")
    second = intent("AAPL", order_notional="80")
    approved_notional = sum(
        item.source_evaluation.risk.order_notional
        for item in (first, second)
        if item.source_evaluation.risk is not None
    )

    plan = build_execution_plan((first, second))

    assert approved_notional > batch_cash
    assert plan.intents == (first, second)
    assert not hasattr(plan, "cash_reserved")
    assert not hasattr(plan, "buying_power_reserved")


def test_execution_plan_has_exactly_one_intents_field() -> None:
    plan_fields = fields(ExecutionPlan)
    field_names = tuple(field.name for field in plan_fields)

    assert field_names == ("intents",)
    assert len(plan_fields) == 1
    assert set(field_names).isdisjoint(_FORBIDDEN_PLAN_FIELD_NAMES)


def test_execution_plan_has_no_direct_policy_or_traceability_fields() -> None:
    plan = build_execution_plan([intent("MSFT")])

    for field_name in _FORBIDDEN_PLAN_FIELD_NAMES:
        assert not hasattr(plan, field_name)


def test_no_client_order_id_or_idempotency_fields_exist() -> None:
    plan = build_execution_plan([intent("MSFT")])

    assert not hasattr(plan, "client_order_id")
    assert not hasattr(plan, "client_order_ids")
    assert not hasattr(plan, "idempotency_key")
    assert not hasattr(plan, "idempotency_keys")


def test_no_broker_order_fill_or_submission_fields_exist() -> None:
    plan = build_execution_plan([intent("MSFT")])

    assert not hasattr(plan, "broker_order_id")
    assert not hasattr(plan, "broker_order_ids")
    assert not hasattr(plan, "fill")
    assert not hasattr(plan, "filled_at")
    assert not hasattr(plan, "fill_price")
    assert not hasattr(plan, "fill_quantity")
    assert not hasattr(plan, "submitted_at")
    assert not hasattr(plan, "submission")


def test_no_broker_account_or_venue_fields_exist() -> None:
    plan = build_execution_plan([intent("MSFT")])

    assert not hasattr(plan, "account_id")
    assert not hasattr(plan, "broker")
    assert not hasattr(plan, "broker_name")
    assert not hasattr(plan, "venue")


def test_no_direct_order_risk_or_status_convenience_fields_exist() -> None:
    plan = build_execution_plan([intent("MSFT")])

    assert not hasattr(plan, "order")
    assert not hasattr(plan, "orders")
    assert not hasattr(plan, "risk")
    assert not hasattr(plan, "risks")
    assert not hasattr(plan, "status")
    assert not hasattr(plan, "statuses")


def test_proposed_order_remains_reachable_only_through_intent_source() -> None:
    original = intent("MSFT")

    plan = build_execution_plan([original])

    assert plan.intents[0].source_evaluation is original.source_evaluation
    assert plan.intents[0].source_evaluation.order is (
        original.source_evaluation.order
    )
    assert not hasattr(plan, "order")
    assert not hasattr(plan.intents[0], "order")


def test_risk_verdict_remains_reachable_only_through_intent_source() -> None:
    original = intent("MSFT")

    plan = build_execution_plan([original])

    assert plan.intents[0].source_evaluation is original.source_evaluation
    assert plan.intents[0].source_evaluation.risk is (
        original.source_evaluation.risk
    )
    assert not hasattr(plan, "risk")
    assert not hasattr(plan.intents[0], "risk")


def test_status_remains_reachable_only_through_intent_source() -> None:
    original = intent("MSFT")

    plan = build_execution_plan([original])

    assert plan.intents[0] is original
    assert plan.intents[0].source_evaluation is original.source_evaluation
    assert plan.intents[0].source_evaluation.status == "risk_approved"
    assert not hasattr(plan, "status")
    assert not hasattr(plan.intents[0], "status")


def test_multiple_intent_traceability_flows_through_sources_by_identity() -> None:
    first_source = risk_approved("MSFT")
    second_source = risk_approved("AAPL")
    first = ExecutionIntent(source_evaluation=first_source)
    second = ExecutionIntent(source_evaluation=second_source)

    plan = build_execution_plan([first, second])

    assert plan.intents[0] is first
    assert plan.intents[1] is second
    assert plan.intents[0].source_evaluation is first_source
    assert plan.intents[1].source_evaluation is second_source
    assert plan.intents[0].source_evaluation.order is first_source.order
    assert plan.intents[1].source_evaluation.order is second_source.order
    assert plan.intents[0].source_evaluation.risk is first_source.risk
    assert plan.intents[1].source_evaluation.risk is second_source.risk
    assert plan.intents[0].source_evaluation.status == first_source.status
    assert plan.intents[1].source_evaluation.status == second_source.status


def test_mutating_input_list_after_plan_creation_does_not_mutate_plan() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    intents = [first]

    plan = build_execution_plan(intents)
    intents.append(second)

    assert plan.intents == (first,)
    assert plan.intents[0] is first
    assert second not in plan.intents


def test_builder_does_not_copy_or_mutate_intents_or_source_evaluations() -> None:
    source = risk_approved("MSFT")
    original = ExecutionIntent(source_evaluation=source)

    plan = build_execution_plan([original])

    assert plan.intents[0] is original
    assert plan.intents[0].source_evaluation is source
    assert plan.intents[0].source_evaluation.order is source.order
    assert plan.intents[0].source_evaluation.risk is source.risk
    assert plan.intents[0].source_evaluation.status == source.status


def test_duplicate_intents_are_preserved_without_deduplication_policy() -> None:
    original = intent("MSFT")

    plan = build_execution_plan([original, original])

    assert plan.intents == (original, original)
    assert plan.intents[0] is original
    assert plan.intents[1] is original


def test_builder_applies_no_priority_or_ranking_policy() -> None:
    lower_alpha_symbol = intent("ZZZZ")
    higher_alpha_symbol = intent("AAAA")

    plan = build_execution_plan([lower_alpha_symbol, higher_alpha_symbol])

    assert plan.intents == (lower_alpha_symbol, higher_alpha_symbol)
    assert not hasattr(plan, "priority")
    assert not hasattr(plan, "priorities")
    assert not hasattr(plan, "rank")
    assert not hasattr(plan, "ranks")


def test_builder_signature_requires_only_intents_iterable() -> None:
    parameters = tuple(inspect.signature(build_execution_plan).parameters)

    assert parameters == ("intents",)


def test_builder_requires_no_runtime_or_policy_objects() -> None:
    parameter_names = tuple(inspect.signature(build_execution_plan).parameters)
    referenced_names = _referenced_names()

    assert parameter_names == ("intents",)
    assert referenced_names.isdisjoint(
        {
            "Broker",
            "BrokerOrderResult",
            "Execution",
            "LocalBroker",
            "PortfolioState",
            "RiskEngine",
            "Scheduler",
            "persistence",
            "runtime",
        }
    )


def test_execution_planning_module_references_no_runtime_dependencies() -> None:
    names = _referenced_names()

    assert names.isdisjoint(
        {
            "AlpacaPaperBroker",
            "Broker",
            "BrokerOrderResult",
            "LocalBroker",
            "PortfolioState",
            "RiskEngine",
            "client_order_id",
            "create_client_order_id",
            "idempotency",
            "idempotency_key",
            "scheduler",
            "runtime",
            "persistence",
            "submit_order",
        }
    )


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names
