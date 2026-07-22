"""Schema validation and fail-closed V5.35 burn-in status derivation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.execution.v535_unattended_readonly import (
    EXPECTED_PAPER_ENDPOINT,
    V535_CYCLE_SCHEMA,
    V535_DUPLICATE_SCHEMA,
    V535_ROLE_SCHEMA,
    V535_TASK_ARGUMENTS,
    V535_TASK_EXECUTE,
    V535_TASK_IDENTITY,
    AcceptedWindow,
    TaskSchedulerSnapshot,
    _canonical_hash,
    _file_sha256,
    _no_mutation_facts,
    _parse_datetime,
    _write_json_immutable,
)


V535_BURN_IN_SCHEMA = "v5_35_fail_closed_burn_in_status_v1"
BURN_IN_TARGET_CYCLES = 24
_ROLES = (
    "source",
    "scheduler",
    "market_data",
    "broker",
    "readiness",
    "decision",
)
_COMMON_ROLE_KEYS = {
    "schema_version",
    "evidence_role",
    "cycle_id",
    "scheduler_job_identity",
    "accepted_window",
    "window_start_bar_open",
    "window_end_bar_open",
    "provider_as_of_boundary",
    "canonical_receipt_sha256",
}
_MUTATION_FIELDS = set(_no_mutation_facts())


@dataclass(frozen=True, slots=True)
class EvidenceValidation:
    valid: bool
    errors: tuple[str, ...]
    composite: Mapping[str, object] | None
    roles: Mapping[str, Mapping[str, object]]


def validate_completed_cycle_evidence(
    cycle_path: Path | str,
    *,
    output_root: Path | str | None = None,
) -> EvidenceValidation:
    """Validate one complete cycle and every cross-hashed referenced receipt."""

    path = Path(cycle_path)
    root = Path(output_root) if output_root is not None else path.parent.parent
    errors: list[str] = []
    composite = _load_object(path, errors, "cycle_unreadable")
    if composite is None:
        return EvidenceValidation(False, tuple(errors), None, {})
    _validate_composite_shape(composite, errors)
    if errors:
        return EvidenceValidation(False, tuple(dict.fromkeys(errors)), composite, {})

    references = composite["evidence_references"]
    assert isinstance(references, Mapping)
    roles: dict[str, Mapping[str, object]] = {}
    resolved_root = root.resolve()
    for role in _ROLES:
        reference = references.get(role)
        if not isinstance(reference, Mapping) or set(reference) != {"path", "sha256"}:
            errors.append(f"{role}_reference_malformed")
            continue
        relative_value = reference.get("path")
        digest = reference.get("sha256")
        if type(relative_value) is not str or not _is_sha256(digest):
            errors.append(f"{role}_reference_malformed")
            continue
        relative = Path(relative_value)
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"{role}_reference_path_escape")
            continue
        role_path = (root / relative).resolve()
        try:
            role_path.relative_to(resolved_root)
        except ValueError:
            errors.append(f"{role}_reference_path_escape")
            continue
        role_receipt = _load_object(role_path, errors, f"{role}_receipt_unreadable")
        if role_receipt is None:
            continue
        if digest != _canonical_hash(role_receipt):
            errors.append(f"{role}_reference_hash_mismatch")
        if role_receipt.get("canonical_receipt_sha256") != digest:
            errors.append(f"{role}_self_hash_mismatch")
        if not role_path.name.endswith(f"_{digest}.json"):
            errors.append(f"{role}_content_address_mismatch")
        _validate_role_shape(role, role_receipt, errors)
        _validate_common_binding(composite, role_receipt, role, errors)
        roles[role] = role_receipt

    if set(roles) == set(_ROLES):
        _validate_cross_hashes(composite, roles, errors)
        _validate_source(roles["source"], errors)
        _validate_scheduler(roles["scheduler"], errors)
        _validate_market(roles["market_data"], root, errors)
        _validate_broker(roles["broker"], errors)
        _validate_readiness(roles["readiness"], errors)
        _validate_decision(roles["decision"], errors)

    return EvidenceValidation(
        not errors,
        tuple(dict.fromkeys(errors)),
        composite,
        roles,
    )


def build_v535_burn_in_status(
    *,
    output_root: Path | str,
    expected_windows: Sequence[AcceptedWindow],
    task_snapshot: TaskSchedulerSnapshot,
    as_of: datetime,
    scheduler_job_identity: str = V535_TASK_IDENTITY,
    expected_task_execute: str = V535_TASK_EXECUTE,
    expected_task_arguments: str = V535_TASK_ARGUMENTS,
    target_cycles: int = BURN_IN_TARGET_CYCLES,
    max_frontier_lag: timedelta = timedelta(hours=2),
    write_packet: bool = True,
) -> dict[str, object]:
    """Derive active/complete only from an exact target-window evidence set."""

    root = Path(output_root)
    now = _aware_utc(as_of)
    blockers: list[str] = []
    if type(target_cycles) is not int or target_cycles != BURN_IN_TARGET_CYCLES:
        blockers.append("burn_in_target_must_equal_24")
    if not isinstance(max_frontier_lag, timedelta) or max_frontier_lag <= timedelta(0):
        blockers.append("frontier_lag_bound_malformed")

    windows = tuple(expected_windows)
    if any(not isinstance(window, AcceptedWindow) for window in windows):
        blockers.append("target_window_malformed")
        windows = ()
    identities = tuple(window.identity for window in windows)
    if len(set(identities)) != len(identities):
        blockers.append("target_window_ambiguous")
    if len(windows) > target_cycles:
        blockers.append("target_window_count_exceeds_24")
    for previous, current in zip(windows, windows[1:]):
        if current.start_bar_open != previous.start_bar_open + timedelta(hours=1):
            blockers.append("target_windows_non_contiguous")
            break

    validations: dict[str, EvidenceValidation] = {}
    invalid_receipt_count = 0
    blocked_cycle_count = 0
    failed_cycle_count = 0
    ambiguous_cycle_count = 0
    cycle_dir = root / "cycles"
    if cycle_dir.is_dir():
        for cycle_path in sorted(cycle_dir.glob("cycle_*.json")):
            raw_errors: list[str] = []
            raw = _load_object(cycle_path, raw_errors, "cycle_unreadable")
            if raw is None or raw.get("schema_version") != V535_CYCLE_SCHEMA:
                invalid_receipt_count += 1
                continue
            if raw.get("canonical_receipt_sha256") != _canonical_hash(raw):
                invalid_receipt_count += 1
                continue
            classification = raw.get("classification")
            if classification == "completed_read_only_cycle":
                validation = validate_completed_cycle_evidence(
                    cycle_path,
                    output_root=root,
                )
                if not validation.valid or validation.composite is None:
                    invalid_receipt_count += 1
                    continue
                identity = str(validation.composite.get("accepted_window", ""))
                if identity in validations:
                    ambiguous_cycle_count += 1
                else:
                    validations[identity] = validation
            elif type(classification) is str and classification.startswith("blocked_"):
                blocked_cycle_count += 1
            elif type(classification) is str and classification.startswith("failed_"):
                failed_cycle_count += 1
            else:
                invalid_receipt_count += 1

    duplicate_count, invalid_duplicate_count = _validate_duplicate_receipts(root)
    invalid_receipt_count += invalid_duplicate_count
    if invalid_receipt_count:
        blockers.append("invalid_cycle_evidence")
    if blocked_cycle_count:
        blockers.append("blocked_cycle_evidence_present")
    if failed_cycle_count:
        blockers.append("failed_cycle_evidence_present")
    if ambiguous_cycle_count:
        blockers.append("ambiguous_cycle_evidence")

    missing = [identity for identity in identities if identity not in validations]
    if missing:
        blockers.append("target_window_evidence_missing")
    extra_target_validations = [
        identity
        for identity in validations
        if identity in set(identities)
    ]
    if len(extra_target_validations) != len(identities):
        blockers.append("target_window_binding_mismatch")

    selected = [validations[identity] for identity in identities if identity in validations]
    source_bindings: set[tuple[object, object, object]] = set()
    for validation in selected:
        source = validation.roles.get("source", {})
        source_bindings.add(
            (
                source.get("source_commit_sha"),
                source.get("source_tree_sha"),
                source.get("source_bundle_sha256"),
            )
        )
    if len(source_bindings) > 1:
        blockers.append("source_binding_mismatch_across_cycles")

    _validate_current_task(
        task_snapshot,
        scheduler_job_identity=scheduler_job_identity,
        expected_task_execute=expected_task_execute,
        expected_task_arguments=expected_task_arguments,
        blockers=blockers,
    )
    if windows:
        latest = windows[-1]
        if task_snapshot.last_run_time < latest.provider_as_of_boundary:
            blockers.append("scheduled_task_last_run_mismatch")
        lag = now - latest.provider_as_of_boundary
        if lag < timedelta(0) or lag > max_frontier_lag:
            blockers.append("frontier_lag_out_of_bounds")
    else:
        lag = None

    if not windows:
        status = "blocked" if blockers else "not_started"
    elif blockers:
        status = "blocked"
    elif len(windows) < target_cycles:
        status = "active"
    elif len(windows) == target_cycles:
        status = "complete"
    else:
        status = "blocked"

    packet: dict[str, object] = {
        "schema_version": V535_BURN_IN_SCHEMA,
        "burn_in_status": status,
        "as_of_utc": now.isoformat(),
        "scheduler_job_identity": scheduler_job_identity,
        "target_cycle_count": target_cycles,
        "target_window_count": len(windows),
        "valid_target_cycle_count": len(selected),
        "target_windows": list(identities),
        "invalid_receipt_count": invalid_receipt_count,
        "blocked_cycle_count": blocked_cycle_count,
        "failed_cycle_count": failed_cycle_count,
        "ambiguous_cycle_count": ambiguous_cycle_count,
        "duplicate_no_op_count": duplicate_count,
        "missing_target_window_count": len(missing),
        "frontier_lag_seconds": None if lag is None else lag.total_seconds(),
        "max_frontier_lag_seconds": max_frontier_lag.total_seconds(),
        "task_health": {
            "task_identity": task_snapshot.task_identity,
            "enabled": task_snapshot.enabled,
            "state": task_snapshot.state,
            "action_execute": task_snapshot.action_execute,
            "action_arguments": task_snapshot.action_arguments,
            "last_task_result": task_snapshot.last_task_result,
            "last_run_time": task_snapshot.last_run_time.isoformat(),
            "observed_at": task_snapshot.observed_at.isoformat(),
        },
        "blockers": list(dict.fromkeys(blockers)),
        "completed_cycle_sha256": [
            str(validation.composite["canonical_receipt_sha256"])
            for validation in selected
            if validation.composite is not None
        ],
        "account_flat_reconciled": bool(selected)
        and all(
            validation.composite.get("account_flat_reconciled") is True
            for validation in selected
            if validation.composite is not None
        ),
        **_no_mutation_facts(),
    }
    packet["canonical_receipt_sha256"] = _canonical_hash(packet)
    if write_packet:
        digest = str(packet["canonical_receipt_sha256"])
        _write_json_immutable(
            root / "burn_in" / f"status_{digest}.json",
            packet,
        )
    return packet


def _validate_composite_shape(
    composite: Mapping[str, object],
    errors: list[str],
) -> None:
    expected = {
        "schema_version",
        "classification",
        "invocation_source",
        "cycle_id",
        "scheduler_job_identity",
        "accepted_window",
        "window_start_bar_open",
        "window_end_bar_open",
        "provider_as_of_boundary",
        "completed_at_utc",
        "evidence_references",
        "account_flat_reconciled",
        "production_dispatcher",
        "canonical_receipt_sha256",
        *_MUTATION_FIELDS,
    }
    if set(composite) != expected:
        errors.append("cycle_schema_malformed")
    if composite.get("schema_version") != V535_CYCLE_SCHEMA:
        errors.append("cycle_schema_version_mismatch")
    if composite.get("classification") != "completed_read_only_cycle":
        errors.append("cycle_not_completed")
    if composite.get("invocation_source") != "scheduled":
        errors.append("cycle_not_scheduled")
    if composite.get("production_dispatcher") != "RealCommandDispatcher":
        errors.append("production_dispatcher_mismatch")
    if composite.get("account_flat_reconciled") is not True:
        errors.append("cycle_non_flat")
    _require_no_mutations(composite, errors, "cycle")
    if composite.get("canonical_receipt_sha256") != _canonical_hash(composite):
        errors.append("cycle_self_hash_mismatch")
    references = composite.get("evidence_references")
    if not isinstance(references, Mapping) or set(references) != set(_ROLES):
        errors.append("cycle_evidence_references_malformed")
    _validate_window_fields(composite, errors, "cycle")


def _validate_role_shape(
    role: str,
    receipt: Mapping[str, object],
    errors: list[str],
) -> None:
    role_keys = {
        "source": {
            "source_commit_sha",
            "source_tree_sha",
            "source_worktree_clean",
            "source_branch_or_detached",
            "source_bundle_sha256",
            "source_bundle_manifest",
        },
        "scheduler": {
            "task_identity",
            "task_enabled",
            "task_state",
            "task_action_execute",
            "task_action_arguments",
            "last_task_result",
            "last_run_time",
            "observed_at",
            "source_receipt_sha256",
        },
        "market_data": {
            "dispatch_type",
            "dispatch_status",
            "dispatch_classification",
            "market_data_fetch_occurred",
            "network_access_attempted",
            "artifact_manifest",
            "source_receipt_sha256",
            "scheduler_receipt_sha256",
            *_MUTATION_FIELDS,
        },
        "broker": {
            "observation_classification",
            "observed_at",
            "paper_endpoint",
            "expected_account_match",
            "account_active",
            "account_flat_reconciled",
            "position_count",
            "open_order_count",
            "target_asset_valid",
            "read_counts",
            "broker_read_occurred",
            "source_receipt_sha256",
            "scheduler_receipt_sha256",
            *_MUTATION_FIELDS,
        },
        "readiness": {
            "readiness_classification",
            "blockers",
            "account_flat_reconciled",
            "source_receipt_sha256",
            "scheduler_receipt_sha256",
            "market_data_receipt_sha256",
            "broker_receipt_sha256",
            *_MUTATION_FIELDS,
        },
        "decision": {
            "decision",
            "decision_classification",
            "readiness_receipt_sha256",
            "account_flat_reconciled",
            *_MUTATION_FIELDS,
        },
    }[role]
    if set(receipt) != _COMMON_ROLE_KEYS | role_keys:
        errors.append(f"{role}_schema_malformed")
    if receipt.get("schema_version") != V535_ROLE_SCHEMA:
        errors.append(f"{role}_schema_version_mismatch")
    if receipt.get("evidence_role") != role:
        errors.append(f"{role}_role_mismatch")
    _validate_window_fields(receipt, errors, role)


def _validate_common_binding(
    composite: Mapping[str, object],
    receipt: Mapping[str, object],
    role: str,
    errors: list[str],
) -> None:
    for key in (
        "cycle_id",
        "scheduler_job_identity",
        "accepted_window",
        "window_start_bar_open",
        "window_end_bar_open",
        "provider_as_of_boundary",
    ):
        if receipt.get(key) != composite.get(key):
            errors.append(f"{role}_{key}_mismatch")


def _validate_cross_hashes(
    composite: Mapping[str, object],
    roles: Mapping[str, Mapping[str, object]],
    errors: list[str],
) -> None:
    references = composite["evidence_references"]
    assert isinstance(references, Mapping)
    hashes = {
        role: str(cast_ref["sha256"])
        for role, cast_ref in references.items()
        if isinstance(cast_ref, Mapping)
    }
    expectations = {
        ("scheduler", "source_receipt_sha256"): "source",
        ("market_data", "source_receipt_sha256"): "source",
        ("market_data", "scheduler_receipt_sha256"): "scheduler",
        ("broker", "source_receipt_sha256"): "source",
        ("broker", "scheduler_receipt_sha256"): "scheduler",
        ("readiness", "source_receipt_sha256"): "source",
        ("readiness", "scheduler_receipt_sha256"): "scheduler",
        ("readiness", "market_data_receipt_sha256"): "market_data",
        ("readiness", "broker_receipt_sha256"): "broker",
        ("decision", "readiness_receipt_sha256"): "readiness",
    }
    for (role, field), target_role in expectations.items():
        if roles[role].get(field) != hashes.get(target_role):
            errors.append(f"{role}_{field}_mismatch")


def _validate_source(receipt: Mapping[str, object], errors: list[str]) -> None:
    for field, length in (
        ("source_commit_sha", 40),
        ("source_tree_sha", 40),
        ("source_bundle_sha256", 64),
    ):
        value = receipt.get(field)
        if not _is_hex(value, length):
            errors.append(f"{field}_malformed")
    if receipt.get("source_worktree_clean") is not True:
        errors.append("source_worktree_not_clean")
    manifest = receipt.get("source_bundle_manifest")
    if not isinstance(manifest, Mapping) or not manifest:
        errors.append("source_bundle_manifest_malformed")
        return
    if any(type(path) is not str or not _is_sha256(value) for path, value in manifest.items()):
        errors.append("source_bundle_manifest_malformed")
        return
    digest = hashlib.sha256()
    for relative_path, file_hash in sorted(manifest.items()):
        digest.update(f"{relative_path}:{file_hash}\n".encode("utf-8"))
    if digest.hexdigest() != receipt.get("source_bundle_sha256"):
        errors.append("source_bundle_hash_mismatch")


def _validate_scheduler(receipt: Mapping[str, object], errors: list[str]) -> None:
    if receipt.get("task_identity") != V535_TASK_IDENTITY:
        errors.append("scheduler_task_identity_mismatch")
    if receipt.get("task_enabled") is not True:
        errors.append("scheduler_task_disabled")
    if receipt.get("task_state") not in {"Ready", "Running"}:
        errors.append("scheduler_task_state_failed")
    if str(receipt.get("task_action_execute", "")).lower() != V535_TASK_EXECUTE.lower():
        errors.append("scheduler_task_action_mismatch")
    if receipt.get("task_action_arguments") != V535_TASK_ARGUMENTS:
        errors.append("scheduler_task_action_mismatch")
    if receipt.get("last_task_result") != 0:
        errors.append("scheduler_task_result_failed")
    try:
        last_run = _parse_datetime(receipt.get("last_run_time"))
        observed = _parse_datetime(receipt.get("observed_at"))
        provider_as_of = _parse_datetime(receipt.get("provider_as_of_boundary"))
        if last_run < provider_as_of or last_run > observed:
            errors.append("scheduler_task_time_mismatch")
    except Exception:
        errors.append("scheduler_task_time_malformed")


def _validate_market(
    receipt: Mapping[str, object],
    root: Path,
    errors: list[str],
) -> None:
    if receipt.get("dispatch_type") != "real":
        errors.append("market_dispatch_not_real")
    if receipt.get("dispatch_status") != "success":
        errors.append("market_dispatch_failed")
    if receipt.get("market_data_fetch_occurred") is not True:
        errors.append("market_data_fetch_missing")
    if receipt.get("network_access_attempted") is not True:
        errors.append("market_network_binding_missing")
    _require_no_mutations(receipt, errors, "market_data")
    manifest = receipt.get("artifact_manifest")
    if not isinstance(manifest, Sequence) or isinstance(manifest, (str, bytes)):
        errors.append("market_artifact_manifest_malformed")
        return
    seen_types: set[str] = set()
    root_resolved = root.resolve()
    for item in manifest:
        if not isinstance(item, Mapping) or set(item) != {
            "path",
            "sha256",
            "type",
            "window_identity",
        }:
            errors.append("market_artifact_manifest_malformed")
            continue
        if item.get("window_identity") != receipt.get("accepted_window"):
            errors.append("market_artifact_window_mismatch")
        relative_value = item.get("path")
        if type(relative_value) is not str or not _is_sha256(item.get("sha256")):
            errors.append("market_artifact_manifest_malformed")
            continue
        relative = Path(relative_value)
        path = (root / relative).resolve()
        try:
            path.relative_to(root_resolved)
        except ValueError:
            errors.append("market_artifact_path_escape")
            continue
        if not path.is_file() or _file_sha256(path) != item.get("sha256"):
            errors.append("market_artifact_hash_mismatch")
            continue
        artifact = _load_object(path, errors, "market_artifact_unreadable")
        artifact_type = str(item.get("type"))
        seen_types.add(artifact_type)
        if artifact is not None:
            time_field = "as_of" if artifact_type == "operating_packet" else "updated_at"
            if artifact.get(time_field) != receipt.get("provider_as_of_boundary"):
                errors.append("market_artifact_time_binding_mismatch")
    if seen_types != {"operating_packet", "frozen_state"}:
        errors.append("market_artifact_manifest_ambiguous")


def _validate_broker(receipt: Mapping[str, object], errors: list[str]) -> None:
    if receipt.get("observation_classification") != "read_only_paper_observation_complete":
        errors.append("broker_observation_failed")
    if receipt.get("paper_endpoint") != EXPECTED_PAPER_ENDPOINT:
        errors.append("broker_paper_endpoint_mismatch")
    if receipt.get("expected_account_match") is not True:
        errors.append("broker_account_mismatch")
    if receipt.get("account_active") is not True:
        errors.append("broker_account_inactive")
    if receipt.get("account_flat_reconciled") is not True:
        errors.append("broker_account_non_flat")
    if receipt.get("position_count") != 0 or receipt.get("open_order_count") != 0:
        errors.append("broker_account_non_flat")
    if receipt.get("target_asset_valid") is not True:
        errors.append("broker_target_asset_invalid")
    if receipt.get("broker_read_occurred") is not True:
        errors.append("broker_read_missing")
    if receipt.get("read_counts") != {
        "account": 1,
        "positions": 1,
        "open_orders": 1,
        "target_asset": 1,
    }:
        errors.append("broker_read_count_mismatch")
    _require_no_mutations(receipt, errors, "broker")


def _validate_readiness(receipt: Mapping[str, object], errors: list[str]) -> None:
    if receipt.get("readiness_classification") != "read_only_cycle_ready":
        errors.append("readiness_failed")
    if receipt.get("blockers") != []:
        errors.append("readiness_blocked")
    if receipt.get("account_flat_reconciled") is not True:
        errors.append("readiness_non_flat")
    _require_no_mutations(receipt, errors, "readiness")


def _validate_decision(receipt: Mapping[str, object], errors: list[str]) -> None:
    if receipt.get("decision") != "observe_only_no_action":
        errors.append("decision_mismatch")
    if receipt.get("decision_classification") != "completed_read_only_no_submit":
        errors.append("decision_classification_mismatch")
    if receipt.get("account_flat_reconciled") is not True:
        errors.append("decision_non_flat")
    _require_no_mutations(receipt, errors, "decision")


def _validate_window_fields(
    payload: Mapping[str, object],
    errors: list[str],
    prefix: str,
) -> None:
    try:
        start = _parse_datetime(payload.get("window_start_bar_open"))
        end = _parse_datetime(payload.get("window_end_bar_open"))
        provider_as_of = _parse_datetime(payload.get("provider_as_of_boundary"))
        window = AcceptedWindow(start, end, provider_as_of)
        if payload.get("accepted_window") != window.identity:
            errors.append(f"{prefix}_accepted_window_mismatch")
    except Exception:
        errors.append(f"{prefix}_window_malformed")


def _validate_current_task(
    snapshot: TaskSchedulerSnapshot,
    *,
    scheduler_job_identity: str,
    expected_task_execute: str,
    expected_task_arguments: str,
    blockers: list[str],
) -> None:
    if not isinstance(snapshot, TaskSchedulerSnapshot):
        blockers.append("scheduled_task_snapshot_malformed")
        return
    if snapshot.task_identity != scheduler_job_identity:
        blockers.append("scheduled_task_identity_mismatch")
    if not snapshot.enabled or snapshot.state not in {"Ready", "Running"}:
        blockers.append("scheduled_task_disabled_or_failed")
    if snapshot.action_execute.lower() != expected_task_execute.lower():
        blockers.append("scheduled_task_action_mismatch")
    if snapshot.action_arguments != expected_task_arguments:
        blockers.append("scheduled_task_action_mismatch")
    if snapshot.last_task_result != 0:
        blockers.append("scheduled_task_result_failed")
    if snapshot.last_run_time > snapshot.observed_at:
        blockers.append("scheduled_task_time_mismatch")


def _validate_duplicate_receipts(root: Path) -> tuple[int, int]:
    count = 0
    invalid = 0
    folder = root / "duplicates"
    if not folder.is_dir():
        return count, invalid
    seen: set[str] = set()
    for path in sorted(folder.glob("duplicate_*.json")):
        errors: list[str] = []
        receipt = _load_object(path, errors, "duplicate_unreadable")
        if receipt is None:
            invalid += 1
            continue
        expected = {
            "schema_version",
            "classification",
            "invocation_id",
            "original_owner_invocation_id",
            "scheduler_job_identity",
            "accepted_window",
            "observed_at_utc",
            "subprocess_created",
            "client_constructed",
            "network_access_attempted",
            "broker_read_occurred",
            "canonical_receipt_sha256",
            *_MUTATION_FIELDS,
        }
        invocation_id = receipt.get("invocation_id")
        valid = (
            set(receipt) == expected
            and receipt.get("schema_version") == V535_DUPLICATE_SCHEMA
            and receipt.get("classification") == "duplicate_window_no_op"
            and type(invocation_id) is str
            and invocation_id not in seen
            and receipt.get("canonical_receipt_sha256") == _canonical_hash(receipt)
            and receipt.get("subprocess_created") is False
            and receipt.get("client_constructed") is False
            and receipt.get("network_access_attempted") is False
            and receipt.get("broker_read_occurred") is False
            and all(receipt.get(field) is False for field in _MUTATION_FIELDS)
        )
        if not valid:
            invalid += 1
            continue
        seen.add(str(invocation_id))
        count += 1
    return count, invalid


def _require_no_mutations(
    payload: Mapping[str, object],
    errors: list[str],
    prefix: str,
) -> None:
    for field in _MUTATION_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_{field}_not_false")


def _load_object(
    path: Path,
    errors: list[str],
    classification: str,
) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        errors.append(classification)
        return None
    if not isinstance(payload, dict):
        errors.append(classification)
        return None
    return payload


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    return value.astimezone(UTC)


def _is_sha256(value: object) -> bool:
    return _is_hex(value, 64)


def _is_hex(value: object, length: int) -> bool:
    if type(value) is not str or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
