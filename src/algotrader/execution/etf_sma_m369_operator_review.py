"""M369 explicit operator review for tiny SPY paper submit path."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_M369_OPERATOR_REVIEW_LABELS",
    "ETF_SMA_M369_OPERATOR_REVIEW_LIMITATIONS",
    "EtfSmaM369ChecklistItem",
    "EtfSmaM369OperatorReview",
    "EtfSmaM369OperatorReviewConfig",
    "EtfSmaM369OperatorReviewWriteConfig",
    "EtfSmaM369OperatorReviewWriteResult",
    "EtfSmaM369SnapshotSummary",
    "build_etf_sma_m369_operator_review",
    "load_m368b_preview_artifact_record",
    "load_m368b_snapshot_summary",
    "render_etf_sma_m369_operator_review_json",
    "render_etf_sma_m369_operator_review_text",
    "write_etf_sma_m369_operator_review",
]


ETF_SMA_M369_OPERATOR_REVIEW_LABELS = (
    "paper_lab_only",
    "operator_review_only",
    "not_live_authorized",
    "profit_claim=none",
)
ETF_SMA_M369_OPERATOR_REVIEW_LIMITATIONS = (
    "operator_review_only",
    "not_submit_authorization",
    "separate_future_submit_milestone_required",
    "paper_submit_not_performed",
    "no_broker_preview_or_staging",
    "no_broker_action_authorized",
    "no_cancel_replace_close_liquidate_retry_or_delete",
    "no_account_position_order_fill_or_portfolio_mutation",
    "not_live_authorization",
    "not_profit_evidence",
    "m368a_signal_was_deterministic_fixture_not_live_market_data",
)

_REVIEW_VERSION = "etf_sma_m369_tiny_spy_paper_submit_operator_review_v1"
_RECORD_TYPE = "etf_sma_m369_tiny_spy_paper_submit_operator_review"
_DEFAULT_RUN_ID = "m369_tiny_spy_paper_submit_operator_review"
_DEFAULT_PREVIEW_PATH = "runs/paper_lab/m368b_spy_etf_sma_broker_preview_only.jsonl"
_DEFAULT_SNAPSHOT_PATH = "runs/paper_lab/m368b_fresh_read_only_paper_snapshot.jsonl"
_DEFAULT_OUTPUT_PATH = "runs/paper_lab/m369_tiny_spy_paper_submit_operator_review.jsonl"
_M368B_PREVIEW_RUN_ID = "m368b_spy_etf_sma_broker_preview_only"
_M368B_SNAPSHOT_RUN_ID = "m368b_fresh_read_only_paper_snapshot"
_M368B_PREVIEW_VERSION = "etf_sma_m368_paper_broker_preview_v1"
_M368B_RECORD_TYPE = "etf_sma_m368_paper_broker_preview"
_M368B_READY_DECISION = "ready_for_operator_review_before_tiny_spy_paper_submit"
_M368B_REQUIRED_NEXT_MILESTONE = "M369 - Explicit operator review for tiny SPY paper submit"
_M368B_REQUIRED_LABELS = (
    "paper_lab_only",
    "preview_only",
    "not_live_authorized",
    "profit_claim=none",
)
_M368A_READY_DECISION = "ready_for_separate_broker_preview_milestone"
_M368A_REQUIRED_NEXT_MILESTONE = (
    "M368 - SPY ETF/SMA broker-facing preview-only milestone"
)
_READY_DECISION = "ready_for_separate_tiny_spy_paper_submit_milestone"
_BLOCKED_DECISION = "blocked_before_separate_tiny_spy_paper_submit_milestone"
_READY_REQUIRED_NEXT_MILESTONE = (
    "M370 - Tiny SPY paper submit only after explicit operator approval"
)
_BLOCKED_REQUIRED_NEXT_MILESTONE = (
    "Resolve M369 operator-review blockers before any future submit milestone"
)
_READY_REASON = (
    "M368B preview and fresh paper snapshot are clean, SPY-only, capped at "
    "25.00, non-mutating, and ready only for a separate M370 submit milestone; "
    "M369 authorizes no submit."
)
_PROFIT_CLAIM = "none"
_SYMBOL = "SPY"
_ASSET_CLASS = "equity"
_SIDE = "buy"
_ORDER_TYPE = "market"
_TIME_IN_FORCE = "day"
_MAX_NOTIONAL = Decimal("25.00")
_SNAPSHOT_EVENTS = (
    "paper_lab_snapshot_requested",
    "paper_lab_snapshot_account_observed",
    "paper_lab_snapshot_positions_observed",
    "paper_lab_snapshot_orders_observed",
)
_ACCEPTED_SNAPSHOT_STATUSES = (
    "paper_lab_flat_clean",
    "read_only_snapshot_completed_for_manual_review",
)
_FORBIDDEN_LIVE_AUTHORIZATION_VALUES = {
    "authorized_for_live_trading",
    "live_authorized",
    "live_authorized=true",
    "live_trading_authorized",
}


@dataclass(frozen=True, slots=True)
class EtfSmaM369OperatorReviewConfig:
    """Static M369 operator-review gates for committed M368B evidence."""

    run_id: str = _DEFAULT_RUN_ID
    source_m368b_preview_path: Path | str = _DEFAULT_PREVIEW_PATH
    source_m368b_snapshot_path: Path | str = _DEFAULT_SNAPSHOT_PATH
    source_m368b_preview_run_id: str = _M368B_PREVIEW_RUN_ID
    source_m368b_snapshot_run_id: str = _M368B_SNAPSHOT_RUN_ID
    max_notional: Decimal = _MAX_NOTIONAL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_m368b_preview_path",
            _path(self.source_m368b_preview_path, "source_m368b_preview_path"),
        )
        object.__setattr__(
            self,
            "source_m368b_snapshot_path",
            _path(self.source_m368b_snapshot_path, "source_m368b_snapshot_path"),
        )
        object.__setattr__(
            self,
            "source_m368b_preview_run_id",
            _required_string(
                self.source_m368b_preview_run_id,
                "source_m368b_preview_run_id",
            ),
        )
        object.__setattr__(
            self,
            "source_m368b_snapshot_run_id",
            _required_string(
                self.source_m368b_snapshot_run_id,
                "source_m368b_snapshot_run_id",
            ),
        )
        object.__setattr__(
            self,
            "max_notional",
            _positive_capped_decimal(self.max_notional, "max_notional"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return primitive config metadata."""

        return {
            "run_id": self.run_id,
            "source_m368b_preview_path": str(self.source_m368b_preview_path),
            "source_m368b_snapshot_path": str(self.source_m368b_snapshot_path),
            "source_m368b_preview_run_id": self.source_m368b_preview_run_id,
            "source_m368b_snapshot_run_id": self.source_m368b_snapshot_run_id,
            "max_notional": str(self.max_notional),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaM369OperatorReviewWriteConfig:
    """Local JSONL output target for the ignored M369 artifact."""

    output_path: Path | str = _DEFAULT_OUTPUT_PATH
    append: bool = False
    overwrite: bool = False
    create_parent_dirs: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "output_path",
            _path(self.output_path, "output_path"),
        )
        object.__setattr__(self, "append", _bool(self.append, "append"))
        object.__setattr__(self, "overwrite", _bool(self.overwrite, "overwrite"))
        object.__setattr__(
            self,
            "create_parent_dirs",
            _bool(self.create_parent_dirs, "create_parent_dirs"),
        )
        if self.append and self.overwrite:
            raise ValidationError("append and overwrite cannot both be true.")


