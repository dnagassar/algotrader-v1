"""Explicit Alpaca DTO to internal model mappers."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position

from .alpaca_translator import (
    TranslatedAlpacaAccount,
    TranslatedAlpacaOrderResult,
    TranslatedAlpacaPosition,
)


@dataclass(frozen=True, slots=True)
class AlpacaOrderReceiptExecution:
    filled: bool


class AlpacaOrderReason(str):
    __slots__ = ("normalized_status", "raw_reason", "raw_status")

    def __new__(
        cls,
        value: str,
        *,
        normalized_status: str,
        raw_reason: str,
        raw_status: str,
    ):
        reason = str.__new__(cls, value)
        reason.normalized_status = normalized_status
        reason.raw_reason = raw_reason
        reason.raw_status = raw_status
        return reason


def broker_order_result_receipt_metadata(
    result: BrokerOrderResult,
) -> dict[str, str]:
    reason = result.reason
    return {
        "normalized_status": str(getattr(reason, "normalized_status", "") or ""),
        "raw_reason": str(getattr(reason, "raw_reason", "") or ""),
        "raw_status": str(getattr(reason, "raw_status", "") or ""),
    }


def map_translated_account_to_account(
    translated: TranslatedAlpacaAccount,
) -> Account:
    return Account(
        cash=translated.cash,
        currency=translated.currency,
    )


def map_translated_position_to_position(
    translated: TranslatedAlpacaPosition,
) -> Position:
    return Position(
        symbol=translated.symbol,
        quantity=translated.quantity,
        average_price=translated.average_entry_price,
    )


def map_translated_order_result_to_broker_result(
    translated: TranslatedAlpacaOrderResult,
) -> BrokerOrderResult:
    execution = (
        AlpacaOrderReceiptExecution(filled=True) if translated.filled else None
    )
    return BrokerOrderResult(
        accepted=translated.accepted,
        reason=_broker_order_reason(translated),
        execution=execution,
        portfolio=None,
    )


def _broker_order_reason(translated: TranslatedAlpacaOrderResult) -> AlpacaOrderReason:
    value = translated.raw_reason or translated.message or translated.raw_status
    if translated.accepted:
        value = ""

    return AlpacaOrderReason(
        value,
        normalized_status=translated.status,
        raw_reason=translated.raw_reason or "",
        raw_status=translated.raw_status,
    )


__all__ = [
    "AlpacaOrderReason",
    "AlpacaOrderReceiptExecution",
    "broker_order_result_receipt_metadata",
    "map_translated_account_to_account",
    "map_translated_order_result_to_broker_result",
    "map_translated_position_to_position",
]
