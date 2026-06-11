from __future__ import annotations

import json
import os
import shutil
import pytest
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_soak_release_gate import (
    EtfSmaDailySoakReleaseGateConfig,
    run_etf_sma_daily_soak_release_gate,
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


def _write_mock_brief(
    path: Path,
    *,
    status: str = "accepted",
    finding_count: int = 0,
    missing_expected_artifact_count: int = 0,
    absolute_path_finding_count: int = 0,
    regression_status: str = "matched",
    live_trading_authorized: bool = False,
    extra_mods: dict[str, any] | None = None,
) -> None:
    payload = {
        "phase": "offline_daily_loop_soak_brief",
        "status": status,
        "source_soak_rollup_path": "runs/daily_soak/soak_rollup.jsonl",
        "daily_root": "runs/daily",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "attempted_date_count": 5,
        "accepted_date_count": 5,
        "blocked_date_count": 0,
        "insufficient_history_date_count": 0,
        "finding_count": finding_count,
        "attempted_dates": ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"],
        "accepted_dates": ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"],
        "blocked_dates": [],
        "insufficient_history_dates": [],
        "posture_counts": {"bullish": 5},
        "cycle_decision_counts": {"hold/noop": 5},
        "blocker_counts": {},
        "missing_expected_artifact_count": missing_expected_artifact_count,
        "missing_expected_artifacts": [],
        "absolute_path_finding_count": absolute_path_finding_count,
        "regression_status": regression_status,
        "regression_findings": [],
        "artifact_paths": ["runs/daily/2026-06-01/cycle.jsonl"],
        "live_trading_authorized": live_trading_authorized,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }
    if extra_mods:
        payload.update(extra_mods)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_mock_validation(
    path: Path,
    *,
    status: str = "passed",
    finding_count: int = 0,
    extra_flags: dict[str, bool] | None = None,
) -> None:
    safety_flags = {
        "submitted": False,
        "mutated": False,
        "broker_accessed": False,
        "network_accessed": False,
        "credentials_read": False,
        "live_authorized": False,
        "paper_submit_authorized": False,
        "scanned_files_mutated": False,
    }
    if extra_flags:
        safety_flags.update(extra_flags)
    payload = {
        "report_schema_version": 1,
        "tool": "validate-artifacts",
        "input_root": "runs/daily",
        "output_path": "runs/validation/artifact_validation_report.jsonl",
        "status": status,
        "scanned_file_count": 50,
        "scanned_record_count": 500,
        "file_result_count": 50,
        "finding_count": finding_count,
        "required_keys_checked": [],
        "safety_flags": safety_flags,
        "file_results": [],
        "findings": [],
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_release_gate_happy_path(tmp_path: Path) -> None:
    """Verify happy-path runs compile accepted release packets correctly."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"
    
    # Use workspace-relative paths to avoid triggering the absolute path check on outputs
    out_jsonl = "runs/test_soak_release_gate_happy.jsonl"
    out_text = "runs/test_soak_release_gate_happy.txt"

    # Clean up any leftover artifacts
    for p in (out_jsonl, out_text):
        if Path(p).exists():
            os.remove(p)

    try:
        _write_mock_brief(brief_path)
        _write_mock_validation(val_path)

        config = EtfSmaDailySoakReleaseGateConfig(
            soak_brief_jsonl=brief_path,
            artifact_validation_jsonl=val_path,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_release_gate(config)

        assert payload["status"] == "accepted"
        assert payload["release_gate_status"] == "accepted"
        assert payload["release_gate_blockers"] == []
        assert payload["finding_count"] == 0
        assert payload["artifact_validation_finding_count"] == 0
        assert payload["missing_expected_artifact_count"] == 0
        assert payload["absolute_path_finding_count"] == 0
        assert payload["regression_status"] == "matched"
        assert payload["live_trading_authorized"] is False
        assert payload["paper_submit_authorized"] is False
        assert payload["broker_mutation_authorized"] is False
        assert payload["paper_broker_reads_authorized"] is False
        assert payload["network_access_authorized"] is False
        assert payload["credential_loading_authorized"] is False

        assert Path(out_jsonl).exists()
        assert Path(out_text).exists()
    finally:
        for p in (out_jsonl, out_text):
            if Path(p).exists():
                os.remove(p)


def test_release_gate_block_validation_findings(tmp_path: Path) -> None:
    """Verify that release gate blocks if artifact validation report has findings."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"

    _write_mock_brief(brief_path)
    # Write validation with 1 finding and failed status
    _write_mock_validation(val_path, status="failed", finding_count=1)

    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl=tmp_path / "soak_release_gate.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )

    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "artifact_validation_findings" in payload["release_gate_blockers"]
    assert payload["artifact_validation_finding_count"] == 1


def test_release_gate_block_soak_brief_absolute_paths(tmp_path: Path) -> None:
    """Verify that release gate blocks if soak brief has absolute path findings."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"

    # Write brief with absolute path findings
    _write_mock_brief(brief_path, status="completed_with_findings", absolute_path_finding_count=1)
    _write_mock_validation(val_path)

    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl=tmp_path / "soak_release_gate.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )

    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "absolute_path_findings" in payload["release_gate_blockers"]
    assert payload["absolute_path_finding_count"] == 1


def test_release_gate_block_missing_artifacts(tmp_path: Path) -> None:
    """Verify that release gate blocks if expected artifacts are missing."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"

    # Write brief with missing artifacts
    _write_mock_brief(brief_path, status="completed_with_findings", missing_expected_artifact_count=2)
    _write_mock_validation(val_path)

    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl=tmp_path / "soak_release_gate.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )

    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "missing_expected_artifacts" in payload["release_gate_blockers"]
    assert payload["missing_expected_artifact_count"] == 2


def test_release_gate_block_regression_mismatch(tmp_path: Path) -> None:
    """Verify that release gate blocks if soak brief reports a baseline mismatch regression."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"

    # Write brief with mismatch regression status
    _write_mock_brief(brief_path, regression_status="mismatch")
    _write_mock_validation(val_path)

    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl=tmp_path / "soak_release_gate.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )

    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "regression_mismatch" in payload["release_gate_blockers"]


def test_release_gate_block_authorization_true(tmp_path: Path) -> None:
    """Verify that release gate blocks if any authorization boolean is True."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"

    # Case A: live_trading_authorized True in brief
    _write_mock_brief(brief_path, live_trading_authorized=True)
    _write_mock_validation(val_path)

    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl=tmp_path / "soak_release_gate.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )

    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "authorization_boolean_true" in payload["release_gate_blockers"]

    # Case B: safety_flags in validation has True
    _write_mock_brief(brief_path, live_trading_authorized=False)
    _write_mock_validation(val_path, extra_flags={"submitted": True})

    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "authorization_boolean_true" in payload["release_gate_blockers"]


def test_release_gate_block_missing_required_fields(tmp_path: Path) -> None:
    """Verify that release gate blocks if required brief fields are missing."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"

    # Write a brief missing "start_date" and "regression_status"
    payload = {
        "phase": "offline_daily_loop_soak_brief",
        "status": "accepted",
        "end_date": "2026-06-05",
        "attempted_date_count": 5,
        "accepted_date_count": 5,
        "blocked_date_count": 0,
        "insufficient_history_date_count": 0,
        "finding_count": 0,
        "artifact_paths": [],
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }
    brief_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    _write_mock_validation(val_path)

    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl=tmp_path / "soak_release_gate.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )

    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    # Finders should flag the missing fields
    assert any(b.startswith("missing_required_v3f_fields:") for b in payload["release_gate_blockers"])


def test_release_gate_block_unsafe_output_paths(tmp_path: Path) -> None:
    """Verify that release gate blocks on absolute, drive letter, backslash, or user home output paths."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"

    _write_mock_brief(brief_path)
    _write_mock_validation(val_path)

    # Case A: Backslashes in path
    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl="runs\\unsafe\\path.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )
    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "unsafe_output_path" in payload["release_gate_blockers"]

    # Case B: Absolute path
    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl="/absolute/path.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )
    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "unsafe_output_path" in payload["release_gate_blockers"]

    # Case C: User Home indicators (e.g. ~ or /Users/ or /home/)
    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl=brief_path,
        artifact_validation_jsonl=val_path,
        output_jsonl="~/runs/unsafe.jsonl",
        output_text=tmp_path / "soak_release_gate.txt",
    )
    payload = run_etf_sma_daily_soak_release_gate(config)
    assert payload["status"] == "blocked"
    assert "unsafe_output_path" in payload["release_gate_blockers"]


def test_release_gate_input_file_validation_error() -> None:
    """Verify that core code raises ValidationError (which exits 2) on missing files."""
    config = EtfSmaDailySoakReleaseGateConfig(
        soak_brief_jsonl="nonexistent_brief.jsonl",
        artifact_validation_jsonl="nonexistent_val.jsonl",
    )
    with pytest.raises(ValidationError):
        run_etf_sma_daily_soak_release_gate(config)


def test_release_gate_cli_exit_codes(tmp_path: Path) -> None:
    """Verify that CLI exits 0 for accepted releases and 1 for blocked releases."""
    brief_path = tmp_path / "soak_operator_brief.jsonl"
    val_path = tmp_path / "artifact_validation_report.jsonl"
    
    # Use workspace-relative paths to avoid triggering the absolute path check on outputs
    out_jsonl = "runs/test_soak_release_gate_cli.jsonl"
    out_text = "runs/test_soak_release_gate_cli.txt"

    for p in (out_jsonl, out_text):
        if Path(p).exists():
            os.remove(p)

    try:
        # Scenario 1: Happy path (Exit code 0)
        _write_mock_brief(brief_path)
        _write_mock_validation(val_path)

        exit_code = cli_module.main([
            "etf-sma-daily-soak-release-gate",
            "--soak-brief-jsonl", str(brief_path),
            "--artifact-validation-jsonl", str(val_path),
            "--output-jsonl", out_jsonl,
            "--output-text", out_text,
            "--format", "json",
        ])
        assert exit_code == 0
        assert Path(out_jsonl).exists()

        # Scenario 2: Blocked path (Exit code 1)
        _write_mock_validation(val_path, status="failed", finding_count=2)
        exit_code = cli_module.main([
            "etf-sma-daily-soak-release-gate",
            "--soak-brief-jsonl", str(brief_path),
            "--artifact-validation-jsonl", str(val_path),
            "--output-jsonl", out_jsonl,
            "--output-text", out_text,
            "--format", "json",
        ])
        assert exit_code == 1
    finally:
        for p in (out_jsonl, out_text):
            if Path(p).exists():
                os.remove(p)
