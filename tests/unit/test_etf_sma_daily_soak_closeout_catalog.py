"""Unit tests for V3Q Daily Lab Closeout Catalog Index."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_soak_closeout_catalog import (
    DailyLabCloseoutCatalogConfig,
    run_daily_lab_closeout_catalog,
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


def _create_fake_bundle_root(root_dir: Path, with_validation: bool = True, val_status: str = "passed") -> None:
    root_dir.mkdir(parents=True, exist_ok=True)
    
    # Write a fake validation jsonl
    if with_validation:
        val_path = root_dir / "v3o_daily_lab_closeout_bundle_validation.jsonl"
        val_record = {
            "status": val_status,
            "bundle_root": str(root_dir),
            "labels": [
                "paper_lab_only",
                "research_only",
                "not_live_authorized",
                "profit_claim=none",
                "offline_only",
            ],
            "safety": {
                "broker_reads": False,
                "broker_mutations": False,
                "paper_submit": False,
                "credentials_required": False,
                "network_required": False,
                "live_trading": False,
            }
        }
        val_path.write_text(json.dumps(val_record) + "\n", encoding="utf-8")
        
        # Also markdown validation file
        val_md = root_dir / "v3o_daily_lab_closeout_bundle_validation.md"
        val_md.write_text("# Validation Report", encoding="utf-8")

    # Write some other dummy closeout artifacts
    (root_dir / "v3j_daily_soak_acceptance_history_index.jsonl").write_text('{"record_type": "v3j"}\n', encoding="utf-8")
    (root_dir / "v3k_daily_soak_operator_summary.jsonl").write_text('{"record_type": "v3k"}\n', encoding="utf-8")
    (root_dir / "v3k_daily_soak_operator_summary.md").write_text("dummy summary", encoding="utf-8")


def test_catalog_single_bundle_root(tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak_root"
    _create_fake_bundle_root(soak_dir, with_validation=True, val_status="passed")

    output_jsonl = tmp_path / "catalog.jsonl"
    output_text = tmp_path / "catalog.md"

    config = DailyLabCloseoutCatalogConfig(
        bundle_roots=[str(soak_dir)],
        output_jsonl=str(output_jsonl),
        output_text=str(output_text),
    )

    records = run_daily_lab_closeout_catalog(config)

    assert len(records) == 1
    rec = records[0]
    assert rec["status"] == "passed"
    assert rec["validation_status"] == "passed"
    assert rec["artifact_count"] == 5  # v3j jsonl, v3k jsonl, v3k md, v3o jsonl, v3o md
    assert rec["recommended_next_action"] == "review_closeout_packet"
    
    # Required safety labels
    for lbl in ["paper_lab_only", "research_only", "not_live_authorized", "profit_claim=none", "offline_only"]:
        assert lbl in rec["labels"]

    # Check that outputs are written
    assert output_jsonl.exists()
    assert output_text.exists()

    jsonl_content = output_jsonl.read_text(encoding="utf-8")
    assert soak_dir.name in jsonl_content
    
    md_content = output_text.read_text(encoding="utf-8")
    assert "# Daily Lab Closeout Catalog Index" in md_content
    assert soak_dir.name in md_content


def test_catalog_multiple_bundle_roots_deterministic_ordering(tmp_path: Path) -> None:
    root_b = tmp_path / "root_b"
    root_a = tmp_path / "root_a"

    _create_fake_bundle_root(root_b, with_validation=True, val_status="passed")
    _create_fake_bundle_root(root_a, with_validation=True, val_status="failed")

    output_jsonl = tmp_path / "catalog.jsonl"
    output_text = tmp_path / "catalog.md"

    # Pass them in non-alphabetical order: root_b first, then root_a
    config = DailyLabCloseoutCatalogConfig(
        bundle_roots=[str(root_b), str(root_a)],
        output_jsonl=str(output_jsonl),
        output_text=str(output_text),
    )

    records = run_daily_lab_closeout_catalog(config)

    assert len(records) == 2
    # Deterministic sorting should order root_a (normalized) before root_b (normalized)
    assert records[0]["bundle_root"].endswith("root_a")
    assert records[1]["bundle_root"].endswith("root_b")

    assert records[0]["status"] == "failed"
    assert records[0]["recommended_next_action"] == "inspect_validation_failures"
    assert records[1]["status"] == "passed"
    assert records[1]["recommended_next_action"] == "review_closeout_packet"


def test_catalog_missing_validation_artifact(tmp_path: Path) -> None:
    soak_dir = tmp_path / "soak_root_no_val"
    _create_fake_bundle_root(soak_dir, with_validation=False)

    output_jsonl = tmp_path / "catalog.jsonl"
    output_text = tmp_path / "catalog.md"

    config = DailyLabCloseoutCatalogConfig(
        bundle_roots=[str(soak_dir)],
        output_jsonl=str(output_jsonl),
        output_text=str(output_text),
    )

    records = run_daily_lab_closeout_catalog(config)

    assert len(records) == 1
    rec = records[0]
    assert rec["status"] == "not_available"
    assert rec["validation_status"] == "not_available"
    assert rec["recommended_next_action"] == "run_validation"


def test_catalog_empty_roots_throws_validation_error() -> None:
    config = DailyLabCloseoutCatalogConfig(
        bundle_roots=[],
    )
    with pytest.raises(ValidationError, match="At least one bundle root must be supplied"):
        run_daily_lab_closeout_catalog(config)


def test_cli_integration(tmp_path: Path) -> None:
    root_dir = tmp_path / "cli_root"
    _create_fake_bundle_root(root_dir, with_validation=True, val_status="passed")

    output_jsonl = tmp_path / "cli_catalog.jsonl"
    output_text = tmp_path / "cli_catalog.md"

    parser = cli_module.build_parser()
    args = parser.parse_args([
        "etf-sma-daily-soak-closeout-catalog",
        "--bundle-root", str(root_dir),
        "--output-jsonl", str(output_jsonl),
        "--output-text", str(output_text),
        "--format", "json",
    ])

    assert args.bundle_root == [str(root_dir)]
    assert args.output_jsonl == str(output_jsonl)
    assert args.output_text == str(output_text)
    assert args.output_format == "json"

    # Run the handler via main or _run_etf_sma_daily_soak_closeout_catalog
    exit_code = cli_module.main([
        "etf-sma-daily-soak-closeout-catalog",
        "--bundle-root", str(root_dir),
        "--output-jsonl", str(output_jsonl),
        "--output-text", str(output_text),
        "--format", "json",
    ])
    
    assert exit_code == 0
    assert output_jsonl.exists()
    assert output_text.exists()

    # Verify JSON structure
    json_lines = output_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(json_lines) == 1
    loaded = json.loads(json_lines[0])
    assert loaded["status"] == "passed"
    assert loaded["validation_status"] == "passed"
    assert loaded["artifact_count"] == 5
