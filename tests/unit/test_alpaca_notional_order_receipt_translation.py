from decimal import Decimal
import socket

import pytest

from algotrader.execution.alpaca_translator import (
    AlpacaTranslationError,
    translate_alpaca_order_result,
)


def test_notional_order_response_without_qty_parses_successfully() -> None:
    receipt = translate_alpaca_order_result(
        {
            "id": "broker-order-1",
            "client_order_id": "paper-order-probe-notional-1",
            "symbol": "spy",
            "side": "buy",
            "notional": "5.00",
            "status": "filled",
        }
    )

    assert receipt.order_id == "broker-order-1"
    assert receipt.client_order_id == "paper-order-probe-notional-1"
    assert receipt.symbol == "SPY"
    assert receipt.side == "buy"
    assert receipt.status == "filled"
    assert receipt.accepted is True
    assert receipt.quantity is None


def test_notional_is_preserved_and_empty_qty_stays_optional() -> None:
    receipt = translate_alpaca_order_result(
        {
            "order_id": "broker-order-1",
            "client_order_id": "paper-order-probe-notional-1",
            "symbol": "SPY",
            "side": "buy",
            "qty": "",
            "notional": "5.00",
            "status": "accepted",
        }
    )

    assert receipt.notional == Decimal("5.00")
    assert receipt.quantity is None


def test_qty_order_response_still_parses_as_before() -> None:
    receipt = translate_alpaca_order_result(
        {
            "order_id": "broker-order-2",
            "client_order_id": "deterministic-order-2",
            "symbol": "AAPL",
            "side": "buy",
            "qty": "1",
            "status": "accepted",
        }
    )

    assert receipt.quantity == Decimal("1")
    assert receipt.notional is None
    assert receipt.accepted is True


def test_order_response_without_qty_or_notional_fails_deterministically() -> None:
    with pytest.raises(AlpacaTranslationError) as exc_info:
        translate_alpaca_order_result(
            {
                "order_id": "broker-order-3",
                "client_order_id": "deterministic-order-3",
                "symbol": "AAPL",
                "side": "buy",
                "status": "accepted",
            }
        )

    assert (
        str(exc_info.value)
        == "Missing required field in Alpaca response: qty, quantity, notional."
    )


def test_notional_receipt_translation_is_offline_and_credential_free(
    monkeypatch,
) -> None:
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network calls are not allowed in translator tests")

    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    receipt = translate_alpaca_order_result(
        {
            "order_id": "broker-order-1",
            "client_order_id": "paper-order-probe-notional-1",
            "symbol": "SPY",
            "side": "buy",
            "notional": "5.00",
            "status": "accepted",
        }
    )

    assert receipt.notional == Decimal("5.00")
