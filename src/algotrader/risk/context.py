"""Observed runtime context for production pre-trade risk checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import decimal_value
from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class RiskContext:
    as_of: datetime
    account_tradable: bool = True
    account_trading_blocked: bool = False
    operator_paused: bool = False
    data_current: bool = True
    market_session_open: bool = True
    buying_power: Decimal | str | None = None
    open_order_notional: Decimal | str = Decimal("0")
    gross_exposure: Decimal | str = Decimal("0")
    symbol_exposure: Decimal | str = Decimal("0")
    equity: Decimal | str | None = None
    start_of_day_equity: Decimal | str | None = None
    high_watermark_equity: Decimal | str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "as_of", require_utc_datetime(self.as_of))
        except (TypeError, ValidationError) as exc:
            raise ValidationError(
                "as_of must be a timezone-aware UTC datetime."
            ) from exc
        for field_name in (
            "account_tradable",
            "account_trading_blocked",
            "operator_paused",
            "data_current",
            "market_session_open",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        for field_name in (
            "open_order_notional",
            "gross_exposure",
            "symbol_exposure",
        ):
            value = decimal_value(getattr(self, field_name), field_name)
            if value < 0:
                raise ValidationError(f"{field_name} must be non-negative.")
            object.__setattr__(self, field_name, value)
        for field_name in (
            "buying_power",
            "equity",
            "start_of_day_equity",
            "high_watermark_equity",
        ):
            raw = getattr(self, field_name)
            if raw is None:
                continue
            value = decimal_value(raw, field_name)
            if value < 0:
                raise ValidationError(f"{field_name} must be non-negative.")
            object.__setattr__(self, field_name, value)


__all__ = ["RiskContext"]
