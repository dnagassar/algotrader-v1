"""Metadata-only bundle for advisory operating brief source content."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.candidate_research_brief import CandidateResearchBrief
from algotrader.research.research_return_observation_brief_container import (
    ResearchReturnObservationBrief,
)
from algotrader.research.research_return_summary_observation_brief import (
    ResearchReturnSummaryObservationBrief,
)
from algotrader.research.research_queue_brief import ResearchQueueBrief
from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
)
from algotrader.research.risk_authority_brief import RiskAuthorityBrief
from algotrader.research.sma_research_observation_brief_container import (
    SmaResearchObservationBrief,
)
from algotrader.research.sma_research_summary_observation import (
    SmaResearchSummaryObservation,
)
from algotrader.research.strategy_eligibility_brief import StrategyEligibilityBrief

__all__ = [
    "AdvisoryOperatingBriefContentBundle",
    "build_advisory_operating_brief_content_bundle",
]

_BUNDLE_TYPE = "advisory_operating_brief_content_bundle"
_CANDIDATE_BRIEF_TYPE = "candidate_research_brief"
_STRATEGY_ELIGIBILITY_BRIEF_TYPE = "strategy_eligibility_brief"
_RISK_AUTHORITY_BRIEF_TYPE = "risk_authority_brief"
_RESEARCH_QUEUE_BRIEF_TYPE = "research_queue_brief"
_RESEARCH_DATA_SOURCE_READINESS_TYPE = "research_data_source_readiness"
_SMA_RESEARCH_OBSERVATION_BRIEF_TYPE = "sma_research_observation_brief"
_SMA_RESEARCH_SUMMARY_OBSERVATION_TYPE = "sma_research_summary_observation"
_RESEARCH_RETURN_OBSERVATION_BRIEF_TYPE = "research_return_observation_brief"
_RESEARCH_RETURN_SUMMARY_OBSERVATION_BRIEF_TYPE = (
    "research_return_summary_observation_brief"
)
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_TITLE = "Advisory operating brief content bundle metadata"


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefContentBundle:
    """Advisory-only grouping for existing operating brief content families."""

    bundle_type: str
    status: str
    authority: str
    capital_authority: bool
    title: str
    summary: str
    candidate_research_briefs: tuple[CandidateResearchBrief, ...]
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...] = ()
    research_queue_briefs: tuple[ResearchQueueBrief, ...] = ()
    sma_research_observation_briefs: tuple[SmaResearchObservationBrief, ...] = ()
    research_return_observation_briefs: tuple[
        ResearchReturnObservationBrief, ...
    ] = ()
    research_return_summary_observation_briefs: tuple[
        ResearchReturnSummaryObservationBrief, ...
    ] = ()
    sma_research_summary_observations: tuple[SmaResearchSummaryObservation, ...] = ()
    research_data_source_readiness: tuple[ResearchDataSourceReadiness, ...] = ()

    def __post_init__(self) -> None:
        candidate_briefs = _candidate_research_briefs_tuple(
            self.candidate_research_briefs
        )
        eligibility_briefs = _strategy_eligibility_briefs_tuple(
            self.strategy_eligibility_briefs
        )
        risk_briefs = _risk_authority_briefs_tuple(self.risk_authority_briefs)
        research_queue_briefs = _research_queue_briefs_tuple(
            self.research_queue_briefs
        )
        sma_briefs = _sma_research_observation_briefs_tuple(
            self.sma_research_observation_briefs
        )
        research_return_briefs = _research_return_observation_briefs_tuple(
            self.research_return_observation_briefs
        )
        research_return_summary_briefs = (
            _research_return_summary_observation_briefs_tuple(
                self.research_return_summary_observation_briefs
            )
        )
        sma_summary_observations = _sma_research_summary_observations_tuple(
            self.sma_research_summary_observations
        )
        data_source_readiness = _research_data_source_readiness_tuple(
            self.research_data_source_readiness
        )
        _validate_non_empty_bundle(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs,
            sma_briefs,
            research_return_briefs,
            research_return_summary_briefs,
            sma_summary_observations,
            data_source_readiness,
        )
        _validate_unique_brief_identities(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs,
            sma_briefs,
            research_return_briefs,
            research_return_summary_briefs,
            sma_summary_observations,
            data_source_readiness,
        )

        limitations = _required_string_tuple(self.limitations, "limitations")
        non_claims = _required_string_tuple(self.non_claims, "non_claims")
        expected_limitations = _combined_brief_values(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs,
            sma_briefs,
            research_return_briefs,
            research_return_summary_briefs,
            sma_summary_observations,
            data_source_readiness,
            "limitations",
        )
        expected_non_claims = _combined_brief_values(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs,
            sma_briefs,
            research_return_briefs,
            research_return_summary_briefs,
            sma_summary_observations,
            data_source_readiness,
            "non_claims",
        )

        _validate_fixed_metadata(
            self.bundle_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        _validate_matches("title", _required_string(self.title, "title"), _title())
        _validate_matches(
            "summary",
            _required_string(self.summary, "summary"),
            _summary(
                candidate_briefs,
                eligibility_briefs,
                risk_briefs,
                research_queue_briefs,
                sma_briefs,
                research_return_briefs,
                research_return_summary_briefs,
                sma_summary_observations,
                data_source_readiness,
            ),
        )
        _validate_matches("limitations", limitations, expected_limitations)
        _validate_matches("non_claims", non_claims, expected_non_claims)

        object.__setattr__(self, "candidate_research_briefs", candidate_briefs)
        object.__setattr__(self, "strategy_eligibility_briefs", eligibility_briefs)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "non_claims", non_claims)
        object.__setattr__(self, "risk_authority_briefs", risk_briefs)
        object.__setattr__(self, "research_queue_briefs", research_queue_briefs)
        object.__setattr__(self, "sma_research_observation_briefs", sma_briefs)
        object.__setattr__(
            self,
            "research_return_observation_briefs",
            research_return_briefs,
        )
        object.__setattr__(
            self,
            "research_return_summary_observation_briefs",
            research_return_summary_briefs,
        )
        object.__setattr__(
            self,
            "sma_research_summary_observations",
            sma_summary_observations,
        )
        object.__setattr__(
            self,
            "research_data_source_readiness",
            data_source_readiness,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only bundle metadata."""

        payload: dict[str, object] = {
            "bundle_type": self.bundle_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "title": self.title,
            "summary": self.summary,
            "candidate_research_brief_count": len(self.candidate_research_briefs),
            "strategy_eligibility_brief_count": len(
                self.strategy_eligibility_briefs
            ),
        }
        if self.risk_authority_briefs:
            payload["risk_authority_brief_count"] = len(self.risk_authority_briefs)
        if self.research_queue_briefs:
            payload["research_queue_brief_count"] = len(self.research_queue_briefs)
        if self.sma_research_observation_briefs:
            payload["sma_research_observation_brief_count"] = len(
                self.sma_research_observation_briefs
            )
        if self.sma_research_summary_observations:
            payload["sma_research_summary_observation_count"] = len(
                self.sma_research_summary_observations
            )
        if self.research_return_observation_briefs:
            payload["research_return_observation_brief_count"] = len(
                self.research_return_observation_briefs
            )
        if self.research_return_summary_observation_briefs:
            payload["research_return_summary_observation_brief_count"] = len(
                self.research_return_summary_observation_briefs
            )
        if self.research_data_source_readiness:
            payload["research_data_source_readiness_count"] = len(
                self.research_data_source_readiness
            )

        payload["candidate_research_briefs"] = [
            brief.to_dict() for brief in self.candidate_research_briefs
        ]
        payload["strategy_eligibility_briefs"] = [
            brief.to_dict() for brief in self.strategy_eligibility_briefs
        ]
        if self.risk_authority_briefs:
            payload["risk_authority_briefs"] = [
                brief.to_dict() for brief in self.risk_authority_briefs
            ]
        if self.research_queue_briefs:
            payload["research_queue_briefs"] = [
                brief.to_dict() for brief in self.research_queue_briefs
            ]
        if self.sma_research_observation_briefs:
            payload["sma_research_observation_briefs"] = [
                brief.to_dict() for brief in self.sma_research_observation_briefs
            ]
        if self.sma_research_summary_observations:
            payload["sma_research_summary_observations"] = [
                observation.to_dict()
                for observation in self.sma_research_summary_observations
            ]
        if self.research_return_observation_briefs:
            payload["research_return_observation_briefs"] = [
                brief.to_dict() for brief in self.research_return_observation_briefs
            ]
        if self.research_return_summary_observation_briefs:
            payload["research_return_summary_observation_briefs"] = [
                brief.to_dict()
                for brief in self.research_return_summary_observation_briefs
            ]
        if self.research_data_source_readiness:
            payload["research_data_source_readiness"] = [
                readiness.to_dict()
                for readiness in self.research_data_source_readiness
            ]

        payload["limitations"] = list(self.limitations)
        payload["non_claims"] = list(self.non_claims)
        return payload


