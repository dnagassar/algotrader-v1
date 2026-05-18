"""Research-only cumulative return path metadata from exposure returns."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.exposure_returns import ExposureReturnObservation

__all__ = [
    "CumulativeReturnObservation",
    "build_cumulative_return_path",
]

_ONE = Decimal("1")
_ZERO = Decimal("0")
_MIN_SIMPLE_RETURN = Decimal("-1")
_INITIAL_BASELINE_REASON = "initial_cumulative_return_baseline"
_COMPOUNDED_REASON = "return_compounded"
_RETURN_UNAVAILABLE_REASON = "return_unavailable_cumulative_return_preserved"


@dataclass(frozen=True, slots=True)
class CumulativeReturnObservation:
    """Cumulative return metadata for one exposure-applied return row."""

    observation_date: date
    asset_return: Decimal | None
    exposure_return: Decimal | None
    asset_cumulative_return: Decimal
    exposure_cumulative_return: Decimal
    return_available: bool
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_date",
            _plain_date_value(self.observation_date, "observation_date"),
        )
        object.__setattr__(
            self,
            "return_available",
            _bool_value(self.return_available, "return_available"),
        )
        object.__setattr__(
            self,
            "asset_cumulative_return",
            _finite_decimal_value(
                self.asset_cumulative_return,
                "asset_cumulative_return",
            ),
        )
        object.__setattr__(
            self,
            "exposure_cumulative_return",
            _finite_decimal_value(
                self.exposure_cumulative_return,
                "exposure_cumulative_return",
            ),
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
            _simple_return_value(self.asset_return, "asset_return"),
        )
        object.__setattr__(
            self,
            "exposure_return",
            _simple_return_value(self.exposure_return, "exposure_return"),
        )


def build_cumulative_return_path(
    returns: Iterable[ExposureReturnObservation],
) -> tuple[CumulativeReturnObservation, ...]:
    """Build cumulative return metadata from ordered exposure-return rows."""

    checked_returns = _return_tuple(returns)
    path: list[CumulativeReturnObservation] = []
    prior_asset_cumulative_return = _ZERO
    prior_exposure_cumulative_return = _ZERO

    for index, return_row in enumerate(checked_returns):
        asset_cumulative_return = prior_asset_cumulative_return
        exposure_cumulative_return = prior_exposure_cumulative_return
        reason = _RETURN_UNAVAILABLE_REASON

        if index == 0:
            reason = _INITIAL_BASELINE_REASON
        elif return_row.return_available:
            asset_cumulative_return = (
                (_ONE + prior_asset_cumulative_return)
                * (_ONE + return_row.asset_return)
                - _ONE
            )
            exposure_cumulative_return = (
                (_ONE + prior_exposure_cumulative_return)
                * (_ONE + return_row.exposure_return)
                - _ONE
            )
            reason = _COMPOUNDED_REASON

        path.append(
            CumulativeReturnObservation(
                observation_date=return_row.observation_date,
                asset_return=return_row.asset_return,
                exposure_return=return_row.exposure_return,
                asset_cumulative_return=asset_cumulative_return,
                exposure_cumulative_return=exposure_cumulative_return,
                return_available=return_row.return_available,
                reason=reason,
            )
        )
        prior_asset_cumulative_return = asset_cumulative_return
        prior_exposure_cumulative_return = exposure_cumulative_return

    return tuple(path)


def _return_tuple(
    returns: Iterable[ExposureReturnObservation],
) -> tuple[ExposureReturnObservation, ...]:
    try:
        return_items = tuple(returns)
    except TypeError as exc:
        raise ValidationError(
            "returns must be an iterable of ExposureReturnObservation."
        ) from exc

    if not return_items:
        raise ValidationError(
            "returns must contain at least one ExposureReturnObservation."
        )

    seen_dates: set[date] = set()
    previous_date: date | None = None

    for return_row in return_items:
        if not isinstance(return_row, ExposureReturnObservation):
            raise ValidationError(
                "returns must contain ExposureReturnObservation values."
            )

        observation_date = _plain_date_value(
            return_row.observation_date,
            "observation_date",
        )
        if observation_date in seen_dates:
            raise ValidationError("returns must not contain duplicate dates.")
        if previous_date is not None and observation_date <= previous_date:
            raise ValidationError("returns must be strictly increasing by date.")

        _positive_decimal_value(return_row.value, "value")
        _exposure_value(return_row.current_exposure, "current_exposure")
        _bool_value(return_row.return_available, "return_available")
        _reason_value(return_row.reason)
        if return_row.return_available:
            asset_return = _simple_return_value(
                return_row.asset_return,
                "asset_return",
            )
            exposure_return = _simple_return_value(
                return_row.exposure_return,
                "exposure_return",
            )
            expected_exposure_return = (
                _ZERO if return_row.current_exposure == 0 else asset_return
            )
            if exposure_return != expected_exposure_return:
                raise ValidationError(
                    "exposure_return must match asset_return applied to current_exposure."
                )
        else:
            if return_row.asset_return is not None:
                raise ValidationError(
                    "asset_return must be None when return_available is false."
                )
            if return_row.exposure_return is not None:
                raise ValidationError(
                    "exposure_return must be None when return_available is false."
                )

        seen_dates.add(observation_date)
        previous_date = observation_date

    return return_items


def _plain_date_value(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def _positive_decimal_value(value: Decimal, field_name: str) -> Decimal:
    checked_value = _finite_decimal_value(value, field_name)
    if checked_value <= _ZERO:
        raise ValidationError(f"{field_name} must be greater than zero.")

    return checked_value


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
