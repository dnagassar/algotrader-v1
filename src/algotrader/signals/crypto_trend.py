"""Preview-only crypto trend signal for the paper-lab seed lane."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from algotrader.core.time import require_utc_datetime
from algotrader.core.types import Bar
from algotrader.errors import ValidationError

CRYPTO_TREND_STRATEGY_FAMILY = "crypto_long_only_sma_trend_filter_preview"
CRYPTO_TREND_STRATEGY_ID = "crypto_sma_20_50_training_wheel_preview"
CRYPTO_TREND_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "crypto_preview_only",
    "profit_claim=none",
)
CRYPTO_TREND_POSTURES = (
    "risk_on",
    "risk_off",
    "insufficient_history",
)

CryptoTrendPosture = Literal[
    "risk_on",
    "risk_off",
    "insufficient_history",
]

__all__ = [
    "CRYPTO_TREND_LABELS",
    "CRYPTO_TREND_POSTURES",
    "CRYPTO_TREND_STRATEGY_FAMILY",
    "CRYPTO_TREND_STRATEGY_ID",
    "CryptoTrendPosture",
    "CryptoTrendSignalConfig",
    "CryptoTrendSignalEvaluator",
    "CryptoTrendSignalResult",
    "evaluate_crypto_trend_signal",
    "normalize_crypto_symbol",
]


@dataclass(frozen=True, slots=True)
class CryptoTrendSignalConfig:
    """Static parameters for one preview-only crypto SMA trend signal."""

    as_of: datetime
    symbol: str
    short_window: int = 20
    long_window: int = 50
    asset_class: str = "crypto"
    timeframe: str = "crypto_24_7_bar"

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(self, "symbol", normalize_crypto_symbol(self.symbol))
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
        if self.short_window >= self.long_window:
            raise ValidationError("short_window must be less than long_window.")
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, "crypto", "asset_class"),
        )
        object.__setattr__(
            self,
            "timeframe",
            _required_string(self.timeframe, "timeframe"),
        )


@dataclass(frozen=True, slots=True)
class CryptoTrendSignalResult:
    """Immutable preview-only crypto trend posture result."""

    symbol: str
    asset_class: str
    strategy_id: str
    strategy_family: str
    timeframe: str
    as_of: datetime
    short_window: int
    long_window: int
    total_bar_count: int
    usable_bar_count: int
    short_sma: Decimal | None
    long_sma: Decimal | None
    posture: CryptoTrendPosture
    labels: tuple[str, ...]
    blockers: tuple[str, ...]
    broker_action_performed: bool
    submit_allowed: bool
    next_action: str
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_crypto_symbol(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, "crypto", "asset_class"),
        )
        object.__setattr__(
            self,
            "strategy_id",
            _fixed_string(self.strategy_id, CRYPTO_TREND_STRATEGY_ID, "strategy_id"),
        )
        object.__setattr__(
            self,
            "strategy_family",
            _fixed_string(
                self.strategy_family,
                CRYPTO_TREND_STRATEGY_FAMILY,
                "strategy_family",
            ),
        )
        object.__setattr__(self, "timeframe", _required_string(self.timeframe, "timeframe"))
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
            _nonnegative_int(self.total_bar_count, "total_bar_count"),
        )
        object.__setattr__(
            self,
            "usable_bar_count",
            _nonnegative_int(self.usable_bar_count, "usable_bar_count"),
        )
        object.__setattr__(self, "short_sma", _optional_decimal(self.short_sma))
        object.__setattr__(self, "long_sma", _optional_decimal(self.long_sma))
        object.__setattr__(self, "posture", _posture(self.posture))
        object.__setattr__(self, "labels", _string_tuple(self.labels, "labels"))
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        if type(self.broker_action_performed) is not bool:
            raise ValidationError("broker_action_performed must be a boolean.")
        if type(self.submit_allowed) is not bool:
            raise ValidationError("submit_allowed must be a boolean.")
        object.__setattr__(
            self,
            "next_action",
            _required_string(self.next_action, "next_action"),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only signal metadata."""

        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "strategy_id": self.strategy_id,
            "strategy_family": self.strategy_family,
            "timeframe": self.timeframe,
            "as_of": self.as_of.isoformat(),
            "short_window": self.short_window,
            "long_window": self.long_window,
            "total_bar_count": self.total_bar_count,
            "usable_bar_count": self.usable_bar_count,
            "short_sma": _decimal_text(self.short_sma),
            "long_sma": _decimal_text(self.long_sma),
            "posture": self.posture,
            "labels": list(self.labels),
            "blockers": list(self.blockers),
            "broker_action_performed": self.broker_action_performed,
            "submit_allowed": self.submit_allowed,
            "next_action": self.next_action,
            "limitations": list(self.limitations),
        }


class CryptoTrendSignalEvaluator:
    """Small callable wrapper matching the signal evaluator convention."""

    def __init__(self, config: CryptoTrendSignalConfig):
        self.config = config

    def evaluate(self, bars: tuple[Bar, ...]) -> CryptoTrendSignalResult:
        return evaluate_crypto_trend_signal(bars, self.config)


