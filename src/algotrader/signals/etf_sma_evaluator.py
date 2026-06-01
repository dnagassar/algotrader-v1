"""Deterministic ETF/SMA signal evaluation for caller-supplied daily bars."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from algotrader.core.time import require_utc_datetime
from algotrader.core.types import Bar
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_SIGNAL_LABELS",
    "ETF_SMA_SIGNAL_POSTURES",
    "EtfSmaSignalConfig",
    "EtfSmaSignalEvaluator",
    "EtfSmaSignalResult",
    "evaluate_etf_sma_signal",
]

_ZERO = Decimal("0")
_STRATEGY_TYPE = "long_only_broad_etf_sma_trend_filter"
_ASSET_CLASS = "equity"
_TIMEFRAME = "daily"
_PROFIT_CLAIM = "none"
_NEXT_ACTION = (
    "m346_offline_etf_sma_signal_to_risk_execution_preview_bridge_no_broker_action"
)
_DEFAULT_LIMITATIONS = (
    "signal evaluation only",
    "not live authorized",
    "not a profitability claim",
    "not risk approval",
    "not execution authority",
    "no broker action performed",
    "no submit allowed",
    "separate offline bridge milestone required before any downstream preview",
)

ETF_SMA_SIGNAL_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
)
ETF_SMA_SIGNAL_POSTURES = (
    "bullish_risk_on",
    "defensive_risk_off",
    "insufficient_history",
)


@dataclass(frozen=True, slots=True)
class EtfSmaSignalConfig:
    """Static ETF/SMA evaluation parameters for explicit in-memory bars."""

    as_of: datetime
    symbol: str = "SPY"
    short_window: int = 50
    long_window: int = 200
    asset_class: str = _ASSET_CLASS
    timeframe: str = _TIMEFRAME

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
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
class EtfSmaSignalEvaluator:
    """Frozen evaluator object for the ETF/SMA signal contract."""

    config: EtfSmaSignalConfig

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", _config(self.config))

    def evaluate(self, bars: Iterable[Bar]) -> "EtfSmaSignalResult":
        """Evaluate explicit in-memory bars using this evaluator's config."""

        return evaluate_etf_sma_signal(bars, self.config)


