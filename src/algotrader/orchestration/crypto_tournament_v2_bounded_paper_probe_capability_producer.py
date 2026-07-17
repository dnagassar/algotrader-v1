"""Candidate-deferred, source-bound capability production for tournament v2.

This module reads only local artifacts.  It does not import an execution
adapter, contact a broker or network, expose credentials, construct an order,
or grant paper/live authority.  Capability emission is all-or-nothing and can
begin only after frozen V5.25 terminal evidence names the exact winner.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterator

from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
    validate_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError
from algotrader.orchestration.crypto_paper_certification_ingestion import (
    DISALLOWED_ACTIONS as V59_DISALLOWED_ACTIONS,
    REQUIRED_LABELS as V59_REQUIRED_LABELS,
)
from algotrader.orchestration.crypto_tournament_v2_bounded_paper_probe_review import (
    CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SCHEMA_VERSION,
    CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION,
    CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_CAPABILITY_ROOT,
    CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT,
    build_crypto_tournament_v2_bounded_paper_probe_review,
)
from algotrader.research.crypto_tournament_v2_forward_shadow_state import (
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT,
    export_crypto_tournament_v2_forward_shadow_terminal_evidence,
    run_crypto_tournament_v2_forward_shadow_state,
)


CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION = (
    "v5_27_crypto_tournament_v2_bounded_paper_probe_capability_production_v1"
)
CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT = (
    CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_DEFAULT_CAPABILITY_ROOT
)

_CAPABILITY_RECORD_TYPE = (
    "crypto_tournament_v2_bounded_paper_probe_capability_evidence"
)
_CAPABILITY_SOURCE_RECORD_TYPE = (
    "crypto_tournament_v2_bounded_paper_probe_capability_source"
)
_CAPABILITY_PRODUCER_VERSION = (
    "v5_26_crypto_tournament_v2_bounded_paper_probe_capability_producer_v1"
)
_POLICY_SNAPSHOT_VERSION = "v5_26_crypto_bounded_order_policy_snapshot_v1"
_SAFETY_POLICY_FINGERPRINT = (
    "c0abbc047f7bdf01f19d46e06d3824acd980016b4bd992d78dd4994db6d2c407"
)
_SAFETY_CERTIFICATION_SCHEMA = (
    "v5_27_crypto_bounded_probe_safety_certification_receipt_v1"
)
_FLAT_OBSERVATION_SCHEMA = (
    "v5_27_crypto_bounded_probe_independent_flat_observation_v1"
)
_SUPPORTED_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD")
_V510_REQUIRED_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
    "bounded_btcusd_paper_fill_exit_certification",
    "one_entry_attempt_only",
    "one_exit_attempt_only",
    "btcusd_only",
    "not_live",
    "operator_authorized_v5_10",
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
_UPSTREAM_CONTRACTS = {
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
            _POLICY_SNAPSHOT_VERSION,
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
_INPUT_ARTIFACT_PATHS = {
    "venue_refresh_manifest": "resolved_sources/venue/manifest.json",
    "venue_universe": "resolved_sources/venue/crypto_universe.json",
    "orderability_metadata": (
        "resolved_sources/venue/crypto_orderability_metadata.json"
    ),
    "venue_router_input_manifest": (
        "resolved_sources/venue/crypto_router_input_manifest.json"
    ),
    "venue_runtime_visibility_status": (
        "resolved_sources/venue/runtime_visibility_status.json"
    ),
    "venue_refresh_source": (
        "resolved_sources/venue/crypto_universe_refresh.py"
    ),
    "venue_visibility_operator_source": (
        "resolved_sources/venue/crypto_paper_visibility_operator.py"
    ),
    "venue_supervisor_source": (
        "resolved_sources/venue/crypto_paper_supervisor.py"
    ),
    "submit_cancel_receipt": (
        "resolved_sources/lifecycle/v5_8_submit_cancel_result.json"
    ),
    "submit_cancel_manifest": (
        "resolved_sources/lifecycle/v5_8_manifest.json"
    ),
    "submit_approval_packet": (
        "resolved_sources/lifecycle/v5_7_submit_approval_packet.json"
    ),
    "paper_oms_dry_run": (
        "resolved_sources/lifecycle/v5_6_paper_oms_dry_run.json"
    ),
    "paper_submit_cancel_source": (
        "resolved_sources/lifecycle/"
        "crypto_paper_submit_cancel_certification.py"
    ),
    "paper_submit_approval_source": (
        "resolved_sources/lifecycle/crypto_paper_submit_approval_packet.py"
    ),
    "paper_oms_dry_run_source": (
        "resolved_sources/lifecycle/crypto_paper_oms_dry_run.py"
    ),
    "fill_exit_receipt": (
        "resolved_sources/lifecycle/v5_10_fill_exit_result.json"
    ),
    "fill_exit_manifest": (
        "resolved_sources/lifecycle/v5_10_manifest.json"
    ),
    "fill_approval_packet": (
        "resolved_sources/lifecycle/v5_9_fill_approval_packet.json"
    ),
    "fill_approval_manifest": (
        "resolved_sources/lifecycle/v5_9_manifest.json"
    ),
    "paper_fill_exit_source": (
        "resolved_sources/lifecycle/crypto_paper_fill_exit_certification.py"
    ),
    "paper_certification_ingestion_source": (
        "resolved_sources/lifecycle/crypto_paper_certification_ingestion.py"
    ),
    "independent_flat_reconciliation": (
        "resolved_sources/lifecycle/independent_flat_reconciliation.json"
    ),
    "independent_flat_reconciliation_source": (
        "resolved_sources/lifecycle/"
        "crypto_bounded_probe_independent_flat_reconciliation.py"
    ),
    "account_binding_source": (
        "resolved_sources/lifecycle/paper_account_binding.py"
    ),
    "capability_producer_source": (
        "resolved_sources/producer/"
        "crypto_tournament_v2_bounded_paper_probe_capability_producer.py"
    ),
    "safety_kernel_source": (
        "resolved_sources/safety/crypto_bounded_probe_safety.py"
    ),
    "safety_certifier_source": (
        "resolved_sources/safety/crypto_bounded_probe_safety_certification.py"
    ),
    "safety_focused_test_source": (
        "resolved_sources/safety/test_crypto_bounded_probe_safety.py"
    ),
    "safety_certification_receipt": (
        "resolved_sources/safety/safety_certification_receipt.json"
    ),
}
_LOCAL_SOURCE_PATHS = {
    "capability_producer_source": Path(__file__).resolve(),
    "account_binding_source": (
        Path(__file__).resolve().parents[1]
        / "core"
        / "paper_account_binding.py"
    ),
    "independent_flat_reconciliation_source": (
        Path(__file__).resolve().parents[1]
        / "execution"
        / "crypto_bounded_probe_independent_flat_reconciliation.py"
    ),
    "venue_refresh_source": (
        Path(__file__).resolve().parent / "crypto_universe_refresh.py"
    ),
    "venue_visibility_operator_source": (
        Path(__file__).resolve().parents[1]
        / "execution"
        / "crypto_paper_visibility_operator.py"
    ),
    "venue_supervisor_source": (
        Path(__file__).resolve().parents[1]
        / "execution"
        / "crypto_paper_supervisor.py"
    ),
    "paper_submit_cancel_source": (
        Path(__file__).resolve().parents[1]
        / "execution"
        / "crypto_paper_submit_cancel_certification.py"
    ),
    "paper_submit_approval_source": (
        Path(__file__).resolve().parent
        / "crypto_paper_submit_approval_packet.py"
    ),
    "paper_oms_dry_run_source": (
        Path(__file__).resolve().parent / "crypto_paper_oms_dry_run.py"
    ),
    "paper_fill_exit_source": (
        Path(__file__).resolve().parents[1]
        / "execution"
        / "crypto_paper_fill_exit_certification.py"
    ),
    "paper_certification_ingestion_source": (
        Path(__file__).resolve().parent
        / "crypto_paper_certification_ingestion.py"
    ),
    "safety_kernel_source": (
        Path(__file__).resolve().parents[1]
        / "execution"
        / "crypto_bounded_probe_safety.py"
    ),
    "safety_certifier_source": (
        Path(__file__).resolve().parents[1]
        / "execution"
        / "crypto_bounded_probe_safety_certification.py"
    ),
    "safety_focused_test_source": (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "unit"
        / "test_crypto_bounded_probe_safety.py"
    ),
}
_LOADED_LOCAL_SOURCE_SHA256 = {
    role: hashlib.sha256(path.read_bytes()).hexdigest()
    for role, path in _LOCAL_SOURCE_PATHS.items()
}
_VENUE_PAPER_READ_LABELS = [
    "paper_lab_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_submit_mode",
    "paper_read_only",
]
_VENUE_MANIFEST_KEYS = {
    "schema_version", "as_of", "artifact_root", "required_artifacts",
    "history_data_files", "paper_submit_authorized",
    "paper_submit_performed", "broker_mutation_performed",
    "live_mutation_performed", "network_access_attempted",
    "generated_under_runs", "labels",
}
_VENUE_REQUIRED_ARTIFACT_ROLES = {
    "crypto_universe", "crypto_orderability_metadata",
    "crypto_history_manifest", "crypto_history_quality_report",
    "crypto_router_input_manifest", "operating_brief", "operating_record",
}
_VENUE_UNIVERSE_KEYS = {
    "schema_version", "as_of", "asset_class", "mode", "source_mode",
    "source_path", "symbol_count", "symbols", "valid_metadata_count",
    "valid_history_count", "eligible_input_symbol_count",
    "eligible_input_symbols", "orderability_status_counts",
    "notional_orderable_metadata_count", "qty_orderable_metadata_count",
    "derived_min_order_value_count", "top_blockers", "broker_state_mode",
    "broker_read_observed", "labels", "paper_submit_authorized",
    "paper_submit_performed", "broker_mutation_performed",
    "live_mutation_performed", "network_access_attempted", "profit_claim",
    "local_artifacts_discovered", "local_artifacts_accepted",
    "local_artifacts_rejected", "local_artifacts_discovered_count",
    "local_artifacts_accepted_count", "local_artifacts_rejected_count",
    "metadata_symbol_count", "history_symbol_count", "metadata_gap_symbols",
}
_VENUE_ORDERABILITY_KEYS = {
    "schema_version", "as_of", "asset_class", "mode", "source_mode",
    "broker_state_mode", "records", "valid_metadata_count",
    "orderable_symbol_count", "orderability_status_counts",
    "notional_orderable_metadata_count", "qty_orderable_metadata_count",
    "top_blockers",
}
_VENUE_ORDERABILITY_RECORD_KEYS = {
    "symbol", "asset_class", "source_mode", "broker_state_mode",
    "tradable", "status", "min_notional", "min_order_notional",
    "min_order_size", "min_trade_increment", "price_increment",
    "qty_increment", "broker_observed_min_notional",
    "broker_observed_min_order_size", "broker_observed_min_trade_increment",
    "broker_observed_price_increment", "derived_min_order_value",
    "orderability_basis", "metadata_status", "metadata_blockers",
    "orderability_status", "orderability_blockers",
}
_VENUE_ROUTER_KEYS = {
    "schema_version", "as_of", "asset_class", "mode", "source_mode",
    "source_path", "broker_state_mode", "broker_read_observed", "symbols",
    "router_ready_symbols", "crypto_universe_path",
    "crypto_orderability_metadata_path", "crypto_history_manifest_path",
    "crypto_history_quality_report_path", "records", "labels",
    "paper_submit_authorized", "paper_submit_performed",
    "broker_mutation_performed", "live_mutation_performed",
    "network_access_attempted", "profit_claim", "local_artifact_discovery",
}
_VENUE_RUNTIME_KEYS = {
    "schema_version", "universe", "asset_class", "run_timestamp",
    "input_data_path", "input_data_sha256", "selected_symbol",
    "latest_bar_at", "data_freshness_status", "freshness_policy",
    "broker_state_mode", "broker_read_performed", "capability_source",
    "crypto_trading_supported", "crypto_capability",
    "eligible_crypto_symbols", "selected_symbol_tradable",
    "selected_symbol_marginable", "selected_symbol_fractionable",
    "min_order_size", "min_trade_increment", "min_order_increment",
    "min_notional", "unsupported_jurisdiction_account_blocker",
    "strategy_id", "strategy_signal", "strategy_posture",
    "strategy_intended_action", "strategy_route_receipt",
    "strategy_adapter_resolution", "strategy_adapter_resolution_status",
    "strategy_adapter_reason", "strategy_adapter_id", "strategy_adapter_mode",
    "strategy_adapter_paper_mutation_allowed", "paper_mutation_allowed",
    "submit_allowed", "action_decision", "no_submit_mode",
    "paper_submit_performed", "broker_mutation_performed",
    "live_mutation_performed", "readiness_status", "blockers",
    "final_operator_action", "safety_labels", "paper_only_mode",
    "live_endpoint_indicator", "operator_command", "operating_mode",
    "operator_preflight", "broker_read_requested", "broker_read_error_type",
    "no_submit_wrapper", "target_symbol", "target_scoped",
}
_VENUE_RUNTIME_CAPABILITY_KEYS = {
    "universe", "asset_class", "broker_read_performed", "broker_state_mode",
    "crypto_trading_supported", "eligible_crypto_symbols", "selected_symbol",
    "selected_symbol_tradable", "selected_symbol_marginable",
    "selected_symbol_fractionable", "min_order_size", "min_trade_increment",
    "min_order_increment", "min_notional", "paper_only_mode",
    "live_endpoint_indicator", "unsupported_jurisdiction_account_blocker",
    "capability_source", "blockers",
}
_CERTIFICATION_CHECKS = (
    "default_pause_blocks_entry",
    "exact_one_to_ten_usd_entry_envelope",
    "cash_margin_and_account_gates",
    "stale_future_and_expired_entry_blocked",
    "ambiguity_and_unexpected_state_blocked",
    "exact_two_usd_loss_latched",
    "maximum_loss_and_halt_survive_restart",
    "later_profit_cannot_reset_halt",
    "halted_expired_cancel_path_admitted_locally",
    "halted_expired_full_exit_path_admitted_locally",
    "entry_attempt_claim_is_atomic",
    "entry_attempt_budget_survives_restart",
    "cancel_attempt_budget_survives_restart",
    "exit_attempt_budget_survives_restart",
    "all_authority_fields_remain_false",
)
_CAPABILITY_AUTHORITY = {
    "paper_submit_authorized": False,
    "broker_mutation_authorized": False,
    "capital_allocation_authorized": False,
    "live_authorized": False,
}
_CERTIFICATION_AUTHORITY = {
    "network_access_occurred": False,
    "broker_read_occurred": False,
    "broker_mutation_authorized": False,
    "broker_mutation_occurred": False,
    "paper_submit_authorized": False,
    "paper_mutation_authorized": False,
    "paper_mutation_occurred": False,
    "capital_allocation_authorized": False,
    "live_authorized": False,
    "live_endpoint_touched": False,
}
_STATUS_FALSE_AUTHORITY = {
    "network_access_authorized": False,
    "network_access_attempted": False,
    "broker_read_authorized": False,
    "broker_read_occurred": False,
    "broker_mutation_authorized": False,
    "broker_mutation_occurred": False,
    "paper_probe_authorized": False,
    "paper_mutation_authorized": False,
    "paper_mutation_occurred": False,
    "paper_submit_authorized": False,
    "paper_submit_occurred": False,
    "paper_cancel_occurred": False,
    "paper_replace_occurred": False,
    "paper_close_occurred": False,
    "paper_liquidate_occurred": False,
    "paper_or_broker_eligible": False,
    "paper_or_live_execution_authorized": False,
    "capital_allocation_authorized": False,
    "live_authorized": False,
    "live_endpoint_touched": False,
    "credential_values_exposed": False,
}
_STATUS_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "as_of",
        "classification",
        "v5_26_preregistration_fingerprint",
        "terminal_binding",
        "source_results",
        "capability_results",
        "capability_bundle_emitted",
        "capability_bundle_fingerprint",
        "review_preview_classification",
        "review_preview_fingerprint",
        "blockers",
        "next_action",
        "profit_claim",
        "status_fingerprint",
    }
    | set(_STATUS_FALSE_AUTHORITY)
)
_GENERATION_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "publication_fingerprint",
        "status_fingerprint",
        "classification",
        "as_of",
        "artifact_sha256",
        "broker_mutation_authorized",
        "paper_mutation_authorized",
        "capital_allocation_authorized",
        "live_authorized",
    }
)
_LATEST_POINTER_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "publication_fingerprint",
        "generation_relative_path",
        "generation_manifest_sha256",
        "status_fingerprint",
        "classification",
        "as_of",
        "broker_mutation_authorized",
        "paper_mutation_authorized",
        "capital_allocation_authorized",
        "live_authorized",
        "pointer_fingerprint",
    }
)

__all__ = [
    "CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION",
    "CryptoBoundedProbeCapabilityProduction",
    "build_crypto_tournament_v2_bounded_paper_probe_capability_production",
    "load_crypto_tournament_v2_bounded_paper_probe_capability_generation",
    "main",
    "run_crypto_tournament_v2_bounded_paper_probe_capability_producer",
]


@dataclass(frozen=True)
class CryptoBoundedProbeCapabilityProduction:
    status: Mapping[str, object]
    artifacts: Mapping[str, bytes]


def build_crypto_tournament_v2_bounded_paper_probe_capability_production(
    terminal_evidence: Mapping[str, object] | None,
    *,
    resolved_input_bytes: Mapping[str, bytes],
    as_of: datetime | str,
) -> CryptoBoundedProbeCapabilityProduction:
    """Build one deterministic production without accepting a symbol input."""

    evaluated_at = _utc_datetime(as_of, "as_of")
    initial_review = build_crypto_tournament_v2_bounded_paper_probe_review(
        terminal_evidence,
        as_of=evaluated_at,
    )
    initial_classification = str(initial_review["classification"])
    artifacts: dict[str, bytes] = {}
    terminal_binding = _terminal_binding(terminal_evidence)

    if initial_classification == "waiting_for_v5_25_terminal_evidence":
        status = _production_status(
            as_of=evaluated_at,
            classification="candidate_deferred_pending_terminal_winner",
            terminal_binding=terminal_binding,
            source_results={},
            capability_results=initial_review["capability_results"],
            bundle_fingerprint="",
            review_preview=initial_review,
            blockers=("v5_25_terminal_winner_not_available",),
            next_action="continue_v5_25_forward_shadow_accrual",
        )
        artifacts["production_status.json"] = _json_bytes(status)
        return CryptoBoundedProbeCapabilityProduction(status, artifacts)

    if initial_classification != "blocked_by_operational_evidence":
        if terminal_evidence is not None:
            artifacts["inputs/terminal_evidence.json"] = _json_bytes(
                dict(terminal_evidence)
            )
        status = _production_status(
            as_of=evaluated_at,
            classification="terminal_closed_without_strategy_eligible_winner",
            terminal_binding=terminal_binding,
            source_results={},
            capability_results=initial_review["capability_results"],
            bundle_fingerprint="",
            review_preview=initial_review,
            blockers=tuple(str(item) for item in initial_review["blockers"]),
            next_action=str(initial_review["next_action"]),
        )
        artifacts["production_status.json"] = _json_bytes(status)
        return CryptoBoundedProbeCapabilityProduction(status, artifacts)

    if terminal_evidence is None:  # pragma: no cover - V5.26 contract enforces
        raise ValidationError("selected winner terminal evidence is absent.")
    symbol = _selected_symbol(terminal_evidence)
    artifacts["inputs/terminal_evidence.json"] = _json_bytes(
        dict(terminal_evidence)
    )
    source_results = _source_results(resolved_input_bytes)
    blockers = [
        f"resolved_source_missing:{role}"
        for role in _INPUT_ARTIFACT_PATHS
        if role not in resolved_input_bytes
        or not isinstance(resolved_input_bytes[role], bytes)
        or not resolved_input_bytes[role]
    ]
    review_preview = initial_review
    capability_results = initial_review["capability_results"]
    bundle_fingerprint = ""
    if not blockers:
        try:
            (
                capabilities,
                capability_hashes,
                sources,
                source_hashes,
                upstreams,
                upstream_hashes,
            ) = _build_complete_bundle(
                resolved_input_bytes,
                symbol=symbol,
                as_of=evaluated_at,
            )
            review_preview = (
                build_crypto_tournament_v2_bounded_paper_probe_review(
                    terminal_evidence,
                    capability_evidence=capabilities,
                    capability_artifact_sha256=capability_hashes,
                    capability_source_evidence=sources,
                    capability_source_artifact_sha256=source_hashes,
                    capability_upstream_evidence=upstreams,
                    capability_upstream_artifact_sha256=upstream_hashes,
                    as_of=evaluated_at,
                )
            )
            capability_results = review_preview["capability_results"]
            if review_preview["classification"] != "eligible_for_operator_review_only":
                blockers.extend(str(item) for item in review_preview["blockers"])
            else:
                bundle_fingerprint = str(
                    capabilities[_CAPABILITY_KINDS[0]]["bundle_fingerprint"]
                )
                for role, relative_path in _INPUT_ARTIFACT_PATHS.items():
                    artifacts[relative_path] = resolved_input_bytes[role]
                for kind in _CAPABILITY_KINDS:
                    artifacts[f"bundle/{kind}.json"] = _json_bytes(
                        capabilities[kind]
                    )
                    artifacts[
                        f"bundle/sources/{kind}/producer_source.json"
                    ] = _json_bytes(sources[kind])
                    for role, payload in upstreams[kind].items():
                        artifacts[
                            f"bundle/sources/{kind}/upstream/{role}.json"
                        ] = _json_bytes(payload)
                artifacts["bundle/review_preview.json"] = _json_bytes(
                    dict(review_preview)
                )
        except ValidationError as exc:
            blockers.append(f"source_normalization_failed:{exc}")

    for kind in _CAPABILITY_KINDS:
        diagnostic = {
            "schema_version": (
                CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
            ),
            "record_type": "crypto_bounded_probe_capability_diagnostic",
            "symbol": symbol,
            "evidence_kind": kind,
            "result": dict(capability_results[kind]),
            "authority": dict(_CAPABILITY_AUTHORITY),
            "profit_claim": "none",
        }
        diagnostic["diagnostic_fingerprint"] = _stable_hash(diagnostic)
        artifacts[f"diagnostics/{symbol}/{kind}.json"] = _json_bytes(diagnostic)

    emitted = bool(bundle_fingerprint) and not blockers
    status = _production_status(
        as_of=evaluated_at,
        classification=(
            "selected_winner_capability_bundle_emitted"
            if emitted
            else "selected_winner_operational_evidence_blocked"
        ),
        terminal_binding=terminal_binding,
        source_results=source_results,
        capability_results=capability_results,
        bundle_fingerprint=bundle_fingerprint if emitted else "",
        review_preview=review_preview,
        blockers=tuple(dict.fromkeys(blockers)),
        next_action=(
            "request_separate_exact_bounded_paper_probe_authorization_review"
            if emitted
            else "produce_missing_selected_symbol_operational_evidence"
        ),
    )
    artifacts["production_status.json"] = _json_bytes(status)
    if not emitted:
        for name in tuple(artifacts):
            if name.startswith("bundle/"):
                del artifacts[name]
    return CryptoBoundedProbeCapabilityProduction(status, artifacts)


def run_crypto_tournament_v2_bounded_paper_probe_capability_producer(
    *,
    shadow_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT
    ),
    venue_orderability_path: Path | str = (
        "runs/crypto_universe_refresh/paper_read_latest/"
        "crypto_orderability_metadata.json"
    ),
    submit_cancel_receipt_path: Path | str = (
        "runs/crypto_paper_submit_cancel_certification/latest/"
        "certification_result.json"
    ),
    fill_exit_receipt_path: Path | str = (
        "runs/crypto_paper_fill_exit_certification/latest/"
        "fill_exit_certification_result.json"
    ),
    independent_flat_reconciliation_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/bounded_paper_probe_capabilities/"
        "independent_flat_reconciliation.json"
    ),
    safety_kernel_source_path: Path | str = (
        "src/algotrader/execution/crypto_bounded_probe_safety.py"
    ),
    safety_certifier_source_path: Path | str = (
        "src/algotrader/execution/"
        "crypto_bounded_probe_safety_certification.py"
    ),
    safety_focused_test_source_path: Path | str = (
        "tests/unit/test_crypto_bounded_probe_safety.py"
    ),
    safety_certification_receipt_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/bounded_paper_probe_capabilities/"
        "safety_certification_receipt.json"
    ),
    as_of: datetime | str,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Inspect local terminal state and publish one immutable production."""

    evaluated_at = _utc_datetime(as_of, "as_of")
    shadow_path = _local_path(shadow_root, "shadow_root")
    output_path = _local_path(output_root, "output_root")
    terminal_evidence: Mapping[str, object] | None = None
    if (shadow_path / "frozen_state.json").is_file():
        state_packet = run_crypto_tournament_v2_forward_shadow_state(
            output_root=shadow_path,
            as_of=evaluated_at,
            write_artifacts=False,
        )
        frozen_state = state_packet.get("frozen_state")
        if (
            isinstance(frozen_state, Mapping)
            and frozen_state.get("terminal_outcome_closed") is True
        ):
            terminal_evidence = (
                export_crypto_tournament_v2_forward_shadow_terminal_evidence(
                    output_root=shadow_path,
                    as_of=evaluated_at,
                )
            )
    preliminary = (
        build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal_evidence,
            resolved_input_bytes={},
            as_of=evaluated_at,
        )
    )
    production = preliminary
    if preliminary.status["classification"] == (
        "selected_winner_operational_evidence_blocked"
    ):
        venue_root = Path(venue_orderability_path).parent
        submit_root = Path(submit_cancel_receipt_path).parent
        fill_root = Path(fill_exit_receipt_path).parent
        input_paths = {
            **_LOCAL_SOURCE_PATHS,
            "venue_refresh_manifest": venue_root / "manifest.json",
            "venue_universe": venue_root / "crypto_universe.json",
            "orderability_metadata": venue_orderability_path,
            "venue_router_input_manifest": (
                venue_root / "crypto_router_input_manifest.json"
            ),
            "venue_runtime_visibility_status": (
                Path("runs/crypto_paper_visibility/latest/latest_status.json")
            ),
            "submit_cancel_receipt": submit_cancel_receipt_path,
            "submit_cancel_manifest": submit_root / "manifest.json",
            "submit_approval_packet": Path(
                "runs/crypto_paper_submit_approval_packet/latest/"
                "paper_submit_approval_packet.json"
            ),
            "paper_oms_dry_run": Path(
                "runs/crypto_paper_oms_dry_run/latest/paper_oms_dry_run.json"
            ),
            "fill_exit_receipt": fill_exit_receipt_path,
            "fill_exit_manifest": fill_root / "manifest.json",
            "fill_approval_packet": Path(
                "runs/crypto_paper_certification_ingestion/latest/"
                "paper_fill_experiment_approval_packet.json"
            ),
            "fill_approval_manifest": Path(
                "runs/crypto_paper_certification_ingestion/latest/manifest.json"
            ),
            "independent_flat_reconciliation": (
                independent_flat_reconciliation_path
            ),
            "safety_kernel_source": safety_kernel_source_path,
            "safety_certifier_source": safety_certifier_source_path,
            "safety_focused_test_source": safety_focused_test_source_path,
            "safety_certification_receipt": (
                safety_certification_receipt_path
            ),
        }
        resolved = {
            role: payload
            for role, path in input_paths.items()
            if (payload := _read_optional_source(path, role)) is not None
        }
        production = (
            build_crypto_tournament_v2_bounded_paper_probe_capability_production(
                terminal_evidence,
                resolved_input_bytes=resolved,
                as_of=evaluated_at,
            )
        )
    if write_artifacts:
        _publish_production(output_path, production)
    return dict(production.status)


