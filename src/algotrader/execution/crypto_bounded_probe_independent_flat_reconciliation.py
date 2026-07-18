"""Pure crypto flat-account evidence construction for a bounded probe.

Broker reads, profile checks, credential handling, and authorization remain at
the command boundary. This module only validates already-collected observations
and emits a sanitized, fingerprinted receipt. It has no network or mutation
path.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json

from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
    validate_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError


CRYPTO_BOUNDED_PROBE_INDEPENDENT_FLAT_SCHEMA_VERSION = (
    "v5_27_crypto_bounded_probe_independent_flat_observation_v1"
)
CRYPTO_BOUNDED_PROBE_FLAT_SUPPORTED_SYMBOLS = (
    "BTCUSD",
    "ETHUSD",
    "SOLUSD",
)
_AUTHORITY = {
    "paper_submit_authorized": False,
    "broker_mutation_authorized": False,
    "capital_allocation_authorized": False,
    "live_authorized": False,
}
_EXPECTED_KEYS = {
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

__all__ = [
    "CRYPTO_BOUNDED_PROBE_FLAT_SUPPORTED_SYMBOLS",
    "CRYPTO_BOUNDED_PROBE_INDEPENDENT_FLAT_SCHEMA_VERSION",
    "build_crypto_bounded_probe_independent_flat_reconciliation",
    "validate_crypto_bounded_probe_independent_flat_reconciliation",
]


def build_crypto_bounded_probe_independent_flat_reconciliation(
    *,
    symbol: str,
    observed_at: datetime | str,
    account_observation: Mapping[str, object],
    expected_account_configured: bool,
    expected_account_matched: bool,
    positions: Sequence[Mapping[str, object]],
    open_orders: Sequence[Mapping[str, object]],
    broker_read_occurred: bool,
    account_read_occurred: bool,
    positions_read_occurred: bool,
    open_orders_read_occurred: bool,
    broker_ambiguity: bool = False,
    mutation_occurred: bool = False,
    live_endpoint_touched: bool = False,
) -> dict[str, object]:
    """Build one exact all-account-flat, read-only crypto receipt."""

    normalized_symbol = str(symbol).strip().upper()
    if normalized_symbol not in CRYPTO_BOUNDED_PROBE_FLAT_SUPPORTED_SYMBOLS:
        raise ValidationError("flat reconciliation symbol is unsupported.")
    timestamp = _utc_datetime(observed_at, "observed_at")
    for name, value, expected in (
        ("broker_read_occurred", broker_read_occurred, True),
        ("account_read_occurred", account_read_occurred, True),
        ("positions_read_occurred", positions_read_occurred, True),
        ("open_orders_read_occurred", open_orders_read_occurred, True),
        ("broker_ambiguity", broker_ambiguity, False),
        ("mutation_occurred", mutation_occurred, False),
        ("live_endpoint_touched", live_endpoint_touched, False),
    ):
        if type(value) is not bool or value is not expected:
            raise ValidationError(f"{name} must be {str(expected).lower()}.")
    if not isinstance(account_observation, Mapping):
        raise ValidationError("account_observation must be a mapping.")
    if _normalized_status(account_observation.get("status")) not in {
        "ACTIVE",
        "ACCOUNT_ACTIVE",
    }:
        raise ValidationError("paper account is not active.")
    for blocker in ("account_blocked", "trading_blocked"):
        if blocker not in account_observation:
            raise ValidationError("paper account block flags are incomplete.")
        value = account_observation.get(blocker)
        if type(value) is not bool or value is not False:
            raise ValidationError("paper account is blocked or ambiguous.")
    if "blocked" in account_observation:
        value = account_observation.get("blocked")
        if type(value) is not bool or value is not False:
            raise ValidationError("paper account is blocked or ambiguous.")
    position_rows = _mapping_rows(positions, "positions")
    order_rows = _mapping_rows(open_orders, "open_orders")
    if position_rows or order_rows:
        raise ValidationError("paper account is not flat for bounded-probe entry.")
    account_binding = build_alpaca_paper_account_binding(
        account_observation,
        expected_account_configured=expected_account_configured,
        expected_account_matched=expected_account_matched,
    )
    source_snapshot = {
        "as_of": timestamp.isoformat(),
        "symbol": normalized_symbol,
        "account_binding": account_binding,
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
    receipt: dict[str, object] = {
        "schema_version": (
            CRYPTO_BOUNDED_PROBE_INDEPENDENT_FLAT_SCHEMA_VERSION
        ),
        "record_type": "crypto_bounded_probe_independent_flat_observation",
        "as_of": timestamp.isoformat(),
        "subject": {
            "asset_class": "crypto",
            "symbol": normalized_symbol,
            "environment": "alpaca_paper",
        },
        "account_binding": account_binding,
        "read_only_reconciliation": True,
        "broker_read_occurred": True,
        "account_read_occurred": True,
        "positions_read_occurred": True,
        "open_orders_read_occurred": True,
        "final_position_count": 0,
        "final_open_order_count": 0,
        "observed_position_symbols": [],
        "observed_open_order_symbols": [],
        "broker_ambiguity": False,
        "mutation_occurred": False,
        "live_endpoint_touched": False,
        "authority": dict(_AUTHORITY),
        "profit_claim": "none",
        "source_snapshot_fingerprint": _stable_hash(source_snapshot),
    }
    receipt["observation_fingerprint"] = _stable_hash(receipt)
    validate_crypto_bounded_probe_independent_flat_reconciliation(receipt)
    return receipt


def validate_crypto_bounded_probe_independent_flat_reconciliation(
    receipt: Mapping[str, object],
) -> None:
    """Validate the exact sanitized receipt and both fingerprints."""

    unsigned = dict(receipt)
    fingerprint = str(unsigned.pop("observation_fingerprint", ""))
    account_binding = receipt.get("account_binding")
    if not isinstance(account_binding, Mapping):
        raise ValidationError("flat account binding is absent.")
    validate_alpaca_paper_account_binding(account_binding)
    subject = receipt.get("subject")
    if (
        set(receipt) != _EXPECTED_KEYS
        or receipt.get("schema_version")
        != CRYPTO_BOUNDED_PROBE_INDEPENDENT_FLAT_SCHEMA_VERSION
        or receipt.get("record_type")
        != "crypto_bounded_probe_independent_flat_observation"
        or not isinstance(subject, Mapping)
        or subject.get("asset_class") != "crypto"
        or subject.get("symbol")
        not in CRYPTO_BOUNDED_PROBE_FLAT_SUPPORTED_SYMBOLS
        or subject.get("environment") != "alpaca_paper"
        or set(subject) != {"asset_class", "symbol", "environment"}
        or receipt.get("read_only_reconciliation") is not True
        or receipt.get("broker_read_occurred") is not True
        or receipt.get("account_read_occurred") is not True
        or receipt.get("positions_read_occurred") is not True
        or receipt.get("open_orders_read_occurred") is not True
        or type(receipt.get("final_position_count")) is not int
        or receipt.get("final_position_count") != 0
        or type(receipt.get("final_open_order_count")) is not int
        or receipt.get("final_open_order_count") != 0
        or receipt.get("observed_position_symbols") != []
        or receipt.get("observed_open_order_symbols") != []
        or receipt.get("broker_ambiguity") is not False
        or receipt.get("mutation_occurred") is not False
        or receipt.get("live_endpoint_touched") is not False
        or receipt.get("authority") != _AUTHORITY
        or receipt.get("profit_claim") != "none"
        or fingerprint != _stable_hash(unsigned)
    ):
        raise ValidationError("independent flat reconciliation is invalid.")
    _utc_datetime(receipt.get("as_of"), "receipt.as_of")
    source_fingerprint = str(receipt.get("source_snapshot_fingerprint", ""))
    if len(source_fingerprint) != 64 or any(
        character not in "0123456789abcdef"
        for character in source_fingerprint
    ):
        raise ValidationError("flat source snapshot fingerprint is invalid.")


def _mapping_rows(
    rows: Sequence[Mapping[str, object]],
    field_name: str,
) -> list[dict[str, object]]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise ValidationError(f"{field_name} must be a sequence.")
    result: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValidationError(f"{field_name} rows must be mappings.")
        result.append(dict(row))
    return result


def _normalized_status(value: object) -> str:
    status = str(value or "").strip().upper()
    if "." in status:
        status = status.rsplit(".", 1)[-1]
    return status


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


def _stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
