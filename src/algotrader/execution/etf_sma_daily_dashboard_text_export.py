"""Offline daily dashboard text export for Milestone M456.

This module validates the M455 daily operator dashboard packet
and outputs a deterministic text export and a JSONL manifest record.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyDashboardTextExportConfig",
    "run_etf_sma_daily_dashboard_text_export",
    "build_etf_sma_daily_dashboard_text_export",
]

_MILESTONE = "M456"
_PHASE = "offline_daily_dashboard_text_export"
_COMMAND = "etf-sma-daily-dashboard-text-export"

_DEFAULT_INPUT = "runs/paper_lab/m455_daily_operator_dashboard_packet.jsonl"
_DEFAULT_TEXT_OUTPUT = "runs/paper_lab/m456_daily_dashboard_text_export.txt"
_DEFAULT_MANIFEST_OUTPUT = "runs/paper_lab/m456_daily_dashboard_text_export.jsonl"

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
class EtfSmaDailyDashboardTextExportConfig:
    """Configuration for M456 offline daily dashboard text export command."""

    input_dashboard_packet_path: Path | str = _DEFAULT_INPUT
    output_text_path: Path | str = _DEFAULT_TEXT_OUTPUT
    output_manifest_path: Path | str = _DEFAULT_MANIFEST_OUTPUT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_dashboard_packet_path",
            _required_path(self.input_dashboard_packet_path, "input_dashboard_packet_path"),
        )
        object.__setattr__(
            self,
            "output_text_path",
            _required_path(self.output_text_path, "output_text_path"),
        )
        object.__setattr__(
            self,
            "output_manifest_path",
            _required_path(self.output_manifest_path, "output_manifest_path"),
        )


def run_etf_sma_daily_dashboard_text_export(
    config: EtfSmaDailyDashboardTextExportConfig,
) -> dict[str, Any]:
    """Execute validation of M455, write text export and JSONL manifest."""
    payload, text_content = build_etf_sma_daily_dashboard_text_export(config)

    output_text_p = Path(config.output_text_path)
    if output_text_p.parent != Path(".") and not output_text_p.parent.exists():
        output_text_p.parent.mkdir(parents=True, exist_ok=True)

    output_manifest_p = Path(config.output_manifest_path)
    if output_manifest_p.parent != Path(".") and not output_manifest_p.parent.exists():
        output_manifest_p.parent.mkdir(parents=True, exist_ok=True)

    # Overwrite/truncate existing files
    output_text_p.write_text(text_content, encoding="utf-8", newline="\n")
    manifest_line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    output_manifest_p.write_text(manifest_line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_dashboard_text_export(
    config: EtfSmaDailyDashboardTextExportConfig,
) -> tuple[dict[str, Any], str]:
    """Load, validate M455 dashboard packet, and build manifest payload and text content."""
    blockers: list[str] = []

    m455_rec = _load_record(Path(config.input_dashboard_packet_path), blockers)

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
            _check_strict_safety_field(m455_rec, field, blockers)

    blockers = list(dict.fromkeys(blockers))

    if blockers:
        sorted_blockers = sorted(blockers)
        payload = {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "export_state": "blocked_or_invalid",
            "accepted_for_operator_observation": False,
            "source_dashboard_milestone": "M455",
            "source_dashboard_state": m455_rec.get("dashboard_state") if m455_rec else "unknown",
            "input_dashboard_packet_path": _normalize_path(config.input_dashboard_packet_path),
            "output_text_path": _normalize_path(config.output_text_path),
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
        
        blockers_str = json.dumps(sorted_blockers)
        text_content = (
            "ETF/SMA Daily Operator Dashboard Export (M456)\n"
            "==============================================\n"
            "export_state: blocked_or_invalid\n"
            "submitted=false\n"
            "mutated=false\n"
            "paper_submit_allowed=false\n"
            "live_submit_allowed=false\n"
            "scheduler_install_allowed=false\n"
            f"blockers={blockers_str}\n"
        )
        return payload, text_content

    # Success Path
    decision_summary = m455_rec.get("decision_summary")
    posture_summary = m455_rec.get("posture_summary")
    checked_artifact_count = m455_rec.get("checked_artifact_count")

    payload = {
        "milestone": _MILESTONE,
        "phase": _PHASE,
        "command": _COMMAND,
        "export_state": "ready",
        "accepted_for_operator_observation": True,
        "source_dashboard_milestone": "M455",
        "source_dashboard_state": "ready",
        "input_dashboard_packet_path": _normalize_path(config.input_dashboard_packet_path),
        "output_text_path": _normalize_path(config.output_text_path),
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

    text_content = (
        "ETF/SMA Daily Operator Dashboard Export (M456)\n"
        "==============================================\n"
        "export_state: ready\n"
        "source M455 state: ready\n"
        f"dashboard_state: {m455_rec.get('dashboard_state')}\n"
        f"source M453 state: {m455_rec.get('source_run_index_state')}\n"
        f"source M454 state: {m455_rec.get('source_manifest_health_state')}\n"
        f"latest_bar_date_consistent: {str(m455_rec.get('latest_bar_date_consistent')).lower()}\n"
        f"operator_warning: {m455_rec.get('operator_warning')}\n"
        f"decision_summary: {decision_summary}\n"
        f"posture_summary: {posture_summary}\n"
        f"checked_artifact_count: {checked_artifact_count}\n"
        "submitted=false\n"
        "mutated=false\n"
        "paper_submit_allowed=false\n"
        "live_submit_allowed=false\n"
        "scheduler_install_allowed=false\n"
        "order_authorization=false\n"
        "blockers=[]\n"
    )

    return payload, text_content


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


def _check_strict_safety_field(rec: dict[str, Any], field: str, blockers: list[str]) -> None:
    if field not in rec:
        blockers.append(f"m455_{field}_missing")
        return
    val = rec[field]
    if not isinstance(val, bool) or val is not False:
        blockers.append(f"m455_{field}_invalid_or_unsafe")


def _load_record(path: Path, blockers: list[str]) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        blockers.append("m455_missing")
        return {}
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        blockers.append("m455_error_reading")
        return {}
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) == 0:
        blockers.append("m455_empty")
        return {}
    if len(lines) > 1:
        blockers.append("m455_record_count_not_one")
        return {}
    try:
        rec = json.loads(lines[0])
        if not isinstance(rec, Mapping):
            blockers.append("m455_malformed_json")
            return {}
        return dict(rec)
    except json.JSONDecodeError:
        blockers.append("m455_malformed_json")
        return {}
