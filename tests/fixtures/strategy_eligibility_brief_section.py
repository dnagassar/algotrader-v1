"""Synthetic strategy eligibility brief section fixture."""

from __future__ import annotations

from algotrader.research.strategy_eligibility_brief_section import (
    StrategyEligibilityBriefSection,
    build_strategy_eligibility_brief_section,
)
from tests.fixtures.strategy_eligibility_brief_item import (
    build_synthetic_strategy_eligibility_brief_item,
    expected_synthetic_strategy_eligibility_brief_item_dict,
)

__all__ = [
    "build_synthetic_strategy_eligibility_brief_section",
    "expected_synthetic_strategy_eligibility_brief_section_dict",
]

_TITLE = "Strategy eligibility metadata: research_only"
_SUMMARY = (
    "Advisory section contains 1 candidate eligibility item(s) across "
    "1 strategy id(s), state(s): research_only, with 3 limitation(s) "
    "and 9 non-claim(s)."
)


def build_synthetic_strategy_eligibility_brief_section() -> (
    StrategyEligibilityBriefSection
):
    """Return the deterministic synthetic strategy eligibility brief section."""

    item = build_synthetic_strategy_eligibility_brief_item()
    return build_strategy_eligibility_brief_section((item,))


def expected_synthetic_strategy_eligibility_brief_section_dict() -> (
    dict[str, object]
):
    """Return the exact primitive brief section payload emitted by the fixture."""

    item = expected_synthetic_strategy_eligibility_brief_item_dict()
    return {
        "section_type": "strategy_eligibility_brief_section",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY,
        "item_count": 1,
        "items": [item],
        "limitations": list(item["limitations"]),
        "non_claims": list(item["non_claims"]),
    }
