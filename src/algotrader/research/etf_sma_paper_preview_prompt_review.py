"""Offline ETF/SMA paper-preview prompt-review contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_paper_preview_design import (
    ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS,
    EtfSmaPaperPreviewDesign,
)

__all__ = [
    "ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS",
    "ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LIMITATIONS",
    "ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_OPERATOR_CHECKLIST",
    "EtfSmaPaperPreviewPromptReview",
    "EtfSmaPaperPreviewPromptReviewConfig",
    "build_etf_sma_paper_preview_prompt_review",
]


_PROMPT_REVIEW_TYPE = "etf_sma_paper_lab_preview_prompt_review"
_SOURCE_READY_STATUS = "ready_for_paper_lab_preview_prompt_review"
_SOURCE_READY_NEXT_ACTION = "draft_separate_paper_lab_preview_prompt"
_READY_STATUS = "prompt_ready_for_operator_review"
_BLOCKED_STATUS = "blocked_from_prompt_review"
_READY_NEXT_ACTION = "operator_review_before_separate_paper_preview_milestone"
_BLOCKED_NEXT_ACTION = "resolve_paper_preview_design_blockers"
_SUPPORTED_POSTURES = (
    "bullish_trend_candidate",
    "defensive_or_cash_candidate",
    "insufficient_history",
)
_REQUIRED_PROMPT_PLACEHOLDERS = (
    "<FUTURE_SEPARATE_MILESTONE_REQUIRED>",
    "<BROKER_PREVIEW_COMMAND_NOT_INCLUDED>",
    "<SUBMIT_FLAG_NOT_INCLUDED>",
    "<PAPER_PROFILE_REQUIRED>",
    "<FRESH_READ_ONLY_SNAPSHOT_REQUIRED>",
)

ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS = ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS
ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_OPERATOR_CHECKLIST = (
    "confirm paper profile only",
    "run fresh read-only paper snapshot before any future broker-facing preview",
    "confirm no open conflicting orders before future preview",
    "explicit operator approval required before broker-facing preview",
    "separate milestone required before broker-facing preview",
    "separate milestone required before any submit",
    "no live trading authorization",
    "stop on ambiguous broker response",
    "no retry/cancel/liquidate/fix-forward without separate explicit milestone",
)
ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LIMITATIONS = (
    "offline_prompt_review_only",
    "not_profit_evidence",
    "no_broker_preview_authorized",
    "no_broker_action_authorized",
    "paper_preview_requires_separate_milestone",
    "submit_requires_separate_explicit_milestone",
    "not_live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewPromptReviewConfig:
    """Static offline gates for reviewing a future paper-preview prompt."""

    future_operator_checklist: tuple[
        str, ...
    ] = ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_OPERATOR_CHECKLIST
    additional_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "future_operator_checklist",
            _future_operator_checklist(self.future_operator_checklist),
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
            "future_operator_checklist": list(self.future_operator_checklist),
            "additional_limitations": list(self.additional_limitations),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewPromptReview:
    """Immutable review packet for a future operator-facing prompt."""

    prompt_review_type: str
    status: str
    prompt_review_status: str
    future_prompt_ready: bool
    symbol: str
    strategy_name: str
    as_of: str
    source_design_status: str
    source_design_required_next_action: str
    source_labels: tuple[str, ...]
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
    blocking_reasons: tuple[str, ...]
    source_limitations: tuple[str, ...]
    limitations: tuple[str, ...]
    future_operator_checklist: tuple[str, ...]
    future_prompt_template: str
    required_next_action: str

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            prompt_review_type=self.prompt_review_type,
            status=self.status,
            prompt_review_status=self.prompt_review_status,
            future_prompt_ready=self.future_prompt_ready,
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
            "source_design_status",
            _required_string(self.source_design_status, "source_design_status"),
        )
        object.__setattr__(
            self,
            "source_design_required_next_action",
            _required_string(
                self.source_design_required_next_action,
                "source_design_required_next_action",
            ),
        )
        object.__setattr__(
            self,
            "source_labels",
            _label_tuple(self.source_labels, "source_labels"),
        )
        object.__setattr__(self, "labels", _prompt_review_labels(self.labels))
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
            "future_operator_checklist",
            _future_operator_checklist(self.future_operator_checklist),
        )
        object.__setattr__(
            self,
            "future_prompt_template",
            _future_prompt_template_text(self.future_prompt_template),
        )
        _validate_prompt_review_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only prompt-review metadata."""

        return {
            "prompt_review_type": self.prompt_review_type,
            "status": self.status,
            "prompt_review_status": self.prompt_review_status,
            "future_prompt_ready": self.future_prompt_ready,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "source_design_status": self.source_design_status,
            "source_design_required_next_action": (
                self.source_design_required_next_action
            ),
            "source_labels": list(self.source_labels),
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
            "blocking_reasons": list(self.blocking_reasons),
            "source_limitations": list(self.source_limitations),
            "limitations": list(self.limitations),
            "future_operator_checklist": list(self.future_operator_checklist),
            "future_prompt_template": self.future_prompt_template,
            "required_next_action": self.required_next_action,
        }


