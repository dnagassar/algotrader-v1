from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_dashboard_bundle_manifest import (
    EtfSmaDailyDashboardBundleManifestConfig,
    run_etf_sma_daily_dashboard_bundle_manifest,
    _normalize_path,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_dashboard_bundle_manifest.py")

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


def _write_valid_m456_jsonl(path: Path, delete_fields: list[str] = None, **overrides) -> dict:
    record = {
        "milestone": "M456",
        "phase": "offline_daily_dashboard_text_export",
        "command": "etf-sma-daily-dashboard-text-export",
        "export_state": "ready",
        "accepted_for_operator_observation": True,
        "source_dashboard_milestone": "M455",
        "source_dashboard_state": "ready",
        "input_dashboard_packet_path": "runs/paper_lab/m455_daily_operator_dashboard_packet.jsonl",
        "output_text_path": "runs/paper_lab/m456_daily_dashboard_text_export.txt",
        "operator_warning": "preview_only_not_order_authorization",
        "blockers": [],
        "profit_claim": "none",
        "decision_summary": "hold/noop",
        "posture_summary": "risk_on",
        "checked_artifact_count": 8,
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
    }
    record.update(overrides)
    if delete_fields:
        for f in delete_fields:
            if f in record:
                del record[f]
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m456_txt(path: Path, **overrides) -> str:
    content = (
        "ETF/SMA Daily Operator Dashboard Export (M456)\n"
        "==============================================\n"
        "export_state: ready\n"
        "source M455 state: ready\n"
        "dashboard_state: ready\n"
        "source M453 state: ready\n"
        "source M454 state: ready\n"
        "latest_bar_date_consistent: true\n"
        "operator_warning: preview_only_not_order_authorization\n"
        f"decision_summary: {overrides.get('decision_summary', 'hold/noop')}\n"
        f"posture_summary: {overrides.get('posture_summary', 'risk_on')}\n"
        f"checked_artifact_count: {overrides.get('checked_artifact_count', 8)}\n"
        "submitted=false\n"
        "mutated=false\n"
        "paper_submit_allowed=false\n"
        "live_submit_allowed=false\n"
        "scheduler_install_allowed=false\n"
        "order_authorization=false\n"
        "blockers=[]\n"
    )
    path.write_text(content, encoding="utf-8")
    return content


def _write_all_valid_fixtures(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "input_dashboard_packet_path": tmp_path / "m455.jsonl",
        "input_text_export_manifest_path": tmp_path / "m456.jsonl",
        "input_text_export_path": tmp_path / "m456.txt",
        "output_manifest_path": tmp_path / "m457.jsonl",
    }
    _write_valid_m455(paths["input_dashboard_packet_path"])
    _write_valid_m456_jsonl(
        paths["input_text_export_manifest_path"],
        input_dashboard_packet_path=_normalize_path(paths["input_dashboard_packet_path"]),
        output_text_path=_normalize_path(paths["input_text_export_path"]),
    )
    _write_valid_m456_txt(paths["input_text_export_path"])
    return paths


def test_success_path_writes_exactly_one_record(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["milestone"] == "M457"
    assert payload["phase"] == "offline_daily_dashboard_bundle_manifest"
    assert payload["command"] == "etf-sma-daily-dashboard-bundle-manifest"
    assert payload["bundle_state"] == "ready"
    assert payload["accepted_for_operator_observation"] is True

    manifest_lines = paths["output_manifest_path"].read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    manifest_rec = json.loads(manifest_lines[0])
    assert manifest_rec["milestone"] == "M457"
    assert manifest_rec["bundle_state"] == "ready"


def test_success_path_overwrites_or_truncates(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["output_manifest_path"].write_text("stale manifest 1\nstale manifest 2\n", encoding="utf-8")

    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    run_etf_sma_daily_dashboard_bundle_manifest(config)

    manifest_lines = paths["output_manifest_path"].read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    assert "stale manifest" not in manifest_lines[0]


def test_success_path_includes_metadata_and_source_states(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["source_dashboard_milestone"] == "M455"
    assert payload["source_dashboard_state"] == "ready"
    assert payload["source_text_export_milestone"] == "M456"
    assert payload["source_text_export_state"] == "ready"


def test_success_path_keeps_safety_booleans_false(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    for field in [
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
        assert payload[field] is False


def test_success_path_normalizes_paths(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert "\\" not in payload["input_dashboard_packet_path"]
    assert "\\" not in payload["input_text_export_manifest_path"]
    assert "\\" not in payload["input_text_export_path"]


def test_success_path_derives_summaries_from_m456(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["decision_summary"] == "hold/noop"
    assert payload["posture_summary"] == "risk_on"
    assert payload["checked_artifact_count"] == 8
    assert payload["operator_warning"] == "preview_only_not_order_authorization"


def test_success_path_validates_m456_text_lines(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Write text export missing one required line
    paths["input_text_export_path"].write_text("random text\n", encoding="utf-8")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    
    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m456_text_line_missing" in payload["blockers"]


def test_success_path_validates_m456_text_values_match(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Write mismatching decision_summary in text
    _write_valid_m456_txt(paths["input_text_export_path"], decision_summary="mismatch_dec")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    
    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m456_text_decision_summary_mismatch" in payload["blockers"]


def test_missing_m455_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_dashboard_packet_path"].unlink()
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m455_missing" in payload["blockers"]


def test_empty_m455_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_dashboard_packet_path"].write_text("", encoding="utf-8")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m455_empty" in payload["blockers"]


def test_malformed_m455_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_dashboard_packet_path"].write_text("{malformed\n", encoding="utf-8")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m455_malformed_json" in payload["blockers"]


def test_multi_record_m455_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    rec = json.dumps({"milestone": "M455"})
    paths["input_dashboard_packet_path"].write_text(f"{rec}\n{rec}\n", encoding="utf-8")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m455_record_count_not_one" in payload["blockers"]


def test_missing_m456_manifest_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_text_export_manifest_path"].unlink()
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m456_manifest_missing" in payload["blockers"]


def test_empty_m456_manifest_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_text_export_manifest_path"].write_text("", encoding="utf-8")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m456_manifest_empty" in payload["blockers"]


def test_malformed_m456_manifest_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_text_export_manifest_path"].write_text("{malformed\n", encoding="utf-8")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m456_manifest_malformed_json" in payload["blockers"]


def test_multi_record_m456_manifest_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    rec = json.dumps({"milestone": "M456"})
    paths["input_text_export_manifest_path"].write_text(f"{rec}\n{rec}\n", encoding="utf-8")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m456_manifest_record_count_not_one" in payload["blockers"]


def test_missing_m456_text_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["input_text_export_path"].unlink()
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)

    assert payload["bundle_state"] == "blocked_or_invalid"
    assert "m456_text_missing" in payload["blockers"]


def test_m455_validation_mismatches(tmp_path) -> None:
    # milestone
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], milestone="M999")
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_milestone_mismatch" in payload["blockers"]

    # phase
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], phase="wrong")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_phase_mismatch" in payload["blockers"]

    # command
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], command="wrong")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_command_mismatch" in payload["blockers"]

    # dashboard_state
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], dashboard_state="blocked")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_dashboard_state_not_ready" in payload["blockers"]

    # accepted_for_operator_observation
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], accepted_for_operator_observation=False)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_not_accepted_for_observation" in payload["blockers"]

    # source_run_index_milestone
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], source_run_index_milestone="M999")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_source_run_index_milestone_mismatch" in payload["blockers"]

    # source_manifest_health_milestone
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], source_manifest_health_milestone="M999")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_source_manifest_health_milestone_mismatch" in payload["blockers"]

    # source_run_index_state
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], source_run_index_state="blocked")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_source_run_index_state_not_ready" in payload["blockers"]

    # source_manifest_health_state
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], source_manifest_health_state="blocked")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_source_manifest_health_state_not_ready" in payload["blockers"]

    # latest_bar_date_consistent
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], latest_bar_date_consistent=False)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_latest_bar_date_consistent_not_true" in payload["blockers"]

    # operator_warning
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], operator_warning="wrong")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_operator_warning_mismatch" in payload["blockers"]

    # blockers
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], blockers=["blocker"])
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_blockers_not_empty" in payload["blockers"]

    # profit_claim
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], profit_claim="wrong")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m455_profit_claim_not_none" in payload["blockers"]


