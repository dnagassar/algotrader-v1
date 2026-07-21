"""Unit tests for the V5.34 unattended paper-observed OOS burn-in repair.

These tests drive the real production components — the real observation
adapter return contract, the real durable OneShotExecutor with persistent
SQLite and on-disk frozen state, and the real composite cycle receipt
pipeline — mocking only the network-facing Alpaca SDK client, the source
provenance reads, and the Windows Task Scheduler query boundary.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from algotrader.execution.crypto_paper_account_cleanup import (
    run_crypto_paper_account_cleanup,
)
from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    PRODUCTION_INVOCATION_SCHEMA,
    PRODUCTION_OBSERVATION_SCHEMA,
    perform_genuine_paper_observation,
)
from algotrader.execution.v534_burn_in_status import (
    build_v534_burn_in_status_packet,
    query_windows_scheduled_task,
)
from algotrader.execution.v534_unattended_cycle import (
    CYCLE_SCHEMA_VERSION,
    run_v534_unattended_cycle,
)
from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
    PreviewDispatcher,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ACCOUNT_ID = "test-account-uuid-1234"

FROZEN_STATE_SCHEMA = "v5_23_crypto_tournament_v2_frozen_state_v1"

REQUIRED_ACCEPTED_BINDINGS = (
    "invocation_id",
    "invocation_source",
    "started_at_utc",
    "completed_at_utc",
    "cycle_as_of_utc",
    "classification",
    "exact_blocker",
    "source_commit_sha",
    "source_tree_sha",
    "adapter_source_bundle_sha256",
    "scheduler_job_identity",
    "scheduler_job_status",
    "scheduler_classification",
    "accepted_window_identity",
    "requested_start_bar_open",
    "requested_end_bar_open",
    "provider_as_of_boundary",
    "oos_frontier_before",
    "oos_frontier_after",
    "oos_state_fingerprint_before",
    "oos_state_fingerprint_after",
    "market_data_receipt_paths",
    "market_data_receipt_hashes",
    "scheduler_receipt_path",
    "scheduler_receipt_sha256",
    "broker_observation_classification",
    "broker_observation_receipt_path",
    "broker_observation_receipt_sha256",
    "broker_invocation_receipt_path",
    "broker_invocation_receipt_sha256",
    "broker_stage_attempt_counts",
    "broker_stage_completion_counts",
    "observed_positions_count",
    "observed_open_orders_count",
    "readiness_rung_before",
    "readiness_rung_after",
    "decision",
    "next_autonomous_action",
    "canonical_receipt_sha256",
)


# ==========================================================================
# Test doubles: plain attribute objects so validators see exact values.
# ==========================================================================


class _FakeAccount:
    def __init__(self, account_id: str = EXPECTED_ACCOUNT_ID) -> None:
        self.account_id = account_id
        self.account_number = account_id
        self.status = "ACTIVE"
        self.trading_blocked = False
        self.account_blocked = False
        self.suspended = False
        self.transact_blocked = False
        self.currency = "USD"


class _FakePosition:
    def __init__(self, symbol: str = "BTC/USD", qty: str = "0.5") -> None:
        self.symbol = symbol
        self.qty = qty
        self.average_entry_price = "50000"
        self.market_value = "25000"


class _FakeOrder:
    def __init__(
        self,
        order_id: str,
        symbol: str = "BTC/USD",
        side: str = "buy",
        status: str = "open",
    ) -> None:
        self.order_id = order_id
        self.id = order_id
        self.client_order_id = f"client_{order_id}"
        self.symbol = symbol
        self.side = side
        self.status = status
        self.qty = "0.1"
        self.notional = None


class _FakeAsset:
    def __init__(self) -> None:
        self.symbol = "BTC/USD"
        self.tradable = True
        self.orderable = True
        self.asset_class = "crypto"


class _FakeBrokerClient:
    """Read-only observation client double for the real adapter."""

    def __init__(self, positions=None, orders=None) -> None:
        self._positions = positions if positions is not None else []
        self._orders = orders if orders is not None else []

    def get_account(self):
        return _FakeAccount()

    def get_positions(self):
        return list(self._positions)

    def get_orders(self, query=None):
        return list(self._orders)

    def get_asset(self, symbol):
        return _FakeAsset()


class _ExactMutationRawClient:
    """Raw trading client exposing ONLY exact-order mutation methods.

    The intentional absence of ``cancel_orders`` and ``close_all_positions``
    proves the cleanup never reaches for account-wide bulk mutations.
    """

    def __init__(self) -> None:
        self.cancel_calls: list[str] = []
        self.close_calls: list[str] = []

    def cancel_order_by_id(self, order_id: str):
        self.cancel_calls.append(order_id)
        return None

    def close_position(self, symbol: str):
        self.close_calls.append(symbol)
        return _FakeOrder("close-order-1", symbol=symbol, side="sell")


_CLEAN_PROVENANCE = {
    "source_commit_sha": "9d40560052b2fb155586d5e978e25fd21f241cae",
    "source_tree_sha": "a9159fbfb3764914ab1a4d7cd94013b3bc41a455",
    "source_worktree_clean": True,
    "source_branch_or_detached": "main",
    "adapter_source_bundle_sha256": "0" * 64,
    "source_bundle_manifest": {},
}


@pytest.fixture
def mock_paper_env(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "PKTEST1234567890")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "SKTEST12345678901234567890")
    monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", EXPECTED_ACCOUNT_ID)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")
    return tmp_path


def _patch_clean_provenance():
    return patch.multiple(
        "algotrader.execution.v534_unattended_cycle",
        get_source_provenance=MagicMock(return_value=_CLEAN_PROVENANCE),
    )


def _patch_adapter_provenance():
    return patch(
        "algotrader.execution.crypto_read_only_paper_observation_adapter."
        "get_source_provenance",
        return_value=_CLEAN_PROVENANCE,
    )


def _patch_sdk_client(fake_client):
    return patch(
        "algotrader.execution.alpaca_sdk_client.AlpacaSdkClient",
        return_value=fake_client,
    )


def _patch_preview_dispatcher():
    return patch(
        "algotrader.orchestration.crypto_tournament_v2_oos_scheduler."
        "RealCommandDispatcher",
        new=lambda scheduler_enabled, market_data_read_authorized: PreviewDispatcher(),
    )


def _fake_oos_status(output_root, as_of=None, write_artifacts=False, **kwargs):
    """Persistent-state OOS status double: the frontier lives on disk."""
    state = json.loads(
        (Path(output_root) / "frozen_state.json").read_text(encoding="utf-8")
    )
    requested_start = state["updated_at"]
    return {
        "next_refresh": {
            "classification": "ready_for_explicit_read_only_market_data_fetch",
            "requested_start": requested_start,
            "requested_end": requested_start,
            "as_of": "",
        }
    }


def _patch_oos_status():
    return patch(
        "algotrader.research.crypto_tournament_v2_forward_oos."
        "run_crypto_tournament_v2_forward_oos",
        side_effect=_fake_oos_status,
    )


def _init_scheduler_state(scheduler_root: Path, first_requested_start: datetime) -> None:
    scheduler_root.mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": FROZEN_STATE_SCHEMA,
        "updated_at": first_requested_start.isoformat(),
    }
    (scheduler_root / "frozen_state.json").write_text(
        json.dumps(state), encoding="utf-8"
    )


def _run_cycle(tmp_path: Path, as_of: datetime, **overrides):
    kwargs = {
        "output_root": tmp_path / "cycle",
        "scheduler_output_root": tmp_path / "sched",
        "discovery_source": tmp_path / "missing_discovery.csv",
        "discovery_receipt": tmp_path / "missing_receipt.json",
        "scheduler_enabled": True,
        "market_data_read_authorized": True,
        "paper_broker_read_authorized": True,
        "allow_network": True,
        "as_of": as_of,
        "repo_root": tmp_path,
        "readiness_packet_path": tmp_path / "missing_readiness.json",
    }
    kwargs.update(overrides)
    return run_v534_unattended_cycle(**kwargs)


def _receipt_files(tmp_path: Path) -> list[Path]:
    receipts_dir = tmp_path / "cycle" / "receipts"
    if not receipts_dir.is_dir():
        return []
    return sorted(receipts_dir.glob("cycle_*.json"))


T0 = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)


def _cycle_as_of(hour_index: int) -> datetime:
    # Window [T0+h, T0+h] closes at T0+h+1h and is eligible 5 minutes later.
    return T0 + timedelta(hours=hour_index + 1, minutes=6)


# ==========================================================================
# 1. Actual production observation return contract (defect A).
# ==========================================================================


def test_actual_observation_return_ordering(mock_paper_env) -> None:
    with _patch_adapter_provenance(), _patch_sdk_client(_FakeBrokerClient()):
        result = perform_genuine_paper_observation(
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=mock_paper_env,
        )

    assert isinstance(result, tuple) and len(result) == 2
    observation_receipt, invocation_receipt = result
    assert observation_receipt["schema_version"] == PRODUCTION_OBSERVATION_SCHEMA
    assert invocation_receipt["schema_version"] == PRODUCTION_INVOCATION_SCHEMA
    assert (
        invocation_receipt["observation_receipt_sha256"]
        == observation_receipt["canonical_receipt_sha256"]
    )


def test_cycle_exercises_real_adapter_contract(mock_paper_env) -> None:
    """The composed cycle must succeed against the REAL adapter return order."""
    _init_scheduler_state(mock_paper_env / "sched", T0)
    with (
        _patch_clean_provenance(),
        _patch_adapter_provenance(),
        _patch_sdk_client(_FakeBrokerClient()),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        receipt = _run_cycle(mock_paper_env, _cycle_as_of(0))

    assert receipt["classification"] == "cycle_completed_hold"
    assert receipt["account_flat_reconciled"] is True
    obs = json.loads(
        Path(receipt["broker_observation_receipt_path"]).read_text(encoding="utf-8")
    )
    inv = json.loads(
        Path(receipt["broker_invocation_receipt_path"]).read_text(encoding="utf-8")
    )
    assert obs["schema_version"] == PRODUCTION_OBSERVATION_SCHEMA
    assert inv["schema_version"] == PRODUCTION_INVOCATION_SCHEMA


# ==========================================================================
# 2. Dirty source blocks before all side effects (defect B).
# ==========================================================================


def test_dirty_source_blocks_before_all_side_effects(mock_paper_env) -> None:
    from algotrader.execution.crypto_read_only_paper_observation_adapter import (
        PreflightCheckError,
    )

    with (
        patch(
            "algotrader.execution.v534_unattended_cycle.get_source_provenance",
            side_effect=PreflightCheckError("source_worktree_dirty"),
        ),
        patch(
            "algotrader.orchestration.crypto_tournament_v2_oos_scheduler."
            "OneShotExecutor"
        ) as mock_executor_cls,
        patch(
            "algotrader.execution.alpaca_sdk_client.AlpacaSdkClient"
        ) as mock_sdk_cls,
    ):
        receipt = _run_cycle(mock_paper_env, _cycle_as_of(0))

    assert receipt["classification"] == (
        "cycle_blocked_source_admission_source_worktree_dirty"
    )
    assert receipt["exact_blocker"] == "source_worktree_dirty"
    # Zero scheduler construction, zero claims, zero broker construction.
    assert mock_executor_cls.call_count == 0
    assert mock_sdk_cls.call_count == 0
    # Zero scheduler or OOS state changes.
    assert not (mock_paper_env / "sched").exists()
    # The only artifact is the immutable blocked receipt.
    assert len(_receipt_files(mock_paper_env)) == 1


# ==========================================================================
# 3-6. Receipt layouts, exact window binding, non-null accepted evidence.
# ==========================================================================


def _run_accepted_cycle(mock_paper_env, hour_index: int = 0, **overrides):
    with (
        _patch_clean_provenance(),
        _patch_adapter_provenance(),
        _patch_sdk_client(_FakeBrokerClient()),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        return _run_cycle(mock_paper_env, _cycle_as_of(hour_index), **overrides)


def test_success_receipt_layout_and_exact_window_binding(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    receipt = _run_accepted_cycle(mock_paper_env)

    assert receipt["classification"] == "cycle_completed_hold"
    expected_start = T0.isoformat()
    assert receipt["requested_start_bar_open"] == expected_start
    assert receipt["requested_end_bar_open"] == expected_start
    assert receipt["accepted_window_identity"] == f"{expected_start}_{expected_start}"
    assert receipt["provider_as_of_boundary"] == (T0 + timedelta(hours=1)).isoformat()
    assert receipt["oos_frontier_before"] == (T0 - timedelta(hours=1)).isoformat()
    assert receipt["oos_frontier_after"] == (T0 + timedelta(hours=1)).isoformat()

    # Scheduler receipt binding must reference a real hashed file.
    scheduler_receipt = Path(receipt["scheduler_receipt_path"])
    assert scheduler_receipt.is_file()
    digest = hashlib.sha256(scheduler_receipt.read_bytes()).hexdigest()
    assert digest == receipt["scheduler_receipt_sha256"]
    assert receipt["scheduler_job_identity"] not in ("", "na", None)

    # Market-data receipt bindings are populated with hashes.
    assert len(receipt["market_data_receipt_paths"]) == 2
    assert len(receipt["market_data_receipt_hashes"]) == 2
    assert receipt["oos_state_fingerprint_before"] != receipt[
        "oos_state_fingerprint_after"
    ]


def test_accepted_receipt_has_no_null_required_bindings(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    receipt = _run_accepted_cycle(mock_paper_env)

    for key in REQUIRED_ACCEPTED_BINDINGS:
        assert receipt.get(key) is not None, f"required binding {key!r} is null"
    assert receipt["broker_stage_attempt_counts"] == {
        "account": 1,
        "positions": 1,
        "open_orders": 1,
        "target_asset": 1,
    }
    assert receipt["broker_stage_completion_counts"] == {
        "account": 1,
        "positions": 1,
        "open_orders": 1,
        "target_asset": 1,
    }


def test_failure_receipt_layout_scheduler_blocked(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    with (
        _patch_clean_provenance(),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        receipt = _run_cycle(
            mock_paper_env, _cycle_as_of(0), scheduler_enabled=False
        )

    assert receipt["classification"] == (
        "cycle_blocked_scheduler_blocked_scheduler_disabled"
    )
    assert receipt["exact_blocker"] == "blocked_scheduler_disabled"
    assert receipt["decision"] == "hold_evidence_incomplete"
    assert receipt["next_autonomous_action"] is not None
    assert receipt["scheduler_receipt_path"] is not None
    assert receipt["paper_submit_performed"] is False
    assert receipt["mutation_count"] == 0


# ==========================================================================
# 7-8. Immutable originals and duplicate-window no-op receipts (defect D).
# ==========================================================================


def test_original_failure_receipts_are_immutable(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    with (
        _patch_clean_provenance(),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        first = _run_cycle(mock_paper_env, _cycle_as_of(0), scheduler_enabled=False)
        first_file = _receipt_files(mock_paper_env)[0]
        first_bytes = first_file.read_bytes()

        second = _run_cycle(mock_paper_env, _cycle_as_of(0), scheduler_enabled=False)

    files = _receipt_files(mock_paper_env)
    assert len(files) == 2
    # The original failure receipt remains byte-identical and stays a failure.
    assert first_file.read_bytes() == first_bytes
    assert first["classification"].startswith("cycle_blocked_")
    assert second["classification"].startswith("cycle_blocked_")
    assert second["invocation_id"] != first["invocation_id"]


def test_duplicate_window_emits_separate_no_op_receipt(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    original = _run_accepted_cycle(mock_paper_env)
    original_file = Path(original["broker_observation_receipt_path"])
    cycle_files = _receipt_files(mock_paper_env)
    assert len(cycle_files) == 1
    original_receipt_bytes = cycle_files[0].read_bytes()

    duplicate = _run_accepted_cycle(mock_paper_env)

    assert duplicate["classification"] == "duplicate_window_no_op"
    assert duplicate["idempotent_replay"] is True
    # The duplicate references the original receipt and its canonical hash.
    assert duplicate["duplicate_of_receipt_path"] == str(cycle_files[0])
    assert duplicate["duplicate_of_receipt_sha256"] == (
        original["canonical_receipt_sha256"]
    )
    # The original is untouched; the duplicate is a separate receipt.
    assert cycle_files[0].read_bytes() == original_receipt_bytes
    assert len(_receipt_files(mock_paper_env)) == 2
    # No second broker observation was performed for the duplicate.
    assert duplicate["broker_observation_receipt_path"] is None
    assert original_file.is_file()


def test_duplicate_keyed_on_window_not_wall_clock_hour(mock_paper_env) -> None:
    """A later wall-clock hour with no new window is still the same-window no-op."""
    _init_scheduler_state(mock_paper_env / "sched", T0)
    original = _run_accepted_cycle(mock_paper_env)
    assert original["classification"] == "cycle_completed_hold"

    # 20 minutes later, same accepted window: duplicate no-op.
    with (
        _patch_clean_provenance(),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        replay = _run_cycle(
            mock_paper_env, _cycle_as_of(0) + timedelta(minutes=20)
        )
    assert replay["classification"] == "duplicate_window_no_op"

    # One hour later a NEW window exists: not a duplicate, a fresh cycle.
    second = _run_accepted_cycle(mock_paper_env, hour_index=1)
    assert second["classification"] == "cycle_completed_hold"
    assert second["accepted_window_identity"] != original["accepted_window_identity"]


# ==========================================================================
# 9-10. Persistent 24-cycle continuity with restart between invocations.
# ==========================================================================


def test_persistent_24_cycle_frontier_progression_with_restart(
    mock_paper_env,
) -> None:
    scheduler_root = mock_paper_env / "sched"
    _init_scheduler_state(scheduler_root, T0)

    window_identities: list[str] = []
    for hour in range(24):
        # Every invocation is a fresh construction of the executor, store and
        # dispatcher; continuity may come only from the persistent SQLite
        # store, the on-disk frozen state, and the immutable receipt history.
        receipt = _run_accepted_cycle(mock_paper_env, hour_index=hour)

        expected_start = (T0 + timedelta(hours=hour)).isoformat()
        assert receipt["classification"] == "cycle_completed_hold"
        assert receipt["requested_start_bar_open"] == expected_start
        assert receipt["requested_end_bar_open"] == expected_start
        assert receipt["oos_frontier_after"] == (
            T0 + timedelta(hours=hour + 1)
        ).isoformat()
        assert receipt["mutation_count"] == 0
        assert receipt["submission_count"] == 0
        window_identities.append(receipt["accepted_window_identity"])

    # Exact frontier progression: 24 distinct contiguous hourly windows.
    assert len(set(window_identities)) == 24
    assert len(_receipt_files(mock_paper_env)) == 24

    # The persistent index binds all 24 accepted windows.
    index = json.loads(
        (mock_paper_env / "cycle" / "cycle_index.json").read_text(encoding="utf-8")
    )
    assert len(index["entries"]) == 24

    # The frozen state on disk carries the final frontier.
    state = json.loads(
        (scheduler_root / "frozen_state.json").read_text(encoding="utf-8")
    )
    assert state["updated_at"] == (T0 + timedelta(hours=24)).isoformat()

    # A same-window replay after the 24 cycles remains a no-op.
    with (
        _patch_clean_provenance(),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        replay = _run_cycle(mock_paper_env, _cycle_as_of(23) + timedelta(minutes=5))
    assert replay["classification"] == "duplicate_window_no_op"


def test_missed_hours_accrue_as_catch_up_window(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    first = _run_accepted_cycle(mock_paper_env, hour_index=0)
    assert first["classification"] == "cycle_completed_hold"

    # Two invocation hours are missed; the next tick accrues the catch-up
    # window covering exactly the missed closed hours.
    catch_up = _run_accepted_cycle(mock_paper_env, hour_index=3)
    assert catch_up["classification"] == "cycle_completed_hold"
    assert catch_up["requested_start_bar_open"] == (
        T0 + timedelta(hours=1)
    ).isoformat()
    assert catch_up["requested_end_bar_open"] == (
        T0 + timedelta(hours=3)
    ).isoformat()


# ==========================================================================
# Blocked-cycle accumulation and broker-authorization gating.
# ==========================================================================


def test_blocked_cycles_accumulate_immutable_receipts(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    with (
        _patch_clean_provenance(),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        for attempt in range(3):
            receipt = _run_cycle(
                mock_paper_env, _cycle_as_of(0), scheduler_enabled=False
            )
            assert receipt["classification"].startswith("cycle_blocked_")

    assert len(_receipt_files(mock_paper_env)) == 3


def test_broker_observation_not_authorized_blocks_after_accrual(
    mock_paper_env,
) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    with (
        _patch_clean_provenance(),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
        patch(
            "algotrader.execution.alpaca_sdk_client.AlpacaSdkClient"
        ) as mock_sdk_cls,
    ):
        receipt = _run_cycle(
            mock_paper_env, _cycle_as_of(0), paper_broker_read_authorized=False
        )

    assert receipt["classification"] == (
        "cycle_blocked_broker_observation_not_authorized"
    )
    assert mock_sdk_cls.call_count == 0


# ==========================================================================
# 15. Retained R1 for a non-flat account.
# ==========================================================================


def test_non_flat_btc_account_retains_r1(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    fake_client = _FakeBrokerClient(positions=[_FakePosition()])
    with (
        _patch_clean_provenance(),
        _patch_adapter_provenance(),
        _patch_sdk_client(fake_client),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        receipt = _run_cycle(mock_paper_env, _cycle_as_of(0))

    assert receipt["classification"] == "cycle_completed_hold_account_not_flat"
    assert receipt["account_flat_reconciled"] is False
    assert receipt["observed_positions_count"] == 1
    assert receipt["readiness_rung_after"] == "R1"
    assert receipt["exact_blocker"] == "blocked_external_paper_account_state"
    assert receipt["decision"] == "hold_evidence_incomplete"


def test_unexpected_equity_exposure_fails_observation(mock_paper_env) -> None:
    """A retained non-target position (e.g. SPY) is a truthful failed cycle."""
    _init_scheduler_state(mock_paper_env / "sched", T0)
    fake_client = _FakeBrokerClient(positions=[_FakePosition(symbol="SPY")])
    with (
        _patch_clean_provenance(),
        _patch_adapter_provenance(),
        _patch_sdk_client(fake_client),
        _patch_preview_dispatcher(),
        _patch_oos_status(),
    ):
        receipt = _run_cycle(mock_paper_env, _cycle_as_of(0))

    assert receipt["classification"] == (
        "cycle_failed_broker_observation_positions_validation_failed"
    )
    assert receipt["broker_failure_receipt_path"] is not None
    assert receipt["decision"] == "hold_evidence_incomplete"


# ==========================================================================
# 17. No account identity or identity-derived hashes in evidence (defect H).
# ==========================================================================


def test_observation_receipts_contain_no_account_identity(mock_paper_env) -> None:
    with _patch_adapter_provenance(), _patch_sdk_client(_FakeBrokerClient()):
        observation_receipt, invocation_receipt = perform_genuine_paper_observation(
            paper_broker_read_authorized=True,
            allow_network=True,
            repo_root=mock_paper_env,
        )

    serialized = json.dumps(observation_receipt) + json.dumps(invocation_receipt)
    assert EXPECTED_ACCOUNT_ID not in serialized
    assert "fingerprint" not in serialized.lower()
    identity_digest = hashlib.sha256(
        f"{EXPECTED_ACCOUNT_ID}:{EXPECTED_ACCOUNT_ID}".encode("utf-8")
    ).hexdigest()
    assert identity_digest not in serialized
    # Safe facts remain.
    assert observation_receipt["expected_account_configured"] is True
    assert observation_receipt["expected_account_match"] is True


def test_adapter_source_defines_no_account_fingerprint_field() -> None:
    source = (
        PROJECT_ROOT
        / "src/algotrader/execution/crypto_read_only_paper_observation_adapter.py"
    ).read_text(encoding="utf-8")
    assert "sanitized_account_fingerprint" not in source
    assert "account_fingerprint" not in source


# ==========================================================================
# 16 + defect F. Exact-order-bound cleanup.
# ==========================================================================


def _patch_cleanup_env():
    return patch(
        "algotrader.execution.crypto_paper_account_cleanup.get_source_provenance",
        return_value=_CLEAN_PROVENANCE,
    )


def test_cleanup_account_mismatch_stops_before_mutation(mock_paper_env) -> None:
    client = MagicMock()
    client.get_account.return_value = _FakeAccount(account_id="wrong-account-id")
    with (
        _patch_cleanup_env(),
        patch(
            "algotrader.execution.crypto_paper_account_cleanup.AlpacaSdkClient",
            return_value=client,
        ),
    ):
        res = run_crypto_paper_account_cleanup(
            output_root=mock_paper_env / "cleanup",
            paper_cleanup_authorized=True,
            allow_network=True,
        )
    assert res["classification"] == "account_mismatch"
    assert res["expected_account_matched"] is False
    assert res["broker_mutation_performed"] is False


def test_cleanup_uses_exact_order_bound_mutations(mock_paper_env) -> None:
    raw = _ExactMutationRawClient()
    client = MagicMock()
    client.get_account.return_value = _FakeAccount()
    client.raw_trading_client = raw
    # Pre-observed: one long BTCUSD position, one NON-reducing open buy order.
    client.get_positions.side_effect = [[_FakePosition()], []]
    client.get_orders.side_effect = [
        [_FakeOrder("order-1", side="buy")],  # pre-observation
        [],  # cancel reconciliation
        [],  # final reconciliation
    ]

    with (
        _patch_cleanup_env(),
        patch(
            "algotrader.execution.crypto_paper_account_cleanup.AlpacaSdkClient",
            return_value=client,
        ),
    ):
        res = run_crypto_paper_account_cleanup(
            output_root=mock_paper_env / "cleanup",
            paper_cleanup_authorized=True,
            allow_network=True,
        )

    assert res["classification"] == "cleanup_successful"
    # Mutations bound to the exact pre-observed order id and position symbol.
    assert raw.cancel_calls == ["order-1"]
    assert raw.close_calls == ["BTCUSD"]
    assert res["cancel_attempt_count"] == 1
    assert res["cancel_completion_count"] == 1
    assert res["close_attempt_count"] == 1
    assert res["close_completion_count"] == 1
    assert res["flatness_reconciled"] is True
    assert res["cancel_operations"][0]["classification"] == "cancel_request_accepted"
    assert res["close_operations"][0]["classification"] == "close_request_accepted"


def test_cleanup_never_duplicates_existing_close_order(mock_paper_env) -> None:
    raw = _ExactMutationRawClient()
    client = MagicMock()
    client.get_account.return_value = _FakeAccount()
    client.raw_trading_client = raw
    # A long position with an existing reducing (sell) order: never cancel it,
    # never submit another close, and stop blocked while it stays open.
    client.get_positions.return_value = [_FakePosition()]
    client.get_orders.return_value = [_FakeOrder("close-existing", side="sell")]

    with (
        _patch_cleanup_env(),
        patch(
            "algotrader.execution.crypto_paper_account_cleanup.AlpacaSdkClient",
            return_value=client,
        ),
        patch("algotrader.execution.crypto_paper_account_cleanup.time.sleep"),
    ):
        res = run_crypto_paper_account_cleanup(
            output_root=mock_paper_env / "cleanup",
            paper_cleanup_authorized=True,
            allow_network=True,
        )

    assert res["classification"] == "cleanup_blocked_existing_close_order_pending"
    assert raw.cancel_calls == []
    assert raw.close_calls == []
    assert res["preserved_close_orders"] == [
        {
            "order_id": "close-existing",
            "symbol": "BTCUSD",
            "classification": "preserved_existing_close_order",
        }
    ]
    assert res["close_operations"][0]["classification"] == (
        "close_skipped_existing_close_order_pending"
    )
    assert res["flatness_reconciled"] is False


def test_cleanup_submission_acceptance_is_not_closure(mock_paper_env) -> None:
    raw = _ExactMutationRawClient()
    client = MagicMock()
    client.get_account.return_value = _FakeAccount()
    client.raw_trading_client = raw
    # close_position is accepted, but the position never leaves the account.
    client.get_positions.return_value = [_FakePosition()]
    client.get_orders.return_value = []

    with (
        _patch_cleanup_env(),
        patch(
            "algotrader.execution.crypto_paper_account_cleanup.AlpacaSdkClient",
            return_value=client,
        ),
        patch("algotrader.execution.crypto_paper_account_cleanup.time.sleep"),
    ):
        res = run_crypto_paper_account_cleanup(
            output_root=mock_paper_env / "cleanup",
            paper_cleanup_authorized=True,
            allow_network=True,
        )

    assert res["classification"] == "cleanup_reconciliation_unresolved"
    assert raw.close_calls == ["BTCUSD"]
    assert res["close_completion_count"] == 0
    assert res["flatness_reconciled"] is False


def test_cleanup_source_contains_no_bulk_mutation_calls() -> None:
    path = PROJECT_ROOT / "src/algotrader/execution/crypto_paper_account_cleanup.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    attribute_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "cancel_orders" not in attribute_calls
    assert "close_all_positions" not in attribute_calls
    assert "cancel_order_by_id" in attribute_calls
    assert "close_position" in attribute_calls


# ==========================================================================
# 13-14. Actual Task Scheduler observation boundary (defect C).
# ==========================================================================


class _FakeCompleted:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_task_query_failure_is_truthful() -> None:
    def failing_runner(*args, **kwargs):
        raise OSError("powershell unavailable")

    observation = query_windows_scheduled_task(runner=failing_runner)
    assert observation["query_classification"] == "task_query_failed"
    assert observation["task_observed"] is False
    assert "enabled" not in observation


def test_task_disabled_classification(tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "state": "Disabled",
            "action_execute": "powershell.exe",
            "action_arguments": "-File run_v534_unattended_cycle.ps1",
            "last_run_time": "7/20/2026 6:05:01 PM",
            "last_task_result": 1,
            "next_run_time": "",
            "missed_run_count": 1,
        }
    )

    def disabled_runner(*args, **kwargs):
        return _FakeCompleted(0, stdout=payload)

    observation = query_windows_scheduled_task(runner=disabled_runner)
    assert observation["query_classification"] == "task_observed"
    assert observation["enabled"] is False

    packet = build_v534_burn_in_status_packet(
        output_root=tmp_path / "burn_in",
        cycle_output_root=tmp_path / "cycle",
        task_query=lambda: observation,
        credential_rotation_confirmed=True,
    )
    assert packet["burn_in_classification"] == "activation_disabled"
    assert packet["task_health"]["last_task_result"] == 1


def test_burn_in_status_query_failure_blocks(tmp_path: Path) -> None:
    packet = build_v534_burn_in_status_packet(
        output_root=tmp_path / "burn_in",
        cycle_output_root=tmp_path / "cycle",
        task_query=lambda: {
            "task_name": "x",
            "query_classification": "task_query_failed",
            "task_observed": False,
        },
        credential_rotation_confirmed=True,
    )
    assert packet["burn_in_classification"] == "blocked_task_query_failed"
    assert packet["scheduled_completed_cycle_count"] == 0


# ==========================================================================
# 11-12 + defect C. Burn-in accounting from validated receipts only.
# ==========================================================================


def _write_cycle_receipt(
    cycle_root: Path,
    *,
    index: int,
    classification: str,
    window_start: datetime,
    window_end: datetime | None = None,
    invocation_source: str = "scheduled",
    account_flat: bool = True,
    tamper: bool = False,
) -> None:
    end = window_end or window_start
    receipt = {
        "schema_version": CYCLE_SCHEMA_VERSION,
        "invocation_id": f"invocation-{index}",
        "invocation_source": invocation_source,
        "classification": classification,
        "completed_at_utc": (end + timedelta(hours=1, minutes=6)).isoformat(),
        "requested_start_bar_open": window_start.isoformat(),
        "requested_end_bar_open": end.isoformat(),
        "oos_frontier_after": (end + timedelta(hours=1)).isoformat(),
        "account_flat_reconciled": account_flat,
        "readiness_rung_after": "R1",
        "broker_observation_classification": "genuine_alpaca_paper_observation",
        "decision": "hold_evidence_incomplete",
        "mutation_count": 0,
        "submission_count": 0,
        "paper_submit_performed": False,
        "paper_mutation_performed": False,
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    receipt["canonical_receipt_sha256"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    if tamper:
        receipt["classification"] = "cycle_completed_hold"
    receipts_dir = cycle_root / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    (receipts_dir / f"cycle_{index:04d}.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )


def _enabled_task_query() -> dict:
    return {
        "task_name": "crypto-tournament-v2-oos-scheduler",
        "query_classification": "task_observed",
        "task_observed": True,
        "state": "Ready",
        "enabled": True,
        "running": False,
        "last_task_result": 0,
    }


def test_burn_in_counts_only_validated_scheduled_receipts(tmp_path: Path) -> None:
    cycle_root = tmp_path / "cycle"
    start = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)
    # 3 scheduled completed cycles with a 1-hour gap after the second
    # (missed cycle), plus a manual completed cycle, a blocked cycle, and a
    # tampered receipt that must be rejected.
    _write_cycle_receipt(cycle_root, index=0, classification="cycle_completed_hold", window_start=start)
    _write_cycle_receipt(cycle_root, index=1, classification="cycle_completed_hold", window_start=start + timedelta(hours=1))
    _write_cycle_receipt(cycle_root, index=2, classification="cycle_completed_hold", window_start=start + timedelta(hours=3))
    _write_cycle_receipt(cycle_root, index=3, classification="cycle_completed_hold", window_start=start + timedelta(hours=4), invocation_source="manual")
    _write_cycle_receipt(cycle_root, index=4, classification="cycle_blocked_scheduler_blocked_scheduler_disabled", window_start=start + timedelta(hours=5))
    _write_cycle_receipt(cycle_root, index=5, classification="cycle_blocked_source_admission_source_worktree_dirty", window_start=start + timedelta(hours=6))
    _write_cycle_receipt(cycle_root, index=6, classification="cycle_blocked_scheduler_blocked_scheduler_disabled", window_start=start + timedelta(hours=7), tamper=True)

    packet = build_v534_burn_in_status_packet(
        output_root=tmp_path / "burn_in",
        cycle_output_root=cycle_root,
        task_query=_enabled_task_query,
        credential_rotation_confirmed=True,
        unattended_secret_mechanism="windows_credential_manager",
    )

    assert packet["scheduled_completed_cycle_count"] == 3
    assert packet["manual_completed_cycle_count"] == 1
    assert packet["blocked_cycle_count"] == 2
    assert packet["missed_cycle_count"] == 1
    assert packet["invalid_receipt_count"] == 1
    assert packet["burn_in_classification"] == "burn_in_active_cycle_3_of_24"
    assert packet["mutation_counters"]["mutation_count"] == 0
    assert packet["mutation_counters"]["submission_count"] == 0


def test_burn_in_complete_requires_24_scheduled_receipts(tmp_path: Path) -> None:
    cycle_root = tmp_path / "cycle"
    start = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)
    for hour in range(24):
        _write_cycle_receipt(
            cycle_root,
            index=hour,
            classification="cycle_completed_hold",
            window_start=start + timedelta(hours=hour),
        )

    packet = build_v534_burn_in_status_packet(
        output_root=tmp_path / "burn_in",
        cycle_output_root=cycle_root,
        task_query=_enabled_task_query,
        credential_rotation_confirmed=True,
        unattended_secret_mechanism="windows_credential_manager",
    )
    assert packet["burn_in_classification"] == "burn_in_complete_24_of_24"
    assert packet["missed_cycle_count"] == 0


def test_burn_in_no_fabricated_defaults(tmp_path: Path) -> None:
    """An empty evidence root must never classify as active or healthy."""
    packet = build_v534_burn_in_status_packet(
        output_root=tmp_path / "burn_in",
        cycle_output_root=tmp_path / "cycle",
        task_query=_enabled_task_query,
        credential_rotation_confirmed=True,
        unattended_secret_mechanism="windows_credential_manager",
    )
    assert packet["burn_in_classification"] == "not_started"
    assert packet["scheduled_completed_cycle_count"] == 0
    assert packet["current_oos_frontier"] is None
    assert packet["current_frontier_lag_seconds"] is None
    assert packet["last_cycle_classification"] is None
    assert packet["paper_account_flat"] is None


def test_burn_in_credential_rotation_gate(tmp_path: Path) -> None:
    packet = build_v534_burn_in_status_packet(
        output_root=tmp_path / "burn_in",
        cycle_output_root=tmp_path / "cycle",
        task_query=_enabled_task_query,
        credential_rotation_confirmed=False,
    )
    assert packet["burn_in_classification"] == "blocked_credential_rotation_required"
    assert packet["next_autonomous_action"] == (
        "await_credential_rotation_confirmation"
    )


def test_burn_in_unattended_secret_loading_gate(tmp_path: Path) -> None:
    packet = build_v534_burn_in_status_packet(
        output_root=tmp_path / "burn_in",
        cycle_output_root=tmp_path / "cycle",
        task_query=_enabled_task_query,
        credential_rotation_confirmed=True,
        unattended_secret_mechanism=None,
    )
    assert packet["burn_in_classification"] == "blocked_unattended_secret_loading"


def test_burn_in_non_flat_account_reports_external_blocker(tmp_path: Path) -> None:
    cycle_root = tmp_path / "cycle"
    start = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)
    _write_cycle_receipt(
        cycle_root,
        index=0,
        classification="cycle_completed_hold_account_not_flat",
        window_start=start,
        account_flat=False,
    )
    packet = build_v534_burn_in_status_packet(
        output_root=tmp_path / "burn_in",
        cycle_output_root=cycle_root,
        task_query=_enabled_task_query,
        credential_rotation_confirmed=True,
        unattended_secret_mechanism="windows_credential_manager",
    )
    assert packet["paper_account_flat"] is False
    assert packet["external_account_blocker"] == "blocked_external_paper_account_state"
    assert packet["readiness_rung"] == "R1"


# ==========================================================================
# 18 + defect G. Credential isolation and least-privilege child environments.
# ==========================================================================


V534_WRAPPERS = (
    "scripts/run_v534_unattended_cycle.ps1",
    "scripts/run_v534_paper_broker_observation.ps1",
    "scripts/run_crypto_paper_account_cleanup.ps1",
)


@pytest.mark.parametrize("wrapper", V534_WRAPPERS)
def test_wrappers_never_load_plaintext_env_files(wrapper: str) -> None:
    source = (PROJECT_ROOT / wrapper).read_text(encoding="utf-8")
    assert "load_env" not in source
    assert ".env" not in source
    assert "Desktop\\algo_trader\\.env" not in source


@pytest.mark.parametrize("wrapper", V534_WRAPPERS)
def test_wrappers_never_duplicate_secret_aliases(wrapper: str) -> None:
    source = (PROJECT_ROOT / wrapper).read_text(encoding="utf-8")
    assert "$env:ALPACA_API_KEY =" not in source
    assert "$env:ALPACA_SECRET_KEY =" not in source
    assert "APCA_API_KEY_ID" not in source
    assert "APCA_API_SECRET_KEY" not in source


def test_scheduler_child_environment_is_least_privilege() -> None:
    source = (
        PROJECT_ROOT
        / "src/algotrader/orchestration/crypto_tournament_v2_oos_scheduler.py"
    ).read_text(encoding="utf-8")
    # The dispatcher must exclude credential prefixes from child environments
    # and must never re-inject or alias secrets into the child process.
    assert '("ALPACA_", "APCA_", "TIINGO_")' in source
    assert 'env["ALPACA_API_KEY"]' not in source
    assert 'env["ALPACA_SECRET_KEY"]' not in source
    assert 'env["APCA_API_KEY_ID"]' not in source
    assert 'env["APCA_API_SECRET_KEY"]' not in source
    # Subprocess stderr/stdout must not be persisted into receipt reasons.
    assert "result.stderr or result.stdout" not in source


def test_preflight_inputs_require_matched_credential_pairs(monkeypatch) -> None:
    from algotrader.execution.crypto_read_only_paper_observation_adapter import (
        get_production_preflight_inputs,
    )

    for name in (
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_API_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    # A key from one alias family with a secret from another must not pair.
    monkeypatch.setenv("ALPACA_API_KEY", "PKTEST")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "SKTEST")
    inputs = get_production_preflight_inputs()
    assert inputs["key_id"] is None
    assert inputs["secret_key"] is None


# ==========================================================================
# 19. No paper submission surface while strategy evidence is incomplete.
# ==========================================================================


def test_cycle_module_has_no_mutation_surface() -> None:
    path = PROJECT_ROOT / "src/algotrader/execution/v534_unattended_cycle.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    attribute_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden = {
        "submit_order",
        "submit_order_request",
        "cancel_order",
        "cancel_order_by_id",
        "replace_order",
        "close_position",
        "close_all_positions",
        "liquidate",
    }
    assert attribute_calls.isdisjoint(forbidden)


def test_completed_cycle_never_submits(mock_paper_env) -> None:
    _init_scheduler_state(mock_paper_env / "sched", T0)
    receipt = _run_accepted_cycle(mock_paper_env)
    assert receipt["decision"] == "hold_evidence_incomplete"
    assert receipt["paper_submit_performed"] is False
    assert receipt["paper_mutation_performed"] is False
    assert receipt["mutation_count"] == 0
    assert receipt["submission_count"] == 0


# ==========================================================================
# 20. No generated runs/ artifacts are tracked.
# ==========================================================================


def test_no_tracked_runs_artifacts() -> None:
    result = subprocess.run(
        ["git", "ls-files", "runs/"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
