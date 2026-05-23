"""Synthetic advisory operating brief content bundle fixture."""

from __future__ import annotations

from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
    expected_synthetic_candidate_research_brief_dict,
)
from tests.fixtures.strategy_eligibility_brief import (
    build_synthetic_strategy_eligibility_brief,
    expected_synthetic_strategy_eligibility_brief_dict,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_content_bundle",
    "expected_synthetic_advisory_operating_brief_content_bundle_dict",
]

_TITLE = "Advisory operating brief content bundle metadata"
_SUMMARY = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 12 limitation(s), and 25 non-claim(s)."
)


def build_synthetic_advisory_operating_brief_content_bundle() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic synthetic advisory operating content bundle."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
    )


def expected_synthetic_advisory_operating_brief_content_bundle_dict() -> (
    dict[str, object]
):
    """Return the exact primitive bundle payload emitted by the fixture."""

    candidate_brief = expected_synthetic_candidate_research_brief_dict()
    strategy_eligibility_brief = expected_synthetic_strategy_eligibility_brief_dict()
    limitations = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "limitations",
    )
    non_claims = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "non_claims",
    )

    return {
        "bundle_type": "advisory_operating_brief_content_bundle",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY,
        "candidate_research_brief_count": 1,
        "strategy_eligibility_brief_count": 1,
        "candidate_research_briefs": [candidate_brief],
        "strategy_eligibility_briefs": [strategy_eligibility_brief],
        "limitations": limitations,
        "non_claims": non_claims,
    }


def _combined_expected_values(
    first: dict[str, object],
    second: dict[str, object],
    field_name: str,
) -> list[str]:
    values: list[str] = []
    for payload in (first, second):
        for value in payload[field_name]:
            if value in values:
                continue
            values.append(value)

    return values
