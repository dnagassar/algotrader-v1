"""Default-denied review of one sealed tournament-v2 crypto winner.

This module consumes only validated local V5.25 terminal evidence and local
capability-reference files.  It never imports an execution adapter, reads an
account, contacts a network, constructs an order, mutates paper state, or
authorizes capital.  Its strongest outcome is operator-review eligibility for
a separate, exact future authorization milestone.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
from typing import BinaryIO, Iterator

from algotrader.core.paper_account_binding import (
    validate_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError
from algotrader.research.crypto_preregistered_tournament_v2 import (
    MAXIMUM_CONSECUTIVE_MISSING_HOURS,
    MINIMUM_POSITIVE_RAW_VOLUME_FRACTION,
    MINIMUM_RAW_HOURLY_COVERAGE,
    build_crypto_tournament_v2_preregistration,
)
from algotrader.research.crypto_tournament_v2_forward_shadow import (
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT,
    FORWARD_SHADOW_CHECKPOINT_HOURS,
    FORWARD_SHADOW_HOURLY_BARS,
)
from algotrader.research.crypto_tournament_v2_forward_shadow_state import (
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT,
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION,
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION,
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_TERMINAL_EVIDENCE_SCHEMA_VERSION,
    export_crypto_tournament_v2_forward_shadow_terminal_evidence,
    run_crypto_tournament_v2_forward_shadow_state,
)


CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_REVIEW_SCHEMA_VERSION = (
    "v5_26_crypto_tournament_v2_bounded_paper_probe_review_v1"
)
CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_POLICY_VERSION = (
    "v5_26_crypto_tournament_v2_bounded_paper_probe_policy_v1"
)
CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SCHEMA_VERSION = (
    "v5_26_crypto_tournament_v2_bounded_paper_probe_capability_v1"
)
CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION = (
    "v5_26_crypto_tournament_v2_bounded_paper_probe_capability_source_v1"
)
CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT = (
    "3b82ebcaf3c80b9c1fbda5797623b2e616dfef0a3ed38d2cc52c0b1d3151efb5"
)
CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_strategy_tournament/v2/bounded_paper_probe_review/latest"
)
CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_CAPABILITY_ROOT = Path(
    "runs/crypto_strategy_tournament/v2/bounded_paper_probe_capabilities/latest"
)

_REVIEW_GENERATION_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "publication_fingerprint",
        "review_fingerprint",
        "admission_fingerprint",
        "as_of",
        "artifact_sha256",
        "broker_mutation_authorized",
        "paper_mutation_authorized",
        "capital_allocation_authorized",
        "live_authorized",
    }
)
_REVIEW_LATEST_POINTER_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "publication_fingerprint",
        "generation_relative_path",
        "generation_manifest_sha256",
        "review_fingerprint",
        "admission_fingerprint",
        "as_of",
        "broker_mutation_authorized",
        "paper_mutation_authorized",
        "capital_allocation_authorized",
        "live_authorized",
        "pointer_fingerprint",
    }
)

_ELIGIBLE_SOURCE_CLASSIFICATION = (
    "evidence_complete_for_bounded_paper_probe_review"
)
_QUALITY_SOURCE_CLASSIFICATION = "terminal_shadow_input_quality_gate"
_CAPABILITY_RECORD_TYPE = (
    "crypto_tournament_v2_bounded_paper_probe_capability_evidence"
)
_CAPABILITY_SOURCE_RECORD_TYPE = (
    "crypto_tournament_v2_bounded_paper_probe_capability_source"
)
_CAPABILITY_PRODUCER_VERSION = (
    "v5_26_crypto_tournament_v2_bounded_paper_probe_capability_producer_v1"
)
_BOUNDED_ORDER_POLICY_SNAPSHOT_VERSION = (
    "v5_26_crypto_bounded_order_policy_snapshot_v1"
)
_CAPABILITY_KINDS = (
    "venue_orderability",
    "bounded_order_policy",
    "lifecycle_flat_reconciliation",
    "durable_kill_loss_control",
)
_CAPABILITY_MAX_AGE_HOURS = {
    "venue_orderability": 24,
    "bounded_order_policy": 720,
    "lifecycle_flat_reconciliation": 720,
    "durable_kill_loss_control": 168,
}
_CAPABILITY_UPSTREAM_SOURCE_CONTRACTS = {
    "venue_orderability": (
        (
            "orderability_metadata",
            "v5_1_crypto_universe_refresh_v1",
            "crypto_orderability_metadata",
        ),
    ),
    "bounded_order_policy": (
        (
            "canonical_order_policy_snapshot",
            _BOUNDED_ORDER_POLICY_SNAPSHOT_VERSION,
            "crypto_bounded_order_policy_snapshot",
        ),
    ),
    "lifecycle_flat_reconciliation": (
        (
            "lifecycle_mechanics_certification",
            "v5_26_crypto_lifecycle_mechanics_certification_v1",
            "crypto_lifecycle_mechanics_certification_result",
        ),
        (
            "independent_flat_reconciliation",
            "v5_26_crypto_independent_flat_reconciliation_v1",
            "crypto_independent_flat_reconciliation_result",
        ),
    ),
    "durable_kill_loss_control": (
        (
            "durable_kill_loss_certification",
            "v5_26_crypto_durable_kill_loss_certification_v1",
            "crypto_durable_kill_loss_certification_result",
        ),
    ),
}
_SUPPORTED_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD")
_MAX_NOTIONAL = Decimal("10")
_MAX_LOSS = Decimal("2")
_MAX_DRAWDOWN = Decimal("0.20")
_BASE_COST = Decimal("0.004")
_STRESS_COST = Decimal("0.008")
_DECIMAL_QUANTUM = Decimal("0.00000001")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_REVIEW_AUTHORITY_FIELDS = (
    "network_access_authorized",
    "network_access_attempted",
    "broker_read_authorized",
    "broker_read_occurred",
    "broker_mutation_authorized",
    "broker_mutation_occurred",
    "paper_probe_authorized",
    "paper_mutation_authorized",
    "paper_mutation_occurred",
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
)
_SOURCE_SAFETY_FALSE_FIELDS = (
    "broker_read_occurred",
    "broker_mutation_authorized",
    "broker_mutation_occurred",
    "paper_probe_authorized",
    "paper_mutation_authorized",
    "capital_allocation_authorized",
    "live_authorized",
    "live_endpoint_touched",
    "credential_values_exposed",
)
_TERMINAL_EVIDENCE_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "classification",
        "review_eligible_source",
        "terminal_scoring_performed",
        "selected_candidate",
        "selected_symbol",
        "shadow_window",
        "progress",
        "terminal_input_quality",
        "terminal_metrics",
        "source_binding",
        "safety",
        "as_of",
        "evidence_export_fingerprint",
    }
)
_TERMINAL_SOURCE_BINDING_KEYS = frozenset(
    {
        "preregistration_fingerprint",
        "state_schema_version",
        "packet_schema_version",
        "activation_fingerprint",
        "activation_source_state_fingerprint",
        "state_fingerprint",
        "context_sha256",
        "terminal_packet_sha256",
        "terminal_evidence_fingerprint",
        "terminal_closed_at",
        "artifact_sha256",
    }
)
_TERMINAL_ARTIFACT_NAMES = frozenset(
    {
        "preregistration",
        "activation",
        "source_terminal_packet",
        "context",
        "activation_warmup",
        "shadow_raw",
        "shadow_normalized",
        "ledger",
        "decision_log",
        "checkpoint_ledger",
    }
)
_TERMINAL_SAFETY_KEYS = frozenset(
    {
        *_SOURCE_SAFETY_FALSE_FIELDS,
        "source_network_access_attempted",
        "source_market_data_fetch_occurred",
        "profit_claim",
    }
)
_WINDOW_METRIC_KEYS = {
    "start",
    "end",
    "bar_count",
    "total_return",
    "max_drawdown",
    "transition_count",
    "completed_round_trips",
    "turnover",
    "estimated_cost_return",
}
_TERMINAL_METRIC_KEYS = {
    "initial_exposure",
    "base_metrics",
    "stress_metrics",
    "cash_total_return",
    "same_symbol_buy_hold",
    "base_excess_vs_buy_hold",
    "stress_excess_vs_buy_hold",
    "decision_log_expected_rows",
    "decision_log_observed_rows",
    "decision_log_missing_rows",
    "decision_log_duplicate_rows",
    "decision_log_complete",
    "no_forced_terminal_liquidation",
    "paper_probe_authorized",
    "live_probe_authorized",
}

__all__ = [
    "CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SCHEMA_VERSION",
    "CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION",
    "CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_CAPABILITY_ROOT",
    "CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_POLICY_VERSION",
    "CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT",
    "CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_REVIEW_SCHEMA_VERSION",
    "build_crypto_tournament_v2_bounded_paper_probe_preregistration",
    "build_crypto_tournament_v2_bounded_paper_probe_review",
    "main",
    "render_crypto_tournament_v2_bounded_paper_probe_review_markdown",
    "run_crypto_tournament_v2_bounded_paper_probe_review",
    "validate_crypto_tournament_v2_bounded_paper_probe_review_packet",
]


def build_crypto_tournament_v2_bounded_paper_probe_preregistration(
) -> dict[str, object]:
    """Return the candidate-agnostic contract frozen before shadow results."""

    manifest: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_REVIEW_SCHEMA_VERSION
        ),
        "policy_version": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_POLICY_VERSION
        ),
        "record_type": (
            "crypto_tournament_v2_bounded_paper_probe_preregistration"
        ),
        "source_contract": {
            "required_forward_shadow_preregistration_fingerprint": (
                CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT
            ),
            "required_state_schema_version": (
                CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION
            ),
            "required_packet_schema_version": (
                CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION
            ),
            "required_terminal_export_schema_version": (
                CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_TERMINAL_EVIDENCE_SCHEMA_VERSION
            ),
            "required_terminal_classification": (
                _ELIGIBLE_SOURCE_CLASSIFICATION
            ),
            "required_terminal_scoring_performed": True,
            "required_hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
            "required_checkpoint_hours": list(FORWARD_SHADOW_CHECKPOINT_HOURS),
            "terminal_packet_sha256_required": True,
            "terminal_evidence_fingerprint_required": True,
            "independent_metric_and_decision_regeneration_required": True,
            "base_transition_cost_rate": _decimal_text(_BASE_COST),
            "stress_transition_cost_rate": _decimal_text(_STRESS_COST),
        },
        "ordered_strategy_gates": [
            {
                "gate_id": "base_return_strictly_positive",
                "metric": "base_metrics.total_return",
                "comparison": ">",
                "threshold": "0",
            },
            {
                "gate_id": "stress_return_strictly_positive",
                "metric": "stress_metrics.total_return",
                "comparison": ">",
                "threshold": "0",
            },
            {
                "gate_id": "base_excess_vs_buy_hold_strictly_positive",
                "metric": "base_excess_vs_buy_hold",
                "comparison": ">",
                "threshold": "0",
            },
            {
                "gate_id": "stress_excess_vs_buy_hold_strictly_positive",
                "metric": "stress_excess_vs_buy_hold",
                "comparison": ">",
                "threshold": "0",
            },
            {
                "gate_id": "base_max_drawdown_within_20_percent",
                "metric": "base_metrics.max_drawdown",
                "comparison": "<=",
                "threshold": _decimal_text(_MAX_DRAWDOWN),
            },
            {
                "gate_id": "stress_max_drawdown_within_20_percent",
                "metric": "stress_metrics.max_drawdown",
                "comparison": "<=",
                "threshold": _decimal_text(_MAX_DRAWDOWN),
            },
            {
                "gate_id": "base_drawdown_not_worse_than_buy_hold",
                "metric": "base_metrics.max_drawdown",
                "comparison": "<=",
                "threshold_metric": (
                    "same_symbol_buy_hold.base_metrics.max_drawdown"
                ),
            },
            {
                "gate_id": "stress_drawdown_not_worse_than_buy_hold",
                "metric": "stress_metrics.max_drawdown",
                "comparison": "<=",
                "threshold_metric": (
                    "same_symbol_buy_hold.stress_metrics.max_drawdown"
                ),
            },
        ],
        "strategy_gate_policy": {
            "all_gates_required": True,
            "minimum_transition_count": None,
            "minimum_completed_round_trips": None,
            "ranking_or_candidate_substitution_allowed": False,
            "rescoring_or_retuning_allowed": False,
            "window_extension_allowed": False,
            "economic_failure_is_terminal_for_activation": True,
        },
        "bounded_probe_envelope": _probe_envelope(),
        "operational_evidence_policy": {
            "required_capability_kinds": list(_CAPABILITY_KINDS),
            "capability_schema_version": (
                CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SCHEMA_VERSION
            ),
            "capability_source_schema_version": (
                CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION
            ),
            "capability_producer_version": _CAPABILITY_PRODUCER_VERSION,
            "exact_selected_symbol_required": True,
            "source_file_sha256_required": True,
            "source_digest_chain_required": True,
            "producer_source_resolution_required": True,
            "claims_must_equal_producer_source": True,
            "coherent_bundle_fingerprint_required": True,
            "upstream_source_contracts": {
                kind: [
                    {
                        "role": role,
                        "schema_version": schema_version,
                        "record_type": record_type,
                    }
                    for role, schema_version, record_type in contracts
                ]
                for kind, contracts in (
                    _CAPABILITY_UPSTREAM_SOURCE_CONTRACTS.items()
                )
            },
            "upstream_freshness_rule": (
                "earliest_upstream_observation_controls_kind_expiry"
            ),
            "maximum_age_hours": dict(_CAPABILITY_MAX_AGE_HOURS),
            "all_capabilities_required": True,
        },
        "outcome_policy": {
            "strongest_outcome": "eligible_for_operator_review_only",
            "separate_exact_operator_authorization_required": True,
            "automatic_paper_promotion_allowed": False,
            "automatic_live_promotion_allowed": False,
        },
        "authority_boundary": {
            "network_access_authorized": False,
            "broker_read_authorized": False,
            "broker_mutation_authorized": False,
            "paper_probe_authorized": False,
            "paper_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_endpoint_authorized": False,
            "live_trading_authorized": False,
        },
        "dynamic_parameter_optimization": False,
        "post_terminal_gate_mutation_allowed": False,
        "profit_claim": "none",
    }
    fingerprint = _stable_hash(manifest)
    if (
        CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        and fingerprint
        != CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
    ):
        raise RuntimeError(
            "crypto bounded-paper-probe preregistration drift detected: "
            f"{fingerprint}"
        )
    manifest["preregistration_fingerprint"] = fingerprint
    return manifest


def build_crypto_tournament_v2_bounded_paper_probe_review(
    terminal_evidence: Mapping[str, object] | None,
    *,
    capability_evidence: Mapping[str, Mapping[str, object]] | None = None,
    capability_artifact_sha256: Mapping[str, str] | None = None,
    capability_source_evidence: Mapping[
        str, Mapping[str, object]
    ] | None = None,
    capability_source_artifact_sha256: Mapping[str, str] | None = None,
    capability_upstream_evidence: Mapping[
        str, Mapping[str, Mapping[str, object]]
    ] | None = None,
    capability_upstream_artifact_sha256: Mapping[
        str, Mapping[str, str]
    ] | None = None,
    as_of: datetime | str,
) -> dict[str, object]:
    """Build one deterministic review without paper or live authority."""

    evaluated_at = _utc_datetime(as_of, "as_of")
    contract = build_crypto_tournament_v2_bounded_paper_probe_preregistration()
    capabilities = capability_evidence or {}
    capability_hashes = capability_artifact_sha256 or {}
    capability_sources = capability_source_evidence or {}
    capability_source_hashes = capability_source_artifact_sha256 or {}
    capability_upstreams = capability_upstream_evidence or {}
    capability_upstream_hashes = capability_upstream_artifact_sha256 or {}
    if terminal_evidence is None:
        return _review_packet(
            contract=contract,
            as_of=evaluated_at,
            classification="waiting_for_v5_25_terminal_evidence",
            next_action="continue_v5_25_forward_shadow_accrual",
            terminal_evidence=None,
            strategy_gate_results=(),
            capability_results=_missing_capability_results(),
            blockers=("v5_25_terminal_evidence_not_available",),
        )

    source = _validate_terminal_evidence(terminal_evidence, evaluated_at)
    if source["classification"] == _QUALITY_SOURCE_CLASSIFICATION:
        return _review_packet(
            contract=contract,
            as_of=evaluated_at,
            classification="closed_by_terminal_shadow_input_quality_gate",
            next_action="do_not_extend_retune_or_activate_paper_probe",
            terminal_evidence=source,
            strategy_gate_results=(),
            capability_results=_missing_capability_results(
                status="not_evaluated_after_source_rejection"
            ),
            blockers=("v5_25_terminal_shadow_input_quality_gate",),
        )

    strategy_results, strategy_failures = _evaluate_strategy_gates(
        source,
        contract,
    )
    if strategy_failures:
        return _review_packet(
            contract=contract,
            as_of=evaluated_at,
            classification="rejected_by_preregistered_strategy_gates",
            next_action="close_activation_without_probe_or_rescue_tuning",
            terminal_evidence=source,
            strategy_gate_results=strategy_results,
            capability_results=_missing_capability_results(
                status="not_evaluated_after_strategy_rejection"
            ),
            blockers=strategy_failures,
        )

    symbol = _required_text(source.get("selected_symbol"), "selected_symbol")
    capability_results = _evaluate_capabilities(
        capabilities,
        capability_hashes,
        capability_sources,
        capability_source_hashes,
        capability_upstreams,
        capability_upstream_hashes,
        symbol=symbol,
        as_of=evaluated_at,
    )
    capability_blockers = tuple(
        blocker
        for kind in _CAPABILITY_KINDS
        for blocker in _string_sequence(
            _mapping(capability_results[kind], kind).get("blockers")
        )
    )
    ready = not capability_blockers
    return _review_packet(
        contract=contract,
        as_of=evaluated_at,
        classification=(
            "eligible_for_operator_review_only"
            if ready
            else "blocked_by_operational_evidence"
        ),
        next_action=(
            "request_separate_exact_bounded_paper_probe_authorization_review"
            if ready
            else "produce_missing_selected_symbol_operational_evidence"
        ),
        terminal_evidence=source,
        strategy_gate_results=strategy_results,
        capability_results=capability_results,
        blockers=capability_blockers,
    )


def run_crypto_tournament_v2_bounded_paper_probe_review(
    *,
    shadow_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    capability_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_CAPABILITY_ROOT
    ),
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Inspect local evidence and persist a no-authority review packet."""

    evaluated_at = _utc_datetime(as_of, "as_of")
    shadow_path = _local_path(shadow_root, "shadow_root")
    capability_path = _local_path(capability_root, "capability_root")
    output_path = _local_path(output_root, "output_root")
    terminal_evidence: Mapping[str, object] | None = None
    state_path = shadow_path / "frozen_state.json"
    if state_path.is_file():
        status = run_crypto_tournament_v2_forward_shadow_state(
            output_root=shadow_path,
            as_of=evaluated_at,
            write_artifacts=False,
        )
        frozen_state = _mapping(status.get("frozen_state"), "frozen_state")
        if frozen_state.get("terminal_outcome_closed") is True:
            terminal_evidence = (
                export_crypto_tournament_v2_forward_shadow_terminal_evidence(
                    output_root=shadow_path,
                    as_of=evaluated_at,
                )
            )
    packet = build_crypto_tournament_v2_bounded_paper_probe_review(
        terminal_evidence,
        as_of=evaluated_at,
    )
    capabilities: Mapping[str, Mapping[str, object]] = {}
    capability_sources: Mapping[str, Mapping[str, object]] = {}
    capability_upstreams: Mapping[
        str, Mapping[str, Mapping[str, object]]
    ] = {}
    capability_support_artifacts: Mapping[str, bytes] = {}
    if packet["classification"] == "blocked_by_operational_evidence":
        (
            capabilities,
            capability_hashes,
            capability_sources,
            capability_source_hashes,
            capability_upstreams,
            capability_upstream_hashes,
            capability_support_artifacts,
        ) = _load_capability_artifacts(capability_path)
        packet = build_crypto_tournament_v2_bounded_paper_probe_review(
            terminal_evidence,
            capability_evidence=capabilities,
            capability_artifact_sha256=capability_hashes,
            capability_source_evidence=capability_sources,
            capability_source_artifact_sha256=capability_source_hashes,
            capability_upstream_evidence=capability_upstreams,
            capability_upstream_artifact_sha256=capability_upstream_hashes,
            as_of=evaluated_at,
        )
    if write_artifacts:
        _publish_review_artifacts(
            output_path,
            preregistration=(
                build_crypto_tournament_v2_bounded_paper_probe_preregistration()
            ),
            packet=packet,
            markdown=render_crypto_tournament_v2_bounded_paper_probe_review_markdown(
                packet
            ),
            terminal_evidence=terminal_evidence,
            capability_evidence=capabilities,
            capability_source_evidence=capability_sources,
            capability_upstream_evidence=capability_upstreams,
            capability_support_artifacts=capability_support_artifacts,
        )
    return packet


