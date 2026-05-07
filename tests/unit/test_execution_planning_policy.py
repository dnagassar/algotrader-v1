import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.orchestration.execution_planning_flow import (
    ExecutionPlan,
    build_execution_plan,
)
from algotrader.orchestration.execution_planning_policy import (
    PlanningPolicyResult,
    SkippedExecutionIntent,
    apply_noop_execution_planning_policy,
)
from algotrader.orchestration.risk_execution_flow import ExecutionIntent
from algotrader.orchestration.signal_risk_flow import SignalRiskEvaluation
from algotrader.risk.state import RiskVerdict


NOW = datetime(2026, 5, 7, tzinfo=timezone.utc)

_FORBIDDEN_POLICY_RESULT_FIELD_NAMES = {
    "account_id",
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
    "rank",
    "ranks",
    "rejected_intents",
    "risk",
    "risks",
    "selected_intents",
    "status",
    "statuses",
    "submitted_at",
    "symbol",
    "symbols",
    "venue",
}

_FORBIDDEN_SKIPPED_INTENT_FIELD_NAMES = {
    "account_id",
    "broker",
    "broker_order_id",
    "client_order_id",
    "fill",
    "filled_at",
    "idempotency_key",
    "persisted_at",
    "submitted_at",
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


def test_empty_plan_returns_empty_policy_result() -> None:
    result = apply_noop_execution_planning_policy(ExecutionPlan(intents=()))

    assert result == PlanningPolicyResult(
        accepted_intents=(),
        skipped_intents=(),
    )
    assert result.accepted_intents == ()
    assert result.skipped_intents == ()


def test_one_intent_is_accepted() -> None:
    original = intent("MSFT")
    plan = build_execution_plan((original,))

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents == (original,)
    assert result.skipped_intents == ()


def test_multiple_intents_preserve_accepted_order() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    third = intent("NVDA")
    plan = build_execution_plan((first, second, third))

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents == (first, second, third)


def test_accepted_execution_intent_object_identity_is_preserved() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    plan = build_execution_plan([first, second])

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents[0] is first
    assert result.accepted_intents[1] is second


def test_source_evaluation_identity_is_preserved_through_accepted_intents() -> None:
    first_source = risk_approved("MSFT")
    second_source = risk_approved("AAPL")
    first = ExecutionIntent(source_evaluation=first_source)
    second = ExecutionIntent(source_evaluation=second_source)
    plan = build_execution_plan((first, second))

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents[0].source_evaluation is first_source
    assert result.accepted_intents[1].source_evaluation is second_source


def test_proposed_order_remains_reachable_only_through_accepted_intent_source() -> None:
    original = intent("MSFT")
    plan = build_execution_plan([original])

    result = apply_noop_execution_planning_policy(plan)

    accepted = result.accepted_intents[0]
    assert accepted.source_evaluation.order is original.source_evaluation.order
    assert not hasattr(result, "order")
    assert not hasattr(result, "orders")
    assert not hasattr(accepted, "order")


def test_risk_verdict_remains_reachable_only_through_accepted_intent_source() -> None:
    original = intent("MSFT")
    plan = build_execution_plan([original])

    result = apply_noop_execution_planning_policy(plan)

    accepted = result.accepted_intents[0]
    assert accepted.source_evaluation.risk is original.source_evaluation.risk
    assert not hasattr(result, "risk")
    assert not hasattr(result, "risks")
    assert not hasattr(accepted, "risk")


def test_status_remains_reachable_only_through_accepted_intent_source() -> None:
    original = intent("MSFT")
    plan = build_execution_plan([original])

    result = apply_noop_execution_planning_policy(plan)

    accepted = result.accepted_intents[0]
    assert accepted.source_evaluation.status == "risk_approved"
    assert not hasattr(result, "status")
    assert not hasattr(result, "statuses")
    assert not hasattr(accepted, "status")


def test_result_fields_are_tuples() -> None:
    result = apply_noop_execution_planning_policy(
        build_execution_plan([intent("MSFT")])
    )

    assert isinstance(result.accepted_intents, tuple)
    assert isinstance(result.skipped_intents, tuple)


def test_planning_policy_result_is_frozen() -> None:
    result = apply_noop_execution_planning_policy(
        build_execution_plan([intent("MSFT")])
    )

    with pytest.raises(FrozenInstanceError):
        result.accepted_intents = ()


def test_skipped_execution_intent_is_frozen() -> None:
    skipped = SkippedExecutionIntent(
        intent=intent("MSFT"),
        reason="future_policy_reason",
    )

    with pytest.raises(FrozenInstanceError):
        skipped.reason = "changed"


def test_input_execution_plan_is_not_mutated() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    plan = build_execution_plan([first, second])
    original_intents = plan.intents

    result = apply_noop_execution_planning_policy(plan)

    assert plan.intents is original_intents
    assert plan.intents == (first, second)
    assert result.accepted_intents == original_intents


def test_intents_and_source_evaluations_are_not_mutated() -> None:
    source = risk_approved("MSFT")
    original = ExecutionIntent(source_evaluation=source)
    plan = build_execution_plan([original])

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents[0] is original
    assert original.source_evaluation is source
    assert original.source_evaluation.order is source.order
    assert original.source_evaluation.risk is source.risk
    assert original.source_evaluation.status == source.status


def test_same_symbol_intents_are_accepted_without_conflict_policy() -> None:
    first = intent("MSFT", quantity="1")
    second = intent("MSFT", quantity="2")
    plan = build_execution_plan((first, second))

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents == (first, second)
    assert result.accepted_intents[0] is first
    assert result.accepted_intents[1] is second
    assert result.skipped_intents == ()


def test_duplicate_intent_objects_are_accepted_without_dedup_policy() -> None:
    original = intent("MSFT")
    plan = build_execution_plan((original, original))

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents == (original, original)
    assert result.accepted_intents[0] is original
    assert result.accepted_intents[1] is original


def test_no_batch_cash_or_buying_power_reservation_is_applied() -> None:
    first = intent("MSFT", order_notional="80")
    second = intent("AAPL", order_notional="80")
    plan = build_execution_plan((first, second))

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents == (first, second)
    assert not hasattr(result, "cash_reserved")
    assert not hasattr(result, "buying_power_reserved")


def test_no_priority_or_ranking_policy_is_applied() -> None:
    first = intent("ZZZZ")
    second = intent("AAAA")
    plan = build_execution_plan((first, second))

    result = apply_noop_execution_planning_policy(plan)

    assert result.accepted_intents == (first, second)
    assert not hasattr(result, "priority")
    assert not hasattr(result, "priorities")
    assert not hasattr(result, "rank")
    assert not hasattr(result, "ranks")


def test_planning_policy_result_has_only_accepted_and_skipped_fields() -> None:
    field_names = tuple(field.name for field in fields(PlanningPolicyResult))

    assert field_names == ("accepted_intents", "skipped_intents")
    assert set(field_names).isdisjoint(_FORBIDDEN_POLICY_RESULT_FIELD_NAMES)


def test_no_client_order_id_or_idempotency_fields_exist() -> None:
    result = apply_noop_execution_planning_policy(
        build_execution_plan([intent("MSFT")])
    )

    assert not hasattr(result, "client_order_id")
    assert not hasattr(result, "client_order_ids")
    assert not hasattr(result, "idempotency_key")
    assert not hasattr(result, "idempotency_keys")


def test_no_broker_order_fill_or_submission_fields_exist() -> None:
    result = apply_noop_execution_planning_policy(
        build_execution_plan([intent("MSFT")])
    )

    assert not hasattr(result, "broker_order_id")
    assert not hasattr(result, "broker_order_ids")
    assert not hasattr(result, "fill")
    assert not hasattr(result, "filled_at")
    assert not hasattr(result, "fill_price")
    assert not hasattr(result, "fill_quantity")
    assert not hasattr(result, "submitted_at")


def test_no_broker_account_or_venue_fields_exist() -> None:
    result = apply_noop_execution_planning_policy(
        build_execution_plan([intent("MSFT")])
    )

    assert not hasattr(result, "account_id")
    assert not hasattr(result, "broker")
    assert not hasattr(result, "broker_name")
    assert not hasattr(result, "venue")


def test_no_direct_order_risk_or_status_convenience_fields_exist() -> None:
    result = apply_noop_execution_planning_policy(
        build_execution_plan([intent("MSFT")])
    )

    assert not hasattr(result, "order")
    assert not hasattr(result, "orders")
    assert not hasattr(result, "risk")
    assert not hasattr(result, "risks")
    assert not hasattr(result, "status")
    assert not hasattr(result, "statuses")


def test_function_signature_requires_only_execution_plan() -> None:
    signature = inspect.signature(apply_noop_execution_planning_policy)

    assert tuple(signature.parameters) == ("plan",)
    assert signature.parameters["plan"].annotation in {
        ExecutionPlan,
        "ExecutionPlan",
    }


def test_skipped_execution_intent_stores_intent_identity_and_reason() -> None:
    original = intent("MSFT")

    skipped = SkippedExecutionIntent(
        intent=original,
        reason="future_policy_reason",
    )

    assert skipped.intent is original
    assert skipped.reason == "future_policy_reason"


def test_skipped_execution_intent_has_only_intent_and_reason_fields() -> None:
    skipped = SkippedExecutionIntent(
        intent=intent("MSFT"),
        reason="future_policy_reason",
    )
    field_names = tuple(field.name for field in fields(SkippedExecutionIntent))

    assert field_names == ("intent", "reason")
    assert set(field_names).isdisjoint(_FORBIDDEN_SKIPPED_INTENT_FIELD_NAMES)
    for field_name in _FORBIDDEN_SKIPPED_INTENT_FIELD_NAMES:
        assert not hasattr(skipped, field_name)
