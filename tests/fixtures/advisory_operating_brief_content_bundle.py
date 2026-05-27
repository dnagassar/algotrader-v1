"""Synthetic advisory operating brief content bundle fixture."""

from __future__ import annotations

from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.research_data_source_readiness_summary import (
    build_research_data_source_readiness_summary,
)
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
    expected_synthetic_candidate_research_brief_dict,
)
from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_dict,
    expected_synthetic_research_data_source_readiness_summary,
    expected_synthetic_research_data_source_readiness_summary_dict,
)
from tests.fixtures.strategy_eligibility_brief import (
    build_synthetic_strategy_eligibility_brief,
    expected_synthetic_strategy_eligibility_brief_dict,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_content_bundle",
    "build_synthetic_advisory_operating_brief_content_bundle_with_risk",
    "build_synthetic_advisory_operating_brief_content_bundle_with_research_queue",
    "build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation",
    "build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation",
    "build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation",
    "build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness",
    "build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary",
    "build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary",
    "expected_synthetic_advisory_operating_brief_content_bundle_dict",
    "expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict",
    "expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict",
    "expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict",
    "expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict",
    "expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation_dict",
    "expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_dict",
    "expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary_dict",
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
_SUMMARY_WITH_RESEARCH_QUEUE = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 1 risk authority brief(s), "
    "1 research queue brief(s), 17 limitation(s), and 41 non-claim(s)."
)
_SUMMARY_WITH_SMA_RESEARCH_OBSERVATION = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 1 risk authority brief(s), "
    "1 research queue brief(s), 1 SMA research observation brief(s), "
    "20 limitation(s), and 46 non-claim(s)."
)
_SUMMARY_WITH_RESEARCH_RETURN_OBSERVATION = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 1 risk authority brief(s), "
    "1 research queue brief(s), 1 SMA research observation brief(s), "
    "1 research return observation brief(s), 22 limitation(s), and "
    "48 non-claim(s)."
)
_SUMMARY_WITH_RESEARCH_RETURN_SUMMARY_OBSERVATION = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 1 risk authority brief(s), "
    "1 research queue brief(s), 1 SMA research observation brief(s), "
    "1 research return observation brief(s), 1 research return summary "
    "observation brief(s), 22 limitation(s), and 48 non-claim(s)."
)
_SUMMARY_WITH_RESEARCH_DATA_SOURCE_READINESS = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 1 research data source readiness "
    "diagnostic(s), 14 limitation(s), and 30 non-claim(s)."
)
_SUMMARY_WITH_RESEARCH_DATA_SOURCE_READINESS_SUMMARY = (
    "Advisory content bundle contains 1 candidate research brief(s), "
    "1 strategy eligibility brief(s), 1 research data source readiness summary "
    "diagnostic(s), 14 limitation(s), and 25 non-claim(s)."
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


def build_synthetic_research_queue_brief() -> object:
    """Return the deterministic Phase 183 research queue brief fixture."""

    build_synthetic_candidate_research_brief = __import__
    research_queue_fixture_module = build_synthetic_candidate_research_brief(
        "tests.fixtures.research_queue_brief",
        fromlist=("build_synthetic_research_queue_brief",),
    )
    build_synthetic_candidate_research_brief = (
        research_queue_fixture_module.build_synthetic_research_queue_brief
    )
    return build_synthetic_candidate_research_brief()


def build_synthetic_sma_research_observation_brief() -> object:
    """Return the deterministic Phase 202 SMA research observation brief."""

    build_synthetic_candidate_research_brief = __import__
    sma_research_observation_fixture_module = build_synthetic_candidate_research_brief(
        "tests.fixtures.sma_research_observation_brief_container",
        fromlist=("build_synthetic_sma_research_observation_brief",),
    )
    build_synthetic_candidate_research_brief = (
        sma_research_observation_fixture_module.build_synthetic_sma_research_observation_brief
    )
    return build_synthetic_candidate_research_brief()


def build_synthetic_research_return_observation_brief() -> object:
    """Return the deterministic Phase 216-219 return observation brief."""

    build_synthetic_candidate_research_brief = __import__
    research_return_observation_fixture_module = build_synthetic_candidate_research_brief(
        "tests.fixtures.research_return_observation_brief_container",
        fromlist=("build_synthetic_research_return_observation_brief",),
    )
    build_synthetic_candidate_research_brief = (
        research_return_observation_fixture_module.build_synthetic_research_return_observation_brief
    )
    return build_synthetic_candidate_research_brief()


def build_synthetic_research_return_summary_observation_brief() -> object:
    """Return the deterministic Phase 226-230 return summary brief."""

    build_synthetic_candidate_research_brief = __import__
    research_return_summary_fixture_module = build_synthetic_candidate_research_brief(
        "tests.fixtures.research_return_summary_observation",
        fromlist=("build_synthetic_research_return_summary_observation_brief",),
    )
    build_synthetic_candidate_research_brief = (
        research_return_summary_fixture_module.build_synthetic_research_return_summary_observation_brief
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


def build_synthetic_advisory_operating_brief_content_bundle_with_research_queue() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic content bundle with research queue metadata."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_risk_authority_brief
    )
    risk_authority_brief = expected_synthetic_strategy_eligibility_brief_dict()
    expected_synthetic_candidate_research_brief_dict = (
        build_synthetic_research_queue_brief
    )
    research_queue_brief = expected_synthetic_candidate_research_brief_dict()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        risk_authority_briefs=(risk_authority_brief,),
        research_queue_briefs=(research_queue_brief,),
    )


def build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic content bundle with SMA observation metadata."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_risk_authority_brief
    )
    risk_authority_brief = expected_synthetic_strategy_eligibility_brief_dict()
    expected_synthetic_candidate_research_brief_dict = (
        build_synthetic_research_queue_brief
    )
    research_queue_brief = expected_synthetic_candidate_research_brief_dict()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_sma_research_observation_brief
    )
    sma_brief = expected_synthetic_strategy_eligibility_brief_dict()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        risk_authority_briefs=(risk_authority_brief,),
        research_queue_briefs=(research_queue_brief,),
        sma_research_observation_briefs=(sma_brief,),
    )


def build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic content bundle with return observation metadata."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_risk_authority_brief
    )
    risk_authority_brief = expected_synthetic_strategy_eligibility_brief_dict()
    expected_synthetic_candidate_research_brief_dict = (
        build_synthetic_research_queue_brief
    )
    research_queue_brief = expected_synthetic_candidate_research_brief_dict()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_sma_research_observation_brief
    )
    sma_brief = expected_synthetic_strategy_eligibility_brief_dict()
    expected_synthetic_candidate_research_brief_dict = (
        build_synthetic_research_return_observation_brief
    )
    research_return_brief = expected_synthetic_candidate_research_brief_dict()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        risk_authority_briefs=(risk_authority_brief,),
        research_queue_briefs=(research_queue_brief,),
        sma_research_observation_briefs=(sma_brief,),
        research_return_observation_briefs=(research_return_brief,),
    )


def build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic content bundle with return summary metadata."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_risk_authority_brief
    )
    risk_authority_brief = expected_synthetic_strategy_eligibility_brief_dict()
    expected_synthetic_candidate_research_brief_dict = (
        build_synthetic_research_queue_brief
    )
    research_queue_brief = expected_synthetic_candidate_research_brief_dict()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_sma_research_observation_brief
    )
    sma_brief = expected_synthetic_strategy_eligibility_brief_dict()
    expected_synthetic_candidate_research_brief_dict = (
        build_synthetic_research_return_observation_brief
    )
    research_return_brief = expected_synthetic_candidate_research_brief_dict()
    expected_synthetic_strategy_eligibility_brief_dict = (
        build_synthetic_research_return_summary_observation_brief
    )
    research_return_summary_brief = expected_synthetic_strategy_eligibility_brief_dict()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        risk_authority_briefs=(risk_authority_brief,),
        research_queue_briefs=(research_queue_brief,),
        sma_research_observation_briefs=(sma_brief,),
        research_return_observation_briefs=(research_return_brief,),
        research_return_summary_observation_briefs=(
            research_return_summary_brief,
        ),
    )


def build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic content bundle with data-source diagnostics."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    readiness = expected_synthetic_research_data_source_readiness()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        research_data_source_readiness=(readiness,),
    )


def build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic content bundle with data-source summary diagnostics."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    summary = expected_synthetic_research_data_source_readiness_summary(
        build_research_data_source_readiness_summary
    )
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        research_data_source_readiness_summaries=(summary,),
    )


def build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic content bundle with paired data-source diagnostics."""

    candidate_brief = build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = build_synthetic_strategy_eligibility_brief()
    readiness = expected_synthetic_research_data_source_readiness()
    summary = expected_synthetic_research_data_source_readiness_summary(
        build_research_data_source_readiness_summary,
        readiness,
    )
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        research_data_source_readiness=(readiness,),
        research_data_source_readiness_summaries=(summary,),
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


def expected_synthetic_research_queue_brief_dict() -> dict[str, object]:
    """Return the exact primitive Phase 183 research queue brief payload."""

    build_synthetic_candidate_research_brief = __import__
    research_queue_fixture_module = build_synthetic_candidate_research_brief(
        "tests.fixtures.research_queue_brief",
        fromlist=("expected_synthetic_research_queue_brief_dict",),
    )
    build_synthetic_candidate_research_brief = (
        research_queue_fixture_module.expected_synthetic_research_queue_brief_dict
    )
    return build_synthetic_candidate_research_brief()


def expected_synthetic_sma_research_observation_brief_dict() -> dict[str, object]:
    """Return the exact primitive Phase 202 SMA observation brief payload."""

    expected_synthetic_candidate_research_brief_dict = __import__
    sma_research_observation_fixture_module = (
        expected_synthetic_candidate_research_brief_dict(
            "tests.fixtures.sma_research_observation_brief_container",
            fromlist=("expected_synthetic_sma_research_observation_brief_dict",),
        )
    )
    expected_synthetic_candidate_research_brief_dict = (
        sma_research_observation_fixture_module.expected_synthetic_sma_research_observation_brief_dict
    )
    return expected_synthetic_candidate_research_brief_dict()


def expected_synthetic_research_return_observation_brief_dict() -> dict[str, object]:
    """Return the exact primitive Phase 216-219 return observation payload."""

    expected_synthetic_candidate_research_brief_dict = __import__
    research_return_observation_fixture_module = (
        expected_synthetic_candidate_research_brief_dict(
            "tests.fixtures.research_return_observation_brief_container",
            fromlist=("expected_synthetic_research_return_observation_brief_dict",),
        )
    )
    expected_synthetic_candidate_research_brief_dict = (
        research_return_observation_fixture_module.expected_synthetic_research_return_observation_brief_dict
    )
    return expected_synthetic_candidate_research_brief_dict()


def expected_synthetic_research_return_summary_observation_brief_dict() -> (
    dict[str, object]
):
    """Return the exact primitive Phase 226-230 return summary payload."""

    expected_synthetic_candidate_research_brief_dict = __import__
    research_return_summary_fixture_module = (
        expected_synthetic_candidate_research_brief_dict(
            "tests.fixtures.research_return_summary_observation",
            fromlist=(
                "expected_synthetic_research_return_summary_observation_brief_dict",
            ),
        )
    )
    expected_synthetic_candidate_research_brief_dict = (
        research_return_summary_fixture_module.expected_synthetic_research_return_summary_observation_brief_dict
    )
    return expected_synthetic_candidate_research_brief_dict()


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


def expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict() -> (
    dict[str, object]
):
    """Return the exact primitive research-queue-inclusive bundle payload."""

    candidate_brief = expected_synthetic_candidate_research_brief_dict()
    strategy_eligibility_brief = expected_synthetic_strategy_eligibility_brief_dict()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_risk_authority_brief_dict
    )
    risk_authority_brief = build_synthetic_candidate_research_brief()
    build_synthetic_strategy_eligibility_brief = (
        expected_synthetic_research_queue_brief_dict
    )
    research_queue_brief = build_synthetic_strategy_eligibility_brief()
    limitations = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "limitations",
        risk_authority_brief,
        research_queue_brief,
    )
    non_claims = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "non_claims",
        risk_authority_brief,
        research_queue_brief,
    )

    return {
        "bundle_type": "advisory_operating_brief_content_bundle",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY_WITH_RESEARCH_QUEUE,
        "candidate_research_brief_count": 1,
        "strategy_eligibility_brief_count": 1,
        "risk_authority_brief_count": 1,
        "research_queue_brief_count": 1,
        "candidate_research_briefs": [candidate_brief],
        "strategy_eligibility_briefs": [strategy_eligibility_brief],
        "risk_authority_briefs": [risk_authority_brief],
        "research_queue_briefs": [research_queue_brief],
        "limitations": limitations,
        "non_claims": non_claims,
    }


def expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive SMA-inclusive content bundle payload."""

    candidate_brief = expected_synthetic_candidate_research_brief_dict()
    strategy_eligibility_brief = expected_synthetic_strategy_eligibility_brief_dict()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_risk_authority_brief_dict
    )
    risk_authority_brief = build_synthetic_candidate_research_brief()
    build_synthetic_strategy_eligibility_brief = (
        expected_synthetic_research_queue_brief_dict
    )
    research_queue_brief = build_synthetic_strategy_eligibility_brief()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_sma_research_observation_brief_dict
    )
    sma_brief = build_synthetic_candidate_research_brief()
    limitations = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "limitations",
        risk_authority_brief,
        research_queue_brief,
        sma_brief,
    )
    non_claims = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "non_claims",
        risk_authority_brief,
        research_queue_brief,
        sma_brief,
    )

    return {
        "bundle_type": "advisory_operating_brief_content_bundle",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY_WITH_SMA_RESEARCH_OBSERVATION,
        "candidate_research_brief_count": 1,
        "strategy_eligibility_brief_count": 1,
        "risk_authority_brief_count": 1,
        "research_queue_brief_count": 1,
        "sma_research_observation_brief_count": 1,
        "candidate_research_briefs": [candidate_brief],
        "strategy_eligibility_briefs": [strategy_eligibility_brief],
        "risk_authority_briefs": [risk_authority_brief],
        "research_queue_briefs": [research_queue_brief],
        "sma_research_observation_briefs": [sma_brief],
        "limitations": limitations,
        "non_claims": non_claims,
    }


def expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive return-observation bundle payload."""

    candidate_brief = expected_synthetic_candidate_research_brief_dict()
    strategy_eligibility_brief = expected_synthetic_strategy_eligibility_brief_dict()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_risk_authority_brief_dict
    )
    risk_authority_brief = build_synthetic_candidate_research_brief()
    build_synthetic_strategy_eligibility_brief = (
        expected_synthetic_research_queue_brief_dict
    )
    research_queue_brief = build_synthetic_strategy_eligibility_brief()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_sma_research_observation_brief_dict
    )
    sma_brief = build_synthetic_candidate_research_brief()
    build_synthetic_strategy_eligibility_brief = (
        expected_synthetic_research_return_observation_brief_dict
    )
    research_return_brief = build_synthetic_strategy_eligibility_brief()
    limitations = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "limitations",
        risk_authority_brief,
        research_queue_brief,
        sma_brief,
        research_return_brief,
    )
    non_claims = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "non_claims",
        risk_authority_brief,
        research_queue_brief,
        sma_brief,
        research_return_brief,
    )

    return {
        "bundle_type": "advisory_operating_brief_content_bundle",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY_WITH_RESEARCH_RETURN_OBSERVATION,
        "candidate_research_brief_count": 1,
        "strategy_eligibility_brief_count": 1,
        "risk_authority_brief_count": 1,
        "research_queue_brief_count": 1,
        "sma_research_observation_brief_count": 1,
        "research_return_observation_brief_count": 1,
        "candidate_research_briefs": [candidate_brief],
        "strategy_eligibility_briefs": [strategy_eligibility_brief],
        "risk_authority_briefs": [risk_authority_brief],
        "research_queue_briefs": [research_queue_brief],
        "sma_research_observation_briefs": [sma_brief],
        "research_return_observation_briefs": [research_return_brief],
        "limitations": limitations,
        "non_claims": non_claims,
    }


def expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive return-summary bundle payload."""

    candidate_brief = expected_synthetic_candidate_research_brief_dict()
    strategy_eligibility_brief = expected_synthetic_strategy_eligibility_brief_dict()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_risk_authority_brief_dict
    )
    risk_authority_brief = build_synthetic_candidate_research_brief()
    build_synthetic_strategy_eligibility_brief = (
        expected_synthetic_research_queue_brief_dict
    )
    research_queue_brief = build_synthetic_strategy_eligibility_brief()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_sma_research_observation_brief_dict
    )
    sma_brief = build_synthetic_candidate_research_brief()
    build_synthetic_strategy_eligibility_brief = (
        expected_synthetic_research_return_observation_brief_dict
    )
    research_return_brief = build_synthetic_strategy_eligibility_brief()
    build_synthetic_candidate_research_brief = (
        expected_synthetic_research_return_summary_observation_brief_dict
    )
    research_return_summary_brief = build_synthetic_candidate_research_brief()
    limitations = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "limitations",
        risk_authority_brief,
        research_queue_brief,
        sma_brief,
        research_return_brief,
        research_return_summary_brief,
    )
    non_claims = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "non_claims",
        risk_authority_brief,
        research_queue_brief,
        sma_brief,
        research_return_brief,
        research_return_summary_brief,
    )

    return {
        "bundle_type": "advisory_operating_brief_content_bundle",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY_WITH_RESEARCH_RETURN_SUMMARY_OBSERVATION,
        "candidate_research_brief_count": 1,
        "strategy_eligibility_brief_count": 1,
        "risk_authority_brief_count": 1,
        "research_queue_brief_count": 1,
        "sma_research_observation_brief_count": 1,
        "research_return_observation_brief_count": 1,
        "research_return_summary_observation_brief_count": 1,
        "candidate_research_briefs": [candidate_brief],
        "strategy_eligibility_briefs": [strategy_eligibility_brief],
        "risk_authority_briefs": [risk_authority_brief],
        "research_queue_briefs": [research_queue_brief],
        "sma_research_observation_briefs": [sma_brief],
        "research_return_observation_briefs": [research_return_brief],
        "research_return_summary_observation_briefs": [
            research_return_summary_brief
        ],
        "limitations": limitations,
        "non_claims": non_claims,
    }


def expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_dict() -> (
    dict[str, object]
):
    """Return the exact primitive data-source-readiness bundle payload."""

    candidate_brief = expected_synthetic_candidate_research_brief_dict()
    strategy_eligibility_brief = expected_synthetic_strategy_eligibility_brief_dict()
    readiness = expected_synthetic_research_data_source_readiness_dict()
    limitations = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "limitations",
        readiness,
    )
    non_claims = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "non_claims",
        readiness,
    )

    return {
        "bundle_type": "advisory_operating_brief_content_bundle",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _TITLE,
        "summary": _SUMMARY_WITH_RESEARCH_DATA_SOURCE_READINESS,
        "candidate_research_brief_count": 1,
        "strategy_eligibility_brief_count": 1,
        "research_data_source_readiness_count": 1,
        "candidate_research_briefs": [candidate_brief],
        "strategy_eligibility_briefs": [strategy_eligibility_brief],
        "research_data_source_readiness": [readiness],
        "limitations": limitations,
        "non_claims": non_claims,
    }


def expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary_dict() -> (
    dict[str, object]
):
    """Return the exact primitive data-source summary bundle payload."""

    candidate_brief = expected_synthetic_candidate_research_brief_dict()
    strategy_eligibility_brief = expected_synthetic_strategy_eligibility_brief_dict()
    summary = expected_synthetic_research_data_source_readiness_summary_dict(
        build_research_data_source_readiness_summary
    )
    limitations = _combined_expected_values(
        candidate_brief,
        strategy_eligibility_brief,
        "limitations",
        {"limitations": summary["diagnostic_limitations"]},
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
        "summary": _SUMMARY_WITH_RESEARCH_DATA_SOURCE_READINESS_SUMMARY,
        "candidate_research_brief_count": 1,
        "strategy_eligibility_brief_count": 1,
        "research_data_source_readiness_summary_count": 1,
        "candidate_research_briefs": [candidate_brief],
        "strategy_eligibility_briefs": [strategy_eligibility_brief],
        "research_data_source_readiness_summaries": [summary],
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
