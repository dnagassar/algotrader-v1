from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily import (
    EtfSmaDailyConfig,
    run_etf_sma_daily,
)
from algotrader.execution.etf_sma_daily_status import (
    EtfSmaDailyStatusConfig,
    run_etf_sma_daily_status,
    _normalize_path,
    compute_sha256,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"
MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_status.py")

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "urllib",
)

FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "delete",
    "getenv",
    "liquidate",
    "load_config",
    "replace_order",
    "request",
    "retry",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


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


def create_valid_bundle(tmp_path: Path, as_of_date: str = "2026-06-05", blockers: bool = False) -> tuple[Path, Path]:
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    if blockers:
        reco_path = FIXTURES_DIR / "reconciliation_state_open_order.jsonl"
    else:
        reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyConfig(
        as_of_date=as_of_date,
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )
    run_etf_sma_daily(config)
    return output_root / as_of_date, output_root


def test_status_happy_path(tmp_path: Path) -> None:
    bundle_dir, output_root = create_valid_bundle(tmp_path)
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "accepted"
    assert payload["finding_count"] == 0
    assert payload["findings"] == []
    assert payload["required_files_present"] is True
    assert payload["jsonl_parse_ok"] is True
    assert payload["manifest_hashes_match"] is True
    assert payload["daily_index_matches"] is True
    assert payload["labels_present"] is True
    assert payload["safety_booleans_present"] is True
    assert payload["status_consistency_ok"] is True
    assert payload["credential_scan_ok"] is True
    assert payload["validate_artifacts_ok"] is True

    # Verify output files
    assert (bundle_dir / "bundle_status.jsonl").exists()
    assert (bundle_dir / "bundle_status.txt").exists()

    # Verify txt report content
    txt_content = (bundle_dir / "bundle_status.txt").read_text(encoding="utf-8")
    assert "STATUS (V3B) - ACCEPTED" in txt_content.upper()
    assert "finding_count: 0" in txt_content


def test_status_missing_file(tmp_path: Path) -> None:
    bundle_dir, _ = create_valid_bundle(tmp_path)
    
    # Delete cycle.jsonl
    (bundle_dir / "cycle.jsonl").unlink()
    
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "blocked"
    assert payload["required_files_present"] is False
    assert any(f["code"] == "file_missing" for f in payload["findings"])


def test_status_malformed_jsonl(tmp_path: Path) -> None:
    bundle_dir, _ = create_valid_bundle(tmp_path)
    
    # Overwrite brief.jsonl with garbage
    (bundle_dir / "brief.jsonl").write_text("invalid_json{garbage}", encoding="utf-8")
    
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "blocked"
    assert payload["jsonl_parse_ok"] is False
    assert any(f["code"] == "jsonl_parse_error" for f in payload["findings"])


def test_status_manifest_hash_mismatch(tmp_path: Path) -> None:
    bundle_dir, _ = create_valid_bundle(tmp_path)
    
    # Corrupt brief.txt (changes hash and size)
    brief_txt = bundle_dir / "brief.txt"
    brief_txt.write_text(brief_txt.read_text(encoding="utf-8") + "\ncorrupted\n", encoding="utf-8")
    
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "blocked"
    assert payload["manifest_hashes_match"] is False
    assert any(f["code"] == "manifest_hash_mismatch" for f in payload["findings"])


