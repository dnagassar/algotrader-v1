"""Local JSONL artifact for the offline SPY ETF/SMA next-experiment review."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_next_experiment_review import (
    ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS,
    EtfSmaNextExperimentReview,
    EtfSmaNextExperimentReviewConfig,
    build_etf_sma_next_experiment_review,
)

__all__ = [
    "EtfSmaNextExperimentOfflineSignalEvidence",
    "EtfSmaNextExperimentResetEvidence",
    "EtfSmaNextExperimentReviewArtifactConfig",
    "EtfSmaNextExperimentReviewArtifactRecord",
    "EtfSmaNextExperimentReviewArtifactWriteResult",
    "build_etf_sma_next_experiment_review_artifact_record",
    "render_etf_sma_next_experiment_review_artifact_record",
    "write_etf_sma_next_experiment_review_artifact",
]


_ARTIFACT_VERSION = "etf_sma_next_experiment_review_artifact_v1"
_RECORD_TYPE = "etf_sma_next_experiment_review_artifact_record"
_DEFAULT_RUN_ID = "m368a_offline_spy_etf_sma_next_experiment_review"
_M367_SOURCE_EVIDENCE_ID = "m366_fresh_paper_lab_reset_snapshot"
_CLEAN_RESET_CLASSIFICATION = "paper_lab_flat_clean"
_INCOMPLETE_RESET_CLASSIFICATION = "ambiguous_or_incomplete"
_READY_DECISION = "ready_for_separate_broker_preview_milestone"
_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class EtfSmaNextExperimentResetEvidence:
    """Explicit M366-style paper-lab reset evidence for offline review."""

    evidence_id: str = _M367_SOURCE_EVIDENCE_ID
    classification: str = _CLEAN_RESET_CLASSIFICATION
    account_observed: bool = True
    positions_observed: bool = True
    open_orders_observed: bool = True
    cash: Decimal | None = Decimal("1999.81")
    currency: str | None = "USD"
    position_count: int = 0
    position_symbols: tuple[str, ...] = ()
    recent_order_count: int = 0
    spy_absent_or_zero: bool = True
    no_open_orders: bool = True
    mutated: bool = False
    submitted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _required_string(self.evidence_id, "evidence_id"))
        object.__setattr__(
            self,
            "classification",
            _required_string(self.classification, "classification"),
        )
        object.__setattr__(
            self,
            "account_observed",
            _bool(self.account_observed, "account_observed"),
        )
        object.__setattr__(
            self,
            "positions_observed",
            _bool(self.positions_observed, "positions_observed"),
        )
        object.__setattr__(
            self,
            "open_orders_observed",
            _bool(self.open_orders_observed, "open_orders_observed"),
        )
        object.__setattr__(self, "cash", _optional_decimal(self.cash, "cash"))
        object.__setattr__(self, "currency", _optional_string(self.currency, "currency"))
        object.__setattr__(
            self,
            "position_count",
            _non_negative_int(self.position_count, "position_count"),
        )
        object.__setattr__(
            self,
            "position_symbols",
            _symbol_tuple(self.position_symbols, "position_symbols", allow_empty=True),
        )
        object.__setattr__(
            self,
            "recent_order_count",
            _non_negative_int(self.recent_order_count, "recent_order_count"),
        )
        object.__setattr__(
            self,
            "spy_absent_or_zero",
            _bool(self.spy_absent_or_zero, "spy_absent_or_zero"),
        )
        object.__setattr__(
            self,
            "no_open_orders",
            _bool(self.no_open_orders, "no_open_orders"),
        )
        object.__setattr__(self, "mutated", _false_bool(self.mutated, "mutated"))
        object.__setattr__(self, "submitted", _false_bool(self.submitted, "submitted"))

    def reset_blockers(self) -> tuple[str, ...]:
        """Return M366-style reset evidence gaps that should block M367 readiness."""

        blockers: list[str] = []

        if self.evidence_id != _M367_SOURCE_EVIDENCE_ID:
            blockers.append("m366_evidence_id_missing_or_unexpected")
        if self.classification != _CLEAN_RESET_CLASSIFICATION:
            blockers.append("reset_classification_not_paper_lab_flat_clean")
        if not self.account_observed:
            blockers.append("account_not_observed")
        if not self.positions_observed:
            blockers.append("positions_not_observed")
        if not self.open_orders_observed:
            blockers.append("open_orders_not_observed")
        if self.position_count != 0:
            blockers.append("positions_present")
        if self.position_symbols:
            blockers.append("position_symbols_present")
        if self.recent_order_count != 0:
            blockers.append("recent_orders_present")
        if not self.spy_absent_or_zero:
            blockers.append("spy_position_not_absent_or_zero")
        if not self.no_open_orders:
            blockers.append("open_orders_present")

        return tuple(blockers)

    def m367_classification(self) -> str:
        """Return the reset classification to feed the existing M367 builder."""

        if self.reset_blockers():
            return _INCOMPLETE_RESET_CLASSIFICATION

        return self.classification

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only reset evidence."""

        return {
            "evidence_id": self.evidence_id,
            "classification": self.classification,
            "account_observed": self.account_observed,
            "positions_observed": self.positions_observed,
            "open_orders_observed": self.open_orders_observed,
            "cash": _decimal_text(self.cash),
            "currency": self.currency,
            "position_count": self.position_count,
            "position_symbols": list(self.position_symbols),
            "recent_order_count": self.recent_order_count,
            "spy_absent_or_zero": self.spy_absent_or_zero,
            "no_open_orders": self.no_open_orders,
            "mutated": self.mutated,
            "submitted": self.submitted,
            "reset_blockers": list(self.reset_blockers()),
            "m367_classification": self.m367_classification(),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaNextExperimentOfflineSignalEvidence:
    """Explicit offline ETF/SMA signal evidence for the M367 review."""

    evidence_id: str
    symbol: str
    asset_class: str
    as_of: str
    status: str | None
    short_window: int
    long_window: int
    total_bar_count: int
    usable_bar_count: int
    ignored_future_bar_count: int
    latest_close: Decimal | None
    short_sma: Decimal | None
    long_sma: Decimal | None
    actionable_risk_on: bool
    provenance: str = "explicit_offline_signal_evidence"
    fixture_data_not_live_market_data: bool = False
    limitations: tuple[str, ...] = (
        "offline_signal_evidence_only",
        "not_live_market_data_unless_explicitly_stated_by_operator",
        "not_profit_evidence",
        "not_live_authorized",
        "no_broker_action_performed",
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _required_string(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _required_string(self.asset_class, "asset_class"),
        )
        object.__setattr__(self, "as_of", _required_string(self.as_of, "as_of"))
        object.__setattr__(self, "status", _optional_string(self.status, "status"))
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
        object.__setattr__(
            self,
            "actionable_risk_on",
            _bool(self.actionable_risk_on, "actionable_risk_on"),
        )
        object.__setattr__(
            self,
            "provenance",
            _required_string(self.provenance, "provenance"),
        )
        object.__setattr__(
            self,
            "fixture_data_not_live_market_data",
            _bool(
                self.fixture_data_not_live_market_data,
                "fixture_data_not_live_market_data",
            ),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations", allow_empty=False),
        )

    def signal_blockers(self) -> tuple[str, ...]:
        """Return evidence-quality blockers for the offline signal summary."""

        blockers: list[str] = []

        if self.symbol != "SPY":
            blockers.append("signal_symbol_not_spy")
        if self.asset_class != "equity":
            blockers.append("signal_asset_class_not_equity")
        if self.usable_bar_count + self.ignored_future_bar_count != self.total_bar_count:
            blockers.append("signal_bar_count_inconsistent")
        if self.usable_bar_count < self.long_window:
            blockers.append("signal_status_insufficient_history")
        if self.status is None:
            blockers.append("signal_status_missing")
        if self.latest_close is None:
            blockers.append("signal_latest_close_missing")
        if self.short_sma is None:
            blockers.append("signal_short_sma_missing")
        if self.long_sma is None:
            blockers.append("signal_long_sma_missing")
        if self.status == "stale":
            blockers.append("signal_status_stale")
        if self.status == "malformed":
            blockers.append("signal_status_malformed")
        if self.actionable_risk_on and self.status != "bullish_risk_on":
            blockers.append("signal_actionable_status_mismatch")
        if self.status == "bullish_risk_on" and not self.actionable_risk_on:
            blockers.append("signal_status_not_marked_actionable")
        if (
            self.status == "bullish_risk_on"
            and self.short_sma is not None
            and self.long_sma is not None
            and self.short_sma <= self.long_sma
        ):
            blockers.append("signal_sma_comparison_not_risk_on")
        if self.status == "defensive_risk_off":
            blockers.append("signal_status_risk_off")

        return tuple(_dedupe(blockers))

    def m367_signal_status(self) -> str | None:
        """Return the signal status to feed the existing M367 builder."""

        blockers = self.signal_blockers()
        if "signal_status_missing" in blockers:
            return None
        if any(blocker.startswith("signal_status_insufficient") for blocker in blockers):
            return "insufficient_history"
        if "signal_status_stale" in blockers:
            return "stale"
        if "signal_status_malformed" in blockers:
            return "malformed"
        if "signal_bar_count_inconsistent" in blockers:
            return "malformed"
        if "signal_latest_close_missing" in blockers:
            return "malformed"
        if "signal_short_sma_missing" in blockers:
            return "malformed"
        if "signal_long_sma_missing" in blockers:
            return "malformed"
        if "signal_sma_comparison_not_risk_on" in blockers:
            return "malformed"
        if "signal_actionable_status_mismatch" in blockers:
            return "malformed"
        if "signal_status_not_marked_actionable" in blockers:
            return "not_actionable"

        return self.status

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only signal evidence."""

        return {
            "evidence_id": self.evidence_id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "as_of": self.as_of,
            "status": self.status,
            "m367_signal_status": self.m367_signal_status(),
            "short_window": self.short_window,
            "long_window": self.long_window,
            "total_bar_count": self.total_bar_count,
            "usable_bar_count": self.usable_bar_count,
            "ignored_future_bar_count": self.ignored_future_bar_count,
            "latest_close": _decimal_text(self.latest_close),
            "short_sma": _decimal_text(self.short_sma),
            "long_sma": _decimal_text(self.long_sma),
            "actionable_risk_on": self.actionable_risk_on,
            "provenance": self.provenance,
            "fixture_data_not_live_market_data": self.fixture_data_not_live_market_data,
            "limitations": list(self.limitations),
            "signal_blockers": list(self.signal_blockers()),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaNextExperimentReviewArtifactConfig:
    """Explicit local file-write configuration for the M368A artifact."""

    output_path: Path | str
    run_id: str = _DEFAULT_RUN_ID
    target_cap: Decimal = Decimal("25.00")
    append: bool = False
    create_parent_dirs: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "target_cap",
            _positive_decimal(self.target_cap, "target_cap"),
        )
        object.__setattr__(self, "append", _bool(self.append, "append"))
        object.__setattr__(
            self,
            "create_parent_dirs",
            _bool(self.create_parent_dirs, "create_parent_dirs"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaNextExperimentReviewArtifactRecord:
    """Immutable local JSONL record for one M367 next-experiment review."""

    artifact_version: str
    record_type: str
    run_id: str
    evidence_ids: tuple[str, ...]
    m366_evidence_id: str
    signal_evidence_id: str
    source_review: EtfSmaNextExperimentReview
    reset_evidence: EtfSmaNextExperimentResetEvidence
    offline_signal_evidence: EtfSmaNextExperimentOfflineSignalEvidence
    symbol: str
    asset_class: str
    cap: Decimal
    labels: tuple[str, ...]
    reset_evidence_summary: dict[str, object]
    offline_signal_evidence_summary: dict[str, object]
    offline_signal_status: str | None
    offline_signal_actionable_risk_on: bool
    decision: str
    reason: str
    blockers: tuple[str, ...]
    required_next_milestone: str
    separate_preview_milestone_required: bool
    separate_broker_preview_milestone_allowed: bool
    submit_authorized: bool
    mutated: bool
    submitted: bool
    broker_action_performed: bool
    broker_preview_performed: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_version",
            _fixed_string(
                self.artifact_version,
                _ARTIFACT_VERSION,
                "artifact_version",
            ),
        )
        object.__setattr__(
            self,
            "record_type",
            _fixed_string(self.record_type, _RECORD_TYPE, "record_type"),
        )
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "evidence_ids",
            _string_tuple(self.evidence_ids, "evidence_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "m366_evidence_id",
            _fixed_string(self.m366_evidence_id, _M367_SOURCE_EVIDENCE_ID, "m366_evidence_id"),
        )
        object.__setattr__(
            self,
            "signal_evidence_id",
            _required_string(self.signal_evidence_id, "signal_evidence_id"),
        )
        object.__setattr__(
            self,
            "source_review",
            _source_review(self.source_review),
        )
        object.__setattr__(
            self,
            "reset_evidence",
            _reset_evidence(self.reset_evidence),
        )
        object.__setattr__(
            self,
            "offline_signal_evidence",
            _signal_evidence(self.offline_signal_evidence),
        )
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _required_string(self.asset_class, "asset_class"),
        )
        object.__setattr__(self, "cap", _positive_decimal(self.cap, "cap"))
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS,
                "labels",
            ),
        )
        object.__setattr__(
            self,
            "reset_evidence_summary",
            _primitive_dict(self.reset_evidence_summary, "reset_evidence_summary"),
        )
        object.__setattr__(
            self,
            "offline_signal_evidence_summary",
            _primitive_dict(
                self.offline_signal_evidence_summary,
                "offline_signal_evidence_summary",
            ),
        )
        object.__setattr__(
            self,
            "offline_signal_status",
            _optional_string(self.offline_signal_status, "offline_signal_status"),
        )
        object.__setattr__(
            self,
            "offline_signal_actionable_risk_on",
            _bool(
                self.offline_signal_actionable_risk_on,
                "offline_signal_actionable_risk_on",
            ),
        )
        object.__setattr__(
            self,
            "decision",
            _fixed_string(self.decision, self.source_review.decision, "decision"),
        )
        object.__setattr__(
            self,
            "reason",
            _fixed_string(self.reason, self.source_review.reason, "reason"),
        )
        object.__setattr__(
            self,
            "blockers",
            _string_tuple(self.blockers, "blockers", allow_empty=True),
        )
        object.__setattr__(
            self,
            "required_next_milestone",
            _fixed_string(
                self.required_next_milestone,
                self.source_review.required_next_milestone,
                "required_next_milestone",
            ),
        )
        object.__setattr__(
            self,
            "separate_preview_milestone_required",
            _true_bool(
                self.separate_preview_milestone_required,
                "separate_preview_milestone_required",
            ),
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
        object.__setattr__(self, "mutated", _false_bool(self.mutated, "mutated"))
        object.__setattr__(self, "submitted", _false_bool(self.submitted, "submitted"))
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(self.broker_action_performed, "broker_action_performed"),
        )
        object.__setattr__(
            self,
            "broker_preview_performed",
            _false_bool(self.broker_preview_performed, "broker_preview_performed"),
        )
        _validate_record_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only JSONL payload metadata."""

        return {
            "artifact_version": self.artifact_version,
            "record_type": self.record_type,
            "run_id": self.run_id,
            "evidence_ids": list(self.evidence_ids),
            "m366_evidence_id": self.m366_evidence_id,
            "signal_evidence_id": self.signal_evidence_id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "cap": _decimal_text(self.cap),
            "labels": list(self.labels),
            "reset_evidence_summary": _primitive_dict(
                self.reset_evidence_summary,
                "reset_evidence_summary",
            ),
            "offline_signal_evidence_summary": _primitive_dict(
                self.offline_signal_evidence_summary,
                "offline_signal_evidence_summary",
            ),
            "offline_signal_status": self.offline_signal_status,
            "offline_signal_actionable_risk_on": self.offline_signal_actionable_risk_on,
            "decision": self.decision,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "required_next_milestone": self.required_next_milestone,
            "separate_preview_milestone_required": (
                self.separate_preview_milestone_required
            ),
            "separate_broker_preview_milestone_allowed": (
                self.separate_broker_preview_milestone_allowed
            ),
            "submit_authorized": self.submit_authorized,
            "mutated": self.mutated,
            "submitted": self.submitted,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "source_review": self.source_review.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaNextExperimentReviewArtifactWriteResult:
    """Result metadata for one local JSONL artifact write."""

    output_path: Path
    record_count: int
    bytes_written: int
    append: bool
    created_parent_dirs: bool
    newline_terminated: bool
    submit_authorized: bool
    mutated: bool
    submitted: bool
    broker_action_performed: bool
    broker_preview_performed: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        object.__setattr__(
            self,
            "record_count",
            _fixed_int(self.record_count, 1, "record_count"),
        )
        object.__setattr__(
            self,
            "bytes_written",
            _positive_int(self.bytes_written, "bytes_written"),
        )
        object.__setattr__(self, "append", _bool(self.append, "append"))
        object.__setattr__(
            self,
            "created_parent_dirs",
            _bool(self.created_parent_dirs, "created_parent_dirs"),
        )
        object.__setattr__(
            self,
            "newline_terminated",
            _true_bool(self.newline_terminated, "newline_terminated"),
        )
        object.__setattr__(
            self,
            "submit_authorized",
            _false_bool(self.submit_authorized, "submit_authorized"),
        )
        object.__setattr__(self, "mutated", _false_bool(self.mutated, "mutated"))
        object.__setattr__(self, "submitted", _false_bool(self.submitted, "submitted"))
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(self.broker_action_performed, "broker_action_performed"),
        )
        object.__setattr__(
            self,
            "broker_preview_performed",
            _false_bool(self.broker_preview_performed, "broker_preview_performed"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return primitive local write metadata."""

        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "append": self.append,
            "created_parent_dirs": self.created_parent_dirs,
            "newline_terminated": self.newline_terminated,
            "submit_authorized": self.submit_authorized,
            "mutated": self.mutated,
            "submitted": self.submitted,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
        }


def build_etf_sma_next_experiment_review_artifact_record(
    *,
    reset_evidence: EtfSmaNextExperimentResetEvidence,
    offline_signal_evidence: EtfSmaNextExperimentOfflineSignalEvidence,
    config: EtfSmaNextExperimentReviewArtifactConfig,
) -> EtfSmaNextExperimentReviewArtifactRecord:
    """Build one deterministic local JSONL record from explicit offline evidence."""

    checked_reset = _reset_evidence(reset_evidence)
    checked_signal = _signal_evidence(offline_signal_evidence)
    checked_config = _config(config)
    review_config = EtfSmaNextExperimentReviewConfig(
        symbol=checked_signal.symbol,
        asset_class=checked_signal.asset_class,
        target_cap=checked_config.target_cap,
        allowlist=("SPY",),
        labels=ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS,
        source_evidence_id=checked_reset.evidence_id,
    )
    review = build_etf_sma_next_experiment_review(
        paper_reset_classification=checked_reset.m367_classification(),
        cash=checked_reset.cash,
        currency=checked_reset.currency,
        position_count=checked_reset.position_count,
        open_order_count=checked_reset.recent_order_count,
        signal_status=checked_signal.m367_signal_status(),
        config=review_config,
    )
    blockers = _merged_strings(
        review.blockers,
        checked_reset.reset_blockers(),
        checked_signal.signal_blockers(),
    )
    evidence_ids = _merged_strings(
        (_M367_SOURCE_EVIDENCE_ID,),
        (checked_reset.evidence_id,),
        (checked_signal.evidence_id,),
    )

    return EtfSmaNextExperimentReviewArtifactRecord(
        artifact_version=_ARTIFACT_VERSION,
        record_type=_RECORD_TYPE,
        run_id=checked_config.run_id,
        evidence_ids=evidence_ids,
        m366_evidence_id=_M367_SOURCE_EVIDENCE_ID,
        signal_evidence_id=checked_signal.evidence_id,
        source_review=review,
        reset_evidence=checked_reset,
        offline_signal_evidence=checked_signal,
        symbol=review.symbol,
        asset_class=review.asset_class,
        cap=checked_config.target_cap,
        labels=review.safety_labels,
        reset_evidence_summary=checked_reset.to_dict(),
        offline_signal_evidence_summary=checked_signal.to_dict(),
        offline_signal_status=checked_signal.m367_signal_status(),
        offline_signal_actionable_risk_on=checked_signal.actionable_risk_on,
        decision=review.decision,
        reason=review.reason,
        blockers=blockers,
        required_next_milestone=review.required_next_milestone,
        separate_preview_milestone_required=True,
        separate_broker_preview_milestone_allowed=(
            review.separate_broker_preview_milestone_allowed
        ),
        submit_authorized=False,
        mutated=False,
        submitted=False,
        broker_action_performed=False,
        broker_preview_performed=False,
    )


def render_etf_sma_next_experiment_review_artifact_record(
    record: EtfSmaNextExperimentReviewArtifactRecord,
) -> str:
    """Render one newline-terminated deterministic JSON object."""

    checked_record = _record(record)
    return json.dumps(
        checked_record.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def write_etf_sma_next_experiment_review_artifact(
    *,
    reset_evidence: EtfSmaNextExperimentResetEvidence,
    offline_signal_evidence: EtfSmaNextExperimentOfflineSignalEvidence,
    config: EtfSmaNextExperimentReviewArtifactConfig,
) -> EtfSmaNextExperimentReviewArtifactWriteResult:
    """Write one local JSONL artifact record to an explicit caller path."""

    checked_config = _config(config)
    record = build_etf_sma_next_experiment_review_artifact_record(
        reset_evidence=reset_evidence,
        offline_signal_evidence=offline_signal_evidence,
        config=checked_config,
    )
    line = render_etf_sma_next_experiment_review_artifact_record(record)
    created_parent_dirs = _prepare_output_parent(checked_config.output_path, checked_config)
    _write_line(checked_config.output_path, line, append=checked_config.append)

    return EtfSmaNextExperimentReviewArtifactWriteResult(
        output_path=checked_config.output_path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        append=checked_config.append,
        created_parent_dirs=created_parent_dirs,
        newline_terminated=line.endswith("\n"),
        submit_authorized=False,
        mutated=False,
        submitted=False,
        broker_action_performed=False,
        broker_preview_performed=False,
    )


def _config(
    value: object,
) -> EtfSmaNextExperimentReviewArtifactConfig:
    if type(value) is not EtfSmaNextExperimentReviewArtifactConfig:
        raise ValidationError(
            "config must be an EtfSmaNextExperimentReviewArtifactConfig."
        )

    return value


def _record(value: object) -> EtfSmaNextExperimentReviewArtifactRecord:
    if type(value) is not EtfSmaNextExperimentReviewArtifactRecord:
        raise ValidationError(
            "record must be an EtfSmaNextExperimentReviewArtifactRecord."
        )

    return value


def _source_review(value: object) -> EtfSmaNextExperimentReview:
    if type(value) is not EtfSmaNextExperimentReview:
        raise ValidationError("source_review must be an EtfSmaNextExperimentReview.")

    return value


def _reset_evidence(value: object) -> EtfSmaNextExperimentResetEvidence:
    if type(value) is not EtfSmaNextExperimentResetEvidence:
        raise ValidationError(
            "reset_evidence must be an EtfSmaNextExperimentResetEvidence."
        )

    return value


def _signal_evidence(value: object) -> EtfSmaNextExperimentOfflineSignalEvidence:
    if type(value) is not EtfSmaNextExperimentOfflineSignalEvidence:
        raise ValidationError(
            "offline_signal_evidence must be an "
            "EtfSmaNextExperimentOfflineSignalEvidence."
        )

    return value


def _validate_record_consistency(
    record: EtfSmaNextExperimentReviewArtifactRecord,
) -> None:
    if record.m366_evidence_id not in record.evidence_ids:
        raise ValidationError("evidence_ids must include m366_evidence_id.")
    if record.signal_evidence_id not in record.evidence_ids:
        raise ValidationError("evidence_ids must include signal_evidence_id.")
    if record.symbol != record.source_review.symbol:
        raise ValidationError("symbol must match source review.")
    if record.asset_class != record.source_review.asset_class:
        raise ValidationError("asset_class must match source review.")
    if record.cap != record.source_review.target_cap:
        raise ValidationError("cap must match source review target_cap.")
    if record.labels != record.source_review.safety_labels:
        raise ValidationError("labels must match source review safety labels.")
    if record.submit_authorized != record.source_review.submit_authorized:
        raise ValidationError("submit_authorized must match source review.")
    if (
        record.separate_broker_preview_milestone_allowed
        != record.source_review.separate_broker_preview_milestone_allowed
    ):
        raise ValidationError(
            "separate_broker_preview_milestone_allowed must match source review."
        )
    if record.decision == _READY_DECISION and record.blockers:
        raise ValidationError("ready artifact records must not contain blockers.")
    if record.decision != _READY_DECISION and not record.blockers:
        raise ValidationError("blocked artifact records must contain blockers.")
    if record.decision == _READY_DECISION:
        _validate_ready_record(record)


def _validate_ready_record(record: EtfSmaNextExperimentReviewArtifactRecord) -> None:
    signal = record.offline_signal_evidence
    reset = record.reset_evidence

    if reset.evidence_id != _M367_SOURCE_EVIDENCE_ID:
        raise ValidationError("ready records require explicit M366 evidence id.")
    if reset.classification != _CLEAN_RESET_CLASSIFICATION:
        raise ValidationError("ready records require flat-clean reset evidence.")
    if signal.status != "bullish_risk_on" or not signal.actionable_risk_on:
        raise ValidationError("ready records require actionable risk-on signal evidence.")
    if signal.short_sma is None or signal.long_sma is None:
        raise ValidationError("ready records require both SMA values.")
    if signal.short_sma <= signal.long_sma:
        raise ValidationError("ready records require short_sma above long_sma.")


def _prepare_output_parent(
    output_path: Path,
    config: EtfSmaNextExperimentReviewArtifactConfig,
) -> bool:
    parent = output_path.parent
    if parent == Path(".") or parent.exists():
        return False
    if not config.create_parent_dirs:
        raise ValidationError("output parent directory does not exist.")

    parent.mkdir(parents=True, exist_ok=True)
    return True


def _write_line(output_path: Path, line: str, *, append: bool) -> None:
    if output_path.exists() and not append:
        raise ValidationError("output path exists; pass append=True to append.")

    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8", newline="\n") as target:
        target.write(line)


def _output_path(value: object) -> Path:
    if type(value) is not str and not isinstance(value, Path):
        raise ValidationError("output_path must be a Path or string.")

    return Path(value)


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


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    if type(value) is not str or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")

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
    for index, item in enumerate(items):
        _required_string(item, f"{field_name}[{index}]")
    if len(frozenset(items)) != len(items):
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return items


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name, allow_empty=False)
    if items != expected:
        raise ValidationError(f"{field_name} must match the required values.")

    return items


def _symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    if symbol != symbol.upper():
        raise ValidationError("symbol must use uppercase deterministic text.")
    if any(character.isspace() for character in symbol):
        raise ValidationError("symbol must not contain whitespace.")

    return symbol


def _symbol_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name, allow_empty=allow_empty)
    return tuple(_symbol(item) for item in items)


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")

    return value


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")

    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")

    return False


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _fixed_int(value: object, expected: int, field_name: str) -> int:
    checked_value = _non_negative_int(value, field_name)
    if checked_value != expected:
        raise ValidationError(f"{field_name} must be {expected}.")

    return checked_value


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be a positive integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")

    return value


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    checked_value = _optional_decimal(value, field_name)
    if checked_value is None or checked_value <= _ZERO:
        raise ValidationError(f"{field_name} must be a positive Decimal.")

    return checked_value


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    checked_value = _optional_decimal(value, field_name)
    if checked_value is not None and checked_value <= _ZERO:
        raise ValidationError(f"{field_name} must be a positive Decimal.")

    return checked_value


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)


def _primitive_dict(value: object, field_name: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ValidationError(f"{field_name} must be a dict.")

    copied: dict[str, object] = {}
    for key, item in value.items():
        if type(key) is not str:
            raise ValidationError(f"{field_name} keys must be strings.")
        copied[key] = _primitive_value(item, field_name)

    return copied


def _primitive_value(value: object, field_name: str) -> object:
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is list:
        return [_primitive_value(item, field_name) for item in value]
    if type(value) is dict:
        return _primitive_dict(value, field_name)

    raise ValidationError(f"{field_name} must contain only primitive values.")


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
        checked_value = _required_string(value, "blocker")
        if checked_value not in deduped:
            deduped.append(checked_value)

    return tuple(deduped)