def build_advisory_operating_brief_content_bundle(
    candidate_research_briefs: Iterable[CandidateResearchBrief] = (),
    strategy_eligibility_briefs: Iterable[StrategyEligibilityBrief] = (),
    risk_authority_briefs: Iterable[RiskAuthorityBrief] = (),
    research_queue_briefs: Iterable[ResearchQueueBrief] = (),
    sma_research_observation_briefs: Iterable[SmaResearchObservationBrief] = (),
    research_return_observation_briefs: Iterable[
        ResearchReturnObservationBrief
    ] = (),
    research_return_summary_observation_briefs: Iterable[
        ResearchReturnSummaryObservationBrief
    ] = (),
    sma_research_summary_observations: Iterable[
        SmaResearchSummaryObservation
    ] = (),
    research_data_source_readiness: Iterable[ResearchDataSourceReadiness] = (),
) -> AdvisoryOperatingBriefContentBundle:
    """Build a deterministic advisory-only content bundle from existing briefs."""

    candidate_briefs = _candidate_research_briefs_tuple(candidate_research_briefs)
    eligibility_briefs = _strategy_eligibility_briefs_tuple(
        strategy_eligibility_briefs
    )
    risk_briefs = _risk_authority_briefs_tuple(risk_authority_briefs)
    research_queue_briefs_tuple = _research_queue_briefs_tuple(research_queue_briefs)
    sma_briefs = _sma_research_observation_briefs_tuple(
        sma_research_observation_briefs
    )
    research_return_briefs = _research_return_observation_briefs_tuple(
        research_return_observation_briefs
    )
    research_return_summary_briefs = _research_return_summary_observation_briefs_tuple(
        research_return_summary_observation_briefs
    )
    sma_summary_observations = _sma_research_summary_observations_tuple(
        sma_research_summary_observations
    )
    data_source_readiness = _research_data_source_readiness_tuple(
        research_data_source_readiness
    )
    _validate_non_empty_bundle(
        candidate_briefs,
        eligibility_briefs,
        risk_briefs,
        research_queue_briefs_tuple,
        sma_briefs,
        research_return_briefs,
        research_return_summary_briefs,
        sma_summary_observations,
        data_source_readiness,
    )
    _validate_unique_brief_identities(
        candidate_briefs,
        eligibility_briefs,
        risk_briefs,
        research_queue_briefs_tuple,
        sma_briefs,
        research_return_briefs,
        research_return_summary_briefs,
        sma_summary_observations,
        data_source_readiness,
    )

    return AdvisoryOperatingBriefContentBundle(
        bundle_type=_BUNDLE_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        title=_title(),
        summary=_summary(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs_tuple,
            sma_briefs,
            research_return_briefs,
            research_return_summary_briefs,
            sma_summary_observations,
            data_source_readiness,
        ),
        candidate_research_briefs=candidate_briefs,
        strategy_eligibility_briefs=eligibility_briefs,
        limitations=_combined_brief_values(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs_tuple,
            sma_briefs,
            research_return_briefs,
            research_return_summary_briefs,
            sma_summary_observations,
            data_source_readiness,
            "limitations",
        ),
        non_claims=_combined_brief_values(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs_tuple,
            sma_briefs,
            research_return_briefs,
            research_return_summary_briefs,
            sma_summary_observations,
            data_source_readiness,
            "non_claims",
        ),
        risk_authority_briefs=risk_briefs,
        research_queue_briefs=research_queue_briefs_tuple,
        sma_research_observation_briefs=sma_briefs,
        research_return_observation_briefs=research_return_briefs,
        research_return_summary_observation_briefs=research_return_summary_briefs,
        sma_research_summary_observations=sma_summary_observations,
        research_data_source_readiness=data_source_readiness,
    )


