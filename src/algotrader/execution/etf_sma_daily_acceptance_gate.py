"""Offline daily acceptance gate for Milestone M452.

This module consumes the M450 preview pipeline manifest and M451 operator brief artifacts,
validates their consistency, and emits one local JSONL acceptance-gate packet.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyAcceptanceGateConfig",
    "run_etf_sma_daily_acceptance_gate",
    "build_etf_sma_daily_acceptance_gate",
    "render_etf_sma_daily_acceptance_gate_json",
    "render_etf_sma_daily_acceptance_gate_text",
]

_MILESTONE = "M452"
_PHASE = "offline_daily_acceptance_gate"
_COMMAND = "etf-sma-daily-acceptance-gate"

_DEFAULT_PIPELINE_JSONL = "runs/paper_lab/m450_daily_preview_pipeline_manifest.jsonl"
_DEFAULT_BRIEF_SUMMARY_JSONL = "runs/paper_lab/m451_daily_operator_brief_summary.jsonl"
_DEFAULT_BRIEF_TXT = "runs/paper_lab/m451_daily_operator_brief.txt"
_DEFAULT_OUTPUT_JSONL = "runs/paper_lab/m452_daily_acceptance_gate_packet.jsonl"

_WARNING_TEXT = "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders."


@dataclass(frozen=True, slots=True)
class EtfSmaDailyAcceptanceGateConfig:
    """Configuration for M452 Daily Acceptance Gate."""

    pipeline_jsonl: Path | str = _DEFAULT_PIPELINE_JSONL
    brief_summary_jsonl: Path | str = _DEFAULT_BRIEF_SUMMARY_JSONL
    brief_txt: Path | str = _DEFAULT_BRIEF_TXT
    output_jsonl: Path | str = _DEFAULT_OUTPUT_JSONL

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pipeline_jsonl",
            _required_path(self.pipeline_jsonl, "pipeline_jsonl"),
        )
        object.__setattr__(
            self,
            "brief_summary_jsonl",
            _required_path(self.brief_summary_jsonl, "brief_summary_jsonl"),
        )
        object.__setattr__(
            self,
            "brief_txt",
            _required_path(self.brief_txt, "brief_txt"),
        )
        object.__setattr__(
            self,
            "output_jsonl",
            _required_path(self.output_jsonl, "output_jsonl"),
        )


def run_etf_sma_daily_acceptance_gate(
    config: EtfSmaDailyAcceptanceGateConfig,
) -> dict[str, Any]:
    """Execute validation and write the acceptance gate packet JSONL."""
    payload = build_etf_sma_daily_acceptance_gate(config)

    output_path = Path(config.output_jsonl)
    if output_path.parent != Path(".") and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    jsonl_line = render_etf_sma_daily_acceptance_gate_json(payload) + "\n"
    output_path.write_text(jsonl_line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_acceptance_gate(
    config: EtfSmaDailyAcceptanceGateConfig,
) -> dict[str, Any]:
    """Load inputs, perform validation checks, and build the output payload."""
    blockers: list[str] = []

    pipeline_path = Path(config.pipeline_jsonl)
    brief_summary_path = Path(config.brief_summary_jsonl)
    brief_txt_path = Path(config.brief_txt)

    pipeline_rec = _load_record(pipeline_path, blockers, "pipeline_jsonl")
    brief_rec = _load_record(brief_summary_path, blockers, "brief_summary_jsonl")

    # Validate M451 text brief
    text_warning_present = False
    if not brief_txt_path.exists() or not brief_txt_path.is_file():
        blockers.append("brief_txt_missing")
    else:
        try:
            txt_content = brief_txt_path.read_text(encoding="utf-8")
            if _WARNING_TEXT in txt_content:
                text_warning_present = True
            else:
                blockers.append("brief_txt_warning_missing")
        except Exception:
            blockers.append("brief_txt_warning_missing")

    # M450 validation
    if pipeline_rec:
        required_pipeline_keys = (
            "pipeline_state",
            "stages_run",
            "stages_validated",
            "current_action",
            "recommended_operator_action",
            "freshness_state",
            "expected_latest_bar_date",
            "latest_local_bar_date",
            "blockers",
            "submitted",
            "mutated",
            "broker_action_performed",
            "network_access_attempted",
            "credential_access_attempted",
            "live_authorized",
            "os_scheduler_installed",
            "scheduler_mutation_performed",
            "paper_submit_allowed",
            "live_submit_allowed",
            "profit_claim",
        )
        missing_keys = [k for k in required_pipeline_keys if k not in pipeline_rec]
        if missing_keys:
            blockers.append("pipeline_record_missing_required_keys")
        else:
            if pipeline_rec.get("pipeline_state") != "preview_pipeline_ready":
                blockers.append("pipeline_state_not_ready")

            stages_run = pipeline_rec.get("stages_run")
            stages_val = pipeline_rec.get("stages_validated")
            if (
                not isinstance(stages_run, list)
                or stages_run != ["M447", "M448", "M449"]
                or not isinstance(stages_val, list)
                or stages_val != ["M447", "M448", "M449"]
            ):
                blockers.append("pipeline_stages_unexpected")

            if (
                pipeline_rec.get("current_action") != "observe_hold_noop"
                or pipeline_rec.get("recommended_operator_action") != "observe_hold_noop"
            ):
                blockers.append("pipeline_actions_unexpected")

            if pipeline_rec.get("freshness_state") != "accepted_current_adjusted_bars":
                blockers.append("pipeline_freshness_state_unexpected")

            if (
                pipeline_rec.get("expected_latest_bar_date") != "2026-06-08"
                or pipeline_rec.get("latest_local_bar_date") != "2026-06-08"
            ):
                blockers.append("pipeline_latest_bar_date_unexpected")

            p_blockers = pipeline_rec.get("blockers")
            if not isinstance(p_blockers, list) or len(p_blockers) > 0:
                blockers.append("pipeline_has_blockers")

            safety_flags = (
                "submitted",
                "mutated",
                "broker_action_performed",
                "network_access_attempted",
                "credential_access_attempted",
                "live_authorized",
                "paper_submit_allowed",
                "live_submit_allowed",
            )
            for k in safety_flags:
                if pipeline_rec.get(k) is not False:
                    blockers.append("pipeline_safety_flags_not_false")
                    break

            scheduler_flags = ("os_scheduler_installed", "scheduler_mutation_performed")
            for k in scheduler_flags:
                if pipeline_rec.get(k) is not False:
                    blockers.append("pipeline_scheduler_flags_not_false")
                    break

            if pipeline_rec.get("profit_claim") != "none":
                blockers.append("pipeline_profit_claim_unexpected")

    # M451 validation
    if brief_rec:
        required_brief_keys = (
            "milestone",
            "phase",
            "command",
            "brief_state",
            "source_milestone",
            "source_pipeline_state",
            "source_stages_run",
            "source_stages_validated",
            "freshness_state",
            "freshness_blockers",
            "expected_latest_bar_date",
            "latest_local_bar_date",
            "posture",
            "cycle_decision",
            "current_action",
            "recommended_operator_action",
            "operator_warning",
            "paper_submit_allowed",
            "live_submit_allowed",
            "os_scheduler_installed",
            "scheduler_mutation_performed",
            "submitted",
            "mutated",
            "broker_action_performed",
            "network_access_attempted",
            "credential_access_attempted",
            "live_authorized",
            "profit_claim",
            "blockers",
        )
        missing_keys = [k for k in required_brief_keys if k not in brief_rec]
        if missing_keys:
            blockers.append("brief_summary_record_missing_required_keys")
        else:
            if brief_rec.get("milestone") != "M451":
                blockers.append("brief_milestone_unexpected")

            if brief_rec.get("phase") != "offline_daily_operator_brief_renderer":
                blockers.append("brief_phase_unexpected")

            if brief_rec.get("command") != "etf-sma-daily-operator-brief":
                blockers.append("brief_command_unexpected")

            if brief_rec.get("brief_state") != "ready":
                blockers.append("brief_state_not_ready")

            if brief_rec.get("source_milestone") != "M450":
                blockers.append("brief_source_milestone_unexpected")

            if brief_rec.get("source_pipeline_state") != "preview_pipeline_ready":
                blockers.append("brief_source_pipeline_state_unexpected")

            source_stages_run = brief_rec.get("source_stages_run")
            source_stages_val = brief_rec.get("source_stages_validated")
            if (
                not isinstance(source_stages_run, list)
                or source_stages_run != ["M447", "M448", "M449"]
                or not isinstance(source_stages_val, list)
                or source_stages_val != ["M447", "M448", "M449"]
            ):
                blockers.append("brief_source_stages_unexpected")

            if brief_rec.get("freshness_state") != "accepted_current_adjusted_bars":
                blockers.append("brief_freshness_state_unexpected")

            f_blockers = brief_rec.get("freshness_blockers")
            if not isinstance(f_blockers, list) or len(f_blockers) > 0:
                blockers.append("brief_freshness_blockers_present")

            if (
                brief_rec.get("expected_latest_bar_date") != "2026-06-08"
                or brief_rec.get("latest_local_bar_date") != "2026-06-08"
            ):
                blockers.append("brief_latest_bar_date_unexpected")

            if brief_rec.get("posture") != "risk_on":
                blockers.append("brief_posture_unexpected")

            if brief_rec.get("cycle_decision") != "hold/noop":
                blockers.append("brief_cycle_decision_unexpected")

            if (
                brief_rec.get("current_action") != "observe_hold_noop"
                or brief_rec.get("recommended_operator_action") != "observe_hold_noop"
            ):
                blockers.append("brief_actions_unexpected")

            if brief_rec.get("operator_warning") != "preview_only_not_order_authorization":
                blockers.append("brief_operator_warning_unexpected")

            safety_flags = (
                "submitted",
                "mutated",
                "broker_action_performed",
                "network_access_attempted",
                "credential_access_attempted",
                "live_authorized",
                "paper_submit_allowed",
                "live_submit_allowed",
            )
            for k in safety_flags:
                if brief_rec.get(k) is not False:
                    blockers.append("brief_safety_flags_not_false")
                    break

            scheduler_flags = ("os_scheduler_installed", "scheduler_mutation_performed")
            for k in scheduler_flags:
                if brief_rec.get(k) is not False:
                    blockers.append("brief_scheduler_flags_not_false")
                    break

            if brief_rec.get("profit_claim") != "none":
                blockers.append("brief_profit_claim_unexpected")

            b_blockers = brief_rec.get("blockers")
            if not isinstance(b_blockers, list) or len(b_blockers) > 0:
                blockers.append("brief_has_blockers")

    # Cross-artifact consistency validation
    if pipeline_rec and brief_rec and not missing_keys:
        if brief_rec.get("source_pipeline_state") != pipeline_rec.get("pipeline_state"):
            blockers.append("mismatched_pipeline_state")

        if brief_rec.get("source_stages_run") != pipeline_rec.get("stages_run"):
            blockers.append("mismatched_stages_run")

        if brief_rec.get("source_stages_validated") != pipeline_rec.get("stages_validated"):
            blockers.append("mismatched_stages_validated")

        if brief_rec.get("freshness_state") != pipeline_rec.get("freshness_state"):
            blockers.append("mismatched_freshness_state")

        if brief_rec.get("expected_latest_bar_date") != pipeline_rec.get("expected_latest_bar_date"):
            blockers.append("mismatched_expected_latest_bar_date")

        if brief_rec.get("latest_local_bar_date") != pipeline_rec.get("latest_local_bar_date"):
            blockers.append("mismatched_latest_local_bar_date")

        if brief_rec.get("current_action") != pipeline_rec.get("current_action"):
            blockers.append("mismatched_current_action")

        if brief_rec.get("recommended_operator_action") != pipeline_rec.get("recommended_operator_action"):
            blockers.append("mismatched_recommended_operator_action")

    # Deduplicate blockers preserving order
    blockers = list(dict.fromkeys(blockers))

    if blockers:
        return {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "acceptance_gate_state": "blocked_or_invalid",
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
        "expected_latest_bar_date": "2026-06-08",
        "latest_local_bar_date": "2026-06-08",
        "posture": brief_rec.get("posture", "risk_on"),
        "cycle_decision": brief_rec.get("cycle_decision", "hold/noop"),
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


def render_etf_sma_daily_acceptance_gate_text(payload: dict[str, Any]) -> str:
    """Render the payload into a deterministic text brief summary."""
    state = payload.get("acceptance_gate_state")
    if state == "blocked_or_invalid":
        blockers_str = ", ".join(payload.get("blockers", []))
        return (
            "ETF/SMA Daily Acceptance Gate (M452) - BLOCKED OR INVALID\n"
            "==========================================================\n"
            f"Acceptance Gate State: {state}\n"
            f"Accepted for Observation: {payload.get('accepted_for_operator_observation')}\n"
            f"Blockers: {blockers_str}\n"
            "Safety: order_auth=false, paper_submit=false, live_submit=false, scheduler_install=false\n"
        )

    return (
        "ETF/SMA Daily Acceptance Gate (M452) - ACCEPTED FOR OBSERVATION\n"
        "===============================================================\n"
        "Acceptance Gate State: accepted_for_preview_only_observation\n"
        "Accepted for Observation: true\n"
        "Order Authorization: false\n"
        "Paper Submit Allowed: false\n"
        "Live Submit Allowed: false\n"
        "Scheduler Install Allowed: false\n"
        "Source: M450 pipeline + M451 operator brief\n"
        "Data Freshness: accepted_current_adjusted_bars (2026-06-08)\n"
        "Current Action: observe_hold_noop\n"
        "Recommended Operator Action: observe_hold_noop\n"
        "Warning: preview-only and does not authorize or recommend submitting orders.\n"
        "\n"
        "Next-action policy suggestion:\n"
        "Recommend implementing either a deterministic daily run index or a read-only paper-state freshness scaffold that is credential-gated and skipped/offline by default.\n"
    )


def render_etf_sma_daily_acceptance_gate_json(payload: Mapping[str, Any]) -> str:
    """Render the payload dict to a deterministic compact JSON string."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


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