@dataclass(frozen=True, slots=True)
class EtfSmaM369OperatorReviewWriteResult:
    """Primitive write result for the M369 JSONL artifact."""

    output_path: Path
    record_count: int
    bytes_written: int
    append: bool
    overwrite: bool
    created_parent_dirs: bool
    newline_terminated: bool
    submit_authorized: bool
    submitted: bool
    mutated: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _path(self.output_path, "output_path"))
        object.__setattr__(self, "record_count", _fixed_int(self.record_count, 1, "record_count"))
        object.__setattr__(
            self,
            "bytes_written",
            _positive_int(self.bytes_written, "bytes_written"),
        )
        object.__setattr__(self, "append", _bool(self.append, "append"))
        object.__setattr__(self, "overwrite", _bool(self.overwrite, "overwrite"))
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
        for field_name in ("submit_authorized", "submitted", "mutated"):
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
            )

    def to_dict(self) -> dict[str, object]:
        """Return primitive write metadata."""

        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "append": self.append,
            "overwrite": self.overwrite,
            "created_parent_dirs": self.created_parent_dirs,
            "newline_terminated": self.newline_terminated,
            "submit_authorized": self.submit_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
        }


@dataclass(frozen=True, slots=True)
class EtfSmaM369SnapshotSummary:
    """Explicit flat/clean M368B fresh paper snapshot evidence."""

    snapshot_run_id: str
    records_observed: bool
    event_types: tuple[str, ...]
    account_observed: bool
    positions_observed: bool
    orders_observed: bool
    cash: Decimal | None
    currency: str | None
    position_count: int | None
    position_symbols: tuple[str, ...] | None
    open_order_count: int | None
    recent_order_count: int | None
    recent_order_query_metadata_complete: bool
    credentials_redacted_present: bool
    unavailable_observations: tuple[str, ...]
    submitted: bool
    mutated: bool
    ok: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_run_id",
            _required_string(self.snapshot_run_id, "snapshot_run_id"),
        )
        object.__setattr__(
            self,
            "records_observed",
            _bool(self.records_observed, "records_observed"),
        )
        object.__setattr__(
            self,
            "event_types",
            _string_tuple(self.event_types, "event_types", allow_empty=False),
        )
        for field_name in (
            "account_observed",
            "positions_observed",
            "orders_observed",
            "recent_order_query_metadata_complete",
            "credentials_redacted_present",
            "submitted",
            "mutated",
            "ok",
        ):
            object.__setattr__(self, field_name, _bool(getattr(self, field_name), field_name))
        object.__setattr__(self, "cash", _optional_decimal(self.cash, "cash"))
        object.__setattr__(self, "currency", _optional_string(self.currency, "currency"))
        object.__setattr__(
            self,
            "position_count",
            _optional_non_negative_int(self.position_count, "position_count"),
        )
        object.__setattr__(
            self,
            "position_symbols",
            _optional_string_tuple(self.position_symbols, "position_symbols"),
        )
        object.__setattr__(
            self,
            "open_order_count",
            _optional_non_negative_int(self.open_order_count, "open_order_count"),
        )
        object.__setattr__(
            self,
            "recent_order_count",
            _optional_non_negative_int(self.recent_order_count, "recent_order_count"),
        )
        object.__setattr__(
            self,
            "unavailable_observations",
            _string_tuple(
                self.unavailable_observations,
                "unavailable_observations",
                allow_empty=True,
            ),
        )

    def blockers(self) -> tuple[str, ...]:
        """Return snapshot blockers that fail closed before submit review."""

        blockers: list[str] = []
        _append_if(blockers, not self.records_observed, "snapshot_records_not_observed")
        _append_if(blockers, not self.ok, "snapshot_not_ok")
        _append_if(
            blockers,
            self.snapshot_run_id != _M368B_SNAPSHOT_RUN_ID,
            "snapshot_run_id_unexpected",
        )
        _append_if(blockers, not self.account_observed, "snapshot_account_not_observed")
        _append_if(
            blockers,
            not self.positions_observed,
            "snapshot_positions_not_observed",
        )
        _append_if(blockers, not self.orders_observed, "snapshot_orders_not_observed")
        _append_if(
            blockers,
            self.cash is None or self.currency is None,
            "snapshot_cash_or_currency_missing",
        )
        if self.position_count is None:
            blockers.append("snapshot_position_count_missing_or_invalid")
        elif self.position_count != 0:
            blockers.append("snapshot_positions_present")
        if self.position_symbols is None:
            blockers.append("snapshot_position_symbols_missing_or_invalid")
        elif self.position_symbols:
            blockers.append("snapshot_position_symbols_present")
        if self.open_order_count is None:
            blockers.append("snapshot_open_order_count_missing_or_invalid")
        elif self.open_order_count != 0:
            blockers.append("snapshot_open_orders_present")
        if self.recent_order_count is None:
            blockers.append("snapshot_recent_order_count_missing_or_invalid")
        elif self.recent_order_count != 0:
            blockers.append("snapshot_recent_orders_present")
        _append_if(
            blockers,
            not self.recent_order_query_metadata_complete,
            "snapshot_recent_order_metadata_incomplete",
        )
        _append_if(
            blockers,
            not self.credentials_redacted_present,
            "snapshot_credentials_not_redacted",
        )
        _append_if(
            blockers,
            bool(self.unavailable_observations),
            "snapshot_unavailable_observations_present",
        )
        _append_if(blockers, self.submitted, "snapshot_submitted_not_false")
        _append_if(blockers, self.mutated, "snapshot_mutated_not_false")
        return tuple(blockers)

    def to_dict(self) -> dict[str, object]:
        """Return primitive snapshot summary metadata."""

        return {
            "snapshot_run_id": self.snapshot_run_id,
            "records_observed": self.records_observed,
            "event_types": list(self.event_types),
            "account_observed": self.account_observed,
            "positions_observed": self.positions_observed,
            "orders_observed": self.orders_observed,
            "cash": _decimal_text(self.cash),
            "currency": self.currency,
            "position_count": self.position_count,
            "position_symbols": (
                None if self.position_symbols is None else list(self.position_symbols)
            ),
            "open_order_count": self.open_order_count,
            "recent_order_count": self.recent_order_count,
            "recent_order_query_metadata_complete": (
                self.recent_order_query_metadata_complete
            ),
            "credentials_redacted_present": self.credentials_redacted_present,
            "unavailable_observations": list(self.unavailable_observations),
            "submitted": self.submitted,
            "mutated": self.mutated,
            "ok": self.ok,
            "blockers": list(self.blockers()),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaM369ChecklistItem:
    """One operator-readable M369 checklist item."""

    item: str
    passed: bool
    evidence: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "item", _required_string(self.item, "item"))
        object.__setattr__(self, "passed", _bool(self.passed, "passed"))
        object.__setattr__(self, "evidence", _required_string(self.evidence, "evidence"))

    def to_dict(self) -> dict[str, object]:
        """Return primitive checklist metadata."""

        return {
            "item": self.item,
            "passed": self.passed,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class EtfSmaM369OperatorReview:
    """Immutable M369 review result with no submit authority."""

    review_version: str
    record_type: str
    run_id: str
    source_m368b_preview_run_id: str
    source_m368b_preview_path: str
    source_m368b_snapshot_run_id: str
    source_m368b_snapshot_path: str
    source_m368a_run_id: str
    source_m368a_evidence_ids: tuple[str, ...]
    source_m368a_signal_evidence_id: str
    source_m368a_signal_caveat: str
    snapshot_summary: EtfSmaM369SnapshotSummary
    proposed_order: Mapping[str, object] | None
    symbol: str
    asset_class: str
    side: str
    order_type: str
    time_in_force: str
    notional_cap: Decimal | None
    labels: tuple[str, ...]
    checklist: tuple[EtfSmaM369ChecklistItem, ...]
    decision: str
    reason: str
    blockers: tuple[str, ...]
    required_next_milestone: str
    operator_review_ready: bool
    separate_submit_milestone_required: bool
    submit_authorized: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    live_authorized: bool
    profit_claim: str
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "review_version",
            _fixed_string(self.review_version, _REVIEW_VERSION, "review_version"),
        )
        object.__setattr__(
            self,
            "record_type",
            _fixed_string(self.record_type, _RECORD_TYPE, "record_type"),
        )
        for field_name in (
            "run_id",
            "source_m368b_preview_run_id",
            "source_m368b_preview_path",
            "source_m368b_snapshot_run_id",
            "source_m368b_snapshot_path",
            "source_m368a_run_id",
            "source_m368a_signal_evidence_id",
            "source_m368a_signal_caveat",
            "symbol",
            "asset_class",
            "side",
            "order_type",
            "time_in_force",
            "reason",
        ):
            object.__setattr__(self, field_name, _required_string(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "source_m368a_evidence_ids",
            _string_tuple(
                self.source_m368a_evidence_ids,
                "source_m368a_evidence_ids",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "snapshot_summary",
            _snapshot_summary(self.snapshot_summary),
        )
        object.__setattr__(
            self,
            "proposed_order",
            _optional_proposed_order(self.proposed_order),
        )
        object.__setattr__(
            self,
            "notional_cap",
            _optional_positive_decimal(self.notional_cap, "notional_cap"),
        )
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                ETF_SMA_M369_OPERATOR_REVIEW_LABELS,
                "labels",
            ),
        )
        object.__setattr__(self, "checklist", _checklist_tuple(self.checklist))
        object.__setattr__(self, "decision", _decision(self.decision))
        object.__setattr__(
            self,
            "blockers",
            _string_tuple(self.blockers, "blockers", allow_empty=True),
        )
        object.__setattr__(
            self,
            "required_next_milestone",
            _required_next_milestone(self.required_next_milestone, self.decision),
        )
        object.__setattr__(
            self,
            "operator_review_ready",
            _bool(self.operator_review_ready, "operator_review_ready"),
        )
        object.__setattr__(
            self,
            "separate_submit_milestone_required",
            _true_bool(
                self.separate_submit_milestone_required,
                "separate_submit_milestone_required",
            ),
        )
        for field_name in (
            "submit_authorized",
            "submitted",
            "mutated",
            "broker_action_performed",
            "broker_preview_performed",
            "live_authorized",
        ):
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "profit_claim",
            _fixed_string(self.profit_claim, _PROFIT_CLAIM, "profit_claim"),
        )
        object.__setattr__(
            self,
            "limitations",
            _fixed_string_tuple(
                self.limitations,
                ETF_SMA_M369_OPERATOR_REVIEW_LIMITATIONS,
                "limitations",
            ),
        )
        _validate_review_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only review payload."""

        return {
            "review_version": self.review_version,
            "record_type": self.record_type,
            "run_id": self.run_id,
            "source_m368b_preview_run_id": self.source_m368b_preview_run_id,
            "source_m368b_preview_path": self.source_m368b_preview_path,
            "source_m368b_snapshot_run_id": self.source_m368b_snapshot_run_id,
            "source_m368b_snapshot_path": self.source_m368b_snapshot_path,
            "source_m368a_run_id": self.source_m368a_run_id,
            "source_m368a_evidence_ids": list(self.source_m368a_evidence_ids),
            "source_m368a_signal_evidence_id": (
                self.source_m368a_signal_evidence_id
            ),
            "source_m368a_signal_caveat": self.source_m368a_signal_caveat,
            "snapshot_summary": self.snapshot_summary.to_dict(),
            "proposed_order": _json_safe(self.proposed_order),
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "notional_cap": _decimal_text(self.notional_cap),
            "labels": list(self.labels),
            "checklist": [item.to_dict() for item in self.checklist],
            "decision": self.decision,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "required_next_milestone": self.required_next_milestone,
            "operator_review_ready": self.operator_review_ready,
            "separate_submit_milestone_required": (
                self.separate_submit_milestone_required
            ),
            "submit_authorized": self.submit_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "live_authorized": self.live_authorized,
            "profit_claim": self.profit_claim,
            "limitations": list(self.limitations),
        }


def load_m368b_preview_artifact_record(
    path: Path | str = _DEFAULT_PREVIEW_PATH,
    *,
    run_id: str = _M368B_PREVIEW_RUN_ID,
) -> Mapping[str, object]:
    """Read exactly one local M368B preview JSONL record."""

    checked_path = _path(path, "path")
    checked_run_id = _required_string(run_id, "run_id")
    records = tuple(
        record
        for record in _jsonl_records(checked_path, "M368B preview run log")
        if record.get("run_id") == checked_run_id
    )
    if len(records) != 1:
        raise ValidationError("expected exactly one M368B preview record to review.")
    return records[0]


def load_m368b_snapshot_summary(
    path: Path | str = _DEFAULT_SNAPSHOT_PATH,
    *,
    run_id: str = _M368B_SNAPSHOT_RUN_ID,
) -> EtfSmaM369SnapshotSummary:
    """Read the local M368B snapshot JSONL and return a flat/clean summary."""

    checked_path = _path(path, "path")
    checked_run_id = _required_string(run_id, "run_id")
    records = tuple(
        record
        for record in _jsonl_records(checked_path, "M368B snapshot run log")
        if record.get("run_id") == checked_run_id
    )
    if len(records) != len(_SNAPSHOT_EVENTS):
        raise ValidationError("expected exactly four M368B snapshot records.")

    event_records: dict[str, Mapping[str, object]] = {}
    for event_type in _SNAPSHOT_EVENTS:
        matches = tuple(record for record in records if record.get("event_type") == event_type)
        if len(matches) != 1:
            raise ValidationError(
                "M368B snapshot run log must contain each required event exactly once."
            )
        event_records[event_type] = matches[0]
    if set(event_records) != {str(record.get("event_type")) for record in records}:
        raise ValidationError("M368B snapshot run log contains unexpected events.")

    account_record = event_records["paper_lab_snapshot_account_observed"]
    positions_record = event_records["paper_lab_snapshot_positions_observed"]
    orders_record = event_records["paper_lab_snapshot_orders_observed"]
    account_payload = _optional_mapping(account_record.get("account")) or {}
    position_symbols = _optional_string_tuple_payload(
        positions_record.get("position_symbols")
    )
    recent_order_count = _int_payload(orders_record.get("recent_order_count"))
    open_order_count = _int_payload(orders_record.get("open_order_count"))
    if open_order_count is None:
        open_order_count = recent_order_count

    return EtfSmaM369SnapshotSummary(
        snapshot_run_id=checked_run_id,
        records_observed=True,
        event_types=tuple(str(record.get("event_type")) for record in records),
        account_observed=(
            all(record.get("account_observation_available") is True for record in records)
            and bool(account_payload)
        ),
        positions_observed=(
            all(record.get("positions_observation_available") is True for record in records)
            and position_symbols is not None
        ),
        orders_observed=(
            all(record.get("orders_observation_available") is True for record in records)
            and recent_order_count is not None
        ),
        cash=_decimal_payload(account_payload.get("cash")),
        currency=_optional_string_payload(account_payload.get("currency")),
        position_count=_int_payload(positions_record.get("position_count")),
        position_symbols=position_symbols,
        open_order_count=open_order_count,
        recent_order_count=recent_order_count,
        recent_order_query_metadata_complete=all(
            record.get("recent_order_query_metadata_complete") is True
            for record in records
        ),
        credentials_redacted_present=all(
            record.get("redaction") == "credentials_redacted" for record in records
        ),
        unavailable_observations=_dedupe(
            tuple(
                item
                for record in records
                for item in _string_items(record.get("unavailable_observations"))
            )
        ),
        submitted=not all(record.get("submitted") is False for record in records),
        mutated=not all(record.get("mutated") is False for record in records),
        ok=all(record.get("ok") is True for record in records),
    )


def build_etf_sma_m369_operator_review(
    m368b_preview_record: Mapping[str, object],
    snapshot_summary: EtfSmaM369SnapshotSummary,
    config: EtfSmaM369OperatorReviewConfig | None = None,
) -> EtfSmaM369OperatorReview:
    """Review M368B evidence without broker calls or submit authority."""

    checked_record = _mapping(m368b_preview_record, "m368b_preview_record")
    checked_snapshot = _snapshot_summary(snapshot_summary)
    checked_config = config or EtfSmaM369OperatorReviewConfig()
    if type(checked_config) is not EtfSmaM369OperatorReviewConfig:
        raise ValidationError("config must be an EtfSmaM369OperatorReviewConfig.")

    blockers = _review_blockers(checked_record, checked_snapshot, checked_config)
    checklist = _build_checklist(checked_record, checked_snapshot, checked_config)
    if any(not item.passed for item in checklist):
        blockers = _dedupe((*blockers, "operator_review_checklist_failed"))
    ready = not blockers
    proposed_order = _proposed_order(checked_record)
    notional_cap = _decimal_payload(checked_record.get("notional_cap"))

    return EtfSmaM369OperatorReview(
        review_version=_REVIEW_VERSION,
        record_type=_RECORD_TYPE,
        run_id=checked_config.run_id,
        source_m368b_preview_run_id=_string_payload(checked_record.get("run_id")),
        source_m368b_preview_path=str(checked_config.source_m368b_preview_path),
        source_m368b_snapshot_run_id=checked_snapshot.snapshot_run_id,
        source_m368b_snapshot_path=str(checked_config.source_m368b_snapshot_path),
        source_m368a_run_id=_string_payload(checked_record.get("source_m368a_run_id")),
        source_m368a_evidence_ids=_string_items(
            checked_record.get("source_m368a_evidence_ids")
        ),
        source_m368a_signal_evidence_id=_string_payload(
            checked_record.get("source_m368a_signal_evidence_id")
        ),
        source_m368a_signal_caveat=(
            "M368A actionable SMA evidence was deterministic fixture evidence, "
            "not live market data, not profitability evidence, and not live "
            "trading authorization."
        ),
        snapshot_summary=checked_snapshot,
        proposed_order=proposed_order,
        symbol=_string_payload(checked_record.get("symbol")),
        asset_class=_string_payload(checked_record.get("asset_class")),
        side=_string_payload(checked_record.get("side")),
        order_type=_string_payload(checked_record.get("order_type")),
        time_in_force=_string_payload(checked_record.get("time_in_force")),
        notional_cap=notional_cap,
        labels=ETF_SMA_M369_OPERATOR_REVIEW_LABELS,
        checklist=checklist,
        decision=_READY_DECISION if ready else _BLOCKED_DECISION,
        reason=_READY_REASON if ready else _blocked_reason(blockers),
        blockers=blockers,
        required_next_milestone=(
            _READY_REQUIRED_NEXT_MILESTONE
            if ready
            else _BLOCKED_REQUIRED_NEXT_MILESTONE
        ),
        operator_review_ready=ready,
        separate_submit_milestone_required=True,
        submit_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_preview_performed=False,
        live_authorized=False,
        profit_claim=_PROFIT_CLAIM,
        limitations=ETF_SMA_M369_OPERATOR_REVIEW_LIMITATIONS,
    )


def render_etf_sma_m369_operator_review_json(
    review: EtfSmaM369OperatorReview,
) -> str:
    """Render one newline-free deterministic JSON object."""

    checked_review = _review(review)
    return json.dumps(
        checked_review.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )


def render_etf_sma_m369_operator_review_text(
    review: EtfSmaM369OperatorReview,
) -> str:
    """Render a compact operator-readable M369 review summary."""

    checked_review = _review(review)
    checklist = [
        f"checklist.{item.item}: {'pass' if item.passed else 'fail'}"
        for item in checked_review.checklist
    ]
    blockers = ",".join(checked_review.blockers) if checked_review.blockers else "none"
    lines = [
        "M369 explicit operator review for tiny SPY paper submit",
        f"run_id: {checked_review.run_id}",
        f"decision: {checked_review.decision}",
        f"reason: {checked_review.reason}",
        f"blockers: {blockers}",
        f"source_m368b_preview_run_id: {checked_review.source_m368b_preview_run_id}",
        f"source_m368b_snapshot_run_id: {checked_review.source_m368b_snapshot_run_id}",
        f"source_m368a_signal_evidence_id: {checked_review.source_m368a_signal_evidence_id}",
        f"symbol: {checked_review.symbol}",
        f"asset_class: {checked_review.asset_class}",
        f"side: {checked_review.side}",
        f"order_type: {checked_review.order_type}",
        f"time_in_force: {checked_review.time_in_force}",
        f"notional_cap: {_decimal_text(checked_review.notional_cap) or 'none'}",
        f"position_count: {checked_review.snapshot_summary.position_count}",
        f"position_symbols: {_joined(checked_review.snapshot_summary.position_symbols)}",
        f"open_order_count: {checked_review.snapshot_summary.open_order_count}",
        f"recent_order_count: {checked_review.snapshot_summary.recent_order_count}",
        f"operator_review_ready: {_bool_text(checked_review.operator_review_ready)}",
        "separate_submit_milestone_required: "
        f"{_bool_text(checked_review.separate_submit_milestone_required)}",
        f"submit_authorized: {_bool_text(checked_review.submit_authorized)}",
        f"submitted: {_bool_text(checked_review.submitted)}",
        f"mutated: {_bool_text(checked_review.mutated)}",
        f"required_next_milestone: {checked_review.required_next_milestone}",
        *checklist,
    ]
    return "\n".join(lines)


def write_etf_sma_m369_operator_review(
    review: EtfSmaM369OperatorReview,
    config: EtfSmaM369OperatorReviewWriteConfig | None = None,
) -> EtfSmaM369OperatorReviewWriteResult:
    """Write one deterministic M369 review record to a local JSONL file."""

    checked_review = _review(review)
    checked_config = config or EtfSmaM369OperatorReviewWriteConfig()
    if type(checked_config) is not EtfSmaM369OperatorReviewWriteConfig:
        raise ValidationError("config must be an EtfSmaM369OperatorReviewWriteConfig.")
    line = render_etf_sma_m369_operator_review_json(checked_review) + "\n"
    created_parent_dirs = _prepare_output_parent(
        checked_config.output_path,
        checked_config,
    )
    _write_line(
        checked_config.output_path,
        line,
        append=checked_config.append,
        overwrite=checked_config.overwrite,
    )
    return EtfSmaM369OperatorReviewWriteResult(
        output_path=checked_config.output_path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        append=checked_config.append,
        overwrite=checked_config.overwrite,
        created_parent_dirs=created_parent_dirs,
        newline_terminated=line.endswith("\n"),
        submit_authorized=False,
        submitted=False,
        mutated=False,
    )


def _review_blockers(
    record: Mapping[str, object],
    snapshot: EtfSmaM369SnapshotSummary,
    config: EtfSmaM369OperatorReviewConfig,
) -> tuple[str, ...]:
    blockers: list[str] = []
    labels = _string_items(record.get("labels"))
    allowlist = _string_items(record.get("allowlist"))
    preview_blockers = _string_items(record.get("blockers"))
    nested_snapshot = _optional_mapping(record.get("fresh_paper_snapshot_summary"))
    preview_order = _optional_mapping(record.get("preview_order"))
    notional_cap = _decimal_payload(record.get("notional_cap"))
    notional = _decimal_payload(record.get("notional"))

    _append_if(
        blockers,
        record.get("preview_version") != _M368B_PREVIEW_VERSION,
        "m368b_preview_version_unexpected",
    )
    _append_if(
        blockers,
        record.get("record_type") != _M368B_RECORD_TYPE,
        "m368b_record_type_unexpected",
    )
    _append_if(
        blockers,
        record.get("run_id") != config.source_m368b_preview_run_id,
        "m368b_preview_run_id_unexpected",
    )
    _append_if(
        blockers,
        snapshot.snapshot_run_id != config.source_m368b_snapshot_run_id,
        "m368b_snapshot_run_id_unexpected",
    )
    _append_if(
        blockers,
        record.get("decision") != _M368B_READY_DECISION,
        "m368b_preview_decision_not_ready",
    )
    _append_if(
        blockers,
        record.get("required_next_milestone") != _M368B_REQUIRED_NEXT_MILESTONE,
        "m368b_required_next_milestone_unexpected",
    )
    _append_if(
        blockers,
        bool(preview_blockers),
        "m368b_preview_blockers_present",
    )
    _append_if(
        blockers,
        record.get("source_m368a_decision") != _M368A_READY_DECISION,
        "m368a_source_decision_not_ready",
    )
    _append_if(
        blockers,
        record.get("source_m368a_required_next_milestone")
        != _M368A_REQUIRED_NEXT_MILESTONE,
        "m368a_source_required_next_milestone_unexpected",
    )
    _append_if(
        blockers,
        not _string_items(record.get("source_m368a_evidence_ids")),
        "m368a_source_evidence_ids_missing",
    )
    _append_if(
        blockers,
        not _string_payload(record.get("source_m368a_signal_evidence_id")),
        "m368a_source_signal_evidence_id_missing",
    )
    _append_if(
        blockers,
        record.get("source_m368a_submit_authorized") is not False,
        "m368a_source_submit_authorized_not_false",
    )
    _append_if(
        blockers,
        record.get("source_m368a_submitted") is not False,
        "m368a_source_submitted_not_false",
    )
    _append_if(
        blockers,
        record.get("source_m368a_mutated") is not False,
        "m368a_source_mutated_not_false",
    )
    _append_if(
        blockers,
        record.get("offline_signal_status") != "bullish_risk_on",
        "m368a_fixture_signal_status_not_bullish",
    )
    _append_if(
        blockers,
        record.get("offline_signal_actionable_risk_on") is not True,
        "m368a_fixture_signal_not_actionable",
    )
    _append_if(blockers, record.get("symbol") != _SYMBOL, "symbol_not_spy")
    _append_if(blockers, record.get("asset_class") != _ASSET_CLASS, "asset_class_not_equity")
    _append_if(blockers, record.get("side") != _SIDE, "side_not_buy")
    _append_if(blockers, record.get("order_type") != _ORDER_TYPE, "order_type_not_market")
    _append_if(
        blockers,
        record.get("time_in_force") != _TIME_IN_FORCE,
        "time_in_force_not_day",
    )
    _append_if(blockers, allowlist != (_SYMBOL,), "allowlist_not_spy_only")
    if notional_cap is None:
        blockers.append("notional_cap_missing_or_invalid")
    elif notional_cap > config.max_notional:
        blockers.append("notional_cap_above_25")
    if notional is None:
        blockers.append("notional_missing_or_invalid")
    elif notional > config.max_notional:
        blockers.append("notional_above_25")
    if notional is not None and notional_cap is not None and notional > notional_cap:
        blockers.append("notional_above_cap")
    _append_if(
        blockers,
        record.get("preview_order") is None,
        "preview_order_missing",
    )
    blockers.extend(_preview_order_blockers(preview_order, config.max_notional))
    for label in _M368B_REQUIRED_LABELS:
        if label not in labels:
            blockers.append(f"m368b_label_missing_{label}")
    _append_if(blockers, record.get("preview_only") is not True, "preview_only_not_true")
    _append_if(blockers, record.get("paper_only") is not True, "paper_only_not_true")
    _append_if(
        blockers,
        record.get("not_live_authorized") is not True,
        "not_live_authorized_not_true",
    )
    _append_if(blockers, record.get("profit_claim") != _PROFIT_CLAIM, "profit_claim_not_none")
    _append_if(
        blockers,
        record.get("submit_authorized") is not False,
        "m368b_submit_authorized_not_false",
    )
    _append_if(blockers, record.get("submitted") is not False, "m368b_submitted_not_false")
    _append_if(blockers, record.get("mutated") is not False, "m368b_mutated_not_false")
    _append_if(
        blockers,
        record.get("broker_action_performed") is not False,
        "m368b_broker_action_performed_not_false",
    )
    _append_if(
        blockers,
        record.get("broker_preview_performed") is not False,
        "m368b_broker_preview_performed_not_false",
    )
    _append_if(
        blockers,
        record.get("local_payload_preview_performed") is not True,
        "m368b_local_payload_preview_not_performed",
    )
    _append_if(
        blockers,
        _contains_forbidden_live_authorization(record),
        "live_authorization_evidence_present",
    )
    _append_if(
        blockers,
        _contains_non_none_profit_claim(record),
        "non_none_profit_claim_present",
    )

    blockers.extend(snapshot.blockers())
    blockers.extend(_nested_snapshot_blockers(nested_snapshot, snapshot))

    return _dedupe(tuple(blockers))


def _nested_snapshot_blockers(
    nested: Mapping[str, object] | None,
    snapshot: EtfSmaM369SnapshotSummary,
) -> tuple[str, ...]:
    if nested is None:
        return ("m368b_preview_snapshot_summary_missing",)

    blockers: list[str] = []
    nested_blockers = _string_items(nested.get("blockers"))
    _append_if(
        blockers,
        nested.get("snapshot_evidence_id") != snapshot.snapshot_run_id,
        "m368b_preview_snapshot_evidence_id_mismatch",
    )
    _append_if(
        blockers,
        _string_payload(nested.get("fresh_snapshot_status"))
        not in _ACCEPTED_SNAPSHOT_STATUSES,
        "m368b_preview_snapshot_status_unexpected",
    )
    _append_if(
        blockers,
        bool(nested_blockers),
        "m368b_preview_snapshot_blockers_present",
    )
    _append_if(
        blockers,
        nested.get("account_observation_available") is not True,
        "m368b_preview_snapshot_account_missing",
    )
    _append_if(
        blockers,
        nested.get("positions_observation_available") is not True,
        "m368b_preview_snapshot_positions_missing",
    )
    _append_if(
        blockers,
        nested.get("orders_observation_available") is not True,
        "m368b_preview_snapshot_orders_missing",
    )
    _append_if(
        blockers,
        _decimal_payload(nested.get("cash")) != snapshot.cash,
        "m368b_preview_snapshot_cash_mismatch",
    )
    _append_if(
        blockers,
        _optional_string_payload(nested.get("currency")) != snapshot.currency,
        "m368b_preview_snapshot_currency_mismatch",
    )
    _append_if(
        blockers,
        _int_payload(nested.get("position_count")) != snapshot.position_count,
        "m368b_preview_snapshot_position_count_mismatch",
    )
    _append_if(
        blockers,
        _optional_string_tuple_payload(nested.get("position_symbols"))
        != snapshot.position_symbols,
        "m368b_preview_snapshot_position_symbols_mismatch",
    )
    _append_if(
        blockers,
        _int_payload(nested.get("open_order_count")) != snapshot.open_order_count,
        "m368b_preview_snapshot_open_order_count_mismatch",
    )
    _append_if(
        blockers,
        nested.get("recent_order_query_metadata_complete") is not True,
        "m368b_preview_snapshot_recent_order_metadata_incomplete",
    )
    _append_if(
        blockers,
        nested.get("submitted") is not False,
        "m368b_preview_snapshot_submitted_not_false",
    )
    _append_if(
        blockers,
        nested.get("mutated") is not False,
        "m368b_preview_snapshot_mutated_not_false",
    )
    return tuple(blockers)


def _preview_order_blockers(
    preview_order: Mapping[str, object] | None,
    max_notional: Decimal,
) -> tuple[str, ...]:
    if preview_order is None:
        return ()

    blockers: list[str] = []
    _append_if(
        blockers,
        preview_order.get("symbol") != _SYMBOL,
        "preview_order_symbol_not_spy",
    )
    _append_if(
        blockers,
        preview_order.get("asset_class") != _ASSET_CLASS,
        "preview_order_asset_class_not_equity",
    )
    _append_if(
        blockers,
        preview_order.get("side") != _SIDE,
        "preview_order_side_not_buy",
    )
    _append_if(
        blockers,
        preview_order.get("order_type") != _ORDER_TYPE,
        "preview_order_order_type_not_market",
    )
    _append_if(
        blockers,
        preview_order.get("time_in_force") != _TIME_IN_FORCE,
        "preview_order_time_in_force_not_day",
    )
    notional = _decimal_payload(preview_order.get("notional"))
    if notional is None:
        blockers.append("preview_order_notional_missing_or_invalid")
    elif notional > max_notional:
        blockers.append("preview_order_notional_above_25")
    return tuple(blockers)


def _build_checklist(
    record: Mapping[str, object],
    snapshot: EtfSmaM369SnapshotSummary,
    config: EtfSmaM369OperatorReviewConfig,
) -> tuple[EtfSmaM369ChecklistItem, ...]:
    notional_cap = _decimal_payload(record.get("notional_cap"))
    preview_order = _optional_mapping(record.get("preview_order"))
    preview_order_notional = (
        _decimal_payload(preview_order.get("notional")) if preview_order else None
    )
    return (
        EtfSmaM369ChecklistItem(
            "M368A ready evidence present",
            (
                record.get("source_m368a_decision") == _M368A_READY_DECISION
                and bool(_string_items(record.get("source_m368a_evidence_ids")))
                and bool(_string_payload(record.get("source_m368a_signal_evidence_id")))
            ),
            "M368B links to M368A ready-review evidence and signal evidence id.",
        ),
        EtfSmaM369ChecklistItem(
            "M368B fresh snapshot flat/clean",
            not snapshot.blockers(),
            "Snapshot records show account/positions/orders observed and flat.",
        ),
        EtfSmaM369ChecklistItem(
            "M368B preview ready",
            (
                record.get("decision") == _M368B_READY_DECISION
                and record.get("required_next_milestone")
                == _M368B_REQUIRED_NEXT_MILESTONE
                and not _string_items(record.get("blockers"))
            ),
            "Preview decision requires M369 operator review and has no blockers.",
        ),
        EtfSmaM369ChecklistItem(
            "SPY-only scope",
            (
                record.get("symbol") == _SYMBOL
                and record.get("asset_class") == _ASSET_CLASS
                and _string_items(record.get("allowlist")) == (_SYMBOL,)
                and preview_order is not None
                and preview_order.get("symbol") == _SYMBOL
                and preview_order.get("asset_class") == _ASSET_CLASS
            ),
            "Symbol, asset class, and allowlist remain SPY/equity only.",
        ),
        EtfSmaM369ChecklistItem(
            "cap <= 25.00",
            (
                notional_cap is not None
                and notional_cap <= config.max_notional
                and preview_order_notional is not None
                and preview_order_notional <= config.max_notional
            ),
            "Preview notional cap is present and does not exceed 25.00.",
        ),
        EtfSmaM369ChecklistItem(
            "no open orders",
            (
                snapshot.open_order_count == 0
                and _int_payload(record.get("open_order_count")) == 0
            ),
            "Fresh snapshot and preview show zero open orders.",
        ),
        EtfSmaM369ChecklistItem(
            "no positions",
            (
                snapshot.position_count == 0
                and snapshot.position_symbols == ()
                and _int_payload(record.get("position_count")) == 0
                and _string_items(record.get("position_symbols")) == ()
            ),
            "Fresh snapshot and preview show no positions.",
        ),
        EtfSmaM369ChecklistItem(
            "no broker mutation",
            (
                record.get("broker_action_performed") is False
                and record.get("broker_preview_performed") is False
                and record.get("submitted") is False
                and record.get("mutated") is False
                and not snapshot.submitted
                and not snapshot.mutated
            ),
            "M368B evidence records no broker action, preview call, submit, or mutation.",
        ),
        EtfSmaM369ChecklistItem(
            "no submit authorization in this milestone",
            record.get("submit_authorized") is False,
            "M369 is operator-review-only and keeps submit_authorized=false.",
        ),
        EtfSmaM369ChecklistItem(
            "separate submit milestone required",
            record.get("required_next_milestone") == _M368B_REQUIRED_NEXT_MILESTONE,
            "Ready review may only identify a separate M370 submit milestone.",
        ),
    )


def _proposed_order(record: Mapping[str, object]) -> Mapping[str, object] | None:
    preview_order = _optional_mapping(record.get("preview_order"))
    if preview_order is not None:
        return dict(preview_order)
    return {
        "asset_class": _string_payload(record.get("asset_class")),
        "notional": _optional_text(record.get("notional_cap")),
        "order_type": _string_payload(record.get("order_type")),
        "side": _string_payload(record.get("side")),
        "symbol": _string_payload(record.get("symbol")),
        "time_in_force": _string_payload(record.get("time_in_force")),
    }


def _jsonl_records(path: Path, label: str) -> tuple[Mapping[str, object], ...]:
    if not path.exists() or not path.is_file():
        raise ValidationError(f"{label} must be an existing file.")
    records: list[Mapping[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{label} contains invalid JSON.") from exc
        records.append(_mapping(payload, label))
    return tuple(records)


def _prepare_output_parent(
    path: Path,
    config: EtfSmaM369OperatorReviewWriteConfig,
) -> bool:
    parent = path.parent
    if str(parent) in ("", ".") or parent.exists():
        return False
    if not config.create_parent_dirs:
        raise ValidationError("output parent directory does not exist.")
    parent.mkdir(parents=True, exist_ok=True)
    return True


def _write_line(path: Path, line: str, *, append: bool, overwrite: bool) -> None:
    mode = "a" if append else "w" if overwrite else "x"
    try:
        with path.open(mode, encoding="utf-8", newline="\n") as stream:
            stream.write(line)
    except FileExistsError:
        raise ValidationError("output path exists; pass append=True or overwrite=True.") from None
    except OSError as exc:
        raise ValidationError(
            f"M369 operator-review write failed: {exc.__class__.__name__}."
        ) from None


def _validate_review_consistency(review: EtfSmaM369OperatorReview) -> None:
    ready = review.decision == _READY_DECISION
    if ready and review.blockers:
        raise ValidationError("ready M369 review must not contain blockers.")
    if not ready and not review.blockers:
        raise ValidationError("blocked M369 review must contain blockers.")
    if review.operator_review_ready is not ready:
        raise ValidationError("operator_review_ready must match decision readiness.")
    if any(not item.passed for item in review.checklist) and ready:
        raise ValidationError("ready M369 review requires all checklist items to pass.")
    if ready:
        if review.source_m368b_preview_run_id != _M368B_PREVIEW_RUN_ID:
            raise ValidationError("ready M369 review requires the M368B preview run id.")
        if review.source_m368b_snapshot_run_id != _M368B_SNAPSHOT_RUN_ID:
            raise ValidationError("ready M369 review requires the M368B snapshot run id.")
        if review.proposed_order is None:
            raise ValidationError("ready M369 review requires proposed_order.")
        _require_order_shape(review.proposed_order)
        if review.symbol != _SYMBOL or review.asset_class != _ASSET_CLASS:
            raise ValidationError("ready M369 review requires SPY equity scope.")
        if review.side != _SIDE:
            raise ValidationError("ready M369 review requires buy side.")
        if review.order_type != _ORDER_TYPE or review.time_in_force != _TIME_IN_FORCE:
            raise ValidationError("ready M369 review requires market/day shape.")
        if review.notional_cap is None or review.notional_cap > _MAX_NOTIONAL:
            raise ValidationError("ready M369 review requires notional cap <= 25.00.")


def _require_order_shape(value: Mapping[str, object]) -> None:
    expected = {
        "asset_class": _ASSET_CLASS,
        "order_type": _ORDER_TYPE,
        "side": _SIDE,
        "symbol": _SYMBOL,
        "time_in_force": _TIME_IN_FORCE,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValidationError(f"proposed_order {key} is invalid.")
    notional = _decimal_payload(value.get("notional"))
    if notional is None or notional <= Decimal("0") or notional > _MAX_NOTIONAL:
        raise ValidationError("proposed_order notional is invalid.")


def _review(value: object) -> EtfSmaM369OperatorReview:
    if type(value) is not EtfSmaM369OperatorReview:
        raise ValidationError("review must be an EtfSmaM369OperatorReview.")
    return value


def _snapshot_summary(value: object) -> EtfSmaM369SnapshotSummary:
    if type(value) is not EtfSmaM369SnapshotSummary:
        raise ValidationError("snapshot_summary must be an EtfSmaM369SnapshotSummary.")
    return value


def _checklist_tuple(values: object) -> tuple[EtfSmaM369ChecklistItem, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("checklist must be a tuple or list.")
    items = tuple(values)
    if not items:
        raise ValidationError("checklist must not be empty.")
    for item in items:
        if type(item) is not EtfSmaM369ChecklistItem:
            raise ValidationError("checklist items must be EtfSmaM369ChecklistItem.")
    return items


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _optional_mapping(value: object) -> Mapping[str, object] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value
    return None


def _optional_proposed_order(value: object) -> Mapping[str, object] | None:
    if value is None:
        return None
    mapping = _mapping(value, "proposed_order")
    return dict(mapping)


def _decision(value: object) -> str:
    if type(value) is not str or value not in (_READY_DECISION, _BLOCKED_DECISION):
        raise ValidationError("decision is invalid.")
    return value


def _required_next_milestone(value: object, decision: str) -> str:
    expected = (
        _READY_REQUIRED_NEXT_MILESTONE
        if decision == _READY_DECISION
        else _BLOCKED_REQUIRED_NEXT_MILESTONE
    )
    return _fixed_string(value, expected, "required_next_milestone")


def _path(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a Path or string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} must not be empty.")
    if path.exists() and path.is_dir():
        raise ValidationError(f"{field_name} must not be a directory.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    if type(value) is not str or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _string_payload(value: object) -> str:
    return value if type(value) is str else ""


def _optional_string_payload(value: object) -> str | None:
    return value if type(value) is str and value else None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


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


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _fixed_int(value: object, expected: int, field_name: str) -> int:
    if type(value) is not int or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return value


def _optional_non_negative_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return value


def _int_payload(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value
    return None


def _positive_capped_decimal(value: object, field_name: str) -> Decimal:
    checked = _optional_decimal(value, field_name)
    if checked is None or checked <= Decimal("0") or checked > _MAX_NOTIONAL:
        raise ValidationError(f"{field_name} must be between 0 and 25.00.")
    return checked


def _optional_positive_capped_decimal(
    value: object,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None
    return _positive_capped_decimal(value, field_name)


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    checked = _optional_decimal(value, field_name)
    if checked is None or checked <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    return checked


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is Decimal:
        parsed = value
    elif type(value) is str:
        parsed = _decimal_payload(value)
        if parsed is None:
            raise ValidationError(f"{field_name} must be a Decimal.")
    else:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return parsed


def _decimal_payload(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    items = tuple(_required_string(item, field_name) for item in values)
    if not items and not allow_empty:
        raise ValidationError(f"{field_name} must not be empty.")
    return items


def _optional_string_tuple(values: object, field_name: str) -> tuple[str, ...] | None:
    if values is None:
        return None
    return _string_tuple(values, field_name, allow_empty=True)


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name, allow_empty=False)
    if _contains_forbidden_live_authorization(items):
        raise ValidationError(f"{field_name} contains live authorization.")
    if items != expected:
        raise ValidationError(f"{field_name} must match the required values.")
    return items


def _string_items(values: object) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        return ()
    return tuple(value for value in values if type(value) is str and value)


def _optional_string_tuple_payload(values: object) -> tuple[str, ...] | None:
    if values is None:
        return None
    if type(values) not in (list, tuple):
        return None
    if any(type(value) is not str for value in values):
        return None
    return tuple(values)


def _blocked_reason(blockers: tuple[str, ...]) -> str:
    first = blockers[0] if blockers else "unknown_blocker"
    return (
        f"blocked_before_m370_submit_milestone: {first}; resolve M369 "
        "operator-review blockers before any future submit milestone."
    )


def _append_if(blockers: list[str], condition: bool, blocker: str) -> None:
    if condition:
        blockers.append(blocker)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _joined(values: tuple[str, ...] | None) -> str:
    if values is None:
        return "none"
    return ",".join(values) if values else "none"


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if type(value) is tuple:
        return [_json_safe(item) for item in value]
    if type(value) is list:
        return [_json_safe(item) for item in value]
    return value


def _contains_forbidden_live_authorization(value: object) -> bool:
    for item in _walk(value):
        if type(item) is str and item.lower() in _FORBIDDEN_LIVE_AUTHORIZATION_VALUES:
            return True
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "live_authorized" and item is True:
                return True
    return False


def _contains_non_none_profit_claim(value: object) -> bool:
    for key, item in _walk_mapping_items(value):
        if key == "profit_claim" and item != _PROFIT_CLAIM:
            return True
    for item in _walk(value):
        if type(item) is str and item.startswith("profit_claim="):
            if item != "profit_claim=none":
                return True
    return False


def _walk(value: object) -> tuple[object, ...]:
    items: list[object] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.append(key)
            items.extend(_walk(item))
    elif type(value) in (list, tuple):
        for item in value:
            items.extend(_walk(item))
    else:
        items.append(value)
    return tuple(items)


def _walk_mapping_items(value: object) -> tuple[tuple[str, object], ...]:
    items: list[tuple[str, object]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is str:
                items.append((key, item))
            items.extend(_walk_mapping_items(item))
    elif type(value) in (list, tuple):
        for item in value:
            items.extend(_walk_mapping_items(item))
    return tuple(items)
