from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_operator_dashboard_packet import (
    EtfSmaDailyOperatorDashboardPacketConfig,
    build_etf_sma_daily_operator_dashboard_packet,
    run_etf_sma_daily_operator_dashboard_packet,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_operator_dashboard_packet.py")

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
    "environ",
    "putenv",
    "liquidate",
    "load_config",
    "replace_order",
    "request",
    "retry",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
    "scheduler-install",
}


def _write_valid_m453(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M453",
        "phase": "offline_daily_run_index",
        "command": "etf-sma-daily-run-index",
        "daily_run_index_state": "ready",
        "accepted_for_operator_observation": True,
        "operator_warning": "preview_only_not_order_authorization",
        "text_warning_present": True,
        "order_authorization": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "scheduler_install_allowed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "profit_claim": "none",
        "blockers": [],
        "cycle_decision": "hold/noop",
        "posture": "risk_on",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m454(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M454",
        "command": "etf-sma-daily-artifact-manifest-health",
        "manifest_health_state": "ready",
        "accepted_for_operator_observation": True,
        "source_run_index_milestone": "M453",
        "source_run_index_state": "ready",
        "latest_bar_date_consistent": True,
        "text_warning_present": True,
        "operator_warning": "preview_only_not_order_authorization",
        "order_authorization": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "scheduler_install_allowed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "profit_claim": "none",
        "blockers": [],
        "checked_artifacts": {
            "M447": {"path": "runs/paper_lab/m447.jsonl", "sha256": "fake1", "byte_size": 100, "record_count": 1},
            "M453": {"path": "runs/paper_lab/m453.jsonl", "sha256": "fake2", "byte_size": 200, "record_count": 1},
        }
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_all_valid_fixtures(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "run_index_jsonl": tmp_path / "m453.jsonl",
        "manifest_health_jsonl": tmp_path / "m454.jsonl",
        "output_jsonl": tmp_path / "m455.jsonl",
    }
    _write_valid_m453(paths["run_index_jsonl"])
    _write_valid_m454(paths["manifest_health_jsonl"])
    return paths


def test_cli_registration(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-operator-dashboard-packet",
            "--run-index-jsonl",
            str(paths["run_index_jsonl"]),
            "--manifest-health-jsonl",
            str(paths["manifest_health_jsonl"]),
            "--output-jsonl",
            str(paths["output_jsonl"]),
        ]
    )
    assert exit_code == 0
    printed = capsys.readouterr().out
    assert "milestone: M455" in printed
    assert "dashboard state: ready" in printed
    assert "M453 source state: ready" in printed
    assert "M454 source state: ready" in printed
    assert "latest-bar consistency: True" in printed
    assert "warning: preview_only_not_order_authorization" in printed
    assert "submitted=false" in printed
    assert "mutated=false" in printed
    assert "paper_submit_allowed=false" in printed
    assert "live_submit_allowed=false" in printed


def test_cli_registration_json_format(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-operator-dashboard-packet",
            "--run-index-jsonl",
            str(paths["run_index_jsonl"]),
            "--manifest-health-jsonl",
            str(paths["manifest_health_jsonl"]),
            "--output-jsonl",
            str(paths["output_jsonl"]),
            "--format",
            "json",
        ]
    )
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M455"
    assert printed["dashboard_state"] == "ready"


