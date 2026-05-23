"""Metadata-only advisory risk authority brief item contract."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.risk_authority_status import RiskAuthorityStatus

__all__ = [
    "RiskAuthorityBriefItem",
    "build_risk_authority_brief_item",
]

_ITEM_TYPE = "risk_authority_brief_item"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False


@dataclass(frozen=True, slots=True)
class RiskAuthorityBriefItem:
    """Primitive advisory metadata wrapping a risk authority status."""

    item_type: str
    status: str
    authority: str
    capital_authority: bool
    authority_state: str
    headline: str
    summary: str
    reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    related_strategy_ids: tuple[str, ...]
    source_status: RiskAuthorityStatus

    def __post_init__(self) -> None:
        source_status = _require_source_status(self.source_status)
        _validate_fixed_metadata(
            self.item_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "authority_state",
            _required_string(self.authority_state, "authority_state"),
        )
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
            "reasons",
            _required_string_tuple(self.reasons, "reasons"),
        )
        object.__setattr__(
            self,
            "blockers",
            _required_string_tuple(self.blockers, "blockers"),
        )
        object.__setattr__(
            self,
            "required_next_steps",
            _required_string_tuple(self.required_next_steps, "required_next_steps"),
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
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(
            self,
            "related_strategy_ids",
            _string_tuple(self.related_strategy_ids, "related_strategy_ids"),
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
            "authority_state": self.authority_state,
            "headline": self.headline,
            "summary": self.summary,
            "reasons": list(self.reasons),
            "blockers": list(self.blockers),
            "required_next_steps": list(self.required_next_steps),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
            "evidence_refs": list(self.evidence_refs),
            "related_strategy_ids": list(self.related_strategy_ids),
            "source_status": self.source_status.to_dict(),
        }


def build_risk_authority_brief_item(
    status: RiskAuthorityStatus,
) -> RiskAuthorityBriefItem:
    """Build a deterministic advisory-only risk authority brief item."""

    source_status = _require_source_status(status)
    return RiskAuthorityBriefItem(
        item_type=_ITEM_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        authority_state=source_status.authority_state,
        headline=_headline(source_status),
        summary=_summary(source_status),
        reasons=source_status.reasons,
        blockers=source_status.blockers,
        required_next_steps=source_status.required_next_steps,
        limitations=source_status.limitations,
        non_claims=source_status.non_claims,
        evidence_refs=source_status.evidence_refs,
        related_strategy_ids=source_status.related_strategy_ids,
        source_status=source_status,
    )


def _headline(status: RiskAuthorityStatus) -> str:
    return f"Advisory risk metadata: {status.authority_state}."


def _summary(status: RiskAuthorityStatus) -> str:
    return (
        "Advisory risk metadata records "
        f"{status.authority_state} with "
        f"{len(status.reasons)} reason(s), "
        f"{len(status.limitations)} limitation(s), "
        f"{len(status.non_claims)} non-claim(s), "
        f"{len(status.evidence_refs)} evidence reference(s), "
        f"{len(status.blockers)} blocker(s), "
        f"{len(status.required_next_steps)} required next step(s), and "
        f"{len(status.related_strategy_ids)} related strategy id(s)."
    )


def _require_source_status(value: object) -> RiskAuthorityStatus:
    if type(value) is not RiskAuthorityStatus:
        raise ValidationError("source_status must be a RiskAuthorityStatus.")

    return value


def _validate_fixed_metadata(
    item_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if item_type != _ITEM_TYPE:
        raise ValidationError("item_type must be exactly risk_authority_brief_item.")
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")


def _validate_source_metadata(
    item: RiskAuthorityBriefItem,
    source_status: RiskAuthorityStatus,
) -> None:
    _validate_matches_source(
        "authority_state",
        item.authority_state,
        source_status.authority_state,
    )
    _validate_matches_source("headline", item.headline, _headline(source_status))
    _validate_matches_source("summary", item.summary, _summary(source_status))
    _validate_matches_source("reasons", item.reasons, source_status.reasons)
    _validate_matches_source("blockers", item.blockers, source_status.blockers)
    _validate_matches_source(
        "required_next_steps",
        item.required_next_steps,
        source_status.required_next_steps,
    )
    _validate_matches_source("limitations", item.limitations, source_status.limitations)
    _validate_matches_source("non_claims", item.non_claims, source_status.non_claims)
    _validate_matches_source(
        "evidence_refs",
        item.evidence_refs,
        source_status.evidence_refs,
    )
    _validate_matches_source(
        "related_strategy_ids",
        item.related_strategy_ids,
        source_status.related_strategy_ids,
    )


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
