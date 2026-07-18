"""Authority-free exact-winner bounded paper lifecycle planning.

The V5.30 boundary remains dormant until sealed V5.25 terminal evidence names
one strategy-eligible winner. Planning is local, broker-free, and mutation-free.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from algotrader.core.crypto_bounded_probe_lifecycle import (
    LIFECYCLE_RUNTIME_SOURCE_RELATIVE_PATHS,
    PLAN_SCHEMA_VERSION,
    SAFETY_POLICY_FINGERPRINT,
    SUPPORTED_SYMBOLS,
    build_dormant_lifecycle_plan,
    build_ready_lifecycle_plan,
    canonical_json_bytes,
    exact_operation_authorization_text,
    stable_hash,
    utc_datetime,
    validate_terminal_evidence_reference,
    validate_lifecycle_plan,
)
from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
)
from algotrader.execution.crypto_bounded_probe_safety_certification import (
    validate_crypto_bounded_probe_safety_certification,
)
from algotrader.errors import ValidationError
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_capability_producer as capability_producer,
)
from algotrader.orchestration.crypto_tournament_v2_bounded_paper_probe_review import (
    build_crypto_tournament_v2_bounded_paper_probe_review,
)


_VENUE_ROLES = (
    "venue_refresh_manifest",
    "venue_universe",
    "orderability_metadata",
    "venue_router_input_manifest",
    "venue_runtime_visibility_status",
    "venue_refresh_source",
    "venue_visibility_operator_source",
    "venue_supervisor_source",
)
_SAFETY_AUTHORITY = {
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
_SAFETY_KEYS = {
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


CRYPTO_TOURNAMENT_V2_LIFECYCLE_PLANNER_SCHEMA_VERSION = (
    "v5_30_crypto_tournament_v2_lifecycle_planner_status_v1"
)
CRYPTO_TOURNAMENT_V2_LIFECYCLE_PLANNER_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_strategy_tournament/v2/bounded_paper_probe_lifecycle"
)
_DEFAULT_VENUE_ORDERABILITY_PATH = Path(
    "runs/crypto_universe_refresh/paper_read_latest/"
    "crypto_orderability_metadata.json"
)
_DEFAULT_RUNTIME_VISIBILITY_PATH = Path(
    "runs/crypto_paper_visibility/latest/latest_status.json"
)
_DEFAULT_SAFETY_RECEIPT_PATH = Path(
    "runs/crypto_strategy_tournament/v2/"
    "bounded_paper_probe_capabilities/safety_certification_receipt.json"
)
_EXPECTED_ACCOUNT_NAMES = (
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
)
_CREDENTIAL_NAMES = (
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
_NETWORK_TEST_FLAG_NAMES = (
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
)


__all__ = [
    "CRYPTO_TOURNAMENT_V2_LIFECYCLE_PLANNER_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_TOURNAMENT_V2_LIFECYCLE_PLANNER_SCHEMA_VERSION",
    "PLAN_SCHEMA_VERSION",
    "build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan",
    "exact_v530_operation_authorization_text",
    "run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner",
    "validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan",
    "main",
]


def build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan(
    terminal_evidence: Mapping[str, object] | None,
    *,
    venue_source_bytes: Mapping[str, bytes] | None = None,
    safety_certification: Mapping[str, object] | None = None,
    safety_certification_source_sha256: str = "",
    safety_kernel_source_bytes: bytes = b"",
    safety_certifier_source_bytes: bytes = b"",
    safety_focused_test_source_bytes: bytes = b"",
    expected_paper_account_id: str = "",
    terminal_source_sha256: str = "",
    as_of: datetime | str,
) -> dict[str, object]:
    """Build one immutable plan without accepting a caller-selected symbol."""

    evaluated_at = utc_datetime(as_of, "as_of")
    initial_review = build_crypto_tournament_v2_bounded_paper_probe_review(
        terminal_evidence,
        as_of=evaluated_at,
    )
    if initial_review.get("classification") == (
        "waiting_for_v5_25_terminal_evidence"
    ):
        return build_dormant_lifecycle_plan(evaluated_at)
    if initial_review.get("classification") != "blocked_by_operational_evidence":
        raise ValidationError(
            "terminal evidence does not identify a strategy-eligible winner."
        )
    if terminal_evidence is None:
        raise ValidationError("terminal evidence is required.")
    symbol = _terminal_symbol(terminal_evidence)
    terminal_binding = _terminal_binding(
        terminal_evidence,
        source_sha256=terminal_source_sha256,
    )
    if venue_source_bytes is None:
        raise ValidationError("target-scoped venue source bytes are required.")
    venue_binding = _venue_binding(
        venue_source_bytes,
        symbol=symbol,
        as_of=evaluated_at,
    )
    if safety_certification is None:
        raise ValidationError("safety certification is required.")
    _validate_safety_certification(
        safety_certification,
        as_of=evaluated_at,
        receipt_source_sha256=safety_certification_source_sha256,
        kernel_source_bytes=safety_kernel_source_bytes,
        certifier_source_bytes=safety_certifier_source_bytes,
        focused_test_source_bytes=safety_focused_test_source_bytes,
    )
    if symbol not in safety_certification.get("supported_symbols", []):
        raise ValidationError("winner is outside the safety certification.")
    account_id = str(expected_paper_account_id).strip()
    if not account_id:
        raise ValidationError("expected paper account id is required.")
    account_binding = build_alpaca_paper_account_binding(
        {"account_id": account_id},
        expected_account_configured=True,
        expected_account_matched=True,
    )
    safety_binding = {
        "policy_fingerprint": SAFETY_POLICY_FINGERPRINT,
        "certification_receipt_fingerprint": safety_certification[
            "receipt_fingerprint"
        ],
        "certification_source_sha256": safety_certification_source_sha256,
        "kernel_source_sha256": safety_certification["kernel_source_sha256"],
        "certifier_source_sha256": safety_certification[
            "certifier_source_sha256"
        ],
        "focused_test_source_sha256": safety_certification[
            "focused_test_source_sha256"
        ],
        "runtime_source_bundle_sha256": (
            _runtime_source_bundle_sha256()
        ),
        "certified_at": utc_datetime(
            safety_certification.get("as_of"),
            "safety_certification.as_of",
        ).isoformat(),
    }
    return build_ready_lifecycle_plan(
        symbol=symbol,
        terminal_binding=terminal_binding,
        venue_binding=venue_binding,
        safety_binding=safety_binding,
        account_binding=account_binding,
        as_of=evaluated_at,
    )


def exact_v530_operation_authorization_text(
    plan: Mapping[str, object],
) -> str:
    return exact_operation_authorization_text(plan)


def validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan(
    plan: Mapping[str, object],
) -> None:
    validate_lifecycle_plan(plan)


def _terminal_symbol(terminal: Mapping[str, object]) -> str:
    if (
        terminal.get("schema_version")
        != "v5_26_crypto_tournament_v2_forward_shadow_terminal_evidence_v1"
        or terminal.get("record_type")
        != "crypto_tournament_v2_forward_shadow_terminal_evidence"
        or terminal.get("classification")
        != "evidence_complete_for_bounded_paper_probe_review"
        or terminal.get("review_eligible_source") is not True
        or terminal.get("terminal_scoring_performed") is not True
    ):
        raise ValidationError("terminal winner evidence identity mismatch.")
    symbol = str(terminal.get("selected_symbol", "")).strip().upper()
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValidationError("terminal winner is outside the bounded probe.")
    candidate = _mapping(terminal.get("selected_candidate"), "selected_candidate")
    if candidate.get("symbol") != symbol:
        raise ValidationError("terminal winner candidate binding mismatch.")
    expected = stable_hash(
        {
            key: value
            for key, value in terminal.items()
            if key not in {"as_of", "evidence_export_fingerprint"}
        }
    )
    if terminal.get("evidence_export_fingerprint") != expected:
        raise ValidationError("terminal evidence export fingerprint mismatch.")
    return symbol


def _terminal_binding(
    terminal: Mapping[str, object],
    *,
    source_sha256: str,
) -> dict[str, object]:
    symbol = _terminal_symbol(terminal)
    source_sha = _sha256(source_sha256, "terminal_source_sha256")
    if source_sha != hashlib.sha256(_artifact_json_bytes(terminal)).hexdigest():
        raise ValidationError("terminal source hash mismatch.")
    source = _mapping(terminal.get("source_binding"), "terminal.source_binding")
    return {
        "selected_symbol": symbol,
        "selected_candidate": dict(
            _mapping(terminal.get("selected_candidate"), "selected_candidate")
        ),
        "classification": terminal["classification"],
        "preregistration_fingerprint": source["preregistration_fingerprint"],
        "activation_fingerprint": source["activation_fingerprint"],
        "state_fingerprint": source["state_fingerprint"],
        "terminal_evidence_fingerprint": source[
            "terminal_evidence_fingerprint"
        ],
        "terminal_closed_at": source["terminal_closed_at"],
        "evidence_export_fingerprint": terminal[
            "evidence_export_fingerprint"
        ],
        "terminal_source_sha256": source_sha,
    }


def _validate_terminal_evidence_shadow_binding(
    terminal: Mapping[str, object],
    frozen_state: Mapping[str, object],
) -> None:
    source = _mapping(
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
            _mapping(
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


def _venue_binding(
    raw: Mapping[str, bytes],
    *,
    symbol: str,
    as_of: datetime,
) -> dict[str, object]:
    missing = [
        role
        for role in _VENUE_ROLES
        if role not in raw or not isinstance(raw[role], bytes) or not raw[role]
    ]
    if missing:
        raise ValidationError(
            "target-scoped venue source bytes are incomplete: "
            + ",".join(missing)
        )
    parsed = {
        role: _json_mapping(raw[role], role)
        for role in (
            "venue_refresh_manifest",
            "venue_universe",
            "orderability_metadata",
            "venue_router_input_manifest",
            "venue_runtime_visibility_status",
        )
    }
    raw_hashes = {
        role: hashlib.sha256(raw[role]).hexdigest()
        for role in _VENUE_ROLES
    }
    normalized = capability_producer._normalize_venue(
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
    return {
        "target_symbol": symbol,
        "observed_at": normalized["as_of"],
        "bundle_fingerprint": stable_hash(normalized),
        "resolved_source_digests": dict(
            _mapping(
                normalized.get("resolved_source_digests"),
                "venue.resolved_source_digests",
            )
        ),
        "orderability_record": dict(normalized["records"][0]),
    }


def _validate_safety_certification(
    receipt: Mapping[str, object],
    *,
    as_of: datetime,
    receipt_source_sha256: str,
    kernel_source_bytes: bytes,
    certifier_source_bytes: bytes,
    focused_test_source_bytes: bytes,
) -> None:
    validate_crypto_bounded_probe_safety_certification(
        receipt,
        kernel_source_bytes=kernel_source_bytes,
        certifier_source_bytes=certifier_source_bytes,
        focused_test_source_bytes=focused_test_source_bytes,
    )
    certified_at = utc_datetime(receipt.get("as_of"), "safety.as_of")
    if certified_at > as_of or as_of - certified_at > timedelta(hours=168):
        raise ValidationError(
            "bounded-probe certification is stale or future-dated."
        )
    if set(receipt) != _SAFETY_KEYS:
        raise ValidationError("bounded-probe certification keys drifted.")
    unsigned = dict(receipt)
    fingerprint = _sha256(
        unsigned.pop("receipt_fingerprint"),
        "safety.receipt_fingerprint",
    )
    if fingerprint != stable_hash(unsigned):
        raise ValidationError("bounded-probe certification fingerprint mismatch.")
    if (
        receipt.get("schema_version")
        != "v5_27_crypto_bounded_probe_safety_certification_receipt_v1"
        or receipt.get("record_type")
        != "crypto_bounded_probe_safety_certification_receipt"
        or receipt.get("supported_symbols") != list(SUPPORTED_SYMBOLS)
        or receipt.get("policy_fingerprint") != SAFETY_POLICY_FINGERPRINT
        or receipt.get("offline_only") is not True
        or receipt.get("profit_claim") != "none"
        or receipt.get("authority") != _SAFETY_AUTHORITY
    ):
        raise ValidationError("bounded-probe certification identity mismatch.")
    utc_datetime(receipt.get("as_of"), "safety.as_of")
    source_digests = {
        "kernel_source_sha256": hashlib.sha256(kernel_source_bytes).hexdigest(),
        "certifier_source_sha256": hashlib.sha256(
            certifier_source_bytes
        ).hexdigest(),
        "focused_test_source_sha256": hashlib.sha256(
            focused_test_source_bytes
        ).hexdigest(),
    }
    if any(receipt.get(key) != value for key, value in source_digests.items()):
        raise ValidationError("bounded-probe certification source bytes drifted.")
    receipt_sha = _sha256(
        receipt_source_sha256,
        "safety_certification_source_sha256",
    )
    if receipt_sha != hashlib.sha256(_artifact_json_bytes(receipt)).hexdigest():
        raise ValidationError("safety certification source hash mismatch.")
    claims = _mapping(receipt.get("claims"), "safety.claims")
    if (
        claims.get("test_passed") is not True
        or claims.get("durable") is not True
        or claims.get("default_paused") is not True
        or claims.get("cancel_exit_path_certified") is not True
    ):
        raise ValidationError("bounded-probe certification claims are incomplete.")


def _runtime_source_bundle_sha256() -> str:
    source_root = Path(__file__).resolve().parents[2]
    source_digests: dict[str, str] = {}
    for role, relative_path in sorted(
        LIFECYCLE_RUNTIME_SOURCE_RELATIVE_PATHS.items()
    ):
        path = source_root / relative_path
        if not path.is_file():
            raise ValidationError(
                f"lifecycle runtime source is absent: {role}"
            )
        payload = path.read_bytes()
        if not payload:
            raise ValidationError(
                f"lifecycle runtime source is empty: {role}"
            )
        source_digests[role] = hashlib.sha256(payload).hexdigest()
    return stable_hash(source_digests)


def _artifact_json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _json_mapping(payload: bytes, field_name: str) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{field_name} is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be a JSON object.")
    return value


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return dict(value)


def _sha256(value: object, field_name: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise ValidationError(f"{field_name} must be a sha256 digest.")
    return text


def run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner(
    *,
    shadow_root: Path | str = (
        capability_producer.CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_LIFECYCLE_PLANNER_DEFAULT_OUTPUT_ROOT
    ),
    venue_orderability_path: Path | str = _DEFAULT_VENUE_ORDERABILITY_PATH,
    venue_runtime_visibility_path: Path | str = (
        _DEFAULT_RUNTIME_VISIBILITY_PATH
    ),
    safety_kernel_source_path: Path | str = (
        capability_producer._LOCAL_SOURCE_PATHS["safety_kernel_source"]
    ),
    safety_certifier_source_path: Path | str = (
        capability_producer._LOCAL_SOURCE_PATHS["safety_certifier_source"]
    ),
    safety_focused_test_source_path: Path | str = (
        capability_producer._LOCAL_SOURCE_PATHS["safety_focused_test_source"]
    ),
    safety_certification_receipt_path: Path | str = (
        _DEFAULT_SAFETY_RECEIPT_PATH
    ),
    timestamp: datetime | str | None = None,
    env: Mapping[str, str] | None = None,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Export terminal evidence once and build a local sealed plan."""

    evaluated_at = utc_datetime(
        timestamp or datetime.now(UTC),
        "timestamp",
    )
    source_env = _normalized_env(os.environ if env is None else env)
    preflight_blockers = _offline_planner_preflight_blockers(source_env)
    if preflight_blockers:
        return _planner_status(
            build_dormant_lifecycle_plan(evaluated_at),
            as_of=evaluated_at,
            classification="blocked_by_offline_preflight",
            terminal_source_bytes=None,
            blockers=preflight_blockers,
        )

    root = Path(output_root)
    terminal_evidence: Mapping[str, object] | None = None
    terminal_source_bytes: bytes | None = None
    try:
        shadow_path = Path(shadow_root)
        if (shadow_path / "frozen_state.json").is_file():
            state_packet = (
                capability_producer.run_crypto_tournament_v2_forward_shadow_state(
                    output_root=shadow_path,
                    as_of=evaluated_at,
                    write_artifacts=False,
                )
            )
            frozen_state = _mapping(
                state_packet.get("frozen_state"),
                "frozen_state",
            )
            if frozen_state.get("terminal_outcome_closed") is True:
                terminal_reference = (
                    capability_producer.export_crypto_tournament_v2_forward_shadow_terminal_evidence(
                        output_root=shadow_path,
                        as_of=evaluated_at,
                    )
                )
                terminal_path = root / "latest" / "terminal_evidence.json"
                if terminal_path.is_file():
                    terminal_source_bytes = terminal_path.read_bytes()
                    terminal_evidence = capability_producer._json_mapping(
                        terminal_source_bytes,
                        "terminal_evidence",
                    )
                    capability_producer._require_canonical_json(
                        terminal_source_bytes,
                        terminal_evidence,
                        "terminal_evidence",
                    )
                    validate_terminal_evidence_reference(
                        terminal_evidence,
                        terminal_reference,
                    )
                else:
                    terminal_evidence = terminal_reference
                    terminal_source_bytes = _artifact_json_bytes(
                        terminal_evidence
                    )
                _validate_terminal_evidence_shadow_binding(
                    terminal_evidence,
                    frozen_state,
                )

        if terminal_evidence is None:
            plan = build_dormant_lifecycle_plan(evaluated_at)
        else:
            venue_raw = _read_venue_source_family(
                venue_orderability_path=venue_orderability_path,
                venue_runtime_visibility_path=(
                    venue_runtime_visibility_path
                ),
            )
            safety_receipt_bytes = _read_canonical_json_source(
                safety_certification_receipt_path,
                "safety_certification_receipt",
            )
            safety_receipt = capability_producer._json_mapping(
                safety_receipt_bytes,
                "safety_certification_receipt",
            )
            safety_kernel = _read_source_bytes(
                safety_kernel_source_path,
                "safety_kernel_source",
            )
            safety_certifier = _read_source_bytes(
                safety_certifier_source_path,
                "safety_certifier_source",
            )
            safety_test = _read_source_bytes(
                safety_focused_test_source_path,
                "safety_focused_test_source",
            )
            expected_account = _first_nonempty(
                source_env,
                _EXPECTED_ACCOUNT_NAMES,
            )
            plan = (
                build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan(
                    terminal_evidence,
                    venue_source_bytes=venue_raw,
                    safety_certification=safety_receipt,
                    safety_certification_source_sha256=hashlib.sha256(
                        safety_receipt_bytes
                    ).hexdigest(),
                    safety_kernel_source_bytes=safety_kernel,
                    safety_certifier_source_bytes=safety_certifier,
                    safety_focused_test_source_bytes=safety_test,
                    expected_paper_account_id=expected_account,
                    terminal_source_sha256=hashlib.sha256(
                        terminal_source_bytes
                    ).hexdigest(),
                    as_of=evaluated_at,
                )
            )
        validate_lifecycle_plan(plan)
    except (OSError, ValidationError) as exc:
        safe_plan = build_dormant_lifecycle_plan(evaluated_at)
        status = _planner_status(
            safe_plan,
            as_of=evaluated_at,
            classification="blocked_by_local_evidence",
            terminal_source_bytes=terminal_source_bytes,
            blockers=[str(exc)],
        )
        if write_artifacts:
            _publish_planner_artifacts(
                root,
                plan=safe_plan,
                status=status,
                terminal_source_bytes=terminal_source_bytes,
                authorization_text="",
            )
        return status

    classification = str(plan["classification"])
    ready = classification == "ready_for_exact_operation_authorization"
    blockers = (
        [] if ready else ["v5_25_terminal_winner_not_available"]
    )
    status = _planner_status(
        plan,
        as_of=evaluated_at,
        classification=classification,
        terminal_source_bytes=terminal_source_bytes,
        blockers=blockers,
    )
    if write_artifacts:
        _publish_planner_artifacts(
            root,
            plan=plan,
            status=status,
            terminal_source_bytes=terminal_source_bytes,
            authorization_text=(
                exact_operation_authorization_text(plan) if ready else ""
            ),
        )
    return status


