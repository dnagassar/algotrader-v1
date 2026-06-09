from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_artifact_manifest_health import (
    EtfSmaDailyArtifactManifestHealthConfig,
    build_etf_sma_daily_artifact_manifest_health,
    run_etf_sma_daily_artifact_manifest_health,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_artifact_manifest_health.py")
EXPECTED_DATE = "2026-06-08"

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


def _write_valid_m447(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M447",
        "command": "etf-sma-offline-daily-cycle-rerun-m446",
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m448(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M448",
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m449(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M449",
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m450(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M450",
        "stages_run": ["M447", "M448", "M449"],
        "stages_validated": ["M447", "M448", "M449"],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m451_summary(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M451",
        "brief_state": "ready",
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m451_text(path: Path, warning: str = "preview_only_not_order_authorization") -> None:
    content = f"Some header info\n{warning}\nSome footer info\n"
    path.write_text(content, encoding="utf-8")


def _write_valid_m452(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M452",
        "acceptance_gate_state": "accepted_for_preview_only_observation",
        "accepted_for_operator_observation": True,
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
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
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "paper_action_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


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
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "paper_action_authorized": False,
        "profit_claim": "none",
        "blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_all_valid_fixtures(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "m447_jsonl": tmp_path / "m447.jsonl",
        "m448_jsonl": tmp_path / "m448.jsonl",
        "m449_jsonl": tmp_path / "m449.jsonl",
        "m450_jsonl": tmp_path / "m450.jsonl",
        "m451_summary_jsonl": tmp_path / "m451_summary.jsonl",
        "m451_txt": tmp_path / "m451.txt",
        "m452_jsonl": tmp_path / "m452.jsonl",
        "m453_jsonl": tmp_path / "m453.jsonl",
        "output_jsonl": tmp_path / "m454.jsonl",
    }
    _write_valid_m447(paths["m447_jsonl"])
    _write_valid_m448(paths["m448_jsonl"])
    _write_valid_m449(paths["m449_jsonl"])
    _write_valid_m450(paths["m450_jsonl"])
    _write_valid_m451_summary(paths["m451_summary_jsonl"])
    _write_valid_m451_text(paths["m451_txt"])
    _write_valid_m452(paths["m452_jsonl"])
    _write_valid_m453(paths["m453_jsonl"])
    return paths


def test_cli_registration(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-artifact-manifest-health",
            "--m447-jsonl",
            str(paths["m447_jsonl"]),
            "--m448-jsonl",
            str(paths["m448_jsonl"]),
            "--m449-jsonl",
            str(paths["m449_jsonl"]),
            "--m450-jsonl",
            str(paths["m450_jsonl"]),
            "--m451-summary-jsonl",
            str(paths["m451_summary_jsonl"]),
            "--m451-txt",
            str(paths["m451_txt"]),
            "--m452-jsonl",
            str(paths["m452_jsonl"]),
            "--m453-jsonl",
            str(paths["m453_jsonl"]),
            "--output-jsonl",
            str(paths["output_jsonl"]),
        ]
    )
    assert exit_code == 0
    printed = capsys.readouterr().out
    assert "ETF/SMA Daily Artifact Manifest Health Check (M454) - READY FOR OBSERVATION" in printed
    assert "Manifest Health State: ready" in printed


def test_cli_registration_json_format(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-artifact-manifest-health",
            "--m447-jsonl",
            str(paths["m447_jsonl"]),
            "--m448-jsonl",
            str(paths["m448_jsonl"]),
            "--m449-jsonl",
            str(paths["m449_jsonl"]),
            "--m450-jsonl",
            str(paths["m450_jsonl"]),
            "--m451-summary-jsonl",
            str(paths["m451_summary_jsonl"]),
            "--m451-txt",
            str(paths["m451_txt"]),
            "--m452-jsonl",
            str(paths["m452_jsonl"]),
            "--m453-jsonl",
            str(paths["m453_jsonl"]),
            "--output-jsonl",
            str(paths["output_jsonl"]),
            "--format",
            "json",
        ]
    )
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M454"
    assert printed["manifest_health_state"] == "ready"


def test_successful_health_check_ready(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)

    assert payload["milestone"] == "M454"
    assert payload["manifest_health_state"] == "ready"
    assert payload["accepted_for_operator_observation"] is True
    assert payload["blockers"] == []

    # Verify output JSONL content
    lines = paths["output_jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    json_rec = json.loads(lines[0])
    assert json_rec["milestone"] == "M454"
    assert json_rec["manifest_health_state"] == "ready"
    assert json_rec["accepted_for_operator_observation"] is True
    assert json_rec["indexed_milestones"] == ["M447", "M448", "M449", "M450", "M451", "M452", "M453"]

    # Verify hashes, byte sizes, paths, and record counts
    for milestone in ["M447", "M448", "M449", "M450", "M451", "M452", "M453"]:
        stats = json_rec["checked_artifacts"][milestone]
        assert "path" in stats
        assert "sha256" in stats
        assert len(stats["sha256"]) == 64
        assert stats["byte_size"] > 0
        assert stats["record_count"] == 1

    stats_txt = json_rec["checked_artifacts"]["M451_txt"]
    assert "path" in stats_txt
    assert len(stats_txt["sha256"]) == 64
    assert stats_txt["byte_size"] > 0
    assert "record_count" not in stats_txt


def test_missing_input_artifact_produces_blocked(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Remove one input file
    paths["m453_jsonl"].unlink()
    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)

    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert payload["accepted_for_operator_observation"] is False
    assert "m453_missing" in payload["blockers"]

    # Verify one JSONL line still written
    lines = paths["output_jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    json_rec = json.loads(lines[0])
    assert json_rec["manifest_health_state"] == "blocked_or_invalid"
    assert json_rec["accepted_for_operator_observation"] is False


def test_empty_jsonl_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Truncate m448
    paths["m448_jsonl"].write_text("", encoding="utf-8")
    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)

    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert "m448_empty" in payload["blockers"]


def test_malformed_jsonl_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["m449_jsonl"].write_text("{malformed\n", encoding="utf-8")
    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)

    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert "m449_malformed_json" in payload["blockers"]


def test_multi_record_jsonl_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    rec = json.dumps({"milestone": "M450"})
    paths["m450_jsonl"].write_text(f"{rec}\n{rec}\n", encoding="utf-8")

    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)
    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert "m450_record_count_not_one" in payload["blockers"]


def test_missing_m451_text_artifact_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["m451_txt"].unlink()

    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)
    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert "m451_txt_missing" in payload["blockers"]


def test_missing_warning_text_in_m451_txt_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m451_text(paths["m451_txt"], warning="NO WARNING HERE")

    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)
    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert "m451_txt_warning_missing" in payload["blockers"]


def test_m453_not_ready_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m453(paths["m453_jsonl"], daily_run_index_state="blocked")

    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)
    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert "m453_run_index_state_not_ready" in payload["blockers"]


