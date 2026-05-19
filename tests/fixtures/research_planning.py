"""Synthetic broad ETF research-planning package fixture."""

from __future__ import annotations

from tests.fixtures.research_methodology import (
    build_synthetic_broad_etf_methodology_scope,
    expected_synthetic_broad_etf_methodology_scope_json,
)
from tests.fixtures.research_scope import (
    build_synthetic_broad_etf_research_scope,
    expected_synthetic_broad_etf_research_scope_json,
)

__all__ = [
    "build_synthetic_broad_etf_research_planning_package",
    "expected_synthetic_broad_etf_research_planning_package_json",
]


_PLANNING_PACKAGE_ID = "synthetic_broad_etf_research_planning_package_candidate"
_AS_OF_DATE = "2026-01-20"

_LIMITATIONS = (
    "Combines only the Phase 73 synthetic research-scope payload and Phase 75 "
    "synthetic methodology-scope payload for deterministic tests.",
    "Contains no external observations, external identifiers, operational "
    "instructions, or reviewed authority.",
)

_NON_CLAIMS = (
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not strategy validation",
    "not signal approval",
    "not evaluator approval",
    "not trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "no real data ingestion",
)


def build_synthetic_broad_etf_research_planning_package() -> dict[str, object]:
    """Return a deterministic primitive package for synthetic planning tests."""

    return {
        "planning_package_id": _PLANNING_PACKAGE_ID,
        "as_of_date": _AS_OF_DATE,
        "research_scope": build_synthetic_broad_etf_research_scope().to_dict(),
        "methodology_scope": (
            build_synthetic_broad_etf_methodology_scope().to_dict()
        ),
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_NON_CLAIMS),
    }


def expected_synthetic_broad_etf_research_planning_package_json() -> str:
    """Return the pinned compact JSON payload for the synthetic package."""

    return _EXPECTED_SYNTHETIC_BROAD_ETF_RESEARCH_PLANNING_PACKAGE_JSON


_EXPECTED_SYNTHETIC_BROAD_ETF_RESEARCH_PLANNING_PACKAGE_JSON = (
    '{"planning_package_id":"synthetic_broad_etf_research_planning_package_candidate",'
    '"as_of_date":"2026-01-20","research_scope":'
    + expected_synthetic_broad_etf_research_scope_json()
    + ',"methodology_scope":'
    + expected_synthetic_broad_etf_methodology_scope_json()
    + ',"limitations":["Combines only the Phase 73 synthetic research-scope '
    'payload and Phase 75 synthetic methodology-scope payload for deterministic '
    'tests.","Contains no external observations, external identifiers, '
    'operational instructions, or reviewed authority."],"non_claims":['
    '"not source approval","not universe approval","not benchmark approval",'
    '"not cash proxy approval","not methodology approval","not parameter approval",'
    '"not strategy validation","not signal approval","not evaluator approval",'
    '"not trading authority","no broker/order/fill/portfolio/runtime behavior",'
    '"no real data ingestion"]}'
)
