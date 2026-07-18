from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_bounded_probe_safety import (
    CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT,
    CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS,
    CryptoBoundedProbeObservation,
    CryptoBoundedProbeSafetyStore,
    build_crypto_bounded_probe_safety_policy,
    evaluate_crypto_bounded_probe_safety,
)


NOW = datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc)
SHA_A = "a" * 64
SHA_B = "b" * 64
MODULE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "algotrader"
    / "execution"
    / "crypto_bounded_probe_safety.py"
)


def _initialized_store(
    tmp_path: Path,
    *,
    symbol: str = "BTCUSD",
) -> CryptoBoundedProbeSafetyStore:
    store = CryptoBoundedProbeSafetyStore(tmp_path / f"{symbol}.sqlite3")
    store.initialize(selected_symbol=symbol, as_of=NOW)
    return store


def _enabled_state(
    tmp_path: Path,
    *,
    symbol: str = "BTCUSD",
):
    store = _initialized_store(tmp_path, symbol=symbol)
    state = store.record_operator_control(
        entry_enabled=True,
        authorization_fingerprint=SHA_A,
        as_of=NOW,
    )
    return store, state


def _observation(
    *,
    symbol: str = "BTCUSD",
    action: str = "entry",
    as_of: datetime = NOW,
    **overrides: object,
) -> CryptoBoundedProbeObservation:
    values: dict[str, object] = {
        "symbol": symbol,
        "action": action,
        "as_of": as_of,
        "broker_snapshot_as_of": as_of,
        "capability_valid_until": as_of + timedelta(hours=1),
        "market_data_as_of": as_of,
        "requested_notional_usd": Decimal("10") if action == "entry" else 0,
        "requested_exit_quantity": Decimal("1") if action == "exit" else 0,
        "principal_at_risk_usd": 0,
        "available_cash_usd": 10,
        "position_quantity": Decimal("1") if action == "exit" else 0,
        "position_count": 1 if action == "exit" else 0,
        "open_order_count": 1 if action == "cancel" else 0,
        "entry_attempt_count": 0,
        "exit_attempt_count": 0,
        "cancel_attempt_count": 0,
        "replacement_attempt_count": 0,
        "loss_context_complete": True,
        "cumulative_net_pnl_usd": 0,
        "observed_order_fingerprint": SHA_A if action == "cancel" else "",
        "cancel_target_fingerprint": SHA_A if action == "cancel" else "",
        "account_trading_blocked": False,
        "margin_used": False,
        "broker_ambiguity": False,
        "unexpected_symbol_exposure": False,
    }
    values.update(overrides)
    return CryptoBoundedProbeObservation(**values)  # type: ignore[arg-type]


def test_policy_is_exact_candidate_deferred_and_non_authorizing() -> None:
    policy = build_crypto_bounded_probe_safety_policy()

    assert policy["policy_fingerprint"] == (
        "c0abbc047f7bdf01f19d46e06d3824acd980016b4bd992d78dd4994db6d2c407"
    )
    assert policy["policy_fingerprint"] == (
        CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
    )
    assert policy["supported_symbols"] == ["BTCUSD", "ETHUSD", "SOLUSD"]
    assert policy["default_paused"] is True
    assert policy["loss_halt_restart_latched"] is True
    assert policy["automatic_loss_halt_reset_allowed"] is False
    assert policy["maximum_notional_usd"] == "10"
    assert policy["minimum_notional_usd"] == "1"
    assert policy["time_in_force"] == "gtc"
    assert policy["loss_halt_usd"] == "2"
    assert policy["broker_mutation_authorized"] is False
    assert policy["live_authorized"] is False


@pytest.mark.parametrize("symbol", CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS)
def test_store_initializes_paused_and_replays_exact_state(
    tmp_path: Path,
    symbol: str,
) -> None:
    store = _initialized_store(tmp_path, symbol=symbol)
    first = store.load()
    replay = CryptoBoundedProbeSafetyStore(store.path).initialize(
        selected_symbol=symbol,
        as_of=NOW + timedelta(minutes=1),
    )

    assert first == replay
    assert replay.selected_symbol == symbol
    assert replay.entry_enabled is False
    assert replay.loss_halt_latched is False
    assert replay.maximum_observed_loss_usd == 0
    assert replay.entry_attempt_count == 0
    assert replay.exit_attempt_count == 0
    assert replay.cancel_attempt_count == 0
    assert replay.revision == 0
    assert replay.state_fingerprint


def test_store_rejects_cross_symbol_reinitialization(tmp_path: Path) -> None:
    store = _initialized_store(tmp_path)

    with pytest.raises(ValidationError, match="selected symbol mismatch"):
        store.initialize(selected_symbol="ETHUSD", as_of=NOW)


