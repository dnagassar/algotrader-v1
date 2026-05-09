"""Immutable validated signal definition metadata contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError

__all__ = [
    "ValidatedSignalDefinition",
]


@dataclass(frozen=True, slots=True)
class ValidatedSignalDefinition:
    """Metadata-only record for a reviewed deterministic signal definition."""

    signal_id: str
    name: str
    version: str
    description: str
    source_artifact_id: str
    source_artifact_version: str
    required_inputs: tuple[str, ...]
    output_type: str
    evaluation_rule_ref: str
    approved_for: tuple[str, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "signal_id",
            _required_string(self.signal_id, "signal_id"),
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
        object.__setattr__(
            self,
            "required_inputs",
            _string_tuple(self.required_inputs, "required_inputs"),
        )
        object.__setattr__(
            self,
            "output_type",
            _required_string(self.output_type, "output_type"),
        )
        object.__setattr__(
            self,
            "evaluation_rule_ref",
            _required_string(self.evaluation_rule_ref, "evaluation_rule_ref"),
        )
        object.__setattr__(
            self,
            "approved_for",
            _string_tuple(self.approved_for, "approved_for"),
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
