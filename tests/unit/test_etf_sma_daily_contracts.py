from __future__ import annotations

import ast
import csv
import json
import os
import re
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily import (
    EtfSmaDailyConfig,
    run_etf_sma_daily,
    load_etf_sma_cycle_bars_csv,
)
from algotrader.execution.etf_sma_daily_status import (
    EtfSmaDailyStatusConfig,
    run_etf_sma_daily_status,
)
from algotrader.execution.etf_sma_daily_offline_check import (
    EtfSmaDailyOfflineCheckConfig,
    run_etf_sma_daily_offline_check,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"

V3_DAILY_MODULES = [
    Path("src/algotrader/core/daily_bundle_schema.py"),
    Path("src/algotrader/execution/etf_sma_daily.py"),
    Path("src/algotrader/execution/etf_sma_daily_status.py"),
    Path("src/algotrader/execution/etf_sma_daily_offline_check.py"),
    Path("src/algotrader/execution/etf_sma_daily_soak.py"),
    Path("src/algotrader/execution/etf_sma_daily_soak_brief.py"),
]

FORBIDDEN_IMPORT_PREFIXES = (
    # broker SDKs/adapters
    "alpaca",
    "alpaca_trade_api",
    "polygon",
    "ibapi",
    "ccxt",
    "web3",
    # network clients
    "aiohttp",
    "httpx",
    "requests",
    "socket",
    "urllib",
    # LLM/agent/notebook/vectorbt/QuantConnect
    "anthropic",
    "openai",
    "langchain",
    "langgraph",
    "llm",
    "notebook",
    "ipynb",
    "vectorbt",
    "QuantConnect",
    "quantconnect",
)

FORBIDDEN_CALL_NAMES = {
    # submit/cancel/replace/close/liquidate/delete/retry mutation calls
    "submit_order",
    "submit_order_request",
    "cancel_order",
    "replace_order",
    "close_position",
    "close_all_positions",
    "liquidate",
    "delete",
    "retry",
    # network connections
    "connect",
    "create_connection",
    "request",
    "socket.socket",
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


@pytest.mark.parametrize("module_path", V3_DAILY_MODULES)
def test_v3_daily_modules_architecture_invariants(module_path: Path) -> None:
    """Centralized safety/architecture test scanning V3 daily modules for forbidden imports/calls."""
    assert module_path.exists(), f"Module {module_path} does not exist."
    
    with open(module_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(module_path))
        
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
                
    # Verify imports
    for imp in imports:
        for prefix in FORBIDDEN_IMPORT_PREFIXES:
            assert not (imp == prefix or imp.startswith(f"{prefix}.")), (
                f"Forbidden import '{imp}' found in {module_path}."
            )
            
    # Verify call names
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
    assert not violations, f"Forbidden calls {violations} found in {module_path}."


def test_bundle_level_lookahead_regression(tmp_path: Path) -> None:
    """Verify that future bars do not affect posture/decision and ignored_future_bar_count is correct."""
    base_bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    bars = load_etf_sma_cycle_bars_csv(base_bars_csv, symbol="SPY")
    
    assert len(bars) >= 200
    
    # Pick the 190th bar as our as_of_date boundary (index 189)
    boundary_bar = bars[189]
    as_of_date = boundary_bar.timestamp.strftime("%Y-%m-%d")
    
    future_bars_count = len(bars) - 190
    assert future_bars_count > 0
    
    # Write a truncated CSV containing only the first 190 bars
    truncated_csv_path = tmp_path / "truncated_bars.csv"
    with open(base_bars_csv, "r", encoding="utf-8") as fin:
        reader = csv.reader(fin)
        headers = next(reader)
        rows = list(reader)
        
    # Keep only headers and the first 190 data rows
    with open(truncated_csv_path, "w", encoding="utf-8", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerow(headers)
        writer.writerows(rows[:190])
        
    # Run daily bundle with the FULL CSV
    output_root_full = tmp_path / "full"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"
    
    run_etf_sma_daily(EtfSmaDailyConfig(
        as_of_date=as_of_date,
        output_root=output_root_full,
        bars_csv=base_bars_csv,
        reconciliation_state_path=reco_path,
    ))
    
    # Run daily bundle with the TRUNCATED CSV
    output_root_trunc = tmp_path / "trunc"
    run_etf_sma_daily(EtfSmaDailyConfig(
        as_of_date=as_of_date,
        output_root=output_root_trunc,
        bars_csv=truncated_csv_path,
        reconciliation_state_path=reco_path,
    ))
    
    # Load brief JSONL files from both runs
    brief_full = json.loads((output_root_full / as_of_date / "brief.jsonl").read_text(encoding="utf-8").strip())
    brief_trunc = json.loads((output_root_trunc / as_of_date / "brief.jsonl").read_text(encoding="utf-8").strip())
    
    # Decisions and posture must be identical
    assert brief_full["cycle_decision"] == brief_trunc["cycle_decision"]
    assert brief_full["posture"] == brief_trunc["posture"]
    assert brief_full["current_action"] == brief_trunc["current_action"]
    assert brief_full["brief_state"] == brief_trunc["brief_state"]
    
    # Load cycle JSONL files
    cycle_full = json.loads((output_root_full / as_of_date / "cycle.jsonl").read_text(encoding="utf-8").strip())
    cycle_trunc = json.loads((output_root_trunc / as_of_date / "cycle.jsonl").read_text(encoding="utf-8").strip())
    
    # Verify ignored_future_bar_count is correct
    assert cycle_full["market_data"]["ignored_future_bar_count"] == future_bars_count
    assert cycle_trunc["market_data"]["ignored_future_bar_count"] == 0
    
    # Posture/decision should match
    assert cycle_full["decision"] == cycle_trunc["decision"]
    assert cycle_full["sma_posture"] == cycle_trunc["sma_posture"]


def test_no_absolute_paths_assertion(tmp_path: Path) -> None:
    """Verify that none of the generated daily loop artifacts contain absolute path strings."""
    # We construct a relative directory under the current working directory for the run
    # to make sure relative path normalization can be applied correctly
    test_run_dir = Path("runs/test_contract_absolute_path_assertion")
    if test_run_dir.exists():
        import shutil
        shutil.rmtree(test_run_dir, ignore_errors=True)
        
    try:
        bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
        reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"
        
        # Run offline check command (which runs daily bundle, status validation, and offline check)
        run_etf_sma_daily_offline_check(EtfSmaDailyOfflineCheckConfig(
            as_of_date="2026-06-05",
            output_root=test_run_dir,
            bars_csv=bars_csv,
            reconciliation_state_path=reco_path,
        ))
        
        # Check files that are generated
        bundle_dir = test_run_dir / "2026-06-05"
        index_file = test_run_dir / "daily_run_index.jsonl"
        
        generated_files = [
            bundle_dir / "cycle.jsonl",
            bundle_dir / "brief.jsonl",
            bundle_dir / "brief.txt",
            bundle_dir / "gate.jsonl",
            bundle_dir / "dashboard.txt",
            bundle_dir / "bundle_manifest.jsonl",
            bundle_dir / "bundle_status.jsonl",
            bundle_dir / "bundle_status.txt",
            bundle_dir / "offline_check.jsonl",
            bundle_dir / "offline_check.txt",
            index_file,
        ]
        
        cwd_str = str(Path.cwd().resolve())
        cwd_str_posix = cwd_str.replace("\\", "/")
        
        for filepath in generated_files:
            assert filepath.exists(), f"Expected file {filepath} was not generated."
            content = filepath.read_text(encoding="utf-8")
            
            # Assert no resolved current working directory paths appear in the file content
            assert cwd_str not in content, f"Absolute path leak (resolved CWD) in {filepath}"
            assert cwd_str_posix not in content, f"Absolute path leak (POSIX resolved CWD) in {filepath}"
            
            # Assert no drive-letter style absolute paths appear (e.g. C:\ or C:/)
            assert not re.search(r"[a-zA-Z]:[\\/]", content), f"Absolute drive path leak in {filepath}"
            
            # If JSONL, verify specific key values recursively
            if filepath.suffix == ".jsonl":
                for line in content.splitlines():
                    if line.strip():
                        obj = json.loads(line)
                        _verify_no_absolute_paths_in_obj(obj, filepath)
                        
    finally:
        import shutil
        shutil.rmtree(test_run_dir, ignore_errors=True)


def _verify_no_absolute_paths_in_obj(val: any, filepath: Path) -> None:
    if isinstance(val, str):
        # Assert no windows absolute paths
        assert not re.match(r"^[a-zA-Z]:[\\/]", val), f"Absolute path '{val}' found in JSON {filepath}"
        # Assert no UNIX absolute paths (except URL schemes or double slashes)
        if val.startswith("/") and not val.startswith("//"):
            assert False, f"UNIX Absolute path '{val}' found in JSON {filepath}"
    elif isinstance(val, dict):
        for k, v in val.items():
            _verify_no_absolute_paths_in_obj(v, filepath)
    elif isinstance(val, list):
        for item in val:
            _verify_no_absolute_paths_in_obj(item, filepath)
