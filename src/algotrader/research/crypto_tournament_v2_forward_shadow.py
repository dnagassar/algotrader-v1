"""Preregister and bind the tournament-v2 single-winner forward shadow.

This module closes the implementation gap between a sealed tournament-v2
winner and its required future no-submit shadow evidence window.  It validates
the existing forward-OOS state through the public state-machine boundary,
freezes the downstream evidence contract before a winner is known, and can
derive an immutable activation only from a hash-bound terminal winner.

The module is local and research-only.  It cannot load credentials, access a
network or broker, plan an order, mutate a paper account, or authorize live
capital.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.crypto_preregistered_tournament_v2 import (
    CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT,
    MAXIMUM_CONSECUTIVE_MISSING_HOURS,
    MINIMUM_POSITIVE_RAW_VOLUME_FRACTION,
    MINIMUM_RAW_HOURLY_COVERAGE,
    OOS_END_EXCLUSIVE,
    build_crypto_tournament_v2_preregistration,
)
from algotrader.research.crypto_tournament_v2_forward_oos import (
    CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    run_crypto_tournament_v2_forward_oos,
)


CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_SCHEMA_VERSION = (
    "v5_24_crypto_tournament_v2_forward_shadow_v1"
)
CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_POLICY_VERSION = (
    "v5_24_crypto_tournament_v2_forward_shadow_policy_v1"
)
CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT = (
    "7ff152e69bd00eb8da9376d1f2be15194fbd04ed6a420151e30c3c46bec82436"
)
CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_strategy_tournament/v2/forward_shadow/latest"
)
FORWARD_SHADOW_HOURLY_BARS = 168
FORWARD_SHADOW_CHECKPOINT_HOURS = (24, 72, 168)

_ZERO_AUTHORITY_FIELDS = (
    "broker_read_occurred",
    "paper_or_broker_eligible",
    "paper_or_live_execution_authorized",
    "broker_mutation_authorized",
    "broker_mutation_occurred",
    "paper_submit_authorized",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_authorized",
    "live_endpoint_touched",
    "credential_values_exposed",
)
_NONTERMINAL_CLASSIFICATIONS = {
    "research_ready_for_future_oos_accrual",
    "collecting_untouched_oos",
    "awaiting_terminal_market_data_receipt",
}
_CLOSED_WITHOUT_WINNER_CLASSIFICATIONS = {
    "terminal_input_quality_gate",
    "no_candidate_qualified",
}
_ELIGIBLE_TERMINAL_CLASSIFICATION = (
    "eligible_for_no_submit_shadow_evaluation"
)
_ONE_HOUR = timedelta(hours=1)

__all__ = [
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_POLICY_VERSION",
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT",
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_SCHEMA_VERSION",
    "FORWARD_SHADOW_CHECKPOINT_HOURS",
    "FORWARD_SHADOW_HOURLY_BARS",
    "build_crypto_tournament_v2_forward_shadow_activation",
    "build_crypto_tournament_v2_forward_shadow_preregistration",
    "render_crypto_tournament_v2_forward_shadow_markdown",
    "run_crypto_tournament_v2_forward_shadow_readiness",
    "validate_crypto_tournament_v2_forward_shadow_activation",
]


def build_crypto_tournament_v2_forward_shadow_preregistration(
) -> dict[str, object]:
    """Return the candidate-agnostic contract frozen before v2 selection."""

    manifest: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_SCHEMA_VERSION
        ),
        "policy_version": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_POLICY_VERSION
        ),
        "record_type": (
            "crypto_tournament_v2_forward_shadow_preregistration"
        ),
        "source_tournament": {
            "required_preregistration_fingerprint": (
                CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
            ),
            "required_terminal_classification": (
                _ELIGIBLE_TERMINAL_CLASSIFICATION
            ),
            "required_terminal_scoring_performed": True,
            "required_selection_scope": (
                _ELIGIBLE_TERMINAL_CLASSIFICATION
            ),
            "required_selected_candidate_count": 1,
            "terminal_packet_sha256_required": True,
            "terminal_evidence_fingerprint_required": True,
            "selected_candidate_must_match_frozen_v2_manifest": True,
        },
        "temporal_policy": {
            "timeframe": "1Hour",
            "start_rule": (
                "first_complete_utc_hour_not_earlier_than_both_"
                "terminal_closure_and_v2_oos_end"
            ),
            "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
            "checkpoint_hours": list(FORWARD_SHADOW_CHECKPOINT_HOURS),
            "untouched_after_candidate_selection": True,
            "interim_performance_promotion_allowed": False,
            "early_stop_allowed": False,
            "window_extension_allowed": False,
        },
        "strategy_policy": {
            "candidate_set": "exactly_one_sealed_v2_terminal_winner",
            "candidate_parameters_mutable": False,
            "candidate_fingerprint_mutable": False,
            "direction": "long_or_cash",
            "signal_execution": "one_bar_lag",
            "decision_log_required_each_completed_hour": True,
            "imputed_bar_transition_policy": (
                "hold_prior_target_no_transition"
            ),
        },
        "data_quality_policy": {
            "source": "alpaca_market_data_crypto_bars_v1beta3",
            "guarded_refresh_receipt_required": True,
            "receipt_output_sha256_required": True,
            "exact_selected_symbol_only": True,
            "minimum_raw_hourly_coverage": (
                MINIMUM_RAW_HOURLY_COVERAGE
            ),
            "minimum_positive_raw_volume_fraction": (
                MINIMUM_POSITIVE_RAW_VOLUME_FRACTION
            ),
            "maximum_consecutive_missing_hours": (
                MAXIMUM_CONSECUTIVE_MISSING_HOURS
            ),
            "missing_first_or_last_bar_allowed": False,
            "isolated_gap_fill": "prior_close_ohlc_zero_volume",
        },
        "evidence_policy": {
            "hourly_causal_target_log_required": True,
            "hypothetical_position_and_transition_log_required": True,
            "base_cost_bps_per_transition": 40,
            "stress_cost_bps_per_transition": 80,
            "benchmarks": ["cash", "same_symbol_buy_hold"],
            "terminal_metrics": [
                "base_total_return",
                "stress_total_return",
                "same_symbol_buy_hold_return",
                "base_max_drawdown",
                "stress_max_drawdown",
                "transition_count",
                "completed_round_trip_count",
                "decision_log_completeness",
            ],
            "terminal_scope": (
                "evidence_complete_for_bounded_paper_probe_review"
            ),
            "paper_probe_authorized_by_terminal_scope": False,
            "live_probe_authorized_by_terminal_scope": False,
            "profit_claim_allowed": False,
        },
        "authority_boundary": {
            "network_access_authorized": False,
            "broker_read_authorized": False,
            "broker_mutation_authorized": False,
            "paper_planning_authorized": False,
            "paper_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_endpoint_authorized": False,
            "live_trading_authorized": False,
            "operator_review_required_after_terminal_shadow": True,
        },
        "dynamic_parameter_optimization": False,
        "post_selection_gate_mutation_allowed": False,
        "paper_or_live_execution_authorized": False,
        "profit_claim": "none",
    }
    fingerprint = _stable_hash(manifest)
    if (
        fingerprint
        != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT
    ):
        raise RuntimeError(
            "crypto tournament v2 forward-shadow preregistration drift "
            f"detected: {fingerprint}"
        )
    manifest["preregistration_fingerprint"] = fingerprint
    return manifest


def build_crypto_tournament_v2_forward_shadow_activation(
    tournament_packet: Mapping[str, object],
    *,
    as_of: datetime | str,
) -> dict[str, object]:
    """Classify and, only after a sealed winner, derive shadow activation."""

    evaluated_at = _utc_datetime(as_of, "as_of")
    contract = build_crypto_tournament_v2_forward_shadow_preregistration()
    source_classification = _required_text(
        tournament_packet.get("classification"),
        "tournament_packet.classification",
    )
    source_fingerprint = _required_text(
        tournament_packet.get("preregistration_fingerprint"),
        "tournament_packet.preregistration_fingerprint",
    )
    if source_fingerprint != CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT:
        raise ValidationError(
            "forward-shadow source tournament fingerprint mismatch."
        )
    _validate_false_authority(tournament_packet)

    frozen_state = _mapping(
        tournament_packet.get("frozen_state"),
        "tournament_packet.frozen_state",
    )
    packet = _base_activation_packet(
        contract=contract,
        tournament_packet=tournament_packet,
        frozen_state=frozen_state,
        as_of=evaluated_at,
    )

    terminal_closed = _required_bool(
        frozen_state.get("terminal_outcome_closed", False),
        "frozen_state.terminal_outcome_closed",
    )
    if not terminal_closed:
        if source_classification not in _NONTERMINAL_CLASSIFICATIONS:
            raise ValidationError(
                "nonterminal tournament state has an unsupported "
                "classification."
            )
        packet.update(
            {
                "classification": "waiting_for_tournament_terminal",
                "principal_blocker": (
                    "tournament_v2_untouched_oos_not_terminal"
                ),
                "next_action": (
                    "continue_receipt_bound_tournament_v2_oos_accrual"
                ),
            }
        )
        return packet

    _validate_terminal_binding(
        tournament_packet,
        frozen_state=frozen_state,
        as_of=evaluated_at,
    )
    selected = _mapping(
        tournament_packet.get("selected_candidate"),
        "tournament_packet.selected_candidate",
    )
    if source_classification in _CLOSED_WITHOUT_WINNER_CLASSIFICATIONS:
        if selected:
            raise ValidationError(
                "closed tournament without a winner cannot select a candidate."
            )
        packet.update(
            {
                "classification": "closed_without_shadow_candidate",
                "principal_blocker": "tournament_v2_produced_no_winner",
                "next_action": (
                    "do_not_activate_shadow_or_rescue_tune_tournament_v2"
                ),
            }
        )
        return packet

    if source_classification != _ELIGIBLE_TERMINAL_CLASSIFICATION:
        raise ValidationError(
            "terminal tournament classification is not supported by the "
            "forward-shadow contract."
        )
    candidate = _validated_selected_candidate(selected)
    closed_at = _utc_datetime(
        frozen_state.get("terminal_closed_at"),
        "frozen_state.terminal_closed_at",
    )
    start = max(
        _utc_datetime(OOS_END_EXCLUSIVE, "oos_end_exclusive"),
        _ceil_hour(closed_at),
    )
    end_exclusive = start + timedelta(hours=FORWARD_SHADOW_HOURLY_BARS)
    source_binding = _mapping(packet["source_binding"], "source_binding")
    activation_basis = {
        "forward_shadow_preregistration_fingerprint": contract[
            "preregistration_fingerprint"
        ],
        "source_terminal_packet_sha256": source_binding[
            "terminal_packet_sha256"
        ],
        "source_terminal_evidence_fingerprint": source_binding[
            "terminal_evidence_fingerprint"
        ],
        "source_state_fingerprint": source_binding[
            "state_fingerprint"
        ],
        "selected_candidate_id": candidate["candidate_id"],
        "selected_candidate_fingerprint": candidate[
            "candidate_fingerprint"
        ],
        "start": start.isoformat(),
        "end_exclusive": end_exclusive.isoformat(),
        "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
    }
    packet.update(
        {
            "classification": (
                "ready_to_activate_no_submit_forward_shadow"
            ),
            "principal_blocker": "none",
            "selected_candidate": candidate,
            "shadow_window": {
                "status": "frozen_untouched_future_window",
                "start": start.isoformat(),
                "end_exclusive": end_exclusive.isoformat(),
                "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
                "checkpoint_hours": list(FORWARD_SHADOW_CHECKPOINT_HOURS),
            },
            "activation_fingerprint": _stable_hash(activation_basis),
            "next_action": (
                "initialize_no_submit_forward_shadow_state_from_this_"
                "immutable_activation"
            ),
        }
    )
    validate_crypto_tournament_v2_forward_shadow_activation(packet)
    return packet


def validate_crypto_tournament_v2_forward_shadow_activation(
    packet: Mapping[str, object],
) -> dict[str, object]:
    """Validate one immutable ready activation without broadening authority."""

    if packet.get("classification") != (
        "ready_to_activate_no_submit_forward_shadow"
    ):
        raise ValidationError(
            "forward-shadow activation is not ready."
        )
    if packet.get("preregistration_fingerprint") != (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT
    ):
        raise ValidationError(
            "forward-shadow activation preregistration mismatch."
        )
    source = _mapping(packet.get("source_binding"), "source_binding")
    if source.get("tournament_preregistration_fingerprint") != (
        CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
    ):
        raise ValidationError(
            "forward-shadow activation tournament fingerprint mismatch."
        )
    if source.get("terminal_outcome_closed") is not True:
        raise ValidationError(
            "forward-shadow activation requires terminal closure."
        )
    if source.get("terminal_classification") != (
        _ELIGIBLE_TERMINAL_CLASSIFICATION
    ):
        raise ValidationError(
            "forward-shadow activation terminal classification mismatch."
        )
    for field_name in (
        "terminal_packet_sha256",
        "terminal_evidence_fingerprint",
        "state_fingerprint",
    ):
        value = _required_text(source.get(field_name), f"source_binding.{field_name}")
        _require_sha256(value, f"source_binding.{field_name}")
    closed_at = _utc_datetime(
        source.get("terminal_closed_at"),
        "source_binding.terminal_closed_at",
    )
    candidate = _validated_activation_candidate(
        _mapping(packet.get("selected_candidate"), "selected_candidate")
    )
    window = _mapping(packet.get("shadow_window"), "shadow_window")
    start = _utc_datetime(window.get("start"), "shadow_window.start")
    end_exclusive = _utc_datetime(
        window.get("end_exclusive"),
        "shadow_window.end_exclusive",
    )
    if window.get("status") != "frozen_untouched_future_window":
        raise ValidationError("forward-shadow window is not frozen.")
    if window.get("hourly_bars") != FORWARD_SHADOW_HOURLY_BARS:
        raise ValidationError("forward-shadow hourly bar count drifted.")
    if window.get("checkpoint_hours") != list(FORWARD_SHADOW_CHECKPOINT_HOURS):
        raise ValidationError("forward-shadow checkpoints drifted.")
    if end_exclusive - start != timedelta(hours=FORWARD_SHADOW_HOURLY_BARS):
        raise ValidationError("forward-shadow window duration drifted.")
    required_start = max(
        _utc_datetime(OOS_END_EXCLUSIVE, "oos_end_exclusive"),
        _ceil_hour(closed_at),
    )
    if start != required_start:
        raise ValidationError(
            "forward-shadow window start must equal the first eligible UTC hour."
        )
    activation_basis = {
        "forward_shadow_preregistration_fingerprint": packet[
            "preregistration_fingerprint"
        ],
        "source_terminal_packet_sha256": source[
            "terminal_packet_sha256"
        ],
        "source_terminal_evidence_fingerprint": source[
            "terminal_evidence_fingerprint"
        ],
        "source_state_fingerprint": source["state_fingerprint"],
        "selected_candidate_id": candidate["candidate_id"],
        "selected_candidate_fingerprint": candidate[
            "candidate_fingerprint"
        ],
        "start": start.isoformat(),
        "end_exclusive": end_exclusive.isoformat(),
        "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
    }
    if packet.get("activation_fingerprint") != _stable_hash(activation_basis):
        raise ValidationError("forward-shadow activation fingerprint mismatch.")
    for field_name in (
        "network_access_attempted",
        "market_data_fetch_occurred",
        "broker_read_occurred",
        "broker_mutation_authorized",
        "broker_mutation_occurred",
        "paper_submit_authorized",
        "paper_submit_occurred",
        "paper_cancel_occurred",
        "paper_replace_occurred",
        "paper_close_occurred",
        "paper_liquidate_occurred",
        "paper_or_broker_eligible",
        "paper_or_live_execution_authorized",
        "capital_allocation_authorized",
        "live_authorized",
        "live_endpoint_touched",
        "credential_values_exposed",
    ):
        if packet.get(field_name) is not False:
            raise ValidationError(
                f"forward-shadow activation safety field must be false: {field_name}"
            )
    if packet.get("paper_planning_eligibility") != "not_eligible":
        raise ValidationError(
            "forward-shadow activation paper planning must be ineligible."
        )
    if packet.get("profit_claim") != "none":
        raise ValidationError("forward-shadow activation profit claim must be none.")
    return {
        "activation_fingerprint": packet["activation_fingerprint"],
        "selected_candidate": candidate,
        "source_binding": dict(source),
        "shadow_window": dict(window),
    }


def run_crypto_tournament_v2_forward_shadow_readiness(
    *,
    tournament_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Validate tournament state and emit the downstream readiness packet."""

    evaluated_at = _utc_datetime(as_of, "as_of")
    tournament_path = _local_path(tournament_root, "tournament_root")
    output_path = _local_path(output_root, "output_root")
    tournament_packet = run_crypto_tournament_v2_forward_oos(
        output_root=tournament_path,
        as_of=evaluated_at,
        write_artifacts=False,
    )
    packet = build_crypto_tournament_v2_forward_shadow_activation(
        tournament_packet,
        as_of=evaluated_at,
    )
    packet["tournament_root"] = str(tournament_path)
    packet["output_root"] = str(output_path)
    if write_artifacts:
        output_path.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(
            output_path / "preregistration.json",
            build_crypto_tournament_v2_forward_shadow_preregistration(),
        )
        _write_json_atomic(output_path / "readiness_packet.json", packet)
        _write_text_atomic(
            output_path / "readiness_packet.md",
            render_crypto_tournament_v2_forward_shadow_markdown(packet),
        )
    return packet