def test_status_daily_index_missing_and_mismatch(tmp_path: Path) -> None:
    bundle_dir, output_root = create_valid_bundle(tmp_path)
    index_file = output_root / "daily_run_index.jsonl"
    
    # 1. Missing index file
    index_file.unlink()
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    assert payload["status"] == "blocked"
    assert any(f["code"] == "file_missing" and "daily_run_index.jsonl" in f["message"] for f in payload["findings"])

    # 2. Mismatched entry status
    # Recreate bundle and index first
    bundle_dir, output_root = create_valid_bundle(tmp_path)
    # Read index entry, corrupt its status
    entries = [json.loads(line) for line in index_file.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    entries[0]["status"] = "blocked_or_invalid" # Should be "ready"
    
    lines = [json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n" for e in entries]
    index_file.write_text("".join(lines), encoding="utf-8", newline="\n")
    
    payload = run_etf_sma_daily_status(config)
    assert payload["status"] == "blocked"
    assert payload["daily_index_matches"] is False
    assert any(f["code"] == "daily_index_mismatch" for f in payload["findings"])


def test_status_missing_labels(tmp_path: Path) -> None:
    bundle_dir, output_root = create_valid_bundle(tmp_path)
    manifest_file = bundle_dir / "bundle_manifest.jsonl"
    
    manifest_rec = json.loads(manifest_file.read_text(encoding="utf-8").strip())
    # Remove safety label
    manifest_rec["labels"].remove("paper_lab_only")
    manifest_file.write_text(json.dumps(manifest_rec) + "\n", encoding="utf-8", newline="\n")
    
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "blocked"
    assert payload["labels_present"] is False
    assert any(f["code"] == "label_missing" for f in payload["findings"])


def test_status_safety_boolean_invalid(tmp_path: Path) -> None:
    bundle_dir, _ = create_valid_bundle(tmp_path)
    brief_jsonl = bundle_dir / "brief.jsonl"
    
    rec = json.loads(brief_jsonl.read_text(encoding="utf-8").strip())
    # Set safety boolean to true
    rec["live_authorized"] = True
    brief_jsonl.write_text(json.dumps(rec) + "\n", encoding="utf-8", newline="\n")
    
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "blocked"
    assert payload["safety_booleans_present"] is False
    assert any(f["code"] == "safety_boolean_invalid" for f in payload["findings"])


def test_status_safety_text_line_invalid(tmp_path: Path) -> None:
    bundle_dir, _ = create_valid_bundle(tmp_path)
    brief_txt = bundle_dir / "brief.txt"
    
    content = brief_txt.read_text(encoding="utf-8")
    content = content.replace("live_submit_allowed=false", "live_submit_allowed=true")
    brief_txt.write_text(content, encoding="utf-8")
    
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "blocked"
    assert payload["safety_booleans_present"] is False
    assert any(f["code"] == "safety_boolean_invalid" for f in payload["findings"])


def test_status_inconsistency(tmp_path: Path) -> None:
    # Create bundle with blockers
    bundle_dir, _ = create_valid_bundle(tmp_path, blockers=True)
    
    # Cycle has blockers, but let's clear brief.jsonl blockers
    brief_jsonl = bundle_dir / "brief.jsonl"
    rec = json.loads(brief_jsonl.read_text(encoding="utf-8").strip())
    rec["brief_state"] = "ready"
    rec["blockers"] = []
    brief_jsonl.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "blocked"
    assert payload["status_consistency_ok"] is False
    assert any(f["code"] == "status_inconsistency" for f in payload["findings"])


def test_status_credential_leak(tmp_path: Path) -> None:
    bundle_dir, _ = create_valid_bundle(tmp_path)
    
    # Add a mock secret into brief.txt
    brief_txt = bundle_dir / "brief.txt"
    brief_txt.write_text(brief_txt.read_text(encoding="utf-8") + "\nALPACA_API_KEY = PKFAKE123456789012345\n")
    
    config = EtfSmaDailyStatusConfig(bundle_dir=bundle_dir)
    payload = run_etf_sma_daily_status(config)
    
    assert payload["status"] == "blocked"
    assert payload["credential_scan_ok"] is False
    assert any(f["code"] == "credential_leak" for f in payload["findings"])
    
    # Confirm secret value is redacted/masked and does NOT appear in the payload or findings
    payload_str = json.dumps(payload)
    assert "PKFAKE123456789012345" not in payload_str


def test_status_custom_output_root(tmp_path: Path) -> None:
    output_root = tmp_path / "custom_root"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )
    run_etf_sma_daily(config)
    
    bundle_dir = output_root / "2026-06-05"
    payload = run_etf_sma_daily_status(EtfSmaDailyStatusConfig(bundle_dir=bundle_dir))
    
    assert payload["status"] == "accepted"
    assert payload["daily_index_matches"] is True
    assert (bundle_dir / "bundle_status.jsonl").exists()


def test_status_cli_command(tmp_path: Path) -> None:
    bundle_dir, _ = create_valid_bundle(tmp_path)
    
    code = cli_module.main([
        "etf-sma-daily-status",
        "--bundle-dir", str(bundle_dir),
        "--format", "json",
    ])
    assert code == 0


def test_imports_and_calls_invariant() -> None:
    """Verify that the module has no forbidden network/credentials imports or calls."""
    with open(MODULE_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(MODULE_PATH))

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    # Check forbidden imports
    for prefix in FORBIDDEN_IMPORT_PREFIXES:
        for imp in imports:
            assert not (imp == prefix or imp.startswith(f"{prefix}.")), f"Forbidden import: {imp}"

    # Check call names
    call_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                call_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    call_names.add(f"{func.value.id}.{func.attr}")
                else:
                    call_names.add(func.attr)

    violations = call_names.intersection(FORBIDDEN_CALL_NAMES)
    assert not violations, f"Forbidden calls found: {violations}"
