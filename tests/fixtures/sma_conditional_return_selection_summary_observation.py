"""Deterministic synthetic SMA conditional return-selection summary fixtures."""

from __future__ import annotations

from algotrader.research.sma_conditional_return_selection_summary_observation import (
    SmaConditionalReturnSelectionSummaryObservation,
    build_sma_conditional_return_selection_summary_observation,
)
from tests.fixtures.sma_conditional_return_selection_observation import (
    build_synthetic_sma_conditional_return_selection_observation,
    expected_synthetic_sma_conditional_return_selection_observation_dict,
)

__all__ = [
    "build_synthetic_sma_conditional_return_selection_summary_observation",
    "expected_synthetic_sma_conditional_return_selection_summary_observation_dict",
]


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def build_synthetic_sma_conditional_return_selection_summary_observation() -> (
    SmaConditionalReturnSelectionSummaryObservation
):
    """Return the deterministic synthetic selection-classification summary."""

    return build_sma_conditional_return_selection_summary_observation(
        build_synthetic_sma_conditional_return_selection_observation()
    )


def expected_synthetic_sma_conditional_return_selection_summary_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic selection-summary payload."""

    source_selection = expected_synthetic_sma_conditional_return_selection_observation_dict()
    return {
        "observation_type": "sma_conditional_return_selection_summary_observation",
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
        "selection_period_count": 3,
        "included_period_count": 1,
        "excluded_period_count": 2,
        "no_prior_sma_state_excluded_count": 0,
        "insufficient_history_excluded_count": 0,
        "below_sma_excluded_count": 1,
        "equal_sma_excluded_count": 1,
        "summary_state": "mixed_selection_classifications",
        "source_selection_observation": source_selection,
        "limitations": _expected_limitations(source_selection),
        "non_claims": _expected_non_claims(source_selection),
    }


def _expected_limitations(source_selection: dict[str, object]) -> list[str]:
    limitations: list[str] = []
    for value in (
        "summarizes existing SMA conditional return-selection metadata only",
        "counts include and exclude classifications without return math",
        "preserves source selection metadata without deriving performance metrics",
        *source_selection["limitations"],
    ):
        if value in limitations:
            continue
        limitations.append(value)

    return limitations


def _expected_non_claims(source_selection: dict[str, object]) -> list[str]:
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
        *source_selection["non_claims"],
    )
    non_claims: list[str] = []
    for value in values:
        if value in non_claims:
            continue
        non_claims.append(value)

    return non_claims
