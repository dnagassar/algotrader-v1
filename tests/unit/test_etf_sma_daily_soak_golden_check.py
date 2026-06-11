from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_soak_golden_check import (
    EtfSmaDailySoakGoldenCheckConfig,
    run_etf_sma_daily_soak_golden_check,
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


def _get_mock_rollup() -> dict[str, any]:
    return {
        "phase": "offline_daily_loop_soak",
        "status": "accepted",
        "start_date": "2025-06-01",
        "end_date": "2025-06-10",
        "attempted_dates": ["2025-06-01", "2025-06-02"],
        "accepted_dates": ["2025-06-01", "2025-06-02"],
        "blocked_dates": [],
        "insufficient_history_dates": [],
        "finding_count": 0,
        "artifact_paths": ["runs/test_soak_golden_check/soak_rollup.jsonl"],
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }


def _get_mock_brief() -> dict[str, any]:
    return {
        "phase": "offline_daily_loop_soak_brief",
        "status": "accepted",
        "source_soak_rollup_path": "runs/test_soak_golden_check/soak_rollup.jsonl",
        "daily_root": "runs/test_soak_golden_check",
        "start_date": "2025-06-01",
        "end_date": "2025-06-10",
        "attempted_date_count": 2,
        "accepted_date_count": 2,
        "blocked_date_count": 0,
        "insufficient_history_date_count": 0,
        "finding_count": 0,
        "attempted_dates": ["2025-06-01", "2025-06-02"],
        "accepted_dates": ["2025-06-01", "2025-06-02"],
        "blocked_dates": [],
        "insufficient_history_dates": [],
        "posture_counts": {"bullish": 2},
        "cycle_decision_counts": {"hold/noop": 2},
        "blocker_counts": {},
        "missing_expected_artifact_count": 0,
        "missing_expected_artifacts": [],
        "absolute_path_finding_count": 0,
        "regression_status": "not_requested",
        "regression_findings": [],
        "artifact_paths": [
            "runs/test_soak_golden_check/soak_rollup.jsonl",
            "runs/test_soak_golden_check/soak_operator_brief.jsonl",
        ],
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }


def _get_mock_validation(status: str = "passed", finding_count: int = 0) -> MagicMock:
    report = MagicMock()
    report.status = status
    report.finding_count = finding_count
    report.scanned_file_count = 5
    report.scanned_record_count = 50
    report.safety_flags = {
        "submitted": False,
        "mutated": False,
        "broker_accessed": False,
        "network_accessed": False,
        "credentials_read": False,
        "live_authorized": False,
        "paper_submit_authorized": False,
        "scanned_files_mutated": False,
    }
    return report


def _get_mock_release_gate(status: str = "accepted") -> dict[str, any]:
    return {
        "phase": "offline_daily_loop_soak_release_gate",
        "status": status,
        "source_soak_brief_path": "runs/test_soak_golden_check/soak_operator_brief.jsonl",
        "source_artifact_validation_path": "runs/validation/artifact_validation_report.jsonl",
        "start_date": "2025-06-01",
        "end_date": "2025-06-10",
        "attempted_date_count": 2,
        "accepted_date_count": 2,
        "blocked_date_count": 0,
        "insufficient_history_date_count": 0,
        "finding_count": 0,
        "artifact_validation_finding_count": 0,
        "missing_expected_artifact_count": 0,
        "absolute_path_finding_count": 0,
        "regression_status": "not_requested",
        "release_gate_status": status,
        "release_gate_blockers": [],
        "artifact_paths": [
            "runs/test_soak_golden_check/soak_rollup.jsonl",
            "runs/test_soak_golden_check/soak_operator_brief.jsonl",
            "runs/test_soak_golden_check/soak_release_gate.jsonl",
        ],
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_happy_path(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify end-to-end happy path execution using workspace relative paths."""
    mock_soak.return_value = _get_mock_rollup()
    mock_brief.return_value = _get_mock_brief()
    mock_gate.return_value = _get_mock_release_gate()
    mock_val.return_value = _get_mock_validation()

    # Clean up test directories
    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "accepted"
        assert payload["golden_acceptance_status"] == "accepted"
        assert payload["golden_acceptance_blockers"] == []
        assert out_jsonl.exists()
        assert out_text.exists()
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_validation_findings(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify that golden check blocks if artifact validation report has findings."""
    mock_soak.return_value = _get_mock_rollup()
    mock_brief.return_value = _get_mock_brief()
    mock_gate.return_value = _get_mock_release_gate()
    
    # First validation returns a report with 1 finding
    mock_val.side_effect = [
        _get_mock_validation(status="failed", finding_count=1),
        _get_mock_validation(status="passed", finding_count=0),
    ]

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert "artifact_validation_findings" in payload["golden_acceptance_blockers"]
        assert payload["artifact_validation_finding_count"] == 1
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_release_gate_blocked(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify that golden check blocks if release gate blocks."""
    mock_soak.return_value = _get_mock_rollup()
    mock_brief.return_value = _get_mock_brief()
    mock_gate.return_value = _get_mock_release_gate(status="blocked")
    mock_val.return_value = _get_mock_validation()

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert "release_gate_blocked" in payload["golden_acceptance_blockers"]
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_post_validation_findings(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify that golden check blocks if post-release artifact validation has findings."""
    mock_soak.return_value = _get_mock_rollup()
    mock_brief.return_value = _get_mock_brief()
    mock_gate.return_value = _get_mock_release_gate()
    
    # Second validation returns failed
    mock_val.side_effect = [
        _get_mock_validation(status="passed", finding_count=0),
        _get_mock_validation(status="failed", finding_count=2),
    ]

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert "post_release_artifact_validation_findings" in payload["golden_acceptance_blockers"]
        assert payload["post_release_artifact_validation_finding_count"] == 2
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_unsafe_artifact_paths(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify that golden check blocks on absolute or backslashed artifact paths."""
    mock_soak.return_value = _get_mock_rollup()
    mock_brief.return_value = _get_mock_brief()
    mock_val.return_value = _get_mock_validation()

    # Add an absolute path in artifact_paths returned by release gate
    gate_payload = _get_mock_release_gate()
    gate_payload["artifact_paths"].append("/absolute/unwanted/path.jsonl")
    mock_gate.return_value = gate_payload

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert "unsafe_artifact_path" in payload["golden_acceptance_blockers"]
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_auth_boolean_true(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify that golden check blocks if any authorization boolean is True."""
    mock_soak.return_value = _get_mock_rollup()
    mock_gate.return_value = _get_mock_release_gate()
    mock_val.return_value = _get_mock_validation()

    # Case: live_trading_authorized True in brief
    brief_data = _get_mock_brief()
    brief_data["live_trading_authorized"] = True
    mock_brief.return_value = brief_data

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert "authorization_boolean_true" in payload["golden_acceptance_blockers"]
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=True)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_git_tracked(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify that golden check blocks if any generated file is tracked or staged in git."""
    mock_soak.return_value = _get_mock_rollup()
    mock_brief.return_value = _get_mock_brief()
    mock_gate.return_value = _get_mock_release_gate()
    mock_val.return_value = _get_mock_validation()

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert "generated_artifacts_tracked_or_staged" in payload["golden_acceptance_blockers"]
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_crossed_roots(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify that golden check blocks if artifacts cross unexpected roots."""
    mock_soak.return_value = _get_mock_rollup()
    mock_brief.return_value = _get_mock_brief()
    mock_val.return_value = _get_mock_validation()

    # Add a crossed root path (like runs/daily/file.jsonl instead of runs/test_soak_golden_check/)
    gate_payload = _get_mock_release_gate()
    gate_payload["artifact_paths"].append("runs/daily/crossed_file.jsonl")
    mock_gate.return_value = gate_payload

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert "artifacts_crossed_roots" in payload["golden_acceptance_blockers"]
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_missing_upstream_fields(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify that golden check blocks if required fields are missing from upstream artifacts."""
    # Soak rollup is missing 'attempted_dates'
    rollup_data = _get_mock_rollup()
    rollup_data.pop("attempted_dates")
    mock_soak.return_value = rollup_data

    mock_brief.return_value = _get_mock_brief()
    mock_gate.return_value = _get_mock_release_gate()
    mock_val.return_value = _get_mock_validation()

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert any(b.startswith("missing_required_v3e_fields:") for b in payload["golden_acceptance_blockers"])
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_blocks_on_phase_exception(mock_soak) -> None:
    """Verify that golden check blocks if any called phase raises an exception."""
    mock_soak.side_effect = ValueError("Fatal simulation failure")

    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        config = EtfSmaDailySoakGoldenCheckConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            output_root=test_root,
            validation_output=test_val,
            post_release_validation_output=test_post_val,
            output_jsonl=out_jsonl,
            output_text=out_text,
        )

        payload = run_etf_sma_daily_soak_golden_check(config)

        assert payload["status"] == "blocked"
        assert any("soak_phase_failed: Fatal simulation failure" in b for b in payload["golden_acceptance_blockers"])
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)


@patch("algotrader.execution.etf_sma_daily_soak_golden_check._is_git_tracked_or_staged", return_value=False)
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.write_validation_report")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.validate_tree")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_release_gate")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak_brief")
@patch("algotrader.execution.etf_sma_daily_soak_golden_check.run_etf_sma_daily_soak")
def test_golden_check_cli_exit_codes(
    mock_soak,
    mock_brief,
    mock_gate,
    mock_val,
    mock_write,
    mock_git,
) -> None:
    """Verify CLI exit codes for etf-sma-daily-soak-golden-check."""
    test_root = Path("runs/test_soak_golden_check")
    test_val = Path("runs/validation/test_artifact_validation_report.jsonl")
    test_post_val = Path("runs/validation/test_artifact_validation_after_release_gate_report.jsonl")
    out_jsonl = Path("runs/test_soak_golden_check/soak_golden_acceptance.jsonl")
    out_text = Path("runs/test_soak_golden_check/soak_golden_acceptance.txt")

    for p in (test_val, test_post_val):
        if p.exists():
            os.remove(p)
    if test_root.exists():
        shutil.rmtree(test_root, ignore_errors=True)

    try:
        # Scenario 1: Happy path exits 0
        mock_soak.return_value = _get_mock_rollup()
        mock_brief.return_value = _get_mock_brief()
        mock_gate.return_value = _get_mock_release_gate()
        mock_val.return_value = _get_mock_validation()

        exit_code = cli_module.main([
            "etf-sma-daily-soak-golden-check",
            "--start-date", "2025-06-01",
            "--end-date", "2025-06-10",
            "--bars-csv", "tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            "--reconciliation-state-path", "tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            "--output-root", str(test_root),
            "--validation-output", str(test_val),
            "--post-release-validation-output", str(test_post_val),
            "--output-jsonl", str(out_jsonl),
            "--output-text", str(out_text),
            "--format", "json",
        ])
        assert exit_code == 0

        # Scenario 2: Blocked path exits 1
        mock_gate.return_value = _get_mock_release_gate(status="blocked")
        exit_code = cli_module.main([
            "etf-sma-daily-soak-golden-check",
            "--start-date", "2025-06-01",
            "--end-date", "2025-06-10",
            "--bars-csv", "tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
            "--reconciliation-state-path", "tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
            "--output-root", str(test_root),
            "--validation-output", str(test_val),
            "--post-release-validation-output", str(test_post_val),
            "--output-jsonl", str(out_jsonl),
            "--output-text", str(out_text),
            "--format", "json",
        ])
        assert exit_code == 1
    finally:
        for p in (test_val, test_post_val):
            if p.exists():
                os.remove(p)
        if test_root.exists():
            shutil.rmtree(test_root, ignore_errors=True)
