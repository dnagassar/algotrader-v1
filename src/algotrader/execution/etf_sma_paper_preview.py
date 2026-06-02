"""M368 SPY ETF/SMA paper broker-facing preview-only artifact."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_M368_PAPER_PREVIEW_LABELS",
    "EtfSmaM368PaperPreview",
    "EtfSmaM368PaperPreviewConfig",
    "EtfSmaM368PaperPreviewWriteConfig",
    "EtfSmaM368PaperPreviewWriteResult",
    "EtfSmaM368PaperSnapshotSummary",
    "build_etf_sma_m368_paper_preview",
    "load_m368a_review_artifact_record",
    "m368a_reset_summary_as_snapshot",
    "render_etf_sma_m368_paper_preview_json",
    "render_etf_sma_m368_paper_preview_text",
    "write_etf_sma_m368_paper_preview",
]


ETF_SMA_M368_PAPER_PREVIEW_LABELS = (
    "paper_lab_only",
    "preview_only",
    "not_live_authorized",
    "profit_claim=none",
)
_M368A_REQUIRED_LABELS = (
    "paper_lab_only",
    "offline_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
)

_PREVIEW_VERSION = "etf_sma_m368_paper_broker_preview_v1"
_RECORD_TYPE = "etf_sma_m368_paper_broker_preview"
_COMMAND = "etf-sma-m368-broker-preview-only"
_BUILDER = "build_etf_sma_m368_paper_preview"
_DEFAULT_RUN_ID = "m368_spy_etf_sma_broker_preview_only"
_DEFAULT_SOURCE_PATH = (
    "runs/paper_lab/m368a_offline_spy_etf_sma_next_experiment_review.jsonl"
)
_M368A_ARTIFACT_VERSION = "etf_sma_next_experiment_review_artifact_v1"
_M368A_RECORD_TYPE = "etf_sma_next_experiment_review_artifact_record"
_M368A_RUN_ID = "m368a_offline_spy_etf_sma_next_experiment_review"
_M368A_READY_DECISION = "ready_for_separate_broker_preview_milestone"
_M368A_REQUIRED_NEXT_MILESTONE = (
    "M368 - SPY ETF/SMA broker-facing preview-only milestone"
)
_READY_DECISION = "ready_for_operator_review_before_tiny_spy_paper_submit"
_BLOCKED_DECISION = "blocked_before_operator_review_for_tiny_spy_paper_submit"
_READY_REASON = (
    "M368A is ready, the paper snapshot is flat/clean, and only a local "
    "preview payload was rendered; M369 operator approval is required before "
    "any submit."
)
_REQUIRED_NEXT_MILESTONE = "M369 - Explicit operator review for tiny SPY paper submit"
_SYMBOL = "SPY"
_ASSET_CLASS = "equity"
_SIDE = "buy"
_ORDER_TYPE = "market"
_TIME_IN_FORCE = "day"
_MAX_NOTIONAL_CAP = Decimal("25.00")
_PROFIT_CLAIM = "none"


@dataclass(frozen=True, slots=True)
class EtfSmaM368PaperSnapshotSummary:
    """Explicit flat/clean paper snapshot evidence for the M368 preview."""

    snapshot_source: str = "fresh_read_only_paper_snapshot"
    snapshot_evidence_id: str = "m368_fresh_read_only_paper_snapshot"
    fresh_snapshot_status: str = "paper_lab_flat_clean"
    account_observation_available: bool = True
    positions_observation_available: bool = True
    orders_observation_available: bool = True
    cash: Decimal | str | None = None
    currency: str | None = None
    position_count: int = 0
    position_symbols: tuple[str, ...] = ()
    open_order_count: int = 0
    recent_order_query_metadata_complete: bool = True
    unavailable_observations: tuple[str, ...] = ()
    submitted: bool = False
    mutated: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_source",
            _required_string(self.snapshot_source, "snapshot_source"),
        )
        object.__setattr__(
            self,
            "snapshot_evidence_id",
            _required_string(self.snapshot_evidence_id, "snapshot_evidence_id"),
        )
        object.__setattr__(
            self,
            "fresh_snapshot_status",
            _required_string(self.fresh_snapshot_status, "fresh_snapshot_status"),
        )
        for field_name in (
            "account_observation_available",
            "positions_observation_available",
            "orders_observation_available",
            "recent_order_query_metadata_complete",
            "submitted",
            "mutated",
        ):
            object.__setattr__(self, field_name, _bool(getattr(self, field_name), field_name))
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
            "open_order_count",
            _non_negative_int(self.open_order_count, "open_order_count"),
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
        """Return snapshot blockers that prevent rendering a ready preview."""

        blockers: list[str] = []
        if not self.account_observation_available:
            blockers.append("account_observation_unavailable")
        if not self.positions_observation_available:
            blockers.append("positions_observation_unavailable")
        if not self.orders_observation_available:
            blockers.append("orders_observation_unavailable")
        if self.position_count != 0:
            blockers.append("positions_present")
        if self.position_symbols:
            blockers.append("position_symbols_present")
        if any(symbol != _SYMBOL for symbol in self.position_symbols):
            blockers.append("non_spy_position_present")
        if self.open_order_count != 0:
            blockers.append("open_orders_present")
        if not self.recent_order_query_metadata_complete:
            blockers.append("recent_order_metadata_incomplete")
        if self.unavailable_observations:
            blockers.append("unavailable_observations_present")
        if self.submitted:
            blockers.append("snapshot_submitted_not_false")
        if self.mutated:
            blockers.append("snapshot_mutated_not_false")

        return tuple(blockers)

    def to_dict(self) -> dict[str, object]:
        """Return primitive snapshot evidence for the preview artifact."""

        return {
            "snapshot_source": self.snapshot_source,
            "snapshot_evidence_id": self.snapshot_evidence_id,
            "fresh_snapshot_status": self.fresh_snapshot_status,
            "account_observation_available": self.account_observation_available,
            "positions_observation_available": self.positions_observation_available,
            "orders_observation_available": self.orders_observation_available,
            "cash": _decimal_text(self.cash),
            "currency": self.currency,
            "position_count": self.position_count,
            "position_symbols": list(self.position_symbols),
            "open_order_count": self.open_order_count,
            "recent_order_query_metadata_complete": (
                self.recent_order_query_metadata_complete
            ),
            "unavailable_observations": list(self.unavailable_observations),
            "submitted": self.submitted,
            "mutated": self.mutated,
            "blockers": list(self.blockers()),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaM368PaperPreviewConfig:
    """Static M368 preview-only constraints."""

    run_id: str = _DEFAULT_RUN_ID
    source_m368a_artifact_path: Path | str = _DEFAULT_SOURCE_PATH
    notional_cap: Decimal = _MAX_NOTIONAL_CAP
    allowlist: tuple[str, ...] = (_SYMBOL,)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_m368a_artifact_path",
            _output_path(self.source_m368a_artifact_path),
        )
        object.__setattr__(
            self,
            "notional_cap",
            _positive_capped_decimal(self.notional_cap, "notional_cap"),
        )
        object.__setattr__(self, "allowlist", _allowlist(self.allowlist))


@dataclass(frozen=True, slots=True)
class EtfSmaM368PaperPreview:
    """Immutable M368 preview-only JSONL record."""

    preview_version: str
    record_type: str
    command: str
    builder_name: str
    run_id: str
    source_m368a_artifact_path: str
    source_m368a_run_id: str
    source_m368a_evidence_ids: tuple[str, ...]
    source_m368a_signal_evidence_id: str
    source_m368a_decision: str
    source_m368a_required_next_milestone: str
    source_m368a_submit_authorized: bool | None
    source_m368a_submitted: bool | None
    source_m368a_mutated: bool | None
    offline_signal_status: str | None
    offline_signal_actionable_risk_on: bool | None
    account_observation_available: bool
    positions_observation_available: bool
    orders_observation_available: bool
    cash: Decimal | None
    currency: str | None
    position_count: int
    position_symbols: tuple[str, ...]
    open_order_count: int
    symbol: str
    asset_class: str
    side: str | None
    order_type: str | None
    time_in_force: str | None
    notional_cap: Decimal
    notional: Decimal | None
    allowlist: tuple[str, ...]
    labels: tuple[str, ...]
    preview_order: dict[str, object] | None
    decision: str
    reason: str
    blockers: tuple[str, ...]
    required_next_milestone: str
    preview_only: bool
    paper_only: bool
    not_live_authorized: bool
    profit_claim: str
    submit_authorized: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    local_payload_preview_performed: bool
    fresh_paper_snapshot_summary: EtfSmaM368PaperSnapshotSummary

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "preview_version",
            _fixed_string(self.preview_version, _PREVIEW_VERSION, "preview_version"),
        )
        object.__setattr__(
            self,
            "record_type",
            _fixed_string(self.record_type, _RECORD_TYPE, "record_type"),
        )
        object.__setattr__(self, "command", _fixed_string(self.command, _COMMAND, "command"))
        object.__setattr__(
            self,
            "builder_name",
            _fixed_string(self.builder_name, _BUILDER, "builder_name"),
        )
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_m368a_artifact_path",
            _required_string(
                self.source_m368a_artifact_path,
                "source_m368a_artifact_path",
            ),
        )
        object.__setattr__(
            self,
            "source_m368a_run_id",
            _required_string(self.source_m368a_run_id, "source_m368a_run_id"),
        )
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
            "source_m368a_signal_evidence_id",
            _optional_string(
                self.source_m368a_signal_evidence_id,
                "source_m368a_signal_evidence_id",
            )
            or "",
        )
        object.__setattr__(
            self,
            "source_m368a_decision",
            _string(self.source_m368a_decision, "source_m368a_decision"),
        )
        object.__setattr__(
            self,
            "source_m368a_required_next_milestone",
            _string(
                self.source_m368a_required_next_milestone,
                "source_m368a_required_next_milestone",
            ),
        )
        for field_name in (
            "source_m368a_submit_authorized",
            "source_m368a_submitted",
            "source_m368a_mutated",
            "offline_signal_actionable_risk_on",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_bool(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "offline_signal_status",
            _optional_string(self.offline_signal_status, "offline_signal_status"),
        )
        for field_name in (
            "account_observation_available",
            "positions_observation_available",
            "orders_observation_available",
            "preview_only",
            "paper_only",
            "not_live_authorized",
            "local_payload_preview_performed",
        ):
            object.__setattr__(self, field_name, _bool(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "cash",
            _optional_decimal(self.cash, "cash"),
        )
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
            "open_order_count",
            _non_negative_int(self.open_order_count, "open_order_count"),
        )
        object.__setattr__(self, "symbol", _fixed_string(self.symbol, _SYMBOL, "symbol"))
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(
            self,
            "side",
            _optional_fixed_string(self.side, _SIDE, "side"),
        )
        object.__setattr__(
            self,
            "order_type",
            _optional_fixed_string(self.order_type, _ORDER_TYPE, "order_type"),
        )
        object.__setattr__(
            self,
            "time_in_force",
            _optional_fixed_string(
                self.time_in_force,
                _TIME_IN_FORCE,
                "time_in_force",
            ),
        )
        object.__setattr__(
            self,
            "notional_cap",
            _positive_capped_decimal(self.notional_cap, "notional_cap"),
        )
        object.__setattr__(
            self,
            "notional",
            _optional_positive_capped_decimal(self.notional, "notional"),
        )
        object.__setattr__(self, "allowlist", _allowlist(self.allowlist))
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                ETF_SMA_M368_PAPER_PREVIEW_LABELS,
                "labels",
            ),
        )
        object.__setattr__(
            self,
            "preview_order",
            _optional_preview_order(self.preview_order),
        )
        object.__setattr__(self, "decision", _decision(self.decision))
        object.__setattr__(self, "reason", _required_string(self.reason, "reason"))
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
                _REQUIRED_NEXT_MILESTONE,
                "required_next_milestone",
            ),
        )
        object.__setattr__(self, "profit_claim", _fixed_string(self.profit_claim, _PROFIT_CLAIM, "profit_claim"))
        for field_name in (
            "submit_authorized",
            "submitted",
            "mutated",
            "broker_action_performed",
            "broker_preview_performed",
        ):
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "fresh_paper_snapshot_summary",
            _snapshot(self.fresh_paper_snapshot_summary),
        )
        _validate_preview_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only preview payload."""

        return {
            "preview_version": self.preview_version,
            "record_type": self.record_type,
            "command": self.command,
            "builder_name": self.builder_name,
            "run_id": self.run_id,
            "source_m368a_artifact_path": self.source_m368a_artifact_path,
            "source_m368a_run_id": self.source_m368a_run_id,
            "source_m368a_evidence_ids": list(self.source_m368a_evidence_ids),
            "source_m368a_signal_evidence_id": self.source_m368a_signal_evidence_id,
            "source_m368a_decision": self.source_m368a_decision,
            "source_m368a_required_next_milestone": (
                self.source_m368a_required_next_milestone
            ),
            "source_m368a_submit_authorized": self.source_m368a_submit_authorized,
            "source_m368a_submitted": self.source_m368a_submitted,
            "source_m368a_mutated": self.source_m368a_mutated,
            "offline_signal_status": self.offline_signal_status,
            "offline_signal_actionable_risk_on": (
                self.offline_signal_actionable_risk_on
            ),
            "fresh_paper_snapshot_summary": (
                self.fresh_paper_snapshot_summary.to_dict()
            ),
            "account_observation_available": self.account_observation_available,
            "positions_observation_available": self.positions_observation_available,
            "orders_observation_available": self.orders_observation_available,
            "cash": _decimal_text(self.cash),
            "currency": self.currency,
            "position_count": self.position_count,
            "position_symbols": list(self.position_symbols),
            "open_order_count": self.open_order_count,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "notional_cap": str(self.notional_cap),
            "notional": _decimal_text(self.notional),
            "allowlist": list(self.allowlist),
            "labels": list(self.labels),
            "preview_order": _json_safe(self.preview_order),
            "decision": self.decision,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "required_next_milestone": self.required_next_milestone,
            "preview_only": self.preview_only,
            "paper_only": self.paper_only,
            "not_live_authorized": self.not_live_authorized,
            "profit_claim": self.profit_claim,
            "submit_authorized": self.submit_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "local_payload_preview_performed": self.local_payload_preview_performed,
        }


