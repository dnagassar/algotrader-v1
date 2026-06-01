"""ETF/SMA paper broker-facing local preview with no broker mutation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.orchestration.etf_sma_preview_jsonl_artifact import (
    ETF_SMA_PREVIEW_JSONL_ARTIFACT_LABELS,
    EtfSmaPreviewJsonlRecord,
)

__all__ = [
    "ETF_SMA_PAPER_BROKER_PREVIEW_LABELS",
    "EtfSmaPaperBrokerPreview",
    "EtfSmaPaperBrokerPreviewConfig",
    "EtfSmaPaperBrokerPreviewWriteConfig",
    "EtfSmaPaperBrokerPreviewWriteResult",
    "EtfSmaPaperSnapshotEvidence",
    "build_etf_sma_paper_broker_preview",
    "render_etf_sma_paper_broker_preview_json",
    "render_etf_sma_paper_broker_preview_text",
    "write_etf_sma_paper_broker_preview",
]

ETF_SMA_PAPER_BROKER_PREVIEW_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "broker_facing_preview_only",
    "not_live_authorized",
    "profit_claim=none",
)

_PREVIEW_VERSION = "etf_sma_paper_broker_preview_v1"
_RECORD_TYPE = "etf_sma_paper_broker_preview"
_DEFAULT_RUN_ID = "m349_etf_sma_paper_preview_only"
_DEFAULT_SOURCE_RECORD_ID = "m347_etf_sma_preview_jsonl_record:synthetic_bullish_spy"
_PRIOR_SNAPSHOT_RUN_ID = "m348_etf_sma_fresh_read_only_snapshot"
_USABLE_REVALIDATION_STATE = "usable_for_manual_review"
_SNAPSHOT_STATUS = "read_only_snapshot_completed_for_manual_review"
_NEXT_ACTION = "m350_operator_review_before_any_tiny_spy_paper_probe"
_PROFIT_CLAIM = "none"
_SYMBOL = "SPY"
_ASSET_CLASS = "equity"
_SIDE = "buy"
_ORDER_TYPE = "market"
_TIME_IN_FORCE = "day"
_MAX_NOTIONAL_CAP = Decimal("25.00")
_ACCEPTED_PREVIEW_STATUS = "broker_facing_local_payload_previewed"
_SKIPPED_PREVIEW_STATUS = "skipped_from_broker_facing_preview"
_BLOCKED_PREVIEW_STATUS = "blocked_before_broker_facing_preview"
_FORBIDDEN_LIVE_AUTHORIZATION_VALUES = {
    "authorized_for_live_trading",
    "live_authorized",
    "live_authorized=true",
    "live_trading_authorized",
}


@dataclass(frozen=True, slots=True)
class EtfSmaPaperSnapshotEvidence:
    """Small M348 read-only snapshot gate consumed by the M349 preview."""

    prior_snapshot_run_id: str = _PRIOR_SNAPSHOT_RUN_ID
    prior_snapshot_revalidation_state: str = _USABLE_REVALIDATION_STATE
    fresh_snapshot_status: str = _SNAPSHOT_STATUS
    usable_for_manual_review: bool = True
    snapshot_records_observed: bool = True
    account_observation_available: bool = True
    positions_observation_available: bool = True
    orders_observation_available: bool = True
    position_count: int = 0
    position_symbols: tuple[str, ...] = ()
    recent_open_order_count: int = 0
    recent_order_query_metadata_complete: bool = True
    unavailable_observations: tuple[str, ...] = ()
    submitted: bool = False
    mutated: bool = False
    credentials_redacted_present: bool = True
    live_profile_evidence: bool = False
    credential_leak_evidence: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "prior_snapshot_run_id",
            _non_empty_string(self.prior_snapshot_run_id, "prior_snapshot_run_id"),
        )
        object.__setattr__(
            self,
            "prior_snapshot_revalidation_state",
            _non_empty_string(
                self.prior_snapshot_revalidation_state,
                "prior_snapshot_revalidation_state",
            ),
        )
        object.__setattr__(
            self,
            "fresh_snapshot_status",
            _non_empty_string(self.fresh_snapshot_status, "fresh_snapshot_status"),
        )
        for field_name in (
            "usable_for_manual_review",
            "snapshot_records_observed",
            "account_observation_available",
            "positions_observation_available",
            "orders_observation_available",
            "recent_order_query_metadata_complete",
            "credentials_redacted_present",
            "live_profile_evidence",
            "credential_leak_evidence",
        ):
            object.__setattr__(self, field_name, _bool(getattr(self, field_name), field_name))
        object.__setattr__(self, "submitted", _false_bool(self.submitted, "submitted"))
        object.__setattr__(self, "mutated", _false_bool(self.mutated, "mutated"))
        object.__setattr__(
            self,
            "position_count",
            _non_negative_int(self.position_count, "position_count"),
        )
        object.__setattr__(
            self,
            "position_symbols",
            _symbol_tuple(self.position_symbols, allow_empty=True),
        )
        object.__setattr__(
            self,
            "recent_open_order_count",
            _non_negative_int(
                self.recent_open_order_count,
                "recent_open_order_count",
            ),
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

    def to_dict(self) -> dict[str, object]:
        """Return primitive M348 evidence fields."""

        return {
            "prior_snapshot_run_id": self.prior_snapshot_run_id,
            "prior_snapshot_revalidation_state": self.prior_snapshot_revalidation_state,
            "fresh_snapshot_status": self.fresh_snapshot_status,
            "usable_for_manual_review": self.usable_for_manual_review,
            "snapshot_records_observed": self.snapshot_records_observed,
            "account_observation_available": self.account_observation_available,
            "positions_observation_available": self.positions_observation_available,
            "orders_observation_available": self.orders_observation_available,
            "position_count": self.position_count,
            "position_symbols": list(self.position_symbols),
            "recent_open_order_count": self.recent_open_order_count,
            "recent_order_query_metadata_complete": (
                self.recent_order_query_metadata_complete
            ),
            "unavailable_observations": list(self.unavailable_observations),
            "submitted": self.submitted,
            "mutated": self.mutated,
            "credentials_redacted_present": self.credentials_redacted_present,
            "live_profile_evidence": self.live_profile_evidence,
            "credential_leak_evidence": self.credential_leak_evidence,
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPaperBrokerPreviewConfig:
    """Static M349 preview-only constraints."""

    run_id: str = _DEFAULT_RUN_ID
    source_record_id: str = _DEFAULT_SOURCE_RECORD_ID
    max_notional: Decimal = _MAX_NOTIONAL_CAP
    order_type: str = _ORDER_TYPE
    time_in_force: str = _TIME_IN_FORCE
    allowlist: tuple[str, ...] = (_SYMBOL,)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _non_empty_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_record_id",
            _non_empty_string(self.source_record_id, "source_record_id"),
        )
        object.__setattr__(
            self,
            "max_notional",
            _positive_capped_notional(self.max_notional, "max_notional"),
        )
        object.__setattr__(
            self,
            "order_type",
            _fixed_string(self.order_type, _ORDER_TYPE, "order_type"),
        )
        object.__setattr__(
            self,
            "time_in_force",
            _fixed_string(self.time_in_force, _TIME_IN_FORCE, "time_in_force"),
        )
        object.__setattr__(self, "allowlist", _symbol_tuple(self.allowlist))


@dataclass(frozen=True, slots=True)
class EtfSmaPaperBrokerPreview:
    """Immutable broker-facing local payload preview with submit disabled."""

    preview_version: str
    record_type: str
    run_id: str
    source_record: EtfSmaPreviewJsonlRecord
    source_record_id: str
    symbol: str
    asset_class: str
    signal_posture: str
    preview_status: str
    accepted_for_broker_payload_preview: bool
    skipped: bool
    blocked: bool
    skip_reason: str
    block_reason: str
    side: str | None
    order_type: str | None
    time_in_force: str | None
    max_notional: Decimal
    notional: Decimal | None
    quantity: Decimal | None
    broker_payload_preview: dict[str, object] | None
    labels: tuple[str, ...]
    source_record_labels: tuple[str, ...]
    profit_claim: str
    prior_snapshot: EtfSmaPaperSnapshotEvidence
    prior_snapshot_run_id: str
    prior_snapshot_revalidation_state: str
    prior_snapshot_position_count: int
    prior_snapshot_position_symbols: tuple[str, ...]
    prior_snapshot_recent_open_order_count: int
    prior_snapshot_recent_order_query_metadata_complete: bool
    submit_allowed: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    local_payload_preview_performed: bool
    next_action: str

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
        object.__setattr__(self, "run_id", _non_empty_string(self.run_id, "run_id"))
        object.__setattr__(self, "source_record", _source_record(self.source_record))
        object.__setattr__(
            self,
            "source_record_id",
            _non_empty_string(self.source_record_id, "source_record_id"),
        )
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(
            self,
            "signal_posture",
            _non_empty_string(self.signal_posture, "signal_posture"),
        )
        object.__setattr__(self, "preview_status", _preview_status(self.preview_status))
        for field_name in (
            "accepted_for_broker_payload_preview",
            "skipped",
            "blocked",
            "prior_snapshot_recent_order_query_metadata_complete",
            "local_payload_preview_performed",
        ):
            object.__setattr__(self, field_name, _bool(getattr(self, field_name), field_name))
        object.__setattr__(self, "skip_reason", _string(self.skip_reason, "skip_reason"))
        object.__setattr__(self, "block_reason", _string(self.block_reason, "block_reason"))
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
            "max_notional",
            _positive_capped_notional(self.max_notional, "max_notional"),
        )
        object.__setattr__(
            self,
            "notional",
            _optional_positive_capped_notional(self.notional, "notional"),
        )
        object.__setattr__(
            self,
            "quantity",
            _optional_positive_capped_notional(self.quantity, "quantity"),
        )
        object.__setattr__(
            self,
            "broker_payload_preview",
            _optional_broker_payload(self.broker_payload_preview),
        )
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                ETF_SMA_PAPER_BROKER_PREVIEW_LABELS,
                "labels",
            ),
        )
        object.__setattr__(
            self,
            "source_record_labels",
            _fixed_string_tuple(
                self.source_record_labels,
                ETF_SMA_PREVIEW_JSONL_ARTIFACT_LABELS,
                "source_record_labels",
            ),
        )
        object.__setattr__(
            self,
            "profit_claim",
            _fixed_string(self.profit_claim, _PROFIT_CLAIM, "profit_claim"),
        )
        object.__setattr__(self, "prior_snapshot", _snapshot(self.prior_snapshot))
        object.__setattr__(
            self,
            "prior_snapshot_run_id",
            _fixed_string(
                self.prior_snapshot_run_id,
                self.prior_snapshot.prior_snapshot_run_id,
                "prior_snapshot_run_id",
            ),
        )
        object.__setattr__(
            self,
            "prior_snapshot_revalidation_state",
            _fixed_string(
                self.prior_snapshot_revalidation_state,
                self.prior_snapshot.prior_snapshot_revalidation_state,
                "prior_snapshot_revalidation_state",
            ),
        )
        object.__setattr__(
            self,
            "prior_snapshot_position_count",
            _non_negative_int(
                self.prior_snapshot_position_count,
                "prior_snapshot_position_count",
            ),
        )
        object.__setattr__(
            self,
            "prior_snapshot_position_symbols",
            _symbol_tuple(self.prior_snapshot_position_symbols, allow_empty=True),
        )
        object.__setattr__(
            self,
            "prior_snapshot_recent_open_order_count",
            _non_negative_int(
                self.prior_snapshot_recent_open_order_count,
                "prior_snapshot_recent_open_order_count",
            ),
        )
        for field_name in (
            "submit_allowed",
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
            "next_action",
            _fixed_string(self.next_action, _NEXT_ACTION, "next_action"),
        )
        _validate_preview_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only preview payload."""

        return {
            "preview_version": self.preview_version,
            "record_type": self.record_type,
            "run_id": self.run_id,
            "source_record_id": self.source_record_id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "signal_posture": self.signal_posture,
            "preview_status": self.preview_status,
            "accepted_for_broker_payload_preview": (
                self.accepted_for_broker_payload_preview
            ),
            "skipped": self.skipped,
            "blocked": self.blocked,
            "skip_reason": self.skip_reason,
            "block_reason": self.block_reason,
            "side": self.side,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
            "max_notional": str(self.max_notional),
            "notional": _decimal_text(self.notional),
            "quantity": _decimal_text(self.quantity),
            "broker_payload_preview": _json_safe(self.broker_payload_preview),
            "labels": list(self.labels),
            "source_record_labels": list(self.source_record_labels),
            "profit_claim": self.profit_claim,
            "prior_snapshot_run_id": self.prior_snapshot_run_id,
            "prior_snapshot_revalidation_state": (
                self.prior_snapshot_revalidation_state
            ),
            "prior_snapshot_position_count": self.prior_snapshot_position_count,
            "prior_snapshot_position_symbols": list(
                self.prior_snapshot_position_symbols
            ),
            "prior_snapshot_recent_open_order_count": (
                self.prior_snapshot_recent_open_order_count
            ),
            "prior_snapshot_recent_order_query_metadata_complete": (
                self.prior_snapshot_recent_order_query_metadata_complete
            ),
            "submit_allowed": self.submit_allowed,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "local_payload_preview_performed": self.local_payload_preview_performed,
            "next_action": self.next_action,
            "prior_snapshot": self.prior_snapshot.to_dict(),
            "source_record": self.source_record.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPaperBrokerPreviewWriteConfig:
    """Explicit local JSONL write configuration for M349."""

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
class EtfSmaPaperBrokerPreviewWriteResult:
    """Result metadata for one M349 local JSONL write."""

    output_path: Path
    record_count: int
    bytes_written: int
    append: bool
    created_parent_dirs: bool
    newline_terminated: bool
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
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
        }


