"""Tiny in-memory event ledger for deterministic local broker flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class LedgerEventType(StrEnum):
    ORDER_SUBMITTED = "order_submitted"
    ORDER_REJECTED = "order_rejected"
    ORDER_FILLED = "order_filled"
    ORDER_NOT_FILLED = "order_not_filled"
    PORTFOLIO_UPDATED = "portfolio_updated"
    RECONCILIATION_CHECKED = "reconciliation_checked"


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    event_type: LedgerEventType
    timestamp: datetime
    order_id: str | None = None
    symbol: str | None = None
    message: str = ""


class InMemoryLedger:
    """Append-only local event ledger that preserves insertion order."""

    def __init__(self) -> None:
        self._events: list[LedgerEvent] = []

    def append(
        self,
        event_type: LedgerEventType | str,
        timestamp: datetime,
        *,
        order_id: str | None = None,
        symbol: str | None = None,
        message: str = "",
    ) -> LedgerEvent:
        event = LedgerEvent(
            event_type=LedgerEventType(event_type),
            timestamp=timestamp,
            order_id=order_id,
            symbol=symbol,
            message=message,
        )
        self._events.append(event)
        return event

    def list_events(self) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    def by_order_id(self, order_id: str) -> tuple[LedgerEvent, ...]:
        return tuple(event for event in self._events if event.order_id == order_id)
