from __future__ import annotations

import ast
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_review as subject,
)
from algotrader.research.crypto_tournament_v2_forward_shadow import (
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT,
)
from algotrader.research.crypto_preregistered_tournament_v2 import (
    build_crypto_tournament_v2_preregistration,
)
from algotrader.research.crypto_tournament_v2_forward_shadow_state import (
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION,
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION,
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_TERMINAL_EVIDENCE_SCHEMA_VERSION,
)


AS_OF = datetime(2026, 8, 20, 1, tzinfo=UTC)
START = datetime(2026, 8, 13, tzinfo=UTC)
END = datetime(2026, 8, 20, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64


def _window_metrics(
    *,
    total_return: str,
    max_drawdown: str,
    transitions: int,
    round_trips: int,
    cost: str,
) -> dict[str, object]:
    return {
        "start": START.isoformat(),
        "end": (END - timedelta(hours=1)).isoformat(),
        "bar_count": 168,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "transition_count": transitions,
        "completed_round_trips": round_trips,
        "turnover": str(transitions),
        "estimated_cost_return": cost,
    }


def _passing_metrics() -> dict[str, object]:
    return {
        "initial_exposure": "0",
        "base_metrics": _window_metrics(
            total_return="0.95456618",
            max_drawdown="0.00898",
            transitions=2,
            round_trips=1,
            cost="0.008",
        ),
        "stress_metrics": _window_metrics(
            total_return="0.93889838",
            max_drawdown="0.01296",
            transitions=2,
            round_trips=1,
            cost="0.016",
        ),
        "cash_total_return": "0",
        "same_symbol_buy_hold": {
            "gross_total_return": "-0.99",
            "base_metrics": _window_metrics(
                total_return="-0.99004",
                max_drawdown="0.995",
                transitions=1,
                round_trips=0,
                cost="0.004",
            ),
            "stress_metrics": _window_metrics(
                total_return="-0.99008",
                max_drawdown="0.995",
                transitions=1,
                round_trips=0,
                cost="0.008",
            ),
        },
        "base_excess_vs_buy_hold": "1.94460618",
        "stress_excess_vs_buy_hold": "1.92897838",
        "decision_log_expected_rows": 168,
        "decision_log_observed_rows": 168,
        "decision_log_missing_rows": 0,
        "decision_log_duplicate_rows": 0,
        "decision_log_complete": True,
        "no_forced_terminal_liquidation": True,
        "paper_probe_authorized": False,
        "live_probe_authorized": False,
    }


def _terminal_evidence(
    *,
    classification: str = "evidence_complete_for_bounded_paper_probe_review",
    metrics: dict[str, object] | None = None,
    symbol: str = "BTCUSD",
) -> dict[str, object]:
    eligible = classification == (
        "evidence_complete_for_bounded_paper_probe_review"
    )
    quality_errors = [] if eligible else ["shadow_raw_coverage_below_threshold"]
    candidates = build_crypto_tournament_v2_preregistration()["candidates"]
    candidate = next(
        item
        for item in candidates
        if item["symbol"] == symbol
        and item["strategy_id"] == "trend_momentum_72h"
    )
    warmup_quality = {
        "phase": "activation_warmup",
        "status": "passed",
        "start": START.isoformat(),
        "end_exclusive": START.isoformat(),
        "expected_raw_rows": 0,
        "observed_raw_rows": 0,
        "raw_coverage": "0",
        "positive_raw_volume_fraction": "0",
        "missing_timestamps": [],
        "maximum_consecutive_missing_hours": 0,
        "imputed_rows": 0,
    }
    shadow_quality = {
        "phase": "shadow",
        "status": "passed" if eligible else "failed",
        "symbol": symbol,
        "start": START.isoformat(),
        "end_exclusive": END.isoformat(),
        "expected_raw_rows": 168,
        "observed_raw_rows": 168 if eligible else 167,
        "raw_coverage": "1" if eligible else "0.99404762",
        "positive_raw_volume_fraction": "1",
        "missing_timestamps": (
            [] if eligible else [(START + timedelta(hours=1)).isoformat()]
        ),
        "maximum_consecutive_missing_hours": 0 if eligible else 1,
        "imputed_rows": 0 if eligible else 1,
        "isolated_gap_fill": "prior_close_ohlc_zero_volume",
    }
    identity: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_TERMINAL_EVIDENCE_SCHEMA_VERSION
        ),
        "record_type": (
            "crypto_tournament_v2_forward_shadow_terminal_evidence"
        ),
        "classification": classification,
        "review_eligible_source": eligible,
        "terminal_scoring_performed": eligible,
        "selected_candidate": deepcopy(candidate),
        "selected_symbol": symbol,
        "shadow_window": {
            "start": START.isoformat(),
            "end_exclusive": END.isoformat(),
            "hourly_bars": 168,
            "checkpoint_hours": [24, 72, 168],
        },
        "progress": {
            "activation_warmup_expected_rows": 0,
            "activation_warmup_raw_rows": 0,
            "shadow_expected_rows": 168,
            "shadow_raw_rows": 168 if eligible else 167,
            "shadow_normalized_rows": 168,
            "decision_log_rows": 168,
            "completed_checkpoint_hours": [24, 72, 168],
        },
        "terminal_input_quality": {
            "activation_warmup": warmup_quality,
            "shadow": shadow_quality,
            "errors": quality_errors,
        },
        "terminal_metrics": (
            deepcopy(metrics if metrics is not None else _passing_metrics())
            if eligible
            else {}
        ),
        "source_binding": {
            "preregistration_fingerprint": (
                CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT
            ),
            "state_schema_version": (
                CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION
            ),
            "packet_schema_version": (
                CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION
            ),
            "activation_fingerprint": SHA_B,
            "activation_source_state_fingerprint": SHA_C,
            "state_fingerprint": SHA_D,
            "context_sha256": SHA_E,
            "terminal_packet_sha256": SHA_F,
            "terminal_evidence_fingerprint": SHA_A,
            "terminal_closed_at": END.isoformat(),
            "artifact_sha256": {
                name: SHA_B
                for name in (
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
                )
            },
        },
        "safety": {
            "source_network_access_attempted": True,
            "source_market_data_fetch_occurred": True,
            "broker_read_occurred": False,
            "broker_mutation_authorized": False,
            "broker_mutation_occurred": False,
            "paper_probe_authorized": False,
            "paper_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_authorized": False,
            "live_endpoint_touched": False,
            "credential_values_exposed": False,
            "profit_claim": "none",
        },
    }
    return {
        **identity,
        "as_of": END.isoformat(),
        "evidence_export_fingerprint": subject._stable_hash(identity),
    }


