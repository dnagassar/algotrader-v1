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
