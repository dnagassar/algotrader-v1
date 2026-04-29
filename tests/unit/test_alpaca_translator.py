from datetime import UTC, datetime
from decimal import Decimal
import inspect
import socket

import pytest

import algotrader.execution.alpaca_translator as alpaca_translator_module
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaOrderSubmissionResponse,
    AlpacaPositionResponse,
)
from algotrader.execution.alpaca_translator import (
    AlpacaTranslationError,
    TranslatedAlpacaAccount,
    TranslatedAlpacaOrderResult,
    TranslatedAlpacaPosition,
    translate_alpaca_account,
    translate_alpaca_order_result,
    translate_alpaca_position,
)


def test_translator_module_has_no_dynamic_model_resolution():
    source = inspect.getsource(alpaca_translator_module)

    assert "_MODEL_MODULES" not in source
    assert "_resolve_model" not in source
    assert "_construct_model" not in source
    assert "_constructor_kwargs" not in source
    assert "import_module" not in source
    assert "signature(" not in source


def test_translate_valid_fake_account_response_returns_pinned_dto():
    response = AlpacaAccountResponse(
        account_id="paper-account-1",
        status="ACTIVE",
        cash=Decimal("100000"),
        buying_power=Decimal("200000"),
        equity=Decimal("100000"),
    )

    account = translate_alpaca_account(response)

    assert account == TranslatedAlpacaAccount(
        account_id="paper-account-1",
        status="ACTIVE",
        cash=Decimal("100000"),
        buying_power=Decimal("200000"),
        equity=Decimal("100000"),
        currency="USD",
    )


def test_translate_account_missing_or_invalid_fields_fail_clearly():
    with pytest.raises(AlpacaTranslationError, match="cash"):
        translate_alpaca_account(
            {
                "account_id": "paper-account-1",
                "status": "ACTIVE",
                "buying_power": "200000",
                "equity": "100000",
            }
        )

    with pytest.raises(AlpacaTranslationError, match="equity"):
        translate_alpaca_account(
            {
                "account_id": "paper-account-1",
                "status": "ACTIVE",
                "cash": "100000",
                "buying_power": "200000",
                "equity": "not-a-number",
            }
        )


def test_translate_valid_fake_position_response_returns_pinned_dto():
    response = AlpacaPositionResponse(
        symbol="aapl",
        qty=Decimal("5"),
        market_value=Decimal("950"),
        average_entry_price=Decimal("180"),
    )

    position = translate_alpaca_position(response)

    assert position == TranslatedAlpacaPosition(
        symbol="AAPL",
        quantity=Decimal("5"),
        market_value=Decimal("950"),
        average_entry_price=Decimal("180"),
        side="long",
    )


def test_translate_position_missing_or_invalid_fields_fail_clearly():
    with pytest.raises(AlpacaTranslationError, match="symbol"):
        translate_alpaca_position(
            {
                "qty": "5",
                "market_value": "950",
                "average_entry_price": "180",
            }
        )

    with pytest.raises(AlpacaTranslationError, match="qty"):
        translate_alpaca_position(
            {
                "symbol": "AAPL",
                "qty": "not-a-number",
                "market_value": "950",
                "average_entry_price": "180",
            }
        )


def test_translate_valid_fake_order_submission_returns_pinned_dto():
    submitted_at = datetime(2026, 1, 1, tzinfo=UTC)
    response = AlpacaOrderSubmissionResponse(
        order_id="broker-order-1",
        client_order_id="deterministic-order-1",
        symbol="aapl",
        side="buy",
        qty=Decimal("1"),
        status="accepted",
        submitted_at=submitted_at,
    )

    result = translate_alpaca_order_result(response)

    assert result == TranslatedAlpacaOrderResult(
        order_id="broker-order-1",
        client_order_id="deterministic-order-1",
        symbol="AAPL",
        side="buy",
        quantity=Decimal("1"),
        status="accepted",
        accepted=True,
        message=None,
        submitted_at=submitted_at,
    )


def test_translate_rejected_fake_order_response_returns_pinned_dto():
    result = translate_alpaca_order_result(
        {
            "order_id": "broker-order-2",
            "client_order_id": "deterministic-order-2",
            "symbol": "AAPL",
            "side": "buy",
            "qty": "1",
            "status": "rejected",
            "reject_reason": "insufficient buying power",
        }
    )

    assert result == TranslatedAlpacaOrderResult(
        order_id="broker-order-2",
        client_order_id="deterministic-order-2",
        symbol="AAPL",
        side="buy",
        quantity=Decimal("1"),
        status="rejected",
        accepted=False,
        message="insufficient buying power",
        submitted_at=None,
    )


def test_translate_rejected_order_missing_required_fields_fails_clearly():
    with pytest.raises(AlpacaTranslationError, match="symbol"):
        translate_alpaca_order_result(
            {
                "order_id": "broker-order-2",
                "client_order_id": "deterministic-order-2",
                "side": "buy",
                "qty": "1",
                "status": "rejected",
            }
        )


def test_translators_require_no_credentials(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)

    account = translate_alpaca_account(
        {
            "account_id": "paper-account-1",
            "status": "ACTIVE",
            "cash": "100000",
            "buying_power": "200000",
            "equity": "100000",
        }
    )

    assert account.cash == Decimal("100000")


def test_translators_make_no_network_calls(monkeypatch):
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network calls are not allowed in translator tests")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    translate_alpaca_account(
        {
            "account_id": "paper-account-1",
            "status": "ACTIVE",
            "cash": "100000",
            "buying_power": "200000",
            "equity": "100000",
        }
    )
    translate_alpaca_position(
        {
            "symbol": "AAPL",
            "qty": "5",
            "market_value": "950",
            "average_entry_price": "180",
        }
    )
    translate_alpaca_order_result(
        {
            "order_id": "broker-order-1",
            "client_order_id": "deterministic-order-1",
            "symbol": "AAPL",
            "side": "buy",
            "qty": "1",
            "status": "accepted",
        }
    )