def _capability_claims(kind: str) -> dict[str, object]:
    if kind == "venue_orderability":
        return {
            "venue": "alpaca_crypto_paper",
            "tradable": True,
            "orderable": True,
            "notional_orders_supported": True,
            "minimum_notional_usd": "1",
            "maximum_notional_supported_usd": "10",
            "paper_endpoint": True,
            "live_endpoint": False,
        }
    if kind == "bounded_order_policy":
        return {
            "policy_version": subject._BOUNDED_ORDER_POLICY_SNAPSHOT_VERSION,
            "symbol_allowlisted": True,
            "sizing_basis": "notional",
            "minimum_notional_usd": "10",
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
        }
    if kind == "lifecycle_flat_reconciliation":
        return {
            "mechanics_certified": True,
            "tested_notional_ceiling_usd": "25",
            "entry_submit_attempts": 1,
            "exit_submit_attempts": 1,
            "cancel_attempts_max_per_order": 1,
            "replacement_attempts": 0,
            "flat_reconciliation_completed": True,
            "final_position_count": 0,
            "final_open_order_count": 0,
            "broker_ambiguity": False,
        }
    assert kind == "durable_kill_loss_control"
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


def _upstream_artifacts(
    kind: str,
    *,
    symbol: str,
    observed_at: datetime,
) -> dict[str, dict[str, object]]:
    subject_payload = {
        "asset_class": "crypto",
        "symbol": symbol,
        "environment": "alpaca_paper",
    }
    authority = {
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
    }
    if kind == "venue_orderability":
        return {
            "orderability_metadata": {
                "schema_version": "v5_1_crypto_universe_refresh_v1",
                "record_type": "crypto_orderability_metadata",
                "as_of": observed_at.isoformat(),
                "asset_class": "crypto",
                "broker_state_mode": "alpaca_paper_observed",
                "resolved_source_sha256": SHA_D,
                "resolved_source_digests": {},
                "records": [
                    {
                        "asset_class": "crypto",
                        "source_mode": "paper_read_only",
                        "broker_state_mode": "alpaca_paper_observed",
                        "metadata_status": "metadata_observed",
                        "orderability_status": "notional_orderable",
                        "orderability_basis": (
                            "broker_notional_and_qty_metadata"
                        ),
                        "status": "active",
                        "symbol": symbol,
                        "tradable": True,
                        "min_notional": "1.00",
                        "min_order_notional": "",
                        "min_order_size": "0.0001",
                        "min_trade_increment": "0.00000001",
                        "price_increment": "",
                        "qty_increment": "",
                        "broker_observed_min_notional": "1.00",
                        "broker_observed_min_order_size": "0.0001",
                        "broker_observed_min_trade_increment": "0.00000001",
                        "broker_observed_price_increment": "",
                        "derived_min_order_value": "1.00",
                        "metadata_blockers": [],
                        "orderability_blockers": [],
                    }
                ],
            }
        }
    if kind == "bounded_order_policy":
        return {
            "canonical_order_policy_snapshot": {
                "schema_version": subject._BOUNDED_ORDER_POLICY_SNAPSHOT_VERSION,
                "record_type": "crypto_bounded_order_policy_snapshot",
                "as_of": observed_at.isoformat(),
                "subject": subject_payload,
                "claims": _capability_claims(kind),
                "source_code_sha256": SHA_D,
                "resolved_source_digests": {},
                "authority": authority,
                "profit_claim": "none",
            }
        }
    if kind == "lifecycle_flat_reconciliation":
        account_binding = build_alpaca_paper_account_binding(
            {
                "account_id": "synthetic-review-paper-account",
                "id": "synthetic-review-paper-account",
            },
            expected_account_configured=True,
            expected_account_matched=True,
        )
        return {
            "lifecycle_mechanics_certification": {
                "schema_version": (
                    "v5_26_crypto_lifecycle_mechanics_certification_v1"
                ),
                "record_type": (
                    "crypto_lifecycle_mechanics_certification_result"
                ),
                "as_of": observed_at.isoformat(),
                "last_broker_mutation_at": observed_at.isoformat(),
                "subject": subject_payload,
                "mechanics_certified": True,
                "tested_notional_ceiling_usd": "25.00",
                "entry_submit_attempts": 1,
                "exit_submit_attempts": 1,
                "cancel_attempts_max_per_order": 1,
                "replacement_attempts": 0,
                "broker_ambiguity": False,
                "account_binding": account_binding,
                "paper_only": True,
                "live_endpoint_touched": False,
                "resolved_source_digests": {},
                "provenance_classification": (
                    "local_hash_coherent_legacy_reconstruction"
                ),
                "authority": authority,
                "profit_claim": "none",
            },
            "independent_flat_reconciliation": {
                "schema_version": (
                    "v5_26_crypto_independent_flat_reconciliation_v1"
                ),
                "record_type": (
                    "crypto_independent_flat_reconciliation_result"
                ),
                "as_of": observed_at.isoformat(),
                "subject": subject_payload,
                "account_binding": account_binding,
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
                "resolved_source_sha256": SHA_D,
                "validator_source_sha256": SHA_E,
                "authority": authority,
                "profit_claim": "none",
            },
        }
    assert kind == "durable_kill_loss_control"
    return {
        "durable_kill_loss_certification": {
            "schema_version": (
                "v5_26_crypto_durable_kill_loss_certification_v1"
            ),
            "record_type": (
                "crypto_durable_kill_loss_certification_result"
            ),
            "as_of": observed_at.isoformat(),
            "subject": subject_payload,
            "claims": _capability_claims(kind),
            "offline_test_receipt_sha256": SHA_E,
            "resolved_source_digests": {},
            "authority": authority,
            "profit_claim": "none",
        }
    }


