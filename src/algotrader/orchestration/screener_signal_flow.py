"""Pure bridge from screener results to signal-ready market inputs."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from algotrader.core.types import Bar, ProposedOrder, Quote
from algotrader.errors import ValidationError
from algotrader.screener import AskMomentumCandidate, AskMomentumResult
from algotrader.signals.simple_rule import generate_momentum_buy_order

SignalInput = tuple[Bar, Quote]
SignalRule = Callable[
    [Bar, Quote, Decimal | str, Decimal | str],
    ProposedOrder | None,
]

__all__ = [
    "ScreenerSignalEvaluation",
    "SignalInput",
    "SignalRule",
    "evaluate_signals_from_screener",
    "ordered_signal_inputs_from_screener",
]


@dataclass(frozen=True, slots=True)
class ScreenerSignalEvaluation:
    symbol: str
    previous_bar: Bar
    quote: Quote
    order: ProposedOrder | None


def ordered_signal_inputs_from_screener(
    results: Iterable[AskMomentumResult],
    candidates: Iterable[AskMomentumCandidate] | Mapping[str, AskMomentumCandidate],
) -> tuple[SignalInput, ...]:
    """Return ``(Bar, Quote)`` pairs in ranked screener-result order."""

    result_values = _validated_results(results)
    candidates_by_symbol = _candidates_by_symbol(candidates)

    signal_inputs: list[SignalInput] = []
    for result in result_values:
        try:
            candidate = candidates_by_symbol[result.symbol]
        except KeyError as exc:
            raise ValidationError(
                f"missing AskMomentumCandidate for symbol {result.symbol}."
            ) from exc

        signal_inputs.append((candidate.previous_bar, candidate.quote))

    return tuple(signal_inputs)


def evaluate_signals_from_screener(
    results: Iterable[AskMomentumResult],
    candidates: Iterable[AskMomentumCandidate] | Mapping[str, AskMomentumCandidate],
    threshold: Decimal | str = Decimal("0.01"),
    quantity: Decimal | str = Decimal("1"),
    signal_rule: SignalRule = generate_momentum_buy_order,
) -> tuple[ScreenerSignalEvaluation, ...]:
    """Evaluate pure signal outputs in screener order without trade execution.

    Returned ``ProposedOrder`` values are proposed signal outputs only. They are
    not risk-approved, submitted, or executed.
    """

    evaluations: list[ScreenerSignalEvaluation] = []
    for previous_bar, quote in ordered_signal_inputs_from_screener(
        results,
        candidates,
    ):
        order = signal_rule(previous_bar, quote, threshold, quantity)
        evaluations.append(
            ScreenerSignalEvaluation(
                symbol=quote.symbol,
                previous_bar=previous_bar,
                quote=quote,
                order=order,
            )
        )

    return tuple(evaluations)


def _validated_results(
    results: Iterable[AskMomentumResult],
) -> tuple[AskMomentumResult, ...]:
    if isinstance(results, (str, bytes)) or not isinstance(results, Iterable):
        raise ValidationError(
            "results must be an iterable of AskMomentumResult values."
        )

    seen_symbols: set[str] = set()
    result_values: list[AskMomentumResult] = []
    for result in results:
        if not isinstance(result, AskMomentumResult):
            raise ValidationError("results must contain AskMomentumResult values.")

        if result.symbol in seen_symbols:
            raise ValidationError(
                f"duplicate AskMomentumResult symbol {result.symbol}."
            )
        seen_symbols.add(result.symbol)
        result_values.append(result)

    return tuple(result_values)


def _candidates_by_symbol(
    candidates: Iterable[AskMomentumCandidate] | Mapping[str, AskMomentumCandidate],
) -> dict[str, AskMomentumCandidate]:
    if isinstance(candidates, Mapping):
        candidate_values = candidates.values()
    elif isinstance(candidates, (str, bytes)) or not isinstance(candidates, Iterable):
        raise ValidationError(
            "candidates must be an iterable or mapping of AskMomentumCandidate values."
        )
    else:
        candidate_values = candidates

    candidates_by_symbol: dict[str, AskMomentumCandidate] = {}
    for candidate in candidate_values:
        if not isinstance(candidate, AskMomentumCandidate):
            raise ValidationError(
                "candidates must contain AskMomentumCandidate values."
            )

        symbol = candidate.quote.symbol
        if symbol in candidates_by_symbol:
            raise ValidationError(
                f"duplicate AskMomentumCandidate symbol {symbol}."
            )
        candidates_by_symbol[symbol] = candidate

    return candidates_by_symbol
