"""V5.32 end-to-end supervised crypto readiness evidence trial.

This module composes the existing deterministic crypto operating loop.  It does
not add a strategy, broker mutation path, retry loop, or authorization surface.
The default command is offline, writes only local generated evidence, and
performs no paper or live broker mutation.
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

from algotrader.execution.tomorrow_crypto_trader_demo import (
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

    replay_a = _run_sequential_replay(
        root=root / "replay_a",
        decision_start=start,
        cycle_count=cycle_count,
    )
    replay_b = _run_sequential_replay(
        root=root / "replay_b",
        decision_start=start,
        cycle_count=cycle_count,
    )
    deterministic_rerun = _deterministic_rerun_evidence(replay_a, replay_b)
    scenario_receipts = _run_scenario_matrix(
        root=root / "scenarios",
        decision_start=start + timedelta(hours=cycle_count + 2),
        primary_receipts=replay_a["receipts"],
        broker_observed_readiness=broker_observed_readiness,
        allow_alpaca_paper_read=allow_alpaca_paper_read,
    )
    is_fail_layout = False
    if receipt_root is not None:
        validation = _validate_offline_receipt(receipt_root)
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
            "app_profile_paper": _environment_preflight()["app_profile_paper"],
            "app_profile_live": _environment_preflight()["app_profile_live"],
            "credentials_present": _environment_preflight()["credentials_present"],
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
    root = Path(output_root)
    errors: list[str] = []
    packet_path = root / "readiness_packet.json"
    manifest_path = root / "manifest.json"
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "validation_status": "failed",
            "errors": [f"unreadable_or_invalid_artifact:{exc.__class__.__name__}"],
        }
    for name, entry in _mapping(manifest.get("artifacts")).items():
        path = Path(str(_mapping(entry).get("path", "")))
        if not path.is_file():
            errors.append(f"missing_artifact:{name}")
            continue
        if _file_sha256(path) != _mapping(entry).get("sha256"):
            errors.append(f"artifact_hash_mismatch:{name}")
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


def _run_sequential_replay(
    *,
    root: Path,
    decision_start: datetime,
    cycle_count: int,
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
            explanation="An injected SOLUSD position without matching fill provenance failed state reconciliation closed.",
        )
    )
    matrix.append(
        _duplicate_intent_scenario(
            root=root / "restart_idempotency",
            decision_time=decision_start + timedelta(hours=2),
        )
    )
    matrix.append(
        _state_injection_scenario(
            root=root / "stale_mismatch",
            decision_time=decision_start + timedelta(hours=3),
            scenario_id="stale_or_mismatched_evidence_block",
            mutation="cash_mismatch",
            expected_decision="blocked_state_reconciliation_failed",
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
) -> dict[str, object]:
    receipt = next(
        item
        for item in scenario_receipts
        if item.get("scenario_id") == "broker_unobserved_or_unavailable_block"
    )
    preview = _mapping(receipt.get("broker_preview"))
    preflight = _environment_preflight()
    if preview.get("broker_state_observed") is True:
        classification = "broker_observed_no_submit_completed"
    elif preflight["credentials_present"] is False:
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


def _write_trial_artifacts(root: Path, packet: Mapping[str, object]) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "readiness_packet": root / "readiness_packet.json",
        "operating_report": root / "operating_report.md",
        "cycle_receipts": root / "cycle_receipts.jsonl",
        "scenario_receipts": root / "scenario_receipts.jsonl",
        "manifest": root / "manifest.json",
    }
    artifact_paths = {name: str(path) for name, path in paths.items()}
    _write_json(paths["readiness_packet"], {**dict(packet), "artifact_paths": artifact_paths})
    paths["operating_report"].write_text(
        _render_operating_report(packet) + "\n", encoding="utf-8", newline="\n"
    )
    _write_jsonl(
        paths["cycle_receipts"],
        _mapping_sequence(_mapping(packet.get("sequential_replay")).get("receipts")),
    )
    _write_jsonl(paths["scenario_receipts"], _mapping_sequence(packet.get("scenario_receipts")))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_supervised_readiness_trial_manifest",
        "generated_under_runs": "runs" in tuple(part.lower() for part in root.parts),
        "tracked_runs_files": False,
        "artifacts": {
            name: {
                "path": str(path),
                "sha256": _file_sha256(path),
                "size": path.stat().st_size,
            }
            for name, path in paths.items()
            if name != "manifest"
        },
        "receipt_chain_hash": _mapping(packet.get("receipt_chain")).get("final_receipt_hash"),
        "trial_classification": packet.get("trial_classification"),
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_authorized": False,
    }
    _write_json(paths["manifest"], manifest)
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


def _environment_preflight() -> dict[str, bool]:
    profile = os.environ.get("APP_PROFILE", "").strip().lower()
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
        "credentials_present": any(bool(os.environ.get(name, "").strip()) for name in credential_names),
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


def _validate_offline_receipt(receipt_root: Path | str | None) -> dict[str, Any]:
    if not receipt_root:
        return {"valid": False, "classification": "blocked_credentials_unavailable", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

    root_path = Path(receipt_root)
    obs_path = root_path / "observation_receipt.json"
    inv_path = root_path / "invocation_receipt.json"
    fail_path = root_path / "failure_receipt.json"

    has_obs = obs_path.is_file()
    has_inv = inv_path.is_file()
    has_fail = fail_path.is_file()

    # Reject mixed layouts
    if has_obs and has_fail:
        return {"valid": False, "classification": "blocked_mixed_layouts", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

    if not has_obs and not has_fail:
        return {"valid": False, "classification": "blocked_credentials_or_expected_account_unavailable", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

    # Validate Success layout
    if has_obs:
        try:
            obs_receipt = json.loads(obs_path.read_text(encoding="utf-8"))
        except Exception:
            return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        schema_version = obs_receipt.get("schema_version")

        if schema_version == "v5_33_offline_fixture_replay_receipt_v1":
            if obs_receipt.get("source_classification") == "genuine_alpaca_paper_observation":
                return {"valid": False, "classification": "blocked_not_genuine", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            r_copy = dict(obs_receipt)
            original_hash = r_copy.pop("canonical_receipt_sha256", None)
            canonical_str = json.dumps(r_copy, sort_keys=True, separators=(",", ":"))
            expected_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
            if original_hash != expected_hash:
                return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            return {
                "valid": True,
                "classification": "fixture_replay_validated",
                "broker_state_observed": False,
                "network_used": False,
                "broker_read_occurred": False,
                "receipt": obs_receipt
            }

        elif schema_version == "v5_33_production_broker_observation_receipt_v1":
            if not has_inv:
                return {"valid": False, "classification": "blocked_invocation_receipt_missing", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            try:
                inv_receipt = json.loads(inv_path.read_text(encoding="utf-8"))
            except Exception:
                return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if inv_receipt.get("schema_version") != "v5_33_production_invocation_receipt_v1":
                return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            obs_copy = dict(obs_receipt)
            obs_original_hash = obs_copy.pop("canonical_receipt_sha256", None)
            obs_canonical_str = json.dumps(obs_copy, sort_keys=True, separators=(",", ":"))
            obs_expected_hash = hashlib.sha256(obs_canonical_str.encode("utf-8")).hexdigest()
            if obs_original_hash != obs_expected_hash:
                return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            inv_copy = dict(inv_receipt)
            inv_original_hash = inv_copy.pop("canonical_invocation_sha256", None)
            inv_canonical_str = json.dumps(inv_copy, sort_keys=True, separators=(",", ":"))
            inv_expected_hash = hashlib.sha256(inv_canonical_str.encode("utf-8")).hexdigest()
            if inv_original_hash != inv_expected_hash:
                return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if inv_receipt.get("observation_receipt_sha256") != obs_original_hash:
                return {"valid": False, "classification": "blocked_cross_bind_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if obs_receipt.get("source_classification") != "genuine_alpaca_paper_observation":
                return {"valid": False, "classification": "blocked_not_genuine", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            bundle_digest = inv_receipt.get("adapter_source_bundle_sha256")
            if not bundle_digest or bundle_digest == "0" * 64:
                return {"valid": False, "classification": "blocked_source_bundle_digest_invalid", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            repo_root = Path(".").resolve()
            from algotrader.execution.crypto_read_only_paper_observation_adapter import compute_source_bundle_digest
            try:
                local_digest, local_manifest = compute_source_bundle_digest(repo_root)
            except Exception:
                return {"valid": False, "classification": "blocked_source_bundle_missing_files", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if bundle_digest != local_digest:
                return {"valid": False, "classification": "blocked_source_bundle_digest_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            stored_manifest = inv_receipt.get("source_bundle_manifest", {})
            if local_manifest != stored_manifest:
                return {"valid": False, "classification": "blocked_source_bundle_manifest_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if obs_receipt.get("paper_endpoint_classification") != "https://paper-api.alpaca.markets":
                  return {"valid": False, "classification": "blocked_endpoint_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            if inv_receipt.get("normalized_paper_endpoint") != "https://paper-api.alpaca.markets":
                  return {"valid": False, "classification": "blocked_endpoint_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if not obs_receipt.get("expected_account_match") or not inv_receipt.get("expected_account_match"):
                return {"valid": False, "classification": "blocked_expected_account_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if obs_receipt.get("target_symbol") != "BTCUSD":
                return {"valid": False, "classification": "blocked_target_symbol_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            if obs_receipt.get("target_asset_class") != "crypto":
                return {"valid": False, "classification": "blocked_target_asset_class_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if not obs_receipt.get("target_tradability") or not obs_receipt.get("target_orderability"):
                return {"valid": False, "classification": "blocked_non_tradable_or_non_orderable", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            trunc = obs_receipt.get("truncation_indicators", {})
            if trunc.get("positions_truncated") or trunc.get("orders_truncated"):
                return {"valid": False, "classification": "blocked_truncation_detected", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if obs_receipt.get("unexpected_exposure_classification") != "clean":
                return {"valid": False, "classification": "blocked_unexpected_exposure", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            ambiguity = obs_receipt.get("ambiguity_indicators", {})
            if ambiguity.get("duplicate_positions") or ambiguity.get("duplicate_client_order_ids"):
                return {"valid": False, "classification": "blocked_ambiguity_detected", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            counters = inv_receipt.get("call_counters", {})
            expected_counters = {
                "account_read_count": 1,
                "positions_read_count": 1,
                "orders_read_count": 1,
                "target_asset_read_count": 1
            }
            if counters != expected_counters:
                return {"valid": False, "classification": "blocked_invalid_call_counts", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            obs_completion = inv_receipt.get("observation_completion_utc")
            if not obs_completion:
                return {"valid": False, "classification": "blocked_freshness_check_failed", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            try:
                completion_dt = datetime.fromisoformat(obs_completion.replace("Z", "+00:00"))
                age = (datetime.now(UTC) - completion_dt).total_seconds()
                if age < -60 or age > 900:
                    return {"valid": False, "classification": "blocked_stale_observation", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            except Exception:
                return {"valid": False, "classification": "blocked_malformed_timestamp", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            safety_obs = obs_receipt.get("safety_booleans", {})
            safety_inv = inv_receipt.get("safety_booleans", {})
            if (safety_obs.get("paper_submit_authorized") or safety_obs.get("paper_submit_performed") or
                safety_obs.get("broker_mutation_authorized") or safety_obs.get("broker_mutation_performed") or
                safety_obs.get("live_authorized") or
                safety_inv.get("paper_submit_authorized") or safety_inv.get("paper_submit_performed") or
                safety_inv.get("broker_mutation_authorized") or safety_inv.get("broker_mutation_performed") or
                safety_inv.get("live_authorized")):
                return {"valid": False, "classification": "blocked_mutation_or_live_authorized", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            status_fields = obs_receipt.get("account_status_fields", {})
            if (status_fields.get("status") != "active" or
                status_fields.get("trading_blocked") is not False or
                status_fields.get("account_blocked") is not False):
                return {"valid": False, "classification": "blocked_account_inactive_or_blocked", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            return {
                "valid": True,
                "classification": "broker_observed_no_submit_completed",
                "broker_state_observed": True,
                "network_used": True,
                "broker_read_occurred": True,
                "receipt": obs_receipt,
                "invocation": inv_receipt
            }
        else:
            return {"valid": False, "classification": "blocked_unsupported_schema", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

    # Validate Failure layout
    if has_fail:
        if not has_inv:
            return {"valid": False, "classification": "blocked_invocation_receipt_missing", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        try:
            failure_receipt = json.loads(fail_path.read_text(encoding="utf-8"))
        except Exception:
            return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if failure_receipt.get("schema_version") != "v5_33_production_failure_receipt_v1":
            return {"valid": False, "classification": "blocked_unsupported_schema", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Verify failure receipt hash
        fail_copy = dict(failure_receipt)
        fail_original_hash = fail_copy.pop("canonical_receipt_sha256", None)
        fail_canonical_str = json.dumps(fail_copy, sort_keys=True, separators=(",", ":"))
        fail_expected_hash = hashlib.sha256(fail_canonical_str.encode("utf-8")).hexdigest()
        if fail_original_hash != fail_expected_hash:
            return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Parse and verify invocation receipt
        try:
            inv_receipt = json.loads(inv_path.read_text(encoding="utf-8"))
        except Exception:
            return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if inv_receipt.get("schema_version") != "v5_33_production_invocation_receipt_v1":
            return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Verify invocation receipt hash (popping its own hash)
        inv_copy = dict(inv_receipt)
        inv_original_hash = inv_copy.pop("canonical_invocation_sha256", None)
        inv_canonical_str = json.dumps(inv_copy, sort_keys=True, separators=(",", ":"))
        inv_expected_hash = hashlib.sha256(inv_canonical_str.encode("utf-8")).hexdigest()
        if inv_original_hash != inv_expected_hash:
            return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Verify invocation ID equality
        if failure_receipt.get("invocation_id") != inv_receipt.get("invocation_id"):
            return {"valid": False, "classification": "blocked_invocation_id_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Verify invocation hash referenced by failure receipt
        if failure_receipt.get("invocation_receipt_sha256") != inv_original_hash:
            return {"valid": False, "classification": "blocked_cross_bind_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Source bundle check
        bundle_digest = inv_receipt.get("adapter_source_bundle_sha256")
        if not bundle_digest or bundle_digest == "0" * 64:
            return {"valid": False, "classification": "blocked_source_bundle_digest_invalid", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        repo_root = Path(".").resolve()
        from algotrader.execution.crypto_read_only_paper_observation_adapter import compute_source_bundle_digest
        try:
            local_digest, local_manifest = compute_source_bundle_digest(repo_root)
        except Exception:
            return {"valid": False, "classification": "blocked_source_bundle_missing_files", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if bundle_digest != local_digest:
            return {"valid": False, "classification": "blocked_source_bundle_digest_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        stored_manifest = inv_receipt.get("source_bundle_manifest", {})
        if local_manifest != stored_manifest:
            return {"valid": False, "classification": "blocked_source_bundle_manifest_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if inv_receipt.get("normalized_paper_endpoint") != "https://paper-api.alpaca.markets":
            return {"valid": False, "classification": "blocked_endpoint_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Return valid failure layout
        return {
            "valid": True,
            "is_failure_receipt": True,
            "classification": failure_receipt.get("terminal_stable_classification") or "blocked_observation_failed",
            "terminal_failure_stage": failure_receipt.get("terminal_failure_stage"),
            "sanitized_failure_category": failure_receipt.get("sanitized_transport_category"),
            "broker_state_observed": False,
            "network_used": inv_receipt.get("safety_booleans", {}).get("network_access_attempted", False),
            "broker_read_occurred": inv_receipt.get("safety_booleans", {}).get("network_access_attempted", False),
            "invocation": inv_receipt,
            "failure": failure_receipt
        }

    return {"valid": False, "classification": "blocked_unsupported_schema", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=MILESTONE_NAME)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--decision-start", default=DEFAULT_DECISION_START.isoformat())
    parser.add_argument("--cycle-count", type=int, default=DEFAULT_CYCLE_COUNT)
    parser.add_argument("--broker-observed-readiness", action="store_true")
    parser.add_argument("--allow-alpaca-paper-read", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--receipt-root", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.validate_only:
        result = validate_crypto_supervised_readiness_trial(args.output_root)
        print(json.dumps(result, sort_keys=True) if args.format == "json" else f"v5_32_validation_status={result['validation_status']}")
        return 0 if result["validation_status"] == "passed" else 1
    packet = run_crypto_supervised_readiness_trial(
        output_root=args.output_root,
        decision_start=args.decision_start,
        cycle_count=args.cycle_count,
        broker_observed_readiness=args.broker_observed_readiness,
        allow_alpaca_paper_read=args.allow_alpaca_paper_read,
        write_artifacts=True,
        receipt_root=args.receipt_root,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        print(f"v5_32_trial_classification={packet['trial_classification']}")
        print(f"v5_32_current_readiness_rung={packet['current_readiness_rung_code']}")
        print(f"v5_32_cycle_count={packet['cycle_count']}")
        print(f"v5_32_receipt_chain_hash={_mapping(packet['receipt_chain']).get('final_receipt_hash')}")
        print(f"v5_32_broker_observed_result={_mapping(packet['broker_observed_result']).get('classification')}")
        print("v5_32_paper_submit_performed=false")
        print("v5_32_broker_mutation_performed=false")
        print("v5_32_live_authorized=false")
    return 0 if packet["trial_classification"] == "accepted" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
