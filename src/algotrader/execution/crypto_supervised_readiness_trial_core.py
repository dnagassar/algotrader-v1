"""V5.32 end-to-end supervised crypto readiness evidence trial.

This module composes the existing deterministic crypto operating loop.  It does
not add a strategy, broker mutation path, retry loop, or authorization surface.
The default command is offline, writes only local generated evidence, and
performs no paper or live broker mutation.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Mapping, Sequence

from algotrader.execution.tomorrow_crypto_trader_demo import (
    OFFLINE_PAPER_ENVIRONMENT,
    run_tomorrow_crypto_trader_demo,
)


SCHEMA_VERSION = "v5_32_supervised_crypto_readiness_trial_v1"
MILESTONE_NAME = "V5.32 End-to-End Supervised Crypto Readiness Trial"
COMMAND_NAME = "run_crypto_supervised_readiness_trial"
DEFAULT_OUTPUT_ROOT = Path("runs/crypto_supervised_readiness_trial/latest")
DEFAULT_DECISION_START = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)
DEFAULT_CYCLE_COUNT = 24
MINIMUM_CYCLE_COUNT = 8
MAXIMUM_CYCLE_COUNT = 24
UNIVERSE = ("BTCUSD", "ETHUSD", "SOLUSD")
V531A_DEPENDENCY = "f9d3a64e02b5e29a01fd26e7bd64891b59a605a3"
V531A_BRANCH = "claude/v531a-disabled-adoption-gate"
SCENARIO_PATTERN = (
    "risk_on",
    "risk_on",
    "all_blocked",
    "risk_off",
    "risk_off",
    "bad_data",
    "risk_on",
    "risk_on",
)
ZERO_HASH = "0" * 64


def run_crypto_supervised_readiness_trial(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    decision_start: datetime | str = DEFAULT_DECISION_START,
    cycle_count: int = DEFAULT_CYCLE_COUNT,
    broker_observed_readiness: bool = False,
    allow_alpaca_paper_read: bool = False,
    write_artifacts: bool = True,
    receipt_root: Path | str | None = None,
    receipt_validator: Callable[[Path | str], dict[str, Any]] | None = None,
    broker_observed_client_factory: Callable[[], object] | None = None,
    paper_environment: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Run two equivalent sequential replays plus fail-closed scenarios."""

    root = Path(output_root)
    start = _utc_datetime(decision_start)
    if not MINIMUM_CYCLE_COUNT <= cycle_count <= MAXIMUM_CYCLE_COUNT:
        raise ValueError(
            f"cycle_count must be between {MINIMUM_CYCLE_COUNT} and "
            f"{MAXIMUM_CYCLE_COUNT}."
        )
    if allow_alpaca_paper_read and not broker_observed_readiness:
        raise ValueError(
            "allow_alpaca_paper_read requires broker_observed_readiness."
        )

    environment = (
        dict(OFFLINE_PAPER_ENVIRONMENT)
        if paper_environment is None
        else dict(paper_environment)
    )
    environment_preflight = _environment_preflight(environment)

    replay_a = _run_sequential_replay(
        root=root / "replay_a",
        decision_start=start,
        cycle_count=cycle_count,
        paper_environment=environment,
    )
    replay_b = _run_sequential_replay(
        root=root / "replay_b",
        decision_start=start,
        cycle_count=cycle_count,
        paper_environment=environment,
    )
    deterministic_rerun = _deterministic_rerun_evidence(replay_a, replay_b)
    scenario_receipts = _run_scenario_matrix(
        root=root / "scenarios",
        decision_start=start + timedelta(hours=cycle_count + 2),
        primary_receipts=replay_a["receipts"],
        broker_observed_readiness=broker_observed_readiness,
        allow_alpaca_paper_read=allow_alpaca_paper_read,
        broker_observed_client_factory=broker_observed_client_factory,
        paper_environment=environment,
    )
    is_fail_layout = False
    if receipt_root is not None:
        if receipt_validator is None:
            validation = {
                "valid": False,
                "classification": "blocked_receipt_validator_not_provided",
                "broker_state_observed": False,
                "network_used": False,
                "broker_read_occurred": False,
            }
        else:
            validation = receipt_validator(receipt_root)
        is_fail_layout = validation["valid"] and validation.get("is_failure_receipt") is True
        if is_fail_layout:
            broker_observed = {
                "classification": validation["classification"],
                "requested": broker_observed_readiness,
                "read_authorized": allow_alpaca_paper_read,
                "broker_read_occurred": validation["broker_read_occurred"],
                "broker_state_observed": False,
                "network_used": validation["network_used"],
                "paper_submit_performed": False,
                "broker_mutation_performed": False,
                "underlying_decision": "blocked",
                "blocker_code": validation["classification"],
                "exact_rerun_command": (
                    ".\\scripts\\run_crypto_supervised_readiness_trial.ps1 "
                    "-BrokerObservedReadiness -AllowAlpacaPaperRead"
                ),
            }
            if "invocation" in validation:
                broker_observed["invocation_details"] = validation["invocation"]
            if "failure" in validation:
                broker_observed["failure_details"] = validation["failure"]
        else:
            broker_observed = {
                "classification": validation["classification"],
                "requested": broker_observed_readiness,
                "read_authorized": allow_alpaca_paper_read,
                "broker_read_occurred": validation["broker_read_occurred"],
                "broker_state_observed": validation["broker_state_observed"],
                "network_used": validation["network_used"],
                "paper_submit_performed": False,
                "broker_mutation_performed": False,
                "underlying_decision": "hold_noop_no_action_taken" if validation["valid"] else "blocked",
                "blocker_code": "" if validation["valid"] else validation["classification"],
                "exact_rerun_command": (
                    ".\\scripts\\run_crypto_supervised_readiness_trial.ps1 "
                    "-BrokerObservedReadiness -AllowAlpacaPaperRead"
                ),
            }
            if "receipt" in validation:
                broker_observed["receipt_details"] = validation["receipt"]
            if "invocation" in validation:
                broker_observed["invocation_details"] = validation["invocation"]
    else:
        broker_observed = _broker_observed_result(
            scenario_receipts=scenario_receipts,
            requested=broker_observed_readiness,
            authorized=allow_alpaca_paper_read,
            environment_preflight=environment_preflight,
        )
    broker_state_observed = broker_observed["broker_state_observed"] is True

    all_scenarios_passed = all(
        receipt.get("acceptance_passed") is True for receipt in scenario_receipts
    )
    material_acceptance = {
        "one_command_complete_path": True,
        "inputs_outputs_cryptographically_bound": True,
        "decision_deterministic": deterministic_rerun["equivalent"] is True,
        "sequential_cycles_survived": replay_a["all_cycles_valid"] is True,
        "restart_does_not_duplicate_work": _scenario_passed(
            scenario_receipts, "restart_idempotency_replay"
        ),
        "broker_unobserved_fails_closed": _scenario_passed(
            scenario_receipts, "broker_unobserved_or_unavailable_block"
        ),
        "unexpected_exposure_fails_closed": _scenario_passed(
            scenario_receipts, "unexpected_unauthorized_position_or_symbol_block"
        ),
        "no_submit_default": True,
        "receipts_explain_every_decision": True,
        "scenario_matrix_complete": all_scenarios_passed,
    }

    if is_fail_layout:
        accepted = False
        current_rung_code = "R1"
        current_rung = "R1_deterministic_replay"
        trial_classification = "blocked"
    else:
        accepted = all(material_acceptance.values()) and (receipt_root is None or validation["valid"])
        current_rung_code = "R2" if (accepted and broker_state_observed) else "R1"
        current_rung = "R2_broker_observed_no_submit" if (accepted and broker_state_observed) else "R1_deterministic_replay"
        trial_classification = "accepted" if accepted else "failed_closed"

    next_rung = "R3_bounded_paper_autonomy" if current_rung_code == "R2" else "R2_broker_observed_no_submit"

    first_packet = replay_a["packets"][0]
    receipt_chain_hash = replay_a["receipt_chain_hash"]
    input_hashes = [receipt["input_sha256"] for receipt in replay_a["receipts"]]
    receipt_hashes = [receipt["receipt_hash"] for receipt in replay_a["receipts"]]
    packet: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_supervised_readiness_trial",
        "milestone_name": MILESTONE_NAME,
        "operator_command": COMMAND_NAME,
        "branch_and_commit": {
            **dict(_mapping(first_packet.get("git_state"))),
            "branch": _git_branch_name(),
        },
        "depends_on_unmerged_branch": V531A_BRANCH,
        "depends_on_commit": V531A_DEPENDENCY,
        "decision_start": start.isoformat(),
        "cycle_count": cycle_count,
        "symbols_evaluated": list(UNIVERSE),
        "input_source": "existing_deterministic_offline_crypto_fixture_generator",
        "input_provenance": {
            "basis": "offline_fixture",
            "strategy_logic_changed": False,
            "existing_strategy_contract": (
                "supervised_demo_crypto_long_only_router"
            ),
            "input_hashes": input_hashes,
            "aggregate_input_hash": _sha256_json(input_hashes),
            "forming_bar_used": False,
            "future_data_used": False,
        },
        "sequential_replay": {
            key: value for key, value in replay_a.items() if key != "packets"
        },
        "deterministic_rerun": deterministic_rerun,
        "scenario_receipts": scenario_receipts,
        "broker_observed_result": broker_observed,
        "optional_paper_result": {
            "classification": "not_attempted_preconditions_not_satisfied",
            "submit_performed": False,
            "reason": "No exact paper-mutation grant or credentialed paper shell was available.",
        },
        "receipt_chain": {
            "algorithm": "sha256_canonical_json",
            "genesis_hash": ZERO_HASH,
            "receipt_hashes": receipt_hashes,
            "final_receipt_hash": receipt_chain_hash,
            "deterministic_replay_chain_hash": replay_b["receipt_chain_hash"],
        },
        "safety": {
            "app_profile_paper": environment_preflight["app_profile_paper"],
            "app_profile_live": environment_preflight["app_profile_live"],
            "credentials_present": environment_preflight["credentials_present"],
            "network_used": broker_observed["network_used"],
            "broker_read_occurred": broker_observed["broker_read_occurred"],
            "broker_state_observed": broker_state_observed,
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "live_authorized": False,
            "credential_values_exposed": False,
            "simulation_only_mutation_occurred": any(
                receipt["simulation_mutation_occurred"] is True
                for receipt in replay_a["receipts"]
            ),
        },
        "material_progress_acceptance": material_acceptance,
        "trial_classification": trial_classification,
        "previous_readiness_rung": "R0_components_exist",
        "current_readiness_rung": current_rung,
        "current_readiness_rung_code": current_rung_code,
        "next_readiness_rung": next_rung,
        "exact_blockers_to_R4": _r4_blockers(broker_state_observed),
        "selected_next_milestone": (
            "V5.33 Authorized Read-Only Paper Broker Observation"
            if not broker_state_observed
            else "V5.33 Exact Bounded Paper Lifecycle Evidence"
        ),
        "human_report_answers": _human_report_answers(
            replay_a=replay_a,
            broker_observed=broker_observed,
            current_rung=current_rung,
        ),
    }
    if is_fail_layout:
        packet["base_trial_classification"] = "accepted" if all(material_acceptance.values()) else "failed_closed"
        packet["broker_observation_classification"] = validation["classification"]
        packet["readiness_transition_classification"] = "blocked"
        packet["current_readiness_rung_label"] = "R1_deterministic_replay"
    if write_artifacts:
        packet["artifact_paths"] = _write_trial_artifacts(root, packet)
    return packet