def load_crypto_tournament_v2_bounded_paper_probe_capability_generation(
    root: Path | str,
    *,
    expected_publication_fingerprint: str,
) -> CryptoBoundedProbeCapabilityProduction:
    """Load and hash-validate one exact immutable production generation."""

    output_root = _local_path(root, "root")
    fingerprint = _sha256(
        expected_publication_fingerprint,
        "expected_publication_fingerprint",
    )
    generation = output_root / "generations" / fingerprint
    _assert_safe_tree_path(output_root, generation, must_exist=False)
    if not generation.is_dir() or _is_link_or_reparse(generation):
        raise ValidationError("capability production generation is absent.")
    _assert_safe_tree_path(output_root, generation, must_exist=True)
    manifest_path = generation / "generation_manifest.json"
    manifest_bytes = _read_regular_bytes(manifest_path, "generation_manifest")
    manifest = _json_mapping(manifest_bytes, "generation_manifest")
    _require_canonical_json(manifest_bytes, manifest, "generation_manifest")
    if (
        set(manifest) != _GENERATION_MANIFEST_KEYS
        or manifest.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
        or manifest.get("record_type")
        != "crypto_bounded_probe_capability_production_generation"
        or manifest.get("publication_fingerprint") != fingerprint
        or manifest.get("broker_mutation_authorized") is not False
        or manifest.get("paper_mutation_authorized") is not False
        or manifest.get("capital_allocation_authorized") is not False
        or manifest.get("live_authorized") is not False
    ):
        raise ValidationError("capability production manifest identity mismatch.")
    digest_map = manifest.get("artifact_sha256")
    if not isinstance(digest_map, Mapping) or not digest_map:
        raise ValidationError("capability production artifact manifest is empty.")
    artifacts: dict[str, bytes] = {}
    for raw_name, raw_digest in digest_map.items():
        name = _safe_relative_name(raw_name)
        digest = _sha256(raw_digest, f"artifact_sha256.{name}")
        artifact_path = generation / PurePosixPath(name)
        _assert_safe_descendant(generation, artifact_path)
        payload = _read_regular_bytes(artifact_path, name)
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValidationError("capability production artifact hash mismatch.")
        artifacts[name] = payload
    actual_names = _actual_artifact_names(generation)
    if actual_names != set(artifacts):
        raise ValidationError("capability production artifact set drifted.")
    if _stable_hash(dict(digest_map)) != fingerprint:
        raise ValidationError("capability production fingerprint mismatch.")
    status_bytes = artifacts.get("production_status.json")
    if status_bytes is None:
        raise ValidationError("capability production status is absent.")
    status = _json_mapping(status_bytes, "production_status")
    _require_canonical_json(status_bytes, status, "production_status")
    _validate_status(status)
    if (
        manifest.get("status_fingerprint") != status.get("status_fingerprint")
        or manifest.get("classification") != status.get("classification")
        or manifest.get("as_of") != status.get("as_of")
    ):
        raise ValidationError("capability production status binding mismatch.")
    return CryptoBoundedProbeCapabilityProduction(status, artifacts)


