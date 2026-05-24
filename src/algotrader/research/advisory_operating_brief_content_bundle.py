"""Metadata-only bundle for advisory operating brief source content."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.candidate_research_brief import CandidateResearchBrief
from algotrader.research.research_queue_brief import ResearchQueueBrief
from algotrader.research.risk_authority_brief import RiskAuthorityBrief
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
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
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
        _validate_non_empty_bundle(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs,
        )
        _validate_unique_brief_identities(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs,
        )

        limitations = _required_string_tuple(self.limitations, "limitations")
        non_claims = _required_string_tuple(self.non_claims, "non_claims")
        expected_limitations = _combined_brief_values(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs,
            "limitations",
        )
        expected_non_claims = _combined_brief_values(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs,
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

        payload["limitations"] = list(self.limitations)
        payload["non_claims"] = list(self.non_claims)
        return payload


def build_advisory_operating_brief_content_bundle(
    candidate_research_briefs: Iterable[CandidateResearchBrief] = (),
    strategy_eligibility_briefs: Iterable[StrategyEligibilityBrief] = (),
    risk_authority_briefs: Iterable[RiskAuthorityBrief] = (),
    research_queue_briefs: Iterable[ResearchQueueBrief] = (),
) -> AdvisoryOperatingBriefContentBundle:
    """Build a deterministic advisory-only content bundle from existing briefs."""

    candidate_briefs = _candidate_research_briefs_tuple(candidate_research_briefs)
    eligibility_briefs = _strategy_eligibility_briefs_tuple(
        strategy_eligibility_briefs
    )
    risk_briefs = _risk_authority_briefs_tuple(risk_authority_briefs)
    research_queue_briefs_tuple = _research_queue_briefs_tuple(research_queue_briefs)
    _validate_non_empty_bundle(
        candidate_briefs,
        eligibility_briefs,
        risk_briefs,
        research_queue_briefs_tuple,
    )
    _validate_unique_brief_identities(
        candidate_briefs,
        eligibility_briefs,
        risk_briefs,
        research_queue_briefs_tuple,
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
        ),
        candidate_research_briefs=candidate_briefs,
        strategy_eligibility_briefs=eligibility_briefs,
        limitations=_combined_brief_values(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs_tuple,
            "limitations",
        ),
        non_claims=_combined_brief_values(
            candidate_briefs,
            eligibility_briefs,
            risk_briefs,
            research_queue_briefs_tuple,
            "non_claims",
        ),
        risk_authority_briefs=risk_briefs,
        research_queue_briefs=research_queue_briefs_tuple,
    )


def _title() -> str:
    return _TITLE


def _summary(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
    research_queue_briefs: tuple[ResearchQueueBrief, ...],
) -> str:
    limitations = _combined_brief_values(
        candidate_research_briefs,
        strategy_eligibility_briefs,
        risk_authority_briefs,
        research_queue_briefs,
        "limitations",
    )
    non_claims = _combined_brief_values(
        candidate_research_briefs,
        strategy_eligibility_briefs,
        risk_authority_briefs,
        research_queue_briefs,
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
    return (
        "Advisory content bundle contains "
        f"{len(candidate_research_briefs)} candidate research brief(s), "
        f"{len(strategy_eligibility_briefs)} strategy eligibility brief(s), "
        f"{risk_clause}{research_queue_clause}{len(limitations)} limitation(s), and "
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


def _validate_non_empty_bundle(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
    research_queue_briefs: tuple[ResearchQueueBrief, ...],
) -> None:
    if (
        not candidate_research_briefs
        and not strategy_eligibility_briefs
        and not risk_authority_briefs
        and not research_queue_briefs
    ):
        raise ValidationError(
            "content bundle must contain at least one supported brief."
        )


def _validate_unique_brief_identities(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
    research_queue_briefs: tuple[ResearchQueueBrief, ...],
) -> None:
    seen_identities: set[int] = set()
    for brief in (
        *candidate_research_briefs,
        *strategy_eligibility_briefs,
        *risk_authority_briefs,
        *research_queue_briefs,
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
    field_name: str,
) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for brief in (
        *candidate_research_briefs,
        *strategy_eligibility_briefs,
        *risk_authority_briefs,
        *research_queue_briefs,
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
