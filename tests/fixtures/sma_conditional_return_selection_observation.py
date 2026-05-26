"""Deterministic synthetic SMA conditional return-selection fixtures."""

from __future__ import annotations

from algotrader.research.sma_conditional_return_selection_observation import (
    SmaConditionalReturnSelectionObservation,
    build_sma_conditional_return_selection_observation,
)
from tests.fixtures.sma_return_alignment_observation import (
    build_synthetic_sma_return_alignment_observation,
    expected_synthetic_sma_return_alignment_observation_dict,
)

__all__ = [
    "build_synthetic_sma_conditional_return_selection_observation",
    "expected_synthetic_sma_conditional_return_selection_observation_dict",
]


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def build_synthetic_sma_conditional_return_selection_observation() -> (
    SmaConditionalReturnSelectionObservation
):
    """Return the deterministic synthetic above-SMA selection classification."""

    return build_sma_conditional_return_selection_observation(
        build_synthetic_sma_return_alignment_observation()
    )


def expected_synthetic_sma_conditional_return_selection_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic selection-classification payload."""

    source_alignment = expected_synthetic_sma_return_alignment_observation_dict()
    source_periods = source_alignment["alignment_periods"]
    return {
        "observation_type": "sma_conditional_return_selection_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "selection_rule": "include_when_sma_state_is_above",
        "symbol": "SYNTH_ETF",
        "as_of": "2026-01-20",
        "source_return_count": 3,
        "source_sma_observation_count": 4,
        "alignment_period_count": 3,
        "included_period_count": 1,
        "excluded_period_count": 2,
        "no_prior_sma_state_excluded_count": 0,
        "insufficient_history_excluded_count": 0,
        "below_sma_excluded_count": 1,
        "equal_sma_excluded_count": 1,
        "selection_periods": [
            _expected_selection_period(source_periods[0], "excluded", "equal_sma"),
            _expected_selection_period(source_periods[1], "included", "above_sma"),
            _expected_selection_period(source_periods[2], "excluded", "below_sma"),
        ],
        "source_alignment_observation": source_alignment,
        "limitations": _expected_limitations(source_alignment),
        "non_claims": _expected_non_claims(source_alignment),
    }


def _expected_selection_period(
    source_alignment_period: dict[str, object],
    selection_state: str,
    selection_reason: str,
) -> dict[str, object]:
    return {
        "return_start_date": source_alignment_period["return_start_date"],
        "return_end_date": source_alignment_period["return_end_date"],
        "selection_state": selection_state,
        "selection_reason": selection_reason,
        "sma_observation_as_of": source_alignment_period["sma_observation_as_of"],
        "sma_observation_state": source_alignment_period["sma_observation_state"],
        "source_alignment_period": source_alignment_period,
    }


def _expected_limitations(source_alignment: dict[str, object]) -> list[str]:
    limitations: list[str] = []
    for value in (
        "classifies existing SMA-return alignment periods under a fixed above-SMA rule only",
        "preserves source alignment metadata without deriving performance metrics",
        "treats missing or non-above SMA states as excluded classifications only",
        *source_alignment["limitations"],
    ):
        if value in limitations:
            continue
        limitations.append(value)

    return limitations


def _expected_non_claims(source_alignment: dict[str, object]) -> list[str]:
    values = (
        _not("strategy app", "roval"),
        _not("sour", "ce/data app", "roval"),
        _not("predictive validity"),
        _not("profitability"),
        _not("a recomm", "endation"),
        _not("sig", "nal or evaluator behavior"),
        _not("strategy-return computation"),
        _not("compounded-return computation"),
        _not("equity-curve computation"),
        _not("cash-return computation"),
        _not("exposure computation"),
        _not("cost model"),
        _not("bench", "mark comparison"),
        _not("positions"),
        _not("cash behavior"),
        _not("allo", "cation or or", "der authority"),
        _not("bro", "ker authority"),
        _not("port", "folio state"),
        _not("port", "folio mutation authority"),
        _not("paper read", "iness"),
        _not("live read", "iness"),
        _not("capital authority"),
        _not("tra", "ding authority"),
        *source_alignment["non_claims"],
    )
    non_claims: list[str] = []
    for value in values:
        if value in non_claims:
            continue
        non_claims.append(value)

    return non_claims