def _title() -> str:
    return _TITLE


def _summary(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
    research_queue_briefs: tuple[ResearchQueueBrief, ...],
    sma_research_observation_briefs: tuple[SmaResearchObservationBrief, ...],
    research_return_observation_briefs: tuple[ResearchReturnObservationBrief, ...],
    research_return_summary_observation_briefs: tuple[
        ResearchReturnSummaryObservationBrief, ...
    ],
    sma_research_summary_observations: tuple[SmaResearchSummaryObservation, ...],
    research_data_source_readiness: tuple[ResearchDataSourceReadiness, ...],
) -> str:
    limitations = _combined_brief_values(
        candidate_research_briefs,
        strategy_eligibility_briefs,
        risk_authority_briefs,
        research_queue_briefs,
        sma_research_observation_briefs,
        research_return_observation_briefs,
        research_return_summary_observation_briefs,
        sma_research_summary_observations,
        research_data_source_readiness,
        "limitations",
    )
    non_claims = _combined_brief_values(
        candidate_research_briefs,
        strategy_eligibility_briefs,
        risk_authority_briefs,
        research_queue_briefs,
        sma_research_observation_briefs,
        research_return_observation_briefs,
        research_return_summary_observation_briefs,
        sma_research_summary_observations,
        research_data_source_readiness,
        "non_claims",
    )
    risk_clause = (
        f"{len(risk_authority_briefs)} risk authority brief(s), "
        if risk_authority_briefs
        else ""
    )
    research_queue_clause = (
        f"{len(research_queue_briefs)} research queue brief(s), "
        if research_queue_briefs
        else ""
    )
    sma_clause = (
        f"{len(sma_research_observation_briefs)} SMA research observation brief(s), "
        if sma_research_observation_briefs
        else ""
    )
    sma_summary_clause = (
        f"{len(sma_research_summary_observations)} SMA research summary "
        "observation(s), "
        if sma_research_summary_observations
        else ""
    )
    research_return_clause = (
        f"{len(research_return_observation_briefs)} research return observation "
        "brief(s), "
        if research_return_observation_briefs
        else ""
    )
    research_return_summary_clause = (
        f"{len(research_return_summary_observation_briefs)} research return "
        "summary observation brief(s), "
        if research_return_summary_observation_briefs
        else ""
    )
    data_source_readiness_clause = (
        f"{len(research_data_source_readiness)} research data source readiness "
        "diagnostic(s), "
        if research_data_source_readiness
        else ""
    )
    return (
        "Advisory content bundle contains "
        f"{len(candidate_research_briefs)} candidate research brief(s), "
        f"{len(strategy_eligibility_briefs)} strategy eligibility brief(s), "
        f"{risk_clause}{research_queue_clause}{sma_clause}{sma_summary_clause}"
        f"{research_return_clause}{research_return_summary_clause}"
        f"{data_source_readiness_clause}"
        f"{len(limitations)} limitation(s), and "
        f"{len(non_claims)} non-claim(s)."
    )


