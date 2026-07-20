"""V5.34 Unattended paper-observed OOS burn-in autonomous operating cycle.

Combines clean-source admission, fresh completed-hour OOS accrual, clean-source
bounded Alpaca paper observation, account flatness reconciliation, and durable
composite cycle receipt persistence.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.cli import _write_receipt_atomically
from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    BrokerObservationError,
    get_source_provenance,
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
    latest_composite_receipt_path = out_dir / "composite_cycle_receipt.json"

    started_at_iso = datetime.now(UTC).isoformat()
    now_utc = _parse_datetime(as_of) if as_of is not None else datetime.now(UTC)
    accepted_hour_dt = now_utc.replace(minute=0, second=0, microsecond=0)
    accepted_hour_window_str = accepted_hour_dt.strftime("%Y-%m-%dT%H:00:00Z")
    window_dir_name = accepted_hour_dt.strftime("%Y%m%dT%H%M%SZ")
    cycle_window_dir = out_dir / "cycles" / window_dir_name
    cycle_window_dir.mkdir(parents=True, exist_ok=True)
    window_composite_receipt_path = cycle_window_dir / "composite_cycle_receipt.json"

    # Composite receipt structure with derived fields (no nulls on completion)
    composite: dict[str, Any] = {
        "schema_version": CYCLE_SCHEMA_VERSION,
        "started_at_utc": started_at_iso,
        "completed_at_utc": None,
        "classification": "in_progress",
        "accepted_hour_window": accepted_hour_window_str,
        "idempotent_replay": False,
        "source_commit_sha": None,
        "source_tree_sha": None,
        "source_worktree_clean": False,
        "source_bundle_manifest": {},
        "adapter_source_bundle_sha256": None,
        "scheduler_job_identity": None,
        "scheduler_classification": None,
        "market_data_receipt_path": None,
        "market_data_receipt_hash": None,
        "oos_state_fingerprint_before": None,
        "oos_state_fingerprint_after": None,
        "broker_invocation_hash": None,
        "broker_observation_hash": None,
        "broker_failure_hash": None,
        "broker_observation_classification": None,
        "broker_stage_attempt_counts": {},
        "broker_stage_completion_counts": {},
        "readiness_before": "R1",
        "readiness_after": "R1",
        "account_flat_reconciled": False,
        "decision": "hold_evidence_incomplete",
        "paper_submit_performed": False,
        "paper_mutation_performed": False,
        "mutation_count": 0,
        "submission_count": 0,
        "blocker": None,
        "next_autonomous_action": "await_next_scheduled_hourly_cycle",
    }

    # STEP 0: Clean-Source Admission Gate BEFORE scheduler, network, state, or broker
    try:
        provenance = get_source_provenance(root_dir)
        composite["source_commit_sha"] = provenance.get("source_commit_sha")
        composite["source_tree_sha"] = provenance.get("source_tree_sha")
        composite["source_worktree_clean"] = provenance.get("source_worktree_clean", False)
        composite["source_bundle_manifest"] = provenance.get("source_bundle_manifest", {})
        composite["adapter_source_bundle_sha256"] = provenance.get("adapter_source_bundle_sha256")
    except Exception as exc:
        composite["classification"] = f"blocked_provenance_failed_{exc.__class__.__name__}"
        composite["blocker"] = "provenance_check_failed"
        composite["next_autonomous_action"] = "resolve_repository_provenance"
        composite["completed_at_utc"] = datetime.now(UTC).isoformat()
        _persist_cycle_receipts(composite, window_composite_receipt_path, latest_composite_receipt_path)
        return composite

    if not composite["source_worktree_clean"]:
        composite["classification"] = "blocked_dirty_worktree"
        composite["blocker"] = "dirty_worktree"
        composite["next_autonomous_action"] = "clean_worktree_before_retry"
        composite["completed_at_utc"] = datetime.now(UTC).isoformat()
        _persist_cycle_receipts(composite, window_composite_receipt_path, latest_composite_receipt_path)
        return composite

    # STEP 0.5: Check for same-window idempotency replay based on scheduler window identity
    if window_composite_receipt_path.is_file():
        try:
            prior_data = json.loads(window_composite_receipt_path.read_text(encoding="utf-8"))
            if (
                prior_data.get("schema_version") == CYCLE_SCHEMA_VERSION
                and prior_data.get("accepted_hour_window") == accepted_hour_window_str
                and prior_data.get("classification") != "in_progress"
            ):
                prior_hash = hashlib.sha256(
                    json.dumps(prior_data, sort_keys=True).encode("utf-8")
                ).hexdigest()
                idempotent_receipt = dict(prior_data)
                idempotent_receipt["classification"] = "idempotent_same_window_replay"
                idempotent_receipt["idempotent_replay"] = True
                idempotent_receipt["original_cycle_receipt_path"] = str(window_composite_receipt_path)
                idempotent_receipt["original_canonical_hash"] = prior_hash
                idempotent_receipt["original_classification"] = prior_data.get("classification")
                _persist_cycle_receipts(idempotent_receipt, window_composite_receipt_path, latest_composite_receipt_path)
                return idempotent_receipt
        except Exception:
            pass

    # STEP 1: Tournament V2 Initialization (no silent exception swallowing)
    sched_out_dir = Path(scheduler_output_root)
    database_path = Path(db_path) if db_path else sched_out_dir / "scheduler_state.db"
    state_file = sched_out_dir / "frozen_state.json"

    if not state_file.is_file():
        try:
            from algotrader.research.crypto_tournament_v2_forward_oos import initialize_crypto_tournament_v2_forward_oos
            initialize_crypto_tournament_v2_forward_oos(
                output_root=sched_out_dir,
                discovery_source_path=Path(discovery_source),
                discovery_receipt_path=Path(discovery_receipt),
                as_of="2026-07-15T00:00:00+00:00",
            )
        except Exception as init_exc:
            composite["classification"] = "blocked_v2_initialization_failed"
            composite["blocker"] = f"v2_initialization_failed_{init_exc.__class__.__name__}"
            composite["next_autonomous_action"] = "resolve_v2_initialization_failure"
            composite["completed_at_utc"] = datetime.now(UTC).isoformat()
            _persist_cycle_receipts(composite, window_composite_receipt_path, latest_composite_receipt_path)
            return composite

    # Read state fingerprint before scheduler tick
    state_fingerprint_before = None
    if state_file.is_file():
        try:
            state_fingerprint_before = hashlib.sha256(state_file.read_bytes()).hexdigest()
        except Exception:
            pass
    composite["oos_state_fingerprint_before"] = state_fingerprint_before

    # STEP 2: Market-data OOS Accrual via Scheduler
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
    job_status = sched_tick.get("job_status") or sched_tick.get("status")
    cmd_class = sched_tick.get("command_classification") or sched_tick.get("classification")
    composite["scheduler_job_identity"] = sched_tick.get("job_id", "na")
    composite["scheduler_classification"] = cmd_class

    # Read state fingerprint after scheduler tick
    state_fingerprint_after = None
    if state_file.is_file():
        try:
            state_fingerprint_after = hashlib.sha256(state_file.read_bytes()).hexdigest()
        except Exception:
            pass
    composite["oos_state_fingerprint_after"] = state_fingerprint_after

    if job_status not in ("completed", "succeeded", "success", "no_op"):
        composite["classification"] = f"scheduler_failed_{cmd_class}"
        composite["blocker"] = f"scheduler_failed_{cmd_class}"
        composite["next_autonomous_action"] = "resolve_scheduler_failure"
        composite["completed_at_utc"] = datetime.now(UTC).isoformat()
        _persist_cycle_receipts(composite, window_composite_receipt_path, latest_composite_receipt_path)
        return composite

    # STEP 3: Bounded Clean-Source Paper Broker Observation (correct tuple unpacking)
    try:
        obs_receipt, inv_receipt = perform_genuine_paper_observation(
            paper_broker_read_authorized=paper_broker_read_authorized,
            allow_network=allow_network,
            repo_root=root_dir,
        )

        inv_bytes = json.dumps(inv_receipt, sort_keys=True).encode("utf-8")
        obs_bytes = json.dumps(obs_receipt, sort_keys=True).encode("utf-8")
        composite["broker_invocation_hash"] = hashlib.sha256(inv_bytes).hexdigest()
        composite["broker_observation_hash"] = hashlib.sha256(obs_bytes).hexdigest()
        composite["broker_observation_classification"] = obs_receipt.get("classification")

        stage_records = obs_receipt.get("stage_records", {})
        for stage, data in stage_records.items():
            if isinstance(data, dict):
                composite["broker_stage_attempt_counts"][stage] = data.get("attempt_count", 0)
                composite["broker_stage_completion_counts"][stage] = data.get("completion_count", 0)

        # STEP 4: Account Flatness Reconciliation
        acc_valid = obs_receipt.get("account_validation") == "success"
        pos_valid = obs_receipt.get("positions_validation") == "success"
        ord_valid = obs_receipt.get("orders_validation") == "success"
        asset_valid = obs_receipt.get("asset_validation") == "success"

        is_flat = (
            obs_receipt.get("observed_positions_count") == 0
            and obs_receipt.get("observed_open_orders_count") == 0
        )
        composite["account_flat_reconciled"] = bool(acc_valid and pos_valid and ord_valid and asset_valid and is_flat)

        if not composite["account_flat_reconciled"]:
            composite["classification"] = "broker_reconciliation_failed"
            composite["blocker"] = "broker_positions_or_orders_non_flat"
            composite["readiness_after"] = "R1"
            composite["completed_at_utc"] = datetime.now(UTC).isoformat()
            _persist_cycle_receipts(composite, window_composite_receipt_path, latest_composite_receipt_path)
            return composite

        composite["readiness_after"] = "R2"

    except BrokerObservationError as exc:
        inv_rec = exc.invocation_receipt or {}
        fail_rec = exc.failure_receipt or {}
        if inv_rec:
            inv_bytes = json.dumps(inv_rec, sort_keys=True).encode("utf-8")
            composite["broker_invocation_hash"] = hashlib.sha256(inv_bytes).hexdigest()
        if fail_rec:
            fail_bytes = json.dumps(fail_rec, sort_keys=True).encode("utf-8")
            composite["broker_failure_hash"] = hashlib.sha256(fail_bytes).hexdigest()

        stage_records = inv_rec.get("stage_records", {})
        for stage, data in stage_records.items():
            if isinstance(data, dict):
                composite["broker_stage_attempt_counts"][stage] = data.get("attempt_count", 0)
                composite["broker_stage_completion_counts"][stage] = data.get("completion_count", 0)

        composite["broker_observation_classification"] = fail_rec.get(
            "terminal_stable_classification", str(exc)
        )
        composite["classification"] = f"broker_observation_failed_{exc.__class__.__name__}"
        composite["blocker"] = f"broker_observation_failed_{exc}"
        composite["readiness_after"] = "R1"
        composite["completed_at_utc"] = datetime.now(UTC).isoformat()
        _persist_cycle_receipts(composite, window_composite_receipt_path, latest_composite_receipt_path)
        return composite
    except Exception as exc:
        composite["classification"] = f"broker_observation_failed_{exc.__class__.__name__}"
        composite["blocker"] = f"broker_observation_unexpected_{exc.__class__.__name__}"
        composite["readiness_after"] = "R1"
        composite["completed_at_utc"] = datetime.now(UTC).isoformat()
        _persist_cycle_receipts(composite, window_composite_receipt_path, latest_composite_receipt_path)
        return composite

    # STEP 5: Finalize Decision and Composite Receipt
    composite["decision"] = "hold_evidence_incomplete"
    composite["classification"] = "cycle_completed_hold"
    composite["completed_at_utc"] = datetime.now(UTC).isoformat()
    _persist_cycle_receipts(composite, window_composite_receipt_path, latest_composite_receipt_path)
    return composite


def _persist_cycle_receipts(
    composite: dict[str, Any],
    window_path: Path,
    latest_path: Path,
) -> None:
    """Persist composite cycle receipts atomically to both generation path and latest path."""
    _write_receipt_atomically(window_path, composite)
    _write_receipt_atomically(latest_path, composite)


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
