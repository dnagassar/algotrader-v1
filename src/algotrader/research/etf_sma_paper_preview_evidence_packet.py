"""Offline ETF/SMA paper-preview evidence packet contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_paper_preview_operator_review import (
    ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS,
    EtfSmaPaperPreviewOperatorReview,
)

__all__ = [
    "ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS",
    "ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LIMITATIONS",
    "ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_REQUIRED_FUTURE_PREREQUISITES",
    "EtfSmaPaperPreviewEvidencePacket",
    "EtfSmaPaperPreviewEvidencePacketConfig",
    "build_etf_sma_paper_preview_evidence_packet",
]


_EVIDENCE_PACKET_VERSION = "etf_sma_paper_preview_evidence_packet_v1"
_EVIDENCE_SCOPE = "local_research_to_paper_preview_preparation_only"
_SOURCE_READY_STATUS = "authorize_separate_paper_preview_milestone"
_SOURCE_READY_NEXT_ACTION = "prepare_separate_etf_sma_paper_preview_milestone"
_READY_STATUS = "ready_for_separate_paper_preview_preparation"
_BLOCKED_STATUS = "blocked_from_separate_paper_preview_preparation"
_READY_NEXT_ACTION = "draft_separate_etf_sma_paper_preview_milestone"
_BLOCKED_NEXT_ACTION = "resolve_operator_review_blockers"
_SUPPORTED_POSTURES = (
    "bullish_trend_candidate",
    "defensive_or_cash_candidate",
    "insufficient_history",
)
_REQUIRED_TEMPLATE_MARKERS = (
    "<SEPARATE_PAPER_PREVIEW_MILESTONE_REQUIRED>",
    "<MANUAL_OPERATOR_REVIEW_REQUIRED>",
    "<FRESH_READ_ONLY_PAPER_SNAPSHOT_REQUIRED>",
    "<EXPLICIT_OPERATOR_APPROVAL_REQUIRED>",
    "<BROKER_FACING_PREVIEW_NOT_INCLUDED>",
    "<SUBMIT_FLAG_NOT_INCLUDED>",
)

ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS = (
    ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS
)
ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_REQUIRED_FUTURE_PREREQUISITES = (
    "manual_operator_review_required",
    "fresh_read_only_paper_snapshot_required",
    "separate_paper_preview_milestone_required",
    "explicit_operator_approval_required_before_any_broker_facing_preview",
)
ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LIMITATIONS = (
    "local_advisory_evidence_only",
    "not_live_authorized",
    "not_profit_evidence",
    "not_strategy_validation",
    "not_execution_authority",
    "not_broker_order_fill_account_portfolio_evidence",
    "paper_preview_requires_separate_milestone",
    "broker_facing_preview_requires_separate_milestone",
    "submit_requires_separate_explicit_milestone",
)


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewEvidencePacketConfig:
    """Static offline gates for packaging M341 operator-review evidence."""

    required_future_prerequisites: tuple[
        str, ...
    ] = ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_REQUIRED_FUTURE_PREREQUISITES
    additional_limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_future_prerequisites",
            _future_prerequisites(self.required_future_prerequisites),
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
            "required_future_prerequisites": list(
                self.required_future_prerequisites
            ),
            "additional_limitations": list(self.additional_limitations),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewEvidencePacket:
    """Immutable local evidence packet with no broker-facing authority."""

    evidence_packet_version: str
    evidence_scope: str
    status: str
    evidence_packet_status: str
    future_paper_preview_preparation_ready: bool
    recommended_next_action: str
    broker_facing: bool
    executable: bool
    authorize_paper_preview_now: bool
    authorize_broker_action: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    submit_allowed: bool
    manual_operator_review_required: bool
    fresh_read_only_paper_snapshot_required: bool
    separate_paper_preview_milestone_required: bool
    explicit_operator_approval_required_before_any_broker_facing_preview: bool
    symbol: str
    strategy_name: str
    as_of: str
    source_operator_review_status: str
    source_operator_review_required_next_action: str
    source_operator_review_ready: bool
    source_operator_review_blocking_reasons: tuple[str, ...]
    source_blocking_reasons: tuple[str, ...]
    source_operator_review_limitations: tuple[str, ...]
    source_limitations: tuple[str, ...]
    source_operator_review_labels: tuple[str, ...]
    source_labels: tuple[str, ...]
    upstream_labels: tuple[str, ...]
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
    limitations: tuple[str, ...]
    required_future_prerequisites: tuple[str, ...]
    future_preparation_template: str

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            evidence_packet_version=self.evidence_packet_version,
            evidence_scope=self.evidence_scope,
            status=self.status,
            evidence_packet_status=self.evidence_packet_status,
            future_paper_preview_preparation_ready=(
                self.future_paper_preview_preparation_ready
            ),
            recommended_next_action=self.recommended_next_action,
            broker_facing=self.broker_facing,
            executable=self.executable,
            authorize_paper_preview_now=self.authorize_paper_preview_now,
            authorize_broker_action=self.authorize_broker_action,
            broker_action_performed=self.broker_action_performed,
            broker_preview_performed=self.broker_preview_performed,
            submit_allowed=self.submit_allowed,
            manual_operator_review_required=self.manual_operator_review_required,
            fresh_read_only_paper_snapshot_required=(
                self.fresh_read_only_paper_snapshot_required
            ),
            separate_paper_preview_milestone_required=(
                self.separate_paper_preview_milestone_required
            ),
            explicit_operator_approval_required_before_any_broker_facing_preview=(
                self.explicit_operator_approval_required_before_any_broker_facing_preview
            ),
            labels=self.labels,
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
            "source_operator_review_status",
            _required_string(
                self.source_operator_review_status,
                "source_operator_review_status",
            ),
        )
        object.__setattr__(
            self,
            "source_operator_review_required_next_action",
            _required_string(
                self.source_operator_review_required_next_action,
                "source_operator_review_required_next_action",
            ),
        )
        object.__setattr__(
            self,
            "source_operator_review_ready",
            _bool(self.source_operator_review_ready, "source_operator_review_ready"),
        )
        object.__setattr__(
            self,
            "source_operator_review_blocking_reasons",
            _string_tuple(
                self.source_operator_review_blocking_reasons,
                "source_operator_review_blocking_reasons",
                allow_empty=True,
            ),
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
            "source_operator_review_limitations",
            _string_tuple(
                self.source_operator_review_limitations,
                "source_operator_review_limitations",
                allow_empty=False,
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
        object.__setattr__(
            self,
            "source_operator_review_labels",
            _label_tuple(
                self.source_operator_review_labels,
                "source_operator_review_labels",
            ),
        )
        object.__setattr__(
            self,
            "source_labels",
            _label_tuple(self.source_labels, "source_labels"),
        )
        object.__setattr__(
            self,
            "upstream_labels",
            _label_tuple(self.upstream_labels, "upstream_labels"),
        )
        object.__setattr__(self, "labels", _evidence_packet_labels(self.labels))
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
        object.__setattr__(self, "limitations", _limitations(self.limitations))
        object.__setattr__(
            self,
            "required_future_prerequisites",
            _future_prerequisites(self.required_future_prerequisites),
        )
        object.__setattr__(
            self,
            "future_preparation_template",
            _future_preparation_template_text(self.future_preparation_template),
        )
        _validate_evidence_packet_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only evidence-packet metadata."""

        return {
            "evidence_packet_version": self.evidence_packet_version,
            "evidence_scope": self.evidence_scope,
            "status": self.status,
            "evidence_packet_status": self.evidence_packet_status,
            "future_paper_preview_preparation_ready": (
                self.future_paper_preview_preparation_ready
            ),
            "recommended_next_action": self.recommended_next_action,
            "broker_facing": self.broker_facing,
            "executable": self.executable,
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
            "separate_paper_preview_milestone_required": (
                self.separate_paper_preview_milestone_required
            ),
            "explicit_operator_approval_required_before_any_broker_facing_preview": (
                self.explicit_operator_approval_required_before_any_broker_facing_preview
            ),
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "source_operator_review_status": self.source_operator_review_status,
            "source_operator_review_required_next_action": (
                self.source_operator_review_required_next_action
            ),
            "source_operator_review_ready": self.source_operator_review_ready,
            "source_operator_review_blocking_reasons": list(
                self.source_operator_review_blocking_reasons
            ),
            "source_blocking_reasons": list(self.source_blocking_reasons),
            "source_operator_review_limitations": list(
                self.source_operator_review_limitations
            ),
            "source_limitations": list(self.source_limitations),
            "source_operator_review_labels": list(self.source_operator_review_labels),
            "source_labels": list(self.source_labels),
            "upstream_labels": list(self.upstream_labels),
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
            "limitations": list(self.limitations),
            "required_future_prerequisites": list(
                self.required_future_prerequisites
            ),
            "future_preparation_template": self.future_preparation_template,
        }


