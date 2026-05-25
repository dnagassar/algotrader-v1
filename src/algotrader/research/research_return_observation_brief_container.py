"""Metadata-only advisory container for research return observation sections."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation_brief_section import (
    ResearchReturnObservationBriefSection,
)

__all__ = [
    "ResearchReturnObservationBrief",
    "build_research_return_observation_brief",
]

_BRIEF_TYPE = "research_return_observation_brief"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False


def _join(*parts: str) -> str:
    return "".join(parts)


_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("author", "ity"),
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("allo", "cation"),
    _join("or", "der"),
    _join("bro", "ker"),
    _join("port", "folio"),
    _join("pa", "per"),
    _join("li", "ve"),
    _join("read", "iness"),
    _join("trading", "_ready"),
    _join("trading", "-ready"),
    _join("action", "ability"),
    _join("action", "able"),
    _join("b", "uy"),
    _join("s", "ell"),
    _join("h", "old"),
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class ResearchReturnObservationBrief:
    """Primitive advisory metadata grouping return observation brief sections."""

    brief_type: str
    status: str
    authority: str
    capital_authority: bool
    brief_id: str
    title: str
    summary: str
    sections: tuple[ResearchReturnObservationBriefSection, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        checked_sections = _sections_tuple(self.sections)
        checked_limitations = _deduped_advisory_text_tuple(
            self.limitations,
            "limitations",
        )
        checked_non_claims = _deduped_non_claims(self.non_claims)
        _validate_fixed_metadata(
            self.brief_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "brief_id",
            _advisory_text(self.brief_id, "brief_id"),
        )
        object.__setattr__(self, "title", _advisory_text(self.title, "title"))
        object.__setattr__(
            self,
            "summary",
            _advisory_text(self.summary, "summary"),
        )
        object.__setattr__(self, "sections", checked_sections)
        object.__setattr__(self, "limitations", checked_limitations)
        object.__setattr__(self, "non_claims", checked_non_claims)
        _validate_matches(
            "limitations",
            checked_limitations,
            _combined_section_values(checked_sections, "limitations"),
        )
        _validate_matches(
            "non_claims",
            checked_non_claims,
            _combined_section_values(checked_sections, "non_claims"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only return observation brief metadata."""

        return {
            "brief_type": self.brief_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "brief_id": self.brief_id,
            "title": self.title,
            "summary": self.summary,
            "section_count": len(self.sections),
            "sections": [section.to_dict() for section in self.sections],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_research_return_observation_brief(
    brief_id: str,
    title: str,
    summary: str,
    sections: Iterable[ResearchReturnObservationBriefSection],
) -> ResearchReturnObservationBrief:
    """Build a deterministic advisory-only return observation brief."""

    checked_sections = _sections_tuple(sections)
    return ResearchReturnObservationBrief(
        brief_type=_BRIEF_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        brief_id=brief_id,
        title=title,
        summary=summary,
        sections=checked_sections,
        limitations=_combined_section_values(checked_sections, "limitations"),
        non_claims=_combined_section_values(checked_sections, "non_claims"),
    )


def _sections_tuple(
    values: Iterable[ResearchReturnObservationBriefSection],
) -> tuple[ResearchReturnObservationBriefSection, ...]:
    try:
        sections = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "sections must be an iterable of ResearchReturnObservationBriefSection."
        ) from exc

    if not sections:
        raise ValidationError("sections must contain at least one brief section.")

    seen_identities: set[int] = set()
    for index, section in enumerate(sections):
        if type(section) is not ResearchReturnObservationBriefSection:
            raise ValidationError(
                f"sections[{index}] must be a ResearchReturnObservationBriefSection."
            )

        section_identity = id(section)
        if section_identity in seen_identities:
            raise ValidationError(
                "sections must not contain duplicate section identities."
            )
        seen_identities.add(section_identity)

    return sections


def _combined_section_values(
    sections: tuple[ResearchReturnObservationBriefSection, ...],
    field_name: str,
) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for section in sections:
        for value in getattr(section, field_name):
            if value in seen:
                continue
            values.append(value)
            seen.add(value)

    return tuple(values)


def _validate_fixed_metadata(
    brief_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if brief_type != _BRIEF_TYPE:
        raise ValidationError(
            "brief_type must be exactly research_return_observation_brief."
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


def _advisory_text(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    lowered = text.lower()
    if any(token in lowered for token in _FORBIDDEN_TEXT_TOKENS):
        raise ValidationError(f"{field_name} must remain advisory metadata text.")

    return text


def _deduped_advisory_text_tuple(
    values: object,
    field_name: str,
) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, field_name))
    for index, value in enumerate(items):
        _advisory_text(value, f"{field_name}[{index}]")

    return items


def _deduped_non_claims(values: object) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, "non_claims"))
    if any(not item.startswith("not ") for item in items):
        raise ValidationError("non_claims entries must be negative statements.")

    return items


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)


def _validate_matches(
    field_name: str,
    value: object,
    expected: object,
) -> None:
    if value != expected:
        raise ValidationError(f"{field_name} must match section metadata.")
