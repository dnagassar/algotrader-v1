from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import pytest
from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_offline_daily_cycle_rerun_m446 import (
    EtfSmaOfflineDailyCycleRerunM446Config,
    build_etf_sma_offline_daily_cycle_rerun_m446,
    run_etf_sma_offline_daily_cycle_rerun_m446,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_offline_daily_cycle_rerun_m446.py")

EXPECTED_SHA256 = "408fd46ef351442cbcb72067e7c7874d92981554fe560b68e3da98492b77db69"
VALIDATED_AT = "2026-06-08T20:33:47+00:00"
RUN_ID = "m447_unit_test"

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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_csv(path: Path, latest_date: str = "2026-06-08") -> str:
    columns = ("symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume")
    rows = [
        {"symbol": "SPY", "date": "1993-01-29", "open": "43.9", "high": "43.9", "low": "43.7", "close": "43.9", "adjusted_close": "25.0", "volume": "1000"},
    ]
    from datetime import date, timedelta
    end_date = date.fromisoformat(latest_date)
    for i in range(200):
        d = end_date - timedelta(days=(200 - i - 1))
        rows.append({
            "symbol": "SPY",
            "date": d.isoformat(),
            "open": "100.0",
            "high": "100.0",
            "low": "100.0",
            "close": "100.0",
            "adjusted_close": str(100.0 + i),
            "volume": "1000",
        })

    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row[col] for col in columns))
    content = "\n".join(lines) + "\n"
    path.write_bytes(content.encode("utf-8"))
    return _sha256(content.encode("utf-8"))


def _write_manifest(
    path: Path,
    csv_path: str = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    csv_sha256: str = EXPECTED_SHA256,
    latest_date: str = "2026-06-08",
) -> None:
    record = {
        "milestone": "M446",
        "latest_local_bar_date": latest_date,
        "expected_latest_bar_date": latest_date,
        "refreshed_canonical_csv_path": csv_path,
        "refreshed_canonical_csv_sha256": csv_sha256,
        "refresh_blockers": [],
        "refresh_state": "accepted_current_adjusted_bars",
    }
    content = json.dumps(record) + "\n"
    path.write_bytes(content.encode("utf-8"))


def _write_recon(path: Path) -> None:
    record = {
        "run_id": "m439_m436_spy_buy_fresh_read_only_reconciliation",
        "symbol": "SPY",
        "client_order_id": "client-id",
        "broker_order_id": "broker-id",
        "expected_side": "buy",
        "expected_qty": "",
        "observed_status": "filled",
        "observed_symbol": "SPY",
        "observed_side": "buy",
        "observed_qty": "",
        "observed_filled_qty": "0.033695775",
        "observed_remaining_qty": "0E-9",
        "exact_order_found": True,
        "exact_order_source": "all",
        "terminal_state": "terminal",
        "terminal_reason": "status_filled",
        "reconciliation_decision": "m376_terminal_filled",
        "next_spy_submit_blocked": False,
        "reason": "status_filled",
        "spy_position_qty": "0.033695775",
        "open_order_count": 0,
        "spy_open_order_count": 0,
        "open_order_symbols": [],
        "open_order_client_order_ids": [],
        "open_order_broker_order_ids": [],
        "open_order_statuses": [],
        "open_order_sides": [],
        "open_order_quantities": [],
        "open_order_filled_quantities": [],
        "non_spy_positions": [],
        "blockers": [],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "account_observation_available": True,
        "positions_observation_available": True,
        "orders_observation_available": True,
    }
    content = json.dumps(record) + "\n"
    path.write_bytes(content.encode("utf-8"))


