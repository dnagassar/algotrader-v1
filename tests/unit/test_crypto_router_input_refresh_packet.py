from __future__ import annotations

import ast
import csv
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

import algotrader.orchestration.crypto_router_input_refresh_packet as packet_module
from algotrader.orchestration.crypto_router_input_refresh_packet import (
    FINAL_STATES,
    NEXT_OPERATOR_ACTIONS,
    REQUIRED_LABELS,
    SCHEMA_VERSION,
    run_crypto_router_input_refresh_packet,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "src" / "algotrader" / "orchestration" / (
    "crypto_router_input_refresh_packet.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_crypto_router_input_refresh_packet.ps1"
DEPENDENCY_GUARD_PATH = PROJECT_ROOT / "tests" / "unit" / "test_dependency_direction.py"
AS_OF = datetime(2026, 7, 4, 0, 30, tzinfo=UTC)
CLIENT_ORDER_ID = "v58-btcusd-paper-cert-bfa9caadd6b57b19"
ENTRY_CLIENT_ORDER_ID = "v510-btcusd-entry-31147aa0135b0e92"
EXIT_CLIENT_ORDER_ID = "v510-btcusd-exit-a32677e4399a7c86"
SENSITIVE_KEY = "SENTINEL_ALPACA_SECRET_DO_NOT_PRINT"


def test_inventory_detects_valid_local_crypto_router_inputs(tmp_path: Path) -> None:
    paths = _write_packet_inputs(tmp_path)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        write_artifacts=True,
    )

    components = _components(packet)
    actions = packet["refresh_actions"]["actions"]

    assert packet["schema_version"] == SCHEMA_VERSION
    assert packet["final_state"] == "local_replay_cycle_rerun_complete"
    assert packet["input_basis"] == "local_replay"
    assert packet["router_input_blocker_removed"] is True
    assert packet["router_input_blocker_count"] == 0
    assert components["crypto_universe_metadata"]["classification"] == "present_valid"
    assert components["symbol_orderability_metadata"]["classification"] == "present_valid"
    assert components["history_or_feature_data"]["classification"] == "present_valid"
    assert any(
        action["action"] == "generate_local_replay_refresh_packet"
        and action["performed"] is True
        for action in actions
    )
    assert packet["cycle_rerun_status"]["cycle_final_state"] == (
        "selected_candidate_no_submit_packet_ready"
    )


def test_inventory_detects_missing_router_inputs_and_blocks(
    tmp_path: Path,
) -> None:
    paths = _packet_paths(tmp_path)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        write_artifacts=True,
    )

    components = _components(packet)

    assert packet["final_state"] == "blocked_missing_local_inputs"
    assert packet["final_state"] != "router_inputs_ready_cycle_rerun_complete"
    assert packet["router_input_blocker_removed"] is False
    assert packet["router_input_blocker_count"] > 0
    assert packet["next_operator_action"]["action"] == (
        "provide_or_authorize_market_data_refresh"
    )
    assert components["history_or_feature_data"]["classification"] == "missing"
    assert components["candidate_generation_inputs"]["classification"] == "missing"
    assert packet["cycle_rerun_status"]["cycle_final_state"] == "blocked_missing_router_inputs"


def test_stale_local_inputs_emit_blocked_stale_local_inputs(tmp_path: Path) -> None:
    paths = _write_packet_inputs(tmp_path, bars_latest=AS_OF - timedelta(days=2))

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        write_artifacts=True,
    )

    history = _components(packet)["history_or_feature_data"]

    assert packet["final_state"] == "blocked_stale_local_inputs"
    assert packet["final_state"] != "router_inputs_ready_cycle_rerun_complete"
    assert packet["router_input_blocker_removed"] is False
    assert packet["router_input_blocker_count"] > 0
    assert history["classification"] == "present_stale"
    assert "stale_data" in history["blockers"]
    assert packet["next_operator_action"]["action"] == (
        "provide_or_authorize_market_data_refresh"
    )


