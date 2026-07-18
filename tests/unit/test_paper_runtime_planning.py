from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from algotrader.core.types import Bar, OrderSide
from algotrader.execution.paper_runtime_planning import (
    PaperRuntimePlanningInput,
    build_canonical_paper_runtime_plan,
)
from algotrader.portfolio.state import Position


NOW = datetime(2026, 7, 10, tzinfo=UTC)


def _bar(close: str = "100") -> Bar:
    return Bar("SPY", NOW, close, close, close, close, "1000")


def _planning_input(
    action: str,
    *,
    cash: str | None = "1000",
    positions: tuple[Position, ...] = (),
    quantity: str | None = None,
    trading_enabled: bool = True,
) -> PaperRuntimePlanningInput:
    return PaperRuntimePlanningInput(
        symbol="SPY",
        action=action,
        reason="test_runtime_decision",
        latest_bar=_bar(),
        account_cash=cash,
        positions=positions,
        trading_enabled=trading_enabled,
        trading_disabled_reason="operator_pause" if not trading_enabled else "",
        max_notional="25",
        client_order_id="canonical-spy-order-1",
        quantity=quantity,
    )


def test_buy_flows_through_risk_intent_plan_and_policy() -> None:
    result = build_canonical_paper_runtime_plan(_planning_input("buy"))

    assert result.decision_status == "accepted"
    assert result.risk_allowed is True
    assert result.policy_accepted is True
    assert result.proposed_order is not None
    assert result.proposed_order.side == OrderSide.BUY
    assert result.proposed_order.quantity == Decimal("0.25")
    assert result.accepted_order is result.proposed_order
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.risk is not None
    assert result.risk_evaluation.risk.order_notional == Decimal("25.00")
    assert result.execution_plan.intents[0].source_evaluation is result.risk_evaluation
    assert result.planning_policy.accepted_intents[0] is result.execution_plan.intents[0]
    assert result.to_dict()["pipeline"] == [
        "risk",
        "execution_intent",
        "execution_plan",
        "planning_policy",
    ]


def test_sell_close_uses_observed_position_quantity() -> None:
    position = Position("SPY", "0.25", "100")

    result = build_canonical_paper_runtime_plan(
        _planning_input("sell_close", positions=(position,), quantity="0.25")
    )

    assert result.policy_accepted is True
    assert result.accepted_order is not None
    assert result.accepted_order.side == OrderSide.SELL
    assert result.accepted_order.quantity == Decimal("0.25")


def test_hold_produces_an_empty_canonical_plan() -> None:
    result = build_canonical_paper_runtime_plan(_planning_input("hold"))

    assert result.decision_status == "no_action_required"
    assert result.execution_plan.intents == ()
    assert result.planning_policy.accepted_intents == ()
    assert result.blockers == ()


def test_trading_disabled_is_rejected_by_authoritative_risk_engine() -> None:
    result = build_canonical_paper_runtime_plan(
        _planning_input("buy", trading_enabled=False)
    )

    assert result.decision_status == "risk_rejected"
    assert result.risk_allowed is False
    assert result.policy_accepted is False
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.risk is not None
    assert result.risk_evaluation.risk.reason == "trading_disabled"
    assert result.risk_evaluation.risk.detail == "operator_pause"
    assert result.blockers == ("canonical_risk_rejected_trading_disabled",)


def test_insufficient_cash_cannot_reach_execution_policy() -> None:
    result = build_canonical_paper_runtime_plan(
        _planning_input("buy", cash="10")
    )

    assert result.decision_status == "risk_rejected"
    assert result.risk_allowed is False
    assert result.policy_accepted is False
    assert result.execution_plan.intents == ()
    assert result.planning_policy.accepted_intents == ()
    assert result.blockers == ("canonical_risk_rejected_insufficient_cash",)
