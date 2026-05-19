"""Internal validation helpers for research-planning metadata contracts."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import TypeVar

from algotrader.errors import ValidationError


_T = TypeVar("_T")


def required_string(value: str, field_name: str) -> str:
    """Return a stripped non-empty string or raise a validation error."""

    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return normalized


def allowed_string(
    value: str,
    field_name: str,
    allowed_values: tuple[str, ...],
) -> str:
    """Return a required string that exactly matches an allowed value."""

    normalized = required_string(value, field_name)
    if normalized not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ValidationError(f"{field_name} must be one of: {allowed}.")

    return normalized


def plain_date(value: date, field_name: str) -> date:
    """Return a plain date, rejecting datetimes and non-date values."""

    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def date_to_iso(value: date, field_name: str = "as_of_date") -> str:
    """Serialize a validated plain date deterministically."""

    return plain_date(value, field_name).isoformat()


def string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    """Normalize an iterable of required strings to a tuple."""

    if isinstance(values, str):
        raise ValidationError(f"{field_name} must be an iterable of strings.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be an iterable of strings.") from exc

    return tuple(
        required_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )


def required_string_tuple(
    values: Iterable[str],
    field_name: str,
) -> tuple[str, ...]:
    """Normalize a non-empty iterable of required strings to a tuple."""

    items = string_tuple(values, field_name)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    return items


def unique_required_string_tuple(
    values: Iterable[str],
    field_name: str,
) -> tuple[str, ...]:
    """Normalize a non-empty string tuple and reject duplicate entries."""

    items = required_string_tuple(values, field_name)
    if len(frozenset(items)) != len(items):
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return items


def required_non_claims(
    values: Iterable[str],
    required_claims: tuple[str, ...],
    error_message: str,
) -> tuple[str, ...]:
    """Normalize non-claims and require a contract-specific claim set."""

    items = required_string_tuple(values, "non_claims")
    missing = tuple(claim for claim in required_claims if claim not in items)
    if missing:
        raise ValidationError(error_message)

    return items


def candidate_tuple(
    values: Iterable[_T],
    field_name: str,
    expected_type: type[_T],
) -> tuple[_T, ...]:
    """Normalize a non-empty iterable of candidate contract instances."""

    if isinstance(values, str):
        raise ValidationError(
            f"{field_name} must be an iterable of {expected_type.__name__} values."
        )

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be an iterable of {expected_type.__name__} values."
        ) from exc

    if not items:
        raise ValidationError(f"{field_name} must contain at least one candidate.")

    for item in items:
        if not isinstance(item, expected_type):
            raise ValidationError(
                f"{field_name} must contain {expected_type.__name__} values."
            )

    return items


def validate_unique_candidate_ids(
    candidates: Iterable[object],
    field_name: str,
    id_field_name: str,
) -> None:
    """Reject duplicate candidate ids inside one candidate group."""

    ids: list[str] = []
    for candidate in candidates:
        try:
            candidate_id = getattr(candidate, id_field_name)
        except AttributeError as exc:
            raise ValidationError(f"{field_name} contains malformed candidates.") from exc

        ids.append(required_string(candidate_id, id_field_name))

    if len(frozenset(ids)) != len(ids):
        raise ValidationError(f"{field_name} must not contain duplicate ids.")
