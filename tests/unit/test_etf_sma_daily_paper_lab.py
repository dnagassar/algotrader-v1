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
        "candidates",
    }
    assert queue["research_candidate_queue_version"] == (
        "assistant_v1.7_research_candidate_queue"
    )
    assert queue["status"] == "generated"
    assert str(queue["artifact_path"]).endswith("research_candidate_queue.jsonl")
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
        "19/19 required checks passed; 0 failed; 0 warnings"
    )
    assert container["quality_gate_passed_required_count"] == 19
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
    _assert_next_action_selector_shape(payload["next_action_selector"])
    assert payload["next_action_selector"]["status"] == (
        "operator_support_review_ingest_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        "collect_offline_review_feedback"
    )
    assert payload["next_action_selector"]["selected_work_order"] == (
        "gpt_next_action_handoff"
    )
    assert payload["next_action_selector"]["priority"] == "P1"
    assert payload["next_action_selector"]["selected_research_candidate_id"] == (
        "offline_review_evidence_gap"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    _assert_work_order_exports_shape(payload["work_order_exports"])
    assert payload["work_order_exports"]["selected_research_candidate_id"] == (
        "offline_review_evidence_gap"
    )
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
        "baseline_health_evaluation_spy_sma_50_200"
    )
    assert queue["selected_safe_candidate_priority"] == "P2"
    candidate_ids = [
        candidate["candidate_id"] for candidate in queue["candidates"]
    ]
    assert candidate_ids == [
        "offline_review_evidence_gap",
        "baseline_health_evaluation_spy_sma_50_200",
        "benchmark_buy_and_hold_comparison_spy",
        "current_baseline_evidence_gap_map",
        "paper_lab_observation_readiness",
        "future_non_sma_strategy_research_slot",
        "strategy_candidate_intake_requirements",
    ]

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
    assert (output_root / "research_candidate_queue.jsonl").exists()
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
    assert "offline_review_evidence_gap" in brief
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
    assert "collect_offline_review_feedback" in brief
    assert "Work order exports" in brief
    assert "work_orders/gpt_next_action_handoff.md" in brief
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
    assert record["next_action_selector"] == payload["next_action_selector"]
    assert record["work_order_exports"] == payload["work_order_exports"]
    assert record["research_candidate_queue_version"] == (
        "assistant_v1.7_research_candidate_queue"
    )
    assert record["research_candidate_queue_path"].endswith(
        "research_candidate_queue.jsonl"
    )
    assert record["research_candidate_queue"] == payload["research_candidate_queue"]
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
        assert "Assistant v1.7 - Research Candidate Evidence Queue" in work_order
        assert "collect_offline_review_feedback" in work_order
        assert "research_candidate_queue.jsonl" in work_order
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
        "safe_offline_research_candidate_selected"
    )
    assert payload["next_action_selector"]["selected_next_action_id"] == (
        "baseline_health_evaluation_spy_sma_50_200"
    )
    assert payload["next_action_selector"]["selected_research_candidate_id"] == (
        "baseline_health_evaluation_spy_sma_50_200"
    )
    assert payload["next_action_selector"]["selected_work_order"] == (
        "codex_work_order"
    )
    assert payload["next_action_selector"]["blocks_offline_build"] is False
    assert payload["next_action_selector"]["broker_action_allowed"] is False
    assert payload["next_action_selector"]["llm_runtime_calls_allowed"] is False


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
        "16/19 required checks passed; 3 failed; 0 warnings"
    )
    assert validation["quality_gate_failed_checks"] == [
        "required_packet_artifacts_exist",
        "required_operating_record_fields_exist",
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
