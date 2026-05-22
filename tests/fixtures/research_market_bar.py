"""Source-agnostic synthetic research market-bar fixture."""

from __future__ import annotations

from decimal import Decimal

from algotrader.research.return_construction import close_to_close_returns

__all__ = [
    "build_synthetic_research_market_bar",
    "build_synthetic_research_market_bar_close_to_close_returns",
    "build_synthetic_research_market_bar_close_values",
    "build_synthetic_research_market_bar_sequence",
    "expected_synthetic_research_market_bar_close_to_close_returns_dict",
    "expected_synthetic_research_market_bar_close_to_close_returns_json",
    "expected_synthetic_research_market_bar_close_values",
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


def build_synthetic_research_market_bar_close_values() -> list[float]:
    """Extract deterministic close values from the synthetic market-bar sequence."""

    sequence = build_synthetic_research_market_bar_sequence()
    return [bar["close"] for bar in sequence["bars"]]


def build_synthetic_research_market_bar_close_to_close_returns() -> dict[str, object]:
    """Build primitive close-to-close return inputs from the synthetic sequence."""

    sequence = build_synthetic_research_market_bar_sequence()
    bars = sequence["bars"]
    close_values = build_synthetic_research_market_bar_close_values()
    decimal_closes = tuple(Decimal(str(close_value)) for close_value in close_values)
    simple_returns = close_to_close_returns(decimal_closes)

    return {
        "sequence_id": sequence["sequence_id"],
        "symbol": sequence["symbol"],
        "bar_count": sequence["bar_count"],
        "close_values": close_values,
        "return_count": len(simple_returns),
        "close_to_close_returns": [
            _synthetic_research_market_bar_close_to_close_return_row(
                previous_bar=previous_bar,
                current_bar=current_bar,
                simple_return=simple_return_value,
            )
            for previous_bar, current_bar, simple_return_value in zip(
                bars,
                bars[1:],
                simple_returns,
            )
        ],
        "return_basis": "synthetic_close_to_close_simple_return_input_consumer",
        "synthetic_only": True,
        "candidate_only": True,
        "non_claims": list(_SYNTHETIC_RESEARCH_MARKET_BAR_NON_CLAIMS),
    }


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


def expected_synthetic_research_market_bar_close_values() -> list[float]:
    """Return the pinned close values extracted from the synthetic sequence."""

    return [100.25, 100.75, 101.0]


def expected_synthetic_research_market_bar_close_to_close_returns_dict() -> dict[str, object]:
    """Return the pinned primitive payload for synthetic close-to-close returns."""

    return {
        "sequence_id": "synthetic_research_market_bar_sequence_001",
        "symbol": "SYNBARSEQ001",
        "bar_count": 3,
        "close_values": expected_synthetic_research_market_bar_close_values(),
        "return_count": 2,
        "close_to_close_returns": [
            {
                "observation_date": "2026-01-22",
                "previous_observation_date": "2026-01-21",
                "previous_close": "100.25",
                "close": "100.75",
                "simple_return": "0.004987531172069825436408977556",
            },
            {
                "observation_date": "2026-01-23",
                "previous_observation_date": "2026-01-22",
                "previous_close": "100.75",
                "close": "101.0",
                "simple_return": "0.002481389578163771712158808933",
            },
        ],
        "return_basis": "synthetic_close_to_close_simple_return_input_consumer",
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


def expected_synthetic_research_market_bar_close_to_close_returns_json() -> str:
    """Return the pinned compact JSON payload for synthetic close-to-close returns."""

    return _EXPECTED_SYNTHETIC_RESEARCH_MARKET_BAR_CLOSE_TO_CLOSE_RETURNS_JSON


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


def _synthetic_research_market_bar_close_to_close_return_row(
    *,
    previous_bar: dict[str, object],
    current_bar: dict[str, object],
    simple_return: Decimal,
) -> dict[str, str]:
    return {
        "observation_date": str(current_bar["observation_date"]),
        "previous_observation_date": str(previous_bar["observation_date"]),
        "previous_close": str(previous_bar["close"]),
        "close": str(current_bar["close"]),
        "simple_return": str(simple_return),
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

_EXPECTED_SYNTHETIC_RESEARCH_MARKET_BAR_CLOSE_TO_CLOSE_RETURNS_JSON = (
    '{"sequence_id":"synthetic_research_market_bar_sequence_001",'
    '"symbol":"SYNBARSEQ001","bar_count":3,'
    '"close_values":[100.25,100.75,101.0],"return_count":2,'
    '"close_to_close_returns":['
    '{"observation_date":"2026-01-22",'
    '"previous_observation_date":"2026-01-21",'
    '"previous_close":"100.25","close":"100.75",'
    '"simple_return":"0.004987531172069825436408977556"},'
    '{"observation_date":"2026-01-23",'
    '"previous_observation_date":"2026-01-22",'
    '"previous_close":"100.75","close":"101.0",'
    '"simple_return":"0.002481389578163771712158808933"}],'
    '"return_basis":"synthetic_close_to_close_simple_return_input_consumer",'
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
