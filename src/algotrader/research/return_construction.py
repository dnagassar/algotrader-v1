"""Synthetic-only return construction and lagged timing mechanics."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from algotrader.errors import ValidationError

__all__ = [
    "close_to_close_returns",
    "lagged_signal_action_pairs",
    "simple_return",
]

LaggedSignalActionPair = tuple[date, date]


def simple_return(previous_value: Decimal, current_value: Decimal) -> Decimal:
    """Return the arithmetic simple return between two synthetic Decimal values."""

    previous = _decimal_value(previous_value, "previous_value")
    current = _decimal_value(current_value, "current_value")
    _positive_prior_value(previous, "previous_value")

    return (current - previous) / previous


def close_to_close_returns(values: Sequence[Decimal]) -> tuple[Decimal, ...]:
    """Build arithmetic close-to-close returns from synthetic Decimal values."""

    value_items = _decimal_sequence(values, "values", minimum_length=2)

    return tuple(
        simple_return(previous_value, current_value)
        for previous_value, current_value in zip(value_items, value_items[1:])
    )


def lagged_signal_action_pairs(
    observation_dates: Sequence[date],
    lag_days: int = 1,
) -> tuple[LaggedSignalActionPair, ...]:
    """Pair each synthetic observation date with its lagged action date."""

    if not isinstance(lag_days, int) or isinstance(lag_days, bool):
        raise ValidationError("lag_days must be an integer.")
    if lag_days < 0:
        raise ValidationError("lag_days must be zero or greater.")

    dates = _date_sequence(observation_dates, "observation_dates")
    lag = timedelta(days=lag_days)

    return tuple((observation_date, observation_date + lag) for observation_date in dates)


def _decimal_sequence(
    values: Sequence[Decimal],
    field_name: str,
    minimum_length: int,
) -> tuple[Decimal, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError(f"{field_name} must be a sequence of Decimal values.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be a sequence of Decimal values."
        ) from exc

    if len(items) < minimum_length:
        raise ValidationError(
            f"{field_name} must contain at least {minimum_length} Decimal values."
        )

    return tuple(
        _decimal_value(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )


def _decimal_value(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal.")

    return value


def _positive_prior_value(value: Decimal, field_name: str) -> None:
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")


def _date_sequence(values: Sequence[date], field_name: str) -> tuple[date, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError(f"{field_name} must be a sequence of dates.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be a sequence of dates.") from exc

    if not items:
        raise ValidationError(f"{field_name} must contain at least one date.")

    for index, value in enumerate(items):
        if type(value) is not date:
            raise ValidationError(f"{field_name}[{index}] must be a date.")

    for previous_date, current_date in zip(items, items[1:]):
        if current_date <= previous_date:
            raise ValidationError(f"{field_name} must be strictly increasing.")

    return items