def _planner_status(
    plan: Mapping[str, object],
    *,
    as_of: datetime,
    classification: str,
    terminal_source_bytes: bytes | None,
    blockers: Sequence[str],
) -> dict[str, object]:
    plan_bytes = canonical_json_bytes(plan)
    ready = classification == "ready_for_exact_operation_authorization"
    authorization_sha = (
        str(plan.get("required_authorization_sha256", "")) if ready else ""
    )
    status: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_LIFECYCLE_PLANNER_SCHEMA_VERSION
        ),
        "record_type": "crypto_tournament_v2_lifecycle_planner_status",
        "as_of": as_of.isoformat(),
        "classification": classification,
        "plan_classification": plan["classification"],
        "plan_fingerprint": plan["plan_fingerprint"],
        "plan_source_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "terminal_source_sha256": (
            ""
            if terminal_source_bytes is None
            else hashlib.sha256(terminal_source_bytes).hexdigest()
        ),
        "authorization_request_sha256": authorization_sha,
        "authorization_request_file_emitted": ready,
        "ready_for_exact_operation_authorization": ready,
        "blockers": list(dict.fromkeys(str(item) for item in blockers)),
        "offline_only": True,
        "network_access_occurred": False,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_mutation_authorized": False,
        "paper_mutation_occurred": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "next_action": (
            "review_exact_authorization_request_without_auto_grant"
            if ready
            else (
                "continue_receipt_bound_forward_shadow_accrual"
                if classification == "dormant_pending_terminal_winner"
                else "repair_local_plan_evidence_without_broker_access"
            )
        ),
    }
    status["planner_status_fingerprint"] = stable_hash(status)
    return status


