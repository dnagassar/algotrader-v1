"""Offline ETF/SMA paper-preview milestone draft contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_paper_preview_evidence_packet import (
    ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS,
    EtfSmaPaperPreviewEvidencePacket,
)

__all__ = [
    "ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LABELS",
    "ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LIMITATIONS",
    "ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_REQUIRED_FUTURE_PREREQUISITES",
    "EtfSmaPaperPreviewMilestoneDraft",
    "EtfSmaPaperPreviewMilestoneDraftConfig",
    "build_etf_sma_paper_preview_milestone_draft",
]


_MILESTONE_DRAFT_VERSION = "etf_sma_paper_preview_milestone_draft_v1"
_DRAFT_SCOPE = "local_paper_preview_milestone_draft_only"
_SOURCE_READY_STATUS = "ready_for_separate_paper_preview_preparation"
_SOURCE_READY_NEXT_ACTION = "draft_separate_etf_sma_paper_preview_milestone"
_READY_STATUS = "ready_for_operator_review_of_paper_preview_milestone"
_BLOCKED_STATUS = "blocked_from_operator_review_of_paper_preview_milestone"
_READY_NEXT_ACTION = (
    "operator_review_m343_then_prepare_m344_fresh_read_only_snapshot"
)
_BLOCKED_NEXT_ACTION = "resolve_evidence_packet_blockers"
_SUPPORTED_POSTURES = (
    "bullish_trend_candidate",
    "defensive_or_cash_candidate",
    "insufficient_history",
)
_REQUIRED_DRAFT_TEXT_PHRASES = (
    "research_only",
    "paper_lab_candidate",
    "not_live_authorized",
    "profit_claim=none",
    "not execution authority",
    "not strategy validation",
    "not live authorization",
    "no broker command included",
    "no submit flag included",
    "normal pytest must remain offline, credential-free, deterministic, and safe",
)

ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LABELS = (
    ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS
)
ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_REQUIRED_FUTURE_PREREQUISITES = (
    "commit_m343_before_any_future_milestone",
    "fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe",
    "explicit_operator_approval_required_before_any_broker_facing_preview",
    "market_hours_session_check_required_for_equities_before_any_broker_facing_preview",
    "stop_if_market_session_or_broker_behavior_is_ambiguous",
)
ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LIMITATIONS = (
    "local_runbook_review_packet_only",
    "operator_facing_instructions_only",
    "not_live_authorized",
    "not_profit_evidence",
    "not_strategy_validation",
    "not_execution_authority",
    "paper_preview_not_performed",
    "no_broker_preview_or_staging",
    "no_broker_action_authorized",
    "broker_facing_preview_requires_future_milestone",
    "submit_not_allowed",
)


@dataclass(frozen=True, slots=True)
class EtfSmaPaperPreviewMilestoneDraftConfig:
    """Static offline gates for drafting the future paper-preview milestone."""

    required_future_prerequisites: tuple[
        str, ...
    ] = ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_REQUIRED_FUTURE_PREREQUISITES
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
class EtfSmaPaperPreviewMilestoneDraft:
    """Immutable local runbook packet for a future separate milestone."""

    milestone_draft_version: str
    draft_scope: str
    status: str
    milestone_draft_status: str
    operator_review_of_paper_preview_milestone_ready: bool
    recommended_next_action: str
    paper_preview_performed: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    submit_allowed: bool
    executable: bool
    broker_facing: bool
    commit_m343_before_any_future_milestone: bool
    fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe: bool
    explicit_operator_approval_required_before_any_broker_facing_preview: bool
    market_hours_session_check_required_for_equities_before_any_broker_facing_preview: bool
    stop_if_market_session_or_broker_behavior_is_ambiguous: bool
    symbol: str
    strategy_name: str
    as_of: str
    source_evidence_packet_status: str
    source_evidence_packet_recommended_next_action: str
    source_future_paper_preview_preparation_ready: bool
    source_broker_facing: bool
    source_executable: bool
    source_evidence_packet_blocking_reasons: tuple[str, ...]
    source_operator_review_blocking_reasons: tuple[str, ...]
    source_blocking_reasons: tuple[str, ...]
    source_evidence_packet_limitations: tuple[str, ...]
    source_operator_review_limitations: tuple[str, ...]
    source_limitations: tuple[str, ...]
    source_evidence_packet_labels: tuple[str, ...]
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
    draft_milestone_outline: str

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            milestone_draft_version=self.milestone_draft_version,
            draft_scope=self.draft_scope,
            status=self.status,
            milestone_draft_status=self.milestone_draft_status,
            operator_review_of_paper_preview_milestone_ready=(
                self.operator_review_of_paper_preview_milestone_ready
            ),
            recommended_next_action=self.recommended_next_action,
            paper_preview_performed=self.paper_preview_performed,
            broker_action_performed=self.broker_action_performed,
            broker_preview_performed=self.broker_preview_performed,
            submit_allowed=self.submit_allowed,
            executable=self.executable,
            broker_facing=self.broker_facing,
            commit_m343_before_any_future_milestone=(
                self.commit_m343_before_any_future_milestone
            ),
            fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe=(
                self.fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe
            ),
            explicit_operator_approval_required_before_any_broker_facing_preview=(
                self.explicit_operator_approval_required_before_any_broker_facing_preview
            ),
            market_hours_session_check_required_for_equities_before_any_broker_facing_preview=(
                self.market_hours_session_check_required_for_equities_before_any_broker_facing_preview
            ),
            stop_if_market_session_or_broker_behavior_is_ambiguous=(
                self.stop_if_market_session_or_broker_behavior_is_ambiguous
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
            "source_evidence_packet_status",
            _required_string(
                self.source_evidence_packet_status,
                "source_evidence_packet_status",
            ),
        )
        object.__setattr__(
            self,
            "source_evidence_packet_recommended_next_action",
            _required_string(
                self.source_evidence_packet_recommended_next_action,
                "source_evidence_packet_recommended_next_action",
            ),
        )
        object.__setattr__(
            self,
            "source_future_paper_preview_preparation_ready",
            _bool(
                self.source_future_paper_preview_preparation_ready,
                "source_future_paper_preview_preparation_ready",
            ),
        )
        object.__setattr__(
            self,
            "source_broker_facing",
            _bool(self.source_broker_facing, "source_broker_facing"),
        )
        object.__setattr__(
            self,
            "source_executable",
            _bool(self.source_executable, "source_executable"),
        )
        object.__setattr__(
            self,
            "source_evidence_packet_blocking_reasons",
            _string_tuple(
                self.source_evidence_packet_blocking_reasons,
                "source_evidence_packet_blocking_reasons",
                allow_empty=True,
            ),
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
            "source_evidence_packet_limitations",
            _string_tuple(
                self.source_evidence_packet_limitations,
                "source_evidence_packet_limitations",
                allow_empty=False,
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
            "source_evidence_packet_labels",
            _label_tuple(
                self.source_evidence_packet_labels,
                "source_evidence_packet_labels",
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
        object.__setattr__(self, "labels", _milestone_draft_labels(self.labels))
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
            "draft_milestone_outline",
            _draft_milestone_outline_text(self.draft_milestone_outline),
        )
        _validate_milestone_draft_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only milestone-draft metadata."""

        return {
            "milestone_draft_version": self.milestone_draft_version,
            "draft_scope": self.draft_scope,
            "status": self.status,
            "milestone_draft_status": self.milestone_draft_status,
            "operator_review_of_paper_preview_milestone_ready": (
                self.operator_review_of_paper_preview_milestone_ready
            ),
            "recommended_next_action": self.recommended_next_action,
            "paper_preview_performed": self.paper_preview_performed,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "submit_allowed": self.submit_allowed,
            "executable": self.executable,
            "broker_facing": self.broker_facing,
            "commit_m343_before_any_future_milestone": (
                self.commit_m343_before_any_future_milestone
            ),
            "fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe": (
                self.fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe
            ),
            "explicit_operator_approval_required_before_any_broker_facing_preview": (
                self.explicit_operator_approval_required_before_any_broker_facing_preview
            ),
            "market_hours_session_check_required_for_equities_before_any_broker_facing_preview": (
                self.market_hours_session_check_required_for_equities_before_any_broker_facing_preview
            ),
            "stop_if_market_session_or_broker_behavior_is_ambiguous": (
                self.stop_if_market_session_or_broker_behavior_is_ambiguous
            ),
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "as_of": self.as_of,
            "source_evidence_packet_status": self.source_evidence_packet_status,
            "source_evidence_packet_recommended_next_action": (
                self.source_evidence_packet_recommended_next_action
            ),
            "source_future_paper_preview_preparation_ready": (
                self.source_future_paper_preview_preparation_ready
            ),
            "source_broker_facing": self.source_broker_facing,
            "source_executable": self.source_executable,
            "source_evidence_packet_blocking_reasons": list(
                self.source_evidence_packet_blocking_reasons
            ),
            "source_operator_review_blocking_reasons": list(
                self.source_operator_review_blocking_reasons
            ),
            "source_blocking_reasons": list(self.source_blocking_reasons),
            "source_evidence_packet_limitations": list(
                self.source_evidence_packet_limitations
            ),
            "source_operator_review_limitations": list(
                self.source_operator_review_limitations
            ),
            "source_limitations": list(self.source_limitations),
            "source_evidence_packet_labels": list(
                self.source_evidence_packet_labels
            ),
            "source_operator_review_labels": list(
                self.source_operator_review_labels
            ),
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
            "draft_milestone_outline": self.draft_milestone_outline,
        }


