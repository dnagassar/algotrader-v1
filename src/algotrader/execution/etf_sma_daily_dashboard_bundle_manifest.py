"""Offline daily dashboard bundle manifest for Milestone M457.

This module validates the accepted M455 daily operator dashboard packet,
the accepted M456 daily dashboard text export manifest, and the M456
dashboard text export itself. It then writes a single JSONL bundle manifest.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyDashboardBundleManifestConfig",
    "run_etf_sma_daily_dashboard_bundle_manifest",
    "build_etf_sma_daily_dashboard_bundle_manifest",
]

_MILESTONE = "M457"
_PHASE = "offline_daily_dashboard_bundle_manifest"
_COMMAND = "etf-sma-daily-dashboard-bundle-manifest"

_DEFAULT_INPUT_M455 = "runs/paper_lab/m455_daily_operator_dashboard_packet.jsonl"
_DEFAULT_INPUT_M456_JSONL = "runs/paper_lab/m456_daily_dashboard_text_export.jsonl"
_DEFAULT_INPUT_M456_TXT = "runs/paper_lab/m456_daily_dashboard_text_export.txt"
_DEFAULT_MANIFEST_OUTPUT = "runs/paper_lab/m457_daily_dashboard_bundle_manifest.jsonl"

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
class EtfSmaDailyDashboardBundleManifestConfig:
    """Configuration for M457 offline daily dashboard bundle manifest command."""

    input_dashboard_packet_path: Path | str = _DEFAULT_INPUT_M455
    input_text_export_manifest_path: Path | str = _DEFAULT_INPUT_M456_JSONL
    input_text_export_path: Path | str = _DEFAULT_INPUT_M456_TXT
    output_manifest_path: Path | str = _DEFAULT_MANIFEST_OUTPUT

    def __post_init__(self) -> None:
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
            "output_manifest_path",
            _required_path(self.output_manifest_path, "output_manifest_path"),
        )


def run_etf_sma_daily_dashboard_bundle_manifest(
    config: EtfSmaDailyDashboardBundleManifestConfig,
) -> dict[str, Any]:
    """Execute validation of M455 and M456, and write bundle manifest."""
    payload = build_etf_sma_daily_dashboard_bundle_manifest(config)

    output_manifest_p = Path(config.output_manifest_path)
    if output_manifest_p.parent != Path(".") and not output_manifest_p.parent.exists():
        output_manifest_p.parent.mkdir(parents=True, exist_ok=True)

    # Overwrite/truncate the output JSONL path. Do not append.
    manifest_line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    output_manifest_p.write_text(manifest_line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_dashboard_bundle_manifest(
    config: EtfSmaDailyDashboardBundleManifestConfig,
) -> dict[str, Any]:
    """Load and validate inputs, and construct M457 manifest payload."""
    blockers: list[str] = []

    m455_rec = _load_record(Path(config.input_dashboard_packet_path), "m455", blockers)
    m456_rec = _load_record(Path(config.input_text_export_manifest_path), "m456_manifest", blockers)

    txt_path = Path(config.input_text_export_path)
    m456_txt_lines: list[str] = []
    if not txt_path.exists() or not txt_path.is_file():
        blockers.append("m456_text_missing")
    else:
        try:
            txt_content = txt_path.read_text(encoding="utf-8")
            m456_txt_lines = [line.strip() for line in txt_content.splitlines()]
        except Exception:
            blockers.append("m456_text_error_reading")

    # M455 validation
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

    # M456 JSONL validation
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

        expected_normalized_input_path = _normalize_path(config.input_dashboard_packet_path)
        if m456_rec.get("input_dashboard_packet_path") != expected_normalized_input_path:
            blockers.append("m456_input_path_mismatch")

        expected_normalized_output_text_path = _normalize_path(config.input_text_export_path)
        if m456_rec.get("output_text_path") != expected_normalized_output_text_path:
            blockers.append("m456_output_text_path_mismatch")

        for field in _STRICT_SAFETY_FIELDS:
            _check_strict_safety_field(m456_rec, field, "m456", blockers)

    # Cross-artifact validation
    if m455_rec and m456_rec:
        if "decision_summary" in m455_rec and m455_rec["decision_summary"] is not None:
            if m456_rec.get("decision_summary") != m455_rec["decision_summary"]:
                blockers.append("m456_decision_summary_mismatch")
        if "posture_summary" in m455_rec and m455_rec["posture_summary"] is not None:
            if m456_rec.get("posture_summary") != m455_rec["posture_summary"]:
                blockers.append("m456_posture_summary_mismatch")
        if "checked_artifact_count" in m455_rec and m455_rec["checked_artifact_count"] is not None:
            if m456_rec.get("checked_artifact_count") != m455_rec["checked_artifact_count"]:
                blockers.append("m456_checked_artifact_count_mismatch")
        if m456_rec.get("operator_warning") != m455_rec.get("operator_warning"):
            blockers.append("m456_operator_warning_mismatch")
        if m456_rec.get("source_dashboard_state") != m455_rec.get("dashboard_state"):
            blockers.append("m456_source_dashboard_state_mismatch")

    # M456 text export validation
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

    blockers = list(dict.fromkeys(blockers))

    if blockers:
        sorted_blockers = sorted(blockers)
        payload = {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "bundle_state": "blocked_or_invalid",
            "accepted_for_operator_observation": False,
            "source_dashboard_milestone": "M455",
            "source_dashboard_state": m455_rec.get("dashboard_state") if (m455_rec and m455_rec.get("dashboard_state")) else "unknown",
            "source_text_export_milestone": "M456",
            "source_text_export_state": m456_rec.get("export_state") if (m456_rec and m456_rec.get("export_state")) else "unknown",
            "input_dashboard_packet_path": _normalize_path(config.input_dashboard_packet_path),
            "input_text_export_manifest_path": _normalize_path(config.input_text_export_manifest_path),
            "input_text_export_path": _normalize_path(config.input_text_export_path),
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
    decision_summary = m456_rec.get("decision_summary")
    posture_summary = m456_rec.get("posture_summary")
    checked_artifact_count = m456_rec.get("checked_artifact_count")

    payload = {
        "milestone": _MILESTONE,
        "phase": _PHASE,
        "command": _COMMAND,
        "bundle_state": "ready",
        "accepted_for_operator_observation": True,
        "source_dashboard_milestone": "M455",
        "source_dashboard_state": "ready",
        "source_text_export_milestone": "M456",
        "source_text_export_state": "ready",
        "input_dashboard_packet_path": _normalize_path(config.input_dashboard_packet_path),
        "input_text_export_manifest_path": _normalize_path(config.input_text_export_manifest_path),
        "input_text_export_path": _normalize_path(config.input_text_export_path),
        "decision_summary": decision_summary,
        "posture_summary": posture_summary,
        "checked_artifact_count": checked_artifact_count,
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


def _check_strict_safety_field(rec: dict[str, Any], field: str, prefix: str, blockers: list[str]) -> None:
    if field not in rec:
        blockers.append(f"{prefix}_{field}_missing")
        return
    val = rec[field]
    if not isinstance(val, bool) or val is not False:
        blockers.append(f"{prefix}_{field}_invalid_or_unsafe")


def _load_record(path: Path, prefix: str, blockers: list[str]) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        blockers.append(f"{prefix}_missing")
        return {}
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        blockers.append(f"{prefix}_error_reading")
        return {}
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) == 0:
        blockers.append(f"{prefix}_empty")
        return {}
    if len(lines) > 1:
        blockers.append(f"{prefix}_record_count_not_one")
        return {}
    try:
        rec = json.loads(lines[0])
        if not isinstance(rec, Mapping):
            blockers.append(f"{prefix}_malformed_json")
            return {}
        return dict(rec)
    except json.JSONDecodeError:
        blockers.append(f"{prefix}_malformed_json")
        return {}