@dataclass(frozen=True, slots=True)
class EtfSmaSignalResult:
    """Immutable advisory ETF/SMA posture result with hard safety flags."""

    symbol: str
    asset_class: str
    strategy_type: str
    timeframe: str
    as_of: datetime
    short_window: int
    long_window: int
    total_bar_count: int
    usable_bar_count: int
    ignored_future_bar_count: int
    latest_close: Decimal | None
    short_sma: Decimal | None
    long_sma: Decimal | None
    posture: str
    labels: tuple[str, ...]
    profit_claim: str
    broker_action_performed: bool
    submit_allowed: bool
    next_action: str
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(
            self,
            "strategy_type",
            _fixed_string(self.strategy_type, _STRATEGY_TYPE, "strategy_type"),
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
        object.__setattr__(self, "posture", _posture(self.posture))
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(self.labels, ETF_SMA_SIGNAL_LABELS, "labels"),
        )
        object.__setattr__(
            self,
            "profit_claim",
            _fixed_string(self.profit_claim, _PROFIT_CLAIM, "profit_claim"),
        )
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(
                self.broker_action_performed,
                "broker_action_performed",
            ),
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
            _fixed_string_tuple(
                self.limitations,
                _DEFAULT_LIMITATIONS,
                "limitations",
            ),
        )
        _validate_result_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only signal posture metadata."""

        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "strategy_type": self.strategy_type,
            "timeframe": self.timeframe,
            "as_of": self.as_of.isoformat(),
            "short_window": self.short_window,
            "long_window": self.long_window,
            "total_bar_count": self.total_bar_count,
            "usable_bar_count": self.usable_bar_count,
            "ignored_future_bar_count": self.ignored_future_bar_count,
            "latest_close": _decimal_text(self.latest_close),
            "short_sma": _decimal_text(self.short_sma),
            "long_sma": _decimal_text(self.long_sma),
            "posture": self.posture,
            "labels": list(self.labels),
            "profit_claim": self.profit_claim,
            "broker_action_performed": self.broker_action_performed,
            "submit_allowed": self.submit_allowed,
            "next_action": self.next_action,
            "limitations": list(self.limitations),
        }


def evaluate_etf_sma_signal(
    bars: Iterable[Bar],
    config: EtfSmaSignalConfig,
) -> EtfSmaSignalResult:
    """Evaluate the current ETF/SMA posture from explicit in-memory bars."""

    checked_config = _config(config)
    checked_bars = _bar_tuple(bars, checked_config.symbol)
    ordered_bars = tuple(sorted(checked_bars, key=lambda bar: bar.timestamp))
    usable_bars = tuple(
        bar for bar in ordered_bars if bar.timestamp <= checked_config.as_of
    )
    latest_close = usable_bars[-1].close if usable_bars else None
    short_sma = _window_sma(usable_bars, checked_config.short_window)
    long_sma = _window_sma(usable_bars, checked_config.long_window)
    ignored_future_bar_count = len(ordered_bars) - len(usable_bars)

    if len(usable_bars) < checked_config.long_window:
        posture = "insufficient_history"
    elif short_sma is not None and long_sma is not None and short_sma > long_sma:
        posture = "bullish_risk_on"
    else:
        posture = "defensive_risk_off"

    return EtfSmaSignalResult(
        symbol=checked_config.symbol,
        asset_class=checked_config.asset_class,
        strategy_type=_STRATEGY_TYPE,
        timeframe=checked_config.timeframe,
        as_of=checked_config.as_of,
        short_window=checked_config.short_window,
        long_window=checked_config.long_window,
        total_bar_count=len(ordered_bars),
        usable_bar_count=len(usable_bars),
        ignored_future_bar_count=ignored_future_bar_count,
        latest_close=latest_close,
        short_sma=short_sma,
        long_sma=long_sma,
        posture=posture,
        labels=ETF_SMA_SIGNAL_LABELS,
        profit_claim=_PROFIT_CLAIM,
        broker_action_performed=False,
        submit_allowed=False,
        next_action=_NEXT_ACTION,
        limitations=_DEFAULT_LIMITATIONS,
    )


def _config(value: object) -> EtfSmaSignalConfig:
    if type(value) is not EtfSmaSignalConfig:
        raise ValidationError("config must be an EtfSmaSignalConfig.")

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
            raise ValidationError("bars must contain only the configured symbol.")

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


def _validate_result_consistency(result: EtfSmaSignalResult) -> None:
    if result.short_window >= result.long_window:
        raise ValidationError("short_window must be less than long_window.")
    if result.usable_bar_count + result.ignored_future_bar_count != result.total_bar_count:
        raise ValidationError(
            "usable_bar_count plus ignored_future_bar_count must equal "
            "total_bar_count."
        )
    if result.usable_bar_count == 0 and result.latest_close is not None:
        raise ValidationError("latest_close must be None without usable bars.")
    if result.usable_bar_count < result.short_window and result.short_sma is not None:
        raise ValidationError("short_sma must be None without enough bars.")
    if result.usable_bar_count < result.long_window:
        if result.posture != "insufficient_history":
            raise ValidationError(
                "posture must be insufficient_history without enough bars."
            )
        if result.long_sma is not None:
            raise ValidationError("long_sma must be None without enough bars.")
        return

    if result.latest_close is None or result.short_sma is None or result.long_sma is None:
        raise ValidationError("latest_close, short_sma, and long_sma are required.")

    expected_posture = (
        "bullish_risk_on"
        if result.short_sma > result.long_sma
        else "defensive_risk_off"
    )
    if result.posture != expected_posture:
        raise ValidationError("posture must match the SMA comparison.")


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
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be a positive integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")

    return value


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal or not value.is_finite() or value <= _ZERO:
        raise ValidationError(f"{field_name} must be a positive Decimal.")

    return value


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


def _posture(value: object) -> str:
    if type(value) is not str or value not in ETF_SMA_SIGNAL_POSTURES:
        allowed = ", ".join(ETF_SMA_SIGNAL_POSTURES)
        raise ValidationError(f"posture must be one of: {allowed}.")

    return value


def _false_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be false.")
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")

    return value


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)
