"""Canonical pre-broker planning for the bounded SPY paper runtime.

The paper supervisor historically carried its own intent and plan shapes. This
module makes the deterministic risk -> ExecutionIntent -> ExecutionPlan ->
PlanningPolicy chain authoritative before the broker-specific envelope can
authorize a mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.core.validation import decimal_value, symbol_value
from algotrader.errors import ValidationError
from algotrader.orchestration.execution_planning_flow import (
    ExecutionPlan,
    build_execution_plan,
)
from algotrader.orchestration.execution_planning_policy import (
    MaxAcceptedIntentsPolicyConfig,
    PlanningPolicyResult,
    apply_max_intents_execution_planning_policy,
)
from algotrader.orchestration.risk_execution_flow import (
    build_execution_intents_from_risk_approved,
)
from algotrader.orchestration.signal_risk_flow import SignalRiskEvaluation
from algotrader.portfolio.state import Account, PortfolioState, Position, RiskState
from algotrader.risk.config import RiskConfig
from algotrader.risk.context import RiskContext
from algotrader.risk.engine import RiskEngine

__all__ = [
    "CanonicalPaperRuntimePlan",
    "PaperRuntimePlanningInput",
    "build_canonical_paper_runtime_plan",
]

_SUPPORTED_ACTIONS = frozenset({"blocked", "buy", "hold", "sell_close"})


@dataclass(frozen=True, slots=True)
class PaperRuntimePlanningInput:
    """Typed inputs required to construct the canonical pre-broker plan."""

    symbol: str
    action: str
    reason: str
    latest_bar: Bar | None
    account_cash: Decimal | str | None
    positions: tuple[Position, ...]
    trading_enabled: bool
    trading_disabled_reason: str
    max_notional: Decimal | str
    client_order_id: str
    quantity: Decimal | str | None = None
    currency: str = "USD"
    risk_context: RiskContext | None = None


@dataclass(frozen=True, slots=True)
class CanonicalPaperRuntimePlan:
    """Immutable result of the canonical deterministic planning chain."""

    requested_action: str
    decision_status: str
    proposed_order: ProposedOrder | None
    portfolio: PortfolioState | None
    quote: Quote | None
    risk_evaluation: SignalRiskEvaluation | None
    execution_plan: ExecutionPlan
    planning_policy: PlanningPolicyResult
    blockers: tuple[str, ...]

    @property
    def risk_allowed(self) -> bool:
        evaluation = self.risk_evaluation
        return bool(
            evaluation is not None
            and evaluation.status == "risk_approved"
            and evaluation.risk is not None
            and evaluation.risk.allowed
        )

    @property
    def policy_accepted(self) -> bool:
        return bool(
            self.risk_allowed
            and len(self.execution_plan.intents) == 1
            and len(self.planning_policy.accepted_intents) == 1
            and not self.planning_policy.skipped_intents
            and self.planning_policy.accepted_intents[0]
            is self.execution_plan.intents[0]
        )

    @property
    def accepted_order(self) -> ProposedOrder | None:
        if not self.policy_accepted:
            return None
        return self.planning_policy.accepted_intents[0].source_evaluation.order

    def to_dict(self) -> dict[str, object]:
        evaluation = self.risk_evaluation
        verdict = evaluation.risk if evaluation is not None else None
        order = self.proposed_order
        return {
            "pipeline": [
                "risk",
                "execution_intent",
                "execution_plan",
                "planning_policy",
            ],
            "requested_action": self.requested_action,
            "decision_status": self.decision_status,
            "risk_status": evaluation.status if evaluation is not None else "not_required",
            "risk_allowed": self.risk_allowed,
            "risk_reason": verdict.reason if verdict is not None else "",
            "risk_detail": verdict.detail if verdict is not None else "",
            "risk_order_notional": (
                str(verdict.order_notional)
                if verdict is not None and verdict.order_notional is not None
                else ""
            ),
            "proposed_order": {
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": str(order.quantity),
                "client_order_id": order.client_order_id or "",
            }
            if order is not None
            else {},
            "execution_intent_count": len(self.execution_plan.intents),
            "execution_plan_immutable": True,
            "planning_policy_accepted_count": len(
                self.planning_policy.accepted_intents
            ),
            "planning_policy_skipped_count": len(
                self.planning_policy.skipped_intents
            ),
            "policy_accepted": self.policy_accepted,
            "runtime_risk_context_applied": (
                self.risk_evaluation is not None
                and self.portfolio is not None
            ),
            "blockers": list(self.blockers),
        }


def build_canonical_paper_runtime_plan(
    planning_input: PaperRuntimePlanningInput,
) -> CanonicalPaperRuntimePlan:
    """Build the only risk-approved plan eligible for the paper broker envelope."""

    if not isinstance(planning_input, PaperRuntimePlanningInput):
        raise ValidationError("planning_input must be PaperRuntimePlanningInput.")

    symbol = symbol_value(planning_input.symbol)
    action = planning_input.action.strip().lower()
    if action not in _SUPPORTED_ACTIONS:
        raise ValidationError("paper runtime action is unsupported.")

    if action == "blocked":
        blocker = planning_input.reason.strip() or "runtime_intent_blocked"
        return _blocked_plan(action, blocker)
    if action == "hold":
        execution_plan, planning_policy = _empty_plan_and_policy()
        return CanonicalPaperRuntimePlan(
            requested_action=action,
            decision_status="no_action_required",
            proposed_order=None,
            portfolio=None,
            quote=None,
            risk_evaluation=None,
            execution_plan=execution_plan,
            planning_policy=planning_policy,
            blockers=(),
        )

    latest_bar = planning_input.latest_bar
    if not isinstance(latest_bar, Bar) or latest_bar.symbol != symbol:
        return _blocked_plan(action, "canonical_latest_bar_unavailable")
    if planning_input.account_cash is None:
        return _blocked_plan(action, "canonical_portfolio_cash_unavailable")

    max_notional = decimal_value(planning_input.max_notional, "max_notional")
    if max_notional <= 0:
        raise ValidationError("max_notional must be greater than zero.")
    client_order_id = planning_input.client_order_id.strip()
    if not client_order_id:
        return _blocked_plan(action, "canonical_client_order_id_unavailable")

    quote = Quote(
        symbol=symbol,
        timestamp=latest_bar.timestamp,
        bid=latest_bar.close,
        ask=latest_bar.close,
    )
    if action == "buy":
        side = OrderSide.BUY
        quantity = max_notional / latest_bar.close
    else:
        side = OrderSide.SELL
        if planning_input.quantity is None:
            return _blocked_plan(action, "canonical_sell_quantity_unavailable")
        quantity = decimal_value(planning_input.quantity, "quantity")

    order = ProposedOrder(
        symbol=symbol,
        side=side,
        order_type=OrderType.MARKET,
        quantity=quantity,
        client_order_id=client_order_id,
    )
    portfolio = PortfolioState(
        account=Account(planning_input.account_cash, planning_input.currency),
        positions=planning_input.positions,
        risk=RiskState(
            trading_enabled=planning_input.trading_enabled,
            reason=(planning_input.trading_disabled_reason.strip() or None),
        ),
        timestamp=latest_bar.timestamp,
    )
    risk = RiskEngine(
        RiskConfig(
            max_order_notional=max_notional,
            allow_short=False,
            allow_fractional_shares=True,
            max_positions=1,
            max_gross_exposure=max_notional,
            max_symbol_exposure=max_notional,
        )
    ).check(order, portfolio, quote, planning_input.risk_context)
    risk_evaluation = SignalRiskEvaluation(
        symbol=symbol,
        previous_bar=latest_bar,
        quote=quote,
        order=order,
        risk=risk,
        status="risk_approved" if risk.allowed else "risk_rejected",
    )
    intents = build_execution_intents_from_risk_approved((risk_evaluation,))
    execution_plan = build_execution_plan(intents)
    planning_policy = apply_max_intents_execution_planning_policy(
        execution_plan,
        MaxAcceptedIntentsPolicyConfig(max_accepted_intents=1),
    )
    blockers: tuple[str, ...] = ()
    decision_status = "accepted"
    if not risk.allowed:
        blockers = (f"canonical_risk_rejected_{risk.reason}",)
        decision_status = "risk_rejected"
    elif len(planning_policy.accepted_intents) != 1:
        blockers = ("canonical_planning_policy_rejected",)
        decision_status = "planning_policy_rejected"

    return CanonicalPaperRuntimePlan(
        requested_action=action,
        decision_status=decision_status,
        proposed_order=order,
        portfolio=portfolio,
        quote=quote,
        risk_evaluation=risk_evaluation,
        execution_plan=execution_plan,
        planning_policy=planning_policy,
        blockers=blockers,
    )


def _empty_plan_and_policy() -> tuple[ExecutionPlan, PlanningPolicyResult]:
    execution_plan = build_execution_plan(())
    planning_policy = apply_max_intents_execution_planning_policy(
        execution_plan,
        MaxAcceptedIntentsPolicyConfig(max_accepted_intents=1),
    )
    return execution_plan, planning_policy


def _blocked_plan(action: str, blocker: str) -> CanonicalPaperRuntimePlan:
    execution_plan, planning_policy = _empty_plan_and_policy()
    return CanonicalPaperRuntimePlan(
        requested_action=action,
        decision_status="blocked_before_risk",
        proposed_order=None,
        portfolio=None,
        quote=None,
        risk_evaluation=None,
        execution_plan=execution_plan,
        planning_policy=planning_policy,
        blockers=(blocker,),
    )
