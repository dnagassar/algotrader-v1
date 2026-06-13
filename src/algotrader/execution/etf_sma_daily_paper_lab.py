"""Assistant v1 daily ETF/SMA paper-lab command center.

This module is completely offline, deterministic, credential-free,
network-free, and broker-free. It generates the first operator-facing daily
assistant packet for the controlled SPY SMA 50/200 paper-lab strategy.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)

__all__ = [
    "EtfSmaDailyPaperLabConfig",
    "run_etf_sma_daily_paper_lab",
    "build_etf_sma_daily_paper_lab",
    "validate_etf_sma_daily_paper_lab_packet",
]

_DEFAULT_SYMBOL = "SPY"
_DEFAULT_BARS_CSV = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
_STRATEGY_NAME = "SPY daily long-only ETF SMA 50/200 trend filter"
_SCHEMA_VERSION = "1"
_ASSISTANT_VERSION = "assistant_v1"
_ASSISTANT_PACKET_VERSION = "assistant_v1.1"
_ASSISTANT_ACTION_QUEUE_VERSION = "assistant_v1.3_action_queue"
_RESEARCH_BOARD_VERSION = "assistant_v1.3_research_board"
_QUALITY_GATE_VERSION = "assistant_v1.4_quality_gate"
_REVIEW_HANDOFF_VERSION = "assistant_v1.4_review_handoff"
_DECISION_LEDGER_VERSION = "assistant_v1.5_decision_ledger"
_DECISION_LEDGER_ENTRY_VERSION = "assistant_v1.5_decision_ledger_entry"
_PACKET_TYPE = "daily_trading_research_command_center"
_COMMAND = "etf-sma-daily-paper-lab"
_SCRIPT = "scripts/run_daily_paper_lab.ps1"
_BRIEF_FILENAME = "operating_brief.md"
_RECORD_FILENAME = "operating_record.jsonl"
_MANIFEST_FILENAME = "manifest.jsonl"
_HISTORY_LEDGER_FILENAME = "history_ledger.jsonl"
_REVIEW_HANDOFF_FILENAME = "review_handoff.md"
_DECISION_LEDGER_FILENAME = "decision_ledger.jsonl"
_REVIEW_INPUTS_DIRNAME = "review_inputs"
_HISTORY_ENTRY_VERSION = "assistant_v1.2_history_entry"
_REQUIRED_LABELS = [
    "paper_lab_only",
    "signal_evaluation_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "offline_only",
    "broker_state_not_observed",
    "paper_submit_not_authorized",
]
_EXPECTED_ARTIFACTS = (
    ("operating_brief", _BRIEF_FILENAME),
    ("operating_record", _RECORD_FILENAME),
    ("manifest", _MANIFEST_FILENAME),
    ("review_handoff", _REVIEW_HANDOFF_FILENAME),
)
_REQUIRED_PACKET_FIELDS = (
    "input_data_path",
    "as_of_date",
    "active_strategy_name",
    "posture",
    "sma_posture_status",
    "preview_decision",
    "blocker_status",
    "broker_state_mode",
    "next_operator_action",
    "safety_labels",
    "assistant_packet_version",
    "history_ledger_path",
    "history_delta",
    "executive_action_queue",
    "executive_action_summary",
    "research_lab",
    "quality_gate_status",
    "quality_gate_score",
    "quality_gate_passed_required_count",
    "quality_gate_failed_required_count",
    "quality_gate_warning_count",
    "quality_gate_required_fields_present",
    "quality_gate_failed_checks",
    "quality_gate_warning_checks",
    "quality_gate_required_checks",
    "quality_gate_optional_checks",
    "review_handoff_path",
    "review_handoff_status",
    "decision_ledger_version",
    "decision_ledger_path",
    "decision_ledger_status",
    "decision_ledger_append_status",
    "decision_ledger_entry_count",
    "review_input_status",
    "review_classification",
    "reviewer_source",
    "review_selected_next_action",
)
_REQUIRED_MANIFEST_FIELDS = (
    "input_data_path",
    "as_of_date",
    "active_strategy_name",
    "posture",
    "sma_posture_status",
    "preview_decision",
    "blocker_status",
    "broker_state_mode",
    "paper_submit_authorized",
    "paper_submit_authorization_status",
    "next_operator_action",
    "safety_labels",
    "assistant_packet_version",
    "validation_status",
    "missing_required_fields",
    "artifact_presence_status",
    "history_ledger_path",
    "history_delta",
    "executive_action_queue",
    "executive_action_summary",
    "quality_gate_status",
    "quality_gate_score",
    "quality_gate_passed_required_count",
    "quality_gate_failed_required_count",
    "quality_gate_warning_count",
    "quality_gate_required_fields_present",
    "quality_gate_failed_checks",
    "quality_gate_warning_checks",
    "quality_gate_required_checks",
    "quality_gate_optional_checks",
    "review_handoff_path",
    "review_handoff_status",
    "decision_ledger_version",
    "decision_ledger_path",
    "decision_ledger_status",
    "decision_ledger_append_status",
    "decision_ledger_entry_count",
    "review_input_status",
    "review_classification",
    "reviewer_source",
    "review_selected_next_action",
)
_REQUIRED_FIELDS_ALLOW_EMPTY = {
    "quality_gate_failed_checks",
    "quality_gate_warning_checks",
    "quality_gate_required_checks",
    "quality_gate_optional_checks",
}
_REVIEW_CLASSIFICATIONS = (
    "accepted",
    "accepted-with-minor-note",
    "needs-repair",
    "rejected",
)
_REVIEW_NON_INPUT_CLASSIFICATIONS = (
    "missing",
    "unclassified",
)
_REVIEW_TEXT_SUFFIXES = (".md", ".markdown", ".txt")
_REVIEW_FORBIDDEN_NEXT_ACTION_TERMS = (
    "submit",
    "cancel",
    "replace",
    "liquidate",
    "live trading",
    "live order",
    "paper order",
    "broker read",
    "broker mutation",
    "alpaca",
    "credential",
)
_REQUIRED_DELTA_FIELDS = (
    "previous_packet_found",
    "previous_as_of_date",
    "current_as_of_date",
    "posture_changed",
    "previous_posture",
    "current_posture",
    "preview_decision_changed",
    "previous_preview_decision",
    "current_preview_decision",
    "blocker_status_changed",
    "previous_blocker_status",
    "current_blocker_status",
    "validation_status_changed",
    "previous_validation_status",
    "current_validation_status",
    "broker_state_mode_changed",
    "previous_broker_state_mode",
    "current_broker_state_mode",
    "research_board_changed",
    "research_board_delta_status",
    "next_operator_action_changed",
    "delta_summary_text",
)
_BRIEF_REQUIRED_VALUE_FIELDS = (
    "input_data_path",
    "as_of_date",
    "active_strategy_name",
    "sma_posture_status",
    "preview_decision",
    "blocker_status",
    "broker_state_mode",
    "next_operator_action",
)
_REQUIRED_ACTION_QUEUE_FIELDS = (
    "action_id",
    "priority",
    "action_type",
    "title",
    "rationale",
    "reason_codes",
    "blocked_by",
    "requires_daniel",
    "hard_gate_required",
    "expected_artifact_or_command",
    "safety_scope",
)
_REQUIRED_RESEARCH_BOARD_FIELDS = (
    "candidate_name",
    "status",
    "hypothesis",
    "evidence_status",
    "confidence_status",
    "missing_evidence",
    "next_research_action",
    "promotion_blockers",
    "safety_scope",
    "notes",
)
_ACTION_PRIORITIES = ("P0", "P1", "P2", "P3")
_ACTION_PRIORITY_RANK = {
    priority: rank for rank, priority in enumerate(_ACTION_PRIORITIES)
}
_ACTION_TYPES = (
    "operator_action",
    "research_action",
    "validation_action",
    "blocked_action",
    "noop",
)
_RESEARCH_BOARD_STATUSES = (
    "active_baseline",
    "candidate",
    "backlog",
    "rejected",
    "blocked",
)
_P0_VALIDATION_FIELD_MARKERS = (
    "paper_submit_authorized_false_or_not_authorized",
    "broker_state_observed_false",
    "broker_state_mode_offline_or_not_observed",
    "safety_labels",
)
_NOT_AUTHORIZED_STATUSES = {
    "not_authorized",
    "paper_submit_not_authorized",
}
_FORBIDDEN_BROKER_NOT_OBSERVED_CLAIMS = (
    "no positions",
    "no open orders",
    "zero positions",
    "zero open orders",
)


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPaperLabConfig:
    """Configuration for the Assistant v1 daily paper-lab loop."""

    output_root: Path | str
    bars_csv: Path | str = _DEFAULT_BARS_CSV
    as_of_date: str | None = None
    symbol: str = _DEFAULT_SYMBOL
    sma_fast_window: int = 50
    sma_slow_window: int = 200

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _required_path(self.output_root, "output_root"))
        object.__setattr__(self, "bars_csv", _required_path(self.bars_csv, "bars_csv"))
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        if self.sma_fast_window <= 0:
            raise ValidationError("sma_fast_window must be positive.")
        if self.sma_slow_window <= 0:
            raise ValidationError("sma_slow_window must be positive.")
        if self.sma_fast_window >= self.sma_slow_window:
            raise ValidationError("sma_fast_window must be less than sma_slow_window.")


def run_etf_sma_daily_paper_lab(config: EtfSmaDailyPaperLabConfig) -> dict[str, Any]:
    """Execute the daily assistant command and write the packet artifacts."""
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    history_ledger_path = output_root / _HISTORY_LEDGER_FILENAME
    history_entries = _read_history_ledger(history_ledger_path)
    previous_history_entry = history_entries[-1] if history_entries else None

    payload = build_etf_sma_daily_paper_lab(config)
    _apply_history_delta(payload, previous_history_entry)
    _apply_executive_action_queue(payload)

    _write_packet_artifacts(output_root=output_root, payload=payload)
    validation = validate_etf_sma_daily_paper_lab_packet(output_root, packet=payload)
    _apply_packet_validation(payload, validation)
    _apply_history_delta(payload, previous_history_entry)
    _apply_executive_action_queue(payload)

    history_entry = _build_history_entry(
        payload=payload,
        sequence_number=len(history_entries) + 1,
    )
    _append_history_entry(history_ledger_path, history_entry)
    payload["history_ledger_entry"] = dict(history_entry)
    payload["executive_dashboard"]["history_ledger_entry_sequence"] = history_entry[
        "sequence_number"
    ]
    _write_packet_artifacts(output_root=output_root, payload=payload)
    pre_review_quality_gate = _build_quality_gate(output_root)
    _apply_quality_gate(payload, pre_review_quality_gate)
    _apply_review_decision_state(payload, output_root)
    _apply_executive_action_queue(payload)
    _write_packet_artifacts(output_root=output_root, payload=payload)
    quality_gate = _build_quality_gate(output_root)
    _apply_quality_gate(payload, quality_gate)
    _write_packet_artifacts(output_root=output_root, payload=payload)

    return payload


def validate_etf_sma_daily_paper_lab_packet(
    output_root: Path | str,
    *,
    packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a generated Assistant v1.1 daily paper-lab packet."""
    root = Path(output_root)
    artifact_presence_status = _artifact_presence_status(root)
    packet_payload = packet
    read_failures: list[str] = []

    if packet_payload is None:
        packet_payload, read_failures = _read_packet_record(root / _RECORD_FILENAME)

    missing_required_fields: list[str] = []
    missing_required_fields.extend(read_failures)
    if packet_payload is None:
        missing_required_fields.append("operating_record.packet")
    else:
        missing_required_fields.extend(_missing_packet_fields(packet_payload))
        missing_required_fields.extend(_missing_manifest_fields(root, packet_payload))
        missing_required_fields.extend(_missing_brief_references(root, packet_payload))

    validation_status = (
        "pass"
        if (
            artifact_presence_status["status"] == "pass"
            and not missing_required_fields
        )
        else "fail"
    )
    quality_gate = _build_quality_gate(root, packet_payload)
    return {
        "assistant_packet_version": _ASSISTANT_PACKET_VERSION,
        "validation_status": validation_status,
        "missing_required_fields": missing_required_fields,
        "artifact_presence_status": artifact_presence_status,
        **quality_gate,
    }


def _write_packet_artifacts(
    *,
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    record_file = output_root / _RECORD_FILENAME
    record_line = json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":")) + "\n"
    record_file.write_text(record_line, encoding="utf-8", newline="\n")

    brief_file = output_root / _BRIEF_FILENAME
    brief_file.write_text(_render_brief_markdown(payload), encoding="utf-8", newline="\n")

    review_handoff_file = output_root / _REVIEW_HANDOFF_FILENAME
    review_handoff_file.write_text(
        _render_review_handoff_markdown(payload),
        encoding="utf-8",
        newline="\n",
    )

    manifest_file = output_root / _MANIFEST_FILENAME
    manifest_data = _build_manifest(output_root, payload)
    manifest_line = json.dumps(manifest_data, sort_keys=True, separators=(",", ":")) + "\n"
    manifest_file.write_text(manifest_line, encoding="utf-8", newline="\n")


def _apply_packet_validation(
    payload: dict[str, Any],
    validation: Mapping[str, Any],
) -> None:
    payload["assistant_packet_version"] = str(validation["assistant_packet_version"])
    payload["validation_status"] = str(validation["validation_status"])
    payload["missing_required_fields"] = list(validation["missing_required_fields"])
    payload["artifact_presence_status"] = dict(validation["artifact_presence_status"])
    payload["executive_dashboard"]["validation_status"] = payload["validation_status"]
    payload["executive_dashboard"]["missing_required_fields"] = list(
        payload["missing_required_fields"]
    )
    payload["executive_dashboard"]["artifact_presence_status"] = dict(
        payload["artifact_presence_status"]
    )


