from __future__ import annotations

import json
import os
import shutil
import hashlib
from pathlib import Path
import pytest

import algotrader.cli as cli_module
import algotrader.execution.etf_sma_daily_paper_lab as paper_lab_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_paper_lab import (
    EtfSmaDailyPaperLabConfig,
    build_etf_sma_daily_paper_lab,
    run_etf_sma_daily_paper_lab,
    validate_etf_sma_daily_paper_lab_packet,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"


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
        "assistant_v1.22_candidate_risk_rule_status"
    )
    assert status["risk_rule_status"] == "ready"
    assert status["risk_rule_status_mode"] == (
        "offline_candidate_risk_rule_status_only"
    )
    assert status["baseline_strategy_id"] == "spy_sma_50_200_control"
    assert status["source_queue_item_id"] == "candidate_gap_closure_queue_item_002"
    assert status["source_action_id"] == "execute_candidate_gap_closure_queue_item_002"
    assert status["source_gap_id"] == "candidate_risk_rule_status"
    assert status["source_candidate_family_id"] == "mean_reversion_candidate"
    assert status["source_candidate_family"] == "Mean reversion candidate"
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
        "execute_candidate_gap_closure_queue_item_003"
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
        "mean_reversion_candidate"
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
        "execute_candidate_gap_closure_queue_item_003"
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
        "33/33 required checks passed; 0 failed; 0 warnings"
    )
    assert container["quality_gate_passed_required_count"] == 33
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
    _assert_next_action_selector_shape(payload["next_action_selector"])
    assert payload["next_action_selector"]["status"] == (
        "candidate_risk_rule_status_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        "execute_candidate_gap_closure_queue_item_003"
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
    assert "execute_candidate_gap_closure_queue_item_002" in brief
    assert "mean_reversion_candidate" in brief
    assert "execute_candidate_gap_closure_queue_item_003" in brief
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
    assert "execute_candidate_gap_closure_queue_item_003" in brief
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
            "Assistant v1.22 - Candidate Risk Rule Status Artifact"
            in work_order
        )
        assert "execute_candidate_gap_closure_queue_item_001" in work_order
        assert "execute_candidate_gap_closure_queue_item_002" in work_order
        assert "execute_candidate_gap_closure_queue_item_003" in work_order
        assert "research_candidate_queue.jsonl" in work_order
        assert "baseline_health_evaluation.jsonl" in work_order
        assert "baseline_evidence_metrics.jsonl" in work_order
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
    _assert_next_action_selector_shape(payload["next_action_selector"])
    assert payload["review_classification"] == "accepted"
    assert payload["next_action_selector"]["status"] == (
        "candidate_risk_rule_status_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        "execute_candidate_gap_closure_queue_item_003"
    )
    assert payload["next_action_selector"]["selected_research_candidate_id"] is None
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    assert payload["next_action_selector"]["broker_action_allowed"] is False
    assert payload["next_action_selector"]["llm_runtime_calls_allowed"] is False
    assert "candidate_risk_rule_status_ready" in payload["next_action_selector"][
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
        "21/33 required checks passed; 12 failed; 0 warnings"
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
        "candidate_risk_rule_status_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        "execute_candidate_gap_closure_queue_item_003"
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
    """Verify v1.22 item-002 candidate risk-rule status artifact and wiring."""
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
        assert "candidate_gap_closure_queue_item_002" in markdown
        assert "mean_reversion_candidate" in markdown
        assert "candidate_risk_rule_status" in markdown
        assert "execute_candidate_gap_closure_queue_item_003" in markdown
        assert "broker_state_not_observed" in markdown
        assert "paper_submit_authorized" in markdown
        assert "profit_claim" in markdown

    _assert_next_action_selector_shape(payload["next_action_selector"])
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["next_action_selector"]["candidate_risk_rule_status"] == data
    assert payload["work_order_exports"]["candidate_risk_rule_status"] == data
    assert payload["next_action_selector"]["status"] == (
        "candidate_risk_rule_status_next_action_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        "execute_candidate_gap_closure_queue_item_003"
    )
    assert data["risk_rule_status"] == "ready"
    assert data["risk_rule_status_mode"] == (
        "offline_candidate_risk_rule_status_only"
    )
    assert data["source_queue_item_id"] == "candidate_gap_closure_queue_item_002"
    assert data["source_action_id"] == "execute_candidate_gap_closure_queue_item_002"
    assert data["source_gap_id"] == "candidate_risk_rule_status"
    assert data["source_candidate_family_id"] == "mean_reversion_candidate"
    assert data["source_expected_evidence_artifact"] == (
        "candidate_risk_rule_status.jsonl"
    )
    assert data["candidate_family_count"] == 3
    assert data["candidate_scope_count"] == 3
    assert data["target_candidate_risk_rule_summary"]["candidate_family_id"] == (
        "mean_reversion_candidate"
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
