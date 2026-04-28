"""Offline Alpaca client boundary for future paper broker integration.

This module intentionally does not import alpaca-py, instantiate clients, load
credentials, or perform network calls. It only defines the small internal shape
that a future adapter can satisfy.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Protocol


@dataclass(frozen=True)
class AlpacaAccountResponse:
    account_id: str
    status: str
    cash: Decimal
    buying_power: Decimal
    equity: Decimal
    currency: str = "USD"


@dataclass(frozen=True)
class AlpacaPositionResponse:
    symbol: str
    qty: Decimal
    market_value: Decimal
    average_entry_price: Decimal
    side: str = "long"


@dataclass(frozen=True)
class AlpacaOrderRequest:
    client_order_id: str
    symbol: str
    side: str
    qty: Decimal
    order_type: str = "market"
    time_in_force: str = "day"
    limit_price: Optional[Decimal] = None


@dataclass(frozen=True)
class AlpacaOrderSubmissionResponse:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    qty: Decimal
    status: str
    submitted_at: datetime


class AlpacaClient(Protocol):
    """Minimal client protocol a future Alpaca adapter must satisfy."""

    def get_account(self) -> AlpacaAccountResponse:
        ...

    def get_positions(self) -> Sequence[AlpacaPositionResponse]:
        ...

    def submit_order(
        self, request: AlpacaOrderRequest
    ) -> AlpacaOrderSubmissionResponse:
        ...


__all__ = [
    "AlpacaAccountResponse",
    "AlpacaClient",
    "AlpacaOrderRequest",
    "AlpacaOrderSubmissionResponse",
    "AlpacaPositionResponse",
]
