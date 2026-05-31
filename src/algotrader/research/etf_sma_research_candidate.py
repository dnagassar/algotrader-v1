"""Offline ETF SMA research-to-paper candidate contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_CANDIDATE_LABELS",
    "ETF_SMA_CANDIDATE_POSTURES",
    "SmaCandidateConfig",
    "SmaCandidateInputBar",
    "SmaResearchToPaperCandidate",
    "build_etf_sma_research_candidate",
]


_CANDIDATE_TYPE = "etf_sma_research_to_paper_candidate"
_CANDIDATE_STATUS = "research_candidate_only"
_ELIGIBILITY_STATUS = "separate_plan_required_before_paper_experiment"
_NEXT_OPERATOR_ACTION = "draft_separate_paper_lab_experiment_plan"
_DEFAULT_STRATEGY_NAME = "ETF SMA trend/crossover research-to-paper candidate"

ETF_SMA_CANDIDATE_LABELS = (
    "research_only",
    "paper_lab_candidate",
    "not_live_authorized",
    "profit_claim=none",
)
ETF_SMA_CANDIDATE_POSTURES = (
    "bullish_trend_candidate",
    "defensive_or_cash_candidate",
    "insufficient_history",
)
_DEFAULT_LIMITATIONS = (
    "offline deterministic candidate from caller-supplied local bars",
    "not approved for paper-lab submission",
    "no live authorization",
    "no profitability or edge claim",
    "separate paper-lab experiment plan required before any submission review",
)


@dataclass(frozen=True, slots=True)
class SmaCandidateInputBar:
    """One deterministic local close observation for candidate review."""

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
class SmaCandidateConfig:
    """Static SMA candidate parameters for operator review."""

    symbol: str = "SPY"
    strategy_name: str = _DEFAULT_STRATEGY_NAME
    short_window: int = 50
    long_window: int = 200

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
        if self.short_window >= self.long_window:
            raise ValidationError("short_window must be less than long_window.")

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only config metadata."""

        return {
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "short_window": self.short_window,
            "long_window": self.long_window,
        }


