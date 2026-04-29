from decimal import Decimal

from algotrader.execution.alpaca_mapper import (
    map_translated_account_to_account,
    map_translated_order_result_to_broker_result,
    map_translated_position_to_position,
)
from algotrader.execution.alpaca_translator import (
    TranslatedAlpacaAccount,
    TranslatedAlpacaOrderResult,
    TranslatedAlpacaPosition,
)
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position


def test_map_translated_account_to_internal_account():
    account = map_translated_account_to_account(
        TranslatedAlpacaAccount(
            account_id="paper-account-1",
            status="ACTIVE",
            cash=Decimal("100000"),
            buying_power=Decimal("200000"),
            equity=Decimal("100000"),
            currency="usd",
        )
    )

    assert isinstance(account, Account)
    assert account.cash == Decimal("100000")
    assert account.currency == "USD"


def test_map_translated_position_to_internal_position():
    position = map_translated_position_to_position(
        TranslatedAlpacaPosition(
            symbol="msft",
            quantity=Decimal("3"),
            market_value=Decimal("300.30"),
            average_entry_price=Decimal("100.10"),
            side="long",
        )
    )

    assert isinstance(position, Position)
    assert position.symbol == "MSFT"
    assert position.quantity == Decimal("3")
    assert position.average_price == Decimal("100.10")


def test_map_accepted_translated_order_result_to_broker_result():
    result = map_translated_order_result_to_broker_result(
        TranslatedAlpacaOrderResult(
            order_id="broker-order-1",
            client_order_id="deterministic-order-1",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("1"),
            status="accepted",
            accepted=True,
        )
    )

    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is True
    assert result.reason == ""
    assert result.execution is None
    assert result.portfolio is None
    assert result.filled is False


def test_map_rejected_translated_order_result_to_broker_result():
    result = map_translated_order_result_to_broker_result(
        TranslatedAlpacaOrderResult(
            order_id="broker-order-2",
            client_order_id="deterministic-order-2",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("1"),
            status="rejected",
            accepted=False,
            message="insufficient buying power",
        )
    )

    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is False
    assert result.reason == "insufficient buying power"
    assert result.execution is None
    assert result.portfolio is None
    assert result.filled is False