def render_crypto_tournament_v2_bounded_paper_probe_review_markdown(
    packet: Mapping[str, object],
) -> str:
    """Render one compact, explicit no-authority review summary."""

    candidate = _mapping(packet.get("selected_candidate"), "selected_candidate")
    blockers = _string_sequence(packet.get("blockers"))
    return "\n".join(
        (
            "# Crypto Tournament V2 Bounded Paper-Probe Review",
            "",
            f"- Classification: {packet.get('classification', '')}",
            f"- Candidate: {candidate.get('candidate_id', '')}",
            f"- Symbol: {candidate.get('symbol', '')}",
            (
                "- Contract fingerprint: "
                f"{packet.get('preregistration_fingerprint', '')}"
            ),
            (
                "- Review fingerprint: "
                f"{packet.get('review_fingerprint', '')}"
            ),
            f"- Blockers: {', '.join(blockers) if blockers else 'none'}",
            "- Paper probe, broker mutation, capital, and live authority: false",
            "- Separate exact operator authorization still required: true",
            "- Profit claim: none",
            f"- Next action: {packet.get('next_action', '')}",
            "",
        )
    )


def _review_packet(
    *,
    contract: Mapping[str, object],
    as_of: datetime,
    classification: str,
    next_action: str,
    terminal_evidence: Mapping[str, object] | None,
    strategy_gate_results: Sequence[Mapping[str, object]],
    capability_results: Mapping[str, Mapping[str, object]],
    blockers: Sequence[str],
) -> dict[str, object]:
    source = dict(terminal_evidence or {})
    source_binding = dict(
        _mapping(source.get("source_binding", {}), "source_binding")
    )
    candidate = dict(
        _mapping(source.get("selected_candidate", {}), "selected_candidate")
    )
    terminal_summary = (
        {
            "classification": source.get("classification", ""),
            "review_eligible_source": source.get(
                "review_eligible_source", False
            ),
            "terminal_scoring_performed": source.get(
                "terminal_scoring_performed", False
            ),
            "evidence_export_fingerprint": source.get(
                "evidence_export_fingerprint", ""
            ),
            "source_binding": source_binding,
            "shadow_window": dict(
                _mapping(source.get("shadow_window", {}), "shadow_window")
            ),
            "terminal_input_quality": dict(
                _mapping(
                    source.get("terminal_input_quality", {}),
                    "terminal_input_quality",
                )
            ),
            "terminal_metrics": dict(
                _mapping(source.get("terminal_metrics", {}), "terminal_metrics")
            ),
            "source_safety": dict(
                _mapping(source.get("safety", {}), "safety")
            ),
        }
        if source
        else {}
    )
    normalized_capabilities = {
        kind: dict(_mapping(capability_results[kind], kind))
        for kind in _CAPABILITY_KINDS
    }
    normalized_gates = [dict(item) for item in strategy_gate_results]
    unique_blockers = list(dict.fromkeys(str(item) for item in blockers))
    ready = classification == "eligible_for_operator_review_only"
    packet: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_REVIEW_SCHEMA_VERSION
        ),
        "record_type": (
            "crypto_tournament_v2_bounded_paper_probe_review_packet"
        ),
        "as_of": as_of.isoformat(),
        "classification": classification,
        "preregistration_fingerprint": contract[
            "preregistration_fingerprint"
        ],
        "selected_candidate": candidate,
        "selected_symbol": candidate.get("symbol", ""),
        "terminal_evidence": terminal_summary,
        "bounded_probe_envelope": _probe_envelope(),
        "strategy_gate_results": normalized_gates,
        "capability_results": normalized_capabilities,
        "blockers": unique_blockers,
        "admission_valid_until": (
            _capability_admission_expiry(normalized_capabilities).isoformat()
            if ready
            else ""
        ),
        "review_fingerprint": "",
        "admission_fingerprint": "",
        "approval_state": "not_authorized",
        "validation_scope": "structural_integrity_only",
        "authorization_requires_source_replay": True,
        "authorization_clock_source": "trusted_current_utc_required",
        "operator_review_required": True,
        "separate_exact_operator_authorization_required": True,
        "next_action": next_action,
        "profit_claim": "none",
    }
    for field_name in _REVIEW_AUTHORITY_FIELDS:
        packet[field_name] = False
    review_fingerprint = _review_packet_fingerprint(packet)
    packet["review_fingerprint"] = review_fingerprint
    packet["admission_fingerprint"] = review_fingerprint if ready else ""
    validate_crypto_tournament_v2_bounded_paper_probe_review_packet(
        packet,
        as_of=as_of,
    )
    return packet


