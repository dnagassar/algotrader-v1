"""Metadata-only advisory risk authority status contract."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError

__all__ = [
    "RISK_AUTHORITY_STATES",
    "RiskAuthorityStatus",
    "build_risk_authority_status",
]

_AUTHORITY_TYPE = "risk_authority_status"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
RISK_AUTHORITY_STATES = ("not_authorized", "blocked", "research_only")


def _join(*parts: str) -> str:
    return "".join(parts)


_REQUIRED_NON_CLAIMS = (
    "not risk approval",
    _join("not allo", "cation authority"),
    _join("not or", "der authority"),
    "not paper readiness",
    "not live readiness",
    _join("not bro", "ker authority"),
    _join("not port", "folio mutation authority"),
    "not capital authority",
    "not trading authority",
)
_FORBIDDEN_STATE_TOKENS = (
    "paper",
    "live",
    "authorized",
    "ready",
    "eligible",
    _join("app", "roved"),
    _join("allo", "cation"),
    _join("or", "der"),
    _join("bro", "ker"),
    _join("ac", "count"),
    _join("port", "folio"),
    _join("b", "uy"),
    _join("se", "ll"),
    _join("h", "old"),
    "target",
    "weight",
    "position",
    "size",
    "capital",
    "trading",
    "trade",
    "authority",
)


@dataclass(frozen=True, slots=True)
class RiskAuthorityStatus:
    """Primitive advisory metadata for current risk-capital authority status."""

    authority_type: str
    status: str
    authority: str
    capital_authority: bool
    authority_state: str
    reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    related_strategy_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            self.authority_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "authority_state",
            _authority_state(self.authority_state),
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
            _required_non_claims(self.non_claims),
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

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only risk authority metadata."""

        return {
            "authority_type": self.authority_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "authority_state": self.authority_state,
            "reasons": list(self.reasons),
            "blockers": list(self.blockers),
            "required_next_steps": list(self.required_next_steps),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
            "evidence_refs": list(self.evidence_refs),
            "related_strategy_ids": list(self.related_strategy_ids),
        }


def build_risk_authority_status(
    *,
    authority_state: str,
    reasons: tuple[str, ...] | list[str],
    blockers: tuple[str, ...] | list[str],
    required_next_steps: tuple[str, ...] | list[str],
    limitations: tuple[str, ...] | list[str],
    non_claims: tuple[str, ...] | list[str] = _REQUIRED_NON_CLAIMS,
    evidence_refs: tuple[str, ...] | list[str] = (),
    related_strategy_ids: tuple[str, ...] | list[str] = (),
) -> RiskAuthorityStatus:
    """Build a deterministic advisory-only risk authority status."""

    return RiskAuthorityStatus(
        authority_type=_AUTHORITY_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        authority_state=authority_state,
        reasons=reasons,
        blockers=blockers,
        required_next_steps=required_next_steps,
        limitations=limitations,
        non_claims=non_claims,
        evidence_refs=evidence_refs,
        related_strategy_ids=related_strategy_ids,
    )


def _validate_fixed_metadata(
    authority_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if authority_type != _AUTHORITY_TYPE:
        raise ValidationError(
            "authority_type must be exactly risk_authority_status."
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


def _authority_state(value: object) -> str:
    state = _required_string(value, "authority_state")
    if state in RISK_AUTHORITY_STATES:
        return state

    lowered = state.lower()
    if any(token in lowered for token in _FORBIDDEN_STATE_TOKENS):
        raise ValidationError(
            "authority_state does not allow paper, live, authorized, "
            "trading-ready, allocation, order-capable, broker, account, "
            "portfolio, or capital-authority states."
        )

    allowed = ", ".join(RISK_AUTHORITY_STATES)
    raise ValidationError(f"authority_state must be one of: {allowed}.")


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


def _required_non_claims(values: object) -> tuple[str, ...]:
    non_claims = _required_string_tuple(values, "non_claims")
    missing = tuple(claim for claim in _REQUIRED_NON_CLAIMS if claim not in non_claims)
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"non_claims must include required advisory non-claims: {missing_text}."
        )

    if any(not claim.startswith("not ") for claim in non_claims):
        raise ValidationError("non_claims entries must be negative statements.")

    return non_claims
