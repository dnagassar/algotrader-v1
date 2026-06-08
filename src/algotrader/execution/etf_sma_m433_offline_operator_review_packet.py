"""M433 offline operator review packet for filled M376 plus buy preview.

This module is a deterministic local artifact reducer. It reads prior JSONL
evidence only and never loads broker configuration, credentials, SDKs, or
network paths.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "DEFAULT_M432_AUTHORIZED_OFFLINE_CYCLE_PREVIEW_RERUN_PATH",
    "DEFAULT_M432_M376_RECONCILIATION_REFRESH_PATH",
    "DEFAULT_M433_OFFLINE_OPERATOR_REVIEW_PACKET_PATH",
    "EtfSmaM433OfflineOperatorReviewPacketConfig",
    "EtfSmaM433OfflineOperatorReviewPacketWriteResult",
    "build_etf_sma_m433_offline_operator_review_packet",
    "render_etf_sma_m433_offline_operator_review_packet_json",
    "render_etf_sma_m433_offline_operator_review_packet_text",
    "write_etf_sma_m433_offline_operator_review_packet_jsonl",
]


DEFAULT_M432_M376_RECONCILIATION_REFRESH_PATH = (
    Path("runs")
    / "paper_lab"
    / "m432_m376_read_only_reconciliation_refresh.jsonl"
)
DEFAULT_M432_AUTHORIZED_OFFLINE_CYCLE_PREVIEW_RERUN_PATH = (
    Path("runs")
    / "paper_lab"
    / "m432_authorized_offline_cycle_preview_rerun.jsonl"
)
DEFAULT_M433_OFFLINE_OPERATOR_REVIEW_PACKET_PATH = (
    Path("runs")
    / "paper_lab"
    / "m433_offline_operator_review_packet.jsonl"
)

_COMMAND = "etf-sma-m433-offline-operator-review-packet"
_RECORD_TYPE = "etf_sma_m433_offline_operator_review_packet"
_SCHEMA_VERSION = "1"
_MILESTONE = "M433"
_REVIEW_SCOPE = "offline_operator_review_packet"
_SYMBOL = "SPY"
_TARGET_CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
_TARGET_BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
_TERMINAL_FILLED_DECISION = "m376_terminal_filled"
_PREVIEW_SUCCESS_STATUS = "offline_cycle_preview_computed"
_BUY_PREVIEW_DECISION = "buy_preview"
_READY_DECISION = "ready_for_separate_operator_authorized_paper_buy_submit_milestone"
_OPEN_ORDER_BLOCKED_DECISION = "blocked_open_order_present"
_AMBIGUOUS_BLOCKED_DECISION = "blocked_m432_evidence_incomplete_or_ambiguous"
_NO_SUBMIT_DECISION = "no_submit_path_from_current_preview"
_READY_NEXT_MILESTONE = "M434_operator_authorized_tiny_spy_paper_buy_submit"
_OPEN_ORDER_NEXT_MILESTONE = "resolve_m376_open_order_before_any_submit_milestone"
_AMBIGUOUS_NEXT_MILESTONE = "rerun_m432_evidence_before_any_submit_milestone"
_NO_SUBMIT_NEXT_MILESTONE = "none_current_preview_not_buy"
_PROFIT_CLAIM = "none"
_TRADE_RECOMMENDATION = "none"
_TERMINAL_ORDER_STATUSES = {
    "filled",
    "canceled",
    "cancelled",
    "expired",
    "rejected",
    "done_for_day",
}
_NONTERMINAL_ORDER_STATUSES = {
    "accepted",
    "accepted_for_bidding",
    "calculated",
    "held",
    "new",
    "partially_filled",
    "pending_cancel",
    "pending_new",
    "pending_replace",
    "stopped",
    "suspended",
}
_SAFETY_FALSE_FIELDS = (
    "submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_read_only",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SOURCE_FALSE_RECONCILIATION_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "live_authorized",
)
_SOURCE_FALSE_PREVIEW_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
    "broker_state_loaded",
)


@dataclass(frozen=True, slots=True)
class EtfSmaM433OfflineOperatorReviewPacketConfig:
    """Explicit local inputs for one M433 offline review packet."""

    run_id: str
    m432_reconciliation_path: (
        str | Path
    ) = DEFAULT_M432_M376_RECONCILIATION_REFRESH_PATH
    m432_preview_path: str | Path = (
        DEFAULT_M432_AUTHORIZED_OFFLINE_CYCLE_PREVIEW_RERUN_PATH
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "m432_reconciliation_path",
            _jsonl_path(self.m432_reconciliation_path, "m432_reconciliation_path"),
        )
        object.__setattr__(
            self,
            "m432_preview_path",
            _jsonl_path(self.m432_preview_path, "m432_preview_path"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaM433OfflineOperatorReviewPacketWriteResult:
    """Local JSONL write metadata for the single M433 record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    submit_authorized: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_read_only: bool
    network_access_attempted: bool
    credential_access_attempted: bool
    live_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        object.__setattr__(
            self,
            "newline_terminated",
            _true_bool(self.newline_terminated, "newline_terminated"),
        )
        for field_name in _SAFETY_FALSE_FIELDS:
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "newline_terminated": self.newline_terminated,
            "submit_authorized": self.submit_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_read_only": self.broker_read_only,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


