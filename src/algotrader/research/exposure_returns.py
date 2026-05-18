"""Research-only exposure-applied close-to-close return metadata."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.moving_average import MovingAverageInput
from algotrader.research.moving_average_exposure import MovingAverageExposureState
from algotrader.research.return_construction import simple_return

__all__ = [
    "ExposureReturnObservation",
    "build_exposure_applied_returns",
]

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class ExposureReturnObservation:
    """Exposure-applied return metadata for one dated synthetic value."""

    observation_date: date
    value: Decimal
    current_exposure: int
    asset_return: Decimal | None
    exposure_return: Decimal | None
    return_available: bool
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_date",
            _plain_date_value(self.observation_date, "observation_date"),
        )
        object.__setattr__(self, "value", _positive_decimal_value(self.value, "value"))
        object.__setattr__(
            self,
            "current_exposure",
            _exposure_value(self.current_exposure, "current_exposure"),
        )
        object.__setattr__(
            self,
            "return_available",
            _bool_value(self.return_available, "return_available"),
        )
        object.__setattr__(self, "reason", _reason_value(self.reason))

        if not self.return_available:
            if self.asset_return is not None:
                raise ValidationError(
                    "asset_return must be None when return_available is false."
                )
            if self.exposure_return is not None:
                raise ValidationError(
                    "exposure_return must be None when return_available is false."
                )
            return

        object.__setattr__(
            self,
            "asset_return",
            _finite_decimal_value(self.asset_return, "asset_return"),
        )
        object.__setattr__(
            self,
            "exposure_return",
            _finite_decimal_value(self.exposure_return, "exposure_return"),
        )

        expected_exposure_return = (
            _ZERO if self.current_exposure == 0 else self.asset_return
        )
        if self.exposure_return != expected_exposure_return:
            raise ValidationError(
                "exposure_return must match asset_return applied to current_exposure."
            )


def build_exposure_applied_returns(
    values: Iterable[MovingAverageInput],
    exposure_states: Iterable[MovingAverageExposureState],
) -> tuple[ExposureReturnObservation, ...]:
    """Apply current exposure states to close-to-close simple returns."""

    checked_values = _value_tuple(values)
    checked_exposure_states = _exposure_state_tuple(exposure_states)
    if len(checked_values) != len(checked_exposure_states):
        raise ValidationError("values and exposure_states must have the same length.")

    observations: list[ExposureReturnObservation] = []
    previous_value: Decimal | None = None

    for value_row, exposure_state in zip(checked_values, checked_exposure_states):
        if value_row.observation_date != exposure_state.observation_date:
            raise ValidationError(
                "values and exposure_states must use matching observation dates."
            )

        asset_return: Decimal | None = None
        exposure_return: Decimal | None = None
        return_available = False

        if previous_value is not None:
            asset_return = simple_return(previous_value, value_row.value)
            exposure_return = (
                _ZERO
                if exposure_state.current_exposure == 0
                else asset_return * Decimal(exposure_state.current_exposure)
            )
            return_available = True

        observations.append(
            ExposureReturnObservation(
                observation_date=value_row.observation_date,
                value=value_row.value,
                current_exposure=exposure_state.current_exposure,
                asset_return=asset_return,
                exposure_return=exposure_return,
                return_available=return_available,
                reason=exposure_state.reason,
            )
        )
        previous_value = value_row.value

    return tuple(observations)


def _value_tuple(
    values: Iterable[MovingAverageInput],
) -> tuple[MovingAverageInput, ...]:
    try:
        value_items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "values must be an iterable of MovingAverageInput."
        ) from exc

    if not value_items:
        raise ValidationError("values must contain at least one MovingAverageInput.")

    seen_dates: set[date] = set()
    previous_date: date | None = None
    for value in value_items:
        if not isinstance(value, MovingAverageInput):
            raise ValidationError("values must contain MovingAverageInput values.")
        if value.observation_date in seen_dates:
            raise ValidationError("values must not contain duplicate dates.")
        if previous_date is not None and value.observation_date <= previous_date:
            raise ValidationError("values must be strictly increasing by date.")

        seen_dates.add(value.observation_date)
        previous_date = value.observation_date

    return value_items


def _exposure_state_tuple(
    exposure_states: Iterable[MovingAverageExposureState],
) -> tuple[MovingAverageExposureState, ...]:
    try:
        exposure_state_items = tuple(exposure_states)
    except TypeError as exc:
        raise ValidationError(
            "exposure_states must be an iterable of MovingAverageExposureState."
        ) from exc

    if not exposure_state_items:
        raise ValidationError(
            "exposure_states must contain at least one MovingAverageExposureState."
        )

    seen_dates: set[date] = set()
    previous_date: date | None = None
    for exposure_state in exposure_state_items:
        if not isinstance(exposure_state, MovingAverageExposureState):
            raise ValidationError(
                "exposure_states must contain MovingAverageExposureState values."
            )
        if exposure_state.observation_date in seen_dates:
            raise ValidationError("exposure_states must not contain duplicate dates.")
        if (
            previous_date is not None
            and exposure_state.observation_date <= previous_date
        ):
            raise ValidationError(
                "exposure_states must be strictly increasing by date."
            )

        seen_dates.add(exposure_state.observation_date)
        previous_date = exposure_state.observation_date

    return exposure_state_items


def _plain_date_value(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def _positive_decimal_value(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite() or value <= _ZERO:
        raise ValidationError(f"{field_name} must be greater than zero.")

    return value


def _finite_decimal_value(value: Decimal | None, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _exposure_value(value: int, field_name: str) -> int:
    if type(value) is not int or value not in (0, 1):
        raise ValidationError(f"{field_name} must be integer 0 or 1.")

    return value


def _bool_value(value: bool, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")

    return value


def _reason_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("reason must be a non-empty string.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError("reason must be a non-empty string.")

    return normalized
