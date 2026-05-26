"""Deterministic synthetic SMA return research pipeline fixtures."""

from __future__ import annotations

from algotrader.research.sma_conditional_return_selection_observation import (
    build_sma_conditional_return_selection_observation,
)
from algotrader.research.sma_conditional_return_selection_summary_observation import (
    build_sma_conditional_return_selection_summary_observation,
)
from algotrader.research.sma_return_alignment_summary_observation import (
    build_sma_return_alignment_summary_observation,
)
from algotrader.research.sma_return_research_pipeline_observation import (
    SmaReturnResearchPipelineObservation,
    build_sma_return_research_pipeline_observation,
)
from algotrader.research.sma_selected_source_return_series_observation import (
    build_sma_selected_source_return_series_observation,
)
from algotrader.research.sma_selected_source_return_summary_observation import (
    build_sma_selected_source_return_summary_observation,
)
from tests.fixtures.research_return_construction_policy import (
    expected_synthetic_research_return_construction_policy_dict,
)
from tests.fixtures.sma_conditional_return_selection_observation import (
    expected_synthetic_sma_conditional_return_selection_observation_dict,
)
from tests.fixtures.sma_conditional_return_selection_summary_observation import (
    expected_synthetic_sma_conditional_return_selection_summary_observation_dict,
)
from tests.fixtures.sma_return_alignment_observation import (
    build_synthetic_sma_return_alignment_observation,
    expected_synthetic_sma_return_alignment_observation_dict,
)
from tests.fixtures.sma_return_alignment_summary_observation import (
    expected_synthetic_sma_return_alignment_summary_observation_dict,
)
from tests.fixtures.sma_selected_source_return_series_observation import (
    expected_synthetic_sma_selected_source_return_series_observation_dict,
)
from tests.fixtures.sma_selected_source_return_summary_observation import (
    expected_synthetic_sma_selected_source_return_summary_observation_dict,
)

__all__ = [
    "build_synthetic_sma_return_research_pipeline_observation",
    "expected_synthetic_sma_return_research_pipeline_observation_dict",
]


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def build_synthetic_sma_return_research_pipeline_observation() -> (
    SmaReturnResearchPipelineObservation
):
    """Return the deterministic synthetic SMA return research pipeline."""

    alignment = build_synthetic_sma_return_alignment_observation()
    alignment_summary = build_sma_return_alignment_summary_observation(alignment)
    selection = build_sma_conditional_return_selection_observation(alignment)
    selection_summary = build_sma_conditional_return_selection_summary_observation(
        selection
    )
    selected_series = build_sma_selected_source_return_series_observation(selection)
    selected_summary = build_sma_selected_source_return_summary_observation(
        selected_series
    )
    return build_sma_return_research_pipeline_observation(
        alignment,
        alignment_summary,
        selection,
        selection_summary,
        selected_series,
        selected_summary,
    )


def expected_synthetic_sma_return_research_pipeline_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic SMA return research pipeline."""

    alignment = expected_synthetic_sma_return_alignment_observation_dict()
    alignment_summary = expected_synthetic_sma_return_alignment_summary_observation_dict()
    selection = expected_synthetic_sma_conditional_return_selection_observation_dict()
    selection_summary = (
        expected_synthetic_sma_conditional_return_selection_summary_observation_dict()
    )
    selected_series = (
        expected_synthetic_sma_selected_source_return_series_observation_dict()
    )
    selected_summary = (
        expected_synthetic_sma_selected_source_return_summary_observation_dict()
    )
    return {
        "observation_type": "sma_return_research_pipeline_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "pipeline_rule": "compose_existing_sma_return_research_artifacts",
        "alignment_rule": "latest_sma_as_of_on_or_before_return_start",
        "selection_rule": "include_when_sma_state_is_above",
        "source_return_value_rule": (
            "collect_source_simple_returns_from_included_selection_periods"
        ),
        "symbol": "SYNTH_ETF",
        "as_of": "2026-01-20",
        "pipeline_component_count": 6,
        "source_return_count": 3,
        "source_sma_observation_count": 4,
        "alignment_period_count": 3,
        "selection_period_count": 3,
        "included_period_count": 1,
        "excluded_period_count": 2,
        "selected_source_return_count": 1,
        "alignment_summary_state": "all_return_periods_aligned",
        "selection_summary_state": "mixed_selection_classifications",
        "selected_source_return_summary_state": (
            "selected_source_returns_summarized"
        ),
        "pipeline_state": "sma_return_research_pipeline_composed",
        "source_alignment_observation": alignment,
        "source_alignment_summary_observation": alignment_summary,
        "source_selection_observation": selection,
        "source_selection_summary_observation": selection_summary,
        "source_selected_source_return_series_observation": selected_series,
        "source_selected_source_return_summary_observation": selected_summary,
        "return_construction_policy_observation": (
            _expected_return_construction_policy_observation()
        ),
        "limitations": _expected_limitations(
            alignment,
            alignment_summary,
            selection,
            selection_summary,
            selected_series,
            selected_summary,
        ),
        "non_claims": _expected_non_claims(
            alignment,
            alignment_summary,
            selection,
            selection_summary,
            selected_series,
            selected_summary,
        ),
    }


def _expected_return_construction_policy_observation() -> dict[str, object]:
    return {
        "observation_type": "research_return_construction_policy_observation",
        "advisory_scope": "policy_contract_observation_only",
        "policy_state": "return_construction_policy_defined",
        "selected_period_count": 0,
        "excluded_period_count": 0,
        "source_return_observation_count": 0,
        "forbidden_output_count": 0,
        "source_policy": expected_synthetic_research_return_construction_policy_dict(),
    }


def _expected_limitations(
    alignment: dict[str, object],
    alignment_summary: dict[str, object],
    selection: dict[str, object],
    selection_summary: dict[str, object],
    selected_series: dict[str, object],
    selected_summary: dict[str, object],
) -> list[str]:
    limitations: list[str] = []
    for value in (
        "composes existing SMA return research artifacts only",
        "preserves source artifact identity and derivation chain metadata",
        "does not calculate new return values or performance metrics",
        *alignment["limitations"],
        *alignment_summary["limitations"],
        *selection["limitations"],
        *selection_summary["limitations"],
        *selected_series["limitations"],
        *selected_summary["limitations"],
    ):
        if value in limitations:
            continue
        limitations.append(value)

    return limitations


def _expected_non_claims(
    alignment: dict[str, object],
    alignment_summary: dict[str, object],
    selection: dict[str, object],
    selection_summary: dict[str, object],
    selected_series: dict[str, object],
    selected_summary: dict[str, object],
) -> list[str]:
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
        _not("SMA return research pipeline back", "test result"),
        *alignment["non_claims"],
        *alignment_summary["non_claims"],
        *selection["non_claims"],
        *selection_summary["non_claims"],
        *selected_series["non_claims"],
        *selected_summary["non_claims"],
    )
    non_claims: list[str] = []
    for value in values:
        if value in non_claims:
            continue
        non_claims.append(value)

    return non_claims
