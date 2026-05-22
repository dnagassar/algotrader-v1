"""Source-agnostic return-input snapshot metadata contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from algotrader.errors import ValidationError

__all__ = [
    "ResearchReturnInputSnapshot",
]


_SNAPSHOT_FIELD_NAMES = (
    "snapshot_id",
    "symbol",
    "observation_dates",
    "close_values",
    "close_to_close_returns",
    "return_basis",
    "adjustment_policy",
    "synthetic_only",
    "candidate_only",
    "non_claims",
)
_DECIMAL_TUPLE_FIELD_NAMES = frozenset(("close_values", "close_to_close_returns"))
_REQUIRED_NON_CLAIMS = frozenset(
    (
        "not source approval",
        "not data approval",
        "not endpoint approval",
        "not universe approval",
        "not benchmark approval",
        "not cash proxy approval",
        "not methodology approval",
        "not evidence approval",
        "not return-construction approval",
        "not no-lookahead approval",
        "not strategy validation",
        "not trading readiness",
    )
)


@dataclass(frozen=True, slots=True)
class ResearchReturnInputSnapshot:
    """Metadata snapshot for deterministic, already prepared return inputs."""

    snapshot_id: str
    symbol: str
    observation_dates: tuple[date, ...]
    close_values: tuple[Decimal, ...]
    close_to_close_returns: tuple[Decimal, ...]
    return_basis: str
    adjustment_policy: str
    synthetic_only: bool
    candidate_only: bool
    non_claims: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible snapshot representation."""
        payload: dict[str, object] = {}

        for field_name in _SNAPSHOT_FIELD_NAMES:
            value = getattr(self, field_name)
            if field_name == "observation_dates":
                payload[field_name] = [
                    _serialize_plain_date(item) for item in self.observation_dates
                ]
            elif field_name in _DECIMAL_TUPLE_FIELD_NAMES:
                payload[field_name] = [str(item) for item in value]
            elif field_name == "non_claims":
                payload[field_name] = list(self.non_claims)
            else:
                payload[field_name] = value

        return payload

    @classmethod
    def from_dict(cls, payload: object) -> "ResearchReturnInputSnapshot":
        """Restore a snapshot from strict JSON-compatible metadata."""
        if not isinstance(payload, dict):
            raise ValidationError("research return input payload must be a dict.")

        _validate_snapshot_payload_fields(payload)
        values: dict[str, object] = {}

        for field_name in _SNAPSHOT_FIELD_NAMES:
            value = payload[field_name]
            if field_name == "observation_dates":
                values[field_name] = _deserialize_plain_date_list(value, field_name)
            elif field_name in _DECIMAL_TUPLE_FIELD_NAMES:
                values[field_name] = _deserialize_decimal_list(value, field_name)
            elif field_name == "non_claims":
                values[field_name] = _deserialize_string_list(value, field_name)
            else:
                values[field_name] = value

        return cls(**values)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            _required_string(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(self, "symbol", _required_string(self.symbol, "symbol"))
        object.__setattr__(
            self,
            "observation_dates",
            _plain_date_tuple(self.observation_dates, "observation_dates"),
        )
        object.__setattr__(
            self,
            "close_values",
            _decimal_tuple(self.close_values, "close_values", minimum_length=2),
        )
        object.__setattr__(
            self,
            "close_to_close_returns",
            _decimal_tuple(self.close_to_close_returns, "close_to_close_returns"),
        )
        object.__setattr__(
            self,
            "return_basis",
            _required_string(self.return_basis, "return_basis"),
        )
        object.__setattr__(
            self,
            "adjustment_policy",
            _required_string(self.adjustment_policy, "adjustment_policy"),
        )
        object.__setattr__(
            self,
            "synthetic_only",
            _required_true(self.synthetic_only, "synthetic_only"),
        )
        object.__setattr__(
            self,
            "candidate_only",
            _required_true(self.candidate_only, "candidate_only"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _string_tuple(self.non_claims, "non_claims"),
        )
        _validate_lengths(
            self.observation_dates,
            self.close_values,
            self.close_to_close_returns,
        )
        _validate_required_non_claims(self.non_claims)


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _plain_date_tuple(values: Iterable[date], field_name: str) -> tuple[date, ...]:
    items = _tuple_values(values, field_name, "dates")
    dates = tuple(_plain_date(value, f"{field_name}[{index}]") for index, value in enumerate(items))

    if len(dates) != len(set(dates)):
        raise ValidationError("observation_dates must not contain duplicate dates.")

    for previous_date, current_date in zip(dates, dates[1:]):
        if current_date <= previous_date:
            raise ValidationError("observation_dates must be strictly increasing.")

    return dates


def _plain_date(value: object, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")
    return value


def _decimal_tuple(
    values: Iterable[Decimal],
    field_name: str,
    minimum_length: int = 0,
) -> tuple[Decimal, ...]:
    items = _tuple_values(values, field_name, "Decimal values")
    if len(items) < minimum_length:
        raise ValidationError(
            f"{field_name} must contain at least {minimum_length} Decimal values."
        )

    return tuple(
        _decimal_value(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )


def _decimal_value(value: object, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be a finite Decimal.")
    return value


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    items = _tuple_values(values, field_name, "strings")
    return tuple(
        _required_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )


def _tuple_values(values: object, field_name: str, item_description: str) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, bool)):
        raise ValidationError(f"{field_name} must be an iterable of {item_description}.")

    try:
        return tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be an iterable of {item_description}."
        ) from exc


def _required_true(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be exactly True.")
    return value


def _validate_lengths(
    observation_dates: tuple[date, ...],
    close_values: tuple[Decimal, ...],
    close_to_close_returns: tuple[Decimal, ...],
) -> None:
    expected_return_count = len(close_values) - 1
    if len(close_to_close_returns) != expected_return_count:
        raise ValidationError(
            "close_to_close_returns count must equal close_values count minus one."
        )

    expected_observation_return_count = len(observation_dates) - 1
    if len(close_to_close_returns) != expected_observation_return_count:
        raise ValidationError(
            "close_to_close_returns count must equal observation_dates count minus one."
        )


def _validate_required_non_claims(non_claims: tuple[str, ...]) -> None:
    missing = tuple(sorted(_REQUIRED_NON_CLAIMS.difference(non_claims)))
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"non_claims must include required non-claims: {missing_text}."
        )

    positive_claims = tuple(claim for claim in non_claims if not claim.startswith("not "))
    if positive_claims:
        raise ValidationError("non_claims entries must be negative statements.")


def _serialize_plain_date(value: object) -> str:
    if type(value) is not date:
        raise ValidationError("observation_dates must contain plain dates.")
    return value.isoformat()


def _deserialize_plain_date_list(value: object, field_name: str) -> tuple[date, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list of ISO date strings.")

    return tuple(
        _deserialize_plain_date(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )


def _deserialize_plain_date(value: object, field_name: str) -> date:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be an ISO date string.")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO YYYY-MM-DD date string."
        ) from exc

    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")
    return parsed


def _deserialize_decimal_list(value: object, field_name: str) -> tuple[Decimal, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list of Decimal strings.")

    return tuple(
        _deserialize_decimal(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )


def _deserialize_decimal(value: object, field_name: str) -> Decimal:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a Decimal string.")

    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a valid Decimal string.") from exc

    return _decimal_value(parsed, field_name)


def _deserialize_string_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list of strings.")
    return tuple(value)


def _validate_snapshot_payload_fields(payload: dict[object, object]) -> None:
    unknown_fields = tuple(
        field_name for field_name in payload if field_name not in _SNAPSHOT_FIELD_NAMES
    )
    if unknown_fields:
        unknown = ", ".join(str(field_name) for field_name in unknown_fields)
        raise ValidationError(f"unknown research return input field(s): {unknown}.")

    missing_fields = tuple(
        field_name for field_name in _SNAPSHOT_FIELD_NAMES if field_name not in payload
    )
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValidationError(f"missing research return input field(s): {missing}.")
