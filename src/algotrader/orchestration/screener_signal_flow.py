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

    candidates_by_symbol = _candidates_by_symbol(candidates)

    signal_inputs: list[SignalInput] = []
    for result in results:
        if not isinstance(result, AskMomentumResult):
            raise ValidationError("result must be an AskMomentumResult.")

        try:
            candidate = candidates_by_symbol[result.symbol]
        except KeyError as exc:
            raise ValidationError(
                f"missing AskMomentumCandidate for symbol {result.symbol}."
            ) from exc

        signal_inputs.append((candidate.previous_bar, candidate.quote))

    return tuple(signal_inputs)


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
            raise ValidationError("candidate must be an AskMomentumCandidate.")

        symbol = candidate.quote.symbol
        if symbol in candidates_by_symbol:
            raise ValidationError(
                f"duplicate AskMomentumCandidate symbol {symbol}."
            )
        candidates_by_symbol[symbol] = candidate

    return candidates_by_symbol