def build_etf_sma_paper_preview_milestone_draft(
    evidence_packet: EtfSmaPaperPreviewEvidencePacket,
    config: EtfSmaPaperPreviewMilestoneDraftConfig,
) -> EtfSmaPaperPreviewMilestoneDraft:
    """Build a local runbook draft only from an M342 evidence packet."""

    checked_packet = _evidence_packet(evidence_packet)
    checked_config = _config(config)
    source_evidence_packet_labels = _label_tuple(
        checked_packet.labels,
        "source_evidence_packet_labels",
    )
    source_operator_review_labels = _label_tuple(
        checked_packet.source_operator_review_labels,
        "source_operator_review_labels",
    )
    source_labels = _label_tuple(checked_packet.source_labels, "source_labels")
    upstream_labels = _label_tuple(checked_packet.upstream_labels, "upstream_labels")
    source_evidence_packet_blocking_reasons = _string_tuple(
        checked_packet.blocking_reasons,
        "source_evidence_packet_blocking_reasons",
        allow_empty=True,
    )
    source_operator_review_blocking_reasons = _string_tuple(
        checked_packet.source_operator_review_blocking_reasons,
        "source_operator_review_blocking_reasons",
        allow_empty=True,
    )
    source_blocking_reasons = _string_tuple(
        checked_packet.source_blocking_reasons,
        "source_blocking_reasons",
        allow_empty=True,
    )
    source_evidence_packet_limitations = _string_tuple(
        checked_packet.limitations,
        "source_evidence_packet_limitations",
        allow_empty=False,
    )
    source_operator_review_limitations = _string_tuple(
        checked_packet.source_operator_review_limitations,
        "source_operator_review_limitations",
        allow_empty=False,
    )
    source_limitations = _string_tuple(
        checked_packet.source_limitations,
        "source_limitations",
        allow_empty=False,
    )
    blocking_reasons = _blocking_reasons(
        checked_packet,
        source_evidence_packet_labels,
        source_operator_review_labels,
        source_labels,
        upstream_labels,
        source_evidence_packet_blocking_reasons,
        source_operator_review_blocking_reasons,
        source_blocking_reasons,
    )
    status = _BLOCKED_STATUS if blocking_reasons else _READY_STATUS
    recommended_next_action = (
        _BLOCKED_NEXT_ACTION if blocking_reasons else _READY_NEXT_ACTION
    )
    operator_review_ready = not blocking_reasons

    return EtfSmaPaperPreviewMilestoneDraft(
        milestone_draft_version=_MILESTONE_DRAFT_VERSION,
        draft_scope=_DRAFT_SCOPE,
        status=status,
        milestone_draft_status=status,
        operator_review_of_paper_preview_milestone_ready=operator_review_ready,
        recommended_next_action=recommended_next_action,
        paper_preview_performed=False,
        broker_action_performed=False,
        broker_preview_performed=False,
        submit_allowed=False,
        executable=False,
        broker_facing=False,
        commit_m343_before_any_future_milestone=True,
        fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe=True,
        explicit_operator_approval_required_before_any_broker_facing_preview=True,
        market_hours_session_check_required_for_equities_before_any_broker_facing_preview=True,
        stop_if_market_session_or_broker_behavior_is_ambiguous=True,
        symbol=checked_packet.symbol,
        strategy_name=checked_packet.strategy_name,
        as_of=checked_packet.as_of,
        source_evidence_packet_status=checked_packet.status,
        source_evidence_packet_recommended_next_action=(
            checked_packet.recommended_next_action
        ),
        source_future_paper_preview_preparation_ready=(
            checked_packet.future_paper_preview_preparation_ready
        ),
        source_broker_facing=checked_packet.broker_facing,
        source_executable=checked_packet.executable,
        source_evidence_packet_blocking_reasons=(
            source_evidence_packet_blocking_reasons
        ),
        source_operator_review_blocking_reasons=(
            source_operator_review_blocking_reasons
        ),
        source_blocking_reasons=source_blocking_reasons,
        source_evidence_packet_limitations=source_evidence_packet_limitations,
        source_operator_review_limitations=source_operator_review_limitations,
        source_limitations=source_limitations,
        source_evidence_packet_labels=source_evidence_packet_labels,
        source_operator_review_labels=source_operator_review_labels,
        source_labels=source_labels,
        upstream_labels=upstream_labels,
        labels=ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LABELS,
        latest_posture=checked_packet.latest_posture,
        strategy_total_return=checked_packet.strategy_total_return,
        benchmark_total_return=checked_packet.benchmark_total_return,
        max_drawdown=checked_packet.max_drawdown,
        bar_count=checked_packet.bar_count,
        signal_count=checked_packet.signal_count,
        exposure_count=checked_packet.exposure_count,
        defensive_count=checked_packet.defensive_count,
        posture_change_count=checked_packet.posture_change_count,
        blocking_reasons=blocking_reasons,
        limitations=_merged_strings(
            source_evidence_packet_limitations,
            source_operator_review_limitations,
            source_limitations,
            ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LIMITATIONS,
            checked_config.additional_limitations,
        ),
        required_future_prerequisites=(
            checked_config.required_future_prerequisites
        ),
        draft_milestone_outline=_draft_milestone_outline(),
    )


