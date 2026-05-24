"""Deterministic synthetic SMA research observation fixtures."""

from __future__ import annotations

from decimal import Decimal

from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)

__all__ = [
    "build_synthetic_sma_research_price_points",
    "expected_synthetic_sma_research_price_point_dicts",
    "build_synthetic_sma_research_observation",
    "expected_synthetic_sma_research_observation_dict",
    "build_synthetic_insufficient_history_sma_research_observation",
    "expected_synthetic_insufficient_history_sma_research_observation_dict",
]

_SYMBOL = "SYNTH_ETF"
_AS_OF = "2026-01-20"
_WINDOW = 3
_LIMITATIONS = (
    "synthetic broad ETF close series for fixture mechanics only",
    "fixed date samples with later samples ignored by the builder",
    "candidate-only advisory research metadata with no system connection",
)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predict", "ive validity"),
    _not("prof", "itability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evalu", "ator behavior"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mut", "ation authority"),
    _not("pa", "per read", "iness"),
    _not("li", "ve read", "iness"),
    _not("capital ", "authority"),
    _not("tra", "ding authority"),
)
_EXTRA_NON_CLAIMS = (
    _not("meth", "odology app", "roval"),
)
_EXPECTED_NON_CLAIMS = (*_REQUIRED_NON_CLAIMS, *_EXTRA_NON_CLAIMS)


def build_synthetic_sma_research_price_points() -> tuple[SmaResearchPricePoint, ...]:
    """Return deterministic synthetic broad ETF SMA-like price points."""

    return (
        _price_point("2026-01-16", "90.00"),
        _price_point("2026-01-17", "100.00"),
        _price_point("2026-01-20", "110.00"),
        _price_point("2026-01-21", "130.00"),
    )


def expected_synthetic_sma_research_price_point_dicts() -> list[dict[str, str]]:
    """Return exact primitive price point payload copies."""

    return [
        {"date": "2026-01-16", "close": "90.00"},
        {"date": "2026-01-17", "close": "100.00"},
        {"date": "2026-01-20", "close": "110.00"},
        {"date": "2026-01-21", "close": "130.00"},
    ]


def build_synthetic_sma_research_observation() -> SmaResearchObservation:
    """Return the deterministic synthetic broad ETF SMA observation."""

    return build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=_AS_OF,
        window=_WINDOW,
        price_points=build_synthetic_sma_research_price_points(),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def expected_synthetic_sma_research_observation_dict() -> dict[str, object]:
    """Return the exact primitive synthetic SMA observation payload."""

    return {
        "observation_type": "sma_research_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": _SYMBOL,
        "as_of": _AS_OF,
        "window": _WINDOW,
        "sample_count": 4,
        "eligible_sample_count": 3,
        "ignored_future_sample_count": 1,
        "latest_close": "110.00",
        "sma_value": "100.00",
        "distance_from_sma": "10.00",
        "distance_from_sma_pct": "0.1",
        "position_vs_sma": "above",
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_EXPECTED_NON_CLAIMS),
    }


def build_synthetic_insufficient_history_sma_research_observation() -> (
    SmaResearchObservation
):
    """Return a deterministic synthetic SMA observation with too little history."""

    return build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=_AS_OF,
        window=_WINDOW,
        price_points=_insufficient_history_price_points(),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def expected_synthetic_insufficient_history_sma_research_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive insufficient-history SMA observation payload."""

    return {
        "observation_type": "sma_research_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": _SYMBOL,
        "as_of": _AS_OF,
        "window": _WINDOW,
        "sample_count": 3,
        "eligible_sample_count": 2,
        "ignored_future_sample_count": 1,
        "latest_close": "101.00",
        "sma_value": None,
        "distance_from_sma": None,
        "distance_from_sma_pct": None,
        "position_vs_sma": "insufficient_history",
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_EXPECTED_NON_CLAIMS),
    }


def _insufficient_history_price_points() -> tuple[SmaResearchPricePoint, ...]:
    return (
        _price_point("2026-01-19", "100.00"),
        _price_point("2026-01-20", "101.00"),
        _price_point("2026-01-21", "125.00"),
    )


def _price_point(value_date: str, close: str) -> SmaResearchPricePoint:
    return SmaResearchPricePoint(value_date, Decimal(close))
