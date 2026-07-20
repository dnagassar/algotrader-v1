"""Unit tests for V5.33 crypto read-only paper broker observation and repairs."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    BrokerObservationError,
    PreflightCheckError,
    perform_fixture_observation_evaluation,
    perform_genuine_paper_observation,
    validate_preflight_gates,
    compute_source_bundle_digest,
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


class MockAlpacaClient:
    def __init__(self):
        self.account_id = "PA12345"
        self.account_number = "12345"
        self.status = "ACTIVE"
        self.trading_blocked = False
        self.account_blocked = False
        self.currency = "USD"
        self.positions = [MockPosition("BTCUSD", "0.5", "60000.0", "30000.0")]
        self.orders = []
        self.asset = MockAsset("BTCUSD", True, True, "crypto")

    def get_account(self) -> Any:
        return self

    def get_positions(self) -> list[Any]:
        return self.positions

    def get_orders(self, query: Any) -> list[Any]:
        return self.orders

    def get_asset(self, symbol: str) -> Any:
        return self.asset


def test_preflight_gates_success() -> None:
    validate_preflight_gates(
        app_profile="paper",
        endpoint="https://paper-api.alpaca.markets",
        key_id="fake_key",
        secret_key="fake_secret",
        expected_account_id="PA12345",
        paper_broker_read_authorized=True,
        allow_network=True,
    )


def test_preflight_gates_failures() -> None:
    # Profile not paper
    with pytest.raises(PreflightCheckError, match="preflight_failed_profile_not_paper"):
        validate_preflight_gates(
            app_profile="live",
            endpoint="https://paper-api.alpaca.markets",
            key_id="fake_key",
            secret_key="fake_secret",
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
        )

    # Endpoint missing
    with pytest.raises(PreflightCheckError, match="preflight_failed_endpoint_missing"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint=None,
            key_id="fake_key",
            secret_key="fake_secret",
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
        )

    # Endpoint not paper
    with pytest.raises(PreflightCheckError, match="preflight_failed_endpoint_not_paper"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://api.alpaca.markets",
            key_id="fake_key",
            secret_key="fake_secret",
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
        )

    # Credentials incomplete
    with pytest.raises(PreflightCheckError, match="preflight_failed_credentials_incomplete"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            key_id="fake_key",
            secret_key=None,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
        )

    # Expected account missing
    with pytest.raises(PreflightCheckError, match="preflight_failed_expected_account_missing"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            key_id="fake_key",
            secret_key="fake_secret",
            expected_account_id=None,
            paper_broker_read_authorized=True,
            allow_network=True,
        )

    # Not authorized
    with pytest.raises(PreflightCheckError, match="preflight_failed_not_authorized"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            key_id="fake_key",
            secret_key="fake_secret",
            expected_account_id="PA12345",
            paper_broker_read_authorized=False,
            allow_network=True,
        )

    # Network blocked
    with pytest.raises(PreflightCheckError, match="preflight_failed_network_blocked"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            key_id="fake_key",
            secret_key="fake_secret",
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=False,
        )


def test_credentials_admission_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only one variable present: should block before client construction
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA12345")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)

    with pytest.raises(PreflightCheckError, match="preflight_failed_credentials_incomplete"):
        perform_genuine_paper_observation(
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=Path(".")
        )


def test_missing_explicit_endpoint_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA12345")
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")
    monkeypatch.delenv("ALPACA_PAPER_BASE_URL", raising=False)
    monkeypatch.delenv("APCA_API_BASE_URL", raising=False)
    monkeypatch.delenv("ALPACA_BASE_URL", raising=False)

    with pytest.raises(PreflightCheckError, match="preflight_failed_endpoint_missing"):
        perform_genuine_paper_observation(
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=Path(".")
        )


def test_blocked_account_status_blocks() -> None:
    client = MockAlpacaClient()
    client.account_blocked = True

    with pytest.raises(BrokerObservationError, match="broker_account_blocked"):
        perform_fixture_observation_evaluation(
            client,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
        )


def test_blocked_trading_status_blocks() -> None:
    client = MockAlpacaClient()
    client.trading_blocked = True

    with pytest.raises(BrokerObservationError, match="broker_account_trading_blocked"):
        perform_fixture_observation_evaluation(
            client,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
        )


def test_account_mismatch_hides_identifiers() -> None:
    client = MockAlpacaClient()
    # Different expected account ID
    with pytest.raises(BrokerObservationError) as exc_info:
        perform_fixture_observation_evaluation(
            client,
            expected_account_id="PA99999",
            paper_broker_read_authorized=True,
            allow_network=True,
        )
    # Check that neither observed nor expected values are leaked in exception
    err_text = str(exc_info.value)
    assert "PA12345" not in err_text
    assert "PA99999" not in err_text
    assert "12345" not in err_text
    assert err_text == "broker_account_mismatch"


def test_sdk_error_sanitized() -> None:
    client = MockAlpacaClient()
    # Mocking call to fail
    client.get_account = MagicMock(side_effect=RuntimeError("Connection refused by remote host, SSL Handshake failed, API key ID invalid."))

    with pytest.raises(BrokerObservationError) as exc_info:
        perform_fixture_observation_evaluation(
            client,
            expected_account_id="PA12345",
            paper_broker_read_authorized=True,
            allow_network=True,
        )

    err_text = str(exc_info.value)
    assert "Connection refused" not in err_text
    assert "SSL" not in err_text
    assert "API key" not in err_text
    assert err_text == "broker_read_failed"


def test_unreachable_market_data() -> None:
    # Assert that no quote, trade, or bar methods exist on perform genuine call or adapter surface
    # We can check that the module contains no references to get_crypto_latest_quote or similar
    adapter_file = Path("src/algotrader/execution/crypto_read_only_paper_observation_adapter.py")
    content = adapter_file.read_text(encoding="utf-8")
    assert "get_crypto_latest_quote" not in content
    assert "get_crypto_latest_trade" not in content
    assert "get_crypto_latest_bar" not in content


def test_truncation_fail_closed() -> None:
    client = MockAlpacaClient()
    # Generate 100 positions to trigger truncation
    client.positions = [MockPosition("BTCUSD", "0.1", "60000.0", "6000.0") for _ in range(100)]

    receipt = perform_fixture_observation_evaluation(
        client,
        expected_account_id="PA12345",
        paper_broker_read_authorized=True,
        allow_network=True,
    )
    assert receipt["truncation_indicators"]["positions_truncated"] is True


def test_fixture_capped_at_r1(tmp_path: Path) -> None:
    client = MockAlpacaClient()
    receipt = perform_fixture_observation_evaluation(
        client,
        expected_account_id="PA12345",
        paper_broker_read_authorized=True,
        allow_network=True,
    )

    # Save the fixture receipt
    tmp_path.mkdir(parents=True, exist_ok=True)
    obs_file = tmp_path / "observation_receipt.json"
    obs_file.write_text(json.dumps(receipt), encoding="utf-8")

    res = _validate_offline_receipt(tmp_path)
    assert res["valid"] is True
    assert res["classification"] == "fixture_replay_validated"
    assert res["broker_state_observed"] is False
    assert res["network_used"] is False
    assert res["broker_read_occurred"] is False


def test_manually_created_genuine_rejected(tmp_path: Path) -> None:
    # A manually created receipt with genuine classification but no invocation receipt must fail
    receipt = {
        "schema_version": "v5_33_production_broker_observation_receipt_v1",
        "adapter_version": "1.0",
        "observation_id": "man_id",
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "source_classification": "genuine_alpaca_paper_observation",
        "paper_endpoint_classification": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "sanitized_account_fingerprint": "abc",
        "target_symbol": "BTCUSD",
        "target_asset_class": "crypto",
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {
            "status": "active",
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        },
        "positions": [],
        "open_orders": [],
        "truncation_indicators": {"positions_truncated": False, "orders_truncated": False},
        "ambiguity_indicators": {"duplicate_positions": False, "duplicate_client_order_ids": False},
        "unexpected_exposure_classification": "clean",
        "safety_booleans": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "live_authorized": False,
            "network_used": True,
        },
    }

    # Compute canonical hash
    r_copy = dict(receipt)
    canonical_str = json.dumps(r_copy, sort_keys=True, separators=(",", ":"))
    receipt["canonical_receipt_sha256"] = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    obs_file = tmp_path / "observation_receipt.json"
    obs_file.write_text(json.dumps(receipt), encoding="utf-8")

    # Run validation (should fail since invocation receipt is missing)
    res = _validate_offline_receipt(tmp_path)
    assert res["valid"] is False
    assert res["classification"] == "blocked_invocation_receipt_missing"


def test_fixture_source_changed_to_genuine_rejected(tmp_path: Path) -> None:
    client = MockAlpacaClient()
    receipt = perform_fixture_observation_evaluation(
        client,
        expected_account_id="PA12345",
        paper_broker_read_authorized=True,
        allow_network=True,
    )

    # Tamper: change source_classification to genuine
    receipt["source_classification"] = "genuine_alpaca_paper_observation"

    # Re-calculate hash
    r_copy = dict(receipt)
    r_copy.pop("canonical_receipt_sha256", None)
    canonical_str = json.dumps(r_copy, sort_keys=True, separators=(",", ":"))
    receipt["canonical_receipt_sha256"] = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    obs_file = tmp_path / "observation_receipt.json"
    obs_file.write_text(json.dumps(receipt), encoding="utf-8")

    res = _validate_offline_receipt(tmp_path)
    assert res["valid"] is False
    assert res["classification"] == "blocked_not_genuine"


def test_invocation_without_matching_hash_rejected(tmp_path: Path) -> None:
    # Valid observation receipt
    obs = {
        "schema_version": "v5_33_production_broker_observation_receipt_v1",
        "source_classification": "genuine_alpaca_paper_observation",
        "paper_endpoint_classification": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "target_symbol": "BTCUSD",
        "target_asset_class": "crypto",
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {"status": "active", "trading_blocked": False, "account_blocked": False},
        "positions": [],
        "open_orders": [],
        "truncation_indicators": {"positions_truncated": False, "orders_truncated": False},
        "ambiguity_indicators": {"duplicate_positions": False, "duplicate_client_order_ids": False},
        "unexpected_exposure_classification": "clean",
        "safety_booleans": {"live_authorized": False, "network_used": True}
    }
    obs_hash = hashlib.sha256(json.dumps(obs, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    obs["canonical_receipt_sha256"] = obs_hash

    # Stale/mismatched invocation receipt
    inv = {
        "schema_version": "v5_33_production_invocation_receipt_v1",
        "adapter_version": "1.0",
        "adapter_source_bundle_sha256": "0" * 64,
        "command_source_identity": "crypto-paper-broker-observation",
        "normalized_paper_endpoint": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "observation_completion_utc": datetime.now(UTC).isoformat(),
        "call_counters": {
            "account_read_count": 1,
            "positions_read_count": 1,
            "orders_read_count": 1,
            "target_asset_read_count": 1
        },
        "safety_booleans": {"live_authorized": False},
        "observation_receipt_sha256": "different_hash"  # mismatch!
    }
    inv_hash = hashlib.sha256(json.dumps(inv, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    inv["canonical_invocation_sha256"] = inv_hash

    (tmp_path / "observation_receipt.json").write_text(json.dumps(obs), encoding="utf-8")
    (tmp_path / "invocation_receipt.json").write_text(json.dumps(inv), encoding="utf-8")

    res = _validate_offline_receipt(tmp_path)
    assert res["valid"] is False
    assert res["classification"] == "blocked_cross_bind_mismatch"


def test_all_zero_provenance_digest_rejected(tmp_path: Path) -> None:
    obs = {
        "schema_version": "v5_33_production_broker_observation_receipt_v1",
        "source_classification": "genuine_alpaca_paper_observation",
        "paper_endpoint_classification": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "target_symbol": "BTCUSD",
        "target_asset_class": "crypto",
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {"status": "active", "trading_blocked": False, "account_blocked": False},
        "positions": [],
        "open_orders": [],
        "truncation_indicators": {"positions_truncated": False, "orders_truncated": False},
        "ambiguity_indicators": {"duplicate_positions": False, "duplicate_client_order_ids": False},
        "unexpected_exposure_classification": "clean",
        "safety_booleans": {"live_authorized": False, "network_used": True}
    }
    obs_hash = hashlib.sha256(json.dumps(obs, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    obs["canonical_receipt_sha256"] = obs_hash

    inv = {
        "schema_version": "v5_33_production_invocation_receipt_v1",
        "adapter_version": "1.0",
        "adapter_source_bundle_sha256": "0" * 64,  # all-zero digest!
        "command_source_identity": "crypto-paper-broker-observation",
        "normalized_paper_endpoint": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "observation_completion_utc": datetime.now(UTC).isoformat(),
        "call_counters": {
            "account_read_count": 1,
            "positions_read_count": 1,
            "orders_read_count": 1,
            "target_asset_read_count": 1
        },
        "safety_booleans": {"live_authorized": False},
        "observation_receipt_sha256": obs_hash
    }
    inv_hash = hashlib.sha256(json.dumps(inv, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    inv["canonical_invocation_sha256"] = inv_hash

    (tmp_path / "observation_receipt.json").write_text(json.dumps(obs), encoding="utf-8")
    (tmp_path / "invocation_receipt.json").write_text(json.dumps(inv), encoding="utf-8")

    res = _validate_offline_receipt(tmp_path)
    assert res["valid"] is False
    assert res["classification"] == "blocked_source_bundle_digest_invalid"


def test_wrong_adapter_source_bundle_digest_rejected(tmp_path: Path) -> None:
    obs = {
        "schema_version": "v5_33_production_broker_observation_receipt_v1",
        "source_classification": "genuine_alpaca_paper_observation",
        "paper_endpoint_classification": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "target_symbol": "BTCUSD",
        "target_asset_class": "crypto",
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {"status": "active", "trading_blocked": False, "account_blocked": False},
        "positions": [],
        "open_orders": [],
        "truncation_indicators": {"positions_truncated": False, "orders_truncated": False},
        "ambiguity_indicators": {"duplicate_positions": False, "duplicate_client_order_ids": False},
        "unexpected_exposure_classification": "clean",
        "safety_booleans": {"live_authorized": False, "network_used": True}
    }
    obs_hash = hashlib.sha256(json.dumps(obs, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    obs["canonical_receipt_sha256"] = obs_hash

    inv = {
        "schema_version": "v5_33_production_invocation_receipt_v1",
        "adapter_version": "1.0",
        "adapter_source_bundle_sha256": "a" * 64,  # wrong digest!
        "command_source_identity": "crypto-paper-broker-observation",
        "normalized_paper_endpoint": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "observation_completion_utc": datetime.now(UTC).isoformat(),
        "call_counters": {
            "account_read_count": 1,
            "positions_read_count": 1,
            "orders_read_count": 1,
            "target_asset_read_count": 1
        },
        "safety_booleans": {"live_authorized": False},
        "observation_receipt_sha256": obs_hash
    }
    inv_hash = hashlib.sha256(json.dumps(inv, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    inv["canonical_invocation_sha256"] = inv_hash

    (tmp_path / "observation_receipt.json").write_text(json.dumps(obs), encoding="utf-8")
    (tmp_path / "invocation_receipt.json").write_text(json.dumps(inv), encoding="utf-8")

    res = _validate_offline_receipt(tmp_path)
    assert res["valid"] is False
    assert res["classification"] == "blocked_source_bundle_digest_mismatch"


def test_exact_call_counts_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set environment variables for preflight
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA12345")
    monkeypatch.setenv("ALPACA_API_KEY", "fake_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake_secret")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    # Mock client and verify that exactly 4 calls are performed
    client_instance = MockAlpacaClient()

    # Track call count
    get_acc_mock = MagicMock(return_value=client_instance)
    get_pos_mock = MagicMock(return_value=[])
    get_ord_mock = MagicMock(return_value=[])
    get_ast_mock = MagicMock(return_value=MockAsset("BTCUSD", True, True, "crypto"))

    with patch("algotrader.execution.alpaca_sdk_client.AlpacaSdkClient") as mock_sdk_class:
        sdk_instance = MagicMock()
        sdk_instance.get_account = get_acc_mock
        sdk_instance.get_positions = get_pos_mock
        sdk_instance.get_orders = get_ord_mock
        sdk_instance.get_asset = get_ast_mock
        mock_sdk_class.return_value = sdk_instance

        obs, inv = perform_genuine_paper_observation(
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=Path(".")
        )

        assert get_acc_mock.call_count == 1
        assert get_pos_mock.call_count == 1
        assert get_ord_mock.call_count == 1
        assert get_ast_mock.call_count == 1
        assert inv["call_counters"]["account_read_count"] == 1
        assert inv["call_counters"]["positions_read_count"] == 1
        assert inv["call_counters"]["orders_read_count"] == 1
        assert inv["call_counters"]["target_asset_read_count"] == 1


def test_v532_simulated_mode_remains_deterministic() -> None:
    # Verify we didn't break baseline replay determinism in crypto_supervised_readiness_trial
    # Run trial on sample fixture directory
    res = run_crypto_supervised_readiness_trial(
        output_root=Path("runs/crypto_supervised_readiness_trial/latest"),
        cycle_count=8,
    )
    assert res["trial_classification"] == "accepted"
    assert res["current_readiness_rung_code"] == "R1"