def validate_crypto_tournament_v2_bounded_paper_probe_review_packet(
    value: Mapping[str, object],
    *,
    as_of: datetime | str,
) -> dict[str, object]:
    """Validate structural integrity and expiry, not trading authorization."""

    packet = dict(_mapping(value, "review_packet"))
    evaluated_at = _utc_datetime(as_of, "as_of")
    expected_keys = {
        "schema_version",
        "record_type",
        "as_of",
        "classification",
        "preregistration_fingerprint",
        "selected_candidate",
        "selected_symbol",
        "terminal_evidence",
        "bounded_probe_envelope",
        "strategy_gate_results",
        "capability_results",
        "blockers",
        "admission_valid_until",
        "review_fingerprint",
        "admission_fingerprint",
        "approval_state",
        "validation_scope",
        "authorization_requires_source_replay",
        "authorization_clock_source",
        "operator_review_required",
        "separate_exact_operator_authorization_required",
        "next_action",
        "profit_claim",
        *_REVIEW_AUTHORITY_FIELDS,
    }
    if set(packet) != expected_keys:
        raise ValidationError("bounded paper-probe review packet keys drifted.")
    if (
        packet.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_REVIEW_SCHEMA_VERSION
        or packet.get("record_type")
        != "crypto_tournament_v2_bounded_paper_probe_review_packet"
        or packet.get("preregistration_fingerprint")
        != CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        or packet.get("bounded_probe_envelope") != _probe_envelope()
        or packet.get("approval_state") != "not_authorized"
        or packet.get("validation_scope") != "structural_integrity_only"
        or packet.get("authorization_requires_source_replay") is not True
        or packet.get("authorization_clock_source")
        != "trusted_current_utc_required"
        or packet.get("operator_review_required") is not True
        or packet.get("separate_exact_operator_authorization_required") is not True
        or packet.get("profit_claim") != "none"
    ):
        raise ValidationError("bounded paper-probe review identity mismatch.")
    packet_as_of = _utc_datetime(packet.get("as_of"), "review_packet.as_of")
    if packet_as_of > evaluated_at:
        raise ValidationError("bounded paper-probe review is future-dated.")
    for field_name in _REVIEW_AUTHORITY_FIELDS:
        if packet.get(field_name) is not False:
            raise ValidationError(
                f"bounded paper-probe review authority must be false: {field_name}."
            )
    candidate = _mapping(packet.get("selected_candidate"), "selected_candidate")
    if packet.get("selected_symbol") != candidate.get("symbol", ""):
        raise ValidationError("bounded paper-probe selected symbol drifted.")
    fingerprint = _required_sha256(
        packet.get("review_fingerprint"), "review_fingerprint"
    )
    if _review_packet_fingerprint(packet) != fingerprint:
        raise ValidationError("bounded paper-probe review fingerprint mismatch.")
    classification = _required_text(packet.get("classification"), "classification")
    next_actions = {
        "waiting_for_v5_25_terminal_evidence": (
            "continue_v5_25_forward_shadow_accrual"
        ),
        "closed_by_terminal_shadow_input_quality_gate": (
            "do_not_extend_retune_or_activate_paper_probe"
        ),
        "rejected_by_preregistered_strategy_gates": (
            "close_activation_without_probe_or_rescue_tuning"
        ),
        "blocked_by_operational_evidence": (
            "produce_missing_selected_symbol_operational_evidence"
        ),
        "eligible_for_operator_review_only": (
            "request_separate_exact_bounded_paper_probe_authorization_review"
        ),
    }
    if packet.get("next_action") != next_actions.get(classification):
        raise ValidationError("bounded paper-probe classification drifted.")
    ready = classification == "eligible_for_operator_review_only"
    admission = packet.get("admission_fingerprint")
    expiry_text = packet.get("admission_valid_until")
    if ready:
        if admission != fingerprint:
            raise ValidationError("eligible review admission fingerprint mismatch.")
        expiry = _utc_datetime(expiry_text, "admission_valid_until")
        capabilities = _mapping(packet.get("capability_results"), "capabilities")
        if set(capabilities) != set(_CAPABILITY_KINDS) or any(
            _mapping(capabilities[kind], kind).get("status") != "satisfied"
            for kind in _CAPABILITY_KINDS
        ):
            raise ValidationError("eligible review capabilities are incomplete.")
        gates = _mapping_sequence(packet.get("strategy_gate_results"), "gates")
        if not gates or any(item.get("passed") is not True for item in gates):
            raise ValidationError("eligible review strategy gates are incomplete.")
        if _string_sequence(packet.get("blockers")):
            raise ValidationError("eligible review cannot contain blockers.")
        if expiry != _capability_admission_expiry(capabilities):
            raise ValidationError("eligible review admission expiry drifted.")
        if evaluated_at > expiry:
            raise ValidationError("eligible review admission evidence has expired.")
    elif admission != "" or expiry_text != "":
        raise ValidationError("ineligible review cannot carry admission identity.")
    return packet


def _review_packet_fingerprint(packet: Mapping[str, object]) -> str:
    identity = dict(packet)
    identity.pop("as_of", None)
    identity.pop("review_fingerprint", None)
    identity.pop("admission_fingerprint", None)
    return _stable_hash(identity)


def _capability_admission_expiry(
    capabilities: Mapping[str, Mapping[str, object]],
) -> datetime:
    expiries: list[datetime] = []
    for kind in _CAPABILITY_KINDS:
        result = _mapping(capabilities.get(kind), kind)
        observed = _utc_datetime(result.get("observed_at"), f"{kind}.observed_at")
        declared = _utc_datetime(result.get("valid_until"), f"{kind}.valid_until")
        expiries.append(
            min(
                declared,
                observed + timedelta(hours=_CAPABILITY_MAX_AGE_HOURS[kind]),
            )
        )
    return min(expiries)


def _validate_terminal_evidence(
    value: Mapping[str, object],
    as_of: datetime,
) -> dict[str, object]:
    source = dict(_mapping(value, "terminal_evidence"))
    if set(source) != _TERMINAL_EVIDENCE_KEYS:
        raise ValidationError("terminal evidence export keys drifted.")
    fingerprint = _required_sha256(
        source.get("evidence_export_fingerprint"),
        "evidence_export_fingerprint",
    )
    identity = dict(source)
    identity.pop("as_of", None)
    identity.pop("evidence_export_fingerprint", None)
    if _stable_hash(identity) != fingerprint:
        raise ValidationError("terminal evidence export fingerprint mismatch.")
    if (
        source.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_TERMINAL_EVIDENCE_SCHEMA_VERSION
        or source.get("record_type")
        != "crypto_tournament_v2_forward_shadow_terminal_evidence"
    ):
        raise ValidationError("terminal evidence export schema mismatch.")
    source_as_of = _utc_datetime(source.get("as_of"), "terminal_evidence.as_of")
    if source_as_of > as_of:
        raise ValidationError("terminal evidence export is later than review as_of.")
    classification = _required_text(
        source.get("classification"), "terminal_evidence.classification"
    )
    if classification not in {
        _ELIGIBLE_SOURCE_CLASSIFICATION,
        _QUALITY_SOURCE_CLASSIFICATION,
    }:
        raise ValidationError("terminal evidence classification is unsupported.")
    expected_eligible = classification == _ELIGIBLE_SOURCE_CLASSIFICATION
    if source.get("review_eligible_source") is not expected_eligible:
        raise ValidationError("terminal evidence eligibility binding mismatch.")
    if source.get("terminal_scoring_performed") is not expected_eligible:
        raise ValidationError("terminal evidence scoring binding mismatch.")
    symbol = _required_text(source.get("selected_symbol"), "selected_symbol")
    candidate = _mapping(source.get("selected_candidate"), "selected_candidate")
    if symbol not in _SUPPORTED_SYMBOLS or candidate.get("symbol") != symbol:
        raise ValidationError("terminal evidence selected symbol is invalid.")
    frozen_candidates = _mapping_sequence(
        build_crypto_tournament_v2_preregistration().get("candidates"),
        "frozen_v2_candidates",
    )
    if not any(dict(candidate) == dict(item) for item in frozen_candidates):
        raise ValidationError(
            "terminal evidence candidate does not match the frozen v2 manifest."
        )
    source_binding = _mapping(source.get("source_binding"), "source_binding")
    if set(source_binding) != _TERMINAL_SOURCE_BINDING_KEYS:
        raise ValidationError("terminal evidence source-binding keys drifted.")
    if source_binding.get("preregistration_fingerprint") != (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT
    ):
        raise ValidationError("terminal evidence preregistration mismatch.")
    if (
        source_binding.get("state_schema_version")
        != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION
        or source_binding.get("packet_schema_version")
        != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION
    ):
        raise ValidationError("terminal evidence source schema mismatch.")
    for field_name in (
        "activation_fingerprint",
        "activation_source_state_fingerprint",
        "state_fingerprint",
        "context_sha256",
        "terminal_packet_sha256",
        "terminal_evidence_fingerprint",
    ):
        _required_sha256(source_binding.get(field_name), field_name)
    terminal_closed_at = _utc_datetime(
        source_binding.get("terminal_closed_at"),
        "source_binding.terminal_closed_at",
    )
    artifact_hashes = _mapping(
        source_binding.get("artifact_sha256"), "artifact_sha256"
    )
    if set(artifact_hashes) != _TERMINAL_ARTIFACT_NAMES:
        raise ValidationError("terminal evidence artifact manifest drifted.")
    for name, digest in artifact_hashes.items():
        if not isinstance(name, str) or not name:
            raise ValidationError("terminal artifact name is invalid.")
        _required_sha256(digest, f"artifact_sha256.{name}")
    window = _mapping(source.get("shadow_window"), "shadow_window")
    if (
        set(window)
        != {"start", "end_exclusive", "hourly_bars", "checkpoint_hours"}
        or window.get("hourly_bars") != FORWARD_SHADOW_HOURLY_BARS
        or window.get("checkpoint_hours")
        != list(FORWARD_SHADOW_CHECKPOINT_HOURS)
    ):
        raise ValidationError("terminal evidence window contract mismatch.")
    window_start = _utc_datetime(window.get("start"), "shadow_window.start")
    window_end = _utc_datetime(
        window.get("end_exclusive"), "shadow_window.end_exclusive"
    )
    if (
        window_end - window_start
        != timedelta(hours=FORWARD_SHADOW_HOURLY_BARS)
        or not (window_end <= terminal_closed_at <= source_as_of <= as_of)
    ):
        raise ValidationError("terminal evidence timestamp ordering mismatch.")
    progress = _mapping(source.get("progress"), "progress")
    if set(progress) != {
        "activation_warmup_expected_rows",
        "activation_warmup_raw_rows",
        "shadow_expected_rows",
        "shadow_raw_rows",
        "shadow_normalized_rows",
        "decision_log_rows",
        "completed_checkpoint_hours",
    }:
        raise ValidationError("terminal evidence progress keys drifted.")
    for field_name in (
        "activation_warmup_expected_rows",
        "activation_warmup_raw_rows",
        "shadow_raw_rows",
        "shadow_normalized_rows",
        "decision_log_rows",
    ):
        if _required_int(progress.get(field_name), field_name) < 0:
            raise ValidationError(f"{field_name} cannot be negative.")
    completed = progress.get("completed_checkpoint_hours")
    checkpoint_prefixes = [
        list(FORWARD_SHADOW_CHECKPOINT_HOURS[:index])
        for index in range(len(FORWARD_SHADOW_CHECKPOINT_HOURS) + 1)
    ]
    if (
        progress.get("shadow_expected_rows") != FORWARD_SHADOW_HOURLY_BARS
        or completed not in checkpoint_prefixes
    ):
        raise ValidationError("terminal evidence progress contract mismatch.")
    quality = _mapping(
        source.get("terminal_input_quality"), "terminal_input_quality"
    )
    if set(quality) != {"activation_warmup", "shadow", "errors"}:
        raise ValidationError("terminal input-quality keys drifted.")
    warmup_quality = _validate_quality_block(
        quality.get("activation_warmup"),
        phase="activation_warmup",
        symbol=symbol,
    )
    shadow_quality = _validate_quality_block(
        quality.get("shadow"),
        phase="shadow",
        symbol=symbol,
    )
    if (
        shadow_quality["start"] != window_start
        or shadow_quality["end_exclusive"] != window_end
        or warmup_quality["end_exclusive"] != window_start
    ):
        raise ValidationError("terminal input-quality window binding mismatch.")
    if (
        warmup_quality["expected_rows"]
        != progress.get("activation_warmup_expected_rows")
        or warmup_quality["observed_rows"]
        != progress.get("activation_warmup_raw_rows")
        or shadow_quality["expected_rows"]
        != progress.get("shadow_expected_rows")
        or shadow_quality["observed_rows"]
        != progress.get("shadow_raw_rows")
    ):
        raise ValidationError(
            "terminal input-quality counts do not match progress."
        )
    errors = _string_sequence(quality.get("errors"))
    if expected_eligible:
        if (
            errors
            or warmup_quality["status"] != "passed"
            or shadow_quality["status"] != "passed"
            or warmup_quality["expected_rows"]
            != warmup_quality["observed_rows"]
            or shadow_quality["expected_rows"]
            != shadow_quality["observed_rows"]
            or warmup_quality["missing_timestamps"]
            or shadow_quality["missing_timestamps"]
            or warmup_quality["maximum_gap"] != 0
            or shadow_quality["maximum_gap"] != 0
            or warmup_quality["imputed_rows"] != 0
            or shadow_quality["imputed_rows"] != 0
            or completed != list(FORWARD_SHADOW_CHECKPOINT_HOURS)
            or progress.get("shadow_raw_rows") != FORWARD_SHADOW_HOURLY_BARS
            or progress.get("shadow_normalized_rows")
            != FORWARD_SHADOW_HOURLY_BARS
            or progress.get("decision_log_rows")
            != FORWARD_SHADOW_HOURLY_BARS
        ):
            raise ValidationError(
                "eligible terminal evidence is incomplete or quality-gated."
            )
    elif not errors:
        raise ValidationError(
            "input-quality terminal evidence must identify its gate."
        )
    safety = _mapping(source.get("safety"), "safety")
    if set(safety) != _TERMINAL_SAFETY_KEYS:
        raise ValidationError("terminal evidence safety keys drifted.")
    for field_name in _SOURCE_SAFETY_FALSE_FIELDS:
        if safety.get(field_name) is not False:
            raise ValidationError(
                f"terminal evidence safety field must be false: {field_name}."
            )
    if safety.get("profit_claim") != "none":
        raise ValidationError("terminal evidence profit claim must be none.")
    for field_name in (
        "source_network_access_attempted",
        "source_market_data_fetch_occurred",
    ):
        if not isinstance(safety.get(field_name), bool):
            raise ValidationError(
                f"terminal evidence safety field must be boolean: {field_name}."
            )
    if expected_eligible:
        _validate_terminal_metric_structure(source)
    else:
        if _mapping(source.get("terminal_metrics"), "terminal_metrics"):
            raise ValidationError(
                "input-quality source cannot expose terminal strategy metrics."
            )
    return source