def build_etf_sma_paper_preview_prompt_review(
    design: EtfSmaPaperPreviewDesign,
    config: EtfSmaPaperPreviewPromptReviewConfig,
) -> EtfSmaPaperPreviewPromptReview:
    """Build an offline prompt review only from an M339 preview design."""

    checked_design = _design(design)
    checked_config = _config(config)
    source_labels = _label_tuple(checked_design.labels, "source_labels")
    source_limitations = _string_tuple(
        checked_design.limitations,
        "source_limitations",
        allow_empty=False,
    )
    blocking_reasons = _blocking_reasons(checked_design, source_labels)
    status = _BLOCKED_STATUS if blocking_reasons else _READY_STATUS
    future_prompt_ready = not blocking_reasons
    required_next_action = (
        _BLOCKED_NEXT_ACTION if blocking_reasons else _READY_NEXT_ACTION
    )

    return EtfSmaPaperPreviewPromptReview(
        prompt_review_type=_PROMPT_REVIEW_TYPE,
        status=status,
        prompt_review_status=status,
        future_prompt_ready=future_prompt_ready,
        symbol=checked_design.symbol,
        strategy_name=checked_design.strategy_name,
        as_of=checked_design.as_of,
        source_design_status=checked_design.status,
        source_design_required_next_action=checked_design.required_next_action,
        source_labels=source_labels,
        labels=ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS,
        latest_posture=checked_design.latest_posture,
        strategy_total_return=checked_design.strategy_total_return,
        benchmark_total_return=checked_design.benchmark_total_return,
        max_drawdown=checked_design.max_drawdown,
        bar_count=checked_design.bar_count,
        signal_count=checked_design.signal_count,
        exposure_count=checked_design.exposure_count,
        defensive_count=checked_design.defensive_count,
        posture_change_count=checked_design.posture_change_count,
        blocking_reasons=blocking_reasons,
        source_limitations=source_limitations,
        limitations=_merged_strings(
            source_limitations,
            ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LIMITATIONS,
            checked_config.additional_limitations,
        ),
        future_operator_checklist=checked_config.future_operator_checklist,
        future_prompt_template=_future_prompt_template(),
        required_next_action=required_next_action,
    )


def _design(value: object) -> EtfSmaPaperPreviewDesign:
    if type(value) is not EtfSmaPaperPreviewDesign:
        raise ValidationError("design must be an EtfSmaPaperPreviewDesign.")

    return value


def _config(value: object) -> EtfSmaPaperPreviewPromptReviewConfig:
    if type(value) is not EtfSmaPaperPreviewPromptReviewConfig:
        raise ValidationError(
            "config must be an EtfSmaPaperPreviewPromptReviewConfig."
        )

    return value


