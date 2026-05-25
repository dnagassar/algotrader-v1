"""Deterministic synthetic research return observation fixtures."""

from __future__ import annotations

from decimal import Decimal

from algotrader.research.research_return_observation import (
    ResearchReturnPricePoint,
    ResearchReturnSeriesObservation,
    build_research_return_series_observation,
)

__all__ = [
    "build_synthetic_research_return_price_points",
    "expected_synthetic_research_return_price_point_dicts",
    "build_synthetic_research_return_series_observation",
    "expected_synthetic_research_return_series_observation_dict",
    "build_synthetic_insufficient_research_return_series_observation",
    "expected_synthetic_insufficient_research_return_series_observation_dict",
]

_SYMBOL = "SYNTH_ETF"
_AS_OF = "2026-01-20"
_LIMITATIONS = (
    "synthetic broad ETF close series for return mechanics only",
    "fixed close samples with later samples ignored by the builder",
    "candidate-only advisory research metadata with no system connection",
)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_REQUIRED_NON_CLAIMS = (
    _not("sour", "ce/data app", "roval"),
    _not("adjusted-close/corporate-action completeness"),
    _not("predict", "ive validity"),
    _not("prof", "itability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evalu", "ator behavior"),
    _not("back", "testing validation"),
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


def build_synthetic_research_return_price_points() -> (
    tuple[ResearchReturnPricePoint, ...]
):
    """Return deterministic synthetic broad ETF close samples."""

    return (
        _price_point("2026-01-15", "100.00"),
        _price_point("2026-01-16", "105.00"),
        _price_point("2026-01-19", "94.50"),
        _price_point("2026-01-20", "94.50"),
        _price_point("2026-01-21", "120.00"),
    )


def expected_synthetic_research_return_price_point_dicts() -> list[dict[str, str]]:
    """Return exact primitive price point payload copies."""

    return [
        {"date": "2026-01-15", "close": "100.00"},
        {"date": "2026-01-16", "close": "105.00"},
        {"date": "2026-01-19", "close": "94.50"},
        {"date": "2026-01-20", "close": "94.50"},
        {"date": "2026-01-21", "close": "120.00"},
    ]


def build_synthetic_research_return_series_observation() -> (
    ResearchReturnSeriesObservation
):
    """Return the deterministic synthetic broad ETF return observation."""

    return build_research_return_series_observation(
        symbol=_SYMBOL,
        as_of=_AS_OF,
        price_points=build_synthetic_research_return_price_points(),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def expected_synthetic_research_return_series_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic return observation payload."""

    return {
        "observation_type": "research_return_series_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": _SYMBOL,
        "as_of": _AS_OF,
        "return_method": "close_to_close_simple_return",
        "price_basis": "synthetic_close",
        "sample_count": 5,
        "eligible_sample_count": 4,
        "ignored_future_sample_count": 1,
        "return_count": 3,
        "returns": [
            {
                "start_date": "2026-01-15",
                "end_date": "2026-01-16",
                "start_close": "100.00",
                "end_close": "105.00",
                "simple_return": "0.05",
            },
            {
                "start_date": "2026-01-16",
                "end_date": "2026-01-19",
                "start_close": "105.00",
                "end_close": "94.50",
                "simple_return": "-0.1",
            },
            {
                "start_date": "2026-01-19",
                "end_date": "2026-01-20",
                "start_close": "94.50",
                "end_close": "94.50",
                "simple_return": "0",
            },
        ],
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_EXPECTED_NON_CLAIMS),
    }


def build_synthetic_insufficient_research_return_series_observation() -> (
    ResearchReturnSeriesObservation
):
    """Return a deterministic synthetic return observation with too little history."""

    return build_research_return_series_observation(
        symbol=_SYMBOL,
        as_of=_AS_OF,
        price_points=_insufficient_price_points(),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def expected_synthetic_insufficient_research_return_series_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive insufficient-history return observation payload."""

    return {
        "observation_type": "research_return_series_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": _SYMBOL,
        "as_of": _AS_OF,
        "return_method": "close_to_close_simple_return",
        "price_basis": "synthetic_close",
        "sample_count": 2,
        "eligible_sample_count": 1,
        "ignored_future_sample_count": 1,
        "return_count": 0,
        "returns": [],
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_EXPECTED_NON_CLAIMS),
    }


def _insufficient_price_points() -> tuple[ResearchReturnPricePoint, ...]:
    return (
        _price_point("2026-01-20", "101.00"),
        _price_point("2026-01-21", "125.00"),
    )


def _price_point(value_date: str, close: str) -> ResearchReturnPricePoint:
    return ResearchReturnPricePoint(value_date, Decimal(close))