def render_crypto_tournament_v2_forward_shadow_markdown(
    packet: Mapping[str, object],
) -> str:
    """Render the compact forward-shadow readiness receipt."""

    source = _mapping(packet.get("source_binding"), "source_binding")
    selected = _mapping(packet.get("selected_candidate"), "selected_candidate")
    window = _mapping(packet.get("shadow_window"), "shadow_window")
    return "\n".join(
        (
            "# Crypto Tournament V2 Forward-Shadow Readiness",
            "",
            f"- Classification: {packet.get('classification', '')}",
            f"- Principal blocker: {packet.get('principal_blocker', '')}",
            (
                "- Contract fingerprint: "
                f"{packet.get('preregistration_fingerprint', '')}"
            ),
            (
                "- Tournament classification: "
                f"{source.get('terminal_classification', '')}"
            ),
            (
                "- Tournament terminal SHA-256: "
                f"{source.get('terminal_packet_sha256', '')}"
            ),
            f"- Selected candidate: {selected.get('candidate_id', '')}",
            (
                "- Shadow start/end: "
                f"{window.get('start', '')} / {window.get('end_exclusive', '')}"
            ),
            (
                "- Activation fingerprint: "
                f"{packet.get('activation_fingerprint', '')}"
            ),
            "- Network, broker read/mutation, paper mutation, and live: false",
            "- Paper/capital authorization: none",
            "- Profit claim: none",
            f"- Next action: {packet.get('next_action', '')}",
            "",
        )
    )


