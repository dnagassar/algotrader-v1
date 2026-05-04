"""Deterministic ask-momentum ranking for synthetic market inputs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from algotrader.core.types import Bar, Quote
from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class AskMomentumCandidate:
    previous_bar: Bar
    quote: Quote

    def __post_init__(self) -> None:
        _validate_bar_and_quote(self.previous_bar, self.quote)


@dataclass(frozen=True, slots=True)
class AskMomentumResult:
    symbol: str
    score: Decimal
    previous_close: Decimal
    ask: Decimal


def rank_by_ask_momentum(
    candidates: Iterable[AskMomentumCandidate],
) -> tuple[AskMomentumResult, ...]:
    """Rank candidates by ask momentum versus the previous close."""

    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Iterable):
        raise ValidationError(
            "candidates must be an iterable of AskMomentumCandidate values."
        )

    results = tuple(_score_candidate(candidate) for candidate in candidates)
    return tuple(sorted(results, key=lambda result: (-result.score, result.symbol)))


def _score_candidate(candidate: AskMomentumCandidate) -> AskMomentumResult:
    if not isinstance(candidate, AskMomentumCandidate):
        raise ValidationError("candidate must be an AskMomentumCandidate.")

    _validate_bar_and_quote(candidate.previous_bar, candidate.quote)
    score = (candidate.quote.ask - candidate.previous_bar.close) / (
        candidate.previous_bar.close
    )

    return AskMomentumResult(
        symbol=candidate.quote.symbol,
        score=score,
        previous_close=candidate.previous_bar.close,
        ask=candidate.quote.ask,
    )


def _validate_bar_and_quote(previous_bar: Bar, quote: Quote) -> None:
    if not isinstance(previous_bar, Bar):
        raise ValidationError("previous_bar must be a Bar.")
    if not isinstance(quote, Quote):
        raise ValidationError("quote must be a Quote.")
    if previous_bar.symbol != quote.symbol:
        raise ValidationError("previous_bar and quote symbols must match.")
    if previous_bar.close <= 0:
        raise ValidationError("previous_bar close must be greater than zero.")
