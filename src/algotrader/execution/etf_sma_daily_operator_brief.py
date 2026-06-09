"""Offline daily operator brief renderer for Milestone M451.

This module reads one M450 pipeline manifest record, validates it fail-closed,
and produces a human-readable text brief and a compact JSONL summary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyOperatorBriefConfig",
    "EtfSmaDailyOperatorBriefWriteResult",
    "run_etf_sma_daily_operator_brief",
    "build_etf_sma_daily_operator_brief",
    "write_etf_sma_daily_operator_brief_artifacts",
    "render_etf_sma_daily_operator_brief_json",
]

_MILESTONE = "M451"
_PHASE = "offline_daily_operator_brief_renderer"
_COMMAND = "etf-sma-daily-operator-brief"
_DEFAULT_INPUT_JSONL = "runs/paper_lab/m450_daily_preview_pipeline_manifest.jsonl"
_DEFAULT_OUTPUT_TXT = "runs/paper_lab/m451_daily_operator_brief.txt"
_DEFAULT_OUTPUT_JSONL = "runs/paper_lab/m451_daily_operator_brief_summary.jsonl"

_REQUIRED_KEYS = (
    "milestone",
    "pipeline_state",
    "stages_run",
    "stages_validated",
    "current_action",
    "recommended_operator_action",
    "freshness_state",
    "freshness_blockers",
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


@dataclass(frozen=True, slots=True)
class EtfSmaDailyOperatorBriefConfig:
    """Configuration for M451 Daily Operator Brief Renderer."""

    input_jsonl: Path | str = _DEFAULT_INPUT_JSONL
    output_txt: Path | str = _DEFAULT_OUTPUT_TXT
    output_jsonl: Path | str = _DEFAULT_OUTPUT_JSONL

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_jsonl",
            _required_path(self.input_jsonl, "input_jsonl"),
        )
        object.__setattr__(
            self,
            "output_txt",
            _required_path(self.output_txt, "output_txt"),
        )
        object.__setattr__(
            self,
            "output_jsonl",
            _required_path(self.output_jsonl, "output_jsonl"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaDailyOperatorBriefWriteResult:
    """Metadata about written brief artifacts."""

    output_txt_path: Path
    output_jsonl_path: Path
    record_count: int
    newline_terminated: bool


def run_etf_sma_daily_operator_brief(
    config: EtfSmaDailyOperatorBriefConfig,
) -> dict[str, Any]:
    """Execute the M451 daily operator brief flow."""
    payload = build_etf_sma_daily_operator_brief(config)
    write_etf_sma_daily_operator_brief_artifacts(payload, config)
    return payload


def build_etf_sma_daily_operator_brief(
    config: EtfSmaDailyOperatorBriefConfig,
) -> dict[str, Any]:
    """Validate input M450 record and build M451 operator brief payload."""
    input_path = Path(config.input_jsonl)
    blockers: list[str] = []
    record: dict[str, Any] = {}

    if not input_path.exists():
        blockers.append("input_jsonl_missing")
    elif not input_path.is_file():
        blockers.append("input_jsonl_missing")
    else:
        try:
            content = input_path.read_text(encoding="utf-8")
        except Exception:
            content = ""

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if len(lines) != 1:
            blockers.append("input_jsonl_record_count_not_one")
        else:
            try:
                rec = json.loads(lines[0])
                if not isinstance(rec, Mapping):
                    blockers.append("input_jsonl_malformed_json")
                else:
                    record = dict(rec)
            except json.JSONDecodeError:
                blockers.append("input_jsonl_malformed_json")

            if record:
                # Check for missing required fields
                missing_fields = [k for k in _REQUIRED_KEYS if k not in record]
                if missing_fields:
                    blockers.append("input_jsonl_missing_required_fields")

                # 1. Milestone
                if record.get("milestone") != "M450":
                    blockers.append("source_milestone_not_m450")

                # 2. Pipeline state
                if record.get("pipeline_state") != "preview_pipeline_ready":
                    blockers.append("source_pipeline_not_ready")

                # 3. Stages Run/Validated
                stages_run = record.get("stages_run")
                stages_validated = record.get("stages_validated")
                if (
                    not isinstance(stages_run, list)
                    or stages_run != ["M447", "M448", "M449"]
                    or not isinstance(stages_validated, list)
                    or stages_validated != ["M447", "M448", "M449"]
                ):
                    blockers.append("source_stages_unexpected")

                # 4. Freshness state
                if record.get("freshness_state") != "accepted_current_adjusted_bars":
                    blockers.append("source_freshness_not_accepted")

                # 5. Freshness blockers present
                fb = record.get("freshness_blockers")
                if not isinstance(fb, list) or len(fb) > 0:
                    blockers.append("source_freshness_blockers_present")

                # 6. Latest date mismatch
                expected_date = record.get("expected_latest_bar_date")
                local_date = record.get("latest_local_bar_date")
                if expected_date is None or local_date is None or expected_date != local_date:
                    blockers.append("source_latest_bar_date_mismatch")

                # 7. Unexpected action
                if (
                    record.get("current_action") != "observe_hold_noop"
                    or record.get("recommended_operator_action") != "observe_hold_noop"
                ):
                    blockers.append("source_action_unexpected")

                # 8. Source blockers present
                src_blockers = record.get("blockers")
                if not isinstance(src_blockers, list) or len(src_blockers) > 0:
                    blockers.append("source_blockers_present")

                # 9. Safety / mutation flags
                safety_keys = (
                    "submitted",
                    "mutated",
                    "broker_action_performed",
                    "network_access_attempted",
                    "credential_access_attempted",
                    "live_authorized",
                )
                for k in safety_keys:
                    val = record.get(k)
                    if val is not False:
                        blockers.append("source_safety_flags_not_false")
                        break

                # 10. Scheduler flags
                scheduler_keys = ("os_scheduler_installed", "scheduler_mutation_performed")
                for k in scheduler_keys:
                    val = record.get(k)
                    if val is not False:
                        blockers.append("source_scheduler_flags_not_false")
                        break

                # 11. Submit permissions
                submit_keys = ("paper_submit_allowed", "live_submit_allowed")
                for k in submit_keys:
                    val = record.get(k)
                    if val is not False:
                        blockers.append("source_submit_permissions_not_false")
                        break

                # 12. Profit claim
                if record.get("profit_claim") != "none":
                    blockers.append("source_profit_claim_not_none")

    # Deduplicate blockers preserving order
    blockers = list(dict.fromkeys(blockers))

    if blockers:
        return {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "brief_state": "blocked",
            "current_action": "blocked/fail_closed",
            "recommended_operator_action": "repair_m450_pipeline_manifest_before_operator_brief_use",
            "paper_submit_allowed": False,
            "live_submit_allowed": False,
            "os_scheduler_installed": False,
            "scheduler_mutation_performed": False,
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "live_authorized": False,
            "profit_claim": "none",
            "blockers": blockers,
        }

    return {
        "milestone": _MILESTONE,
        "phase": _PHASE,
        "command": _COMMAND,
        "brief_state": "ready",
        "input_jsonl_path": str(config.input_jsonl),
        "output_txt_path": str(config.output_txt),
        "output_jsonl_path": str(config.output_jsonl),
        "source_milestone": "M450",
        "source_pipeline_state": "preview_pipeline_ready",
        "source_stages_run": ["M447", "M448", "M449"],
        "source_stages_validated": ["M447", "M448", "M449"],
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": record.get("expected_latest_bar_date"),
        "latest_local_bar_date": record.get("latest_local_bar_date"),
        "posture": record.get("posture", "risk_on"),
        "cycle_decision": record.get("cycle_decision", "hold/noop"),
        "current_action": record.get("current_action", "observe_hold_noop"),
        "recommended_operator_action": record.get("recommended_operator_action", "observe_hold_noop"),
        "operator_warning": "preview_only_not_order_authorization",
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
        "blockers": [],
        "next_safe_command": f"python -m algotrader.cli {_COMMAND}",
    }


def render_etf_sma_daily_operator_brief_text(payload: dict[str, Any]) -> str:
    """Render the payload into a deterministic text brief."""
    if payload.get("brief_state") == "blocked":
        blockers_str = ", ".join(payload["blockers"])
        return (
            "ETF/SMA Daily Operator Brief (M451) - BLOCKED / FAIL-CLOSED\n"
            "===========================================================\n"
            "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders.\n\n"
            "Status: blocked/fail-closed\n"
            f"Recommended Operator Action: {payload.get('recommended_operator_action')}\n"
            f"Blockers: {blockers_str}\n"
            "Safety Flags: submitted=false, mutated=false, broker_action_performed=false, network_access_attempted=false, credential_access_attempted=false, live_authorized=false\n"
            "Scheduler Flags: os_scheduler_installed=false, scheduler_mutation_performed=false\n"
            "Submit Permissions: paper_submit_allowed=false, live_submit_allowed=false\n"
            "Profit Claim: none\n"
        )

    return (
        "ETF/SMA Daily Operator Brief (M451)\n"
        "===================================\n"
        "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders.\n\n"
        "Source: M450 Daily Preview Pipeline\n"
        f"Pipeline State: {payload.get('source_pipeline_state')}\n"
        f"Data Freshness: {payload.get('freshness_state')}\n"
        f"Latest Local Bar Date: {payload.get('latest_local_bar_date')}\n"
        f"Expected Latest Bar Date: {payload.get('expected_latest_bar_date')}\n"
        f"Posture: {payload.get('posture')}\n"
        f"Cycle Decision: {payload.get('cycle_decision')}\n"
        f"Current Action: {payload.get('current_action')}\n"
        f"Recommended Operator Action: {payload.get('recommended_operator_action')}\n"
        "Stages Validated: M447, M448, M449\n"
        "Blockers: none\n"
        "Safety Flags: submitted=false, mutated=false, broker_action_performed=false, network_access_attempted=false, credential_access_attempted=false, live_authorized=false\n"
        "Scheduler Flags: os_scheduler_installed=false, scheduler_mutation_performed=false\n"
        "Submit Permissions: paper_submit_allowed=false, live_submit_allowed=false\n"
        "Profit Claim: none\n"
        f"Next Safe Command: {payload.get('next_safe_command')}\n"
    )


def render_etf_sma_daily_operator_brief_json(payload: Mapping[str, Any]) -> str:
    """Render the payload dict to a deterministic compact JSON string."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def write_etf_sma_daily_operator_brief_artifacts(
    payload: dict[str, Any],
    config: EtfSmaDailyOperatorBriefConfig,
) -> EtfSmaDailyOperatorBriefWriteResult:
    """Write the text brief and JSONL summary to their configured output paths."""
    txt_path = Path(config.output_txt)
    jsonl_path = Path(config.output_jsonl)

    # Ensure parent directories exist
    for p in (txt_path, jsonl_path):
        if p.parent != Path(".") and not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)

    # Render contents
    txt_content = render_etf_sma_daily_operator_brief_text(payload)
    jsonl_line = render_etf_sma_daily_operator_brief_json(payload) + "\n"

    # Write files
    txt_path.write_text(txt_content, encoding="utf-8", newline="\n")
    jsonl_path.write_text(jsonl_line, encoding="utf-8", newline="\n")

    return EtfSmaDailyOperatorBriefWriteResult(
        output_txt_path=txt_path,
        output_jsonl_path=jsonl_path,
        record_count=1,
        newline_terminated=True,
    )


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
    return path


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