def _candidate_research_briefs_tuple(
    values: Iterable[CandidateResearchBrief],
) -> tuple[CandidateResearchBrief, ...]:
    try:
        briefs = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "candidate_research_briefs must be an iterable of CandidateResearchBrief."
        ) from exc

    for index, brief in enumerate(briefs):
        if type(brief) is not CandidateResearchBrief:
            raise ValidationError(
                f"candidate_research_briefs[{index}] must be a CandidateResearchBrief."
            )
        if brief.brief_type != _CANDIDATE_BRIEF_TYPE:
            raise ValidationError(
                f"candidate_research_briefs[{index}] brief_type must be exactly "
                "candidate_research_brief."
            )
        if brief.status != _STATUS:
            raise ValidationError(
                f"candidate_research_briefs[{index}] status must be exactly "
                "candidate_only."
            )

    return briefs


def _strategy_eligibility_briefs_tuple(
    values: Iterable[StrategyEligibilityBrief],
) -> tuple[StrategyEligibilityBrief, ...]:
    try:
        briefs = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "strategy_eligibility_briefs must be an iterable of "
            "StrategyEligibilityBrief."
        ) from exc

    for index, brief in enumerate(briefs):
        if type(brief) is not StrategyEligibilityBrief:
            raise ValidationError(
                f"strategy_eligibility_briefs[{index}] must be a "
                "StrategyEligibilityBrief."
            )
        if brief.brief_type != _STRATEGY_ELIGIBILITY_BRIEF_TYPE:
            raise ValidationError(
                f"strategy_eligibility_briefs[{index}] brief_type must be exactly "
                "strategy_eligibility_brief."
            )
        if brief.status != _STATUS:
            raise ValidationError(
                f"strategy_eligibility_briefs[{index}] status must be exactly "
                "candidate_only."
            )
        if brief.authority != _AUTHORITY:
            raise ValidationError(
                f"strategy_eligibility_briefs[{index}] authority must be exactly "
                "advisory_only."
            )
        if brief.capital_authority is not _CAPITAL_AUTHORITY:
            raise ValidationError(
                f"strategy_eligibility_briefs[{index}] capital_authority must be "
                "False."
            )

    return briefs


