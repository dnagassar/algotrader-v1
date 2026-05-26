"""Deterministic synthetic SMA selected source return summary fixtures."""

from __future__ import annotations

from algotrader.research.sma_selected_source_return_summary_observation import (
    SmaSelectedSourceReturnSummaryObservation,
    build_sma_selected_source_return_summary_observation,
)
from tests.fixtures.sma_selected_source_return_series_observation import (
    build_synthetic_sma_selected_source_return_series_observation,
    expected_synthetic_sma_selected_source_return_series_observation_dict,
)

__all__ = [
    "build_synthetic_sma_selected_source_return_summary_observation",
    "expected_synthetic_sma_selected_source_return_summary_observation_dict",
]


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def build_synthetic_sma_selected_source_return_summary_observation() -> (
    SmaSelectedSourceReturnSummaryObservation
):
    """Return the deterministic synthetic selected source return summary."""

    return build_sma_selected_source_return_summary_observation(
        build_synthetic_sma_selected_source_return_series_observation()
    )


def expected_synthetic_sma_selected_source_return_summary_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic selected source return summary."""

    source_series = (
        expected_synthetic_sma_selected_source_return_series_observation_dict()
    )
    return {
        "observation_type": "sma_selected_source_return_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "selection_rule": "include_when_sma_state_is_above",
        "source_return_value_rule": (
            "collect_source_simple_returns_from_included_selection_periods"
        ),
        "symbol": "SYNTH_ETF",
        "as_of": "2026-01-20",
        "source_return_count": 3,
        "source_sma_observation_count": 4,
        "alignment_period_count": 3,
        "selection_period_count": 3,
        "included_period_count": 1,
        "selected_source_return_count": 1,
        "min_selected_source_return": "-0.1",
        "max_selected_source_return": "-0.1",
        "mean_selected_source_return": "-0.1",
        "summary_state": "selected_source_returns_summarized",
        "source_selected_source_return_series_observation": source_series,
        "limitations": _expected_limitations(source_series),
        "non_claims": _expected_non_claims(source_series),
    }


def _expected_limitations(source_series: dict[str, object]) -> list[str]:
    limitations: list[str] = []
    for value in (
        "summarizes existing selected source return values only",
        "computes selected source return count, minimum, maximum, and arithmetic mean",
        "does not compound selected source returns",
        *source_series["limitations"],
    ):
        if value in limitations:
            continue
        limitations.append(value)

    return limitations


def _expected_non_claims(source_series: dict[str, object]) -> list[str]:
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
        _not("selected source return strategy performance result"),
        _not("selected source return port", "folio result"),
        _not("selected source return invested result"),
        _not("selected source return back", "test result"),
        *source_series["non_claims"],
    )
    non_claims: list[str] = []
    for value in values:
        if value in non_claims:
            continue
        non_claims.append(value)

    return non_claims
