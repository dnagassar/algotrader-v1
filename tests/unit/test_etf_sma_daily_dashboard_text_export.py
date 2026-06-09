from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_dashboard_text_export import (
    EtfSmaDailyDashboardTextExportConfig,
    run_etf_sma_daily_dashboard_text_export,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_dashboard_text_export.py")

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


def _write_valid_m455(path: Path, delete_fields: list[str] = None, **overrides) -> dict:
    record = {
        "milestone": "M455",
        "phase": "offline_daily_operator_dashboard_packet",
        "command": "etf-sma-daily-operator-dashboard-packet",
        "dashboard_state": "ready",
        "accepted_for_operator_observation": True,
        "source_run_index_milestone": "M453",
        "source_manifest_health_milestone": "M454",
        "source_run_index_state": "ready",
        "source_manifest_health_state": "ready",
        "latest_bar_date_consistent": True,
        "operator_warning": "preview_only_not_order_authorization",
        "blockers": [],
        "profit_claim": "none",
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
        "decision_summary": "hold/noop",
        "posture_summary": "risk_on",
        "checked_artifact_count": 8,
    }
    record.update(overrides)
    if delete_fields:
        for f in delete_fields:
            if f in record:
                del record[f]
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_all_valid_fixtures(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "input_dashboard_packet_path": tmp_path / "m455.jsonl",
        "output_text_path": tmp_path / "m456.txt",
        "output_manifest_path": tmp_path / "m456.jsonl",
    }
    _write_valid_m455(paths["input_dashboard_packet_path"])
    return paths


# 1. success path writes exactly one JSONL manifest record
# 2. success path writes deterministic text export
# 4. success path includes M456 milestone, phase, command, ready export state, and M455 source state
# 6. success path JSON keeps all strict safety booleans false
def test_success_path_writes_files(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)

    assert payload["milestone"] == "M456"
    assert payload["phase"] == "offline_daily_dashboard_text_export"
    assert payload["command"] == "etf-sma-daily-dashboard-text-export"
    assert payload["export_state"] == "ready"
    assert payload["accepted_for_operator_observation"] is True
    assert payload["source_dashboard_milestone"] == "M455"
    assert payload["source_dashboard_state"] == "ready"

    # Verify JSONL manifest has exactly one line
    manifest_lines = paths["output_manifest_path"].read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    manifest_rec = json.loads(manifest_lines[0])
    assert manifest_rec["milestone"] == "M456"
    assert manifest_rec["export_state"] == "ready"
    assert manifest_rec["accepted_for_operator_observation"] is True

    # Check strict safety fields in JSON are False
    for f in [
        "order_authorization",
        "paper_submit_allowed",
        "live_submit_allowed",
        "scheduler_install_allowed",
        "submitted",
        "mutated",
        "broker_action_performed",
        "network_access_attempted",
        "credential_access_attempted",
        "live_authorized",
        "os_scheduler_installed",
        "scheduler_mutation_performed",
    ]:
        assert manifest_rec[f] is False


# 3. success path overwrites/truncates stale JSONL and text outputs, not append
def test_success_path_overwrites_stale(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Write stale content
    paths["output_text_path"].write_text("stale text content 1\nstale text content 2\n", encoding="utf-8")
    paths["output_manifest_path"].write_text("stale manifest 1\nstale manifest 2\n", encoding="utf-8")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    run_etf_sma_daily_dashboard_text_export(config)

    text_content = paths["output_text_path"].read_text(encoding="utf-8")
    assert "stale text" not in text_content

    manifest_lines = paths["output_manifest_path"].read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    assert "stale manifest" not in manifest_lines[0]


# 5. success path text includes decision_summary, posture_summary, checked_artifact_count, operator_warning, submitted=false, mutated=false, paper_submit_allowed=false, live_submit_allowed=false, scheduler_install_allowed=false
def test_success_path_text_content(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    run_etf_sma_daily_dashboard_text_export(config)

    text_content = paths["output_text_path"].read_text(encoding="utf-8")
    assert "ETF/SMA Daily Operator Dashboard Export (M456)" in text_content
    assert "dashboard_state: ready" in text_content
    assert "source M453 state: ready" in text_content
    assert "source M454 state: ready" in text_content
    assert "latest_bar_date_consistent: true" in text_content
    assert "operator_warning: preview_only_not_order_authorization" in text_content
    assert "decision_summary: hold/noop" in text_content
    assert "posture_summary: risk_on" in text_content
    assert "checked_artifact_count: 8" in text_content
    assert "submitted=false" in text_content
    assert "mutated=false" in text_content
    assert "paper_submit_allowed=false" in text_content
    assert "live_submit_allowed=false" in text_content
    assert "scheduler_install_allowed=false" in text_content
    assert "order_authorization=false" in text_content
    assert "blockers=[]" in text_content


# 7. success path normalizes artifact paths with forward slashes
def test_success_path_normalizes_paths(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Use absolute paths with backslashes on Windows, or just generic absolute paths
    abs_input = Path(paths["input_dashboard_packet_path"]).resolve()
    abs_output_txt = Path(paths["output_text_path"]).resolve()
    abs_output_jsonl = Path(paths["output_manifest_path"]).resolve()

    config = EtfSmaDailyDashboardTextExportConfig(
        input_dashboard_packet_path=abs_input,
        output_text_path=abs_output_txt,
        output_manifest_path=abs_output_jsonl,
    )
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert "\\" not in payload["input_dashboard_packet_path"]
    assert "\\" not in payload["output_text_path"]


# 8. missing M455 JSONL blocks fail-closed with one manifest record and blocked text
def test_missing_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_dashboard_packet_path"].unlink()

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)

    assert payload["export_state"] == "blocked_or_invalid"
    assert payload["accepted_for_operator_observation"] is False
    assert "m455_missing" in payload["blockers"]

    # Verify manifest & text
    manifest_lines = paths["output_manifest_path"].read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    manifest_rec = json.loads(manifest_lines[0])
    assert manifest_rec["export_state"] == "blocked_or_invalid"

    text_content = paths["output_text_path"].read_text(encoding="utf-8")
    assert "export_state: blocked_or_invalid" in text_content
    assert "blockers=[\"m455_missing\"]" in text_content


# 9. empty M455 JSONL blocks fail-closed
def test_empty_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_dashboard_packet_path"].write_text("", encoding="utf-8")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_empty" in payload["blockers"]


# 10. malformed M455 JSONL blocks fail-closed
def test_malformed_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_dashboard_packet_path"].write_text("{malformed\n", encoding="utf-8")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_malformed_json" in payload["blockers"]


# 11. multi-record M455 JSONL blocks fail-closed
def test_multi_record_input_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    rec = json.dumps({"milestone": "M455"})
    paths["input_dashboard_packet_path"].write_text(f"{rec}\n{rec}\n", encoding="utf-8")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_record_count_not_one" in payload["blockers"]


# 12. M455 wrong milestone blocks fail-closed
def test_wrong_milestone_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], milestone="M999")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_milestone_mismatch" in payload["blockers"]


# 13. M455 wrong phase blocks fail-closed
def test_wrong_phase_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], phase="wrong_phase")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_phase_mismatch" in payload["blockers"]


