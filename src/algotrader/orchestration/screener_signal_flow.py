"""Pure bridge from screener results to signal-ready market inputs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from algotrader.core.types import Bar, Quote
from algotrader.errors import ValidationError
from algotrader.screener import AskMomentumCandidate, AskMomentumResult

SignalInput = tuple[Bar, Quote]

__all__ = ["SignalInput", "ordered_signal_inputs_from_screener"]


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
