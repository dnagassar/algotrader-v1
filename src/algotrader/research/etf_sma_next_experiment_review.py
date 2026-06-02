"""Offline SPY ETF/SMA next-experiment review packet."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_NEXT_EXPERIMENT_REVIEW_DECISIONS",
    "ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS",
    "ETF_SMA_NEXT_EXPERIMENT_REVIEW_LIMITATIONS",
    "EtfSmaNextExperimentReview",
    "EtfSmaNextExperimentReviewConfig",
    "build_etf_sma_next_experiment_review",
]


_REVIEW_TYPE = "etf_sma_next_experiment_review"
_CLEAN_RESET_CLASSIFICATION = "paper_lab_flat_clean"
_DEFAULT_SOURCE_EVIDENCE_ID = "m366_fresh_paper_lab_reset_snapshot"
_DEFAULT_STRATEGY_NAME = "long_only_broad_etf_sma_50_200_daily"
_MAX_TARGET_CAP = Decimal("25.00")
_ZERO = Decimal("0")

_READY_DECISION = "ready_for_separate_broker_preview_milestone"
_BLOCKED_RESET_DECISION = "blocked_reset_not_clean"
_BLOCKED_SYMBOL_DECISION = "blocked_symbol_not_allowed"
_BLOCKED_CAP_DECISION = "blocked_cap_invalid"
_BLOCKED_SIGNAL_DECISION = "blocked_signal_not_actionable"
_OPERATOR_REVIEW_DECISION = "operator_review_required"

_READY_NEXT_MILESTONE = "M368 - SPY ETF/SMA broker-facing preview-only milestone"
_BLOCKED_NEXT_MILESTONE = "resolve_m367_blocker_offline_before_paper_facing_work"
_OPERATOR_NEXT_MILESTONE = "operator_review_m367_inputs_before_preview_decision"

ETF_SMA_NEXT_EXPERIMENT_REVIEW_DECISIONS = (
    _READY_DECISION,
    _BLOCKED_RESET_DECISION,
    _BLOCKED_SYMBOL_DECISION,
    _BLOCKED_CAP_DECISION,
    _BLOCKED_SIGNAL_DECISION,
    _OPERATOR_REVIEW_DECISION,
)

ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS = (
    "paper_lab_only",
    "offline_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
)

ETF_SMA_NEXT_EXPERIMENT_REVIEW_LIMITATIONS = (
    "offline_review_only",
    "no_broker_call_performed",
    "no_broker_preview_authorized_by_m367",
    "broker_preview_requires_separate_milestone",
    "no_order_submit_authorized",
    "submit_authorized_always_false",
    "not_live_authorized",
    "profit_claim=none",
)

_ACTIONABLE_SIGNAL_STATUSES = (
    "bullish_risk_on",
    "risk_on",
    "actionable_risk_on",
    "sma50_gt_sma200",
)

_RISK_OFF_SIGNAL_STATUSES = (
    "defensive_risk_off",
    "defensive_or_cash_candidate",
    "risk_off",
    "sma50_lte_sma200",
)

_INSUFFICIENT_SIGNAL_STATUSES = (
    "insufficient_history",
    "fewer_than_200_usable_bars",
)

_STALE_SIGNAL_STATUSES = (
    "stale",
    "stale_signal",
)

_MISSING_SIGNAL_STATUSES = (
    "missing",
    "unknown",
    "not_actionable",
)


@dataclass(frozen=True, slots=True)
class EtfSmaNextExperimentReviewConfig:
    """Static offline scope for the next SPY ETF/SMA paper-lab review."""

    symbol: str = "SPY"
    asset_class: str = "equity"
    strategy_name: str = _DEFAULT_STRATEGY_NAME
    target_cap: Decimal | None = _MAX_TARGET_CAP
    allowlist: tuple[str, ...] = ("SPY",)
    labels: tuple[str, ...] = ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS
    source_evidence_id: str = _DEFAULT_SOURCE_EVIDENCE_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _required_string(self.asset_class, "asset_class"),
        )
        object.__setattr__(
            self,
            "strategy_name",
            _required_string(self.strategy_name, "strategy_name"),
        )
        object.__setattr__(
            self,
            "target_cap",
            _optional_decimal(self.target_cap, "target_cap"),
        )
        object.__setattr__(
            self,
            "allowlist",
            _symbol_tuple(self.allowlist, "allowlist"),
        )
        object.__setattr__(
            self,
            "labels",
            _string_tuple(self.labels, "labels", allow_empty=False),
        )
        object.__setattr__(
            self,
            "source_evidence_id",
            _required_string(self.source_evidence_id, "source_evidence_id"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only config metadata."""

        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "strategy_name": self.strategy_name,
            "target_cap": _decimal_text(self.target_cap),
            "allowlist": list(self.allowlist),
            "labels": list(self.labels),
            "source_evidence_id": self.source_evidence_id,
        }


