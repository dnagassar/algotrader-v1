"""Research-only exposure metadata from moving-average observations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.errors import ValidationError
from algotrader.research.moving_average import MovingAverageObservation

__all__ = [
    "MovingAverageExposureState",
    "build_previous_exposure_states",
]


@dataclass(frozen=True, slots=True)
class MovingAverageExposureState:
    """Previous-row exposure metadata for one moving-average observation."""

    observation_date: date
    window: int
    moving_average_available: bool
    is_above_moving_average: bool | None
    current_exposure: int
    next_exposure: int
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_date",
            _plain_date_value(self.observation_date, "observation_date"),
        )
        object.__setattr__(self, "window", _window_value(self.window))
        object.__setattr__(
            self,
            "moving_average_available",
            _bool_value(
                self.moving_average_available,
                "moving_average_available",
            ),
        )
        object.__setattr__(
            self,
            "is_above_moving_average",
            _optional_bool_value(
                self.is_above_moving_average,
                "is_above_moving_average",
            ),
        )
        object.__setattr__(
            self,
            "current_exposure",
            _exposure_value(self.current_exposure, "current_exposure"),
        )
        object.__setattr__(
            self,
            "next_exposure",
            _exposure_value(self.next_exposure, "next_exposure"),
        )
        object.__setattr__(self, "reason", _reason_value(self.reason))

        expected_next_exposure, _ = _next_exposure_metadata(
            moving_average_available=self.moving_average_available,
            is_above_moving_average=self.is_above_moving_average,
        )
        if self.next_exposure != expected_next_exposure:
            raise ValidationError(
                "next_exposure must match moving-average observation metadata."
            )


def build_previous_exposure_states(
    observations: Iterable[MovingAverageObservation],
) -> tuple[MovingAverageExposureState, ...]:
    """Build immutable previous-row exposure metadata from ordered observations."""

    checked_observations = _observation_tuple(observations)
    previous_next_exposure = 0
    states: list[MovingAverageExposureState] = []

    for observation in checked_observations:
        next_exposure, reason = _next_exposure_metadata(
            moving_average_available=observation.moving_average_available,
            is_above_moving_average=observation.is_above_moving_average,
        )
        states.append(
            MovingAverageExposureState(
                observation_date=observation.observation_date,
                window=observation.window,
                moving_average_available=observation.moving_average_available,
                is_above_moving_average=observation.is_above_moving_average,
                current_exposure=previous_next_exposure,
                next_exposure=next_exposure,
                reason=reason,
            )
        )
        previous_next_exposure = next_exposure

    return tuple(states)


def _next_exposure_metadata(
    *,
    moving_average_available: bool,
    is_above_moving_average: bool | None,
) -> tuple[int, str]:
    if not moving_average_available:
        return 0, "moving_average_unavailable"
    if is_above_moving_average is True:
        return 1, "above_moving_average"

    return 0, "not_above_moving_average"


def _observation_tuple(
    observations: Iterable[MovingAverageObservation],
) -> tuple[MovingAverageObservation, ...]:
    try:
        observation_items = tuple(observations)
    except TypeError as exc:
        raise ValidationError(
            "observations must be an iterable of MovingAverageObservation."
        ) from exc

    if not observation_items:
        raise ValidationError(
            "observations must contain at least one MovingAverageObservation."
        )

    seen_dates: set[date] = set()
    previous_date: date | None = None
    expected_window: int | None = None

    for observation in observation_items:
        if not isinstance(observation, MovingAverageObservation):
            raise ValidationError(
                "observations must contain MovingAverageObservation values."
            )
        if observation.observation_date in seen_dates:
            raise ValidationError("observations must not contain duplicate dates.")
        if previous_date is not None and observation.observation_date <= previous_date:
            raise ValidationError("observations must be strictly increasing by date.")
        if expected_window is None:
            expected_window = observation.window
        elif observation.window != expected_window:
            raise ValidationError("observations must use a single moving-average window.")

        seen_dates.add(observation.observation_date)
        previous_date = observation.observation_date

    return observation_items


def _plain_date_value(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def _window_value(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError("window must be a positive integer.")
    if value <= 0:
        raise ValidationError("window must be a positive integer.")

    return value


def _bool_value(value: bool, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")

    return value


def _optional_bool_value(value: bool | None, field_name: str) -> bool | None:
    if value is not None and type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool or None.")

    return value


def _exposure_value(value: int, field_name: str) -> int:
    if type(value) is not int or value not in (0, 1):
        raise ValidationError(f"{field_name} must be integer 0 or 1.")

    return value


def _reason_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("reason must be a non-empty string.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError("reason must be a non-empty string.")

    return normalized