def _validate_quality_block(
    value: object,
    *,
    phase: str,
    symbol: str,
) -> dict[str, object]:
    quality = _mapping(value, f"terminal_input_quality.{phase}")
    base_keys = {
        "phase",
        "status",
        "start",
        "end_exclusive",
        "expected_raw_rows",
        "observed_raw_rows",
        "raw_coverage",
        "positive_raw_volume_fraction",
        "missing_timestamps",
        "maximum_consecutive_missing_hours",
        "imputed_rows",
    }
    normalized_keys = {*base_keys, "symbol", "isolated_gap_fill"}
    quality_keys = frozenset(quality)
    if quality_keys not in {frozenset(base_keys), frozenset(normalized_keys)}:
        raise ValidationError(f"terminal {phase} quality keys drifted.")
    status = _required_text(quality.get("status"), f"{phase}.status")
    if (
        quality.get("phase") != phase
        or status not in {"passed", "failed"}
    ):
        raise ValidationError(f"terminal {phase} quality identity mismatch.")
    if quality_keys == frozenset(normalized_keys) and (
        quality.get("symbol") != symbol
        or quality.get("isolated_gap_fill")
        != "prior_close_ohlc_zero_volume"
    ):
        raise ValidationError(f"terminal {phase} quality identity mismatch.")
    start = _utc_datetime(quality.get("start"), f"{phase}.start")
    end = _utc_datetime(quality.get("end_exclusive"), f"{phase}.end_exclusive")
    expected_rows = _required_int(
        quality.get("expected_raw_rows"), f"{phase}.expected_raw_rows"
    )
    observed_rows = _required_int(
        quality.get("observed_raw_rows"), f"{phase}.observed_raw_rows"
    )
    missing = _string_sequence(quality.get("missing_timestamps"))
    maximum_gap = _required_int(
        quality.get("maximum_consecutive_missing_hours"),
        f"{phase}.maximum_consecutive_missing_hours",
    )
    imputed = _required_int(quality.get("imputed_rows"), f"{phase}.imputed_rows")
    coverage = _canonical_decimal(quality.get("raw_coverage"), f"{phase}.raw_coverage")
    positive_fraction = _canonical_decimal(
        quality.get("positive_raw_volume_fraction"),
        f"{phase}.positive_raw_volume_fraction",
    )
    missing_datetimes = tuple(
        _utc_datetime(timestamp, f"{phase}.missing_timestamps")
        for timestamp in missing
    )
    expected_coverage = (
        _quantized(Decimal(observed_rows) / Decimal(expected_rows))
        if expected_rows
        else _ZERO
    )
    missing_set = set(missing_datetimes)
    expected_grid = {
        start + timedelta(hours=index) for index in range(expected_rows)
    }
    computed_maximum_gap = 0
    running_gap = 0
    for timestamp in sorted(expected_grid):
        if timestamp in missing_set:
            running_gap += 1
            computed_maximum_gap = max(computed_maximum_gap, running_gap)
        else:
            running_gap = 0
    if (
        end < start
        or expected_rows != int((end - start).total_seconds() // 3600)
        or not 0 <= observed_rows <= expected_rows
        or len(missing) != expected_rows - observed_rows
        or len(missing_set) != len(missing)
        or not missing_set <= expected_grid
        or maximum_gap < 0
        or maximum_gap != computed_maximum_gap
        or not 0 <= imputed <= len(missing)
        or not _ZERO <= coverage <= _ONE
        or coverage != expected_coverage
        or not _ZERO <= positive_fraction <= _ONE
    ):
        raise ValidationError(f"terminal {phase} quality values are invalid.")
    minimum_coverage = (
        _ONE
        if phase == "activation_warmup"
        else Decimal(str(MINIMUM_RAW_HOURLY_COVERAGE))
    )
    allowed_gap = (
        0
        if phase == "activation_warmup"
        else MAXIMUM_CONSECUTIVE_MISSING_HOURS
    )
    quality_failed = expected_rows > 0 and (
        coverage < minimum_coverage
        or positive_fraction
        < Decimal(str(MINIMUM_POSITIVE_RAW_VOLUME_FRACTION))
        or maximum_gap > allowed_gap
        or start in missing_set
        or end - timedelta(hours=1) in missing_set
    )
    expected_status = "failed" if quality_failed else "passed"
    if status != expected_status:
        raise ValidationError(f"terminal {phase} quality status is inconsistent.")
    return {
        "status": status,
        "start": start,
        "end_exclusive": end,
        "expected_rows": expected_rows,
        "observed_rows": observed_rows,
        "missing_timestamps": missing_datetimes,
        "maximum_gap": maximum_gap,
        "imputed_rows": imputed,
    }


def _validate_terminal_metric_structure(source: Mapping[str, object]) -> None:
    metrics = _mapping(source.get("terminal_metrics"), "terminal_metrics")
    if set(metrics) != _TERMINAL_METRIC_KEYS:
        raise ValidationError("terminal metric keys do not match the contract.")
    window = _mapping(source.get("shadow_window"), "shadow_window")
    start = _required_text(window.get("start"), "shadow_window.start")
    end_exclusive = _utc_datetime(
        window.get("end_exclusive"), "shadow_window.end_exclusive"
    )
    expected_end = (end_exclusive - timedelta(hours=1)).isoformat()
    initial_exposure = _canonical_decimal(
        metrics.get("initial_exposure"), "initial_exposure"
    )
    if initial_exposure not in {_ZERO, _ONE}:
        raise ValidationError("initial_exposure must be zero or one.")
    if _canonical_decimal(metrics.get("cash_total_return"), "cash_total_return") != _ZERO:
        raise ValidationError("cash_total_return must be zero.")
    base = _validated_window_metrics(
        metrics.get("base_metrics"),
        field_name="base_metrics",
        expected_start=start,
        expected_end=expected_end,
        cost_rate=_BASE_COST,
    )
    stress = _validated_window_metrics(
        metrics.get("stress_metrics"),
        field_name="stress_metrics",
        expected_start=start,
        expected_end=expected_end,
        cost_rate=_STRESS_COST,
    )
    if (
        base["transition_count"] != stress["transition_count"]
        or base["completed_round_trips"] != stress["completed_round_trips"]
    ):
        raise ValidationError("base/stress transition accounting drifted.")
    buy_hold = _mapping(
        metrics.get("same_symbol_buy_hold"), "same_symbol_buy_hold"
    )
    if set(buy_hold) != {"gross_total_return", "base_metrics", "stress_metrics"}:
        raise ValidationError("buy-hold metric keys do not match the contract.")
    gross = _canonical_decimal(
        buy_hold.get("gross_total_return"), "buy_hold.gross_total_return"
    )
    buy_base = _validated_window_metrics(
        buy_hold.get("base_metrics"),
        field_name="buy_hold.base_metrics",
        expected_start=start,
        expected_end=expected_end,
        cost_rate=_BASE_COST,
        expected_transitions=1,
        expected_round_trips=0,
    )
    buy_stress = _validated_window_metrics(
        buy_hold.get("stress_metrics"),
        field_name="buy_hold.stress_metrics",
        expected_start=start,
        expected_end=expected_end,
        cost_rate=_STRESS_COST,
        expected_transitions=1,
        expected_round_trips=0,
    )
    expected_buy_base = ((gross + _ONE) * (_ONE - _BASE_COST)) - _ONE
    expected_buy_stress = ((gross + _ONE) * (_ONE - _STRESS_COST)) - _ONE
    if buy_base["total_return"] != _quantized(expected_buy_base):
        raise ValidationError("buy-hold base return is inconsistent with gross.")
    if buy_stress["total_return"] != _quantized(expected_buy_stress):
        raise ValidationError("buy-hold stress return is inconsistent with gross.")
    base_excess = _canonical_decimal(
        metrics.get("base_excess_vs_buy_hold"), "base_excess_vs_buy_hold"
    )
    stress_excess = _canonical_decimal(
        metrics.get("stress_excess_vs_buy_hold"), "stress_excess_vs_buy_hold"
    )
    if base_excess != _quantized(
        base["total_return"] - buy_base["total_return"]
    ):
        raise ValidationError("base excess return is inconsistent.")
    if stress_excess != _quantized(
        stress["total_return"] - buy_stress["total_return"]
    ):
        raise ValidationError("stress excess return is inconsistent.")
    _required_exact_int(
        metrics.get("decision_log_expected_rows"),
        "decision_log_expected_rows",
        expected=FORWARD_SHADOW_HOURLY_BARS,
    )
    _required_exact_int(
        metrics.get("decision_log_observed_rows"),
        "decision_log_observed_rows",
        expected=FORWARD_SHADOW_HOURLY_BARS,
    )
    _required_exact_int(
        metrics.get("decision_log_missing_rows"),
        "decision_log_missing_rows",
        expected=0,
    )
    _required_exact_int(
        metrics.get("decision_log_duplicate_rows"),
        "decision_log_duplicate_rows",
        expected=0,
    )
    for field_name, expected in (
        ("decision_log_complete", True),
        ("no_forced_terminal_liquidation", True),
        ("paper_probe_authorized", False),
        ("live_probe_authorized", False),
    ):
        if metrics.get(field_name) is not expected:
            raise ValidationError(f"terminal metric field mismatch: {field_name}.")


def _validated_window_metrics(
    value: object,
    *,
    field_name: str,
    expected_start: str,
    expected_end: str,
    cost_rate: Decimal,
    expected_transitions: int | None = None,
    expected_round_trips: int | None = None,
) -> dict[str, object]:
    metrics = _mapping(value, field_name)
    if set(metrics) != _WINDOW_METRIC_KEYS:
        raise ValidationError(f"{field_name} keys do not match the contract.")
    if metrics.get("start") != expected_start or metrics.get("end") != expected_end:
        raise ValidationError(f"{field_name} window bounds drifted.")
    _required_exact_int(
        metrics.get("bar_count"),
        f"{field_name}.bar_count",
        expected=FORWARD_SHADOW_HOURLY_BARS,
    )
    total_return = _canonical_decimal(
        metrics.get("total_return"), f"{field_name}.total_return"
    )
    drawdown = _canonical_decimal(
        metrics.get("max_drawdown"), f"{field_name}.max_drawdown"
    )
    transitions = _required_int(
        metrics.get("transition_count"), f"{field_name}.transition_count"
    )
    round_trips = _required_int(
        metrics.get("completed_round_trips"),
        f"{field_name}.completed_round_trips",
    )
    turnover = _canonical_decimal(
        metrics.get("turnover"), f"{field_name}.turnover"
    )
    cost = _canonical_decimal(
        metrics.get("estimated_cost_return"),
        f"{field_name}.estimated_cost_return",
    )
    if total_return <= Decimal("-1"):
        raise ValidationError(f"{field_name}.total_return must exceed -1.")
    if drawdown < _ZERO or drawdown > _ONE:
        raise ValidationError(f"{field_name}.max_drawdown is out of range.")
    if transitions < 0 or transitions > FORWARD_SHADOW_HOURLY_BARS + 1:
        raise ValidationError(f"{field_name}.transition_count is out of range.")
    if round_trips < 0 or round_trips > transitions:
        raise ValidationError(
            f"{field_name}.completed_round_trips is out of range."
        )
    if turnover != Decimal(transitions):
        raise ValidationError(f"{field_name}.turnover is inconsistent.")
    if cost != _quantized(Decimal(transitions) * cost_rate):
        raise ValidationError(f"{field_name}.estimated cost is inconsistent.")
    if expected_transitions is not None and transitions != expected_transitions:
        raise ValidationError(f"{field_name}.transition_count drifted.")
    if expected_round_trips is not None and round_trips != expected_round_trips:
        raise ValidationError(f"{field_name}.completed_round_trips drifted.")
    return {
        "total_return": total_return,
        "max_drawdown": drawdown,
        "transition_count": transitions,
        "completed_round_trips": round_trips,
    }


def _evaluate_strategy_gates(
    source: Mapping[str, object],
    contract: Mapping[str, object],
) -> tuple[tuple[dict[str, object], ...], tuple[str, ...]]:
    metrics = _mapping(source.get("terminal_metrics"), "terminal_metrics")
    gates = _mapping_sequence(contract.get("ordered_strategy_gates"), "gates")
    results: list[dict[str, object]] = []
    failures: list[str] = []
    for gate in gates:
        gate_id = _required_text(gate.get("gate_id"), "gate_id")
        metric_path = _required_text(gate.get("metric"), f"{gate_id}.metric")
        comparison = _required_text(
            gate.get("comparison"), f"{gate_id}.comparison"
        )
        observed = _metric_decimal_at_path(metrics, metric_path)
        threshold = (
            _metric_decimal_at_path(
                metrics,
                _required_text(
                    gate.get("threshold_metric"),
                    f"{gate_id}.threshold_metric",
                ),
            )
            if "threshold_metric" in gate
            else _canonical_decimal(
                gate.get("threshold"), f"{gate_id}.threshold"
            )
        )
        if comparison not in {">", "<="}:
            raise ValidationError(f"unsupported strategy gate: {gate_id}.")
        passed = observed > threshold if comparison == ">" else observed <= threshold
        results.append(
            {
                "gate_id": gate_id,
                "observed": _decimal_text(observed),
                "comparison": comparison,
                "threshold": _decimal_text(threshold),
                "passed": passed,
            }
        )
        if not passed:
            failures.append(gate_id)
    return tuple(results), tuple(failures)


def _metric_decimal_at_path(
    metrics: Mapping[str, object],
    path: str,
) -> Decimal:
    current: object = metrics
    for part in path.split("."):
        current = _mapping(current, path).get(part)
    return _canonical_decimal(current, path)


def _evaluate_capabilities(
    evidence: Mapping[str, Mapping[str, object]],
    artifact_hashes: Mapping[str, str],
    source_evidence: Mapping[str, Mapping[str, object]],
    source_artifact_hashes: Mapping[str, str],
    upstream_evidence: Mapping[
        str, Mapping[str, Mapping[str, object]]
    ],
    upstream_artifact_hashes: Mapping[str, Mapping[str, str]],
    *,
    symbol: str,
    as_of: datetime,
) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for kind in _CAPABILITY_KINDS:
        payload = evidence.get(kind)
        digest = artifact_hashes.get(kind, "")
        source_payload = source_evidence.get(kind)
        source_digest = source_artifact_hashes.get(kind, "")
        if payload is None:
            results[kind] = {
                "status": "missing",
                "artifact_sha256": "",
                "evidence_fingerprint": "",
                "observed_at": "",
                "valid_until": "",
                "bundle_fingerprint": "",
                "source_fingerprint": "",
                "blockers": [f"{kind}_evidence_missing"],
            }
            continue
        try:
            results[kind] = _validate_capability(
                payload,
                digest,
                source_payload,
                source_digest,
                upstream_evidence.get(kind, {}),
                upstream_artifact_hashes.get(kind, {}),
                kind=kind,
                symbol=symbol,
                as_of=as_of,
            )
        except ValidationError:
            results[kind] = {
                "status": "invalid",
                "artifact_sha256": (
                    digest if _is_sha256(digest) else ""
                ),
                "evidence_fingerprint": "",
                "observed_at": "",
                "valid_until": "",
                "bundle_fingerprint": "",
                "source_fingerprint": "",
                "blockers": [f"{kind}_evidence_invalid"],
            }
    if all(
        kind in evidence and results[kind].get("status") == "satisfied"
        for kind in _CAPABILITY_KINDS
    ):
        expected_bundle = _capability_bundle_fingerprint(evidence)
        bundle_values = {
            str(_mapping(evidence[kind], kind).get("bundle_fingerprint", ""))
            for kind in _CAPABILITY_KINDS
        }
        if bundle_values != {expected_bundle}:
            for kind in _CAPABILITY_KINDS:
                result = results[kind]
                result["status"] = "invalid"
                result["blockers"] = ["capability_bundle_incoherent"]
    return results


def _validate_capability(
    payload: Mapping[str, object],
    artifact_sha256: str,
    source_payload: Mapping[str, object] | None,
    source_artifact_sha256: str,
    upstream_evidence: Mapping[str, Mapping[str, object]],
    upstream_artifact_sha256: Mapping[str, str],
    *,
    kind: str,
    symbol: str,
    as_of: datetime,
) -> dict[str, object]:
    evidence = dict(_mapping(payload, f"{kind}_evidence"))
    expected_keys = {
        "schema_version",
        "record_type",
        "evidence_kind",
        "subject",
        "observed_at",
        "valid_until",
        "status",
        "claims",
        "source_digests",
        "producer_version",
        "policy_fingerprint",
        "bundle_fingerprint",
        "authority",
        "profit_claim",
        "evidence_fingerprint",
    }
    if set(evidence) != expected_keys:
        raise ValidationError("capability evidence keys do not match contract.")
    if (
        evidence.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SCHEMA_VERSION
        or evidence.get("record_type") != _CAPABILITY_RECORD_TYPE
        or evidence.get("evidence_kind") != kind
        or evidence.get("status") != "satisfied"
        or evidence.get("producer_version") != _CAPABILITY_PRODUCER_VERSION
        or evidence.get("policy_fingerprint")
        != CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        or evidence.get("profit_claim") != "none"
    ):
        raise ValidationError("capability evidence identity mismatch.")
    digest = _required_sha256(artifact_sha256, "artifact_sha256")
    if digest != hashlib.sha256(_json_artifact_bytes(evidence)).hexdigest():
        raise ValidationError("capability artifact bytes are not bound.")
    _required_sha256(evidence.get("bundle_fingerprint"), "bundle_fingerprint")
    fingerprint = _required_sha256(
        evidence.get("evidence_fingerprint"), "evidence_fingerprint"
    )
    unsigned = dict(evidence)
    unsigned.pop("evidence_fingerprint", None)
    if _stable_hash(unsigned) != fingerprint:
        raise ValidationError("capability evidence fingerprint mismatch.")
    subject = _mapping(evidence.get("subject"), "subject")
    if subject != {
        "asset_class": "crypto",
        "symbol": symbol,
        "environment": "alpaca_paper",
    }:
        raise ValidationError("capability evidence subject mismatch.")
    observed_at = _utc_datetime(evidence.get("observed_at"), "observed_at")
    valid_until = _utc_datetime(evidence.get("valid_until"), "valid_until")
    if (
        observed_at > as_of
        or valid_until < as_of
        or as_of - observed_at
        > timedelta(hours=_CAPABILITY_MAX_AGE_HOURS[kind])
    ):
        raise ValidationError("capability evidence is stale or future-dated.")
    authority = _mapping(evidence.get("authority"), "authority")
    if authority != {
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
    }:
        raise ValidationError("capability evidence grants authority.")
    source_digests = _mapping_sequence(
        evidence.get("source_digests"), "source_digests"
    )
    if len(source_digests) != 1:
        raise ValidationError("capability evidence requires one producer source.")
    source_item = source_digests[0]
    source_digest = _required_sha256(
        source_artifact_sha256, "source_artifact_sha256"
    )
    if source_item != {
        "role": "producer_source",
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION
        ),
        "record_type": _CAPABILITY_SOURCE_RECORD_TYPE,
        "sha256": source_digest,
    }:
        raise ValidationError("capability producer-source digest mismatch.")
    source = _validate_capability_source(
        source_payload,
        source_digest,
        upstream_evidence,
        upstream_artifact_sha256,
        kind=kind,
        evidence=evidence,
    )
    claims = _mapping(evidence.get("claims"), "claims")
    _validate_capability_claims(kind, claims)
    return {
        "status": "satisfied",
        "artifact_sha256": digest,
        "evidence_fingerprint": fingerprint,
        "observed_at": observed_at.isoformat(),
        "valid_until": valid_until.isoformat(),
        "bundle_fingerprint": evidence["bundle_fingerprint"],
        "source_fingerprint": source["source_fingerprint"],
        "blockers": [],
    }


