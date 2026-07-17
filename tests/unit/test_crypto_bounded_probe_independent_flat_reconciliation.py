from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
)
from algotrader.errors import ValidationError
from algotrader.execution.crypto_bounded_probe_independent_flat_reconciliation import (
    build_crypto_bounded_probe_independent_flat_reconciliation,
    validate_crypto_bounded_probe_independent_flat_reconciliation,
)


NOW = datetime(2026, 8, 20, tzinfo=timezone.utc)
MODULE = Path(
    "src/algotrader/execution/"
    "crypto_bounded_probe_independent_flat_reconciliation.py"
)


def _account(identifier: str = "paper-account-fixture") -> dict[str, object]:
    return {
        "account_id": identifier,
        "id": identifier,
        "account_number": "paper-number-fixture",
        "status": "ACTIVE",
        "blocked": False,
        "account_blocked": False,
        "trading_blocked": False,
    }


def _receipt(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "symbol": "BTCUSD",
        "observed_at": NOW,
        "account_observation": _account(),
        "expected_account_configured": True,
        "expected_account_matched": True,
        "positions": (),
        "open_orders": (),
        "broker_read_occurred": True,
        "account_read_occurred": True,
        "positions_read_occurred": True,
        "open_orders_read_occurred": True,
    }
    values.update(overrides)
    return build_crypto_bounded_probe_independent_flat_reconciliation(
        **values  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("symbol", ("BTCUSD", "ETHUSD", "SOLUSD"))
def test_flat_receipt_is_sanitized_account_bound_and_all_authority_false(
    symbol: str,
) -> None:
    receipt = _receipt(symbol=symbol)

    validate_crypto_bounded_probe_independent_flat_reconciliation(receipt)
    encoded = json.dumps(receipt)
    assert "paper-account-fixture" not in encoded
    assert "paper-number-fixture" not in encoded
    assert receipt["subject"]["symbol"] == symbol
    assert receipt["final_position_count"] == 0
    assert receipt["final_open_order_count"] == 0
    assert receipt["account_binding"] == build_alpaca_paper_account_binding(
        _account(),
        expected_account_configured=True,
        expected_account_matched=True,
    )
    assert receipt["authority"]["broker_mutation_authorized"] is False
    assert receipt["authority"]["live_authorized"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("expected_account_matched", False),
        ("positions", ({"symbol": "BTCUSD", "qty": "1"},)),
        ("open_orders", ({"symbol": "ETHUSD"},)),
        ("broker_read_occurred", False),
        ("broker_ambiguity", True),
        ("mutation_occurred", True),
        ("live_endpoint_touched", True),
    ),
)
def test_flat_receipt_fails_closed_on_untrusted_or_nonflat_input(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _receipt(**{field: value})


def test_account_alias_disagreement_fails_closed() -> None:
    account = _account()
    account["id"] = "different-account"

    with pytest.raises(ValidationError, match="aliases disagree"):
        _receipt(account_observation=account)


@pytest.mark.parametrize(
    "field",
    ("blocked", "account_blocked", "trading_blocked"),
)
def test_missing_account_block_flag_fails_closed(field: str) -> None:
    account = _account()
    del account[field]

    with pytest.raises(ValidationError, match="block flags are incomplete"):
        _receipt(account_observation=account)


@pytest.mark.parametrize("field", ("account_id", "id", "account_number"))
def test_non_string_account_identity_fails_closed(field: str) -> None:
    account = _account()
    account[field] = ["not", "an", "identity"]

    with pytest.raises(ValidationError, match="must be a string"):
        _receipt(account_observation=account)


def test_boolean_counts_cannot_pass_integer_validation() -> None:
    receipt = _receipt()
    receipt["final_position_count"] = False
    unsigned = dict(receipt)
    unsigned.pop("observation_fingerprint")
    receipt["observation_fingerprint"] = _stable_hash(unsigned)

    with pytest.raises(ValidationError, match="invalid"):
        validate_crypto_bounded_probe_independent_flat_reconciliation(receipt)


def test_flat_builder_has_no_broker_network_or_mutation_imports() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"), filename=str(MODULE))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert not any(
        name.startswith(("alpaca", "httpx", "requests", "socket", "urllib"))
        for name in imports
    )
    assert calls.isdisjoint(
        {
            "cancel_order",
            "close_position",
            "get_account",
            "get_orders",
            "replace_order",
            "submit_order",
            "urlopen",
        }
    )


def _stable_hash(value: object) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
