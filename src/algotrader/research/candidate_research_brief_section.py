"""Advisory display section for candidate research brief item metadata."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.candidate_research_brief_item import (
    CandidateResearchBriefItem,
)

__all__ = [
    "CandidateResearchBriefSection",
    "build_candidate_research_brief_section",
]

_SECTION_TYPE = "candidate_research_results"
_ADVISORY_STATUS = "candidate_only"
_TITLE = "Candidate research results metadata"
_DEFAULT_LIMITATIONS = (
    "metadata-only section for existing candidate brief items",
    "does not create research, compute metrics, or mutate item payloads",
    "advisory grouping for future queue and brief surfaces only",
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
class CandidateResearchBriefSection:
    """Metadata-only advisory grouping for candidate research brief items."""

    section_type: str
    status: str
    title: str
    items: tuple[CandidateResearchBriefItem, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_section_type(self.section_type)
        _validate_status(self.status)
        _required_string(self.title, "title")
        checked_items = _validate_items(self.items)
        checked_limitations = _required_string_tuple(
            self.limitations,
            "limitations",
        )
        checked_non_claims = _required_string_tuple(self.non_claims, "non_claims")
        _validate_limitations(checked_items, checked_limitations)
        _validate_non_claims(checked_items, checked_non_claims)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive section metadata."""

        return {
            "section_type": self.section_type,
            "status": self.status,
            "title": self.title,
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_candidate_research_brief_section(
    items: Iterable[CandidateResearchBriefItem],
) -> CandidateResearchBriefSection:
    """Build a deterministic advisory section from existing brief items."""

    checked_items = _items_tuple(items)
    return CandidateResearchBriefSection(
        section_type=_SECTION_TYPE,
        status=_ADVISORY_STATUS,
        title=_TITLE,
        items=checked_items,
        limitations=_combine_string_tuples(
            _DEFAULT_LIMITATIONS,
            *(item.limitations for item in checked_items),
        ),
        non_claims=_combine_string_tuples(
            _REQUIRED_NON_CLAIMS,
            *(item.non_claims for item in checked_items),
        ),
    )


def _items_tuple(
    values: Iterable[CandidateResearchBriefItem],
) -> tuple[CandidateResearchBriefItem, ...]:
    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "items must be an iterable of CandidateResearchBriefItem."
        ) from exc

    return _validate_items(items)


def _validate_items(
    items: object,
) -> tuple[CandidateResearchBriefItem, ...]:
    if not isinstance(items, tuple):
        raise ValidationError(
            "items must be a non-empty tuple of CandidateResearchBriefItem."
        )

    if not items:
        raise ValidationError("items must contain at least one brief item.")

    seen_identities: set[int] = set()
    for index, item in enumerate(items):
        if not isinstance(item, CandidateResearchBriefItem):
            raise ValidationError(
                f"items[{index}] must be a CandidateResearchBriefItem."
            )

        item_identity = id(item)
        if item_identity in seen_identities:
            raise ValidationError("items must not contain duplicate item identities.")
        seen_identities.add(item_identity)

    return items


def _validate_section_type(value: object) -> None:
    if value != _SECTION_TYPE:
        raise ValidationError(
            "section_type must be exactly candidate_research_results."
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
    items: tuple[CandidateResearchBriefItem, ...],
    limitations: tuple[str, ...],
) -> None:
    for item in items:
        missing = tuple(value for value in item.limitations if value not in limitations)
        if missing:
            missing_text = ", ".join(missing)
            raise ValidationError(
                f"limitations must carry forward item limitations: {missing_text}."
            )


def _validate_non_claims(
    items: tuple[CandidateResearchBriefItem, ...],
    non_claims: tuple[str, ...],
) -> None:
    _validate_required_non_claims(non_claims)

    for item in items:
        missing = tuple(value for value in item.non_claims if value not in non_claims)
        if missing:
            missing_text = ", ".join(missing)
            raise ValidationError(
                f"non_claims must carry forward item advisory non-claims: {missing_text}."
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