def _capability_source(
    kind: str,
    *,
    upstream_hashes: dict[str, str],
    symbol: str = "BTCUSD",
    observed_at: datetime | None = None,
) -> dict[str, object]:
    observed = observed_at or (AS_OF - timedelta(hours=1))
    authority = {
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
    }
    unsigned: dict[str, object] = {
        "schema_version": (
            subject.CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION
        ),
        "record_type": subject._CAPABILITY_SOURCE_RECORD_TYPE,
        "evidence_kind": kind,
        "source_role": "producer_source",
        "subject": {
            "asset_class": "crypto",
            "symbol": symbol,
            "environment": "alpaca_paper",
        },
        "observed_at": observed.isoformat(),
        "valid_until": (
            observed
            + timedelta(hours=subject._CAPABILITY_MAX_AGE_HOURS[kind])
        ).isoformat(),
        "claims": _capability_claims(kind),
        "upstream_source_digests": [
            {
                "role": role,
                "schema_version": schema_version,
                "record_type": record_type,
                "sha256": upstream_hashes[role],
            }
            for role, schema_version, record_type in (
                subject._CAPABILITY_UPSTREAM_SOURCE_CONTRACTS[kind]
            )
        ],
        "producer_version": subject._CAPABILITY_PRODUCER_VERSION,
        "policy_fingerprint": (
            subject.CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        ),
        "authority": authority,
        "profit_claim": "none",
    }
    return {**unsigned, "source_fingerprint": subject._stable_hash(unsigned)}


def _capability_unsigned(
    kind: str,
    *,
    source_sha256: str,
    symbol: str,
    observed_at: datetime,
) -> dict[str, object]:
    unsigned: dict[str, object] = {
        "schema_version": (
            subject.CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SCHEMA_VERSION
        ),
        "record_type": (
            "crypto_tournament_v2_bounded_paper_probe_capability_evidence"
        ),
        "evidence_kind": kind,
        "subject": {
            "asset_class": "crypto",
            "symbol": symbol,
            "environment": "alpaca_paper",
        },
        "observed_at": observed_at.isoformat(),
        "valid_until": (
            observed_at
            + timedelta(hours=subject._CAPABILITY_MAX_AGE_HOURS[kind])
        ).isoformat(),
        "status": "satisfied",
        "claims": _capability_claims(kind),
        "source_digests": [
            {
                "role": "producer_source",
                "schema_version": (
                    subject.CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_CAPABILITY_SOURCE_SCHEMA_VERSION
                ),
                "record_type": subject._CAPABILITY_SOURCE_RECORD_TYPE,
                "sha256": source_sha256,
            }
        ],
        "producer_version": subject._CAPABILITY_PRODUCER_VERSION,
        "policy_fingerprint": (
            subject.CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_PREREGISTRATION_FINGERPRINT
        ),
        "bundle_fingerprint": "",
        "authority": {
            "paper_submit_authorized": False,
            "broker_mutation_authorized": False,
            "capital_allocation_authorized": False,
            "live_authorized": False,
        },
        "profit_claim": "none",
    }
    return unsigned


