from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
import pytest

from algotrader.execution.etf_sma_cycle import (
    EtfSmaCycleConfig,
    build_etf_sma_cycle_from_offline_inputs,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"


@pytest.fixture(autouse=True)
def enforce_preflight_offline_only() -> None:
    """Ensure that no credentials or paper profiles are present in the environment."""
    assert not os.environ.get("APP_PROFILE") == "paper"
    for var in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        assert var not in os.environ


@pytest.mark.parametrize(
    (
        "row_id",
        "bars_filename",
        "reco_filename",
        "expected_decision",
        "expected_reason",
        "expected_blockers",
        "expected_preview_order",
    ),
    [
        # 1. risk_on where SMA50 > SMA200, flat SPY state, no open orders: expected buy_preview.
        (
            1,
            "spy_daily_bars_200_bullish.csv",
            "reconciliation_state_flat.jsonl",
            "buy_preview",
            "risk_on_no_position",
            [],
            {
                "asset_class": "equity",
                "symbol": "SPY",
                "side": "buy",
                "order_type": "market",
                "time_in_force": "day",
                "notional": "25",
                "preview_only": True,
            },
        ),
        # 2. risk_on with existing SPY long: expected hold/noop.
        (
            2,
            "spy_daily_bars_200_bullish.csv",
            "reconciliation_state_long.jsonl",
            "hold/noop",
            "risk_on_existing_position",
            [],
            None,
        ),
        # 3. risk_off where SMA50 <= SMA200, existing SPY long: expected sell_preview.
        (
            3,
            "spy_daily_bars_200_bearish.csv",
            "reconciliation_state_long.jsonl",
            "sell_preview",
            "risk_off_existing_position",
            [],
            {
                "asset_class": "equity",
                "symbol": "SPY",
                "side": "sell",
                "order_type": "market",
                "time_in_force": "day",
                "quantity": "0.033172072",
                "preview_only": True,
            },
        ),
        # 4. risk_off with flat SPY state: expected hold/noop.
        (
            4,
            "spy_daily_bars_200_bearish.csv",
            "reconciliation_state_flat.jsonl",
            "hold/noop",
            "risk_off_no_position",
            [],
            None,
        ),
        # 5. 199 usable as-of bars: expected insufficient_history.
        (
            5,
            "spy_daily_bars_199.csv",
            "reconciliation_state_flat.jsonl",
            "insufficient_history",
            "sma_insufficient_history",
            [],
            None,
        ),
        # 6. exactly 200 usable as-of bars: expected decision computed and not insufficient_history.
        (
            6,
            "spy_daily_bars_200_bearish.csv",
            "reconciliation_state_flat.jsonl",
            "hold/noop",
            "risk_off_no_position",
            [],
            None,
        ),
        # 7. open SPY order, risk_on, flat SPY state: expected blocked/open_order_present and no second SPY order intent in payload.
        (
            7,
            "spy_daily_bars_200_bullish.csv",
            "reconciliation_state_open_order.jsonl",
            "blocked/open_order_present",
            "open_order_present",
            ["open_order_present"],
            None,
        ),
        # 8. unexpected non-SPY position present: expected blocked.
        (
            8,
            "spy_daily_bars_200_bullish.csv",
            "reconciliation_state_non_spy.jsonl",
            "blocked/unexpected_non_spy_position",
            "unexpected_non_spy_position",
            ["unexpected_non_spy_position"],
            None,
        ),
        # 9. broker/reconciliation state unavailable in paper-facing/offline observation mode: expected blocked or offline_preview_only, and never a submit-shaped payload.
        (
            9,
            "spy_daily_bars_200_bullish.csv",
            "non_existent_reconciliation_state.jsonl",
            "blocked/broker_state_unavailable",
            "broker_state_unavailable",
            ["broker_state_unavailable", "order_reconciliation_unavailable"],
            None,
        ),
    ],
)
def test_etf_sma_cycle_decision_matrix(
    row_id: int,
    bars_filename: str,
    reco_filename: str | None,
    expected_decision: str,
    expected_reason: str,
    expected_blockers: list[str],
    expected_preview_order: dict[str, object] | None,
) -> None:
    """Validate the SPY ETF/SMA cycle-preview decision semantics against the offline implementation."""
    bars_path = FIXTURES_DIR / bars_filename
    assert bars_path.exists(), f"Missing synthetic bars CSV fixture: {bars_path}"

    if reco_filename and reco_filename != "non_existent_reconciliation_state.jsonl":
        reco_path: Path | None = FIXTURES_DIR / reco_filename
        assert reco_path.exists(), f"Missing reconciliation log fixture: {reco_path}"
    else:
        reco_path = FIXTURES_DIR / "non_existent_reconciliation_state.jsonl"

    config = EtfSmaCycleConfig(
        run_id=f"matrix_row_{row_id}",
        symbol="SPY",
        market_data_csv=bars_path,
        order_reconciliation_log=reco_path,
    )

    payload = build_etf_sma_cycle_from_offline_inputs(config)

    # Verify basic assertions
    assert payload["decision"] == expected_decision
    assert payload["decision_reason"] == expected_reason
    assert all(b in payload["blockers"] for b in expected_blockers)
    assert payload["preview_order"] == expected_preview_order

    # Row 10: allowlist invariant (every preview order payload references SPY only)
    preview_order = payload.get("preview_order")
    if preview_order is not None:
        assert preview_order.get("symbol") == "SPY"

    # Verify safety flags remain false
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["live_authorized"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
