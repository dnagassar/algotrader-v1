from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.orchestration.screener_signal_flow import ScreenerSignalEvaluation
from algotrader.orchestration.signal_risk_flow import (
    SignalRiskEvaluation,
    evaluate_risk_for_screener_signals,
)
from algotrader.portfolio.state import Account, PortfolioState, Position
from algotrader.risk.config import RiskConfig


NOW = datetime(2026, 5, 5, tzinfo=timezone.utc)


def bar(symbol: str, close: str = "100") -> Bar:
    return Bar(symbol, NOW, close, close, close, close, "1000")


def quote(symbol: str, ask: str = "100.10") -> Quote:
    return Quote(symbol, NOW, bid=ask, ask=ask)


def order(
    symbol: str,
    quantity: str = "1",
    side: OrderSide = OrderSide.BUY,
) -> ProposedOrder:
    return ProposedOrder(symbol, side, OrderType.MARKET, quantity)


def evaluation(
    symbol: str,
    proposed_order: ProposedOrder | None,
    current_quote: Quote | None = None,
) -> ScreenerSignalEvaluation:
    return ScreenerSignalEvaluation(
        symbol=symbol,
        previous_bar=bar(symbol),
        quote=current_quote or quote(symbol),
        order=proposed_order,
    )


def portfolio(cash: str = "1000") -> PortfolioState:
    return PortfolioState(account=Account(cash))


def test_empty_input_returns_empty_tuple() -> None:
    assert evaluate_risk_for_screener_signals((), portfolio()) == ()


def test_no_signal_row_skips_risk_and_keeps_risk_none() -> None:
    risk_config = RiskConfig(max_order_notional="1")
    evaluations = (evaluation("MSFT", None),)

    results = evaluate_risk_for_screener_signals(
        evaluations,
        portfolio("0"),
        risk_config=risk_config,
    )

    assert results == (
        SignalRiskEvaluation(
            symbol="MSFT",
            previous_bar=evaluations[0].previous_bar,
            quote=evaluations[0].quote,
            order=None,
            risk=None,
            status="no_signal",
        ),
    )


def test_single_approved_order_returns_risk_approved() -> None:
    evaluations = (evaluation("MSFT", order("MSFT")),)

    results = evaluate_risk_for_screener_signals(evaluations, portfolio("1000"))

    assert results[0].status == "risk_approved"
    assert results[0].risk is not None
    assert results[0].risk.allowed is True


def test_single_rejected_order_returns_risk_rejected() -> None:
    evaluations = (evaluation("MSFT", order("MSFT")),)

    results = evaluate_risk_for_screener_signals(evaluations, portfolio("50"))

    assert results[0].status == "risk_rejected"
    assert results[0].risk is not None
    assert results[0].risk.allowed is False
    assert results[0].risk.reason == "insufficient_cash"


def test_mixed_batch_preserves_input_order_and_statuses() -> None:
    evaluations = (
        evaluation("TSLA", order("TSLA"), quote("TSLA", "200")),
        evaluation("AAPL", None, quote("AAPL", "50")),
        evaluation("MSFT", order("MSFT"), quote("MSFT", "100")),
    )

    results = evaluate_risk_for_screener_signals(evaluations, portfolio("250"))

    assert [result.symbol for result in results] == ["TSLA", "AAPL", "MSFT"]
    assert [result.status for result in results] == [
        "risk_approved",
        "no_signal",
        "risk_approved",
    ]
    assert results[1].risk is None


def test_same_portfolio_snapshot_is_reused_and_not_mutated() -> None:
    starting_portfolio = PortfolioState(
        account=Account("150"),
        positions=(Position("MSFT", "1", "100"),),
    )
    portfolio_snapshot = starting_portfolio
    evaluations = (
        evaluation("MSFT", order("MSFT"), quote("MSFT", "100")),
        evaluation("AAPL", order("AAPL"), quote("AAPL", "100")),
    )

    results = evaluate_risk_for_screener_signals(evaluations, starting_portfolio)

    assert starting_portfolio == portfolio_snapshot
    assert starting_portfolio.position("AAPL") is None
    assert [result.status for result in results] == [
        "risk_approved",
        "risk_approved",
    ]


def test_output_tuple_and_result_model_are_immutable() -> None:
    results = evaluate_risk_for_screener_signals(
        (evaluation("MSFT", order("MSFT")),),
        portfolio(),
    )

    with pytest.raises(TypeError):
        results[0] = results[0]

    with pytest.raises(FrozenInstanceError):
        results[0].status = "no_signal"


def test_inputs_and_domain_objects_are_not_mutated() -> None:
    previous_bar = bar("MSFT")
    current_quote = quote("MSFT")
    proposed_order = order("MSFT")
    input_evaluation = ScreenerSignalEvaluation(
        symbol="MSFT",
        previous_bar=previous_bar,
        quote=current_quote,
        order=proposed_order,
    )
    input_snapshot = input_evaluation
    order_snapshot = proposed_order

    results = evaluate_risk_for_screener_signals((input_evaluation,), portfolio())

    assert input_evaluation == input_snapshot
    assert input_evaluation.previous_bar is previous_bar
    assert input_evaluation.quote is current_quote
    assert input_evaluation.order is proposed_order
    assert proposed_order == order_snapshot
    assert results[0].previous_bar is previous_bar
    assert results[0].quote is current_quote
    assert results[0].order is proposed_order


def test_mismatched_quote_and_order_symbol_returns_risk_rejected() -> None:
    evaluations = (evaluation("MSFT", order("MSFT"), quote("AAPL")),)

    results = evaluate_risk_for_screener_signals(evaluations, portfolio())

    assert results[0].status == "risk_rejected"
    assert results[0].risk is not None
    assert results[0].risk.allowed is False
    assert results[0].risk.reason == "symbol_mismatch"


def test_risk_engine_fail_closed_verdict_becomes_risk_rejected_row() -> None:
    evaluations = (evaluation("MSFT", order("MSFT")),)

    results = evaluate_risk_for_screener_signals(evaluations, portfolio=None)

    assert results[0].status == "risk_rejected"
    assert results[0].risk is not None
    assert results[0].risk.allowed is False
    assert results[0].risk.reason == "invalid_risk_input"


def test_no_broker_execution_or_trade_flow_object_is_required() -> None:
    evaluations = (evaluation("MSFT", order("MSFT")),)

    results = evaluate_risk_for_screener_signals(evaluations, portfolio())

    assert results[0].status == "risk_approved"
    assert results[0].risk is not None
    assert results[0].risk.order_notional == Decimal("100.10")