def _risk_authority_briefs_tuple(
    values: Iterable[RiskAuthorityBrief],
) -> tuple[RiskAuthorityBrief, ...]:
    try:
        briefs = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "risk_authority_briefs must be an iterable of RiskAuthorityBrief."
        ) from exc

    for index, brief in enumerate(briefs):
        if type(brief) is not RiskAuthorityBrief:
            raise ValidationError(
                f"risk_authority_briefs[{index}] must be a RiskAuthorityBrief."
            )
        if brief.brief_type != _RISK_AUTHORITY_BRIEF_TYPE:
            raise ValidationError(
                f"risk_authority_briefs[{index}] brief_type must be exactly "
                "risk_authority_brief."
            )
        if brief.status != _STATUS:
            raise ValidationError(
                f"risk_authority_briefs[{index}] status must be exactly "
                "candidate_only."
            )
        if brief.authority != _AUTHORITY:
            raise ValidationError(
                f"risk_authority_briefs[{index}] authority must be exactly "
                "advisory_only."
            )
        if brief.capital_authority is not _CAPITAL_AUTHORITY:
            raise ValidationError(
                f"risk_authority_briefs[{index}] capital_authority must be False."
            )

    return briefs


def _research_queue_briefs_tuple(
    values: Iterable[ResearchQueueBrief],
) -> tuple[ResearchQueueBrief, ...]:
    try:
        briefs = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "research_queue_briefs must be an iterable of ResearchQueueBrief."
        ) from exc

    for index, brief in enumerate(briefs):
        if type(brief) is not ResearchQueueBrief:
            raise ValidationError(
                f"research_queue_briefs[{index}] must be a ResearchQueueBrief."
            )
        if brief.brief_type != _RESEARCH_QUEUE_BRIEF_TYPE:
            raise ValidationError(
                f"research_queue_briefs[{index}] brief_type must be exactly "
                "research_queue_brief."
            )
        if brief.status != _STATUS:
            raise ValidationError(
                f"research_queue_briefs[{index}] status must be exactly "
                "candidate_only."
            )
        if brief.authority != _AUTHORITY:
            raise ValidationError(
                f"research_queue_briefs[{index}] authority must be exactly "
                "advisory_only."
            )
        if brief.capital_authority is not _CAPITAL_AUTHORITY:
            raise ValidationError(
                f"research_queue_briefs[{index}] capital_authority must be False."
            )

    return briefs


def _sma_research_observation_briefs_tuple(
    values: Iterable[SmaResearchObservationBrief],
) -> tuple[SmaResearchObservationBrief, ...]:
    try:
        briefs = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "sma_research_observation_briefs must be an iterable of "
            "SmaResearchObservationBrief."
        ) from exc

    for index, brief in enumerate(briefs):
        if type(brief) is not SmaResearchObservationBrief:
            raise ValidationError(
                f"sma_research_observation_briefs[{index}] must be a "
                "SmaResearchObservationBrief."
            )
        if brief.brief_type != _SMA_RESEARCH_OBSERVATION_BRIEF_TYPE:
            raise ValidationError(
                f"sma_research_observation_briefs[{index}] brief_type must be "
                "exactly sma_research_observation_brief."
            )
        if brief.status != _STATUS:
            raise ValidationError(
                f"sma_research_observation_briefs[{index}] status must be exactly "
                "candidate_only."
            )
        if brief.authority != _AUTHORITY:
            raise ValidationError(
                f"sma_research_observation_briefs[{index}] authority must be exactly "
                "advisory_only."
            )
        if brief.capital_authority is not _CAPITAL_AUTHORITY:
            raise ValidationError(
                f"sma_research_observation_briefs[{index}] capital_authority must be "
                "False."
            )

    return briefs