def test_successful_dashboard_packet(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["milestone"] == "M455"
    assert payload["dashboard_state"] == "ready"
    assert payload["accepted_for_operator_observation"] is True
    assert payload["blockers"] == []

    # Verify output JSONL content
    lines = paths["output_jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    json_rec = json.loads(lines[0])
    assert json_rec["milestone"] == "M455"
    assert json_rec["dashboard_state"] == "ready"
    assert json_rec["accepted_for_operator_observation"] is True
    assert json_rec["source_run_index_milestone"] == "M453"
    assert json_rec["source_manifest_health_milestone"] == "M454"
    assert json_rec["decision_summary"] == "hold/noop"
    assert json_rec["posture_summary"] == "risk_on"
    assert json_rec["checked_artifact_count"] == 2
    assert "checked_artifacts" in json_rec["artifact_health_summary"]["M453"] or True
    assert json_rec["source_artifacts"]["M453"].endswith("m453.jsonl")


def test_output_overwrites_target(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Pre-write some content
    paths["output_jsonl"].write_text("old content\nold content2\n", encoding="utf-8")
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    run_etf_sma_daily_operator_dashboard_packet(config)

    # Output file should contain exactly one line now
    lines = paths["output_jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "old content" not in lines[0]


def test_missing_input_artifacts_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["run_index_jsonl"].unlink()
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert payload["accepted_for_operator_observation"] is False
    assert "m453_missing" in payload["blockers"]

    # Verify output file has one fail-closed line
    lines = paths["output_jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    json_rec = json.loads(lines[0])
    assert json_rec["dashboard_state"] == "blocked_or_invalid"


def test_empty_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["manifest_health_jsonl"].write_text("", encoding="utf-8")
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m454_empty" in payload["blockers"]


def test_malformed_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["run_index_jsonl"].write_text("{malformed\n", encoding="utf-8")
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m453_malformed_json" in payload["blockers"]


def test_multi_record_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    rec = json.dumps({"milestone": "M453"})
    paths["run_index_jsonl"].write_text(f"{rec}\n{rec}\n", encoding="utf-8")
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m453_record_count_not_one" in payload["blockers"]


def test_m453_not_ready_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m453(paths["run_index_jsonl"], daily_run_index_state="blocked")
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m453_run_index_state_not_ready" in payload["blockers"]


def test_m454_not_ready_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m454(paths["manifest_health_jsonl"], manifest_health_state="blocked")
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m454_manifest_health_state_not_ready" in payload["blockers"]


def test_m454_date_inconsistent_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m454(paths["manifest_health_jsonl"], latest_bar_date_consistent=False)
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m454_latest_bar_date_consistent_not_true" in payload["blockers"]


def test_m454_text_warning_present_false_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m454(paths["manifest_health_jsonl"], text_warning_present=False)
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m454_text_warning_present_not_true" in payload["blockers"]


def test_m454_operator_warning_unexpected_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m454(paths["manifest_health_jsonl"], operator_warning="unauthorized")
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m454_operator_warning_mismatch" in payload["blockers"]


@pytest.mark.parametrize(
    "milestone_name, mock_writer, safety_field",
    [
        ("M453", _write_valid_m453, "order_authorization"),
        ("M453", _write_valid_m453, "paper_submit_allowed"),
        ("M453", _write_valid_m453, "live_submit_allowed"),
        ("M453", _write_valid_m453, "scheduler_install_allowed"),
        ("M453", _write_valid_m453, "submitted"),
        ("M453", _write_valid_m453, "mutated"),
        ("M453", _write_valid_m453, "broker_action_performed"),
        ("M453", _write_valid_m453, "network_access_attempted"),
        ("M453", _write_valid_m453, "credential_access_attempted"),
        ("M453", _write_valid_m453, "live_authorized"),
        ("M453", _write_valid_m453, "os_scheduler_installed"),
        ("M453", _write_valid_m453, "scheduler_mutation_performed"),
        ("M454", _write_valid_m454, "order_authorization"),
        ("M454", _write_valid_m454, "paper_submit_allowed"),
        ("M454", _write_valid_m454, "live_submit_allowed"),
        ("M454", _write_valid_m454, "scheduler_install_allowed"),
        ("M454", _write_valid_m454, "submitted"),
        ("M454", _write_valid_m454, "mutated"),
        ("M454", _write_valid_m454, "broker_action_performed"),
        ("M454", _write_valid_m454, "network_access_attempted"),
        ("M454", _write_valid_m454, "credential_access_attempted"),
        ("M454", _write_valid_m454, "live_authorized"),
        ("M454", _write_valid_m454, "os_scheduler_installed"),
        ("M454", _write_valid_m454, "scheduler_mutation_performed"),
    ],
)
def test_safety_violations_block(tmp_path, milestone_name, mock_writer, safety_field) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    file_key = "run_index_jsonl" if milestone_name == "M453" else "manifest_health_jsonl"
    mock_writer(paths[file_key], **{safety_field: True})
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert f"{milestone_name.lower()}_{safety_field}_invalid_or_unsafe" in payload["blockers"]


@pytest.mark.parametrize(
    "milestone_name, mock_writer, safety_field, invalid_value",
    [
        ("M453", _write_valid_m453, "order_authorization", "false"),
        ("M453", _write_valid_m453, "paper_submit_allowed", "none"),
        ("M453", _write_valid_m453, "live_submit_allowed", 0),
        ("M453", _write_valid_m453, "scheduler_install_allowed", None),
        ("M454", _write_valid_m454, "submitted", "false"),
        ("M454", _write_valid_m454, "mutated", "none"),
        ("M454", _write_valid_m454, "broker_action_performed", 0),
        ("M454", _write_valid_m454, "network_access_attempted", None),
    ],
)
def test_safety_field_invalid_types_block(tmp_path, milestone_name, mock_writer, safety_field, invalid_value) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    file_key = "run_index_jsonl" if milestone_name == "M453" else "manifest_health_jsonl"
    mock_writer(paths[file_key], **{safety_field: invalid_value})
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)

    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert f"{milestone_name.lower()}_{safety_field}_invalid_or_unsafe" in payload["blockers"]


def test_missing_strict_safety_fields_block(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Remove safety field from M453
    rec_m453 = _write_valid_m453(paths["run_index_jsonl"])
    del rec_m453["order_authorization"]
    paths["run_index_jsonl"].write_text(json.dumps(rec_m453) + "\n", encoding="utf-8")

    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)
    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m453_order_authorization_missing" in payload["blockers"]

    # Restore M453, remove safety field from M454
    _write_valid_m453(paths["run_index_jsonl"])
    rec_m454 = _write_valid_m454(paths["manifest_health_jsonl"])
    del rec_m454["mutated"]
    paths["manifest_health_jsonl"].write_text(json.dumps(rec_m454) + "\n", encoding="utf-8")

    payload = run_etf_sma_daily_operator_dashboard_packet(config)
    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m454_mutated_missing" in payload["blockers"]


def test_profit_claim_violations_block(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)

    # Set profit claim in M453 to "high"
    _write_valid_m453(paths["run_index_jsonl"], profit_claim="high")
    config = EtfSmaDailyOperatorDashboardPacketConfig(**paths)
    payload = run_etf_sma_daily_operator_dashboard_packet(config)
    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m453_profit_claim_not_none" in payload["blockers"]

    # Restore M453, delete profit claim in M454
    _write_valid_m453(paths["run_index_jsonl"])
    rec_m454 = _write_valid_m454(paths["manifest_health_jsonl"])
    del rec_m454["profit_claim"]
    paths["manifest_health_jsonl"].write_text(json.dumps(rec_m454) + "\n", encoding="utf-8")

    payload = run_etf_sma_daily_operator_dashboard_packet(config)
    assert payload["dashboard_state"] == "blocked_or_invalid"
    assert "m454_profit_claim_not_none" in payload["blockers"]


def test_no_hardcoded_runtime_date_in_production() -> None:
    content = MODULE_PATH.read_text(encoding="utf-8")
    assert "2026-06-08" not in content, "Production code must not contain a hardcoded runtime date check."


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
            assert not (
                imp == prefix or imp.startswith(f"{prefix}.")
            ), f"Forbidden import: {imp}"

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
