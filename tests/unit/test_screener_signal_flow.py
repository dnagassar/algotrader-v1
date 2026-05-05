from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Bar, Quote
from algotrader.errors import ValidationError
from algotrader.orchestration.screener_signal_flow import (
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