def test_default_pause_blocks_entry_and_grants_no_authority(tmp_path: Path) -> None:
    state = _initialized_store(tmp_path).load()

    verdict = evaluate_crypto_bounded_probe_safety(state, _observation())

    assert verdict["classification"] == "blocked_by_local_safety_policy"
    assert "operator_control_paused" in verdict["blockers"]
    assert verdict["entry_admitted"] is False
    assert verdict["paper_submit_authorized"] is False
    assert verdict["paper_mutation_authorized"] is False
    assert verdict["live_authorized"] is False


def test_exact_boundary_entry_can_pass_local_policy_without_authority(
    tmp_path: Path,
) -> None:
    _, state = _enabled_state(tmp_path)

    verdict = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(requested_notional_usd="10"),
    )

    assert verdict["classification"] == "admitted_by_local_safety_policy"
    assert verdict["entry_admitted"] is True
    assert verdict["claim_recorded"] is False
    assert verdict["blockers"] == []
    assert verdict["paper_submit_authorized"] is False
    assert verdict["broker_mutation_authorized"] is False


@pytest.mark.parametrize(
    ("overrides", "blocker"),
    (
        ({"requested_notional_usd": "10.00000001"}, "entry_notional_out_of_bounds"),
        ({"requested_notional_usd": "0.99999999"}, "entry_notional_out_of_bounds"),
        ({"available_cash_usd": "9.99"}, "insufficient_cash"),
        ({"account_trading_blocked": True}, "account_trading_blocked"),
        ({"margin_used": True}, "margin_not_allowed"),
        (
            {"requested_notional_usd": "6", "principal_at_risk_usd": "5"},
            "principal_at_risk_cap_exceeded",
        ),
        ({"position_count": 1}, "entry_requires_flat_no_open_orders"),
        ({"open_order_count": 1}, "entry_requires_flat_no_open_orders"),
        ({"entry_attempt_count": 1}, "attempt_state_mismatch"),
        ({"replacement_attempt_count": 1}, "replacement_not_allowed"),
        ({"broker_ambiguity": True}, "broker_ambiguity"),
        ({"unexpected_symbol_exposure": True}, "cross_symbol_exposure"),
    ),
)
def test_entry_envelope_fails_closed(
    tmp_path: Path,
    overrides: dict[str, object],
    blocker: str,
) -> None:
    _, state = _enabled_state(tmp_path)

    verdict = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(**overrides),
    )

    assert verdict["local_safety_admitted"] is False
    assert blocker in verdict["blockers"]


@pytest.mark.parametrize(
    ("overrides", "blocker"),
    (
        (
            {"market_data_as_of": NOW - timedelta(hours=2, microseconds=1)},
            "market_data_stale",
        ),
        (
            {"market_data_as_of": NOW + timedelta(microseconds=1)},
            "market_data_from_future",
        ),
        (
            {
                "broker_snapshot_as_of": NOW
                - timedelta(minutes=5, microseconds=1)
            },
            "broker_snapshot_stale",
        ),
        (
            {"broker_snapshot_as_of": NOW + timedelta(microseconds=1)},
            "broker_snapshot_from_future",
        ),
        (
            {"capability_valid_until": NOW - timedelta(microseconds=1)},
            "capability_expired",
        ),
        ({"market_data_as_of": None}, "market_data_missing"),
    ),
)
def test_entry_time_and_freshness_edges_fail_closed(
    tmp_path: Path,
    overrides: dict[str, object],
    blocker: str,
) -> None:
    _, state = _enabled_state(tmp_path)

    verdict = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(**overrides),
    )

    assert blocker in verdict["blockers"]


def test_probe_duration_boundary_is_exact(tmp_path: Path) -> None:
    _, state = _enabled_state(tmp_path)
    at_boundary = NOW + timedelta(hours=168)
    after_boundary = at_boundary + timedelta(microseconds=1)

    passing = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(
            as_of=at_boundary,
            broker_snapshot_as_of=at_boundary,
            market_data_as_of=at_boundary,
            capability_valid_until=at_boundary,
        ),
    )
    blocked = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(
            as_of=after_boundary,
            broker_snapshot_as_of=after_boundary,
            market_data_as_of=after_boundary,
            capability_valid_until=after_boundary,
        ),
    )

    assert passing["entry_admitted"] is True
    assert "probe_duration_expired" in blocked["blockers"]


