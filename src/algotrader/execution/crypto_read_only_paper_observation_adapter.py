"""V5.33 Bounded read-only paper broker observation adapter.

This module performs a single, bounded, explicitly authorized, read-only paper
account observation for BTCUSD, producing cross-bound receipts.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import PaperObservationReader

PRODUCTION_OBSERVATION_SCHEMA = "v5_33_production_broker_observation_receipt_v1"
PRODUCTION_INVOCATION_SCHEMA = "v5_33_production_invocation_receipt_v1"
OFFLINE_FIXTURE_SCHEMA = "v5_33_offline_fixture_replay_receipt_v1"
ADAPTER_VERSION = "1.0"
TARGET_SYMBOL = "BTCUSD"
SUPPORTED_ASSET_CLASS = "crypto"
EXPECTED_PAPER_ENDPOINT = "https://paper-api.alpaca.markets"

class PreflightCheckError(ValidationError):
    """Raised when any preflight safety check fails."""
    pass

class BrokerObservationError(ValidationError):
    """Raised when broker state cannot be observed or fails checks."""
    pass

def compute_source_bundle_digest(repo_root: Path) -> tuple[str, dict[str, str]]:
    relative_paths = [
        "src/algotrader/execution/crypto_read_only_paper_observation_adapter.py",
        "src/algotrader/execution/alpaca_sdk_client.py",
        "src/algotrader/execution/alpaca_client.py",
        "src/algotrader/cli.py",
        "src/algotrader/execution/crypto_supervised_readiness_trial.py",
        "scripts/run_crypto_paper_broker_observation.ps1",
        "scripts/consume_crypto_observation_receipt.ps1",
        "scripts/verify_crypto_preflight.ps1",
        "scripts/verify_crypto_readiness_replay.ps1"
    ]
    manifest = {}
    h = hashlib.sha256()
    for rel_path in sorted(relative_paths):
        full_path = repo_root / rel_path
        if not full_path.is_file():
            raise FileNotFoundError(f"Missing manifest file: {rel_path}")
        content = full_path.read_bytes()
        normalized_content = content.replace(b"\r\n", b"\n")
        file_hash = hashlib.sha256(normalized_content).hexdigest()
        manifest[rel_path] = file_hash
        h.update(f"{rel_path}:{file_hash}\n".encode("utf-8"))

    return h.hexdigest(), manifest

def validate_preflight_gates(
    *,
    app_profile: str | None,
    endpoint: str | None,
    key_id: str | None,
    secret_key: str | None,
    expected_account_id: str | None,
    paper_broker_read_authorized: bool,
    allow_network: bool,
) -> None:
    if not app_profile or app_profile.strip().lower() != "paper":
        raise PreflightCheckError("preflight_failed_profile_not_paper")

    if not endpoint:
        raise PreflightCheckError("preflight_failed_endpoint_missing")
    normalized_endpoint = endpoint.strip().lower().rstrip("/")
    if normalized_endpoint != EXPECTED_PAPER_ENDPOINT:
        raise PreflightCheckError("preflight_failed_endpoint_not_paper")

    if not key_id or not key_id.strip() or not secret_key or not secret_key.strip():
        raise PreflightCheckError("preflight_failed_credentials_incomplete")

    if not expected_account_id or not expected_account_id.strip():
        raise PreflightCheckError("preflight_failed_expected_account_missing")

    if not paper_broker_read_authorized:
        raise PreflightCheckError("preflight_failed_not_authorized")

    if not allow_network:
        raise PreflightCheckError("preflight_failed_network_blocked")

def get_production_preflight_inputs() -> dict[str, Any]:
    env = os.environ
    app_profile = env.get("APP_PROFILE")

    key_id = None
    secret_key = None
    if env.get("ALPACA_API_KEY") and (env.get("ALPACA_SECRET_KEY") or env.get("ALPACA_API_SECRET_KEY")):
        key_id = env.get("ALPACA_API_KEY")
        secret_key = env.get("ALPACA_SECRET_KEY") or env.get("ALPACA_API_SECRET_KEY")
    elif env.get("APCA_API_KEY_ID") and env.get("APCA_API_SECRET_KEY"):
        key_id = env.get("APCA_API_KEY_ID")
        secret_key = env.get("APCA_API_SECRET_KEY")

    expected_account_id = env.get("ALPACA_EXPECTED_PAPER_ACCOUNT_ID")

    endpoint = None
    for var_name in ("ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL", "ALPACA_BASE_URL"):
        if var_name in env:
            endpoint = env.get(var_name)
            break

    return {
        "app_profile": app_profile,
        "endpoint": endpoint,
        "key_id": key_id,
        "secret_key": secret_key,
        "expected_account_id": expected_account_id,
    }

def perform_genuine_paper_observation(
    *,
    paper_broker_read_authorized: bool,
    allow_network: bool,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Production entrypoint constructing concrete client after all gates pass."""
    inputs = get_production_preflight_inputs()

    # Run preflight gates
    validate_preflight_gates(
        app_profile=inputs["app_profile"],
        endpoint=inputs["endpoint"],
        key_id=inputs["key_id"],
        secret_key=inputs["secret_key"],
        expected_account_id=inputs["expected_account_id"],
        paper_broker_read_authorized=paper_broker_read_authorized,
        allow_network=allow_network,
    )

    # Initialize client locally after gates pass
    from algotrader.config import AlpacaPaperConfig
    from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient

    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key=inputs["key_id"],
        alpaca_secret_key=inputs["secret_key"],
        alpaca_paper_base_url=EXPECTED_PAPER_ENDPOINT,
    )
    client: PaperObservationReader = AlpacaSdkClient(config)

    observation_start_utc = datetime.now(UTC)

    call_counters = {
        "account_read_count": 0,
        "positions_read_count": 0,
        "orders_read_count": 0,
        "target_asset_read_count": 0
    }

    try:
        # 1. Account read
        raw_account = client.get_account()
        call_counters["account_read_count"] += 1

        # 2. Positions read
        raw_positions = client.get_positions()
        call_counters["positions_read_count"] += 1

        # 3. Bounded orders read
        from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
        recent_query = AlpacaRecentOrderQuery(
            status_filter="open",
            limit=100,
            direction="desc",
        )
        raw_orders = client.get_orders(recent_query)
        call_counters["orders_read_count"] += 1

        # 4. Target asset read
        raw_asset = client.get_asset(TARGET_SYMBOL)
        call_counters["target_asset_read_count"] += 1
    except Exception as exc:
        raise BrokerObservationError("broker_read_failed") from None

    observation_completion_utc = datetime.now(UTC)

    # Validate call counters exactly equal 1
    for key, count in call_counters.items():
        if count != 1:
            raise BrokerObservationError("invalid_call_counts")

    # Process and sanitize observations
    observation_receipt = _process_raw_observations(
        raw_account=raw_account,
        raw_positions=raw_positions,
        raw_orders=raw_orders,
        raw_asset=raw_asset,
        expected_account_id=inputs["expected_account_id"],
        is_fixture=False,
    )

    # Compute source-bundle digest
    bundle_digest, bundle_manifest = compute_source_bundle_digest(repo_root)

    # Build invocation receipt
    invocation_receipt = {
        "schema_version": PRODUCTION_INVOCATION_SCHEMA,
        "adapter_version": ADAPTER_VERSION,
        "adapter_source_bundle_sha256": bundle_digest,
        "source_bundle_manifest": bundle_manifest,
        "command_source_identity": "crypto-paper-broker-observation",
        "normalized_paper_endpoint": EXPECTED_PAPER_ENDPOINT,
        "expected_account_match": observation_receipt["expected_account_match"],
        "observation_start_utc": observation_start_utc.isoformat(),
        "observation_completion_utc": observation_completion_utc.isoformat(),
        "call_counters": call_counters,
        "read_completion_status": {
            "account_read_completed": True,
            "positions_read_completed": True,
            "open_orders_read_completed": True,
            "exact_target_asset_read_completed": True
        },
        "safety_booleans": {
            "network_authorization_present": paper_broker_read_authorized,
            "network_access_attempted": allow_network,
            "broker_read_completed": True,
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "live_authorized": False
        },
        "observation_receipt_sha256": observation_receipt["canonical_receipt_sha256"]
    }

    # Hashing invocation receipt
    inv_copy = dict(invocation_receipt)
    canonical_inv_str = json.dumps(inv_copy, sort_keys=True, separators=(",", ":"))
    invocation_receipt["canonical_invocation_sha256"] = hashlib.sha256(canonical_inv_str.encode("utf-8")).hexdigest()

    return observation_receipt, invocation_receipt


