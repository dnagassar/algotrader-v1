"""Offline daily artifact manifest health check for Milestone M454.

This module validates all daily paper-lab artifacts (M447 through M453),
verifies their presence, shapes, SHA256 hashes, sizes, safety flags, M451 txt warning,
M453 readiness, date consistency, and outputs exactly one JSONL health-check artifact.
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
    "EtfSmaDailyArtifactManifestHealthConfig",
    "run_etf_sma_daily_artifact_manifest_health",
    "build_etf_sma_daily_artifact_manifest_health",
    "render_etf_sma_daily_artifact_manifest_health_json",
    "render_etf_sma_daily_artifact_manifest_health_text",
]

_MILESTONE = "M454"
_PHASE = "offline_daily_artifact_manifest_health"
_COMMAND = "etf-sma-daily-artifact-manifest-health"

_DEFAULT_M447 = "runs/paper_lab/m447_offline_daily_cycle_m446_rerun_manifest.jsonl"
_DEFAULT_M448 = "runs/paper_lab/m448_refreshed_current_cycle_rollup.jsonl"
_DEFAULT_M449 = "runs/paper_lab/m449_preview_only_daily_run_packet.jsonl"
_DEFAULT_M450 = "runs/paper_lab/m450_daily_preview_pipeline_manifest.jsonl"
_DEFAULT_M451_SUMMARY = "runs/paper_lab/m451_daily_operator_brief_summary.jsonl"
_DEFAULT_M451_TXT = "runs/paper_lab/m451_daily_operator_brief.txt"
_DEFAULT_M452 = "runs/paper_lab/m452_daily_acceptance_gate_packet.jsonl"
_DEFAULT_M453 = "runs/paper_lab/m453_daily_run_index.jsonl"
_DEFAULT_OUTPUT = "runs/paper_lab/m454_daily_artifact_manifest_health.jsonl"


@dataclass(frozen=True, slots=True)
class EtfSmaDailyArtifactManifestHealthConfig:
    """Configuration for M454 Daily Artifact Manifest Health Check command."""

    m447_jsonl: Path | str = _DEFAULT_M447
    m448_jsonl: Path | str = _DEFAULT_M448
    m449_jsonl: Path | str = _DEFAULT_M449
    m450_jsonl: Path | str = _DEFAULT_M450
    m451_summary_jsonl: Path | str = _DEFAULT_M451_SUMMARY
    m451_txt: Path | str = _DEFAULT_M451_TXT
    m452_jsonl: Path | str = _DEFAULT_M452
    m453_jsonl: Path | str = _DEFAULT_M453
    output_jsonl: Path | str = _DEFAULT_OUTPUT

    def __post_init__(self) -> None:
        object.__setattr__(self, "m447_jsonl", _required_path(self.m447_jsonl, "m447_jsonl"))
        object.__setattr__(self, "m448_jsonl", _required_path(self.m448_jsonl, "m448_jsonl"))
        object.__setattr__(self, "m449_jsonl", _required_path(self.m449_jsonl, "m449_jsonl"))
        object.__setattr__(self, "m450_jsonl", _required_path(self.m450_jsonl, "m450_jsonl"))
        object.__setattr__(
            self,
            "m451_summary_jsonl",
            _required_path(self.m451_summary_jsonl, "m451_summary_jsonl"),
        )
        object.__setattr__(self, "m451_txt", _required_path(self.m451_txt, "m451_txt"))
        object.__setattr__(self, "m452_jsonl", _required_path(self.m452_jsonl, "m452_jsonl"))
        object.__setattr__(self, "m453_jsonl", _required_path(self.m453_jsonl, "m453_jsonl"))
        object.__setattr__(self, "output_jsonl", _required_path(self.output_jsonl, "output_jsonl"))


def run_etf_sma_daily_artifact_manifest_health(
    config: EtfSmaDailyArtifactManifestHealthConfig,
) -> dict[str, Any]:
    """Execute validation of all preceding daily cycle artifacts and write exactly one JSONL record."""
    payload = build_etf_sma_daily_artifact_manifest_health(config)

    output_path = Path(config.output_jsonl)
    if output_path.parent != Path(".") and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    line = render_etf_sma_daily_artifact_manifest_health_json(payload) + "\n"
    output_path.write_text(line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_artifact_manifest_health(
    config: EtfSmaDailyArtifactManifestHealthConfig,
) -> dict[str, Any]:
    """Load preceding daily artifacts, perform safety validation checks, and build the M454 health brief."""
    blockers: list[str] = []

    # Load JSONL records and collect their metrics
    m447_rec, stats_m447 = _load_record_and_stats(Path(config.m447_jsonl), blockers, "m447")
    m448_rec, stats_m448 = _load_record_and_stats(Path(config.m448_jsonl), blockers, "m448")
    m449_rec, stats_m449 = _load_record_and_stats(Path(config.m449_jsonl), blockers, "m449")
    m450_rec, stats_m450 = _load_record_and_stats(Path(config.m450_jsonl), blockers, "m450")
    m451_summary_rec, stats_m451 = _load_record_and_stats(
        Path(config.m451_summary_jsonl), blockers, "m451"
    )
    m452_rec, stats_m452 = _load_record_and_stats(Path(config.m452_jsonl), blockers, "m452")
    m453_rec, stats_m453 = _load_record_and_stats(Path(config.m453_jsonl), blockers, "m453")

    # Load M451 text brief operator warning validation
    stats_m451_txt = _load_txt_stats(Path(config.m451_txt), blockers, "m451_txt")
    text_warning_present = False
    brief_txt_path = Path(config.m451_txt)
    if brief_txt_path.exists() and brief_txt_path.is_file():
        try:
            txt_content = brief_txt_path.read_text(encoding="utf-8")
            if (
                "preview_only_not_order_authorization" in txt_content
                or "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders."
                in txt_content
            ):
                text_warning_present = True
            else:
                blockers.append("m451_txt_warning_missing")
        except Exception:
            blockers.append("m451_txt_warning_missing")
    else:
        # _load_txt_stats already added missing blocker
        pass

    # Safety checks definition (boolean flags)
    boolean_strict_safety_fields = [
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

    boolean_optional_safety_fields = [
        "submit_authorized",
        "paper_submit_authorized",
        "paper_action_authorized",
    ]

    # Verify legacy artifacts vs strict modern artifacts
    legacy_artifacts = [
        ("M447", m447_rec),
        ("M448", m448_rec),
        ("M449", m449_rec),
        ("M450", m450_rec),
        ("M451", m451_summary_rec),
    ]
    strict_artifacts = [
        ("M452", m452_rec),
        ("M453", m453_rec),
    ]

    # Legacy artifacts checks: block if fields exist and affirmatively indicate safety issues
    for name, rec in legacy_artifacts:
        if rec:
            for field in boolean_strict_safety_fields + boolean_optional_safety_fields:
                if field in rec and rec[field] is not False and rec[field] is not None:
                    blockers.append(f"{name.lower()}_{field}_not_false")
            if "profit_claim" in rec and rec["profit_claim"] != "none":
                blockers.append(f"{name.lower()}_profit_claim_not_none")

    # Strict artifacts checks: field must exist and must be False
    for name, rec in strict_artifacts:
        if rec:
            for field in boolean_strict_safety_fields:
                if field not in rec:
                    blockers.append(f"{name.lower()}_{field}_missing")
                elif rec[field] is not False:
                    blockers.append(f"{name.lower()}_{field}_not_false")
            for field in boolean_optional_safety_fields:
                if field in rec and rec[field] is not False and rec[field] is not None:
                    blockers.append(f"{name.lower()}_{field}_not_false")
            if "profit_claim" not in rec:
                blockers.append(f"{name.lower()}_profit_claim_missing")
            elif rec["profit_claim"] != "none":
                blockers.append(f"{name.lower()}_profit_claim_not_none")

    # Validate M450 stages run / validated
    if m450_rec:
        if m450_rec.get("milestone") != "M450":
            blockers.append("m450_milestone_mismatch")
        stages_run = m450_rec.get("stages_run")
        if stages_run is not None:
            if (
                not isinstance(stages_run, list)
                or "M447" not in stages_run
                or "M448" not in stages_run
                or "M449" not in stages_run
            ):
                blockers.append("m450_stages_run_invalid")
        stages_val = m450_rec.get("stages_validated")
        if stages_val is not None:
            if (
                not isinstance(stages_val, list)
                or "M447" not in stages_val
                or "M448" not in stages_val
                or "M449" not in stages_val
            ):
                blockers.append("m450_stages_validated_invalid")

    # Validate M451 Summary schema
    if m451_summary_rec:
        # Validate schema-supported indicator of ready status
        if "brief_state" in m451_summary_rec:
            if m451_summary_rec["brief_state"] != "ready":
                blockers.append("m451_brief_state_not_ready")

    # Validate M452 Gate fields
    if m452_rec:
        if m452_rec.get("acceptance_gate_state") != "accepted_for_preview_only_observation":
            blockers.append("m452_acceptance_gate_state_not_accepted")
        if m452_rec.get("accepted_for_operator_observation") is not True:
            blockers.append("m452_not_accepted_for_observation")

    # Validate M453 Run Index fields
    if m453_rec:
        if m453_rec.get("milestone") != "M453":
            blockers.append("m453_milestone_mismatch")
        if m453_rec.get("phase") != "offline_daily_run_index":
            blockers.append("m453_phase_mismatch")
        if m453_rec.get("command") != "etf-sma-daily-run-index":
            blockers.append("m453_command_mismatch")
        if m453_rec.get("daily_run_index_state") != "ready":
            blockers.append("m453_run_index_state_not_ready")
        if m453_rec.get("accepted_for_operator_observation") is not True:
            blockers.append("m453_not_accepted_for_observation")
        if m453_rec.get("operator_warning") != "preview_only_not_order_authorization":
            blockers.append("m453_operator_warning_unexpected")
        if m453_rec.get("text_warning_present") is not True:
            blockers.append("m453_text_warning_not_true")
        m453_blockers = m453_rec.get("blockers")
        if not isinstance(m453_blockers, list) or len(m453_blockers) > 0:
            blockers.append("m453_blockers_not_empty")

    # Cross-artifact latest-bar-date consistency where fields exist
    dates = []
    for rec in [
        m447_rec,
        m448_rec,
        m449_rec,
        m450_rec,
        m451_summary_rec,
        m452_rec,
        m453_rec,
    ]:
        if rec:
            for k in ("expected_latest_bar_date", "latest_local_bar_date"):
                if k in rec and rec[k] is not None:
                    dates.append(str(rec[k]).strip())

    latest_bar_date_consistent = True
    if dates:
        unique_dates = set(dates)
        if len(unique_dates) > 1:
            latest_bar_date_consistent = False
            blockers.append("mismatched_latest_bar_dates")

    # Deduplicate blockers preserving order
    blockers = list(dict.fromkeys(blockers))

    checked_artifacts = {
        "M447": stats_m447,
        "M448": stats_m448,
        "M449": stats_m449,
        "M450": stats_m450,
        "M451": stats_m451,
        "M451_txt": stats_m451_txt,
        "M452": stats_m452,
        "M453": stats_m453,
    }

    if blockers:
        return {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "manifest_health_state": "blocked_or_invalid",
            "accepted_for_operator_observation": False,
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

    return {
        "milestone": _MILESTONE,
        "phase": _PHASE,
        "command": _COMMAND,
        "manifest_health_state": "ready",
        "accepted_for_operator_observation": True,
        "source_run_index_milestone": "M453",
        "source_run_index_state": "ready",
        "indexed_milestones": ["M447", "M448", "M449", "M450", "M451", "M452", "M453"],
        "checked_artifacts": checked_artifacts,
        "text_warning_present": text_warning_present,
        "latest_bar_date_consistent": latest_bar_date_consistent,
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


def render_etf_sma_daily_artifact_manifest_health_text(payload: dict[str, Any]) -> str:
    """Render the payload into a deterministic text brief summary."""
    state = payload.get("manifest_health_state")
    if state == "blocked_or_invalid":
        blockers_str = ", ".join(payload.get("blockers", []))
        return (
            "ETF/SMA Daily Artifact Manifest Health Check (M454) - BLOCKED OR INVALID\n"
            "========================================================================\n"
            f"Milestone: {payload.get('milestone')}\n"
            f"Manifest Health State: {state}\n"
            f"Source M453 Milestone: {payload.get('source_run_index_milestone', 'M453')}\n"
            f"Source M453 State: {payload.get('source_run_index_state', 'unknown')}\n"
            f"Warning: {payload.get('operator_warning')}\n"
            f"Blockers: {blockers_str}\n"
        )
    return (
        "ETF/SMA Daily Artifact Manifest Health Check (M454) - READY FOR OBSERVATION\n"
        "===========================================================================\n"
        f"Milestone: {payload.get('milestone')}\n"
        f"Manifest Health State: {state}\n"
        f"Source M453 Milestone: {payload.get('source_run_index_milestone')}\n"
        f"Source M453 State: {payload.get('source_run_index_state')}\n"
        f"Warning: {payload.get('operator_warning')}\n"
        f"Latest Bar Date Consistent: {payload.get('latest_bar_date_consistent')}\n"
    )


def render_etf_sma_daily_artifact_manifest_health_json(payload: Mapping[str, Any]) -> str:
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


def _compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


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


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
