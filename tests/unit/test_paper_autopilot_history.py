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
    assert rollup["operating_mode"] == "bounded_paper_mutation"
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
    assert rollup["attention_required"] is False
    assert rollup["paper_submit_performed"] is True


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
    assert rollup["comparison_to_previous"]["previous_run_id"] == "run-new"


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
    assert Path(artifact_paths["latest_rollup"]).is_file()
    assert Path(artifact_paths["operating_summary"]).is_file()
    latest_rollup = json.loads(
        Path(artifact_paths["latest_rollup"]).read_text(encoding="utf-8")
    )
    assert latest_rollup["classification"] == rollup["classification"]


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
        "input_data_path": "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
        "input_data_sha256": "a" * 64,
        "sma_posture": "risk_on",
        "operating_mode": "bounded_paper_mutation",
        "broker_state_mode": "alpaca_paper_observed",
        "broker_state_observed": True,
        "pre_broker_daily_cycle_status": "no_refresh_required",
        "pre_broker_daily_cycle_classification": "pre_broker_daily_cycle_ready",
        "broker_state": {
            "unexpected_non_spy_positions": [],
            "open_spy_order_present": False,
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
        },
        "preview_action_decision": "hold/noop",
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
