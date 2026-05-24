"""Metadata-only advisory research queue brief section contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.research_queue_brief_item import ResearchQueueBriefItem

__all__ = [
    "ResearchQueueBriefSection",
    "build_research_queue_brief_section",
]

_SECTION_TYPE = "research_queue_brief_section"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False


@dataclass(frozen=True, slots=True)
class ResearchQueueBriefSection:
    """Primitive advisory metadata grouping research queue brief items."""

    section_type: str
    status: str
    authority: str
    capital_authority: bool
    title: str
    summary: str
    items: tuple[ResearchQueueBriefItem, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        checked_items = _items_tuple(self.items)
        checked_limitations = _required_string_tuple(
            self.limitations,
            "limitations",
        )
        checked_non_claims = _required_string_tuple(self.non_claims, "non_claims")
        _validate_fixed_metadata(
            self.section_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(self, "items", checked_items)
        object.__setattr__(self, "limitations", checked_limitations)
        object.__setattr__(self, "non_claims", checked_non_claims)
        object.__setattr__(self, "title", _required_string(self.title, "title"))
        object.__setattr__(
            self,
            "summary",
            _required_string(self.summary, "summary"),
        )
        _validate_matches("title", self.title, _title(checked_items))
        _validate_matches("summary", self.summary, _summary(checked_items))
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
        """Return deterministic primitive-only section metadata."""

        return {
            "section_type": self.section_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "title": self.title,
            "summary": self.summary,
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_research_queue_brief_section(
    items: Iterable[ResearchQueueBriefItem],
) -> ResearchQueueBriefSection:
    """Build a deterministic advisory-only research queue section."""

    checked_items = _items_tuple(items)
    return ResearchQueueBriefSection(
        section_type=_SECTION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        title=_title(checked_items),
        summary=_summary(checked_items),
        items=checked_items,
        limitations=_combined_item_values(checked_items, "limitations"),
        non_claims=_combined_item_values(checked_items, "non_claims"),
    )


def _title(items: tuple[ResearchQueueBriefItem, ...]) -> str:
    if len(items) == 1:
        return f"Research queue metadata: {items[0].research_state}"

    return f"Research queue metadata: {len(items)} items"


def _summary(items: tuple[ResearchQueueBriefItem, ...]) -> str:
    strategy_ids = _unique_string_values(
        strategy_id
        for item in items
        for strategy_id in item.related_strategy_ids
    )
    states = _unique_string_values(item.research_state for item in items)
    priority_buckets = _unique_string_values(item.priority_bucket for item in items)
    limitations = _combined_item_values(items, "limitations")
    non_claims = _combined_item_values(items, "non_claims")
    return (
        f"Research queue section contains {len(items)} candidate metadata "
        f"item(s) across {len(strategy_ids)} related strategy id(s), state(s): "
        f"{', '.join(states)}, priority bucket(s): "
        f"{', '.join(priority_buckets)}, with {len(limitations)} limitation(s) "
        f"and {len(non_claims)} non-claim(s)."
    )


def _items_tuple(
    values: Iterable[ResearchQueueBriefItem],
) -> tuple[ResearchQueueBriefItem, ...]:
    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "items must be an iterable of ResearchQueueBriefItem."
        ) from exc

    if not items:
        raise ValidationError("items must contain at least one brief item.")

    seen_identities: set[int] = set()
    for index, item in enumerate(items):
        if type(item) is not ResearchQueueBriefItem:
            raise ValidationError(
                f"items[{index}] must be a ResearchQueueBriefItem."
            )

        item_identity = id(item)
        if item_identity in seen_identities:
            raise ValidationError("items must not contain duplicate item identities.")
        seen_identities.add(item_identity)

    return items


def _combined_item_values(
    items: tuple[ResearchQueueBriefItem, ...],
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


def _unique_string_values(values: Iterable[str]) -> tuple[str, ...]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        unique_values.append(value)
        seen.add(value)

    return tuple(unique_values)


def _validate_fixed_metadata(
    section_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if section_type != _SECTION_TYPE:
        raise ValidationError(
            "section_type must be exactly research_queue_brief_section."
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
        raise ValidationError(f"{field_name} must match item metadata.")
