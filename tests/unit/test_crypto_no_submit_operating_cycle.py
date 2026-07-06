from __future__ import annotations

import ast
import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess
from collections.abc import Mapping

import pytest

import algotrader.orchestration.crypto_no_submit_operating_cycle as cycle
from algotrader.orchestration.crypto_no_submit_operating_cycle import (
    FINAL_STATES,
    NEXT_OPERATOR_ACTIONS,
    REQUIRED_LABELS,
    SCHEMA_VERSION,
    run_crypto_no_submit_operating_cycle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "src" / "algotrader" / "orchestration" / (
    "crypto_no_submit_operating_cycle.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_crypto_no_submit_operating_cycle.ps1"
DEPENDENCY_GUARD_PATH = PROJECT_ROOT / "tests" / "unit" / "test_dependency_direction.py"
AS_OF = datetime(2026, 7, 4, 0, 30, tzinfo=UTC)
CLIENT_ORDER_ID = "v58-btcusd-paper-cert-bfa9caadd6b57b19"
ENTRY_CLIENT_ORDER_ID = "v510-btcusd-entry-31147aa0135b0e92"
EXIT_CLIENT_ORDER_ID = "v510-btcusd-exit-a32677e4399a7c86"
SENSITIVE_KEY = "crypto-cycle-key-value-not-for-output"


def test_happy_path_selected_candidate_flows_into_no_submit_packet(tmp_path: Path) -> None:
    paths = _write_cycle_inputs(tmp_path)

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)
    status = packet["cycle_status"]

    assert packet["schema_version"] == SCHEMA_VERSION
    assert status["final_state"] == "selected_candidate_no_submit_packet_ready"
    assert status["next_operator_action"] == "review_no_submit_packet"
    assert status["selected_candidate_id"].startswith("crypto:BTCUSD:")
    assert packet["router_result"]["router_decision"] == "selected"
    assert packet["sizing_preview_status"]["sizing_status"] == "preview_ready"
    assert packet["paper_oms_handoff_status"]["handoff_status"] == "approval_required"
    assert packet["dry_run_identity_status"]["dry_run_status"] == "blocked_not_authorized"
    assert packet["autonomy_cadence_status"]["cadence_status"] == (
        "ready_for_supervised_operator_review"
    )
    assert set(REQUIRED_LABELS) <= set(status["labels"])

    artifact_paths = packet["artifact_paths"]
    expected_artifacts = {
        "cycle_brief.md",
        "cycle_status.json",
        "router_result.json",
        "sizing_preview_status.json",
        "paper_oms_handoff_status.json",
        "dry_run_identity_status.json",
        "autonomy_cadence_status.json",
        "next_operator_action.json",
        "operating_record.jsonl",
        "manifest.json",
    }
    assert expected_artifacts == {Path(path).name for path in artifact_paths.values()}

    cycle_status = json.loads(
        Path(artifact_paths["cycle_status"]).read_text(encoding="utf-8")
    )
    next_action = json.loads(
        Path(artifact_paths["next_operator_action"]).read_text(encoding="utf-8")
    )
    manifest = json.loads(Path(artifact_paths["manifest"]).read_text(encoding="utf-8"))
    brief = Path(artifact_paths["cycle_brief"]).read_text(encoding="utf-8")

    assert cycle_status["broker_read_occurred"] is False
    assert next_action["fresh_authorization_required_for_order"] is True
    assert manifest["generated_under_runs"] is True
    assert set(manifest["required_artifacts"]) == {
        "autonomy_cadence_status",
        "cycle_brief",
        "cycle_status",
        "dry_run_identity_status",
        "next_operator_action",
        "operating_record",
        "paper_oms_handoff_status",
        "router_result",
        "sizing_preview_status",
    }
    assert "fresh authorization required for any order: `true`" in brief


def test_router_no_selected_candidate_becomes_no_trade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_cycle_inputs(tmp_path)

    def run_router_no_trade(**_: object) -> dict[str, object]:
        return _router_packet(decision="no_trade")

    monkeypatch.setattr(cycle, "run_opportunity_router", run_router_no_trade)

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)

    assert packet["cycle_status"]["final_state"] == "no_trade"
    assert packet["cycle_status"]["next_operator_action"] == "no_trade"
    assert packet["next_operator_action"]["action"] == "no_trade"


