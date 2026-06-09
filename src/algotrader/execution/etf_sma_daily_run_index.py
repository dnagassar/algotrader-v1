"""Offline daily run index for Milestone M453.

This module reads all preceding daily cycle artifacts (M447 through M452),
validates their presence and key acceptance states, and emits one JSONL
daily run index artifact for operator observation only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyRunIndexConfig",
    "run_etf_sma_daily_run_index",
    "build_etf_sma_daily_run_index",
    "render_etf_sma_daily_run_index_json",
    "render_etf_sma_daily_run_index_text",
]

_MILESTONE = "M453"
_PHASE = "offline_daily_run_index"
_COMMAND = "etf-sma-daily-run-index"

_DEFAULT_M447 = "runs/paper_lab/m447_offline_daily_cycle_m446_rerun_manifest.jsonl"
_DEFAULT_M448 = "runs/paper_lab/m448_refreshed_current_cycle_rollup.jsonl"
_DEFAULT_M449 = "runs/paper_lab/m449_preview_only_daily_run_packet.jsonl"
_DEFAULT_M450 = "runs/paper_lab/m450_daily_preview_pipeline_manifest.jsonl"
_DEFAULT_M451_SUMMARY = "runs/paper_lab/m451_daily_operator_brief_summary.jsonl"
_DEFAULT_M451_TXT = "runs/paper_lab/m451_daily_operator_brief.txt"
_DEFAULT_M452 = "runs/paper_lab/m452_daily_acceptance_gate_packet.jsonl"
_DEFAULT_OUTPUT = "runs/paper_lab/m453_daily_run_index.jsonl"

_WARNING_TEXT = "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders."


@dataclass(frozen=True, slots=True)
class EtfSmaDailyRunIndexConfig:
    """Configuration for M453 Daily Run Index command."""

    m447_jsonl: Path | str = _DEFAULT_M447
    m448_jsonl: Path | str = _DEFAULT_M448
    m449_jsonl: Path | str = _DEFAULT_M449
    m450_jsonl: Path | str = _DEFAULT_M450
    m451_summary_jsonl: Path | str = _DEFAULT_M451_SUMMARY
    m451_txt: Path | str = _DEFAULT_M451_TXT
    m452_jsonl: Path | str = _DEFAULT_M452
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
        object.__setattr__(self, "output_jsonl", _required_path(self.output_jsonl, "output_jsonl"))


def run_etf_sma_daily_run_index(config: EtfSmaDailyRunIndexConfig) -> dict[str, Any]:
    """Execute validation of all source artifacts and write the run index JSONL."""
    payload = build_etf_sma_daily_run_index(config)

    output_path = Path(config.output_jsonl)
    if output_path.parent != Path(".") and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    line = render_etf_sma_daily_run_index_json(payload) + "\n"
    output_path.write_text(line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_run_index(config: EtfSmaDailyRunIndexConfig) -> dict[str, Any]:
    """Load inputs, perform validation checks, and build the M453 run index payload."""
    blockers: list[str] = []

    m447_rec = _load_record(Path(config.m447_jsonl), blockers, "m447")
    m448_rec = _load_record(Path(config.m448_jsonl), blockers, "m448")
    m449_rec = _load_record(Path(config.m449_jsonl), blockers, "m449")
    m450_rec = _load_record(Path(config.m450_jsonl), blockers, "m450")
    m451_summary_rec = _load_record(Path(config.m451_summary_jsonl), blockers, "m451_summary")
    m452_rec = _load_record(Path(config.m452_jsonl), blockers, "m452")

    # M451 text brief warning validation
    text_warning_present = False
    brief_txt_path = Path(config.m451_txt)
    if not brief_txt_path.exists() or not brief_txt_path.is_file():
        blockers.append("m451_txt_missing")
    else:
        try:
            txt_content = brief_txt_path.read_text(encoding="utf-8")
            if _WARNING_TEXT in txt_content:
                text_warning_present = True
            else:
                blockers.append("m451_txt_warning_missing")
        except Exception:
            blockers.append("m451_txt_warning_missing")

    records = {
        "M447": m447_rec,
        "M448": m448_rec,
        "M449": m449_rec,
        "M450": m450_rec,
        "M451": m451_summary_rec,
        "M452": m452_rec,
    }

    # Derive expected/latest bar dates dynamically from accepted source artifacts
    expected_dates = {}
    latest_local_dates = {}
    for name, rec in records.items():
        if rec:
            if "expected_latest_bar_date" in rec:
                expected_dates[name] = rec["expected_latest_bar_date"]
            else:
                blockers.append(f"{name.lower()}_expected_latest_bar_date_missing")

            if "latest_local_bar_date" in rec:
                latest_local_dates[name] = rec["latest_local_bar_date"]
            else:
                blockers.append(f"{name.lower()}_latest_local_bar_date_missing")

    derived_expected_date = None
    derived_latest_local_date = None

    if expected_dates:
        unique_expected = set(expected_dates.values())
        if len(unique_expected) > 1:
            blockers.append("mismatched_expected_latest_bar_date")
        else:
            derived_expected_date = list(unique_expected)[0]

    if latest_local_dates:
        unique_latest = set(latest_local_dates.values())
        if len(unique_latest) > 1:
            blockers.append("mismatched_latest_local_bar_date")
        else:
            derived_latest_local_date = list(unique_latest)[0]

    if derived_expected_date and derived_latest_local_date:
        if derived_expected_date != derived_latest_local_date:
            blockers.append("expected_and_latest_local_bar_date_mismatch")

    # Milestone checks
    for name, rec in records.items():
        if rec:
            if rec.get("milestone") != name:
                blockers.append(f"{name.lower()}_milestone_mismatch")

    # Invariants checks (posture, cycle_decision, current_action, recommended_operator_action, profit_claim, freshness_state)
    for name, rec in records.items():
        if rec:
            if rec.get("freshness_state") != "accepted_current_adjusted_bars":
                blockers.append(f"{name.lower()}_freshness_state_unexpected")
            if rec.get("profit_claim") != "none":
                blockers.append(f"{name.lower()}_profit_claim_unexpected")

            fb = rec.get("freshness_blockers")
            if not isinstance(fb, list) or len(fb) > 0:
                blockers.append(f"{name.lower()}_freshness_blockers_not_empty")

    # M447 specific checks
    if m447_rec:
        if m447_rec.get("posture") != "risk_on":
            blockers.append("m447_posture_unexpected")
        if m447_rec.get("cycle_decision") != "hold/noop":
            blockers.append("m447_cycle_decision_unexpected")
        if m447_rec.get("recommended_operator_action") != "observe_hold_noop":
            blockers.append("m447_recommended_operator_action_unexpected")

    # M448 specific checks
    if m448_rec:
        if m448_rec.get("posture") != "risk_on":
            blockers.append("m448_posture_unexpected")
        if m448_rec.get("cycle_decision") != "hold/noop":
            blockers.append("m448_cycle_decision_unexpected")
        if m448_rec.get("current_action") != "observe_hold_noop":
            blockers.append("m448_current_action_unexpected")
        if m448_rec.get("recommended_operator_action") != "observe_hold_noop":
            blockers.append("m448_recommended_operator_action_unexpected")

    # M449 specific checks
    if m449_rec:
        if m449_rec.get("source_posture") != "risk_on":
            blockers.append("m449_source_posture_unexpected")
        if m449_rec.get("source_cycle_decision") != "hold/noop":
            blockers.append("m449_source_cycle_decision_unexpected")
        if m449_rec.get("source_current_action") != "observe_hold_noop":
            blockers.append("m449_source_current_action_unexpected")
        if m449_rec.get("current_action") != "observe_hold_noop":
            blockers.append("m449_current_action_unexpected")
        if m449_rec.get("recommended_operator_action") != "observe_hold_noop":
            blockers.append("m449_recommended_operator_action_unexpected")

    # M450 specific checks
    if m450_rec:
        if m450_rec.get("posture") != "risk_on":
            blockers.append("m450_posture_unexpected")
        if m450_rec.get("cycle_decision") != "hold/noop":
            blockers.append("m450_cycle_decision_unexpected")
        if m450_rec.get("current_action") != "observe_hold_noop":
            blockers.append("m450_current_action_unexpected")
        if m450_rec.get("recommended_operator_action") != "observe_hold_noop":
            blockers.append("m450_recommended_operator_action_unexpected")

    # M451 specific checks
    if m451_summary_rec:
        if m451_summary_rec.get("posture") != "risk_on":
            blockers.append("m451_posture_unexpected")
        if m451_summary_rec.get("cycle_decision") != "hold/noop":
            blockers.append("m451_cycle_decision_unexpected")
        if m451_summary_rec.get("current_action") != "observe_hold_noop":
            blockers.append("m451_current_action_unexpected")
        if m451_summary_rec.get("recommended_operator_action") != "observe_hold_noop":
            blockers.append("m451_recommended_operator_action_unexpected")

    # M452 specific checks
    if m452_rec:
        if m452_rec.get("posture") != "risk_on":
            blockers.append("m452_posture_unexpected")
        if m452_rec.get("cycle_decision") != "hold/noop":
            blockers.append("m452_cycle_decision_unexpected")
        if m452_rec.get("current_action") != "observe_hold_noop":
            blockers.append("m452_current_action_unexpected")
        if m452_rec.get("recommended_operator_action") != "observe_hold_noop":
            blockers.append("m452_recommended_operator_action_unexpected")

    # Blockers key checks for files that have them
    for name, rec in records.items():
        if rec:
            if "blockers" in rec:
                b = rec.get("blockers")
                if not isinstance(b, list) or len(b) > 0:
                    blockers.append(f"{name.lower()}_blockers_not_empty")

    # Operator warning checks (M451 and M452)
    for name, rec in [("M451", m451_summary_rec), ("M452", m452_rec)]:
        if rec:
            if rec.get("operator_warning") != "preview_only_not_order_authorization":
                blockers.append(f"{name.lower()}_operator_warning_unexpected")

    # Safety/mutation flag checks
    safety_keys = [
        "submitted",
        "mutated",
        "broker_action_performed",
        "network_access_attempted",
        "credential_access_attempted",
        "live_authorized",
    ]
    for name, rec in records.items():
        if rec:
            for key in safety_keys:
                if rec.get(key) is not False:
                    blockers.append(f"{name.lower()}_{key}_not_false")

    # Submit/scheduler/broker permission flag checks
    permission_keys = [
        "paper_submit_allowed",
        "live_submit_allowed",
        "scheduler_install_allowed",
        "os_scheduler_installed",
        "scheduler_mutation_performed",
        "submit_authorized",
        "paper_submit_authorized",
        "paper_action_authorized",
    ]
    for name, rec in records.items():
        if rec:
            for key in permission_keys:
                if key in rec:
                    if rec.get(key) is not False:
                        blockers.append(f"{name.lower()}_{key}_not_false")

    # Specific state validations
    if m452_rec:
        if m452_rec.get("acceptance_gate_state") != "accepted_for_preview_only_observation":
            blockers.append("m452_state_not_accepted")
        if m452_rec.get("accepted_for_operator_observation") is not True:
            blockers.append("m452_observation_not_true")

    if m450_rec:
        if m450_rec.get("pipeline_state") != "preview_pipeline_ready":
            blockers.append("m450_pipeline_state_not_ready")

    if m451_summary_rec:
        if m451_summary_rec.get("brief_state") != "ready":
            blockers.append("m451_brief_state_not_ready")

    if m449_rec:
        if m449_rec.get("daily_preview_run_state") != "preview_only_daily_run_ready":
            blockers.append("m449_run_state_not_ready")
        if m449_rec.get("operating_brief_state") != "ready":
            blockers.append("m449_brief_state_not_ready")
        if m449_rec.get("schedule_contract_state") != "local_preview_contract_ready":
            blockers.append("m449_contract_state_not_ready")

    if m448_rec:
        if m448_rec.get("record_type") != "m448_refreshed_current_cycle_rollup":
            blockers.append("m448_record_type_unexpected")

    # Cross-artifact consistency validation
    if m452_rec and m450_rec:
        if m452_rec.get("source_pipeline_state") != m450_rec.get("pipeline_state"):
            blockers.append("mismatched_pipeline_state")
        if m452_rec.get("source_stages_run") != m450_rec.get("stages_run"):
            blockers.append("mismatched_stages_run")
        if m452_rec.get("source_stages_validated") != m450_rec.get("stages_validated"):
            blockers.append("mismatched_stages_validated")

    if m452_rec and m451_summary_rec:
        if m452_rec.get("source_brief_state") != m451_summary_rec.get("brief_state"):
            blockers.append("mismatched_brief_state")

    if m451_summary_rec and m450_rec:
        if m451_summary_rec.get("source_pipeline_state") != m450_rec.get("pipeline_state"):
            blockers.append("mismatched_pipeline_state")
        if m451_summary_rec.get("source_stages_run") != m450_rec.get("stages_run"):
            blockers.append("mismatched_stages_run")
        if m451_summary_rec.get("source_stages_validated") != m450_rec.get("stages_validated"):
            blockers.append("mismatched_stages_validated")

    # Deduplicate blockers preserving order
    blockers = list(dict.fromkeys(blockers))

    if blockers:
        return {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "daily_run_index_state": "blocked_or_invalid",
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
        "daily_run_index_state": "ready",
        "accepted_for_operator_observation": True,
        "order_authorization": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "scheduler_install_allowed": False,
        "source_acceptance_gate_milestone": "M452",
        "source_acceptance_gate_state": "accepted_for_preview_only_observation",
        "source_pipeline_milestone": "M450",
        "source_pipeline_state": "preview_pipeline_ready",
        "source_operator_brief_milestone": "M451",
        "source_brief_state": "ready",
        "source_stages_run": ["M447", "M448", "M449"],
        "source_stages_validated": ["M447", "M448", "M449"],
        "indexed_milestones": ["M447", "M448", "M449", "M450", "M451", "M452"],
        "indexed_artifacts": {
            "M447": _normalize_path(config.m447_jsonl),
            "M448": _normalize_path(config.m448_jsonl),
            "M449": _normalize_path(config.m449_jsonl),
            "M450": _normalize_path(config.m450_jsonl),
            "M451": _normalize_path(config.m451_summary_jsonl),
            "M451_txt": _normalize_path(config.m451_txt),
            "M452": _normalize_path(config.m452_jsonl),
        },
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": derived_expected_date,
        "latest_local_bar_date": derived_latest_local_date,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "operator_warning": "preview_only_not_order_authorization",
        "text_warning_present": text_warning_present,
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


def render_etf_sma_daily_run_index_text(payload: dict[str, Any]) -> str:
    """Render the payload into a deterministic text brief summary."""
    state = payload.get("daily_run_index_state")
    if state == "blocked_or_invalid":
        blockers_str = ", ".join(payload.get("blockers", []))
        return (
            "ETF/SMA Daily Run Index (M453) - BLOCKED OR INVALID\n"
            "===================================================\n"
            f"Daily Run Index State: {state}\n"
            f"Accepted for Observation: {payload.get('accepted_for_operator_observation')}\n"
            f"Blockers: {blockers_str}\n"
            "Safety: order_auth=false, paper_submit=false, live_submit=false, scheduler_install=false\n"
        )

    return (
        "ETF/SMA Daily Run Index (M453) - READY FOR OBSERVATION\n"
        "=======================================================\n"
        "Daily Run Index State: ready\n"
        "Accepted for Observation: true\n"
        "Order Authorization: false\n"
        "Paper Submit Allowed: false\n"
        "Live Submit Allowed: false\n"
        "Scheduler Install Allowed: false\n"
        "Data Freshness: accepted_current_adjusted_bars\n"
        f"Expected Latest Bar Date: {payload.get('expected_latest_bar_date')}\n"
        f"Latest Local Bar Date: {payload.get('latest_local_bar_date')}\n"
        f"Posture: {payload.get('posture')}\n"
        f"Cycle Decision: {payload.get('cycle_decision')}\n"
        f"Current Action: {payload.get('current_action')}\n"
        f"Recommended Operator Action: {payload.get('recommended_operator_action')}\n"
        f"Warning: {payload.get('operator_warning')}\n"
        "\n"
        "Next-action policy suggestion:\n"
        "Recommend proceeding to the next safe offline or read-only milestone.\n"
    )


def render_etf_sma_daily_run_index_json(payload: Mapping[str, Any]) -> str:
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


def _load_record(path: Path, blockers: list[str], prefix: str) -> dict[str, Any]:
    if not path.exists():
        blockers.append(f"{prefix}_missing")
        return {}
    if not path.is_file():
        blockers.append(f"{prefix}_missing")
        return {}
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        blockers.append(f"{prefix}_missing")
        return {}
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) != 1:
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