def build_etf_sma_paper_broker_preview(
    source_record: EtfSmaPreviewJsonlRecord,
    prior_snapshot: EtfSmaPaperSnapshotEvidence,
    config: EtfSmaPaperBrokerPreviewConfig | None = None,
) -> EtfSmaPaperBrokerPreview:
    """Build a broker-facing local payload preview without broker calls."""

    checked_record = _source_record(source_record)
    checked_snapshot = _snapshot(prior_snapshot)
    checked_config = config or EtfSmaPaperBrokerPreviewConfig()
    if type(checked_config) is not EtfSmaPaperBrokerPreviewConfig:
        raise ValidationError("config must be an EtfSmaPaperBrokerPreviewConfig.")

    block_reason = _snapshot_block_reason(checked_snapshot)
    skip_reason = "" if block_reason else _source_skip_reason(checked_record, checked_config)
    accepted = block_reason == "" and skip_reason == ""
    payload = _broker_payload(checked_record, checked_config) if accepted else None
    preview_status = (
        _ACCEPTED_PREVIEW_STATUS
        if accepted
        else _BLOCKED_PREVIEW_STATUS
        if block_reason
        else _SKIPPED_PREVIEW_STATUS
    )

    return EtfSmaPaperBrokerPreview(
        preview_version=_PREVIEW_VERSION,
        record_type=_RECORD_TYPE,
        run_id=checked_config.run_id,
        source_record=checked_record,
        source_record_id=checked_config.source_record_id,
        symbol=checked_record.symbol,
        asset_class=checked_record.asset_class,
        signal_posture=checked_record.signal_posture,
        preview_status=preview_status,
        accepted_for_broker_payload_preview=accepted,
        skipped=skip_reason != "",
        blocked=block_reason != "",
        skip_reason=skip_reason,
        block_reason=block_reason,
        side=_SIDE if accepted else None,
        order_type=checked_config.order_type if accepted else None,
        time_in_force=checked_config.time_in_force if accepted else None,
        max_notional=checked_config.max_notional,
        notional=checked_record.preview_notional if accepted else None,
        quantity=None,
        broker_payload_preview=payload,
        labels=ETF_SMA_PAPER_BROKER_PREVIEW_LABELS,
        source_record_labels=checked_record.labels,
        profit_claim=_PROFIT_CLAIM,
        prior_snapshot=checked_snapshot,
        prior_snapshot_run_id=checked_snapshot.prior_snapshot_run_id,
        prior_snapshot_revalidation_state=(
            checked_snapshot.prior_snapshot_revalidation_state
        ),
        prior_snapshot_position_count=checked_snapshot.position_count,
        prior_snapshot_position_symbols=checked_snapshot.position_symbols,
        prior_snapshot_recent_open_order_count=(
            checked_snapshot.recent_open_order_count
        ),
        prior_snapshot_recent_order_query_metadata_complete=(
            checked_snapshot.recent_order_query_metadata_complete
        ),
        submit_allowed=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_preview_performed=False,
        local_payload_preview_performed=accepted,
        next_action=_NEXT_ACTION,
    )


