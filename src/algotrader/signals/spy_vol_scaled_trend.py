"""Deterministic SPY volatility-scaled trend preview signal evaluation."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from statistics import stdev

from algotrader.core.time import require_utc_datetime
from algotrader.core.types import Bar
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "SPY_VOL_SCALED_TREND_LABELS",
    "SPY_VOL_SCALED_TREND_POSTURES",
    "SPY_VOL_SCALED_TREND_STRATEGY_FAMILY",
    "SPY_VOL_SCALED_TREND_STRATEGY_ID",
    "SPYVolScaledTrendSignalConfig",
    "SPYVolScaledTrendSignalEvaluator",
    "SPYVolScaledTrendSignalResult",
    "evaluate_spy_vol_scaled_trend_signal",
]

SPY_VOL_SCALED_TREND_STRATEGY_ID = "spy_vol_scaled_trend_20d_fixed"
SPY_VOL_SCALED_TREND_STRATEGY_FAMILY = "trend_volatility_adjusted"
SPY_VOL_SCALED_TREND_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "paper_preview_quarantine",
    "preview_only",
    "not_live_authorized",
    "profit_claim=none",
    "accepted_adjusted_spy_daily_bars",
)
SPY_VOL_SCALED_TREND_POSTURES = (
    "trend_on_full_exposure",
    "trend_on_half_exposure_high_volatility",
    "trend_off_cash",
    "insufficient_history",
)

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HALF = Decimal("0.5")
_DEFAULT_SHORT_WINDOW = 50
_DEFAULT_LONG_WINDOW = 200
_DEFAULT_VOLATILITY_WINDOW = 20
_DEFAULT_HIGH_VOLATILITY_THRESHOLD = Decimal("0.25")
_ASSET_CLASS = "equity"
_TIMEFRAME = "daily"
_PROFIT_CLAIM = "none"
_NEXT_ACTION = "paper_preview_quarantine_only_no_broker_action"
_DEFAULT_LIMITATIONS = (
    "paper preview signal evaluation only",
    "not live authorized",
    "not a profitability claim",
    "not risk approval",
    "not execution authority",
    "no broker action performed",
    "no submit allowed",
    "preview-only quarantine; SMA50/200 remains the only paper mutation path",
)


@dataclass(frozen=True, slots=True)
class SPYVolScaledTrendSignalConfig:
    """Fixed v4.0/v4.1 SPY volatility-scaled SMA50/200 parameters."""

    as_of: datetime
    symbol: str = "SPY"
    short_window: int = _DEFAULT_SHORT_WINDOW
    long_window: int = _DEFAULT_LONG_WINDOW
    volatility_window: int = _DEFAULT_VOLATILITY_WINDOW
    high_volatility_threshold: Decimal | str = _DEFAULT_HIGH_VOLATILITY_THRESHOLD
    high_volatility_exposure: Decimal | str = _HALF
    asset_class: str = _ASSET_CLASS
    timeframe: str = _TIMEFRAME

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "symbol",
            _fixed_string(symbol_value(self.symbol), "SPY", "symbol"),
        )
        object.__setattr__(
            self,
            "short_window",
            _positive_int(self.short_window, "short_window"),
        )
        object.__setattr__(
            self,
            "long_window",
            _positive_int(self.long_window, "long_window"),
        )
        object.__setattr__(
            self,
            "volatility_window",
            _positive_int(self.volatility_window, "volatility_window"),
        )
        object.__setattr__(
            self,
            "high_volatility_threshold",
            _positive_decimal(
                self.high_volatility_threshold,
                "high_volatility_threshold",
            ),
        )
        object.__setattr__(
            self,
            "high_volatility_exposure",
            _exposure_decimal(
                self.high_volatility_exposure,
                "high_volatility_exposure",
            ),
        )
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(
            self,
            "timeframe",
            _fixed_string(self.timeframe, _TIMEFRAME, "timeframe"),
        )
        if self.short_window >= self.long_window:
            raise ValidationError("short_window must be less than long_window.")


@dataclass(frozen=True, slots=True)
class SPYVolScaledTrendSignalEvaluator:
    """Frozen evaluator object for the SPY paper-preview quarantine signal."""

    config: SPYVolScaledTrendSignalConfig

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", _config(self.config))

    def evaluate(self, bars: Iterable[Bar]) -> "SPYVolScaledTrendSignalResult":
        """Evaluate explicit accepted SPY daily bars using this evaluator config."""

        return evaluate_spy_vol_scaled_trend_signal(bars, self.config)


@dataclass(frozen=True, slots=True)
class SPYVolScaledTrendSignalResult:
    """Immutable SPY volatility-scaled trend preview result."""

    symbol: str
    asset_class: str
    strategy_id: str
    strategy_family: str
    timeframe: str
    as_of: datetime
    short_window: int
    long_window: int
    volatility_window: int
    high_volatility_threshold: Decimal
    high_volatility_exposure: Decimal
    total_bar_count: int
    usable_bar_count: int
    ignored_future_bar_count: int
    latest_close: Decimal | None
    short_sma: Decimal | None
    long_sma: Decimal | None
    latest_annualized_volatility: Decimal | None
    target_exposure: Decimal
    posture: str
    labels: tuple[str, ...]
    blockers: tuple[str, ...]
    profit_claim: str
    broker_action_performed: bool
    submit_allowed: bool
    next_action: str
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "symbol",
            _fixed_string(symbol_value(self.symbol), "SPY", "symbol"),
        )
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(
            self,
            "strategy_id",
            _fixed_string(
                self.strategy_id,
                SPY_VOL_SCALED_TREND_STRATEGY_ID,
                "strategy_id",
            ),
        )
        object.__setattr__(
            self,
            "strategy_family",
            _fixed_string(
                self.strategy_family,
                SPY_VOL_SCALED_TREND_STRATEGY_FAMILY,
                "strategy_family",
            ),
        )
        object.__setattr__(
            self,
            "timeframe",
            _fixed_string(self.timeframe, _TIMEFRAME, "timeframe"),
        )
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "short_window",
            _positive_int(self.short_window, "short_window"),
        )
        object.__setattr__(
            self,
            "long_window",
            _positive_int(self.long_window, "long_window"),
        )
        object.__setattr__(
            self,
            "volatility_window",
            _positive_int(self.volatility_window, "volatility_window"),
        )
        object.__setattr__(
            self,
            "high_volatility_threshold",
            _positive_decimal(
                self.high_volatility_threshold,
                "high_volatility_threshold",
            ),
        )
        object.__setattr__(
            self,
            "high_volatility_exposure",
            _exposure_decimal(
                self.high_volatility_exposure,
                "high_volatility_exposure",
            ),
        )
        object.__setattr__(
            self,
            "total_bar_count",
            _non_negative_int(self.total_bar_count, "total_bar_count"),
        )
        object.__setattr__(
            self,
            "usable_bar_count",
            _non_negative_int(self.usable_bar_count, "usable_bar_count"),
        )
        object.__setattr__(
            self,
            "ignored_future_bar_count",
            _non_negative_int(
                self.ignored_future_bar_count,
                "ignored_future_bar_count",
            ),
        )
        object.__setattr__(
            self,
            "latest_close",
            _optional_positive_decimal(self.latest_close, "latest_close"),
        )
        object.__setattr__(
            self,
            "short_sma",
            _optional_positive_decimal(self.short_sma, "short_sma"),
        )
        object.__setattr__(
            self,
            "long_sma",
            _optional_positive_decimal(self.long_sma, "long_sma"),
        )
        object.__setattr__(
            self,
            "latest_annualized_volatility",
            _optional_non_negative_decimal(
                self.latest_annualized_volatility,
                "latest_annualized_volatility",
            ),
        )
        object.__setattr__(
            self,
            "target_exposure",
            _exposure_decimal(self.target_exposure, "target_exposure"),
        )
        object.__setattr__(self, "posture", _posture(self.posture))
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                SPY_VOL_SCALED_TREND_LABELS,
                "labels",
            ),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "profit_claim",
            _fixed_string(self.profit_claim, _PROFIT_CLAIM, "profit_claim"),
        )
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(self.broker_action_performed, "broker_action_performed"),
        )
        object.__setattr__(
            self,
            "submit_allowed",
            _false_bool(self.submit_allowed, "submit_allowed"),
        )
        object.__setattr__(
            self,
            "next_action",
            _fixed_string(self.next_action, _NEXT_ACTION, "next_action"),
        )
        object.__setattr__(
            self,
            "limitations",
            _fixed_string_tuple(self.limitations, _DEFAULT_LIMITATIONS, "limitations"),
        )
        _validate_result_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only preview signal metadata."""

        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "strategy_id": self.strategy_id,
            "strategy_family": self.strategy_family,
            "timeframe": self.timeframe,
            "as_of": self.as_of.isoformat(),
            "short_window": self.short_window,
            "long_window": self.long_window,
            "volatility_window": self.volatility_window,
            "high_volatility_threshold": _decimal_text(
                self.high_volatility_threshold
            ),
            "high_volatility_exposure": _decimal_text(self.high_volatility_exposure),
            "total_bar_count": self.total_bar_count,
            "usable_bar_count": self.usable_bar_count,
            "ignored_future_bar_count": self.ignored_future_bar_count,
            "latest_close": _decimal_text(self.latest_close),
            "short_sma": _decimal_text(self.short_sma),
            "long_sma": _decimal_text(self.long_sma),
            "latest_annualized_volatility": _decimal_text(
                self.latest_annualized_volatility
            ),
            "target_exposure": _decimal_text(self.target_exposure),
            "posture": self.posture,
            "labels": list(self.labels),
            "blockers": list(self.blockers),
            "profit_claim": self.profit_claim,
            "broker_action_performed": self.broker_action_performed,
            "submit_allowed": self.submit_allowed,
            "next_action": self.next_action,
            "limitations": list(self.limitations),
        }


