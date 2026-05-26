"""Deterministic primitive export snapshot for the synthetic SMA return pipeline."""

from __future__ import annotations

from decimal import Decimal

from algotrader.research.research_return_observation import (
    ResearchReturnPricePoint,
    ResearchReturnSeriesObservation,
    build_research_return_series_observation,
)
from algotrader.research.sma_conditional_return_selection_observation import (
    build_sma_conditional_return_selection_observation,
)
from algotrader.research.sma_conditional_return_selection_summary_observation import (
    build_sma_conditional_return_selection_summary_observation,
)
from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_return_alignment_observation import (
    build_sma_return_alignment_observation,
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

__all__ = [
    "export_synthetic_sma_return_research_pipeline_observation_snapshot",
]

_SYMBOL = "SYNTH_ETF"
_AS_OF = "2026-01-20"
_SMA_WINDOW = 2
_SMA_LIMITATIONS = (
    "synthetic SMA states for alignment fixture only",
    "fixed as-of samples exercise no-lookahead alignment",
)
_RETURN_LIMITATIONS = (
    "synthetic broad ETF close series for return mechanics only",
    "fixed close samples with later samples ignored by the builder",
    "candidate-only advisory research metadata with no system connection",
)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_EXTRA_NON_CLAIMS = (
    _not("meth", "odology app", "roval"),
)


def export_synthetic_sma_return_research_pipeline_observation_snapshot() -> (
    dict[str, object]
):
    """Return the canonical synthetic SMA return pipeline primitive payload."""

    return _build_synthetic_sma_return_research_pipeline_observation().to_dict()


def _build_synthetic_sma_return_research_pipeline_observation() -> (
    SmaReturnResearchPipelineObservation
):
    alignment = build_sma_return_alignment_observation(
        _build_sma_observations(),
        _build_return_observation(),
    )
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


def _build_sma_observations() -> tuple[SmaResearchObservation, ...]:
    return (
        _build_sma_observation(
            as_of="2026-01-14",
            prices=(
                _sma_price_point("2026-01-13", "10.00"),
                _sma_price_point("2026-01-14", "10.00"),
            ),
        ),
        _build_sma_observation(
            as_of="2026-01-16",
            prices=(
                _sma_price_point("2026-01-15", "10.00"),
                _sma_price_point("2026-01-16", "30.00"),
            ),
        ),
        _build_sma_observation(
            as_of="2026-01-19",
            prices=(
                _sma_price_point("2026-01-16", "30.00"),
                _sma_price_point("2026-01-19", "10.00"),
            ),
        ),
        _build_sma_observation(
            as_of="2026-01-20",
            prices=(
                _sma_price_point("2026-01-19", "10.00"),
                _sma_price_point("2026-01-20", "40.00"),
            ),
        ),
    )


def _build_sma_observation(
    *,
    as_of: str,
    prices: tuple[SmaResearchPricePoint, ...],
) -> SmaResearchObservation:
    return build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=as_of,
        window=_SMA_WINDOW,
        price_points=prices,
        limitations=_SMA_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def _build_return_observation() -> ResearchReturnSeriesObservation:
    return build_research_return_series_observation(
        symbol=_SYMBOL,
        as_of=_AS_OF,
        price_points=(
            _return_price_point("2026-01-15", "100.00"),
            _return_price_point("2026-01-16", "105.00"),
            _return_price_point("2026-01-19", "94.50"),
            _return_price_point("2026-01-20", "94.50"),
            _return_price_point("2026-01-21", "120.00"),
        ),
        limitations=_RETURN_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def _sma_price_point(
    value_date: str,
    close: str,
) -> SmaResearchPricePoint:
    return SmaResearchPricePoint(value_date, Decimal(close))


def _return_price_point(
    value_date: str,
    close: str,
) -> ResearchReturnPricePoint:
    return ResearchReturnPricePoint(value_date, Decimal(close))