def test_missing_sizing_preview_produces_honest_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_cycle_inputs(tmp_path)

    monkeypatch.setattr(cycle, "run_crypto_qty_sizing_preview", lambda **_: {})

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)

    assert packet["cycle_status"]["final_state"] == "blocked_missing_sizing_preview"
    assert packet["cycle_status"]["next_operator_action"] == (
        "refresh_data_and_rerun_router"
    )
    assert "blocked_missing_sizing_preview" in packet["cycle_status"]["blockers"]


def test_missing_handoff_produces_honest_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_cycle_inputs(tmp_path)

    monkeypatch.setattr(cycle, "run_crypto_paper_oms_handoff", lambda **_: {})

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)

    assert packet["cycle_status"]["final_state"] == "blocked_missing_handoff"
    assert packet["cycle_status"]["next_operator_action"] == "approval_packet_required"
    assert "blocked_missing_handoff" in packet["cycle_status"]["blockers"]


def test_missing_dry_run_identity_produces_honest_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_cycle_inputs(tmp_path)

    monkeypatch.setattr(cycle, "run_crypto_paper_oms_dry_run", lambda **_: {})

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)

    assert packet["cycle_status"]["final_state"] == "blocked_missing_dry_run"
    assert packet["cycle_status"]["next_operator_action"] == "approval_packet_required"
    assert "blocked_missing_dry_run" in packet["cycle_status"]["blockers"]


def test_missing_lifecycle_evidence_produces_honest_blocker(tmp_path: Path) -> None:
    paths = _write_cycle_inputs(tmp_path, include_lifecycle=False)

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)

    assert packet["cycle_status"]["final_state"] == "blocked_missing_lifecycle_evidence"
    assert packet["cycle_status"]["next_operator_action"] == "blocked"
    assert "submit_cancel_result_missing" in packet["cycle_status"]["blockers"]


def test_no_submit_flags_remain_false_for_current_cycle(tmp_path: Path) -> None:
    paths = _write_cycle_inputs(tmp_path)

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)
    payloads = [
        packet,
        packet["cycle_status"],
        packet["next_operator_action"],
        json.loads(Path(packet["artifact_paths"]["manifest"]).read_text("utf-8")),
        json.loads(Path(packet["artifact_paths"]["operating_record"]).read_text("utf-8")),
    ]

    for payload in payloads:
        for field_name in cycle.FALSE_SAFETY_FIELDS:
            assert payload[field_name] is False
        assert payload["profit_claim"] == "none"
        assert set(REQUIRED_LABELS) <= set(payload["labels"])


def test_prior_v5_8_and_v5_10_authorizations_are_not_reusable(
    tmp_path: Path,
) -> None:
    paths = _write_cycle_inputs(tmp_path)

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)
    status = packet["cycle_status"]
    next_action = packet["next_operator_action"]

    assert status["prior_v5_8_authorization_status"] == "consumed_not_reusable"
    assert status["prior_v5_10_authorization_status"] == "consumed_not_reusable"
    assert status["prior_authorizations_reusable"] is False
    assert status["fresh_authorization_required_for_order"] is True
    assert next_action["prior_authorizations_reusable"] is False
    assert next_action["fresh_authorization_required_for_order"] is True