# 14. M455 wrong command blocks fail-closed
def test_wrong_command_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], command="wrong-command")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_command_mismatch" in payload["blockers"]


# 15. M455 dashboard_state not ready blocks fail-closed
def test_dashboard_state_not_ready_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], dashboard_state="blocked")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_dashboard_state_not_ready" in payload["blockers"]


# 16. M455 accepted_for_operator_observation not true blocks fail-closed
def test_observation_not_accepted_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], accepted_for_operator_observation=False)

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_not_accepted_for_observation" in payload["blockers"]


# 17. M455 source_run_index_milestone not M453 blocks fail-closed
def test_source_run_index_milestone_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], source_run_index_milestone="M999")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_source_run_index_milestone_mismatch" in payload["blockers"]


# 18. M455 source_manifest_health_milestone not M454 blocks fail-closed
def test_source_manifest_health_milestone_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], source_manifest_health_milestone="M999")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_source_manifest_health_milestone_mismatch" in payload["blockers"]


# 19. M455 source_run_index_state not ready blocks fail-closed
def test_source_run_index_state_not_ready_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], source_run_index_state="blocked")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_source_run_index_state_not_ready" in payload["blockers"]


# 20. M455 source_manifest_health_state not ready blocks fail-closed
def test_source_manifest_health_state_not_ready_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], source_manifest_health_state="blocked")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_source_manifest_health_state_not_ready" in payload["blockers"]


# 21. M455 latest_bar_date_consistent not true blocks fail-closed
def test_latest_bar_date_inconsistent_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], latest_bar_date_consistent=False)

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_latest_bar_date_consistent_not_true" in payload["blockers"]


# 22. M455 operator_warning not exactly preview_only_not_order_authorization blocks fail-closed
def test_operator_warning_unexpected_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], operator_warning="unsafe_authorization")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_operator_warning_mismatch" in payload["blockers"]


# 23. M455 blockers not [] blocks fail-closed
def test_blockers_not_empty_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], blockers=["some_blocker"])

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_blockers_not_empty" in payload["blockers"]


