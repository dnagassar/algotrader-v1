"""Deterministic time contracts for explicit timestamp handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from algotrader.errors import ValidationError


_UTC_OFFSET = timedelta(0)


def require_utc_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("timestamp must be a datetime.")

    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        raise ValidationError("timestamp must be a timezone-aware UTC datetime.")
    if offset != _UTC_OFFSET:
        raise ValidationError("timestamp must be UTC.")

    return value


class Clock(Protocol):
    def now(self) -> datetime:
        ...


@dataclass(frozen=True, slots=True)
class FixedClock:
    timestamp: datetime

    def __post_init__(self) -> None:
        _require_utc_datetime(self.timestamp, "timestamp")

    def now(self) -> datetime:
        return self.timestamp


def assert_not_after_as_of(observed_at: datetime, as_of: datetime) -> None:
    observed_at = _require_utc_datetime(observed_at, "observed_at")
    as_of = _require_utc_datetime(as_of, "as_of")

    if observed_at > as_of:
        raise ValidationError("observed_at must not be after as_of.")


def _require_utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc
