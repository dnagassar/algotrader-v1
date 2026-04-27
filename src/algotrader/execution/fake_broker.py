"""Local fake broker backed by the deterministic paper execution simulator."""

from __future__ import annotations

from algotrader.core.types import ProposedOrder, Quote
from algotrader.errors import AlgoTraderError
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.execution.ledger import InMemoryLedger, LedgerEventType
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
        ledger: InMemoryLedger | None = None,
    ) -> None:
        self._portfolio = portfolio
        self._require_risk_approval = require_risk_approval
        self._order_id_prefix = order_id_prefix
        self._next_order_number = 1
        self._ledger = ledger

    def submit_order(
        self,
        order: ProposedOrder,
        quote: Quote,
        risk_verdict: RiskVerdict | None = None,
        order_id: str | None = None,
    ) -> BrokerOrderResult:
        resolved_order_id = order_id or self._next_order_id()
        self._record(
            LedgerEventType.ORDER_SUBMITTED,
            quote,
            resolved_order_id,
            order.symbol,
        )

        if self._require_risk_approval and risk_verdict is None:
            self._record(
                LedgerEventType.ORDER_REJECTED,
                quote,
                resolved_order_id,
                order.symbol,
                "risk_approval_required",
            )
            return BrokerOrderResult(
                accepted=False,
                reason="risk_approval_required",
                portfolio=self._portfolio,
            )

        if risk_verdict is not None and not risk_verdict.allowed:
            reason = risk_verdict.reason or "risk_rejected"
            self._record(
                LedgerEventType.ORDER_REJECTED,
                quote,
                resolved_order_id,
                order.symbol,
                reason,
            )
            return BrokerOrderResult(
                accepted=False,
                reason=reason,
                portfolio=self._portfolio,
            )

        try:
            execution = simulate_order(
                order=order,
                quote=quote,
                order_id=resolved_order_id,
            )
            if execution.fill is not None:
                self._portfolio = apply_fill(self._portfolio, execution.fill)
                self._record(
                    LedgerEventType.ORDER_FILLED,
                    quote,
                    resolved_order_id,
                    order.symbol,
                )
                self._record(
                    LedgerEventType.PORTFOLIO_UPDATED,
                    quote,
                    resolved_order_id,
                    order.symbol,
                )
            else:
                self._record(
                    LedgerEventType.ORDER_NOT_FILLED,
                    quote,
                    resolved_order_id,
                    order.symbol,
                    execution.ack.message,
                )

            return BrokerOrderResult(
                accepted=True,
                execution=execution,
                portfolio=self._portfolio,
            )
        except AlgoTraderError as exc:
            self._record(
                LedgerEventType.ORDER_REJECTED,
                quote,
                resolved_order_id,
                order.symbol,
                str(exc),
            )
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

    def _record(
        self,
        event_type: LedgerEventType,
        quote: Quote,
        order_id: str,
        symbol: str,
        message: str = "",
    ) -> None:
        if self._ledger is None:
            return

        self._ledger.append(
            event_type,
            quote.timestamp,
            order_id=order_id,
            symbol=symbol,
            message=message,
        )
