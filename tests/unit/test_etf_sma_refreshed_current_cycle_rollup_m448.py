from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_refreshed_current_cycle_rollup_m448 import (
    EtfSmaRefreshedCurrentCycleRollupM448Config,
    build_etf_sma_refreshed_current_cycle_rollup_m448,
    run_etf_sma_refreshed_current_cycle_rollup_m448,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_refreshed_current_cycle_rollup_m448.py")
EXPECTED_CSV_SHA = "408fd46ef351442cbcb72067e7c7874d92981554fe560b68e3da98492b77db69"
EXPECTED_DATE = "2026-06-08"
RUN_ID = "m448_unit_test"

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


def _write_m447_manifest(
    path: Path,
    csv_sha: str = EXPECTED_CSV_SHA,
    latest_date: str = EXPECTED_DATE,
    expected_date: str = EXPECTED_DATE,
    freshness_state: str = "accepted_current_adjusted_bars",
    freshness_blockers: list = None,
    cycle_decision: str = "hold/noop",
    recommended_operator_action: str = "observe_hold_noop",
    submitted: bool = False,
    mutated: bool = False,
    broker_action_performed: bool = False,
    network_access_attempted: bool = False,
    credential_access_attempted: bool = False,
    live_authorized: bool = False,
    profit_claim: str = "none",
) -> None:
    if freshness_blockers is None:
        freshness_blockers = []
    record = {
        "broker_action_performed": broker_action_performed,
        "command": "etf-sma-offline-daily-cycle-rerun-m446",
        "credential_access_attempted": credential_access_attempted,
        "cycle_decision": cycle_decision,
        "expected_latest_bar_date": expected_date,
        "freshness_blockers": freshness_blockers,
        "freshness_state": freshness_state,
        "latest_local_bar_date": latest_date,
        "live_authorized": live_authorized,
        "milestone": "M447",
        "mutated": mutated,
        "network_access_attempted": network_access_attempted,
        "paper_action_authorized": False,
        "paper_submit_authorized": False,
        "posture": "risk_on",
        "profit_claim": profit_claim,
        "recommended_operator_action": recommended_operator_action,
        "record_type": "etf_sma_offline_daily_cycle_m446_rerun_manifest",
        "run_id": "m447_offline_daily_cycle_m446_rerun",
        "sma200": "682.085890355442307",
        "sma50": "715.3944",
        "source_m446_canonical_csv_path": "runs\\operator_input\\m446_spy_daily_tiingo_adjusted_canonical.csv",
        "source_m446_canonical_csv_sha256": csv_sha,
        "source_m446_manifest_path": "runs\\paper_lab\\m446_adjusted_spy_bars_refresh_manifest.jsonl",
        "source_m446_manifest_sha256": "550747d300cf8bfc3302fbdf2e103fd70b1d10aca8280c01abfd1a81797d9b5a",
        "submit_authorized": False,
        "submitted": submitted,
        "usable_spy_bars": 8396,
    }
    content = json.dumps(record) + "\n"
    path.write_bytes(content.encode("utf-8"))


def test_successful_rollup_execution(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    output_path = tmp_path / "m448_rollup.jsonl"

    _write_m447_manifest(m447_path)

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_refreshed_current_cycle_rollup_m448(config)

    assert payload["milestone"] == "M448"
    assert payload["record_type"] == "m448_refreshed_current_cycle_rollup"
    assert payload["run_id"] == RUN_ID
    assert payload["source_m447_manifest_path"] == str(m447_path)
    assert payload["freshness_state"] == "accepted_current_adjusted_bars"
    assert payload["freshness_blockers"] == []
    assert payload["expected_latest_bar_date"] == EXPECTED_DATE
    assert payload["latest_local_bar_date"] == EXPECTED_DATE
    assert payload["posture"] == "risk_on"
    assert payload["cycle_decision"] == "hold/noop"
    assert payload["current_action"] == "observe_hold_noop"
    assert payload["recommended_operator_action"] == "observe_hold_noop"
    assert payload["paper_action_authorized"] is False
    assert payload["submit_authorized"] is False
    assert payload["paper_submit_authorized"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["profit_claim"] == "none"

    # Verify JSONL content
    lines = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0] == payload


def test_fails_closed_missing_manifest(tmp_path) -> None:
    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=tmp_path / "nonexistent.jsonl",
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="M447 manifest file missing"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_csv_sha256_mismatch(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, csv_sha="wrong_hash")

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="M447 source_m446_canonical_csv_sha256 mismatch"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_expected_latest_bar_date_mismatch(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, expected_date="2026-06-07")

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="M447 expected_latest_bar_date mismatch"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_latest_local_bar_date_mismatch(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, latest_date="2026-06-07")

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="M447 latest_local_bar_date mismatch"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_freshness_state_mismatch(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, freshness_state="stale_bars")

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="M447 freshness_state mismatch"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_freshness_blockers_mismatch(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, freshness_blockers=["some_blocker"])

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="M447 freshness_blockers is not empty"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_cycle_decision_mismatch(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, cycle_decision="buy")

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="M447 cycle_decision mismatch"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_recommended_operator_action_mismatch(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, recommended_operator_action="buy_preview")

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="M447 recommended_operator_action mismatch"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_safety_flags_not_false(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, submitted=True)

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="Safety constraint violation: M447 field 'submitted' is not False"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_fails_closed_profit_claim_not_none(tmp_path) -> None:
    m447_path = tmp_path / "m447_manifest.jsonl"
    _write_m447_manifest(m447_path, profit_claim="some_claim")

    config = EtfSmaRefreshedCurrentCycleRollupM448Config(
        run_id=RUN_ID,
        source_m447_manifest_path=m447_path,
        expected_m447_latest_bar_date=EXPECTED_DATE,
        expected_m446_csv_sha256=EXPECTED_CSV_SHA,
        output_jsonl=tmp_path / "output.jsonl",
    )
    with pytest.raises(ValidationError, match="Safety constraint violation: profit_claim must be 'none'"):
        build_etf_sma_refreshed_current_cycle_rollup_m448(config)


def test_imports_and_calls_invariant() -> None:
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
