"""Deterministic research-only replay packages for moving-average mechanics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import TypeVar

from algotrader.errors import ValidationError
from algotrader.research.cumulative_return_summary import (
    CumulativeReturnPathSummary,
    summarize_cumulative_return_path,
)
from algotrader.research.cumulative_returns import (
    CumulativeReturnObservation,
    build_cumulative_return_path,
)
from algotrader.research.exposure_returns import (
    ExposureReturnObservation,
    build_exposure_applied_returns,
)
from algotrader.research.moving_average import (
    MovingAverageInput,
    MovingAverageObservation,
    build_simple_moving_average_observations,
)
from algotrader.research.moving_average_exposure import (
    MovingAverageExposureState,
    build_previous_exposure_states,
)

__all__ = [
    "MovingAverageReplayPackage",
    "build_moving_average_replay_package",
]

_DEFAULT_LIMITATIONS = (
    "research-only replay package of already-built moving-average mechanics",
    "uses only synthetic inputs and deterministic mechanics outputs",
    "does not validate a strategy, define a signal, evaluate performance, or authorize trading",
)

_REQUIRED_NON_CLAIMS = (
    "not validated evidence",
    "not a strategy approval",
    "not a trading recommendation",
    "not an approved signal",
    "not paper/live trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
)

_DEFAULT_NON_CLAIMS = (
    *_REQUIRED_NON_CLAIMS,
    "exposure is a 0/1 research indicator and not allocation, target weight, position size, or portfolio instruction",
)

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class MovingAverageReplayPackage:
    """Immutable metadata package for one synthetic moving-average replay."""

    replay_id: str
    as_of_date: date
    window: int
    inputs: tuple[MovingAverageInput, ...]
    moving_average_observations: tuple[MovingAverageObservation, ...]
    exposure_states: tuple[MovingAverageExposureState, ...]
    exposure_returns: tuple[ExposureReturnObservation, ...]
    cumulative_path: tuple[CumulativeReturnObservation, ...]
    summary: CumulativeReturnPathSummary
    limitations: tuple[str, ...] = _DEFAULT_LIMITATIONS
    non_claims: tuple[str, ...] = _DEFAULT_NON_CLAIMS

    def __post_init__(self) -> None:
        object.__setattr__(self, "replay_id", _replay_id_value(self.replay_id))
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date_value(self.as_of_date, "as_of_date"),
        )
        object.__setattr__(self, "window", _window_value(self.window))
        object.__setattr__(
            self,
            "inputs",
            _object_tuple(self.inputs, "inputs", MovingAverageInput),
        )
        object.__setattr__(
            self,
            "moving_average_observations",
            _object_tuple(
                self.moving_average_observations,
                "moving_average_observations",
                MovingAverageObservation,
            ),
        )
        object.__setattr__(
            self,
            "exposure_states",
            _object_tuple(
                self.exposure_states,
                "exposure_states",
                MovingAverageExposureState,
            ),
        )
        object.__setattr__(
            self,
            "exposure_returns",
            _object_tuple(
                self.exposure_returns,
                "exposure_returns",
                ExposureReturnObservation,
            ),
        )
        object.__setattr__(
            self,
            "cumulative_path",
            _object_tuple(
                self.cumulative_path,
                "cumulative_path",
                CumulativeReturnObservation,
            ),
        )
        object.__setattr__(self, "summary", _summary_value(self.summary))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple_value(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims_value(self.non_claims),
        )

        _validate_package_alignment(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive replay metadata."""

        return {
            "replay_id": self.replay_id,
            "as_of_date": self.as_of_date.isoformat(),
            "window": self.window,
            "inputs": [_moving_average_input_to_dict(item) for item in self.inputs],
            "moving_average_observations": [
                _moving_average_observation_to_dict(item)
                for item in self.moving_average_observations
            ],
            "exposure_states": [
                _exposure_state_to_dict(item) for item in self.exposure_states
            ],
            "exposure_returns": [
                _exposure_return_to_dict(item) for item in self.exposure_returns
            ],
            "cumulative_path": [
                _cumulative_observation_to_dict(item) for item in self.cumulative_path
            ],
            "summary": self.summary.to_dict(),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_moving_average_replay_package(
    *,
    replay_id: str,
    as_of_date: date,
    inputs: Iterable[MovingAverageInput],
    window: int,
) -> MovingAverageReplayPackage:
    """Build a replay package by composing the existing deterministic kernels."""

    checked_replay_id = _replay_id_value(replay_id)
    checked_as_of_date = _plain_date_value(as_of_date, "as_of_date")
    input_items = _input_tuple_for_builder(inputs)
    moving_average_observations = build_simple_moving_average_observations(
        input_items,
        window=window,
    )
    exposure_states = build_previous_exposure_states(moving_average_observations)
    exposure_returns = build_exposure_applied_returns(input_items, exposure_states)
    cumulative_path = build_cumulative_return_path(exposure_returns)
    summary = summarize_cumulative_return_path(cumulative_path)

    return MovingAverageReplayPackage(
        replay_id=checked_replay_id,
        as_of_date=checked_as_of_date,
        window=window,
        inputs=input_items,
        moving_average_observations=moving_average_observations,
        exposure_states=exposure_states,
        exposure_returns=exposure_returns,
        cumulative_path=cumulative_path,
        summary=summary,
        limitations=_DEFAULT_LIMITATIONS,
        non_claims=_DEFAULT_NON_CLAIMS,
    )


def _validate_package_alignment(package: MovingAverageReplayPackage) -> None:
    _validate_matching_lengths(package)
    _validate_matching_dates(package)
    _validate_windows(package)
    _validate_summary_dates(package)
    _validate_chain_outputs(package)


def _validate_matching_lengths(package: MovingAverageReplayPackage) -> None:
    expected_length = len(package.inputs)
    lengths = (
        len(package.moving_average_observations),
        len(package.exposure_states),
        len(package.exposure_returns),
        len(package.cumulative_path),
    )
    if any(length != expected_length for length in lengths):
        raise ValidationError("all replay sequence fields must have matching lengths.")
    if package.summary.observation_count != expected_length:
        raise ValidationError("summary observation_count must match replay length.")


def _validate_matching_dates(package: MovingAverageReplayPackage) -> None:
    input_dates = _dates_for(package.inputs, "inputs")
    ordered_dates = (
        _dates_for(
            package.moving_average_observations,
            "moving_average_observations",
        ),
        _dates_for(package.exposure_states, "exposure_states"),
        _dates_for(package.exposure_returns, "exposure_returns"),
        _dates_for(package.cumulative_path, "cumulative_path"),
    )
    if any(dates != input_dates for dates in ordered_dates):
        raise ValidationError(
            "all replay sequence fields must use matching ordered observation dates."
        )


def _validate_windows(package: MovingAverageReplayPackage) -> None:
    for observation in package.moving_average_observations:
        if _item_window(observation, "moving_average_observations") != package.window:
            raise ValidationError(
                "moving_average_observations must match package window."
            )

    for state in package.exposure_states:
        if _item_window(state, "exposure_states") != package.window:
            raise ValidationError("exposure_states must match package window.")


def _validate_summary_dates(package: MovingAverageReplayPackage) -> None:
    first_path_date = package.cumulative_path[0].observation_date
    last_path_date = package.cumulative_path[-1].observation_date
    if package.summary.first_observation_date != first_path_date:
        raise ValidationError(
            "summary first_observation_date must match cumulative path."
        )
    if package.summary.last_observation_date != last_path_date:
        raise ValidationError(
            "summary last_observation_date must match cumulative path."
        )


def _validate_chain_outputs(package: MovingAverageReplayPackage) -> None:
    try:
        expected_moving_average_observations = (
            build_simple_moving_average_observations(
                package.inputs,
                window=package.window,
            )
        )
        expected_exposure_states = build_previous_exposure_states(
            package.moving_average_observations
        )
        expected_exposure_returns = build_exposure_applied_returns(
            package.inputs,
            package.exposure_states,
        )
        expected_cumulative_path = build_cumulative_return_path(
            package.exposure_returns
        )
        expected_summary = summarize_cumulative_return_path(package.cumulative_path)
    except AttributeError as exc:
        raise ValidationError(
            "replay package contains malformed mechanics objects."
        ) from exc

    if package.moving_average_observations != expected_moving_average_observations:
        raise ValidationError(
            "moving_average_observations must match inputs and window."
        )
    if package.exposure_states != expected_exposure_states:
        raise ValidationError(
            "exposure_states must match moving_average_observations."
        )
    if package.exposure_returns != expected_exposure_returns:
        raise ValidationError("exposure_returns must match inputs and exposure_states.")
    if package.cumulative_path != expected_cumulative_path:
        raise ValidationError("cumulative_path must match exposure_returns.")
    if package.summary != expected_summary:
        raise ValidationError("summary must match cumulative_path.")


def _input_tuple_for_builder(
    inputs: Iterable[MovingAverageInput],
) -> tuple[MovingAverageInput, ...]:
    try:
        return tuple(inputs)
    except TypeError as exc:
        raise ValidationError(
            "inputs must be an iterable of MovingAverageInput."
        ) from exc


def _object_tuple(
    values: Iterable[_T],
    field_name: str,
    expected_type: type[_T],
) -> tuple[_T, ...]:
    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be a tuple of {expected_type.__name__} values."
        ) from exc

    if not items:
        raise ValidationError(f"{field_name} must contain at least one value.")

    for item in items:
        if not isinstance(item, expected_type):
            raise ValidationError(
                f"{field_name} must contain {expected_type.__name__} values."
            )

    return items