def test_successful_rerun_execution(tmp_path) -> None:
    manifest_path = tmp_path / "m446_manifest.jsonl"
    csv_path = tmp_path / "m446_canonical.csv"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    csv_sha = _write_csv(csv_path)
    _write_manifest(manifest_path, csv_path=str(csv_path), csv_sha256=csv_sha)
    _write_recon(recon_path)

    config = EtfSmaOfflineDailyCycleRerunM446Config(
        run_id=RUN_ID,
        source_m446_manifest_path=manifest_path,
        source_m446_canonical_csv_path=csv_path,
        expected_m446_csv_sha256=csv_sha,
        order_reconciliation_log=recon_path,
        validated_at=VALIDATED_AT,
        expected_latest_bar_date="2026-06-08",
        output_jsonl=output_path,
    )

    payload = run_etf_sma_offline_daily_cycle_rerun_m446(config)

    assert payload["milestone"] == "M447"
    assert payload["run_id"] == RUN_ID
    assert payload["source_m446_manifest_path"] == str(manifest_path)
    assert payload["source_m446_canonical_csv_path"] == str(csv_path)
    assert payload["source_m446_canonical_csv_sha256"] == csv_sha
    assert payload["expected_latest_bar_date"] == "2026-06-08"
    assert payload["latest_local_bar_date"] == "2026-06-08"
    assert payload["freshness_state"] == "accepted_current_adjusted_bars"
    assert payload["freshness_blockers"] == []
    assert payload["posture"] == "risk_on"
    assert payload["cycle_decision"] == "hold/noop"
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
    csv_path = tmp_path / "m446_canonical.csv"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    csv_sha = _write_csv(csv_path)
    _write_recon(recon_path)

    config = EtfSmaOfflineDailyCycleRerunM446Config(
        run_id=RUN_ID,
        source_m446_manifest_path=tmp_path / "nonexistent.jsonl",
        source_m446_canonical_csv_path=csv_path,
        expected_m446_csv_sha256=csv_sha,
        order_reconciliation_log=recon_path,
        validated_at=VALIDATED_AT,
        output_jsonl=output_path,
    )

    with pytest.raises(ValidationError, match="M446 manifest file missing"):
        build_etf_sma_offline_daily_cycle_rerun_m446(config)


def test_fails_closed_missing_csv(tmp_path) -> None:
    manifest_path = tmp_path / "m446_manifest.jsonl"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    _write_manifest(manifest_path, csv_path="nonexistent.csv", csv_sha256=EXPECTED_SHA256)
    _write_recon(recon_path)

    config = EtfSmaOfflineDailyCycleRerunM446Config(
        run_id=RUN_ID,
        source_m446_manifest_path=manifest_path,
        source_m446_canonical_csv_path=tmp_path / "nonexistent.csv",
        expected_m446_csv_sha256=EXPECTED_SHA256,
        order_reconciliation_log=recon_path,
        validated_at=VALIDATED_AT,
        output_jsonl=output_path,
    )

    with pytest.raises(ValidationError, match="M446 canonical CSV missing"):
        build_etf_sma_offline_daily_cycle_rerun_m446(config)


def test_fails_closed_csv_sha256_mismatch_with_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "m446_manifest.jsonl"
    csv_path = tmp_path / "m446_canonical.csv"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    _write_csv(csv_path)
    _write_manifest(manifest_path, csv_path=str(csv_path), csv_sha256="wrong_hash")
    _write_recon(recon_path)

    config = EtfSmaOfflineDailyCycleRerunM446Config(
        run_id=RUN_ID,
        source_m446_manifest_path=manifest_path,
        source_m446_canonical_csv_path=csv_path,
        expected_m446_csv_sha256="wrong_hash",
        order_reconciliation_log=recon_path,
        validated_at=VALIDATED_AT,
        output_jsonl=output_path,
    )

    with pytest.raises(ValidationError, match="M446 CSV SHA256 mismatch"):
        build_etf_sma_offline_daily_cycle_rerun_m446(config)


def test_fails_closed_csv_sha256_mismatch_with_expected(tmp_path) -> None:
    manifest_path = tmp_path / "m446_manifest.jsonl"
    csv_path = tmp_path / "m446_canonical.csv"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    csv_sha = _write_csv(csv_path)
    _write_manifest(manifest_path, csv_path=str(csv_path), csv_sha256=csv_sha)
    _write_recon(recon_path)

    config = EtfSmaOfflineDailyCycleRerunM446Config(
        run_id=RUN_ID,
        source_m446_manifest_path=manifest_path,
        source_m446_canonical_csv_path=csv_path,
        expected_m446_csv_sha256="different_hash",
        order_reconciliation_log=recon_path,
        validated_at=VALIDATED_AT,
        output_jsonl=output_path,
    )

    with pytest.raises(ValidationError, match="M446 CSV SHA256 mismatch"):
        build_etf_sma_offline_daily_cycle_rerun_m446(config)