def render_etf_sma_paper_broker_preview_json(
    preview: EtfSmaPaperBrokerPreview,
) -> str:
    """Render one newline-free deterministic JSON object."""

    checked_preview = _preview(preview)
    return json.dumps(
        checked_preview.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )


def render_etf_sma_paper_broker_preview_text(
    preview: EtfSmaPaperBrokerPreview,
) -> str:
    """Render a compact operator-readable preview summary."""

    checked_preview = _preview(preview)
    lines = [
        "ETF/SMA paper broker-facing preview",
        f"run_id: {checked_preview.run_id}",
        f"preview_status: {checked_preview.preview_status}",
        f"submitted: {_bool_text(checked_preview.submitted)}",
        f"mutated: {_bool_text(checked_preview.mutated)}",
        "broker_action_performed: "
        f"{_bool_text(checked_preview.broker_action_performed)}",
        "broker_preview_performed: "
        f"{_bool_text(checked_preview.broker_preview_performed)}",
        "local_payload_preview_performed: "
        f"{_bool_text(checked_preview.local_payload_preview_performed)}",
        f"symbol: {checked_preview.symbol}",
        f"asset_class: {checked_preview.asset_class}",
        f"signal_posture: {checked_preview.signal_posture}",
        f"side: {checked_preview.side or 'none'}",
        f"notional: {_decimal_text(checked_preview.notional) or 'none'}",
        f"skip_reason: {checked_preview.skip_reason or 'none'}",
        f"block_reason: {checked_preview.block_reason or 'none'}",
        f"prior_snapshot_run_id: {checked_preview.prior_snapshot_run_id}",
        "prior_snapshot_revalidation_state: "
        f"{checked_preview.prior_snapshot_revalidation_state}",
        f"next_action: {checked_preview.next_action}",
    ]
    return "\n".join(lines)