def build_etf_sma_paper_preview_evidence_packet(
    operator_review: EtfSmaPaperPreviewOperatorReview,
    config: EtfSmaPaperPreviewEvidencePacketConfig,
) -> EtfSmaPaperPreviewEvidencePacket:
    """Build a local evidence packet only from an M341 operator review."""

    checked_review = _operator_review(operator_review)
    checked_config = _config(config)
    source_operator_review_labels = _label_tuple(
        checked_review.labels,
        "source_operator_review_labels",
    )
    source_labels = _label_tuple(checked_review.source_labels, "source_labels")
    upstream_labels = _label_tuple(
        checked_review.source_prompt_review_source_labels,
        "upstream_labels",
    )
    source_operator_review_blocking_reasons = _string_tuple(
        checked_review.blocking_reasons,
        "source_operator_review_blocking_reasons",
        allow_empty=True,
    )
    source_blocking_reasons = _string_tuple(
        checked_review.source_blocking_reasons,
        "source_blocking_reasons",
        allow_empty=True,
    )
    source_operator_review_limitations = _string_tuple(
        checked_review.limitations,
        "source_operator_review_limitations",
        allow_empty=False,
    )
    source_limitations = _string_tuple(
        checked_review.source_limitations,
        "source_limitations",
        allow_empty=False,
    )
    blocking_reasons = _blocking_reasons(
        checked_review,
        source_operator_review_labels,
        source_labels,
        upstream_labels,
        source_operator_review_blocking_reasons,
        source_blocking_reasons,
    )
    status = _BLOCKED_STATUS if blocking_reasons else _READY_STATUS
    recommended_next_action = (
        _BLOCKED_NEXT_ACTION if blocking_reasons else _READY_NEXT_ACTION
    )
    preparation_ready = not blocking_reasons

    return EtfSmaPaperPreviewEvidencePacket(
        evidence_packet_version=_EVIDENCE_PACKET_VERSION,
        evidence_scope=_EVIDENCE_SCOPE,
        status=status,
        evidence_packet_status=status,
        future_paper_preview_preparation_ready=preparation_ready,
        recommended_next_action=recommended_next_action,
        broker_facing=False,
        executable=False,
        authorize_paper_preview_now=False,
        authorize_broker_action=False,
        broker_action_performed=False,
        broker_preview_performed=False,
        submit_allowed=False,
        manual_operator_review_required=True,
        fresh_read_only_paper_snapshot_required=True,
        separate_paper_preview_milestone_required=True,
        explicit_operator_approval_required_before_any_broker_facing_preview=True,
        symbol=checked_review.symbol,
        strategy_name=checked_review.strategy_name,
        as_of=checked_review.as_of,
        source_operator_review_status=checked_review.status,
        source_operator_review_required_next_action=(
            checked_review.required_next_action
        ),
        source_operator_review_ready=(
            checked_review.authorize_separate_paper_preview_milestone
        ),
        source_operator_review_blocking_reasons=(
            source_operator_review_blocking_reasons
        ),
        source_blocking_reasons=source_blocking_reasons,
        source_operator_review_limitations=source_operator_review_limitations,
        source_limitations=source_limitations,
        source_operator_review_labels=source_operator_review_labels,
        source_labels=source_labels,
        upstream_labels=upstream_labels,
        labels=ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS,
        latest_posture=checked_review.latest_posture,
        strategy_total_return=checked_review.strategy_total_return,
        benchmark_total_return=checked_review.benchmark_total_return,
        max_drawdown=checked_review.max_drawdown,
        bar_count=checked_review.bar_count,
        signal_count=checked_review.signal_count,
        exposure_count=checked_review.exposure_count,
        defensive_count=checked_review.defensive_count,
        posture_change_count=checked_review.posture_change_count,
        blocking_reasons=blocking_reasons,
        limitations=_merged_strings(
            source_operator_review_limitations,
            source_limitations,
            ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LIMITATIONS,
            checked_config.additional_limitations,
        ),
        required_future_prerequisites=(
            checked_config.required_future_prerequisites
        ),
        future_preparation_template=_future_preparation_template(),
    )