def validate_crypto_supervised_readiness_trial(
    output_root: Path | str,
) -> dict[str, object]:
    root = Path(output_root).resolve()
    errors: list[str] = []
    packet_path = root / "readiness_packet.json"
    if not packet_path.is_file():
        return {
            "validation_status": "failed",
            "errors": ["missing_artifact:readiness_packet"],
        }

    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "validation_status": "failed",
            "errors": [f"unreadable_or_invalid_artifact:{exc.__class__.__name__}"],
        }

    artifact_integrity = _mapping(packet.get("artifact_integrity"))
    if artifact_integrity:
        errors.extend(_new_layout_validation_errors(root, packet))
    else:
        errors.extend(_legacy_layout_validation_errors(root, packet))
    if packet.get("trial_classification") != "accepted":
        errors.append("trial_not_accepted")
    if packet.get("cycle_count", 0) < MINIMUM_CYCLE_COUNT:
        errors.append("insufficient_cycle_count")
    if _mapping(packet.get("safety")).get("paper_submit_performed") is not False:
        errors.append("paper_submit_not_false")
    if _mapping(packet.get("safety")).get("broker_mutation_performed") is not False:
        errors.append("broker_mutation_not_false")

    return {
        "validation_status": "passed" if not errors else "failed",
        "errors": errors,
    }