def _dates_for(values: Iterable[object], field_name: str) -> tuple[date, ...]:
    dates: list[date] = []
    for value in values:
        try:
            observation_date = value.observation_date
        except AttributeError as exc:
            raise ValidationError(
                f"{field_name} must contain dated observations."
            ) from exc
        dates.append(_plain_date_value(observation_date, "observation_date"))

    return tuple(dates)


def _item_window(value: object, field_name: str) -> int:
    try:
        item_window = value.window
    except AttributeError as exc:
        raise ValidationError(f"{field_name} must contain window metadata.") from exc

    return _window_value(item_window)


def _moving_average_input_to_dict(item: MovingAverageInput) -> dict[str, object]:
    return {
        "observation_date": item.observation_date.isoformat(),
        "value": str(item.value),
    }


def _moving_average_observation_to_dict(
    item: MovingAverageObservation,
) -> dict[str, object]:
    return {
        "observation_date": item.observation_date.isoformat(),
        "value": str(item.value),
        "window": item.window,
        "moving_average": _decimal_or_none_to_string(item.moving_average),
        "moving_average_available": item.moving_average_available,
        "is_above_moving_average": item.is_above_moving_average,
    }


def _exposure_state_to_dict(item: MovingAverageExposureState) -> dict[str, object]:
    return {
        "observation_date": item.observation_date.isoformat(),
        "window": item.window,
        "moving_average_available": item.moving_average_available,
        "is_above_moving_average": item.is_above_moving_average,
        "current_exposure": item.current_exposure,
        "next_exposure": item.next_exposure,
        "reason": item.reason,
    }


