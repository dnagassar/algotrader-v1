from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import ValidationError
from algotrader.orchestration.screener_signal_flow import (
    ScreenerSignalEvaluation,
    evaluate_signals_from_screener,
    ordered_signal_inputs_from_screener,
)
from algotrader.screener import AskMomentumCandidate, AskMomentumResult


NOW = datetime(2026, 5, 4, tzinfo=timezone.utc)


def bar(symbol: str, close: str) -> Bar:
    return Bar(symbol, NOW, close, close, close, close, "1000")


def quote(symbol: str, ask: str) -> Quote:
    return Quote(symbol, NOW, bid=ask, ask=ask)


def test_ordered_signal_inputs_preserve_screener_order() -> None:
    msft_bar = bar("MSFT", "100")
    aapl_bar = bar("AAPL", "50")
    tsla_bar = bar("TSLA", "200")
    msft_quote = quote("MSFT", "105")
    aapl_quote = quote("AAPL", "52")
    tsla_quote = quote("TSLA", "220")
    candidates = (
        AskMomentumCandidate(msft_bar, msft_quote),
        AskMomentumCandidate(aapl_bar, aapl_quote),
        AskMomentumCandidate(tsla_bar, tsla_quote),
    )
    results = (
        AskMomentumResult("TSLA", Decimal("0.10"), Decimal("200"), Decimal("220")),
        AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),
        AskMomentumResult("AAPL", Decimal("0.04"), Decimal("50"), Decimal("52")),
    )

    signal_inputs = ordered_signal_inputs_from_screener(results, candidates)

    assert signal_inputs == (
        (tsla_bar, tsla_quote),
        (msft_bar, msft_quote),
        (aapl_bar, aapl_quote),
    )


def test_ordered_signal_inputs_return_empty_tuple_for_empty_results() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
    )

    assert ordered_signal_inputs_from_screener((), candidates) == ()


def test_ordered_signal_inputs_reject_missing_candidate_symbol() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
    )
    results = (AskMomentumResult("TSLA", Decimal("0.10"), Decimal("200"), Decimal("220")),)

    with pytest.raises(ValidationError, match="missing AskMomentumCandidate.*TSLA"):
        ordered_signal_inputs_from_screener(results, candidates)


def test_ordered_signal_inputs_reject_duplicate_candidate_symbols() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
        AskMomentumCandidate(bar("MSFT", "101"), quote("MSFT", "106")),
    )
    results = (AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),)

    with pytest.raises(ValidationError, match="duplicate AskMomentumCandidate.*MSFT"):
        ordered_signal_inputs_from_screener(results, candidates)


def test_ordered_signal_inputs_reject_duplicate_result_symbols() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
    )
    results = (
        AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),
        AskMomentumResult("MSFT", Decimal("0.04"), Decimal("100"), Decimal("104")),
    )

    with pytest.raises(ValidationError, match="duplicate AskMomentumResult.*MSFT"):
        ordered_signal_inputs_from_screener(results, candidates)


def test_ordered_signal_inputs_reject_invalid_result_items_clearly() -> None:
    with pytest.raises(ValidationError, match="results.*AskMomentumResult"):
        ordered_signal_inputs_from_screener((object(),), ())


def test_ordered_signal_inputs_reject_invalid_candidate_items_clearly() -> None:
    with pytest.raises(ValidationError, match="candidates.*AskMomentumCandidate"):
        ordered_signal_inputs_from_screener((), (object(),))


def test_ordered_signal_inputs_preserve_original_bar_and_quote_objects() -> None:
    previous_bar = bar("MSFT", "100")
    current_quote = quote("MSFT", "105")
    candidates = (AskMomentumCandidate(previous_bar, current_quote),)
    results = (AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),)

    signal_inputs = ordered_signal_inputs_from_screener(results, candidates)

    assert signal_inputs[0][0] is previous_bar
    assert signal_inputs[0][1] is current_quote


def test_evaluate_signals_from_screener_preserves_screener_order() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
        AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
        AskMomentumCandidate(bar("TSLA", "200"), quote("TSLA", "220")),
    )
    results = (
        AskMomentumResult("TSLA", Decimal("0.10"), Decimal("200"), Decimal("220")),
        AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),
        AskMomentumResult("AAPL", Decimal("0.04"), Decimal("50"), Decimal("52")),
    )

    evaluations = evaluate_signals_from_screener(results, candidates)

    assert isinstance(evaluations, tuple)
    assert [evaluation.symbol for evaluation in evaluations] == [
        "TSLA",
        "MSFT",
        "AAPL",
    ]
    assert all(isinstance(evaluation, ScreenerSignalEvaluation) for evaluation in evaluations)
    assert [evaluation.order.symbol for evaluation in evaluations if evaluation.order] == [
        "TSLA",
        "MSFT",
        "AAPL",
    ]
    assert all(evaluation.order.side == OrderSide.BUY for evaluation in evaluations)
    assert all(evaluation.order.order_type == OrderType.MARKET for evaluation in evaluations)


