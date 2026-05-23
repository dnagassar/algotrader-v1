"""Synthetic advisory-only risk authority brief fixture."""

from __future__ import annotations

from algotrader.research.risk_authority_brief import (
    RiskAuthorityBrief,
    build_risk_authority_brief,
)
from tests.fixtures.risk_authority_brief_section import (
    build_synthetic_risk_authority_brief_section,
    expected_synthetic_risk_authority_brief_section_dict,
)

__all__ = [
    "build_synthetic_risk_authority_brief",
    "expected_synthetic_risk_authority_brief_dict",
]

_TITLE = "Advisory risk metadata brief: 1 section"
_SUMMARY = (
    "Advisory brief contains 1 candidate risk metadata section(s) with "
    "1 item(s), 3 limitation(s), and 13 non-claim(s)."
)


def build_synthetic_risk_authority_brief() -> RiskAuthorityBrief:
    """Return the deterministic synthetic risk authority brief."""

    section = build_synthetic_risk_authority_brief_section()
    return build_risk_authority_brief((section,))


def expected_synthetic_risk_authority_brief_dict() -> dict[str, object]:
    """Return the exact primitive risk authority brief payload."""

    section = expected_synthetic_risk_authority_brief_section_dict()
    return {
        "brief_type": "risk_authority_brief",
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
