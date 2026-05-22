"""Source-agnostic synthetic research market-bar fixture."""

from __future__ import annotations

__all__ = [
    "build_synthetic_research_market_bar",
    "expected_synthetic_research_market_bar_dict",
    "expected_synthetic_research_market_bar_json",
]


_SYNTHETIC_RESEARCH_MARKET_BAR_NON_CLAIMS = (
    "not source approval",
    "not data approval",
    "not endpoint approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not evidence approval",
    "not return-construction approval",
    "not no-lookahead approval",
    "not strategy validation",
    "not trading readiness",
)


def build_synthetic_research_market_bar() -> dict[str, object]:
    """Return one deterministic primitive source-agnostic market-bar row."""

    return expected_synthetic_research_market_bar_dict()


def expected_synthetic_research_market_bar_dict() -> dict[str, object]:
    """Return the pinned primitive payload for the synthetic market-bar fixture."""

    return {
        "symbol": "SYNBAR001",
        "observation_date": "2026-01-23",
        "open": 100.0,
        "high": 101.25,
        "low": 99.75,
        "close": 100.5,
        "volume": 12345,
        "currency": "SYN",
        "calendar_name": "synthetic_research_calendar",
        "adjustment_policy": "synthetic_unadjusted_placeholder",
        "return_basis": "not_applicable_single_observation",
        "source_category": "source_agnostic_synthetic_research_input_shape",
        "synthetic_only": True,
        "candidate_only": True,
        "non_claims": list(_SYNTHETIC_RESEARCH_MARKET_BAR_NON_CLAIMS),
    }


def expected_synthetic_research_market_bar_json() -> str:
    """Return the pinned compact JSON payload for the synthetic market-bar fixture."""

    return _EXPECTED_SYNTHETIC_RESEARCH_MARKET_BAR_JSON


_EXPECTED_SYNTHETIC_RESEARCH_MARKET_BAR_JSON = (
    '{"symbol":"SYNBAR001","observation_date":"2026-01-23",'
    '"open":100.0,"high":101.25,"low":99.75,"close":100.5,'
    '"volume":12345,"currency":"SYN",'
    '"calendar_name":"synthetic_research_calendar",'
    '"adjustment_policy":"synthetic_unadjusted_placeholder",'
    '"return_basis":"not_applicable_single_observation",'
    '"source_category":"source_agnostic_synthetic_research_input_shape",'
    '"synthetic_only":true,"candidate_only":true,'
    '"non_claims":["not source approval","not data approval",'
    '"not endpoint approval","not universe approval","not benchmark approval",'
    '"not cash proxy approval","not methodology approval",'
    '"not evidence approval","not return-construction approval",'
    '"not no-lookahead approval","not strategy validation",'
    '"not trading readiness"]}'
)
