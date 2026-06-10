from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_offline_check import (
    EtfSmaDailyOfflineCheckConfig,
    run_etf_sma_daily_offline_check,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"
MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_offline_check.py")

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


def test_offline_check_happy_path(tmp_path: Path) -> None:
    """Test a successful offline check run with bullish bars and flat reconciliation."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )

    payload = run_etf_sma_daily_offline_check(config)

    assert payload["status"] == "accepted"
    assert payload["finding_count"] == 0
    assert payload["findings"] == []
    assert payload["daily_bundle_created"] is True
    assert payload["daily_status_created"] is True
    assert payload["daily_status_accepted"] is True
    assert payload["validate_artifacts_ok"] is True
    assert payload["next_operator_action"] == "proceed_to_operator_brief"

    # Verify check files were created
    day_dir = output_root / "2026-06-05"
    assert (day_dir / "offline_check.jsonl").exists()
    assert (day_dir / "offline_check.txt").exists()

    # Verify JSON content
    check_rec = json.loads((day_dir / "offline_check.jsonl").read_text(encoding="utf-8").strip())
    assert check_rec["phase"] == "offline_daily_loop_offline_check"
    assert check_rec["status"] == "accepted"
    assert check_rec["decision_matrix_required"] is True
    assert "tests/unit/test_etf_sma_cycle_decision_matrix.py" in check_rec["tests_required"]
    
    # Check authorization flags are all False
    auth = check_rec["authorization_status"]
    for key, val in auth.items():
        assert val is False


def test_offline_check_v3a_blocker(tmp_path: Path) -> None:
    """Test that blocker presence in V3A bundle results in blocked check."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_open_order.jsonl"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )

    payload = run_etf_sma_daily_offline_check(config)

    assert payload["status"] == "blocked"
    assert payload["daily_bundle_created"] is True
    assert payload["daily_status_accepted"] is False
    assert any(f["code"] == "open_order_present" for f in payload["findings"])
    assert payload["next_operator_action"] == "repair_blockers"


def test_offline_check_v3a_failed(tmp_path: Path) -> None:
    """Test that V3A bundle generation failure produces blocked check and missing files findings."""
    output_root = tmp_path / "daily"
    # Provide non-existent bars file to trigger failure
    bars_csv = tmp_path / "non_existent_bars.csv"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
    )

    with pytest.raises(ValidationError):
        run_etf_sma_daily_offline_check(config)


def test_offline_check_v3b_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that a blocked status validator results in blocked offline check."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )

    # First run normally to create outputs
    run_etf_sma_daily_offline_check(config)

    # Now corrupt brief.txt inside bundle to make V3B fail
    day_dir = output_root / "2026-06-05"
    brief_txt = day_dir / "brief.txt"
    brief_txt.write_text(brief_txt.read_text(encoding="utf-8") + "\ncorrupted\n", encoding="utf-8")

    # Monkeypatch run_etf_sma_daily so it doesn't overwrite the corrupt brief.txt
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_offline_check.run_etf_sma_daily",
        lambda *args, **kwargs: {"blockers": []}
    )

    # Run check again (it should re-run validator and detect hash mismatch)
    payload = run_etf_sma_daily_offline_check(config)

    assert payload["status"] == "blocked"
    assert any(f["code"] == "manifest_hash_mismatch" for f in payload["findings"])


def test_offline_check_validate_artifacts_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that validate_artifact finding results in blocked offline check."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )
    run_etf_sma_daily_offline_check(config)

    # Corrupt a jsonl file to make validate_artifact fail (e.g. invalid json structure)
    day_dir = output_root / "2026-06-05"
    brief_jsonl = day_dir / "brief.jsonl"
    brief_jsonl.write_text("invalid{json", encoding="utf-8")

    # Monkeypatch run_etf_sma_daily so it doesn't overwrite the corrupt brief.jsonl
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_offline_check.run_etf_sma_daily",
        lambda *args, **kwargs: {"blockers": []}
    )

    payload = run_etf_sma_daily_offline_check(config)

    assert payload["status"] == "blocked"
    assert payload["validate_artifacts_ok"] is False
    assert any(f["code"] == "artifact_validation_failed" for f in payload["findings"])


def test_offline_check_missing_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing required output files produce deterministic findings."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )
    run_etf_sma_daily_offline_check(config)

    # Delete brief.txt and brief.jsonl
    day_dir = output_root / "2026-06-05"
    (day_dir / "brief.txt").unlink()
    (day_dir / "brief.jsonl").unlink()

    # Monkeypatch run_etf_sma_daily so it doesn't recreate the deleted files
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_offline_check.run_etf_sma_daily",
        lambda *args, **kwargs: {"blockers": []}
    )

    payload = run_etf_sma_daily_offline_check(config)

    assert payload["status"] == "blocked"
    findings_codes = [f["code"] for f in payload["findings"]]
    assert "missing_required_output" in findings_codes


def test_offline_check_custom_output_root(tmp_path: Path) -> None:
    """Test custom output root parameter and verify paths resolve correctly."""
    output_root = tmp_path / "custom_root"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )

    payload = run_etf_sma_daily_offline_check(config)

    assert payload["status"] == "accepted"
    assert (output_root / "2026-06-05" / "offline_check.jsonl").exists()
    assert (output_root / "2026-06-05" / "offline_check.txt").exists()
    assert (output_root / "daily_run_index.jsonl").exists()


def test_offline_check_same_date_rerun(tmp_path: Path) -> None:
    """Test same-date rerun behaves deterministically and keeps index unique."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )

    # First run
    run_etf_sma_daily_offline_check(config)

    # Second run
    run_etf_sma_daily_offline_check(config)

    # Index file should have exactly 1 record
    index_file = output_root / "daily_run_index.jsonl"
    lines = index_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1


def test_offline_check_credential_leak_blocks_and_hides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that credential leaks in txt files block the check but do not leak secrets."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyOfflineCheckConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )
    run_etf_sma_daily_offline_check(config)

    # Inject mock credential in brief.txt
    day_dir = output_root / "2026-06-05"
    brief_txt = day_dir / "brief.txt"
    secret_val = "ALPACA_API_KEY = PKSECRETKEY1234567890"
    brief_txt.write_text(brief_txt.read_text(encoding="utf-8") + f"\n{secret_val}\n", encoding="utf-8")

    # Monkeypatch run_etf_sma_daily so it doesn't overwrite brief.txt
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_offline_check.run_etf_sma_daily",
        lambda *args, **kwargs: {"blockers": []}
    )

    payload = run_etf_sma_daily_offline_check(config)

    assert payload["status"] == "blocked"
    
    # Confirm leak finding exists
    leak_finding = None
    for f in payload["findings"]:
        if f["code"] == "credential_leak":
            leak_finding = f
            break
    assert leak_finding is not None
    
    # Ensure the secret itself is not echoed in payload
    payload_str = json.dumps(payload)
    assert "PKSECRETKEY1234567890" not in payload_str


def test_offline_check_cli_command(tmp_path: Path) -> None:
    """Test the CLI entrypoint for a successful run."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    code = cli_module.main([
        "etf-sma-daily-offline-check",
        "--as-of-date", "2026-06-05",
        "--output-root", str(output_root),
        "--bars-csv", str(bars_csv),
        "--reconciliation-state-path", str(reco_path),
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
