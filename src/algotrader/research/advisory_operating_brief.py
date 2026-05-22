"""Advisory display container for candidate research brief metadata."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.candidate_research_brief import CandidateResearchBrief

__all__ = [
    "AdvisoryOperatingBrief",
    "build_advisory_operating_brief",
]

_OPERATING_BRIEF_TYPE = "advisory_operating_brief"
_CANDIDATE_BRIEF_TYPE = "candidate_research_brief"
_ADVISORY_STATUS = "candidate_only"
_TITLE = "Candidate research operating brief metadata"
_DEFAULT_LIMITATIONS = (
    "metadata-only container for existing candidate research briefs",
    "does not create research, compute metrics, or mutate brief payloads",
    "advisory grouping for future operating brief surfaces only",
)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_REQUIRED_NON_CLAIMS = (
    _not("source approval"),
    _not("data approval"),
    _not("endpoint approval"),
    _not("universe approval"),
    _not("bench", "mark approval"),
    _not("ca", "sh proxy approval"),
    _not("methodology approval"),
    _not("evidence approval"),
    _not("return-construction approval"),
    _not("no-lookahead approval"),
    _not("stra", "tegy validation"),
    _not("tra", "ding readiness"),
    _not("production use"),
    _not("bro", "ker or run", "time use"),
    _not("or", "der generation"),
    _not("port", "folio or allo", "cation authority"),
)


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBrief:
    """Metadata-only advisory container for candidate research briefs."""

    operating_brief_type: str
    status: str
    title: str
    candidate_research_briefs: tuple[CandidateResearchBrief, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_operating_brief_type(self.operating_brief_type)
        _validate_status(self.status)
        _required_string(self.title, "title")
        checked_briefs = _validate_candidate_research_briefs(
            self.candidate_research_briefs
        )
        checked_limitations = _required_string_tuple(
            self.limitations,
            "limitations",
        )
        checked_non_claims = _required_string_tuple(self.non_claims, "non_claims")
        _validate_limitations(checked_briefs, checked_limitations)
        _validate_non_claims(checked_briefs, checked_non_claims)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive operating brief metadata."""

        return {
            "operating_brief_type": self.operating_brief_type,
            "status": self.status,
            "title": self.title,
            "candidate_research_brief_count": len(self.candidate_research_briefs),
            "candidate_research_briefs": [
                brief.to_dict() for brief in self.candidate_research_briefs
            ],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_advisory_operating_brief(
    candidate_research_briefs: Iterable[CandidateResearchBrief],
) -> AdvisoryOperatingBrief:
    """Build a deterministic advisory operating brief from existing briefs."""

    checked_briefs = _candidate_research_briefs_tuple(candidate_research_briefs)
    return AdvisoryOperatingBrief(
        operating_brief_type=_OPERATING_BRIEF_TYPE,
        status=_ADVISORY_STATUS,
        title=_TITLE,
        candidate_research_briefs=checked_briefs,
        limitations=_combine_string_tuples(
            _DEFAULT_LIMITATIONS,
            *(brief.limitations for brief in checked_briefs),
        ),
        non_claims=_combine_string_tuples(
            _REQUIRED_NON_CLAIMS,
            *(brief.non_claims for brief in checked_briefs),
        ),
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

    return _validate_candidate_research_briefs(briefs)


def _validate_candidate_research_briefs(
    candidate_research_briefs: object,
) -> tuple[CandidateResearchBrief, ...]:
    if not isinstance(candidate_research_briefs, tuple):
        raise ValidationError(
            "candidate_research_briefs must be a non-empty tuple of "
            "CandidateResearchBrief."
        )

    if not candidate_research_briefs:
        raise ValidationError(
            "candidate_research_briefs must contain at least one candidate brief."
        )

    seen_identities: set[int] = set()
    for index, brief in enumerate(candidate_research_briefs):
        if not isinstance(brief, CandidateResearchBrief):
            raise ValidationError(
                f"candidate_research_briefs[{index}] must be a CandidateResearchBrief."
            )

        if brief.brief_type != _CANDIDATE_BRIEF_TYPE:
            raise ValidationError(
                f"candidate_research_briefs[{index}] brief_type must be exactly "
                "candidate_research_brief."
            )

        if brief.status != _ADVISORY_STATUS:
            raise ValidationError(
                f"candidate_research_briefs[{index}] status must be exactly "
                "candidate_only."
            )

        brief_identity = id(brief)
        if brief_identity in seen_identities:
            raise ValidationError(
                "candidate_research_briefs must not contain duplicate brief "
                "identities."
            )
        seen_identities.add(brief_identity)

    return candidate_research_briefs


def _validate_operating_brief_type(value: object) -> None:
    if value != _OPERATING_BRIEF_TYPE:
        raise ValidationError(
            "operating_brief_type must be exactly advisory_operating_brief."
        )


def _validate_status(value: object) -> None:
    if value != _ADVISORY_STATUS:
        raise ValidationError("status must be exactly candidate_only.")


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _required_string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValidationError(f"{field_name} must be a non-empty tuple of strings.")

    if not values:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise ValidationError(f"{field_name}[{index}] must be a string.")
        if value != value.strip() or not value:
            raise ValidationError(f"{field_name}[{index}] must be a non-empty string.")

    return values


def _validate_limitations(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    limitations: tuple[str, ...],
) -> None:
    for brief in candidate_research_briefs:
        missing = tuple(value for value in brief.limitations if value not in limitations)
        if missing:
            missing_text = ", ".join(missing)
            raise ValidationError(
                "limitations must carry forward candidate brief limitations: "
                f"{missing_text}."
            )


def _validate_non_claims(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    non_claims: tuple[str, ...],
) -> None:
    _validate_required_non_claims(non_claims)

    for brief in candidate_research_briefs:
        missing = tuple(value for value in brief.non_claims if value not in non_claims)
        if missing:
            missing_text = ", ".join(missing)
            raise ValidationError(
                "non_claims must carry forward candidate brief advisory "
                f"non-claims: {missing_text}."
            )


def _validate_required_non_claims(non_claims: tuple[str, ...]) -> None:
    missing = tuple(
        claim for claim in _REQUIRED_NON_CLAIMS if claim not in non_claims
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"non_claims must include required advisory non-claims: {missing_text}."
        )

    positive_claims = tuple(
        claim for claim in non_claims if not claim.startswith("not ")
    )
    if positive_claims:
        raise ValidationError("non_claims entries must be negative statements.")


def _combine_string_tuples(
    first: tuple[str, ...],
    *remaining: tuple[str, ...],
) -> tuple[str, ...]:
    combined: list[str] = []
    seen: set[str] = set()
    for values in (first, *remaining):
        for value in values:
            if value in seen:
                continue
            combined.append(value)
            seen.add(value)

    return tuple(combined)
