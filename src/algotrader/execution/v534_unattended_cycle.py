"""V5.34 Unattended paper-observed OOS burn-in autonomous operating cycle.

Composes clean-source admission, completed-hour OOS accrual (Tournament V2 OOS
scheduler), bounded expected-account Alpaca paper observation, account flatness
reconciliation, and immutable composite cycle receipt persistence.

Admission ordering contract: exact source provenance is validated before the
scheduler is constructed, before any market-data access, before any OOS state
initialization or accrual, and before any broker client construction. A dirty
worktree causes zero network calls, zero scheduler claims, and zero state
changes; the only artifact is an immutable blocked cycle receipt.

Idempotency contract: the idempotency key is the exact accepted scheduler
window and job identity, never the wall-clock hour. Original receipts are
immutable; duplicate invocations emit separate no-op receipts referencing the
original receipt path and canonical hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    PRODUCTION_INVOCATION_SCHEMA,
    PRODUCTION_OBSERVATION_SCHEMA,
    BrokerObservationError,
    PreflightCheckError,
    get_source_provenance,
    perform_genuine_paper_observation,
)

CYCLE_SCHEMA_VERSION = "v5_34_unattended_operating_cycle_receipt_v2"
CYCLE_INDEX_SCHEMA_VERSION = "v5_34_cycle_index_v1"
DEFAULT_CYCLE_OUTPUT_ROOT = Path("runs/v5_34_operating_cycle/latest")
DEFAULT_SCHEDULER_OUTPUT_ROOT = Path("runs/crypto_strategy_tournament/v2/latest")
DEFAULT_DISCOVERY_SOURCE = Path("runs/crypto_strategy_tournament/v1/input/crypto_1h_1y.csv")
DEFAULT_DISCOVERY_RECEIPT = Path("runs/crypto_strategy_tournament/v1/refresh/refresh_packet.json")
DEFAULT_READINESS_PACKET = Path("runs/crypto_supervised_readiness_trial/latest/readiness_packet.json")

COMPLETED_CYCLE_CLASSIFICATIONS = frozenset(
    {
        "cycle_completed_hold",
        "cycle_completed_hold_account_not_flat",
    }
)

_ACCRUAL_SUCCESS_CLASSIFICATIONS = frozenset(
    {"subprocess_completed", "preview_successful"}
)


class CycleContractError(ValueError):
    """Raised when a composed component returns an ambiguous result."""


def _bind_observation_receipts(
    result: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind the production observation result to named roles by schema.

    Refuses positional ambiguity: each element is identified by its exact
    schema version, so a reversed or malformed producer fails closed instead of
    silently mislabeling evidence.
    """
    if not isinstance(result, tuple) or len(result) != 2:
        raise CycleContractError("observation_result_not_pair")

    by_schema: dict[str, dict[str, Any]] = {}
    for element in result:
        if not isinstance(element, dict):
            raise CycleContractError("observation_result_element_not_mapping")
        schema = element.get("schema_version")
        if not isinstance(schema, str) or schema in by_schema:
            raise CycleContractError("observation_result_schema_ambiguous")
        by_schema[schema] = element

    observation_receipt = by_schema.get(PRODUCTION_OBSERVATION_SCHEMA)
    invocation_receipt = by_schema.get(PRODUCTION_INVOCATION_SCHEMA)
    if observation_receipt is None or invocation_receipt is None:
        raise CycleContractError("observation_result_schema_unrecognized")

    return observation_receipt, invocation_receipt


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
    invocation_source: str = "manual",
    readiness_packet_path: Path | str = DEFAULT_READINESS_PACKET,
) -> dict[str, Any]:
    """Run one production one-shot operating cycle.

    Every invocation persists exactly one new immutable receipt describing its
    truthful terminal classification; prior receipts are never modified.
    """
    root_dir = Path(repo_root or Path.cwd()).resolve()
    out_dir = Path(output_root)
    sched_out_dir = Path(scheduler_output_root)
    database_path = Path(db_path) if db_path else sched_out_dir / "scheduler_state.db"

    if invocation_source not in ("manual", "scheduled"):
        raise CycleContractError("invocation_source_invalid")

    invocation_id = str(uuid.uuid4())
    now_utc = _parse_datetime(as_of) if as_of is not None else datetime.now(UTC)

    composite: dict[str, Any] = {
        "schema_version": CYCLE_SCHEMA_VERSION,
        "invocation_id": invocation_id,
        "invocation_source": invocation_source,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "completed_at_utc": None,
        "cycle_as_of_utc": now_utc.isoformat(),
        "classification": None,
        "exact_blocker": None,
        "idempotent_replay": False,
        "duplicate_of_receipt_path": None,
        "duplicate_of_receipt_sha256": None,
        # Source admission bindings
        "source_commit_sha": None,
        "source_tree_sha": None,
        "source_worktree_clean": False,
        "adapter_source_bundle_sha256": None,
        # Exact scheduler window bindings
        "scheduler_job_identity": None,
        "scheduler_job_status": None,
        "scheduler_classification": None,
        "accepted_window_identity": None,
        "requested_start_bar_open": None,
        "requested_end_bar_open": None,
        "provider_as_of_boundary": None,
        "oos_frontier_before": None,
        "oos_frontier_after": None,
        "oos_state_fingerprint_before": None,
        "oos_state_fingerprint_after": None,
        "market_data_receipt_paths": None,
        "market_data_receipt_hashes": None,
        "scheduler_receipt_path": None,
        "scheduler_receipt_sha256": None,
        # Broker observation bindings
        "broker_observation_classification": None,
        "broker_observation_receipt_path": None,
        "broker_observation_receipt_sha256": None,
        "broker_invocation_receipt_path": None,
        "broker_invocation_receipt_sha256": None,
        "broker_failure_receipt_path": None,
        "broker_failure_receipt_sha256": None,
        "broker_stage_attempt_counts": None,
        "broker_stage_completion_counts": None,
        "observed_positions_count": None,
        "observed_open_orders_count": None,
        "account_flat_reconciled": False,
        # Readiness and decision bindings
        "readiness_rung_before": None,
        "readiness_rung_after": None,
        "decision": None,
        "paper_submit_performed": False,
        "paper_mutation_performed": False,
        "mutation_count": 0,
        "submission_count": 0,
        "next_autonomous_action": None,
    }

    # ------------------------------------------------------------------
    # Stage 1: exact source-provenance admission BEFORE any other effect.
    # ------------------------------------------------------------------
    try:
        provenance = get_source_provenance(root_dir)
    except PreflightCheckError as exc:
        composite["classification"] = f"cycle_blocked_source_admission_{exc}"
        composite["exact_blocker"] = str(exc)
        composite["next_autonomous_action"] = "restore_clean_committed_source_and_reinvoke"
        return _finalize_receipt(out_dir, composite, index_accepted=False)

    composite["source_commit_sha"] = provenance["source_commit_sha"]
    composite["source_tree_sha"] = provenance["source_tree_sha"]
    composite["source_worktree_clean"] = provenance["source_worktree_clean"]
    composite["adapter_source_bundle_sha256"] = provenance["adapter_source_bundle_sha256"]

    readiness_before = _read_readiness_rung(Path(readiness_packet_path))
    composite["readiness_rung_before"] = readiness_before

    # ------------------------------------------------------------------
    # Stage 2: completed-hour OOS accrual through the durable scheduler.
    # Construction happens only after clean-source admission.
    # ------------------------------------------------------------------
    from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
        OneShotExecutor,
        RealCommandDispatcher,
    )

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

    receipts_before = _list_scheduler_receipts(sched_out_dir)
    try:
        sched_tick = executor.tick(now_utc)
    except Exception as exc:
        composite["classification"] = f"cycle_failed_scheduler_{exc.__class__.__name__}"
        composite["exact_blocker"] = "scheduler_tick_exception"
        composite["next_autonomous_action"] = "await_operator_review"
        return _finalize_receipt(out_dir, composite, index_accepted=False)

    scheduler_receipt_path = _newest_scheduler_receipt(sched_out_dir, receipts_before)
    if scheduler_receipt_path is not None:
        composite["scheduler_receipt_path"] = str(scheduler_receipt_path)
        composite["scheduler_receipt_sha256"] = _file_sha256(scheduler_receipt_path)

    job_id = str(sched_tick.get("job_id") or "na")
    job_status = str(sched_tick.get("job_status") or "")
    sched_class = str(sched_tick.get("command_classification") or "")
    requested_start = sched_tick.get("requested_start_bar_open")
    requested_end = sched_tick.get("requested_end_bar_open")

    composite["scheduler_job_identity"] = job_id
    composite["scheduler_job_status"] = job_status
    composite["scheduler_classification"] = sched_class
    composite["requested_start_bar_open"] = requested_start
    composite["requested_end_bar_open"] = requested_end
    composite["provider_as_of_boundary"] = sched_tick.get("provider_as_of_boundary")
    composite["oos_frontier_before"] = sched_tick.get("accepted_frontier_bar_open")
    composite["oos_frontier_after"] = sched_tick.get("expected_frontier_bar_open")
    composite["oos_state_fingerprint_before"] = sched_tick.get("source_state_hash_before")
    composite["oos_state_fingerprint_after"] = sched_tick.get("source_state_hash_after")
    composite["market_data_receipt_paths"] = list(
        sched_tick.get("native_tournament_receipt_paths") or []
    )
    composite["market_data_receipt_hashes"] = list(
        sched_tick.get("native_tournament_receipt_hashes") or []
    )

    if requested_start and requested_end:
        composite["accepted_window_identity"] = f"{requested_start}_{requested_end}"

    index = _load_index(out_dir)

    fresh_accrual = (
        job_status == "completed" and sched_class in _ACCRUAL_SUCCESS_CLASSIFICATIONS
    )

    if not fresh_accrual:
        duplicate_entry = _resolve_duplicate_entry(index, sched_tick, job_id, sched_class)
        if duplicate_entry is not None:
            composite["classification"] = "duplicate_window_no_op"
            composite["idempotent_replay"] = True
            composite["duplicate_of_receipt_path"] = duplicate_entry["receipt_path"]
            composite["duplicate_of_receipt_sha256"] = duplicate_entry["receipt_sha256"]
            composite["exact_blocker"] = "none"
            composite["decision"] = "hold_evidence_incomplete"
            composite["readiness_rung_after"] = readiness_before
            composite["next_autonomous_action"] = "await_next_scheduled_hourly_cycle"
            return _finalize_receipt(out_dir, composite, index_accepted=False)

        if sched_class == "accrual_complete":
            composite["classification"] = "cycle_no_action_accrual_complete"
            composite["exact_blocker"] = "tournament_accrual_complete"
            composite["next_autonomous_action"] = "await_tournament_terminal_evaluation"
        elif job_status == "failed":
            composite["classification"] = f"cycle_failed_scheduler_{sched_class}"
            composite["exact_blocker"] = sched_class
            composite["next_autonomous_action"] = "await_operator_review"
        else:
            composite["classification"] = f"cycle_blocked_scheduler_{sched_class}"
            composite["exact_blocker"] = sched_class
            composite["next_autonomous_action"] = "await_next_scheduled_hourly_cycle"
        composite["decision"] = "hold_evidence_incomplete"
        composite["readiness_rung_after"] = readiness_before
        return _finalize_receipt(out_dir, composite, index_accepted=False)

    window_key = _window_key(job_id, composite["accepted_window_identity"])
    existing = index["entries"].get(window_key)
    if existing is not None:
        composite["classification"] = "duplicate_window_no_op"
        composite["idempotent_replay"] = True
        composite["duplicate_of_receipt_path"] = existing["receipt_path"]
        composite["duplicate_of_receipt_sha256"] = existing["receipt_sha256"]
        composite["exact_blocker"] = "none"
        composite["decision"] = "hold_evidence_incomplete"
        composite["readiness_rung_after"] = readiness_before
        composite["next_autonomous_action"] = "await_next_scheduled_hourly_cycle"
        return _finalize_receipt(out_dir, composite, index_accepted=False)

    # ------------------------------------------------------------------
    # Stage 3: bounded expected-account paper observation.
    # ------------------------------------------------------------------
    if not paper_broker_read_authorized or not allow_network:
        composite["classification"] = "cycle_blocked_broker_observation_not_authorized"
        composite["exact_blocker"] = "broker_observation_not_authorized"
        composite["decision"] = "hold_evidence_incomplete"
        composite["readiness_rung_after"] = readiness_before
        composite["next_autonomous_action"] = "await_operator_authorization"
        return _finalize_receipt(out_dir, composite, index_accepted=False)

    broker_dir = out_dir / "broker" / invocation_id
    try:
        result = perform_genuine_paper_observation(
            paper_broker_read_authorized=paper_broker_read_authorized,
            allow_network=allow_network,
            repo_root=root_dir,
        )
        observation_receipt, invocation_receipt = _bind_observation_receipts(result)
    except BrokerObservationError as exc:
        composite["classification"] = f"cycle_failed_broker_observation_{exc}"
        composite["exact_blocker"] = str(exc)
        if exc.invocation_receipt is not None:
            path = _write_json_immutable(
                broker_dir / "invocation_receipt.json", exc.invocation_receipt
            )
            composite["broker_invocation_receipt_path"] = str(path)
            composite["broker_invocation_receipt_sha256"] = _file_sha256(path)
            composite["broker_stage_attempt_counts"] = _stage_counts(
                exc.invocation_receipt, "attempt_count"
            )
            composite["broker_stage_completion_counts"] = _stage_counts(
                exc.invocation_receipt, "completion_count"
            )
        if exc.failure_receipt is not None:
            path = _write_json_immutable(
                broker_dir / "failure_receipt.json", exc.failure_receipt
            )
            composite["broker_failure_receipt_path"] = str(path)
            composite["broker_failure_receipt_sha256"] = _file_sha256(path)
        composite["decision"] = "hold_evidence_incomplete"
        composite["readiness_rung_after"] = readiness_before
        composite["next_autonomous_action"] = "await_operator_review"
        return _finalize_receipt(out_dir, composite, index_accepted=False)
    except (PreflightCheckError, CycleContractError) as exc:
        composite["classification"] = f"cycle_blocked_broker_observation_{exc}"
        composite["exact_blocker"] = str(exc)
        composite["decision"] = "hold_evidence_incomplete"
        composite["readiness_rung_after"] = readiness_before
        composite["next_autonomous_action"] = "await_operator_review"
        return _finalize_receipt(out_dir, composite, index_accepted=False)

    obs_path = _write_json_immutable(
        broker_dir / "observation_receipt.json", observation_receipt
    )
    inv_path = _write_json_immutable(
        broker_dir / "invocation_receipt.json", invocation_receipt
    )
    composite["broker_observation_receipt_path"] = str(obs_path)
    composite["broker_observation_receipt_sha256"] = _file_sha256(obs_path)
    composite["broker_invocation_receipt_path"] = str(inv_path)
    composite["broker_invocation_receipt_sha256"] = _file_sha256(inv_path)
    composite["broker_observation_classification"] = observation_receipt.get(
        "source_classification"
    )
    composite["broker_stage_attempt_counts"] = _stage_counts(
        invocation_receipt, "attempt_count"
    )
    composite["broker_stage_completion_counts"] = _stage_counts(
        invocation_receipt, "completion_count"
    )

    # ------------------------------------------------------------------
    # Stage 4: account flatness reconciliation from validated evidence.
    # ------------------------------------------------------------------
    stage_records = invocation_receipt.get("stage_records") or {}
    stages_valid = all(
        isinstance(record, dict)
        and record.get("read_classification") == "success"
        and record.get("validation_classification") == "success"
        for record in stage_records.values()
    ) and len(stage_records) == 4

    positions = observation_receipt.get("positions")
    open_orders = observation_receipt.get("open_orders")
    if not stages_valid or not isinstance(positions, list) or not isinstance(open_orders, list):
        composite["classification"] = "cycle_failed_broker_evidence_invalid"
        composite["exact_blocker"] = "broker_evidence_invalid"
        composite["decision"] = "hold_evidence_incomplete"
        composite["readiness_rung_after"] = readiness_before
        composite["next_autonomous_action"] = "await_operator_review"
        return _finalize_receipt(out_dir, composite, index_accepted=False)

    composite["observed_positions_count"] = len(positions)
    composite["observed_open_orders_count"] = len(open_orders)
    account_flat = len(positions) == 0 and len(open_orders) == 0
    composite["account_flat_reconciled"] = account_flat

    # ------------------------------------------------------------------
    # Stage 5: evidence-gated decision. Tournament V2 is nonterminal, so the
    # only valid directional decision is a canonical evidence-incomplete hold.
    # ------------------------------------------------------------------
    composite["decision"] = "hold_evidence_incomplete"
    composite["readiness_rung_after"] = readiness_before if account_flat else "R1"
    if account_flat:
        composite["classification"] = "cycle_completed_hold"
        composite["exact_blocker"] = "none"
    else:
        composite["classification"] = "cycle_completed_hold_account_not_flat"
        composite["exact_blocker"] = "blocked_external_paper_account_state"
    composite["next_autonomous_action"] = "await_next_scheduled_hourly_cycle"

    return _finalize_receipt(out_dir, composite, index_accepted=True)


