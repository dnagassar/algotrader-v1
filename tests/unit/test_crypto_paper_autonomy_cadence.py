from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.orchestration.crypto_paper_autonomy_cadence import (
    FALSE_AUTHORIZATION_FIELDS,
    REQUIRED_LABELS,
    SCHEMA_VERSION,
    run_crypto_paper_autonomy_cadence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "orchestration"
    / "crypto_paper_autonomy_cadence.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_crypto_paper_autonomy_cadence.ps1"
DEPENDENCY_GUARD_PATH = PROJECT_ROOT / "tests" / "unit" / "test_dependency_direction.py"
AS_OF = "2026-07-06T00:00:00+00:00"
CLIENT_ORDER_ID = "v58-btcusd-paper-cert-bfa9caadd6b57b19"
ENTRY_CLIENT_ORDER_ID = "v510-btcusd-entry-31147aa0135b0e92"
EXIT_CLIENT_ORDER_ID = "v510-btcusd-exit-a32677e4399a7c86"
SELECTED_CANDIDATE_ID = "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview"
SENSITIVE_KEY = "SENTINEL_ALPACA_SECRET_DO_NOT_PRINT"


def test_successful_lifecycle_and_candidate_inputs_produce_operator_review_packet(
    tmp_path: Path,
) -> None:
    paths = _write_all_inputs(tmp_path)

    cadence = run_crypto_paper_autonomy_cadence(**paths, write_artifacts=True)

    assert cadence["schema_version"] == SCHEMA_VERSION
    assert cadence["cadence_status"] == "ready_for_supervised_operator_review"
    assert cadence["next_action"] == "operator_review_required"
    assert cadence["lifecycle_certified"] is True
    assert cadence["submit_cancel_certified"] is True
    assert cadence["fill_exit_certified"] is True
    assert cadence["final_flat_observed"] is True
    assert cadence["current_router_candidate_eligible"] is True
    assert cadence["current_candidate_eligible"] is True
    assert cadence["paper_submit_currently_authorized"] is False
    assert cadence["would_do_next_if_authorization_granted"] == (
        "prepare_one_bounded_BTCUSD_paper_entry_from_dry_run_identity_for_"
        "operator_authorized_submit_flow"
    )
    assert cadence["blockers"] == []
    assert set(REQUIRED_LABELS) <= set(cadence["labels"])

    evidence = cadence["paper_lifecycle_evidence"]
    assert evidence["submit_cancel_evidence"]["client_order_id"] == CLIENT_ORDER_ID
    assert evidence["fill_exit_evidence"]["entry_client_order_id"] == (
        ENTRY_CLIENT_ORDER_ID
    )
    assert evidence["fill_exit_evidence"]["exit_client_order_id"] == (
        EXIT_CLIENT_ORDER_ID
    )
    assert "prior_operator_authorizations_are_consumed_and_not_reusable" in evidence[
        "evidence_learned"
    ]

    artifact_paths = cadence["artifact_paths"]
    assert set(artifact_paths) == {
        "autonomy_cadence_brief",
        "autonomy_cadence_status",
        "paper_lifecycle_evidence",
        "next_operator_action",
        "operating_record",
        "manifest",
    }
    status = json.loads(
        Path(artifact_paths["autonomy_cadence_status"]).read_text(encoding="utf-8")
    )
    lifecycle = json.loads(
        Path(artifact_paths["paper_lifecycle_evidence"]).read_text(encoding="utf-8")
    )
    action = json.loads(
        Path(artifact_paths["next_operator_action"]).read_text(encoding="utf-8")
    )
    manifest = json.loads(Path(artifact_paths["manifest"]).read_text(encoding="utf-8"))
    operating_record = json.loads(
        Path(artifact_paths["operating_record"]).read_text(encoding="utf-8")
    )
    brief = Path(artifact_paths["autonomy_cadence_brief"]).read_text(encoding="utf-8")

    assert status["next_action"] == "operator_review_required"
    assert lifecycle["lifecycle_certified"] is True
    assert action["action"] == "operator_review_required"
    assert operating_record["fresh_authorization_required_for_order"] is True
    assert manifest["generated_under_runs"] is True
    assert "paper submit currently authorized: `false`" in brief


def test_missing_v5_10_and_v5_11_artifacts_block_lifecycle_certification(
    tmp_path: Path,
) -> None:
    paths = _write_all_inputs(tmp_path, include_fill_exit=False)

    cadence = run_crypto_paper_autonomy_cadence(**paths, write_artifacts=True)

    assert cadence["cadence_status"] == "blocked"
    assert cadence["next_action"] == "blocked"
    assert cadence["lifecycle_certified"] is False
    assert cadence["fill_exit_certified"] is False
    assert "fill_exit_result_missing" in cadence["blockers"]
    assert "fill_exit_ingestion_missing" in cadence["blockers"]
    assert (
        "final_flat_not_observed_from_v5_10_or_v5_11_artifact"
        in cadence["blockers"]
    )
    assert cadence["paper_submit_authorized"] is False


def test_prior_v5_8_and_v5_10_authorizations_are_not_reusable(
    tmp_path: Path,
) -> None:
    paths = _write_all_inputs(tmp_path)

    cadence = run_crypto_paper_autonomy_cadence(**paths, write_artifacts=False)
    evidence = cadence["paper_lifecycle_evidence"]
    next_operator_action = cadence["next_operator_action"]

    assert cadence["prior_v5_8_authorization_status"] == "consumed_not_reusable"
    assert cadence["prior_v5_10_authorization_status"] == "consumed_not_reusable"
    assert cadence["prior_authorizations_reusable"] is False
    assert cadence["fresh_authorization_required_for_order"] is True
    assert evidence["prior_authorizations_reusable"] is False
    assert next_operator_action["fresh_authorization_required_for_order"] is True
    assert "fresh_authorization_required_for_order" in cadence["labels"]
    assert cadence["paper_submit_authorized"] is False
    assert cadence["broker_mutation_authorized"] is False
    assert cadence["live_authorized"] is False


def test_no_submit_flags_remain_false_across_generated_payloads(tmp_path: Path) -> None:
    paths = _write_all_inputs(tmp_path)

    cadence = run_crypto_paper_autonomy_cadence(**paths, write_artifacts=True)
    artifact_paths = cadence["artifact_paths"]
    payloads = [
        cadence,
        cadence["paper_lifecycle_evidence"],
        cadence["candidate_evidence"],
        cadence["next_operator_action"],
        json.loads(Path(artifact_paths["manifest"]).read_text(encoding="utf-8")),
        json.loads(Path(artifact_paths["operating_record"]).read_text(encoding="utf-8")),
    ]

    for payload in payloads:
        assert payload["paper_submit_authorized"] is False
        assert payload["broker_mutation_authorized"] is False
        assert payload["live_authorized"] is False
        for field_name in FALSE_AUTHORIZATION_FIELDS:
            if field_name in payload:
                assert payload[field_name] is False
        assert payload["profit_claim"] == "none"


def test_missing_router_sizing_handoff_and_dry_run_inputs_report_honest_blockers(
    tmp_path: Path,
) -> None:
    paths = _write_all_inputs(tmp_path, include_candidate_inputs=False)

    cadence = run_crypto_paper_autonomy_cadence(**paths, write_artifacts=False)

    assert cadence["lifecycle_certified"] is True
    assert cadence["current_router_candidate_eligible"] is False
    assert cadence["current_candidate_eligible"] is False
    assert cadence["next_action"] == "refresh_data_and_rerun_router"
    assert cadence["cadence_status"] == "action_required"
    assert "router_decision_missing" in cadence["blockers"]
    assert "sizing_preview_missing" in cadence["blockers"]
    assert "paper_oms_handoff_missing" in cadence["blockers"]
    assert "paper_oms_dry_run_missing" in cadence["blockers"]
    assert cadence["would_do_next_if_authorization_granted"] == (
        "do_nothing_no_current_router_candidate"
    )


def test_normal_pytest_path_remains_offline_broker_free_and_credential_free() -> None:
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
    source_text = MODULE_PATH.read_text(encoding="utf-8")
    assert "os.environ" not in source_text
    assert "getenv" not in source_text


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    paths = _write_all_inputs(tmp_path)

    cadence = run_crypto_paper_autonomy_cadence(**paths, write_artifacts=True)
    manifest = json.loads(
        Path(cadence["artifact_paths"]["manifest"]).read_text(encoding="utf-8")
    )
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert manifest["generated_under_runs"] is True
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")


def test_dependency_direction_guard_includes_cadence_module() -> None:
    guard = DEPENDENCY_GUARD_PATH.read_text(encoding="utf-8")

    assert "algotrader.orchestration.crypto_paper_autonomy_cadence" in guard


def test_runner_script_contract_is_no_submit_and_offline() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the supervised crypto paper autonomy cadence controller in no-submit mode",
        '[string]$OutputRoot = "runs\\crypto_paper_autonomy_cadence\\latest"',
        "crypto_paper_autonomy_cadence_mode=offline/no_submit",
        "crypto_paper_autonomy_cadence_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_APP_PROFILE_is_live",
        "preflight_credential_variables_loaded",
        "preflight_network_flags_loaded",
        "preflight_live_endpoint_indicator",
        "crypto_paper_autonomy_cadence_paper_submit_authorized=false",
        "crypto_paper_autonomy_cadence_paper_submit_performed=false",
        "crypto_paper_autonomy_cadence_broker_read_performed=false",
        "crypto_paper_autonomy_cadence_broker_mutation_performed=false",
        "crypto_paper_autonomy_cadence_fresh_authorization_required_for_order=true",
        "algotrader.orchestration.crypto_paper_autonomy_cadence",
        "--submit-cancel-result-path",
        "--fill-exit-ingestion-path",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert " -Submit" not in script
    assert "[switch]$Submit" not in script
    assert "paper_submit_authorized=true" not in script
    assert "submit_order" not in script
    assert "cancel_order" not in script
    assert "replace_order" not in script
    assert "close_position" not in script
    assert "liquidate" not in script


def test_runner_script_blocks_loaded_credentials_without_printing_values(
    tmp_path: Path,
) -> None:
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
    assert "crypto_paper_autonomy_cadence_status=blocked_unsafe_environment" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def _write_all_inputs(
    tmp_path: Path,
    *,
    include_fill_exit: bool = True,
    include_candidate_inputs: bool = True,
) -> dict[str, Path]:
    root = tmp_path / "runs"
    paths = {
        "submit_cancel_result_path": (
            root
            / "crypto_paper_submit_cancel_certification"
            / "latest"
            / "certification_result.json"
        ),
        "certification_ingestion_path": (
            root
            / "crypto_paper_certification_ingestion"
            / "latest"
            / "certification_ingestion.json"
        ),
        "fill_exit_result_path": (
            root
            / "crypto_paper_fill_exit_certification"
            / "latest"
            / "fill_exit_certification_result.json"
        ),
        "fill_exit_ingestion_path": (
            root
            / "crypto_paper_fill_exit_ingestion"
            / "latest"
            / "fill_exit_ingestion.json"
        ),
        "router_decision_path": (
            root
            / "opportunity_router"
            / "paper_read_repair_latest"
            / "router_decision.json"
        ),
        "sizing_preview_path": (
            root / "crypto_qty_sizing_preview" / "latest" / "sizing_preview.json"
        ),
        "handoff_path": (
            root / "crypto_paper_oms_handoff" / "latest" / "paper_oms_handoff.json"
        ),
        "dry_run_path": (
            root / "crypto_paper_oms_dry_run" / "latest" / "paper_oms_dry_run.json"
        ),
        "output_root": root / "crypto_paper_autonomy_cadence" / "latest",
    }
    _write_json(paths["submit_cancel_result_path"], _submit_cancel_result())
    _write_json(paths["certification_ingestion_path"], _certification_ingestion())
    if include_fill_exit:
        _write_json(paths["fill_exit_result_path"], _fill_exit_result())
        _write_json(paths["fill_exit_ingestion_path"], _fill_exit_ingestion())
    if include_candidate_inputs:
        _write_json(paths["router_decision_path"], _router_decision())
        _write_json(paths["sizing_preview_path"], _sizing_preview())
        _write_json(paths["handoff_path"], _handoff())
        _write_json(paths["dry_run_path"], _dry_run())
    return paths


def _submit_cancel_result() -> dict[str, object]:
    return copy.deepcopy(
        {
            "schema_version": "v5_8_crypto_paper_submit_cancel_certification_v1",
            "as_of": AS_OF,
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
            "expected_account_matched": True,
            "submitted_qty": "0.000396783",
            "approved_qty": "0.000396783",
            "estimated_submit_notional": "12.49999372305",
            "approved_max_notional": "25",
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
    )


def _certification_ingestion() -> dict[str, object]:
    return {
        "schema_version": "v5_9_crypto_paper_certification_ingestion_v1",
        "record_type": "crypto_paper_certification_ingestion",
        "as_of": AS_OF,
        "certification_status": "certified_submit_cancel_no_fill",
        "prior_certification_id": "v58_btcusd_submit_cancel_abc123",
        "prior_client_order_id": CLIENT_ORDER_ID,
        "paper_submit_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "live_authorized": False,
        "blockers": [],
        "labels": [
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
    }


def _fill_exit_result() -> dict[str, object]:
    return copy.deepcopy(
        {
            "schema_version": "v5_10_crypto_paper_fill_exit_certification_v1",
            "as_of": AS_OF,
            "outcome_classification": "filled_exit_confirmed",
            "symbol": "BTCUSD",
            "approved_max_notional": "25",
            "entry_client_order_id": ENTRY_CLIENT_ORDER_ID,
            "exit_client_order_id": EXIT_CLIENT_ORDER_ID,
            "entry_attempt_count": 1,
            "exit_attempt_count": 1,
            "entry_final_status": "filled",
            "entry_filled_qty": "0.00038542",
            "entry_filled_avg_price": "63588.7",
            "position_after_entry": {
                "symbol": "BTCUSD",
                "qty": "0.000384456",
                "side": "long",
            },
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
    )


def _fill_exit_ingestion() -> dict[str, object]:
    return {
        "schema_version": "v5_11_crypto_paper_fill_exit_ingestion_v1",
        "record_type": "crypto_paper_fill_exit_ingestion",
        "as_of": AS_OF,
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


def _router_decision() -> dict[str, object]:
    return {
        "schema_version": "opportunity_router_fixture_v1",
        "as_of": AS_OF,
        "router_decision": "selected",
        "selected_candidate_id": SELECTED_CANDIDATE_ID,
        "selected_candidate": {
            "candidate_id": SELECTED_CANDIDATE_ID,
            "asset_class": "crypto",
            "symbol": "BTCUSD",
            "strategy_id": "crypto_vol_adjusted_momentum_24h_preview",
            "blockers": [],
        },
        "blockers": [],
    }


def _sizing_preview() -> dict[str, object]:
    return {
        "schema_version": "v5_4_crypto_qty_sizing_preview_v1",
        "as_of": AS_OF,
        "sizing_status": "preview_ready",
        "router_decision": "selected",
        "selected_candidate_id": SELECTED_CANDIDATE_ID,
        "asset_class": "crypto",
        "symbol": "BTCUSD",
        "rounded_qty": "0.000396783",
        "derived_preview_value": "24.999991017147",
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "blockers": [],
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }


def _handoff() -> dict[str, object]:
    return {
        "schema_version": "v5_5_crypto_paper_oms_handoff_v1",
        "as_of": AS_OF,
        "handoff_status": "approval_required",
        "approval_state": "not_authorized",
        "intended_action": "buy_preview",
        "asset_class": "crypto",
        "symbol": "BTCUSD",
        "strategy_id": "crypto_vol_adjusted_momentum_24h_preview",
        "selected_candidate_id": SELECTED_CANDIDATE_ID,
        "selected_backing": "real_local_artifact_backed",
        "rounded_qty": "0.000396783",
        "derived_preview_value": "24.999991017147",
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
        "blockers": [],
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }


def _dry_run() -> dict[str, object]:
    return {
        "schema_version": "v5_6_crypto_paper_oms_dry_run_v1",
        "as_of": AS_OF,
        "dry_run_status": "blocked_not_authorized",
        "approval_state": "not_authorized",
        "asset_class": "crypto",
        "symbol": "BTCUSD",
        "selected_candidate_id": SELECTED_CANDIDATE_ID,
        "selected_strategy": "crypto_vol_adjusted_momentum_24h_preview",
        "dry_run_id": "dryrun_123",
        "pre_broker_order_id": "prebroker_123",
        "idempotency_key": "crypto_paper_oms_dry_run:123",
        "rounded_qty": "0.000396783",
        "derived_preview_value": "24.999991017147",
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
        "blockers": [],
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"cadence_status\":\"operator_review_ready\"}\r\n"
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
        pytest.skip("PowerShell is required to verify run_crypto_paper_autonomy_cadence.ps1")
    return powershell


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