def test_invalid_schema_emit_blocked_invalid_schema(tmp_path: Path) -> None:
    paths = _write_packet_inputs(tmp_path)
    Path(paths["crypto_visibility_status"]).write_text("{not-json", encoding="utf-8")

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=True,
        write_artifacts=True,
    )

    assert packet["final_state"] == "blocked_invalid_schema"
    assert packet["next_operator_action"]["action"] == "repair_local_input_schema"
    assert _components(packet)["symbol_orderability_metadata"]["classification"] == (
        "invalid_schema"
    )


def test_broker_read_required_path_does_not_read_broker(tmp_path: Path) -> None:
    paths = _write_packet_inputs(
        tmp_path,
        visibility_payload={
            "schema_version": "test_crypto_visibility_status",
            "as_of": AS_OF.isoformat(),
            "broker_state_mode": "broker_state_not_observed",
            "eligible_crypto_symbols": ["BTC/USD"],
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "live_mutation_performed": False,
        },
    )

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        request_paper_read_repair=True,
        write_artifacts=True,
    )

    orderability = _components(packet)["symbol_orderability_metadata"]

    assert packet["final_state"] == "blocked_requires_broker_read_authorization"
    assert orderability["classification"] == "not_refreshable_without_authorization"
    assert orderability["authorization_required"] == "broker_read"
    assert packet["broker_read_occurred"] is False
    assert packet["next_operator_action"]["action"] == "authorize_scoped_paper_read"
    request = str(packet["next_operator_action"]["operator_request"]).lower()
    for mutation_verb in ("submit", "cancel", "replace", "close", "liquidate", "retry"):
        assert mutation_verb not in request


def test_market_data_required_path_does_not_use_network(tmp_path: Path) -> None:
    paths = _write_packet_inputs(tmp_path, write_bars=False)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        request_market_data_refresh=True,
        write_artifacts=True,
    )

    history = _components(packet)["history_or_feature_data"]

    assert packet["final_state"] == "blocked_requires_market_data_authorization"
    assert history["classification"] == "not_refreshable_without_authorization"
    assert history["authorization_required"] == "market_data"
    assert packet["network_access_attempted"] is False
    assert packet["next_operator_action"]["action"] == (
        "provide_or_authorize_market_data_refresh"
    )


