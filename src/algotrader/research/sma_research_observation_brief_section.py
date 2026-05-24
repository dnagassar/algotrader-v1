"""Metadata-only advisory section for SMA research observation brief items."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.sma_research_observation_brief import (
    SmaResearchObservationBriefItem,
)

__all__ = [
    "SmaResearchObservationBriefSection",
    "build_sma_research_observation_brief_section",
]

_SECTION_TYPE = "sma_research_observation_brief_section"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False


def _join(*parts: str) -> str:
    return "".join(parts)


_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
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
    _join("capital ", "authority"),
    _join("tra", "ding authority"),
    _join("trading", "_ready"),
    _join("trading", "-ready"),
    _join("action", "able"),
    _join("b", "uy"),
    _join("s", "ell"),
    _join("h", "old"),
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class SmaResearchObservationBriefSection:
    """Primitive advisory metadata grouping SMA observation brief items."""

    section_type: str
    status: str
    authority: str
    capital_authority: bool
    section_id: str
    title: str
    summary: str
    items: tuple[SmaResearchObservationBriefItem, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        checked_items = _items_tuple(self.items)
        checked_limitations = _deduped_advisory_text_tuple(
            self.limitations,
            "limitations",
        )
        checked_non_claims = _deduped_non_claims(self.non_claims)
        _validate_fixed_metadata(
            self.section_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "section_id",
            _advisory_text(self.section_id, "section_id"),
        )
        object.__setattr__(
            self,
            "title",
            _advisory_text(self.title, "title"),
        )
        object.__setattr__(
            self,
            "summary",
            _advisory_text(self.summary, "summary"),
        )
        object.__setattr__(self, "items", checked_items)
        object.__setattr__(self, "limitations", checked_limitations)
        object.__setattr__(self, "non_claims", checked_non_claims)
        _validate_matches(
            "limitations",
            checked_limitations,
            _combined_item_values(checked_items, "limitations"),
        )
        _validate_matches(
            "non_claims",
            checked_non_claims,
            _combined_item_values(checked_items, "non_claims"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only SMA observation section metadata."""

        return {
            "section_type": self.section_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "section_id": self.section_id,
            "title": self.title,
            "summary": self.summary,
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_research_observation_brief_section(
    section_id: str,
    title: str,
    summary: str,
    items: Iterable[SmaResearchObservationBriefItem],
) -> SmaResearchObservationBriefSection:
    """Build a deterministic advisory-only SMA observation brief section."""

    checked_items = _items_tuple(items)
    return SmaResearchObservationBriefSection(
        section_type=_SECTION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        section_id=section_id,
        title=title,
        summary=summary,
        items=checked_items,
        limitations=_combined_item_values(checked_items, "limitations"),
        non_claims=_combined_item_values(checked_items, "non_claims"),
    )


def _items_tuple(
    values: Iterable[SmaResearchObservationBriefItem],
) -> tuple[SmaResearchObservationBriefItem, ...]:
    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "items must be an iterable of SmaResearchObservationBriefItem."
        ) from exc

    if not items:
        raise ValidationError("items must contain at least one brief item.")

    seen_identities: set[int] = set()
    for index, item in enumerate(items):
        if type(item) is not SmaResearchObservationBriefItem:
            raise ValidationError(
                f"items[{index}] must be a SmaResearchObservationBriefItem."
            )

        item_identity = id(item)
        if item_identity in seen_identities:
            raise ValidationError("items must not contain duplicate item identities.")
        seen_identities.add(item_identity)

    return items


def _combined_item_values(
    items: tuple[SmaResearchObservationBriefItem, ...],
    field_name: str,
) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        for value in getattr(item, field_name):
            if value in seen:
                continue
            values.append(value)
            seen.add(value)

    return tuple(values)


def _validate_fixed_metadata(
    section_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if section_type != _SECTION_TYPE:
        raise ValidationError(
            "section_type must be exactly sma_research_observation_brief_section."
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
        raise ValidationError(f"{field_name} must match item metadata.")
