from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_preview_archive_index import (
    EtfSmaDailyPreviewArchiveIndexConfig,
    run_etf_sma_daily_preview_archive_index,
    _normalize_path,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_preview_archive_index.py")

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "urllib",
    "os.environ",
    "os.getenv",
    "os.putenv",
    "subprocess",
)

# Also forbid research/features/screener/strategy/risk/market-hours modules
FORBIDDEN_INTERNAL_MODULES = (
    "algotrader.research",
    "algotrader.features",
    "algotrader.screener",
    "algotrader.strategy",
    "algotrader.risk",
    "algotrader.market_hours",
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

_STRICT_SAFETY = {
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


def _write_jsonl(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def _write_valid_m453(path: Path, **overrides) -> dict:
    rec = {
        "milestone": "M453",
        "phase": "offline_daily_run_index",
        "command": "etf-sma-daily-run-index",
        "daily_run_index_state": "ready",
        "accepted_for_operator_observation": True,
        "operator_warning": "preview_only_not_order_authorization",
        "text_warning_present": True,
        "blockers": [],
        "profit_claim": "none",
    }
    rec.update(_STRICT_SAFETY)
    rec.update(overrides)
    _write_jsonl(path, rec)
    return rec


def _write_valid_m454(path: Path, **overrides) -> dict:
    rec = {
        "milestone": "M454",
        "phase": "offline_daily_artifact_manifest_health",
        "command": "etf-sma-daily-artifact-manifest-health",
        "manifest_health_state": "ready",
        "accepted_for_operator_observation": True,
        "operator_warning": "preview_only_not_order_authorization",
        "blockers": [],
        "profit_claim": "none",
    }
    rec.update(_STRICT_SAFETY)
    rec.update(overrides)
    _write_jsonl(path, rec)
    return rec


def _write_valid_m455(path: Path, **overrides) -> dict:
    rec = {
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
        "decision_summary": "hold/noop",
        "posture_summary": "risk_on",
        "checked_artifact_count": 8,
    }
    rec.update(_STRICT_SAFETY)
    rec.update(overrides)
    _write_jsonl(path, rec)
    return rec


def _write_valid_m456_jsonl(path: Path, **overrides) -> dict:
    rec = {
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
    }
    rec.update(_STRICT_SAFETY)
    rec.update(overrides)
    _write_jsonl(path, rec)
    return rec


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


def _write_valid_m457(path: Path, **overrides) -> dict:
    rec = {
        "milestone": "M457",
        "phase": "offline_daily_dashboard_bundle_manifest",
        "command": "etf-sma-daily-dashboard-bundle-manifest",
        "bundle_state": "ready",
        "accepted_for_operator_observation": True,
        "source_dashboard_milestone": "M455",
        "source_dashboard_state": "ready",
        "source_text_export_milestone": "M456",
        "source_text_export_state": "ready",
        "input_dashboard_packet_path": "runs/paper_lab/m455_daily_operator_dashboard_packet.jsonl",
        "input_text_export_manifest_path": "runs/paper_lab/m456_daily_dashboard_text_export.jsonl",
        "input_text_export_path": "runs/paper_lab/m456_daily_dashboard_text_export.txt",
        "decision_summary": "hold/noop",
        "posture_summary": "risk_on",
        "checked_artifact_count": 8,
        "operator_warning": "preview_only_not_order_authorization",
        "blockers": [],
        "profit_claim": "none",
    }
    rec.update(_STRICT_SAFETY)
    rec.update(overrides)
    _write_jsonl(path, rec)
    return rec


def _write_all_valid_fixtures(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "input_run_index_path": tmp_path / "m453.jsonl",
        "input_manifest_health_path": tmp_path / "m454.jsonl",
        "input_dashboard_packet_path": tmp_path / "m455.jsonl",
        "input_text_export_manifest_path": tmp_path / "m456.jsonl",
        "input_text_export_path": tmp_path / "m456.txt",
        "input_bundle_manifest_path": tmp_path / "m457.jsonl",
        "output_archive_index_path": tmp_path / "m458.jsonl",
    }

    norm_m455 = _normalize_path(paths["input_dashboard_packet_path"])
    norm_m456_jsonl = _normalize_path(paths["input_text_export_manifest_path"])
    norm_m456_txt = _normalize_path(paths["input_text_export_path"])

    _write_valid_m453(paths["input_run_index_path"])
    _write_valid_m454(paths["input_manifest_health_path"])
    _write_valid_m455(paths["input_dashboard_packet_path"])
    _write_valid_m456_jsonl(
        paths["input_text_export_manifest_path"],
        input_dashboard_packet_path=norm_m455,
        output_text_path=norm_m456_txt,
    )
    _write_valid_m456_txt(paths["input_text_export_path"])
    _write_valid_m457(
        paths["input_bundle_manifest_path"],
        input_dashboard_packet_path=norm_m455,
        input_text_export_manifest_path=norm_m456_jsonl,
        input_text_export_path=norm_m456_txt,
    )
    return paths


def test_success_path_writes_exactly_one_record(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)

    assert payload["milestone"] == "M458"
    assert payload["phase"] == "offline_daily_preview_archive_index"
    assert payload["command"] == "etf-sma-daily-preview-archive-index"
    assert payload["archive_state"] == "ready"
    assert payload["accepted_for_operator_observation"] is True

    manifest_lines = paths["output_archive_index_path"].read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    manifest_rec = json.loads(manifest_lines[0])
    assert manifest_rec["milestone"] == "M458"
    assert manifest_rec["archive_state"] == "ready"


def test_success_path_overwrites_or_truncates(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    paths["output_archive_index_path"].write_text("stale manifest 1\nstale manifest 2\n", encoding="utf-8")

    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    run_etf_sma_daily_preview_archive_index(config)

    manifest_lines = paths["output_archive_index_path"].read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    assert "stale manifest" not in manifest_lines[0]


def test_success_path_includes_expected_paths(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)

    assert payload["input_run_index_path"] == _normalize_path(paths["input_run_index_path"])
    assert payload["input_manifest_health_path"] == _normalize_path(paths["input_manifest_health_path"])
    assert payload["input_dashboard_packet_path"] == _normalize_path(paths["input_dashboard_packet_path"])
    assert payload["input_text_export_manifest_path"] == _normalize_path(paths["input_text_export_manifest_path"])
    assert payload["input_text_export_path"] == _normalize_path(paths["input_text_export_path"])
    assert payload["input_bundle_manifest_path"] == _normalize_path(paths["input_bundle_manifest_path"])
    assert payload["output_archive_index_path"] == _normalize_path(paths["output_archive_index_path"])


def test_success_path_includes_derived_fields(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)

    assert payload["decision_summary"] == "hold/noop"
    assert payload["posture_summary"] == "risk_on"
    assert payload["checked_artifact_count"] == 8
    assert payload["operator_warning"] == "preview_only_not_order_authorization"


def test_success_path_archived_artifacts_metadata(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)

    assert payload["archived_artifact_count"] == 6
    artifacts = payload["archived_artifacts"]
    assert len(artifacts) == 6

    # Verify workflow order
    assert artifacts[0]["path"] == _normalize_path(paths["input_run_index_path"])
    assert artifacts[1]["path"] == _normalize_path(paths["input_manifest_health_path"])
    assert artifacts[2]["path"] == _normalize_path(paths["input_dashboard_packet_path"])
    assert artifacts[3]["path"] == _normalize_path(paths["input_text_export_manifest_path"])
    assert artifacts[4]["path"] == _normalize_path(paths["input_text_export_path"])
    assert artifacts[5]["path"] == _normalize_path(paths["input_bundle_manifest_path"])

    # Kinds
    assert artifacts[0]["kind"] == "jsonl"
    assert artifacts[1]["kind"] == "jsonl"
    assert artifacts[2]["kind"] == "jsonl"
    assert artifacts[3]["kind"] == "jsonl"
    assert artifacts[4]["kind"] == "txt"
    assert artifacts[5]["kind"] == "jsonl"

    # SHA and byte sizes present
    for art in artifacts:
        assert art["sha256"] != ""
        assert art["byte_size"] > 0

    # record counts present for jsonl, and not present for txt
    assert artifacts[0]["record_count"] == 1
    assert artifacts[1]["record_count"] == 1
    assert artifacts[2]["record_count"] == 1
    assert artifacts[3]["record_count"] == 1
    assert "record_count" not in artifacts[4]
    assert artifacts[5]["record_count"] == 1


def test_success_path_keeps_safety_booleans_false(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)

    for field in _STRICT_SAFETY:
        assert payload[field] is False
    assert payload["profit_claim"] == "none"


def test_missing_files_blocks(tmp_path) -> None:
    for key in ["input_run_index_path", "input_manifest_health_path", "input_dashboard_packet_path",
                "input_text_export_manifest_path", "input_text_export_path", "input_bundle_manifest_path"]:
        paths = _write_all_valid_fixtures(tmp_path)
        file_to_delete = paths[key]
        file_to_delete.unlink()

        config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
        payload = run_etf_sma_daily_preview_archive_index(config)

        assert payload["archive_state"] == "blocked_or_invalid"
        assert payload["accepted_for_operator_observation"] is False
        prefix = key.replace("input_", "").replace("_path", "").replace("text_export_manifest", "m456").replace("text_export", "m456_text").replace("bundle_manifest", "m457").replace("dashboard_packet", "m455").replace("manifest_health", "m454").replace("run_index", "m453")
        assert f"{prefix}_missing" in payload["blockers"]


def test_empty_jsonl_input_blocks(tmp_path) -> None:
    for key in ["input_run_index_path", "input_manifest_health_path", "input_dashboard_packet_path",
                "input_text_export_manifest_path", "input_bundle_manifest_path"]:
        paths = _write_all_valid_fixtures(tmp_path)
        paths[key].write_text("", encoding="utf-8")

        config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
        payload = run_etf_sma_daily_preview_archive_index(config)

        assert payload["archive_state"] == "blocked_or_invalid"
        prefix = key.replace("input_", "").replace("_path", "").replace("text_export_manifest", "m456").replace("bundle_manifest", "m457").replace("dashboard_packet", "m455").replace("manifest_health", "m454").replace("run_index", "m453")
        assert f"{prefix}_empty" in payload["blockers"]


def test_malformed_jsonl_input_blocks(tmp_path) -> None:
    for key in ["input_run_index_path", "input_manifest_health_path", "input_dashboard_packet_path",
                "input_text_export_manifest_path", "input_bundle_manifest_path"]:
        paths = _write_all_valid_fixtures(tmp_path)
        paths[key].write_text("{malformed\n", encoding="utf-8")

        config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
        payload = run_etf_sma_daily_preview_archive_index(config)

        assert payload["archive_state"] == "blocked_or_invalid"
        prefix = key.replace("input_", "").replace("_path", "").replace("text_export_manifest", "m456").replace("bundle_manifest", "m457").replace("dashboard_packet", "m455").replace("manifest_health", "m454").replace("run_index", "m453")
        assert f"{prefix}_malformed_json" in payload["blockers"]


def test_multi_record_jsonl_input_blocks(tmp_path) -> None:
    for key in ["input_run_index_path", "input_manifest_health_path", "input_dashboard_packet_path",
                "input_text_export_manifest_path", "input_bundle_manifest_path"]:
        paths = _write_all_valid_fixtures(tmp_path)
        rec = json.dumps({"milestone": "dummy"})
        paths[key].write_text(f"{rec}\n{rec}\n", encoding="utf-8")

        config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
        payload = run_etf_sma_daily_preview_archive_index(config)

        assert payload["archive_state"] == "blocked_or_invalid"
        prefix = key.replace("input_", "").replace("_path", "").replace("text_export_manifest", "m456").replace("bundle_manifest", "m457").replace("dashboard_packet", "m455").replace("manifest_health", "m454").replace("run_index", "m453")
        assert f"{prefix}_record_count_not_one" in payload["blockers"]


def test_m457_wrong_milestone_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], milestone="M999")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_milestone_mismatch" in payload["blockers"]


def test_m457_wrong_phase_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], phase="wrong")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_phase_mismatch" in payload["blockers"]


