
"""V5.30 target-family capability production with frozen legacy delegation.

This module is local-only and authority-free. It leaves the frozen V5.27
producer byte-exact, delegates an exact legacy input family to it, and admits a
separate exact V5.30 lifecycle/flat family without mixing or fallback.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from algotrader.core.crypto_bounded_probe_lifecycle import (
    BUDGETS,
    ENTRY_NOTIONAL_USD,
    LIFECYCLE_RECORD_TYPE,
    LIFECYCLE_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    SAFETY_POLICY_FINGERPRINT,
    SUPPORTED_SYMBOLS,
    canonical_json_bytes,
    stable_hash,
    validate_terminal_evidence_reference,
    utc_datetime,
    validate_lifecycle_plan,
)
from algotrader.core.paper_account_binding import (
    validate_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_capability_producer as legacy,
)


CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION = (
    legacy.CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
)
CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT = (
    legacy.CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT
)
CryptoBoundedProbeCapabilityProduction = (
    legacy.CryptoBoundedProbeCapabilityProduction
)

_LEGACY_INPUT_ARTIFACT_PATHS = dict(legacy._INPUT_ARTIFACT_PATHS)
_COMMON_TARGET_INPUT_ARTIFACT_PATHS = {
    role: _LEGACY_INPUT_ARTIFACT_PATHS[role]
    for role in (
        "venue_refresh_manifest",
        "venue_universe",
        "orderability_metadata",
        "venue_router_input_manifest",
        "venue_runtime_visibility_status",
        "venue_refresh_source",
        "venue_visibility_operator_source",
        "venue_supervisor_source",
        "independent_flat_reconciliation",
        "independent_flat_reconciliation_source",
        "account_binding_source",
        "capability_producer_source",
        "safety_kernel_source",
        "safety_certifier_source",
        "safety_focused_test_source",
        "safety_certification_receipt",
    )
}
_TARGET_ONLY_INPUT_ARTIFACT_PATHS = {
    "target_capability_producer_source": (
        "resolved_sources/producer/"
        "crypto_tournament_v2_bounded_paper_probe_capability_producer_v530.py"
    ),
    "target_lifecycle_plan": (
        "resolved_sources/lifecycle/v5_30_lifecycle_plan.json"
    ),
    "target_lifecycle_receipt": (
        "resolved_sources/lifecycle/v5_30_lifecycle_result.json"
    ),
    "target_lifecycle_manifest": (
        "resolved_sources/lifecycle/v5_30_lifecycle_manifest.json"
    ),
    "target_lifecycle_operator_source": (
        "resolved_sources/lifecycle/"
        "crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py"
    ),
    "independent_flat_status": (
        "resolved_sources/lifecycle/v5_29_independent_flat_status.json"
    ),
    "independent_flat_manifest": (
        "resolved_sources/lifecycle/v5_29_independent_flat_manifest.json"
    ),
    "independent_flat_operator_source": (
        "resolved_sources/lifecycle/"
        "crypto_bounded_probe_independent_flat_operator.py"
    ),
}
_TARGET_INPUT_ARTIFACT_PATHS = {
    **_COMMON_TARGET_INPUT_ARTIFACT_PATHS,
    **_TARGET_ONLY_INPUT_ARTIFACT_PATHS,
}
_INPUT_ARTIFACT_PATHS = _LEGACY_INPUT_ARTIFACT_PATHS

_THIS_FILE = Path(__file__).resolve()
_ALGOTRADER_ROOT = _THIS_FILE.parents[1]
_REPOSITORY_ROOT = _THIS_FILE.parents[3]
_TARGET_LOCAL_SOURCE_PATHS = {
    "capability_producer_source": Path(legacy.__file__).resolve(),
    "target_capability_producer_source": _THIS_FILE,
    "account_binding_source": (
        _ALGOTRADER_ROOT / "core" / "paper_account_binding.py"
    ),
    "independent_flat_reconciliation_source": (
        _ALGOTRADER_ROOT
        / "execution"
        / "crypto_bounded_probe_independent_flat_reconciliation.py"
    ),
    "venue_refresh_source": (
        _ALGOTRADER_ROOT / "orchestration" / "crypto_universe_refresh.py"
    ),
    "venue_visibility_operator_source": (
        _ALGOTRADER_ROOT / "execution" / "crypto_paper_visibility_operator.py"
    ),
    "venue_supervisor_source": (
        _ALGOTRADER_ROOT / "execution" / "crypto_paper_supervisor.py"
    ),
    "safety_kernel_source": (
        _ALGOTRADER_ROOT / "execution" / "crypto_bounded_probe_safety.py"
    ),
    "safety_certifier_source": (
        _ALGOTRADER_ROOT
        / "execution"
        / "crypto_bounded_probe_safety_certification.py"
    ),
    "safety_focused_test_source": (
        _REPOSITORY_ROOT
        / "tests"
        / "unit"
        / "test_crypto_bounded_probe_safety.py"
    ),
    "target_lifecycle_operator_source": (
        _ALGOTRADER_ROOT
        / "execution"
        / "crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py"
    ),
    "independent_flat_operator_source": (
        _ALGOTRADER_ROOT
        / "execution"
        / "crypto_bounded_probe_independent_flat_operator.py"
    ),
}
_TARGET_LOADED_SOURCE_SHA256 = {
    role: hashlib.sha256(path.read_bytes()).hexdigest()
    for role, path in _TARGET_LOCAL_SOURCE_PATHS.items()
}

_TARGET_LIFECYCLE_RECEIPT_KEYS = {
    "schema_version",
    "record_type",
    "as_of",
    "subject",
    "plan_fingerprint",
    "plan_source_sha256",
    "terminal_binding",
    "venue_binding",
    "safety_binding",
    "account_binding",
    "authorization",
    "operator_preflight",
    "deterministic_ids",
    "budgets",
    "entry_attempt_count",
    "cancel_attempt_count",
    "exit_attempt_count",
    "action_claim_fingerprints",
    "entry_final_order",
    "exit_final_order",
    "final_position_count",
    "final_open_order_count",
    "broker_read_occurred",
    "broker_mutation_performed",
    "paper_submit_performed",
    "paper_cancel_performed",
    "paper_replace_performed",
    "paper_close_performed",
    "paper_liquidate_performed",
    "broker_ambiguity",
    "outcome_classification",
    "blockers",
    "next_action",
    "paper_only",
    "live_endpoint_touched",
    "credential_values_exposed",
    "capital_allocation_authorized",
    "live_authorized",
    "profit_claim",
    "lifecycle_fingerprint",
}
_TARGET_LIFECYCLE_MANIFEST_KEYS = {
    "schema_version",
    "record_type",
    "as_of",
    "symbol",
    "plan_sha256",
    "receipt_sha256",
    "operator_source_sha256",
    "outcome_classification",
    "entry_attempt_count",
    "cancel_attempt_count",
    "exit_attempt_count",
    "paper_only",
    "live_endpoint_touched",
    "credential_values_exposed",
    "capital_allocation_authorized",
    "live_authorized",
    "manifest_fingerprint",
}
_TARGET_FLAT_MANIFEST_KEYS = {
    "schema_version",
    "record_type",
    "as_of",
    "symbol",
    "receipt_sha256",
    "status_sha256",
    "collector_source_sha256",
    "lifecycle_source_sha256",
    "broker_mutation_occurred",
    "paper_mutation_occurred",
    "live_endpoint_touched",
    "credential_values_exposed",
    "manifest_fingerprint",
}
_TARGET_AUTHORIZATION_KEYS = {
    "paper_mutation_authorized",
    "network_authorized",
    "exact_operation_authorization_matched",
    "authorization_fingerprint",
    "entry_authorization_valid_until",
    "risk_reducing_unwind_authorized_for_claimed_entry",
    "live_authorized",
    "capital_allocation_authorized",
}
_TARGET_PREFLIGHT_KEYS = {
    "APP_PROFILE_is_paper",
    "APP_PROFILE_is_live",
    "paper_credentials_present",
    "expected_paper_account_id_loaded",
    "paper_endpoint_exact_match_indicator",
    "live_endpoint_indicator",
    "network_test_flag_enabled",
    "ALPACA_API_KEY_present",
    "ALPACA_API_SECRET_KEY_present",
    "ALPACA_SECRET_KEY_present",
    "APCA_API_KEY_ID_present",
    "APCA_API_SECRET_KEY_present",
}
_TARGET_LIFECYCLE_PREFLIGHT_KEYS = {
    *_TARGET_PREFLIGHT_KEYS,
    "runtime_source_bundle_matched",
}
_TARGET_ORDER_KEYS = {
    "client_order_id",
    "broker_order_fingerprint",
    "symbol",
    "side",
    "asset_class",
    "order_type",
    "time_in_force",
    "limit_price",
    "status",
    "qty",
    "notional",
    "filled_qty",
    "filled_avg_price",
    "submitted_at",
    "filled_at",
    "order_fingerprint",
}
_TARGET_FLAT_STATUS_KEYS = {
    "schema_version",
    "record_type",
    "as_of",
    "subject",
    "lifecycle_source",
    "lifecycle_binding",
    "operator_preflight",
    "read_authorized",
    "network_authorized",
    "broker_read_occurred",
    "account_read_occurred",
    "positions_read_occurred",
    "open_orders_read_occurred",
    "broker_mutation_occurred",
    "paper_mutation_occurred",
    "live_endpoint_touched",
    "credential_values_exposed",
    "receipt_emitted",
    "receipt_fingerprint",
    "final_position_count",
    "final_open_order_count",
    "blockers",
    "classification",
    "next_action",
    "profit_claim",
    "status_fingerprint",
}
_TARGET_FLAT_LIFECYCLE_BINDING_KEYS = {
    "schema_version",
    "symbol",
    "account_binding",
    "exit_filled_at",
    "source_sha256",
}


__all__ = [
    "CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION",
    "CryptoBoundedProbeCapabilityProduction",
    "build_crypto_tournament_v2_bounded_paper_probe_capability_production",
    "load_crypto_tournament_v2_bounded_paper_probe_capability_generation",
    "run_crypto_tournament_v2_bounded_paper_probe_capability_producer",
    "main",
]


def build_crypto_tournament_v2_bounded_paper_probe_capability_production(
    terminal_evidence: Mapping[str, object] | None,
    *,
    resolved_input_bytes: Mapping[str, bytes],
    terminal_evidence_source_bytes: bytes | None = None,
    as_of: datetime | str,
) -> CryptoBoundedProbeCapabilityProduction:
    """Build an exact legacy or exact V5.30 family, never a mixed family."""

    evaluated_at = legacy._utc_datetime(as_of, "as_of")
    initial_review = (
        legacy.build_crypto_tournament_v2_bounded_paper_probe_review(
            terminal_evidence,
            as_of=evaluated_at,
        )
    )
    if initial_review["classification"] != "blocked_by_operational_evidence":
        return (
            legacy.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
                terminal_evidence,
                resolved_input_bytes=resolved_input_bytes,
                as_of=evaluated_at,
            )
        )
    family = _select_input_family_by_roles(resolved_input_bytes)
    if family == "legacy":
        return (
            legacy.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
                terminal_evidence,
                resolved_input_bytes=resolved_input_bytes,
                as_of=evaluated_at,
            )
        )
    if terminal_evidence is None:  # pragma: no cover
        raise ValidationError("selected winner terminal evidence is absent.")
    return _build_target_capability_production(
        terminal_evidence,
        terminal_evidence_source_bytes=terminal_evidence_source_bytes,
        resolved_input_bytes=resolved_input_bytes,
        as_of=evaluated_at,
        initial_review=initial_review,
    )


def _select_input_family_by_roles(raw: Mapping[str, bytes]) -> str:
    roles = set(raw)
    legacy_roles = set(_LEGACY_INPUT_ARTIFACT_PATHS)
    target_roles = set(_TARGET_INPUT_ARTIFACT_PATHS)
    if roles == legacy_roles:
        return "legacy"
    if roles == target_roles:
        return "target"
    target_only = set(_TARGET_ONLY_INPUT_ARTIFACT_PATHS)
    legacy_only = legacy_roles - set(_COMMON_TARGET_INPUT_ARTIFACT_PATHS)
    if roles & target_only and roles & legacy_only:
        raise ValidationError("mixed legacy and V5.30 input families are forbidden.")
    if roles & target_only:
        missing = sorted(target_roles - roles)
        extra = sorted(roles - target_roles)
        raise ValidationError(
            "partial V5.30 input family: missing="
            + ",".join(missing)
            + ";extra="
            + ",".join(extra)
        )
    if roles & legacy_only or roles:
        missing = sorted(legacy_roles - roles)
        extra = sorted(roles - legacy_roles)
        raise ValidationError(
            "partial legacy input family: missing="
            + ",".join(missing)
            + ";extra="
            + ",".join(extra)
        )
    raise ValidationError("an exact resolved input family is required.")


def _validated_terminal_evidence_bytes(
    terminal_evidence: Mapping[str, object],
    source_bytes: bytes | None,
) -> bytes:
    payload = (
        legacy._json_bytes(dict(terminal_evidence))
        if source_bytes is None
        else source_bytes
    )
    if not isinstance(payload, bytes) or not payload:
        raise ValidationError("terminal evidence source bytes are required.")
    parsed = legacy._json_mapping(payload, "terminal_evidence")
    legacy._require_canonical_json(
        payload,
        parsed,
        "terminal_evidence",
    )
    if parsed != dict(terminal_evidence):
        raise ValidationError(
            "terminal evidence source bytes do not match the mapping."
        )
    return payload


def _build_target_capability_production(
    terminal_evidence: Mapping[str, object],
    *,
    terminal_evidence_source_bytes: bytes | None,
    resolved_input_bytes: Mapping[str, bytes],
    as_of: datetime,
    initial_review: Mapping[str, object],
) -> CryptoBoundedProbeCapabilityProduction:
    symbol = legacy._selected_symbol(terminal_evidence)
    terminal_bytes = _validated_terminal_evidence_bytes(
        terminal_evidence,
        terminal_evidence_source_bytes,
    )
    artifacts: dict[str, bytes] = {
        "inputs/terminal_evidence.json": terminal_bytes
    }
    source_results = _target_source_results(resolved_input_bytes)
    blockers: list[str] = []
    review_preview = initial_review
    capability_results = initial_review["capability_results"]
    bundle_fingerprint = ""
    try:
        (
            capabilities,
            capability_hashes,
            sources,
            source_hashes,
            upstreams,
            upstream_hashes,
        ) = _build_target_complete_bundle(
            resolved_input_bytes,
            terminal_evidence=terminal_evidence,
            terminal_evidence_source_bytes=terminal_bytes,
            symbol=symbol,
            as_of=as_of,
        )
        review_preview = (
            legacy.build_crypto_tournament_v2_bounded_paper_probe_review(
                terminal_evidence,
                capability_evidence=capabilities,
                capability_artifact_sha256=capability_hashes,
                capability_source_evidence=sources,
                capability_source_artifact_sha256=source_hashes,
                capability_upstream_evidence=upstreams,
                capability_upstream_artifact_sha256=upstream_hashes,
                as_of=as_of,
            )
        )
        capability_results = review_preview["capability_results"]
        if review_preview["classification"] != "eligible_for_operator_review_only":
            blockers.extend(str(item) for item in review_preview["blockers"])
        else:
            bundle_fingerprint = str(
                capabilities[legacy._CAPABILITY_KINDS[0]][
                    "bundle_fingerprint"
                ]
            )
            for role, relative_path in _TARGET_INPUT_ARTIFACT_PATHS.items():
                artifacts[relative_path] = resolved_input_bytes[role]
            for kind in legacy._CAPABILITY_KINDS:
                artifacts[f"bundle/{kind}.json"] = legacy._json_bytes(
                    capabilities[kind]
                )
                artifacts[
                    f"bundle/sources/{kind}/producer_source.json"
                ] = legacy._json_bytes(sources[kind])
                for role, payload in upstreams[kind].items():
                    artifacts[
                        f"bundle/sources/{kind}/upstream/{role}.json"
                    ] = legacy._json_bytes(payload)
            artifacts["bundle/review_preview.json"] = legacy._json_bytes(
                dict(review_preview)
            )
    except ValidationError as exc:
        blockers.append(f"source_normalization_failed:{exc}")

    for kind in legacy._CAPABILITY_KINDS:
        diagnostic = {
            "schema_version": (
                CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
            ),
            "record_type": "crypto_bounded_probe_capability_diagnostic",
            "symbol": symbol,
            "evidence_kind": kind,
            "result": dict(capability_results[kind]),
            "authority": dict(legacy._CAPABILITY_AUTHORITY),
            "profit_claim": "none",
        }
        diagnostic["diagnostic_fingerprint"] = legacy._stable_hash(diagnostic)
        artifacts[f"diagnostics/{symbol}/{kind}.json"] = legacy._json_bytes(
            diagnostic
        )

    emitted = bool(bundle_fingerprint) and not blockers
    status = legacy._production_status(
        as_of=as_of,
        classification=(
            "selected_winner_capability_bundle_emitted"
            if emitted
            else "selected_winner_operational_evidence_blocked"
        ),
        terminal_binding=legacy._terminal_binding(terminal_evidence),
        source_results=source_results,
        capability_results=capability_results,
        bundle_fingerprint=bundle_fingerprint if emitted else "",
        review_preview=review_preview,
        blockers=tuple(dict.fromkeys(blockers)),
        next_action=(
            "request_separate_exact_bounded_paper_probe_authorization_review"
            if emitted
            else "repair_exact_v5_30_target_evidence_family"
        ),
    )
    artifacts["production_status.json"] = legacy._json_bytes(status)
    if not emitted:
        for name in tuple(artifacts):
            if name.startswith("bundle/"):
                del artifacts[name]
    return CryptoBoundedProbeCapabilityProduction(status, artifacts)


def _target_source_results(
    raw: Mapping[str, bytes],
) -> dict[str, dict[str, object]]:
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
        for role in _TARGET_INPUT_ARTIFACT_PATHS
    }



def _build_target_complete_bundle(
    raw: Mapping[str, bytes],
    *,
    terminal_evidence: Mapping[str, object],
    terminal_evidence_source_bytes: bytes,
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
    invalid_roles = [
        role
        for role in _TARGET_INPUT_ARTIFACT_PATHS
        if not isinstance(raw.get(role), bytes) or not raw.get(role)
    ]
    if invalid_roles:
        raise ValidationError(
            "invalid target source payloads: " + ",".join(invalid_roles)
        )
    parsed = _parse_target_inputs(raw)
    raw_hashes = {
        role: hashlib.sha256(payload).hexdigest()
        for role, payload in raw.items()
    }
    _validate_target_source_bindings(raw, raw_hashes)
    safety_receipt = parsed["safety_certification_receipt"]
    legacy._validate_safety_receipt(
        safety_receipt,
        raw,
        raw_hashes,
        as_of=as_of,
    )
    subject = {
        "asset_class": "crypto",
        "symbol": symbol,
        "environment": "alpaca_paper",
    }
    venue = legacy._normalize_venue(
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
    policy = legacy._normalize_policy(
        safety_receipt,
        raw_hashes,
        subject=subject,
    )
    mechanics = _normalize_target_lifecycle(
        parsed["target_lifecycle_plan"],
        parsed["target_lifecycle_receipt"],
        parsed["target_lifecycle_manifest"],
        terminal_evidence=terminal_evidence,
        terminal_evidence_source_bytes=terminal_evidence_source_bytes,
        venue=venue,
        safety_receipt=safety_receipt,
        raw_hashes=raw_hashes,
        subject=subject,
        as_of=as_of,
    )
    _validate_target_flat_provenance(
        parsed["independent_flat_reconciliation"],
        parsed["independent_flat_status"],
        parsed["independent_flat_manifest"],
        lifecycle_receipt=parsed["target_lifecycle_receipt"],
        raw_hashes=raw_hashes,
    )
    flat = legacy._normalize_flat(
        parsed["independent_flat_reconciliation"],
        raw_hashes["independent_flat_reconciliation"],
        subject=subject,
        expected_account_binding=legacy._mapping(
            mechanics.get("account_binding"),
            "mechanics.account_binding",
        ),
        not_before=legacy._utc_datetime(
            mechanics.get("last_broker_mutation_at"),
            "mechanics.last_broker_mutation_at",
        ),
        as_of=as_of,
    )
    kill = legacy._normalize_kill(
        safety_receipt,
        raw_hashes,
        subject=subject,
    )
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
            role: hashlib.sha256(legacy._json_bytes(payload)).hexdigest()
            for role, payload in items.items()
        }
        for kind, items in upstreams.items()
    }
    claims = {
        "venue_orderability": legacy._venue_claims(venue, symbol),
        "bounded_order_policy": dict(policy["claims"]),
        "lifecycle_flat_reconciliation": legacy._lifecycle_claims(
            mechanics,
            flat,
        ),
        "durable_kill_loss_control": dict(kill["claims"]),
    }
    observed = {
        kind: min(
            legacy._utc_datetime(item["as_of"], f"{kind}.as_of")
            for item in items.values()
        )
        for kind, items in upstreams.items()
    }
    sources = {
        kind: legacy._producer_source(
            kind,
            subject=subject,
            claims=claims[kind],
            observed_at=observed[kind],
            upstream_hashes=upstream_hashes[kind],
        )
        for kind in legacy._CAPABILITY_KINDS
    }
    source_hashes = {
        kind: hashlib.sha256(legacy._json_bytes(payload)).hexdigest()
        for kind, payload in sources.items()
    }
    unsigned_evidence = {
        kind: legacy._capability_unsigned(
            kind,
            subject=subject,
            claims=claims[kind],
            observed_at=observed[kind],
            source_sha256=source_hashes[kind],
        )
        for kind in legacy._CAPABILITY_KINDS
    }
    bundle_basis = {
        kind: {
            key: value
            for key, value in payload.items()
            if key != "bundle_fingerprint"
        }
        for kind, payload in unsigned_evidence.items()
    }
    bundle_fingerprint = legacy._stable_hash(bundle_basis)
    capabilities: dict[str, dict[str, object]] = {}
    for kind, payload in unsigned_evidence.items():
        unsigned = {**payload, "bundle_fingerprint": bundle_fingerprint}
        capabilities[kind] = {
            **unsigned,
            "evidence_fingerprint": legacy._stable_hash(unsigned),
        }
    capability_hashes = {
        kind: hashlib.sha256(legacy._json_bytes(payload)).hexdigest()
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


def _parse_target_inputs(
    raw: Mapping[str, bytes],
) -> dict[str, dict[str, object]]:
    json_roles = (
        "venue_refresh_manifest",
        "venue_universe",
        "orderability_metadata",
        "venue_router_input_manifest",
        "venue_runtime_visibility_status",
        "safety_certification_receipt",
        "target_lifecycle_plan",
        "target_lifecycle_receipt",
        "target_lifecycle_manifest",
        "independent_flat_reconciliation",
        "independent_flat_status",
        "independent_flat_manifest",
    )
    parsed = {
        role: legacy._json_mapping(raw[role], role)
        for role in json_roles
    }
    compact_roles = (
        "target_lifecycle_plan",
        "target_lifecycle_receipt",
        "target_lifecycle_manifest",
        "independent_flat_reconciliation",
        "independent_flat_status",
        "independent_flat_manifest",
    )
    for role in compact_roles:
        if raw[role] != canonical_json_bytes(parsed[role]):
            raise ValidationError(f"{role} is not exact compact canonical JSON.")
    pretty_roles = set(json_roles) - set(compact_roles)
    for role in pretty_roles:
        legacy._require_canonical_json(raw[role], parsed[role], role)
    return parsed




def _validate_target_source_bindings(
    raw: Mapping[str, bytes],
    raw_hashes: Mapping[str, str],
) -> None:
    frozen_digest = (
        "31919e9d787c90fa0f5b9444726035f919ed7a57d4bca378d7bcf0941f7efaba"
    )
    if raw_hashes.get("capability_producer_source") != frozen_digest:
        raise ValidationError("frozen legacy producer source digest drifted.")
    for role, expected_sha256 in _TARGET_LOADED_SOURCE_SHA256.items():
        if (
            not isinstance(raw.get(role), bytes)
            or raw_hashes.get(role) != expected_sha256
        ):
            raise ValidationError(
                f"canonical target local source binding mismatch: {role}"
            )
    markers = {
        "target_capability_producer_source": (
            b"def _build_target_complete_bundle("
        ),
        "target_lifecycle_operator_source": (
            b"def run_crypto_tournament_v2_bounded_paper_probe_lifecycle("
        ),
        "independent_flat_operator_source": (
            b"def run_crypto_bounded_probe_independent_flat_operator("
        ),
    }
    for role, marker in markers.items():
        if marker not in raw[role]:
            raise ValidationError(f"target source marker is absent: {role}")


def _normalize_target_lifecycle(
    plan: Mapping[str, object],
    receipt: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    terminal_evidence: Mapping[str, object],
    terminal_evidence_source_bytes: bytes,
    venue: Mapping[str, object],
    safety_receipt: Mapping[str, object],
    raw_hashes: Mapping[str, str],
    subject: Mapping[str, object],
    as_of: datetime,
) -> dict[str, object]:
    validate_lifecycle_plan(plan)
    if (
        plan.get("classification")
        != "ready_for_exact_operation_authorization"
        or plan.get("subject") != subject
        or plan.get("entry_notional_usd") != "10"
        or plan.get("time_in_force") != "gtc"
        or plan.get("budgets") != BUDGETS
    ):
        raise ValidationError("V5.30 lifecycle plan identity drifted.")
    _validate_target_terminal_binding(
        plan,
        terminal_evidence=terminal_evidence,
        terminal_source_sha256=hashlib.sha256(
            terminal_evidence_source_bytes
        ).hexdigest(),
    )
    _validate_target_venue_binding(plan, venue=venue)
    _validate_target_safety_binding(
        plan,
        receipt=safety_receipt,
        raw_hashes=raw_hashes,
    )
    plan_at = _canonical_time(plan.get("as_of"), "plan.as_of")
    terminal_at = _canonical_time(
        legacy._mapping(
            plan.get("terminal_binding"),
            "plan.terminal_binding",
        ).get("terminal_closed_at"),
        "plan.terminal_binding.terminal_closed_at",
    )
    venue_at = _canonical_time(
        legacy._mapping(
            plan.get("venue_binding"),
            "plan.venue_binding",
        ).get("observed_at"),
        "plan.venue_binding.observed_at",
    )
    safety_at = _canonical_time(
        legacy._mapping(
            plan.get("safety_binding"),
            "plan.safety_binding",
        ).get("certified_at"),
        "plan.safety_binding.certified_at",
    )
    if (
        terminal_at > plan_at
        or venue_at > plan_at
        or safety_at > plan_at
        or plan_at - venue_at > timedelta(hours=24)
        or plan_at - safety_at > timedelta(hours=168)
    ):
        raise ValidationError("V5.30 plan evidence chronology drifted.")
    _validate_target_lifecycle_receipt(
        receipt,
        plan=plan,
        plan_sha256=raw_hashes["target_lifecycle_plan"],
    )
    _validate_target_lifecycle_manifest(
        manifest,
        plan=plan,
        receipt=receipt,
        raw_hashes=raw_hashes,
    )
    exit_order = legacy._mapping(
        receipt.get("exit_final_order"),
        "target_lifecycle.exit_final_order",
    )
    exit_filled_at = _canonical_time(
        exit_order.get("filled_at"),
        "target_lifecycle.exit_filled_at",
    )
    receipt_observed = _canonical_time(
        receipt.get("as_of"),
        "target_lifecycle.as_of",
    )
    plan_observed = _canonical_time(plan.get("as_of"), "plan.as_of")
    if (
        receipt_observed > as_of or exit_filled_at > receipt_observed
    ):
        raise ValidationError("V5.30 lifecycle receipt is future-dated.")
    return {
        "schema_version": "v5_26_crypto_lifecycle_mechanics_certification_v1",
        "record_type": "crypto_lifecycle_mechanics_certification_result",
        "as_of": plan_observed.isoformat(),
        "last_broker_mutation_at": exit_filled_at.isoformat(),
        "subject": dict(subject),
        "mechanics_certified": True,
        "tested_notional_ceiling_usd": "10",
        "entry_submit_attempts": 1,
        "exit_submit_attempts": 1,
        "cancel_attempts_max_per_order": 1,
        "replacement_attempts": 0,
        "broker_ambiguity": False,
        "account_binding": dict(receipt["account_binding"]),
        "paper_only": True,
        "live_endpoint_touched": False,
        "resolved_source_digests": {
            role: raw_hashes[role]
            for role in (
                "target_lifecycle_plan",
                "target_lifecycle_receipt",
                "target_lifecycle_manifest",
                "target_lifecycle_operator_source",
                "target_capability_producer_source",
            )
        },
        "provenance_classification": (
            "v5_30_exact_winner_source_bound_lifecycle"
        ),
        "authority": dict(legacy._CAPABILITY_AUTHORITY),
        "profit_claim": "none",
    }



def _sha256_digest(value: object, field_name: str) -> str:
    text = str(value).strip().lower()
    if (
        len(text) != 64
        or any(character not in "0123456789abcdef" for character in text)
    ):
        raise ValidationError(f"{field_name} must be a sha256 digest.")
    return text


def _decimal_value(value: object, field_name: str) -> Decimal:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a decimal string.")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be decimal.") from exc
    if not result.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    canonical = format(result, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    if result == 0:
        canonical = "0"
    if value != canonical:
        raise ValidationError(f"{field_name} must be canonical decimal text.")
    return result


def _optional_decimal_value(
    value: object,
    field_name: str,
) -> Decimal | None:
    if type(value) is not str:
        raise ValidationError(
            f"{field_name} must be an optional decimal string."
        )
    if value == "":
        return None
    return _decimal_value(value, field_name)


def _canonical_time(value: object, field_name: str) -> datetime:
    parsed = utc_datetime(value, field_name)
    if value != parsed.isoformat():
        raise ValidationError(f"{field_name} must be canonical ISO-8601.")
    return parsed


def _validate_target_terminal_binding(
    plan: Mapping[str, object],
    *,
    terminal_evidence: Mapping[str, object],
    terminal_source_sha256: str,
) -> None:
    terminal_binding = legacy._mapping(
        plan.get("terminal_binding"),
        "plan.terminal_binding",
    )
    source = legacy._mapping(
        terminal_evidence.get("source_binding"),
        "terminal.source_binding",
    )
    selected_candidate = legacy._mapping(
        terminal_evidence.get("selected_candidate"),
        "terminal.selected_candidate",
    )
    source_sha = _sha256_digest(
        terminal_source_sha256,
        "terminal_source_sha256",
    )
    expected = {
        "selected_symbol": terminal_evidence.get("selected_symbol"),
        "selected_candidate": selected_candidate,
        "classification": terminal_evidence.get("classification"),
        "preregistration_fingerprint": source.get(
            "preregistration_fingerprint"
        ),
        "activation_fingerprint": source.get("activation_fingerprint"),
        "state_fingerprint": source.get("state_fingerprint"),
        "terminal_evidence_fingerprint": source.get(
            "terminal_evidence_fingerprint"
        ),
        "terminal_closed_at": source.get("terminal_closed_at"),
        "evidence_export_fingerprint": terminal_evidence.get(
            "evidence_export_fingerprint"
        ),
        "terminal_source_sha256": source_sha,
    }
    if terminal_binding != expected:
        raise ValidationError("V5.30 terminal plan binding drifted.")


def _validate_target_venue_binding(
    plan: Mapping[str, object],
    *,
    venue: Mapping[str, object],
) -> None:
    records = legacy._mapping_sequence(venue.get("records"), "venue.records")
    if len(records) != 1:
        raise ValidationError("V5.30 venue target record is not unique.")
    resolved = legacy._mapping(
        venue.get("resolved_source_digests"),
        "venue.resolved_source_digests",
    )
    expected = {
        "target_symbol": venue.get("target_symbol"),
        "observed_at": venue.get("as_of"),
        "bundle_fingerprint": stable_hash(venue),
        "resolved_source_digests": resolved,
        "orderability_record": dict(records[0]),
    }
    if plan.get("venue_binding") != expected:
        raise ValidationError("V5.30 venue plan binding drifted.")


def _validate_target_safety_binding(
    plan: Mapping[str, object],
    *,
    receipt: Mapping[str, object],
    raw_hashes: Mapping[str, str],
) -> None:
    plan_safety = legacy._mapping(
        plan.get("safety_binding"),
        "plan.safety_binding",
    )
    runtime_source_bundle_sha256 = _sha256_digest(
        plan_safety.get("runtime_source_bundle_sha256"),
        "plan.safety_binding.runtime_source_bundle_sha256",
    )
    expected = {
        "policy_fingerprint": SAFETY_POLICY_FINGERPRINT,
        "certification_receipt_fingerprint": receipt.get(
            "receipt_fingerprint"
        ),
        "certification_source_sha256": raw_hashes[
            "safety_certification_receipt"
        ],
        "kernel_source_sha256": receipt.get("kernel_source_sha256"),
        "certifier_source_sha256": receipt.get("certifier_source_sha256"),
        "focused_test_source_sha256": receipt.get(
            "focused_test_source_sha256"
        ),
        "runtime_source_bundle_sha256": runtime_source_bundle_sha256,
        "certified_at": _canonical_time(
            receipt.get("as_of"),
            "safety.as_of",
        ).isoformat(),
    }
    if plan.get("safety_binding") != expected:
        raise ValidationError("V5.30 safety plan binding drifted.")


def _validate_terminal_evidence_shadow_binding(
    terminal: Mapping[str, object],
    frozen_state: Mapping[str, object],
) -> None:
    source = legacy._mapping(
        terminal.get("source_binding"),
        "terminal.source_binding",
    )
    expected = {
        "preregistration_fingerprint": frozen_state.get(
            "preregistration_fingerprint"
        ),
        "state_schema_version": frozen_state.get("schema_version"),
        "activation_fingerprint": frozen_state.get(
            "activation_fingerprint"
        ),
        "activation_source_state_fingerprint": frozen_state.get(
            "source_state_fingerprint"
        ),
        "state_fingerprint": frozen_state.get("state_fingerprint"),
        "context_sha256": frozen_state.get("context_sha256"),
        "terminal_packet_sha256": frozen_state.get(
            "terminal_packet_sha256"
        ),
        "terminal_evidence_fingerprint": frozen_state.get(
            "terminal_evidence_fingerprint"
        ),
        "terminal_closed_at": frozen_state.get("terminal_closed_at"),
        "artifact_sha256": dict(
            legacy._mapping(
                frozen_state.get("artifact_sha256"),
                "frozen_state.artifact_sha256",
            )
        ),
    }
    observed = {
        key: source.get(key)
        for key in expected
    }
    if (
        frozen_state.get("terminal_outcome_closed") is not True
        or observed != expected
    ):
        raise ValidationError(
            "pinned terminal evidence does not match current frozen shadow."
        )


def _action_claim_fingerprint(
    plan: Mapping[str, object],
    role: str,
) -> str:
    ids = legacy._mapping(
        plan.get("deterministic_ids"),
        "plan.deterministic_ids",
    )
    safety = legacy._mapping(
        plan.get("safety_binding"),
        "plan.safety_binding",
    )
    return stable_hash(
        {
            "plan_fingerprint": plan.get("plan_fingerprint"),
            "execution_plan_id": ids.get("execution_plan_id"),
            "role": role,
            "policy_fingerprint": safety.get("policy_fingerprint"),
        }
    )


def _validate_target_lifecycle_receipt(
    receipt: Mapping[str, object],
    *,
    plan: Mapping[str, object],
    plan_sha256: str,
) -> None:
    if set(receipt) != _TARGET_LIFECYCLE_RECEIPT_KEYS:
        raise ValidationError("V5.30 lifecycle receipt keys drifted.")
    unsigned = dict(receipt)
    fingerprint = _sha256_digest(
        unsigned.pop("lifecycle_fingerprint", ""),
        "lifecycle_fingerprint",
    )
    if fingerprint != stable_hash(unsigned):
        raise ValidationError("V5.30 lifecycle receipt fingerprint drifted.")
    mapping_fields = (
        "subject",
        "terminal_binding",
        "venue_binding",
        "safety_binding",
        "account_binding",
        "authorization",
        "operator_preflight",
        "deterministic_ids",
        "entry_final_order",
        "exit_final_order",
    )
    if any(
        not isinstance(receipt.get(field), Mapping)
        for field in mapping_fields
    ):
        raise ValidationError("V5.30 lifecycle receipt mapping drifted.")
    authorization = dict(receipt["authorization"])
    preflight = dict(receipt["operator_preflight"])
    ids = dict(receipt["deterministic_ids"])
    account_binding = dict(receipt["account_binding"])
    validate_alpaca_paper_account_binding(account_binding)
    cancel_count = receipt.get("cancel_attempt_count")
    if (
        receipt.get("schema_version") != LIFECYCLE_SCHEMA_VERSION
        or receipt.get("record_type") != LIFECYCLE_RECORD_TYPE
        or receipt.get("subject") != plan.get("subject")
        or receipt.get("plan_fingerprint") != plan.get("plan_fingerprint")
        or receipt.get("plan_source_sha256")
        != _sha256_digest(plan_sha256, "plan_sha256")
        or receipt.get("terminal_binding") != plan.get("terminal_binding")
        or receipt.get("venue_binding") != plan.get("venue_binding")
        or receipt.get("safety_binding") != plan.get("safety_binding")
        or account_binding != plan.get("account_binding")
        or ids != plan.get("deterministic_ids")
        or receipt.get("budgets") != BUDGETS
        or type(receipt.get("entry_attempt_count")) is not int
        or type(receipt.get("cancel_attempt_count")) is not int
        or type(receipt.get("exit_attempt_count")) is not int
        or type(receipt.get("final_position_count")) is not int
        or type(receipt.get("final_open_order_count")) is not int
        or receipt.get("entry_attempt_count") != 1
        or receipt.get("exit_attempt_count") != 1
        or cancel_count not in {0, 1}
        or receipt.get("final_position_count") != 0
        or receipt.get("final_open_order_count") != 0
        or receipt.get("broker_read_occurred") is not True
        or receipt.get("broker_mutation_performed") is not True
        or receipt.get("paper_submit_performed") is not True
        or type(receipt.get("paper_cancel_performed")) is not bool
        or (
            cancel_count == 0
            and receipt.get("paper_cancel_performed") is not False
        )
        or receipt.get("paper_replace_performed") is not False
        or receipt.get("paper_close_performed") is not False
        or receipt.get("paper_liquidate_performed") is not False
        or receipt.get("broker_ambiguity") is not False
        or receipt.get("outcome_classification") != "filled_exit_confirmed"
        or receipt.get("blockers") != []
        or receipt.get("next_action")
        != "run_v5_29_independent_flat_collector"
        or receipt.get("paper_only") is not True
        or receipt.get("live_endpoint_touched") is not False
        or receipt.get("credential_values_exposed") is not False
        or receipt.get("capital_allocation_authorized") is not False
        or receipt.get("live_authorized") is not False
        or receipt.get("profit_claim") != "none"
    ):
        raise ValidationError("V5.30 lifecycle success semantics drifted.")
    if (
        set(authorization) != _TARGET_AUTHORIZATION_KEYS
        or authorization.get("paper_mutation_authorized") is not True
        or authorization.get("network_authorized") is not True
        or authorization.get("exact_operation_authorization_matched")
        is not True
        or authorization.get("authorization_fingerprint")
        != plan.get("required_authorization_sha256")
        or authorization.get("entry_authorization_valid_until")
        != plan.get("entry_authorization_valid_until")
        or authorization.get(
            "risk_reducing_unwind_authorized_for_claimed_entry"
        )
        is not True
        or authorization.get("live_authorized") is not False
        or authorization.get("capital_allocation_authorized") is not False
    ):
        raise ValidationError("V5.30 lifecycle authorization drifted.")
    if (
        set(preflight) != _TARGET_LIFECYCLE_PREFLIGHT_KEYS
        or any(type(value) is not bool for value in preflight.values())
        or preflight.get("APP_PROFILE_is_paper") is not True
        or preflight.get("APP_PROFILE_is_live") is not False
        or preflight.get("paper_credentials_present") is not True
        or preflight.get("expected_paper_account_id_loaded") is not True
        or preflight.get("paper_endpoint_exact_match_indicator") is not True
        or preflight.get("live_endpoint_indicator") is not False
        or preflight.get("network_test_flag_enabled") is not False
        or preflight.get("runtime_source_bundle_matched") is not True
        or preflight.get("ALPACA_API_KEY_present") is not True
        or preflight.get("ALPACA_SECRET_KEY_present") is not True
    ):
        raise ValidationError("V5.30 lifecycle preflight drifted.")
    expected_claims = [
        _action_claim_fingerprint(plan, role)
        for role, count in (
            ("entry", 1),
            ("cancel", cancel_count),
            ("exit", 1),
        )
        if count
    ]
    if receipt.get("action_claim_fingerprints") != expected_claims:
        raise ValidationError("V5.30 lifecycle action claims drifted.")

    entry = dict(receipt["entry_final_order"])
    exit_order = dict(receipt["exit_final_order"])
    for field_name, order in (
        ("entry_final_order", entry),
        ("exit_final_order", exit_order),
    ):
        if set(order) != _TARGET_ORDER_KEYS:
            raise ValidationError(
                f"V5.30 lifecycle {field_name} keys drifted."
            )
        unsigned_order = dict(order)
        order_fingerprint = _sha256_digest(
            unsigned_order.pop("order_fingerprint", ""),
            f"{field_name}.order_fingerprint",
        )
        broker_fingerprint = _sha256_digest(
            unsigned_order.get("broker_order_fingerprint", ""),
            f"{field_name}.broker_order_fingerprint",
        )
        if (
            order_fingerprint != stable_hash(unsigned_order)
            or not broker_fingerprint
        ):
            raise ValidationError(
                f"V5.30 lifecycle {field_name} fingerprint drifted."
            )
        for decimal_field in ("filled_qty", "filled_avg_price"):
            decimal_value = _decimal_value(
                order.get(decimal_field),
                f"{field_name}.{decimal_field}",
            )
            if decimal_value < 0:
                raise ValidationError(
                    f"V5.30 lifecycle {field_name} decimal is negative."
                )
        for decimal_field in ("qty", "notional", "limit_price"):
            decimal_value = _optional_decimal_value(
                order.get(decimal_field),
                f"{field_name}.{decimal_field}",
            )
            if decimal_value is not None and decimal_value < 0:
                raise ValidationError(
                    f"V5.30 lifecycle {field_name} decimal is negative."
                )

    entry_qty = _decimal_value(entry["filled_qty"], "entry.filled_qty")
    exit_qty = _decimal_value(exit_order["filled_qty"], "exit.filled_qty")
    entry_request_qty = _optional_decimal_value(entry["qty"], "entry.qty")
    entry_notional = _optional_decimal_value(
        entry["notional"],
        "entry.notional",
    )
    exit_request_qty = _optional_decimal_value(
        exit_order["qty"],
        "exit.qty",
    )
    exit_notional = _optional_decimal_value(
        exit_order["notional"],
        "exit.notional",
    )
    entry_limit_price = _optional_decimal_value(
        entry["limit_price"],
        "entry.limit_price",
    )
    exit_limit_price = _optional_decimal_value(
        exit_order["limit_price"],
        "exit.limit_price",
    )
    plan_at = _canonical_time(plan.get("as_of"), "plan.as_of")
    authorization_until = _canonical_time(
        plan.get("entry_authorization_valid_until"),
        "plan.entry_authorization_valid_until",
    )
    entry_submitted = _canonical_time(
        entry.get("submitted_at"),
        "entry.submitted_at",
    )
    entry_filled = _canonical_time(entry.get("filled_at"), "entry.filled_at")
    exit_submitted = _canonical_time(
        exit_order.get("submitted_at"),
        "exit.submitted_at",
    )
    exit_filled = _canonical_time(
        exit_order.get("filled_at"),
        "exit.filled_at",
    )
    receipt_at = _canonical_time(receipt.get("as_of"), "receipt.as_of")
    if (
        entry.get("client_order_id") != ids.get("entry_client_order_id")
        or exit_order.get("client_order_id") != ids.get("exit_client_order_id")
        or entry.get("symbol") != plan["subject"]["symbol"]
        or exit_order.get("symbol") != plan["subject"]["symbol"]
        or entry.get("side") != "buy"
        or exit_order.get("side") != "sell"
        or entry.get("asset_class") != "crypto"
        or exit_order.get("asset_class") != "crypto"
        or entry.get("order_type") != "market"
        or exit_order.get("order_type") != "market"
        or entry.get("time_in_force") != "gtc"
        or exit_order.get("time_in_force") != "gtc"
        or entry_limit_price is not None
        or exit_limit_price is not None
        or entry.get("status") not in {"filled", "canceled", "cancelled"}
        or exit_order.get("status") != "filled"
        or entry_request_qty is not None
        or entry_notional != ENTRY_NOTIONAL_USD
        or exit_notional is not None
        or entry_qty <= 0
        or exit_qty != entry_qty
        or exit_request_qty != entry_qty
        or _decimal_value(entry["filled_avg_price"], "entry.filled_avg_price")
        <= 0
        or _decimal_value(
            exit_order["filled_avg_price"],
            "exit.filled_avg_price",
        )
        <= 0
        or not (
            plan_at
            <= entry_submitted
            <= authorization_until
            and entry_submitted
            <= entry_filled
            <= exit_submitted
            <= exit_filled
            <= receipt_at
        )
        or exit_filled
        > plan_at + timedelta(hours=int(plan["maximum_duration_hours"]))
    ):
        raise ValidationError("V5.30 lifecycle order chronology drifted.")


def _validate_target_lifecycle_manifest(
    manifest: Mapping[str, object],
    *,
    plan: Mapping[str, object],
    receipt: Mapping[str, object],
    raw_hashes: Mapping[str, str],
) -> None:
    if set(manifest) != _TARGET_LIFECYCLE_MANIFEST_KEYS:
        raise ValidationError("V5.30 lifecycle manifest keys drifted.")
    unsigned = dict(manifest)
    fingerprint = _sha256_digest(
        unsigned.pop("manifest_fingerprint", ""),
        "lifecycle_manifest.manifest_fingerprint",
    )
    if fingerprint != stable_hash(unsigned):
        raise ValidationError("V5.30 lifecycle manifest fingerprint drifted.")
    if (
        manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or manifest.get("record_type")
        != "crypto_tournament_v2_bounded_paper_probe_lifecycle_manifest"
        or manifest.get("as_of") != receipt.get("as_of")
        or manifest.get("symbol") != plan["subject"]["symbol"]
        or manifest.get("plan_sha256")
        != raw_hashes["target_lifecycle_plan"]
        or manifest.get("receipt_sha256")
        != raw_hashes["target_lifecycle_receipt"]
        or manifest.get("operator_source_sha256")
        != raw_hashes["target_lifecycle_operator_source"]
        or manifest.get("outcome_classification")
        != receipt.get("outcome_classification")
        or manifest.get("entry_attempt_count")
        != receipt.get("entry_attempt_count")
        or manifest.get("cancel_attempt_count")
        != receipt.get("cancel_attempt_count")
        or manifest.get("exit_attempt_count")
        != receipt.get("exit_attempt_count")
        or manifest.get("paper_only") is not True
        or manifest.get("live_endpoint_touched") is not False
        or manifest.get("credential_values_exposed") is not False
        or manifest.get("capital_allocation_authorized") is not False
        or manifest.get("live_authorized") is not False
    ):
        raise ValidationError("V5.30 lifecycle manifest binding drifted.")


def _validate_target_flat_provenance(
    flat_receipt: Mapping[str, object],
    status: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    lifecycle_receipt: Mapping[str, object],
    raw_hashes: Mapping[str, str],
) -> None:
    if set(status) != _TARGET_FLAT_STATUS_KEYS:
        raise ValidationError("V5.29 flat status keys drifted.")
    unsigned_status = dict(status)
    status_fingerprint = _sha256_digest(
        unsigned_status.pop("status_fingerprint", ""),
        "flat_status.status_fingerprint",
    )
    if status_fingerprint != hashlib.sha256(
        canonical_json_bytes(unsigned_status)
    ).hexdigest():
        raise ValidationError("V5.29 flat status fingerprint drifted.")
    if (
        not isinstance(status.get("subject"), Mapping)
        or not isinstance(status.get("lifecycle_binding"), Mapping)
        or not isinstance(status.get("operator_preflight"), Mapping)
        or not isinstance(flat_receipt.get("account_binding"), Mapping)
        or not isinstance(lifecycle_receipt.get("account_binding"), Mapping)
        or not isinstance(lifecycle_receipt.get("exit_final_order"), Mapping)
    ):
        raise ValidationError("V5.29 flat provenance mapping drifted.")
    subject = dict(status["subject"])
    lifecycle_binding = dict(status["lifecycle_binding"])
    preflight = dict(status["operator_preflight"])
    account_binding = dict(flat_receipt["account_binding"])
    validate_alpaca_paper_account_binding(account_binding)
    lifecycle_account = dict(lifecycle_receipt["account_binding"])
    exit_order = dict(lifecycle_receipt["exit_final_order"])
    expected_lifecycle_binding = {
        "schema_version": lifecycle_receipt.get("schema_version"),
        "symbol": subject.get("symbol"),
        "account_binding": lifecycle_account,
        "exit_filled_at": exit_order.get("filled_at"),
        "source_sha256": raw_hashes["target_lifecycle_receipt"],
    }
    flat_at = _canonical_time(flat_receipt.get("as_of"), "flat_receipt.as_of")
    status_at = _canonical_time(status.get("as_of"), "flat_status.as_of")
    lifecycle_at = _canonical_time(
        lifecycle_receipt.get("as_of"),
        "target_lifecycle.as_of",
    )
    if (
        set(lifecycle_binding) != _TARGET_FLAT_LIFECYCLE_BINDING_KEYS
        or lifecycle_binding != expected_lifecycle_binding
        or subject != lifecycle_receipt.get("subject")
        or flat_receipt.get("subject") != subject
        or account_binding != lifecycle_account
        or status_at != flat_at
        or status_at < lifecycle_at
        or type(status.get("lifecycle_source")) is not str
        or not str(status.get("lifecycle_source")).strip()
        or status.get("schema_version")
        != "v5_29_crypto_bounded_probe_independent_flat_operator_v1"
        or status.get("record_type")
        != "crypto_bounded_probe_independent_flat_operator_status"
        or status.get("read_authorized") is not True
        or status.get("network_authorized") is not True
        or status.get("broker_read_occurred") is not True
        or status.get("account_read_occurred") is not True
        or status.get("positions_read_occurred") is not True
        or status.get("open_orders_read_occurred") is not True
        or status.get("broker_mutation_occurred") is not False
        or status.get("paper_mutation_occurred") is not False
        or status.get("live_endpoint_touched") is not False
        or status.get("credential_values_exposed") is not False
        or status.get("receipt_emitted") is not True
        or status.get("receipt_fingerprint")
        != flat_receipt.get("observation_fingerprint")
        or status.get("final_position_count") != 0
        or type(status.get("final_position_count")) is not int
        or type(status.get("final_open_order_count")) is not int
        or status.get("final_open_order_count") != 0
        or status.get("blockers") != []
        or status.get("classification")
        != "independent_flat_receipt_emitted"
        or status.get("next_action")
        != "run_source_bound_capability_production"
        or status.get("profit_claim") != "none"
    ):
        raise ValidationError("V5.29 flat success provenance drifted.")
    if (
        set(preflight) != _TARGET_PREFLIGHT_KEYS
        or any(type(value) is not bool for value in preflight.values())
        or preflight.get("APP_PROFILE_is_paper") is not True
        or preflight.get("APP_PROFILE_is_live") is not False
        or preflight.get("paper_credentials_present") is not True
        or preflight.get("expected_paper_account_id_loaded") is not True
        or preflight.get("paper_endpoint_exact_match_indicator") is not True
        or preflight.get("live_endpoint_indicator") is not False
        or preflight.get("network_test_flag_enabled") is not False
        or preflight.get("ALPACA_API_KEY_present") is not True
        or preflight.get("ALPACA_SECRET_KEY_present") is not True
    ):
        raise ValidationError("V5.29 flat preflight drifted.")

    if set(manifest) != _TARGET_FLAT_MANIFEST_KEYS:
        raise ValidationError("V5.29 flat manifest keys drifted.")
    unsigned_manifest = dict(manifest)
    manifest_fingerprint = _sha256_digest(
        unsigned_manifest.pop("manifest_fingerprint", ""),
        "flat_manifest.manifest_fingerprint",
    )
    if manifest_fingerprint != hashlib.sha256(
        canonical_json_bytes(unsigned_manifest)
    ).hexdigest():
        raise ValidationError("V5.29 flat manifest fingerprint drifted.")
    if (
        manifest.get("schema_version")
        != "v5_29_crypto_bounded_probe_independent_flat_operator_v1"
        or manifest.get("record_type")
        != "crypto_bounded_probe_independent_flat_manifest"
        or manifest.get("as_of") != status.get("as_of")
        or manifest.get("symbol") != subject.get("symbol")
        or manifest.get("receipt_sha256")
        != raw_hashes["independent_flat_reconciliation"]
        or manifest.get("status_sha256")
        != raw_hashes["independent_flat_status"]
        or manifest.get("collector_source_sha256")
        != raw_hashes["independent_flat_operator_source"]
        or manifest.get("lifecycle_source_sha256")
        != raw_hashes["target_lifecycle_receipt"]
        or manifest.get("broker_mutation_occurred") is not False
        or manifest.get("paper_mutation_occurred") is not False
        or manifest.get("live_endpoint_touched") is not False
        or manifest.get("credential_values_exposed") is not False
    ):
        raise ValidationError("V5.29 flat manifest binding drifted.")


def load_crypto_tournament_v2_bounded_paper_probe_capability_generation(
    root: Path | str,
    *,
    expected_publication_fingerprint: str,
) -> CryptoBoundedProbeCapabilityProduction:
    """Load a family-agnostic immutable production generation."""

    return (
        legacy.load_crypto_tournament_v2_bounded_paper_probe_capability_generation(
            root,
            expected_publication_fingerprint=(
                expected_publication_fingerprint
            ),
        )
    )


def run_crypto_tournament_v2_bounded_paper_probe_capability_producer(
    *,
    shadow_root: Path | str = (
        legacy.CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT
    ),
    venue_orderability_path: Path | str = (
        "runs/crypto_universe_refresh/paper_read_latest/"
        "crypto_orderability_metadata.json"
    ),
    target_terminal_evidence_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/"
        "bounded_paper_probe_lifecycle/latest/terminal_evidence.json"
    ),
    target_lifecycle_plan_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/"
        "bounded_paper_probe_lifecycle/latest/lifecycle_plan.json"
    ),
    target_lifecycle_receipt_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/"
        "bounded_paper_probe_lifecycle/latest/lifecycle_result.json"
    ),
    target_lifecycle_manifest_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/"
        "bounded_paper_probe_lifecycle/latest/manifest.json"
    ),
    independent_flat_reconciliation_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/"
        "bounded_paper_probe_capabilities/"
        "independent_flat_reconciliation.json"
    ),
    independent_flat_status_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/"
        "bounded_paper_probe_capabilities/latest_status.json"
    ),
    independent_flat_manifest_path: Path | str = (
        "runs/crypto_strategy_tournament/v2/"
        "bounded_paper_probe_capabilities/independent_flat_manifest.json"
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
        "runs/crypto_strategy_tournament/v2/"
        "bounded_paper_probe_capabilities/"
        "safety_certification_receipt.json"
    ),
    as_of: datetime | str,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Publish target evidence only after terminal winner selection."""

    evaluated_at = legacy._utc_datetime(as_of, "as_of")
    shadow_path = legacy._local_path(shadow_root, "shadow_root")
    output_path = legacy._local_path(output_root, "output_root")
    terminal_evidence: Mapping[str, object] | None = None
    terminal_evidence_source_bytes: bytes | None = None
    if (shadow_path / "frozen_state.json").is_file():
        state_packet = legacy.run_crypto_tournament_v2_forward_shadow_state(
            output_root=shadow_path,
            as_of=evaluated_at,
            write_artifacts=False,
        )
        frozen_state = state_packet.get("frozen_state")
        if (
            isinstance(frozen_state, Mapping)
            and frozen_state.get("terminal_outcome_closed") is True
        ):
            terminal_reference = (
                legacy.export_crypto_tournament_v2_forward_shadow_terminal_evidence(
                    output_root=shadow_path,
                    as_of=evaluated_at,
                )
            )
            pinned_terminal = legacy._read_optional_source(
                target_terminal_evidence_path,
                "target_terminal_evidence",
            )
            if pinned_terminal is not None:
                pinned_mapping = legacy._json_mapping(
                    pinned_terminal,
                    "target_terminal_evidence",
                )
                legacy._require_canonical_json(
                    pinned_terminal,
                    pinned_mapping,
                    "target_terminal_evidence",
                )
                validate_terminal_evidence_reference(
                    pinned_mapping,
                    terminal_reference,
                )
                terminal_evidence = pinned_mapping
                terminal_evidence_source_bytes = pinned_terminal
            else:
                terminal_evidence = terminal_reference
            _validate_terminal_evidence_shadow_binding(
                terminal_evidence,
                frozen_state,
            )
    preliminary = (
        legacy.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
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
        input_paths: dict[str, Path | str] = {
            **_TARGET_LOCAL_SOURCE_PATHS,
            "venue_refresh_manifest": venue_root / "manifest.json",
            "venue_universe": venue_root / "crypto_universe.json",
            "orderability_metadata": venue_orderability_path,
            "venue_router_input_manifest": (
                venue_root / "crypto_router_input_manifest.json"
            ),
            "venue_runtime_visibility_status": (
                Path("runs/crypto_paper_visibility/latest/latest_status.json")
            ),
            "target_lifecycle_plan": target_lifecycle_plan_path,
            "target_lifecycle_receipt": target_lifecycle_receipt_path,
            "target_lifecycle_manifest": target_lifecycle_manifest_path,
            "independent_flat_reconciliation": (
                independent_flat_reconciliation_path
            ),
            "independent_flat_status": independent_flat_status_path,
            "independent_flat_manifest": independent_flat_manifest_path,
            "safety_kernel_source": safety_kernel_source_path,
            "safety_certifier_source": safety_certifier_source_path,
            "safety_focused_test_source": safety_focused_test_source_path,
            "safety_certification_receipt": (
                safety_certification_receipt_path
            ),
        }
        resolved: dict[str, bytes] = {}
        for role in _TARGET_INPUT_ARTIFACT_PATHS:
            payload = legacy._read_optional_source(input_paths[role], role)
            resolved[role] = b"" if payload is None else payload
        production = (
            build_crypto_tournament_v2_bounded_paper_probe_capability_production(
                terminal_evidence,
                resolved_input_bytes=resolved,
                terminal_evidence_source_bytes=(
                    terminal_evidence_source_bytes
                ),
                as_of=evaluated_at,
            )
        )
    if write_artifacts:
        legacy._publish_production(output_path, production)
    return dict(production.status)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--shadow-root",
        default=str(
            legacy.CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(
            CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_DEFAULT_OUTPUT_ROOT
        ),
    )
    parser.add_argument(
        "--venue-orderability-path",
        default=(
            "runs/crypto_universe_refresh/paper_read_latest/"
            "crypto_orderability_metadata.json"
        ),
    )
    parser.add_argument(
        "--target-terminal-evidence-path",
        default=(
            "runs/crypto_strategy_tournament/v2/"
            "bounded_paper_probe_lifecycle/latest/terminal_evidence.json"
        ),
    )
    parser.add_argument(
        "--target-lifecycle-plan-path",
        default=(
            "runs/crypto_strategy_tournament/v2/"
            "bounded_paper_probe_lifecycle/latest/lifecycle_plan.json"
        ),
    )
    parser.add_argument(
        "--target-lifecycle-receipt-path",
        default=(
            "runs/crypto_strategy_tournament/v2/"
            "bounded_paper_probe_lifecycle/latest/lifecycle_result.json"
        ),
    )
    parser.add_argument(
        "--target-lifecycle-manifest-path",
        default=(
            "runs/crypto_strategy_tournament/v2/"
            "bounded_paper_probe_lifecycle/latest/manifest.json"
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
        "--independent-flat-status-path",
        default=(
            "runs/crypto_strategy_tournament/v2/"
            "bounded_paper_probe_capabilities/latest_status.json"
        ),
    )
    parser.add_argument(
        "--independent-flat-manifest-path",
        default=(
            "runs/crypto_strategy_tournament/v2/"
            "bounded_paper_probe_capabilities/"
            "independent_flat_manifest.json"
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
        target_terminal_evidence_path=(
            args.target_terminal_evidence_path
        ),
        target_lifecycle_plan_path=args.target_lifecycle_plan_path,
        target_lifecycle_receipt_path=args.target_lifecycle_receipt_path,
        target_lifecycle_manifest_path=args.target_lifecycle_manifest_path,
        independent_flat_reconciliation_path=(
            args.independent_flat_reconciliation_path
        ),
        independent_flat_status_path=args.independent_flat_status_path,
        independent_flat_manifest_path=args.independent_flat_manifest_path,
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
    return (
        0
        if status.get("classification")
        == "selected_winner_capability_bundle_emitted"
        and status.get("capability_bundle_emitted") is True
        else 2
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