def test_loss_boundary_latches_pauses_and_survives_restart(tmp_path: Path) -> None:
    store, _ = _enabled_state(tmp_path)
    latched = store.record_loss_observation(
        cumulative_net_pnl_usd="-2",
        loss_basis_fingerprint=SHA_B,
        as_of=NOW + timedelta(minutes=1),
    )
    replay = CryptoBoundedProbeSafetyStore(store.path).load()

    assert latched == replay
    assert replay.loss_halt_latched is True
    assert replay.entry_enabled is False
    with pytest.raises(ValidationError, match="cannot enable entry"):
        store.record_operator_control(
            entry_enabled=True,
            authorization_fingerprint=SHA_A,
            as_of=NOW + timedelta(minutes=2),
        )

    recovered_pnl = store.record_loss_observation(
        cumulative_net_pnl_usd="1",
        loss_basis_fingerprint=SHA_B,
        as_of=NOW + timedelta(minutes=3),
    )
    assert recovered_pnl.loss_halt_latched is True
    assert recovered_pnl.entry_enabled is False
    assert recovered_pnl.maximum_observed_loss_usd == 2


def test_loss_below_boundary_does_not_latch(tmp_path: Path) -> None:
    store, _ = _enabled_state(tmp_path)

    state = store.record_loss_observation(
        cumulative_net_pnl_usd="-1.99999999",
        loss_basis_fingerprint=SHA_B,
        as_of=NOW + timedelta(minutes=1),
    )

    assert state.loss_halt_latched is False
    assert state.entry_enabled is True
    assert state.maximum_observed_loss_usd == Decimal("1.99999999")


def test_entry_evaluation_and_attempt_claim_are_atomic_and_persistent(
    tmp_path: Path,
) -> None:
    store, _ = _enabled_state(tmp_path)

    claimed = store.evaluate_and_claim(
        _observation(),
        claim_fingerprint=SHA_B,
    )
    replay = CryptoBoundedProbeSafetyStore(store.path).load()

    assert claimed["verdict"]["claim_recorded"] is True
    assert claimed["verdict"]["local_safety_admitted"] is True
    assert claimed["verdict"]["paper_submit_authorized"] is False
    assert replay.entry_attempt_count == 1
    assert replay.last_action_fingerprint == SHA_B
    assert claimed["state"] == replay.canonical()

    blocked = CryptoBoundedProbeSafetyStore(store.path).evaluate_and_claim(
        _observation(entry_attempt_count=1),
        claim_fingerprint=SHA_A,
    )

    assert blocked["verdict"]["claim_recorded"] is False
    assert "entry_attempt_budget_exhausted" in blocked["verdict"]["blockers"]
    assert store.load().revision == replay.revision


@pytest.mark.parametrize(
    ("action", "attempt_field", "budget_blocker"),
    (
        ("cancel", "cancel_attempt_count", "cancel_attempt_budget_exhausted"),
        ("exit", "exit_attempt_count", "exit_attempt_budget_exhausted"),
    ),
)
def test_risk_reducing_claim_budget_survives_restart(
    tmp_path: Path,
    action: str,
    attempt_field: str,
    budget_blocker: str,
) -> None:
    store = _initialized_store(tmp_path)

    first = store.evaluate_and_claim(
        _observation(action=action),
        claim_fingerprint=SHA_B,
    )
    replay_store = CryptoBoundedProbeSafetyStore(store.path)
    replay = replay_store.load()

    assert first["verdict"]["claim_recorded"] is True
    assert first["verdict"]["risk_reducing_action_admitted"] is True
    assert getattr(replay, attempt_field) == 1

    second = replay_store.evaluate_and_claim(
        _observation(action=action, **{attempt_field: 1}),
        claim_fingerprint=SHA_A,
    )

    assert second["verdict"]["claim_recorded"] is False
    assert budget_blocker in second["verdict"]["blockers"]


def test_concurrent_entry_claims_admit_exactly_one_attempt(
    tmp_path: Path,
) -> None:
    store, _ = _enabled_state(tmp_path)

    def claim(fingerprint: str) -> dict[str, object]:
        return CryptoBoundedProbeSafetyStore(store.path).evaluate_and_claim(
            _observation(),
            claim_fingerprint=fingerprint,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, (SHA_B, "c" * 64)))

    recorded = [
        result
        for result in results
        if result["verdict"]["claim_recorded"] is True
    ]
    blocked = [
        result
        for result in results
        if result["verdict"]["claim_recorded"] is False
    ]

    assert len(recorded) == 1
    assert len(blocked) == 1
    assert store.load().entry_attempt_count == 1
    assert "attempt_state_mismatch" in blocked[0]["verdict"]["blockers"]


