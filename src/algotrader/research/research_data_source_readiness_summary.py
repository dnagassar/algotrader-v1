"""Deterministic metadata summary for research data source readiness."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
)

__all__ = [
    "ResearchDataSourceReadinessSummary",
    "build_research_data_source_readiness_summary",
]

_SUMMARY_TYPE = "research_data_source_readiness_summary"
_SCHEMA_VERSION = "1"
_SUMMARY_SCOPE = "advisory_metadata_only"


@dataclass(frozen=True, slots=True)
class ResearchDataSourceReadinessSummary:
    """Advisory metadata summary over an existing readiness object."""

    summary_type: str
    schema_version: str
    summary_scope: str
    summary_state: str
    required_control_count: int
    satisfied_control_count: int
    missing_control_count: int
    diagnostic_limitations: tuple[str, ...]
    source_readiness: ResearchDataSourceReadiness

    def __post_init__(self) -> None:
        source_readiness = _require_source_readiness(self.source_readiness)
        _validate_fixed_metadata(
            self.summary_type,
            self.schema_version,
            self.summary_scope,
        )
        object.__setattr__(
            self,
            "summary_state",
            _required_string(self.summary_state, "summary_state"),
        )
        object.__setattr__(
            self,
            "required_control_count",
            _non_negative_int(
                self.required_control_count,
                "required_control_count",
            ),
        )
        object.__setattr__(
            self,
            "satisfied_control_count",
            _non_negative_int(
                self.satisfied_control_count,
                "satisfied_control_count",
            ),
        )
        object.__setattr__(
            self,
            "missing_control_count",
            _non_negative_int(self.missing_control_count, "missing_control_count"),
        )
        object.__setattr__(
            self,
            "diagnostic_limitations",
            _string_tuple(
                self.diagnostic_limitations,
                "diagnostic_limitations",
            ),
        )
        object.__setattr__(self, "source_readiness", source_readiness)
        _validate_source_summary(self, source_readiness)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only summary metadata."""

        return {
            "summary_type": self.summary_type,
            "schema_version": self.schema_version,
            "summary_scope": self.summary_scope,
            "summary_state": self.summary_state,
            "required_control_count": self.required_control_count,
            "satisfied_control_count": self.satisfied_control_count,
            "missing_control_count": self.missing_control_count,
            "diagnostic_limitations": list(self.diagnostic_limitations),
        }


def build_research_data_source_readiness_summary(
    source_readiness: ResearchDataSourceReadiness,
) -> ResearchDataSourceReadinessSummary:
    """Build a deterministic summary from existing readiness metadata."""

    readiness = _require_source_readiness(source_readiness)

    return ResearchDataSourceReadinessSummary(
        summary_type=_SUMMARY_TYPE,
        schema_version=_SCHEMA_VERSION,
        summary_scope=_SUMMARY_SCOPE,
        summary_state=readiness.readiness_state,
        required_control_count=len(readiness.required_controls),
        satisfied_control_count=len(readiness.satisfied_controls),
        missing_control_count=len(readiness.missing_controls),
        diagnostic_limitations=_diagnostic_limitations(readiness),
        source_readiness=readiness,
    )


def _require_source_readiness(value: object) -> ResearchDataSourceReadiness:
    if type(value) is not ResearchDataSourceReadiness:
        raise ValidationError(
            "source_readiness must be a ResearchDataSourceReadiness."
        )

    return value


def _validate_fixed_metadata(
    summary_type: object,
    schema_version: object,
    summary_scope: object,
) -> None:
    if type(summary_type) is not str or summary_type != _SUMMARY_TYPE:
        raise ValidationError(
            "summary_type must be exactly research_data_source_readiness_summary."
        )
    if type(schema_version) is not str or schema_version != _SCHEMA_VERSION:
        raise ValidationError("schema_version must be exactly 1.")
    if type(summary_scope) is not str or summary_scope != _SUMMARY_SCOPE:
        raise ValidationError("summary_scope must be exactly advisory_metadata_only.")


def _validate_source_summary(
    summary: ResearchDataSourceReadinessSummary,
    source_readiness: ResearchDataSourceReadiness,
) -> None:
    _validate_matches_source(
        "summary_state",
        summary.summary_state,
        source_readiness.readiness_state,
    )
    _validate_matches_source(
        "required_control_count",
        summary.required_control_count,
        len(source_readiness.required_controls),
    )
    _validate_matches_source(
        "satisfied_control_count",
        summary.satisfied_control_count,
        len(source_readiness.satisfied_controls),
    )
    _validate_matches_source(
        "missing_control_count",
        summary.missing_control_count,
        len(source_readiness.missing_controls),
    )
    _validate_matches_source(
        "diagnostic_limitations",
        summary.diagnostic_limitations,
        _diagnostic_limitations(source_readiness),
    )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source_readiness.")


def _diagnostic_limitations(
    source_readiness: ResearchDataSourceReadiness,
) -> tuple[str, ...]:
    return tuple(sorted(_dedupe(source_readiness.limitations)))


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value in deduped:
            continue
        deduped.append(value)

    return tuple(deduped)
