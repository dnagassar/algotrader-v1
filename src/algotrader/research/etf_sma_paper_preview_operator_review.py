"""Offline ETF/SMA paper-preview operator-review contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_paper_preview_prompt_review import (
    ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS,
    EtfSmaPaperPreviewPromptReview,
)

__all__ = [
    "ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS",
    "ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LIMITATIONS",
    "ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_REQUIRED_CHECKS",
    "EtfSmaPaperPreviewOperatorReview",
    "EtfSmaPaperPreviewOperatorReviewConfig",
    "build_etf_sma_paper_preview_operator_review",
]


_OPERATOR_REVIEW_TYPE = "etf_sma_paper_preview_operator_review"
_SOURCE_READY_STATUS = "prompt_ready_for_operator_review"
_SOURCE_READY_NEXT_ACTION = "operator_review_before_separate_paper_preview_milestone"
_READY_STATUS = "authorize_separate_paper_preview_milestone"
_BLOCKED_STATUS = "blocked_from_separate_paper_preview_milestone"
_READY_NEXT_ACTION = "prepare_separate_etf_sma_paper_preview_milestone"
_BLOCKED_NEXT_ACTION = "resolve_prompt_review_blockers"
_SUPPORTED_POSTURES = (
    "bullish_trend_candidate",
    "defensive_or_cash_candidate",
    "insufficient_history",
)
_REQUIRED_TEMPLATE_MARKERS = (
    "<FUTURE_SEPARATE_MILESTONE_REQUIRED>",
    "<MANUAL_OPERATOR_REVIEW_REQUIRED>",
    "<FRESH_READ_ONLY_PAPER_SNAPSHOT_REQUIRED>",
    "<BROKER_PREVIEW_COMMAND_NOT_INCLUDED>",
    "<SUBMIT_FLAG_NOT_INCLUDED>",
)

ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS = (
    ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS
)
ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_REQUIRED_CHECKS = (
    "manual operator review before any future separate paper-preview milestone",
    "fresh read-only paper snapshot before any later broker-facing preview/probe milestone",
    "separate milestone required before broker-facing preview/probe work",
    "no broker action from this operator review",
    "no preview/staging from this operator review",
    "no submit authority from this operator review",
    "resolve M340 prompt-review blockers before preparing a separate milestone",
)
ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LIMITATIONS = (
    "offline_operator_review_only",
    "manual_operator_review_required",
    "fresh_read_only_paper_snapshot_required_before_later_broker_facing_preview",
    "not_live_authorization",
    "not_profit_evidence",
    "not_strategy_validation",
    "not_execution_authority",
    "no_broker_preview_authorized",
    "no_broker_action_authorized",
    "paper_preview_requires_separate_milestone",
    "submit_requires_separate_explicit_milestone",
)


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewOperatorReviewConfig:
    """Static offline gates for reviewing M340 prompt-review output."""

    required_future_operator_checks: tuple[
        str, ...
    ] = ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_REQUIRED_CHECKS
    additional_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_future_operator_checks",
            _future_operator_checks(self.required_future_operator_checks),
        )
        object.__setattr__(
            self,
            "additional_limitations",
            _string_tuple(
                self.additional_limitations,
                "additional_limitations",
                allow_empty=True,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only config metadata."""

        return {
            "required_future_operator_checks": list(
                self.required_future_operator_checks
            ),
            "additional_limitations": list(self.additional_limitations),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewOperatorReview:
    """Immutable operator review with no capital authority."""

    operator_review_type: str
    status: str
    operator_review_status: str
    authorize_separate_paper_preview_milestone: bool
    authorize_paper_preview_now: bool
    authorize_broker_action: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    submit_allowed: bool
    manual_operator_review_required: bool
    fresh_read_only_paper_snapshot_required: bool
    symbol: str
    strategy_name: str
    as_of: str
    source_prompt_review_type: str
    source_prompt_review_status: str
    source_prompt_review_required_next_action: str
    source_future_prompt_ready: bool
    source_labels: tuple[str, ...]
    source_prompt_review_source_labels: tuple[str, ...]
    labels: tuple[str, ...]
    latest_posture: str
    strategy_total_return: Decimal
    benchmark_total_return: Decimal
    max_drawdown: Decimal
    bar_count: int
    signal_count: int
    exposure_count: int
    defensive_count: int
    posture_change_count: int
    source_blocking_reasons: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    source_limitations: tuple[str, ...]
    limitations: tuple[str, ...]
    required_future_operator_checks: tuple[str, ...]
    future_operator_review_template: str
    required_next_action: str

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            operator_review_type=self.operator_review_type,
            status=self.status,
            operator_review_status=self.operator_review_status,
            authorize_separate_paper_preview_milestone=(
                self.authorize_separate_paper_preview_milestone
            ),
            authorize_paper_preview_now=self.authorize_paper_preview_now,
            authorize_broker_action=self.authorize_broker_action,
            broker_action_performed=self.broker_action_performed,
            broker_preview_performed=self.broker_preview_performed,
            submit_allowed=self.submit_allowed,
            manual_operator_review_required=self.manual_operator_review_required,
            fresh_read_only_paper_snapshot_required=(
                self.fresh_read_only_paper_snapshot_required
            ),
            labels=self.labels,
            required_next_action=self.required_next_action,
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
            "source_prompt_review_type",
            _required_string(
                self.source_prompt_review_type,
                "source_prompt_review_type",
            ),
        )
        object.__setattr__(
            self,
            "source_prompt_review_status",
            _required_string(
                self.source_prompt_review_status,
                "source_prompt_review_status",
            ),
        )
        object.__setattr__(
            self,
            "source_prompt_review_required_next_action",
            _required_string(
                self.source_prompt_review_required_next_action,
                "source_prompt_review_required_next_action",
            ),
        )
        object.__setattr__(
            self,
            "source_future_prompt_ready",
            _bool(self.source_future_prompt_ready, "source_future_prompt_ready"),
        )
        object.__setattr__(
            self,
            "source_labels",
            _label_tuple(self.source_labels, "source_labels"),
        )
        object.__setattr__(
            self,
            "source_prompt_review_source_labels",
            _label_tuple(
                self.source_prompt_review_source_labels,
                "source_prompt_review_source_labels",
            ),
        )
        object.__setattr__(self, "labels", _operator_review_labels(self.labels))
        object.__setattr__(self, "latest_posture", _posture(self.latest_posture))
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
        object.__setattr__(
            self,
            "bar_count",
            _non_negative_int(self.bar_count, "bar_count"),
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
            "source_blocking_reasons",
            _string_tuple(
                self.source_blocking_reasons,
                "source_blocking_reasons",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _string_tuple(
                self.blocking_reasons,
                "blocking_reasons",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "source_limitations",
            _string_tuple(
                self.source_limitations,
                "source_limitations",
                allow_empty=False,
            ),
        )
        object.__setattr__(self, "limitations", _limitations(self.limitations))
        object.__setattr__(
            self,
            "required_future_operator_checks",
            _future_operator_checks(self.required_future_operator_checks),
        )
        object.__setattr__(
            self,
            "future_operator_review_template",
            _future_operator_review_template_text(
                self.future_operator_review_template
            ),
        )
        _validate_operator_review_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only operator-review metadata."""

        return {
            "operator_review_type": self.operator_review_type,
            "status": self.status,
            "operator_review_status": self.operator_review_status,
            "authorize_separate_paper_preview_milestone": (
                self.authorize_separate_paper_preview_milestone
            ),
            "authorize_paper_preview_now": self.authorize_paper_preview_now,
            "authorize_broker_action": self.authorize_broker_action,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "submit_allowed": self.submit_allowed,
            "manual_operator_review_required": (
                self.manual_operator_review_required
            ),
            "fresh_read_only_paper_snapshot_required": (
                self.fresh_read_only_paper_snapshot_required
            ),
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "source_prompt_review_type": self.source_prompt_review_type,
            "source_prompt_review_status": self.source_prompt_review_status,
            "source_prompt_review_required_next_action": (
                self.source_prompt_review_required_next_action
            ),
            "source_future_prompt_ready": self.source_future_prompt_ready,
            "source_labels": list(self.source_labels),
            "source_prompt_review_source_labels": list(
                self.source_prompt_review_source_labels
            ),
            "labels": list(self.labels),
            "latest_posture": self.latest_posture,
            "strategy_total_return": str(self.strategy_total_return),
            "benchmark_total_return": str(self.benchmark_total_return),
            "max_drawdown": str(self.max_drawdown),
            "bar_count": self.bar_count,
            "signal_count": self.signal_count,
            "exposure_count": self.exposure_count,
            "defensive_count": self.defensive_count,
            "posture_change_count": self.posture_change_count,
            "source_blocking_reasons": list(self.source_blocking_reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "source_limitations": list(self.source_limitations),
            "limitations": list(self.limitations),
            "required_future_operator_checks": list(
                self.required_future_operator_checks
            ),
            "future_operator_review_template": (
                self.future_operator_review_template
            ),
            "required_next_action": self.required_next_action,
        }


def build_etf_sma_paper_preview_operator_review(
    prompt_review: EtfSmaPaperPreviewPromptReview,
    config: EtfSmaPaperPreviewOperatorReviewConfig,
) -> EtfSmaPaperPreviewOperatorReview:
    """Build an offline operator review only from an M340 prompt review."""

    checked_review = _prompt_review(prompt_review)
    checked_config = _config(config)
    source_labels = _label_tuple(checked_review.labels, "source_labels")
    source_prompt_review_source_labels = _label_tuple(
        checked_review.source_labels,
        "source_prompt_review_source_labels",
    )
    source_limitations = _string_tuple(
        checked_review.limitations,
        "source_limitations",
        allow_empty=False,
    )
    source_blocking_reasons = _string_tuple(
        checked_review.blocking_reasons,
        "source_blocking_reasons",
        allow_empty=True,
    )
    blocking_reasons = _blocking_reasons(
        checked_review,
        source_labels,
        source_prompt_review_source_labels,
        source_blocking_reasons,
    )
    status = _BLOCKED_STATUS if blocking_reasons else _READY_STATUS
    required_next_action = (
        _BLOCKED_NEXT_ACTION if blocking_reasons else _READY_NEXT_ACTION
    )
    authorize_separate_milestone = not blocking_reasons

    return EtfSmaPaperPreviewOperatorReview(
        operator_review_type=_OPERATOR_REVIEW_TYPE,
        status=status,
        operator_review_status=status,
        authorize_separate_paper_preview_milestone=authorize_separate_milestone,
        authorize_paper_preview_now=False,
        authorize_broker_action=False,
        broker_action_performed=False,
        broker_preview_performed=False,
        submit_allowed=False,
        manual_operator_review_required=True,
        fresh_read_only_paper_snapshot_required=True,
        symbol=checked_review.symbol,
        strategy_name=checked_review.strategy_name,
        as_of=checked_review.as_of,
        source_prompt_review_type=checked_review.prompt_review_type,
        source_prompt_review_status=checked_review.status,
        source_prompt_review_required_next_action=checked_review.required_next_action,
        source_future_prompt_ready=checked_review.future_prompt_ready,
        source_labels=source_labels,
        source_prompt_review_source_labels=source_prompt_review_source_labels,
        labels=ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS,
        latest_posture=checked_review.latest_posture,
        strategy_total_return=checked_review.strategy_total_return,
        benchmark_total_return=checked_review.benchmark_total_return,
        max_drawdown=checked_review.max_drawdown,
        bar_count=checked_review.bar_count,
        signal_count=checked_review.signal_count,
        exposure_count=checked_review.exposure_count,
        defensive_count=checked_review.defensive_count,
        posture_change_count=checked_review.posture_change_count,
        source_blocking_reasons=source_blocking_reasons,
        blocking_reasons=blocking_reasons,
        source_limitations=source_limitations,
        limitations=_merged_strings(
            source_limitations,
            ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LIMITATIONS,
            checked_config.additional_limitations,
        ),
        required_future_operator_checks=(
            checked_config.required_future_operator_checks
        ),
        future_operator_review_template=_future_operator_review_template(),
        required_next_action=required_next_action,
    )


def _prompt_review(value: object) -> EtfSmaPaperPreviewPromptReview:
    if type(value) is not EtfSmaPaperPreviewPromptReview:
        raise ValidationError(
            "prompt_review must be an EtfSmaPaperPreviewPromptReview."
        )

    return value


def _config(value: object) -> EtfSmaPaperPreviewOperatorReviewConfig:
    if type(value) is not EtfSmaPaperPreviewOperatorReviewConfig:
        raise ValidationError(
            "config must be an EtfSmaPaperPreviewOperatorReviewConfig."
        )

    return value


def _blocking_reasons(
    prompt_review: EtfSmaPaperPreviewPromptReview,
    source_labels: tuple[str, ...],
    source_prompt_review_source_labels: tuple[str, ...],
    source_blocking_reasons: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if prompt_review.status != _SOURCE_READY_STATUS:
        reasons.append("source_prompt_review_not_ready")
    if prompt_review.prompt_review_status != prompt_review.status:
        reasons.append("source_prompt_review_status_mismatch")
    if prompt_review.prompt_review_status != _SOURCE_READY_STATUS:
        reasons.append("source_prompt_review_status_not_ready")
    if prompt_review.future_prompt_ready is not True:
        reasons.append("source_future_prompt_not_ready")
    if prompt_review.required_next_action != _SOURCE_READY_NEXT_ACTION:
        reasons.append("source_prompt_review_required_next_action_unexpected")
    reasons.extend(source_blocking_reasons)

    for label in ("research_only", "paper_lab_candidate", "not_live_authorized"):
        if label not in source_labels:
            reasons.append(f"source_missing_{label}_label")
        if label not in source_prompt_review_source_labels:
            reasons.append(f"source_prompt_review_source_missing_{label}_label")
    if "profit_claim=none" not in source_labels:
        reasons.append("source_missing_profit_claim_none_label")
    if "profit_claim=none" not in source_prompt_review_source_labels:
        reasons.append("source_prompt_review_source_missing_profit_claim_none_label")

    if _has_live_authorized_text(
        source_labels,
        source_prompt_review_source_labels,
    ) or _has_live_authorized_status(prompt_review):
        reasons.append("source_contains_live_authorized")
    if _has_profit_claim_other_than_none(
        source_labels,
        source_prompt_review_source_labels,
    ):
        reasons.append("source_contains_profit_claim_other_than_none")
    if prompt_review.latest_posture == "insufficient_history":
        reasons.append("source_insufficient_history_posture")
    if prompt_review.latest_posture == "defensive_or_cash_candidate":
        reasons.append("source_defensive_posture")

    return _dedupe(reasons)


def _future_operator_review_template() -> str:
    return "\n".join(
        (
            "ETF/SMA paper-preview operator review for a future milestone.",
            "Decision scope: prepare a separate future paper-preview milestone.",
            "Separate milestone: <FUTURE_SEPARATE_MILESTONE_REQUIRED>",
            "Manual review: <MANUAL_OPERATOR_REVIEW_REQUIRED>",
            "Fresh snapshot: <FRESH_READ_ONLY_PAPER_SNAPSHOT_REQUIRED>",
            "Preview placeholder: <BROKER_PREVIEW_COMMAND_NOT_INCLUDED>",
            "Submit placeholder: <SUBMIT_FLAG_NOT_INCLUDED>",
            "No executable command is included in this review packet.",
        )
    )


def _validate_fixed_metadata(
    *,
    operator_review_type: object,
    status: object,
    operator_review_status: object,
    authorize_separate_paper_preview_milestone: object,
    authorize_paper_preview_now: object,
    authorize_broker_action: object,
    broker_action_performed: object,
    broker_preview_performed: object,
    submit_allowed: object,
    manual_operator_review_required: object,
    fresh_read_only_paper_snapshot_required: object,
    labels: object,
    required_next_action: object,
) -> None:
    if operator_review_type != _OPERATOR_REVIEW_TYPE:
        raise ValidationError(
            "operator_review_type must be exactly "
            "etf_sma_paper_preview_operator_review."
        )
    if status not in (_READY_STATUS, _BLOCKED_STATUS):
        raise ValidationError("status must be a supported operator review status.")
    if operator_review_status != status:
        raise ValidationError("operator_review_status must match status.")
    _validate_safety_bool(
        authorize_paper_preview_now,
        "authorize_paper_preview_now",
        expected=False,
    )
    _validate_safety_bool(
        authorize_broker_action,
        "authorize_broker_action",
        expected=False,
    )
    _validate_safety_bool(
        broker_action_performed,
        "broker_action_performed",
        expected=False,
    )
    _validate_safety_bool(
        broker_preview_performed,
        "broker_preview_performed",
        expected=False,
    )
    _validate_safety_bool(submit_allowed, "submit_allowed", expected=False)
    _validate_safety_bool(
        manual_operator_review_required,
        "manual_operator_review_required",
        expected=True,
    )
    _validate_safety_bool(
        fresh_read_only_paper_snapshot_required,
        "fresh_read_only_paper_snapshot_required",
        expected=True,
    )
    _validate_safety_bool(
        authorize_separate_paper_preview_milestone,
        "authorize_separate_paper_preview_milestone",
        expected=status == _READY_STATUS,
    )
    if _operator_review_labels(labels) != ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS:
        raise ValidationError("labels must preserve the ETF/SMA label set.")
    if status == _READY_STATUS and required_next_action != _READY_NEXT_ACTION:
        raise ValidationError(
            "ready operator reviews must prepare a separate milestone."
        )
    if status == _BLOCKED_STATUS and required_next_action != _BLOCKED_NEXT_ACTION:
        raise ValidationError(
            "blocked operator reviews must resolve prompt-review blockers."
        )


def _validate_operator_review_consistency(
    review: EtfSmaPaperPreviewOperatorReview,
) -> None:
    if review.exposure_count + review.defensive_count != review.bar_count:
        raise ValidationError(
            "exposure_count plus defensive_count must equal bar_count."
        )
    if review.signal_count > review.bar_count:
        raise ValidationError("signal_count must not exceed bar_count.")
    if review.posture_change_count > review.bar_count:
        raise ValidationError("posture_change_count must not exceed bar_count.")
    if review.status == _READY_STATUS and review.blocking_reasons:
        raise ValidationError("ready operator reviews must not contain blockers.")
    if review.status == _BLOCKED_STATUS and not review.blocking_reasons:
        raise ValidationError("blocked operator reviews must contain blockers.")
    if review.status == _READY_STATUS:
        _validate_ready_source(review)


def _validate_ready_source(review: EtfSmaPaperPreviewOperatorReview) -> None:
    if review.source_prompt_review_status != _SOURCE_READY_STATUS:
        raise ValidationError(
            "ready operator reviews require a ready prompt review."
        )
    if not review.source_future_prompt_ready:
        raise ValidationError("ready operator reviews require ready source output.")
    if review.source_prompt_review_required_next_action != _SOURCE_READY_NEXT_ACTION:
        raise ValidationError(
            "ready operator reviews require the M340 next action."
        )
    for label in ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS:
        if label not in review.source_labels:
            raise ValidationError(
                "ready operator reviews require all source labels."
            )
        if label not in review.source_prompt_review_source_labels:
            raise ValidationError(
                "ready operator reviews require all source prompt-review labels."
            )
    if _has_live_authorized_text(
        review.source_labels,
        review.source_prompt_review_source_labels,
    ):
        raise ValidationError("ready operator reviews cannot contain live authority.")
    if _has_profit_claim_other_than_none(
        review.source_labels,
        review.source_prompt_review_source_labels,
    ):
        raise ValidationError("ready operator reviews cannot contain a profit claim.")
    if review.latest_posture != "bullish_trend_candidate":
        raise ValidationError("ready operator reviews require bullish research posture.")


def _future_operator_review_template_text(value: object) -> str:
    template = _required_string(value, "future_operator_review_template")
    missing = tuple(
        marker for marker in _REQUIRED_TEMPLATE_MARKERS if marker not in template
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            "future_operator_review_template missing marker(s): "
            f"{missing_text}."
        )
    if _contains_submit_flag(template):
        raise ValidationError(
            "future_operator_review_template must not include a submit flag."
        )
    if _contains_executable_command(template):
        raise ValidationError(
            "future_operator_review_template must not include executable commands."
        )

    return template


def _contains_submit_flag(value: str) -> bool:
    lowered = value.lower()
    forbidden_patterns = (
        "--submit",
        "submit=true",
        "submit = true",
        "submit: true",
        "submit=yes",
        "submit = yes",
        "submit: yes",
        "submit=1",
        "submit = 1",
        "submit: 1",
    )

    return any(pattern in lowered for pattern in forbidden_patterns)


def _contains_executable_command(value: str) -> bool:
    lowered = value.lower()
    forbidden_patterns = (
        "submit_order",
        "create_order",
        "cancel_order",
        "replace_order",
        "close_position",
        "liquidate",
        "preview_order",
        "stage_order",
        "python -m",
    )

    return any(pattern in lowered for pattern in forbidden_patterns)


def _validate_safety_bool(value: object, field_name: str, *, expected: bool) -> None:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    if value is not expected:
        expected_text = str(expected).lower()
        raise ValidationError(f"{field_name} must be {expected_text}.")


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")

    return value


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

    return items


def _symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    normalized = symbol.upper()
    if normalized != symbol:
        raise ValidationError("symbol must use uppercase deterministic text.")
    if any(character.isspace() for character in normalized):
        raise ValidationError("symbol must not contain whitespace.")

    return normalized


def _posture(value: object) -> str:
    posture = _required_string(value, "latest_posture")
    if posture not in _SUPPORTED_POSTURES:
        allowed = ", ".join(_SUPPORTED_POSTURES)
        raise ValidationError(f"latest_posture must be one of: {allowed}.")

    return posture


def _decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal(value, field_name)
    if decimal_value < Decimal("0"):
        raise ValidationError(f"{field_name} must be non-negative.")

    return decimal_value


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _label_tuple(values: object, field_name: str) -> tuple[str, ...]:
    labels = _string_tuple(values, field_name, allow_empty=False)
    if len(frozenset(labels)) != len(labels):
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return labels


def _operator_review_labels(values: object) -> tuple[str, ...]:
    labels = _label_tuple(values, "labels")
    if labels != ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS:
        raise ValidationError("labels must match the ETF/SMA operator label set.")

    return labels


def _limitations(values: object) -> tuple[str, ...]:
    limitations = _string_tuple(values, "limitations", allow_empty=False)
    missing = tuple(
        limitation
        for limitation in ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LIMITATIONS
        if limitation not in limitations
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(f"limitations missing required value(s): {missing_text}.")
    if len(frozenset(limitations)) != len(limitations):
        raise ValidationError("limitations must not contain duplicates.")

    return limitations


def _future_operator_checks(values: object) -> tuple[str, ...]:
    checks = _string_tuple(
        values,
        "required_future_operator_checks",
        allow_empty=False,
    )
    missing = tuple(
        check
        for check in ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_REQUIRED_CHECKS
        if check not in checks
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            "required_future_operator_checks missing required value(s): "
            f"{missing_text}."
        )
    if len(frozenset(checks)) != len(checks):
        raise ValidationError("required_future_operator_checks must not duplicate.")

    return checks


def _has_live_authorized_status(
    prompt_review: EtfSmaPaperPreviewPromptReview,
) -> bool:
    return any(
        _is_live_authorized_text(text)
        for text in (
            prompt_review.status,
            prompt_review.prompt_review_status,
            prompt_review.required_next_action,
            prompt_review.source_design_status,
            prompt_review.source_design_required_next_action,
            prompt_review.latest_posture,
        )
    )


def _has_live_authorized_text(*label_groups: tuple[str, ...]) -> bool:
    return any(
        _is_live_authorized_text(label)
        for labels in label_groups
        for label in labels
    )


def _is_live_authorized_text(value: str) -> bool:
    if value.startswith("not_live_authorized"):
        return False
    if value.startswith("not_live_authorization"):
        return False

    return "live_authorized" in value


def _has_profit_claim_other_than_none(*label_groups: tuple[str, ...]) -> bool:
    return any(
        label.startswith("profit_claim=") and label != "profit_claim=none"
        for labels in label_groups
        for label in labels
    )


def _merged_strings(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in groups:
        for item in _string_tuple(group, "string_group", allow_empty=True):
            if item not in merged:
                merged.append(item)

    return tuple(merged)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        checked_value = _required_string(value, "blocking_reason")
        if checked_value not in deduped:
            deduped.append(checked_value)

    return tuple(deduped)
