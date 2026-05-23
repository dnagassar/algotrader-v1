"""Synthetic strategy eligibility brief item fixture."""

from __future__ import annotations

from algotrader.research.strategy_eligibility_brief_item import (
    StrategyEligibilityBriefItem,
    build_strategy_eligibility_brief_item,
)
from tests.fixtures.strategy_eligibility_status import (
    build_synthetic_strategy_eligibility_status,
    expected_synthetic_strategy_eligibility_status_dict,
)

__all__ = [
    "build_synthetic_strategy_eligibility_brief_item",
    "expected_synthetic_strategy_eligibility_brief_item_dict",
]

_HEADLINE = "Advisory eligibility metadata: research_only."
_SUMMARY = (
    "Candidate metadata records research_only with 2 reason(s), "
    "3 limitation(s), 9 non-claim(s), 2 evidence reference(s), "
    "2 blocker(s), and 2 required next step(s)."
)


def build_synthetic_strategy_eligibility_brief_item() -> (
    StrategyEligibilityBriefItem
):
    """Return the deterministic synthetic strategy eligibility brief item."""

    status = build_synthetic_strategy_eligibility_status()
    return build_strategy_eligibility_brief_item(status)


def expected_synthetic_strategy_eligibility_brief_item_dict() -> (
    dict[str, object]
):
    """Return the exact primitive brief item payload emitted by the fixture."""

    source_status = expected_synthetic_strategy_eligibility_status_dict()
    return {
        "item_type": "strategy_eligibility_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "strategy_id": source_status["strategy_id"],
        "strategy_name": source_status["strategy_name"],
        "eligibility_state": source_status["eligibility_state"],
        "headline": _HEADLINE,
        "summary": _SUMMARY,
        "reasons": list(source_status["reasons"]),
        "evidence_refs": list(source_status["evidence_refs"]),
        "blockers": list(source_status["blockers"]),
        "required_next_steps": list(source_status["required_next_steps"]),
        "limitations": list(source_status["limitations"]),
        "non_claims": list(source_status["non_claims"]),
        "source_status": source_status,
    }