def evaluate_spy_vol_scaled_trend_signal(
    bars: Iterable[Bar],
    config: SPYVolScaledTrendSignalConfig,
) -> SPYVolScaledTrendSignalResult:
    """Evaluate the fixed SPY volatility-scaled trend preview posture."""

    checked_config = _config(config)
    checked_bars = _bar_tuple(bars, checked_config.symbol)
    ordered_bars = tuple(sorted(checked_bars, key=lambda bar: bar.timestamp))
    usable_bars = tuple(
        bar for bar in ordered_bars if bar.timestamp <= checked_config.as_of
    )
    latest_close = usable_bars[-1].close if usable_bars else None
    short_sma = _window_sma(usable_bars, checked_config.short_window)
    long_sma = _window_sma(usable_bars, checked_config.long_window)
    latest_volatility = _latest_annualized_volatility(
        usable_bars,
        checked_config.volatility_window,
    )
    ignored_future_bar_count = len(ordered_bars) - len(usable_bars)

    if long_sma is None or short_sma is None or latest_volatility is None:
        posture = "insufficient_history"
        target_exposure = _ZERO
        blockers = ("insufficient_history",)
    elif short_sma <= long_sma:
        posture = "trend_off_cash"
        target_exposure = _ZERO
        blockers = ()
    elif latest_volatility > checked_config.high_volatility_threshold:
        posture = "trend_on_half_exposure_high_volatility"
        target_exposure = checked_config.high_volatility_exposure
        blockers = ()
    else:
        posture = "trend_on_full_exposure"
        target_exposure = _ONE
        blockers = ()

    return SPYVolScaledTrendSignalResult(
        symbol=checked_config.symbol,
        asset_class=checked_config.asset_class,
        strategy_id=SPY_VOL_SCALED_TREND_STRATEGY_ID,
        strategy_family=SPY_VOL_SCALED_TREND_STRATEGY_FAMILY,
        timeframe=checked_config.timeframe,
        as_of=checked_config.as_of,
        short_window=checked_config.short_window,
        long_window=checked_config.long_window,
        volatility_window=checked_config.volatility_window,
        high_volatility_threshold=checked_config.high_volatility_threshold,
        high_volatility_exposure=checked_config.high_volatility_exposure,
        total_bar_count=len(ordered_bars),
        usable_bar_count=len(usable_bars),
        ignored_future_bar_count=ignored_future_bar_count,
        latest_close=latest_close,
        short_sma=short_sma,
        long_sma=long_sma,
        latest_annualized_volatility=latest_volatility,
        target_exposure=target_exposure,
        posture=posture,
        labels=SPY_VOL_SCALED_TREND_LABELS,
        blockers=blockers,
        profit_claim=_PROFIT_CLAIM,
        broker_action_performed=False,
        submit_allowed=False,
        next_action=_NEXT_ACTION,
        limitations=_DEFAULT_LIMITATIONS,
    )


