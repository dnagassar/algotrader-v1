"""Offline daily preview archive index for Milestone M458.

This module validates accepted daily workflow artifacts from M453 through M457
and writes exactly one JSONL record containing metadata of these artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyPreviewArchiveIndexConfig",
    "run_etf_sma_daily_preview_archive_index",
    "build_etf_sma_daily_preview_archive_index",
]

_MILESTONE = "M458"
_PHASE = "offline_daily_preview_archive_index"
_COMMAND = "etf-sma-daily-preview-archive-index"

_DEFAULT_INPUT_M453 = "runs/paper_lab/m453_daily_run_index.jsonl"
_DEFAULT_INPUT_M454 = "runs/paper_lab/m454_daily_artifact_manifest_health_check.jsonl"
_DEFAULT_INPUT_M455 = "runs/paper_lab/m455_daily_operator_dashboard_packet.jsonl"
_DEFAULT_INPUT_M456_JSONL = "runs/paper_lab/m456_daily_dashboard_text_export.jsonl"
_DEFAULT_INPUT_M456_TXT = "runs/paper_lab/m456_daily_dashboard_text_export.txt"
_DEFAULT_INPUT_M457 = "runs/paper_lab/m457_daily_dashboard_bundle_manifest.jsonl"
_DEFAULT_OUTPUT = "runs/paper_lab/m458_daily_preview_archive_index.jsonl"

_STRICT_SAFETY_FIELDS = [
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
]


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPreviewArchiveIndexConfig:
    """Configuration for M458 offline daily preview archive index command."""

    input_run_index_path: Path | str = _DEFAULT_INPUT_M453
    input_manifest_health_path: Path | str = _DEFAULT_INPUT_M454
    input_dashboard_packet_path: Path | str = _DEFAULT_INPUT_M455
    input_text_export_manifest_path: Path | str = _DEFAULT_INPUT_M456_JSONL
    input_text_export_path: Path | str = _DEFAULT_INPUT_M456_TXT
    input_bundle_manifest_path: Path | str = _DEFAULT_INPUT_M457
    output_archive_index_path: Path | str = _DEFAULT_OUTPUT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_run_index_path",
            _required_path(self.input_run_index_path, "input_run_index_path"),
        )
        object.__setattr__(
            self,
            "input_manifest_health_path",
            _required_path(self.input_manifest_health_path, "input_manifest_health_path"),
        )
        object.__setattr__(
            self,
            "input_dashboard_packet_path",
            _required_path(self.input_dashboard_packet_path, "input_dashboard_packet_path"),
        )
        object.__setattr__(
            self,
            "input_text_export_manifest_path",
            _required_path(self.input_text_export_manifest_path, "input_text_export_manifest_path"),
        )
        object.__setattr__(
            self,
            "input_text_export_path",
            _required_path(self.input_text_export_path, "input_text_export_path"),
        )
        object.__setattr__(
            self,
            "input_bundle_manifest_path",
            _required_path(self.input_bundle_manifest_path, "input_bundle_manifest_path"),
        )
        object.__setattr__(
            self,
            "output_archive_index_path",
            _required_path(self.output_archive_index_path, "output_archive_index_path"),
        )


def run_etf_sma_daily_preview_archive_index(
    config: EtfSmaDailyPreviewArchiveIndexConfig,
) -> dict[str, Any]:
    """Execute validation of daily cycle artifacts and write exactly one JSONL record."""
    payload = build_etf_sma_daily_preview_archive_index(config)

    output_path = Path(config.output_archive_index_path)
    if output_path.parent != Path(".") and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Overwrite/truncate the output JSONL path. Do not append.
    line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    output_path.write_text(line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_preview_archive_index(
    config: EtfSmaDailyPreviewArchiveIndexConfig,
) -> dict[str, Any]:
    """Load preceding daily artifacts, validate, and construct M458 archive brief."""
    blockers: list[str] = []

    # Load JSONL records and collect stats
    m453_rec, stats_m453 = _load_record_and_stats(Path(config.input_run_index_path), blockers, "m453")
    m454_rec, stats_m454 = _load_record_and_stats(Path(config.input_manifest_health_path), blockers, "m454")
    m455_rec, stats_m455 = _load_record_and_stats(Path(config.input_dashboard_packet_path), blockers, "m455")
    m456_rec, stats_m456 = _load_record_and_stats(Path(config.input_text_export_manifest_path), blockers, "m456")
    m457_rec, stats_m457 = _load_record_and_stats(Path(config.input_bundle_manifest_path), blockers, "m457")

    # Load M456 Text Export stats and contents
    stats_m456_txt = _load_txt_stats(Path(config.input_text_export_path), blockers, "m456_text")
    m456_txt_lines: list[str] = []
    txt_path = Path(config.input_text_export_path)
    if txt_path.exists() and txt_path.is_file():
        try:
            txt_content = txt_path.read_text(encoding="utf-8")
            m456_txt_lines = [line.strip() for line in txt_content.splitlines()]
        except Exception:
            blockers.append("m456_text_error_reading")

    # Expected normalized paths
    expected_m453_path = _normalize_path(config.input_run_index_path)
    expected_m454_path = _normalize_path(config.input_manifest_health_path)
    expected_m455_path = _normalize_path(config.input_dashboard_packet_path)
    expected_m456_jsonl_path = _normalize_path(config.input_text_export_manifest_path)
    expected_m456_txt_path = _normalize_path(config.input_text_export_path)
    expected_m457_path = _normalize_path(config.input_bundle_manifest_path)
    expected_m458_path = _normalize_path(config.output_archive_index_path)

    # Validate M455
    if m455_rec:
        if m455_rec.get("milestone") != "M455":
            blockers.append("m455_milestone_mismatch")
        if m455_rec.get("phase") != "offline_daily_operator_dashboard_packet":
            blockers.append("m455_phase_mismatch")
        if m455_rec.get("command") != "etf-sma-daily-operator-dashboard-packet":
            blockers.append("m455_command_mismatch")
        if m455_rec.get("dashboard_state") != "ready":
            blockers.append("m455_dashboard_state_not_ready")
        if m455_rec.get("accepted_for_operator_observation") is not True:
            blockers.append("m455_not_accepted_for_observation")
        if m455_rec.get("source_run_index_milestone") != "M453":
            blockers.append("m455_source_run_index_milestone_mismatch")
        if m455_rec.get("source_manifest_health_milestone") != "M454":
            blockers.append("m455_source_manifest_health_milestone_mismatch")
        if m455_rec.get("source_run_index_state") != "ready":
            blockers.append("m455_source_run_index_state_not_ready")
        if m455_rec.get("source_manifest_health_state") != "ready":
            blockers.append("m455_source_manifest_health_state_not_ready")
        if m455_rec.get("latest_bar_date_consistent") is not True:
            blockers.append("m455_latest_bar_date_consistent_not_true")
        if m455_rec.get("operator_warning") != "preview_only_not_order_authorization":
            blockers.append("m455_operator_warning_mismatch")
        if "blockers" not in m455_rec:
            blockers.append("m455_blockers_missing")
        elif not isinstance(m455_rec["blockers"], list) or len(m455_rec["blockers"]) > 0:
            blockers.append("m455_blockers_not_empty")
        if "profit_claim" not in m455_rec:
            blockers.append("m455_profit_claim_missing")
        elif m455_rec["profit_claim"] != "none":
            blockers.append("m455_profit_claim_not_none")
        for field in _STRICT_SAFETY_FIELDS:
            _check_strict_safety_field(m455_rec, field, "m455", blockers)

    # Validate M456 manifest
    if m456_rec:
        if m456_rec.get("milestone") != "M456":
            blockers.append("m456_milestone_mismatch")
        if m456_rec.get("phase") != "offline_daily_dashboard_text_export":
            blockers.append("m456_phase_mismatch")
        if m456_rec.get("command") != "etf-sma-daily-dashboard-text-export":
            blockers.append("m456_command_mismatch")
        if m456_rec.get("export_state") != "ready":
            blockers.append("m456_export_state_not_ready")
        if m456_rec.get("accepted_for_operator_observation") is not True:
            blockers.append("m456_not_accepted_for_observation")
        if m456_rec.get("source_dashboard_milestone") != "M455":
            blockers.append("m456_source_dashboard_milestone_mismatch")
        if m456_rec.get("source_dashboard_state") != "ready":
            blockers.append("m456_source_dashboard_state_not_ready")
        if m456_rec.get("input_dashboard_packet_path") != expected_m455_path:
            blockers.append("m456_input_dashboard_packet_path_mismatch")
        if m456_rec.get("output_text_path") != expected_m456_txt_path:
            blockers.append("m456_output_text_path_mismatch")
        if m456_rec.get("operator_warning") != "preview_only_not_order_authorization":
            blockers.append("m456_operator_warning_mismatch")
        if "blockers" not in m456_rec:
            blockers.append("m456_blockers_missing")
        elif not isinstance(m456_rec["blockers"], list) or len(m456_rec["blockers"]) > 0:
            blockers.append("m456_blockers_not_empty")
        if "profit_claim" not in m456_rec:
            blockers.append("m456_profit_claim_missing")
        elif m456_rec["profit_claim"] != "none":
            blockers.append("m456_profit_claim_not_none")
        for field in _STRICT_SAFETY_FIELDS:
            _check_strict_safety_field(m456_rec, field, "m456", blockers)

    # Validate M456 text export lines and variables
    if m456_txt_lines:
        exact_text_lines = [
            "ETF/SMA Daily Operator Dashboard Export (M456)",
            "export_state: ready",
            "source M455 state: ready",
            "dashboard_state: ready",
            "source M453 state: ready",
            "source M454 state: ready",
            "latest_bar_date_consistent: true",
            "operator_warning: preview_only_not_order_authorization",
            "submitted=false",
            "mutated=false",
            "paper_submit_allowed=false",
            "live_submit_allowed=false",
            "scheduler_install_allowed=false",
            "order_authorization=false",
            "blockers=[]",
        ]
        for line in exact_text_lines:
            if line not in m456_txt_lines:
                blockers.append("m456_text_line_missing")
                break

        if m456_rec:
            dec_val = m456_rec.get("decision_summary")
            pos_val = m456_rec.get("posture_summary")
            cnt_val = m456_rec.get("checked_artifact_count")
            if f"decision_summary: {dec_val}" not in m456_txt_lines:
                blockers.append("m456_text_decision_summary_mismatch")
            if f"posture_summary: {pos_val}" not in m456_txt_lines:
                blockers.append("m456_text_posture_summary_mismatch")
            if f"checked_artifact_count: {cnt_val}" not in m456_txt_lines:
                blockers.append("m456_text_checked_artifact_count_mismatch")

    # Validate M457
    if m457_rec:
        if m457_rec.get("milestone") != "M457":
            blockers.append("m457_milestone_mismatch")
        if m457_rec.get("phase") != "offline_daily_dashboard_bundle_manifest":
            blockers.append("m457_phase_mismatch")
        if m457_rec.get("command") != "etf-sma-daily-dashboard-bundle-manifest":
            blockers.append("m457_command_mismatch")
        if m457_rec.get("bundle_state") != "ready":
            blockers.append("m457_bundle_state_not_ready")
        if m457_rec.get("accepted_for_operator_observation") is not True:
            blockers.append("m457_not_accepted_for_observation")
        if m457_rec.get("source_dashboard_milestone") != "M455":
            blockers.append("m457_source_dashboard_milestone_mismatch")
        if m457_rec.get("source_dashboard_state") != "ready":
            blockers.append("m457_source_dashboard_state_not_ready")
        if m457_rec.get("source_text_export_milestone") != "M456":
            blockers.append("m457_source_text_export_milestone_mismatch")
        if m457_rec.get("source_text_export_state") != "ready":
            blockers.append("m457_source_text_export_state_not_ready")
        if m457_rec.get("input_dashboard_packet_path") != expected_m455_path:
            blockers.append("m457_input_dashboard_packet_path_mismatch")
        if m457_rec.get("input_text_export_manifest_path") != expected_m456_jsonl_path:
            blockers.append("m457_input_text_export_manifest_path_mismatch")
        if m457_rec.get("input_text_export_path") != expected_m456_txt_path:
            blockers.append("m457_input_text_export_path_mismatch")
        if m457_rec.get("operator_warning") != "preview_only_not_order_authorization":
            blockers.append("m457_operator_warning_mismatch")
        if "blockers" not in m457_rec:
            blockers.append("m457_blockers_missing")
        elif not isinstance(m457_rec["blockers"], list) or len(m457_rec["blockers"]) > 0:
            blockers.append("m457_blockers_not_empty")
        if "profit_claim" not in m457_rec:
            blockers.append("m457_profit_claim_missing")
        elif m457_rec["profit_claim"] != "none":
            blockers.append("m457_profit_claim_not_none")
        for field in _STRICT_SAFETY_FIELDS:
            _check_strict_safety_field(m457_rec, field, "m457", blockers)

    # Cross-artifact validations
    if m455_rec and m456_rec:
        if m456_rec.get("source_dashboard_state") != m455_rec.get("dashboard_state"):
            blockers.append("m456_source_dashboard_state_mismatch")
        if m456_rec.get("operator_warning") != m455_rec.get("operator_warning"):
            blockers.append("m456_operator_warning_mismatch")
        if "decision_summary" in m455_rec and m455_rec["decision_summary"] is not None:
            if m456_rec.get("decision_summary") != m455_rec["decision_summary"]:
                blockers.append("m456_decision_summary_mismatch")
        if "posture_summary" in m455_rec and m455_rec["posture_summary"] is not None:
            if m456_rec.get("posture_summary") != m455_rec["posture_summary"]:
                blockers.append("m456_posture_summary_mismatch")
        if "checked_artifact_count" in m455_rec and m455_rec["checked_artifact_count"] is not None:
            if m456_rec.get("checked_artifact_count") != m455_rec["checked_artifact_count"]:
                blockers.append("m456_checked_artifact_count_mismatch")

    if m457_rec:
        if m455_rec and m457_rec.get("source_dashboard_state") != m455_rec.get("dashboard_state"):
            blockers.append("m457_source_dashboard_state_mismatch")
        if m456_rec and m457_rec.get("source_text_export_state") != m456_rec.get("export_state"):
            blockers.append("m457_source_text_export_state_mismatch")
        if m455_rec and m457_rec.get("operator_warning") != m455_rec.get("operator_warning"):
            blockers.append("m457_operator_warning_mismatch")
        if m456_rec and m457_rec.get("operator_warning") != m456_rec.get("operator_warning"):
            blockers.append("m457_operator_warning_mismatch")

    # Clean duplicates preserving order
    blockers = list(dict.fromkeys(blockers))

    # Error path
    if blockers:
        sorted_blockers = sorted(blockers)
        payload = {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "archive_state": "blocked_or_invalid",
            "accepted_for_operator_observation": False,
            "source_bundle_milestone": "M457",
            "source_bundle_state": m457_rec.get("bundle_state") if (m457_rec and m457_rec.get("bundle_state")) else "unknown",
            "source_dashboard_milestone": "M455",
            "source_dashboard_state": m455_rec.get("dashboard_state") if (m455_rec and m455_rec.get("dashboard_state")) else "unknown",
            "source_text_export_milestone": "M456",
            "source_text_export_state": m456_rec.get("export_state") if (m456_rec and m456_rec.get("export_state")) else "unknown",
            "input_run_index_path": expected_m453_path,
            "input_manifest_health_path": expected_m454_path,
            "input_dashboard_packet_path": expected_m455_path,
            "input_text_export_manifest_path": expected_m456_jsonl_path,
            "input_text_export_path": expected_m456_txt_path,
            "input_bundle_manifest_path": expected_m457_path,
            "output_archive_index_path": expected_m458_path,
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
            "blockers": sorted_blockers,
        }
        return payload

    # Success Path
    decision_summary = m457_rec.get("decision_summary")
    posture_summary = m457_rec.get("posture_summary")
    checked_artifact_count = m457_rec.get("checked_artifact_count")
    operator_warning = m457_rec.get("operator_warning")

    # Construct the deterministic workflow order list of archived artifacts
    archived_artifacts = [
        {
            "path": stats_m453["path"],
            "kind": "jsonl",
            "sha256": stats_m453["sha256"],
            "byte_size": stats_m453["byte_size"],
            "record_count": stats_m453["record_count"],
        },
        {
            "path": stats_m454["path"],
            "kind": "jsonl",
            "sha256": stats_m454["sha256"],
            "byte_size": stats_m454["byte_size"],
            "record_count": stats_m454["record_count"],
        },
        {
            "path": stats_m455["path"],
            "kind": "jsonl",
            "sha256": stats_m455["sha256"],
            "byte_size": stats_m455["byte_size"],
            "record_count": stats_m455["record_count"],
        },
        {
            "path": stats_m456["path"],
            "kind": "jsonl",
            "sha256": stats_m456["sha256"],
            "byte_size": stats_m456["byte_size"],
            "record_count": stats_m456["record_count"],
        },
        {
            "path": stats_m456_txt["path"],
            "kind": "txt",
            "sha256": stats_m456_txt["sha256"],
            "byte_size": stats_m456_txt["byte_size"],
        },
        {
            "path": stats_m457["path"],
            "kind": "jsonl",
            "sha256": stats_m457["sha256"],
            "byte_size": stats_m457["byte_size"],
            "record_count": stats_m457["record_count"],
        },
    ]

    payload = {
        "milestone": _MILESTONE,
        "phase": _PHASE,
        "command": _COMMAND,
        "archive_state": "ready",
        "accepted_for_operator_observation": True,
        "source_bundle_milestone": "M457",
        "source_bundle_state": "ready",
        "source_dashboard_milestone": "M455",
        "source_dashboard_state": "ready",
        "source_text_export_milestone": "M456",
        "source_text_export_state": "ready",
        "input_run_index_path": expected_m453_path,
        "input_manifest_health_path": expected_m454_path,
        "input_dashboard_packet_path": expected_m455_path,
        "input_text_export_manifest_path": expected_m456_jsonl_path,
        "input_text_export_path": expected_m456_txt_path,
        "input_bundle_manifest_path": expected_m457_path,
        "output_archive_index_path": expected_m458_path,
        "decision_summary": decision_summary,
        "posture_summary": posture_summary,
        "checked_artifact_count": checked_artifact_count,
        "operator_warning": operator_warning,
        "archived_artifact_count": len(archived_artifacts),
        "archived_artifacts": archived_artifacts,
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
    }

    return payload


def _normalize_path(path: Path | str) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
    return path


def _compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def _check_strict_safety_field(rec: dict[str, Any], field: str, prefix: str, blockers: list[str]) -> None:
    if field not in rec:
        blockers.append(f"{prefix}_{field}_missing")
        return
    val = rec[field]
    if not isinstance(val, bool) or val is not False:
        blockers.append(f"{prefix}_{field}_invalid_or_unsafe")


def _load_record_and_stats(
    path: Path, blockers: list[str], prefix: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    stats = {
        "path": _normalize_path(path),
        "sha256": "",
        "byte_size": 0,
        "record_count": 0,
    }
    if not path.exists() or not path.is_file():
        blockers.append(f"{prefix}_missing")
        return {}, stats

    try:
        stats["byte_size"] = path.stat().st_size
        stats["sha256"] = _compute_sha256(path)
    except Exception:
        blockers.append(f"{prefix}_error_reading")
        return {}, stats

    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        blockers.append(f"{prefix}_error_reading")
        return {}, stats

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    stats["record_count"] = len(lines)

    if len(lines) == 0:
        blockers.append(f"{prefix}_empty")
        return {}, stats
    if len(lines) > 1:
        blockers.append(f"{prefix}_record_count_not_one")
        return {}, stats

    try:
        rec = json.loads(lines[0])
        if not isinstance(rec, Mapping):
            blockers.append(f"{prefix}_malformed_json")
            return {}, stats
        return dict(rec), stats
    except json.JSONDecodeError:
        blockers.append(f"{prefix}_malformed_json")
        return {}, stats


def _load_txt_stats(path: Path, blockers: list[str], prefix: str) -> dict[str, Any]:
    stats = {
        "path": _normalize_path(path),
        "sha256": "",
        "byte_size": 0,
    }
    if not path.exists() or not path.is_file():
        blockers.append(f"{prefix}_missing")
        return stats

    try:
        stats["byte_size"] = path.stat().st_size
        stats["sha256"] = _compute_sha256(path)
    except Exception:
        blockers.append(f"{prefix}_error_reading")
        return stats
    return stats
