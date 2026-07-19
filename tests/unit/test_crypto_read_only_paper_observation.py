"""Unit tests for V5.33 crypto read-only paper broker observation."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    BrokerObservationError,
    PreflightCheckError,
    perform_crypto_observation,
    validate_preflight_gates,
)
from algotrader.execution.crypto_supervised_readiness_trial import (
    _validate_offline_receipt,
    run_crypto_supervised_readiness_trial,
)


class MockAsset:
    def __init__(self, symbol: str, tradable: bool, orderable: bool, asset_class: str):
        self.symbol = symbol
        self.tradable = tradable
        self.orderable = orderable
        self.asset_class = asset_class


class MockPosition:
    def __init__(self, symbol: str, qty: float | str, average_entry_price: float | str, market_value: float | str):
        self.symbol = symbol
        self.qty = qty
        self.average_entry_price = average_entry_price
        self.market_value = market_value


class MockOrder:
    def __init__(self, order_id: str, client_order_id: str, symbol: str, status: str, qty: float | str, side: str):
        self.id = order_id
        self.client_order_id = client_order_id
        self.symbol = symbol
        self.status = status
        self.qty = qty
        self.side = side
        self.notional = None


class MockPrice:
    def __init__(self, price: float, timestamp: datetime):
        self.price = price
        self.timestamp = timestamp
        self.ask_price = price


class MockAlpacaClient:
    def __init__(self):
        self.account_id = "fake_acc_123"
        self.account_number = "PA12345"
        self.status = "ACTIVE"
        self.cash = 100000.0
        self.buying_power = 200000.0
        self.currency = "USD"
        
        self.positions = [
            MockPosition("BTCUSD", "0.5", "60000.0", "30000.0")
        ]
        self.orders = []
        self.assets = [
            MockAsset("BTCUSD", True, True, "crypto")
        ]
        self.latest_price = 60000.0
        self.price_timestamp = datetime.now(UTC)

    def get_account(self) -> Any:
        return {
            "id": self.account_id,
            "account_number": self.account_number,
            "status": self.status,
            "cash": self.cash,
            "buying_power": self.buying_power,
            "currency": self.currency,
        }

    def get_positions(self) -> list[Any]:
        return self.positions

    def get_orders(self, query: Any) -> list[Any]:
        return self.orders

    def list_assets(self) -> list[Any]:
        return self.assets

    def get_crypto_latest_quote(self, symbol: str) -> Any:
        return MockPrice(self.latest_price, self.price_timestamp)

    def get_crypto_latest_trade(self, symbol: str) -> Any:
        return MockPrice(self.latest_price, self.price_timestamp)

    def get_crypto_latest_bar(self, symbol: str) -> Any:
        return MockPrice(self.latest_price, self.price_timestamp)


def test_preflight_gates_success() -> None:
    # Golden path
    validate_preflight_gates(
        app_profile="paper",
        endpoint="https://paper-api.alpaca.markets",
        credentials_present=True,
        expected_account_id="PA12345",
        paper_broker_read_authorized=True,
        allow_network=True,
        target_symbol="BTCUSD",
        allow_mutation=False,
        live_endpoint_indicator=False,
    )


def test_preflight_gates_failures() -> None:
    # Wrong profile
    with pytest.raises(PreflightCheckError, match="APP_PROFILE must be exactly 'paper'"):
        validate_preflight_gates(
            app_profile="live",
            endpoint="https://paper-api.alpaca.markets",
            credentials_present=True,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
            target_symbol="BTCUSD",
        )

    # Wrong endpoint
    with pytest.raises(PreflightCheckError, match="does not match expected"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://api.alpaca.markets",
            credentials_present=True,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
            target_symbol="BTCUSD",
        )

    # Credentials missing
    with pytest.raises(PreflightCheckError, match="credentials must be present"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            credentials_present=False,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
            target_symbol="BTCUSD",
        )

    # Expected account missing
    with pytest.raises(PreflightCheckError, match="expected paper-account ID.*is not configured"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            credentials_present=True,
            expected_account_id=None,
            paper_broker_read_authorized=True,
            allow_network=True,
            target_symbol="BTCUSD",
        )

    # Not authorized
    with pytest.raises(PreflightCheckError, match="PaperBrokerReadAuthorized switch/flag is not set"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            credentials_present=True,
            expected_account_id="PA12345",
            paper_broker_read_authorized=False,
            allow_network=True,
            target_symbol="BTCUSD",
        )

    # Network blocked
    with pytest.raises(PreflightCheckError, match="AllowNetwork switch/flag is not set"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            credentials_present=True,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=False,
            target_symbol="BTCUSD",
        )

    # Wrong target symbol
    with pytest.raises(PreflightCheckError, match="target symbol.*is not authorized"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            credentials_present=True,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
            target_symbol="ETHUSD",
        )

    # Live indicator URL
    with pytest.raises(PreflightCheckError, match="Live endpoint or live profile detected"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            credentials_present=True,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
            target_symbol="BTCUSD",
            live_endpoint_indicator=True,
        )

    # Mutation allowed
    with pytest.raises(PreflightCheckError, match="Mutation authorization is forbidden"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            credentials_present=True,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
            target_symbol="BTCUSD",
            allow_mutation=True,
        )


def test_perform_observation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set environment variables for preflight
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA12345")
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    client = MockAlpacaClient()
    receipt = perform_crypto_observation(
        client,
        paper_broker_read_authorized=True,
        allow_network=True,
    )

    assert receipt["schema_version"] == "v5_33_broker_observation_receipt_v1"
    assert receipt["expected_account_match"] is True
    assert receipt["target_symbol"] == "BTCUSD"
    assert receipt["unexpected_exposure_classification"] == "clean"
    assert len(receipt["positions"]) == 1
    assert receipt["positions"][0]["symbol"] == "BTCUSD"
    assert receipt["canonical_receipt_sha256"] is not None


def test_perform_observation_account_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA99999")  # different
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    client = MockAlpacaClient()
    with pytest.raises(BrokerObservationError, match="does not match expected paper-account ID"):
        perform_crypto_observation(
            client,
            paper_broker_read_authorized=True,
            allow_network=True,
        )


def test_perform_observation_unexpected_exposure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA12345")
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")

    client = MockAlpacaClient()
    # Add non-BTCUSD position
    client.positions.append(MockPosition("ETHUSD", "1.0", "2000.0", "2000.0"))

    receipt = perform_crypto_observation(
        client,
        paper_broker_read_authorized=True,
        allow_network=True,
    )
    assert receipt["unexpected_exposure_classification"] == "unexpected_exposure_detected"


def test_perform_observation_duplicate_order_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA12345")
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")

    client = MockAlpacaClient()
    client.orders = [
        MockOrder("ord_1", "client_1", "BTCUSD", "new", 0.1, "buy"),
        MockOrder("ord_2", "client_1", "BTCUSD", "new", 0.1, "buy"),  # duplicate client ID
    ]

    with pytest.raises(BrokerObservationError, match="Duplicate client order ID detected"):
        perform_crypto_observation(
            client,
            paper_broker_read_authorized=True,
            allow_network=True,
        )


def test_perform_observation_unsupported_order_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA12345")
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")

    client = MockAlpacaClient()
    client.orders = [
        MockOrder("ord_1", "client_1", "BTCUSD", "calculated", 0.1, "buy"),  # unsupported status
    ]

    with pytest.raises(BrokerObservationError, match="Unsupported open order status"):
        perform_crypto_observation(
            client,
            paper_broker_read_authorized=True,
            allow_network=True,
        )


def test_perform_observation_stale_price(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA12345")
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")

    client = MockAlpacaClient()
    client.price_timestamp = datetime.now(UTC) - timedelta(minutes=20)  # stale

    with pytest.raises(BrokerObservationError, match="Price observation is stale"):
        perform_crypto_observation(
            client,
            paper_broker_read_authorized=True,
            allow_network=True,
        )


def test_validate_offline_receipt_tampered(tmp_path: Path) -> None:
    # Build a valid receipt
    receipt = {
        "schema_version": "v5_33_broker_observation_receipt_v1",
        "adapter_version": "1.0",
        "observation_id": "test_id",
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "source_classification": "genuine_alpaca_paper_observation",
        "paper_endpoint_classification": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "sanitized_account_fingerprint": "abc",
        "target_symbol": "BTCUSD",
        "target_asset_class": "crypto",
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {"status": "active"},
        "positions": [],
        "open_orders": [],
        "truncation_indicators": {"positions_truncated": False, "orders_truncated": False},
        "freshness": {"price_timestamp": datetime.now(UTC).isoformat()},
        "ambiguity_indicators": {"duplicate_positions": False, "duplicate_client_order_ids": False},
        "unexpected_exposure_classification": "clean",
        "safety_booleans": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "live_authorized": False,
        },
        "source_artifact_sha256": "0" * 64,
    }

    # Hash it correctly
    r_copy = dict(receipt)
    import hashlib
    canonical_str = json.dumps(r_copy, sort_keys=True, separators=(",", ":"))
    canonical_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
    receipt["canonical_receipt_sha256"] = canonical_hash

    # Save to file
    receipt_file = tmp_path / "receipt.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    # Valid check
    res = _validate_offline_receipt(receipt_file)
    assert res["valid"] is True

    # Tamper with the receipt content
    receipt["target_symbol"] = "ETHUSD"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    # Validation should fail
    res2 = _validate_offline_receipt(receipt_file)
    assert res2["valid"] is False
    assert res2["classification"] == "blocked_receipt_tampered"


def test_readiness_trial_with_receipt(tmp_path: Path) -> None:
    # Build a valid receipt
    receipt = {
        "schema_version": "v5_33_broker_observation_receipt_v1",
        "adapter_version": "1.0",
        "observation_id": "test_id",
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "source_classification": "genuine_alpaca_paper_observation",
        "paper_endpoint_classification": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "sanitized_account_fingerprint": "abc",
        "target_symbol": "BTCUSD",
        "target_asset_class": "crypto",
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {"status": "active"},
        "positions": [],
        "open_orders": [],
        "truncation_indicators": {"positions_truncated": False, "orders_truncated": False},
        "freshness": {"price_timestamp": datetime.now(UTC).isoformat()},
        "ambiguity_indicators": {"duplicate_positions": False, "duplicate_client_order_ids": False},
        "unexpected_exposure_classification": "clean",
        "safety_booleans": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "live_authorized": False,
        },
        "source_artifact_sha256": "0" * 64,
    }

    # Hash it correctly
    r_copy = dict(receipt)
    import hashlib
    canonical_str = json.dumps(r_copy, sort_keys=True, separators=(",", ":"))
    canonical_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
    receipt["canonical_receipt_sha256"] = canonical_hash

    # Save to file
    receipt_file = tmp_path / "receipt.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    trial_res = run_crypto_supervised_readiness_trial(
        output_root=tmp_path / "trial_out",
        cycle_count=8,
        receipt_path=receipt_file,
    )

    assert trial_res["current_readiness_rung"] == "R2_broker_observed_no_submit"
    assert trial_res["current_readiness_rung_code"] == "R2"