def _config(value: object) -> SPYVolScaledTrendSignalConfig:
    if type(value) is not SPYVolScaledTrendSignalConfig:
        raise ValidationError("config must be a SPYVolScaledTrendSignalConfig.")
    return value


def _bar_tuple(values: Iterable[Bar], symbol: str) -> tuple[Bar, ...]:
    try:
        bars = tuple(values)
    except TypeError as exc:
        raise ValidationError("bars must be an iterable of Bar values.") from exc

    seen_dates: set[object] = set()
    for index, bar in enumerate(bars):
        if not isinstance(bar, Bar):
            raise ValidationError(f"bars[{index}] must be a Bar.")
        bar_timestamp = _utc_datetime(bar.timestamp, "timestamp")
        if bar.symbol != symbol:
            raise ValidationError("bars must contain only SPY bars.")
        bar_date = bar_timestamp.date()
        if bar_date in seen_dates:
            raise ValidationError("bars must not contain duplicate daily dates.")
        seen_dates.add(bar_date)
    return bars


def _window_sma(bars: tuple[Bar, ...], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    window_bars = bars[-window:]
    return sum((bar.close for bar in window_bars), _ZERO) / Decimal(window)


def _latest_annualized_volatility(
    bars: tuple[Bar, ...],
    window: int,
) -> Decimal | None:
    if len(bars) < window + 1:
        return None
    closes = tuple(bar.close for bar in bars)
    daily_returns = tuple(
        (current / previous) - _ONE
        for previous, current in zip(closes, closes[1:])
    )
    sample = daily_returns[-window:]
    if len(sample) < 2:
        return None
    return _decimal_from_float(stdev(float(item) for item in sample) * math.sqrt(252.0))


def _validate_result_consistency(result: SPYVolScaledTrendSignalResult) -> None:
    if result.short_window >= result.long_window:
        raise ValidationError("short_window must be less than long_window.")
    if result.usable_bar_count + result.ignored_future_bar_count != result.total_bar_count:
        raise ValidationError(
            "usable_bar_count plus ignored_future_bar_count must equal "
            "total_bar_count."
        )
    if result.usable_bar_count == 0 and result.latest_close is not None:
        raise ValidationError("latest_close must be None without usable bars.")
    insufficient = result.posture == "insufficient_history"
    if insufficient:
        if result.target_exposure != _ZERO:
            raise ValidationError("insufficient history must have zero target exposure.")
        if "insufficient_history" not in result.blockers:
            raise ValidationError("insufficient history must carry a blocker.")
        return
    if result.blockers:
        raise ValidationError("usable preview results cannot carry blockers.")
    if (
        result.latest_close is None
        or result.short_sma is None
        or result.long_sma is None
        or result.latest_annualized_volatility is None
    ):
        raise ValidationError(
            "latest close, SMAs, and volatility are required when history is usable."
        )
    if result.short_sma <= result.long_sma:
        expected_posture = "trend_off_cash"
        expected_exposure = _ZERO
    elif result.latest_annualized_volatility > result.high_volatility_threshold:
        expected_posture = "trend_on_half_exposure_high_volatility"
        expected_exposure = result.high_volatility_exposure
    else:
        expected_posture = "trend_on_full_exposure"
        expected_exposure = _ONE
    if result.posture != expected_posture:
        raise ValidationError("posture must match the fixed trend/volatility rules.")
    if result.target_exposure != expected_exposure:
        raise ValidationError(
            "target_exposure must match the fixed trend/volatility rules."
        )


def _utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a timezone-aware UTC datetime.")
    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_value(value, field_name)
    if decimal_value <= _ZERO:
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    return decimal_value


def _exposure_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_value(value, field_name)
    if decimal_value < _ZERO or decimal_value > _ONE:
        raise ValidationError(f"{field_name} must be between 0 and 1.")
    return decimal_value


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    return _positive_decimal(value, field_name)


def _optional_non_negative_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    decimal_value = _decimal_value(value, field_name)
    if decimal_value < _ZERO:
        raise ValidationError(f"{field_name} must be non-negative.")
    return decimal_value


def _decimal_value(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a Decimal.")
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a Decimal.") from exc
    if not decimal_value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return decimal_value


def _decimal_from_float(value: float) -> Decimal:
    if not math.isfinite(value):
        raise ValidationError("float metric must be finite.")
    return Decimal(str(round(value, 10)))


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    if type(value) is not str or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return value


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    items = tuple(values)
    if items != expected:
        raise ValidationError(f"{field_name} must match the required values.")
    return items


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    items = tuple(values)
    if any(type(item) is not str or not item.strip() for item in items):
        raise ValidationError(f"{field_name} must contain non-empty strings.")
    return tuple(item.strip() for item in items)


def _posture(value: object) -> str:
    if type(value) is not str or value not in SPY_VOL_SCALED_TREND_POSTURES:
        allowed = ", ".join(SPY_VOL_SCALED_TREND_POSTURES)
        raise ValidationError(f"posture must be one of: {allowed}.")
    return value


def _false_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool or value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return value


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)