@dataclass(frozen=True, slots=True)
class EtfSmaNextExperimentReview:
    """Immutable offline review packet with no paper-order authority."""

    review_type: str
    decision: str
    reason: str
    source_evidence_id: str
    paper_reset_classification: str
    cash: Decimal | None
    currency: str | None
    position_count: int
    open_order_count: int
    symbol: str
    asset_class: str
    strategy_name: str
    signal_status: str | None
    target_cap: Decimal | None
    allowlist: tuple[str, ...]
    required_next_milestone: str
    safety_labels: tuple[str, ...]
    blockers: tuple[str, ...]
    separate_broker_preview_milestone_allowed: bool
    submit_authorized: bool
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "review_type", _review_type(self.review_type))
        object.__setattr__(self, "decision", _decision(self.decision))
        object.__setattr__(self, "reason", _required_string(self.reason, "reason"))
        object.__setattr__(
            self,
            "source_evidence_id",
            _required_string(self.source_evidence_id, "source_evidence_id"),
        )
        object.__setattr__(
            self,
            "paper_reset_classification",
            _required_string(
                self.paper_reset_classification,
                "paper_reset_classification",
            ),
        )
        object.__setattr__(self, "cash", _optional_decimal(self.cash, "cash"))
        object.__setattr__(
            self,
            "currency",
            _optional_string(self.currency, "currency"),
        )
        object.__setattr__(
            self,
            "position_count",
            _non_negative_int(self.position_count, "position_count"),
        )
        object.__setattr__(
            self,
            "open_order_count",
            _non_negative_int(self.open_order_count, "open_order_count"),
        )
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _required_string(self.asset_class, "asset_class"),
        )
        object.__setattr__(
            self,
            "strategy_name",
            _required_string(self.strategy_name, "strategy_name"),
        )
        object.__setattr__(
            self,
            "signal_status",
            _optional_string(self.signal_status, "signal_status"),
        )
        object.__setattr__(
            self,
            "target_cap",
            _optional_decimal(self.target_cap, "target_cap"),
        )
        object.__setattr__(
            self,
            "allowlist",
            _symbol_tuple(self.allowlist, "allowlist"),
        )
        object.__setattr__(
            self,
            "required_next_milestone",
            _required_string(self.required_next_milestone, "required_next_milestone"),
        )
        object.__setattr__(
            self,
            "safety_labels",
            _string_tuple(self.safety_labels, "safety_labels", allow_empty=False),
        )
        object.__setattr__(
            self,
            "blockers",
            _string_tuple(self.blockers, "blockers", allow_empty=True),
        )
        object.__setattr__(
            self,
            "separate_broker_preview_milestone_allowed",
            _bool(
                self.separate_broker_preview_milestone_allowed,
                "separate_broker_preview_milestone_allowed",
            ),
        )
        object.__setattr__(
            self,
            "submit_authorized",
            _false_bool(self.submit_authorized, "submit_authorized"),
        )
        object.__setattr__(
            self,
            "limitations",
            _limitations(self.limitations),
        )
        _validate_review_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only review metadata."""

        return {
            "review_type": self.review_type,
            "decision": self.decision,
            "reason": self.reason,
            "source_evidence_id": self.source_evidence_id,
            "paper_reset_classification": self.paper_reset_classification,
            "cash": _decimal_text(self.cash),
            "currency": self.currency,
            "position_count": self.position_count,
            "open_order_count": self.open_order_count,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "strategy_name": self.strategy_name,
            "signal_status": self.signal_status,
            "target_cap": _decimal_text(self.target_cap),
            "allowlist": list(self.allowlist),
            "required_next_milestone": self.required_next_milestone,
            "safety_labels": list(self.safety_labels),
            "blockers": list(self.blockers),
            "separate_broker_preview_milestone_allowed": (
                self.separate_broker_preview_milestone_allowed
            ),
            "submit_authorized": self.submit_authorized,
            "limitations": list(self.limitations),
        }


def build_etf_sma_next_experiment_review(
    *,
    paper_reset_classification: str,
    position_count: int,
    open_order_count: int,
    signal_status: str | None,
    config: EtfSmaNextExperimentReviewConfig | None = None,
    cash: Decimal | None = None,
    currency: str | None = None,
) -> EtfSmaNextExperimentReview:
    """Build a deterministic offline review packet from explicit inputs only."""

    checked_config = _config_or_default(config)
    checked_reset = _required_string(
        paper_reset_classification,
        "paper_reset_classification",
    )
    checked_position_count = _non_negative_int(position_count, "position_count")
    checked_open_order_count = _non_negative_int(open_order_count, "open_order_count")
    checked_signal_status = _optional_string(signal_status, "signal_status")
    checked_cash = _optional_decimal(cash, "cash")
    checked_currency = _optional_string(currency, "currency")

    reset_blockers = _reset_blockers(
        checked_reset,
        checked_position_count,
        checked_open_order_count,
    )
    symbol_blockers = _symbol_blockers(
        checked_config.symbol,
        checked_config.allowlist,
    )
    cap_blockers = _cap_blockers(checked_config.target_cap)
    signal_blockers = _signal_blockers(checked_signal_status)
    operator_blockers = _operator_blockers(
        asset_class=checked_config.asset_class,
        labels=checked_config.labels,
        cash=checked_cash,
        currency=checked_currency,
        target_cap=checked_config.target_cap,
    )

    blockers = _merged_strings(
        reset_blockers,
        symbol_blockers,
        cap_blockers,
        signal_blockers,
        operator_blockers,
    )
    decision = _decision_from_blockers(
        reset_blockers=reset_blockers,
        symbol_blockers=symbol_blockers,
        cap_blockers=cap_blockers,
        signal_blockers=signal_blockers,
        operator_blockers=operator_blockers,
    )

    return EtfSmaNextExperimentReview(
        review_type=_REVIEW_TYPE,
        decision=decision,
        reason=_reason(decision),
        source_evidence_id=checked_config.source_evidence_id,
        paper_reset_classification=checked_reset,
        cash=checked_cash,
        currency=checked_currency,
        position_count=checked_position_count,
        open_order_count=checked_open_order_count,
        symbol=checked_config.symbol,
        asset_class=checked_config.asset_class,
        strategy_name=checked_config.strategy_name,
        signal_status=checked_signal_status,
        target_cap=checked_config.target_cap,
        allowlist=checked_config.allowlist,
        required_next_milestone=_required_next_milestone(decision),
        safety_labels=checked_config.labels,
        blockers=blockers,
        separate_broker_preview_milestone_allowed=decision == _READY_DECISION,
        submit_authorized=False,
        limitations=ETF_SMA_NEXT_EXPERIMENT_REVIEW_LIMITATIONS,
    )


def _config_or_default(
    value: EtfSmaNextExperimentReviewConfig | None,
) -> EtfSmaNextExperimentReviewConfig:
    if value is None:
        return EtfSmaNextExperimentReviewConfig()
    if type(value) is not EtfSmaNextExperimentReviewConfig:
        raise ValidationError("config must be an EtfSmaNextExperimentReviewConfig.")

    return value


def _reset_blockers(
    paper_reset_classification: str,
    position_count: int,
    open_order_count: int,
) -> tuple[str, ...]:
    blockers: list[str] = []

    if paper_reset_classification != _CLEAN_RESET_CLASSIFICATION:
        blockers.append("reset_classification_not_paper_lab_flat_clean")
    if position_count != 0:
        blockers.append("positions_present")
    if open_order_count != 0:
        blockers.append("open_orders_present")

    return tuple(blockers)


def _symbol_blockers(symbol: str, allowlist: tuple[str, ...]) -> tuple[str, ...]:
    blockers: list[str] = []

    if symbol != "SPY":
        blockers.append("symbol_not_spy")
    if allowlist != ("SPY",):
        blockers.append("allowlist_not_spy_only")

    return tuple(blockers)


def _cap_blockers(target_cap: Decimal | None) -> tuple[str, ...]:
    if target_cap is None:
        return ("cap_missing",)
    if target_cap <= _ZERO:
        return ("cap_non_positive",)
    if target_cap > _MAX_TARGET_CAP:
        return ("cap_above_25_usd",)

    return ()


def _signal_blockers(signal_status: str | None) -> tuple[str, ...]:
    if signal_status is None:
        return ("signal_status_missing",)
    if signal_status in _ACTIONABLE_SIGNAL_STATUSES:
        return ()
    if signal_status in _RISK_OFF_SIGNAL_STATUSES:
        return ("signal_status_risk_off",)
    if signal_status in _INSUFFICIENT_SIGNAL_STATUSES:
        return ("signal_status_insufficient_history",)
    if signal_status in _STALE_SIGNAL_STATUSES:
        return ("signal_status_stale",)
    if signal_status in _MISSING_SIGNAL_STATUSES:
        return ("signal_status_missing_or_not_actionable",)

    return ("signal_status_not_actionable",)


def _operator_blockers(
    *,
    asset_class: str,
    labels: tuple[str, ...],
    cash: Decimal | None,
    currency: str | None,
    target_cap: Decimal | None,
) -> tuple[str, ...]:
    blockers: list[str] = []

    if asset_class != "equity":
        blockers.append("asset_class_not_equity")
    if labels != ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS:
        blockers.append("safety_labels_not_m367_default")
    if currency is not None and currency != "USD":
        blockers.append("currency_not_usd")
    if cash is not None and cash < _ZERO:
        blockers.append("cash_negative")
    if cash is not None and target_cap is not None and cash < target_cap:
        blockers.append("cash_below_target_cap")

    return tuple(blockers)


def _decision_from_blockers(
    *,
    reset_blockers: tuple[str, ...],
    symbol_blockers: tuple[str, ...],
    cap_blockers: tuple[str, ...],
    signal_blockers: tuple[str, ...],
    operator_blockers: tuple[str, ...],
) -> str:
    if reset_blockers:
        return _BLOCKED_RESET_DECISION
    if symbol_blockers:
        return _BLOCKED_SYMBOL_DECISION
    if cap_blockers:
        return _BLOCKED_CAP_DECISION
    if signal_blockers:
        return _BLOCKED_SIGNAL_DECISION
    if operator_blockers:
        return _OPERATOR_REVIEW_DECISION

    return _READY_DECISION


def _reason(decision: str) -> str:
    if decision == _READY_DECISION:
        return (
            "M366 flat-clean reset, SPY-only scope, valid cap, no positions or "
            "open orders, and actionable offline ETF/SMA signal support only a "
            "separate M368 preview-only milestone."
        )
    if decision == _BLOCKED_RESET_DECISION:
        return "Paper reset evidence is not flat and clean, or positions/orders remain."
    if decision == _BLOCKED_SYMBOL_DECISION:
        return "Review scope is not exactly SPY with a SPY-only allowlist."
    if decision == _BLOCKED_CAP_DECISION:
        return "Target cap is missing, non-positive, or above the USD 25.00 limit."
    if decision == _BLOCKED_SIGNAL_DECISION:
        return "Offline ETF/SMA signal status is missing, stale, risk-off, or not actionable."
    if decision == _OPERATOR_REVIEW_DECISION:
        return "Inputs are offline-safe but incomplete for a broker-facing preview decision."

    raise ValidationError("decision must be supported.")


def _required_next_milestone(decision: str) -> str:
    if decision == _READY_DECISION:
        return _READY_NEXT_MILESTONE
    if decision == _OPERATOR_REVIEW_DECISION:
        return _OPERATOR_NEXT_MILESTONE
    if decision in (
        _BLOCKED_RESET_DECISION,
        _BLOCKED_SYMBOL_DECISION,
        _BLOCKED_CAP_DECISION,
        _BLOCKED_SIGNAL_DECISION,
    ):
        return _BLOCKED_NEXT_MILESTONE

    raise ValidationError("decision must be supported.")


def _validate_review_consistency(review: EtfSmaNextExperimentReview) -> None:
    expected_next = _required_next_milestone(review.decision)
    expected_preview_allowed = review.decision == _READY_DECISION

    if review.required_next_milestone != expected_next:
        raise ValidationError("required_next_milestone must match the decision.")
    if review.separate_broker_preview_milestone_allowed != expected_preview_allowed:
        raise ValidationError(
            "separate_broker_preview_milestone_allowed must match the decision."
        )
    if review.decision == _READY_DECISION and review.blockers:
        raise ValidationError("ready reviews must not contain blockers.")
    if review.decision != _READY_DECISION and not review.blockers:
        raise ValidationError("blocked/operator reviews must contain blockers.")
    if review.decision == _READY_DECISION:
        _validate_ready_review(review)


def _validate_ready_review(review: EtfSmaNextExperimentReview) -> None:
    if review.paper_reset_classification != _CLEAN_RESET_CLASSIFICATION:
        raise ValidationError("ready reviews require a flat-clean reset.")
    if review.position_count != 0:
        raise ValidationError("ready reviews require zero positions.")
    if review.open_order_count != 0:
        raise ValidationError("ready reviews require zero open orders.")
    if review.symbol != "SPY" or review.allowlist != ("SPY",):
        raise ValidationError("ready reviews require SPY-only scope.")
    if review.asset_class != "equity":
        raise ValidationError("ready reviews require equity asset class.")
    if review.target_cap is None or review.target_cap <= _ZERO:
        raise ValidationError("ready reviews require a positive cap.")
    if review.target_cap > _MAX_TARGET_CAP:
        raise ValidationError("ready reviews require a cap no greater than USD 25.00.")
    if review.signal_status not in _ACTIONABLE_SIGNAL_STATUSES:
        raise ValidationError("ready reviews require an actionable signal status.")
    if review.safety_labels != ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS:
        raise ValidationError("ready reviews require the M367 safety labels.")


def _review_type(value: object) -> str:
    if value != _REVIEW_TYPE:
        raise ValidationError("review_type must be exactly etf_sma_next_experiment_review.")

    return _REVIEW_TYPE


def _decision(value: object) -> str:
    if type(value) is not str or value not in ETF_SMA_NEXT_EXPERIMENT_REVIEW_DECISIONS:
        allowed = ", ".join(ETF_SMA_NEXT_EXPERIMENT_REVIEW_DECISIONS)
        raise ValidationError(f"decision must be one of: {allowed}.")

    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None

    return _required_string(value, field_name)


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not allow_empty and not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")
    if len(frozenset(items)) != len(items):
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return items


def _symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    if symbol != symbol.upper():
        raise ValidationError("symbol must use uppercase deterministic text.")
    if any(character.isspace() for character in symbol):
        raise ValidationError("symbol must not contain whitespace.")

    return symbol


def _symbol_tuple(values: object, field_name: str) -> tuple[str, ...]:
    items = _string_tuple(values, field_name, allow_empty=False)
    return tuple(_symbol(item) for item in items)


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")

    return value


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")

    return False


def _limitations(values: object) -> tuple[str, ...]:
    limitations = _string_tuple(values, "limitations", allow_empty=False)
    missing = tuple(
        limitation
        for limitation in ETF_SMA_NEXT_EXPERIMENT_REVIEW_LIMITATIONS
        if limitation not in limitations
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(f"limitations missing required value(s): {missing_text}.")

    return limitations


def _merged_strings(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in groups:
        for item in group:
            checked_item = _required_string(item, "blocker")
            if checked_item not in merged:
                merged.append(checked_item)

    return tuple(merged)


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)
