"""Local fake broker backed by the deterministic paper execution simulator."""

from __future__ import annotations

from algotrader.core.types import ProposedOrder, Quote
from algotrader.errors import AlgoTraderError
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.execution.simulator import simulate_order
from algotrader.portfolio.state import Account, PortfolioState, Position, apply_fill
from algotrader.risk.state import RiskVerdict


class LocalBroker:
    """A replaceable local broker implementation with no external API calls."""

    def __init__(
        self,
        portfolio: PortfolioState,
        *,
        require_risk_approval: bool = True,
        order_id_prefix: str = "local-order",
    ) -> None:
        self._portfolio = portfolio
        self._require_risk_approval = require_risk_approval
        self._order_id_prefix = order_id_prefix
        self._next_order_number = 1

    def submit_order(
        self,
        order: ProposedOrder,
        quote: Quote,
        risk_verdict: RiskVerdict | None = None,
        order_id: str | None = None,
    ) -> BrokerOrderResult:
        if self._require_risk_approval and risk_verdict is None:
            return BrokerOrderResult(
                accepted=False,
                reason="risk_approval_required",
                portfolio=self._portfolio,
            )

        if risk_verdict is not None and not risk_verdict.allowed:
            return BrokerOrderResult(
                accepted=False,
                reason=risk_verdict.reason or "risk_rejected",
                portfolio=self._portfolio,
            )

        try:
            execution = simulate_order(
                order=order,
                quote=quote,
                order_id=order_id or self._next_order_id(),
            )
            if execution.fill is not None:
                self._portfolio = apply_fill(self._portfolio, execution.fill)

            return BrokerOrderResult(
                accepted=True,
                execution=execution,
                portfolio=self._portfolio,
            )
        except AlgoTraderError as exc:
            return BrokerOrderResult(
                accepted=False,
                reason=str(exc),
                portfolio=self._portfolio,
            )

    def get_account(self) -> Account:
        return self._portfolio.account

    def get_positions(self) -> tuple[Position, ...]:
        return self._portfolio.positions

    def _next_order_id(self) -> str:
        order_id = f"{self._order_id_prefix}-{self._next_order_number}"
        self._next_order_number += 1
        return order_id
