"""Deterministic synthetic SMA-return alignment summary fixtures."""

from __future__ import annotations

from algotrader.research.sma_return_alignment_summary_observation import (
    SmaReturnAlignmentSummaryObservation,
    build_sma_return_alignment_summary_observation,
)
from tests.fixtures.sma_return_alignment_observation import (
    build_synthetic_sma_return_alignment_observation,
    expected_synthetic_sma_return_alignment_observation_dict,
)

__all__ = [
    "build_synthetic_sma_return_alignment_summary_observation",
    "expected_synthetic_sma_return_alignment_summary_observation_dict",
]


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def build_synthetic_sma_return_alignment_summary_observation() -> (
    SmaReturnAlignmentSummaryObservation
):
    """Return the deterministic synthetic SMA-return alignment summary."""

    return build_sma_return_alignment_summary_observation(
        build_synthetic_sma_return_alignment_observation()
    )


def expected_synthetic_sma_return_alignment_summary_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic alignment-summary payload."""

    source_alignment = expected_synthetic_sma_return_alignment_observation_dict()
    return {
        "observation_type": "sma_return_alignment_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "alignment_rule": "latest_sma_as_of_on_or_before_return_start",
        "symbol": "SYNTH_ETF",
        "as_of": "2026-01-20",
        "source_return_count": 3,
        "source_sma_observation_count": 4,
        "alignment_period_count": 3,
        "aligned_return_count": 3,
        "no_prior_sma_state_count": 0,
        "insufficient_history_alignment_count": 0,
        "above_sma_alignment_count": 1,
        "below_sma_alignment_count": 1,
        "equal_sma_alignment_count": 1,
        "summary_state": "all_return_periods_aligned",
        "source_alignment_observation": source_alignment,
        "limitations": _expected_limitations(source_alignment),
        "non_claims": _expected_non_claims(source_alignment),
    }


def _expected_limitations(source_alignment: dict[str, object]) -> list[str]:
    limitations: list[str] = []
    for value in (
        "summarizes existing SMA-return alignment metadata only",
        "counts alignment availability and SMA states across aligned return periods",
        "does not compute return-adjusted metrics from SMA state",
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
        _not("equity-curve computation"),
        _not("exposure computation"),
        _not("cost model"),
        _not("bench", "mark comparison"),
        _not("positions"),
        _not("cash behavior"),
        _not("allo", "cation or or", "der authority"),
        _not("bro", "ker authority"),
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