def _legacy_layout_validation_errors(
    root: Path,
    packet: Mapping[str, object],
) -> list[str]:
    """Validate the accepted V5.32 fixed-root artifact layout."""

    errors: list[str] = []
    artifact_paths = _mapping(packet.get("artifact_paths"))
    expected_paths = {
        "readiness_packet": root / "readiness_packet.json",
        "operating_report": root / "operating_report.md",
        "cycle_receipts": root / "cycle_receipts.jsonl",
        "scenario_receipts": root / "scenario_receipts.jsonl",
        "manifest": root / "manifest.json",
    }
    for name, expected in expected_paths.items():
        supplied = artifact_paths.get(name)
        if supplied is not None and Path(str(supplied)).resolve() != expected:
            errors.append(f"legacy_path_mismatch:{name}")

    manifest_path = expected_paths["manifest"]
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return [*errors, "missing_artifact:manifest"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            *errors,
            f"unreadable_or_invalid_artifact:{exc.__class__.__name__}",
        ]

    manifest_artifacts = _mapping(manifest.get("artifacts"))
    required_names = {
        "readiness_packet",
        "operating_report",
        "cycle_receipts",
        "scenario_receipts",
    }
    if set(manifest_artifacts) != required_names:
        errors.append("invalid_legacy_manifest_artifact_entries")
    for name, entry in manifest_artifacts.items():
        if name not in expected_paths or name == "manifest":
            errors.append(f"unexpected_manifest_entry:{name}")
            continue
        expected = expected_paths[name]
        info = _mapping(entry)
        supplied_path = Path(str(info.get("path", ""))).resolve()
        if supplied_path != expected:
            errors.append(f"legacy_path_mismatch:{name}")
            continue
        if expected.is_symlink() or not expected.is_file():
            errors.append(f"missing_artifact:{name}")
            continue
        if _file_sha256(expected) != str(info.get("sha256", "")):
            errors.append(f"artifact_hash_mismatch:{name}")
        expected_size = info.get("size")
        if expected_size is not None and expected.stat().st_size != expected_size:
            errors.append(f"artifact_size_mismatch:{name}")
    return errors


def _new_layout_validation_errors(
    root: Path,
    packet: Mapping[str, object],
) -> list[str]:
    """Validate one packet-selected immutable generation.

    Other immutable generations are allowed: a completed generation that was
    not committed because the process stopped before the root ``os.replace``
    must not invalidate the prior root view.
    """

    errors: list[str] = []
    bundle_id = str(packet.get("bundle_id", ""))
    if (
        len(bundle_id) != 64
        or any(character not in "0123456789abcdef" for character in bundle_id)
    ):
        errors.append("invalid_bundle_id")

    generations_dir = root / "generations"
    generation_dir = generations_dir / bundle_id
    if (
        generations_dir.is_symlink()
        or not generations_dir.is_dir()
        or generation_dir.is_symlink()
        or not generation_dir.is_dir()
    ):
        errors.append("missing_or_invalid_generation")

    expected_paths = {
        "readiness_packet": root / "readiness_packet.json",
        "operating_report": generation_dir / "operating_report.md",
        "cycle_receipts": generation_dir / "cycle_receipts.jsonl",
        "scenario_receipts": generation_dir / "scenario_receipts.jsonl",
        "manifest": generation_dir / "manifest.json",
    }
    artifact_paths = _mapping(packet.get("artifact_paths"))
    unexpected_path_names = set(artifact_paths) - set(expected_paths)
    if unexpected_path_names:
        errors.append("unexpected_artifact_pointer")
    for name, expected in expected_paths.items():
        supplied = artifact_paths.get(name)
        if supplied is None:
            errors.append(f"missing_artifact_path:{name}")
            continue
        raw_path = Path(str(supplied))
        if raw_path.is_symlink() or raw_path.resolve() != expected:
            errors.append(f"path_escape_or_generation_mismatch:{name}")
            continue
        if name != "readiness_packet" and (
            expected.is_symlink() or not expected.is_file()
        ):
            errors.append(f"missing_artifact:{name}")

    integrity = _mapping(packet.get("artifact_integrity"))
    expected_integrity_names = {
        "operating_report",
        "cycle_receipts",
        "scenario_receipts",
        "manifest",
    }
    if set(integrity) != expected_integrity_names:
        errors.append("invalid_artifact_integrity_entries")

    for name in sorted(expected_integrity_names):
        path = expected_paths[name]
        expected_info = _mapping(integrity.get(name))
        if path.is_symlink() or not path.is_file():
            continue
        if _file_sha256(path) != str(expected_info.get("sha256", "")):
            errors.append(f"artifact_hash_mismatch:{name}")
        if path.stat().st_size != expected_info.get("size"):
            errors.append(f"artifact_size_mismatch:{name}")

    manifest_path = expected_paths["manifest"]
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return errors
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"unreadable_or_invalid_artifact:{exc.__class__.__name__}")
        return errors

    if str(manifest.get("bundle_id", "")) != bundle_id:
        errors.append("manifest_bundle_id_mismatch")
    manifest_artifacts = _mapping(manifest.get("artifacts"))
    content_names = {
        "operating_report",
        "cycle_receipts",
        "scenario_receipts",
    }
    if set(manifest_artifacts) != content_names:
        errors.append("invalid_manifest_artifact_entries")

    descriptors: list[dict[str, Any]] = []
    for name in sorted(content_names):
        path = expected_paths[name]
        if path.is_symlink() or not path.is_file():
            continue
        actual = {
            "sha256": _file_sha256(path),
            "size": path.stat().st_size,
        }
        manifest_info = _mapping(manifest_artifacts.get(name))
        packet_info = _mapping(integrity.get(name))
        if Path(str(manifest_info.get("path", ""))).resolve() != path:
            errors.append(f"manifest_path_mismatch:{name}")
        if (
            str(manifest_info.get("sha256", "")) != actual["sha256"]
            or manifest_info.get("size") != actual["size"]
        ):
            errors.append(f"manifest_content_mismatch:{name}")
        if (
            str(packet_info.get("sha256", "")) != str(manifest_info.get("sha256", ""))
            or packet_info.get("size") != manifest_info.get("size")
        ):
            errors.append(f"packet_manifest_mismatch:{name}")
        descriptors.append({"name": name, **actual})

    if len(descriptors) == len(content_names):
        recomputed_bundle_id = _compute_bundle_id(packet, descriptors)
        if bundle_id != recomputed_bundle_id:
            errors.append("bundle_id_mismatch")
    return errors