def _base_activation_packet(
    *,
    contract: Mapping[str, object],
    tournament_packet: Mapping[str, object],
    frozen_state: Mapping[str, object],
    as_of: datetime,
) -> dict[str, object]:
    return {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_SCHEMA_VERSION
        ),
        "record_type": (
            "crypto_tournament_v2_forward_shadow_readiness_packet"
        ),
        "as_of": as_of.isoformat(),
        "classification": "",
        "principal_blocker": "",
        "preregistration_fingerprint": contract[
            "preregistration_fingerprint"
        ],
        "source_binding": {
            "tournament_preregistration_fingerprint": tournament_packet.get(
                "preregistration_fingerprint", ""
            ),
            "terminal_outcome_closed": frozen_state.get(
                "terminal_outcome_closed", False
            ),
            "terminal_classification": tournament_packet.get(
                "classification", ""
            ),
            "terminal_closed_at": frozen_state.get("terminal_closed_at", ""),
            "terminal_packet_sha256": frozen_state.get(
                "terminal_packet_sha256", ""
            ),
            "terminal_evidence_fingerprint": tournament_packet.get(
                "terminal_evidence_fingerprint", ""
            ),
            "state_fingerprint": frozen_state.get("state_fingerprint", ""),
        },
        "selected_candidate": {},
        "shadow_window": {
            "status": "not_frozen",
            "start": "",
            "end_exclusive": "",
            "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
            "checkpoint_hours": list(FORWARD_SHADOW_CHECKPOINT_HOURS),
        },
        "activation_fingerprint": "",
        "evidence_scope": "future_decision_quality_shadow_evidence",
        "strategy_evidence_evaluation_performed": False,
        "network_access_attempted": False,
        "market_data_fetch_occurred": False,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "paper_cancel_occurred": False,
        "paper_replace_occurred": False,
        "paper_close_occurred": False,
        "paper_liquidate_occurred": False,
        "paper_or_broker_eligible": False,
        "paper_planning_eligibility": "not_eligible",
        "paper_or_live_execution_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
        "next_action": "",
    }


