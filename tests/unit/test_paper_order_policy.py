from __future__ import annotations

from decimal import Decimal

import pytest

from algotrader.execution.paper_order_policy import (
    ASSET_CLASS_CHOICES,
    OPTIONS_SUBMIT_DISABLED_REASON,
    PAPER_CLOSE_PREVIEW_RECOMMENDED_ACTION,
    PAPER_CLOSE_PREVIEW_SUBMISSION_DISABLED_REASON,
    PAPER_CRYPTO_BTCUSD_MIN_NOTIONAL,
    PAPER_ORDER_PROBE_QTY_DISABLED_REASON,
    build_btcusd_paper_close_preview_contract,
    paper_order_policy_for_asset_class,
)


def test_policy_matrix_separates_equity_crypto_and_options_lanes() -> None:
    equity = paper_order_policy_for_asset_class("equity")
    crypto = paper_order_policy_for_asset_class("crypto")
    option = paper_order_policy_for_asset_class("option")

    assert ASSET_CLASS_CHOICES == ("equity", "crypto", "option")
    assert equity.symbol_allowlist == ("SPY",)
    assert equity.allowed_sizing_modes == ("qty", "notional")
    assert equity.max_notional_cap == Decimal("10")
    assert equity.time_in_force == "day"
    assert equity.submit_enabled is True
    assert equity.submit_disabled_reason == ""

    assert crypto.symbol_allowlist == ("BTCUSD",)
    assert crypto.allowed_sizing_modes == ("notional",)
    assert crypto.max_notional_cap == Decimal("10.00")
    assert crypto.min_notional == PAPER_CRYPTO_BTCUSD_MIN_NOTIONAL
    assert crypto.min_notional == Decimal("10.00")
    assert crypto.time_in_force == "gtc"
    assert crypto.submit_enabled is True
    assert crypto.submit_disabled_reason == ""
    assert crypto.market_session_note.startswith("Crypto paper observations")

    assert option.symbol_allowlist is None
    assert option.allowed_sizing_modes == ("qty",)
    assert option.required_qty == Decimal("1")
    assert option.submit_enabled is False
    assert option.submit_disabled_reason == OPTIONS_SUBMIT_DISABLED_REASON


def test_policy_normalizes_asset_class_and_symbols() -> None:
    equity = paper_order_policy_for_asset_class(" EQUITY ")
    crypto = paper_order_policy_for_asset_class("crypto")
    option = paper_order_policy_for_asset_class("option")

    assert equity.allows_symbol("spy") is True
    assert equity.allows_symbol("AAPL") is False
    assert crypto.allows_symbol("btcusd") is True
    assert crypto.allows_symbol("ETHUSD") is False
    assert option.allows_symbol("SPY260117C00600000") is True
    assert option.allows_symbol(" ") is False


def test_policy_exposes_deterministic_failure_details() -> None:
    equity = paper_order_policy_for_asset_class("equity")
    crypto = paper_order_policy_for_asset_class("crypto")
    option = paper_order_policy_for_asset_class("option")

    assert equity.quantity_failure_detail("") == "invalid_quantity"
    assert PAPER_ORDER_PROBE_QTY_DISABLED_REASON.endswith(
        "quote_based_cap_is_supported"
    )
    assert equity.quantity_detail("notional") == "positive_whole_share_quantity"
    assert equity.notional_minimum_detail() == "min_notional_not_applicable"
    assert crypto.quantity_detail("notional") == "not_applicable_for_notional"
    assert crypto.notional_minimum_detail() == "min_notional=10.00"
    assert (
        crypto.notional_minimum_failure_detail()
        == "notional_below_crypto_min_notional"
    )
    assert crypto.sizing_failure_detail() == "crypto_notional_required"
    assert option.sizing_failure_detail() == "option_qty_1_contract_required"
    assert option.quantity_failure_detail("") == "qty_must_equal_1_contract"


def test_policy_rejects_unknown_asset_class() -> None:
    with pytest.raises(ValueError, match="unsupported paper order asset_class"):
        paper_order_policy_for_asset_class("futures")


def test_btcusd_close_preview_contract_is_preview_only_and_manual_review() -> None:
    payload = build_btcusd_paper_close_preview_contract(
        observed_position_quantity=Decimal("0.000132386"),
        requested_close_quantity=Decimal("0.000132386"),
        fresh_snapshot_status="read_only_snapshot_completed_for_manual_review",
        recent_order_query_metadata_complete=True,
        source_mutated=False,
        source_submitted=False,
    ).to_payload()

    assert payload["ok"] is True
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["close_order_submitted"] is False
    assert payload["paper_lab_only"] is True
    assert payload["not_live_authorized"] is True
    assert payload["profit_claim"] == "none"
    assert payload["manual_review_required"] is True
    assert payload["asset_class"] == "crypto"
    assert payload["symbol"] == "BTCUSD"
    assert payload["side"] == "sell"
    assert payload["order_type"] == "market"
    assert payload["time_in_force"] == "gtc"
    assert payload["observed_position_quantity"] == "0.000132386"
    assert payload["quantity"] == "0.000132386"
    assert payload["max_quantity"] == "0.000132386"
    assert payload["requested_close_quantity"] == "0.000132386"
    assert payload["remaining_quantity_after_preview"] == "0"
    assert payload["close_quantity_within_observed_position"] is True
    assert payload["no_shorting_gate"] == "passed"
    assert payload["fresh_snapshot_required"] is True
    assert (
        payload["fresh_snapshot_status"]
        == "read_only_snapshot_completed_for_manual_review"
    )
    assert payload["recent_order_query_metadata_complete"] is True
    assert (
        payload["submission_disabled_reason"]
        == PAPER_CLOSE_PREVIEW_SUBMISSION_DISABLED_REASON
    )
    assert (
        payload["recommended_next_operator_action"]
        == PAPER_CLOSE_PREVIEW_RECOMMENDED_ACTION
    )
    assert payload["gates"]["submit_disabled_gate"]["passed"] is True


def test_btcusd_close_preview_contract_blocks_shorting() -> None:
    payload = build_btcusd_paper_close_preview_contract(
        observed_position_quantity=Decimal("0.000132386"),
        requested_close_quantity=Decimal("0.000132387"),
        fresh_snapshot_status="read_only_snapshot_completed_for_manual_review",
        recent_order_query_metadata_complete=True,
        source_mutated=False,
        source_submitted=False,
    ).to_payload()

    assert payload["ok"] is False
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["close_quantity_within_observed_position"] is False
    assert payload["no_shorting_gate"] == "failed"
    assert payload["remaining_quantity_after_preview"] == ""
    assert payload["gates"]["no_shorting_gate"] == {
        "detail": "requested_close_quantity_would_short_BTCUSD",
        "passed": False,
    }