def test_no_broker_sdk_import_network_dependency_is_introduced() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    forbidden_prefixes = (
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "algotrader.execution",
        "algotrader.broker",
        "algotrader.brokers",
        "algotrader.runtime",
    )
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    source_text = MODULE_PATH.read_text(encoding="utf-8")

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imported_modules
        for prefix in forbidden_prefixes
    )
    assert call_names.isdisjoint(
        {
            "cancel_order",
            "close_position",
            "connect",
            "create_order",
            "delete",
            "liquidate",
            "replace_order",
            "request",
            "socket.socket",
            "submit_order",
            "urlopen",
        }
    )
    assert "os.environ" not in source_text
    assert "getenv" not in source_text


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    paths = _write_cycle_inputs(tmp_path)

    packet = run_crypto_no_submit_operating_cycle(**paths, write_artifacts=True)
    manifest = json.loads(Path(packet["artifact_paths"]["manifest"]).read_text("utf-8"))
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert manifest["generated_under_runs"] is True
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_decision_and_next_action_enums_are_exact() -> None:
    assert FINAL_STATES == (
        "selected_candidate_no_submit_packet_ready",
        "no_trade",
        "blocked_missing_router_inputs",
        "blocked_router_decision_not_selected",
        "blocked_missing_sizing_preview",
        "blocked_missing_handoff",
        "blocked_missing_dry_run",
        "blocked_missing_lifecycle_evidence",
        "paper_read_reconciliation_required",
        "blocked",
    )
    assert NEXT_OPERATOR_ACTIONS == (
        "review_no_submit_packet",
        "refresh_data_and_rerun_router",
        "approval_packet_required",
        "paper_read_reconciliation_required",
        "blocked",
        "no_trade",
    )


def test_script_contract_is_no_submit_offline_and_invokes_module() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the v5.13 crypto no-submit operating cycle",
        '[string]$OutputRoot = "runs\\crypto_no_submit_operating_cycle\\latest"',
        '[ValidateSet("local_replay", "offline_fixture")]',
        "crypto_no_submit_operating_cycle_mode=offline/no_submit",
        "crypto_no_submit_operating_cycle_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_credential_variables_loaded",
        "preflight_network_flags_loaded",
        "preflight_live_endpoint_indicator",
        "crypto_no_submit_operating_cycle_broker_read_occurred=false",
        "crypto_no_submit_operating_cycle_paper_submit_authorized=false",
        "crypto_no_submit_operating_cycle_paper_submit_occurred=false",
        "crypto_no_submit_operating_cycle_broker_mutation_occurred=false",
        "crypto_no_submit_operating_cycle_live_endpoint_touched=false",
        "fresh_authorization_required_for_order=true",
        "algotrader.orchestration.crypto_no_submit_operating_cycle",
        "--crypto-refresh-output-root",
        "--router-output-root",
        "--preview-notional-cap",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "paper_read_only" not in script
    assert "[switch]$Submit" not in script
    assert "paper_submit_authorized=true" not in script
    assert "submit_order" not in script
    assert "cancel_order" not in script
    assert "replace_order" not in script
    assert "close_position" not in script
    assert "liquidate" not in script


def test_script_blocks_loaded_credentials_without_printing_values(tmp_path: Path) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["ALPACA_API_KEY"] = SENSITIVE_KEY

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "preflight_credential_variables_loaded=true" in result.stdout
    assert "crypto_no_submit_operating_cycle_status=blocked_unsafe_environment" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def test_dependency_direction_guard_includes_cycle_module() -> None:
    guard = DEPENDENCY_GUARD_PATH.read_text(encoding="utf-8")

    assert "algotrader.orchestration.crypto_no_submit_operating_cycle" in guard


