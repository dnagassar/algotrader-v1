"""Unit tests for Daily Lab Closeout Run Receipt (V3N)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

import algotrader.cli as cli_module
from algotrader.execution.daily_lab_closeout_run_receipt import (
    DailyLabCloseoutRunReceiptConfig,
    run_daily_lab_closeout_receipt,
)


@pytest.fixture(autouse=True)
def enforce_preflight_offline_only() -> None:
    """Ensure that no credentials or paper profiles are present in the environment."""
    assert os.environ.get("APP_PROFILE") != "paper"
    for var in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        assert var not in os.environ


def _dummy_steps() -> list[dict[str, Any]]:
    return [
        {
            "name": "V3I daily lab acceptance launcher",
            "command": "powershell scripts/run_daily_lab_acceptance.ps1",
            "status": "completed",
            "exit_code": 0,
        },
        {
            "name": "Building V3J daily soak acceptance history index",
            "command": "python -m algotrader.cli etf-sma-daily-soak-acceptance-history-index",
            "status": "completed",
            "exit_code": 0,
        },
    ]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_receipt_writer_creates_jsonl_and_markdown_for_completed_run(tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    soak_dir.mkdir()
    receipt_out = soak_dir / "receipt.jsonl"
    receipt_text_out = soak_dir / "receipt.md"

    steps_list = _dummy_steps()
    steps_json = json.dumps(steps_list)

    config = DailyLabCloseoutRunReceiptConfig(
        start_date="2025-06-01",
        end_date="2025-06-10",
        bars_csv="tests/fixtures/spy_bars.csv",
        reconciliation_state_path="tests/fixtures/recon.jsonl",
        daily_soak_dir=str(soak_dir),
        status="completed",
        steps_json=steps_json,
        receipt_out=str(receipt_out),
        receipt_text_out=str(receipt_text_out),
    )

    receipt = run_daily_lab_closeout_receipt(config)

    assert receipt["status"] == "completed"
    assert receipt["recommended_next_offline_action"] == "review_closeout_packet"
    assert receipt["schema_version"] == "1"
    assert receipt["milestone"] == "V3N"

    # Verify files created on disk
    assert receipt_out.exists()
    assert receipt_text_out.exists()

    # Verify JSONL content
    lines = receipt_out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded_receipt = json.loads(lines[0])
    assert loaded_receipt["status"] == "completed"
    assert loaded_receipt["milestone"] == "V3N"
    assert len(loaded_receipt["steps"]) == 2

    # Verify Markdown content
    markdown = receipt_text_out.read_text(encoding="utf-8")
    assert "# V3N Daily Lab Closeout Run Receipt" in markdown
    assert "## Status" in markdown
    assert "**final_status**: `completed`" in markdown
    assert "## Step Execution Sequence" in markdown
    assert "does not authorize broker reads, paper submit, broker mutation, or live trading" in markdown


def test_receipt_writer_records_missing_artifacts_with_exists_false(tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    soak_dir.mkdir()
    receipt_out = soak_dir / "receipt.jsonl"
    receipt_text_out = soak_dir / "receipt.md"

    config = DailyLabCloseoutRunReceiptConfig(
        start_date="2025-06-01",
        end_date="2025-06-10",
        bars_csv="tests/fixtures/spy_bars.csv",
        reconciliation_state_path="tests/fixtures/recon.jsonl",
        daily_soak_dir=str(soak_dir),
        status="completed",
        steps_json="[]",
        receipt_out=str(receipt_out),
        receipt_text_out=str(receipt_text_out),
    )

    receipt = run_daily_lab_closeout_receipt(config)

    # Check history index artifact which doesn't exist
    history_art = next(a for a in receipt["artifacts"] if a["kind"] == "v3j_history_index")
    assert history_art["exists"] is False
    assert history_art["size_bytes"] is None
    assert history_art["sha256"] is None


def test_receipt_writer_records_present_artifacts_with_size_bytes_and_sha256(tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    soak_dir.mkdir()
    receipt_out = soak_dir / "receipt.jsonl"
    receipt_text_out = soak_dir / "receipt.md"

    # Create dummy V3J history index file
    dummy_history_path = soak_dir / "v3j_daily_soak_acceptance_history_index.jsonl"
    dummy_content = b"dummy history content\n"
    dummy_history_path.write_bytes(dummy_content)

    config = DailyLabCloseoutRunReceiptConfig(
        start_date="2025-06-01",
        end_date="2025-06-10",
        bars_csv="tests/fixtures/spy_bars.csv",
        reconciliation_state_path="tests/fixtures/recon.jsonl",
        daily_soak_dir=str(soak_dir),
        status="completed",
        steps_json="[]",
        receipt_out=str(receipt_out),
        receipt_text_out=str(receipt_text_out),
    )

    receipt = run_daily_lab_closeout_receipt(config)

    history_art = next(a for a in receipt["artifacts"] if a["kind"] == "v3j_history_index")
    assert history_art["exists"] is True
    assert history_art["size_bytes"] == len(dummy_content)
    assert history_art["sha256"] == _sha256(dummy_content)

    # V3N receipt JSONL should also exist and have correct size and sha256 in the final receipt record
    receipt_art = next(a for a in receipt["artifacts"] if a["kind"] == "v3n_receipt_jsonl")
    assert receipt_art["exists"] is True
    assert receipt_art["size_bytes"] is not None
    assert receipt_art["size_bytes"] > 0
    assert receipt_art["sha256"] is not None


def test_receipt_references_selected_repo_relative_output_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    soak_dir = Path("runs/daily_soak/v3p_unit")
    soak_dir.mkdir(parents=True)
    receipt_out = soak_dir / "v3n_daily_lab_closeout_run_receipt.jsonl"
    receipt_text_out = soak_dir / "v3n_daily_lab_closeout_run_receipt.md"

    for artifact_name in (
        "v3j_daily_soak_acceptance_history_index.jsonl",
        "v3k_daily_soak_operator_summary.jsonl",
        "v3k_daily_soak_operator_summary.md",
        "v3l_daily_soak_closeout_packet.jsonl",
        "v3l_daily_soak_closeout_packet.md",
    ):
        (soak_dir / artifact_name).write_text("fixture\n", encoding="utf-8")

    receipt = run_daily_lab_closeout_receipt(
        DailyLabCloseoutRunReceiptConfig(
            start_date="2025-06-01",
            end_date="2025-06-10",
            bars_csv="tests/fixtures/spy_bars.csv",
            reconciliation_state_path="tests/fixtures/recon.jsonl",
            daily_soak_dir=str(soak_dir),
            status="completed",
            steps_json="[]",
            receipt_out=str(receipt_out),
            receipt_text_out=str(receipt_text_out),
        )
    )

    assert receipt["daily_soak_dir"] == "runs/daily_soak/v3p_unit"
    artifact_paths = {artifact["path"] for artifact in receipt["artifacts"]}
    assert artifact_paths == {
        "runs/daily_soak/v3p_unit/v3j_daily_soak_acceptance_history_index.jsonl",
        "runs/daily_soak/v3p_unit/v3k_daily_soak_operator_summary.jsonl",
        "runs/daily_soak/v3p_unit/v3k_daily_soak_operator_summary.md",
        "runs/daily_soak/v3p_unit/v3l_daily_soak_closeout_packet.jsonl",
        "runs/daily_soak/v3p_unit/v3l_daily_soak_closeout_packet.md",
        "runs/daily_soak/v3p_unit/v3n_daily_lab_closeout_run_receipt.jsonl",
        "runs/daily_soak/v3p_unit/v3n_daily_lab_closeout_run_receipt.md",
    }


def test_receipt_includes_all_required_safety_booleans_set_to_false(tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    soak_dir.mkdir()
    receipt_out = soak_dir / "receipt.jsonl"
    receipt_text_out = soak_dir / "receipt.md"

    config = DailyLabCloseoutRunReceiptConfig(
        start_date="2025-06-01",
        end_date="2025-06-10",
        bars_csv="tests/fixtures/spy_bars.csv",
        reconciliation_state_path="tests/fixtures/recon.jsonl",
        daily_soak_dir=str(soak_dir),
        status="completed",
        steps_json="[]",
        receipt_out=str(receipt_out),
        receipt_text_out=str(receipt_text_out),
    )

    receipt = run_daily_lab_closeout_receipt(config)

    assert receipt["safety"] == {
        "broker_reads": False,
        "broker_mutations": False,
        "paper_submit": False,
        "credentials_required": False,
        "network_required": False,
        "live_trading": False,
    }


def test_receipt_labels_include_required_values(tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    soak_dir.mkdir()
    receipt_out = soak_dir / "receipt.jsonl"
    receipt_text_out = soak_dir / "receipt.md"

    config = DailyLabCloseoutRunReceiptConfig(
        start_date="2025-06-01",
        end_date="2025-06-10",
        bars_csv="tests/fixtures/spy_bars.csv",
        reconciliation_state_path="tests/fixtures/recon.jsonl",
        daily_soak_dir=str(soak_dir),
        status="completed",
        steps_json="[]",
        receipt_out=str(receipt_out),
        receipt_text_out=str(receipt_text_out),
    )

    receipt = run_daily_lab_closeout_receipt(config)

    for label in (
        "paper_lab_only",
        "research_only",
        "not_live_authorized",
        "profit_claim=none",
        "offline_only",
    ):
        assert label in receipt["labels"]


@pytest.mark.parametrize(
    "status,expected_action",
    [
        ("failed_acceptance_launcher", "inspect_failed_step"),
        ("failed_history_index", "inspect_failed_step"),
        ("failed_operator_summary", "inspect_failed_step"),
        ("failed_closeout_packet", "inspect_failed_step"),
        ("failed_receipt_generation", "inspect_failed_step"),
        ("completed", "review_closeout_packet"),
        ("other_unknown_status", "rerun_offline_daily_lab_closeout"),
    ],
)
def test_failed_status_mappings(tmp_path: Path, status: str, expected_action: str) -> None:
    soak_dir = tmp_path / "soak"
    soak_dir.mkdir()
    receipt_out = soak_dir / "receipt.jsonl"
    receipt_text_out = soak_dir / "receipt.md"

    config = DailyLabCloseoutRunReceiptConfig(
        start_date="2025-06-01",
        end_date="2025-06-10",
        bars_csv="tests/fixtures/spy_bars.csv",
        reconciliation_state_path="tests/fixtures/recon.jsonl",
        daily_soak_dir=str(soak_dir),
        status=status,
        steps_json="[]",
        receipt_out=str(receipt_out),
        receipt_text_out=str(receipt_text_out),
    )

    receipt = run_daily_lab_closeout_receipt(config)
    assert receipt["recommended_next_offline_action"] == expected_action


def test_receipt_cli_integration(tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    soak_dir.mkdir()
    receipt_out = soak_dir / "cli_receipt.jsonl"
    receipt_text_out = soak_dir / "cli_receipt.md"

    exit_code = cli_module.main(
        [
            "etf-sma-daily-soak-closeout-receipt",
            "--start-date",
            "2025-06-01",
            "--end-date",
            "2025-06-10",
            "--bars-csv",
            "tests/fixtures/spy_bars.csv",
            "--reconciliation-state-path",
            "tests/fixtures/recon.jsonl",
            "--daily-soak-dir",
            str(soak_dir),
            "--status",
            "completed",
            "--steps-json",
            "[]",
            "--receipt-out",
            str(receipt_out),
            "--receipt-text-out",
            str(receipt_text_out),
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    assert receipt_out.exists()
    assert receipt_text_out.exists()