def _build_complete_bundle(
    raw: Mapping[str, bytes],
    *,
    symbol: str,
    as_of: datetime,
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, str],
    dict[str, dict[str, object]],
    dict[str, str],
    dict[str, dict[str, dict[str, object]]],
    dict[str, dict[str, str]],
]:
    parsed = {
        role: _json_mapping(raw[role], role)
        for role in (
            "venue_refresh_manifest",
            "venue_universe",
            "orderability_metadata",
            "venue_router_input_manifest",
            "venue_runtime_visibility_status",
            "submit_cancel_receipt",
            "submit_cancel_manifest",
            "submit_approval_packet",
            "paper_oms_dry_run",
            "fill_exit_receipt",
            "fill_exit_manifest",
            "fill_approval_packet",
            "fill_approval_manifest",
            "independent_flat_reconciliation",
            "safety_certification_receipt",
        )
    }
    raw_hashes = {
        role: hashlib.sha256(payload).hexdigest()
        for role, payload in raw.items()
    }
    raw_sizes = {role: len(payload) for role, payload in raw.items()}
    _validate_local_source_bindings(raw, raw_hashes)
    receipt = parsed["safety_certification_receipt"]
    _validate_safety_receipt(receipt, raw, raw_hashes, as_of=as_of)
    subject = {
        "asset_class": "crypto",
        "symbol": symbol,
        "environment": "alpaca_paper",
    }
    venue = _normalize_venue(
        parsed["orderability_metadata"],
        raw_hashes["orderability_metadata"],
        manifest=parsed["venue_refresh_manifest"],
        universe=parsed["venue_universe"],
        router=parsed["venue_router_input_manifest"],
        runtime=parsed["venue_runtime_visibility_status"],
        raw_hashes=raw_hashes,
        symbol=symbol,
        as_of=as_of,
    )
    policy = _normalize_policy(receipt, raw_hashes, subject=subject)
    mechanics = _normalize_lifecycle(
        parsed["submit_cancel_receipt"],
        parsed["fill_exit_receipt"],
        submit_manifest=parsed["submit_cancel_manifest"],
        submit_approval=parsed["submit_approval_packet"],
        dry_run=parsed["paper_oms_dry_run"],
        fill_manifest=parsed["fill_exit_manifest"],
        fill_approval=parsed["fill_approval_packet"],
        fill_approval_manifest=parsed["fill_approval_manifest"],
        raw_hashes=raw_hashes,
        raw_sizes=raw_sizes,
        subject=subject,
        as_of=as_of,
    )
    flat = _normalize_flat(
        parsed["independent_flat_reconciliation"],
        raw_hashes["independent_flat_reconciliation"],
        subject=subject,
        expected_account_binding=_mapping(
            mechanics.get("account_binding"),
            "mechanics.account_binding",
        ),
        not_before=_utc_datetime(
            mechanics.get("last_broker_mutation_at"),
            "mechanics.last_broker_mutation_at",
        ),
        as_of=as_of,
    )
    kill = _normalize_kill(receipt, raw_hashes, subject=subject)
    upstreams = {
        "venue_orderability": {"orderability_metadata": venue},
        "bounded_order_policy": {"canonical_order_policy_snapshot": policy},
        "lifecycle_flat_reconciliation": {
            "lifecycle_mechanics_certification": mechanics,
            "independent_flat_reconciliation": flat,
        },
        "durable_kill_loss_control": {
            "durable_kill_loss_certification": kill
        },
    }
    upstream_hashes = {
        kind: {
            role: hashlib.sha256(_json_bytes(payload)).hexdigest()
            for role, payload in items.items()
        }
        for kind, items in upstreams.items()
    }
    claims = {
        "venue_orderability": _venue_claims(venue, symbol),
        "bounded_order_policy": dict(policy["claims"]),
        "lifecycle_flat_reconciliation": _lifecycle_claims(mechanics, flat),
        "durable_kill_loss_control": dict(kill["claims"]),
    }
    observed = {
        kind: min(
            _utc_datetime(item["as_of"], f"{kind}.as_of")
            for item in items.values()
        )
        for kind, items in upstreams.items()
    }
    sources = {
        kind: _producer_source(
            kind,
            subject=subject,
            claims=claims[kind],
            observed_at=observed[kind],
            upstream_hashes=upstream_hashes[kind],
        )
        for kind in _CAPABILITY_KINDS
    }
    source_hashes = {
        kind: hashlib.sha256(_json_bytes(payload)).hexdigest()
        for kind, payload in sources.items()
    }
    unsigned_evidence = {
        kind: _capability_unsigned(
            kind,
            subject=subject,
            claims=claims[kind],
            observed_at=observed[kind],
            source_sha256=source_hashes[kind],
        )
        for kind in _CAPABILITY_KINDS
    }
    bundle_basis = {
        kind: {
            key: value
            for key, value in payload.items()
            if key != "bundle_fingerprint"
        }
        for kind, payload in unsigned_evidence.items()
    }
    bundle_fingerprint = _stable_hash(bundle_basis)
    capabilities: dict[str, dict[str, object]] = {}
    for kind, payload in unsigned_evidence.items():
        unsigned = {**payload, "bundle_fingerprint": bundle_fingerprint}
        capabilities[kind] = {
            **unsigned,
            "evidence_fingerprint": _stable_hash(unsigned),
        }
    capability_hashes = {
        kind: hashlib.sha256(_json_bytes(payload)).hexdigest()
        for kind, payload in capabilities.items()
    }
    return (
        capabilities,
        capability_hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
    )


def _normalize_venue(
    raw: Mapping[str, object],
    raw_sha256: str,
    *,
    manifest: Mapping[str, object],
    universe: Mapping[str, object],
    router: Mapping[str, object],
    runtime: Mapping[str, object],
    raw_hashes: Mapping[str, str],
    symbol: str,
    as_of: datetime,
) -> dict[str, object]:
    if (
        set(raw) != _VENUE_ORDERABILITY_KEYS
        or raw.get("schema_version") != "v5_1_crypto_universe_refresh_v1"
        or raw.get("asset_class") != "crypto"
        or raw.get("broker_state_mode") != "alpaca_paper_observed"
        or raw.get("mode") != "paper_read_only"
        or raw.get("source_mode") != "paper_read_only"
    ):
        raise ValidationError("venue source identity mismatch")
    observed = _validate_venue_provenance(
        manifest,
        universe,
        raw,
        router,
        runtime,
        raw_hashes,
        symbol=symbol,
        as_of=as_of,
    )
    records = _mapping_sequence(raw.get("records"), "venue.records")
    matches = [dict(item) for item in records if item.get("symbol") == symbol]
    if len(matches) != 1:
        raise ValidationError("selected-symbol venue record is not unique")
    record = matches[0]
    minimum = _decimal(record.get("min_notional"), "min_notional")
    if (
        set(record) != _VENUE_ORDERABILITY_RECORD_KEYS
        or record.get("asset_class") != "crypto"
        or record.get("source_mode") != "paper_read_only"
        or record.get("broker_state_mode") != "alpaca_paper_observed"
        or record.get("metadata_status") != "metadata_observed"
        or record.get("orderability_status") != "notional_orderable"
        or record.get("status") != "active"
        or record.get("tradable") is not True
        or record.get("orderability_basis")
        != "broker_notional_and_qty_metadata"
        or _string_sequence(record.get("metadata_blockers"))
        or _string_sequence(record.get("orderability_blockers"))
        or not Decimal("0") < minimum <= Decimal("10")
        or _decimal(record.get("min_order_size"), "min_order_size") <= 0
        or _decimal(
            record.get("min_trade_increment"),
            "min_trade_increment",
        ) <= 0
    ):
        raise ValidationError("selected-symbol venue orderability is not proven")
    return {
        "schema_version": "v5_1_crypto_universe_refresh_v1",
        "record_type": "crypto_orderability_metadata",
        "as_of": observed.isoformat(),
        "asset_class": "crypto",
        "broker_state_mode": "alpaca_paper_observed",
        "target_symbol": symbol,
        "target_scoped": True,
        "records": [record],
        "resolved_source_sha256": raw_sha256,
        "resolved_source_digests": {
            role: raw_hashes[role]
            for role in (
                "venue_refresh_manifest",
                "venue_universe",
                "orderability_metadata",
                "venue_router_input_manifest",
                "venue_runtime_visibility_status",
                "venue_refresh_source",
                "venue_visibility_operator_source",
                "venue_supervisor_source",
            )
        },
    }