@dataclass(frozen=True, slots=True)
class SmaResearchToPaperCandidate:
    """Offline-only SMA candidate review artifact with no capital authority."""

    candidate_type: str
    status: str
    symbol: str
    strategy_name: str
    as_of: str
    short_window: int
    long_window: int
    sample_count: int
    eligible_sample_count: int
    ignored_future_sample_count: int
    latest_close: Decimal | None
    short_sma: Decimal | None
    long_sma: Decimal | None
    posture: str
    evidence_summary: tuple[str, ...]
    limitations: tuple[str, ...]
    labels: tuple[str, ...]
    eligibility_status: str
    recommended_next_operator_action: str

    def __post_init__(self) -> None:
        checked_labels = _validate_fixed_metadata(
            candidate_type=self.candidate_type,
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
            "sample_count",
            _non_negative_int(self.sample_count, "sample_count"),
        )
        object.__setattr__(
            self,
            "eligible_sample_count",
            _non_negative_int(self.eligible_sample_count, "eligible_sample_count"),
        )
        object.__setattr__(
            self,
            "ignored_future_sample_count",
            _non_negative_int(
                self.ignored_future_sample_count,
                "ignored_future_sample_count",
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
            "evidence_summary",
            _required_string_tuple(self.evidence_summary, "evidence_summary"),
        )
        object.__setattr__(
            self,
            "limitations",
            _required_string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "labels", checked_labels)
        _validate_count_consistency(
            sample_count=self.sample_count,
            eligible_sample_count=self.eligible_sample_count,
            ignored_future_sample_count=self.ignored_future_sample_count,
        )
        _validate_window_consistency(
            short_window=self.short_window,
            long_window=self.long_window,
        )
        _validate_candidate_consistency(
            long_window=self.long_window,
            eligible_sample_count=self.eligible_sample_count,
            latest_close=self.latest_close,
            short_sma=self.short_sma,
            long_sma=self.long_sma,
            posture=self.posture,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only candidate metadata."""

        return {
            "candidate_type": self.candidate_type,
            "status": self.status,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "short_window": self.short_window,
            "long_window": self.long_window,
            "sample_count": self.sample_count,
            "eligible_sample_count": self.eligible_sample_count,
            "ignored_future_sample_count": self.ignored_future_sample_count,
            "latest_close": _decimal_text(self.latest_close),
            "short_sma": _decimal_text(self.short_sma),
            "long_sma": _decimal_text(self.long_sma),
            "posture": self.posture,
            "evidence_summary": list(self.evidence_summary),
            "limitations": list(self.limitations),
            "labels": list(self.labels),
            "eligibility_status": self.eligibility_status,
            "recommended_next_operator_action": self.recommended_next_operator_action,
        }


def build_etf_sma_research_candidate(
    bars: tuple[SmaCandidateInputBar, ...] | list[SmaCandidateInputBar],
    config: SmaCandidateConfig,
    as_of: str,
) -> SmaResearchToPaperCandidate:
    """Build an offline SMA candidate using only bars at or before as-of."""

    checked_config = _config(config)
    checked_as_of = _iso_date(as_of, "as_of")
    checked_bars = _sorted_bars(bars)
    eligible_bars = tuple(bar for bar in checked_bars if bar.date <= checked_as_of)
    ignored_future_sample_count = len(checked_bars) - len(eligible_bars)
    latest_close = eligible_bars[-1].close if eligible_bars else None
    short_sma = _window_sma(eligible_bars, checked_config.short_window)
    long_sma = _window_sma(eligible_bars, checked_config.long_window)

    if len(eligible_bars) < checked_config.long_window:
        posture = "insufficient_history"
    elif short_sma is not None and long_sma is not None and short_sma > long_sma:
        posture = "bullish_trend_candidate"
    else:
        posture = "defensive_or_cash_candidate"

    return SmaResearchToPaperCandidate(
        candidate_type=_CANDIDATE_TYPE,
        status=_CANDIDATE_STATUS,
        symbol=checked_config.symbol,
        strategy_name=checked_config.strategy_name,
        as_of=checked_as_of,
        short_window=checked_config.short_window,
        long_window=checked_config.long_window,
        sample_count=len(checked_bars),
        eligible_sample_count=len(eligible_bars),
        ignored_future_sample_count=ignored_future_sample_count,
        latest_close=latest_close,
        short_sma=short_sma,
        long_sma=long_sma,
        posture=posture,
        evidence_summary=_evidence_summary(
            as_of=checked_as_of,
            eligible_sample_count=len(eligible_bars),
            short_window=checked_config.short_window,
            long_window=checked_config.long_window,
            short_sma=short_sma,
            long_sma=long_sma,
            posture=posture,
        ),
        limitations=_DEFAULT_LIMITATIONS,
        labels=ETF_SMA_CANDIDATE_LABELS,
        eligibility_status=_ELIGIBILITY_STATUS,
        recommended_next_operator_action=_NEXT_OPERATOR_ACTION,
    )


def _validate_fixed_metadata(
    *,
    candidate_type: object,
    status: object,
    labels: object,
    eligibility_status: object,
    recommended_next_operator_action: object,
) -> tuple[str, ...]:
    if candidate_type != _CANDIDATE_TYPE:
        raise ValidationError(
            "candidate_type must be exactly etf_sma_research_to_paper_candidate."
        )
    if status != _CANDIDATE_STATUS:
        raise ValidationError("status must be exactly research_candidate_only.")
    checked_labels = _label_tuple(labels)
    if checked_labels != ETF_SMA_CANDIDATE_LABELS:
        raise ValidationError("labels must match the required SMA candidate labels.")
    if eligibility_status != _ELIGIBILITY_STATUS:
        raise ValidationError(
            "eligibility_status must require a separate paper experiment plan."
        )
    if recommended_next_operator_action != _NEXT_OPERATOR_ACTION:
        raise ValidationError(
            "recommended_next_operator_action must be the separate plan action."
        )

    return checked_labels


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
    if decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")

    return decimal_value


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None

    return _positive_decimal(value, field_name)


def _config(value: object) -> SmaCandidateConfig:
    if type(value) is not SmaCandidateConfig:
        raise ValidationError("config must be a SmaCandidateConfig.")

    return value


def _sorted_bars(values: object) -> tuple[SmaCandidateInputBar, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("bars must be a tuple or list of SmaCandidateInputBar.")

    bars = tuple(values)
    seen_dates: set[str] = set()
    for index, bar in enumerate(bars):
        if type(bar) is not SmaCandidateInputBar:
            raise ValidationError(f"bars[{index}] must be a SmaCandidateInputBar.")
        if bar.date in seen_dates:
            raise ValidationError("bars must not contain duplicate dates.")
        seen_dates.add(bar.date)

    return tuple(sorted(bars, key=lambda bar: bar.date))


def _window_sma(
    bars: tuple[SmaCandidateInputBar, ...],
    window: int,
) -> Decimal | None:
    if len(bars) < window:
        return None

    window_bars = bars[-window:]
    return sum((bar.close for bar in window_bars), Decimal("0")) / Decimal(window)


def _posture(value: object) -> str:
    posture = _required_string(value, "posture")
    if posture not in ETF_SMA_CANDIDATE_POSTURES:
        allowed = ", ".join(ETF_SMA_CANDIDATE_POSTURES)
        raise ValidationError(f"posture must be one of: {allowed}.")

    return posture


def _label_tuple(values: object) -> tuple[str, ...]:
    labels = _required_string_tuple(values, "labels")
    if len(frozenset(labels)) != len(labels):
        raise ValidationError("labels must not contain duplicates.")

    return labels


def _validate_count_consistency(
    *,
    sample_count: int,
    eligible_sample_count: int,
    ignored_future_sample_count: int,
) -> None:
    if eligible_sample_count + ignored_future_sample_count != sample_count:
        raise ValidationError(
            "eligible_sample_count plus ignored_future_sample_count must equal "
            "sample_count."
        )


def _validate_window_consistency(*, short_window: int, long_window: int) -> None:
    if short_window >= long_window:
        raise ValidationError("short_window must be less than long_window.")


def _validate_candidate_consistency(
    *,
    long_window: int,
    eligible_sample_count: int,
    latest_close: Decimal | None,
    short_sma: Decimal | None,
    long_sma: Decimal | None,
    posture: str,
) -> None:
    if eligible_sample_count == 0 and latest_close is not None:
        raise ValidationError("latest_close must be None without eligible bars.")

    if eligible_sample_count < long_window:
        if posture != "insufficient_history":
            raise ValidationError(
                "posture must be insufficient_history without enough bars."
            )
        if long_sma is not None:
            raise ValidationError("long_sma must be None without enough bars.")
        return

    if latest_close is None or short_sma is None or long_sma is None:
        raise ValidationError("latest_close, short_sma, and long_sma are required.")
    expected_posture = (
        "bullish_trend_candidate"
        if short_sma > long_sma
        else "defensive_or_cash_candidate"
    )
    if posture != expected_posture:
        raise ValidationError("posture must match the SMA comparison.")


def _evidence_summary(
    *,
    as_of: str,
    eligible_sample_count: int,
    short_window: int,
    long_window: int,
    short_sma: Decimal | None,
    long_sma: Decimal | None,
    posture: str,
) -> tuple[str, ...]:
    if posture == "insufficient_history":
        return (
            f"{eligible_sample_count} as-of bars available; {long_window} required.",
            "Future-dated bars were ignored before SMA calculation.",
        )

    comparison = "above" if posture == "bullish_trend_candidate" else "at or below"
    return (
        (
            f"As of {as_of}, the {short_window}-bar SMA {short_sma} is "
            f"{comparison} the {long_window}-bar SMA {long_sma}."
        ),
        "Future-dated bars were ignored before SMA calculation.",
    )


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)
