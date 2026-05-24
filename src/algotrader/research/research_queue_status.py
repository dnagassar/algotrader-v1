"""Metadata-only advisory research queue status contract."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError

__all__ = [
    "RESEARCH_QUEUE_PRIORITY_BUCKETS",
    "RESEARCH_QUEUE_STATES",
    "ResearchQueueStatus",
    "build_research_queue_status",
]

_QUEUE_TYPE = "research_queue_status"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
RESEARCH_QUEUE_STATES = (
    "untriaged",
    "needs_evidence",
    "blocked",
    "ready_for_scoping",
)
RESEARCH_QUEUE_PRIORITY_BUCKETS = ("low", "medium", "high", "deferred")


def _join(*parts: str) -> str:
    return "".join(parts)


_REQUIRED_NON_CLAIMS = (
    _join("not a recomm", "endation"),
    _join("not allo", "cation authority"),
    _join("not or", "der authority"),
    "not paper readiness",
    "not live readiness",
    _join("not bro", "ker authority"),
    _join("not ac", "count authority"),
    _join("not port", "folio mutation authority"),
    "not capital authority",
    "not trading authority",
)
_FORBIDDEN_LANGUAGE_TOKENS = (
    _join("recomm", "endation"),
    _join("allo", "cation"),
    _join("or", "der"),
    _join("bro", "ker"),
    _join("ac", "count"),
    _join("port", "folio"),
    "capital authority",
    "trading authority",
    "paper",
    "live",
    _join("app", "roved"),
    _join("author", "ized"),
    "trading-ready",
    "trading_ready",
)


@dataclass(frozen=True, slots=True)
class ResearchQueueStatus:
    """Primitive advisory metadata for unresolved research queue work."""

    queue_type: str
    status: str
    authority: str
    capital_authority: bool
    queue_id: str
    title: str
    research_state: str
    priority_bucket: str
    topic: str
    hypothesis: str
    blockers: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    evidence_gaps: tuple[str, ...]
    related_strategy_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            self.queue_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "queue_id",
            _advisory_string(self.queue_id, "queue_id"),
        )
        object.__setattr__(self, "title", _advisory_string(self.title, "title"))
        object.__setattr__(
            self,
            "research_state",
            _research_state(self.research_state),
        )
        object.__setattr__(
            self,
            "priority_bucket",
            _priority_bucket(self.priority_bucket),
        )
        object.__setattr__(self, "topic", _advisory_string(self.topic, "topic"))
        object.__setattr__(
            self,
            "hypothesis",
            _advisory_string(self.hypothesis, "hypothesis"),
        )
        object.__setattr__(
            self,
            "blockers",
            _required_advisory_string_tuple(self.blockers, "blockers"),
        )
        object.__setattr__(
            self,
            "required_next_steps",
            _required_advisory_string_tuple(
                self.required_next_steps,
                "required_next_steps",
            ),
        )
        object.__setattr__(
            self,
            "evidence_gaps",
            _required_advisory_string_tuple(self.evidence_gaps, "evidence_gaps"),
        )
        object.__setattr__(
            self,
            "related_strategy_ids",
            _advisory_string_tuple(
                self.related_strategy_ids,
                "related_strategy_ids",
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _advisory_string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(
            self,
            "limitations",
            _required_advisory_string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only research queue metadata."""

        return {
            "queue_type": self.queue_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "queue_id": self.queue_id,
            "title": self.title,
            "research_state": self.research_state,
            "priority_bucket": self.priority_bucket,
            "topic": self.topic,
            "hypothesis": self.hypothesis,
            "blockers": list(self.blockers),
            "required_next_steps": list(self.required_next_steps),
            "evidence_gaps": list(self.evidence_gaps),
            "related_strategy_ids": list(self.related_strategy_ids),
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_research_queue_status(
    *,
    queue_id: str,
    title: str,
    research_state: str,
    priority_bucket: str,
    topic: str,
    hypothesis: str,
    blockers: tuple[str, ...] | list[str],
    required_next_steps: tuple[str, ...] | list[str],
    evidence_gaps: tuple[str, ...] | list[str],
    limitations: tuple[str, ...] | list[str],
    related_strategy_ids: tuple[str, ...] | list[str] = (),
    evidence_refs: tuple[str, ...] | list[str] = (),
    non_claims: tuple[str, ...] | list[str] = _REQUIRED_NON_CLAIMS,
) -> ResearchQueueStatus:
    """Build deterministic advisory-only research queue metadata."""

    return ResearchQueueStatus(
        queue_type=_QUEUE_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        queue_id=queue_id,
        title=title,
        research_state=research_state,
        priority_bucket=priority_bucket,
        topic=topic,
        hypothesis=hypothesis,
        blockers=blockers,
        required_next_steps=required_next_steps,
        evidence_gaps=evidence_gaps,
        related_strategy_ids=related_strategy_ids,
        evidence_refs=evidence_refs,
        limitations=limitations,
        non_claims=non_claims,
    )


def _validate_fixed_metadata(
    queue_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if queue_type != _QUEUE_TYPE:
        raise ValidationError("queue_type must be exactly research_queue_status.")
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


def _advisory_string(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    lowered = text.lower()
    if any(token in lowered for token in _FORBIDDEN_LANGUAGE_TOKENS):
        raise ValidationError(
            f"{field_name} must not contain recommendation, allocation, "
            "order, broker, account, portfolio, capital-authority, "
            "trading-authority, paper, live, approved, authorized, or "
            "trading-ready language."
        )

    return text


def _research_state(value: object) -> str:
    state = _required_string(value, "research_state")
    if state in RESEARCH_QUEUE_STATES:
        return state

    raise ValidationError(
        "research_state must be one of: "
        f"{', '.join(RESEARCH_QUEUE_STATES)}."
    )


def _priority_bucket(value: object) -> str:
    bucket = _required_string(value, "priority_bucket")
    if bucket in RESEARCH_QUEUE_PRIORITY_BUCKETS:
        return bucket

    raise ValidationError(
        "priority_bucket must be one of: "
        f"{', '.join(RESEARCH_QUEUE_PRIORITY_BUCKETS)}."
    )


def _advisory_string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    for index, value in enumerate(items):
        _advisory_string(value, f"{field_name}[{index}]")

    return items


def _required_advisory_string_tuple(
    values: object,
    field_name: str,
) -> tuple[str, ...]:
    items = _advisory_string_tuple(values, field_name)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    return items


def _required_non_claims(values: object) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("non_claims must be a tuple or list of strings.")

    non_claims = tuple(values)
    if not non_claims:
        raise ValidationError("non_claims must contain at least one string.")

    for index, value in enumerate(non_claims):
        _required_string(value, f"non_claims[{index}]")

    missing = tuple(claim for claim in _REQUIRED_NON_CLAIMS if claim not in non_claims)
    if missing:
        raise ValidationError(
            "non_claims must include required advisory non-claims: "
            f"{', '.join(missing)}."
        )

    if any(not claim.startswith("not ") for claim in non_claims):
        raise ValidationError("non_claims entries must be negative statements.")

    return non_claims