def test_m452_not_accepted_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m452(
        paths["m452_jsonl"],
        acceptance_gate_state="blocked_or_invalid",
        accepted_for_operator_observation=False,
    )

    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)
    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert "m452_acceptance_gate_state_not_accepted" in payload["blockers"]


@pytest.mark.parametrize(
    "milestone_name, mock_writer, permission_key",
    [
        ("M452", _write_valid_m452, "paper_submit_allowed"),
        ("M452", _write_valid_m452, "live_submit_allowed"),
        ("M452", _write_valid_m452, "scheduler_install_allowed"),
        ("M453", _write_valid_m453, "paper_submit_allowed"),
        ("M453", _write_valid_m453, "live_submit_allowed"),
        ("M453", _write_valid_m453, "scheduler_install_allowed"),
    ],
)
def test_submit_allowed_blocks(tmp_path, milestone_name, mock_writer, permission_key) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    file_key = {
        "M452": "m452_jsonl",
        "M453": "m453_jsonl",
    }[milestone_name]

    mock_writer(paths[file_key], **{permission_key: True})
    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)
    assert payload["manifest_health_state"] == "blocked_or_invalid"


@pytest.mark.parametrize(
    "milestone_name, mock_writer, safety_flag",
    [
        ("M453", _write_valid_m453, "submitted"),
        ("M453", _write_valid_m453, "mutated"),
        ("M453", _write_valid_m453, "broker_action_performed"),
        ("M453", _write_valid_m453, "network_access_attempted"),
        ("M453", _write_valid_m453, "credential_access_attempted"),
        ("M453", _write_valid_m453, "live_authorized"),
        ("M453", _write_valid_m453, "os_scheduler_installed"),
        ("M453", _write_valid_m453, "scheduler_mutation_performed"),
    ],
)
def test_safety_and_scheduler_violations_block(
    tmp_path, milestone_name, mock_writer, safety_flag
) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    file_key = {
        "M453": "m453_jsonl",
    }[milestone_name]

    mock_writer(paths[file_key], **{safety_flag: True})
    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)
    assert payload["manifest_health_state"] == "blocked_or_invalid"


def test_date_inconsistency_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m453(paths["m453_jsonl"], expected_latest_bar_date="2026-06-09")

    config = EtfSmaDailyArtifactManifestHealthConfig(**paths)
    payload = run_etf_sma_daily_artifact_manifest_health(config)
    assert payload["manifest_health_state"] == "blocked_or_invalid"
    assert "mismatched_latest_bar_dates" in payload["blockers"]


def test_no_hardcoded_runtime_date_in_production() -> None:
    content = MODULE_PATH.read_text(encoding="utf-8")
    # Assert that the date string '2026-06-08' is NOT inside the production module
    assert (
        "2026-06-08" not in content
    ), "Production code must not contain a hardcoded runtime date check."


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
