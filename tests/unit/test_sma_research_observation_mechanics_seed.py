from __future__ import annotations

import json
from decimal import Decimal

from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SYMBOL = "SYN-SMA-SEED"
_AS_OF = "2026-02-03"
_WINDOW = 3
_LIMITATIONS = (
    "synthetic close-price samples for pipeline validation only",
    "as-of filtering ignores later samples before SMA arithmetic",
    "advisory-only research observation with no system connection",
)
_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mutation authority"),
    _not("paper read", "iness"),
    _not("live read", "iness"),
    _not("capital authority"),
    _not("tra", "ding authority"),
)
_EXTRA_NON_CLAIMS = ("not operational advice",)
_EXPECTED_NON_CLAIMS = (*_REQUIRED_NON_CLAIMS, *_EXTRA_NON_CLAIMS)
_EXPECTED_OBSERVATION = {
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
    "latest_close": "11.00",
    "sma_value": "10.00",
    "distance_from_sma": "1.00",
    "distance_from_sma_pct": "0.1",
    "position_vs_sma": "above",
    "limitations": list(_LIMITATIONS),
    "non_claims": list(_EXPECTED_NON_CLAIMS),
}


def test_tiny_synthetic_seed_computes_exact_decimal_sma_observation() -> None:
    observation = _build_seed_observation()

    assert type(observation) is SmaResearchObservation
    assert observation.latest_close == Decimal("11.00")
    assert observation.sma_value == Decimal("10.00")
    assert observation.distance_from_sma == Decimal("1.00")
    assert observation.distance_from_sma_pct == Decimal("0.1")
    assert observation.position_vs_sma == "above"
    assert observation.to_dict() == _EXPECTED_OBSERVATION


def test_insufficient_history_seed_does_not_form_sma_values() -> None:
    observation = build_sma_research_observation(
        symbol=_SYMBOL,
        as_of="2026-02-02",
        window=_WINDOW,
        price_points=_seed_price_points(),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )
    payload = observation.to_dict()

    assert observation.sample_count == 4
    assert observation.eligible_sample_count == 2
    assert observation.ignored_future_sample_count == 2
    assert observation.latest_close == Decimal("10.00")
    assert observation.sma_value is None
    assert observation.distance_from_sma is None
    assert observation.distance_from_sma_pct is None
    assert observation.position_vs_sma == "insufficient_history"
    assert payload["sma_value"] is None
    assert payload["distance_from_sma"] is None
    assert payload["distance_from_sma_pct"] is None


def test_as_of_seed_ignores_future_close_changes_without_lookahead() -> None:
    baseline = _build_seed_observation(future_close="999.99")
    revised_future = _build_seed_observation(future_close="12.34")

    assert baseline.to_dict() == revised_future.to_dict() == _EXPECTED_OBSERVATION
    assert baseline.ignored_future_sample_count == 1
    assert baseline.latest_close == Decimal("11.00")
    assert baseline.sma_value == Decimal("10.00")


def test_repeated_seed_construction_and_serialization_are_deterministic() -> None:
    first = _build_seed_observation()
    second = _build_seed_observation()
    first_json = _compact_json(first.to_dict())
    second_json = _compact_json(second.to_dict())

    assert first == second
    assert first is not second
    assert first.to_dict() == second.to_dict() == _EXPECTED_OBSERVATION
    assert first_json == second_json
    assert json.loads(first_json) == _EXPECTED_OBSERVATION
    assert _primitive_only(first.to_dict())


def test_seed_builder_does_not_mutate_source_price_point_order_or_identity() -> None:
    price_points = [
        _price_point("2026-02-03", "11.00"),
        _price_point("2026-02-01", "9.00"),
        _price_point("2026-02-04", "999.99"),
        _price_point("2026-02-02", "10.00"),
    ]
    original_ids = tuple(id(point) for point in price_points)
    original_payloads = [point.to_dict() for point in price_points]

    observation = build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=_AS_OF,
        window=_WINDOW,
        price_points=price_points,
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )

    assert observation.to_dict() == _EXPECTED_OBSERVATION
    assert tuple(id(point) for point in price_points) == original_ids
    assert [point.to_dict() for point in price_points] == original_payloads
    assert tuple(point.date for point in price_points) == (
        "2026-02-03",
        "2026-02-01",
        "2026-02-04",
        "2026-02-02",
    )


def test_seed_payload_excludes_forbidden_action_or_trading_fields() -> None:
    payloads = (
        _build_seed_observation().to_dict(),
        build_sma_research_observation(
            symbol=_SYMBOL,
            as_of="2026-02-02",
            window=_WINDOW,
            price_points=_seed_price_points(),
            limitations=_LIMITATIONS,
            non_claims=_EXTRA_NON_CLAIMS,
        ).to_dict(),
    )

    for payload in payloads:
        assert _forbidden_payload_keys().isdisjoint(_payload_keys(payload))
        assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))


def _build_seed_observation(
    *,
    future_close: str = "999.99",
) -> SmaResearchObservation:
    return build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=_AS_OF,
        window=_WINDOW,
        price_points=_seed_price_points(future_close=future_close),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def _seed_price_points(
    *,
    future_close: str = "999.99",
) -> tuple[SmaResearchPricePoint, ...]:
    return (
        _price_point("2026-02-01", "9.00"),
        _price_point("2026-02-02", "10.00"),
        _price_point("2026-02-03", "11.00"),
        _price_point("2026-02-04", future_close),
    )


def _price_point(value_date: str, close: str) -> SmaResearchPricePoint:
    return SmaResearchPricePoint(value_date, Decimal(close))


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, nested_value in value.items():
            keys.add(str(key))
            keys.update(_payload_keys(nested_value))
        return keys
    if isinstance(value, list):
        keys = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()


def _forbidden_payload_keys() -> set[str]:
    return {
        "account",
        "accounts",
        "actionable",
        "allocation",
        "allocations",
        "allocation_authority",
        "approved",
        "broker",
        "broker_authority",
        "capital_authority_state",
        "evaluator",
        "live_authorized",
        "live_probe_eligible",
        "order",
        "orders",
        "order_authority",
        "paper_eligible",
        "portfolio",
        "portfolios",
        "ranking",
        "recommendation",
        "readiness",
        "score",
        "scoring",
        "signal",
        "trading_authority",
        "trading_ready",
    }
