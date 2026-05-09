"""Immutable validated research artifact metadata contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from algotrader.core.validation import timestamp_value
from algotrader.errors import ValidationError

__all__ = [
    "ResearchMetric",
    "ValidatedResearchArtifact",
]


@dataclass(frozen=True, slots=True)
class ResearchMetric:
    """Named metric recorded as evidence for a validated research artifact."""

    name: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_string(self.name, "name"))
        object.__setattr__(self, "value", _required_string(self.value, "value"))


@dataclass(frozen=True, slots=True)
class ValidatedResearchArtifact:
    """Metadata-only record for reviewed research evidence."""

    artifact_id: str
    name: str
    version: str
    description: str
    validated_at: datetime
    metrics: tuple[ResearchMetric, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    approved_for: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_id",
            _required_string(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(self, "name", _required_string(self.name, "name"))
        object.__setattr__(
            self,
            "version",
            _required_string(self.version, "version"),
        )
        object.__setattr__(
            self,
            "description",
            _required_string(self.description, "description"),
        )
        timestamp_value(self.validated_at)
        object.__setattr__(self, "metrics", _metric_tuple(self.metrics))
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
        object.__setattr__(
            self,
            "approved_for",
            _string_tuple(self.approved_for, "approved_for"),
        )


def _required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _metric_tuple(metrics: Iterable[ResearchMetric]) -> tuple[ResearchMetric, ...]:
    try:
        metric_items = tuple(metrics)
    except TypeError as exc:
        raise ValidationError("metrics must be an iterable of ResearchMetric.") from exc

    for metric in metric_items:
        if not isinstance(metric, ResearchMetric):
            raise ValidationError("metrics must contain ResearchMetric values.")

    return metric_items


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
