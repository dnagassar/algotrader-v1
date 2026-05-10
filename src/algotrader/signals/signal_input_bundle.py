"""Immutable deterministic signal input bundle contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from algotrader.core.time import assert_not_after_as_of, require_utc_datetime
from algotrader.errors import ValidationError

from .signal_input_value import SignalInputValue

__all__ = [
    "SignalInputBundle",
]


@dataclass(frozen=True, slots=True)
class SignalInputBundle:
    """Explicit observed values grouped for future signal evaluation."""

    snapshot_id: str
    as_of: datetime
    values: tuple[SignalInputValue, ...]

    def __post_init__(self) -> None:
        as_of = _utc_datetime(self.as_of, "as_of")
        values = _signal_input_value_tuple(self.values)
        _reject_duplicate_value_names(values)
        _reject_lookahead_values(values, as_of)

        object.__setattr__(
            self,
            "snapshot_id",
            _required_string(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "values", values)


def _required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    if not value.strip():
        raise ValidationError(f"{field_name} is required.")
    return value


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _signal_input_value_tuple(
    values: Iterable[SignalInputValue],
) -> tuple[SignalInputValue, ...]:
    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "values must be an iterable of SignalInputValue objects."
        ) from exc

    if not items:
        raise ValidationError("values must contain at least one SignalInputValue.")

    for index, value in enumerate(items):
        if not isinstance(value, SignalInputValue):
            raise ValidationError(f"values[{index}] must be a SignalInputValue.")

    return items


def _reject_duplicate_value_names(values: tuple[SignalInputValue, ...]) -> None:
    seen_names: set[str] = set()
    for value in values:
        if value.name in seen_names:
            raise ValidationError("values contain duplicate SignalInputValue.name.")
        seen_names.add(value.name)


def _reject_lookahead_values(
    values: tuple[SignalInputValue, ...],
    as_of: datetime,
) -> None:
    for value in values:
        try:
            assert_not_after_as_of(value.observed_at, as_of)
        except ValidationError as exc:
            raise ValidationError(
                "values observed_at must not be after as_of."
            ) from exc
