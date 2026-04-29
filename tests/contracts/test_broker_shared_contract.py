"""Tiny shared broker contract for behavior common to local and fake Alpaca brokers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.execution.local_broker import LocalBroker
from algotrader.portfolio.state import Account, PortfolioState
from algotrader.risk.state import RiskVerdict
from tests.fakes.alpaca import FakeAlpacaClient


NOW = datetime(2026, 4, 28, tzinfo=UTC)
SHARED_ORDER_ID = "shared-contract-order-1"


@dataclass(frozen=True, slots=True)
class BrokerCase:
    broker: Any
    fake_client: FakeAlpacaClient | None = None


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def proposed_order() -> ProposedOrder:
    return ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")


def approved_risk() -> RiskVerdict:
    return RiskVerdict.allow(order_notional=Decimal("100.10"))


def local_broker_case() -> BrokerCase:
    return BrokerCase(
        broker=LocalBroker(PortfolioState(account=Account("1000"))),
    )


def alpaca_broker_case() -> BrokerCase:
    fake_client = FakeAlpacaClient()
    return BrokerCase(
        broker=AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client)),
        fake_client=fake_client,
    )


@pytest.fixture(params=[local_broker_case, alpaca_broker_case], ids=["local", "alpaca"])
def broker_case(request) -> BrokerCase:
    return request.param()


def test_shared_broker_rejects_submission_without_risk_verdict(
    broker_case: BrokerCase,
) -> None:
    result = broker_case.broker.submit_order(proposed_order(), quote())

    assert type(result) is BrokerOrderResult
    assert result.accepted is False
    assert result.reason == "risk_approval_required"
    assert result.execution is None

    if broker_case.fake_client is not None:
        assert broker_case.fake_client.calls == []
        assert broker_case.fake_client.submitted_requests == []


def test_shared_broker_rejects_submission_with_rejected_risk_verdict(
    broker_case: BrokerCase,
) -> None:
    result = broker_case.broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.reject("contract_rejected"),
    )

    assert type(result) is BrokerOrderResult
    assert result.accepted is False
    assert result.reason == "contract_rejected"
    assert result.execution is None

    if broker_case.fake_client is not None:
        assert broker_case.fake_client.calls == []
        assert broker_case.fake_client.submitted_requests == []


def test_shared_broker_accepts_approved_order_as_broker_order_result(
    broker_case: BrokerCase,
) -> None:
    result = broker_case.broker.submit_order(
        proposed_order(),
        quote(),
        approved_risk(),
        order_id=SHARED_ORDER_ID,
    )

    assert type(result) is BrokerOrderResult
    assert result.accepted is True
    assert result.reason == ""

    if broker_case.fake_client is not None:
        assert broker_case.fake_client.calls == ["submit_order"]


def test_shared_broker_uses_provided_deterministic_order_id(
    broker_case: BrokerCase,
) -> None:
    result = broker_case.broker.submit_order(
        proposed_order(),
        quote(),
        approved_risk(),
        order_id=SHARED_ORDER_ID,
    )

    assert result.accepted is True

    if broker_case.fake_client is None:
        assert result.execution is not None
        assert result.execution.ack.order_id == SHARED_ORDER_ID
        assert result.execution.fill is not None
        assert result.execution.fill.order_id == SHARED_ORDER_ID
    else:
        assert broker_case.fake_client.submitted_requests[0].client_order_id == (
            SHARED_ORDER_ID
        )


def test_shared_broker_rejects_duplicate_order_id_without_second_submission(
    broker_case: BrokerCase,
) -> None:
    first = broker_case.broker.submit_order(
        proposed_order(),
        quote(),
        approved_risk(),
        order_id=SHARED_ORDER_ID,
    )
    if broker_case.fake_client is None:
        account_after_first = broker_case.broker.get_account()
        positions_after_first = broker_case.broker.get_positions()

    second = broker_case.broker.submit_order(
        proposed_order(),
        quote(),
        approved_risk(),
        order_id=SHARED_ORDER_ID,
    )

    assert first.accepted is True
    assert type(second) is BrokerOrderResult
    assert second.accepted is False
    assert second.reason == "duplicate_order_id"
    assert second.execution is None

    if broker_case.fake_client is None:
        assert broker_case.broker.get_account() == account_after_first
        assert broker_case.broker.get_positions() == positions_after_first
    else:
        assert broker_case.fake_client.calls == ["submit_order"]
        assert len(broker_case.fake_client.submitted_requests) == 1
