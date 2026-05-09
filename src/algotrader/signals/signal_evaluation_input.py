"""Immutable signal evaluation input snapshot metadata contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError

__all__ = [
    "SignalEvaluationInputSnapshot",
]


@dataclass(frozen=True, slots=True)
class SignalEvaluationInputSnapshot:
    """Reference metadata for deterministic future signal evaluation inputs."""

    snapshot_id: str
    as_of: datetime
    required_input_names: tuple[str, ...]
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            _required_string(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "required_input_names",
            _string_tuple(self.required_input_names, "required_input_names"),
        )
        object.__setattr__(
            self,
            "source_ids",
            _string_tuple(self.source_ids, "source_ids"),
        )


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


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValidationError(f"{field_name} must be an iterable of strings.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be an iterable of strings.") from exc

    return tuple(
        _required_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )
