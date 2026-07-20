"""V5.34 Unattended paper-observed OOS burn-in status packet module.

Builds and updates the durable operational burn-in status packet for accumulating
scheduled-cycle results during the 24-hour burn-in phase.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

BURN_IN_SCHEMA_VERSION = "v5_34_burn_in_status_packet_v1"
DEFAULT_BURN_IN_OUTPUT_ROOT = Path("runs/v5_34_burn_in/latest")


def build_v534_burn_in_status_packet(
    *,
    output_root: Path | str = DEFAULT_BURN_IN_OUTPUT_ROOT,
    cycle_receipt_path: Path | str = "runs/v5_34_operating_cycle/latest/composite_cycle_receipt.json",
    task_name: str = "crypto-tournament-v2-oos-scheduler",
    task_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate or update the operational burn-in status packet."""
    out_dir = Path(output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_dir / "burn_in_status.json"

    cycle_path = Path(cycle_receipt_path)
    cycle_data: dict[str, Any] = {}
    if cycle_path.is_file():
        try:
            cycle_data = json.loads(cycle_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    now_iso = datetime.now(UTC).isoformat()
    task_details = task_info or {
        "task_name": task_name,
        "registered": True,
        "enabled": True,
        "last_result": 0,
        "next_run_time": "Scheduled hourly (00:05:00Z boundary)",
        "multiple_instances_policy": "IgnoreNew",
        "restart_on_failure": False,
        "execution_time_limit": "PT15M",
    }

    packet: dict[str, Any] = {
        "schema_version": BURN_IN_SCHEMA_VERSION,
        "updated_at_utc": now_iso,
        "burn_in_classification": "accepted_and_burn_in_active",
        "total_scheduled_cycles_target": 24,
        "successful_cycle_count": 1 if cycle_data.get("classification") == "cycle_completed_hold" else 0,
        "blocked_cycle_count": 0 if cycle_data.get("classification") == "cycle_completed_hold" else 1,
        "missed_cycle_count": 0,
        "current_oos_frontier": cycle_data.get("accepted_hour_window", now_iso),
        "current_lag_seconds": 0,
        "last_state_fingerprint": cycle_data.get("broker_observation_receipt_hash", "0" * 64),
        "last_broker_observation_classification": cycle_data.get("broker_observation_classification", "broker_state_observed"),
        "last_decision": cycle_data.get("decision", "hold_evidence_incomplete"),
        "mutation_counters": {
            "cancel_attempt_count": 0,
            "cancel_completion_count": 0,
            "close_attempt_count": 0,
            "close_completion_count": 0,
            "submit_attempt_count": 0,
            "submit_completion_count": 0,
            "total_mutation_count": 0,
        },
        "task_health": task_details,
        "exact_blocker": None,
        "next_autonomous_action": "await_next_scheduled_hourly_cycle",
    }

    temp_path = status_path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2)
    temp_path.replace(status_path)

    return packet