def _exposure_return_to_dict(item: ExposureReturnObservation) -> dict[str, object]:
    return {
        "observation_date": item.observation_date.isoformat(),
        "value": str(item.value),
        "current_exposure": item.current_exposure,
        "asset_return": _decimal_or_none_to_string(item.asset_return),
        "exposure_return": _decimal_or_none_to_string(item.exposure_return),
        "return_available": item.return_available,
        "reason": item.reason,
    }


def _cumulative_observation_to_dict(
    item: CumulativeReturnObservation,
) -> dict[str, object]:
    return {
        "observation_date": item.observation_date.isoformat(),
        "asset_return": _decimal_or_none_to_string(item.asset_return),
        "exposure_return": _decimal_or_none_to_string(item.exposure_return),
        "asset_cumulative_return": str(item.asset_cumulative_return),
        "exposure_cumulative_return": str(item.exposure_cumulative_return),
        "return_available": item.return_available,
        "reason": item.reason,
    }


def _decimal_or_none_to_string(value: object) -> str | None:
    if value is None:
        return None

    return str(value)


def _replay_id_value(value: str) -> str:
    if type(value) is not str:
        raise ValidationError("replay_id must be a non-empty string.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError("replay_id must be a non-empty string.")

    return normalized


def _plain_date_value(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def _window_value(value: int) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError("window must be a positive integer.")

    return value


def _summary_value(value: CumulativeReturnPathSummary) -> CumulativeReturnPathSummary:
    if not isinstance(value, CumulativeReturnPathSummary):
        raise ValidationError("summary must be a CumulativeReturnPathSummary.")

    return value


def _string_tuple_value(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ValidationError(f"{field_name} must be a tuple of non-empty strings.")

    normalized = tuple(_non_empty_string_value(value, field_name) for value in values)
    if not normalized:
        raise ValidationError(f"{field_name} must contain at least one string.")

    return normalized


def _required_non_claims_value(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = _string_tuple_value(values, "non_claims")
    missing = tuple(
        claim for claim in _REQUIRED_NON_CLAIMS if claim not in normalized
    )
    if missing:
        raise ValidationError("non_claims must include required replay non-claims.")

    return normalized


def _non_empty_string_value(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must contain non-empty strings.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must contain non-empty strings.")

    return normalized
