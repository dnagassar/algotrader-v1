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


def test_rank_by_ask_momentum_top_n_returns_highest_ranked_results() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
            AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
            AskMomentumCandidate(bar("TSLA", "200"), quote("TSLA", "220")),
        ),
        top_n=2,
    )

    assert [result.symbol for result in results] == ["TSLA", "MSFT"]


def test_rank_by_ask_momentum_top_n_larger_than_population_returns_all() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
            AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
        ),
        top_n=5,
    )

    assert [result.symbol for result in results] == ["MSFT", "AAPL"]


def test_rank_by_ask_momentum_top_n_preserves_tie_ordering() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "200"), quote("MSFT", "202")),
            AskMomentumCandidate(bar("AAPL", "100"), quote("AAPL", "101")),
        ),
        top_n=1,
    )

    assert [result.symbol for result in results] == ["AAPL"]


def test_rank_by_ask_momentum_min_score_filters_below_threshold() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
            AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
            AskMomentumCandidate(bar("TSLA", "200"), quote("TSLA", "220")),
        ),
        min_score=Decimal("0.05"),
    )

    assert [result.symbol for result in results] == ["TSLA", "MSFT"]
    assert all(result.score >= Decimal("0.05") for result in results)


def test_rank_by_ask_momentum_min_score_accepts_string_threshold() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
            AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
            AskMomentumCandidate(bar("TSLA", "200"), quote("TSLA", "220")),
        ),
        min_score="0.05",
    )

    assert [result.symbol for result in results] == ["TSLA", "MSFT"]


def test_rank_by_ask_momentum_top_n_and_min_score_work_together() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
            AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
            AskMomentumCandidate(bar("TSLA", "200"), quote("TSLA", "220")),
        ),
        top_n=1,
        min_score=Decimal("0.04"),
    )

    assert [result.symbol for result in results] == ["TSLA"]


def test_rank_by_ask_momentum_explicit_no_op_filters_match_defaults() -> None:
    candidates = (
        AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
        AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
        AskMomentumCandidate(bar("TSLA", "200"), quote("TSLA", "220")),
    )

    assert rank_by_ask_momentum(
        candidates,
        top_n=None,
        min_score=None,
    ) == rank_by_ask_momentum(candidates)


def test_rank_by_ask_momentum_rejects_bool_min_score_values() -> None:
    for min_score in (True, False):
        with pytest.raises(ValidationError, match="min_score"):
            rank_by_ask_momentum((), min_score=min_score)


def test_rank_by_ask_momentum_min_score_can_filter_all_before_top_n() -> None:
    results = rank_by_ask_momentum(
        (
            AskMomentumCandidate(bar("MSFT", "100"), quote("MSFT", "105")),
            AskMomentumCandidate(bar("AAPL", "50"), quote("AAPL", "52")),
        ),
        top_n=1,
        min_score=Decimal("0.2"),
    )

    assert results == ()


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


@pytest.mark.parametrize("top_n", [0, -1, "2", True])
def test_rank_by_ask_momentum_rejects_invalid_top_n_values_clearly(top_n) -> None:
    with pytest.raises(ValidationError, match="top_n"):
        rank_by_ask_momentum((), top_n=top_n)


@pytest.mark.parametrize("min_score", ["not-a-decimal", 0.1, object()])
def test_rank_by_ask_momentum_rejects_invalid_min_score_values_clearly(
    min_score,
) -> None:
    with pytest.raises(ValidationError, match="min_score"):
        rank_by_ask_momentum((), min_score=min_score)


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
