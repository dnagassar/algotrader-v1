"""Deterministic SPY RSI mean-reversion shadow signal evaluation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from algotrader.core.time import require_utc_datetime
from algotrader.core.types import Bar
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "SPY_RSI_MEAN_REVERSION_LABELS",
    "SPY_RSI_MEAN_REVERSION_POSTURES",
    "SPYRsiMeanReversionSignalConfig",
    "SPYRsiMeanReversionSignalEvaluator",
    "SPYRsiMeanReversionSignalResult",
    "evaluate_spy_rsi_mean_reversion_signal",
]

SPY_RSI_MEAN_REVERSION_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "shadow_only",
    "not_live_authorized",
    "profit_claim=none",
    "accepted_adjusted_spy_daily_bars",
)
SPY_RSI_MEAN_REVERSION_POSTURES = (
    "oversold_buy_candidate",
    "overbought_cash_candidate",
    "neutral_no_trade",
    "insufficient_history",
)

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_STRATEGY_TYPE = "mean_reversion"
_ASSET_CLASS = "equity"
_TIMEFRAME = "daily"
_PROFIT_CLAIM = "none"
_NEXT_ACTION = "shadow_route_only_no_broker_action"
_DEFAULT_LIMITATIONS = (
    "shadow signal evaluation only",
    "not live authorized",
    "not a profitability claim",
    "not risk approval",
    "not execution authority",
    "no broker action performed",
    "no submit allowed",
    "requires explicit future promotion before paper mutation eligibility",
)


@dataclass(frozen=True, slots=True)
class SPYRsiMeanReversionSignalConfig:
    """Static RSI parameters for explicit in-memory accepted SPY daily bars."""

    as_of: datetime
    symbol: str = "SPY"
    lookback_window: int = 14
    oversold_threshold: Decimal | str = Decimal("30")
    overbought_threshold: Decimal | str = Decimal("70")
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
            "lookback_window",
            _positive_int(self.lookback_window, "lookback_window"),
        )
        object.__setattr__(
            self,
            "oversold_threshold",
            _threshold_decimal(self.oversold_threshold, "oversold_threshold"),
        )
        object.__setattr__(
            self,
            "overbought_threshold",
            _threshold_decimal(self.overbought_threshold, "overbought_threshold"),
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
        if self.oversold_threshold >= self.overbought_threshold:
            raise ValidationError(
                "oversold_threshold must be less than overbought_threshold."
            )


@dataclass(frozen=True, slots=True)
class SPYRsiMeanReversionSignalEvaluator:
    """Frozen evaluator object for the SPY RSI shadow signal contract."""

    config: SPYRsiMeanReversionSignalConfig

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", _config(self.config))

    def evaluate(self, bars: Iterable[Bar]) -> "SPYRsiMeanReversionSignalResult":
        """Evaluate explicit accepted SPY daily bars using this evaluator config."""

        return evaluate_spy_rsi_mean_reversion_signal(bars, self.config)


@dataclass(frozen=True, slots=True)
class SPYRsiMeanReversionSignalResult:
    """Immutable SPY RSI mean-reversion shadow result with hard safety flags."""

    symbol: str
    asset_class: str
    strategy_type: str
    timeframe: str
    as_of: datetime
    lookback_window: int
    oversold_threshold: Decimal
    overbought_threshold: Decimal
    total_bar_count: int
    usable_bar_count: int
    ignored_future_bar_count: int
    latest_close: Decimal | None
    latest_rsi: Decimal | None
    average_gain: Decimal | None
    average_loss: Decimal | None
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
            "lookback_window",
            _positive_int(self.lookback_window, "lookback_window"),
        )
        object.__setattr__(
            self,
            "oversold_threshold",
            _threshold_decimal(self.oversold_threshold, "oversold_threshold"),
        )
        object.__setattr__(
            self,
            "overbought_threshold",
            _threshold_decimal(self.overbought_threshold, "overbought_threshold"),
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
            "latest_rsi",
            _optional_threshold_decimal(self.latest_rsi, "latest_rsi"),
        )
        object.__setattr__(
            self,
            "average_gain",
            _optional_non_negative_decimal(self.average_gain, "average_gain"),
        )
        object.__setattr__(
            self,
            "average_loss",
            _optional_non_negative_decimal(self.average_loss, "average_loss"),
        )
        object.__setattr__(self, "posture", _posture(self.posture))
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                SPY_RSI_MEAN_REVERSION_LABELS,
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
        """Return deterministic primitive-only RSI shadow metadata."""

        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "strategy_type": self.strategy_type,
            "timeframe": self.timeframe,
            "as_of": self.as_of.isoformat(),
            "lookback_window": self.lookback_window,
            "oversold_threshold": _decimal_text(self.oversold_threshold),
            "overbought_threshold": _decimal_text(self.overbought_threshold),
            "total_bar_count": self.total_bar_count,
            "usable_bar_count": self.usable_bar_count,
            "ignored_future_bar_count": self.ignored_future_bar_count,
            "latest_close": _decimal_text(self.latest_close),
            "latest_rsi": _decimal_text(self.latest_rsi),
            "average_gain": _decimal_text(self.average_gain),
            "average_loss": _decimal_text(self.average_loss),
            "posture": self.posture,
            "labels": list(self.labels),
            "blockers": list(self.blockers),
            "profit_claim": self.profit_claim,
            "broker_action_performed": self.broker_action_performed,
            "submit_allowed": self.submit_allowed,
            "next_action": self.next_action,
            "limitations": list(self.limitations),
        }


def evaluate_spy_rsi_mean_reversion_signal(
    bars: Iterable[Bar],
    config: SPYRsiMeanReversionSignalConfig,
) -> SPYRsiMeanReversionSignalResult:
    """Evaluate the SPY RSI mean-reversion shadow posture from explicit bars."""

    checked_config = _config(config)
    checked_bars = _bar_tuple(bars, checked_config.symbol)
    ordered_bars = tuple(sorted(checked_bars, key=lambda bar: bar.timestamp))
    usable_bars = tuple(
        bar for bar in ordered_bars if bar.timestamp <= checked_config.as_of
    )
    latest_close = usable_bars[-1].close if usable_bars else None
    latest_rsi, average_gain, average_loss = _window_rsi(
        usable_bars,
        checked_config.lookback_window,
    )
    ignored_future_bar_count = len(ordered_bars) - len(usable_bars)

    if len(usable_bars) < checked_config.lookback_window + 1:
        posture = "insufficient_history"
        blockers = ("insufficient_history",)
    elif latest_rsi is not None and latest_rsi <= checked_config.oversold_threshold:
        posture = "oversold_buy_candidate"
        blockers = ()
    elif latest_rsi is not None and latest_rsi >= checked_config.overbought_threshold:
        posture = "overbought_cash_candidate"
        blockers = ()
    else:
        posture = "neutral_no_trade"
        blockers = ()

    return SPYRsiMeanReversionSignalResult(
        symbol=checked_config.symbol,
        asset_class=checked_config.asset_class,
        strategy_type=_STRATEGY_TYPE,
        timeframe=checked_config.timeframe,
        as_of=checked_config.as_of,
        lookback_window=checked_config.lookback_window,
        oversold_threshold=checked_config.oversold_threshold,
        overbought_threshold=checked_config.overbought_threshold,
        total_bar_count=len(ordered_bars),
        usable_bar_count=len(usable_bars),
        ignored_future_bar_count=ignored_future_bar_count,
        latest_close=latest_close,
        latest_rsi=latest_rsi,
        average_gain=average_gain,
        average_loss=average_loss,
        posture=posture,
        labels=SPY_RSI_MEAN_REVERSION_LABELS,
        blockers=blockers,
        profit_claim=_PROFIT_CLAIM,
        broker_action_performed=False,
        submit_allowed=False,
        next_action=_NEXT_ACTION,
        limitations=_DEFAULT_LIMITATIONS,
    )


def _config(value: object) -> SPYRsiMeanReversionSignalConfig:
    if type(value) is not SPYRsiMeanReversionSignalConfig:
        raise ValidationError("config must be a SPYRsiMeanReversionSignalConfig.")
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


def _window_rsi(
    bars: tuple[Bar, ...],
    lookback_window: int,
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    if len(bars) < lookback_window + 1:
        return None, None, None

    window_bars = bars[-(lookback_window + 1) :]
    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for previous, current in zip(window_bars, window_bars[1:]):
        delta = current.close - previous.close
        gains.append(delta if delta > _ZERO else _ZERO)
        losses.append(-delta if delta < _ZERO else _ZERO)

    divisor = Decimal(lookback_window)
    average_gain = sum(gains, _ZERO) / divisor
    average_loss = sum(losses, _ZERO) / divisor
    if average_gain == _ZERO and average_loss == _ZERO:
        latest_rsi = Decimal("50")
    elif average_loss == _ZERO:
        latest_rsi = _HUNDRED
    else:
        relative_strength = average_gain / average_loss
        latest_rsi = _HUNDRED - (_HUNDRED / (_ONE + relative_strength))
    return latest_rsi, average_gain, average_loss


def _validate_result_consistency(result: SPYRsiMeanReversionSignalResult) -> None:
    if result.oversold_threshold >= result.overbought_threshold:
        raise ValidationError(
            "oversold_threshold must be less than overbought_threshold."
        )
    if result.usable_bar_count + result.ignored_future_bar_count != result.total_bar_count:
        raise ValidationError(
            "usable_bar_count plus ignored_future_bar_count must equal "
            "total_bar_count."
        )
    if result.usable_bar_count == 0 and result.latest_close is not None:
        raise ValidationError("latest_close must be None without usable bars.")
    if result.usable_bar_count < result.lookback_window + 1:
        if result.posture != "insufficient_history":
            raise ValidationError(
                "posture must be insufficient_history without enough bars."
            )
        if result.latest_rsi is not None:
            raise ValidationError("latest_rsi must be None without enough bars.")
        if result.average_gain is not None or result.average_loss is not None:
            raise ValidationError("average gains/losses require enough bars.")
        if "insufficient_history" not in result.blockers:
            raise ValidationError("insufficient history must carry a blocker.")
        return

    if (
        result.latest_close is None
        or result.latest_rsi is None
        or result.average_gain is None
        or result.average_loss is None
    ):
        raise ValidationError(
            "latest_close, latest_rsi, average_gain, and average_loss are required."
        )

    expected_posture = "neutral_no_trade"
    if result.latest_rsi <= result.oversold_threshold:
        expected_posture = "oversold_buy_candidate"
    elif result.latest_rsi >= result.overbought_threshold:
        expected_posture = "overbought_cash_candidate"
    if result.posture != expected_posture:
        raise ValidationError("posture must match the RSI threshold comparison.")
    if result.posture != "insufficient_history" and result.blockers:
        raise ValidationError("actionable or neutral RSI results cannot carry blockers.")


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


def _threshold_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_value(value, field_name)
    if decimal_value < _ZERO or decimal_value > _HUNDRED:
        raise ValidationError(f"{field_name} must be between 0 and 100.")
    return decimal_value


def _optional_threshold_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    return _threshold_decimal(value, field_name)


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    decimal_value = _decimal_value(value, field_name)
    if decimal_value <= _ZERO:
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    return decimal_value


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
    if type(value) is not str or value not in SPY_RSI_MEAN_REVERSION_POSTURES:
        allowed = ", ".join(SPY_RSI_MEAN_REVERSION_POSTURES)
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