def test_fixture_repair_produces_refreshed_deterministic_artifacts(
    tmp_path: Path,
) -> None:
    paths = _packet_paths(tmp_path)
    _write_lifecycle_inputs(paths)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=True,
        write_artifacts=True,
    )
    actions = packet["refresh_actions"]["actions"]
    refresh_root = Path(paths["crypto_refresh_output_root"])

    assert packet["final_state"] == "fixture_backed_cycle_rerun_complete"
    assert packet["input_basis"] == "offline_fixture"
    assert packet["next_operator_action"]["action"] == (
        "review_fixture_backed_no_submit_packet"
    )
    assert packet["router_input_blocker_removed"] is True
    assert packet["router_input_blocker_count"] == 0
    assert any(
        action["action"] == "generate_fixture_backed_refresh_packet"
        and action["performed"] is True
        and action["fixture_backed"] is True
        for action in actions
    )
    assert (refresh_root / "crypto_router_input_manifest.json").is_file()
    assert (refresh_root / "history" / "BTCUSD.csv").is_file()
    manifest = json.loads(
        (refresh_root / "crypto_router_input_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["source_mode"] == "offline_fixture"
    assert manifest["router_ready_symbols"] == ["BTCUSD"]


def test_cycle_rerun_integration_invokes_no_submit_cycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_packet_inputs(tmp_path)
    captured: dict[str, object] = {}

    def fake_cycle(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "cycle_status": {
                "final_state": "selected_candidate_no_submit_packet_ready",
                "next_operator_action": "review_no_submit_packet",
                "blockers": [],
            },
            "artifact_paths": {},
        }

    monkeypatch.setattr(packet_module, "run_crypto_no_submit_operating_cycle", fake_cycle)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        write_artifacts=True,
    )

    assert packet["final_state"] == "router_inputs_partially_repaired_cycle_blocked"
    assert packet["router_input_blocker_removed"] is False
    assert packet["router_input_blocker_count"] > 0
    assert captured["refresh_mode"] == "local_replay"
    assert captured["write_artifacts"] is True
    assert captured["allow_fixture_backed"] is False
    assert captured["as_of"] == AS_OF


def test_cycle_rerun_threads_local_observed_artifact_to_no_submit_cycle(
    tmp_path: Path,
) -> None:
    paths = _write_packet_inputs(tmp_path)
    freshness_evaluated_at = AS_OF + timedelta(minutes=30)
    artifact_path = tmp_path / "runs" / "observed" / "broker_observed_readiness_packet.json"
    _write_json(artifact_path, _observed_latest_price_artifact())

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        observed_latest_price_artifact_path=artifact_path,
        freshness_evaluation_mode="wall_clock",
        freshness_evaluated_at=freshness_evaluated_at,
        allow_fixture_repair=False,
        write_artifacts=True,
    )
    cycle_status = packet["cycle_rerun_status"]

    assert cycle_status["crypto_readiness_decision"] == (
        "local_observed_artifact_ready_no_submit"
    )
    assert cycle_status["crypto_readiness_evidence_classification"] == (
        "local_observed_artifact_replay"
    )
    assert cycle_status["latest_price_source"] == "local_observed_artifact_latest_quote"
    assert cycle_status["latest_price_observed_at"] == AS_OF.isoformat()
    assert cycle_status["latest_price_age_seconds"] == "1800"
    assert cycle_status["latest_price_freshness_threshold_seconds"] == "7200"
    assert cycle_status["latest_price_freshness_status"] == "fresh"
    assert cycle_status["freshness_evaluated_at"] == freshness_evaluated_at.isoformat()
    assert cycle_status["freshness_evaluation_mode"] == "wall_clock"
    assert (
        cycle_status["latest_price_age_basis"]
        == "freshness_evaluated_at_minus_observed_at_wall_clock"
    )
    assert cycle_status["operational_freshness_confirmed"] is True
    assert cycle_status["observed_latest_price_artifact"]["status"] == "accepted"
    assert cycle_status["broker_read_occurred"] is False
    assert cycle_status["broker_mutation_occurred"] is False
    assert cycle_status["paper_submit_occurred"] is False


def test_no_submit_no_broker_no_live_flags_remain_false(tmp_path: Path) -> None:
    paths = _write_packet_inputs(tmp_path)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        write_artifacts=True,
    )
    payloads = [
        packet,
        packet["input_readiness"],
        packet["next_operator_action"],
        json.loads(Path(packet["artifact_paths"]["manifest"]).read_text("utf-8")),
        json.loads(Path(packet["artifact_paths"]["operating_record"]).read_text("utf-8")),
    ]

    for payload in payloads:
        for field_name in packet_module.FALSE_SAFETY_FIELDS:
            assert payload[field_name] is False
        assert payload["profit_claim"] == "none"
        assert set(REQUIRED_LABELS) <= set(payload["labels"])


@pytest.mark.parametrize(
    "cycle_final_state",
    (
        "blocked_missing_dry_run",
        "blocked_missing_sizing_preview",
        "blocked_missing_handoff",
        "blocked_missing_lifecycle_evidence",
    ),
)
def test_blocked_inner_cycle_states_do_not_produce_ready_final_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cycle_final_state: str,
) -> None:
    paths = _write_packet_inputs(tmp_path)
    blocker = f"{cycle_final_state}_blocker"

    def fake_cycle(**kwargs: object) -> dict[str, object]:
        return {
            "cycle_status": {
                "final_state": cycle_final_state,
                "next_operator_action": "blocked",
                "blockers": [blocker],
            },
            "artifact_paths": {},
        }

    monkeypatch.setattr(packet_module, "run_crypto_no_submit_operating_cycle", fake_cycle)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        write_artifacts=True,
    )

    assert packet["final_state"] == "router_inputs_partially_repaired_cycle_blocked"
    assert packet["final_state"] != "router_inputs_ready_cycle_rerun_complete"
    assert packet["router_input_blocker_removed"] is False
    assert packet["router_input_blocker_count"] > 0
    assert packet["next_operator_action"]["action"] == (
        "rerun_crypto_no_submit_operating_cycle"
    )
    assert any(
        record["component"] == "cycle_rerun" and record["blocker"] == blocker
        for record in packet["router_input_blockers_remaining"]
    )


