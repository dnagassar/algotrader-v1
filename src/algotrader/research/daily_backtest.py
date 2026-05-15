"""Minimal deterministic daily equity curve utilities."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.price_snapshot import (
    HistoricalPriceBar,
    HistoricalPriceSnapshot,
)

__all__ = [
    "DailyBacktestAssumptions",
    "DailyBacktestPoint",
    "DailyBacktestResult",
    "DailyExposure",
    "run_daily_backtest",
]


_BASIS_POINTS_DENOMINATOR = Decimal("10000")
_ONE = Decimal("1")
_ZERO = Decimal("0")
_BACKTEST_RESULT_FIELD_NAMES = (
    "symbol",
    "assumptions",
    "starting_equity",
    "ending_equity",
    "total_return",
    "max_drawdown",
    "exposure_ratio",
    "turnover",
    "points",
)
_ASSUMPTION_FIELD_NAMES = ("initial_equity", "fee_bps", "slippage_bps")
_POINT_FIELD_NAMES = (
    "date",
    "adjusted_close",
    "exposure",
    "asset_return",
    "strategy_return_before_costs",
    "transaction_cost",
    "strategy_return_after_costs",
    "equity",
)


@dataclass(frozen=True, slots=True)
class DailyBacktestAssumptions:
    """Simple cost and starting equity assumptions for daily equity curves."""

    initial_equity: Decimal
    fee_bps: Decimal
    slippage_bps: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "initial_equity",
            _positive_decimal_value(self.initial_equity, "initial_equity"),
        )
        object.__setattr__(
            self,
            "fee_bps",
            _non_negative_decimal_value(self.fee_bps, "fee_bps"),
        )
        object.__setattr__(
            self,
            "slippage_bps",
            _non_negative_decimal_value(self.slippage_bps, "slippage_bps"),
        )


@dataclass(frozen=True, slots=True)
class DailyExposure:
    """Precomputed daily exposure for one snapshot date."""

    date: date
    exposure: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", _plain_date_value(self.date, "date"))
        object.__setattr__(
            self,
            "exposure",
            _exposure_value(self.exposure, "exposure"),
        )


@dataclass(frozen=True, slots=True)
class DailyBacktestPoint:
    """One deterministic daily equity curve point."""

    date: date
    adjusted_close: Decimal
    exposure: Decimal
    asset_return: Decimal
    strategy_return_before_costs: Decimal
    transaction_cost: Decimal
    strategy_return_after_costs: Decimal
    equity: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", _plain_date_value(self.date, "date"))
        object.__setattr__(
            self,
            "adjusted_close",
            _positive_decimal_value(self.adjusted_close, "adjusted_close"),
        )
        object.__setattr__(
            self,
            "exposure",
            _exposure_value(self.exposure, "exposure"),
        )
        object.__setattr__(
            self,
            "asset_return",
            _finite_decimal_value(self.asset_return, "asset_return"),
        )
        object.__setattr__(
            self,
            "strategy_return_before_costs",
            _finite_decimal_value(
                self.strategy_return_before_costs,
                "strategy_return_before_costs",
            ),
        )
        object.__setattr__(
            self,
            "transaction_cost",
            _non_negative_decimal_value(self.transaction_cost, "transaction_cost"),
        )
        object.__setattr__(
            self,
            "strategy_return_after_costs",
            _finite_decimal_value(
                self.strategy_return_after_costs,
                "strategy_return_after_costs",
            ),
        )
        object.__setattr__(self, "equity", _positive_decimal_value(self.equity, "equity"))


@dataclass(frozen=True, slots=True)
class DailyBacktestResult:
    """Deterministic daily equity curve and descriptive metrics."""

    symbol: str
    assumptions: DailyBacktestAssumptions
    points: tuple[DailyBacktestPoint, ...]

    def __post_init__(self) -> None:
        symbol = _symbol_value(self.symbol, "symbol")
        assumptions = _assumptions_value(self.assumptions)
        points = _point_tuple(self.points)
        _validate_point_dates(points)

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "points", points)

    @property
    def starting_equity(self) -> Decimal:
        return self.assumptions.initial_equity

    @property
    def ending_equity(self) -> Decimal:
        return self.points[-1].equity

    @property
    def total_return(self) -> Decimal:
        return (self.ending_equity / self.starting_equity) - _ONE

    @property
    def max_drawdown(self) -> Decimal:
        peak = self.starting_equity
        worst_drawdown = _ZERO

        for point in self.points:
            if point.equity > peak:
                peak = point.equity
            drawdown = (point.equity / peak) - _ONE
            if drawdown < worst_drawdown:
                worst_drawdown = drawdown

        return -worst_drawdown

    @property
    def exposure_ratio(self) -> Decimal:
        return sum((point.exposure for point in self.points), _ZERO) / Decimal(
            len(self.points)
        )

    @property
    def turnover(self) -> Decimal:
        previous_exposure = _ZERO
        total_turnover = _ZERO

        for point in self.points:
            total_turnover += abs(point.exposure - previous_exposure)
            previous_exposure = point.exposure

        return total_turnover

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive result values."""
        values: dict[str, object] = {}

        for field_name in _BACKTEST_RESULT_FIELD_NAMES:
            if field_name == "assumptions":
                values[field_name] = _assumptions_to_dict(self.assumptions)
            elif field_name == "points":
                values[field_name] = [_point_to_dict(point) for point in self.points]
            elif field_name == "symbol":
                values[field_name] = self.symbol
            else:
                values[field_name] = _decimal_to_string(getattr(self, field_name))

        return values


