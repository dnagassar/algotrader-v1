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
    __slots__ = (
        "client_order_id",
        "filled_average_price",
        "filled_quantity",
        "normalized_status",
        "order_id",
        "quantity",
        "raw_reason",
        "raw_status",
    )

    def __new__(
        cls,
        value: str,
        *,
        client_order_id: str = "",
        filled_average_price: str = "",
        filled_quantity: str = "",
        normalized_status: str,
        order_id: str = "",
        quantity: str = "",
        raw_reason: str,
        raw_status: str,
    ):
        reason = str.__new__(cls, value)
        reason.client_order_id = client_order_id
        reason.filled_average_price = filled_average_price
        reason.filled_quantity = filled_quantity
        reason.normalized_status = normalized_status
        reason.order_id = order_id
        reason.quantity = quantity
        reason.raw_reason = raw_reason
        reason.raw_status = raw_status
        return reason


def broker_order_result_receipt_metadata(
    result: BrokerOrderResult,
) -> dict[str, str]:
    reason = result.reason
    return {
        "client_order_id": str(getattr(reason, "client_order_id", "") or ""),
        "filled_average_price": str(
            getattr(reason, "filled_average_price", "") or ""
        ),
        "filled_quantity": str(getattr(reason, "filled_quantity", "") or ""),
        "normalized_status": str(getattr(reason, "normalized_status", "") or ""),
        "order_id": str(getattr(reason, "order_id", "") or ""),
        "quantity": str(getattr(reason, "quantity", "") or ""),
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
        client_order_id=translated.client_order_id,
        filled_average_price=_optional_decimal_text(
            translated.filled_average_price
        ),
        filled_quantity=_optional_decimal_text(translated.filled_quantity),
        normalized_status=translated.status,
        order_id=translated.order_id,
        quantity=_optional_decimal_text(translated.quantity),
        raw_reason=translated.raw_reason or "",
        raw_status=translated.raw_status,
    )


def _optional_decimal_text(value) -> str:  # noqa: ANN001
    return "" if value is None else str(value)


__all__ = [
    "AlpacaOrderReason",
    "AlpacaOrderReceiptExecution",
    "broker_order_result_receipt_metadata",
    "map_translated_account_to_account",
    "map_translated_order_result_to_broker_result",
    "map_translated_position_to_position",
]