@dataclass(frozen=True, slots=True)
class _ReconciliationSummary:
    decision: str
    terminal_state: str
    observed_order_status: str
    observed_filled_qty: str
    observed_remaining_qty: str
    open_order_count: int | None
    open_spy_order_count: int | None
    spy_position_present: bool
    spy_position_qty: str
    unexpected_position_symbols: tuple[str, ...]
    blockers: tuple[str, ...]
    open_order_blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PreviewSummary:
    status: str
    decision: str
    sma_posture: str
    paper_preview_computed: bool
    blockers: tuple[str, ...]


def build_etf_sma_m433_offline_operator_review_packet(
    config: EtfSmaM433OfflineOperatorReviewPacketConfig,
) -> dict[str, object]:
    """Build one deterministic local-only M433 operator review packet."""

    checked_config = _config(config)
    payload = _base_payload(checked_config)

    reconciliation_record, reconciliation_read_blockers = _load_single_jsonl_record(
        checked_config.m432_reconciliation_path,
        "m432_reconciliation",
    )
    preview_record, preview_read_blockers = _load_single_jsonl_record(
        checked_config.m432_preview_path,
        "m432_preview",
    )

    reconciliation = _summarize_reconciliation(reconciliation_record)
    preview = _summarize_preview(preview_record)
    _copy_reconciliation_summary(payload, reconciliation)
    _copy_preview_summary(payload, preview)

    evidence_blockers = _dedupe(
        (
            *reconciliation_read_blockers,
            *preview_read_blockers,
            *reconciliation.blockers,
            *preview.blockers,
        )
    )

    if reconciliation.open_order_blockers:
        return _complete_payload(
            payload,
            readiness_decision=_OPEN_ORDER_BLOCKED_DECISION,
            next_required_milestone=_OPEN_ORDER_NEXT_MILESTONE,
            blockers=reconciliation.open_order_blockers,
        )

    if evidence_blockers:
        return _complete_payload(
            payload,
            readiness_decision=_AMBIGUOUS_BLOCKED_DECISION,
            next_required_milestone=_AMBIGUOUS_NEXT_MILESTONE,
            blockers=evidence_blockers,
        )

    if preview.decision != _BUY_PREVIEW_DECISION:
        return _complete_payload(
            payload,
            readiness_decision=_NO_SUBMIT_DECISION,
            next_required_milestone=_NO_SUBMIT_NEXT_MILESTONE,
            blockers=[],
        )

    return _complete_payload(
        payload,
        readiness_decision=_READY_DECISION,
        next_required_milestone=_READY_NEXT_MILESTONE,
        blockers=[],
    )