def _validate_venue_provenance(
    manifest: Mapping[str, object],
    universe: Mapping[str, object],
    orderability: Mapping[str, object],
    router: Mapping[str, object],
    runtime: Mapping[str, object],
    raw_hashes: Mapping[str, str],
    *,
    symbol: str,
    as_of: datetime,
) -> datetime:
    schema = "v5_1_crypto_universe_refresh_v1"
    if (
        set(manifest) != _VENUE_MANIFEST_KEYS
        or manifest.get("schema_version") != schema
        or manifest.get("generated_under_runs") is not True
        or manifest.get("labels") != _VENUE_PAPER_READ_LABELS
        or set(universe) != _VENUE_UNIVERSE_KEYS
        or set(router) != _VENUE_ROUTER_KEYS
    ):
        raise ValidationError("venue provenance control envelope drifted")
    required = _mapping(
        manifest.get("required_artifacts"),
        "venue_manifest.required_artifacts",
    )
    if set(required) != _VENUE_REQUIRED_ARTIFACT_ROLES:
        raise ValidationError("venue manifest artifact roles drifted")
    if any(
        set(_mapping(entry, "venue_manifest.required_entry"))
        != {"path", "sha256"}
        for entry in required.values()
    ):
        raise ValidationError("venue manifest artifact entry drifted")
    for role, source_role, basename in (
        ("crypto_universe", "venue_universe", "crypto_universe.json"),
        (
            "crypto_orderability_metadata",
            "orderability_metadata",
            "crypto_orderability_metadata.json",
        ),
        (
            "crypto_router_input_manifest",
            "venue_router_input_manifest",
            "crypto_router_input_manifest.json",
        ),
    ):
        entry = _mapping(required.get(role), f"venue_manifest.{role}")
        if (
            set(entry) != {"path", "sha256"}
            or _path_basename(entry.get("path")) != basename
            or entry.get("sha256") != raw_hashes[source_role]
        ):
            raise ValidationError(f"venue manifest hash binding failed: {role}")
    refresh_at = _utc_datetime(orderability.get("as_of"), "venue.as_of")
    shared_identity = (
        ("schema_version", schema),
        ("as_of", refresh_at.isoformat()),
        ("asset_class", "crypto"),
        ("mode", "paper_read_only"),
        ("source_mode", "paper_read_only"),
        ("broker_state_mode", "alpaca_paper_observed"),
    )
    for name, packet in (
        ("universe", universe),
        ("orderability", orderability),
        ("router", router),
    ):
        for field_name, expected in shared_identity:
            if packet.get(field_name) != expected:
                raise ValidationError(
                    f"venue {name} identity mismatch: {field_name}"
                )
    if manifest.get("as_of") != refresh_at.isoformat():
        raise ValidationError("venue manifest timestamp mismatch")
    for packet in (manifest, universe, router):
        for field_name in (
            "paper_submit_authorized",
            "paper_submit_performed",
            "broker_mutation_performed",
            "live_mutation_performed",
            "network_access_attempted",
        ):
            if packet.get(field_name) is not False:
                raise ValidationError("venue packet carries mutation authority")
    if (
        universe.get("broker_read_observed") is not True
        or router.get("broker_read_observed") is not True
        or universe.get("labels") != _VENUE_PAPER_READ_LABELS
        or router.get("labels") != _VENUE_PAPER_READ_LABELS
        or router.get("crypto_universe_path") != "crypto_universe.json"
        or router.get("crypto_orderability_metadata_path")
        != "crypto_orderability_metadata.json"
        or router.get("crypto_history_manifest_path")
        != "crypto_history_manifest.json"
        or router.get("crypto_history_quality_report_path")
        != "crypto_history_quality_report.json"
        or symbol not in _string_sequence(universe.get("symbols"))
    ):
        raise ValidationError("venue packet read-only identity is invalid")
    runtime_at = _utc_datetime(
        runtime.get("run_timestamp"),
        "venue_runtime.run_timestamp",
    )
    capability = _mapping(
        runtime.get("crypto_capability"),
        "venue_runtime.crypto_capability",
    )
    preflight = _mapping(
        runtime.get("operator_preflight"),
        "venue_runtime.operator_preflight",
    )
    preflight_keys = {
        "APP_PROFILE_is_paper", "APP_PROFILE_is_live",
        "ALPACA_API_KEY_present", "ALPACA_API_SECRET_KEY_present",
        "ALPACA_SECRET_KEY_present", "APCA_API_KEY_ID_present",
        "APCA_API_SECRET_KEY_present", "paper_credentials_present",
        "paper_endpoint_exact_match_indicator", "live_endpoint_indicator",
    }
    if (
        set(runtime) != _VENUE_RUNTIME_KEYS
        or set(capability) != _VENUE_RUNTIME_CAPABILITY_KEYS
        or set(preflight) != preflight_keys
        or any(type(value) is not bool for value in preflight.values())
        or runtime.get("schema_version")
        != "v4_11c_crypto_paper_supervisor_v1"
        or runtime.get("universe") != "crypto"
        or runtime.get("asset_class") != "crypto"
        or runtime.get("operator_command")
        != "run_crypto_paper_visibility_cycle"
        or runtime.get("target_symbol") != symbol
        or runtime.get("target_scoped") is not True
        or runtime.get("operating_mode") != "visibility/no_submit"
        or runtime.get("broker_read_requested") is not True
        or runtime.get("broker_read_performed") is not True
        or runtime.get("broker_read_error_type") != ""
        or runtime.get("broker_state_mode") != "alpaca_paper_observed"
        or runtime.get("capability_source") != "observed"
        or runtime.get("crypto_trading_supported") is not True
        or runtime.get("selected_symbol") != symbol
        or symbol not in _string_sequence(runtime.get("eligible_crypto_symbols"))
        or runtime.get("selected_symbol_tradable") is not True
        or runtime.get("unsupported_jurisdiction_account_blocker") not in ("", False)
        or runtime.get("no_submit_wrapper") is not True
        or runtime.get("no_submit_mode") is not True
        or runtime.get("paper_only_mode") is not True
        or runtime.get("submit_allowed") is not False
        or runtime.get("paper_mutation_allowed") is not False
        or runtime.get("strategy_adapter_paper_mutation_allowed") is not False
        or runtime.get("paper_submit_performed") is not False
        or runtime.get("broker_mutation_performed") is not False
        or runtime.get("live_mutation_performed") is not False
        or runtime.get("live_endpoint_indicator") is not False
        or preflight.get("APP_PROFILE_is_paper") is not True
        or preflight.get("APP_PROFILE_is_live") is not False
        or preflight.get("paper_credentials_present") is not True
        or preflight.get("paper_endpoint_exact_match_indicator") is not True
        or preflight.get("live_endpoint_indicator") is not False
    ):
        raise ValidationError("runtime venue visibility is invalid")
    repeated_fields = (
        "broker_read_performed", "broker_state_mode", "crypto_trading_supported",
        "eligible_crypto_symbols", "selected_symbol", "selected_symbol_tradable",
        "selected_symbol_marginable", "selected_symbol_fractionable",
        "min_order_size", "min_trade_increment", "min_order_increment",
        "min_notional", "paper_only_mode", "live_endpoint_indicator",
        "unsupported_jurisdiction_account_blocker", "capability_source",
    )
    if any(capability.get(field) != runtime.get(field) for field in repeated_fields):
        raise ValidationError("runtime nested venue capability drifted")
    records = _mapping_sequence(orderability.get("records"), "venue.records")
    matches = [record for record in records if record.get("symbol") == symbol]
    router_records = _mapping_sequence(router.get("records"), "router.records")
    router_matches = [record for record in router_records if record.get("symbol") == symbol]
    if len(matches) != 1 or len(router_matches) != 1:
        raise ValidationError("venue candidate cross-binding is not unique")
    record = matches[0]
    router_record = router_matches[0]
    for field_name in ("metadata_status", "orderability_status"):
        if router_record.get(field_name) != record.get(field_name):
            raise ValidationError("venue router metadata drifted")
    if _string_sequence(router_record.get("orderability_blockers")):
        raise ValidationError("venue router orderability is blocked")
    for record_field, observed_field, runtime_field in (
        ("min_notional", "broker_observed_min_notional", "min_notional"),
        (
            "min_order_size",
            "broker_observed_min_order_size",
            "min_order_size",
        ),
        (
            "min_trade_increment",
            "broker_observed_min_trade_increment",
            "min_trade_increment",
        ),
    ):
        record_value = _decimal(record.get(record_field), record_field)
        observed_value = _decimal(record.get(observed_field), observed_field)
        runtime_value = _decimal(runtime.get(runtime_field), runtime_field)
        if record_value != observed_value or observed_value != runtime_value:
            raise ValidationError("venue broker metadata cross-binding drifted")
    alternate_minimum = record.get("min_order_notional")
    if (
        type(alternate_minimum) is not str
        or (
            alternate_minimum
            and _decimal(alternate_minimum, "min_order_notional")
            != _decimal(record.get("min_notional"), "min_notional")
        )
    ):
        raise ValidationError("venue alternate minimum notional drifted")
    price_increment = record.get("price_increment")
    observed_price_increment = record.get("broker_observed_price_increment")
    qty_increment = record.get("qty_increment")
    runtime_order_increment = runtime.get("min_order_increment")
    if (
        type(price_increment) is not str
        or type(observed_price_increment) is not str
        or price_increment != observed_price_increment
        or (
            price_increment
            and _decimal(price_increment, "price_increment") <= 0
        )
        or type(qty_increment) is not str
        or type(runtime_order_increment) is not str
        or qty_increment != runtime_order_increment
        or (
            qty_increment
            and _decimal(qty_increment, "qty_increment") <= 0
        )
    ):
        raise ValidationError("venue broker increment cross-binding drifted")
    derived_minimum = record.get("derived_min_order_value")
    if (
        type(derived_minimum) is not str
        or (
            bool(derived_minimum)
            and not Decimal("0")
            < _decimal(derived_minimum, "derived_min_order_value")
            <= Decimal("10")
        )
    ):
        raise ValidationError("venue derived minimum exceeds probe envelope")
    if (
        runtime_at > refresh_at
        or refresh_at > as_of
        or as_of - runtime_at > timedelta(hours=24)
        or as_of - refresh_at > timedelta(hours=24)
    ):
        raise ValidationError("venue evidence is stale or future-dated")
    return min(runtime_at, refresh_at)


def _normalize_policy(
    receipt: Mapping[str, object],
    raw_hashes: Mapping[str, str],
    *,
    subject: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema_version": _POLICY_SNAPSHOT_VERSION,
        "record_type": "crypto_bounded_order_policy_snapshot",
        "as_of": receipt["as_of"],
        "subject": dict(subject),
        "claims": {
            "policy_version": _POLICY_SNAPSHOT_VERSION,
            "symbol_allowlisted": True,
            "sizing_basis": "notional",
            "minimum_notional_usd": "1",
            "maximum_notional_usd": "10",
            "time_in_force": "gtc",
            "long_only": True,
            "cash_only": True,
            "leverage_allowed": False,
            "shorting_allowed": False,
            "max_positions": 1,
            "max_open_orders": 1,
            "max_entry_orders": 1,
            "max_exit_orders": 1,
            "max_replacements": 0,
        },
        "source_code_sha256": raw_hashes["safety_kernel_source"],
        "resolved_source_digests": {
            role: raw_hashes[role]
            for role in (
                "safety_kernel_source",
                "safety_certifier_source",
                "safety_focused_test_source",
                "safety_certification_receipt",
            )
        },
        "authority": dict(_CAPABILITY_AUTHORITY),
        "profit_claim": "none",
    }


def _normalize_lifecycle(
    submit_cancel: Mapping[str, object],
    fill_exit: Mapping[str, object],
    *,
    submit_manifest: Mapping[str, object],
    submit_approval: Mapping[str, object],
    dry_run: Mapping[str, object],
    fill_manifest: Mapping[str, object],
    fill_approval: Mapping[str, object],
    fill_approval_manifest: Mapping[str, object],
    raw_hashes: Mapping[str, str],
    raw_sizes: Mapping[str, int],
    subject: Mapping[str, object],
    as_of: datetime,
) -> dict[str, object]:
    symbol = subject["symbol"]
    if symbol != "BTCUSD":
        raise ValidationError(
            "legacy V5.8/V5.10 lifecycle evidence is BTCUSD-only"
        )
    provenance_observed = _validate_lifecycle_provenance(
        submit_cancel,
        fill_exit,
        submit_manifest=submit_manifest,
        submit_approval=submit_approval,
        dry_run=dry_run,
        fill_manifest=fill_manifest,
        fill_approval=fill_approval,
        fill_approval_manifest=fill_approval_manifest,
        raw_hashes=raw_hashes,
        raw_sizes=raw_sizes,
        as_of=as_of,
    )
    submit_preflight = _mapping(
        submit_cancel.get("operator_preflight"),
        "submit_cancel.operator_preflight",
    )
    fill_preflight = _mapping(
        fill_exit.get("operator_preflight"),
        "fill_exit.operator_preflight",
    )
    if (
        submit_cancel.get("schema_version")
        != "v5_8_crypto_paper_submit_cancel_certification_v1"
        or submit_cancel.get("symbol") != symbol
        or submit_cancel.get("outcome_classification")
        != "submitted_cancel_confirmed"
        or type(submit_cancel.get("submit_attempt_count")) is not int
        or submit_cancel.get("submit_attempt_count") != 1
        or type(submit_cancel.get("cancel_attempt_count")) is not int
        or submit_cancel.get("cancel_attempt_count") != 1
        or submit_cancel.get("final_order_status") != "canceled"
        or submit_cancel.get("reconciliation_status") != "reconciled"
        or _decimal(submit_cancel.get("filled_qty"), "filled_qty") != 0
        or submit_cancel.get("residual_open_order") is not False
        or _mapping(
            submit_cancel.get("residual_position"),
            "submit_cancel.residual_position",
        )
        != {}
        or _decimal(
            submit_cancel.get("submitted_qty"),
            "submit_cancel.submitted_qty",
        )
        > _decimal(
            submit_cancel.get("approved_qty"),
            "submit_cancel.approved_qty",
        )
        or not Decimal("0")
        < _decimal(
            submit_cancel.get("estimated_submit_notional"),
            "submit_cancel.estimated_submit_notional",
        )
        <= Decimal("25")
        or submit_cancel.get("paper_submit_performed") is not True
        or submit_cancel.get("paper_cancel_performed") is not True
        or submit_cancel.get("paper_submit_authorized") is not True
        or submit_cancel.get("paper_cancel_authorized") is not True
        or submit_cancel.get("broker_read_observed") is not True
        or submit_cancel.get("broker_mutation_performed") is not True
        or submit_cancel.get("expected_paper_account_id_loaded") is not True
        or submit_cancel.get("expected_account_matched") is not True
        or submit_cancel.get("retry_submit_allowed") is not False
        or submit_cancel.get("second_order_submit_allowed") is not False
        or submit_cancel.get("close_or_liquidate_allowed") is not False
        or submit_cancel.get("replace_allowed") is not False
        or submit_cancel.get("live_mutation_performed") is not False
        or submit_cancel.get("live_endpoint_touched") is not False
        or submit_cancel.get("credential_values_exposed") is not False
        or not _paper_preflight_passed(submit_preflight)
        or _string_sequence(submit_cancel.get("blockers"))
    ):
        raise ValidationError("submit/cancel mechanics receipt is invalid")
    if (
        fill_exit.get("schema_version")
        != "v5_10_crypto_paper_fill_exit_certification_v1"
        or fill_exit.get("symbol") != symbol
        or fill_exit.get("outcome_classification") != "filled_exit_confirmed"
        or type(fill_exit.get("entry_attempt_count")) is not int
        or fill_exit.get("entry_attempt_count") != 1
        or type(fill_exit.get("exit_attempt_count")) is not int
        or fill_exit.get("exit_attempt_count") != 1
        or fill_exit.get("entry_final_status") != "filled"
        or fill_exit.get("exit_final_status") != "filled"
        or not Decimal("0")
        < _decimal(
            fill_exit.get("entry_filled_qty"),
            "fill_exit.entry_filled_qty",
        )
        or not Decimal("0")
        < _decimal(
            fill_exit.get("exit_filled_qty"),
            "fill_exit.exit_filled_qty",
        )
        or fill_exit.get("residual_position_status")
        != f"flat_or_no_{symbol}_position_observed"
        or _mapping(fill_exit.get("final_position"), "fill_exit.final_position")
        != {}
        or fill_exit.get("labels") != list(_V510_REQUIRED_LABELS)
        or fill_exit.get("paper_submit_performed") is not True
        or fill_exit.get("paper_fill_exit_authorized") is not True
        or fill_exit.get("broker_read_observed") is not True
        or fill_exit.get("broker_mutation_performed") is not True
        or type(fill_exit.get("entry_call_count_max")) is not int
        or fill_exit.get("entry_call_count_max") != 1
        or type(fill_exit.get("exit_call_count_max")) is not int
        or fill_exit.get("exit_call_count_max") != 1
        or fill_exit.get("retry_entry_allowed") is not False
        or fill_exit.get("retry_exit_allowed") is not False
        or fill_exit.get("close_or_liquidate_allowed") is not False
        or fill_exit.get("replace_allowed") is not False
        or fill_exit.get("live_mutation_performed") is not False
        or fill_exit.get("live_endpoint_touched") is not False
        or fill_exit.get("credential_values_exposed") is not False
        or not _paper_preflight_passed(fill_preflight)
        or _string_sequence(fill_exit.get("blockers"))
    ):
        raise ValidationError("fill/exit mechanics receipt is invalid")
    submit_account_observation = _mapping(
        submit_cancel.get("account_observation"),
        "submit_cancel.account_observation",
    )
    fill_account_observation = _mapping(
        fill_exit.get("account_observation"),
        "fill_exit.account_observation",
    )
    _validate_lifecycle_account_observation(
        submit_account_observation,
        "submit_cancel.account_observation",
    )
    _validate_lifecycle_account_observation(
        fill_account_observation,
        "fill_exit.account_observation",
    )
    submit_binding = build_alpaca_paper_account_binding(
        submit_account_observation,
        expected_account_configured=True,
        expected_account_matched=True,
    )
    fill_binding = build_alpaca_paper_account_binding(
        fill_account_observation,
        expected_account_configured=True,
        expected_account_matched=True,
    )
    if submit_binding != fill_binding:
        raise ValidationError("lifecycle receipts observed different accounts")
    entry_final_order = _mapping(
        fill_exit.get("entry_final_order"), "fill_exit.entry_final_order"
    )
    exit_final_order = _mapping(
        fill_exit.get("exit_final_order"), "fill_exit.exit_final_order"
    )
    if (
        entry_final_order.get("status") != "filled"
        or exit_final_order.get("status") != "filled"
        or _decimal(
            entry_final_order.get("filled_qty"),
            "entry_final_order.filled_qty",
        )
        != _decimal(fill_exit.get("entry_filled_qty"), "entry_filled_qty")
        or _decimal(
            exit_final_order.get("filled_qty"),
            "exit_final_order.filled_qty",
        )
        != _decimal(fill_exit.get("exit_filled_qty"), "exit_filled_qty")
    ):
        raise ValidationError("fill/exit final order evidence drifted")
    submit_at = _utc_datetime(submit_cancel.get("as_of"), "submit_cancel.as_of")
    exit_at = _utc_datetime(fill_exit.get("as_of"), "fill_exit.as_of")
    entry_submitted_at = _utc_datetime(
        entry_final_order.get("submitted_at"), "entry_final_order.submitted_at"
    )
    entry_filled_at = _utc_datetime(
        entry_final_order.get("filled_at"), "entry_final_order.filled_at"
    )
    exit_submitted_at = _utc_datetime(
        exit_final_order.get("submitted_at"), "exit_final_order.submitted_at"
    )
    exit_filled_at = _utc_datetime(
        exit_final_order.get("filled_at"), "exit_final_order.filled_at"
    )
    if (
        submit_at > as_of
        or exit_at > as_of
        or exit_filled_at > as_of
        or not (
            exit_at
            <= entry_submitted_at
            <= entry_filled_at
            <= exit_submitted_at
            <= exit_filled_at
        )
    ):
        raise ValidationError("lifecycle mechanics receipt is future-dated")
    observed = min(provenance_observed, submit_at, exit_at)
    if as_of - observed > timedelta(hours=720):
        raise ValidationError("lifecycle mechanics receipt is stale")
    tested_ceiling = min(
        _decimal(
            submit_cancel.get("estimated_submit_notional"),
            "estimated_submit_notional",
        ),
        _decimal(
            fill_exit.get("estimated_entry_notional"),
            "estimated_entry_notional",
        ),
    )
    if tested_ceiling < Decimal("10"):
        raise ValidationError("lifecycle mechanics did not test ten USD")
    return {
        "schema_version": "v5_26_crypto_lifecycle_mechanics_certification_v1",
        "record_type": "crypto_lifecycle_mechanics_certification_result",
        "as_of": observed.isoformat(),
        "last_broker_mutation_at": exit_filled_at.isoformat(),
        "subject": dict(subject),
        "mechanics_certified": True,
        "tested_notional_ceiling_usd": _decimal_text(tested_ceiling),
        "entry_submit_attempts": 1,
        "exit_submit_attempts": 1,
        "cancel_attempts_max_per_order": 1,
        "replacement_attempts": 0,
        "broker_ambiguity": False,
        "account_binding": submit_binding,
        "paper_only": True,
        "live_endpoint_touched": False,
        "resolved_source_digests": {
            role: raw_hashes[role]
            for role in (
                "submit_cancel_receipt",
                "submit_cancel_manifest",
                "submit_approval_packet",
                "paper_oms_dry_run",
                "paper_submit_cancel_source",
                "paper_submit_approval_source",
                "paper_oms_dry_run_source",
                "fill_exit_receipt",
                "fill_exit_manifest",
                "fill_approval_packet",
                "fill_approval_manifest",
                "paper_fill_exit_source",
                "paper_certification_ingestion_source",
            )
        },
        "provenance_classification": "local_hash_coherent_legacy_reconstruction",
        "authority": dict(_CAPABILITY_AUTHORITY),
        "profit_claim": "none",
    }


