"""V5.34 Unattended paper-observed OOS burn-in status packet module.

Derives the durable operational burn-in status packet exclusively from
validated immutable cycle receipts and an actual bounded Windows Task
Scheduler observation. Nothing in the packet is asserted or defaulted to a
healthy value: every health field reflects observed evidence, and every
blocked state is reported with its exact classification.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from algotrader.execution.v534_unattended_cycle import (
    COMPLETED_CYCLE_CLASSIFICATIONS,
    CYCLE_SCHEMA_VERSION,
)

BURN_IN_SCHEMA_VERSION = "v5_34_burn_in_status_packet_v2"
DEFAULT_BURN_IN_OUTPUT_ROOT = Path("runs/v5_34_burn_in/latest")
DEFAULT_CYCLE_OUTPUT_ROOT = Path("runs/v5_34_operating_cycle/latest")
DEFAULT_TASK_NAME = "crypto-tournament-v2-oos-scheduler"
BURN_IN_TARGET_CYCLES = 24

_ONE_HOUR_SECONDS = 3600.0

_TASK_QUERY_COMMAND_TEMPLATE = (
    "$t = Get-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop; "
    "$i = Get-ScheduledTaskInfo -TaskName '{task_name}' -ErrorAction Stop; "
    "@{{state = [string]$t.State; "
    "action_execute = [string]$t.Actions[0].Execute; "
    "action_arguments = [string]$t.Actions[0].Arguments; "
    "last_run_time = [string]$i.LastRunTime; "
    "last_task_result = $i.LastTaskResult; "
    "next_run_time = [string]$i.NextRunTime; "
    "missed_run_count = $i.NumberOfMissedRuns}} | ConvertTo-Json -Compress"
)


def query_windows_scheduled_task(
    task_name: str = DEFAULT_TASK_NAME,
    *,
    runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Perform one bounded read-only Windows Task Scheduler observation.

    Returns a truthful observation record; failures are reported as exact
    classifications instead of fabricated healthy defaults.
    """
    run = runner or subprocess.run
    command = _TASK_QUERY_COMMAND_TEMPLATE.format(task_name=task_name)
    try:
        completed = run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        return {
            "task_name": task_name,
            "query_classification": "task_query_failed",
            "query_error_type": exc.__class__.__name__,
            "task_observed": False,
        }

    if getattr(completed, "returncode", 1) != 0:
        stderr_text = str(getattr(completed, "stderr", "") or "")
        classification = (
            "task_not_found"
            if "No MSFT_ScheduledTask objects found" in stderr_text
            or "ObjectNotFound" in stderr_text
            else "task_query_failed"
        )
        return {
            "task_name": task_name,
            "query_classification": classification,
            "task_observed": False,
        }

    try:
        payload = json.loads(str(getattr(completed, "stdout", "") or ""))
    except ValueError:
        return {
            "task_name": task_name,
            "query_classification": "task_query_unparseable",
            "task_observed": False,
        }

    state = str(payload.get("state") or "")
    return {
        "task_name": task_name,
        "query_classification": "task_observed",
        "task_observed": True,
        "state": state,
        "enabled": state not in ("", "Disabled"),
        "running": state == "Running",
        "action_execute": payload.get("action_execute"),
        "action_arguments": payload.get("action_arguments"),
        "last_run_time": payload.get("last_run_time"),
        "last_task_result": payload.get("last_task_result"),
        "next_run_time": payload.get("next_run_time"),
        "missed_run_count": payload.get("missed_run_count"),
    }


