from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.strategy_sleeve_ledger import (
    SqliteStrategySleeveLedger,
)
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
)


NOW = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)


def test_pristine_ledger_contains_two_zero_quantity_sleeves(tmp_path) -> None:
    ledger = SqliteStrategySleeveLedger(tmp_path / "sleeves.sqlite3")

    snapshot = ledger.snapshot(SMA_TRAINING_WHEEL_STRATEGY_ID)

    assert snapshot.generation == 0
    assert snapshot.active_quantity == Decimal("0")
    assert snapshot.total_quantity == Decimal("0")
    assert snapshot.pending_intent_count == 0
    assert dict(snapshot.sleeves) == {
        SMA_TRAINING_WHEEL_STRATEGY_ID: Decimal("0"),
        SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID: Decimal("0"),
    }


def test_explicit_adoption_assigns_existing_position_to_one_sleeve(tmp_path) -> None:
    ledger = SqliteStrategySleeveLedger(tmp_path / "sleeves.sqlite3")

    snapshot = ledger.adopt_existing_position(
        strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
        broker_quantity="0.041",
        occurred_at=NOW,
    )

    assert snapshot.generation == 1
    assert snapshot.active_quantity == Decimal("0.041")
    assert snapshot.total_quantity == Decimal("0.041")
    with pytest.raises(ValidationError, match="pristine zero ledger"):
        ledger.adopt_existing_position(
            strategy_id=SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
            broker_quantity="0.01",
            occurred_at=NOW,
        )


def test_buy_fill_and_strategy_owned_sell_update_only_selected_sleeve(
    tmp_path,
) -> None:
    ledger = SqliteStrategySleeveLedger(tmp_path / "sleeves.sqlite3")
    buy = ledger.reserve_intent(
        client_order_id="rsi-buy-1",
        strategy_id=SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
        side="buy",
        requested_quantity=None,
        requested_notional="25.00",
        expected_quantity_before="0",
        occurred_at=NOW,
        max_orders_per_session=2,
    )

    assert buy.pending is True
    ledger.reconcile_intent(
        "rsi-buy-1",
        terminal_status="filled",
        filled_quantity="0.04",
        occurred_at=NOW,
    )
    after_buy = ledger.snapshot(SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID)
    assert after_buy.active_quantity == Decimal("0.04")
    assert after_buy.total_quantity == Decimal("0.04")

    ledger.reserve_intent(
        client_order_id="rsi-close-1",
        strategy_id=SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
        side="sell",
        requested_quantity="0.04",
        requested_notional=None,
        expected_quantity_before="0.04",
        occurred_at=NOW + timedelta(minutes=1),
        max_orders_per_session=2,
    )
    ledger.reconcile_intent(
        "rsi-close-1",
        terminal_status="filled",
        filled_quantity="0.04",
        occurred_at=NOW + timedelta(minutes=1),
    )
    after_close = ledger.snapshot(SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID)

    assert after_close.active_quantity == Decimal("0")
    assert after_close.total_quantity == Decimal("0")
    assert after_close.generation == 2


def test_strategy_cannot_sell_quantity_owned_by_other_sleeve(tmp_path) -> None:
    ledger = SqliteStrategySleeveLedger(tmp_path / "sleeves.sqlite3")
    ledger.adopt_existing_position(
        strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
        broker_quantity="0.05",
        occurred_at=NOW,
    )

    with pytest.raises(ValidationError, match="sell exceeds owned quantity"):
        ledger.reserve_intent(
            client_order_id="rsi-cross-close",
            strategy_id=SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
            side="sell",
            requested_quantity="0.05",
            requested_notional=None,
            expected_quantity_before="0",
            occurred_at=NOW,
            max_orders_per_session=2,
        )


def test_pending_intent_and_two_order_session_cap_fail_closed(tmp_path) -> None:
    ledger = SqliteStrategySleeveLedger(tmp_path / "sleeves.sqlite3")
    ledger.reserve_intent(
        client_order_id="sma-buy",
        strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
        side="buy",
        requested_quantity=None,
        requested_notional="25.00",
        expected_quantity_before="0",
        occurred_at=NOW,
        max_orders_per_session=2,
    )
    with pytest.raises(ValidationError, match="pending intent"):
        ledger.reserve_intent(
            client_order_id="rsi-buy",
            strategy_id=SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
            side="buy",
            requested_quantity=None,
            requested_notional="25.00",
            expected_quantity_before="0",
            occurred_at=NOW,
            max_orders_per_session=2,
        )
    ledger.reconcile_intent(
        "sma-buy",
        terminal_status="rejected",
        filled_quantity="0",
        occurred_at=NOW,
    )
    ledger.reserve_intent(
        client_order_id="rsi-buy",
        strategy_id=SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
        side="buy",
        requested_quantity=None,
        requested_notional="25.00",
        expected_quantity_before="0",
        occurred_at=NOW,
        max_orders_per_session=2,
    )
    ledger.reconcile_intent(
        "rsi-buy",
        terminal_status="rejected",
        filled_quantity="0",
        occurred_at=NOW,
    )

    with pytest.raises(ValidationError, match="session order cap exceeded"):
        ledger.reserve_intent(
            client_order_id="third-order",
            strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
            side="buy",
            requested_quantity=None,
            requested_notional="25.00",
            expected_quantity_before="0",
            occurred_at=NOW,
            max_orders_per_session=2,
        )


def test_reconciliation_is_idempotent_but_conflicting_replay_blocks(
    tmp_path,
) -> None:
    ledger = SqliteStrategySleeveLedger(tmp_path / "sleeves.sqlite3")
    ledger.reserve_intent(
        client_order_id="sma-buy",
        strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
        side="buy",
        requested_quantity=None,
        requested_notional="25",
        expected_quantity_before="0",
        occurred_at=NOW,
        max_orders_per_session=2,
    )
    first = ledger.reconcile_intent(
        "sma-buy",
        terminal_status="filled",
        filled_quantity="0.04",
        occurred_at=NOW,
    )
    replay = ledger.reconcile_intent(
        "sma-buy",
        terminal_status="filled",
        filled_quantity="0.04",
        occurred_at=NOW,
    )

    assert first == replay
    assert ledger.snapshot(SMA_TRAINING_WHEEL_STRATEGY_ID).total_quantity == (
        Decimal("0.04")
    )
    with pytest.raises(ValidationError, match="conflicts with stored result"):
        ledger.reconcile_intent(
            "sma-buy",
            terminal_status="filled",
            filled_quantity="0.05",
            occurred_at=NOW,
        )


def test_terminal_filled_status_requires_positive_quantity(tmp_path) -> None:
    ledger = SqliteStrategySleeveLedger(tmp_path / "sleeves.sqlite3")
    ledger.reserve_intent(
        client_order_id="sma-impossible-fill",
        strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
        side="buy",
        requested_quantity=None,
        requested_notional="25",
        expected_quantity_before="0",
        occurred_at=NOW,
        max_orders_per_session=2,
    )

    with pytest.raises(ValidationError, match="requires positive quantity"):
        ledger.reconcile_intent(
            "sma-impossible-fill",
            terminal_status="filled",
            filled_quantity="0",
            occurred_at=NOW,
        )
    assert ledger.pending_intents()[0].client_order_id == "sma-impossible-fill"