def _write_cycle_inputs(
    tmp_path: Path,
    *,
    include_lifecycle: bool = True,
) -> dict[str, object]:
    root = tmp_path / "runs"
    paths: dict[str, object] = {
        "output_root": root / "crypto_no_submit_operating_cycle" / "latest",
        "crypto_refresh_output_root": root
        / "crypto_universe_refresh"
        / "paper_read_repair_latest",
        "router_output_root": root / "opportunity_router" / "paper_read_repair_latest",
        "sizing_preview_output_root": root / "crypto_qty_sizing_preview" / "latest",
        "handoff_output_root": root / "crypto_paper_oms_handoff" / "latest",
        "dry_run_output_root": root / "crypto_paper_oms_dry_run" / "latest",
        "autonomy_cadence_output_root": root / "crypto_paper_autonomy_cadence" / "latest",
        "refresh_mode": "local_replay",
        "bars_csv": root / "operator_input" / "crypto_paper_bars.csv",
        "crypto_visibility_status": root
        / "crypto_paper_visibility"
        / "latest"
        / "latest_status.json",
        "spy_bars_csv": root / "operator_input" / "missing_spy.csv",
        "submit_cancel_result_path": root
        / "crypto_paper_submit_cancel_certification"
        / "latest"
        / "certification_result.json",
        "certification_ingestion_path": root
        / "crypto_paper_certification_ingestion"
        / "latest"
        / "certification_ingestion.json",
        "fill_exit_result_path": root
        / "crypto_paper_fill_exit_certification"
        / "latest"
        / "fill_exit_certification_result.json",
        "fill_exit_ingestion_path": root
        / "crypto_paper_fill_exit_ingestion"
        / "latest"
        / "fill_exit_ingestion.json",
        "preview_notional_cap": "25",
        "as_of": AS_OF.isoformat(),
    }
    _write_crypto_bars(Path(paths["bars_csv"]))
    _write_json(Path(paths["crypto_visibility_status"]), _crypto_visibility_status())
    if include_lifecycle:
        _write_json(Path(paths["submit_cancel_result_path"]), _submit_cancel_result())
        _write_json(Path(paths["certification_ingestion_path"]), _certification_ingestion())
        _write_json(Path(paths["fill_exit_result_path"]), _fill_exit_result())
        _write_json(Path(paths["fill_exit_ingestion_path"]), _fill_exit_ingestion())
    return paths


def _router_packet(*, decision: str) -> dict[str, object]:
    selected = None
    candidate_id = "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview"
    if decision == "selected":
        selected = {
            "candidate_id": candidate_id,
            "asset_class": "crypto",
            "symbol": "BTCUSD",
            "strategy_id": "crypto_vol_adjusted_momentum_24h_preview",
            "blockers": [],
        }
    return {
        "router_decision": {
            "schema_version": "test_router",
            "as_of": AS_OF.isoformat(),
            "decision": decision,
            "selected_candidate_id": candidate_id if selected else None,
            "selected_candidate": selected,
            "selected_symbol": "BTCUSD" if selected else "",
            "selected_asset_class": "crypto" if selected else "",
            "selected_strategy_id": (
                "crypto_vol_adjusted_momentum_24h_preview" if selected else ""
            ),
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "live_mutation_performed": False,
            "profit_claim": "none",
            "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
        },
        "artifact_paths": {},
    }


def _crypto_visibility_status() -> dict[str, object]:
    return {
        "schema_version": "test_crypto_visibility_status",
        "as_of": AS_OF.isoformat(),
        "broker_state_mode": "alpaca_paper_observed",
        "capability_source": "local_test_fixture",
        "crypto_capability": {
            "eligible_crypto_symbols": ["BTC/USD"],
            "selected_symbol": "BTC/USD",
            "selected_symbol_tradable": True,
            "selected_symbol_marginable": False,
            "selected_symbol_fractionable": True,
            "min_order_size": "0.00001",
            "min_trade_increment": "0.00000001",
            "min_notional": "",
        },
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "credential_values_exposed": False,
        "blockers": [],
    }


def _submit_cancel_result() -> dict[str, object]:
    return {
        "schema_version": "v5_8_crypto_paper_submit_cancel_certification_v1",
        "as_of": AS_OF.isoformat(),
        "outcome_classification": "submitted_cancel_confirmed",
        "submit_attempt_count": 1,
        "cancel_attempt_count": 1,
        "broker_read_observed": True,
        "broker_mutation_performed": True,
        "paper_submit_performed": True,
        "paper_cancel_performed": True,
        "live_endpoint_touched": False,
        "live_mutation_performed": False,
        "credential_values_exposed": False,
        "client_order_id": CLIENT_ORDER_ID,
        "symbol": "BTCUSD",
        "final_order_status": "canceled",
        "filled_qty": "0",
        "reconciliation": {
            "filled_qty": "0",
            "final_order_status": "canceled",
            "residual_position": {},
        },
        "final_order": {
            "client_order_id": CLIENT_ORDER_ID,
            "filled_qty": "0",
            "qty": "0.000396783",
            "status": "canceled",
            "symbol": "BTCUSD",
        },
    }


