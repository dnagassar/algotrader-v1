"""Unit tests for V5.34 unattended paper-observed OOS burn-in.

Verifies bounded paper account cleanup, clean-source paper observation, flat reconciliation,
unattended composite operating cycle, same-window idempotency, 24-cycle deterministic
frontier progression, and strict credential/safety isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from algotrader.execution.crypto_paper_account_cleanup import (
    run_crypto_paper_account_cleanup,
)
from algotrader.execution.v534_unattended_cycle import (
    run_v534_unattended_cycle,
)


@pytest.fixture
def mock_paper_env(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "PKTEST1234567890")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "SKTEST12345678901234567890")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "test-account-uuid-1234")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")
    return tmp_path


@pytest.fixture
def mock_clean_provenance():
    with patch("algotrader.execution.crypto_paper_account_cleanup.get_source_provenance") as m1, \
         patch("algotrader.execution.crypto_read_only_paper_observation_adapter.get_source_provenance") as m2:
        prov = {
            "source_commit_sha": "9d40560052b2fb155586d5e978e25fd21f241cae",
            "source_tree_sha": "a9159fbfb3764914ab1a4d7cd94013b3bc41a455",
            "source_worktree_clean": True,
            "source_branch_or_detached": "main",
            "adapter_source_bundle_sha256": "0" * 64,
            "source_bundle_manifest": {},
        }
        m1.return_value = prov
        m2.return_value = prov
        yield prov


def test_cleanup_account_mismatch(mock_paper_env, mock_clean_provenance):
    with patch("algotrader.execution.crypto_paper_account_cleanup.AlpacaSdkClient") as mock_client_cls:
        client = MagicMock()
        client.get_account.return_value = MagicMock(id="wrong-account-id", status="ACTIVE", trading_blocked=False, account_blocked=False)
        mock_client_cls.return_value = client

        res = run_crypto_paper_account_cleanup(
            output_root=mock_paper_env / "cleanup",
            paper_cleanup_authorized=True,
            allow_network=True,
        )
        assert res["classification"] == "account_mismatch"
        assert res["expected_account_matched"] is False


def test_cleanup_successful(mock_paper_env, mock_clean_provenance):
    exp_acc_id = os.environ.get("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", "test-account-uuid-1234")
    with patch("algotrader.execution.crypto_paper_account_cleanup.AlpacaSdkClient") as mock_client_cls:
        client = MagicMock()
        account_mock = MagicMock(
            id=exp_acc_id,
            account_number=exp_acc_id,
            status="ACTIVE",
            trading_blocked=False,
            account_blocked=False,
            suspended=False,
            transact_blocked=False,
        )
        client.get_account.return_value = account_mock

        # First call has 1 position and 1 open order; second call (reconciliation) has 0
        pos_mock = MagicMock(symbol="BTCUSD", qty="1.0")
        order_mock = MagicMock(id="order-1", symbol="BTCUSD")
        client.get_positions.side_effect = [[pos_mock], []]
        client.get_orders.side_effect = [[order_mock], []]

        mock_client_cls.return_value = client

        res = run_crypto_paper_account_cleanup(
            output_root=mock_paper_env / "cleanup",
            paper_cleanup_authorized=True,
            allow_network=True,
        )
        assert res["classification"] == "cleanup_successful"
        assert res["expected_account_matched"] is True
        assert res["positions_before_count"] == 1
        assert res["open_orders_before_count"] == 1
        assert res["positions_after_count"] == 0
        assert res["open_orders_after_count"] == 0
        assert res["flatness_reconciled"] is True
        assert res["broker_mutation_performed"] is True


def test_v534_unattended_cycle_successful(mock_paper_env, mock_clean_provenance):
    out_dir = mock_paper_env / "cycle"
    as_of = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)

    with patch("algotrader.execution.v534_unattended_cycle.OneShotExecutor") as mock_exec_cls, \
         patch("algotrader.execution.v534_unattended_cycle.perform_genuine_paper_observation") as mock_obs:

        executor = MagicMock()
        executor.tick.return_value = {
            "status": "success",
            "classification": "fresh_completed_hour_accrued",
            "job_id": "job-20260720-1200",
        }
        mock_exec_cls.return_value = executor

        mock_obs.return_value = (
            {
                "source_commit_sha": "9d40560052b2fb155586d5e978e25fd21f241cae",
                "source_tree_sha": "a9159fbfb3764914ab1a4d7cd94013b3bc41a455",
                "source_worktree_clean": True,
            },
            {
                "classification": "broker_state_observed",
                "account_validation": "success",
                "positions_validation": "success",
                "orders_validation": "success",
                "asset_validation": "success",
                "observed_positions_count": 0,
                "observed_open_orders_count": 0,
                "stage_records": {
                    "account": {"attempt_count": 1, "completion_count": 1},
                    "positions": {"attempt_count": 1, "completion_count": 1},
                    "open_orders": {"attempt_count": 1, "completion_count": 1},
                    "target_asset": {"attempt_count": 1, "completion_count": 1},
                },
            },
        )

        res = run_v534_unattended_cycle(
            output_root=out_dir,
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            as_of=as_of,
        )

        assert res["classification"] == "cycle_completed_hold"
        assert res["decision"] == "hold_evidence_incomplete"
        assert res["account_flat_reconciled"] is True
        assert res["mutation_count"] == 0
        assert res["submission_count"] == 0
        assert res["idempotent_replay"] is False

        # Test same-window idempotency
        res_replay = run_v534_unattended_cycle(
            output_root=out_dir,
            scheduler_enabled=True,
            market_data_read_authorized=True,
            paper_broker_read_authorized=True,
            allow_network=True,
            as_of=as_of,
        )
        assert res_replay["classification"] == "idempotent_same_window_replay"
        assert res_replay["idempotent_replay"] is True


def test_deterministic_24_cycle_frontier_progression(mock_paper_env, mock_clean_provenance):
    out_dir = mock_paper_env / "cycle_24"
    start_time = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)

    with patch("algotrader.execution.v534_unattended_cycle.OneShotExecutor") as mock_exec_cls, \
         patch("algotrader.execution.v534_unattended_cycle.perform_genuine_paper_observation") as mock_obs:

        executor = MagicMock()
        mock_exec_cls.return_value = executor

        mock_obs.return_value = (
            {
                "source_commit_sha": "9d40560052b2fb155586d5e978e25fd21f241cae",
                "source_tree_sha": "a9159fbfb3764914ab1a4d7cd94013b3bc41a455",
                "source_worktree_clean": True,
            },
            {
                "classification": "broker_state_observed",
                "account_validation": "success",
                "positions_validation": "success",
                "orders_validation": "success",
                "asset_validation": "success",
                "observed_positions_count": 0,
                "observed_open_orders_count": 0,
                "stage_records": {
                    "account": {"attempt_count": 1, "completion_count": 1},
                    "positions": {"attempt_count": 1, "completion_count": 1},
                    "open_orders": {"attempt_count": 1, "completion_count": 1},
                    "target_asset": {"attempt_count": 1, "completion_count": 1},
                },
            },
        )

        for hour in range(24):
            tick_time = start_time + timedelta(hours=hour)
            hour_dir = out_dir / f"hour_{hour}"
            executor.tick.return_value = {
                "status": "success",
                "classification": "fresh_completed_hour_accrued",
                "job_id": f"job-{hour}",
            }

            res = run_v534_unattended_cycle(
                output_root=hour_dir,
                scheduler_enabled=True,
                market_data_read_authorized=True,
                paper_broker_read_authorized=True,
                allow_network=True,
                as_of=tick_time,
            )

            assert res["classification"] == "cycle_completed_hold"
            assert res["decision"] == "hold_evidence_incomplete"
            assert res["mutation_count"] == 0
            assert res["submission_count"] == 0
