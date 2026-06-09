"""Offline daily preview run for Milestone M449.

This module reads one M448 current-cycle rollup record, validates it fail-closed,
and produces one preview-only daily operating brief/schedule contract artifact.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyPreviewRunConfig",
    "EtfSmaDailyPreviewRunWriteResult",
    "run_etf_sma_daily_preview_run",
    "build_etf_sma_daily_preview_run",
    "write_etf_sma_daily_preview_run_jsonl",
    "render_etf_sma_daily_preview_run_json",
]

_MILESTONE = "M449"
_PHASE = "offline_preview_only_daily_operating_brief_automation_packet"
_COMMAND = "etf-sma-daily-preview-run"
_DEFAULT_SOURCE_ROLLUP = "runs/paper_lab/m448_refreshed_current_cycle_rollup.jsonl"
_DEFAULT_OUTPUT_JSONL = "runs/paper_lab/m449_preview_only_daily_run_packet.jsonl"

_REQUIRED_KEYS = (
    "freshness_state",
    "freshness_blockers",
    "expected_latest_bar_date",
    "latest_local_bar_date",
    "current_action",
    "cycle_decision",
    "posture",
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
    "profit_claim",
)

_SAFETY_KEYS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPreviewRunConfig:
    """Configuration for the M449 daily preview run."""

    source_rollup_jsonl: Path | str = _DEFAULT_SOURCE_ROLLUP
    output_jsonl: Path | str = _DEFAULT_OUTPUT_JSONL

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_rollup_jsonl",
            _required_path(self.source_rollup_jsonl, "source_rollup_jsonl"),
        )
        object.__setattr__(
            self,
            "output_jsonl",
            _required_path(self.output_jsonl, "output_jsonl"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPreviewRunWriteResult:
    """Metadata about written JSONL record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool

    def __post_init__(self) -> None:
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        if not self.newline_terminated:
            raise ValidationError("Output must be newline terminated.")


def run_etf_sma_daily_preview_run(
    config: EtfSmaDailyPreviewRunConfig,
) -> dict[str, Any]:
    """Execute the M449 daily preview run flow."""
    payload = build_etf_sma_daily_preview_run(config)
    write_etf_sma_daily_preview_run_jsonl(payload, config.output_jsonl)
    return payload


