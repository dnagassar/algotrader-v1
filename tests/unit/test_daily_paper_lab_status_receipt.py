from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.execution.daily_paper_lab_status_receipt import (
    DailyPaperLabStatusReceiptError,
    build_daily_paper_lab_status_receipt,
    render_daily_paper_lab_status_receipt,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATUS_SCRIPT = PROJECT_ROOT / "scripts" / "show_daily_paper_lab_status.ps1"
STATUS_MODULE = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "execution"
    / "daily_paper_lab_status_receipt.py"
)


def test_status_receipt_accepts_broker_aware_hold_noop_state(tmp_path: Path) -> None:
    output_root = _write_latest_run(tmp_path, _base_latest_run())

    receipt = _rendered_receipt(output_root)

    assert receipt["validation_status"] == "passed"
    assert receipt["data_freshness_status"] == "current_for_daily_bar_lab"
    assert receipt["sma_posture"] == "bullish_risk_on"
    assert receipt["broker_state_mode"] == "alpaca_paper_read_only"
    assert receipt["broker_state_observed"] == "true"
    assert receipt["broker_aware_preview_decision"] == "hold/noop"
    assert receipt["execution_plan_status"] == "no_action_required"
    assert receipt["execution_plan_action"] == "hold/noop"
    assert receipt["approval_state"] == "not_required_noop"
    assert receipt["next_safe_action"] == "run_next_completed_session_daily_cycle"


def test_status_receipt_reports_blocked_state_as_valid_data(tmp_path: Path) -> None:
    payload = _base_latest_run()
    payload["daily_decision_summary"]["broker_aware_preview_decision"] = (
        "blocked/local_artifact_missing"
    )
    payload["execution_plan"]["execution_plan_status"] = "blocked"
    payload["execution_plan"]["execution_plan_action"] = "none"
    payload["execution_plan"]["execution_plan_blocker"] = "local_artifact_missing"
    payload["execution_plan"]["execution_plan_reason"] = "local_artifact_missing"
    payload["daily_approval_gate"]["approval_state"] = "blocked"
    payload["daily_autopilot_controller"]["autopilot_control_status"] = (
        "repair_required"
    )
    payload["daily_autopilot_controller"]["next_safe_action"] = (
        "repair_current_blocker"
    )
    payload["daily_autopilot_controller"]["selected_agent"] = "Codex"
    output_root = _write_latest_run(tmp_path, payload)

    receipt = _rendered_receipt(output_root)

    assert receipt["broker_aware_preview_decision"] == "blocked/local_artifact_missing"
    assert receipt["execution_plan_status"] == "blocked"
    assert receipt["execution_plan_blocker"] == "local_artifact_missing"
    assert receipt["approval_state"] == "blocked"
    assert receipt["autopilot_control_status"] == "repair_required"
    assert receipt["selected_agent"] == "Codex"


def test_status_receipt_reports_hard_gate_required_state(tmp_path: Path) -> None:
    payload = _base_latest_run()
    payload["daily_autopilot_controller"]["autopilot_control_status"] = (
        "hard_gate_required"
    )
    payload["daily_autopilot_controller"]["can_continue_without_daniel"] = False
    payload["daily_autopilot_controller"]["selected_agent"] = "Daniel"
    payload["daily_autopilot_controller"]["hard_gate_required"] = True
    payload["daily_autopilot_controller"]["hard_gate_type"] = "broker_read"
    payload["daily_autopilot_controller"]["hard_gate_reason"] = "broker_unavailable"
    output_root = _write_latest_run(tmp_path, payload)

    receipt = _rendered_receipt(output_root)

    assert receipt["autopilot_control_status"] == "hard_gate_required"
    assert receipt["can_continue_without_daniel"] == "false"
    assert receipt["selected_agent"] == "Daniel"
    assert receipt["hard_gate_required"] == "true"
    assert receipt["hard_gate_type"] == "broker_read"
    assert receipt["hard_gate_reason"] == "broker_unavailable"


def test_status_receipt_preserves_boolean_false_values(tmp_path: Path) -> None:
    payload = _base_latest_run()
    payload["broker_state_observed"] = False
    payload["daily_autopilot_controller"]["can_continue_without_daniel"] = False
    output_root = _write_latest_run(tmp_path, payload)

    receipt = _rendered_receipt(output_root)

    assert receipt["broker_state_observed"] == "false"
    assert receipt["submit_allowed"] == "false"
    assert receipt["can_continue_without_daniel"] == "false"
    assert receipt["hard_gate_required"] == "false"
    assert receipt["paper_submit_authorized"] == "false"
    assert receipt["live_authorized"] == "false"
    assert receipt["broker_mutation_performed"] == "false"


def test_status_receipt_extracts_nested_required_fields(tmp_path: Path) -> None:
    output_root = _write_latest_run(tmp_path, _base_latest_run())

    receipt = build_daily_paper_lab_status_receipt(output_root)

    assert receipt["latest_bar_date"] == "2026-06-18"
    assert receipt["broker_snapshot_freshness_status"] == "fresh"
    assert receipt["execution_plan_reason"] == (
        "existing_spy_position_satisfies_risk_on_preview"
    )
    assert receipt["approval_state"] == "not_required_noop"
    assert receipt["autopilot_control_status"] == (
        "waiting_for_next_completed_session"
    )


