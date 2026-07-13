"""Coordinator-free immutable inputs for durable cancellation admission."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class DurableCancelIdentity:
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    reservation_run_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class DurableCancelEvidence:
    cancel_allowed: bool
    snapshot_fresh: bool

    def __post_init__(self) -> None:
        if type(self.cancel_allowed) is not bool:
            raise ValidationError("cancel_allowed must be a boolean.")
        if type(self.snapshot_fresh) is not bool:
            raise ValidationError("snapshot_fresh must be a boolean.")


__all__ = [
    "DurableCancelEvidence",
    "DurableCancelIdentity",
]
