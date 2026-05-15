"""Synthetic-only as-of replay availability mechanics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.errors import ValidationError

__all__ = [
    "AsofObservation",
    "iter_asof_available",
    "next_available_asof_date",
]


@dataclass(frozen=True, slots=True)
class AsofObservation:
    """Synthetic observation with an explicit availability date."""

    observation_date: date
    available_after: date

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_date",
            _plain_date(self.observation_date, "observation_date"),
        )
        object.__setattr__(
            self,
            "available_after",
            _plain_date(self.available_after, "available_after"),
        )
        if self.available_after < self.observation_date:
            raise ValidationError(
                "available_after must be on or after observation_date."
            )


def iter_asof_available(
    observations: Iterable[AsofObservation],
    asof_date: date,
) -> tuple[AsofObservation, ...]:
    """Return synthetic observations available on or before ``asof_date``."""

    asof = _plain_date(asof_date, "asof_date")
    observation_items = _observation_sequence(observations, allow_empty=True)

    return tuple(
        observation
        for observation in observation_items
        if observation.available_after <= asof
    )


def next_available_asof_date(observations: Iterable[AsofObservation]) -> date:
    """Return the earliest synthetic availability date in ``observations``."""

    observation_items = _observation_sequence(observations, allow_empty=False)

    return min(observation.available_after for observation in observation_items)


def _plain_date(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")

    return value


def _observation_sequence(
    observations: Iterable[AsofObservation],
    *,
    allow_empty: bool,
) -> tuple[AsofObservation, ...]:
    if isinstance(observations, (str, bytes)):
        raise ValidationError("observations must be an iterable of AsofObservation.")

    try:
        items = tuple(observations)
    except TypeError as exc:
        raise ValidationError(
            "observations must be an iterable of AsofObservation."
        ) from exc

    if not items and not allow_empty:
        raise ValidationError("observations must contain at least one observation.")

    for index, observation in enumerate(items):
        if not isinstance(observation, AsofObservation):
            raise ValidationError(
                f"observations[{index}] must be an AsofObservation."
            )

    for previous, current in zip(items, items[1:]):
        if current.observation_date == previous.observation_date:
            raise ValidationError("observations must not contain duplicate dates.")
        if current.observation_date < previous.observation_date:
            raise ValidationError(
                "observations must be ordered by increasing observation_date."
            )

    return items