def write_etf_sma_paper_broker_preview(
    preview: EtfSmaPaperBrokerPreview,
    config: EtfSmaPaperBrokerPreviewWriteConfig,
) -> EtfSmaPaperBrokerPreviewWriteResult:
    """Write one deterministic M349 JSONL record to an explicit local path."""

    checked_preview = _preview(preview)
    checked_config = _write_config(config)
    line = render_etf_sma_paper_broker_preview_json(checked_preview) + "\n"
    created_parent_dirs = _prepare_output_parent(checked_config.output_path, checked_config)
    _write_line(checked_config.output_path, line, append=checked_config.append)

    return EtfSmaPaperBrokerPreviewWriteResult(
        output_path=checked_config.output_path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        append=checked_config.append,
        created_parent_dirs=created_parent_dirs,
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_preview_performed=False,
    )


def _snapshot_block_reason(snapshot: EtfSmaPaperSnapshotEvidence) -> str:
    if snapshot.prior_snapshot_run_id != _PRIOR_SNAPSHOT_RUN_ID:
        return "prior_snapshot_run_id_mismatch"
    if (
        snapshot.prior_snapshot_revalidation_state != _USABLE_REVALIDATION_STATE
        or snapshot.fresh_snapshot_status != _SNAPSHOT_STATUS
        or not snapshot.usable_for_manual_review
        or not snapshot.snapshot_records_observed
    ):
        return "prior_snapshot_not_usable"
    if snapshot.submitted or snapshot.mutated:
        return "prior_snapshot_mutated_or_submitted"
    if not (
        snapshot.account_observation_available
        and snapshot.positions_observation_available
        and snapshot.orders_observation_available
    ):
        return "prior_snapshot_observations_unavailable"
    if snapshot.unavailable_observations:
        return "prior_snapshot_unavailable_observations_present"
    if snapshot.position_count != 0 or snapshot.position_symbols:
        return "prior_snapshot_unexpected_positions"
    if snapshot.recent_open_order_count != 0:
        return "prior_snapshot_recent_open_orders_present"
    if not snapshot.recent_order_query_metadata_complete:
        return "prior_snapshot_recent_order_metadata_incomplete"
    if not snapshot.credentials_redacted_present:
        return "prior_snapshot_missing_redaction"
    if snapshot.live_profile_evidence or snapshot.credential_leak_evidence:
        return "prior_snapshot_live_or_credential_evidence"

    return ""