def _validate_capability_claims(
    kind: str,
    claims: Mapping[str, object],
) -> None:
    if kind == "venue_orderability":
        expected_keys = {
            "venue",
            "tradable",
            "orderable",
            "notional_orders_supported",
            "minimum_notional_usd",
            "maximum_notional_supported_usd",
            "paper_endpoint",
            "live_endpoint",
        }
        if set(claims) != expected_keys:
            raise ValidationError("venue capability claim keys drifted.")
        if (
            claims.get("venue") != "alpaca_crypto_paper"
            or claims.get("tradable") is not True
            or claims.get("orderable") is not True
            or claims.get("notional_orders_supported") is not True
            or claims.get("paper_endpoint") is not True
            or claims.get("live_endpoint") is not False
            or not (
                _ZERO
                < _canonical_decimal(
                    claims.get("minimum_notional_usd"),
                    "minimum_notional_usd",
                )
                <= _MAX_NOTIONAL
            )
            or _canonical_decimal(
                claims.get("maximum_notional_supported_usd"),
                "maximum_notional_supported_usd",
            )
            < _MAX_NOTIONAL
        ):
            raise ValidationError("venue capability claims do not satisfy cap.")
        return
    if kind == "bounded_order_policy":
        expected_keys = {
            "policy_version",
            "symbol_allowlisted",
            "sizing_basis",
            "minimum_notional_usd",
            "maximum_notional_usd",
            "time_in_force",
            "long_only",
            "cash_only",
            "leverage_allowed",
            "shorting_allowed",
            "max_positions",
            "max_open_orders",
            "max_entry_orders",
            "max_exit_orders",
            "max_replacements",
        }
        if set(claims) != expected_keys:
            raise ValidationError("order-policy capability claim keys drifted.")
        if (
            claims.get("policy_version")
            != _BOUNDED_ORDER_POLICY_SNAPSHOT_VERSION
            or claims.get("symbol_allowlisted") is not True
            or claims.get("sizing_basis") != "notional"
            or not (
                _ZERO
                < _canonical_decimal(
                    claims.get("minimum_notional_usd"),
                    "minimum_notional_usd",
                )
                <= _MAX_NOTIONAL
            )
            or _canonical_decimal(
                claims.get("maximum_notional_usd"), "maximum_notional_usd"
            )
            != _MAX_NOTIONAL
            or claims.get("time_in_force") != "gtc"
            or claims.get("long_only") is not True
            or claims.get("cash_only") is not True
            or claims.get("leverage_allowed") is not False
            or claims.get("shorting_allowed") is not False
        ):
            raise ValidationError("order-policy capability claims drifted.")
        for field_name, expected in (
            ("max_positions", 1),
            ("max_open_orders", 1),
            ("max_entry_orders", 1),
            ("max_exit_orders", 1),
            ("max_replacements", 0),
        ):
            _required_exact_int(claims.get(field_name), field_name, expected=expected)
        return
    if kind == "lifecycle_flat_reconciliation":
        expected_keys = {
            "mechanics_certified",
            "tested_notional_ceiling_usd",
            "entry_submit_attempts",
            "exit_submit_attempts",
            "cancel_attempts_max_per_order",
            "replacement_attempts",
            "flat_reconciliation_completed",
            "final_position_count",
            "final_open_order_count",
            "broker_ambiguity",
        }
        if set(claims) != expected_keys:
            raise ValidationError("lifecycle capability claim keys drifted.")
        if (
            claims.get("mechanics_certified") is not True
            or _canonical_decimal(
                claims.get("tested_notional_ceiling_usd"),
                "tested_notional_ceiling_usd",
            )
            < _MAX_NOTIONAL
            or claims.get("flat_reconciliation_completed") is not True
            or claims.get("broker_ambiguity") is not False
        ):
            raise ValidationError("lifecycle capability claims drifted.")
        for field_name, expected in (
            ("entry_submit_attempts", 1),
            ("exit_submit_attempts", 1),
            ("replacement_attempts", 0),
            ("flat_reconciliation_completed", True),
            ("final_position_count", 0),
            ("final_open_order_count", 0),
        ):
            if type(expected) is bool:
                if claims.get(field_name) is not expected:
                    raise ValidationError(f"{field_name} drifted.")
            else:
                _required_exact_int(
                    claims.get(field_name), field_name, expected=expected
                )
        cancel_attempts = _required_int(
            claims.get("cancel_attempts_max_per_order"),
            "cancel_attempts_max_per_order",
        )
        if cancel_attempts < 0 or cancel_attempts > 1:
            raise ValidationError("cancel_attempts_max_per_order exceeds one.")
        return
    if kind == "durable_kill_loss_control":
        expected_keys = {
            "durable",
            "default_paused",
            "restart_persists_halt",
            "loss_halt_usd",
            "stale_data_blocks_entry",
            "loss_breach_blocks_entry",
            "unexpected_state_blocks_entry",
            "broker_ambiguity_blocks_entry",
            "expiry_blocks_entry",
            "cancel_exit_path_certified",
            "test_passed",
        }
        if set(claims) != expected_keys:
            raise ValidationError("kill-control capability claim keys drifted.")
        true_fields = expected_keys - {"loss_halt_usd"}
        if any(claims.get(field_name) is not True for field_name in true_fields):
            raise ValidationError("kill-control capability is incomplete.")
        if _canonical_decimal(claims.get("loss_halt_usd"), "loss_halt_usd") != _MAX_LOSS:
            raise ValidationError("kill-control loss halt drifted.")
        return
    raise ValidationError("unsupported capability kind.")