def _operator_review(value: object) -> EtfSmaPaperPreviewOperatorReview:
    if type(value) is not EtfSmaPaperPreviewOperatorReview:
        raise ValidationError(
            "operator_review must be an EtfSmaPaperPreviewOperatorReview."
        )

    return value


def _config(value: object) -> EtfSmaPaperPreviewEvidencePacketConfig:
    if type(value) is not EtfSmaPaperPreviewEvidencePacketConfig:
        raise ValidationError(
            "config must be an EtfSmaPaperPreviewEvidencePacketConfig."
        )

    return value


def _blocking_reasons(
    operator_review: EtfSmaPaperPreviewOperatorReview,
    source_operator_review_labels: tuple[str, ...],
    source_labels: tuple[str, ...],
    upstream_labels: tuple[str, ...],
    source_operator_review_blocking_reasons: tuple[str, ...],
    source_blocking_reasons: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if operator_review.status != _SOURCE_READY_STATUS:
        reasons.append("source_operator_review_not_ready")
    if operator_review.operator_review_status != operator_review.status:
        reasons.append("source_operator_review_status_mismatch")
    if operator_review.operator_review_status != _SOURCE_READY_STATUS:
        reasons.append("source_operator_review_status_not_ready")
    if operator_review.required_next_action != _SOURCE_READY_NEXT_ACTION:
        reasons.append("source_operator_review_required_next_action_unexpected")
    if operator_review.authorize_separate_paper_preview_milestone is not True:
        reasons.append("source_operator_review_readiness_false")
    if operator_review.authorize_paper_preview_now is not False:
        reasons.append("source_authorize_paper_preview_now_not_false")
    if operator_review.authorize_broker_action is not False:
        reasons.append("source_authorize_broker_action_not_false")
    if operator_review.broker_action_performed is not False:
        reasons.append("source_broker_action_performed_not_false")
    if operator_review.broker_preview_performed is not False:
        reasons.append("source_broker_preview_performed_not_false")
    if operator_review.submit_allowed is not False:
        reasons.append("source_submit_allowed_not_false")
    reasons.extend(source_operator_review_blocking_reasons)
    reasons.extend(source_blocking_reasons)

    label_groups = (
        source_operator_review_labels,
        source_labels,
        upstream_labels,
    )
    for label in ("research_only", "paper_lab_candidate", "not_live_authorized"):
        if any(label not in labels for labels in label_groups):
            reasons.append(f"source_missing_{label}_label")
    if any("profit_claim=none" not in labels for labels in label_groups):
        reasons.append("source_missing_profit_claim_none_label")

    if _has_live_authorized_text(
        source_operator_review_labels,
        source_labels,
        upstream_labels,
    ) or _has_live_authorized_status(operator_review):
        reasons.append("source_contains_live_authorized")
    if _has_profit_claim_other_than_none(
        source_operator_review_labels,
        source_labels,
        upstream_labels,
    ):
        reasons.append("source_contains_profit_claim_other_than_none")
    if operator_review.latest_posture == "insufficient_history":
        reasons.append("source_insufficient_history_posture")
    if operator_review.latest_posture == "defensive_or_cash_candidate":
        reasons.append("source_defensive_posture")

    return _dedupe(reasons)


def _future_preparation_template() -> str:
    return "\n".join(
        (
            "ETF/SMA paper-preview evidence packet for a future milestone.",
            "Decision scope: local research evidence packaging only.",
            "Separate milestone: <SEPARATE_PAPER_PREVIEW_MILESTONE_REQUIRED>",
            "Manual review: <MANUAL_OPERATOR_REVIEW_REQUIRED>",
            "Fresh snapshot: <FRESH_READ_ONLY_PAPER_SNAPSHOT_REQUIRED>",
            "Explicit approval: <EXPLICIT_OPERATOR_APPROVAL_REQUIRED>",
            "Broker-facing preview: <BROKER_FACING_PREVIEW_NOT_INCLUDED>",
            "Submit placeholder: <SUBMIT_FLAG_NOT_INCLUDED>",
            "No executable command is included in this evidence packet.",
        )
    )


def _validate_fixed_metadata(
    *,
    evidence_packet_version: object,
    evidence_scope: object,
    status: object,
    evidence_packet_status: object,
    future_paper_preview_preparation_ready: object,
    recommended_next_action: object,
    broker_facing: object,
    executable: object,
    authorize_paper_preview_now: object,
    authorize_broker_action: object,
    broker_action_performed: object,
    broker_preview_performed: object,
    submit_allowed: object,
    manual_operator_review_required: object,
    fresh_read_only_paper_snapshot_required: object,
    separate_paper_preview_milestone_required: object,
    explicit_operator_approval_required_before_any_broker_facing_preview: object,
    labels: object,
) -> None:
    if evidence_packet_version != _EVIDENCE_PACKET_VERSION:
        raise ValidationError(
            "evidence_packet_version must be exactly "
            "etf_sma_paper_preview_evidence_packet_v1."
        )
    if evidence_scope != _EVIDENCE_SCOPE:
        raise ValidationError(
            "evidence_scope must be local research to paper-preview preparation only."
        )
    if status not in (_READY_STATUS, _BLOCKED_STATUS):
        raise ValidationError("status must be a supported evidence packet status.")
    if evidence_packet_status != status:
        raise ValidationError("evidence_packet_status must match status.")
    _validate_safety_bool(
        future_paper_preview_preparation_ready,
        "future_paper_preview_preparation_ready",
        expected=status == _READY_STATUS,
    )
    _validate_safety_bool(broker_facing, "broker_facing", expected=False)
    _validate_safety_bool(executable, "executable", expected=False)
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
        separate_paper_preview_milestone_required,
        "separate_paper_preview_milestone_required",
        expected=True,
    )
    _validate_safety_bool(
        explicit_operator_approval_required_before_any_broker_facing_preview,
        "explicit_operator_approval_required_before_any_broker_facing_preview",
        expected=True,
    )
    if _evidence_packet_labels(labels) != ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS:
        raise ValidationError("labels must preserve the ETF/SMA evidence label set.")
    if status == _READY_STATUS and recommended_next_action != _READY_NEXT_ACTION:
        raise ValidationError(
            "ready evidence packets must draft a separate preview milestone."
        )
    if status == _BLOCKED_STATUS and recommended_next_action != _BLOCKED_NEXT_ACTION:
        raise ValidationError(
            "blocked evidence packets must resolve operator-review blockers."
        )


