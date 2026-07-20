"""V5.34 Unattended paper-observed OOS burn-in autonomous operating cycle.

Combines fresh completed-hour OOS accrual (Tournament V2 OOS scheduler), clean-source
bounded Alpaca paper observation, account flatness reconciliation, and durable
composite cycle receipt persistence.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    perform_genuine_paper_observation,
)
from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
    OneShotExecutor,
    RealCommandDispatcher,
)

CYCLE_SCHEMA_VERSION = "v5_34_unattended_operating_cycle_receipt_v1"
DEFAULT_CYCLE_OUTPUT_ROOT = Path("runs/v5_34_operating_cycle/latest")
DEFAULT_SCHEDULER_OUTPUT_ROOT = Path("runs/crypto_strategy_tournament/v2/latest")
DEFAULT_DISCOVERY_SOURCE = Path("runs/crypto_strategy_tournament/v1/input/crypto_1h_1y.csv")
DEFAULT_DISCOVERY_RECEIPT = Path("runs/crypto_strategy_tournament/v1/refresh/refresh_packet.json")


def run_v534_unattended_cycle(
    *,
    output_root: Path | str = DEFAULT_CYCLE_OUTPUT_ROOT,
    scheduler_output_root: Path | str = DEFAULT_SCHEDULER_OUTPUT_ROOT,
    discovery_source: Path | str = DEFAULT_DISCOVERY_SOURCE,
    discovery_receipt: Path | str = DEFAULT_DISCOVERY_RECEIPT,
    db_path: Path | str | None = None,
    scheduler_enabled: bool = False,
    market_data_read_authorized: bool = False,
    paper_broker_read_authorized: bool = False,
    allow_network: bool = False,
    as_of: datetime | str | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Run one production one-shot operating cycle or return an idempotent no-op."""
    root_dir = Path(repo_root or Path.cwd()).resolve()
    out_dir = Path(output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    composite_receipt_path = out_dir / "composite_cycle_receipt.json"

    now_utc = _parse_datetime(as_of) if as_of is not None else datetime.now(UTC)
    current_hour_str = now_utc.strftime("%Y-%m-%dT%H:00:00Z")

    # Check for same-window idempotency replay
    if composite_receipt_path.is_file():
        try:
            prior_data = json.loads(composite_receipt_path.read_text(encoding="utf-8"))
            if (
                prior_data.get("schema_version") == CYCLE_SCHEMA_VERSION
                and prior_data.get("accepted_hour_window") == current_hour_str
                and prior_data.get("classification") in ("cycle_completed_hold", "idempotent_same_window_replay")
            ):
                idempotent_receipt = dict(prior_data)
                idempotent_receipt["classification"] = "idempotent_same_window_replay"
                idempotent_receipt["idempotent_replay"] = True
                _write_json_atomic(composite_receipt_path, idempotent_receipt)
                return idempotent_receipt
        except Exception:
            pass

    started_at_iso = datetime.now(UTC).isoformat()
    sched_out_dir = Path(scheduler_output_root)
    database_path = Path(db_path) if db_path else sched_out_dir / "scheduler_state.db"

    composite: dict[str, Any] = {
        "schema_version": CYCLE_SCHEMA_VERSION,
        "started_at_utc": started_at_iso,
        "completed_at_utc": None,
        "classification": "in_progress",
        "accepted_hour_window": current_hour_str,
        "idempotent_replay": False,
        "source_commit_sha": None,
        "source_tree_sha": None,
        "source_worktree_clean": False,
        "scheduler_job_identity": None,
        "scheduler_classification": None,
        "market_data_receipt_path": None,
        "market_data_receipt_hash": None,
        "oos_state_fingerprint_before": None,
        "oos_state_fingerprint_after": None,
        "broker_observation_classification": None,
        "broker_observation_receipt_hash": None,
        "broker_stage_attempt_counts": {},
        "broker_stage_completion_counts": {},
        "account_flat_reconciled": False,
        "decision": "hold_evidence_incomplete",
        "paper_submit_performed": False,
        "paper_mutation_performed": False,
        "mutation_count": 0,
        "submission_count": 0,
        "next_autonomous_action": "await_next_scheduled_hourly_cycle",
    }

    # 1. Market-data OOS Accrual via Scheduler
    dispatcher = RealCommandDispatcher(
        scheduler_enabled=scheduler_enabled,
        market_data_read_authorized=market_data_read_authorized,
    )
    executor = OneShotExecutor(
        db_path=database_path,
        output_root=sched_out_dir,
        discovery_source=Path(discovery_source),
        discovery_receipt=Path(discovery_receipt),
        dispatcher=dispatcher,
        enabled=scheduler_enabled,
        allow_network=allow_network,
    )

    sched_tick = executor.tick(now_utc)
    composite["scheduler_job_identity"] = sched_tick.get("job_id")
    composite["scheduler_classification"] = sched_tick.get("classification")

    if sched_tick.get("status") not in ("success", "no_op"):
        composite["classification"] = f"scheduler_failed_{sched_tick.get('classification')}"
        composite["completed_at_utc"] = datetime.now(UTC).isoformat()
        _write_json_atomic(composite_receipt_path, composite)
        return composite

    # 2. Bounded Clean-Source Paper Broker Observation
    try:
        inv_receipt, obs_receipt = perform_genuine_paper_observation(
            paper_broker_read_authorized=paper_broker_read_authorized,
            allow_network=allow_network,
            repo_root=root_dir,
        )
        composite["source_commit_sha"] = inv_receipt.get("source_commit_sha")
        composite["source_tree_sha"] = inv_receipt.get("source_tree_sha")
        composite["source_worktree_clean"] = inv_receipt.get("source_worktree_clean", False)

        obs_bytes = json.dumps(obs_receipt, sort_keys=True).encode("utf-8")
        import hashlib
        composite["broker_observation_receipt_hash"] = hashlib.sha256(obs_bytes).hexdigest()
        composite["broker_observation_classification"] = obs_receipt.get("classification")

        stage_records = obs_receipt.get("stage_records", {})
        for stage, data in stage_records.items():
            if isinstance(data, dict):
                composite["broker_stage_attempt_counts"][stage] = data.get("attempt_count", 0)
                composite["broker_stage_completion_counts"][stage] = data.get("completion_count", 0)

        # 3. Account Flatness Reconciliation
        acc_valid = obs_receipt.get("account_validation") == "success"
        pos_valid = obs_receipt.get("positions_validation") == "success"
        ord_valid = obs_receipt.get("orders_validation") == "success"
        asset_valid = obs_receipt.get("asset_validation") == "success"

        is_flat = (
            obs_receipt.get("observed_positions_count") == 0
            and obs_receipt.get("observed_open_orders_count") == 0
        )
        composite["account_flat_reconciled"] = (acc_valid and pos_valid and ord_valid and asset_valid and is_flat)

        if not composite["account_flat_reconciled"]:
            composite["classification"] = "broker_reconciliation_failed"
            composite["completed_at_utc"] = datetime.now(UTC).isoformat()
            _write_json_atomic(composite_receipt_path, composite)
            return composite

    except Exception as exc:
        composite["classification"] = f"broker_observation_failed_{exc.__class__.__name__}"
        composite["completed_at_utc"] = datetime.now(UTC).isoformat()
        _write_json_atomic(composite_receipt_path, composite)
        return composite

    # 4. Finalize Decision and Composite Receipt
    composite["decision"] = "hold_evidence_incomplete"
    composite["classification"] = "cycle_completed_hold"
    composite["completed_at_utc"] = datetime.now(UTC).isoformat()
    _write_json_atomic(composite_receipt_path, composite)
    return composite


def _parse_datetime(val: datetime | str) -> datetime:
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=UTC)
        return val
    s = str(val).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    temp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="V5.34 Unattended Paper-Observed OOS Burn-In Cycle")
    parser.add_argument("--output-root", default=str(DEFAULT_CYCLE_OUTPUT_ROOT))
    parser.add_argument("--scheduler-output-root", default=str(DEFAULT_SCHEDULER_OUTPUT_ROOT))
    parser.add_argument("--discovery-source", default=str(DEFAULT_DISCOVERY_SOURCE))
    parser.add_argument("--discovery-receipt", default=str(DEFAULT_DISCOVERY_RECEIPT))
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--scheduler-enabled", action="store_true")
    parser.add_argument("--market-data-read-authorized", action="store_true")
    parser.add_argument("--paper-broker-read-authorized", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args()

    res = run_v534_unattended_cycle(
        output_root=args.output_root,
        scheduler_output_root=args.scheduler_output_root,
        discovery_source=args.discovery_source,
        discovery_receipt=args.discovery_receipt,
        db_path=args.db_path,
        scheduler_enabled=args.scheduler_enabled,
        market_data_read_authorized=args.market_data_read_authorized,
        paper_broker_read_authorized=args.paper_broker_read_authorized,
        allow_network=args.allow_network,
        as_of=args.as_of,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
