import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import ValidationError
from algotrader.orchestration.execution_planning_flow import (
    ExecutionPlan,
    build_execution_plan,
)
from algotrader.orchestration.execution_planning_policy import (
    MAX_INTENTS_PER_PLAN_EXCEEDED_REASON,
    MaxAcceptedIntentsPolicyConfig,
    PlanningPolicyResult,
    SkippedExecutionIntent,
    apply_max_intents_execution_planning_policy,
    apply_noop_execution_planning_policy,
)
from algotrader.orchestration.risk_execution_flow import ExecutionIntent
from algotrader.orchestration.signal_risk_flow import SignalRiskEvaluation
from algotrader.risk.state import RiskVerdict


NOW = datetime(2026, 5, 7, tzinfo=timezone.utc)

_FORBIDDEN_POLICY_RESULT_FIELD_NAMES = {
    "accepted_orders",
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
    "intents",
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
    "skipped_orders",
    "status",
    "statuses",
    "submitted_at",
    "symbol",
    "symbols",
    "venue",
}

_FORBIDDEN_SKIPPED_INTENT_FIELD_NAMES = {
    "account_id",
    "alpaca_order",
    "broker",
    "broker_name",
    "broker_order_id",
    "client_order_id",
    "cash_reserved",
    "fill",
    "fill_price",
    "fill_quantity",
    "filled_at",
    "idempotency_key",
    "native_order",
    "order",
    "persisted_at",
    "priority",
    "quantity",
    "rank",
    "risk",
    "sdk_order",
    "side",
    "status",
    "submitted_at",
    "symbol",
    "venue",
}

_FORBIDDEN_MAX_INTENTS_CONFIG_FIELD_NAMES = {
    "account_id",
    "broker",
    "cash_reserved",
    "client_order_id",
    "fill",
    "filled_at",
    "idempotency_key",
    "persisted_at",
    "priority",
    "rank",
    "submitted_at",
    "venue",
}

_FORBIDDEN_MAX_POLICY_PARAMETER_NAMES = {
    "account",
    "broker",
    "database",
    "execution",
    "persistence",
    "portfolio",
    "risk_engine",
    "runtime",
    "scheduler",
}