def evaluate_crypto_trend_signal(
    bars: tuple[Bar, ...] | list[Bar],
    config: CryptoTrendSignalConfig,
) -> CryptoTrendSignalResult:
    """Evaluate a no-claim long-only SMA posture over explicit crypto bars."""

    checked_config = _config(config)
    checked_bars = _bar_tuple(bars, checked_config.symbol)
    ordered_bars = tuple(sorted(checked_bars, key=lambda bar: bar.timestamp))
    usable_bars = tuple(
        bar for bar in ordered_bars if _utc_datetime(bar.timestamp, "timestamp") <= checked_config.as_of
    )
    if len(usable_bars) < checked_config.long_window:
        return _result(
            checked_config,
            total_bar_count=len(ordered_bars),
            usable_bar_count=len(usable_bars),
            short_sma=None,
            long_sma=None,
            posture="insufficient_history",
            blockers=("insufficient_history",),
            next_action="observe_until_required_history_available",
        )

    short_sma = _mean_close(usable_bars[-checked_config.short_window :])
    long_sma = _mean_close(usable_bars[-checked_config.long_window :])
    posture: CryptoTrendPosture = "risk_on" if short_sma > long_sma else "risk_off"
    next_action = (
        "preview_long_only_buy_no_submit"
        if posture == "risk_on"
        else "continue_observation_no_submit"
    )
    return _result(
        checked_config,
        total_bar_count=len(ordered_bars),
        usable_bar_count=len(usable_bars),
        short_sma=short_sma,
        long_sma=long_sma,
        posture=posture,
        blockers=(),
        next_action=next_action,
    )


def normalize_crypto_symbol(value: object) -> str:
    """Normalize common crypto pair spellings to broker-style compact symbols."""

    if type(value) is not str or not value.strip():
        raise ValidationError("symbol must be a non-empty string.")
    symbol = (
        value.strip()
        .upper()
        .replace("/", "")
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )
    if not symbol:
        raise ValidationError("symbol must be a non-empty string.")
    return symbol


def _result(
    config: CryptoTrendSignalConfig,
    *,
    total_bar_count: int,
    usable_bar_count: int,
    short_sma: Decimal | None,
    long_sma: Decimal | None,
    posture: CryptoTrendPosture,
    blockers: tuple[str, ...],
    next_action: str,
) -> CryptoTrendSignalResult:
    limitations = (
        "preview_only_no_paper_or_live_authority",
        "training_wheel_trend_filter_no_alpha_claim",
    )
    return CryptoTrendSignalResult(
        symbol=config.symbol,
        asset_class=config.asset_class,
        strategy_id=CRYPTO_TREND_STRATEGY_ID,
        strategy_family=CRYPTO_TREND_STRATEGY_FAMILY,
        timeframe=config.timeframe,
        as_of=config.as_of,
        short_window=config.short_window,
        long_window=config.long_window,
        total_bar_count=total_bar_count,
        usable_bar_count=usable_bar_count,
        short_sma=short_sma,
        long_sma=long_sma,
        posture=posture,
        labels=CRYPTO_TREND_LABELS,
        blockers=blockers,
        broker_action_performed=False,
        submit_allowed=False,
        next_action=next_action,
        limitations=limitations,
    )


def _bar_tuple(values: tuple[Bar, ...] | list[Bar], symbol: str) -> tuple[Bar, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValidationError("bars must be a tuple or list of Bar values.")
    checked: list[Bar] = []
    seen_timestamps: set[datetime] = set()
    for index, value in enumerate(values):
        if not isinstance(value, Bar):
            raise ValidationError(f"bars[{index}] must be a Bar.")
        bar_symbol = normalize_crypto_symbol(value.symbol)
        if bar_symbol != symbol:
            continue
        timestamp = _utc_datetime(value.timestamp, "timestamp")
        if timestamp in seen_timestamps:
            raise ValidationError("bars must not contain duplicate timestamps.")
        seen_timestamps.add(timestamp)
        checked.append(value)
    return tuple(checked)


def _mean_close(values: tuple[Bar, ...]) -> Decimal:
    if not values:
        raise ValidationError("cannot average an empty bar window.")
    return sum((bar.close for bar in values), Decimal("0")) / Decimal(len(values))


def _config(value: object) -> CryptoTrendSignalConfig:
    if not isinstance(value, CryptoTrendSignalConfig):
        raise ValidationError("config must be a CryptoTrendSignalConfig.")
    return value


def _posture(value: object) -> CryptoTrendPosture:
    if type(value) is not str or value not in CRYPTO_TREND_POSTURES:
        raise ValidationError("posture is invalid.")
    return value  # type: ignore[return-value]


def _utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a timezone-aware UTC datetime.")
    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    text = _required_string(value, field_name)
    if text != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return text


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _nonnegative_int(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return value


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValidationError("SMA values must be finite Decimal values or None.")
    return value


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    return tuple(_required_string(value, f"{field_name}[]") for value in values)


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