def _validate_evidence_packet_consistency(
    packet: EtfSmaPaperPreviewEvidencePacket,
) -> None:
    if packet.exposure_count + packet.defensive_count != packet.bar_count:
        raise ValidationError(
            "exposure_count plus defensive_count must equal bar_count."
        )
    if packet.signal_count > packet.bar_count:
        raise ValidationError("signal_count must not exceed bar_count.")
    if packet.posture_change_count > packet.bar_count:
        raise ValidationError("posture_change_count must not exceed bar_count.")
    if packet.status == _READY_STATUS and packet.blocking_reasons:
        raise ValidationError("ready evidence packets must not contain blockers.")
    if packet.status == _BLOCKED_STATUS and not packet.blocking_reasons:
        raise ValidationError("blocked evidence packets must contain blockers.")
    if packet.status == _READY_STATUS:
        _validate_ready_source(packet)


def _validate_ready_source(packet: EtfSmaPaperPreviewEvidencePacket) -> None:
    if packet.source_operator_review_status != _SOURCE_READY_STATUS:
        raise ValidationError(
            "ready evidence packets require a ready operator review."
        )
    if packet.source_operator_review_required_next_action != _SOURCE_READY_NEXT_ACTION:
        raise ValidationError(
            "ready evidence packets require the M341 next action."
        )
    if not packet.source_operator_review_ready:
        raise ValidationError(
            "ready evidence packets require source operator-review readiness."
        )
    if packet.source_operator_review_blocking_reasons:
        raise ValidationError(
            "ready evidence packets require no operator-review blockers."
        )
    if packet.source_blocking_reasons:
        raise ValidationError("ready evidence packets require no source blockers.")
    for label in ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS:
        if label not in packet.source_operator_review_labels:
            raise ValidationError(
                "ready evidence packets require all operator-review labels."
            )
        if label not in packet.source_labels:
            raise ValidationError(
                "ready evidence packets require all source labels."
            )
        if label not in packet.upstream_labels:
            raise ValidationError(
                "ready evidence packets require all upstream labels."
            )
    if _has_live_authorized_text(
        packet.source_operator_review_labels,
        packet.source_labels,
        packet.upstream_labels,
    ):
        raise ValidationError("ready evidence packets cannot contain live authority.")
    if _has_profit_claim_other_than_none(
        packet.source_operator_review_labels,
        packet.source_labels,
        packet.upstream_labels,
    ):
        raise ValidationError("ready evidence packets cannot contain a profit claim.")
    if packet.latest_posture != "bullish_trend_candidate":
        raise ValidationError("ready evidence packets require bullish research posture.")