def _resolve_duplicate_entry(
    index: dict[str, Any],
    sched_tick: dict[str, Any],
    job_id: str,
    sched_class: str,
) -> dict[str, Any] | None:
    """Resolve a non-accrual tick to the original accepted receipt, if any.

    ``idempotent_no_op`` binds by exact job identity and window. A
    ``no_eligible_closed_window`` tick is a duplicate only when the scheduler
    frontier still equals the expected frontier of an indexed accepted cycle,
    meaning no new window opened since that exact job.
    """
    entries: dict[str, dict[str, Any]] = index["entries"]

    if sched_class == "idempotent_no_op":
        requested_start = sched_tick.get("requested_start_bar_open")
        requested_end = sched_tick.get("requested_end_bar_open")
        if requested_start and requested_end:
            key = _window_key(job_id, f"{requested_start}_{requested_end}")
            return entries.get(key)
        return None

    if sched_class == "no_eligible_closed_window":
        frontier = sched_tick.get("accepted_frontier_bar_open")
        if not frontier:
            return None
        for entry in entries.values():
            if frontier in (
                entry.get("requested_end_bar_open"),
                entry.get("oos_frontier_after"),
            ):
                return entry
        return None

    return None


def _window_key(job_id: str, window_identity: str | None) -> str:
    return f"{job_id}:{window_identity or 'na'}"


