"""Immutable deterministic signal input value contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError

__all__ = [
    "SignalInputValue",
    "SignalInputValueScalar",
]


SignalInputValueScalar = Decimal | int | str | bool


@dataclass(frozen=True, slots=True)
class SignalInputValue:
    """One explicit observed value for future deterministic signal evaluation."""

    name: str
    value: SignalInputValueScalar
    observed_at: datetime
    source_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_string(self.name, "name"))
        object.__setattr__(self, "value", _supported_value(self.value))
        object.__setattr__(
            self,
            "observed_at",
            _utc_datetime(self.observed_at, "observed_at"),
        )
        object.__setattr__(
            self,
            "source_id",
            _required_string(self.source_id, "source_id"),
        )


def _required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    if not value.strip():
        raise ValidationError(f"{field_name} is required.")
    return value


def _supported_value(value: object) -> SignalInputValueScalar:
    if isinstance(value, (Decimal, bool, int, str)):
        return value
    raise ValidationError(
        "value must be a deterministic scalar: Decimal, int, str, or bool."
    )


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc
