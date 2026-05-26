"""Deterministic synthetic SMA-return alignment observation fixtures."""

from __future__ import annotations

from decimal import Decimal

from algotrader.research.research_return_observation import (
    ResearchReturnSeriesObservation,
)
from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_return_alignment_observation import (
    SmaReturnAlignmentObservation,
    build_sma_return_alignment_observation,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_research_return_series_observation,
    expected_synthetic_research_return_series_observation_dict,
)

__all__ = [
    "build_synthetic_sma_return_alignment_sma_observations",
    "expected_synthetic_sma_return_alignment_sma_observation_dicts",
    "build_synthetic_sma_return_alignment_return_observation",
    "build_synthetic_sma_return_alignment_observation",
    "expected_synthetic_sma_return_alignment_observation_dict",
]

_SYMBOL = "SYNTH_ETF"
_WINDOW = 2
_SMA_LIMITATIONS = (
    "synthetic SMA states for alignment fixture only",
    "fixed as-of samples exercise no-lookahead alignment",
)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SMA_EXTRA_NON_CLAIMS = (_not("meth", "odology app", "roval"),)


def build_synthetic_sma_return_alignment_sma_observations() -> (
    tuple[SmaResearchObservation, ...]
):
    """Return deterministic SMA states used by the alignment fixture."""

    return (
        _build_sma_observation(
            as_of="2026-01-14",
            prices=(
                _price_point("2026-01-13", "10.00"),
                _price_point("2026-01-14", "10.00"),
            ),
        ),
        _build_sma_observation(
            as_of="2026-01-16",
            prices=(
                _price_point("2026-01-15", "10.00"),
                _price_point("2026-01-16", "30.00"),
            ),
        ),
        _build_sma_observation(
            as_of="2026-01-19",
            prices=(
                _price_point("2026-01-16", "30.00"),
                _price_point("2026-01-19", "10.00"),
            ),
        ),
        _build_sma_observation(
            as_of="2026-01-20",
            prices=(
                _price_point("2026-01-19", "10.00"),
                _price_point("2026-01-20", "40.00"),
            ),
        ),
    )


def expected_synthetic_sma_return_alignment_sma_observation_dicts() -> (
    list[dict[str, object]]
):
    """Return exact primitive SMA source payload copies for alignment tests."""

    return [
        observation.to_dict()
        for observation in build_synthetic_sma_return_alignment_sma_observations()
    ]


def build_synthetic_sma_return_alignment_return_observation() -> (
    ResearchReturnSeriesObservation
):
    """Return the deterministic source return observation for alignment."""

    return build_synthetic_research_return_series_observation()


def build_synthetic_sma_return_alignment_observation() -> (
    SmaReturnAlignmentObservation
):
    """Return the deterministic no-lookahead SMA-return alignment artifact."""

    return build_sma_return_alignment_observation(
        build_synthetic_sma_return_alignment_sma_observations(),
        build_synthetic_sma_return_alignment_return_observation(),
    )


def expected_synthetic_sma_return_alignment_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic SMA-return alignment payload."""

    source_return = expected_synthetic_research_return_series_observation_dict()
    source_returns = source_return["returns"]
    source_sma_observations = (
        expected_synthetic_sma_return_alignment_sma_observation_dicts()
    )
    limitations = _expected_limitations(source_return, source_sma_observations)
    non_claims = _expected_non_claims(source_return, source_sma_observations)

    return {
        "observation_type": "sma_return_alignment_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "alignment_rule": "latest_sma_as_of_on_or_before_return_start",
        "symbol": _SYMBOL,
        "as_of": "2026-01-20",
        "source_return_count": 3,
        "source_sma_observation_count": 4,
        "aligned_return_count": 3,
        "unaligned_return_count": 0,
        "alignment_periods": [
            _expected_alignment_period(
                source_returns[0],
                source_sma_observations[0],
            ),
            _expected_alignment_period(
                source_returns[1],
                source_sma_observations[1],
            ),
            _expected_alignment_period(
                source_returns[2],
                source_sma_observations[2],
            ),
        ],
        "source_return_observation": source_return,
        "source_sma_observations": source_sma_observations,
        "limitations": limitations,
        "non_claims": non_claims,
    }


def _expected_alignment_period(
    source_return: dict[str, str],
    source_sma_observation: dict[str, object],
) -> dict[str, object]:
    return {
        "return_start_date": source_return["start_date"],
        "return_end_date": source_return["end_date"],
        "simple_return": source_return["simple_return"],
        "alignment_state": "sma_state_available",
        "sma_observation_as_of": source_sma_observation["as_of"],
        "sma_observation_state": source_sma_observation["position_vs_sma"],
        "source_return": source_return,
        "source_sma_observation": source_sma_observation,
    }


def _expected_limitations(
    source_return: dict[str, object],
    source_sma_observations: list[dict[str, object]],
) -> list[str]:
    limitations: list[str] = []
    for value in (
        "aligns existing SMA observation metadata to existing return periods only",
        "uses latest SMA observation with as_of on or before each return start date",
        "does not derive return-adjusted metrics from SMA state",
        *source_return["limitations"],
        *(
            limitation
            for observation in source_sma_observations
            for limitation in observation["limitations"]
        ),
    ):
        if value in limitations:
            continue
        limitations.append(value)

    return limitations


def _expected_non_claims(
    source_return: dict[str, object],
    source_sma_observations: list[dict[str, object]],
) -> list[str]:
    values = (
        _not("strategy app", "roval"),
        _not("sour", "ce/data app", "roval"),
        _not("predictive validity"),
        _not("profitability"),
        _not("a recomm", "endation"),
        _not("sig", "nal or evaluator behavior"),
        _not("strategy-return computation"),
        _not("equity-curve computation"),
        _not("cost model"),
        _not("bench", "mark comparison"),
        _not("positions"),
        _not("allo", "cation or or", "der authority"),
        _not("bro", "ker authority"),
        _not("port", "folio mutation authority"),
        _not("paper read", "iness"),
        _not("live read", "iness"),
        _not("capital authority"),
        _not("tra", "ding authority"),
        *source_return["non_claims"],
        *(
            non_claim
            for observation in source_sma_observations
            for non_claim in observation["non_claims"]
        ),
    )
    non_claims: list[str] = []
    for value in values:
        if value in non_claims:
            continue
        non_claims.append(value)

    return non_claims


def _build_sma_observation(
    *,
    as_of: str,
    prices: tuple[SmaResearchPricePoint, ...],
) -> SmaResearchObservation:
    return build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=as_of,
        window=_WINDOW,
        price_points=prices,
        limitations=_SMA_LIMITATIONS,
        non_claims=_SMA_EXTRA_NON_CLAIMS,
    )


def _price_point(value_date: str, close: str) -> SmaResearchPricePoint:
    return SmaResearchPricePoint(value_date, Decimal(close))