def perform_fixture_observation_evaluation(
    mock_client: PaperObservationReader,
    *,
    expected_account_id: str | None,
    paper_broker_read_authorized: bool,
    allow_network: bool,
) -> dict[str, Any]:
    """Fixture entrypoint accepts injected client, returning fixture receipt capped at R1."""
    if not expected_account_id or not expected_account_id.strip():
        raise PreflightCheckError("preflight_failed_expected_account_missing")

    try:
        raw_account = mock_client.get_account()
        raw_positions = mock_client.get_positions()
        raw_orders = mock_client.get_orders(None)
        raw_asset = mock_client.get_asset(TARGET_SYMBOL)
    except Exception:
        raise BrokerObservationError("broker_read_failed") from None

    return _process_raw_observations(
        raw_account=raw_account,
        raw_positions=raw_positions,
        raw_orders=raw_orders,
        raw_asset=raw_asset,
        expected_account_id=expected_account_id,
        is_fixture=True,
    )


def _process_raw_observations(
    *,
    raw_account: Any,
    raw_positions: Sequence[Any],
    raw_orders: Sequence[Any],
    raw_asset: Any,
    expected_account_id: str,
    is_fixture: bool,
) -> dict[str, Any]:
    # 1. Read and validate account safety fields
    status = _get_attr_or_key(raw_account, "status")
    trading_blocked = _get_attr_or_key(raw_account, "trading_blocked")
    account_blocked = _get_attr_or_key(raw_account, "account_blocked")

    if status is None or trading_blocked is None or account_blocked is None:
        raise BrokerObservationError("broker_account_safety_fields_missing")

    status_str = _to_string_value(status)
    if not status_str or status_str.upper() != "ACTIVE":
        raise BrokerObservationError("broker_account_inactive")
    if trading_blocked is not False:
        raise BrokerObservationError("broker_account_trading_blocked")
    if account_blocked is not False:
        raise BrokerObservationError("broker_account_blocked")

    # Additional suspension checks
    for suspended_key in ("suspended", "transact_blocked"):
        val = _get_attr_or_key(raw_account, suspended_key)
        if val is not None and val is not False:
            raise BrokerObservationError(f"broker_account_{suspended_key}_active")

    # Match expected account ID or number safely (without exposing raw values in errors)
    account_id = _get_attr_or_key(raw_account, "account_id") or _get_attr_or_key(raw_account, "id")
    account_number = _get_attr_or_key(raw_account, "account_number")
    account_matched = (account_id == expected_account_id) or (account_number == expected_account_id)
    if not account_matched:
        raise BrokerObservationError("broker_account_mismatch")

    # Sanitized account fingerprint
    fingerprint_input = f"{account_id or ''}:{account_number or ''}"
    account_fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()
    currency = _get_attr_or_key(raw_account, "currency") or "USD"

    # Normalize positions
    normalized_positions: list[dict[str, Any]] = []
    unexpected_exposure_classification = "clean"
    for pos in raw_positions:
        p_symbol = _get_attr_or_key(pos, "symbol")
        p_qty = _get_attr_or_key(pos, "qty")
        p_avg_price = _get_attr_or_key(pos, "average_entry_price") or _get_attr_or_key(pos, "avg_entry_price")
        p_market_value = _get_attr_or_key(pos, "market_value")

        if not p_symbol or p_qty is None:
            raise BrokerObservationError("malformed_position_data")

        normalized_sym = p_symbol.replace("/", "").upper()
        if normalized_sym != TARGET_SYMBOL:
            unexpected_exposure_classification = "unexpected_exposure_detected"

        normalized_positions.append({
            "symbol": normalized_sym,
            "quantity": str(Decimal(str(p_qty)).normalize()),
            "average_price": str(Decimal(str(p_avg_price or 0)).normalize()),
            "market_value": str(Decimal(str(p_market_value or 0)).normalize()),
        })

    # Normalize open orders
    normalized_orders: list[dict[str, Any]] = []
    seen_client_order_ids: set[str] = set()
    for order in raw_orders:
        o_id = _get_attr_or_key(order, "order_id") or _get_attr_or_key(order, "id")
        o_client_id = _get_attr_or_key(order, "client_order_id")
        o_symbol = _get_attr_or_key(order, "symbol")
        o_status = _get_attr_or_key(order, "status")
        o_qty = _get_attr_or_key(order, "qty")
        o_notional = _get_attr_or_key(order, "notional")
        o_side = _get_attr_or_key(order, "side")

        o_status_str = _to_string_value(o_status)
        o_side_str = _to_string_value(o_side)

        if not o_symbol or not o_status_str or not o_id or not o_client_id:
            raise BrokerObservationError("malformed_open_order_data")

        if o_client_id in seen_client_order_ids:
            raise BrokerObservationError("duplicate_client_order_id")
        seen_client_order_ids.add(o_client_id)

        normalized_sym = o_symbol.replace("/", "").upper()
        if normalized_sym != TARGET_SYMBOL:
            unexpected_exposure_classification = "unexpected_exposure_detected"

        if o_status_str.lower() not in (
            "open", "new", "accepted", "partially_filled", "pending_new", "accepted_for_bidding", "held"
        ):
            raise BrokerObservationError("unsupported_open_order_status")

        normalized_orders.append({
            "order_id": o_id,
            "client_order_id": o_client_id,
            "symbol": normalized_sym,
            "status": o_status_str.lower(),
            "quantity": str(Decimal(str(o_qty)).normalize()) if o_qty is not None else None,
            "notional": str(Decimal(str(o_notional)).normalize()) if o_notional is not None else None,
            "side": o_side_str.lower() if o_side_str else None,
        })

    # Validate target asset metadata
    if not raw_asset:
        raise BrokerObservationError("target_asset_missing")

    a_tradable = _get_attr_or_key(raw_asset, "tradable")
    a_orderable = _get_attr_or_key(raw_asset, "orderable")
    a_class = _get_attr_or_key(raw_asset, "asset_class") or _get_attr_or_key(raw_asset, "class")
    a_class_str = _to_string_value(a_class)

    if a_tradable is not True or a_orderable is not True:
        raise BrokerObservationError("target_asset_not_tradable_or_orderable")
    if a_class_str and a_class_str.lower() != SUPPORTED_ASSET_CLASS:
        raise BrokerObservationError("target_asset_class_invalid")

    # Check for truncation/completeness
    positions_truncated = len(normalized_positions) >= 100
    orders_truncated = len(normalized_orders) >= 100

    observed_at = datetime.now(UTC)

    schema = OFFLINE_FIXTURE_SCHEMA if is_fixture else PRODUCTION_OBSERVATION_SCHEMA
    source_classification = "fixture_replay" if is_fixture else "genuine_alpaca_paper_observation"
    authority = "fixture_replay_validated" if is_fixture else None

    receipt: dict[str, Any] = {
        "schema_version": schema,
        "adapter_version": ADAPTER_VERSION,
        "observation_id": str(uuid.uuid4()),
        "observed_at_utc": observed_at.isoformat(),
        "source_classification": source_classification,
        "paper_endpoint_classification": EXPECTED_PAPER_ENDPOINT,
        "expected_account_match": True,
        "sanitized_account_fingerprint": account_fingerprint,
        "target_symbol": TARGET_SYMBOL,
        "target_asset_class": SUPPORTED_ASSET_CLASS,
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {
            "status": status_str.lower(),
            "trading_blocked": False,
            "account_blocked": False,
            "currency": currency.upper(),
        },
        "positions": normalized_positions,
        "open_orders": normalized_orders,
        "truncation_indicators": {
            "positions_truncated": positions_truncated,
            "orders_truncated": orders_truncated,
        },
        "ambiguity_indicators": {
            "duplicate_positions": len(raw_positions) != len({_get_attr_or_key(p, "symbol") for p in raw_positions}),
            "duplicate_client_order_ids": False,
        },
        "unexpected_exposure_classification": unexpected_exposure_classification,
        "safety_booleans": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "live_authorized": False,
            "network_used": not is_fixture,
        },
    }

    if authority:
        receipt["authority"] = authority

    # Generate canonical hash
    canonical_str = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    receipt["canonical_receipt_sha256"] = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    return receipt


def _get_attr_or_key(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(key)
    try:
        return getattr(obj, key)
    except AttributeError:
        return None


def _to_string_value(val: Any) -> str | None:
    if val is None:
        return None
    if hasattr(val, "value"):
        return str(val.value)
    if hasattr(val, "name"):
        return str(val.name)
    return str(val)