def _future_preparation_template_text(value: object) -> str:
    template = _required_string(value, "future_preparation_template")
    missing = tuple(
        marker for marker in _REQUIRED_TEMPLATE_MARKERS if marker not in template
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            "future_preparation_template missing marker(s): "
            f"{missing_text}."
        )
    if _contains_submit_flag(template):
        raise ValidationError(
            "future_preparation_template must not include a submit flag."
        )
    if _contains_executable_command(template):
        raise ValidationError(
            "future_preparation_template must not include executable commands."
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


def _evidence_packet_labels(values: object) -> tuple[str, ...]:
    labels = _label_tuple(values, "labels")
    if labels != ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS:
        raise ValidationError("labels must match the ETF/SMA evidence labels.")

    return labels


def _limitations(values: object) -> tuple[str, ...]:
    limitations = _string_tuple(values, "limitations", allow_empty=False)
    missing = tuple(
        limitation
        for limitation in ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LIMITATIONS
        if limitation not in limitations
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(f"limitations missing required value(s): {missing_text}.")
    if len(frozenset(limitations)) != len(limitations):
        raise ValidationError("limitations must not contain duplicates.")

    return limitations


def _future_prerequisites(values: object) -> tuple[str, ...]:
    prerequisites = _string_tuple(
        values,
        "required_future_prerequisites",
        allow_empty=False,
    )
    missing = tuple(
        prerequisite
        for prerequisite in (
            ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_REQUIRED_FUTURE_PREREQUISITES
        )
        if prerequisite not in prerequisites
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            "required_future_prerequisites missing required value(s): "
            f"{missing_text}."
        )
    if len(frozenset(prerequisites)) != len(prerequisites):
        raise ValidationError("required_future_prerequisites must not duplicate.")

    return prerequisites


def _has_live_authorized_status(
    operator_review: EtfSmaPaperPreviewOperatorReview,
) -> bool:
    return any(
        _is_live_authorized_text(text)
        for text in (
            operator_review.status,
            operator_review.operator_review_status,
            operator_review.required_next_action,
            operator_review.source_prompt_review_status,
            operator_review.source_prompt_review_required_next_action,
            operator_review.latest_posture,
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