def _research_return_observation_briefs_tuple(
    values: Iterable[ResearchReturnObservationBrief],
) -> tuple[ResearchReturnObservationBrief, ...]:
    try:
        briefs = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "research_return_observation_briefs must be an iterable of "
            "ResearchReturnObservationBrief."
        ) from exc

    for index, brief in enumerate(briefs):
        if type(brief) is not ResearchReturnObservationBrief:
            raise ValidationError(
                f"research_return_observation_briefs[{index}] must be a "
                "ResearchReturnObservationBrief."
            )
        if brief.brief_type != _RESEARCH_RETURN_OBSERVATION_BRIEF_TYPE:
            raise ValidationError(
                f"research_return_observation_briefs[{index}] brief_type must be "
                "exactly research_return_observation_brief."
            )
        if brief.status != _STATUS:
            raise ValidationError(
                f"research_return_observation_briefs[{index}] status must be "
                "exactly candidate_only."
            )
        if brief.authority != _AUTHORITY:
            raise ValidationError(
                f"research_return_observation_briefs[{index}] authority must be "
                "exactly advisory_only."
            )
        if brief.capital_authority is not _CAPITAL_AUTHORITY:
            raise ValidationError(
                f"research_return_observation_briefs[{index}] capital_authority "
                "must be False."
            )

    return briefs


def _research_return_summary_observation_briefs_tuple(
    values: Iterable[ResearchReturnSummaryObservationBrief],
) -> tuple[ResearchReturnSummaryObservationBrief, ...]:
    try:
        briefs = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "research_return_summary_observation_briefs must be an iterable of "
            "ResearchReturnSummaryObservationBrief."
        ) from exc

    for index, brief in enumerate(briefs):
        if type(brief) is not ResearchReturnSummaryObservationBrief:
            raise ValidationError(
                f"research_return_summary_observation_briefs[{index}] must be a "
                "ResearchReturnSummaryObservationBrief."
            )
        if brief.brief_type != _RESEARCH_RETURN_SUMMARY_OBSERVATION_BRIEF_TYPE:
            raise ValidationError(
                f"research_return_summary_observation_briefs[{index}] brief_type "
                "must be exactly research_return_summary_observation_brief."
            )
        if brief.status != _STATUS:
            raise ValidationError(
                f"research_return_summary_observation_briefs[{index}] status must "
                "be exactly candidate_only."
            )
        if brief.authority != _AUTHORITY:
            raise ValidationError(
                f"research_return_summary_observation_briefs[{index}] authority "
                "must be exactly advisory_only."
            )
        if brief.capital_authority is not _CAPITAL_AUTHORITY:
            raise ValidationError(
                f"research_return_summary_observation_briefs[{index}] "
                "capital_authority must be False."
            )

    return briefs


def _sma_research_summary_observations_tuple(
    values: Iterable[SmaResearchSummaryObservation],
) -> tuple[SmaResearchSummaryObservation, ...]:
    try:
        observations = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "sma_research_summary_observations must be an iterable of "
            "SmaResearchSummaryObservation."
        ) from exc

    for index, observation in enumerate(observations):
        if type(observation) is not SmaResearchSummaryObservation:
            raise ValidationError(
                f"sma_research_summary_observations[{index}] must be a "
                "SmaResearchSummaryObservation."
            )
        if observation.observation_type != _SMA_RESEARCH_SUMMARY_OBSERVATION_TYPE:
            raise ValidationError(
                f"sma_research_summary_observations[{index}] observation_type must "
                "be exactly sma_research_summary_observation."
            )
        if observation.status != _STATUS:
            raise ValidationError(
                f"sma_research_summary_observations[{index}] status must be exactly "
                "candidate_only."
            )
        if observation.authority != _AUTHORITY:
            raise ValidationError(
                f"sma_research_summary_observations[{index}] authority must be "
                "exactly advisory_only."
            )
        if observation.capital_authority is not _CAPITAL_AUTHORITY:
            raise ValidationError(
                f"sma_research_summary_observations[{index}] capital_authority must "
                "be False."
            )
        if observation.research_scope != _RESEARCH_SCOPE:
            raise ValidationError(
                f"sma_research_summary_observations[{index}] research_scope must be "
                "exactly research_only."
            )

    return observations