def test_m457_wrong_command_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], command="wrong")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_command_mismatch" in payload["blockers"]


def test_m457_bundle_state_not_ready_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], bundle_state="blocked")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_bundle_state_not_ready" in payload["blockers"]


def test_m457_accepted_observation_not_true_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], accepted_for_operator_observation=False)
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_not_accepted_for_observation" in payload["blockers"]


def test_m457_source_states_not_ready_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], source_dashboard_state="blocked")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_source_dashboard_state_not_ready" in payload["blockers"]

    _write_valid_m457(paths["input_bundle_manifest_path"], source_text_export_state="blocked")
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_source_text_export_state_not_ready" in payload["blockers"]


def test_m457_operator_warning_mismatch(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], operator_warning="wrong")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_operator_warning_mismatch" in payload["blockers"]


def test_m457_blockers_not_empty_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], blockers=["m457_failed"])
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_blockers_not_empty" in payload["blockers"]


def test_m457_profit_claim_invalid_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m457(paths["input_bundle_manifest_path"], profit_claim="wrong")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_profit_claim_not_none" in payload["blockers"]


def test_m455_wrong_readiness_fields_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], dashboard_state="blocked")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m455_dashboard_state_not_ready" in payload["blockers"]


def test_m456_wrong_readiness_fields_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m456_jsonl(paths["input_text_export_manifest_path"], export_state="blocked")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m456_export_state_not_ready" in payload["blockers"]


