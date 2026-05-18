"""Deterministic moving-average mechanics for synthetic research inputs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError

__all__ = [
    "MovingAverageInput",
    "MovingAverageObservation",
    "build_simple_moving_average_observations",
]

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class MovingAverageInput:
    """One dated positive Decimal value for moving-average mechanics."""

    observation_date: date
    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_date",
            _plain_date_value(self.observation_date, "observation_date"),
        )
        object.__setattr__(self, "value", _positive_decimal_value(self.value, "value"))


@dataclass(frozen=True, slots=True)
class MovingAverageObservation:
    """Moving-average metadata for one dated input value."""

    observation_date: date
    value: Decimal
    window: int
    moving_average: Decimal | None
    moving_average_available: bool
    is_above_moving_average: bool | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_date",
            _plain_date_value(self.observation_date, "observation_date"),
        )
        object.__setattr__(self, "value", _positive_decimal_value(self.value, "value"))
        object.__setattr__(self, "window", _window_value(self.window))
        object.__setattr__(
            self,
            "moving_average_available",
            _bool_value(
                self.moving_average_available,
                "moving_average_available",
            ),
        )

        if self.moving_average is None:
            if self.moving_average_available:
                raise ValidationError(
                    "moving_average_available must be false when moving_average is None."
                )
            if self.is_above_moving_average is not None:
                raise ValidationError(
                    "is_above_moving_average must be None when moving_average is None."
                )
            return

        object.__setattr__(
            self,
            "moving_average",
            _positive_decimal_value(self.moving_average, "moving_average"),
        )
        if not self.moving_average_available:
            raise ValidationError(
                "moving_average_available must be true when moving_average is present."
            )
        object.__setattr__(
            self,
            "is_above_moving_average",
            _bool_value(
                self.is_above_moving_average,
                "is_above_moving_average",
            ),
        )


def build_simple_moving_average_observations(
    observations: Iterable[MovingAverageInput],
    *,
    window: int,
) -> tuple[MovingAverageObservation, ...]:
    """Build trailing simple moving-average metadata from ordered inputs."""

    checked_window = _window_value(window)
    checked_observations = _observation_tuple(observations)
    values = tuple(observation.value for observation in checked_observations)
    trailing_total = _ZERO
    moving_average_observations: list[MovingAverageObservation] = []

    for index, observation in enumerate(checked_observations):
        trailing_total += observation.value
        if index >= checked_window:
            trailing_total -= values[index - checked_window]

        moving_average: Decimal | None = None
        moving_average_available = False
        is_above_moving_average: bool | None = None

        if index >= checked_window - 1:
            moving_average = trailing_total / Decimal(checked_window)
            moving_average_available = True
            is_above_moving_average = observation.value > moving_average

        moving_average_observations.append(
            MovingAverageObservation(
                observation_date=observation.observation_date,
                value=observation.value,
                window=checked_window,
                moving_average=moving_average,
                moving_average_available=moving_average_available,
                is_above_moving_average=is_above_moving_average,
            )
        )

    return tuple(moving_average_observations)


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


def _window_value(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError("window must be a positive integer.")
    if value <= 0:
        raise ValidationError("window must be a positive integer.")

    return value


def _bool_value(value: bool | None, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")

    return value


def _observation_tuple(
    observations: Iterable[MovingAverageInput],
) -> tuple[MovingAverageInput, ...]:
    try:
        observation_items = tuple(observations)
    except TypeError as exc:
        raise ValidationError(
            "observations must be an iterable of MovingAverageInput."
        ) from exc

    if not observation_items:
        raise ValidationError("observations must contain at least one MovingAverageInput.")

    seen_dates: set[date] = set()
    previous_date: date | None = None
    for observation in observation_items:
        if not isinstance(observation, MovingAverageInput):
            raise ValidationError("observations must contain MovingAverageInput values.")
        if observation.observation_date in seen_dates:
            raise ValidationError("observations must not contain duplicate dates.")
        if previous_date is not None and observation.observation_date <= previous_date:
            raise ValidationError("observations must be strictly increasing by date.")

        seen_dates.add(observation.observation_date)
        previous_date = observation.observation_date

    return observation_items