@pytest.mark.parametrize("action", ("cancel", "exit"))
def test_risk_reducing_actions_remain_locally_admissible_while_halted(
    tmp_path: Path,
    action: str,
) -> None:
    store, _ = _enabled_state(tmp_path)
    state = store.record_loss_observation(
        cumulative_net_pnl_usd="-2",
        loss_basis_fingerprint=SHA_B,
        as_of=NOW + timedelta(minutes=1),
    )
    observed_at = NOW + timedelta(days=10)

    verdict = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(
            action=action,
            as_of=observed_at,
            broker_snapshot_as_of=observed_at,
            capability_valid_until=NOW,
            market_data_as_of=None,
            cumulative_net_pnl_usd="-2",
        ),
    )

    assert verdict["risk_reducing_action_admitted"] is True
    assert verdict["entry_admitted"] is False
    assert verdict["paper_cancel_authorized"] is False
    assert verdict["paper_exit_authorized"] is False


@pytest.mark.parametrize(
    ("action", "overrides", "blocker"),
    (
        ("cancel", {"open_order_count": 0}, "cancel_requires_exactly_one_open_order"),
        (
            "cancel",
            {"cancel_target_fingerprint": SHA_B},
            "cancel_target_not_exactly_observed",
        ),
        ("cancel", {"cancel_attempt_count": 1}, "attempt_state_mismatch"),
        ("exit", {"position_count": 0}, "exit_requires_exactly_one_position"),
        (
            "exit",
            {"requested_exit_quantity": "0.5"},
            "exit_requires_exact_full_long_position",
        ),
        ("exit", {"exit_attempt_count": 1}, "attempt_state_mismatch"),
    ),
)
def test_risk_reducing_attempt_budgets_are_exact(
    tmp_path: Path,
    action: str,
    overrides: dict[str, object],
    blocker: str,
) -> None:
    state = _initialized_store(tmp_path).load()

    verdict = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(action=action, **overrides),
    )

    assert blocker in verdict["blockers"]


def test_loss_context_and_state_binding_are_required(tmp_path: Path) -> None:
    _, state = _enabled_state(tmp_path)

    missing = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(loss_context_complete=False),
    )
    drifted = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(cumulative_net_pnl_usd="0.01"),
    )

    assert "loss_context_missing" in missing["blockers"]
    assert "loss_state_mismatch" in drifted["blockers"]


def test_cross_symbol_observation_is_blocked(tmp_path: Path) -> None:
    _, state = _enabled_state(tmp_path, symbol="BTCUSD")

    verdict = evaluate_crypto_bounded_probe_safety(
        state,
        _observation(symbol="ETHUSD"),
    )

    assert "selected_symbol_mismatch" in verdict["blockers"]


def test_store_time_cannot_regress(tmp_path: Path) -> None:
    store = _initialized_store(tmp_path)

    with pytest.raises(ValidationError, match="time cannot regress"):
        store.record_loss_observation(
            cumulative_net_pnl_usd=0,
            loss_basis_fingerprint=SHA_B,
            as_of=NOW - timedelta(microseconds=1),
        )


def test_corrupt_or_tampered_store_fails_closed(tmp_path: Path) -> None:
    corrupt_path = tmp_path / "corrupt.sqlite3"
    corrupt_path.write_bytes(b"not sqlite")
    with pytest.raises(ValidationError, match="unreadable"):
        CryptoBoundedProbeSafetyStore(corrupt_path).load()

    store = _initialized_store(tmp_path)
    connection = sqlite3.connect(store.path)
    connection.execute(
        "UPDATE bounded_probe_state SET state_fingerprint = ? WHERE singleton = 1",
        (SHA_A,),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        store.load()


def test_concurrent_loss_updates_are_serialized_without_lost_revision(
    tmp_path: Path,
) -> None:
    store, _ = _enabled_state(tmp_path)

    def update(pnl: str) -> int:
        return CryptoBoundedProbeSafetyStore(store.path).record_loss_observation(
            cumulative_net_pnl_usd=pnl,
            loss_basis_fingerprint=SHA_B,
            as_of=NOW + timedelta(minutes=1),
        ).revision

    with ThreadPoolExecutor(max_workers=2) as pool:
        revisions = sorted(pool.map(update, ("-0.25", "-0.50")))

    assert revisions == [2, 3]
    assert store.load().revision == 3


@pytest.mark.parametrize(
    "path",
    ("https://example.test/state.sqlite3", r"\\server\share\state.sqlite3", ":memory:"),
)
def test_store_rejects_nonlocal_or_nondurable_paths(path: str) -> None:
    with pytest.raises(ValidationError, match="local filesystem|durable file"):
        CryptoBoundedProbeSafetyStore(path)


def test_module_has_no_broker_network_credential_or_order_construction() -> None:
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
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not any(
        name.startswith(
            (
                "alpaca",
                "httpx",
                "requests",
                "socket",
                "urllib",
            )
        )
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
