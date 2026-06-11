from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_soak_operator_summary import (
    EtfSmaDailySoakOperatorSummaryConfig,
    run_etf_sma_daily_soak_operator_summary,
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


def _create_v3j_payload(
    latest_status: str = "accepted",
    golden_status: str = "accepted",
    release_status: str = "accepted",
    findings: int = 0,
    attempted: int = 5,
    accepted: int = 5,
    blocked: int = 0,
    insufficient: int = 0,
    blocker_trends: dict[str, int] = None,
    latest_blockers: list[str] = None,
    override_safety: dict[str, bool] = None,
) -> list[dict[str, Any]]:
    """Helper to generate mock V3J records for testing."""
    safety_auths = {
        "live_authorized": False,
        "paper_submit_authorized": False,
        "paper_broker_reads_authorized": False,
        "broker_mutation_authorized": False,
        "network_authorized": False,
        "credentials_loaded": False,
    }
    if override_safety:
        safety_auths.update(override_safety)

    rec_trends = blocker_trends or {}
    rec_blockers = latest_blockers or []

    # 1. Summary Record
    summary = {
        "phase": "V3J",
        "record_type": "summary",
        "status": latest_status,
        "input_daily_soak_dir": "runs/daily_soak",
        "scanned_file_count": 2,
        "indexed_golden_acceptance_count": 1,
        "latest_golden_acceptance_status": golden_status,
        "latest_release_gate_status": release_status,
        "latest_run_id": "2025-06-01_2025-06-05",
        "latest_as_of": "2025-06-05",
        "validation_finding_count_total": findings,
        "attempted_count": attempted,
        "accepted_count": accepted,
        "blocked_count": blocked,
        "insufficient_history_count": insufficient,
        "blocker_trends": rec_trends,
        "key_artifact_paths": ["runs/daily_soak/2025-06-01_2025-06-05/rollup.jsonl"],
        "safety_authorizations": safety_auths,
    }

    # 2. Latest Run Record
    latest_run = {
        "phase": "V3J",
        "record_type": "latest_run",
        "latest_as_of": "2025-06-05",
        "latest_golden_acceptance_status": golden_status,
        "latest_release_gate_status": release_status,
        "key_artifact_paths": ["runs/daily_soak/2025-06-01_2025-06-05/rollup.jsonl"],
        "safety_authorizations": safety_auths,
    }

    # 3. Blocker Trends Record
    trends = {
        "phase": "V3J",
        "record_type": "blocker_trends",
        "blocker_trends": rec_trends,
        "safety_authorizations": safety_auths,
    }

    # 4. Per Run Record
    per_run = {
        "phase": "V3J",
        "record_type": "per_run",
        "run_index": 0,
        "start_date": "2025-06-01",
        "end_date": "2025-06-05",
        "golden_acceptance_status": golden_status,
        "release_gate_status": release_status,
        "validation_finding_count": findings,
        "attempted_date_count": attempted,
        "accepted_date_count": accepted,
        "blocked_date_count": blocked,
        "insufficient_history_date_count": insufficient,
        "blockers": rec_blockers,
        "file_path": "runs/daily_soak/soak_golden_acceptance.jsonl",
        "safety_authorizations": safety_auths,
    }

    return [summary, latest_run, trends, per_run]


def test_operator_summary_proceed_offline(tmp_path: Path) -> None:
    """Verify that a green V3J index correctly produces proceed_offline classification."""
    index_file = tmp_path / "v3j_index.jsonl"
    out_file = tmp_path / "v3k_summary.jsonl"
    text_file = tmp_path / "v3k_summary.md"

    # Setup green records
    records = _create_v3j_payload()
    lines_str = "\n".join(json.dumps(r) for r in records) + "\n"
    index_file.write_text(lines_str, encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(
        history_index=index_file,
        out=out_file,
        text_out=text_file,
    )

    summary_records = run_etf_sma_daily_soak_operator_summary(config)

    # 4 records written
    assert len(summary_records) == 4
    assert out_file.exists()
    assert text_file.exists()

    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")
    assert summary_rec["next_safe_action_classification"] == "proceed_offline"
    assert "safety invariants hold" in summary_rec["next_safe_action_reason"]

    # Verify counts preserved
    assert summary_rec["attempted_count"] == 5
    assert summary_rec["accepted_count"] == 5
    assert summary_rec["blocked_count"] == 0
    assert summary_rec["insufficient_history_count"] == 0
    assert summary_rec["validation_finding_count_total"] == 0


def test_operator_summary_proceed_offline_requirements(tmp_path: Path) -> None:
    """Verify that proceed_offline strictly requires all green preconditions."""
    index_file = tmp_path / "v3j_index.jsonl"
    out_file = tmp_path / "v3k_summary.jsonl"

    # Scenario: Golden status is accepted, but findings count is > 0
    records = _create_v3j_payload(findings=1)
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")
    
    # Should not proceed_offline because findings > 0
    assert summary_rec["next_safe_action_classification"] == "repair_required"


def test_operator_summary_inspect_blockers_no_history(tmp_path: Path) -> None:
    """Verify that blocked status due ONLY to deterministic no-history produces inspect_blockers."""
    index_file = tmp_path / "v3j_index.jsonl"
    out_file = tmp_path / "v3k_summary.jsonl"

    # Setup blocked status, but blockers are only insufficient_history
    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="accepted",
        attempted=5,
        accepted=0,
        blocked=0,
        insufficient=5,
        latest_blockers=["insufficient_history"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    assert summary_rec["next_safe_action_classification"] == "inspect_blockers"
    assert "known deterministic no-history/insufficient-history" in summary_rec["next_safe_action_reason"]


def test_operator_summary_release_gate_blocked_not_harmless(tmp_path: Path) -> None:
    """Verify that generic release_gate_blocked alone is not treated as harmless if findings/mismatches exist."""
    index_file = tmp_path / "v3j_index.jsonl"
    out_file = tmp_path / "v3k_summary.jsonl"

    # Scenario: Blocked by release_gate_blocked, but insufficient_history count is 0 (generic block)
    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="blocked",
        attempted=5,
        accepted=5,
        blocked=0,
        insufficient=0,
        latest_blockers=["release_gate_blocked"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    # Generic release gate block is repair_required
    assert summary_rec["next_safe_action_classification"] == "repair_required"


def test_operator_summary_missing_or_empty_input(tmp_path: Path) -> None:
    """Verify that missing or empty index produces deterministic no_history."""
    non_existent = tmp_path / "non_existent.jsonl"
    out_file = tmp_path / "v3k_summary.jsonl"

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=non_existent, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    assert summary_rec["next_safe_action_classification"] == "no_history"
    assert "missing or empty" in summary_rec["next_safe_action_reason"]
    assert out_file.exists()


def test_operator_summary_malformed_jsonl(tmp_path: Path) -> None:
    """Verify that malformed JSONL produces repair_required."""
    index_file = tmp_path / "malformed.jsonl"
    out_file = tmp_path / "v3k_summary.jsonl"

    index_file.write_text("invalid json lines {\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    assert summary_rec["next_safe_action_classification"] == "repair_required"
    assert "Malformed JSONL records found" in summary_rec["next_safe_action_reason"]
    assert out_file.exists()


def test_operator_summary_non_false_safety_override(tmp_path: Path) -> None:
    """Verify that non-false source safety authorization booleans force repair_required."""
    index_file = tmp_path / "safety_override.jsonl"
    out_file = tmp_path / "v3k_summary.jsonl"

    # live_authorized = True
    records = _create_v3j_payload(override_safety={"live_authorized": True})
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    assert summary_rec["next_safe_action_classification"] == "repair_required"
    assert "non-false/truthy safety authorization flags" in summary_rec["next_safe_action_reason"]


def test_operator_summary_recurring_blockers_sorting(tmp_path: Path) -> None:
    """Verify that blocker trends are summarized and recurring ones sorted alphabetically."""
    index_file = tmp_path / "blockers.jsonl"
    out_file = tmp_path / "v3k_summary.jsonl"

    # Setup blockers with counts
    # "beta_blocker" count 2, "alpha_blocker" count 3, "charlie_blocker" count 1
    trends_dict = {
        "beta_blocker": 2,
        "alpha_blocker": 3,
        "charlie_blocker": 1,
    }
    records = _create_v3j_payload(blocker_trends=trends_dict)
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    # Only "alpha_blocker" and "beta_blocker" appear >= 2 times
    # Sorted alphabetically: ["alpha_blocker", "beta_blocker"]
    assert summary_rec["recurring_blockers"] == ["alpha_blocker", "beta_blocker"]
    assert summary_rec["blocker_trend_summary"] == {
        "alpha_blocker": 3,
        "beta_blocker": 2,
        "charlie_blocker": 1,
    }


def test_operator_summary_text_determinism(tmp_path: Path) -> None:
    """Verify that markdown reports are fully deterministic and repeated runs match exactly."""
    index_file = tmp_path / "index.jsonl"
    out_file = tmp_path / "out.jsonl"
    text_file_1 = tmp_path / "report_1.md"
    text_file_2 = tmp_path / "report_2.md"

    records = _create_v3j_payload()
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config_1 = EtfSmaDailySoakOperatorSummaryConfig(
        history_index=index_file,
        out=out_file,
        text_out=text_file_1,
    )
    run_etf_sma_daily_soak_operator_summary(config_1)

    config_2 = EtfSmaDailySoakOperatorSummaryConfig(
        history_index=index_file,
        out=out_file,
        text_out=text_file_2,
    )
    run_etf_sma_daily_soak_operator_summary(config_2)

    content_1 = text_file_1.read_text(encoding="utf-8")
    content_2 = text_file_2.read_text(encoding="utf-8")

    assert content_1 == content_2
    assert "# Daily Lab Acceptance Operator Summary" in content_1


def test_operator_summary_cli_integration_exit_codes(tmp_path: Path) -> None:
    """Verify CLI exit status codes under green/blocked/missing index conditions."""
    index_file = tmp_path / "index.jsonl"
    out_file = tmp_path / "out.jsonl"

    # Scenario 1: Green V3J index => CLI exit code 0
    records = _create_v3j_payload()
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    exit_code = cli_module.main([
        "etf-sma-daily-soak-operator-summary",
        "--history-index", str(index_file),
        "--out", str(out_file),
        "--format", "json",
    ])
    assert exit_code == 0

    # Scenario 2: Blocked V3J index => CLI exit code 1
    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="blocked",
        latest_blockers=["release_gate_blocked"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    exit_code = cli_module.main([
        "etf-sma-daily-soak-operator-summary",
        "--history-index", str(index_file),
        "--out", str(out_file),
        "--format", "json",
    ])
    assert exit_code == 1

    # Scenario 3: Malformed index file => CLI exit code 1 (Summary record still written)
    index_file.write_text("malformed content {\n", encoding="utf-8")
    exit_code = cli_module.main([
        "etf-sma-daily-soak-operator-summary",
        "--history-index", str(index_file),
        "--out", str(out_file),
        "--format", "json",
    ])
    assert exit_code == 1
    assert out_file.exists()

    # Scenario 4: Nonexistent input file => CLI exit code 1 (Summary record still written)
    non_existent = tmp_path / "non_existent.jsonl"
    exit_code = cli_module.main([
        "etf-sma-daily-soak-operator-summary",
        "--history-index", str(non_existent),
        "--out", str(out_file),
        "--format", "json",
    ])
    assert exit_code == 1
    assert out_file.exists()

    # Scenario 5: Missing CLI parameters or invalid arg => SystemExit / exit code 2
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main([
            "etf-sma-daily-soak-operator-summary",
            "--invalid-option-unwanted", "some-value",
        ])
    assert excinfo.value.code == 2


def test_operator_summary_regression_release_gate_blocked_alone(tmp_path: Path) -> None:
    """Verify that release_gate_blocked alone with insufficient_history_count > 0 classifies as repair_required."""
    index_file = tmp_path / "index.jsonl"
    out_file = tmp_path / "out.jsonl"

    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="blocked",
        attempted=5,
        accepted=0,
        insufficient=5,
        latest_blockers=["release_gate_blocked"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    assert summary_rec["next_safe_action_classification"] == "repair_required"


def test_operator_summary_regression_release_gate_blocked_plus_insufficient_history(tmp_path: Path) -> None:
    """Verify that release_gate_blocked alongside explicit insufficient_history classifies as inspect_blockers."""
    index_file = tmp_path / "index.jsonl"
    out_file = tmp_path / "out.jsonl"

    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="blocked",
        attempted=5,
        accepted=0,
        insufficient=5,
        latest_blockers=["release_gate_blocked", "insufficient_history"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    assert summary_rec["next_safe_action_classification"] == "inspect_blockers"


def test_operator_summary_regression_release_gate_blocked_plus_no_history(tmp_path: Path) -> None:
    """Verify that release_gate_blocked alongside explicit no_history classifies as inspect_blockers."""
    index_file = tmp_path / "index.jsonl"
    out_file = tmp_path / "out.jsonl"

    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="blocked",
        attempted=5,
        accepted=0,
        insufficient=5,
        latest_blockers=["release_gate_blocked", "no_history"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
    summary_records = run_etf_sma_daily_soak_operator_summary(config)
    summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

    assert summary_rec["next_safe_action_classification"] == "inspect_blockers"


def test_operator_summary_regression_release_gate_blocked_plus_no_data(tmp_path: Path) -> None:
    """Verify that release_gate_blocked alongside explicit no-data/no_data classifies as inspect_blockers."""
    index_file = tmp_path / "index.jsonl"
    out_file = tmp_path / "out.jsonl"

    for no_data_token in ["no-data", "no_data"]:
        records = _create_v3j_payload(
            latest_status="blocked",
            golden_status="blocked",
            release_status="blocked",
            attempted=5,
            accepted=0,
            insufficient=5,
            latest_blockers=["release_gate_blocked", no_data_token],
        )
        index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

        config = EtfSmaDailySoakOperatorSummaryConfig(history_index=index_file, out=out_file)
        summary_records = run_etf_sma_daily_soak_operator_summary(config)
        summary_rec = next(r for r in summary_records if r.get("record_type") == "summary")

        assert summary_rec["next_safe_action_classification"] == "inspect_blockers"


def test_operator_summary_regression_exit_code_for_non_green(tmp_path: Path) -> None:
    """Confirm exit code is 1 for the repaired non-green deterministic summaries."""
    index_file = tmp_path / "index.jsonl"
    out_file = tmp_path / "out.jsonl"

    # Scenario 1: release_gate_blocked alone => repair_required => exit code 1
    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="blocked",
        attempted=5,
        accepted=0,
        insufficient=5,
        latest_blockers=["release_gate_blocked"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    exit_code = cli_module.main([
        "etf-sma-daily-soak-operator-summary",
        "--history-index", str(index_file),
        "--out", str(out_file),
        "--format", "json",
    ])
    assert exit_code == 1

    # Scenario 2: release_gate_blocked + insufficient_history => inspect_blockers => exit code 1
    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="blocked",
        attempted=5,
        accepted=0,
        insufficient=5,
        latest_blockers=["release_gate_blocked", "insufficient_history"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    exit_code = cli_module.main([
        "etf-sma-daily-soak-operator-summary",
        "--history-index", str(index_file),
        "--out", str(out_file),
        "--format", "json",
    ])
    assert exit_code == 1


def test_operator_summary_regression_determinism_repeated(tmp_path: Path) -> None:
    """Confirm repeated output remains deterministic."""
    index_file = tmp_path / "index.jsonl"
    out_file_1 = tmp_path / "out_1.jsonl"
    out_file_2 = tmp_path / "out_2.jsonl"

    records = _create_v3j_payload(
        latest_status="blocked",
        golden_status="blocked",
        release_status="blocked",
        attempted=5,
        accepted=0,
        insufficient=5,
        latest_blockers=["release_gate_blocked", "insufficient_history"],
    )
    index_file.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    # First run
    cli_module.main([
        "etf-sma-daily-soak-operator-summary",
        "--history-index", str(index_file),
        "--out", str(out_file_1),
        "--format", "json",
    ])

    # Second run
    cli_module.main([
        "etf-sma-daily-soak-operator-summary",
        "--history-index", str(index_file),
        "--out", str(out_file_2),
        "--format", "json",
    ])

    assert out_file_1.read_text(encoding="utf-8") == out_file_2.read_text(encoding="utf-8")
