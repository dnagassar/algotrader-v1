"""Source-agnostic synthetic research market-bar fixture."""

from __future__ import annotations

__all__ = [
    "build_synthetic_research_market_bar",
    "build_synthetic_research_market_bar_sequence",
    "expected_synthetic_research_market_bar_dict",
    "expected_synthetic_research_market_bar_json",
    "expected_synthetic_research_market_bar_sequence_dict",
    "expected_synthetic_research_market_bar_sequence_json",
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


def build_synthetic_research_market_bar_sequence() -> dict[str, object]:
    """Return one deterministic primitive source-agnostic market-bar sequence."""

    return expected_synthetic_research_market_bar_sequence_dict()


def expected_synthetic_research_market_bar_dict() -> dict[str, object]:
    """Return the pinned primitive payload for the synthetic market-bar fixture."""

    return _synthetic_research_market_bar_row(
        symbol="SYNBAR001",
        observation_date="2026-01-23",
        open_value=100.0,
        high=101.25,
        low=99.75,
        close=100.5,
        volume=12345,
        return_basis="not_applicable_single_observation",
    )


def expected_synthetic_research_market_bar_sequence_dict() -> dict[str, object]:
    """Return the pinned primitive payload for a synthetic market-bar sequence."""

    symbol = "SYNBARSEQ001"
    return {
        "sequence_id": "synthetic_research_market_bar_sequence_001",
        "symbol": symbol,
        "bar_count": 3,
        "bars": [
            _synthetic_research_market_bar_row(
                symbol=symbol,
                observation_date="2026-01-21",
                open_value=100.0,
                high=100.75,
                low=99.5,
                close=100.25,
                volume=10000,
                return_basis="not_applicable_sequence_fixture",
            ),
            _synthetic_research_market_bar_row(
                symbol=symbol,
                observation_date="2026-01-22",
                open_value=100.25,
                high=101.0,
                low=100.0,
                close=100.75,
                volume=11000,
                return_basis="not_applicable_sequence_fixture",
            ),
            _synthetic_research_market_bar_row(
                symbol=symbol,
                observation_date="2026-01-23",
                open_value=100.75,
                high=101.25,
                low=100.5,
                close=101.0,
                volume=12000,
                return_basis="not_applicable_sequence_fixture",
            ),
        ],
        "synthetic_only": True,
        "candidate_only": True,
        "non_claims": list(_SYNTHETIC_RESEARCH_MARKET_BAR_NON_CLAIMS),
    }


def expected_synthetic_research_market_bar_json() -> str:
    """Return the pinned compact JSON payload for the synthetic market-bar fixture."""

    return _EXPECTED_SYNTHETIC_RESEARCH_MARKET_BAR_JSON


def expected_synthetic_research_market_bar_sequence_json() -> str:
    """Return the pinned compact JSON payload for the synthetic sequence fixture."""

    return _EXPECTED_SYNTHETIC_RESEARCH_MARKET_BAR_SEQUENCE_JSON


def _synthetic_research_market_bar_row(
    *,
    symbol: str,
    observation_date: str,
    open_value: float,
    high: float,
    low: float,
    close: float,
    volume: int,
    return_basis: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "observation_date": observation_date,
        "open": open_value,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "currency": "SYN",
        "calendar_name": "synthetic_research_calendar",
        "adjustment_policy": "synthetic_unadjusted_placeholder",
        "return_basis": return_basis,
        "source_category": "source_agnostic_synthetic_research_input_shape",
        "synthetic_only": True,
        "candidate_only": True,
        "non_claims": list(_SYNTHETIC_RESEARCH_MARKET_BAR_NON_CLAIMS),
    }


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

_EXPECTED_SYNTHETIC_RESEARCH_MARKET_BAR_SEQUENCE_JSON = (
    '{"sequence_id":"synthetic_research_market_bar_sequence_001",'
    '"symbol":"SYNBARSEQ001","bar_count":3,"bars":['
    '{"symbol":"SYNBARSEQ001","observation_date":"2026-01-21",'
    '"open":100.0,"high":100.75,"low":99.5,"close":100.25,'
    '"volume":10000,"currency":"SYN",'
    '"calendar_name":"synthetic_research_calendar",'
    '"adjustment_policy":"synthetic_unadjusted_placeholder",'
    '"return_basis":"not_applicable_sequence_fixture",'
    '"source_category":"source_agnostic_synthetic_research_input_shape",'
    '"synthetic_only":true,"candidate_only":true,'
    '"non_claims":["not source approval","not data approval",'
    '"not endpoint approval","not universe approval","not benchmark approval",'
    '"not cash proxy approval","not methodology approval",'
    '"not evidence approval","not return-construction approval",'
    '"not no-lookahead approval","not strategy validation",'
    '"not trading readiness"]},'
    '{"symbol":"SYNBARSEQ001","observation_date":"2026-01-22",'
    '"open":100.25,"high":101.0,"low":100.0,"close":100.75,'
    '"volume":11000,"currency":"SYN",'
    '"calendar_name":"synthetic_research_calendar",'
    '"adjustment_policy":"synthetic_unadjusted_placeholder",'
    '"return_basis":"not_applicable_sequence_fixture",'
    '"source_category":"source_agnostic_synthetic_research_input_shape",'
    '"synthetic_only":true,"candidate_only":true,'
    '"non_claims":["not source approval","not data approval",'
    '"not endpoint approval","not universe approval","not benchmark approval",'
    '"not cash proxy approval","not methodology approval",'
    '"not evidence approval","not return-construction approval",'
    '"not no-lookahead approval","not strategy validation",'
    '"not trading readiness"]},'
    '{"symbol":"SYNBARSEQ001","observation_date":"2026-01-23",'
    '"open":100.75,"high":101.25,"low":100.5,"close":101.0,'
    '"volume":12000,"currency":"SYN",'
    '"calendar_name":"synthetic_research_calendar",'
    '"adjustment_policy":"synthetic_unadjusted_placeholder",'
    '"return_basis":"not_applicable_sequence_fixture",'
    '"source_category":"source_agnostic_synthetic_research_input_shape",'
    '"synthetic_only":true,"candidate_only":true,'
    '"non_claims":["not source approval","not data approval",'
    '"not endpoint approval","not universe approval","not benchmark approval",'
    '"not cash proxy approval","not methodology approval",'
    '"not evidence approval","not return-construction approval",'
    '"not no-lookahead approval","not strategy validation",'
    '"not trading readiness"]}],'
    '"synthetic_only":true,"candidate_only":true,'
    '"non_claims":["not source approval","not data approval",'
    '"not endpoint approval","not universe approval","not benchmark approval",'
    '"not cash proxy approval","not methodology approval",'
    '"not evidence approval","not return-construction approval",'
    '"not no-lookahead approval","not strategy validation",'
    '"not trading readiness"]}'
)
