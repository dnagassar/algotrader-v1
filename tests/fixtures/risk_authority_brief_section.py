"""Synthetic advisory-only risk authority brief section fixture."""

from __future__ import annotations

from algotrader.research.risk_authority_brief_section import (
    RiskAuthorityBriefSection,
    build_risk_authority_brief_section,
)
from tests.fixtures.risk_authority_brief_item import (
    build_synthetic_risk_authority_brief_item,
    expected_synthetic_risk_authority_brief_item_dict,
)

__all__ = [
    "build_synthetic_risk_authority_brief_section",
    "expected_synthetic_risk_authority_brief_section_dict",
]

_TITLE = "Advisory risk metadata: not_authorized"
_SUMMARY = (
    "Advisory section contains 1 candidate risk metadata item(s) across "
    "1 related strategy id(s), state(s): not_authorized, with "
    "3 limitation(s) and 13 non-claim(s)."
)


def build_synthetic_risk_authority_brief_section() -> RiskAuthorityBriefSection:
    """Return the deterministic synthetic risk authority brief section."""

    item = build_synthetic_risk_authority_brief_item()
    return build_risk_authority_brief_section((item,))


def expected_synthetic_risk_authority_brief_section_dict() -> dict[str, object]:
    """Return the exact primitive brief section payload emitted by the fixture."""

    item = expected_synthetic_risk_authority_brief_item_dict()
    return {
        "section_type": "risk_authority_brief_section",
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
