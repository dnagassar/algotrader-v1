from __future__ import annotations

from decimal import Decimal

import pytest

from algotrader.execution.paper_order_policy import (
    ASSET_CLASS_CHOICES,
    CRYPTO_SUBMIT_DISABLED_REASON,
    OPTIONS_SUBMIT_DISABLED_REASON,
    PAPER_ORDER_PROBE_QTY_DISABLED_REASON,
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
    assert crypto.max_notional_cap == Decimal("5")
    assert crypto.time_in_force == "gtc"
    assert crypto.submit_enabled is False
    assert crypto.submit_disabled_reason == CRYPTO_SUBMIT_DISABLED_REASON

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
    assert crypto.sizing_failure_detail() == "crypto_notional_required"
    assert option.sizing_failure_detail() == "option_qty_1_contract_required"
    assert option.quantity_failure_detail("") == "qty_must_equal_1_contract"


def test_policy_rejects_unknown_asset_class() -> None:
    with pytest.raises(ValueError, match="unsupported paper order asset_class"):
        paper_order_policy_for_asset_class("futures")
