"""Synthetic strategy eligibility brief fixture."""

from __future__ import annotations

from algotrader.research.strategy_eligibility_brief import (
    StrategyEligibilityBrief,
    build_strategy_eligibility_brief,
)
from tests.fixtures.strategy_eligibility_brief_section import (
    build_synthetic_strategy_eligibility_brief_section,
    expected_synthetic_strategy_eligibility_brief_section_dict,
)

__all__ = [
    "build_synthetic_strategy_eligibility_brief",
    "expected_synthetic_strategy_eligibility_brief_dict",
]

_TITLE = "Strategy eligibility brief metadata"
_SUMMARY = (
    "Advisory brief contains 1 strategy eligibility section(s), "
    "1 candidate item(s), 3 limitation(s), and 9 non-claim(s)."
)


def build_synthetic_strategy_eligibility_brief() -> StrategyEligibilityBrief:
    """Return the deterministic synthetic strategy eligibility brief."""

    section = build_synthetic_strategy_eligibility_brief_section()
    return build_strategy_eligibility_brief((section,))


def expected_synthetic_strategy_eligibility_brief_dict() -> dict[str, object]:
    """Return the exact primitive brief payload emitted by the fixture."""

    section = expected_synthetic_strategy_eligibility_brief_section_dict()
    return {
        "brief_type": "strategy_eligibility_brief",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY,
        "section_count": 1,
        "sections": [section],
        "limitations": list(section["limitations"]),
        "non_claims": list(section["non_claims"]),
    }