def _publish_planner_artifacts(
    root: Path,
    *,
    plan: Mapping[str, object],
    status: Mapping[str, object],
    terminal_source_bytes: bytes | None,
    authorization_text: str,
) -> None:
    latest = root / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    _atomic_write(latest / "lifecycle_plan.json", canonical_json_bytes(plan))
    if terminal_source_bytes is not None:
        terminal_path = latest / "terminal_evidence.json"
        if (
            terminal_path.is_file()
            and terminal_path.read_bytes() != terminal_source_bytes
        ):
            raise ValidationError(
                "sealed terminal evidence conflicts with existing bytes."
            )
        if not terminal_path.is_file():
            _atomic_write(terminal_path, terminal_source_bytes)
    authorization_payload = (
        (authorization_text + "\n").encode("utf-8")
        if authorization_text
        else b""
    )
    _atomic_write(
        latest / "authorization_request.txt",
        authorization_payload,
    )
    _atomic_write(
        latest / "planner_status.json",
        canonical_json_bytes(status),
    )


def _read_venue_source_family(
    *,
    venue_orderability_path: Path | str,
    venue_runtime_visibility_path: Path | str,
) -> dict[str, bytes]:
    venue_root = Path(venue_orderability_path).parent
    paths: dict[str, Path | str] = {
        "venue_refresh_manifest": venue_root / "manifest.json",
        "venue_universe": venue_root / "crypto_universe.json",
        "orderability_metadata": venue_orderability_path,
        "venue_router_input_manifest": (
            venue_root / "crypto_router_input_manifest.json"
        ),
        "venue_runtime_visibility_status": venue_runtime_visibility_path,
        "venue_refresh_source": (
            capability_producer._LOCAL_SOURCE_PATHS["venue_refresh_source"]
        ),
        "venue_visibility_operator_source": (
            capability_producer._LOCAL_SOURCE_PATHS[
                "venue_visibility_operator_source"
            ]
        ),
        "venue_supervisor_source": (
            capability_producer._LOCAL_SOURCE_PATHS["venue_supervisor_source"]
        ),
    }
    json_roles = {
        "venue_refresh_manifest",
        "venue_universe",
        "orderability_metadata",
        "venue_router_input_manifest",
        "venue_runtime_visibility_status",
    }
    return {
        role: (
            _read_canonical_json_source(paths[role], role)
            if role in json_roles
            else _read_source_bytes(paths[role], role)
        )
        for role in _VENUE_ROLES
    }