def test_emitted_artifacts_do_not_contain_credential_sentinel_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_packet_inputs(tmp_path)
    sentinels = {
        "ALPACA_API_KEY": SENSITIVE_KEY,
        "ALPACA_API_SECRET_KEY": f"{SENSITIVE_KEY}_SECRET",
        "ALPACA_SECRET_KEY": f"{SENSITIVE_KEY}_LEGACY",
        "APCA_API_KEY_ID": f"{SENSITIVE_KEY}_APCA_ID",
        "APCA_API_SECRET_KEY": f"{SENSITIVE_KEY}_APCA_SECRET",
    }
    for name, value in sentinels.items():
        monkeypatch.setenv(name, value)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        write_artifacts=True,
    )
    output_root = Path(paths["output_root"])
    emitted_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    )

    assert packet["credential_values_exposed"] is False
    for value in sentinels.values():
        assert value not in emitted_text


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    paths = _write_packet_inputs(tmp_path)

    packet = run_crypto_router_input_refresh_packet(
        **paths,
        allow_fixture_repair=False,
        write_artifacts=True,
    )
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


def test_dependency_direction_guard_includes_refresh_packet_module() -> None:
    guard = DEPENDENCY_GUARD_PATH.read_text(encoding="utf-8")

    assert "algotrader.orchestration.crypto_router_input_refresh_packet" in guard


def test_decision_and_next_action_enums_are_exact() -> None:
    assert FINAL_STATES == (
        "router_inputs_ready_cycle_rerun_complete",
        "local_replay_cycle_rerun_complete",
        "fixture_backed_cycle_rerun_complete",
        "router_inputs_partially_repaired_cycle_blocked",
        "blocked_missing_local_inputs",
        "blocked_stale_local_inputs",
        "blocked_invalid_schema",
        "blocked_requires_broker_read_authorization",
        "blocked_requires_market_data_authorization",
        "blocked_requires_paid_or_new_service",
        "blocked",
    )
    assert NEXT_OPERATOR_ACTIONS == (
        "review_no_submit_packet",
        "review_local_replay_no_submit_packet",
        "review_fixture_backed_no_submit_packet",
        "rerun_crypto_no_submit_operating_cycle",
        "provide_or_authorize_market_data_refresh",
        "authorize_scoped_paper_read",
        "repair_local_input_schema",
        "blocked",
    )


def test_refresh_packet_has_no_broker_network_or_mutation_imports() -> None:
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