def _capability_bundle(
    *,
    symbol: str = "BTCUSD",
    symbol_overrides: dict[str, str] | None = None,
    observed_overrides: dict[str, datetime] | None = None,
    lifecycle_mechanics_observed_at: datetime | None = None,
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, str],
    dict[str, dict[str, object]],
    dict[str, str],
    dict[str, dict[str, dict[str, object]]],
    dict[str, dict[str, str]],
]:
    symbols = symbol_overrides or {}
    observed = observed_overrides or {}
    upstreams = {
        kind: _upstream_artifacts(
            kind,
            symbol=symbols.get(kind, symbol),
            observed_at=observed.get(kind, AS_OF - timedelta(hours=1)),
        )
        for kind in subject._CAPABILITY_KINDS
    }
    if lifecycle_mechanics_observed_at is not None:
        upstreams["lifecycle_flat_reconciliation"][
            "lifecycle_mechanics_certification"
        ]["as_of"] = lifecycle_mechanics_observed_at.isoformat()
    derived_observed = {
        kind: min(
            datetime.fromisoformat(str(payload["as_of"]))
            for payload in items.values()
        )
        for kind, items in upstreams.items()
    }
    upstream_hashes = {
        kind: {
            role: hashlib.sha256(
                subject._json_artifact_bytes(payload)
            ).hexdigest()
            for role, payload in items.items()
        }
        for kind, items in upstreams.items()
    }
    sources = {
        kind: _capability_source(
            kind,
            upstream_hashes=upstream_hashes[kind],
            symbol=symbols.get(kind, symbol),
            observed_at=derived_observed[kind],
        )
        for kind in subject._CAPABILITY_KINDS
    }
    source_hashes = {
        kind: hashlib.sha256(subject._json_artifact_bytes(payload)).hexdigest()
        for kind, payload in sources.items()
    }
    evidence = {
        kind: _capability_unsigned(
            kind,
            source_sha256=source_hashes[kind],
            symbol=symbols.get(kind, symbol),
            observed_at=derived_observed[kind],
        )
        for kind in subject._CAPABILITY_KINDS
    }
    bundle_fingerprint = subject._capability_bundle_fingerprint(evidence)
    for payload in evidence.values():
        payload["bundle_fingerprint"] = bundle_fingerprint
        payload["evidence_fingerprint"] = subject._stable_hash(payload)
    hashes = {
        kind: hashlib.sha256(subject._json_artifact_bytes(payload)).hexdigest()
        for kind, payload in evidence.items()
    }
    return (
        evidence,
        hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
    )


def _eligible_review_packet(*, symbol: str = "BTCUSD") -> dict[str, object]:
    (
        evidence,
        hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
    ) = _capability_bundle(symbol=symbol)
    return subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(symbol=symbol),
        capability_evidence=evidence,
        capability_artifact_sha256=hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF,
    )


def test_preregistration_is_frozen_before_terminal_evidence() -> None:
    contract = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_preregistration()
    )

    assert contract["preregistration_fingerprint"] == (
        "3b82ebcaf3c80b9c1fbda5797623b2e616dfef0a3ed38d2cc52c0b1d3151efb5"
    )
    assert contract["bounded_probe_envelope"]["maximum_notional_usd"] == "10"
    assert contract["bounded_probe_envelope"]["loss_halt_usd"] == "2"
    assert contract["authority_boundary"]["paper_probe_authorized"] is False
    assert contract["strategy_gate_policy"]["window_extension_allowed"] is False


def test_waiting_review_is_deterministic_and_denies_all_authority() -> None:
    first = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        None,
        as_of=AS_OF,
    )
    later = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        None,
        as_of=AS_OF + timedelta(hours=1),
    )

    assert first["classification"] == "waiting_for_v5_25_terminal_evidence"
    assert first["review_fingerprint"] == later["review_fingerprint"]
    assert first["admission_fingerprint"] == ""
    assert all(first[field] is False for field in subject._REVIEW_AUTHORITY_FIELDS)


def test_terminal_input_quality_gate_closes_without_metric_review() -> None:
    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(classification="terminal_shadow_input_quality_gate"),
        as_of=AS_OF,
    )

    assert packet["classification"] == (
        "closed_by_terminal_shadow_input_quality_gate"
    )
    assert packet["strategy_gate_results"] == []
    assert packet["admission_fingerprint"] == ""
    assert packet["paper_probe_authorized"] is False


