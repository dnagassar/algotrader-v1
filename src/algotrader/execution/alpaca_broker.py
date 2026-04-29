"""Inert Alpaca paper broker skeleton.

This module intentionally does not import alpaca-py, instantiate a real client,
read credentials, or perform network calls. By default, operational methods
raise ``BrokerNotImplementedError``.
"""

from __future__ import annotations

from typing import Any, Optional

from algotrader.core.types import ProposedOrder, Quote
from algotrader.errors import BrokerNotImplementedError
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position
from algotrader.risk.state import RiskVerdict


class AlpacaPaperBroker:
    """Future Alpaca paper broker boundary.

    The broker remains inert by default. Tests may inject a fake adapter to
    exercise broker -> adapter delegation before real SDK connectivity exists.
    """

    def __init__(self, adapter: Optional[Any] = None, config: Optional[Any] = None):
        self._adapter = adapter
        self.config = config

    def get_account(self) -> Account:
        if self._adapter is None:
            raise BrokerNotImplementedError(
                "AlpacaPaperBroker skeleton only; get_account is not "
                "implemented and performs no network calls."
            )

        return self._adapter.get_account()

    def get_positions(self) -> tuple[Position, ...]:
        if self._adapter is None:
            raise BrokerNotImplementedError(
                "AlpacaPaperBroker skeleton only; get_positions is not "
                "implemented and does not use credentials."
            )

        return self._adapter.list_positions()

    def list_positions(self) -> tuple[Position, ...]:
        return self.get_positions()

    def submit_order(
        self,
        order: ProposedOrder,
        quote: Quote,
        risk_verdict: RiskVerdict | None = None,
        order_id: str | None = None,
    ) -> BrokerOrderResult:
        if self._adapter is None:
            raise BrokerNotImplementedError(
                "AlpacaPaperBroker skeleton only; submit_order is not "
                "implemented and performs no network calls."
            )

        return self._adapter.submit_order(
            order,
            quote,
            risk_verdict,
            order_id=order_id,
        )


__all__ = [
    "AlpacaPaperBroker",
    "BrokerNotImplementedError",
]
