"""Unit tests for V3O Daily Lab Closeout Bundle Validator."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.daily_lab_closeout_run_receipt import (
    DailyLabCloseoutRunReceiptConfig,
    run_daily_lab_closeout_receipt,
)
from algotrader.execution.etf_sma_daily_soak_closeout_bundle_validator import (
    DailyLabCloseoutBundleValidationConfig,
    run_daily_lab_closeout_bundle_validation,
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_path(path: Path) -> str:
    if path.is_absolute():
        try:
            path = path.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(path.as_posix())


def _create_passing_artifacts(soak_dir: Path) -> dict[str, Path]:
    soak_dir.mkdir(parents=True, exist_ok=True)

    labels = [
        "paper_lab_only",
        "research_only",
        "not_live_authorized",
        "profit_claim=none",
        "offline_only",
    ]
    safety = {
        "broker_reads": False,
        "broker_mutations": False,
        "paper_submit": False,
        "credentials_required": False,
        "network_required": False,
        "live_trading": False,
    }

    # JSONL files
    v3j_path = soak_dir / "v3j_daily_soak_acceptance_history_index.jsonl"
    v3j_path.write_text(
        json.dumps({"record_type": "v3j", "safety_authorizations": {
            "live_authorized": False,
            "paper_submit_authorized": False,
            "paper_broker_reads_authorized": False,
            "broker_mutation_authorized": False,
            "network_authorized": False,
            "credentials_loaded": False,
        }})
        + "\n",
        encoding="utf-8",
    )

    v3k_jsonl_path = soak_dir / "v3k_daily_soak_operator_summary.jsonl"
    v3k_jsonl_path.write_text(
        json.dumps({"record_type": "v3k", "safety_authorizations": {
            "live_authorized": False,
            "paper_submit_authorized": False,
            "paper_broker_reads_authorized": False,
            "broker_mutation_authorized": False,
            "network_authorized": False,
            "credentials_loaded": False,
        }})
        + "\n",
        encoding="utf-8",
    )

    v3l_jsonl_path = soak_dir / "v3l_daily_soak_closeout_packet.jsonl"
    v3l_jsonl_path.write_text(
        json.dumps({"record_type": "v3l", "labels": labels, "safety_booleans": safety}) + "\n",
        encoding="utf-8",
    )

    # Markdown files
    v3k_md_path = soak_dir / "v3k_daily_soak_operator_summary.md"
    v3k_md_path.write_text("v3k md non empty summary content", encoding="utf-8")

    v3l_md_path = soak_dir / "v3l_daily_soak_closeout_packet.md"
    v3l_md_path.write_text("v3l md non empty summary content", encoding="utf-8")

    # Generate V3N receipt JSONL and MD using run_daily_lab_closeout_receipt
    v3n_jsonl_path = soak_dir / "v3n_daily_lab_closeout_run_receipt.jsonl"
    v3n_md_path = soak_dir / "v3n_daily_lab_closeout_run_receipt.md"

    config = DailyLabCloseoutRunReceiptConfig(
        start_date="2025-06-01",
        end_date="2025-06-10",
        bars_csv="tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
        reconciliation_state_path="tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
        daily_soak_dir=str(soak_dir),
        status="completed",
        steps_json="[]",
        receipt_out=str(v3n_jsonl_path),
        receipt_text_out=str(v3n_md_path),
    )
    run_daily_lab_closeout_receipt(config)

    return {
        "v3j_history_index": v3j_path,
        "v3k_operator_summary_jsonl": v3k_jsonl_path,
        "v3k_operator_summary_markdown": v3k_md_path,
        "v3l_closeout_packet_jsonl": v3l_jsonl_path,
        "v3l_closeout_packet_markdown": v3l_md_path,
        "v3n_receipt_jsonl": v3n_jsonl_path,
        "v3n_receipt_markdown": v3n_md_path,
    }


@patch("subprocess.run")
def test_validation_passes_when_all_artifacts_are_healthy(
    mock_subproc: MagicMock, tmp_path: Path
) -> None:
    soak_dir = tmp_path / "soak"
    validation_out = soak_dir / "validation.jsonl"
    validation_text_out = soak_dir / "validation.md"

    _create_passing_artifacts(soak_dir)

    # Mock git check to return zero tracked files
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = ""
    mock_subproc.return_value = mock_res

    config = DailyLabCloseoutBundleValidationConfig(
        daily_soak_dir=str(soak_dir),
        validation_out=str(validation_out),
        validation_text_out=str(validation_text_out),
    )

    record = run_daily_lab_closeout_bundle_validation(config)

    assert record["status"] == "passed"
    assert record["recommended_next_offline_action"] == "review_closeout_packet"
    assert len(record["failures"]) == 0
    assert validation_out.exists()
    assert validation_text_out.exists()

    # Verify written validation record
    lines = validation_out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["status"] == "passed"
    assert loaded["milestone"] == "V3O"

    # Verify markdown summary content
    md = validation_text_out.read_text(encoding="utf-8")
    assert "# V3O Daily Lab Closeout Bundle Validation Report" in md
    assert "**validation_status**: `passed`" in md
    assert "No failures detected." in md


@patch("subprocess.run")
def test_validation_fails_on_missing_artifact(mock_subproc: MagicMock, tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    validation_out = soak_dir / "validation.jsonl"
    validation_text_out = soak_dir / "validation.md"

    paths = _create_passing_artifacts(soak_dir)
    # Remove one artifact
    paths["v3l_closeout_packet_markdown"].unlink()

    # Mock git check
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = ""
    mock_subproc.return_value = mock_res

    config = DailyLabCloseoutBundleValidationConfig(
        daily_soak_dir=str(soak_dir),
        validation_out=str(validation_out),
        validation_text_out=str(validation_text_out),
    )

    record = run_daily_lab_closeout_bundle_validation(config)

    assert record["status"] == "failed"
    assert record["recommended_next_offline_action"] == "inspect_validation_failures"
    assert any("v3l_closeout_packet_markdown" in f for f in record["failures"])

    # Output files must still be written
    assert validation_out.exists()
    assert validation_text_out.exists()


@patch("subprocess.run")
def test_validation_fails_on_invalid_jsonl(mock_subproc: MagicMock, tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    paths = _create_passing_artifacts(soak_dir)
    # Write invalid json content
    paths["v3j_history_index"].write_text("invalid json content\n")

    # Mock git check
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = ""
    mock_subproc.return_value = mock_res

    config = DailyLabCloseoutBundleValidationConfig(
        daily_soak_dir=str(soak_dir),
        validation_out=str(soak_dir / "val.jsonl"),
        validation_text_out=str(soak_dir / "val.md"),
    )

    record = run_daily_lab_closeout_bundle_validation(config)

    assert record["status"] == "failed"
    assert any("is malformed" in f for f in record["failures"])


@patch("subprocess.run")
def test_validation_fails_on_empty_markdown(mock_subproc: MagicMock, tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    paths = _create_passing_artifacts(soak_dir)
    # Write empty string
    paths["v3k_operator_summary_markdown"].write_text("  \n  ")

    # Mock git check
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = ""
    mock_subproc.return_value = mock_res

    config = DailyLabCloseoutBundleValidationConfig(
        daily_soak_dir=str(soak_dir),
        validation_out=str(soak_dir / "val.jsonl"),
        validation_text_out=str(soak_dir / "val.md"),
    )

    record = run_daily_lab_closeout_bundle_validation(config)

    assert record["status"] == "failed"
    assert any("is empty" in f for f in record["failures"])


@patch("subprocess.run")
def test_validation_fails_on_v3n_receipt_path_mismatch(
    mock_subproc: MagicMock, tmp_path: Path
) -> None:
    soak_dir = tmp_path / "soak"
    paths = _create_passing_artifacts(soak_dir)

    # Read receipt, edit a path reference, and write back
    lines = paths["v3n_receipt_jsonl"].read_text(encoding="utf-8").splitlines()
    receipt = json.loads(lines[0])
    for art in receipt["artifacts"]:
        if art["kind"] == "v3j_history_index":
            art["path"] = "runs/mismatched_history_index.jsonl"

    paths["v3n_receipt_jsonl"].write_text(json.dumps(receipt) + "\n", encoding="utf-8")

    # Mock git check
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = ""
    mock_subproc.return_value = mock_res

    config = DailyLabCloseoutBundleValidationConfig(
        daily_soak_dir=str(soak_dir),
        validation_out=str(soak_dir / "val.jsonl"),
        validation_text_out=str(soak_dir / "val.md"),
    )

    record = run_daily_lab_closeout_bundle_validation(config)

    assert record["status"] == "failed"
    assert any("path mismatch" in f for f in record["failures"])


@patch("subprocess.run")
def test_validation_fails_on_missing_required_labels(
    mock_subproc: MagicMock, tmp_path: Path
) -> None:
    soak_dir = tmp_path / "soak"
    paths = _create_passing_artifacts(soak_dir)

    # Edit closeout packet to have missing labels
    packet = json.loads(paths["v3l_closeout_packet_jsonl"].read_text(encoding="utf-8"))
    packet["labels"] = ["offline_only"]  # missing others
    paths["v3l_closeout_packet_jsonl"].write_text(json.dumps(packet) + "\n", encoding="utf-8")

    # Mock git check
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = ""
    mock_subproc.return_value = mock_res

    config = DailyLabCloseoutBundleValidationConfig(
        daily_soak_dir=str(soak_dir),
        validation_out=str(soak_dir / "val.jsonl"),
        validation_text_out=str(soak_dir / "val.md"),
    )

    record = run_daily_lab_closeout_bundle_validation(config)

    assert record["status"] == "failed"
    assert any("missing required label" in f for f in record["failures"])


@patch("subprocess.run")
def test_validation_fails_on_unsafe_safety_boolean(
    mock_subproc: MagicMock, tmp_path: Path
) -> None:
    soak_dir = tmp_path / "soak"
    paths = _create_passing_artifacts(soak_dir)

    # Edit closeout packet to have unsafe boolean
    packet = json.loads(paths["v3l_closeout_packet_jsonl"].read_text(encoding="utf-8"))
    packet["safety_booleans"]["live_trading"] = True
    paths["v3l_closeout_packet_jsonl"].write_text(json.dumps(packet) + "\n", encoding="utf-8")

    # Mock git check
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = ""
    mock_subproc.return_value = mock_res

    config = DailyLabCloseoutBundleValidationConfig(
        daily_soak_dir=str(soak_dir),
        validation_out=str(soak_dir / "val.jsonl"),
        validation_text_out=str(soak_dir / "val.md"),
    )

    record = run_daily_lab_closeout_bundle_validation(config)

    assert record["status"] == "failed"
    assert any("is unsafe (True)" in f for f in record["failures"])


@patch("subprocess.run")
def test_validation_fails_on_tracked_runs_artifact(
    mock_subproc: MagicMock, tmp_path: Path
) -> None:
    soak_dir = tmp_path / "soak"
    _create_passing_artifacts(soak_dir)

    # Mock git check to return tracked runs files
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "runs/daily_soak/v3j_daily_soak_acceptance_history_index.jsonl\n"
    mock_subproc.return_value = mock_res

    config = DailyLabCloseoutBundleValidationConfig(
        daily_soak_dir=str(soak_dir),
        validation_out=str(soak_dir / "val.jsonl"),
        validation_text_out=str(soak_dir / "val.md"),
    )

    record = run_daily_lab_closeout_bundle_validation(config)

    assert record["status"] == "failed"
    assert any("Tracked runtime file found" in f for f in record["failures"])


@patch("subprocess.run")
def test_cli_integration_exits_correctly(mock_subproc: MagicMock, tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak"
    _create_passing_artifacts(soak_dir)

    # Mock git check
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = ""
    mock_subproc.return_value = mock_res

    validation_out = soak_dir / "cli_val.jsonl"
    validation_text_out = soak_dir / "cli_val.md"

    exit_code = cli_module.main([
        "etf-sma-daily-soak-closeout-bundle-validate",
        "--daily-soak-dir",
        str(soak_dir),
        "--validation-out",
        str(validation_out),
        "--validation-text-out",
        str(validation_text_out),
        "--format",
        "json",
    ])

    assert exit_code == 0
    assert validation_out.exists()
    assert validation_text_out.exists()

    # Now make it fail
    paths = _create_passing_artifacts(soak_dir)
    paths["v3l_closeout_packet_markdown"].unlink()

    exit_code_fail = cli_module.main([
        "etf-sma-daily-soak-closeout-bundle-validate",
        "--daily-soak-dir",
        str(soak_dir),
        "--validation-out",
        str(validation_out),
        "--validation-text-out",
        str(validation_text_out),
        "--format",
        "text",
    ])

    assert exit_code_fail == 1