def _paper_preflight_passed(preflight: Mapping[str, object]) -> bool:
    return (
        preflight.get("APP_PROFILE_is_paper") is True
        and preflight.get("APP_PROFILE_is_live") is False
        and preflight.get("paper_credentials_present") is True
        and preflight.get("expected_paper_account_id_loaded") is True
        and preflight.get("paper_endpoint_exact_match_indicator") is True
        and preflight.get("live_endpoint_indicator") is False
        and preflight.get("network_test_flag_enabled") is False
    )


def _validate_lifecycle_account_observation(
    observation: Mapping[str, object],
    field_name: str,
) -> None:
    status = observation.get("status")
    if type(status) is not str or status.strip().upper() not in {
        "ACTIVE",
        "ACCOUNT_ACTIVE",
    }:
        raise ValidationError(f"{field_name} is not an active paper account")
    for blocker in ("blocked", "account_blocked", "trading_blocked"):
        if blocker not in observation or observation.get(blocker) is not False:
            raise ValidationError(
                f"{field_name} block flags are incomplete or unsafe"
            )


def _validate_lifecycle_provenance(
    submit_cancel: Mapping[str, object],
    fill_exit: Mapping[str, object],
    *,
    submit_manifest: Mapping[str, object],
    submit_approval: Mapping[str, object],
    dry_run: Mapping[str, object],
    fill_manifest: Mapping[str, object],
    fill_approval: Mapping[str, object],
    fill_approval_manifest: Mapping[str, object],
    raw_hashes: Mapping[str, str],
    raw_sizes: Mapping[str, int],
    as_of: datetime,
) -> datetime:
    _reject_unexpected_true_authority(dry_run, allowed_true=frozenset())
    _reject_unexpected_true_authority(submit_approval, allowed_true=frozenset())
    _reject_unexpected_true_authority(fill_approval, allowed_true=frozenset())
    _reject_unexpected_true_authority(
        submit_cancel,
        allowed_true=frozenset(
            {
                "paper_submit_authorized", "paper_cancel_authorized",
                "paper_submit_performed", "paper_cancel_performed",
                "broker_mutation_performed",
            }
        ),
    )
    _reject_unexpected_true_authority(
        fill_exit,
        allowed_true=frozenset(
            {
                "paper_fill_exit_authorized", "paper_submit_performed",
                "broker_mutation_performed",
            }
        ),
    )
    v58_keys = {
        "schema_version", "as_of", "artifact_root", "generated_under_runs",
        "credential_values_redacted", "required_artifacts", "input_artifacts",
        "paper_submit_authorized", "paper_submit_performed",
        "broker_mutation_performed", "live_mutation_performed",
        "live_endpoint_touched", "credential_values_exposed",
        "outcome_classification", "labels",
    }
    v59_keys = {
        "schema_version", "record_type", "as_of", "artifact_root",
        "required_artifacts", "manifest", "input_artifacts",
        "certification_status", "approval_packet_status", "approval_state",
        "broker_action_permitted", "paper_submit_authorized",
        "paper_fill_authorized", "broker_mutation_authorized_by_this_packet",
        "broker_read_performed_current_run",
        "broker_mutation_performed_current_run",
        "paper_submit_performed_current_run", "live_endpoint_touched_current_run",
        "live_mutation_performed_current_run", "credential_values_exposed",
        "network_access_attempted", "generated_under_runs", "labels",
        "profit_claim",
    }
    v59_packet_keys = {
        "schema_version", "record_type", "as_of", "approval_packet_status",
        "approval_state", "certification_status",
        "requested_future_authorization_scope",
        "prior_certification_result_source",
        "prior_certification_result_sha256",
        "prior_certification_result_referenced", "prior_certification_id",
        "prior_client_order_id", "prior_final_order_status",
        "prior_filled_qty", "prior_residual_position", "proposed_symbol",
        "proposed_symbol_scope",
        "proposed_max_notional", "proposed_max_notional_cap",
        "proposed_notional_no_greater_than_25", "required_operator_phrase",
        "operator_phrase_generated_for_review_only",
        "operator_phrase_accepted", "disallowed_actions", "blockers", "labels",
        "live_authorized", "autonomous_submit_authorized",
        "paper_fill_authorized", "paper_entry_authorized",
        "paper_exit_authorized", "paper_submit_authorized",
        "broker_action_permitted",
        "broker_mutation_authorized_by_this_packet",
        "broker_read_performed_current_run",
        "broker_mutation_performed_current_run",
        "paper_submit_performed_current_run",
        "paper_cancel_performed_current_run",
        "live_endpoint_touched_current_run",
        "live_mutation_performed_current_run", "credential_values_exposed",
        "network_access_attempted", "profit_claim", "next_operator_action",
        "artifact_paths",
    }
    v510_keys = {
        "schema_version", "record_type", "as_of", "artifact_root",
        "generated_under_runs", "credential_values_redacted",
        "required_artifacts", "input_artifacts", "broker_read_observed",
        "broker_mutation_performed", "paper_submit_performed",
        "live_mutation_performed", "live_endpoint_touched",
        "credential_values_exposed", "outcome_classification", "labels",
    }
    if (
        set(submit_manifest) != v58_keys
        or submit_manifest.get("schema_version")
        != "v5_8_crypto_paper_submit_cancel_certification_v1"
        or set(fill_approval_manifest) != v59_keys
        or fill_approval_manifest.get("schema_version")
        != "v5_9_crypto_paper_certification_ingestion_v1"
        or fill_approval_manifest.get("record_type")
        != "crypto_paper_certification_ingestion_manifest"
        or set(fill_approval) != v59_packet_keys
        or set(fill_manifest) != v510_keys
        or fill_manifest.get("schema_version")
        != "v5_10_crypto_paper_fill_exit_certification_v1"
        or fill_manifest.get("record_type")
        != "crypto_paper_fill_exit_certification_manifest"
    ):
        raise ValidationError("lifecycle manifest control envelope drifted")
    lifecycle_times = (
        _utc_datetime(dry_run.get("as_of"), "paper_oms_dry_run.as_of"),
        _utc_datetime(
            submit_approval.get("as_of"),
            "submit_approval_packet.as_of",
        ),
        _utc_datetime(submit_cancel.get("as_of"), "submit_cancel.as_of"),
        _utc_datetime(
            fill_approval.get("as_of"),
            "fill_approval_packet.as_of",
        ),
        _utc_datetime(fill_exit.get("as_of"), "fill_exit.as_of"),
    )
    if (
        any(timestamp > as_of for timestamp in lifecycle_times)
        or any(
            later < earlier
            for earlier, later in zip(
                lifecycle_times[:-1],
                lifecycle_times[1:],
                strict=True,
            )
        )
        or fill_approval_manifest.get("as_of")
        != lifecycle_times[3].isoformat()
    ):
        raise ValidationError("lifecycle chronology is invalid")
    submit_required = _mapping(
        submit_manifest.get("required_artifacts"),
        "submit_manifest.required_artifacts",
    )
    submit_inputs = _mapping(
        submit_manifest.get("input_artifacts"),
        "submit_manifest.input_artifacts",
    )
    if (
        set(submit_required)
        != {"certification_result_json", "certification_result_md", "operating_record"}
        or set(submit_inputs) != {"approval_packet", "paper_oms_dry_run"}
    ):
        raise ValidationError("V5.8 manifest roles drifted")
    result_entry = _mapping(
        submit_required.get("certification_result_json"),
        "submit_manifest.certification_result_json",
    )
    if (
        set(result_entry) != {"path", "sha256", "size"}
        or _path_basename(result_entry.get("path")) != "certification_result.json"
        or result_entry.get("sha256") != raw_hashes["submit_cancel_receipt"]
        or type(result_entry.get("size")) is not int
        or result_entry.get("size") != raw_sizes["submit_cancel_receipt"]
    ):
        raise ValidationError("V5.8 result hash binding failed")
    for entry in submit_required.values():
        if set(_mapping(entry, "submit_manifest.required_entry")) != {
            "path", "sha256", "size"
        }:
            raise ValidationError("V5.8 artifact entry drifted")
    approval_entry = _mapping(
        submit_inputs.get("approval_packet"),
        "submit_manifest.approval_packet",
    )
    dry_run_entry = _mapping(
        submit_inputs.get("paper_oms_dry_run"),
        "submit_manifest.paper_oms_dry_run",
    )
    if (
        set(approval_entry) != {"path", "sha256"}
        or set(dry_run_entry) != {"path", "sha256"}
        or approval_entry.get("sha256") != raw_hashes["submit_approval_packet"]
        or dry_run_entry.get("sha256") != raw_hashes["paper_oms_dry_run"]
        or submit_cancel.get("approval_packet_source") != approval_entry.get("path")
        or submit_cancel.get("dry_run_source") != dry_run_entry.get("path")
        or submit_approval.get("dry_run_source") != dry_run_entry.get("path")
    ):
        raise ValidationError("V5.8 input hash binding failed")
    if (
        dry_run.get("schema_version") != "v5_6_crypto_paper_oms_dry_run_v1"
        or dry_run.get("symbol") != "BTCUSD"
        or dry_run.get("approval_state") != "not_authorized"
        or dry_run.get("broker_action_permitted") is not False
        or submit_approval.get("schema_version")
        != "v5_7_crypto_paper_submit_approval_packet_v1"
        or submit_approval.get("symbol") != "BTCUSD"
        or submit_approval.get("approval_packet_status")
        != "ready_for_operator_review"
        or submit_approval.get("approval_state") != "not_authorized"
        or submit_approval.get("broker_action_permitted") is not False
    ):
        raise ValidationError("V5.6/V5.7 lifecycle antecedent is invalid")
    for packet in (dry_run, submit_approval):
        for field_name in (
            "paper_submit_authorized", "paper_submit_performed",
            "broker_mutation_performed", "live_mutation_performed",
            "live_endpoint_touched", "credential_values_exposed",
            "network_access_attempted",
        ):
            if field_name in packet and packet.get(field_name) is not False:
                raise ValidationError("lifecycle antecedent carries authority")
    approval_summary = {
        field_name: submit_approval.get(field_name)
        for field_name in (
            "schema_version", "approval_packet_status", "approval_state",
            "dry_run_id", "pre_broker_order_id", "symbol", "exact_qty",
            "exact_cap", "blockers", "labels",
        )
    }
    dry_run_summary = {
        field_name: dry_run.get(field_name)
        for field_name in (
            "schema_version", "dry_run_status", "approval_state", "dry_run_id",
            "pre_broker_order_id", "symbol", "rounded_qty", "preview_cap",
            "latest_price", "blockers", "labels",
        )
    }
    if (
        submit_cancel.get("approval_packet_summary") != approval_summary
        or submit_cancel.get("dry_run_summary") != dry_run_summary
        or submit_cancel.get("dry_run_id") != dry_run.get("dry_run_id")
        or submit_cancel.get("pre_broker_order_id")
        != dry_run.get("pre_broker_order_id")
        or submit_cancel.get("approved_authorization_text")
        != submit_approval.get("required_operator_phrase")
    ):
        raise ValidationError("V5.8 lifecycle summary binding failed")
    fill_required = _mapping(
        fill_approval_manifest.get("required_artifacts"),
        "fill_approval_manifest.required_artifacts",
    )
    fill_approval_inputs = _mapping(
        fill_approval_manifest.get("input_artifacts"),
        "fill_approval_manifest.input_artifacts",
    )
    if (
        set(fill_required) != {
            "certification_ingestion_json", "certification_ingestion_md",
            "paper_fill_experiment_approval_packet_json",
            "paper_fill_experiment_approval_packet_md", "operating_record",
        }
        or set(fill_approval_inputs) != {"certification_result"}
    ):
        raise ValidationError("V5.9 manifest roles drifted")
    if any(
        set(_mapping(entry, "fill_approval_manifest.required_entry"))
        != {"path", "sha256", "size"}
        for entry in fill_required.values()
    ) or set(
        _mapping(fill_approval_manifest.get("manifest"), "V5.9 manifest path")
    ) != {"path"}:
        raise ValidationError("V5.9 artifact entry drifted")
    packet_entry = _mapping(
        fill_required.get("paper_fill_experiment_approval_packet_json"),
        "fill_approval_manifest.packet",
    )
    prior_entry = _mapping(
        fill_approval_inputs.get("certification_result"),
        "fill_approval_manifest.prior",
    )
    v58_sha = raw_hashes["submit_cancel_receipt"]
    if (
        set(packet_entry) != {"path", "sha256", "size"}
        or packet_entry.get("sha256") != raw_hashes["fill_approval_packet"]
        or packet_entry.get("size") != raw_sizes["fill_approval_packet"]
        or set(prior_entry) != {"path", "sha256"}
        or prior_entry.get("sha256") != v58_sha
        or prior_entry.get("path") != result_entry.get("path")
        or fill_approval.get("prior_certification_result_sha256") != v58_sha
    ):
        raise ValidationError("V5.9 hash binding failed")
    prior_reference = _mapping(
        fill_approval.get("prior_certification_result_referenced"),
        "fill_approval.prior_reference",
    )
    expected_prior_id = (
        "v58_btcusd_submit_cancel_"
        + _stable_hash(
            {
                "client_order_id": submit_cancel.get("client_order_id"),
                "outcome": submit_cancel.get("outcome_classification"),
                "source_sha256": v58_sha,
            }
        )[:16]
    )
    disallowed_actions = list(V59_DISALLOWED_ACTIONS)
    expected_operator_phrase = (
        "Authorized for future v5.10 review: using prior_certification_id "
        f"{expected_prior_id} and prior client_order_id "
        f"{submit_cancel.get('client_order_id')}, authorize exactly one bounded "
        "BTCUSD Alpaca paper entry attempt and one bounded exit/flatten attempt "
        "for the resulting BTCUSD paper position, with max notional 25. This "
        "does not authorize live trading, additional orders, replacement, "
        "liquidation/close-all, capital changes, credential exposure, or paid "
        "services."
    )
    if (
        set(prior_reference)
        != {
            "path", "sha256", "schema_version", "as_of",
            "outcome_classification", "client_order_id",
            "final_order_status", "filled_qty",
        }
        or
        prior_reference.get("sha256") != v58_sha
        or prior_reference.get("path") != prior_entry.get("path")
        or prior_reference.get("schema_version")
        != submit_cancel.get("schema_version")
        or prior_reference.get("as_of") != submit_cancel.get("as_of")
        or prior_reference.get("outcome_classification")
        != submit_cancel.get("outcome_classification")
        or prior_reference.get("client_order_id")
        != submit_cancel.get("client_order_id")
        or prior_reference.get("final_order_status")
        != submit_cancel.get("final_order_status")
        or prior_reference.get("filled_qty") != submit_cancel.get("filled_qty")
        or fill_approval.get("prior_certification_id") != expected_prior_id
        or fill_approval.get("prior_client_order_id")
        != submit_cancel.get("client_order_id")
        or fill_approval.get("prior_final_order_status")
        != submit_cancel.get("final_order_status")
        or fill_approval.get("prior_filled_qty")
        != submit_cancel.get("filled_qty")
        or fill_approval.get("prior_residual_position")
        != submit_cancel.get("residual_position", {})
        or fill_approval.get("prior_certification_result_source")
        != prior_entry.get("path")
        or fill_approval.get("schema_version")
        != "v5_9_crypto_paper_certification_ingestion_v1"
        or fill_approval.get("record_type")
        != "paper_fill_experiment_approval_packet"
        or fill_approval.get("approval_packet_status")
        != "ready_for_operator_review"
        or fill_approval.get("approval_state") != "not_authorized"
        or fill_approval.get("certification_status")
        != "certified_submit_cancel_no_fill"
        or fill_approval.get("requested_future_authorization_scope")
        != "bounded_btcusd_paper_fill_and_exit_certification"
        or fill_approval.get("proposed_symbol") != "BTCUSD"
        or fill_approval.get("proposed_symbol_scope") != "BTCUSD only"
        or _decimal(
            fill_approval.get("proposed_max_notional"),
            "proposed_max_notional",
        ) != Decimal("25")
        or _decimal(
            fill_approval.get("proposed_max_notional_cap"),
            "proposed_max_notional_cap",
        ) != Decimal("25")
        or fill_approval.get("proposed_notional_no_greater_than_25") is not True
        or fill_approval.get("required_operator_phrase")
        != expected_operator_phrase
        or fill_approval.get("operator_phrase_generated_for_review_only")
        is not True
        or fill_approval.get("operator_phrase_accepted") is not False
        or fill_approval.get("disallowed_actions") != disallowed_actions
        or fill_approval.get("labels") != list(V59_REQUIRED_LABELS)
        or fill_approval_manifest.get("labels") != list(V59_REQUIRED_LABELS)
        or fill_approval_manifest.get("certification_status")
        != fill_approval.get("certification_status")
        or fill_approval_manifest.get("approval_packet_status")
        != fill_approval.get("approval_packet_status")
        or fill_approval_manifest.get("approval_state")
        != fill_approval.get("approval_state")
        or fill_approval.get("next_operator_action")
        != (
            "operator_review_required_before_any_future_bounded_btcusd_paper_"
            "fill_and_exit_certification"
        )
        or _string_sequence(fill_approval.get("blockers"))
        or fill_approval.get("profit_claim") != "none"
    ):
        raise ValidationError("V5.9 prior certification binding failed")
    artifact_paths = _mapping(
        fill_approval.get("artifact_paths"),
        "fill_approval.artifact_paths",
    )
    expected_artifact_basenames = {
        "certification_ingestion_json": "certification_ingestion.json",
        "certification_ingestion_md": "certification_ingestion.md",
        "paper_fill_experiment_approval_packet_json": (
            "paper_fill_experiment_approval_packet.json"
        ),
        "paper_fill_experiment_approval_packet_md": (
            "paper_fill_experiment_approval_packet.md"
        ),
        "operating_record": "operating_record.jsonl",
        "manifest": "manifest.json",
    }
    manifest_path = _mapping(
        fill_approval_manifest.get("manifest"), "V5.9 manifest path"
    ).get("path")
    if (
        set(artifact_paths) != set(expected_artifact_basenames)
        or any(
            _path_basename(artifact_paths.get(role)) != basename
            for role, basename in expected_artifact_basenames.items()
        )
        or any(
            artifact_paths.get(role)
            != _mapping(fill_required.get(role), f"V5.9 {role}").get("path")
            for role in fill_required
        )
        or artifact_paths.get("manifest") != manifest_path
    ):
        raise ValidationError("V5.9 artifact paths drifted")
    expected_approval_summary = {
        field_name: fill_approval.get(field_name)
        for field_name in (
            "schema_version", "approval_packet_status", "approval_state",
            "requested_future_authorization_scope", "prior_certification_id",
            "prior_client_order_id", "proposed_symbol",
            "proposed_max_notional", "blockers", "labels",
        )
    }
    expected_prior_summary = {
        "schema_version": submit_cancel.get("schema_version"),
        "client_order_id": submit_cancel.get("client_order_id"),
        "symbol": submit_cancel.get("symbol"),
        "approved_max_notional": submit_cancel.get("approved_max_notional"),
        "outcome_classification": submit_cancel.get("outcome_classification"),
        "final_order_status": submit_cancel.get("final_order_status"),
        "filled_qty": submit_cancel.get("filled_qty"),
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
    }
    if (
        fill_exit.get("approval_packet_summary") != expected_approval_summary
        or fill_exit.get("prior_certification_summary")
        != expected_prior_summary
    ):
        raise ValidationError("V5.10 lifecycle summary binding failed")
    for field_name in (
        "live_authorized", "autonomous_submit_authorized",
        "paper_fill_authorized", "paper_entry_authorized",
        "paper_exit_authorized", "paper_submit_authorized",
        "broker_action_permitted",
        "broker_mutation_authorized_by_this_packet",
        "broker_read_performed_current_run",
        "broker_mutation_performed_current_run",
        "paper_submit_performed_current_run",
        "paper_cancel_performed_current_run",
        "live_endpoint_touched_current_run",
        "live_mutation_performed_current_run", "credential_values_exposed",
        "network_access_attempted",
    ):
        if fill_approval.get(field_name) is not False:
            raise ValidationError("V5.9 approval packet carries authority")
    fill_required = _mapping(
        fill_manifest.get("required_artifacts"),
        "fill_manifest.required_artifacts",
    )
    fill_inputs = _mapping(
        fill_manifest.get("input_artifacts"),
        "fill_manifest.input_artifacts",
    )
    if (
        set(fill_required) != {
            "fill_exit_certification_result_json",
            "fill_exit_certification_result_md", "operating_record", "manifest",
        }
        or set(fill_inputs) != {"approval_packet", "prior_certification_result"}
    ):
        raise ValidationError("V5.10 manifest roles drifted")
    for role, entry in fill_required.items():
        expected_keys = {"path"} if role == "manifest" else {
            "path", "exists", "sha256"
        }
        if set(_mapping(entry, f"fill_manifest.{role}")) != expected_keys:
            raise ValidationError("V5.10 artifact entry drifted")
    fill_result_entry = _mapping(
        fill_required.get("fill_exit_certification_result_json"),
        "fill_manifest.result",
    )
    fill_packet_input = _mapping(fill_inputs.get("approval_packet"), "fill input")
    fill_prior_input = _mapping(
        fill_inputs.get("prior_certification_result"),
        "fill prior input",
    )
    if (
        set(fill_result_entry) != {"path", "exists", "sha256"}
        or fill_result_entry.get("exists") is not True
        or fill_result_entry.get("sha256") != raw_hashes["fill_exit_receipt"]
        or set(fill_packet_input) != {"path", "exists"}
        or fill_packet_input.get("exists") is not True
        or set(fill_prior_input) != {"path", "exists"}
        or fill_prior_input.get("exists") is not True
        or fill_exit.get("approval_packet_source") != fill_packet_input.get("path")
        or fill_exit.get("prior_certification_source")
        != fill_prior_input.get("path")
        or fill_packet_input.get("path") != packet_entry.get("path")
        or fill_prior_input.get("path") != prior_entry.get("path")
        or fill_exit.get("prior_certification_id") != expected_prior_id
        or fill_exit.get("approved_authorization_text")
        != fill_approval.get("required_operator_phrase")
    ):
        raise ValidationError("V5.10 lifecycle hash binding failed")
    if (
        submit_manifest.get("as_of") != submit_cancel.get("as_of")
        or submit_manifest.get("outcome_classification")
        != submit_cancel.get("outcome_classification")
        or fill_manifest.get("as_of") != fill_exit.get("as_of")
        or fill_manifest.get("outcome_classification")
        != fill_exit.get("outcome_classification")
        or fill_manifest.get("labels") != fill_exit.get("labels")
    ):
        raise ValidationError("lifecycle manifest result identity drifted")
    for manifest in (submit_manifest, fill_manifest):
        if (
            manifest.get("generated_under_runs") is not True
            or manifest.get("credential_values_redacted") is not True
            or manifest.get("live_mutation_performed") is not False
            or manifest.get("live_endpoint_touched") is not False
            or manifest.get("credential_values_exposed") is not False
        ):
            raise ValidationError("lifecycle manifest safety drifted")
    for field_name in (
        "broker_action_permitted", "paper_submit_authorized",
        "paper_fill_authorized", "broker_mutation_authorized_by_this_packet",
        "broker_read_performed_current_run",
        "broker_mutation_performed_current_run",
        "paper_submit_performed_current_run", "live_endpoint_touched_current_run",
        "live_mutation_performed_current_run", "credential_values_exposed",
        "network_access_attempted",
    ):
        if fill_approval_manifest.get(field_name) is not False:
            raise ValidationError("V5.9 manifest carries authority")
    return min(lifecycle_times)