def test_m456_validation_mismatches(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    norm_input = _normalize_path(paths["input_dashboard_packet_path"])
    norm_txt = _normalize_path(paths["input_text_export_path"])
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)

    # milestone
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], milestone="M999", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_milestone_mismatch" in payload["blockers"]

    # phase
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], phase="wrong", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_phase_mismatch" in payload["blockers"]

    # command
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], command="wrong", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_command_mismatch" in payload["blockers"]

    # export_state
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], export_state="blocked", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_export_state_not_ready" in payload["blockers"]

    # accepted_for_operator_observation
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], accepted_for_operator_observation=False, input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_not_accepted_for_observation" in payload["blockers"]

    # source_dashboard_milestone
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], source_dashboard_milestone="M999", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_source_dashboard_milestone_mismatch" in payload["blockers"]

    # source_dashboard_state
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], source_dashboard_state="blocked", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_source_dashboard_state_not_ready" in payload["blockers"]

    # operator_warning
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], operator_warning="wrong", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_operator_warning_mismatch" in payload["blockers"]

    # profit_claim
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], profit_claim="wrong", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_profit_claim_not_none" in payload["blockers"]

    # path mismatch
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], input_dashboard_packet_path="wrong_path", output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_input_path_mismatch" in payload["blockers"]

    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], input_dashboard_packet_path=norm_input, output_text_path="wrong_path")
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_output_text_path_mismatch" in payload["blockers"]


