"""Asset-class policy matrix for guarded paper order probes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


ASSET_CLASS_EQUITY = "equity"
ASSET_CLASS_CRYPTO = "crypto"
ASSET_CLASS_OPTION = "option"
ASSET_CLASS_CHOICES = (
    ASSET_CLASS_EQUITY,
    ASSET_CLASS_CRYPTO,
    ASSET_CLASS_OPTION,
)

PAPER_MARKET_SESSION_NOTE = (
    "Market DAY equity orders submitted after hours may be accepted or queued "
    "by the broker and may not fill until the next regular session."
)
PAPER_ORDER_PROBE_QTY_DISABLED_REASON = (
    "qty_submission_disabled_until_quote_based_cap_is_supported"
)
PAPER_CRYPTO_SESSION_NOTE = (
    "Crypto paper observations are a shared broker-path harness only and do "
    "not prove equity behavior."
)
OPTIONS_SUBMIT_DISABLED_REASON = (
    "options_submit_disabled_until_options_risk_contract_exists"
)


@dataclass(frozen=True)
class PaperOrderPolicy:
    asset_class: str
    symbol_allowlist: tuple[str, ...] | None
    allowed_sizing_modes: tuple[str, ...]
    time_in_force: str
    submit_enabled: bool
    submit_disabled_reason: str
    max_notional_cap: Decimal | None = None
    required_qty: Decimal | None = None
    market_session_note: str = ""

    def allows_symbol(self, symbol: str) -> bool:
        normalized_symbol = symbol.strip().upper()
        if self.symbol_allowlist is None:
            return bool(normalized_symbol)

        return normalized_symbol in self.symbol_allowlist

    def allowlist_detail(self, symbol: str) -> str:
        normalized_symbol = symbol.strip().upper()
        if self.symbol_allowlist is None:
            return f"symbol={normalized_symbol} explicit_contract_symbol"

        return (
            f"symbol={normalized_symbol} "
            f"allowlist={','.join(self.symbol_allowlist)}"
        )

    def sizing_failure_detail(self) -> str:
        if self.asset_class == ASSET_CLASS_CRYPTO:
            return "crypto_notional_required"
        if self.asset_class == ASSET_CLASS_OPTION:
            return "option_qty_1_contract_required"

        return "exactly_one_of_qty_or_notional_required"

    def quantity_detail(self) -> str:
        if self.required_qty is not None:
            return f"qty={self.required_qty}_contract_only"

        return "positive_whole_share_quantity"

    def quantity_failure_detail(self, quantity_error: str) -> str:
        if quantity_error:
            return quantity_error
        if self.required_qty is not None:
            return f"qty_must_equal_{self.required_qty}_contract"

        return "invalid_quantity"

    def notional_cap_detail(self) -> str:
        if self.max_notional_cap is None:
            return "max_notional_not_applicable"

        return f"max_notional_cap={self.max_notional_cap}"


_POLICIES = {
    ASSET_CLASS_EQUITY: PaperOrderPolicy(
        asset_class=ASSET_CLASS_EQUITY,
        symbol_allowlist=("SPY",),
        allowed_sizing_modes=("qty", "notional"),
        max_notional_cap=Decimal("10"),
        time_in_force="day",
        submit_enabled=True,
        submit_disabled_reason="",
        market_session_note=PAPER_MARKET_SESSION_NOTE,
    ),
    ASSET_CLASS_CRYPTO: PaperOrderPolicy(
        asset_class=ASSET_CLASS_CRYPTO,
        symbol_allowlist=("BTCUSD",),
        allowed_sizing_modes=("notional",),
        max_notional_cap=Decimal("5.00"),
        time_in_force="gtc",
        submit_enabled=True,
        submit_disabled_reason="",
        market_session_note=PAPER_CRYPTO_SESSION_NOTE,
    ),
    ASSET_CLASS_OPTION: PaperOrderPolicy(
        asset_class=ASSET_CLASS_OPTION,
        symbol_allowlist=None,
        allowed_sizing_modes=("qty",),
        time_in_force="day",
        submit_enabled=False,
        submit_disabled_reason=OPTIONS_SUBMIT_DISABLED_REASON,
        required_qty=Decimal("1"),
    ),
}


def paper_order_policy_for_asset_class(asset_class: str) -> PaperOrderPolicy:
    normalized_asset_class = asset_class.strip().lower()
    try:
        return _POLICIES[normalized_asset_class]
    except KeyError:
        expected = ", ".join(ASSET_CLASS_CHOICES)
        raise ValueError(
            f"unsupported paper order asset_class: {asset_class!r}; "
            f"expected one of {expected}"
        ) from None


__all__ = [
    "ASSET_CLASS_CHOICES",
    "ASSET_CLASS_CRYPTO",
    "ASSET_CLASS_EQUITY",
    "ASSET_CLASS_OPTION",
    "OPTIONS_SUBMIT_DISABLED_REASON",
    "PAPER_CRYPTO_SESSION_NOTE",
    "PAPER_MARKET_SESSION_NOTE",
    "PAPER_ORDER_PROBE_QTY_DISABLED_REASON",
    "PaperOrderPolicy",
    "paper_order_policy_for_asset_class",
]