def _validate_capability_source(
    payload: Mapping[str, object] | None,
    artifact_sha256: str,
    upstream_evidence: Mapping[str, Mapping[str, object]],
    upstream_artifact_sha256: Mapping[str, str],
    *,
    kind: str,
    evidence: Mapping[str, object],
) -> dict[str, object]:
    source = dict(_mapping(payload, f"{kind}_producer_source"))
    expected_keys = {
        "schema_version",
        "record_type",
        "evidence_kind",
        "source_role",
        "subject",
        "observed_at",
        "valid_until",
        "claims",
        "upstream_source_digests",
        "producer_version",
        "policy_fingerprint",
        "authority",
        "profit_claim",
        "source_fingerprint",
    }
    if set(source) != expected_keys:
        raise ValidationError("capability producer-source keys drifted.")
    if (
        source.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION
        or source.get("record_type") != _CAPABILITY_SOURCE_RECORD_TYPE
        or source.get("evidence_kind") != kind
        or source.get("source_role") != "producer_source"
        or source.get("producer_version") != _CAPABILITY_PRODUCER_VERSION
        or source.get("policy_fingerprint")
        != CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        or source.get("profit_claim") != "none"
    ):
        raise ValidationError("capability producer-source identity mismatch.")
    digest = _required_sha256(artifact_sha256, "source_artifact_sha256")
    if digest != hashlib.sha256(_json_artifact_bytes(source)).hexdigest():
        raise ValidationError("capability producer-source bytes are not bound.")
    source_fingerprint = _required_sha256(
        source.get("source_fingerprint"), "source_fingerprint"
    )
    unsigned = dict(source)
    unsigned.pop("source_fingerprint", None)
    if _stable_hash(unsigned) != source_fingerprint:
        raise ValidationError("capability producer-source fingerprint mismatch.")
    for field_name in (
        "subject",
        "observed_at",
        "valid_until",
        "claims",
        "producer_version",
        "policy_fingerprint",
        "authority",
        "profit_claim",
    ):
        if source.get(field_name) != evidence.get(field_name):
            raise ValidationError(
                f"capability producer-source field mismatch: {field_name}."
            )
    upstream = _mapping_sequence(
        source.get("upstream_source_digests"), "upstream_source_digests"
    )
    contracts = _CAPABILITY_UPSTREAM_SOURCE_CONTRACTS[kind]
    if len(upstream) != len(contracts):
        raise ValidationError("capability upstream source count mismatch.")
    resolved_upstreams: dict[str, Mapping[str, object]] = {}
    for item, contract in zip(upstream, contracts, strict=True):
        role, schema_version, record_type = contract
        descriptor = {
            "role": role,
            "schema_version": schema_version,
            "record_type": record_type,
        }
        if set(item) != {"role", "schema_version", "record_type", "sha256"}:
            raise ValidationError("capability upstream source keys drifted.")
        if any(item.get(key) != value for key, value in descriptor.items()):
            raise ValidationError("capability upstream source contract mismatch.")
        resolved = _mapping(
            upstream_evidence.get(role), f"upstream_source.{role}"
        )
        resolved_digest = _required_sha256(
            upstream_artifact_sha256.get(role),
            f"upstream_source.{role}.artifact_sha256",
        )
        if (
            item.get("sha256") != resolved_digest
            or resolved_digest
            != hashlib.sha256(_json_artifact_bytes(resolved)).hexdigest()
        ):
            raise ValidationError("capability upstream source bytes mismatch.")
        resolved_upstreams[role] = resolved
    derived_claims, derived_observed_at = _derive_capability_source_claims(
        kind,
        subject=_mapping(source.get("subject"), "source.subject"),
        upstreams=resolved_upstreams,
    )
    if source.get("claims") != derived_claims:
        raise ValidationError("capability claims were not derived from upstreams.")
    if (
        source.get("observed_at") != derived_observed_at.isoformat()
        or source.get("valid_until")
        != (
            derived_observed_at
            + timedelta(hours=_CAPABILITY_MAX_AGE_HOURS[kind])
        ).isoformat()
    ):
        raise ValidationError("capability source freshness was not derived.")
    return source


def _derive_capability_source_claims(
    kind: str,
    *,
    subject: Mapping[str, object],
    upstreams: Mapping[str, Mapping[str, object]],
) -> tuple[dict[str, object], datetime]:
    symbol = _required_text(subject.get("symbol"), "source.subject.symbol")
    expected_subject = {
        "asset_class": "crypto",
        "symbol": symbol,
        "environment": "alpaca_paper",
    }
    if dict(subject) != expected_subject:
        raise ValidationError("capability source subject is invalid.")
    if kind == "venue_orderability":
        metadata = _mapping(
            upstreams.get("orderability_metadata"), "orderability_metadata"
        )
        _validate_normalized_authority_fields(metadata)
        if (
            set(metadata) != _VENUE_NORMALIZED_UPSTREAM_KEYS
            or
            metadata.get("schema_version") != "v5_1_crypto_universe_refresh_v1"
            or metadata.get("asset_class") != "crypto"
            or metadata.get("broker_state_mode") != "alpaca_paper_observed"
        ):
            raise ValidationError("orderability metadata identity mismatch.")
        records = _mapping_sequence(metadata.get("records"), "metadata.records")
        matches = [item for item in records if item.get("symbol") == symbol]
        if len(matches) != 1:
            raise ValidationError("selected-symbol orderability record is missing.")
        record = matches[0]
        minimum = _loose_decimal(record.get("min_notional"), "min_notional")
        minimum_size = _loose_decimal(
            record.get("min_order_size"), "min_order_size"
        )
        minimum_trade_increment = _loose_decimal(
            record.get("min_trade_increment"), "min_trade_increment"
        )
        observed_minimum = _loose_decimal(
            record.get("broker_observed_min_notional"),
            "broker_observed_min_notional",
        )
        observed_minimum_size = _loose_decimal(
            record.get("broker_observed_min_order_size"),
            "broker_observed_min_order_size",
        )
        observed_minimum_trade_increment = _loose_decimal(
            record.get("broker_observed_min_trade_increment"),
            "broker_observed_min_trade_increment",
        )
        alternate_minimum = record.get("min_order_notional")
        price_increment = record.get("price_increment")
        observed_price_increment = record.get(
            "broker_observed_price_increment"
        )
        qty_increment = record.get("qty_increment")
        derived_minimum = record.get("derived_min_order_value")
        if (
            set(record) != _VENUE_NORMALIZED_RECORD_KEYS
            or record.get("asset_class") != "crypto"
            or record.get("source_mode") != "paper_read_only"
            or record.get("broker_state_mode") != "alpaca_paper_observed"
            or record.get("metadata_status") != "metadata_observed"
            or record.get("orderability_status") != "notional_orderable"
            or record.get("orderability_basis")
            != "broker_notional_and_qty_metadata"
            or record.get("status") != "active"
            or record.get("tradable") is not True
            or record.get("metadata_blockers") != []
            or record.get("orderability_blockers") != []
            or not _ZERO < minimum <= _MAX_NOTIONAL
            or minimum_size <= _ZERO
            or minimum_trade_increment <= _ZERO
            or minimum != observed_minimum
            or minimum_size != observed_minimum_size
            or minimum_trade_increment != observed_minimum_trade_increment
            or type(alternate_minimum) is not str
            or (
                bool(alternate_minimum)
                and _loose_decimal(
                    alternate_minimum, "min_order_notional"
                )
                != minimum
            )
            or type(price_increment) is not str
            or type(observed_price_increment) is not str
            or price_increment != observed_price_increment
            or (
                bool(price_increment)
                and _loose_decimal(price_increment, "price_increment")
                <= _ZERO
            )
            or type(qty_increment) is not str
            or (
                bool(qty_increment)
                and _loose_decimal(qty_increment, "qty_increment") <= _ZERO
            )
            or type(derived_minimum) is not str
            or (
                bool(derived_minimum)
                and not _ZERO
                < _loose_decimal(
                    derived_minimum, "derived_min_order_value"
                )
                <= _MAX_NOTIONAL
            )
        ):
            raise ValidationError("selected-symbol orderability is not proven.")
        claims = {
            "venue": "alpaca_crypto_paper",
            "tradable": True,
            "orderable": True,
            "notional_orders_supported": True,
            "minimum_notional_usd": _decimal_text(minimum),
            "maximum_notional_supported_usd": _decimal_text(_MAX_NOTIONAL),
            "paper_endpoint": True,
            "live_endpoint": False,
        }
        observed = _utc_datetime(metadata.get("as_of"), "metadata.as_of")
    elif kind == "bounded_order_policy":
        snapshot = _mapping(
            upstreams.get("canonical_order_policy_snapshot"), "policy_snapshot"
        )
        _validate_normalized_upstream(
            snapshot,
            schema_version=_BOUNDED_ORDER_POLICY_SNAPSHOT_VERSION,
            record_type="crypto_bounded_order_policy_snapshot",
            subject=expected_subject,
        )
        claims = dict(_mapping(snapshot.get("claims"), "policy_snapshot.claims"))
        _validate_capability_claims(kind, claims)
        _required_sha256(snapshot.get("source_code_sha256"), "source_code_sha256")
        observed = _utc_datetime(snapshot.get("as_of"), "policy_snapshot.as_of")
    elif kind == "lifecycle_flat_reconciliation":
        mechanics = _mapping(
            upstreams.get("lifecycle_mechanics_certification"),
            "lifecycle_mechanics_certification",
        )
        reconciliation = _mapping(
            upstreams.get("independent_flat_reconciliation"),
            "independent_flat_reconciliation",
        )
        _validate_normalized_upstream(
            mechanics,
            schema_version="v5_26_crypto_lifecycle_mechanics_certification_v1",
            record_type="crypto_lifecycle_mechanics_certification_result",
            subject=expected_subject,
        )
        _validate_normalized_upstream(
            reconciliation,
            schema_version="v5_26_crypto_independent_flat_reconciliation_v1",
            record_type="crypto_independent_flat_reconciliation_result",
            subject=expected_subject,
        )
        mechanics_account_binding = _mapping(
            mechanics.get("account_binding"),
            "mechanics.account_binding",
        )
        reconciliation_account_binding = _mapping(
            reconciliation.get("account_binding"),
            "reconciliation.account_binding",
        )
        validate_alpaca_paper_account_binding(mechanics_account_binding)
        validate_alpaca_paper_account_binding(reconciliation_account_binding)
        if (
            mechanics_account_binding != reconciliation_account_binding
            or mechanics.get("mechanics_certified") is not True
            or mechanics.get("paper_only") is not True
            or mechanics.get("live_endpoint_touched") is not False
            or mechanics.get("broker_ambiguity") is not False
            or reconciliation.get("read_only_reconciliation") is not True
            or reconciliation.get("fresh") is not True
            or reconciliation.get("mutation_occurred") is not False
            or reconciliation.get("live_endpoint_touched") is not False
        ):
            raise ValidationError("lifecycle upstream evidence is incomplete.")
        claims = {
            "mechanics_certified": True,
            "tested_notional_ceiling_usd": _decimal_text(
                _loose_decimal(
                    mechanics.get("tested_notional_ceiling_usd"),
                    "tested_notional_ceiling_usd",
                )
            ),
            "entry_submit_attempts": mechanics.get("entry_submit_attempts"),
            "exit_submit_attempts": mechanics.get("exit_submit_attempts"),
            "cancel_attempts_max_per_order": mechanics.get(
                "cancel_attempts_max_per_order"
            ),
            "replacement_attempts": mechanics.get("replacement_attempts"),
            "flat_reconciliation_completed": True,
            "final_position_count": reconciliation.get("final_position_count"),
            "final_open_order_count": reconciliation.get("final_open_order_count"),
            "broker_ambiguity": reconciliation.get("broker_ambiguity"),
        }
        _validate_capability_claims(kind, claims)
        mechanics_observed = _utc_datetime(
            mechanics.get("as_of"), "mechanics.as_of"
        )
        last_broker_mutation = _utc_datetime(
            mechanics.get("last_broker_mutation_at"),
            "mechanics.last_broker_mutation_at",
        )
        reconciliation_observed = _utc_datetime(
            reconciliation.get("as_of"), "reconciliation.as_of"
        )
        if (
            last_broker_mutation < mechanics_observed
            or reconciliation_observed < last_broker_mutation
        ):
            raise ValidationError(
                "independent flat reconciliation predates the final broker "
                "mutation."
            )
        observed = min(mechanics_observed, reconciliation_observed)
    elif kind == "durable_kill_loss_control":
        certification = _mapping(
            upstreams.get("durable_kill_loss_certification"),
            "durable_kill_loss_certification",
        )
        _validate_normalized_upstream(
            certification,
            schema_version="v5_26_crypto_durable_kill_loss_certification_v1",
            record_type="crypto_durable_kill_loss_certification_result",
            subject=expected_subject,
        )
        claims = dict(
            _mapping(certification.get("claims"), "kill_certification.claims")
        )
        _validate_capability_claims(kind, claims)
        _required_sha256(
            certification.get("offline_test_receipt_sha256"),
            "offline_test_receipt_sha256",
        )
        observed = _utc_datetime(certification.get("as_of"), "kill.as_of")
    else:  # pragma: no cover - callers iterate the frozen kind tuple
        raise ValidationError("unsupported capability kind.")
    return claims, observed