def test_evaluate_signals_from_screener_preserves_mixed_signal_order() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
        AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "50.50")),
        AskMomentumCandidate(bar("TSLA", "200"), quote("TSLA", "220")),
    )
    results = (
        AskMomentumResult("TSLA", Decimal("0.10"), Decimal("200"), Decimal("220")),
        AskMomentumResult("AAPL", Decimal("0.01"), Decimal("50"), Decimal("50.50")),
        AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),
    )

    evaluations = evaluate_signals_from_screener(results, candidates)

    assert [evaluation.symbol for evaluation in evaluations] == [
        "TSLA",
        "AAPL",
        "MSFT",
    ]
    assert evaluations[0].order is not None
    assert evaluations[1].order is None
    assert evaluations[2].order is not None


def test_evaluate_signals_from_screener_returns_empty_tuple_for_empty_results() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
    )

    assert evaluate_signals_from_screener((), candidates) == ()


def test_evaluate_signals_from_screener_keeps_no_signal_symbols() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "101.00")),
    )
    results = (
        AskMomentumResult("MSFT", Decimal("0.01"), Decimal("100"), Decimal("101.00")),
    )

    evaluations = evaluate_signals_from_screener(results, candidates)

    assert evaluations == (
        ScreenerSignalEvaluation(
            symbol="MSFT",
            previous_bar=candidates[0].previous_bar,
            quote=candidates[0].quote,
            order=None,
        ),
    )


def test_evaluate_signals_from_screener_does_not_mutate_inputs() -> None:
    msft_bar = bar("MSFT", "100")
    msft_quote = quote("MSFT", "105")
    aapl_bar = bar("AAPL", "50")
    aapl_quote = quote("AAPL", "50.50")
    candidates = (
        AskMomentumCandidate(msft_bar, msft_quote),
        AskMomentumCandidate(aapl_bar, aapl_quote),
    )
    results = (
        AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),
        AskMomentumResult("AAPL", Decimal("0.01"), Decimal("50"), Decimal("50.50")),
    )
    candidate_snapshot = tuple(candidates)
    result_snapshot = tuple(results)

    evaluations = evaluate_signals_from_screener(results, candidates)

    assert candidates == candidate_snapshot
    assert results == result_snapshot
    assert candidates[0].previous_bar is msft_bar
    assert candidates[0].quote is msft_quote
    assert candidates[1].previous_bar is aapl_bar
    assert candidates[1].quote is aapl_quote
    assert evaluations[0].previous_bar is msft_bar
    assert evaluations[0].quote is msft_quote
    assert evaluations[1].previous_bar is aapl_bar
    assert evaluations[1].quote is aapl_quote


def test_screener_signal_evaluation_is_frozen() -> None:
    evaluation = ScreenerSignalEvaluation(
        symbol="MSFT",
        previous_bar=bar("MSFT", "100"),
        quote=quote("MSFT", "105"),
        order=None,
    )

    with pytest.raises(FrozenInstanceError):
        evaluation.symbol = "AAPL"


def test_evaluate_signals_from_screener_propagates_signal_rule_exceptions() -> None:
    def signal_rule(
        previous_bar: Bar,
        current_quote: Quote,
        threshold: Decimal | str,
        quantity: Decimal | str,
    ) -> ProposedOrder | None:
        raise RuntimeError(f"deliberate signal failure for {current_quote.symbol}")

    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
    )
    results = (
        AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),
    )

    with pytest.raises(RuntimeError, match="deliberate signal failure for MSFT"):
        evaluate_signals_from_screener(
            results,
            candidates,
            signal_rule=signal_rule,
        )


def test_evaluate_signals_from_screener_applies_bridge_validation() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
    )
    results = (
        AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),
        AskMomentumResult("MSFT", Decimal("0.04"), Decimal("100"), Decimal("104")),
    )

    with pytest.raises(ValidationError, match="duplicate AskMomentumResult.*MSFT"):
        evaluate_signals_from_screener(results, candidates)


def test_evaluate_signals_from_screener_needs_no_risk_broker_or_execution() -> None:
    calls: list[tuple[str, Decimal | str, Decimal | str]] = []

    def signal_rule(
        previous_bar: Bar,
        current_quote: Quote,
        threshold: Decimal | str,
        quantity: Decimal | str,
    ) -> ProposedOrder | None:
        calls.append((current_quote.symbol, threshold, quantity))
        return None

    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
    )
    results = (
        AskMomentumResult("MSFT", Decimal("0.05"), Decimal("100"), Decimal("105")),
    )

    evaluations = evaluate_signals_from_screener(
        results,
        candidates,
        threshold=Decimal("0.02"),
        quantity=Decimal("3"),
        signal_rule=signal_rule,
    )

    assert evaluations[0].order is None
    assert calls == [("MSFT", Decimal("0.02"), Decimal("3"))]
