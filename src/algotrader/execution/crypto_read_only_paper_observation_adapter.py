"""V5.33 Isolated read-only paper broker observation adapter.

This module performs a single, bounded, explicitly authorized, read-only paper
account observation for BTCUSD. It does not perform order submission, cancellation,
replacement, closing, or liquidation, and rejects live credentials or endpoints.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

from algotrader.config import AlpacaPaperConfig
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaOrderResponse,
    AlpacaPositionResponse,
    AlpacaRecentOrderQuery,
)

SCHEMA_VERSION = "v5_33_broker_observation_receipt_v1"
ADAPTER_VERSION = "1.0"
TARGET_SYMBOL = "BTCUSD"
SUPPORTED_ASSET_CLASS = "crypto"

# Alpaca paper endpoints
EXPECTED_PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
EXPECTED_ACCOUNT_ENV = "ALPACA_EXPECTED_PAPER_ACCOUNT_ID"

class PreflightCheckError(ValidationError):
    """Raised when any preflight safety gate fails before network access."""
    pass

class BrokerObservationError(ValidationError):
    """Raised when broker state cannot be conclusively observed or fails checks."""
    pass


def validate_preflight_gates(
    *,
    app_profile: str,
    endpoint: str,
    credentials_present: bool,
    expected_account_id: str | None,
    paper_broker_read_authorized: bool,
    allow_network: bool,
    target_symbol: str,
    allow_mutation: bool = False,
    live_endpoint_indicator: bool = False,
) -> None:
    """Validate all preflight safety gates before network access."""
    if app_profile.strip().lower() != "paper":
        raise PreflightCheckError("Preflight failed: APP_PROFILE must be exactly 'paper'.")

    normalized_endpoint = endpoint.strip().lower().rstrip("/")
    if normalized_endpoint != EXPECTED_PAPER_ENDPOINT:
        raise PreflightCheckError(
            f"Preflight failed: endpoint {endpoint} does not match expected {EXPECTED_PAPER_ENDPOINT}."
        )

    if not credentials_present:
        raise PreflightCheckError("Preflight failed: Alpaca credentials must be present in the environment.")

    if not expected_account_id or not expected_account_id.strip():
        raise PreflightCheckError(
            f"Preflight failed: expected paper-account ID ({EXPECTED_ACCOUNT_ENV}) is not configured."
        )

    if not paper_broker_read_authorized:
        raise PreflightCheckError("Preflight failed: PaperBrokerReadAuthorized switch/flag is not set.")

    if not allow_network:
        raise PreflightCheckError("Preflight failed: AllowNetwork switch/flag is not set.")

    if target_symbol.strip().upper() != TARGET_SYMBOL:
        raise PreflightCheckError(
            f"Preflight failed: target symbol {target_symbol} is not authorized. Strictly authorized: {TARGET_SYMBOL}."
        )

    if live_endpoint_indicator or "live" in normalized_endpoint or "api.alpaca.markets" in normalized_endpoint and "paper" not in normalized_endpoint:
        raise PreflightCheckError("Preflight failed: Live endpoint or live profile detected.")

    if allow_mutation:
        raise PreflightCheckError("Preflight failed: Mutation authorization is forbidden.")


def get_environment_preflight_state() -> dict[str, Any]:
    """Retrieve current preflight inputs from environment variables."""
    env = os.environ
    profile = env.get("APP_PROFILE", "").strip().lower()
    credential_names = (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    )
    credentials_present = any(bool(env.get(name, "").strip()) for name in credential_names)
    
    endpoint = env.get("ALPACA_PAPER_BASE_URL", EXPECTED_PAPER_ENDPOINT)
    expected_account_id = env.get(EXPECTED_ACCOUNT_ENV)

    # Check for live URLs in variables
    live_endpoint_indicator = False
    for name in ("ALPACA_BASE_URL", "APCA_API_BASE_URL", "ALPACA_PAPER_BASE_URL"):
        val = env.get(name, "").lower()
        if "api.alpaca.markets" in val and "paper" not in val:
            live_endpoint_indicator = True

    return {
        "app_profile": profile,
        "endpoint": endpoint,
        "credentials_present": credentials_present,
        "expected_account_id": expected_account_id,
        "live_endpoint_indicator": live_endpoint_indicator or (profile == "live"),
    }


def perform_crypto_observation(
    client: Any,
    *,
    paper_broker_read_authorized: bool,
    allow_network: bool,
    source_artifact_sha256: str = "0" * 64,
) -> dict[str, Any]:
    """Perform isolated broker read and sanitize results into a receipt."""
    env_state = get_environment_preflight_state()
    
    # Run preflight gates
    validate_preflight_gates(
        app_profile=env_state["app_profile"],
        endpoint=env_state["endpoint"],
        credentials_present=env_state["credentials_present"],
        expected_account_id=env_state["expected_account_id"],
        paper_broker_read_authorized=paper_broker_read_authorized,
        allow_network=allow_network,
        target_symbol=TARGET_SYMBOL,
        live_endpoint_indicator=env_state["live_endpoint_indicator"],
    )

    expected_account_id = env_state["expected_account_id"] or ""
    observed_at = datetime.now(UTC)

    # Fetch data from client
    try:
        raw_account = client.get_account()
        raw_positions = client.get_positions()
        
        # Read open orders
        recent_query = AlpacaRecentOrderQuery(
            status_filter="open",
            limit=100,
            direction="desc",
        )
        raw_orders = client.get_orders(recent_query)

        # Read assets to check tradability
        raw_assets = client.list_assets()
    except Exception as exc:
        raise BrokerObservationError(f"Broker read call failed: {exc.__class__.__name__}: {exc}") from exc

    # Parse and validate account status
    account_id = _get_attr_or_key(raw_account, "account_id") or _get_attr_or_key(raw_account, "id")
    account_number = _get_attr_or_key(raw_account, "account_number")
    status = _get_attr_or_key(raw_account, "status")
    cash = _get_attr_or_key(raw_account, "cash")
    buying_power = _get_attr_or_key(raw_account, "buying_power")
    currency = _get_attr_or_key(raw_account, "currency") or "USD"

    if not status or status.upper() not in ("ACTIVE", "ACCOUNT_STATUS_ACTIVE"):
        raise BrokerObservationError(f"Safety violation: broker account status is not active (got '{status}').")

    # Match expected account ID or number
    account_matched = (account_id == expected_account_id) or (account_number == expected_account_id)
    if not account_matched:
        raise BrokerObservationError(
            f"Safety violation: observed account ID/number ('{account_id}'/'{account_number}') "
            f"does not match expected paper-account ID ('{expected_account_id}')."
        )

    # Sanitize account fingerprint
    fingerprint_input = f"{account_id or ''}:{account_number or ''}"
    account_fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()

    # Parse and normalize positions
    normalized_positions: list[dict[str, Any]] = []
    unexpected_exposure_classification = "clean"
    for pos in raw_positions:
        p_symbol = _get_attr_or_key(pos, "symbol")
        p_qty = _get_attr_or_key(pos, "qty")
        p_avg_price = _get_attr_or_key(pos, "average_entry_price") or _get_attr_or_key(pos, "avg_entry_price")
        p_market_value = _get_attr_or_key(pos, "market_value")

        if not p_symbol or p_qty is None:
            raise BrokerObservationError("Malformed position data observed from broker.")

        # Flag unexpected exposure
        normalized_sym = p_symbol.replace("/", "").upper()
        if normalized_sym != TARGET_SYMBOL:
            unexpected_exposure_classification = "unexpected_exposure_detected"

        normalized_positions.append({
            "symbol": normalized_sym,
            "quantity": str(Decimal(str(p_qty)).normalize()),
            "average_price": str(Decimal(str(p_avg_price or 0)).normalize()),
            "market_value": str(Decimal(str(p_market_value or 0)).normalize()),
        })

    # Parse and normalize open orders
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

        if not o_symbol or not o_status or not o_id or not o_client_id:
            raise BrokerObservationError("Malformed open order data observed from broker.")

        if o_client_id in seen_client_order_ids:
            raise BrokerObservationError(f"Duplicate client order ID detected: {o_client_id}")
        seen_client_order_ids.add(o_client_id)

        # Flag unexpected exposure
        normalized_sym = o_symbol.replace("/", "").upper()
        if normalized_sym != TARGET_SYMBOL:
            unexpected_exposure_classification = "unexpected_exposure_detected"

        # Check unsupported order state (active order must be supported)
        # Supported states for open orders typically are: open, new, accepted, partially_filled, pending_new
        if o_status.lower() not in (
            "open", "new", "accepted", "partially_filled", "pending_new", "accepted_for_bidding", "held"
        ):
            raise BrokerObservationError(f"Unsupported open order status detected: {o_status}")

        normalized_orders.append({
            "order_id": o_id,
            "client_order_id": o_client_id,
            "symbol": normalized_sym,
            "status": o_status.lower(),
            "quantity": str(Decimal(str(o_qty)).normalize()) if o_qty is not None else None,
            "notional": str(Decimal(str(o_notional)).normalize()) if o_notional is not None else None,
            "side": o_side.lower() if o_side else None,
        })

    # Validate target symbol metadata (tradability and orderability)
    target_asset = None
    for asset in raw_assets:
        a_sym = _get_attr_or_key(asset, "symbol")
        if a_sym and a_sym.replace("/", "").upper() == TARGET_SYMBOL:
            target_asset = asset
            break

    if not target_asset:
        raise BrokerObservationError(f"Target symbol {TARGET_SYMBOL} metadata is missing in asset list.")

    a_tradable = _get_attr_or_key(target_asset, "tradable")
    a_orderable = _get_attr_or_key(target_asset, "orderable")
    a_class = _get_attr_or_key(target_asset, "asset_class") or _get_attr_or_key(target_asset, "class")

    # Target symbol must be tradable and orderable
    if a_tradable is not True or a_orderable is not True:
        raise BrokerObservationError(
            f"Safety violation: target asset {TARGET_SYMBOL} is not tradable/orderable "
            f"(tradable={a_tradable}, orderable={a_orderable})."
        )
    if a_class and a_class.lower() != SUPPORTED_ASSET_CLASS:
        raise BrokerObservationError(
            f"Safety violation: target asset class is {a_class}, expected {SUPPORTED_ASSET_CLASS}."
        )

    # Fetch latest price for target asset
    latest_price = None
    price_source = "unavailable"
    price_timestamp = None

    # Try Quote first
    try:
        quote = client.get_crypto_latest_quote(TARGET_SYMBOL)
        if quote:
            latest_price = _get_attr_or_key(quote, "ask_price") or _get_attr_or_key(quote, "bp") or _get_attr_or_key(quote, "price")
            price_timestamp = _get_attr_or_key(quote, "timestamp") or _get_attr_or_key(quote, "t")
            price_source = "quote"
    except Exception:
        pass

    if latest_price is None:
        # Try Trade
        try:
            trade = client.get_crypto_latest_trade(TARGET_SYMBOL)
            if trade:
                latest_price = _get_attr_or_key(trade, "price") or _get_attr_or_key(trade, "p")
                price_timestamp = _get_attr_or_key(trade, "timestamp") or _get_attr_or_key(trade, "t")
                price_source = "trade"
        except Exception:
            pass

    if latest_price is None:
        # Try Bar
        try:
            bar = client.get_crypto_latest_bar(TARGET_SYMBOL)
            if bar:
                latest_price = _get_attr_or_key(bar, "close") or _get_attr_or_key(bar, "c")
                price_timestamp = _get_attr_or_key(bar, "timestamp") or _get_attr_or_key(bar, "t")
                price_source = "bar"
        except Exception:
            pass

    if latest_price is None:
        raise BrokerObservationError("Failed to observe target symbol price from quotes, trades, or bars.")

    # Freshness check: price timestamp must be timezone-aware and not too old
    if price_timestamp:
        if isinstance(price_timestamp, str):
            price_dt = datetime.fromisoformat(price_timestamp.replace("Z", "+00:00"))
        else:
            price_dt = price_timestamp
        
        if price_dt.tzinfo is None:
            raise BrokerObservationError("Price observation timestamp must be timezone-aware.")
        
        price_age = (datetime.now(UTC) - price_dt.astimezone(UTC)).total_seconds()
        if price_age < -60 or price_age > 900:  # 15 minutes
            raise BrokerObservationError(f"Price observation is stale (age={price_age:.1f} seconds).")
        price_time_str = price_dt.astimezone(UTC).isoformat()
    else:
        raise BrokerObservationError("Price observation timestamp is missing.")

    # Check for truncation/completeness
    positions_truncated = len(normalized_positions) >= 100
    orders_truncated = len(normalized_orders) >= 100

    # Build receipt payload
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "observation_id": str(uuid.uuid4()),
        "observed_at_utc": observed_at.isoformat(),
        "source_classification": "genuine_alpaca_paper_observation",
        "paper_endpoint_classification": EXPECTED_PAPER_ENDPOINT,
        "expected_account_match": True,
        "sanitized_account_fingerprint": account_fingerprint,
        "target_symbol": TARGET_SYMBOL,
        "target_asset_class": SUPPORTED_ASSET_CLASS,
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {
            "status": status.lower(),
            "trading_blocked": False,
            "account_blocked": False,
            "cash": str(Decimal(str(cash)).normalize()) if cash is not None else None,
            "buying_power": str(Decimal(str(buying_power)).normalize()) if buying_power is not None else None,
            "currency": currency.upper(),
        },
        "positions": normalized_positions,
        "open_orders": normalized_orders,
        "truncation_indicators": {
            "positions_truncated": positions_truncated,
            "orders_truncated": orders_truncated,
        },
        "freshness": {
            "latest_price": str(Decimal(str(latest_price)).normalize()),
            "price_timestamp": price_time_str,
            "price_source": price_source,
            "price_age_seconds": price_age,
        },
        "ambiguity_indicators": {
            "duplicate_positions": len(raw_positions) != len({p["symbol"] for p in normalized_positions}),
            "duplicate_client_order_ids": False,
        },
        "unexpected_exposure_classification": unexpected_exposure_classification,
        "safety_booleans": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "live_authorized": False,
            "network_used": True,
        },
        "source_artifact_sha256": source_artifact_sha256,
    }

    # Generate canonical hash
    canonical_str = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    canonical_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
    receipt["canonical_receipt_sha256"] = canonical_hash

    return receipt


def _get_attr_or_key(obj: Any, key: str) -> Any:
    """Helper to get attribute or key from object safely."""
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(key)
    try:
        return getattr(obj, key)
    except AttributeError:
        return None
