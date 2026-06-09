from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_run_index import (
    EtfSmaDailyRunIndexConfig,
    build_etf_sma_daily_run_index,
    run_etf_sma_daily_run_index,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_run_index.py")
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

_WARNING_TEXT = "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders."


def _write_valid_m447(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M447",
        "command": "etf-sma-offline-daily-cycle-rerun-m446",
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "recommended_operator_action": "observe_hold_noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "source_m446_canonical_csv_sha256": "408fd46ef351442cbcb72067e7c7874d92981554fe560b68e3da98492b77db69",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m448(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M448",
        "record_type": "m448_refreshed_current_cycle_rollup",
        "command": "etf-sma-refreshed-current-cycle-rollup-m448",
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "paper_action_authorized": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m449(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M449",
        "phase": "offline_preview_only_daily_operating_brief_automation_packet",
        "command": "etf-sma-daily-preview-run",
        "daily_preview_run_state": "preview_only_daily_run_ready",
        "operating_brief_state": "ready",
        "schedule_contract_state": "local_preview_contract_ready",
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "source_posture": "risk_on",
        "source_cycle_decision": "hold/noop",
        "source_current_action": "observe_hold_noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "profit_claim": "none",
        "blockers": [],
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m450(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M450",
        "phase": "one_command_offline_daily_preview_pipeline",
        "command": "etf-sma-daily-preview-pipeline",
        "pipeline_state": "preview_pipeline_ready",
        "stages_run": ["M447", "M448", "M449"],
        "stages_validated": ["M447", "M448", "M449"],
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "profit_claim": "none",
        "blockers": [],
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m451_summary(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M451",
        "phase": "offline_daily_operator_brief_renderer",
        "command": "etf-sma-daily-operator-brief",
        "brief_state": "ready",
        "source_milestone": "M450",
        "source_pipeline_state": "preview_pipeline_ready",
        "source_stages_run": ["M447", "M448", "M449"],
        "source_stages_validated": ["M447", "M448", "M449"],
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "operator_warning": "preview_only_not_order_authorization",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "profit_claim": "none",
        "blockers": [],
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m451_text(path: Path, warning: str = _WARNING_TEXT) -> None:
    content = f"Some header info\n{warning}\nSome footer info\n"
    path.write_text(content, encoding="utf-8")


def _write_valid_m452(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M452",
        "phase": "offline_daily_acceptance_gate",
        "command": "etf-sma-daily-acceptance-gate",
        "acceptance_gate_state": "accepted_for_preview_only_observation",
        "accepted_for_operator_observation": True,
        "order_authorization": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "scheduler_install_allowed": False,
        "source_pipeline_milestone": "M450",
        "source_operator_brief_milestone": "M451",
        "source_pipeline_state": "preview_pipeline_ready",
        "source_brief_state": "ready",
        "source_stages_run": ["M447", "M448", "M449"],
        "source_stages_validated": ["M447", "M448", "M449"],
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "operator_warning": "preview_only_not_order_authorization",
        "text_warning_present": True,
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
        "output_jsonl": tmp_path / "m453.jsonl",
    }
    _write_valid_m447(paths["m447_jsonl"])
    _write_valid_m448(paths["m448_jsonl"])
    _write_valid_m449(paths["m449_jsonl"])
    _write_valid_m450(paths["m450_jsonl"])
    _write_valid_m451_summary(paths["m451_summary_jsonl"])
    _write_valid_m451_text(paths["m451_txt"])
    _write_valid_m452(paths["m452_jsonl"])
    return paths


def test_cli_registration(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-run-index",
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
            "--output-jsonl",
            str(paths["output_jsonl"]),
        ]
    )
    assert exit_code == 0
    printed = capsys.readouterr().out
    assert "ETF/SMA Daily Run Index (M453) - READY FOR OBSERVATION" in printed
    assert "Daily Run Index State: ready" in printed


def test_cli_registration_json_format(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-run-index",
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
            "--output-jsonl",
            str(paths["output_jsonl"]),
            "--format",
            "json",
        ]
    )
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M453"
    assert printed["daily_run_index_state"] == "ready"


def test_successful_run_index_ready(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)

    assert payload["milestone"] == "M453"
    assert payload["daily_run_index_state"] == "ready"
    assert payload["accepted_for_operator_observation"] is True
    assert payload["expected_latest_bar_date"] == EXPECTED_DATE
    assert payload["latest_local_bar_date"] == EXPECTED_DATE
    assert payload["blockers"] == []

    # Verify output JSONL content
    lines = paths["output_jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    json_rec = json.loads(lines[0])
    assert json_rec["milestone"] == "M453"
    assert json_rec["daily_run_index_state"] == "ready"
    assert json_rec["accepted_for_operator_observation"] is True
    assert json_rec["expected_latest_bar_date"] == EXPECTED_DATE
    assert json_rec["latest_local_bar_date"] == EXPECTED_DATE
    assert json_rec["indexed_milestones"] == ["M447", "M448", "M449", "M450", "M451", "M452"]
    
    # Check indexed_artifacts normalizations
    assert "M447" in json_rec["indexed_artifacts"]
    assert "M452" in json_rec["indexed_artifacts"]


def test_missing_input_artifact_produces_blocked(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Remove one input file
    paths["m452_jsonl"].unlink()
    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)

    assert payload["daily_run_index_state"] == "blocked_or_invalid"
    assert payload["accepted_for_operator_observation"] is False
    assert "m452_missing" in payload["blockers"]

    # Verify one JSONL line still written
    lines = paths["output_jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    json_rec = json.loads(lines[0])
    assert json_rec["daily_run_index_state"] == "blocked_or_invalid"
    assert json_rec["accepted_for_operator_observation"] is False


def test_multi_record_jsonl_input_produces_blocked(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Write two records inside m450
    rec = json.dumps({"milestone": "M450"})
    paths["m450_jsonl"].write_text(f"{rec}\n{rec}\n", encoding="utf-8")

    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)
    assert payload["daily_run_index_state"] == "blocked_or_invalid"
    assert "m450_record_count_not_one" in payload["blockers"]


def test_m452_not_accepted_produces_blocked(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m452(paths["m452_jsonl"], acceptance_gate_state="blocked_or_invalid", accepted_for_operator_observation=False)

    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)
    assert payload["daily_run_index_state"] == "blocked_or_invalid"
    assert "m452_state_not_accepted" in payload["blockers"]


def test_m451_text_warning_missing_produces_blocked(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m451_text(paths["m451_txt"], warning="Missing warning string")

    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)
    assert payload["daily_run_index_state"] == "blocked_or_invalid"
    assert "m451_txt_warning_missing" in payload["blockers"]


def test_mismatched_dates_produce_blocked(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m450(paths["m450_jsonl"], expected_latest_bar_date="2026-06-07")

    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)
    assert payload["daily_run_index_state"] == "blocked_or_invalid"
    assert "mismatched_expected_latest_bar_date" in payload["blockers"]


def test_mismatched_posture_produces_blocked(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m449(paths["m449_jsonl"], source_posture="risk_off")

    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)
    assert payload["daily_run_index_state"] == "blocked_or_invalid"
    assert "m449_source_posture_unexpected" in payload["blockers"]


@pytest.mark.parametrize(
    "milestone_name, mock_writer, permission_key",
    [
        ("M447", _write_valid_m447, "submit_authorized"),
        ("M447", _write_valid_m447, "paper_submit_authorized"),
        ("M448", _write_valid_m448, "paper_action_authorized"),
        ("M448", _write_valid_m448, "submit_authorized"),
        ("M448", _write_valid_m448, "paper_submit_authorized"),
        ("M449", _write_valid_m449, "paper_submit_allowed"),
        ("M449", _write_valid_m449, "live_submit_allowed"),
        ("M450", _write_valid_m450, "paper_submit_allowed"),
        ("M450", _write_valid_m450, "live_submit_allowed"),
        ("M451", _write_valid_m451_summary, "paper_submit_allowed"),
        ("M451", _write_valid_m451_summary, "live_submit_allowed"),
        ("M452", _write_valid_m452, "paper_submit_allowed"),
        ("M452", _write_valid_m452, "live_submit_allowed"),
    ],
)
def test_submit_allowed_blocks(tmp_path, milestone_name, mock_writer, permission_key) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    file_key = {
        "M447": "m447_jsonl",
        "M448": "m448_jsonl",
        "M449": "m449_jsonl",
        "M450": "m450_jsonl",
        "M451": "m451_summary_jsonl",
        "M452": "m452_jsonl",
    }[milestone_name]
    
    mock_writer(paths[file_key], **{permission_key: True})
    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)
    assert payload["daily_run_index_state"] == "blocked_or_invalid"


@pytest.mark.parametrize(
    "milestone_name, mock_writer, safety_flag",
    [
        ("M452", _write_valid_m452, "submitted"),
        ("M452", _write_valid_m452, "mutated"),
        ("M452", _write_valid_m452, "broker_action_performed"),
        ("M452", _write_valid_m452, "network_access_attempted"),
        ("M452", _write_valid_m452, "credential_access_attempted"),
        ("M452", _write_valid_m452, "live_authorized"),
        ("M452", _write_valid_m452, "os_scheduler_installed"),
        ("M452", _write_valid_m452, "scheduler_mutation_performed"),
    ],
)
def test_safety_and_scheduler_violations_block(tmp_path, milestone_name, mock_writer, safety_flag) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    file_key = {
        "M452": "m452_jsonl"
    }[milestone_name]

    mock_writer(paths[file_key], **{safety_flag: True})
    config = EtfSmaDailyRunIndexConfig(**paths)
    payload = run_etf_sma_daily_run_index(config)
    assert payload["daily_run_index_state"] == "blocked_or_invalid"


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
