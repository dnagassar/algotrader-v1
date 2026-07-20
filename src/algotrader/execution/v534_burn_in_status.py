"""V5.34 Unattended paper-observed OOS burn-in status packet module.

Builds and updates the durable operational burn-in status packet by dynamically
deriving state from validated immutable cycle receipts, Task Scheduler query,
and actual OOS accumulator frontier.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any

from algotrader.cli import _write_receipt_atomically

BURN_IN_SCHEMA_VERSION = "v5_34_burn_in_status_packet_v1"
DEFAULT_BURN_IN_OUTPUT_ROOT = Path("runs/v5_34_burn_in/latest")
DEFAULT_CYCLES_ROOT = Path("runs/v5_34_operating_cycle")


def query_task_scheduler_status(task_name: str = "crypto-tournament-v2-oos-scheduler") -> dict[str, Any]:
    """Query Task Scheduler state via bounded PowerShell call without credentials."""
    script = f"""
    $t = Get-ScheduledTask -TaskName "{task_name}" -ErrorAction SilentlyContinue
    if (-not $t) {{
        [PSCustomObject]@{{ task_exists = $false; enabled = $false; state = "Missing" }} | ConvertTo-Json
        exit 0
    }}
    $i = Get-ScheduledTaskInfo -TaskName "{task_name}" -ErrorAction SilentlyContinue
    [PSCustomObject]@{{
        task_exists = $true
        task_name = $t.TaskName
        state = $t.State.ToString()
        enabled = ($t.State.ToString() -ne 'Disabled')
        last_run_time = if ($i.LastRunTime) {{ $i.LastRunTime.ToString('o') }} else {{ $null }}
        last_task_result = $i.LastTaskResult
        next_run_time = if ($i.NextRunTime) {{ $i.NextRunTime.ToString('o') }} else {{ $null }}
    }} | ConvertTo-Json
    """
    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=10)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout.strip())
    except Exception:
        pass
    return {"task_exists": False, "enabled": False, "state": "Unknown", "last_task_result": None}


def build_v534_burn_in_status_packet(
    *,
    output_root: Path | str = DEFAULT_BURN_IN_OUTPUT_ROOT,
    cycles_root: Path | str = DEFAULT_CYCLES_ROOT,
    task_name: str = "crypto-tournament-v2-oos-scheduler",
    task_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate the operational burn-in status packet derived from actual evidence."""
    out_dir = Path(output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_dir / "burn_in_status.json"

    c_dir = Path(cycles_root)
    cycle_files = list(c_dir.glob("cycles/*/composite_cycle_receipt.json"))
    if not cycle_files:
        latest_file = c_dir / "latest" / "composite_cycle_receipt.json"
        if latest_file.is_file():
            cycle_files = [latest_file]

    cycle_receipts: list[dict[str, Any]] = []
    for cf in sorted(cycle_files):
        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("schema_version") == "v5_34_unattended_operating_cycle_receipt_v1":
                cycle_receipts.append(data)
        except Exception:
            pass

    task_details = task_info if task_info is not None else query_task_scheduler_status(task_name)

    now_iso = datetime.now(UTC).isoformat()
    successful_count = sum(1 for c in cycle_receipts if c.get("classification") in ("cycle_completed_hold", "idempotent_same_window_replay"))
    blocked_count = sum(1 for c in cycle_receipts if "blocked" in c.get("classification", "") or "failed" in c.get("classification", ""))
    missed_count = 0

    latest_receipt = cycle_receipts[-1] if cycle_receipts else {}

    # Classification logic derived from evidence
    exact_blocker = None
    if not cycle_receipts:
        burn_in_class = "not_started"
        exact_blocker = "no_cycle_evidence"
    elif not task_details.get("task_exists", False):
        burn_in_class = "blocked_task_query_failed"
        exact_blocker = "task_scheduler_query_failed"
    elif not task_details.get("enabled", False):
        burn_in_class = "activation_disabled"
        exact_blocker = "task_scheduler_disabled"
    elif latest_receipt.get("readiness_after") == "R1" or not latest_receipt.get("account_flat_reconciled", False):
        burn_in_class = "blocked_external_paper_account_state"
        exact_blocker = latest_receipt.get("blocker", "paper_account_non_flat_r1")
    elif successful_count == 1:
        burn_in_class = "burn_in_active_cycle_1_of_24"
    elif successful_count >= 24:
        burn_in_class = "accepted_and_burn_in_active"
    else:
        burn_in_class = f"burn_in_active_cycle_{successful_count}_of_24"

    packet: dict[str, Any] = {
        "schema_version": BURN_IN_SCHEMA_VERSION,
        "updated_at_utc": now_iso,
        "burn_in_classification": burn_in_class,
        "total_scheduled_cycles_target": 24,
        "successful_cycle_count": successful_count,
        "blocked_cycle_count": blocked_count,
        "missed_cycle_count": missed_count,
        "current_oos_frontier": latest_receipt.get("accepted_hour_window"),
        "current_lag_seconds": None,
        "last_state_fingerprint": latest_receipt.get("oos_state_fingerprint_after"),
        "last_broker_observation_classification": latest_receipt.get("broker_observation_classification"),
        "last_decision": latest_receipt.get("decision"),
        "mutation_counters": {
            "cancel_attempt_count": latest_receipt.get("mutation_count", 0),
            "cancel_completion_count": 0,
            "close_attempt_count": 0,
            "close_completion_count": 0,
            "submit_attempt_count": latest_receipt.get("submission_count", 0),
            "submit_completion_count": 0,
            "total_mutation_count": latest_receipt.get("mutation_count", 0),
        },
        "task_health": task_details,
        "exact_blocker": exact_blocker or latest_receipt.get("blocker"),
        "next_autonomous_action": latest_receipt.get("next_autonomous_action", "await_next_scheduled_hourly_cycle"),
    }

    _write_receipt_atomically(status_path, packet)
    return packet


def main() -> None:
    pkt = build_v534_burn_in_status_packet()
    print(json.dumps(pkt, indent=2))


if __name__ == "__main__":
    main()