def _apply_quality_gate(
    payload: dict[str, Any],
    quality_gate: Mapping[str, Any],
) -> None:
    payload["quality_gate_version"] = str(
        quality_gate.get("quality_gate_version", _QUALITY_GATE_VERSION)
    )
    payload["quality_gate_status"] = str(quality_gate["quality_gate_status"])
    payload["quality_gate_score"] = str(quality_gate["quality_gate_score"])
    payload["quality_gate_passed_required_count"] = int(
        quality_gate["quality_gate_passed_required_count"]
    )
    payload["quality_gate_failed_required_count"] = int(
        quality_gate["quality_gate_failed_required_count"]
    )
    payload["quality_gate_warning_count"] = int(
        quality_gate["quality_gate_warning_count"]
    )
    payload["quality_gate_required_fields_present"] = bool(
        quality_gate["quality_gate_required_fields_present"]
    )
    payload["quality_gate_failed_checks"] = list(
        quality_gate["quality_gate_failed_checks"]
    )
    payload["quality_gate_warning_checks"] = list(
        quality_gate["quality_gate_warning_checks"]
    )
    payload["quality_gate_required_checks"] = list(
        quality_gate["quality_gate_required_checks"]
    )
    payload["quality_gate_optional_checks"] = list(
        quality_gate["quality_gate_optional_checks"]
    )
    payload["review_handoff_version"] = str(
        quality_gate.get("review_handoff_version", _REVIEW_HANDOFF_VERSION)
    )
    payload["review_handoff_path"] = str(quality_gate["review_handoff_path"])
    payload["review_handoff_status"] = str(quality_gate["review_handoff_status"])
    payload["executive_dashboard"]["quality_gate_status"] = payload[
        "quality_gate_status"
    ]
    payload["executive_dashboard"]["quality_gate_score"] = payload[
        "quality_gate_score"
    ]
    payload["executive_dashboard"]["quality_gate_failed_checks"] = list(
        payload["quality_gate_failed_checks"]
    )
    payload["executive_dashboard"]["quality_gate_warning_checks"] = list(
        payload["quality_gate_warning_checks"]
    )
    payload["executive_dashboard"]["review_handoff_path"] = payload[
        "review_handoff_path"
    ]
    payload["executive_dashboard"]["review_handoff_status"] = payload[
        "review_handoff_status"
    ]


def _apply_executive_action_queue(payload: dict[str, Any]) -> None:
    action_queue = _build_executive_action_queue(payload)
    action_summary = _build_executive_action_summary(action_queue)
    payload["executive_action_queue_version"] = _ASSISTANT_ACTION_QUEUE_VERSION
    payload["executive_action_queue"] = action_queue
    payload["executive_action_summary"] = action_summary
    payload["daniel_action_required_now"] = action_summary["daniel_action_required"]
    payload["executive_dashboard"]["executive_action_queue"] = list(action_queue)
    payload["executive_dashboard"]["executive_action_summary"] = dict(action_summary)
    if "executive_summary" in payload:
        payload["executive_summary"]["daniel_action_required"] = action_summary[
            "daniel_action_status"
        ]


def _build_executive_action_queue(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    validation_status = str(payload.get("validation_status", "pending"))
    if validation_status == "fail":
        actions.append(_validation_action(payload))

    if str(payload.get("posture")) == "insufficient_history":
        slow_window = int(payload.get("sma_slow_window", 200))
        actions.append(
            _action_queue_item(
                action_id="provide_missing_offline_daily_history",
                priority="P1",
                action_type="operator_action",
                title="Supply enough offline daily bars for the SMA baseline",
                rationale=(
                    f"The baseline has fewer than {slow_window} usable as-of bars, "
                    "so the preview remains blocked until the local input data is "
                    "refreshed."
                ),
                reason_codes=[
                    "insufficient_history",
                    f"slow_sma_window_{slow_window}_not_met",
                    "offline_input_required",
                ],
                blocked_by=[
                    str(payload.get("sma_posture_status", "insufficient_history"))
                ],
                requires_daniel=True,
                hard_gate_required=False,
                expected_artifact_or_command=(
                    "refresh offline SPY daily CSV input, then rerun "
                    f"{_SCRIPT} -OutputRoot runs/daily_lab/latest"
                ),
                safety_scope="offline_data_refresh_only_no_broker_access",
            )
        )

    history_delta = payload.get("history_delta")
    if _history_delta_needs_review(history_delta):
        actions.append(
            _action_queue_item(
                action_id="review_material_history_delta",
                priority="P1",
                action_type="operator_action",
                title="Review material daily packet delta",
                rationale=(
                    "A tracked posture, blocker, or validation field changed "
                    "relative to the prior packet in this output-root history."
                ),
                reason_codes=_history_delta_reason_codes(history_delta),
                blocked_by=[],
                requires_daniel=True,
                hard_gate_required=False,
                expected_artifact_or_command="review operating_brief.md and history_ledger.jsonl",
                safety_scope="offline_review_only_no_broker_access",
            )
        )

    review_classification = str(payload.get("review_classification", "missing"))
    if review_classification in {"needs-repair", "rejected"}:
        actions.append(_review_feedback_action(payload, review_classification))

    research_lab = payload.get("research_lab")
    if _research_confidence_not_quantified(research_lab):
        actions.append(
            _action_queue_item(
                action_id="quantify_spy_sma_baseline_confidence",
                priority="P2",
                action_type="research_action",
                title="Quantify confidence for the SPY SMA 50/200 baseline",
                rationale=(
                    "The research board explicitly marks confidence as not yet "
                    "quantified, so the next research improvement is an offline "
                    "confidence packet for the existing baseline."
                ),
                reason_codes=[
                    "research_confidence_not_quantified",
                    "active_baseline_confidence_gap",
                    "offline_research_backlog",
                ],
                blocked_by=["strategy_confidence_not_yet_quantified"],
                requires_daniel=False,
                hard_gate_required=False,
                expected_artifact_or_command=(
                    "future offline research artifact quantifying baseline confidence"
                ),
                safety_scope="offline_research_only_no_new_strategy_no_broker_access",
            )
        )

    if not any(action["requires_daniel"] for action in actions):
        actions.append(
            _action_queue_item(
                action_id="no_daniel_action_required_now",
                priority="P3",
                action_type="noop",
                title="No Daniel action required now",
                rationale=(
                    "The packet is an offline preview, broker state was not "
                    "observed, and no paper submit authorization is present."
                ),
                reason_codes=[
                    "no_human_action_required",
                    "broker_state_not_observed",
                    "paper_submit_not_authorized",
                ],
                blocked_by=[],
                requires_daniel=False,
                hard_gate_required=False,
                expected_artifact_or_command="none",
                safety_scope=(
                    "offline_preview_only; broker_state_not_observed; future "
                    "broker reads require a separately scoped hard gate"
                ),
            )
        )

    return sorted(
        actions,
        key=lambda item: (
            _ACTION_PRIORITY_RANK[item["priority"]],
            item["action_id"],
        ),
    )


def _review_feedback_action(
    payload: Mapping[str, Any],
    classification: str,
) -> dict[str, Any]:
    if classification == "rejected":
        return _action_queue_item(
            action_id="stop_on_rejected_review_feedback",
            priority="P1",
            action_type="blocked_action",
            title="Stop relying on packet until rejected review feedback is repaired",
            rationale=(
                "An offline saved review classified this packet as rejected. "
                "Repair must stay inside the offline packet workflow."
            ),
            reason_codes=[
                "review_feedback_ingested",
                "review_classification_rejected",
                "offline_packet_repair_required",
            ],
            blocked_by=["review_classification_rejected"],
            requires_daniel=False,
            hard_gate_required=True,
            expected_artifact_or_command=str(
                payload.get(
                    "review_selected_next_action",
                    _default_review_next_action(classification),
                )
            ),
            safety_scope="offline_review_repair_only_no_broker_access_no_submit",
        )

    return _action_queue_item(
        action_id="repair_review_feedback_before_next_packet_use",
        priority="P1",
        action_type="validation_action",
        title="Repair offline packet from review feedback",
        rationale=(
            "An offline saved review classified this packet as needing repair. "
            "The next step is deterministic packet repair, not broker access."
        ),
        reason_codes=[
            "review_feedback_ingested",
            "review_classification_needs_repair",
            "offline_packet_repair_required",
        ],
        blocked_by=["review_classification_needs_repair"],
        requires_daniel=False,
        hard_gate_required=False,
        expected_artifact_or_command=str(
            payload.get(
                "review_selected_next_action",
                _default_review_next_action(classification),
            )
        ),
        safety_scope="offline_review_repair_only_no_broker_access_no_submit",
    )


def _validation_action(payload: Mapping[str, Any]) -> dict[str, Any]:
    missing_fields = [
        str(item) for item in payload.get("missing_required_fields", [])
    ]
    priority = _validation_failure_priority(missing_fields)
    if priority == "P0":
        return _action_queue_item(
            action_id="validation_safety_invariant_failure",
            priority="P0",
            action_type="validation_action",
            title="Stop for packet safety invariant failure",
            rationale=(
                "Validation failed on a safety-critical field. Normal daily-lab "
                "workflow must stop until the packet is repaired."
            ),
            reason_codes=["validation_failed", "safety_invariant_failure"],
            blocked_by=missing_fields,
            requires_daniel=True,
            hard_gate_required=True,
            expected_artifact_or_command="repair packet safety invariant before use",
            safety_scope="offline_validation_stop_no_broker_access_no_submit",
        )

    artifact_status = payload.get("artifact_presence_status")
    artifact_state = "artifact_presence_unknown"
    if isinstance(artifact_status, Mapping):
        artifact_state = str(artifact_status.get("status", artifact_state))
    return _action_queue_item(
        action_id="validation_packet_repair_required",
        priority="P1",
        action_type="validation_action",
        title="Repair daily packet validation failure",
        rationale=(
            "Validation failed on packet completeness or artifact presence, but "
            "no safety-critical broker or submit invariant was violated."
        ),
        reason_codes=["validation_failed", artifact_state],
        blocked_by=missing_fields,
        requires_daniel=True,
        hard_gate_required=False,
        expected_artifact_or_command="rerun offline packet generation after repair",
        safety_scope="offline_validation_repair_no_broker_access",
    )


def _validation_failure_priority(missing_fields: list[str]) -> str:
    for field_name in missing_fields:
        if any(marker in field_name for marker in _P0_VALIDATION_FIELD_MARKERS):
            return "P0"
    return "P1"


def _action_queue_item(
    *,
    action_id: str,
    priority: str,
    action_type: str,
    title: str,
    rationale: str,
    reason_codes: list[str],
    blocked_by: list[str],
    requires_daniel: bool,
    hard_gate_required: bool,
    expected_artifact_or_command: str,
    safety_scope: str,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "priority": priority,
        "action_type": action_type,
        "title": title,
        "rationale": rationale,
        "reason_codes": list(reason_codes),
        "blocked_by": list(blocked_by),
        "requires_daniel": requires_daniel,
        "hard_gate_required": hard_gate_required,
        "expected_artifact_or_command": expected_artifact_or_command,
        "safety_scope": safety_scope,
    }


def _build_executive_action_summary(
    action_queue: list[Mapping[str, Any]],
) -> dict[str, Any]:
    highest_priority = action_queue[0]["priority"] if action_queue else "P3"
    daniel_required = any(bool(item["requires_daniel"]) for item in action_queue)
    if daniel_required:
        daniel_action_status = (
            "Yes: review the P0/P1 executive action queue item before relying "
            "on this packet."
        )
    else:
        daniel_action_status = (
            "No: Daniel does not need to do anything now. The packet remains "
            "offline_preview_only with broker_state_not_observed."
        )
    return {
        "daniel_action_required": daniel_required,
        "daniel_action_status": daniel_action_status,
        "highest_priority": highest_priority,
        "queue_length": len(action_queue),
    }


def _history_delta_needs_review(delta: Any) -> bool:
    if not isinstance(delta, Mapping):
        return False
    return any(
        bool(delta.get(field_name))
        for field_name in (
            "posture_changed",
            "blocker_status_changed",
            "validation_status_changed",
        )
    )


def _history_delta_reason_codes(delta: Any) -> list[str]:
    if not isinstance(delta, Mapping):
        return ["history_delta_unavailable"]
    reason_codes = []
    if delta.get("posture_changed"):
        reason_codes.append("posture_changed")
    if delta.get("blocker_status_changed"):
        reason_codes.append("blocker_status_changed")
    if delta.get("validation_status_changed"):
        reason_codes.append("validation_status_changed")
    return reason_codes or ["history_delta_review"]


def _research_confidence_not_quantified(research_lab: Any) -> bool:
    if not isinstance(research_lab, Mapping):
        return False
    values = [str(research_lab.get("confidence_status", ""))]
    board = research_lab.get(
        "research_board",
        research_lab.get("candidate_strategy_board"),
    )
    if isinstance(board, list):
        for item in board:
            if isinstance(item, Mapping):
                values.append(str(item.get("confidence_status", "")))
    return any("not_yet_quantified" in value for value in values)


def build_etf_sma_daily_paper_lab(config: EtfSmaDailyPaperLabConfig) -> dict[str, Any]:
    """Load inputs and build the Assistant v1 daily paper-lab payload."""
    bars_path = Path(config.bars_csv)
    bars = _load_bars(bars_path, config.symbol)

    if config.as_of_date:
        as_of_str = config.as_of_date.strip()
        try:
            as_of_dt = datetime.combine(
                datetime.fromisoformat(as_of_str).date(),
                datetime.min.time(),
                tzinfo=timezone.utc,
            )
        except ValueError as exc:
            raise ValidationError(
                f"as_of_date must be in YYYY-MM-DD format: {config.as_of_date}"
            ) from exc
        as_of_source = "explicit_config"
    else:
        if not bars:
            raise ValidationError("No usable bars found to derive default as-of date.")
        as_of_dt = max(bar.timestamp for bar in bars)
        as_of_str = as_of_dt.strftime("%Y-%m-%d")
        as_of_source = "latest_input_bar"

    latest_input_bar_date = max(bar.timestamp for bar in bars).strftime("%Y-%m-%d")
    signal = evaluate_etf_sma_signal(
        bars,
        EtfSmaSignalConfig(
            as_of=as_of_dt,
            symbol=config.symbol,
            short_window=config.sma_fast_window,
            long_window=config.sma_slow_window,
        ),
    )

    posture = signal.posture
    sma_fast_value = _decimal_text(signal.short_sma)
    sma_slow_value = _decimal_text(signal.long_sma)
    preview_decision = _preview_decision(posture)
    next_operator_action = _next_operator_action(posture, config.sma_slow_window)
    blocker_status = "broker_state_not_observed"
    broker_state_mode = "broker_state_not_observed"
    output_root = Path(config.output_root)
    artifact_paths = _artifact_paths(output_root)
    quality_gate_defaults = _default_quality_gate_fields(artifact_paths)
    decision_ledger_defaults = _default_decision_ledger_fields(artifact_paths)
    sma_status = _sma_status(
        posture=posture,
        fast_window=config.sma_fast_window,
        slow_window=config.sma_slow_window,
        usable_bar_count=signal.usable_bar_count,
    )
    data_freshness = _data_freshness(
        as_of_date=as_of_str,
        latest_input_bar_date=latest_input_bar_date,
    )
    research_lab = _research_lab(
        config=config,
        as_of_date=as_of_str,
        posture=posture,
        sma_status=sma_status,
        sma_fast_value=sma_fast_value,
        sma_slow_value=sma_slow_value,
    )

    payload: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "assistant_version": _ASSISTANT_VERSION,
        "assistant_packet_version": _ASSISTANT_PACKET_VERSION,
        "packet_type": _PACKET_TYPE,
        "command": _COMMAND,
        "script": _SCRIPT,
        "run_id": f"daily_paper_lab_{as_of_str}",
        "input_data_path": _normalize_path(bars_path),
        "input_data_sha256": _sha256_file(bars_path),
        "as_of_date": as_of_str,
        "as_of_source": as_of_source,
        "latest_input_bar_date": latest_input_bar_date,
        "active_strategy_name": _STRATEGY_NAME,
        "strategy_name": _STRATEGY_NAME,
        "symbol": config.symbol,
        "sma_fast_window": config.sma_fast_window,
        "sma_slow_window": config.sma_slow_window,
        "sma_fast_value": sma_fast_value,
        "sma_slow_value": sma_slow_value,
        "sma_posture_status": sma_status,
        "posture": posture,
        "preview_decision": preview_decision,
        "decision": preview_decision,
        "current_recommendation": _current_recommendation(posture),
        "blocker_status": blocker_status,
        "blockers": [blocker_status],
        "broker_state_mode": broker_state_mode,
        "broker_state_observed": False,
        "broker_state_claim": (
            "Broker positions and open orders were not read; this packet makes no "
            "position or order-state claim."
        ),
        "paper_submit_authorized": False,
        "paper_submit_authorization_status": "not_authorized",
        "paper_submit_authorization_reason": "operator_has_not_authorized_submit",
        "next_operator_action": next_operator_action,
        "labels": list(_REQUIRED_LABELS),
        "safety_labels": list(_REQUIRED_LABELS),
        "data_freshness": data_freshness,
        "validation_status": "pending",
        "missing_required_fields": [],
        "artifact_presence_status": {
            "status": "not_evaluated",
            "missing_artifacts": [],
            "empty_artifacts": [],
            "artifacts": {},
        },
        "system_health": "offline_assistant_packet_ready",
        "artifact_paths": artifact_paths,
        "history_ledger_path": artifact_paths["history_ledger"],
        **quality_gate_defaults,
        **decision_ledger_defaults,
        "history_delta": _empty_history_delta(as_of_str),
        "history_ledger_entry": {},
        "artifacts": {
            "assistant_brief": artifact_paths["assistant_brief"],
            "operating_brief": artifact_paths["assistant_brief"],
            "operating_record": artifact_paths["operating_record"],
            "manifest": artifact_paths["manifest"],
            "history_ledger": artifact_paths["history_ledger"],
            "review_handoff": artifact_paths["review_handoff"],
            "decision_ledger": artifact_paths["decision_ledger"],
            "review_inputs": artifact_paths["review_inputs"],
        },
        "sma": {
            "symbol": signal.symbol,
            "fast_window": signal.short_window,
            "slow_window": signal.long_window,
            "fast_value": sma_fast_value,
            "slow_value": sma_slow_value,
            "latest_close": _decimal_text(signal.latest_close),
            "total_bar_count": signal.total_bar_count,
            "usable_bar_count": signal.usable_bar_count,
            "ignored_future_bar_count": signal.ignored_future_bar_count,
            "posture": posture,
            "status": sma_status,
        },
        "research_lab": research_lab,
        "research_board": list(research_lab["research_board"]),
        "executive_action_queue_version": _ASSISTANT_ACTION_QUEUE_VERSION,
        "executive_action_queue": [],
        "executive_action_summary": {
            "daniel_action_required": False,
            "daniel_action_status": "Action queue has not been evaluated yet.",
            "highest_priority": "P3",
            "queue_length": 0,
        },
        "daniel_action_required_now": False,
        "executive_dashboard": {
            "data_freshness": data_freshness,
            "validation_status": "pending",
            "missing_required_fields": [],
            "artifact_presence_status": {
                "status": "not_evaluated",
                "missing_artifacts": [],
                "empty_artifacts": [],
                "artifacts": {},
            },
            "artifact_paths": artifact_paths,
            "history_ledger_path": artifact_paths["history_ledger"],
            "history_ledger_entry_sequence": None,
            "system_health": "offline_assistant_packet_ready",
            "safety_labels": list(_REQUIRED_LABELS),
            "next_operator_action": next_operator_action,
            "executive_action_queue": [],
            "executive_action_summary": {},
            "quality_gate_status": quality_gate_defaults["quality_gate_status"],
            "quality_gate_score": quality_gate_defaults["quality_gate_score"],
            "quality_gate_failed_checks": list(
                quality_gate_defaults["quality_gate_failed_checks"]
            ),
            "quality_gate_warning_checks": list(
                quality_gate_defaults["quality_gate_warning_checks"]
            ),
            "review_handoff_path": quality_gate_defaults["review_handoff_path"],
            "review_handoff_status": quality_gate_defaults["review_handoff_status"],
            "decision_ledger_path": decision_ledger_defaults[
                "decision_ledger_path"
            ],
            "decision_ledger_status": decision_ledger_defaults[
                "decision_ledger_status"
            ],
            "decision_ledger_append_status": decision_ledger_defaults[
                "decision_ledger_append_status"
            ],
            "review_input_status": decision_ledger_defaults["review_input_status"],
            "review_classification": decision_ledger_defaults[
                "review_classification"
            ],
            "review_selected_next_action": decision_ledger_defaults[
                "review_selected_next_action"
            ],
        },
    }
    payload["executive_summary"] = {
        "plain_english_status": _plain_english_status(payload),
        "current_recommendation": payload["current_recommendation"],
        "current_blocker": blocker_status,
        "daniel_action_required": _daniel_action_required(posture),
    }
    _apply_executive_action_queue(payload)
    return payload