def test_cross_artifact_mismatches(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    norm_input = _normalize_path(paths["input_dashboard_packet_path"])
    norm_txt = _normalize_path(paths["input_text_export_path"])
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)

    # decision_summary
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], decision_summary="mismatch", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_decision_summary_mismatch" in payload["blockers"]

    # posture_summary
    _write_all_valid_fixtures(tmp_path)
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], posture_summary="mismatch", input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_posture_summary_mismatch" in payload["blockers"]

    # checked_artifact_count
    _write_all_valid_fixtures(tmp_path)
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], checked_artifact_count=999, input_dashboard_packet_path=norm_input, output_text_path=norm_txt)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert "m456_checked_artifact_count_mismatch" in payload["blockers"]


@pytest.mark.parametrize(
    "field, val_override, expect_blocker",
    [
        ("order_authorization", True, "m455_order_authorization_invalid_or_unsafe"),
        ("order_authorization", "false", "m455_order_authorization_invalid_or_unsafe"),
        ("order_authorization", "none", "m455_order_authorization_invalid_or_unsafe"),
        ("order_authorization", 0, "m455_order_authorization_invalid_or_unsafe"),
        ("order_authorization", None, "m455_order_authorization_invalid_or_unsafe"),
        ("paper_submit_allowed", True, "m455_paper_submit_allowed_invalid_or_unsafe"),
        ("live_submit_allowed", True, "m455_live_submit_allowed_invalid_or_unsafe"),
        ("submitted", True, "m455_submitted_invalid_or_unsafe"),
    ],
)
def test_safety_field_violations_m455(tmp_path, field, val_override, expect_blocker) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], **{field: val_override})
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert payload["bundle_state"] == "blocked_or_invalid"
    assert expect_blocker in payload["blockers"]


@pytest.mark.parametrize(
    "field, val_override, expect_blocker",
    [
        ("order_authorization", True, "m456_order_authorization_invalid_or_unsafe"),
        ("order_authorization", "false", "m456_order_authorization_invalid_or_unsafe"),
        ("order_authorization", "none", "m456_order_authorization_invalid_or_unsafe"),
        ("order_authorization", 0, "m456_order_authorization_invalid_or_unsafe"),
        ("order_authorization", None, "m456_order_authorization_invalid_or_unsafe"),
        ("paper_submit_allowed", True, "m456_paper_submit_allowed_invalid_or_unsafe"),
        ("live_submit_allowed", True, "m456_live_submit_allowed_invalid_or_unsafe"),
        ("submitted", True, "m456_submitted_invalid_or_unsafe"),
    ],
)
def test_safety_field_violations_m456(tmp_path, field, val_override, expect_blocker) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    norm_input = _normalize_path(paths["input_dashboard_packet_path"])
    norm_txt = _normalize_path(paths["input_text_export_path"])
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], input_dashboard_packet_path=norm_input, output_text_path=norm_txt, **{field: val_override})
    config = EtfSmaDailyDashboardBundleManifestConfig(**paths)
    payload = run_etf_sma_daily_dashboard_bundle_manifest(config)
    assert payload["bundle_state"] == "blocked_or_invalid"
    assert expect_blocker in payload["blockers"]


def test_cli_format_json(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-dashboard-bundle-manifest",
            "--input-dashboard-packet-path",
            str(paths["input_dashboard_packet_path"]),
            "--input-text-export-manifest-path",
            str(paths["input_text_export_manifest_path"]),
            "--input-text-export-path",
            str(paths["input_text_export_path"]),
            "--output-manifest-path",
            str(paths["output_manifest_path"]),
            "--format",
            "json",
        ]
    )
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M457"
    assert printed["bundle_state"] == "ready"


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

    for prefix in FORBIDDEN_IMPORT_PREFIXES:
        for imp in imports:
            assert not (
                imp == prefix or imp.startswith(f"{prefix}.")
            ), f"Forbidden import: {imp}"

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