def test_terminal_quality_gate_accepts_only_canonical_checkpoint_prefix() -> None:
    evidence = _terminal_evidence(
        classification="terminal_shadow_input_quality_gate"
    )
    progress = evidence["progress"]
    assert isinstance(progress, dict)
    progress["completed_checkpoint_hours"] = []
    identity = dict(evidence)
    identity.pop("as_of")
    identity.pop("evidence_export_fingerprint")
    evidence["evidence_export_fingerprint"] = subject._stable_hash(identity)

    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        evidence,
        as_of=AS_OF,
    )

    assert packet["classification"] == (
        "closed_by_terminal_shadow_input_quality_gate"
    )

    progress["completed_checkpoint_hours"] = [72]
    identity = dict(evidence)
    identity.pop("as_of")
    identity.pop("evidence_export_fingerprint")
    evidence["evidence_export_fingerprint"] = subject._stable_hash(identity)
    with pytest.raises(ValidationError, match="progress contract"):
        subject.build_crypto_tournament_v2_bounded_paper_probe_review(
            evidence,
            as_of=AS_OF,
        )


def test_positive_strategy_without_capabilities_is_operationally_blocked() -> None:
    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        as_of=AS_OF,
    )

    assert packet["classification"] == "blocked_by_operational_evidence"
    assert all(item["passed"] for item in packet["strategy_gate_results"])
    assert set(packet["blockers"]) == {
        f"{kind}_evidence_missing" for kind in subject._CAPABILITY_KINDS
    }
    assert packet["admission_fingerprint"] == ""


@pytest.mark.parametrize("symbol", ("BTCUSD", "ETHUSD", "SOLUSD"))
def test_all_capabilities_yield_operator_review_only_without_authority(
    symbol: str,
) -> None:
    evidence, hashes, sources, source_hashes, upstreams, upstream_hashes = (
        _capability_bundle(symbol=symbol)
    )
    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(symbol=symbol),
        capability_evidence=evidence,
        capability_artifact_sha256=hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF,
    )

    assert packet["classification"] == "eligible_for_operator_review_only"
    assert packet["admission_fingerprint"] == packet["review_fingerprint"]
    assert packet["approval_state"] == "not_authorized"
    assert packet["separate_exact_operator_authorization_required"] is True
    assert all(packet[field] is False for field in subject._REVIEW_AUTHORITY_FIELDS)


def test_admission_fingerprint_excludes_review_clock_within_validity() -> None:
    evidence, hashes, sources, source_hashes, upstreams, upstream_hashes = (
        _capability_bundle()
    )
    first = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        capability_evidence=evidence,
        capability_artifact_sha256=hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF,
    )
    second = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        capability_evidence=evidence,
        capability_artifact_sha256=hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF + timedelta(hours=1),
    )

    assert first["admission_fingerprint"] == second["admission_fingerprint"]


def test_persisted_eligible_review_binds_safety_fields_and_selected_symbol() -> None:
    packet = _eligible_review_packet()
    subject.validate_crypto_tournament_v2_bounded_paper_probe_review_packet(
        packet,
        as_of=AS_OF,
    )

    for field_name, value in (
        ("selected_symbol", "ETHUSD"),
        ("paper_submit_authorized", True),
        ("paper_mutation_authorized", True),
        ("broker_mutation_authorized", True),
        ("capital_allocation_authorized", True),
        ("live_authorized", True),
    ):
        tampered = deepcopy(packet)
        tampered[field_name] = value
        with pytest.raises(ValidationError):
            subject.validate_crypto_tournament_v2_bounded_paper_probe_review_packet(
                tampered,
                as_of=AS_OF,
            )


def test_eligible_review_expires_at_earliest_capability_boundary() -> None:
    packet = _eligible_review_packet()
    expiry = datetime.fromisoformat(str(packet["admission_valid_until"]))

    subject.validate_crypto_tournament_v2_bounded_paper_probe_review_packet(
        packet,
        as_of=expiry,
    )
    with pytest.raises(ValidationError, match="expired"):
        subject.validate_crypto_tournament_v2_bounded_paper_probe_review_packet(
            packet,
            as_of=expiry + timedelta(microseconds=1),
        )


def test_strategy_gate_evaluator_exactly_tracks_frozen_manifest_order() -> None:
    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        as_of=AS_OF,
    )
    contract = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_preregistration()
    )

    assert [item["gate_id"] for item in packet["strategy_gate_results"]] == [
        item["gate_id"] for item in contract["ordered_strategy_gates"]
    ]
    assert all(item["passed"] for item in packet["strategy_gate_results"])