def _validate_terminal_binding(
    tournament_packet: Mapping[str, object],
    *,
    frozen_state: Mapping[str, object],
    as_of: datetime,
) -> None:
    classification = _required_text(
        tournament_packet.get("classification"),
        "tournament_packet.classification",
    )
    state_classification = _required_text(
        frozen_state.get("terminal_classification"),
        "frozen_state.terminal_classification",
    )
    if state_classification != classification:
        raise ValidationError(
            "forward-shadow terminal classification binding mismatch."
        )
    closed_at = _utc_datetime(
        frozen_state.get("terminal_closed_at"),
        "frozen_state.terminal_closed_at",
    )
    if as_of < closed_at:
        raise ValidationError("forward-shadow as_of precedes terminal closure.")
    terminal_sha = _required_text(
        frozen_state.get("terminal_packet_sha256"),
        "frozen_state.terminal_packet_sha256",
    )
    _require_sha256(terminal_sha, "frozen_state.terminal_packet_sha256")
    state_fingerprint = _required_text(
        frozen_state.get("state_fingerprint"),
        "frozen_state.state_fingerprint",
    )
    _require_sha256(state_fingerprint, "frozen_state.state_fingerprint")
    evidence = _required_text(
        tournament_packet.get("terminal_evidence_fingerprint"),
        "tournament_packet.terminal_evidence_fingerprint",
    )
    _require_sha256(evidence, "terminal_evidence_fingerprint")
    if frozen_state.get("terminal_evidence_fingerprint") != evidence:
        raise ValidationError(
            "forward-shadow terminal evidence fingerprint mismatch."
        )
    scoring = _required_bool(
        tournament_packet.get("terminal_scoring_performed"),
        "tournament_packet.terminal_scoring_performed",
    )
    if frozen_state.get("terminal_scoring_performed") is not scoring:
        raise ValidationError(
            "forward-shadow terminal scoring binding mismatch."
        )
    if classification == _ELIGIBLE_TERMINAL_CLASSIFICATION and not scoring:
        raise ValidationError(
            "eligible forward-shadow activation requires terminal scoring."
        )
    closure = _mapping(
        tournament_packet.get("terminal_closure"),
        "tournament_packet.terminal_closure",
    )
    if closure.get("terminal_outcome_closed") is not True:
        raise ValidationError("forward-shadow requires a sealed terminal closure.")
    if closure.get("terminal_classification") != classification:
        raise ValidationError(
            "forward-shadow terminal closure classification mismatch."
        )
    if closure.get("terminal_closed_at") != closed_at.isoformat():
        raise ValidationError(
            "forward-shadow terminal closure timestamp mismatch."
        )
    if closure.get("terminal_scoring_performed") is not scoring:
        raise ValidationError(
            "forward-shadow terminal closure scoring mismatch."
        )
    if closure.get("terminal_evidence_fingerprint") != evidence:
        raise ValidationError(
            "forward-shadow terminal closure evidence mismatch."
        )