def test_script_contract_is_no_submit_offline_and_invokes_module() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the v5.14 crypto router input refresh packet",
        '[string]$OutputRoot = "runs\\crypto_router_input_refresh_packet\\latest"',
        '[bool]$AllowFixtureRepair = $true',
        "crypto_router_input_refresh_packet_mode=offline/no_submit",
        "crypto_router_input_refresh_packet_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_credential_variables_loaded",
        "preflight_network_flags_loaded",
        "preflight_live_endpoint_indicator",
        "crypto_router_input_refresh_packet_broker_read_occurred=false",
        "crypto_router_input_refresh_packet_paper_submit_authorized=false",
        "crypto_router_input_refresh_packet_paper_submit_occurred=false",
        "crypto_router_input_refresh_packet_broker_mutation_occurred=false",
        "crypto_router_input_refresh_packet_live_endpoint_touched=false",
        "fresh_authorization_required_for_order=true",
        "algotrader.orchestration.crypto_router_input_refresh_packet",
        "--request-paper-read-repair",
        "--request-market-data-refresh",
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
    assert "crypto_router_input_refresh_packet_status=blocked_unsafe_environment" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def _packet_paths(tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "runs"
    return {
        "output_root": root / "crypto_router_input_refresh_packet" / "latest",
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
        "as_of": AS_OF,
    }


def _write_packet_inputs(
    tmp_path: Path,
    *,
    bars_latest: datetime = AS_OF,
    write_bars: bool = True,
    visibility_payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    paths = _packet_paths(tmp_path)
    if write_bars:
        _write_crypto_bars(Path(paths["bars_csv"]), latest=bars_latest)
    _write_json(
        Path(paths["crypto_visibility_status"]),
        visibility_payload or _crypto_visibility_status(),
    )
    _write_lifecycle_inputs(paths)
    return paths


def _write_lifecycle_inputs(paths: Mapping[str, object]) -> None:
    _write_json(Path(paths["submit_cancel_result_path"]), _submit_cancel_result())
    _write_json(Path(paths["certification_ingestion_path"]), _certification_ingestion())
    _write_json(Path(paths["fill_exit_result_path"]), _fill_exit_result())
    _write_json(Path(paths["fill_exit_ingestion_path"]), _fill_exit_ingestion())


def _components(packet: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    inventory = packet["input_inventory"]
    return {
        str(component["component"]): component
        for component in inventory["components"]
        if isinstance(component, Mapping)
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


def _observed_latest_price_artifact() -> dict[str, object]:
    observed_text = AS_OF.isoformat()
    return {
        "schema_version": "test_broker_observed_readiness_packet",
        "record_type": "broker_observed_readiness_packet",
        "run_id": "test_observed_run",
        "as_of": observed_text,
        "symbol": "BTCUSD",
        "selected_symbol": "BTCUSD",
        "broker_observed_readiness_decision": "broker_observed_ready_preview",
        "blocker_code": "",
        "broker_read_authorized": True,
        "broker_read_attempted": True,
        "broker_read_occurred": True,
        "broker_read_blocked": False,
        "broker_state_observed": True,
        "network_used": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "latest_price_value": "125",
        "latest_price_source": "broker_observed",
        "latest_price_source_selected": "quote",
        "latest_price_basis": "broker_observed_latest_quote_mid",
        "latest_price_final_selected_basis": "broker_observed_latest_quote_mid",
        "latest_price_observed_at": observed_text,
        "latest_price_normalized_timestamp": observed_text,
        "latest_price_age_seconds": "0",
        "latest_price_freshness_status": "fresh",
        "latest_price_freshness_threshold_seconds": "7200",
        "latest_price_final_blocker": "",
        "latest_price_source_acceptability": "accepted_broker_observed",
        "price_evidence_status": "passed",
        "price_evidence_blocker": "",
        "broker_observed_price_freshness_check": {
            "latest_price_value": "125",
            "latest_price_source": "broker_observed",
            "latest_price_source_selected": "quote",
            "latest_price_basis": "broker_observed_latest_quote_mid",
            "latest_price_final_selected_basis": "broker_observed_latest_quote_mid",
            "latest_price_observed_at": observed_text,
            "latest_price_normalized_timestamp": observed_text,
            "latest_price_age_seconds": "0",
            "latest_price_freshness_status": "fresh",
            "latest_price_freshness_threshold_seconds": "7200",
            "latest_price_final_blocker": "",
            "latest_price_fallback_source_result": "not_needed",
            "price_evidence_status": "passed",
            "price_evidence_blocker": "",
            "latest_price_source_table": [
                {
                    "source": "quote",
                    "method_name": "get_latest_quote",
                    "attempted": True,
                    "value": "125",
                    "observed_at": observed_text,
                    "age_seconds": "0",
                    "freshness": "fresh",
                    "status": "passed",
                    "blocker": "",
                    "basis": "broker_observed_latest_quote_mid",
                    "raw_timestamp_field_names_present": "timestamp",
                }
            ],
        },
    }


def _write_crypto_bars(path: Path, *, latest: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    first = latest - timedelta(hours=79)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ("timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume")
        )
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
        "echo {\"final_state\":\"router_inputs_ready_cycle_rerun_complete\"}\r\n"
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
        pytest.skip("PowerShell is required to verify run_crypto_router_input_refresh_packet.ps1")
    return powershell