def _blocking_reasons(
    design: EtfSmaPaperPreviewDesign,
    source_labels: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    source_blockers = _string_tuple(
        design.blocking_reasons,
        "source_blocking_reasons",
        allow_empty=True,
    )

    if design.status != _SOURCE_READY_STATUS:
        reasons.append("source_design_not_ready_for_prompt_review")
    if design.required_next_action != _SOURCE_READY_NEXT_ACTION:
        reasons.append("source_design_required_next_action_unexpected")
    reasons.extend(source_blockers)

    if "research_only" not in source_labels:
        reasons.append("source_missing_research_only_label")
    if "paper_lab_candidate" not in source_labels:
        reasons.append("source_missing_paper_lab_candidate_label")
    if "not_live_authorized" not in source_labels:
        reasons.append("source_missing_not_live_authorized_label")
    if "profit_claim=none" not in source_labels:
        reasons.append("source_missing_profit_claim_none_label")
    if any(_is_live_authorized_text(label) for label in source_labels):
        reasons.append("source_contains_live_authorized")
    if _has_live_authorized_status(design):
        reasons.append("source_contains_live_authorized")
    if _has_profit_claim_other_than_none(source_labels):
        reasons.append("source_contains_profit_claim_other_than_none")
    if design.latest_posture == "insufficient_history":
        reasons.append("source_insufficient_history_posture")
    if design.latest_posture == "defensive_or_cash_candidate":
        reasons.append("source_defensive_posture")

    return _dedupe(reasons)


def _future_prompt_template() -> str:
    return "\n".join(
        (
            "ETF/SMA paper-lab preview prompt draft for a future milestone.",
            "Use the M340 review packet fields for symbol, posture, returns, "
            "drawdown, counts, labels, limitations, and blockers.",
            "Separate milestone: <FUTURE_SEPARATE_MILESTONE_REQUIRED>",
            "Paper profile: <PAPER_PROFILE_REQUIRED>",
            "Fresh snapshot: <FRESH_READ_ONLY_SNAPSHOT_REQUIRED>",
            "Preview placeholder: <BROKER_PREVIEW_COMMAND_NOT_INCLUDED>",
            "Submit placeholder: <SUBMIT_FLAG_NOT_INCLUDED>",
            "Operator review is required before any separate paper-only "
            "preview milestone.",
        )
    )


def _validate_fixed_metadata(
    *,
    prompt_review_type: object,
    status: object,
    prompt_review_status: object,
    future_prompt_ready: object,
    labels: object,
    required_next_action: object,
) -> None:
    if prompt_review_type != _PROMPT_REVIEW_TYPE:
        raise ValidationError(
            "prompt_review_type must be exactly "
            "etf_sma_paper_lab_preview_prompt_review."
        )
    if status not in (_READY_STATUS, _BLOCKED_STATUS):
        raise ValidationError("status must be a supported prompt review status.")
    if prompt_review_status != status:
        raise ValidationError("prompt_review_status must match status.")
    if type(future_prompt_ready) is not bool:
        raise ValidationError("future_prompt_ready must be a bool.")
    if status == _READY_STATUS and not future_prompt_ready:
        raise ValidationError("ready prompt reviews must set future_prompt_ready.")
    if status == _BLOCKED_STATUS and future_prompt_ready:
        raise ValidationError("blocked prompt reviews cannot be prompt-ready.")
    if _prompt_review_labels(labels) != ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS:
        raise ValidationError("labels must preserve the ETF/SMA label set.")
    if status == _READY_STATUS and required_next_action != _READY_NEXT_ACTION:
        raise ValidationError(
            "ready prompt reviews must require operator review first."
        )
    if status == _BLOCKED_STATUS and required_next_action != _BLOCKED_NEXT_ACTION:
        raise ValidationError(
            "blocked prompt reviews must resolve preview design blockers."
        )


def _validate_prompt_review_consistency(
    review: EtfSmaPaperPreviewPromptReview,
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
        raise ValidationError("ready prompt reviews must not contain blockers.")
    if review.status == _BLOCKED_STATUS and not review.blocking_reasons:
        raise ValidationError("blocked prompt reviews must contain blockers.")
    if review.status == _READY_STATUS:
        _validate_ready_source(review)


def _validate_ready_source(review: EtfSmaPaperPreviewPromptReview) -> None:
    if review.source_design_status != _SOURCE_READY_STATUS:
        raise ValidationError("ready prompt reviews require a ready source design.")
    if review.source_design_required_next_action != _SOURCE_READY_NEXT_ACTION:
        raise ValidationError("ready prompt reviews require the M339 next action.")
    for label in ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS:
        if label not in review.source_labels:
            raise ValidationError("ready prompt reviews require all source labels.")
    if any(_is_live_authorized_text(label) for label in review.source_labels):
        raise ValidationError("ready prompt reviews cannot contain live authority.")
    if _has_profit_claim_other_than_none(review.source_labels):
        raise ValidationError("ready prompt reviews cannot contain a profit claim.")
    if review.latest_posture != "bullish_trend_candidate":
        raise ValidationError("ready prompt reviews require bullish research posture.")


def _future_prompt_template_text(value: object) -> str:
    template = _required_string(value, "future_prompt_template")
    missing = tuple(
        placeholder
        for placeholder in _REQUIRED_PROMPT_PLACEHOLDERS
        if placeholder not in template
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"future_prompt_template missing placeholder(s): {missing_text}."
        )
    if _contains_submit_flag(template):
        raise ValidationError("future_prompt_template must not include a submit flag.")
    if _contains_broker_execution_command(template):
        raise ValidationError(
            "future_prompt_template must not include executable broker commands."
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


def _contains_broker_execution_command(value: str) -> bool:
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
        "alpaca",
    )

    return any(pattern in lowered for pattern in forbidden_patterns)


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


def _prompt_review_labels(values: object) -> tuple[str, ...]:
    labels = _label_tuple(values, "labels")
    if labels != ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS:
        raise ValidationError("labels must match the ETF/SMA prompt review labels.")

    return labels


def _limitations(values: object) -> tuple[str, ...]:
    limitations = _string_tuple(values, "limitations", allow_empty=False)
    missing = tuple(
        limitation
        for limitation in ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LIMITATIONS
        if limitation not in limitations
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(f"limitations missing required value(s): {missing_text}.")
    if len(frozenset(limitations)) != len(limitations):
        raise ValidationError("limitations must not contain duplicates.")

    return limitations


def _future_operator_checklist(values: object) -> tuple[str, ...]:
    checklist = _string_tuple(values, "future_operator_checklist", allow_empty=False)
    missing = tuple(
        item
        for item in ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_OPERATOR_CHECKLIST
        if item not in checklist
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"future_operator_checklist missing required value(s): {missing_text}."
        )
    if len(frozenset(checklist)) != len(checklist):
        raise ValidationError("future_operator_checklist must not duplicate.")

    return checklist


def _has_live_authorized_status(design: EtfSmaPaperPreviewDesign) -> bool:
    return any(
        _is_live_authorized_text(text)
        for text in (
            design.status,
            design.preview_design_status,
            design.required_next_action,
            design.latest_posture,
        )
    )


def _is_live_authorized_text(value: str) -> bool:
    if value.startswith("not_live_authorized"):
        return False

    return "live_authorized" in value


def _has_profit_claim_other_than_none(labels: tuple[str, ...]) -> bool:
    return any(
        label.startswith("profit_claim=") and label != "profit_claim=none"
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
