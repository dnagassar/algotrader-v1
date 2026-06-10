from __future__ import annotations

import ast
import json
import os
import re
import shutil
from pathlib import Path
import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily import (
    EtfSmaDailyConfig,
    run_etf_sma_daily,
    compute_sha256,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"
MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily.py")

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


def test_etf_sma_daily_success(tmp_path: Path) -> None:
    """Test a successful offline daily run with bullish bars and flat reconciliation state."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )

    payload = run_etf_sma_daily(config)

    assert payload["milestone"] == "V3A"
    assert payload["bundle_state"] == "ready"
    assert payload["as_of_date"] == "2026-06-05"
    assert not payload["blockers"]

    # Verify that files were created
    day_dir = output_root / "2026-06-05"
    assert day_dir.exists()
    assert (day_dir / "cycle.jsonl").exists()
    assert (day_dir / "brief.jsonl").exists()
    assert (day_dir / "brief.txt").exists()
    assert (day_dir / "gate.jsonl").exists()
    assert (day_dir / "dashboard.txt").exists()
    assert (day_dir / "bundle_manifest.jsonl").exists()
    assert (output_root / "daily_run_index.jsonl").exists()

    # Validate bundle manifest hashes
    manifest_content = (day_dir / "bundle_manifest.jsonl").read_text(encoding="utf-8").strip()
    manifest_rec = json.loads(manifest_content)
    assert manifest_rec["bundle_state"] == "ready"
    
    for f_info in manifest_rec["files"]:
        fpath = Path(f_info["path"])
        assert fpath.exists()
        assert compute_sha256(fpath) == f_info["sha256"]
        assert fpath.stat().st_size == f_info["byte_size"]
        assert f_info["status"] == "ready"

    # Validate daily run index contents
    index_content = (output_root / "daily_run_index.jsonl").read_text(encoding="utf-8").strip()
    index_recs = [json.loads(line) for line in index_content.splitlines()]
    assert len(index_recs) == 1
    assert index_recs[0]["as_of_date"] == "2026-06-05"
    assert index_recs[0]["status"] == "ready"


def test_etf_sma_daily_determinism(tmp_path: Path) -> None:
    """Verify that repeated runs are deterministically identical, ignoring absolute temp paths."""
    output_root1 = tmp_path / "daily1"
    output_root2 = tmp_path / "daily2"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config1 = EtfSmaDailyConfig(
        as_of_date="2026-06-05",
        output_root=output_root1,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )
    run_etf_sma_daily(config1)

    config2 = EtfSmaDailyConfig(
        as_of_date="2026-06-05",
        output_root=output_root2,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )
    run_etf_sma_daily(config2)

    day_dir1 = output_root1 / "2026-06-05"
    day_dir2 = output_root2 / "2026-06-05"

    # 1. Compare cycle.jsonl (should be exactly identical)
    assert (day_dir1 / "cycle.jsonl").read_bytes() == (day_dir2 / "cycle.jsonl").read_bytes()

    # 2. Compare brief.jsonl and brief.txt (replace daily1/daily2 in paths)
    assert (day_dir1 / "brief.txt").read_bytes().replace(b"daily1", b"") == (day_dir2 / "brief.txt").read_bytes().replace(b"daily2", b"")
    
    brief1 = json.loads((day_dir1 / "brief.jsonl").read_text(encoding="utf-8"))
    brief2 = json.loads((day_dir2 / "brief.jsonl").read_text(encoding="utf-8"))
    assert brief1 == brief2  # No paths in brief.jsonl

    # 3. Compare gate.jsonl (exactly identical)
    assert (day_dir1 / "gate.jsonl").read_bytes() == (day_dir2 / "gate.jsonl").read_bytes()

    # 4. Compare dashboard.txt (exactly identical)
    assert (day_dir1 / "dashboard.txt").read_bytes() == (day_dir2 / "dashboard.txt").read_bytes()

    # 5. Compare bundle_manifest.jsonl
    man1 = json.loads((day_dir1 / "bundle_manifest.jsonl").read_text(encoding="utf-8"))
    man2 = json.loads((day_dir2 / "bundle_manifest.jsonl").read_text(encoding="utf-8"))
    assert man1["bundle_state"] == man2["bundle_state"]
    assert man1["as_of_date"] == man2["as_of_date"]
    assert man1["labels"] == man2["labels"]
    
    # Files array in manifest
    assert len(man1["files"]) == len(man2["files"])
    for f1, f2 in zip(man1["files"], man2["files"]):
        assert f1["sha256"] == f2["sha256"]
        assert f1["byte_size"] == f2["byte_size"]
        assert f1["status"] == f2["status"]
        assert f1["path"].replace("daily1", "") == f2["path"].replace("daily2", "")

    # 6. Compare daily_run_index.jsonl
    idx1 = json.loads((output_root1 / "daily_run_index.jsonl").read_text(encoding="utf-8").strip())
    idx2 = json.loads((output_root2 / "daily_run_index.jsonl").read_text(encoding="utf-8").strip())
    assert idx1["as_of_date"] == idx2["as_of_date"]
    assert idx1["status"] == idx2["status"]
    assert idx1["bundle_manifest_path"].replace("daily1", "") == idx2["bundle_manifest_path"].replace("daily2", "")



def test_etf_sma_daily_gate_failure_fail_closed(tmp_path: Path) -> None:
    """Test that a run with a blocker (e.g. open order) fail-closed but still writes diagnostic files."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_open_order.jsonl"

    config = EtfSmaDailyConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )

    payload = run_etf_sma_daily(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "open_order_present" in payload["blockers"]

    day_dir = output_root / "2026-06-05"
    assert day_dir.exists()
    assert (day_dir / "cycle.jsonl").exists()
    assert (day_dir / "brief.jsonl").exists()
    assert (day_dir / "brief.txt").exists()
    assert (day_dir / "gate.jsonl").exists()
    assert (day_dir / "dashboard.txt").exists()
    assert (day_dir / "bundle_manifest.jsonl").exists()

    # Verify that gate.jsonl states blocked_or_invalid
    gate_content = json.loads((day_dir / "gate.jsonl").read_text(encoding="utf-8").strip())
    assert gate_content["acceptance_gate_state"] == "blocked_or_invalid"
    assert gate_content["accepted_for_operator_observation"] is False
    assert "open_order_present" in gate_content["blockers"]


def test_etf_sma_daily_date_derivation(tmp_path: Path) -> None:
    """Test that the default as-of date is derived deterministically from the latest bar timestamp."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailyConfig(
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    )

    payload = run_etf_sma_daily(config)
    # The latest date in spy_daily_bars_200_bullish.csv should be used
    derived_date = payload["as_of_date"]
    assert derived_date is not None
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", derived_date)

    # Ensure files are created under that derived date folder
    assert (output_root / derived_date).exists()
    assert (output_root / derived_date / "cycle.jsonl").exists()


def test_etf_sma_daily_rebuild_index(tmp_path: Path) -> None:
    """Test that index rebuilds correctly from multiple daily runs sorted ascending."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    # Run 1: 2026-06-06
    run_etf_sma_daily(EtfSmaDailyConfig(
        as_of_date="2026-06-06",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    ))

    # Run 2: 2026-06-05 (earlier date run later)
    run_etf_sma_daily(EtfSmaDailyConfig(
        as_of_date="2026-06-05",
        output_root=output_root,
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
    ))

    index_content = (output_root / "daily_run_index.jsonl").read_text(encoding="utf-8").strip()
    lines = index_content.splitlines()
    assert len(lines) == 2
    
    rec0 = json.loads(lines[0])
    rec1 = json.loads(lines[1])
    
    # Must be sorted ascending by date
    assert rec0["as_of_date"] == "2026-06-05"
    assert rec1["as_of_date"] == "2026-06-06"


def test_cli_command_success(tmp_path: Path) -> None:
    """Test the CLI entrypoint for a successful run."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    code = cli_module.main([
        "etf-sma-daily",
        "--as-of-date", "2026-06-05",
        "--output-root", str(output_root),
        "--bars-csv", str(bars_csv),
        "--reconciliation-state-path", str(reco_path),
        "--format", "json",
    ])
    assert code == 0


def test_cli_command_blocked(tmp_path: Path) -> None:
    """Test the CLI entrypoint exits with a nonzero code on gate failure/blocker."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_open_order.jsonl"

    code = cli_module.main([
        "etf-sma-daily",
        "--as-of-date", "2026-06-05",
        "--output-root", str(output_root),
        "--bars-csv", str(bars_csv),
        "--reconciliation-state-path", str(reco_path),
        "--format", "json",
    ])
    assert code == 1


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