_FORBIDDEN_NOOP_POLICY_PARAMETER_NAMES = {
    "account",
    "broker",
    "database",
    "execution",
    "persistence",
    "policy_config",
    "portfolio",
    "risk_engine",
    "runtime",
    "scheduler",
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


def max_config(limit: int) -> MaxAcceptedIntentsPolicyConfig:
    return MaxAcceptedIntentsPolicyConfig(max_accepted_intents=limit)


def test_max_intents_config_accepts_positive_int() -> None:
    config = max_config(3)

    assert config.max_accepted_intents == 3


def test_max_intents_config_accepts_one() -> None:
    config = max_config(1)

    assert config.max_accepted_intents == 1


@pytest.mark.parametrize("invalid_limit", [0, -1, -100])
def test_max_intents_config_rejects_non_positive_ints(invalid_limit: int) -> None:
    with pytest.raises(ValidationError, match="max_accepted_intents"):
        MaxAcceptedIntentsPolicyConfig(max_accepted_intents=invalid_limit)


@pytest.mark.parametrize(
    "invalid_limit",
    [True, False, None, 1.5, "3", Decimal("3")],
)
def test_max_intents_config_rejects_unsupported_types(
    invalid_limit: object,
) -> None:
    with pytest.raises(ValidationError, match="max_accepted_intents"):
        MaxAcceptedIntentsPolicyConfig(max_accepted_intents=invalid_limit)


def test_max_intents_config_is_frozen() -> None:
    config = max_config(3)

    with pytest.raises(FrozenInstanceError):
        config.max_accepted_intents = 4


def test_max_intents_config_has_only_limit_field() -> None:
    field_names = tuple(field.name for field in fields(MaxAcceptedIntentsPolicyConfig))

    assert field_names == ("max_accepted_intents",)
    assert set(field_names).isdisjoint(_FORBIDDEN_MAX_INTENTS_CONFIG_FIELD_NAMES)


def test_max_intents_config_exposes_no_forbidden_fields() -> None:
    config = max_config(3)

    for field_name in _FORBIDDEN_MAX_INTENTS_CONFIG_FIELD_NAMES:
        assert not hasattr(config, field_name)


def test_max_intents_reason_constant_is_deterministic() -> None:
    assert (
        MAX_INTENTS_PER_PLAN_EXCEEDED_REASON
        == "max_intents_per_plan_exceeded"
    )


def test_max_intents_policy_empty_plan_returns_empty_result() -> None:
    result = apply_max_intents_execution_planning_policy(
        ExecutionPlan(intents=()),
        max_config(3),
    )

    assert result == PlanningPolicyResult(
        accepted_intents=(),
        skipped_intents=(),
    )
    assert result.accepted_intents == ()
    assert result.skipped_intents == ()


def test_max_intents_policy_accepts_all_when_plan_length_below_cap() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    plan = build_execution_plan((first, second))

    result = apply_max_intents_execution_planning_policy(plan, max_config(3))

    assert result.accepted_intents == (first, second)
    assert result.skipped_intents == ()


def test_max_intents_policy_accepts_all_when_plan_length_equals_cap() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    plan = build_execution_plan((first, second))

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert result.accepted_intents == (first, second)
    assert result.skipped_intents == ()


def test_max_intents_policy_accepts_first_n_and_skips_remaining() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    third = intent("NVDA")
    fourth = intent("TSLA")
    plan = build_execution_plan((first, second, third, fourth))

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert result.accepted_intents == (first, second)
    assert tuple(skipped.intent for skipped in result.skipped_intents) == (
        third,
        fourth,
    )


def test_max_intents_policy_skipped_reasons_use_constant() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    third = intent("NVDA")
    plan = build_execution_plan((first, second, third))

    result = apply_max_intents_execution_planning_policy(plan, max_config(1))

    assert tuple(skipped.reason for skipped in result.skipped_intents) == (
        MAX_INTENTS_PER_PLAN_EXCEEDED_REASON,
        MAX_INTENTS_PER_PLAN_EXCEEDED_REASON,
    )
    assert result.skipped_intents[0].reason == "max_intents_per_plan_exceeded"


def test_max_intents_policy_preserves_accepted_and_skipped_order() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    third = intent("NVDA")
    fourth = intent("TSLA")
    plan = build_execution_plan((first, second, third, fourth))

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert result.accepted_intents == (first, second)
    assert tuple(skipped.intent for skipped in result.skipped_intents) == (
        third,
        fourth,
    )


def test_max_intents_policy_preserves_execution_intent_identity() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    third = intent("NVDA")
    plan = build_execution_plan((first, second, third))

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert result.accepted_intents[0] is first
    assert result.accepted_intents[1] is second
    assert result.skipped_intents[0].intent is third


def test_max_intents_policy_preserves_source_identity_through_accepted_path() -> None:
    first_source = risk_approved("MSFT")
    second_source = risk_approved("AAPL")
    first = ExecutionIntent(source_evaluation=first_source)
    second = ExecutionIntent(source_evaluation=second_source)
    plan = build_execution_plan((first, second))

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert result.accepted_intents[0].source_evaluation is first_source
    assert result.accepted_intents[1].source_evaluation is second_source


def test_max_intents_policy_preserves_source_identity_through_skipped_path() -> None:
    first_source = risk_approved("MSFT")
    second_source = risk_approved("AAPL")
    first = ExecutionIntent(source_evaluation=first_source)
    second = ExecutionIntent(source_evaluation=second_source)
    plan = build_execution_plan((first, second))

    result = apply_max_intents_execution_planning_policy(plan, max_config(1))

    assert result.accepted_intents[0].source_evaluation is first_source
    assert result.skipped_intents[0].intent is second
    assert result.skipped_intents[0].intent.source_evaluation is second_source


def test_max_intents_policy_keeps_order_risk_and_status_source_only() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    plan = build_execution_plan((first, second))

    result = apply_max_intents_execution_planning_policy(plan, max_config(1))
    accepted = result.accepted_intents[0]
    skipped = result.skipped_intents[0]

    assert accepted.source_evaluation.order is first.source_evaluation.order
    assert accepted.source_evaluation.risk is first.source_evaluation.risk
    assert accepted.source_evaluation.status == first.source_evaluation.status
    assert skipped.intent.source_evaluation.order is second.source_evaluation.order
    assert skipped.intent.source_evaluation.risk is second.source_evaluation.risk
    assert skipped.intent.source_evaluation.status == second.source_evaluation.status
    assert not hasattr(result, "order")
    assert not hasattr(result, "risk")
    assert not hasattr(result, "status")
    assert not hasattr(accepted, "order")
    assert not hasattr(accepted, "risk")
    assert not hasattr(accepted, "status")
    assert not hasattr(skipped, "order")
    assert not hasattr(skipped, "risk")
    assert not hasattr(skipped, "status")


def test_max_intents_policy_does_not_mutate_input_plan() -> None:
    first = intent("MSFT")
    second = intent("AAPL")
    third = intent("NVDA")
    plan = build_execution_plan((first, second, third))
    original_intents = plan.intents

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert plan.intents is original_intents
    assert plan.intents == (first, second, third)
    assert result.accepted_intents == (first, second)
    assert tuple(skipped.intent for skipped in result.skipped_intents) == (third,)


def test_max_intents_policy_does_not_mutate_intents_or_sources() -> None:
    first_source = risk_approved("MSFT")
    second_source = risk_approved("AAPL")
    first = ExecutionIntent(source_evaluation=first_source)
    second = ExecutionIntent(source_evaluation=second_source)
    plan = build_execution_plan((first, second))

    result = apply_max_intents_execution_planning_policy(plan, max_config(1))

    assert first.source_evaluation is first_source
    assert second.source_evaluation is second_source
    assert result.accepted_intents[0] is first
    assert result.skipped_intents[0].intent is second


def test_max_intents_policy_caps_same_symbol_intents_by_order_only() -> None:
    first = intent("MSFT", quantity="1")
    second = intent("MSFT", quantity="2")
    third = intent("MSFT", quantity="3")
    plan = build_execution_plan((first, second, third))

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert result.accepted_intents == (first, second)
    assert result.skipped_intents[0].intent is third
    assert result.skipped_intents[0].reason == MAX_INTENTS_PER_PLAN_EXCEEDED_REASON


def test_max_intents_policy_preserves_duplicate_intents_by_position() -> None:
    original = intent("MSFT")
    plan = build_execution_plan((original, original, original))

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert result.accepted_intents == (original, original)
    assert result.accepted_intents[0] is original
    assert result.accepted_intents[1] is original
    assert result.skipped_intents[0].intent is original


def test_max_intents_policy_applies_no_cash_or_buying_power_reservation() -> None:
    first = intent("MSFT", order_notional="80")
    second = intent("AAPL", order_notional="80")
    plan = build_execution_plan((first, second))

    result = apply_max_intents_execution_planning_policy(plan, max_config(1))

    assert result.accepted_intents == (first,)
    assert result.skipped_intents[0].intent is second
    assert not hasattr(result, "cash_reserved")
    assert not hasattr(result, "buying_power_reserved")
    assert not hasattr(max_config(1), "cash_reserved")
    assert not hasattr(max_config(1), "buying_power_reserved")


def test_max_intents_policy_applies_no_priority_or_ranking() -> None:
    first = intent("ZZZZ")
    second = intent("AAAA")
    third = intent("MMMM")
    plan = build_execution_plan((first, second, third))

    result = apply_max_intents_execution_planning_policy(plan, max_config(2))

    assert result.accepted_intents == (first, second)
    assert result.skipped_intents[0].intent is third
    assert not hasattr(result, "priority")
    assert not hasattr(result, "priorities")
    assert not hasattr(result, "rank")
    assert not hasattr(result, "ranks")


def test_max_intents_policy_applies_no_client_order_id_or_idempotency() -> None:
    result = apply_max_intents_execution_planning_policy(
        build_execution_plan((intent("MSFT"), intent("AAPL"))),
        max_config(1),
    )

    assert not hasattr(result, "client_order_id")
    assert not hasattr(result, "client_order_ids")
    assert not hasattr(result, "idempotency_key")
    assert not hasattr(result, "idempotency_keys")
    assert not hasattr(result.accepted_intents[0], "client_order_id")
    assert not hasattr(result.accepted_intents[0], "idempotency_key")
    assert not hasattr(result.skipped_intents[0], "client_order_id")
    assert not hasattr(result.skipped_intents[0], "idempotency_key")


def test_max_intents_policy_exposes_no_broker_account_venue_submission_or_fill_fields() -> None:
    result = apply_max_intents_execution_planning_policy(
        build_execution_plan((intent("MSFT"), intent("AAPL"))),
        max_config(1),
    )

    for field_name in (
        "account_id",
        "broker",
        "broker_name",
        "venue",
        "submitted_at",
        "fill",
        "filled_at",
        "fill_price",
        "fill_quantity",
    ):
        assert not hasattr(result, field_name)
        assert not hasattr(result.accepted_intents[0], field_name)
        assert not hasattr(result.skipped_intents[0], field_name)


def test_max_intents_policy_signature_requires_plan_and_config_only() -> None:
    signature = inspect.signature(apply_max_intents_execution_planning_policy)

    assert tuple(signature.parameters) == ("plan", "config")
    assert signature.parameters["plan"].annotation in {
        ExecutionPlan,
        "ExecutionPlan",
    }
    assert signature.parameters["config"].annotation in {
        MaxAcceptedIntentsPolicyConfig,
        "MaxAcceptedIntentsPolicyConfig",
    }
    assert set(signature.parameters).isdisjoint(
        _FORBIDDEN_MAX_POLICY_PARAMETER_NAMES
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


def test_planning_policy_result_skipped_intents_field_is_frozen() -> None:
    result = apply_noop_execution_planning_policy(
        build_execution_plan([intent("MSFT")])
    )

    with pytest.raises(FrozenInstanceError):
        result.skipped_intents = ()


def test_skipped_execution_intent_is_frozen() -> None:
    skipped = SkippedExecutionIntent(
        intent=intent("MSFT"),
        reason="future_policy_reason",
    )

    with pytest.raises(FrozenInstanceError):
        skipped.reason = "changed"


def test_skipped_execution_intent_intent_field_is_frozen() -> None:
    skipped = SkippedExecutionIntent(
        intent=intent("MSFT"),
        reason="future_policy_reason",
    )

    with pytest.raises(FrozenInstanceError):
        skipped.intent = intent("AAPL")


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


def test_planning_policy_result_exposes_no_forbidden_traceability_fields() -> None:
    result = PlanningPolicyResult(
        accepted_intents=(intent("MSFT"),),
        skipped_intents=(),
    )

    for field_name in _FORBIDDEN_POLICY_RESULT_FIELD_NAMES:
        assert not hasattr(result, field_name)


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
    assert set(signature.parameters).isdisjoint(
        _FORBIDDEN_NOOP_POLICY_PARAMETER_NAMES
    )


def test_skipped_execution_intent_stores_intent_identity_and_reason() -> None:
    original = intent("MSFT")

    skipped = SkippedExecutionIntent(
        intent=original,
        reason="future_policy_reason",
    )

    assert skipped.intent is original
    assert skipped.reason == "future_policy_reason"


def test_skipped_intent_traceability_flows_through_source_evaluation() -> None:
    source = risk_approved("MSFT")
    original = ExecutionIntent(source_evaluation=source)
    skipped = SkippedExecutionIntent(
        intent=original,
        reason="future_policy_reason",
    )
    result = PlanningPolicyResult(
        accepted_intents=(),
        skipped_intents=(skipped,),
    )

    assert result.skipped_intents[0] is skipped
    assert result.skipped_intents[0].intent is original
    assert result.skipped_intents[0].intent.source_evaluation is source
    assert result.skipped_intents[0].reason == "future_policy_reason"
    assert result.skipped_intents[0].intent.source_evaluation.order is source.order
    assert result.skipped_intents[0].intent.source_evaluation.risk is source.risk
    assert result.skipped_intents[0].intent.source_evaluation.status == source.status
    assert not hasattr(skipped, "order")
    assert not hasattr(skipped, "risk")
    assert not hasattr(skipped, "status")
    assert not hasattr(result, "skipped_orders")


def test_accepted_intent_traceability_preserves_sources_order_risk_and_status() -> None:
    first_source = risk_approved("MSFT")
    second_source = risk_approved("AAPL")
    first = ExecutionIntent(source_evaluation=first_source)
    second = ExecutionIntent(source_evaluation=second_source)
    result = apply_noop_execution_planning_policy(
        build_execution_plan([first, second])
    )

    assert result.accepted_intents[0] is first
    assert result.accepted_intents[1] is second
    assert result.accepted_intents[0].source_evaluation is first_source
    assert result.accepted_intents[1].source_evaluation is second_source
    assert result.accepted_intents[0].source_evaluation.order is first_source.order
    assert result.accepted_intents[1].source_evaluation.order is second_source.order
    assert result.accepted_intents[0].source_evaluation.risk is first_source.risk
    assert result.accepted_intents[1].source_evaluation.risk is second_source.risk
    assert result.accepted_intents[0].source_evaluation.status == first_source.status
    assert result.accepted_intents[1].source_evaluation.status == second_source.status
    assert not hasattr(result, "accepted_orders")
    assert not hasattr(result, "orders")
    assert not hasattr(result, "risks")
    assert not hasattr(result, "symbols")
    assert not hasattr(result, "statuses")


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
