from datetime import datetime, timezone
from decimal import Decimal
import json

import pytest

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import ValidationError
from algotrader.execution.ledger import InMemoryLedger, JsonlLedger, LedgerEventType
from algotrader.execution.local_broker import LocalBroker
from algotrader.portfolio.state import Account, PortfolioState
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine


NOW = datetime(2026, 4, 27, tzinfo=timezone.utc)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def portfolio() -> PortfolioState:
    return PortfolioState(account=Account("1000"))


def risk_verdict(order: ProposedOrder, state: PortfolioState):
    return RiskEngine(RiskConfig(max_order_notional="1000")).check(
        order,
        state,
        quote(),
    )


def event_types(ledger: InMemoryLedger) -> list[LedgerEventType]:
    return [event.event_type for event in ledger.list_events()]


def test_appending_events_preserves_order() -> None:
    ledger = InMemoryLedger()

    ledger.append(LedgerEventType.ORDER_SUBMITTED, NOW, order_id="order-1")
    ledger.append(LedgerEventType.ORDER_FILLED, NOW, order_id="order-1")

    assert event_types(ledger) == [
        LedgerEventType.ORDER_SUBMITTED,
        LedgerEventType.ORDER_FILLED,
    ]


def test_filtering_events_by_order_id() -> None:
    ledger = InMemoryLedger()

    ledger.append(LedgerEventType.ORDER_SUBMITTED, NOW, order_id="order-1")
    ledger.append(LedgerEventType.ORDER_SUBMITTED, NOW, order_id="order-2")
    ledger.append(LedgerEventType.ORDER_FILLED, NOW, order_id="order-1")

    events = ledger.by_order_id("order-1")

    assert [event.event_type for event in events] == [
        LedgerEventType.ORDER_SUBMITTED,
        LedgerEventType.ORDER_FILLED,
    ]


def test_local_broker_records_filled_order_events() -> None:
    state = portfolio()
    ledger = InMemoryLedger()
    broker = LocalBroker(state, ledger=ledger)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    result = broker.submit_order(
        order,
        quote(),
        risk_verdict(order, state),
        order_id="order-1",
    )

    assert result.filled is True
    assert event_types(ledger) == [
        LedgerEventType.ORDER_SUBMITTED,
        LedgerEventType.ORDER_FILLED,
        LedgerEventType.PORTFOLIO_UPDATED,
    ]
    assert broker.get_account().cash == Decimal("899.90")


def test_local_broker_records_missing_risk_rejection() -> None:
    ledger = InMemoryLedger()
    broker = LocalBroker(portfolio(), ledger=ledger)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    result = broker.submit_order(order, quote(), order_id="order-1")

    assert result.accepted is False
    assert result.reason == "risk_approval_required"
    assert event_types(ledger) == [
        LedgerEventType.ORDER_SUBMITTED,
        LedgerEventType.ORDER_REJECTED,
    ]
    assert ledger.by_order_id("order-1")[-1].message == "risk_approval_required"


def test_unfilled_limit_order_records_no_fill_without_mutation() -> None:
    state = portfolio()
    ledger = InMemoryLedger()
    broker = LocalBroker(state, ledger=ledger)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.LIMIT, "1", "100.09")

    result = broker.submit_order(
        order,
        quote(),
        risk_verdict(order, state),
        order_id="order-1",
    )

    assert result.accepted is True
    assert result.filled is False
    assert broker.get_account().cash == Decimal("1000")
    assert broker.get_positions() == ()
    assert event_types(ledger) == [
        LedgerEventType.ORDER_SUBMITTED,
        LedgerEventType.ORDER_NOT_FILLED,
    ]


def test_jsonl_ledger_appends_one_line_per_event(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    ledger = JsonlLedger(path)

    ledger.append(LedgerEventType.ORDER_SUBMITTED, NOW, order_id="order-1")
    ledger.append(LedgerEventType.ORDER_FILLED, NOW, order_id="order-1")

    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_jsonl_ledger_reads_events_back_in_order(tmp_path) -> None:
    ledger = JsonlLedger(tmp_path / "events.jsonl")

    ledger.append(LedgerEventType.ORDER_SUBMITTED, NOW, order_id="order-1")
    ledger.append(LedgerEventType.ORDER_NOT_FILLED, NOW, order_id="order-1")

    assert event_types(ledger) == [
        LedgerEventType.ORDER_SUBMITTED,
        LedgerEventType.ORDER_NOT_FILLED,
    ]


def test_jsonl_ledger_filters_by_order_id(tmp_path) -> None:
    ledger = JsonlLedger(tmp_path / "events.jsonl")

    ledger.append(LedgerEventType.ORDER_SUBMITTED, NOW, order_id="order-1")
    ledger.append(LedgerEventType.ORDER_SUBMITTED, NOW, order_id="order-2")
    ledger.append(LedgerEventType.ORDER_FILLED, NOW, order_id="order-1")

    events = ledger.by_order_id("order-1")

    assert [event.event_type for event in events] == [
        LedgerEventType.ORDER_SUBMITTED,
        LedgerEventType.ORDER_FILLED,
    ]


def test_jsonl_ledger_missing_file_returns_no_events(tmp_path) -> None:
    ledger = JsonlLedger(tmp_path / "missing.jsonl")

    assert ledger.list_events() == ()


def test_jsonl_ledger_malformed_line_fails_clearly(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"event_type": "order_submitted"}) + "\n", encoding="utf-8")
    ledger = JsonlLedger(path)

    with pytest.raises(ValidationError, match="Malformed ledger event"):
        ledger.list_events()


def test_local_broker_can_record_to_jsonl_ledger(tmp_path) -> None:
    state = portfolio()
    ledger = JsonlLedger(tmp_path / "events.jsonl")
    broker = LocalBroker(state, ledger=ledger)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    result = broker.submit_order(
        order,
        quote(),
        risk_verdict(order, state),
        order_id="order-1",
    )

    assert result.filled is True
    assert event_types(ledger) == [
        LedgerEventType.ORDER_SUBMITTED,
        LedgerEventType.ORDER_FILLED,
        LedgerEventType.PORTFOLIO_UPDATED,
    ]