def run_daily_backtest(
    snapshot: HistoricalPriceSnapshot,
    exposures: Iterable[DailyExposure],
    assumptions: DailyBacktestAssumptions,
) -> DailyBacktestResult:
    """Build a deterministic equity curve from prices and precomputed exposure."""
    checked_snapshot = _snapshot_value(snapshot)
    exposure_items = _exposure_tuple(exposures)
    checked_assumptions = _assumptions_value(assumptions)
    _validate_exposure_alignment(checked_snapshot, exposure_items)

    cost_rate = (
        checked_assumptions.fee_bps + checked_assumptions.slippage_bps
    ) / _BASIS_POINTS_DENOMINATOR
    equity = checked_assumptions.initial_equity
    previous_adjusted_close: Decimal | None = None
    previous_exposure = _ZERO
    points: list[DailyBacktestPoint] = []

    for bar, exposure_item in zip(checked_snapshot.bars, exposure_items):
        adjusted_close = bar.adjusted_close
        if previous_adjusted_close is None:
            asset_return = _ZERO
        else:
            asset_return = (adjusted_close / previous_adjusted_close) - _ONE

        current_exposure = exposure_item.exposure
        strategy_return_before_costs = previous_exposure * asset_return
        transaction_cost = abs(current_exposure - previous_exposure) * cost_rate
        strategy_return_after_costs = (
            strategy_return_before_costs - transaction_cost
        )
        equity = equity * (_ONE + strategy_return_after_costs)

        points.append(
            DailyBacktestPoint(
                date=bar.date,
                adjusted_close=adjusted_close,
                exposure=current_exposure,
                asset_return=asset_return,
                strategy_return_before_costs=strategy_return_before_costs,
                transaction_cost=transaction_cost,
                strategy_return_after_costs=strategy_return_after_costs,
                equity=equity,
            )
        )

        previous_adjusted_close = adjusted_close
        previous_exposure = current_exposure

    return DailyBacktestResult(
        symbol=checked_snapshot.symbol,
        assumptions=checked_assumptions,
        points=tuple(points),
    )


def _snapshot_value(value: HistoricalPriceSnapshot) -> HistoricalPriceSnapshot:
    if not isinstance(value, HistoricalPriceSnapshot):
        raise ValidationError("snapshot must be a HistoricalPriceSnapshot.")
    if not isinstance(value.bars, tuple):
        raise ValidationError("snapshot bars must be an immutable tuple.")
    if not value.bars:
        raise ValidationError("snapshot bars must contain HistoricalPriceBar values.")

    _symbol_value(value.symbol, "snapshot symbol")
    previous_date: date | None = None
    for bar in value.bars:
        if not isinstance(bar, HistoricalPriceBar):
            raise ValidationError("snapshot bars must contain HistoricalPriceBar values.")
        if bar.symbol != value.symbol:
            raise ValidationError("snapshot bars must match the snapshot symbol.")
        _plain_date_value(bar.date, "snapshot bar date")
        _positive_decimal_value(bar.adjusted_close, "snapshot adjusted_close")
        if previous_date is not None and bar.date <= previous_date:
            raise ValidationError("snapshot bars must be strictly increasing by date.")
        previous_date = bar.date

    return value


def _assumptions_value(
    value: DailyBacktestAssumptions,
) -> DailyBacktestAssumptions:
    if not isinstance(value, DailyBacktestAssumptions):
        raise ValidationError("assumptions must be DailyBacktestAssumptions.")

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


