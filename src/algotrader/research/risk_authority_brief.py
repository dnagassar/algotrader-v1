"""Metadata-only advisory risk authority brief contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.risk_authority_brief_section import (
    RiskAuthorityBriefSection,
)

__all__ = [
    "RiskAuthorityBrief",
    "build_risk_authority_brief",
]

_BRIEF_TYPE = "risk_authority_brief"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False


@dataclass(frozen=True, slots=True)
class RiskAuthorityBrief:
    """Primitive advisory metadata grouping risk authority brief sections."""

    brief_type: str
    status: str
    authority: str
    capital_authority: bool
    title: str
    summary: str
    sections: tuple[RiskAuthorityBriefSection, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        checked_sections = _sections_tuple(self.sections)
        checked_limitations = _required_string_tuple(
            self.limitations,
            "limitations",
        )
        checked_non_claims = _required_string_tuple(self.non_claims, "non_claims")
        _validate_fixed_metadata(
            self.brief_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(self, "sections", checked_sections)
        object.__setattr__(self, "limitations", checked_limitations)
        object.__setattr__(self, "non_claims", checked_non_claims)
        object.__setattr__(self, "title", _required_string(self.title, "title"))
        object.__setattr__(
            self,
            "summary",
            _required_string(self.summary, "summary"),
        )
        _validate_matches("title", self.title, _title(checked_sections))
        _validate_matches("summary", self.summary, _summary(checked_sections))
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
        """Return deterministic primitive-only brief metadata."""

        return {
            "brief_type": self.brief_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "title": self.title,
            "summary": self.summary,
            "section_count": len(self.sections),
            "sections": [section.to_dict() for section in self.sections],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_risk_authority_brief(
    sections: Iterable[RiskAuthorityBriefSection],
) -> RiskAuthorityBrief:
    """Build a deterministic advisory-only risk authority brief."""

    checked_sections = _sections_tuple(sections)
    return RiskAuthorityBrief(
        brief_type=_BRIEF_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        title=_title(checked_sections),
        summary=_summary(checked_sections),
        sections=checked_sections,
        limitations=_combined_section_values(checked_sections, "limitations"),
        non_claims=_combined_section_values(checked_sections, "non_claims"),
    )


def _title(sections: tuple[RiskAuthorityBriefSection, ...]) -> str:
    if len(sections) == 1:
        return "Advisory risk metadata brief: 1 section"

    return f"Advisory risk metadata brief: {len(sections)} sections"


def _summary(sections: tuple[RiskAuthorityBriefSection, ...]) -> str:
    limitations = _combined_section_values(sections, "limitations")
    non_claims = _combined_section_values(sections, "non_claims")
    item_count = sum(len(section.items) for section in sections)
    return (
        f"Advisory brief contains {len(sections)} candidate risk metadata "
        f"section(s) with {item_count} item(s), {len(limitations)} "
        f"limitation(s), and {len(non_claims)} non-claim(s)."
    )


def _sections_tuple(
    values: Iterable[RiskAuthorityBriefSection],
) -> tuple[RiskAuthorityBriefSection, ...]:
    try:
        sections = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "sections must be an iterable of RiskAuthorityBriefSection."
        ) from exc

    if not sections:
        raise ValidationError("sections must contain at least one brief section.")

    seen_identities: set[int] = set()
    for index, section in enumerate(sections):
        if type(section) is not RiskAuthorityBriefSection:
            raise ValidationError(
                f"sections[{index}] must be a RiskAuthorityBriefSection."
            )

        section_identity = id(section)
        if section_identity in seen_identities:
            raise ValidationError(
                "sections must not contain duplicate section identities."
            )
        seen_identities.add(section_identity)

    return sections


def _combined_section_values(
    sections: tuple[RiskAuthorityBriefSection, ...],
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
        raise ValidationError("brief_type must be exactly risk_authority_brief.")
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
        raise ValidationError(f"{field_name} must match section metadata.")
