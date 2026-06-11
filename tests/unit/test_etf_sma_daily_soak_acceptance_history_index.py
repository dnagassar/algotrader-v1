from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_soak_acceptance_history_index import (
    EtfSmaDailySoakAcceptanceHistoryIndexConfig,
    run_etf_sma_daily_soak_acceptance_history_index,
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


def _mock_golden_check(
    start_date: str,
    end_date: str,
    status: str,
    release_gate_status: str,
    attempted: int,
    accepted: int,
    blocked: int,
    insufficient: int,
    validation_findings: int,
    post_validation_findings: int,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "phase": "offline_daily_loop_soak_golden_check",
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "output_root": "runs/daily_soak",
        "attempted_date_count": attempted,
        "accepted_date_count": accepted,
        "blocked_date_count": blocked,
        "insufficient_history_date_count": insufficient,
        "release_gate_status": release_gate_status,
        "artifact_validation_finding_count": validation_findings,
        "post_release_artifact_validation_finding_count": post_validation_findings,
        "golden_acceptance_status": status,
        "golden_acceptance_blockers": blockers,
        "artifact_paths": [
            f"runs/daily_soak/{start_date}_{end_date}/soak_rollup.jsonl",
            f"runs/daily_soak/{start_date}_{end_date}/soak_release_gate.jsonl",
        ],
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }


def test_history_index_no_history_directory(tmp_path: Path) -> None:
    """Verify index behavior when the daily soak folder is empty or non-existent."""
    empty_dir = tmp_path / "empty_daily_soak"
    out_file = tmp_path / "index.jsonl"
    
    config = EtfSmaDailySoakAcceptanceHistoryIndexConfig(
        daily_soak_dir=empty_dir,
        out=out_file,
    )
    records = run_etf_sma_daily_soak_acceptance_history_index(config)
    
    assert out_file.exists()
    
    # Read output and verify
    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # Summary, Latest Run, Blocker Trends
    
    summary = json.loads(lines[0])
    assert summary["phase"] == "V3J"
    assert summary["record_type"] == "summary"
    assert summary["status"] == "blocked-no-history"
    assert summary["indexed_golden_acceptance_count"] == 0
    assert summary["scanned_file_count"] == 0
    assert summary["latest_golden_acceptance_status"] is None
    
    latest = json.loads(lines[1])
    assert latest["record_type"] == "latest_run"
    assert latest["latest_golden_acceptance_status"] is None
    
    trends = json.loads(lines[2])
    assert trends["record_type"] == "blocker_trends"
    assert trends["blocker_trends"] == {}


def test_history_index_multiple_runs(tmp_path: Path) -> None:
    """Verify that multiple golden checks are sorted and aggregated correctly."""
    daily_soak_dir = tmp_path / "daily_soak"
    daily_soak_dir.mkdir()
    out_file = tmp_path / "index.jsonl"

    # Write 3 mock runs out of order chronologically
    run_1_data = _mock_golden_check(
        start_date="2025-06-01",
        end_date="2025-06-05",
        status="accepted",
        release_gate_status="accepted",
        attempted=5,
        accepted=5,
        blocked=0,
        insufficient=0,
        validation_findings=0,
        post_validation_findings=0,
        blockers=[],
    )
    run_2_data = _mock_golden_check(
        start_date="2025-06-06",
        end_date="2025-06-10",
        status="blocked",
        release_gate_status="blocked",
        attempted=5,
        accepted=3,
        blocked=1,
        insufficient=1,
        validation_findings=2,
        post_validation_findings=1,
        blockers=["some_blocker_code", "another_blocker_code"],
    )
    run_3_data = _mock_golden_check(
        start_date="2025-06-11",
        end_date="2025-06-15",
        status="accepted",
        release_gate_status="accepted",
        attempted=5,
        accepted=5,
        blocked=0,
        insufficient=0,
        validation_findings=0,
        post_validation_findings=0,
        blockers=[],
    )

    # Write in jumbled order to verify deterministic sorting
    (daily_soak_dir / "run_2.jsonl").write_text(json.dumps(run_2_data), encoding="utf-8")
    (daily_soak_dir / "run_3.jsonl").write_text(json.dumps(run_3_data), encoding="utf-8")
    (daily_soak_dir / "run_1.jsonl").write_text(json.dumps(run_1_data), encoding="utf-8")

    config = EtfSmaDailySoakAcceptanceHistoryIndexConfig(
        daily_soak_dir=daily_soak_dir,
        out=out_file,
    )
    records = run_etf_sma_daily_soak_acceptance_history_index(config)
    assert len(records) == 6  # Summary, Latest Run, Blocker Trends, + 3 Per-Run records

    # Read output lines
    lines = [json.loads(line) for line in out_file.read_text(encoding="utf-8").splitlines()]
    
    summary = lines[0]
    assert summary["phase"] == "V3J"
    assert summary["record_type"] == "summary"
    assert summary["status"] == "accepted"  # Latest run (run 3) is accepted
    assert summary["indexed_golden_acceptance_count"] == 3
    assert summary["scanned_file_count"] == 3
    assert summary["latest_golden_acceptance_status"] == "accepted"
    assert summary["latest_release_gate_status"] == "accepted"
    assert summary["latest_run_id"] == "2025-06-11_2025-06-15"
    assert summary["latest_as_of"] == "2025-06-15"
    
    # Counts aggregation
    # Attempted: 5 + 5 + 5 = 15
    # Accepted: 5 + 3 + 5 = 13
    # Blocked: 0 + 1 + 0 = 1
    # Insufficient: 0 + 1 + 0 = 1
    # Validation findings: 0 + (2 + 1) + 0 = 3
    assert summary["attempted_count"] == 15
    assert summary["accepted_count"] == 13
    assert summary["blocked_count"] == 1
    assert summary["insufficient_history_count"] == 1
    assert summary["validation_finding_count_total"] == 3

    # Blocker trends
    assert summary["blocker_trends"] == {
        "another_blocker_code": 1,
        "some_blocker_code": 1,
    }

    # Latest record (lines[1])
    latest = lines[1]
    assert latest["record_type"] == "latest_run"
    assert latest["latest_as_of"] == "2025-06-15"
    assert latest["latest_golden_acceptance_status"] == "accepted"
    
    # Blocker trends record (lines[2])
    trends = lines[2]
    assert trends["record_type"] == "blocker_trends"
    assert trends["blocker_trends"] == {
        "another_blocker_code": 1,
        "some_blocker_code": 1,
    }

    # Per-run records (lines[3, 4, 5])
    # Verify they are sorted chronologically
    run_p1 = lines[3]
    assert run_p1["record_type"] == "per_run"
    assert run_p1["run_index"] == 0
    assert run_p1["start_date"] == "2025-06-01"
    assert run_p1["end_date"] == "2025-06-05"

    run_p2 = lines[4]
    assert run_p2["record_type"] == "per_run"
    assert run_p2["run_index"] == 1
    assert run_p2["start_date"] == "2025-06-06"
    assert run_p2["end_date"] == "2025-06-10"
    assert run_p2["golden_acceptance_status"] == "blocked"

    run_p3 = lines[5]
    assert run_p3["record_type"] == "per_run"
    assert run_p3["run_index"] == 2
    assert run_p3["start_date"] == "2025-06-11"
    assert run_p3["end_date"] == "2025-06-15"
    
    # Check V3J safety authorizations on all records
    for rec in lines:
        auths = rec["safety_authorizations"]
        assert auths["live_authorized"] is False
        assert auths["paper_submit_authorized"] is False
        assert auths["paper_broker_reads_authorized"] is False
        assert auths["broker_mutation_authorized"] is False
        assert auths["network_authorized"] is False
        assert auths["credentials_loaded"] is False


def test_history_index_ignores_irrelevant_files(tmp_path: Path) -> None:
    """Verify that indexer ignores non-golden check files and logs scanned count correctly."""
    daily_soak_dir = tmp_path / "daily_soak"
    daily_soak_dir.mkdir()
    out_file = tmp_path / "index.jsonl"

    valid_data = _mock_golden_check(
        start_date="2025-06-01",
        end_date="2025-06-05",
        status="accepted",
        release_gate_status="accepted",
        attempted=5,
        accepted=5,
        blocked=0,
        insufficient=0,
        validation_findings=0,
        post_validation_findings=0,
        blockers=[],
    )
    # Write a valid candidate
    (daily_soak_dir / "valid_golden_check.jsonl").write_text(json.dumps(valid_data), encoding="utf-8")
    
    # Write a non-candidate jsonl (e.g. daily brief)
    brief_data = {
        "phase": "offline_daily_loop_soak_brief",
        "status": "accepted",
    }
    (daily_soak_dir / "brief.jsonl").write_text(json.dumps(brief_data), encoding="utf-8")

    # Write a completely random text file (not scanned as .jsonl)
    (daily_soak_dir / "other.txt").write_text("hello world", encoding="utf-8")

    config = EtfSmaDailySoakAcceptanceHistoryIndexConfig(
        daily_soak_dir=daily_soak_dir,
        out=out_file,
    )
    records = run_etf_sma_daily_soak_acceptance_history_index(config)
    summary = next(r for r in records if r["record_type"] == "summary")
    
    # Scanned: valid_golden_check.jsonl and brief.jsonl (2 jsonl files)
    assert summary["scanned_file_count"] == 2
    assert summary["indexed_golden_acceptance_count"] == 1


def test_history_index_handles_malformed_json_deterministically(tmp_path: Path) -> None:
    """Verify that corrupted JSONL candidate files are counted as validation findings without crashing."""
    daily_soak_dir = tmp_path / "daily_soak"
    daily_soak_dir.mkdir()
    out_file = tmp_path / "index.jsonl"

    valid_data = _mock_golden_check(
        start_date="2025-06-01",
        end_date="2025-06-05",
        status="accepted",
        release_gate_status="accepted",
        attempted=5,
        accepted=5,
        blocked=0,
        insufficient=0,
        validation_findings=0,
        post_validation_findings=0,
        blockers=[],
    )
    (daily_soak_dir / "valid.jsonl").write_text(json.dumps(valid_data), encoding="utf-8")

    # Write a malformed JSON file ending with .jsonl that matches candidate name pattern or contains bad JSON
    # Wait, the indexer checks if it's a candidate by parsing first line. If it's malformed JSON, JSONDecodeError is raised.
    # We treat it as a candidate that failed validation.
    (daily_soak_dir / "corrupted_soak_golden_acceptance.jsonl").write_text("invalid json line {", encoding="utf-8")

    config = EtfSmaDailySoakAcceptanceHistoryIndexConfig(
        daily_soak_dir=daily_soak_dir,
        out=out_file,
    )
    records = run_etf_sma_daily_soak_acceptance_history_index(config)
    summary = next(r for r in records if r["record_type"] == "summary")
    
    assert summary["scanned_file_count"] == 2
    assert summary["indexed_golden_acceptance_count"] == 1
    # Check that validation_finding_count_total aggregates the malformed candidate finding
    assert summary["validation_finding_count_total"] == 1


def test_history_index_cli_integration(tmp_path: Path) -> None:
    """Verify the CLI subcommand exit status codes and output files."""
    daily_soak_dir = tmp_path / "daily_soak"
    daily_soak_dir.mkdir()
    out_file = tmp_path / "index.jsonl"

    # Happy path scenario
    valid_data = _mock_golden_check(
        start_date="2025-06-01",
        end_date="2025-06-05",
        status="accepted",
        release_gate_status="accepted",
        attempted=5,
        accepted=5,
        blocked=0,
        insufficient=0,
        validation_findings=0,
        post_validation_findings=0,
        blockers=[],
    )
    (daily_soak_dir / "valid_run.jsonl").write_text(json.dumps(valid_data), encoding="utf-8")

    exit_code = cli_module.main([
        "etf-sma-daily-soak-acceptance-history-index",
        "--daily-soak-dir", str(daily_soak_dir),
        "--out", str(out_file),
        "--format", "json",
    ])
    assert exit_code == 0
    assert out_file.exists()

    # Blocked scenario
    blocked_data = _mock_golden_check(
        start_date="2025-06-06",
        end_date="2025-06-10",
        status="blocked",
        release_gate_status="blocked",
        attempted=5,
        accepted=3,
        blocked=1,
        insufficient=1,
        validation_findings=0,
        post_validation_findings=0,
        blockers=["some_blocker"],
    )
    (daily_soak_dir / "blocked_run.jsonl").write_text(json.dumps(blocked_data), encoding="utf-8")

    exit_code = cli_module.main([
        "etf-sma-daily-soak-acceptance-history-index",
        "--daily-soak-dir", str(daily_soak_dir),
        "--out", str(out_file),
        "--format", "json",
    ])
    assert exit_code == 1  # 1 because latest run status is blocked
    
    # Invalid argument raises SystemExit (exits with 2)
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main([
            "etf-sma-daily-soak-acceptance-history-index",
            "--invalid-arg-unwanted", "some-value",
        ])
    assert excinfo.value.code == 2
