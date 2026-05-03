from datetime import datetime, timezone

from algotrader.core.types import Quote
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.local_broker import LocalBroker
from algotrader.execution.reconciler import reconcile_portfolio
from algotrader.portfolio.state import Account, PortfolioState, Position
from tests.fakes.alpaca import FakeAlpacaClient


NOW = datetime(2026, 4, 26, tzinfo=timezone.utc)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100", ask="100.10")


def portfolio(cash: str, positions=()) -> PortfolioState:
    return PortfolioState(account=Account(cash), positions=tuple(positions))


def mismatch_kinds(report) -> set[str]:
    return {mismatch.kind for mismatch in report.mismatches}


def test_matching_expected_portfolio_reconciles() -> None:
    expected = portfolio("1000", (Position("MSFT", "2", "90"),))
    broker = LocalBroker(expected)

    report = reconcile_portfolio(expected, broker)

    assert report.ok is True
    assert report.mismatches == ()


def test_cash_mismatch_fails_clearly() -> None:
    expected = portfolio("1000")
    broker = LocalBroker(portfolio("999"))

    report = reconcile_portfolio(expected, broker)

    assert report.ok is False
    assert mismatch_kinds(report) == {"cash_mismatch"}
    assert report.mismatches[0].expected == "1000 USD"
    assert report.mismatches[0].actual == "999 USD"


def test_account_currency_mismatch_fails_clearly() -> None:
    expected = PortfolioState(account=Account("1000", currency="USD"))
    broker = LocalBroker(PortfolioState(account=Account("1000", currency="EUR")))

    report = reconcile_portfolio(expected, broker)

    assert report.ok is False
    assert mismatch_kinds(report) == {"cash_mismatch"}
    assert report.mismatches[0].expected == "1000 USD"
    assert report.mismatches[0].actual == "1000 EUR"


def test_missing_broker_position_fails_clearly() -> None:
    expected = portfolio("1000", (Position("MSFT", "2", "90"),))
    broker = LocalBroker(portfolio("1000"))

    report = reconcile_portfolio(expected, broker)

    assert report.ok is False
    assert mismatch_kinds(report) == {"missing_position"}
    assert report.mismatches[0].symbol == "MSFT"


def test_unexpected_broker_position_fails_clearly() -> None:
    expected = portfolio("1000")
    broker = LocalBroker(portfolio("1000", (Position("MSFT", "2", "90"),)))

    report = reconcile_portfolio(expected, broker)

    assert report.ok is False
    assert mismatch_kinds(report) == {"unexpected_position"}
    assert report.mismatches[0].symbol == "MSFT"


def test_fake_alpaca_broker_reconciles_through_adapter_path() -> None:
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))
    expected = portfolio("999")

    report = reconcile_portfolio(expected, broker)

    assert fake_client.calls == ["get_account", "get_positions"]
    assert "submit_order" not in fake_client.calls
    assert report.ok is False
    assert mismatch_kinds(report) == {"cash_mismatch", "unexpected_position"}


def test_fake_alpaca_broker_matching_state_reconciles() -> None:
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))
    expected = portfolio("100000", (Position("MSFT", "3", "100.10"),))

    report = reconcile_portfolio(expected, broker)

    assert fake_client.calls == ["get_account", "get_positions"]
    assert "submit_order" not in fake_client.calls
    assert report.ok is True
    assert report.mismatches == ()


def test_quantity_mismatch_fails_clearly() -> None:
    expected = portfolio("1000", (Position("MSFT", "2", "90"),))
    broker = LocalBroker(portfolio("1000", (Position("MSFT", "1", "90"),)))

    report = reconcile_portfolio(expected, broker)

    assert report.ok is False
    assert mismatch_kinds(report) == {"quantity_mismatch"}
    assert report.mismatches[0].expected == "2"
    assert report.mismatches[0].actual == "1"


def test_valuation_mismatch_is_reported_when_quotes_are_supplied() -> None:
    expected = portfolio("1000", (Position("MSFT", "2", "90"),))
    broker = LocalBroker(portfolio("999", (Position("MSFT", "2", "95"),)))

    report = reconcile_portfolio(expected, broker, {"MSFT": quote()})

    assert report.ok is False
    assert "valuation_mismatch" in mismatch_kinds(report)
    assert "unrealized_pnl_mismatch" in mismatch_kinds(report)
    assert report.expected_valuation is not None
    assert report.broker_valuation is not None
