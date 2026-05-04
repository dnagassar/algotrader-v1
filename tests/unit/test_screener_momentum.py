from datetime import datetime, timezone
from decimal import Decimal

import pytest

import algotrader.screener as screener
from algotrader.core.types import Bar, Quote
from algotrader.errors import ValidationError
from algotrader.screener import (
    AskMomentumCandidate,
    AskMomentumResult,
    rank_by_ask_momentum,
)


NOW = datetime(2026, 5, 4, tzinfo=timezone.utc)


def bar(symbol: str, close: str) -> Bar:
    return Bar(symbol, NOW, close, close, close, close, "1000")


def quote(symbol: str, ask: str) -> Quote:
    return Quote(symbol, NOW, bid=ask, ask=ask)


def test_rank_by_ask_momentum_orders_highest_score_first() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
            AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
            AskMomentumCandidate(bar("TSLA", "200"), quote("TSLA", "220")),
        )
    )

    assert isinstance(results, tuple)
    assert [result.symbol for result in results] == ["TSLA", "MSFT", "AAPL"]
    assert [result.score for result in results] == [
        Decimal("0.1"),
        Decimal("0.05"),
        Decimal("0.04"),
    ]
    assert results[0] == AskMomentumResult(
        symbol="TSLA",
        score=Decimal("0.1"),
        previous_close=Decimal("200"),
        ask=Decimal("220"),
    )


def test_rank_by_ask_momentum_breaks_score_ties_by_symbol() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "200"), quote("MSFT", "202")),
            AskMomentumCandidate(bar("AAPL", "100"), quote("AAPL", "101")),
        )
    )

    assert [result.symbol for result in results] == ["AAPL", "MSFT"]
    assert results[0].score == results[1].score == Decimal("0.01")


def test_rank_by_ask_momentum_handles_negative_scores() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
            AskMomentumCandidate(bar("AAPL", "100"), quote("AAPL", "95")),
        )
    )

    assert [result.symbol for result in results] == ["MSFT", "AAPL"]
    assert results[0].score == Decimal("0.05")
    assert results[1].score == Decimal("-0.05")


def test_rank_by_ask_momentum_handles_zero_score() -> None:
    results = rank_by_ask_momentum(
        (AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "100")),)
    )

    assert len(results) == 1
    assert results[0].score == Decimal("0")


def test_rank_by_ask_momentum_handles_single_candidate() -> None:
    results = rank_by_ask_momentum(
        (AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),)
    )

    assert len(results) == 1
    assert results[0].symbol == "MSFT"
    assert results[0].score == Decimal("0.05")


def test_rank_by_ask_momentum_returns_empty_tuple_for_empty_input() -> None:
    assert rank_by_ask_momentum(()) == ()


def test_candidate_rejects_mismatched_bar_and_quote_symbols() -> None:
    with pytest.raises(ValidationError, match="symbols must match"):
        AskMomentumCandidate(bar("MSFT", "100"), quote("AAPL", "101"))


def test_ranker_rejects_invalid_candidate_inputs_clearly() -> None:
    with pytest.raises(ValidationError, match="AskMomentumCandidate"):
        rank_by_ask_momentum((object(),))

    with pytest.raises(ValidationError, match="close must be greater than zero"):
        AskMomentumCandidate(_unsafe_bar_with_close("MSFT", "0"), quote("MSFT", "1"))


def test_rank_by_ask_momentum_rejects_string_input() -> None:
    with pytest.raises(ValidationError, match="AskMomentumCandidate"):
        rank_by_ask_momentum("MSFT")


def test_rank_by_ask_momentum_rejects_non_iterable_input() -> None:
    with pytest.raises(ValidationError):
        rank_by_ask_momentum(42)


def test_screener_package_exports_public_api() -> None:
    assert screener.AskMomentumCandidate is AskMomentumCandidate
    assert screener.AskMomentumResult is AskMomentumResult
    assert screener.rank_by_ask_momentum is rank_by_ask_momentum
    assert screener.__all__ == [
        "AskMomentumCandidate",
        "AskMomentumResult",
        "rank_by_ask_momentum",
    ]


def _unsafe_bar_with_close(symbol: str, close: str) -> Bar:
    unsafe_bar = object.__new__(Bar)
    object.__setattr__(unsafe_bar, "symbol", symbol)
    object.__setattr__(unsafe_bar, "timestamp", NOW)
    object.__setattr__(unsafe_bar, "open", Decimal("1"))
    object.__setattr__(unsafe_bar, "high", Decimal("1"))
    object.__setattr__(unsafe_bar, "low", Decimal("1"))
    object.__setattr__(unsafe_bar, "close", Decimal(close))
    object.__setattr__(unsafe_bar, "volume", Decimal("1000"))
    return unsafe_bar
