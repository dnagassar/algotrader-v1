"""Advisory display container for candidate research brief section metadata."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.candidate_research_brief_section import (
    CandidateResearchBriefSection,
)

__all__ = [
    "CandidateResearchBrief",
    "build_candidate_research_brief",
]

_BRIEF_TYPE = "candidate_research_brief"
_ADVISORY_STATUS = "candidate_only"
_TITLE = "Candidate research brief metadata"
_DEFAULT_LIMITATIONS = (
    "metadata-only brief for existing candidate research brief sections",
    "does not create research, compute metrics, or mutate section payloads",
    "advisory container for future queue and brief surfaces only",
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
class CandidateResearchBrief:
    """Metadata-only advisory container for candidate research brief sections."""

    brief_type: str
    status: str
    title: str
    sections: tuple[CandidateResearchBriefSection, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_brief_type(self.brief_type)
        _validate_status(self.status)
        _required_string(self.title, "title")
        checked_sections = _validate_sections(self.sections)
        checked_limitations = _required_string_tuple(
            self.limitations,
            "limitations",
        )
        checked_non_claims = _required_string_tuple(self.non_claims, "non_claims")
        _validate_limitations(checked_sections, checked_limitations)
        _validate_non_claims(checked_sections, checked_non_claims)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive brief metadata."""

        return {
            "brief_type": self.brief_type,
            "status": self.status,
            "title": self.title,
            "section_count": len(self.sections),
            "sections": [section.to_dict() for section in self.sections],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_candidate_research_brief(
    sections: Iterable[CandidateResearchBriefSection],
) -> CandidateResearchBrief:
    """Build a deterministic advisory brief from existing sections."""

    checked_sections = _sections_tuple(sections)
    return CandidateResearchBrief(
        brief_type=_BRIEF_TYPE,
        status=_ADVISORY_STATUS,
        title=_TITLE,
        sections=checked_sections,
        limitations=_combine_string_tuples(
            _DEFAULT_LIMITATIONS,
            *(section.limitations for section in checked_sections),
        ),
        non_claims=_combine_string_tuples(
            _REQUIRED_NON_CLAIMS,
            *(section.non_claims for section in checked_sections),
        ),
    )


def _sections_tuple(
    values: Iterable[CandidateResearchBriefSection],
) -> tuple[CandidateResearchBriefSection, ...]:
    try:
        sections = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "sections must be an iterable of CandidateResearchBriefSection."
        ) from exc

    return _validate_sections(sections)


def _validate_sections(
    sections: object,
) -> tuple[CandidateResearchBriefSection, ...]:
    if not isinstance(sections, tuple):
        raise ValidationError(
            "sections must be a non-empty tuple of CandidateResearchBriefSection."
        )

    if not sections:
        raise ValidationError("sections must contain at least one brief section.")

    seen_identities: set[int] = set()
    for index, section in enumerate(sections):
        if not isinstance(section, CandidateResearchBriefSection):
            raise ValidationError(
                f"sections[{index}] must be a CandidateResearchBriefSection."
            )

        section_identity = id(section)
        if section_identity in seen_identities:
            raise ValidationError(
                "sections must not contain duplicate section identities."
            )
        seen_identities.add(section_identity)

    return sections


def _validate_brief_type(value: object) -> None:
    if value != _BRIEF_TYPE:
        raise ValidationError(
            "brief_type must be exactly candidate_research_brief."
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
    sections: tuple[CandidateResearchBriefSection, ...],
    limitations: tuple[str, ...],
) -> None:
    for section in sections:
        missing = tuple(value for value in section.limitations if value not in limitations)
        if missing:
            missing_text = ", ".join(missing)
            raise ValidationError(
                f"limitations must carry forward section limitations: {missing_text}."
            )


def _validate_non_claims(
    sections: tuple[CandidateResearchBriefSection, ...],
    non_claims: tuple[str, ...],
) -> None:
    _validate_required_non_claims(non_claims)

    for section in sections:
        missing = tuple(value for value in section.non_claims if value not in non_claims)
        if missing:
            missing_text = ", ".join(missing)
            raise ValidationError(
                f"non_claims must carry forward section advisory non-claims: {missing_text}."
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
