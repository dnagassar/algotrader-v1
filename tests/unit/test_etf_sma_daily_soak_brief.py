from __future__ import annotations

import json
import os
import re
from pathlib import Path
import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_soak_brief import (
    EtfSmaDailySoakBriefConfig,
    run_etf_sma_daily_soak_brief,
)


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


def test_soak_brief_happy_path(tmp_path: Path) -> None:
    """Verify soak brief consumes a valid rollup, computes counts, and checks artifacts."""
    rollup_path = tmp_path / "soak_rollup.jsonl"
    daily_root = tmp_path / "daily"
    daily_root.mkdir()

    # Create dummy daily run folders with some files
    dates = ["2025-06-01", "2025-06-02"]
    for date_str in dates:
        day_dir = daily_root / date_str
        day_dir.mkdir()
        
        # Create all 10 expected files for a clean day
        expected_files = [
            "cycle.jsonl", "brief.jsonl", "brief.txt", "gate.jsonl",
            "dashboard.txt", "bundle_manifest.jsonl", "bundle_status.jsonl",
            "bundle_status.txt", "offline_check.jsonl", "offline_check.txt"
        ]
        for fname in expected_files:
            (day_dir / fname).write_text("{}", encoding="utf-8")

        # Write dummy cycle.jsonl data
        cycle_data = {
            "sma_posture": "bullish" if date_str == "2025-06-01" else "defensive",
            "decision": "buy" if date_str == "2025-06-01" else "hold/noop",
            "blockers": []
        }
        (day_dir / "cycle.jsonl").write_text(json.dumps(cycle_data), encoding="utf-8")

    # Create a mock soak rollup payload
    soak_rollup_payload = {
        "phase": "offline_daily_loop_soak",
        "status": "accepted",
        "start_date": "2025-06-01",
        "end_date": "2025-06-02",
        "attempted_dates": dates,
        "accepted_dates": dates,
        "blocked_dates": [],
        "insufficient_history_dates": [],
        "finding_count": 0,
        "artifact_paths": [
            f"daily/{dates[0]}/cycle.jsonl",
            f"daily/{dates[1]}/cycle.jsonl"
        ],
        "live_trading_authorized": False,
        "network_access_authorized": False,
    }
    
    rollup_path.write_text(json.dumps(soak_rollup_payload) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakBriefConfig(
        soak_rollup_jsonl=rollup_path,
        daily_root=daily_root,
        output_jsonl=tmp_path / "soak_operator_brief.jsonl",
        output_text=tmp_path / "soak_operator_brief.txt",
    )

    payload = run_etf_sma_daily_soak_brief(config)

    assert payload["status"] == "accepted"
    assert payload["attempted_date_count"] == 2
    assert payload["accepted_date_count"] == 2
    assert payload["blocked_date_count"] == 0
    assert payload["insufficient_history_date_count"] == 0
    assert payload["missing_expected_artifact_count"] == 0
    assert payload["absolute_path_finding_count"] == 0
    assert payload["posture_counts"] == {"bullish": 1, "defensive": 1}
    assert payload["cycle_decision_counts"] == {"buy": 1, "hold/noop": 1}
    assert payload["blocker_counts"] == {}
    
    assert (tmp_path / "soak_operator_brief.jsonl").exists()
    assert (tmp_path / "soak_operator_brief.txt").exists()


def test_soak_brief_with_missing_artifacts_and_blockers(tmp_path: Path) -> None:
    """Verify that missing artifacts and blockers are compiled correctly and status is blocked."""
    rollup_path = tmp_path / "soak_rollup.jsonl"
    daily_root = tmp_path / "daily"
    daily_root.mkdir()

    dates = ["2025-06-01", "2025-06-02"]
    for date_str in dates:
        day_dir = daily_root / date_str
        day_dir.mkdir()

    # Write dummy cycle.jsonl only for 2025-06-01 with blockers
    cycle_data = {
        "sma_posture": "insufficient_history",
        "decision": "hold/noop",
        "blockers": ["open_order"]
    }
    (daily_root / "2025-06-01" / "cycle.jsonl").write_text(json.dumps(cycle_data), encoding="utf-8")

    soak_rollup_payload = {
        "phase": "offline_daily_loop_soak",
        "status": "completed_with_findings",
        "start_date": "2025-06-01",
        "end_date": "2025-06-02",
        "attempted_dates": dates,
        "accepted_dates": [],
        "blocked_dates": ["2025-06-01"],
        "insufficient_history_dates": ["2025-06-02"],
        "finding_count": 2,
        "artifact_paths": [
            f"daily/{dates[0]}/cycle.jsonl"
        ],
        "live_trading_authorized": False,
        "network_access_authorized": False,
    }
    rollup_path.write_text(json.dumps(soak_rollup_payload) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakBriefConfig(
        soak_rollup_jsonl=rollup_path,
        daily_root=daily_root,
        output_jsonl=tmp_path / "soak_operator_brief.jsonl",
        output_text=tmp_path / "soak_operator_brief.txt",
    )

    payload = run_etf_sma_daily_soak_brief(config)

    assert payload["status"] == "blocked"
    assert payload["attempted_date_count"] == 2
    assert payload["accepted_date_count"] == 0
    assert payload["blocked_date_count"] == 1
    assert payload["insufficient_history_date_count"] == 1
    
    # Check missing artifacts (2025-06-01 has 9 missing files, 2025-06-02 has 10 missing files)
    assert payload["missing_expected_artifact_count"] == 19
    assert payload["blocker_counts"] == {"open_order": 1}
    assert payload["posture_counts"] == {"insufficient_history": 2}


def test_soak_brief_absolute_path_leakage_scan() -> None:
    """Verify that absolute path leaks in artifacts are detected and counted."""
    test_run_dir = Path("runs/test_soak_brief_absolute_path_leakage_scan")
    if test_run_dir.exists():
        import shutil
        shutil.rmtree(test_run_dir, ignore_errors=True)

    try:
        rollup_path = test_run_dir / "soak_rollup.jsonl"
        daily_root = test_run_dir / "daily"
        daily_root.mkdir(parents=True)

        day_dir = daily_root / "2025-06-01"
        day_dir.mkdir()
        
        # Write cycle.jsonl containing a simulated Windows absolute path
        cycle_data = {
            "sma_posture": "bullish",
            "decision": "buy",
            "blockers": [],
            "debug_path": "C:\\Users\\danie\\Desktop\\algo_trader\\runs\\daily\\2025-06-01\\cycle.jsonl"
        }
        (day_dir / "cycle.jsonl").write_text(json.dumps(cycle_data), encoding="utf-8")
        
        # Write a text file with a POSIX absolute path leak
        expected_files = [
            "brief.jsonl", "brief.txt", "gate.jsonl",
            "dashboard.txt", "bundle_manifest.jsonl", "bundle_status.jsonl",
            "bundle_status.txt", "offline_check.jsonl", "offline_check.txt"
        ]
        for fname in expected_files:
            if fname == "brief.txt":
                (day_dir / fname).write_text("Absolute path here: /home/user/algo_trader/runs/daily\n", encoding="utf-8")
            else:
                (day_dir / fname).write_text("{}", encoding="utf-8")

        soak_rollup_payload = {
            "phase": "offline_daily_loop_soak",
            "status": "accepted",
            "start_date": "2025-06-01",
            "end_date": "2025-06-01",
            "attempted_dates": ["2025-06-01"],
            "accepted_dates": ["2025-06-01"],
            "blocked_dates": [],
            "insufficient_history_dates": [],
            "finding_count": 0,
            "artifact_paths": [
                f"runs/test_soak_brief_absolute_path_leakage_scan/daily/2025-06-01/cycle.jsonl",
                f"runs/test_soak_brief_absolute_path_leakage_scan/daily/2025-06-01/brief.txt"
            ],
            "live_trading_authorized": False,
            "network_access_authorized": False,
        }
        rollup_path.write_text(json.dumps(soak_rollup_payload) + "\n", encoding="utf-8")

        config = EtfSmaDailySoakBriefConfig(
            soak_rollup_jsonl=rollup_path,
            daily_root=daily_root,
            output_jsonl=test_run_dir / "soak_operator_brief.jsonl",
            output_text=test_run_dir / "soak_operator_brief.txt",
        )

        # Convert paths inside the mocked payload to absolute first for checking
        payload = run_etf_sma_daily_soak_brief(config)
        
        # C:\Users\... is flagged, and /home/user/... is flagged.
        assert payload["absolute_path_finding_count"] == 2
        assert payload["status"] == "completed_with_findings"

        # Make sure no absolute path leaked into the output operator brief itself
        brief_json_content = (test_run_dir / "soak_operator_brief.jsonl").read_text(encoding="utf-8")
        assert "C:" not in brief_json_content
        assert "\\" not in brief_json_content
        assert not re.search(r"[a-zA-Z]:[\\/]", brief_json_content)

    finally:
        import shutil
        shutil.rmtree(test_run_dir, ignore_errors=True)


def test_soak_brief_baseline_comparison(tmp_path: Path) -> None:
    """Verify baseline comparison correctly detects matches and mismatches."""
    rollup_path = tmp_path / "soak_rollup.jsonl"
    baseline_path = tmp_path / "baseline_rollup.jsonl"
    daily_root = tmp_path / "daily"
    daily_root.mkdir()

    day_dir = daily_root / "2025-06-01"
    day_dir.mkdir()
    
    expected_files = [
        "cycle.jsonl", "brief.jsonl", "brief.txt", "gate.jsonl",
        "dashboard.txt", "bundle_manifest.jsonl", "bundle_status.jsonl",
        "bundle_status.txt", "offline_check.jsonl", "offline_check.txt"
    ]
    for fname in expected_files:
        (day_dir / fname).write_text("{}", encoding="utf-8")

    soak_rollup_payload = {
        "phase": "offline_daily_loop_soak",
        "status": "accepted",
        "start_date": "2025-06-01",
        "end_date": "2025-06-01",
        "attempted_dates": ["2025-06-01"],
        "accepted_dates": ["2025-06-01"],
        "blocked_dates": [],
        "insufficient_history_dates": [],
        "finding_count": 0,
        "artifact_paths": [f"daily/2025-06-01/cycle.jsonl"],
        "live_trading_authorized": False,
        "network_access_authorized": False,
    }
    rollup_path.write_text(json.dumps(soak_rollup_payload) + "\n", encoding="utf-8")

    # Match baseline case
    baseline_path.write_text(json.dumps(soak_rollup_payload) + "\n", encoding="utf-8")
    
    config = EtfSmaDailySoakBriefConfig(
        soak_rollup_jsonl=rollup_path,
        daily_root=daily_root,
        output_jsonl=tmp_path / "soak_operator_brief.jsonl",
        output_text=tmp_path / "soak_operator_brief.txt",
        baseline_rollup_jsonl=baseline_path,
    )
    
    payload = run_etf_sma_daily_soak_brief(config)
    assert payload["regression_status"] == "matched"
    assert payload["regression_findings"] == []
    assert payload["status"] == "accepted"

    # Mismatch baseline case (change attempted dates)
    mismatched_payload = dict(soak_rollup_payload)
    mismatched_payload["attempted_dates"] = ["2025-06-01", "2025-06-02"]
    baseline_path.write_text(json.dumps(mismatched_payload) + "\n", encoding="utf-8")

    payload = run_etf_sma_daily_soak_brief(config)
    assert payload["regression_status"] == "mismatch"
    assert len(payload["regression_findings"]) > 0
    assert payload["status"] == "completed_with_findings"


def test_soak_brief_cli_command(tmp_path: Path) -> None:
    """Verify the CLI wrapper successfully invokes the brief command and exits 0."""
    rollup_path = tmp_path / "soak_rollup.jsonl"
    daily_root = tmp_path / "daily"
    daily_root.mkdir()

    day_dir = daily_root / "2025-06-01"
    day_dir.mkdir()
    
    expected_files = [
        "cycle.jsonl", "brief.jsonl", "brief.txt", "gate.jsonl",
        "dashboard.txt", "bundle_manifest.jsonl", "bundle_status.jsonl",
        "bundle_status.txt", "offline_check.jsonl", "offline_check.txt"
    ]
    for fname in expected_files:
        (day_dir / fname).write_text("{}", encoding="utf-8")

    soak_rollup_payload = {
        "phase": "offline_daily_loop_soak",
        "status": "accepted",
        "start_date": "2025-06-01",
        "end_date": "2025-06-01",
        "attempted_dates": ["2025-06-01"],
        "accepted_dates": ["2025-06-01"],
        "blocked_dates": [],
        "insufficient_history_dates": [],
        "finding_count": 0,
        "artifact_paths": [f"daily/2025-06-01/cycle.jsonl"],
        "live_trading_authorized": False,
        "network_access_authorized": False,
    }
    rollup_path.write_text(json.dumps(soak_rollup_payload) + "\n", encoding="utf-8")

    code = cli_module.main([
        "etf-sma-daily-soak-brief",
        "--soak-rollup-jsonl", str(rollup_path),
        "--daily-root", str(daily_root),
        "--output-jsonl", str(tmp_path / "brief.jsonl"),
        "--output-text", str(tmp_path / "brief.txt"),
        "--format", "json",
    ])
    assert code == 0
    assert (tmp_path / "brief.jsonl").exists()
    assert (tmp_path / "brief.txt").exists()
