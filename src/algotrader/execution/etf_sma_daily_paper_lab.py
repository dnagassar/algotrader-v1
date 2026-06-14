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
_NEXT_ACTION_SELECTOR_VERSION = "assistant_v1.6_next_action_selector"
_WORK_ORDER_EXPORTS_VERSION = "assistant_v1.6_work_order_exports"
_RESEARCH_CANDIDATE_QUEUE_VERSION = "assistant_v1.7_research_candidate_queue"
_BASELINE_HEALTH_EVALUATION_VERSION = "assistant_v1.8_baseline_health_evaluation"
_BASELINE_EVIDENCE_METRICS_VERSION = "assistant_v1.9_baseline_evidence_metrics"
_PAPER_OBSERVATION_READINESS_VERSION = (
    "assistant_v1.12_paper_observation_readiness"
)
_RESEARCH_BOARD_PRIORITIZATION_VERSION = (
    "assistant_v1.13_research_board_prioritization"
)
_PHASE_NAME = "Assistant v1.13A - Minimal Research Board Prioritization Artifact"
_PHASE_GOAL = (
    "Add the minimal deterministic offline prioritization object "
    "research_board_prioritization while preserving all offline safety lockouts."
)
_PACKET_TYPE = "daily_trading_research_command_center"
_COMMAND = "etf-sma-daily-paper-lab"
_SCRIPT = "scripts/run_daily_paper_lab.ps1"
_BASELINE_HEALTH_NEXT_SAFE_TEST = (
    "python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py "
    "-k baseline_health_evaluation"
)
_BRIEF_FILENAME = "operating_brief.md"
_RECORD_FILENAME = "operating_record.jsonl"
_MANIFEST_FILENAME = "manifest.jsonl"
_HISTORY_LEDGER_FILENAME = "history_ledger.jsonl"
_REVIEW_HANDOFF_FILENAME = "review_handoff.md"
_DECISION_LEDGER_FILENAME = "decision_ledger.jsonl"
_RESEARCH_CANDIDATE_QUEUE_FILENAME = "research_candidate_queue.jsonl"
_BASELINE_HEALTH_EVALUATION_FILENAME = "baseline_health_evaluation.jsonl"
_BASELINE_EVIDENCE_METRICS_FILENAME = "baseline_evidence_metrics.jsonl"
_PAPER_OBSERVATION_READINESS_FILENAME = "paper_observation_readiness.jsonl"
_RESEARCH_BOARD_PRIORITIZATION_FILENAME = "research_board_prioritization.jsonl"
_PAPER_OBSERVATION_APPROVAL_PHRASE = (
    "Daniel approves read-only paper observation for SPY paper lab: "
    "account/clock/status, SPY position, SPY open orders, and latest paper "
    "portfolio snapshot only; no submit/cancel/replace/close/liquidate/delete/"
    "retry mutation/live trading."
)
_BASELINE_METRIC_MATERIALIZATION_FILENAME = (
    "baseline_authorized_adjusted_metrics.jsonl"
)
_BASELINE_BACKTEST_CONFIDENCE_SUMMARY_FILENAME = (
    "offline_backtest_confidence_summary.jsonl"
)
_BASELINE_ADJUSTED_CLOSE_EVIDENCE_FILENAME = "adjusted_close_evidence.jsonl"
_BASELINE_TURNOVER_SUMMARY_FILENAME = "turnover_summary.jsonl"
_BASELINE_COST_MODEL_SUMMARY_FILENAME = "cost_model_summary.jsonl"
_BASELINE_METRIC_ARTIFACTS = (
    (
        "baseline_authorized_adjusted_metrics",
        _BASELINE_METRIC_MATERIALIZATION_FILENAME,
    ),
    (
        "offline_backtest_confidence_summary",
        _BASELINE_BACKTEST_CONFIDENCE_SUMMARY_FILENAME,
    ),
    ("adjusted_close_evidence", _BASELINE_ADJUSTED_CLOSE_EVIDENCE_FILENAME),
    ("turnover_summary", _BASELINE_TURNOVER_SUMMARY_FILENAME),
    ("cost_model_summary", _BASELINE_COST_MODEL_SUMMARY_FILENAME),
)
_REVIEW_INPUTS_DIRNAME = "review_inputs"
_WORK_ORDERS_DIRNAME = "work_orders"
_GPT_WORK_ORDER_FILENAME = "gpt_next_action_handoff.md"
_CODEX_WORK_ORDER_FILENAME = "codex_work_order.md"
_ANTIGRAVITY_WORK_ORDER_FILENAME = "antigravity_review_order.md"
_CLAUDE_WORK_ORDER_FILENAME = "claude_critique_order.md"
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
    ("paper_observation_readiness", _PAPER_OBSERVATION_READINESS_FILENAME),
    ("research_board_prioritization", _RESEARCH_BOARD_PRIORITIZATION_FILENAME),
    ("research_candidate_queue", _RESEARCH_CANDIDATE_QUEUE_FILENAME),
    ("baseline_health_evaluation", _BASELINE_HEALTH_EVALUATION_FILENAME),
    ("baseline_evidence_metrics", _BASELINE_EVIDENCE_METRICS_FILENAME),
    ("review_handoff", _REVIEW_HANDOFF_FILENAME),
    ("gpt_next_action_handoff", f"{_WORK_ORDERS_DIRNAME}/{_GPT_WORK_ORDER_FILENAME}"),
    ("codex_work_order", f"{_WORK_ORDERS_DIRNAME}/{_CODEX_WORK_ORDER_FILENAME}"),
    (
        "antigravity_review_order",
        f"{_WORK_ORDERS_DIRNAME}/{_ANTIGRAVITY_WORK_ORDER_FILENAME}",
    ),
    ("claude_critique_order", f"{_WORK_ORDERS_DIRNAME}/{_CLAUDE_WORK_ORDER_FILENAME}"),
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
    "research_candidate_queue_version",
    "research_candidate_queue_path",
    "research_candidate_queue",
    "paper_observation_readiness_version",
    "paper_observation_readiness_path",
    "paper_observation_readiness",
    "research_board_prioritization_version",
    "research_board_prioritization_path",
    "research_board_prioritization",
    "baseline_health_evaluation_version",
    "baseline_health_evaluation_path",
    "baseline_health_evaluation",
    "baseline_evidence_metrics_version",
    "baseline_evidence_metrics_path",
    "baseline_evidence_metrics",
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
    "next_action_selector",
    "work_order_exports",
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
    "research_candidate_queue_version",
    "research_candidate_queue_path",
    "research_candidate_queue",
    "paper_observation_readiness_version",
    "paper_observation_readiness_path",
    "paper_observation_readiness",
    "research_board_prioritization_version",
    "research_board_prioritization_path",
    "research_board_prioritization",
    "baseline_health_evaluation_version",
    "baseline_health_evaluation_path",
    "baseline_health_evaluation",
    "baseline_evidence_metrics_version",
    "baseline_evidence_metrics_path",
    "baseline_evidence_metrics",
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
    "next_action_selector",
    "work_order_exports",
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
_SELECTOR_FORBIDDEN_ACTION_TERMS = (
    "submit_order",
    "place_order",
    "cancel_order",
    "replace_order",
    "close_order",
    "liquidate",
    "live_trading",
    "paper_submit_authorized=true",
    "broker_read",
    "broker_mutation",
    "load_secret",
    "load_credential",
)
_WORK_ORDER_ARTIFACTS = (
    (
        "gpt_next_action_handoff",
        _GPT_WORK_ORDER_FILENAME,
        "GPT",
        "source_of_truth_next_action_routing",
    ),
    (
        "codex_work_order",
        _CODEX_WORK_ORDER_FILENAME,
        "Codex",
        "implementation_work_order",
    ),
    (
        "antigravity_review_order",
        _ANTIGRAVITY_WORK_ORDER_FILENAME,
        "Antigravity",
        "independent_repo_health_review",
    ),
    (
        "claude_critique_order",
        _CLAUDE_WORK_ORDER_FILENAME,
        "Claude",
        "independent_critique_audit",
    ),
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
_RESEARCH_CANDIDATE_STATUSES = (
    "queued",
    "waiting_for_review",
    "blocked",
    "repair_required",
)
_REQUIRED_RESEARCH_CANDIDATE_QUEUE_FIELDS = (
    "research_candidate_queue_version",
    "status",
    "artifact_path",
    "generation_mode",
    "priority_rules",
    "candidate_count",
    "top_candidate_id",
    "top_candidate_priority",
    "top_candidate_title",
    "selected_safe_candidate_id",
    "selected_safe_candidate_priority",
    "selected_safe_candidate_title",
    "paper_observation_readiness_path",
    "paper_observation_readiness",
    "candidates",
)
_REQUIRED_RESEARCH_CANDIDATE_FIELDS = (
    "candidate_id",
    "candidate_type",
    "title",
    "hypothesis",
    "rationale",
    "evidence_sources",
    "required_data",
    "expected_artifact_or_command",
    "priority",
    "status",
    "blocked_by",
    "safety_scope",
    "requires_daniel",
    "hard_gate_required",
    "promotion_criteria",
    "rejection_criteria",
    "next_safe_test",
)
_BASELINE_HEALTH_STATUSES = (
    "usable_control_harness",
    "evidence_incomplete",
    "blocked_by_quality_gate",
    "blocked_by_safety",
    "not_ready_for_paper_submit",
    "deprecated_candidate",
)
_BASELINE_EVIDENCE_STATUSES = (
    "daily_signal_evidence_available",
    "evidence_incomplete",
    "not_evaluated",
)
_BASELINE_METRIC_STATUSES = (
    "metrics_available",
    "metrics_partially_available",
    "metrics_missing",
    "evidence_incomplete",
    "not_ready_for_paper_submit",
    "offline_only",
    "broker_state_not_observed",
)
_BASELINE_METRIC_CONFIDENCE_STATUSES = (
    "confidence_not_yet_quantified",
    "offline_confidence_quantified",
)
_BASELINE_METRIC_ARTIFACT_INGEST_STATUSES = (
    "metric_artifacts_missing",
    "metric_artifacts_partially_ingested",
    "metric_artifacts_ingested",
    "metric_artifacts_parse_failed",
)
_BASELINE_METRIC_ARTIFACT_PARSE_STATUSES = (
    "missing",
    "path_not_file",
    "unreadable",
    "decode_error",
    "json_decode_error",
    "record_not_object",
    "empty",
    "ambiguous_record_count",
    "parsed",
)
_REQUIRED_BASELINE_HEALTH_EVALUATION_FIELDS = (
    "baseline_health_evaluation_version",
    "status",
    "artifact_path",
    "generation_mode",
    "baseline_id",
    "baseline_name",
    "baseline_role",
    "active_symbol",
    "active_strategy",
    "as_of_date",
    "posture_status",
    "preview_decision",
    "broker_state_mode",
    "blocker_status",
    "quality_gate_status",
    "decision_ledger_status",
    "research_candidate_queue_status",
    "health_status",
    "confidence_status",
    "evidence_status",
    "baseline_evidence_metrics_status",
    "baseline_evidence_snapshot_status",
    "baseline_metric_confidence_status",
    "baseline_metric_artifact_ingest_status",
    "baseline_metric_artifact_parse_status",
    "baseline_remaining_missing_metric_sources",
    "paper_observation_readiness_path",
    "paper_observation_readiness",
    "baseline_evidence_metrics_path",
    "next_safe_metric_command",
    "paper_submit_readiness_status",
    "known_strengths",
    "known_weaknesses",
    "missing_evidence",
    "required_next_artifacts",
    "next_safe_test",
    "promotion_criteria",
    "deprecation_criteria",
    "replacement_research_status",
    "requires_daniel",
    "hard_gate_required",
    "safety_scope",
)
_REQUIRED_BASELINE_EVIDENCE_METRICS_FIELDS = (
    "baseline_evidence_metrics_version",
    "status",
    "artifact_path",
    "generation_mode",
    "baseline_id",
    "baseline_name",
    "active_symbol",
    "active_strategy",
    "as_of_date",
    "evidence_snapshot_status",
    "metric_confidence_status",
    "metric_artifact_ingest_status",
    "turnover_artifact_ingest_status",
    "cost_model_artifact_ingest_status",
    "metric_artifact_paths",
    "metric_artifact_hashes",
    "metric_artifact_parse_status",
    "metric_artifact_record_count",
    "turnover_artifact_path",
    "cost_model_artifact_path",
    "turnover_artifact_hash",
    "cost_model_artifact_hash",
    "turnover_artifact_parse_status",
    "cost_model_artifact_parse_status",
    "available_metric_sources",
    "missing_metric_sources",
    "backtest_confidence_summary_status",
    "benchmark_metric_status",
    "benchmark_comparison_status",
    "backtest_metric_status",
    "drawdown_metric_status",
    "turnover_metric_status",
    "cost_model_status",
    "sample_window_status",
    "adjusted_close_basis_status",
    "quantified_metric_summary",
    "remaining_missing_metric_sources",
    "paper_observation_status",
    "paper_observation_readiness_path",
    "paper_observation_readiness",
    "broker_state_mode",
    "paper_submit_readiness_status",
    "profit_claim",
    "required_next_artifacts",
    "artifact_prerequisite_chain",
    "next_safe_metric_command",
    "promotion_criteria",
    "deprecation_criteria",
    "requires_daniel",
    "hard_gate_required",
    "safety_scope",
)
_REQUIRED_PAPER_OBSERVATION_READINESS_FIELDS = (
    "paper_observation_readiness_version",
    "status",
    "artifact_path",
    "generation_mode",
    "readiness_status",
    "remaining_gap",
    "hard_gate_required",
    "requires_daniel",
    "approval_phrase_required",
    "allowed_future_read_operations",
    "forbidden_future_operations",
    "required_preflight_booleans",
    "expected_output_artifacts",
    "stop_conditions",
    "broker_state_claim_policy",
    "broker_reads_performed",
    "broker_mutation_performed",
    "runtime_callouts_performed",
    "network_calls_performed",
    "profit_claim",
    "safety_scope",
    "broker_state_mode",
)
_REQUIRED_RESEARCH_BOARD_PRIORITIZATION_FIELDS = (
    "research_board_prioritization_version",
    "prioritization_status",
    "research_mode",
    "candidate_count",
    "ranking_method",
    "ranking_weights",
    "ranked_candidates",
    "top_candidate",
    "selected_next_safe_action",
    "why_selected",
    "why_not_broker_observation_yet",
    "hard_gate_required",
    "requires_daniel",
    "daniel_action_required_now",
    "safety_scope",
    "broker_state_mode",
    "paper_submit_authorized",
    "profit_claim",
)
_RESEARCH_CANDIDATE_FORBIDDEN_TERMS = (
    "submit_order",
    "place_order",
    "cancel_order",
    "replace_order",
    "close_order",
    "liquidate",
    "live trading",
    "live order",
    "paper order",
    "paper submit",
    "paper_submit_authorized=true",
    "broker read",
    "broker mutation",
    "load_secret",
    "load_credential",
    "credential",
    "secret",
    "paid service",
    "paid tool",
    "new account",
    "capital deployment",
    "alpaca",
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
    _materialize_turnover_and_cost_model_artifacts(
        output_root=output_root,
        config=config,
        payload=payload,
    )
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
    payload: dict[str, Any],
) -> None:
    _apply_paper_observation_readiness(payload, output_root)
    _apply_research_board_prioritization(payload, output_root)
    _apply_research_candidate_queue(payload, output_root)
    _apply_baseline_evidence_metrics(payload, output_root)
    _apply_baseline_health_evaluation(payload, output_root)
    _apply_next_action_selector(payload, output_root)
    _apply_work_order_exports(payload, output_root)
    _write_research_candidate_queue_artifact(output_root, payload)
    _write_baseline_evidence_metrics_artifact(output_root, payload)
    _write_baseline_health_evaluation_artifact(output_root, payload)
    _write_paper_observation_readiness_artifact(output_root, payload)
    _write_research_board_prioritization_artifact(output_root, payload)
    _write_work_order_artifacts(output_root, payload)

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


def _apply_paper_observation_readiness(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    readiness = _build_paper_observation_readiness(payload, artifact_paths)
    payload["paper_observation_readiness_version"] = (
        _PAPER_OBSERVATION_READINESS_VERSION
    )
    payload["paper_observation_readiness_path"] = str(
        artifact_paths["paper_observation_readiness"]
    )
    payload["paper_observation_readiness"] = readiness
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["paper_observation_readiness_path"] = payload[
            "paper_observation_readiness_path"
        ]
        dashboard["paper_observation_readiness"] = dict(readiness)


def _apply_research_candidate_queue(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    queue = _build_research_candidate_queue(payload, artifact_paths)
    payload["research_candidate_queue_version"] = _RESEARCH_CANDIDATE_QUEUE_VERSION
    payload["research_candidate_queue_path"] = str(
        artifact_paths["research_candidate_queue"]
    )
    payload["research_candidate_queue"] = queue
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["research_candidate_queue_path"] = payload[
            "research_candidate_queue_path"
        ]
        dashboard["research_candidate_queue"] = dict(queue)


def _apply_baseline_evidence_metrics(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    metrics = _build_baseline_evidence_metrics(payload, artifact_paths)
    payload["baseline_evidence_metrics_version"] = _BASELINE_EVIDENCE_METRICS_VERSION
    payload["baseline_evidence_metrics_path"] = str(
        artifact_paths["baseline_evidence_metrics"]
    )
    payload["baseline_evidence_metrics"] = metrics
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["baseline_evidence_metrics_path"] = payload[
            "baseline_evidence_metrics_path"
        ]
        dashboard["baseline_evidence_metrics"] = dict(metrics)


def _apply_baseline_health_evaluation(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    evaluation = _build_baseline_health_evaluation(payload, artifact_paths)
    payload["baseline_health_evaluation_version"] = (
        _BASELINE_HEALTH_EVALUATION_VERSION
    )
    payload["baseline_health_evaluation_path"] = str(
        artifact_paths["baseline_health_evaluation"]
    )
    payload["baseline_health_evaluation"] = evaluation
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["baseline_health_evaluation_path"] = payload[
            "baseline_health_evaluation_path"
        ]
        dashboard["baseline_health_evaluation"] = dict(evaluation)


def _build_baseline_evidence_metrics(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    active_baseline = _active_baseline_record(payload)
    readiness = _paper_observation_readiness_record(payload, artifact_paths)
    output_root = _artifact_output_root(artifact_paths["baseline_evidence_metrics"])
    metric_artifact_ingest = _ingest_baseline_metric_artifacts(output_root)
    metric_artifact_records = metric_artifact_ingest.pop("_records")
    sample_window_status = _baseline_sample_window_status(payload)
    adjusted_close_basis_status = _adjusted_close_basis_status(payload)
    artifact_statuses = _baseline_metric_statuses_from_artifacts(
        metric_artifact_records=metric_artifact_records,
        initial_sample_window_status=sample_window_status,
        initial_adjusted_close_basis_status=adjusted_close_basis_status,
    )
    sample_window_status = artifact_statuses["sample_window_status"]
    adjusted_close_basis_status = artifact_statuses["adjusted_close_basis_status"]
    available_sources = _available_baseline_metric_sources(
        payload,
        sample_window_status=sample_window_status,
        adjusted_close_basis_status=adjusted_close_basis_status,
        metric_artifact_records=metric_artifact_records,
    )
    remaining_missing_sources = _remaining_missing_baseline_metric_sources(
        backtest_confidence_summary_status=artifact_statuses[
            "backtest_confidence_summary_status"
        ],
        benchmark_metric_status=artifact_statuses["benchmark_metric_status"],
        drawdown_metric_status=artifact_statuses["drawdown_metric_status"],
        turnover_metric_status=artifact_statuses["turnover_metric_status"],
        cost_model_status=artifact_statuses["cost_model_status"],
        adjusted_close_basis_status=adjusted_close_basis_status,
        metric_artifact_ingest_status=str(
            metric_artifact_ingest["metric_artifact_ingest_status"]
        ),
    )
    evidence_snapshot_status = _baseline_evidence_snapshot_status(
        available_sources,
        remaining_missing_sources,
    )
    metric_confidence_status = _baseline_metric_confidence_status(
        artifact_statuses=artifact_statuses,
        remaining_missing_sources=remaining_missing_sources,
    )
    next_artifacts = _baseline_metric_next_artifacts(artifact_paths)
    return {
        "baseline_evidence_metrics_version": _BASELINE_EVIDENCE_METRICS_VERSION,
        "status": "generated",
        "artifact_path": str(artifact_paths["baseline_evidence_metrics"]),
        "generation_mode": "deterministic_offline_from_packet_evidence",
        "baseline_id": "spy_sma_50_200_daily_long_only",
        "baseline_name": str(
            active_baseline.get(
                "candidate_name",
                "SPY SMA 50/200 daily long-only baseline",
            )
        ),
        "active_symbol": str(payload.get("symbol", _DEFAULT_SYMBOL)),
        "active_strategy": "SMA 50/200",
        "as_of_date": str(payload.get("as_of_date", "as_of_date_missing")),
        "evidence_snapshot_status": evidence_snapshot_status,
        "metric_confidence_status": metric_confidence_status,
        "metric_artifact_ingest_status": metric_artifact_ingest[
            "metric_artifact_ingest_status"
        ],
        "turnover_artifact_ingest_status": _single_metric_artifact_ingest_status(
            artifact_id="turnover_summary",
            parsed_status=metric_artifact_ingest["metric_artifact_parse_status"].get(
                "turnover_summary",
                "missing",
            ),
        ),
        "cost_model_artifact_ingest_status": _single_metric_artifact_ingest_status(
            artifact_id="cost_model_summary",
            parsed_status=metric_artifact_ingest["metric_artifact_parse_status"].get(
                "cost_model_summary",
                "missing",
            ),
        ),
        "metric_artifact_paths": metric_artifact_ingest["metric_artifact_paths"],
        "metric_artifact_hashes": metric_artifact_ingest["metric_artifact_hashes"],
        "metric_artifact_parse_status": metric_artifact_ingest[
            "metric_artifact_parse_status"
        ],
        "metric_artifact_record_count": metric_artifact_ingest[
            "metric_artifact_record_count"
        ],
        "turnover_artifact_path": metric_artifact_ingest["metric_artifact_paths"][
            "turnover_summary"
        ],
        "cost_model_artifact_path": metric_artifact_ingest["metric_artifact_paths"][
            "cost_model_summary"
        ],
        "turnover_artifact_hash": metric_artifact_ingest[
            "metric_artifact_hashes"
        ].get("turnover_summary"),
        "cost_model_artifact_hash": metric_artifact_ingest[
            "metric_artifact_hashes"
        ].get("cost_model_summary"),
        "turnover_artifact_parse_status": metric_artifact_ingest[
            "metric_artifact_parse_status"
        ]["turnover_summary"],
        "cost_model_artifact_parse_status": metric_artifact_ingest[
            "metric_artifact_parse_status"
        ]["cost_model_summary"],
        "available_metric_sources": available_sources,
        "missing_metric_sources": remaining_missing_sources,
        "backtest_confidence_summary_status": artifact_statuses[
            "backtest_confidence_summary_status"
        ],
        "benchmark_metric_status": artifact_statuses["benchmark_metric_status"],
        "benchmark_comparison_status": artifact_statuses["benchmark_metric_status"],
        "backtest_metric_status": artifact_statuses["backtest_metric_status"],
        "drawdown_metric_status": artifact_statuses["drawdown_metric_status"],
        "turnover_metric_status": artifact_statuses["turnover_metric_status"],
        "cost_model_status": artifact_statuses["cost_model_status"],
        "sample_window_status": sample_window_status,
        "adjusted_close_basis_status": adjusted_close_basis_status,
        "quantified_metric_summary": _quantified_metric_summary(
            metric_artifact_records
        ),
        "remaining_missing_metric_sources": remaining_missing_sources,
        "paper_observation_status": "broker_state_not_observed",
        "paper_observation_readiness_path": str(
            artifact_paths["paper_observation_readiness"]
        ),
        "paper_observation_readiness": dict(readiness),
        "broker_state_mode": str(
            payload.get("broker_state_mode", "broker_state_not_observed")
        ),
        "paper_submit_readiness_status": "not_ready_for_paper_submit",
        "profit_claim": "none",
        "required_next_artifacts": next_artifacts,
        "artifact_prerequisite_chain": _baseline_metric_prerequisite_chain(
            artifact_paths
        ),
        "next_safe_metric_command": _baseline_evidence_next_safe_metric_command(
            artifact_paths
        ),
        "promotion_criteria": [
            "offline backtest confidence summary exists",
            "buy-and-hold benchmark comparison status is explicit",
            "drawdown and turnover metrics are materialized from deterministic local inputs",
            "cost model assumptions are explicit",
            "adjusted-close basis is confirmed from local evidence",
            "profit_claim remains none",
            "broker_state_not_observed wording remains intact until a separate read-only milestone observes broker state",
        ],
        "deprecation_criteria": [
            "required offline metric artifacts cannot be produced without broker or network access",
            "adjusted-close basis cannot be established from local evidence",
            "metric command requires credentialed or paid-service runtime access",
            "Daniel/GPT approve a replacement control harness with explicit intake evidence",
        ],
        "requires_daniel": False,
        "hard_gate_required": False,
        "safety_scope": (
            "offline_preview_only_no_broker_access_no_submit_no_profit_claim_"
            "broker_state_not_observed"
        ),
    }


def _ingest_baseline_metric_artifacts(output_root: Path) -> dict[str, Any]:
    records: dict[str, Mapping[str, Any]] = {}
    paths: dict[str, str] = {}
    hashes: dict[str, str] = {}
    parse_status: dict[str, str] = {}
    record_count: dict[str, int] = {}

    for artifact_id, filename in _BASELINE_METRIC_ARTIFACTS:
        path = output_root / filename
        paths[artifact_id] = _normalize_path(path)
        artifact_record, status, count, digest = _read_single_jsonl_artifact(path)
        parse_status[artifact_id] = status
        record_count[artifact_id] = count
        if digest is not None:
            hashes[artifact_id] = digest
        if artifact_record is not None:
            records[artifact_id] = artifact_record

    statuses = set(parse_status.values())
    if statuses == {"missing"}:
        ingest_status = "metric_artifacts_missing"
    elif statuses == {"parsed"}:
        ingest_status = "metric_artifacts_ingested"
    elif any(status not in {"missing", "parsed"} for status in statuses):
        ingest_status = "metric_artifacts_parse_failed"
    else:
        ingest_status = "metric_artifacts_partially_ingested"

    return {
        "metric_artifact_ingest_status": ingest_status,
        "metric_artifact_paths": paths,
        "metric_artifact_hashes": hashes,
        "metric_artifact_parse_status": parse_status,
        "metric_artifact_record_count": record_count,
        "_records": records,
    }


def _single_metric_artifact_ingest_status(
    *,
    artifact_id: str,
    parsed_status: str,
) -> str:
    if parsed_status == "parsed":
        suffix = "ingested"
    elif parsed_status == "missing":
        suffix = "missing"
    else:
        suffix = "parse_failed"
    if artifact_id == "turnover_summary":
        return f"turnover_artifact_{suffix}"
    if artifact_id == "cost_model_summary":
        return f"cost_model_artifact_{suffix}"
    return f"{artifact_id}_{suffix}"


def _read_single_jsonl_artifact(
    path: Path,
) -> tuple[Mapping[str, Any] | None, str, int, str | None]:
    if not path.exists():
        return None, "missing", 0, None
    if not path.is_file():
        return None, "path_not_file", 0, None

    try:
        content = path.read_bytes()
    except OSError:
        return None, "unreadable", 0, None

    digest = hashlib.sha256(content).hexdigest()
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return None, "decode_error", 0, digest

    records: list[Mapping[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            return None, "json_decode_error", len(records), digest
        if not isinstance(decoded, Mapping):
            return None, "record_not_object", len(records) + 1, digest
        records.append(decoded)

    if not records:
        return None, "empty", 0, digest
    if len(records) != 1:
        return None, "ambiguous_record_count", len(records), digest
    return records[0], "parsed", 1, digest


def _baseline_metric_statuses_from_artifacts(
    *,
    metric_artifact_records: Mapping[str, Mapping[str, Any]],
    initial_sample_window_status: str,
    initial_adjusted_close_basis_status: str,
) -> dict[str, str]:
    metrics_record = metric_artifact_records.get("baseline_authorized_adjusted_metrics")
    summary_record = metric_artifact_records.get("offline_backtest_confidence_summary")
    evidence_record = metric_artifact_records.get("adjusted_close_evidence")
    turnover_record = metric_artifact_records.get("turnover_summary")
    cost_model_record = metric_artifact_records.get("cost_model_summary")
    metrics_materialized = _artifact_bool(metrics_record, "metrics_materialized")

    backtest_confidence_summary_status = (
        "metrics_available"
        if _has_artifact_value(summary_record, "comparison_summary_status")
        else "metrics_missing"
    )
    backtest_metric_status = (
        "metrics_available"
        if metrics_materialized
        and (
            _has_artifact_value(metrics_record, "matched_evaluated_return_count")
            or _has_artifact_value(metrics_record, "full_window_return_deltas")
        )
        else "metrics_missing"
    )
    benchmark_metric_status = (
        "metrics_available"
        if metrics_materialized
        and (
            _artifact_mapping_has_any_key(
                metrics_record,
                "full_window_return_deltas",
                ("benchmark_total_return",),
            )
            or _artifact_slice_has_any_key(
                metrics_record,
                "matched_slice_comparisons",
                ("adjusted_benchmark_total_return", "raw_benchmark_total_return"),
            )
        )
        else "metrics_missing"
    )
    drawdown_metric_status = (
        "metrics_available"
        if metrics_materialized
        and (
            _has_artifact_value(metrics_record, "drawdown_conclusion_changes")
            or _artifact_slice_has_any_key(
                metrics_record,
                "matched_slice_comparisons",
                ("adjusted_strategy_max_drawdown", "raw_strategy_max_drawdown"),
            )
        )
        else "metrics_missing"
    )
    turnover_metric_status = _turnover_metric_status(turnover_record)
    cost_model_status = _cost_model_metric_status(cost_model_record)
    sample_window_status = initial_sample_window_status
    if _has_artifact_value(metrics_record, "matched_evaluated_return_count"):
        sample_window_status = "metrics_available"
    adjusted_close_basis_status = initial_adjusted_close_basis_status
    if _artifact_bool(evidence_record, "adjusted_basis_verified"):
        adjusted_close_basis_status = "metrics_available"

    return {
        "backtest_confidence_summary_status": backtest_confidence_summary_status,
        "benchmark_metric_status": benchmark_metric_status,
        "backtest_metric_status": backtest_metric_status,
        "drawdown_metric_status": drawdown_metric_status,
        "turnover_metric_status": turnover_metric_status,
        "cost_model_status": cost_model_status,
        "sample_window_status": sample_window_status,
        "adjusted_close_basis_status": adjusted_close_basis_status,
    }


def _turnover_metric_status(record: Mapping[str, Any] | None) -> str:
    status = str(record.get("turnover_summary_status", "")) if isinstance(record, Mapping) else ""
    if status.startswith("turnover_summary_materialized"):
        return "metrics_available"
    if status:
        return "metrics_partially_available"
    return "metrics_missing"


def _cost_model_metric_status(record: Mapping[str, Any] | None) -> str:
    status = str(record.get("cost_model_summary_status", "")) if isinstance(record, Mapping) else ""
    if status.startswith("cost_model_summary_materialized"):
        return "metrics_available"
    if status:
        return "metrics_partially_available"
    return "metrics_missing"


def _baseline_metric_confidence_status(
    *,
    artifact_statuses: Mapping[str, str],
    remaining_missing_sources: list[str],
) -> str:
    offline_required_statuses = (
        "backtest_confidence_summary_status",
        "benchmark_metric_status",
        "backtest_metric_status",
        "drawdown_metric_status",
        "turnover_metric_status",
        "cost_model_status",
        "sample_window_status",
        "adjusted_close_basis_status",
    )
    if all(
        artifact_statuses.get(status_name) == "metrics_available"
        for status_name in offline_required_statuses
    ):
        return "offline_confidence_quantified"
    _ = remaining_missing_sources
    return "confidence_not_yet_quantified"


def _quantified_metric_summary(
    metric_artifact_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    metrics_record = metric_artifact_records.get("baseline_authorized_adjusted_metrics")
    if not isinstance(metrics_record, Mapping):
        return {}
    summary: dict[str, Any] = {}
    for field_name in (
        "metrics_materialization_status",
        "metrics_materialized",
        "metrics_source_basis",
        "active_preferred_baseline",
        "active_preferred_basis",
        "comparison_basis",
        "matched_total_interval_count",
        "matched_evaluated_return_count",
        "full_adjusted_history_evaluated_return_count",
        "known_basis_delta_slices",
        "known_basis_delta_slice_count",
        "return_conclusions_unchanged",
        "basis_delta_review_required",
        "return_conclusion_changes",
        "drawdown_conclusion_changes",
        "full_window_return_deltas",
        "metrics_materialized_fields",
    ):
        if field_name in metrics_record:
            summary[field_name] = _json_safe(metrics_record[field_name])
    matched_slice_comparisons = metrics_record.get("matched_slice_comparisons")
    if isinstance(matched_slice_comparisons, list):
        summary["matched_slice_count"] = len(matched_slice_comparisons)
        summary["matched_slice_names"] = [
            str(item.get("slice_name"))
            for item in matched_slice_comparisons
            if isinstance(item, Mapping) and item.get("slice_name") is not None
        ]
    if summary:
        summary["summary_source"] = "baseline_authorized_adjusted_metrics.jsonl"
    return summary


def _has_artifact_value(
    record: Mapping[str, Any] | None,
    field_name: str,
) -> bool:
    if not isinstance(record, Mapping) or field_name not in record:
        return False
    value = record[field_name]
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _artifact_bool(record: Mapping[str, Any] | None, field_name: str) -> bool:
    return isinstance(record, Mapping) and record.get(field_name) is True


def _artifact_mapping_has_any_key(
    record: Mapping[str, Any] | None,
    field_name: str,
    keys: tuple[str, ...],
) -> bool:
    if not isinstance(record, Mapping):
        return False
    value = record.get(field_name)
    return isinstance(value, Mapping) and any(key in value for key in keys)


def _artifact_slice_has_any_key(
    record: Mapping[str, Any] | None,
    field_name: str,
    keys: tuple[str, ...],
) -> bool:
    if not isinstance(record, Mapping):
        return False
    value = record.get(field_name)
    if not isinstance(value, list):
        return False
    return any(
        isinstance(item, Mapping) and any(key in item for key in keys)
        for item in value
    )


def _any_artifact_has_key(
    records: Mapping[str, Mapping[str, Any]],
    keys: tuple[str, ...],
) -> bool:
    for record in records.values():
        if any(key in record for key in keys):
            return True
    return False


def _baseline_sample_window_status(payload: Mapping[str, Any]) -> str:
    sma = payload.get("sma")
    usable_bar_count = None
    if isinstance(sma, Mapping):
        usable_bar_count = sma.get("usable_bar_count")
    try:
        usable_count = int(usable_bar_count)
        slow_window = int(payload.get("sma_slow_window", 200))
    except (TypeError, ValueError):
        return "metrics_missing"
    return "metrics_available" if usable_count >= slow_window else "metrics_missing"


def _adjusted_close_basis_status(payload: Mapping[str, Any]) -> str:
    if _input_csv_has_column(payload.get("input_data_path"), "adjusted_close"):
        return "metrics_available"
    return "metrics_missing"


def _input_csv_has_column(input_data_path: Any, column_name: str) -> bool:
    text = str(input_data_path or "").strip()
    if not text:
        return False
    path = Path(text)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            headers = next(csv.reader(stream), [])
    except (OSError, StopIteration):
        return False
    expected = column_name.strip().lower()
    return any(str(header).strip().lower() == expected for header in headers)


def _available_baseline_metric_sources(
    payload: Mapping[str, Any],
    *,
    sample_window_status: str,
    adjusted_close_basis_status: str,
    metric_artifact_records: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    sources = [
        "packet.sma.posture",
        "packet.sma.fast_value",
        "packet.sma.slow_value",
        "packet.sma.usable_bar_count",
        "packet.input_data_sha256",
        "packet.research_lab.active_strategy_evidence",
    ]
    if sample_window_status == "metrics_available":
        sources.append("sample_window.usable_bar_count_at_least_slow_window")
    if adjusted_close_basis_status == "metrics_available":
        sources.append("input_csv.adjusted_close_column")
    if str(payload.get("quality_gate_status")) == "pass":
        sources.append("packet.quality_gate.pass")
    for artifact_id in metric_artifact_records:
        sources.append(f"metric_artifact.{artifact_id}")
    metrics_record = metric_artifact_records.get("baseline_authorized_adjusted_metrics")
    if _has_artifact_value(metrics_record, "metrics_materialization_status"):
        sources.append("baseline_authorized_adjusted_metrics.materialization_status")
    if _has_artifact_value(metrics_record, "full_window_return_deltas"):
        sources.append("baseline_authorized_adjusted_metrics.full_window_return_deltas")
    if _has_artifact_value(metrics_record, "matched_slice_comparisons"):
        sources.append("baseline_authorized_adjusted_metrics.matched_slice_comparisons")
    summary_record = metric_artifact_records.get("offline_backtest_confidence_summary")
    if _has_artifact_value(summary_record, "comparison_summary_status"):
        sources.append("offline_backtest_confidence_summary.comparison_summary_status")
    evidence_record = metric_artifact_records.get("adjusted_close_evidence")
    if _has_artifact_value(evidence_record, "promotion_status"):
        sources.append("adjusted_close_evidence.promotion_status")
    turnover_record = metric_artifact_records.get("turnover_summary")
    if _has_artifact_value(turnover_record, "turnover_summary_status"):
        sources.append("turnover_summary.turnover_summary_status")
    if _has_artifact_value(turnover_record, "signal_change_count"):
        sources.append("turnover_summary.signal_change_count")
    cost_model_record = metric_artifact_records.get("cost_model_summary")
    if _has_artifact_value(cost_model_record, "cost_model_summary_status"):
        sources.append("cost_model_summary.cost_model_summary_status")
    if _has_artifact_value(cost_model_record, "estimated_cost_per_trade_status"):
        sources.append("cost_model_summary.estimated_cost_per_trade_status")
    return sources


def _remaining_missing_baseline_metric_sources(
    *,
    backtest_confidence_summary_status: str,
    benchmark_metric_status: str,
    drawdown_metric_status: str,
    turnover_metric_status: str,
    cost_model_status: str,
    adjusted_close_basis_status: str,
    metric_artifact_ingest_status: str,
) -> list[str]:
    missing: list[str] = []
    if metric_artifact_ingest_status == "metric_artifacts_parse_failed":
        missing.append("parseable_metric_artifacts")
    if backtest_confidence_summary_status != "metrics_available":
        missing.append("offline_backtest_confidence_summary")
    if benchmark_metric_status != "metrics_available":
        missing.append("buy_and_hold_benchmark_status")
    if drawdown_metric_status != "metrics_available":
        missing.append("drawdown_summary")
    if turnover_metric_status != "metrics_available":
        missing.append("turnover_summary")
    if cost_model_status != "metrics_available":
        missing.append("cost_model_summary")
    missing.append("paper_observation_summary")
    if adjusted_close_basis_status != "metrics_available":
        missing.append("input_csv.adjusted_close_column")
    return missing


def _baseline_evidence_snapshot_status(
    available_sources: list[str],
    missing_sources: list[str],
) -> str:
    if available_sources and missing_sources:
        return "metrics_partially_available"
    if available_sources:
        return "metrics_available"
    return "metrics_missing"


def _baseline_metric_next_artifacts(
    artifact_paths: Mapping[str, str],
) -> list[str]:
    output_root = _artifact_output_root(artifact_paths["baseline_evidence_metrics"])
    return [
        _normalize_path(output_root / _BASELINE_BACKTEST_CONFIDENCE_SUMMARY_FILENAME),
        _normalize_path(output_root / _BASELINE_ADJUSTED_CLOSE_EVIDENCE_FILENAME),
        _normalize_path(output_root / _BASELINE_METRIC_MATERIALIZATION_FILENAME),
        _normalize_path(output_root / _BASELINE_TURNOVER_SUMMARY_FILENAME),
        _normalize_path(output_root / _BASELINE_COST_MODEL_SUMMARY_FILENAME),
        "buy_and_hold_benchmark_status",
        "drawdown_summary",
        "paper_observation_summary_hard_gated_by_broker_read_scope",
    ]


def _baseline_evidence_next_safe_metric_command(
    artifact_paths: Mapping[str, str],
) -> str:
    output_root = _artifact_output_root(artifact_paths["baseline_evidence_metrics"])
    run_log = _normalize_path(output_root / _BASELINE_METRIC_MATERIALIZATION_FILENAME)
    summary_path = _normalize_path(
        output_root / _BASELINE_BACKTEST_CONFIDENCE_SUMMARY_FILENAME
    )
    source_evidence_path = _normalize_path(
        output_root / _BASELINE_ADJUSTED_CLOSE_EVIDENCE_FILENAME
    )
    return (
        "python -m algotrader.cli etf-sma-authorized-adjusted-baseline-metrics "
        "--symbol SPY "
        "--run-id spy_sma_50_200_baseline_metrics "
        f"--run-log {run_log} "
        f"--summary-path {summary_path} "
        f"--source-evidence-path {source_evidence_path} "
        "--format json"
    )


def _baseline_metric_prerequisite_chain(
    artifact_paths: Mapping[str, str],
) -> list[str]:
    output_root = _artifact_output_root(artifact_paths["baseline_evidence_metrics"])
    run_command = f"{_SCRIPT} -OutputRoot {_normalize_path(output_root)}"
    return [
        (
            "1. Run the daily packet once to create the selected output root and "
            f"materialize {_BASELINE_TURNOVER_SUMMARY_FILENAME} plus "
            f"{_BASELINE_COST_MODEL_SUMMARY_FILENAME}: {run_command}"
        ),
        (
            "2. Materialize the v1.10 prerequisite local metric sources with "
            f"next_safe_metric_command: {_baseline_evidence_next_safe_metric_command(artifact_paths)}"
        ),
        (
            "3. Rerun the daily packet against the same output root so "
            f"{_BASELINE_EVIDENCE_METRICS_FILENAME} ingests the v1.10 metrics, "
            f"{_BASELINE_TURNOVER_SUMMARY_FILENAME}, and "
            f"{_BASELINE_COST_MODEL_SUMMARY_FILENAME}: {run_command}"
        ),
        (
            "4. Leave paper_observation_summary missing; any future broker-state "
            "observation requires a separate Daniel-scoped read-only hard gate."
        ),
    ]


def _artifact_output_root(artifact_path: str) -> Path:
    return Path(str(artifact_path)).parent


def _build_baseline_health_evaluation(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    active_baseline = _active_baseline_record(payload)
    readiness = _paper_observation_readiness_record(payload, artifact_paths)
    missing_evidence = _baseline_missing_evidence(payload, active_baseline)
    health_status = _baseline_health_status(payload, active_baseline)
    evidence_status = _baseline_evidence_status(active_baseline, missing_evidence)
    known_strengths = _baseline_known_strengths(payload, active_baseline)
    known_weaknesses = _baseline_known_weaknesses(payload, missing_evidence)
    metrics = payload.get("baseline_evidence_metrics")
    metrics_record = metrics if isinstance(metrics, Mapping) else {}
    return {
        "baseline_health_evaluation_version": _BASELINE_HEALTH_EVALUATION_VERSION,
        "status": "generated",
        "artifact_path": str(artifact_paths["baseline_health_evaluation"]),
        "generation_mode": "deterministic_offline_from_packet_evidence",
        "baseline_id": "spy_sma_50_200_daily_long_only",
        "baseline_name": str(
            active_baseline.get(
                "candidate_name",
                "SPY SMA 50/200 daily long-only baseline",
            )
        ),
        "baseline_role": "controlled_baseline_harness_for_assistant_evaluation",
        "active_symbol": str(payload.get("symbol", _DEFAULT_SYMBOL)),
        "active_strategy": "SMA 50/200",
        "as_of_date": str(payload.get("as_of_date", "as_of_date_missing")),
        "posture_status": str(
            payload.get("sma_posture_status", payload.get("posture", "unknown"))
        ),
        "preview_decision": str(
            payload.get("preview_decision", "preview_decision_missing")
        ),
        "broker_state_mode": str(
            payload.get("broker_state_mode", "broker_state_not_observed")
        ),
        "blocker_status": str(
            payload.get("blocker_status", "broker_state_not_observed")
        ),
        "quality_gate_status": str(payload.get("quality_gate_status", "not_evaluated")),
        "decision_ledger_status": str(
            payload.get("decision_ledger_status", "decision_ledger_status_missing")
        ),
        "research_candidate_queue_status": _research_candidate_queue_status(payload),
        "health_status": health_status,
        "confidence_status": str(
            active_baseline.get(
                "confidence_status",
                payload.get("research_lab", {}).get(
                    "confidence_status",
                    "confidence_not_yet_quantified",
                )
                if isinstance(payload.get("research_lab"), Mapping)
                else "confidence_not_yet_quantified",
            )
        ),
        "evidence_status": evidence_status,
        "baseline_evidence_metrics_status": str(
            metrics_record.get("status", "not_generated")
        ),
        "baseline_evidence_snapshot_status": str(
            metrics_record.get("evidence_snapshot_status", "metrics_missing")
        ),
        "baseline_metric_confidence_status": str(
            metrics_record.get(
                "metric_confidence_status",
                "confidence_not_yet_quantified",
            )
        ),
        "baseline_metric_artifact_ingest_status": str(
            metrics_record.get(
                "metric_artifact_ingest_status",
                "metric_artifacts_missing",
            )
        ),
        "baseline_metric_artifact_parse_status": dict(
            metrics_record.get("metric_artifact_parse_status", {})
        ),
        "baseline_remaining_missing_metric_sources": list(
            metrics_record.get(
                "remaining_missing_metric_sources",
                metrics_record.get("missing_metric_sources", []),
            )
        ),
        "paper_observation_readiness_path": str(
            artifact_paths["paper_observation_readiness"]
        ),
        "paper_observation_readiness": dict(readiness),
        "baseline_evidence_metrics_path": str(
            payload.get(
                "baseline_evidence_metrics_path",
                artifact_paths["baseline_evidence_metrics"],
            )
        ),
        "next_safe_metric_command": str(
            metrics_record.get(
                "next_safe_metric_command",
                _baseline_evidence_next_safe_metric_command(artifact_paths),
            )
        ),
        "paper_submit_readiness_status": "not_ready_for_paper_submit",
        "known_strengths": known_strengths,
        "known_weaknesses": known_weaknesses,
        "missing_evidence": missing_evidence,
        "required_next_artifacts": [
            "baseline_evidence_metrics.jsonl",
            "offline_backtest_confidence_summary",
            "drawdown_summary",
            _BASELINE_TURNOVER_SUMMARY_FILENAME,
            _BASELINE_COST_MODEL_SUMMARY_FILENAME,
            "buy_and_hold_benchmark_status",
            "paper_observation_summary_hard_gated_by_broker_read_scope",
            "baseline_evidence_gap_summary",
        ],
        "next_safe_test": _BASELINE_HEALTH_NEXT_SAFE_TEST,
        "promotion_criteria": [
            "quality_gate_status remains pass",
            "decision ledger records accepted or accepted-with-minor-note review",
            "offline confidence, drawdown, turnover, cost-model, and benchmark artifacts exist",
            "broker_state_not_observed wording remains intact until a separate read-only milestone observes broker state",
            "paper-submit promotion requires a separately scoped Daniel hard gate",
            "artifact makes no profit claim",
        ],
        "deprecation_criteria": [
            "quality gate cannot be repaired without weakening safety invariants",
            "local daily history is insufficient and cannot be refreshed safely",
            "required offline evidence remains unavailable after the evidence-gap test",
            "Daniel/GPT approve a replacement control harness with explicit intake evidence",
        ],
        "replacement_research_status": _replacement_research_status(payload),
        "requires_daniel": _baseline_requires_daniel(payload, health_status),
        "hard_gate_required": False,
        "safety_scope": (
            "offline_preview_only_no_broker_access_no_submit_no_profit_claim"
        ),
    }


def _active_baseline_record(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    board = payload.get("research_board")
    if not isinstance(board, list):
        research_lab = payload.get("research_lab")
        board = (
            research_lab.get("research_board", [])
            if isinstance(research_lab, Mapping)
            else []
        )
    for item in board:
        if isinstance(item, Mapping) and item.get("status") == "active_baseline":
            return item
    return {}


def _baseline_missing_evidence(
    payload: Mapping[str, Any],
    active_baseline: Mapping[str, Any],
) -> list[str]:
    evidence: list[str] = []
    for source in (
        active_baseline.get("missing_evidence"),
        payload.get("research_lab", {}).get("missing_evidence", [])
        if isinstance(payload.get("research_lab"), Mapping)
        else [],
    ):
        if isinstance(source, list):
            for item in source:
                text = str(item)
                if text and text not in evidence:
                    evidence.append(text)
    return _filter_resolved_baseline_missing_evidence(payload, evidence)


def _filter_resolved_baseline_missing_evidence(
    payload: Mapping[str, Any],
    evidence: list[str],
) -> list[str]:
    metrics = payload.get("baseline_evidence_metrics")
    if not isinstance(metrics, Mapping):
        return evidence

    resolved: set[str] = set()
    if metrics.get("backtest_confidence_summary_status") == "metrics_available":
        resolved.add("offline_backtest_confidence_summary")
    if metrics.get("drawdown_metric_status") == "metrics_available":
        resolved.update({"drawdown_review", "drawdown_and_turnover_review"})
    if metrics.get("turnover_metric_status") == "metrics_available":
        resolved.add("drawdown_and_turnover_review")
    if metrics.get("metric_confidence_status") == "offline_confidence_quantified":
        resolved.add("strategy_confidence_not_yet_quantified")
    return [item for item in evidence if item not in resolved]


def _baseline_health_status(
    payload: Mapping[str, Any],
    active_baseline: Mapping[str, Any],
) -> str:
    if not active_baseline:
        return "deprecated_candidate"
    if str(payload.get("quality_gate_status", "not_evaluated")) == "fail":
        return "blocked_by_quality_gate"
    if not _paper_submit_not_authorized(payload):
        return "blocked_by_safety"
    if payload.get("broker_state_mode") not in {
        "broker_state_not_observed",
        "offline_preview_only",
    }:
        return "blocked_by_safety"
    if str(payload.get("posture", "")) == "insufficient_history":
        return "evidence_incomplete"
    return "usable_control_harness"


def _baseline_evidence_status(
    active_baseline: Mapping[str, Any],
    missing_evidence: list[str],
) -> str:
    if missing_evidence:
        return "evidence_incomplete"
    if active_baseline:
        return "daily_signal_evidence_available"
    return "not_evaluated"


def _baseline_known_strengths(
    payload: Mapping[str, Any],
    active_baseline: Mapping[str, Any],
) -> list[str]:
    strengths = [
        "active baseline is restricted to SPY",
        "SMA 50/200 posture is generated from local offline daily bars",
        "preview decision is explicitly offline_preview_only",
        "broker state wording remains broker_state_not_observed",
        "paper submit remains not_authorized",
    ]
    if active_baseline:
        strengths.append("research board identifies the active baseline explicitly")
    if str(payload.get("quality_gate_status")) == "pass":
        strengths.append("quality gate passed for the generated packet")
    metrics = payload.get("baseline_evidence_metrics")
    if isinstance(metrics, Mapping):
        if metrics.get("turnover_metric_status") == "metrics_available":
            strengths.append("turnover summary is materialized from local signal transitions")
        if metrics.get("cost_model_status") == "metrics_available":
            strengths.append("cost-model summary is materialized as offline assumptions")
    return strengths


def _baseline_known_weaknesses(
    payload: Mapping[str, Any],
    missing_evidence: list[str],
) -> list[str]:
    weaknesses = [
        "strategy confidence is not yet quantified",
        "broker_state_not_observed means positions and open orders were not read",
        "paper-submit readiness is not established",
    ]
    if missing_evidence:
        weaknesses.append("offline evidence gaps remain: " + ", ".join(missing_evidence))
    if str(payload.get("review_classification", "missing")) in {
        "missing",
        "unclassified",
    }:
        weaknesses.append("decision-ledger review evidence is not yet accepted")
    return weaknesses


def _research_candidate_queue_status(payload: Mapping[str, Any]) -> str:
    queue = payload.get("research_candidate_queue")
    if isinstance(queue, Mapping):
        return str(queue.get("status", "research_candidate_queue_missing"))
    return "research_candidate_queue_missing"


def _replacement_research_status(payload: Mapping[str, Any]) -> str:
    queue = payload.get("research_candidate_queue")
    if not isinstance(queue, Mapping):
        return "replacement_research_not_evaluated"
    candidates = queue.get("candidates")
    if not isinstance(candidates, list):
        return "replacement_research_not_evaluated"
    candidate_ids = {
        str(candidate.get("candidate_id"))
        for candidate in candidates
        if isinstance(candidate, Mapping)
    }
    if "future_non_sma_strategy_research_slot" in candidate_ids:
        return "future_research_slot_blocked_pending_strategy_intake_requirements"
    if "strategy_candidate_intake_requirements" in candidate_ids:
        return "strategy_intake_requirements_queued"
    return "no_replacement_research_candidate_selected"


def _baseline_requires_daniel(
    payload: Mapping[str, Any],
    health_status: str,
) -> bool:
    if health_status == "blocked_by_safety":
        return True
    return str(payload.get("posture", "")) == "insufficient_history"


def _build_research_candidate_queue(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    readiness = _paper_observation_readiness_record(payload, artifact_paths)
    candidates: list[dict[str, Any]] = []
    if _research_candidate_needs_p0_repair(payload):
        candidates.append(_quality_gate_repair_candidate(payload))

    if str(payload.get("validation_status", "pending")) == "fail":
        missing_fields = [str(item) for item in payload.get("missing_required_fields", [])]
        if _validation_failure_priority(missing_fields) != "P0":
            candidates.append(_packet_completeness_repair_candidate(payload))

    if str(payload.get("posture")) == "insufficient_history":
        candidates.append(_offline_daily_history_gap_candidate(payload))

    review_classification = str(payload.get("review_classification", "missing"))
    if review_classification in {"needs-repair", "rejected"}:
        candidates.append(_offline_packet_review_repair_candidate(payload))
    elif str(payload.get("review_input_status", "review_input_not_found")) in {
        "review_input_not_found",
        "review_input_directory_empty",
    }:
        candidates.append(_offline_review_evidence_gap_candidate(payload))

    candidates.extend(
        [
            _baseline_evidence_metrics_candidate(payload, artifact_paths),
            _baseline_health_evaluation_candidate(payload),
            _buy_and_hold_benchmark_candidate(payload),
            _current_baseline_evidence_gap_candidate(payload),
            _paper_lab_observation_readiness_candidate(payload),
            _strategy_candidate_intake_candidate(payload),
            _future_non_sma_strategy_slot_candidate(payload),
        ]
    )
    candidates = sorted(
        candidates,
        key=lambda item: (
            _ACTION_PRIORITY_RANK[str(item["priority"])],
            str(item["candidate_id"]),
        ),
    )
    top_candidate = candidates[0] if candidates else None
    selected_safe_candidate = _first_safe_research_candidate_from_list(candidates)
    return {
        "research_candidate_queue_version": _RESEARCH_CANDIDATE_QUEUE_VERSION,
        "status": "generated",
        "artifact_path": str(artifact_paths["research_candidate_queue"]),
        "generation_mode": "deterministic_offline_from_packet_evidence",
        "priority_rules": {
            "P0": "safety invariant or quality gate failure",
            "P1": "missing operator/data/review evidence required to interpret current packet",
            "P2": "offline research work that improves strategy evaluation",
            "P3": "backlog or future enhancements",
        },
        "candidate_count": len(candidates),
        "top_candidate_id": (
            str(top_candidate["candidate_id"]) if top_candidate is not None else None
        ),
        "top_candidate_priority": (
            str(top_candidate["priority"]) if top_candidate is not None else None
        ),
        "top_candidate_title": (
            str(top_candidate["title"]) if top_candidate is not None else None
        ),
        "selected_safe_candidate_id": (
            str(selected_safe_candidate["candidate_id"])
            if selected_safe_candidate is not None
            else None
        ),
        "selected_safe_candidate_priority": (
            str(selected_safe_candidate["priority"])
            if selected_safe_candidate is not None
            else None
        ),
        "selected_safe_candidate_title": (
            str(selected_safe_candidate["title"])
            if selected_safe_candidate is not None
            else None
        ),
        "paper_observation_readiness_path": str(
            artifact_paths["paper_observation_readiness"]
        ),
        "paper_observation_readiness": dict(readiness),
        "candidates": candidates,
    }


def _research_candidate_needs_p0_repair(payload: Mapping[str, Any]) -> bool:
    if str(payload.get("quality_gate_status", "not_evaluated")) == "fail":
        return True
    if str(payload.get("validation_status", "pending")) != "fail":
        return False
    missing_fields = [str(item) for item in payload.get("missing_required_fields", [])]
    return _validation_failure_priority(missing_fields) == "P0"


def _quality_gate_repair_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    failed_checks = [str(item) for item in payload.get("quality_gate_failed_checks", [])]
    missing_fields = [str(item) for item in payload.get("missing_required_fields", [])]
    return _research_candidate_item(
        candidate_id="quality_gate_or_safety_invariant_repair",
        candidate_type="safety_repair",
        title="Repair packet quality gate or safety invariant failure",
        hypothesis=(
            "The assistant should not rank ordinary research until the packet "
            "quality gate and safety invariants are repaired."
        ),
        rationale=(
            "P0 repair outranks research because packet evidence is not safe to "
            "interpret while required checks are failing."
        ),
        evidence_sources=[
            "quality_gate_status",
            "quality_gate_failed_checks",
            "validation_status",
            "missing_required_fields",
        ],
        required_data=[
            f"quality_gate_status={payload.get('quality_gate_status')}",
            f"validation_status={payload.get('validation_status')}",
            "failed_checks=" + ",".join(failed_checks),
            "missing_required_fields=" + ",".join(missing_fields),
        ],
        expected_artifact_or_command="repair offline packet artifacts and rerun daily lab",
        priority="P0",
        status="repair_required",
        blocked_by=[*failed_checks, *missing_fields] or ["quality_gate_or_validation_pending"],
        safety_scope="offline_packet_repair_only_no_broker_access_no_submit",
        requires_daniel=True,
        hard_gate_required=True,
        promotion_criteria=[
            "quality_gate_status returns pass",
            "validation_status returns pass",
            "safety labels and broker_state_not_observed wording remain intact",
        ],
        rejection_criteria=[
            "packet repair requires broker access",
            "packet repair weakens paper-submit lockout",
        ],
        next_safe_test="python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py",
    )


def _packet_completeness_repair_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    missing_fields = [str(item) for item in payload.get("missing_required_fields", [])]
    return _research_candidate_item(
        candidate_id="packet_completeness_repair",
        candidate_type="packet_repair",
        title="Repair missing packet completeness evidence",
        hypothesis=(
            "Completeness repair should happen before interpreting weaker research "
            "signals from the packet."
        ),
        rationale="The packet validation failed without a safety invariant breach.",
        evidence_sources=["validation_status", "missing_required_fields"],
        required_data=missing_fields or ["missing_required_fields_not_populated"],
        expected_artifact_or_command="repair deterministic packet fields and rerun daily lab",
        priority="P1",
        status="repair_required",
        blocked_by=missing_fields,
        safety_scope="offline_packet_repair_only_no_broker_access_no_submit",
        requires_daniel=True,
        hard_gate_required=False,
        promotion_criteria=["validation_status returns pass"],
        rejection_criteria=["repair requires broker or network access"],
        next_safe_test="python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py",
    )


def _offline_daily_history_gap_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    slow_window = int(payload.get("sma_slow_window", 200))
    return _research_candidate_item(
        candidate_id="offline_daily_history_gap",
        candidate_type="offline_data_gap",
        title="Provide enough offline daily bars for the active baseline",
        hypothesis=(
            "The assistant cannot interpret the active baseline until the local "
            f"input has at least {slow_window} usable as-of bars."
        ),
        rationale=str(payload.get("sma_posture_status", "insufficient_history")),
        evidence_sources=["posture", "sma_posture_status", "sma_slow_window"],
        required_data=[f"at least {slow_window} usable local daily bars for SPY"],
        expected_artifact_or_command=(
            "refresh offline SPY daily CSV input, then rerun "
            f"{_SCRIPT} -OutputRoot runs/daily_lab/latest"
        ),
        priority="P1",
        status="blocked",
        blocked_by=["insufficient_history"],
        safety_scope="offline_data_refresh_only_no_broker_access",
        requires_daniel=True,
        hard_gate_required=False,
        promotion_criteria=["posture is no longer insufficient_history"],
        rejection_criteria=["data source requires protected broker material or network access in pytest"],
        next_safe_test="python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py",
    )


def _offline_packet_review_repair_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    classification = str(payload.get("review_classification", "missing"))
    return _research_candidate_item(
        candidate_id="offline_packet_review_repair",
        candidate_type="review_repair",
        title="Repair packet issues identified by offline review",
        hypothesis=(
            "Review feedback must be resolved before the assistant promotes new "
            "research work from this packet."
        ),
        rationale=f"review_classification={classification}",
        evidence_sources=[
            "review_classification",
            "review_blockers",
            "review_repair_items",
            "review_selected_next_action",
        ],
        required_data=[
            "review_blockers="
            + ",".join(str(item) for item in payload.get("review_blockers", [])),
            "review_repair_items="
            + ",".join(str(item) for item in payload.get("review_repair_items", [])),
        ],
        expected_artifact_or_command=str(
            payload.get("review_selected_next_action", "repair offline packet artifacts")
        ),
        priority="P1",
        status="repair_required",
        blocked_by=[f"review_classification_{classification}"],
        safety_scope="offline_review_repair_only_no_broker_access_no_submit",
        requires_daniel=False,
        hard_gate_required=classification == "rejected",
        promotion_criteria=["review_classification returns accepted or accepted-with-minor-note"],
        rejection_criteria=["review repair requires broker access or runtime external calls"],
        next_safe_test="python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py",
    )


def _offline_review_evidence_gap_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    review_status = str(payload.get("review_input_status", "review_input_not_found"))
    return _research_candidate_item(
        candidate_id="offline_review_evidence_gap",
        candidate_type="review_evidence_gap",
        title="Collect offline review evidence for the current packet",
        hypothesis=(
            "A saved review classification makes the assistant's next research "
            "routing more reliable than unreviewed packet intuition."
        ),
        rationale=f"review_input_status={review_status}",
        evidence_sources=[
            "review_input_status",
            "decision_ledger_status",
            "review_classification",
        ],
        required_data=["offline review text saved under review_inputs/"],
        expected_artifact_or_command="save offline review feedback, then rerun daily lab",
        priority="P1",
        status="waiting_for_review",
        blocked_by=[review_status],
        safety_scope="offline_review_ingest_only_no_broker_access_no_submit",
        requires_daniel=False,
        hard_gate_required=False,
        promotion_criteria=[
            "decision ledger records accepted or accepted-with-minor-note review",
            "review_selected_next_action remains safety scoped",
        ],
        rejection_criteria=["review requests broker access, external services, or capital action"],
        next_safe_test="python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py",
    )


def _baseline_evidence_metrics_candidate(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    next_safe_metric_command = _baseline_evidence_next_safe_metric_command(
        artifact_paths
    )
    return _research_candidate_item(
        candidate_id="baseline_evidence_metrics_snapshot_spy_sma_50_200",
        candidate_type="baseline_evidence_metrics",
        title="Materialize and ingest offline baseline evidence for SPY SMA 50/200",
        hypothesis=(
            "The assistant becomes more useful when it can separate available "
            "signal evidence from locally materialized quantitative baseline metrics."
        ),
        rationale=(
            "Assistant v1.12 preserves v1.11 metric artifact ingest while adding "
            "the offline-only paper observation readiness hard gate without "
            "broker or network access."
        ),
        evidence_sources=[
            "baseline_evidence_metrics",
            "baseline_evidence_metrics.metric_artifact_ingest_status",
            "baseline_evidence_metrics.metric_artifact_parse_status",
            "research_lab.missing_evidence",
            "sma posture fields",
            "input_data_sha256",
        ],
        required_data=[
            "baseline_evidence_metrics.jsonl",
            "offline_backtest_confidence_summary.jsonl",
            "adjusted_close_evidence.jsonl",
            "baseline_authorized_adjusted_metrics.jsonl",
            _BASELINE_TURNOVER_SUMMARY_FILENAME,
            _BASELINE_COST_MODEL_SUMMARY_FILENAME,
            "local SPY daily CSV",
        ],
        expected_artifact_or_command=next_safe_metric_command,
        priority="P2",
        status="queued",
        blocked_by=[],
        safety_scope="offline_research_metrics_only_no_broker_access_no_submit",
        requires_daniel=False,
        hard_gate_required=False,
        promotion_criteria=[
            "baseline_evidence_metrics.jsonl is generated from packet evidence",
            "next metric command references deterministic local artifact paths",
            "metric artifact ingest status and parse status remain explicit",
            "turnover and cost-model artifact paths, hashes, and parse statuses are explicit",
            "paper_observation_summary remains missing until a broker-read hard gate is scoped",
            "profit_claim remains none",
        ],
        rejection_criteria=[
            "metrics snapshot invents performance values",
            "metric command requires nonlocal runtime access or protected material",
        ],
        next_safe_test=next_safe_metric_command,
    )


def _baseline_health_evaluation_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _research_candidate_item(
        candidate_id="baseline_health_evaluation_spy_sma_50_200",
        candidate_type="baseline_evaluation",
        title="Build baseline health evaluation for SPY SMA 50/200",
        hypothesis=(
            "The assistant becomes more useful when it can summarize baseline "
            "health beyond the current daily posture."
        ),
        rationale=(
            "The research board marks confidence as not yet quantified and names "
            "offline backtest confidence, drawdown, cost-model estimate, and "
            "paper-observation evidence gaps."
        ),
        evidence_sources=[
            "research_board.active_baseline",
            "research_lab.confidence_status",
            "research_lab.missing_evidence",
            "sma posture fields",
        ],
        required_data=[
            "local SPY daily CSV",
            "current SMA 50/200 signal output",
            "current quality gate, decision-ledger, and research queue status",
        ],
        expected_artifact_or_command=_BASELINE_HEALTH_EVALUATION_FILENAME,
        priority="P2",
        status="queued",
        blocked_by=[],
        safety_scope="offline_research_only_no_new_strategy_no_broker_access",
        requires_daniel=False,
        hard_gate_required=False,
        promotion_criteria=[
            "baseline evidence includes drawdown, turnover, cost-model, and confidence summary",
            "artifact makes no profit claim",
            "artifact keeps broker_state_not_observed wording when no broker state is observed",
        ],
        rejection_criteria=[
            "research expands the SMA catalog",
            "research relies on broker access, network calls, or nonlocal services",
        ],
        next_safe_test=_BASELINE_HEALTH_NEXT_SAFE_TEST,
    )


def _buy_and_hold_benchmark_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _research_candidate_item(
        candidate_id="benchmark_buy_and_hold_comparison_spy",
        candidate_type="benchmark_comparison",
        title="Track buy-and-hold benchmark comparison status",
        hypothesis=(
            "The assistant should know whether the active baseline has a local "
            "buy-and-hold comparison before interpreting strategy quality."
        ),
        rationale=(
            "A benchmark status item separates missing evidence from evaluated "
            "evidence without adding another strategy variant."
        ),
        evidence_sources=["research_lab.missing_evidence", "artifact_paths"],
        required_data=[
            "existing local benchmark comparison artifact if one is already available",
            "otherwise an explicit benchmark_missing status",
        ],
        expected_artifact_or_command=(
            "future offline benchmark status artifact; no broker or network access"
        ),
        priority="P2",
        status="queued",
        blocked_by=[],
        safety_scope="offline_research_only_no_new_strategy_no_broker_access",
        requires_daniel=False,
        hard_gate_required=False,
        promotion_criteria=[
            "benchmark status is explicit as available or missing",
            "comparison uses local deterministic inputs only",
        ],
        rejection_criteria=["benchmark work requires external APIs or capital action"],
        next_safe_test="python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py -k research_candidate_queue",
    )


def _current_baseline_evidence_gap_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    research_lab = payload.get("research_lab")
    missing_evidence: list[str] = []
    if isinstance(research_lab, Mapping):
        missing_evidence = [str(item) for item in research_lab.get("missing_evidence", [])]
    return _research_candidate_item(
        candidate_id="current_baseline_evidence_gap_map",
        candidate_type="evidence_gap",
        title="Map evidence gaps for the current active baseline",
        hypothesis=(
            "The assistant can route better research work when active-baseline "
            "evidence gaps are explicit and stable across packets."
        ),
        rationale="missing_evidence=" + ",".join(missing_evidence),
        evidence_sources=["research_lab.missing_evidence", "history_delta"],
        required_data=missing_evidence or ["research_lab.missing_evidence"],
        expected_artifact_or_command=(
            "future offline evidence_gap_summary artifact from packet fields"
        ),
        priority="P2",
        status="queued",
        blocked_by=[],
        safety_scope="offline_research_only_no_broker_access_no_submit",
        requires_daniel=False,
        hard_gate_required=False,
        promotion_criteria=[
            "evidence gaps are classified as data, review, benchmark, or observation gaps",
            "gap summary is deterministic from packet evidence",
        ],
        rejection_criteria=["gap summary recommends broker access without a hard gate"],
        next_safe_test="python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py -k research_candidate_queue",
    )


def _paper_lab_observation_readiness_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _research_candidate_item(
        candidate_id="paper_lab_observation_readiness",
        candidate_type="paper_lab_readiness",
        title="Define paper-lab observation readiness criteria",
        hypothesis=(
            "Before any paper-lab observation is scoped, the assistant should "
            "state exactly which offline packet conditions would make observation useful."
        ),
        rationale=(
            "Broker state remains broker_state_not_observed and paper-submit "
            "authorization remains not_authorized."
        ),
        evidence_sources=[
            "broker_state_mode",
            "paper_submit_authorization_status",
            "safety_labels",
        ],
        required_data=[
            _PAPER_OBSERVATION_READINESS_FILENAME,
            "Daniel-scoped hard gate before any future read-only observation",
        ],
        expected_artifact_or_command=_PAPER_OBSERVATION_READINESS_FILENAME,
        priority="P2",
        status="blocked",
        blocked_by=["broker_state_not_observed", "paper_submit_not_authorized"],
        safety_scope="offline_readiness_metadata_only_no_broker_access_no_submit",
        requires_daniel=True,
        hard_gate_required=True,
        promotion_criteria=[
            "readiness criteria are documented without observing broker state",
            "Daniel explicitly scopes any later hard gate outside this command",
        ],
        rejection_criteria=[
            "readiness work asks for protected broker material",
            "readiness work recommends order or capital action",
        ],
        next_safe_test="review research_candidate_queue.jsonl and operating_brief.md only",
    )


def _strategy_candidate_intake_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _research_candidate_item(
        candidate_id="strategy_candidate_intake_requirements",
        candidate_type="strategy_intake",
        title="Define strategy candidate intake requirements",
        hypothesis=(
            "Future strategy work should enter through a fixed evidence intake "
            "checklist instead of manual intuition or milestone churn."
        ),
        rationale=(
            "The current product is the assistant, not indefinite expansion of "
            "the active SMA baseline."
        ),
        evidence_sources=["research_board.future_candidate_strategy_slot"],
        required_data=[
            "candidate hypothesis",
            "required offline data",
            "benchmark expectation",
            "safety and dependency-direction review",
        ],
        expected_artifact_or_command="future offline strategy_candidate_intake.md",
        priority="P3",
        status="queued",
        blocked_by=[],
        safety_scope="offline_metadata_only_no_strategy_code_no_broker_access",
        requires_daniel=False,
        hard_gate_required=False,
        promotion_criteria=[
            "intake rejects candidates without offline evidence requirements",
            "intake preserves no broker, network, LLM, or runtime agent calls",
        ],
        rejection_criteria=["intake weakens live-mode or paper-submit lockout"],
        next_safe_test="python -m pytest tests\\unit\\test_dependency_direction.py",
    )


def _future_non_sma_strategy_slot_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _research_candidate_item(
        candidate_id="future_non_sma_strategy_research_slot",
        candidate_type="future_strategy_slot",
        title="Reserve blocked non-SMA strategy research slot",
        hypothesis=(
            "The assistant can acknowledge future non-SMA research without "
            "implementing it before evidence requirements are defined."
        ),
        rationale=(
            "A blocked slot prevents endless SMA catalog expansion while keeping "
            "future research visible."
        ),
        evidence_sources=["research_board.future_candidate_strategy_slot"],
        required_data=[
            "approved candidate definition",
            "offline evidence requirements",
            "promotion and rejection criteria",
        ],
        expected_artifact_or_command=(
            "no implementation until evidence requirements are defined"
        ),
        priority="P3",
        status="blocked",
        blocked_by=[
            "candidate_definition_missing",
            "evidence_requirements_missing",
        ],
        safety_scope="metadata_only_no_strategy_code_no_broker_access",
        requires_daniel=True,
        hard_gate_required=True,
        promotion_criteria=[
            "Daniel/GPT approve a candidate definition",
            "offline evidence requirements are documented first",
        ],
        rejection_criteria=[
            "candidate requires broker access",
            "candidate requires external nonlocal services or protected material",
        ],
        next_safe_test="review strategy_candidate_intake_requirements first",
    )


def _research_candidate_item(
    *,
    candidate_id: str,
    candidate_type: str,
    title: str,
    hypothesis: str,
    rationale: str,
    evidence_sources: list[str],
    required_data: list[str],
    expected_artifact_or_command: str,
    priority: str,
    status: str,
    blocked_by: list[str],
    safety_scope: str,
    requires_daniel: bool,
    hard_gate_required: bool,
    promotion_criteria: list[str],
    rejection_criteria: list[str],
    next_safe_test: str,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "title": title,
        "hypothesis": hypothesis,
        "rationale": rationale,
        "evidence_sources": list(evidence_sources),
        "required_data": list(required_data),
        "expected_artifact_or_command": expected_artifact_or_command,
        "priority": priority,
        "status": status,
        "blocked_by": list(blocked_by),
        "safety_scope": safety_scope,
        "requires_daniel": requires_daniel,
        "hard_gate_required": hard_gate_required,
        "promotion_criteria": list(promotion_criteria),
        "rejection_criteria": list(rejection_criteria),
        "next_safe_test": next_safe_test,
    }


def _first_safe_research_candidate_from_list(
    candidates: list[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for candidate in candidates:
        if candidate.get("priority") not in {"P2", "P3"}:
            continue
        if candidate.get("status") != "queued":
            continue
        if candidate.get("requires_daniel") is not False:
            continue
        if candidate.get("hard_gate_required") is not False:
            continue
        if _research_candidate_contains_forbidden_term(candidate):
            continue
        return candidate
    return None


def _first_safe_research_candidate(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    queue = payload.get("research_candidate_queue")
    if not isinstance(queue, Mapping):
        return None
    candidates = queue.get("candidates")
    if not isinstance(candidates, list):
        return None
    candidate_mappings = [item for item in candidates if isinstance(item, Mapping)]
    return _first_safe_research_candidate_from_list(candidate_mappings)


def _research_candidate_by_id(
    payload: Mapping[str, Any],
    candidate_id: str,
) -> Mapping[str, Any] | None:
    queue = payload.get("research_candidate_queue")
    if not isinstance(queue, Mapping):
        return None
    candidates = queue.get("candidates")
    if not isinstance(candidates, list):
        return None
    for candidate in candidates:
        if isinstance(candidate, Mapping) and candidate.get("candidate_id") == candidate_id:
            return candidate
    return None


def _research_candidate_contains_forbidden_term(candidate: Mapping[str, Any]) -> bool:
    candidate_text = json.dumps(
        _json_safe(candidate),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    return any(term in candidate_text for term in _RESEARCH_CANDIDATE_FORBIDDEN_TERMS)


def _write_research_candidate_queue_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    queue = payload.get("research_candidate_queue")
    candidates: Any = []
    if isinstance(queue, Mapping):
        candidates = queue.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    line_values = [
        item for item in candidates if isinstance(item, Mapping)
    ]
    lines = [
        json.dumps(_json_safe(item), sort_keys=True, separators=(",", ":"))
        for item in line_values
    ]
    (output_root / _RESEARCH_CANDIDATE_QUEUE_FILENAME).write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
        newline="\n",
    )


def _write_baseline_health_evaluation_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    evaluation = payload.get("baseline_health_evaluation")
    record = evaluation if isinstance(evaluation, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _BASELINE_HEALTH_EVALUATION_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_baseline_evidence_metrics_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    metrics = payload.get("baseline_evidence_metrics")
    record = metrics if isinstance(metrics, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _BASELINE_EVIDENCE_METRICS_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_paper_observation_readiness_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    readiness = payload.get("paper_observation_readiness")
    record = readiness if isinstance(readiness, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _PAPER_OBSERVATION_READINESS_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_research_board_prioritization_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    prioritization = payload.get("research_board_prioritization")
    record = prioritization if isinstance(prioritization, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _RESEARCH_BOARD_PRIORITIZATION_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


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
                    "metrics packet for the existing baseline."
                ),
                reason_codes=[
                    "research_confidence_not_quantified",
                    "active_baseline_confidence_gap",
                    "offline_research_backlog",
                ],
                blocked_by=["strategy_confidence_not_yet_quantified"],
                requires_daniel=False,
                hard_gate_required=False,
                expected_artifact_or_command=_baseline_metric_command_from_payload(
                    payload
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


def _baseline_metric_command_from_payload(payload: Mapping[str, Any]) -> str:
    artifact_paths = payload.get("artifact_paths")
    if isinstance(artifact_paths, Mapping) and artifact_paths.get(
        "baseline_evidence_metrics"
    ):
        return _baseline_evidence_next_safe_metric_command(artifact_paths)
    return _baseline_evidence_next_safe_metric_command(
        _artifact_paths(Path("runs/daily_lab/latest"))
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
    research_candidate_queue_defaults = _default_research_candidate_queue_fields(
        artifact_paths
    )
    baseline_health_evaluation_defaults = (
        _default_baseline_health_evaluation_fields(artifact_paths)
    )
    baseline_evidence_metrics_defaults = _default_baseline_evidence_metrics_fields(
        artifact_paths
    )
    paper_observation_readiness_defaults = (
        _default_paper_observation_readiness_fields(artifact_paths)
    )
    research_board_prioritization_defaults = (
        _default_research_board_prioritization_fields(artifact_paths)
    )
    next_action_selector_defaults = _default_next_action_selector_fields(
        artifact_paths
    )
    work_order_export_defaults = _default_work_order_export_fields(artifact_paths)
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
        **research_candidate_queue_defaults,
        **baseline_evidence_metrics_defaults,
        **paper_observation_readiness_defaults,
        **research_board_prioritization_defaults,
        **baseline_health_evaluation_defaults,
        **next_action_selector_defaults,
        **work_order_export_defaults,
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
            "research_candidate_queue": artifact_paths["research_candidate_queue"],
            "baseline_health_evaluation": artifact_paths[
                "baseline_health_evaluation"
            ],
            "baseline_evidence_metrics": artifact_paths[
                "baseline_evidence_metrics"
            ],
            "paper_observation_readiness": artifact_paths[
                "paper_observation_readiness"
            ],
            "research_board_prioritization": artifact_paths[
                "research_board_prioritization"
            ],
            "review_inputs": artifact_paths["review_inputs"],
            "work_orders": artifact_paths["work_orders"],
            "gpt_next_action_handoff": artifact_paths[
                "gpt_next_action_handoff"
            ],
            "codex_work_order": artifact_paths["codex_work_order"],
            "antigravity_review_order": artifact_paths[
                "antigravity_review_order"
            ],
            "claude_critique_order": artifact_paths["claude_critique_order"],
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
            "research_candidate_queue_path": research_candidate_queue_defaults[
                "research_candidate_queue_path"
            ],
            "research_candidate_queue": dict(
                research_candidate_queue_defaults["research_candidate_queue"]
            ),
            "baseline_health_evaluation_path": (
                baseline_health_evaluation_defaults[
                    "baseline_health_evaluation_path"
                ]
            ),
            "baseline_health_evaluation": dict(
                baseline_health_evaluation_defaults["baseline_health_evaluation"]
            ),
            "baseline_evidence_metrics_path": baseline_evidence_metrics_defaults[
                "baseline_evidence_metrics_path"
            ],
            "baseline_evidence_metrics": dict(
                baseline_evidence_metrics_defaults["baseline_evidence_metrics"]
            ),
            "paper_observation_readiness_path": (
                paper_observation_readiness_defaults[
                    "paper_observation_readiness_path"
                ]
            ),
            "paper_observation_readiness": dict(
                paper_observation_readiness_defaults[
                    "paper_observation_readiness"
                ]
            ),
            "research_board_prioritization_path": (
                research_board_prioritization_defaults[
                    "research_board_prioritization_path"
                ]
            ),
            "research_board_prioritization": dict(
                research_board_prioritization_defaults[
                    "research_board_prioritization"
                ]
            ),
            "next_action_selector": dict(
                next_action_selector_defaults["next_action_selector"]
            ),
            "work_order_exports": dict(
                work_order_export_defaults["work_order_exports"]
            ),
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


def _materialize_turnover_and_cost_model_artifacts(
    *,
    output_root: Path,
    config: EtfSmaDailyPaperLabConfig,
    payload: Mapping[str, Any],
) -> None:
    bars_path = Path(config.bars_csv)
    bars = _load_bars(bars_path, config.symbol)
    as_of_dt = datetime.combine(
        datetime.fromisoformat(str(payload["as_of_date"])).date(),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    turnover_record = _build_turnover_summary_record(
        bars=bars,
        bars_path=bars_path,
        symbol=config.symbol,
        fast_window=config.sma_fast_window,
        slow_window=config.sma_slow_window,
        as_of_dt=as_of_dt,
    )
    turnover_path = output_root / _BASELINE_TURNOVER_SUMMARY_FILENAME
    _write_jsonl_record(turnover_path, turnover_record)
    turnover_hash = _sha256_file(turnover_path)

    cost_model_record = _build_cost_model_summary_record(
        bars_path=bars_path,
        turnover_record=turnover_record,
        turnover_path=turnover_path,
        turnover_hash=turnover_hash,
    )
    _write_jsonl_record(
        output_root / _BASELINE_COST_MODEL_SUMMARY_FILENAME,
        cost_model_record,
    )


def _build_turnover_summary_record(
    *,
    bars: list[Bar],
    bars_path: Path,
    symbol: str,
    fast_window: int,
    slow_window: int,
    as_of_dt: datetime,
) -> dict[str, Any]:
    as_of_bars = sorted(
        (
            bar
            for bar in bars
            if bar.symbol == symbol and bar.timestamp <= as_of_dt
        ),
        key=lambda bar: bar.timestamp,
    )
    posture_series = _daily_sma_posture_series(
        as_of_bars,
        fast_window=fast_window,
        slow_window=slow_window,
    )
    signal_change_count = 0
    for previous, current in zip(posture_series, posture_series[1:]):
        if previous["posture"] != current["posture"]:
            signal_change_count += 1

    initial_entry_count = (
        1
        if posture_series and posture_series[0]["posture"] == "risk_on"
        else 0
    )
    estimated_trade_count = signal_change_count + initial_entry_count
    sample_row_count = len(posture_series)
    if sample_row_count:
        status = "turnover_summary_materialized_from_daily_signal_transitions"
        sample_window_start = str(posture_series[0]["date"])
        sample_window_end = str(posture_series[-1]["date"])
        missing_source_detail: list[str] = []
    else:
        status = "turnover_summary_partial_insufficient_slow_window_history"
        sample_window_start = "not_available_insufficient_history"
        sample_window_end = "not_available_insufficient_history"
        missing_source_detail = [
            f"requires_at_least_{slow_window}_usable_as_of_bars",
            f"usable_as_of_bar_count={len(as_of_bars)}",
        ]

    return {
        "baseline_id": "spy_sma_50_200_daily_long_only",
        "active_symbol": symbol,
        "active_strategy": "SMA 50/200",
        "as_of_date": as_of_dt.strftime("%Y-%m-%d"),
        "turnover_summary_status": status,
        "turnover_metric_basis": (
            "daily_sma_50_200_signal_transition_count_from_local_bars; "
            "estimated_trade_count assumes a flat starting exposure and counts "
            "an initial risk-on entry plus subsequent posture transitions; no "
            "broker fills, quantities, notional turnover, or profitability are inferred"
        ),
        "signal_change_count": signal_change_count,
        "estimated_trade_count": estimated_trade_count,
        "estimated_trade_count_basis": (
            "conservative_signal_transition_count_not_broker_order_count"
        ),
        "sample_window_start": sample_window_start,
        "sample_window_end": sample_window_end,
        "sample_row_count": sample_row_count,
        "missing_source_detail": missing_source_detail,
        "source_artifact_paths": {
            "input_bars_csv": _normalize_path(bars_path),
        },
        "source_artifact_hashes": {
            "input_bars_csv": _sha256_file(bars_path),
        },
        "profit_claim": "none",
        "safety_scope": (
            "offline_preview_only_no_broker_access_no_submit_no_profit_claim_"
            "broker_state_not_observed"
        ),
    }


def _daily_sma_posture_series(
    bars: list[Bar],
    *,
    fast_window: int,
    slow_window: int,
) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for index in range(slow_window - 1, len(bars)):
        fast_slice = bars[index - fast_window + 1 : index + 1]
        slow_slice = bars[index - slow_window + 1 : index + 1]
        fast_value = sum((bar.close for bar in fast_slice), Decimal("0")) / Decimal(
            fast_window
        )
        slow_value = sum((bar.close for bar in slow_slice), Decimal("0")) / Decimal(
            slow_window
        )
        series.append(
            {
                "date": bars[index].timestamp.strftime("%Y-%m-%d"),
                "posture": "risk_on" if fast_value > slow_value else "risk_off",
            }
        )
    return series


def _build_cost_model_summary_record(
    *,
    bars_path: Path,
    turnover_record: Mapping[str, Any],
    turnover_path: Path,
    turnover_hash: str,
) -> dict[str, Any]:
    turnover_status = str(
        turnover_record.get("turnover_summary_status", "turnover_summary_missing")
    )
    if turnover_status.startswith("turnover_summary_materialized"):
        status = "cost_model_summary_materialized_assumptions_only"
        missing_source_detail = [
            "real_fill_prices_not_observed",
            "bid_ask_spread_or_quote_data_not_available",
            "commission_schedule_not_encoded_in_offline_packet",
        ]
    else:
        status = "cost_model_summary_partial_waiting_for_turnover_summary"
        missing_source_detail = [
            "turnover_summary_not_fully_materialized",
            "real_fill_prices_not_observed",
            "bid_ask_spread_or_quote_data_not_available",
            "commission_schedule_not_encoded_in_offline_packet",
        ]

    return {
        "baseline_id": "spy_sma_50_200_daily_long_only",
        "active_symbol": str(turnover_record.get("active_symbol", _DEFAULT_SYMBOL)),
        "active_strategy": "SMA 50/200",
        "as_of_date": str(turnover_record.get("as_of_date", "as_of_date_missing")),
        "cost_model_summary_status": status,
        "cost_model_basis": (
            "assumption_inventory_only_from_offline_turnover_summary; no dollar "
            "cost estimate is computed without fills, quotes, spread data, "
            "trade notional, and an explicit commission schedule"
        ),
        "commission_assumption": (
            "not_estimated_commission_schedule_not_encoded_in_offline_packet"
        ),
        "spread_slippage_assumption": (
            "not_estimated_requires_fill_or_quote_spread_data"
        ),
        "estimated_cost_per_trade_status": (
            "not_computed_requires_commission_schedule_and_fill_or_spread_data"
        ),
        "estimated_total_cost_status": (
            "not_computed_requires_real_fill_data_trade_notional_spread_or_commission_schedule"
        ),
        "estimated_trade_count_source": "turnover_summary.estimated_trade_count",
        "estimated_trade_count": turnover_record.get("estimated_trade_count"),
        "requires_real_fill_data": True,
        "missing_source_detail": missing_source_detail,
        "source_artifact_paths": {
            "input_bars_csv": _normalize_path(bars_path),
            "turnover_summary": _normalize_path(turnover_path),
        },
        "source_artifact_hashes": {
            "input_bars_csv": _sha256_file(bars_path),
            "turnover_summary": turnover_hash,
        },
        "profit_claim": "none",
        "safety_scope": (
            "offline_preview_only_no_broker_access_no_submit_no_profit_claim_"
            "broker_state_not_observed"
        ),
    }


def _write_jsonl_record(path: Path, record: Mapping[str, Any]) -> None:
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(line, encoding="utf-8", newline="\n")


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
    work_orders_dir = output_root / _WORK_ORDERS_DIRNAME
    return {
        "assistant_brief": _normalize_path(output_root / _BRIEF_FILENAME),
        "operating_record": _normalize_path(output_root / _RECORD_FILENAME),
        "manifest": _normalize_path(output_root / _MANIFEST_FILENAME),
        "history_ledger": _normalize_path(output_root / _HISTORY_LEDGER_FILENAME),
        "review_handoff": _normalize_path(output_root / _REVIEW_HANDOFF_FILENAME),
        "decision_ledger": _normalize_path(output_root / _DECISION_LEDGER_FILENAME),
        "research_candidate_queue": _normalize_path(
            output_root / _RESEARCH_CANDIDATE_QUEUE_FILENAME
        ),
        "baseline_health_evaluation": _normalize_path(
            output_root / _BASELINE_HEALTH_EVALUATION_FILENAME
        ),
        "baseline_evidence_metrics": _normalize_path(
            output_root / _BASELINE_EVIDENCE_METRICS_FILENAME
        ),
        "paper_observation_readiness": _normalize_path(
            output_root / _PAPER_OBSERVATION_READINESS_FILENAME
        ),
        "research_board_prioritization": _normalize_path(
            output_root / _RESEARCH_BOARD_PRIORITIZATION_FILENAME
        ),
        "review_inputs": _normalize_path(output_root / _REVIEW_INPUTS_DIRNAME),
        "work_orders": _normalize_path(work_orders_dir),
        "gpt_next_action_handoff": _normalize_path(
            work_orders_dir / _GPT_WORK_ORDER_FILENAME
        ),
        "codex_work_order": _normalize_path(
            work_orders_dir / _CODEX_WORK_ORDER_FILENAME
        ),
        "antigravity_review_order": _normalize_path(
            work_orders_dir / _ANTIGRAVITY_WORK_ORDER_FILENAME
        ),
        "claude_critique_order": _normalize_path(
            work_orders_dir / _CLAUDE_WORK_ORDER_FILENAME
        ),
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


def _default_research_candidate_queue_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    readiness = _build_paper_observation_readiness({}, artifact_paths)
    return {
        "research_candidate_queue_version": _RESEARCH_CANDIDATE_QUEUE_VERSION,
        "research_candidate_queue_path": str(
            artifact_paths["research_candidate_queue"]
        ),
        "research_candidate_queue": {
            "research_candidate_queue_version": _RESEARCH_CANDIDATE_QUEUE_VERSION,
            "status": "not_generated",
            "artifact_path": str(artifact_paths["research_candidate_queue"]),
            "generation_mode": "deterministic_offline_from_packet_evidence",
            "priority_rules": {
                "P0": "safety invariant or quality gate failure",
                "P1": "missing operator/data/review evidence required to interpret current packet",
                "P2": "offline research work that improves strategy evaluation",
                "P3": "backlog or future enhancements",
            },
            "candidate_count": 0,
            "top_candidate_id": None,
            "top_candidate_priority": None,
            "top_candidate_title": None,
            "selected_safe_candidate_id": None,
            "selected_safe_candidate_priority": None,
            "selected_safe_candidate_title": None,
            "paper_observation_readiness_path": str(
                artifact_paths["paper_observation_readiness"]
            ),
            "paper_observation_readiness": dict(readiness),
            "candidates": [],
        },
    }


def _default_baseline_health_evaluation_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    next_safe_metric_command = _baseline_evidence_next_safe_metric_command(
        artifact_paths
    )
    readiness = _build_paper_observation_readiness({}, artifact_paths)
    return {
        "baseline_health_evaluation_version": _BASELINE_HEALTH_EVALUATION_VERSION,
        "baseline_health_evaluation_path": str(
            artifact_paths["baseline_health_evaluation"]
        ),
        "baseline_health_evaluation": {
            "baseline_health_evaluation_version": (
                _BASELINE_HEALTH_EVALUATION_VERSION
            ),
            "status": "not_generated",
            "artifact_path": str(artifact_paths["baseline_health_evaluation"]),
            "generation_mode": "deterministic_offline_from_packet_evidence",
            "baseline_id": "spy_sma_50_200_daily_long_only",
            "baseline_name": "SPY SMA 50/200 daily long-only baseline",
            "baseline_role": "controlled_baseline_harness_for_assistant_evaluation",
            "active_symbol": _DEFAULT_SYMBOL,
            "active_strategy": "SMA 50/200",
            "as_of_date": "not_evaluated",
            "posture_status": "not_evaluated",
            "preview_decision": "not_evaluated",
            "broker_state_mode": "broker_state_not_observed",
            "blocker_status": "broker_state_not_observed",
            "quality_gate_status": "not_evaluated",
            "decision_ledger_status": "decision_ledger_no_review_input",
            "research_candidate_queue_status": "not_generated",
            "health_status": "evidence_incomplete",
            "confidence_status": "confidence_not_yet_quantified",
            "evidence_status": "not_evaluated",
            "baseline_evidence_metrics_status": "not_generated",
            "baseline_evidence_snapshot_status": "metrics_missing",
            "baseline_metric_confidence_status": "confidence_not_yet_quantified",
            "baseline_metric_artifact_ingest_status": "metric_artifacts_missing",
            "baseline_metric_artifact_parse_status": {
                artifact_id: "missing"
                for artifact_id, _filename in _BASELINE_METRIC_ARTIFACTS
            },
            "baseline_remaining_missing_metric_sources": [],
            "paper_observation_readiness_path": str(
                artifact_paths["paper_observation_readiness"]
            ),
            "paper_observation_readiness": dict(readiness),
            "baseline_evidence_metrics_path": str(
                artifact_paths["baseline_evidence_metrics"]
            ),
            "next_safe_metric_command": next_safe_metric_command,
            "paper_submit_readiness_status": "not_ready_for_paper_submit",
            "known_strengths": [],
            "known_weaknesses": [],
            "missing_evidence": [],
            "required_next_artifacts": [],
            "next_safe_test": _BASELINE_HEALTH_NEXT_SAFE_TEST,
            "promotion_criteria": [],
            "deprecation_criteria": [],
            "replacement_research_status": "replacement_research_not_evaluated",
            "requires_daniel": False,
            "hard_gate_required": False,
            "safety_scope": (
                "offline_preview_only_no_broker_access_no_submit_no_profit_claim"
            ),
        },
    }


def _default_baseline_evidence_metrics_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    next_artifacts = _baseline_metric_next_artifacts(artifact_paths)
    output_root = _artifact_output_root(artifact_paths["baseline_evidence_metrics"])
    readiness = _build_paper_observation_readiness({}, artifact_paths)
    artifact_paths_by_id = {
        artifact_id: _normalize_path(output_root / filename)
        for artifact_id, filename in _BASELINE_METRIC_ARTIFACTS
    }
    missing_sources = [
        "offline_backtest_confidence_summary",
        "buy_and_hold_benchmark_status",
        "drawdown_summary",
        "turnover_summary",
        "cost_model_summary",
        "paper_observation_summary",
        "input_csv.adjusted_close_column",
    ]
    return {
        "baseline_evidence_metrics_version": _BASELINE_EVIDENCE_METRICS_VERSION,
        "baseline_evidence_metrics_path": str(
            artifact_paths["baseline_evidence_metrics"]
        ),
        "baseline_evidence_metrics": {
            "baseline_evidence_metrics_version": _BASELINE_EVIDENCE_METRICS_VERSION,
            "status": "not_generated",
            "artifact_path": str(artifact_paths["baseline_evidence_metrics"]),
            "generation_mode": "deterministic_offline_from_packet_evidence",
            "baseline_id": "spy_sma_50_200_daily_long_only",
            "baseline_name": "SPY SMA 50/200 daily long-only baseline",
            "active_symbol": _DEFAULT_SYMBOL,
            "active_strategy": "SMA 50/200",
            "as_of_date": "not_evaluated",
            "evidence_snapshot_status": "metrics_missing",
            "metric_confidence_status": "confidence_not_yet_quantified",
            "metric_artifact_ingest_status": "metric_artifacts_missing",
            "turnover_artifact_ingest_status": "turnover_artifact_missing",
            "cost_model_artifact_ingest_status": "cost_model_artifact_missing",
            "metric_artifact_paths": artifact_paths_by_id,
            "metric_artifact_hashes": {},
            "metric_artifact_parse_status": {
                artifact_id: "missing"
                for artifact_id, _filename in _BASELINE_METRIC_ARTIFACTS
            },
            "metric_artifact_record_count": {
                artifact_id: 0 for artifact_id, _filename in _BASELINE_METRIC_ARTIFACTS
            },
            "turnover_artifact_path": artifact_paths_by_id["turnover_summary"],
            "cost_model_artifact_path": artifact_paths_by_id["cost_model_summary"],
            "turnover_artifact_hash": None,
            "cost_model_artifact_hash": None,
            "turnover_artifact_parse_status": "missing",
            "cost_model_artifact_parse_status": "missing",
            "available_metric_sources": [],
            "missing_metric_sources": list(missing_sources),
            "backtest_confidence_summary_status": "metrics_missing",
            "benchmark_metric_status": "metrics_missing",
            "benchmark_comparison_status": "metrics_missing",
            "backtest_metric_status": "metrics_missing",
            "drawdown_metric_status": "metrics_missing",
            "turnover_metric_status": "metrics_missing",
            "cost_model_status": "metrics_missing",
            "sample_window_status": "metrics_missing",
            "adjusted_close_basis_status": "metrics_missing",
            "quantified_metric_summary": {},
            "remaining_missing_metric_sources": list(missing_sources),
            "paper_observation_status": "broker_state_not_observed",
            "paper_observation_readiness_path": str(
                artifact_paths["paper_observation_readiness"]
            ),
            "paper_observation_readiness": dict(readiness),
            "broker_state_mode": "broker_state_not_observed",
            "paper_submit_readiness_status": "not_ready_for_paper_submit",
            "profit_claim": "none",
            "required_next_artifacts": next_artifacts,
            "artifact_prerequisite_chain": _baseline_metric_prerequisite_chain(
                artifact_paths
            ),
            "next_safe_metric_command": _baseline_evidence_next_safe_metric_command(
                artifact_paths
            ),
            "promotion_criteria": [],
            "deprecation_criteria": [],
            "requires_daniel": False,
            "hard_gate_required": False,
            "safety_scope": (
                "offline_preview_only_no_broker_access_no_submit_no_profit_claim_"
                "broker_state_not_observed"
            ),
        },
    }


def _build_research_board_prioritization(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    ranked_candidates = [
        {
            "candidate_id": "build_offline_strategy_comparison_scaffold",
            "priority": "P2",
            "status": "active",
            "requires_daniel_approval": False,
            "rationale": "Build offline scaffold for strategy comparison."
        },
        {
            "candidate_id": "prepare_candidate_strategy_evidence_template",
            "priority": "P2",
            "status": "active",
            "requires_daniel_approval": False,
            "rationale": "Template preparation for strategy evidence collection."
        },
        {
            "candidate_id": "paper_observation_readiness_deferred",
            "priority": "P3",
            "status": "deferred",
            "requires_daniel_approval": True,
            "rationale": "Deferred broker observation requires Daniel's hard-gate approval."
        }
    ]
    return {
        "research_board_prioritization_version": _RESEARCH_BOARD_PRIORITIZATION_VERSION,
        "prioritization_status": "ranked",
        "research_mode": "offline_research_planning_only",
        "candidate_count": len(ranked_candidates),
        "ranking_method": "deterministic_offline_safety_hierarchy",
        "ranking_weights": {
            "safety_priority": 1.0,
            "offline_feasibility": 1.0,
            "daniel_approval_deferral": -1.0
        },
        "ranked_candidates": ranked_candidates,
        "top_candidate": "build_offline_strategy_comparison_scaffold",
        "selected_next_safe_action": "build_offline_strategy_comparison_scaffold",
        "why_selected": "The top candidate is offline-only, feasible, and does not require Daniel's active gate approval.",
        "why_not_broker_observation_yet": "Broker reads require Daniel's explicit scoped approval later.",
        "hard_gate_required": False,
        "requires_daniel": False,
        "daniel_action_required_now": False,
        "safety_scope": "offline_only",
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "profit_claim": "none",
    }


def _default_research_board_prioritization_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    prioritization = _build_research_board_prioritization({}, artifact_paths)
    return {
        "research_board_prioritization_version": _RESEARCH_BOARD_PRIORITIZATION_VERSION,
        "research_board_prioritization_path": str(
            artifact_paths["research_board_prioritization"]
        ),
        "research_board_prioritization": prioritization,
    }


def _research_board_prioritization_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    prioritization = payload.get("research_board_prioritization")
    if isinstance(prioritization, Mapping):
        return dict(prioritization)
    return _build_research_board_prioritization(payload, artifact_paths)


def _apply_research_board_prioritization(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    prioritization = _build_research_board_prioritization(payload, artifact_paths)
    payload["research_board_prioritization_version"] = _RESEARCH_BOARD_PRIORITIZATION_VERSION
    payload["research_board_prioritization_path"] = str(
        artifact_paths["research_board_prioritization"]
    )
    payload["research_board_prioritization"] = prioritization
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["research_board_prioritization_path"] = payload[
            "research_board_prioritization_path"
        ]
        dashboard["research_board_prioritization"] = dict(prioritization)


def _default_paper_observation_readiness_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    readiness = _build_paper_observation_readiness({}, artifact_paths)
    readiness["status"] = "not_generated"
    readiness["readiness_status"] = "offline_readiness_packet_not_generated"
    return {
        "paper_observation_readiness_version": (
            _PAPER_OBSERVATION_READINESS_VERSION
        ),
        "paper_observation_readiness_path": str(
            artifact_paths["paper_observation_readiness"]
        ),
        "paper_observation_readiness": readiness,
    }


def _build_paper_observation_readiness(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    broker_state_mode = str(
        payload.get("broker_state_mode", "broker_state_not_observed")
    )
    if broker_state_mode != "broker_state_not_observed":
        broker_state_mode = "broker_state_not_observed"
    return {
        "paper_observation_readiness_version": (
            _PAPER_OBSERVATION_READINESS_VERSION
        ),
        "status": "generated",
        "artifact_path": str(artifact_paths["paper_observation_readiness"]),
        "generation_mode": "deterministic_offline_hard_gate_packet",
        "readiness_status": "hard_gate_prepared_not_authorized",
        "remaining_gap": "paper_observation_summary",
        "hard_gate_required": True,
        "requires_daniel": True,
        "approval_phrase_required": _PAPER_OBSERVATION_APPROVAL_PHRASE,
        "allowed_future_read_operations": [
            "account_clock_status_read_if_needed",
            "SPY_position_read",
            "SPY_open_order_read",
            "latest_paper_portfolio_snapshot_read",
        ],
        "forbidden_future_operations": [
            "submit",
            "cancel",
            "replace",
            "close",
            "close_all_positions",
            "liquidate",
            "delete",
            "retry mutation",
            "live trading",
        ],
        "required_preflight_booleans": {
            "APP_PROFILE_is_paper": False,
            "ALPACA_API_KEY_loaded": False,
            "ALPACA_API_SECRET_KEY_loaded": False,
            "ALPACA_SECRET_KEY_loaded": False,
            "APCA_API_KEY_ID_loaded": False,
            "APCA_API_SECRET_KEY_loaded": False,
        },
        "expected_output_artifacts": [
            _PAPER_OBSERVATION_READINESS_FILENAME,
            "future_paper_observation_summary.jsonl_after_explicit_approval",
            "future_operating_record_and_manifest_broker_state_evidence",
        ],
        "stop_conditions": [
            "any_required_preflight_boolean_is_true",
            "approval_phrase_missing_or_changed",
            "requested_scope_expands_beyond_SPY_read_only_observation",
            "requested_action_is_submit_cancel_replace_close_close_all_positions_liquidate_delete_or_retry_mutation",
            "live_trading_requested",
            "paper_or_live_mode_change_requested",
            "credential_value_would_be_printed",
            "broker_response_is_ambiguous",
            "broker_read_attempted_during_this_offline_readiness_milestone",
        ],
        "broker_state_claim_policy": {
            "current_mode": broker_state_mode,
            "claim_status": "broker_state_not_observed",
            "position_state_claims_allowed": False,
            "open_order_state_claims_allowed": False,
            "policy": (
                "State only that broker state was not observed; do not infer "
                "position or open-order state until a separately approved "
                "read-only observation artifact exists."
            ),
            "forbidden_claim_types": [
                "position_absence_claim",
                "open_order_absence_claim",
                "cash_or_equity_claim_without_read",
                "broker_state_present_tense_claim",
            ],
        },
        "broker_reads_performed": False,
        "broker_mutation_performed": False,
        "runtime_callouts_performed": False,
        "network_calls_performed": False,
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "safety_scope": "offline_only",
        "broker_state_mode": broker_state_mode,
    }


def _paper_observation_readiness_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    readiness = payload.get("paper_observation_readiness")
    if isinstance(readiness, Mapping):
        return dict(readiness)
    return _build_paper_observation_readiness(payload, artifact_paths)


def _default_next_action_selector_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    readiness = _build_paper_observation_readiness({}, artifact_paths)
    return {
        "next_action_selector": {
            "next_action_selector_version": _NEXT_ACTION_SELECTOR_VERSION,
            "status": "not_evaluated",
            "priority": "P3",
            "selected_next_action_id": "prepare_daily_packet_for_quality_gate",
            "selected_next_action_type": "packet_preparation",
            "selected_work_order": "gpt_next_action_handoff",
        "selected_work_order_path": str(artifact_paths["gpt_next_action_handoff"]),
        "selected_owner": "GPT",
        "selected_research_candidate_id": None,
        "selected_research_candidate_priority": None,
        "selected_research_candidate_title": None,
        "research_candidate_queue_path": str(
            artifact_paths["research_candidate_queue"]
        ),
        "rationale": "Packet artifacts have not completed final quality-gate evaluation.",
        "reason_codes": ["quality_gate_not_yet_evaluated"],
            "blocks_offline_build": False,
            "requires_daniel": False,
            "hard_gate_required": False,
            "broker_action_allowed": False,
            "capital_action_allowed": False,
            "llm_runtime_calls_allowed": False,
            "network_runtime_calls_allowed": False,
            "safety_scope": "offline_text_artifacts_only_no_broker_no_network_no_submit",
            "forbidden_actions": _forbidden_behavior_lines(),
            "paper_observation_readiness_path": str(
                artifact_paths["paper_observation_readiness"]
            ),
            "paper_observation_readiness": dict(readiness),
            "source_state": {},
        }
    }


def _default_work_order_export_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    output_root = _artifact_output_root(artifact_paths["baseline_evidence_metrics"])
    readiness = _build_paper_observation_readiness({}, artifact_paths)
    prioritization = _build_research_board_prioritization({}, artifact_paths)
    return {
        "work_order_exports": {
            "work_order_exports_version": _WORK_ORDER_EXPORTS_VERSION,
            "status": "not_generated",
            "directory": str(artifact_paths["work_orders"]),
            "artifact_count": len(_WORK_ORDER_ARTIFACTS),
            "generation_mode": "deterministic_offline_markdown_only",
            "runtime_callouts_performed": False,
            "research_candidate_queue_path": str(
                artifact_paths["research_candidate_queue"]
            ),
            "baseline_evidence_metrics_path": str(
                artifact_paths["baseline_evidence_metrics"]
            ),
            "paper_observation_readiness_path": str(
                artifact_paths["paper_observation_readiness"]
            ),
            "paper_observation_readiness": dict(readiness),
            "paper_observation_readiness_status": str(
                readiness["readiness_status"]
            ),
            "research_board_prioritization_path": str(
                artifact_paths["research_board_prioritization"]
            ),
            "research_board_prioritization": dict(prioritization),
            "research_board_prioritization_status": str(
                prioritization["prioritization_status"]
            ),
            "turnover_artifact_ingest_status": "turnover_artifact_missing",
            "cost_model_artifact_ingest_status": "cost_model_artifact_missing",
            "turnover_metric_status": "metrics_missing",
            "cost_model_status": "metrics_missing",
            "turnover_artifact_path": _normalize_path(
                output_root / _BASELINE_TURNOVER_SUMMARY_FILENAME
            ),
            "cost_model_artifact_path": _normalize_path(
                output_root / _BASELINE_COST_MODEL_SUMMARY_FILENAME
            ),
            "turnover_artifact_hash": None,
            "cost_model_artifact_hash": None,
            "turnover_artifact_parse_status": "missing",
            "cost_model_artifact_parse_status": "missing",
            "next_safe_metric_command": _baseline_evidence_next_safe_metric_command(
                artifact_paths
            ),
            "artifact_prerequisite_chain": _baseline_metric_prerequisite_chain(
                artifact_paths
            ),
            "top_research_candidate_id": None,
            "selected_research_candidate_id": None,
            "safety_scope": "offline_text_export_only_no_broker_no_network_no_llm_calls",
            "artifacts": _work_order_export_artifacts(artifact_paths, "not_generated"),
        }
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


def _apply_next_action_selector(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    selector = _build_next_action_selector(payload, _artifact_paths(output_root))
    payload["next_action_selector"] = selector
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["next_action_selector"] = dict(selector)


def _build_next_action_selector(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    source_state = _selector_source_state(payload)
    action_queue = payload.get("executive_action_queue")
    actions = action_queue if isinstance(action_queue, list) else []
    p0_action = _first_selector_action(actions, priority="P0")
    if p0_action is not None:
        return _selector_result(
            artifact_paths=artifact_paths,
            source_state=source_state,
            status="safety_stop_selected",
            priority="P0",
            selected_next_action_id=str(p0_action.get("action_id")),
            selected_next_action_type="safety_stop",
            selected_work_order="gpt_next_action_handoff",
            selected_owner="GPT",
            rationale=(
                "A P0 executive action is present, so GPT/Daniel source-of-truth "
                "review must happen before any implementation work."
            ),
            reason_codes=["p0_safety_stop_wins", *_selector_action_reasons(p0_action)],
            blocks_offline_build=True,
            requires_daniel=bool(p0_action.get("requires_daniel")),
            hard_gate_required=True,
            selected_research_candidate=_research_candidate_by_id(
                payload,
                "quality_gate_or_safety_invariant_repair",
            ),
        )

    review_classification = str(payload.get("review_classification", "missing"))
    if review_classification in {"needs-repair", "rejected"}:
        repair_action = _first_selector_action(
            actions,
            action_ids=(
                "repair_review_feedback_before_next_packet_use",
                "stop_on_rejected_review_feedback",
            ),
        )
        selected_id = (
            str(repair_action.get("action_id"))
            if repair_action is not None
            else "repair_decision_ledger_feedback"
        )
        return _selector_result(
            artifact_paths=artifact_paths,
            source_state=source_state,
            status="repair_work_order_selected",
            priority="P1",
            selected_next_action_id=selected_id,
            selected_next_action_type="decision_ledger_repair",
            selected_work_order="codex_work_order",
            selected_owner="Codex",
            rationale=(
                "The ingested decision-ledger classification requires offline "
                "packet repair before the packet is relied on."
            ),
            reason_codes=[
                "decision_ledger_input_requires_repair",
                f"review_classification_{review_classification}",
            ],
            blocks_offline_build=True,
            requires_daniel=False,
            hard_gate_required=review_classification == "rejected",
            selected_research_candidate=_research_candidate_by_id(
                payload,
                "offline_packet_review_repair",
            ),
        )

    quality_gate_status = str(payload.get("quality_gate_status", "not_evaluated"))
    if quality_gate_status == "fail":
        return _selector_result(
            artifact_paths=artifact_paths,
            source_state=source_state,
            status="packet_repair_selected",
            priority="P1",
            selected_next_action_id="repair_packet_quality_gate_failure",
            selected_next_action_type="quality_gate_packet_repair",
            selected_work_order="codex_work_order",
            selected_owner="Codex",
            rationale=(
                "The quality gate failed, so the next action is deterministic "
                "packet repair inside the offline daily-lab surfaces."
            ),
            reason_codes=["quality_gate_failed", *source_state["quality_gate_failed_checks"]],
            blocks_offline_build=True,
            requires_daniel=False,
            hard_gate_required=False,
            selected_research_candidate=_research_candidate_by_id(
                payload,
                "quality_gate_or_safety_invariant_repair",
            ),
        )

    review_input_status = str(payload.get("review_input_status", "review_input_not_found"))
    if review_input_status in {
        "review_input_not_found",
        "review_input_directory_empty",
    }:
        review_candidate = _research_candidate_by_id(
            payload,
            "offline_review_evidence_gap",
        )
        return _selector_result(
            artifact_paths=artifact_paths,
            source_state=source_state,
            status="operator_support_review_ingest_selected",
            priority=(
                str(review_candidate.get("priority"))
                if review_candidate is not None
                else "P1"
            ),
            selected_next_action_id="collect_offline_review_feedback",
            selected_next_action_type="operator_support_review_ingest",
            selected_work_order="gpt_next_action_handoff",
            selected_owner="GPT",
            rationale=(
                "No offline review input is present. That requests review/feedback "
                "ingest support, but it is not a blocker for safe offline build work."
            ),
            reason_codes=["missing_review_input", "not_build_blocker"],
            blocks_offline_build=False,
            requires_daniel=False,
            hard_gate_required=False,
            selected_research_candidate=review_candidate,
        )

    research_candidate = _first_safe_research_candidate(payload)
    if research_candidate is not None:
        return _selector_result(
            artifact_paths=artifact_paths,
            source_state=source_state,
            status="safe_offline_research_candidate_selected",
            priority=str(research_candidate.get("priority", "P2")),
            selected_next_action_id=str(research_candidate["candidate_id"]),
            selected_next_action_type="research_candidate",
            selected_work_order="codex_work_order",
            selected_owner="Codex",
            rationale=str(research_candidate["rationale"]),
            reason_codes=[
                "quality_gate_passed",
                "decision_ledger_allows_research_candidate",
                f"research_candidate_priority_{research_candidate['priority']}",
                str(research_candidate["candidate_id"]),
            ],
            blocks_offline_build=False,
            requires_daniel=False,
            hard_gate_required=False,
            selected_research_candidate=research_candidate,
        )

    next_safe_action = _first_safe_offline_action(actions)
    if next_safe_action is not None:
        work_order, owner = _work_order_for_action(next_safe_action)
        return _selector_result(
            artifact_paths=artifact_paths,
            source_state=source_state,
            status="safe_offline_action_selected",
            priority=str(next_safe_action.get("priority", "P2")),
            selected_next_action_id=str(next_safe_action.get("action_id")),
            selected_next_action_type=str(next_safe_action.get("action_type")),
            selected_work_order=work_order,
            selected_owner=owner,
            rationale=str(next_safe_action.get("rationale", "Safe offline action selected.")),
            reason_codes=[
                "quality_gate_passed",
                "no_repair_blocker",
                *_selector_action_reasons(next_safe_action),
            ],
            blocks_offline_build=False,
            requires_daniel=bool(next_safe_action.get("requires_daniel")),
            hard_gate_required=bool(next_safe_action.get("hard_gate_required")),
            selected_research_candidate=None,
        )

    return _selector_result(
        artifact_paths=artifact_paths,
        source_state=source_state,
        status="safe_noop_selected",
        priority="P3",
        selected_next_action_id="continue_offline_packet_history",
        selected_next_action_type="noop",
        selected_work_order="gpt_next_action_handoff",
        selected_owner="GPT",
        rationale=(
            "The packet has no higher-priority repair, review, or research action "
            "after deterministic safety filtering."
        ),
        reason_codes=["quality_gate_passed", "no_blocker", "no_safe_action_queued"],
        blocks_offline_build=False,
        requires_daniel=False,
        hard_gate_required=False,
        selected_research_candidate=None,
    )


def _selector_source_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    action_queue = payload.get("executive_action_queue")
    action_ids: list[str] = []
    highest_priority = "P3"
    if isinstance(action_queue, list) and action_queue:
        for item in action_queue:
            if isinstance(item, Mapping):
                action_ids.append(str(item.get("action_id", "action_id_missing")))
        first = action_queue[0]
        if isinstance(first, Mapping):
            highest_priority = str(first.get("priority", highest_priority))
    return {
        "quality_gate_status": str(payload.get("quality_gate_status", "not_evaluated")),
        "quality_gate_failed_checks": [
            str(item) for item in payload.get("quality_gate_failed_checks", [])
        ],
        "decision_ledger_status": str(
            payload.get("decision_ledger_status", "decision_ledger_status_missing")
        ),
        "review_input_status": str(
            payload.get("review_input_status", "review_input_status_missing")
        ),
        "review_classification": str(
            payload.get("review_classification", "classification_missing")
        ),
        "executive_highest_priority": highest_priority,
        "executive_action_ids": action_ids,
        "history_delta_summary": str(
            payload.get("history_delta", {}).get(
                "delta_summary_text",
                "history_delta_missing",
            )
            if isinstance(payload.get("history_delta"), Mapping)
            else "history_delta_missing"
        ),
        "research_candidate_queue_status": str(
            payload.get("research_candidate_queue", {}).get(
                "status",
                "research_candidate_queue_missing",
            )
            if isinstance(payload.get("research_candidate_queue"), Mapping)
            else "research_candidate_queue_missing"
        ),
        "top_research_candidate_id": str(
            payload.get("research_candidate_queue", {}).get(
                "top_candidate_id",
                "top_candidate_missing",
            )
            if isinstance(payload.get("research_candidate_queue"), Mapping)
            else "top_candidate_missing"
        ),
        "selected_safe_research_candidate_id": str(
            payload.get("research_candidate_queue", {}).get(
                "selected_safe_candidate_id",
                "selected_safe_candidate_missing",
            )
            if isinstance(payload.get("research_candidate_queue"), Mapping)
            else "selected_safe_candidate_missing"
        ),
        "baseline_evidence_metrics_status": str(
            payload.get("baseline_evidence_metrics", {}).get(
                "status",
                "baseline_evidence_metrics_missing",
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else "baseline_evidence_metrics_missing"
        ),
        "baseline_evidence_snapshot_status": str(
            payload.get("baseline_evidence_metrics", {}).get(
                "evidence_snapshot_status",
                "metrics_missing",
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else "metrics_missing"
        ),
        "baseline_metric_confidence_status": str(
            payload.get("baseline_evidence_metrics", {}).get(
                "metric_confidence_status",
                "confidence_not_yet_quantified",
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else "confidence_not_yet_quantified"
        ),
        "baseline_metric_artifact_ingest_status": str(
            payload.get("baseline_evidence_metrics", {}).get(
                "metric_artifact_ingest_status",
                "metric_artifacts_missing",
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else "metric_artifacts_missing"
        ),
        "turnover_artifact_ingest_status": str(
            payload.get("baseline_evidence_metrics", {}).get(
                "turnover_artifact_ingest_status",
                "turnover_artifact_missing",
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else "turnover_artifact_missing"
        ),
        "cost_model_artifact_ingest_status": str(
            payload.get("baseline_evidence_metrics", {}).get(
                "cost_model_artifact_ingest_status",
                "cost_model_artifact_missing",
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else "cost_model_artifact_missing"
        ),
        "turnover_metric_status": str(
            payload.get("baseline_evidence_metrics", {}).get(
                "turnover_metric_status",
                "metrics_missing",
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else "metrics_missing"
        ),
        "cost_model_status": str(
            payload.get("baseline_evidence_metrics", {}).get(
                "cost_model_status",
                "metrics_missing",
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else "metrics_missing"
        ),
        "baseline_remaining_missing_metric_sources": list(
            payload.get("baseline_evidence_metrics", {}).get(
                "remaining_missing_metric_sources",
                [],
            )
            if isinstance(payload.get("baseline_evidence_metrics"), Mapping)
            else []
        ),
        "paper_observation_readiness_status": str(
            payload.get("paper_observation_readiness", {}).get(
                "readiness_status",
                "offline_readiness_packet_missing",
            )
            if isinstance(payload.get("paper_observation_readiness"), Mapping)
            else "offline_readiness_packet_missing"
        ),
        "paper_observation_readiness": dict(
            payload.get("paper_observation_readiness", {})
            if isinstance(payload.get("paper_observation_readiness"), Mapping)
            else {}
        ),
        "research_board_prioritization": dict(
            payload.get("research_board_prioritization", {})
            if isinstance(payload.get("research_board_prioritization"), Mapping)
            else {}
        ),
    }


def _selector_result(
    *,
    artifact_paths: Mapping[str, str],
    source_state: Mapping[str, Any],
    status: str,
    priority: str,
    selected_next_action_id: str,
    selected_next_action_type: str,
    selected_work_order: str,
    selected_owner: str,
    rationale: str,
    reason_codes: list[str],
    blocks_offline_build: bool,
    requires_daniel: bool,
    hard_gate_required: bool,
    selected_research_candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selected_work_order_path = str(artifact_paths[selected_work_order])
    candidate_id = (
        str(selected_research_candidate["candidate_id"])
        if selected_research_candidate is not None
        else None
    )
    candidate_priority = (
        str(selected_research_candidate["priority"])
        if selected_research_candidate is not None
        else None
    )
    candidate_title = (
        str(selected_research_candidate["title"])
        if selected_research_candidate is not None
        else None
    )
    return {
        "next_action_selector_version": _NEXT_ACTION_SELECTOR_VERSION,
        "status": status,
        "priority": priority,
        "selected_next_action_id": selected_next_action_id,
        "selected_next_action_type": selected_next_action_type,
        "selected_work_order": selected_work_order,
        "selected_work_order_path": selected_work_order_path,
        "selected_owner": selected_owner,
        "selected_research_candidate_id": candidate_id,
        "selected_research_candidate_priority": candidate_priority,
        "selected_research_candidate_title": candidate_title,
        "research_candidate_queue_path": str(
            artifact_paths["research_candidate_queue"]
        ),
        "rationale": rationale,
        "reason_codes": list(reason_codes),
        "blocks_offline_build": blocks_offline_build,
        "requires_daniel": requires_daniel,
        "hard_gate_required": hard_gate_required,
        "broker_action_allowed": False,
        "capital_action_allowed": False,
        "llm_runtime_calls_allowed": False,
        "network_runtime_calls_allowed": False,
        "safety_scope": "offline_text_artifacts_only_no_broker_no_network_no_submit",
        "forbidden_actions": _forbidden_behavior_lines(),
        "paper_observation_readiness_path": str(
            artifact_paths["paper_observation_readiness"]
        ),
        "paper_observation_readiness": dict(
            source_state.get("paper_observation_readiness", {})
            if isinstance(source_state.get("paper_observation_readiness"), Mapping)
            else {}
        ),
        "research_board_prioritization_path": str(
            artifact_paths["research_board_prioritization"]
        ),
        "research_board_prioritization": dict(
            source_state.get("research_board_prioritization", {})
            if isinstance(source_state.get("research_board_prioritization"), Mapping)
            else {}
        ),
        "source_state": dict(source_state),
    }


def _first_selector_action(
    actions: list[Any],
    *,
    priority: str | None = None,
    action_ids: tuple[str, ...] = (),
) -> Mapping[str, Any] | None:
    for action in actions:
        if not isinstance(action, Mapping):
            continue
        if priority is not None and action.get("priority") != priority:
            continue
        if action_ids and action.get("action_id") not in action_ids:
            continue
        return action
    return None


def _first_safe_offline_action(actions: list[Any]) -> Mapping[str, Any] | None:
    for action in actions:
        if not isinstance(action, Mapping):
            continue
        if action.get("action_type") == "noop":
            continue
        action_id = str(action.get("action_id", ""))
        if _selector_contains_forbidden_action(action_id):
            continue
        safety_scope = str(action.get("safety_scope", ""))
        if "no_broker_access" not in safety_scope and "broker_state_not_observed" not in safety_scope:
            continue
        return action
    return None


def _selector_action_reasons(action: Mapping[str, Any]) -> list[str]:
    reason_codes = action.get("reason_codes", [])
    if not isinstance(reason_codes, list):
        return []
    return [str(item) for item in reason_codes]


def _work_order_for_action(action: Mapping[str, Any]) -> tuple[str, str]:
    action_type = str(action.get("action_type", ""))
    if action_type in {"research_action", "validation_action"}:
        return "codex_work_order", "Codex"
    if action_type == "operator_action":
        return "gpt_next_action_handoff", "GPT"
    return "gpt_next_action_handoff", "GPT"


def _selector_contains_forbidden_action(value: str) -> bool:
    token = _classification_token(value)
    return any(term in token or term in value.lower() for term in _SELECTOR_FORBIDDEN_ACTION_TERMS)


def _apply_work_order_exports(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    queue = payload.get("research_candidate_queue")
    top_candidate_id = None
    if isinstance(queue, Mapping):
        top_candidate_id = queue.get("top_candidate_id")
    selector = payload.get("next_action_selector")
    selected_candidate_id = None
    if isinstance(selector, Mapping):
        selected_candidate_id = selector.get("selected_research_candidate_id")
    metrics = payload.get("baseline_evidence_metrics")
    metrics_record = metrics if isinstance(metrics, Mapping) else {}
    readiness = _paper_observation_readiness_record(payload, artifact_paths)
    prioritization = _research_board_prioritization_record(payload, artifact_paths)
    exports = {
        "work_order_exports_version": _WORK_ORDER_EXPORTS_VERSION,
        "status": "generated",
        "directory": str(artifact_paths["work_orders"]),
        "artifact_count": len(_WORK_ORDER_ARTIFACTS),
        "generation_mode": "deterministic_offline_markdown_only",
        "runtime_callouts_performed": False,
        "research_candidate_queue_path": str(artifact_paths["research_candidate_queue"]),
        "baseline_evidence_metrics_path": str(
            artifact_paths["baseline_evidence_metrics"]
        ),
        "paper_observation_readiness_path": str(
            artifact_paths["paper_observation_readiness"]
        ),
        "paper_observation_readiness": dict(readiness),
        "paper_observation_readiness_status": str(
            readiness.get("readiness_status", "offline_readiness_packet_missing")
        ),
        "research_board_prioritization_path": str(
            artifact_paths["research_board_prioritization"]
        ),
        "research_board_prioritization": dict(prioritization),
        "research_board_prioritization_status": str(
            prioritization.get("prioritization_status", "ranked")
        ),
        "metric_artifact_ingest_status": str(
            metrics_record.get(
                "metric_artifact_ingest_status",
                "metric_artifacts_missing",
            )
            if isinstance(metrics_record, Mapping)
            else "metric_artifacts_missing"
        ),
        "turnover_artifact_ingest_status": str(
            metrics_record.get(
                "turnover_artifact_ingest_status",
                "turnover_artifact_missing",
            )
            if isinstance(metrics_record, Mapping)
            else "turnover_artifact_missing"
        ),
        "cost_model_artifact_ingest_status": str(
            metrics_record.get(
                "cost_model_artifact_ingest_status",
                "cost_model_artifact_missing",
            )
            if isinstance(metrics_record, Mapping)
            else "cost_model_artifact_missing"
        ),
        "turnover_metric_status": str(
            metrics_record.get("turnover_metric_status", "metrics_missing")
            if isinstance(metrics_record, Mapping)
            else "metrics_missing"
        ),
        "cost_model_status": str(
            metrics_record.get("cost_model_status", "metrics_missing")
            if isinstance(metrics_record, Mapping)
            else "metrics_missing"
        ),
        "metric_artifact_paths": dict(
            metrics_record.get("metric_artifact_paths", {})
            if isinstance(metrics_record, Mapping)
            else {}
        ),
        "metric_artifact_hashes": dict(
            metrics_record.get("metric_artifact_hashes", {})
            if isinstance(metrics_record, Mapping)
            else {}
        ),
        "metric_artifact_parse_status": dict(
            metrics_record.get("metric_artifact_parse_status", {})
            if isinstance(metrics_record, Mapping)
            else {}
        ),
        "metric_artifact_record_count": dict(
            metrics_record.get("metric_artifact_record_count", {})
            if isinstance(metrics_record, Mapping)
            else {}
        ),
        "turnover_artifact_path": str(
            metrics_record.get(
                "turnover_artifact_path",
                _normalize_path(
                    Path(artifact_paths["baseline_evidence_metrics"]).parent
                    / _BASELINE_TURNOVER_SUMMARY_FILENAME
                ),
            )
            if isinstance(metrics_record, Mapping)
            else ""
        ),
        "cost_model_artifact_path": str(
            metrics_record.get(
                "cost_model_artifact_path",
                _normalize_path(
                    Path(artifact_paths["baseline_evidence_metrics"]).parent
                    / _BASELINE_COST_MODEL_SUMMARY_FILENAME
                ),
            )
            if isinstance(metrics_record, Mapping)
            else ""
        ),
        "turnover_artifact_hash": (
            metrics_record.get("turnover_artifact_hash")
            if isinstance(metrics_record, Mapping)
            else None
        ),
        "cost_model_artifact_hash": (
            metrics_record.get("cost_model_artifact_hash")
            if isinstance(metrics_record, Mapping)
            else None
        ),
        "turnover_artifact_parse_status": str(
            metrics_record.get("turnover_artifact_parse_status", "missing")
            if isinstance(metrics_record, Mapping)
            else "missing"
        ),
        "cost_model_artifact_parse_status": str(
            metrics_record.get("cost_model_artifact_parse_status", "missing")
            if isinstance(metrics_record, Mapping)
            else "missing"
        ),
        "remaining_missing_metric_sources": list(
            metrics_record.get("remaining_missing_metric_sources", [])
            if isinstance(metrics_record, Mapping)
            else []
        ),
        "next_safe_metric_command": _baseline_evidence_next_safe_metric_command(
            artifact_paths
        ),
        "artifact_prerequisite_chain": _baseline_metric_prerequisite_chain(
            artifact_paths
        ),
        "top_research_candidate_id": top_candidate_id,
        "selected_research_candidate_id": selected_candidate_id,
        "safety_scope": "offline_text_export_only_no_broker_no_network_no_llm_calls",
        "artifacts": _work_order_export_artifacts(artifact_paths, "generated"),
    }
    payload["work_order_exports"] = exports
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["work_order_exports"] = dict(exports)


def _work_order_export_artifacts(
    artifact_paths: Mapping[str, str],
    status: str,
) -> dict[str, dict[str, str]]:
    return {
        artifact_id: {
            "path": str(artifact_paths[artifact_id]),
            "audience": audience,
            "purpose": purpose,
            "status": status,
        }
        for artifact_id, _filename, audience, purpose in _WORK_ORDER_ARTIFACTS
    }


def _write_work_order_artifacts(output_root: Path, payload: Mapping[str, Any]) -> None:
    work_orders_dir = output_root / _WORK_ORDERS_DIRNAME
    work_orders_dir.mkdir(parents=True, exist_ok=True)
    renderers = {
        _GPT_WORK_ORDER_FILENAME: _render_gpt_next_action_handoff,
        _CODEX_WORK_ORDER_FILENAME: _render_codex_work_order,
        _ANTIGRAVITY_WORK_ORDER_FILENAME: _render_antigravity_review_order,
        _CLAUDE_WORK_ORDER_FILENAME: _render_claude_critique_order,
    }
    for filename, renderer in renderers.items():
        (work_orders_dir / filename).write_text(
            renderer(payload),
            encoding="utf-8",
            newline="\n",
        )


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
    selector_ok, selector_summary = _quality_next_action_selector_summary(
        packet_for_checks
    )
    work_orders_ok, work_orders_summary = _quality_work_order_exports_summary(
        root,
        packet_for_checks,
    )
    candidate_queue_ok, candidate_queue_summary = (
        _quality_research_candidate_queue_summary(root, packet_for_checks)
    )
    baseline_health_ok, baseline_health_summary = (
        _quality_baseline_health_evaluation_summary(root, packet_for_checks)
    )
    baseline_metrics_ok, baseline_metrics_summary = (
        _quality_baseline_evidence_metrics_summary(root, packet_for_checks)
    )
    readiness_ok, readiness_summary = (
        _quality_paper_observation_readiness_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    metric_ingest_ok, metric_ingest_summary = _quality_metric_artifact_ingest_summary(
        root,
        packet_for_checks,
    )
    turnover_cost_ok, turnover_cost_summary = (
        _quality_turnover_cost_artifact_summary(root, packet_for_checks)
    )
    legacy_outputs_ok, legacy_outputs_summary = (
        _quality_legacy_outputs_preserved_summary(artifact_presence_status)
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
            "research_candidate_queue_generated",
            candidate_queue_ok,
            candidate_queue_summary,
        ),
        _quality_check(
            "baseline_health_evaluation_generated",
            baseline_health_ok,
            baseline_health_summary,
        ),
        _quality_check(
            "baseline_evidence_metrics_generated",
            baseline_metrics_ok,
            baseline_metrics_summary,
        ),
        _quality_check(
            "paper_observation_readiness_generated",
            readiness_ok,
            readiness_summary,
        ),
        _quality_check(
            "baseline_metric_artifact_ingest_status_explicit",
            metric_ingest_ok,
            metric_ingest_summary,
        ),
        _quality_check(
            "turnover_and_cost_model_artifacts_explicit",
            turnover_cost_ok,
            turnover_cost_summary,
        ),
        _quality_check(
            "assistant_v1_through_v1_11_outputs_preserved",
            legacy_outputs_ok,
            legacy_outputs_summary,
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
        _quality_check(
            "next_action_selector_safety_scoped",
            selector_ok,
            selector_summary,
        ),
        _quality_check(
            "work_order_exports_generated",
            work_orders_ok,
            work_orders_summary,
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
        "## Research Candidate Queue",
        "## Baseline Health Evaluation",
        "## Baseline Evidence Metrics",
        "## Paper Observation Readiness",
        "## Next Action Selector",
        "## Executive dashboard",
        "Quality Gate",
        "Decision Ledger",
        "Work order exports",
        _RESEARCH_CANDIDATE_QUEUE_FILENAME,
        _BASELINE_HEALTH_EVALUATION_FILENAME,
        _BASELINE_EVIDENCE_METRICS_FILENAME,
        _PAPER_OBSERVATION_READINESS_FILENAME,
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


def _quality_research_candidate_queue_summary(
    output_root: Path,
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_research_candidate_queue_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    queue = packet["research_candidate_queue"]
    assert isinstance(queue, Mapping)
    queue_path = output_root / _RESEARCH_CANDIDATE_QUEUE_FILENAME
    if not queue_path.exists() or not queue_path.is_file():
        return False, f"{_RESEARCH_CANDIDATE_QUEUE_FILENAME} missing"
    if queue_path.stat().st_size <= 0:
        return False, f"{_RESEARCH_CANDIDATE_QUEUE_FILENAME} empty"
    candidates = queue["candidates"]
    assert isinstance(candidates, list)
    expected = sorted(
        candidates,
        key=lambda item: (
            _ACTION_PRIORITY_RANK[str(item["priority"])],
            str(item["candidate_id"]),
        ),
    )
    if list(candidates) != expected:
        return False, "research candidates are not sorted by priority/candidate_id"
    if queue["candidate_count"] != len(candidates):
        return False, "candidate_count does not match candidates length"
    if candidates:
        top = candidates[0]
        if queue["top_candidate_id"] != top["candidate_id"]:
            return False, "top_candidate_id does not match first sorted candidate"
        if queue["top_candidate_priority"] != top["priority"]:
            return False, "top_candidate_priority does not match first sorted candidate"
    artifact_lines = [
        line.strip()
        for line in queue_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != len(candidates):
        return False, "queue artifact line count does not match candidates length"
    for index, line in enumerate(artifact_lines):
        try:
            artifact_candidate = json.loads(line)
        except json.JSONDecodeError:
            return False, f"queue artifact line {index + 1} is not JSON"
        if artifact_candidate != candidates[index]:
            return False, f"queue artifact line {index + 1} does not match packet"
    for candidate in candidates:
        if _research_candidate_contains_forbidden_term(candidate):
            return False, (
                "research candidate contains forbidden broker, order, credential, "
                "paid-tool, account, or capital term"
            )
    return True, (
        "research candidate queue generated; top_candidate_id="
        f"{queue['top_candidate_id']}; candidate_count={queue['candidate_count']}"
    )


def _quality_baseline_health_evaluation_summary(
    output_root: Path,
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_baseline_health_evaluation_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    evaluation = packet["baseline_health_evaluation"]
    assert isinstance(evaluation, Mapping)
    artifact_path = output_root / _BASELINE_HEALTH_EVALUATION_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_BASELINE_HEALTH_EVALUATION_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, f"{_BASELINE_HEALTH_EVALUATION_FILENAME} must be one JSONL record"
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_BASELINE_HEALTH_EVALUATION_FILENAME} is not JSON"
    if artifact_record != evaluation:
        return False, "baseline health artifact does not match packet"
    return True, (
        "baseline health evaluation generated; health_status="
        f"{evaluation['health_status']}; next_safe_test={evaluation['next_safe_test']}"
    )


def _quality_baseline_evidence_metrics_summary(
    output_root: Path,
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_baseline_evidence_metrics_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    metrics = packet["baseline_evidence_metrics"]
    assert isinstance(metrics, Mapping)
    artifact_path = output_root / _BASELINE_EVIDENCE_METRICS_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_BASELINE_EVIDENCE_METRICS_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, f"{_BASELINE_EVIDENCE_METRICS_FILENAME} must be one JSONL record"
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_BASELINE_EVIDENCE_METRICS_FILENAME} is not JSON"
    if artifact_record != metrics:
        return False, "baseline evidence metrics artifact does not match packet"
    return True, (
        "baseline evidence metrics generated; evidence_snapshot_status="
        f"{metrics['evidence_snapshot_status']}; "
        f"next_safe_metric_command={metrics['next_safe_metric_command']}"
    )


def _quality_paper_observation_readiness_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_paper_observation_readiness_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    readiness = packet["paper_observation_readiness"]
    assert isinstance(readiness, Mapping)
    artifact_path = output_root / _PAPER_OBSERVATION_READINESS_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_PAPER_OBSERVATION_READINESS_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, f"{_PAPER_OBSERVATION_READINESS_FILENAME} must be one JSONL record"
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_PAPER_OBSERVATION_READINESS_FILENAME} is not JSON"
    if artifact_record != readiness:
        return False, "paper observation readiness artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("paper_observation_readiness")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index paper_observation_readiness"
    if not str(indexed.get("path", "")).endswith(
        _PAPER_OBSERVATION_READINESS_FILENAME
    ):
        return False, "manifest readiness artifact path is not explicit"
    if readiness["approval_phrase_required"] != _PAPER_OBSERVATION_APPROVAL_PHRASE:
        return False, "approval phrase is not explicit"
    if readiness["broker_reads_performed"] is not False:
        return False, "broker read was performed"
    if readiness["broker_state_mode"] != "broker_state_not_observed":
        return False, "broker state wording changed"
    if readiness["paper_submit_authorized"] is not False:
        return False, "paper_submit_authorized is not false"
    if readiness["profit_claim"] != "none":
        return False, "profit_claim is not none"
    forbidden_ops = {
        str(item) for item in readiness.get("forbidden_future_operations", [])
    }
    if "live trading" not in forbidden_ops:
        return False, "live trading is not explicitly forbidden"
    serialized = json.dumps(
        _json_safe(readiness),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    for forbidden in _FORBIDDEN_BROKER_NOT_OBSERVED_CLAIMS:
        if forbidden in serialized:
            return False, f"forbidden broker-state claim found: {forbidden}"
    return True, (
        "paper observation readiness generated; broker_reads_performed=false; "
        "broker_state_mode=broker_state_not_observed; paper_submit_authorized=false"
    )


def _quality_legacy_outputs_preserved_summary(
    artifact_presence_status: Mapping[str, Any],
) -> tuple[bool, str]:
    artifacts = artifact_presence_status.get("artifacts")
    if not isinstance(artifacts, Mapping):
        return False, "artifact presence map missing"
    legacy_artifact_ids = (
        "operating_brief",
        "operating_record",
        "manifest",
        "research_candidate_queue",
        "baseline_health_evaluation",
        "baseline_evidence_metrics",
        "review_handoff",
        "gpt_next_action_handoff",
        "codex_work_order",
        "antigravity_review_order",
        "claude_critique_order",
    )
    missing = [
        artifact_id
        for artifact_id in legacy_artifact_ids
        if not (
            isinstance(artifacts.get(artifact_id), Mapping)
            and artifacts[artifact_id].get("exists") is True
            and artifacts[artifact_id].get("non_empty") is True
        )
    ]
    if missing:
        return False, "legacy_outputs_missing=" + ",".join(missing)
    return True, "v1 through v1.11 expected outputs remain present and non-empty"


def _quality_metric_artifact_ingest_summary(
    output_root: Path,
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_baseline_evidence_metrics_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    metrics = packet["baseline_evidence_metrics"]
    assert isinstance(metrics, Mapping)
    paths = metrics["metric_artifact_paths"]
    hashes = metrics["metric_artifact_hashes"]
    parse_status = metrics["metric_artifact_parse_status"]
    record_count = metrics["metric_artifact_record_count"]
    assert isinstance(paths, Mapping)
    assert isinstance(hashes, Mapping)
    assert isinstance(parse_status, Mapping)
    assert isinstance(record_count, Mapping)

    parsed_artifacts: list[str] = []
    for artifact_id, filename in _BASELINE_METRIC_ARTIFACTS:
        path_text = str(paths.get(artifact_id, ""))
        if not path_text.endswith(filename):
            return False, f"{artifact_id} path does not end with {filename}"
        status = parse_status.get(artifact_id)
        if status not in _BASELINE_METRIC_ARTIFACT_PARSE_STATUSES:
            return False, f"{artifact_id} parse status is not explicit"
        count = record_count.get(artifact_id)
        if not isinstance(count, int) or count < 0:
            return False, f"{artifact_id} record count is not explicit"

        path = Path(path_text)
        if not path.is_absolute():
            path = output_root / filename
        if path.exists() and path.is_file():
            digest = str(hashes.get(artifact_id, ""))
            if len(digest) != 64 or digest != _sha256_file(path):
                return False, f"{artifact_id} sha256 missing or mismatched"
            if status == "missing":
                return False, f"{artifact_id} exists but parse status is missing"
        elif path.exists() and status != "path_not_file":
            return False, f"{artifact_id} exists but parse status is {status}"
        elif not path.exists() and status != "missing":
            return False, f"{artifact_id} missing but parse status is {status}"
        if status == "parsed":
            parsed_artifacts.append(artifact_id)

    ingest_status = str(metrics.get("metric_artifact_ingest_status", ""))
    if ingest_status == "metric_artifacts_missing":
        if parsed_artifacts:
            return False, "missing ingest status includes parsed artifacts"
        if metrics.get("metric_confidence_status") != "confidence_not_yet_quantified":
            return False, "missing artifacts must not quantify confidence"
        if metrics.get("quantified_metric_summary") != {}:
            return False, "missing artifacts must not expose quantified metrics"
    if (
        metrics.get("profit_claim") != "none"
        or metrics.get("paper_submit_readiness_status") != "not_ready_for_paper_submit"
        or metrics.get("broker_state_mode")
        not in {"broker_state_not_observed", "offline_preview_only"}
    ):
        return False, "baseline metric safety wording changed"

    return True, (
        f"metric_artifact_ingest_status={ingest_status}; "
        f"parsed_artifacts={','.join(parsed_artifacts) or 'none'}"
    )


def _quality_turnover_cost_artifact_summary(
    output_root: Path,
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    metrics = packet.get("baseline_evidence_metrics")
    if not isinstance(metrics, Mapping):
        return False, "baseline_evidence_metrics missing"

    expected = {
        "turnover": {
            "filename": _BASELINE_TURNOVER_SUMMARY_FILENAME,
            "path_field": "turnover_artifact_path",
            "hash_field": "turnover_artifact_hash",
            "parse_field": "turnover_artifact_parse_status",
            "ingest_field": "turnover_artifact_ingest_status",
            "metric_field": "turnover_metric_status",
            "parsed_ingest": "turnover_artifact_ingested",
        },
        "cost_model": {
            "filename": _BASELINE_COST_MODEL_SUMMARY_FILENAME,
            "path_field": "cost_model_artifact_path",
            "hash_field": "cost_model_artifact_hash",
            "parse_field": "cost_model_artifact_parse_status",
            "ingest_field": "cost_model_artifact_ingest_status",
            "metric_field": "cost_model_status",
            "parsed_ingest": "cost_model_artifact_ingested",
        },
    }
    parsed: list[str] = []
    for artifact_name, fields in expected.items():
        path_text = str(metrics.get(fields["path_field"], ""))
        filename = str(fields["filename"])
        if not path_text.endswith(filename):
            return False, f"{artifact_name} artifact path missing or wrong"
        parse_status = str(metrics.get(fields["parse_field"], ""))
        if parse_status not in _BASELINE_METRIC_ARTIFACT_PARSE_STATUSES:
            return False, f"{artifact_name} parse status is not explicit"
        metric_status = str(metrics.get(fields["metric_field"], ""))
        if metric_status not in _BASELINE_METRIC_STATUSES:
            return False, f"{artifact_name} metric status is not explicit"
        path = Path(path_text)
        if not path.is_absolute():
            path = output_root / filename
        if path.exists() and path.is_file():
            digest = metrics.get(fields["hash_field"])
            if not _sha256_text(digest) or digest != _sha256_file(path):
                return False, f"{artifact_name} artifact hash missing or mismatched"
            if parse_status != "parsed":
                return False, f"{artifact_name} exists but parse status={parse_status}"
            if metrics.get(fields["ingest_field"]) != fields["parsed_ingest"]:
                return False, f"{artifact_name} ingest status is not parsed"
            parsed.append(artifact_name)
        elif parse_status != "missing":
            return False, f"{artifact_name} missing but parse status={parse_status}"

    missing_sources = [
        str(item) for item in metrics.get("remaining_missing_metric_sources", [])
    ]
    if (
        "turnover_summary" in missing_sources
        or "cost_model_summary" in missing_sources
    ):
        return False, "turnover or cost-model source remains marked missing"
    if "paper_observation_summary" not in missing_sources:
        return False, "paper observation is not explicitly hard-gated as missing"
    if (
        metrics.get("profit_claim") != "none"
        or metrics.get("paper_observation_status") != "broker_state_not_observed"
        or metrics.get("paper_submit_readiness_status") != "not_ready_for_paper_submit"
        or metrics.get("broker_state_mode")
        not in {"broker_state_not_observed", "offline_preview_only"}
    ):
        return False, "turnover/cost safety wording changed"

    return True, (
        "turnover_and_cost_model_artifacts="
        f"{','.join(parsed) or 'none'}; "
        "paper_observation_summary=hard_gated_missing"
    )


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
        _RESEARCH_CANDIDATE_QUEUE_FILENAME,
        _BASELINE_HEALTH_EVALUATION_FILENAME,
        _BASELINE_EVIDENCE_METRICS_FILENAME,
        _REVIEW_INPUTS_DIRNAME,
        _WORK_ORDERS_DIRNAME,
        _GPT_WORK_ORDER_FILENAME,
        _CODEX_WORK_ORDER_FILENAME,
        _ANTIGRAVITY_WORK_ORDER_FILENAME,
        _CLAUDE_WORK_ORDER_FILENAME,
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


def _quality_next_action_selector_summary(
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_next_action_selector_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    selector = packet["next_action_selector"]
    assert isinstance(selector, Mapping)
    selected_action_id = str(selector["selected_next_action_id"])
    if _selector_contains_forbidden_action(selected_action_id):
        return False, "selected_next_action_id includes forbidden runtime action"
    selected_path = str(selector["selected_work_order_path"])
    if f"{_WORK_ORDERS_DIRNAME}/" not in selected_path.replace("\\", "/"):
        return False, "selected_work_order_path is not under work_orders"
    return True, (
        "selected_next_action_id="
        f"{selected_action_id}; selected_work_order={selector['selected_work_order']}"
    )


def _quality_work_order_exports_summary(
    output_root: Path,
    packet: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_work_order_export_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    exports = packet["work_order_exports"]
    assert isinstance(exports, Mapping)
    if exports.get("status") != "generated":
        return False, f"work_order_exports status={exports.get('status')}"
    artifacts = exports["artifacts"]
    assert isinstance(artifacts, Mapping)
    missing_files: list[str] = []
    empty_files: list[str] = []
    missing_tokens: list[str] = []
    for artifact_id, filename, _audience, _purpose in _WORK_ORDER_ARTIFACTS:
        path = output_root / _WORK_ORDERS_DIRNAME / filename
        if not path.exists() or not path.is_file():
            missing_files.append(artifact_id)
            continue
        text = _read_text_or_empty(path)
        if not text.strip():
            empty_files.append(artifact_id)
            continue
        for token in (
            _PHASE_NAME,
            "## Research candidate queue",
            _RESEARCH_CANDIDATE_QUEUE_FILENAME,
            "## Baseline health evaluation",
            _BASELINE_HEALTH_EVALUATION_FILENAME,
            "## Baseline evidence metrics",
            _BASELINE_EVIDENCE_METRICS_FILENAME,
            _BASELINE_HEALTH_NEXT_SAFE_TEST,
            "## Prerequisite artifact chain",
            _BASELINE_TURNOVER_SUMMARY_FILENAME,
            _BASELINE_COST_MODEL_SUMMARY_FILENAME,
            "paper_observation_summary",
            "next_safe_metric_command",
            "Do not commit unless GPT/Daniel explicitly asks after review.",
            "## Forbidden behavior",
            "## Required tests",
            "## Expected report format",
        ):
            if token not in text:
                missing_tokens.append(f"{artifact_id}.{token}")
    if missing_files or empty_files or missing_tokens:
        return False, (
            "missing="
            f"{','.join(missing_files)}; empty={','.join(empty_files)}; "
            f"missing_tokens={','.join(missing_tokens)}"
        )
    return True, "all deterministic work-order markdown artifacts are generated"


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
    missing.extend(_missing_research_candidate_queue_fields("", packet))
    missing.extend(_missing_paper_observation_readiness_fields("", packet))
    missing.extend(_missing_research_board_prioritization_fields("", packet))
    missing.extend(_missing_baseline_evidence_metrics_fields("", packet))
    missing.extend(_missing_baseline_health_evaluation_fields("", packet))
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
    missing.extend(_missing_next_action_selector_fields("", packet))
    missing.extend(_missing_work_order_export_fields("", packet))
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
    missing.extend(_missing_research_candidate_queue_fields("manifest", manifest))
    missing.extend(_missing_paper_observation_readiness_fields("manifest", manifest))
    missing.extend(_missing_research_board_prioritization_fields("manifest", manifest))
    missing.extend(_missing_baseline_evidence_metrics_fields("manifest", manifest))
    missing.extend(_missing_baseline_health_evaluation_fields("manifest", manifest))
    missing.extend(_missing_review_decision_fields("manifest", manifest))
    missing.extend(_missing_next_action_selector_fields("manifest", manifest))
    missing.extend(_missing_work_order_export_fields("manifest", manifest))

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
        "research_candidate_queue_version",
        "research_candidate_queue_path",
        "research_candidate_queue",
        "paper_observation_readiness_version",
        "paper_observation_readiness_path",
        "paper_observation_readiness",
        "research_board_prioritization_version",
        "research_board_prioritization_path",
        "research_board_prioritization",
        "baseline_health_evaluation_version",
        "baseline_health_evaluation_path",
        "baseline_health_evaluation",
        "baseline_evidence_metrics_version",
        "baseline_evidence_metrics_path",
        "baseline_evidence_metrics",
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
        "next_action_selector",
        "work_order_exports",
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

    if (
        isinstance(packet.get("research_candidate_queue"), Mapping)
        and isinstance(manifest.get("research_candidate_queue"), Mapping)
        and dict(manifest["research_candidate_queue"])
        != dict(packet["research_candidate_queue"])
    ):
        missing.append("manifest.research_candidate_queue.matches_record")

    if (
        isinstance(packet.get("paper_observation_readiness"), Mapping)
        and isinstance(manifest.get("paper_observation_readiness"), Mapping)
        and dict(manifest["paper_observation_readiness"])
        != dict(packet["paper_observation_readiness"])
    ):
        missing.append("manifest.paper_observation_readiness.matches_record")

    if (
        isinstance(packet.get("baseline_health_evaluation"), Mapping)
        and isinstance(manifest.get("baseline_health_evaluation"), Mapping)
        and dict(manifest["baseline_health_evaluation"])
        != dict(packet["baseline_health_evaluation"])
    ):
        missing.append("manifest.baseline_health_evaluation.matches_record")

    if (
        isinstance(packet.get("baseline_evidence_metrics"), Mapping)
        and isinstance(manifest.get("baseline_evidence_metrics"), Mapping)
        and dict(manifest["baseline_evidence_metrics"])
        != dict(packet["baseline_evidence_metrics"])
    ):
        missing.append("manifest.baseline_evidence_metrics.matches_record")

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


def _missing_research_candidate_queue_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    queue = packet.get("research_candidate_queue")
    if not isinstance(queue, Mapping):
        return [f"{field_prefix}research_candidate_queue"]
    for field_name in _REQUIRED_RESEARCH_CANDIDATE_QUEUE_FIELDS:
        if field_name not in queue:
            missing.append(f"{field_prefix}research_candidate_queue.{field_name}")
    if (
        packet.get("research_candidate_queue_version")
        != _RESEARCH_CANDIDATE_QUEUE_VERSION
    ):
        missing.append(f"{field_prefix}research_candidate_queue_version")
    if queue.get("research_candidate_queue_version") != _RESEARCH_CANDIDATE_QUEUE_VERSION:
        missing.append(
            f"{field_prefix}research_candidate_queue.research_candidate_queue_version"
        )
    if queue.get("status") not in {"generated", "not_generated"}:
        missing.append(f"{field_prefix}research_candidate_queue.status.allowed")
    if not str(packet.get("research_candidate_queue_path", "")).strip():
        missing.append(f"{field_prefix}research_candidate_queue_path")
    if not str(queue.get("artifact_path", "")).strip():
        missing.append(f"{field_prefix}research_candidate_queue.artifact_path")
    if not isinstance(queue.get("priority_rules"), Mapping):
        missing.append(f"{field_prefix}research_candidate_queue.priority_rules")
    else:
        for priority in _ACTION_PRIORITIES:
            if priority not in queue["priority_rules"]:
                missing.append(
                    f"{field_prefix}research_candidate_queue.priority_rules.{priority}"
                )
    candidates = queue.get("candidates")
    if not isinstance(candidates, list):
        missing.append(f"{field_prefix}research_candidate_queue.candidates")
        return missing
    if not isinstance(queue.get("candidate_count"), int):
        missing.append(f"{field_prefix}research_candidate_queue.candidate_count.int")
    elif queue["candidate_count"] != len(candidates):
        missing.append(f"{field_prefix}research_candidate_queue.candidate_count")
    for field_name in (
        "top_candidate_id",
        "top_candidate_priority",
        "top_candidate_title",
        "selected_safe_candidate_id",
        "selected_safe_candidate_priority",
        "selected_safe_candidate_title",
    ):
        if field_name not in queue:
            missing.append(f"{field_prefix}research_candidate_queue.{field_name}")
    if not str(queue.get("paper_observation_readiness_path", "")).endswith(
        _PAPER_OBSERVATION_READINESS_FILENAME
    ):
        missing.append(
            f"{field_prefix}research_candidate_queue.paper_observation_readiness_path"
        )
    if not isinstance(queue.get("paper_observation_readiness"), Mapping):
        missing.append(
            f"{field_prefix}research_candidate_queue.paper_observation_readiness.object"
        )
    for index, candidate in enumerate(candidates):
        candidate_prefix = (
            f"{field_prefix}research_candidate_queue.candidates.{index}"
        )
        if not isinstance(candidate, Mapping):
            missing.append(candidate_prefix)
            continue
        for field_name in _REQUIRED_RESEARCH_CANDIDATE_FIELDS:
            if field_name not in candidate:
                missing.append(f"{candidate_prefix}.{field_name}")
        if candidate.get("priority") not in _ACTION_PRIORITIES:
            missing.append(f"{candidate_prefix}.priority.allowed")
        if candidate.get("status") not in _RESEARCH_CANDIDATE_STATUSES:
            missing.append(f"{candidate_prefix}.status.allowed")
        for list_field in (
            "evidence_sources",
            "required_data",
            "blocked_by",
            "promotion_criteria",
            "rejection_criteria",
        ):
            if list_field in candidate and not isinstance(candidate.get(list_field), list):
                missing.append(f"{candidate_prefix}.{list_field}.list")
        for bool_field in ("requires_daniel", "hard_gate_required"):
            if bool_field in candidate and not isinstance(candidate.get(bool_field), bool):
                missing.append(f"{candidate_prefix}.{bool_field}.bool")
        if _research_candidate_contains_forbidden_term(candidate):
            missing.append(f"{candidate_prefix}.safe")
    return missing


def _missing_paper_observation_readiness_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    readiness = packet.get("paper_observation_readiness")
    if not isinstance(readiness, Mapping):
        return [f"{field_prefix}paper_observation_readiness"]
    for field_name in _REQUIRED_PAPER_OBSERVATION_READINESS_FIELDS:
        if field_name not in readiness:
            missing.append(f"{field_prefix}paper_observation_readiness.{field_name}")
    if (
        packet.get("paper_observation_readiness_version")
        != _PAPER_OBSERVATION_READINESS_VERSION
    ):
        missing.append(f"{field_prefix}paper_observation_readiness_version")
    if (
        readiness.get("paper_observation_readiness_version")
        != _PAPER_OBSERVATION_READINESS_VERSION
    ):
        missing.append(
            f"{field_prefix}paper_observation_readiness.paper_observation_readiness_version"
        )
    if not str(packet.get("paper_observation_readiness_path", "")).endswith(
        _PAPER_OBSERVATION_READINESS_FILENAME
    ):
        missing.append(f"{field_prefix}paper_observation_readiness_path")
    if not str(readiness.get("artifact_path", "")).endswith(
        _PAPER_OBSERVATION_READINESS_FILENAME
    ):
        missing.append(f"{field_prefix}paper_observation_readiness.artifact_path")
    if readiness.get("status") not in {"generated", "not_generated"}:
        missing.append(f"{field_prefix}paper_observation_readiness.status.allowed")
    if readiness.get("readiness_status") not in {
        "hard_gate_prepared_not_authorized",
        "offline_readiness_packet_not_generated",
    }:
        missing.append(
            f"{field_prefix}paper_observation_readiness.readiness_status"
        )
    if readiness.get("remaining_gap") != "paper_observation_summary":
        missing.append(f"{field_prefix}paper_observation_readiness.remaining_gap")
    for true_field in ("hard_gate_required", "requires_daniel"):
        if readiness.get(true_field) is not True:
            missing.append(
                f"{field_prefix}paper_observation_readiness.{true_field}.true"
            )
    if readiness.get("approval_phrase_required") != _PAPER_OBSERVATION_APPROVAL_PHRASE:
        missing.append(
            f"{field_prefix}paper_observation_readiness.approval_phrase_required"
        )
    if not isinstance(readiness.get("allowed_future_read_operations"), list):
        missing.append(
            f"{field_prefix}paper_observation_readiness.allowed_future_read_operations.list"
        )
    if not isinstance(readiness.get("forbidden_future_operations"), list):
        missing.append(
            f"{field_prefix}paper_observation_readiness.forbidden_future_operations.list"
        )
    else:
        forbidden_ops = {str(item) for item in readiness["forbidden_future_operations"]}
        for operation in (
            "submit",
            "cancel",
            "replace",
            "close",
            "close_all_positions",
            "liquidate",
            "delete",
            "retry mutation",
            "live trading",
        ):
            if operation not in forbidden_ops:
                missing.append(
                    f"{field_prefix}paper_observation_readiness.forbidden_future_operations.{operation}"
                )
    preflight = readiness.get("required_preflight_booleans")
    if not isinstance(preflight, Mapping):
        missing.append(
            f"{field_prefix}paper_observation_readiness.required_preflight_booleans.object"
        )
    else:
        for key in (
            "APP_PROFILE_is_paper",
            "ALPACA_API_KEY_loaded",
            "ALPACA_API_SECRET_KEY_loaded",
            "ALPACA_SECRET_KEY_loaded",
            "APCA_API_KEY_ID_loaded",
            "APCA_API_SECRET_KEY_loaded",
        ):
            if preflight.get(key) is not False:
                missing.append(
                    f"{field_prefix}paper_observation_readiness.required_preflight_booleans.{key}.false"
                )
    for list_field in ("expected_output_artifacts", "stop_conditions"):
        if not isinstance(readiness.get(list_field), list):
            missing.append(
                f"{field_prefix}paper_observation_readiness.{list_field}.list"
            )
    if isinstance(readiness.get("expected_output_artifacts"), list):
        if _PAPER_OBSERVATION_READINESS_FILENAME not in {
            str(item) for item in readiness["expected_output_artifacts"]
        }:
            missing.append(
                f"{field_prefix}paper_observation_readiness.expected_output_artifacts.current_artifact"
            )
    if not isinstance(readiness.get("broker_state_claim_policy"), Mapping):
        missing.append(
            f"{field_prefix}paper_observation_readiness.broker_state_claim_policy.object"
        )
    else:
        policy = readiness["broker_state_claim_policy"]
        if policy.get("current_mode") != "broker_state_not_observed":
            missing.append(
                f"{field_prefix}paper_observation_readiness.broker_state_claim_policy.current_mode"
            )
        if policy.get("position_state_claims_allowed") is not False:
            missing.append(
                f"{field_prefix}paper_observation_readiness.broker_state_claim_policy.position_state_claims_allowed.false"
            )
        if policy.get("open_order_state_claims_allowed") is not False:
            missing.append(
                f"{field_prefix}paper_observation_readiness.broker_state_claim_policy.open_order_state_claims_allowed.false"
            )
    for false_field in (
        "broker_reads_performed",
        "broker_mutation_performed",
        "runtime_callouts_performed",
        "network_calls_performed",
        "paper_submit_authorized",
    ):
        if readiness.get(false_field) is not False:
            missing.append(
                f"{field_prefix}paper_observation_readiness.{false_field}.false"
            )
    if readiness.get("profit_claim") != "none":
        missing.append(f"{field_prefix}paper_observation_readiness.profit_claim")
    if readiness.get("safety_scope") != "offline_only":
        missing.append(f"{field_prefix}paper_observation_readiness.safety_scope")
    if readiness.get("broker_state_mode") != "broker_state_not_observed":
        missing.append(f"{field_prefix}paper_observation_readiness.broker_state_mode")
    serialized = json.dumps(
        _json_safe(readiness),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    for forbidden in _FORBIDDEN_BROKER_NOT_OBSERVED_CLAIMS:
        if forbidden in serialized:
            missing.append(
                f"{field_prefix}paper_observation_readiness.forbidden_broker_state_claim.{forbidden}"
            )
    return missing


def _missing_research_board_prioritization_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    prioritization = packet.get("research_board_prioritization")
    if not isinstance(prioritization, Mapping):
        return [f"{field_prefix}research_board_prioritization"]
    for field_name in _REQUIRED_RESEARCH_BOARD_PRIORITIZATION_FIELDS:
        if field_name not in prioritization:
            missing.append(f"{field_prefix}research_board_prioritization.{field_name}")
    if (
        packet.get("research_board_prioritization_version")
        != _RESEARCH_BOARD_PRIORITIZATION_VERSION
    ):
        missing.append(f"{field_prefix}research_board_prioritization_version")
    if (
        prioritization.get("research_board_prioritization_version")
        != _RESEARCH_BOARD_PRIORITIZATION_VERSION
    ):
        missing.append(
            f"{field_prefix}research_board_prioritization.research_board_prioritization_version"
        )
    if not str(packet.get("research_board_prioritization_path", "")).endswith(
        _RESEARCH_BOARD_PRIORITIZATION_FILENAME
    ):
        missing.append(f"{field_prefix}research_board_prioritization_path")
    if prioritization.get("prioritization_status") not in {"ranked", "not_ranked"}:
        missing.append(f"{field_prefix}research_board_prioritization.prioritization_status.allowed")
    if prioritization.get("research_mode") != "offline_research_planning_only":
        missing.append(f"{field_prefix}research_board_prioritization.research_mode")
    if prioritization.get("safety_scope") != "offline_only":
        missing.append(f"{field_prefix}research_board_prioritization.safety_scope")
    if prioritization.get("broker_state_mode") != "broker_state_not_observed":
        missing.append(f"{field_prefix}research_board_prioritization.broker_state_mode")
    if prioritization.get("paper_submit_authorized") is not False:
        missing.append(f"{field_prefix}research_board_prioritization.paper_submit_authorized")
    if prioritization.get("profit_claim") != "none":
        missing.append(f"{field_prefix}research_board_prioritization.profit_claim")
    if prioritization.get("hard_gate_required") is not False:
        missing.append(f"{field_prefix}research_board_prioritization.hard_gate_required")
    if prioritization.get("requires_daniel") is not False:
        missing.append(f"{field_prefix}research_board_prioritization.requires_daniel")
    if prioritization.get("daniel_action_required_now") is not False:
        missing.append(f"{field_prefix}research_board_prioritization.daniel_action_required_now")
    if prioritization.get("selected_next_safe_action") != "build_offline_strategy_comparison_scaffold":
        missing.append(f"{field_prefix}research_board_prioritization.selected_next_safe_action")
    return missing


def _missing_baseline_health_evaluation_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    evaluation = packet.get("baseline_health_evaluation")
    if not isinstance(evaluation, Mapping):
        return [f"{field_prefix}baseline_health_evaluation"]
    for field_name in _REQUIRED_BASELINE_HEALTH_EVALUATION_FIELDS:
        if field_name not in evaluation:
            missing.append(f"{field_prefix}baseline_health_evaluation.{field_name}")
    if (
        packet.get("baseline_health_evaluation_version")
        != _BASELINE_HEALTH_EVALUATION_VERSION
    ):
        missing.append(f"{field_prefix}baseline_health_evaluation_version")
    if (
        evaluation.get("baseline_health_evaluation_version")
        != _BASELINE_HEALTH_EVALUATION_VERSION
    ):
        missing.append(
            f"{field_prefix}baseline_health_evaluation.baseline_health_evaluation_version"
        )
    if not str(packet.get("baseline_health_evaluation_path", "")).strip():
        missing.append(f"{field_prefix}baseline_health_evaluation_path")
    if not str(evaluation.get("artifact_path", "")).strip():
        missing.append(f"{field_prefix}baseline_health_evaluation.artifact_path")
    if evaluation.get("status") not in {"generated", "not_generated"}:
        missing.append(f"{field_prefix}baseline_health_evaluation.status.allowed")
    if evaluation.get("health_status") not in _BASELINE_HEALTH_STATUSES:
        missing.append(
            f"{field_prefix}baseline_health_evaluation.health_status.allowed"
        )
    if evaluation.get("evidence_status") not in _BASELINE_EVIDENCE_STATUSES:
        missing.append(
            f"{field_prefix}baseline_health_evaluation.evidence_status.allowed"
        )
    if evaluation.get("baseline_evidence_snapshot_status") not in _BASELINE_METRIC_STATUSES:
        missing.append(
            f"{field_prefix}baseline_health_evaluation.baseline_evidence_snapshot_status.allowed"
        )
    if (
        evaluation.get("baseline_metric_confidence_status")
        not in _BASELINE_METRIC_CONFIDENCE_STATUSES
    ):
        missing.append(
            f"{field_prefix}baseline_health_evaluation.baseline_metric_confidence_status"
        )
    if (
        evaluation.get("baseline_metric_artifact_ingest_status")
        not in _BASELINE_METRIC_ARTIFACT_INGEST_STATUSES
    ):
        missing.append(
            f"{field_prefix}baseline_health_evaluation.baseline_metric_artifact_ingest_status"
        )
    if not isinstance(
        evaluation.get("baseline_metric_artifact_parse_status"), Mapping
    ):
        missing.append(
            f"{field_prefix}baseline_health_evaluation.baseline_metric_artifact_parse_status.object"
        )
    if not isinstance(
        evaluation.get("baseline_remaining_missing_metric_sources"), list
    ):
        missing.append(
            f"{field_prefix}baseline_health_evaluation.baseline_remaining_missing_metric_sources.list"
        )
    if not str(evaluation.get("paper_observation_readiness_path", "")).endswith(
        _PAPER_OBSERVATION_READINESS_FILENAME
    ):
        missing.append(
            f"{field_prefix}baseline_health_evaluation.paper_observation_readiness_path"
        )
    if not isinstance(evaluation.get("paper_observation_readiness"), Mapping):
        missing.append(
            f"{field_prefix}baseline_health_evaluation.paper_observation_readiness.object"
        )
    if not str(evaluation.get("baseline_evidence_metrics_path", "")).strip():
        missing.append(
            f"{field_prefix}baseline_health_evaluation.baseline_evidence_metrics_path"
        )
    if not str(evaluation.get("next_safe_metric_command", "")).strip():
        missing.append(
            f"{field_prefix}baseline_health_evaluation.next_safe_metric_command"
        )
    if evaluation.get("active_symbol") != _DEFAULT_SYMBOL:
        missing.append(f"{field_prefix}baseline_health_evaluation.active_symbol")
    if evaluation.get("active_strategy") != "SMA 50/200":
        missing.append(f"{field_prefix}baseline_health_evaluation.active_strategy")
    if evaluation.get("broker_state_mode") not in {
        "broker_state_not_observed",
        "offline_preview_only",
    }:
        missing.append(f"{field_prefix}baseline_health_evaluation.broker_state_mode")
    if evaluation.get("paper_submit_readiness_status") != "not_ready_for_paper_submit":
        missing.append(
            f"{field_prefix}baseline_health_evaluation.paper_submit_readiness_status"
        )
    if evaluation.get("next_safe_test") != _BASELINE_HEALTH_NEXT_SAFE_TEST:
        missing.append(f"{field_prefix}baseline_health_evaluation.next_safe_test")
    for list_field in (
        "known_strengths",
        "known_weaknesses",
        "missing_evidence",
        "required_next_artifacts",
        "promotion_criteria",
        "deprecation_criteria",
    ):
        if list_field in evaluation and not isinstance(evaluation.get(list_field), list):
            missing.append(
                f"{field_prefix}baseline_health_evaluation.{list_field}.list"
            )
    for bool_field in ("requires_daniel", "hard_gate_required"):
        if bool_field in evaluation and not isinstance(evaluation.get(bool_field), bool):
            missing.append(
                f"{field_prefix}baseline_health_evaluation.{bool_field}.bool"
            )
    serialized = json.dumps(
        _json_safe(evaluation),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    if "broker_state_not_observed" not in serialized:
        missing.append(
            f"{field_prefix}baseline_health_evaluation.broker_state_not_observed"
        )
    if "offline_preview_only" not in serialized:
        missing.append(
            f"{field_prefix}baseline_health_evaluation.offline_preview_only"
        )
    return missing


def _missing_baseline_evidence_metrics_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    metrics = packet.get("baseline_evidence_metrics")
    if not isinstance(metrics, Mapping):
        return [f"{field_prefix}baseline_evidence_metrics"]
    for field_name in _REQUIRED_BASELINE_EVIDENCE_METRICS_FIELDS:
        if field_name not in metrics:
            missing.append(f"{field_prefix}baseline_evidence_metrics.{field_name}")
    if (
        packet.get("baseline_evidence_metrics_version")
        != _BASELINE_EVIDENCE_METRICS_VERSION
    ):
        missing.append(f"{field_prefix}baseline_evidence_metrics_version")
    if (
        metrics.get("baseline_evidence_metrics_version")
        != _BASELINE_EVIDENCE_METRICS_VERSION
    ):
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.baseline_evidence_metrics_version"
        )
    if not str(packet.get("baseline_evidence_metrics_path", "")).strip():
        missing.append(f"{field_prefix}baseline_evidence_metrics_path")
    if not str(metrics.get("artifact_path", "")).strip():
        missing.append(f"{field_prefix}baseline_evidence_metrics.artifact_path")
    if metrics.get("status") not in {"generated", "not_generated"}:
        missing.append(f"{field_prefix}baseline_evidence_metrics.status.allowed")
    for status_field in (
        "evidence_snapshot_status",
        "backtest_confidence_summary_status",
        "benchmark_metric_status",
        "benchmark_comparison_status",
        "backtest_metric_status",
        "drawdown_metric_status",
        "turnover_metric_status",
        "cost_model_status",
        "sample_window_status",
        "adjusted_close_basis_status",
        "paper_observation_status",
    ):
        if metrics.get(status_field) not in _BASELINE_METRIC_STATUSES:
            missing.append(
                f"{field_prefix}baseline_evidence_metrics.{status_field}.allowed"
            )
    if (
        metrics.get("metric_confidence_status")
        not in _BASELINE_METRIC_CONFIDENCE_STATUSES
    ):
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.metric_confidence_status"
        )
    if (
        metrics.get("metric_artifact_ingest_status")
        not in _BASELINE_METRIC_ARTIFACT_INGEST_STATUSES
    ):
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.metric_artifact_ingest_status"
        )
    if metrics.get("turnover_artifact_ingest_status") not in {
        "turnover_artifact_missing",
        "turnover_artifact_ingested",
        "turnover_artifact_parse_failed",
    }:
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.turnover_artifact_ingest_status"
        )
    if metrics.get("cost_model_artifact_ingest_status") not in {
        "cost_model_artifact_missing",
        "cost_model_artifact_ingested",
        "cost_model_artifact_parse_failed",
    }:
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.cost_model_artifact_ingest_status"
        )
    for mapping_field in (
        "metric_artifact_paths",
        "metric_artifact_hashes",
        "metric_artifact_parse_status",
        "metric_artifact_record_count",
        "quantified_metric_summary",
    ):
        if not isinstance(metrics.get(mapping_field), Mapping):
            missing.append(
                f"{field_prefix}baseline_evidence_metrics.{mapping_field}.object"
            )
    for artifact_field, filename in (
        ("turnover_artifact_path", _BASELINE_TURNOVER_SUMMARY_FILENAME),
        ("cost_model_artifact_path", _BASELINE_COST_MODEL_SUMMARY_FILENAME),
    ):
        if not str(metrics.get(artifact_field, "")).endswith(filename):
            missing.append(
                f"{field_prefix}baseline_evidence_metrics.{artifact_field}"
            )
    for status_field in (
        "turnover_artifact_parse_status",
        "cost_model_artifact_parse_status",
    ):
        if metrics.get(status_field) not in _BASELINE_METRIC_ARTIFACT_PARSE_STATUSES:
            missing.append(
                f"{field_prefix}baseline_evidence_metrics.{status_field}"
            )
    for hash_field in ("turnover_artifact_hash", "cost_model_artifact_hash"):
        value = metrics.get(hash_field)
        if value is not None and not _sha256_text(value):
            missing.append(f"{field_prefix}baseline_evidence_metrics.{hash_field}")
    parse_status = metrics.get("metric_artifact_parse_status")
    record_count = metrics.get("metric_artifact_record_count")
    artifact_paths = metrics.get("metric_artifact_paths")
    if isinstance(parse_status, Mapping):
        for artifact_id, _filename in _BASELINE_METRIC_ARTIFACTS:
            status = parse_status.get(artifact_id)
            if status not in _BASELINE_METRIC_ARTIFACT_PARSE_STATUSES:
                missing.append(
                    f"{field_prefix}baseline_evidence_metrics.metric_artifact_parse_status.{artifact_id}"
                )
    if isinstance(record_count, Mapping):
        for artifact_id, _filename in _BASELINE_METRIC_ARTIFACTS:
            count = record_count.get(artifact_id)
            if not isinstance(count, int) or count < 0:
                missing.append(
                    f"{field_prefix}baseline_evidence_metrics.metric_artifact_record_count.{artifact_id}"
                )
    if isinstance(artifact_paths, Mapping):
        for artifact_id, filename in _BASELINE_METRIC_ARTIFACTS:
            path_text = str(artifact_paths.get(artifact_id, ""))
            if not path_text.endswith(filename):
                missing.append(
                    f"{field_prefix}baseline_evidence_metrics.metric_artifact_paths.{artifact_id}"
                )
    if (
        metrics.get("metric_artifact_ingest_status") == "metric_artifacts_missing"
        and metrics.get("quantified_metric_summary") != {}
    ):
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.quantified_metric_summary.empty_when_missing"
        )
    if metrics.get("active_symbol") != _DEFAULT_SYMBOL:
        missing.append(f"{field_prefix}baseline_evidence_metrics.active_symbol")
    if metrics.get("active_strategy") != "SMA 50/200":
        missing.append(f"{field_prefix}baseline_evidence_metrics.active_strategy")
    if metrics.get("broker_state_mode") not in {
        "broker_state_not_observed",
        "offline_preview_only",
    }:
        missing.append(f"{field_prefix}baseline_evidence_metrics.broker_state_mode")
    if metrics.get("paper_submit_readiness_status") != "not_ready_for_paper_submit":
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.paper_submit_readiness_status"
        )
    if not str(metrics.get("paper_observation_readiness_path", "")).endswith(
        _PAPER_OBSERVATION_READINESS_FILENAME
    ):
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.paper_observation_readiness_path"
        )
    if not isinstance(metrics.get("paper_observation_readiness"), Mapping):
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.paper_observation_readiness.object"
        )
    if metrics.get("profit_claim") != "none":
        missing.append(f"{field_prefix}baseline_evidence_metrics.profit_claim")
    for list_field in (
        "available_metric_sources",
        "missing_metric_sources",
        "remaining_missing_metric_sources",
        "required_next_artifacts",
        "artifact_prerequisite_chain",
        "promotion_criteria",
        "deprecation_criteria",
    ):
        if list_field in metrics and not isinstance(metrics.get(list_field), list):
            missing.append(
                f"{field_prefix}baseline_evidence_metrics.{list_field}.list"
            )
    if not str(metrics.get("next_safe_metric_command", "")).strip():
        missing.append(
            f"{field_prefix}baseline_evidence_metrics.next_safe_metric_command"
        )
    for bool_field in ("requires_daniel", "hard_gate_required"):
        if bool_field in metrics and not isinstance(metrics.get(bool_field), bool):
            missing.append(
                f"{field_prefix}baseline_evidence_metrics.{bool_field}.bool"
            )
    serialized = json.dumps(
        _json_safe(metrics),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    for token in (
        "broker_state_not_observed",
        "offline_preview_only",
        "profit_claim",
        "none",
    ):
        if token not in serialized:
            missing.append(f"{field_prefix}baseline_evidence_metrics.{token}")
    return missing


def _missing_next_action_selector_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    selector = packet.get("next_action_selector")
    if not isinstance(selector, Mapping):
        return [f"{field_prefix}next_action_selector"]

    missing: list[str] = []
    required_fields = (
        "next_action_selector_version",
        "status",
        "priority",
        "selected_next_action_id",
        "selected_next_action_type",
        "selected_work_order",
        "selected_work_order_path",
        "selected_owner",
        "selected_research_candidate_id",
        "selected_research_candidate_priority",
        "selected_research_candidate_title",
        "research_candidate_queue_path",
        "rationale",
        "reason_codes",
        "blocks_offline_build",
        "requires_daniel",
        "hard_gate_required",
        "broker_action_allowed",
        "capital_action_allowed",
        "llm_runtime_calls_allowed",
        "network_runtime_calls_allowed",
        "safety_scope",
        "forbidden_actions",
        "paper_observation_readiness_path",
        "paper_observation_readiness",
        "research_board_prioritization_path",
        "research_board_prioritization",
        "source_state",
    )
    for field_name in required_fields:
        if field_name not in selector:
            missing.append(f"{field_prefix}next_action_selector.{field_name}")
    if selector.get("next_action_selector_version") != _NEXT_ACTION_SELECTOR_VERSION:
        missing.append(
            f"{field_prefix}next_action_selector.next_action_selector_version"
        )
    if selector.get("priority") not in _ACTION_PRIORITIES:
        missing.append(f"{field_prefix}next_action_selector.priority.allowed")
    if selector.get("selected_work_order") not in {
        artifact_id for artifact_id, _filename, _audience, _purpose in _WORK_ORDER_ARTIFACTS
    }:
        missing.append(
            f"{field_prefix}next_action_selector.selected_work_order.allowed"
        )
    for bool_field in (
        "blocks_offline_build",
        "requires_daniel",
        "hard_gate_required",
        "broker_action_allowed",
        "capital_action_allowed",
        "llm_runtime_calls_allowed",
        "network_runtime_calls_allowed",
    ):
        if bool_field in selector and not isinstance(selector.get(bool_field), bool):
            missing.append(f"{field_prefix}next_action_selector.{bool_field}.bool")
    for false_field in (
        "broker_action_allowed",
        "capital_action_allowed",
        "llm_runtime_calls_allowed",
        "network_runtime_calls_allowed",
    ):
        if selector.get(false_field) is not False:
            missing.append(f"{field_prefix}next_action_selector.{false_field}.false")
    if not isinstance(selector.get("reason_codes"), list):
        missing.append(f"{field_prefix}next_action_selector.reason_codes.list")
    if not isinstance(selector.get("forbidden_actions"), list):
        missing.append(f"{field_prefix}next_action_selector.forbidden_actions.list")
    if not isinstance(selector.get("source_state"), Mapping):
        missing.append(f"{field_prefix}next_action_selector.source_state.object")
    if not str(selector.get("paper_observation_readiness_path", "")).endswith(
        _PAPER_OBSERVATION_READINESS_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector.paper_observation_readiness_path"
        )
    if not isinstance(selector.get("paper_observation_readiness"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector.paper_observation_readiness.object"
        )
    if not str(selector.get("research_board_prioritization_path", "")).endswith(
        _RESEARCH_BOARD_PRIORITIZATION_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector.research_board_prioritization_path"
        )
    if not isinstance(selector.get("research_board_prioritization"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector.research_board_prioritization.object"
        )
    if not str(selector.get("research_candidate_queue_path", "")).strip():
        missing.append(f"{field_prefix}next_action_selector.research_candidate_queue_path")
    selected_candidate_priority = selector.get("selected_research_candidate_priority")
    if (
        selected_candidate_priority is not None
        and selected_candidate_priority not in _ACTION_PRIORITIES
    ):
        missing.append(
            f"{field_prefix}next_action_selector.selected_research_candidate_priority.allowed"
        )
    selected_action_id = str(selector.get("selected_next_action_id", ""))
    if not selected_action_id.strip():
        missing.append(f"{field_prefix}next_action_selector.selected_next_action_id")
    elif _selector_contains_forbidden_action(selected_action_id):
        missing.append(f"{field_prefix}next_action_selector.selected_next_action_id.safe")
    selected_path = str(selector.get("selected_work_order_path", ""))
    if f"{_WORK_ORDERS_DIRNAME}/" not in selected_path.replace("\\", "/"):
        missing.append(
            f"{field_prefix}next_action_selector.selected_work_order_path.work_orders"
        )
    return missing


def _missing_work_order_export_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    exports = packet.get("work_order_exports")
    if not isinstance(exports, Mapping):
        return [f"{field_prefix}work_order_exports"]

    missing: list[str] = []
    required_fields = (
        "work_order_exports_version",
        "status",
        "directory",
        "artifact_count",
        "generation_mode",
        "runtime_callouts_performed",
        "research_candidate_queue_path",
        "baseline_evidence_metrics_path",
        "paper_observation_readiness_path",
        "paper_observation_readiness",
        "paper_observation_readiness_status",
        "research_board_prioritization_path",
        "research_board_prioritization",
        "research_board_prioritization_status",
        "metric_artifact_ingest_status",
        "turnover_artifact_ingest_status",
        "cost_model_artifact_ingest_status",
        "turnover_metric_status",
        "cost_model_status",
        "metric_artifact_paths",
        "metric_artifact_hashes",
        "metric_artifact_parse_status",
        "metric_artifact_record_count",
        "turnover_artifact_path",
        "cost_model_artifact_path",
        "turnover_artifact_hash",
        "cost_model_artifact_hash",
        "turnover_artifact_parse_status",
        "cost_model_artifact_parse_status",
        "remaining_missing_metric_sources",
        "next_safe_metric_command",
        "artifact_prerequisite_chain",
        "top_research_candidate_id",
        "selected_research_candidate_id",
        "safety_scope",
        "artifacts",
    )
    for field_name in required_fields:
        if field_name not in exports:
            missing.append(f"{field_prefix}work_order_exports.{field_name}")
    if exports.get("work_order_exports_version") != _WORK_ORDER_EXPORTS_VERSION:
        missing.append(
            f"{field_prefix}work_order_exports.work_order_exports_version"
        )
    if exports.get("status") not in {"generated", "not_generated"}:
        missing.append(f"{field_prefix}work_order_exports.status.allowed")
    if exports.get("artifact_count") != len(_WORK_ORDER_ARTIFACTS):
        missing.append(f"{field_prefix}work_order_exports.artifact_count")
    if exports.get("runtime_callouts_performed") is not False:
        missing.append(
            f"{field_prefix}work_order_exports.runtime_callouts_performed.false"
        )
    if not str(exports.get("research_candidate_queue_path", "")).strip():
        missing.append(f"{field_prefix}work_order_exports.research_candidate_queue_path")
    if not str(exports.get("baseline_evidence_metrics_path", "")).strip():
        missing.append(
            f"{field_prefix}work_order_exports.baseline_evidence_metrics_path"
        )
    if not str(exports.get("paper_observation_readiness_path", "")).endswith(
        _PAPER_OBSERVATION_READINESS_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports.paper_observation_readiness_path"
        )
    if not isinstance(exports.get("paper_observation_readiness"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports.paper_observation_readiness.object"
        )
    if not str(exports.get("paper_observation_readiness_status", "")).strip():
        missing.append(
            f"{field_prefix}work_order_exports.paper_observation_readiness_status"
        )
    if not str(exports.get("research_board_prioritization_path", "")).endswith(
        _RESEARCH_BOARD_PRIORITIZATION_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports.research_board_prioritization_path"
        )
    if not isinstance(exports.get("research_board_prioritization"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports.research_board_prioritization.object"
        )
    if not str(exports.get("research_board_prioritization_status", "")).strip():
        missing.append(
            f"{field_prefix}work_order_exports.research_board_prioritization_status"
        )
    if (
        exports.get("metric_artifact_ingest_status")
        not in _BASELINE_METRIC_ARTIFACT_INGEST_STATUSES
    ):
        missing.append(f"{field_prefix}work_order_exports.metric_artifact_ingest_status")
    if exports.get("turnover_artifact_ingest_status") not in {
        "turnover_artifact_missing",
        "turnover_artifact_ingested",
        "turnover_artifact_parse_failed",
    }:
        missing.append(
            f"{field_prefix}work_order_exports.turnover_artifact_ingest_status"
        )
    if exports.get("cost_model_artifact_ingest_status") not in {
        "cost_model_artifact_missing",
        "cost_model_artifact_ingested",
        "cost_model_artifact_parse_failed",
    }:
        missing.append(
            f"{field_prefix}work_order_exports.cost_model_artifact_ingest_status"
        )
    for status_field in ("turnover_metric_status", "cost_model_status"):
        if exports.get(status_field) not in _BASELINE_METRIC_STATUSES:
            missing.append(f"{field_prefix}work_order_exports.{status_field}")
    for mapping_field in (
        "metric_artifact_paths",
        "metric_artifact_hashes",
        "metric_artifact_parse_status",
        "metric_artifact_record_count",
    ):
        if not isinstance(exports.get(mapping_field), Mapping):
            missing.append(f"{field_prefix}work_order_exports.{mapping_field}.object")
    if not isinstance(exports.get("remaining_missing_metric_sources"), list):
        missing.append(
            f"{field_prefix}work_order_exports.remaining_missing_metric_sources.list"
        )
    for artifact_field, filename in (
        ("turnover_artifact_path", _BASELINE_TURNOVER_SUMMARY_FILENAME),
        ("cost_model_artifact_path", _BASELINE_COST_MODEL_SUMMARY_FILENAME),
    ):
        if not str(exports.get(artifact_field, "")).endswith(filename):
            missing.append(f"{field_prefix}work_order_exports.{artifact_field}")
    for status_field in (
        "turnover_artifact_parse_status",
        "cost_model_artifact_parse_status",
    ):
        if exports.get(status_field) not in _BASELINE_METRIC_ARTIFACT_PARSE_STATUSES:
            missing.append(f"{field_prefix}work_order_exports.{status_field}")
    for hash_field in ("turnover_artifact_hash", "cost_model_artifact_hash"):
        value = exports.get(hash_field)
        if value is not None and not _sha256_text(value):
            missing.append(f"{field_prefix}work_order_exports.{hash_field}")
    if not str(exports.get("next_safe_metric_command", "")).strip():
        missing.append(f"{field_prefix}work_order_exports.next_safe_metric_command")
    if not isinstance(exports.get("artifact_prerequisite_chain"), list):
        missing.append(
            f"{field_prefix}work_order_exports.artifact_prerequisite_chain.list"
        )
    for optional_text_field in (
        "top_research_candidate_id",
        "selected_research_candidate_id",
    ):
        if optional_text_field in exports and exports.get(optional_text_field) is not None:
            if not str(exports.get(optional_text_field, "")).strip():
                missing.append(f"{field_prefix}work_order_exports.{optional_text_field}")
    artifacts = exports.get("artifacts")
    if not isinstance(artifacts, Mapping):
        missing.append(f"{field_prefix}work_order_exports.artifacts")
        return missing
    for artifact_id, _filename, audience, purpose in _WORK_ORDER_ARTIFACTS:
        artifact = artifacts.get(artifact_id)
        artifact_prefix = f"{field_prefix}work_order_exports.artifacts.{artifact_id}"
        if not isinstance(artifact, Mapping):
            missing.append(artifact_prefix)
            continue
        if not str(artifact.get("path", "")).strip():
            missing.append(f"{artifact_prefix}.path")
        if artifact.get("audience") != audience:
            missing.append(f"{artifact_prefix}.audience")
        if artifact.get("purpose") != purpose:
            missing.append(f"{artifact_prefix}.purpose")
        if artifact.get("status") not in {"generated", "not_generated"}:
            missing.append(f"{artifact_prefix}.status")
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
    if "## Baseline Health Evaluation" not in brief_text:
        missing.append("operating_brief.baseline_health_evaluation.section")
    baseline_health = packet.get("baseline_health_evaluation")
    if isinstance(baseline_health, Mapping):
        for field_name in (
            "health_status",
            "evidence_status",
            "baseline_evidence_snapshot_status",
            "next_safe_test",
            "next_safe_metric_command",
        ):
            value = baseline_health.get(field_name)
            if _has_required_value(value) and str(value) not in brief_text:
                missing.append(
                    f"operating_brief.baseline_health_evaluation.{field_name}"
                )
    baseline_health_path = packet.get("baseline_health_evaluation_path")
    if (
        _has_required_value(baseline_health_path)
        and str(baseline_health_path) not in brief_text
    ):
        missing.append("operating_brief.baseline_health_evaluation_path")
    if "## Baseline Evidence Metrics" not in brief_text:
        missing.append("operating_brief.baseline_evidence_metrics.section")
    baseline_metrics = packet.get("baseline_evidence_metrics")
    if isinstance(baseline_metrics, Mapping):
        for field_name in (
            "evidence_snapshot_status",
            "metric_confidence_status",
            "next_safe_metric_command",
        ):
            value = baseline_metrics.get(field_name)
            if _has_required_value(value) and str(value) not in brief_text:
                missing.append(
                    f"operating_brief.baseline_evidence_metrics.{field_name}"
                )
    baseline_metrics_path = packet.get("baseline_evidence_metrics_path")
    if (
        _has_required_value(baseline_metrics_path)
        and str(baseline_metrics_path) not in brief_text
    ):
        missing.append("operating_brief.baseline_evidence_metrics_path")
    if "Quality Gate" not in brief_text:
        missing.append("operating_brief.quality_gate")
    if "Decision Ledger" not in brief_text:
        missing.append("operating_brief.decision_ledger")
    if "## Next Action Selector" not in brief_text:
        missing.append("operating_brief.next_action_selector.section")
    if "Work order exports" not in brief_text:
        missing.append("operating_brief.work_order_exports")
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
    selector = packet.get("next_action_selector")
    if isinstance(selector, Mapping):
        selected_action = str(selector.get("selected_next_action_id", ""))
        selected_path = str(selector.get("selected_work_order_path", ""))
        if selected_action and selected_action not in brief_text:
            missing.append("operating_brief.next_action_selector.selected_action")
        if selected_path and selected_path not in brief_text:
            missing.append("operating_brief.next_action_selector.selected_path")
    work_order_exports = packet.get("work_order_exports")
    if isinstance(work_order_exports, Mapping):
        artifacts = work_order_exports.get("artifacts")
        if isinstance(artifacts, Mapping):
            for artifact_id, artifact in artifacts.items():
                if not isinstance(artifact, Mapping):
                    continue
                path = str(artifact.get("path", ""))
                if path and path not in brief_text:
                    missing.append(f"operating_brief.work_order_exports.{artifact_id}")
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
                "drawdown_review",
                "cost_model_requires_real_fill_data_for_cost_estimates",
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


def _render_gpt_next_action_handoff(payload: Mapping[str, Any]) -> str:
    selector = payload["next_action_selector"]
    exports = payload["work_order_exports"]
    return _render_work_order_markdown(
        title="GPT Next Action Handoff",
        audience="GPT",
        orientation=(
            "Source-of-truth routing handoff. Classify the packet state and decide "
            "whether the selected next action should proceed, be repaired, or be "
            "sent back for more offline review input."
        ),
        payload=payload,
        extra_sections=f"""## GPT classification focus
* **Current assistant packet status**: `{payload["system_health"]}`
* **Quality gate status**: `{payload["quality_gate_status"]}` ({payload["quality_gate_score"]})
* **Decision-ledger status**: `{payload["decision_ledger_status"]}`; review classification `{payload["review_classification"]}`
* **Executive action queue**:
{_render_review_action_queue(payload["executive_action_queue"])}
* **Research board**:
{_render_review_research_board(payload["research_board"])}
* **Safety assessment**: offline preview only; broker state `{payload["broker_state_mode"]}`; paper submit authorization `{payload["paper_submit_authorization_status"]}`.
* **Selected next action**: `{selector["selected_next_action_id"]}` via `{selector["selected_work_order"]}`.
* **Files/artifacts generated**:
{_render_generated_artifacts(payload)}
* **Work-order exports**: `{exports["status"]}` in `{exports["directory"]}`.

## What GPT should classify next
Classify whether the current packet and selected next action are `accepted`, `accepted-with-minor-note`, `needs-repair`, or `rejected`. If repair is needed, return concrete offline repair items only.
""",
    )


def _render_codex_work_order(payload: Mapping[str, Any]) -> str:
    selector = payload["next_action_selector"]
    return _render_work_order_markdown(
        title="Codex Work Order",
        audience="Codex",
        orientation=(
            "Implementation-oriented work order for safe offline packet, test, "
            "documentation, or research-support changes."
        ),
        payload=payload,
        extra_sections=f"""## Implementation target
* **Selected action**: `{selector["selected_next_action_id"]}`
* **Selected action type**: `{selector["selected_next_action_type"]}`
* **Selector rationale**: {selector["rationale"]}
* **Expected implementation stance**: keep changes scoped to offline deterministic packet artifacts, tests, and docs. Do not add broker, SDK, network, LLM, browser, notebook, paid-service, credential, paper-submit, or live-trading behavior.

## Allowed files and surfaces
* `src/algotrader/execution/etf_sma_daily_paper_lab.py`
* `tests/unit/test_etf_sma_daily_paper_lab.py`
* `task.md`
* A small focused helper module/test only if it is needed to keep the main file maintainable.
* Generated runtime artifacts under the selected output root may be inspected but must not be staged or tracked.
""",
    )


def _render_antigravity_review_order(payload: Mapping[str, Any]) -> str:
    selector = payload["next_action_selector"]
    return _render_work_order_markdown(
        title="Antigravity Review Order",
        audience="Antigravity",
        orientation=(
            "Independent repo-health and implementation-review order. Focus on "
            "dependency direction, offline determinism, artifact integrity, and "
            "whether the selected next action is correctly scoped."
        ),
        payload=payload,
        extra_sections=f"""## Review focus
* Confirm the selected action `{selector["selected_next_action_id"]}` follows the deterministic priority rules.
* Inspect repo-health risks, dependency direction, default-pytest network safety, and generated artifact consistency.
* Review whether any implementation would broaden broker, network, SDK, LLM, browser, notebook, paid-service, credential, paper-submit, or live-trading surfaces.
* Return actionable findings only; GPT remains source of truth for final classification.
""",
    )


def _render_claude_critique_order(payload: Mapping[str, Any]) -> str:
    selector = payload["next_action_selector"]
    return _render_work_order_markdown(
        title="Claude Critique Order",
        audience="Claude",
        orientation=(
            "Independent critique/audit order. Challenge assumptions, identify "
            "safety regressions, and evaluate packet clarity without acting as "
            "source of truth."
        ),
        payload=payload,
        extra_sections=f"""## Critique focus
* Audit the selected action `{selector["selected_next_action_id"]}` and explain whether the selector should have chosen a higher-priority safety, repair, review-ingest, or offline build action.
* Check safety wording, broker-state wording, quality-gate claims, decision-ledger handling, executive action queue order, and research-board claims.
* Do not approve live trading, paper submits, broker reads, capital actions, credential use, or runtime LLM/agent calls.
* Return critique findings for GPT/Daniel review; Claude is not the source of truth.
""",
    )


def _render_work_order_markdown(
    *,
    title: str,
    audience: str,
    orientation: str,
    payload: Mapping[str, Any],
    extra_sections: str,
) -> str:
    selector = payload["next_action_selector"]
    queue = payload["research_candidate_queue"]
    baseline_health = payload["baseline_health_evaluation"]
    baseline_metrics = payload["baseline_evidence_metrics"]
    readiness = payload["paper_observation_readiness"]
    readiness_json = _json_markdown(readiness)
    prioritization = payload["research_board_prioritization"]
    prioritization_json = _json_markdown(prioritization)
    selected_candidate_id = selector.get("selected_research_candidate_id")
    selected_candidate = (
        _research_candidate_by_id(payload, str(selected_candidate_id))
        if selected_candidate_id is not None
        else None
    )
    selected_candidate_json = _json_markdown(
        dict(selected_candidate) if selected_candidate is not None else {}
    )
    return f"""# {title}

## Phase
* **Phase name**: {_PHASE_NAME}
* **Goal**: {_PHASE_GOAL}
* **Project location**: `{Path.cwd()}`
* **Audience**: {audience}
* **Orientation**: {orientation}

## Current packet identity
* **packet_type**: `{payload["packet_type"]}`
* **run_id**: `{payload["run_id"]}`
* **as_of_date**: `{payload["as_of_date"]}`
* **active_strategy_name**: {payload["active_strategy_name"]}
* **output_root**: `{_review_output_root(payload)}`
* **assistant_packet_version**: `{payload["assistant_packet_version"]}`

## Selected next action
```json
{_json_markdown(selector)}
```

## Research candidate queue
* **Queue artifact**: `{payload["research_candidate_queue_path"]}`
* **Queue status**: `{queue["status"]}`
* **Top candidate**: `{queue["top_candidate_id"]}` ({queue["top_candidate_priority"]})
* **Selected safe candidate**: `{queue["selected_safe_candidate_id"]}` ({queue["selected_safe_candidate_priority"]})
* **Selector candidate reference**: `{selector["selected_research_candidate_id"]}`

```json
{selected_candidate_json}
```

## Baseline health evaluation
* **Health status**: `{baseline_health["health_status"]}`
* **Evidence status**: `{baseline_health["evidence_status"]}`
* **Metrics snapshot status**: `{baseline_health["baseline_evidence_snapshot_status"]}`
* **Confidence status**: `{baseline_health["confidence_status"]}`
* **Artifact**: `{payload["baseline_health_evaluation_path"]}`
* **Selected next safe test**: `{baseline_health["next_safe_test"]}`
* **Selected next safe metric command**: `{baseline_health["next_safe_metric_command"]}`
* **Safety scope**: `{baseline_health["safety_scope"]}`

## Baseline evidence metrics
* **Artifact**: `{payload["baseline_evidence_metrics_path"]}`
* **Evidence snapshot status**: `{baseline_metrics["evidence_snapshot_status"]}`
* **Metric confidence status**: `{baseline_metrics["metric_confidence_status"]}`
* **Metric artifact ingest status**: `{baseline_metrics["metric_artifact_ingest_status"]}`
* **Metric artifact parse status**: `{baseline_metrics["metric_artifact_parse_status"]}`
* **Metric artifact hashes**: `{baseline_metrics["metric_artifact_hashes"]}`
* **Turnover artifact ingest status**: `{baseline_metrics["turnover_artifact_ingest_status"]}`
* **Cost-model artifact ingest status**: `{baseline_metrics["cost_model_artifact_ingest_status"]}`
* **Turnover metric status**: `{baseline_metrics["turnover_metric_status"]}`
* **Cost-model status**: `{baseline_metrics["cost_model_status"]}`
* **next_safe_metric_command**: `{baseline_metrics["next_safe_metric_command"]}`
* **Available metric sources**: {", ".join(baseline_metrics["available_metric_sources"])}
* **Remaining missing metric sources**: {", ".join(baseline_metrics["remaining_missing_metric_sources"])}

## Paper observation readiness
* **Artifact**: `{payload["paper_observation_readiness_path"]}`
* **Readiness status**: `{readiness["readiness_status"]}`
* **Remaining gap**: `{readiness["remaining_gap"]}`
* **Hard gate required**: {str(readiness["hard_gate_required"]).lower()}
* **Requires Daniel**: {str(readiness["requires_daniel"]).lower()}
* **Broker-state mode**: `{readiness["broker_state_mode"]}`
* **Paper submit authorized**: {str(readiness["paper_submit_authorized"]).lower()}
* **Profit claim**: `{readiness["profit_claim"]}`
* **Approval phrase required**: `{readiness["approval_phrase_required"]}`
```json
{readiness_json}
```

## Research board prioritization
* **Artifact**: `{payload["research_board_prioritization_path"]}`
* **Prioritization status**: `{prioritization["prioritization_status"]}`
* **Research mode**: `{prioritization["research_mode"]}`
* **Candidate count**: {prioritization["candidate_count"]}
* **Top candidate**: `{prioritization["top_candidate"]}`
* **Selected next safe action**: `{prioritization["selected_next_safe_action"]}`
* **Why selected**: {prioritization["why_selected"]}
* **Why not broker observation yet**: {prioritization["why_not_broker_observation_yet"]}
* **Hard gate required**: {str(prioritization["hard_gate_required"]).lower()}
* **Requires Daniel**: {str(prioritization["requires_daniel"]).lower()}
* **Daniel action required now**: {str(prioritization["daniel_action_required_now"]).lower()}
* **Safety scope**: `{prioritization["safety_scope"]}`
* **Broker-state mode**: `{prioritization["broker_state_mode"]}`
* **Paper submit authorized**: {str(prioritization["paper_submit_authorized"]).lower()}
* **Profit claim**: `{prioritization["profit_claim"]}`
```json
{prioritization_json}
```

## Prerequisite artifact chain
{_render_bullets(list(baseline_metrics["artifact_prerequisite_chain"]))}

{extra_sections}

## Forbidden behavior
{_render_bullets(_forbidden_behavior_lines())}

## Safety constraints
* Normal pytest must remain offline, credential-free, deterministic, and safe.
* Preserve `paper_lab_only`, `not_live_authorized`, `profit_claim=none`, `offline_only`, `broker_state_not_observed`, and `paper_submit_not_authorized` safety labels.
* Preserve `ExecutionIntent`/`ExecutionPlan` pre-broker boundaries and dependency-direction safety.
* Runtime code must not call GPT, Codex, Claude, Antigravity, agents, LLMs, browsers, network APIs, broker APIs, notebooks, or external services.
* Work-order files are offline text artifacts only.

## Required tests
* `python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py`
* `python -m pytest tests\\unit\\test_dependency_direction.py tests\\unit\\test_broker_mutation_surface_invariant.py tests\\unit\\test_default_pytest_network_guard.py`
* `.\\scripts\\verify_offline.ps1`
* `.\\scripts\\run_daily_paper_lab.ps1 -OutputRoot runs/daily_lab/v_assistant_v1_12_smoke`
* Full `python -m pytest` only after the required credential/profile preflight booleans are all false.

## Expected artifacts
* `operating_brief.md`
* `operating_record.jsonl`
* `manifest.jsonl`
* `history_ledger.jsonl`
* `review_handoff.md`
* `research_candidate_queue.jsonl`
* `baseline_health_evaluation.jsonl`
* `baseline_evidence_metrics.jsonl`
* `paper_observation_readiness.jsonl`
* `baseline_authorized_adjusted_metrics.jsonl`
* `offline_backtest_confidence_summary.jsonl`
* `adjusted_close_evidence.jsonl`
* `turnover_summary.jsonl`
* `cost_model_summary.jsonl`
* `work_orders/gpt_next_action_handoff.md`
* `work_orders/codex_work_order.md`
* `work_orders/antigravity_review_order.md`
* `work_orders/claude_critique_order.md`

## Expected report format
1. Classification recommendation.
2. Starting branch and HEAD.
3. Preflight credential/profile booleans.
4. Files changed.
5. Commands added or changed.
6. Behavior implemented.
7. Output artifacts produced, including `paper_observation_readiness.jsonl`.
8. Quality gate result.
9. Tests run and exact results.
10. Safety assessment.
11. Broker-read/broker-mutation/paper-submit/live-trading confirmation.
12. Final `git status --short`.
13. Untracked files intentionally left untouched.
14. Recommended commit message.

## Commit instruction
Do not commit unless GPT/Daniel explicitly asks after review.
"""


def _json_markdown(value: Any) -> str:
    return json.dumps(_json_safe(value), indent=2, sort_keys=True)


def _render_bullets(items: list[str]) -> str:
    return "\n".join(f"* {item}" for item in items)


def _forbidden_behavior_lines() -> list[str]:
    return [
        "Do not perform broker reads.",
        "Do not perform broker mutation.",
        "Do not submit paper orders.",
        "Do not cancel, replace, close, close_all_positions, liquidate, delete, or retry broker mutation.",
        "Do not add live trading support.",
        "Do not add broker SDK imports.",
        "Do not add network calls.",
        "Do not call LLMs, agents, external tools, browser tools, notebooks, or paid services from runtime code.",
        "Do not request, load, or print secrets.",
        "Do not stage or track generated runtime artifacts under runs/.",
        "Do not weaken safety labels, broker-state wording, paper-submit lockout, or offline guarantees.",
        "Do not make normal pytest depend on credentials, broker access, market hours, network, or local runtime artifacts.",
    ]


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
    research_candidate_queue_lines = _render_research_candidate_queue(
        payload["research_candidate_queue"]
    )
    baseline_health_json = _json_markdown(payload["baseline_health_evaluation"])
    baseline_metrics_json = _json_markdown(payload["baseline_evidence_metrics"])
    readiness_json = _json_markdown(payload["paper_observation_readiness"])
    prioritization_json = _json_markdown(payload["research_board_prioritization"])
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
    selector = payload["next_action_selector"]
    selector_json = _json_markdown(selector)
    exports_json = _json_markdown(payload["work_order_exports"])

    return f"""# Daily Trading Research Command Center

## Executive summary
* **Recommendation**: {payload["current_recommendation"]}
* **Evidence**: {payload["executive_summary"]["plain_english_status"]} Preview decision: `{payload["preview_decision"]}`.
* **Risks / blockers**: {payload["blocker_status"]}. {payload["broker_state_claim"]} Paper submit authorization is `{payload["paper_submit_authorization_status"]}` (`paper_submit_authorized=false`).
* **Delta since prior packet**: {delta["delta_summary_text"]}
* **Review decision**: classification `{payload["review_classification"]}`; ledger status `{payload["decision_ledger_status"]}`; append status `{payload["decision_ledger_append_status"]}`.
* **Selected next action**: `{selector["selected_next_action_id"]}` via `{selector["selected_work_order_path"]}`.
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

## Research Candidate Queue
* **Queue artifact**: `{payload["research_candidate_queue_path"]}`
* **Queue status**: `{payload["research_candidate_queue"]["status"]}`
* **Top candidate**: `{payload["research_candidate_queue"]["top_candidate_id"]}` ({payload["research_candidate_queue"]["top_candidate_priority"]})
* **Selected safe candidate**: `{payload["research_candidate_queue"]["selected_safe_candidate_id"]}` ({payload["research_candidate_queue"]["selected_safe_candidate_priority"]})
* **Paper observation readiness**: `{payload["paper_observation_readiness"]["readiness_status"]}` at `{payload["paper_observation_readiness_path"]}`
{research_candidate_queue_lines}

## Baseline Health Evaluation
* **Artifact**: `{payload["baseline_health_evaluation_path"]}`
* **Health status**: `{payload["baseline_health_evaluation"]["health_status"]}`
* **Evidence status**: `{payload["baseline_health_evaluation"]["evidence_status"]}`
* **Metrics snapshot status**: `{payload["baseline_health_evaluation"]["baseline_evidence_snapshot_status"]}`
* **Selected next safe test**: `{payload["baseline_health_evaluation"]["next_safe_test"]}`
* **Selected next safe metric command**: `{payload["baseline_health_evaluation"]["next_safe_metric_command"]}`
```json
{baseline_health_json}
```

## Baseline Evidence Metrics
* **Artifact**: `{payload["baseline_evidence_metrics_path"]}`
* **Evidence snapshot status**: `{payload["baseline_evidence_metrics"]["evidence_snapshot_status"]}`
* **Metric confidence status**: `{payload["baseline_evidence_metrics"]["metric_confidence_status"]}`
* **Metric artifact ingest status**: `{payload["baseline_evidence_metrics"]["metric_artifact_ingest_status"]}`
* **Metric artifact parse status**: `{payload["baseline_evidence_metrics"]["metric_artifact_parse_status"]}`
* **Metric artifact hashes**: `{payload["baseline_evidence_metrics"]["metric_artifact_hashes"]}`
* **Turnover artifact ingest status**: `{payload["baseline_evidence_metrics"]["turnover_artifact_ingest_status"]}`
* **Cost-model artifact ingest status**: `{payload["baseline_evidence_metrics"]["cost_model_artifact_ingest_status"]}`
* **Benchmark comparison status**: `{payload["baseline_evidence_metrics"]["benchmark_comparison_status"]}`
* **Backtest metric status**: `{payload["baseline_evidence_metrics"]["backtest_metric_status"]}`
* **Drawdown metric status**: `{payload["baseline_evidence_metrics"]["drawdown_metric_status"]}`
* **Turnover metric status**: `{payload["baseline_evidence_metrics"]["turnover_metric_status"]}`
* **Cost model status**: `{payload["baseline_evidence_metrics"]["cost_model_status"]}`
* **Sample window status**: `{payload["baseline_evidence_metrics"]["sample_window_status"]}`
* **Adjusted-close basis status**: `{payload["baseline_evidence_metrics"]["adjusted_close_basis_status"]}`
* **Paper observation status**: `{payload["baseline_evidence_metrics"]["paper_observation_status"]}`
* **Remaining missing metric sources**: `{payload["baseline_evidence_metrics"]["remaining_missing_metric_sources"]}`
* **Next safe metric command**: `{payload["baseline_evidence_metrics"]["next_safe_metric_command"]}`
```json
{baseline_metrics_json}
```

## Paper Observation Readiness
* **Artifact**: `{payload["paper_observation_readiness_path"]}`
* **Readiness status**: `{payload["paper_observation_readiness"]["readiness_status"]}`
* **Remaining gap**: `{payload["paper_observation_readiness"]["remaining_gap"]}`
* **Hard gate required**: {str(payload["paper_observation_readiness"]["hard_gate_required"]).lower()}
* **Requires Daniel**: {str(payload["paper_observation_readiness"]["requires_daniel"]).lower()}
* **Broker-state mode**: `{payload["paper_observation_readiness"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["paper_observation_readiness"]["paper_submit_authorized"]).lower()}
* **Profit claim**: `{payload["paper_observation_readiness"]["profit_claim"]}`
* **Approval phrase required**: `{payload["paper_observation_readiness"]["approval_phrase_required"]}`
```json
{readiness_json}
```

## Research Board Prioritization
* **Artifact**: `{payload["research_board_prioritization_path"]}`
* **Prioritization status**: `{payload["research_board_prioritization"]["prioritization_status"]}`
* **Research mode**: `{payload["research_board_prioritization"]["research_mode"]}`
* **Candidate count**: {payload["research_board_prioritization"]["candidate_count"]}
* **Top candidate**: `{payload["research_board_prioritization"]["top_candidate"]}`
* **Selected next safe action**: `{payload["research_board_prioritization"]["selected_next_safe_action"]}`
* **Why selected**: {payload["research_board_prioritization"]["why_selected"]}
* **Why not broker observation yet**: {payload["research_board_prioritization"]["why_not_broker_observation_yet"]}
* **Hard gate required**: {str(payload["research_board_prioritization"]["hard_gate_required"]).lower()}
* **Requires Daniel**: {str(payload["research_board_prioritization"]["requires_daniel"]).lower()}
* **Daniel action required now**: {str(payload["research_board_prioritization"]["daniel_action_required_now"]).lower()}
* **Safety scope**: `{payload["research_board_prioritization"]["safety_scope"]}`
* **Broker-state mode**: `{payload["research_board_prioritization"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["research_board_prioritization"]["paper_submit_authorized"]).lower()}
* **Profit claim**: `{payload["research_board_prioritization"]["profit_claim"]}`
```json
{prioritization_json}
```

## Next Action Selector
```json
{selector_json}
```

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
* **Work order exports**:
```json
{exports_json}
```
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
    research_candidate_queue_lines = _render_research_candidate_queue(
        payload["research_candidate_queue"]
    )
    baseline_health_json = _json_markdown(payload["baseline_health_evaluation"])
    baseline_metrics_json = _json_markdown(payload["baseline_evidence_metrics"])
    readiness_json = _json_markdown(payload["paper_observation_readiness"])
    prioritization_json = _json_markdown(payload["research_board_prioritization"])
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
    selector_json = _json_markdown(payload["next_action_selector"])
    exports_json = _json_markdown(payload["work_order_exports"])
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

## Next action selector
```json
{selector_json}
```

## Work order exports
```json
{exports_json}
```

## Executive action queue
{action_lines}

## Research board
{research_lines}

## Research candidate queue
* **research_candidate_queue_version**: `{payload["research_candidate_queue_version"]}`
* **research_candidate_queue_path**: `{payload["research_candidate_queue_path"]}`
* **top_candidate_id**: `{payload["research_candidate_queue"]["top_candidate_id"]}`
* **selected_safe_candidate_id**: `{payload["research_candidate_queue"]["selected_safe_candidate_id"]}`
{research_candidate_queue_lines}

## Baseline health evaluation
* **baseline_health_evaluation_version**: `{payload["baseline_health_evaluation_version"]}`
* **baseline_health_evaluation_path**: `{payload["baseline_health_evaluation_path"]}`
* **health_status**: `{payload["baseline_health_evaluation"]["health_status"]}`
* **evidence_status**: `{payload["baseline_health_evaluation"]["evidence_status"]}`
* **baseline_evidence_snapshot_status**: `{payload["baseline_health_evaluation"]["baseline_evidence_snapshot_status"]}`
* **next_safe_test**: `{payload["baseline_health_evaluation"]["next_safe_test"]}`
* **next_safe_metric_command**: `{payload["baseline_health_evaluation"]["next_safe_metric_command"]}`
```json
{baseline_health_json}
```

## Baseline evidence metrics
* **baseline_evidence_metrics_version**: `{payload["baseline_evidence_metrics_version"]}`
* **baseline_evidence_metrics_path**: `{payload["baseline_evidence_metrics_path"]}`
* **evidence_snapshot_status**: `{payload["baseline_evidence_metrics"]["evidence_snapshot_status"]}`
* **metric_confidence_status**: `{payload["baseline_evidence_metrics"]["metric_confidence_status"]}`
* **metric_artifact_ingest_status**: `{payload["baseline_evidence_metrics"]["metric_artifact_ingest_status"]}`
* **metric_artifact_parse_status**: `{payload["baseline_evidence_metrics"]["metric_artifact_parse_status"]}`
* **metric_artifact_hashes**: `{payload["baseline_evidence_metrics"]["metric_artifact_hashes"]}`
* **turnover_artifact_ingest_status**: `{payload["baseline_evidence_metrics"]["turnover_artifact_ingest_status"]}`
* **cost_model_artifact_ingest_status**: `{payload["baseline_evidence_metrics"]["cost_model_artifact_ingest_status"]}`
* **remaining_missing_metric_sources**: `{payload["baseline_evidence_metrics"]["remaining_missing_metric_sources"]}`
* **next_safe_metric_command**: `{payload["baseline_evidence_metrics"]["next_safe_metric_command"]}`
```json
{baseline_metrics_json}
```

## Paper observation readiness
* **paper_observation_readiness_version**: `{payload["paper_observation_readiness_version"]}`
* **paper_observation_readiness_path**: `{payload["paper_observation_readiness_path"]}`
* **readiness_status**: `{payload["paper_observation_readiness"]["readiness_status"]}`
* **remaining_gap**: `{payload["paper_observation_readiness"]["remaining_gap"]}`
* **hard_gate_required**: {str(payload["paper_observation_readiness"]["hard_gate_required"]).lower()}
* **requires_daniel**: {str(payload["paper_observation_readiness"]["requires_daniel"]).lower()}
* **broker_state_mode**: `{payload["paper_observation_readiness"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["paper_observation_readiness"]["paper_submit_authorized"]).lower()}
* **profit_claim**: `{payload["paper_observation_readiness"]["profit_claim"]}`
* **approval_phrase_required**: `{payload["paper_observation_readiness"]["approval_phrase_required"]}`
```json
{readiness_json}
```

## Research board prioritization
* **research_board_prioritization_version**: `{payload["research_board_prioritization_version"]}`
* **research_board_prioritization_path**: `{payload["research_board_prioritization_path"]}`
* **prioritization_status**: `{payload["research_board_prioritization"]["prioritization_status"]}`
* **research_mode**: `{payload["research_board_prioritization"]["research_mode"]}`
* **candidate_count**: {payload["research_board_prioritization"]["candidate_count"]}
* **top_candidate**: `{payload["research_board_prioritization"]["top_candidate"]}`
* **selected_next_safe_action**: `{payload["research_board_prioritization"]["selected_next_safe_action"]}`
* **why_selected**: {payload["research_board_prioritization"]["why_selected"]}
* **why_not_broker_observation_yet**: {payload["research_board_prioritization"]["why_not_broker_observation_yet"]}
* **hard_gate_required**: {str(payload["research_board_prioritization"]["hard_gate_required"]).lower()}
* **requires_daniel**: {str(payload["research_board_prioritization"]["requires_daniel"]).lower()}
* **daniel_action_required_now**: {str(payload["research_board_prioritization"]["daniel_action_required_now"]).lower()}
* **safety_scope**: `{payload["research_board_prioritization"]["safety_scope"]}`
* **broker_state_mode**: `{payload["research_board_prioritization"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["research_board_prioritization"]["paper_submit_authorized"]).lower()}
* **profit_claim**: `{payload["research_board_prioritization"]["profit_claim"]}`
```json
{prioritization_json}
```

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
* **Verify**: required artifacts, quality gate result, validation status, action queue priority order, research candidate queue priority order, baseline-health evaluation status, baseline evidence metrics status, metric artifact ingest status, active SPY SMA 50/200 baseline, history delta, decision ledger status, safety labels, and broker-state wording.
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
        (
            "research_candidate_queue",
            artifact_paths.get("research_candidate_queue"),
        ),
        (
            "baseline_health_evaluation",
            artifact_paths.get("baseline_health_evaluation"),
        ),
        (
            "baseline_evidence_metrics",
            artifact_paths.get("baseline_evidence_metrics"),
        ),
        (
            "paper_observation_readiness",
            artifact_paths.get("paper_observation_readiness"),
        ),
        (
            "research_board_prioritization",
            artifact_paths.get("research_board_prioritization"),
        ),
        ("review_inputs", artifact_paths.get("review_inputs")),
        ("work_orders", artifact_paths.get("work_orders")),
        (
            "gpt_next_action_handoff",
            artifact_paths.get("gpt_next_action_handoff"),
        ),
        ("codex_work_order", artifact_paths.get("codex_work_order")),
        (
            "antigravity_review_order",
            artifact_paths.get("antigravity_review_order"),
        ),
        ("claude_critique_order", artifact_paths.get("claude_critique_order")),
    ]
    metrics = payload.get("baseline_evidence_metrics")
    if isinstance(metrics, Mapping):
        metric_artifact_paths = metrics.get("metric_artifact_paths")
        if isinstance(metric_artifact_paths, Mapping):
            ordered_artifacts.extend(
                (artifact_id, metric_artifact_paths.get(artifact_id))
                for artifact_id, _filename in _BASELINE_METRIC_ARTIFACTS
            )
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


def _render_research_candidate_queue(queue: Mapping[str, Any]) -> str:
    candidates = queue.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return "* No research candidates are present."
    lines = [
        "| Candidate | Priority | Type | Status | Requires Daniel | Hard gate | Next safe test |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in candidates:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"`{item['candidate_id']}` | "
            f"`{item['priority']}` | "
            f"`{item['candidate_type']}` | "
            f"`{item['status']}` | "
            f"{str(item['requires_daniel']).lower()} | "
            f"{str(item['hard_gate_required']).lower()} | "
            f"{item['next_safe_test']} |"
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
    research_candidate_queue_path = output_root / _RESEARCH_CANDIDATE_QUEUE_FILENAME
    if research_candidate_queue_path.exists():
        indexed_artifacts["research_candidate_queue"] = _artifact_metadata(
            research_candidate_queue_path
        )
    baseline_health_evaluation_path = (
        output_root / _BASELINE_HEALTH_EVALUATION_FILENAME
    )
    if baseline_health_evaluation_path.exists():
        indexed_artifacts["baseline_health_evaluation"] = _artifact_metadata(
            baseline_health_evaluation_path
        )
    baseline_evidence_metrics_path = output_root / _BASELINE_EVIDENCE_METRICS_FILENAME
    if baseline_evidence_metrics_path.exists():
        indexed_artifacts["baseline_evidence_metrics"] = _artifact_metadata(
            baseline_evidence_metrics_path
        )
    paper_observation_readiness_path = (
        output_root / _PAPER_OBSERVATION_READINESS_FILENAME
    )
    if paper_observation_readiness_path.exists():
        indexed_artifacts["paper_observation_readiness"] = _artifact_metadata(
            paper_observation_readiness_path
        )
    research_board_prioritization_path = (
        output_root / _RESEARCH_BOARD_PRIORITIZATION_FILENAME
    )
    if research_board_prioritization_path.exists():
        indexed_artifacts["research_board_prioritization"] = _artifact_metadata(
            research_board_prioritization_path
        )
    for artifact_id, filename in _BASELINE_METRIC_ARTIFACTS:
        metric_artifact_path = output_root / filename
        if metric_artifact_path.is_file():
            indexed_artifacts[artifact_id] = _artifact_metadata(metric_artifact_path)
    work_orders_dir = output_root / _WORK_ORDERS_DIRNAME
    for artifact_id, filename, _audience, _purpose in _WORK_ORDER_ARTIFACTS:
        work_order_path = work_orders_dir / filename
        if work_order_path.exists():
            indexed_artifacts[artifact_id] = _artifact_metadata(work_order_path)
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
        "research_candidate_queue_version": payload[
            "research_candidate_queue_version"
        ],
        "research_candidate_queue_path": payload["research_candidate_queue_path"],
        "research_candidate_queue": dict(payload["research_candidate_queue"]),
        "baseline_health_evaluation_version": payload[
            "baseline_health_evaluation_version"
        ],
        "baseline_health_evaluation_path": payload[
            "baseline_health_evaluation_path"
        ],
        "baseline_health_evaluation": dict(
            payload["baseline_health_evaluation"]
        ),
        "baseline_evidence_metrics_version": payload[
            "baseline_evidence_metrics_version"
        ],
        "baseline_evidence_metrics_path": payload["baseline_evidence_metrics_path"],
        "baseline_evidence_metrics": dict(payload["baseline_evidence_metrics"]),
        "paper_observation_readiness_version": payload[
            "paper_observation_readiness_version"
        ],
        "paper_observation_readiness_path": payload[
            "paper_observation_readiness_path"
        ],
        "paper_observation_readiness": dict(
            payload["paper_observation_readiness"]
        ),
        "research_board_prioritization_version": payload[
            "research_board_prioritization_version"
        ],
        "research_board_prioritization_path": payload[
            "research_board_prioritization_path"
        ],
        "research_board_prioritization": dict(
            payload["research_board_prioritization"]
        ),
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
        "next_action_selector": dict(payload["next_action_selector"]),
        "work_order_exports": dict(payload["work_order_exports"]),
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
