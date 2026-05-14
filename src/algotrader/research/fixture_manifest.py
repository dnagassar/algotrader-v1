"""Immutable metadata contract for deterministic research fixtures."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.errors import ValidationError

__all__ = [
    "FIXTURE_KINDS",
    "SOURCE_TYPES",
    "ResearchFixtureManifest",
]


FIXTURE_KINDS = ("synthetic", "derived", "local_only")
SOURCE_TYPES = ("synthetic", "manual", "third_party", "local_snapshot")


@dataclass(frozen=True, slots=True)
class ResearchFixtureManifest:
    """Metadata-only provenance record for deterministic research fixtures."""

    fixture_id: str
    fixture_kind: str
    description: str
    source_name: str
    source_type: str
    retrieval_date: date | None
    data_start: date | None
    data_end: date | None
    fields: tuple[str, ...]
    checksum: str
    normal_pytest_eligible: bool
    redistribution_safe: bool
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fixture_id",
            _required_string(self.fixture_id, "fixture_id"),
        )
        object.__setattr__(
            self,
            "fixture_kind",
            _allowed_string(self.fixture_kind, "fixture_kind", FIXTURE_KINDS),
        )
        object.__setattr__(
            self,
            "description",
            _required_string(self.description, "description"),
        )
        object.__setattr__(
            self,
            "source_name",
            _required_string(self.source_name, "source_name"),
        )
        object.__setattr__(
            self,
            "source_type",
            _allowed_string(self.source_type, "source_type", SOURCE_TYPES),
        )
        object.__setattr__(
            self,
            "retrieval_date",
            _optional_plain_date(self.retrieval_date, "retrieval_date"),
        )
        object.__setattr__(
            self,
            "data_start",
            _optional_plain_date(self.data_start, "data_start"),
        )
        object.__setattr__(
            self,
            "data_end",
            _optional_plain_date(self.data_end, "data_end"),
        )
        object.__setattr__(
            self,
            "fields",
            _required_string_tuple(self.fields, "fields"),
        )
        object.__setattr__(self, "checksum", _required_string(self.checksum, "checksum"))
        object.__setattr__(
            self,
            "normal_pytest_eligible",
            _required_bool(self.normal_pytest_eligible, "normal_pytest_eligible"),
        )
        object.__setattr__(
            self,
            "redistribution_safe",
            _required_bool(self.redistribution_safe, "redistribution_safe"),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _string_tuple(self.non_claims, "non_claims"),
        )
        _validate_date_range(self.data_start, self.data_end)
        _validate_normal_pytest_eligibility(
            self.fixture_kind,
            self.source_type,
            self.normal_pytest_eligible,
            self.redistribution_safe,
        )


def _required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _allowed_string(
    value: str,
    field_name: str,
    allowed_values: tuple[str, ...],
) -> str:
    normalized = _required_string(value, field_name)
    if normalized not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ValidationError(f"{field_name} must be one of: {allowed}.")
    return normalized


def _optional_plain_date(value: date | None, field_name: str) -> date | None:
    if value is None:
        return None
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")
    return value


def _required_bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a bool.")
    return value


def _required_string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    items = _string_tuple(values, field_name)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")
    return items


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


def _validate_date_range(data_start: date | None, data_end: date | None) -> None:
    if data_start is not None and data_end is not None and data_end < data_start:
        raise ValidationError("data_end must be on or after data_start.")


def _validate_normal_pytest_eligibility(
    fixture_kind: str,
    source_type: str,
    normal_pytest_eligible: bool,
    redistribution_safe: bool,
) -> None:
    if not normal_pytest_eligible:
        return

    if not redistribution_safe:
        raise ValidationError(
            "normal_pytest_eligible fixtures must be redistribution safe."
        )
    if fixture_kind == "local_only":
        raise ValidationError("local_only fixtures are not normal pytest eligible.")
    if source_type in {"third_party", "local_snapshot"}:
        raise ValidationError(
            "third_party and local_snapshot sources are not normal pytest eligible."
        )
    if fixture_kind == "synthetic" and source_type != "synthetic":
        raise ValidationError(
            "synthetic fixtures must use synthetic sources for normal pytest."
        )
    if fixture_kind == "derived" and source_type not in {"synthetic", "manual"}:
        raise ValidationError(
            "derived fixtures must use synthetic or manual sources for normal pytest."
        )