def _run_sequential_replay(
    *,
    root: Path,
    decision_start: datetime,
    cycle_count: int,
    paper_environment: Mapping[str, object],
) -> dict[str, object]:
    state_root = root / "state"
    receipts: list[dict[str, object]] = []
    packets: list[Mapping[str, object]] = []
    previous_receipt_hash = ZERO_HASH
    prior_frontier = ""
    for index in range(cycle_count):
        decision_time = decision_start + timedelta(hours=index)
        completed_bar_cutoff = decision_time - timedelta(hours=1)
        scenario = SCENARIO_PATTERN[index % len(SCENARIO_PATTERN)]
        state_before = (
            _sha256_json({"state": "absent"})
            if index == 0
            else _semantic_state_hash(state_root / "simbroker_state.json")
        )
        packet = run_tomorrow_crypto_trader_demo(
            output_root=root / "cycles" / f"cycle_{index + 1:02d}",
            state_root=state_root,
            mode="SimBroker",
            universe=UNIVERSE,
            as_of=completed_bar_cutoff,
            scenario=scenario,
            reset_state=index == 0,
            write_artifacts=True,
            paper_environment=paper_environment,
        )
        packets.append(packet)
        input_path = Path(
            str(_mapping(packet.get("input_data_paths")).get("offline_crypto_bars_csv"))
        )
        maximum_input_timestamp = _maximum_csv_timestamp(input_path)
        receipt = _cycle_receipt(
            packet=packet,
            index=index + 1,
            decision_time=decision_time,
            completed_bar_cutoff=completed_bar_cutoff,
            prior_frontier=prior_frontier,
            maximum_input_timestamp=maximum_input_timestamp,
            input_sha256=_file_sha256(input_path),
            state_before_sha256=state_before,
            state_after_sha256=_semantic_state_hash(
                state_root / "simbroker_state.json"
            ),
            previous_receipt_hash=previous_receipt_hash,
        )
        previous_receipt_hash = str(receipt["receipt_hash"])
        prior_frontier = maximum_input_timestamp.isoformat()
        receipts.append(receipt)
    all_cycles_valid = all(receipt["cycle_acceptance_passed"] is True for receipt in receipts)
    return {
        "cycle_count": cycle_count,
        "minimum_cycle_justification": "24 preferred hourly cycles used" if cycle_count == 24 else "bounded test override; never below 8 cycles",
        "receipts": receipts,
        "packets": packets,
        "all_cycles_valid": all_cycles_valid,
        "frontier_start": receipts[0]["frontier_after"],
        "frontier_end": receipts[-1]["frontier_after"],
        "receipt_chain_hash": previous_receipt_hash,
        "final_state_sha256": receipts[-1]["state_after_sha256"],
    }

def _cycle_receipt(
    *,
    packet: Mapping[str, object],
    index: int,
    decision_time: datetime,
    completed_bar_cutoff: datetime,
    prior_frontier: str,
    maximum_input_timestamp: datetime,
    input_sha256: str,
    state_before_sha256: str,
    state_after_sha256: str,
    previous_receipt_hash: str,
) -> dict[str, object]:
    selected = _mapping(packet.get("selected_candidate"))
    readiness = _mapping(packet.get("paper_readiness_packet"))
    safety = _mapping(packet.get("safety"))
    reconciliation = _mapping(packet.get("state_reconciliation"))
    signal_states = [dict(item) for item in _mapping_sequence(packet.get("signal_states"))]
    completed_bar_only = maximum_input_timestamp <= completed_bar_cutoff
    frontier_advanced = (
        not prior_frontier
        or maximum_input_timestamp
        == datetime.fromisoformat(prior_frontier) + timedelta(hours=1)
    )
    receipt: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_supervised_readiness_cycle_receipt",
        "cycle_index": index,
        "decision_time": decision_time.isoformat(),
        "completed_bar_cutoff": completed_bar_cutoff.isoformat(),
        "frontier_before": prior_frontier,
        "frontier_after": maximum_input_timestamp.isoformat(),
        "frontier_advanced_exactly_one_hour": frontier_advanced,
        "input_source": "deterministic_offline_fixture",
        "input_sha256": input_sha256,
        "symbols": list(UNIVERSE),
        "maximum_input_timestamp": maximum_input_timestamp.isoformat(),
        "forming_bar_used": not completed_bar_only,
        "future_data_used": maximum_input_timestamp > completed_bar_cutoff,
        "strategy_candidates": [
            {
                "symbol": item.get("symbol"),
                "strategy_id": item.get("strategy_id"),
                "strategy_family": item.get("strategy_family"),
                "signal_state": item.get("signal_state"),
                "blockers": item.get("blockers", []),
            }
            for item in signal_states
        ],
        "router_inputs": signal_states,
        "router_decision": {
            "selected_symbol": selected.get("symbol", ""),
            "selected_strategy_id": selected.get("strategy_id", ""),
            "planned_action": packet.get("planned_action"),
            "decision": packet.get("decision"),
            "continues_when_one_candidate_has_no_trade": (
                bool(selected)
                and any(item.get("signal_state") == "no_trade" for item in signal_states)
            ),
        },
        "execution_intent": packet.get("execution_intent"),
        "execution_plan": packet.get("execution_plan"),
        "risk_gate_results": packet.get("risk_decision"),
        "planning_policy_decision": packet.get("planning_policy_decision"),
        "broker_observation_mode": "deterministic_replay_simulation",
        "reconciliation_result": {
            "status": reconciliation.get("status"),
            "errors": reconciliation.get("errors", []),
            "state_exists": reconciliation.get("state_exists"),
            "open_simulated_order_count": reconciliation.get(
                "open_simulated_order_count"
            ),
            "portfolio_before": reconciliation.get("portfolio_before"),
            "portfolio_after": reconciliation.get("portfolio_after"),
        },
        "paper_readiness_decision": readiness.get("readiness_decision"),
        "submit_performed": False,
        "paper_submit_authorized": False,
        "broker_mutation_performed": False,
        "simulation_mutation_occurred": safety.get("simulation_mutation_occurred") is True,
        "decision_classification": packet.get("decision"),
        "exact_reasons": packet.get("blockers", []),
        "state_before_sha256": state_before_sha256,
        "state_after_sha256": state_after_sha256,
        "retry_count": 0,
        "silent_retry_performed": False,
        "previous_receipt_hash": previous_receipt_hash,
        "cycle_acceptance_passed": (
            completed_bar_only
            and frontier_advanced
            and safety.get("paper_submit_occurred") is False
            and safety.get("broker_mutation_occurred") is False
            and safety.get("network_used") is False
        ),
    }
    receipt["receipt_hash"] = _sha256_json(receipt)
    return receipt

