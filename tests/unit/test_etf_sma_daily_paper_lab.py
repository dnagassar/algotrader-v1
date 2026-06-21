from __future__ import annotations

import json
import os
import shutil
import hashlib
from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from pathlib import Path
import pytest

import algotrader.cli as cli_module
import algotrader.execution.etf_sma_daily_paper_lab as paper_lab_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_paper_lab import (
    EtfSmaDailyPaperLabConfig,
    build_etf_sma_daily_paper_lab,
    evaluate_mission_control_readiness_score,
    run_etf_sma_daily_paper_lab,
    validate_etf_sma_daily_paper_lab_packet,
    validate_mission_control_contract,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"
_CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION = (
    "candidate_gap_closure_queue_complete_no_remaining_items"
)
_MISSION_CONTROL_ARTIFACT_RELATIVE_PATHS = {
    "index_path": "index.html",
    "report_path": "assistant_report.md",
    "mission_path": "mission_control.json",
    "validation_path": "mission_control_validation.json",
    "latest_run_path": "latest_run.json",
    "data_freshness_plan_path": "data_freshness_plan.json",
    "data_refresh_bridge_path": "data_refresh_bridge.json",
    "data_refresh_dry_run_path": "data_refresh_dry_run.json",
    "data_refresh_checklist_path": "data_refresh_operator_checklist.md",
    "operator_review_path": "operator_review.md",
    "operating_record_path": "operating_record.jsonl",
}
_MISSION_CONTROL_WORK_ORDER_FILES = {
    "codex_next_prompt.md",
    "codex_next_work_order.json",
    "antigravity_review_prompt.md",
    "antigravity_review_work_order.json",
    "claude_critique_prompt.md",
    "claude_critique_work_order.json",
    "gpt_report_classification_prompt.md",
    "gpt_next_decision_context.json",
}
_MISSION_CONTROL_AGENT_INBOX_PATHS = (
    Path(".agent_inbox") / "codex" / "next_task.md",
    Path(".agent_inbox") / "codex" / "next_work_order.json",
    Path(".agent_inbox") / "antigravity" / "review_task.md",
    Path(".agent_inbox") / "antigravity" / "review_work_order.json",
    Path(".agent_inbox") / "claude" / "critique_task.md",
    Path(".agent_inbox") / "claude" / "critique_work_order.json",
    Path(".agent_inbox") / "gpt" / "report_classification_prompt.md",
    Path(".agent_inbox") / "gpt" / "next_decision_context.json",
)
_FORBIDDEN_ROUTE_FRAGMENTS = {
    "broker_read",
    "paper_submit",
    "broker_mutation",
    "live_trading",
    "secrets_setup",
    "secret",
    "paid_service",
    "external_api",
    "credential_setup",
    "network_fetch",
    "autonomous_ingest",
    "strategy_promotion",
    "safety_weakening",
}
_EXECUTION_PLAN_COMPACT_FIELDS = {
    "execution_plan_version",
    "execution_plan_id",
    "execution_plan_status",
    "execution_plan_action",
    "execution_plan_symbol",
    "execution_plan_reason",
    "execution_plan_blocker",
    "execution_plan_source_preview_decision",
    "execution_plan_requires_approval",
    "execution_plan_broker_order_required",
    "execution_plan_submit_allowed",
    "execution_plan_paper_submit_authorized",
    "execution_plan_live_authorized",
    "execution_plan_broker_mutation_performed",
    "execution_plan_created_order_payload",
    "execution_plan_labels",
}
_DAILY_APPROVAL_GATE_FIELDS = {
    "execution_plan_id",
    "approval_required",
    "approval_state",
    "submit_allowed",
    "paper_submit_authorized",
    "live_authorized",
    "broker_mutation_performed",
    "reason",
    "blocker",
}
_DAILY_APPROVAL_GATE_COMPACT_FIELDS = {
    f"daily_approval_gate_{field}" for field in _DAILY_APPROVAL_GATE_FIELDS
}


@pytest.fixture(autouse=True)
def enforce_preflight_offline_only() -> None:
    """Ensure that no credentials or paper profiles are present in the environment."""
    assert not os.environ.get("APP_PROFILE") == "paper"
    for var in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        assert var not in os.environ


def _assert_action_queue_item_shape(item: dict[str, object]) -> None:
    assert set(item) == {
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
    }
    assert item["priority"] in {"P0", "P1", "P2", "P3"}
    assert item["action_type"] in {
        "operator_action",
        "research_action",
        "validation_action",
        "blocked_action",
        "noop",
    }
    assert isinstance(item["reason_codes"], list)
    assert isinstance(item["blocked_by"], list)
    assert isinstance(item["requires_daniel"], bool)
    assert isinstance(item["hard_gate_required"], bool)


def _assert_research_board_item_shape(item: dict[str, object]) -> None:
    assert set(item) == {
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
    }
    assert item["status"] in {
        "active_baseline",
        "candidate",
        "backlog",
        "rejected",
        "blocked",
    }
    assert isinstance(item["missing_evidence"], list)
    assert isinstance(item["promotion_blockers"], list)
    assert isinstance(item["notes"], list)


def _assert_research_candidate_queue_item_shape(item: dict[str, object]) -> None:
    assert set(item) == {
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
    }
    assert item["priority"] in {"P0", "P1", "P2", "P3"}
    assert item["status"] in {
        "queued",
        "waiting_for_review",
        "blocked",
        "repair_required",
    }
    assert isinstance(item["evidence_sources"], list)
    assert isinstance(item["required_data"], list)
    assert isinstance(item["blocked_by"], list)
    assert isinstance(item["requires_daniel"], bool)
    assert isinstance(item["hard_gate_required"], bool)
    assert isinstance(item["promotion_criteria"], list)
    assert isinstance(item["rejection_criteria"], list)


def _assert_paper_observation_readiness_shape(readiness: dict[str, object]) -> None:
    assert set(readiness) == {
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
        "paper_submit_authorized",
        "profit_claim",
        "safety_scope",
        "broker_state_mode",
    }
    assert readiness["paper_observation_readiness_version"] == (
        "assistant_v1.12_paper_observation_readiness"
    )
    assert readiness["status"] == "generated"
    assert str(readiness["artifact_path"]).endswith(
        "paper_observation_readiness.jsonl"
    )
    assert readiness["readiness_status"] == "hard_gate_prepared_not_authorized"
    assert readiness["remaining_gap"] == "paper_observation_summary"
    assert readiness["hard_gate_required"] is True
    assert readiness["requires_daniel"] is True
    assert "Daniel approves read-only paper observation" in str(
        readiness["approval_phrase_required"]
    )
    assert "SPY_position_read" in readiness["allowed_future_read_operations"]
    assert "SPY_open_order_read" in readiness["allowed_future_read_operations"]
    assert "latest_paper_portfolio_snapshot_read" in readiness[
        "allowed_future_read_operations"
    ]
    assert set(readiness["forbidden_future_operations"]) >= {
        "submit",
        "cancel",
        "replace",
        "close",
        "close_all_positions",
        "liquidate",
        "delete",
        "retry mutation",
        "live trading",
    }
    assert readiness["required_preflight_booleans"] == {
        "APP_PROFILE_is_paper": False,
        "ALPACA_API_KEY_loaded": False,
        "ALPACA_API_SECRET_KEY_loaded": False,
        "ALPACA_SECRET_KEY_loaded": False,
        "APCA_API_KEY_ID_loaded": False,
        "APCA_API_SECRET_KEY_loaded": False,
    }
    assert "paper_observation_readiness.jsonl" in readiness[
        "expected_output_artifacts"
    ]
    assert "approval_phrase_missing_or_changed" in readiness["stop_conditions"]
    policy = readiness["broker_state_claim_policy"]
    assert isinstance(policy, dict)
    assert policy["current_mode"] == "broker_state_not_observed"
    assert policy["position_state_claims_allowed"] is False
    assert policy["open_order_state_claims_allowed"] is False
    assert readiness["broker_reads_performed"] is False
    assert readiness["broker_mutation_performed"] is False
    assert readiness["runtime_callouts_performed"] is False
    assert readiness["network_calls_performed"] is False
    assert readiness["paper_submit_authorized"] is False
    assert readiness["profit_claim"] == "none"
    assert readiness["safety_scope"] == "offline_only"
    assert readiness["broker_state_mode"] == "broker_state_not_observed"
    serialized = json.dumps(readiness, sort_keys=True).lower()
    assert "no positions" not in serialized
    assert "no open orders" not in serialized


def _assert_research_board_prioritization_shape(prioritization: dict[str, object]) -> None:
    assert set(prioritization) == {
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
    }
    assert prioritization["research_board_prioritization_version"] == (
        "assistant_v1.13_research_board_prioritization"
    )
    assert prioritization["prioritization_status"] == "ranked"
    assert prioritization["research_mode"] == "offline_research_planning_only"
    assert prioritization["candidate_count"] == 3
    assert prioritization["ranking_method"] == "deterministic_offline_safety_hierarchy"
    assert prioritization["ranking_weights"] == {
        "safety_priority": 1.0,
        "offline_feasibility": 1.0,
        "daniel_approval_deferral": -1.0,
    }
    assert prioritization["top_candidate"] == "build_offline_strategy_comparison_scaffold"
    assert prioritization["selected_next_safe_action"] == "build_offline_strategy_comparison_scaffold"
    assert "broker reads require daniel" in str(prioritization["why_not_broker_observation_yet"]).lower()
    assert prioritization["hard_gate_required"] is False
    assert prioritization["requires_daniel"] is False
    assert prioritization["daniel_action_required_now"] is False
    assert prioritization["safety_scope"] == "offline_only"
    assert prioritization["broker_state_mode"] == "broker_state_not_observed"
    assert prioritization["paper_submit_authorized"] is False
    assert prioritization["profit_claim"] == "none"
    candidates = prioritization["ranked_candidates"]
    assert isinstance(candidates, list)
    assert len(candidates) == 3
    assert {c["candidate_id"] for c in candidates} == {
        "build_offline_strategy_comparison_scaffold",
        "prepare_candidate_strategy_evidence_template",
        "paper_observation_readiness_deferred"
    }


def _assert_strategy_comparison_scaffold_shape(scaffold: dict[str, object]) -> None:
    assert set(scaffold) == {
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
    }
    assert scaffold["scaffold_status"] == "ready"
    assert scaffold["comparison_mode"] == "offline_research_scaffold_only"
    assert scaffold["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert scaffold["baseline_strategy_role"] == "control_harness"
    assert scaffold["selected_next_safe_action"] == (
        "build_candidate_strategy_evidence_template"
    )
    assert "requires deterministic offline evidence comparison first" in str(
        scaffold["why_no_strategy_replacement_yet"]
    ).lower()
    assert scaffold["broker_state_mode"] == "broker_state_not_observed"
    assert scaffold["safety_scope"] == "offline_only"
    assert scaffold["paper_submit_authorized"] is False
    assert scaffold["profit_claim"] == "none"
    assert scaffold["hard_gate_required"] is False
    assert scaffold["requires_daniel"] is False
    assert scaffold["daniel_action_required_now"] is False

    slots = scaffold["candidate_strategy_slots"]
    assert isinstance(slots, list)
    assert slots
    assert {slot["candidate_slot_id"] for slot in slots} == {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }
    for slot in slots:
        assert set(slot) == {
            "candidate_slot_id",
            "candidate_family",
            "implementation_status",
            "evidence_status",
            "promotion_status",
            "hard_gate_required",
            "safety_scope",
        }
        assert slot["implementation_status"] == "placeholder_not_implemented"
        assert slot["hard_gate_required"] is False
        assert slot["safety_scope"] == "offline_only"

    dimensions = scaffold["comparison_dimensions"]
    assert isinstance(dimensions, list)
    assert set(dimensions) >= {
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
    }
    assert isinstance(scaffold["required_evidence_before_promotion"], list)
    assert scaffold["required_evidence_before_promotion"]


def _assert_candidate_strategy_evidence_template_shape(
    template: dict[str, object],
) -> None:
    assert set(template) == {
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
    }
    assert template["template_status"] == "ready"
    assert template["evidence_mode"] == "offline_strategy_evidence_template_only"
    assert template["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert template["baseline_strategy_role"] == "control_harness"
    assert template["selected_next_safe_action"] == (
        "materialize_candidate_evidence_requirements"
    )
    assert "requires an offline evidence template" in str(
        template["why_no_strategy_implementation_yet"]
    ).lower()
    assert "deterministic comparison requirements first" in str(
        template["why_no_strategy_implementation_yet"]
    ).lower()
    assert template["broker_state_mode"] == "broker_state_not_observed"
    assert template["safety_scope"] == "offline_only"
    assert template["paper_submit_authorized"] is False
    assert template["profit_claim"] == "none"
    assert template["hard_gate_required"] is False
    assert template["requires_daniel"] is False
    assert template["daniel_action_required_now"] is False

    families = template["candidate_families"]
    assert isinstance(families, list)
    assert families
    assert {family["candidate_family_id"] for family in families} == {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }
    for family in families:
        assert set(family) == {
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
        }
        assert family["implementation_status"] == "not_implemented"
        assert family["broker_dependency"] == "none"
        assert family["hard_gate_required"] is False
        assert family["safety_scope"] == "offline_only"
        assert isinstance(family["required_inputs"], list)
        assert family["required_inputs"]
        assert isinstance(family["required_metrics"], list)
        assert family["required_metrics"]
        assert isinstance(family["required_safety_checks"], list)
        assert family["required_safety_checks"]

    assert template["required_evidence_sections"] == [
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
    ]
    assert isinstance(template["minimum_promotion_requirements"], list)
    assert template["minimum_promotion_requirements"]
    assert "offline deterministic implementation exists" in template[
        "minimum_promotion_requirements"
    ]
    assert "no broker/network/LLM imports in strategy path" in template[
        "minimum_promotion_requirements"
    ]
    assert isinstance(template["rejection_criteria"], list)
    assert template["rejection_criteria"]
    assert "broker dependency in research path" in template["rejection_criteria"]
    assert isinstance(template["comparison_against_baseline"], dict)
    assert template["comparison_against_baseline"]["baseline_strategy_id"] == (
        "spy_sma_50_200_control"
    )
    assert "candidate_strategy_evidence_template.jsonl" in template[
        "offline_artifacts_required"
    ]
    assert isinstance(template["human_readable_review_questions"], list)
    assert template["human_readable_review_questions"]


def _assert_candidate_evidence_requirements_shape(
    requirements: dict[str, object],
) -> None:
    assert set(requirements) == {
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
    }
    assert requirements["requirements_status"] == "ready"
    assert (
        requirements["requirements_mode"]
        == "offline_candidate_evidence_requirements_only"
    )
    assert requirements["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert requirements["baseline_strategy_role"] == "control_harness"
    assert (
        requirements["selected_next_safe_action"]
        == "build_candidate_evidence_collection_plan"
    )
    assert "offline" in str(requirements["why_selected"]).lower()
    assert "strategy implementation remains blocked" in str(
        requirements["why_no_strategy_implementation_yet"]
    ).lower()
    assert "materialized, collected, and compared against the baseline" in str(
        requirements["why_no_strategy_implementation_yet"]
    ).lower()
    assert requirements["broker_state_mode"] == "broker_state_not_observed"
    assert requirements["safety_scope"] == "offline_only"
    assert requirements["paper_submit_authorized"] is False
    assert requirements["profit_claim"] == "none"
    assert requirements["hard_gate_required"] is False
    assert requirements["requires_daniel"] is False
    assert requirements["daniel_action_required_now"] is False

    candidate_requirements = requirements["candidate_requirements"]
    assert isinstance(candidate_requirements, list)
    assert {candidate["candidate_family_id"] for candidate in candidate_requirements} == {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }
    for candidate in candidate_requirements:
        assert set(candidate) == {
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
        }
        assert candidate["implementation_status"] == "not_implemented"
        assert candidate["promotion_status"] == "promotion_blocked"
        assert candidate["broker_dependency"] == "none"
        assert candidate["hard_gate_required"] is False
        assert candidate["safety_scope"] == "offline_only"
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
            assert isinstance(candidate[list_field], list)
            assert candidate[list_field]
        assert "paper_observation_not_authorized" in candidate["promotion_blockers"]

    shared = requirements["shared_evidence_requirements"]
    assert isinstance(shared, list)
    assert "deterministic_offline_data_source" in shared
    assert "explicit_data_basis" in shared
    assert "benchmark_comparison_against_spy_sma_50_200_control" in shared
    assert "dependency_direction_guard" in shared
    assert "default_pytest_network_guard" in shared
    assert "broker_mutation_invariant" in shared
    assert "no_broker_dependency_in_research_path" in shared
    assert "no_llm_or_agent_dependency_in_strategy_path" in shared

    per_candidate = requirements["per_candidate_missing_evidence"]
    assert isinstance(per_candidate, dict)
    for candidate_id in {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }:
        assert isinstance(per_candidate[candidate_id], list)
        assert per_candidate[candidate_id]
    assert "candidate_strategy_not_implemented" in requirements[
        "promotion_blockers"
    ]
    assert "offline_backtest_not_materialized" in requirements["promotion_blockers"]
    assert "benchmark_comparison_missing" in requirements["promotion_blockers"]
    assert "cost_model_evidence_missing" in requirements["promotion_blockers"]
    assert "drawdown_evidence_missing" in requirements["promotion_blockers"]
    assert "regime_evidence_missing" in requirements["promotion_blockers"]
    assert "turnover_evidence_missing" in requirements["promotion_blockers"]
    assert "paper_observation_not_authorized" in requirements["promotion_blockers"]
    assert "non_deterministic_signal" in requirements["rejection_triggers"]
    assert "broker_dependency_in_research_path" in requirements["rejection_triggers"]
    assert "network_dependency_in_default_pytest" in requirements["rejection_triggers"]
    assert "excessive_turnover_after_costs" in requirements["rejection_triggers"]
    assert "unacceptable_drawdown_vs_baseline" in requirements["rejection_triggers"]
    assert "fragile_single_period_performance" in requirements["rejection_triggers"]
    assert "missing_benchmark_comparison" in requirements["rejection_triggers"]
    assert "missing_regime_analysis" in requirements["rejection_triggers"]
    assert isinstance(requirements["next_research_artifacts_to_build"], list)
    assert "candidate_evidence_collection_plan.jsonl" in requirements[
        "next_research_artifacts_to_build"
    ]


def _assert_candidate_evidence_collection_plan_shape(
    collection_plan: dict[str, object],
) -> None:
    assert set(collection_plan) == {
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
    }
    assert collection_plan["collection_plan_status"] == "ready"
    assert (
        collection_plan["collection_plan_mode"]
        == "offline_candidate_evidence_collection_plan_only"
    )
    assert collection_plan["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert collection_plan["baseline_strategy_role"] == "control_harness"
    assert (
        collection_plan["selected_next_safe_action"]
        == "build_candidate_evidence_collection_status"
    )
    assert "offline" in str(collection_plan["why_selected"]).lower()
    implementation_reason = str(
        collection_plan["why_no_strategy_implementation_yet"]
    ).lower()
    assert "candidate strategy implementation remains blocked" in implementation_reason
    assert "offline evidence collection plan is executed" in implementation_reason
    assert "evidence is compared against the baseline" in implementation_reason
    assert collection_plan["broker_state_mode"] == "broker_state_not_observed"
    assert collection_plan["safety_scope"] == "offline_only"
    assert collection_plan["paper_submit_authorized"] is False
    assert collection_plan["profit_claim"] == "none"
    assert collection_plan["hard_gate_required"] is False
    assert collection_plan["requires_daniel"] is False
    assert collection_plan["daniel_action_required_now"] is False

    candidate_plans = collection_plan["candidate_collection_plans"]
    assert isinstance(candidate_plans, list)
    assert {candidate["candidate_family_id"] for candidate in candidate_plans} == {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }
    for candidate in candidate_plans:
        assert set(candidate) == {
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
        }
        assert candidate["implementation_status"] == "not_implemented"
        assert candidate["evidence_status"] == "evidence_not_collected"
        assert candidate["collection_status"] == "ready_to_collect_offline_evidence"
        assert (
            candidate["promotion_status"]
            == "promotion_blocked_pending_evidence_collection"
        )
        assert candidate["broker_dependency"] == "none"
        assert candidate["hard_gate_required"] is False
        assert candidate["safety_scope"] == "offline_only"
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
            assert isinstance(candidate[list_field], list)
            assert candidate[list_field]

    for list_field in (
        "shared_collection_steps",
        "data_collection_requirements",
        "metric_collection_requirements",
        "safety_collection_requirements",
        "expected_offline_artifacts",
        "blocked_until_collected",
    ):
        assert isinstance(collection_plan[list_field], list)
        assert collection_plan[list_field]

    shared = collection_plan["shared_collection_steps"]
    assert "confirm deterministic offline data source" in shared
    assert "confirm explicit data basis" in shared
    assert "define candidate hypothesis" in shared
    assert "define feature calculations" in shared
    assert "define signal rule" in shared
    assert "define risk rule" in shared
    assert "define backtest window" in shared
    assert "define benchmark comparison against spy_sma_50_200_control" in shared
    assert "define transaction cost assumption" in shared
    assert "collect turnover estimate" in shared
    assert "collect drawdown evidence" in shared
    assert "collect regime sensitivity evidence" in shared
    assert "run dependency-direction guard" in shared
    assert "run default pytest network guard" in shared
    assert "run broker mutation invariant" in shared
    assert "confirm no broker dependency in research path" in shared
    assert "confirm no LLM/agent dependency in strategy path" in shared
    assert (
        "defer paper observation until Daniel explicitly scopes broker read or paper gate"
        in shared
    )

    expected_artifacts = collection_plan["expected_offline_artifacts"]
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
        assert artifact_name in expected_artifacts


def _assert_candidate_evidence_collection_status_shape(
    collection_status: dict[str, object],
) -> None:
    assert set(collection_status) == {
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
    }
    assert collection_status["collection_status"] == "ready"
    assert (
        collection_status["collection_status_mode"]
        == "offline_candidate_evidence_collection_status_only"
    )
    assert collection_status["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert collection_status["baseline_strategy_role"] == "control_harness"
    assert (
        collection_status["selected_next_safe_action"]
        == "build_candidate_evidence_gap_summary"
    )
    assert "offline" in str(collection_status["why_selected"]).lower()
    implementation_reason = str(
        collection_status["why_no_strategy_implementation_yet"]
    ).lower()
    assert "candidate strategy implementation remains blocked" in implementation_reason
    assert "required evidence is collected, statused" in implementation_reason
    assert "compared against the baseline" in implementation_reason
    assert collection_status["broker_state_mode"] == "broker_state_not_observed"
    assert collection_status["safety_scope"] == "offline_only"
    assert collection_status["paper_submit_authorized"] is False
    assert collection_status["profit_claim"] == "none"
    assert collection_status["hard_gate_required"] is False
    assert collection_status["requires_daniel"] is False
    assert collection_status["daniel_action_required_now"] is False

    counts = collection_status["evidence_status_counts"]
    assert isinstance(counts, dict)
    assert set(counts) == {"not_started", "blocked", "ready_to_collect", "missing"}
    assert all(isinstance(value, int) and value > 0 for value in counts.values())
    for list_field in (
        "not_started_evidence",
        "blocked_evidence",
        "ready_to_collect_evidence",
        "missing_evidence",
        "promotion_blockers",
        "next_collection_actions",
    ):
        assert isinstance(collection_status[list_field], list)
        assert collection_status[list_field]
    assert "build_candidate_evidence_gap_summary" in collection_status[
        "next_collection_actions"
    ]

    candidate_statuses = collection_status["candidate_statuses"]
    assert isinstance(candidate_statuses, list)
    assert {candidate["candidate_family_id"] for candidate in candidate_statuses} == {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }
    for candidate in candidate_statuses:
        assert set(candidate) == {
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
        }
        assert candidate["current_status"] == "blocked"
        assert candidate["implementation_status"] == "not_implemented"
        assert candidate["evidence_status"] == "missing"
        assert candidate["collection_status"] == "ready_to_collect"
        assert candidate["promotion_status"] == "blocked"
        assert candidate["broker_dependency"] == "none"
        assert candidate["hard_gate_required"] is False
        assert candidate["safety_scope"] == "offline_only"
        for list_field in (
            "evidence_items",
            "not_started_items",
            "blocked_items",
            "ready_to_collect_items",
            "missing_items",
            "promotion_blockers",
            "next_collection_actions",
        ):
            assert isinstance(candidate[list_field], list)
            assert candidate[list_field]
        evidence_items = candidate["evidence_items"]
        assert {item["status"] for item in evidence_items} == {
            "not_started",
            "blocked",
            "ready_to_collect",
            "missing",
        }
        for evidence_item in evidence_items:
            assert set(evidence_item) == {
                "evidence_item_id",
                "evidence_item_label",
                "evidence_category",
                "status",
                "blocker",
                "required_before_implementation",
                "required_before_promotion",
                "offline_only",
                "broker_dependency",
            }
            assert evidence_item["status"] in {
                "not_started",
                "blocked",
                "ready_to_collect",
                "missing",
            }
            assert evidence_item["blocker"]
            assert evidence_item["required_before_implementation"] is True
            assert evidence_item["required_before_promotion"] is True
            assert evidence_item["offline_only"] is True
            assert evidence_item["broker_dependency"] == "none"

    shared = collection_status["shared_collection_status"]
    assert isinstance(shared, list)
    assert shared
    shared_ids = {item["shared_status_id"] for item in shared}
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
        assert shared_id in shared_ids
    for item in shared:
        assert item["status"] in {"not_started", "blocked", "ready_to_collect", "missing"}
        assert item["offline_only"] is True
        assert item["broker_dependency"] == "none"


def _assert_candidate_evidence_gap_summary_shape(
    gap_summary: dict[str, object],
) -> None:
    assert set(gap_summary) == {
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
    }
    assert gap_summary["gap_summary_status"] == "ready"
    assert (
        gap_summary["gap_summary_mode"]
        == "offline_candidate_evidence_gap_summary_only"
    )
    assert gap_summary["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert gap_summary["baseline_strategy_role"] == "control_harness"
    assert gap_summary["selected_next_safe_action"] == (
        "build_candidate_gap_closure_queue"
    )
    assert "offline" in str(gap_summary["why_selected"]).lower()
    implementation_reason = str(
        gap_summary["why_no_strategy_implementation_yet"]
    ).lower()
    assert "candidate strategy implementation remains blocked" in implementation_reason
    assert (
        "evidence gaps are summarized, prioritized, closed"
        in implementation_reason
    )
    assert "compared against the baseline" in implementation_reason
    assert gap_summary["broker_state_mode"] == "broker_state_not_observed"
    assert gap_summary["safety_scope"] == "offline_only"
    assert gap_summary["paper_submit_authorized"] is False
    assert gap_summary["profit_claim"] == "none"
    assert gap_summary["hard_gate_required"] is False
    assert gap_summary["requires_daniel"] is False
    assert gap_summary["daniel_action_required_now"] is False

    candidate_gap_summaries = gap_summary["candidate_gap_summaries"]
    assert isinstance(candidate_gap_summaries, list)
    assert {item["candidate_family_id"] for item in candidate_gap_summaries} == {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }
    for candidate in candidate_gap_summaries:
        assert set(candidate) == {
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
        }
        assert candidate["current_status"] == "blocked"
        assert candidate["implementation_status"] == "not_implemented"
        assert candidate["evidence_status"] == "missing"
        assert candidate["collection_status"] == "ready_to_collect"
        assert candidate["promotion_status"] == "blocked"
        assert candidate["total_gap_count"] == len(candidate["evidence_gaps"])
        assert candidate["highest_priority_gap"] in {
            gap["gap_id"] for gap in candidate["evidence_gaps"]
        }
        assert candidate["broker_dependency"] == "none"
        assert candidate["hard_gate_required"] is False
        assert candidate["safety_scope"] == "offline_only"
        for list_field in (
            "evidence_gaps",
            "blocked_gaps",
            "missing_gaps",
            "not_started_gaps",
            "ready_to_collect_gaps",
            "promotion_blockers",
            "next_gap_closure_actions",
        ):
            assert isinstance(candidate[list_field], list)
            assert candidate[list_field]
        assert {gap["status"] for gap in candidate["evidence_gaps"]} == {
            "not_started",
            "blocked",
            "ready_to_collect",
            "missing",
        }
        assert {"high", "medium"} <= {
            gap["priority"] for gap in candidate["evidence_gaps"]
        }
        for gap in candidate["evidence_gaps"]:
            assert set(gap) == {
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
            }
            assert gap["priority"] in {"high", "medium", "low"}
            assert gap["status"] in {
                "not_started",
                "blocked",
                "ready_to_collect",
                "missing",
            }
            assert gap["required_before_implementation"] is True
            assert gap["required_before_promotion"] is True
            assert str(gap["closure_artifact"]).endswith(".jsonl")
            assert gap["offline_only"] is True
            assert gap["broker_dependency"] == "none"

    ranked_gap_groups = gap_summary["ranked_gap_groups"]
    assert isinstance(ranked_gap_groups, list)
    assert [group["group_id"] for group in ranked_gap_groups] == [
        "strategy_definition_gaps",
        "data_and_feature_gaps",
        "backtest_and_benchmark_gaps",
        "cost_turnover_drawdown_gaps",
        "regime_and_failure_mode_gaps",
        "safety_and_dependency_gaps",
        "paper_observation_deferred_gaps",
    ]
    for group in ranked_gap_groups:
        assert set(group) == {
            "group_id",
            "group_label",
            "priority",
            "gap_count",
            "why_ranked_here",
            "next_gap_closure_action",
        }
        assert group["priority"] in {"high", "medium", "low"}
        assert isinstance(group["gap_count"], int)
        assert group["gap_count"] > 0
        assert group["why_ranked_here"]
        assert group["next_gap_closure_action"]

    assert gap_summary["highest_priority_gaps"]
    assert gap_summary["shared_gap_summary"]
    counts = gap_summary["gap_counts"]
    assert isinstance(counts, dict)
    assert counts["total_gap_count"] > 0
    assert counts["candidate_gap_count"] > 0
    assert counts["shared_gap_count"] > 0
    assert counts["ranked_gap_group_count"] == len(ranked_gap_groups)
    assert set(counts["by_status"]) == {
        "not_started",
        "blocked",
        "ready_to_collect",
        "missing",
    }
    assert all(value > 0 for value in counts["by_status"].values())
    assert set(counts["by_priority"]) == {"high", "medium", "low"}
    assert all(value > 0 for value in counts["by_priority"].values())
    assert gap_summary["next_gap_closure_actions"]
    assert (
        gap_summary["selected_next_safe_action"]
        in gap_summary["next_gap_closure_actions"]
    )
    assert gap_summary["next_research_artifacts_to_build"]


def _assert_candidate_gap_closure_queue_shape(queue: dict[str, object]) -> None:
    assert set(queue) == {
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
    }
    assert queue["candidate_gap_closure_queue_version"] == (
        "assistant_v1.20_candidate_gap_closure_queue"
    )
    assert queue["queue_status"] == "ready"
    assert queue["queue_mode"] == "offline_candidate_gap_closure_queue_only"
    assert str(queue["artifact_path"]).endswith("candidate_gap_closure_queue.jsonl")
    assert str(queue["source_gap_summary_path"]).endswith(
        "candidate_evidence_gap_summary.jsonl"
    )
    assert queue["source_gap_summary_status"] == "ready"
    assert queue["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert queue["baseline_strategy_role"] == "control_harness"
    assert queue["selected_next_safe_action_type"] == (
        "candidate_gap_closure_queue_item"
    )
    assert queue["selected_work_order"] == "codex_work_order"
    assert queue["selected_owner"] == "Codex"
    assert isinstance(queue["generation_inputs"], list)
    assert "candidate_evidence_gap_summary.ranked_gap_groups" in queue[
        "generation_inputs"
    ]
    assert isinstance(queue["allowed_scope"], list)
    assert "offline evidence collection" in queue["allowed_scope"]
    assert isinstance(queue["forbidden_scope"], list)
    for forbidden in (
        "broker observation",
        "broker reads",
        "broker mutation",
        "paper submit",
        "live trading",
        "network calls",
    ):
        assert forbidden in queue["forbidden_scope"]
    assert isinstance(queue["acceptance_criteria"], list)
    assert "offline" in str(queue["why_selected"]).lower()
    implementation_reason = str(
        queue["why_no_strategy_implementation_yet"]
    ).lower()
    assert "candidate strategy implementation remains blocked" in implementation_reason
    assert "offline evidence artifacts are materialized" in implementation_reason
    assert "spy sma 50/200 control harness" in implementation_reason
    assert queue["broker_state_mode"] == "broker_state_not_observed"
    assert queue["broker_state_observed"] is False
    assert queue["paper_submit_authorized"] is False
    assert queue["daniel_action_required_now"] is False
    assert queue["profit_claim"] == "none"
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "paper_lab_only",
        "profit_claim=none",
    ):
        assert label in queue["safety_labels"]

    queue_items = queue["queue_items"]
    assert isinstance(queue_items, list)
    assert queue_items
    assert queue["queue_item_count"] == len(queue_items)
    assert queue["selected_queue_item_id"] == queue_items[0]["queue_item_id"]
    assert queue["selected_next_safe_action"] == queue_items[0]["action_id"]
    assert queue["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_001"
    )
    assert queue["next_research_artifacts_to_build"] == [
        item["expected_evidence_artifact"] for item in queue_items
    ]
    for index, item in enumerate(queue_items, start=1):
        assert set(item) == {
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
        }
        assert item["queue_item_id"] == (
            f"candidate_gap_closure_queue_item_{index:03d}"
        )
        assert item["action_id"] == (
            f"execute_candidate_gap_closure_queue_item_{index:03d}"
        )
        assert item["rank"] == index
        assert item["priority"] in {"high", "medium", "low"}
        assert item["action_priority"] in {"P2", "P3"}
        assert item["candidate_family"]
        assert item["candidate_family_id"]
        assert item["gap_group_id"]
        assert item["gap_id"]
        assert item["closure_action"]
        assert "offline packet evidence" in item["closure_objective"]
        assert str(item["expected_evidence_artifact"]).endswith(".jsonl")
        assert item["recommended_agent"] == "Codex"
        assert isinstance(item["allowed_scope"], list)
        assert isinstance(item["forbidden_scope"], list)
        assert "broker reads" in item["forbidden_scope"]
        assert isinstance(item["acceptance_criteria"], list)
        assert isinstance(item["blocked_by"], list)
        assert item["daniel_action_required"] is False
        assert item["broker_state_mode"] == "broker_state_not_observed"
        assert item["broker_state_observed"] is False
        assert item["paper_submit_authorized"] is False
        assert item["profit_claim"] == "none"
        for token in (
            "offline_only",
            "research_only",
            "not_live_authorized",
            "broker_state_not_observed",
            "paper_submit_not_authorized",
            "profit_claim=none",
        ):
            assert token in item["safety_scope"]


def _assert_candidate_signal_rule_status_shape(status: dict[str, object]) -> None:
    assert set(status) == {
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
    }
    assert status["signal_rule_status_version"] == (
        "assistant_v1.26_candidate_signal_rule_status"
    )
    assert status["signal_rule_status"] == "ready"
    assert status["signal_rule_status_mode"] == (
        "offline_candidate_signal_rule_status_only"
    )
    assert status["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert status["source_queue_item_id"] == "candidate_gap_closure_queue_item_006"
    assert status["source_action_id"] == "execute_candidate_gap_closure_queue_item_006"
    assert status["source_gap_id"] == "candidate_signal_rule_status"
    assert (
        status["source_candidate_family_id"]
        == "volatility_or_regime_filter_candidate"
    )
    assert status["source_candidate_family"] == "Volatility or regime filter candidate"
    assert status["source_gap_status"] == "blocked"
    assert status["source_gap_group_id"] == "strategy_definition_gaps"
    assert status["source_gap_group_label"] == "Strategy definition gaps"
    assert status["source_closure_action"] == "close_strategy_definition_gaps"
    assert "candidate_signal_rule_status.jsonl" in status["source_closure_objective"]
    assert "offline packet evidence" in status["source_closure_objective"]
    assert status["source_expected_evidence_artifact"] == (
        "candidate_signal_rule_status.jsonl"
    )
    assert status["broker_state_mode"] == "broker_state_not_observed"
    assert status["paper_submit_authorized"] is False
    assert status["daniel_action_required_now"] is False
    assert status["profit_claim"] == "none"
    assert status["safety_scope"] == "offline_only"
    assert status["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_007"
    )
    assert status["selected_next_safe_action"] in status[
        "next_signal_rule_closure_actions"
    ]
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        assert label in status["safety_labels"]

    summaries = status["candidate_signal_rule_summaries"]
    assert isinstance(summaries, list)
    assert summaries
    assert status["candidate_family_count"] == len(summaries)
    assert status["candidate_scope_count"] == len(summaries)
    assert status["shared_scope_count"] == len(status["shared_signal_rule_gaps"])
    assert status["target_candidate_signal_rule_summary"]["candidate_family_id"] == (
        "volatility_or_regime_filter_candidate"
    )
    assert status["target_candidate_signal_rule_summary"]["signal_rule_evidence_status"] == (
        "blocked"
    )
    assert status["target_explicit_signal_rule_evidence"] == status[
        "target_candidate_signal_rule_summary"
    ]["explicit_signal_rule_evidence"]
    assert status["target_explicit_signal_rule_evidence"][
        "explicit_signal_rules_present"
    ] is False
    condition_evidence = status["target_regime_or_volatility_condition_evidence"]
    assert condition_evidence["condition_evidence_mode"] == (
        "deterministic_local_packet_evidence_only"
    )
    assert condition_evidence["condition_evidence_status"] == "blocked"
    assert condition_evidence["candidate_family_id"] == (
        "volatility_or_regime_filter_candidate"
    )
    assert condition_evidence["explicit_volatility_or_regime_condition_present"] is False
    assert condition_evidence["required_condition_features"] == [
        "volatility_or_regime_state_feature",
        "filter_thresholds_fixed_before_test",
        "interaction_with_baseline_or_candidate_signal_defined",
    ]
    assert condition_evidence["required_regime_analysis"] == [
        "low_volatility_regime_performance_split",
        "high_volatility_regime_performance_split",
        "regime_transition_period_review",
    ]
    assert condition_evidence["planned_regime_outputs_to_collect"] == [
        "low_volatility_regime_performance_split",
        "high_volatility_regime_performance_split",
        "regime_transition_period_review",
    ]
    assert condition_evidence["evidence_item_statuses"] == {
        "candidate_feature_definition_status": "not_started",
        "candidate_signal_rule_status": "blocked",
        "candidate_drawdown_regime_status": "missing",
    }
    assert condition_evidence["status_only_materialization_status"] == (
        "blocked_missing_explicit_signal_rule_evidence"
    )
    assert "feature_calculation_definition_missing" in condition_evidence[
        "remaining_missing_condition_evidence"
    ]
    assert "regime_sensitivity_evidence_missing" in condition_evidence[
        "remaining_missing_condition_evidence"
    ]
    assert condition_evidence["remaining_missing_signal_rule_evidence"] == status[
        "target_remaining_missing_signal_rule_evidence"
    ]
    assert condition_evidence["broker_state_mode"] == "broker_state_not_observed"
    assert condition_evidence["paper_submit_authorized"] is False
    assert condition_evidence["profit_claim"] == "none"
    assert status["target_materialized_candidate_signal_specification"] == status[
        "target_candidate_signal_rule_summary"
    ]["materialized_candidate_signal_specification"]
    assert status["target_materialized_candidate_signal_specification"][
        "materialized_signal_rules"
    ] == []
    assert status["target_materialized_candidate_signal_specification"][
        "implementation_status"
    ] == "not_implemented"
    assert status["target_remaining_missing_signal_rule_evidence"] == status[
        "target_candidate_signal_rule_summary"
    ]["remaining_missing_signal_rule_evidence"]
    assert status["target_remaining_missing_signal_rule_evidence"]
    assert status["target_candidate_signal_readiness"] == status[
        "target_candidate_signal_rule_summary"
    ]["candidate_signal_readiness"]
    assert status["target_candidate_signal_readiness"]["readiness_status"] == "blocked"
    assert status["target_candidate_signal_readiness"]["research_ready"] is False
    assert status["target_candidate_signal_readiness"]["evidence_ready"] is False
    assert status["target_candidate_signal_readiness"]["still_blocked"] is True
    assert status["evidence_status_summary"]["status_categories"] == [
        "complete",
        "incomplete",
        "blocked",
        "not_applicable",
    ]
    assert status["evidence_status_summary"]["missing_evidence_explicit"] is True
    assert status["evidence_status_summary"]["blocked"] == len(summaries)
    assert status["evidence_status_summary"]["complete"] == 0
    assert status["evidence_status_summary"]["not_applicable"] == 0
    assert {item["candidate_family_id"] for item in summaries} == {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }
    for summary in summaries:
        assert set(summary) == {
            "candidate_family",
            "candidate_family_id",
            "candidate_label",
            "candidate_family_label",
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
            "promotion_blockers",
            "missing_signal_rule_evidence",
            "evidence_status_breakdown",
            "recommended_closure_action",
            "expected_evidence_artifact",
        }
        assert summary["candidate_family"] == summary["candidate_family_id"]
        assert summary["signal_rule_status"] == "incomplete"
        assert summary["signal_rule_evidence_status"] == "blocked"
        assert summary["signal_rule_defined"] is False
        assert summary["signal_inputs_defined"] is False
        assert summary["indicator_or_feature_definition_defined"] is False
        assert summary["entry_rule_defined"] is False
        assert summary["exit_rule_defined"] is False
        assert summary["lookback_or_parameter_bounds_defined"] is False
        assert summary["data_basis_defined"] is False
        assert summary["universe_defined"] is False
        assert summary["rebalance_or_evaluation_schedule_defined"] is False
        assert summary["leakage_or_lookahead_guard_defined"] is False
        assert summary["explicit_signal_rule_evidence"][
            "evidence_mode"
        ] == "deterministic_local_packet_evidence_only"
        assert summary["explicit_signal_rule_evidence"][
            "explicit_signal_rules_present"
        ] is False
        assert summary["explicit_signal_rule_evidence"]["local_evidence_items"]
        assert summary["materialized_candidate_signal_specification"][
            "materialization_mode"
        ] == "offline_status_only_no_strategy_rules_created"
        assert summary["materialized_candidate_signal_specification"][
            "materialized_signal_rules"
        ] == []
        assert summary["materialized_candidate_signal_specification"][
            "implementation_status"
        ] == "not_implemented"
        assert summary["materialized_candidate_signal_specification"][
            "promotion_status"
        ] == "not_promoted"
        assert summary["materialized_candidate_signal_specification"][
            "paper_submit_authorized"
        ] is False
        assert summary["materialized_candidate_signal_specification"][
            "profit_claim"
        ] == "none"
        assert summary["remaining_missing_signal_rule_evidence"] == summary[
            "missing_signal_rule_evidence"
        ]
        assert summary["candidate_signal_readiness"]["readiness_status"] == "blocked"
        assert summary["candidate_signal_readiness"]["research_ready"] is False
        assert summary["candidate_signal_readiness"]["evidence_ready"] is False
        assert summary["candidate_signal_readiness"]["still_blocked"] is True
        assert summary["promotion_blockers"]
        assert summary["missing_signal_rule_evidence"]
        assert any(
            "candidate_signal_rule_status" in str(item)
            for item in summary["missing_signal_rule_evidence"]
        )
        breakdown = summary["evidence_status_breakdown"]
        assert set(breakdown) == {
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        }
        assert isinstance(breakdown["complete"], list)
        assert isinstance(breakdown["incomplete"], list)
        assert isinstance(breakdown["blocked"], list)
        assert isinstance(breakdown["not_applicable"], list)
        assert breakdown["blocked"]
        assert breakdown["incomplete"]
        assert any(
            "candidate_signal_rule_status" in str(item)
            for item in breakdown["blocked"] + breakdown["incomplete"]
        )
        assert str(summary["recommended_closure_action"]).startswith(
            f"close_{summary['candidate_family_id']}_signal_rule_definition_gap"
        )
        assert str(summary["expected_evidence_artifact"]).endswith(
            "_signal_spec_packet"
        )
    assert status["shared_signal_rule_gaps"]
    assert status["highest_priority_signal_rule_gaps"]
    assert status["signal_rule_acceptance_criteria"]


def _assert_candidate_risk_rule_status_shape(status: dict[str, object]) -> None:
    assert set(status) == {
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
    }
    assert status["risk_rule_status_version"] == (
        "assistant_v1.23_candidate_risk_rule_status"
    )
    assert status["risk_rule_status"] == "ready"
    assert status["risk_rule_status_mode"] == (
        "offline_candidate_risk_rule_status_only"
    )
    assert status["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert status["source_queue_item_id"] == "candidate_gap_closure_queue_item_003"
    assert status["source_action_id"] == "execute_candidate_gap_closure_queue_item_003"
    assert status["source_gap_id"] == "candidate_risk_rule_status"
    assert (
        status["source_candidate_family_id"]
        == "volatility_or_regime_filter_candidate"
    )
    assert status["source_candidate_family"] == "Volatility or regime filter candidate"
    assert status["source_gap_status"] == "blocked"
    assert status["source_gap_group_id"] == "strategy_definition_gaps"
    assert status["source_gap_group_label"] == "Strategy definition gaps"
    assert status["source_closure_action"] == "close_strategy_definition_gaps"
    assert "candidate_risk_rule_status.jsonl" in status["source_closure_objective"]
    assert "offline packet evidence" in status["source_closure_objective"]
    assert status["source_expected_evidence_artifact"] == (
        "candidate_risk_rule_status.jsonl"
    )
    assert status["broker_state_mode"] == "broker_state_not_observed"
    assert status["paper_submit_authorized"] is False
    assert status["daniel_action_required_now"] is False
    assert status["profit_claim"] == "none"
    assert status["safety_scope"] == "offline_only"
    assert status["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_004"
    )
    assert status["selected_next_safe_action"] in status[
        "next_risk_rule_closure_actions"
    ]
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        assert label in status["safety_labels"]

    summaries = status["candidate_risk_rule_summaries"]
    assert isinstance(summaries, list)
    assert summaries
    assert status["candidate_family_count"] == len(summaries)
    assert status["candidate_scope_count"] == len(summaries)
    assert status["shared_scope_count"] == len(status["shared_risk_rule_gaps"])
    assert status["target_candidate_risk_rule_summary"]["candidate_family_id"] == (
        "volatility_or_regime_filter_candidate"
    )
    assert status["target_candidate_risk_rule_summary"]["risk_rule_evidence_status"] == (
        "blocked"
    )
    assert status["evidence_status_summary"]["status_categories"] == [
        "complete",
        "incomplete",
        "blocked",
        "not_applicable",
    ]
    assert status["evidence_status_summary"]["missing_evidence_explicit"] is True
    assert status["evidence_status_summary"]["blocked"] == len(summaries)
    assert status["evidence_status_summary"]["complete"] == 0
    assert status["evidence_status_summary"]["not_applicable"] == 0
    assert {item["candidate_family_id"] for item in summaries} == {
        "momentum_or_trend_candidate",
        "mean_reversion_candidate",
        "volatility_or_regime_filter_candidate",
    }
    for summary in summaries:
        assert set(summary) == {
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
        }
        assert summary["candidate_family"] == summary["candidate_family_id"]
        assert summary["risk_rule_status"] == "incomplete"
        assert summary["risk_rule_evidence_status"] == "blocked"
        assert summary["risk_rule_defined"] is False
        assert summary["position_sizing_defined"] is False
        assert summary["max_loss_or_drawdown_rule_defined"] is False
        assert summary["entry_exit_risk_boundary_defined"] is False
        assert summary["stop_or_deactivation_rule_defined"] is False
        assert summary["data_quality_risk_rule_defined"] is False
        assert summary["promotion_blockers"]
        assert summary["missing_risk_rule_evidence"]
        assert any(
            "candidate_risk_rule_status" in str(item)
            for item in summary["missing_risk_rule_evidence"]
        )
        breakdown = summary["evidence_status_breakdown"]
        assert set(breakdown) == {
            "complete",
            "incomplete",
            "blocked",
            "not_applicable",
        }
        assert isinstance(breakdown["complete"], list)
        assert isinstance(breakdown["incomplete"], list)
        assert isinstance(breakdown["blocked"], list)
        assert isinstance(breakdown["not_applicable"], list)
        assert breakdown["blocked"]
        assert breakdown["incomplete"]
        assert any(
            "candidate_risk_rule_status" in str(item)
            for item in breakdown["blocked"] + breakdown["incomplete"]
        )
        assert str(summary["recommended_closure_action"]).startswith(
            f"close_{summary['candidate_family_id']}_risk_rule_definition_gap"
        )
        assert str(summary["expected_evidence_artifact"]).endswith(
            "_risk_spec_packet"
        )
    assert status["shared_risk_rule_gaps"]
    assert status["highest_priority_risk_rule_gaps"]
    assert status["risk_rule_acceptance_criteria"]


def _assert_shared_risk_rule_status_shape(status: dict[str, object]) -> None:
    assert set(status) == {
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
    }
    assert status["shared_risk_rule_status_version"] == (
        "assistant_v1.27_shared_risk_rule_status"
    )
    assert status["shared_risk_rule_status"] == "ready"
    assert status["shared_risk_rule_status_mode"] == (
        "offline_shared_risk_rule_status_only"
    )
    assert status["deterministic_scope"] == "shared_candidate_risk_rule_status"
    assert status["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert status["source_queue_item_id"] == "candidate_gap_closure_queue_item_007"
    assert status["source_action_id"] == "execute_candidate_gap_closure_queue_item_007"
    assert status["source_gap_id"] == "risk_rule_status"
    assert status["source_candidate_family_id"] == "shared"
    assert status["source_candidate_family"] == "Shared candidate evidence"
    assert status["source_gap_status"] == "blocked"
    assert status["source_gap_group_id"] == "strategy_definition_gaps"
    assert status["source_gap_group_label"] == "Strategy definition gaps"
    assert status["source_closure_action"] == "close_strategy_definition_gaps"
    assert "shared_risk_rule_status.jsonl" in status["source_closure_objective"]
    assert "offline packet evidence" in status["source_closure_objective"]
    assert status["source_expected_evidence_artifact"] == (
        "shared_risk_rule_status.jsonl"
    )
    assert status["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_008"
    )
    assert status["selected_next_safe_action"] in status[
        "next_shared_risk_rule_closure_actions"
    ]
    assert status["broker_state_mode"] == "broker_state_not_observed"
    assert status["paper_submit_authorized"] is False
    assert status["daniel_action_required_now"] is False
    assert status["profit_claim"] == "none"
    assert status["safety_scope"] == "offline_only"
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        assert label in status["safety_labels"]

    assert status["shared_risk_rule_status_item"]["shared_status_id"] == (
        "risk_rule_status"
    )
    assert status["shared_risk_rule_status_item"]["status"] == "blocked"
    assert status["shared_risk_rule_status_item"]["blocker"] == (
        "candidate_signal_rule_missing"
    )
    assert status["shared_risk_rule_gaps"]
    assert status["shared_scope_count"] == len(status["shared_risk_rule_gaps"])
    assert status["candidate_family_count"] == 3
    assert len(status["candidate_risk_rule_summaries"]) == 3
    assert status["explicit_shared_risk_rule_evidence"][
        "evidence_mode"
    ] == "deterministic_local_packet_evidence_only"
    assert status["explicit_shared_risk_rule_evidence"][
        "evidence_status"
    ] == "blocked"
    assert status["explicit_shared_risk_rule_evidence"][
        "explicit_risk_rules_present"
    ] is False
    assert status["explicit_shared_risk_rule_evidence"]["local_evidence_items"]

    for bucket_name in (
        "position_sizing_evidence",
        "stop_or_exit_evidence",
        "drawdown_or_exposure_control_evidence",
        "portfolio_or_risk_cap_evidence",
    ):
        bucket = status[bucket_name]
        assert bucket["evidence_mode"] == "deterministic_local_packet_evidence_only"
        assert bucket["evidence_status"] == "missing"
        assert bucket["explicit_rules_present"] is False
        assert isinstance(bucket["candidate_evidence"], list)
        assert len(bucket["candidate_evidence"]) == 3

    materialized = status["materialized_shared_risk_specification"]
    assert materialized["materialization_mode"] == (
        "offline_status_only_no_strategy_rules_created"
    )
    assert materialized["materialization_status"] == (
        "blocked_missing_shared_risk_rule_evidence"
    )
    assert materialized["explicit_risk_rules_present"] is False
    assert materialized["materialized_risk_rules"] == []
    assert materialized["position_sizing_rules"] == []
    assert materialized["stop_or_exit_rules"] == []
    assert materialized["drawdown_or_exposure_controls"] == []
    assert materialized["portfolio_or_risk_cap_rules"] == []
    assert materialized["implementation_status"] == "not_implemented"
    assert materialized["promotion_status"] == "not_promoted"
    assert materialized["broker_state_mode"] == "broker_state_not_observed"
    assert materialized["paper_submit_authorized"] is False
    assert materialized["profit_claim"] == "none"

    missing = status["remaining_missing_shared_risk_evidence"]
    assert missing
    assert any("shared_risk_rule_status:blocked" in str(item) for item in missing)
    assert any("shared_risk_rule_gap_status:blocked" in str(item) for item in missing)
    assert any("candidate_signal_rule_missing" in str(item) for item in missing)
    assert status["target_shared_risk_readiness"]["readiness_status"] == "blocked"
    assert status["target_shared_risk_readiness"]["research_ready"] is False
    assert status["target_shared_risk_readiness"]["evidence_ready"] is False
    assert status["target_shared_risk_readiness"]["still_blocked"] is True
    assert status["target_shared_risk_status"]["status"] == "blocked"
    assert status["highest_priority_remaining_gaps"]
    assert status["evidence_status_summary"]["shared_scope_status"] == "blocked"
    assert status["evidence_status_summary"]["shared_scope_blocked"] is True
    assert status["evidence_status_summary"][
        "shared_missing_evidence_explicit"
    ] is True
    assert status["evidence_status_summary"]["blocked"] == 3
    assert status["shared_risk_rule_acceptance_criteria"]


def _assert_shared_signal_rule_status_shape(status: dict[str, object]) -> None:
    assert set(status) == {
        "shared_signal_rule_status_version",
        "shared_signal_rule_status",
        "shared_signal_rule_status_mode",
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
        "shared_signal_rule_status_item",
        "shared_signal_rule_gaps",
        "candidate_signal_rule_summaries",
        "explicit_shared_signal_rule_evidence",
        "entry_condition_evidence",
        "exit_condition_evidence",
        "universe_or_filter_evidence",
        "time_horizon_evidence",
        "confirmation_or_invalidation_evidence",
        "materialized_shared_signal_specification",
        "remaining_missing_shared_signal_evidence",
        "target_shared_signal_readiness",
        "target_shared_signal_status",
        "highest_priority_remaining_gaps",
        "evidence_status_summary",
        "shared_signal_rule_acceptance_criteria",
        "next_shared_signal_rule_closure_actions",
        "selected_next_safe_action",
        "broker_state_mode",
        "paper_submit_authorized",
        "daniel_action_required_now",
        "profit_claim",
        "safety_scope",
        "safety_labels",
    }
    assert status["shared_signal_rule_status_version"] == (
        "assistant_v1.28_shared_signal_rule_status"
    )
    assert status["shared_signal_rule_status"] == "ready"
    assert status["shared_signal_rule_status_mode"] == (
        "offline_shared_signal_rule_status_only"
    )
    assert status["deterministic_scope"] == "shared_candidate_signal_rule_status"
    assert status["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert status["source_queue_item_id"] == "candidate_gap_closure_queue_item_008"
    assert status["source_action_id"] == "execute_candidate_gap_closure_queue_item_008"
    assert status["source_gap_id"] == "signal_rule_status"
    assert status["source_candidate_family_id"] == "shared"
    assert status["source_candidate_family"] == "Shared candidate evidence"
    assert status["source_gap_status"] == "blocked"
    assert status["source_gap_group_id"] == "strategy_definition_gaps"
    assert status["source_gap_group_label"] == "Strategy definition gaps"
    assert status["source_closure_action"] == "close_strategy_definition_gaps"
    assert "shared_signal_rule_status.jsonl" in status["source_closure_objective"]
    assert "offline packet evidence" in status["source_closure_objective"]
    assert status["source_expected_evidence_artifact"] == (
        "shared_signal_rule_status.jsonl"
    )
    assert status["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_009"
    )
    assert status["selected_next_safe_action"] in status[
        "next_shared_signal_rule_closure_actions"
    ]
    assert status["broker_state_mode"] == "broker_state_not_observed"
    assert status["paper_submit_authorized"] is False
    assert status["daniel_action_required_now"] is False
    assert status["profit_claim"] == "none"
    assert status["safety_scope"] == "offline_only"
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        assert label in status["safety_labels"]

    assert status["shared_signal_rule_status_item"]["shared_status_id"] == (
        "signal_rule_status"
    )
    assert status["shared_signal_rule_status_item"]["status"] == "blocked"
    assert status["shared_signal_rule_status_item"]["blocker"] in {
        "candidate_benchmark_comparison_missing",
        "candidate_hypothesis_and_feature_definition_missing",
    }
    assert status["shared_signal_rule_gaps"]
    assert status["shared_scope_count"] == len(status["shared_signal_rule_gaps"])
    assert status["candidate_family_count"] == 3
    assert len(status["candidate_signal_rule_summaries"]) == 3
    assert status["explicit_shared_signal_rule_evidence"][
        "evidence_mode"
    ] == "deterministic_local_packet_evidence_only"
    assert status["explicit_shared_signal_rule_evidence"][
        "evidence_status"
    ] == "blocked"
    assert status["explicit_shared_signal_rule_evidence"][
        "explicit_signal_rules_present"
    ] is False
    assert status["explicit_shared_signal_rule_evidence"]["local_evidence_items"]

    for bucket_name in (
        "entry_condition_evidence",
        "exit_condition_evidence",
        "universe_or_filter_evidence",
        "time_horizon_evidence",
        "confirmation_or_invalidation_evidence",
    ):
        bucket = status[bucket_name]
        assert bucket["evidence_mode"] == "deterministic_local_packet_evidence_only"
        assert bucket["evidence_status"] == "missing"
        assert bucket["explicit_rules_present"] is False
        assert isinstance(bucket["candidate_evidence"], list)
        assert len(bucket["candidate_evidence"]) == 3

    materialized = status["materialized_shared_signal_specification"]
    assert materialized["materialization_mode"] == (
        "offline_status_only_no_strategy_rules_created"
    )
    assert materialized["materialization_status"] == (
        "blocked_missing_shared_signal_rule_evidence"
    )
    assert materialized["explicit_signal_rules_present"] is False
    assert materialized["materialized_signal_rules"] == []
    assert materialized["entry_conditions"] == []
    assert materialized["exit_conditions"] == []
    assert materialized["universe_filters"] == []
    assert materialized["time_horizons"] == []
    assert materialized["confirmation_rules"] == []
    assert materialized["implementation_status"] == "not_implemented"
    assert materialized["promotion_status"] == "not_promoted"
    assert materialized["broker_state_mode"] == "broker_state_not_observed"
    assert materialized["paper_submit_authorized"] is False
    assert materialized["profit_claim"] == "none"

    missing = status["remaining_missing_shared_signal_evidence"]
    assert missing
    assert any("shared_signal_rule_status:blocked" in str(item) for item in missing)
    assert any("shared_signal_rule_gap_status:blocked" in str(item) for item in missing)
    assert any(
        "candidate_benchmark_comparison_missing" in str(item)
        or "candidate_hypothesis_and_feature_definition_missing" in str(item)
        for item in missing
    )
    assert status["target_shared_signal_readiness"]["readiness_status"] == "blocked"
    assert status["target_shared_signal_readiness"]["research_ready"] is False
    assert status["target_shared_signal_readiness"]["evidence_ready"] is False
    assert status["target_shared_signal_readiness"]["still_blocked"] is True
    assert status["target_shared_signal_status"]["status"] == "blocked"
    assert status["highest_priority_remaining_gaps"]
    assert status["evidence_status_summary"]["shared_scope_status"] == "blocked"
    assert status["evidence_status_summary"]["shared_scope_blocked"] is True
    assert status["evidence_status_summary"][
        "shared_missing_evidence_explicit"
    ] is True
    assert status["evidence_status_summary"]["blocked"] == 3
    assert status["shared_signal_rule_acceptance_criteria"]


def _assert_shared_benchmark_comparison_status_shape(status: dict[str, object]) -> None:
    assert set(status) == {
        "shared_benchmark_comparison_status_version",
        "shared_benchmark_comparison_status",
        "shared_benchmark_comparison_status_mode",
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
        "shared_benchmark_comparison_status_item",
        "shared_benchmark_comparison_gaps",
        "candidate_benchmark_comparison_summaries",
        "explicit_shared_benchmark_comparison_evidence",
        "performance_metrics_evidence",
        "drawdown_comparison_evidence",
        "beta_or_correlation_evidence",
        "risk_adjusted_return_evidence",
        "benchmark_comparison_readiness",
        "remaining_missing_shared_benchmark_comparison_evidence",
        "highest_priority_remaining_gaps",
        "evidence_status_summary",
        "shared_benchmark_comparison_acceptance_criteria",
        "next_shared_benchmark_comparison_closure_actions",
        "selected_next_safe_action",
        "broker_state_mode",
        "paper_submit_authorized",
        "daniel_action_required_now",
        "profit_claim",
        "safety_scope",
        "safety_labels",
    }
    assert status["shared_benchmark_comparison_status_version"] == (
        "assistant_v1.29_shared_benchmark_comparison_status"
    )
    assert status["shared_benchmark_comparison_status"] == "ready"
    assert status["shared_benchmark_comparison_status_mode"] == (
        "offline_shared_benchmark_comparison_status_only"
    )
    assert status["deterministic_scope"] == "shared_candidate_benchmark_comparison_status"
    assert status["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert status["source_queue_item_id"] == "candidate_gap_closure_queue_item_009"
    assert status["source_action_id"] == "execute_candidate_gap_closure_queue_item_009"
    assert status["source_gap_id"] == "benchmark_comparison_status"
    assert status["source_candidate_family_id"] == "shared"
    assert status["source_candidate_family"] == "Shared candidate evidence"
    assert status["source_gap_status"] in {"blocked", "missing", "incomplete"}
    assert status["source_gap_group_id"] == "backtest_and_benchmark_gaps"
    assert status["source_gap_group_label"] == "Backtest and benchmark gaps"
    assert status["source_closure_action"] == "materialize_candidate_backtest_benchmark_gap_packets"
    assert "shared_benchmark_comparison_status.jsonl" in status["source_closure_objective"]
    assert "offline packet evidence" in status["source_closure_objective"]
    assert status["source_expected_evidence_artifact"] == (
        "shared_benchmark_comparison_status.jsonl"
    )
    assert status["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_010"
    )
    assert status["selected_next_safe_action"] in status[
        "next_shared_benchmark_comparison_closure_actions"
    ]
    assert status["broker_state_mode"] == "broker_state_not_observed"
    assert status["paper_submit_authorized"] is False
    assert status["daniel_action_required_now"] is False
    assert status["profit_claim"] == "none"
    assert status["safety_scope"] == "offline_only"
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        assert label in status["safety_labels"]

    assert status["shared_benchmark_comparison_status_item"]["shared_status_id"] == (
        "benchmark_comparison_status"
    )
    assert status["shared_benchmark_comparison_status_item"]["status"] in {"blocked", "missing", "incomplete"}
    assert isinstance(status["shared_benchmark_comparison_status_item"].get("blocker", "none"), str)
    assert status["shared_benchmark_comparison_gaps"]
    assert status["shared_scope_count"] == len(status["shared_benchmark_comparison_gaps"])
    assert status["candidate_family_count"] == 3
    assert len(status["candidate_benchmark_comparison_summaries"]) == 3
    assert status["explicit_shared_benchmark_comparison_evidence"][
        "evidence_mode"
    ] == "deterministic_local_packet_evidence_only"
    assert status["explicit_shared_benchmark_comparison_evidence"][
        "evidence_status"
    ] in {"blocked", "missing", "incomplete"}
    assert status["explicit_shared_benchmark_comparison_evidence"][
        "explicit_benchmark_comparison_rules_present"
    ] is False
    assert status["explicit_shared_benchmark_comparison_evidence"]["local_evidence_items"]

    for bucket_name in (
        "performance_metrics_evidence",
        "drawdown_comparison_evidence",
        "beta_or_correlation_evidence",
        "risk_adjusted_return_evidence",
    ):
        bucket = status[bucket_name]
        assert bucket["evidence_mode"] == "deterministic_local_packet_evidence_only"
        assert bucket["evidence_status"] == "missing"
        assert bucket["explicit_rules_present"] is False
        assert isinstance(bucket["candidate_evidence"], list)
        assert len(bucket["candidate_evidence"]) == 3

    missing = status["remaining_missing_shared_benchmark_comparison_evidence"]
    assert missing
    assert any(
        "shared_benchmark_comparison_status:" in str(item)
        for item in missing
    )
    assert any(
        "shared_benchmark_comparison_gap_status:" in str(item)
        for item in missing
    )
    assert status["benchmark_comparison_readiness"]["readiness_status"] in {"blocked", "not_ready"}
    assert status["benchmark_comparison_readiness"]["research_ready"] is False
    assert status["benchmark_comparison_readiness"]["evidence_ready"] is False
    assert status["evidence_status_summary"]["shared_scope_status"] in {"blocked", "missing", "incomplete"}
    assert status["shared_benchmark_comparison_acceptance_criteria"]


def _assert_candidate_backtest_result_packet_shape(status: dict[str, object]) -> None:
    assert set(status) == {
        "candidate_backtest_result_packet_version",
        "candidate_backtest_result_packet",
        "candidate_backtest_outputs_status",
        "candidate_backtest_result_packet_mode",
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
        "candidate_backtest_result_packet_acceptance_criteria",
        "next_candidate_backtest_result_packet_closure_actions",
        "selected_next_safe_action",
        "broker_state_mode",
        "paper_submit_authorized",
        "daniel_action_required_now",
        "profit_claim",
        "safety_scope",
        "safety_labels",
    }
    assert status["candidate_backtest_result_packet_version"] == (
        "assistant_v1.32_candidate_backtest_result_packet"
    )
    assert status["candidate_backtest_result_packet"] == "ready"
    assert status["candidate_backtest_outputs_status"] == "ready"
    assert status["candidate_backtest_result_packet_mode"] == (
        "offline_candidate_backtest_result_packet_only"
    )
    assert status["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert status["source_queue_item_id"] == "candidate_gap_closure_queue_item_012"
    assert status["source_action_id"] == "execute_candidate_gap_closure_queue_item_012"
    assert status["source_gap_id"] == "candidate_backtest_outputs_status"
    assert (
        status["source_candidate_family_id"]
        == "volatility_or_regime_filter_candidate"
    )
    assert status["source_candidate_family"] == "Volatility or regime filter candidate"
    assert status["source_gap_status"] in {"blocked", "missing", "incomplete"}
    assert status["source_gap_group_id"] == "backtest_and_benchmark_gaps"
    assert status["source_gap_group_label"] == "Backtest and benchmark gaps"
    assert status["source_closure_action"] == "materialize_candidate_backtest_benchmark_gap_packets"
    assert "candidate_backtest_result_packet.jsonl" in status["source_closure_objective"]
    assert "offline packet evidence" in status["source_closure_objective"]
    assert status["source_expected_evidence_artifact"] == (
        "candidate_backtest_result_packet.jsonl"
    )
    assert (
        status["selected_next_safe_action"]
        == _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert status["next_candidate_backtest_result_packet_closure_actions"] == []
    assert status["broker_state_mode"] == "broker_state_not_observed"
    assert status["paper_submit_authorized"] is False
    assert status["daniel_action_required_now"] is False
    assert status["profit_claim"] == "none"
    assert status["safety_scope"] == "offline_only"
    for label in (
        "offline_only",
        "research_only",
        "signal_evaluation_only",
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
    ):
        assert label in status["safety_labels"]


def _assert_research_candidate_queue_shape(queue: dict[str, object]) -> None:
    assert set(queue) == {
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
    }
    assert queue["research_candidate_queue_version"] == (
        "assistant_v1.7_research_candidate_queue"
    )
    assert queue["status"] == "generated"
    assert str(queue["artifact_path"]).endswith("research_candidate_queue.jsonl")
    assert str(queue["paper_observation_readiness_path"]).endswith(
        "paper_observation_readiness.jsonl"
    )
    _assert_paper_observation_readiness_shape(
        queue["paper_observation_readiness"]
    )
    assert queue["generation_mode"] == (
        "deterministic_offline_from_packet_evidence"
    )
    assert queue["priority_rules"] == {
        "P0": "safety invariant or quality gate failure",
        "P1": "missing operator/data/review evidence required to interpret current packet",
        "P2": "offline research work that improves strategy evaluation",
        "P3": "backlog or future enhancements",
    }
    candidates = queue["candidates"]
    assert isinstance(candidates, list)
    assert queue["candidate_count"] == len(candidates)
    assert candidates
    for item in candidates:
        _assert_research_candidate_queue_item_shape(item)
    priorities = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    assert candidates == sorted(
        candidates,
        key=lambda item: (priorities[item["priority"]], item["candidate_id"]),
    )
    assert queue["top_candidate_id"] == candidates[0]["candidate_id"]
    assert queue["top_candidate_priority"] == candidates[0]["priority"]


def _assert_next_action_selector_shape(selector: dict[str, object]) -> None:
    assert set(selector) == {
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
        "shared_signal_rule_status_path",
        "shared_signal_rule_status",
        "shared_benchmark_comparison_status_path",
        "shared_benchmark_comparison_status",
        "candidate_backtest_result_packet_path",
        "candidate_backtest_result_packet",
        "source_state",
    }
    assert selector["next_action_selector_version"] == (
        "assistant_v1.6_next_action_selector"
    )
    assert selector["priority"] in {"P0", "P1", "P2", "P3"}
    assert str(selector["selected_work_order_path"]).endswith(".md")
    assert "work_orders/" in str(selector["selected_work_order_path"]).replace(
        "\\",
        "/",
    )
    assert str(selector["research_candidate_queue_path"]).endswith(
        "research_candidate_queue.jsonl"
    )
    assert str(selector["paper_observation_readiness_path"]).endswith(
        "paper_observation_readiness.jsonl"
    )
    _assert_paper_observation_readiness_shape(
        selector["paper_observation_readiness"]
    )
    assert str(selector["research_board_prioritization_path"]).endswith(
        "research_board_prioritization.jsonl"
    )
    _assert_research_board_prioritization_shape(
        selector["research_board_prioritization"]
    )
    assert str(selector["strategy_comparison_scaffold_path"]).endswith(
        "strategy_comparison_scaffold.jsonl"
    )
    _assert_strategy_comparison_scaffold_shape(
        selector["strategy_comparison_scaffold"]
    )
    assert str(selector["candidate_strategy_evidence_template_path"]).endswith(
        "candidate_strategy_evidence_template.jsonl"
    )
    _assert_candidate_strategy_evidence_template_shape(
        selector["candidate_strategy_evidence_template"]
    )
    assert str(selector["candidate_evidence_requirements_path"]).endswith(
        "candidate_evidence_requirements.jsonl"
    )
    _assert_candidate_evidence_requirements_shape(
        selector["candidate_evidence_requirements"]
    )
    assert str(selector["candidate_evidence_collection_plan_path"]).endswith(
        "candidate_evidence_collection_plan.jsonl"
    )
    _assert_candidate_evidence_collection_plan_shape(
        selector["candidate_evidence_collection_plan"]
    )
    assert str(selector["candidate_evidence_collection_status_path"]).endswith(
        "candidate_evidence_collection_status.jsonl"
    )
    _assert_candidate_evidence_collection_status_shape(
        selector["candidate_evidence_collection_status"]
    )
    assert str(selector["candidate_evidence_gap_summary_path"]).endswith(
        "candidate_evidence_gap_summary.jsonl"
    )
    _assert_candidate_evidence_gap_summary_shape(
        selector["candidate_evidence_gap_summary"]
    )
    assert str(selector["candidate_gap_closure_queue_path"]).endswith(
        "candidate_gap_closure_queue.jsonl"
    )
    _assert_candidate_gap_closure_queue_shape(
        selector["candidate_gap_closure_queue"]
    )
    assert str(selector["candidate_risk_rule_status_path"]).endswith(
        "candidate_risk_rule_status.jsonl"
    )
    _assert_candidate_risk_rule_status_shape(
        selector["candidate_risk_rule_status"]
    )
    assert str(selector["candidate_signal_rule_status_path"]).endswith(
        "candidate_signal_rule_status.jsonl"
    )
    _assert_candidate_signal_rule_status_shape(
        selector["candidate_signal_rule_status"]
    )
    assert str(selector["shared_risk_rule_status_path"]).endswith(
        "shared_risk_rule_status.jsonl"
    )
    _assert_shared_risk_rule_status_shape(
        selector["shared_risk_rule_status"]
    )
    assert str(selector["shared_signal_rule_status_path"]).endswith(
        "shared_signal_rule_status.jsonl"
    )
    _assert_shared_signal_rule_status_shape(
        selector["shared_signal_rule_status"]
    )
    assert str(selector["shared_benchmark_comparison_status_path"]).endswith(
        "shared_benchmark_comparison_status.jsonl"
    )
    _assert_shared_benchmark_comparison_status_shape(
        selector["shared_benchmark_comparison_status"]
    )
    assert str(selector["candidate_backtest_result_packet_path"]).endswith(
        "candidate_backtest_result_packet.jsonl"
    )
    _assert_candidate_backtest_result_packet_shape(
        selector["candidate_backtest_result_packet"]
    )
    assert selector["source_state"]
    if selector["selected_research_candidate_priority"] is not None:
        assert selector["selected_research_candidate_priority"] in {
            "P0",
            "P1",
            "P2",
            "P3",
        }
    assert isinstance(selector["reason_codes"], list)
    assert isinstance(selector["forbidden_actions"], list)
    assert isinstance(selector["source_state"], dict)
    assert selector["broker_action_allowed"] is False
    assert selector["capital_action_allowed"] is False
    assert selector["llm_runtime_calls_allowed"] is False
    assert selector["network_runtime_calls_allowed"] is False


def _assert_work_order_exports_shape(exports: dict[str, object]) -> None:
    assert exports["work_order_exports_version"] == "assistant_v1.6_work_order_exports"
    assert exports["status"] == "generated"
    assert exports["artifact_count"] == 4
    assert exports["generation_mode"] == "deterministic_offline_markdown_only"
    assert exports["runtime_callouts_performed"] is False
    assert str(exports["research_candidate_queue_path"]).endswith(
        "research_candidate_queue.jsonl"
    )
    assert str(exports["baseline_evidence_metrics_path"]).endswith(
        "baseline_evidence_metrics.jsonl"
    )
    assert str(exports["paper_observation_readiness_path"]).endswith(
        "paper_observation_readiness.jsonl"
    )
    _assert_paper_observation_readiness_shape(
        exports["paper_observation_readiness"]
    )
    assert exports["paper_observation_readiness_status"] == (
        "hard_gate_prepared_not_authorized"
    )
    assert str(exports["research_board_prioritization_path"]).endswith(
        "research_board_prioritization.jsonl"
    )
    _assert_research_board_prioritization_shape(
        exports["research_board_prioritization"]
    )
    assert exports["research_board_prioritization_status"] == "ranked"
    assert str(exports["strategy_comparison_scaffold_path"]).endswith(
        "strategy_comparison_scaffold.jsonl"
    )
    _assert_strategy_comparison_scaffold_shape(
        exports["strategy_comparison_scaffold"]
    )
    assert exports["strategy_comparison_scaffold_status"] == "ready"
    assert str(exports["candidate_strategy_evidence_template_path"]).endswith(
        "candidate_strategy_evidence_template.jsonl"
    )
    _assert_candidate_strategy_evidence_template_shape(
        exports["candidate_strategy_evidence_template"]
    )
    assert exports["candidate_strategy_evidence_template_status"] == "ready"
    assert str(exports["candidate_evidence_requirements_path"]).endswith(
        "candidate_evidence_requirements.jsonl"
    )
    _assert_candidate_evidence_requirements_shape(
        exports["candidate_evidence_requirements"]
    )
    assert exports["candidate_evidence_requirements_status"] == "ready"
    assert str(exports["candidate_evidence_collection_plan_path"]).endswith(
        "candidate_evidence_collection_plan.jsonl"
    )
    _assert_candidate_evidence_collection_plan_shape(
        exports["candidate_evidence_collection_plan"]
    )
    assert exports["candidate_evidence_collection_plan_status"] == "ready"
    assert str(exports["candidate_evidence_collection_status_path"]).endswith(
        "candidate_evidence_collection_status.jsonl"
    )
    _assert_candidate_evidence_collection_status_shape(
        exports["candidate_evidence_collection_status"]
    )
    assert exports["candidate_evidence_collection_status_status"] == "ready"
    assert str(exports["candidate_evidence_gap_summary_path"]).endswith(
        "candidate_evidence_gap_summary.jsonl"
    )
    _assert_candidate_evidence_gap_summary_shape(
        exports["candidate_evidence_gap_summary"]
    )
    assert exports["candidate_evidence_gap_summary_status"] == "ready"
    assert str(exports["candidate_gap_closure_queue_path"]).endswith(
        "candidate_gap_closure_queue.jsonl"
    )
    _assert_candidate_gap_closure_queue_shape(exports["candidate_gap_closure_queue"])
    assert exports["candidate_gap_closure_queue_status"] == "ready"
    assert exports["candidate_gap_closure_queue_selected_item_id"] == (
        "candidate_gap_closure_queue_item_001"
    )
    assert exports["candidate_gap_closure_queue_selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_001"
    )
    assert str(exports["candidate_risk_rule_status_path"]).endswith(
        "candidate_risk_rule_status.jsonl"
    )
    _assert_candidate_risk_rule_status_shape(exports["candidate_risk_rule_status"])
    assert exports["candidate_risk_rule_status_status"] == "ready"
    assert exports["candidate_risk_rule_status_selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_004"
    )
    assert str(exports["candidate_signal_rule_status_path"]).endswith(
        "candidate_signal_rule_status.jsonl"
    )
    _assert_candidate_signal_rule_status_shape(exports["candidate_signal_rule_status"])
    assert exports["candidate_signal_rule_status_status"] == "ready"
    assert exports["candidate_signal_rule_status_selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_007"
    )
    assert str(exports["shared_risk_rule_status_path"]).endswith(
        "shared_risk_rule_status.jsonl"
    )
    _assert_shared_risk_rule_status_shape(exports["shared_risk_rule_status"])
    assert exports["shared_risk_rule_status_status"] == "ready"
    assert exports["shared_risk_rule_status_selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_008"
    )
    assert str(exports["shared_signal_rule_status_path"]).endswith(
        "shared_signal_rule_status.jsonl"
    )
    _assert_shared_signal_rule_status_shape(exports["shared_signal_rule_status"])
    assert exports["shared_signal_rule_status_status"] == "ready"
    assert exports["shared_signal_rule_status_selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_009"
    )
    assert str(exports["shared_benchmark_comparison_status_path"]).endswith(
        "shared_benchmark_comparison_status.jsonl"
    )
    _assert_shared_benchmark_comparison_status_shape(exports["shared_benchmark_comparison_status"])
    assert exports["shared_benchmark_comparison_status_status"] == "ready"
    assert exports["shared_benchmark_comparison_status_selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_010"
    )
    assert str(exports["candidate_backtest_result_packet_path"]).endswith(
        "candidate_backtest_result_packet.jsonl"
    )
    _assert_candidate_backtest_result_packet_shape(
        exports["candidate_backtest_result_packet"]
    )
    assert exports["candidate_backtest_result_packet_status"] == "ready"
    assert exports["candidate_backtest_result_packet_selected_next_safe_action"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert exports["metric_artifact_ingest_status"] in {
        "metric_artifacts_missing",
        "metric_artifacts_partially_ingested",
        "metric_artifacts_ingested",
        "metric_artifacts_parse_failed",
    }
    assert exports["turnover_artifact_ingest_status"] in {
        "turnover_artifact_missing",
        "turnover_artifact_ingested",
        "turnover_artifact_parse_failed",
    }
    assert exports["cost_model_artifact_ingest_status"] in {
        "cost_model_artifact_missing",
        "cost_model_artifact_ingested",
        "cost_model_artifact_parse_failed",
    }
    assert exports["turnover_metric_status"] in {
        "metrics_available",
        "metrics_partially_available",
        "metrics_missing",
    }
    assert exports["cost_model_status"] in {
        "metrics_available",
        "metrics_partially_available",
        "metrics_missing",
    }
    for field_name in (
        "metric_artifact_paths",
        "metric_artifact_hashes",
        "metric_artifact_parse_status",
        "metric_artifact_record_count",
    ):
        assert isinstance(exports[field_name], dict)
    assert str(exports["turnover_artifact_path"]).endswith("turnover_summary.jsonl")
    assert str(exports["cost_model_artifact_path"]).endswith("cost_model_summary.jsonl")
    assert exports["turnover_artifact_parse_status"] in {
        "missing",
        "path_not_file",
        "unreadable",
        "decode_error",
        "json_decode_error",
        "record_not_object",
        "empty",
        "ambiguous_record_count",
        "parsed",
    }
    assert exports["cost_model_artifact_parse_status"] in {
        "missing",
        "path_not_file",
        "unreadable",
        "decode_error",
        "json_decode_error",
        "record_not_object",
        "empty",
        "ambiguous_record_count",
        "parsed",
    }
    assert isinstance(exports["remaining_missing_metric_sources"], list)
    assert "etf-sma-authorized-adjusted-baseline-metrics" in str(
        exports["next_safe_metric_command"]
    )
    assert isinstance(exports["artifact_prerequisite_chain"], list)
    assert "turnover_summary.jsonl" in " ".join(exports["artifact_prerequisite_chain"])
    assert "cost_model_summary.jsonl" in " ".join(exports["artifact_prerequisite_chain"])
    assert "paper_observation_summary" in " ".join(
        exports["artifact_prerequisite_chain"]
    )
    assert exports["top_research_candidate_id"]
    assert str(exports["directory"]).endswith("work_orders")
    artifacts = exports["artifacts"]
    assert isinstance(artifacts, dict)
    assert set(artifacts) == {
        "gpt_next_action_handoff",
        "codex_work_order",
        "antigravity_review_order",
        "claude_critique_order",
    }
    for artifact_id, artifact in artifacts.items():
        assert artifact["status"] == "generated"
        assert artifact["path"].endswith(".md")
        assert artifact_id in artifact["path"]


def _assert_baseline_health_evaluation_shape(evaluation: dict[str, object]) -> None:
    assert set(evaluation) == {
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
    }
    assert evaluation["baseline_health_evaluation_version"] == (
        "assistant_v1.8_baseline_health_evaluation"
    )
    assert evaluation["status"] == "generated"
    assert str(evaluation["artifact_path"]).endswith("baseline_health_evaluation.jsonl")
    assert evaluation["generation_mode"] == (
        "deterministic_offline_from_packet_evidence"
    )
    assert evaluation["baseline_id"] == "spy_sma_50_200_daily_long_only"
    assert evaluation["baseline_name"] == "SPY SMA 50/200 daily long-only baseline"
    assert evaluation["baseline_role"] == (
        "controlled_baseline_harness_for_assistant_evaluation"
    )
    assert evaluation["active_symbol"] == "SPY"
    assert evaluation["active_strategy"] == "SMA 50/200"
    assert evaluation["broker_state_mode"] == "broker_state_not_observed"
    assert evaluation["blocker_status"] == "broker_state_not_observed"
    assert evaluation["health_status"] in {
        "usable_control_harness",
        "evidence_incomplete",
        "blocked_by_quality_gate",
        "blocked_by_safety",
        "not_ready_for_paper_submit",
        "deprecated_candidate",
    }
    assert evaluation["evidence_status"] in {
        "daily_signal_evidence_available",
        "evidence_incomplete",
        "not_evaluated",
    }
    assert evaluation["paper_submit_readiness_status"] == (
        "not_ready_for_paper_submit"
    )
    assert evaluation["baseline_evidence_metrics_status"] in {
        "generated",
        "not_generated",
    }
    assert evaluation["baseline_evidence_snapshot_status"] in {
        "metrics_available",
        "metrics_partially_available",
        "metrics_missing",
    }
    assert evaluation["baseline_metric_confidence_status"] in {
        "confidence_not_yet_quantified",
        "offline_confidence_quantified",
    }
    assert evaluation["baseline_metric_artifact_ingest_status"] in {
        "metric_artifacts_missing",
        "metric_artifacts_partially_ingested",
        "metric_artifacts_ingested",
        "metric_artifacts_parse_failed",
    }
    assert isinstance(evaluation["baseline_metric_artifact_parse_status"], dict)
    assert isinstance(evaluation["baseline_remaining_missing_metric_sources"], list)
    assert str(evaluation["paper_observation_readiness_path"]).endswith(
        "paper_observation_readiness.jsonl"
    )
    _assert_paper_observation_readiness_shape(
        evaluation["paper_observation_readiness"]
    )
    assert str(evaluation["baseline_evidence_metrics_path"]).endswith(
        "baseline_evidence_metrics.jsonl"
    )
    assert "etf-sma-authorized-adjusted-baseline-metrics" in str(
        evaluation["next_safe_metric_command"]
    )
    assert evaluation["next_safe_test"] == (
        "python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py "
        "-k baseline_health_evaluation"
    )
    for list_field in (
        "known_strengths",
        "known_weaknesses",
        "missing_evidence",
        "required_next_artifacts",
        "promotion_criteria",
        "deprecation_criteria",
    ):
        assert isinstance(evaluation[list_field], list)
    assert isinstance(evaluation["requires_daniel"], bool)
    assert isinstance(evaluation["hard_gate_required"], bool)
    assert "offline_preview_only" in str(evaluation["safety_scope"])
    assert "broker_state_not_observed" in json.dumps(evaluation, sort_keys=True)


def _assert_baseline_evidence_metrics_shape(metrics: dict[str, object]) -> None:
    assert set(metrics) == {
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
    }
    assert metrics["baseline_evidence_metrics_version"] == (
        "assistant_v1.9_baseline_evidence_metrics"
    )
    assert metrics["status"] == "generated"
    assert str(metrics["artifact_path"]).endswith("baseline_evidence_metrics.jsonl")
    assert metrics["generation_mode"] == "deterministic_offline_from_packet_evidence"
    assert metrics["baseline_id"] == "spy_sma_50_200_daily_long_only"
    assert metrics["baseline_name"] == "SPY SMA 50/200 daily long-only baseline"
    assert metrics["active_symbol"] == "SPY"
    assert metrics["active_strategy"] == "SMA 50/200"
    assert metrics["evidence_snapshot_status"] in {
        "metrics_available",
        "metrics_partially_available",
        "metrics_missing",
    }
    assert metrics["metric_confidence_status"] in {
        "confidence_not_yet_quantified",
        "offline_confidence_quantified",
    }
    assert metrics["metric_artifact_ingest_status"] in {
        "metric_artifacts_missing",
        "metric_artifacts_partially_ingested",
        "metric_artifacts_ingested",
        "metric_artifacts_parse_failed",
    }
    assert metrics["turnover_artifact_ingest_status"] in {
        "turnover_artifact_missing",
        "turnover_artifact_ingested",
        "turnover_artifact_parse_failed",
    }
    assert metrics["cost_model_artifact_ingest_status"] in {
        "cost_model_artifact_missing",
        "cost_model_artifact_ingested",
        "cost_model_artifact_parse_failed",
    }
    for mapping_field in (
        "metric_artifact_paths",
        "metric_artifact_hashes",
        "metric_artifact_parse_status",
        "metric_artifact_record_count",
        "quantified_metric_summary",
    ):
        assert isinstance(metrics[mapping_field], dict)
    expected_artifact_ids = {
        "baseline_authorized_adjusted_metrics",
        "offline_backtest_confidence_summary",
        "adjusted_close_evidence",
        "turnover_summary",
        "cost_model_summary",
    }
    assert set(metrics["metric_artifact_paths"]) == expected_artifact_ids
    assert set(metrics["metric_artifact_parse_status"]) == expected_artifact_ids
    assert set(metrics["metric_artifact_record_count"]) == expected_artifact_ids
    assert metrics["backtest_confidence_summary_status"] in {
        "metrics_available",
        "metrics_missing",
    }
    assert metrics["benchmark_metric_status"] in {
        "metrics_available",
        "metrics_missing",
    }
    assert metrics["benchmark_comparison_status"] in {
        "metrics_available",
        "metrics_missing",
    }
    assert metrics["backtest_metric_status"] in {
        "metrics_available",
        "metrics_missing",
    }
    assert metrics["drawdown_metric_status"] in {
        "metrics_available",
        "metrics_missing",
    }
    assert metrics["turnover_metric_status"] in {
        "metrics_available",
        "metrics_partially_available",
        "metrics_missing",
    }
    assert metrics["cost_model_status"] in {
        "metrics_available",
        "metrics_partially_available",
        "metrics_missing",
    }
    assert str(metrics["turnover_artifact_path"]).endswith("turnover_summary.jsonl")
    assert str(metrics["cost_model_artifact_path"]).endswith("cost_model_summary.jsonl")
    assert metrics["turnover_artifact_parse_status"] in {
        "missing",
        "path_not_file",
        "unreadable",
        "decode_error",
        "json_decode_error",
        "record_not_object",
        "empty",
        "ambiguous_record_count",
        "parsed",
    }
    assert metrics["cost_model_artifact_parse_status"] in {
        "missing",
        "path_not_file",
        "unreadable",
        "decode_error",
        "json_decode_error",
        "record_not_object",
        "empty",
        "ambiguous_record_count",
        "parsed",
    }
    assert metrics["paper_observation_status"] == "broker_state_not_observed"
    assert str(metrics["paper_observation_readiness_path"]).endswith(
        "paper_observation_readiness.jsonl"
    )
    _assert_paper_observation_readiness_shape(
        metrics["paper_observation_readiness"]
    )
    assert metrics["broker_state_mode"] == "broker_state_not_observed"
    assert metrics["paper_submit_readiness_status"] == "not_ready_for_paper_submit"
    assert metrics["profit_claim"] == "none"
    for list_field in (
        "available_metric_sources",
        "missing_metric_sources",
        "remaining_missing_metric_sources",
        "required_next_artifacts",
        "artifact_prerequisite_chain",
        "promotion_criteria",
        "deprecation_criteria",
    ):
        assert isinstance(metrics[list_field], list)
    assert metrics["remaining_missing_metric_sources"] == metrics[
        "missing_metric_sources"
    ]
    if metrics["metric_artifact_ingest_status"] == "metric_artifacts_missing":
        assert metrics["metric_artifact_hashes"] == {}
        assert metrics["quantified_metric_summary"] == {}
        assert metrics["metric_confidence_status"] == "confidence_not_yet_quantified"
        assert all(
            status == "missing"
            for status in metrics["metric_artifact_parse_status"].values()
        )
        assert all(
            count == 0 for count in metrics["metric_artifact_record_count"].values()
        )
        assert (
            "offline_backtest_confidence_summary" in metrics["missing_metric_sources"]
        )
        assert "drawdown_summary" in metrics["missing_metric_sources"]
    assert "paper_observation_summary" in metrics["missing_metric_sources"]
    assert "baseline_authorized_adjusted_metrics.jsonl" in " ".join(
        metrics["required_next_artifacts"]
    )
    assert "turnover_summary.jsonl" in " ".join(metrics["required_next_artifacts"])
    assert "cost_model_summary.jsonl" in " ".join(metrics["required_next_artifacts"])
    assert "paper_observation_summary" in " ".join(
        metrics["artifact_prerequisite_chain"]
    )
    assert "etf-sma-authorized-adjusted-baseline-metrics" in str(
        metrics["next_safe_metric_command"]
    )
    assert "baseline_authorized_adjusted_metrics.jsonl" in str(
        metrics["next_safe_metric_command"]
    )
    assert metrics["requires_daniel"] is False
    assert metrics["hard_gate_required"] is False
    assert "offline_preview_only" in str(metrics["safety_scope"])
    assert "broker_state_not_observed" in json.dumps(metrics, sort_keys=True)


def _assert_quality_gate_pass(container: dict[str, object]) -> None:
    expected_check_ids = [
        "required_packet_artifacts_exist",
        "required_operating_record_fields_exist",
        "required_manifest_fields_exist",
        "markdown_brief_references_key_assistant_sections",
        "broker_state_mode_explicit",
        "broker_not_observed_has_no_position_order_claim",
        "paper_submit_not_authorized",
        "executive_action_queue_priorities_deterministic",
        "research_board_has_spy_sma_50_200_active_baseline",
        "research_candidate_queue_generated",
        "baseline_health_evaluation_generated",
        "baseline_evidence_metrics_generated",
        "paper_observation_readiness_generated",
        "strategy_comparison_scaffold_generated",
        "candidate_strategy_evidence_template_generated",
        "candidate_evidence_requirements_generated",
        "candidate_evidence_collection_plan_generated",
        "candidate_evidence_collection_status_generated",
        "candidate_evidence_gap_summary_generated",
        "candidate_gap_closure_queue_generated",
        "candidate_risk_rule_status_generated",
        "candidate_signal_rule_status_generated",
        "shared_risk_rule_status_generated",
        "shared_signal_rule_status_generated",
        "shared_benchmark_comparison_status_generated",
        "candidate_backtest_result_packet_generated",
        "baseline_metric_artifact_ingest_status_explicit",
        "turnover_and_cost_model_artifacts_explicit",
        "assistant_v1_through_v1_11_outputs_preserved",
        "history_delta_exists",
        "safety_labels_exist",
        "review_handoff_references_generated_artifacts",
        "decision_ledger_status_recorded",
        "review_classification_normalized",
        "review_input_path_hash_recorded_when_present",
        "review_selected_next_action_safety_scoped",
        "next_action_selector_safety_scoped",
        "work_order_exports_generated",
    ]
    assert container["quality_gate_version"] == "assistant_v1.4_quality_gate"
    assert container["quality_gate_status"] == "pass"
    assert container["quality_gate_score"] == (
        "38/38 required checks passed; 0 failed; 0 warnings"
    )
    assert container["quality_gate_passed_required_count"] == 38
    assert container["quality_gate_failed_required_count"] == 0
    assert container["quality_gate_warning_count"] == 0
    assert container["quality_gate_required_fields_present"] is True
    assert container["quality_gate_failed_checks"] == []
    assert container["quality_gate_warning_checks"] == []
    assert container["quality_gate_optional_checks"] == []
    required_checks = container["quality_gate_required_checks"]
    assert isinstance(required_checks, list)
    assert [check["check_id"] for check in required_checks] == expected_check_ids
    assert all(check["status"] == "pass" for check in required_checks)
    assert container["review_handoff_version"] == "assistant_v1.4_review_handoff"
    assert str(container["review_handoff_path"]).endswith("review_handoff.md")
    assert container["review_handoff_status"] == "generated"


def test_etf_sma_daily_paper_lab_success_bullish(tmp_path: Path) -> None:
    """Test successful run with 200 bullish bars."""
    output_root = tmp_path / "paper_lab_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    config = EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=bars_csv,
        as_of_date="2025-07-20",
        symbol="SPY",
    )

    payload = run_etf_sma_daily_paper_lab(config)

    assert payload["schema_version"] == "1"
    assert payload["assistant_version"] == "assistant_v1"
    assert payload["assistant_packet_version"] == "assistant_v1.1"
    assert payload["packet_type"] == "daily_trading_research_command_center"
    assert payload["run_id"] == "daily_paper_lab_2025-07-20"
    assert payload["symbol"] == "SPY"
    assert payload["active_strategy_name"] == "SPY daily long-only ETF SMA 50/200 trend filter"
    assert payload["posture"] == "bullish_risk_on"
    assert payload["sma_posture_status"] == "risk_on: SMA50 is above SMA200"
    assert payload["preview_decision"] == "offline_preview_bullish_risk_on"
    assert payload["decision"] == "offline_preview_bullish_risk_on"
    assert payload["blocker_status"] == "broker_state_not_observed"
    assert payload["broker_state_mode"] == "broker_state_not_observed"
    assert payload["broker_state_observed"] is False
    assert payload["paper_submit_authorized"] is False
    assert payload["paper_submit_authorization_status"] == "not_authorized"
    assert payload["next_operator_action"] == "review_assistant_brief_no_broker_action"
    assert payload["validation_status"] == "pass"
    assert payload["missing_required_fields"] == []
    assert payload["artifact_presence_status"]["status"] == "pass"
    assert payload["history_ledger_path"].endswith("history_ledger.jsonl")
    assert payload["decision_ledger_version"] == "assistant_v1.5_decision_ledger"
    assert payload["decision_ledger_path"].endswith("decision_ledger.jsonl")
    assert payload["decision_ledger_status"] == "decision_ledger_no_review_input"
    assert payload["decision_ledger_append_status"] == (
        "not_appended_no_review_input"
    )
    assert payload["decision_ledger_entry_count"] == 0
    assert payload["review_input_status"] == "review_input_not_found"
    assert payload["review_input_path"] is None
    assert payload["review_input_sha256"] is None
    assert payload["review_classification"] == "missing"
    assert payload["reviewer_source"] == "reviewer_not_supplied"
    assert payload["review_selected_next_action"] == "await_offline_review_input"
    assert payload["review_decision"] == {
        "classification": "missing",
        "status": "review_input_not_found",
        "selected_next_action": "await_offline_review_input",
    }
    assert payload["paper_observation_readiness_version"] == (
        "assistant_v1.12_paper_observation_readiness"
    )
    assert payload["paper_observation_readiness_path"].endswith(
        "paper_observation_readiness.jsonl"
    )
    _assert_paper_observation_readiness_shape(
        payload["paper_observation_readiness"]
    )
    assert payload["research_board_prioritization_version"] == (
        "assistant_v1.13_research_board_prioritization"
    )
    assert payload["research_board_prioritization_path"].endswith(
        "research_board_prioritization.jsonl"
    )
    _assert_research_board_prioritization_shape(
        payload["research_board_prioritization"]
    )
    assert payload["strategy_comparison_scaffold_path"].endswith(
        "strategy_comparison_scaffold.jsonl"
    )
    _assert_strategy_comparison_scaffold_shape(
        payload["strategy_comparison_scaffold"]
    )
    assert payload["candidate_strategy_evidence_template_path"].endswith(
        "candidate_strategy_evidence_template.jsonl"
    )
    _assert_candidate_strategy_evidence_template_shape(
        payload["candidate_strategy_evidence_template"]
    )
    assert payload["candidate_evidence_requirements_path"].endswith(
        "candidate_evidence_requirements.jsonl"
    )
    _assert_candidate_evidence_requirements_shape(
        payload["candidate_evidence_requirements"]
    )
    assert payload["candidate_evidence_collection_plan_path"].endswith(
        "candidate_evidence_collection_plan.jsonl"
    )
    _assert_candidate_evidence_collection_plan_shape(
        payload["candidate_evidence_collection_plan"]
    )
    assert payload["candidate_evidence_collection_status_path"].endswith(
        "candidate_evidence_collection_status.jsonl"
    )
    _assert_candidate_evidence_collection_status_shape(
        payload["candidate_evidence_collection_status"]
    )
    assert payload["candidate_evidence_gap_summary_path"].endswith(
        "candidate_evidence_gap_summary.jsonl"
    )
    _assert_candidate_evidence_gap_summary_shape(
        payload["candidate_evidence_gap_summary"]
    )
    assert payload["candidate_gap_closure_queue_path"].endswith(
        "candidate_gap_closure_queue.jsonl"
    )
    _assert_candidate_gap_closure_queue_shape(
        payload["candidate_gap_closure_queue"]
    )
    assert payload["candidate_risk_rule_status_path"].endswith(
        "candidate_risk_rule_status.jsonl"
    )
    _assert_candidate_risk_rule_status_shape(
        payload["candidate_risk_rule_status"]
    )
    assert payload["candidate_signal_rule_status_path"].endswith(
        "candidate_signal_rule_status.jsonl"
    )
    _assert_candidate_signal_rule_status_shape(
        payload["candidate_signal_rule_status"]
    )
    assert payload["shared_risk_rule_status_path"].endswith(
        "shared_risk_rule_status.jsonl"
    )
    _assert_shared_risk_rule_status_shape(
        payload["shared_risk_rule_status"]
    )
    _assert_next_action_selector_shape(payload["next_action_selector"])
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["priority"] == "P2"
    assert payload["next_action_selector"]["selected_research_candidate_id"] is None
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["work_order_exports"]["selected_research_candidate_id"] is None
    delta = payload["history_delta"]
    assert delta["previous_packet_found"] is False
    assert delta["previous_as_of_date"] is None
    assert delta["current_as_of_date"] == "2025-07-20"
    assert delta["posture_changed"] is False
    assert delta["current_posture"] == "bullish_risk_on"
    assert delta["preview_decision_changed"] is False
    assert delta["current_preview_decision"] == "offline_preview_bullish_risk_on"
    assert delta["blocker_status_changed"] is False
    assert delta["current_blocker_status"] == "broker_state_not_observed"
    assert delta["validation_status_changed"] is False
    assert delta["current_validation_status"] == "pass"
    assert delta["broker_state_mode_changed"] is False
    assert delta["current_broker_state_mode"] == "broker_state_not_observed"
    assert delta["research_board_changed"] is False
    assert delta["research_board_delta_status"] == "no_previous_packet"
    assert delta["next_operator_action_changed"] is False
    assert (
        delta["delta_summary_text"]
        == "No prior packet was found in this output root history; this is the "
        "first observed packet in the selected history."
    )
    assert payload["artifact_presence_status"]["missing_artifacts"] == []
    assert payload["artifact_presence_status"]["empty_artifacts"] == []
    assert payload["artifact_presence_status"]["artifacts"]["operating_brief"]["exists"] is True
    assert (
        payload["artifact_presence_status"]["artifacts"]["operating_record"]["exists"]
        is True
    )
    assert payload["artifact_presence_status"]["artifacts"]["manifest"]["exists"] is True
    assert (
        payload["artifact_presence_status"]["artifacts"]["review_handoff"]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "research_candidate_queue"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "baseline_health_evaluation"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "baseline_evidence_metrics"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "paper_observation_readiness"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "research_board_prioritization"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "strategy_comparison_scaffold"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "candidate_strategy_evidence_template"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "candidate_evidence_requirements"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "candidate_evidence_collection_plan"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "candidate_evidence_collection_status"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "candidate_evidence_gap_summary"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "candidate_gap_closure_queue"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "candidate_risk_rule_status"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "candidate_signal_rule_status"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"][
            "shared_risk_rule_status"
        ]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"]["gpt_next_action_handoff"][
            "exists"
        ]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"]["codex_work_order"]["exists"]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"]["antigravity_review_order"][
            "exists"
        ]
        is True
    )
    assert (
        payload["artifact_presence_status"]["artifacts"]["claude_critique_order"][
            "exists"
        ]
        is True
    )
    assert payload["artifacts"]["review_handoff"].endswith("review_handoff.md")
    assert payload["artifacts"]["research_candidate_queue"].endswith(
        "research_candidate_queue.jsonl"
    )
    assert payload["artifacts"]["baseline_health_evaluation"].endswith(
        "baseline_health_evaluation.jsonl"
    )
    assert payload["artifacts"]["baseline_evidence_metrics"].endswith(
        "baseline_evidence_metrics.jsonl"
    )
    assert payload["artifacts"]["paper_observation_readiness"].endswith(
        "paper_observation_readiness.jsonl"
    )
    assert payload["artifacts"]["candidate_strategy_evidence_template"].endswith(
        "candidate_strategy_evidence_template.jsonl"
    )
    assert payload["artifacts"]["candidate_evidence_requirements"].endswith(
        "candidate_evidence_requirements.jsonl"
    )
    assert payload["artifacts"]["candidate_evidence_collection_plan"].endswith(
        "candidate_evidence_collection_plan.jsonl"
    )
    assert payload["artifacts"]["candidate_evidence_collection_status"].endswith(
        "candidate_evidence_collection_status.jsonl"
    )
    assert payload["artifacts"]["candidate_evidence_gap_summary"].endswith(
        "candidate_evidence_gap_summary.jsonl"
    )
    assert payload["artifacts"]["candidate_gap_closure_queue"].endswith(
        "candidate_gap_closure_queue.jsonl"
    )
    assert payload["artifacts"]["candidate_risk_rule_status"].endswith(
        "candidate_risk_rule_status.jsonl"
    )
    assert payload["artifacts"]["candidate_signal_rule_status"].endswith(
        "candidate_signal_rule_status.jsonl"
    )
    assert payload["artifacts"]["shared_risk_rule_status"].endswith(
        "shared_risk_rule_status.jsonl"
    )
    assert payload["artifacts"]["gpt_next_action_handoff"].endswith(
        "work_orders/gpt_next_action_handoff.md"
    )
    _assert_quality_gate_pass(payload)
    assert payload["executive_dashboard"]["quality_gate_status"] == "pass"
    assert payload["executive_dashboard"]["review_handoff_path"].endswith(
        "review_handoff.md"
    )
    assert payload["executive_dashboard"]["validation_status"] == "pass"
    assert payload["executive_dashboard"]["missing_required_fields"] == []
    assert payload["executive_dashboard"]["decision_ledger_status"] == (
        "decision_ledger_no_review_input"
    )
    assert payload["executive_dashboard"]["baseline_health_evaluation"] == payload[
        "baseline_health_evaluation"
    ]
    assert payload["executive_dashboard"]["candidate_strategy_evidence_template"] == (
        payload["candidate_strategy_evidence_template"]
    )
    assert payload["executive_dashboard"]["candidate_evidence_requirements"] == (
        payload["candidate_evidence_requirements"]
    )
    assert payload["executive_dashboard"]["candidate_evidence_collection_plan"] == (
        payload["candidate_evidence_collection_plan"]
    )
    assert payload["executive_dashboard"]["candidate_evidence_collection_status"] == (
        payload["candidate_evidence_collection_status"]
    )
    assert payload["executive_dashboard"]["candidate_evidence_gap_summary"] == (
        payload["candidate_evidence_gap_summary"]
    )
    assert payload["executive_dashboard"]["candidate_gap_closure_queue"] == (
        payload["candidate_gap_closure_queue"]
    )
    assert payload["executive_dashboard"]["candidate_risk_rule_status"] == (
        payload["candidate_risk_rule_status"]
    )
    assert payload["executive_dashboard"]["candidate_signal_rule_status"] == (
        payload["candidate_signal_rule_status"]
    )
    assert payload["executive_dashboard"]["shared_risk_rule_status"] == (
        payload["shared_risk_rule_status"]
    )
    assert payload["executive_dashboard"]["baseline_evidence_metrics"] == payload[
        "baseline_evidence_metrics"
    ]
    assert payload["executive_dashboard"]["paper_observation_readiness"] == payload[
        "paper_observation_readiness"
    ]
    assert payload["executive_dashboard"]["review_classification"] == "missing"
    assert payload["executive_action_queue_version"] == "assistant_v1.3_action_queue"
    assert payload["executive_action_summary"] == {
        "daniel_action_required": False,
        "daniel_action_status": (
            "No: Daniel does not need to do anything now. The packet remains "
            "offline_preview_only with broker_state_not_observed."
        ),
        "highest_priority": "P2",
        "queue_length": 2,
    }
    assert payload["daniel_action_required_now"] is False
    assert payload["executive_dashboard"]["executive_action_summary"] == payload[
        "executive_action_summary"
    ]
    assert len(payload["executive_action_queue"]) == 2
    for action in payload["executive_action_queue"]:
        _assert_action_queue_item_shape(action)
    research_action = payload["executive_action_queue"][0]
    assert research_action["action_id"] == "quantify_spy_sma_baseline_confidence"
    assert research_action["priority"] == "P2"
    assert research_action["action_type"] == "research_action"
    assert research_action["requires_daniel"] is False
    assert "research_confidence_not_quantified" in research_action["reason_codes"]
    noop_action = payload["executive_action_queue"][1]
    assert noop_action["action_id"] == "no_daniel_action_required_now"
    assert noop_action["priority"] == "P3"
    assert noop_action["action_type"] == "noop"
    assert noop_action["requires_daniel"] is False
    assert payload["research_lab"]["research_board_version"] == (
        "assistant_v1.3_research_board"
    )
    assert payload["research_board"] == payload["research_lab"]["research_board"]
    assert len(payload["research_board"]) == 2
    for board_item in payload["research_board"]:
        _assert_research_board_item_shape(board_item)
    active_baseline = payload["research_board"][0]
    assert active_baseline["candidate_name"] == (
        "SPY SMA 50/200 daily long-only baseline"
    )
    assert active_baseline["status"] == "active_baseline"
    assert active_baseline["confidence_status"] == "confidence_not_yet_quantified"
    assert "strategy_confidence_not_yet_quantified" in active_baseline[
        "promotion_blockers"
    ]
    assert payload["research_candidate_queue_version"] == (
        "assistant_v1.7_research_candidate_queue"
    )
    assert payload["research_candidate_queue_path"].endswith(
        "research_candidate_queue.jsonl"
    )
    _assert_research_candidate_queue_shape(payload["research_candidate_queue"])
    queue = payload["research_candidate_queue"]
    assert queue["top_candidate_id"] == "offline_review_evidence_gap"
    assert queue["top_candidate_priority"] == "P1"
    assert queue["selected_safe_candidate_id"] == (
        "baseline_evidence_metrics_snapshot_spy_sma_50_200"
    )
    assert queue["selected_safe_candidate_priority"] == "P2"
    candidate_ids = [
        candidate["candidate_id"] for candidate in queue["candidates"]
    ]
    assert candidate_ids == [
        "offline_review_evidence_gap",
        "baseline_evidence_metrics_snapshot_spy_sma_50_200",
        "baseline_health_evaluation_spy_sma_50_200",
        "benchmark_buy_and_hold_comparison_spy",
        "current_baseline_evidence_gap_map",
        "paper_lab_observation_readiness",
        "future_non_sma_strategy_research_slot",
        "strategy_candidate_intake_requirements",
    ]
    assert payload["baseline_health_evaluation_version"] == (
        "assistant_v1.8_baseline_health_evaluation"
    )
    assert payload["baseline_health_evaluation_path"].endswith(
        "baseline_health_evaluation.jsonl"
    )
    _assert_baseline_health_evaluation_shape(payload["baseline_health_evaluation"])
    baseline_health = payload["baseline_health_evaluation"]
    assert baseline_health["as_of_date"] == "2025-07-20"
    assert baseline_health["posture_status"] == "risk_on: SMA50 is above SMA200"
    assert baseline_health["preview_decision"] == "offline_preview_bullish_risk_on"
    assert baseline_health["quality_gate_status"] == "pass"
    assert baseline_health["decision_ledger_status"] == (
        "decision_ledger_no_review_input"
    )
    assert baseline_health["research_candidate_queue_status"] == "generated"
    assert baseline_health["health_status"] == "usable_control_harness"
    assert baseline_health["confidence_status"] == "confidence_not_yet_quantified"
    assert baseline_health["evidence_status"] == "evidence_incomplete"
    assert baseline_health["baseline_evidence_metrics_status"] == "generated"
    assert baseline_health["baseline_evidence_snapshot_status"] == (
        "metrics_partially_available"
    )
    assert baseline_health["baseline_metric_confidence_status"] == (
        "confidence_not_yet_quantified"
    )
    assert baseline_health["baseline_metric_artifact_ingest_status"] == (
        "metric_artifacts_partially_ingested"
    )
    assert set(baseline_health["baseline_metric_artifact_parse_status"]) == {
        "baseline_authorized_adjusted_metrics",
        "offline_backtest_confidence_summary",
        "adjusted_close_evidence",
        "turnover_summary",
        "cost_model_summary",
    }
    assert baseline_health["baseline_metric_artifact_parse_status"] == {
        "baseline_authorized_adjusted_metrics": "missing",
        "offline_backtest_confidence_summary": "missing",
        "adjusted_close_evidence": "missing",
        "turnover_summary": "parsed",
        "cost_model_summary": "parsed",
    }
    assert baseline_health["baseline_evidence_metrics_path"].endswith(
        "baseline_evidence_metrics.jsonl"
    )
    assert "etf-sma-authorized-adjusted-baseline-metrics" in baseline_health[
        "next_safe_metric_command"
    ]
    assert "offline_backtest_confidence_summary" in baseline_health[
        "missing_evidence"
    ]
    assert "baseline_evidence_metrics.jsonl" in baseline_health[
        "required_next_artifacts"
    ]
    assert "buy_and_hold_benchmark_status" in baseline_health[
        "required_next_artifacts"
    ]
    assert baseline_health["requires_daniel"] is False
    assert baseline_health["hard_gate_required"] is False
    assert payload["baseline_evidence_metrics_version"] == (
        "assistant_v1.9_baseline_evidence_metrics"
    )
    assert payload["baseline_evidence_metrics_path"].endswith(
        "baseline_evidence_metrics.jsonl"
    )
    _assert_baseline_evidence_metrics_shape(payload["baseline_evidence_metrics"])
    baseline_metrics = payload["baseline_evidence_metrics"]
    assert baseline_metrics["as_of_date"] == "2025-07-20"
    assert baseline_metrics["evidence_snapshot_status"] == (
        "metrics_partially_available"
    )
    assert baseline_metrics["metric_artifact_ingest_status"] == (
        "metric_artifacts_partially_ingested"
    )
    assert set(baseline_metrics["metric_artifact_hashes"]) == {
        "turnover_summary",
        "cost_model_summary",
    }
    assert baseline_metrics["quantified_metric_summary"] == {}
    assert baseline_metrics["metric_artifact_parse_status"] == {
        "baseline_authorized_adjusted_metrics": "missing",
        "offline_backtest_confidence_summary": "missing",
        "adjusted_close_evidence": "missing",
        "turnover_summary": "parsed",
        "cost_model_summary": "parsed",
    }
    assert baseline_metrics["metric_artifact_record_count"] == {
        "baseline_authorized_adjusted_metrics": 0,
        "offline_backtest_confidence_summary": 0,
        "adjusted_close_evidence": 0,
        "turnover_summary": 1,
        "cost_model_summary": 1,
    }
    assert baseline_metrics["backtest_confidence_summary_status"] == "metrics_missing"
    assert baseline_metrics["benchmark_metric_status"] == "metrics_missing"
    assert baseline_metrics["benchmark_comparison_status"] == "metrics_missing"
    assert baseline_metrics["backtest_metric_status"] == "metrics_missing"
    assert baseline_metrics["drawdown_metric_status"] == "metrics_missing"
    assert baseline_metrics["turnover_metric_status"] == "metrics_available"
    assert baseline_metrics["cost_model_status"] == "metrics_available"
    assert baseline_metrics["turnover_artifact_ingest_status"] == (
        "turnover_artifact_ingested"
    )
    assert baseline_metrics["cost_model_artifact_ingest_status"] == (
        "cost_model_artifact_ingested"
    )
    assert baseline_metrics["turnover_artifact_parse_status"] == "parsed"
    assert baseline_metrics["cost_model_artifact_parse_status"] == "parsed"
    assert baseline_metrics["turnover_artifact_hash"] == (
        baseline_metrics["metric_artifact_hashes"]["turnover_summary"]
    )
    assert baseline_metrics["cost_model_artifact_hash"] == (
        baseline_metrics["metric_artifact_hashes"]["cost_model_summary"]
    )
    assert baseline_metrics["sample_window_status"] == "metrics_available"
    assert baseline_metrics["adjusted_close_basis_status"] == "metrics_missing"
    assert baseline_metrics["remaining_missing_metric_sources"] == baseline_metrics[
        "missing_metric_sources"
    ]
    assert baseline_metrics["remaining_missing_metric_sources"] == [
        "offline_backtest_confidence_summary",
        "buy_and_hold_benchmark_status",
        "drawdown_summary",
        "paper_observation_summary",
        "input_csv.adjusted_close_column",
    ]
    assert "packet.sma.usable_bar_count" in baseline_metrics[
        "available_metric_sources"
    ]
    assert "metric_artifact.turnover_summary" in baseline_metrics[
        "available_metric_sources"
    ]
    assert "metric_artifact.cost_model_summary" in baseline_metrics[
        "available_metric_sources"
    ]
    assert "input_csv.adjusted_close_column" in baseline_metrics[
        "missing_metric_sources"
    ]
    assert baseline_metrics["paper_observation_status"] == (
        "broker_state_not_observed"
    )

    # Labels verification
    for label in (
        "paper_lab_only",
        "signal_evaluation_only",
        "research_only",
        "not_live_authorized",
        "profit_claim=none",
        "offline_only",
        "broker_state_not_observed",
        "paper_submit_not_authorized",
    ):
        assert label in payload["labels"]
        assert label in payload["safety_labels"]

    # Verify artifacts were created
    assert (output_root / "operating_brief.md").exists()
    assert (output_root / "operating_record.jsonl").exists()
    assert (output_root / "manifest.jsonl").exists()
    assert (output_root / "research_candidate_queue.jsonl").exists()
    assert (output_root / "baseline_health_evaluation.jsonl").exists()
    assert (output_root / "baseline_evidence_metrics.jsonl").exists()
    assert (output_root / "paper_observation_readiness.jsonl").exists()
    assert (output_root / "candidate_strategy_evidence_template.jsonl").exists()
    assert (output_root / "candidate_evidence_requirements.jsonl").exists()
    assert (output_root / "candidate_evidence_collection_plan.jsonl").exists()
    assert (output_root / "candidate_evidence_collection_status.jsonl").exists()
    assert (output_root / "candidate_evidence_gap_summary.jsonl").exists()
    assert (output_root / "candidate_gap_closure_queue.jsonl").exists()
    assert (output_root / "candidate_risk_rule_status.jsonl").exists()
    assert (output_root / "candidate_signal_rule_status.jsonl").exists()
    assert (output_root / "shared_risk_rule_status.jsonl").exists()
    assert (output_root / "turnover_summary.jsonl").exists()
    assert (output_root / "cost_model_summary.jsonl").exists()
    assert (output_root / "work_orders" / "gpt_next_action_handoff.md").exists()
    assert (output_root / "work_orders" / "codex_work_order.md").exists()
    assert (output_root / "work_orders" / "antigravity_review_order.md").exists()
    assert (output_root / "work_orders" / "claude_critique_order.md").exists()
    assert (output_root / "review_handoff.md").exists()
    assert (output_root / "history_ledger.jsonl").exists()
    assert not (output_root / "decision_ledger.jsonl").exists()

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    assert "## Executive summary" in brief
    assert "* **Recommendation**:" in brief
    assert "* **Evidence**:" in brief
    assert "* **Risks / blockers**:" in brief
    assert "## Executive Action Queue" in brief
    assert "quantify_spy_sma_baseline_confidence" in brief
    assert "no_daniel_action_required_now" in brief
    assert "**Daniel action required now**: false" in brief
    assert "## Trading desk brief" in brief
    assert "## Research Board" in brief
    assert "## Research Candidate Queue" in brief
    assert "research_candidate_queue.jsonl" in brief
    assert "## Baseline Health Evaluation" in brief
    assert "baseline_health_evaluation.jsonl" in brief
    assert "## Baseline Evidence Metrics" in brief
    assert "baseline_evidence_metrics.jsonl" in brief
    assert "## Paper Observation Readiness" in brief
    assert "paper_observation_readiness.jsonl" in brief
    assert "## Candidate Strategy Evidence Template" in brief
    assert "candidate_strategy_evidence_template.jsonl" in brief
    assert "offline_strategy_evidence_template_only" in brief
    assert "materialize_candidate_evidence_requirements" in brief
    assert "Candidate Evidence Requirements" in brief
    assert "candidate_evidence_requirements.jsonl" in brief
    assert "offline_candidate_evidence_requirements_only" in brief
    assert "build_candidate_evidence_collection_plan" in brief
    assert "## Candidate Evidence Collection Plan" in brief
    assert "candidate_evidence_collection_plan.jsonl" in brief
    assert "offline_candidate_evidence_collection_plan_only" in brief
    assert "build_candidate_evidence_collection_status" in brief
    assert "## Candidate Evidence Collection Status" in brief
    assert "candidate_evidence_collection_status.jsonl" in brief
    assert "offline_candidate_evidence_collection_status_only" in brief
    assert "build_candidate_evidence_gap_summary" in brief
    assert "## Candidate Evidence Gap Summary" in brief
    assert "candidate_evidence_gap_summary.jsonl" in brief
    assert "offline_candidate_evidence_gap_summary_only" in brief
    assert "build_candidate_gap_closure_queue" in brief
    assert "## Candidate Gap Closure Queue" in brief
    assert "candidate_gap_closure_queue.jsonl" in brief
    assert "offline_candidate_gap_closure_queue_only" in brief
    assert "execute_candidate_gap_closure_queue_item_001" in brief
    assert "## Candidate Risk Rule Status" in brief
    assert "candidate_risk_rule_status.jsonl" in brief
    assert "offline_candidate_risk_rule_status_only" in brief
    assert "execute_candidate_gap_closure_queue_item_003" in brief
    assert "volatility_or_regime_filter_candidate" in brief
    assert "execute_candidate_gap_closure_queue_item_004" in brief
    assert "required evidence is collected, statused" in brief
    assert "Candidate implementation requires an offline evidence template" in brief
    assert "hard_gate_prepared_not_authorized" in brief
    assert "Daniel approves read-only paper observation" in brief
    assert "metrics_partially_available" in brief
    assert "metric_artifacts_partially_ingested" in brief
    assert "Metric artifact ingest status" in brief
    assert "turnover_artifact_ingested" in brief
    assert "cost_model_artifact_ingested" in brief
    assert "turnover_summary.jsonl" in brief
    assert "cost_model_summary.jsonl" in brief
    assert "etf-sma-authorized-adjusted-baseline-metrics" in brief
    assert "usable_control_harness" in brief
    assert (
        "python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py "
        "-k baseline_health_evaluation"
    ) in brief
    assert "offline_review_evidence_gap" in brief
    assert "baseline_evidence_metrics_snapshot_spy_sma_50_200" in brief
    assert "baseline_health_evaluation_spy_sma_50_200" in brief
    assert "## Executive dashboard" in brief
    assert "paper_submit_authorized=false" in brief
    assert "broker_state_not_observed" in brief
    assert "SPY SMA 50/200 daily long-only baseline" in brief
    assert "active_baseline" in brief
    assert "future_candidate_strategy_slot" in brief
    assert "blocked" in brief
    assert "**Assistant packet version**: assistant_v1.1" in brief
    assert "**Validation status**: pass" in brief
    assert "**Quality Gate**: `pass`" in brief
    assert "review_handoff.md" in brief
    assert "**Decision Ledger**: `decision_ledger_no_review_input`" in brief
    assert "decision_ledger.jsonl" in brief
    assert "review_input_not_found" in brief
    assert "await_offline_review_input" in brief
    assert "## Next Action Selector" in brief
    assert "execute_candidate_gap_closure_queue_item_004" in brief
    assert "execute_candidate_gap_closure_queue_item_005" in brief
    assert "execute_candidate_gap_closure_queue_item_006" in brief
    assert "execute_candidate_gap_closure_queue_item_007" in brief
    assert "execute_candidate_gap_closure_queue_item_008" in brief
    assert "## Candidate Signal Rule Status" in brief
    assert "candidate_signal_rule_status.jsonl" in brief
    assert "## Shared Risk Rule Status" in brief
    assert "shared_risk_rule_status.jsonl" in brief
    assert "Work order exports" in brief
    assert "work_orders/codex_work_order.md" in brief
    assert "**Missing required fields**: []" in brief
    assert "**Artifact presence status**: pass" in brief
    assert "**Previous packet found**: false" in brief
    assert "history_ledger.jsonl" in brief
    assert delta["delta_summary_text"] in brief

    record_lines = (output_root / "operating_record.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(record_lines) == 1
    record = json.loads(record_lines[0])
    assert record["assistant_version"] == "assistant_v1"
    assert record["assistant_packet_version"] == "assistant_v1.1"
    assert record["input_data_path"].endswith("spy_daily_bars_200_bullish.csv")
    assert record["as_of_date"] == "2025-07-20"
    assert record["active_strategy_name"] == payload["active_strategy_name"]
    assert record["preview_decision"] == "offline_preview_bullish_risk_on"
    assert record["broker_state_mode"] == "broker_state_not_observed"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_authorization_status"] == "not_authorized"
    assert record["next_operator_action"] == "review_assistant_brief_no_broker_action"
    assert "paper_lab_only" in record["safety_labels"]
    assert record["validation_status"] == "pass"
    assert record["missing_required_fields"] == []
    assert record["artifact_presence_status"]["status"] == "pass"
    _assert_quality_gate_pass(record)
    assert record["decision_ledger_status"] == "decision_ledger_no_review_input"
    assert record["decision_ledger_append_status"] == "not_appended_no_review_input"
    assert record["decision_ledger_entry_count"] == 0
    assert record["review_input_status"] == "review_input_not_found"
    assert record["review_classification"] == "missing"
    assert record["review_selected_next_action"] == "await_offline_review_input"
    assert record["candidate_strategy_evidence_template_path"].endswith(
        "candidate_strategy_evidence_template.jsonl"
    )
    assert record["candidate_strategy_evidence_template"] == payload[
        "candidate_strategy_evidence_template"
    ]
    assert record["candidate_evidence_requirements_path"].endswith(
        "candidate_evidence_requirements.jsonl"
    )
    assert record["candidate_evidence_requirements"] == payload[
        "candidate_evidence_requirements"
    ]
    assert record["candidate_evidence_collection_plan_path"].endswith(
        "candidate_evidence_collection_plan.jsonl"
    )
    assert record["candidate_evidence_collection_plan"] == payload[
        "candidate_evidence_collection_plan"
    ]
    assert record["candidate_evidence_collection_status_path"].endswith(
        "candidate_evidence_collection_status.jsonl"
    )
    assert record["candidate_evidence_collection_status"] == payload[
        "candidate_evidence_collection_status"
    ]
    assert record["candidate_evidence_gap_summary_path"].endswith(
        "candidate_evidence_gap_summary.jsonl"
    )
    assert record["candidate_evidence_gap_summary"] == payload[
        "candidate_evidence_gap_summary"
    ]
    assert record["candidate_gap_closure_queue_path"].endswith(
        "candidate_gap_closure_queue.jsonl"
    )
    assert record["candidate_gap_closure_queue"] == payload[
        "candidate_gap_closure_queue"
    ]
    assert record["candidate_risk_rule_status_path"].endswith(
        "candidate_risk_rule_status.jsonl"
    )
    assert record["candidate_risk_rule_status"] == payload[
        "candidate_risk_rule_status"
    ]
    assert record["candidate_signal_rule_status_path"].endswith(
        "candidate_signal_rule_status.jsonl"
    )
    assert record["candidate_signal_rule_status"] == payload[
        "candidate_signal_rule_status"
    ]
    assert record["shared_risk_rule_status_path"].endswith(
        "shared_risk_rule_status.jsonl"
    )
    assert record["shared_risk_rule_status"] == payload[
        "shared_risk_rule_status"
    ]
    assert record["next_action_selector"] == payload["next_action_selector"]
    assert record["work_order_exports"] == payload["work_order_exports"]
    assert record["research_candidate_queue_version"] == (
        "assistant_v1.7_research_candidate_queue"
    )
    assert record["research_candidate_queue_path"].endswith(
        "research_candidate_queue.jsonl"
    )
    assert record["research_candidate_queue"] == payload["research_candidate_queue"]
    assert record["baseline_health_evaluation_version"] == (
        "assistant_v1.8_baseline_health_evaluation"
    )
    assert record["baseline_health_evaluation_path"].endswith(
        "baseline_health_evaluation.jsonl"
    )
    assert record["baseline_health_evaluation"] == payload[
        "baseline_health_evaluation"
    ]
    assert record["baseline_evidence_metrics_version"] == (
        "assistant_v1.9_baseline_evidence_metrics"
    )
    assert record["baseline_evidence_metrics_path"].endswith(
        "baseline_evidence_metrics.jsonl"
    )
    assert record["baseline_evidence_metrics"] == payload["baseline_evidence_metrics"]
    assert record["history_delta"] == delta
    assert record["history_ledger_path"].endswith("history_ledger.jsonl")
    assert record["executive_action_queue"] == payload["executive_action_queue"]
    assert record["executive_action_summary"] == payload["executive_action_summary"]
    assert record["research_board"] == payload["research_board"]
    candidate = record["research_lab"]["candidate_strategy_board"][0]
    assert candidate["candidate_name"] == "SPY SMA 50/200 daily long-only baseline"
    assert candidate["status"] == "active_baseline"
    assert "hypothesis" in candidate
    assert "evidence_status" in candidate
    assert "confidence_status" in candidate
    assert "missing_evidence" in candidate
    assert "next_research_action" in candidate
    assert "promotion_blockers" in candidate
    assert "safety_scope" in candidate
    assert "notes" in candidate

    # Verify manifest content
    manifest_lines = (output_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    manifest = json.loads(manifest_lines[0])
    assert manifest["schema_version"] == "1"
    assert manifest["assistant_version"] == "assistant_v1"
    assert manifest["assistant_packet_version"] == "assistant_v1.1"
    assert manifest["manifest_type"] == "daily_trading_research_command_center_index"
    assert manifest["run_id"] == "daily_paper_lab_2025-07-20"
    assert manifest["paper_submit_authorized"] is False
    assert manifest["broker_state_mode"] == "broker_state_not_observed"
    assert manifest["next_operator_action"] == "review_assistant_brief_no_broker_action"
    assert manifest["validation_status"] == "pass"
    assert manifest["missing_required_fields"] == []
    assert manifest["artifact_presence_status"]["status"] == "pass"
    _assert_quality_gate_pass(manifest)
    assert manifest["decision_ledger_status"] == "decision_ledger_no_review_input"
    assert manifest["decision_ledger_append_status"] == (
        "not_appended_no_review_input"
    )
    assert manifest["decision_ledger_entry_count"] == 0
    assert manifest["review_input_status"] == "review_input_not_found"
    assert manifest["review_classification"] == "missing"
    assert manifest["review_selected_next_action"] == "await_offline_review_input"
    assert manifest["next_action_selector"] == payload["next_action_selector"]
    assert manifest["work_order_exports"] == payload["work_order_exports"]
    assert manifest["research_candidate_queue_version"] == (
        "assistant_v1.7_research_candidate_queue"
    )
    assert manifest["research_candidate_queue_path"].endswith(
        "research_candidate_queue.jsonl"
    )
    assert manifest["research_candidate_queue"] == payload["research_candidate_queue"]
    assert manifest["baseline_health_evaluation_version"] == (
        "assistant_v1.8_baseline_health_evaluation"
    )
    assert manifest["baseline_health_evaluation_path"].endswith(
        "baseline_health_evaluation.jsonl"
    )
    assert manifest["baseline_health_evaluation"] == payload[
        "baseline_health_evaluation"
    ]
    assert manifest["baseline_evidence_metrics_version"] == (
        "assistant_v1.9_baseline_evidence_metrics"
    )
    assert manifest["baseline_evidence_metrics_path"].endswith(
        "baseline_evidence_metrics.jsonl"
    )
    assert manifest["baseline_evidence_metrics"] == payload[
        "baseline_evidence_metrics"
    ]
    assert manifest["paper_observation_readiness_version"] == (
        "assistant_v1.12_paper_observation_readiness"
    )
    assert manifest["paper_observation_readiness_path"].endswith(
        "paper_observation_readiness.jsonl"
    )
    assert manifest["paper_observation_readiness"] == payload[
        "paper_observation_readiness"
    ]
    assert manifest["research_board_prioritization_version"] == (
        "assistant_v1.13_research_board_prioritization"
    )
    assert manifest["research_board_prioritization_path"].endswith(
        "research_board_prioritization.jsonl"
    )
    assert manifest["research_board_prioritization"] == payload[
        "research_board_prioritization"
    ]
    assert manifest["candidate_strategy_evidence_template_path"].endswith(
        "candidate_strategy_evidence_template.jsonl"
    )
    assert manifest["candidate_strategy_evidence_template"] == payload[
        "candidate_strategy_evidence_template"
    ]
    assert manifest["candidate_evidence_requirements_path"].endswith(
        "candidate_evidence_requirements.jsonl"
    )
    assert manifest["candidate_evidence_requirements"] == payload[
        "candidate_evidence_requirements"
    ]
    assert manifest["candidate_evidence_collection_plan_path"].endswith(
        "candidate_evidence_collection_plan.jsonl"
    )
    assert manifest["candidate_evidence_collection_plan"] == payload[
        "candidate_evidence_collection_plan"
    ]
    assert manifest["candidate_evidence_collection_status_path"].endswith(
        "candidate_evidence_collection_status.jsonl"
    )
    assert manifest["candidate_evidence_collection_status"] == payload[
        "candidate_evidence_collection_status"
    ]
    assert manifest["candidate_evidence_gap_summary_path"].endswith(
        "candidate_evidence_gap_summary.jsonl"
    )
    assert manifest["candidate_evidence_gap_summary"] == payload[
        "candidate_evidence_gap_summary"
    ]
    assert manifest["candidate_gap_closure_queue_path"].endswith(
        "candidate_gap_closure_queue.jsonl"
    )
    assert manifest["candidate_gap_closure_queue"] == payload[
        "candidate_gap_closure_queue"
    ]
    assert manifest["candidate_risk_rule_status_path"].endswith(
        "candidate_risk_rule_status.jsonl"
    )
    assert manifest["candidate_risk_rule_status"] == payload[
        "candidate_risk_rule_status"
    ]
    assert manifest["candidate_signal_rule_status_path"].endswith(
        "candidate_signal_rule_status.jsonl"
    )
    assert manifest["candidate_signal_rule_status"] == payload[
        "candidate_signal_rule_status"
    ]
    assert manifest["shared_risk_rule_status_path"].endswith(
        "shared_risk_rule_status.jsonl"
    )
    assert manifest["shared_risk_rule_status"] == payload[
        "shared_risk_rule_status"
    ]
    assert manifest["history_delta"] == delta
    assert manifest["executive_action_queue"] == payload["executive_action_queue"]
    assert manifest["executive_action_summary"] == payload["executive_action_summary"]
    assert manifest["research_board"] == payload["research_board"]
    assert manifest["previous_packet_found"] is False
    assert manifest["delta_summary_text"] == delta["delta_summary_text"]
    assert "assistant_brief" in manifest["indexed_artifacts"]
    assert "operating_record" in manifest["indexed_artifacts"]
    assert "review_handoff" in manifest["indexed_artifacts"]
    assert "history_ledger" in manifest["indexed_artifacts"]
    assert "research_candidate_queue" in manifest["indexed_artifacts"]
    assert "baseline_health_evaluation" in manifest["indexed_artifacts"]
    assert "baseline_evidence_metrics" in manifest["indexed_artifacts"]
    assert "paper_observation_readiness" in manifest["indexed_artifacts"]
    assert "research_board_prioritization" in manifest["indexed_artifacts"]
    assert "strategy_comparison_scaffold" in manifest["indexed_artifacts"]
    assert "candidate_strategy_evidence_template" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_strategy_evidence_template"][
        "path"
    ].endswith("candidate_strategy_evidence_template.jsonl")
    assert "candidate_evidence_requirements" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_evidence_requirements"][
        "path"
    ].endswith("candidate_evidence_requirements.jsonl")
    assert "candidate_evidence_collection_plan" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_evidence_collection_plan"][
        "path"
    ].endswith("candidate_evidence_collection_plan.jsonl")
    assert "candidate_evidence_collection_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_evidence_collection_status"][
        "path"
    ].endswith("candidate_evidence_collection_status.jsonl")
    assert "candidate_evidence_gap_summary" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_evidence_gap_summary"][
        "path"
    ].endswith("candidate_evidence_gap_summary.jsonl")
    assert "candidate_gap_closure_queue" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_gap_closure_queue"][
        "path"
    ].endswith("candidate_gap_closure_queue.jsonl")
    assert "candidate_risk_rule_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_risk_rule_status"][
        "path"
    ].endswith("candidate_risk_rule_status.jsonl")
    assert "candidate_signal_rule_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_signal_rule_status"][
        "path"
    ].endswith("candidate_signal_rule_status.jsonl")
    assert "shared_risk_rule_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["shared_risk_rule_status"][
        "path"
    ].endswith("shared_risk_rule_status.jsonl")
    assert "turnover_summary" in manifest["indexed_artifacts"]
    assert "cost_model_summary" in manifest["indexed_artifacts"]
    assert "gpt_next_action_handoff" in manifest["indexed_artifacts"]
    assert "codex_work_order" in manifest["indexed_artifacts"]
    assert "antigravity_review_order" in manifest["indexed_artifacts"]
    assert "claude_critique_order" in manifest["indexed_artifacts"]
    assert "decision_ledger" not in manifest["indexed_artifacts"]
    assert "manifest" not in manifest["indexed_artifacts"]

    work_order_texts = [
        (output_root / "work_orders" / "gpt_next_action_handoff.md").read_text(
            encoding="utf-8"
        ),
        (output_root / "work_orders" / "codex_work_order.md").read_text(
            encoding="utf-8"
        ),
        (output_root / "work_orders" / "antigravity_review_order.md").read_text(
            encoding="utf-8"
        ),
        (output_root / "work_orders" / "claude_critique_order.md").read_text(
            encoding="utf-8"
        ),
    ]
    for work_order in work_order_texts:
        assert (
            "Assistant v1.40 - Offline Data Refresh Intake Dry-Run UX"
            in work_order
        )
        assert "execute_candidate_gap_closure_queue_item_001" in work_order
        assert "execute_candidate_gap_closure_queue_item_002" in work_order
        assert "execute_candidate_gap_closure_queue_item_003" in work_order
        assert "execute_candidate_gap_closure_queue_item_004" in work_order
        assert "execute_candidate_gap_closure_queue_item_005" in work_order
        assert "execute_candidate_gap_closure_queue_item_006" in work_order
        assert "execute_candidate_gap_closure_queue_item_007" in work_order
        assert "execute_candidate_gap_closure_queue_item_008" in work_order
        assert "execute_candidate_gap_closure_queue_item_009" in work_order
        assert "execute_candidate_gap_closure_queue_item_010" in work_order
        assert "execute_candidate_gap_closure_queue_item_011" in work_order
        assert "execute_candidate_gap_closure_queue_item_012" in work_order
        assert "research_candidate_queue.jsonl" in work_order
        assert "baseline_health_evaluation.jsonl" in work_order
        assert "baseline_evidence_metrics.jsonl" in work_order
        assert "data_refresh_dry_run.json" in work_order
        assert "paper_observation_readiness.jsonl" in work_order
        assert "research_board_prioritization.jsonl" in work_order
        assert "strategy_comparison_scaffold.jsonl" in work_order
        assert "candidate_strategy_evidence_template.jsonl" in work_order
        assert "candidate_evidence_requirements.jsonl" in work_order
        assert "candidate_evidence_collection_plan.jsonl" in work_order
        assert "candidate_evidence_collection_status.jsonl" in work_order
        assert "candidate_evidence_gap_summary.jsonl" in work_order
        assert "candidate_gap_closure_queue.jsonl" in work_order
        assert "candidate_risk_rule_status.jsonl" in work_order
        assert "candidate_backtest_result_packet.jsonl" in work_order
        assert "candidate_signal_rule_status.jsonl" in work_order
        assert "shared_risk_rule_status.jsonl" in work_order
        assert "shared_signal_rule_status.jsonl" in work_order
        assert "## Paper observation readiness" in work_order
        assert "## Research board prioritization" in work_order
        assert "## Strategy comparison scaffold" in work_order
        assert "## Candidate strategy evidence template" in work_order
        assert "## Candidate Evidence Requirements" in work_order
        assert "## Candidate Evidence Collection Plan" in work_order
        assert "## Candidate Evidence Collection Status" in work_order
        assert "## Candidate Evidence Gap Summary" in work_order
        assert "## Candidate Gap Closure Queue" in work_order
        assert "## Candidate Risk Rule Status" in work_order
        assert "## Shared Signal Rule Status" in work_order
        assert "offline_strategy_evidence_template_only" in work_order
        assert "materialize_candidate_evidence_requirements" in work_order
        assert "offline_candidate_evidence_requirements_only" in work_order
        assert "build_candidate_evidence_collection_plan" in work_order
        assert "offline_candidate_evidence_collection_plan_only" in work_order
        assert "build_candidate_evidence_collection_status" in work_order
        assert "offline_candidate_evidence_collection_status_only" in work_order
        assert "build_candidate_evidence_gap_summary" in work_order
        assert "offline_candidate_evidence_gap_summary_only" in work_order
        assert "build_candidate_gap_closure_queue" in work_order
        assert "offline_candidate_gap_closure_queue_only" in work_order
        assert "offline_candidate_risk_rule_status_only" in work_order
        assert "hard_gate_prepared_not_authorized" in work_order
        assert "turnover_summary.jsonl" in work_order
        assert "cost_model_summary.jsonl" in work_order
        assert "paper_observation_summary" in work_order
        assert "## Prerequisite artifact chain" in work_order
        assert "## Baseline health evaluation" in work_order
        assert "## Baseline evidence metrics" in work_order
        assert "next_safe_metric_command" in work_order
        assert "Metric artifact ingest status" in work_order
        assert "etf-sma-authorized-adjusted-baseline-metrics" in work_order
        assert "usable_control_harness" in work_order
        assert (
            "python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py "
            "-k baseline_health_evaluation"
        ) in work_order
        assert "offline_review_evidence_gap" in work_order
        assert "Do not commit unless GPT/Daniel explicitly asks after review." in work_order
        assert "Do not perform broker reads." in work_order
        assert "python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py" in work_order

    history_lines = (output_root / "history_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(history_lines) == 1
    history_entry = json.loads(history_lines[0])
    assert history_entry["history_entry_version"] == "assistant_v1.2_history_entry"
    assert history_entry["sequence_number"] == 1
    assert history_entry["as_of_date"] == "2025-07-20"
    assert history_entry["posture"] == "bullish_risk_on"
    assert history_entry["preview_decision"] == "offline_preview_bullish_risk_on"
    assert history_entry["blocker_status"] == "broker_state_not_observed"
    assert history_entry["validation_status"] == "pass"
    assert history_entry["broker_state_mode"] == "broker_state_not_observed"
    assert history_entry["research_board_status"] == "active_baseline,blocked"
    assert len(history_entry["packet_summary_sha256"]) == 64

    validation = validate_etf_sma_daily_paper_lab_packet(output_root)
    assert validation["validation_status"] == "pass"
    assert validation["missing_required_fields"] == []
    assert validation["artifact_presence_status"]["status"] == "pass"

    queue_lines = (output_root / "research_candidate_queue.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(queue_lines) == queue["candidate_count"]
    queue_records = [json.loads(line) for line in queue_lines]
    assert queue_records == queue["candidates"]

    baseline_health_lines = (
        output_root / "baseline_health_evaluation.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert len(baseline_health_lines) == 1
    assert json.loads(baseline_health_lines[0]) == payload[
        "baseline_health_evaluation"
    ]

    baseline_metrics_lines = (
        output_root / "baseline_evidence_metrics.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert len(baseline_metrics_lines) == 1
    assert json.loads(baseline_metrics_lines[0]) == payload[
        "baseline_evidence_metrics"
    ]


def test_etf_sma_daily_paper_lab_ingests_local_metric_artifacts(
    tmp_path: Path,
) -> None:
    """Local baseline metric JSONL artifacts upgrade the offline confidence snapshot."""
    output_root = tmp_path / "paper_lab_out"
    artifacts = {
        "offline_backtest_confidence_summary.jsonl": {
            "comparison_summary_status": (
                "authorized_preferred_baseline_summary_evaluated"
            ),
            "profit_claim": "none",
        },
        "adjusted_close_evidence.jsonl": {
            "promotion_status": "ready_to_promote_adjusted_matched_window_basis",
            "adjusted_basis_verified": True,
            "profit_claim": "none",
        },
        "baseline_authorized_adjusted_metrics.jsonl": {
            "metrics_materialization_status": (
                "authorized_adjusted_baseline_metrics_materialized"
            ),
            "metrics_materialized": True,
            "metrics_source_basis": "adjusted_close_price_return",
            "active_preferred_baseline": "adjusted_close_matched_window",
            "active_preferred_basis": "adjusted_close_price_return",
            "comparison_basis": "matched_window",
            "matched_total_interval_count": 1055,
            "matched_evaluated_return_count": 1055,
            "full_adjusted_history_evaluated_return_count": 8195,
            "known_basis_delta_slices": ["recovery_2023"],
            "known_basis_delta_slice_count": 1,
            "return_conclusions_unchanged": True,
            "basis_delta_review_required": True,
            "return_conclusion_changes": [],
            "drawdown_conclusion_changes": ["recovery_2023"],
            "full_window_return_deltas": {
                "benchmark_total_return": {
                    "raw": "0.1",
                    "adjusted": "0.2",
                    "delta": "0.1",
                }
            },
            "matched_slice_comparisons": [
                {
                    "slice_name": "full_evaluated_window",
                    "adjusted_benchmark_total_return": "0.2",
                    "raw_benchmark_total_return": "0.1",
                    "adjusted_strategy_max_drawdown": "0.1",
                    "raw_strategy_max_drawdown": "0.2",
                }
            ],
            "metrics_materialized_fields": ["matched_evaluated_return_count"],
            "profit_claim": "none",
        },
    }
    output_root.mkdir(parents=True)
    for filename, record in artifacts.items():
        (output_root / filename).write_text(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    _assert_quality_gate_pass(payload)
    _assert_baseline_evidence_metrics_shape(payload["baseline_evidence_metrics"])
    metrics = payload["baseline_evidence_metrics"]
    assert metrics["metric_artifact_ingest_status"] == "metric_artifacts_ingested"
    assert metrics["metric_artifact_parse_status"] == {
        "baseline_authorized_adjusted_metrics": "parsed",
        "offline_backtest_confidence_summary": "parsed",
        "adjusted_close_evidence": "parsed",
        "turnover_summary": "parsed",
        "cost_model_summary": "parsed",
    }
    assert metrics["metric_artifact_record_count"] == {
        "baseline_authorized_adjusted_metrics": 1,
        "offline_backtest_confidence_summary": 1,
        "adjusted_close_evidence": 1,
        "turnover_summary": 1,
        "cost_model_summary": 1,
    }
    expected_hashes = {
        "baseline_authorized_adjusted_metrics": hashlib.sha256(
            (output_root / "baseline_authorized_adjusted_metrics.jsonl").read_bytes()
        ).hexdigest(),
        "offline_backtest_confidence_summary": hashlib.sha256(
            (output_root / "offline_backtest_confidence_summary.jsonl").read_bytes()
        ).hexdigest(),
        "adjusted_close_evidence": hashlib.sha256(
            (output_root / "adjusted_close_evidence.jsonl").read_bytes()
        ).hexdigest(),
        "turnover_summary": hashlib.sha256(
            (output_root / "turnover_summary.jsonl").read_bytes()
        ).hexdigest(),
        "cost_model_summary": hashlib.sha256(
            (output_root / "cost_model_summary.jsonl").read_bytes()
        ).hexdigest(),
    }
    assert metrics["metric_artifact_hashes"] == expected_hashes
    expected_path_suffixes = {
        "baseline_authorized_adjusted_metrics": "baseline_authorized_adjusted_metrics.jsonl",
        "offline_backtest_confidence_summary": "offline_backtest_confidence_summary.jsonl",
        "adjusted_close_evidence": "adjusted_close_evidence.jsonl",
        "turnover_summary": "turnover_summary.jsonl",
        "cost_model_summary": "cost_model_summary.jsonl",
    }
    assert set(metrics["metric_artifact_paths"]) == set(expected_path_suffixes)
    for artifact_id, filename in expected_path_suffixes.items():
        assert str(metrics["metric_artifact_paths"][artifact_id]).endswith(filename)
    assert metrics["metric_confidence_status"] == "offline_confidence_quantified"
    assert metrics["evidence_snapshot_status"] == "metrics_partially_available"
    assert metrics["backtest_confidence_summary_status"] == "metrics_available"
    assert metrics["benchmark_metric_status"] == "metrics_available"
    assert metrics["benchmark_comparison_status"] == "metrics_available"
    assert metrics["backtest_metric_status"] == "metrics_available"
    assert metrics["drawdown_metric_status"] == "metrics_available"
    assert metrics["turnover_metric_status"] == "metrics_available"
    assert metrics["cost_model_status"] == "metrics_available"
    assert metrics["turnover_artifact_ingest_status"] == (
        "turnover_artifact_ingested"
    )
    assert metrics["cost_model_artifact_ingest_status"] == (
        "cost_model_artifact_ingested"
    )
    assert str(metrics["turnover_artifact_path"]).endswith("turnover_summary.jsonl")
    assert str(metrics["cost_model_artifact_path"]).endswith("cost_model_summary.jsonl")
    assert metrics["turnover_artifact_hash"] == expected_hashes["turnover_summary"]
    assert metrics["cost_model_artifact_hash"] == expected_hashes[
        "cost_model_summary"
    ]
    assert metrics["turnover_artifact_parse_status"] == "parsed"
    assert metrics["cost_model_artifact_parse_status"] == "parsed"
    assert metrics["sample_window_status"] == "metrics_available"
    assert metrics["adjusted_close_basis_status"] == "metrics_available"
    assert metrics["remaining_missing_metric_sources"] == ["paper_observation_summary"]
    assert "metric_artifact.baseline_authorized_adjusted_metrics" in metrics[
        "available_metric_sources"
    ]
    assert "metric_artifact.offline_backtest_confidence_summary" in metrics[
        "available_metric_sources"
    ]
    assert "metric_artifact.adjusted_close_evidence" in metrics[
        "available_metric_sources"
    ]
    assert "metric_artifact.turnover_summary" in metrics["available_metric_sources"]
    assert "metric_artifact.cost_model_summary" in metrics["available_metric_sources"]
    assert "turnover_summary.signal_change_count" in metrics[
        "available_metric_sources"
    ]
    assert "cost_model_summary.estimated_cost_per_trade_status" in metrics[
        "available_metric_sources"
    ]
    summary = metrics["quantified_metric_summary"]
    assert summary["metrics_materialization_status"] == (
        "authorized_adjusted_baseline_metrics_materialized"
    )
    assert summary["matched_evaluated_return_count"] == 1055
    assert summary["matched_slice_count"] == 1
    assert summary["matched_slice_names"] == ["full_evaluated_window"]
    assert summary["summary_source"] == "baseline_authorized_adjusted_metrics.jsonl"
    assert "profit" not in json.dumps(summary, sort_keys=True).lower()
    assert metrics["profit_claim"] == "none"
    assert metrics["paper_submit_readiness_status"] == "not_ready_for_paper_submit"
    assert metrics["broker_state_mode"] == "broker_state_not_observed"
    assert metrics["paper_observation_status"] == "broker_state_not_observed"

    health = payload["baseline_health_evaluation"]
    assert health["baseline_metric_confidence_status"] == (
        "offline_confidence_quantified"
    )
    assert health["baseline_metric_artifact_ingest_status"] == (
        "metric_artifacts_ingested"
    )
    assert health["baseline_metric_artifact_parse_status"] == metrics[
        "metric_artifact_parse_status"
    ]
    assert health["baseline_remaining_missing_metric_sources"] == metrics[
        "remaining_missing_metric_sources"
    ]
    assert payload["next_action_selector"]["source_state"][
        "baseline_metric_artifact_ingest_status"
    ] == "metric_artifacts_ingested"
    assert payload["work_order_exports"]["metric_artifact_ingest_status"] == (
        "metric_artifacts_ingested"
    )
    assert payload["work_order_exports"]["metric_artifact_hashes"] == expected_hashes
    assert payload["work_order_exports"]["turnover_artifact_ingest_status"] == (
        "turnover_artifact_ingested"
    )
    assert payload["work_order_exports"]["cost_model_artifact_ingest_status"] == (
        "cost_model_artifact_ingested"
    )
    assert payload["work_order_exports"]["turnover_metric_status"] == (
        "metrics_available"
    )
    assert payload["work_order_exports"]["cost_model_status"] == "metrics_available"
    assert payload["work_order_exports"]["remaining_missing_metric_sources"] == [
        "paper_observation_summary"
    ]

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    for artifact_id, digest in expected_hashes.items():
        assert artifact_id in manifest["indexed_artifacts"]
        assert manifest["indexed_artifacts"][artifact_id]["sha256"] == digest

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    assert "offline_confidence_quantified" in brief
    assert "metric_artifacts_ingested" in brief
    assert "turnover_artifact_ingested" in brief
    assert "cost_model_artifact_ingested" in brief


def test_etf_sma_daily_paper_lab_second_run_delta_compares_prior_packet(
    tmp_path: Path,
) -> None:
    """Second run against one output root reports the prior packet delta."""
    output_root = tmp_path / "paper_lab_out"

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )
    second_payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bearish.csv",
            as_of_date="2025-07-21",
            symbol="SPY",
        )
    )

    delta = second_payload["history_delta"]
    assert delta["previous_packet_found"] is True
    assert delta["previous_as_of_date"] == "2025-07-20"
    assert delta["current_as_of_date"] == "2025-07-21"
    assert delta["posture_changed"] is True
    assert delta["previous_posture"] == "bullish_risk_on"
    assert delta["current_posture"] == "defensive_risk_off"
    assert delta["preview_decision_changed"] is True
    assert delta["previous_preview_decision"] == "offline_preview_bullish_risk_on"
    assert delta["current_preview_decision"] == "offline_preview_defensive_risk_off"
    assert delta["blocker_status_changed"] is False
    assert delta["validation_status_changed"] is False
    assert delta["broker_state_mode_changed"] is False
    assert delta["research_board_changed"] is False
    assert delta["research_board_delta_status"] == "unchanged"
    assert delta["next_operator_action_changed"] is False
    assert delta["delta_summary_text"] == (
        "Prior packet found; as-of date moved from 2025-07-20 to "
        "2025-07-21; posture changed from bullish_risk_on to "
        "defensive_risk_off; preview decision changed from "
        "offline_preview_bullish_risk_on to "
        "offline_preview_defensive_risk_off."
    )

    history_lines = (output_root / "history_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(history_lines) == 2
    first_history_entry = json.loads(history_lines[0])
    second_history_entry = json.loads(history_lines[1])
    assert first_history_entry["sequence_number"] == 1
    assert second_history_entry["sequence_number"] == 2
    assert second_history_entry["posture"] == "defensive_risk_off"
    assert second_history_entry["delta_summary_text"] == delta["delta_summary_text"]

    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()[0]
    )
    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    assert record["history_delta"] == delta
    assert manifest["history_delta"] == delta
    assert manifest["previous_packet_found"] is True
    assert delta["delta_summary_text"] in brief


def test_etf_sma_daily_paper_lab_delta_reports_changed_operational_fields(
    tmp_path: Path,
) -> None:
    """Seeded history proves blocker, validation, broker, and action changes."""
    output_root = tmp_path / "paper_lab_out"
    output_root.mkdir(parents=True)
    seeded_history_entry = {
        "history_entry_version": "assistant_v1.2_history_entry",
        "sequence_number": 1,
        "run_id": "daily_paper_lab_2025-07-19",
        "as_of_date": "2025-07-19",
        "posture": "defensive_risk_off",
        "preview_decision": "offline_preview_defensive_risk_off",
        "blocker_status": "legacy_blocker",
        "validation_status": "fail",
        "broker_state_mode": "offline_preview_only",
        "research_board_fingerprint": "legacy_research_board",
        "next_operator_action": "legacy_operator_action",
    }
    (output_root / "history_ledger.jsonl").write_text(
        json.dumps(seeded_history_entry, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    delta = payload["history_delta"]
    assert delta["previous_packet_found"] is True
    assert delta["previous_as_of_date"] == "2025-07-19"
    assert delta["current_as_of_date"] == "2025-07-20"
    assert delta["posture_changed"] is True
    assert delta["preview_decision_changed"] is True
    assert delta["blocker_status_changed"] is True
    assert delta["previous_blocker_status"] == "legacy_blocker"
    assert delta["current_blocker_status"] == "broker_state_not_observed"
    assert delta["validation_status_changed"] is True
    assert delta["previous_validation_status"] == "fail"
    assert delta["current_validation_status"] == "pass"
    assert delta["broker_state_mode_changed"] is True
    assert delta["previous_broker_state_mode"] == "offline_preview_only"
    assert delta["current_broker_state_mode"] == "broker_state_not_observed"
    assert delta["research_board_changed"] is True
    assert delta["research_board_delta_status"] == "changed"
    assert delta["next_operator_action_changed"] is True
    assert delta["previous_next_operator_action"] == "legacy_operator_action"
    assert (
        delta["current_next_operator_action"]
        == "review_assistant_brief_no_broker_action"
    )
    assert delta["delta_summary_text"] == (
        "Prior packet found; as-of date moved from 2025-07-19 to "
        "2025-07-20; posture changed from defensive_risk_off to "
        "bullish_risk_on; preview decision changed from "
        "offline_preview_defensive_risk_off to "
        "offline_preview_bullish_risk_on; blocker status changed from "
        "legacy_blocker to broker_state_not_observed; validation status "
        "changed from fail to pass; broker-state mode changed from "
        "offline_preview_only to broker_state_not_observed; research board "
        "changed; next operator action changed from legacy_operator_action "
        "to review_assistant_brief_no_broker_action."
    )

    history_lines = (output_root / "history_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(history_lines) == 2
    appended_entry = json.loads(history_lines[1])
    assert appended_entry["sequence_number"] == 2
    assert appended_entry["validation_status"] == "pass"
    assert appended_entry["blocker_status"] == "broker_state_not_observed"
    review_action = payload["executive_action_queue"][0]
    assert review_action["action_id"] == "review_material_history_delta"
    assert review_action["priority"] == "P1"
    assert review_action["action_type"] == "operator_action"
    assert review_action["requires_daniel"] is True
    assert review_action["hard_gate_required"] is False
    assert "posture_changed" in review_action["reason_codes"]
    assert "blocker_status_changed" in review_action["reason_codes"]
    assert "validation_status_changed" in review_action["reason_codes"]
    assert payload["executive_action_summary"]["daniel_action_required"] is True


def test_etf_sma_daily_paper_lab_validator_reports_missing_fields_and_artifacts(
    tmp_path: Path,
) -> None:
    """Validator failure output is deterministic for missing fields and artifacts."""
    output_root = tmp_path / "paper_lab_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    record_path = output_root / "operating_record.jsonl"
    record = json.loads(record_path.read_text(encoding="utf-8").splitlines()[0])
    del record["input_data_path"]
    del record["safety_labels"]
    record["paper_submit_authorized"] = True
    record["paper_submit_authorization_status"] = "authorized"
    record_path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_root / "manifest.jsonl").unlink()

    validation = validate_etf_sma_daily_paper_lab_packet(output_root)
    repeated_validation = validate_etf_sma_daily_paper_lab_packet(output_root)

    assert validation == repeated_validation
    assert validation["assistant_packet_version"] == "assistant_v1.1"
    assert validation["validation_status"] == "fail"
    assert validation["artifact_presence_status"]["status"] == "fail"
    assert validation["artifact_presence_status"]["missing_artifacts"] == ["manifest"]
    assert validation["artifact_presence_status"]["empty_artifacts"] == []
    assert validation["missing_required_fields"] == [
        "input_data_path",
        "safety_labels",
        "paper_submit_authorized_false_or_not_authorized",
    ]
    assert validation["quality_gate_status"] == "fail"
    assert "required_packet_artifacts_exist" in validation["quality_gate_failed_checks"]
    assert (
        "required_operating_record_fields_exist"
        in validation["quality_gate_failed_checks"]
    )
    assert "required_manifest_fields_exist" in validation["quality_gate_failed_checks"]


def test_etf_sma_daily_paper_lab_review_handoff_sections_and_safety(
    tmp_path: Path,
) -> None:
    """Review handoff is paste-ready and carries the required safety assessment."""
    output_root = tmp_path / "paper_lab_out"
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    handoff_path = output_root / "review_handoff.md"
    assert handoff_path.exists()
    assert payload["review_handoff_path"].endswith("review_handoff.md")
    handoff = handoff_path.read_text(encoding="utf-8")
    for section in (
        "## Classification request",
        "## Packet identity",
        "## Executive summary",
        "## Trading desk state",
        "## Quality gate result",
        "## Decision ledger",
        "## Next action selector",
        "## Work order exports",
        "## Executive action queue",
        "## Research board",
        "## Research candidate queue",
        "## Baseline health evaluation",
        "## Baseline evidence metrics",
        "## Paper observation readiness",
        "## Candidate Gap Closure Queue",
        "## Candidate Risk Rule Status",
        "## History delta",
        "## Safety assessment",
        "## Reviewer instructions",
    ):
        assert section in handoff
    assert "accepted-with-minor-note" in handoff
    assert (
        "classification: accepted|accepted-with-minor-note|needs-repair|rejected"
        in handoff
    )
    assert "No broker reads were performed by this command." in handoff
    assert "No broker mutation was performed." in handoff
    assert "No paper submit was performed." in handoff
    assert "No live trading was performed." in handoff
    assert "No network calls were performed." in handoff
    assert "broker_state_not_observed" in handoff
    assert "usable_control_harness" in handoff
    assert "baseline_health_evaluation.jsonl" in handoff
    assert "baseline_evidence_metrics.jsonl" in handoff
    assert "paper_observation_readiness.jsonl" in handoff
    assert "hard_gate_prepared_not_authorized" in handoff
    assert "metrics_partially_available" in handoff
    assert "etf-sma-authorized-adjusted-baseline-metrics" in handoff
    assert (
        "python -m pytest tests\\unit\\test_etf_sma_daily_paper_lab.py "
        "-k baseline_health_evaluation"
    ) in handoff
    assert "decision_ledger_no_review_input" in handoff
    assert "review_input_not_found" in handoff
    for artifact_name in (
        "operating_brief.md",
        "operating_record.jsonl",
        "manifest.jsonl",
        "history_ledger.jsonl",
        "review_handoff.md",
        "decision_ledger.jsonl",
        "research_candidate_queue.jsonl",
        "baseline_health_evaluation.jsonl",
        "baseline_evidence_metrics.jsonl",
        "paper_observation_readiness.jsonl",
        "candidate_gap_closure_queue.jsonl",
        "turnover_summary.jsonl",
        "cost_model_summary.jsonl",
        "review_inputs",
        "work_orders",
        "gpt_next_action_handoff.md",
        "codex_work_order.md",
        "antigravity_review_order.md",
        "claude_critique_order.md",
    ):
        assert artifact_name in handoff


def test_etf_sma_daily_paper_lab_ingests_review_feedback_decision_ledger(
    tmp_path: Path,
) -> None:
    """Saved offline review text is normalized and appended to the decision ledger."""
    output_root = tmp_path / "paper_lab_out"
    review_inputs = output_root / "review_inputs"
    review_inputs.mkdir(parents=True)
    review_file = review_inputs / "gpt_review.md"
    review_file.write_text(
        "\n".join(
            (
                "reviewer: GPT",
                "classification: needs repair",
                "blocking_findings:",
                "- Decision ledger status is missing from the packet.",
                "repair_items:",
                "- Add deterministic decision ledger status to the daily artifacts.",
                "minor_notes: none",
                "recommended_next_action: repair offline packet artifacts and rerun daily lab",
            )
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    expected_hash = hashlib.sha256(review_file.read_bytes()).hexdigest()
    assert payload["validation_status"] == "pass"
    assert payload["quality_gate_status"] == "pass"
    assert payload["decision_ledger_status"] == "decision_ledger_appended"
    assert payload["decision_ledger_append_status"] == "appended"
    assert payload["decision_ledger_entry_count"] == 1
    assert payload["review_input_status"] == "review_input_ingested"
    assert payload["review_input_path"].endswith("review_inputs/gpt_review.md")
    assert payload["review_input_sha256"] == expected_hash
    assert payload["reviewer_source"] == "GPT"
    assert payload["review_classification"] == "needs-repair"
    assert payload["review_blockers"] == [
        "Decision ledger status is missing from the packet."
    ]
    assert payload["review_repair_items"] == [
        "Add deterministic decision ledger status to the daily artifacts."
    ]
    assert payload["review_selected_next_action"] == (
        "repair offline packet artifacts and rerun daily lab"
    )
    _assert_next_action_selector_shape(payload["next_action_selector"])
    assert payload["next_action_selector"]["status"] == "repair_work_order_selected"
    assert payload["next_action_selector"]["priority"] == "P1"
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        "repair_review_feedback_before_next_packet_use"
    )
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is True
    _assert_work_order_exports_shape(payload["work_order_exports"])
    action_ids = [action["action_id"] for action in payload["executive_action_queue"]]
    assert action_ids == [
        "repair_review_feedback_before_next_packet_use",
        "quantify_spy_sma_baseline_confidence",
        "no_daniel_action_required_now",
    ]
    repair_action = payload["executive_action_queue"][0]
    _assert_action_queue_item_shape(repair_action)
    assert repair_action["priority"] == "P1"
    assert repair_action["action_type"] == "validation_action"
    assert repair_action["requires_daniel"] is False
    assert repair_action["hard_gate_required"] is False
    assert repair_action["safety_scope"] == (
        "offline_review_repair_only_no_broker_access_no_submit"
    )
    assert "paper order" not in json.dumps(repair_action, sort_keys=True).lower()
    assert "live trading" not in json.dumps(repair_action, sort_keys=True).lower()

    ledger_lines = (output_root / "decision_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(ledger_lines) == 1
    ledger_entry = json.loads(ledger_lines[0])
    assert ledger_entry["decision_ledger_entry_version"] == (
        "assistant_v1.5_decision_ledger_entry"
    )
    assert ledger_entry["sequence_number"] == 1
    assert ledger_entry["assistant_packet_version"] == "assistant_v1.1"
    assert ledger_entry["quality_gate_status"] == "pass"
    assert ledger_entry["reviewer_source"] == "GPT"
    assert ledger_entry["classification"] == "needs-repair"
    assert ledger_entry["review_input_sha256"] == expected_hash
    assert ledger_entry["ledger_append_status"] == "appended"
    assert ledger_entry["safety_scope"] == (
        "offline_review_decision_only_no_broker_access_no_submit"
    )

    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    assert record["review_classification"] == "needs-repair"
    assert record["decision_ledger_status"] == "decision_ledger_appended"
    assert manifest["review_classification"] == "needs-repair"
    assert manifest["decision_ledger_status"] == "decision_ledger_appended"
    assert "decision_ledger" in manifest["indexed_artifacts"]
    assert validate_etf_sma_daily_paper_lab_packet(output_root)["validation_status"] == (
        "pass"
    )

    rerun_payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )
    rerun_ledger_lines = (output_root / "decision_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(rerun_ledger_lines) == 1
    assert rerun_payload["decision_ledger_status"] == "decision_ledger_already_recorded"
    assert rerun_payload["decision_ledger_append_status"] == "already_recorded"


def test_etf_sma_daily_paper_lab_accepted_review_selects_safe_offline_action(
    tmp_path: Path,
) -> None:
    """Accepted review input lets the selector choose the next safe offline action."""
    output_root = tmp_path / "paper_lab_out"
    review_inputs = output_root / "review_inputs"
    review_inputs.mkdir(parents=True)
    (review_inputs / "gpt_review.md").write_text(
        "\n".join(
            (
                "reviewer: GPT",
                "classification: accepted",
                "blocking_findings: none",
                "minor_notes: none",
                "recommended_next_action: continue offline packet history",
            )
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    _assert_quality_gate_pass(payload)
    assert payload["review_selected_next_action"] == (
        "continue offline packet history"
    )
    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert payload["next_action_selector"]["selected_research_candidate_id"] is None
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    assert payload["next_action_selector"]["broker_action_allowed"] is False
    assert payload["next_action_selector"]["llm_runtime_calls_allowed"] is False
    assert "candidate_backtest_result_packet_ready" in payload["next_action_selector"][
        "reason_codes"
    ]
    assert payload["candidate_gap_closure_queue"]["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_001"
    )


def test_etf_sma_daily_paper_lab_quality_gate_failure_is_deterministic(
    tmp_path: Path,
) -> None:
    """Removing required v1.4 packet pieces creates repeatable gate failures."""
    output_root = tmp_path / "paper_lab_out"
    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    record_path = output_root / "operating_record.jsonl"
    record = json.loads(record_path.read_text(encoding="utf-8").splitlines()[0])
    del record["quality_gate_status"]
    record_path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_root / "review_handoff.md").unlink()

    validation = validate_etf_sma_daily_paper_lab_packet(output_root)
    repeated_validation = validate_etf_sma_daily_paper_lab_packet(output_root)

    assert validation == repeated_validation
    assert validation["quality_gate_status"] == "fail"
    assert validation["review_handoff_status"] == "missing"
    assert validation["quality_gate_score"] == (
        "21/38 required checks passed; 17 failed; 0 warnings"
    )
    assert validation["quality_gate_failed_checks"] == [
        "required_packet_artifacts_exist",
        "required_operating_record_fields_exist",
        "strategy_comparison_scaffold_generated",
        "candidate_strategy_evidence_template_generated",
        "candidate_evidence_requirements_generated",
        "candidate_evidence_collection_plan_generated",
        "candidate_evidence_collection_status_generated",
        "candidate_evidence_gap_summary_generated",
        "candidate_gap_closure_queue_generated",
        "candidate_risk_rule_status_generated",
        "candidate_signal_rule_status_generated",
        "shared_risk_rule_status_generated",
        "shared_signal_rule_status_generated",
        "shared_benchmark_comparison_status_generated",
        "candidate_backtest_result_packet_generated",
        "assistant_v1_through_v1_11_outputs_preserved",
        "review_handoff_references_generated_artifacts",
    ]


def test_etf_sma_daily_paper_lab_validation_failure_priority_is_deterministic(
    tmp_path: Path,
) -> None:
    """Safety validation failures map to P0; ordinary repair work maps to P1."""
    payload = build_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=tmp_path / "paper_lab_out",
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    payload["validation_status"] = "fail"
    payload["missing_required_fields"] = [
        "paper_submit_authorized_false_or_not_authorized",
    ]
    payload["artifact_presence_status"] = {
        "status": "pass",
        "missing_artifacts": [],
        "empty_artifacts": [],
        "artifacts": {},
    }
    paper_lab_module._apply_executive_action_queue(payload)

    p0_action = payload["executive_action_queue"][0]
    _assert_action_queue_item_shape(p0_action)
    assert p0_action["action_id"] == "validation_safety_invariant_failure"
    assert p0_action["priority"] == "P0"
    assert p0_action["action_type"] == "validation_action"
    assert p0_action["requires_daniel"] is True
    assert p0_action["hard_gate_required"] is True

    payload["missing_required_fields"] = ["input_data_path"]
    payload["artifact_presence_status"] = {
        "status": "fail",
        "missing_artifacts": ["operating_record"],
        "empty_artifacts": [],
        "artifacts": {},
    }
    paper_lab_module._apply_executive_action_queue(payload)

    p1_action = payload["executive_action_queue"][0]
    _assert_action_queue_item_shape(p1_action)
    assert p1_action["action_id"] == "validation_packet_repair_required"
    assert p1_action["priority"] == "P1"
    assert p1_action["action_type"] == "validation_action"
    assert p1_action["requires_daniel"] is True
    assert p1_action["hard_gate_required"] is False


def test_etf_sma_daily_paper_lab_broker_not_observed_makes_no_position_claim(
    tmp_path: Path,
) -> None:
    """Broker-not-observed packets avoid position and open-order claims."""
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=tmp_path / "paper_lab_out",
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    assert payload["broker_state_mode"] == "broker_state_not_observed"
    assert payload["broker_state_observed"] is False
    assert payload["blocker_status"] == "broker_state_not_observed"
    assert payload["executive_summary"]["current_blocker"] == (
        "broker_state_not_observed"
    )
    assert payload["paper_submit_authorized"] is False
    assert payload["live_authorized"] is False
    assert payload["broker_mutation_performed"] is False
    broker_claim = payload["broker_state_claim"].lower()
    assert "not read" in broker_claim
    assert "makes no position or order-state claim" in broker_claim
    assert "no positions" not in broker_claim
    assert "no open orders" not in broker_claim
    output_root = tmp_path / "paper_lab_out"
    packet_text = "\n".join(
        (
            (output_root / "operating_brief.md").read_text(encoding="utf-8"),
            (output_root / "review_handoff.md").read_text(encoding="utf-8"),
            json.dumps(payload, sort_keys=True),
        )
    ).lower()
    assert "no positions" not in packet_text
    assert "no open orders" not in packet_text
    mission = json.loads(
        (output_root / "mission_control.json").read_text(encoding="utf-8")
    )
    broker = mission["broker_state_lane"]
    latest = mission["latest_run"]
    daily_summary = mission["daily_decision_summary"]
    data_refresh_dry_run = mission["data_refresh_dry_run"]
    assert broker["broker_state_mode"] == "broker_state_not_observed"
    assert broker["broker_state_status"] == "broker_state_not_observed"
    assert broker["broker_state_observed"] is False
    assert broker["broker_read_performed"] is False
    assert broker["broker_mutation_performed"] is False
    assert broker["paper_submit_authorized"] is False
    assert broker["live_authorized"] is False
    assert daily_summary["broker_state_mode"] == "broker_state_not_observed"
    assert daily_summary["broker_state_status"] == "broker_state_not_observed"
    assert daily_summary["spy_position_observed"] is False
    assert daily_summary["spy_position_present"] is None
    assert daily_summary["spy_position_qty"] is None
    assert daily_summary["open_spy_order_count"] is None
    assert daily_summary["main_blocker"] == "broker_state_not_observed"
    assert latest["main_blocker"] == "broker_state_not_observed"
    assert latest["broker_state_observed"] is False
    assert latest["observed_spy_position_qty"] is None
    assert latest["observed_spy_open_order_count"] is None
    assert data_refresh_dry_run["broker_state_observed"] is False
    assert data_refresh_dry_run["broker_state_not_observed"] is True
    assert mission["daily_approval_gate"]["submit_allowed"] is False
    assert mission["daily_approval_gate"]["paper_submit_authorized"] is False
    assert mission["daily_approval_gate"]["live_authorized"] is False
    assert mission["daily_approval_gate"]["broker_mutation_performed"] is False
    assert payload["quality_gate_status"] == "pass"
    assert "broker_not_observed_has_no_position_order_claim" not in payload[
        "quality_gate_failed_checks"
    ]
    assert all(
        "broker_state_not_observed" in action["safety_scope"]
        or "no_broker_access" in action["safety_scope"]
        for action in payload["executive_action_queue"]
    )


def test_etf_sma_daily_paper_lab_paper_submit_false_never_queues_submit(
    tmp_path: Path,
) -> None:
    """The executive action queue never recommends paper submit when unauthorized."""
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=tmp_path / "paper_lab_out",
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    assert payload["paper_submit_authorized"] is False
    assert payload["paper_submit_authorization_status"] == "not_authorized"
    assert payload["quality_gate_status"] == "pass"
    assert "paper_submit_not_authorized" not in payload["quality_gate_failed_checks"]
    forbidden_recommendations = (
        "submit_order",
        "place_order",
        "paper order",
        "paper_submit_authorized=true",
    )
    for action in payload["executive_action_queue"]:
        action_text = json.dumps(action, sort_keys=True).lower()
        assert not any(term in action_text for term in forbidden_recommendations)


def test_etf_sma_daily_paper_lab_research_confidence_gap_queues_p2(
    tmp_path: Path,
) -> None:
    """Unquantified research confidence creates a P2 non-Daniel research action."""
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=tmp_path / "paper_lab_out",
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    assert payload["research_lab"]["confidence_status"] == (
        "confidence_not_yet_quantified"
    )
    research_actions = [
        action
        for action in payload["executive_action_queue"]
        if action["action_id"] == "quantify_spy_sma_baseline_confidence"
    ]
    assert len(research_actions) == 1
    action = research_actions[0]
    assert action["priority"] == "P2"
    assert action["action_type"] == "research_action"
    assert action["requires_daniel"] is False
    assert action["hard_gate_required"] is False


def test_etf_sma_daily_paper_lab_research_board_active_baseline_fields(
    tmp_path: Path,
) -> None:
    """Research Board emits the active SPY SMA 50/200 baseline and required fields."""
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=tmp_path / "paper_lab_out",
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    board = payload["research_lab"]["research_board"]
    assert board == payload["research_lab"]["candidate_strategy_board"]
    assert board == payload["research_board"]
    for item in board:
        _assert_research_board_item_shape(item)
    assert board[0]["candidate_name"] == "SPY SMA 50/200 daily long-only baseline"
    assert board[0]["status"] == "active_baseline"
    assert board[0]["evidence_status"] == "daily_sma_signal_evaluated_from_offline_csv"
    assert board[0]["confidence_status"] == "confidence_not_yet_quantified"
    assert "offline_backtest_confidence_summary" in board[0]["missing_evidence"]


def test_etf_sma_daily_paper_lab_insufficient_history(tmp_path: Path) -> None:
    """Test run with only 199 bars, resulting in insufficient history."""
    output_root = tmp_path / "paper_lab_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_199.csv"

    config = EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=bars_csv,
        as_of_date="2025-07-19",
        symbol="SPY",
    )

    payload = run_etf_sma_daily_paper_lab(config)

    assert payload["posture"] == "insufficient_history"
    assert payload["decision"] == "insufficient_history"
    assert payload["sma_slow_value"] is None
    assert payload["sma_posture_status"] == (
        "insufficient_history: 199 usable bars is fewer than "
        "the 200-bar slow SMA requirement"
    )
    assert payload["next_operator_action"] == (
        "provide_at_least_200_usable_daily_bars_before_preview_use"
    )
    offline_data_action = payload["executive_action_queue"][0]
    assert offline_data_action["action_id"] == "provide_missing_offline_daily_history"
    assert offline_data_action["priority"] == "P1"
    assert offline_data_action["action_type"] == "operator_action"
    assert offline_data_action["requires_daniel"] is True
    assert offline_data_action["hard_gate_required"] is False
    assert "offline_input_required" in offline_data_action["reason_codes"]


def test_etf_sma_daily_paper_lab_defensive_bearish(tmp_path: Path) -> None:
    """Test successful run with 200 bearish bars, resulting in risk-off posture."""
    output_root = tmp_path / "paper_lab_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bearish.csv"

    config = EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=bars_csv,
        as_of_date="2025-07-20",
        symbol="SPY",
    )

    payload = run_etf_sma_daily_paper_lab(config)

    assert payload["posture"] == "defensive_risk_off"
    assert payload["decision"] == "offline_preview_defensive_risk_off"
    assert payload["sma_posture_status"] == "risk_off: SMA50 is at or below SMA200"
    assert payload["next_operator_action"] == "review_assistant_brief_no_broker_action"


def test_etf_sma_daily_paper_lab_cli_invocation(tmp_path: Path) -> None:
    """Test invocation of the new command via CLI."""
    output_root = tmp_path / "paper_lab_cli_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    argv = [
        "etf-sma-daily-paper-lab",
        "--output-root", str(output_root),
        "--bars-csv", str(bars_csv),
        "--as-of-date", "2025-07-20",
        "--symbol", "SPY",
        "--format", "json",
    ]

    exit_code = cli_module.main(argv)
    assert exit_code == 0

    assert (output_root / "operating_brief.md").exists()
    assert (output_root / "operating_record.jsonl").exists()
    assert (output_root / "manifest.jsonl").exists()
    assert (output_root / "research_board_prioritization.jsonl").exists()
    assert (output_root / "strategy_comparison_scaffold.jsonl").exists()
    assert (output_root / "index.html").exists()
    assert (output_root / "assistant_report.md").exists()
    assert (output_root / "mission_control.json").exists()
    assert (output_root / "mission_control_validation.json").exists()
    assert (output_root / "latest_run.json").exists()


def _generate_mission_control_output(tmp_path: Path, name: str) -> Path:
    output_root = tmp_path / name
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )
    return output_root


def _write_shifted_spy_fixture(
    target_csv: Path,
    *,
    latest_bar_date: str,
) -> str:
    source_lines = (FIXTURES_DIR / "spy_daily_bars_200_bullish.csv").read_text(
        encoding="utf-8"
    ).splitlines()
    rows = source_lines[1:]
    end_date = date.fromisoformat(latest_bar_date)
    start_date = end_date - timedelta(days=len(rows) - 1)
    output_lines = [source_lines[0]]
    for offset, row in enumerate(rows):
        _, rest = row.split(",", 1)
        output_lines.append(
            f"{(start_date + timedelta(days=offset)).isoformat()},{rest}"
        )
    target_csv.parent.mkdir(parents=True, exist_ok=True)
    target_csv.write_text(
        "\n".join(output_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return hashlib.sha256(target_csv.read_bytes()).hexdigest()


def _write_accepted_refresh_manifest(
    tmp_path: Path,
    *,
    canonical_sha256: str,
    latest_bar_date: str,
) -> Path:
    manifest_path = (
        tmp_path / "runs" / "paper_lab" / "m446_adjusted_spy_bars_refresh_manifest.jsonl"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_record = {
        "refresh_state": "accepted_current_adjusted_bars",
        "expected_latest_bar_date": latest_bar_date,
        "latest_local_bar_date": latest_bar_date,
        "operator_input_sha256": "operator-fixture-sha",
        "refreshed_canonical_csv_path": (
            "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
        ),
        "refreshed_canonical_csv_sha256": canonical_sha256,
        "refresh_blockers": [],
        "refresh_warnings": [],
    }
    manifest_path.write_text(
        json.dumps(manifest_record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


def _read_mission_control(output_root: Path) -> dict[str, object]:
    return json.loads(
        (output_root / "mission_control.json").read_text(encoding="utf-8")
    )


def _write_mission_control(output_root: Path, mission: dict[str, object]) -> None:
    (output_root / "mission_control.json").write_text(
        json.dumps(mission, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _dispatcher_result(
    *,
    validation_status: str = "passed",
    staleness_days: int = 0,
    broker_read_performed: bool = False,
    broker_state_mode: str = "broker_state_not_observed",
    blocker_status: str = "broker_state_not_observed",
    missing_artifact: str | None = None,
    offline_validation_commands: list[str] | None = None,
    input_csv_present: bool = False,
    accepted_refresh_consumed: bool = False,
) -> dict[str, object]:
    artifacts: dict[str, object] = {
        "index_html": "index.html",
        "assistant_report_md": "assistant_report.md",
        "mission_control_json": "mission_control.json",
        "latest_run_json": "latest_run.json",
        "data_freshness_plan_json": "data_freshness_plan.json",
        "data_refresh_bridge_json": "data_refresh_bridge.json",
        "data_refresh_dry_run_json": "data_refresh_dry_run.json",
        "data_refresh_operator_checklist_md": "data_refresh_operator_checklist.md",
        "operator_review_md": "operator_review.md",
        "work_orders": "work_orders",
        "codex_next_prompt": "work_orders/codex_next_prompt.md",
        "codex_next_work_order": "work_orders/codex_next_work_order.json",
        "antigravity_review_prompt": "work_orders/antigravity_review_prompt.md",
        "antigravity_review_work_order": (
            "work_orders/antigravity_review_work_order.json"
        ),
        "claude_critique_prompt": "work_orders/claude_critique_prompt.md",
        "claude_critique_work_order": "work_orders/claude_critique_work_order.json",
        "gpt_report_classification_prompt": (
            "work_orders/gpt_report_classification_prompt.md"
        ),
        "gpt_next_decision_context": "work_orders/gpt_next_decision_context.json",
    }
    if missing_artifact is not None:
        artifacts.pop(missing_artifact)
    return paper_lab_module._mission_control_dispatcher(
        payload={},
        artifacts=artifacts,
        safety_gates={"all_clear": {"passed": True}},
        market_data_lane={"staleness_in_days": staleness_days},
        broker_state_lane={
            "broker_state_mode": broker_state_mode,
            "broker_read_performed": broker_read_performed,
        },
        decision_lane={"blocker_status": blocker_status},
        data_refresh_bridge={
            "offline_validation_commands": offline_validation_commands
            if offline_validation_commands is not None
            else ["python -m algotrader.cli etf-sma-adjusted-spy-bars-refresh-intake"],
            "accepted_refresh_consumed": accepted_refresh_consumed,
        },
        data_refresh_dry_run={
            "dry_run_status": (
                "ready_for_offline_intake_validation"
                if input_csv_present
                else "awaiting_operator_csv"
            ),
            "input_csv_present": input_csv_present,
            "ingest_performed": False,
            "accepted_refresh_consumed": accepted_refresh_consumed,
        },
        validation_summary={"validation_status": validation_status},
    )


def _read_json_artifact(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_false_safety_flags(
    container: dict[str, object],
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        assert container[field] is False


def _assert_execution_plan_safety(plan: dict[str, object]) -> None:
    assert _EXECUTION_PLAN_COMPACT_FIELDS <= set(plan)
    assert str(plan["execution_plan_version"]) == (
        "assistant_v1.64_pre_broker_execution_plan"
    )
    assert str(plan["execution_plan_id"]).startswith("daily_execution_plan_")
    assert plan["execution_plan_symbol"] == "SPY"
    assert plan["execution_plan_broker_order_required"] is False
    assert plan["execution_plan_submit_allowed"] is False
    assert plan["execution_plan_paper_submit_authorized"] is False
    assert plan["execution_plan_live_authorized"] is False
    assert plan["execution_plan_broker_mutation_performed"] is False
    assert plan["execution_plan_created_order_payload"] is False
    assert {"paper_lab_only", "not_live_authorized", "profit_claim=none"} <= set(
        plan["execution_plan_labels"]
    )
    serialized = json.dumps(plan, sort_keys=True).lower()
    assert "client_order_id" not in serialized
    assert "broker_order_payload" not in serialized
    assert "order_payload" not in serialized.replace(
        "execution_plan_created_order_payload",
        "",
    )


def _assert_daily_approval_gate_safety(gate: dict[str, object]) -> None:
    assert _DAILY_APPROVAL_GATE_FIELDS <= set(gate)
    assert str(gate["execution_plan_id"]).startswith("daily_execution_plan_")
    assert gate["submit_allowed"] is False
    assert gate["paper_submit_authorized"] is False
    assert gate["live_authorized"] is False
    assert gate["broker_mutation_performed"] is False
    serialized = json.dumps(gate, sort_keys=True).lower()
    assert "client_order_id" not in serialized
    assert "broker_request" not in serialized
    assert "submit_request" not in serialized
    assert "order_payload" not in serialized


def _expected_daily_approval_gate(
    *,
    plan: dict[str, object],
    expected_status: str,
    expected_action: str,
    expected_blocker: str,
) -> dict[str, object]:
    if expected_blocker != "none" or expected_status == "blocked" or (
        expected_action == "none"
    ):
        return {
            "execution_plan_id": plan["execution_plan_id"],
            "approval_required": False,
            "approval_state": "blocked",
            "submit_allowed": False,
            "paper_submit_authorized": False,
            "live_authorized": False,
            "broker_mutation_performed": False,
            "reason": "execution_plan_blocked",
            "blocker": (
                expected_blocker if expected_blocker != "none" else "execution_plan_blocked"
            ),
        }
    if expected_status == "no_action_required" and expected_action == "hold/noop":
        return {
            "execution_plan_id": plan["execution_plan_id"],
            "approval_required": False,
            "approval_state": "not_required_noop",
            "submit_allowed": False,
            "paper_submit_authorized": False,
            "live_authorized": False,
            "broker_mutation_performed": False,
            "reason": "execution_plan_requires_no_action",
            "blocker": "none",
        }
    if expected_status == "preview_only" and expected_action in {
        "buy_preview",
        "sell_preview",
    }:
        return {
            "execution_plan_id": plan["execution_plan_id"],
            "approval_required": True,
            "approval_state": "awaiting_explicit_paper_submit_authorization",
            "submit_allowed": False,
            "paper_submit_authorized": False,
            "live_authorized": False,
            "broker_mutation_performed": False,
            "reason": "explicit_paper_submit_authorization_required",
            "blocker": "none",
        }
    return {
        "execution_plan_id": plan["execution_plan_id"],
        "approval_required": False,
        "approval_state": "blocked",
        "submit_allowed": False,
        "paper_submit_authorized": False,
        "live_authorized": False,
        "broker_mutation_performed": False,
        "reason": "execution_plan_blocked",
        "blocker": "unsupported_execution_plan_state",
    }


def _assert_execution_plan_surfaces(
    mission: dict[str, object],
    *,
    expected_status: str,
    expected_action: str,
    expected_source_preview_decision: str,
    expected_blocker: str,
    expected_requires_approval: bool,
    expected_reason: str | None = None,
) -> dict[str, object]:
    plan = mission["execution_plan"]
    assert isinstance(plan, dict)
    _assert_execution_plan_safety(plan)
    assert plan["execution_plan_status"] == expected_status
    assert plan["execution_plan_action"] == expected_action
    assert (
        plan["execution_plan_source_preview_decision"]
        == expected_source_preview_decision
    )
    assert plan["execution_plan_blocker"] == expected_blocker
    assert plan["execution_plan_requires_approval"] is expected_requires_approval
    if expected_reason is not None:
        assert plan["execution_plan_reason"] == expected_reason

    for section_name in ("latest_run", "daily_latest", "daily_decision_summary"):
        section = mission[section_name]
        assert isinstance(section, dict)
        assert _EXECUTION_PLAN_COMPACT_FIELDS <= set(section)
        for field in _EXECUTION_PLAN_COMPACT_FIELDS:
            assert section[field] == plan[field]
        _assert_execution_plan_safety(section)

    latest_plan = mission["latest_run"]["execution_plan"]
    daily_latest_plan = mission["daily_latest"]["execution_plan"]
    assert latest_plan == plan
    assert daily_latest_plan == plan

    expected_gate = _expected_daily_approval_gate(
        plan=plan,
        expected_status=expected_status,
        expected_action=expected_action,
        expected_blocker=expected_blocker,
    )
    gate = mission["daily_approval_gate"]
    assert isinstance(gate, dict)
    assert gate == expected_gate
    _assert_daily_approval_gate_safety(gate)
    for section_name in ("latest_run", "daily_latest", "daily_decision_summary"):
        section = mission[section_name]
        assert isinstance(section, dict)
        assert section["daily_approval_gate"] == gate
        assert _DAILY_APPROVAL_GATE_COMPACT_FIELDS <= set(section)
        for field in _DAILY_APPROVAL_GATE_FIELDS:
            assert section[f"daily_approval_gate_{field}"] == gate[field]
        _assert_daily_approval_gate_safety(section["daily_approval_gate"])

    return plan


def _daily_execution_plan_for_gate(
    **overrides: object,
) -> paper_lab_module.EtfSmaDailyExecutionPlan:
    values: dict[str, object] = {
        "execution_plan_version": "assistant_v1.64_pre_broker_execution_plan",
        "execution_plan_id": "daily_execution_plan_unit",
        "execution_plan_status": "no_action_required",
        "execution_plan_action": "hold/noop",
        "execution_plan_symbol": "SPY",
        "execution_plan_reason": "existing_spy_position_satisfies_risk_on_preview",
        "execution_plan_blocker": "none",
        "execution_plan_source_preview_decision": "hold/noop",
        "execution_plan_requires_approval": False,
        "execution_plan_broker_order_required": False,
        "execution_plan_submit_allowed": False,
        "execution_plan_paper_submit_authorized": False,
        "execution_plan_live_authorized": False,
        "execution_plan_broker_mutation_performed": False,
        "execution_plan_created_order_payload": False,
        "execution_plan_labels": (
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
        ),
    }
    values.update(overrides)
    return paper_lab_module.EtfSmaDailyExecutionPlan(**values)


def test_etf_sma_daily_execution_plan_type_is_immutable() -> None:
    plan = paper_lab_module.EtfSmaDailyExecutionPlan(
        execution_plan_version="assistant_v1.64_pre_broker_execution_plan",
        execution_plan_id="daily_execution_plan_unit",
        execution_plan_status="no_action_required",
        execution_plan_action="hold/noop",
        execution_plan_symbol="SPY",
        execution_plan_reason="existing_spy_position_satisfies_risk_on_preview",
        execution_plan_blocker="none",
        execution_plan_source_preview_decision="hold/noop",
        execution_plan_requires_approval=False,
        execution_plan_broker_order_required=False,
        execution_plan_submit_allowed=False,
        execution_plan_paper_submit_authorized=False,
        execution_plan_live_authorized=False,
        execution_plan_broker_mutation_performed=False,
        execution_plan_created_order_payload=False,
        execution_plan_labels=(
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
        ),
    )

    with pytest.raises(FrozenInstanceError):
        plan.execution_plan_status = "mutated"  # type: ignore[misc]


def test_etf_sma_daily_approval_gate_noop_is_immutable_and_deterministic() -> None:
    plan = _daily_execution_plan_for_gate()
    before = plan.to_dict()

    gate = paper_lab_module._project_daily_approval_gate(plan)
    repeated_gate = paper_lab_module._project_daily_approval_gate(plan)

    assert gate.to_dict() == {
        "execution_plan_id": "daily_execution_plan_unit",
        "approval_required": False,
        "approval_state": "not_required_noop",
        "submit_allowed": False,
        "paper_submit_authorized": False,
        "live_authorized": False,
        "broker_mutation_performed": False,
        "reason": "execution_plan_requires_no_action",
        "blocker": "none",
    }
    assert repeated_gate.to_dict() == gate.to_dict()
    assert plan.to_dict() == before
    _assert_daily_approval_gate_safety(gate.to_dict())
    with pytest.raises(FrozenInstanceError):
        gate.approval_state = "mutated"  # type: ignore[misc]


@pytest.mark.parametrize("action", ["buy_preview", "sell_preview"])
def test_etf_sma_daily_approval_gate_actionable_preview_requires_approval(
    action: str,
) -> None:
    plan = _daily_execution_plan_for_gate(
        execution_plan_status="preview_only",
        execution_plan_action=action,
        execution_plan_reason=f"{action}_requires_explicit_authorization",
        execution_plan_source_preview_decision=action,
        execution_plan_requires_approval=True,
    )

    gate = paper_lab_module._project_daily_approval_gate(plan).to_dict()

    assert gate["execution_plan_id"] == plan.execution_plan_id
    assert gate["approval_required"] is True
    assert gate["approval_state"] == "awaiting_explicit_paper_submit_authorization"
    assert gate["submit_allowed"] is False
    assert gate["paper_submit_authorized"] is False
    assert gate["live_authorized"] is False
    assert gate["broker_mutation_performed"] is False
    assert gate["reason"] == "explicit_paper_submit_authorization_required"
    assert gate["blocker"] == "none"
    _assert_daily_approval_gate_safety(gate)


@pytest.mark.parametrize(
    "blocker",
    [
        "open_order_present",
        "unexpected_non_spy_position",
        "stale_snapshot",
        "broker_state_not_observed",
        "insufficient_history",
    ],
)
def test_etf_sma_daily_approval_gate_blocked_plan_fails_closed(
    blocker: str,
) -> None:
    plan = _daily_execution_plan_for_gate(
        execution_plan_status="blocked",
        execution_plan_action="none",
        execution_plan_reason=blocker,
        execution_plan_blocker=blocker,
        execution_plan_source_preview_decision=f"blocked/{blocker}",
    )

    gate = paper_lab_module._project_daily_approval_gate(plan).to_dict()

    assert gate["approval_required"] is False
    assert gate["approval_state"] == "blocked"
    assert gate["submit_allowed"] is False
    assert gate["reason"] == "execution_plan_blocked"
    assert gate["blocker"] == blocker
    _assert_daily_approval_gate_safety(gate)


def test_etf_sma_daily_approval_gate_unknown_plan_state_fails_closed() -> None:
    plan = _daily_execution_plan_for_gate(
        execution_plan_status="unsupported",
        execution_plan_action="rebalance_preview",
        execution_plan_source_preview_decision="rebalance_preview",
        execution_plan_requires_approval=True,
    )

    gate = paper_lab_module._project_daily_approval_gate(plan).to_dict()

    assert gate["approval_required"] is False
    assert gate["approval_state"] == "blocked"
    assert gate["submit_allowed"] is False
    assert gate["paper_submit_authorized"] is False
    assert gate["live_authorized"] is False
    assert gate["broker_mutation_performed"] is False
    assert gate["reason"] == "execution_plan_blocked"
    assert gate["blocker"] == "unsupported_execution_plan_state"
    _assert_daily_approval_gate_safety(gate)


@pytest.mark.parametrize(
    "unsafe_field",
    [
        "execution_plan_broker_order_required",
        "execution_plan_submit_allowed",
        "execution_plan_paper_submit_authorized",
        "execution_plan_live_authorized",
        "execution_plan_broker_mutation_performed",
        "execution_plan_created_order_payload",
    ],
)
def test_etf_sma_daily_approval_gate_unsafe_plan_flags_fail_closed(
    unsafe_field: str,
) -> None:
    plan = _daily_execution_plan_for_gate(**{unsafe_field: True})

    gate = paper_lab_module._project_daily_approval_gate(plan).to_dict()

    assert gate["approval_required"] is False
    assert gate["approval_state"] == "blocked"
    assert gate["submit_allowed"] is False
    assert gate["paper_submit_authorized"] is False
    assert gate["live_authorized"] is False
    assert gate["broker_mutation_performed"] is False
    assert gate["reason"] == "execution_plan_blocked"
    assert gate["blocker"] == "execution_plan_safety_flags_not_false"


def _assert_expected_artifacts_exist(output_root: Path) -> dict[str, Path]:
    paths = {
        key: output_root / relative_path
        for key, relative_path in _MISSION_CONTROL_ARTIFACT_RELATIVE_PATHS.items()
    }
    for path in paths.values():
        assert path.exists()

    work_orders_dir = output_root / "work_orders"
    assert _MISSION_CONTROL_WORK_ORDER_FILES <= {
        path.name for path in work_orders_dir.iterdir() if path.is_file()
    }
    for path in _MISSION_CONTROL_AGENT_INBOX_PATHS:
        assert path.exists()

    return paths


def _assert_path_fields_exist(
    container: dict[str, object],
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        assert Path(str(container[field]).split("#", 1)[0]).exists()


def _assert_no_forbidden_routes(dispatcher: dict[str, object]) -> None:
    selected_route = str(dispatcher["selected_route"])
    assert selected_route not in dispatcher["forbidden_routes"]
    for fragment in _FORBIDDEN_ROUTE_FRAGMENTS:
        assert fragment not in selected_route
    _assert_false_safety_flags(
        dispatcher,
        ("broker_read_authorized", "paper_submit_authorized", "live_authorized"),
    )


def _assert_data_freshness_plan_shape(plan: dict[str, object]) -> None:
    assert {
        "data_freshness_status",
        "data_as_of",
        "generated_at",
        "staleness_days",
        "staleness_policy",
        "accepted_data_path",
        "accepted_data_basis",
        "accepted_row_count",
        "preview_only_reason",
        "freshness_blocker",
        "offline_refresh_needed",
        "external_api_required",
        "secrets_required",
        "broker_read_required",
        "paid_service_required",
        "next_offline_data_action",
        "operator_data_action_summary",
        "safe_to_continue_preview_only",
        "safety_labels",
    } <= set(plan)
    assert plan["external_api_required"] is False
    assert plan["secrets_required"] is False
    assert plan["broker_read_required"] is False
    assert plan["paid_service_required"] is False
    assert "paper_lab_only" in plan["safety_labels"]
    assert "not_live_authorized" in plan["safety_labels"]
    assert "profit_claim=none" in plan["safety_labels"]


def _assert_data_refresh_dry_run_shape(dry_run: dict[str, object]) -> None:
    assert {
        "data_refresh_dry_run_version",
        "dry_run_status",
        "generated_at",
        "labels",
        "broker_state_mode",
        "broker_state_observed",
        "paper_submit_authorized",
        "live_authorized",
        "broker_read_authorized",
        "broker_mutation_authorized",
        "network_required",
        "credential_required",
        "ingest_performed",
        "dry_run_only",
        "input_csv_path",
        "input_csv_present",
        "operator_csv_tracked_by_git",
        "generated_runs_tracked_by_git",
        "expected_latest_bar_date_status",
        "expected_latest_bar_date_source",
        "current_accepted_data_as_of",
        "current_accepted_data_path",
        "accepted_refresh_consumed",
        "accepted_refresh_manifest_path",
        "accepted_refresh_manifest_status",
        "accepted_canonical_csv_sha256",
        "accepted_data_source",
        "accepted_data_as_of",
        "current_data_freshness_status",
        "staleness_status",
        "stale_accepted_data_consumed",
        "accepted_data_staleness_state",
        "offline_intake_command_template",
        "next_operator_action",
        "next_agent_action",
        "blocker_status",
    } <= set(dry_run)
    assert dry_run["data_refresh_dry_run_version"] == (
        "assistant_v1.40_data_refresh_dry_run"
    )
    assert dry_run["broker_state_mode"] == "broker_state_not_observed"
    _assert_false_safety_flags(
        dry_run,
        (
            "broker_state_observed",
            "paper_submit_authorized",
            "live_authorized",
            "broker_read_authorized",
            "broker_mutation_authorized",
            "network_required",
            "credential_required",
            "ingest_performed",
            "operator_csv_tracked_by_git",
            "generated_runs_tracked_by_git",
        ),
    )
    assert dry_run["dry_run_only"] is True
    assert dry_run["input_csv_path"] == (
        ".data/operator_inputs/spy_tiingo_adjusted_refresh_latest.csv"
    )
    assert "etf-sma-adjusted-spy-bars-refresh-intake" in str(
        dry_run["offline_intake_command_template"]
    )
    assert "paper_lab_only" in dry_run["labels"]
    assert "not_live_authorized" in dry_run["labels"]
    assert "profit_claim=none" in dry_run["labels"]
    assert "offline_only" in dry_run["labels"]
    assert "broker_state_not_observed" in dry_run["labels"]
    assert "paper_submit_not_authorized" in dry_run["labels"]


def test_etf_sma_daily_paper_lab_mission_control_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify v1.33 Mission Control dashboard, report, JSON, and handoffs."""
    monkeypatch.chdir(tmp_path)
    output_root = tmp_path / "paper_lab_mission_control_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    paths = _assert_expected_artifacts_exist(output_root)
    index_path = paths["index_path"]
    report_path = paths["report_path"]
    mission_path = paths["mission_path"]
    validation_path = paths["validation_path"]
    latest_run_path = paths["latest_run_path"]
    data_freshness_plan_path = paths["data_freshness_plan_path"]
    data_refresh_bridge_path = paths["data_refresh_bridge_path"]
    data_refresh_dry_run_path = paths["data_refresh_dry_run_path"]
    data_refresh_checklist_path = paths["data_refresh_checklist_path"]
    operator_review_path = paths["operator_review_path"]

    mission = _read_json_artifact(mission_path)
    assert mission == payload["mission_control"]
    assert mission["mission_control_version"] == "assistant_v1.33_mission_control"

    executive = mission["executive_summary"]
    _assert_false_safety_flags(
        executive,
        ("paper_submit_authorized", "live_authorized", "live_trading_authorized"),
    )
    assert executive["readiness_score"]
    assert executive["validation_status"] == "passed"
    assert executive["market_signal_preview"] == "buy_preview"
    assert executive["broker_state_mode"] == "broker_state_not_observed"

    latest_run = _read_json_artifact(latest_run_path)
    assert mission["latest_run"] == latest_run
    assert {
        "run_id",
        "generated_at",
        "output_root",
        "open_first",
        "open_first_path",
        "mission_control_path",
        "assistant_report_path",
        "operator_review_path",
        "daily_latest_path",
        "mission_control_json_path",
        "data_freshness_plan_path",
        "data_refresh_bridge_path",
        "data_refresh_dry_run_path",
        "data_refresh_dry_run_status",
        "data_refresh_input_csv_path",
        "data_refresh_input_csv_present",
        "data_refresh_ingest_performed",
        "data_refresh_dry_run_only",
        "accepted_refresh_consumed",
        "accepted_refresh_manifest_status",
        "accepted_data_source",
        "accepted_data_as_of",
        "accepted_canonical_csv_sha256",
        "stale_accepted_data_consumed",
        "accepted_data_staleness_state",
        "data_refresh_operator_checklist_path",
        "current_accepted_data_path",
        "current_data_as_of",
        "current_staleness_days",
        "next_operator_data_action",
        "next_agent_data_action",
        "offline_validation_commands",
        "validation_path",
        "validation_status",
        "readiness_score",
        "preview_decision",
        "market_signal_preview",
        "main_blocker",
        "broker_state_mode",
        "data_freshness_status",
        "staleness_days",
        "next_safest_action",
        "paper_submit_authorized",
        "live_authorized",
        "broker_read_performed",
        "broker_mutation_performed",
        "safety_labels",
        "execution_plan",
        "daily_approval_gate",
        *_EXECUTION_PLAN_COMPACT_FIELDS,
        *_DAILY_APPROVAL_GATE_COMPACT_FIELDS,
    } <= set(latest_run)
    assert latest_run["open_first"] == "index.html"
    assert latest_run["open_first_path"].endswith("index.html")
    assert latest_run["mission_control_path"].endswith("mission_control.json")
    assert latest_run["assistant_report_path"].endswith("assistant_report.md")
    assert latest_run["operator_review_path"].endswith("operator_review.md")
    assert latest_run["daily_latest_path"].endswith(
        "mission_control.json#daily_latest"
    )
    assert latest_run["mission_control_json_path"].endswith("mission_control.json")
    assert latest_run["data_freshness_plan_path"].endswith(
        "data_freshness_plan.json"
    )
    assert latest_run["data_refresh_bridge_path"].endswith(
        "data_refresh_bridge.json"
    )
    assert latest_run["data_refresh_dry_run_path"].endswith(
        "data_refresh_dry_run.json"
    )
    assert latest_run["data_refresh_operator_checklist_path"].endswith(
        "data_refresh_operator_checklist.md"
    )
    assert latest_run["validation_path"].endswith("mission_control_validation.json")
    _assert_path_fields_exist(
        latest_run,
        (
            "open_first_path",
            "mission_control_path",
            "assistant_report_path",
            "operator_review_path",
            "mission_control_json_path",
            "data_freshness_plan_path",
            "data_refresh_bridge_path",
            "data_refresh_dry_run_path",
            "data_refresh_operator_checklist_path",
            "validation_path",
        ),
    )
    assert latest_run["validation_status"] == "passed"
    assert latest_run["readiness_score"]
    assert latest_run["preview_decision"] == "blocked/broker_state_not_observed"
    assert latest_run["market_signal_preview"] == "buy_preview"
    assert latest_run["main_blocker"] == "broker_state_not_observed"
    assert latest_run["broker_state_mode"] == "broker_state_not_observed"
    assert latest_run["data_freshness_status"] == "stale_data_preview_only"
    assert latest_run["data_refresh_dry_run_status"] == "awaiting_operator_csv"
    assert latest_run["data_refresh_input_csv_path"].endswith(
        "spy_tiingo_adjusted_refresh_latest.csv"
    )
    assert latest_run["data_refresh_input_csv_present"] is False
    assert latest_run["data_refresh_ingest_performed"] is False
    assert latest_run["data_refresh_dry_run_only"] is True
    assert latest_run["accepted_refresh_consumed"] is False
    assert latest_run["accepted_refresh_manifest_status"] == "manifest_missing"
    assert latest_run["stale_accepted_data_consumed"] is False
    assert latest_run["accepted_data_staleness_state"] == (
        "accepted_refresh_not_consumed"
    )
    assert isinstance(latest_run["staleness_days"], int)
    assert latest_run["current_accepted_data_path"].endswith(
        "spy_daily_bars_200_bullish.csv"
    )
    assert latest_run["current_data_as_of"] == "2025-07-20"
    assert latest_run["current_staleness_days"] == latest_run["staleness_days"]
    assert (
        "operator-supplied SPY adjusted-close CSV"
        in latest_run["next_operator_data_action"]
    )
    assert "data_refresh_bridge.json" in latest_run["next_agent_data_action"]
    assert any(
        "etf-sma-adjusted-spy-bars-refresh-intake" in command
        for command in latest_run["offline_validation_commands"]
    )
    assert latest_run["next_safest_action"] == (
        "offline_data_refresh_dry_run_operator_input_needed"
    )
    _assert_false_safety_flags(
        latest_run,
        (
            "paper_submit_authorized",
            "live_authorized",
            "broker_read_performed",
            "broker_mutation_performed",
        ),
    )
    assert "paper_lab_only" in latest_run["safety_labels"]

    daily_latest = mission["daily_latest"]
    daily_decision_summary = mission["daily_decision_summary"]
    assert latest_run["daily_decision_summary"] == daily_decision_summary
    assert daily_latest["daily_decision_summary"] == daily_decision_summary
    assert {
        "run_id",
        "generated_at",
        "as_of_date",
        "latest_bar_date",
        "data_freshness_status",
        "data_refresh_status",
        "input_data_path",
        "sma50",
        "sma200",
        "sma_posture",
        "risk_posture",
        "market_signal_preview",
        "broker_state_mode",
        "broker_snapshot_freshness_status",
        "snapshot_validation_status",
        "broker_state_status",
        "spy_position_observed",
        "spy_position_present",
        "spy_position_qty",
        "open_spy_order_count",
        "unexpected_non_spy_position_count",
        "broker_aware_preview_decision",
        "main_blocker",
        "paper_submit_authorized",
        "live_authorized",
        "broker_mutation_performed",
        "exact_next_operator_action",
        "what_changed",
        "daily_approval_gate",
        *_EXECUTION_PLAN_COMPACT_FIELDS,
        *_DAILY_APPROVAL_GATE_COMPACT_FIELDS,
    } <= set(daily_decision_summary)
    assert daily_decision_summary["as_of_date"] == "2025-07-20"
    assert daily_decision_summary["latest_bar_date"] == "2025-07-19"
    assert daily_decision_summary["data_freshness_status"] == (
        "stale_data_preview_only"
    )
    assert daily_decision_summary["data_refresh_status"] == "awaiting_operator_csv"
    assert daily_decision_summary["input_data_path"].endswith(
        "spy_daily_bars_200_bullish.csv"
    )
    assert daily_decision_summary["sma_posture"] == "bullish_risk_on"
    assert daily_decision_summary["risk_posture"] == "risk_on"
    assert daily_decision_summary["market_signal_preview"] == "buy_preview"
    assert daily_decision_summary["broker_state_mode"] == "broker_state_not_observed"
    assert daily_decision_summary["broker_snapshot_freshness_status"] == (
        "not_observed"
    )
    assert daily_decision_summary["snapshot_validation_status"] == "not_observed"
    assert daily_decision_summary["broker_state_status"] == (
        "broker_state_not_observed"
    )
    assert daily_decision_summary["spy_position_observed"] is False
    assert daily_decision_summary["spy_position_present"] is None
    assert daily_decision_summary["spy_position_qty"] is None
    assert daily_decision_summary["open_spy_order_count"] is None
    assert daily_decision_summary["unexpected_non_spy_position_count"] is None
    assert daily_decision_summary["broker_aware_preview_decision"] == (
        "blocked/broker_state_not_observed"
    )
    assert daily_decision_summary["main_blocker"] == "broker_state_not_observed"
    assert daily_decision_summary["paper_submit_authorized"] is False
    assert daily_decision_summary["live_authorized"] is False
    assert daily_decision_summary["broker_mutation_performed"] is False
    assert daily_decision_summary["exact_next_operator_action"] == (
        "run_existing_local_adjusted_data_validation_or_refresh_before_next_cycle"
    )
    assert "No prior packet was found" in daily_decision_summary["what_changed"]
    _assert_execution_plan_surfaces(
        mission,
        expected_status="blocked",
        expected_action="none",
        expected_source_preview_decision="blocked/broker_state_not_observed",
        expected_blocker="broker_state_not_observed",
        expected_requires_approval=False,
        expected_reason="broker_state_not_observed",
    )
    assert {
        "run_id",
        "generated_at",
        "output_root",
        "open_first",
        "open_first_path",
        "latest_run_path",
        "mission_control_path",
        "mission_control_json_path",
        "assistant_report_path",
        "validation_path",
        "validation_status",
        "readiness_score",
        "preview_decision",
        "market_signal_preview",
        "blocker",
        "next_action",
        "next_safest_action",
        "broker_state_mode",
        "broker_read_performed",
        "broker_mutation_performed",
        "paper_submit_authorized",
        "live_authorized",
        "data_as_of",
        "staleness_days",
        "data_freshness_status",
        "preview_only_reason",
        "offline_refresh_needed",
        "next_offline_data_action",
        "operator_data_action_summary",
        "data_freshness_plan_path",
        "data_refresh_bridge_path",
        "data_refresh_dry_run_path",
        "data_refresh_dry_run_status",
        "data_refresh_input_csv_path",
        "data_refresh_input_csv_present",
        "data_refresh_ingest_performed",
        "data_refresh_dry_run_only",
        "accepted_refresh_consumed",
        "accepted_refresh_manifest_status",
        "accepted_data_source",
        "accepted_data_as_of",
        "accepted_canonical_csv_sha256",
        "stale_accepted_data_consumed",
        "accepted_data_staleness_state",
        "data_refresh_operator_checklist_path",
        "current_accepted_data_path",
        "next_operator_data_action",
        "next_agent_data_action",
        "offline_validation_commands",
        "operator_review_path",
        "safety_labels",
        "execution_plan",
        "daily_approval_gate",
        *_EXECUTION_PLAN_COMPACT_FIELDS,
        *_DAILY_APPROVAL_GATE_COMPACT_FIELDS,
    } <= set(daily_latest)
    assert daily_latest["validation_status"] == "passed"
    assert daily_latest["open_first"] == "index.html"
    assert daily_latest["open_first_path"] == latest_run["open_first_path"]
    assert daily_latest["latest_run_path"].endswith("latest_run.json")
    assert daily_latest["preview_decision"] == "blocked/broker_state_not_observed"
    assert daily_latest["market_signal_preview"] == "buy_preview"
    assert daily_latest["blocker"] == "broker_state_not_observed"
    assert daily_latest["broker_state_mode"] == "broker_state_not_observed"
    _assert_false_safety_flags(
        daily_latest,
        (
            "broker_read_performed",
            "broker_mutation_performed",
            "paper_submit_authorized",
            "live_authorized",
        ),
    )
    assert daily_latest["data_as_of"] == "2025-07-20"
    assert isinstance(daily_latest["staleness_days"], int)
    assert daily_latest["data_freshness_status"] == "stale_data_preview_only"
    assert daily_latest["offline_refresh_needed"] is True
    assert "current" not in str(daily_latest["data_freshness_status"])
    assert "external_api" not in str(daily_latest["next_offline_data_action"])
    assert daily_latest["data_freshness_plan_path"].endswith(
        "data_freshness_plan.json"
    )
    assert daily_latest["data_refresh_bridge_path"].endswith(
        "data_refresh_bridge.json"
    )
    assert daily_latest["data_refresh_dry_run_path"].endswith(
        "data_refresh_dry_run.json"
    )
    assert daily_latest["data_refresh_dry_run_status"] == "awaiting_operator_csv"
    assert daily_latest["data_refresh_input_csv_present"] is False
    assert daily_latest["data_refresh_ingest_performed"] is False
    assert daily_latest["data_refresh_dry_run_only"] is True
    assert daily_latest["accepted_refresh_consumed"] is False
    assert daily_latest["accepted_refresh_manifest_status"] == "manifest_missing"
    assert daily_latest["stale_accepted_data_consumed"] is False
    assert daily_latest["accepted_data_staleness_state"] == (
        "accepted_refresh_not_consumed"
    )
    assert daily_latest["data_refresh_operator_checklist_path"].endswith(
        "data_refresh_operator_checklist.md"
    )
    assert daily_latest["current_accepted_data_path"].endswith(
        "spy_daily_bars_200_bullish.csv"
    )
    assert "data_refresh_operator_checklist.md" in daily_latest["next_agent_data_action"]
    assert any(
        "etf-sma-adjusted-spy-bars-refresh-intake" in command
        for command in daily_latest["offline_validation_commands"]
    )
    assert daily_latest["operator_review_path"].endswith("operator_review.md")
    assert daily_latest["next_safest_action"] == latest_run["next_safest_action"]

    data_plan = mission["data_freshness_plan"]
    _assert_data_freshness_plan_shape(data_plan)
    assert data_plan == _read_json_artifact(data_freshness_plan_path)
    assert data_plan["data_freshness_status"] == "stale_data_preview_only"
    assert data_plan["data_as_of"] == "2025-07-20"
    assert data_plan["staleness_days"] == daily_latest["staleness_days"]
    assert data_plan["accepted_data_path"].endswith("spy_daily_bars_200_bullish.csv")
    assert data_plan["accepted_data_basis"] == "close"
    assert data_plan["accepted_row_count"] == 200
    assert data_plan["freshness_blocker"] == "stale_local_data"
    assert data_plan["offline_refresh_needed"] is True
    assert data_plan["safe_to_continue_preview_only"] is True
    assert "preview only" in str(data_plan["preview_only_reason"]).lower()
    serialized_plan = json.dumps(data_plan, sort_keys=True).lower()
    assert "broker_read_required\": false" in serialized_plan
    assert "external_api_required\": false" in serialized_plan
    assert "secrets_required\": false" in serialized_plan
    assert "paid_service_required\": false" in serialized_plan

    data_refresh_bridge = mission["data_refresh_bridge"]
    assert data_refresh_bridge == _read_json_artifact(data_refresh_bridge_path)
    assert data_refresh_bridge["refresh_bridge_version"] == (
        "assistant_v1.38_data_refresh_bridge"
    )
    assert data_refresh_bridge["refresh_bridge_status"] == (
        "stale_data_preview_only_bridge_ready"
    )
    assert data_refresh_bridge["current_data_freshness_status"] == (
        "stale_data_preview_only"
    )
    assert data_refresh_bridge["current_accepted_data_path"].endswith(
        "spy_daily_bars_200_bullish.csv"
    )
    assert data_refresh_bridge["current_accepted_data_basis"] == "close"
    assert data_refresh_bridge["current_accepted_row_count"] == 200
    assert data_refresh_bridge["current_data_as_of"] == "2025-07-20"
    assert data_refresh_bridge["current_staleness_days"] == data_plan["staleness_days"]
    assert data_refresh_bridge["target_symbol"] == "SPY"
    assert data_refresh_bridge["target_data_basis"] == "adjusted_close"
    assert data_refresh_bridge["local_operator_csv_required"] is True
    assert data_refresh_bridge["accepted_input_mode"] == "operator_supplied_local_csv"
    _assert_false_safety_flags(
        data_refresh_bridge,
        (
            "external_api_required",
            "secrets_required",
            "broker_read_required",
            "broker_mutation_required",
            "paid_service_required",
            "paper_submit_required",
            "live_trading_required",
            "paper_submit_authorized",
            "live_authorized",
            "broker_read_performed",
            "broker_mutation_performed",
        ),
    )
    assert data_refresh_bridge["preferred_operator_input_directory"] == (
        ".data/operator_inputs"
    )
    assert data_refresh_bridge["preferred_operator_input_path"].endswith(
        "spy_tiingo_adjusted_refresh_latest.csv"
    )
    assert data_refresh_bridge["canonical_output_path"].endswith(
        "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    assert {
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
    } <= set(data_refresh_bridge["expected_schema"]["required_columns"])
    assert "symbol" in data_refresh_bridge["expected_schema"]["optional_columns"]
    assert "adjusted_close_column_required" in data_refresh_bridge[
        "validation_requirements"
    ]
    assert any(
        "etf-sma-adjusted-spy-bars-refresh-intake" in command
        for command in data_refresh_bridge["offline_validation_commands"]
    )
    assert "external_api_pull" in data_refresh_bridge["forbidden_refresh_paths"]
    assert "operator-supplied SPY adjusted-close CSV" in data_refresh_bridge[
        "next_operator_data_action"
    ]
    assert "data_refresh_operator_checklist.md" in data_refresh_bridge[
        "next_agent_data_action"
    ]
    assert data_refresh_bridge["safe_to_continue_preview_only"] is True
    assert "current" not in data_refresh_bridge["current_data_freshness_status"]
    assert "current" not in data_refresh_bridge["refresh_bridge_status"]
    actionable_refresh_text = " ".join(
        [
            data_refresh_bridge["next_operator_data_action"],
            data_refresh_bridge["next_agent_data_action"],
            *data_refresh_bridge["offline_validation_commands"],
        ]
    ).lower()
    for forbidden_fragment in (
        "external_api",
        "external api",
        "secret",
        "broker_read",
        "broker read",
        "broker_mutation",
        "broker mutation",
        "paper_submit",
        "paper submit",
        "live_trading",
        "live trading",
        "paid_service",
        "paid service",
        "strategy_promotion",
        "strategy promotion",
        "safety_weakening",
        "safety weakening",
    ):
        assert forbidden_fragment not in actionable_refresh_text
    serialized_bridge = json.dumps(data_refresh_bridge, sort_keys=True).lower()
    assert "external_api_required\": false" in serialized_bridge
    assert "secrets_required\": false" in serialized_bridge
    assert "broker_read_required\": false" in serialized_bridge
    assert "broker_mutation_required\": false" in serialized_bridge
    assert "paid_service_required\": false" in serialized_bridge
    assert "paper_submit_required\": false" in serialized_bridge
    assert "live_trading_required\": false" in serialized_bridge

    data_refresh_dry_run = mission["data_refresh_dry_run"]
    assert data_refresh_dry_run == _read_json_artifact(data_refresh_dry_run_path)
    _assert_data_refresh_dry_run_shape(data_refresh_dry_run)
    assert data_refresh_dry_run["dry_run_status"] == "awaiting_operator_csv"
    assert data_refresh_dry_run["safe_success_state"] == "input_csv_missing"
    assert data_refresh_dry_run["input_csv_present"] is False
    assert data_refresh_dry_run["ready_for_offline_intake_validation"] is False
    assert data_refresh_dry_run["expected_latest_bar_date"] is None
    assert data_refresh_dry_run["expected_latest_bar_date_status"] == (
        "operator_required_not_determined_by_dry_run"
    )
    assert data_refresh_dry_run["current_accepted_data_as_of"] == "2025-07-20"
    assert data_refresh_dry_run["current_data_freshness_status"] == (
        "stale_data_preview_only"
    )
    assert data_refresh_dry_run["staleness_status"] == "stale_data_preview_only"
    assert data_refresh_dry_run["stale_accepted_data_consumed"] is False
    assert data_refresh_dry_run["accepted_data_staleness_state"] == (
        "accepted_refresh_not_consumed"
    )
    assert data_refresh_dry_run["offline_intake_command_status"] == (
        "template_only_expected_latest_bar_date_required"
    )
    assert "No" not in json.dumps(data_refresh_dry_run, sort_keys=True)
    assert "no positions" not in json.dumps(data_refresh_dry_run, sort_keys=True).lower()
    assert "no open orders" not in json.dumps(data_refresh_dry_run, sort_keys=True).lower()
    assert "not ingest" in str(data_refresh_dry_run["next_operator_action"]).lower()

    refresh_checklist = data_refresh_checklist_path.read_text(encoding="utf-8")
    assert "Data Refresh Operator Checklist" in refresh_checklist
    assert "Dry-Run Readiness" in refresh_checklist
    assert "Input CSV present: `false`" in refresh_checklist
    assert "Ingest performed: `false`" in refresh_checklist
    assert "Dry-run only: `true`" in refresh_checklist
    assert "Accepted refresh consumed: `false`" in refresh_checklist
    assert "Accepted data staleness state: `accepted_refresh_not_consumed`" in (
        refresh_checklist
    )
    assert "Status: `stale_data_preview_only`" in refresh_checklist
    assert "spy_daily_bars_200_bullish.csv" in refresh_checklist
    assert "Expected symbol: `SPY`" in refresh_checklist
    assert "Expected basis: `adjusted_close`" in refresh_checklist
    assert "date, open, high, low, close, adjusted_close, volume" in refresh_checklist
    assert ".data/operator_inputs/spy_tiingo_adjusted_refresh_latest.csv" in (
        refresh_checklist
    )
    assert "etf-sma-adjusted-spy-bars-refresh-intake" in refresh_checklist
    assert "external_api_required=false" in refresh_checklist
    assert "secrets_required=false" in refresh_checklist
    assert "broker_read_required=false" in refresh_checklist
    assert "broker_mutation_required=false" in refresh_checklist
    assert "paper_submit_required=false" in refresh_checklist
    assert "live_trading_required=false" in refresh_checklist
    assert "paid_service_required=false" in refresh_checklist

    market = mission["market_data_lane"]
    assert market["symbol"] == "SPY"
    assert market["source_mode"] in {"generated_fixture", "accepted_local_file"}
    assert market["basis"] == "close"
    assert market["row_count"] == 200
    assert market["as_of_date"] == "2025-07-20"
    assert market["preview_currency_status"] in {
        "accepted_but_stale",
        "stale_data_preview_only",
        "current",
    }
    assert market["sma50"] is not None
    assert market["sma200"] is not None
    assert market["posture"] == "risk_on"

    broker = mission["broker_state_lane"]
    assert broker["broker_state_mode"] == "broker_state_not_observed"
    _assert_false_safety_flags(
        broker,
        (
            "broker_read_performed",
            "broker_mutation_performed",
            "paper_submit_authorized",
            "live_authorized",
        ),
    )
    assert broker["broker_state_status"] == "broker_state_not_observed"
    assert broker["spy_position_absence_claimed"] is False
    assert broker["spy_open_order_absence_claimed"] is False
    assert "absence remain unknown" in broker["warning"]

    decision = mission["decision_lane"]
    assert decision["preview_decision"] == "blocked/broker_state_not_observed"
    assert decision["market_signal_preview"] == "buy_preview"
    assert decision["blocker_status"] == "broker_state_not_observed"
    assert {
        "paper_lab_only",
        "research_only",
        "not_live_authorized",
        "profit_claim=none",
        "offline_only",
    } <= set(decision["safety_labels"])

    readiness = mission["readiness_score"]
    assert readiness["readiness_score_version"] == (
        "assistant_v1.33_readiness_score"
    )
    assert readiness["status"] == "valid"
    assert readiness["score_valid"] is True
    assert readiness["weights"] == {
        "real_world_attachment": 40,
        "product_readiness": 30,
        "autonomy_middleman_reduction": 20,
        "strategy_quality": 10,
    }
    assert all(gate["passed"] for gate in readiness["safety_gates"].values())

    command_center = mission["agent_command_center"]
    assert command_center["generation_mode"] == "rule_based_no_llm_no_broker"
    _assert_false_safety_flags(
        command_center,
        ("paper_submit_authorized", "live_authorized"),
    )

    dispatcher = mission["rule_based_dispatcher_v0"]
    assert dispatcher["dispatcher_version"] == (
        "assistant_v1.33_rule_dispatcher_v0"
    )
    assert dispatcher["generation_mode"] == "deterministic_rule_based_no_llm_routing"
    assert dispatcher["selected_rule_id"] == "stale_data_present"
    assert dispatcher["selected_route"] == (
        "offline_data_refresh_dry_run_operator_input_needed"
    )
    assert dispatcher["selected_work_order_type"] == (
        "codex_offline_data_refresh_dry_run"
    )
    _assert_no_forbidden_routes(dispatcher)
    assert "broker_read" in dispatcher["forbidden_routes"]
    assert "external_api_data_pull" in dispatcher["forbidden_routes"]
    assert "credential_setup" in dispatcher["forbidden_routes"]
    assert "network_fetch" in dispatcher["forbidden_routes"]
    assert "autonomous_ingest_from_external_service" in dispatcher["forbidden_routes"]

    work_orders_dir = output_root / "work_orders"
    expected_work_orders = {
        "codex_next_prompt.md",
        "codex_next_work_order.json",
        "antigravity_review_prompt.md",
        "antigravity_review_work_order.json",
        "claude_critique_prompt.md",
        "claude_critique_work_order.json",
        "gpt_report_classification_prompt.md",
        "gpt_next_decision_context.json",
    }
    assert expected_work_orders <= {
        path.name for path in work_orders_dir.iterdir() if path.is_file()
    }

    inbox_root = Path(".agent_inbox")
    assert (inbox_root / "codex" / "next_task.md").exists()
    assert (inbox_root / "codex" / "next_work_order.json").exists()
    assert (inbox_root / "antigravity" / "review_task.md").exists()
    assert (inbox_root / "antigravity" / "review_work_order.json").exists()
    assert (inbox_root / "claude" / "critique_task.md").exists()
    assert (inbox_root / "claude" / "critique_work_order.json").exists()
    assert (inbox_root / "gpt" / "report_classification_prompt.md").exists()
    assert (inbox_root / "gpt" / "next_decision_context.json").exists()

    manifest = json.loads((output_root / "manifest.jsonl").read_text(encoding="utf-8"))
    indexed = manifest["indexed_artifacts"]
    assert indexed["mission_control"]["path"].endswith("mission_control.json")
    assert indexed["mission_control_index"]["path"].endswith("index.html")
    assert indexed["assistant_report"]["path"].endswith("assistant_report.md")
    assert indexed["latest_run"]["path"].endswith("latest_run.json")
    assert indexed["data_freshness_plan"]["path"].endswith(
        "data_freshness_plan.json"
    )
    assert indexed["data_refresh_bridge"]["path"].endswith(
        "data_refresh_bridge.json"
    )
    assert indexed["data_refresh_dry_run"]["path"].endswith(
        "data_refresh_dry_run.json"
    )
    assert indexed["data_refresh_operator_checklist"]["path"].endswith(
        "data_refresh_operator_checklist.md"
    )
    assert indexed["operator_review"]["path"].endswith("operator_review.md")
    assert indexed["mission_control_validation"]["path"].endswith(
        "mission_control_validation.json"
    )
    assert indexed["codex_next_work_order"]["path"].endswith(
        "work_orders/codex_next_work_order.json"
    )

    serialized_broker = json.dumps(broker, sort_keys=True).lower()
    assert "no positions" not in serialized_broker
    assert "no open orders" not in serialized_broker

    report = report_path.read_text(encoding="utf-8")
    assert "## Daily Decision Summary" in report
    assert report.index("## Daily Decision Summary") < report.index(
        "## Executive Summary"
    )
    assert "Broker-aware preview decision: `blocked/broker_state_not_observed`" in report
    assert "ExecutionPlan status: `blocked`" in report
    assert "ExecutionPlan action: `none`" in report
    assert "ExecutionPlan submit allowed: `false`" in report
    assert "ExecutionPlan created order payload: `false`" in report
    assert "DailyApprovalGate approval required: `false`" in report
    assert "DailyApprovalGate approval state: `blocked`" in report
    assert "DailyApprovalGate submit allowed: `false`" in report
    assert "DailyApprovalGate paper submit authorized: `false`" in report
    assert "DailyApprovalGate live authorized: `false`" in report
    assert "DailyApprovalGate reason: `execution_plan_blocked`" in report
    assert "DailyApprovalGate blocker: `broker_state_not_observed`" in report
    assert "Exact next operator action: `run_existing_local_adjusted_data_validation_or_refresh_before_next_cycle`" in report
    assert "System status: `offline_mission_control_ready`" in report
    assert "## Open First" in report
    assert "latest_run.json" in report
    assert "Readiness score:" in report
    assert "Validation status: `passed`" in report
    assert "Market signal preview: `buy_preview`" in report
    assert "Broker-state mode: `broker_state_not_observed`" in report
    assert "paper_submit_authorized=false" in report
    assert "live_authorized=false" in report
    assert "Data freshness status: `stale_data_preview_only`" in report
    assert "data_freshness_plan.json" in report
    assert "data_refresh_bridge.json" in report
    assert "data_refresh_dry_run.json" in report
    assert "data_refresh_operator_checklist.md" in report
    assert "Data Refresh Dry Run" in report
    assert "Input CSV present: `false`" in report
    assert "Ingest performed: `false`" in report
    assert "Dry-run only: `true`" in report
    assert "Next operator data action:" in report
    assert "operator-supplied SPY adjusted-close CSV" in report
    assert "operator_review.md" in report

    index_html = index_path.read_text(encoding="utf-8")
    assert "<h2>Daily Decision Summary</h2>" in index_html
    assert index_html.index("<h2>Daily Decision Summary</h2>") < index_html.index(
        "<h2>Open First</h2>"
    )
    assert "Broker-aware preview decision" in index_html
    assert "ExecutionPlan status" in index_html
    assert "ExecutionPlan submit allowed" in index_html
    assert "ExecutionPlan created order payload" in index_html
    assert "DailyApprovalGate approval required" in index_html
    assert "DailyApprovalGate approval state</dt><dd>blocked" in index_html
    assert "DailyApprovalGate submit allowed</dt><dd>false" in index_html
    assert "DailyApprovalGate paper submit authorized</dt><dd>false" in index_html
    assert "DailyApprovalGate live authorized</dt><dd>false" in index_html
    assert "blocked/broker_state_not_observed" in index_html
    assert (
        "run_existing_local_adjusted_data_validation_or_refresh_before_next_cycle"
        in index_html
    )
    assert "mission_control.json" in index_html
    assert "assistant_report.md" in index_html
    assert "latest_run.json" in index_html
    assert "Open First" in index_html
    assert "data_freshness_plan.json" in index_html
    assert "data_refresh_bridge.json" in index_html
    assert "data_refresh_dry_run.json" in index_html
    assert "data_refresh_operator_checklist.md" in index_html
    assert "Data Refresh Dry Run" in index_html
    assert "Input CSV present" in index_html
    assert "Ingest performed" in index_html
    assert "spy_tiingo_adjusted_refresh_latest.csv" in index_html
    assert "operator_review.md" in index_html
    assert "work_orders/" in index_html
    assert "Validation status" in index_html
    assert "passed" in index_html
    assert "stale_data_preview_only" in index_html
    assert "broker_read_required" in index_html

    operator_review = operator_review_path.read_text(encoding="utf-8")
    assert "## Daily Decision Summary" in operator_review
    assert operator_review.index("## Daily Decision Summary") < operator_review.index(
        "## Open First"
    )
    assert (
        "Broker-aware preview decision: `blocked/broker_state_not_observed`"
        in operator_review
    )
    assert "ExecutionPlan status: `blocked`" in operator_review
    assert "ExecutionPlan action: `none`" in operator_review
    assert "ExecutionPlan submit allowed: `false`" in operator_review
    assert "ExecutionPlan created order payload: `false`" in operator_review
    assert "DailyApprovalGate approval required: `false`" in operator_review
    assert "DailyApprovalGate approval state: `blocked`" in operator_review
    assert "DailyApprovalGate submit allowed: `false`" in operator_review
    assert "DailyApprovalGate paper submit authorized: `false`" in operator_review
    assert "DailyApprovalGate live authorized: `false`" in operator_review
    assert "DailyApprovalGate reason: `execution_plan_blocked`" in operator_review
    assert "DailyApprovalGate blocker: `broker_state_not_observed`" in operator_review
    assert (
        "Exact next operator action: `run_existing_local_adjusted_data_validation_or_refresh_before_next_cycle`"
        in operator_review
    )
    assert "## Executive Summary" in operator_review
    assert "## Open First" in operator_review
    assert "Latest-run summary:" in operator_review
    assert "System status: `offline_mission_control_ready`" in operator_review
    assert "Validation status: `passed`" in operator_review
    assert "Readiness score:" in operator_review
    assert "Current preview decision: `blocked/broker_state_not_observed`" in operator_review
    assert "Market signal preview: `buy_preview`" in operator_review
    assert "Main blocker: `broker_state_not_observed`" in operator_review
    assert "Broker-state mode: `broker_state_not_observed`" in operator_review
    assert "Data freshness status: `stale_data_preview_only`" in operator_review
    assert "paper_submit_authorized=false" in operator_review
    assert "live_authorized=false" in operator_review
    assert "broker_read_performed=false" in operator_review
    assert "broker_mutation_performed=false" in operator_review
    assert "What The Operator Should Not Do" in operator_review
    assert "What Agents Should Do Next" in operator_review
    assert "data_freshness_plan.json" in operator_review
    assert "data_refresh_bridge.json" in operator_review
    assert "data_refresh_dry_run.json" in operator_review
    assert "data_refresh_operator_checklist.md" in operator_review
    assert "Dry-run status: `awaiting_operator_csv`" in operator_review
    assert "Local refresh CSV present: `false`" in operator_review
    assert "Ingest performed: `false`" in operator_review
    assert "Dry-run only: `true`" in operator_review
    assert "operator-supplied SPY adjusted-close CSV" in operator_review
    assert "etf-sma-adjusted-spy-bars-refresh-intake" in operator_review
    assert "latest_run.json" in operator_review
    assert "operator_review.md" in operator_review

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    assert validation["validation_status"] == "passed"
    assert validation["missing_artifacts"] == []
    assert validation["schema_errors"] == []
    assert validation["safety_errors"] == []
    assert validation["next_repair_action"] == "none_contract_valid"
    _assert_false_safety_flags(
        validation,
        ("paper_submit_authorized", "live_authorized"),
    )

    direct_validation = validate_mission_control_contract(
        output_root,
        write_artifact=False,
    )
    assert direct_validation["validation_status"] == "passed"


def test_data_refresh_dry_run_detects_present_csv_without_ingesting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    operator_input = tmp_path / ".data" / "operator_inputs"
    operator_input.mkdir(parents=True)
    (operator_input / "spy_tiingo_adjusted_refresh_latest.csv").write_text(
        "date,open,high,low,close,adjusted_close,volume\n",
        encoding="utf-8",
        newline="\n",
    )

    output_root = tmp_path / "paper_lab_present_csv_out"
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    dry_run = payload["mission_control"]["data_refresh_dry_run"]
    _assert_data_refresh_dry_run_shape(dry_run)
    assert dry_run["input_csv_present"] is True
    assert dry_run["dry_run_status"] == "ready_for_offline_intake_validation"
    assert dry_run["ready_for_offline_intake_validation"] is True
    assert dry_run["accepted_refresh_consumed"] is False
    assert dry_run["stale_accepted_data_consumed"] is False
    assert dry_run["accepted_data_staleness_state"] == "accepted_refresh_not_consumed"
    assert dry_run["ingest_performed"] is False
    assert dry_run["dry_run_only"] is True
    assert dry_run["safe_success_state"] == "ready_for_offline_intake_validation"
    assert payload["mission_control"]["rule_based_dispatcher_v0"]["selected_route"] == (
        "offline_data_refresh_ready_for_intake_validation"
    )
    assert validate_mission_control_contract(output_root, write_artifact=False)[
        "validation_status"
    ] == "passed"


def test_daily_bar_freshness_policy_treats_latest_completed_session_as_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    latest_bar_date = "2026-06-17"
    canonical_csv = (
        tmp_path
        / "runs"
        / "operator_input"
        / "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    canonical_sha256 = _write_shifted_spy_fixture(
        canonical_csv,
        latest_bar_date=latest_bar_date,
    )
    _write_accepted_refresh_manifest(
        tmp_path,
        canonical_sha256=canonical_sha256,
        latest_bar_date=latest_bar_date,
    )

    output_root = tmp_path / "paper_lab_latest_completed_session_out"
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=canonical_csv,
            as_of_date=latest_bar_date,
            symbol="SPY",
            run_date="2026-06-18",
        )
    )

    mission = payload["mission_control"]
    latest_run = _read_json_artifact(output_root / "latest_run.json")
    data_plan = _read_json_artifact(output_root / "data_freshness_plan.json")
    bridge = _read_json_artifact(output_root / "data_refresh_bridge.json")
    dry_run = _read_json_artifact(output_root / "data_refresh_dry_run.json")
    dispatcher = mission["rule_based_dispatcher_v0"]

    assert mission["latest_run"] == latest_run
    assert mission["data_freshness_plan"] == data_plan
    assert mission["data_refresh_bridge"] == bridge
    assert mission["data_refresh_dry_run"] == dry_run

    assert data_plan["data_freshness_status"] == "current_for_daily_bar_lab"
    assert data_plan["data_as_of"] == latest_bar_date
    assert data_plan["run_date"] == "2026-06-18"
    assert data_plan["latest_completed_session_date"] == latest_bar_date
    assert data_plan["staleness_days"] == 1
    assert data_plan["freshness_blocker"] == "none"
    assert data_plan["offline_refresh_needed"] is False
    assert data_plan["next_offline_data_action"] == (
        "continue_daily_operator_review_preview_only"
    )

    assert bridge["current_data_freshness_status"] == "current_for_daily_bar_lab"
    assert bridge["current_data_as_of"] == latest_bar_date
    assert bridge["run_date"] == "2026-06-18"
    assert bridge["current_staleness_days"] == 1
    assert bridge["accepted_refresh_consumed"] is True
    assert bridge["accepted_refresh_manifest_status"] == "accepted_refresh_consumed"
    assert bridge["accepted_data_as_of"] == latest_bar_date
    assert bridge["accepted_canonical_csv_sha256"] == canonical_sha256
    assert bridge["local_operator_csv_required"] is False
    assert "No new CSV refresh is requested" in bridge["next_operator_data_action"]

    assert dry_run["current_data_freshness_status"] == "current_for_daily_bar_lab"
    assert dry_run["current_staleness_days"] == 1
    assert dry_run["accepted_refresh_consumed"] is True
    assert dry_run["dry_run_status"] == "accepted_refresh_consumed_preview_only"
    assert dry_run["stale_accepted_data_consumed"] is False
    assert dry_run["accepted_data_staleness_state"] == (
        "accepted_refresh_consumed_not_stale"
    )
    assert dry_run["safe_success_state"] == "accepted_refresh_consumed"
    assert dry_run["paper_submit_authorized"] is False

    for summary in (latest_run, mission["daily_latest"]):
        assert summary["accepted_refresh_consumed"] is True
        assert summary["accepted_refresh_manifest_status"] == (
            "accepted_refresh_consumed"
        )
        assert summary["accepted_data_as_of"] == latest_bar_date
        assert summary["data_freshness_status"] == "current_for_daily_bar_lab"
        assert summary["staleness_days"] == 1
        assert summary["market_signal_preview"] == "buy_preview"
        assert summary["preview_decision"] == "blocked/broker_state_not_observed"
        assert summary["broker_state_mode"] == "broker_state_not_observed"
        assert summary["paper_submit_authorized"] is False
        assert summary["stale_accepted_data_consumed"] is False
        assert summary["accepted_data_staleness_state"] == (
            "accepted_refresh_consumed_not_stale"
        )

    assert latest_run["current_staleness_days"] == 1
    assert dispatcher["selected_rule_id"] == (
        "broker_state_not_observed_and_read_not_authorized"
    )
    assert dispatcher["selected_route"] == "offline_dashboard_data_decision_improvement"
    assert dispatcher["selected_route"] not in {
        "offline_accepted_data_staleness_resolution",
        "offline_data_refresh_dry_run_operator_input_needed",
        "offline_accepted_data_refresh_dry_run_checklist_improvement",
    }
    assert dispatcher["paper_submit_authorized"] is False
    assert dispatcher["broker_read_authorized"] is False
    _assert_no_forbidden_routes(dispatcher)

    required_labels = {
        "paper_lab_only",
        "signal_evaluation_only",
        "research_only",
        "not_live_authorized",
        "profit_claim=none",
        "offline_only",
        "broker_state_not_observed",
        "paper_submit_not_authorized",
    }
    for labels in (
        mission["daily_latest"]["safety_labels"],
        latest_run["safety_labels"],
        data_plan["safety_labels"],
        bridge["safety_labels"],
        dry_run["labels"],
    ):
        assert required_labels <= set(labels)

    assert "current_for_daily_bar_lab" in (
        output_root / "assistant_report.md"
    ).read_text(encoding="utf-8")
    assert "current_for_daily_bar_lab" in (
        output_root / "operator_review.md"
    ).read_text(encoding="utf-8")
    assert "current_for_daily_bar_lab" in (
        output_root / "index.html"
    ).read_text(encoding="utf-8")
    assert validate_mission_control_contract(output_root, write_artifact=False)[
        "validation_status"
    ] == "passed"


def test_accepted_m446_refresh_is_current_on_juneteenth_weekend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    latest_bar_date = "2026-06-18"
    canonical_csv = (
        tmp_path
        / "runs"
        / "operator_input"
        / "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    canonical_sha256 = _write_shifted_spy_fixture(
        canonical_csv,
        latest_bar_date=latest_bar_date,
    )
    _write_accepted_refresh_manifest(
        tmp_path,
        canonical_sha256=canonical_sha256,
        latest_bar_date=latest_bar_date,
    )

    output_root = tmp_path / "paper_lab_m446_juneteenth_weekend_out"
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=canonical_csv,
            as_of_date=latest_bar_date,
            symbol="SPY",
            run_date="2026-06-20",
        )
    )

    mission = payload["mission_control"]
    latest_run = _read_json_artifact(output_root / "latest_run.json")
    data_plan = _read_json_artifact(output_root / "data_freshness_plan.json")
    bridge = _read_json_artifact(output_root / "data_refresh_bridge.json")
    dry_run = _read_json_artifact(output_root / "data_refresh_dry_run.json")
    dispatcher = mission["rule_based_dispatcher_v0"]

    assert data_plan["data_freshness_status"] == "current_for_daily_bar_lab"
    assert data_plan["data_as_of"] == latest_bar_date
    assert data_plan["run_date"] == "2026-06-20"
    assert data_plan["latest_completed_session_date"] == latest_bar_date
    assert data_plan["staleness_days"] == 2
    assert data_plan["freshness_blocker"] == "none"
    assert data_plan["offline_refresh_needed"] is False

    assert bridge["current_data_freshness_status"] == "current_for_daily_bar_lab"
    assert bridge["current_data_as_of"] == latest_bar_date
    assert bridge["current_staleness_days"] == 2
    assert bridge["accepted_refresh_consumed"] is True
    assert bridge["accepted_refresh_manifest_status"] == "accepted_refresh_consumed"
    assert bridge["accepted_refresh_expected_latest_bar_date"] == latest_bar_date
    assert bridge["accepted_refresh_latest_bar_date"] == latest_bar_date
    assert bridge["accepted_data_as_of"] == latest_bar_date
    assert bridge["accepted_canonical_csv_sha256"] == canonical_sha256
    assert bridge["local_operator_csv_required"] is False

    assert dry_run["current_data_freshness_status"] == "current_for_daily_bar_lab"
    assert dry_run["current_staleness_days"] == 2
    assert dry_run["accepted_refresh_consumed"] is True
    assert dry_run["dry_run_status"] == "accepted_refresh_consumed_preview_only"
    assert dry_run["dry_run_status"] != "accepted_refresh_consumed_stale_preview_only"
    assert dry_run["stale_accepted_data_consumed"] is False
    assert dry_run["accepted_data_staleness_state"] == (
        "accepted_refresh_consumed_not_stale"
    )
    assert dry_run["blocker_status"] == "offline_preview_only_broker_state_not_observed"
    assert dry_run["paper_submit_authorized"] is False
    assert dry_run["live_authorized"] is False
    assert dry_run["broker_read_performed"] is False
    assert dry_run["broker_mutation_performed"] is False

    forbidden_refresh_action = (
        "run_existing_local_adjusted_data_validation_or_refresh_before_next_cycle"
    )
    expected_broker_action = (
        "produce_fresh_explicitly_authorized_read_only_paper_broker_snapshot_"
        "for_spy_daily_lab"
    )
    for summary in (latest_run, mission["daily_latest"]):
        assert summary["accepted_refresh_consumed"] is True
        assert summary["accepted_data_as_of"] == latest_bar_date
        assert summary["data_freshness_status"] == "current_for_daily_bar_lab"
        assert summary["data_refresh_dry_run_status"] == (
            "accepted_refresh_consumed_preview_only"
        )
        assert summary["data_refresh_dry_run_status"] != (
            "accepted_refresh_consumed_stale_preview_only"
        )
        assert summary["stale_accepted_data_consumed"] is False
        assert summary["accepted_data_staleness_state"] == (
            "accepted_refresh_consumed_not_stale"
        )
        assert summary["market_signal_preview"] == "buy_preview"
        assert summary["preview_decision"] == "blocked/broker_state_not_observed"
        assert summary["broker_state_mode"] == "broker_state_not_observed"
        assert summary["paper_submit_authorized"] is False
        assert summary["live_authorized"] is False
        assert summary["broker_read_performed"] is False
        assert summary["broker_mutation_performed"] is False
        assert summary["exact_next_operator_action"] == expected_broker_action
        assert summary["exact_next_operator_action"] != forbidden_refresh_action

    assert dispatcher["selected_rule_id"] == (
        "broker_state_not_observed_and_read_not_authorized"
    )
    assert dispatcher["selected_route"] == "offline_dashboard_data_decision_improvement"
    assert dispatcher["selected_route"] not in {
        "offline_accepted_data_staleness_resolution",
        "offline_data_refresh_dry_run_operator_input_needed",
        "offline_accepted_data_refresh_dry_run_checklist_improvement",
    }
    assert dispatcher["paper_submit_authorized"] is False
    assert dispatcher["live_authorized"] is False
    assert dispatcher["broker_read_authorized"] is False
    _assert_no_forbidden_routes(dispatcher)

    operator_review = (output_root / "operator_review.md").read_text(encoding="utf-8")
    assert "Dry-run status: `accepted_refresh_consumed_preview_only`" in operator_review
    assert "accepted_refresh_consumed_stale_preview_only" not in operator_review
    assert forbidden_refresh_action not in operator_review
    assert validate_mission_control_contract(output_root, write_artifact=False)[
        "validation_status"
    ] == "passed"


def test_daily_bar_freshness_policy_keeps_same_day_data_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    bars_csv = tmp_path / "runs" / "operator_input" / "same_day_spy.csv"
    _write_shifted_spy_fixture(bars_csv, latest_bar_date="2026-06-17")

    output_root = tmp_path / "paper_lab_same_day_current_out"
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2026-06-17",
            symbol="SPY",
            run_date="2026-06-17",
        )
    )

    mission = payload["mission_control"]
    data_plan = mission["data_freshness_plan"]
    bridge = mission["data_refresh_bridge"]
    dry_run = mission["data_refresh_dry_run"]

    assert data_plan["data_freshness_status"] == "current_for_daily_bar_lab"
    assert data_plan["staleness_days"] == 0
    assert data_plan["offline_refresh_needed"] is False
    assert bridge["current_data_freshness_status"] == "current_for_daily_bar_lab"
    assert bridge["local_operator_csv_required"] is False
    assert dry_run["dry_run_status"] == "offline_intake_not_required_current_data"
    assert dry_run["safe_success_state"] == "current_data_no_offline_intake_required"
    assert mission["rule_based_dispatcher_v0"]["selected_route"] == (
        "offline_dashboard_data_decision_improvement"
    )


def test_daily_bar_freshness_policy_preserves_stale_refresh_routing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    bars_csv = tmp_path / "runs" / "operator_input" / "stale_spy.csv"
    _write_shifted_spy_fixture(bars_csv, latest_bar_date="2026-06-15")

    output_root = tmp_path / "paper_lab_stale_daily_bar_out"
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2026-06-15",
            symbol="SPY",
            run_date="2026-06-18",
        )
    )

    mission = payload["mission_control"]
    data_plan = mission["data_freshness_plan"]
    bridge = mission["data_refresh_bridge"]
    dry_run = mission["data_refresh_dry_run"]
    dispatcher = mission["rule_based_dispatcher_v0"]

    assert data_plan["data_freshness_status"] == "stale_data_preview_only"
    assert data_plan["staleness_days"] == 3
    assert data_plan["freshness_blocker"] == "stale_local_data"
    assert data_plan["offline_refresh_needed"] is True
    assert bridge["current_data_freshness_status"] == "stale_data_preview_only"
    assert bridge["local_operator_csv_required"] is True
    assert dry_run["dry_run_status"] == "awaiting_operator_csv"
    assert dispatcher["selected_rule_id"] == "stale_data_present"
    assert dispatcher["selected_route"] == (
        "offline_data_refresh_dry_run_operator_input_needed"
    )


def test_daily_bar_freshness_policy_blocks_future_dated_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    bars_csv = tmp_path / "runs" / "operator_input" / "future_spy.csv"
    _write_shifted_spy_fixture(bars_csv, latest_bar_date="2026-06-19")

    output_root = tmp_path / "paper_lab_future_dated_daily_bar_out"
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2026-06-19",
            symbol="SPY",
            run_date="2026-06-18",
        )
    )

    mission = payload["mission_control"]
    data_plan = mission["data_freshness_plan"]
    bridge = mission["data_refresh_bridge"]
    dispatcher = mission["rule_based_dispatcher_v0"]

    assert data_plan["data_freshness_status"] == "blocked_future_dated_local_data"
    assert data_plan["staleness_days"] == -1
    assert data_plan["freshness_blocker"] == "future_dated_local_data"
    assert data_plan["offline_refresh_needed"] is True
    assert data_plan["safe_to_continue_preview_only"] is False
    assert bridge["current_data_freshness_status"] == (
        "blocked_future_dated_local_data"
    )
    assert bridge["local_operator_csv_required"] is True
    assert dispatcher["selected_rule_id"] == "stale_data_present"
    assert dispatcher["selected_route"] == (
        "offline_data_refresh_dry_run_operator_input_needed"
    )
    assert validate_mission_control_contract(output_root, write_artifact=False)[
        "validation_status"
    ] == "passed"


def test_mission_control_routes_past_consumed_refresh_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    operator_input = tmp_path / ".data" / "operator_inputs"
    operator_input.mkdir(parents=True)
    (operator_input / "spy_tiingo_adjusted_refresh_latest.csv").write_text(
        "date,open,high,low,close,adjusted_close,volume\n",
        encoding="utf-8",
        newline="\n",
    )

    canonical_csv = (
        tmp_path
        / "runs"
        / "operator_input"
        / "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    canonical_csv.parent.mkdir(parents=True)
    canonical_csv.write_text(
        (FIXTURES_DIR / "spy_daily_bars_200_bullish.csv").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
        newline="\n",
    )
    canonical_sha256 = hashlib.sha256(canonical_csv.read_bytes()).hexdigest()
    manifest_path = (
        tmp_path / "runs" / "paper_lab" / "m446_adjusted_spy_bars_refresh_manifest.jsonl"
    )
    manifest_path.parent.mkdir(parents=True)
    manifest_record = {
        "refresh_state": "accepted_current_adjusted_bars",
        "expected_latest_bar_date": "2025-07-20",
        "latest_local_bar_date": "2025-07-20",
        "operator_input_sha256": "operator-fixture-sha",
        "refreshed_canonical_csv_path": (
            "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
        ),
        "refreshed_canonical_csv_sha256": canonical_sha256,
        "refresh_blockers": [],
        "refresh_warnings": [],
    }
    manifest_path.write_text(
        json.dumps(manifest_record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    output_root = tmp_path / "paper_lab_consumed_refresh_out"
    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=canonical_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    mission = payload["mission_control"]
    bridge = mission["data_refresh_bridge"]
    dry_run = mission["data_refresh_dry_run"]
    dispatcher = mission["rule_based_dispatcher_v0"]

    assert bridge["accepted_refresh_consumed"] is True
    assert bridge["accepted_refresh_manifest_status"] == "accepted_refresh_consumed"
    assert bridge["accepted_data_source"].endswith(
        "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    assert bridge["accepted_data_as_of"] == "2025-07-20"
    assert bridge["accepted_canonical_csv_sha256"] == canonical_sha256
    assert bridge["accepted_refresh_consumption_checks"] == {
        "manifest_state_accepted": True,
        "canonical_path_matches_selected_data": True,
        "canonical_sha256_matches_selected_data": True,
        "latest_bar_date_matches_selected_as_of": True,
    }

    _assert_data_refresh_dry_run_shape(dry_run)
    assert dry_run["accepted_refresh_consumed"] is True
    assert dry_run["accepted_refresh_manifest_status"] == "accepted_refresh_consumed"
    assert dry_run["dry_run_status"] == "accepted_refresh_consumed_stale_preview_only"
    assert dry_run["ingest_performed"] is False
    assert dry_run["ready_for_offline_intake_validation"] is False
    assert dry_run["safe_success_state"] == "stale_accepted_data_consumed"
    assert dry_run["blocker_status"] == (
        "stale_accepted_data_consumed_offline_preview_only_"
        "broker_state_not_observed"
    )
    assert dry_run["accepted_data_as_of"] == "2025-07-20"
    assert dry_run["accepted_canonical_csv_sha256"] == canonical_sha256
    assert dry_run["stale_accepted_data_consumed"] is True
    assert dry_run["accepted_data_staleness_state"] == "stale_accepted_data_consumed"
    assert "newer offline adjusted-data CSV" in dry_run["next_operator_action"]
    assert "order submission remains unauthorized" in dry_run["next_operator_action"]
    assert "completed offline intake consumption" in dry_run["next_agent_action"]

    latest_run = _read_json_artifact(output_root / "latest_run.json")
    daily_latest = mission["daily_latest"]
    for summary in (latest_run, daily_latest):
        assert summary["accepted_refresh_consumed"] is True
        assert summary["accepted_refresh_manifest_status"] == (
            "accepted_refresh_consumed"
        )
        assert summary["accepted_data_source"].endswith(
            "m446_spy_daily_tiingo_adjusted_canonical.csv"
        )
        assert summary["accepted_data_as_of"] == "2025-07-20"
        assert summary["accepted_canonical_csv_sha256"] == canonical_sha256
        assert summary["stale_accepted_data_consumed"] is True
        assert summary["accepted_data_staleness_state"] == (
            "stale_accepted_data_consumed"
        )
        assert summary["preview_decision"] == "blocked/broker_state_not_observed"
        assert summary["broker_state_mode"] == "broker_state_not_observed"
        assert summary["paper_submit_authorized"] is False

    assert dispatcher["selected_rule_id"] == "stale_accepted_data_consumed"
    assert dispatcher["selected_route"] == "offline_accepted_data_staleness_resolution"
    assert dispatcher["selected_work_order_type"] == (
        "codex_offline_stale_accepted_data_followup"
    )
    assert dispatcher["selected_route"] not in {
        "offline_data_refresh_ready_for_intake_validation",
        "offline_accepted_data_refresh_dry_run_checklist_improvement",
    }
    assert dispatcher["broker_read_authorized"] is False
    assert dispatcher["paper_submit_authorized"] is False
    _assert_no_forbidden_routes(dispatcher)

    codex_work_order = _read_json_artifact(
        output_root / "work_orders" / "codex_next_work_order.json"
    )
    assert codex_work_order["selected_rule_id"] == "stale_accepted_data_consumed"
    assert codex_work_order["selected_route"] == (
        "offline_accepted_data_staleness_resolution"
    )
    assert codex_work_order["work_order_type"] == (
        "codex_offline_stale_accepted_data_followup"
    )

    surfaces = [
        output_root / "mission_control.json",
        output_root / "latest_run.json",
        output_root / "assistant_report.md",
        output_root / "operator_review.md",
        output_root / "index.html",
        output_root / "work_orders" / "codex_next_prompt.md",
        output_root / "work_orders" / "codex_next_work_order.json",
    ]
    for surface in surfaces:
        text = surface.read_text(encoding="utf-8")
        assert (
            "stale_accepted_data_consumed" in text
            or "stale accepted data consumed" in text.lower()
        ), surface
        assert "offline_accepted_data_refresh_dry_run_checklist_improvement" not in (
            text
        ), surface
        assert "codex_offline_data_refresh_dry_run" not in text, surface

    evidence_surfaces = [
        output_root / "mission_control.json",
        output_root / "latest_run.json",
        output_root / "assistant_report.md",
        output_root / "operator_review.md",
        output_root / "index.html",
    ]
    for surface in evidence_surfaces:
        text = surface.read_text(encoding="utf-8")
        assert (
            "accepted_refresh_consumed" in text
            or "accepted refresh consumed" in text.lower()
        ), surface

    report = (output_root / "assistant_report.md").read_text(encoding="utf-8")
    assert "accepted_refresh_consumed: `true`" in report
    assert "stale_accepted_data_consumed: `true`" in report
    assert "Accepted data staleness state: `stale_accepted_data_consumed`" in report
    assert "Broker state mode: `broker_state_not_observed`" in report

    operator_review = (output_root / "operator_review.md").read_text(
        encoding="utf-8"
    )
    assert "Accepted refresh consumed: `true`" in operator_review
    assert "Stale accepted data consumed: `true`" in operator_review
    assert "paper_submit_authorized=false" in operator_review

    index_html = (output_root / "index.html").read_text(encoding="utf-8")
    assert "accepted_refresh_consumed</dt><dd>true" in index_html
    assert "Stale accepted data consumed</dt><dd>true" in index_html
    assert "broker_state_not_observed" in index_html

    assert validate_mission_control_contract(output_root, write_artifact=False)[
        "validation_status"
    ] == "passed"


def test_mission_control_dispatcher_selects_expected_safe_routes() -> None:
    cases = [
        (
            "validation_failure",
            {"validation_status": "failed"},
            "mission_control_validation_failed",
            "codex_schema_safety_repair",
            "codex_schema_safety_repair",
        ),
        (
            "product_artifact_missing",
            {"missing_artifact": "operator_review_md"},
            "mission_control_product_artifact_missing_or_weak",
            "mission_control_product_repair_to_codex",
            "codex_product_repair",
        ),
        (
            "work_order_missing",
            {"missing_artifact": "codex_next_prompt"},
            "work_orders_missing",
            "middleman_reduction_repair_to_codex",
            "codex_work_order_repair",
        ),
        (
            "offline_validation_command_missing",
            {"staleness_days": 5, "offline_validation_commands": []},
            "offline_validation_command_missing",
            "offline_data_intake_validation_planning",
            "codex_offline_data_intake_validation_planning",
        ),
        (
            "stale_data_refresh_bridge",
            {"staleness_days": 5},
            "stale_data_present",
            "offline_data_refresh_dry_run_operator_input_needed",
            "codex_offline_data_refresh_dry_run",
        ),
        (
            "csv_present_ready_for_intake_validation",
            {"staleness_days": 5, "input_csv_present": True},
            "offline_refresh_csv_present_not_ingested",
            "offline_data_refresh_ready_for_intake_validation",
            "codex_offline_data_refresh_ready_for_intake_validation",
        ),
        (
            "csv_present_consumed_refresh_routes_past_intake",
            {
                "staleness_days": 5,
                "input_csv_present": True,
                "accepted_refresh_consumed": True,
            },
            "stale_accepted_data_consumed",
            "offline_accepted_data_staleness_resolution",
            "codex_offline_stale_accepted_data_followup",
        ),
        (
            "broker_not_observed",
            {"staleness_days": 0},
            "broker_state_not_observed_and_read_not_authorized",
            "offline_dashboard_data_decision_improvement",
            "codex_next_work_order",
        ),
        (
            "valid_no_blocker",
            {
                "staleness_days": 0,
                "broker_read_performed": True,
                "blocker_status": "none",
            },
            "product_loop_valid_no_blocker",
            "next_mission_control_slice",
            "codex_next_mission_control_slice",
        ),
    ]

    for (
        case_name,
        dispatcher_kwargs,
        expected_rule_id,
        expected_route,
        expected_work_order_type,
    ) in cases:
        dispatcher = _dispatcher_result(**dispatcher_kwargs)

        assert dispatcher["selected_rule_id"] == expected_rule_id, case_name
        assert dispatcher["selected_route"] == expected_route, case_name
        assert (
            dispatcher["selected_work_order_type"] == expected_work_order_type
        ), case_name
        assert set(dispatcher["forbidden_routes"]) >= {
            "broker_read",
            "paper_submit",
            "broker_mutation",
            "live_trading",
            "external_api_data_pull",
            "external_api_pull",
            "secrets_setup",
            "credential_setup",
            "network_fetch",
            "autonomous_ingest_from_external_service",
            "paid_service_setup",
            "strategy_promotion",
            "safety_weakening",
        }, case_name
        _assert_no_forbidden_routes(dispatcher)


def test_mission_control_work_order_prompts_are_paste_ready(tmp_path: Path) -> None:
    output_root = _generate_mission_control_output(
        tmp_path,
        "paper_lab_prompt_contract_out",
    )
    prompt_paths = [
        output_root / "work_orders" / "codex_next_prompt.md",
        output_root / "work_orders" / "antigravity_review_prompt.md",
        output_root / "work_orders" / "claude_critique_prompt.md",
        output_root / "work_orders" / "gpt_report_classification_prompt.md",
    ]

    for prompt_path in prompt_paths:
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "Project path:" in prompt
        assert (
            "Assistant v1.40 - Offline Data Refresh Intake Dry-Run UX"
            in prompt
        )
        assert "Goal:" in prompt
        assert "Start-here artifacts:" in prompt
        assert "Start with latest-run summary:" in prompt
        assert "latest_run.json" in prompt
        assert "Mission Control JSON" in prompt
        assert "Operator review flow inputs:" in prompt
        assert "daily_latest" in prompt
        assert "mission_control.json" in prompt
        assert "mission_control_validation.json" in prompt
        assert "data_freshness_plan.json" in prompt
        assert "data_refresh_bridge.json" in prompt
        assert "data_refresh_dry_run.json" in prompt
        assert "data_refresh_operator_checklist.md" in prompt
        assert "operator_review.md" in prompt
        assert "Forbidden behavior:" in prompt
        assert "perform broker reads" in prompt
        assert "Do not authorize paper submit." in prompt
        assert "Required tests/review checks:" in prompt
        assert (
            "python -m pytest tests/unit/test_etf_sma_daily_paper_lab.py -q"
            in prompt
        )
        assert "Expected report format:" in prompt
        assert "Classification recommendation" in prompt
        assert "Safety assessment" in prompt
        assert (
            "Normal pytest remains offline, deterministic, credential-free, "
            "broker-free, and network-free."
        ) in prompt
        assert "Do not stage generated or local handoff artifacts:" in prompt
        assert "`runs/`" in prompt
        assert "`.agent_inbox/`" in prompt
        assert "`docs/reviews/`" in prompt
        assert "`.data/`" in prompt
        assert "`operator-supplied CSVs`" in prompt

    codex_prompt = prompt_paths[0].read_text(encoding="utf-8")
    assert "Allowed files:" in codex_prompt
    assert "src/algotrader/execution/etf_sma_daily_paper_lab.py" in codex_prompt
    for review_prompt_path in prompt_paths[1:]:
        assert "Review scope:" in review_prompt_path.read_text(encoding="utf-8")


def test_mission_control_contract_validator_fails_missing_required_artifacts(
    tmp_path: Path,
) -> None:
    cases = (
        (
            "codex_prompt",
            "work_orders/codex_next_prompt.md",
            "work_orders/codex_next_prompt.md",
            "regenerate_missing_artifact:work_orders/codex_next_prompt.md",
        ),
        (
            "latest_run",
            "latest_run.json",
            "latest_run.json",
            "regenerate_missing_artifact:latest_run.json",
        ),
        (
            "refresh_bridge",
            "data_refresh_bridge.json",
            "data_refresh_bridge.json",
            "regenerate_missing_artifact:data_refresh_bridge.json",
        ),
        (
            "refresh_dry_run",
            "data_refresh_dry_run.json",
            "data_refresh_dry_run.json",
            "regenerate_missing_artifact:data_refresh_dry_run.json",
        ),
        (
            "refresh_checklist",
            "data_refresh_operator_checklist.md",
            "data_refresh_operator_checklist.md",
            "regenerate_missing_artifact:data_refresh_operator_checklist.md",
        ),
    )

    for case_name, relative_path, expected_missing, expected_repair_action in cases:
        output_root = _generate_mission_control_output(
            tmp_path,
            f"paper_lab_missing_required_artifact_{case_name}_out",
        )
        (output_root / relative_path).unlink()

        validation = validate_mission_control_contract(
            output_root,
            write_artifact=False,
        )

        assert validation["validation_status"] == "failed", case_name
        assert expected_missing in validation["missing_artifacts"], case_name
        assert validation["next_repair_action"] == expected_repair_action, case_name
        _assert_false_safety_flags(
            validation,
            ("paper_submit_authorized", "live_authorized"),
        )


def test_mission_control_contract_validator_fails_broken_latest_run_references(
    tmp_path: Path,
) -> None:
    cases = (
        (
            "operator_review_path",
            "operator_review_path",
            "missing_review.md",
            (
                "latest_run.operator_review_path.missing_target",
                "latest_run.operator_review_path.unexpected_target",
            ),
        ),
        (
            "data_refresh_bridge_path",
            "data_refresh_bridge_path",
            "missing_bridge.json",
            (
                "latest_run.data_refresh_bridge_path.missing_target",
                "latest_run.data_refresh_bridge_path.unexpected_target",
                "latest_run.data_refresh_bridge_path.bridge_mismatch",
            ),
        ),
        (
            "data_refresh_dry_run_path",
            "data_refresh_dry_run_path",
            "missing_dry_run.json",
            (
                "latest_run.data_refresh_dry_run_path.missing_target",
                "latest_run.data_refresh_dry_run_path.unexpected_target",
                "latest_run.data_refresh_dry_run_path.dry_run_mismatch",
            ),
        ),
    )

    for case_name, field, missing_filename, expected_schema_errors in cases:
        output_root = _generate_mission_control_output(
            tmp_path,
            f"paper_lab_broken_latest_run_reference_{case_name}_out",
        )
        latest_run_path = output_root / "latest_run.json"
        latest_run = _read_json_artifact(latest_run_path)
        latest_run[field] = str(output_root / missing_filename)
        latest_run_path.write_text(
            json.dumps(latest_run, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        validation = validate_mission_control_contract(
            output_root,
            write_artifact=False,
        )

        assert validation["validation_status"] == "failed", case_name
        for expected_error in expected_schema_errors:
            assert expected_error in validation["schema_errors"], case_name


def test_mission_control_contract_validator_fails_missing_required_section(
    tmp_path: Path,
) -> None:
    output_root = _generate_mission_control_output(
        tmp_path,
        "paper_lab_missing_section_out",
    )
    mission = _read_mission_control(output_root)
    mission.pop("decision_lane")
    _write_mission_control(output_root, mission)

    validation = validate_mission_control_contract(
        output_root,
        write_artifact=False,
    )

    assert validation["validation_status"] == "failed"
    assert "mission_control.decision_lane.missing_or_not_object" in validation[
        "schema_errors"
    ]


def test_mission_control_contract_validator_blocks_unobserved_broker_absence_claims(
    tmp_path: Path,
) -> None:
    output_root = _generate_mission_control_output(
        tmp_path,
        "paper_lab_broker_absence_claim_out",
    )
    mission = _read_mission_control(output_root)
    broker = mission["broker_state_lane"]
    assert isinstance(broker, dict)
    broker["spy_position_absence_claimed"] = True
    broker["spy_open_order_absence_claimed"] = True
    broker["warning"] = "No SPY position and no open orders were found."
    _write_mission_control(output_root, mission)

    validation = validate_mission_control_contract(
        output_root,
        write_artifact=False,
    )

    assert validation["validation_status"] == "failed"
    assert (
        "mission_control.broker_state_lane.spy_position_absence_claimed"
        in validation["safety_errors"]
    )
    assert (
        "mission_control.broker_state_lane.spy_open_order_absence_claimed"
        in validation["safety_errors"]
    )
    assert (
        "mission_control.broker_state_not_observed.absence_claim_text"
        in validation["safety_errors"]
    )


def test_mission_control_contract_validator_blocks_unsafe_refresh_dry_run_flags(
    tmp_path: Path,
) -> None:
    output_root = _generate_mission_control_output(
        tmp_path,
        "paper_lab_unsafe_refresh_dry_run_out",
    )
    mission = _read_mission_control(output_root)
    dry_run = mission["data_refresh_dry_run"]
    assert isinstance(dry_run, dict)
    dry_run["paper_submit_authorized"] = True
    dry_run["broker_read_authorized"] = True
    dry_run["ingest_performed"] = True
    dry_run["dry_run_only"] = False
    _write_mission_control(output_root, mission)
    (output_root / "data_refresh_dry_run.json").write_text(
        json.dumps(dry_run, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    validation = validate_mission_control_contract(
        output_root,
        write_artifact=False,
    )

    assert validation["validation_status"] == "failed"
    assert "mission_control.data_refresh_dry_run.paper_submit_authorized" in (
        validation["safety_errors"]
    )
    assert "mission_control.data_refresh_dry_run.broker_read_authorized" in (
        validation["safety_errors"]
    )
    assert "mission_control.data_refresh_dry_run.ingest_performed" in (
        validation["safety_errors"]
    )
    assert "mission_control.data_refresh_dry_run.dry_run_only" in (
        validation["safety_errors"]
    )
    assert "data_refresh_dry_run.paper_submit_authorized" in validation[
        "safety_errors"
    ]
    assert "data_refresh_dry_run.ingest_performed" in validation["safety_errors"]


def test_mission_control_contract_validator_blocks_stale_data_labeled_current(
    tmp_path: Path,
) -> None:
    cases = (
        (
            "market_lane",
            "market_data_lane",
            {
                "staleness_in_days": 5,
                "preview_currency_status": "current",
                "preview_is_current": True,
            },
            None,
            (
                "mission_control.market_data_lane.stale_data_represented_as_current",
            ),
        ),
        (
            "freshness_plan",
            "data_freshness_plan",
            {"staleness_days": 5, "data_freshness_status": "current_local_data"},
            None,
            (
                "mission_control.data_freshness_plan.stale_data_represented_as_current",
            ),
        ),
        (
            "refresh_bridge",
            "data_refresh_bridge",
            {
                "current_staleness_days": 5,
                "current_data_freshness_status": "current_local_data",
            },
            "data_refresh_bridge.json",
            (
                "mission_control.data_refresh_bridge.stale_data_represented_as_current",
                "data_refresh_bridge.stale_data_represented_as_current",
            ),
        ),
    )

    for case_name, section, updates, mirror_artifact, expected_safety_errors in cases:
        output_root = _generate_mission_control_output(
            tmp_path,
            f"paper_lab_stale_current_{case_name}_out",
        )
        mission = _read_mission_control(output_root)
        stale_surface = mission[section]
        assert isinstance(stale_surface, dict)
        stale_surface.update(updates)
        _write_mission_control(output_root, mission)
        if mirror_artifact is not None:
            (output_root / mirror_artifact).write_text(
                json.dumps(stale_surface, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )

        validation = validate_mission_control_contract(
            output_root,
            write_artifact=False,
        )

        assert validation["validation_status"] == "failed", case_name
        for expected_error in expected_safety_errors:
            assert expected_error in validation["safety_errors"], case_name


def test_mission_control_readiness_score_blocks_on_safety_gate_failure() -> None:
    score = evaluate_mission_control_readiness_score(
        {
            "real_world_attachment": {"score": 1.0},
            "product_readiness": {"score": 1.0},
            "autonomy_middleman_reduction": {"score": 1.0},
            "strategy_quality": {"score": 1.0},
        },
        {
            "broker_mutation_path_appears": {"passed": False},
            "credentials_printed": {"passed": True},
        },
    )

    assert score["status"] == "blocked_by_safety_gate"
    assert score["score_valid"] is False
    assert score["total_score"] is None
    assert score["total_score_label"] == "blocked"
    assert score["blocked_by"] == ["broker_mutation_path_appears"]


def test_etf_sma_daily_paper_lab_alpaca_read_only_mode_is_scaffold_only(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_alpaca_read_only_scaffold_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
            broker_state_mode="alpaca_paper_read_only",
        )
    )

    mission = json.loads(
        (output_root / "mission_control.json").read_text(encoding="utf-8")
    )
    broker = mission["broker_state_lane"]
    assert payload["broker_state_mode"] == "alpaca_paper_read_only"
    assert broker["broker_state_mode"] == "alpaca_paper_read_only"
    assert broker["broker_state_status"] == "broker_read_scaffold_only"
    assert broker["broker_read_performed"] is False
    assert broker["broker_mutation_performed"] is False
    assert broker["paper_submit_authorized"] is False
    assert broker["live_authorized"] is False
    scaffold = broker["alpaca_paper_read_only_scaffold"]
    assert scaffold["requested"] is True
    assert scaffold["broker_read_scaffold_only"] is True
    assert scaffold["broker_read_requires_explicit_authorization"] is True
    assert scaffold["broker_read_performed"] is False
    assert scaffold["network_call_performed"] is False
    assert scaffold["sdk_client_imported"] is False

    validation = json.loads(
        (output_root / "mission_control_validation.json").read_text(encoding="utf-8")
    )
    assert validation["validation_status"] == "passed"
    assert validation["paper_submit_authorized"] is False
    assert validation["live_authorized"] is False


def _write_daily_lab_broker_snapshot(
    path: Path,
    *,
    symbol: str = "SPY",
    source_review_symbol: str = "SPY",
    generated_at: str = "2025-07-20T12:00:00+00:00",
    spy_position_qty: str = "0.033695775",
    open_spy_order_count: int = 0,
    unexpected_non_spy_position: bool = False,
    live_url_detected: bool = False,
    paper_lab_only: bool = True,
    read_only_broker_observation: bool = True,
    paper_profile_gate_passed: bool = True,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    spy_position_present = spy_position_qty not in {"", "0", "0.0", "0.000000000"}
    positions: list[dict[str, object]] = []
    if spy_position_present:
        positions.append({"symbol": "SPY", "qty": spy_position_qty})
    unexpected_positions: list[dict[str, object]] = []
    if unexpected_non_spy_position:
        unexpected = {"symbol": "MSFT", "qty": "1"}
        positions.append(unexpected)
        unexpected_positions.append(unexpected)
    open_orders = [
        {"symbol": "SPY", "qty": spy_position_qty or "1", "side": "buy"}
        for _ in range(open_spy_order_count)
    ]
    labels = [
        "paper_lab_only",
        "read_only_broker_observation",
        "operator_review_only",
        "not_live_authorized",
        "profit_claim=none",
    ]
    if not paper_lab_only:
        labels = [label for label in labels if label != "paper_lab_only"]
    if not read_only_broker_observation:
        labels = [
            label for label in labels if label != "read_only_broker_observation"
        ]
    record: dict[str, object] = {
        "command": "paper-lab-read-only-broker-snapshot-reconciliation",
        "record_type": "read_only_paper_broker_snapshot_reconciliation",
        "run_id": "m403_read_only_paper_broker_snapshot_reconciliation",
        "symbol": symbol,
        "generated_at": generated_at,
        "source_review_symbol": source_review_symbol,
        "source_review_state": "ready_for_operator_review",
        "source_cycle_decision": "buy_preview",
        "paper_profile_gate_passed": paper_profile_gate_passed,
        "paper_profile_ready": paper_profile_gate_passed,
        "profile_gate": {
            "passed": paper_profile_gate_passed,
            "status": "passed" if paper_profile_gate_passed else "blocked",
            "detail": "",
            "live_url_detected": live_url_detected,
        },
        "live_url_detected": live_url_detected,
        "account_observed": True,
        "positions_observed": True,
        "orders_observed": True,
        "open_orders_observed": True,
        "recent_orders_observed": True,
        "account": {"cash": "1000", "buying_power": "1000", "currency": "USD"},
        "positions": positions,
        "open_orders": open_orders,
        "recent_orders": [],
        "cash": "1000",
        "buying_power": "1000",
        "currency": "USD",
        "position_count": len(positions),
        "position_symbols": [str(position["symbol"]) for position in positions],
        "spy_position_present": spy_position_present,
        "spy_position_qty": spy_position_qty,
        "unexpected_non_spy_positions": unexpected_positions,
        "open_order_count": len(open_orders),
        "open_order_symbols": [str(order["symbol"]) for order in open_orders],
        "open_spy_orders": open_orders,
        "open_spy_order_count": len(open_orders),
        "unexpected_non_spy_open_orders": [],
        "unexpected_non_spy_open_order_count": 0,
        "recent_order_count": 0,
        "recent_order_symbols": [],
        "recent_spy_orders": [],
        "recent_spy_order_count": 0,
        "broker_observation_state": "observed",
        "reconciliation_state": (
            "blocked_open_order_present"
            if open_orders
            else (
                "blocked_unexpected_non_spy_position"
                if unexpected_positions
                else "ready_for_operator_review"
            )
        ),
        "blockers": (
            ["open_order_present", "open_spy_order_present"]
            if open_orders
            else (["unexpected_non_spy_position"] if unexpected_positions else [])
        ),
        "next_action": "operator_review_only",
        "paper_lab_only": paper_lab_only,
        "operator_review_only": True,
        "read_only_broker_observation": read_only_broker_observation,
        "labels": labels,
        "profit_claim": "none",
        "not_live_authorized": True,
        "paper_execution_authorized": False,
        "paper_submit_authorized": False,
        "submit_authorized": False,
        "broker_mutation_authorized": False,
        "broker_mutation_allowed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_action_flags": {
            "submit": False,
            "cancel": False,
            "replace": False,
            "close": False,
            "liquidate": False,
            "mutation": False,
        },
        "network_access_attempted": True,
        "credential_access_attempted": True,
        "live_authorized": False,
        "forbidden_actions": ["submit", "cancel", "replace", "close", "liquidate"],
        "next_forbidden_action": ["submit", "cancel", "replace", "close", "liquidate"],
    }
    if overrides:
        record.update(overrides)
    path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return record


def _write_daily_lab_broker_snapshot_without_generated_at(path: Path) -> None:
    record = _write_daily_lab_broker_snapshot(path)
    record.pop("generated_at")
    path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def test_etf_sma_daily_paper_lab_consumes_read_only_broker_snapshot(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_broker_snapshot_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    broker_snapshot_log = tmp_path / "m403_read_only_snapshot.jsonl"
    _write_daily_lab_broker_snapshot(broker_snapshot_log, spy_position_qty="0.5")

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-19",
            run_date="2025-07-20",
            symbol="SPY",
            broker_state_mode="alpaca_paper_read_only",
            broker_snapshot_log=broker_snapshot_log,
        )
    )

    mission = json.loads(
        (output_root / "mission_control.json").read_text(encoding="utf-8")
    )
    latest = json.loads((output_root / "latest_run.json").read_text(encoding="utf-8"))
    broker = mission["broker_state_lane"]
    decision = mission["decision_lane"]
    executive = mission["executive_summary"]
    daily_latest = mission["daily_latest"]
    daily_decision_summary = mission["daily_decision_summary"]
    data_refresh_dry_run = mission["data_refresh_dry_run"]

    assert payload["broker_state_observed"] is True
    assert broker["broker_state_mode"] == "alpaca_paper_read_only"
    assert broker["broker_state_status"] == "observed"
    assert broker["broker_state_observed"] is True
    assert broker["broker_snapshot_consumed"] is True
    assert broker["broker_read_performed"] is False
    assert broker["broker_mutation_performed"] is False
    assert broker["paper_submit_authorized"] is False
    assert broker["live_authorized"] is False
    assert broker["spy_position_present"] is True
    assert broker["spy_position_qty"] == "0.5"
    assert broker["open_order_count"] == 0
    assert broker["unexpected_non_spy_position_present"] is False
    assert decision["market_signal_preview"] == "buy_preview"
    assert decision["preview_decision"] == "hold/noop"
    assert decision["blocker_status"] == "none"
    assert "read_only_broker_observation" in decision["safety_labels"]
    assert "broker_state_observed" in decision["safety_labels"]
    assert "broker_state_not_observed" not in decision["safety_labels"]
    assert executive["validation_status"] == "passed"
    assert executive["main_blocker"] == "none"
    assert executive["broker_state_mode"] == "alpaca_paper_read_only"
    assert executive["broker_state_status"] == "observed"
    assert executive["broker_state_observed"] is True
    assert daily_latest["validation_status"] == "passed"
    assert daily_latest["blocker"] == "none"
    assert daily_latest["broker_state_mode"] == "alpaca_paper_read_only"
    assert daily_latest["broker_state_status"] == "observed"
    assert daily_latest["broker_state_observed"] is True
    assert data_refresh_dry_run["broker_state_mode"] == "alpaca_paper_read_only"
    assert data_refresh_dry_run["broker_state_observed"] is True
    assert data_refresh_dry_run["broker_state_not_observed"] is False
    assert data_refresh_dry_run["blocker_status"] != "broker_state_not_observed"
    assert data_refresh_dry_run["paper_submit_authorized"] is False
    assert data_refresh_dry_run["live_authorized"] is False
    assert data_refresh_dry_run["broker_read_performed"] is False
    assert data_refresh_dry_run["broker_mutation_performed"] is False
    _assert_execution_plan_surfaces(
        mission,
        expected_status="no_action_required",
        expected_action="hold/noop",
        expected_source_preview_decision="hold/noop",
        expected_blocker="none",
        expected_requires_approval=False,
        expected_reason="existing_spy_position_satisfies_risk_on_preview",
    )
    assert latest["daily_decision_summary"] == daily_decision_summary
    assert daily_decision_summary["broker_state_mode"] == "alpaca_paper_read_only"
    assert daily_decision_summary["broker_snapshot_freshness_status"] == "fresh"
    assert daily_decision_summary["snapshot_validation_status"] == "passed"
    assert daily_decision_summary["broker_state_status"] == "observed"
    assert daily_decision_summary["spy_position_observed"] is True
    assert daily_decision_summary["spy_position_present"] is True
    assert daily_decision_summary["spy_position_qty"] == "0.5"
    assert daily_decision_summary["open_spy_order_count"] == 0
    assert daily_decision_summary["unexpected_non_spy_position_count"] == 0
    assert daily_decision_summary["broker_aware_preview_decision"] == "hold/noop"
    assert daily_decision_summary["main_blocker"] == "none"
    assert daily_decision_summary["paper_submit_authorized"] is False
    assert daily_decision_summary["live_authorized"] is False
    assert daily_decision_summary["broker_mutation_performed"] is False
    assert daily_decision_summary["exact_next_operator_action"] == (
        "no_immediate_trading_action_run_next_completed_session_daily_cycle"
    )
    assert latest["preview_decision"] == "hold/noop"
    assert latest["main_blocker"] == "none"
    assert latest["broker_state_mode"] == "alpaca_paper_read_only"
    assert latest["broker_state_status"] == "observed"
    assert latest["broker_state_observed"] is True
    assert latest["observed_spy_position_qty"] == "0.5"
    assert latest["observed_spy_open_order_count"] == 0
    assert latest["exact_next_operator_action"] == (
        "no_immediate_trading_action_run_next_completed_session_daily_cycle"
    )
    assert latest["broker_read_performed"] is False
    assert latest["paper_submit_authorized"] is False
    assert latest["validation_status"] == "passed"

    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    manifest = json.loads((output_root / "manifest.jsonl").read_text(encoding="utf-8"))
    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")

    assert payload["preview_decision"] == "hold/noop"
    assert payload["blocker_status"] == "none"
    assert payload["blockers"] == []
    assert payload["broker_state_status"] == "observed"
    assert payload["broker_state_observed"] is True
    assert payload["broker_read_performed"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["paper_submit_authorized"] is False
    assert payload["live_authorized"] is False
    assert "read_only_broker_observation" in payload["safety_labels"]
    assert "broker_state_observed" in payload["safety_labels"]
    assert "broker_state_not_observed" not in payload["safety_labels"]
    assert "linked read-only snapshot artifact" in payload["broker_state_claim"]
    assert payload["validation_status"] == "pass"
    assert payload["missing_required_fields"] == []
    assert payload["history_delta"]["current_validation_status"] == "pass"
    assert payload["history_delta"]["current_validation_status"] != "fail"
    assert payload["history_ledger_entry"]["validation_status"] == "pass"
    assert payload["history_ledger_entry"]["blocker_status"] == "none"
    assert payload["history_ledger_entry"]["broker_state_mode"] == (
        "alpaca_paper_read_only"
    )
    assert payload["history_ledger_entry"]["broker_state_observed"] is True
    assert payload["executive_summary"]["current_blocker"] == "none"
    assert "broker_state_not_observed" not in json.dumps(
        payload["executive_summary"],
        sort_keys=True,
    )

    for artifact_record in (record, manifest):
        assert artifact_record["preview_decision"] == "hold/noop"
        assert artifact_record["blocker_status"] == "none"
        assert artifact_record["validation_status"] == "pass"
        assert artifact_record["missing_required_fields"] == []
        assert artifact_record["next_operator_action"] == (
            "no_immediate_trading_action_run_next_completed_session_daily_cycle"
        )
        assert "read_only_broker_observation" in artifact_record["safety_labels"]
        assert "broker_state_observed" in artifact_record["safety_labels"]
        assert "broker_state_not_observed" not in artifact_record["safety_labels"]

    assert record["blockers"] == []
    assert record["broker_state_status"] == "observed"
    assert record["broker_state_observed"] is True
    assert record["broker_read_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["paper_submit_authorized"] is False
    assert record["live_authorized"] is False
    assert record["execution_plan"] == mission["execution_plan"]
    assert record["daily_approval_gate"] == mission["daily_approval_gate"]
    assert payload["daily_approval_gate"] == mission["daily_approval_gate"]
    assert mission["daily_approval_gate"]["approval_required"] is False
    assert mission["daily_approval_gate"]["approval_state"] == "not_required_noop"
    assert mission["daily_approval_gate"]["submit_allowed"] is False
    assert (
        mission["daily_approval_gate"]["paper_submit_authorized"]
        is False
    )
    assert mission["daily_approval_gate"]["live_authorized"] is False
    assert (
        mission["daily_approval_gate"]["broker_mutation_performed"]
        is False
    )
    assert (
        mission["daily_approval_gate"]["reason"]
        == "execution_plan_requires_no_action"
    )
    assert mission["daily_approval_gate"]["blocker"] == "none"
    assert "* **Preview decision**: hold/noop" in brief
    assert "* **Blocker status**: none" in brief
    assert "Preview decision: `hold/noop`" in brief
    assert "* **Risks / blockers**: none." in brief

    index_html = (output_root / "index.html").read_text(encoding="utf-8")
    operator_review = (output_root / "operator_review.md").read_text(
        encoding="utf-8"
    )
    assert index_html.index("<h2>Daily Decision Summary</h2>") < index_html.index(
        "<h2>Open First</h2>"
    )
    assert "Broker-aware preview decision</dt><dd>hold/noop" in index_html
    assert "ExecutionPlan status</dt><dd>no_action_required" in index_html
    assert "ExecutionPlan action</dt><dd>hold/noop" in index_html
    assert "ExecutionPlan submit allowed</dt><dd>false" in index_html
    assert "DailyApprovalGate approval required</dt><dd>false" in index_html
    assert "DailyApprovalGate approval state</dt><dd>not_required_noop" in index_html
    assert "DailyApprovalGate submit allowed</dt><dd>false" in index_html
    assert "DailyApprovalGate paper submit authorized</dt><dd>false" in index_html
    assert "DailyApprovalGate live authorized</dt><dd>false" in index_html
    assert (
        "no_immediate_trading_action_run_next_completed_session_daily_cycle"
        in index_html
    )
    assert operator_review.index("## Daily Decision Summary") < operator_review.index(
        "## Open First"
    )
    assert "Broker-aware preview decision: `hold/noop`" in operator_review
    assert "ExecutionPlan status: `no_action_required`" in operator_review
    assert "ExecutionPlan action: `hold/noop`" in operator_review
    assert "ExecutionPlan submit allowed: `false`" in operator_review
    assert "DailyApprovalGate approval required: `false`" in operator_review
    assert "DailyApprovalGate approval state: `not_required_noop`" in operator_review
    assert "DailyApprovalGate submit allowed: `false`" in operator_review
    assert "DailyApprovalGate paper submit authorized: `false`" in operator_review
    assert "DailyApprovalGate live authorized: `false`" in operator_review
    assert (
        "DailyApprovalGate reason: `execution_plan_requires_no_action`"
        in operator_review
    )
    assert "DailyApprovalGate blocker: `none`" in operator_review
    assert (
        "Exact next operator action: `no_immediate_trading_action_run_next_completed_session_daily_cycle`"
        in operator_review
    )

    validation = json.loads(
        (output_root / "mission_control_validation.json").read_text(encoding="utf-8")
    )
    assert validation["validation_status"] == "passed"
    assert mission["mission_control_validation_summary"]["validation_status"] == (
        "passed"
    )
    active_validation_statuses = [
        payload["validation_status"],
        record["validation_status"],
        manifest["validation_status"],
        executive["validation_status"],
        latest["validation_status"],
        daily_latest["validation_status"],
        validation["validation_status"],
    ]
    assert "fail" not in active_validation_statuses
    assert "failed" not in active_validation_statuses
    active_blocker_surfaces = {
        "legacy_executive_summary": payload["executive_summary"],
        "executive_summary": executive,
        "latest_run": latest,
        "daily_latest": daily_latest,
        "daily_decision_summary": daily_decision_summary,
        "history_delta": payload["history_delta"],
        "history_ledger_entry": payload["history_ledger_entry"],
    }
    active_surface_text = json.dumps(active_blocker_surfaces, sort_keys=True)
    assert "broker_state_not_observed" not in active_surface_text


@pytest.mark.parametrize(
    (
        "bars_fixture",
        "spy_position_qty",
        "expected_decision",
        "expected_action",
        "expected_plan_status",
        "expected_plan_action",
        "expected_requires_approval",
        "expected_plan_reason",
    ),
    [
        (
            "spy_daily_bars_200_bullish.csv",
            "0",
            "buy_preview",
            "paper_submit_not_authorized_record_preview_only_no_submission",
            "preview_only",
            "buy_preview",
            True,
            (
                "risk_on_without_spy_position_preview_requires_explicit_"
                "paper_submit_authorization"
            ),
        ),
        (
            "spy_daily_bars_200_bullish.csv",
            "0.033695775",
            "hold/noop",
            "no_immediate_trading_action_run_next_completed_session_daily_cycle",
            "no_action_required",
            "hold/noop",
            False,
            "existing_spy_position_satisfies_risk_on_preview",
        ),
        (
            "spy_daily_bars_200_bearish.csv",
            "0.033695775",
            "sell_preview",
            "paper_submit_not_authorized_record_preview_only_no_submission",
            "preview_only",
            "sell_preview",
            True,
            (
                "risk_off_with_spy_position_preview_requires_explicit_"
                "paper_submit_authorization"
            ),
        ),
        (
            "spy_daily_bars_200_bearish.csv",
            "0",
            "hold/noop",
            "no_immediate_trading_action_run_next_completed_session_daily_cycle",
            "no_action_required",
            "hold/noop",
            False,
            "risk_off_flat_no_action_required",
        ),
    ],
)
def test_etf_sma_daily_paper_lab_broker_aware_decision_matrix(
    tmp_path: Path,
    bars_fixture: str,
    spy_position_qty: str,
    expected_decision: str,
    expected_action: str,
    expected_plan_status: str,
    expected_plan_action: str,
    expected_requires_approval: bool,
    expected_plan_reason: str,
) -> None:
    output_root = tmp_path / "paper_lab_decision_matrix"
    broker_snapshot_log = tmp_path / "m403_snapshot.jsonl"
    _write_daily_lab_broker_snapshot(
        broker_snapshot_log,
        spy_position_qty=spy_position_qty,
    )

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / bars_fixture,
            as_of_date="2025-07-19",
            run_date="2025-07-20",
            symbol="SPY",
            broker_state_mode="alpaca_paper_read_only",
            broker_snapshot_log=broker_snapshot_log,
        )
    )

    mission = _read_mission_control(output_root)
    decision = mission["decision_lane"]
    latest = mission["latest_run"]
    assert decision["preview_decision"] == expected_decision
    assert decision["blocker_status"] == "none"
    assert latest["exact_next_operator_action"] == expected_action
    assert latest["paper_submit_authorized"] is False
    assert latest["live_authorized"] is False
    _assert_execution_plan_surfaces(
        mission,
        expected_status=expected_plan_status,
        expected_action=expected_plan_action,
        expected_source_preview_decision=expected_decision,
        expected_blocker="none",
        expected_requires_approval=expected_requires_approval,
        expected_reason=expected_plan_reason,
    )


def test_etf_sma_daily_paper_lab_insufficient_history_wins_before_broker_state(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_insufficient_history"
    broker_snapshot_log = tmp_path / "m403_snapshot.jsonl"
    _write_daily_lab_broker_snapshot(broker_snapshot_log, spy_position_qty="0.033")

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_199.csv",
            as_of_date="2025-07-18",
            run_date="2025-07-19",
            symbol="SPY",
            broker_state_mode="alpaca_paper_read_only",
            broker_snapshot_log=broker_snapshot_log,
        )
    )

    mission = _read_mission_control(output_root)
    assert mission["decision_lane"]["preview_decision"] == "insufficient_history"
    assert mission["decision_lane"]["blocker_status"] == "insufficient_history"
    _assert_execution_plan_surfaces(
        mission,
        expected_status="blocked",
        expected_action="none",
        expected_source_preview_decision="insufficient_history",
        expected_blocker="insufficient_history",
        expected_requires_approval=False,
        expected_reason="insufficient_history",
    )
    assert mission["latest_run"]["exact_next_operator_action"] == (
        "provide_at_least_200_usable_daily_bars_before_preview_use"
    )


def test_etf_sma_daily_paper_lab_open_spy_order_blocks_preview(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_open_order"
    broker_snapshot_log = tmp_path / "m403_snapshot.jsonl"
    _write_daily_lab_broker_snapshot(
        broker_snapshot_log,
        spy_position_qty="0",
        open_spy_order_count=1,
    )

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-19",
            run_date="2025-07-20",
            symbol="SPY",
            broker_state_mode="alpaca_paper_read_only",
            broker_snapshot_log=broker_snapshot_log,
        )
    )

    mission = _read_mission_control(output_root)
    assert mission["decision_lane"]["preview_decision"] == "blocked/open_order_present"
    assert mission["decision_lane"]["blocker_status"] == "open_order_present"
    _assert_execution_plan_surfaces(
        mission,
        expected_status="blocked",
        expected_action="none",
        expected_source_preview_decision="blocked/open_order_present",
        expected_blocker="open_order_present",
        expected_requires_approval=False,
        expected_reason="open_order_present",
    )
    assert mission["latest_run"]["exact_next_operator_action"] == (
        "review_open_spy_order_with_read_only_reconciliation_no_mutation"
    )


def test_etf_sma_daily_paper_lab_unexpected_non_spy_position_blocks_preview(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_unexpected_position"
    broker_snapshot_log = tmp_path / "m403_snapshot.jsonl"
    _write_daily_lab_broker_snapshot(
        broker_snapshot_log,
        spy_position_qty="0.033695775",
        unexpected_non_spy_position=True,
    )

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-19",
            run_date="2025-07-20",
            symbol="SPY",
            broker_state_mode="alpaca_paper_read_only",
            broker_snapshot_log=broker_snapshot_log,
        )
    )

    mission = _read_mission_control(output_root)
    assert mission["decision_lane"]["preview_decision"] == (
        "blocked/unexpected_non_spy_position"
    )
    assert mission["decision_lane"]["blocker_status"] == "unexpected_non_spy_position"
    _assert_execution_plan_surfaces(
        mission,
        expected_status="blocked",
        expected_action="none",
        expected_source_preview_decision="blocked/unexpected_non_spy_position",
        expected_blocker="unexpected_non_spy_position",
        expected_requires_approval=False,
        expected_reason="unexpected_non_spy_position",
    )
    assert mission["latest_run"]["exact_next_operator_action"] == (
        "review_unexpected_non_spy_position_with_read_only_reconciliation_no_mutation"
    )


def test_etf_sma_daily_paper_lab_missing_snapshot_never_claims_broker_absence(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_missing_snapshot"

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-19",
            run_date="2025-07-20",
            symbol="SPY",
        )
    )

    mission = _read_mission_control(output_root)
    broker = mission["broker_state_lane"]
    latest = mission["latest_run"]
    assert broker["broker_state_status"] == "broker_state_not_observed"
    assert broker["broker_state_observed"] is False
    assert broker["spy_position_qty"] is None
    assert broker["open_order_count"] is None
    assert latest["observed_spy_position_qty"] is None
    assert latest["observed_spy_open_order_count"] is None
    assert latest["preview_decision"] == "blocked/broker_state_not_observed"
    _assert_execution_plan_surfaces(
        mission,
        expected_status="blocked",
        expected_action="none",
        expected_source_preview_decision="blocked/broker_state_not_observed",
        expected_blocker="broker_state_not_observed",
        expected_requires_approval=False,
        expected_reason="broker_state_not_observed",
    )
    assert latest["exact_next_operator_action"] == (
        "produce_fresh_explicitly_authorized_read_only_paper_broker_snapshot_"
        "for_spy_daily_lab"
    )


@pytest.mark.parametrize(
    ("case_name", "writer", "expected_status", "expected_error"),
    [
        (
            "stale_broker_snapshot",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                generated_at="2025-07-18T12:00:00+00:00",
            ),
            "stale_snapshot",
            "broker_snapshot_stale",
        ),
        (
            "missing_broker_snapshot_timestamp",
            _write_daily_lab_broker_snapshot_without_generated_at,
            "invalid_snapshot",
            "broker_snapshot_generated_at_missing_or_invalid",
        ),
        (
            "future_broker_snapshot_timestamp",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                generated_at="2025-07-21T12:00:00+00:00",
            ),
            "future_dated_snapshot",
            "broker_snapshot_future_dated",
        ),
        (
            "malformed",
            lambda path: path.write_text("{not-json}\n", encoding="utf-8"),
            "invalid_snapshot",
            "broker_snapshot_json_decode_error",
        ),
        (
            "contradictory",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                spy_position_qty="0",
                overrides={"open_order_count": 0, "open_order_symbols": ["SPY"]},
            ),
            "contradictory_snapshot",
            "broker_snapshot_open_order_symbols_contradiction",
        ),
        (
            "live_labeled",
            lambda path: _write_daily_lab_broker_snapshot(path, live_url_detected=True),
            "live_url_detected",
            "broker_snapshot_live_labeled",
        ),
        (
            "symbol_mismatch",
            lambda path: _write_daily_lab_broker_snapshot(path, symbol="MSFT"),
            "snapshot_context_mismatch",
            "broker_snapshot_symbol_mismatch",
        ),
    ],
)
def test_etf_sma_daily_paper_lab_unsafe_snapshots_fail_closed(
    tmp_path: Path,
    case_name: str,
    writer: object,
    expected_status: str,
    expected_error: str,
) -> None:
    output_root = tmp_path / f"paper_lab_unsafe_{case_name}"
    broker_snapshot_log = tmp_path / f"{case_name}.jsonl"
    writer(broker_snapshot_log)  # type: ignore[operator]

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-19",
            run_date="2025-07-20",
            symbol="SPY",
            broker_state_mode="alpaca_paper_read_only",
            broker_snapshot_log=broker_snapshot_log,
        )
    )

    mission = _read_mission_control(output_root)
    broker = mission["broker_state_lane"]
    latest = mission["latest_run"]
    snapshot = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )["broker_state_snapshot"]
    assert broker["broker_state_status"] == expected_status
    assert broker["broker_state_observed"] is False
    assert latest["preview_decision"] == f"blocked/{expected_status}"
    _assert_execution_plan_surfaces(
        mission,
        expected_status="blocked",
        expected_action="none",
        expected_source_preview_decision=f"blocked/{expected_status}",
        expected_blocker=expected_status,
        expected_requires_approval=False,
        expected_reason=expected_status,
    )
    assert latest["paper_submit_authorized"] is False
    assert latest["live_authorized"] is False
    assert latest["exact_next_operator_action"] == (
        "correct_or_replace_unsafe_local_broker_snapshot_before_next_cycle"
    )
    assert expected_error in snapshot["snapshot_validation_errors"]


def _pin_daily_lab_cli_run_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        paper_lab_module,
        "_current_utc_date",
        lambda: date(2025, 7, 20),
    )


def _run_daily_paper_lab_cli(
    *,
    output_root: Path,
    bars_csv: Path,
    broker_snapshot_log: Path | None = None,
) -> int:
    argv = [
        "etf-sma-daily-paper-lab",
        "--output-root",
        str(output_root),
        "--bars-csv",
        str(bars_csv),
        "--as-of-date",
        "2025-07-19",
        "--symbol",
        "SPY",
        "--format",
        "json",
    ]
    if broker_snapshot_log is not None:
        argv.extend(
            [
                "--broker-state-mode",
                "alpaca_paper_read_only",
                "--broker-snapshot-log",
                str(broker_snapshot_log),
            ]
        )
    return cli_module.main(argv)


def test_etf_sma_daily_paper_lab_cli_no_snapshot_exit_zero_and_no_false_broker_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_daily_lab_cli_run_date(monkeypatch)
    output_root = tmp_path / "paper_lab_cli_no_snapshot"

    exit_code = _run_daily_paper_lab_cli(
        output_root=output_root,
        bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
    )

    mission = _read_mission_control(output_root)
    broker = mission["broker_state_lane"]
    latest = mission["latest_run"]
    assert exit_code == 0
    assert broker["broker_state_status"] == "broker_state_not_observed"
    assert broker["broker_state_observed"] is False
    assert broker["broker_snapshot_consumed"] is False
    assert broker["spy_position_qty"] is None
    assert broker["open_order_count"] is None
    assert latest["observed_spy_position_qty"] is None
    assert latest["observed_spy_open_order_count"] is None
    assert latest["preview_decision"] == "blocked/broker_state_not_observed"
    assert latest["paper_submit_authorized"] is False
    assert latest["live_authorized"] is False


def test_etf_sma_daily_paper_lab_cli_valid_snapshot_exit_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_daily_lab_cli_run_date(monkeypatch)
    output_root = tmp_path / "paper_lab_cli_valid_snapshot"
    broker_snapshot_log = tmp_path / "valid_snapshot.jsonl"
    _write_daily_lab_broker_snapshot(
        broker_snapshot_log,
        generated_at="2025-07-20T12:00:00+00:00",
        spy_position_qty="0.5",
    )

    exit_code = _run_daily_paper_lab_cli(
        output_root=output_root,
        bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
        broker_snapshot_log=broker_snapshot_log,
    )

    mission = _read_mission_control(output_root)
    broker = mission["broker_state_lane"]
    latest = mission["latest_run"]
    assert exit_code == 0
    assert broker["broker_state_status"] == "observed"
    assert broker["broker_state_observed"] is True
    assert broker["spy_position_qty"] == "0.5"
    assert latest["preview_decision"] == "hold/noop"
    assert latest["main_blocker"] == "none"
    assert latest["paper_submit_authorized"] is False
    assert latest["live_authorized"] is False


def test_etf_sma_daily_paper_lab_cli_stale_snapshot_policy_is_zero_but_untrusted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_daily_lab_cli_run_date(monkeypatch)
    output_root = tmp_path / "paper_lab_cli_stale_snapshot"
    broker_snapshot_log = tmp_path / "stale_snapshot.jsonl"
    _write_daily_lab_broker_snapshot(
        broker_snapshot_log,
        generated_at="2025-07-18T12:00:00+00:00",
    )

    exit_code = _run_daily_paper_lab_cli(
        output_root=output_root,
        bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
        broker_snapshot_log=broker_snapshot_log,
    )

    mission = _read_mission_control(output_root)
    broker = mission["broker_state_lane"]
    latest = mission["latest_run"]
    snapshot = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )["broker_state_snapshot"]
    assert exit_code == 0
    assert broker["broker_state_status"] == "stale_snapshot"
    assert broker["broker_state_observed"] is False
    assert latest["preview_decision"] == "blocked/stale_snapshot"
    assert snapshot["broker_state_trusted"] is False
    assert snapshot["broker_observation_state"] == "stale_snapshot"
    assert "broker_snapshot_stale" in snapshot["snapshot_validation_errors"]
    assert latest["paper_submit_authorized"] is False
    assert latest["live_authorized"] is False


@pytest.mark.parametrize(
    ("case_name", "writer", "expected_status", "expected_error"),
    [
        (
            "malformed",
            lambda path: path.write_text("{not-json}\n", encoding="utf-8"),
            "invalid_snapshot",
            "broker_snapshot_json_decode_error",
        ),
        (
            "ambiguous",
            lambda path: path.write_text(
                json.dumps(_write_daily_lab_broker_snapshot(path), sort_keys=True)
                + "\n"
                + json.dumps(
                    _write_daily_lab_broker_snapshot(path, spy_position_qty="0"),
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            ),
            "invalid_snapshot",
            "broker_snapshot_ambiguous_record_count",
        ),
        (
            "contradictory",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                generated_at="2025-07-20T12:00:00+00:00",
                spy_position_qty="0",
                overrides={"open_order_count": 0, "open_order_symbols": ["SPY"]},
            ),
            "contradictory_snapshot",
            "broker_snapshot_open_order_symbols_contradiction",
        ),
        (
            "live_labeled",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                generated_at="2025-07-20T12:00:00+00:00",
                live_url_detected=True,
            ),
            "live_url_detected",
            "broker_snapshot_live_labeled",
        ),
        (
            "non_paper_labeled",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                generated_at="2025-07-20T12:00:00+00:00",
                paper_lab_only=False,
            ),
            "non_paper_or_mutation_capable_snapshot",
            "broker_snapshot_not_paper_lab_only",
        ),
        (
            "invalid_timestamp",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                generated_at="not-a-timestamp",
            ),
            "invalid_snapshot",
            "broker_snapshot_generated_at_missing_or_invalid",
        ),
        (
            "missing_broker_snapshot_timestamp",
            _write_daily_lab_broker_snapshot_without_generated_at,
            "invalid_snapshot",
            "broker_snapshot_generated_at_missing_or_invalid",
        ),
        (
            "future_broker_snapshot_timestamp",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                generated_at="2025-07-21T12:00:00+00:00",
            ),
            "future_dated_snapshot",
            "broker_snapshot_future_dated",
        ),
        (
            "symbol_mismatch",
            lambda path: _write_daily_lab_broker_snapshot(
                path,
                generated_at="2025-07-20T12:00:00+00:00",
                symbol="MSFT",
            ),
            "snapshot_context_mismatch",
            "broker_snapshot_symbol_mismatch",
        ),
    ],
)
def test_etf_sma_daily_paper_lab_cli_unsafe_snapshot_exit_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case_name: str,
    writer: object,
    expected_status: str,
    expected_error: str,
) -> None:
    _pin_daily_lab_cli_run_date(monkeypatch)
    output_root = tmp_path / f"paper_lab_cli_unsafe_{case_name}"
    broker_snapshot_log = tmp_path / f"{case_name}.jsonl"
    writer(broker_snapshot_log)  # type: ignore[operator]

    exit_code = _run_daily_paper_lab_cli(
        output_root=output_root,
        bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
        broker_snapshot_log=broker_snapshot_log,
    )

    mission = _read_mission_control(output_root)
    broker = mission["broker_state_lane"]
    latest = mission["latest_run"]
    snapshot = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )["broker_state_snapshot"]
    assert exit_code == 1
    assert broker["broker_state_status"] == expected_status
    assert broker["broker_state_observed"] is False
    assert snapshot["broker_state_trusted"] is False
    assert latest["preview_decision"] == f"blocked/{expected_status}"
    assert latest["exact_next_operator_action"] == (
        "correct_or_replace_unsafe_local_broker_snapshot_before_next_cycle"
    )
    assert latest["paper_submit_authorized"] is False
    assert latest["live_authorized"] is False
    assert expected_error in snapshot["snapshot_validation_errors"]


def test_etf_sma_daily_paper_lab_exit_status_flags_validation_and_safety_failures() -> None:
    assert paper_lab_module.etf_sma_daily_paper_lab_exit_status(
        {"mission_control_validation": {"validation_status": "failed"}}
    ) == 1
    assert paper_lab_module.etf_sma_daily_paper_lab_exit_status(
        {"paper_submit_authorized": True}
    ) == 1
    assert paper_lab_module.etf_sma_daily_paper_lab_exit_status(
        {"live_authorized": True}
    ) == 1

def test_etf_sma_daily_paper_lab_forward_ledger_is_idempotent(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_forward_ledger_idempotent"
    config = EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
        as_of_date="2025-07-19",
        run_date="2025-07-20",
        symbol="SPY",
    )

    run_etf_sma_daily_paper_lab(config)
    ledger_path = output_root / "forward_signal_evidence_ledger.jsonl"
    first_content = ledger_path.read_text(encoding="utf-8")
    run_etf_sma_daily_paper_lab(config)
    second_content = ledger_path.read_text(encoding="utf-8")

    assert second_content == first_content
    entries = [json.loads(line) for line in second_content.splitlines()]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["profit_claim"] == "none"
    assert entry["actual_broker_portfolio_pnl_claim"] == "none"
    assert entry["return_kind"] == "hypothetical_signal_forward_return"
    assert entry["horizon_status"] == "pending"


def test_etf_sma_daily_paper_lab_forward_ledger_matures_prior_observation(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_forward_ledger_maturity"
    base_bars = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    extended_bars = tmp_path / "spy_daily_bars_201_bullish.csv"
    extended_bars.write_text(
        base_bars.read_text(encoding="utf-8") + "2025-07-20,21.0\n",
        encoding="utf-8",
    )

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=base_bars,
            as_of_date="2025-07-19",
            run_date="2025-07-20",
            symbol="SPY",
        )
    )
    first_entries = [
        json.loads(line)
        for line in (output_root / "forward_signal_evidence_ledger.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert first_entries[0]["horizon_status"] == "pending"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=extended_bars,
            as_of_date="2025-07-20",
            run_date="2025-07-21",
            symbol="SPY",
        )
    )

    ledger_entries = [
        json.loads(line)
        for line in (output_root / "forward_signal_evidence_ledger.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    by_date = {entry["signal_as_of_date"]: entry for entry in ledger_entries}
    assert len(ledger_entries) == 2
    assert by_date["2025-07-19"]["horizon_status"] == "evaluated"
    assert by_date["2025-07-19"]["forward_close_date"] == "2025-07-20"
    assert by_date["2025-07-20"]["horizon_status"] == "pending"
    summary = payload["forward_signal_evidence_ledger_summary"]
    assert summary["evaluated_count"] == 1
    assert summary["pending_count"] == 1
    assert by_date["2025-07-19"]["actual_broker_portfolio_pnl_claim"] == "none"


def test_etf_sma_daily_paper_lab_mission_control_exposes_ledger_and_action(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_mission_control_v147a"

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-19",
            run_date="2025-07-20",
            symbol="SPY",
        )
    )

    mission = _read_mission_control(output_root)
    daily_latest = mission["daily_latest"]
    assert daily_latest["forward_signal_evidence_ledger_status"] == "generated"
    assert daily_latest["forward_signal_evidence_ledger_summary"]["profit_claim"] == (
        "none"
    )
    assert daily_latest["exact_next_operator_action"] == (
        "produce_fresh_explicitly_authorized_read_only_paper_broker_snapshot_"
        "for_spy_daily_lab"
    )
    assert "paper_lab_only" in daily_latest["safety_labels"]
    assert "not_live_authorized" in daily_latest["safety_labels"]
    assert "profit_claim=none" in daily_latest["safety_labels"]


def test_etf_sma_daily_paper_lab_research_board_prioritization(tmp_path: Path) -> None:
    """Explicitly verify research board prioritization generation and validator logic."""
    output_root = tmp_path / "paper_lab_prioritization_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    config = EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=bars_csv,
        as_of_date="2025-07-20",
        symbol="SPY",
    )

    payload = run_etf_sma_daily_paper_lab(config)

    # Verify output file exists and is populated
    prioritization_file = output_root / "research_board_prioritization.jsonl"
    assert prioritization_file.exists()
    lines = prioritization_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_research_board_prioritization_shape(data)
    _assert_research_board_prioritization_shape(payload["research_board_prioritization"])

    # Verify validation logic passes
    validation_result = validate_etf_sma_daily_paper_lab_packet(output_root, packet=payload)
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_strategy_comparison_scaffold(
    tmp_path: Path,
) -> None:
    """Verify v1.14 strategy comparison scaffold artifact and packet wiring."""
    output_root = tmp_path / "paper_lab_strategy_comparison_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    scaffold_file = output_root / "strategy_comparison_scaffold.jsonl"
    assert scaffold_file.exists()
    lines = scaffold_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_strategy_comparison_scaffold_shape(data)
    _assert_strategy_comparison_scaffold_shape(
        payload["strategy_comparison_scaffold"]
    )
    assert data == payload["strategy_comparison_scaffold"]
    assert payload["strategy_comparison_scaffold_path"].endswith(
        "strategy_comparison_scaffold.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["strategy_comparison_scaffold"] == data
    assert record["strategy_comparison_scaffold"] == data
    assert "strategy_comparison_scaffold" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["strategy_comparison_scaffold"][
        "path"
    ].endswith("strategy_comparison_scaffold.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    assert "## Strategy Comparison Scaffold" in brief
    assert "## Strategy Comparison Scaffold" in handoff
    assert "strategy_comparison_scaffold.jsonl" in brief
    assert "strategy_comparison_scaffold.jsonl" in handoff

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["strategy_comparison_scaffold"] == data
    assert payload["work_order_exports"]["strategy_comparison_scaffold"] == data
    assert (
        payload["strategy_comparison_scaffold"]["selected_next_safe_action"]
        == "build_candidate_strategy_evidence_template"
    )
    assert payload["quality_gate_status"] == "pass"
    assert "strategy_comparison_scaffold_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_evidence_collection_plan(
    tmp_path: Path,
) -> None:
    """Verify v1.17 candidate evidence collection plan artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_collection_plan_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    collection_plan_file = output_root / "candidate_evidence_collection_plan.jsonl"
    assert collection_plan_file.exists()
    lines = collection_plan_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_evidence_collection_plan_shape(data)
    _assert_candidate_evidence_collection_plan_shape(
        payload["candidate_evidence_collection_plan"]
    )
    assert data == payload["candidate_evidence_collection_plan"]
    assert payload["candidate_evidence_collection_plan_path"].endswith(
        "candidate_evidence_collection_plan.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_evidence_collection_plan"] == data
    assert record["candidate_evidence_collection_plan"] == data
    assert "candidate_evidence_collection_plan" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_evidence_collection_plan"][
        "path"
    ].endswith("candidate_evidence_collection_plan.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    assert "## Candidate Evidence Collection Plan" in brief
    assert "## Candidate Evidence Collection Plan" in handoff
    assert "candidate_evidence_collection_plan.jsonl" in brief
    assert "candidate_evidence_collection_plan.jsonl" in handoff
    assert "offline_candidate_evidence_collection_plan_only" in brief
    assert "build_candidate_evidence_collection_status" in handoff

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert (
        payload["next_action_selector"]["candidate_evidence_collection_plan"]
        == data
    )
    assert payload["work_order_exports"]["candidate_evidence_collection_plan"] == data
    assert data["collection_plan_status"] == "ready"
    assert (
        data["collection_plan_mode"]
        == "offline_candidate_evidence_collection_plan_only"
    )
    assert data["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert data["baseline_strategy_role"] == "control_harness"
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["safety_scope"] == "offline_only"
    assert data["paper_submit_authorized"] is False
    assert data["profit_claim"] == "none"
    assert data["daniel_action_required_now"] is False
    assert data["selected_next_safe_action"] == (
        "build_candidate_evidence_collection_status"
    )
    assert data["candidate_collection_plans"]
    assert data["shared_collection_steps"]
    assert data["data_collection_requirements"]
    assert data["metric_collection_requirements"]
    assert data["safety_collection_requirements"]
    assert data["expected_offline_artifacts"]
    assert data["blocked_until_collected"]
    assert "candidate_evidence_collection_plan_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_evidence_collection_status(
    tmp_path: Path,
) -> None:
    """Verify v1.18 candidate evidence collection status artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_collection_status_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2024-10-18",
            symbol="SPY",
        )
    )

    collection_status_file = (
        output_root / "candidate_evidence_collection_status.jsonl"
    )
    assert collection_status_file.exists()
    lines = collection_status_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_evidence_collection_status_shape(data)
    _assert_candidate_evidence_collection_status_shape(
        payload["candidate_evidence_collection_status"]
    )
    assert data == payload["candidate_evidence_collection_status"]
    assert payload["candidate_evidence_collection_status_path"].endswith(
        "candidate_evidence_collection_status.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_evidence_collection_status"] == data
    assert record["candidate_evidence_collection_status"] == data
    assert "candidate_evidence_collection_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_evidence_collection_status"][
        "path"
    ].endswith("candidate_evidence_collection_status.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    assert "## Candidate Evidence Collection Status" in brief
    assert "## Candidate Evidence Collection Status" in handoff
    assert "candidate_evidence_collection_status.jsonl" in brief
    assert "candidate_evidence_collection_status.jsonl" in handoff
    assert "offline_candidate_evidence_collection_status_only" in brief
    assert "build_candidate_evidence_gap_summary" in handoff

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert (
        payload["next_action_selector"]["candidate_evidence_collection_status"]
        == data
    )
    assert (
        payload["work_order_exports"]["candidate_evidence_collection_status"]
        == data
    )
    assert data["collection_status"] == "ready"
    assert (
        data["collection_status_mode"]
        == "offline_candidate_evidence_collection_status_only"
    )
    assert data["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert data["baseline_strategy_role"] == "control_harness"
    assert data["candidate_statuses"]
    assert data["shared_collection_status"]
    assert data["evidence_status_counts"]
    assert data["not_started_evidence"]
    assert data["blocked_evidence"]
    assert data["ready_to_collect_evidence"]
    assert data["missing_evidence"]
    assert data["promotion_blockers"]
    assert data["selected_next_safe_action"] == "build_candidate_evidence_gap_summary"
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["safety_scope"] == "offline_only"
    assert data["paper_submit_authorized"] is False
    assert data["profit_claim"] == "none"
    assert data["daniel_action_required_now"] is False
    assert "candidate_evidence_collection_status_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_evidence_gap_summary(
    tmp_path: Path,
) -> None:
    """Verify v1.19 candidate evidence gap summary artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_gap_summary_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2024-10-18",
            symbol="SPY",
        )
    )

    gap_summary_file = output_root / "candidate_evidence_gap_summary.jsonl"
    assert gap_summary_file.exists()
    lines = gap_summary_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_evidence_gap_summary_shape(data)
    _assert_candidate_evidence_gap_summary_shape(
        payload["candidate_evidence_gap_summary"]
    )
    assert data == payload["candidate_evidence_gap_summary"]
    assert payload["candidate_evidence_gap_summary_path"].endswith(
        "candidate_evidence_gap_summary.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_evidence_gap_summary"] == data
    assert record["candidate_evidence_gap_summary"] == data
    assert "candidate_evidence_gap_summary" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_evidence_gap_summary"][
        "path"
    ].endswith("candidate_evidence_gap_summary.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    for markdown in (brief, handoff):
        assert "## Candidate Evidence Gap Summary" in markdown
        assert "candidate_evidence_gap_summary.jsonl" in markdown
        assert "offline_candidate_evidence_gap_summary_only" in markdown
        assert "build_candidate_gap_closure_queue" in markdown
    assert "Candidate strategy implementation remains blocked" in brief
    assert "compared against the baseline" in handoff

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["candidate_evidence_gap_summary"] == data
    assert payload["work_order_exports"]["candidate_evidence_gap_summary"] == data
    assert data["gap_summary_status"] == "ready"
    assert (
        data["gap_summary_mode"]
        == "offline_candidate_evidence_gap_summary_only"
    )
    assert data["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert data["baseline_strategy_role"] == "control_harness"
    assert data["candidate_gap_summaries"]
    assert data["ranked_gap_groups"]
    assert data["highest_priority_gaps"]
    assert data["shared_gap_summary"]
    assert data["gap_counts"]
    assert data["next_gap_closure_actions"]
    assert data["selected_next_safe_action"] == "build_candidate_gap_closure_queue"
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["safety_scope"] == "offline_only"
    assert data["paper_submit_authorized"] is False
    assert data["profit_claim"] == "none"
    assert data["daniel_action_required_now"] is False
    assert "candidate_evidence_gap_summary_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_gap_closure_queue(
    tmp_path: Path,
) -> None:
    """Verify v1.20 candidate gap closure queue artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_gap_queue_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    queue_file = output_root / "candidate_gap_closure_queue.jsonl"
    assert queue_file.exists()
    lines = queue_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_gap_closure_queue_shape(data)
    _assert_candidate_gap_closure_queue_shape(
        payload["candidate_gap_closure_queue"]
    )
    assert data == payload["candidate_gap_closure_queue"]
    assert payload["candidate_gap_closure_queue_path"].endswith(
        "candidate_gap_closure_queue.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_gap_closure_queue"] == data
    assert record["candidate_gap_closure_queue"] == data
    assert "candidate_gap_closure_queue" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_gap_closure_queue"][
        "path"
    ].endswith("candidate_gap_closure_queue.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    for markdown in (brief, handoff):
        assert "## Candidate Gap Closure Queue" in markdown
        assert "candidate_gap_closure_queue.jsonl" in markdown
        assert "offline_candidate_gap_closure_queue_only" in markdown
        assert "candidate_gap_closure_queue_item_001" in markdown
        assert "execute_candidate_gap_closure_queue_item_001" in markdown
        assert "broker_state_not_observed" in markdown
        assert "profit_claim=none" in markdown

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["candidate_gap_closure_queue"] == data
    assert payload["work_order_exports"]["candidate_gap_closure_queue"] == data
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert data["queue_status"] == "ready"
    assert data["queue_mode"] == "offline_candidate_gap_closure_queue_only"
    assert data["queue_item_count"] > 0
    assert data["selected_queue_item_id"] == (
        "candidate_gap_closure_queue_item_001"
    )
    assert data["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_001"
    )
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["broker_state_observed"] is False
    assert data["paper_submit_authorized"] is False
    assert data["daniel_action_required_now"] is False
    assert data["profit_claim"] == "none"
    assert "candidate_gap_closure_queue_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_risk_rule_status(
    tmp_path: Path,
) -> None:
    """Verify v1.23 item-003 candidate risk-rule status artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_risk_rule_status_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    status_file = output_root / "candidate_risk_rule_status.jsonl"
    assert status_file.exists()
    lines = status_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_risk_rule_status_shape(data)
    _assert_candidate_risk_rule_status_shape(
        payload["candidate_risk_rule_status"]
    )
    assert data == payload["candidate_risk_rule_status"]
    assert payload["candidate_risk_rule_status_path"].endswith(
        "candidate_risk_rule_status.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_risk_rule_status"] == data
    assert record["candidate_risk_rule_status"] == data
    assert "candidate_risk_rule_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_risk_rule_status"][
        "path"
    ].endswith("candidate_risk_rule_status.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    for markdown in (brief, handoff):
        assert "## Candidate Risk Rule Status" in markdown
        assert "candidate_risk_rule_status.jsonl" in markdown
        assert "offline_candidate_risk_rule_status_only" in markdown
        assert "candidate_gap_closure_queue_item_003" in markdown
        assert "volatility_or_regime_filter_candidate" in markdown
        assert "candidate_risk_rule_status" in markdown
        assert "execute_candidate_gap_closure_queue_item_004" in markdown
        assert "## Candidate Signal Rule Status" in markdown
        assert "candidate_signal_rule_status.jsonl" in markdown
        assert "offline_candidate_signal_rule_status_only" in markdown
        assert "candidate_gap_closure_queue_item_006" in markdown
        assert "volatility_or_regime_filter_candidate" in markdown
        assert "candidate_signal_rule_status" in markdown
        assert "execute_candidate_gap_closure_queue_item_007" in markdown
        assert "## Shared Risk Rule Status" in markdown
        assert "shared_risk_rule_status.jsonl" in markdown
        assert "candidate_gap_closure_queue_item_007" in markdown
        assert "risk_rule_status" in markdown
        assert "execute_candidate_gap_closure_queue_item_008" in markdown
        assert "broker_state_not_observed" in markdown
        assert "paper_submit_authorized" in markdown
        assert "profit_claim" in markdown

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["candidate_risk_rule_status"] == data
    assert payload["work_order_exports"]["candidate_risk_rule_status"] == data
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert data["risk_rule_status"] == "ready"
    assert data["risk_rule_status_mode"] == (
        "offline_candidate_risk_rule_status_only"
    )
    assert data["source_queue_item_id"] == "candidate_gap_closure_queue_item_003"
    assert data["source_action_id"] == "execute_candidate_gap_closure_queue_item_003"
    assert data["source_gap_id"] == "candidate_risk_rule_status"
    assert (
        data["source_candidate_family_id"]
        == "volatility_or_regime_filter_candidate"
    )
    assert data["source_expected_evidence_artifact"] == (
        "candidate_risk_rule_status.jsonl"
    )
    assert data["candidate_family_count"] == 3
    assert data["candidate_scope_count"] == 3
    assert data["target_candidate_risk_rule_summary"]["candidate_family_id"] == (
        "volatility_or_regime_filter_candidate"
    )
    incomplete_count = sum(
        1
        for item in data["candidate_risk_rule_summaries"]
        if item["risk_rule_status"] == "incomplete"
    )
    assert incomplete_count == 3
    blocked_count = sum(
        1
        for item in data["candidate_risk_rule_summaries"]
        if item["risk_rule_evidence_status"] == "blocked"
    )
    assert blocked_count == 3
    assert data["evidence_status_summary"]["blocked"] == 3
    assert data["evidence_status_summary"]["missing_evidence_explicit"] is True
    assert data["highest_priority_risk_rule_gaps"]
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["paper_submit_authorized"] is False
    assert data["daniel_action_required_now"] is False
    assert data["profit_claim"] == "none"
    assert data["safety_scope"] == "offline_only"
    assert "candidate_risk_rule_status_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_signal_rule_status(
    tmp_path: Path,
) -> None:
    """Verify v1.26 item-006 candidate signal-rule status artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_signal_rule_status_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    status_file = output_root / "candidate_signal_rule_status.jsonl"
    assert status_file.exists()
    lines = status_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_signal_rule_status_shape(data)
    _assert_candidate_signal_rule_status_shape(
        payload["candidate_signal_rule_status"]
    )
    assert data == payload["candidate_signal_rule_status"]
    assert payload["candidate_signal_rule_status_path"].endswith(
        "candidate_signal_rule_status.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_signal_rule_status"] == data
    assert record["candidate_signal_rule_status"] == data
    assert "candidate_signal_rule_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_signal_rule_status"][
        "path"
    ].endswith("candidate_signal_rule_status.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    for markdown in (brief, handoff):
        assert "## Candidate Signal Rule Status" in markdown
        assert "candidate_signal_rule_status.jsonl" in markdown
        assert "offline_candidate_signal_rule_status_only" in markdown
        assert "candidate_gap_closure_queue_item_006" in markdown
        assert "volatility_or_regime_filter_candidate" in markdown
        assert "candidate_signal_rule_status" in markdown
        assert "execute_candidate_gap_closure_queue_item_007" in markdown
        assert "## Shared Risk Rule Status" in markdown
        assert "shared_risk_rule_status.jsonl" in markdown
        assert "candidate_gap_closure_queue_item_007" in markdown
        assert "risk_rule_status" in markdown
        assert "execute_candidate_gap_closure_queue_item_008" in markdown
        assert "broker_state_not_observed" in markdown
        assert "paper_submit_authorized" in markdown
        assert "profit_claim" in markdown

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["candidate_signal_rule_status"] == data
    assert payload["work_order_exports"]["candidate_signal_rule_status"] == data
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert data["signal_rule_status"] == "ready"
    assert data["signal_rule_status_mode"] == (
        "offline_candidate_signal_rule_status_only"
    )
    assert data["source_queue_item_id"] == "candidate_gap_closure_queue_item_006"
    assert data["source_action_id"] == "execute_candidate_gap_closure_queue_item_006"
    assert data["source_gap_id"] == "candidate_signal_rule_status"
    assert (
        data["source_candidate_family_id"]
        == "volatility_or_regime_filter_candidate"
    )
    assert data["source_expected_evidence_artifact"] == (
        "candidate_signal_rule_status.jsonl"
    )
    assert data["candidate_family_count"] == 3
    assert data["candidate_scope_count"] == 3
    assert data["target_candidate_signal_rule_summary"]["candidate_family_id"] == (
        "volatility_or_regime_filter_candidate"
    )
    assert data["target_explicit_signal_rule_evidence"][
        "explicit_signal_rules_present"
    ] is False
    assert data["target_materialized_candidate_signal_specification"][
        "materialized_signal_rules"
    ] == []
    assert data["target_remaining_missing_signal_rule_evidence"]
    assert data["target_candidate_signal_readiness"]["readiness_status"] == "blocked"
    incomplete_count = sum(
        1
        for item in data["candidate_signal_rule_summaries"]
        if item["signal_rule_status"] == "incomplete"
    )
    assert incomplete_count == 3
    blocked_count = sum(
        1
        for item in data["candidate_signal_rule_summaries"]
        if item["signal_rule_evidence_status"] == "blocked"
    )
    assert blocked_count == 3
    assert data["evidence_status_summary"]["blocked"] == 3
    assert data["evidence_status_summary"]["missing_evidence_explicit"] is True
    assert data["highest_priority_signal_rule_gaps"]
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["paper_submit_authorized"] is False
    assert data["daniel_action_required_now"] is False
    assert data["profit_claim"] == "none"
    assert data["safety_scope"] == "offline_only"
    assert "candidate_signal_rule_status_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_shared_risk_rule_status(
    tmp_path: Path,
) -> None:
    """Verify v1.27 item-007 shared risk-rule status artifact and wiring."""
    output_root = tmp_path / "paper_lab_shared_risk_rule_status_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    status_file = output_root / "shared_risk_rule_status.jsonl"
    assert status_file.exists()
    lines = status_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_shared_risk_rule_status_shape(data)
    _assert_shared_risk_rule_status_shape(payload["shared_risk_rule_status"])
    assert data == payload["shared_risk_rule_status"]
    assert payload["shared_risk_rule_status_path"].endswith(
        "shared_risk_rule_status.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["shared_risk_rule_status"] == data
    assert record["shared_risk_rule_status"] == data
    assert "shared_risk_rule_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["shared_risk_rule_status"][
        "path"
    ].endswith("shared_risk_rule_status.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    for markdown in (brief, handoff):
        assert "## Shared Risk Rule Status" in markdown
        assert "shared_risk_rule_status.jsonl" in markdown
        assert "offline_shared_risk_rule_status_only" in markdown
        assert "candidate_gap_closure_queue_item_007" in markdown
        assert "risk_rule_status" in markdown
        assert "shared" in markdown
        assert "execute_candidate_gap_closure_queue_item_008" in markdown
        assert "broker_state_not_observed" in markdown
        assert "paper_submit_authorized" in markdown
        assert "profit_claim" in markdown

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["shared_risk_rule_status"] == data
    assert payload["work_order_exports"]["shared_risk_rule_status"] == data
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert payload["next_action_selector"]["selected_research_candidate_id"] is None
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    assert "candidate_backtest_result_packet_ready" in payload["next_action_selector"][
        "reason_codes"
    ]
    assert data["source_queue_item_id"] == "candidate_gap_closure_queue_item_007"
    assert data["source_action_id"] == "execute_candidate_gap_closure_queue_item_007"
    assert data["source_gap_id"] == "risk_rule_status"
    assert data["source_candidate_family_id"] == "shared"
    assert data["source_expected_evidence_artifact"] == (
        "shared_risk_rule_status.jsonl"
    )
    assert data["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_008"
    )
    assert data["explicit_shared_risk_rule_evidence"][
        "explicit_risk_rules_present"
    ] is False
    assert data["materialized_shared_risk_specification"][
        "materialized_risk_rules"
    ] == []
    assert data["materialized_shared_risk_specification"][
        "position_sizing_rules"
    ] == []
    assert data["materialized_shared_risk_specification"][
        "stop_or_exit_rules"
    ] == []
    assert data["remaining_missing_shared_risk_evidence"]
    assert data["target_shared_risk_readiness"]["readiness_status"] == "blocked"
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["paper_submit_authorized"] is False
    assert data["daniel_action_required_now"] is False
    assert data["profit_claim"] == "none"
    assert data["safety_scope"] == "offline_only"
    assert "shared_risk_rule_status_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_shared_signal_rule_status(
    tmp_path: Path,
) -> None:
    """Verify v1.28 item-008 shared signal-rule status artifact and wiring."""
    output_root = tmp_path / "paper_lab_shared_signal_rule_status_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    status_file = output_root / "shared_signal_rule_status.jsonl"
    assert status_file.exists()
    lines = status_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_shared_signal_rule_status_shape(data)
    _assert_shared_signal_rule_status_shape(payload["shared_signal_rule_status"])
    assert data == payload["shared_signal_rule_status"]
    assert payload["shared_signal_rule_status_path"].endswith(
        "shared_signal_rule_status.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["shared_signal_rule_status"] == data
    assert record["shared_signal_rule_status"] == data
    assert "shared_signal_rule_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["shared_signal_rule_status"][
        "path"
    ].endswith("shared_signal_rule_status.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    for markdown in (brief, handoff):
        assert "## Shared Signal Rule Status" in markdown
        assert "shared_signal_rule_status.jsonl" in markdown
        assert "offline_shared_signal_rule_status_only" in markdown
        assert "candidate_gap_closure_queue_item_008" in markdown
        assert "signal_rule_status" in markdown
        assert "shared" in markdown
        assert "execute_candidate_gap_closure_queue_item_009" in markdown
        assert "broker_state_not_observed" in markdown
        assert "paper_submit_authorized" in markdown
        assert "profit_claim" in markdown

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["shared_signal_rule_status"] == data
    assert payload["work_order_exports"]["shared_signal_rule_status"] == data
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert payload["next_action_selector"]["selected_research_candidate_id"] is None
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    assert "candidate_backtest_result_packet_ready" in payload["next_action_selector"][
        "reason_codes"
    ]
    assert data["source_queue_item_id"] == "candidate_gap_closure_queue_item_008"
    assert data["source_action_id"] == "execute_candidate_gap_closure_queue_item_008"
    assert data["source_gap_id"] == "signal_rule_status"
    assert data["source_candidate_family_id"] == "shared"
    assert data["source_expected_evidence_artifact"] == (
        "shared_signal_rule_status.jsonl"
    )
    assert data["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_009"
    )
    assert "shared_signal_rule_status_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_shared_benchmark_comparison_status(
    tmp_path: Path,
) -> None:
    """Verify v1.29 item-009 shared benchmark-comparison status artifact and wiring."""
    output_root = tmp_path / "paper_lab_shared_benchmark_comparison_status_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    status_file = output_root / "shared_benchmark_comparison_status.jsonl"
    assert status_file.exists()
    lines = status_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_shared_benchmark_comparison_status_shape(data)
    _assert_shared_benchmark_comparison_status_shape(payload["shared_benchmark_comparison_status"])
    assert data == payload["shared_benchmark_comparison_status"]
    assert payload["shared_benchmark_comparison_status_path"].endswith(
        "shared_benchmark_comparison_status.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["shared_benchmark_comparison_status"] == data
    assert record["shared_benchmark_comparison_status"] == data
    assert "shared_benchmark_comparison_status" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["shared_benchmark_comparison_status"][
        "path"
    ].endswith("shared_benchmark_comparison_status.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    for markdown in (brief, handoff):
        assert "## Shared Benchmark Comparison Status" in markdown
        assert "shared_benchmark_comparison_status.jsonl" in markdown
        assert "offline_shared_benchmark_comparison_status_only" in markdown
        assert "candidate_gap_closure_queue_item_009" in markdown
        assert "benchmark_comparison_status" in markdown
        assert "shared" in markdown
        assert "execute_candidate_gap_closure_queue_item_010" in markdown
        assert "broker_state_not_observed" in markdown
        assert "paper_submit_authorized" in markdown
        assert "profit_claim" in markdown

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["shared_benchmark_comparison_status"] == data
    assert payload["work_order_exports"]["shared_benchmark_comparison_status"] == data
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert payload["next_action_selector"]["selected_research_candidate_id"] is None
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    assert "candidate_backtest_result_packet_ready" in payload["next_action_selector"][
        "reason_codes"
    ]
    assert data["source_queue_item_id"] == "candidate_gap_closure_queue_item_009"
    assert data["source_action_id"] == "execute_candidate_gap_closure_queue_item_009"
    assert data["source_gap_id"] == "benchmark_comparison_status"
    assert data["source_candidate_family_id"] == "shared"
    assert data["source_expected_evidence_artifact"] == (
        "shared_benchmark_comparison_status.jsonl"
    )
    assert data["selected_next_safe_action"] == (
        "execute_candidate_gap_closure_queue_item_010"
    )
    assert "shared_benchmark_comparison_status_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_strategy_evidence_template(
    tmp_path: Path,
) -> None:
    """Verify v1.15 candidate strategy evidence template artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_template_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    template_file = output_root / "candidate_strategy_evidence_template.jsonl"
    assert template_file.exists()
    lines = template_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_strategy_evidence_template_shape(data)
    _assert_candidate_strategy_evidence_template_shape(
        payload["candidate_strategy_evidence_template"]
    )
    assert data == payload["candidate_strategy_evidence_template"]
    assert payload["candidate_strategy_evidence_template_path"].endswith(
        "candidate_strategy_evidence_template.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_strategy_evidence_template"] == data
    assert record["candidate_strategy_evidence_template"] == data
    assert "candidate_strategy_evidence_template" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_strategy_evidence_template"][
        "path"
    ].endswith("candidate_strategy_evidence_template.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    assert "## Candidate Strategy Evidence Template" in brief
    assert "## Candidate Strategy Evidence Template" in handoff
    assert "candidate_strategy_evidence_template.jsonl" in brief
    assert "candidate_strategy_evidence_template.jsonl" in handoff
    assert "offline_strategy_evidence_template_only" in brief
    assert "materialize_candidate_evidence_requirements" in handoff

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert (
        payload["next_action_selector"]["candidate_strategy_evidence_template"]
        == data
    )
    assert (
        payload["work_order_exports"]["candidate_strategy_evidence_template"]
        == data
    )
    assert data["template_status"] == "ready"
    assert data["evidence_mode"] == "offline_strategy_evidence_template_only"
    assert data["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["safety_scope"] == "offline_only"
    assert data["paper_submit_authorized"] is False
    assert data["profit_claim"] == "none"
    assert data["daniel_action_required_now"] is False
    assert payload["quality_gate_status"] == "pass"
    assert "candidate_strategy_evidence_template_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_evidence_requirements(
    tmp_path: Path,
) -> None:
    """Verify v1.16 candidate evidence requirements artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_requirements_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2024-10-18",
            symbol="SPY",
        )
    )

    requirements_file = output_root / "candidate_evidence_requirements.jsonl"
    assert requirements_file.exists()
    lines = requirements_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_evidence_requirements_shape(data)
    _assert_candidate_evidence_requirements_shape(
        payload["candidate_evidence_requirements"]
    )
    assert data == payload["candidate_evidence_requirements"]
    assert payload["candidate_evidence_requirements_path"].endswith(
        "candidate_evidence_requirements.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_evidence_requirements"] == data
    assert record["candidate_evidence_requirements"] == data
    assert "candidate_evidence_requirements" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_evidence_requirements"][
        "path"
    ].endswith("candidate_evidence_requirements.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    assert "## Candidate Evidence Requirements" in brief
    assert "## Candidate Evidence Requirements" in handoff
    assert "candidate_evidence_requirements.jsonl" in brief
    assert "candidate_evidence_requirements.jsonl" in handoff
    assert "offline_candidate_evidence_requirements_only" in brief
    assert "build_candidate_evidence_collection_plan" in handoff

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert (
        payload["next_action_selector"]["candidate_evidence_requirements"]
        == data
    )
    assert payload["work_order_exports"]["candidate_evidence_requirements"] == data
    assert data["requirements_status"] == "ready"
    assert (
        data["requirements_mode"]
        == "offline_candidate_evidence_requirements_only"
    )
    assert data["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert data["broker_state_mode"] == "broker_state_not_observed"
    assert data["safety_scope"] == "offline_only"
    assert data["paper_submit_authorized"] is False
    assert data["profit_claim"] == "none"
    assert data["daniel_action_required_now"] is False
    assert "candidate_evidence_requirements_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"


def test_etf_sma_daily_paper_lab_candidate_backtest_outputs_status(
    tmp_path: Path,
) -> None:
    """Verify v1.31 candidate backtest result packet status artifact and wiring."""
    output_root = tmp_path / "paper_lab_candidate_backtest_result_packet_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    status_file = output_root / "candidate_backtest_result_packet.jsonl"
    assert status_file.exists()
    lines = status_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])

    _assert_candidate_backtest_result_packet_shape(data)
    _assert_candidate_backtest_result_packet_shape(payload["candidate_backtest_result_packet"])
    assert data == payload["candidate_backtest_result_packet"]
    assert payload["candidate_backtest_result_packet_path"].endswith(
        "candidate_backtest_result_packet.jsonl"
    )

    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8")
    )
    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(encoding="utf-8")
    )
    assert manifest["candidate_backtest_result_packet"] == data
    assert record["candidate_backtest_result_packet"] == data
    assert "candidate_backtest_result_packet" in manifest["indexed_artifacts"]
    assert manifest["indexed_artifacts"]["candidate_backtest_result_packet"][
        "path"
    ].endswith("candidate_backtest_result_packet.jsonl")

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    handoff = (output_root / "review_handoff.md").read_text(encoding="utf-8")
    for markdown in (brief, handoff):
        assert "## Candidate Backtest Result Packet" in markdown
        assert "candidate_backtest_result_packet.jsonl" in markdown
        assert "offline_candidate_backtest_result_packet_only" in markdown
        assert "candidate_gap_closure_queue_item_012" in markdown
        assert "candidate_backtest_outputs_status" in markdown
        assert "volatility_or_regime_filter_candidate" in markdown
        assert _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION in markdown
        assert "broker_state_not_observed" in markdown
        assert "paper_submit_authorized" in markdown
        assert "profit_claim" in markdown

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["candidate_backtest_result_packet"] == data
    assert payload["work_order_exports"]["candidate_backtest_result_packet"] == data
    assert payload["next_action_selector"]["status"] == (
        "candidate_backtest_result_packet_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert payload["next_action_selector"]["selected_research_candidate_id"] is None
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    assert "candidate_backtest_result_packet_ready" in payload["next_action_selector"][
        "reason_codes"
    ]
    assert data["source_queue_item_id"] == "candidate_gap_closure_queue_item_012"
    assert data["source_action_id"] == "execute_candidate_gap_closure_queue_item_012"
    assert data["source_gap_id"] == "candidate_backtest_outputs_status"
    assert (
        data["source_candidate_family_id"]
        == "volatility_or_regime_filter_candidate"
    )
    assert data["source_expected_evidence_artifact"] == (
        "candidate_backtest_result_packet.jsonl"
    )
    assert data["selected_next_safe_action"] == (
        _CANDIDATE_BACKTEST_TERMINAL_NEXT_ACTION
    )
    assert "candidate_backtest_result_packet_generated" not in payload[
        "quality_gate_failed_checks"
    ]
    validation_result = validate_etf_sma_daily_paper_lab_packet(
        output_root,
        packet=payload,
    )
    assert validation_result["validation_status"] == "pass"
