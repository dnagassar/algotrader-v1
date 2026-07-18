"""Configuration for deterministic pre-trade risk checks."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.core.validation import decimal_value
from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class RiskConfig:
    max_order_notional: Decimal = Decimal("10000")
    allow_short: bool = False
    allow_fractional_shares: bool = False
    max_positions: int | None = None
    cash_reserve: Decimal = Decimal("0")
    buying_power_reserve: Decimal = Decimal("0")
    max_gross_exposure: Decimal | None = None
    max_symbol_exposure: Decimal | None = None
    max_daily_loss: Decimal | None = None
    max_drawdown: Decimal | None = None
    max_quote_age_seconds: int | None = None
    max_spread_bps: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_order_notional",
            decimal_value(self.max_order_notional, "max_order_notional"),
        )
        if self.max_order_notional <= 0:
            raise ValidationError("max_order_notional must be greater than zero.")

        if self.max_positions is not None and self.max_positions <= 0:
            raise ValidationError("max_positions must be greater than zero.")

        for field_name in ("cash_reserve", "buying_power_reserve"):
            value = decimal_value(getattr(self, field_name), field_name)
            if value < 0:
                raise ValidationError(f"{field_name} must be non-negative.")
            object.__setattr__(self, field_name, value)
        for field_name in (
            "max_gross_exposure",
            "max_symbol_exposure",
            "max_daily_loss",
            "max_drawdown",
            "max_spread_bps",
        ):
            raw = getattr(self, field_name)
            if raw is None:
                continue
            value = decimal_value(raw, field_name)
            if value <= 0:
                raise ValidationError(f"{field_name} must be greater than zero.")
            object.__setattr__(self, field_name, value)
        if self.max_quote_age_seconds is not None:
            if type(self.max_quote_age_seconds) is not int:
                raise ValidationError("max_quote_age_seconds must be an integer.")
            if self.max_quote_age_seconds <= 0:
                raise ValidationError(
                    "max_quote_age_seconds must be greater than zero."
                )