def _source_skip_reason(
    source_record: EtfSmaPreviewJsonlRecord,
    config: EtfSmaPaperBrokerPreviewConfig,
) -> str:
    if source_record.symbol != _SYMBOL or source_record.symbol not in config.allowlist:
        return "symbol_not_allowed"
    if source_record.asset_class != _ASSET_CLASS:
        return "asset_class_not_supported"
    if source_record.preview_notional is None:
        return source_record.skip_reason or "source_preview_not_accepted"
    if source_record.preview_notional > config.max_notional:
        return "notional_exceeds_m349_cap"
    if not source_record.accepted_for_offline_preview:
        return source_record.skip_reason or "source_preview_not_accepted"
    if source_record.signal_posture == "insufficient_history":
        return "signal_insufficient_history"
    if source_record.signal_posture != "bullish_risk_on":
        return "signal_posture_not_bullish"
    if source_record.intended_side != _SIDE:
        return "source_side_not_buy"
    if source_record.profit_claim != _PROFIT_CLAIM:
        return "source_profit_claim_not_none"

    return ""


def _broker_payload(
    source_record: EtfSmaPreviewJsonlRecord,
    config: EtfSmaPaperBrokerPreviewConfig,
) -> dict[str, object]:
    if source_record.preview_notional is None:
        raise ValidationError("accepted source record requires preview_notional.")

    return {
        "asset_class": _ASSET_CLASS,
        "notional": str(source_record.preview_notional),
        "order_type": config.order_type,
        "side": _SIDE,
        "symbol": _SYMBOL,
        "time_in_force": config.time_in_force,
    }