def _validated_selected_candidate(
    selected: Mapping[str, object],
) -> dict[str, object]:
    candidate_id = _required_text(
        selected.get("candidate_id"),
        "selected_candidate.candidate_id",
    )
    candidate_fingerprint = _required_text(
        selected.get("candidate_fingerprint"),
        "selected_candidate.candidate_fingerprint",
    )
    manifest = build_crypto_tournament_v2_preregistration()
    candidates = _mapping_sequence(manifest.get("candidates"), "candidates")
    matches = tuple(
        candidate
        for candidate in candidates
        if candidate.get("candidate_id") == candidate_id
        and candidate.get("candidate_fingerprint") == candidate_fingerprint
    )
    if len(matches) != 1:
        raise ValidationError(
            "selected shadow candidate does not match the frozen v2 manifest."
        )
    if selected.get("candidate_decision") != _ELIGIBLE_TERMINAL_CLASSIFICATION:
        raise ValidationError("selected shadow candidate decision is not eligible.")
    if selected.get("selection_scope") != _ELIGIBLE_TERMINAL_CLASSIFICATION:
        raise ValidationError("selected shadow candidate scope is not eligible.")
    if selected.get("paper_or_broker_eligible") is not False:
        raise ValidationError(
            "selected shadow candidate must remain broker-ineligible."
        )
    return dict(matches[0])


