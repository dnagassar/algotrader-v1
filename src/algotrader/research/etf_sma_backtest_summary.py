"""Deterministic offline ETF/SMA backtest summary contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_research_candidate import (
    ETF_SMA_CANDIDATE_LABELS,
    ETF_SMA_CANDIDATE_POSTURES,
)

__all__ = [
    "ETF_SMA_BACKTEST_SUMMARY_LABELS",
    "ETF_SMA_BACKTEST_SUMMARY_LIMITATIONS",
    "EtfSmaBacktestBar",
    "EtfSmaBacktestConfig",
    "EtfSmaBacktestSummary",
    "build_etf_sma_backtest_summary",
]


_SUMMARY_TYPE = "etf_sma_offline_backtest_summary"
_SUMMARY_STATUS = "research_measurement_only"
_ELIGIBILITY_STATUS = "research_measurement_only"
_NEXT_OPERATOR_ACTION = (
    "draft_or_review_local_data_snapshot_validation_before_paper_experiment"
)
_DEFAULT_STRATEGY_NAME = "ETF SMA offline backtest summary"
_BASIS_POINTS_DENOMINATOR = Decimal("10000")
_ONE = Decimal("1")
_ZERO = Decimal("0")

ETF_SMA_BACKTEST_SUMMARY_LABELS = ETF_SMA_CANDIDATE_LABELS
ETF_SMA_BACKTEST_SUMMARY_LIMITATIONS = (
    "synthetic_or_local_input_only",
    "zero_cost_or_declared_cost_model",
    "no_slippage_model_unless_explicitly_added",
    "no_live_or_paper_authorization",
    "not_profit_evidence",
)


@dataclass(frozen=True, slots=True)
class EtfSmaBacktestBar:
    """One deterministic local close observation for offline measurement."""

    date: str
    close: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", _iso_date(self.date, "date"))
        object.__setattr__(self, "close", _positive_decimal(self.close, "close"))

    def to_dict(self) -> dict[str, str]:
        """Return deterministic primitive-only bar metadata."""

        return {
            "date": self.date,
            "close": str(self.close),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaBacktestConfig:
    """Static ETF/SMA offline backtest parameters."""

    symbol: str = "SPY"
    strategy_name: str = _DEFAULT_STRATEGY_NAME
    short_window: int = 50
    long_window: int = 200
    cost_bps: Decimal = _ZERO

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "strategy_name",
            _required_string(self.strategy_name, "strategy_name"),
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
            "cost_bps",
            _non_negative_decimal(self.cost_bps, "cost_bps"),
        )
        if self.short_window >= self.long_window:
            raise ValidationError("short_window must be less than long_window.")

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only config metadata."""

        return {
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "short_window": self.short_window,
            "long_window": self.long_window,
            "cost_bps": str(self.cost_bps),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaBacktestSummary:
    """Offline-only ETF/SMA measurement summary with no capital authority."""

    summary_type: str
    status: str
    symbol: str
    strategy_name: str
    as_of: str
    start_date: str | None
    end_date: str | None
    sample_count: int
    bar_count: int
    ignored_future_bar_count: int
    short_window: int
    long_window: int
    cost_bps: Decimal
    signal_count: int
    exposure_count: int
    defensive_count: int
    posture_change_count: int
    strategy_total_return: Decimal
    benchmark_total_return: Decimal
    max_drawdown: Decimal
    latest_posture: str
    labels: tuple[str, ...]
    eligibility_status: str
    recommended_next_operator_action: str
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        checked_labels = _validate_fixed_metadata(
            summary_type=self.summary_type,
            status=self.status,
            labels=self.labels,
            eligibility_status=self.eligibility_status,
            recommended_next_operator_action=self.recommended_next_operator_action,
        )
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "strategy_name",
            _required_string(self.strategy_name, "strategy_name"),
        )
        object.__setattr__(self, "as_of", _iso_date(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "start_date",
            _optional_iso_date(self.start_date, "start_date"),
        )
        object.__setattr__(
            self,
            "end_date",
            _optional_iso_date(self.end_date, "end_date"),
        )
        object.__setattr__(
            self,
            "sample_count",
            _non_negative_int(self.sample_count, "sample_count"),
        )
        object.__setattr__(
            self,
            "bar_count",
            _non_negative_int(self.bar_count, "bar_count"),
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
            "cost_bps",
            _non_negative_decimal(self.cost_bps, "cost_bps"),
        )
        object.__setattr__(
            self,
            "signal_count",
            _non_negative_int(self.signal_count, "signal_count"),
        )
        object.__setattr__(
            self,
            "exposure_count",
            _non_negative_int(self.exposure_count, "exposure_count"),
        )
        object.__setattr__(
            self,
            "defensive_count",
            _non_negative_int(self.defensive_count, "defensive_count"),
        )
        object.__setattr__(
            self,
            "posture_change_count",
            _non_negative_int(self.posture_change_count, "posture_change_count"),
        )
        object.__setattr__(
            self,
            "strategy_total_return",
            _decimal(self.strategy_total_return, "strategy_total_return"),
        )
        object.__setattr__(
            self,
            "benchmark_total_return",
            _decimal(self.benchmark_total_return, "benchmark_total_return"),
        )
        object.__setattr__(
            self,
            "max_drawdown",
            _non_negative_decimal(self.max_drawdown, "max_drawdown"),
        )
        object.__setattr__(self, "latest_posture", _posture(self.latest_posture))
        object.__setattr__(self, "labels", checked_labels)
        object.__setattr__(
            self,
            "limitations",
            _limitations(self.limitations),
        )
        _validate_summary_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only summary metadata."""

        return {
            "summary_type": self.summary_type,
            "status": self.status,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "sample_count": self.sample_count,
            "bar_count": self.bar_count,
            "ignored_future_bar_count": self.ignored_future_bar_count,
            "short_window": self.short_window,
            "long_window": self.long_window,
            "cost_bps": str(self.cost_bps),
            "signal_count": self.signal_count,
            "exposure_count": self.exposure_count,
            "defensive_count": self.defensive_count,
            "posture_change_count": self.posture_change_count,
            "strategy_total_return": str(self.strategy_total_return),
            "benchmark_total_return": str(self.benchmark_total_return),
            "max_drawdown": str(self.max_drawdown),
            "latest_posture": self.latest_posture,
            "labels": list(self.labels),
            "eligibility_status": self.eligibility_status,
            "recommended_next_operator_action": (
                self.recommended_next_operator_action
            ),
            "limitations": list(self.limitations),
        }


def build_etf_sma_backtest_summary(
    bars: tuple[EtfSmaBacktestBar, ...] | list[EtfSmaBacktestBar],
    config: EtfSmaBacktestConfig,
    as_of: str,
) -> EtfSmaBacktestSummary:
    """Build an offline ETF/SMA summary using only bars at or before as-of."""

    checked_config = _config(config)
    checked_as_of = _iso_date(as_of, "as_of")
    checked_bars = _sorted_bars(bars)
    eligible_bars = tuple(bar for bar in checked_bars if bar.date <= checked_as_of)
    ignored_future_bar_count = len(checked_bars) - len(eligible_bars)
    signals, postures = _signals(
        eligible_bars,
        short_window=checked_config.short_window,
        long_window=checked_config.long_window,
    )
    measurement = _measure_returns(
        eligible_bars,
        signals,
        cost_bps=checked_config.cost_bps,
    )

    return EtfSmaBacktestSummary(
        summary_type=_SUMMARY_TYPE,
        status=_SUMMARY_STATUS,
        symbol=checked_config.symbol,
        strategy_name=checked_config.strategy_name,
        as_of=checked_as_of,
        start_date=eligible_bars[0].date if eligible_bars else None,
        end_date=eligible_bars[-1].date if eligible_bars else None,
        sample_count=len(checked_bars),
        bar_count=len(eligible_bars),
        ignored_future_bar_count=ignored_future_bar_count,
        short_window=checked_config.short_window,
        long_window=checked_config.long_window,
        cost_bps=checked_config.cost_bps,
        signal_count=sum(signal is not None for signal in signals),
        exposure_count=measurement.exposure_count,
        defensive_count=measurement.defensive_count,
        posture_change_count=measurement.posture_change_count,
        strategy_total_return=measurement.strategy_total_return,
        benchmark_total_return=_benchmark_total_return(eligible_bars),
        max_drawdown=measurement.max_drawdown,
        latest_posture=postures[-1] if postures else "insufficient_history",
        labels=ETF_SMA_BACKTEST_SUMMARY_LABELS,
        eligibility_status=_ELIGIBILITY_STATUS,
        recommended_next_operator_action=_NEXT_OPERATOR_ACTION,
        limitations=ETF_SMA_BACKTEST_SUMMARY_LIMITATIONS,
    )


@dataclass(frozen=True, slots=True)
class _ReturnMeasurement:
    strategy_total_return: Decimal
    max_drawdown: Decimal
    exposure_count: int
    defensive_count: int
    posture_change_count: int


def _signals(
    bars: tuple[EtfSmaBacktestBar, ...],
    *,
    short_window: int,
    long_window: int,
) -> tuple[tuple[Decimal | None, ...], tuple[str, ...]]:
    signals: list[Decimal | None] = []
    postures: list[str] = []

    for index in range(len(bars)):
        history = bars[: index + 1]
        short_sma = _window_sma(history, short_window)
        long_sma = _window_sma(history, long_window)

        if long_sma is None:
            signals.append(None)
            postures.append("insufficient_history")
        elif short_sma is not None and short_sma > long_sma:
            signals.append(_ONE)
            postures.append("bullish_trend_candidate")
        else:
            signals.append(_ZERO)
            postures.append("defensive_or_cash_candidate")

    return tuple(signals), tuple(postures)


def _measure_returns(
    bars: tuple[EtfSmaBacktestBar, ...],
    signals: tuple[Decimal | None, ...],
    *,
    cost_bps: Decimal,
) -> _ReturnMeasurement:
    cost_rate = cost_bps / _BASIS_POINTS_DENOMINATOR
    equity = _ONE
    peak = _ONE
    max_drawdown = _ZERO
    previous_close: Decimal | None = None
    previous_signal: Decimal | None = None
    previous_exposure = _ZERO
    exposure_count = 0
    defensive_count = 0
    posture_change_count = 0

    for bar, signal in zip(bars, signals):
        current_exposure = _ZERO if previous_signal is None else previous_signal
        asset_return = (
            _ZERO
            if previous_close is None
            else (bar.close / previous_close) - _ONE
        )
        transaction_cost = abs(current_exposure - previous_exposure) * cost_rate
        strategy_return = (current_exposure * asset_return) - transaction_cost
        equity *= _ONE + strategy_return
        if equity <= _ZERO:
            raise ValidationError("cost_bps and returns produced non-positive equity.")

        if current_exposure == _ONE:
            exposure_count += 1
        else:
            defensive_count += 1

        if current_exposure != previous_exposure:
            posture_change_count += 1

        if equity > peak:
            peak = equity
        drawdown = (equity / peak) - _ONE
        if drawdown < -max_drawdown:
            max_drawdown = -drawdown

        previous_close = bar.close
        previous_signal = signal
        previous_exposure = current_exposure

    return _ReturnMeasurement(
        strategy_total_return=equity - _ONE,
        max_drawdown=max_drawdown,
        exposure_count=exposure_count,
        defensive_count=defensive_count,
        posture_change_count=posture_change_count,
    )


def _benchmark_total_return(bars: tuple[EtfSmaBacktestBar, ...]) -> Decimal:
    if not bars:
        return _ZERO

    return (bars[-1].close / bars[0].close) - _ONE


def _window_sma(
    bars: tuple[EtfSmaBacktestBar, ...],
    window: int,
) -> Decimal | None:
    if len(bars) < window:
        return None

    window_bars = bars[-window:]
    return sum((bar.close for bar in window_bars), _ZERO) / Decimal(window)


def _validate_fixed_metadata(
    *,
    summary_type: object,
    status: object,
    labels: object,
    eligibility_status: object,
    recommended_next_operator_action: object,
) -> tuple[str, ...]:
    if summary_type != _SUMMARY_TYPE:
        raise ValidationError(
            "summary_type must be exactly etf_sma_offline_backtest_summary."
        )
    if status != _SUMMARY_STATUS:
        raise ValidationError("status must be exactly research_measurement_only.")
    checked_labels = _label_tuple(labels)
    if checked_labels != ETF_SMA_BACKTEST_SUMMARY_LABELS:
        raise ValidationError("labels must preserve the ETF/SMA candidate labels.")
    if eligibility_status != _ELIGIBILITY_STATUS:
        raise ValidationError(
            "eligibility_status must remain research_measurement_only."
        )
    if recommended_next_operator_action != _NEXT_OPERATOR_ACTION:
        raise ValidationError(
            "recommended_next_operator_action must require local data validation."
        )

    return checked_labels


def _validate_summary_consistency(summary: EtfSmaBacktestSummary) -> None:
    if summary.short_window >= summary.long_window:
        raise ValidationError("short_window must be less than long_window.")
    if summary.bar_count + summary.ignored_future_bar_count != summary.sample_count:
        raise ValidationError(
            "bar_count plus ignored_future_bar_count must equal sample_count."
        )
    if summary.bar_count == 0:
        if summary.start_date is not None or summary.end_date is not None:
            raise ValidationError("start_date and end_date must be None without bars.")
    elif summary.start_date is None or summary.end_date is None:
        raise ValidationError("start_date and end_date are required with bars.")
    elif summary.start_date > summary.end_date:
        raise ValidationError("start_date must be on or before end_date.")

    if summary.end_date is not None and summary.end_date > summary.as_of:
        raise ValidationError("end_date must be on or before as_of.")
    if summary.signal_count > summary.bar_count:
        raise ValidationError("signal_count must not exceed bar_count.")
    if summary.exposure_count + summary.defensive_count != summary.bar_count:
        raise ValidationError(
            "exposure_count plus defensive_count must equal bar_count."
        )
    if summary.posture_change_count > summary.bar_count:
        raise ValidationError("posture_change_count must not exceed bar_count.")
    if (
        summary.bar_count < summary.long_window
        and summary.latest_posture != "insufficient_history"
    ):
        raise ValidationError(
            "latest_posture must be insufficient_history without enough bars."
        )


def _iso_date(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO YYYY-MM-DD date string."
        ) from exc

    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")

    return value


def _optional_iso_date(value: object, field_name: str) -> str | None:
    if value is None:
        return None

    return _iso_date(value, field_name)


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _required_string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    normalized = symbol.upper()
    if normalized != symbol:
        raise ValidationError("symbol must use uppercase deterministic text.")
    if any(character.isspace() for character in normalized):
        raise ValidationError("symbol must not contain whitespace.")

    return normalized


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 1:
        raise ValidationError(f"{field_name} must be at least 1.")

    return value


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal(value, field_name)
    if decimal_value <= _ZERO:
        raise ValidationError(f"{field_name} must be positive.")

    return decimal_value


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal(value, field_name)
    if decimal_value < _ZERO:
        raise ValidationError(f"{field_name} must be non-negative.")

    return decimal_value


def _config(value: object) -> EtfSmaBacktestConfig:
    if type(value) is not EtfSmaBacktestConfig:
        raise ValidationError("config must be an EtfSmaBacktestConfig.")

    return value


def _sorted_bars(values: object) -> tuple[EtfSmaBacktestBar, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("bars must be a tuple or list of EtfSmaBacktestBar.")

    bars = tuple(values)
    seen_dates: set[str] = set()
    for index, bar in enumerate(bars):
        if type(bar) is not EtfSmaBacktestBar:
            raise ValidationError(f"bars[{index}] must be an EtfSmaBacktestBar.")
        if bar.date in seen_dates:
            raise ValidationError("bars must not contain duplicate dates.")
        seen_dates.add(bar.date)

    return tuple(sorted(bars, key=lambda bar: bar.date))


def _posture(value: object) -> str:
    posture = _required_string(value, "latest_posture")
    if posture not in ETF_SMA_CANDIDATE_POSTURES:
        allowed = ", ".join(ETF_SMA_CANDIDATE_POSTURES)
        raise ValidationError(f"latest_posture must be one of: {allowed}.")

    return posture


def _label_tuple(values: object) -> tuple[str, ...]:
    labels = _required_string_tuple(values, "labels")
    if len(frozenset(labels)) != len(labels):
        raise ValidationError("labels must not contain duplicates.")

    return labels


def _limitations(values: object) -> tuple[str, ...]:
    limitations = _required_string_tuple(values, "limitations")
    missing = tuple(
        limitation
        for limitation in ETF_SMA_BACKTEST_SUMMARY_LIMITATIONS
        if limitation not in limitations
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(f"limitations missing required value(s): {missing_text}.")
    if len(frozenset(limitations)) != len(limitations):
        raise ValidationError("limitations must not contain duplicates.")

    return limitations