def _validate_preview_consistency(preview: EtfSmaPaperBrokerPreview) -> None:
    source = preview.source_record
    accepted = preview.accepted_for_broker_payload_preview
    if preview.symbol != source.symbol:
        raise ValidationError("symbol must match source record symbol.")
    if preview.asset_class != source.asset_class:
        raise ValidationError("asset_class must match source record asset_class.")
    if preview.signal_posture != source.signal_posture:
        raise ValidationError("signal_posture must match source record posture.")
    if preview.prior_snapshot_position_count != preview.prior_snapshot.position_count:
        raise ValidationError("prior snapshot position count mismatch.")
    if (
        preview.prior_snapshot_recent_open_order_count
        != preview.prior_snapshot.recent_open_order_count
    ):
        raise ValidationError("prior snapshot recent open order count mismatch.")
    if preview.blocked and preview.skipped:
        raise ValidationError("preview cannot be both blocked and skipped.")
    if accepted:
        if preview.preview_status != _ACCEPTED_PREVIEW_STATUS:
            raise ValidationError("accepted preview_status is invalid.")
        if preview.blocked or preview.skipped:
            raise ValidationError("accepted preview cannot be blocked or skipped.")
        if preview.block_reason or preview.skip_reason:
            raise ValidationError("accepted preview must not carry block or skip reason.")
        if preview.side != _SIDE or preview.order_type != _ORDER_TYPE:
            raise ValidationError("accepted preview must carry the SPY buy payload.")
        if preview.time_in_force != _TIME_IN_FORCE:
            raise ValidationError("accepted preview must use day time_in_force.")
        if preview.notional is None or preview.quantity is not None:
            raise ValidationError("accepted preview must use notional-only sizing.")
        if preview.broker_payload_preview is None:
            raise ValidationError("accepted preview requires broker payload preview.")
        if not preview.local_payload_preview_performed:
            raise ValidationError("accepted preview must render the local payload.")
        return

    if preview.preview_status not in (_BLOCKED_PREVIEW_STATUS, _SKIPPED_PREVIEW_STATUS):
        raise ValidationError("non-accepted preview_status is invalid.")
    if preview.notional is not None or preview.quantity is not None:
        raise ValidationError("non-accepted preview must not carry sizing.")
    if preview.broker_payload_preview is not None:
        raise ValidationError("non-accepted preview must not carry broker payload.")
    if preview.local_payload_preview_performed:
        raise ValidationError("non-accepted preview must not render a local payload.")
    if preview.blocked and not preview.block_reason:
        raise ValidationError("blocked preview requires block_reason.")
    if preview.skipped and not preview.skip_reason:
        raise ValidationError("skipped preview requires skip_reason.")


