"""Deterministic SMA-200 exposure generation for research backtests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.daily_backtest import DailyExposure
from algotrader.research.price_snapshot import (
    HistoricalPriceBar,
    HistoricalPriceSnapshot,
)

__all__ = ["build_sma_200_daily_exposures"]


_SMA_200_WINDOW = 200
_ONE = Decimal("1")
_ZERO = Decimal("0")


def build_sma_200_daily_exposures(
    snapshot: HistoricalPriceSnapshot,
) -> tuple[DailyExposure, ...]:
    """Build precomputed daily exposure flags from adjusted close SMA-200."""
    checked_snapshot = _snapshot_value(snapshot)
    prices = tuple(
        _positive_decimal_value(bar.adjusted_close, "snapshot adjusted_close")
        for bar in checked_snapshot.bars
    )
    trailing_total = _ZERO
    exposures: list[DailyExposure] = []

    for index, (bar, adjusted_close) in enumerate(zip(checked_snapshot.bars, prices)):
        trailing_total += adjusted_close
        if index >= _SMA_200_WINDOW:
            trailing_total -= prices[index - _SMA_200_WINDOW]

        exposure_value = _ZERO
        if index >= _SMA_200_WINDOW - 1:
            sma = trailing_total / Decimal(_SMA_200_WINDOW)
            if adjusted_close > sma:
                exposure_value = _ONE

        exposures.append(DailyExposure(date=bar.date, exposure=exposure_value))

    return tuple(exposures)


def _snapshot_value(value: HistoricalPriceSnapshot) -> HistoricalPriceSnapshot:
    if not isinstance(value, HistoricalPriceSnapshot):
        raise ValidationError("snapshot must be a HistoricalPriceSnapshot.")
    if not isinstance(value.bars, tuple):
        raise ValidationError("snapshot bars must be an immutable tuple.")
    if not value.bars:
        raise ValidationError("snapshot bars must contain HistoricalPriceBar values.")

    _symbol_value(value.symbol, "snapshot symbol")
    seen_dates: set[date] = set()
    previous_date: date | None = None

    for bar in value.bars:
        if not isinstance(bar, HistoricalPriceBar):
            raise ValidationError("snapshot bars must contain HistoricalPriceBar values.")
        if bar.symbol != value.symbol:
            raise ValidationError("snapshot bars must match the snapshot symbol.")
        _plain_date_value(bar.date, "snapshot bar date")
        _positive_decimal_value(bar.adjusted_close, "snapshot adjusted_close")
        if bar.date in seen_dates:
            raise ValidationError("snapshot bars must not contain duplicate dates.")
        if previous_date is not None and bar.date <= previous_date:
            raise ValidationError("snapshot bars must be strictly increasing by date.")

        seen_dates.add(bar.date)
        previous_date = bar.date

    return value


def _symbol_value(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be an uppercase non-empty symbol.")

    normalized = value.strip().upper()
    if not normalized:
        raise ValidationError(f"{field_name} must be an uppercase non-empty symbol.")

    return normalized


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