def _read_canonical_json_source(
    path: Path | str,
    role: str,
) -> bytes:
    payload = _read_source_bytes(path, role)
    parsed = capability_producer._json_mapping(payload, role)
    capability_producer._require_canonical_json(payload, parsed, role)
    return payload


def _read_source_bytes(path: Path | str, role: str) -> bytes:
    source = Path(path)
    if not source.is_file():
        raise ValidationError(f"required local source is absent: {role}")
    payload = source.read_bytes()
    if not payload:
        raise ValidationError(f"required local source is empty: {role}")
    return payload


def _normalized_env(raw: Mapping[str, str]) -> dict[str, str]:
    return {
        str(key): str(value).strip()
        for key, value in raw.items()
        if value is not None
    }


def _first_nonempty(
    values: Mapping[str, str],
    names: Sequence[str],
) -> str:
    return next(
        (values.get(name, "") for name in names if values.get(name)),
        "",
    )


def _offline_planner_preflight_blockers(
    env: Mapping[str, str],
) -> list[str]:
    blockers: list[str] = []
    profile = env.get("APP_PROFILE", "").lower()
    if profile in {"paper", "live"}:
        blockers.append("offline_planner_rejects_paper_or_live_profile")
    if any(env.get(name) for name in _CREDENTIAL_NAMES):
        blockers.append("offline_planner_requires_credential_free_process")
    if any(env.get(name) for name in _NETWORK_TEST_FLAG_NAMES):
        blockers.append("offline_planner_rejects_network_test_flags")
    for name in (
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        endpoint = env.get(name, "").lower()
        if (
            endpoint
            and "api.alpaca.markets" in endpoint
            and "paper" not in endpoint
        ):
            blockers.append("offline_planner_rejects_live_endpoint")
            break
    return list(dict.fromkeys(blockers))


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one sealed local V5.30 lifecycle plan.",
    )
    parser.add_argument(
        "--shadow-root",
        default=str(
            capability_producer.CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(
            CRYPTO_TOURNAMENT_V2_LIFECYCLE_PLANNER_DEFAULT_OUTPUT_ROOT
        ),
    )
    parser.add_argument(
        "--venue-orderability-path",
        default=str(_DEFAULT_VENUE_ORDERABILITY_PATH),
    )
    parser.add_argument(
        "--venue-runtime-visibility-path",
        default=str(_DEFAULT_RUNTIME_VISIBILITY_PATH),
    )
    parser.add_argument(
        "--safety-kernel-source-path",
        default=str(
            capability_producer._LOCAL_SOURCE_PATHS["safety_kernel_source"]
        ),
    )
    parser.add_argument(
        "--safety-certifier-source-path",
        default=str(
            capability_producer._LOCAL_SOURCE_PATHS["safety_certifier_source"]
        ),
    )
    parser.add_argument(
        "--safety-focused-test-source-path",
        default=str(
            capability_producer._LOCAL_SOURCE_PATHS[
                "safety_focused_test_source"
            ]
        ),
    )
    parser.add_argument(
        "--safety-certification-receipt-path",
        default=str(_DEFAULT_SAFETY_RECEIPT_PATH),
    )
    parser.add_argument("--no-write", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = run_crypto_tournament_v2_bounded_paper_probe_lifecycle_planner(
        shadow_root=args.shadow_root,
        output_root=args.output_root,
        venue_orderability_path=args.venue_orderability_path,
        venue_runtime_visibility_path=args.venue_runtime_visibility_path,
        safety_kernel_source_path=args.safety_kernel_source_path,
        safety_certifier_source_path=args.safety_certifier_source_path,
        safety_focused_test_source_path=(
            args.safety_focused_test_source_path
        ),
        safety_certification_receipt_path=(
            args.safety_certification_receipt_path
        ),
        write_artifacts=not args.no_write,
    )
    print(json.dumps(status, indent=2, sort_keys=True))
    return (
        0
        if status.get("classification")
        == "ready_for_exact_operation_authorization"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
