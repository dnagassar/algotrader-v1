"""Executable offline certification for the bounded crypto probe safety kernel.

The certifier uses only local temporary SQLite state and deterministic inputs.
It has no broker client, credential access, network path, order construction,
or paper/live authority.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Mapping

from algotrader.errors import ValidationError
from algotrader.execution import crypto_bounded_probe_safety as safety_kernel
from algotrader.execution.crypto_bounded_probe_safety import (
    CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT,
    CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS,
    CryptoBoundedProbeObservation,
    CryptoBoundedProbeSafetyStore,
    build_crypto_bounded_probe_safety_policy,
    evaluate_crypto_bounded_probe_safety,
)


CRYPTO_BOUNDED_PROBE_SAFETY_CERTIFICATION_SCHEMA_VERSION = (
    "v5_27_crypto_bounded_probe_safety_certification_receipt_v1"
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
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
_AUTHORITY = {
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
_LOADED_KERNEL_SOURCE_SHA256 = hashlib.sha256(
    Path(str(safety_kernel.__file__)).read_bytes()
).hexdigest()
_LOADED_CERTIFIER_SOURCE_SHA256 = hashlib.sha256(
    Path(__file__).read_bytes()
).hexdigest()
_CANONICAL_FOCUSED_TEST_PATH = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "unit"
    / "test_crypto_bounded_probe_safety.py"
)

__all__ = [
    "CRYPTO_BOUNDED_PROBE_SAFETY_CERTIFICATION_SCHEMA_VERSION",
    "build_crypto_bounded_probe_safety_certification",
    "run_crypto_bounded_probe_safety_certification",
    "validate_crypto_bounded_probe_safety_certification",
    "main",
]


def build_crypto_bounded_probe_safety_certification(
    *,
    kernel_source_bytes: bytes,
    certifier_source_bytes: bytes,
    focused_test_source_bytes: bytes,
    as_of: datetime | str,
) -> dict[str, object]:
    """Execute the frozen safety checks and return one path-free receipt."""

    observed_at = _utc_datetime(as_of, "as_of")
    _validate_source_markers(
        kernel_source_bytes,
        certifier_source_bytes,
        focused_test_source_bytes,
    )
    _validate_loaded_runtime_bindings(
        kernel_source_bytes,
        certifier_source_bytes,
        focused_test_source_bytes,
    )
    with TemporaryDirectory(prefix="crypto-bounded-probe-cert-") as directory:
        workspace = Path(directory)
        symbol_results = [
            _certify_symbol(workspace, symbol, observed_at)
            for symbol in CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS
        ]
    claims: dict[str, object] = {
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
    receipt: dict[str, object] = {
        "schema_version": (
            CRYPTO_BOUNDED_PROBE_SAFETY_CERTIFICATION_SCHEMA_VERSION
        ),
        "record_type": "crypto_bounded_probe_safety_certification_receipt",
        "as_of": observed_at.isoformat(),
        "supported_symbols": list(CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS),
        "policy_fingerprint": (
            CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
        ),
        "policy_manifest": build_crypto_bounded_probe_safety_policy(),
        "kernel_source_sha256": hashlib.sha256(kernel_source_bytes).hexdigest(),
        "certifier_source_sha256": hashlib.sha256(
            certifier_source_bytes
        ).hexdigest(),
        "focused_test_source_sha256": hashlib.sha256(
            focused_test_source_bytes
        ).hexdigest(),
        "certification_checks": list(_CERTIFICATION_CHECKS),
        "symbol_results": symbol_results,
        "claims": claims,
        "offline_only": True,
        "profit_claim": "none",
        "authority": dict(_AUTHORITY),
    }
    receipt["receipt_fingerprint"] = _stable_hash(receipt)
    validate_crypto_bounded_probe_safety_certification(
        receipt,
        kernel_source_bytes=kernel_source_bytes,
        certifier_source_bytes=certifier_source_bytes,
        focused_test_source_bytes=focused_test_source_bytes,
    )
    return receipt


def run_crypto_bounded_probe_safety_certification(
    *,
    kernel_source_path: Path | str,
    certifier_source_path: Path | str,
    focused_test_source_path: Path | str,
    output_path: Path | str,
    as_of: datetime | str,
    write_artifact: bool = True,
) -> dict[str, object]:
    """Resolve exact local source bytes, execute checks, and optionally write."""

    kernel_bytes = _read_required_bytes(kernel_source_path, "kernel_source_path")
    certifier_bytes = _read_required_bytes(
        certifier_source_path,
        "certifier_source_path",
    )
    test_bytes = _read_required_bytes(
        focused_test_source_path,
        "focused_test_source_path",
    )
    receipt = build_crypto_bounded_probe_safety_certification(
        kernel_source_bytes=kernel_bytes,
        certifier_source_bytes=certifier_bytes,
        focused_test_source_bytes=test_bytes,
        as_of=as_of,
    )
    if write_artifact:
        path = _local_path(output_path, "output_path")
        _write_bytes_atomic(path, _json_bytes(receipt))
    return receipt


def validate_crypto_bounded_probe_safety_certification(
    receipt: Mapping[str, object],
    *,
    kernel_source_bytes: bytes,
    certifier_source_bytes: bytes,
    focused_test_source_bytes: bytes,
) -> None:
    """Validate receipt shape, source bindings, semantics, and fingerprint."""

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
    if set(receipt) != expected_keys:
        raise ValidationError("bounded-probe certification keys drifted.")
    fingerprint = _sha256(
        receipt.get("receipt_fingerprint"),
        "receipt_fingerprint",
    )
    unsigned = dict(receipt)
    unsigned.pop("receipt_fingerprint")
    if fingerprint != _stable_hash(unsigned):
        raise ValidationError("bounded-probe certification fingerprint mismatch.")
    if (
        receipt.get("schema_version")
        != CRYPTO_BOUNDED_PROBE_SAFETY_CERTIFICATION_SCHEMA_VERSION
        or receipt.get("record_type")
        != "crypto_bounded_probe_safety_certification_receipt"
        or receipt.get("supported_symbols")
        != list(CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS)
        or receipt.get("policy_fingerprint")
        != CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
        or receipt.get("policy_manifest")
        != build_crypto_bounded_probe_safety_policy()
        or receipt.get("offline_only") is not True
        or receipt.get("profit_claim") != "none"
        or receipt.get("authority") != _AUTHORITY
    ):
        raise ValidationError("bounded-probe certification identity mismatch.")
    _utc_datetime(receipt.get("as_of"), "receipt.as_of")
    _validate_source_markers(
        kernel_source_bytes,
        certifier_source_bytes,
        focused_test_source_bytes,
    )
    expected_source_hashes = {
        "kernel_source_sha256": hashlib.sha256(kernel_source_bytes).hexdigest(),
        "certifier_source_sha256": hashlib.sha256(
            certifier_source_bytes
        ).hexdigest(),
        "focused_test_source_sha256": hashlib.sha256(
            focused_test_source_bytes
        ).hexdigest(),
    }
    if any(receipt.get(key) != value for key, value in expected_source_hashes.items()):
        raise ValidationError("bounded-probe certification source bytes drifted.")
    _validate_loaded_runtime_bindings(
        kernel_source_bytes,
        certifier_source_bytes,
        focused_test_source_bytes,
    )
    if receipt.get("certification_checks") != list(_CERTIFICATION_CHECKS):
        raise ValidationError("bounded-probe certification checks drifted.")
    results = receipt.get("symbol_results")
    if not isinstance(results, list) or len(results) != len(
        CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS
    ):
        raise ValidationError("bounded-probe symbol results are incomplete.")
    for result, symbol in zip(
        results,
        CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS,
        strict=True,
    ):
        if result != {
            "symbol": symbol,
            "passed": True,
            "passed_checks": list(_CERTIFICATION_CHECKS),
        }:
            raise ValidationError("bounded-probe symbol certification failed.")
    if receipt.get("claims") != {
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
    }:
        raise ValidationError("bounded-probe certification claims drifted.")


def _certify_symbol(
    workspace: Path,
    symbol: str,
    as_of: datetime,
) -> dict[str, object]:
    checks: list[str] = []
    default_store = CryptoBoundedProbeSafetyStore(
        workspace / f"{symbol}-default.sqlite3"
    )
    paused = default_store.initialize(selected_symbol=symbol, as_of=as_of)
    paused_verdict = evaluate_crypto_bounded_probe_safety(
        paused,
        _observation(symbol, "entry", as_of),
    )
    _require_blocked(paused_verdict, "operator_control_paused")
    checks.append("default_pause_blocks_entry")

    envelope_store = CryptoBoundedProbeSafetyStore(
        workspace / f"{symbol}-envelope.sqlite3"
    )
    envelope_store.initialize(selected_symbol=symbol, as_of=as_of)
    enabled = envelope_store.record_operator_control(
        entry_enabled=True,
        authorization_fingerprint=_SHA_A,
        as_of=as_of,
    )
    admitted = evaluate_crypto_bounded_probe_safety(
        enabled,
        _observation(symbol, "entry", as_of),
    )
    if admitted["local_safety_admitted"] is not True:
        raise ValidationError("bounded-probe exact entry boundary was rejected.")
    for notional in ("0.99999999", "10.00000001"):
        _require_blocked(
            evaluate_crypto_bounded_probe_safety(
                enabled,
                _observation(
                    symbol,
                    "entry",
                    as_of,
                    requested_notional_usd=notional,
                ),
            ),
            "entry_notional_out_of_bounds",
        )
    checks.append("exact_one_to_ten_usd_entry_envelope")
    for overrides, blocker in (
        ({"available_cash_usd": "9.99"}, "insufficient_cash"),
        ({"margin_used": True}, "margin_not_allowed"),
        ({"account_trading_blocked": True}, "account_trading_blocked"),
    ):
        _require_blocked(
            evaluate_crypto_bounded_probe_safety(
                enabled,
                _observation(symbol, "entry", as_of, **overrides),
            ),
            blocker,
        )
    checks.append("cash_margin_and_account_gates")
    for overrides, blocker in (
        (
            {"market_data_as_of": as_of - timedelta(hours=2, microseconds=1)},
            "market_data_stale",
        ),
        (
            {"market_data_as_of": as_of + timedelta(microseconds=1)},
            "market_data_from_future",
        ),
        (
            {"capability_valid_until": as_of - timedelta(microseconds=1)},
            "capability_expired",
        ),
    ):
        _require_blocked(
            evaluate_crypto_bounded_probe_safety(
                enabled,
                _observation(symbol, "entry", as_of, **overrides),
            ),
            blocker,
        )
    checks.append("stale_future_and_expired_entry_blocked")
    for overrides, blocker in (
        ({"broker_ambiguity": True}, "broker_ambiguity"),
        ({"unexpected_symbol_exposure": True}, "cross_symbol_exposure"),
    ):
        _require_blocked(
            evaluate_crypto_bounded_probe_safety(
                enabled,
                _observation(symbol, "entry", as_of, **overrides),
            ),
            blocker,
        )
    checks.append("ambiguity_and_unexpected_state_blocked")

    loss_store = CryptoBoundedProbeSafetyStore(
        workspace / f"{symbol}-loss.sqlite3"
    )
    loss_store.initialize(selected_symbol=symbol, as_of=as_of)
    loss_store.record_operator_control(
        entry_enabled=True,
        authorization_fingerprint=_SHA_A,
        as_of=as_of,
    )
    below = loss_store.record_loss_observation(
        cumulative_net_pnl_usd="-1.99999999",
        loss_basis_fingerprint=_SHA_B,
        as_of=as_of + timedelta(minutes=1),
    )
    if below.loss_halt_latched:
        raise ValidationError("bounded-probe loss halt triggered below boundary.")
    latched = loss_store.record_loss_observation(
        cumulative_net_pnl_usd="-2",
        loss_basis_fingerprint=_SHA_B,
        as_of=as_of + timedelta(minutes=2),
    )
    if not latched.loss_halt_latched or latched.entry_enabled:
        raise ValidationError("bounded-probe exact loss boundary did not halt.")
    checks.append("exact_two_usd_loss_latched")
    replay = CryptoBoundedProbeSafetyStore(loss_store.path).load()
    if not replay.loss_halt_latched or replay.maximum_observed_loss_usd != 2:
        raise ValidationError("bounded-probe durable loss state did not replay.")
    checks.append("maximum_loss_and_halt_survive_restart")
    recovered = loss_store.record_loss_observation(
        cumulative_net_pnl_usd="1",
        loss_basis_fingerprint=_SHA_B,
        as_of=as_of + timedelta(minutes=3),
    )
    if not recovered.loss_halt_latched or recovered.maximum_observed_loss_usd != 2:
        raise ValidationError("bounded-probe loss halt reset after recovery.")
    checks.append("later_profit_cannot_reset_halt")
    risk_as_of = as_of + timedelta(days=10)
    cancel_verdict = evaluate_crypto_bounded_probe_safety(
        recovered,
        _observation(
            symbol,
            "cancel",
            risk_as_of,
            capability_valid_until=as_of,
            market_data_as_of=None,
            cumulative_net_pnl_usd="1",
        ),
    )
    if cancel_verdict["risk_reducing_action_admitted"] is not True:
        raise ValidationError("bounded-probe halted cancel path was rejected.")
    checks.append("halted_expired_cancel_path_admitted_locally")
    exit_verdict = evaluate_crypto_bounded_probe_safety(
        recovered,
        _observation(
            symbol,
            "exit",
            risk_as_of,
            capability_valid_until=as_of,
            market_data_as_of=None,
            cumulative_net_pnl_usd="1",
        ),
    )
    if exit_verdict["risk_reducing_action_admitted"] is not True:
        raise ValidationError("bounded-probe halted exit path was rejected.")
    checks.append("halted_expired_full_exit_path_admitted_locally")

    claim_store = CryptoBoundedProbeSafetyStore(
        workspace / f"{symbol}-entry-claim.sqlite3"
    )
    claim_store.initialize(selected_symbol=symbol, as_of=as_of)
    claim_store.record_operator_control(
        entry_enabled=True,
        authorization_fingerprint=_SHA_A,
        as_of=as_of,
    )

    def claim(fingerprint: str) -> dict[str, object]:
        return CryptoBoundedProbeSafetyStore(claim_store.path).evaluate_and_claim(
            _observation(symbol, "entry", as_of),
            claim_fingerprint=fingerprint,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(claim, (_SHA_B, _SHA_C)))
    if sum(result["verdict"]["claim_recorded"] is True for result in outcomes) != 1:
        raise ValidationError("bounded-probe entry claim was not atomic.")
    checks.append("entry_attempt_claim_is_atomic")
    if CryptoBoundedProbeSafetyStore(claim_store.path).load().entry_attempt_count != 1:
        raise ValidationError("bounded-probe entry budget did not survive restart.")
    checks.append("entry_attempt_budget_survives_restart")

    for action, counter in (
        ("cancel", "cancel_attempt_count"),
        ("exit", "exit_attempt_count"),
    ):
        action_store = CryptoBoundedProbeSafetyStore(
            workspace / f"{symbol}-{action}-claim.sqlite3"
        )
        action_store.initialize(selected_symbol=symbol, as_of=as_of)
        result = action_store.evaluate_and_claim(
            _observation(symbol, action, as_of),
            claim_fingerprint=_SHA_B,
        )
        replayed = CryptoBoundedProbeSafetyStore(action_store.path).load()
        if (
            result["verdict"]["claim_recorded"] is not True
            or getattr(replayed, counter) != 1
        ):
            raise ValidationError(
                f"bounded-probe {action} budget did not survive restart."
            )
        checks.append(f"{action}_attempt_budget_survives_restart")
    for verdict in (paused_verdict, admitted, cancel_verdict, exit_verdict):
        if any(verdict.get(key) is not False for key in (
            "broker_mutation_authorized",
            "paper_submit_authorized",
            "paper_mutation_authorized",
            "capital_allocation_authorized",
            "live_authorized",
        )):
            raise ValidationError("bounded-probe verdict granted authority.")
    checks.append("all_authority_fields_remain_false")
    if tuple(checks) != _CERTIFICATION_CHECKS:
        raise ValidationError("bounded-probe certification check order drifted.")
    return {
        "symbol": symbol,
        "passed": True,
        "passed_checks": list(checks),
    }


def _observation(
    symbol: str,
    action: str,
    as_of: datetime,
    **overrides: object,
) -> CryptoBoundedProbeObservation:
    values: dict[str, object] = {
        "symbol": symbol,
        "action": action,
        "as_of": as_of,
        "broker_snapshot_as_of": as_of,
        "capability_valid_until": as_of + timedelta(hours=1),
        "market_data_as_of": as_of,
        "requested_notional_usd": Decimal("10") if action == "entry" else 0,
        "requested_exit_quantity": Decimal("1") if action == "exit" else 0,
        "principal_at_risk_usd": 0,
        "available_cash_usd": 10,
        "position_quantity": Decimal("1") if action == "exit" else 0,
        "position_count": 1 if action == "exit" else 0,
        "open_order_count": 1 if action == "cancel" else 0,
        "loss_context_complete": True,
        "cumulative_net_pnl_usd": 0,
        "observed_order_fingerprint": _SHA_A if action == "cancel" else "",
        "cancel_target_fingerprint": _SHA_A if action == "cancel" else "",
    }
    values.update(overrides)
    return CryptoBoundedProbeObservation(**values)  # type: ignore[arg-type]


def _require_blocked(verdict: Mapping[str, object], blocker: str) -> None:
    blockers = verdict.get("blockers")
    if (
        verdict.get("local_safety_admitted") is not False
        or not isinstance(blockers, list)
        or blocker not in blockers
    ):
        raise ValidationError(f"bounded-probe check did not block: {blocker}.")


def _validate_source_markers(
    kernel_source_bytes: bytes,
    certifier_source_bytes: bytes,
    focused_test_source_bytes: bytes,
) -> None:
    markers = (
        (
            kernel_source_bytes,
            b"CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT",
            "kernel",
        ),
        (
            certifier_source_bytes,
            b"build_crypto_bounded_probe_safety_certification",
            "certifier",
        ),
        (
            focused_test_source_bytes,
            b"test_concurrent_entry_claims_admit_exactly_one_attempt",
            "focused test",
        ),
    )
    for payload, marker, label in markers:
        if not isinstance(payload, bytes) or not payload or marker not in payload:
            raise ValidationError(f"bounded-probe {label} source is invalid.")


def _validate_loaded_runtime_bindings(
    kernel_source_bytes: bytes,
    certifier_source_bytes: bytes,
    focused_test_source_bytes: bytes,
) -> None:
    """Bind certified bytes to loaded code and the canonical focused test.

    The certifier executes already-imported Python objects. Comparing only
    caller-provided source hashes would allow a stale installed runtime to
    certify different checkout bytes. The two loaded digests are captured at
    module import, and the focused test is supporting provenance whose exact
    canonical repository bytes must be present (it is not claimed to execute
    inside this function).
    """

    if hashlib.sha256(kernel_source_bytes).hexdigest() != (
        _LOADED_KERNEL_SOURCE_SHA256
    ):
        raise ValidationError(
            "bounded-probe kernel source does not match loaded runtime."
        )
    if hashlib.sha256(certifier_source_bytes).hexdigest() != (
        _LOADED_CERTIFIER_SOURCE_SHA256
    ):
        raise ValidationError(
            "bounded-probe certifier source does not match loaded runtime."
        )
    if (
        not _CANONICAL_FOCUSED_TEST_PATH.is_file()
        or _CANONICAL_FOCUSED_TEST_PATH.is_symlink()
    ):
        raise ValidationError(
            "bounded-probe canonical focused test is unavailable."
        )
    if focused_test_source_bytes != _CANONICAL_FOCUSED_TEST_PATH.read_bytes():
        raise ValidationError(
            "bounded-probe focused test source does not match canonical bytes."
        )


def _read_required_bytes(path: Path | str, field_name: str) -> bytes:
    local = _local_path(path, field_name)
    if not local.is_file() or local.is_symlink():
        raise ValidationError(f"{field_name} must resolve to a regular file.")
    payload = local.read_bytes()
    if not payload:
        raise ValidationError(f"{field_name} cannot be empty.")
    return payload


def _local_path(value: Path | str, field_name: str) -> Path:
    text = str(value).strip()
    if not text or "://" in text or text.startswith(("\\\\", "//")):
        raise ValidationError(f"{field_name} must be a local filesystem path.")
    return Path(text)


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
    return parsed.astimezone(timezone.utc)


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


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kernel-source-path",
        default="src/algotrader/execution/crypto_bounded_probe_safety.py",
    )
    parser.add_argument(
        "--certifier-source-path",
        default=(
            "src/algotrader/execution/"
            "crypto_bounded_probe_safety_certification.py"
        ),
    )
    parser.add_argument(
        "--focused-test-source-path",
        default="tests/unit/test_crypto_bounded_probe_safety.py",
    )
    parser.add_argument(
        "--output-path",
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
    receipt = run_crypto_bounded_probe_safety_certification(
        kernel_source_path=args.kernel_source_path,
        certifier_source_path=args.certifier_source_path,
        focused_test_source_path=args.focused_test_source_path,
        output_path=args.output_path,
        as_of=args.as_of,
        write_artifact=not args.no_write,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