def _read_readiness_rung(packet_path: Path) -> str:
    """Derive the readiness rung from consumed readiness evidence.

    R2 requires an accepted broker-observed readiness packet; anything else
    (missing, unparseable, or non-accepted evidence) retains R1.
    """
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "R1"
    if not isinstance(packet, dict):
        return "R1"
    if (
        packet.get("trial_classification") == "accepted"
        and packet.get("readiness_rung") == "R2"
    ):
        return "R2"
    return "R1"


def _stage_counts(invocation_receipt: dict[str, Any], counter: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    stage_records = invocation_receipt.get("stage_records") or {}
    for stage, record in stage_records.items():
        if isinstance(record, dict):
            counts[stage] = int(record.get(counter) or 0)
    return counts


def _list_scheduler_receipts(sched_out_dir: Path) -> set[str]:
    folder = sched_out_dir / "scheduler_receipts"
    if not folder.is_dir():
        return set()
    return {p.name for p in folder.glob("receipt_*.json")}


def _newest_scheduler_receipt(
    sched_out_dir: Path, receipts_before: set[str]
) -> Path | None:
    folder = sched_out_dir / "scheduler_receipts"
    if not folder.is_dir():
        return None
    new_receipts = [
        p for p in folder.glob("receipt_*.json") if p.name not in receipts_before
    ]
    if not new_receipts:
        return None
    return max(new_receipts, key=lambda p: (p.stat().st_mtime, p.name))


def _load_index(out_dir: Path) -> dict[str, Any]:
    index_path = out_dir / "cycle_index.json"
    if index_path.is_file():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            if (
                isinstance(index, dict)
                and index.get("schema_version") == CYCLE_INDEX_SCHEMA_VERSION
                and isinstance(index.get("entries"), dict)
            ):
                return index
        except (OSError, ValueError):
            pass
    return {"schema_version": CYCLE_INDEX_SCHEMA_VERSION, "entries": {}}


def _finalize_receipt(
    out_dir: Path, composite: dict[str, Any], *, index_accepted: bool
) -> dict[str, Any]:
    composite["completed_at_utc"] = datetime.now(UTC).isoformat()

    canonical_str = json.dumps(composite, sort_keys=True, separators=(",", ":"))
    composite["canonical_receipt_sha256"] = hashlib.sha256(
        canonical_str.encode("utf-8")
    ).hexdigest()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    receipt_path = (
        out_dir
        / "receipts"
        / f"cycle_{timestamp}_{composite['invocation_id']}.json"
    )
    _write_json_immutable(receipt_path, composite)

    if index_accepted:
        index = _load_index(out_dir)
        key = _window_key(
            str(composite["scheduler_job_identity"]),
            composite["accepted_window_identity"],
        )
        index["entries"][key] = {
            "receipt_path": str(receipt_path),
            "receipt_sha256": composite["canonical_receipt_sha256"],
            "classification": composite["classification"],
            "invocation_source": composite["invocation_source"],
            "scheduler_job_identity": composite["scheduler_job_identity"],
            "accepted_window_identity": composite["accepted_window_identity"],
            "requested_end_bar_open": composite["requested_end_bar_open"],
            "oos_frontier_after": composite["oos_frontier_after"],
        }
        _write_json_atomic(out_dir / "cycle_index.json", index)

    # Convenience copy of the newest receipt; history above stays immutable.
    _write_json_atomic(out_dir / "composite_cycle_receipt.json", composite)
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


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _write_json_immutable(path: Path, data: dict[str, Any]) -> Path:
    """Write a receipt exactly once; refuse to overwrite existing evidence."""
    if path.exists():
        raise CycleContractError(f"immutable_receipt_exists:{path.name}")
    _write_json_atomic(path, data)
    return path


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    temp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="V5.34 Unattended Paper-Observed OOS Burn-In Cycle"
    )
    parser.add_argument("--output-root", default=str(DEFAULT_CYCLE_OUTPUT_ROOT))
    parser.add_argument(
        "--scheduler-output-root", default=str(DEFAULT_SCHEDULER_OUTPUT_ROOT)
    )
    parser.add_argument("--discovery-source", default=str(DEFAULT_DISCOVERY_SOURCE))
    parser.add_argument("--discovery-receipt", default=str(DEFAULT_DISCOVERY_RECEIPT))
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--scheduler-enabled", action="store_true")
    parser.add_argument("--market-data-read-authorized", action="store_true")
    parser.add_argument("--paper-broker-read-authorized", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--as-of", default=None)
    parser.add_argument(
        "--invocation-source", choices=("manual", "scheduled"), default="manual"
    )
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
        invocation_source=args.invocation_source,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
