"""Unit tests for V5.33.2 account identity canonicalization and safety ordering."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    BrokerObservationError,
    PreflightCheckError,
    _canonical_account_identity,
    _validate_account,
    perform_genuine_paper_observation,
    validate_preflight_gates,
)


class MockAccount:
    def __init__(self, account_id: Any = None, account_number: str | None = None):
        self.account_id = account_id
        self.account_number = account_number
        self.status = "ACTIVE"
        self.trading_blocked = False
        self.account_blocked = False
        self.suspended = False
        self.transact_blocked = False


def test_canonical_account_identity_rules() -> None:
    # 1. None / empty / whitespace
    assert _canonical_account_identity(None) is None
    assert _canonical_account_identity("") is None
    assert _canonical_account_identity("   ") is None

    # 2. uuid.UUID object
    u_obj = uuid.UUID("12345678-1234-5678-1234-567812345678")
    assert _canonical_account_identity(u_obj) == "12345678-1234-5678-1234-567812345678"

    # 3. Harmless whitespace and casing on UUID string
    raw_uuid_upper_space = "  12345678-1234-5678-1234-567812345678  ".upper()
    assert _canonical_account_identity(raw_uuid_upper_space) == "12345678-1234-5678-1234-567812345678"

    # 4. Non-UUID account number (case preserved, internal chars preserved)
    raw_acc_num = "  PA12345678-X  "
    assert _canonical_account_identity(raw_acc_num) == "PA12345678-X"


def test_validate_account_uuid_and_number_matching() -> None:
    u_str = "12345678-1234-5678-1234-567812345678"
    u_obj = uuid.UUID(u_str)

    raw_acc_uuid = MockAccount(account_id=u_obj, account_number="9999")

    # 1. Match SDK uuid object against expected uppercase UUID string with space
    assert _validate_account(raw_acc_uuid, f"  {u_str.upper()}  ") is None

    # 2. Match account number string
    raw_acc_num = MockAccount(account_id=None, account_number="PA-998877")
    assert _validate_account(raw_acc_num, "PA-998877") is None

    # 3. Genuine mismatch
    assert _validate_account(raw_acc_num, "DIFFERENT_ACCOUNT") == "account_mismatch"


def test_empty_expected_account_admission_blocked() -> None:
    with pytest.raises(PreflightCheckError, match="preflight_failed_expected_account_missing"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint="https://paper-api.alpaca.markets",
            key_id="fake_key",
            secret_key="fake_secret",
            expected_account_id="   ",
            paper_broker_read_authorized=True,
            allow_network=True,
        )


def test_no_later_broker_stage_runs_after_identity_mismatch(tmp_path: Path) -> None:
    # Mock client with mismatched account
    mock_client = MagicMock()
    raw_acc = MockAccount(account_id="WRONG_ID", account_number="WRONG_NUM")
    mock_client.get_account.return_value = raw_acc

    env_vars = {
        "APP_PROFILE": "paper",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
        "ALPACA_API_KEY": "fake_key",
        "ALPACA_SECRET_KEY": "fake_secret",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "EXPECTED_ID",
    }

    mock_prov = {
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "source_worktree_clean": True,
        "source_branch_or_detached": "test-branch",
        "adapter_source_bundle_sha256": "c" * 64,
        "source_bundle_manifest": {},
    }

    with patch.dict("os.environ", env_vars), \
         patch("algotrader.execution.alpaca_sdk_client.AlpacaSdkClient", return_value=mock_client), \
         patch("algotrader.execution.crypto_read_only_paper_observation_adapter.get_source_provenance", return_value=mock_prov):

        with pytest.raises(BrokerObservationError) as exc_info:
            perform_genuine_paper_observation(
                paper_broker_read_authorized=True,
                allow_network=True,
                repo_root=tmp_path,
            )

        assert exc_info.value.failure_receipt["terminal_failure_stage"] == "account"
        assert exc_info.value.failure_receipt["terminal_stable_classification"] == "account_validation_failed"

        # Verify account read occurred 1 time, and positions, open_orders, target_asset reads NEVER ran
        assert mock_client.get_account.call_count == 1
        assert mock_client.get_positions.call_count == 0
        assert mock_client.get_orders.call_count == 0
        assert mock_client.get_asset.call_count == 0

        # Verify raw identity is absent from receipts and exceptions
        receipt_str = str(exc_info.value.invocation_receipt) + str(exc_info.value.failure_receipt)
        assert "EXPECTED_ID" not in receipt_str
        assert "WRONG_ID" not in receipt_str
        assert "sanitized_account_fingerprint" not in receipt_str
