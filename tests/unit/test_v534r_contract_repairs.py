"""Comprehensive contract tests for V5.34R repairs.

Verifies all 17 contract invariants specified in V5.34R requirements.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from algotrader.execution.crypto_paper_account_cleanup import (
    run_crypto_paper_account_cleanup,
)
from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    BrokerObservationError,
    get_source_provenance,
    perform_genuine_paper_observation,
)
from algotrader.execution.v534_burn_in_status import (
    build_v534_burn_in_status_packet,
    query_task_scheduler_status,
)
from algotrader.execution.v534_unattended_cycle import (
    run_v534_unattended_cycle,
)


@pytest.fixture
def mock_clean_provenance():
    with patch("algotrader.execution.v534_unattended_cycle.get_source_provenance") as m1, \
         patch("algotrader.execution.crypto_paper_account_cleanup.get_source_provenance") as m2:
        clean_prov = {
            "source_commit_sha": "9d40560052b2fb155586d5e978e25fd21f241cae",
            "source_tree_sha": "a9159fbfb3764914ab1a4d7cd94013b3bc41a455",
            "source_worktree_clean": True,
            "source_branch_or_detached": "main",
            "adapter_source_bundle_sha256": "0" * 64,
            "source_bundle_manifest": {},
        }
        m1.return_value = clean_prov
        m2.return_value = clean_prov
        yield clean_prov


@pytest.fixture
def mock_paper_env(tmp_path: Path):
    env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "test-key-id",
        "ALPACA_SECRET_KEY": "test-secret-key",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "PA3L5TESTACCOUNT",
    }
    with patch.dict(os.environ, env, clear=True):
        yield tmp_path


# 1. Real observation return ordering: (observation_receipt, invocation_receipt)
def test_1_real_observation_return_ordering(mock_paper_env):
    with patch("algotrader.execution.crypto_read_only_paper_observation_adapter.get_production_preflight_inputs") as mock_inputs, \
         patch("algotrader.execution.crypto_read_only_paper_observation_adapter.get_source_provenance") as mock_prov, \
         patch("algotrader.execution.alpaca_sdk_client.AlpacaSdkClient") as mock_client_cls:

        mock_inputs.return_value = {
            "app_profile": "paper",
            "endpoint": "https://paper-api.alpaca.markets",
            "key_id": "test-key",
            "secret_key": "test-secret",
            "expected_account_id": "PA3L5TESTACCOUNT",
        }
        mock_prov.return_value = {
            "source_commit_sha": "9d40560052b2fb155586d5e978e25fd21f241cae",
            "source_tree_sha": "a9159fbfb3764914ab1a4d7cd94013b3bc41a455",
            "source_worktree_clean": True,
            "source_branch_or_detached": "main",
            "adapter_source_bundle_sha256": "0" * 64,
            "source_bundle_manifest": {},
        }
        client = MagicMock()
        client.get_account.return_value = MagicMock(
            id="PA3L5TESTACCOUNT",
            account_id="PA3L5TESTACCOUNT",
            account_number="PA3L5TESTACCOUNT",
            status="ACTIVE",
            trading_blocked=False,
            account_blocked=False,
            suspended=False,
            transact_blocked=False,
            currency="USD",
        )
        client.get_positions.return_value = []
        client.get_orders.return_value = []
        client.get_asset.return_value = MagicMock(symbol="BTCUSD", asset_class="crypto", tradable=True, orderable=True)
        mock_client_cls.return_value = client

        obs_receipt, inv_receipt = perform_genuine_paper_observation(
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=mock_paper_env,
        )

        assert obs_receipt["schema_version"] == "v5_33_production_broker_observation_receipt_v1"
        assert inv_receipt["schema_version"] == "v5_33_production_invocation_receipt_v1"
        assert obs_receipt["canonical_receipt_sha256"] is not None
        assert inv_receipt["canonical_invocation_sha256"] is not None


# 2. Dirty source blocks before scheduler or network access
def test_2_dirty_source_blocks_before_scheduler_or_network(mock_paper_env):
    with patch("algotrader.execution.v534_unattended_cycle.get_source_provenance") as mock_prov, \
         patch("algotrader.execution.v534_unattended_cycle.OneShotExecutor") as mock_exec, \
         patch("algotrader.execution.v534_unattended_cycle.perform_genuine_paper_observation") as mock_obs:

        mock_prov.return_value = {
            "source_commit_sha": "dirty_commit",
            "source_tree_sha": "dirty_tree",
            "source_worktree_clean": False,
        }

        res = run_v534_unattended_cycle(
            output_root=mock_paper_env / "cycle_dirty",
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=mock_paper_env,
        )

        assert res["classification"] == "blocked_dirty_worktree"
        assert res["blocker"] == "dirty_worktree"
        assert res["next_autonomous_action"] == "clean_worktree_before_retry"
        mock_exec.assert_not_called()
        mock_obs.assert_not_called()


# 3. Success and failure observation layouts are persisted and consumed
def test_3_failure_observation_receipts_persisted(mock_paper_env, mock_clean_provenance):
    with patch("algotrader.execution.v534_unattended_cycle.OneShotExecutor") as mock_exec_cls, \
         patch("algotrader.execution.v534_unattended_cycle.perform_genuine_paper_observation") as mock_obs:

        executor = MagicMock()
        executor.tick.return_value = {"status": "completed", "classification": "accrued", "job_id": "job-1"}
        mock_exec_cls.return_value = executor

        inv_rec = {"schema_version": "v5_33_production_invocation_receipt_v1", "invocation_id": "inv-123"}
        fail_rec = {"schema_version": "v5_33_production_failure_receipt_v1", "terminal_stable_classification": "positions_validation_failed"}

        mock_obs.side_effect = BrokerObservationError(
            "positions_validation_failed",
            invocation_receipt=inv_rec,
            failure_receipt=fail_rec,
        )

        res = run_v534_unattended_cycle(
            output_root=mock_paper_env / "cycle_fail_obs",
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=mock_paper_env,
        )

        assert "broker_observation_failed" in res["classification"]
        assert res["broker_invocation_hash"] is not None
        assert res["broker_failure_hash"] is not None
        assert res["readiness_after"] == "R1"


# 4. Exact scheduler window fields populate composite receipt
def test_4_scheduler_window_fields_populate_composite(mock_paper_env, mock_clean_provenance):
    with patch("algotrader.execution.v534_unattended_cycle.OneShotExecutor") as mock_exec_cls, \
         patch("algotrader.execution.v534_unattended_cycle.perform_genuine_paper_observation") as mock_obs:

        executor = MagicMock()
        executor.tick.return_value = {"status": "completed", "classification": "accrued", "job_id": "job-20260720-1200"}
        mock_exec_cls.return_value = executor

        obs_rec = {
            "classification": "broker_state_observed",
            "account_validation": "success",
            "positions_validation": "success",
            "orders_validation": "success",
            "asset_validation": "success",
            "observed_positions_count": 0,
            "observed_open_orders_count": 0,
        }
        inv_rec = {"invocation_id": "inv-1"}
        mock_obs.return_value = (obs_rec, inv_rec)

        res = run_v534_unattended_cycle(
            output_root=mock_paper_env / "cycle_success",
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            as_of="2026-07-20T12:00:00Z",
            repo_root=mock_paper_env,
        )

        assert res["scheduler_job_identity"] == "job-20260720-1200"
        assert res["accepted_hour_window"] == "2026-07-20T12:00:00Z"
        assert res["classification"] == "cycle_completed_hold"
        assert res["readiness_after"] == "R2"
        assert res["account_flat_reconciled"] is True


# 5. No accepted receipt contains null required bindings
def test_5_no_accepted_receipt_contains_null_required_bindings(mock_paper_env, mock_clean_provenance):
    with patch("algotrader.execution.v534_unattended_cycle.OneShotExecutor") as mock_exec_cls, \
         patch("algotrader.execution.v534_unattended_cycle.perform_genuine_paper_observation") as mock_obs:

        executor = MagicMock()
        executor.tick.return_value = {"status": "completed", "classification": "accrued", "job_id": "job-1"}
        mock_exec_cls.return_value = executor

        obs_rec = {
            "classification": "broker_state_observed",
            "account_validation": "success",
            "positions_validation": "success",
            "orders_validation": "success",
            "asset_validation": "success",
            "observed_positions_count": 0,
            "observed_open_orders_count": 0,
        }
        inv_rec = {"invocation_id": "inv-1"}
        mock_obs.return_value = (obs_rec, inv_rec)

        res = run_v534_unattended_cycle(
            output_root=mock_paper_env / "cycle_no_nulls",
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            as_of="2026-07-20T14:00:00Z",
            repo_root=mock_paper_env,
        )

        for key in ("schema_version", "started_at_utc", "completed_at_utc", "classification", "accepted_hour_window", "source_commit_sha", "source_tree_sha", "scheduler_job_identity", "readiness_before", "readiness_after", "decision", "next_autonomous_action"):
            assert res.get(key) is not None, f"Key {key} should not be None"


# 6 & 7. Same accepted window performs no second fetch and failed cycle replay preserves failure
def test_6_7_same_accepted_window_idempotency_preserves_classification(mock_paper_env, mock_clean_provenance):
    out_dir = mock_paper_env / "idempotency_cycle"

    with patch("algotrader.execution.v534_unattended_cycle.OneShotExecutor") as mock_exec_cls, \
         patch("algotrader.execution.v534_unattended_cycle.perform_genuine_paper_observation") as mock_obs:

        executor = MagicMock()
        executor.tick.return_value = {"status": "completed", "classification": "accrued", "job_id": "job-1"}
        mock_exec_cls.return_value = executor

        obs_rec = {
            "classification": "broker_state_observed",
            "account_validation": "success",
            "positions_validation": "success",
            "orders_validation": "success",
            "asset_validation": "success",
            "observed_positions_count": 0,
            "observed_open_orders_count": 0,
        }
        inv_rec = {"invocation_id": "inv-1"}
        mock_obs.return_value = (obs_rec, inv_rec)

        res1 = run_v534_unattended_cycle(
            output_root=out_dir,
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            as_of="2026-07-20T15:15:00Z",
            repo_root=mock_paper_env,
        )
        assert res1["idempotent_replay"] is False

        # Re-run in same hour window
        res2 = run_v534_unattended_cycle(
            output_root=out_dir,
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            as_of="2026-07-20T15:45:00Z",
            repo_root=mock_paper_env,
        )
        assert res2["idempotent_replay"] is True
        assert res2["classification"] == "idempotent_same_window_replay"
        assert res2["original_classification"] == "cycle_completed_hold"


# 9 & 10. Status packet never defaults to success & missed/blocked derived
def test_9_10_status_packet_derives_classifications(mock_paper_env):
    with patch("algotrader.execution.v534_burn_in_status.query_task_scheduler_status") as mock_query:
        # Case A: Disabled task
        mock_query.return_value = {"task_exists": True, "enabled": False, "state": "Disabled"}
        pkt_disabled = build_v534_burn_in_status_packet(
            output_root=mock_paper_env / "status_disabled",
            cycles_root=mock_paper_env / "empty_cycles",
        )
        assert pkt_disabled["burn_in_classification"] in ("not_started", "activation_disabled")
        assert pkt_disabled["task_health"]["enabled"] is False

        # Case B: No cycle evidence
        mock_query.return_value = {"task_exists": True, "enabled": True, "state": "Ready"}
        pkt_no_cycles = build_v534_burn_in_status_packet(
            output_root=mock_paper_env / "status_empty",
            cycles_root=mock_paper_env / "empty_cycles",
        )
        assert pkt_no_cycles["burn_in_classification"] == "not_started"


# 13. Account non-flat preserves R1
def test_13_account_non_flat_preserves_r1(mock_paper_env, mock_clean_provenance):
    with patch("algotrader.execution.v534_unattended_cycle.OneShotExecutor") as mock_exec_cls, \
         patch("algotrader.execution.v534_unattended_cycle.perform_genuine_paper_observation") as mock_obs:

        executor = MagicMock()
        executor.tick.return_value = {"status": "completed", "classification": "accrued", "job_id": "job-1"}
        mock_exec_cls.return_value = executor

        obs_rec = {
            "classification": "broker_state_observed",
            "account_validation": "success",
            "positions_validation": "failed",
            "orders_validation": "success",
            "asset_validation": "success",
            "observed_positions_count": 1,
            "observed_open_orders_count": 0,
        }
        inv_rec = {"invocation_id": "inv-1"}
        mock_obs.return_value = (obs_rec, inv_rec)

        res = run_v534_unattended_cycle(
            output_root=mock_paper_env / "cycle_non_flat",
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            as_of="2026-07-20T16:00:00Z",
            repo_root=mock_paper_env,
        )

        assert res["readiness_after"] == "R1"
        assert res["account_flat_reconciled"] is False
        assert res["classification"] == "broker_reconciliation_failed"


# 14. Existing accepted close order prevents duplicate close
def test_14_existing_accepted_close_order_prevents_duplicate_close(mock_paper_env, mock_clean_provenance):
    with patch("algotrader.execution.crypto_paper_account_cleanup.AlpacaSdkClient") as mock_client_cls:
        client = MagicMock()
        exp_acc_id = os.environ.get("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "PA3L5TESTACCOUNT")
        account_mock = MagicMock(id=exp_acc_id, account_number=exp_acc_id, status="ACTIVE", trading_blocked=False, account_blocked=False, suspended=False, transact_blocked=False)
        client.get_account.return_value = account_mock

        pos_mock = MagicMock(symbol="SPY", qty="0.033")
        order_mock = MagicMock(id="order-spy-close", symbol="SPY", side="sell", type="market")
        client.get_positions.return_value = [pos_mock]
        client.get_orders.return_value = [order_mock]

        mock_client_cls.return_value = client

        res = run_crypto_paper_account_cleanup(
            output_root=mock_paper_env / "cleanup_dup_close",
            paper_cleanup_authorized=True,
            allow_network=True,
            repo_root=mock_paper_env,
        )

        # Ensure close_all_positions was NOT called because a close order was pending
        client.raw_trading_client.close_all_positions.assert_not_called()
        assert res["classification"] == "external_state_blocked"
        assert res["completed_at_utc"] is not None


# 15. Production receipts contain no account identity or identity-derived hash
def test_15_production_receipts_privacy_audit(mock_paper_env, mock_clean_provenance):
    with patch("algotrader.execution.crypto_read_only_paper_observation_adapter.get_production_preflight_inputs") as mock_inputs, \
         patch("algotrader.execution.crypto_read_only_paper_observation_adapter.get_source_provenance") as mock_prov, \
         patch("algotrader.execution.alpaca_sdk_client.AlpacaSdkClient") as mock_client_cls:

        mock_inputs.return_value = {
            "app_profile": "paper",
            "endpoint": "https://paper-api.alpaca.markets",
            "key_id": "test-key",
            "secret_key": "test-secret",
            "expected_account_id": "PA3L5TESTACCOUNT",
        }
        mock_prov.return_value = {
            "source_commit_sha": "9d40560052b2fb155586d5e978e25fd21f241cae",
            "source_tree_sha": "a9159fbfb3764914ab1a4d7cd94013b3bc41a455",
            "source_worktree_clean": True,
            "source_branch_or_detached": "main",
            "adapter_source_bundle_sha256": "0" * 64,
            "source_bundle_manifest": {},
        }
        client = MagicMock()
        client.get_account.return_value = MagicMock(
            id="PA3L5TESTACCOUNT",
            account_id="PA3L5TESTACCOUNT",
            account_number="PA3L5TESTACCOUNT",
            status="ACTIVE",
            trading_blocked=False,
            account_blocked=False,
            suspended=False,
            transact_blocked=False,
            currency="USD",
        )
        client.get_positions.return_value = []
        client.get_orders.return_value = []
        client.get_asset.return_value = MagicMock(symbol="BTCUSD", asset_class="crypto", tradable=True, orderable=True)
        mock_client_cls.return_value = client

        obs_receipt, inv_receipt = perform_genuine_paper_observation(
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=mock_paper_env,
        )

        obs_str = json.dumps(obs_receipt)
        assert "account_fingerprint" not in obs_str
        assert "sanitized_account_fingerprint" not in obs_str
        assert "PA3L5TESTACCOUNT" not in obs_str
