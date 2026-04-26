"""Small broker interface for deterministic and future broker implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from algotrader.core.types import ProposedOrder, Quote
from algotrader.execution.simulator import ExecutionResult
from algotrader.portfolio.state import Account, PortfolioState, Position
from algotrader.risk.state import RiskVerdict


@dataclass(frozen=True, slots=True)
class BrokerOrderResult:
    accepted: bool
    reason: str = ""
    execution: ExecutionResult | None = None
    portfolio: PortfolioState | None = None

    @property
    def filled(self) -> bool:
        return self.execution is not None and self.execution.filled


class Broker(Protocol):
    """Minimal broker surface needed by the deterministic core."""

    def submit_order(
        self,
        order: ProposedOrder,
        quote: Quote,
        risk_verdict: RiskVerdict | None = None,
        order_id: str | None = None,
    ) -> BrokerOrderResult:
        """Submit an order after pre-trade risk approval."""

    def get_account(self) -> Account:
        """Return the current account state."""

    def get_positions(self) -> tuple[Position, ...]:
        """Return the current position state."""
