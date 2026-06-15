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
_STRATEGY_COMPARISON_SCAFFOLD_VERSION = (
    "assistant_v1.14_strategy_comparison_scaffold"
)
_CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_VERSION = (
    "assistant_v1.15_candidate_strategy_evidence_template"
)
_CANDIDATE_EVIDENCE_REQUIREMENTS_VERSION = (
    "assistant_v1.16_candidate_evidence_requirements"
)
_CANDIDATE_EVIDENCE_COLLECTION_PLAN_VERSION = (
    "assistant_v1.17_candidate_evidence_collection_plan"
)
_CANDIDATE_EVIDENCE_COLLECTION_STATUS_VERSION = (
    "assistant_v1.18_candidate_evidence_collection_status"
)
_CANDIDATE_EVIDENCE_GAP_SUMMARY_VERSION = (
    "assistant_v1.19_candidate_evidence_gap_summary"
)
_CANDIDATE_GAP_CLOSURE_QUEUE_VERSION = (
    "assistant_v1.20_candidate_gap_closure_queue"
)
_CANDIDATE_RISK_RULE_STATUS_VERSION = (
    "assistant_v1.23_candidate_risk_rule_status"
)
_CANDIDATE_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID = (
    "candidate_gap_closure_queue_item_003"
)
_CANDIDATE_RISK_RULE_STATUS_SOURCE_ACTION_ID = (
    "execute_candidate_gap_closure_queue_item_003"
)
_CANDIDATE_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID = (
    "volatility_or_regime_filter_candidate"
)
_CANDIDATE_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY = (
    "Volatility or regime filter candidate"
)
_CANDIDATE_RISK_RULE_STATUS_NEXT_ACTION_ID = (
    "execute_candidate_gap_closure_queue_item_004"
)
_CANDIDATE_SIGNAL_RULE_STATUS_VERSION = (
    "assistant_v1.26_candidate_signal_rule_status"
)
_CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_QUEUE_ITEM_ID = (
    "candidate_gap_closure_queue_item_006"
)
_CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_ACTION_ID = (
    "execute_candidate_gap_closure_queue_item_006"
)
_CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID = (
    "volatility_or_regime_filter_candidate"
)
_CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_CANDIDATE_FAMILY = (
    "Volatility or regime filter candidate"
)
_CANDIDATE_SIGNAL_RULE_STATUS_NEXT_ACTION_ID = (
    "execute_candidate_gap_closure_queue_item_007"
)
_SHARED_RISK_RULE_STATUS_VERSION = (
    "assistant_v1.27_shared_risk_rule_status"
)
_SHARED_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID = (
    "candidate_gap_closure_queue_item_007"
)
_SHARED_RISK_RULE_STATUS_SOURCE_ACTION_ID = (
    "execute_candidate_gap_closure_queue_item_007"
)
_SHARED_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID = "shared"
_SHARED_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY = "Shared candidate evidence"
_SHARED_RISK_RULE_STATUS_NEXT_ACTION_ID = (
    "execute_candidate_gap_closure_queue_item_008"
)
_PHASE_NAME = "Assistant v1.27 - Shared Risk Rule Status Item 007 Artifact"
_PHASE_GOAL = (
    "Materialize deterministic offline shared risk-rule status evidence for "
    "candidate_gap_closure_queue_item_007 before any strategy implementation, "
    "promotion, paper observation, broker read, paper submit, or live trading."
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
_STRATEGY_COMPARISON_SCAFFOLD_FILENAME = "strategy_comparison_scaffold.jsonl"
_CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME = (
    "candidate_strategy_evidence_template.jsonl"
)
_CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME = "candidate_evidence_requirements.jsonl"
_CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME = (
    "candidate_evidence_collection_plan.jsonl"
)
_CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME = (
    "candidate_evidence_collection_status.jsonl"
)
_CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME = "candidate_evidence_gap_summary.jsonl"
_CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME = "candidate_gap_closure_queue.jsonl"
_CANDIDATE_RISK_RULE_STATUS_FILENAME = "candidate_risk_rule_status.jsonl"
_CANDIDATE_SIGNAL_RULE_STATUS_FILENAME = "candidate_signal_rule_status.jsonl"
_SHARED_RISK_RULE_STATUS_FILENAME = "shared_risk_rule_status.jsonl"
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
    ("strategy_comparison_scaffold", _STRATEGY_COMPARISON_SCAFFOLD_FILENAME),
    (
        "candidate_strategy_evidence_template",
        _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME,
    ),
    ("candidate_evidence_requirements", _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME),
    (
        "candidate_evidence_collection_plan",
        _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME,
    ),
    (
        "candidate_evidence_collection_status",
        _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME,
    ),
    (
        "candidate_evidence_gap_summary",
        _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME,
    ),
    (
        "candidate_gap_closure_queue",
        _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME,
    ),
    (
        "candidate_risk_rule_status",
        _CANDIDATE_RISK_RULE_STATUS_FILENAME,
    ),
    (
        "candidate_signal_rule_status",
        _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME,
    ),
    (
        "shared_risk_rule_status",
        _SHARED_RISK_RULE_STATUS_FILENAME,
    ),
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
    "strategy_comparison_scaffold_path",
    "strategy_comparison_scaffold",
    "candidate_strategy_evidence_template_path",
    "candidate_strategy_evidence_template",
    "candidate_evidence_requirements_path",
    "candidate_evidence_requirements",
    "candidate_evidence_collection_plan_path",
    "candidate_evidence_collection_plan",
    "candidate_evidence_collection_status_path",
    "candidate_evidence_collection_status",
    "candidate_evidence_gap_summary_path",
    "candidate_evidence_gap_summary",
    "candidate_gap_closure_queue_path",
    "candidate_gap_closure_queue",
    "candidate_risk_rule_status_path",
    "candidate_risk_rule_status",
    "candidate_signal_rule_status_path",
    "candidate_signal_rule_status",
    "shared_risk_rule_status_path",
    "shared_risk_rule_status",
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
    "strategy_comparison_scaffold_path",
    "strategy_comparison_scaffold",
    "candidate_strategy_evidence_template_path",
    "candidate_strategy_evidence_template",
    "candidate_evidence_requirements_path",
    "candidate_evidence_requirements",
    "candidate_evidence_collection_plan_path",
    "candidate_evidence_collection_plan",
    "candidate_evidence_collection_status_path",
    "candidate_evidence_collection_status",
    "candidate_evidence_gap_summary_path",
    "candidate_evidence_gap_summary",
    "candidate_gap_closure_queue_path",
    "candidate_gap_closure_queue",
    "candidate_risk_rule_status_path",
    "candidate_risk_rule_status",
    "candidate_signal_rule_status_path",
    "candidate_signal_rule_status",
    "shared_risk_rule_status_path",
    "shared_risk_rule_status",
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
_REQUIRED_STRATEGY_COMPARISON_SCAFFOLD_FIELDS = (
    "scaffold_status",
    "comparison_mode",
    "baseline_strategy_id",
    "baseline_strategy_label",
    "baseline_strategy_role",
    "candidate_strategy_slots",
    "comparison_dimensions",
    "required_evidence_before_promotion",
    "selected_next_safe_action",
    "why_selected",
    "why_no_strategy_replacement_yet",
    "broker_state_mode",
    "safety_scope",
    "paper_submit_authorized",
    "profit_claim",
    "hard_gate_required",
    "requires_daniel",
    "daniel_action_required_now",
)
_REQUIRED_STRATEGY_COMPARISON_SLOT_FIELDS = (
    "candidate_slot_id",
    "candidate_family",
    "implementation_status",
    "evidence_status",
    "promotion_status",
    "hard_gate_required",
    "safety_scope",
)
_REQUIRED_CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FIELDS = (
    "template_status",
    "evidence_mode",
    "baseline_strategy_id",
    "baseline_strategy_role",
    "candidate_families",
    "required_evidence_sections",
    "minimum_promotion_requirements",
    "rejection_criteria",
    "comparison_against_baseline",
    "offline_artifacts_required",
    "human_readable_review_questions",
    "selected_next_safe_action",
    "why_selected",
    "why_no_strategy_implementation_yet",
    "broker_state_mode",
    "safety_scope",
    "paper_submit_authorized",
    "profit_claim",
    "hard_gate_required",
    "requires_daniel",
    "daniel_action_required_now",
)
_REQUIRED_CANDIDATE_STRATEGY_FAMILY_FIELDS = (
    "candidate_family_id",
    "candidate_family_label",
    "current_status",
    "implementation_status",
    "evidence_status",
    "promotion_status",
    "required_inputs",
    "required_metrics",
    "required_safety_checks",
    "broker_dependency",
    "hard_gate_required",
    "safety_scope",
)
_REQUIRED_CANDIDATE_EVIDENCE_REQUIREMENTS_FIELDS = (
    "requirements_status",
    "requirements_mode",
    "baseline_strategy_id",
    "baseline_strategy_role",
    "candidate_requirements",
    "shared_evidence_requirements",
    "per_candidate_missing_evidence",
    "promotion_blockers",
    "rejection_triggers",
    "next_research_artifacts_to_build",
    "selected_next_safe_action",
    "why_selected",
    "why_no_strategy_implementation_yet",
    "broker_state_mode",
    "safety_scope",
    "paper_submit_authorized",
    "profit_claim",
    "hard_gate_required",
    "requires_daniel",
    "daniel_action_required_now",
)
_REQUIRED_CANDIDATE_EVIDENCE_REQUIREMENT_FIELDS = (
    "candidate_family_id",
    "candidate_family_label",
    "current_status",
    "implementation_status",
    "evidence_status",
    "promotion_status",
    "required_data_inputs",
    "required_feature_definitions",
    "required_signal_definition",
    "required_risk_definition",
    "required_backtest_outputs",
    "required_cost_model_outputs",
    "required_benchmark_comparisons",
    "required_regime_analysis",
    "required_turnover_analysis",
    "required_drawdown_analysis",
    "required_failure_mode_review",
    "required_safety_checks",
    "missing_evidence",
    "promotion_blockers",
    "rejection_triggers",
    "broker_dependency",
    "hard_gate_required",
    "safety_scope",
)
_REQUIRED_CANDIDATE_EVIDENCE_COLLECTION_PLAN_FIELDS = (
    "collection_plan_status",
    "collection_plan_mode",
    "baseline_strategy_id",
    "baseline_strategy_role",
    "candidate_collection_plans",
    "shared_collection_steps",
    "data_collection_requirements",
    "metric_collection_requirements",
    "safety_collection_requirements",
    "expected_offline_artifacts",
    "blocked_until_collected",
    "selected_next_safe_action",
    "why_selected",
    "why_no_strategy_implementation_yet",
    "broker_state_mode",
    "safety_scope",
    "paper_submit_authorized",
    "profit_claim",
    "hard_gate_required",
    "requires_daniel",
    "daniel_action_required_now",
)
_REQUIRED_CANDIDATE_EVIDENCE_COLLECTION_PLAN_ENTRY_FIELDS = (
    "candidate_family_id",
    "candidate_family_label",
    "current_status",
    "implementation_status",
    "evidence_status",
    "collection_status",
    "promotion_status",
    "collection_steps",
    "data_inputs_to_collect",
    "features_to_define",
    "signal_rules_to_specify",
    "risk_rules_to_specify",
    "backtest_outputs_to_collect",
    "cost_outputs_to_collect",
    "benchmark_outputs_to_collect",
    "regime_outputs_to_collect",
    "turnover_outputs_to_collect",
    "drawdown_outputs_to_collect",
    "failure_modes_to_review",
    "safety_checks_to_run",
    "expected_artifacts",
    "blocked_until_collected",
    "broker_dependency",
    "hard_gate_required",
    "safety_scope",
)
_REQUIRED_CANDIDATE_EVIDENCE_COLLECTION_STATUS_FIELDS = (
    "collection_status",
    "collection_status_mode",
    "baseline_strategy_id",
    "baseline_strategy_role",
    "candidate_statuses",
    "shared_collection_status",
    "evidence_status_counts",
    "not_started_evidence",
    "blocked_evidence",
    "ready_to_collect_evidence",
    "missing_evidence",
    "promotion_blockers",
    "next_collection_actions",
    "selected_next_safe_action",
    "why_selected",
    "why_no_strategy_implementation_yet",
    "broker_state_mode",
    "safety_scope",
    "paper_submit_authorized",
    "profit_claim",
    "hard_gate_required",
    "requires_daniel",
    "daniel_action_required_now",
)
_REQUIRED_CANDIDATE_EVIDENCE_COLLECTION_STATUS_ENTRY_FIELDS = (
    "candidate_family_id",
    "candidate_family_label",
    "current_status",
    "implementation_status",
    "evidence_status",
    "collection_status",
    "promotion_status",
    "evidence_items",
    "not_started_items",
    "blocked_items",
    "ready_to_collect_items",
    "missing_items",
    "promotion_blockers",
    "next_collection_actions",
    "broker_dependency",
    "hard_gate_required",
    "safety_scope",
)
_REQUIRED_CANDIDATE_EVIDENCE_GAP_SUMMARY_FIELDS = (
    "gap_summary_status",
    "gap_summary_mode",
    "baseline_strategy_id",
    "baseline_strategy_role",
    "candidate_gap_summaries",
    "ranked_gap_groups",
    "highest_priority_gaps",
    "shared_gap_summary",
    "gap_counts",
    "next_gap_closure_actions",
    "next_research_artifacts_to_build",
    "selected_next_safe_action",
    "why_selected",
    "why_no_strategy_implementation_yet",
    "broker_state_mode",
    "safety_scope",
    "paper_submit_authorized",
    "profit_claim",
    "hard_gate_required",
    "requires_daniel",
    "daniel_action_required_now",
)
_REQUIRED_CANDIDATE_EVIDENCE_GAP_SUMMARY_ENTRY_FIELDS = (
    "candidate_family_id",
    "candidate_family_label",
    "current_status",
    "implementation_status",
    "evidence_status",
    "collection_status",
    "promotion_status",
    "total_gap_count",
    "highest_priority_gap",
    "evidence_gaps",
    "blocked_gaps",
    "missing_gaps",
    "not_started_gaps",
    "ready_to_collect_gaps",
    "promotion_blockers",
    "next_gap_closure_actions",
    "broker_dependency",
    "hard_gate_required",
    "safety_scope",
)
_REQUIRED_CANDIDATE_EVIDENCE_GAP_FIELDS = (
    "gap_id",
    "gap_label",
    "gap_category",
    "priority",
    "status",
    "why_it_matters",
    "required_before_implementation",
    "required_before_promotion",
    "closure_artifact",
    "offline_only",
    "broker_dependency",
)
_REQUIRED_CANDIDATE_EVIDENCE_GAP_GROUP_FIELDS = (
    "group_id",
    "group_label",
    "priority",
    "gap_count",
    "why_ranked_here",
    "next_gap_closure_action",
)
_REQUIRED_CANDIDATE_GAP_CLOSURE_QUEUE_FIELDS = (
    "candidate_gap_closure_queue_version",
    "queue_status",
    "queue_mode",
    "artifact_path",
    "source_gap_summary_path",
    "source_gap_summary_status",
    "baseline_strategy_id",
    "baseline_strategy_role",
    "queue_item_count",
    "queue_items",
    "selected_queue_item_id",
    "selected_next_safe_action",
    "selected_next_safe_action_type",
    "selected_work_order",
    "selected_owner",
    "selection_policy",
    "generation_inputs",
    "next_research_artifacts_to_build",
    "allowed_scope",
    "forbidden_scope",
    "acceptance_criteria",
    "why_selected",
    "why_no_strategy_implementation_yet",
    "broker_state_mode",
    "broker_state_observed",
    "paper_submit_authorized",
    "daniel_action_required_now",
    "profit_claim",
    "safety_scope",
    "safety_labels",
)
_REQUIRED_CANDIDATE_GAP_CLOSURE_QUEUE_ITEM_FIELDS = (
    "queue_item_id",
    "action_id",
    "rank",
    "priority",
    "action_priority",
    "candidate_family",
    "candidate_family_id",
    "gap_group_id",
    "gap_group_label",
    "gap_id",
    "gap_label",
    "gap_status",
    "closure_action",
    "closure_objective",
    "expected_evidence_artifact",
    "recommended_agent",
    "allowed_scope",
    "forbidden_scope",
    "acceptance_criteria",
    "blocked_by",
    "daniel_action_required",
    "broker_state_mode",
    "broker_state_observed",
    "paper_submit_authorized",
    "profit_claim",
    "safety_scope",
    "safety_labels",
)
_REQUIRED_CANDIDATE_RISK_RULE_STATUS_FIELDS = (
    "risk_rule_status_version",
    "risk_rule_status",
    "risk_rule_status_mode",
    "baseline_strategy_id",
    "source_queue_item_id",
    "source_action_id",
    "source_gap_id",
    "source_candidate_family_id",
    "source_candidate_family",
    "source_gap_status",
    "source_gap_group_id",
    "source_gap_group_label",
    "source_closure_action",
    "source_closure_objective",
    "source_expected_evidence_artifact",
    "candidate_family_count",
    "candidate_scope_count",
    "shared_scope_count",
    "candidate_risk_rule_summaries",
    "target_candidate_risk_rule_summary",
    "shared_risk_rule_gaps",
    "highest_priority_risk_rule_gaps",
    "evidence_status_summary",
    "risk_rule_acceptance_criteria",
    "next_risk_rule_closure_actions",
    "selected_next_safe_action",
    "broker_state_mode",
    "paper_submit_authorized",
    "daniel_action_required_now",
    "profit_claim",
    "safety_scope",
    "safety_labels",
)
_REQUIRED_CANDIDATE_RISK_RULE_SUMMARY_FIELDS = (
    "candidate_family",
    "candidate_family_id",
    "candidate_family_label",
    "risk_rule_status",
    "risk_rule_evidence_status",
    "risk_rule_defined",
    "position_sizing_defined",
    "max_loss_or_drawdown_rule_defined",
    "entry_exit_risk_boundary_defined",
    "stop_or_deactivation_rule_defined",
    "data_quality_risk_rule_defined",
    "promotion_blockers",
    "missing_risk_rule_evidence",
    "evidence_status_breakdown",
    "recommended_closure_action",
    "expected_evidence_artifact",
)
_REQUIRED_CANDIDATE_SIGNAL_RULE_STATUS_FIELDS = (
    "signal_rule_status_version",
    "signal_rule_status",
    "signal_rule_status_mode",
    "baseline_strategy_id",
    "source_queue_item_id",
    "source_action_id",
    "source_gap_id",
    "source_candidate_family_id",
    "source_candidate_family",
    "source_gap_status",
    "source_gap_group_id",
    "source_gap_group_label",
    "source_closure_action",
    "source_closure_objective",
    "source_expected_evidence_artifact",
    "candidate_family_count",
    "candidate_scope_count",
    "shared_scope_count",
    "candidate_signal_rule_summaries",
    "target_candidate_signal_rule_summary",
    "target_explicit_signal_rule_evidence",
    "target_regime_or_volatility_condition_evidence",
    "target_materialized_candidate_signal_specification",
    "target_remaining_missing_signal_rule_evidence",
    "target_candidate_signal_readiness",
    "shared_signal_rule_gaps",
    "highest_priority_signal_rule_gaps",
    "evidence_status_summary",
    "signal_rule_acceptance_criteria",
    "next_signal_rule_closure_actions",
    "selected_next_safe_action",
    "broker_state_mode",
    "paper_submit_authorized",
    "daniel_action_required_now",
    "profit_claim",
    "safety_scope",
    "safety_labels",
)
_REQUIRED_CANDIDATE_SIGNAL_RULE_SUMMARY_FIELDS = (
    "candidate_family",
    "candidate_family_id",
    "candidate_label",
    "signal_rule_status",
    "signal_rule_evidence_status",
    "signal_rule_defined",
    "signal_inputs_defined",
    "indicator_or_feature_definition_defined",
    "entry_rule_defined",
    "exit_rule_defined",
    "lookback_or_parameter_bounds_defined",
    "data_basis_defined",
    "universe_defined",
    "rebalance_or_evaluation_schedule_defined",
    "leakage_or_lookahead_guard_defined",
    "explicit_signal_rule_evidence",
    "materialized_candidate_signal_specification",
    "remaining_missing_signal_rule_evidence",
    "candidate_signal_readiness",
    "missing_signal_rule_evidence",
    "promotion_blockers",
    "evidence_status_breakdown",
    "recommended_closure_action",
    "expected_evidence_artifact",
)
_REQUIRED_SHARED_RISK_RULE_STATUS_FIELDS = (
    "shared_risk_rule_status_version",
    "shared_risk_rule_status",
    "shared_risk_rule_status_mode",
    "deterministic_scope",
    "baseline_strategy_id",
    "source_queue_item_id",
    "source_action_id",
    "source_gap_id",
    "source_candidate_family_id",
    "source_candidate_family",
    "source_gap_status",
    "source_gap_group_id",
    "source_gap_group_label",
    "source_closure_action",
    "source_closure_objective",
    "source_expected_evidence_artifact",
    "candidate_family_count",
    "shared_scope_count",
    "shared_risk_rule_status_item",
    "shared_risk_rule_gaps",
    "candidate_risk_rule_summaries",
    "explicit_shared_risk_rule_evidence",
    "position_sizing_evidence",
    "stop_or_exit_evidence",
    "drawdown_or_exposure_control_evidence",
    "portfolio_or_risk_cap_evidence",
    "materialized_shared_risk_specification",
    "remaining_missing_shared_risk_evidence",
    "target_shared_risk_readiness",
    "target_shared_risk_status",
    "highest_priority_remaining_gaps",
    "evidence_status_summary",
    "shared_risk_rule_acceptance_criteria",
    "next_shared_risk_rule_closure_actions",
    "selected_next_safe_action",
    "broker_state_mode",
    "paper_submit_authorized",
    "daniel_action_required_now",
    "profit_claim",
    "safety_scope",
    "safety_labels",
)
_CANDIDATE_EVIDENCE_GAP_PRIORITIES = ("high", "medium", "low")
_REQUIRED_CANDIDATE_EVIDENCE_ITEM_FIELDS = (
    "evidence_item_id",
    "evidence_item_label",
    "evidence_category",
    "status",
    "blocker",
    "required_before_implementation",
    "required_before_promotion",
    "offline_only",
    "broker_dependency",
)
_CANDIDATE_EVIDENCE_ITEM_STATUSES = (
    "not_started",
    "blocked",
    "ready_to_collect",
    "missing",
)
_REQUIRED_CANDIDATE_EVIDENCE_SECTIONS = (
    "hypothesis",
    "market_universe",
    "data_requirements",
    "feature_requirements",
    "signal_definition",
    "risk_definition",
    "backtest_requirements",
    "cost_model_requirements",
    "benchmark_requirements",
    "regime_analysis_requirements",
    "turnover_requirements",
    "drawdown_requirements",
    "failure_modes",
    "paper_observation_requirements",
    "promotion_gate",
    "rejection_gate",
)
_REQUIRED_CANDIDATE_FAMILY_IDS = (
    "momentum_or_trend_candidate",
    "mean_reversion_candidate",
    "volatility_or_regime_filter_candidate",
)
_REQUIRED_STRATEGY_COMPARISON_DIMENSIONS = (
    "data_basis",
    "lookback_window",
    "signal_frequency",
    "trade_frequency",
    "turnover",
    "transaction_cost_assumption",
    "drawdown_profile",
    "benchmark_relative_return",
    "regime_sensitivity",
    "paper_observation_readiness",
    "broker_dependency",
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
    _apply_strategy_comparison_scaffold(payload, output_root)
    _apply_candidate_strategy_evidence_template(payload, output_root)
    _apply_candidate_evidence_requirements(payload, output_root)
    _apply_candidate_evidence_collection_plan(payload, output_root)
    _apply_candidate_evidence_collection_status(payload, output_root)
    _apply_candidate_evidence_gap_summary(payload, output_root)
    _apply_candidate_gap_closure_queue(payload, output_root)
    _apply_candidate_risk_rule_status(payload, output_root)
    _apply_candidate_signal_rule_status(payload, output_root)
    _apply_shared_risk_rule_status(payload, output_root)
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
    _write_strategy_comparison_scaffold_artifact(output_root, payload)
    _write_candidate_strategy_evidence_template_artifact(output_root, payload)
    _write_candidate_evidence_requirements_artifact(output_root, payload)
    _write_candidate_evidence_collection_plan_artifact(output_root, payload)
    _write_candidate_evidence_collection_status_artifact(output_root, payload)
    _write_candidate_evidence_gap_summary_artifact(output_root, payload)
    _write_candidate_gap_closure_queue_artifact(output_root, payload)
    _write_candidate_risk_rule_status_artifact(output_root, payload)
    _write_candidate_signal_rule_status_artifact(output_root, payload)
    _write_shared_risk_rule_status_artifact(output_root, payload)
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


def _apply_strategy_comparison_scaffold(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    scaffold = _build_strategy_comparison_scaffold(payload, artifact_paths)
    payload["strategy_comparison_scaffold_path"] = str(
        artifact_paths["strategy_comparison_scaffold"]
    )
    payload["strategy_comparison_scaffold"] = scaffold
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["strategy_comparison_scaffold_path"] = payload[
            "strategy_comparison_scaffold_path"
        ]
        dashboard["strategy_comparison_scaffold"] = dict(scaffold)


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


def _write_strategy_comparison_scaffold_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    scaffold = payload.get("strategy_comparison_scaffold")
    record = scaffold if isinstance(scaffold, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _STRATEGY_COMPARISON_SCAFFOLD_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_candidate_strategy_evidence_template_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    template = payload.get("candidate_strategy_evidence_template")
    record = template if isinstance(template, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_candidate_evidence_requirements_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    requirements = payload.get("candidate_evidence_requirements")
    record = requirements if isinstance(requirements, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_candidate_evidence_collection_plan_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    collection_plan = payload.get("candidate_evidence_collection_plan")
    record = collection_plan if isinstance(collection_plan, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_candidate_evidence_collection_status_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    collection_status = payload.get("candidate_evidence_collection_status")
    record = collection_status if isinstance(collection_status, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_candidate_evidence_gap_summary_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    gap_summary = payload.get("candidate_evidence_gap_summary")
    record = gap_summary if isinstance(gap_summary, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_candidate_gap_closure_queue_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    queue = payload.get("candidate_gap_closure_queue")
    record = queue if isinstance(queue, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_candidate_risk_rule_status_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    status = payload.get("candidate_risk_rule_status")
    record = status if isinstance(status, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _CANDIDATE_RISK_RULE_STATUS_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _write_shared_risk_rule_status_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    status = payload.get("shared_risk_rule_status")
    record = status if isinstance(status, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _SHARED_RISK_RULE_STATUS_FILENAME).write_text(
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
    strategy_comparison_scaffold_defaults = (
        _default_strategy_comparison_scaffold_fields(artifact_paths)
    )
    candidate_strategy_evidence_template_defaults = (
        _default_candidate_strategy_evidence_template_fields(artifact_paths)
    )
    candidate_evidence_requirements_defaults = (
        _default_candidate_evidence_requirements_fields(artifact_paths)
    )
    candidate_evidence_collection_plan_defaults = (
        _default_candidate_evidence_collection_plan_fields(artifact_paths)
    )
    candidate_evidence_collection_status_defaults = (
        _default_candidate_evidence_collection_status_fields(artifact_paths)
    )
    candidate_evidence_gap_summary_defaults = (
        _default_candidate_evidence_gap_summary_fields(artifact_paths)
    )
    candidate_gap_closure_queue_defaults = (
        _default_candidate_gap_closure_queue_fields(artifact_paths)
    )
    candidate_risk_rule_status_defaults = (
        _default_candidate_risk_rule_status_fields(artifact_paths)
    )
    candidate_signal_rule_status_defaults = (
        _default_candidate_signal_rule_status_fields(artifact_paths)
    )
    shared_risk_rule_status_defaults = (
        _default_shared_risk_rule_status_fields(artifact_paths)
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
        **strategy_comparison_scaffold_defaults,
        **candidate_strategy_evidence_template_defaults,
        **candidate_evidence_requirements_defaults,
        **candidate_evidence_collection_plan_defaults,
        **candidate_evidence_collection_status_defaults,
        **candidate_evidence_gap_summary_defaults,
        **candidate_gap_closure_queue_defaults,
        **candidate_risk_rule_status_defaults,
        **candidate_signal_rule_status_defaults,
        **shared_risk_rule_status_defaults,
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
            "strategy_comparison_scaffold": artifact_paths[
                "strategy_comparison_scaffold"
            ],
            "candidate_strategy_evidence_template": artifact_paths[
                "candidate_strategy_evidence_template"
            ],
            "candidate_evidence_requirements": artifact_paths[
                "candidate_evidence_requirements"
            ],
            "candidate_evidence_collection_plan": artifact_paths[
                "candidate_evidence_collection_plan"
            ],
            "candidate_evidence_collection_status": artifact_paths[
                "candidate_evidence_collection_status"
            ],
            "candidate_evidence_gap_summary": artifact_paths[
                "candidate_evidence_gap_summary"
            ],
            "candidate_gap_closure_queue": artifact_paths[
                "candidate_gap_closure_queue"
            ],
            "candidate_risk_rule_status": artifact_paths[
                "candidate_risk_rule_status"
            ],
            "candidate_signal_rule_status": artifact_paths[
                "candidate_signal_rule_status"
            ],
            "shared_risk_rule_status": artifact_paths[
                "shared_risk_rule_status"
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
            "strategy_comparison_scaffold_path": (
                strategy_comparison_scaffold_defaults[
                    "strategy_comparison_scaffold_path"
                ]
            ),
            "strategy_comparison_scaffold": dict(
                strategy_comparison_scaffold_defaults[
                    "strategy_comparison_scaffold"
                ]
            ),
            "candidate_evidence_collection_status_path": (
                candidate_evidence_collection_status_defaults[
                    "candidate_evidence_collection_status_path"
                ]
            ),
            "candidate_evidence_collection_status": dict(
                candidate_evidence_collection_status_defaults[
                    "candidate_evidence_collection_status"
                ]
            ),
            "candidate_evidence_gap_summary_path": (
                candidate_evidence_gap_summary_defaults[
                    "candidate_evidence_gap_summary_path"
                ]
            ),
            "candidate_evidence_gap_summary": dict(
                candidate_evidence_gap_summary_defaults[
                    "candidate_evidence_gap_summary"
                ]
            ),
            "candidate_gap_closure_queue_path": (
                candidate_gap_closure_queue_defaults[
                    "candidate_gap_closure_queue_path"
                ]
            ),
            "candidate_gap_closure_queue": dict(
                candidate_gap_closure_queue_defaults[
                    "candidate_gap_closure_queue"
                ]
            ),
            "candidate_risk_rule_status_path": (
                candidate_risk_rule_status_defaults[
                    "candidate_risk_rule_status_path"
                ]
            ),
            "candidate_risk_rule_status": dict(
                candidate_risk_rule_status_defaults[
                    "candidate_risk_rule_status"
                ]
            ),
            "candidate_signal_rule_status_path": (
                candidate_signal_rule_status_defaults[
                    "candidate_signal_rule_status_path"
                ]
            ),
            "candidate_signal_rule_status": dict(
                candidate_signal_rule_status_defaults[
                    "candidate_signal_rule_status"
                ]
            ),
            "shared_risk_rule_status_path": (
                shared_risk_rule_status_defaults[
                    "shared_risk_rule_status_path"
                ]
            ),
            "shared_risk_rule_status": dict(
                shared_risk_rule_status_defaults[
                    "shared_risk_rule_status"
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
        "strategy_comparison_scaffold": _normalize_path(
            output_root / _STRATEGY_COMPARISON_SCAFFOLD_FILENAME
        ),
        "candidate_strategy_evidence_template": _normalize_path(
            output_root / _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME
        ),
        "candidate_evidence_requirements": _normalize_path(
            output_root / _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME
        ),
        "candidate_evidence_collection_plan": _normalize_path(
            output_root / _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME
        ),
        "candidate_evidence_collection_status": _normalize_path(
            output_root / _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME
        ),
        "candidate_evidence_gap_summary": _normalize_path(
            output_root / _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME
        ),
        "candidate_gap_closure_queue": _normalize_path(
            output_root / _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME
        ),
        "candidate_risk_rule_status": _normalize_path(
            output_root / _CANDIDATE_RISK_RULE_STATUS_FILENAME
        ),
        "candidate_signal_rule_status": _normalize_path(
            output_root / _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME
        ),
        "shared_risk_rule_status": _normalize_path(
            output_root / _SHARED_RISK_RULE_STATUS_FILENAME
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


def _build_strategy_comparison_scaffold(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    del payload, artifact_paths
    candidate_slots = [
        {
            "candidate_slot_id": "momentum_or_trend_candidate",
            "candidate_family": "momentum_or_trend",
            "implementation_status": "placeholder_not_implemented",
            "evidence_status": "offline_evidence_not_yet_collected",
            "promotion_status": "not_promotable_until_offline_evidence_comparison",
            "hard_gate_required": False,
            "safety_scope": "offline_only",
        },
        {
            "candidate_slot_id": "mean_reversion_candidate",
            "candidate_family": "mean_reversion",
            "implementation_status": "placeholder_not_implemented",
            "evidence_status": "offline_evidence_not_yet_collected",
            "promotion_status": "not_promotable_until_offline_evidence_comparison",
            "hard_gate_required": False,
            "safety_scope": "offline_only",
        },
        {
            "candidate_slot_id": "volatility_or_regime_filter_candidate",
            "candidate_family": "volatility_or_regime_filter",
            "implementation_status": "placeholder_not_implemented",
            "evidence_status": "offline_evidence_not_yet_collected",
            "promotion_status": "not_promotable_until_offline_evidence_comparison",
            "hard_gate_required": False,
            "safety_scope": "offline_only",
        },
    ]
    return {
        "scaffold_status": "ready",
        "comparison_mode": "offline_research_scaffold_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_label": "SPY SMA 50/200 daily long-only baseline",
        "baseline_strategy_role": "control_harness",
        "candidate_strategy_slots": candidate_slots,
        "comparison_dimensions": list(_REQUIRED_STRATEGY_COMPARISON_DIMENSIONS),
        "required_evidence_before_promotion": [
            "deterministic_offline_data_basis",
            "fixed_lookback_window_definition",
            "signal_and_trade_frequency_summary",
            "turnover_and_transaction_cost_assumption",
            "drawdown_profile_summary",
            "benchmark_relative_return_summary",
            "regime_sensitivity_summary",
            "paper_observation_readiness_status_without_broker_claims",
            "broker_dependency_absent_or_hard_gated",
        ],
        "selected_next_safe_action": "build_candidate_strategy_evidence_template",
        "why_selected": (
            "The scaffold is offline-only and prepares candidate evidence before "
            "any future strategy implementation or promotion decision."
        ),
        "why_no_strategy_replacement_yet": (
            "No replacement is considered yet; replacing the control harness "
            "requires deterministic offline evidence comparison first."
        ),
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "hard_gate_required": False,
        "requires_daniel": False,
        "daniel_action_required_now": False,
    }


def _default_strategy_comparison_scaffold_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    scaffold = _build_strategy_comparison_scaffold({}, artifact_paths)
    return {
        "strategy_comparison_scaffold_path": str(
            artifact_paths["strategy_comparison_scaffold"]
        ),
        "strategy_comparison_scaffold": scaffold,
    }


def _strategy_comparison_scaffold_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    scaffold = payload.get("strategy_comparison_scaffold")
    if isinstance(scaffold, Mapping):
        return dict(scaffold)
    return _build_strategy_comparison_scaffold(payload, artifact_paths)


def _build_candidate_strategy_evidence_template(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    del payload, artifact_paths
    candidate_families = [
        {
            "candidate_family_id": "momentum_or_trend_candidate",
            "candidate_family_label": "Momentum or trend candidate",
            "current_status": "evidence_template_ready_not_implemented",
            "implementation_status": "not_implemented",
            "evidence_status": "offline_evidence_requirements_defined",
            "promotion_status": "not_promotable_without_deterministic_evidence",
            "required_inputs": [
                "deterministic_adjusted_daily_bars",
                "as_of_date_filter",
                "fixed_universe_definition",
                "candidate_signal_parameters",
            ],
            "required_metrics": [
                "benchmark_relative_return",
                "maximum_drawdown",
                "turnover",
                "transaction_cost_sensitivity",
                "regime_sensitivity",
            ],
            "required_safety_checks": [
                "offline_default_pytest_only",
                "dependency_direction_guard_passes",
                "no_broker_network_or_llm_imports",
                "paper_observation_deferred_until_explicit_gate",
            ],
            "broker_dependency": "none",
            "hard_gate_required": False,
            "safety_scope": "offline_only",
        },
        {
            "candidate_family_id": "mean_reversion_candidate",
            "candidate_family_label": "Mean reversion candidate",
            "current_status": "evidence_template_ready_not_implemented",
            "implementation_status": "not_implemented",
            "evidence_status": "offline_evidence_requirements_defined",
            "promotion_status": "not_promotable_without_deterministic_evidence",
            "required_inputs": [
                "deterministic_adjusted_daily_bars",
                "as_of_date_filter",
                "fixed_universe_definition",
                "candidate_signal_parameters",
            ],
            "required_metrics": [
                "benchmark_relative_return",
                "maximum_drawdown",
                "turnover",
                "transaction_cost_sensitivity",
                "regime_sensitivity",
            ],
            "required_safety_checks": [
                "offline_default_pytest_only",
                "dependency_direction_guard_passes",
                "no_broker_network_or_llm_imports",
                "paper_observation_deferred_until_explicit_gate",
            ],
            "broker_dependency": "none",
            "hard_gate_required": False,
            "safety_scope": "offline_only",
        },
        {
            "candidate_family_id": "volatility_or_regime_filter_candidate",
            "candidate_family_label": "Volatility or regime filter candidate",
            "current_status": "evidence_template_ready_not_implemented",
            "implementation_status": "not_implemented",
            "evidence_status": "offline_evidence_requirements_defined",
            "promotion_status": "not_promotable_without_deterministic_evidence",
            "required_inputs": [
                "deterministic_adjusted_daily_bars",
                "as_of_date_filter",
                "fixed_universe_definition",
                "candidate_signal_parameters",
            ],
            "required_metrics": [
                "benchmark_relative_return",
                "maximum_drawdown",
                "turnover",
                "transaction_cost_sensitivity",
                "regime_sensitivity",
            ],
            "required_safety_checks": [
                "offline_default_pytest_only",
                "dependency_direction_guard_passes",
                "no_broker_network_or_llm_imports",
                "paper_observation_deferred_until_explicit_gate",
            ],
            "broker_dependency": "none",
            "hard_gate_required": False,
            "safety_scope": "offline_only",
        },
    ]
    return {
        "template_status": "ready",
        "evidence_mode": "offline_strategy_evidence_template_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "candidate_families": candidate_families,
        "required_evidence_sections": list(_REQUIRED_CANDIDATE_EVIDENCE_SECTIONS),
        "minimum_promotion_requirements": [
            "offline deterministic implementation exists",
            "tests pass",
            "dependency-direction guard passes",
            "no broker/network/LLM imports in strategy path",
            "benchmark comparison exists",
            "transaction cost assumption exists",
            "drawdown evidence exists",
            "turnover evidence exists",
            "regime sensitivity evidence exists",
            (
                "paper observation remains deferred until Daniel explicitly "
                "scopes broker read/paper gate"
            ),
        ],
        "rejection_criteria": [
            "insufficient data",
            "non-deterministic signal",
            "broker dependency in research path",
            "network dependency in default pytest path",
            "fragile performance concentrated in one period",
            "excessive turnover under cost assumptions",
            "drawdown profile unacceptable versus baseline",
            "missing benchmark comparison",
            "missing regime evidence",
            "unclear promotion gate",
        ],
        "comparison_against_baseline": {
            "baseline_strategy_id": "spy_sma_50_200_control",
            "baseline_strategy_role": "control_harness",
            "comparison_mode": "deterministic_offline_before_candidate_promotion",
            "comparison_requirement": (
                "Every candidate must be compared against the SPY SMA 50/200 "
                "control harness before implementation can be treated as useful."
            ),
        },
        "offline_artifacts_required": [
            "candidate_strategy_evidence_template.jsonl",
            "future_candidate_signal_definition.jsonl",
            "future_candidate_backtest_requirements.jsonl",
            "future_candidate_baseline_comparison.jsonl",
            "future_candidate_safety_review.jsonl",
        ],
        "human_readable_review_questions": [
            "What hypothesis is this candidate testing?",
            "What market universe and data basis does it require?",
            "How is the signal deterministic as of the evaluation date?",
            "How does it compare with the SPY SMA 50/200 control harness?",
            "What turnover, cost, drawdown, and regime risks could reject it?",
            "Which evidence must exist before any paper observation is scoped?",
        ],
        "selected_next_safe_action": "materialize_candidate_evidence_requirements",
        "why_selected": (
            "The next useful step is still offline-only: materialize candidate "
            "evidence requirements before any candidate implementation."
        ),
        "why_no_strategy_implementation_yet": (
            "Candidate implementation requires an offline evidence template and "
            "deterministic comparison requirements first."
        ),
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "hard_gate_required": False,
        "requires_daniel": False,
        "daniel_action_required_now": False,
    }


def _default_candidate_strategy_evidence_template_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    template = _build_candidate_strategy_evidence_template({}, artifact_paths)
    return {
        "candidate_strategy_evidence_template_path": str(
            artifact_paths["candidate_strategy_evidence_template"]
        ),
        "candidate_strategy_evidence_template": template,
    }


def _candidate_strategy_evidence_template_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    template = payload.get("candidate_strategy_evidence_template")
    if isinstance(template, Mapping):
        return dict(template)
    return _build_candidate_strategy_evidence_template(payload, artifact_paths)


def _apply_candidate_strategy_evidence_template(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    template = _build_candidate_strategy_evidence_template(payload, artifact_paths)
    payload["candidate_strategy_evidence_template_path"] = str(
        artifact_paths["candidate_strategy_evidence_template"]
    )
    payload["candidate_strategy_evidence_template"] = template
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["candidate_strategy_evidence_template_path"] = payload[
            "candidate_strategy_evidence_template_path"
        ]
        dashboard["candidate_strategy_evidence_template"] = dict(template)


def _build_candidate_evidence_requirements(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    del payload, artifact_paths
    promotion_blockers = [
        "candidate_strategy_not_implemented",
        "offline_backtest_not_materialized",
        "benchmark_comparison_missing",
        "cost_model_evidence_missing",
        "drawdown_evidence_missing",
        "regime_evidence_missing",
        "turnover_evidence_missing",
        "paper_observation_not_authorized",
    ]
    rejection_triggers = [
        "non_deterministic_signal",
        "broker_dependency_in_research_path",
        "network_dependency_in_default_pytest",
        "excessive_turnover_after_costs",
        "unacceptable_drawdown_vs_baseline",
        "fragile_single_period_performance",
        "missing_benchmark_comparison",
        "missing_regime_analysis",
    ]
    missing_evidence = [
        "deterministic_offline_data_source_not_selected",
        "explicit_data_basis_not_documented",
        "feature_calculation_definition_missing",
        "signal_rule_definition_missing",
        "risk_rule_definition_missing",
        "offline_backtest_outputs_missing",
        "transaction_cost_assumption_missing",
        "benchmark_comparison_against_spy_sma_50_200_control_missing",
        "turnover_estimate_missing",
        "drawdown_evidence_missing",
        "regime_sensitivity_evidence_missing",
        "failure_mode_review_missing",
    ]
    candidate_requirements = [
        _candidate_evidence_requirement(
            candidate_family_id="momentum_or_trend_candidate",
            candidate_family_label="Momentum or trend candidate",
            required_feature_definitions=[
                "trend_or_momentum_feature_calculated_from_as_of_bars_only",
                "lookback_window_and_parameter_values_fixed_before_test",
                "ranking_or_filter_basis_defined_without_optimizer_dependency",
            ],
            required_signal_definition=[
                "deterministic_long_flat_or_ranked_entry_rule",
                "deterministic_exit_or_deallocation_rule",
                "as_of_date_signal_timing_and_no_lookahead_rule",
            ],
            required_risk_definition=[
                "max_position_notional_or_weight",
                "position_concentration_limit",
                "risk_off_or_stop_condition_defined_before_backtest",
            ],
            required_regime_analysis=[
                "trend_regime_performance_split",
                "range_bound_regime_performance_split",
                "high_volatility_regime_performance_split",
            ],
            promotion_blockers=promotion_blockers,
            rejection_triggers=rejection_triggers,
            missing_evidence=missing_evidence,
        ),
        _candidate_evidence_requirement(
            candidate_family_id="mean_reversion_candidate",
            candidate_family_label="Mean reversion candidate",
            required_feature_definitions=[
                "deviation_from_reference_price_feature",
                "reversion_horizon_definition",
                "entry_and_exit_thresholds_fixed_before_test",
            ],
            required_signal_definition=[
                "deterministic_oversold_or_overextended_entry_rule",
                "deterministic_mean_reversion_exit_rule",
                "as_of_date_signal_timing_and_no_lookahead_rule",
            ],
            required_risk_definition=[
                "max_position_notional_or_weight",
                "adverse_trend_or_failed_reversion_exit_rule",
                "trade_cooldown_or_frequency_limit_if_applicable",
            ],
            required_regime_analysis=[
                "trend_regime_failure_review",
                "range_bound_regime_performance_split",
                "high_volatility_regime_performance_split",
            ],
            promotion_blockers=promotion_blockers,
            rejection_triggers=rejection_triggers,
            missing_evidence=missing_evidence,
        ),
        _candidate_evidence_requirement(
            candidate_family_id="volatility_or_regime_filter_candidate",
            candidate_family_label="Volatility or regime filter candidate",
            required_feature_definitions=[
                "volatility_or_regime_state_feature",
                "filter_thresholds_fixed_before_test",
                "interaction_with_baseline_or_candidate_signal_defined",
            ],
            required_signal_definition=[
                "deterministic_risk_on_or_risk_off_filter_rule",
                "deterministic_filter_update_frequency",
                "as_of_date_signal_timing_and_no_lookahead_rule",
            ],
            required_risk_definition=[
                "risk_reduction_or_exposure_cap_rule",
                "filter_override_limits",
                "behavior_when_regime_state_is_ambiguous_or_missing",
            ],
            required_regime_analysis=[
                "low_volatility_regime_performance_split",
                "high_volatility_regime_performance_split",
                "regime_transition_period_review",
            ],
            promotion_blockers=promotion_blockers,
            rejection_triggers=rejection_triggers,
            missing_evidence=missing_evidence,
        ),
    ]
    per_candidate_missing_evidence = {
        str(candidate["candidate_family_id"]): list(candidate["missing_evidence"])
        for candidate in candidate_requirements
    }
    return {
        "requirements_status": "ready",
        "requirements_mode": "offline_candidate_evidence_requirements_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "candidate_requirements": candidate_requirements,
        "shared_evidence_requirements": [
            "deterministic_offline_data_source",
            "explicit_data_basis",
            "feature_calculation_definition",
            "signal_rule_definition",
            "risk_rule_definition",
            "benchmark_comparison_against_spy_sma_50_200_control",
            "transaction_cost_assumption",
            "turnover_estimate",
            "drawdown_evidence",
            "regime_sensitivity_evidence",
            "dependency_direction_guard",
            "default_pytest_network_guard",
            "broker_mutation_invariant",
            "no_broker_dependency_in_research_path",
            "no_llm_or_agent_dependency_in_strategy_path",
            (
                "paper_observation_deferred_until_daniel_explicitly_scopes_"
                "broker_read_or_paper_gate"
            ),
        ],
        "per_candidate_missing_evidence": per_candidate_missing_evidence,
        "promotion_blockers": list(promotion_blockers),
        "rejection_triggers": list(rejection_triggers),
        "next_research_artifacts_to_build": [
            "candidate_evidence_collection_plan.jsonl",
            "candidate_data_basis_specification.jsonl",
            "candidate_signal_definition_packet.jsonl",
            "candidate_baseline_comparison_requirements.jsonl",
            "candidate_safety_review_requirements.jsonl",
        ],
        "selected_next_safe_action": "build_candidate_evidence_collection_plan",
        "why_selected": (
            "This is the next useful deterministic offline research artifact: it "
            "turns candidate evidence requirements into a collection plan without "
            "implementing or promoting any strategy."
        ),
        "why_no_strategy_implementation_yet": (
            "Strategy implementation remains blocked until required offline "
            "evidence is materialized, collected, and compared against the "
            "baseline."
        ),
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "hard_gate_required": False,
        "requires_daniel": False,
        "daniel_action_required_now": False,
    }


def _candidate_evidence_requirement(
    *,
    candidate_family_id: str,
    candidate_family_label: str,
    required_feature_definitions: list[str],
    required_signal_definition: list[str],
    required_risk_definition: list[str],
    required_regime_analysis: list[str],
    promotion_blockers: list[str],
    rejection_triggers: list[str],
    missing_evidence: list[str],
) -> dict[str, Any]:
    return {
        "candidate_family_id": candidate_family_id,
        "candidate_family_label": candidate_family_label,
        "current_status": "requirements_ready_candidate_unimplemented",
        "implementation_status": "not_implemented",
        "evidence_status": "required_offline_evidence_missing",
        "promotion_status": "promotion_blocked",
        "required_data_inputs": [
            "deterministic_offline_data_source",
            "explicit_adjusted_or_raw_price_basis",
            "as_of_date_filter",
            "fixed_universe_definition",
            "missing_data_policy",
        ],
        "required_feature_definitions": list(required_feature_definitions),
        "required_signal_definition": list(required_signal_definition),
        "required_risk_definition": list(required_risk_definition),
        "required_backtest_outputs": [
            "daily_equity_curve",
            "trade_or_position_ledger",
            "return_summary",
            "benchmark_relative_return_summary",
            "sample_window_and_bar_count",
        ],
        "required_cost_model_outputs": [
            "transaction_cost_assumption",
            "slippage_assumption",
            "turnover_after_costs",
            "cost_sensitivity_summary",
        ],
        "required_benchmark_comparisons": [
            "spy_sma_50_200_control_comparison",
            "buy_and_hold_spy_comparison_if_data_available",
            "same_sample_window_comparison",
        ],
        "required_regime_analysis": list(required_regime_analysis),
        "required_turnover_analysis": [
            "annualized_turnover_estimate",
            "trade_count_by_period",
            "holding_period_distribution",
            "turnover_vs_cost_sensitivity",
        ],
        "required_drawdown_analysis": [
            "maximum_drawdown",
            "drawdown_duration",
            "worst_period_review",
            "drawdown_vs_baseline",
        ],
        "required_failure_mode_review": [
            "lookahead_bias_check",
            "data_snooping_or_overfit_review",
            "single_period_performance_fragility_review",
            "ambiguous_signal_or_missing_data_behavior",
        ],
        "required_safety_checks": [
            "dependency_direction_guard",
            "default_pytest_network_guard",
            "broker_mutation_invariant",
            "no_broker_dependency_in_research_path",
            "no_llm_or_agent_dependency_in_strategy_path",
        ],
        "missing_evidence": list(missing_evidence),
        "promotion_blockers": list(promotion_blockers),
        "rejection_triggers": list(rejection_triggers),
        "broker_dependency": "none",
        "hard_gate_required": False,
        "safety_scope": "offline_only",
    }


def _default_candidate_evidence_requirements_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    requirements = _build_candidate_evidence_requirements({}, artifact_paths)
    return {
        "candidate_evidence_requirements_path": str(
            artifact_paths["candidate_evidence_requirements"]
        ),
        "candidate_evidence_requirements": requirements,
    }


def _candidate_evidence_requirements_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    requirements = payload.get("candidate_evidence_requirements")
    if isinstance(requirements, Mapping):
        return dict(requirements)
    return _build_candidate_evidence_requirements(payload, artifact_paths)


def _apply_candidate_evidence_requirements(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    requirements = _build_candidate_evidence_requirements(payload, artifact_paths)
    payload["candidate_evidence_requirements_path"] = str(
        artifact_paths["candidate_evidence_requirements"]
    )
    payload["candidate_evidence_requirements"] = requirements
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["candidate_evidence_requirements_path"] = payload[
            "candidate_evidence_requirements_path"
        ]
        dashboard["candidate_evidence_requirements"] = dict(requirements)


def _build_candidate_evidence_collection_plan(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    del payload, artifact_paths
    shared_collection_steps = [
        "confirm deterministic offline data source",
        "confirm explicit data basis",
        "define candidate hypothesis",
        "define feature calculations",
        "define signal rule",
        "define risk rule",
        "define backtest window",
        "define benchmark comparison against spy_sma_50_200_control",
        "define transaction cost assumption",
        "collect turnover estimate",
        "collect drawdown evidence",
        "collect regime sensitivity evidence",
        "run dependency-direction guard",
        "run default pytest network guard",
        "run broker mutation invariant",
        "confirm no broker dependency in research path",
        "confirm no LLM/agent dependency in strategy path",
        (
            "defer paper observation until Daniel explicitly scopes broker read "
            "or paper gate"
        ),
    ]
    expected_offline_artifacts = [
        "candidate_hypothesis_packet",
        "candidate_data_requirements_packet",
        "candidate_signal_spec_packet",
        "candidate_risk_spec_packet",
        "candidate_backtest_result_packet",
        "candidate_baseline_comparison_packet",
        "candidate_cost_turnover_packet",
        "candidate_regime_drawdown_packet",
        "candidate_safety_review_packet",
        "candidate_promotion_decision_packet",
    ]
    blocked_until_collected = [
        "candidate_hypothesis_packet_collected",
        "candidate_data_requirements_packet_collected",
        "candidate_signal_spec_packet_collected",
        "candidate_risk_spec_packet_collected",
        "candidate_backtest_result_packet_collected",
        "candidate_baseline_comparison_packet_collected",
        "candidate_cost_turnover_packet_collected",
        "candidate_regime_drawdown_packet_collected",
        "candidate_safety_review_packet_collected",
        "candidate_evidence_compared_against_spy_sma_50_200_control",
    ]
    safety_checks = [
        "dependency-direction guard",
        "default pytest network guard",
        "broker mutation invariant",
        "no broker dependency in research path",
        "no LLM/agent dependency in strategy path",
        "paper submit remains unauthorized",
        "live trading remains forbidden",
    ]
    candidate_collection_plans = [
        _candidate_evidence_collection_plan_entry(
            candidate_family_id="momentum_or_trend_candidate",
            candidate_family_label="Momentum or trend candidate",
            collection_steps=[
                "collect fixed momentum or trend hypothesis",
                "collect as-of bar window and data-basis statement",
                "collect deterministic trend or momentum feature definitions",
                "collect entry and exit rule specification",
                "collect risk cap and risk-off behavior specification",
                "collect offline backtest and baseline comparison outputs",
                "collect turnover, cost, drawdown, and regime evidence",
                "collect offline safety review outputs",
            ],
            features_to_define=[
                "trend_or_momentum_feature_calculated_from_as_of_bars_only",
                "fixed_lookback_window_and_parameter_values",
                "ranking_or_filter_basis_without_optimizer_dependency",
            ],
            signal_rules_to_specify=[
                "deterministic_long_flat_or_ranked_entry_rule",
                "deterministic_exit_or_deallocation_rule",
                "as_of_date_signal_timing_and_no_lookahead_rule",
            ],
            risk_rules_to_specify=[
                "max_position_notional_or_weight",
                "position_concentration_limit",
                "risk_off_or_stop_condition_defined_before_backtest",
            ],
            regime_outputs_to_collect=[
                "trend_regime_performance_split",
                "range_bound_regime_performance_split",
                "high_volatility_regime_performance_split",
            ],
            failure_modes_to_review=[
                "late_trend_entry_after_move",
                "whipsaw_in_range_bound_periods",
                "excessive_turnover_after_costs",
            ],
            safety_checks_to_run=safety_checks,
        ),
        _candidate_evidence_collection_plan_entry(
            candidate_family_id="mean_reversion_candidate",
            candidate_family_label="Mean reversion candidate",
            collection_steps=[
                "collect fixed mean-reversion hypothesis",
                "collect as-of bar window and data-basis statement",
                "collect reference-price deviation feature definitions",
                "collect entry, exit, and failed-reversion rule specification",
                "collect adverse-trend and cooldown risk rules",
                "collect offline backtest and baseline comparison outputs",
                "collect turnover, cost, drawdown, and regime evidence",
                "collect offline safety review outputs",
            ],
            features_to_define=[
                "deviation_from_reference_price_feature",
                "reversion_horizon_definition",
                "entry_and_exit_thresholds_fixed_before_test",
            ],
            signal_rules_to_specify=[
                "deterministic_oversold_or_overextended_entry_rule",
                "deterministic_mean_reversion_exit_rule",
                "as_of_date_signal_timing_and_no_lookahead_rule",
            ],
            risk_rules_to_specify=[
                "max_position_notional_or_weight",
                "adverse_trend_or_failed_reversion_exit_rule",
                "trade_cooldown_or_frequency_limit_if_applicable",
            ],
            regime_outputs_to_collect=[
                "trend_regime_failure_review",
                "range_bound_regime_performance_split",
                "high_volatility_regime_performance_split",
            ],
            failure_modes_to_review=[
                "catching_falling_market_or_failed_reversion",
                "threshold_overfit_to_single_sample",
                "excessive_trade_frequency_after_costs",
            ],
            safety_checks_to_run=safety_checks,
        ),
        _candidate_evidence_collection_plan_entry(
            candidate_family_id="volatility_or_regime_filter_candidate",
            candidate_family_label="Volatility or regime filter candidate",
            collection_steps=[
                "collect fixed volatility or regime-filter hypothesis",
                "collect as-of bar window and data-basis statement",
                "collect regime-state feature and threshold definitions",
                "collect filter activation and deactivation rule specification",
                "collect risk-reduction and ambiguous-state behavior rules",
                "collect offline backtest and baseline comparison outputs",
                "collect turnover, cost, drawdown, and regime evidence",
                "collect offline safety review outputs",
            ],
            features_to_define=[
                "volatility_or_regime_state_feature",
                "filter_thresholds_fixed_before_test",
                "interaction_with_baseline_or_candidate_signal_defined",
            ],
            signal_rules_to_specify=[
                "deterministic_risk_on_or_risk_off_filter_rule",
                "deterministic_filter_update_frequency",
                "as_of_date_signal_timing_and_no_lookahead_rule",
            ],
            risk_rules_to_specify=[
                "risk_reduction_or_exposure_cap_rule",
                "filter_override_limits",
                "behavior_when_regime_state_is_ambiguous_or_missing",
            ],
            regime_outputs_to_collect=[
                "low_volatility_regime_performance_split",
                "high_volatility_regime_performance_split",
                "regime_transition_period_review",
            ],
            failure_modes_to_review=[
                "filter_lag_during_fast_regime_change",
                "false_risk_off_during_recovery",
                "ambiguous_state_or_missing_data_behavior",
            ],
            safety_checks_to_run=safety_checks,
        ),
    ]
    return {
        "collection_plan_status": "ready",
        "collection_plan_mode": "offline_candidate_evidence_collection_plan_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "candidate_collection_plans": candidate_collection_plans,
        "shared_collection_steps": shared_collection_steps,
        "data_collection_requirements": [
            "deterministic offline source and immutable input snapshot",
            "explicit adjusted/raw/total-return data basis",
            "as-of-date filter and no-lookahead rule",
            "fixed universe definition",
            "missing data policy",
            "sample window and usable bar count",
        ],
        "metric_collection_requirements": [
            "daily equity curve",
            "return summary",
            "benchmark comparison against spy_sma_50_200_control",
            "transaction cost and slippage assumptions",
            "turnover estimate",
            "maximum drawdown and drawdown duration",
            "regime sensitivity evidence",
            "failure mode review",
        ],
        "safety_collection_requirements": safety_checks,
        "expected_offline_artifacts": expected_offline_artifacts,
        "blocked_until_collected": blocked_until_collected,
        "selected_next_safe_action": "build_candidate_evidence_collection_status",
        "why_selected": (
            "This is the next useful deterministic offline research artifact "
            "after the collection plan: it records whether each required "
            "candidate evidence item has been collected without implementing "
            "or promoting any strategy."
        ),
        "why_no_strategy_implementation_yet": (
            "Candidate strategy implementation remains blocked until the "
            "offline evidence collection plan is executed and evidence is "
            "compared against the baseline."
        ),
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "hard_gate_required": False,
        "requires_daniel": False,
        "daniel_action_required_now": False,
    }


def _candidate_evidence_collection_plan_entry(
    *,
    candidate_family_id: str,
    candidate_family_label: str,
    collection_steps: list[str],
    features_to_define: list[str],
    signal_rules_to_specify: list[str],
    risk_rules_to_specify: list[str],
    regime_outputs_to_collect: list[str],
    failure_modes_to_review: list[str],
    safety_checks_to_run: list[str],
) -> dict[str, Any]:
    blocked_until_collected = [
        "candidate_hypothesis_packet_collected",
        "candidate_data_requirements_packet_collected",
        "candidate_signal_spec_packet_collected",
        "candidate_risk_spec_packet_collected",
        "candidate_backtest_result_packet_collected",
        "candidate_baseline_comparison_packet_collected",
        "candidate_cost_turnover_packet_collected",
        "candidate_regime_drawdown_packet_collected",
        "candidate_safety_review_packet_collected",
    ]
    return {
        "candidate_family_id": candidate_family_id,
        "candidate_family_label": candidate_family_label,
        "current_status": "collection_plan_ready_candidate_unimplemented",
        "implementation_status": "not_implemented",
        "evidence_status": "evidence_not_collected",
        "collection_status": "ready_to_collect_offline_evidence",
        "promotion_status": "promotion_blocked_pending_evidence_collection",
        "collection_steps": list(collection_steps),
        "data_inputs_to_collect": [
            "deterministic_offline_data_source",
            "explicit_adjusted_or_raw_price_basis",
            "as_of_date_filter",
            "fixed_universe_definition",
            "missing_data_policy",
        ],
        "features_to_define": list(features_to_define),
        "signal_rules_to_specify": list(signal_rules_to_specify),
        "risk_rules_to_specify": list(risk_rules_to_specify),
        "backtest_outputs_to_collect": [
            "daily_equity_curve",
            "trade_or_position_ledger",
            "return_summary",
            "benchmark_relative_return_summary",
            "sample_window_and_bar_count",
        ],
        "cost_outputs_to_collect": [
            "transaction_cost_assumption",
            "slippage_assumption",
            "turnover_after_costs",
            "cost_sensitivity_summary",
        ],
        "benchmark_outputs_to_collect": [
            "spy_sma_50_200_control_comparison",
            "buy_and_hold_spy_comparison_if_data_available",
            "same_sample_window_comparison",
        ],
        "regime_outputs_to_collect": list(regime_outputs_to_collect),
        "turnover_outputs_to_collect": [
            "annualized_turnover_estimate",
            "trade_count_by_period",
            "holding_period_distribution",
            "turnover_vs_cost_sensitivity",
        ],
        "drawdown_outputs_to_collect": [
            "maximum_drawdown",
            "drawdown_duration",
            "worst_period_review",
            "drawdown_vs_baseline",
        ],
        "failure_modes_to_review": list(failure_modes_to_review),
        "safety_checks_to_run": list(safety_checks_to_run),
        "expected_artifacts": [
            f"{candidate_family_id}_hypothesis_packet",
            f"{candidate_family_id}_signal_spec_packet",
            f"{candidate_family_id}_risk_spec_packet",
            f"{candidate_family_id}_backtest_result_packet",
            f"{candidate_family_id}_baseline_comparison_packet",
            f"{candidate_family_id}_safety_review_packet",
        ],
        "blocked_until_collected": blocked_until_collected,
        "broker_dependency": "none",
        "hard_gate_required": False,
        "safety_scope": "offline_only",
    }


def _default_candidate_evidence_collection_plan_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    collection_plan = _build_candidate_evidence_collection_plan({}, artifact_paths)
    return {
        "candidate_evidence_collection_plan_path": str(
            artifact_paths["candidate_evidence_collection_plan"]
        ),
        "candidate_evidence_collection_plan": collection_plan,
    }


def _candidate_evidence_collection_plan_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    collection_plan = payload.get("candidate_evidence_collection_plan")
    if isinstance(collection_plan, Mapping):
        return dict(collection_plan)
    return _build_candidate_evidence_collection_plan(payload, artifact_paths)


def _apply_candidate_evidence_collection_plan(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    collection_plan = _build_candidate_evidence_collection_plan(
        payload,
        artifact_paths,
    )
    payload["candidate_evidence_collection_plan_path"] = str(
        artifact_paths["candidate_evidence_collection_plan"]
    )
    payload["candidate_evidence_collection_plan"] = collection_plan
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["candidate_evidence_collection_plan_path"] = payload[
            "candidate_evidence_collection_plan_path"
        ]
        dashboard["candidate_evidence_collection_plan"] = dict(collection_plan)


def _candidate_evidence_status_item(
    *,
    evidence_item_id: str,
    evidence_item_label: str,
    evidence_category: str,
    status: str,
    blocker: str,
    required_before_implementation: bool = True,
    required_before_promotion: bool = True,
) -> dict[str, Any]:
    return {
        "evidence_item_id": evidence_item_id,
        "evidence_item_label": evidence_item_label,
        "evidence_category": evidence_category,
        "status": status,
        "blocker": blocker,
        "required_before_implementation": required_before_implementation,
        "required_before_promotion": required_before_promotion,
        "offline_only": True,
        "broker_dependency": "none",
    }


def _candidate_evidence_status_items(candidate_family_id: str) -> list[dict[str, Any]]:
    return [
        _candidate_evidence_status_item(
            evidence_item_id="candidate_hypothesis_packet",
            evidence_item_label="Candidate hypothesis packet",
            evidence_category="hypothesis",
            status="ready_to_collect",
            blocker="none",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_data_basis_status",
            evidence_item_label="Deterministic data basis status",
            evidence_category="data",
            status="not_started",
            blocker=f"{candidate_family_id}_data_basis_not_collected",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_feature_definition_status",
            evidence_item_label="Feature calculation definition status",
            evidence_category="feature_definition",
            status="not_started",
            blocker=f"{candidate_family_id}_feature_definition_not_collected",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_signal_rule_status",
            evidence_item_label="Signal rule specification status",
            evidence_category="signal_rule",
            status="blocked",
            blocker=f"{candidate_family_id}_hypothesis_and_data_basis_missing",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_risk_rule_status",
            evidence_item_label="Risk rule specification status",
            evidence_category="risk_rule",
            status="blocked",
            blocker=f"{candidate_family_id}_signal_rule_missing",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_backtest_window_status",
            evidence_item_label="Backtest window status",
            evidence_category="backtest_window",
            status="not_started",
            blocker=f"{candidate_family_id}_backtest_window_not_collected",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_backtest_outputs_status",
            evidence_item_label="Offline backtest output status",
            evidence_category="backtest_outputs",
            status="missing",
            blocker=f"{candidate_family_id}_backtest_result_packet_missing",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_baseline_comparison_status",
            evidence_item_label="Baseline comparison status",
            evidence_category="benchmark_comparison",
            status="missing",
            blocker=f"{candidate_family_id}_baseline_comparison_packet_missing",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_cost_turnover_status",
            evidence_item_label="Cost and turnover evidence status",
            evidence_category="cost_turnover",
            status="missing",
            blocker=f"{candidate_family_id}_cost_turnover_packet_missing",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_drawdown_regime_status",
            evidence_item_label="Drawdown and regime evidence status",
            evidence_category="drawdown_regime",
            status="missing",
            blocker=f"{candidate_family_id}_regime_drawdown_packet_missing",
        ),
        _candidate_evidence_status_item(
            evidence_item_id="candidate_safety_review_status",
            evidence_item_label="Offline safety review status",
            evidence_category="safety_review",
            status="ready_to_collect",
            blocker="none",
        ),
    ]


def _candidate_evidence_collection_status_entry(
    *,
    candidate_family_id: str,
    candidate_family_label: str,
) -> dict[str, Any]:
    evidence_items = _candidate_evidence_status_items(candidate_family_id)
    item_ids_by_status = {
        status: [
            str(item["evidence_item_id"])
            for item in evidence_items
            if item["status"] == status
        ]
        for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES
    }
    promotion_blockers = [
        f"{candidate_family_id}_implementation_not_authorized",
        f"{candidate_family_id}_offline_evidence_missing",
        f"{candidate_family_id}_baseline_comparison_missing",
        f"{candidate_family_id}_paper_observation_deferred",
    ]
    return {
        "candidate_family_id": candidate_family_id,
        "candidate_family_label": candidate_family_label,
        "current_status": "blocked",
        "implementation_status": "not_implemented",
        "evidence_status": "missing",
        "collection_status": "ready_to_collect",
        "promotion_status": "blocked",
        "evidence_items": evidence_items,
        "not_started_items": item_ids_by_status["not_started"],
        "blocked_items": item_ids_by_status["blocked"],
        "ready_to_collect_items": item_ids_by_status["ready_to_collect"],
        "missing_items": item_ids_by_status["missing"],
        "promotion_blockers": promotion_blockers,
        "next_collection_actions": [
            f"build_{candidate_family_id}_evidence_gap_summary",
            f"collect_{candidate_family_id}_hypothesis_packet",
            f"collect_{candidate_family_id}_data_basis_status",
            f"collect_{candidate_family_id}_feature_definition_status",
            f"collect_{candidate_family_id}_safety_review_status",
        ],
        "broker_dependency": "none",
        "hard_gate_required": False,
        "safety_scope": "offline_only",
    }


def _shared_candidate_evidence_collection_status() -> list[dict[str, Any]]:
    shared_items = (
        (
            "deterministic_offline_data_source_status",
            "Deterministic offline data source status",
            "ready_to_collect",
            "none",
        ),
        (
            "explicit_data_basis_status",
            "Explicit data basis status",
            "not_started",
            "explicit_data_basis_not_collected",
        ),
        (
            "candidate_hypothesis_status",
            "Candidate hypothesis status",
            "ready_to_collect",
            "none",
        ),
        (
            "feature_calculation_status",
            "Feature calculation status",
            "not_started",
            "feature_calculation_definition_not_collected",
        ),
        (
            "signal_rule_status",
            "Signal rule status",
            "blocked",
            "candidate_hypothesis_and_feature_definition_missing",
        ),
        (
            "risk_rule_status",
            "Risk rule status",
            "blocked",
            "candidate_signal_rule_missing",
        ),
        (
            "backtest_window_status",
            "Backtest window status",
            "not_started",
            "backtest_window_not_collected",
        ),
        (
            "benchmark_comparison_status",
            "Benchmark comparison status",
            "missing",
            "benchmark_comparison_against_spy_sma_50_200_control_missing",
        ),
        (
            "transaction_cost_assumption_status",
            "Transaction cost assumption status",
            "ready_to_collect",
            "none",
        ),
        (
            "turnover_estimate_status",
            "Turnover estimate status",
            "missing",
            "candidate_turnover_estimate_missing",
        ),
        (
            "drawdown_evidence_status",
            "Drawdown evidence status",
            "missing",
            "candidate_drawdown_evidence_missing",
        ),
        (
            "regime_sensitivity_evidence_status",
            "Regime sensitivity evidence status",
            "missing",
            "candidate_regime_sensitivity_evidence_missing",
        ),
        (
            "dependency_direction_guard_status",
            "Dependency-direction guard status",
            "ready_to_collect",
            "none",
        ),
        (
            "default_pytest_network_guard_status",
            "Default pytest network guard status",
            "ready_to_collect",
            "none",
        ),
        (
            "broker_mutation_invariant_status",
            "Broker mutation invariant status",
            "ready_to_collect",
            "none",
        ),
        (
            "broker_dependency_status",
            "Broker dependency status",
            "ready_to_collect",
            "none",
        ),
        (
            "llm_agent_dependency_status",
            "LLM/agent dependency status",
            "ready_to_collect",
            "none",
        ),
        (
            "paper_observation_deferral_status",
            "Paper observation deferral status",
            "blocked",
            "paper_observation_deferred_until_daniel_explicit_scope",
        ),
    )
    return [
        {
            "shared_status_id": item_id,
            "shared_status_label": label,
            "status": status,
            "blocker": blocker,
            "offline_only": True,
            "broker_dependency": "none",
        }
        for item_id, label, status, blocker in shared_items
    ]


def _candidate_evidence_collection_rollups(
    candidate_statuses: list[Mapping[str, Any]],
    shared_collection_status: list[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    rollups: dict[str, list[dict[str, Any]]] = {
        status: [] for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES
    }
    for candidate in candidate_statuses:
        candidate_id = str(candidate["candidate_family_id"])
        for item in candidate["evidence_items"]:
            if not isinstance(item, Mapping):
                continue
            status = str(item.get("status", ""))
            if status not in rollups:
                continue
            rollups[status].append(
                {
                    "candidate_family_id": candidate_id,
                    "evidence_item_id": str(item["evidence_item_id"]),
                    "evidence_item_label": str(item["evidence_item_label"]),
                    "blocker": str(item["blocker"]),
                }
            )
    for item in shared_collection_status:
        status = str(item.get("status", ""))
        if status not in rollups:
            continue
        rollups[status].append(
            {
                "candidate_family_id": "shared",
                "evidence_item_id": str(item["shared_status_id"]),
                "evidence_item_label": str(item["shared_status_label"]),
                "blocker": str(item["blocker"]),
            }
        )
    return rollups


def _candidate_evidence_status_counts(
    rollups: Mapping[str, list[Mapping[str, Any]]],
) -> dict[str, int]:
    return {
        status: len(rollups.get(status, []))
        for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES
    }


def _build_candidate_evidence_collection_status(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    del payload, artifact_paths
    candidate_statuses = [
        _candidate_evidence_collection_status_entry(
            candidate_family_id="momentum_or_trend_candidate",
            candidate_family_label="Momentum or trend candidate",
        ),
        _candidate_evidence_collection_status_entry(
            candidate_family_id="mean_reversion_candidate",
            candidate_family_label="Mean reversion candidate",
        ),
        _candidate_evidence_collection_status_entry(
            candidate_family_id="volatility_or_regime_filter_candidate",
            candidate_family_label="Volatility or regime filter candidate",
        ),
    ]
    shared_collection_status = _shared_candidate_evidence_collection_status()
    evidence_rollups = _candidate_evidence_collection_rollups(
        candidate_statuses,
        shared_collection_status,
    )
    promotion_blockers = [
        "candidate_strategy_implementation_blocked_until_required_evidence_statused",
        "candidate_offline_evidence_missing",
        "candidate_baseline_comparison_missing",
        "candidate_backtest_outputs_missing",
        "candidate_cost_turnover_drawdown_regime_evidence_missing",
        "paper_observation_deferred_until_daniel_explicitly_scopes_broker_read_or_paper_gate",
    ]
    return {
        "collection_status": "ready",
        "collection_status_mode": (
            "offline_candidate_evidence_collection_status_only"
        ),
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "candidate_statuses": candidate_statuses,
        "shared_collection_status": shared_collection_status,
        "evidence_status_counts": _candidate_evidence_status_counts(
            evidence_rollups
        ),
        "not_started_evidence": evidence_rollups["not_started"],
        "blocked_evidence": evidence_rollups["blocked"],
        "ready_to_collect_evidence": evidence_rollups["ready_to_collect"],
        "missing_evidence": evidence_rollups["missing"],
        "promotion_blockers": promotion_blockers,
        "next_collection_actions": [
            "build_candidate_evidence_gap_summary",
            "collect_candidate_hypothesis_packets",
            "collect_candidate_data_basis_statuses",
            "collect_candidate_feature_definition_statuses",
            "collect_candidate_safety_review_statuses",
        ],
        "selected_next_safe_action": "build_candidate_evidence_gap_summary",
        "why_selected": (
            "This is the next useful deterministic offline artifact: it "
            "summarizes candidate evidence gaps from the status object without "
            "implementing or promoting any strategy."
        ),
        "why_no_strategy_implementation_yet": (
            "Candidate strategy implementation remains blocked until required "
            "evidence is collected, statused, and compared against the baseline."
        ),
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "hard_gate_required": False,
        "requires_daniel": False,
        "daniel_action_required_now": False,
    }


def _default_candidate_evidence_collection_status_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    collection_status = _build_candidate_evidence_collection_status({}, artifact_paths)
    return {
        "candidate_evidence_collection_status_path": str(
            artifact_paths["candidate_evidence_collection_status"]
        ),
        "candidate_evidence_collection_status": collection_status,
    }


def _candidate_evidence_collection_status_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    collection_status = payload.get("candidate_evidence_collection_status")
    if isinstance(collection_status, Mapping):
        return dict(collection_status)
    return _build_candidate_evidence_collection_status(payload, artifact_paths)


def _apply_candidate_evidence_collection_status(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    collection_status = _build_candidate_evidence_collection_status(
        payload,
        artifact_paths,
    )
    payload["candidate_evidence_collection_status_path"] = str(
        artifact_paths["candidate_evidence_collection_status"]
    )
    payload["candidate_evidence_collection_status"] = collection_status
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["candidate_evidence_collection_status_path"] = payload[
            "candidate_evidence_collection_status_path"
        ]
        dashboard["candidate_evidence_collection_status"] = dict(collection_status)


def _candidate_gap_priority(item_id: str, category: str, status: str) -> str:
    del status
    high_item_ids = {
        "candidate_hypothesis_packet",
        "candidate_data_basis_status",
        "candidate_feature_definition_status",
        "candidate_signal_rule_status",
        "candidate_risk_rule_status",
        "candidate_backtest_outputs_status",
        "candidate_baseline_comparison_status",
        "candidate_safety_review_status",
        "deterministic_offline_data_source_status",
        "explicit_data_basis_status",
        "candidate_hypothesis_status",
        "feature_calculation_status",
        "signal_rule_status",
        "risk_rule_status",
        "benchmark_comparison_status",
        "dependency_direction_guard_status",
        "default_pytest_network_guard_status",
        "broker_mutation_invariant_status",
        "broker_dependency_status",
        "llm_agent_dependency_status",
    }
    medium_categories = {
        "backtest_window",
        "cost_turnover",
        "transaction_cost_assumption",
        "turnover",
        "drawdown_regime",
        "drawdown",
        "regime_sensitivity",
        "failure_modes",
    }
    if item_id in high_item_ids:
        return "high"
    if category in medium_categories:
        return "medium"
    return "low"


def _candidate_gap_closure_artifact(item_id: str) -> str:
    artifact_map = {
        "candidate_hypothesis_packet": "candidate_hypothesis_packet.jsonl",
        "candidate_data_basis_status": "candidate_data_basis_status.jsonl",
        "candidate_feature_definition_status": (
            "candidate_feature_definition_status.jsonl"
        ),
        "candidate_signal_rule_status": "candidate_signal_rule_status.jsonl",
        "candidate_risk_rule_status": "candidate_risk_rule_status.jsonl",
        "candidate_backtest_window_status": "candidate_backtest_window_status.jsonl",
        "candidate_backtest_outputs_status": "candidate_backtest_result_packet.jsonl",
        "candidate_baseline_comparison_status": (
            "candidate_baseline_comparison_packet.jsonl"
        ),
        "candidate_cost_turnover_status": "candidate_cost_turnover_packet.jsonl",
        "candidate_drawdown_regime_status": (
            "candidate_regime_drawdown_packet.jsonl"
        ),
        "candidate_safety_review_status": "candidate_safety_review_packet.jsonl",
        "deterministic_offline_data_source_status": (
            "shared_deterministic_data_source_status.jsonl"
        ),
        "explicit_data_basis_status": "shared_data_basis_status.jsonl",
        "candidate_hypothesis_status": "shared_candidate_hypothesis_status.jsonl",
        "feature_calculation_status": "shared_feature_calculation_status.jsonl",
        "signal_rule_status": "shared_signal_rule_status.jsonl",
        "risk_rule_status": "shared_risk_rule_status.jsonl",
        "backtest_window_status": "shared_backtest_window_status.jsonl",
        "benchmark_comparison_status": "shared_benchmark_comparison_status.jsonl",
        "transaction_cost_assumption_status": (
            "shared_transaction_cost_assumption_status.jsonl"
        ),
        "turnover_estimate_status": "shared_turnover_estimate_status.jsonl",
        "drawdown_evidence_status": "shared_drawdown_evidence_status.jsonl",
        "regime_sensitivity_evidence_status": (
            "shared_regime_sensitivity_evidence_status.jsonl"
        ),
        "dependency_direction_guard_status": (
            "shared_dependency_direction_guard_status.jsonl"
        ),
        "default_pytest_network_guard_status": (
            "shared_default_pytest_network_guard_status.jsonl"
        ),
        "broker_mutation_invariant_status": (
            "shared_broker_mutation_invariant_status.jsonl"
        ),
        "broker_dependency_status": "shared_broker_dependency_status.jsonl",
        "llm_agent_dependency_status": "shared_llm_agent_dependency_status.jsonl",
        "paper_observation_deferral_status": (
            "shared_paper_observation_deferral_status.jsonl"
        ),
    }
    return artifact_map.get(item_id, f"{item_id}.jsonl")


def _candidate_gap_why_it_matters(
    label: str,
    category: str,
    status: str,
) -> str:
    return (
        f"{label} is a {category} evidence gap with status {status}; closing it "
        "keeps candidate research comparable to the SPY SMA 50/200 control "
        "before any implementation, promotion, paper observation, or trading."
    )


def _candidate_evidence_gap_entry(item: Mapping[str, Any]) -> dict[str, Any]:
    item_id = str(item["evidence_item_id"])
    label = str(item["evidence_item_label"])
    category = str(item["evidence_category"])
    status = str(item["status"])
    return {
        "gap_id": item_id,
        "gap_label": label,
        "gap_category": category,
        "priority": _candidate_gap_priority(item_id, category, status),
        "status": status,
        "why_it_matters": _candidate_gap_why_it_matters(label, category, status),
        "required_before_implementation": bool(
            item["required_before_implementation"]
        ),
        "required_before_promotion": bool(item["required_before_promotion"]),
        "closure_artifact": _candidate_gap_closure_artifact(item_id),
        "offline_only": True,
        "broker_dependency": "none",
    }


def _shared_candidate_gap_category(shared_status_id: str) -> str:
    category_map = {
        "deterministic_offline_data_source_status": "data_source",
        "explicit_data_basis_status": "data_basis",
        "candidate_hypothesis_status": "hypothesis",
        "feature_calculation_status": "feature_calculation",
        "signal_rule_status": "signal_rule",
        "risk_rule_status": "risk_rule",
        "backtest_window_status": "backtest_window",
        "benchmark_comparison_status": "benchmark_comparison",
        "transaction_cost_assumption_status": "transaction_cost_assumption",
        "turnover_estimate_status": "turnover",
        "drawdown_evidence_status": "drawdown",
        "regime_sensitivity_evidence_status": "regime_sensitivity",
        "dependency_direction_guard_status": "dependency_direction",
        "default_pytest_network_guard_status": "network_guard",
        "broker_mutation_invariant_status": "broker_mutation_guard",
        "broker_dependency_status": "broker_dependency",
        "llm_agent_dependency_status": "llm_agent_dependency",
        "paper_observation_deferral_status": "paper_observation_deferred",
    }
    return category_map[shared_status_id]


def _shared_candidate_evidence_gap_summary() -> list[dict[str, Any]]:
    shared_gap_summary: list[dict[str, Any]] = []
    for item in _shared_candidate_evidence_collection_status():
        shared_status_id = str(item["shared_status_id"])
        label = str(item["shared_status_label"])
        status = str(item["status"])
        category = _shared_candidate_gap_category(shared_status_id)
        shared_gap_summary.append(
            {
                "shared_gap_id": shared_status_id,
                "shared_gap_label": label,
                "gap_category": category,
                "priority": _candidate_gap_priority(
                    shared_status_id,
                    category,
                    status,
                ),
                "status": status,
                "why_it_matters": _candidate_gap_why_it_matters(
                    label,
                    category,
                    status,
                ),
                "closure_artifact": _candidate_gap_closure_artifact(
                    shared_status_id
                ),
                "offline_only": True,
                "broker_dependency": "none",
            }
        )
    return shared_gap_summary


def _candidate_gap_sort_key(gap: Mapping[str, Any]) -> tuple[int, int, str]:
    priority_rank = {
        priority: rank
        for rank, priority in enumerate(_CANDIDATE_EVIDENCE_GAP_PRIORITIES)
    }
    status_rank = {
        "blocked": 0,
        "missing": 1,
        "not_started": 2,
        "ready_to_collect": 3,
    }
    return (
        priority_rank.get(str(gap.get("priority", "low")), 99),
        status_rank.get(str(gap.get("status", "ready_to_collect")), 99),
        str(gap.get("gap_id", gap.get("shared_gap_id", ""))),
    )


def _candidate_evidence_gap_summary_entry(
    candidate_status: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_gaps = [
        _candidate_evidence_gap_entry(item)
        for item in candidate_status["evidence_items"]
        if isinstance(item, Mapping)
    ]
    gaps_by_status = {
        status: [
            str(gap["gap_id"])
            for gap in evidence_gaps
            if gap["status"] == status
        ]
        for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES
    }
    highest_priority_gap = sorted(evidence_gaps, key=_candidate_gap_sort_key)[0]
    candidate_family_id = str(candidate_status["candidate_family_id"])
    return {
        "candidate_family_id": candidate_family_id,
        "candidate_family_label": str(candidate_status["candidate_family_label"]),
        "current_status": str(candidate_status["current_status"]),
        "implementation_status": str(candidate_status["implementation_status"]),
        "evidence_status": str(candidate_status["evidence_status"]),
        "collection_status": str(candidate_status["collection_status"]),
        "promotion_status": str(candidate_status["promotion_status"]),
        "total_gap_count": len(evidence_gaps),
        "highest_priority_gap": str(highest_priority_gap["gap_id"]),
        "evidence_gaps": evidence_gaps,
        "blocked_gaps": gaps_by_status["blocked"],
        "missing_gaps": gaps_by_status["missing"],
        "not_started_gaps": gaps_by_status["not_started"],
        "ready_to_collect_gaps": gaps_by_status["ready_to_collect"],
        "promotion_blockers": list(candidate_status["promotion_blockers"]),
        "next_gap_closure_actions": [
            f"close_{candidate_family_id}_strategy_definition_gaps",
            f"close_{candidate_family_id}_data_and_feature_gaps",
            f"close_{candidate_family_id}_backtest_and_benchmark_gaps",
            f"close_{candidate_family_id}_safety_dependency_gaps",
        ],
        "broker_dependency": "none",
        "hard_gate_required": False,
        "safety_scope": "offline_only",
    }


def _gap_matches_categories(
    gap: Mapping[str, Any],
    categories: set[str],
) -> bool:
    return str(gap.get("gap_category", "")) in categories


def _ranked_candidate_gap_groups(
    candidate_gap_summaries: list[Mapping[str, Any]],
    shared_gap_summary: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidate_gaps: list[Mapping[str, Any]] = []
    for candidate in candidate_gap_summaries:
        gaps = candidate.get("evidence_gaps", [])
        if isinstance(gaps, list):
            candidate_gaps.extend(gap for gap in gaps if isinstance(gap, Mapping))
    all_gaps = [*candidate_gaps, *shared_gap_summary]
    group_specs = (
        (
            "strategy_definition_gaps",
            "Strategy definition gaps",
            "high",
            {"hypothesis", "feature_definition", "feature_calculation", "signal_rule", "risk_rule"},
            (
                "Strategy rules must be explicit before any candidate can be "
                "implemented or compared."
            ),
            "close_strategy_definition_gaps",
        ),
        (
            "data_and_feature_gaps",
            "Data and feature gaps",
            "high",
            {"data", "data_source", "data_basis", "feature_definition", "feature_calculation"},
            (
                "Candidate evidence must identify deterministic data and feature "
                "inputs before code exists."
            ),
            "close_candidate_data_and_feature_gap_packets",
        ),
        (
            "backtest_and_benchmark_gaps",
            "Backtest and benchmark gaps",
            "high",
            {"backtest_window", "backtest_outputs", "benchmark_comparison"},
            (
                "Candidate promotion is blocked without deterministic offline "
                "backtest and baseline comparison artifacts."
            ),
            "materialize_candidate_backtest_benchmark_gap_packets",
        ),
        (
            "cost_turnover_drawdown_gaps",
            "Cost, turnover, and drawdown gaps",
            "medium",
            {"cost_turnover", "transaction_cost_assumption", "turnover", "drawdown"},
            (
                "Cost, turnover, and drawdown evidence prevent candidates from "
                "being ranked on incomplete performance claims."
            ),
            "materialize_candidate_cost_turnover_drawdown_gap_packets",
        ),
        (
            "regime_and_failure_mode_gaps",
            "Regime and failure-mode gaps",
            "medium",
            {"drawdown_regime", "regime_sensitivity", "failure_modes"},
            (
                "Regime and failure-mode evidence is needed before a candidate "
                "can be compared against the control harness."
            ),
            "materialize_candidate_regime_failure_mode_gap_packets",
        ),
        (
            "safety_and_dependency_gaps",
            "Safety and dependency gaps",
            "high",
            {
                "safety_review",
                "dependency_direction",
                "network_guard",
                "broker_mutation_guard",
                "broker_dependency",
                "llm_agent_dependency",
            },
            (
                "Safety and dependency gaps guard against broker, network, SDK, "
                "LLM, and mutation surfaces entering research paths."
            ),
            "run_candidate_safety_dependency_gap_audit_offline",
        ),
        (
            "paper_observation_deferred_gaps",
            "Paper observation deferred gaps",
            "low",
            {"paper_observation_deferred"},
            (
                "Paper observation remains explicitly deferred until Daniel "
                "scopes a separate read-only broker milestone."
            ),
            "keep_paper_observation_deferred_until_daniel_scope",
        ),
    )
    return [
        {
            "group_id": group_id,
            "group_label": group_label,
            "priority": priority,
            "gap_count": sum(
                1 for gap in all_gaps if _gap_matches_categories(gap, categories)
            ),
            "why_ranked_here": why_ranked_here,
            "next_gap_closure_action": next_gap_closure_action,
        }
        for (
            group_id,
            group_label,
            priority,
            categories,
            why_ranked_here,
            next_gap_closure_action,
        ) in group_specs
    ]


def _highest_priority_candidate_gaps(
    candidate_gap_summaries: list[Mapping[str, Any]],
    shared_gap_summary: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    priority_gaps: list[dict[str, Any]] = []
    for candidate in candidate_gap_summaries:
        candidate_id = str(candidate["candidate_family_id"])
        gaps = candidate.get("evidence_gaps", [])
        if not isinstance(gaps, list):
            continue
        for gap in gaps:
            if not isinstance(gap, Mapping):
                continue
            if gap.get("priority") != "high":
                continue
            if gap.get("status") not in {"blocked", "missing", "not_started"}:
                continue
            priority_gaps.append(
                {
                    "scope": "candidate",
                    "candidate_family_id": candidate_id,
                    "gap_id": str(gap["gap_id"]),
                    "gap_label": str(gap["gap_label"]),
                    "priority": str(gap["priority"]),
                    "status": str(gap["status"]),
                    "closure_artifact": str(gap["closure_artifact"]),
                }
            )
    for gap in shared_gap_summary:
        if gap.get("priority") != "high":
            continue
        if gap.get("status") not in {"blocked", "missing", "not_started"}:
            continue
        priority_gaps.append(
            {
                "scope": "shared",
                "candidate_family_id": "shared",
                "gap_id": str(gap["shared_gap_id"]),
                "gap_label": str(gap["shared_gap_label"]),
                "priority": str(gap["priority"]),
                "status": str(gap["status"]),
                "closure_artifact": str(gap["closure_artifact"]),
            }
        )
    return sorted(priority_gaps, key=_candidate_gap_sort_key)[:12]


def _candidate_gap_counts(
    candidate_gap_summaries: list[Mapping[str, Any]],
    shared_gap_summary: list[Mapping[str, Any]],
    ranked_gap_groups: list[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_gaps: list[Mapping[str, Any]] = []
    for candidate in candidate_gap_summaries:
        gaps = candidate.get("evidence_gaps", [])
        if isinstance(gaps, list):
            candidate_gaps.extend(gap for gap in gaps if isinstance(gap, Mapping))
    all_gaps = [*candidate_gaps, *shared_gap_summary]
    return {
        "total_gap_count": len(all_gaps),
        "candidate_gap_count": len(candidate_gaps),
        "shared_gap_count": len(shared_gap_summary),
        "ranked_gap_group_count": len(ranked_gap_groups),
        "by_status": {
            status: sum(1 for gap in all_gaps if gap.get("status") == status)
            for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES
        },
        "by_priority": {
            priority: sum(1 for gap in all_gaps if gap.get("priority") == priority)
            for priority in _CANDIDATE_EVIDENCE_GAP_PRIORITIES
        },
        "by_candidate_family": {
            str(candidate["candidate_family_id"]): int(candidate["total_gap_count"])
            for candidate in candidate_gap_summaries
        },
    }


def _build_candidate_evidence_gap_summary(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    collection_status = _candidate_evidence_collection_status_record(
        payload,
        artifact_paths,
    )
    candidate_gap_summaries = [
        _candidate_evidence_gap_summary_entry(candidate_status)
        for candidate_status in collection_status["candidate_statuses"]
        if isinstance(candidate_status, Mapping)
    ]
    shared_gap_summary = _shared_candidate_evidence_gap_summary()
    ranked_gap_groups = _ranked_candidate_gap_groups(
        candidate_gap_summaries,
        shared_gap_summary,
    )
    highest_priority_gaps = _highest_priority_candidate_gaps(
        candidate_gap_summaries,
        shared_gap_summary,
    )
    return {
        "gap_summary_status": "ready",
        "gap_summary_mode": "offline_candidate_evidence_gap_summary_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "candidate_gap_summaries": candidate_gap_summaries,
        "ranked_gap_groups": ranked_gap_groups,
        "highest_priority_gaps": highest_priority_gaps,
        "shared_gap_summary": shared_gap_summary,
        "gap_counts": _candidate_gap_counts(
            candidate_gap_summaries,
            shared_gap_summary,
            ranked_gap_groups,
        ),
        "next_gap_closure_actions": [
            "build_candidate_gap_closure_queue",
            "close_strategy_definition_gaps",
            "close_candidate_data_and_feature_gap_packets",
            "materialize_candidate_backtest_benchmark_gap_packets",
            "run_candidate_safety_dependency_gap_audit_offline",
        ],
        "next_research_artifacts_to_build": [
            "candidate_gap_closure_queue.jsonl",
            "candidate_hypothesis_packets.jsonl",
            "candidate_data_feature_gap_packets.jsonl",
            "candidate_backtest_benchmark_gap_packets.jsonl",
            "candidate_cost_turnover_drawdown_regime_gap_packets.jsonl",
            "candidate_safety_dependency_gap_packet.jsonl",
        ],
        "selected_next_safe_action": "build_candidate_gap_closure_queue",
        "why_selected": (
            "This offline-only deterministic artifact should queue the highest "
            "priority evidence gaps for closure before any candidate strategy "
            "implementation or promotion."
        ),
        "why_no_strategy_implementation_yet": (
            "Candidate strategy implementation remains blocked until evidence "
            "gaps are summarized, prioritized, closed, and compared against the "
            "baseline."
        ),
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "hard_gate_required": False,
        "requires_daniel": False,
        "daniel_action_required_now": False,
    }


def _default_candidate_evidence_gap_summary_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    gap_summary = _build_candidate_evidence_gap_summary({}, artifact_paths)
    return {
        "candidate_evidence_gap_summary_path": str(
            artifact_paths["candidate_evidence_gap_summary"]
        ),
        "candidate_evidence_gap_summary": gap_summary,
    }


def _candidate_evidence_gap_summary_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    gap_summary = payload.get("candidate_evidence_gap_summary")
    if isinstance(gap_summary, Mapping):
        return dict(gap_summary)
    return _build_candidate_evidence_gap_summary(payload, artifact_paths)


def _apply_candidate_evidence_gap_summary(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    gap_summary = _build_candidate_evidence_gap_summary(payload, artifact_paths)
    payload["candidate_evidence_gap_summary_path"] = str(
        artifact_paths["candidate_evidence_gap_summary"]
    )
    payload["candidate_evidence_gap_summary"] = gap_summary
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["candidate_evidence_gap_summary_path"] = payload[
            "candidate_evidence_gap_summary_path"
        ]
        dashboard["candidate_evidence_gap_summary"] = dict(gap_summary)


def _candidate_gap_group_for_category(category: str) -> str:
    category_groups = (
        (
            "strategy_definition_gaps",
            {
                "hypothesis",
                "feature_definition",
                "feature_calculation",
                "signal_rule",
                "risk_rule",
            },
        ),
        (
            "data_and_feature_gaps",
            {
                "data",
                "data_source",
                "data_basis",
                "feature_definition",
                "feature_calculation",
            },
        ),
        (
            "backtest_and_benchmark_gaps",
            {"backtest_window", "backtest_outputs", "benchmark_comparison"},
        ),
        (
            "cost_turnover_drawdown_gaps",
            {"cost_turnover", "transaction_cost_assumption", "turnover", "drawdown"},
        ),
        (
            "regime_and_failure_mode_gaps",
            {"drawdown_regime", "regime_sensitivity", "failure_modes"},
        ),
        (
            "safety_and_dependency_gaps",
            {
                "safety_review",
                "dependency_direction",
                "network_guard",
                "broker_mutation_guard",
                "broker_dependency",
                "llm_agent_dependency",
            },
        ),
        ("paper_observation_deferred_gaps", {"paper_observation_deferred"}),
    )
    for group_id, categories in category_groups:
        if category in categories:
            return group_id
    return "strategy_definition_gaps"


def _candidate_gap_lookup(
    gap_summary: Mapping[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    candidate_summaries = gap_summary.get("candidate_gap_summaries", [])
    if isinstance(candidate_summaries, list):
        for candidate in candidate_summaries:
            if not isinstance(candidate, Mapping):
                continue
            candidate_id = str(candidate.get("candidate_family_id", "unknown"))
            candidate_label = str(
                candidate.get("candidate_family_label", candidate_id)
            )
            gaps = candidate.get("evidence_gaps", [])
            if not isinstance(gaps, list):
                continue
            for gap in gaps:
                if not isinstance(gap, Mapping):
                    continue
                gap_record = dict(gap)
                gap_record["candidate_family_id"] = candidate_id
                gap_record["candidate_family"] = candidate_label
                lookup[(candidate_id, str(gap.get("gap_id", "")))] = gap_record

    shared_gaps = gap_summary.get("shared_gap_summary", [])
    if isinstance(shared_gaps, list):
        for gap in shared_gaps:
            if not isinstance(gap, Mapping):
                continue
            gap_id = str(gap.get("shared_gap_id", ""))
            gap_record = dict(gap)
            gap_record["gap_id"] = gap_id
            gap_record["gap_label"] = str(gap.get("shared_gap_label", gap_id))
            gap_record["candidate_family_id"] = "shared"
            gap_record["candidate_family"] = "Shared candidate evidence"
            lookup[("shared", gap_id)] = gap_record
    return lookup


def _ranked_candidate_gap_group_lookup(
    gap_summary: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    groups = gap_summary.get("ranked_gap_groups", [])
    if not isinstance(groups, list):
        return {}
    return {
        str(group.get("group_id")): dict(group)
        for group in groups
        if isinstance(group, Mapping)
    }


def _candidate_gap_closure_queue_allowed_scope(group_id: str) -> list[str]:
    base_scope = [
        "offline evidence collection",
        "deterministic artifact materialization",
        "local fixture/test construction",
        "data-quality checks",
    ]
    if group_id in {
        "backtest_and_benchmark_gaps",
        "cost_turnover_drawdown_gaps",
        "regime_and_failure_mode_gaps",
    }:
        base_scope.append("comparison scaffolding")
    if group_id == "safety_and_dependency_gaps":
        base_scope.append("offline dependency and safety audit")
    return base_scope


def _candidate_gap_closure_queue_forbidden_scope() -> list[str]:
    return [
        "broker observation",
        "broker reads",
        "broker mutation",
        "paper submit",
        "live trading",
        "strategy implementation",
        "optimizer implementation",
        "backtester implementation",
        "strategy registry or catalog expansion",
        "network calls",
        "credential use",
        "runtime LLM or agent calls in the trading path",
    ]


def _candidate_gap_closure_acceptance_criteria(
    artifact_name: str,
    gap_id: str,
) -> list[str]:
    return [
        f"{artifact_name} is a deterministic offline JSONL artifact",
        f"artifact records source gap_id={gap_id}",
        "artifact is derived from local packet evidence or local fixtures only",
        "artifact makes no profit claim",
        "artifact preserves broker_state_not_observed",
        "artifact preserves paper_submit_authorized=false",
        "artifact does not implement, promote, or register a candidate strategy",
        "unit coverage keeps default pytest offline, credential-free, broker-free, and network-free",
    ]


def _candidate_gap_action_priority(priority: str) -> str:
    if priority == "high":
        return "P2"
    if priority == "medium":
        return "P3"
    return "P3"


def _candidate_gap_closure_queue_item(
    *,
    rank: int,
    priority_gap: Mapping[str, Any],
    gap_detail: Mapping[str, Any],
    group: Mapping[str, Any],
) -> dict[str, Any]:
    item_id = f"candidate_gap_closure_queue_item_{rank:03d}"
    gap_id = str(priority_gap["gap_id"])
    candidate_family_id = str(priority_gap["candidate_family_id"])
    candidate_family = str(
        gap_detail.get("candidate_family", candidate_family_id)
    )
    gap_label = str(priority_gap.get("gap_label", gap_id))
    gap_status = str(priority_gap.get("status", gap_detail.get("status", "missing")))
    expected_artifact = str(
        priority_gap.get(
            "closure_artifact",
            gap_detail.get("closure_artifact", _candidate_gap_closure_artifact(gap_id)),
        )
    )
    group_id = str(group.get("group_id", "strategy_definition_gaps"))
    closure_action = str(
        group.get("next_gap_closure_action", f"close_{group_id}")
    )
    return {
        "queue_item_id": item_id,
        "action_id": f"execute_{item_id}",
        "rank": rank,
        "priority": str(priority_gap.get("priority", "high")),
        "action_priority": _candidate_gap_action_priority(
            str(priority_gap.get("priority", "high"))
        ),
        "candidate_family": candidate_family,
        "candidate_family_id": candidate_family_id,
        "gap_group_id": group_id,
        "gap_group_label": str(group.get("group_label", group_id)),
        "gap_id": gap_id,
        "gap_label": gap_label,
        "gap_status": gap_status,
        "closure_action": closure_action,
        "closure_objective": (
            f"Create {expected_artifact} for {gap_label} using only deterministic "
            "offline packet evidence before any candidate implementation, "
            "promotion, paper observation, broker read, paper submit, or live trading."
        ),
        "expected_evidence_artifact": expected_artifact,
        "recommended_agent": "Codex",
        "allowed_scope": _candidate_gap_closure_queue_allowed_scope(group_id),
        "forbidden_scope": _candidate_gap_closure_queue_forbidden_scope(),
        "acceptance_criteria": _candidate_gap_closure_acceptance_criteria(
            expected_artifact,
            gap_id,
        ),
        "blocked_by": [gap_status],
        "daniel_action_required": False,
        "broker_state_mode": "broker_state_not_observed",
        "broker_state_observed": False,
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "safety_scope": (
            "offline_only; research_only; signal_evaluation_only; "
            "paper_lab_only; not_live_authorized; broker_state_not_observed; "
            "paper_submit_not_authorized; profit_claim=none"
        ),
        "safety_labels": list(_REQUIRED_LABELS),
    }


def _candidate_gap_closure_queue_items(
    gap_summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    gap_lookup = _candidate_gap_lookup(gap_summary)
    group_lookup = _ranked_candidate_gap_group_lookup(gap_summary)
    priority_gaps = gap_summary.get("highest_priority_gaps", [])
    if not isinstance(priority_gaps, list):
        priority_gaps = []

    queue_items: list[dict[str, Any]] = []
    for priority_gap in priority_gaps:
        if not isinstance(priority_gap, Mapping):
            continue
        candidate_family_id = str(priority_gap.get("candidate_family_id", "shared"))
        gap_id = str(priority_gap.get("gap_id", ""))
        gap_detail = gap_lookup.get((candidate_family_id, gap_id), dict(priority_gap))
        gap_category = str(gap_detail.get("gap_category", ""))
        group_id = _candidate_gap_group_for_category(gap_category)
        group = group_lookup.get(group_id, {"group_id": group_id})
        queue_items.append(
            _candidate_gap_closure_queue_item(
                rank=len(queue_items) + 1,
                priority_gap=priority_gap,
                gap_detail=gap_detail,
                group=group,
            )
        )
    return queue_items


def _build_candidate_gap_closure_queue(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    gap_summary = _candidate_evidence_gap_summary_record(payload, artifact_paths)
    queue_items = _candidate_gap_closure_queue_items(gap_summary)
    selected_item = queue_items[0] if queue_items else {}
    selected_item_id = str(selected_item.get("queue_item_id", ""))
    selected_action = str(
        selected_item.get(
            "action_id",
            "execute_candidate_gap_closure_queue_item_001",
        )
    )
    return {
        "candidate_gap_closure_queue_version": (
            _CANDIDATE_GAP_CLOSURE_QUEUE_VERSION
        ),
        "queue_status": "ready",
        "queue_mode": "offline_candidate_gap_closure_queue_only",
        "artifact_path": str(artifact_paths["candidate_gap_closure_queue"]),
        "source_gap_summary_path": str(
            artifact_paths["candidate_evidence_gap_summary"]
        ),
        "source_gap_summary_status": str(
            gap_summary.get("gap_summary_status", "ready")
        ),
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "queue_item_count": len(queue_items),
        "queue_items": queue_items,
        "selected_queue_item_id": selected_item_id,
        "selected_next_safe_action": selected_action,
        "selected_next_safe_action_type": "candidate_gap_closure_queue_item",
        "selected_work_order": "codex_work_order",
        "selected_owner": "Codex",
        "selection_policy": (
            "highest_priority_gaps_from_candidate_evidence_gap_summary_in_"
            "deterministic_gap_order"
        ),
        "generation_inputs": [
            "candidate_evidence_gap_summary.ranked_gap_groups",
            "candidate_evidence_gap_summary.highest_priority_gaps",
            "candidate_evidence_gap_summary.next_gap_closure_actions",
        ],
        "next_research_artifacts_to_build": [
            str(item["expected_evidence_artifact"]) for item in queue_items
        ],
        "allowed_scope": [
            "offline evidence collection",
            "deterministic artifact materialization",
            "comparison scaffolding",
            "fixture/test construction",
            "data-quality checks",
        ],
        "forbidden_scope": _candidate_gap_closure_queue_forbidden_scope(),
        "acceptance_criteria": [
            "candidate_gap_closure_queue.jsonl exists as one deterministic JSONL record",
            "queue items are derived from v1.19 ranked gap groups and highest priority gaps",
            "first selected action is a concrete queue item rather than queue construction",
            "no queue item recommends broker observation, broker reads, broker mutation, paper submit, or live trading",
            "queue preserves broker_state_not_observed, paper_submit_authorized=false, daniel_action_required=false, and profit_claim=none",
        ],
        "why_selected": (
            "The gap summary artifact already exists, so the next useful "
            "offline-only assistant step is to execute the first concrete gap "
            "closure queue item."
        ),
        "why_no_strategy_implementation_yet": (
            "Candidate strategy implementation remains blocked until queued "
            "offline evidence artifacts are materialized, reviewed, and compared "
            "against the SPY SMA 50/200 control harness."
        ),
        "broker_state_mode": "broker_state_not_observed",
        "broker_state_observed": False,
        "paper_submit_authorized": False,
        "daniel_action_required_now": False,
        "profit_claim": "none",
        "safety_scope": (
            "offline_only; research_only; signal_evaluation_only; paper_lab_only; "
            "not_live_authorized; broker_state_not_observed; "
            "paper_submit_not_authorized; profit_claim=none"
        ),
        "safety_labels": list(_REQUIRED_LABELS),
    }


def _default_candidate_gap_closure_queue_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    queue = _build_candidate_gap_closure_queue({}, artifact_paths)
    return {
        "candidate_gap_closure_queue_path": str(
            artifact_paths["candidate_gap_closure_queue"]
        ),
        "candidate_gap_closure_queue": queue,
    }


def _candidate_gap_closure_queue_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    queue = payload.get("candidate_gap_closure_queue")
    if isinstance(queue, Mapping):
        return dict(queue)
    return _build_candidate_gap_closure_queue(payload, artifact_paths)


def _apply_candidate_gap_closure_queue(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    queue = _build_candidate_gap_closure_queue(payload, artifact_paths)
    payload["candidate_gap_closure_queue_path"] = str(
        artifact_paths["candidate_gap_closure_queue"]
    )
    payload["candidate_gap_closure_queue"] = queue
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["candidate_gap_closure_queue_path"] = payload[
            "candidate_gap_closure_queue_path"
        ]
        dashboard["candidate_gap_closure_queue"] = dict(queue)


def _candidate_lookup_by_id(
    records: Any,
    id_field: str = "candidate_family_id",
) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        return {}
    return {
        str(record.get(id_field)): dict(record)
        for record in records
        if isinstance(record, Mapping) and _has_required_value(record.get(id_field))
    }


def _candidate_risk_rule_queue_item(
    queue: Mapping[str, Any],
) -> dict[str, Any]:
    queue_items = queue.get("queue_items", [])
    if not isinstance(queue_items, list):
        return {}
    first_risk_rule_item: dict[str, Any] = {}
    for item in queue_items:
        if not isinstance(item, Mapping):
            continue
        if (
            item.get("queue_item_id")
            == _CANDIDATE_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID
        ):
            return dict(item)
        if (
            not first_risk_rule_item
            and str(item.get("gap_id", "")) == "candidate_risk_rule_status"
        ):
            first_risk_rule_item = dict(item)
    if first_risk_rule_item:
        return first_risk_rule_item
    selected_item_id = str(queue.get("selected_queue_item_id", ""))
    for item in queue_items:
        if isinstance(item, Mapping) and item.get("queue_item_id") == selected_item_id:
            return dict(item)
    return dict(queue_items[0]) if queue_items and isinstance(queue_items[0], Mapping) else {}


def _candidate_risk_rule_next_actions(
    queue: Mapping[str, Any],
    source_queue_item_id: str,
    source_gap_id: str,
) -> list[str]:
    queue_items = queue.get("queue_items", [])
    if not isinstance(queue_items, list):
        return []
    source_rank = 0
    for item in queue_items:
        if not isinstance(item, Mapping):
            continue
        if item.get("queue_item_id") == source_queue_item_id:
            source_rank = int(item.get("rank", 0))
            break
    later_items = [
        item
        for item in queue_items
        if isinstance(item, Mapping)
        and int(item.get("rank", 0)) > source_rank
        and str(item.get("gap_id", "")) == source_gap_id
    ]
    if not later_items:
        later_items = [
            item
            for item in queue_items
            if isinstance(item, Mapping) and int(item.get("rank", 0)) > source_rank
        ]
    return [str(item["action_id"]) for item in later_items if item.get("action_id")]


def _candidate_risk_status_item(
    candidate_status: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_items = candidate_status.get("evidence_items", [])
    if not isinstance(evidence_items, list):
        return {}
    for item in evidence_items:
        if (
            isinstance(item, Mapping)
            and item.get("evidence_item_id") == "candidate_risk_rule_status"
        ):
            return dict(item)
    return {}


def _candidate_risk_gap(
    candidate_gap_summary: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_gaps = candidate_gap_summary.get("evidence_gaps", [])
    if not isinstance(evidence_gaps, list):
        return {}
    for gap in evidence_gaps:
        if isinstance(gap, Mapping) and gap.get("gap_id") == "candidate_risk_rule_status":
            return dict(gap)
    return {}


def _candidate_missing_risk_rule_evidence(
    *,
    requirement: Mapping[str, Any],
    plan: Mapping[str, Any],
    status_item: Mapping[str, Any],
    risk_gap: Mapping[str, Any],
) -> list[str]:
    missing: list[str] = []
    for item in requirement.get("required_risk_definition", []):
        missing.append(f"required_risk_definition:{item}")
    for item in plan.get("risk_rules_to_specify", []):
        if f"risk_rules_to_specify:{item}" not in missing:
            missing.append(f"risk_rules_to_specify:{item}")
    status = str(status_item.get("status", "missing"))
    if status != "collected":
        missing.append(f"candidate_risk_rule_status:{status}")
    blocker = str(status_item.get("blocker", "candidate_risk_rule_status_missing"))
    if blocker and blocker != "none":
        missing.append(f"risk_rule_blocker:{blocker}")
    gap_status = str(risk_gap.get("status", "missing"))
    missing.append(f"risk_rule_gap_status:{gap_status}")
    return list(dict.fromkeys(missing))


def _candidate_risk_rule_evidence_status(
    *,
    status_item: Mapping[str, Any],
    risk_gap: Mapping[str, Any],
) -> str:
    item_status = str(status_item.get("status", "missing"))
    gap_status = str(risk_gap.get("status", item_status or "missing"))
    if item_status in {"not_applicable", "not-applicable"} or gap_status in {
        "not_applicable",
        "not-applicable",
    }:
        return "not_applicable"
    if item_status in {"blocked"} or gap_status in {"blocked"}:
        return "blocked"
    if item_status in {"collected", "complete"} and gap_status in {
        "collected",
        "complete",
    }:
        return "complete"
    return "incomplete"


def _candidate_risk_rule_evidence_status_breakdown(
    *,
    status_item: Mapping[str, Any],
    risk_gap: Mapping[str, Any],
    missing_evidence: list[str],
) -> dict[str, list[str]]:
    breakdown: dict[str, list[str]] = {
        "complete": [],
        "incomplete": [],
        "blocked": [],
        "not_applicable": [],
    }
    evidence_item_id = str(
        status_item.get("evidence_item_id", "candidate_risk_rule_status")
    )
    item_status = str(status_item.get("status", "missing"))
    if item_status in {"collected", "complete"}:
        breakdown["complete"].append(f"{evidence_item_id}:{item_status}")
    elif item_status in {"not_applicable", "not-applicable"}:
        breakdown["not_applicable"].append(f"{evidence_item_id}:{item_status}")
    elif item_status == "blocked":
        breakdown["blocked"].append(f"{evidence_item_id}:{item_status}")
    else:
        breakdown["incomplete"].append(f"{evidence_item_id}:{item_status}")

    gap_status = str(risk_gap.get("status", "missing"))
    if gap_status in {"collected", "complete"}:
        breakdown["complete"].append(f"risk_rule_gap_status:{gap_status}")
    elif gap_status in {"not_applicable", "not-applicable"}:
        breakdown["not_applicable"].append(f"risk_rule_gap_status:{gap_status}")
    elif gap_status == "blocked":
        breakdown["blocked"].append(f"risk_rule_gap_status:{gap_status}")
    else:
        breakdown["incomplete"].append(f"risk_rule_gap_status:{gap_status}")

    blocker = str(status_item.get("blocker", "none"))
    if blocker and blocker != "none":
        breakdown["blocked"].append(f"risk_rule_blocker:{blocker}")

    for item in missing_evidence:
        target = (
            "blocked"
            if "risk_rule_blocker:" in item or item.endswith(":blocked")
            else "incomplete"
        )
        breakdown[target].append(item)

    return {key: list(dict.fromkeys(values)) for key, values in breakdown.items()}


def _candidate_risk_rule_summary(
    *,
    requirement: Mapping[str, Any],
    plan: Mapping[str, Any],
    candidate_status: Mapping[str, Any],
    candidate_gap_summary: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_family_id = str(requirement["candidate_family_id"])
    status_item = _candidate_risk_status_item(candidate_status)
    risk_gap = _candidate_risk_gap(candidate_gap_summary)
    missing_evidence = _candidate_missing_risk_rule_evidence(
        requirement=requirement,
        plan=plan,
        status_item=status_item,
        risk_gap=risk_gap,
    )
    risk_rule_evidence_status = _candidate_risk_rule_evidence_status(
        status_item=status_item,
        risk_gap=risk_gap,
    )
    evidence_status_breakdown = _candidate_risk_rule_evidence_status_breakdown(
        status_item=status_item,
        risk_gap=risk_gap,
        missing_evidence=missing_evidence,
    )
    return {
        "candidate_family": candidate_family_id,
        "candidate_family_id": candidate_family_id,
        "candidate_family_label": str(requirement["candidate_family_label"]),
        "risk_rule_status": "incomplete",
        "risk_rule_evidence_status": risk_rule_evidence_status,
        "risk_rule_defined": False,
        "position_sizing_defined": False,
        "max_loss_or_drawdown_rule_defined": False,
        "entry_exit_risk_boundary_defined": False,
        "stop_or_deactivation_rule_defined": False,
        "data_quality_risk_rule_defined": False,
        "promotion_blockers": list(
            dict.fromkeys(
                [
                    *requirement.get("promotion_blockers", []),
                    f"{candidate_family_id}_risk_rule_evidence_incomplete",
                    f"{candidate_family_id}_candidate_risk_spec_packet_missing",
                ]
            )
        ),
        "missing_risk_rule_evidence": missing_evidence,
        "evidence_status_breakdown": evidence_status_breakdown,
        "recommended_closure_action": (
            f"close_{candidate_family_id}_risk_rule_definition_gap"
        ),
        "expected_evidence_artifact": f"{candidate_family_id}_risk_spec_packet",
    }


def _candidate_risk_rule_evidence_status_summary(
    summaries: list[Mapping[str, Any]],
) -> dict[str, Any]:
    counts = {
        "complete": 0,
        "incomplete": 0,
        "blocked": 0,
        "not_applicable": 0,
    }
    for summary in summaries:
        status = str(summary.get("risk_rule_evidence_status", "incomplete"))
        if status not in counts:
            status = "incomplete"
        counts[status] += 1
    return {
        **counts,
        "status_categories": [
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        ],
        "missing_evidence_explicit": all(
            isinstance(summary.get("missing_risk_rule_evidence"), list)
            and bool(summary.get("missing_risk_rule_evidence"))
            for summary in summaries
        ),
    }


def _candidate_signal_status_item(
    candidate_status: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_items = candidate_status.get("evidence_items", [])
    if not isinstance(evidence_items, list):
        return {}
    for item in evidence_items:
        if (
            isinstance(item, Mapping)
            and item.get("evidence_item_id") == "candidate_signal_rule_status"
        ):
            return dict(item)
    return {}


def _candidate_signal_gap(
    candidate_gap_summary: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_gaps = candidate_gap_summary.get("evidence_gaps", [])
    if not isinstance(evidence_gaps, list):
        return {}
    for gap in evidence_gaps:
        if isinstance(gap, Mapping) and gap.get("gap_id") == "candidate_signal_rule_status":
            return dict(gap)
    return {}


def _candidate_missing_signal_rule_evidence(
    *,
    requirement: Mapping[str, Any],
    plan: Mapping[str, Any],
    status_item: Mapping[str, Any],
    signal_gap: Mapping[str, Any],
) -> list[str]:
    missing: list[str] = []
    for item in requirement.get("required_signal_definition", []):
        missing.append(f"required_signal_definition:{item}")
    for item in plan.get("signal_rules_to_specify", []):
        if f"signal_rules_to_specify:{item}" not in missing:
            missing.append(f"signal_rules_to_specify:{item}")
    status = str(status_item.get("status", "missing"))
    if status != "collected":
        missing.append(f"candidate_signal_rule_status:{status}")
    blocker = str(status_item.get("blocker", "candidate_signal_rule_status_missing"))
    if blocker and blocker != "none":
        missing.append(f"signal_rule_blocker:{blocker}")
    gap_status = str(signal_gap.get("status", "missing"))
    missing.append(f"signal_rule_gap_status:{gap_status}")
    return list(dict.fromkeys(missing))


def _candidate_signal_rule_evidence_status(
    *,
    status_item: Mapping[str, Any],
    signal_gap: Mapping[str, Any],
) -> str:
    item_status = str(status_item.get("status", "missing"))
    gap_status = str(signal_gap.get("status", item_status or "missing"))
    if item_status in {"not_applicable", "not-applicable"} or gap_status in {
        "not_applicable",
        "not-applicable",
    }:
        return "not_applicable"
    if item_status in {"blocked"} or gap_status in {"blocked"}:
        return "blocked"
    if item_status in {"collected", "complete"} and gap_status in {
        "collected",
        "complete",
    }:
        return "complete"
    return "incomplete"


def _candidate_signal_rule_evidence_status_breakdown(
    *,
    status_item: Mapping[str, Any],
    signal_gap: Mapping[str, Any],
    missing_evidence: list[str],
) -> dict[str, list[str]]:
    breakdown: dict[str, list[str]] = {
        "complete": [],
        "incomplete": [],
        "blocked": [],
        "not_applicable": [],
    }
    evidence_item_id = str(
        status_item.get("evidence_item_id", "candidate_signal_rule_status")
    )
    item_status = str(status_item.get("status", "missing"))
    if item_status in {"collected", "complete"}:
        breakdown["complete"].append(f"{evidence_item_id}:{item_status}")
    elif item_status in {"not_applicable", "not-applicable"}:
        breakdown["not_applicable"].append(f"{evidence_item_id}:{item_status}")
    elif item_status == "blocked":
        breakdown["blocked"].append(f"{evidence_item_id}:{item_status}")
    else:
        breakdown["incomplete"].append(f"{evidence_item_id}:{item_status}")

    gap_status = str(signal_gap.get("status", "missing"))
    if gap_status in {"collected", "complete"}:
        breakdown["complete"].append(f"signal_rule_gap_status:{gap_status}")
    elif gap_status in {"not_applicable", "not-applicable"}:
        breakdown["not_applicable"].append(f"signal_rule_gap_status:{gap_status}")
    elif gap_status == "blocked":
        breakdown["blocked"].append(f"signal_rule_gap_status:{gap_status}")
    else:
        breakdown["incomplete"].append(f"signal_rule_gap_status:{gap_status}")

    blocker = str(status_item.get("blocker", "none"))
    if blocker and blocker != "none":
        breakdown["blocked"].append(f"signal_rule_blocker:{blocker}")

    for item in missing_evidence:
        target = (
            "blocked"
            if "signal_rule_blocker:" in item or item.endswith(":blocked")
            else "incomplete"
        )
        breakdown[target].append(item)

    return {key: list(dict.fromkeys(values)) for key, values in breakdown.items()}


def _candidate_signal_rule_explicit_evidence(
    *,
    requirement: Mapping[str, Any],
    plan: Mapping[str, Any],
    status_item: Mapping[str, Any],
    signal_gap: Mapping[str, Any],
) -> dict[str, Any]:
    item_status = str(status_item.get("status", "missing"))
    gap_status = str(signal_gap.get("status", "missing"))
    blocker = str(status_item.get("blocker", "candidate_signal_rule_status_missing"))
    evidence_items = [
        f"candidate_signal_rule_status:{item_status}",
        f"signal_rule_gap_status:{gap_status}",
    ]
    if blocker and blocker != "none":
        evidence_items.append(f"signal_rule_blocker:{blocker}")
    return {
        "evidence_mode": "deterministic_local_packet_evidence_only",
        "explicit_signal_rules_present": False,
        "rule_source": "none_available_from_local_packet_evidence",
        "required_signal_definition": list(
            requirement.get("required_signal_definition", [])
        ),
        "planned_signal_rules_to_specify": list(
            plan.get("signal_rules_to_specify", [])
        ),
        "local_evidence_items": list(dict.fromkeys(evidence_items)),
        "collection_status": item_status,
        "collection_blocker": blocker or "none",
        "gap_status": gap_status,
        "gap_label": str(signal_gap.get("gap_label", "Signal rule specification status")),
        "broker_state_mode": "broker_state_not_observed",
    }


def _candidate_signal_readiness(
    *,
    signal_rule_evidence_status: str,
    missing_evidence: list[str],
) -> dict[str, Any]:
    if signal_rule_evidence_status == "complete" and not missing_evidence:
        readiness_status = "evidence_ready"
    elif signal_rule_evidence_status == "blocked":
        readiness_status = "blocked"
    elif signal_rule_evidence_status == "not_applicable":
        readiness_status = "not_applicable"
    else:
        readiness_status = "not_ready"
    return {
        "readiness_status": readiness_status,
        "research_ready": False,
        "evidence_ready": readiness_status == "evidence_ready",
        "still_blocked": readiness_status == "blocked",
        "remaining_missing_evidence_count": len(missing_evidence),
        "blocking_evidence": [
            item
            for item in missing_evidence
            if "blocker:" in item or item.endswith(":blocked")
        ],
    }


def _candidate_signal_specification_materialization(
    *,
    candidate_family_id: str,
    explicit_evidence: Mapping[str, Any],
    missing_evidence: list[str],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    readiness_status = str(readiness.get("readiness_status", "not_ready"))
    if readiness_status == "evidence_ready":
        materialization_status = "ready_for_human_specification_review"
    elif readiness_status == "blocked":
        materialization_status = "blocked_missing_explicit_signal_rule_evidence"
    else:
        materialization_status = "not_materialized_missing_signal_rule_evidence"
    return {
        "specification_id": f"{candidate_family_id}_signal_specification",
        "materialization_status": materialization_status,
        "materialization_mode": "offline_status_only_no_strategy_rules_created",
        "explicit_signal_rules_present": bool(
            explicit_evidence.get("explicit_signal_rules_present", False)
        ),
        "materialized_signal_rules": [],
        "remaining_missing_evidence": list(missing_evidence),
        "implementation_status": "not_implemented",
        "promotion_status": "not_promoted",
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "profit_claim": "none",
    }


def _candidate_signal_rule_summary(
    *,
    requirement: Mapping[str, Any],
    plan: Mapping[str, Any],
    candidate_status: Mapping[str, Any],
    candidate_gap_summary: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_family_id = str(requirement["candidate_family_id"])
    status_item = _candidate_signal_status_item(candidate_status)
    signal_gap = _candidate_signal_gap(candidate_gap_summary)
    missing_evidence = _candidate_missing_signal_rule_evidence(
        requirement=requirement,
        plan=plan,
        status_item=status_item,
        signal_gap=signal_gap,
    )
    signal_rule_evidence_status = _candidate_signal_rule_evidence_status(
        status_item=status_item,
        signal_gap=signal_gap,
    )
    evidence_status_breakdown = _candidate_signal_rule_evidence_status_breakdown(
        status_item=status_item,
        signal_gap=signal_gap,
        missing_evidence=missing_evidence,
    )
    explicit_evidence = _candidate_signal_rule_explicit_evidence(
        requirement=requirement,
        plan=plan,
        status_item=status_item,
        signal_gap=signal_gap,
    )
    readiness = _candidate_signal_readiness(
        signal_rule_evidence_status=signal_rule_evidence_status,
        missing_evidence=missing_evidence,
    )
    materialized_specification = _candidate_signal_specification_materialization(
        candidate_family_id=candidate_family_id,
        explicit_evidence=explicit_evidence,
        missing_evidence=missing_evidence,
        readiness=readiness,
    )
    return {
        "candidate_family": candidate_family_id,
        "candidate_family_id": candidate_family_id,
        "candidate_label": str(requirement["candidate_family_label"]),
        "candidate_family_label": str(requirement["candidate_family_label"]),
        "signal_rule_status": "incomplete",
        "signal_rule_evidence_status": signal_rule_evidence_status,
        "signal_rule_defined": False,
        "signal_inputs_defined": False,
        "indicator_or_feature_definition_defined": False,
        "entry_rule_defined": False,
        "exit_rule_defined": False,
        "lookback_or_parameter_bounds_defined": False,
        "data_basis_defined": False,
        "universe_defined": False,
        "rebalance_or_evaluation_schedule_defined": False,
        "leakage_or_lookahead_guard_defined": False,
        "explicit_signal_rule_evidence": explicit_evidence,
        "materialized_candidate_signal_specification": materialized_specification,
        "remaining_missing_signal_rule_evidence": list(missing_evidence),
        "candidate_signal_readiness": readiness,
        "promotion_blockers": list(
            dict.fromkeys(
                [
                    *requirement.get("promotion_blockers", []),
                    f"{candidate_family_id}_signal_rule_evidence_incomplete",
                    f"{candidate_family_id}_candidate_signal_spec_packet_missing",
                ]
            )
        ),
        "missing_signal_rule_evidence": missing_evidence,
        "evidence_status_breakdown": evidence_status_breakdown,
        "recommended_closure_action": (
            f"close_{candidate_family_id}_signal_rule_definition_gap"
        ),
        "expected_evidence_artifact": f"{candidate_family_id}_signal_spec_packet",
    }


def _candidate_signal_rule_evidence_status_summary(
    summaries: list[Mapping[str, Any]],
) -> dict[str, Any]:
    counts = {
        "complete": 0,
        "incomplete": 0,
        "blocked": 0,
        "not_applicable": 0,
    }
    for summary in summaries:
        status = str(summary.get("signal_rule_evidence_status", "incomplete"))
        if status not in counts:
            status = "incomplete"
        counts[status] += 1
    return {
        **counts,
        "status_categories": [
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        ],
        "missing_evidence_explicit": all(
            isinstance(summary.get("missing_signal_rule_evidence"), list)
            and bool(summary.get("missing_signal_rule_evidence"))
            for summary in summaries
        ),
    }


def _candidate_signal_rule_queue_item(
    queue: Mapping[str, Any],
) -> dict[str, Any]:
    queue_items = queue.get("queue_items", [])
    if not isinstance(queue_items, list):
        return {}
    first_signal_rule_item: dict[str, Any] = {}
    for item in queue_items:
        if not isinstance(item, Mapping):
            continue
        if (
            item.get("queue_item_id")
            == _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_QUEUE_ITEM_ID
        ):
            return dict(item)
        if (
            not first_signal_rule_item
            and str(item.get("gap_id", "")) == "candidate_signal_rule_status"
        ):
            first_signal_rule_item = dict(item)
    if first_signal_rule_item:
        return first_signal_rule_item
    selected_item_id = str(queue.get("selected_queue_item_id", ""))
    for item in queue_items:
        if isinstance(item, Mapping) and item.get("queue_item_id") == selected_item_id:
            return dict(item)
    return dict(queue_items[0]) if queue_items and isinstance(queue_items[0], Mapping) else {}


def _candidate_signal_rule_next_actions(
    queue: Mapping[str, Any],
    source_queue_item_id: str,
    source_gap_id: str,
) -> list[str]:
    queue_items = queue.get("queue_items", [])
    if not isinstance(queue_items, list):
        return []
    source_rank = 0
    for item in queue_items:
        if not isinstance(item, Mapping):
            continue
        if item.get("queue_item_id") == source_queue_item_id:
            source_rank = int(item.get("rank", 0))
            break
    later_items = [
        item
        for item in queue_items
        if isinstance(item, Mapping)
        and int(item.get("rank", 0)) > source_rank
        and str(item.get("gap_id", "")) == source_gap_id
    ]
    if not later_items:
        later_items = [
            item
            for item in queue_items
            if isinstance(item, Mapping) and int(item.get("rank", 0)) > source_rank
        ]
    return [str(item["action_id"]) for item in later_items if item.get("action_id")]


def _candidate_regime_or_volatility_condition_evidence(
    *,
    requirement: Mapping[str, Any],
    plan: Mapping[str, Any],
    candidate_status: Mapping[str, Any],
    target_summary: Mapping[str, Any],
    explicit_signal_rule_evidence: Mapping[str, Any],
    materialized_signal_specification: Mapping[str, Any],
    remaining_missing_signal_rule_evidence: list[str],
) -> dict[str, Any]:
    evidence_items = candidate_status.get("evidence_items", [])
    if not isinstance(evidence_items, list):
        evidence_items = []
    evidence_item_statuses = {
        str(item.get("evidence_item_id")): str(item.get("status", "unknown"))
        for item in evidence_items
        if isinstance(item, Mapping)
        and item.get("evidence_category")
        in {"feature_definition", "signal_rule", "drawdown_regime"}
    }
    missing_evidence = requirement.get("missing_evidence", [])
    if not isinstance(missing_evidence, list):
        missing_evidence = []
    condition_missing_evidence = [
        str(item)
        for item in missing_evidence
        if any(token in str(item) for token in ("feature", "signal_rule", "regime"))
    ]
    return {
        "condition_evidence_mode": "deterministic_local_packet_evidence_only",
        "condition_evidence_status": str(
            target_summary.get("signal_rule_evidence_status", "blocked")
        ),
        "candidate_family_id": str(
            target_summary.get(
                "candidate_family_id",
                requirement.get("candidate_family_id", ""),
            )
        ),
        "candidate_family_label": str(
            target_summary.get(
                "candidate_family_label",
                requirement.get("candidate_family_label", ""),
            )
        ),
        "explicit_volatility_or_regime_condition_present": bool(
            explicit_signal_rule_evidence.get("explicit_signal_rules_present", False)
        ),
        "required_condition_features": list(
            requirement.get("required_feature_definitions", [])
            if isinstance(requirement.get("required_feature_definitions"), list)
            else []
        ),
        "planned_condition_features_to_define": list(
            plan.get("features_to_define", [])
            if isinstance(plan.get("features_to_define"), list)
            else []
        ),
        "planned_signal_rules_to_specify": list(
            plan.get("signal_rules_to_specify", [])
            if isinstance(plan.get("signal_rules_to_specify"), list)
            else []
        ),
        "required_regime_analysis": list(
            requirement.get("required_regime_analysis", [])
            if isinstance(requirement.get("required_regime_analysis"), list)
            else []
        ),
        "planned_regime_outputs_to_collect": list(
            plan.get("regime_outputs_to_collect", [])
            if isinstance(plan.get("regime_outputs_to_collect"), list)
            else []
        ),
        "collection_status": str(candidate_status.get("current_status", "blocked")),
        "evidence_item_statuses": evidence_item_statuses,
        "status_only_materialization_status": str(
            materialized_signal_specification.get(
                "materialization_status",
                "blocked_missing_explicit_signal_rule_evidence",
            )
        ),
        "remaining_missing_condition_evidence": condition_missing_evidence,
        "remaining_missing_signal_rule_evidence": list(
            remaining_missing_signal_rule_evidence
        ),
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "profit_claim": "none",
    }


def _build_candidate_signal_rule_status(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    requirements = _candidate_evidence_requirements_record(payload, artifact_paths)
    collection_plan = _candidate_evidence_collection_plan_record(
        payload,
        artifact_paths,
    )
    collection_status = _candidate_evidence_collection_status_record(
        payload,
        artifact_paths,
    )
    gap_summary = _candidate_evidence_gap_summary_record(payload, artifact_paths)
    queue = _candidate_gap_closure_queue_record(payload, artifact_paths)

    requirement_lookup = _candidate_lookup_by_id(
        requirements.get("candidate_requirements", [])
    )
    plan_lookup = _candidate_lookup_by_id(
        collection_plan.get("candidate_collection_plans", [])
    )
    status_lookup = _candidate_lookup_by_id(
        collection_status.get("candidate_statuses", [])
    )
    gap_summary_lookup = _candidate_lookup_by_id(
        gap_summary.get("candidate_gap_summaries", [])
    )
    summaries = [
        _candidate_signal_rule_summary(
            requirement=requirement_lookup[candidate_id],
            plan=plan_lookup.get(candidate_id, {}),
            candidate_status=status_lookup.get(candidate_id, {}),
            candidate_gap_summary=gap_summary_lookup.get(candidate_id, {}),
        )
        for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS
        if candidate_id in requirement_lookup
    ]

    source_item = _candidate_signal_rule_queue_item(queue)
    source_queue_item_id = str(
        source_item.get(
            "queue_item_id",
            _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
        )
    )
    source_gap_id = str(source_item.get("gap_id", "candidate_signal_rule_status"))
    source_candidate_family_id = str(
        source_item.get(
            "candidate_family_id",
            _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID,
        )
    )
    next_actions = _candidate_signal_rule_next_actions(
        queue,
        source_queue_item_id,
        source_gap_id,
    )
    shared_signal_rule_gaps = [
        dict(gap)
        for gap in gap_summary.get("shared_gap_summary", [])
        if isinstance(gap, Mapping) and gap.get("gap_category") == "signal_rule"
    ]
    highest_priority_signal_rule_gaps = [
        dict(gap)
        for gap in gap_summary.get("highest_priority_gaps", [])
        if isinstance(gap, Mapping) and gap.get("gap_id") == source_gap_id
    ]
    target_summary = next(
        (
            dict(summary)
            for summary in summaries
            if summary.get("candidate_family_id") == source_candidate_family_id
        ),
        {},
    )
    target_explicit_evidence = (
        dict(target_summary.get("explicit_signal_rule_evidence", {}))
        if isinstance(target_summary.get("explicit_signal_rule_evidence"), Mapping)
        else {}
    )
    target_materialized_specification = (
        dict(
            target_summary.get(
                "materialized_candidate_signal_specification",
                {},
            )
        )
        if isinstance(
            target_summary.get("materialized_candidate_signal_specification"),
            Mapping,
        )
        else {}
    )
    target_remaining_missing_evidence = list(
        target_summary.get("remaining_missing_signal_rule_evidence", [])
        if isinstance(
            target_summary.get("remaining_missing_signal_rule_evidence"),
            list,
        )
        else []
    )
    target_readiness = (
        dict(target_summary.get("candidate_signal_readiness", {}))
        if isinstance(target_summary.get("candidate_signal_readiness"), Mapping)
        else {}
    )
    target_requirement = dict(requirement_lookup.get(source_candidate_family_id, {}))
    target_plan = dict(plan_lookup.get(source_candidate_family_id, {}))
    target_collection_status = dict(status_lookup.get(source_candidate_family_id, {}))
    target_condition_evidence = _candidate_regime_or_volatility_condition_evidence(
        requirement=target_requirement,
        plan=target_plan,
        candidate_status=target_collection_status,
        target_summary=target_summary,
        explicit_signal_rule_evidence=target_explicit_evidence,
        materialized_signal_specification=target_materialized_specification,
        remaining_missing_signal_rule_evidence=target_remaining_missing_evidence,
    )
    selected_next_action = (
        next_actions[0] if next_actions else "review_candidate_signal_rule_status_artifact"
    )
    return {
        "signal_rule_status_version": _CANDIDATE_SIGNAL_RULE_STATUS_VERSION,
        "signal_rule_status": "ready",
        "signal_rule_status_mode": "offline_candidate_signal_rule_status_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "source_queue_item_id": source_queue_item_id,
        "source_action_id": str(
            source_item.get("action_id", f"execute_{source_queue_item_id}")
        ),
        "source_gap_id": source_gap_id,
        "source_candidate_family_id": source_candidate_family_id,
        "source_candidate_family": str(
            source_item.get(
                "candidate_family",
                _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_CANDIDATE_FAMILY,
            )
        ),
        "source_gap_status": str(source_item.get("gap_status", "blocked")),
        "source_gap_group_id": str(
            source_item.get("gap_group_id", "strategy_definition_gaps")
        ),
        "source_gap_group_label": str(
            source_item.get("gap_group_label", "Strategy definition gaps")
        ),
        "source_closure_action": str(
            source_item.get("closure_action", "close_strategy_definition_gaps")
        ),
        "source_closure_objective": str(
            source_item.get(
                "closure_objective",
                "Create candidate_signal_rule_status.jsonl using deterministic offline packet evidence.",
            )
        ),
        "source_expected_evidence_artifact": str(
            source_item.get(
                "expected_evidence_artifact",
                _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME,
            )
        ),
        "candidate_family_count": len(summaries),
        "candidate_scope_count": len(summaries),
        "shared_scope_count": len(shared_signal_rule_gaps),
        "candidate_signal_rule_summaries": summaries,
        "target_candidate_signal_rule_summary": target_summary,
        "target_explicit_signal_rule_evidence": target_explicit_evidence,
        "target_regime_or_volatility_condition_evidence": target_condition_evidence,
        "target_materialized_candidate_signal_specification": (
            target_materialized_specification
        ),
        "target_remaining_missing_signal_rule_evidence": (
            target_remaining_missing_evidence
        ),
        "target_candidate_signal_readiness": target_readiness,
        "shared_signal_rule_gaps": shared_signal_rule_gaps,
        "highest_priority_signal_rule_gaps": highest_priority_signal_rule_gaps,
        "evidence_status_summary": _candidate_signal_rule_evidence_status_summary(
            summaries
        ),
        "signal_rule_acceptance_criteria": [
            "candidate_signal_rule_status.jsonl exists as one deterministic JSONL record",
            (
                "source_queue_item_id="
                f"{_CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_QUEUE_ITEM_ID}"
            ),
            (
                "source_candidate_family_id="
                f"{_CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID}"
            ),
            "source_gap_id=candidate_signal_rule_status",
            "target explicit signal-rule evidence is recorded without inventing rules",
            "target volatility/regime condition evidence is recorded as status-only local evidence",
            "target materialized candidate signal specification remains status-only when explicit rules are missing",
            "target readiness distinguishes research-ready, evidence-ready, blocked, and not-ready states",
            "each candidate family distinguishes complete, incomplete, blocked, and not-applicable evidence buckets",
            "each candidate family has explicit incomplete or blocked signal-rule evidence when missing",
            "candidate strategies remain unimplemented, unpromoted, and not paper-ready",
            (
                "selected_next_safe_action="
                f"{_CANDIDATE_SIGNAL_RULE_STATUS_NEXT_ACTION_ID}"
            ),
            "broker_state_mode=broker_state_not_observed",
            "paper_submit_authorized=false",
            "daniel_action_required_now=false",
            "profit_claim=none",
            "safety_scope=offline_only",
        ],
        "next_signal_rule_closure_actions": next_actions,
        "selected_next_safe_action": selected_next_action,
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "daniel_action_required_now": False,
        "profit_claim": "none",
        "safety_scope": "offline_only",
        "safety_labels": list(_REQUIRED_LABELS),
    }


def _default_candidate_signal_rule_status_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    status = _build_candidate_signal_rule_status({}, artifact_paths)
    return {
        "candidate_signal_rule_status_path": str(
            artifact_paths["candidate_signal_rule_status"]
        ),
        "candidate_signal_rule_status": status,
    }


def _candidate_signal_rule_status_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    status = payload.get("candidate_signal_rule_status")
    if isinstance(status, Mapping):
        return dict(status)
    return _build_candidate_signal_rule_status(payload, artifact_paths)


def _apply_candidate_signal_rule_status(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    status = _build_candidate_signal_rule_status(payload, artifact_paths)
    payload["candidate_signal_rule_status_path"] = str(
        artifact_paths["candidate_signal_rule_status"]
    )
    payload["candidate_signal_rule_status"] = status
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["candidate_signal_rule_status_path"] = payload[
            "candidate_signal_rule_status_path"
        ]
        dashboard["candidate_signal_rule_status"] = dict(status)


def _write_candidate_signal_rule_status_artifact(
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    status = payload.get("candidate_signal_rule_status")
    record = status if isinstance(status, Mapping) else {}
    line = json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n"
    (output_root / _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME).write_text(
        line,
        encoding="utf-8",
        newline="\n",
    )


def _build_candidate_risk_rule_status(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    requirements = _candidate_evidence_requirements_record(payload, artifact_paths)
    collection_plan = _candidate_evidence_collection_plan_record(
        payload,
        artifact_paths,
    )
    collection_status = _candidate_evidence_collection_status_record(
        payload,
        artifact_paths,
    )
    gap_summary = _candidate_evidence_gap_summary_record(payload, artifact_paths)
    queue = _candidate_gap_closure_queue_record(payload, artifact_paths)

    requirement_lookup = _candidate_lookup_by_id(
        requirements.get("candidate_requirements", [])
    )
    plan_lookup = _candidate_lookup_by_id(
        collection_plan.get("candidate_collection_plans", [])
    )
    status_lookup = _candidate_lookup_by_id(
        collection_status.get("candidate_statuses", [])
    )
    gap_summary_lookup = _candidate_lookup_by_id(
        gap_summary.get("candidate_gap_summaries", [])
    )
    summaries = [
        _candidate_risk_rule_summary(
            requirement=requirement_lookup[candidate_id],
            plan=plan_lookup.get(candidate_id, {}),
            candidate_status=status_lookup.get(candidate_id, {}),
            candidate_gap_summary=gap_summary_lookup.get(candidate_id, {}),
        )
        for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS
        if candidate_id in requirement_lookup
    ]

    source_item = _candidate_risk_rule_queue_item(queue)
    source_queue_item_id = str(
        source_item.get(
            "queue_item_id",
            _CANDIDATE_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
        )
    )
    source_gap_id = str(source_item.get("gap_id", "candidate_risk_rule_status"))
    source_candidate_family_id = str(
        source_item.get(
            "candidate_family_id",
            _CANDIDATE_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID,
        )
    )
    next_actions = _candidate_risk_rule_next_actions(
        queue,
        source_queue_item_id,
        source_gap_id,
    )
    shared_risk_rule_gaps = [
        dict(gap)
        for gap in gap_summary.get("shared_gap_summary", [])
        if isinstance(gap, Mapping) and gap.get("gap_category") == "risk_rule"
    ]
    highest_priority_risk_rule_gaps = [
        dict(gap)
        for gap in gap_summary.get("highest_priority_gaps", [])
        if isinstance(gap, Mapping) and gap.get("gap_id") == source_gap_id
    ]
    target_summary = next(
        (
            dict(summary)
            for summary in summaries
            if summary.get("candidate_family_id") == source_candidate_family_id
        ),
        {},
    )
    selected_next_action = (
        next_actions[0] if next_actions else "review_candidate_risk_rule_status_artifact"
    )
    return {
        "risk_rule_status_version": _CANDIDATE_RISK_RULE_STATUS_VERSION,
        "risk_rule_status": "ready",
        "risk_rule_status_mode": "offline_candidate_risk_rule_status_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "source_queue_item_id": source_queue_item_id,
        "source_action_id": str(
            source_item.get("action_id", f"execute_{source_queue_item_id}")
        ),
        "source_gap_id": source_gap_id,
        "source_candidate_family_id": source_candidate_family_id,
        "source_candidate_family": str(
            source_item.get(
                "candidate_family",
                _CANDIDATE_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY,
            )
        ),
        "source_gap_status": str(source_item.get("gap_status", "blocked")),
        "source_gap_group_id": str(
            source_item.get("gap_group_id", "strategy_definition_gaps")
        ),
        "source_gap_group_label": str(
            source_item.get("gap_group_label", "Strategy definition gaps")
        ),
        "source_closure_action": str(
            source_item.get("closure_action", "close_strategy_definition_gaps")
        ),
        "source_closure_objective": str(
            source_item.get(
                "closure_objective",
                "Create candidate_risk_rule_status.jsonl using deterministic offline packet evidence.",
            )
        ),
        "source_expected_evidence_artifact": str(
            source_item.get(
                "expected_evidence_artifact",
                _CANDIDATE_RISK_RULE_STATUS_FILENAME,
            )
        ),
        "candidate_family_count": len(summaries),
        "candidate_scope_count": len(summaries),
        "shared_scope_count": len(shared_risk_rule_gaps),
        "candidate_risk_rule_summaries": summaries,
        "target_candidate_risk_rule_summary": target_summary,
        "shared_risk_rule_gaps": shared_risk_rule_gaps,
        "highest_priority_risk_rule_gaps": highest_priority_risk_rule_gaps,
        "evidence_status_summary": _candidate_risk_rule_evidence_status_summary(
            summaries
        ),
        "risk_rule_acceptance_criteria": [
            "candidate_risk_rule_status.jsonl exists as one deterministic JSONL record",
            (
                "source_queue_item_id="
                f"{_CANDIDATE_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID}"
            ),
            (
                "source_candidate_family_id="
                f"{_CANDIDATE_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID}"
            ),
            "source_gap_id=candidate_risk_rule_status",
            "each candidate family distinguishes complete, incomplete, blocked, and not-applicable evidence buckets",
            "each candidate family has explicit incomplete or blocked risk-rule evidence when missing",
            "candidate strategies remain unimplemented, unpromoted, and not paper-ready",
            (
                "selected_next_safe_action="
                f"{_CANDIDATE_RISK_RULE_STATUS_NEXT_ACTION_ID}"
            ),
            "broker_state_mode=broker_state_not_observed",
            "paper_submit_authorized=false",
            "daniel_action_required_now=false",
            "profit_claim=none",
            "safety_scope=offline_only",
        ],
        "next_risk_rule_closure_actions": next_actions,
        "selected_next_safe_action": selected_next_action,
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "daniel_action_required_now": False,
        "profit_claim": "none",
        "safety_scope": "offline_only",
        "safety_labels": list(_REQUIRED_LABELS),
    }


def _default_candidate_risk_rule_status_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    status = _build_candidate_risk_rule_status({}, artifact_paths)
    return {
        "candidate_risk_rule_status_path": str(
            artifact_paths["candidate_risk_rule_status"]
        ),
        "candidate_risk_rule_status": status,
    }


def _candidate_risk_rule_status_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    status = payload.get("candidate_risk_rule_status")
    if isinstance(status, Mapping):
        return dict(status)
    return _build_candidate_risk_rule_status(payload, artifact_paths)


def _apply_candidate_risk_rule_status(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    status = _build_candidate_risk_rule_status(payload, artifact_paths)
    payload["candidate_risk_rule_status_path"] = str(
        artifact_paths["candidate_risk_rule_status"]
    )
    payload["candidate_risk_rule_status"] = status
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["candidate_risk_rule_status_path"] = payload[
            "candidate_risk_rule_status_path"
        ]
        dashboard["candidate_risk_rule_status"] = dict(status)


def _shared_status_item(
    collection_status: Mapping[str, Any],
    status_id: str,
) -> dict[str, Any]:
    shared_statuses = collection_status.get("shared_collection_status", [])
    if not isinstance(shared_statuses, list):
        return {}
    for item in shared_statuses:
        if (
            isinstance(item, Mapping)
            and item.get("shared_status_id") == status_id
        ):
            return dict(item)
    return {}


def _shared_gap_item(
    gap_summary: Mapping[str, Any],
    gap_id: str,
) -> dict[str, Any]:
    shared_gaps = gap_summary.get("shared_gap_summary", [])
    if not isinstance(shared_gaps, list):
        return {}
    for gap in shared_gaps:
        if (
            isinstance(gap, Mapping)
            and gap.get("shared_gap_id") == gap_id
        ):
            return dict(gap)
    return {}


def _shared_risk_rule_queue_item(
    queue: Mapping[str, Any],
) -> dict[str, Any]:
    queue_items = queue.get("queue_items", [])
    if not isinstance(queue_items, list):
        return {}
    first_shared_risk_item: dict[str, Any] = {}
    for item in queue_items:
        if not isinstance(item, Mapping):
            continue
        if (
            item.get("queue_item_id")
            == _SHARED_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID
        ):
            return dict(item)
        if (
            not first_shared_risk_item
            and str(item.get("candidate_family_id", "")) == "shared"
            and str(item.get("gap_id", "")) == "risk_rule_status"
        ):
            first_shared_risk_item = dict(item)
    if first_shared_risk_item:
        return first_shared_risk_item
    return dict(queue_items[0]) if queue_items and isinstance(queue_items[0], Mapping) else {}


def _shared_risk_rule_next_actions(
    queue: Mapping[str, Any],
    source_queue_item_id: str,
    source_gap_id: str,
) -> list[str]:
    queue_items = queue.get("queue_items", [])
    if not isinstance(queue_items, list):
        return []
    source_rank = 0
    for item in queue_items:
        if not isinstance(item, Mapping):
            continue
        if item.get("queue_item_id") == source_queue_item_id:
            source_rank = int(item.get("rank", 0))
            break
    later_items = [
        item
        for item in queue_items
        if isinstance(item, Mapping)
        and int(item.get("rank", 0)) > source_rank
        and str(item.get("gap_id", "")) == source_gap_id
    ]
    if not later_items:
        later_items = [
            item
            for item in queue_items
            if isinstance(item, Mapping) and int(item.get("rank", 0)) > source_rank
        ]
    return [str(item["action_id"]) for item in later_items if item.get("action_id")]


def _shared_risk_rule_evidence_status(
    *,
    status_item: Mapping[str, Any],
    risk_gap: Mapping[str, Any],
) -> str:
    item_status = str(status_item.get("status", "missing"))
    gap_status = str(risk_gap.get("status", item_status or "missing"))
    if item_status in {"not_applicable", "not-applicable"} or gap_status in {
        "not_applicable",
        "not-applicable",
    }:
        return "not_applicable"
    if item_status == "blocked" or gap_status == "blocked":
        return "blocked"
    if item_status in {"collected", "complete"} and gap_status in {
        "collected",
        "complete",
    }:
        return "complete"
    return "incomplete"


def _shared_risk_remaining_evidence(
    *,
    requirements: Mapping[str, Any],
    status_item: Mapping[str, Any],
    risk_gap: Mapping[str, Any],
    candidate_summaries: list[Mapping[str, Any]],
) -> list[str]:
    missing: list[str] = []
    for item in requirements.get("shared_evidence_requirements", []):
        if item == "risk_rule_definition":
            missing.append(f"shared_evidence_requirement:{item}")
    status = str(status_item.get("status", "missing"))
    if status != "collected":
        missing.append(f"shared_risk_rule_status:{status}")
    blocker = str(status_item.get("blocker", "shared_risk_rule_status_missing"))
    if blocker and blocker != "none":
        missing.append(f"shared_risk_rule_blocker:{blocker}")
    gap_status = str(risk_gap.get("status", "missing"))
    missing.append(f"shared_risk_rule_gap_status:{gap_status}")
    for summary in candidate_summaries:
        candidate_id = str(summary.get("candidate_family_id", "unknown"))
        for item in summary.get("missing_risk_rule_evidence", []):
            missing.append(f"{candidate_id}:{item}")
    return list(dict.fromkeys(missing))


def _shared_risk_rule_evidence_breakdown(
    *,
    status_item: Mapping[str, Any],
    risk_gap: Mapping[str, Any],
    remaining_missing_evidence: list[str],
) -> dict[str, list[str]]:
    breakdown: dict[str, list[str]] = {
        "complete": [],
        "incomplete": [],
        "blocked": [],
        "not_applicable": [],
    }
    item_status = str(status_item.get("status", "missing"))
    gap_status = str(risk_gap.get("status", "missing"))
    if item_status in {"collected", "complete"}:
        breakdown["complete"].append(f"shared_risk_rule_status:{item_status}")
    elif item_status in {"not_applicable", "not-applicable"}:
        breakdown["not_applicable"].append(
            f"shared_risk_rule_status:{item_status}"
        )
    elif item_status == "blocked":
        breakdown["blocked"].append(f"shared_risk_rule_status:{item_status}")
    else:
        breakdown["incomplete"].append(f"shared_risk_rule_status:{item_status}")
    if gap_status in {"collected", "complete"}:
        breakdown["complete"].append(f"shared_risk_rule_gap_status:{gap_status}")
    elif gap_status in {"not_applicable", "not-applicable"}:
        breakdown["not_applicable"].append(
            f"shared_risk_rule_gap_status:{gap_status}"
        )
    elif gap_status == "blocked":
        breakdown["blocked"].append(f"shared_risk_rule_gap_status:{gap_status}")
    else:
        breakdown["incomplete"].append(f"shared_risk_rule_gap_status:{gap_status}")
    blocker = str(status_item.get("blocker", "none"))
    if blocker and blocker != "none":
        breakdown["blocked"].append(f"shared_risk_rule_blocker:{blocker}")
    for item in remaining_missing_evidence:
        target = (
            "blocked"
            if "blocker:" in item or item.endswith(":blocked")
            else "incomplete"
        )
        breakdown[target].append(item)
    return {key: list(dict.fromkeys(values)) for key, values in breakdown.items()}


def _candidate_missing_risk_items_for_tokens(
    summary: Mapping[str, Any],
    tokens: tuple[str, ...],
) -> list[str]:
    missing_items = summary.get("missing_risk_rule_evidence", [])
    if not isinstance(missing_items, list):
        return []
    return [
        str(item)
        for item in missing_items
        if any(token in str(item) for token in tokens)
    ]


def _shared_risk_evidence_bucket(
    *,
    bucket_id: str,
    bucket_label: str,
    tokens: tuple[str, ...],
    candidate_summaries: list[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_evidence = []
    for summary in candidate_summaries:
        candidate_evidence.append(
            {
                "candidate_family_id": str(
                    summary.get("candidate_family_id", "unknown")
                ),
                "risk_rule_status": str(
                    summary.get("risk_rule_status", "incomplete")
                ),
                "risk_rule_evidence_status": str(
                    summary.get("risk_rule_evidence_status", "incomplete")
                ),
                "missing_evidence": _candidate_missing_risk_items_for_tokens(
                    summary,
                    tokens,
                ),
            }
        )
    return {
        "bucket_id": bucket_id,
        "bucket_label": bucket_label,
        "evidence_mode": "deterministic_local_packet_evidence_only",
        "evidence_status": "missing",
        "explicit_rules_present": False,
        "candidate_evidence": candidate_evidence,
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
    }


def _shared_risk_rule_readiness(
    *,
    evidence_status: str,
    remaining_missing_evidence: list[str],
) -> dict[str, Any]:
    if evidence_status == "complete" and not remaining_missing_evidence:
        readiness_status = "evidence_ready"
    elif evidence_status == "blocked":
        readiness_status = "blocked"
    elif evidence_status == "not_applicable":
        readiness_status = "not_applicable"
    else:
        readiness_status = "not_ready"
    return {
        "readiness_status": readiness_status,
        "research_ready": False,
        "evidence_ready": readiness_status == "evidence_ready",
        "still_blocked": readiness_status == "blocked",
        "remaining_missing_evidence_count": len(remaining_missing_evidence),
        "blocking_evidence": [
            item
            for item in remaining_missing_evidence
            if "blocker:" in item or item.endswith(":blocked")
        ],
    }


def _shared_risk_specification_materialization(
    *,
    explicit_evidence: Mapping[str, Any],
    remaining_missing_evidence: list[str],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    readiness_status = str(readiness.get("readiness_status", "not_ready"))
    if readiness_status == "evidence_ready":
        materialization_status = "ready_for_human_risk_specification_review"
    elif readiness_status == "blocked":
        materialization_status = "blocked_missing_shared_risk_rule_evidence"
    else:
        materialization_status = "not_materialized_missing_shared_risk_rule_evidence"
    return {
        "specification_id": "shared_risk_rule_specification",
        "materialization_status": materialization_status,
        "materialization_mode": "offline_status_only_no_strategy_rules_created",
        "explicit_risk_rules_present": bool(
            explicit_evidence.get("explicit_risk_rules_present", False)
        ),
        "materialized_risk_rules": [],
        "position_sizing_rules": [],
        "stop_or_exit_rules": [],
        "drawdown_or_exposure_controls": [],
        "portfolio_or_risk_cap_rules": [],
        "remaining_missing_evidence": list(remaining_missing_evidence),
        "implementation_status": "not_implemented",
        "promotion_status": "not_promoted",
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "profit_claim": "none",
    }


def _build_shared_risk_rule_status(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    requirements = _candidate_evidence_requirements_record(payload, artifact_paths)
    collection_status = _candidate_evidence_collection_status_record(
        payload,
        artifact_paths,
    )
    gap_summary = _candidate_evidence_gap_summary_record(payload, artifact_paths)
    queue = _candidate_gap_closure_queue_record(payload, artifact_paths)
    candidate_risk_status = _candidate_risk_rule_status_record(
        payload,
        artifact_paths,
    )
    candidate_summaries = [
        dict(item)
        for item in candidate_risk_status.get("candidate_risk_rule_summaries", [])
        if isinstance(item, Mapping)
    ]
    source_item = _shared_risk_rule_queue_item(queue)
    source_queue_item_id = str(
        source_item.get(
            "queue_item_id",
            _SHARED_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
        )
    )
    source_gap_id = str(source_item.get("gap_id", "risk_rule_status"))
    source_candidate_family_id = str(
        source_item.get(
            "candidate_family_id",
            _SHARED_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID,
        )
    )
    status_item = _shared_status_item(collection_status, source_gap_id)
    risk_gap = _shared_gap_item(gap_summary, source_gap_id)
    shared_risk_rule_gaps = [
        dict(gap)
        for gap in gap_summary.get("shared_gap_summary", [])
        if isinstance(gap, Mapping) and gap.get("gap_category") == "risk_rule"
    ]
    highest_priority_remaining_gaps = [
        dict(gap)
        for gap in gap_summary.get("highest_priority_gaps", [])
        if isinstance(gap, Mapping)
        and str(gap.get("gap_id", "")) in {source_gap_id, "candidate_risk_rule_status"}
    ]
    evidence_status = _shared_risk_rule_evidence_status(
        status_item=status_item,
        risk_gap=risk_gap,
    )
    remaining_missing_evidence = _shared_risk_remaining_evidence(
        requirements=requirements,
        status_item=status_item,
        risk_gap=risk_gap,
        candidate_summaries=candidate_summaries,
    )
    explicit_evidence = {
        "evidence_mode": "deterministic_local_packet_evidence_only",
        "evidence_status": evidence_status,
        "explicit_risk_rules_present": False,
        "rule_source": "none_available_from_local_packet_evidence",
        "shared_status_id": str(status_item.get("shared_status_id", source_gap_id)),
        "shared_status": str(status_item.get("status", "missing")),
        "shared_status_blocker": str(
            status_item.get("blocker", "shared_risk_rule_status_missing")
        ),
        "shared_gap_status": str(risk_gap.get("status", "missing")),
        "shared_gap_label": str(risk_gap.get("shared_gap_label", "Risk rule status")),
        "local_evidence_items": [
            f"shared_risk_rule_status:{status_item.get('status', 'missing')}",
            f"shared_risk_rule_gap_status:{risk_gap.get('status', 'missing')}",
            f"shared_risk_rule_blocker:{status_item.get('blocker', 'missing')}",
        ],
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "profit_claim": "none",
    }
    position_sizing_evidence = _shared_risk_evidence_bucket(
        bucket_id="position_sizing_evidence",
        bucket_label="Position sizing evidence",
        tokens=("position", "notional", "weight"),
        candidate_summaries=candidate_summaries,
    )
    stop_or_exit_evidence = _shared_risk_evidence_bucket(
        bucket_id="stop_or_exit_evidence",
        bucket_label="Stop or exit evidence",
        tokens=("exit", "stop", "risk_off", "adverse_trend", "failed_reversion"),
        candidate_summaries=candidate_summaries,
    )
    drawdown_or_exposure_control_evidence = _shared_risk_evidence_bucket(
        bucket_id="drawdown_or_exposure_control_evidence",
        bucket_label="Drawdown or exposure control evidence",
        tokens=("drawdown", "exposure", "risk_reduction"),
        candidate_summaries=candidate_summaries,
    )
    portfolio_or_risk_cap_evidence = _shared_risk_evidence_bucket(
        bucket_id="portfolio_or_risk_cap_evidence",
        bucket_label="Portfolio or risk-cap evidence",
        tokens=("concentration", "exposure_cap", "filter_override", "max_position"),
        candidate_summaries=candidate_summaries,
    )
    readiness = _shared_risk_rule_readiness(
        evidence_status=evidence_status,
        remaining_missing_evidence=remaining_missing_evidence,
    )
    materialized_specification = _shared_risk_specification_materialization(
        explicit_evidence=explicit_evidence,
        remaining_missing_evidence=remaining_missing_evidence,
        readiness=readiness,
    )
    next_actions = _shared_risk_rule_next_actions(
        queue,
        source_queue_item_id,
        source_gap_id,
    )
    selected_next_action = (
        next_actions[0] if next_actions else "review_shared_risk_rule_status_artifact"
    )
    evidence_breakdown = _shared_risk_rule_evidence_breakdown(
        status_item=status_item,
        risk_gap=risk_gap,
        remaining_missing_evidence=remaining_missing_evidence,
    )
    candidate_status_summary = _candidate_risk_rule_evidence_status_summary(
        candidate_summaries
    )
    return {
        "shared_risk_rule_status_version": _SHARED_RISK_RULE_STATUS_VERSION,
        "shared_risk_rule_status": "ready",
        "shared_risk_rule_status_mode": "offline_shared_risk_rule_status_only",
        "deterministic_scope": "shared_candidate_risk_rule_status",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "source_queue_item_id": source_queue_item_id,
        "source_action_id": str(
            source_item.get("action_id", f"execute_{source_queue_item_id}")
        ),
        "source_gap_id": source_gap_id,
        "source_candidate_family_id": source_candidate_family_id,
        "source_candidate_family": str(
            source_item.get(
                "candidate_family",
                _SHARED_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY,
            )
        ),
        "source_gap_status": str(source_item.get("gap_status", "blocked")),
        "source_gap_group_id": str(
            source_item.get("gap_group_id", "strategy_definition_gaps")
        ),
        "source_gap_group_label": str(
            source_item.get("gap_group_label", "Strategy definition gaps")
        ),
        "source_closure_action": str(
            source_item.get("closure_action", "close_strategy_definition_gaps")
        ),
        "source_closure_objective": str(
            source_item.get(
                "closure_objective",
                (
                    "Create shared_risk_rule_status.jsonl using deterministic "
                    "offline packet evidence."
                ),
            )
        ),
        "source_expected_evidence_artifact": str(
            source_item.get(
                "expected_evidence_artifact",
                _SHARED_RISK_RULE_STATUS_FILENAME,
            )
        ),
        "candidate_family_count": len(candidate_summaries),
        "shared_scope_count": len(shared_risk_rule_gaps),
        "shared_risk_rule_status_item": status_item,
        "shared_risk_rule_gaps": shared_risk_rule_gaps,
        "candidate_risk_rule_summaries": candidate_summaries,
        "explicit_shared_risk_rule_evidence": explicit_evidence,
        "position_sizing_evidence": position_sizing_evidence,
        "stop_or_exit_evidence": stop_or_exit_evidence,
        "drawdown_or_exposure_control_evidence": (
            drawdown_or_exposure_control_evidence
        ),
        "portfolio_or_risk_cap_evidence": portfolio_or_risk_cap_evidence,
        "materialized_shared_risk_specification": materialized_specification,
        "remaining_missing_shared_risk_evidence": remaining_missing_evidence,
        "target_shared_risk_readiness": readiness,
        "target_shared_risk_status": {
            "status": evidence_status,
            "shared_status": str(status_item.get("status", "missing")),
            "shared_gap_status": str(risk_gap.get("status", "missing")),
            "materialization_status": str(
                materialized_specification["materialization_status"]
            ),
            "research_ready": readiness["research_ready"],
            "evidence_ready": readiness["evidence_ready"],
            "still_blocked": readiness["still_blocked"],
        },
        "highest_priority_remaining_gaps": highest_priority_remaining_gaps,
        "evidence_status_summary": {
            **candidate_status_summary,
            "shared_scope_status": evidence_status,
            "shared_scope_blocked": evidence_status == "blocked",
            "shared_missing_evidence_explicit": bool(remaining_missing_evidence),
            "shared_evidence_status_breakdown": evidence_breakdown,
        },
        "shared_risk_rule_acceptance_criteria": [
            "shared_risk_rule_status.jsonl exists as one deterministic JSONL record",
            (
                "source_queue_item_id="
                f"{_SHARED_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID}"
            ),
            "source_candidate_family_id=shared",
            "source_gap_id=risk_rule_status",
            "explicit shared risk-rule evidence is recorded without inventing rules",
            "position sizing evidence is separated from stop, drawdown, exposure, and portfolio-cap evidence",
            "materialized shared risk specification remains status-only when explicit rules are missing",
            "shared readiness distinguishes research-ready, evidence-ready, blocked, and not-ready states",
            (
                "selected_next_safe_action="
                f"{_SHARED_RISK_RULE_STATUS_NEXT_ACTION_ID}"
            ),
            "broker_state_mode=broker_state_not_observed",
            "paper_submit_authorized=false",
            "daniel_action_required_now=false",
            "profit_claim=none",
            "safety_scope=offline_only",
        ],
        "next_shared_risk_rule_closure_actions": next_actions,
        "selected_next_safe_action": selected_next_action,
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "daniel_action_required_now": False,
        "profit_claim": "none",
        "safety_scope": "offline_only",
        "safety_labels": list(_REQUIRED_LABELS),
    }


def _default_shared_risk_rule_status_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    status = _build_shared_risk_rule_status({}, artifact_paths)
    return {
        "shared_risk_rule_status_path": str(
            artifact_paths["shared_risk_rule_status"]
        ),
        "shared_risk_rule_status": status,
    }


def _shared_risk_rule_status_record(
    payload: Mapping[str, Any],
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    status = payload.get("shared_risk_rule_status")
    if isinstance(status, Mapping):
        return dict(status)
    return _build_shared_risk_rule_status(payload, artifact_paths)


def _apply_shared_risk_rule_status(
    payload: dict[str, Any],
    output_root: Path,
) -> None:
    artifact_paths = _artifact_paths(output_root)
    status = _build_shared_risk_rule_status(payload, artifact_paths)
    payload["shared_risk_rule_status_path"] = str(
        artifact_paths["shared_risk_rule_status"]
    )
    payload["shared_risk_rule_status"] = status
    dashboard = payload.get("executive_dashboard")
    if isinstance(dashboard, dict):
        dashboard["shared_risk_rule_status_path"] = payload[
            "shared_risk_rule_status_path"
        ]
        dashboard["shared_risk_rule_status"] = dict(status)


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
    prioritization = _build_research_board_prioritization({}, artifact_paths)
    scaffold = _build_strategy_comparison_scaffold({}, artifact_paths)
    template = _build_candidate_strategy_evidence_template({}, artifact_paths)
    requirements = _build_candidate_evidence_requirements({}, artifact_paths)
    collection_plan = _build_candidate_evidence_collection_plan({}, artifact_paths)
    collection_status = _build_candidate_evidence_collection_status(
        {},
        artifact_paths,
    )
    gap_summary = _build_candidate_evidence_gap_summary({}, artifact_paths)
    gap_closure_queue = _build_candidate_gap_closure_queue({}, artifact_paths)
    risk_rule_status = _build_candidate_risk_rule_status({}, artifact_paths)
    signal_rule_status = _build_candidate_signal_rule_status({}, artifact_paths)
    shared_risk_rule_status = _build_shared_risk_rule_status({}, artifact_paths)
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
            "research_board_prioritization_path": str(
                artifact_paths["research_board_prioritization"]
            ),
            "research_board_prioritization": dict(prioritization),
            "strategy_comparison_scaffold_path": str(
                artifact_paths["strategy_comparison_scaffold"]
            ),
            "strategy_comparison_scaffold": dict(scaffold),
            "candidate_strategy_evidence_template_path": str(
                artifact_paths["candidate_strategy_evidence_template"]
            ),
            "candidate_strategy_evidence_template": dict(template),
            "candidate_evidence_requirements_path": str(
                artifact_paths["candidate_evidence_requirements"]
            ),
            "candidate_evidence_requirements": dict(requirements),
            "candidate_evidence_collection_plan_path": str(
                artifact_paths["candidate_evidence_collection_plan"]
            ),
            "candidate_evidence_collection_plan": dict(collection_plan),
            "candidate_evidence_collection_status_path": str(
                artifact_paths["candidate_evidence_collection_status"]
            ),
            "candidate_evidence_collection_status": dict(collection_status),
            "candidate_evidence_gap_summary_path": str(
                artifact_paths["candidate_evidence_gap_summary"]
            ),
            "candidate_evidence_gap_summary": dict(gap_summary),
            "candidate_gap_closure_queue_path": str(
                artifact_paths["candidate_gap_closure_queue"]
            ),
            "candidate_gap_closure_queue": dict(gap_closure_queue),
            "candidate_risk_rule_status_path": str(
                artifact_paths["candidate_risk_rule_status"]
            ),
            "candidate_risk_rule_status": dict(risk_rule_status),
            "candidate_signal_rule_status_path": str(
                artifact_paths["candidate_signal_rule_status"]
            ),
            "candidate_signal_rule_status": dict(signal_rule_status),
            "shared_risk_rule_status_path": str(
                artifact_paths["shared_risk_rule_status"]
            ),
            "shared_risk_rule_status": dict(shared_risk_rule_status),
            "source_state": {},
        }
    }


def _default_work_order_export_fields(
    artifact_paths: Mapping[str, str],
) -> dict[str, Any]:
    output_root = _artifact_output_root(artifact_paths["baseline_evidence_metrics"])
    readiness = _build_paper_observation_readiness({}, artifact_paths)
    prioritization = _build_research_board_prioritization({}, artifact_paths)
    scaffold = _build_strategy_comparison_scaffold({}, artifact_paths)
    template = _build_candidate_strategy_evidence_template({}, artifact_paths)
    requirements = _build_candidate_evidence_requirements({}, artifact_paths)
    collection_plan = _build_candidate_evidence_collection_plan({}, artifact_paths)
    collection_status = _build_candidate_evidence_collection_status(
        {},
        artifact_paths,
    )
    gap_summary = _build_candidate_evidence_gap_summary({}, artifact_paths)
    gap_closure_queue = _build_candidate_gap_closure_queue({}, artifact_paths)
    risk_rule_status = _build_candidate_risk_rule_status({}, artifact_paths)
    signal_rule_status = _build_candidate_signal_rule_status({}, artifact_paths)
    shared_risk_rule_status = _build_shared_risk_rule_status({}, artifact_paths)
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
            "strategy_comparison_scaffold_path": str(
                artifact_paths["strategy_comparison_scaffold"]
            ),
            "strategy_comparison_scaffold": dict(scaffold),
            "strategy_comparison_scaffold_status": str(
                scaffold["scaffold_status"]
            ),
            "candidate_strategy_evidence_template_path": str(
                artifact_paths["candidate_strategy_evidence_template"]
            ),
            "candidate_strategy_evidence_template": dict(template),
            "candidate_strategy_evidence_template_status": str(
                template["template_status"]
            ),
            "candidate_evidence_requirements_path": str(
                artifact_paths["candidate_evidence_requirements"]
            ),
            "candidate_evidence_requirements": dict(requirements),
            "candidate_evidence_requirements_status": str(
                requirements["requirements_status"]
            ),
            "candidate_evidence_collection_plan_path": str(
                artifact_paths["candidate_evidence_collection_plan"]
            ),
            "candidate_evidence_collection_plan": dict(collection_plan),
            "candidate_evidence_collection_plan_status": str(
                collection_plan["collection_plan_status"]
            ),
            "candidate_evidence_collection_status_path": str(
                artifact_paths["candidate_evidence_collection_status"]
            ),
            "candidate_evidence_collection_status": dict(collection_status),
            "candidate_evidence_collection_status_status": str(
                collection_status["collection_status"]
            ),
            "candidate_evidence_gap_summary_path": str(
                artifact_paths["candidate_evidence_gap_summary"]
            ),
            "candidate_evidence_gap_summary": dict(gap_summary),
            "candidate_evidence_gap_summary_status": str(
                gap_summary["gap_summary_status"]
            ),
            "candidate_gap_closure_queue_path": str(
                artifact_paths["candidate_gap_closure_queue"]
            ),
            "candidate_gap_closure_queue": dict(gap_closure_queue),
            "candidate_gap_closure_queue_status": str(
                gap_closure_queue["queue_status"]
            ),
            "candidate_gap_closure_queue_selected_item_id": str(
                gap_closure_queue["selected_queue_item_id"]
            ),
            "candidate_gap_closure_queue_selected_next_safe_action": str(
                gap_closure_queue["selected_next_safe_action"]
            ),
            "candidate_risk_rule_status_path": str(
                artifact_paths["candidate_risk_rule_status"]
            ),
            "candidate_risk_rule_status": dict(risk_rule_status),
            "candidate_risk_rule_status_status": str(
                risk_rule_status["risk_rule_status"]
            ),
            "candidate_risk_rule_status_selected_next_safe_action": str(
                risk_rule_status["selected_next_safe_action"]
            ),
            "candidate_signal_rule_status_path": str(
                artifact_paths["candidate_signal_rule_status"]
            ),
            "candidate_signal_rule_status": dict(signal_rule_status),
            "candidate_signal_rule_status_status": str(
                signal_rule_status["signal_rule_status"]
            ),
            "candidate_signal_rule_status_selected_next_safe_action": str(
                signal_rule_status["selected_next_safe_action"]
            ),
            "shared_risk_rule_status_path": str(
                artifact_paths["shared_risk_rule_status"]
            ),
            "shared_risk_rule_status": dict(shared_risk_rule_status),
            "shared_risk_rule_status_status": str(
                shared_risk_rule_status["shared_risk_rule_status"]
            ),
            "shared_risk_rule_status_selected_next_safe_action": str(
                shared_risk_rule_status["selected_next_safe_action"]
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

    shared_risk_rule_status = payload.get("shared_risk_rule_status")
    if (
        isinstance(shared_risk_rule_status, Mapping)
        and shared_risk_rule_status.get("shared_risk_rule_status") == "ready"
    ):
        selected_action = str(
            shared_risk_rule_status.get("selected_next_safe_action", "")
        )
        if selected_action and not _selector_contains_forbidden_action(selected_action):
            return _selector_result(
                artifact_paths=artifact_paths,
                source_state=source_state,
                status="shared_risk_rule_status_next_action_selected",
                priority="P2",
                selected_next_action_id=selected_action,
                selected_next_action_type="candidate_gap_closure_queue_item",
                selected_work_order="codex_work_order",
                selected_owner="Codex",
                rationale=(
                    "shared_risk_rule_status materialized the source queue item, "
                    "so the next deterministic offline queue item is selected."
                ),
                reason_codes=[
                    "quality_gate_not_failed",
                    "shared_risk_rule_status_ready",
                    str(
                        shared_risk_rule_status.get(
                            "source_queue_item_id",
                            _SHARED_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
                        )
                    ),
                    str(
                        shared_risk_rule_status.get(
                            "source_gap_id",
                            "risk_rule_status",
                        )
                    ),
                ],
                blocks_offline_build=False,
                requires_daniel=False,
                hard_gate_required=False,
                selected_research_candidate=None,
            )

    signal_rule_status = payload.get("candidate_signal_rule_status")
    if (
        isinstance(signal_rule_status, Mapping)
        and signal_rule_status.get("signal_rule_status") == "ready"
    ):
        selected_action = str(signal_rule_status.get("selected_next_safe_action", ""))
        if selected_action and not _selector_contains_forbidden_action(selected_action):
            return _selector_result(
                artifact_paths=artifact_paths,
                source_state=source_state,
                status="candidate_signal_rule_status_next_action_selected",
                priority="P2",
                selected_next_action_id=selected_action,
                selected_next_action_type="candidate_gap_closure_queue_item",
                selected_work_order="codex_work_order",
                selected_owner="Codex",
                rationale=(
                    "candidate_signal_rule_status materialized the source queue "
                    "item, so the next deterministic offline queue item is "
                    "selected."
                ),
                reason_codes=[
                    "quality_gate_not_failed",
                    "candidate_signal_rule_status_ready",
                    str(
                        signal_rule_status.get(
                            "source_queue_item_id",
                            _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
                        )
                    ),
                    str(
                        signal_rule_status.get(
                            "source_gap_id",
                            "candidate_signal_rule_status",
                        )
                    ),
                ],
                blocks_offline_build=False,
                requires_daniel=False,
                hard_gate_required=False,
                selected_research_candidate=None,
            )

    risk_rule_status = payload.get("candidate_risk_rule_status")
    if (
        isinstance(risk_rule_status, Mapping)
        and risk_rule_status.get("risk_rule_status") == "ready"
    ):
        selected_action = str(risk_rule_status.get("selected_next_safe_action", ""))
        if selected_action and not _selector_contains_forbidden_action(selected_action):
            return _selector_result(
                artifact_paths=artifact_paths,
                source_state=source_state,
                status="candidate_risk_rule_status_next_action_selected",
                priority="P2",
                selected_next_action_id=selected_action,
                selected_next_action_type="candidate_gap_closure_queue_item",
                selected_work_order="codex_work_order",
                selected_owner="Codex",
                rationale=(
                    "candidate_risk_rule_status materialized the source queue "
                    "item, so the next deterministic offline queue item is "
                    "selected."
                ),
                reason_codes=[
                    "quality_gate_not_failed",
                    "candidate_risk_rule_status_ready",
                    str(
                        risk_rule_status.get(
                            "source_queue_item_id",
                            _CANDIDATE_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
                        )
                    ),
                    str(
                        risk_rule_status.get(
                            "source_gap_id",
                            "candidate_risk_rule_status",
                        )
                    ),
                ],
                blocks_offline_build=False,
                requires_daniel=False,
                hard_gate_required=False,
                selected_research_candidate=None,
            )

    gap_closure_queue = payload.get("candidate_gap_closure_queue")
    if isinstance(gap_closure_queue, Mapping):
        queue_items = gap_closure_queue.get("queue_items")
        if (
            gap_closure_queue.get("queue_status") == "ready"
            and isinstance(queue_items, list)
            and queue_items
        ):
            selected_item = queue_items[0]
            if isinstance(selected_item, Mapping):
                return _selector_result(
                    artifact_paths=artifact_paths,
                    source_state=source_state,
                    status="candidate_gap_closure_queue_item_selected",
                    priority=str(selected_item.get("action_priority", "P2")),
                    selected_next_action_id=str(
                        gap_closure_queue.get(
                            "selected_next_safe_action",
                            selected_item.get("action_id"),
                        )
                    ),
                    selected_next_action_type="candidate_gap_closure_queue_item",
                    selected_work_order=str(
                        gap_closure_queue.get("selected_work_order", "codex_work_order")
                    ),
                    selected_owner=str(gap_closure_queue.get("selected_owner", "Codex")),
                    rationale=str(
                        gap_closure_queue.get(
                            "why_selected",
                            "Safe offline candidate gap closure queue item selected.",
                        )
                    ),
                    reason_codes=[
                        "quality_gate_not_failed",
                        "candidate_gap_closure_queue_ready",
                        str(selected_item.get("queue_item_id", "queue_item_missing")),
                        str(selected_item.get("gap_group_id", "gap_group_missing")),
                    ],
                    blocks_offline_build=False,
                    requires_daniel=bool(
                        selected_item.get("daniel_action_required", False)
                    ),
                    hard_gate_required=False,
                    selected_research_candidate=None,
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
        "strategy_comparison_scaffold": dict(
            payload.get("strategy_comparison_scaffold", {})
            if isinstance(payload.get("strategy_comparison_scaffold"), Mapping)
            else {}
        ),
        "candidate_strategy_evidence_template": dict(
            payload.get("candidate_strategy_evidence_template", {})
            if isinstance(payload.get("candidate_strategy_evidence_template"), Mapping)
            else {}
        ),
        "candidate_evidence_requirements": dict(
            payload.get("candidate_evidence_requirements", {})
            if isinstance(payload.get("candidate_evidence_requirements"), Mapping)
            else {}
        ),
        "candidate_evidence_collection_plan": dict(
            payload.get("candidate_evidence_collection_plan", {})
            if isinstance(payload.get("candidate_evidence_collection_plan"), Mapping)
            else {}
        ),
        "candidate_evidence_collection_status": dict(
            payload.get("candidate_evidence_collection_status", {})
            if isinstance(
                payload.get("candidate_evidence_collection_status"),
                Mapping,
            )
            else {}
        ),
        "candidate_evidence_gap_summary": dict(
            payload.get("candidate_evidence_gap_summary", {})
            if isinstance(
                payload.get("candidate_evidence_gap_summary"),
                Mapping,
            )
            else {}
        ),
        "candidate_gap_closure_queue": dict(
            payload.get("candidate_gap_closure_queue", {})
            if isinstance(
                payload.get("candidate_gap_closure_queue"),
                Mapping,
            )
            else {}
        ),
        "candidate_risk_rule_status": dict(
            payload.get("candidate_risk_rule_status", {})
            if isinstance(
                payload.get("candidate_risk_rule_status"),
                Mapping,
            )
            else {}
        ),
        "candidate_signal_rule_status": dict(
            payload.get("candidate_signal_rule_status", {})
            if isinstance(
                payload.get("candidate_signal_rule_status"),
                Mapping,
            )
            else {}
        ),
        "shared_risk_rule_status": dict(
            payload.get("shared_risk_rule_status", {})
            if isinstance(
                payload.get("shared_risk_rule_status"),
                Mapping,
            )
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
        "strategy_comparison_scaffold_path": str(
            artifact_paths["strategy_comparison_scaffold"]
        ),
        "strategy_comparison_scaffold": dict(
            source_state.get("strategy_comparison_scaffold", {})
            if isinstance(source_state.get("strategy_comparison_scaffold"), Mapping)
            else {}
        ),
        "candidate_strategy_evidence_template_path": str(
            artifact_paths["candidate_strategy_evidence_template"]
        ),
        "candidate_strategy_evidence_template": dict(
            source_state.get("candidate_strategy_evidence_template", {})
            if isinstance(
                source_state.get("candidate_strategy_evidence_template"),
                Mapping,
            )
            else {}
        ),
        "candidate_evidence_requirements_path": str(
            artifact_paths["candidate_evidence_requirements"]
        ),
        "candidate_evidence_requirements": dict(
            source_state.get("candidate_evidence_requirements", {})
            if isinstance(source_state.get("candidate_evidence_requirements"), Mapping)
            else {}
        ),
        "candidate_evidence_collection_plan_path": str(
            artifact_paths["candidate_evidence_collection_plan"]
        ),
        "candidate_evidence_collection_plan": dict(
            source_state.get("candidate_evidence_collection_plan", {})
            if isinstance(
                source_state.get("candidate_evidence_collection_plan"),
                Mapping,
            )
            else {}
        ),
        "candidate_evidence_collection_status_path": str(
            artifact_paths["candidate_evidence_collection_status"]
        ),
        "candidate_evidence_collection_status": dict(
            source_state.get("candidate_evidence_collection_status", {})
            if isinstance(
                source_state.get("candidate_evidence_collection_status"),
                Mapping,
            )
            else {}
        ),
        "candidate_evidence_gap_summary_path": str(
            artifact_paths["candidate_evidence_gap_summary"]
        ),
        "candidate_evidence_gap_summary": dict(
            source_state.get("candidate_evidence_gap_summary", {})
            if isinstance(
                source_state.get("candidate_evidence_gap_summary"),
                Mapping,
            )
            else {}
        ),
        "candidate_gap_closure_queue_path": str(
            artifact_paths["candidate_gap_closure_queue"]
        ),
        "candidate_gap_closure_queue": dict(
            source_state.get("candidate_gap_closure_queue", {})
            if isinstance(
                source_state.get("candidate_gap_closure_queue"),
                Mapping,
            )
            else {}
        ),
        "candidate_risk_rule_status_path": str(
            artifact_paths["candidate_risk_rule_status"]
        ),
        "candidate_risk_rule_status": dict(
            source_state.get("candidate_risk_rule_status", {})
            if isinstance(
                source_state.get("candidate_risk_rule_status"),
                Mapping,
            )
            else {}
        ),
        "candidate_signal_rule_status_path": str(
            artifact_paths["candidate_signal_rule_status"]
        ),
        "candidate_signal_rule_status": dict(
            source_state.get("candidate_signal_rule_status", {})
            if isinstance(
                source_state.get("candidate_signal_rule_status"),
                Mapping,
            )
            else {}
        ),
        "shared_risk_rule_status_path": str(
            artifact_paths["shared_risk_rule_status"]
        ),
        "shared_risk_rule_status": dict(
            source_state.get("shared_risk_rule_status", {})
            if isinstance(
                source_state.get("shared_risk_rule_status"),
                Mapping,
            )
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
    scaffold = _strategy_comparison_scaffold_record(payload, artifact_paths)
    template = _candidate_strategy_evidence_template_record(payload, artifact_paths)
    requirements = _candidate_evidence_requirements_record(payload, artifact_paths)
    collection_plan = _candidate_evidence_collection_plan_record(
        payload,
        artifact_paths,
    )
    collection_status = _candidate_evidence_collection_status_record(
        payload,
        artifact_paths,
    )
    gap_summary = _candidate_evidence_gap_summary_record(
        payload,
        artifact_paths,
    )
    gap_closure_queue = _candidate_gap_closure_queue_record(
        payload,
        artifact_paths,
    )
    risk_rule_status = _candidate_risk_rule_status_record(
        payload,
        artifact_paths,
    )
    signal_rule_status = _candidate_signal_rule_status_record(
        payload,
        artifact_paths,
    )
    shared_risk_rule_status = _shared_risk_rule_status_record(
        payload,
        artifact_paths,
    )
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
        "strategy_comparison_scaffold_path": str(
            artifact_paths["strategy_comparison_scaffold"]
        ),
        "strategy_comparison_scaffold": dict(scaffold),
        "strategy_comparison_scaffold_status": str(
            scaffold.get("scaffold_status", "ready")
        ),
        "candidate_strategy_evidence_template_path": str(
            artifact_paths["candidate_strategy_evidence_template"]
        ),
        "candidate_strategy_evidence_template": dict(template),
        "candidate_strategy_evidence_template_status": str(
            template.get("template_status", "ready")
        ),
        "candidate_evidence_requirements_path": str(
            artifact_paths["candidate_evidence_requirements"]
        ),
        "candidate_evidence_requirements": dict(requirements),
        "candidate_evidence_requirements_status": str(
            requirements.get("requirements_status", "ready")
        ),
        "candidate_evidence_collection_plan_path": str(
            artifact_paths["candidate_evidence_collection_plan"]
        ),
        "candidate_evidence_collection_plan": dict(collection_plan),
        "candidate_evidence_collection_plan_status": str(
            collection_plan.get("collection_plan_status", "ready")
        ),
        "candidate_evidence_collection_status_path": str(
            artifact_paths["candidate_evidence_collection_status"]
        ),
        "candidate_evidence_collection_status": dict(collection_status),
        "candidate_evidence_collection_status_status": str(
            collection_status.get("collection_status", "ready")
        ),
        "candidate_evidence_gap_summary_path": str(
            artifact_paths["candidate_evidence_gap_summary"]
        ),
        "candidate_evidence_gap_summary": dict(gap_summary),
        "candidate_evidence_gap_summary_status": str(
            gap_summary.get("gap_summary_status", "ready")
        ),
        "candidate_gap_closure_queue_path": str(
            artifact_paths["candidate_gap_closure_queue"]
        ),
        "candidate_gap_closure_queue": dict(gap_closure_queue),
        "candidate_gap_closure_queue_status": str(
            gap_closure_queue.get("queue_status", "ready")
        ),
        "candidate_gap_closure_queue_selected_item_id": str(
            gap_closure_queue.get("selected_queue_item_id", "")
        ),
        "candidate_gap_closure_queue_selected_next_safe_action": str(
            gap_closure_queue.get("selected_next_safe_action", "")
        ),
        "candidate_risk_rule_status_path": str(
            artifact_paths["candidate_risk_rule_status"]
        ),
        "candidate_risk_rule_status": dict(risk_rule_status),
        "candidate_risk_rule_status_status": str(
            risk_rule_status.get("risk_rule_status", "ready")
        ),
        "candidate_risk_rule_status_selected_next_safe_action": str(
            risk_rule_status.get("selected_next_safe_action", "")
        ),
        "candidate_signal_rule_status_path": str(
            artifact_paths["candidate_signal_rule_status"]
        ),
        "candidate_signal_rule_status": dict(signal_rule_status),
        "candidate_signal_rule_status_status": str(
            signal_rule_status.get("signal_rule_status", "ready")
        ),
        "candidate_signal_rule_status_selected_next_safe_action": str(
            signal_rule_status.get("selected_next_safe_action", "")
        ),
        "shared_risk_rule_status_path": str(
            artifact_paths["shared_risk_rule_status"]
        ),
        "shared_risk_rule_status": dict(shared_risk_rule_status),
        "shared_risk_rule_status_status": str(
            shared_risk_rule_status.get("shared_risk_rule_status", "ready")
        ),
        "shared_risk_rule_status_selected_next_safe_action": str(
            shared_risk_rule_status.get("selected_next_safe_action", "")
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
    scaffold_ok, scaffold_summary = _quality_strategy_comparison_scaffold_summary(
        root,
        packet_for_checks,
        manifest if isinstance(manifest, Mapping) else {},
    )
    template_ok, template_summary = (
        _quality_candidate_strategy_evidence_template_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    requirements_ok, requirements_summary = (
        _quality_candidate_evidence_requirements_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    collection_plan_ok, collection_plan_summary = (
        _quality_candidate_evidence_collection_plan_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    collection_status_ok, collection_status_summary = (
        _quality_candidate_evidence_collection_status_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    gap_summary_ok, gap_summary_summary = (
        _quality_candidate_evidence_gap_summary_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    gap_closure_queue_ok, gap_closure_queue_summary = (
        _quality_candidate_gap_closure_queue_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    risk_rule_status_ok, risk_rule_status_summary = (
        _quality_candidate_risk_rule_status_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    signal_rule_status_ok, signal_rule_status_summary = (
        _quality_candidate_signal_rule_status_summary(
            root,
            packet_for_checks,
            manifest if isinstance(manifest, Mapping) else {},
        )
    )
    shared_risk_rule_status_ok, shared_risk_rule_status_summary = (
        _quality_shared_risk_rule_status_summary(
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
            "strategy_comparison_scaffold_generated",
            scaffold_ok,
            scaffold_summary,
        ),
        _quality_check(
            "candidate_strategy_evidence_template_generated",
            template_ok,
            template_summary,
        ),
        _quality_check(
            "candidate_evidence_requirements_generated",
            requirements_ok,
            requirements_summary,
        ),
        _quality_check(
            "candidate_evidence_collection_plan_generated",
            collection_plan_ok,
            collection_plan_summary,
        ),
        _quality_check(
            "candidate_evidence_collection_status_generated",
            collection_status_ok,
            collection_status_summary,
        ),
        _quality_check(
            "candidate_evidence_gap_summary_generated",
            gap_summary_ok,
            gap_summary_summary,
        ),
        _quality_check(
            "candidate_gap_closure_queue_generated",
            gap_closure_queue_ok,
            gap_closure_queue_summary,
        ),
        _quality_check(
            "candidate_risk_rule_status_generated",
            risk_rule_status_ok,
            risk_rule_status_summary,
        ),
        _quality_check(
            "candidate_signal_rule_status_generated",
            signal_rule_status_ok,
            signal_rule_status_summary,
        ),
        _quality_check(
            "shared_risk_rule_status_generated",
            shared_risk_rule_status_ok,
            shared_risk_rule_status_summary,
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
        "## Candidate Strategy Evidence Template",
        "## Candidate Evidence Requirements",
        "## Candidate Evidence Collection Plan",
        "## Candidate Evidence Collection Status",
        "## Candidate Evidence Gap Summary",
        "## Next Action Selector",
        "## Executive dashboard",
        "Quality Gate",
        "Decision Ledger",
        "Work order exports",
        _RESEARCH_CANDIDATE_QUEUE_FILENAME,
        _BASELINE_HEALTH_EVALUATION_FILENAME,
        _BASELINE_EVIDENCE_METRICS_FILENAME,
        _PAPER_OBSERVATION_READINESS_FILENAME,
        _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME,
        _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME,
        _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME,
        _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME,
        _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME,
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


def _quality_strategy_comparison_scaffold_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_strategy_comparison_scaffold_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    scaffold = packet["strategy_comparison_scaffold"]
    assert isinstance(scaffold, Mapping)
    artifact_path = output_root / _STRATEGY_COMPARISON_SCAFFOLD_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_STRATEGY_COMPARISON_SCAFFOLD_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_STRATEGY_COMPARISON_SCAFFOLD_FILENAME} must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_STRATEGY_COMPARISON_SCAFFOLD_FILENAME} is not JSON"
    if artifact_record != scaffold:
        return False, "strategy comparison scaffold artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("strategy_comparison_scaffold")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index strategy_comparison_scaffold"
    if not str(indexed.get("path", "")).endswith(
        _STRATEGY_COMPARISON_SCAFFOLD_FILENAME
    ):
        return False, "manifest scaffold artifact path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _STRATEGY_COMPARISON_SCAFFOLD_FILENAME not in text:
            return False, f"{text_name} does not reference scaffold artifact"
        if "Strategy Comparison Scaffold" not in text:
            return False, f"{text_name} does not include scaffold section"
    return True, (
        "strategy comparison scaffold generated; scaffold_status=ready; "
        "comparison_mode=offline_research_scaffold_only; "
        "selected_next_safe_action=build_candidate_strategy_evidence_template"
    )


def _quality_candidate_strategy_evidence_template_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_candidate_strategy_evidence_template_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    template = packet["candidate_strategy_evidence_template"]
    assert isinstance(template, Mapping)
    artifact_path = output_root / _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME} must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, (
            f"{_CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME} is not JSON"
        )
    if artifact_record != template:
        return False, "candidate strategy evidence template artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("candidate_strategy_evidence_template")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index candidate_strategy_evidence_template"
    if not str(indexed.get("path", "")).endswith(
        _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME
    ):
        return False, "manifest candidate template artifact path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME not in text:
            return False, f"{text_name} does not reference candidate template artifact"
        if "Candidate Strategy Evidence Template" not in text:
            return False, f"{text_name} does not include candidate template section"
    return True, (
        "candidate strategy evidence template generated; template_status=ready; "
        "evidence_mode=offline_strategy_evidence_template_only; "
        "selected_next_safe_action=materialize_candidate_evidence_requirements"
    )


def _quality_candidate_evidence_requirements_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_candidate_evidence_requirements_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    requirements = packet["candidate_evidence_requirements"]
    assert isinstance(requirements, Mapping)
    artifact_path = output_root / _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME} must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME} is not JSON"
    if artifact_record != requirements:
        return False, "candidate evidence requirements artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("candidate_evidence_requirements")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index candidate_evidence_requirements"
    if not str(indexed.get("path", "")).endswith(
        _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME
    ):
        return False, "manifest candidate requirements artifact path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME not in text:
            return False, (
                f"{text_name} does not reference candidate requirements artifact"
            )
        if "Candidate Evidence Requirements" not in text:
            return False, f"{text_name} does not include candidate requirements section"
    return True, (
        "candidate evidence requirements generated; requirements_status=ready; "
        "requirements_mode=offline_candidate_evidence_requirements_only; "
        "selected_next_safe_action=build_candidate_evidence_collection_plan"
    )


def _quality_candidate_evidence_collection_plan_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_candidate_evidence_collection_plan_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    collection_plan = packet["candidate_evidence_collection_plan"]
    assert isinstance(collection_plan, Mapping)
    artifact_path = output_root / _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME} must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME} is not JSON"
    if artifact_record != collection_plan:
        return False, "candidate evidence collection plan artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("candidate_evidence_collection_plan")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index candidate_evidence_collection_plan"
    if not str(indexed.get("path", "")).endswith(
        _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME
    ):
        return False, "manifest candidate collection plan artifact path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME not in text:
            return False, (
                f"{text_name} does not reference candidate collection plan artifact"
            )
        if "Candidate Evidence Collection Plan" not in text:
            return False, (
                f"{text_name} does not include candidate collection plan section"
            )
    return True, (
        "candidate evidence collection plan generated; "
        "collection_plan_status=ready; "
        "collection_plan_mode=offline_candidate_evidence_collection_plan_only; "
        "selected_next_safe_action=build_candidate_evidence_collection_status"
    )


def _quality_candidate_evidence_collection_status_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_candidate_evidence_collection_status_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    collection_status = packet["candidate_evidence_collection_status"]
    assert isinstance(collection_status, Mapping)
    artifact_path = output_root / _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME} "
            "must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME} is not JSON"
    if artifact_record != collection_status:
        return (
            False,
            "candidate evidence collection status artifact does not match packet",
        )
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("candidate_evidence_collection_status")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index candidate_evidence_collection_status"
    if not str(indexed.get("path", "")).endswith(
        _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME
    ):
        return False, "manifest candidate collection status artifact path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME not in text:
            return False, (
                f"{text_name} does not reference candidate collection status artifact"
            )
        if "Candidate Evidence Collection Status" not in text:
            return False, (
                f"{text_name} does not include candidate collection status section"
            )
    return True, (
        "candidate evidence collection status generated; "
        "collection_status=ready; "
        "collection_status_mode=offline_candidate_evidence_collection_status_only; "
        "selected_next_safe_action=build_candidate_evidence_gap_summary"
    )


def _quality_candidate_evidence_gap_summary_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_candidate_evidence_gap_summary_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    gap_summary = packet["candidate_evidence_gap_summary"]
    assert isinstance(gap_summary, Mapping)
    artifact_path = output_root / _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME} "
            "must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME} is not JSON"
    if artifact_record != gap_summary:
        return False, "candidate evidence gap summary artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("candidate_evidence_gap_summary")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index candidate_evidence_gap_summary"
    if not str(indexed.get("path", "")).endswith(
        _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME
    ):
        return False, "manifest candidate gap summary artifact path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME not in text:
            return False, (
                f"{text_name} does not reference candidate gap summary artifact"
            )
        if "Candidate Evidence Gap Summary" not in text:
            return False, (
                f"{text_name} does not include candidate gap summary section"
            )
    return True, (
        "candidate evidence gap summary generated; "
        "gap_summary_status=ready; "
        "gap_summary_mode=offline_candidate_evidence_gap_summary_only; "
        "selected_next_safe_action=build_candidate_gap_closure_queue"
    )


def _quality_candidate_gap_closure_queue_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_candidate_gap_closure_queue_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    queue = packet["candidate_gap_closure_queue"]
    assert isinstance(queue, Mapping)
    artifact_path = output_root / _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME} "
            "must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME} is not JSON"
    if artifact_record != queue:
        return False, "candidate gap closure queue artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("candidate_gap_closure_queue")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index candidate_gap_closure_queue"
    if not str(indexed.get("path", "")).endswith(
        _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME
    ):
        return False, "manifest candidate gap closure queue path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME not in text:
            return False, (
                f"{text_name} does not reference candidate gap closure queue"
            )
        if "Candidate Gap Closure Queue" not in text:
            return False, (
                f"{text_name} does not include candidate gap closure queue section"
            )
    return True, (
        "candidate gap closure queue generated; "
        "queue_status=ready; "
        "queue_mode=offline_candidate_gap_closure_queue_only; "
        f"selected_next_safe_action={queue['selected_next_safe_action']}"
    )


def _quality_candidate_risk_rule_status_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_candidate_risk_rule_status_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    status = packet["candidate_risk_rule_status"]
    assert isinstance(status, Mapping)
    artifact_path = output_root / _CANDIDATE_RISK_RULE_STATUS_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_CANDIDATE_RISK_RULE_STATUS_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_CANDIDATE_RISK_RULE_STATUS_FILENAME} must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_CANDIDATE_RISK_RULE_STATUS_FILENAME} is not JSON"
    if artifact_record != status:
        return False, "candidate risk rule status artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("candidate_risk_rule_status")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index candidate_risk_rule_status"
    if not str(indexed.get("path", "")).endswith(
        _CANDIDATE_RISK_RULE_STATUS_FILENAME
    ):
        return False, "manifest candidate risk rule status path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _CANDIDATE_RISK_RULE_STATUS_FILENAME not in text:
            return False, (
                f"{text_name} does not reference candidate risk rule status"
            )
        if "Candidate Risk Rule Status" not in text:
            return False, (
                f"{text_name} does not include candidate risk rule status section"
            )
    return True, (
        "candidate risk rule status generated; "
        "risk_rule_status=ready; "
        "risk_rule_status_mode=offline_candidate_risk_rule_status_only; "
        f"source_queue_item_id={status['source_queue_item_id']}; "
        f"source_candidate_family_id={status['source_candidate_family_id']}; "
        f"selected_next_safe_action={status['selected_next_safe_action']}"
    )


def _quality_candidate_signal_rule_status_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_candidate_signal_rule_status_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    status = packet["candidate_signal_rule_status"]
    assert isinstance(status, Mapping)
    artifact_path = output_root / _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_CANDIDATE_SIGNAL_RULE_STATUS_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_CANDIDATE_SIGNAL_RULE_STATUS_FILENAME} must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_CANDIDATE_SIGNAL_RULE_STATUS_FILENAME} is not JSON"
    if artifact_record != status:
        return False, "candidate signal rule status artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("candidate_signal_rule_status")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index candidate_signal_rule_status"
    if not str(indexed.get("path", "")).endswith(
        _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME
    ):
        return False, "manifest candidate signal rule status path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME not in text:
            return False, (
                f"{text_name} does not reference candidate signal rule status"
            )
        if "Candidate Signal Rule Status" not in text:
            return False, (
                f"{text_name} does not include candidate signal rule status section"
            )
    return True, (
        "candidate signal rule status generated; "
        "signal_rule_status=ready; "
        "signal_rule_status_mode=offline_candidate_signal_rule_status_only; "
        f"source_queue_item_id={status['source_queue_item_id']}; "
        f"source_candidate_family_id={status['source_candidate_family_id']}; "
        f"selected_next_safe_action={status['selected_next_safe_action']}"
    )


def _quality_shared_risk_rule_status_summary(
    output_root: Path,
    packet: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> tuple[bool, str]:
    missing = _missing_shared_risk_rule_status_fields("", packet)
    if missing:
        return False, _quality_missing_summary(missing)
    status = packet["shared_risk_rule_status"]
    assert isinstance(status, Mapping)
    artifact_path = output_root / _SHARED_RISK_RULE_STATUS_FILENAME
    if not artifact_path.exists() or not artifact_path.is_file():
        return False, f"{_SHARED_RISK_RULE_STATUS_FILENAME} missing"
    artifact_lines = [
        line.strip()
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(artifact_lines) != 1:
        return False, (
            f"{_SHARED_RISK_RULE_STATUS_FILENAME} must be one JSONL record"
        )
    try:
        artifact_record = json.loads(artifact_lines[0])
    except json.JSONDecodeError:
        return False, f"{_SHARED_RISK_RULE_STATUS_FILENAME} is not JSON"
    if artifact_record != status:
        return False, "shared risk rule status artifact does not match packet"
    indexed_artifacts = manifest.get("indexed_artifacts")
    if not isinstance(indexed_artifacts, Mapping):
        return False, "manifest indexed_artifacts missing"
    indexed = indexed_artifacts.get("shared_risk_rule_status")
    if not isinstance(indexed, Mapping):
        return False, "manifest does not index shared_risk_rule_status"
    if not str(indexed.get("path", "")).endswith(_SHARED_RISK_RULE_STATUS_FILENAME):
        return False, "manifest shared risk rule status path is not explicit"
    brief_text = _read_text_or_empty(output_root / _BRIEF_FILENAME)
    review_handoff_text = _read_text_or_empty(output_root / _REVIEW_HANDOFF_FILENAME)
    for text_name, text in (
        ("operating brief", brief_text),
        ("review handoff", review_handoff_text),
    ):
        if _SHARED_RISK_RULE_STATUS_FILENAME not in text:
            return False, f"{text_name} does not reference shared risk rule status"
        if "Shared Risk Rule Status" not in text:
            return False, (
                f"{text_name} does not include shared risk rule status section"
            )
    return True, (
        "shared risk rule status generated; "
        "shared_risk_rule_status=ready; "
        "shared_risk_rule_status_mode=offline_shared_risk_rule_status_only; "
        f"source_queue_item_id={status['source_queue_item_id']}; "
        f"source_candidate_family_id={status['source_candidate_family_id']}; "
        f"selected_next_safe_action={status['selected_next_safe_action']}"
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
        _STRATEGY_COMPARISON_SCAFFOLD_FILENAME,
        _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME,
        _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME,
        _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME,
        "Candidate Evidence Collection Plan",
        _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME,
        "Candidate Evidence Collection Status",
        _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME,
        "Candidate Evidence Gap Summary",
        _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME,
        "Candidate Gap Closure Queue",
        _CANDIDATE_RISK_RULE_STATUS_FILENAME,
        "Candidate Risk Rule Status",
        _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME,
        "Candidate Signal Rule Status",
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
            "## Strategy comparison scaffold",
            _STRATEGY_COMPARISON_SCAFFOLD_FILENAME,
            "## Candidate strategy evidence template",
            _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME,
            "## Candidate Evidence Requirements",
            _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME,
            "build_candidate_evidence_collection_plan",
            "## Candidate Evidence Collection Plan",
            _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME,
            "build_candidate_evidence_collection_status",
            "## Candidate Evidence Collection Status",
            _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME,
            "build_candidate_evidence_gap_summary",
            "## Candidate Evidence Gap Summary",
            _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME,
            "build_candidate_gap_closure_queue",
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
    missing.extend(_missing_strategy_comparison_scaffold_fields("", packet))
    missing.extend(_missing_candidate_strategy_evidence_template_fields("", packet))
    missing.extend(_missing_candidate_evidence_requirements_fields("", packet))
    missing.extend(_missing_candidate_evidence_collection_plan_fields("", packet))
    missing.extend(_missing_candidate_evidence_collection_status_fields("", packet))
    missing.extend(_missing_candidate_evidence_gap_summary_fields("", packet))
    missing.extend(_missing_candidate_gap_closure_queue_fields("", packet))
    missing.extend(_missing_candidate_risk_rule_status_fields("", packet))
    missing.extend(_missing_candidate_signal_rule_status_fields("", packet))
    missing.extend(_missing_shared_risk_rule_status_fields("", packet))
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
    missing.extend(_missing_strategy_comparison_scaffold_fields("manifest", manifest))
    missing.extend(
        _missing_candidate_strategy_evidence_template_fields("manifest", manifest)
    )
    missing.extend(_missing_candidate_evidence_requirements_fields("manifest", manifest))
    missing.extend(
        _missing_candidate_evidence_collection_plan_fields("manifest", manifest)
    )
    missing.extend(
        _missing_candidate_evidence_collection_status_fields("manifest", manifest)
    )
    missing.extend(_missing_candidate_evidence_gap_summary_fields("manifest", manifest))
    missing.extend(_missing_candidate_gap_closure_queue_fields("manifest", manifest))
    missing.extend(_missing_candidate_risk_rule_status_fields("manifest", manifest))
    missing.extend(_missing_candidate_signal_rule_status_fields("manifest", manifest))
    missing.extend(_missing_shared_risk_rule_status_fields("manifest", manifest))
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
        "strategy_comparison_scaffold_path",
        "strategy_comparison_scaffold",
        "candidate_strategy_evidence_template_path",
        "candidate_strategy_evidence_template",
        "candidate_evidence_requirements_path",
        "candidate_evidence_requirements",
        "candidate_evidence_collection_plan_path",
        "candidate_evidence_collection_plan",
        "candidate_evidence_collection_status_path",
        "candidate_evidence_collection_status",
        "candidate_evidence_gap_summary_path",
        "candidate_evidence_gap_summary",
        "candidate_gap_closure_queue_path",
        "candidate_gap_closure_queue",
        "candidate_risk_rule_status_path",
        "candidate_risk_rule_status",
        "candidate_signal_rule_status_path",
        "candidate_signal_rule_status",
        "shared_risk_rule_status_path",
        "shared_risk_rule_status",
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
        isinstance(packet.get("candidate_strategy_evidence_template"), Mapping)
        and isinstance(manifest.get("candidate_strategy_evidence_template"), Mapping)
        and dict(manifest["candidate_strategy_evidence_template"])
        != dict(packet["candidate_strategy_evidence_template"])
    ):
        missing.append(
            "manifest.candidate_strategy_evidence_template.matches_record"
        )

    if (
        isinstance(packet.get("candidate_evidence_collection_status"), Mapping)
        and isinstance(manifest.get("candidate_evidence_collection_status"), Mapping)
        and dict(manifest["candidate_evidence_collection_status"])
        != dict(packet["candidate_evidence_collection_status"])
    ):
        missing.append("manifest.candidate_evidence_collection_status.matches_record")

    if (
        isinstance(packet.get("candidate_evidence_gap_summary"), Mapping)
        and isinstance(manifest.get("candidate_evidence_gap_summary"), Mapping)
        and dict(manifest["candidate_evidence_gap_summary"])
        != dict(packet["candidate_evidence_gap_summary"])
    ):
        missing.append("manifest.candidate_evidence_gap_summary.matches_record")

    if (
        isinstance(packet.get("candidate_gap_closure_queue"), Mapping)
        and isinstance(manifest.get("candidate_gap_closure_queue"), Mapping)
        and dict(manifest["candidate_gap_closure_queue"])
        != dict(packet["candidate_gap_closure_queue"])
    ):
        missing.append("manifest.candidate_gap_closure_queue.matches_record")

    if (
        isinstance(packet.get("candidate_risk_rule_status"), Mapping)
        and isinstance(manifest.get("candidate_risk_rule_status"), Mapping)
        and dict(manifest["candidate_risk_rule_status"])
        != dict(packet["candidate_risk_rule_status"])
    ):
        missing.append("manifest.candidate_risk_rule_status.matches_record")

    if (
        isinstance(packet.get("candidate_signal_rule_status"), Mapping)
        and isinstance(manifest.get("candidate_signal_rule_status"), Mapping)
        and dict(manifest["candidate_signal_rule_status"])
        != dict(packet["candidate_signal_rule_status"])
    ):
        missing.append("manifest.candidate_signal_rule_status.matches_record")

    if (
        isinstance(packet.get("shared_risk_rule_status"), Mapping)
        and isinstance(manifest.get("shared_risk_rule_status"), Mapping)
        and dict(manifest["shared_risk_rule_status"])
        != dict(packet["shared_risk_rule_status"])
    ):
        missing.append("manifest.shared_risk_rule_status.matches_record")

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


def _missing_strategy_comparison_scaffold_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    scaffold = packet.get("strategy_comparison_scaffold")
    if not isinstance(scaffold, Mapping):
        return [f"{field_prefix}strategy_comparison_scaffold"]
    for field_name in _REQUIRED_STRATEGY_COMPARISON_SCAFFOLD_FIELDS:
        if field_name not in scaffold:
            missing.append(f"{field_prefix}strategy_comparison_scaffold.{field_name}")
    if not str(packet.get("strategy_comparison_scaffold_path", "")).endswith(
        _STRATEGY_COMPARISON_SCAFFOLD_FILENAME
    ):
        missing.append(f"{field_prefix}strategy_comparison_scaffold_path")
    expected_values = {
        "scaffold_status": "ready",
        "comparison_mode": "offline_research_scaffold_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "selected_next_safe_action": "build_candidate_strategy_evidence_template",
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "profit_claim": "none",
    }
    for field_name, expected_value in expected_values.items():
        if scaffold.get(field_name) != expected_value:
            missing.append(
                f"{field_prefix}strategy_comparison_scaffold.{field_name}"
            )
    if _selector_contains_forbidden_action(
        str(scaffold.get("selected_next_safe_action", ""))
    ):
        missing.append(
            f"{field_prefix}strategy_comparison_scaffold.selected_next_safe_action.safe"
        )
    for false_field in (
        "paper_submit_authorized",
        "hard_gate_required",
        "requires_daniel",
        "daniel_action_required_now",
    ):
        if scaffold.get(false_field) is not False:
            missing.append(
                f"{field_prefix}strategy_comparison_scaffold.{false_field}.false"
            )
    if not str(scaffold.get("baseline_strategy_label", "")).strip():
        missing.append(
            f"{field_prefix}strategy_comparison_scaffold.baseline_strategy_label"
        )
    candidate_slots = scaffold.get("candidate_strategy_slots")
    if not isinstance(candidate_slots, list) or not candidate_slots:
        missing.append(
            f"{field_prefix}strategy_comparison_scaffold.candidate_strategy_slots"
        )
    else:
        candidate_ids: set[str] = set()
        for index, item in enumerate(candidate_slots):
            item_prefix = (
                f"{field_prefix}strategy_comparison_scaffold."
                f"candidate_strategy_slots[{index}]"
            )
            if not isinstance(item, Mapping):
                missing.append(item_prefix)
                continue
            for field_name in _REQUIRED_STRATEGY_COMPARISON_SLOT_FIELDS:
                if field_name not in item:
                    missing.append(f"{item_prefix}.{field_name}")
            candidate_ids.add(str(item.get("candidate_slot_id", "")))
            if item.get("hard_gate_required") is not False:
                missing.append(f"{item_prefix}.hard_gate_required.false")
            if item.get("safety_scope") != "offline_only":
                missing.append(f"{item_prefix}.safety_scope")
        for candidate_id in (
            "momentum_or_trend_candidate",
            "mean_reversion_candidate",
            "volatility_or_regime_filter_candidate",
        ):
            if candidate_id not in candidate_ids:
                missing.append(
                    f"{field_prefix}strategy_comparison_scaffold.candidate_strategy_slots.{candidate_id}"
                )
    comparison_dimensions = scaffold.get("comparison_dimensions")
    if not isinstance(comparison_dimensions, list) or not comparison_dimensions:
        missing.append(
            f"{field_prefix}strategy_comparison_scaffold.comparison_dimensions"
        )
    else:
        for dimension in _REQUIRED_STRATEGY_COMPARISON_DIMENSIONS:
            if dimension not in comparison_dimensions:
                missing.append(
                    f"{field_prefix}strategy_comparison_scaffold.comparison_dimensions.{dimension}"
                )
    evidence = scaffold.get("required_evidence_before_promotion")
    if not isinstance(evidence, list) or not evidence:
        missing.append(
            f"{field_prefix}strategy_comparison_scaffold.required_evidence_before_promotion"
        )
    if not str(scaffold.get("why_selected", "")).strip():
        missing.append(f"{field_prefix}strategy_comparison_scaffold.why_selected")
    replacement_reason = str(
        scaffold.get("why_no_strategy_replacement_yet", "")
    ).lower()
    if "requires deterministic offline evidence comparison first" not in replacement_reason:
        missing.append(
            f"{field_prefix}strategy_comparison_scaffold.why_no_strategy_replacement_yet"
        )
    return missing


def _missing_candidate_strategy_evidence_template_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    template = packet.get("candidate_strategy_evidence_template")
    if not isinstance(template, Mapping):
        return [f"{field_prefix}candidate_strategy_evidence_template"]
    for field_name in _REQUIRED_CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FIELDS:
        if field_name not in template:
            missing.append(
                f"{field_prefix}candidate_strategy_evidence_template.{field_name}"
            )
    if not str(packet.get("candidate_strategy_evidence_template_path", "")).endswith(
        _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME
    ):
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template_path"
        )
    expected_values = {
        "template_status": "ready",
        "evidence_mode": "offline_strategy_evidence_template_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "selected_next_safe_action": "materialize_candidate_evidence_requirements",
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "profit_claim": "none",
    }
    for field_name, expected_value in expected_values.items():
        if template.get(field_name) != expected_value:
            missing.append(
                f"{field_prefix}candidate_strategy_evidence_template.{field_name}"
            )
    if _selector_contains_forbidden_action(
        str(template.get("selected_next_safe_action", ""))
    ):
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template."
            "selected_next_safe_action.safe"
        )
    for false_field in (
        "paper_submit_authorized",
        "hard_gate_required",
        "requires_daniel",
        "daniel_action_required_now",
    ):
        if template.get(false_field) is not False:
            missing.append(
                f"{field_prefix}candidate_strategy_evidence_template."
                f"{false_field}.false"
            )
    candidate_families = template.get("candidate_families")
    if not isinstance(candidate_families, list) or not candidate_families:
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template.candidate_families"
        )
    else:
        candidate_ids: set[str] = set()
        for index, item in enumerate(candidate_families):
            item_prefix = (
                f"{field_prefix}candidate_strategy_evidence_template."
                f"candidate_families[{index}]"
            )
            if not isinstance(item, Mapping):
                missing.append(item_prefix)
                continue
            for field_name in _REQUIRED_CANDIDATE_STRATEGY_FAMILY_FIELDS:
                if field_name not in item:
                    missing.append(f"{item_prefix}.{field_name}")
            candidate_ids.add(str(item.get("candidate_family_id", "")))
            for list_field in (
                "required_inputs",
                "required_metrics",
                "required_safety_checks",
            ):
                if not isinstance(item.get(list_field), list) or not item.get(list_field):
                    missing.append(f"{item_prefix}.{list_field}")
            if item.get("implementation_status") != "not_implemented":
                missing.append(f"{item_prefix}.implementation_status")
            if item.get("broker_dependency") != "none":
                missing.append(f"{item_prefix}.broker_dependency")
            if item.get("hard_gate_required") is not False:
                missing.append(f"{item_prefix}.hard_gate_required.false")
            if item.get("safety_scope") != "offline_only":
                missing.append(f"{item_prefix}.safety_scope")
        for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS:
            if candidate_id not in candidate_ids:
                missing.append(
                    f"{field_prefix}candidate_strategy_evidence_template."
                    f"candidate_families.{candidate_id}"
                )
    evidence_sections = template.get("required_evidence_sections")
    if not isinstance(evidence_sections, list) or not evidence_sections:
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template."
            "required_evidence_sections"
        )
    else:
        for section in _REQUIRED_CANDIDATE_EVIDENCE_SECTIONS:
            if section not in evidence_sections:
                missing.append(
                    f"{field_prefix}candidate_strategy_evidence_template."
                    f"required_evidence_sections.{section}"
                )
    for list_field in (
        "minimum_promotion_requirements",
        "rejection_criteria",
        "offline_artifacts_required",
        "human_readable_review_questions",
    ):
        if not isinstance(template.get(list_field), list) or not template.get(
            list_field
        ):
            missing.append(
                f"{field_prefix}candidate_strategy_evidence_template.{list_field}"
            )
    if (
        _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME
        not in template.get("offline_artifacts_required", [])
    ):
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template."
            "offline_artifacts_required.template"
        )
    comparison = template.get("comparison_against_baseline")
    if not isinstance(comparison, Mapping):
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template."
            "comparison_against_baseline"
        )
    elif comparison.get("baseline_strategy_id") != "spy_sma_50_200_control":
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template."
            "comparison_against_baseline.baseline_strategy_id"
        )
    if not str(template.get("why_selected", "")).strip():
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template.why_selected"
        )
    implementation_reason = str(
        template.get("why_no_strategy_implementation_yet", "")
    ).lower()
    if (
        "requires an offline evidence template" not in implementation_reason
        or "deterministic comparison requirements first" not in implementation_reason
    ):
        missing.append(
            f"{field_prefix}candidate_strategy_evidence_template."
            "why_no_strategy_implementation_yet"
        )
    return missing


def _missing_candidate_evidence_requirements_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    requirements = packet.get("candidate_evidence_requirements")
    if not isinstance(requirements, Mapping):
        return [f"{field_prefix}candidate_evidence_requirements"]
    for field_name in _REQUIRED_CANDIDATE_EVIDENCE_REQUIREMENTS_FIELDS:
        if field_name not in requirements:
            missing.append(f"{field_prefix}candidate_evidence_requirements.{field_name}")
    if not str(packet.get("candidate_evidence_requirements_path", "")).endswith(
        _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME
    ):
        missing.append(f"{field_prefix}candidate_evidence_requirements_path")
    expected_values = {
        "requirements_status": "ready",
        "requirements_mode": "offline_candidate_evidence_requirements_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "selected_next_safe_action": "build_candidate_evidence_collection_plan",
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "profit_claim": "none",
    }
    for field_name, expected_value in expected_values.items():
        if requirements.get(field_name) != expected_value:
            missing.append(
                f"{field_prefix}candidate_evidence_requirements.{field_name}"
            )
    if _selector_contains_forbidden_action(
        str(requirements.get("selected_next_safe_action", ""))
    ):
        missing.append(
            f"{field_prefix}candidate_evidence_requirements."
            "selected_next_safe_action.safe"
        )
    if "offline" not in str(requirements.get("why_selected", "")).lower():
        missing.append(f"{field_prefix}candidate_evidence_requirements.why_selected")
    implementation_reason = str(
        requirements.get("why_no_strategy_implementation_yet", "")
    ).lower()
    if (
        "strategy implementation remains blocked" not in implementation_reason
        or "materialized, collected, and compared against the baseline"
        not in implementation_reason
    ):
        missing.append(
            f"{field_prefix}candidate_evidence_requirements."
            "why_no_strategy_implementation_yet"
        )
    for false_field in (
        "paper_submit_authorized",
        "hard_gate_required",
        "requires_daniel",
        "daniel_action_required_now",
    ):
        if requirements.get(false_field) is not False:
            missing.append(
                f"{field_prefix}candidate_evidence_requirements."
                f"{false_field}.false"
            )
    candidate_requirements = requirements.get("candidate_requirements")
    if not isinstance(candidate_requirements, list) or not candidate_requirements:
        missing.append(
            f"{field_prefix}candidate_evidence_requirements.candidate_requirements"
        )
    else:
        candidate_ids: set[str] = set()
        for index, item in enumerate(candidate_requirements):
            item_prefix = (
                f"{field_prefix}candidate_evidence_requirements."
                f"candidate_requirements[{index}]"
            )
            if not isinstance(item, Mapping):
                missing.append(item_prefix)
                continue
            for field_name in _REQUIRED_CANDIDATE_EVIDENCE_REQUIREMENT_FIELDS:
                if field_name not in item:
                    missing.append(f"{item_prefix}.{field_name}")
            candidate_ids.add(str(item.get("candidate_family_id", "")))
            if item.get("implementation_status") != "not_implemented":
                missing.append(f"{item_prefix}.implementation_status")
            if item.get("promotion_status") != "promotion_blocked":
                missing.append(f"{item_prefix}.promotion_status")
            if item.get("broker_dependency") != "none":
                missing.append(f"{item_prefix}.broker_dependency")
            if item.get("hard_gate_required") is not False:
                missing.append(f"{item_prefix}.hard_gate_required.false")
            if item.get("safety_scope") != "offline_only":
                missing.append(f"{item_prefix}.safety_scope")
            for list_field in (
                "required_data_inputs",
                "required_feature_definitions",
                "required_signal_definition",
                "required_risk_definition",
                "required_backtest_outputs",
                "required_cost_model_outputs",
                "required_benchmark_comparisons",
                "required_regime_analysis",
                "required_turnover_analysis",
                "required_drawdown_analysis",
                "required_failure_mode_review",
                "required_safety_checks",
                "missing_evidence",
                "promotion_blockers",
                "rejection_triggers",
            ):
                if not isinstance(item.get(list_field), list) or not item.get(
                    list_field
                ):
                    missing.append(f"{item_prefix}.{list_field}")
            if "paper_observation_not_authorized" not in item.get(
                "promotion_blockers",
                [],
            ):
                missing.append(f"{item_prefix}.promotion_blockers.paper_observation")
        for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS:
            if candidate_id not in candidate_ids:
                missing.append(
                    f"{field_prefix}candidate_evidence_requirements."
                    f"candidate_requirements.{candidate_id}"
                )
    for list_field in (
        "shared_evidence_requirements",
        "promotion_blockers",
        "rejection_triggers",
        "next_research_artifacts_to_build",
    ):
        if not isinstance(requirements.get(list_field), list) or not requirements.get(
            list_field
        ):
            missing.append(f"{field_prefix}candidate_evidence_requirements.{list_field}")
    shared = requirements.get("shared_evidence_requirements", [])
    for shared_requirement in (
        "deterministic_offline_data_source",
        "explicit_data_basis",
        "feature_calculation_definition",
        "signal_rule_definition",
        "risk_rule_definition",
        "benchmark_comparison_against_spy_sma_50_200_control",
        "transaction_cost_assumption",
        "turnover_estimate",
        "drawdown_evidence",
        "regime_sensitivity_evidence",
        "dependency_direction_guard",
        "default_pytest_network_guard",
        "broker_mutation_invariant",
        "no_broker_dependency_in_research_path",
        "no_llm_or_agent_dependency_in_strategy_path",
    ):
        if shared_requirement not in shared:
            missing.append(
                f"{field_prefix}candidate_evidence_requirements."
                f"shared_evidence_requirements.{shared_requirement}"
            )
    per_candidate = requirements.get("per_candidate_missing_evidence")
    if not isinstance(per_candidate, Mapping) or not per_candidate:
        missing.append(
            f"{field_prefix}candidate_evidence_requirements."
            "per_candidate_missing_evidence"
        )
    else:
        for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS:
            candidate_missing = per_candidate.get(candidate_id)
            if not isinstance(candidate_missing, list) or not candidate_missing:
                missing.append(
                    f"{field_prefix}candidate_evidence_requirements."
                    f"per_candidate_missing_evidence.{candidate_id}"
                )
    for blocker in (
        "candidate_strategy_not_implemented",
        "offline_backtest_not_materialized",
        "benchmark_comparison_missing",
        "cost_model_evidence_missing",
        "drawdown_evidence_missing",
        "regime_evidence_missing",
        "turnover_evidence_missing",
        "paper_observation_not_authorized",
    ):
        if blocker not in requirements.get("promotion_blockers", []):
            missing.append(
                f"{field_prefix}candidate_evidence_requirements."
                f"promotion_blockers.{blocker}"
            )
    for trigger in (
        "non_deterministic_signal",
        "broker_dependency_in_research_path",
        "network_dependency_in_default_pytest",
        "excessive_turnover_after_costs",
        "unacceptable_drawdown_vs_baseline",
        "fragile_single_period_performance",
        "missing_benchmark_comparison",
        "missing_regime_analysis",
    ):
        if trigger not in requirements.get("rejection_triggers", []):
            missing.append(
                f"{field_prefix}candidate_evidence_requirements."
                f"rejection_triggers.{trigger}"
            )
    return missing


def _missing_candidate_evidence_collection_plan_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    collection_plan = packet.get("candidate_evidence_collection_plan")
    if not isinstance(collection_plan, Mapping):
        return [f"{field_prefix}candidate_evidence_collection_plan"]
    for field_name in _REQUIRED_CANDIDATE_EVIDENCE_COLLECTION_PLAN_FIELDS:
        if field_name not in collection_plan:
            missing.append(
                f"{field_prefix}candidate_evidence_collection_plan.{field_name}"
            )
    if not str(packet.get("candidate_evidence_collection_plan_path", "")).endswith(
        _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME
    ):
        missing.append(f"{field_prefix}candidate_evidence_collection_plan_path")
    expected_values = {
        "collection_plan_status": "ready",
        "collection_plan_mode": "offline_candidate_evidence_collection_plan_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "selected_next_safe_action": "build_candidate_evidence_collection_status",
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "profit_claim": "none",
    }
    for field_name, expected_value in expected_values.items():
        if collection_plan.get(field_name) != expected_value:
            missing.append(
                f"{field_prefix}candidate_evidence_collection_plan.{field_name}"
            )
    if _selector_contains_forbidden_action(
        str(collection_plan.get("selected_next_safe_action", ""))
    ):
        missing.append(
            f"{field_prefix}candidate_evidence_collection_plan."
            "selected_next_safe_action.safe"
        )
    if "offline" not in str(collection_plan.get("why_selected", "")).lower():
        missing.append(
            f"{field_prefix}candidate_evidence_collection_plan.why_selected"
        )
    implementation_reason = str(
        collection_plan.get("why_no_strategy_implementation_yet", "")
    ).lower()
    if (
        "candidate strategy implementation remains blocked"
        not in implementation_reason
        or "offline evidence collection plan is executed"
        not in implementation_reason
        or "evidence is compared against the baseline"
        not in implementation_reason
    ):
        missing.append(
            f"{field_prefix}candidate_evidence_collection_plan."
            "why_no_strategy_implementation_yet"
        )
    for false_field in (
        "paper_submit_authorized",
        "hard_gate_required",
        "requires_daniel",
        "daniel_action_required_now",
    ):
        if collection_plan.get(false_field) is not False:
            missing.append(
                f"{field_prefix}candidate_evidence_collection_plan."
                f"{false_field}.false"
            )
    candidate_plans = collection_plan.get("candidate_collection_plans")
    if not isinstance(candidate_plans, list) or not candidate_plans:
        missing.append(
            f"{field_prefix}candidate_evidence_collection_plan."
            "candidate_collection_plans"
        )
    else:
        candidate_ids: set[str] = set()
        for index, item in enumerate(candidate_plans):
            item_prefix = (
                f"{field_prefix}candidate_evidence_collection_plan."
                f"candidate_collection_plans[{index}]"
            )
            if not isinstance(item, Mapping):
                missing.append(item_prefix)
                continue
            for field_name in _REQUIRED_CANDIDATE_EVIDENCE_COLLECTION_PLAN_ENTRY_FIELDS:
                if field_name not in item:
                    missing.append(f"{item_prefix}.{field_name}")
            candidate_ids.add(str(item.get("candidate_family_id", "")))
            expected_entry_values = {
                "implementation_status": "not_implemented",
                "evidence_status": "evidence_not_collected",
                "collection_status": "ready_to_collect_offline_evidence",
                "promotion_status": "promotion_blocked_pending_evidence_collection",
                "broker_dependency": "none",
                "safety_scope": "offline_only",
            }
            for field_name, expected_value in expected_entry_values.items():
                if item.get(field_name) != expected_value:
                    missing.append(f"{item_prefix}.{field_name}")
            if item.get("hard_gate_required") is not False:
                missing.append(f"{item_prefix}.hard_gate_required.false")
            for list_field in (
                "collection_steps",
                "data_inputs_to_collect",
                "features_to_define",
                "signal_rules_to_specify",
                "risk_rules_to_specify",
                "backtest_outputs_to_collect",
                "cost_outputs_to_collect",
                "benchmark_outputs_to_collect",
                "regime_outputs_to_collect",
                "turnover_outputs_to_collect",
                "drawdown_outputs_to_collect",
                "failure_modes_to_review",
                "safety_checks_to_run",
                "expected_artifacts",
                "blocked_until_collected",
            ):
                if not isinstance(item.get(list_field), list) or not item.get(
                    list_field
                ):
                    missing.append(f"{item_prefix}.{list_field}")
        for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS:
            if candidate_id not in candidate_ids:
                missing.append(
                    f"{field_prefix}candidate_evidence_collection_plan."
                    f"candidate_collection_plans.{candidate_id}"
                )
    for list_field in (
        "shared_collection_steps",
        "data_collection_requirements",
        "metric_collection_requirements",
        "safety_collection_requirements",
        "expected_offline_artifacts",
        "blocked_until_collected",
    ):
        if not isinstance(collection_plan.get(list_field), list) or not collection_plan.get(
            list_field
        ):
            missing.append(
                f"{field_prefix}candidate_evidence_collection_plan.{list_field}"
            )
    shared_steps = collection_plan.get("shared_collection_steps", [])
    for shared_step in (
        "confirm deterministic offline data source",
        "confirm explicit data basis",
        "define candidate hypothesis",
        "define feature calculations",
        "define signal rule",
        "define risk rule",
        "define backtest window",
        "define benchmark comparison against spy_sma_50_200_control",
        "define transaction cost assumption",
        "collect turnover estimate",
        "collect drawdown evidence",
        "collect regime sensitivity evidence",
        "run dependency-direction guard",
        "run default pytest network guard",
        "run broker mutation invariant",
        "confirm no broker dependency in research path",
        "confirm no LLM/agent dependency in strategy path",
        (
            "defer paper observation until Daniel explicitly scopes broker read "
            "or paper gate"
        ),
    ):
        if shared_step not in shared_steps:
            missing.append(
                f"{field_prefix}candidate_evidence_collection_plan."
                f"shared_collection_steps.{shared_step}"
            )
    expected_artifacts = collection_plan.get("expected_offline_artifacts", [])
    for artifact_name in (
        "candidate_hypothesis_packet",
        "candidate_data_requirements_packet",
        "candidate_signal_spec_packet",
        "candidate_risk_spec_packet",
        "candidate_backtest_result_packet",
        "candidate_baseline_comparison_packet",
        "candidate_cost_turnover_packet",
        "candidate_regime_drawdown_packet",
        "candidate_safety_review_packet",
        "candidate_promotion_decision_packet",
    ):
        if artifact_name not in expected_artifacts:
            missing.append(
                f"{field_prefix}candidate_evidence_collection_plan."
                f"expected_offline_artifacts.{artifact_name}"
            )
    return missing


def _missing_candidate_evidence_collection_status_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    collection_status = packet.get("candidate_evidence_collection_status")
    if not isinstance(collection_status, Mapping):
        return [f"{field_prefix}candidate_evidence_collection_status"]
    for field_name in _REQUIRED_CANDIDATE_EVIDENCE_COLLECTION_STATUS_FIELDS:
        if field_name not in collection_status:
            missing.append(
                f"{field_prefix}candidate_evidence_collection_status.{field_name}"
            )
    if not str(packet.get("candidate_evidence_collection_status_path", "")).endswith(
        _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME
    ):
        missing.append(f"{field_prefix}candidate_evidence_collection_status_path")
    expected_values = {
        "collection_status": "ready",
        "collection_status_mode": (
            "offline_candidate_evidence_collection_status_only"
        ),
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "selected_next_safe_action": "build_candidate_evidence_gap_summary",
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "profit_claim": "none",
    }
    for field_name, expected_value in expected_values.items():
        if collection_status.get(field_name) != expected_value:
            missing.append(
                f"{field_prefix}candidate_evidence_collection_status.{field_name}"
            )
    selected_action = str(collection_status.get("selected_next_safe_action", ""))
    if _selector_contains_forbidden_action(selected_action):
        missing.append(
            f"{field_prefix}candidate_evidence_collection_status."
            "selected_next_safe_action.safe"
        )
    if "offline" not in str(collection_status.get("why_selected", "")).lower():
        missing.append(
            f"{field_prefix}candidate_evidence_collection_status.why_selected"
        )
    implementation_reason = str(
        collection_status.get("why_no_strategy_implementation_yet", "")
    ).lower()
    if (
        "candidate strategy implementation remains blocked" not in implementation_reason
        or "required evidence is collected, statused" not in implementation_reason
        or "compared against the baseline" not in implementation_reason
    ):
        missing.append(
            f"{field_prefix}candidate_evidence_collection_status."
            "why_no_strategy_implementation_yet"
        )
    for false_field in (
        "paper_submit_authorized",
        "hard_gate_required",
        "requires_daniel",
        "daniel_action_required_now",
    ):
        if collection_status.get(false_field) is not False:
            missing.append(
                f"{field_prefix}candidate_evidence_collection_status."
                f"{false_field}.false"
            )

    candidate_statuses = collection_status.get("candidate_statuses")
    if not isinstance(candidate_statuses, list) or not candidate_statuses:
        missing.append(
            f"{field_prefix}candidate_evidence_collection_status.candidate_statuses"
        )
    else:
        candidate_ids: set[str] = set()
        for index, item in enumerate(candidate_statuses):
            item_prefix = (
                f"{field_prefix}candidate_evidence_collection_status."
                f"candidate_statuses[{index}]"
            )
            if not isinstance(item, Mapping):
                missing.append(item_prefix)
                continue
            for field_name in _REQUIRED_CANDIDATE_EVIDENCE_COLLECTION_STATUS_ENTRY_FIELDS:
                if field_name not in item:
                    missing.append(f"{item_prefix}.{field_name}")
            candidate_ids.add(str(item.get("candidate_family_id", "")))
            expected_entry_values = {
                "current_status": "blocked",
                "implementation_status": "not_implemented",
                "evidence_status": "missing",
                "collection_status": "ready_to_collect",
                "promotion_status": "blocked",
                "broker_dependency": "none",
                "safety_scope": "offline_only",
            }
            for field_name, expected_value in expected_entry_values.items():
                if item.get(field_name) != expected_value:
                    missing.append(f"{item_prefix}.{field_name}")
            if item.get("hard_gate_required") is not False:
                missing.append(f"{item_prefix}.hard_gate_required.false")
            for list_field in (
                "evidence_items",
                "not_started_items",
                "blocked_items",
                "ready_to_collect_items",
                "missing_items",
                "promotion_blockers",
                "next_collection_actions",
            ):
                if not isinstance(item.get(list_field), list) or not item.get(
                    list_field
                ):
                    missing.append(f"{item_prefix}.{list_field}")
            evidence_items = item.get("evidence_items")
            if not isinstance(evidence_items, list) or not evidence_items:
                continue
            seen_statuses: set[str] = set()
            for evidence_index, evidence_item in enumerate(evidence_items):
                evidence_prefix = f"{item_prefix}.evidence_items[{evidence_index}]"
                if not isinstance(evidence_item, Mapping):
                    missing.append(evidence_prefix)
                    continue
                for field_name in _REQUIRED_CANDIDATE_EVIDENCE_ITEM_FIELDS:
                    if field_name not in evidence_item:
                        missing.append(f"{evidence_prefix}.{field_name}")
                status = str(evidence_item.get("status", ""))
                if status not in _CANDIDATE_EVIDENCE_ITEM_STATUSES:
                    missing.append(f"{evidence_prefix}.status.allowed")
                else:
                    seen_statuses.add(status)
                if not str(evidence_item.get("blocker", "")).strip():
                    missing.append(f"{evidence_prefix}.blocker")
                for bool_field in (
                    "required_before_implementation",
                    "required_before_promotion",
                    "offline_only",
                ):
                    if not isinstance(evidence_item.get(bool_field), bool):
                        missing.append(f"{evidence_prefix}.{bool_field}.bool")
                if evidence_item.get("offline_only") is not True:
                    missing.append(f"{evidence_prefix}.offline_only.true")
                if evidence_item.get("broker_dependency") != "none":
                    missing.append(f"{evidence_prefix}.broker_dependency")
            for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES:
                if status not in seen_statuses:
                    missing.append(f"{item_prefix}.evidence_items.{status}")
        for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS:
            if candidate_id not in candidate_ids:
                missing.append(
                    f"{field_prefix}candidate_evidence_collection_status."
                    f"candidate_statuses.{candidate_id}"
                )

    shared_collection_status = collection_status.get("shared_collection_status")
    if not isinstance(shared_collection_status, list) or not shared_collection_status:
        missing.append(
            f"{field_prefix}candidate_evidence_collection_status."
            "shared_collection_status"
        )
    else:
        shared_ids = set()
        for index, item in enumerate(shared_collection_status):
            item_prefix = (
                f"{field_prefix}candidate_evidence_collection_status."
                f"shared_collection_status[{index}]"
            )
            if not isinstance(item, Mapping):
                missing.append(item_prefix)
                continue
            for field_name in (
                "shared_status_id",
                "shared_status_label",
                "status",
                "blocker",
                "offline_only",
                "broker_dependency",
            ):
                if field_name not in item:
                    missing.append(f"{item_prefix}.{field_name}")
            shared_ids.add(str(item.get("shared_status_id", "")))
            if item.get("status") not in _CANDIDATE_EVIDENCE_ITEM_STATUSES:
                missing.append(f"{item_prefix}.status.allowed")
            if item.get("offline_only") is not True:
                missing.append(f"{item_prefix}.offline_only.true")
            if item.get("broker_dependency") != "none":
                missing.append(f"{item_prefix}.broker_dependency")
        for shared_id in (
            "deterministic_offline_data_source_status",
            "explicit_data_basis_status",
            "candidate_hypothesis_status",
            "feature_calculation_status",
            "signal_rule_status",
            "risk_rule_status",
            "backtest_window_status",
            "benchmark_comparison_status",
            "transaction_cost_assumption_status",
            "turnover_estimate_status",
            "drawdown_evidence_status",
            "regime_sensitivity_evidence_status",
            "dependency_direction_guard_status",
            "default_pytest_network_guard_status",
            "broker_mutation_invariant_status",
            "broker_dependency_status",
            "llm_agent_dependency_status",
            "paper_observation_deferral_status",
        ):
            if shared_id not in shared_ids:
                missing.append(
                    f"{field_prefix}candidate_evidence_collection_status."
                    f"shared_collection_status.{shared_id}"
                )

    counts = collection_status.get("evidence_status_counts")
    if not isinstance(counts, Mapping) or not counts:
        missing.append(
            f"{field_prefix}candidate_evidence_collection_status."
            "evidence_status_counts"
        )
    else:
        for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES:
            count = counts.get(status)
            if not isinstance(count, int) or count <= 0:
                missing.append(
                    f"{field_prefix}candidate_evidence_collection_status."
                    f"evidence_status_counts.{status}"
                )
    for list_field in (
        "not_started_evidence",
        "blocked_evidence",
        "ready_to_collect_evidence",
        "missing_evidence",
        "promotion_blockers",
        "next_collection_actions",
    ):
        if not isinstance(collection_status.get(list_field), list) or not collection_status.get(
            list_field
        ):
            missing.append(
                f"{field_prefix}candidate_evidence_collection_status.{list_field}"
            )
    if selected_action not in collection_status.get("next_collection_actions", []):
        missing.append(
            f"{field_prefix}candidate_evidence_collection_status."
            "selected_next_safe_action.in_next_collection_actions"
        )
    return missing


def _missing_candidate_evidence_gap_summary_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    gap_summary = packet.get("candidate_evidence_gap_summary")
    if not isinstance(gap_summary, Mapping):
        return [f"{field_prefix}candidate_evidence_gap_summary"]
    for field_name in _REQUIRED_CANDIDATE_EVIDENCE_GAP_SUMMARY_FIELDS:
        if field_name not in gap_summary:
            missing.append(
                f"{field_prefix}candidate_evidence_gap_summary.{field_name}"
            )
    if not str(packet.get("candidate_evidence_gap_summary_path", "")).endswith(
        _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME
    ):
        missing.append(f"{field_prefix}candidate_evidence_gap_summary_path")
    expected_values = {
        "gap_summary_status": "ready",
        "gap_summary_mode": "offline_candidate_evidence_gap_summary_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "selected_next_safe_action": "build_candidate_gap_closure_queue",
        "broker_state_mode": "broker_state_not_observed",
        "safety_scope": "offline_only",
        "profit_claim": "none",
    }
    for field_name, expected_value in expected_values.items():
        if gap_summary.get(field_name) != expected_value:
            missing.append(
                f"{field_prefix}candidate_evidence_gap_summary.{field_name}"
            )
    selected_action = str(gap_summary.get("selected_next_safe_action", ""))
    if _selector_contains_forbidden_action(selected_action):
        missing.append(
            f"{field_prefix}candidate_evidence_gap_summary."
            "selected_next_safe_action.safe"
        )
    if "offline" not in str(gap_summary.get("why_selected", "")).lower():
        missing.append(f"{field_prefix}candidate_evidence_gap_summary.why_selected")
    implementation_reason = str(
        gap_summary.get("why_no_strategy_implementation_yet", "")
    ).lower()
    if (
        "candidate strategy implementation remains blocked"
        not in implementation_reason
        or "evidence gaps are summarized, prioritized, closed"
        not in implementation_reason
        or "compared against the baseline" not in implementation_reason
    ):
        missing.append(
            f"{field_prefix}candidate_evidence_gap_summary."
            "why_no_strategy_implementation_yet"
        )
    for false_field in (
        "paper_submit_authorized",
        "hard_gate_required",
        "requires_daniel",
        "daniel_action_required_now",
    ):
        if gap_summary.get(false_field) is not False:
            missing.append(
                f"{field_prefix}candidate_evidence_gap_summary."
                f"{false_field}.false"
            )

    candidate_gap_summaries = gap_summary.get("candidate_gap_summaries")
    if not isinstance(candidate_gap_summaries, list) or not candidate_gap_summaries:
        missing.append(
            f"{field_prefix}candidate_evidence_gap_summary."
            "candidate_gap_summaries"
        )
    else:
        candidate_ids: set[str] = set()
        for index, item in enumerate(candidate_gap_summaries):
            item_prefix = (
                f"{field_prefix}candidate_evidence_gap_summary."
                f"candidate_gap_summaries[{index}]"
            )
            if not isinstance(item, Mapping):
                missing.append(item_prefix)
                continue
            for field_name in _REQUIRED_CANDIDATE_EVIDENCE_GAP_SUMMARY_ENTRY_FIELDS:
                if field_name not in item:
                    missing.append(f"{item_prefix}.{field_name}")
            candidate_ids.add(str(item.get("candidate_family_id", "")))
            expected_entry_values = {
                "current_status": "blocked",
                "implementation_status": "not_implemented",
                "evidence_status": "missing",
                "collection_status": "ready_to_collect",
                "promotion_status": "blocked",
                "broker_dependency": "none",
                "safety_scope": "offline_only",
            }
            for field_name, expected_value in expected_entry_values.items():
                if item.get(field_name) != expected_value:
                    missing.append(f"{item_prefix}.{field_name}")
            if item.get("hard_gate_required") is not False:
                missing.append(f"{item_prefix}.hard_gate_required.false")
            if not isinstance(item.get("total_gap_count"), int) or int(
                item.get("total_gap_count", 0)
            ) <= 0:
                missing.append(f"{item_prefix}.total_gap_count")
            for list_field in (
                "evidence_gaps",
                "blocked_gaps",
                "missing_gaps",
                "not_started_gaps",
                "ready_to_collect_gaps",
                "promotion_blockers",
                "next_gap_closure_actions",
            ):
                if not isinstance(item.get(list_field), list) or not item.get(
                    list_field
                ):
                    missing.append(f"{item_prefix}.{list_field}")
            evidence_gaps = item.get("evidence_gaps")
            gap_ids: set[str] = set()
            seen_statuses: set[str] = set()
            seen_priorities: set[str] = set()
            if isinstance(evidence_gaps, list):
                for gap_index, gap in enumerate(evidence_gaps):
                    gap_prefix = f"{item_prefix}.evidence_gaps[{gap_index}]"
                    if not isinstance(gap, Mapping):
                        missing.append(gap_prefix)
                        continue
                    for field_name in _REQUIRED_CANDIDATE_EVIDENCE_GAP_FIELDS:
                        if field_name not in gap:
                            missing.append(f"{gap_prefix}.{field_name}")
                    gap_id = str(gap.get("gap_id", ""))
                    gap_ids.add(gap_id)
                    priority = str(gap.get("priority", ""))
                    status = str(gap.get("status", ""))
                    if priority not in _CANDIDATE_EVIDENCE_GAP_PRIORITIES:
                        missing.append(f"{gap_prefix}.priority.allowed")
                    else:
                        seen_priorities.add(priority)
                    if status not in _CANDIDATE_EVIDENCE_ITEM_STATUSES:
                        missing.append(f"{gap_prefix}.status.allowed")
                    else:
                        seen_statuses.add(status)
                    for bool_field in (
                        "required_before_implementation",
                        "required_before_promotion",
                        "offline_only",
                    ):
                        if not isinstance(gap.get(bool_field), bool):
                            missing.append(f"{gap_prefix}.{bool_field}.bool")
                    if gap.get("offline_only") is not True:
                        missing.append(f"{gap_prefix}.offline_only.true")
                    if gap.get("broker_dependency") != "none":
                        missing.append(f"{gap_prefix}.broker_dependency")
                    if not str(gap.get("closure_artifact", "")).endswith(".jsonl"):
                        missing.append(f"{gap_prefix}.closure_artifact")
            for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES:
                if status not in seen_statuses:
                    missing.append(f"{item_prefix}.evidence_gaps.{status}")
            for priority in ("high", "medium"):
                if priority not in seen_priorities:
                    missing.append(f"{item_prefix}.evidence_gaps.{priority}")
            if str(item.get("highest_priority_gap", "")) not in gap_ids:
                missing.append(f"{item_prefix}.highest_priority_gap")
        for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS:
            if candidate_id not in candidate_ids:
                missing.append(
                    f"{field_prefix}candidate_evidence_gap_summary."
                    f"candidate_gap_summaries.{candidate_id}"
                )

    ranked_gap_groups = gap_summary.get("ranked_gap_groups")
    expected_group_ids = (
        "strategy_definition_gaps",
        "data_and_feature_gaps",
        "backtest_and_benchmark_gaps",
        "cost_turnover_drawdown_gaps",
        "regime_and_failure_mode_gaps",
        "safety_and_dependency_gaps",
        "paper_observation_deferred_gaps",
    )
    if not isinstance(ranked_gap_groups, list) or not ranked_gap_groups:
        missing.append(
            f"{field_prefix}candidate_evidence_gap_summary.ranked_gap_groups"
        )
    else:
        group_ids: set[str] = set()
        for index, group in enumerate(ranked_gap_groups):
            group_prefix = (
                f"{field_prefix}candidate_evidence_gap_summary."
                f"ranked_gap_groups[{index}]"
            )
            if not isinstance(group, Mapping):
                missing.append(group_prefix)
                continue
            for field_name in _REQUIRED_CANDIDATE_EVIDENCE_GAP_GROUP_FIELDS:
                if field_name not in group:
                    missing.append(f"{group_prefix}.{field_name}")
            group_ids.add(str(group.get("group_id", "")))
            if group.get("priority") not in _CANDIDATE_EVIDENCE_GAP_PRIORITIES:
                missing.append(f"{group_prefix}.priority.allowed")
            if not isinstance(group.get("gap_count"), int) or int(
                group.get("gap_count", 0)
            ) <= 0:
                missing.append(f"{group_prefix}.gap_count")
            if not str(group.get("next_gap_closure_action", "")).strip():
                missing.append(f"{group_prefix}.next_gap_closure_action")
        for group_id in expected_group_ids:
            if group_id not in group_ids:
                missing.append(
                    f"{field_prefix}candidate_evidence_gap_summary."
                    f"ranked_gap_groups.{group_id}"
                )

    highest_priority_gaps = gap_summary.get("highest_priority_gaps")
    if not isinstance(highest_priority_gaps, list) or not highest_priority_gaps:
        missing.append(
            f"{field_prefix}candidate_evidence_gap_summary.highest_priority_gaps"
        )
    shared_gap_summary = gap_summary.get("shared_gap_summary")
    if not isinstance(shared_gap_summary, list) or not shared_gap_summary:
        missing.append(
            f"{field_prefix}candidate_evidence_gap_summary.shared_gap_summary"
        )
    else:
        for index, shared_gap in enumerate(shared_gap_summary):
            shared_prefix = (
                f"{field_prefix}candidate_evidence_gap_summary."
                f"shared_gap_summary[{index}]"
            )
            if not isinstance(shared_gap, Mapping):
                missing.append(shared_prefix)
                continue
            if shared_gap.get("priority") not in _CANDIDATE_EVIDENCE_GAP_PRIORITIES:
                missing.append(f"{shared_prefix}.priority.allowed")
            if shared_gap.get("status") not in _CANDIDATE_EVIDENCE_ITEM_STATUSES:
                missing.append(f"{shared_prefix}.status.allowed")
            if shared_gap.get("offline_only") is not True:
                missing.append(f"{shared_prefix}.offline_only.true")
            if shared_gap.get("broker_dependency") != "none":
                missing.append(f"{shared_prefix}.broker_dependency")

    gap_counts = gap_summary.get("gap_counts")
    if not isinstance(gap_counts, Mapping) or not gap_counts:
        missing.append(f"{field_prefix}candidate_evidence_gap_summary.gap_counts")
    else:
        for count_field in (
            "total_gap_count",
            "candidate_gap_count",
            "shared_gap_count",
            "ranked_gap_group_count",
        ):
            if not isinstance(gap_counts.get(count_field), int) or int(
                gap_counts.get(count_field, 0)
            ) <= 0:
                missing.append(
                    f"{field_prefix}candidate_evidence_gap_summary."
                    f"gap_counts.{count_field}"
                )
        by_status = gap_counts.get("by_status")
        if not isinstance(by_status, Mapping):
            missing.append(
                f"{field_prefix}candidate_evidence_gap_summary.gap_counts.by_status"
            )
        else:
            for status in _CANDIDATE_EVIDENCE_ITEM_STATUSES:
                if not isinstance(by_status.get(status), int) or int(
                    by_status.get(status, 0)
                ) <= 0:
                    missing.append(
                        f"{field_prefix}candidate_evidence_gap_summary."
                        f"gap_counts.by_status.{status}"
                    )
        by_priority = gap_counts.get("by_priority")
        if not isinstance(by_priority, Mapping):
            missing.append(
                f"{field_prefix}candidate_evidence_gap_summary.gap_counts.by_priority"
            )
        else:
            for priority in _CANDIDATE_EVIDENCE_GAP_PRIORITIES:
                if not isinstance(by_priority.get(priority), int) or int(
                    by_priority.get(priority, 0)
                ) <= 0:
                    missing.append(
                        f"{field_prefix}candidate_evidence_gap_summary."
                        f"gap_counts.by_priority.{priority}"
                    )
    for list_field in (
        "next_gap_closure_actions",
        "next_research_artifacts_to_build",
    ):
        if not isinstance(gap_summary.get(list_field), list) or not gap_summary.get(
            list_field
        ):
            missing.append(
                f"{field_prefix}candidate_evidence_gap_summary.{list_field}"
            )
    if selected_action not in gap_summary.get("next_gap_closure_actions", []):
        missing.append(
            f"{field_prefix}candidate_evidence_gap_summary."
            "selected_next_safe_action.in_next_gap_closure_actions"
        )
    return missing


def _missing_candidate_gap_closure_queue_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    queue = packet.get("candidate_gap_closure_queue")
    if not isinstance(queue, Mapping):
        return [f"{field_prefix}candidate_gap_closure_queue"]
    for field_name in _REQUIRED_CANDIDATE_GAP_CLOSURE_QUEUE_FIELDS:
        if field_name not in queue:
            missing.append(f"{field_prefix}candidate_gap_closure_queue.{field_name}")
    if not str(packet.get("candidate_gap_closure_queue_path", "")).endswith(
        _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME
    ):
        missing.append(f"{field_prefix}candidate_gap_closure_queue_path")
    expected_values = {
        "candidate_gap_closure_queue_version": (
            _CANDIDATE_GAP_CLOSURE_QUEUE_VERSION
        ),
        "queue_status": "ready",
        "queue_mode": "offline_candidate_gap_closure_queue_only",
        "source_gap_summary_status": "ready",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "baseline_strategy_role": "control_harness",
        "selected_next_safe_action_type": "candidate_gap_closure_queue_item",
        "selected_work_order": "codex_work_order",
        "selected_owner": "Codex",
        "broker_state_mode": "broker_state_not_observed",
        "broker_state_observed": False,
        "paper_submit_authorized": False,
        "daniel_action_required_now": False,
        "profit_claim": "none",
    }
    for field_name, expected_value in expected_values.items():
        if queue.get(field_name) != expected_value:
            missing.append(f"{field_prefix}candidate_gap_closure_queue.{field_name}")
    if not str(queue.get("artifact_path", "")).endswith(
        _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME
    ):
        missing.append(f"{field_prefix}candidate_gap_closure_queue.artifact_path")
    if not str(queue.get("source_gap_summary_path", "")).endswith(
        _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME
    ):
        missing.append(
            f"{field_prefix}candidate_gap_closure_queue.source_gap_summary_path"
        )
    if _selector_contains_forbidden_action(
        str(queue.get("selected_next_safe_action", ""))
    ):
        missing.append(
            f"{field_prefix}candidate_gap_closure_queue."
            "selected_next_safe_action.safe"
        )
    if not str(queue.get("selected_next_safe_action", "")).startswith(
        "execute_candidate_gap_closure_queue_item_"
    ):
        missing.append(
            f"{field_prefix}candidate_gap_closure_queue."
            "selected_next_safe_action.concrete_item"
        )
    if "offline" not in str(queue.get("why_selected", "")).lower():
        missing.append(f"{field_prefix}candidate_gap_closure_queue.why_selected")
    implementation_reason = str(
        queue.get("why_no_strategy_implementation_yet", "")
    ).lower()
    if (
        "candidate strategy implementation remains blocked"
        not in implementation_reason
        or "offline evidence artifacts are materialized" not in implementation_reason
        or "spy sma 50/200 control harness" not in implementation_reason
    ):
        missing.append(
            f"{field_prefix}candidate_gap_closure_queue."
            "why_no_strategy_implementation_yet"
        )
    for list_field in (
        "generation_inputs",
        "next_research_artifacts_to_build",
        "allowed_scope",
        "forbidden_scope",
        "acceptance_criteria",
        "safety_labels",
    ):
        if not isinstance(queue.get(list_field), list) or not queue.get(list_field):
            missing.append(f"{field_prefix}candidate_gap_closure_queue.{list_field}")
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "paper_lab_only",
        "profit_claim=none",
    ):
        if label not in queue.get("safety_labels", []):
            missing.append(
                f"{field_prefix}candidate_gap_closure_queue.safety_labels.{label}"
            )
    serialized = json.dumps(
        _json_safe(queue),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    for forbidden in (
        "paper_submit_authorized\":true",
        "live_trading_authorized",
        "broker_state_observed\":true",
    ):
        if forbidden in serialized:
            missing.append(
                f"{field_prefix}candidate_gap_closure_queue.forbidden.{forbidden}"
            )
    queue_items = queue.get("queue_items")
    if not isinstance(queue_items, list) or not queue_items:
        missing.append(f"{field_prefix}candidate_gap_closure_queue.queue_items")
        return missing
    if queue.get("queue_item_count") != len(queue_items):
        missing.append(
            f"{field_prefix}candidate_gap_closure_queue.queue_item_count"
        )
    item_ids: set[str] = set()
    action_ids: set[str] = set()
    expected_rank = 1
    for index, item in enumerate(queue_items):
        item_prefix = (
            f"{field_prefix}candidate_gap_closure_queue.queue_items[{index}]"
        )
        if not isinstance(item, Mapping):
            missing.append(item_prefix)
            continue
        for field_name in _REQUIRED_CANDIDATE_GAP_CLOSURE_QUEUE_ITEM_FIELDS:
            if field_name not in item:
                missing.append(f"{item_prefix}.{field_name}")
        item_id = str(item.get("queue_item_id", ""))
        action_id = str(item.get("action_id", ""))
        item_ids.add(item_id)
        action_ids.add(action_id)
        if item.get("rank") != expected_rank:
            missing.append(f"{item_prefix}.rank")
        expected_rank += 1
        if item.get("priority") not in _CANDIDATE_EVIDENCE_GAP_PRIORITIES:
            missing.append(f"{item_prefix}.priority.allowed")
        if item.get("action_priority") not in _ACTION_PRIORITIES:
            missing.append(f"{item_prefix}.action_priority.allowed")
        if not action_id.startswith("execute_candidate_gap_closure_queue_item_"):
            missing.append(f"{item_prefix}.action_id")
        if not str(item.get("expected_evidence_artifact", "")).endswith(".jsonl"):
            missing.append(f"{item_prefix}.expected_evidence_artifact")
        if item.get("recommended_agent") not in {"Codex", "GPT", "Claude", "Antigravity"}:
            missing.append(f"{item_prefix}.recommended_agent")
        for list_field in (
            "allowed_scope",
            "forbidden_scope",
            "acceptance_criteria",
            "blocked_by",
            "safety_labels",
        ):
            if not isinstance(item.get(list_field), list) or not item.get(list_field):
                missing.append(f"{item_prefix}.{list_field}")
        for false_field in (
            "daniel_action_required",
            "broker_state_observed",
            "paper_submit_authorized",
        ):
            if item.get(false_field) is not False:
                missing.append(f"{item_prefix}.{false_field}.false")
        if item.get("broker_state_mode") != "broker_state_not_observed":
            missing.append(f"{item_prefix}.broker_state_mode")
        if item.get("profit_claim") != "none":
            missing.append(f"{item_prefix}.profit_claim")
        item_safety_scope = str(item.get("safety_scope", ""))
        for safety_token in (
            "offline_only",
            "research_only",
            "not_live_authorized",
            "broker_state_not_observed",
            "paper_submit_not_authorized",
            "profit_claim=none",
        ):
            if safety_token not in item_safety_scope:
                missing.append(f"{item_prefix}.safety_scope.{safety_token}")
        item_text = json.dumps(
            _json_safe(item),
            sort_keys=True,
            separators=(",", ":"),
        ).lower()
        for forbidden_token in (
            "broker reads allowed",
            "broker mutation allowed",
            "paper submit authorized",
            "live trading authorized",
        ):
            if forbidden_token in item_text:
                missing.append(f"{item_prefix}.forbidden.{forbidden_token}")
    selected_item_id = str(queue.get("selected_queue_item_id", ""))
    if selected_item_id not in item_ids:
        missing.append(
            f"{field_prefix}candidate_gap_closure_queue.selected_queue_item_id"
        )
    selected_action = str(queue.get("selected_next_safe_action", ""))
    if selected_action not in action_ids:
        missing.append(
            f"{field_prefix}candidate_gap_closure_queue."
            "selected_next_safe_action.in_queue_items"
        )
    return missing


def _missing_candidate_risk_rule_status_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    status = packet.get("candidate_risk_rule_status")
    if not isinstance(status, Mapping):
        return [f"{field_prefix}candidate_risk_rule_status"]
    for field_name in _REQUIRED_CANDIDATE_RISK_RULE_STATUS_FIELDS:
        if field_name not in status:
            missing.append(f"{field_prefix}candidate_risk_rule_status.{field_name}")
    if not str(packet.get("candidate_risk_rule_status_path", "")).endswith(
        _CANDIDATE_RISK_RULE_STATUS_FILENAME
    ):
        missing.append(f"{field_prefix}candidate_risk_rule_status_path")
    expected_values = {
        "risk_rule_status_version": _CANDIDATE_RISK_RULE_STATUS_VERSION,
        "risk_rule_status": "ready",
        "risk_rule_status_mode": "offline_candidate_risk_rule_status_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "source_queue_item_id": _CANDIDATE_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
        "source_action_id": _CANDIDATE_RISK_RULE_STATUS_SOURCE_ACTION_ID,
        "source_gap_id": "candidate_risk_rule_status",
        "source_candidate_family_id": (
            _CANDIDATE_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID
        ),
        "source_candidate_family": _CANDIDATE_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY,
        "source_gap_status": "blocked",
        "source_gap_group_id": "strategy_definition_gaps",
        "source_gap_group_label": "Strategy definition gaps",
        "source_closure_action": "close_strategy_definition_gaps",
        "source_expected_evidence_artifact": _CANDIDATE_RISK_RULE_STATUS_FILENAME,
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "daniel_action_required_now": False,
        "profit_claim": "none",
        "safety_scope": "offline_only",
    }
    for field_name, expected_value in expected_values.items():
        if status.get(field_name) != expected_value:
            missing.append(f"{field_prefix}candidate_risk_rule_status.{field_name}")
    selected_action = str(status.get("selected_next_safe_action", ""))
    if _selector_contains_forbidden_action(selected_action):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status."
            "selected_next_safe_action.safe"
        )
    if not selected_action.startswith("execute_candidate_gap_closure_queue_item_"):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status."
            "selected_next_safe_action.concrete_item"
        )
    if selected_action != _CANDIDATE_RISK_RULE_STATUS_NEXT_ACTION_ID:
        missing.append(
            f"{field_prefix}candidate_risk_rule_status."
            "selected_next_safe_action.advanced"
        )
    if (
        _CANDIDATE_RISK_RULE_STATUS_FILENAME
        not in str(status.get("source_closure_objective", ""))
        or "offline" not in str(status.get("source_closure_objective", "")).lower()
    ):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status.source_closure_objective"
        )
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        if label not in status.get("safety_labels", []):
            missing.append(
                f"{field_prefix}candidate_risk_rule_status.safety_labels.{label}"
            )
    for list_field in (
        "candidate_risk_rule_summaries",
        "shared_risk_rule_gaps",
        "highest_priority_risk_rule_gaps",
        "risk_rule_acceptance_criteria",
        "next_risk_rule_closure_actions",
        "safety_labels",
    ):
        if not isinstance(status.get(list_field), list) or not status.get(list_field):
            missing.append(f"{field_prefix}candidate_risk_rule_status.{list_field}")
    target_summary = status.get("target_candidate_risk_rule_summary")
    if not isinstance(target_summary, Mapping):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status."
            "target_candidate_risk_rule_summary"
        )
    elif (
        target_summary.get("candidate_family_id")
        != _CANDIDATE_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID
    ):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status."
            "target_candidate_risk_rule_summary.candidate_family_id"
        )
    evidence_status_summary = status.get("evidence_status_summary")
    if not isinstance(evidence_status_summary, Mapping):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status.evidence_status_summary"
        )
    else:
        for status_name in (
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        ):
            if not isinstance(evidence_status_summary.get(status_name), int):
                missing.append(
                    f"{field_prefix}candidate_risk_rule_status."
                    f"evidence_status_summary.{status_name}"
                )
        if evidence_status_summary.get("missing_evidence_explicit") is not True:
            missing.append(
                f"{field_prefix}candidate_risk_rule_status."
                "evidence_status_summary.missing_evidence_explicit"
            )
        if not isinstance(
            evidence_status_summary.get("status_categories"),
            list,
        ) or set(evidence_status_summary.get("status_categories", [])) != {
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        }:
            missing.append(
                f"{field_prefix}candidate_risk_rule_status."
                "evidence_status_summary.status_categories"
            )
    if selected_action not in status.get("next_risk_rule_closure_actions", []):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status."
            "selected_next_safe_action.in_next_risk_rule_closure_actions"
        )

    summaries = status.get("candidate_risk_rule_summaries")
    if not isinstance(summaries, list) or not summaries:
        missing.append(
            f"{field_prefix}candidate_risk_rule_status."
            "candidate_risk_rule_summaries"
        )
        return missing
    if status.get("candidate_family_count") != len(summaries):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status.candidate_family_count"
        )
    if status.get("candidate_scope_count") != len(summaries):
        missing.append(
            f"{field_prefix}candidate_risk_rule_status.candidate_scope_count"
        )
    shared_risk_rule_gaps = status.get("shared_risk_rule_gaps")
    if isinstance(shared_risk_rule_gaps, list):
        if status.get("shared_scope_count") != len(shared_risk_rule_gaps):
            missing.append(
                f"{field_prefix}candidate_risk_rule_status.shared_scope_count"
            )
    candidate_ids: set[str] = set()
    for index, summary in enumerate(summaries):
        summary_prefix = (
            f"{field_prefix}candidate_risk_rule_status."
            f"candidate_risk_rule_summaries[{index}]"
        )
        if not isinstance(summary, Mapping):
            missing.append(summary_prefix)
            continue
        for field_name in _REQUIRED_CANDIDATE_RISK_RULE_SUMMARY_FIELDS:
            if field_name not in summary:
                missing.append(f"{summary_prefix}.{field_name}")
        candidate_id = str(summary.get("candidate_family_id", ""))
        candidate_ids.add(candidate_id)
        if summary.get("candidate_family") != candidate_id:
            missing.append(f"{summary_prefix}.candidate_family")
        if summary.get("risk_rule_status") != "incomplete":
            missing.append(f"{summary_prefix}.risk_rule_status")
        if summary.get("risk_rule_evidence_status") not in {
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        }:
            missing.append(f"{summary_prefix}.risk_rule_evidence_status")
        for false_field in (
            "risk_rule_defined",
            "position_sizing_defined",
            "max_loss_or_drawdown_rule_defined",
            "entry_exit_risk_boundary_defined",
            "stop_or_deactivation_rule_defined",
            "data_quality_risk_rule_defined",
        ):
            if summary.get(false_field) is not False:
                missing.append(f"{summary_prefix}.{false_field}.false")
        for list_field in (
            "promotion_blockers",
            "missing_risk_rule_evidence",
        ):
            if not isinstance(summary.get(list_field), list) or not summary.get(
                list_field
            ):
                missing.append(f"{summary_prefix}.{list_field}")
        missing_evidence = summary.get("missing_risk_rule_evidence", [])
        missing_text = " ".join(str(item) for item in missing_evidence)
        if "candidate_risk_rule_status" not in missing_text:
            missing.append(f"{summary_prefix}.missing_risk_rule_evidence.explicit")
        breakdown = summary.get("evidence_status_breakdown")
        if not isinstance(breakdown, Mapping):
            missing.append(f"{summary_prefix}.evidence_status_breakdown")
        else:
            for status_name in (
                "complete",
                "incomplete",
                "blocked",
                "not_applicable",
            ):
                if not isinstance(breakdown.get(status_name), list):
                    missing.append(
                        f"{summary_prefix}.evidence_status_breakdown."
                        f"{status_name}"
                    )
            if (
                summary.get("risk_rule_evidence_status") == "blocked"
                and not breakdown.get("blocked")
            ):
                missing.append(
                    f"{summary_prefix}.evidence_status_breakdown.blocked.explicit"
                )
            if not breakdown.get("incomplete") and not breakdown.get("blocked"):
                missing.append(
                    f"{summary_prefix}.evidence_status_breakdown."
                    "missing_evidence.explicit"
                )
        if not str(summary.get("recommended_closure_action", "")).startswith(
            f"close_{candidate_id}_risk_rule_definition_gap"
        ):
            missing.append(f"{summary_prefix}.recommended_closure_action")
        if not str(summary.get("expected_evidence_artifact", "")).endswith(
            "_risk_spec_packet"
        ):
            missing.append(f"{summary_prefix}.expected_evidence_artifact")
    for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS:
        if candidate_id not in candidate_ids:
            missing.append(
                f"{field_prefix}candidate_risk_rule_status."
                f"candidate_risk_rule_summaries.{candidate_id}"
            )
    serialized = json.dumps(
        _json_safe(status),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    for forbidden in (
        "paper_submit_authorized\":true",
        "live_trading_authorized",
        "broker_state_observed\":true",
        "risk_rule_status\":\"complete\"",
    ):
        if forbidden in serialized:
            missing.append(
                f"{field_prefix}candidate_risk_rule_status.forbidden.{forbidden}"
            )
    return missing


def _missing_candidate_signal_rule_status_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    status = packet.get("candidate_signal_rule_status")
    if not isinstance(status, Mapping):
        return [f"{field_prefix}candidate_signal_rule_status"]
    for field_name in _REQUIRED_CANDIDATE_SIGNAL_RULE_STATUS_FIELDS:
        if field_name not in status:
            missing.append(f"{field_prefix}candidate_signal_rule_status.{field_name}")
    if not str(packet.get("candidate_signal_rule_status_path", "")).endswith(
        _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME
    ):
        missing.append(f"{field_prefix}candidate_signal_rule_status_path")
    expected_values = {
        "signal_rule_status_version": _CANDIDATE_SIGNAL_RULE_STATUS_VERSION,
        "signal_rule_status": "ready",
        "signal_rule_status_mode": "offline_candidate_signal_rule_status_only",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "source_queue_item_id": _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
        "source_action_id": _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_ACTION_ID,
        "source_gap_id": "candidate_signal_rule_status",
        "source_candidate_family_id": (
            _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID
        ),
        "source_candidate_family": _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_CANDIDATE_FAMILY,
        "source_gap_status": "blocked",
        "source_gap_group_id": "strategy_definition_gaps",
        "source_gap_group_label": "Strategy definition gaps",
        "source_closure_action": "close_strategy_definition_gaps",
        "source_expected_evidence_artifact": _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME,
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "daniel_action_required_now": False,
        "profit_claim": "none",
        "safety_scope": "offline_only",
    }
    for field_name, expected_value in expected_values.items():
        if status.get(field_name) != expected_value:
            missing.append(f"{field_prefix}candidate_signal_rule_status.{field_name}")
    selected_action = str(status.get("selected_next_safe_action", ""))
    if _selector_contains_forbidden_action(selected_action):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "selected_next_safe_action.safe"
        )
    if not selected_action.startswith("execute_candidate_gap_closure_queue_item_"):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "selected_next_safe_action.concrete_item"
        )
    if selected_action != _CANDIDATE_SIGNAL_RULE_STATUS_NEXT_ACTION_ID:
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "selected_next_safe_action.advanced"
        )
    if (
        _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME
        not in str(status.get("source_closure_objective", ""))
        or "offline" not in str(status.get("source_closure_objective", "")).lower()
    ):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status.source_closure_objective"
        )
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        if label not in status.get("safety_labels", []):
            missing.append(
                f"{field_prefix}candidate_signal_rule_status.safety_labels.{label}"
            )
    for list_field in (
        "candidate_signal_rule_summaries",
        "shared_signal_rule_gaps",
        "highest_priority_signal_rule_gaps",
        "signal_rule_acceptance_criteria",
        "next_signal_rule_closure_actions",
        "safety_labels",
    ):
        if not isinstance(status.get(list_field), list) or not status.get(list_field):
            missing.append(f"{field_prefix}candidate_signal_rule_status.{list_field}")
    target_summary = status.get("target_candidate_signal_rule_summary")
    if not isinstance(target_summary, Mapping):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "target_candidate_signal_rule_summary"
        )
    elif (
        target_summary.get("candidate_family_id")
        != _CANDIDATE_SIGNAL_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID
    ):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "target_candidate_signal_rule_summary.candidate_family_id"
        )
    target_explicit_evidence = status.get("target_explicit_signal_rule_evidence")
    if not isinstance(target_explicit_evidence, Mapping):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "target_explicit_signal_rule_evidence"
        )
    elif target_explicit_evidence.get("explicit_signal_rules_present") is not False:
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "target_explicit_signal_rule_evidence.explicit_signal_rules_present"
        )
    target_materialized_specification = status.get(
        "target_materialized_candidate_signal_specification"
    )
    if not isinstance(target_materialized_specification, Mapping):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "target_materialized_candidate_signal_specification"
        )
    else:
        if target_materialized_specification.get("implementation_status") != (
            "not_implemented"
        ):
            missing.append(
                f"{field_prefix}candidate_signal_rule_status."
                "target_materialized_candidate_signal_specification."
                "implementation_status"
            )
        if target_materialized_specification.get("promotion_status") != "not_promoted":
            missing.append(
                f"{field_prefix}candidate_signal_rule_status."
                "target_materialized_candidate_signal_specification."
                "promotion_status"
            )
        if target_materialized_specification.get("paper_submit_authorized") is not False:
            missing.append(
                f"{field_prefix}candidate_signal_rule_status."
                "target_materialized_candidate_signal_specification."
                "paper_submit_authorized"
            )
        materialized_rules = target_materialized_specification.get(
            "materialized_signal_rules"
        )
        if not isinstance(materialized_rules, list) or materialized_rules:
            missing.append(
                f"{field_prefix}candidate_signal_rule_status."
                "target_materialized_candidate_signal_specification."
                "materialized_signal_rules"
            )
    target_remaining_missing_evidence = status.get(
        "target_remaining_missing_signal_rule_evidence"
    )
    if (
        not isinstance(target_remaining_missing_evidence, list)
        or not target_remaining_missing_evidence
    ):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "target_remaining_missing_signal_rule_evidence"
        )
    target_readiness = status.get("target_candidate_signal_readiness")
    if not isinstance(target_readiness, Mapping):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "target_candidate_signal_readiness"
        )
    elif target_readiness.get("readiness_status") not in {
        "research_ready",
        "evidence_ready",
        "blocked",
        "not_ready",
        "not_applicable",
    }:
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "target_candidate_signal_readiness.readiness_status"
        )
    evidence_status_summary = status.get("evidence_status_summary")
    if not isinstance(evidence_status_summary, Mapping):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status.evidence_status_summary"
        )
    else:
        for status_name in (
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        ):
            if not isinstance(evidence_status_summary.get(status_name), int):
                missing.append(
                    f"{field_prefix}candidate_signal_rule_status."
                    f"evidence_status_summary.{status_name}"
                )
        if evidence_status_summary.get("missing_evidence_explicit") is not True:
            missing.append(
                f"{field_prefix}candidate_signal_rule_status."
                "evidence_status_summary.missing_evidence_explicit"
            )
        if not isinstance(
            evidence_status_summary.get("status_categories"),
            list,
        ) or set(evidence_status_summary.get("status_categories", [])) != {
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        }:
            missing.append(
                f"{field_prefix}candidate_signal_rule_status."
                "evidence_status_summary.status_categories"
            )
    if selected_action not in status.get("next_signal_rule_closure_actions", []):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "selected_next_safe_action.in_next_signal_rule_closure_actions"
        )

    summaries = status.get("candidate_signal_rule_summaries")
    if not isinstance(summaries, list) or not summaries:
        missing.append(
            f"{field_prefix}candidate_signal_rule_status."
            "candidate_signal_rule_summaries"
        )
        return missing
    if status.get("candidate_family_count") != len(summaries):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status.candidate_family_count"
        )
    if status.get("candidate_scope_count") != len(summaries):
        missing.append(
            f"{field_prefix}candidate_signal_rule_status.candidate_scope_count"
        )
    shared_signal_rule_gaps = status.get("shared_signal_rule_gaps")
    if isinstance(shared_signal_rule_gaps, list):
        if status.get("shared_scope_count") != len(shared_signal_rule_gaps):
            missing.append(
                f"{field_prefix}candidate_signal_rule_status.shared_scope_count"
            )
    candidate_ids: set[str] = set()
    for index, summary in enumerate(summaries):
        summary_prefix = (
            f"{field_prefix}candidate_signal_rule_status."
            f"candidate_signal_rule_summaries[{index}]"
        )
        if not isinstance(summary, Mapping):
            missing.append(summary_prefix)
            continue
        for field_name in _REQUIRED_CANDIDATE_SIGNAL_RULE_SUMMARY_FIELDS:
            if field_name not in summary:
                missing.append(f"{summary_prefix}.{field_name}")
        candidate_id = str(summary.get("candidate_family_id", ""))
        candidate_ids.add(candidate_id)
        if summary.get("candidate_family") != candidate_id:
            missing.append(f"{summary_prefix}.candidate_family")
        if summary.get("signal_rule_status") != "incomplete":
            missing.append(f"{summary_prefix}.signal_rule_status")
        if summary.get("signal_rule_evidence_status") not in {
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        }:
            missing.append(f"{summary_prefix}.signal_rule_evidence_status")
        for false_field in (
            "signal_rule_defined",
            "signal_inputs_defined",
            "indicator_or_feature_definition_defined",
            "entry_rule_defined",
            "exit_rule_defined",
            "lookback_or_parameter_bounds_defined",
            "data_basis_defined",
            "universe_defined",
            "rebalance_or_evaluation_schedule_defined",
            "leakage_or_lookahead_guard_defined",
        ):
            if summary.get(false_field) is not False:
                missing.append(f"{summary_prefix}.{false_field}.false")
        for list_field in (
            "promotion_blockers",
            "missing_signal_rule_evidence",
            "remaining_missing_signal_rule_evidence",
        ):
            if not isinstance(summary.get(list_field), list) or not summary.get(
                list_field
            ):
                missing.append(f"{summary_prefix}.{list_field}")
        missing_evidence = summary.get("missing_signal_rule_evidence", [])
        missing_text = " ".join(str(item) for item in missing_evidence)
        if "candidate_signal_rule_status" not in missing_text:
            missing.append(f"{summary_prefix}.missing_signal_rule_evidence.explicit")
        if summary.get("remaining_missing_signal_rule_evidence") != missing_evidence:
            missing.append(
                f"{summary_prefix}.remaining_missing_signal_rule_evidence.matches"
            )
        explicit_evidence = summary.get("explicit_signal_rule_evidence")
        if not isinstance(explicit_evidence, Mapping):
            missing.append(f"{summary_prefix}.explicit_signal_rule_evidence")
        else:
            if explicit_evidence.get("evidence_mode") != (
                "deterministic_local_packet_evidence_only"
            ):
                missing.append(
                    f"{summary_prefix}.explicit_signal_rule_evidence.evidence_mode"
                )
            if explicit_evidence.get("explicit_signal_rules_present") is not False:
                missing.append(
                    f"{summary_prefix}.explicit_signal_rule_evidence."
                    "explicit_signal_rules_present"
                )
            if not isinstance(
                explicit_evidence.get("local_evidence_items"),
                list,
            ) or not explicit_evidence.get("local_evidence_items"):
                missing.append(
                    f"{summary_prefix}.explicit_signal_rule_evidence."
                    "local_evidence_items"
                )
        materialized_specification = summary.get(
            "materialized_candidate_signal_specification"
        )
        if not isinstance(materialized_specification, Mapping):
            missing.append(
                f"{summary_prefix}.materialized_candidate_signal_specification"
            )
        else:
            if materialized_specification.get("implementation_status") != (
                "not_implemented"
            ):
                missing.append(
                    f"{summary_prefix}.materialized_candidate_signal_specification."
                    "implementation_status"
                )
            if materialized_specification.get("promotion_status") != "not_promoted":
                missing.append(
                    f"{summary_prefix}.materialized_candidate_signal_specification."
                    "promotion_status"
                )
            if materialized_specification.get("broker_state_mode") != (
                "broker_state_not_observed"
            ):
                missing.append(
                    f"{summary_prefix}.materialized_candidate_signal_specification."
                    "broker_state_mode"
                )
            if materialized_specification.get("paper_submit_authorized") is not False:
                missing.append(
                    f"{summary_prefix}.materialized_candidate_signal_specification."
                    "paper_submit_authorized"
                )
            materialized_rules = materialized_specification.get(
                "materialized_signal_rules"
            )
            if not isinstance(materialized_rules, list) or materialized_rules:
                missing.append(
                    f"{summary_prefix}.materialized_candidate_signal_specification."
                    "materialized_signal_rules"
                )
        readiness = summary.get("candidate_signal_readiness")
        if not isinstance(readiness, Mapping):
            missing.append(f"{summary_prefix}.candidate_signal_readiness")
        else:
            if readiness.get("readiness_status") not in {
                "research_ready",
                "evidence_ready",
                "blocked",
                "not_ready",
                "not_applicable",
            }:
                missing.append(
                    f"{summary_prefix}.candidate_signal_readiness.readiness_status"
                )
            for bool_field in ("research_ready", "evidence_ready", "still_blocked"):
                if not isinstance(readiness.get(bool_field), bool):
                    missing.append(
                        f"{summary_prefix}.candidate_signal_readiness."
                        f"{bool_field}"
                    )
        breakdown = summary.get("evidence_status_breakdown")
        if not isinstance(breakdown, Mapping):
            missing.append(f"{summary_prefix}.evidence_status_breakdown")
        else:
            for status_name in (
                "complete",
                "incomplete",
                "blocked",
                "not_applicable",
            ):
                if not isinstance(breakdown.get(status_name), list):
                    missing.append(
                        f"{summary_prefix}.evidence_status_breakdown."
                        f"{status_name}"
                    )
            if (
                summary.get("signal_rule_evidence_status") == "blocked"
                and not breakdown.get("blocked")
            ):
                missing.append(
                    f"{summary_prefix}.evidence_status_breakdown.blocked.explicit"
                )
            if not breakdown.get("incomplete") and not breakdown.get("blocked"):
                missing.append(
                    f"{summary_prefix}.evidence_status_breakdown."
                    "missing_evidence.explicit"
                )
        if not str(summary.get("recommended_closure_action", "")).startswith(
            f"close_{candidate_id}_signal_rule_definition_gap"
        ):
            missing.append(f"{summary_prefix}.recommended_closure_action")
        if not str(summary.get("expected_evidence_artifact", "")).endswith(
            "_signal_spec_packet"
        ):
            missing.append(f"{summary_prefix}.expected_evidence_artifact")
    for candidate_id in _REQUIRED_CANDIDATE_FAMILY_IDS:
        if candidate_id not in candidate_ids:
            missing.append(
                f"{field_prefix}candidate_signal_rule_status."
                f"candidate_signal_rule_summaries.{candidate_id}"
            )
    serialized = json.dumps(
        _json_safe(status),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    for forbidden in (
        "paper_submit_authorized\":true",
        "live_trading_authorized",
        "broker_state_observed\":true",
        "signal_rule_status\":\"complete\"",
    ):
        if forbidden in serialized:
            missing.append(
                f"{field_prefix}candidate_signal_rule_status.forbidden.{forbidden}"
            )
    return missing


def _missing_shared_risk_rule_status_fields(
    prefix: str,
    packet: Mapping[str, Any],
) -> list[str]:
    field_prefix = f"{prefix}." if prefix else ""
    missing: list[str] = []
    status = packet.get("shared_risk_rule_status")
    if not isinstance(status, Mapping):
        return [f"{field_prefix}shared_risk_rule_status"]
    for field_name in _REQUIRED_SHARED_RISK_RULE_STATUS_FIELDS:
        if field_name not in status:
            missing.append(f"{field_prefix}shared_risk_rule_status.{field_name}")
    if not str(packet.get("shared_risk_rule_status_path", "")).endswith(
        _SHARED_RISK_RULE_STATUS_FILENAME
    ):
        missing.append(f"{field_prefix}shared_risk_rule_status_path")
    expected_values = {
        "shared_risk_rule_status_version": _SHARED_RISK_RULE_STATUS_VERSION,
        "shared_risk_rule_status": "ready",
        "shared_risk_rule_status_mode": "offline_shared_risk_rule_status_only",
        "deterministic_scope": "shared_candidate_risk_rule_status",
        "baseline_strategy_id": "spy_sma_50_200_control",
        "source_queue_item_id": _SHARED_RISK_RULE_STATUS_SOURCE_QUEUE_ITEM_ID,
        "source_action_id": _SHARED_RISK_RULE_STATUS_SOURCE_ACTION_ID,
        "source_gap_id": "risk_rule_status",
        "source_candidate_family_id": (
            _SHARED_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY_ID
        ),
        "source_candidate_family": _SHARED_RISK_RULE_STATUS_SOURCE_CANDIDATE_FAMILY,
        "source_gap_status": "blocked",
        "source_gap_group_id": "strategy_definition_gaps",
        "source_gap_group_label": "Strategy definition gaps",
        "source_closure_action": "close_strategy_definition_gaps",
        "source_expected_evidence_artifact": _SHARED_RISK_RULE_STATUS_FILENAME,
        "broker_state_mode": "broker_state_not_observed",
        "paper_submit_authorized": False,
        "daniel_action_required_now": False,
        "profit_claim": "none",
        "safety_scope": "offline_only",
    }
    for field_name, expected_value in expected_values.items():
        if status.get(field_name) != expected_value:
            missing.append(f"{field_prefix}shared_risk_rule_status.{field_name}")
    selected_action = str(status.get("selected_next_safe_action", ""))
    if _selector_contains_forbidden_action(selected_action):
        missing.append(
            f"{field_prefix}shared_risk_rule_status."
            "selected_next_safe_action.safe"
        )
    if selected_action != _SHARED_RISK_RULE_STATUS_NEXT_ACTION_ID:
        missing.append(
            f"{field_prefix}shared_risk_rule_status."
            "selected_next_safe_action.advanced"
        )
    if selected_action not in status.get("next_shared_risk_rule_closure_actions", []):
        missing.append(
            f"{field_prefix}shared_risk_rule_status."
            "selected_next_safe_action.in_next_shared_risk_rule_closure_actions"
        )
    if (
        _SHARED_RISK_RULE_STATUS_FILENAME
        not in str(status.get("source_closure_objective", ""))
        or "offline" not in str(status.get("source_closure_objective", "")).lower()
    ):
        missing.append(
            f"{field_prefix}shared_risk_rule_status.source_closure_objective"
        )
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        if label not in status.get("safety_labels", []):
            missing.append(
                f"{field_prefix}shared_risk_rule_status.safety_labels.{label}"
            )
    for list_field in (
        "shared_risk_rule_gaps",
        "candidate_risk_rule_summaries",
        "remaining_missing_shared_risk_evidence",
        "highest_priority_remaining_gaps",
        "shared_risk_rule_acceptance_criteria",
        "next_shared_risk_rule_closure_actions",
        "safety_labels",
    ):
        if not isinstance(status.get(list_field), list) or not status.get(list_field):
            missing.append(f"{field_prefix}shared_risk_rule_status.{list_field}")
    if status.get("candidate_family_count") != len(
        status.get("candidate_risk_rule_summaries", [])
    ):
        missing.append(
            f"{field_prefix}shared_risk_rule_status.candidate_family_count"
        )
    if status.get("shared_scope_count") != len(
        status.get("shared_risk_rule_gaps", [])
    ):
        missing.append(f"{field_prefix}shared_risk_rule_status.shared_scope_count")
    status_item = status.get("shared_risk_rule_status_item")
    if not isinstance(status_item, Mapping):
        missing.append(
            f"{field_prefix}shared_risk_rule_status.shared_risk_rule_status_item"
        )
    else:
        if status_item.get("shared_status_id") != "risk_rule_status":
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "shared_risk_rule_status_item.shared_status_id"
            )
        if status_item.get("status") != "blocked":
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "shared_risk_rule_status_item.status"
            )
    explicit_evidence = status.get("explicit_shared_risk_rule_evidence")
    if not isinstance(explicit_evidence, Mapping):
        missing.append(
            f"{field_prefix}shared_risk_rule_status."
            "explicit_shared_risk_rule_evidence"
        )
    else:
        if explicit_evidence.get("evidence_mode") != (
            "deterministic_local_packet_evidence_only"
        ):
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "explicit_shared_risk_rule_evidence.evidence_mode"
            )
        if explicit_evidence.get("explicit_risk_rules_present") is not False:
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "explicit_shared_risk_rule_evidence.explicit_risk_rules_present"
            )
        if explicit_evidence.get("evidence_status") not in {
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        }:
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "explicit_shared_risk_rule_evidence.evidence_status"
            )
        if not isinstance(
            explicit_evidence.get("local_evidence_items"),
            list,
        ) or not explicit_evidence.get("local_evidence_items"):
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "explicit_shared_risk_rule_evidence.local_evidence_items"
            )
    for bucket_name in (
        "position_sizing_evidence",
        "stop_or_exit_evidence",
        "drawdown_or_exposure_control_evidence",
        "portfolio_or_risk_cap_evidence",
    ):
        bucket = status.get(bucket_name)
        if not isinstance(bucket, Mapping):
            missing.append(f"{field_prefix}shared_risk_rule_status.{bucket_name}")
            continue
        if bucket.get("evidence_mode") != "deterministic_local_packet_evidence_only":
            missing.append(
                f"{field_prefix}shared_risk_rule_status.{bucket_name}.evidence_mode"
            )
        if bucket.get("explicit_rules_present") is not False:
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                f"{bucket_name}.explicit_rules_present"
            )
        if not isinstance(bucket.get("candidate_evidence"), list):
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                f"{bucket_name}.candidate_evidence"
            )
    materialized = status.get("materialized_shared_risk_specification")
    if not isinstance(materialized, Mapping):
        missing.append(
            f"{field_prefix}shared_risk_rule_status."
            "materialized_shared_risk_specification"
        )
    else:
        for false_field in ("explicit_risk_rules_present", "paper_submit_authorized"):
            if materialized.get(false_field) is not False:
                missing.append(
                    f"{field_prefix}shared_risk_rule_status."
                    f"materialized_shared_risk_specification.{false_field}"
                )
        for empty_list_field in (
            "materialized_risk_rules",
            "position_sizing_rules",
            "stop_or_exit_rules",
            "drawdown_or_exposure_controls",
            "portfolio_or_risk_cap_rules",
        ):
            if (
                not isinstance(materialized.get(empty_list_field), list)
                or materialized.get(empty_list_field)
            ):
                missing.append(
                    f"{field_prefix}shared_risk_rule_status."
                    "materialized_shared_risk_specification."
                    f"{empty_list_field}"
                )
        if materialized.get("implementation_status") != "not_implemented":
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "materialized_shared_risk_specification.implementation_status"
            )
        if materialized.get("promotion_status") != "not_promoted":
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "materialized_shared_risk_specification.promotion_status"
            )
    readiness = status.get("target_shared_risk_readiness")
    if not isinstance(readiness, Mapping):
        missing.append(
            f"{field_prefix}shared_risk_rule_status.target_shared_risk_readiness"
        )
    else:
        if readiness.get("readiness_status") not in {
            "research_ready",
            "evidence_ready",
            "blocked",
            "not_ready",
            "not_applicable",
        }:
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "target_shared_risk_readiness.readiness_status"
            )
        for bool_field in ("research_ready", "evidence_ready", "still_blocked"):
            if not isinstance(readiness.get(bool_field), bool):
                missing.append(
                    f"{field_prefix}shared_risk_rule_status."
                    f"target_shared_risk_readiness.{bool_field}"
                )
    target_status = status.get("target_shared_risk_status")
    if not isinstance(target_status, Mapping):
        missing.append(
            f"{field_prefix}shared_risk_rule_status.target_shared_risk_status"
        )
    elif target_status.get("status") not in {
        "complete",
        "incomplete",
        "blocked",
        "not_applicable",
    }:
        missing.append(
            f"{field_prefix}shared_risk_rule_status.target_shared_risk_status.status"
        )
    evidence_status_summary = status.get("evidence_status_summary")
    if not isinstance(evidence_status_summary, Mapping):
        missing.append(
            f"{field_prefix}shared_risk_rule_status.evidence_status_summary"
        )
    else:
        for status_name in (
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        ):
            if not isinstance(evidence_status_summary.get(status_name), int):
                missing.append(
                    f"{field_prefix}shared_risk_rule_status."
                    f"evidence_status_summary.{status_name}"
                )
        if evidence_status_summary.get("shared_scope_status") not in {
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        }:
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "evidence_status_summary.shared_scope_status"
            )
        if evidence_status_summary.get("shared_missing_evidence_explicit") is not True:
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                "evidence_status_summary.shared_missing_evidence_explicit"
            )
    remaining = status.get("remaining_missing_shared_risk_evidence", [])
    remaining_text = " ".join(str(item) for item in remaining)
    for required_fragment in (
        "shared_risk_rule_status",
        "shared_risk_rule_gap_status",
        "shared_risk_rule_blocker",
    ):
        if required_fragment not in remaining_text:
            missing.append(
                f"{field_prefix}shared_risk_rule_status."
                f"remaining_missing_shared_risk_evidence.{required_fragment}"
            )
    serialized = json.dumps(
        _json_safe(status),
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    for forbidden in (
        "paper_submit_authorized\":true",
        "live_trading_authorized",
        "broker_state_observed\":true",
        "materialized_risk_rules\":[{",
    ):
        if forbidden in serialized:
            missing.append(
                f"{field_prefix}shared_risk_rule_status.forbidden.{forbidden}"
            )
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
        "strategy_comparison_scaffold_path",
        "strategy_comparison_scaffold",
        "candidate_strategy_evidence_template_path",
        "candidate_strategy_evidence_template",
        "candidate_evidence_requirements_path",
        "candidate_evidence_requirements",
        "candidate_evidence_collection_plan_path",
        "candidate_evidence_collection_plan",
        "candidate_evidence_collection_status_path",
        "candidate_evidence_collection_status",
        "candidate_evidence_gap_summary_path",
        "candidate_evidence_gap_summary",
        "candidate_gap_closure_queue_path",
        "candidate_gap_closure_queue",
        "candidate_risk_rule_status_path",
        "candidate_risk_rule_status",
        "candidate_signal_rule_status_path",
        "candidate_signal_rule_status",
        "shared_risk_rule_status_path",
        "shared_risk_rule_status",
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
    if not str(selector.get("strategy_comparison_scaffold_path", "")).endswith(
        _STRATEGY_COMPARISON_SCAFFOLD_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector.strategy_comparison_scaffold_path"
        )
    if not isinstance(selector.get("strategy_comparison_scaffold"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector.strategy_comparison_scaffold.object"
        )
    if not str(selector.get("candidate_strategy_evidence_template_path", "")).endswith(
        _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_strategy_evidence_template_path"
        )
    if not isinstance(selector.get("candidate_strategy_evidence_template"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_strategy_evidence_template.object"
        )
    if not str(selector.get("candidate_evidence_requirements_path", "")).endswith(
        _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_evidence_requirements_path"
        )
    if not isinstance(selector.get("candidate_evidence_requirements"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_evidence_requirements.object"
        )
    if not str(selector.get("candidate_evidence_collection_plan_path", "")).endswith(
        _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_evidence_collection_plan_path"
        )
    if not isinstance(selector.get("candidate_evidence_collection_plan"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_evidence_collection_plan.object"
        )
    if not str(selector.get("candidate_evidence_collection_status_path", "")).endswith(
        _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_evidence_collection_status_path"
        )
    if not isinstance(selector.get("candidate_evidence_collection_status"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_evidence_collection_status.object"
        )
    if not str(selector.get("candidate_evidence_gap_summary_path", "")).endswith(
        _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_evidence_gap_summary_path"
        )
    if not isinstance(selector.get("candidate_evidence_gap_summary"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_evidence_gap_summary.object"
        )
    if not str(selector.get("candidate_gap_closure_queue_path", "")).endswith(
        _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_gap_closure_queue_path"
        )
    if not isinstance(selector.get("candidate_gap_closure_queue"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_gap_closure_queue.object"
        )
    if not str(selector.get("candidate_risk_rule_status_path", "")).endswith(
        _CANDIDATE_RISK_RULE_STATUS_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_risk_rule_status_path"
        )
    if not isinstance(selector.get("candidate_risk_rule_status"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_risk_rule_status.object"
        )
    if not str(selector.get("candidate_signal_rule_status_path", "")).endswith(
        _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_signal_rule_status_path"
        )
    if not isinstance(selector.get("candidate_signal_rule_status"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "candidate_signal_rule_status.object"
        )
    if not str(selector.get("shared_risk_rule_status_path", "")).endswith(
        _SHARED_RISK_RULE_STATUS_FILENAME
    ):
        missing.append(
            f"{field_prefix}next_action_selector."
            "shared_risk_rule_status_path"
        )
    if not isinstance(selector.get("shared_risk_rule_status"), Mapping):
        missing.append(
            f"{field_prefix}next_action_selector."
            "shared_risk_rule_status.object"
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
        "strategy_comparison_scaffold_path",
        "strategy_comparison_scaffold",
        "strategy_comparison_scaffold_status",
        "candidate_strategy_evidence_template_path",
        "candidate_strategy_evidence_template",
        "candidate_strategy_evidence_template_status",
        "candidate_evidence_requirements_path",
        "candidate_evidence_requirements",
        "candidate_evidence_requirements_status",
        "candidate_evidence_collection_plan_path",
        "candidate_evidence_collection_plan",
        "candidate_evidence_collection_plan_status",
        "candidate_evidence_collection_status_path",
        "candidate_evidence_collection_status",
        "candidate_evidence_collection_status_status",
        "candidate_evidence_gap_summary_path",
        "candidate_evidence_gap_summary",
        "candidate_evidence_gap_summary_status",
        "candidate_gap_closure_queue_path",
        "candidate_gap_closure_queue",
        "candidate_gap_closure_queue_status",
        "candidate_gap_closure_queue_selected_item_id",
        "candidate_gap_closure_queue_selected_next_safe_action",
        "candidate_risk_rule_status_path",
        "candidate_risk_rule_status",
        "candidate_risk_rule_status_status",
        "candidate_risk_rule_status_selected_next_safe_action",
        "candidate_signal_rule_status_path",
        "candidate_signal_rule_status",
        "candidate_signal_rule_status_status",
        "candidate_signal_rule_status_selected_next_safe_action",
        "shared_risk_rule_status_path",
        "shared_risk_rule_status",
        "shared_risk_rule_status_status",
        "shared_risk_rule_status_selected_next_safe_action",
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
    if not str(exports.get("strategy_comparison_scaffold_path", "")).endswith(
        _STRATEGY_COMPARISON_SCAFFOLD_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports.strategy_comparison_scaffold_path"
        )
    if not isinstance(exports.get("strategy_comparison_scaffold"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports.strategy_comparison_scaffold.object"
        )
    if exports.get("strategy_comparison_scaffold_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports.strategy_comparison_scaffold_status"
        )
    if not str(exports.get("candidate_strategy_evidence_template_path", "")).endswith(
        _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_strategy_evidence_template_path"
        )
    if not isinstance(exports.get("candidate_strategy_evidence_template"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_strategy_evidence_template.object"
        )
    if exports.get("candidate_strategy_evidence_template_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_strategy_evidence_template_status"
        )
    if not str(exports.get("candidate_evidence_requirements_path", "")).endswith(
        _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_requirements_path"
        )
    if not isinstance(exports.get("candidate_evidence_requirements"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_requirements.object"
        )
    if exports.get("candidate_evidence_requirements_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_requirements_status"
        )
    if not str(exports.get("candidate_evidence_collection_plan_path", "")).endswith(
        _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_collection_plan_path"
        )
    if not isinstance(exports.get("candidate_evidence_collection_plan"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_collection_plan.object"
        )
    if exports.get("candidate_evidence_collection_plan_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_collection_plan_status"
        )
    if not str(exports.get("candidate_evidence_collection_status_path", "")).endswith(
        _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_collection_status_path"
        )
    if not isinstance(exports.get("candidate_evidence_collection_status"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_collection_status.object"
        )
    if exports.get("candidate_evidence_collection_status_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_collection_status_status"
        )
    if not str(exports.get("candidate_evidence_gap_summary_path", "")).endswith(
        _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_gap_summary_path"
        )
    if not isinstance(exports.get("candidate_evidence_gap_summary"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_gap_summary.object"
        )
    if exports.get("candidate_evidence_gap_summary_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_evidence_gap_summary_status"
        )
    if not str(exports.get("candidate_gap_closure_queue_path", "")).endswith(
        _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_gap_closure_queue_path"
        )
    if not isinstance(exports.get("candidate_gap_closure_queue"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_gap_closure_queue.object"
        )
    if exports.get("candidate_gap_closure_queue_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_gap_closure_queue_status"
        )
    if not str(
        exports.get("candidate_gap_closure_queue_selected_item_id", "")
    ).startswith("candidate_gap_closure_queue_item_"):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_gap_closure_queue_selected_item_id"
        )
    if not str(
        exports.get("candidate_gap_closure_queue_selected_next_safe_action", "")
    ).startswith("execute_candidate_gap_closure_queue_item_"):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_gap_closure_queue_selected_next_safe_action"
        )
    if not str(exports.get("candidate_risk_rule_status_path", "")).endswith(
        _CANDIDATE_RISK_RULE_STATUS_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports.candidate_risk_rule_status_path"
        )
    if not isinstance(exports.get("candidate_risk_rule_status"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports.candidate_risk_rule_status.object"
        )
    if exports.get("candidate_risk_rule_status_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports.candidate_risk_rule_status_status"
        )
    if not str(
        exports.get("candidate_risk_rule_status_selected_next_safe_action", "")
    ).startswith("execute_candidate_gap_closure_queue_item_"):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_risk_rule_status_selected_next_safe_action"
        )
    if not str(exports.get("candidate_signal_rule_status_path", "")).endswith(
        _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports.candidate_signal_rule_status_path"
        )
    if not isinstance(exports.get("candidate_signal_rule_status"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports.candidate_signal_rule_status.object"
        )
    if exports.get("candidate_signal_rule_status_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports.candidate_signal_rule_status_status"
        )
    if not str(
        exports.get("candidate_signal_rule_status_selected_next_safe_action", "")
    ).startswith("execute_candidate_gap_closure_queue_item_"):
        missing.append(
            f"{field_prefix}work_order_exports."
            "candidate_signal_rule_status_selected_next_safe_action"
        )
    if not str(exports.get("shared_risk_rule_status_path", "")).endswith(
        _SHARED_RISK_RULE_STATUS_FILENAME
    ):
        missing.append(
            f"{field_prefix}work_order_exports.shared_risk_rule_status_path"
        )
    if not isinstance(exports.get("shared_risk_rule_status"), Mapping):
        missing.append(
            f"{field_prefix}work_order_exports.shared_risk_rule_status.object"
        )
    if exports.get("shared_risk_rule_status_status") != "ready":
        missing.append(
            f"{field_prefix}work_order_exports.shared_risk_rule_status_status"
        )
    if not str(
        exports.get("shared_risk_rule_status_selected_next_safe_action", "")
    ).startswith("execute_candidate_gap_closure_queue_item_"):
        missing.append(
            f"{field_prefix}work_order_exports."
            "shared_risk_rule_status_selected_next_safe_action"
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
    if "## Candidate Gap Closure Queue" not in brief_text:
        missing.append("operating_brief.candidate_gap_closure_queue.section")
    gap_closure_queue = packet.get("candidate_gap_closure_queue")
    if isinstance(gap_closure_queue, Mapping):
        for field_name in (
            "queue_status",
            "queue_mode",
            "selected_queue_item_id",
            "selected_next_safe_action",
            "broker_state_mode",
            "profit_claim",
        ):
            value = gap_closure_queue.get(field_name)
            if _has_required_value(value) and str(value) not in brief_text:
                missing.append(
                    f"operating_brief.candidate_gap_closure_queue.{field_name}"
                )
    gap_closure_queue_path = packet.get("candidate_gap_closure_queue_path")
    if (
        _has_required_value(gap_closure_queue_path)
        and str(gap_closure_queue_path) not in brief_text
    ):
        missing.append("operating_brief.candidate_gap_closure_queue_path")
    if "## Candidate Risk Rule Status" not in brief_text:
        missing.append("operating_brief.candidate_risk_rule_status.section")
    risk_rule_status = packet.get("candidate_risk_rule_status")
    if isinstance(risk_rule_status, Mapping):
        for field_name in (
            "risk_rule_status",
            "risk_rule_status_mode",
            "source_queue_item_id",
            "source_gap_id",
            "source_candidate_family_id",
            "source_expected_evidence_artifact",
            "selected_next_safe_action",
            "broker_state_mode",
            "profit_claim",
        ):
            value = risk_rule_status.get(field_name)
            if _has_required_value(value) and str(value) not in brief_text:
                missing.append(
                    f"operating_brief.candidate_risk_rule_status.{field_name}"
                )
    risk_rule_status_path = packet.get("candidate_risk_rule_status_path")
    if (
        _has_required_value(risk_rule_status_path)
        and str(risk_rule_status_path) not in brief_text
    ):
        missing.append("operating_brief.candidate_risk_rule_status_path")

    if "## Candidate Signal Rule Status" not in brief_text:
        missing.append("operating_brief.candidate_signal_rule_status.section")
    signal_rule_status = packet.get("candidate_signal_rule_status")
    if isinstance(signal_rule_status, Mapping):
        for field_name in (
            "signal_rule_status",
            "signal_rule_status_mode",
            "source_queue_item_id",
            "source_gap_id",
            "source_candidate_family_id",
            "source_expected_evidence_artifact",
            "selected_next_safe_action",
            "broker_state_mode",
            "profit_claim",
        ):
            value = signal_rule_status.get(field_name)
            if _has_required_value(value) and str(value) not in brief_text:
                missing.append(
                    f"operating_brief.candidate_signal_rule_status.{field_name}"
                )
    signal_rule_status_path = packet.get("candidate_signal_rule_status_path")
    if (
        _has_required_value(signal_rule_status_path)
        and str(signal_rule_status_path) not in brief_text
    ):
        missing.append("operating_brief.candidate_signal_rule_status_path")

    if "## Shared Risk Rule Status" not in brief_text:
        missing.append("operating_brief.shared_risk_rule_status.section")
    shared_risk_rule_status = packet.get("shared_risk_rule_status")
    if isinstance(shared_risk_rule_status, Mapping):
        for field_name in (
            "shared_risk_rule_status",
            "shared_risk_rule_status_mode",
            "source_queue_item_id",
            "source_gap_id",
            "source_candidate_family_id",
            "source_expected_evidence_artifact",
            "selected_next_safe_action",
            "broker_state_mode",
            "profit_claim",
        ):
            value = shared_risk_rule_status.get(field_name)
            if _has_required_value(value) and str(value) not in brief_text:
                missing.append(
                    f"operating_brief.shared_risk_rule_status.{field_name}"
                )
    shared_risk_rule_status_path = packet.get("shared_risk_rule_status_path")
    if (
        _has_required_value(shared_risk_rule_status_path)
        and str(shared_risk_rule_status_path) not in brief_text
    ):
        missing.append("operating_brief.shared_risk_rule_status_path")

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
    scaffold = payload["strategy_comparison_scaffold"]
    scaffold_json = _json_markdown(scaffold)
    template = payload["candidate_strategy_evidence_template"]
    template_json = _json_markdown(template)
    requirements = payload["candidate_evidence_requirements"]
    requirements_json = _json_markdown(requirements)
    collection_plan = payload["candidate_evidence_collection_plan"]
    collection_plan_json = _json_markdown(collection_plan)
    collection_status = payload["candidate_evidence_collection_status"]
    collection_status_json = _json_markdown(collection_status)
    gap_summary = payload["candidate_evidence_gap_summary"]
    gap_summary_json = _json_markdown(gap_summary)
    gap_closure_queue = payload["candidate_gap_closure_queue"]
    gap_closure_queue_json = _json_markdown(gap_closure_queue)
    risk_rule_status = payload["candidate_risk_rule_status"]
    risk_rule_status_json = _json_markdown(risk_rule_status)
    signal_rule_status = payload["candidate_signal_rule_status"]
    signal_rule_status_json = _json_markdown(signal_rule_status)
    shared_risk_rule_status = payload["shared_risk_rule_status"]
    shared_risk_rule_status_json = _json_markdown(shared_risk_rule_status)
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

## Strategy comparison scaffold
* **Artifact**: `{payload["strategy_comparison_scaffold_path"]}`
* **Scaffold status**: `{scaffold["scaffold_status"]}`
* **Comparison mode**: `{scaffold["comparison_mode"]}`
* **Baseline strategy**: `{scaffold["baseline_strategy_id"]}`
* **Baseline role**: `{scaffold["baseline_strategy_role"]}`
* **Candidate slots**: {len(scaffold["candidate_strategy_slots"])}
* **Selected next safe action**: `{scaffold["selected_next_safe_action"]}`
* **Why no strategy replacement yet**: {scaffold["why_no_strategy_replacement_yet"]}
* **Safety scope**: `{scaffold["safety_scope"]}`
* **Broker-state mode**: `{scaffold["broker_state_mode"]}`
* **Paper submit authorized**: {str(scaffold["paper_submit_authorized"]).lower()}
* **Profit claim**: `{scaffold["profit_claim"]}`
```json
{scaffold_json}
```

## Candidate strategy evidence template
* **Artifact**: `{payload["candidate_strategy_evidence_template_path"]}`
* **Template status**: `{template["template_status"]}`
* **Evidence mode**: `{template["evidence_mode"]}`
* **Baseline strategy**: `{template["baseline_strategy_id"]}`
* **Baseline role**: `{template["baseline_strategy_role"]}`
* **Candidate families**: {len(template["candidate_families"])}
* **Selected next safe action**: `{template["selected_next_safe_action"]}`
* **Why no strategy implementation yet**: {template["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{template["safety_scope"]}`
* **Broker-state mode**: `{template["broker_state_mode"]}`
* **Paper submit authorized**: {str(template["paper_submit_authorized"]).lower()}
* **Profit claim**: `{template["profit_claim"]}`
```json
{template_json}
```

## Candidate Evidence Requirements
* **Artifact**: `{payload["candidate_evidence_requirements_path"]}`
* **Requirements status**: `{requirements["requirements_status"]}`
* **Requirements mode**: `{requirements["requirements_mode"]}`
* **Baseline strategy**: `{requirements["baseline_strategy_id"]}`
* **Baseline role**: `{requirements["baseline_strategy_role"]}`
* **Candidate requirements**: {len(requirements["candidate_requirements"])}
* **Selected next safe action**: `{requirements["selected_next_safe_action"]}`
* **Why no strategy implementation yet**: {requirements["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{requirements["safety_scope"]}`
* **Broker-state mode**: `{requirements["broker_state_mode"]}`
* **Paper submit authorized**: {str(requirements["paper_submit_authorized"]).lower()}
* **Profit claim**: `{requirements["profit_claim"]}`
```json
{requirements_json}
```

## Candidate Evidence Collection Plan
* **Artifact**: `{payload["candidate_evidence_collection_plan_path"]}`
* **Collection plan status**: `{collection_plan["collection_plan_status"]}`
* **Collection plan mode**: `{collection_plan["collection_plan_mode"]}`
* **Baseline strategy**: `{collection_plan["baseline_strategy_id"]}`
* **Baseline role**: `{collection_plan["baseline_strategy_role"]}`
* **Candidate collection plans**: {len(collection_plan["candidate_collection_plans"])}
* **Shared collection steps**: {collection_plan["shared_collection_steps"]}
* **Expected offline artifacts**: {collection_plan["expected_offline_artifacts"]}
* **Selected next safe action**: `{collection_plan["selected_next_safe_action"]}`
* **Why no strategy implementation yet**: {collection_plan["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{collection_plan["safety_scope"]}`
* **Broker-state mode**: `{collection_plan["broker_state_mode"]}`
* **Paper submit authorized**: {str(collection_plan["paper_submit_authorized"]).lower()}
* **Profit claim**: `{collection_plan["profit_claim"]}`
```json
{collection_plan_json}
```

## Candidate Evidence Collection Status
* **Artifact**: `{payload["candidate_evidence_collection_status_path"]}`
* **Collection status**: `{collection_status["collection_status"]}`
* **Collection status mode**: `{collection_status["collection_status_mode"]}`
* **Baseline strategy**: `{collection_status["baseline_strategy_id"]}`
* **Baseline role**: `{collection_status["baseline_strategy_role"]}`
* **Candidate statuses**: {len(collection_status["candidate_statuses"])}
* **Shared collection statuses**: {len(collection_status["shared_collection_status"])}
* **Evidence status counts**: {collection_status["evidence_status_counts"]}
* **Selected next safe action**: `{collection_status["selected_next_safe_action"]}`
* **Why no strategy implementation yet**: {collection_status["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{collection_status["safety_scope"]}`
* **Broker-state mode**: `{collection_status["broker_state_mode"]}`
* **Paper submit authorized**: {str(collection_status["paper_submit_authorized"]).lower()}
* **Profit claim**: `{collection_status["profit_claim"]}`
```json
{collection_status_json}
```

## Candidate Evidence Gap Summary
* **Artifact**: `{payload["candidate_evidence_gap_summary_path"]}`
* **Gap summary status**: `{gap_summary["gap_summary_status"]}`
* **Gap summary mode**: `{gap_summary["gap_summary_mode"]}`
* **Baseline strategy**: `{gap_summary["baseline_strategy_id"]}`
* **Baseline role**: `{gap_summary["baseline_strategy_role"]}`
* **Candidate gap summaries**: {len(gap_summary["candidate_gap_summaries"])}
* **Ranked gap groups**: {len(gap_summary["ranked_gap_groups"])}
* **Highest priority gaps**: {len(gap_summary["highest_priority_gaps"])}
* **Gap counts**: {gap_summary["gap_counts"]}
* **Selected next safe action**: `{gap_summary["selected_next_safe_action"]}`
* **Why no strategy implementation yet**: {gap_summary["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{gap_summary["safety_scope"]}`
* **Broker-state mode**: `{gap_summary["broker_state_mode"]}`
* **Paper submit authorized**: {str(gap_summary["paper_submit_authorized"]).lower()}
* **Profit claim**: `{gap_summary["profit_claim"]}`
```json
{gap_summary_json}
```

## Candidate Gap Closure Queue
* **Artifact**: `{payload["candidate_gap_closure_queue_path"]}`
* **Queue status**: `{gap_closure_queue["queue_status"]}`
* **Queue mode**: `{gap_closure_queue["queue_mode"]}`
* **Item count**: {gap_closure_queue["queue_item_count"]}
* **First queue item**: `{gap_closure_queue["selected_queue_item_id"]}`
* **Selected next safe action**: `{gap_closure_queue["selected_next_safe_action"]}`
* **Broker-state mode**: `{gap_closure_queue["broker_state_mode"]}`
* **Paper submit authorized**: {str(gap_closure_queue["paper_submit_authorized"]).lower()}
* **Daniel action required now**: {str(gap_closure_queue["daniel_action_required_now"]).lower()}
* **Profit claim**: `{gap_closure_queue["profit_claim"]}`
* **Safety scope**: `{gap_closure_queue["safety_scope"]}`
```json
{gap_closure_queue_json}
```

## Candidate Risk Rule Status
* **Artifact**: `{payload["candidate_risk_rule_status_path"]}`
* **Risk-rule status**: `{risk_rule_status["risk_rule_status"]}`
* **Risk-rule status mode**: `{risk_rule_status["risk_rule_status_mode"]}`
* **Source queue item**: `{risk_rule_status["source_queue_item_id"]}`
* **Source action**: `{risk_rule_status["source_action_id"]}`
* **Source gap**: `{risk_rule_status["source_gap_id"]}`
* **Source candidate**: `{risk_rule_status["source_candidate_family_id"]}`
* **Expected evidence artifact**: `{risk_rule_status["source_expected_evidence_artifact"]}`
* **Candidate families**: {risk_rule_status["candidate_family_count"]}
* **Candidate/shared scope count**: {risk_rule_status["candidate_scope_count"]}/{risk_rule_status["shared_scope_count"]}
* **Evidence status summary**: {risk_rule_status["evidence_status_summary"]}
* **Highest-priority risk-rule gaps**: {len(risk_rule_status["highest_priority_risk_rule_gaps"])}
* **Selected next safe action**: `{risk_rule_status["selected_next_safe_action"]}`
* **Broker-state mode**: `{risk_rule_status["broker_state_mode"]}`
* **Paper submit authorized**: {str(risk_rule_status["paper_submit_authorized"]).lower()}
* **Daniel action required now**: {str(risk_rule_status["daniel_action_required_now"]).lower()}
* **Profit claim**: `{risk_rule_status["profit_claim"]}`
* **Safety scope**: `{risk_rule_status["safety_scope"]}`
```json
{risk_rule_status_json}
```

## Candidate Signal Rule Status
* **Artifact**: `{payload["candidate_signal_rule_status_path"]}`
* **Signal-rule status**: `{signal_rule_status["signal_rule_status"]}`
* **Signal-rule status mode**: `{signal_rule_status["signal_rule_status_mode"]}`
* **Source queue item**: `{signal_rule_status["source_queue_item_id"]}`
* **Source action**: `{signal_rule_status["source_action_id"]}`
* **Source gap**: `{signal_rule_status["source_gap_id"]}`
* **Source candidate**: `{signal_rule_status["source_candidate_family_id"]}`
* **Expected evidence artifact**: `{signal_rule_status["source_expected_evidence_artifact"]}`
* **Candidate families**: {signal_rule_status["candidate_family_count"]}
* **Candidate/shared scope count**: {signal_rule_status["candidate_scope_count"]}/{signal_rule_status["shared_scope_count"]}
* **Evidence status summary**: {signal_rule_status["evidence_status_summary"]}
* **Highest-priority signal-rule gaps**: {len(signal_rule_status["highest_priority_signal_rule_gaps"])}
* **Selected next safe action**: `{signal_rule_status["selected_next_safe_action"]}`
* **Broker-state mode**: `{signal_rule_status["broker_state_mode"]}`
* **Paper submit authorized**: {str(signal_rule_status["paper_submit_authorized"]).lower()}
* **Daniel action required now**: {str(signal_rule_status["daniel_action_required_now"]).lower()}
* **Profit claim**: `{signal_rule_status["profit_claim"]}`
* **Safety scope**: `{signal_rule_status["safety_scope"]}`
```json
{signal_rule_status_json}
```

## Shared Risk Rule Status
* **Artifact**: `{payload["shared_risk_rule_status_path"]}`
* **Shared risk-rule status**: `{shared_risk_rule_status["shared_risk_rule_status"]}`
* **Shared risk-rule status mode**: `{shared_risk_rule_status["shared_risk_rule_status_mode"]}`
* **Source queue item**: `{shared_risk_rule_status["source_queue_item_id"]}`
* **Source action**: `{shared_risk_rule_status["source_action_id"]}`
* **Source gap**: `{shared_risk_rule_status["source_gap_id"]}`
* **Source scope**: `{shared_risk_rule_status["source_candidate_family_id"]}`
* **Expected evidence artifact**: `{shared_risk_rule_status["source_expected_evidence_artifact"]}`
* **Evidence status summary**: {shared_risk_rule_status["evidence_status_summary"]}
* **Remaining missing shared risk evidence**: {len(shared_risk_rule_status["remaining_missing_shared_risk_evidence"])}
* **Target readiness**: `{shared_risk_rule_status["target_shared_risk_readiness"]["readiness_status"]}`
* **Selected next safe action**: `{shared_risk_rule_status["selected_next_safe_action"]}`
* **Broker-state mode**: `{shared_risk_rule_status["broker_state_mode"]}`
* **Paper submit authorized**: {str(shared_risk_rule_status["paper_submit_authorized"]).lower()}
* **Daniel action required now**: {str(shared_risk_rule_status["daniel_action_required_now"]).lower()}
* **Profit claim**: `{shared_risk_rule_status["profit_claim"]}`
* **Safety scope**: `{shared_risk_rule_status["safety_scope"]}`
```json
{shared_risk_rule_status_json}
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
* `.\\scripts\\run_daily_paper_lab.ps1 -OutputRoot runs/daily_lab/v_assistant_v1_22_smoke`
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
* `research_board_prioritization.jsonl`
* `strategy_comparison_scaffold.jsonl`
* `candidate_strategy_evidence_template.jsonl`
* `candidate_evidence_requirements.jsonl`
* `candidate_evidence_collection_plan.jsonl`
* `candidate_evidence_collection_status.jsonl`
* `candidate_evidence_gap_summary.jsonl`
* `candidate_gap_closure_queue.jsonl`
* `candidate_risk_rule_status.jsonl`
* `candidate_signal_rule_status.jsonl`
* `shared_risk_rule_status.jsonl`
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
5. Behavior implemented.
6. Output artifacts produced.
7. Candidate evidence collection status summary.
8. Top selected next safe action.
9. Quality gate result.
10. Tests run and exact results.
11. Full pytest result.
12. Safety assessment.
13. Broker-read/broker-mutation/paper-submit/live-trading confirmation.
14. Final `git status --short`.
15. Untracked files intentionally left untouched.
16. Recommended commit message.

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
    scaffold_json = _json_markdown(payload["strategy_comparison_scaffold"])
    template_json = _json_markdown(payload["candidate_strategy_evidence_template"])
    requirements_json = _json_markdown(payload["candidate_evidence_requirements"])
    collection_plan_json = _json_markdown(
        payload["candidate_evidence_collection_plan"]
    )
    collection_status_json = _json_markdown(
        payload["candidate_evidence_collection_status"]
    )
    collection_status_json = _json_markdown(
        payload["candidate_evidence_collection_status"]
    )
    gap_summary_json = _json_markdown(payload["candidate_evidence_gap_summary"])
    gap_closure_queue_json = _json_markdown(
        payload["candidate_gap_closure_queue"]
    )
    risk_rule_status_json = _json_markdown(
        payload["candidate_risk_rule_status"]
    )
    signal_rule_status_json = _json_markdown(
        payload["candidate_signal_rule_status"]
    )
    shared_risk_rule_status_json = _json_markdown(
        payload["shared_risk_rule_status"]
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

## Strategy Comparison Scaffold
* **Artifact**: `{payload["strategy_comparison_scaffold_path"]}`
* **Scaffold status**: `{payload["strategy_comparison_scaffold"]["scaffold_status"]}`
* **Comparison mode**: `{payload["strategy_comparison_scaffold"]["comparison_mode"]}`
* **Baseline strategy**: `{payload["strategy_comparison_scaffold"]["baseline_strategy_id"]}`
* **Baseline role**: `{payload["strategy_comparison_scaffold"]["baseline_strategy_role"]}`
* **Candidate slots**: {len(payload["strategy_comparison_scaffold"]["candidate_strategy_slots"])}
* **Comparison dimensions**: {payload["strategy_comparison_scaffold"]["comparison_dimensions"]}
* **Selected next safe action**: `{payload["strategy_comparison_scaffold"]["selected_next_safe_action"]}`
* **Why selected**: {payload["strategy_comparison_scaffold"]["why_selected"]}
* **Why no strategy replacement yet**: {payload["strategy_comparison_scaffold"]["why_no_strategy_replacement_yet"]}
* **Safety scope**: `{payload["strategy_comparison_scaffold"]["safety_scope"]}`
* **Broker-state mode**: `{payload["strategy_comparison_scaffold"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["strategy_comparison_scaffold"]["paper_submit_authorized"]).lower()}
* **Profit claim**: `{payload["strategy_comparison_scaffold"]["profit_claim"]}`
```json
{scaffold_json}
```

## Candidate Strategy Evidence Template
* **Artifact**: `{payload["candidate_strategy_evidence_template_path"]}`
* **Template status**: `{payload["candidate_strategy_evidence_template"]["template_status"]}`
* **Evidence mode**: `{payload["candidate_strategy_evidence_template"]["evidence_mode"]}`
* **Baseline strategy**: `{payload["candidate_strategy_evidence_template"]["baseline_strategy_id"]}`
* **Baseline role**: `{payload["candidate_strategy_evidence_template"]["baseline_strategy_role"]}`
* **Candidate families**: {len(payload["candidate_strategy_evidence_template"]["candidate_families"])}
* **Required evidence sections**: {payload["candidate_strategy_evidence_template"]["required_evidence_sections"]}
* **Selected next safe action**: `{payload["candidate_strategy_evidence_template"]["selected_next_safe_action"]}`
* **Why selected**: {payload["candidate_strategy_evidence_template"]["why_selected"]}
* **Why no strategy implementation yet**: {payload["candidate_strategy_evidence_template"]["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{payload["candidate_strategy_evidence_template"]["safety_scope"]}`
* **Broker-state mode**: `{payload["candidate_strategy_evidence_template"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["candidate_strategy_evidence_template"]["paper_submit_authorized"]).lower()}
* **Profit claim**: `{payload["candidate_strategy_evidence_template"]["profit_claim"]}`
```json
{template_json}
```

## Candidate Evidence Requirements
* **Artifact**: `{payload["candidate_evidence_requirements_path"]}`
* **Requirements status**: `{payload["candidate_evidence_requirements"]["requirements_status"]}`
* **Requirements mode**: `{payload["candidate_evidence_requirements"]["requirements_mode"]}`
* **Baseline strategy**: `{payload["candidate_evidence_requirements"]["baseline_strategy_id"]}`
* **Baseline role**: `{payload["candidate_evidence_requirements"]["baseline_strategy_role"]}`
* **Candidate requirements**: {len(payload["candidate_evidence_requirements"]["candidate_requirements"])}
* **Shared evidence requirements**: {payload["candidate_evidence_requirements"]["shared_evidence_requirements"]}
* **Promotion blockers**: {payload["candidate_evidence_requirements"]["promotion_blockers"]}
* **Rejection triggers**: {payload["candidate_evidence_requirements"]["rejection_triggers"]}
* **Selected next safe action**: `{payload["candidate_evidence_requirements"]["selected_next_safe_action"]}`
* **Why selected**: {payload["candidate_evidence_requirements"]["why_selected"]}
* **Why no strategy implementation yet**: {payload["candidate_evidence_requirements"]["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{payload["candidate_evidence_requirements"]["safety_scope"]}`
* **Broker-state mode**: `{payload["candidate_evidence_requirements"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["candidate_evidence_requirements"]["paper_submit_authorized"]).lower()}
* **Profit claim**: `{payload["candidate_evidence_requirements"]["profit_claim"]}`
```json
{requirements_json}
```

## Candidate Evidence Collection Plan
* **Artifact**: `{payload["candidate_evidence_collection_plan_path"]}`
* **Collection plan status**: `{payload["candidate_evidence_collection_plan"]["collection_plan_status"]}`
* **Collection plan mode**: `{payload["candidate_evidence_collection_plan"]["collection_plan_mode"]}`
* **Baseline strategy**: `{payload["candidate_evidence_collection_plan"]["baseline_strategy_id"]}`
* **Baseline role**: `{payload["candidate_evidence_collection_plan"]["baseline_strategy_role"]}`
* **Candidate collection plans**: {len(payload["candidate_evidence_collection_plan"]["candidate_collection_plans"])}
* **Shared collection steps**: {payload["candidate_evidence_collection_plan"]["shared_collection_steps"]}
* **Expected offline artifacts**: {payload["candidate_evidence_collection_plan"]["expected_offline_artifacts"]}
* **Selected next safe action**: `{payload["candidate_evidence_collection_plan"]["selected_next_safe_action"]}`
* **Why selected**: {payload["candidate_evidence_collection_plan"]["why_selected"]}
* **Why no strategy implementation yet**: {payload["candidate_evidence_collection_plan"]["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{payload["candidate_evidence_collection_plan"]["safety_scope"]}`
* **Broker-state mode**: `{payload["candidate_evidence_collection_plan"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["candidate_evidence_collection_plan"]["paper_submit_authorized"]).lower()}
* **Profit claim**: `{payload["candidate_evidence_collection_plan"]["profit_claim"]}`
```json
{collection_plan_json}
```

## Candidate Evidence Collection Status
* **Artifact**: `{payload["candidate_evidence_collection_status_path"]}`
* **Collection status**: `{payload["candidate_evidence_collection_status"]["collection_status"]}`
* **Collection status mode**: `{payload["candidate_evidence_collection_status"]["collection_status_mode"]}`
* **Baseline strategy**: `{payload["candidate_evidence_collection_status"]["baseline_strategy_id"]}`
* **Baseline role**: `{payload["candidate_evidence_collection_status"]["baseline_strategy_role"]}`
* **Candidate statuses**: {len(payload["candidate_evidence_collection_status"]["candidate_statuses"])}
* **Shared collection statuses**: {len(payload["candidate_evidence_collection_status"]["shared_collection_status"])}
* **Evidence status counts**: {payload["candidate_evidence_collection_status"]["evidence_status_counts"]}
* **Promotion blockers**: {payload["candidate_evidence_collection_status"]["promotion_blockers"]}
* **Selected next safe action**: `{payload["candidate_evidence_collection_status"]["selected_next_safe_action"]}`
* **Why selected**: {payload["candidate_evidence_collection_status"]["why_selected"]}
* **Why no strategy implementation yet**: {payload["candidate_evidence_collection_status"]["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{payload["candidate_evidence_collection_status"]["safety_scope"]}`
* **Broker-state mode**: `{payload["candidate_evidence_collection_status"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["candidate_evidence_collection_status"]["paper_submit_authorized"]).lower()}
* **Profit claim**: `{payload["candidate_evidence_collection_status"]["profit_claim"]}`
```json
{collection_status_json}
```

## Candidate Evidence Gap Summary
* **Artifact**: `{payload["candidate_evidence_gap_summary_path"]}`
* **Gap summary status**: `{payload["candidate_evidence_gap_summary"]["gap_summary_status"]}`
* **Gap summary mode**: `{payload["candidate_evidence_gap_summary"]["gap_summary_mode"]}`
* **Baseline strategy**: `{payload["candidate_evidence_gap_summary"]["baseline_strategy_id"]}`
* **Baseline role**: `{payload["candidate_evidence_gap_summary"]["baseline_strategy_role"]}`
* **Candidate gap summaries**: {len(payload["candidate_evidence_gap_summary"]["candidate_gap_summaries"])}
* **Ranked gap groups**: {len(payload["candidate_evidence_gap_summary"]["ranked_gap_groups"])}
* **Highest priority gaps**: {len(payload["candidate_evidence_gap_summary"]["highest_priority_gaps"])}
* **Shared gap summary**: {len(payload["candidate_evidence_gap_summary"]["shared_gap_summary"])}
* **Gap counts**: {payload["candidate_evidence_gap_summary"]["gap_counts"]}
* **Next gap closure actions**: {payload["candidate_evidence_gap_summary"]["next_gap_closure_actions"]}
* **Next research artifacts to build**: {payload["candidate_evidence_gap_summary"]["next_research_artifacts_to_build"]}
* **Selected next safe action**: `{payload["candidate_evidence_gap_summary"]["selected_next_safe_action"]}`
* **Why selected**: {payload["candidate_evidence_gap_summary"]["why_selected"]}
* **Why no strategy implementation yet**: {payload["candidate_evidence_gap_summary"]["why_no_strategy_implementation_yet"]}
* **Safety scope**: `{payload["candidate_evidence_gap_summary"]["safety_scope"]}`
* **Broker-state mode**: `{payload["candidate_evidence_gap_summary"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["candidate_evidence_gap_summary"]["paper_submit_authorized"]).lower()}
* **Profit claim**: `{payload["candidate_evidence_gap_summary"]["profit_claim"]}`
```json
{gap_summary_json}
```

## Candidate Gap Closure Queue
* **Artifact**: `{payload["candidate_gap_closure_queue_path"]}`
* **Queue status**: `{payload["candidate_gap_closure_queue"]["queue_status"]}`
* **Queue mode**: `{payload["candidate_gap_closure_queue"]["queue_mode"]}`
* **Item count**: {payload["candidate_gap_closure_queue"]["queue_item_count"]}
* **First queue item**: `{payload["candidate_gap_closure_queue"]["selected_queue_item_id"]}`
* **Selected next safe action**: `{payload["candidate_gap_closure_queue"]["selected_next_safe_action"]}`
* **Broker-state mode**: `{payload["candidate_gap_closure_queue"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["candidate_gap_closure_queue"]["paper_submit_authorized"]).lower()}
* **Daniel action required now**: {str(payload["candidate_gap_closure_queue"]["daniel_action_required_now"]).lower()}
* **Profit claim**: `{payload["candidate_gap_closure_queue"]["profit_claim"]}`
* **Safety scope**: `{payload["candidate_gap_closure_queue"]["safety_scope"]}`
```json
{gap_closure_queue_json}
```

## Candidate Risk Rule Status
* **Artifact**: `{payload["candidate_risk_rule_status_path"]}`
* **Risk-rule status**: `{payload["candidate_risk_rule_status"]["risk_rule_status"]}`
* **Risk-rule status mode**: `{payload["candidate_risk_rule_status"]["risk_rule_status_mode"]}`
* **Source queue item**: `{payload["candidate_risk_rule_status"]["source_queue_item_id"]}`
* **Source action**: `{payload["candidate_risk_rule_status"]["source_action_id"]}`
* **Source gap**: `{payload["candidate_risk_rule_status"]["source_gap_id"]}`
* **Source candidate**: `{payload["candidate_risk_rule_status"]["source_candidate_family_id"]}`
* **Expected evidence artifact**: `{payload["candidate_risk_rule_status"]["source_expected_evidence_artifact"]}`
* **Candidate family count**: {payload["candidate_risk_rule_status"]["candidate_family_count"]}
* **Candidate/shared scope count**: {payload["candidate_risk_rule_status"]["candidate_scope_count"]}/{payload["candidate_risk_rule_status"]["shared_scope_count"]}
* **Incomplete risk-rule count**: {sum(1 for item in payload["candidate_risk_rule_status"]["candidate_risk_rule_summaries"] if item["risk_rule_status"] == "incomplete")}
* **Evidence status summary**: {payload["candidate_risk_rule_status"]["evidence_status_summary"]}
* **Highest-priority risk-rule gaps**: {payload["candidate_risk_rule_status"]["highest_priority_risk_rule_gaps"]}
* **Selected next safe action**: `{payload["candidate_risk_rule_status"]["selected_next_safe_action"]}`
* **Broker-state mode**: `{payload["candidate_risk_rule_status"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["candidate_risk_rule_status"]["paper_submit_authorized"]).lower()}
* **Daniel action required now**: {str(payload["candidate_risk_rule_status"]["daniel_action_required_now"]).lower()}
* **Profit claim**: `{payload["candidate_risk_rule_status"]["profit_claim"]}`
* **Safety scope**: `{payload["candidate_risk_rule_status"]["safety_scope"]}`
```json
{risk_rule_status_json}
```

## Candidate Signal Rule Status
* **Artifact**: `{payload["candidate_signal_rule_status_path"]}`
* **Signal-rule status**: `{payload["candidate_signal_rule_status"]["signal_rule_status"]}`
* **Signal-rule status mode**: `{payload["candidate_signal_rule_status"]["signal_rule_status_mode"]}`
* **Source queue item**: `{payload["candidate_signal_rule_status"]["source_queue_item_id"]}`
* **Source action**: `{payload["candidate_signal_rule_status"]["source_action_id"]}`
* **Source gap**: `{payload["candidate_signal_rule_status"]["source_gap_id"]}`
* **Source candidate**: `{payload["candidate_signal_rule_status"]["source_candidate_family_id"]}`
* **Expected evidence artifact**: `{payload["candidate_signal_rule_status"]["source_expected_evidence_artifact"]}`
* **Candidate family count**: {payload["candidate_signal_rule_status"]["candidate_family_count"]}
* **Candidate/shared scope count**: {payload["candidate_signal_rule_status"]["candidate_scope_count"]}/{payload["candidate_signal_rule_status"]["shared_scope_count"]}
* **Incomplete signal-rule count**: {sum(1 for item in payload["candidate_signal_rule_status"]["candidate_signal_rule_summaries"] if item["signal_rule_status"] == "incomplete")}
* **Evidence status summary**: {payload["candidate_signal_rule_status"]["evidence_status_summary"]}
* **Highest-priority signal-rule gaps**: {payload["candidate_signal_rule_status"]["highest_priority_signal_rule_gaps"]}
* **Selected next safe action**: `{payload["candidate_signal_rule_status"]["selected_next_safe_action"]}`
* **Broker-state mode**: `{payload["candidate_signal_rule_status"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["candidate_signal_rule_status"]["paper_submit_authorized"]).lower()}
* **Daniel action required now**: {str(payload["candidate_signal_rule_status"]["daniel_action_required_now"]).lower()}
* **Profit claim**: `{payload["candidate_signal_rule_status"]["profit_claim"]}`
* **Safety scope**: `{payload["candidate_signal_rule_status"]["safety_scope"]}`
```json
{signal_rule_status_json}
```

## Shared Risk Rule Status
* **Artifact**: `{payload["shared_risk_rule_status_path"]}`
* **Shared risk-rule status**: `{payload["shared_risk_rule_status"]["shared_risk_rule_status"]}`
* **Shared risk-rule status mode**: `{payload["shared_risk_rule_status"]["shared_risk_rule_status_mode"]}`
* **Source queue item**: `{payload["shared_risk_rule_status"]["source_queue_item_id"]}`
* **Source action**: `{payload["shared_risk_rule_status"]["source_action_id"]}`
* **Source gap**: `{payload["shared_risk_rule_status"]["source_gap_id"]}`
* **Source scope**: `{payload["shared_risk_rule_status"]["source_candidate_family_id"]}`
* **Expected evidence artifact**: `{payload["shared_risk_rule_status"]["source_expected_evidence_artifact"]}`
* **Evidence status summary**: {payload["shared_risk_rule_status"]["evidence_status_summary"]}
* **Target readiness**: `{payload["shared_risk_rule_status"]["target_shared_risk_readiness"]["readiness_status"]}`
* **Selected next safe action**: `{payload["shared_risk_rule_status"]["selected_next_safe_action"]}`
* **Broker-state mode**: `{payload["shared_risk_rule_status"]["broker_state_mode"]}`
* **Paper submit authorized**: {str(payload["shared_risk_rule_status"]["paper_submit_authorized"]).lower()}
* **Daniel action required now**: {str(payload["shared_risk_rule_status"]["daniel_action_required_now"]).lower()}
* **Profit claim**: `{payload["shared_risk_rule_status"]["profit_claim"]}`
* **Safety scope**: `{payload["shared_risk_rule_status"]["safety_scope"]}`
```json
{shared_risk_rule_status_json}
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
    scaffold_json = _json_markdown(payload["strategy_comparison_scaffold"])
    template_json = _json_markdown(payload["candidate_strategy_evidence_template"])
    requirements_json = _json_markdown(payload["candidate_evidence_requirements"])
    collection_plan_json = _json_markdown(
        payload["candidate_evidence_collection_plan"]
    )
    collection_status_json = _json_markdown(
        payload["candidate_evidence_collection_status"]
    )
    gap_summary_json = _json_markdown(payload["candidate_evidence_gap_summary"])
    gap_closure_queue_json = _json_markdown(
        payload["candidate_gap_closure_queue"]
    )
    risk_rule_status_json = _json_markdown(
        payload["candidate_risk_rule_status"]
    )
    signal_rule_status_json = _json_markdown(
        payload["candidate_signal_rule_status"]
    )
    shared_risk_rule_status_json = _json_markdown(
        payload["shared_risk_rule_status"]
    )
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

## Strategy Comparison Scaffold
* **strategy_comparison_scaffold_path**: `{payload["strategy_comparison_scaffold_path"]}`
* **scaffold_status**: `{payload["strategy_comparison_scaffold"]["scaffold_status"]}`
* **comparison_mode**: `{payload["strategy_comparison_scaffold"]["comparison_mode"]}`
* **baseline_strategy_id**: `{payload["strategy_comparison_scaffold"]["baseline_strategy_id"]}`
* **baseline_strategy_role**: `{payload["strategy_comparison_scaffold"]["baseline_strategy_role"]}`
* **candidate_slot_count**: {len(payload["strategy_comparison_scaffold"]["candidate_strategy_slots"])}
* **comparison_dimensions**: `{payload["strategy_comparison_scaffold"]["comparison_dimensions"]}`
* **selected_next_safe_action**: `{payload["strategy_comparison_scaffold"]["selected_next_safe_action"]}`
* **why_selected**: {payload["strategy_comparison_scaffold"]["why_selected"]}
* **why_no_strategy_replacement_yet**: {payload["strategy_comparison_scaffold"]["why_no_strategy_replacement_yet"]}
* **safety_scope**: `{payload["strategy_comparison_scaffold"]["safety_scope"]}`
* **broker_state_mode**: `{payload["strategy_comparison_scaffold"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["strategy_comparison_scaffold"]["paper_submit_authorized"]).lower()}
* **profit_claim**: `{payload["strategy_comparison_scaffold"]["profit_claim"]}`
```json
{scaffold_json}
```

## Candidate Strategy Evidence Template
* **candidate_strategy_evidence_template_path**: `{payload["candidate_strategy_evidence_template_path"]}`
* **template_status**: `{payload["candidate_strategy_evidence_template"]["template_status"]}`
* **evidence_mode**: `{payload["candidate_strategy_evidence_template"]["evidence_mode"]}`
* **baseline_strategy_id**: `{payload["candidate_strategy_evidence_template"]["baseline_strategy_id"]}`
* **baseline_strategy_role**: `{payload["candidate_strategy_evidence_template"]["baseline_strategy_role"]}`
* **candidate_family_count**: {len(payload["candidate_strategy_evidence_template"]["candidate_families"])}
* **required_evidence_sections**: `{payload["candidate_strategy_evidence_template"]["required_evidence_sections"]}`
* **selected_next_safe_action**: `{payload["candidate_strategy_evidence_template"]["selected_next_safe_action"]}`
* **why_selected**: {payload["candidate_strategy_evidence_template"]["why_selected"]}
* **why_no_strategy_implementation_yet**: {payload["candidate_strategy_evidence_template"]["why_no_strategy_implementation_yet"]}
* **safety_scope**: `{payload["candidate_strategy_evidence_template"]["safety_scope"]}`
* **broker_state_mode**: `{payload["candidate_strategy_evidence_template"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["candidate_strategy_evidence_template"]["paper_submit_authorized"]).lower()}
* **profit_claim**: `{payload["candidate_strategy_evidence_template"]["profit_claim"]}`
```json
{template_json}
```

## Candidate Evidence Requirements
* **candidate_evidence_requirements_path**: `{payload["candidate_evidence_requirements_path"]}`
* **requirements_status**: `{payload["candidate_evidence_requirements"]["requirements_status"]}`
* **requirements_mode**: `{payload["candidate_evidence_requirements"]["requirements_mode"]}`
* **baseline_strategy_id**: `{payload["candidate_evidence_requirements"]["baseline_strategy_id"]}`
* **baseline_strategy_role**: `{payload["candidate_evidence_requirements"]["baseline_strategy_role"]}`
* **candidate_requirement_count**: {len(payload["candidate_evidence_requirements"]["candidate_requirements"])}
* **shared_evidence_requirements**: `{payload["candidate_evidence_requirements"]["shared_evidence_requirements"]}`
* **per_candidate_missing_evidence**: `{payload["candidate_evidence_requirements"]["per_candidate_missing_evidence"]}`
* **promotion_blockers**: `{payload["candidate_evidence_requirements"]["promotion_blockers"]}`
* **rejection_triggers**: `{payload["candidate_evidence_requirements"]["rejection_triggers"]}`
* **selected_next_safe_action**: `{payload["candidate_evidence_requirements"]["selected_next_safe_action"]}`
* **why_selected**: {payload["candidate_evidence_requirements"]["why_selected"]}
* **why_no_strategy_implementation_yet**: {payload["candidate_evidence_requirements"]["why_no_strategy_implementation_yet"]}
* **safety_scope**: `{payload["candidate_evidence_requirements"]["safety_scope"]}`
* **broker_state_mode**: `{payload["candidate_evidence_requirements"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["candidate_evidence_requirements"]["paper_submit_authorized"]).lower()}
* **profit_claim**: `{payload["candidate_evidence_requirements"]["profit_claim"]}`
```json
{requirements_json}
```

## Candidate Evidence Collection Plan
* **candidate_evidence_collection_plan_path**: `{payload["candidate_evidence_collection_plan_path"]}`
* **collection_plan_status**: `{payload["candidate_evidence_collection_plan"]["collection_plan_status"]}`
* **collection_plan_mode**: `{payload["candidate_evidence_collection_plan"]["collection_plan_mode"]}`
* **baseline_strategy_id**: `{payload["candidate_evidence_collection_plan"]["baseline_strategy_id"]}`
* **baseline_strategy_role**: `{payload["candidate_evidence_collection_plan"]["baseline_strategy_role"]}`
* **candidate_collection_plan_count**: {len(payload["candidate_evidence_collection_plan"]["candidate_collection_plans"])}
* **shared_collection_steps**: `{payload["candidate_evidence_collection_plan"]["shared_collection_steps"]}`
* **data_collection_requirements**: `{payload["candidate_evidence_collection_plan"]["data_collection_requirements"]}`
* **metric_collection_requirements**: `{payload["candidate_evidence_collection_plan"]["metric_collection_requirements"]}`
* **safety_collection_requirements**: `{payload["candidate_evidence_collection_plan"]["safety_collection_requirements"]}`
* **expected_offline_artifacts**: `{payload["candidate_evidence_collection_plan"]["expected_offline_artifacts"]}`
* **blocked_until_collected**: `{payload["candidate_evidence_collection_plan"]["blocked_until_collected"]}`
* **selected_next_safe_action**: `{payload["candidate_evidence_collection_plan"]["selected_next_safe_action"]}`
* **why_selected**: {payload["candidate_evidence_collection_plan"]["why_selected"]}
* **why_no_strategy_implementation_yet**: {payload["candidate_evidence_collection_plan"]["why_no_strategy_implementation_yet"]}
* **safety_scope**: `{payload["candidate_evidence_collection_plan"]["safety_scope"]}`
* **broker_state_mode**: `{payload["candidate_evidence_collection_plan"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["candidate_evidence_collection_plan"]["paper_submit_authorized"]).lower()}
* **profit_claim**: `{payload["candidate_evidence_collection_plan"]["profit_claim"]}`
```json
{collection_plan_json}
```

## Candidate Evidence Collection Status
* **candidate_evidence_collection_status_path**: `{payload["candidate_evidence_collection_status_path"]}`
* **collection_status**: `{payload["candidate_evidence_collection_status"]["collection_status"]}`
* **collection_status_mode**: `{payload["candidate_evidence_collection_status"]["collection_status_mode"]}`
* **baseline_strategy_id**: `{payload["candidate_evidence_collection_status"]["baseline_strategy_id"]}`
* **baseline_strategy_role**: `{payload["candidate_evidence_collection_status"]["baseline_strategy_role"]}`
* **candidate_status_count**: {len(payload["candidate_evidence_collection_status"]["candidate_statuses"])}
* **shared_collection_status_count**: {len(payload["candidate_evidence_collection_status"]["shared_collection_status"])}
* **evidence_status_counts**: `{payload["candidate_evidence_collection_status"]["evidence_status_counts"]}`
* **not_started_evidence_count**: {len(payload["candidate_evidence_collection_status"]["not_started_evidence"])}
* **blocked_evidence_count**: {len(payload["candidate_evidence_collection_status"]["blocked_evidence"])}
* **ready_to_collect_evidence_count**: {len(payload["candidate_evidence_collection_status"]["ready_to_collect_evidence"])}
* **missing_evidence_count**: {len(payload["candidate_evidence_collection_status"]["missing_evidence"])}
* **promotion_blockers**: `{payload["candidate_evidence_collection_status"]["promotion_blockers"]}`
* **next_collection_actions**: `{payload["candidate_evidence_collection_status"]["next_collection_actions"]}`
* **selected_next_safe_action**: `{payload["candidate_evidence_collection_status"]["selected_next_safe_action"]}`
* **why_selected**: {payload["candidate_evidence_collection_status"]["why_selected"]}
* **why_no_strategy_implementation_yet**: {payload["candidate_evidence_collection_status"]["why_no_strategy_implementation_yet"]}
* **safety_scope**: `{payload["candidate_evidence_collection_status"]["safety_scope"]}`
* **broker_state_mode**: `{payload["candidate_evidence_collection_status"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["candidate_evidence_collection_status"]["paper_submit_authorized"]).lower()}
* **profit_claim**: `{payload["candidate_evidence_collection_status"]["profit_claim"]}`
```json
{collection_status_json}
```

## Candidate Evidence Gap Summary
* **candidate_evidence_gap_summary_path**: `{payload["candidate_evidence_gap_summary_path"]}`
* **gap_summary_status**: `{payload["candidate_evidence_gap_summary"]["gap_summary_status"]}`
* **gap_summary_mode**: `{payload["candidate_evidence_gap_summary"]["gap_summary_mode"]}`
* **baseline_strategy_id**: `{payload["candidate_evidence_gap_summary"]["baseline_strategy_id"]}`
* **baseline_strategy_role**: `{payload["candidate_evidence_gap_summary"]["baseline_strategy_role"]}`
* **candidate_gap_summary_count**: {len(payload["candidate_evidence_gap_summary"]["candidate_gap_summaries"])}
* **ranked_gap_group_count**: {len(payload["candidate_evidence_gap_summary"]["ranked_gap_groups"])}
* **highest_priority_gap_count**: {len(payload["candidate_evidence_gap_summary"]["highest_priority_gaps"])}
* **shared_gap_summary_count**: {len(payload["candidate_evidence_gap_summary"]["shared_gap_summary"])}
* **gap_counts**: `{payload["candidate_evidence_gap_summary"]["gap_counts"]}`
* **next_gap_closure_actions**: `{payload["candidate_evidence_gap_summary"]["next_gap_closure_actions"]}`
* **next_research_artifacts_to_build**: `{payload["candidate_evidence_gap_summary"]["next_research_artifacts_to_build"]}`
* **selected_next_safe_action**: `{payload["candidate_evidence_gap_summary"]["selected_next_safe_action"]}`
* **why_selected**: {payload["candidate_evidence_gap_summary"]["why_selected"]}
* **why_no_strategy_implementation_yet**: {payload["candidate_evidence_gap_summary"]["why_no_strategy_implementation_yet"]}
* **safety_scope**: `{payload["candidate_evidence_gap_summary"]["safety_scope"]}`
* **broker_state_mode**: `{payload["candidate_evidence_gap_summary"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["candidate_evidence_gap_summary"]["paper_submit_authorized"]).lower()}
* **profit_claim**: `{payload["candidate_evidence_gap_summary"]["profit_claim"]}`
```json
{gap_summary_json}
```

## Candidate Gap Closure Queue
* **candidate_gap_closure_queue_path**: `{payload["candidate_gap_closure_queue_path"]}`
* **queue_status**: `{payload["candidate_gap_closure_queue"]["queue_status"]}`
* **queue_mode**: `{payload["candidate_gap_closure_queue"]["queue_mode"]}`
* **queue_item_count**: {payload["candidate_gap_closure_queue"]["queue_item_count"]}
* **selected_queue_item_id**: `{payload["candidate_gap_closure_queue"]["selected_queue_item_id"]}`
* **selected_next_safe_action**: `{payload["candidate_gap_closure_queue"]["selected_next_safe_action"]}`
* **broker_state_mode**: `{payload["candidate_gap_closure_queue"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["candidate_gap_closure_queue"]["paper_submit_authorized"]).lower()}
* **daniel_action_required_now**: {str(payload["candidate_gap_closure_queue"]["daniel_action_required_now"]).lower()}
* **profit_claim**: `{payload["candidate_gap_closure_queue"]["profit_claim"]}`
* **safety_scope**: `{payload["candidate_gap_closure_queue"]["safety_scope"]}`
```json
{gap_closure_queue_json}
```

## Candidate Risk Rule Status
* **candidate_risk_rule_status_path**: `{payload["candidate_risk_rule_status_path"]}`
* **risk_rule_status**: `{payload["candidate_risk_rule_status"]["risk_rule_status"]}`
* **risk_rule_status_mode**: `{payload["candidate_risk_rule_status"]["risk_rule_status_mode"]}`
* **source_queue_item_id**: `{payload["candidate_risk_rule_status"]["source_queue_item_id"]}`
* **source_action_id**: `{payload["candidate_risk_rule_status"]["source_action_id"]}`
* **source_gap_id**: `{payload["candidate_risk_rule_status"]["source_gap_id"]}`
* **source_candidate_family_id**: `{payload["candidate_risk_rule_status"]["source_candidate_family_id"]}`
* **source_expected_evidence_artifact**: `{payload["candidate_risk_rule_status"]["source_expected_evidence_artifact"]}`
* **candidate_family_count**: {payload["candidate_risk_rule_status"]["candidate_family_count"]}
* **candidate_scope_count**: {payload["candidate_risk_rule_status"]["candidate_scope_count"]}
* **shared_scope_count**: {payload["candidate_risk_rule_status"]["shared_scope_count"]}
* **evidence_status_summary**: `{payload["candidate_risk_rule_status"]["evidence_status_summary"]}`
* **highest_priority_risk_rule_gaps**: `{payload["candidate_risk_rule_status"]["highest_priority_risk_rule_gaps"]}`
* **next_risk_rule_closure_actions**: `{payload["candidate_risk_rule_status"]["next_risk_rule_closure_actions"]}`
* **selected_next_safe_action**: `{payload["candidate_risk_rule_status"]["selected_next_safe_action"]}`
* **broker_state_mode**: `{payload["candidate_risk_rule_status"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["candidate_risk_rule_status"]["paper_submit_authorized"]).lower()}
* **daniel_action_required_now**: {str(payload["candidate_risk_rule_status"]["daniel_action_required_now"]).lower()}
* **profit_claim**: `{payload["candidate_risk_rule_status"]["profit_claim"]}`
* **safety_scope**: `{payload["candidate_risk_rule_status"]["safety_scope"]}`
```json
{risk_rule_status_json}
```

## Candidate Signal Rule Status
* **candidate_signal_rule_status_path**: `{payload["candidate_signal_rule_status_path"]}`
* **signal_rule_status**: `{payload["candidate_signal_rule_status"]["signal_rule_status"]}`
* **signal_rule_status_mode**: `{payload["candidate_signal_rule_status"]["signal_rule_status_mode"]}`
* **source_queue_item_id**: `{payload["candidate_signal_rule_status"]["source_queue_item_id"]}`
* **source_action_id**: `{payload["candidate_signal_rule_status"]["source_action_id"]}`
* **source_gap_id**: `{payload["candidate_signal_rule_status"]["source_gap_id"]}`
* **source_candidate_family_id**: `{payload["candidate_signal_rule_status"]["source_candidate_family_id"]}`
* **source_expected_evidence_artifact**: `{payload["candidate_signal_rule_status"]["source_expected_evidence_artifact"]}`
* **candidate_family_count**: {payload["candidate_signal_rule_status"]["candidate_family_count"]}
* **candidate_scope_count**: {payload["candidate_signal_rule_status"]["candidate_scope_count"]}
* **shared_scope_count**: {payload["candidate_signal_rule_status"]["shared_scope_count"]}
* **evidence_status_summary**: `{payload["candidate_signal_rule_status"]["evidence_status_summary"]}`
* **highest_priority_signal_rule_gaps**: `{payload["candidate_signal_rule_status"]["highest_priority_signal_rule_gaps"]}`
* **next_signal_rule_closure_actions**: `{payload["candidate_signal_rule_status"]["next_signal_rule_closure_actions"]}`
* **selected_next_safe_action**: `{payload["candidate_signal_rule_status"]["selected_next_safe_action"]}`
* **broker_state_mode**: `{payload["candidate_signal_rule_status"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["candidate_signal_rule_status"]["paper_submit_authorized"]).lower()}
* **daniel_action_required_now**: {str(payload["candidate_signal_rule_status"]["daniel_action_required_now"]).lower()}
* **profit_claim**: `{payload["candidate_signal_rule_status"]["profit_claim"]}`
* **safety_scope**: `{payload["candidate_signal_rule_status"]["safety_scope"]}`
```json
{signal_rule_status_json}
```

## Shared Risk Rule Status
* **shared_risk_rule_status_path**: `{payload["shared_risk_rule_status_path"]}`
* **shared_risk_rule_status**: `{payload["shared_risk_rule_status"]["shared_risk_rule_status"]}`
* **shared_risk_rule_status_mode**: `{payload["shared_risk_rule_status"]["shared_risk_rule_status_mode"]}`
* **source_queue_item_id**: `{payload["shared_risk_rule_status"]["source_queue_item_id"]}`
* **source_action_id**: `{payload["shared_risk_rule_status"]["source_action_id"]}`
* **source_gap_id**: `{payload["shared_risk_rule_status"]["source_gap_id"]}`
* **source_candidate_family_id**: `{payload["shared_risk_rule_status"]["source_candidate_family_id"]}`
* **source_expected_evidence_artifact**: `{payload["shared_risk_rule_status"]["source_expected_evidence_artifact"]}`
* **evidence_status_summary**: `{payload["shared_risk_rule_status"]["evidence_status_summary"]}`
* **target_readiness**: `{payload["shared_risk_rule_status"]["target_shared_risk_readiness"]["readiness_status"]}`
* **next_shared_risk_rule_closure_actions**: `{payload["shared_risk_rule_status"]["next_shared_risk_rule_closure_actions"]}`
* **selected_next_safe_action**: `{payload["shared_risk_rule_status"]["selected_next_safe_action"]}`
* **broker_state_mode**: `{payload["shared_risk_rule_status"]["broker_state_mode"]}`
* **paper_submit_authorized**: {str(payload["shared_risk_rule_status"]["paper_submit_authorized"]).lower()}
* **daniel_action_required_now**: {str(payload["shared_risk_rule_status"]["daniel_action_required_now"]).lower()}
* **profit_claim**: `{payload["shared_risk_rule_status"]["profit_claim"]}`
* **safety_scope**: `{payload["shared_risk_rule_status"]["safety_scope"]}`
```json
{shared_risk_rule_status_json}
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
* **Verify**: required artifacts, quality gate result, validation status, action queue priority order, research candidate queue priority order, strategy comparison scaffold status, baseline-health evaluation status, baseline evidence metrics status, metric artifact ingest status, active SPY SMA 50/200 baseline, history delta, decision ledger status, safety labels, and broker-state wording.
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
        (
            "strategy_comparison_scaffold",
            artifact_paths.get("strategy_comparison_scaffold"),
        ),
        (
            "candidate_strategy_evidence_template",
            artifact_paths.get("candidate_strategy_evidence_template"),
        ),
        (
            "candidate_evidence_requirements",
            artifact_paths.get("candidate_evidence_requirements"),
        ),
        (
            "candidate_evidence_collection_plan",
            artifact_paths.get("candidate_evidence_collection_plan"),
        ),
        (
            "candidate_evidence_collection_status",
            artifact_paths.get("candidate_evidence_collection_status"),
        ),
        (
            "candidate_evidence_gap_summary",
            artifact_paths.get("candidate_evidence_gap_summary"),
        ),
        (
            "candidate_gap_closure_queue",
            artifact_paths.get("candidate_gap_closure_queue"),
        ),
        (
            "candidate_risk_rule_status",
            artifact_paths.get("candidate_risk_rule_status"),
        ),
        (
            "candidate_signal_rule_status",
            artifact_paths.get("candidate_signal_rule_status"),
        ),
        (
            "shared_risk_rule_status",
            artifact_paths.get("shared_risk_rule_status"),
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
    strategy_comparison_scaffold_path = (
        output_root / _STRATEGY_COMPARISON_SCAFFOLD_FILENAME
    )
    if strategy_comparison_scaffold_path.exists():
        indexed_artifacts["strategy_comparison_scaffold"] = _artifact_metadata(
            strategy_comparison_scaffold_path
        )
    candidate_strategy_evidence_template_path = (
        output_root / _CANDIDATE_STRATEGY_EVIDENCE_TEMPLATE_FILENAME
    )
    if candidate_strategy_evidence_template_path.exists():
        indexed_artifacts["candidate_strategy_evidence_template"] = (
            _artifact_metadata(candidate_strategy_evidence_template_path)
        )
    candidate_evidence_requirements_path = (
        output_root / _CANDIDATE_EVIDENCE_REQUIREMENTS_FILENAME
    )
    if candidate_evidence_requirements_path.exists():
        indexed_artifacts["candidate_evidence_requirements"] = _artifact_metadata(
            candidate_evidence_requirements_path
        )
    candidate_evidence_collection_plan_path = (
        output_root / _CANDIDATE_EVIDENCE_COLLECTION_PLAN_FILENAME
    )
    if candidate_evidence_collection_plan_path.exists():
        indexed_artifacts["candidate_evidence_collection_plan"] = _artifact_metadata(
            candidate_evidence_collection_plan_path
        )
    candidate_evidence_collection_status_path = (
        output_root / _CANDIDATE_EVIDENCE_COLLECTION_STATUS_FILENAME
    )
    if candidate_evidence_collection_status_path.exists():
        indexed_artifacts["candidate_evidence_collection_status"] = (
            _artifact_metadata(candidate_evidence_collection_status_path)
        )
    candidate_evidence_gap_summary_path = (
        output_root / _CANDIDATE_EVIDENCE_GAP_SUMMARY_FILENAME
    )
    if candidate_evidence_gap_summary_path.exists():
        indexed_artifacts["candidate_evidence_gap_summary"] = _artifact_metadata(
            candidate_evidence_gap_summary_path
        )
    candidate_gap_closure_queue_path = (
        output_root / _CANDIDATE_GAP_CLOSURE_QUEUE_FILENAME
    )
    if candidate_gap_closure_queue_path.exists():
        indexed_artifacts["candidate_gap_closure_queue"] = _artifact_metadata(
            candidate_gap_closure_queue_path
        )
    candidate_risk_rule_status_path = (
        output_root / _CANDIDATE_RISK_RULE_STATUS_FILENAME
    )
    if candidate_risk_rule_status_path.exists():
        indexed_artifacts["candidate_risk_rule_status"] = _artifact_metadata(
            candidate_risk_rule_status_path
        )
    candidate_signal_rule_status_path = (
        output_root / _CANDIDATE_SIGNAL_RULE_STATUS_FILENAME
    )
    if candidate_signal_rule_status_path.exists():
        indexed_artifacts["candidate_signal_rule_status"] = _artifact_metadata(
            candidate_signal_rule_status_path
        )
    shared_risk_rule_status_path = output_root / _SHARED_RISK_RULE_STATUS_FILENAME
    if shared_risk_rule_status_path.exists():
        indexed_artifacts["shared_risk_rule_status"] = _artifact_metadata(
            shared_risk_rule_status_path
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
        "strategy_comparison_scaffold_path": payload[
            "strategy_comparison_scaffold_path"
        ],
        "strategy_comparison_scaffold": dict(
            payload["strategy_comparison_scaffold"]
        ),
        "candidate_strategy_evidence_template_path": payload[
            "candidate_strategy_evidence_template_path"
        ],
        "candidate_strategy_evidence_template": dict(
            payload["candidate_strategy_evidence_template"]
        ),
        "candidate_evidence_requirements_path": payload[
            "candidate_evidence_requirements_path"
        ],
        "candidate_evidence_requirements": dict(
            payload["candidate_evidence_requirements"]
        ),
        "candidate_evidence_collection_plan_path": payload[
            "candidate_evidence_collection_plan_path"
        ],
        "candidate_evidence_collection_plan": dict(
            payload["candidate_evidence_collection_plan"]
        ),
        "candidate_evidence_collection_status_path": payload[
            "candidate_evidence_collection_status_path"
        ],
        "candidate_evidence_collection_status": dict(
            payload["candidate_evidence_collection_status"]
        ),
        "candidate_evidence_gap_summary_path": payload[
            "candidate_evidence_gap_summary_path"
        ],
        "candidate_evidence_gap_summary": dict(
            payload["candidate_evidence_gap_summary"]
        ),
        "candidate_gap_closure_queue_path": payload[
            "candidate_gap_closure_queue_path"
        ],
        "candidate_gap_closure_queue": dict(payload["candidate_gap_closure_queue"]),
        "candidate_risk_rule_status_path": payload[
            "candidate_risk_rule_status_path"
        ],
        "candidate_risk_rule_status": dict(payload["candidate_risk_rule_status"]),
        "candidate_signal_rule_status_path": payload[
            "candidate_signal_rule_status_path"
        ],
        "candidate_signal_rule_status": dict(payload["candidate_signal_rule_status"]),
        "shared_risk_rule_status_path": payload[
            "shared_risk_rule_status_path"
        ],
        "shared_risk_rule_status": dict(payload["shared_risk_rule_status"]),
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
