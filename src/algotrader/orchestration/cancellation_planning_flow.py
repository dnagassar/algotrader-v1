"""Immutable broker-free cancellation planning contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError


CANCELLATION_PLAN_VERSION = "cancellation_plan_v1"
CANCELABLE_CANCELLATION_STATUSES = frozenset(
    {
        "accepted",
        "accepted_for_bidding",
        "new",
        "partially_filled",
        "pending_new",
    }
)

__all__ = [
    "CANCELABLE_CANCELLATION_STATUSES",
    "CANCELLATION_PLAN_VERSION",
    "CancellationPlan",
    "build_cancellation_plan",
]


@dataclass(frozen=True, slots=True)
class CancellationPlan:
    """One immutable same-order target before any cancellation boundary."""

    plan_id: str
    client_order_id: str
    broker_order_id: str
    symbol: str
    broker_status: str
    observed_at: datetime
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "client_order_id", _required(self.client_order_id, "client_order_id"))
        object.__setattr__(self, "broker_order_id", _required(self.broker_order_id, "broker_order_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        status = _normalized_status(self.broker_status)
        if status not in CANCELABLE_CANCELLATION_STATUSES:
            raise ValidationError("broker_status must be cancelable.")
        object.__setattr__(self, "broker_status", status)
        try:
            observed_at = require_utc_datetime(self.observed_at)
        except ValidationError as exc:
            raise ValidationError(
                "observed_at must be a timezone-aware UTC datetime."
            ) from exc
        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "reason", _required(self.reason, "reason"))
        expected_plan_id = _plan_id(
            client_order_id=self.client_order_id,
            broker_order_id=self.broker_order_id,
            symbol=self.symbol,
            broker_status=self.broker_status,
            observed_at=self.observed_at,
            reason=self.reason,
        )
        if str(self.plan_id).strip() != expected_plan_id:
            raise ValidationError("plan_id does not match cancellation plan identity.")
        object.__setattr__(self, "plan_id", expected_plan_id)

    def to_dict(self) -> dict[str, str]:
        """Return deterministic primitive-only plan metadata."""

        return {
            "plan_id": self.plan_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "symbol": self.symbol,
            "broker_status": self.broker_status,
            "observed_at": self.observed_at.isoformat(),
            "reason": self.reason,
        }


def build_cancellation_plan(
    *,
    client_order_id: str,
    broker_order_id: str,
    symbol: str,
    broker_status: str,
    observed_at: datetime,
    reason: str,
) -> CancellationPlan:
    """Build one deterministic same-order plan without broker behavior."""

    normalized_client_order_id = _required(client_order_id, "client_order_id")
    normalized_broker_order_id = _required(broker_order_id, "broker_order_id")
    normalized_symbol = symbol_value(symbol)
    normalized_status = _normalized_status(broker_status)
    normalized_reason = _required(reason, "reason")
    try:
        normalized_observed_at = require_utc_datetime(observed_at)
    except ValidationError as exc:
        raise ValidationError(
            "observed_at must be a timezone-aware UTC datetime."
        ) from exc
    return CancellationPlan(
        plan_id=_plan_id(
            client_order_id=normalized_client_order_id,
            broker_order_id=normalized_broker_order_id,
            symbol=normalized_symbol,
            broker_status=normalized_status,
            observed_at=normalized_observed_at,
            reason=normalized_reason,
        ),
        client_order_id=normalized_client_order_id,
        broker_order_id=normalized_broker_order_id,
        symbol=normalized_symbol,
        broker_status=normalized_status,
        observed_at=normalized_observed_at,
        reason=normalized_reason,
    )


def _plan_id(
    *,
    client_order_id: str,
    broker_order_id: str,
    symbol: str,
    broker_status: str,
    observed_at: datetime,
    reason: str,
) -> str:
    basis = {
        "version": CANCELLATION_PLAN_VERSION,
        "client_order_id": client_order_id,
        "broker_order_id": broker_order_id,
        "symbol": symbol,
        "broker_status": broker_status,
        "observed_at": observed_at.isoformat(),
        "reason": reason,
    }
    encoded = json.dumps(basis, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"cancel_plan_{hashlib.sha256(encoded).hexdigest()[:24]}"


def _required(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _normalized_status(value: object) -> str:
    text = str(value).strip().lower()
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text.replace("-", "_").replace(" ", "_")