def _research_data_source_readiness_tuple(
    values: Iterable[ResearchDataSourceReadiness],
) -> tuple[ResearchDataSourceReadiness, ...]:
    try:
        readiness_items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "research_data_source_readiness must be an iterable of "
            "ResearchDataSourceReadiness."
        ) from exc

    for index, readiness in enumerate(readiness_items):
        if type(readiness) is not ResearchDataSourceReadiness:
            raise ValidationError(
                "research_data_source_readiness"
                f"[{index}] must be a ResearchDataSourceReadiness."
            )
        if readiness.contract_type != _RESEARCH_DATA_SOURCE_READINESS_TYPE:
            raise ValidationError(
                "research_data_source_readiness"
                f"[{index}] contract_type must be exactly "
                "research_data_source_readiness."
            )
        if readiness.readiness_state != _STATUS:
            raise ValidationError(
                "research_data_source_readiness"
                f"[{index}] readiness_state must be exactly candidate_only."
            )
        if not readiness.missing_controls:
            raise ValidationError(
                "research_data_source_readiness"
                f"[{index}] must report at least one missing control."
            )

    return readiness_items


def _validate_non_empty_bundle(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
    research_queue_briefs: tuple[ResearchQueueBrief, ...],
    sma_research_observation_briefs: tuple[SmaResearchObservationBrief, ...],
    research_return_observation_briefs: tuple[ResearchReturnObservationBrief, ...],
    research_return_summary_observation_briefs: tuple[
        ResearchReturnSummaryObservationBrief, ...
    ],
    sma_research_summary_observations: tuple[
        SmaResearchSummaryObservation, ...
    ] = (),
    research_data_source_readiness: tuple[ResearchDataSourceReadiness, ...] = (),
) -> None:
    if (
        not candidate_research_briefs
        and not strategy_eligibility_briefs
        and not risk_authority_briefs
        and not research_queue_briefs
        and not sma_research_observation_briefs
        and not research_return_observation_briefs
        and not research_return_summary_observation_briefs
        and not sma_research_summary_observations
        and not research_data_source_readiness
    ):
        raise ValidationError(
            "content bundle must contain at least one supported brief."
        )


def _validate_unique_brief_identities(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
    research_queue_briefs: tuple[ResearchQueueBrief, ...],
    sma_research_observation_briefs: tuple[SmaResearchObservationBrief, ...],
    research_return_observation_briefs: tuple[ResearchReturnObservationBrief, ...],
    research_return_summary_observation_briefs: tuple[
        ResearchReturnSummaryObservationBrief, ...
    ],
    sma_research_summary_observations: tuple[
        SmaResearchSummaryObservation, ...
    ] = (),
    research_data_source_readiness: tuple[ResearchDataSourceReadiness, ...] = (),
) -> None:
    seen_identities: set[int] = set()
    for brief in (
        *candidate_research_briefs,
        *strategy_eligibility_briefs,
        *risk_authority_briefs,
        *research_queue_briefs,
        *sma_research_observation_briefs,
        *research_return_observation_briefs,
        *research_return_summary_observation_briefs,
        *sma_research_summary_observations,
        *research_data_source_readiness,
    ):
        brief_identity = id(brief)
        if brief_identity in seen_identities:
            raise ValidationError(
                "content bundle must not contain duplicate brief identities."
            )
        seen_identities.add(brief_identity)


def _combined_brief_values(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
    research_queue_briefs: tuple[ResearchQueueBrief, ...],
    sma_research_observation_briefs: tuple[SmaResearchObservationBrief, ...],
    research_return_observation_briefs: tuple[ResearchReturnObservationBrief, ...],
    research_return_summary_observation_briefs: tuple[
        ResearchReturnSummaryObservationBrief, ...
    ],
    sma_research_summary_observations: tuple[SmaResearchSummaryObservation, ...],
    research_data_source_readiness: tuple[ResearchDataSourceReadiness, ...],
    field_name: str,
) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for brief in (
        *candidate_research_briefs,
        *strategy_eligibility_briefs,
        *risk_authority_briefs,
        *research_queue_briefs,
        *sma_research_observation_briefs,
        *research_return_observation_briefs,
        *research_return_summary_observation_briefs,
        *sma_research_summary_observations,
        *research_data_source_readiness,
    ):
        for value in getattr(brief, field_name):
            if value in seen:
                continue
            values.append(value)
            seen.add(value)

    return tuple(values)


def _validate_fixed_metadata(
    bundle_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if bundle_type != _BUNDLE_TYPE:
        raise ValidationError(
            "bundle_type must be exactly advisory_operating_brief_content_bundle."
        )
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _required_string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _validate_matches(
    field_name: str,
    value: object,
    expected: object,
) -> None:
    if value != expected:
        raise ValidationError(f"{field_name} must match source brief metadata.")