def build_v534_burn_in_status_packet(
    *,
    output_root: Path | str = DEFAULT_BURN_IN_OUTPUT_ROOT,
    cycle_output_root: Path | str = DEFAULT_CYCLE_OUTPUT_ROOT,
    task_name: str = DEFAULT_TASK_NAME,
    task_query: Callable[[], dict[str, Any]] | None = None,
    credential_rotation_confirmed: bool = False,
    unattended_secret_mechanism: str | None = None,
    target_cycles: int = BURN_IN_TARGET_CYCLES,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Build the burn-in status packet from validated evidence only."""
    out_dir = Path(output_root)
    cycle_dir = Path(cycle_output_root)
    now_utc = as_of if as_of is not None else datetime.now(UTC)

    task_health = (
        task_query() if task_query is not None else query_windows_scheduled_task(task_name)
    )

    receipts, invalid_receipt_count = _load_validated_receipts(cycle_dir / "receipts")

    completed = [
        r for r in receipts if r["classification"] in COMPLETED_CYCLE_CLASSIFICATIONS
    ]
    scheduled_completed = sorted(
        (r for r in completed if r.get("invocation_source") == "scheduled"),
        key=lambda r: str(r.get("requested_start_bar_open") or ""),
    )
    duplicates = [r for r in receipts if r["classification"] == "duplicate_window_no_op"]
    blocked = [
        r
        for r in receipts
        if r["classification"].startswith(("cycle_blocked_", "cycle_no_action_"))
    ]
    failed = [r for r in receipts if r["classification"].startswith("cycle_failed_")]

    missed_cycle_count = _missed_cycles(scheduled_completed)
    frontier = _latest_frontier(completed)
    lag_seconds = _frontier_lag_seconds(frontier, now_utc)

    latest_completed = max(
        completed, key=lambda r: str(r.get("completed_at_utc") or ""), default=None
    )
    paper_account_flat = (
        bool(latest_completed.get("account_flat_reconciled"))
        if latest_completed is not None
        else None
    )
    readiness_rung = (
        str(latest_completed.get("readiness_rung_after"))
        if latest_completed is not None
        else "R1"
    )

    external_account_blocker = (
        "blocked_external_paper_account_state" if paper_account_flat is False else None
    )

    burn_in_classification = _classify_burn_in(
        task_health=task_health,
        credential_rotation_confirmed=credential_rotation_confirmed,
        unattended_secret_mechanism=unattended_secret_mechanism,
        scheduled_completed_count=len(scheduled_completed),
        target_cycles=target_cycles,
    )

    packet: dict[str, Any] = {
        "schema_version": BURN_IN_SCHEMA_VERSION,
        "updated_at_utc": now_utc.isoformat(),
        "burn_in_classification": burn_in_classification,
        "total_scheduled_cycles_target": target_cycles,
        "scheduled_completed_cycle_count": len(scheduled_completed),
        "manual_completed_cycle_count": len(completed) - len(scheduled_completed),
        "duplicate_no_op_count": len(duplicates),
        "blocked_cycle_count": len(blocked),
        "failed_cycle_count": len(failed),
        "missed_cycle_count": missed_cycle_count,
        "invalid_receipt_count": invalid_receipt_count,
        "validated_receipt_count": len(receipts),
        "current_oos_frontier": frontier,
        "current_frontier_lag_seconds": lag_seconds,
        "last_cycle_classification": (
            latest_completed["classification"] if latest_completed is not None else None
        ),
        "last_broker_observation_classification": (
            latest_completed.get("broker_observation_classification")
            if latest_completed is not None
            else None
        ),
        "last_decision": (
            latest_completed.get("decision") if latest_completed is not None else None
        ),
        "paper_account_flat": paper_account_flat,
        "external_account_blocker": external_account_blocker,
        "readiness_rung": readiness_rung,
        "mutation_counters": _sum_mutation_counters(receipts),
        "task_health": task_health,
        "credential_rotation_confirmed": credential_rotation_confirmed,
        "unattended_secret_mechanism_configured": unattended_secret_mechanism is not None,
        "exact_blocker": _packet_blocker(burn_in_classification, external_account_blocker),
        "next_autonomous_action": _next_action(burn_in_classification),
    }

    status_path = out_dir / "burn_in_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = status_path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2, sort_keys=True)
    temp_path.replace(status_path)

    return packet


def _classify_burn_in(
    *,
    task_health: dict[str, Any],
    credential_rotation_confirmed: bool,
    unattended_secret_mechanism: str | None,
    scheduled_completed_count: int,
    target_cycles: int,
) -> str:
    query_classification = task_health.get("query_classification")
    if query_classification in ("task_query_failed", "task_query_unparseable"):
        return "blocked_task_query_failed"
    if not credential_rotation_confirmed:
        return "blocked_credential_rotation_required"
    if query_classification == "task_not_found":
        return "not_started" if scheduled_completed_count == 0 else "activation_disabled"
    if not task_health.get("enabled"):
        return "activation_disabled"
    if unattended_secret_mechanism is None:
        return "blocked_unattended_secret_loading"
    if scheduled_completed_count == 0:
        return "not_started"
    if scheduled_completed_count < target_cycles:
        return f"burn_in_active_cycle_{scheduled_completed_count}_of_{target_cycles}"
    return f"burn_in_complete_{target_cycles}_of_{target_cycles}"


def _packet_blocker(
    burn_in_classification: str, external_account_blocker: str | None
) -> str | None:
    if burn_in_classification.startswith("blocked_"):
        return burn_in_classification
    if burn_in_classification == "activation_disabled":
        return "activation_disabled"
    return external_account_blocker

def _next_action(burn_in_classification: str) -> str:
    if burn_in_classification == "blocked_credential_rotation_required":
        return "await_credential_rotation_confirmation"
    if burn_in_classification == "blocked_unattended_secret_loading":
        return "await_unattended_secret_mechanism_selection"
    if burn_in_classification == "blocked_task_query_failed":
        return "repair_task_scheduler_observation"
    if burn_in_classification in ("not_started", "activation_disabled"):
        return "await_operator_activation_from_clean_main"
    if burn_in_classification.startswith("burn_in_active_"):
        return "await_next_scheduled_hourly_cycle"
    return "await_operator_burn_in_review"


def _load_validated_receipts(
    receipts_dir: Path,
) -> tuple[list[dict[str, Any]], int]:
    """Load cycle receipts, admitting only hash-consistent v2 receipts."""
    validated: list[dict[str, Any]] = []
    invalid_count = 0
    if not receipts_dir.is_dir():
        return validated, invalid_count

    for path in sorted(receipts_dir.glob("cycle_*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            invalid_count += 1
            continue
        if not isinstance(receipt, dict):
            invalid_count += 1
            continue
        if receipt.get("schema_version") != CYCLE_SCHEMA_VERSION:
            invalid_count += 1
            continue
        recorded_hash = receipt.get("canonical_receipt_sha256")
        body = {
            key: value
            for key, value in receipt.items()
            if key != "canonical_receipt_sha256"
        }
        canonical_str = json.dumps(body, sort_keys=True, separators=(",", ":"))
        actual_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        if recorded_hash != actual_hash:
            invalid_count += 1
            continue
        if not isinstance(receipt.get("classification"), str):
            invalid_count += 1
            continue
        validated.append(receipt)

    return validated, invalid_count


def _missed_cycles(scheduled_completed: list[dict[str, Any]]) -> int:
    """Count hour gaps between consecutive accepted scheduled windows."""
    missed = 0
    previous_end: datetime | None = None
    for receipt in scheduled_completed:
        start = _parse_iso(receipt.get("requested_start_bar_open"))
        end = _parse_iso(receipt.get("requested_end_bar_open"))
        if start is None or end is None:
            continue
        if previous_end is not None:
            gap_hours = (start - previous_end).total_seconds() / _ONE_HOUR_SECONDS - 1.0
            if gap_hours > 0:
                missed += int(round(gap_hours))
        previous_end = end
    return missed


def _latest_frontier(completed: list[dict[str, Any]]) -> str | None:
    frontiers = [
        str(r["oos_frontier_after"])
        for r in completed
        if r.get("oos_frontier_after")
    ]
    return max(frontiers, default=None)


def _frontier_lag_seconds(frontier: str | None, now_utc: datetime) -> float | None:
    frontier_dt = _parse_iso(frontier)
    if frontier_dt is None:
        return None
    return max((now_utc - frontier_dt).total_seconds(), 0.0)


def _sum_mutation_counters(receipts: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "mutation_count": 0,
        "submission_count": 0,
        "paper_submit_performed_count": 0,
        "paper_mutation_performed_count": 0,
    }
    for receipt in receipts:
        totals["mutation_count"] += int(receipt.get("mutation_count") or 0)
        totals["submission_count"] += int(receipt.get("submission_count") or 0)
        if receipt.get("paper_submit_performed"):
            totals["paper_submit_performed_count"] += 1
        if receipt.get("paper_mutation_performed"):
            totals["paper_mutation_performed_count"] += 1
    return totals


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