def _validated_activation_candidate(
    selected: Mapping[str, object],
) -> dict[str, object]:
    candidate_id = _required_text(
        selected.get("candidate_id"),
        "selected_candidate.candidate_id",
    )
    candidate_fingerprint = _required_text(
        selected.get("candidate_fingerprint"),
        "selected_candidate.candidate_fingerprint",
    )
    candidates = _mapping_sequence(
        build_crypto_tournament_v2_preregistration().get("candidates"),
        "candidates",
    )
    matches = tuple(
        dict(candidate)
        for candidate in candidates
        if candidate.get("candidate_id") == candidate_id
        and candidate.get("candidate_fingerprint") == candidate_fingerprint
    )
    if len(matches) != 1 or dict(selected) != matches[0]:
        raise ValidationError(
            "forward-shadow activation candidate drifted from the frozen v2 manifest."
        )
    return matches[0]


def _validate_false_authority(packet: Mapping[str, object]) -> None:
    for field_name in _ZERO_AUTHORITY_FIELDS:
        if field_name not in packet or packet[field_name] is not False:
            raise ValidationError(
                f"forward-shadow source safety field must be false: {field_name}"
            )
    if packet.get("paper_planning_eligibility") != "not_eligible":
        raise ValidationError(
            "forward-shadow source paper planning must remain ineligible."
        )
    if packet.get("profit_claim") != "none":
        raise ValidationError("forward-shadow source cannot carry a profit claim.")


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be an object.")
    return value