def _source_record(value: object) -> EtfSmaPreviewJsonlRecord:
    if type(value) is not EtfSmaPreviewJsonlRecord:
        raise ValidationError("source_record must be an EtfSmaPreviewJsonlRecord.")

    _validate_source_record_safety(value)
    return value


def _validate_source_record_safety(record: EtfSmaPreviewJsonlRecord) -> None:
    _reject_live_authorization(record.labels, "source_record_labels")
    _reject_live_authorization(record.source_preview_labels, "source_preview_labels")
    _reject_live_authorization(record.source_signal_labels, "source_signal_labels")
    if record.labels != ETF_SMA_PREVIEW_JSONL_ARTIFACT_LABELS:
        raise ValidationError("source record labels must match M347 labels.")
    if record.profit_claim != _PROFIT_CLAIM:
        raise ValidationError("source record profit_claim must be none.")
    if record.broker_action_performed is not False:
        raise ValidationError("source record broker_action_performed must be false.")
    if record.broker_preview_performed is not False:
        raise ValidationError("source record broker_preview_performed must be false.")
    if record.submit_allowed is not False:
        raise ValidationError("source record submit_allowed must be false.")
    if record.capital_mutated is not False or record.broker_mutated is not False:
        raise ValidationError("source record mutation flags must be false.")


def _snapshot(value: object) -> EtfSmaPaperSnapshotEvidence:
    if type(value) is not EtfSmaPaperSnapshotEvidence:
        raise ValidationError("prior_snapshot must be an EtfSmaPaperSnapshotEvidence.")

    return value


def _preview(value: object) -> EtfSmaPaperBrokerPreview:
    if type(value) is not EtfSmaPaperBrokerPreview:
        raise ValidationError("preview must be an EtfSmaPaperBrokerPreview.")

    return value


def _write_config(value: object) -> EtfSmaPaperBrokerPreviewWriteConfig:
    if type(value) is not EtfSmaPaperBrokerPreviewWriteConfig:
        raise ValidationError(
            "config must be an EtfSmaPaperBrokerPreviewWriteConfig."
        )

    return value