def _validate_normalized_upstream(
    value: Mapping[str, object],
    *,
    schema_version: str,
    record_type: str,
    subject: Mapping[str, object],
) -> None:
    expected_keys = _NORMALIZED_UPSTREAM_KEYS_BY_RECORD_TYPE.get(record_type)
    if expected_keys is None or set(value) != expected_keys:
        raise ValidationError("normalized capability upstream identity mismatch.")
    _validate_normalized_authority_fields(value)
    forbidden_authority_fields = {
        "network_access_authorized",
        "broker_read_authorized",
        "broker_mutation_authorized",
        "broker_mutation_occurred",
        "paper_probe_authorized",
        "paper_mutation_authorized",
        "paper_mutation_occurred",
        "paper_submit_authorized",
        "paper_submit_occurred",
        "paper_cancel_occurred",
        "paper_replace_occurred",
        "paper_close_occurred",
        "paper_liquidate_occurred",
        "capital_allocation_authorized",
        "live_authorized",
        "live_endpoint_touched_override",
        "submit_allowed",
        "paper_mutation_allowed",
    }
    if (
        forbidden_authority_fields.intersection(value)
        or value.get("schema_version") != schema_version
        or value.get("record_type") != record_type
        or value.get("subject") != subject
        or value.get("profit_claim") != "none"
        or value.get("authority")
        != {
            "paper_submit_authorized": False,
            "broker_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_authorized": False,
        }
    ):
        raise ValidationError("normalized capability upstream identity mismatch.")


_NORMALIZED_AUTHORITY_PATH_EXPECTATIONS = {
    ("authority", "paper_submit_authorized"): False,
    ("authority", "broker_mutation_authorized"): False,
    ("authority", "capital_allocation_authorized"): False,
    ("authority", "live_authorized"): False,
    ("claims", "leverage_allowed"): False,
    ("claims", "shorting_allowed"): False,
    ("broker_read_occurred",): True,
    ("account_read_occurred",): True,
    ("positions_read_occurred",): True,
    ("open_orders_read_occurred",): True,
    ("mutation_occurred",): False,
    ("live_endpoint_touched",): False,
}
_NORMALIZED_AUTHORITY_CONTAINER_PATHS = frozenset({("authority",)})
_VENUE_NORMALIZED_UPSTREAM_KEYS = frozenset(
    {
        "schema_version", "record_type", "as_of", "asset_class",
        "broker_state_mode", "records", "resolved_source_sha256",
        "resolved_source_digests",
    }
)
_VENUE_NORMALIZED_RECORD_KEYS = frozenset(
    {
        "symbol", "asset_class", "source_mode", "broker_state_mode",
        "tradable", "status", "min_notional", "min_order_notional",
        "min_order_size", "min_trade_increment", "price_increment",
        "qty_increment", "broker_observed_min_notional",
        "broker_observed_min_order_size",
        "broker_observed_min_trade_increment",
        "broker_observed_price_increment", "derived_min_order_value",
        "orderability_basis", "metadata_status", "metadata_blockers",
        "orderability_status", "orderability_blockers",
    }
)
_NORMALIZED_UPSTREAM_KEYS_BY_RECORD_TYPE = {
    "crypto_bounded_order_policy_snapshot": frozenset(
        {
            "schema_version", "record_type", "as_of", "subject", "claims",
            "source_code_sha256", "resolved_source_digests", "authority",
            "profit_claim",
        }
    ),
    "crypto_lifecycle_mechanics_certification_result": frozenset(
        {
            "schema_version", "record_type", "as_of",
            "last_broker_mutation_at", "subject",
            "mechanics_certified", "tested_notional_ceiling_usd",
            "entry_submit_attempts", "exit_submit_attempts",
            "cancel_attempts_max_per_order", "replacement_attempts",
            "broker_ambiguity", "account_binding", "paper_only",
            "live_endpoint_touched", "resolved_source_digests",
            "provenance_classification", "authority", "profit_claim",
        }
    ),
    "crypto_independent_flat_reconciliation_result": frozenset(
        {
            "schema_version", "record_type", "as_of", "subject",
            "account_binding", "read_only_reconciliation",
            "broker_read_occurred", "account_read_occurred",
            "positions_read_occurred", "open_orders_read_occurred", "fresh",
            "final_position_count", "final_open_order_count",
            "observed_position_symbols", "observed_open_order_symbols",
            "broker_ambiguity", "mutation_occurred", "live_endpoint_touched",
            "resolved_source_sha256", "validator_source_sha256", "authority",
            "profit_claim",
        }
    ),
    "crypto_durable_kill_loss_certification_result": frozenset(
        {
            "schema_version", "record_type", "as_of", "subject", "claims",
            "offline_test_receipt_sha256", "resolved_source_digests",
            "authority", "profit_claim",
        }
    ),
}


def _validate_normalized_authority_fields(
    value: Mapping[str, object],
) -> None:
    """Reject authority-shaped fields outside the exact normalized contract."""

    def walk(item: object, path: tuple[str, ...]) -> None:
        if isinstance(item, Mapping):
            for field_name, child in item.items():
                if not isinstance(field_name, str):
                    raise ValidationError(
                        "normalized capability upstream key is not text."
                    )
                child_path = (*path, field_name)
                lowered = field_name.lower()
                authority_shaped = (
                    "authorit" in lowered
                    or "permit" in lowered
                    or "credential" in lowered
                    or lowered.endswith("_allowed")
                    or lowered.endswith("_occurred")
                    or lowered.endswith("_performed")
                    or lowered.endswith("_attempted")
                    or lowered.endswith("_touched")
                )
                if authority_shaped:
                    expected_path = child_path[-2:] if path else child_path
                    if child_path in _NORMALIZED_AUTHORITY_CONTAINER_PATHS:
                        if not isinstance(child, Mapping):
                            raise ValidationError(
                                "normalized authority container is invalid."
                            )
                    elif expected_path in _NORMALIZED_AUTHORITY_PATH_EXPECTATIONS:
                        expected = _NORMALIZED_AUTHORITY_PATH_EXPECTATIONS[
                            expected_path
                        ]
                        if type(child) is not bool or child is not expected:
                            raise ValidationError(
                                "normalized authority field has unsafe value."
                            )
                    else:
                        raise ValidationError(
                            "unexpected normalized authority-shaped field."
                        )
                walk(child, child_path)
        elif isinstance(item, Sequence) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            for child in item:
                walk(child, (*path, "[]"))

    walk(value, ())


def _loose_decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not str or not value:
        raise ValidationError(f"{field_name} must be a decimal string.")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} is not a decimal.") from exc
    if not parsed.is_finite() or abs(parsed) > Decimal("1000000000"):
        raise ValidationError(f"{field_name} is outside the accepted range.")
    return parsed


def _capability_bundle_fingerprint(
    evidence: Mapping[str, Mapping[str, object]],
) -> str:
    basis: dict[str, object] = {}
    for kind in _CAPABILITY_KINDS:
        item = dict(_mapping(evidence.get(kind), kind))
        item.pop("evidence_fingerprint", None)
        item.pop("bundle_fingerprint", None)
        basis[kind] = item
    return _stable_hash(basis)


def _missing_capability_results(
    *,
    status: str = "not_evaluated_before_strategy_pass",
) -> dict[str, dict[str, object]]:
    return {
        kind: {
            "status": status,
            "artifact_sha256": "",
            "evidence_fingerprint": "",
            "observed_at": "",
            "valid_until": "",
            "bundle_fingerprint": "",
            "source_fingerprint": "",
            "blockers": [],
        }
        for kind in _CAPABILITY_KINDS
    }


def _load_capability_artifacts(
    root: Path,
) -> tuple[
    dict[str, Mapping[str, object]],
    dict[str, str],
    dict[str, Mapping[str, object]],
    dict[str, str],
    dict[str, dict[str, Mapping[str, object]]],
    dict[str, dict[str, str]],
    dict[str, bytes],
]:
    from algotrader.orchestration import (
        crypto_tournament_v2_bounded_paper_probe_capability_producer as capability_producer,
    )

    evidence: dict[str, Mapping[str, object]] = {}
    hashes: dict[str, str] = {}
    sources: dict[str, Mapping[str, object]] = {}
    source_hashes: dict[str, str] = {}
    upstreams: dict[str, dict[str, Mapping[str, object]]] = {}
    upstream_hashes: dict[str, dict[str, str]] = {}
    support_artifacts: dict[str, bytes] = {}
    capability_producer._assert_safe_tree_path(
        root,
        root,
        must_exist=root.exists(),
    )
    latest_path = root / "latest_manifest.json"
    flat_layout_candidates = tuple(
        candidate
        for kind in _CAPABILITY_KINDS
        for candidate in (
            root / f"{kind}.json",
            root / "sources" / kind,
        )
    )
    flat_layout_present = False
    for candidate in flat_layout_candidates:
        if candidate.exists() or candidate.is_symlink():
            capability_producer._assert_safe_tree_path(
                root,
                candidate,
                must_exist=True,
            )
            flat_layout_present = True
    if latest_path.exists() or latest_path.is_symlink():
        if flat_layout_present:
            raise ValidationError(
                "mixed flat and immutable capability layouts are ambiguous."
            )
        capability_producer._assert_safe_tree_path(
            root,
            latest_path,
            must_exist=True,
        )
        latest_bytes = capability_producer._read_regular_bytes(
            latest_path,
            "capability_production_latest_pointer",
        )
        latest = capability_producer._json_mapping(
            latest_bytes,
            "capability_production_latest_pointer",
        )
        capability_producer._require_canonical_json(
            latest_bytes,
            latest,
            "capability_production_latest_pointer",
        )
        pointer = dict(latest)
        pointer_fingerprint = _required_sha256(
            pointer.pop("pointer_fingerprint", ""),
            "capability_pointer_fingerprint",
        )
        publication_fingerprint = _required_sha256(
            latest.get("publication_fingerprint"),
            "capability_publication_fingerprint",
        )
        expected_relative = f"generations/{publication_fingerprint}"
        if (
            set(latest) != capability_producer._LATEST_POINTER_KEYS
            or pointer_fingerprint != _stable_hash(pointer)
            or latest.get("schema_version")
            != capability_producer.CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
            or latest.get("record_type")
            != "crypto_bounded_probe_capability_latest_pointer"
            or latest.get("generation_relative_path") != expected_relative
            or latest.get("broker_mutation_authorized") is not False
            or latest.get("paper_mutation_authorized") is not False
            or latest.get("capital_allocation_authorized") is not False
            or latest.get("live_authorized") is not False
        ):
            raise ValidationError(
                "capability production latest pointer binding failed."
            )
        loaded = (
            capability_producer.load_crypto_tournament_v2_bounded_paper_probe_capability_generation(
                root,
                expected_publication_fingerprint=publication_fingerprint,
            )
        )
        if (
            latest.get("status_fingerprint")
            != loaded.status.get("status_fingerprint")
            or latest.get("classification")
            != loaded.status.get("classification")
            or latest.get("as_of") != loaded.status.get("as_of")
        ):
            raise ValidationError(
                "capability latest pointer status binding failed."
            )
        generation_manifest_path = (
            root
            / "generations"
            / publication_fingerprint
            / "generation_manifest.json"
        )
        capability_producer._assert_safe_tree_path(
            root,
            generation_manifest_path,
            must_exist=True,
        )
        generation_manifest_bytes = capability_producer._read_regular_bytes(
            generation_manifest_path,
            "capability_generation_manifest",
        )
        if hashlib.sha256(generation_manifest_bytes).hexdigest() != (
            latest.get("generation_manifest_sha256")
        ):
            raise ValidationError(
                "capability generation manifest pointer hash mismatch."
            )
        support_artifacts["latest_manifest.json"] = latest_bytes
        support_artifacts[
            f"{expected_relative}/generation_manifest.json"
        ] = generation_manifest_bytes
        for name, payload in loaded.artifacts.items():
            support_artifacts[f"{expected_relative}/{name}"] = payload
        if loaded.status.get("capability_bundle_emitted") is not True:
            return (
                evidence,
                hashes,
                sources,
                source_hashes,
                upstreams,
                upstream_hashes,
                support_artifacts,
            )
        for kind in _CAPABILITY_KINDS:
            capability_name = f"bundle/{kind}.json"
            source_name = f"bundle/sources/{kind}/producer_source.json"
            capability_bytes = loaded.artifacts.get(capability_name)
            source_bytes = loaded.artifacts.get(source_name)
            if capability_bytes is None or source_bytes is None:
                raise ValidationError(
                    "complete capability generation bundle is incomplete."
                )
            capability = capability_producer._json_mapping(
                capability_bytes,
                capability_name,
            )
            capability_producer._require_canonical_json(
                capability_bytes,
                capability,
                capability_name,
            )
            evidence[kind] = capability
            hashes[kind] = hashlib.sha256(capability_bytes).hexdigest()
            source = capability_producer._json_mapping(source_bytes, source_name)
            capability_producer._require_canonical_json(
                source_bytes,
                source,
                source_name,
            )
            sources[kind] = source
            source_hashes[kind] = hashlib.sha256(source_bytes).hexdigest()
            kind_upstreams: dict[str, Mapping[str, object]] = {}
            kind_hashes: dict[str, str] = {}
            for role, _, _ in _CAPABILITY_UPSTREAM_SOURCE_CONTRACTS[kind]:
                upstream_name = (
                    f"bundle/sources/{kind}/upstream/{role}.json"
                )
                upstream_bytes = loaded.artifacts.get(upstream_name)
                if upstream_bytes is None:
                    raise ValidationError(
                        "complete capability generation upstream is absent."
                    )
                upstream = capability_producer._json_mapping(
                    upstream_bytes,
                    upstream_name,
                )
                capability_producer._require_canonical_json(
                    upstream_bytes,
                    upstream,
                    upstream_name,
                )
                kind_upstreams[role] = upstream
                kind_hashes[role] = hashlib.sha256(upstream_bytes).hexdigest()
            upstreams[kind] = kind_upstreams
            upstream_hashes[kind] = kind_hashes
        return (
            evidence,
            hashes,
            sources,
            source_hashes,
            upstreams,
            upstream_hashes,
            support_artifacts,
        )
    for kind in _CAPABILITY_KINDS:
        path = root / f"{kind}.json"
        if not path.is_file():
            continue
        payload = path.read_bytes()
        hashes[kind] = hashlib.sha256(payload).hexdigest()
        try:
            parsed = capability_producer._json_mapping(payload, str(path))
            capability_producer._require_canonical_json(
                payload,
                parsed,
                str(path),
            )
        except ValidationError:
            evidence[kind] = {"invalid_artifact": True}
            continue
        evidence[kind] = parsed
        source_path = root / "sources" / kind / "producer_source.json"
        if not source_path.is_file():
            continue
        source_bytes = source_path.read_bytes()
        source_hashes[kind] = hashlib.sha256(source_bytes).hexdigest()
        try:
            source_parsed = capability_producer._json_mapping(
                source_bytes,
                str(source_path),
            )
            capability_producer._require_canonical_json(
                source_bytes,
                source_parsed,
                str(source_path),
            )
        except ValidationError:
            sources[kind] = {"invalid_artifact": True}
            continue
        sources[kind] = source_parsed
        kind_upstreams: dict[str, Mapping[str, object]] = {}
        kind_hashes: dict[str, str] = {}
        for role, _, _ in _CAPABILITY_UPSTREAM_SOURCE_CONTRACTS[kind]:
            upstream_path = (
                root / "sources" / kind / "upstream" / f"{role}.json"
            )
            if not upstream_path.is_file():
                continue
            upstream_bytes = upstream_path.read_bytes()
            kind_hashes[role] = hashlib.sha256(upstream_bytes).hexdigest()
            try:
                upstream_parsed = capability_producer._json_mapping(
                    upstream_bytes,
                    str(upstream_path),
                )
                capability_producer._require_canonical_json(
                    upstream_bytes,
                    upstream_parsed,
                    str(upstream_path),
                )
            except ValidationError:
                kind_upstreams[role] = {"invalid_artifact": True}
                continue
            kind_upstreams[role] = upstream_parsed
        upstreams[kind] = kind_upstreams
        upstream_hashes[kind] = kind_hashes
    return (
        evidence,
        hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
        support_artifacts,
    )