@dataclass(frozen=True, slots=True)
class EtfSmaM368PaperPreviewWriteConfig:
    """Explicit local JSONL write configuration for M368."""

    output_path: Path | str
    append: bool = False
    create_parent_dirs: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        object.__setattr__(self, "append", _bool(self.append, "append"))
        object.__setattr__(
            self,
            "create_parent_dirs",
            _bool(self.create_parent_dirs, "create_parent_dirs"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaM368PaperPreviewWriteResult:
    """Result metadata for one local M368 JSONL write."""

    output_path: Path
    record_count: int
    bytes_written: int
    append: bool
    created_parent_dirs: bool
    newline_terminated: bool
    submit_authorized: bool
    submitted: bool
    mutated: bool
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
        for field_name in (
            "submit_authorized",
            "submitted",
            "mutated",
            "broker_action_performed",
            "broker_preview_performed",
        ):
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
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
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
        }


def load_m368a_review_artifact_record(
    path: str | Path,
    *,
    run_id: str | None = _M368A_RUN_ID,
) -> dict[str, object]:
    """Read exactly one local M368A JSONL record from a caller-specified path."""

    artifact_path = _output_path(path)
    if not artifact_path.exists() or not artifact_path.is_file():
        raise ValidationError("M368A review artifact must be an existing file.")

    records: list[dict[str, object]] = []
    try:
        lines = artifact_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(
            f"M368A review artifact could not be read: {exc.__class__.__name__}."
        ) from None

    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError("M368A review artifact contains invalid JSON.") from exc
        if not isinstance(payload, Mapping):
            raise ValidationError("M368A review artifact records must be JSON objects.")
        records.append(dict(payload))

    selected_run_id = _optional_string(run_id, "run_id")
    selected = [
        record
        for record in records
        if selected_run_id is None or record.get("run_id") == selected_run_id
    ]
    if len(selected) != 1:
        raise ValidationError("expected exactly one M368A review artifact record.")

    return selected[0]


def m368a_reset_summary_as_snapshot(
    m368a_record: Mapping[str, object],
) -> EtfSmaM368PaperSnapshotSummary:
    """Adapt the embedded M368A reset summary into explicit snapshot evidence."""

    record = _mapping(m368a_record, "m368a_record")
    reset = _mapping(record.get("reset_evidence_summary"), "reset_evidence_summary")
    no_open_orders = reset.get("no_open_orders") is True
    return EtfSmaM368PaperSnapshotSummary(
        snapshot_source="m368a_reset_evidence_summary",
        snapshot_evidence_id=_text(reset.get("evidence_id")) or "m368a_reset_summary",
        fresh_snapshot_status=_text(reset.get("classification")) or "unknown",
        account_observation_available=reset.get("account_observed") is True,
        positions_observation_available=reset.get("positions_observed") is True,
        orders_observation_available=reset.get("open_orders_observed") is True,
        cash=_decimal_from_payload(reset.get("cash")),
        currency=_optional_text(reset.get("currency")),
        position_count=_int_payload(reset.get("position_count")),
        position_symbols=_tuple_payload(reset.get("position_symbols")),
        open_order_count=0 if no_open_orders else _int_payload(reset.get("recent_order_count")),
        recent_order_query_metadata_complete=True,
        unavailable_observations=(),
        submitted=reset.get("submitted") is True,
        mutated=reset.get("mutated") is True,
    )


def build_etf_sma_m368_paper_preview(
    m368a_record: Mapping[str, object],
    fresh_snapshot: EtfSmaM368PaperSnapshotSummary,
    config: EtfSmaM368PaperPreviewConfig | None = None,
) -> EtfSmaM368PaperPreview:
    """Build a local M368 broker-facing preview record without broker calls."""

    record = _mapping(m368a_record, "m368a_record")
    checked_snapshot = _snapshot(fresh_snapshot)
    checked_config = config or EtfSmaM368PaperPreviewConfig()
    if type(checked_config) is not EtfSmaM368PaperPreviewConfig:
        raise ValidationError("config must be an EtfSmaM368PaperPreviewConfig.")

    source_blockers = _m368a_source_blockers(record, checked_config)
    snapshot_blockers = checked_snapshot.blockers()
    blockers = _dedupe((*source_blockers, *snapshot_blockers))
    ready = not blockers
    preview_order = _preview_order(checked_config) if ready else None
    return EtfSmaM368PaperPreview(
        preview_version=_PREVIEW_VERSION,
        record_type=_RECORD_TYPE,
        command=_COMMAND,
        builder_name=_BUILDER,
        run_id=checked_config.run_id,
        source_m368a_artifact_path=str(checked_config.source_m368a_artifact_path),
        source_m368a_run_id=_text(record.get("run_id")) or "missing",
        source_m368a_evidence_ids=_tuple_payload(record.get("evidence_ids")),
        source_m368a_signal_evidence_id=_text(record.get("signal_evidence_id")),
        source_m368a_decision=_text(record.get("decision")),
        source_m368a_required_next_milestone=_text(
            record.get("required_next_milestone")
        ),
        source_m368a_submit_authorized=_optional_bool(
            record.get("submit_authorized"),
            "source_m368a_submit_authorized",
        ),
        source_m368a_submitted=_optional_bool(
            record.get("submitted"),
            "source_m368a_submitted",
        ),
        source_m368a_mutated=_optional_bool(
            record.get("mutated"),
            "source_m368a_mutated",
        ),
        offline_signal_status=_optional_text(record.get("offline_signal_status")),
        offline_signal_actionable_risk_on=_optional_bool(
            record.get("offline_signal_actionable_risk_on"),
            "offline_signal_actionable_risk_on",
        ),
        account_observation_available=checked_snapshot.account_observation_available,
        positions_observation_available=checked_snapshot.positions_observation_available,
        orders_observation_available=checked_snapshot.orders_observation_available,
        cash=checked_snapshot.cash,
        currency=checked_snapshot.currency,
        position_count=checked_snapshot.position_count,
        position_symbols=checked_snapshot.position_symbols,
        open_order_count=checked_snapshot.open_order_count,
        symbol=_SYMBOL,
        asset_class=_ASSET_CLASS,
        side=_SIDE if ready else None,
        order_type=_ORDER_TYPE if ready else None,
        time_in_force=_TIME_IN_FORCE if ready else None,
        notional_cap=checked_config.notional_cap,
        notional=checked_config.notional_cap if ready else None,
        allowlist=checked_config.allowlist,
        labels=ETF_SMA_M368_PAPER_PREVIEW_LABELS,
        preview_order=preview_order,
        decision=_READY_DECISION if ready else _BLOCKED_DECISION,
        reason=_READY_REASON if ready else _blocked_reason(blockers),
        blockers=blockers,
        required_next_milestone=_REQUIRED_NEXT_MILESTONE,
        preview_only=True,
        paper_only=True,
        not_live_authorized=True,
        profit_claim=_PROFIT_CLAIM,
        submit_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_preview_performed=False,
        local_payload_preview_performed=ready,
        fresh_paper_snapshot_summary=checked_snapshot,
    )


def render_etf_sma_m368_paper_preview_json(
    preview: EtfSmaM368PaperPreview,
) -> str:
    """Render one newline-free deterministic JSON object."""

    checked_preview = _preview(preview)
    return json.dumps(
        checked_preview.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )


def render_etf_sma_m368_paper_preview_text(
    preview: EtfSmaM368PaperPreview,
) -> str:
    """Render a compact operator-readable preview summary."""

    checked_preview = _preview(preview)
    lines = [
        "M368 SPY ETF/SMA paper broker-facing preview",
        f"run_id: {checked_preview.run_id}",
        f"source_m368a_artifact_path: {checked_preview.source_m368a_artifact_path}",
        f"source_m368a_decision: {checked_preview.source_m368a_decision}",
        f"decision: {checked_preview.decision}",
        f"reason: {checked_preview.reason}",
        f"blockers: {_joined(checked_preview.blockers)}",
        f"symbol: {checked_preview.symbol}",
        f"asset_class: {checked_preview.asset_class}",
        f"side: {checked_preview.side or 'none'}",
        f"order_type: {checked_preview.order_type or 'none'}",
        f"time_in_force: {checked_preview.time_in_force or 'none'}",
        f"notional_cap: {checked_preview.notional_cap}",
        f"notional: {_decimal_text(checked_preview.notional) or 'none'}",
        f"position_count: {checked_preview.position_count}",
        f"position_symbols: {_joined(checked_preview.position_symbols)}",
        f"open_order_count: {checked_preview.open_order_count}",
        f"submit_authorized: {_bool_text(checked_preview.submit_authorized)}",
        f"submitted: {_bool_text(checked_preview.submitted)}",
        f"mutated: {_bool_text(checked_preview.mutated)}",
        "broker_action_performed: "
        f"{_bool_text(checked_preview.broker_action_performed)}",
        "broker_preview_performed: "
        f"{_bool_text(checked_preview.broker_preview_performed)}",
        f"required_next_milestone: {checked_preview.required_next_milestone}",
    ]
    return "\n".join(lines)


def write_etf_sma_m368_paper_preview(
    preview: EtfSmaM368PaperPreview,
    config: EtfSmaM368PaperPreviewWriteConfig,
) -> EtfSmaM368PaperPreviewWriteResult:
    """Write one deterministic M368 preview record to a local JSONL file."""

    checked_preview = _preview(preview)
    checked_config = _write_config(config)
    line = render_etf_sma_m368_paper_preview_json(checked_preview) + "\n"
    created_parent_dirs = _prepare_output_parent(checked_config.output_path, checked_config)
    _write_line(checked_config.output_path, line, append=checked_config.append)
    return EtfSmaM368PaperPreviewWriteResult(
        output_path=checked_config.output_path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        append=checked_config.append,
        created_parent_dirs=created_parent_dirs,
        newline_terminated=line.endswith("\n"),
        submit_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_preview_performed=False,
    )


def _m368a_source_blockers(
    record: Mapping[str, object],
    config: EtfSmaM368PaperPreviewConfig,
) -> tuple[str, ...]:
    blockers: list[str] = []
    _append_if(
        blockers,
        record.get("artifact_version") != _M368A_ARTIFACT_VERSION,
        "m368a_artifact_version_unexpected",
    )
    _append_if(
        blockers,
        record.get("record_type") != _M368A_RECORD_TYPE,
        "m368a_record_type_unexpected",
    )
    _append_if(
        blockers,
        record.get("run_id") != _M368A_RUN_ID,
        "m368a_run_id_unexpected",
    )
    _append_if(
        blockers,
        record.get("decision") != _M368A_READY_DECISION,
        "m368a_decision_not_ready",
    )
    _append_if(
        blockers,
        record.get("required_next_milestone") != _M368A_REQUIRED_NEXT_MILESTONE,
        "m368a_required_next_milestone_unexpected",
    )
    _append_if(
        blockers,
        record.get("separate_preview_milestone_required") is not True,
        "m368a_separate_preview_required_not_true",
    )
    _append_if(
        blockers,
        record.get("separate_broker_preview_milestone_allowed") is not True,
        "m368a_broker_preview_allowed_not_true",
    )
    _append_if(
        blockers,
        record.get("submit_authorized") is not False,
        "m368a_submit_authorized_not_false",
    )
    _append_if(
        blockers,
        record.get("submitted") is not False,
        "m368a_submitted_not_false",
    )
    _append_if(
        blockers,
        record.get("mutated") is not False,
        "m368a_mutated_not_false",
    )
    _append_if(
        blockers,
        record.get("broker_action_performed") is not False,
        "m368a_broker_action_performed_not_false",
    )
    _append_if(
        blockers,
        record.get("broker_preview_performed") is not False,
        "m368a_broker_preview_performed_not_false",
    )
    _append_if(
        blockers,
        _tuple_payload(record.get("blockers")) != (),
        "m368a_blockers_present",
    )
    _append_if(blockers, record.get("symbol") != _SYMBOL, "m368a_symbol_not_spy")
    _append_if(
        blockers,
        record.get("asset_class") != _ASSET_CLASS,
        "m368a_asset_class_not_equity",
    )
    cap = _decimal_from_payload(record.get("cap"))
    if cap is None:
        blockers.append("m368a_cap_missing_or_invalid")
    elif cap > config.notional_cap:
        blockers.append("m368a_cap_above_m368_cap")
    labels = _tuple_payload(record.get("labels"))
    for label in _M368A_REQUIRED_LABELS:
        if label not in labels:
            blockers.append(f"m368a_label_missing_{label}")

    offline_signal = _mapping(
        record.get("offline_signal_evidence_summary"),
        "offline_signal_evidence_summary",
    )
    _append_if(
        blockers,
        offline_signal.get("symbol") != _SYMBOL,
        "m368a_signal_symbol_not_spy",
    )
    _append_if(
        blockers,
        offline_signal.get("asset_class") != _ASSET_CLASS,
        "m368a_signal_asset_class_not_equity",
    )
    _append_if(
        blockers,
        record.get("offline_signal_status") != "bullish_risk_on",
        "m368a_signal_status_not_bullish",
    )
    _append_if(
        blockers,
        record.get("offline_signal_actionable_risk_on") is not True,
        "m368a_signal_not_actionable",
    )

    return tuple(blockers)


def _preview_order(config: EtfSmaM368PaperPreviewConfig) -> dict[str, object]:
    return {
        "asset_class": _ASSET_CLASS,
        "notional": str(config.notional_cap),
        "order_type": _ORDER_TYPE,
        "side": _SIDE,
        "symbol": _SYMBOL,
        "time_in_force": _TIME_IN_FORCE,
    }


def _blocked_reason(blockers: tuple[str, ...]) -> str:
    first = blockers[0] if blockers else "unknown_blocker"
    return (
        f"blocked_before_preview_only_payload: {first}; M369 operator approval "
        "would still be required before any submit."
    )


def _validate_preview_consistency(preview: EtfSmaM368PaperPreview) -> None:
    ready = preview.decision == _READY_DECISION
    if ready and preview.blockers:
        raise ValidationError("ready M368 preview must not contain blockers.")
    if not ready and not preview.blockers:
        raise ValidationError("blocked M368 preview must contain blockers.")
    if ready:
        if preview.preview_order is None:
            raise ValidationError("ready M368 preview requires preview_order.")
        if preview.notional != preview.notional_cap:
            raise ValidationError("ready M368 preview notional must equal cap.")
        if not preview.local_payload_preview_performed:
            raise ValidationError("ready M368 preview must render local payload.")
        if preview.side != _SIDE or preview.order_type != _ORDER_TYPE:
            raise ValidationError("ready M368 preview order shape is invalid.")
        if preview.time_in_force != _TIME_IN_FORCE:
            raise ValidationError("ready M368 preview time_in_force is invalid.")
    else:
        if preview.preview_order is not None or preview.notional is not None:
            raise ValidationError("blocked M368 preview must not carry order sizing.")
        if preview.local_payload_preview_performed:
            raise ValidationError("blocked M368 preview must not render local payload.")


def _optional_preview_order(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if type(value) is not dict:
        raise ValidationError("preview_order must be a dict or None.")
    expected = {
        "asset_class": _ASSET_CLASS,
        "order_type": _ORDER_TYPE,
        "side": _SIDE,
        "symbol": _SYMBOL,
        "time_in_force": _TIME_IN_FORCE,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValidationError(f"preview_order {key} is invalid.")
    notional = _decimal_from_payload(value.get("notional"))
    if notional is None:
        raise ValidationError("preview_order notional is invalid.")
    _positive_capped_decimal(notional, "preview_order.notional")
    return dict(value)


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        if field_name == "m368a_record":
            raise ValidationError("m368a_record must be a mapping.")
        return {}
    return value


def _snapshot(value: object) -> EtfSmaM368PaperSnapshotSummary:
    if type(value) is not EtfSmaM368PaperSnapshotSummary:
        raise ValidationError(
            "fresh_snapshot must be an EtfSmaM368PaperSnapshotSummary."
        )
    return value


def _preview(value: object) -> EtfSmaM368PaperPreview:
    if type(value) is not EtfSmaM368PaperPreview:
        raise ValidationError("preview must be an EtfSmaM368PaperPreview.")
    return value


def _write_config(value: object) -> EtfSmaM368PaperPreviewWriteConfig:
    if type(value) is not EtfSmaM368PaperPreviewWriteConfig:
        raise ValidationError("config must be an EtfSmaM368PaperPreviewWriteConfig.")
    return value


def _prepare_output_parent(
    path: Path,
    config: EtfSmaM368PaperPreviewWriteConfig,
) -> bool:
    parent = path.parent
    if str(parent) in ("", ".") or parent.exists():
        return False
    if not config.create_parent_dirs:
        raise ValidationError("output parent directory does not exist.")
    parent.mkdir(parents=True, exist_ok=True)
    return True


def _write_line(path: Path, line: str, *, append: bool) -> None:
    mode = "a" if append else "x"
    try:
        with path.open(mode, encoding="utf-8", newline="\n") as stream:
            stream.write(line)
    except FileExistsError:
        raise ValidationError("output path exists; pass append=True to append.") from None
    except OSError as exc:
        raise ValidationError(
            f"M368 paper preview write failed: {exc.__class__.__name__}."
        ) from None


def _output_path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("path must be a Path or string.")
    if str(path).strip() == "":
        raise ValidationError("path must not be empty.")
    if path.exists() and path.is_dir():
        raise ValidationError("path must not be a directory.")
    return path


def _allowlist(values: object) -> tuple[str, ...]:
    symbols = _symbol_tuple(values, "allowlist", allow_empty=False)
    if symbols != (_SYMBOL,):
        raise ValidationError("allowlist must be exactly SPY.")
    return symbols


def _symbol_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name, allow_empty=allow_empty)
    return tuple(_symbol(item) for item in items)


def _symbol(value: object) -> str:
    text = _required_string(value, "symbol").upper()
    if any(character.isspace() for character in text):
        raise ValidationError("symbol must not contain whitespace.")
    return text


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    items = tuple(values)
    if not items and not allow_empty:
        raise ValidationError(f"{field_name} must not be empty.")
    return tuple(_required_string(item, field_name) for item in items)


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name, allow_empty=False)
    if items != expected:
        raise ValidationError(f"{field_name} must match the required values.")
    return items


def _tuple_payload(value: object) -> tuple[str, ...]:
    if type(value) not in (list, tuple):
        return ()
    return tuple(str(item) for item in value if str(item))


def _decision(value: object) -> str:
    if type(value) is not str or value not in (_READY_DECISION, _BLOCKED_DECISION):
        raise ValidationError("decision is invalid.")
    return value


def _optional_fixed_string(
    value: object,
    expected: str,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return _fixed_string(value, expected, field_name)


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    if type(value) is not str or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return value


def _required_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if text != text.strip() or not text:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return text


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _optional_text(value: object) -> str | None:
    text = _text(value)
    return text or None


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    return value


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    return value


def _optional_bool(value: object, field_name: str) -> bool | None:
    if value is None:
        return None
    return _bool(value, field_name)


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return value


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _fixed_int(value: object, expected: int, field_name: str) -> int:
    checked = _non_negative_int(value, field_name)
    if checked != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return checked


def _int_payload(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return 0
    return parsed if parsed >= 0 else 0


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, str):
        decimal_value = _decimal_from_payload(value)
        if decimal_value is None:
            raise ValidationError(f"{field_name} must be a Decimal.")
    else:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not decimal_value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return decimal_value


def _positive_capped_decimal(value: object, field_name: str) -> Decimal:
    checked = _optional_decimal(value, field_name)
    if checked is None or checked <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    if checked > _MAX_NOTIONAL_CAP:
        raise ValidationError(f"{field_name} must be <= 25.00.")
    return checked


def _optional_positive_capped_decimal(
    value: object,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None
    return _positive_capped_decimal(value, field_name)


def _decimal_from_payload(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _append_if(blockers: list[str], condition: bool, blocker: str) -> None:
    if condition:
        blockers.append(blocker)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