def _preview_status(value: object) -> str:
    statuses = (
        _ACCEPTED_PREVIEW_STATUS,
        _SKIPPED_PREVIEW_STATUS,
        _BLOCKED_PREVIEW_STATUS,
    )
    if type(value) is not str or value not in statuses:
        raise ValidationError("preview_status is invalid.")

    return value


def _optional_broker_payload(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if type(value) is not dict:
        raise ValidationError("broker_payload_preview must be a dict or None.")
    required = {
        "asset_class": _ASSET_CLASS,
        "order_type": _ORDER_TYPE,
        "side": _SIDE,
        "symbol": _SYMBOL,
        "time_in_force": _TIME_IN_FORCE,
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            raise ValidationError(f"broker_payload_preview {key} is invalid.")
    notional = value.get("notional")
    if type(notional) is not str:
        raise ValidationError("broker_payload_preview notional must be a string.")
    _positive_capped_notional(Decimal(notional), "broker_payload_preview.notional")
    return dict(value)


def _output_path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("output_path must be a path string.")
    if str(path).strip() == "":
        raise ValidationError("output_path is required.")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")

    return path


def _prepare_output_parent(
    path: Path,
    config: EtfSmaPaperBrokerPreviewWriteConfig,
) -> bool:
    parent = path.parent
    if str(parent) in ("", ".") or parent.exists():
        return False
    if not config.create_parent_dirs:
        raise ValidationError("output parent directory does not exist.")
    parent.mkdir(parents=True, exist_ok=True)
    return True


def _write_line(path: Path, line: str, *, append: bool) -> None:
    if path.exists() and not append:
        raise ValidationError("output_path already exists; use append mode explicitly.")
    mode = "a" if append else "x"
    with path.open(mode, encoding="utf-8", newline="") as stream:
        stream.write(line)


def _fixed_int(value: object, expected: int, field_name: str) -> int:
    if type(value) is not int or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")

    return value


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")

    return value


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")

    return value


def _positive_capped_notional(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    if value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be a positive Decimal.")
    if value > _MAX_NOTIONAL_CAP:
        raise ValidationError(f"{field_name} must be less than or equal to 25.00.")

    return value


def _optional_positive_capped_notional(
    value: object,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None

    return _positive_capped_notional(value, field_name)


def _symbol_tuple(
    values: object,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("symbol values must be a tuple or list.")

    symbols = tuple(symbol_value(symbol) for symbol in values)
    if not symbols and not allow_empty:
        raise ValidationError("symbol values must not be empty.")
    if symbols and not allow_empty and symbols != (_SYMBOL,):
        raise ValidationError("symbol values must be exactly SPY for M349.")

    return symbols


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(_non_empty_string(item, field_name) for item in values)
    if not items and not allow_empty:
        raise ValidationError(f"{field_name} must not be empty.")

    return items


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name)
    _reject_live_authorization(items, field_name)
    if items != expected:
        raise ValidationError(f"{field_name} must match the required values.")

    return items


def _reject_live_authorization(values: object, field_name: str) -> None:
    if type(values) is str:
        checked_values = (values,)
    elif type(values) in (list, tuple):
        checked_values = tuple(values)
    else:
        raise ValidationError(f"{field_name} must be a string or string tuple.")

    for value in checked_values:
        text = _non_empty_string(value, field_name).strip().lower()
        if (
            text in _FORBIDDEN_LIVE_AUTHORIZATION_VALUES
            or text.startswith("live_authorized=")
        ):
            raise ValidationError(f"{field_name} must not include live authorization.")


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


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")

    return value


def _non_empty_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if text == "":
        raise ValidationError(f"{field_name} is required.")

    return text


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a boolean.")

    return value


def _true_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool or value is not True:
        raise ValidationError(f"{field_name} must be true.")

    return value


def _false_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool or value is not False:
        raise ValidationError(f"{field_name} must be false.")

    return value


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)

    return value


def _bool_text(value: bool) -> str:
    return "true" if value else "false"
