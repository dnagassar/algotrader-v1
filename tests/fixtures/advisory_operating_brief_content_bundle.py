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
    "build_synthetic_advisory_operating_brief_content_bundle_with_risk",
    "expected_synthetic_advisory_operating_brief_content_bundle_dict",
    "expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict",
]

_TITLE = "Advisory operating brief content bundle metadata"
_SUMMARY = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 12 limitation(s), and 25 non-claim(s)."
)
_SUMMARY_WITH_RISK = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 1 risk authority brief(s), "
    "14 limitation(s), and 32 non-claim(s)."
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


def build_synthetic_risk_authority_brief() -> object:
    """Return the deterministic Phase 176 risk authority brief fixture."""

    build_synthetic_candidate_research_brief = __import__
    risk_authority_fixture_module = build_synthetic_candidate_research_brief(
        "tests.fixtures.risk_authority_brief",
        fromlist=("build_synthetic_risk_authority_brief",),
    )
    build_synthetic_candidate_research_brief = (
        risk_authority_fixture_module.build_synthetic_risk_authority_brief
    )
    return build_synthetic_candidate_research_brief()


def build_synthetic_advisory_operating_brief_content_bundle_with_risk() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic content bundle with risk authority metadata."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_risk_authority_brief
    )
    risk_authority_brief = expected_synthetic_strategy_eligibility_brief_dict()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        risk_authority_briefs=(risk_authority_brief,),
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


def expected_synthetic_risk_authority_brief_dict() -> dict[str, object]:
    """Return the exact primitive Phase 176 risk authority brief payload."""

    build_synthetic_candidate_research_brief = __import__
    risk_authority_fixture_module = build_synthetic_candidate_research_brief(
        "tests.fixtures.risk_authority_brief",
        fromlist=("expected_synthetic_risk_authority_brief_dict",),
    )
    build_synthetic_candidate_research_brief = (
        risk_authority_fixture_module.expected_synthetic_risk_authority_brief_dict
    )
    return build_synthetic_candidate_research_brief()


def expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict() -> (
    dict[str, object]
):
    """Return the exact primitive risk-inclusive bundle fixture payload."""

    candidate_brief = expected_synthetic_candidate_research_brief_dict()
    strategy_eligibility_brief = expected_synthetic_strategy_eligibility_brief_dict()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_risk_authority_brief_dict
    )
    risk_authority_brief = build_synthetic_candidate_research_brief()
    limitations = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "limitations",
        risk_authority_brief,
    )
    non_claims = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "non_claims",
        risk_authority_brief,
    )

    return {
        "bundle_type": "advisory_operating_brief_content_bundle",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY_WITH_RISK,
        "candidate_research_brief_count": 1,
        "strategy_eligibility_brief_count": 1,
        "risk_authority_brief_count": 1,
        "candidate_research_briefs": [candidate_brief],
        "strategy_eligibility_briefs": [strategy_eligibility_brief],
        "risk_authority_briefs": [risk_authority_brief],
        "limitations": limitations,
        "non_claims": non_claims,
    }


def _combined_expected_values(
    first: dict[str, object],
    second: dict[str, object],
    field_name: str,
    *remaining: dict[str, object],
) -> list[str]:
    values: list[str] = []
    for payload in (first, second, *remaining):
        for value in payload[field_name]:
            if value in values:
                continue
            values.append(value)

    return values