def test_capability_bytes_source_chain_and_bundle_are_all_required() -> None:
    evidence, hashes, sources, source_hashes, upstreams, upstream_hashes = (
        _capability_bundle()
    )
    bad_hashes = dict(hashes)
    bad_hashes["venue_orderability"] = SHA_A
    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        capability_evidence=evidence,
        capability_artifact_sha256=bad_hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF,
    )
    assert packet["classification"] == "blocked_by_operational_evidence"
    assert "venue_orderability_evidence_invalid" in packet["blockers"]

    no_sources = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        capability_evidence=evidence,
        capability_artifact_sha256=hashes,
        as_of=AS_OF,
    )
    assert no_sources["classification"] == "blocked_by_operational_evidence"
    assert all(
        f"{kind}_evidence_invalid" in no_sources["blockers"]
        for kind in subject._CAPABILITY_KINDS
    )

    no_upstreams = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_review(
            _terminal_evidence(),
            capability_evidence=evidence,
            capability_artifact_sha256=hashes,
            capability_source_evidence=sources,
            capability_source_artifact_sha256=source_hashes,
            as_of=AS_OF,
        )
    )
    assert no_upstreams["classification"] == "blocked_by_operational_evidence"
    assert all(
        f"{kind}_evidence_invalid" in no_upstreams["blockers"]
        for kind in subject._CAPABILITY_KINDS
    )

    incoherent = deepcopy(evidence)
    incoherent["venue_orderability"]["bundle_fingerprint"] = SHA_B
    unsigned = dict(incoherent["venue_orderability"])
    unsigned.pop("evidence_fingerprint")
    incoherent["venue_orderability"]["evidence_fingerprint"] = (
        subject._stable_hash(unsigned)
    )
    incoherent_hashes = dict(hashes)
    incoherent_hashes["venue_orderability"] = hashlib.sha256(
        subject._json_artifact_bytes(incoherent["venue_orderability"])
    ).hexdigest()
    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        capability_evidence=incoherent,
        capability_artifact_sha256=incoherent_hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF,
    )
    assert "capability_bundle_incoherent" in packet["blockers"]


def test_zero_return_is_a_terminal_strategy_rejection() -> None:
    metrics = _passing_metrics()
    metrics["base_metrics"] = _window_metrics(
        total_return="0",
        max_drawdown="0",
        transitions=0,
        round_trips=0,
        cost="0",
    )
    metrics["stress_metrics"] = _window_metrics(
        total_return="0",
        max_drawdown="0",
        transitions=0,
        round_trips=0,
        cost="0",
    )
    metrics["base_excess_vs_buy_hold"] = "0.99004"
    metrics["stress_excess_vs_buy_hold"] = "0.99008"

    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(metrics=metrics),
        as_of=AS_OF,
    )

    assert packet["classification"] == (
        "rejected_by_preregistered_strategy_gates"
    )
    assert "base_return_strictly_positive" in packet["blockers"]
    assert "stress_return_strictly_positive" in packet["blockers"]
    assert packet["admission_fingerprint"] == ""


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("total_return", "0E-8"),
        ("total_return", "-0"),
        ("total_return", "NaN"),
        ("max_drawdown", 0),
    ),
)
def test_noncanonical_or_non_string_metrics_are_integrity_errors(
    field: str,
    value: object,
) -> None:
    evidence = _terminal_evidence()
    evidence["terminal_metrics"]["base_metrics"][field] = value
    identity = dict(evidence)
    identity.pop("as_of")
    identity.pop("evidence_export_fingerprint")
    evidence["evidence_export_fingerprint"] = subject._stable_hash(identity)

    with pytest.raises(ValidationError, match="canonical|canonically"):
        subject.build_crypto_tournament_v2_bounded_paper_probe_review(
            evidence,
            as_of=AS_OF,
        )


def test_tampered_terminal_export_fingerprint_is_rejected() -> None:
    evidence = _terminal_evidence()
    evidence["selected_symbol"] = "ETHUSD"

    with pytest.raises(ValidationError, match="export fingerprint mismatch"):
        subject.build_crypto_tournament_v2_bounded_paper_probe_review(
            evidence,
            as_of=AS_OF,
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "candidate",
        "window",
        "scoring",
        "quality",
        "quality_counts",
        "artifact_manifest",
        "extra_top_level",
    ),
)
def test_resigned_terminal_export_still_requires_exact_frozen_contract(
    mutation: str,
) -> None:
    evidence = _terminal_evidence()
    if mutation == "candidate":
        evidence["selected_candidate"]["strategy_id"] = "posthoc_variant"
    elif mutation == "window":
        evidence["shadow_window"]["end_exclusive"] = (
            END + timedelta(hours=1)
        ).isoformat()
    elif mutation == "scoring":
        evidence["terminal_scoring_performed"] = False
    elif mutation == "quality":
        evidence["terminal_input_quality"]["shadow"]["status"] = "failed"
    elif mutation == "quality_counts":
        quality = evidence["terminal_input_quality"]["shadow"]
        quality.update(
            {
                "status": "failed",
                "observed_raw_rows": 167,
                "raw_coverage": "0.99404762",
                "missing_timestamps": [START.isoformat()],
                "maximum_consecutive_missing_hours": 1,
                "imputed_rows": 0,
            }
        )
    elif mutation == "artifact_manifest":
        evidence["source_binding"]["artifact_sha256"]["unexpected"] = SHA_A
    else:
        evidence["unexpected"] = True
    identity = dict(evidence)
    identity.pop("as_of")
    identity.pop("evidence_export_fingerprint")
    evidence["evidence_export_fingerprint"] = subject._stable_hash(identity)

    with pytest.raises(ValidationError):
        subject.build_crypto_tournament_v2_bounded_paper_probe_review(
            evidence,
            as_of=AS_OF,
        )


