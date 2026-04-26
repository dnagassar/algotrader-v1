"""Small risk state/result models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.portfolio.state import RiskState


@dataclass(frozen=True, slots=True)
class RiskVerdict:
    allowed: bool
    reason: str = ""
    detail: str = ""
    order_notional: Decimal | None = None

    @classmethod
    def allow(cls, order_notional: Decimal) -> "RiskVerdict":
        return cls(allowed=True, order_notional=order_notional)

    @classmethod
    def reject(
        cls,
        reason: str,
        detail: str = "",
        order_notional: Decimal | None = None,
    ) -> "RiskVerdict":
        return cls(
            allowed=False,
            reason=reason,
            detail=detail,
            order_notional=order_notional,
        )


__all__ = ["RiskState", "RiskVerdict"]