def _reject_unexpected_true_authority(
    packet: Mapping[str, object],
    *,
    allowed_true: frozenset[str],
) -> None:
    for field_name, value in packet.items():
        authority_shaped = (
            "authoriz" in field_name
            or "permit" in field_name
            or "_allowed" in field_name
            or "_performed" in field_name
            or "_occurred" in field_name
            or "_attempted" in field_name
            or "_touched" in field_name
            or field_name == "credential_values_exposed"
        )
        if authority_shaped and value is True and field_name not in allowed_true:
            raise ValidationError(
                f"unexpected lifecycle authority field: {field_name}"
            )


def _normalize_flat(
    raw: Mapping[str, object],
    raw_sha256: str,
    *,
    subject: Mapping[str, object],
    expected_account_binding: Mapping[str, object],
    not_before: datetime,
    as_of: datetime,
) -> dict[str, object]:
    expected_keys = {
        "schema_version",
        "record_type",
        "as_of",
        "subject",
        "account_binding",
        "read_only_reconciliation",
        "broker_read_occurred",
        "account_read_occurred",
        "positions_read_occurred",
        "open_orders_read_occurred",
        "final_position_count",
        "final_open_order_count",
        "observed_position_symbols",
        "observed_open_order_symbols",
        "broker_ambiguity",
        "mutation_occurred",
        "live_endpoint_touched",
        "authority",
        "profit_claim",
        "source_snapshot_fingerprint",
        "observation_fingerprint",
    }
    fingerprint = str(raw.get("observation_fingerprint", ""))
    unsigned = dict(raw)
    unsigned.pop("observation_fingerprint", None)
    account_binding = _mapping(raw.get("account_binding"), "flat.account_binding")
    validate_alpaca_paper_account_binding(account_binding)
    validate_alpaca_paper_account_binding(expected_account_binding)
    if (
        set(raw) != expected_keys
        or raw.get("schema_version") != _FLAT_OBSERVATION_SCHEMA
        or raw.get("record_type")
        != "crypto_bounded_probe_independent_flat_observation"
        or raw.get("subject") != subject
        or account_binding != expected_account_binding
        or raw.get("read_only_reconciliation") is not True
        or raw.get("broker_read_occurred") is not True
        or raw.get("account_read_occurred") is not True
        or raw.get("positions_read_occurred") is not True
        or raw.get("open_orders_read_occurred") is not True
        or type(raw.get("final_position_count")) is not int
        or raw.get("final_position_count") != 0
        or type(raw.get("final_open_order_count")) is not int
        or raw.get("final_open_order_count") != 0
        or raw.get("observed_position_symbols") != []
        or raw.get("observed_open_order_symbols") != []
        or raw.get("broker_ambiguity") is not False
        or raw.get("mutation_occurred") is not False
        or raw.get("live_endpoint_touched") is not False
        or raw.get("authority") != _CAPABILITY_AUTHORITY
        or raw.get("profit_claim") != "none"
        or fingerprint != _stable_hash(unsigned)
    ):
        raise ValidationError("independent flat observation is invalid")
    observed = _utc_datetime(raw.get("as_of"), "flat.as_of")
    if (
        observed < not_before
        or observed > as_of
        or as_of - observed > timedelta(minutes=15)
    ):
        raise ValidationError("independent flat observation is stale or future-dated")
    source_snapshot = {
        "as_of": observed.isoformat(),
        "symbol": subject["symbol"],
        "account_binding": dict(account_binding),
        "position_count": 0,
        "open_order_count": 0,
        "broker_read_occurred": True,
        "account_read_occurred": True,
        "positions_read_occurred": True,
        "open_orders_read_occurred": True,
        "broker_ambiguity": False,
        "mutation_occurred": False,
        "live_endpoint_touched": False,
    }
    if (
        raw.get("as_of") != observed.isoformat()
        or raw.get("source_snapshot_fingerprint")
        != _stable_hash(source_snapshot)
    ):
        raise ValidationError("independent flat source binding is invalid")
    return {
        "schema_version": "v5_26_crypto_independent_flat_reconciliation_v1",
        "record_type": "crypto_independent_flat_reconciliation_result",
        "as_of": observed.isoformat(),
        "subject": dict(subject),
        "account_binding": dict(account_binding),
        "read_only_reconciliation": True,
        "broker_read_occurred": True,
        "account_read_occurred": True,
        "positions_read_occurred": True,
        "open_orders_read_occurred": True,
        "fresh": True,
        "final_position_count": 0,
        "final_open_order_count": 0,
        "observed_position_symbols": [],
        "observed_open_order_symbols": [],
        "broker_ambiguity": False,
        "mutation_occurred": False,
        "live_endpoint_touched": False,
        "resolved_source_sha256": raw_sha256,
        "validator_source_sha256": _LOADED_LOCAL_SOURCE_SHA256[
            "independent_flat_reconciliation_source"
        ],
        "authority": dict(_CAPABILITY_AUTHORITY),
        "profit_claim": "none",
    }