def test_extreme_decimal_is_a_fail_closed_validation_error() -> None:
    evidence = _terminal_evidence()
    evidence["terminal_metrics"]["base_metrics"]["total_return"] = "1E+999999"
    identity = dict(evidence)
    identity.pop("as_of")
    identity.pop("evidence_export_fingerprint")
    evidence["evidence_export_fingerprint"] = subject._stable_hash(identity)

    with pytest.raises(ValidationError):
        subject.build_crypto_tournament_v2_bounded_paper_probe_review(
            evidence,
            as_of=AS_OF,
        )


def test_stale_or_wrong_symbol_capability_blocks_review() -> None:
    (
        evidence,
        hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
    ) = _capability_bundle(
        observed_overrides={
            "venue_orderability": AS_OF - timedelta(hours=25)
        },
        symbol_overrides={"bounded_order_policy": "ETHUSD"},
    )

    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        capability_evidence=evidence,
        capability_artifact_sha256=hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF,
    )

    assert packet["classification"] == "blocked_by_operational_evidence"
    assert "venue_orderability_evidence_invalid" in packet["blockers"]
    assert "bounded_order_policy_evidence_invalid" in packet["blockers"]


def test_stale_lifecycle_mechanics_cannot_borrow_fresh_reconciliation_time() -> None:
    (
        evidence,
        hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
    ) = _capability_bundle(
        lifecycle_mechanics_observed_at=AS_OF - timedelta(hours=721)
    )

    packet = subject.build_crypto_tournament_v2_bounded_paper_probe_review(
        _terminal_evidence(),
        capability_evidence=evidence,
        capability_artifact_sha256=hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=AS_OF,
    )

    assert packet["classification"] == "blocked_by_operational_evidence"
    assert (
        "lifecycle_flat_reconciliation_evidence_invalid"
        in packet["blockers"]
    )


def test_normalized_upstream_rejects_injected_authority_field() -> None:
    upstreams = _upstream_artifacts(
        "lifecycle_flat_reconciliation",
        symbol="BTCUSD",
        observed_at=AS_OF - timedelta(hours=1),
    )
    upstreams["lifecycle_mechanics_certification"][
        "paper_submit_authorized"
    ] = True

    with pytest.raises(ValidationError, match="identity mismatch"):
        subject._derive_capability_source_claims(
            "lifecycle_flat_reconciliation",
            subject={
                "asset_class": "crypto",
                "symbol": "BTCUSD",
                "environment": "alpaca_paper",
            },
            upstreams=upstreams,
        )


@pytest.mark.parametrize(
    "field",
    (
        "live_trading_permitted",
        "network_access_attempted",
        "credential_values_exposed",
    ),
)
def test_venue_upstream_rejects_injected_authority_field(field: str) -> None:
    upstreams = _upstream_artifacts(
        "venue_orderability",
        symbol="BTCUSD",
        observed_at=AS_OF - timedelta(hours=1),
    )
    upstreams["orderability_metadata"][field] = True

    with pytest.raises(ValidationError):
        subject._derive_capability_source_claims(
            "venue_orderability",
            subject={
                "asset_class": "crypto",
                "symbol": "BTCUSD",
                "environment": "alpaca_paper",
            },
            upstreams=upstreams,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_mode", "unverified"),
        ("orderability_basis", "asserted_only"),
        ("min_order_notional", "100"),
        ("broker_observed_min_notional", "2.00"),
        ("derived_min_order_value", "100"),
        ("price_increment", "0.01"),
    ),
)
def test_venue_upstream_rejects_semantically_unsafe_record(
    field: str,
    value: str,
) -> None:
    upstreams = _upstream_artifacts(
        "venue_orderability",
        symbol="BTCUSD",
        observed_at=AS_OF - timedelta(hours=1),
    )
    upstreams["orderability_metadata"]["records"][0][field] = value

    with pytest.raises(ValidationError, match="orderability is not proven"):
        subject._derive_capability_source_claims(
            "venue_orderability",
            subject={
                "asset_class": "crypto",
                "symbol": "BTCUSD",
                "environment": "alpaca_paper",
            },
            upstreams=upstreams,
        )


def test_flat_reconciliation_must_follow_final_broker_mutation() -> None:
    observed_at = AS_OF - timedelta(hours=1)
    upstreams = _upstream_artifacts(
        "lifecycle_flat_reconciliation",
        symbol="BTCUSD",
        observed_at=observed_at,
    )
    upstreams["lifecycle_mechanics_certification"][
        "last_broker_mutation_at"
    ] = (observed_at + timedelta(minutes=1)).isoformat()

    with pytest.raises(ValidationError, match="predates the final broker mutation"):
        subject._derive_capability_source_claims(
            "lifecycle_flat_reconciliation",
            subject={
                "asset_class": "crypto",
                "symbol": "BTCUSD",
                "environment": "alpaca_paper",
            },
            upstreams=upstreams,
        )