def _load_bars(path: Path, symbol: str) -> list[Bar]:
    if not path.exists():
        raise ValidationError(f"Bars CSV not found: {path}")
    bars = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            bars.append(_parse_row_to_bar(row, symbol))
    return bars


def _row_value(row: Mapping[str, object], field_name: str) -> object:
    for key, value in row.items():
        if str(key).strip().lower() == field_name:
            return value
    return None


def _parse_row_to_bar(row: Mapping[str, object], symbol: str) -> Bar:
    close_val = _row_value(row, "close")
    if close_val in (None, ""):
        raise ValidationError("close price is required in CSV.")
    raw_close = Decimal(str(close_val))

    adj_close_val = _row_value(row, "adjusted_close")
    if adj_close_val not in (None, ""):
        close = Decimal(str(adj_close_val))
        factor = close / raw_close if raw_close != Decimal("0") else Decimal("1")
    else:
        close = raw_close
        factor = Decimal("1")

    open_val = _row_value(row, "open")
    open_price = Decimal(str(open_val)) if open_val not in (None, "") else raw_close

    high_val = _row_value(row, "high")
    high = Decimal(str(high_val)) if high_val not in (None, "") else max(open_price, raw_close)

    low_val = _row_value(row, "low")
    low = Decimal(str(low_val)) if low_val not in (None, "") else min(open_price, raw_close)

    volume_val = _row_value(row, "volume")
    volume = Decimal(str(volume_val)) if volume_val not in (None, "") else Decimal("0")

    open_price = open_price * factor
    high = high * factor
    low = low * factor

    high = max(high, open_price, close)
    low = min(low, open_price, close)

    dt_val = None
    for date_field in ("date", "timestamp", "datetime"):
        val = _row_value(row, date_field)
        if val not in (None, ""):
            dt_val = str(val).strip()
            break

    if not dt_val:
        raise ValidationError("date/timestamp is required in CSV.")

    try:
        if "T" in dt_val:
            dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        else:
            dt = datetime.combine(datetime.fromisoformat(dt_val).date(), datetime.min.time())
    except ValueError as exc:
        raise ValidationError(f"Invalid date format: {dt_val}") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    row_symbol = _row_value(row, "symbol")
    symbol_str = symbol if row_symbol in (None, "") else str(row_symbol).strip().upper()

    return Bar(
        symbol=symbol_str,
        timestamp=dt,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
    return path


def _normalize_path(path: Path | str) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def _artifact_paths(output_root: Path) -> dict[str, str]:
    return {
        "assistant_brief": _normalize_path(output_root / _BRIEF_FILENAME),
        "operating_record": _normalize_path(output_root / _RECORD_FILENAME),
        "manifest": _normalize_path(output_root / _MANIFEST_FILENAME),
        "history_ledger": _normalize_path(output_root / _HISTORY_LEDGER_FILENAME),
        "review_handoff": _normalize_path(output_root / _REVIEW_HANDOFF_FILENAME),
        "decision_ledger": _normalize_path(output_root / _DECISION_LEDGER_FILENAME),
        "review_inputs": _normalize_path(output_root / _REVIEW_INPUTS_DIRNAME),
    }


def _default_quality_gate_fields(artifact_paths: Mapping[str, str]) -> dict[str, Any]:
    return {
        "quality_gate_version": _QUALITY_GATE_VERSION,
        "quality_gate_status": "not_evaluated",
        "quality_gate_score": "0/0 required checks passed; 0 failed; 0 warnings",
        "quality_gate_passed_required_count": 0,
        "quality_gate_failed_required_count": 0,
        "quality_gate_warning_count": 0,
        "quality_gate_required_fields_present": False,
        "quality_gate_failed_checks": [],
        "quality_gate_warning_checks": [],
        "quality_gate_required_checks": [],
        "quality_gate_optional_checks": [],
        "review_handoff_version": _REVIEW_HANDOFF_VERSION,
        "review_handoff_path": str(artifact_paths["review_handoff"]),
        "review_handoff_status": "not_generated",
    }


def _default_decision_ledger_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "decision_ledger_version": _DECISION_LEDGER_VERSION,
        "decision_ledger_path": str(artifact_paths["decision_ledger"]),
        "decision_ledger_status": "decision_ledger_no_review_input",
        "decision_ledger_append_status": "not_appended_no_review_input",
        "decision_ledger_entry_count": 0,
        "decision_ledger_latest_entry": {},
        "review_inputs_path": str(artifact_paths["review_inputs"]),
        "review_input_status": "review_input_not_found",
        "review_input_count": 0,
        "review_input_paths": [],
        "review_input_path": None,
        "review_input_sha256": None,
        "reviewer_source": "reviewer_not_supplied",
        "review_classification": "missing",
        "review_classification_raw": None,
        "review_blockers": [],
        "review_repair_items": [],
        "review_minor_notes": [],
        "review_selected_next_action": "await_offline_review_input",
        "review_decision": {
            "classification": "missing",
            "status": "review_input_not_found",
            "selected_next_action": "await_offline_review_input",
        },
    }


def _read_history_ledger(path: Path) -> list[Mapping[str, Any]]:
    if not path.exists():
        return []

    entries: list[Mapping[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"History ledger is not readable: {path}") from exc

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"History ledger line {index} is not parseable JSON: {path}"
            ) from exc
        if not isinstance(entry, Mapping):
            raise ValidationError(
                f"History ledger line {index} is not a JSON object: {path}"
            )
        entries.append(entry)
    return entries