# 24. M455 profit_claim missing or not equal to "none" blocks fail-closed
def test_profit_claim_violations(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], profit_claim="arbitrary")

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_profit_claim_not_none" in payload["blockers"]

    # Test missing profit_claim
    _write_valid_m455(paths["input_dashboard_packet_path"], delete_fields=["profit_claim"])
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_profit_claim_missing" in payload["blockers"]


# 25. any strict safety field set to true blocks fail-closed
# 26. a strict safety field set to "false" blocks fail-closed
# 27. a strict safety field set to "none" blocks fail-closed
# 28. a strict safety field set to 0 blocks fail-closed
# 29. a strict safety field set to None blocks fail-closed
# 30. a strict safety field missing blocks fail-closed
@pytest.mark.parametrize(
    "field, val_override, expect_blocker",
    [
        ("order_authorization", True, "m455_order_authorization_invalid_or_unsafe"),
        ("order_authorization", "false", "m455_order_authorization_invalid_or_unsafe"),
        ("order_authorization", "none", "m455_order_authorization_invalid_or_unsafe"),
        ("order_authorization", 0, "m455_order_authorization_invalid_or_unsafe"),
        ("order_authorization", None, "m455_order_authorization_invalid_or_unsafe"),
        ("paper_submit_allowed", True, "m455_paper_submit_allowed_invalid_or_unsafe"),
        ("paper_submit_allowed", "false", "m455_paper_submit_allowed_invalid_or_unsafe"),
        ("live_submit_allowed", True, "m455_live_submit_allowed_invalid_or_unsafe"),
        ("submitted", True, "m455_submitted_invalid_or_unsafe"),
        ("mutated", True, "m455_mutated_invalid_or_unsafe"),
        ("broker_action_performed", True, "m455_broker_action_performed_invalid_or_unsafe"),
        ("network_access_attempted", True, "m455_network_access_attempted_invalid_or_unsafe"),
        ("credential_access_attempted", True, "m455_credential_access_attempted_invalid_or_unsafe"),
        ("live_authorized", True, "m455_live_authorized_invalid_or_unsafe"),
        ("os_scheduler_installed", True, "m455_os_scheduler_installed_invalid_or_unsafe"),
        ("scheduler_mutation_performed", True, "m455_scheduler_mutation_performed_invalid_or_unsafe"),
    ],
)
def test_safety_field_violations_block(tmp_path, field, val_override, expect_blocker) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], **{field: val_override})

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert expect_blocker in payload["blockers"]


def test_safety_field_missing_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], delete_fields=["order_authorization"])

    config = EtfSmaDailyDashboardTextExportConfig(**paths)
    payload = run_etf_sma_daily_dashboard_text_export(config)
    assert payload["export_state"] == "blocked_or_invalid"
    assert "m455_order_authorization_missing" in payload["blockers"]


# 31. CLI --format json returns valid JSON
def test_cli_format_json(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-dashboard-text-export",
            "--input-dashboard-packet-path",
            str(paths["input_dashboard_packet_path"]),
            "--output-text-path",
            str(paths["output_text_path"]),
            "--output-manifest-path",
            str(paths["output_manifest_path"]),
            "--format",
            "json",
        ]
    )
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M456"
    assert printed["export_state"] == "ready"


# 32. CLI --format text includes milestone, export state, warning, submitted=false, mutated=false
def test_cli_format_text(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-dashboard-text-export",
            "--input-dashboard-packet-path",
            str(paths["input_dashboard_packet_path"]),
            "--output-text-path",
            str(paths["output_text_path"]),
            "--output-manifest-path",
            str(paths["output_manifest_path"]),
            "--format",
            "text",
        ]
    )
    assert exit_code == 0
    printed = capsys.readouterr().out
    assert "ETF/SMA Daily Operator Dashboard Export (M456)" in printed
    assert "dashboard_state: ready" in printed
    assert "operator_warning: preview_only_not_order_authorization" in printed
    assert "submitted=false" in printed
    assert "mutated=false" in printed


# 33. production implementation does not contain a hardcoded 2026-06-08 runtime validation constant
def test_no_hardcoded_runtime_date_in_production() -> None:
    content = MODULE_PATH.read_text(encoding="utf-8")
    assert "2026-06-08" not in content, "Production code must not contain a hardcoded runtime date check."


# 34. AST/import invariant forbids broker SDK imports and network/socket imports in the new execution module
# 35. AST/call invariant forbids credential env access through os.getenv, os.environ, or os.putenv
# 36. AST/call invariant forbids submit_order, cancel, cancel_order, replace, replace_order, close_position, close_all_positions, liquidate, liquidation, delete, retry, and scheduler-install APIs
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