def _normalize_kill(
    receipt: Mapping[str, object],
    raw_hashes: Mapping[str, str],
    *,
    subject: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema_version": "v5_26_crypto_durable_kill_loss_certification_v1",
        "record_type": "crypto_durable_kill_loss_certification_result",
        "as_of": receipt["as_of"],
        "subject": dict(subject),
        "claims": dict(receipt["claims"]),
        "offline_test_receipt_sha256": raw_hashes[
            "safety_certification_receipt"
        ],
        "resolved_source_digests": {
            role: raw_hashes[role]
            for role in (
                "safety_kernel_source",
                "safety_certifier_source",
                "safety_focused_test_source",
                "safety_certification_receipt",
            )
        },
        "authority": dict(_CAPABILITY_AUTHORITY),
        "profit_claim": "none",
    }


def _validate_safety_receipt(
    receipt: Mapping[str, object],
    raw: Mapping[str, bytes],
    raw_hashes: Mapping[str, str],
    *,
    as_of: datetime,
) -> None:
    expected_keys = {
        "schema_version",
        "record_type",
        "as_of",
        "supported_symbols",
        "policy_fingerprint",
        "policy_manifest",
        "kernel_source_sha256",
        "certifier_source_sha256",
        "focused_test_source_sha256",
        "certification_checks",
        "symbol_results",
        "claims",
        "offline_only",
        "profit_claim",
        "authority",
        "receipt_fingerprint",
    }
    fingerprint = str(receipt.get("receipt_fingerprint", ""))
    unsigned = dict(receipt)
    unsigned.pop("receipt_fingerprint", None)
    if (
        set(receipt) != expected_keys
        or receipt.get("schema_version") != _SAFETY_CERTIFICATION_SCHEMA
        or receipt.get("record_type")
        != "crypto_bounded_probe_safety_certification_receipt"
        or receipt.get("supported_symbols") != list(_SUPPORTED_SYMBOLS)
        or receipt.get("policy_fingerprint") != _SAFETY_POLICY_FINGERPRINT
        or receipt.get("kernel_source_sha256")
        != raw_hashes["safety_kernel_source"]
        or receipt.get("certifier_source_sha256")
        != raw_hashes["safety_certifier_source"]
        or receipt.get("focused_test_source_sha256")
        != raw_hashes["safety_focused_test_source"]
        or receipt.get("certification_checks") != list(_CERTIFICATION_CHECKS)
        or receipt.get("claims") != _kill_claims()
        or receipt.get("offline_only") is not True
        or receipt.get("profit_claim") != "none"
        or receipt.get("authority") != _CERTIFICATION_AUTHORITY
        or fingerprint != _stable_hash(unsigned)
    ):
        raise ValidationError("safety certification receipt is invalid")
    results = receipt.get("symbol_results")
    if not isinstance(results, Sequence) or isinstance(results, (str, bytes)):
        raise ValidationError("safety certification symbol results are absent")
    expected_results = [
        {
            "symbol": symbol,
            "passed": True,
            "passed_checks": list(_CERTIFICATION_CHECKS),
        }
        for symbol in _SUPPORTED_SYMBOLS
    ]
    if list(results) != expected_results:
        raise ValidationError("safety certification did not pass all symbols")
    policy = receipt.get("policy_manifest")
    policy_unsigned = dict(policy) if isinstance(policy, Mapping) else {}
    policy_unsigned.pop("policy_fingerprint", None)
    if not isinstance(policy, Mapping) or (
        policy.get("policy_fingerprint") != _SAFETY_POLICY_FINGERPRINT
        or _stable_hash(policy_unsigned) != _SAFETY_POLICY_FINGERPRINT
        or policy.get("minimum_notional_usd") != "1"
        or policy.get("maximum_notional_usd") != "10"
        or policy.get("loss_halt_usd") != "2"
        or policy.get("maximum_replacements") != 0
        or policy.get("default_paused") is not True
        or policy.get("time_in_force") != "gtc"
        or policy.get("network_access_authorized") is not False
        or policy.get("paper_mutation_authorized") is not False
        or policy.get("live_authorized") is not False
    ):
        raise ValidationError("safety certification policy manifest drifted")
    observed = _utc_datetime(receipt.get("as_of"), "safety_receipt.as_of")
    if observed > as_of or as_of - observed > timedelta(hours=168):
        raise ValidationError("safety certification receipt is stale or future-dated")
    source_markers = {
        "safety_kernel_source": b"CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT",
        "safety_certifier_source": b"build_crypto_bounded_probe_safety_certification",
        "safety_focused_test_source": (
            b"test_concurrent_entry_claims_admit_exactly_one_attempt"
        ),
    }
    for role, marker in source_markers.items():
        if marker not in raw[role]:
            raise ValidationError("safety certification source marker is absent")


def _validate_local_source_bindings(
    raw: Mapping[str, bytes],
    raw_hashes: Mapping[str, str],
) -> None:
    """Bind eligibility to the exact local validators used by this process."""

    markers = {
        "capability_producer_source": (
            b"def _build_complete_bundle("
        ),
        "account_binding_source": (
            b"def validate_alpaca_paper_account_binding("
        ),
        "independent_flat_reconciliation_source": (
            b"def validate_crypto_bounded_probe_independent_flat_reconciliation("
        ),
        "venue_refresh_source": b"CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION",
        "venue_visibility_operator_source": b"CRYPTO_PAPER_VISIBILITY_COMMAND",
        "venue_supervisor_source": b"CRYPTO_PAPER_SUPERVISOR_SCHEMA_VERSION",
        "paper_submit_cancel_source": (
            b"CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_SCHEMA_VERSION"
        ),
        "paper_submit_approval_source": (
            b"CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION"
        ),
        "paper_oms_dry_run_source": b"CRYPTO_PAPER_OMS_DRY_RUN_SCHEMA_VERSION",
        "paper_fill_exit_source": (
            b"run_crypto_paper_fill_exit_certification"
        ),
        "paper_certification_ingestion_source": (
            b"CRYPTO_PAPER_CERTIFICATION_INGESTION_SCHEMA_VERSION"
        ),
        "safety_kernel_source": (
            b"CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT"
        ),
        "safety_certifier_source": (
            b"build_crypto_bounded_probe_safety_certification"
        ),
        "safety_focused_test_source": (
            b"test_concurrent_entry_claims_admit_exactly_one_attempt"
        ),
    }
    for role, expected_sha256 in _LOADED_LOCAL_SOURCE_SHA256.items():
        payload = raw.get(role)
        if (
            not isinstance(payload, bytes)
            or raw_hashes.get(role) != expected_sha256
            or markers[role] not in payload
        ):
            raise ValidationError(
                f"canonical local source binding mismatch: {role}"
            )


def _producer_source(
    kind: str,
    *,
    subject: Mapping[str, object],
    claims: Mapping[str, object],
    observed_at: datetime,
    upstream_hashes: Mapping[str, str],
) -> dict[str, object]:
    unsigned: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION
        ),
        "record_type": _CAPABILITY_SOURCE_RECORD_TYPE,
        "evidence_kind": kind,
        "source_role": "producer_source",
        "subject": dict(subject),
        "observed_at": observed_at.isoformat(),
        "valid_until": (
            observed_at + timedelta(hours=_CAPABILITY_MAX_AGE_HOURS[kind])
        ).isoformat(),
        "claims": dict(claims),
        "upstream_source_digests": [
            {
                "role": role,
                "schema_version": schema_version,
                "record_type": record_type,
                "sha256": upstream_hashes[role],
            }
            for role, schema_version, record_type in _UPSTREAM_CONTRACTS[kind]
        ],
        "producer_version": _CAPABILITY_PRODUCER_VERSION,
        "policy_fingerprint": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        ),
        "authority": dict(_CAPABILITY_AUTHORITY),
        "profit_claim": "none",
    }
    return {**unsigned, "source_fingerprint": _stable_hash(unsigned)}


def _capability_unsigned(
    kind: str,
    *,
    subject: Mapping[str, object],
    claims: Mapping[str, object],
    observed_at: datetime,
    source_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SCHEMA_VERSION
        ),
        "record_type": _CAPABILITY_RECORD_TYPE,
        "evidence_kind": kind,
        "subject": dict(subject),
        "observed_at": observed_at.isoformat(),
        "valid_until": (
            observed_at + timedelta(hours=_CAPABILITY_MAX_AGE_HOURS[kind])
        ).isoformat(),
        "status": "satisfied",
        "claims": dict(claims),
        "source_digests": [
            {
                "role": "producer_source",
                "schema_version": (
                    CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION
                ),
                "record_type": _CAPABILITY_SOURCE_RECORD_TYPE,
                "sha256": source_sha256,
            }
        ],
        "producer_version": _CAPABILITY_PRODUCER_VERSION,
        "policy_fingerprint": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        ),
        "bundle_fingerprint": "",
        "authority": dict(_CAPABILITY_AUTHORITY),
        "profit_claim": "none",
    }


def _venue_claims(venue: Mapping[str, object], symbol: str) -> dict[str, object]:
    records = _mapping_sequence(venue["records"], "venue.records")
    record = next(item for item in records if item.get("symbol") == symbol)
    return {
        "venue": "alpaca_crypto_paper",
        "tradable": True,
        "orderable": True,
        "notional_orders_supported": True,
        "minimum_notional_usd": _decimal_text(
            _decimal(record.get("min_notional"), "min_notional")
        ),
        "maximum_notional_supported_usd": "10",
        "paper_endpoint": True,
        "live_endpoint": False,
    }


def _lifecycle_claims(
    mechanics: Mapping[str, object],
    flat: Mapping[str, object],
) -> dict[str, object]:
    return {
        "mechanics_certified": True,
        "tested_notional_ceiling_usd": mechanics[
            "tested_notional_ceiling_usd"
        ],
        "entry_submit_attempts": 1,
        "exit_submit_attempts": 1,
        "cancel_attempts_max_per_order": 1,
        "replacement_attempts": 0,
        "flat_reconciliation_completed": True,
        "final_position_count": flat["final_position_count"],
        "final_open_order_count": flat["final_open_order_count"],
        "broker_ambiguity": flat["broker_ambiguity"],
    }


def _kill_claims() -> dict[str, object]:
    return {
        "durable": True,
        "default_paused": True,
        "restart_persists_halt": True,
        "loss_halt_usd": "2",
        "stale_data_blocks_entry": True,
        "loss_breach_blocks_entry": True,
        "unexpected_state_blocks_entry": True,
        "broker_ambiguity_blocks_entry": True,
        "expiry_blocks_entry": True,
        "cancel_exit_path_certified": True,
        "test_passed": True,
    }


def _production_status(
    *,
    as_of: datetime,
    classification: str,
    terminal_binding: Mapping[str, object],
    source_results: Mapping[str, Mapping[str, object]],
    capability_results: Mapping[str, Mapping[str, object]],
    bundle_fingerprint: str,
    review_preview: Mapping[str, object],
    blockers: Sequence[str],
    next_action: str,
) -> dict[str, object]:
    status: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
        ),
        "record_type": "crypto_bounded_probe_capability_production_status",
        "as_of": as_of.isoformat(),
        "classification": classification,
        "v5_26_preregistration_fingerprint": (
            CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        ),
        "terminal_binding": dict(terminal_binding),
        "source_results": {
            key: dict(value) for key, value in source_results.items()
        },
        "capability_results": {
            key: dict(value) for key, value in capability_results.items()
        },
        "capability_bundle_emitted": bool(bundle_fingerprint),
        "capability_bundle_fingerprint": bundle_fingerprint,
        "review_preview_classification": review_preview["classification"],
        "review_preview_fingerprint": review_preview["review_fingerprint"],
        "blockers": list(dict.fromkeys(blockers)),
        "next_action": next_action,
        "profit_claim": "none",
        **_STATUS_FALSE_AUTHORITY,
    }
    fingerprint_basis = {
        key: value for key, value in status.items() if key != "as_of"
    }
    status["status_fingerprint"] = _stable_hash(fingerprint_basis)
    _validate_status(status)
    return status


