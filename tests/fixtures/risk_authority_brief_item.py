"""Synthetic advisory-only risk authority brief item fixture."""

from __future__ import annotations

from algotrader.research.risk_authority_brief_item import (
    RiskAuthorityBriefItem,
    build_risk_authority_brief_item,
)
from tests.fixtures.risk_authority_status import (
    build_synthetic_risk_authority_status,
    expected_synthetic_risk_authority_status_dict,
)

__all__ = [
    "build_synthetic_risk_authority_brief_item",
    "expected_synthetic_risk_authority_brief_item_dict",
]

_HEADLINE = "Advisory risk metadata: not_authorized."
_SUMMARY = (
    "Advisory risk metadata records not_authorized with 2 reason(s), "
    "3 limitation(s), 13 non-claim(s), 2 evidence reference(s), "
    "2 blocker(s), 2 required next step(s), and 1 related strategy id(s)."
)


def build_synthetic_risk_authority_brief_item() -> RiskAuthorityBriefItem:
    """Return the deterministic synthetic risk authority brief item."""

    status = build_synthetic_risk_authority_status()
    return build_risk_authority_brief_item(status)


def expected_synthetic_risk_authority_brief_item_dict() -> dict[str, object]:
    """Return the exact primitive brief item payload emitted by the fixture."""

    source_status = expected_synthetic_risk_authority_status_dict()
    return {
        "item_type": "risk_authority_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "authority_state": source_status["authority_state"],
        "headline": _HEADLINE,
        "summary": _SUMMARY,
        "reasons": list(source_status["reasons"]),
        "blockers": list(source_status["blockers"]),
        "required_next_steps": list(source_status["required_next_steps"]),
        "limitations": list(source_status["limitations"]),
        "non_claims": list(source_status["non_claims"]),
        "evidence_refs": list(source_status["evidence_refs"]),
        "related_strategy_ids": list(source_status["related_strategy_ids"]),
        "source_status": source_status,
    }