def _mapping_sequence(
    value: object,
    field_name: str,
) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{field_name} must be a list of objects.")
    rows: list[Mapping[str, object]] = []
    for item in value:
        rows.append(_mapping(item, field_name))
    return tuple(rows)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be non-empty text.")
    return value.strip()


def _required_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be boolean.")
    return value


def _require_sha256(value: str, field_name: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValidationError(f"{field_name} must be lowercase SHA-256 text.")


def _utc_datetime(value: datetime | str | object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO-8601.") from exc
    else:
        raise ValidationError(f"{field_name} must be a UTC timestamp.")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValidationError(f"{field_name} must include UTC offset.")
    return parsed.astimezone(UTC)


def _ceil_hour(value: datetime) -> datetime:
    floored = value.replace(minute=0, second=0, microsecond=0)
    return floored if value == floored else floored + _ONE_HOUR


def _local_path(value: Path | str, field_name: str) -> Path:
    path = Path(value)
    if str(path).startswith(("\\\\", "//")):
        raise ValidationError(f"{field_name} must be a local path.")
    return path


def _stable_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    _write_text_atomic(
        path,
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
    )


def _write_text_atomic(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crypto-tournament-v2-forward-shadow",
        description=(
            "Build the offline preregistered readiness packet for the sealed "
            "tournament-v2 single-winner forward shadow."
        ),
    )
    parser.add_argument(
        "--tournament-root",
        default=str(CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        packet = run_crypto_tournament_v2_forward_shadow_readiness(
            tournament_root=args.tournament_root,
            output_root=args.output_root,
            as_of=args.as_of,
        )
    except (OSError, ValidationError, RuntimeError) as exc:
        raise SystemExit(f"forward-shadow readiness failed: {exc}") from exc
    if args.format == "json":
        print(json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print(render_crypto_tournament_v2_forward_shadow_markdown(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
