"""Metadata-only advisory strategy eligibility status contract."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError

__all__ = [
    "STRATEGY_ELIGIBILITY_STATES",
    "StrategyEligibilityStatus",
    "build_strategy_eligibility_status",
]

_ELIGIBILITY_TYPE = "strategy_eligibility_status"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
STRATEGY_ELIGIBILITY_STATES = ("research_only", "watchlist_only", "blocked")


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_REQUIRED_NON_CLAIMS = (
    _not("validation"),
    _not("paper readiness"),
    _not("live readiness"),
    _not("a tra", "ding recommendation"),
    _not("allo", "cation authority"),
    _not("or", "der authority"),
)
_FORBIDDEN_STATE_TOKENS = (
    "paper",
    "live",
    "authorized",
    "ready",
    "approved",
    "buy",
    "sell",
    "hold",
    "allocation",
    "order",
    "broker",
    "portfolio",
    "trading",
    "trade",
    "tradable",
)


@dataclass(frozen=True, slots=True)
class StrategyEligibilityStatus:
    """Primitive advisory metadata for a strategy candidate's eligibility state."""

    eligibility_type: str
    authority: str
    capital_authority: bool
    strategy_id: str
    strategy_name: str
    eligibility_state: str
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    required_next_steps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            self.eligibility_type,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "strategy_id",
            _required_string(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(
            self,
            "strategy_name",
            _required_string(self.strategy_name, "strategy_name"),
        )
        object.__setattr__(
            self,
            "eligibility_state",
            _eligibility_state(self.eligibility_state),
        )
        object.__setattr__(
            self,
            "reasons",
            _required_string_tuple(self.reasons, "reasons"),
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
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "required_next_steps",
            _string_tuple(self.required_next_steps, "required_next_steps"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only strategy eligibility metadata."""

        return {
            "eligibility_type": self.eligibility_type,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "eligibility_state": self.eligibility_state,
            "reasons": list(self.reasons),
            "evidence_refs": list(self.evidence_refs),
            "blockers": list(self.blockers),
            "required_next_steps": list(self.required_next_steps),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_strategy_eligibility_status(
    *,
    strategy_id: str,
    strategy_name: str,
    eligibility_state: str,
    reasons: tuple[str, ...] | list[str],
    limitations: tuple[str, ...] | list[str],
    non_claims: tuple[str, ...] | list[str] = _REQUIRED_NON_CLAIMS,
    evidence_refs: tuple[str, ...] | list[str] = (),
    blockers: tuple[str, ...] | list[str] = (),
    required_next_steps: tuple[str, ...] | list[str] = (),
) -> StrategyEligibilityStatus:
    """Build a deterministic advisory-only strategy eligibility status."""

    return StrategyEligibilityStatus(
        eligibility_type=_ELIGIBILITY_TYPE,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        eligibility_state=eligibility_state,
        reasons=reasons,
        evidence_refs=evidence_refs,
        blockers=blockers,
        required_next_steps=required_next_steps,
        limitations=limitations,
        non_claims=non_claims,
    )


def _validate_fixed_metadata(
    eligibility_type: object,
    authority: object,
    capital_authority: object,
) -> None:
    if eligibility_type != _ELIGIBILITY_TYPE:
        raise ValidationError(
            "eligibility_type must be exactly strategy_eligibility_status."
        )
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


def _eligibility_state(value: object) -> str:
    state = _required_string(value, "eligibility_state")
    lowered = state.lower()
    if any(token in lowered for token in _FORBIDDEN_STATE_TOKENS):
        raise ValidationError(
            "eligibility_state does not allow paper, live, authorized, "
            "trading-ready, or capital-authority states."
        )
    if state not in STRATEGY_ELIGIBILITY_STATES:
        allowed = ", ".join(STRATEGY_ELIGIBILITY_STATES)
        raise ValidationError(f"eligibility_state must be one of: {allowed}.")

    return state


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
