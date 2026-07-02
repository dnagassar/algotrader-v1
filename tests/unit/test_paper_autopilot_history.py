from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess

from algotrader.execution.paper_autopilot_history import (
    PaperAutopilotHistoryConfig,
    paper_autopilot_history_exit_status,
    render_paper_autopilot_history_status,
    update_paper_autopilot_operating_history,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORY_MODULE = (
    PROJECT_ROOT / "src" / "algotrader" / "execution" / "paper_autopilot_history.py"
)


def test_healthy_broker_observed_hold_noop_classification(tmp_path: Path) -> None:
    rollup = _update_history(tmp_path, _base_status())

    assert rollup["classification"] == "healthy_hold_noop"
    assert rollup["autonomy_status"] == "healthy_continue_next_daily_cycle"
    assert rollup["autonomy_next_action"] == "continue_next_daily_cycle"
    assert rollup["readiness_status"] == "no_mutation_needed_continue"
    assert rollup["readiness_blockers"] == []
    assert rollup["required_operator_action"] == "continue_next_daily_cycle"
    assert rollup["readiness_packet_generated"] is False
    assert rollup["changed_since_previous"] is False
    assert "risk_on_spy_position_already_held" in rollup["reason_codes"]
    assert rollup["operating_mode"] == "bounded_paper_mutation"
    assert rollup["latest_bar_date"] == "2026-08-08"
    assert rollup["data_refresh_status"] == "no_refresh_required"
    assert rollup["data_freshness_status"] == "accepted_data_current"
    assert rollup["broker_read_performed"] is True
    assert rollup["expected_account_matched"] is True
    assert rollup["spy_position_observed"] is True
    assert rollup["spy_position_quantity"] == "0.05"
    assert rollup["open_spy_orders_observed"] == 0
    assert rollup["unexpected_non_spy_positions_count"] == 0
    assert rollup["unexpected_non_spy_positions"] == []
    assert rollup["selected_strategy_id"] == "spy_sma_50_200_training_wheel"
    assert rollup["strategy_route_action"] == "hold"
    assert rollup["execution_plan_action"] == "hold"
    assert rollup["vol_scaled_preview_visible"] is True
    assert rollup["vol_scaled_preview_intended_action"] == "buy"
    assert rollup["vol_scaled_preview_mutation_allowed"] is False
    assert rollup["vol_scaled_preview_submit_allowed"] is False
    assert (
        rollup["vol_scaled_preview_non_mutation_status"]
        == "preview_only_non_mutating"
    )
    assert rollup["final_supervisor_status"] == "none"
    assert rollup["broker_observed_supervisor_status"] == "none"
    assert rollup["final_supervisor_classification"] == (
        "no_action_required_no_mutation"
    )
    assert rollup["final_operator_action"] == "continue_next_daily_cycle"
    assert rollup["attention_required"] is False
    assert rollup["hard_stop"] is False
    assert paper_autopilot_history_exit_status(rollup) == 0
    rendered = render_paper_autopilot_history_status(rollup)
    assert "classification=healthy_hold_noop" in rendered
    assert "autonomy_status=healthy_continue_next_daily_cycle" in rendered
    assert "autonomy_next_action=continue_next_daily_cycle" in rendered
    assert "readiness_status=no_mutation_needed_continue" in rendered
    assert "readiness_packet_generated=false" in rendered
    assert "changed_since_previous=false" in rendered
    assert "latest_bar_date=2026-08-08" in rendered
    assert "data_refresh_status=no_refresh_required" in rendered
    assert "expected_account_matched=true" in rendered
    assert "spy_position_quantity=0.05" in rendered
    assert "selected_strategy_id=spy_sma_50_200_training_wheel" in rendered
    assert "execution_plan_action=hold" in rendered
    assert "vol_scaled_preview_intended_action=buy" in rendered
    assert "vol_scaled_preview_non_mutation_status=preview_only_non_mutating" in rendered
    assert "final_supervisor_status=none" in rendered
    assert "latest_rollup=" in rendered
    _assert_history_artifacts(rollup)


def test_healthy_paper_action_with_confirmed_reconciliation(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status.update(
        {
            "blocker_status": "action/submitted",
            "preview_action_decision": "paper_buy_allowed",
            "paper_submit_authorized": True,
            "paper_submit_performed": True,
            "broker_mutation_performed": True,
            "reconciliation_status": "reconciled_submit_observed",
            "next_operator_action": "review_latest_status_and_next_reconciliation_cycle",
        }
    )
    status["execution_plan_summary"].update(
        {"action": "buy", "paper_submit_authorized": True, "submit_allowed": True}
    )
    status["reconciliation"] = {
        "reconciliation_required": False,
        "reconciliation_status": "reconciled_submit_observed",
    }

    rollup = _update_history(tmp_path, status)

    assert rollup["classification"] == "healthy_paper_action_reconciled"
    assert rollup["autonomy_status"] == "healthy_continue_next_daily_cycle"
    assert rollup["attention_required"] is False
    assert rollup["paper_submit_performed"] is True


def test_risk_off_without_spy_position_is_healthy_noop_with_distinct_reason(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status.update(
        {
            "sma_posture": "risk_off",
            "spy_position_observed": False,
            "spy_position_quantity": "0",
            "preview_action_decision": "hold/noop",
        }
    )
    status["broker_state"].update(
        {
            "spy_position_present": False,
            "spy_position_quantity": "0",
        }
    )

    rollup = _update_history(tmp_path, status)

    assert rollup["autonomy_status"] == "healthy_continue_next_daily_cycle"
    assert "risk_off_no_spy_position_noop" in rollup["reason_codes"]


def test_no_submit_mutation_required_generates_readiness_packet(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status.update(
        {
            "operating_mode": "visibility/no_submit",
            "no_submit_mode": True,
            "spy_position_observed": False,
            "spy_position_quantity": "0",
            "strategy_route_action": "buy",
            "execution_plan_action": "buy",
            "intended_mutation_action": "buy",
            "mutation_would_be_required_without_no_submit": True,
            "preview_action_decision": "paper_buy_blocked_no_submit_mode",
            "blocker_status": "blocked/mutation_would_be_required_no_submit_mode",
            "final_supervisor_status": (
                "blocked/mutation_would_be_required_no_submit_mode"
            ),
            "broker_observed_supervisor_status": (
                "blocked/mutation_would_be_required_no_submit_mode"
            ),
            "final_supervisor_classification": (
                "mutation_would_be_required_no_submit_mode"
            ),
            "paper_submit_authorized": False,
            "next_operator_action": (
                "review_visibility_only_intended_action_no_submit_mode"
            ),
            "final_operator_action": (
                "review_visibility_only_intended_action_no_submit_mode"
            ),
        }
    )
    status["broker_state"].update(
        {
            "spy_position_present": False,
            "spy_position_quantity": "0",
        }
    )
    status["execution_plan_summary"].update(
        {
            "action": "buy",
            "side": "buy",
            "notional": "25.00",
            "notional_cap": "25.00",
            "client_order_id": "pa-v207-spy-buy-20260808-aaaaaaaaaaaa",
            "paper_submit_authorized": False,
            "submit_allowed": False,
            "no_submit_mode": True,
            "mutation_would_be_required_without_no_submit": True,
            "intended_mutation_action": "buy",
        }
    )
    status["execution_plan"] = dict(status["execution_plan_summary"])

    rollup = _update_history(tmp_path, status)

    assert (
        rollup["autonomy_status"]
        == "paper_mutation_would_be_required_no_submit_mode"
    )
    assert rollup["readiness_status"] == "readiness_blocked_no_submit_mode"
    assert rollup["readiness_blockers"] == [
        "no_submit_mode",
        "paper_mutation_required",
    ]
    assert rollup["readiness_packet_generated"] is True
    packet_path = Path(
        rollup["artifact_paths"]["paper_mutation_readiness_packet"]
    )
    assert packet_path.is_file()
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["generated_at"] == status["generated_at"]
    assert packet["source_visibility_run_id"] == status["run_id"]
    assert (
        packet["source_autonomy_status"]
        == "paper_mutation_would_be_required_no_submit_mode"
    )
    assert packet["source_execution_plan_id"] == "plan-spy-20260808"
    assert packet["source_client_order_id"].startswith("pa-v207-spy-buy-")
    assert packet["symbol"] == "SPY"
    assert packet["selected_strategy_id"] == "spy_sma_50_200_training_wheel"
    assert packet["strategy_adapter_id"] == "spy_sma_50_200_paper_mutation_adapter"
    assert packet["strategy_adapter_mode"] == "paper_mutation"
    assert packet["strategy_route_action"] == "buy"
    assert packet["execution_plan_action"] == "buy"
    assert packet["intended_mutation_action"] == "buy"
    assert packet["side"] == "buy"
    assert packet["notional"] == "25.00"
    assert packet["quantity"] == ""
    assert packet["notional_cap"] == "25.00"
    assert packet["no_submit_mode"] is True
    assert packet["broker_read_performed"] is True
    assert packet["broker_state_observed"] is True
    assert packet["broker_state_mode"] == "alpaca_paper_observed"
    assert packet["expected_account_matched"] is True
    assert packet["spy_position_observed"] is False
    assert packet["spy_position_quantity"] == "0"
    assert packet["open_spy_orders_observed"] == 0
    assert packet["unexpected_non_spy_positions"] == []
    assert packet["data_freshness_status"] == "accepted_data_current"
    assert packet["latest_bar_date"] == "2026-08-08"
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_submit_performed"] is False
    assert packet["broker_mutation_performed"] is False
    assert packet["live_mutation_performed"] is False
    assert packet["readiness_status"] == "readiness_blocked_no_submit_mode"
    assert packet["readiness_blockers"] == [
        "no_submit_mode",
        "paper_mutation_required",
    ]
    assert packet["required_operator_action"] == (
        "review_readiness_packet_then_run_explicit_authorized_bounded_paper_mutation_after_operator_approval"
    )
    assert packet["safety_labels"] == status["safety_labels"]


def test_paper_candidate_can_be_ready_only_for_explicit_bounded_run(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status.update(
        {
            "spy_position_observed": False,
            "spy_position_quantity": "0",
            "strategy_route_action": "buy",
            "execution_plan_action": "buy",
            "intended_mutation_action": "buy",
            "preview_action_decision": "paper_buy_allowed",
            "paper_submit_authorized": True,
        }
    )
    status["broker_state"].update(
        {
            "spy_position_present": False,
            "spy_position_quantity": "0",
        }
    )
    status["execution_plan_summary"].update(
        {
            "action": "buy",
            "side": "buy",
            "notional": "25.00",
            "notional_cap": "25.00",
            "client_order_id": "pa-v207-spy-buy-20260808-aaaaaaaaaaaa",
            "paper_submit_authorized": True,
            "submit_allowed": True,
            "intended_mutation_action": "buy",
        }
    )
    status["execution_plan"] = dict(status["execution_plan_summary"])

    rollup = _update_history(tmp_path, status)

    assert (
        rollup["autonomy_status"]
        == "paper_mutation_candidate_requires_explicit_authorized_run"
    )
    assert (
        rollup["readiness_status"]
        == "readiness_ready_for_explicit_bounded_paper_authorized_run"
    )
    assert rollup["readiness_blockers"] == []
    assert rollup["readiness_packet_generated"] is True
    packet = json.loads(
        Path(rollup["artifact_paths"]["paper_mutation_readiness_packet"]).read_text(
            encoding="utf-8"
        )
    )
    assert (
        packet["readiness_status"]
        == "readiness_ready_for_explicit_bounded_paper_authorized_run"
    )
    assert packet["paper_submit_authorized"] is True
    assert packet["paper_submit_performed"] is False
    assert packet["broker_mutation_performed"] is False
    assert packet["live_mutation_performed"] is False


def test_preview_only_strategy_never_becomes_readiness_ready(tmp_path: Path) -> None:
    status = _base_status()
    status.update(
        {
            "selected_strategy_id": "spy_vol_scaled_trend_20d_fixed",
            "strategy_adapter_id": "spy_vol_scaled_trend_preview_adapter",
            "strategy_adapter_mode": "preview_only",
            "strategy_adapter_paper_mutation_allowed": False,
            "strategy_route_action": "buy",
            "execution_plan_action": "buy",
            "intended_mutation_action": "buy",
            "preview_action_decision": "paper_buy_allowed",
            "paper_submit_authorized": True,
        }
    )
    status["execution_plan_summary"].update(
        {
            "action": "buy",
            "side": "buy",
            "notional": "25.00",
            "notional_cap": "25.00",
            "paper_submit_authorized": True,
            "submit_allowed": True,
            "intended_mutation_action": "buy",
        }
    )
    status["execution_plan"] = dict(status["execution_plan_summary"])

    rollup = _update_history(tmp_path, status)

    assert (
        rollup["autonomy_status"]
        == "paper_mutation_candidate_requires_explicit_authorized_run"
    )
    assert rollup["readiness_status"] == "readiness_blocked_preview_only_strategy"
    assert rollup["readiness_packet_generated"] is True


def test_broker_state_not_observed_after_paper_profile_blocks(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status.update(
        {
            "broker_state_mode": "broker_state_not_observed",
            "broker_state_observed": False,
            "blocker_status": "blocked/broker_state_not_observed",
            "preview_action_decision": "blocked",
            "next_operator_action": "configure_verified_paper_profile_then_rerun",
            "safety_labels": [
                "paper_lab_only",
                "not_live_authorized",
                "profit_claim=none",
                "paper_autopilot_unlocked",
                "broker_state_not_observed",
            ],
        }
    )

    rollup = _update_history(tmp_path, status)

    assert rollup["classification"] == "broker_state_not_observed"
    assert rollup["autonomy_status"] == "blocked_configure_verified_paper_profile"
    assert rollup["readiness_status"] == "readiness_blocked_broker_state_not_observed"
    assert rollup["readiness_packet_generated"] is False
    assert rollup["autonomy_next_action"] == "configure_verified_paper_profile_then_rerun"
    assert rollup["attention_required"] is True
    assert paper_autopilot_history_exit_status(rollup) == 1


def test_pre_broker_daily_cycle_broker_state_context_does_not_block_final_rollup(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status.update(
        {
            "daily_cycle": {
                "daily_cycle_ran": True,
                "daily_cycle_blocker_status": "blocked/broker_state_not_observed",
                "daily_cycle_data_freshness_status": "accepted_data_current",
                "daily_cycle_data_refresh_status": "no_refresh_required",
            },
            "pre_broker_daily_cycle_status": "blocked/broker_state_not_observed",
            "pre_broker_daily_cycle_classification": (
                "pre_broker_broker_state_not_observed_context"
            ),
            "final_supervisor_status": "none",
            "broker_observed_supervisor_status": "none",
            "final_supervisor_classification": "no_action_required_no_mutation",
            "final_operator_action": "continue_next_daily_cycle",
        }
    )

    rollup = _update_history(tmp_path, status)

    assert rollup["classification"] == "healthy_hold_noop"
    assert rollup["attention_required"] is False
    assert rollup["pre_broker_daily_cycle_status"] == (
        "blocked/broker_state_not_observed"
    )
    assert rollup["pre_broker_daily_cycle_classification"] == (
        "pre_broker_broker_state_not_observed_context"
    )
    assert rollup["final_supervisor_status"] == "none"
    assert rollup["broker_observed_supervisor_status"] == "none"
    assert rollup["final_supervisor_classification"] == (
        "no_action_required_no_mutation"
    )


def test_live_safety_block_is_hard_stop(tmp_path: Path) -> None:
    status = _base_status()
    status.update(
        {
            "blocker_status": "blocked/live_safety",
            "live_mutation_performed": True,
            "next_operator_action": "stop_and_review_live_safety_before_any_paper_action",
        }
    )

    rollup = _update_history(tmp_path, status)

    assert rollup["classification"] == "live_safety_blocked"
    assert rollup["autonomy_status"] == "hard_stop_safety_invariant"
    assert rollup["readiness_status"] == "readiness_hard_stop_safety_invariant"
    assert rollup["hard_stop"] is True
    assert "live_mutation_performed" in rollup["reason_codes"]
    assert paper_autopilot_history_exit_status(rollup) == 2


def test_missing_required_safety_label_is_live_safety_hard_stop(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status["safety_labels"] = [
        "paper_lab_only",
        "profit_claim=none",
        "paper_autopilot_unlocked",
        "broker_state_observed",
    ]

    rollup = _update_history(tmp_path, status)

    assert rollup["classification"] == "live_safety_blocked"
    assert rollup["hard_stop"] is True
    assert "missing_safety_label:not_live_authorized" in rollup["reason_codes"]


def test_no_submit_mutation_flags_are_hard_stop_safety_invariant(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status.update(
        {
            "operating_mode": "visibility/no_submit",
            "no_submit_mode": True,
            "paper_submit_performed": True,
            "broker_mutation_performed": True,
        }
    )

    rollup = _update_history(tmp_path, status)

    assert rollup["autonomy_status"] == "hard_stop_safety_invariant"
    assert rollup["readiness_status"] == "readiness_hard_stop_safety_invariant"
    assert rollup["hard_stop"] is True
    assert "paper_submit_performed_in_no_submit_mode" in rollup["reason_codes"]
    assert "broker_mutation_performed_in_no_submit_mode" in rollup["reason_codes"]


def test_reconciliation_required_blocks_for_attention(tmp_path: Path) -> None:
    status = _base_status()
    status.update(
        {
            "blocker_status": "blocked/reconciliation_required",
            "preview_action_decision": "paper_buy_allowed",
            "paper_submit_authorized": True,
            "paper_submit_performed": True,
            "broker_mutation_performed": True,
            "reconciliation_status": "reconciliation_required",
            "next_operator_action": "stop_for_manual_reconciliation_review",
        }
    )
    status["reconciliation"] = {
        "reconciliation_required": True,
        "reconciliation_status": "reconciliation_required",
    }

    rollup = _update_history(tmp_path, status)

    assert rollup["classification"] == "reconciliation_required"
    assert rollup["attention_required"] is True


def test_unexpected_non_spy_position_blocks_for_attention(
    tmp_path: Path,
) -> None:
    status = _base_status()
    status.update(
        {
            "blocker_status": "blocked/unexpected_non_spy_position",
            "preview_action_decision": "blocked",
            "next_operator_action": "operator_review_non_spy_position",
        }
    )
    status["broker_state"]["unexpected_non_spy_positions"] = ["QQQ"]

    rollup = _update_history(tmp_path, status)

    assert rollup["classification"] == "unexpected_position_blocked"
    assert rollup["autonomy_status"] == "blocked_unexpected_non_spy_position"
    assert (
        rollup["readiness_status"]
        == "readiness_blocked_unexpected_non_spy_position"
    )
    assert rollup["attention_required"] is True


def test_open_spy_order_conflict_blocks_for_attention(tmp_path: Path) -> None:
    status = _base_status()
    status.update(
        {
            "blocker_status": "blocked/open_order_present",
            "preview_action_decision": "blocked",
            "next_operator_action": "reconcile_existing_spy_open_order_before_submit",
        }
    )
    status["broker_state"]["open_spy_order_present"] = True

    rollup = _update_history(tmp_path, status)

    assert rollup["classification"] == "open_order_conflict_blocked"
    assert rollup["autonomy_status"] == "blocked_open_spy_order_present"
    assert rollup["readiness_status"] == "readiness_blocked_open_spy_order_present"
    assert rollup["attention_required"] is True


def test_missing_latest_status_artifact_classifies_stale_or_missing(
    tmp_path: Path,
) -> None:
    rollup = update_paper_autopilot_operating_history(
        PaperAutopilotHistoryConfig(
            latest_status_path=tmp_path / "latest" / "latest_status.json",
            history_root=tmp_path / "history",
        )
    )

    assert rollup["classification"] == "stale_or_missing_status_artifact"
    assert rollup["autonomy_status"] == "blocked_refresh_or_validate_daily_bars"
    assert rollup["readiness_status"] == "readiness_blocked_stale_data"
    assert rollup["attention_required"] is True
    assert rollup["hard_stop"] is False
    _assert_history_artifacts(rollup)
    history = _history_lines(rollup)
    assert json.loads(history[-1])["status_artifact_available"] is False


def test_stale_latest_status_artifact_classifies_stale_or_missing(
    tmp_path: Path,
) -> None:
    first = _base_status(run_id="run-new", generated_at="2026-06-27T14:00:00+00:00")
    old = _base_status(run_id="run-old", generated_at="2026-06-26T14:00:00+00:00")
    _update_history(tmp_path, first)

    rollup = _update_history(tmp_path, old)

    assert rollup["classification"] == "stale_or_missing_status_artifact"
    assert rollup["autonomy_status"] == "blocked_refresh_or_validate_daily_bars"
    assert rollup["comparison_to_previous"]["previous_run_id"] == "run-new"


def test_daily_autonomy_transition_flags_are_recorded(tmp_path: Path) -> None:
    first = _base_status(run_id="run-1", generated_at="2026-06-26T14:00:00+00:00")
    second = _base_status(run_id="run-2", generated_at="2026-06-27T14:00:00+00:00")
    second.update(
        {
            "latest_bar_date": "2026-08-09",
            "broker_state_mode": "broker_state_not_observed",
            "broker_state_observed": False,
            "spy_position_observed": False,
            "spy_position_quantity": "0",
            "open_spy_orders_observed": 1,
            "selected_strategy_id": "spy_sma_50_200_training_wheel_v2",
            "execution_plan_action": "buy",
            "preview_action_decision": "paper_buy_blocked_no_submit_mode",
            "final_supervisor_classification": (
                "mutation_would_be_required_no_submit_mode"
            ),
            "blocker_status": "blocked/mutation_would_be_required_no_submit_mode",
            "vol_scaled_preview_intended_action": "sell_close",
            "broker_mutation_performed": True,
        }
    )
    second["broker_state"].update(
        {
            "broker_state_mode": "broker_state_not_observed",
            "spy_position_present": False,
            "spy_position_quantity": "0",
            "open_spy_order_present": True,
        }
    )
    second["execution_plan_summary"]["action"] = "buy"
    _update_history(tmp_path, first)

    rollup = _update_history(tmp_path, second)

    comparison = rollup["comparison_to_previous"]
    assert rollup["changed_since_previous"] is True
    assert comparison["latest_bar_date_changed"] is True
    assert comparison["broker_state_mode_changed"] is True
    assert comparison["spy_position_changed"] is True
    assert comparison["open_orders_changed"] is True
    assert comparison["selected_strategy_changed"] is True
    assert comparison["execution_plan_action_changed"] is True
    assert comparison["final_supervisor_classification_changed"] is True
    assert comparison["blocker_status_changed"] is True
    assert comparison["vol_scaled_preview_action_changed"] is True
    assert comparison["mutation_flags_changed"] is True
    autonomy_latest = json.loads(
        Path(rollup["artifact_paths"]["latest_daily_autonomy"]).read_text(
            encoding="utf-8"
        )
    )
    assert autonomy_latest["changed_since_previous"] is True
    assert autonomy_latest["latest_bar_date_changed"] is True
    assert autonomy_latest["mutation_flags_changed"] is True


def test_jsonl_append_behavior_is_deterministic(tmp_path: Path) -> None:
    first_lines = _run_two_history_appends(tmp_path / "one")
    second_lines = _run_two_history_appends(tmp_path / "two")

    assert _normalize_root(first_lines, tmp_path / "one") == _normalize_root(
        second_lines,
        tmp_path / "two",
    )
    records = [json.loads(line) for line in first_lines]
    assert [record["history_sequence"] for record in records] == [1, 2]
    assert records[0]["run_id"] == "run-1"
    assert records[1]["run_id"] == "run-2"


def test_runtime_artifacts_under_runs_remain_untracked() -> None:
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    verify_script = (PROJECT_ROOT / "scripts" / "verify_offline.ps1").read_text(
        encoding="utf-8"
    )
    assert 'git" @("ls-files", "runs/paper_autopilot")' in verify_script
    result = subprocess.run(
        ["git", "ls-files", "runs/paper_autopilot"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_history_module_imports_no_broker_sdk_network_or_credentials() -> None:
    forbidden_roots = {
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
    }
    tree = ast.parse(HISTORY_MODULE.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".", maxsplit=1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", maxsplit=1)[0])

    assert imported_roots & forbidden_roots == set()


def _update_history(tmp_path: Path, status: dict[str, object]) -> dict[str, object]:
    latest_status_path = _write_latest_status(tmp_path, status)
    return update_paper_autopilot_operating_history(
        PaperAutopilotHistoryConfig(
            latest_status_path=latest_status_path,
            history_root=tmp_path / "history",
        )
    )


def _write_latest_status(tmp_path: Path, status: dict[str, object]) -> Path:
    latest_dir = tmp_path / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_status_path = latest_dir / "latest_status.json"
    latest_status_path.write_text(
        json.dumps(status, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return latest_status_path


def _assert_history_artifacts(rollup: dict[str, object]) -> None:
    artifact_paths = rollup["artifact_paths"]
    assert Path(artifact_paths["operating_history"]).is_file()
    assert Path(artifact_paths["daily_autonomy_ledger"]).is_file()
    assert Path(artifact_paths["latest_daily_autonomy"]).is_file()
    assert Path(artifact_paths["daily_autonomy_summary"]).is_file()
    assert Path(artifact_paths["latest_rollup"]).is_file()
    assert Path(artifact_paths["operating_summary"]).is_file()
    latest_rollup = json.loads(
        Path(artifact_paths["latest_rollup"]).read_text(encoding="utf-8")
    )
    assert latest_rollup["classification"] == rollup["classification"]
    latest_autonomy = json.loads(
        Path(artifact_paths["latest_daily_autonomy"]).read_text(encoding="utf-8")
    )
    assert latest_autonomy["autonomy_status"] == rollup["autonomy_status"]


def _history_lines(rollup: dict[str, object]) -> list[str]:
    return (
        Path(rollup["artifact_paths"]["operating_history"])
        .read_text(encoding="utf-8")
        .splitlines()
    )


def _run_two_history_appends(root: Path) -> list[str]:
    _update_history(
        root,
        _base_status(run_id="run-1", generated_at="2026-06-26T14:00:00+00:00"),
    )
    _update_history(
        root,
        _base_status(run_id="run-2", generated_at="2026-06-27T14:00:00+00:00"),
    )
    return (root / "history" / "operating_history.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()


def _normalize_root(lines: list[str], root: Path) -> list[str]:
    escaped_root = json.dumps(str(root))[1:-1]
    return [
        line.replace(escaped_root, "<ROOT>").replace(str(root), "<ROOT>")
        for line in lines
    ]


def _base_status(
    *,
    run_id: str = "paper_autopilot_20260626T140000Z",
    generated_at: str = "2026-06-26T14:00:00+00:00",
) -> dict[str, object]:
    return {
        "schema_version": "v207_paper_autopilot_loop_v1",
        "run_id": run_id,
        "generated_at": generated_at,
        "policy": "paper_autopilot_unlocked",
        "symbol": "SPY",
        "as_of_date": "2026-08-08",
        "latest_bar_date": "2026-08-08",
        "data_refresh_status": "no_refresh_required",
        "data_freshness_status": "accepted_data_current",
        "input_data_path": "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
        "input_data_sha256": "a" * 64,
        "sma_posture": "risk_on",
        "operating_mode": "bounded_paper_mutation",
        "broker_state_mode": "alpaca_paper_observed",
        "broker_state_observed": True,
        "broker_read_performed": True,
        "expected_account_matched": True,
        "spy_position_observed": True,
        "spy_position_quantity": "0.05",
        "open_spy_orders_observed": 0,
        "unexpected_non_spy_positions": [],
        "unexpected_non_spy_positions_observed": 0,
        "selected_strategy_id": "spy_sma_50_200_training_wheel",
        "strategy_route_action": "hold",
        "strategy_route_paper_mutation_allowed": True,
        "strategy_adapter_resolution_status": "resolved",
        "strategy_adapter_reason": "paper_mutation_adapter_resolved",
        "strategy_adapter_id": "spy_sma_50_200_paper_mutation_adapter",
        "strategy_adapter_mode": "paper_mutation",
        "strategy_adapter_paper_mutation_allowed": True,
        "pre_broker_daily_cycle_status": "no_refresh_required",
        "pre_broker_daily_cycle_classification": "pre_broker_daily_cycle_ready",
        "broker_state": {
            "broker_state_mode": "alpaca_paper_observed",
            "broker_state_observed": True,
            "spy_position_present": True,
            "spy_position_quantity": "0.05",
            "unexpected_non_spy_positions": [],
            "open_spy_order_present": False,
            "expected_account_matched": True,
        },
        "preflight": {
            "APP_PROFILE": "paper",
            "APP_PROFILE_is_paper": True,
            "live_endpoint_or_profile_detected": False,
        },
        "execution_plan_summary": {
            "execution_plan_id": "plan-spy-20260808",
            "action": "hold",
            "side": "",
            "client_order_id": "pa-v207-spy-noop-20260808-aaaaaaaaaaaa",
            "paper_submit_authorized": False,
            "submit_allowed": False,
            "no_submit_mode": False,
            "mutation_would_be_required_without_no_submit": False,
            "intended_mutation_action": "",
            "notional_cap": "25.00",
        },
        "execution_plan_action": "hold",
        "preview_action_decision": "hold/noop",
        "vol_scaled_preview": {
            "strategy_id": "spy_vol_scaled_trend_20d_fixed",
            "visible": True,
            "intended_action": "buy",
            "submit_allowed": False,
            "paper_mutation_allowed": False,
            "mutation_allowed": False,
            "non_mutation_status": "preview_only_non_mutating",
        },
        "vol_scaled_preview_visible": True,
        "vol_scaled_preview_intended_action": "buy",
        "vol_scaled_preview_mutation_allowed": False,
        "vol_scaled_preview_submit_allowed": False,
        "vol_scaled_preview_non_mutation_status": "preview_only_non_mutating",
        "blocker_status": "none",
        "final_supervisor_status": "none",
        "broker_observed_supervisor_status": "none",
        "final_supervisor_classification": "no_action_required_no_mutation",
        "reconciliation": {
            "reconciliation_required": False,
            "reconciliation_status": "not_required_no_broker_mutation",
        },
        "reconciliation_status": "not_required_no_broker_mutation",
        "next_operator_action": "continue_next_daily_cycle",
        "final_operator_action": "continue_next_daily_cycle",
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "safety_labels": [
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
            "paper_autopilot_unlocked",
            "broker_state_observed",
        ],
    }