def _evidence_packet(value: object) -> EtfSmaPaperPreviewEvidencePacket:
    if type(value) is not EtfSmaPaperPreviewEvidencePacket:
        raise ValidationError(
            "evidence_packet must be an EtfSmaPaperPreviewEvidencePacket."
        )

    return value


def _config(value: object) -> EtfSmaPaperPreviewMilestoneDraftConfig:
    if type(value) is not EtfSmaPaperPreviewMilestoneDraftConfig:
        raise ValidationError(
            "config must be an EtfSmaPaperPreviewMilestoneDraftConfig."
        )

    return value


def _blocking_reasons(
    evidence_packet: EtfSmaPaperPreviewEvidencePacket,
    source_evidence_packet_labels: tuple[str, ...],
    source_operator_review_labels: tuple[str, ...],
    source_labels: tuple[str, ...],
    upstream_labels: tuple[str, ...],
    source_evidence_packet_blocking_reasons: tuple[str, ...],
    source_operator_review_blocking_reasons: tuple[str, ...],
    source_blocking_reasons: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if evidence_packet.status != _SOURCE_READY_STATUS:
        reasons.append("source_evidence_packet_not_ready")
    if evidence_packet.evidence_packet_status != evidence_packet.status:
        reasons.append("source_evidence_packet_status_mismatch")
    if evidence_packet.evidence_packet_status != _SOURCE_READY_STATUS:
        reasons.append("source_evidence_packet_status_not_ready")
    if evidence_packet.recommended_next_action != _SOURCE_READY_NEXT_ACTION:
        reasons.append("source_evidence_packet_next_action_unexpected")
    if evidence_packet.future_paper_preview_preparation_ready is not True:
        reasons.append("source_future_paper_preview_preparation_not_ready")
    if evidence_packet.source_operator_review_ready is not True:
        reasons.append("source_operator_review_ready_false")
    if evidence_packet.broker_facing is not False:
        reasons.append("source_broker_facing_not_false")
    if evidence_packet.executable is not False:
        reasons.append("source_executable_not_false")
    if evidence_packet.authorize_paper_preview_now is not False:
        reasons.append("source_authorize_paper_preview_now_not_false")
    if evidence_packet.authorize_broker_action is not False:
        reasons.append("source_authorize_broker_action_not_false")
    if evidence_packet.broker_action_performed is not False:
        reasons.append("source_broker_action_performed_not_false")
    if evidence_packet.broker_preview_performed is not False:
        reasons.append("source_broker_preview_performed_not_false")
    if evidence_packet.submit_allowed is not False:
        reasons.append("source_submit_allowed_not_false")

    reasons.extend(source_evidence_packet_blocking_reasons)
    reasons.extend(source_operator_review_blocking_reasons)
    reasons.extend(source_blocking_reasons)

    label_groups = (
        source_evidence_packet_labels,
        source_operator_review_labels,
        source_labels,
        upstream_labels,
    )
    for label in ("research_only", "paper_lab_candidate", "not_live_authorized"):
        if any(label not in labels for labels in label_groups):
            reasons.append(f"source_missing_{label}_label")
    if any("profit_claim=none" not in labels for labels in label_groups):
        reasons.append("source_missing_profit_claim_none_label")

    if _has_live_authorized_text(*label_groups) or _has_live_authorized_status(
        evidence_packet
    ):
        reasons.append("source_contains_live_authorized")
    if _has_profit_claim_other_than_none(*label_groups):
        reasons.append("source_contains_profit_claim_other_than_none")
    if evidence_packet.latest_posture == "insufficient_history":
        reasons.append("source_insufficient_history_posture")
    if evidence_packet.latest_posture == "defensive_or_cash_candidate":
        reasons.append("source_defensive_posture")

    return _dedupe(reasons)


def _draft_milestone_outline() -> str:
    return "\n".join(
        (
            "ETF/SMA paper-preview milestone draft for a future separate milestone.",
            "Scope labels: research_only, paper_lab_candidate, not_live_authorized, profit_claim=none.",
            "Safety posture: not execution authority; not strategy validation; not live authorization.",
            "This local draft prepares operator-facing instructions and prerequisites only.",
            "Future milestone outline:",
            "1. Confirm M343 is committed before any future milestone.",
            "2. Run a fresh read-only paper snapshot before any broker-facing preview/probe.",
            "3. Require explicit operator approval before any broker-facing preview.",
            "4. Require market-hours/session check for equities before any broker-facing preview.",
            "5. Stop if market/session/broker behavior is ambiguous.",
            "No broker command included.",
            "No submit flag included.",
            "Normal pytest must remain offline, credential-free, deterministic, and safe.",
        )
    )


def _validate_fixed_metadata(
    *,
    milestone_draft_version: object,
    draft_scope: object,
    status: object,
    milestone_draft_status: object,
    operator_review_of_paper_preview_milestone_ready: object,
    recommended_next_action: object,
    paper_preview_performed: object,
    broker_action_performed: object,
    broker_preview_performed: object,
    submit_allowed: object,
    executable: object,
    broker_facing: object,
    commit_m343_before_any_future_milestone: object,
    fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe: object,
    explicit_operator_approval_required_before_any_broker_facing_preview: object,
    market_hours_session_check_required_for_equities_before_any_broker_facing_preview: object,
    stop_if_market_session_or_broker_behavior_is_ambiguous: object,
    labels: object,
) -> None:
    if milestone_draft_version != _MILESTONE_DRAFT_VERSION:
        raise ValidationError(
            "milestone_draft_version must be exactly "
            "etf_sma_paper_preview_milestone_draft_v1."
        )
    if draft_scope != _DRAFT_SCOPE:
        raise ValidationError("draft_scope must be local milestone drafting only.")
    if status not in (_READY_STATUS, _BLOCKED_STATUS):
        raise ValidationError("status must be a supported milestone draft status.")
    if milestone_draft_status != status:
        raise ValidationError("milestone_draft_status must match status.")
    _validate_safety_bool(
        operator_review_of_paper_preview_milestone_ready,
        "operator_review_of_paper_preview_milestone_ready",
        expected=status == _READY_STATUS,
    )
    if status == _READY_STATUS and recommended_next_action != _READY_NEXT_ACTION:
        raise ValidationError(
            "ready milestone drafts must recommend M343 operator review."
        )
    if status == _BLOCKED_STATUS and recommended_next_action != _BLOCKED_NEXT_ACTION:
        raise ValidationError(
            "blocked milestone drafts must resolve evidence-packet blockers."
        )
    _validate_safety_bool(
        paper_preview_performed,
        "paper_preview_performed",
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
    _validate_safety_bool(executable, "executable", expected=False)
    _validate_safety_bool(broker_facing, "broker_facing", expected=False)
    _validate_safety_bool(
        commit_m343_before_any_future_milestone,
        "commit_m343_before_any_future_milestone",
        expected=True,
    )
    _validate_safety_bool(
        fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe,
        "fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe",
        expected=True,
    )
    _validate_safety_bool(
        explicit_operator_approval_required_before_any_broker_facing_preview,
        "explicit_operator_approval_required_before_any_broker_facing_preview",
        expected=True,
    )
    _validate_safety_bool(
        market_hours_session_check_required_for_equities_before_any_broker_facing_preview,
        "market_hours_session_check_required_for_equities_before_any_broker_facing_preview",
        expected=True,
    )
    _validate_safety_bool(
        stop_if_market_session_or_broker_behavior_is_ambiguous,
        "stop_if_market_session_or_broker_behavior_is_ambiguous",
        expected=True,
    )
    if (
        _milestone_draft_labels(labels)
        != ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LABELS
    ):
        raise ValidationError("labels must preserve the ETF/SMA draft label set.")


def _validate_milestone_draft_consistency(
    draft: EtfSmaPaperPreviewMilestoneDraft,
) -> None:
    if draft.exposure_count + draft.defensive_count != draft.bar_count:
        raise ValidationError(
            "exposure_count plus defensive_count must equal bar_count."
        )
    if draft.signal_count > draft.bar_count:
        raise ValidationError("signal_count must not exceed bar_count.")
    if draft.posture_change_count > draft.bar_count:
        raise ValidationError("posture_change_count must not exceed bar_count.")
    if draft.status == _READY_STATUS and draft.blocking_reasons:
        raise ValidationError("ready milestone drafts must not contain blockers.")
    if draft.status == _BLOCKED_STATUS and not draft.blocking_reasons:
        raise ValidationError("blocked milestone drafts must contain blockers.")
    if draft.status == _READY_STATUS:
        _validate_ready_source(draft)


def _validate_ready_source(draft: EtfSmaPaperPreviewMilestoneDraft) -> None:
    if draft.source_evidence_packet_status != _SOURCE_READY_STATUS:
        raise ValidationError(
            "ready milestone drafts require a ready evidence packet."
        )
    if (
        draft.source_evidence_packet_recommended_next_action
        != _SOURCE_READY_NEXT_ACTION
    ):
        raise ValidationError("ready milestone drafts require the M342 next action.")
    if not draft.source_future_paper_preview_preparation_ready:
        raise ValidationError(
            "ready milestone drafts require source preparation readiness."
        )
    if draft.source_broker_facing:
        raise ValidationError("ready milestone drafts require local source evidence.")
    if draft.source_executable:
        raise ValidationError(
            "ready milestone drafts require non-executable source evidence."
        )
    if draft.source_evidence_packet_blocking_reasons:
        raise ValidationError("ready milestone drafts require no M342 blockers.")
    if draft.source_operator_review_blocking_reasons:
        raise ValidationError(
            "ready milestone drafts require no operator-review blockers."
        )
    if draft.source_blocking_reasons:
        raise ValidationError("ready milestone drafts require no upstream blockers.")
    for label in ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LABELS:
        if label not in draft.source_evidence_packet_labels:
            raise ValidationError(
                "ready milestone drafts require all evidence-packet labels."
            )
        if label not in draft.source_operator_review_labels:
            raise ValidationError(
                "ready milestone drafts require all operator-review labels."
            )
        if label not in draft.source_labels:
            raise ValidationError(
                "ready milestone drafts require all source labels."
            )
        if label not in draft.upstream_labels:
            raise ValidationError(
                "ready milestone drafts require all upstream labels."
            )
    if _has_live_authorized_text(
        draft.source_evidence_packet_labels,
        draft.source_operator_review_labels,
        draft.source_labels,
        draft.upstream_labels,
    ):
        raise ValidationError(
            "ready milestone drafts cannot contain live authority."
        )
    if _has_profit_claim_other_than_none(
        draft.source_evidence_packet_labels,
        draft.source_operator_review_labels,
        draft.source_labels,
        draft.upstream_labels,
    ):
        raise ValidationError("ready milestone drafts cannot contain a profit claim.")
    if draft.latest_posture != "bullish_trend_candidate":
        raise ValidationError("ready milestone drafts require bullish posture.")


def _draft_milestone_outline_text(value: object) -> str:
    outline = _required_string(value, "draft_milestone_outline")
    lowered = outline.lower()
    missing = tuple(
        phrase for phrase in _REQUIRED_DRAFT_TEXT_PHRASES if phrase not in lowered
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            "draft_milestone_outline missing required phrase(s): "
            f"{missing_text}."
        )
    if _contains_submit_flag(outline):
        raise ValidationError(
            "draft_milestone_outline must not include an enabled submit flag."
        )
    if _contains_executable_command(outline):
        raise ValidationError(
            "draft_milestone_outline must not include executable commands."
        )

    return outline


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
        "curl ",
        "powershell ",
        "pwsh ",
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


def _milestone_draft_labels(values: object) -> tuple[str, ...]:
    labels = _label_tuple(values, "labels")
    if labels != ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LABELS:
        raise ValidationError("labels must match the ETF/SMA milestone draft labels.")

    return labels


def _limitations(values: object) -> tuple[str, ...]:
    limitations = _string_tuple(values, "limitations", allow_empty=False)
    missing = tuple(
        limitation
        for limitation in ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LIMITATIONS
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
            ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_REQUIRED_FUTURE_PREREQUISITES
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
    evidence_packet: EtfSmaPaperPreviewEvidencePacket,
) -> bool:
    return any(
        _is_live_authorized_text(text)
        for text in (
            evidence_packet.status,
            evidence_packet.evidence_packet_status,
            evidence_packet.recommended_next_action,
            evidence_packet.source_operator_review_status,
            evidence_packet.source_operator_review_required_next_action,
            evidence_packet.latest_posture,
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
