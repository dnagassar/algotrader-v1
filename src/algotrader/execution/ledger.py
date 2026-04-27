"""Tiny in-memory event ledger for deterministic local broker flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path

from algotrader.errors import ValidationError


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


class JsonlLedger:
    """Append-only JSONL event ledger backed by a local file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

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
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(_event_to_record(event), sort_keys=True))
            file.write("\n")
        return event

    def list_events(self) -> tuple[LedgerEvent, ...]:
        if not self._path.exists():
            return ()

        events: list[LedgerEvent] = []
        with self._path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                    events.append(_event_from_record(record))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise ValidationError(
                        f"Malformed ledger event at line {line_number}."
                    ) from exc

        return tuple(events)

    def by_order_id(self, order_id: str) -> tuple[LedgerEvent, ...]:
        return tuple(event for event in self.list_events() if event.order_id == order_id)


def _event_to_record(event: LedgerEvent) -> dict[str, str | None]:
    return {
        "event_type": event.event_type.value,
        "timestamp": event.timestamp.isoformat(),
        "order_id": event.order_id,
        "symbol": event.symbol,
        "message": event.message,
    }


def _event_from_record(record: dict) -> LedgerEvent:
    return LedgerEvent(
        event_type=LedgerEventType(record["event_type"]),
        timestamp=datetime.fromisoformat(record["timestamp"]),
        order_id=record.get("order_id"),
        symbol=record.get("symbol"),
        message=record.get("message", ""),
    )