def _finite_decimal_value(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _positive_decimal_value(value: Decimal, field_name: str) -> Decimal:
    checked_value = _finite_decimal_value(value, field_name)
    if checked_value <= _ZERO:
        raise ValidationError(f"{field_name} must be greater than zero.")

    return checked_value


def _non_negative_decimal_value(value: Decimal, field_name: str) -> Decimal:
    checked_value = _finite_decimal_value(value, field_name)
    if checked_value < _ZERO:
        raise ValidationError(f"{field_name} must be zero or greater.")

    return checked_value


def _exposure_value(value: Decimal, field_name: str) -> Decimal:
    checked_value = _finite_decimal_value(value, field_name)
    if checked_value < _ZERO or checked_value > _ONE:
        raise ValidationError(f"{field_name} must be between 0 and 1 inclusive.")

    return checked_value


def _exposure_tuple(
    exposures: Iterable[DailyExposure],
) -> tuple[DailyExposure, ...]:
    if isinstance(exposures, (str, bytes)):
        raise ValidationError("exposures must be an iterable of DailyExposure values.")

    try:
        exposure_items = tuple(exposures)
    except TypeError as exc:
        raise ValidationError(
            "exposures must be an iterable of DailyExposure values."
        ) from exc

    if not exposure_items:
        raise ValidationError("exposures must contain at least one DailyExposure.")

    for exposure_item in exposure_items:
        if not isinstance(exposure_item, DailyExposure):
            raise ValidationError("exposures must contain DailyExposure values.")

    _validate_exposure_dates(exposure_items)
    return exposure_items


def _validate_exposure_dates(
    exposures: tuple[DailyExposure, ...],
) -> None:
    seen_dates: set[date] = set()
    previous_date: date | None = None

    for exposure_item in exposures:
        if exposure_item.date in seen_dates:
            raise ValidationError("exposures must not contain duplicate dates.")
        if previous_date is not None and exposure_item.date <= previous_date:
            raise ValidationError("exposures must be strictly increasing by date.")

        seen_dates.add(exposure_item.date)
        previous_date = exposure_item.date


def _validate_exposure_alignment(
    snapshot: HistoricalPriceSnapshot,
    exposures: tuple[DailyExposure, ...],
) -> None:
    snapshot_dates = tuple(bar.date for bar in snapshot.bars)
    exposure_dates = tuple(exposure_item.date for exposure_item in exposures)
    if exposure_dates == snapshot_dates:
        return

    snapshot_date_set = set(snapshot_dates)
    exposure_date_set = set(exposure_dates)
    missing_dates = tuple(
        snapshot_date for snapshot_date in snapshot_dates if snapshot_date not in exposure_date_set
    )
    extra_dates = tuple(
        exposure_date for exposure_date in exposure_dates if exposure_date not in snapshot_date_set
    )

    if missing_dates:
        missing = ", ".join(value.isoformat() for value in missing_dates)
        raise ValidationError(f"exposures are missing snapshot date(s): {missing}.")
    if extra_dates:
        extra = ", ".join(value.isoformat() for value in extra_dates)
        raise ValidationError(f"exposures include date(s) outside snapshot: {extra}.")

    raise ValidationError("exposures must align exactly with snapshot bar dates.")


def _point_tuple(
    points: Iterable[DailyBacktestPoint],
) -> tuple[DailyBacktestPoint, ...]:
    try:
        point_items = tuple(points)
    except TypeError as exc:
        raise ValidationError(
            "points must be an iterable of DailyBacktestPoint values."
        ) from exc

    if not point_items:
        raise ValidationError("points must contain at least one DailyBacktestPoint.")

    for point in point_items:
        if not isinstance(point, DailyBacktestPoint):
            raise ValidationError("points must contain DailyBacktestPoint values.")

    return point_items


def _validate_point_dates(points: tuple[DailyBacktestPoint, ...]) -> None:
    previous_date: date | None = None

    for point in points:
        if previous_date is not None and point.date <= previous_date:
            raise ValidationError("points must be strictly increasing by date.")

        previous_date = point.date


def _assumptions_to_dict(
    assumptions: DailyBacktestAssumptions,
) -> dict[str, str]:
    return {
        field_name: _decimal_to_string(getattr(assumptions, field_name))
        for field_name in _ASSUMPTION_FIELD_NAMES
    }


def _point_to_dict(point: DailyBacktestPoint) -> dict[str, str]:
    values: dict[str, str] = {}

    for field_name in _POINT_FIELD_NAMES:
        value = getattr(point, field_name)
        if field_name == "date":
            values[field_name] = _date_to_string(value)
        else:
            values[field_name] = _decimal_to_string(value)

    return values


def _date_to_string(value: date) -> str:
    return _plain_date_value(value, "date").isoformat()


def _decimal_to_string(value: Decimal) -> str:
    return str(_finite_decimal_value(value, "decimal"))