def render_etf_sma_m433_offline_operator_review_packet_json(
    payload: Mapping[str, object],
) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_m433_offline_operator_review_packet_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing M433 packet summary."""

    return "\n".join(
        (
            "M433 offline operator review packet",
            f"run_id: {payload.get('run_id', '')}",
            f"m376_reconciliation_decision: "
            f"{payload.get('m376_reconciliation_decision', '')}",
            f"m376_terminal_state: {payload.get('m376_terminal_state', '')}",
            f"m376_observed_order_status: "
            f"{payload.get('m376_observed_order_status', '')}",
            f"open_order_count: {payload.get('open_order_count', '')}",
            f"open_spy_order_count: {payload.get('open_spy_order_count', '')}",
            f"spy_position_present: "
            f"{_bool_text(payload.get('spy_position_present'))}",
            f"spy_position_qty: {payload.get('spy_position_qty', '')}",
            "cycle_preview_status: "
            f"{payload.get('cycle_preview_status', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"sma_posture: {payload.get('sma_posture', '')}",
            f"readiness_decision: {payload.get('readiness_decision', '')}",
            f"next_required_milestone: "
            f"{payload.get('next_required_milestone', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            "operator_approval_required: "
            f"{_bool_text(payload.get('operator_approval_required'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            f"broker_read_only: {_bool_text(payload.get('broker_read_only'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            f"trade_recommendation: {payload.get('trade_recommendation', '')}",
            f"profit_claim: {payload.get('profit_claim', '')}",
        )
    )


def write_etf_sma_m433_offline_operator_review_packet_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaM433OfflineOperatorReviewPacketWriteResult:
    """Write exactly one JSONL record, replacing any prior local artifact."""

    checked_payload = dict(payload)
    _validate_m433_safety_fields(checked_payload)
    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_m433_offline_operator_review_packet_json(
        checked_payload
    ) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaM433OfflineOperatorReviewPacketWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        submit_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_read_only=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _base_payload(
    config: EtfSmaM433OfflineOperatorReviewPacketConfig,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "run_id": config.run_id,
        "milestone": _MILESTONE,
        "review_scope": _REVIEW_SCOPE,
        "symbol": _SYMBOL,
        "source_reconciliation_artifact": str(config.m432_reconciliation_path),
        "source_preview_artifact": str(config.m432_preview_path),
        "target_client_order_id": _TARGET_CLIENT_ORDER_ID,
        "target_broker_order_id": _TARGET_BROKER_ORDER_ID,
        "m376_reconciliation_decision": "",
        "m376_terminal_state": "",
        "m376_observed_order_status": "",
        "m376_observed_filled_qty": "",
        "m376_observed_remaining_qty": "",
        "open_order_count": None,
        "open_spy_order_count": None,
        "spy_position_present": False,
        "spy_position_qty": "",
        "unexpected_position_symbols": [],
        "cycle_preview_status": "",
        "cycle_decision": "",
        "sma_posture": "",
        "paper_preview_computed": False,
        "readiness_decision": _AMBIGUOUS_BLOCKED_DECISION,
        "next_required_milestone": _AMBIGUOUS_NEXT_MILESTONE,
        "operator_approval_required": True,
        "trade_recommendation": _TRADE_RECOMMENDATION,
        "profit_claim": _PROFIT_CLAIM,
        "paper_lab_only": True,
        "not_live_authorized": True,
        "labels": [
            "paper_lab_only",
            "offline_operator_review_packet",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "blockers": [],
        "notes": [
            "M433 is offline-only and does not authorize or perform submit.",
            "Prior M432 read-only broker evidence may record broker reads, "
            "network access, or credential access; this M433 packet does not.",
        ],
        "provenance_summary": (
            "Consumes M432 read-only M376 reconciliation refresh and M432 "
            "authorized offline cycle preview rerun."
        ),
    }
    payload.update(_safety_false_payload())
    return payload


def _complete_payload(
    payload: dict[str, object],
    *,
    readiness_decision: str,
    next_required_milestone: str,
    blockers: Sequence[str],
) -> dict[str, object]:
    payload.update(
        {
            "readiness_decision": readiness_decision,
            "next_required_milestone": next_required_milestone,
            "blockers": list(_dedupe(tuple(blockers))),
        }
    )
    payload.update(_safety_false_payload())
    _validate_m433_safety_fields(payload)
    return payload


def _copy_reconciliation_summary(
    payload: dict[str, object],
    reconciliation: _ReconciliationSummary,
) -> None:
    payload.update(
        {
            "m376_reconciliation_decision": reconciliation.decision,
            "m376_terminal_state": reconciliation.terminal_state,
            "m376_observed_order_status": reconciliation.observed_order_status,
            "m376_observed_filled_qty": reconciliation.observed_filled_qty,
            "m376_observed_remaining_qty": reconciliation.observed_remaining_qty,
            "open_order_count": reconciliation.open_order_count,
            "open_spy_order_count": reconciliation.open_spy_order_count,
            "spy_position_present": reconciliation.spy_position_present,
            "spy_position_qty": reconciliation.spy_position_qty,
            "unexpected_position_symbols": list(
                reconciliation.unexpected_position_symbols
            ),
        }
    )


def _copy_preview_summary(
    payload: dict[str, object],
    preview: _PreviewSummary,
) -> None:
    payload.update(
        {
            "cycle_preview_status": preview.status,
            "cycle_decision": preview.decision,
            "sma_posture": preview.sma_posture,
            "paper_preview_computed": preview.paper_preview_computed,
        }
    )


def _summarize_reconciliation(
    record: Mapping[str, object] | None,
) -> _ReconciliationSummary:
    if record is None:
        return _empty_reconciliation()

    decision = _first_text(
        record.get("reconciliation_decision"),
        record.get("source_reconciliation_decision"),
    )
    observed_status = _first_text(
        record.get("observed_order_status"),
        record.get("observed_status"),
    ).lower()
    terminal_state = _m376_terminal_state(record, decision, observed_status)
    open_order_count = _open_order_count(record)
    open_spy_order_count = _open_spy_order_count(record, open_order_count)
    spy_position_qty = _first_text(record.get("spy_position_qty"))
    spy_position_present = _spy_position_present(record, spy_position_qty)
    unexpected_symbols = _unexpected_position_symbols(record)

    blockers = list(
        _reconciliation_evidence_blockers(
            record=record,
            decision=decision,
            terminal_state=terminal_state,
            observed_status=observed_status,
            observed_filled_qty=_first_text(record.get("observed_filled_qty")),
            observed_remaining_qty=_first_text(record.get("observed_remaining_qty")),
            open_order_count=open_order_count,
            open_spy_order_count=open_spy_order_count,
            spy_position_present=spy_position_present,
            spy_position_qty=spy_position_qty,
            unexpected_position_symbols=unexpected_symbols,
        )
    )
    open_order_blockers = _open_order_blockers(
        record=record,
        decision=decision,
        observed_status=observed_status,
        terminal_state=terminal_state,
        open_order_count=open_order_count,
        open_spy_order_count=open_spy_order_count,
    )

    return _ReconciliationSummary(
        decision=decision,
        terminal_state=terminal_state,
        observed_order_status=observed_status,
        observed_filled_qty=_first_text(record.get("observed_filled_qty")),
        observed_remaining_qty=_first_text(record.get("observed_remaining_qty")),
        open_order_count=open_order_count,
        open_spy_order_count=open_spy_order_count,
        spy_position_present=spy_position_present,
        spy_position_qty=spy_position_qty,
        unexpected_position_symbols=unexpected_symbols,
        blockers=_dedupe(tuple(blockers)),
        open_order_blockers=open_order_blockers,
    )


def _empty_reconciliation() -> _ReconciliationSummary:
    return _ReconciliationSummary(
        decision="",
        terminal_state="",
        observed_order_status="",
        observed_filled_qty="",
        observed_remaining_qty="",
        open_order_count=None,
        open_spy_order_count=None,
        spy_position_present=False,
        spy_position_qty="",
        unexpected_position_symbols=(),
        blockers=(),
        open_order_blockers=(),
    )


def _summarize_preview(record: Mapping[str, object] | None) -> _PreviewSummary:
    if record is None:
        return _PreviewSummary(
            status="",
            decision="",
            sma_posture="",
            paper_preview_computed=False,
            blockers=(),
        )

    status = _first_text(record.get("cycle_preview_status"))
    decision = _first_text(record.get("cycle_decision"))
    paper_preview_computed = record.get("paper_preview_computed") is True
    blockers = _preview_evidence_blockers(
        record=record,
        status=status,
        decision=decision,
        paper_preview_computed=paper_preview_computed,
    )
    return _PreviewSummary(
        status=status,
        decision=decision,
        sma_posture=_first_text(record.get("sma_posture")),
        paper_preview_computed=paper_preview_computed,
        blockers=blockers,
    )


def _reconciliation_evidence_blockers(
    *,
    record: Mapping[str, object],
    decision: str,
    terminal_state: str,
    observed_status: str,
    observed_filled_qty: str,
    observed_remaining_qty: str,
    open_order_count: int | None,
    open_spy_order_count: int | None,
    spy_position_present: bool,
    spy_position_qty: str,
    unexpected_position_symbols: tuple[str, ...],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if record.get("milestone") != "M432":
        blockers.append("m432_reconciliation_milestone_unexpected")
    if record.get("symbol") != _SYMBOL:
        blockers.append("m432_reconciliation_symbol_not_spy")
    if _first_text(record.get("target_client_order_id"), record.get("client_order_id")) != (
        _TARGET_CLIENT_ORDER_ID
    ):
        blockers.append("m432_reconciliation_target_client_order_id_mismatch")
    if _first_text(record.get("target_broker_order_id"), record.get("broker_order_id")) != (
        _TARGET_BROKER_ORDER_ID
    ):
        blockers.append("m432_reconciliation_target_broker_order_id_mismatch")
    for field_name in _SOURCE_FALSE_RECONCILIATION_FIELDS:
        if field_name in record and record[field_name] is not False:
            blockers.append(f"m432_reconciliation_{field_name}_not_false")
    if record.get("profit_claim") not in (None, _PROFIT_CLAIM):
        blockers.append("m432_reconciliation_profit_claim_not_none")
    if record.get("trade_recommendation") not in (None, _TRADE_RECOMMENDATION):
        blockers.append("m432_reconciliation_trade_recommendation_not_none")
    if _string_list(record.get("mismatches")):
        blockers.append("m432_reconciliation_mismatches_present")
    blockers.extend(_source_blockers(record, "m432_reconciliation"))

    if decision != _TERMINAL_FILLED_DECISION:
        blockers.append("m376_terminal_filled_not_proven")
    if terminal_state != "terminal_filled":
        blockers.append("m376_terminal_state_not_terminal_filled")
    if observed_status != "filled":
        blockers.append("m376_observed_order_status_not_filled")
    if not _quantity_positive(observed_filled_qty):
        blockers.append("m376_observed_filled_qty_missing_or_nonpositive")
    if not _quantity_zero_or_blank(observed_remaining_qty):
        blockers.append("m376_observed_remaining_qty_not_zero")
    if open_order_count is None:
        blockers.append("open_order_count_missing")
    if open_spy_order_count is None:
        blockers.append("open_spy_order_count_missing")
    if open_order_count not in (None, 0):
        blockers.append("open_order_present")
    if open_spy_order_count not in (None, 0):
        blockers.append("open_spy_order_present")
    if spy_position_present or not _quantity_zero_or_blank(spy_position_qty):
        blockers.append("spy_position_not_flat")
    if unexpected_position_symbols:
        blockers.append("unexpected_position_symbols_present")
    return _dedupe(tuple(blockers))


def _open_order_blockers(
    *,
    record: Mapping[str, object],
    decision: str,
    observed_status: str,
    terminal_state: str,
    open_order_count: int | None,
    open_spy_order_count: int | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if open_order_count is not None and open_order_count > 0:
        blockers.append("open_order_present")
    if open_spy_order_count is not None and open_spy_order_count > 0:
        blockers.append("open_order_present")
    if record.get("open_order_present") is True:
        blockers.append("open_order_present")
    if record.get("open_spy_order_present") is True:
        blockers.append("open_order_present")
    nonterminal_status = observed_status in _NONTERMINAL_ORDER_STATUSES
    nonterminal_decision = "nonterminal" in decision or "open" in decision
    if nonterminal_status or nonterminal_decision:
        blockers.append("m376_order_nonterminal")
    return _dedupe(tuple(blockers))


def _preview_evidence_blockers(
    *,
    record: Mapping[str, object],
    status: str,
    decision: str,
    paper_preview_computed: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if record.get("command") != "etf-sma-authorized-offline-cycle-preview":
        blockers.append("m432_preview_command_unexpected")
    if record.get("milestone") != "M431":
        blockers.append("m432_preview_milestone_unexpected")
    if record.get("symbol") != _SYMBOL:
        blockers.append("m432_preview_symbol_not_spy")
    if status != _PREVIEW_SUCCESS_STATUS:
        blockers.append("m432_preview_status_not_computed")
    if decision == "":
        blockers.append("m432_preview_cycle_decision_missing")
    if not paper_preview_computed:
        blockers.append("m432_preview_paper_preview_computed_not_true")
    if _string_list(record.get("blockers")):
        blockers.append("m432_preview_blockers_present")
    for field_name in _SOURCE_FALSE_PREVIEW_FIELDS:
        if field_name in record and record[field_name] is not False:
            blockers.append(f"m432_preview_{field_name}_not_false")
    if record.get("profit_claim") not in (None, _PROFIT_CLAIM):
        blockers.append("m432_preview_profit_claim_not_none")
    if record.get("trade_recommendation") not in (None, _TRADE_RECOMMENDATION):
        blockers.append("m432_preview_trade_recommendation_not_none")
    return _dedupe(tuple(blockers))


def _source_blockers(
    record: Mapping[str, object],
    prefix: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    for blocker in _string_list(record.get("blockers")):
        if blocker:
            blockers.append(f"{prefix}_source_blocker_{blocker}")
    return _dedupe(tuple(blockers))


def _m376_terminal_state(
    record: Mapping[str, object],
    decision: str,
    observed_status: str,
) -> str:
    terminal_marker = _first_text(
        record.get("source_terminal_state"),
        record.get("terminal_state"),
    ).lower()
    if decision == _TERMINAL_FILLED_DECISION and observed_status == "filled":
        return "terminal_filled"
    if terminal_marker == "terminal" or record.get("terminal_state") is True:
        if observed_status in _TERMINAL_ORDER_STATUSES:
            return f"terminal_{observed_status}"
        return "terminal"
    if observed_status in _TERMINAL_ORDER_STATUSES:
        return f"terminal_{observed_status}"
    if observed_status in _NONTERMINAL_ORDER_STATUSES:
        return "nonterminal"
    if terminal_marker:
        return terminal_marker
    return ""


def _open_order_count(record: Mapping[str, object]) -> int | None:
    count = _optional_non_negative_int(record.get("open_order_count"))
    if count is not None:
        return count
    if record.get("open_order_present") is False:
        return 0
    if record.get("open_order_present") is True:
        symbols = _string_list(record.get("open_order_symbols"))
        return len(symbols) if symbols else None
    return None


def _open_spy_order_count(
    record: Mapping[str, object],
    open_order_count: int | None,
) -> int | None:
    count = _first_optional_non_negative_int(
        record.get("open_spy_order_count"),
        record.get("spy_open_order_count"),
    )
    if count is not None:
        return count
    if record.get("open_spy_order_present") is False:
        return 0
    if record.get("open_spy_order_present") is True:
        return 1
    symbols = tuple(item.upper() for item in _string_list(record.get("open_order_symbols")))
    if symbols:
        return sum(1 for item in symbols if item == _SYMBOL)
    if open_order_count == 0:
        return 0
    return None


def _spy_position_present(
    record: Mapping[str, object],
    spy_position_qty: str,
) -> bool:
    if record.get("spy_position_present") is True:
        return True
    if record.get("spy_position_present") is False:
        return False
    return not _quantity_zero_or_blank(spy_position_qty)


def _unexpected_position_symbols(
    record: Mapping[str, object],
) -> tuple[str, ...]:
    symbols: list[str] = []
    for value in _string_list(record.get("unexpected_position_symbols")):
        _append_symbol(symbols, value)
    for value in _string_list(record.get("open_order_symbols")):
        if value.upper() != _SYMBOL and record.get("open_order_present") is True:
            _append_symbol(symbols, value)
    for item in _position_items(record.get("non_spy_positions")):
        _append_symbol(symbols, _position_symbol(item))
    if record.get("unexpected_non_spy_position_present") is True and not symbols:
        symbols.append("UNKNOWN")
    return _dedupe(tuple(symbols))


def _load_single_jsonl_record(
    path: Path,
    artifact_name: str,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if not path.exists():
        return None, (f"{artifact_name}_artifact_not_found",)
    if not path.is_file():
        return None, (f"{artifact_name}_artifact_path_not_file",)

    records: list[dict[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, (f"{artifact_name}_artifact_unreadable",)

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            return None, (f"{artifact_name}_artifact_invalid_json_line_{line_number}",)
        if not isinstance(decoded, Mapping):
            return None, (f"{artifact_name}_artifact_record_{line_number}_not_object",)
        records.append(dict(decoded))

    if not records:
        return None, (f"{artifact_name}_artifact_empty",)
    if len(records) != 1:
        return None, (f"ambiguous_{artifact_name}_artifact_record_count",)
    return records[0], ()


def _config(value: object) -> EtfSmaM433OfflineOperatorReviewPacketConfig:
    if type(value) is not EtfSmaM433OfflineOperatorReviewPacketConfig:
        raise ValidationError(
            "config must be an EtfSmaM433OfflineOperatorReviewPacketConfig."
        )
    return value


def _jsonl_path(value: object, field_name: str) -> Path:
    path = _required_path(value, field_name)
    if type(value) is str and "://" in value:
        raise ValidationError(f"{field_name} must be a local JSONL path.")
    if path.suffix.lower() != ".jsonl":
        raise ValidationError(f"{field_name} must reference a JSONL file.")
    return path


def _output_path(value: object) -> Path:
    path = _jsonl_path(value, "output_path")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _required_path(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _first_optional_non_negative_int(*values: object) -> int | None:
    for value in values:
        integer = _optional_non_negative_int(value)
        if integer is not None:
            return integer
    return None


def _optional_non_negative_int(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value
    if type(value) is str and value.isdigit():
        return int(value)
    return None


def _quantity_positive(value: str) -> bool:
    decimal = _decimal_or_none(value)
    return decimal is not None and decimal > Decimal("0")


def _quantity_zero_or_blank(value: str) -> bool:
    decimal = _decimal_or_none(value)
    return decimal is not None and decimal == Decimal("0")


def _decimal_or_none(value: str) -> Decimal | None:
    if value == "":
        return Decimal("0")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _position_items(value: object) -> tuple[object, ...]:
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return tuple(value)
    return ()


def _position_symbol(value: object) -> str:
    if isinstance(value, Mapping):
        return _first_text(value.get("symbol")).upper()
    return _first_text(value).upper()


def _append_symbol(symbols: list[str], value: str) -> None:
    symbol = value.upper()
    if symbol and symbol != _SYMBOL:
        symbols.append(symbol)


def _safety_false_payload() -> dict[str, bool]:
    return {field_name: False for field_name in _SAFETY_FALSE_FIELDS}


def _validate_m433_safety_fields(payload: Mapping[str, object]) -> None:
    if payload.get("operator_approval_required") is not True:
        raise ValidationError("operator_approval_required must be true.")
    for field_name in _SAFETY_FALSE_FIELDS:
        if payload.get(field_name) is not False:
            raise ValidationError(f"{field_name} must be false.")
    if payload.get("trade_recommendation") != _TRADE_RECOMMENDATION:
        raise ValidationError("trade_recommendation must be none.")
    if payload.get("profit_claim") != _PROFIT_CLAIM:
        raise ValidationError("profit_claim must be none.")


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _first_text(*values: object) -> str:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return ""


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_json_safe(item) for item in value]
    if type(value) is list:
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