def _certification_ingestion() -> dict[str, object]:
    return {
        "schema_version": "v5_9_crypto_paper_certification_ingestion_v1",
        "record_type": "crypto_paper_certification_ingestion",
        "as_of": AS_OF.isoformat(),
        "certification_status": "certified_submit_cancel_no_fill",
        "prior_certification_id": "v58_btcusd_submit_cancel_abc123",
        "prior_client_order_id": CLIENT_ORDER_ID,
        "paper_submit_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "live_authorized": False,
        "blockers": [],
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }


def _fill_exit_result() -> dict[str, object]:
    return {
        "schema_version": "v5_10_crypto_paper_fill_exit_certification_v1",
        "as_of": AS_OF.isoformat(),
        "outcome_classification": "filled_exit_confirmed",
        "symbol": "BTCUSD",
        "entry_client_order_id": ENTRY_CLIENT_ORDER_ID,
        "exit_client_order_id": EXIT_CLIENT_ORDER_ID,
        "entry_attempt_count": 1,
        "exit_attempt_count": 1,
        "entry_final_status": "filled",
        "entry_filled_qty": "0.00038542",
        "entry_filled_avg_price": "63588.7",
        "position_after_entry": {"symbol": "BTCUSD", "qty": "0.000384456"},
        "exit_final_status": "filled",
        "exit_filled_qty": "0.000384456",
        "exit_filled_avg_price": "63575.36",
        "final_position": {},
        "residual_position_status": "flat_or_no_BTCUSD_position_observed",
        "broker_read_observed": True,
        "broker_mutation_performed": True,
        "paper_submit_performed": True,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "entry_final_order": {
            "client_order_id": ENTRY_CLIENT_ORDER_ID,
            "symbol": "BTCUSD",
            "status": "filled",
            "filled_qty": "0.00038542",
            "filled_avg_price": "63588.7",
        },
        "exit_final_order": {
            "client_order_id": EXIT_CLIENT_ORDER_ID,
            "symbol": "BTCUSD",
            "status": "filled",
            "filled_qty": "0.000384456",
            "filled_avg_price": "63575.36",
        },
    }


def _fill_exit_ingestion() -> dict[str, object]:
    return {
        "schema_version": "v5_11_crypto_paper_fill_exit_ingestion_v1",
        "record_type": "crypto_paper_fill_exit_ingestion",
        "as_of": AS_OF.isoformat(),
        "certification_status": "certified_fill_exit_flat",
        "prior_entry_client_order_id": ENTRY_CLIENT_ORDER_ID,
        "prior_exit_client_order_id": EXIT_CLIENT_ORDER_ID,
        "prior_residual_position_status": "flat_or_no_BTCUSD_position_observed",
        "read_only_reconciliation_status": "flat_reconciliation_required",
        "paper_submit_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "live_authorized": False,
        "blockers": [],
        "labels": [
            "paper_lab_only",
            "fill_exit_certified",
            "not_live_authorized",
            "profit_claim=none",
        ],
    }


def _write_crypto_bars(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    first = AS_OF - timedelta(hours=79)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume"))
        for index in range(80):
            timestamp = first + timedelta(hours=index)
            price = Decimal("99921") + Decimal(index)
            writer.writerow(
                (
                    timestamp.isoformat(),
                    "BTCUSD",
                    "crypto",
                    price,
                    price,
                    price,
                    price,
                    "1000",
                )
            )


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"final_state\":\"selected_candidate_no_submit_packet_ready\"}\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    env["APP_PROFILE"] = "dev"
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_crypto_no_submit_operating_cycle.ps1")
    return powershell
