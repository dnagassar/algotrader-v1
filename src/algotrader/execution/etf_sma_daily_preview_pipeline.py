"""One-command offline daily preview pipeline for Milestone M450.

This module invokes the existing M447, M448, and M449 stages in sequence,
validates each stage fail-closed, and writes one deterministic M450 manifest.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_offline_daily_cycle_rerun_m446 import (
    EtfSmaOfflineDailyCycleRerunM446Config,
    run_etf_sma_offline_daily_cycle_rerun_m446,
)
from algotrader.execution.etf_sma_refreshed_current_cycle_rollup_m448 import (
    EtfSmaRefreshedCurrentCycleRollupM448Config,
    run_etf_sma_refreshed_current_cycle_rollup_m448,
)
from algotrader.execution.etf_sma_daily_preview_run import (
    EtfSmaDailyPreviewRunConfig,
    run_etf_sma_daily_preview_run,
)

__all__ = [
    "EtfSmaDailyPreviewPipelineConfig",
    "EtfSmaDailyPreviewPipelineWriteResult",
    "run_etf_sma_daily_preview_pipeline",
    "build_etf_sma_daily_preview_pipeline",
    "write_etf_sma_daily_preview_pipeline_jsonl",
    "render_etf_sma_daily_preview_pipeline_json",
]

_m447_default = EtfSmaOfflineDailyCycleRerunM446Config()
_m448_default = EtfSmaRefreshedCurrentCycleRollupM448Config()
_m449_default = EtfSmaDailyPreviewRunConfig()


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPreviewPipelineConfig:
    """Explicit configuration for the M450 daily preview pipeline."""

    m447_output_jsonl: Path | str = _m447_default.output_jsonl
    m448_output_jsonl: Path | str = _m448_default.output_jsonl
    m449_output_jsonl: Path | str = _m449_default.output_jsonl
    output_jsonl: Path | str = "runs/paper_lab/m450_daily_preview_pipeline_manifest.jsonl"
    source_m446_canonical_csv_path: Path | str = _m447_default.source_m446_canonical_csv_path

    def __post_init__(self) -> None:
        object.__setattr__(self, "m447_output_jsonl", _required_path(self.m447_output_jsonl, "m447_output_jsonl"))
        object.__setattr__(self, "m448_output_jsonl", _required_path(self.m448_output_jsonl, "m448_output_jsonl"))
        object.__setattr__(self, "m449_output_jsonl", _required_path(self.m449_output_jsonl, "m449_output_jsonl"))
        object.__setattr__(self, "output_jsonl", _required_path(self.output_jsonl, "output_jsonl"))
        object.__setattr__(
            self,
            "source_m446_canonical_csv_path",
            _required_path(self.source_m446_canonical_csv_path, "source_m446_canonical_csv_path"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPreviewPipelineWriteResult:
    """Metadata about written M450 JSONL record."""

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


def run_etf_sma_daily_preview_pipeline(
    config: EtfSmaDailyPreviewPipelineConfig,
) -> dict[str, Any]:
    """Execute the M450 daily preview pipeline sequence."""
    payload = build_etf_sma_daily_preview_pipeline(config)
    write_etf_sma_daily_preview_pipeline_jsonl(payload, config.output_jsonl)
    return payload


def build_etf_sma_daily_preview_pipeline(
    config: EtfSmaDailyPreviewPipelineConfig,
) -> dict[str, Any]:
    """Build the M450 daily preview pipeline record, running and validating stages."""
    stages_run: list[str] = []
    stages_validated: list[str] = []
    blockers: list[str] = []
    failed_stage: str | None = None

    # Helper to clean target output path to prevent stale artifact acceptance
    def _clean_path(path: Path) -> None:
        if path.exists():
            path.unlink()

    # --- STAGE 1: M447 ---
    stages_run.append("M447")
    _clean_path(Path(config.m447_output_jsonl))
    m447_ok = False
    try:
        run_etf_sma_offline_daily_cycle_rerun_m446(
            EtfSmaOfflineDailyCycleRerunM446Config(
                source_m446_canonical_csv_path=config.source_m446_canonical_csv_path,
                output_jsonl=config.m447_output_jsonl,
            )
        )
        m447_ok = True
    except Exception:
        blockers.append("m447_stage_failed")

    if m447_ok:
        try:
            m447_record = _validate_jsonl_record(Path(config.m447_output_jsonl))
            _validate_m447_record(m447_record, blockers)
        except ValueError as exc:
            err = str(exc)
            if err == "missing":
                blockers.append("m447_artifact_missing")
            elif err == "record_count_not_one":
                blockers.append("m447_record_count_not_one")
            else:
                blockers.append("m447_malformed_json")

    m447_has_blocker = any(b.startswith("m447_") for b in blockers)
    if m447_has_blocker:
        failed_stage = "M447"
    else:
        stages_validated.append("M447")

    # --- STAGE 2: M448 ---
    if not failed_stage:
        stages_run.append("M448")
        _clean_path(Path(config.m448_output_jsonl))
        m448_ok = False
        try:
            run_etf_sma_refreshed_current_cycle_rollup_m448(
                EtfSmaRefreshedCurrentCycleRollupM448Config(
                    source_m447_manifest_path=config.m447_output_jsonl,
                    output_jsonl=config.m448_output_jsonl,
                )
            )
            m448_ok = True
        except Exception:
            blockers.append("m448_stage_failed")

        if m448_ok:
            try:
                m448_record = _validate_jsonl_record(Path(config.m448_output_jsonl))
                _validate_m448_record(m448_record, blockers)
            except ValueError as exc:
                err = str(exc)
                if err == "missing":
                    blockers.append("m448_artifact_missing")
                elif err == "record_count_not_one":
                    blockers.append("m448_record_count_not_one")
                else:
                    blockers.append("m448_malformed_json")

        m448_has_blocker = any(b.startswith("m448_") for b in blockers)
        if m448_has_blocker:
            failed_stage = "M448"
        else:
            stages_validated.append("M448")

    # --- STAGE 3: M449 ---
    m449_record: dict[str, Any] = {}
    if not failed_stage:
        stages_run.append("M449")
        _clean_path(Path(config.m449_output_jsonl))
        m449_ok = False
        try:
            run_etf_sma_daily_preview_run(
                EtfSmaDailyPreviewRunConfig(
                    source_rollup_jsonl=config.m448_output_jsonl,
                    output_jsonl=config.m449_output_jsonl,
                )
            )
            m449_ok = True
        except Exception:
            blockers.append("m449_stage_failed")

        if m449_ok:
            try:
                m449_record = _validate_jsonl_record(Path(config.m449_output_jsonl))
                _validate_m449_record(m449_record, blockers)
            except ValueError as exc:
                err = str(exc)
                if err == "missing":
                    blockers.append("m449_artifact_missing")
                elif err == "record_count_not_one":
                    blockers.append("m449_record_count_not_one")
                else:
                    blockers.append("m449_malformed_json")

        m449_has_blocker = any(b.startswith("m449_") for b in blockers)
        if m449_has_blocker:
            failed_stage = "M449"
        else:
            stages_validated.append("M449")

    # --- FINAL PAYLOAD ---
    if blockers:
        blocked_payload = {
            "milestone": "M450",
            "phase": "one_command_offline_daily_preview_pipeline",
            "command": "etf-sma-daily-preview-pipeline",
            "pipeline_state": "blocked",
            "stages_run": stages_run,
            "stages_validated": stages_validated,
            "m447_artifact_path": str(config.m447_output_jsonl),
            "m448_artifact_path": str(config.m448_output_jsonl),
            "m449_artifact_path": str(config.m449_output_jsonl),
            "m450_artifact_path": str(config.output_jsonl),
            "current_action": "blocked/fail_closed",
            "recommended_operator_action": "repair_daily_preview_pipeline_source_before_use",
            "blockers": list(dict.fromkeys(blockers)),
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "live_authorized": False,
            "os_scheduler_installed": False,
            "scheduler_mutation_performed": False,
            "paper_submit_allowed": False,
            "live_submit_allowed": False,
            "profit_claim": "none",
        }
        if failed_stage is not None:
            blocked_payload["failed_stage"] = failed_stage
        return blocked_payload

    # Accepted Payload
    expected_latest_bar_date = m449_record.get("expected_latest_bar_date")
    latest_local_bar_date = m449_record.get("latest_local_bar_date")

    return {
        "milestone": "M450",
        "phase": "one_command_offline_daily_preview_pipeline",
        "command": "etf-sma-daily-preview-pipeline",
        "pipeline_state": "preview_pipeline_ready",
        "stages_run": ["M447", "M448", "M449"],
        "stages_validated": ["M447", "M448", "M449"],
        "m447_artifact_path": str(config.m447_output_jsonl),
        "m448_artifact_path": str(config.m448_output_jsonl),
        "m449_artifact_path": str(config.m449_output_jsonl),
        "m450_artifact_path": str(config.output_jsonl),
        "m447_record_count": 1,
        "m448_record_count": 1,
        "m449_record_count": 1,
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": expected_latest_bar_date,
        "latest_local_bar_date": latest_local_bar_date,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "next_safe_command": "python -m algotrader.cli etf-sma-daily-preview-pipeline",
        "source_refresh_prerequisite": "refresh_adjusted_bars_before_relying_on_a_new_trading_day",
        "blockers": [],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "profit_claim": "none",
    }


def _validate_safety_flags(record: dict[str, Any]) -> bool:
    required_flags = (
        "submitted",
        "mutated",
        "broker_action_performed",
        "network_access_attempted",
        "credential_access_attempted",
        "live_authorized",
    )
    for flag in required_flags:
        if flag not in record:
            return False
        val = record[flag]
        if not isinstance(val, bool) or val is not False:
            return False

    optional_flags = (
        "os_scheduler_installed",
        "scheduler_mutation_performed",
        "paper_submit_allowed",
        "live_submit_allowed",
    )
    for flag in optional_flags:
        if flag in record:
            val = record[flag]
            if not isinstance(val, bool) or val is not False:
                return False
    return True


def _validate_m447_record(record: dict[str, Any], blockers: list[str]) -> None:
    action_unexpected = False
    if "milestone" in record and record["milestone"] != "M447":
        action_unexpected = True
    if "command" in record and record["command"] != "etf-sma-offline-daily-cycle-rerun-m446":
        action_unexpected = True
    if (
        record.get("posture") != "risk_on"
        or record.get("cycle_decision") != "hold/noop"
        or record.get("recommended_operator_action") != "observe_hold_noop"
    ):
        action_unexpected = True
    if action_unexpected:
        blockers.append("m447_action_unexpected")

    if record.get("freshness_state") != "accepted_current_adjusted_bars":
        blockers.append("m447_freshness_not_accepted")

    fb = record.get("freshness_blockers")
    if not isinstance(fb, list) or len(fb) > 0:
        blockers.append("m447_freshness_blockers_present")

    expected_date = record.get("expected_latest_bar_date")
    local_date = record.get("latest_local_bar_date")
    if expected_date is None or local_date is None or expected_date != local_date:
        blockers.append("m447_latest_bar_date_mismatch")

    if not _validate_safety_flags(record):
        blockers.append("m447_safety_flags_not_false")

    if record.get("profit_claim") != "none":
        blockers.append("m447_profit_claim_not_none")


def _validate_m448_record(record: dict[str, Any], blockers: list[str]) -> None:
    action_unexpected = False
    if "milestone" in record and record["milestone"] != "M448":
        action_unexpected = True
    if "command" in record and record["command"] != "etf-sma-refreshed-current-cycle-rollup-m448":
        action_unexpected = True
    if (
        record.get("posture") != "risk_on"
        or record.get("cycle_decision") != "hold/noop"
        or record.get("current_action") != "observe_hold_noop"
    ):
        action_unexpected = True
    if action_unexpected:
        blockers.append("m448_action_unexpected")

    if record.get("freshness_state") != "accepted_current_adjusted_bars":
        blockers.append("m448_freshness_not_accepted")

    fb = record.get("freshness_blockers")
    if not isinstance(fb, list) or len(fb) > 0:
        blockers.append("m448_freshness_blockers_present")

    expected_date = record.get("expected_latest_bar_date")
    local_date = record.get("latest_local_bar_date")
    if expected_date is None or local_date is None or expected_date != local_date:
        blockers.append("m448_latest_bar_date_mismatch")

    if not _validate_safety_flags(record):
        blockers.append("m448_safety_flags_not_false")

    if record.get("profit_claim") != "none":
        blockers.append("m448_profit_claim_not_none")


def _validate_m449_record(record: dict[str, Any], blockers: list[str]) -> None:
    action_unexpected = False
    if "milestone" in record and record["milestone"] != "M449":
        action_unexpected = True
    if "command" in record and record["command"] != "etf-sma-daily-preview-run":
        action_unexpected = True
    if (
        record.get("daily_preview_run_state") != "preview_only_daily_run_ready"
        or record.get("operating_brief_state") != "ready"
        or record.get("schedule_contract_state") != "local_preview_contract_ready"
        or record.get("current_action") != "observe_hold_noop"
        or record.get("recommended_operator_action") != "observe_hold_noop"
    ):
        action_unexpected = True

    bl = record.get("blockers")
    if not isinstance(bl, list) or len(bl) > 0:
        action_unexpected = True

    if action_unexpected:
        blockers.append("m449_action_unexpected")

    if record.get("freshness_state") != "accepted_current_adjusted_bars":
        blockers.append("m449_freshness_not_accepted")

    fb = record.get("freshness_blockers")
    if not isinstance(fb, list) or len(fb) > 0:
        blockers.append("m449_freshness_blockers_present")

    expected_date = record.get("expected_latest_bar_date")
    local_date = record.get("latest_local_bar_date")
    if expected_date is None or local_date is None or expected_date != local_date:
        blockers.append("m449_latest_bar_date_mismatch")

    if not _validate_safety_flags(record):
        blockers.append("m449_safety_flags_not_false")

    if record.get("profit_claim") != "none":
        blockers.append("m449_profit_claim_not_none")


def _validate_jsonl_record(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ValueError("missing")
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        raise ValueError("malformed")
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError("record_count_not_one")
    try:
        rec = json.loads(lines[0])
    except json.JSONDecodeError:
        raise ValueError("malformed")
    if not isinstance(rec, Mapping):
        raise ValueError("malformed")
    return dict(rec)


def render_etf_sma_daily_preview_pipeline_json(payload: Mapping[str, Any]) -> str:
    """Render the pipeline payload to a compact deterministic JSON string."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def write_etf_sma_daily_preview_pipeline_jsonl(
    payload: Mapping[str, Any],
    output_path: Path | str,
) -> EtfSmaDailyPreviewPipelineWriteResult:
    """Write exactly one JSONL record to the output path."""
    path = Path(output_path)
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    line = render_etf_sma_daily_preview_pipeline_json(payload) + "\n"
    path.write_text(line, encoding="utf-8", newline="\n")

    return EtfSmaDailyPreviewPipelineWriteResult(
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