def test_m456_text_export_changed_required_line_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Write custom file missing required state line
    paths["input_text_export_path"].write_text("Wrong Title\nexport_state: ready\n", encoding="utf-8")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m456_text_line_missing" in payload["blockers"]


def test_m456_text_export_values_match_m456_jsonl(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Write decision summary mismatch
    _write_valid_m456_txt(paths["input_text_export_path"], decision_summary="mismatch")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m456_text_decision_summary_mismatch" in payload["blockers"]


def test_operator_warning_mismatch_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Change M455 operator_warning to mismatch M456
    _write_valid_m455(paths["input_dashboard_packet_path"], operator_warning="mismatch")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m455_operator_warning_mismatch" in payload["blockers"]


def test_path_mismatch_blocks(tmp_path) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    # Write M457 bundle manifest with different input dashboard path
    _write_valid_m457(paths["input_bundle_manifest_path"], input_dashboard_packet_path="wrong/path.jsonl")
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert "m457_input_dashboard_packet_path_mismatch" in payload["blockers"]


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
def test_safety_field_violations(tmp_path, field, val_override, expect_blocker) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    _write_valid_m455(paths["input_dashboard_packet_path"], **{field: val_override})
    config = EtfSmaDailyPreviewArchiveIndexConfig(**paths)
    payload = run_etf_sma_daily_preview_archive_index(config)
    assert payload["archive_state"] == "blocked_or_invalid"
    assert expect_blocker in payload["blockers"]


def test_no_hardcoded_runtime_date_in_production() -> None:
    content = MODULE_PATH.read_text(encoding="utf-8")
    assert "2026-06" not in content, "Production code must not contain a hardcoded runtime date check."


def test_cli_format_json(tmp_path, capsys) -> None:
    paths = _write_all_valid_fixtures(tmp_path)
    exit_code = cli_module.main(
        [
            "etf-sma-daily-preview-archive-index",
            "--input-run-index-path",
            str(paths["input_run_index_path"]),
            "--input-manifest-health-path",
            str(paths["input_manifest_health_path"]),
            "--input-dashboard-packet-path",
            str(paths["input_dashboard_packet_path"]),
            "--input-text-export-manifest-path",
            str(paths["input_text_export_manifest_path"]),
            "--input-text-export-path",
            str(paths["input_text_export_path"]),
            "--input-bundle-manifest-path",
            str(paths["input_bundle_manifest_path"]),
            "--output-archive-index-path",
            str(paths["output_archive_index_path"]),
            "--format",
            "json",
        ]
    )
    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M458"
    assert printed["archive_state"] == "ready"


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

    for internal in FORBIDDEN_INTERNAL_MODULES:
        for imp in imports:
            assert not (
                imp == internal or imp.startswith(f"{internal}.")
            ), f"Forbidden internal import: {imp}"

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