def test_lifecycle_upstream_rejects_injected_network_attempt_field() -> None:
    upstreams = _upstream_artifacts(
        "lifecycle_flat_reconciliation",
        symbol="BTCUSD",
        observed_at=AS_OF - timedelta(hours=1),
    )
    upstreams["lifecycle_mechanics_certification"][
        "network_access_attempted"
    ] = True

    with pytest.raises(ValidationError):
        subject._derive_capability_source_claims(
            "lifecycle_flat_reconciliation",
            subject={
                "asset_class": "crypto",
                "symbol": "BTCUSD",
                "environment": "alpaca_paper",
            },
            upstreams=upstreams,
        )


def test_offline_runner_waits_and_writes_only_local_review_artifacts(
    tmp_path: Path,
) -> None:
    output = tmp_path / "review"
    capability_root = tmp_path / "capabilities"
    capability_root.mkdir()
    (capability_root / "venue_orderability.json").write_text(
        "not valid json",
        encoding="utf-8",
    )
    packet = subject.run_crypto_tournament_v2_bounded_paper_probe_review(
        shadow_root=tmp_path / "missing_shadow",
        capability_root=capability_root,
        output_root=output,
        as_of=AS_OF,
    )

    assert packet["classification"] == "waiting_for_v5_25_terminal_evidence"
    latest = json.loads(
        (output / "latest_manifest.json").read_text(encoding="utf-8")
    )
    generation = output / latest["generation_relative_path"]
    assert (generation / "preregistration.json").is_file()
    assert json.loads(
        (generation / "review_packet.json").read_text(encoding="utf-8")
    ) == packet
    assert (generation / "review_packet.md").is_file()
    assert (generation / "generation_manifest.json").is_file()
    assert not (generation / "inputs" / "capabilities").exists()
    latest_basis = dict(latest)
    pointer_fingerprint = latest_basis.pop("pointer_fingerprint")
    assert pointer_fingerprint == subject._stable_hash(latest_basis)
    assert packet["network_access_attempted"] is False


def test_runner_resolves_canonical_capability_and_producer_source_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence, _, sources, _, upstreams, _ = _capability_bundle()
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    (shadow_root / "frozen_state.json").write_text("{}\n", encoding="utf-8")
    capability_root = tmp_path / "capabilities"
    for kind in subject._CAPABILITY_KINDS:
        capability_root.mkdir(parents=True, exist_ok=True)
        (capability_root / f"{kind}.json").write_bytes(
            subject._json_artifact_bytes(evidence[kind])
        )
        source_path = capability_root / "sources" / kind / "producer_source.json"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(subject._json_artifact_bytes(sources[kind]))
        for role, payload in upstreams[kind].items():
            upstream_path = (
                capability_root
                / "sources"
                / kind
                / "upstream"
                / f"{role}.json"
            )
            upstream_path.parent.mkdir(parents=True, exist_ok=True)
            upstream_path.write_bytes(subject._json_artifact_bytes(payload))
    monkeypatch.setattr(
        subject,
        "run_crypto_tournament_v2_forward_shadow_state",
        lambda **_: {"frozen_state": {"terminal_outcome_closed": True}},
    )
    monkeypatch.setattr(
        subject,
        "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
        lambda **_: _terminal_evidence(),
    )

    packet = subject.run_crypto_tournament_v2_bounded_paper_probe_review(
        shadow_root=shadow_root,
        capability_root=capability_root,
        output_root=tmp_path / "review",
        as_of=AS_OF,
    )

    assert packet["classification"] == "eligible_for_operator_review_only"
    assert packet["paper_mutation_authorized"] is False
    latest = json.loads(
        (tmp_path / "review" / "latest_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    generation = tmp_path / "review" / latest["generation_relative_path"]
    assert (generation / "inputs" / "terminal_evidence.json").is_file()
    for kind in subject._CAPABILITY_KINDS:
        assert (generation / "inputs" / "capabilities" / f"{kind}.json").is_file()
        assert (
            generation / "inputs" / "producer_sources" / f"{kind}.json"
        ).is_file()
        for role in upstreams[kind]:
            assert (
                generation
                / "inputs"
                / "upstreams"
                / kind
                / f"{role}.json"
            ).is_file()


def test_review_module_has_no_execution_network_or_order_construction() -> None:
    path = Path(
        "src/algotrader/orchestration/"
        "crypto_tournament_v2_bounded_paper_probe_review.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert all(not name.startswith("algotrader.execution") for name in imports)
    assert imports.isdisjoint(
        {"alpaca", "httpx", "requests", "socket", "subprocess", "urllib"}
    )
    assert calls.isdisjoint(
        {"ExecutionIntent", "ExecutionPlan", "submit_order", "cancel_order"}
    )