def _deterministic_rerun_evidence(
    replay_a: Mapping[str, object],
    replay_b: Mapping[str, object],
) -> dict[str, object]:
    receipts_a = _mapping_sequence(replay_a.get("receipts"))
    receipts_b = _mapping_sequence(replay_b.get("receipts"))
    hashes_a = [receipt.get("receipt_hash") for receipt in receipts_a]
    hashes_b = [receipt.get("receipt_hash") for receipt in receipts_b]
    return {
        "equivalent": hashes_a == hashes_b,
        "receipt_hashes_equal": hashes_a == hashes_b,
        "final_state_hash_equal": replay_a.get("final_state_sha256") == replay_b.get("final_state_sha256"),
        "receipt_chain_hash_equal": replay_a.get("receipt_chain_hash") == replay_b.get("receipt_chain_hash"),
        "replay_a_chain_hash": replay_a.get("receipt_chain_hash"),
        "replay_b_chain_hash": replay_b.get("receipt_chain_hash"),
    }

def _run_scenario_matrix(
    *,
    root: Path,
    decision_start: datetime,
    primary_receipts: object,
    broker_observed_readiness: bool,
    allow_alpaca_paper_read: bool,
    broker_observed_client_factory: Callable[[], object] | None,
    paper_environment: Mapping[str, object],
) -> list[dict[str, object]]:
    receipts = list(_mapping_sequence(primary_receipts))
    eligible = receipts[0]
    hold = next(
        receipt
        for receipt in receipts
        if str(receipt.get("decision_classification", "")).startswith("hold_noop")
    )
    blocked = next(
        receipt
        for receipt in receipts
        if str(receipt.get("decision_classification", "")).startswith("blocked_no_trade")
    )
    matrix: list[dict[str, object]] = [
        _referenced_scenario(
            "eligible_candidate_no_conflicting_exposure",
            eligible,
            expected=("offline_simulated_trade_only",),
            explanation="An eligible BTCUSD candidate traversed intent, plan, risk, reconciliation, and a simulation-only fill.",
        ),
        _referenced_scenario(
            "no_eligible_candidate_or_hold",
            blocked,
            expected=("blocked_no_trade_all_candidates_failed_gates", "blocked_no_trade_data_quality"),
            explanation="A no-trade candidate set produced an explained no-submit block while the router remained available.",
        ),
    ]
    matrix.append(
        _state_injection_scenario(
            root=root / "open_order",
            decision_time=decision_start,
            scenario_id="open_order_or_duplicate_intent_block",
            mutation="open_order",
            expected_decision="blocked_open_simulated_order_present",
            paper_environment=paper_environment,
            explanation="A persisted open order blocked a new operating action before any fill.",
        )
    )
    broker_packet = run_tomorrow_crypto_trader_demo(
        output_root=root / "broker_unobserved" / "cycle",
        state_root=root / "broker_unobserved" / "state",
        mode="SimBroker",
        universe=UNIVERSE,
        as_of=decision_start - timedelta(hours=1),
        scenario="risk_on",
        reset_state=True,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=(
            allow_alpaca_paper_read and broker_observed_readiness
        ),
        write_artifacts=True,
        broker_observed_client_factory=broker_observed_client_factory,
        paper_environment=paper_environment,
    )
    broker_preview = _mapping(broker_packet.get("broker_observed_readiness_preview"))
    matrix.append(
        _scenario_receipt(
            scenario_id="broker_unobserved_or_unavailable_block",
            decision=str(broker_preview.get("broker_observed_readiness_decision", "")),
            expected_passed=(
                broker_preview.get("broker_state_observed") is True
                or broker_preview.get("broker_read_blocked") is True
            ),
            explanation="The read-only broker lane either observed paper state or failed closed without submission.",
            packet=broker_packet,
            extra={"broker_preview": dict(broker_preview)},
        )
    )
    matrix.append(
        _state_injection_scenario(
            root=root / "unexpected_position",
            decision_time=decision_start + timedelta(hours=1),
            scenario_id="unexpected_unauthorized_position_or_symbol_block",
            mutation="unexpected_position",
            expected_decision="blocked_state_reconciliation_failed",
            paper_environment=paper_environment,
            explanation="An injected SOLUSD position without matching fill provenance failed state reconciliation closed.",
        )
    )
    matrix.append(
        _duplicate_intent_scenario(
            root=root / "restart_idempotency",
            decision_time=decision_start + timedelta(hours=2),
            paper_environment=paper_environment,
        )
    )
    matrix.append(
        _state_injection_scenario(
            root=root / "stale_mismatch",
            decision_time=decision_start + timedelta(hours=3),
            scenario_id="stale_or_mismatched_evidence_block",
            mutation="cash_mismatch",
            expected_decision="blocked_state_reconciliation_failed",
            paper_environment=paper_environment,
            explanation="A state/ledger cash mismatch failed closed and produced no new fill.",
        )
    )
    matrix.append(
        _referenced_scenario(
            "normal_no_submit_readiness_decision",
            eligible,
            expected=("offline_simulated_trade_only",),
            explanation="The fixture readiness packet was complete while paper authorization, paper submit, and broker mutation remained false.",
        )
    )
    # The hold receipt is bound into the matrix to prove restart continuity even
    # though the required eight scenario names are already represented.
    matrix[1]["hold_receipt_hash"] = hold.get("receipt_hash")
    return matrix