def _probe_envelope() -> dict[str, object]:
    return {
        "environment": "alpaca_crypto_paper",
        "asset_class": "crypto",
        "symbol_scope": "exact_selected_symbol_only",
        "direction": "long_or_cash",
        "maximum_notional_usd": _decimal_text(_MAX_NOTIONAL),
        "maximum_principal_at_risk_usd": _decimal_text(_MAX_NOTIONAL),
        "loss_halt_usd": _decimal_text(_MAX_LOSS),
        "loss_halt_fraction_of_cap": _decimal_text(
            _MAX_LOSS / _MAX_NOTIONAL
        ),
        "maximum_concurrent_positions": 1,
        "maximum_open_orders": 1,
        "maximum_entry_orders": 1,
        "maximum_exit_orders": 1,
        "maximum_cancel_attempts_per_order": 1,
        "maximum_replacements": 0,
        "maximum_duration_hours": 168,
        "leverage_allowed": False,
        "margin_allowed": False,
        "shorting_allowed": False,
        "pyramiding_allowed": False,
        "cross_symbol_exposure_allowed": False,
        "stop_execution_guarantees_realized_loss_cap": False,
    }


def _canonical_decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not str or not value:
        raise ValidationError(f"{field_name} must be a canonical decimal string.")
    try:
        parsed = Decimal(value)
        canonical = _decimal_text(parsed)
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise ValidationError(f"{field_name} is not a decimal.") from exc
    if (
        not parsed.is_finite()
        or abs(parsed) > Decimal("1000000000")
        or value != canonical
    ):
        raise ValidationError(f"{field_name} is not canonically encoded.")
    return parsed


def _quantized(value: Decimal) -> Decimal:
    return value.quantize(_DECIMAL_QUANTUM)


def _decimal_text(value: Decimal) -> str:
    if value == _ZERO:
        return "0"
    return format(_quantized(value), "f").rstrip("0").rstrip(".")


def _required_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    return value


def _required_exact_int(
    value: object,
    field_name: str,
    *,
    expected: int,
) -> int:
    result = _required_int(value, field_name)
    if result != expected:
        raise ValidationError(f"{field_name} must equal {expected}.")
    return result


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
    return tuple(_mapping(item, field_name) for item in value)


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be non-empty text.")
    return value.strip()


def _required_sha256(value: object, field_name: str) -> str:
    text = _required_text(value, field_name).lower()
    if not _is_sha256(text):
        raise ValidationError(f"{field_name} must be a SHA-256 digest.")
    return text


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _utc_datetime(value: datetime | str | object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str) and value.strip():
        try:
            result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO-8601.") from exc
    else:
        raise ValidationError(f"{field_name} must be a UTC timestamp.")
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValidationError(f"{field_name} must include UTC offset.")
    try:
        return result.astimezone(UTC)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f"{field_name} is outside the UTC range.") from exc


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
    _write_text_atomic(path, _json_artifact_bytes(payload).decode("utf-8"))


def _json_artifact_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _publish_review_artifacts(
    root: Path,
    *,
    preregistration: Mapping[str, object],
    packet: Mapping[str, object],
    markdown: str,
    terminal_evidence: Mapping[str, object] | None,
    capability_evidence: Mapping[str, Mapping[str, object]],
    capability_source_evidence: Mapping[str, Mapping[str, object]],
    capability_upstream_evidence: Mapping[
        str, Mapping[str, Mapping[str, object]]
    ],
    capability_support_artifacts: Mapping[str, bytes],
) -> dict[str, object]:
    from algotrader.orchestration import (
        crypto_tournament_v2_bounded_paper_probe_capability_producer as capability_producer,
    )

    capability_producer._assert_safe_tree_path(root, root, must_exist=False)
    root.mkdir(parents=True, exist_ok=True)
    capability_producer._assert_safe_tree_path(root, root, must_exist=True)
    with _exclusive_review_lock(root):
        preregistration_bytes = _json_artifact_bytes(preregistration)
        packet_bytes = _json_artifact_bytes(packet)
        markdown_bytes = markdown.encode("utf-8")
        artifacts = {
            "preregistration.json": preregistration_bytes,
            "review_packet.json": packet_bytes,
            "review_packet.md": markdown_bytes,
        }
        if terminal_evidence is not None:
            artifacts["inputs/terminal_evidence.json"] = _json_artifact_bytes(
                terminal_evidence
            )
        for kind, payload in capability_evidence.items():
            artifacts[f"inputs/capabilities/{kind}.json"] = (
                _json_artifact_bytes(payload)
            )
        for kind, payload in capability_source_evidence.items():
            artifacts[f"inputs/producer_sources/{kind}.json"] = (
                _json_artifact_bytes(payload)
            )
        for kind, items in capability_upstream_evidence.items():
            for role, payload in items.items():
                artifacts[f"inputs/upstreams/{kind}/{role}.json"] = (
                    _json_artifact_bytes(payload)
                )
        for raw_name, payload in capability_support_artifacts.items():
            name = str(raw_name)
            parts = name.split("/")
            if (
                not name
                or "\\" in name
                or name.startswith(("/", "//"))
                or any(part in {"", ".", ".."} for part in parts)
                or ":" in parts[0]
                or not isinstance(payload, bytes)
                or not payload
            ):
                raise ValidationError(
                    "capability support artifact path or bytes are invalid."
                )
            destination = f"inputs/capability_production/{name}"
            if destination in artifacts:
                raise ValidationError(
                    "capability support artifact destination conflicts."
                )
            artifacts[destination] = payload
        artifact_manifest = {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in artifacts.items()
        }
        publication_fingerprint = _stable_hash(artifact_manifest)
        generation = root / "generations" / publication_fingerprint
        for name, payload in artifacts.items():
            safe_name = capability_producer._safe_relative_name(name)
            destination = generation / safe_name
            capability_producer._assert_safe_tree_path(
                root,
                destination,
                must_exist=False,
            )
            _write_immutable_bytes(destination, payload)
        generation_manifest: dict[str, object] = {
            "schema_version": (
                CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_REVIEW_SCHEMA_VERSION
            ),
            "record_type": (
                "crypto_tournament_v2_bounded_paper_probe_review_generation"
            ),
            "publication_fingerprint": publication_fingerprint,
            "review_fingerprint": packet["review_fingerprint"],
            "admission_fingerprint": packet["admission_fingerprint"],
            "as_of": packet["as_of"],
            "artifact_sha256": artifact_manifest,
            "broker_mutation_authorized": False,
            "paper_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_authorized": False,
        }
        generation_manifest_path = generation / "generation_manifest.json"
        capability_producer._assert_safe_tree_path(
            root,
            generation_manifest_path,
            must_exist=False,
        )
        _write_immutable_bytes(
            generation_manifest_path,
            _json_artifact_bytes(generation_manifest),
        )
        latest_basis: dict[str, object] = {
            "schema_version": (
                CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_REVIEW_SCHEMA_VERSION
            ),
            "record_type": (
                "crypto_tournament_v2_bounded_paper_probe_review_latest_pointer"
            ),
            "publication_fingerprint": publication_fingerprint,
            "generation_relative_path": (
                f"generations/{publication_fingerprint}"
            ),
            "generation_manifest_sha256": hashlib.sha256(
                _json_artifact_bytes(generation_manifest)
            ).hexdigest(),
            "review_fingerprint": packet["review_fingerprint"],
            "admission_fingerprint": packet["admission_fingerprint"],
            "as_of": packet["as_of"],
            "broker_mutation_authorized": False,
            "paper_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_authorized": False,
        }
        latest = {
            **latest_basis,
            "pointer_fingerprint": _stable_hash(latest_basis),
        }
        if set(latest) != _REVIEW_LATEST_POINTER_KEYS:
            raise ValidationError("review latest pointer schema drifted.")
        capability_producer._assert_safe_tree_path(
            root,
            root / "latest_manifest.json",
            must_exist=False,
        )
        _write_json_atomic(root / "latest_manifest.json", latest)
        return latest


def _write_immutable_bytes(path: Path, payload: bytes) -> None:
    from algotrader.orchestration import (
        crypto_tournament_v2_bounded_paper_probe_capability_producer as capability_producer,
    )

    if capability_producer._is_link_or_reparse(path):
        raise ValidationError("immutable review artifact uses a link.")
    if path.is_file():
        if path.read_bytes() != payload:
            raise ValidationError(
                f"immutable review artifact conflicts: {path.name}."
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists() or temporary.is_symlink():
        if capability_producer._is_link_or_reparse(temporary):
            raise ValidationError("review temporary path uses a link.")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def _exclusive_review_lock(root: Path) -> Iterator[None]:
    from algotrader.orchestration import (
        crypto_tournament_v2_bounded_paper_probe_capability_producer as capability_producer,
    )

    lock_path = root / ".bounded_paper_probe_review.lock"
    capability_producer._assert_safe_tree_path(
        root,
        lock_path,
        must_exist=False,
    )
    stream = lock_path.open("a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        _lock_stream(stream)
    except OSError as exc:
        stream.close()
        raise ValidationError(
            "another bounded-paper-probe review publication is active."
        ) from exc
    try:
        yield
    finally:
        try:
            stream.seek(0)
            _unlock_stream(stream)
        finally:
            stream.close()


def _lock_stream(stream: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl  # pragma: no cover - exercised on non-Windows hosts

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_stream(stream: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl  # pragma: no cover - exercised on non-Windows hosts

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shadow-root",
        default=str(CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--capability-root",
        default=str(
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_CAPABILITY_ROOT
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument("--as-of", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packet = run_crypto_tournament_v2_bounded_paper_probe_review(
        shadow_root=args.shadow_root,
        capability_root=args.capability_root,
        output_root=args.output_root,
        as_of=args.as_of or datetime.now(UTC).isoformat(),
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
