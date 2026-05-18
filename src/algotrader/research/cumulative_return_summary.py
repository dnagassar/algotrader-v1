"""Research-only summary metadata for cumulative return paths."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.cumulative_returns import CumulativeReturnObservation

__all__ = [
    "CumulativeReturnPathSummary",
    "summarize_cumulative_return_path",
]

_MIN_SIMPLE_RETURN = Decimal("-1")

_DEFAULT_LIMITATIONS = (
    "research-only summary of an already-built cumulative return path",
    "uses only row counts and final cumulative path values",
    "does not validate a strategy, define a signal, evaluate performance, or authorize trading",
)

_DEFAULT_NON_CLAIMS = (
    "not validated evidence",
    "not a strategy approval",
    "not a trading recommendation",
    "not an approved signal",
    "not paper/live trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "exposure is a 0/1 research indicator and not allocation, target weight, position size, or portfolio instruction",
)


@dataclass(frozen=True, slots=True)
class CumulativeReturnPathSummary:
    """Metadata-only summary for an existing cumulative return path."""

    first_observation_date: date
    last_observation_date: date
    observation_count: int
    available_return_count: int
    unavailable_return_count: int
    final_asset_cumulative_return: Decimal
    final_exposure_cumulative_return: Decimal
    has_available_returns: bool
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "first_observation_date",
            _plain_date_value(
                self.first_observation_date,
                "first_observation_date",
            ),
        )
        object.__setattr__(
            self,
            "last_observation_date",
            _plain_date_value(
                self.last_observation_date,
                "last_observation_date",
            ),
        )
        if self.last_observation_date < self.first_observation_date:
            raise ValidationError(
                "last_observation_date must be on or after first_observation_date."
            )

        object.__setattr__(
            self,
            "observation_count",
            _positive_int_value(self.observation_count, "observation_count"),
        )
        object.__setattr__(
            self,
            "available_return_count",
            _non_negative_int_value(
                self.available_return_count,
                "available_return_count",
            ),
        )
        object.__setattr__(
            self,
            "unavailable_return_count",
            _non_negative_int_value(
                self.unavailable_return_count,
                "unavailable_return_count",
            ),
        )
        if (
            self.available_return_count + self.unavailable_return_count
            != self.observation_count
        ):
            raise ValidationError(
                "available_return_count plus unavailable_return_count must equal observation_count."
            )

        object.__setattr__(
            self,
            "has_available_returns",
            _bool_value(self.has_available_returns, "has_available_returns"),
        )
        if self.has_available_returns != (self.available_return_count > 0):
            raise ValidationError(
                "has_available_returns must match available_return_count > 0."
            )

        object.__setattr__(
            self,
            "final_asset_cumulative_return",
            _finite_decimal_value(
                self.final_asset_cumulative_return,
                "final_asset_cumulative_return",
            ),
        )
        object.__setattr__(
            self,
            "final_exposure_cumulative_return",
            _finite_decimal_value(
                self.final_exposure_cumulative_return,
                "final_exposure_cumulative_return",
            ),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple_value(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _string_tuple_value(self.non_claims, "non_claims"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive metadata."""

        return {
            "first_observation_date": self.first_observation_date.isoformat(),
            "last_observation_date": self.last_observation_date.isoformat(),
            "observation_count": self.observation_count,
            "available_return_count": self.available_return_count,
            "unavailable_return_count": self.unavailable_return_count,
            "final_asset_cumulative_return": str(self.final_asset_cumulative_return),
            "final_exposure_cumulative_return": str(
                self.final_exposure_cumulative_return
            ),
            "has_available_returns": self.has_available_returns,
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def summarize_cumulative_return_path(
    path: Iterable[CumulativeReturnObservation],
) -> CumulativeReturnPathSummary:
    """Summarize ordered cumulative return observations without recomputing them."""

    observations = _path_tuple(path)
    available_return_count = sum(
        1 for observation in observations if observation.return_available
    )
    unavailable_return_count = len(observations) - available_return_count
    final_observation = observations[-1]

    return CumulativeReturnPathSummary(
        first_observation_date=observations[0].observation_date,
        last_observation_date=final_observation.observation_date,
        observation_count=len(observations),
        available_return_count=available_return_count,
        unavailable_return_count=unavailable_return_count,
        final_asset_cumulative_return=final_observation.asset_cumulative_return,
        final_exposure_cumulative_return=(
            final_observation.exposure_cumulative_return
        ),
        has_available_returns=available_return_count > 0,
        limitations=_DEFAULT_LIMITATIONS,
        non_claims=_DEFAULT_NON_CLAIMS,
    )


def _path_tuple(
    path: Iterable[CumulativeReturnObservation],
) -> tuple[CumulativeReturnObservation, ...]:
    try:
        observations = tuple(path)
    except TypeError as exc:
        raise ValidationError(
            "path must be an iterable of CumulativeReturnObservation."
        ) from exc

    if not observations:
        raise ValidationError(
            "path must contain at least one CumulativeReturnObservation."
        )

    seen_dates: set[date] = set()
    previous_date: date | None = None

    for observation in observations:
        if not isinstance(observation, CumulativeReturnObservation):
            raise ValidationError(
                "path must contain CumulativeReturnObservation values."
            )

        observation_date = _plain_date_value(
            observation.observation_date,
            "observation_date",
        )
        if observation_date in seen_dates:
            raise ValidationError("path must not contain duplicate dates.")
        if previous_date is not None and observation_date <= previous_date:
            raise ValidationError("path must be strictly increasing by date.")

        _validate_path_observation(observation)
        seen_dates.add(observation_date)
        previous_date = observation_date

    return observations


def _validate_path_observation(observation: CumulativeReturnObservation) -> None:
    _finite_decimal_value(
        observation.asset_cumulative_return,
        "asset_cumulative_return",
    )
    _finite_decimal_value(
        observation.exposure_cumulative_return,
        "exposure_cumulative_return",
    )
    _bool_value(observation.return_available, "return_available")
    _reason_value(observation.reason)

    if not observation.return_available:
        if observation.asset_return is not None:
            raise ValidationError(
                "asset_return must be None when return_available is false."
            )
        if observation.exposure_return is not None:
            raise ValidationError(
                "exposure_return must be None when return_available is false."
            )
        return

    _simple_return_value(observation.asset_return, "asset_return")
    _simple_return_value(observation.exposure_return, "exposure_return")


def _plain_date_value(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def _positive_int_value(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")

    return value


def _non_negative_int_value(value: int, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")

    return value


def _bool_value(value: bool, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")

    return value


def _simple_return_value(value: Decimal | None, field_name: str) -> Decimal:
    checked_value = _finite_decimal_value(value, field_name)
    if checked_value <= _MIN_SIMPLE_RETURN:
        raise ValidationError(f"{field_name} must be greater than -1.")

    return checked_value


def _finite_decimal_value(value: Decimal | None, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _string_tuple_value(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ValidationError(f"{field_name} must be a tuple of non-empty strings.")

    normalized = tuple(_non_empty_string_value(value, field_name) for value in values)

    if not normalized:
        raise ValidationError(f"{field_name} must contain at least one string.")

    return normalized


def _non_empty_string_value(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must contain non-empty strings.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must contain non-empty strings.")

    return normalized


def _reason_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("reason must be a non-empty string.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError("reason must be a non-empty string.")

    return normalized
