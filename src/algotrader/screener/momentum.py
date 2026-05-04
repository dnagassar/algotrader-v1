"""Deterministic ask-momentum ranking for synthetic market inputs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

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
    top_n: int | None = None,
    min_score: Decimal | str | None = None,
) -> tuple[AskMomentumResult, ...]:
    """Rank candidates by ask momentum versus the previous close."""

    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Iterable):
        raise ValidationError(
            "candidates must be an iterable of AskMomentumCandidate values."
        )

    top_n_value = _top_n_value(top_n)
    min_score_value = _min_score_value(min_score)

    results = tuple(_score_candidate(candidate) for candidate in candidates)
    ranked = tuple(sorted(results, key=lambda result: (-result.score, result.symbol)))

    if min_score_value is not None:
        ranked = tuple(result for result in ranked if result.score >= min_score_value)
    if top_n_value is not None:
        ranked = ranked[:top_n_value]

    return ranked


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


def _top_n_value(top_n: int | None) -> int | None:
    if top_n is None:
        return None
    if isinstance(top_n, bool) or not isinstance(top_n, int):
        raise ValidationError("top_n must be an integer greater than or equal to 1.")
    if top_n < 1:
        raise ValidationError("top_n must be an integer greater than or equal to 1.")

    return top_n


def _min_score_value(min_score: Decimal | str | None) -> Decimal | None:
    if min_score is None:
        return None
    if isinstance(min_score, Decimal):
        return min_score
    if isinstance(min_score, str):
        try:
            return Decimal(min_score)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(
                "min_score must be a Decimal or decimal string."
            ) from exc

    raise ValidationError("min_score must be a Decimal or decimal string.")