def test_fails_closed_invalid_expected_latest_bar_date(tmp_path) -> None:
    manifest_path = tmp_path / "m446_manifest.jsonl"
    csv_path = tmp_path / "m446_canonical.csv"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    csv_sha = _write_csv(csv_path)
    _write_manifest(manifest_path, csv_path=str(csv_path), csv_sha256=csv_sha)
    _write_recon(recon_path)

    config = EtfSmaOfflineDailyCycleRerunM446Config(
        run_id=RUN_ID,
        source_m446_manifest_path=manifest_path,
        source_m446_canonical_csv_path=csv_path,
        expected_m446_csv_sha256=csv_sha,
        order_reconciliation_log=recon_path,
        validated_at=VALIDATED_AT,
        expected_latest_bar_date="2026-06-07",
        output_jsonl=output_path,
    )

    with pytest.raises(ValidationError, match="expected_latest_bar_date must be 2026-06-08"):
        build_etf_sma_offline_daily_cycle_rerun_m446(config)


def test_fails_closed_manifest_date_mismatch(tmp_path) -> None:
    manifest_path = tmp_path / "m446_manifest.jsonl"
    csv_path = tmp_path / "m446_canonical.csv"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    csv_sha = _write_csv(csv_path)
    _write_manifest(manifest_path, csv_path=str(csv_path), csv_sha256=csv_sha, latest_date="2026-06-07")
    _write_recon(recon_path)

    config = EtfSmaOfflineDailyCycleRerunM446Config(
        run_id=RUN_ID,
        source_m446_manifest_path=manifest_path,
        source_m446_canonical_csv_path=csv_path,
        expected_m446_csv_sha256=csv_sha,
        order_reconciliation_log=recon_path,
        validated_at=VALIDATED_AT,
        output_jsonl=output_path,
    )

    with pytest.raises(ValidationError, match="M446 latest_local_bar_date is not 2026-06-08"):
        build_etf_sma_offline_daily_cycle_rerun_m446(config)


def test_fails_closed_csv_date_mismatch(tmp_path) -> None:
    manifest_path = tmp_path / "m446_manifest.jsonl"
    csv_path = tmp_path / "m446_canonical.csv"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    csv_sha = _write_csv(csv_path, latest_date="2026-06-07")
    _write_manifest(manifest_path, csv_path=str(csv_path), csv_sha256=csv_sha)
    _write_recon(recon_path)

    config = EtfSmaOfflineDailyCycleRerunM446Config(
        run_id=RUN_ID,
        source_m446_manifest_path=manifest_path,
        source_m446_canonical_csv_path=csv_path,
        expected_m446_csv_sha256=csv_sha,
        order_reconciliation_log=recon_path,
        validated_at=VALIDATED_AT,
        output_jsonl=output_path,
    )

    with pytest.raises(ValidationError, match="CSV latest date is not 2026-06-08"):
        build_etf_sma_offline_daily_cycle_rerun_m446(config)


def test_cli_dispatch_works(tmp_path, monkeypatch, capsys) -> None:
    manifest_path = tmp_path / "m446_manifest.jsonl"
    csv_path = tmp_path / "m446_canonical.csv"
    recon_path = tmp_path / "reconciliation.jsonl"
    output_path = tmp_path / "m447_manifest.jsonl"

    csv_sha = _write_csv(csv_path)
    _write_manifest(manifest_path, csv_path=str(csv_path), csv_sha256=csv_sha)
    _write_recon(recon_path)

    exit_code = cli_module.main(
        [
            "etf-sma-offline-daily-cycle-rerun-m446",
            "--run-id",
            RUN_ID,
            "--source-m446-manifest-path",
            str(manifest_path),
            "--source-m446-canonical-csv-path",
            str(csv_path),
            "--expected-m446-csv-sha256",
            csv_sha,
            "--order-reconciliation-log",
            str(recon_path),
            "--validated-at",
            VALIDATED_AT,
            "--output-jsonl",
            str(output_path),
            "--format",
            "json",
        ]
    )

    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert printed["milestone"] == "M447"
    assert printed["run_id"] == RUN_ID


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
