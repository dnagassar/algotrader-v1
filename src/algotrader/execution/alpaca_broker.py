"""Skeleton Alpaca paper broker adapter.

This module defines the future Alpaca paper broker boundary without making any
network calls, loading credentials, or depending on Alpaca SDK packages.
"""

from __future__ import annotations

from algotrader.core.types import ProposedOrder, Quote
from algotrader.errors import BrokerNotImplementedError
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position
from algotrader.risk.state import RiskVerdict


class AlpacaPaperBroker:
    """Broker-shaped skeleton for future Alpaca paper integration.

    The implementation is intentionally absent. Future work must implement this
    adapter without leaking broker-specific behavior into signal, risk,
    portfolio, valuation, or feature calculation logic, and it must satisfy the
    broker contract tests before use.
    """

    def submit_order(
        self,
        order: ProposedOrder,
        quote: Quote,
        risk_verdict: RiskVerdict | None = None,
        order_id: str | None = None,
    ) -> BrokerOrderResult:
        """Submit an order to Alpaca paper trading in a future implementation."""

        raise BrokerNotImplementedError(_MESSAGE)

    def get_account(self) -> Account:
        """Return Alpaca paper account state in a future implementation."""

        raise BrokerNotImplementedError(_MESSAGE)

    def get_positions(self) -> tuple[Position, ...]:
        """Return Alpaca paper positions in a future implementation."""

        raise BrokerNotImplementedError(_MESSAGE)


_MESSAGE = (
    "AlpacaPaperBroker is a skeleton only. It performs no network calls, "
    "does not use credentials, and must satisfy broker contract tests before "
    "it can be implemented."
)