def build_etf_sma_daily_preview_run(
    config: EtfSmaDailyPreviewRunConfig,
) -> dict[str, Any]:
    """Build the M449 daily preview run record payload."""
    source_path = Path(config.source_rollup_jsonl)
    blockers: list[str] = []
    source_rollup_loaded = False
    source_rollup_record_count: int | None = None

    expected_latest_bar_date: str | None = None
    latest_local_bar_date: str | None = None

    # Check source rollup presence
    if not source_path.exists():
        blockers.append("missing_source_rollup")
    elif not source_path.is_file():
        blockers.append("missing_source_rollup")
    else:
        source_rollup_loaded = True
        try:
            content = source_path.read_text(encoding="utf-8")
        except Exception:
            content = ""

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        source_rollup_record_count = len(lines)

        if source_rollup_record_count != 1:
            blockers.append("source_rollup_record_count_not_one")

        parsed_records: list[dict[str, Any]] = []
        malformed = False
        for line in lines:
            try:
                rec = json.loads(line)
                if not isinstance(rec, Mapping):
                    malformed = True
                else:
                    parsed_records.append(dict(rec))
            except json.JSONDecodeError:
                malformed = True

        if malformed:
            blockers.append("source_rollup_malformed_json")

        if source_rollup_record_count == 1 and not malformed:
            record = parsed_records[0]

            # 1. Missing required fields
            missing_fields = [k for k in _REQUIRED_KEYS if k not in record]
            if missing_fields:
                blockers.append("source_rollup_missing_required_fields")

            # Extract date fields
            expected_latest_bar_date = record.get("expected_latest_bar_date")
            latest_local_bar_date = record.get("latest_local_bar_date")

            # 2. freshness_state not accepted_current_adjusted_bars
            if "freshness_state" in record and record["freshness_state"] != "accepted_current_adjusted_bars":
                blockers.append("source_freshness_state_not_accepted")

            # 3. Non-empty freshness_blockers
            if "freshness_blockers" in record:
                fb = record["freshness_blockers"]
                if not isinstance(fb, list) or len(fb) > 0:
                    blockers.append("source_freshness_blockers_present")

            # 4. expected_latest_bar_date != latest_local_bar_date
            if "expected_latest_bar_date" in record and "latest_local_bar_date" in record:
                if record["expected_latest_bar_date"] != record["latest_local_bar_date"]:
                    blockers.append("source_latest_bar_date_mismatch")

            # 5. current_action not observe_hold_noop
            if "current_action" in record and record["current_action"] != "observe_hold_noop":
                blockers.append("source_current_action_unexpected")

            # 6. cycle_decision not hold/noop
            if "cycle_decision" in record and record["cycle_decision"] != "hold/noop":
                blockers.append("source_cycle_decision_unexpected")

            # 7. posture not risk_on
            if "posture" in record and record["posture"] != "risk_on":
                blockers.append("source_posture_unexpected")

            # 8. Any true safety flags
            any_safety_true = False
            for k in _SAFETY_KEYS:
                if record.get(k) is True:
                    any_safety_true = True
            if any_safety_true:
                blockers.append("source_safety_flags_not_false")

            # 9. profit_claim not none
            if "profit_claim" in record and record["profit_claim"] != "none":
                blockers.append("source_profit_claim_not_none")

    # If any blocker is found, build the blocked payload
    if blockers:
        payload = {
            "milestone": _MILESTONE,
            "phase": _PHASE,
            "command": _COMMAND,
            "source_rollup_path": str(config.source_rollup_jsonl),
            "source_rollup_loaded": source_rollup_loaded,
            "daily_preview_run_state": "blocked_fail_closed",
            "operating_brief_state": "blocked",
            "schedule_contract_state": "blocked",
            "os_scheduler_installed": False,
            "scheduler_mutation_performed": False,
            "paper_submit_allowed": False,
            "live_submit_allowed": False,
            "current_action": "blocked/fail_closed",
            "recommended_operator_action": "repair_source_rollup_before_daily_preview_use",
            "blockers": list(dict.fromkeys(blockers)),  # deduplicate preserving order
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "live_authorized": False,
            "profit_claim": "none",
        }
        if source_rollup_record_count is not None:
            payload["source_rollup_record_count"] = source_rollup_record_count
        return payload

    # Build the accepted payload
    return {
        "milestone": _MILESTONE,
        "phase": _PHASE,
        "command": _COMMAND,
        "source_rollup_path": str(config.source_rollup_jsonl),
        "source_rollup_record_count": 1,
        "source_rollup_loaded": True,
        "source_current_action": "observe_hold_noop",
        "source_cycle_decision": "hold/noop",
        "source_posture": "risk_on",
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": expected_latest_bar_date,
        "latest_local_bar_date": latest_local_bar_date,
        "daily_preview_run_state": "preview_only_daily_run_ready",
        "operating_brief_state": "ready",
        "schedule_contract_state": "local_preview_contract_ready",
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "next_safe_command": f"python -m algotrader.cli {_COMMAND}",
        "source_refresh_prerequisite": "refresh_adjusted_bars_and_rerun_current_cycle_rollup_before_relying_on_a_new_trading_day",
        "blockers": [],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
    }


def render_etf_sma_daily_preview_run_json(payload: Mapping[str, Any]) -> str:
    """Render the payload dict to a deterministic compact JSON string."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def write_etf_sma_daily_preview_run_jsonl(
    payload: Mapping[str, Any],
    output_path: Path | str,
) -> EtfSmaDailyPreviewRunWriteResult:
    """Write exactly one JSONL record to the output path."""
    path = Path(output_path)
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    line = render_etf_sma_daily_preview_run_json(payload) + "\n"
    path.write_text(line, encoding="utf-8", newline="\n")

    return EtfSmaDailyPreviewRunWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
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
