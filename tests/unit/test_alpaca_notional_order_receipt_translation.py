from decimal import Decimal
import socket

import pytest

from algotrader.config import AlpacaPaperConfig
from algotrader.execution.alpaca_client import AlpacaOrderRequest
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
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
    assert receipt.raw_status == "filled"
    assert receipt.accepted is True
    assert receipt.filled is True
    assert receipt.quantity is None


@pytest.mark.parametrize(
    ("raw_status", "normalized_status", "accepted", "filled"),
    (
        ("accepted", "accepted", True, False),
        ("new", "new", True, False),
        ("pending_new", "pending_new", True, False),
        ("partially_filled", "partially_filled", True, False),
        ("filled", "filled", True, True),
        ("orderstatus.accepted", "accepted", True, False),
        ("OrderStatus.ACCEPTED", "accepted", True, False),
        ("rejected", "rejected", False, False),
        ("canceled", "canceled", False, False),
        ("expired", "expired", False, False),
    ),
)
def test_order_status_is_normalized_before_acceptance_decision(
    raw_status: str,
    normalized_status: str,
    accepted: bool,
    filled: bool,
) -> None:
    receipt = translate_alpaca_order_result(
        {
            "order_id": "broker-order-1",
            "client_order_id": "paper-order-probe-notional-1",
            "symbol": "SPY",
            "side": "buy",
            "notional": "5.00",
            "status": raw_status,
        }
    )

    assert receipt.raw_status == raw_status
    assert receipt.status == normalized_status
    assert receipt.accepted is accepted
    assert receipt.filled is filled


def test_order_rejection_preserves_raw_reason_for_diagnostics() -> None:
    receipt = translate_alpaca_order_result(
        {
            "order_id": "broker-order-1",
            "client_order_id": "paper-order-probe-notional-1",
            "symbol": "SPY",
            "side": "buy",
            "notional": "5.00",
            "status": "rejected",
            "reject_reason": "insufficient buying power",
        }
    )

    assert receipt.accepted is False
    assert receipt.filled is False
    assert receipt.status == "rejected"
    assert receipt.raw_status == "rejected"
    assert receipt.raw_reason == "insufficient buying power"


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


def test_crypto_notional_receipt_does_not_require_quantity() -> None:
    receipt = translate_alpaca_order_result(
        {
            "order_id": "broker-order-crypto-1",
            "client_order_id": "paper-order-probe-crypto-submit",
            "symbol": "btcusd",
            "side": "buy",
            "notional": "2.00",
            "status": "accepted",
        }
    )

    assert receipt.symbol == "BTCUSD"
    assert receipt.side == "buy"
    assert receipt.quantity is None
    assert receipt.notional == Decimal("2.00")
    assert receipt.status == "accepted"
    assert receipt.raw_status == "accepted"
    assert receipt.accepted is True
    assert receipt.filled is False


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


def test_factory_created_sdk_client_uses_real_market_order_request_shape() -> None:
    fake_sdk_client = _FakeRealSdkTradingClient()
    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="test-api-key",
        alpaca_secret_key="test-secret-key",
        alpaca_paper_base_url="https://paper.example.test",
    )
    client = AlpacaSdkClient(
        config,
        sdk_client_factory=lambda _: fake_sdk_client,
    )

    response = client.submit_order(
        AlpacaOrderRequest(
            client_order_id="paper-order-probe-notional-1",
            symbol="SPY",
            side="buy",
            notional=Decimal("5.00"),
        )
    )

    assert fake_sdk_client.calls == ["submit_order"]
    assert fake_sdk_client.submitted_orders[0].__class__.__name__ == (
        "MarketOrderRequest"
    )
    assert not isinstance(fake_sdk_client.submitted_orders[0], AlpacaOrderRequest)
    assert response["notional"] == "5.0"


class _FakeRealSdkTradingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.submitted_orders: list[object] = []

    def submit_order(self, order_data):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_orders.append(order_data)
        return {
            "id": "broker-order-1",
            "client_order_id": str(order_data.client_order_id),
            "notional": str(order_data.notional),
            "side": str(order_data.side.value),
            "status": "accepted",
            "symbol": str(order_data.symbol),
        }
