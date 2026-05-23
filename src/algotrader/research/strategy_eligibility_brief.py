"""Metadata-only advisory strategy eligibility brief contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.strategy_eligibility_brief_section import (
    StrategyEligibilityBriefSection,
)

__all__ = [
    "StrategyEligibilityBrief",
    "build_strategy_eligibility_brief",
]

_BRIEF_TYPE = "strategy_eligibility_brief"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_TITLE = "Strategy eligibility brief metadata"


@dataclass(frozen=True, slots=True)
class StrategyEligibilityBrief:
    """Primitive advisory metadata grouping strategy eligibility sections."""

    brief_type: str
    status: str
    authority: str
    capital_authority: bool
    title: str
    summary: str
    sections: tuple[StrategyEligibilityBriefSection, ...]
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
        _validate_matches("title", self.title, _title())
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


def build_strategy_eligibility_brief(
    sections: Iterable[StrategyEligibilityBriefSection],
) -> StrategyEligibilityBrief:
    """Build a deterministic advisory-only strategy eligibility brief."""

    checked_sections = _sections_tuple(sections)
    return StrategyEligibilityBrief(
        brief_type=_BRIEF_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        title=_title(),
        summary=_summary(checked_sections),
        sections=checked_sections,
        limitations=_combined_section_values(checked_sections, "limitations"),
        non_claims=_combined_section_values(checked_sections, "non_claims"),
    )


def _title() -> str:
    return _TITLE


def _summary(sections: tuple[StrategyEligibilityBriefSection, ...]) -> str:
    item_count = 0
    for section in sections:
        item_count += len(section.items)

    limitations = _combined_section_values(sections, "limitations")
    non_claims = _combined_section_values(sections, "non_claims")
    return (
        f"Advisory brief contains {len(sections)} strategy eligibility "
        f"section(s), {item_count} candidate item(s), "
        f"{len(limitations)} limitation(s), and {len(non_claims)} non-claim(s)."
    )


def _sections_tuple(
    values: Iterable[StrategyEligibilityBriefSection],
) -> tuple[StrategyEligibilityBriefSection, ...]:
    try:
        sections = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "sections must be an iterable of StrategyEligibilityBriefSection."
        ) from exc

    if not sections:
        raise ValidationError("sections must contain at least one brief section.")

    seen_identities: set[int] = set()
    for index, section in enumerate(sections):
        if type(section) is not StrategyEligibilityBriefSection:
            raise ValidationError(
                f"sections[{index}] must be a StrategyEligibilityBriefSection."
            )

        section_identity = id(section)
        if section_identity in seen_identities:
            raise ValidationError(
                "sections must not contain duplicate section identities."
            )
        seen_identities.add(section_identity)

    return sections


def _combined_section_values(
    sections: tuple[StrategyEligibilityBriefSection, ...],
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
            "brief_type must be exactly strategy_eligibility_brief."
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
        raise ValidationError(f"{field_name} must match section metadata.")
