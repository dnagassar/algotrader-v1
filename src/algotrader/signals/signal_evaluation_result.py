"""Immutable advisory signal evaluation result contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError

__all__ = [
    "SignalEvaluationResult",
]


@dataclass(frozen=True, slots=True)
class SignalEvaluationResult:
    """Advisory metadata for one deterministic signal evaluation result."""

    evaluation_id: str
    signal_id: str
    signal_version: str
    source_artifact_id: str
    source_artifact_version: str
    as_of: datetime
    evaluated_at: datetime
    input_fingerprint: str
    output_value: str
    reason_code: str
    diagnostics: tuple[str, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evaluation_id",
            _required_string(self.evaluation_id, "evaluation_id"),
        )
        object.__setattr__(
            self,
            "signal_id",
            _required_string(self.signal_id, "signal_id"),
        )
        object.__setattr__(
            self,
            "signal_version",
            _required_string(self.signal_version, "signal_version"),
        )
        object.__setattr__(
            self,
            "source_artifact_id",
            _required_string(self.source_artifact_id, "source_artifact_id"),
        )
        object.__setattr__(
            self,
            "source_artifact_version",
            _required_string(
                self.source_artifact_version,
                "source_artifact_version",
            ),
        )
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "evaluated_at",
            _utc_datetime(self.evaluated_at, "evaluated_at"),
        )
        object.__setattr__(
            self,
            "input_fingerprint",
            _required_string(self.input_fingerprint, "input_fingerprint"),
        )
        object.__setattr__(
            self,
            "output_value",
            _required_string(self.output_value, "output_value"),
        )
        object.__setattr__(
            self,
            "reason_code",
            _required_string(self.reason_code, "reason_code"),
        )
        object.__setattr__(
            self,
            "diagnostics",
            _string_tuple(self.diagnostics, "diagnostics"),
        )
        object.__setattr__(
            self,
            "assumptions",
            _string_tuple(self.assumptions, "assumptions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )


def _required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


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