def test_status_receipt_fails_for_missing_output_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"

    with pytest.raises(DailyPaperLabStatusReceiptError, match="missing output root"):
        build_daily_paper_lab_status_receipt(missing_root)


def test_status_receipt_fails_for_missing_canonical_artifact(tmp_path: Path) -> None:
    output_root = tmp_path / "daily out"
    output_root.mkdir()

    with pytest.raises(
        DailyPaperLabStatusReceiptError,
        match="missing canonical artifact",
    ):
        build_daily_paper_lab_status_receipt(output_root)


def test_status_receipt_fails_for_malformed_json(tmp_path: Path) -> None:
    output_root = tmp_path / "daily"
    output_root.mkdir()
    (output_root / "latest_run.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(DailyPaperLabStatusReceiptError, match="malformed JSON"):
        build_daily_paper_lab_status_receipt(output_root)


def test_status_receipt_fails_for_missing_required_contract_field(
    tmp_path: Path,
) -> None:
    payload = _base_latest_run()
    del payload["daily_decision_summary"]["latest_bar_date"]
    output_root = _write_latest_run(tmp_path, payload)

    with pytest.raises(
        DailyPaperLabStatusReceiptError,
        match="missing required contract field: latest_bar_date",
    ):
        build_daily_paper_lab_status_receipt(output_root)


def test_status_receipt_omits_absent_optional_fields_without_corrupting_output(
    tmp_path: Path,
) -> None:
    payload = _base_latest_run()
    del payload["run_date"]
    del payload["safety_labels"]
    del payload["daily_decision_summary"]["input_data_path"]
    del payload["daily_decision_summary"]["as_of_date"]
    output_root = _write_latest_run(tmp_path, payload)

    receipt = _rendered_receipt(output_root)

    assert "run_date" not in receipt
    assert "safety_labels" not in receipt
    assert "input_data_path" not in receipt
    assert "data_as_of_date" not in receipt
    assert receipt["validation_status"] == "passed"
    assert receipt["execution_plan_action"] == "hold/noop"


def test_status_receipt_handles_paths_containing_spaces(tmp_path: Path) -> None:
    output_root = _write_latest_run(
        tmp_path / "root with spaces",
        _base_latest_run(),
    )

    receipt = _rendered_receipt(output_root)

    assert "root with spaces" in receipt["artifact_source_path"]
    assert receipt["validation_status"] == "passed"


def test_status_script_propagates_nonzero_extractor_exit_code(
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text("@echo off\r\nexit /B 17\r\n", encoding="utf-8")
    env = _scrubbed_env()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(STATUS_SCRIPT),
            "-OutputRoot",
            str(tmp_path / "missing root"),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 17


def test_status_extractor_has_no_broker_network_llm_notebook_or_agent_imports() -> None:
    forbidden_roots = {
        "aiohttp",
        "alpaca",
        "alpaca_trade_api",
        "anthropic",
        "httpx",
        "IPython",
        "jupyter",
        "langchain",
        "langgraph",
        "nbformat",
        "notebook",
        "openai",
        "requests",
        "socket",
        "urllib",
        "websockets",
        "algotrader",
    }
    tree = ast.parse(STATUS_MODULE.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", maxsplit=1)[0])

    assert imported_roots & forbidden_roots == set()


def _rendered_receipt(output_root: Path) -> dict[str, str]:
    text = render_daily_paper_lab_status_receipt(output_root)
    return dict(line.split("=", maxsplit=1) for line in text.splitlines())


def _write_latest_run(root: Path, payload: dict[str, object]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_run.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )
    return root


def _base_latest_run() -> dict[str, object]:
    return {
        "run_date": "2026-06-22",
        "validation_status": "passed",
        "data_freshness_status": "current_for_daily_bar_lab",
        "market_signal_preview": "buy_preview",
        "broker_state_mode": "alpaca_paper_read_only",
        "broker_state_observed": True,
        "broker_state_status": "observed",
        "safety_labels": [
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "daily_decision_summary": {
            "latest_bar_date": "2026-06-18",
            "sma_posture": "bullish_risk_on",
            "broker_snapshot_freshness_status": "fresh",
            "broker_aware_preview_decision": "hold/noop",
            "input_data_path": (
                "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
            ),
            "as_of_date": "2026-06-18",
        },
        "execution_plan": {
            "execution_plan_status": "no_action_required",
            "execution_plan_action": "hold/noop",
            "execution_plan_blocker": "none",
            "execution_plan_reason": (
                "existing_spy_position_satisfies_risk_on_preview"
            ),
        },
        "daily_approval_gate": {
            "approval_state": "not_required_noop",
            "submit_allowed": False,
            "paper_submit_authorized": False,
            "live_authorized": False,
            "broker_mutation_performed": False,
        },
        "daily_autopilot_controller": {
            "autopilot_control_status": "waiting_for_next_completed_session",
            "can_continue_without_daniel": True,
            "next_safe_action": "run_next_completed_session_daily_cycle",
            "selected_agent": "none",
            "hard_gate_required": False,
            "hard_gate_type": "none",
            "hard_gate_reason": "none",
        },
    }


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify status script")
    return powershell


def _scrubbed_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "PYTEST_ADDOPTS",
    ):
        env.pop(name, None)
    return env