def _validate_status(status: Mapping[str, object]) -> None:
    if (
        set(status) != _STATUS_KEYS
        or status.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
        or status.get("record_type")
        != "crypto_bounded_probe_capability_production_status"
        or status.get("v5_26_preregistration_fingerprint")
        != CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        or status.get("profit_claim") != "none"
        or any(status.get(key) is not False for key in _STATUS_FALSE_AUTHORITY)
    ):
        raise ValidationError("capability production status identity mismatch.")
    _utc_datetime(status.get("as_of"), "status.as_of")
    fingerprint = _sha256(status.get("status_fingerprint"), "status_fingerprint")
    basis = {
        key: value
        for key, value in status.items()
        if key not in {"as_of", "status_fingerprint"}
    }
    if fingerprint != _stable_hash(basis):
        raise ValidationError("capability production status fingerprint mismatch.")
    emitted = status.get("capability_bundle_emitted") is True
    if emitted != bool(status.get("capability_bundle_fingerprint")):
        raise ValidationError("capability production bundle status drifted.")


def _terminal_binding(
    terminal_evidence: Mapping[str, object] | None,
) -> dict[str, object]:
    if terminal_evidence is None:
        return {
            "selected_candidate": {},
            "selected_symbol": "",
            "terminal_evidence_fingerprint": "",
            "evidence_export_fingerprint": "",
        }
    source = terminal_evidence.get("source_binding")
    binding = source if isinstance(source, Mapping) else {}
    candidate = terminal_evidence.get("selected_candidate")
    return {
        "selected_candidate": dict(candidate) if isinstance(candidate, Mapping) else {},
        "selected_symbol": str(terminal_evidence.get("selected_symbol", "")),
        "terminal_evidence_fingerprint": str(
            binding.get("terminal_evidence_fingerprint", "")
        ),
        "evidence_export_fingerprint": str(
            terminal_evidence.get("evidence_export_fingerprint", "")
        ),
    }


def _selected_symbol(terminal_evidence: Mapping[str, object]) -> str:
    symbol = str(terminal_evidence.get("selected_symbol", "")).strip().upper()
    candidate = terminal_evidence.get("selected_candidate")
    if (
        symbol not in _SUPPORTED_SYMBOLS
        or not isinstance(candidate, Mapping)
        or candidate.get("symbol") != symbol
    ):
        raise ValidationError("terminal winner symbol binding is invalid.")
    return symbol


def _source_results(raw: Mapping[str, bytes]) -> dict[str, dict[str, object]]:
    return {
        role: {
            "status": (
                "captured"
                if isinstance(raw.get(role), bytes) and bool(raw.get(role))
                else "missing"
            ),
            "sha256": (
                hashlib.sha256(raw[role]).hexdigest()
                if isinstance(raw.get(role), bytes) and raw.get(role)
                else ""
            ),
        }
        for role in _INPUT_ARTIFACT_PATHS
    }


def _publish_production(
    root: Path,
    production: CryptoBoundedProbeCapabilityProduction,
) -> dict[str, object]:
    _assert_safe_tree_path(root, root, must_exist=False)
    root.mkdir(parents=True, exist_ok=True)
    _assert_safe_tree_path(root, root, must_exist=True)
    with _exclusive_lock(root):
        artifact_sha256 = {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in production.artifacts.items()
        }
        publication_fingerprint = _stable_hash(artifact_sha256)
        generation = root / "generations" / publication_fingerprint
        for raw_name, payload in production.artifacts.items():
            name = _safe_relative_name(raw_name)
            destination = generation / PurePosixPath(name)
            _assert_safe_tree_path(root, destination, must_exist=False)
            _write_immutable_bytes(destination, payload)
        manifest: dict[str, object] = {
            "schema_version": (
                CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
            ),
            "record_type": (
                "crypto_bounded_probe_capability_production_generation"
            ),
            "publication_fingerprint": publication_fingerprint,
            "status_fingerprint": production.status["status_fingerprint"],
            "classification": production.status["classification"],
            "as_of": production.status["as_of"],
            "artifact_sha256": artifact_sha256,
            "broker_mutation_authorized": False,
            "paper_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_authorized": False,
        }
        manifest_bytes = _json_bytes(manifest)
        _assert_safe_tree_path(
            root,
            generation / "generation_manifest.json",
            must_exist=False,
        )
        _write_immutable_bytes(
            generation / "generation_manifest.json",
            manifest_bytes,
        )
        pointer_basis: dict[str, object] = {
            "schema_version": (
                CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
            ),
            "record_type": "crypto_bounded_probe_capability_latest_pointer",
            "publication_fingerprint": publication_fingerprint,
            "generation_relative_path": (
                f"generations/{publication_fingerprint}"
            ),
            "generation_manifest_sha256": hashlib.sha256(
                manifest_bytes
            ).hexdigest(),
            "status_fingerprint": production.status["status_fingerprint"],
            "classification": production.status["classification"],
            "as_of": production.status["as_of"],
            "broker_mutation_authorized": False,
            "paper_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_authorized": False,
        }
        pointer = {
            **pointer_basis,
            "pointer_fingerprint": _stable_hash(pointer_basis),
        }
        if set(pointer) != _LATEST_POINTER_KEYS:
            raise ValidationError("capability latest pointer schema drifted.")
        _assert_safe_tree_path(
            root,
            root / "latest_manifest.json",
            must_exist=False,
        )
        _write_bytes_atomic(root / "latest_manifest.json", _json_bytes(pointer))
        return pointer


@contextmanager
def _exclusive_lock(root: Path) -> Iterator[None]:
    lock_path = root / ".capability_production.lock"
    _assert_safe_tree_path(root, lock_path, must_exist=False)
    stream = lock_path.open("a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        _lock_stream(stream)
        yield
    finally:
        _unlock_stream(stream)
        stream.close()


def _lock_stream(stream: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        return
    import fcntl  # pragma: no cover

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)


def _unlock_stream(stream: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl  # pragma: no cover

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _read_optional_source(path: Path | str, role: str) -> bytes | None:
    local = _local_path(path, role)
    if not local.exists():
        return None
    _assert_safe_tree_path(local, local, must_exist=True)
    return _read_regular_bytes(local, role)


def _read_regular_bytes(path: Path, field_name: str) -> bytes:
    if not path.is_file() or _is_link_or_reparse(path):
        raise ValidationError(f"{field_name} must be a regular local file.")
    payload = path.read_bytes()
    if not payload:
        raise ValidationError(f"{field_name} cannot be empty.")
    return payload


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & 0x400)


def _assert_safe_descendant(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValidationError("capability artifact escaped its generation.") from exc
    cursor = root
    if _is_link_or_reparse(cursor):
        raise ValidationError("capability generation uses a link or reparse point.")
    for part in relative.parts:
        cursor = cursor / part
        if (cursor.exists() or cursor.is_symlink()) and _is_link_or_reparse(
            cursor
        ):
            raise ValidationError(
                "capability artifact uses a link or reparse point."
            )
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise ValidationError("capability artifact escaped its generation.") from exc


def _assert_safe_tree_path(
    root: Path,
    path: Path,
    *,
    must_exist: bool,
) -> None:
    """Reject links/reparse points in the configured tree and its ancestors."""

    root = Path(os.path.abspath(root))
    path = Path(os.path.abspath(path))
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValidationError("capability path escaped its configured root.") from exc
    for ancestor in (root, *root.parents):
        if (ancestor.exists() or ancestor.is_symlink()) and _is_link_or_reparse(
            ancestor
        ):
            raise ValidationError(
                "capability root uses a link or reparse point."
            )
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if (cursor.exists() or cursor.is_symlink()) and _is_link_or_reparse(
            cursor
        ):
            raise ValidationError(
                "capability path uses a link or reparse point."
            )
    if must_exist:
        try:
            path.resolve(strict=True).relative_to(root.resolve(strict=True))
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            raise ValidationError(
                "capability path escaped its configured root."
            ) from exc


def _actual_artifact_names(generation: Path) -> set[str]:
    names: set[str] = set()
    root_manifest = generation / "generation_manifest.json"
    for path in generation.rglob("*"):
        _assert_safe_descendant(generation, path)
        if path.is_file() and path != root_manifest:
            names.add(path.relative_to(generation).as_posix())
    return names


def _safe_relative_name(value: object) -> str:
    text = str(value)
    path = PurePosixPath(text)
    normalized = path.as_posix()
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{number}"
        for prefix in ("COM", "LPT")
        for number in range(1, 10)
    }
    unsafe_component = any(
        ":" in part
        or part.endswith((".", " "))
        or part.rstrip(". ").split(".", 1)[0].upper() in reserved
        or any(ord(character) < 32 or ord(character) == 127 for character in part)
        for part in path.parts
    )
    if (
        not text
        or "\\" in text
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or unsafe_component
        or text != normalized
    ):
        raise ValidationError("capability artifact path is unsafe.")
    return normalized


def _path_basename(value: object) -> str:
    text = str(value or "").replace("\\", "/").rstrip("/")
    return text.rsplit("/", 1)[-1] if text else ""


def _json_mapping(payload: bytes, field_name: str) -> dict[str, object]:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"{field_name} contains duplicate JSON keys.")
            result[key] = value
        return result

    try:
        parsed = json.loads(payload.decode("utf-8"), object_pairs_hook=pairs_hook)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{field_name} is not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValidationError(f"{field_name} must be a JSON object.")
    return parsed


def _require_canonical_json(
    payload: bytes,
    parsed: Mapping[str, object],
    field_name: str,
) -> None:
    if payload != _json_bytes(parsed):
        raise ValidationError(f"{field_name} is not canonical JSON.")


def _mapping_sequence(value: object, field_name: str) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{field_name} must be a sequence.")
    if any(not isinstance(item, Mapping) for item in value):
        raise ValidationError(f"{field_name} must contain mappings.")
    return tuple(value)  # type: ignore[return-value]


def _mapping(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return dict(value)


def _string_sequence(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError("expected a string sequence.")
    if any(not isinstance(item, str) for item in value):
        raise ValidationError("expected a string sequence.")
    return tuple(value)


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValidationError(f"{field_name} must be a decimal.")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a decimal.") from exc
    if not parsed.is_finite() or abs(parsed) > Decimal("1000000000"):
        raise ValidationError(f"{field_name} is outside the accepted range.")
    return parsed


def _decimal_text(value: Decimal) -> str:
    text = format(value.quantize(Decimal("0.00000001")), "f").rstrip("0").rstrip(".")
    return text or "0"


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO-8601.") from exc
    else:
        raise ValidationError(f"{field_name} must be a datetime.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f"{field_name} is outside the UTC range.") from exc


def _sha256(value: object, field_name: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValidationError(f"{field_name} must be a SHA-256 digest.")
    return text


def _stable_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _local_path(value: Path | str, field_name: str) -> Path:
    text = str(value).strip()
    if not text or "://" in text or text.startswith(("\\\\", "//")):
        raise ValidationError(f"{field_name} must be a local filesystem path.")
    return Path(text)


def _write_immutable_bytes(path: Path, payload: bytes) -> None:
    if _is_link_or_reparse(path):
        raise ValidationError("immutable capability artifact uses a link.")
    if path.is_file():
        if path.read_bytes() != payload:
            raise ValidationError("immutable capability artifact conflicts.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists() or temporary.is_symlink():
        if _is_link_or_reparse(temporary):
            raise ValidationError("capability temporary path uses a link.")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    if _is_link_or_reparse(path):
        raise ValidationError("capability atomic destination uses a link.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists() or temporary.is_symlink():
        if _is_link_or_reparse(temporary):
            raise ValidationError("capability temporary path uses a link.")
    try:
        temporary.write_bytes(payload)
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
        "--output-root",
        default=str(CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--venue-orderability-path",
        default=(
            "runs/crypto_universe_refresh/paper_read_latest/"
            "crypto_orderability_metadata.json"
        ),
    )
    parser.add_argument(
        "--submit-cancel-receipt-path",
        default=(
            "runs/crypto_paper_submit_cancel_certification/latest/"
            "certification_result.json"
        ),
    )
    parser.add_argument(
        "--fill-exit-receipt-path",
        default=(
            "runs/crypto_paper_fill_exit_certification/latest/"
            "fill_exit_certification_result.json"
        ),
    )
    parser.add_argument(
        "--independent-flat-reconciliation-path",
        default=(
            "runs/crypto_strategy_tournament/v2/"
            "bounded_paper_probe_capabilities/"
            "independent_flat_reconciliation.json"
        ),
    )
    parser.add_argument(
        "--safety-kernel-source-path",
        default="src/algotrader/execution/crypto_bounded_probe_safety.py",
    )
    parser.add_argument(
        "--safety-certifier-source-path",
        default=(
            "src/algotrader/execution/"
            "crypto_bounded_probe_safety_certification.py"
        ),
    )
    parser.add_argument(
        "--safety-focused-test-source-path",
        default="tests/unit/test_crypto_bounded_probe_safety.py",
    )
    parser.add_argument(
        "--safety-certification-receipt-path",
        default=(
            "runs/crypto_strategy_tournament/v2/"
            "bounded_paper_probe_capabilities/"
            "safety_certification_receipt.json"
        ),
    )
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--no-write", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = run_crypto_tournament_v2_bounded_paper_probe_capability_producer(
        shadow_root=args.shadow_root,
        output_root=args.output_root,
        venue_orderability_path=args.venue_orderability_path,
        submit_cancel_receipt_path=args.submit_cancel_receipt_path,
        fill_exit_receipt_path=args.fill_exit_receipt_path,
        independent_flat_reconciliation_path=(
            args.independent_flat_reconciliation_path
        ),
        safety_kernel_source_path=args.safety_kernel_source_path,
        safety_certifier_source_path=args.safety_certifier_source_path,
        safety_focused_test_source_path=args.safety_focused_test_source_path,
        safety_certification_receipt_path=(
            args.safety_certification_receipt_path
        ),
        as_of=args.as_of,
        write_artifacts=not args.no_write,
    )
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
