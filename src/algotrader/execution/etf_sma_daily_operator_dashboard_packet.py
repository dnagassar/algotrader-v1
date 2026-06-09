"""Offline daily operator dashboard packet for Milestone M455.

This module validates the M453 daily run index and the M454 daily artifact manifest health check
and outputs exactly one JSONL record summarizing the ETF/SMA daily observation posture.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyOperatorDashboardPacketConfig",
    "run_etf_sma_daily_operator_dashboard_packet",
    "build_etf_sma_daily_operator_dashboard_packet",
    "render_etf_sma_daily_operator_dashboard_packet_json",
    "render_etf_sma_daily_operator_dashboard_packet_text",
]

_MILESTONE = "M455"
_PHASE = "offline_daily_operator_dashboard_packet"
_COMMAND = "etf-sma-daily-operator-dashboard-packet"

_DEFAULT_RUN_INDEX = "runs/paper_lab/m453_daily_run_index.jsonl"
_DEFAULT_MANIFEST_HEALTH = "runs/paper_lab/m454_daily_artifact_manifest_health.jsonl"
_DEFAULT_OUTPUT = "runs/paper_lab/m455_daily_operator_dashboard_packet.jsonl"

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
class EtfSmaDailyOperatorDashboardPacketConfig:
    """Configuration for M455 Daily Operator Dashboard Packet command."""

    run_index_jsonl: Path | str = _DEFAULT_RUN_INDEX
    manifest_health_jsonl: Path | str = _DEFAULT_MANIFEST_HEALTH
    output_jsonl: Path | str = _DEFAULT_OUTPUT

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_index_jsonl", _required_path(self.run_index_jsonl, "run_index_jsonl"))
        object.__setattr__(
            self,
            "manifest_health_jsonl",
            _required_path(self.manifest_health_jsonl, "manifest_health_jsonl"),
        )
        object.__setattr__(self, "output_jsonl", _required_path(self.output_jsonl, "output_jsonl"))


def run_etf_sma_daily_operator_dashboard_packet(
    config: EtfSmaDailyOperatorDashboardPacketConfig,
) -> dict[str, Any]:
    """Execute validation of M453 and M454 and write exactly one JSONL record."""
    payload = build_etf_sma_daily_operator_dashboard_packet(config)

    output_path = Path(config.output_jsonl)
    if output_path.parent != Path(".") and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    line = render_etf_sma_daily_operator_dashboard_packet_json(payload) + "\n"
    output_path.write_text(line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_operator_dashboard_packet(
    config: EtfSmaDailyOperatorDashboardPacketConfig,
) -> dict[str, Any]:
    """Load inputs, validate safety booleans, and construct M455 dashboard packet."""
    blockers: list[str] = []

    m453_rec = _load_record(Path(config.run_index_jsonl), blockers, "m453")
    m454_rec = _load_record(Path(config.manifest_health_jsonl), blockers, "m454")

    # M453 Validation
    if m453_rec:
        if m453_rec.get("milestone") != "M453":
            blockers.append("m453_milestone_mismatch")
        if m453_rec.get("daily_run_index_state") != "ready":
            blockers.append("m453_run_index_state_not_ready")
        if m453_rec.get("accepted_for_operator_observation") is not True:
            blockers.append("m453_not_accepted_for_observation")
        if "blockers" not in m453_rec:
            blockers.append("m453_blockers_missing")
        elif not isinstance(m453_rec["blockers"], list) or len(m453_rec["blockers"]) > 0:
            blockers.append("m453_blockers_not_empty")
        if m453_rec.get("profit_claim") != "none":
            blockers.append("m453_profit_claim_not_none")
        if "command" in m453_rec and m453_rec["command"] != "etf-sma-daily-run-index":
            blockers.append("m453_command_mismatch")

        for field in _STRICT_SAFETY_FIELDS:
            _check_strict_safety_field(m453_rec, field, "m453", blockers)

    # M454 Validation
    if m454_rec:
        if m454_rec.get("milestone") != "M454":
            blockers.append("m454_milestone_mismatch")
        if m454_rec.get("command") != "etf-sma-daily-artifact-manifest-health":
            blockers.append("m454_command_mismatch")
        if m454_rec.get("manifest_health_state") != "ready":
            blockers.append("m454_manifest_health_state_not_ready")
        if m454_rec.get("accepted_for_operator_observation") is not True:
            blockers.append("m454_not_accepted_for_observation")
        if m454_rec.get("source_run_index_milestone") != "M453":
            blockers.append("m454_source_run_index_milestone_mismatch")
        if m454_rec.get("source_run_index_state") != "ready":
            blockers.append("m454_source_run_index_state_not_ready")
        if m454_rec.get("latest_bar_date_consistent") is not True:
            blockers.append("m454_latest_bar_date_consistent_not_true")
        if m454_rec.get("text_warning_present") is not True:
            blockers.append("m454_text_warning_present_not_true")
        if m454_rec.get("operator_warning") != "preview_only_not_order_authorization":
            blockers.append("m454_operator_warning_mismatch")
        if "blockers" not in m454_rec:
            blockers.append("m454_blockers_missing")
        elif not isinstance(m454_rec["blockers"], list) or len(m454_rec["blockers"]) > 0:
            blockers.append("m454_blockers_not_empty")
        if m454_rec.get("profit_claim") != "none":
            blockers.append("m454_profit_claim_not_none")

        for field in _STRICT_SAFETY_FIELDS:
            _check_strict_safety_field(m454_rec, field, "m454", blockers)

    blockers = list(dict.fromkeys(blockers))

    source_artifacts = {
        "M453": _normalize_path(config.run_index_jsonl),
        "M454": _normalize_path(config.manifest_health_jsonl),
    }

    if blockers:
        return {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "dashboard_state": "blocked_or_invalid",
            "accepted_for_operator_observation": False,
            "source_run_index_milestone": "M453",
            "source_manifest_health_milestone": "M454",
            "source_run_index_state": m453_rec.get("daily_run_index_state") if m453_rec else "unknown",
            "source_manifest_health_state": m454_rec.get("manifest_health_state") if m454_rec else "unknown",
            "latest_bar_date_consistent": m454_rec.get("latest_bar_date_consistent") if (m454_rec and "latest_bar_date_consistent" in m454_rec) else False,
            "operator_warning": "preview_only_not_order_authorization",
            "source_artifacts": source_artifacts,
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
            "blockers": blockers,
        }

    # Derive fields from M453 & M454 (strictly from artifacts)
    decision_summary = m453_rec.get("cycle_decision")
    posture_summary = m453_rec.get("posture")
    artifact_health_summary = m454_rec.get("checked_artifacts")
    checked_artifact_count = len(artifact_health_summary) if isinstance(artifact_health_summary, dict) else 0

    return {
        "milestone": _MILESTONE,
        "phase": _PHASE,
        "command": _COMMAND,
        "dashboard_state": "ready",
        "accepted_for_operator_observation": True,
        "source_run_index_milestone": "M453",
        "source_manifest_health_milestone": "M454",
        "source_run_index_state": m453_rec.get("daily_run_index_state"),
        "source_manifest_health_state": m454_rec.get("manifest_health_state"),
        "latest_bar_date_consistent": m454_rec.get("latest_bar_date_consistent"),
        "operator_warning": "preview_only_not_order_authorization",
        "decision_summary": decision_summary,
        "posture_summary": posture_summary,
        "artifact_health_summary": artifact_health_summary,
        "checked_artifact_count": checked_artifact_count,
        "source_artifacts": source_artifacts,
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


def render_etf_sma_daily_operator_dashboard_packet_text(payload: dict[str, Any]) -> str:
    """Render the payload into a deterministic text brief summary."""
    state = payload.get("dashboard_state")
    if state == "blocked_or_invalid":
        blockers_str = ", ".join(payload.get("blockers", []))
        return (
            "ETF/SMA Daily Operator Dashboard Packet (M455) - BLOCKED OR INVALID\n"
            "===================================================================\n"
            f"milestone: {payload.get('milestone')}\n"
            f"dashboard state: {state}\n"
            f"M453 source state: {payload.get('source_run_index_state')}\n"
            f"M454 source state: {payload.get('source_manifest_health_state')}\n"
            f"latest-bar consistency: {payload.get('latest_bar_date_consistent')}\n"
            f"warning: {payload.get('operator_warning')}\n"
            f"submitted={str(payload.get('submitted')).lower()}\n"
            f"mutated={str(payload.get('mutated')).lower()}\n"
            f"paper_submit_allowed={str(payload.get('paper_submit_allowed')).lower()}\n"
            f"live_submit_allowed={str(payload.get('live_submit_allowed')).lower()}\n"
            f"blockers: {blockers_str}\n"
        )
    return (
        "ETF/SMA Daily Operator Dashboard Packet (M455) - READY FOR OBSERVATION\n"
        "=======================================================================\n"
        f"milestone: {payload.get('milestone')}\n"
        f"dashboard state: {state}\n"
        f"M453 source state: {payload.get('source_run_index_state')}\n"
        f"M454 source state: {payload.get('source_manifest_health_state')}\n"
        f"latest-bar consistency: {payload.get('latest_bar_date_consistent')}\n"
        f"warning: {payload.get('operator_warning')}\n"
        f"submitted={str(payload.get('submitted')).lower()}\n"
        f"mutated={str(payload.get('mutated')).lower()}\n"
        f"paper_submit_allowed={str(payload.get('paper_submit_allowed')).lower()}\n"
        f"live_submit_allowed={str(payload.get('live_submit_allowed')).lower()}\n"
    )


def render_etf_sma_daily_operator_dashboard_packet_json(payload: Mapping[str, Any]) -> str:
    """Render the payload dict to a deterministic compact JSON string."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


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


def _load_record(path: Path, blockers: list[str], prefix: str) -> dict[str, Any]:
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


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