def _append_history_entry(path: Path, entry: Mapping[str, Any]) -> None:
    line = json.dumps(_json_safe(entry), sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(line)


def _apply_review_decision_state(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    decision_state = _build_review_decision_state(output_root, payload)
    payload.update(decision_state)
    dashboard = payload["executive_dashboard"]
    for field_name in (
        "decision_ledger_path",
        "decision_ledger_status",
        "decision_ledger_append_status",
        "decision_ledger_entry_count",
        "review_input_status",
        "review_input_count",
        "review_input_path",
        "review_input_sha256",
        "reviewer_source",
        "review_classification",
        "review_selected_next_action",
    ):
        dashboard[field_name] = payload[field_name]
    dashboard["review_decision"] = dict(payload["review_decision"])


def _build_review_decision_state(
    output_root: Path,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    ledger_path = output_root / _DECISION_LEDGER_FILENAME
    input_paths = _discover_review_input_paths(output_root / _REVIEW_INPUTS_DIRNAME)
    existing_entries = _read_decision_ledger(ledger_path)
    existing_keys = {
        (
            str(entry.get("review_input_path", "")),
            str(entry.get("review_input_sha256", "")),
        )
        for entry in existing_entries
        if isinstance(entry, Mapping)
    }

    state = _default_decision_ledger_fields(_artifact_paths(output_root))
    state["decision_ledger_entry_count"] = len(existing_entries)
    if existing_entries:
        state["decision_ledger_latest_entry"] = dict(existing_entries[-1])

    if not input_paths:
        input_status = (
            "review_input_not_found"
            if not (output_root / _REVIEW_INPUTS_DIRNAME).exists()
            else "review_input_directory_empty"
        )
        ledger_status = (
            "decision_ledger_existing_no_review_input"
            if existing_entries
            else "decision_ledger_no_review_input"
        )
        state.update(
            {
                "decision_ledger_status": ledger_status,
                "decision_ledger_append_status": "not_appended_no_review_input",
                "review_input_status": input_status,
                "review_decision": {
                    "classification": "missing",
                    "status": input_status,
                    "selected_next_action": "await_offline_review_input",
                },
            }
        )
        return state

    parsed_reports = [_parse_review_input(path) for path in input_paths]
    appended_entries: list[Mapping[str, Any]] = []
    already_recorded_count = 0
    for report in parsed_reports:
        entry_key = (report["review_input_path"], report["review_input_sha256"])
        if entry_key in existing_keys:
            already_recorded_count += 1
            continue
        entry = _build_decision_ledger_entry(
            payload=payload,
            report=report,
            sequence_number=len(existing_entries) + len(appended_entries) + 1,
        )
        _append_decision_ledger_entry(ledger_path, entry)
        appended_entries.append(entry)
        existing_keys.add(entry_key)

    all_entries = [*existing_entries, *appended_entries]
    selected_report = parsed_reports[-1]
    append_status = _decision_ledger_append_status(
        appended_count=len(appended_entries),
        already_recorded_count=already_recorded_count,
    )
    ledger_status = _decision_ledger_status(
        appended_count=len(appended_entries),
        already_recorded_count=already_recorded_count,
    )
    state.update(
        {
            "decision_ledger_status": ledger_status,
            "decision_ledger_append_status": append_status,
            "decision_ledger_entry_count": len(all_entries),
            "decision_ledger_latest_entry": dict(all_entries[-1])
            if all_entries
            else {},
            "review_input_status": "review_input_ingested",
            "review_input_count": len(parsed_reports),
            "review_input_paths": [
                str(report["review_input_path"]) for report in parsed_reports
            ],
            "review_input_path": selected_report["review_input_path"],
            "review_input_sha256": selected_report["review_input_sha256"],
            "reviewer_source": selected_report["reviewer_source"],
            "review_classification": selected_report["classification"],
            "review_classification_raw": selected_report["classification_raw"],
            "review_blockers": list(selected_report["blockers"]),
            "review_repair_items": list(selected_report["repair_items"]),
            "review_minor_notes": list(selected_report["minor_notes"]),
            "review_selected_next_action": selected_report["selected_next_action"],
            "review_decision": {
                "classification": selected_report["classification"],
                "status": "review_input_ingested",
                "reviewer_source": selected_report["reviewer_source"],
                "blockers": list(selected_report["blockers"]),
                "repair_items": list(selected_report["repair_items"]),
                "minor_notes": list(selected_report["minor_notes"]),
                "selected_next_action": selected_report["selected_next_action"],
                "review_input_path": selected_report["review_input_path"],
                "review_input_sha256": selected_report["review_input_sha256"],
                "ledger_append_status": append_status,
            },
        }
    )
    return state


def _discover_review_input_paths(input_root: Path) -> list[Path]:
    if not input_root.exists() or not input_root.is_dir():
        return []
    paths = [
        path
        for path in input_root.iterdir()
        if path.is_file() and path.suffix.lower() in _REVIEW_TEXT_SUFFIXES
    ]
    return sorted(paths, key=lambda path: _normalize_path(path))


def _read_decision_ledger(path: Path) -> list[Mapping[str, Any]]:
    if not path.exists():
        return []
    entries: list[Mapping[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"Decision ledger is not readable: {path}") from exc
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"Decision ledger line {index} is not parseable JSON: {path}"
            ) from exc
        if not isinstance(entry, Mapping):
            raise ValidationError(
                f"Decision ledger line {index} is not a JSON object: {path}"
            )
        entries.append(entry)
    return entries


def _append_decision_ledger_entry(path: Path, entry: Mapping[str, Any]) -> None:
    line = json.dumps(_json_safe(entry), sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(line)


def _parse_review_input(path: Path) -> dict[str, Any]:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"Review input is not readable: {path}") from exc
    text = content.decode("utf-8", errors="replace")
    sections = _parse_review_sections(text)
    classification_raw = _first_review_value(sections, "classification")
    classification = _normalize_review_classification(classification_raw)
    reviewer_source = _reviewer_source(sections, path)
    blockers = _review_list(sections.get("blockers", []))
    repair_items = _review_list(sections.get("repair_items", []))
    minor_notes = _review_list(sections.get("minor_notes", []))
    if classification in {"needs-repair", "rejected"} and not repair_items:
        repair_items = list(blockers)
    if classification == "rejected" and not blockers:
        blockers = ["review_classification_rejected"]
    if classification == "needs-repair" and not blockers and not repair_items:
        repair_items = ["review_classification_needs_repair"]
    recommended_next_action = _first_review_value(sections, "recommended_next_action")
    selected_next_action = _safe_review_next_action(
        recommended_next_action,
        classification,
    )
    return {
        "review_input_path": _normalize_path(path),
        "review_input_sha256": hashlib.sha256(content).hexdigest(),
        "review_input_size": len(content),
        "reviewer_source": reviewer_source,
        "classification": classification,
        "classification_raw": classification_raw,
        "blockers": blockers,
        "repair_items": repair_items,
        "minor_notes": minor_notes,
        "recommended_next_action_raw": recommended_next_action,
        "selected_next_action": selected_next_action,
    }


def _parse_review_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    active_list_key: str | None = None
    for line in text.splitlines():
        key_value = _review_key_value(line)
        if key_value is not None:
            raw_key, value = key_value
            key = _canonical_review_key(raw_key)
            active_list_key = None
            if key is None:
                continue
            if value:
                sections.setdefault(key, []).append(value)
            if key in {"blockers", "repair_items", "minor_notes"}:
                active_list_key = key
            continue
        stripped = line.strip()
        if (
            active_list_key is not None
            and stripped.startswith(("-", "*"))
            and stripped.strip("-* \t")
        ):
            sections.setdefault(active_list_key, []).append(stripped)
    return sections


def _review_key_value(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if ":" not in stripped:
        return None
    key, value = stripped.split(":", 1)
    normalized_key = _review_key_token(key)
    if not normalized_key:
        return None
    return normalized_key, value.strip()


def _review_key_token(value: str) -> str:
    chars = []
    previous_was_separator = False
    for char in value.strip().lower():
        if char.isalnum():
            chars.append(char)
            previous_was_separator = False
        elif not previous_was_separator:
            chars.append("_")
            previous_was_separator = True
    return "".join(chars).strip("_")


def _canonical_review_key(key: str) -> str | None:
    aliases = {
        "classification": "classification",
        "classification_recommendation": "classification",
        "review_classification": "classification",
        "reviewer": "reviewer_source",
        "source": "reviewer_source",
        "review_source": "reviewer_source",
        "reviewer_source": "reviewer_source",
        "blocking_findings": "blockers",
        "blockers": "blockers",
        "blocked_by": "blockers",
        "repair_items": "repair_items",
        "repair_item": "repair_items",
        "required_repairs": "repair_items",
        "repairs": "repair_items",
        "minor_notes": "minor_notes",
        "minor_note": "minor_notes",
        "notes": "minor_notes",
        "recommended_next_action": "recommended_next_action",
        "selected_next_action": "recommended_next_action",
        "next_action": "recommended_next_action",
    }
    return aliases.get(key)


def _first_review_value(sections: Mapping[str, list[str]], key: str) -> str | None:
    values = sections.get(key)
    if not values:
        return None
    for value in values:
        stripped = _strip_review_list_marker(value)
        if stripped:
            return stripped
    return None


def _normalize_review_classification(value: str | None) -> str:
    if value is None or not value.strip():
        return "unclassified"
    if "|" in value:
        return "unclassified"
    token = _classification_token(value)
    variants = (
        ("accepted-with-minor-note", "accepted-with-minor-note"),
        ("accepted-with-minor-notes", "accepted-with-minor-note"),
        ("accepted-minor-note", "accepted-with-minor-note"),
        ("needs-repair", "needs-repair"),
        ("need-repair", "needs-repair"),
        ("rejected", "rejected"),
        ("accepted", "accepted"),
    )
    for prefix, classification in variants:
        if token == prefix or token.startswith(prefix + "-"):
            return classification
    return "unclassified"


def _classification_token(value: str) -> str:
    chars = []
    previous_was_separator = False
    for char in value.strip().lower().replace("_", "-"):
        if char.isalnum():
            chars.append(char)
            previous_was_separator = False
        elif not previous_was_separator:
            chars.append("-")
            previous_was_separator = True
    return "".join(chars).strip("-")


def _reviewer_source(sections: Mapping[str, list[str]], path: Path) -> str:
    detected = _first_review_value(sections, "reviewer_source")
    if detected:
        return _safe_single_line(detected)
    path_stem = _review_key_token(path.stem)
    return path_stem or "offline_review_input"


def _review_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        item = _strip_review_list_marker(value)
        if not item or _review_none_value(item):
            continue
        normalized.append(_safe_single_line(item))
    return normalized


def _strip_review_list_marker(value: str) -> str:
    return value.strip().lstrip("-*").strip()


def _review_none_value(value: str) -> bool:
    token = _classification_token(value)
    return token in {
        "none",
        "n-a",
        "na",
        "not-applicable",
        "no-blockers",
        "no-blocking-findings",
        "no-repair-items",
        "no-minor-notes",
    } or token.startswith("none-or-")


def _safe_single_line(value: str) -> str:
    return " ".join(value.strip().split())


def _safe_review_next_action(
    recommended_next_action: str | None,
    classification: str,
) -> str:
    if recommended_next_action:
        candidate = _safe_single_line(recommended_next_action)
        if candidate and not _contains_forbidden_review_next_action(candidate):
            return candidate
    return _default_review_next_action(classification)


def _contains_forbidden_review_next_action(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in _REVIEW_FORBIDDEN_NEXT_ACTION_TERMS)


def _default_review_next_action(classification: str) -> str:
    if classification == "accepted":
        return "continue_offline_packet_history"
    if classification == "accepted-with-minor-note":
        return "track_minor_review_note_in_offline_backlog"
    if classification == "needs-repair":
        return "repair_offline_packet_from_review_feedback_then_rerun_daily_lab"
    if classification == "rejected":
        return "stop_using_packet_until_offline_review_repair_is_complete"
    if classification == "unclassified":
        return "classify_offline_review_feedback_before_packet_decision"
    return "await_offline_review_input"


def _build_decision_ledger_entry(
    *,
    payload: Mapping[str, Any],
    report: Mapping[str, Any],
    sequence_number: int,
) -> dict[str, Any]:
    return {
        "decision_ledger_entry_version": _DECISION_LEDGER_ENTRY_VERSION,
        "sequence_number": sequence_number,
        "packet_type": payload["packet_type"],
        "run_id": payload["run_id"],
        "as_of_date": payload["as_of_date"],
        "active_strategy_name": payload["active_strategy_name"],
        "assistant_packet_version": payload["assistant_packet_version"],
        "quality_gate_status": payload.get("quality_gate_status", "not_evaluated"),
        "quality_gate_score": payload.get("quality_gate_score", "not_evaluated"),
        "validation_status": payload.get("validation_status", "not_evaluated"),
        "reviewer_source": report["reviewer_source"],
        "classification": report["classification"],
        "classification_raw": report["classification_raw"],
        "blockers": list(report["blockers"]),
        "repair_items": list(report["repair_items"]),
        "minor_notes": list(report["minor_notes"]),
        "selected_next_action": report["selected_next_action"],
        "review_input_path": report["review_input_path"],
        "review_input_sha256": report["review_input_sha256"],
        "review_input_size": report["review_input_size"],
        "ledger_append_status": "appended",
        "safety_scope": "offline_review_decision_only_no_broker_access_no_submit",
    }


def _decision_ledger_append_status(
    *,
    appended_count: int,
    already_recorded_count: int,
) -> str:
    if appended_count == 1:
        return "appended"
    if appended_count > 1:
        return "appended_multiple"
    if already_recorded_count:
        return "already_recorded"
    return "not_appended_no_review_input"


def _decision_ledger_status(
    *,
    appended_count: int,
    already_recorded_count: int,
) -> str:
    if appended_count:
        return "decision_ledger_appended"
    if already_recorded_count:
        return "decision_ledger_already_recorded"
    return "decision_ledger_no_new_entry"


def _apply_history_delta(
    payload: dict[str, Any],
    previous_history_entry: Mapping[str, Any] | None,
) -> None:
    delta = _build_history_delta(payload, previous_history_entry)
    payload["history_delta"] = delta
    payload["executive_dashboard"]["history_delta"] = dict(delta)
    payload["executive_dashboard"]["delta_summary_text"] = delta["delta_summary_text"]


def _empty_history_delta(current_as_of_date: str) -> dict[str, Any]:
    return {
        "previous_packet_found": False,
        "previous_as_of_date": None,
        "current_as_of_date": current_as_of_date,
        "posture_changed": False,
        "previous_posture": None,
        "current_posture": None,
        "preview_decision_changed": False,
        "previous_preview_decision": None,
        "current_preview_decision": None,
        "blocker_status_changed": False,
        "previous_blocker_status": None,
        "current_blocker_status": None,
        "validation_status_changed": False,
        "previous_validation_status": None,
        "current_validation_status": None,
        "broker_state_mode_changed": False,
        "previous_broker_state_mode": None,
        "current_broker_state_mode": None,
        "research_board_changed": False,
        "research_board_delta_status": "not_evaluated",
        "next_operator_action_changed": False,
        "previous_next_operator_action": None,
        "current_next_operator_action": None,
        "delta_summary_text": "History delta has not been evaluated yet.",
    }


def _build_history_delta(
    payload: Mapping[str, Any],
    previous_history_entry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    previous_packet_found = previous_history_entry is not None
    previous = previous_history_entry or {}

    previous_as_of_date = _history_value(previous, "as_of_date")
    current_as_of_date = str(payload["as_of_date"])
    previous_posture = _history_value(previous, "posture")
    current_posture = str(payload["posture"])
    previous_preview_decision = _history_value(previous, "preview_decision")
    current_preview_decision = str(payload["preview_decision"])
    previous_blocker_status = _history_value(previous, "blocker_status")
    current_blocker_status = str(payload["blocker_status"])
    previous_validation_status = _history_value(previous, "validation_status")
    current_validation_status = str(payload["validation_status"])
    previous_broker_state_mode = _history_value(previous, "broker_state_mode")
    current_broker_state_mode = str(payload["broker_state_mode"])
    previous_next_operator_action = _history_value(previous, "next_operator_action")
    current_next_operator_action = str(payload["next_operator_action"])
    previous_research_board_fingerprint = _history_value(
        previous,
        "research_board_fingerprint",
    )
    current_research_board_fingerprint = _research_board_fingerprint(payload)

    posture_changed = _history_changed(
        previous_packet_found,
        previous_posture,
        current_posture,
    )
    preview_decision_changed = _history_changed(
        previous_packet_found,
        previous_preview_decision,
        current_preview_decision,
    )
    blocker_status_changed = _history_changed(
        previous_packet_found,
        previous_blocker_status,
        current_blocker_status,
    )
    validation_status_changed = _history_changed(
        previous_packet_found,
        previous_validation_status,
        current_validation_status,
    )
    broker_state_mode_changed = _history_changed(
        previous_packet_found,
        previous_broker_state_mode,
        current_broker_state_mode,
    )
    research_board_changed = _history_changed(
        previous_packet_found,
        previous_research_board_fingerprint,
        current_research_board_fingerprint,
    )
    next_operator_action_changed = _history_changed(
        previous_packet_found,
        previous_next_operator_action,
        current_next_operator_action,
    )

    if not previous_packet_found:
        research_board_delta_status = "no_previous_packet"
    elif research_board_changed:
        research_board_delta_status = "changed"
    else:
        research_board_delta_status = "unchanged"

    delta: dict[str, Any] = {
        "previous_packet_found": previous_packet_found,
        "previous_as_of_date": previous_as_of_date,
        "current_as_of_date": current_as_of_date,
        "posture_changed": posture_changed,
        "previous_posture": previous_posture,
        "current_posture": current_posture,
        "preview_decision_changed": preview_decision_changed,
        "previous_preview_decision": previous_preview_decision,
        "current_preview_decision": current_preview_decision,
        "blocker_status_changed": blocker_status_changed,
        "previous_blocker_status": previous_blocker_status,
        "current_blocker_status": current_blocker_status,
        "validation_status_changed": validation_status_changed,
        "previous_validation_status": previous_validation_status,
        "current_validation_status": current_validation_status,
        "broker_state_mode_changed": broker_state_mode_changed,
        "previous_broker_state_mode": previous_broker_state_mode,
        "current_broker_state_mode": current_broker_state_mode,
        "research_board_changed": research_board_changed,
        "research_board_delta_status": research_board_delta_status,
        "previous_research_board_fingerprint": previous_research_board_fingerprint,
        "current_research_board_fingerprint": current_research_board_fingerprint,
        "next_operator_action_changed": next_operator_action_changed,
        "previous_next_operator_action": previous_next_operator_action,
        "current_next_operator_action": current_next_operator_action,
    }
    delta["delta_summary_text"] = _delta_summary_text(delta)
    return delta


def _history_value(entry: Mapping[str, Any], field_name: str) -> str | None:
    value = entry.get(field_name)
    if value is None:
        return None
    return str(value)


def _history_changed(
    previous_packet_found: bool,
    previous_value: str | None,
    current_value: str | None,
) -> bool:
    return previous_packet_found and previous_value != current_value


def _delta_summary_text(delta: Mapping[str, Any]) -> str:
    if not delta["previous_packet_found"]:
        return (
            "No prior packet was found in this output root history; this is the "
            "first observed packet in the selected history."
        )

    changes: list[str] = []
    if delta["previous_as_of_date"] != delta["current_as_of_date"]:
        changes.append(
            "as-of date moved from "
            f"{delta['previous_as_of_date']} to {delta['current_as_of_date']}"
        )
    if delta["posture_changed"]:
        changes.append(
            "posture changed from "
            f"{delta['previous_posture']} to {delta['current_posture']}"
        )
    if delta["preview_decision_changed"]:
        changes.append(
            "preview decision changed from "
            f"{delta['previous_preview_decision']} to "
            f"{delta['current_preview_decision']}"
        )
    if delta["blocker_status_changed"]:
        changes.append(
            "blocker status changed from "
            f"{delta['previous_blocker_status']} to {delta['current_blocker_status']}"
        )
    if delta["validation_status_changed"]:
        changes.append(
            "validation status changed from "
            f"{delta['previous_validation_status']} to "
            f"{delta['current_validation_status']}"
        )
    if delta["broker_state_mode_changed"]:
        changes.append(
            "broker-state mode changed from "
            f"{delta['previous_broker_state_mode']} to "
            f"{delta['current_broker_state_mode']}"
        )
    if delta["research_board_changed"]:
        changes.append("research board changed")
    if delta["next_operator_action_changed"]:
        changes.append(
            "next operator action changed from "
            f"{delta['previous_next_operator_action']} to "
            f"{delta['current_next_operator_action']}"
        )

    if not changes:
        return (
            "Prior packet found; no tracked posture, decision, blocker, validation, "
            "broker-state, research-board, or operator-action fields changed."
        )
    return "Prior packet found; " + "; ".join(changes) + "."


def _build_history_entry(
    *,
    payload: Mapping[str, Any],
    sequence_number: int,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "history_entry_version": _HISTORY_ENTRY_VERSION,
        "sequence_number": sequence_number,
        "run_id": payload["run_id"],
        "as_of_date": payload["as_of_date"],
        "active_strategy_name": payload["active_strategy_name"],
        "input_data_path": payload["input_data_path"],
        "input_data_sha256": payload["input_data_sha256"],
        "posture": payload["posture"],
        "sma_posture_status": payload["sma_posture_status"],
        "preview_decision": payload["preview_decision"],
        "blocker_status": payload["blocker_status"],
        "validation_status": payload["validation_status"],
        "broker_state_mode": payload["broker_state_mode"],
        "broker_state_observed": payload["broker_state_observed"],
        "paper_submit_authorized": payload["paper_submit_authorized"],
        "paper_submit_authorization_status": payload[
            "paper_submit_authorization_status"
        ],
        "research_board_status": _research_board_status(payload),
        "research_board_fingerprint": _research_board_fingerprint(payload),
        "next_operator_action": payload["next_operator_action"],
        "delta_summary_text": payload["history_delta"]["delta_summary_text"],
        "safety_labels": list(payload["safety_labels"]),
    }
    entry["packet_summary_sha256"] = _history_entry_digest(entry)
    return entry


def _history_entry_digest(entry: Mapping[str, Any]) -> str:
    digest_source = {
        key: value
        for key, value in entry.items()
        if key != "packet_summary_sha256"
    }
    encoded = json.dumps(
        _json_safe(digest_source),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _research_board_status(payload: Mapping[str, Any]) -> str:
    research_lab = payload.get("research_lab")
    if not isinstance(research_lab, Mapping):
        return "research_lab_missing"
    candidate_board = research_lab.get("candidate_strategy_board")
    if not isinstance(candidate_board, list) or not candidate_board:
        return "candidate_strategy_board_empty"
    statuses = []
    for item in candidate_board:
        if isinstance(item, Mapping):
            statuses.append(str(item.get("status", "status_missing")))
        else:
            statuses.append("candidate_entry_not_object")
    return ",".join(statuses)


def _research_board_fingerprint(payload: Mapping[str, Any]) -> str:
    research_lab = payload.get("research_lab")
    candidate_board: Any = []
    if isinstance(research_lab, Mapping):
        candidate_board = research_lab.get("candidate_strategy_board", [])
    encoded = json.dumps(
        _json_safe(candidate_board),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact_presence_status(output_root: Path) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    missing_artifacts: list[str] = []
    empty_artifacts: list[str] = []

    for kind, filename in _EXPECTED_ARTIFACTS:
        path = output_root / filename
        exists = path.exists() and path.is_file()
        non_empty = exists and path.stat().st_size > 0
        if not exists:
            missing_artifacts.append(kind)
        elif not non_empty:
            empty_artifacts.append(kind)
        artifacts[kind] = {
            "path": _normalize_path(path),
            "exists": exists,
            "non_empty": non_empty,
        }

    return {
        "status": "pass" if not missing_artifacts and not empty_artifacts else "fail",
        "missing_artifacts": missing_artifacts,
        "empty_artifacts": empty_artifacts,
        "artifacts": artifacts,
    }


def _read_packet_record(path: Path) -> tuple[Mapping[str, Any] | None, list[str]]:
    return _read_jsonl_mapping(path, "operating_record")


def _read_manifest_record(path: Path) -> tuple[Mapping[str, Any] | None, list[str]]:
    return _read_jsonl_mapping(path, "manifest")


def _read_jsonl_mapping(
    path: Path,
    artifact_name: str,
) -> tuple[Mapping[str, Any] | None, list[str]]:
    if not path.exists():
        return None, []
    try:
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError:
        return None, [f"{artifact_name}.readable"]
    if len(lines) != 1:
        return None, [f"{artifact_name}.single_jsonl_record"]
    try:
        record = json.loads(lines[0])
    except json.JSONDecodeError:
        return None, [f"{artifact_name}.parseable_jsonl"]
    if not isinstance(record, Mapping):
        return None, [f"{artifact_name}.record_object"]
    return record, []


def _build_quality_gate(
    output_root: Path | str,
    packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(output_root)
    record, record_failures = _read_packet_record(root / _RECORD_FILENAME)
    manifest, manifest_failures = _read_manifest_record(root / _MANIFEST_FILENAME)
    packet_for_checks: Mapping[str, Any]
    if record is not None:
        packet_for_checks = record
    elif isinstance(packet, Mapping):
        packet_for_checks = packet
    else:
        packet_for_checks = {}

    brief_text = _read_text_or_empty(root / _BRIEF_FILENAME)
    review_handoff_path = root / _REVIEW_HANDOFF_FILENAME
    review_handoff_text = _read_text_or_empty(review_handoff_path)
    artifact_presence_status = _artifact_presence_status(root)

    record_missing = list(record_failures)
    if record is None:
        record_missing.append("operating_record.packet")
    else:
        record_missing.extend(_missing_packet_fields(record))

    manifest_missing = list(manifest_failures)
    if manifest is None:
        manifest_missing.append("manifest.record")
    else:
        manifest_missing.extend(_missing_manifest_fields(root, packet_for_checks))

    brief_missing = _missing_key_brief_sections(brief_text)
    broker_claim_forbidden = _forbidden_broker_state_claims(
        packet_for_checks,
        brief_text,
        review_handoff_text,
    )
    action_queue_ok, action_queue_summary = _quality_action_queue_summary(
        packet_for_checks.get("executive_action_queue")
    )
    research_board_ok, research_board_summary = _quality_research_board_summary(
        packet_for_checks
    )
    history_delta_missing = _missing_history_delta_fields(
        "history_delta",
        packet_for_checks.get("history_delta"),
    )
    safety_label_missing = _missing_safety_labels(packet_for_checks)
    handoff_missing = _missing_review_handoff_references(
        review_handoff_text,
    )
    decision_ledger_ok, decision_ledger_summary = _quality_decision_ledger_summary(
        root,
        packet_for_checks,
    )
    review_classification_ok, review_classification_summary = (
        _quality_review_classification_summary(packet_for_checks)
    )
    review_input_hash_ok, review_input_hash_summary = (
        _quality_review_input_hash_summary(packet_for_checks)
    )
    review_next_action_ok, review_next_action_summary = (
        _quality_review_next_action_summary(packet_for_checks)
    )

    required_checks = [
        _quality_check(
            "required_packet_artifacts_exist",
            artifact_presence_status["status"] == "pass",
            _quality_artifact_summary(artifact_presence_status),
        ),
        _quality_check(
            "required_operating_record_fields_exist",
            not record_missing,
            _quality_missing_summary(record_missing),
        ),
        _quality_check(
            "required_manifest_fields_exist",
            not manifest_missing,
            _quality_missing_summary(manifest_missing),
        ),
        _quality_check(
            "markdown_brief_references_key_assistant_sections",
            not brief_missing,
            _quality_missing_summary(brief_missing),
        ),
        _quality_check(
            "broker_state_mode_explicit",
            packet_for_checks.get("broker_state_mode")
            in {"broker_state_not_observed", "offline_preview_only"},
            f"broker_state_mode={packet_for_checks.get('broker_state_mode')}",
        ),
        _quality_check(
            "broker_not_observed_has_no_position_order_claim",
            not broker_claim_forbidden,
            _quality_missing_summary(broker_claim_forbidden),
        ),
        _quality_check(
            "paper_submit_not_authorized",
            _paper_submit_not_authorized(packet_for_checks),
            (
                "paper_submit_authorized="
                f"{packet_for_checks.get('paper_submit_authorized')}; "
                "paper_submit_authorization_status="
                f"{packet_for_checks.get('paper_submit_authorization_status')}"
            ),
        ),
        _quality_check(
            "executive_action_queue_priorities_deterministic",
            action_queue_ok,
            action_queue_summary,
        ),
        _quality_check(
            "research_board_has_spy_sma_50_200_active_baseline",
            research_board_ok,
            research_board_summary,
        ),
        _quality_check(
            "history_delta_exists",
            not history_delta_missing,
            _quality_missing_summary(history_delta_missing),
        ),
        _quality_check(
            "safety_labels_exist",
            not safety_label_missing,
            _quality_missing_summary(safety_label_missing),
        ),
        _quality_check(
            "review_handoff_references_generated_artifacts",
            not handoff_missing,
            _quality_missing_summary(handoff_missing),
        ),
        _quality_check(
            "decision_ledger_status_recorded",
            decision_ledger_ok,
            decision_ledger_summary,
        ),
        _quality_check(
            "review_classification_normalized",
            review_classification_ok,
            review_classification_summary,
        ),
        _quality_check(
            "review_input_path_hash_recorded_when_present",
            review_input_hash_ok,
            review_input_hash_summary,
        ),
        _quality_check(
            "review_selected_next_action_safety_scoped",
            review_next_action_ok,
            review_next_action_summary,
        ),
    ]
    optional_checks: list[dict[str, Any]] = []

    failed_checks = [
        check["check_id"] for check in required_checks if check["status"] == "fail"
    ]
    warning_checks = [
        check["check_id"]
        for check in optional_checks
        if check["status"] in {"warn", "fail"}
    ]
    passed_required_count = sum(
        1 for check in required_checks if check["status"] == "pass"
    )
    failed_required_count = len(failed_checks)
    warning_count = len(warning_checks)
    if failed_checks:
        quality_gate_status = "fail"
    elif warning_checks:
        quality_gate_status = "warn"
    else:
        quality_gate_status = "pass"

    review_handoff_status = (
        "generated"
        if review_handoff_path.exists()
        and review_handoff_path.is_file()
        and review_handoff_path.stat().st_size > 0
        else "missing"
    )
    quality_gate_score = (
        f"{passed_required_count}/{len(required_checks)} required checks passed; "
        f"{failed_required_count} failed; {warning_count} warnings"
    )
    review_handoff_path_text = _review_handoff_path(packet_for_checks, root)
    return {
        "quality_gate_version": _QUALITY_GATE_VERSION,
        "quality_gate_status": quality_gate_status,
        "quality_gate_score": quality_gate_score,
        "quality_gate_passed_required_count": passed_required_count,
        "quality_gate_failed_required_count": failed_required_count,
        "quality_gate_warning_count": warning_count,
        "quality_gate_required_fields_present": not record_missing
        and not manifest_missing,
        "quality_gate_failed_checks": failed_checks,
        "quality_gate_warning_checks": warning_checks,
        "quality_gate_required_checks": required_checks,
        "quality_gate_optional_checks": optional_checks,
        "review_handoff_version": _REVIEW_HANDOFF_VERSION,
        "review_handoff_path": review_handoff_path_text,
        "review_handoff_status": review_handoff_status,
    }


def _quality_check(check_id: str, passed: bool, summary: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "summary": summary,
    }


def _read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _quality_artifact_summary(status: Mapping[str, Any]) -> str:
    missing = list(status.get("missing_artifacts", []))
    empty = list(status.get("empty_artifacts", []))
    if not missing and not empty:
        return "all required packet artifacts exist and are non-empty"
    parts = []
    if missing:
        parts.append("missing=" + ",".join(str(item) for item in missing))
    if empty:
        parts.append("empty=" + ",".join(str(item) for item in empty))
    return "; ".join(parts)


def _quality_missing_summary(missing: list[str]) -> str:
    if not missing:
        return "all required items present"
    return "missing_or_failed=" + ",".join(missing)


def _missing_key_brief_sections(brief_text: str) -> list[str]:
    required_tokens = [
        "## Executive summary",
        "## Executive Action Queue",
        "## Trading desk brief",
        "## Research Board",
        "## Executive dashboard",
        "Quality Gate",
        "Decision Ledger",
        _REVIEW_HANDOFF_FILENAME,
    ]
    return [token for token in required_tokens if token not in brief_text]


def _forbidden_broker_state_claims(
    packet: Mapping[str, Any],
    brief_text: str,
    review_handoff_text: str,
) -> list[str]:
    broker_state_mode = str(packet.get("broker_state_mode", ""))
    if broker_state_mode not in {"broker_state_not_observed", "offline_preview_only"}:
        return []
    combined_text = (
        json.dumps(_json_safe(packet), sort_keys=True, separators=(",", ":"))
        + "\n"
        + brief_text
        + "\n"
        + review_handoff_text
    ).lower()
    return [
        forbidden
        for forbidden in _FORBIDDEN_BROKER_NOT_OBSERVED_CLAIMS
        if forbidden in combined_text
    ]


def _quality_action_queue_summary(action_queue: Any) -> tuple[bool, str]:
    missing = _missing_action_queue_fields("executive_action_queue", action_queue)
    if missing:
        return False, _quality_missing_summary(missing)
    assert isinstance(action_queue, list)
    expected = sorted(
        action_queue,
        key=lambda item: (
            _ACTION_PRIORITY_RANK[str(item["priority"])],
            str(item["action_id"]),
        ),
    )
    if list(action_queue) != expected:
        return False, "executive action queue is not sorted by priority/action_id"
    return True, "executive action queue exists with deterministic priorities"


def _quality_research_board_summary(packet: Mapping[str, Any]) -> tuple[bool, str]:
    board = packet.get("research_board")
    if not isinstance(board, list):
        research_lab = packet.get("research_lab")
        if isinstance(research_lab, Mapping):
            board = research_lab.get("research_board")
    missing = _missing_research_board_fields("research_board", board)
    if missing:
        return False, _quality_missing_summary(missing)
    assert isinstance(board, list)
    for item in board:
        if not isinstance(item, Mapping):
            continue
        candidate_name = str(item.get("candidate_name", ""))
        if (
            item.get("status") == "active_baseline"
            and "SPY SMA 50/200" in candidate_name
        ):
            return True, "SPY SMA 50/200 active_baseline is present"
    return False, "SPY SMA 50/200 active_baseline is missing"


def _missing_safety_labels(packet: Mapping[str, Any]) -> list[str]:
    labels = packet.get("safety_labels")
    if not isinstance(labels, list):
        return ["safety_labels"]
    return [label for label in _REQUIRED_LABELS if label not in labels]


def _missing_review_handoff_references(review_handoff_text: str) -> list[str]:
    if not review_handoff_text:
        return [_REVIEW_HANDOFF_FILENAME]
    required_tokens = [
        _BRIEF_FILENAME,
        _RECORD_FILENAME,
        _MANIFEST_FILENAME,
        _HISTORY_LEDGER_FILENAME,
        _REVIEW_HANDOFF_FILENAME,
        _DECISION_LEDGER_FILENAME,
        _REVIEW_INPUTS_DIRNAME,
    ]
    return [token for token in required_tokens if token not in review_handoff_text]


def _quality_decision_ledger_summary(
    output_root: Path,
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    status = str(packet.get("decision_ledger_status", ""))
    review_input_status = str(packet.get("review_input_status", ""))
    ledger_path = output_root / _DECISION_LEDGER_FILENAME
    ledger_exists = ledger_path.exists() and ledger_path.is_file()
    explicit_no_review = status in {
        "decision_ledger_no_review_input",
        "decision_ledger_existing_no_review_input",
    } and review_input_status in {
        "review_input_not_found",
        "review_input_directory_empty",
    }
    if ledger_exists:
        return True, f"decision ledger artifact exists; status={status}"
    if explicit_no_review:
        return True, f"explicit no-review status recorded; status={status}"
    return False, (
        "decision ledger missing without explicit no-review status; "
        f"status={status}; review_input_status={review_input_status}"
    )


def _quality_review_classification_summary(
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    classification = str(packet.get("review_classification", ""))
    allowed = set(_REVIEW_CLASSIFICATIONS) | set(_REVIEW_NON_INPUT_CLASSIFICATIONS)
    if classification in allowed:
        return True, f"review_classification={classification}"
    return False, f"review_classification={classification} is not normalized"


def _quality_review_input_hash_summary(
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    review_input_status = str(packet.get("review_input_status", ""))
    review_input_path = packet.get("review_input_path")
    review_input_sha256 = packet.get("review_input_sha256")
    if review_input_status != "review_input_ingested":
        return True, f"review_input_status={review_input_status}"
    if not _has_required_value(review_input_path):
        return False, "review_input_path missing for ingested review input"
    if not _sha256_text(review_input_sha256):
        return False, "review_input_sha256 missing or invalid"
    return True, f"review_input_path={review_input_path}"


def _quality_review_next_action_summary(
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    next_action = str(packet.get("review_selected_next_action", ""))
    if not next_action.strip():
        return False, "review_selected_next_action missing"
    if _contains_forbidden_review_next_action(next_action):
        return False, "review_selected_next_action includes forbidden broker term"
    return True, f"review_selected_next_action={next_action}"


def _sha256_text(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _review_handoff_path(packet: Mapping[str, Any], output_root: Path) -> str:
    artifact_paths = packet.get("artifact_paths")
    if isinstance(artifact_paths, Mapping) and _has_required_value(
        artifact_paths.get("review_handoff")
    ):
        return str(artifact_paths["review_handoff"])
    if _has_required_value(packet.get("review_handoff_path")):
        return str(packet["review_handoff_path"])
    return _normalize_path(output_root / _REVIEW_HANDOFF_FILENAME)


def _missing_packet_fields(packet: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    for field_name in _REQUIRED_PACKET_FIELDS:
        if field_name in _REQUIRED_FIELDS_ALLOW_EMPTY:
            if field_name not in packet or packet.get(field_name) is None:
                missing.append(field_name)
        elif not _has_required_value(packet.get(field_name)):
            missing.append(field_name)

    if (
        "assistant_packet_version" not in missing
        and packet.get("assistant_packet_version") != _ASSISTANT_PACKET_VERSION
    ):
        missing.append("assistant_packet_version")
    if not _paper_submit_not_authorized(packet):
        missing.append("paper_submit_authorized_false_or_not_authorized")
    if packet.get("broker_state_observed") is not False:
        missing.append("broker_state_observed_false")
    if packet.get("broker_state_mode") not in {
        "broker_state_not_observed",
        "offline_preview_only",
    }:
        missing.append("broker_state_mode_offline_or_not_observed")

    labels = packet.get("safety_labels")
    if not isinstance(labels, list) or not labels:
        if "safety_labels" not in missing:
            missing.append("safety_labels")
    else:
        for label in _REQUIRED_LABELS:
            if label not in labels:
                missing.append(f"safety_labels.{label}")
    missing.extend(
        _missing_history_delta_fields("history_delta", packet.get("history_delta"))
    )
    missing.extend(
        _missing_action_queue_fields(
            "executive_action_queue",
            packet.get("executive_action_queue"),
        )
    )
    missing.extend(
        _missing_research_board_fields(
            "research_board",
            packet.get("research_board"),
        )
    )
    research_lab = packet.get("research_lab")
    if isinstance(research_lab, Mapping):
        missing.extend(
            _missing_research_board_fields(
                "research_lab.research_board",
                research_lab.get("research_board"),
            )
        )
    else:
        missing.append("research_lab")
    missing.extend(_missing_review_decision_fields("", packet))
    return missing


def _missing_manifest_fields(
    output_root: Path,
    packet: Mapping[str, Any],
) -> list[str]:
    manifest, failures = _read_manifest_record(output_root / _MANIFEST_FILENAME)
    if manifest is None:
        return failures

    missing: list[str] = list(failures)
    for field_name in _REQUIRED_MANIFEST_FIELDS:
        if field_name == "missing_required_fields":
            if field_name not in manifest or not isinstance(
                manifest.get(field_name),
                list,
            ):
                missing.append(f"manifest.{field_name}")
        elif field_name in _REQUIRED_FIELDS_ALLOW_EMPTY:
            if field_name not in manifest or manifest.get(field_name) is None:
                missing.append(f"manifest.{field_name}")
        elif not _has_required_value(manifest.get(field_name)):
            missing.append(f"manifest.{field_name}")
    if not _paper_submit_not_authorized(manifest):
        missing.append("manifest.paper_submit_authorized_false_or_not_authorized")
    missing.extend(
        _missing_history_delta_fields(
            "manifest.history_delta",
            manifest.get("history_delta"),
        )
    )
    missing.extend(
        _missing_action_queue_fields(
            "manifest.executive_action_queue",
            manifest.get("executive_action_queue"),
        )
    )
    missing.extend(
        _missing_research_board_fields(
            "manifest.research_board",
            manifest.get("research_board"),
        )
    )
    missing.extend(_missing_review_decision_fields("manifest", manifest))

    for field_name in (
        "input_data_path",
        "as_of_date",
        "active_strategy_name",
        "posture",
        "sma_posture_status",
        "preview_decision",
        "blocker_status",
        "broker_state_mode",
        "next_operator_action",
        "assistant_packet_version",
        "history_ledger_path",
        "executive_action_queue_version",
        "executive_action_summary",
        "quality_gate_status",
        "quality_gate_score",
        "quality_gate_failed_checks",
        "quality_gate_warning_checks",
        "quality_gate_required_checks",
        "quality_gate_optional_checks",
        "review_handoff_path",
        "review_handoff_status",
        "decision_ledger_path",
        "decision_ledger_status",
        "decision_ledger_append_status",
        "decision_ledger_entry_count",
        "review_input_status",
        "review_input_count",
        "review_input_path",
        "review_input_sha256",
        "reviewer_source",
        "review_classification",
        "review_selected_next_action",
    ):
        if field_name in packet and manifest.get(field_name) != packet.get(field_name):
            missing.append(f"manifest.{field_name}.matches_record")

    if (
        isinstance(packet.get("history_delta"), Mapping)
        and isinstance(manifest.get("history_delta"), Mapping)
        and dict(manifest["history_delta"]) != dict(packet["history_delta"])
    ):
        missing.append("manifest.history_delta.matches_record")

    if (
        isinstance(packet.get("executive_action_queue"), list)
        and isinstance(manifest.get("executive_action_queue"), list)
        and list(manifest["executive_action_queue"])
        != list(packet["executive_action_queue"])
    ):
        missing.append("manifest.executive_action_queue.matches_record")

    return missing


def _missing_review_decision_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    classification = str(packet.get("review_classification", ""))
    allowed_classifications = set(_REVIEW_CLASSIFICATIONS) | set(
        _REVIEW_NON_INPUT_CLASSIFICATIONS
    )
    if classification not in allowed_classifications:
        missing.append(f"{field_prefix}review_classification.allowed")
    if not isinstance(packet.get("decision_ledger_entry_count"), int):
        missing.append(f"{field_prefix}decision_ledger_entry_count.int")
    selected_next_action = str(packet.get("review_selected_next_action", ""))
    if not selected_next_action.strip():
        missing.append(f"{field_prefix}review_selected_next_action")
    elif _contains_forbidden_review_next_action(selected_next_action):
        missing.append(f"{field_prefix}review_selected_next_action.safe")
    if packet.get("review_input_status") == "review_input_ingested":
        if not _has_required_value(packet.get("review_input_path")):
            missing.append(f"{field_prefix}review_input_path")
        if not _sha256_text(packet.get("review_input_sha256")):
            missing.append(f"{field_prefix}review_input_sha256")
    return missing


def _missing_history_delta_fields(prefix: str, delta: Any) -> list[str]:
    if not isinstance(delta, Mapping):
        return [prefix]

    missing: list[str] = []
    for field_name in _REQUIRED_DELTA_FIELDS:
        if field_name not in delta:
            missing.append(f"{prefix}.{field_name}")

    summary_text = delta.get("delta_summary_text")
    if not isinstance(summary_text, str) or not summary_text.strip():
        if f"{prefix}.delta_summary_text" not in missing:
            missing.append(f"{prefix}.delta_summary_text")
    return missing


def _missing_action_queue_fields(prefix: str, action_queue: Any) -> list[str]:
    if not isinstance(action_queue, list) or not action_queue:
        return [prefix]

    missing: list[str] = []
    for index, item in enumerate(action_queue):
        item_prefix = f"{prefix}[{index}]"
        if not isinstance(item, Mapping):
            missing.append(item_prefix)
            continue
        for field_name in _REQUIRED_ACTION_QUEUE_FIELDS:
            if field_name not in item:
                missing.append(f"{item_prefix}.{field_name}")
        priority = item.get("priority")
        if priority not in _ACTION_PRIORITIES:
            missing.append(f"{item_prefix}.priority.allowed")
        action_type = item.get("action_type")
        if action_type not in _ACTION_TYPES:
            missing.append(f"{item_prefix}.action_type.allowed")
        for list_field in ("reason_codes", "blocked_by"):
            if list_field in item and not isinstance(item.get(list_field), list):
                missing.append(f"{item_prefix}.{list_field}.list")
        for bool_field in ("requires_daniel", "hard_gate_required"):
            if bool_field in item and not isinstance(item.get(bool_field), bool):
                missing.append(f"{item_prefix}.{bool_field}.bool")
    return missing


def _missing_research_board_fields(prefix: str, research_board: Any) -> list[str]:
    if not isinstance(research_board, list) or not research_board:
        return [prefix]

    missing: list[str] = []
    active_baseline_found = False
    for index, item in enumerate(research_board):
        item_prefix = f"{prefix}[{index}]"
        if not isinstance(item, Mapping):
            missing.append(item_prefix)
            continue
        for field_name in _REQUIRED_RESEARCH_BOARD_FIELDS:
            if field_name not in item:
                missing.append(f"{item_prefix}.{field_name}")
        if item.get("status") not in _RESEARCH_BOARD_STATUSES:
            missing.append(f"{item_prefix}.status.allowed")
        if item.get("status") == "active_baseline":
            active_baseline_found = True
        for list_field in ("missing_evidence", "promotion_blockers", "notes"):
            if list_field in item and not isinstance(item.get(list_field), list):
                missing.append(f"{item_prefix}.{list_field}.list")
    if not active_baseline_found:
        missing.append(f"{prefix}.active_baseline")
    return missing


def _missing_brief_references(
    output_root: Path,
    packet: Mapping[str, Any],
) -> list[str]:
    brief_path = output_root / _BRIEF_FILENAME
    if not brief_path.exists():
        return []
    try:
        brief_text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return ["operating_brief.readable"]

    missing: list[str] = []
    for field_name in _BRIEF_REQUIRED_VALUE_FIELDS:
        value = packet.get(field_name)
        if _has_required_value(value) and str(value) not in brief_text:
            missing.append(f"operating_brief.{field_name}")

    if (
        "paper_submit_authorized=false" not in brief_text
        and "not_authorized" not in brief_text
    ):
        missing.append("operating_brief.paper_submit_authorized_false_or_not_authorized")
    for label in _REQUIRED_LABELS:
        if label not in brief_text:
            missing.append(f"operating_brief.safety_labels.{label}")
    if "## Executive Action Queue" not in brief_text:
        missing.append("operating_brief.executive_action_queue.section")
    action_queue = packet.get("executive_action_queue")
    if isinstance(action_queue, list):
        for item in action_queue:
            if isinstance(item, Mapping):
                action_id = str(item.get("action_id", ""))
                if action_id and action_id not in brief_text:
                    missing.append(
                        f"operating_brief.executive_action_queue.{action_id}"
                    )
    if "## Research Board" not in brief_text:
        missing.append("operating_brief.research_board.section")
    if "Quality Gate" not in brief_text:
        missing.append("operating_brief.quality_gate")
    if "Decision Ledger" not in brief_text:
        missing.append("operating_brief.decision_ledger")
    review_handoff_path = packet.get("review_handoff_path")
    if (
        _has_required_value(review_handoff_path)
        and str(review_handoff_path) not in brief_text
    ):
        missing.append("operating_brief.review_handoff_path")
    decision_ledger_path = packet.get("decision_ledger_path")
    if (
        _has_required_value(decision_ledger_path)
        and str(decision_ledger_path) not in brief_text
    ):
        missing.append("operating_brief.decision_ledger_path")
    research_board = packet.get("research_board")
    if isinstance(research_board, list):
        for item in research_board:
            if isinstance(item, Mapping):
                candidate_name = str(item.get("candidate_name", ""))
                if candidate_name and candidate_name not in brief_text:
                    missing.append(
                        f"operating_brief.research_board.{candidate_name}"
                    )
    delta = packet.get("history_delta")
    if isinstance(delta, Mapping):
        delta_summary = delta.get("delta_summary_text")
        if (
            isinstance(delta_summary, str)
            and delta_summary.strip()
            and delta_summary not in brief_text
        ):
            missing.append("operating_brief.history_delta.delta_summary_text")
    return missing


def _has_required_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _paper_submit_not_authorized(packet: Mapping[str, Any]) -> bool:
    status = str(packet.get("paper_submit_authorization_status", "")).strip()
    return packet.get("paper_submit_authorized") is False or status in _NOT_AUTHORIZED_STATUSES


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    return value


def _preview_decision(posture: str) -> str:
    if posture == "insufficient_history":
        return "insufficient_history"
    if posture == "bullish_risk_on":
        return "offline_preview_bullish_risk_on"
    return "offline_preview_defensive_risk_off"


def _next_operator_action(posture: str, slow_window: int) -> str:
    if posture == "insufficient_history":
        return f"provide_at_least_{slow_window}_usable_daily_bars_before_preview_use"
    return "review_assistant_brief_no_broker_action"


def _current_recommendation(posture: str) -> str:
    if posture == "insufficient_history":
        return (
            "Do not submit orders. The SMA preview is blocked until enough "
            "daily bars are available."
        )
    return (
        "Treat this as an offline research preview only. Do not submit paper or "
        "live orders from this packet."
    )


def _sma_status(
    *,
    posture: str,
    fast_window: int,
    slow_window: int,
    usable_bar_count: int,
) -> str:
    if posture == "insufficient_history":
        return (
            f"insufficient_history: {usable_bar_count} usable bars is fewer than "
            f"the {slow_window}-bar slow SMA requirement"
        )
    if posture == "bullish_risk_on":
        return f"risk_on: SMA{fast_window} is above SMA{slow_window}"
    return f"risk_off: SMA{fast_window} is at or below SMA{slow_window}"


def _data_freshness(*, as_of_date: str, latest_input_bar_date: str) -> dict[str, Any]:
    if as_of_date == latest_input_bar_date:
        status = "as_of_matches_latest_input_bar"
    elif as_of_date < latest_input_bar_date:
        status = "as_of_before_latest_input_bar"
    else:
        status = "as_of_after_latest_input_bar"
    return {
        "status": status,
        "as_of_date": as_of_date,
        "latest_input_bar_date": latest_input_bar_date,
        "freshness_basis": "input_csv_latest_bar_only",
        "wall_clock_staleness": "not_evaluated_by_offline_command",
    }


def _research_lab(
    *,
    config: EtfSmaDailyPaperLabConfig,
    as_of_date: str,
    posture: str,
    sma_status: str,
    sma_fast_value: str | None,
    sma_slow_value: str | None,
) -> dict[str, Any]:
    fast_value = sma_fast_value if sma_fast_value is not None else "not_available"
    slow_value = sma_slow_value if sma_slow_value is not None else "not_available"
    active_evidence = [
        f"{config.symbol} daily bars loaded from {_normalize_path(config.bars_csv)}",
        (
            f"SMA {config.sma_fast_window}/{config.sma_slow_window} evaluated "
            f"as of {as_of_date}"
        ),
        f"posture={posture}",
        f"sma_status={sma_status}",
        f"sma_fast_value={fast_value}",
        f"sma_slow_value={slow_value}",
    ]
    board = [
        {
            "candidate_name": "SPY SMA 50/200 daily long-only baseline",
            "status": "active_baseline",
            "hypothesis": (
                "SPY risk posture is risk-on when SMA50 is above SMA200 and "
                "risk-off when SMA50 is at or below SMA200."
            ),
            "evidence_status": "daily_sma_signal_evaluated_from_offline_csv",
            "confidence_status": "confidence_not_yet_quantified",
            "missing_evidence": [
                "offline_backtest_confidence_summary",
                "drawdown_and_turnover_review",
                "paper_fill_reconciliation_not_observed",
            ],
            "next_research_action": (
                "quantify_baseline_confidence_with_offline_research_packet"
            ),
            "promotion_blockers": [
                "strategy_confidence_not_yet_quantified",
                "broker_state_not_observed",
                "paper_submit_not_authorized",
            ],
            "safety_scope": "offline_research_only_no_broker_access_no_submit",
            "notes": [
                "This is the only active strategy path for this milestone.",
                "Current posture evidence is reported outside the board fingerprint.",
            ],
        },
        {
            "candidate_name": "future_candidate_strategy_slot",
            "status": "blocked",
            "hypothesis": (
                "No alternate strategy hypothesis is approved in this milestone; "
                "this slot exists only to route future GPT/operator research."
            ),
            "evidence_status": "no_candidate_defined",
            "confidence_status": "not_applicable_until_candidate_defined",
            "missing_evidence": [
                "operator_and_GPT_approved_candidate_definition",
                "offline_backtest_or_replay_evidence",
                "dependency_direction_and_safety_review",
                "paper_lab_only_promotion_packet",
            ],
            "next_research_action": (
                "wait_for_GPT_approved_candidate_definition_before_any_strategy_code"
            ),
            "promotion_blockers": [
                "no_candidate_strategy_selected",
                "no_offline_evidence_collected",
                "no_approval_to_expand_strategy_catalog",
            ],
            "safety_scope": "metadata_only_no_new_strategy_no_broker_access",
            "notes": [
                "Do not implement or backtest new strategies in Assistant v1.3.",
            ],
        },
    ]
    return {
        "research_board_version": _RESEARCH_BOARD_VERSION,
        "active_strategy_evidence": active_evidence,
        "research_board": board,
        "candidate_strategy_board": board,
        "confidence_status": "confidence_not_yet_quantified",
        "missing_evidence": [
            "broker_state_not_observed",
            "multi_day_assistant_packet_history_not_yet_accumulated",
            "strategy_confidence_not_yet_quantified",
        ],
        "next_research_action": "accumulate_daily_assistant_packets_after_input_data_refresh",
    }


def _plain_english_status(payload: Mapping[str, Any]) -> str:
    fast_window = payload["sma_fast_window"]
    slow_window = payload["sma_slow_window"]
    as_of_date = payload["as_of_date"]
    posture = payload["posture"]
    if posture == "bullish_risk_on":
        return (
            f"As of {as_of_date}, SPY is risk-on under the SMA "
            f"{fast_window}/{slow_window} test."
        )
    if posture == "defensive_risk_off":
        return (
            f"As of {as_of_date}, SPY is risk-off under the SMA "
            f"{fast_window}/{slow_window} test."
        )
    return (
        f"As of {as_of_date}, the SMA {fast_window}/{slow_window} test has "
        "insufficient usable history."
    )


def _daniel_action_required(posture: str) -> str:
    if posture == "insufficient_history":
        return "Yes: provide enough daily input bars before relying on the preview."
    return (
        "No broker action is required. Daniel can review the packet and refresh "
        "input data outside this command when needed."
    )


def _render_brief_markdown(payload: dict[str, Any]) -> str:
    labels_list = "\n".join(f"* `{label}`" for label in payload["safety_labels"])
    artifact_lines = "\n".join(
        f"* **{name}**: `{path}`"
        for name, path in payload["artifact_paths"].items()
    )
    evidence_lines = "\n".join(
        f"* {item}" for item in payload["research_lab"]["active_strategy_evidence"]
    )
    missing_evidence_lines = "\n".join(
        f"* {item}" for item in payload["research_lab"]["missing_evidence"]
    )
    action_lines = _render_executive_action_queue(payload["executive_action_queue"])
    research_board_lines = _render_research_board(
        payload["research_lab"]["research_board"]
    )
    freshness = payload["data_freshness"]
    delta = payload["history_delta"]
    missing_required_fields = payload["missing_required_fields"]
    missing_required_fields_text = (
        "[]" if not missing_required_fields else ", ".join(missing_required_fields)
    )
    failed_checks = payload["quality_gate_failed_checks"]
    failed_checks_text = "[]" if not failed_checks else ", ".join(failed_checks)
    warning_checks = payload["quality_gate_warning_checks"]
    warning_checks_text = "[]" if not warning_checks else ", ".join(warning_checks)
    review_blockers = payload.get("review_blockers", [])
    review_blockers_text = (
        "[]" if not review_blockers else ", ".join(str(item) for item in review_blockers)
    )
    review_repair_items = payload.get("review_repair_items", [])
    review_repair_items_text = (
        "[]"
        if not review_repair_items
        else ", ".join(str(item) for item in review_repair_items)
    )

    return f"""# Daily Trading Research Command Center

## Executive summary
* **Recommendation**: {payload["current_recommendation"]}
* **Evidence**: {payload["executive_summary"]["plain_english_status"]} Preview decision: `{payload["preview_decision"]}`.
* **Risks / blockers**: {payload["blocker_status"]}. {payload["broker_state_claim"]} Paper submit authorization is `{payload["paper_submit_authorization_status"]}` (`paper_submit_authorized=false`).
* **Delta since prior packet**: {delta["delta_summary_text"]}
* **Review decision**: classification `{payload["review_classification"]}`; ledger status `{payload["decision_ledger_status"]}`; append status `{payload["decision_ledger_append_status"]}`.
* **Daniel action**: {payload["executive_summary"]["daniel_action_required"]}
* **Quality Gate**: `{payload["quality_gate_status"]}` ({payload["quality_gate_score"]}); review handoff: `{payload["review_handoff_path"]}`.

## Executive Action Queue
* **Daniel action required now**: {str(payload["executive_action_summary"]["daniel_action_required"]).lower()}
* **Highest priority**: {payload["executive_action_summary"]["highest_priority"]}
{action_lines}

## Trading desk brief
* **Active strategy**: {payload["active_strategy_name"]}
* **Market/posture state**: {payload["sma_posture_status"]}
* **Preview decision**: {payload["preview_decision"]}
* **Blocker status**: {payload["blocker_status"]}
* **Paper submit authorization status**: {payload["paper_submit_authorization_status"]} (`paper_submit_authorized=false`)
* **Broker-state mode**: {payload["broker_state_mode"]}
* **As-of date**: {payload["as_of_date"]}
* **Input data path**: `{payload["input_data_path"]}`

## Research Board
* **Active strategy evidence**:
{evidence_lines}
* **Board status**:
{research_board_lines}
* **Confidence status**: {payload["research_lab"]["confidence_status"]}
* **Missing evidence**:
{missing_evidence_lines}
* **Next research action**: {payload["research_lab"]["next_research_action"]}

## Executive dashboard
* **Data freshness**: {freshness["status"]} (latest input bar: {freshness["latest_input_bar_date"]}; basis: {freshness["freshness_basis"]}; wall-clock staleness: {freshness["wall_clock_staleness"]})
* **Validation status**: {payload["validation_status"]}
* **Quality Gate**: `{payload["quality_gate_status"]}` ({payload["quality_gate_score"]})
* **Quality gate failed checks**: {failed_checks_text}
* **Quality gate warning checks**: {warning_checks_text}
* **Review handoff path**: `{payload["review_handoff_path"]}` (status: `{payload["review_handoff_status"]}`)
* **Decision Ledger**: `{payload["decision_ledger_status"]}` at `{payload["decision_ledger_path"]}`; append status `{payload["decision_ledger_append_status"]}`; entries: {payload["decision_ledger_entry_count"]}
* **Review input**: `{payload["review_input_status"]}`; path `{payload["review_input_path"]}`; hash `{payload["review_input_sha256"]}`; reviewer `{payload["reviewer_source"]}`
* **Review classification**: `{payload["review_classification"]}`; blockers: {review_blockers_text}; repair items: {review_repair_items_text}; selected next action: `{payload["review_selected_next_action"]}`
* **Assistant packet version**: {payload["assistant_packet_version"]}
* **Previous packet found**: {str(delta["previous_packet_found"]).lower()}
* **History ledger path**: `{payload["history_ledger_path"]}`
* **Missing required fields**: {missing_required_fields_text}
* **Artifact presence status**: {payload["artifact_presence_status"]["status"]}
* **Artifact paths**:
{artifact_lines}
* **System health**: {payload["system_health"]}
* **Safety labels**:
{labels_list}
* **Next operator action**: {payload["next_operator_action"]}
"""


def _render_review_handoff_markdown(payload: Mapping[str, Any]) -> str:
    artifact_lines = _render_generated_artifacts(payload)
    action_lines = _render_review_action_queue(payload["executive_action_queue"])
    research_lines = _render_review_research_board(payload["research_board"])
    delta = payload["history_delta"]
    failed_checks_text = json.dumps(
        list(payload["quality_gate_failed_checks"]),
        sort_keys=True,
        separators=(",", ":"),
    )
    warning_checks_text = json.dumps(
        list(payload["quality_gate_warning_checks"]),
        sort_keys=True,
        separators=(",", ":"),
    )
    review_blockers_text = json.dumps(
        list(payload.get("review_blockers", [])),
        sort_keys=True,
        separators=(",", ":"),
    )
    review_repair_items_text = json.dumps(
        list(payload.get("review_repair_items", [])),
        sort_keys=True,
        separators=(",", ":"),
    )
    review_minor_notes_text = json.dumps(
        list(payload.get("review_minor_notes", [])),
        sort_keys=True,
        separators=(",", ":"),
    )
    meaningful_changes_text = _history_meaningful_changes_text(delta)

    return f"""# Daily Packet Review Handoff

## Classification request
Please classify this packet as one of: `accepted`, `accepted-with-minor-note`, `needs-repair`, or `rejected`.

## Packet identity
* **assistant_packet_version**: `{payload["assistant_packet_version"]}`
* **review_handoff_version**: `{payload["review_handoff_version"]}`
* **as_of_date**: `{payload["as_of_date"]}`
* **active_strategy_name**: {payload["active_strategy_name"]}
* **output_root**: `{_review_output_root(payload)}`
* **generated artifacts**:
{artifact_lines}

## Executive summary
* **What is happening**: {payload["executive_summary"]["plain_english_status"]}
* **What the system thinks**: {payload["current_recommendation"]}
* **Daniel action**: {payload["executive_summary"]["daniel_action_required"]}

## Trading desk state
* **Posture/status**: `{payload["posture"]}`; {payload["sma_posture_status"]}
* **Preview decision**: `{payload["preview_decision"]}`
* **Blocker status**: `{payload["blocker_status"]}`
* **Broker-state mode**: `{payload["broker_state_mode"]}`
* **Paper submit authorization status**: `{payload["paper_submit_authorization_status"]}` (`paper_submit_authorized=false`)

## Quality gate result
* **quality_gate_status**: `{payload["quality_gate_status"]}`
* **quality_gate_score**: {payload["quality_gate_score"]}
* **failed_checks**: `{failed_checks_text}`
* **warning_checks**: `{warning_checks_text}`
* **required_fields_present**: {str(payload["quality_gate_required_fields_present"]).lower()}

## Decision ledger
* **decision_ledger_version**: `{payload["decision_ledger_version"]}`
* **decision_ledger_status**: `{payload["decision_ledger_status"]}`
* **decision_ledger_append_status**: `{payload["decision_ledger_append_status"]}`
* **decision_ledger_path**: `{payload["decision_ledger_path"]}`
* **decision_ledger_entry_count**: {payload["decision_ledger_entry_count"]}
* **review_inputs_path**: `{payload["review_inputs_path"]}`
* **review_input_status**: `{payload["review_input_status"]}`
* **review_input_path**: `{payload["review_input_path"]}`
* **review_input_sha256**: `{payload["review_input_sha256"]}`
* **reviewer_source**: `{payload["reviewer_source"]}`
* **review_classification**: `{payload["review_classification"]}`
* **review_blockers**: `{review_blockers_text}`
* **review_repair_items**: `{review_repair_items_text}`
* **review_minor_notes**: `{review_minor_notes_text}`
* **review_selected_next_action**: `{payload["review_selected_next_action"]}`

## Executive action queue
{action_lines}

## Research board
{research_lines}

## History delta
* **previous_packet_found**: {str(delta["previous_packet_found"]).lower()}
* **meaningful changes**: {meaningful_changes_text}
* **delta_summary_text**: {delta["delta_summary_text"]}

## Safety assessment
* No broker reads were performed by this command.
* No broker mutation was performed.
* No paper submit was performed.
* No live trading was performed.
* No network calls were performed.
* Broker state remains `{payload["broker_state_mode"]}`; this packet is `offline_preview_only` review material.

## Reviewer instructions
* **Verify**: required artifacts, quality gate result, validation status, action queue priority order, active SPY SMA 50/200 baseline, history delta, decision ledger status, safety labels, and broker-state wording.
* **Blocker**: any quality gate failure, missing required artifact, missing required field, paper submit authorization, broker observation claim, broker mutation evidence, live-trading evidence, or network dependency.
* **Return format**:
  * `classification: accepted|accepted-with-minor-note|needs-repair|rejected`
  * `blocking_findings: <none or concise bullets>`
  * `minor_notes: <none or concise bullets>`
  * `recommended_next_action: <one sentence>`
"""


def _render_generated_artifacts(payload: Mapping[str, Any]) -> str:
    artifact_paths = payload.get("artifact_paths")
    if not isinstance(artifact_paths, Mapping):
        artifact_paths = {}
    ordered_artifacts = [
        ("operating_brief", artifact_paths.get("assistant_brief")),
        ("operating_record", artifact_paths.get("operating_record")),
        ("manifest", artifact_paths.get("manifest")),
        ("history_ledger", artifact_paths.get("history_ledger")),
        ("review_handoff", artifact_paths.get("review_handoff")),
        ("decision_ledger", artifact_paths.get("decision_ledger")),
        ("review_inputs", artifact_paths.get("review_inputs")),
    ]
    return "\n".join(
        f"* **{name}**: `{path}`"
        for name, path in ordered_artifacts
        if _has_required_value(path)
    )


def _render_review_action_queue(action_queue: Any) -> str:
    if not isinstance(action_queue, list) or not action_queue:
        return "* No executive actions are present."
    lines = [
        "| action_id | priority | action_type | title | requires_daniel | hard_gate_required | reason_codes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in action_queue:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"`{item['action_id']}` | "
            f"`{item['priority']}` | "
            f"`{item['action_type']}` | "
            f"{item['title']} | "
            f"{str(item['requires_daniel']).lower()} | "
            f"{str(item['hard_gate_required']).lower()} | "
            f"{', '.join(item['reason_codes'])} |"
        )
    return "\n".join(lines)


def _render_review_research_board(research_board: Any) -> str:
    if not isinstance(research_board, list) or not research_board:
        return "* Research board is missing."
    active_baseline = _active_baseline_name(research_board)
    lines = [
        f"* **Active baseline**: {active_baseline}",
        "| entry | status | confidence status | missing evidence | next research action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in research_board:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"`{item['candidate_name']}` | "
            f"`{item['status']}` | "
            f"`{item['confidence_status']}` | "
            f"{', '.join(item['missing_evidence'])} | "
            f"{item['next_research_action']} |"
        )
    return "\n".join(lines)


def _active_baseline_name(research_board: list[Any]) -> str:
    for item in research_board:
        if isinstance(item, Mapping) and item.get("status") == "active_baseline":
            return str(item.get("candidate_name", "active_baseline_name_missing"))
    return "active_baseline_missing"


def _history_meaningful_changes_text(delta: Mapping[str, Any]) -> str:
    changed_fields = [
        field_name
        for field_name in (
            "posture_changed",
            "preview_decision_changed",
            "blocker_status_changed",
            "validation_status_changed",
            "broker_state_mode_changed",
            "research_board_changed",
            "next_operator_action_changed",
        )
        if bool(delta.get(field_name))
    ]
    if not changed_fields:
        return "none"
    return ", ".join(changed_fields)


def _review_output_root(payload: Mapping[str, Any]) -> str:
    review_handoff_path = str(payload["review_handoff_path"])
    suffix = "/" + _REVIEW_HANDOFF_FILENAME
    if review_handoff_path.endswith(suffix):
        return review_handoff_path[: -len(suffix)]
    if review_handoff_path.endswith("\\" + _REVIEW_HANDOFF_FILENAME):
        return review_handoff_path[: -(len(_REVIEW_HANDOFF_FILENAME) + 1)]
    return str(Path(review_handoff_path).parent)


def _render_executive_action_queue(action_queue: list[Mapping[str, Any]]) -> str:
    if not action_queue:
        return "* No executive actions are present."
    lines = [
        "| Action | Priority | Type | Requires Daniel | Hard gate | Reason codes | Expected artifact or command | Safety scope |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in action_queue:
        lines.append(
            "| "
            f"`{item['action_id']}` | "
            f"`{item['priority']}` | "
            f"`{item['action_type']}` | "
            f"{str(item['requires_daniel']).lower()} | "
            f"{str(item['hard_gate_required']).lower()} | "
            f"{', '.join(item['reason_codes'])} | "
            f"{item['expected_artifact_or_command']} | "
            f"{item['safety_scope']} |"
        )
    return "\n".join(lines)


def _render_research_board(candidate_board: list[Mapping[str, Any]]) -> str:
    if not candidate_board:
        return "* No research board entries are present."
    lines = [
        "| Candidate | Status | Evidence | Confidence | Missing evidence | Next research action | Promotion blockers | Safety scope |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in candidate_board:
        lines.append(
            "| "
            f"`{item['candidate_name']}` | "
            f"`{item['status']}` | "
            f"{item['evidence_status']} | "
            f"{item['confidence_status']} | "
            f"{', '.join(item['missing_evidence'])} | "
            f"{item['next_research_action']} | "
            f"{', '.join(item['promotion_blockers'])} | "
            f"{item['safety_scope']} |"
        )
    return "\n".join(lines)


def _render_candidate_strategy_board(candidate_board: list[Mapping[str, Any]]) -> str:
    return _render_research_board(candidate_board)


def _build_manifest(output_root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    indexed_artifacts = {
        "assistant_brief": _artifact_metadata(output_root / _BRIEF_FILENAME),
        "operating_record": _artifact_metadata(output_root / _RECORD_FILENAME),
        "review_handoff": _artifact_metadata(output_root / _REVIEW_HANDOFF_FILENAME),
    }
    history_ledger_path = output_root / _HISTORY_LEDGER_FILENAME
    if history_ledger_path.exists():
        indexed_artifacts["history_ledger"] = _artifact_metadata(history_ledger_path)
    decision_ledger_path = output_root / _DECISION_LEDGER_FILENAME
    if decision_ledger_path.exists():
        indexed_artifacts["decision_ledger"] = _artifact_metadata(
            decision_ledger_path
        )
    history_delta = dict(payload["history_delta"])
    return {
        "schema_version": _SCHEMA_VERSION,
        "assistant_version": _ASSISTANT_VERSION,
        "assistant_packet_version": payload["assistant_packet_version"],
        "manifest_type": "daily_trading_research_command_center_index",
        "command": _COMMAND,
        "script": _SCRIPT,
        "run_id": payload["run_id"],
        "as_of_date": payload["as_of_date"],
        "active_strategy_name": payload["active_strategy_name"],
        "input_data_path": payload["input_data_path"],
        "input_data_sha256": payload["input_data_sha256"],
        "posture": payload["posture"],
        "sma_posture_status": payload["sma_posture_status"],
        "preview_decision": payload["preview_decision"],
        "blocker_status": payload["blocker_status"],
        "broker_state_mode": payload["broker_state_mode"],
        "paper_submit_authorized": False,
        "paper_submit_authorization_status": "not_authorized",
        "next_operator_action": payload["next_operator_action"],
        "safety_labels": list(_REQUIRED_LABELS),
        "validation_status": payload["validation_status"],
        "missing_required_fields": list(payload["missing_required_fields"]),
        "artifact_presence_status": dict(payload["artifact_presence_status"]),
        "artifact_paths": dict(payload["artifact_paths"]),
        "history_ledger_path": payload["history_ledger_path"],
        "history_delta": history_delta,
        "executive_action_queue_version": payload["executive_action_queue_version"],
        "executive_action_queue": list(payload["executive_action_queue"]),
        "executive_action_summary": dict(payload["executive_action_summary"]),
        "research_board_version": payload["research_lab"]["research_board_version"],
        "research_board": list(payload["research_lab"]["research_board"]),
        "quality_gate_version": payload["quality_gate_version"],
        "quality_gate_status": payload["quality_gate_status"],
        "quality_gate_score": payload["quality_gate_score"],
        "quality_gate_passed_required_count": payload[
            "quality_gate_passed_required_count"
        ],
        "quality_gate_failed_required_count": payload[
            "quality_gate_failed_required_count"
        ],
        "quality_gate_warning_count": payload["quality_gate_warning_count"],
        "quality_gate_required_fields_present": payload[
            "quality_gate_required_fields_present"
        ],
        "quality_gate_failed_checks": list(payload["quality_gate_failed_checks"]),
        "quality_gate_warning_checks": list(payload["quality_gate_warning_checks"]),
        "quality_gate_required_checks": list(payload["quality_gate_required_checks"]),
        "quality_gate_optional_checks": list(payload["quality_gate_optional_checks"]),
        "review_handoff_version": payload["review_handoff_version"],
        "review_handoff_path": payload["review_handoff_path"],
        "review_handoff_status": payload["review_handoff_status"],
        "decision_ledger_version": payload["decision_ledger_version"],
        "decision_ledger_path": payload["decision_ledger_path"],
        "decision_ledger_status": payload["decision_ledger_status"],
        "decision_ledger_append_status": payload["decision_ledger_append_status"],
        "decision_ledger_entry_count": payload["decision_ledger_entry_count"],
        "decision_ledger_latest_entry": dict(
            payload.get("decision_ledger_latest_entry", {})
        ),
        "review_inputs_path": payload["review_inputs_path"],
        "review_input_status": payload["review_input_status"],
        "review_input_count": payload["review_input_count"],
        "review_input_paths": list(payload["review_input_paths"]),
        "review_input_path": payload["review_input_path"],
        "review_input_sha256": payload["review_input_sha256"],
        "reviewer_source": payload["reviewer_source"],
        "review_classification": payload["review_classification"],
        "review_classification_raw": payload["review_classification_raw"],
        "review_blockers": list(payload["review_blockers"]),
        "review_repair_items": list(payload["review_repair_items"]),
        "review_minor_notes": list(payload["review_minor_notes"]),
        "review_selected_next_action": payload["review_selected_next_action"],
        "review_decision": dict(payload["review_decision"]),
        "previous_packet_found": history_delta["previous_packet_found"],
        "previous_as_of_date": history_delta["previous_as_of_date"],
        "current_as_of_date": history_delta["current_as_of_date"],
        "posture_changed": history_delta["posture_changed"],
        "preview_decision_changed": history_delta["preview_decision_changed"],
        "blocker_status_changed": history_delta["blocker_status_changed"],
        "validation_status_changed": history_delta["validation_status_changed"],
        "broker_state_mode_changed": history_delta["broker_state_mode_changed"],
        "research_board_changed": history_delta["research_board_changed"],
        "next_operator_action_changed": history_delta[
            "next_operator_action_changed"
        ],
        "delta_summary_text": history_delta["delta_summary_text"],
        "indexed_artifacts": indexed_artifacts,
    }


def _artifact_metadata(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "path": _normalize_path(path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