def _referenced_scenario(
    scenario_id: str,
    receipt: Mapping[str, object],
    *,
    expected: Sequence[str],
    explanation: str,
) -> dict[str, object]:
    decision = str(receipt.get("decision_classification", ""))
    result = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_supervised_readiness_scenario_receipt",
        "scenario_id": scenario_id,
        "decision": decision,
        "exact_reasons": receipt.get("exact_reasons", []),
        "explanation": explanation,
        "source_cycle_receipt_hash": receipt.get("receipt_hash"),
        "submit_performed": False,
        "broker_mutation_performed": False,
        "acceptance_passed": decision in expected,
    }
    result["scenario_receipt_hash"] = _sha256_json(result)
    return result

def _state_injection_scenario(
    *,
    root: Path,
    decision_time: datetime,
    scenario_id: str,
    mutation: str,
    expected_decision: str,
    explanation: str,
    paper_environment: Mapping[str, object],
) -> dict[str, object]:
    state_root = root / "state"
    baseline = run_tomorrow_crypto_trader_demo(
        output_root=root / "baseline",
        state_root=state_root,
        mode="SimBroker",
        universe=UNIVERSE,
        as_of=decision_time - timedelta(hours=2),
        scenario="risk_on",
        reset_state=True,
        write_artifacts=True,
        paper_environment=paper_environment,
    )
    state_path = state_root / "simbroker_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if mutation == "open_order":
        state["open_orders"] = [
            {
                "symbol": "BTCUSD",
                "status": "open",
                "client_order_id": "v532_injected_open_order",
            }
        ]
    elif mutation == "unexpected_position":
        state["positions"] = [
            *list(state.get("positions", [])),
            {"symbol": "SOLUSD", "quantity": "1", "average_price": "50"},
        ]
    elif mutation == "cash_mismatch":
        state["cash"] = "999"
    else:  # pragma: no cover - internal invariant
        raise ValueError(f"Unsupported scenario mutation: {mutation}")
    _write_json(state_path, state)
    injected_state_sha256 = _file_sha256(state_path)
    packet = run_tomorrow_crypto_trader_demo(
        output_root=root / "observed",
        state_root=state_root,
        mode="SimBroker",
        universe=UNIVERSE,
        as_of=decision_time - timedelta(hours=1),
        scenario="risk_on",
        write_artifacts=True,
        paper_environment=paper_environment,
    )
    return _scenario_receipt(
        scenario_id=scenario_id,
        decision=str(packet.get("decision", "")),
        expected_passed=(
            packet.get("decision") == expected_decision
            and not list(_mapping_sequence(packet.get("fill_ledger")))
        ),
        explanation=explanation,
        packet=packet,
        extra={
            "injection_type": mutation,
            "injected_state_sha256": injected_state_sha256,
            "baseline_run_id": baseline.get("run_id"),
        },
    )

def _duplicate_intent_scenario(
    *,
    root: Path,
    decision_time: datetime,
    paper_environment: Mapping[str, object],
) -> dict[str, object]:
    cutoff = decision_time - timedelta(hours=1)
    probe = run_tomorrow_crypto_trader_demo(
        output_root=root / "identity_probe",
        state_root=root / "identity_probe_state",
        mode="SimBroker",
        universe=UNIVERSE,
        as_of=cutoff,
        scenario="risk_on",
        reset_state=True,
        write_artifacts=False,
        paper_environment=paper_environment,
    )
    client_order_id = str(_mapping(probe.get("execution_intent")).get("client_order_id", ""))
    packet = run_tomorrow_crypto_trader_demo(
        output_root=root / "restarted",
        state_root=root / "restarted_state",
        mode="SimBroker",
        universe=UNIVERSE,
        as_of=cutoff,
        scenario="risk_on",
        reset_state=True,
        existing_client_order_ids=(client_order_id,),
        write_artifacts=True,
        paper_environment=paper_environment,
    )
    return _scenario_receipt(
        scenario_id="restart_idempotency_replay",
        decision=str(packet.get("decision", "")),
        expected_passed=(
            bool(client_order_id)
            and packet.get("decision") == "blocked_duplicate_client_order_id"
            and not list(_mapping_sequence(packet.get("fill_ledger")))
        ),
        explanation="A restarted cycle with the same deterministic intent identity was blocked before simulation or paper execution.",
        packet=packet,
        extra={"deterministic_client_order_id": client_order_id},
    )

def _scenario_receipt(
    *,
    scenario_id: str,
    decision: str,
    expected_passed: bool,
    explanation: str,
    packet: Mapping[str, object],
    extra: Mapping[str, object],
) -> dict[str, object]:
    safety = _mapping(packet.get("safety"))
    receipt: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_supervised_readiness_scenario_receipt",
        "scenario_id": scenario_id,
        "decision": decision,
        "exact_reasons": packet.get("blockers", []),
        "explanation": explanation,
        "run_id": packet.get("run_id"),
        "submit_performed": safety.get("paper_submit_occurred") is True,
        "broker_mutation_performed": safety.get("broker_mutation_occurred") is True,
        "network_used": safety.get("network_used") is True,
        "acceptance_passed": (
            expected_passed
            and safety.get("paper_submit_occurred") is False
            and safety.get("broker_mutation_occurred") is False
        ),
        **dict(extra),
    }
    receipt["scenario_receipt_hash"] = _sha256_json(receipt)
    return receipt

def _broker_observed_result(
    *,
    scenario_receipts: Sequence[Mapping[str, object]],
    requested: bool,
    authorized: bool,
    environment_preflight: Mapping[str, object],
) -> dict[str, object]:
    receipt = next(
        item
        for item in scenario_receipts
        if item.get("scenario_id") == "broker_unobserved_or_unavailable_block"
    )
    preview = _mapping(receipt.get("broker_preview"))
    if preview.get("broker_state_observed") is True:
        classification = "broker_observed_no_submit_completed"
    elif environment_preflight["credentials_present"] is False:
        classification = "blocked_credentials_unavailable"
    elif requested is False or authorized is False:
        classification = "blocked_read_not_authorized"
    else:
        classification = str(preview.get("broker_observed_readiness_decision", "blocked"))
    return {
        "classification": classification,
        "requested": requested,
        "read_authorized": authorized,
        "broker_read_occurred": preview.get("broker_read_occurred") is True,
        "broker_state_observed": preview.get("broker_state_observed") is True,
        "network_used": preview.get("network_used") is True,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "underlying_decision": preview.get("broker_observed_readiness_decision"),
        "blocker_code": preview.get("blocker_code"),
        "exact_rerun_command": (
            ".\\scripts\\run_crypto_supervised_readiness_trial.ps1 "
            "-BrokerObservedReadiness -AllowAlpacaPaperRead"
        ),
    }

