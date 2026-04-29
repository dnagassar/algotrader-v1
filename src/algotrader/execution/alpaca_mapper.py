"""Explicit Alpaca DTO to internal model mappers."""

from __future__ import annotations

from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position

from .alpaca_translator import (
    TranslatedAlpacaAccount,
    TranslatedAlpacaOrderResult,
    TranslatedAlpacaPosition,
)


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
    return BrokerOrderResult(
        accepted=translated.accepted,
        reason="" if translated.accepted else translated.message or translated.status,
        execution=None,
        portfolio=None,
    )


__all__ = [
    "map_translated_account_to_account",
    "map_translated_order_result_to_broker_result",
    "map_translated_position_to_position",
]
