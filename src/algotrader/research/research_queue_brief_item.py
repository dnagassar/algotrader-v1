"""Metadata-only advisory research queue brief item contract."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.research_queue_status import ResearchQueueStatus

__all__ = [
    "ResearchQueueBriefItem",
    "build_research_queue_brief_item",
]

_ITEM_TYPE = "research_queue_brief_item"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False


@dataclass(frozen=True, slots=True)
class ResearchQueueBriefItem:
    """Primitive advisory metadata wrapping a research queue status."""

    item_type: str
    status: str
    authority: str
    capital_authority: bool
    queue_id: str
    title: str
    research_state: str
    priority_bucket: str
    topic: str
    headline: str
    summary: str
    hypothesis: str
    blockers: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    evidence_gaps: tuple[str, ...]
    related_strategy_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]
    source_status: ResearchQueueStatus

    def __post_init__(self) -> None:
        source_status = _require_source_status(self.source_status)
        _validate_fixed_metadata(
            self.item_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(self, "queue_id", _required_string(self.queue_id, "queue_id"))
        object.__setattr__(self, "title", _required_string(self.title, "title"))
        object.__setattr__(
            self,
            "research_state",
            _required_string(self.research_state, "research_state"),
        )
        object.__setattr__(
            self,
            "priority_bucket",
            _required_string(self.priority_bucket, "priority_bucket"),
        )
        object.__setattr__(self, "topic", _required_string(self.topic, "topic"))
        object.__setattr__(
            self,
            "headline",
            _required_string(self.headline, "headline"),
        )
        object.__setattr__(
            self,
            "summary",
            _required_string(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "hypothesis",
            _required_string(self.hypothesis, "hypothesis"),
        )
        object.__setattr__(
            self,
            "blockers",
            _required_string_tuple(self.blockers, "blockers"),
        )
        object.__setattr__(
            self,
            "required_next_steps",
            _required_string_tuple(
                self.required_next_steps,
                "required_next_steps",
            ),
        )
        object.__setattr__(
            self,
            "evidence_gaps",
            _required_string_tuple(self.evidence_gaps, "evidence_gaps"),
        )
        object.__setattr__(
            self,
            "related_strategy_ids",
            _string_tuple(self.related_strategy_ids, "related_strategy_ids"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(
            self,
            "limitations",
            _required_string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_string_tuple(self.non_claims, "non_claims"),
        )
        object.__setattr__(self, "source_status", source_status)
        _validate_source_metadata(self, source_status)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only brief item metadata."""

        return {
            "item_type": self.item_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "queue_id": self.queue_id,
            "title": self.title,
            "research_state": self.research_state,
            "priority_bucket": self.priority_bucket,
            "topic": self.topic,
            "headline": self.headline,
            "summary": self.summary,
            "hypothesis": self.hypothesis,
            "blockers": list(self.blockers),
            "required_next_steps": list(self.required_next_steps),
            "evidence_gaps": list(self.evidence_gaps),
            "related_strategy_ids": list(self.related_strategy_ids),
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
            "source_status": self.source_status.to_dict(),
        }


def build_research_queue_brief_item(
    status: ResearchQueueStatus,
) -> ResearchQueueBriefItem:
    """Build a deterministic advisory-only research queue brief item."""

    source_status = _require_source_status(status)
    return ResearchQueueBriefItem(
        item_type=_ITEM_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        queue_id=source_status.queue_id,
        title=source_status.title,
        research_state=source_status.research_state,
        priority_bucket=source_status.priority_bucket,
        topic=source_status.topic,
        headline=_headline(source_status),
        summary=_summary(source_status),
        hypothesis=source_status.hypothesis,
        blockers=source_status.blockers,
        required_next_steps=source_status.required_next_steps,
        evidence_gaps=source_status.evidence_gaps,
        related_strategy_ids=source_status.related_strategy_ids,
        evidence_refs=source_status.evidence_refs,
        limitations=source_status.limitations,
        non_claims=source_status.non_claims,
        source_status=source_status,
    )


def _headline(status: ResearchQueueStatus) -> str:
    return (
        f"Research queue item {status.queue_id}: "
        f"{status.research_state}."
    )


def _summary(status: ResearchQueueStatus) -> str:
    return (
        "Research queue metadata records "
        f"{status.research_state} work in the {status.priority_bucket} "
        f"priority bucket with {len(status.blockers)} blocker(s), "
        f"{len(status.required_next_steps)} required next step(s), "
        f"{len(status.evidence_gaps)} evidence gap(s), "
        f"{len(status.evidence_refs)} evidence reference(s), "
        f"{len(status.related_strategy_ids)} related strategy id(s), "
        f"{len(status.limitations)} limitation(s), and "
        f"{len(status.non_claims)} non-claim(s)."
    )


def _require_source_status(value: object) -> ResearchQueueStatus:
    if type(value) is not ResearchQueueStatus:
        raise ValidationError("source_status must be a ResearchQueueStatus.")

    return value


def _validate_fixed_metadata(
    item_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if item_type != _ITEM_TYPE:
        raise ValidationError("item_type must be exactly research_queue_brief_item.")
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")


def _validate_source_metadata(
    item: ResearchQueueBriefItem,
    source_status: ResearchQueueStatus,
) -> None:
    _validate_matches_source("queue_id", item.queue_id, source_status.queue_id)
    _validate_matches_source("title", item.title, source_status.title)
    _validate_matches_source(
        "research_state",
        item.research_state,
        source_status.research_state,
    )
    _validate_matches_source(
        "priority_bucket",
        item.priority_bucket,
        source_status.priority_bucket,
    )
    _validate_matches_source("topic", item.topic, source_status.topic)
    _validate_matches_source("headline", item.headline, _headline(source_status))
    _validate_matches_source("summary", item.summary, _summary(source_status))
    _validate_matches_source("hypothesis", item.hypothesis, source_status.hypothesis)
    _validate_matches_source("blockers", item.blockers, source_status.blockers)
    _validate_matches_source(
        "required_next_steps",
        item.required_next_steps,
        source_status.required_next_steps,
    )
    _validate_matches_source(
        "evidence_gaps",
        item.evidence_gaps,
        source_status.evidence_gaps,
    )
    _validate_matches_source(
        "related_strategy_ids",
        item.related_strategy_ids,
        source_status.related_strategy_ids,
    )
    _validate_matches_source(
        "evidence_refs",
        item.evidence_refs,
        source_status.evidence_refs,
    )
    _validate_matches_source("limitations", item.limitations, source_status.limitations)
    _validate_matches_source("non_claims", item.non_claims, source_status.non_claims)


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source_status.")


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _required_string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    items = _string_tuple(values, field_name)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    return items