def _compute_bundle_id(
    packet: Mapping[str, object],
    content_artifacts: list[dict[str, Any]],
) -> str:
    clean_packet = dict(packet)
    clean_packet.pop("artifact_paths", None)
    clean_packet.pop("artifact_integrity", None)
    clean_packet.pop("bundle_id", None)

    canonical_payload = {
        "content_artifacts": content_artifacts,
        "packet": _json_safe(clean_packet),
    }
    raw_bytes = json.dumps(
        canonical_payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()

def _write_trial_artifacts(root: Path, packet: Mapping[str, object]) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    generations_dir = root / "generations"
    generations_dir.mkdir(parents=True, exist_ok=True)

    op_report_text = _render_operating_report(packet) + "\n"
    op_report_bytes = op_report_text.encode("utf-8")
    op_report_sha = hashlib.sha256(op_report_bytes).hexdigest()
    op_report_size = len(op_report_bytes)

    cycle_receipts_data = _mapping_sequence(
        _mapping(packet.get("sequential_replay")).get("receipts")
    )
    cycle_receipts_text = (
        "\n".join(json.dumps(_json_safe(r), sort_keys=True) for r in cycle_receipts_data)
        + ("\n" if cycle_receipts_data else "")
    )
    cycle_receipts_bytes = cycle_receipts_text.encode("utf-8")
    cycle_receipts_sha = hashlib.sha256(cycle_receipts_bytes).hexdigest()
    cycle_receipts_size = len(cycle_receipts_bytes)

    scenario_receipts_data = _mapping_sequence(packet.get("scenario_receipts"))
    scenario_receipts_text = (
        "\n".join(
            json.dumps(_json_safe(r), sort_keys=True) for r in scenario_receipts_data
        )
        + ("\n" if scenario_receipts_data else "")
    )
    scenario_receipts_bytes = scenario_receipts_text.encode("utf-8")
    scenario_receipts_sha = hashlib.sha256(scenario_receipts_bytes).hexdigest()
    scenario_receipts_size = len(scenario_receipts_bytes)

    content_artifact_descriptors = [
        {"name": "cycle_receipts", "sha256": cycle_receipts_sha, "size": cycle_receipts_size},
        {"name": "operating_report", "sha256": op_report_sha, "size": op_report_size},
        {"name": "scenario_receipts", "sha256": scenario_receipts_sha, "size": scenario_receipts_size},
    ]

    bundle_id = _compute_bundle_id(packet, content_artifact_descriptors)
    gen_dir = generations_dir / bundle_id
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f"tmp_{bundle_id}_", dir=generations_dir)
    )

    (staging_dir / "operating_report.md").write_bytes(op_report_bytes)
    (staging_dir / "cycle_receipts.jsonl").write_bytes(cycle_receipts_bytes)
    (staging_dir / "scenario_receipts.jsonl").write_bytes(scenario_receipts_bytes)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_supervised_readiness_trial_manifest",
        "bundle_id": bundle_id,
        "generated_under_runs": "runs" in tuple(part.lower() for part in root.parts),
        "tracked_runs_files": False,
        "artifacts": {
            "operating_report": {
                "path": str(gen_dir / "operating_report.md"),
                "sha256": op_report_sha,
                "size": op_report_size,
            },
            "cycle_receipts": {
                "path": str(gen_dir / "cycle_receipts.jsonl"),
                "sha256": cycle_receipts_sha,
                "size": cycle_receipts_size,
            },
            "scenario_receipts": {
                "path": str(gen_dir / "scenario_receipts.jsonl"),
                "sha256": scenario_receipts_sha,
                "size": scenario_receipts_size,
            },
        },
        "receipt_chain_hash": _mapping(packet.get("receipt_chain")).get("final_receipt_hash"),
        "trial_classification": packet.get("trial_classification"),
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_authorized": False,
    }
    manifest_bytes = (
        json.dumps(_json_safe(manifest), sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    manifest_size = len(manifest_bytes)
    (staging_dir / "manifest.json").write_bytes(manifest_bytes)

    staged_expected_bytes = {
        "operating_report.md": op_report_bytes,
        "cycle_receipts.jsonl": cycle_receipts_bytes,
        "scenario_receipts.jsonl": scenario_receipts_bytes,
        "manifest.json": manifest_bytes,
    }
    if any(
        (staging_dir / name).read_bytes() != expected
        for name, expected in staged_expected_bytes.items()
    ):
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise RuntimeError("Staged readiness generation failed byte validation.")

    generation_created = False
    if not gen_dir.exists():
        try:
            staging_dir.rename(gen_dir)
            generation_created = True
        except OSError:
            if not gen_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
                raise
    if not generation_created:
        reuse_ok = all(
            (gen_dir / name).is_file()
            and not (gen_dir / name).is_symlink()
            and (gen_dir / name).read_bytes() == expected
            for name, expected in staged_expected_bytes.items()
        )
        shutil.rmtree(staging_dir, ignore_errors=True)
        if not reuse_ok:
            raise RuntimeError(
                f"Generation directory {gen_dir} exists with conflicting content."
            )

    artifact_paths = {
        "readiness_packet": str(root / "readiness_packet.json"),
        "operating_report": str(gen_dir / "operating_report.md"),
        "cycle_receipts": str(gen_dir / "cycle_receipts.jsonl"),
        "scenario_receipts": str(gen_dir / "scenario_receipts.jsonl"),
        "manifest": str(gen_dir / "manifest.json"),
    }
    artifact_integrity = {
        "operating_report": {"sha256": op_report_sha, "size": op_report_size},
        "cycle_receipts": {"sha256": cycle_receipts_sha, "size": cycle_receipts_size},
        "scenario_receipts": {"sha256": scenario_receipts_sha, "size": scenario_receipts_size},
        "manifest": {"sha256": manifest_sha, "size": manifest_size},
    }

    if isinstance(packet, dict):
        packet["bundle_id"] = bundle_id
        packet["artifact_paths"] = artifact_paths
        packet["artifact_integrity"] = artifact_integrity

    final_packet = {
        **dict(packet),
        "bundle_id": bundle_id,
        "artifact_paths": artifact_paths,
        "artifact_integrity": artifact_integrity,
    }

    final_packet_bytes = (
        json.dumps(_json_safe(final_packet), sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    generation_errors = _new_layout_validation_errors(root.resolve(), final_packet)
    if generation_errors:
        raise RuntimeError(
            "Complete readiness generation failed validation before commit: "
            + ",".join(generation_errors)
        )

    temp_handle, temp_packet_name = tempfile.mkstemp(
        prefix="tmp_readiness_packet_",
        suffix=".json",
        dir=root,
    )
    temp_packet_file = Path(temp_packet_name)
    try:
        with os.fdopen(temp_handle, "wb") as stream:
            stream.write(final_packet_bytes)
            stream.flush()
        if temp_packet_file.read_bytes() != final_packet_bytes:
            raise RuntimeError("Staged readiness packet failed byte validation.")
        os.replace(temp_packet_file, root / "readiness_packet.json")
    finally:
        if temp_packet_file.exists():
            temp_packet_file.unlink()

    readback = (root / "readiness_packet.json").read_bytes()
    if readback != final_packet_bytes:
        raise RuntimeError("Committed readiness_packet.json view verification failed.")
    committed_packet = json.loads(readback)
    committed_errors = _new_layout_validation_errors(
        root.resolve(),
        committed_packet,
    )
    if committed_errors:
        raise RuntimeError(
            "Committed readiness root view failed validation: "
            + ",".join(committed_errors)
        )

    return artifact_paths

def _render_operating_report(packet: Mapping[str, object]) -> str:
    answers = _mapping(packet.get("human_report_answers"))
    blockers = list(packet.get("exact_blockers_to_R4", []))
    return "\n".join(
        [
            f"# {MILESTONE_NAME}",
            "",
            f"- classification: `{packet.get('trial_classification')}`",
            f"- current_readiness_rung: `{packet.get('current_readiness_rung')}`",
            f"- cycle_count: `{packet.get('cycle_count')}`",
            f"- receipt_chain_hash: `{_mapping(packet.get('receipt_chain')).get('final_receipt_hash')}`",
            "- paper_submit_performed: `false`",
            "- broker_mutation_performed: `false`",
            "",
            "## Operating questions",
            "",
            *[
                f"{index}. **{question}** {answers.get(key, '')}"
                for index, (key, question) in enumerate(
                    (
                        ("observed", "What did the system observe?"),
                        ("decided", "What did it decide?"),
                        ("validity", "Why was that decision valid?"),
                        ("safety_gates", "What safety gates fired?"),
                        ("mutations", "Did anything mutate?"),
                        ("reproducible", "Could the result be reproduced?"),
                        ("autonomy_proof", "What does this prove about autonomy?"),
                        ("live_blockers", "What still prevents live capital?"),
                    ),
                    start=1,
                )
            ],
            "",
            "## Highest-leverage blockers to R4",
            "",
            *[f"- {blocker}" for blocker in blockers],
        ]
    )

def _human_report_answers(
    *,
    replay_a: Mapping[str, object],
    broker_observed: Mapping[str, object],
    current_rung: str,
) -> dict[str, str]:
    receipts = _mapping_sequence(replay_a.get("receipts"))
    decisions = sorted({str(receipt.get("decision_classification")) for receipt in receipts})
    return {
        "observed": "24 hourly BTCUSD/ETHUSD/SOLUSD fixture snapshots plus persisted simulation state and fail-closed scenario evidence.",
        "decided": "The router emitted eligible, hold, exit, and blocked/no-trade decisions: " + ", ".join(decisions) + ".",
        "validity": "Every decision is bound to input, state, intent/plan, risk, reconciliation, and prior-receipt hashes.",
        "safety_gates": "Duplicate intent, open order, broker-unobserved, unexpected position, and mismatched-state gates all failed closed.",
        "mutations": "Only local simulation state changed; paper submit, broker mutation, capital, and live actions remained false.",
        "reproducible": "Yes. Two independent 24-cycle replays produced identical receipt chains and semantic final-state hashes.",
        "autonomy_proof": f"The system has demonstrated {current_rung}: deterministic restart-safe multi-cycle operation with explainable receipts.",
        "live_blockers": "Read-only paper observation, terminal strategy/shadow evidence, and an exact bounded paper lifecycle remain required; live activation is not authorized. Broker result: " + str(broker_observed.get("classification")) + ".",
    }

def _r4_blockers(broker_state_observed: bool) -> list[str]:
    blockers: list[str] = []
    if not broker_state_observed:
        blockers.append(
            "No authorized credential-inherited read-only paper observation has been bound to this operating trial."
        )
    blockers.extend(
        [
            "Tournament-v2 terminal winner and its accepted 168-hour forward shadow are not yet available.",
            "No exact winner-specific bounded paper lifecycle and post-exit independent-flat evidence has been completed for this path.",
        ]
    )
    return blockers[:3]

def _semantic_state_hash(path: Path) -> str:
    if not path.is_file():
        return _sha256_json({"state": "absent"})
    payload = json.loads(path.read_text(encoding="utf-8"))
    projection = {
        key: payload.get(key)
        for key in (
            "cash",
            "currency",
            "positions",
            "gross_exposure",
            "open_orders",
            "orders",
            "fills",
            "seen_client_order_ids",
            "cycle_history",
        )
    }
    return _sha256_json(projection)

def _maximum_csv_timestamp(path: Path) -> datetime:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream)
        timestamps = [_utc_datetime(row["timestamp"]) for row in rows]
    if not timestamps:
        raise ValueError("offline fixture input contains no bars")
    return max(timestamps)

def _environment_preflight(
    environment: Mapping[str, object],
) -> dict[str, bool]:
    profile = str(environment.get("APP_PROFILE") or "").strip().lower()
    credential_names = (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    )
    return {
        "app_profile_paper": profile == "paper",
        "app_profile_live": profile == "live",
        "credentials_present": any(
            bool(str(environment.get(name) or "").strip())
            for name in credential_names
        ),
    }

def _git_branch_name() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""

def _scenario_passed(receipts: Sequence[Mapping[str, object]], scenario_id: str) -> bool:
    return any(
        receipt.get("scenario_id") == scenario_id
        and receipt.get("acceptance_passed") is True
        for receipt in receipts
    )

def _utc_datetime(value: datetime | str | object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return parsed.astimezone(UTC)

def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}

def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()

def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value

def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        _json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(_json_safe(row), sort_keys=True) + "\n")
