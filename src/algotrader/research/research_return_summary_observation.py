"""Deterministic descriptive summaries for research return observations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation import (
    ResearchReturnSeriesObservation,
)

__all__ = [
    "RESEARCH_RETURN_SUMMARY_STATES",
    "ResearchReturnSummaryObservation",
    "build_research_return_summary_observation",
]

_OBSERVATION_TYPE = "research_return_summary_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
RESEARCH_RETURN_SUMMARY_STATES = (
    "returns_summarized",
    "insufficient_return_history",
)


def _join(*parts: str) -> str:
    return "".join(parts)


_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("action", "ability"),
    _join("action", "able"),
    _join("author", "ity"),
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
    _join("trading", "_ready"),
    _join("trading", "-ready"),
    _join("b", "uy"),
    _join("s", "ell"),
    _join("h", "old"),
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class ResearchReturnSummaryObservation:
    """Advisory-only descriptive summary of synthetic return mechanics."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    symbol: str
    as_of: str
    return_method: str
    price_basis: str
    source_return_count: int
    positive_return_count: int
    negative_return_count: int
    zero_return_count: int
    min_simple_return: Decimal | None
    max_simple_return: Decimal | None
    mean_simple_return: Decimal | None
    summary_state: str
    source_observation: ResearchReturnSeriesObservation
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_observation = _require_source_observation(self.source_observation)
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(self, "symbol", _required_string(self.symbol, "symbol"))
        object.__setattr__(self, "as_of", _required_string(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "return_method",
            _required_string(self.return_method, "return_method"),
        )
        object.__setattr__(
            self,
            "price_basis",
            _required_string(self.price_basis, "price_basis"),
        )
        object.__setattr__(
            self,
            "source_return_count",
            _non_negative_int(self.source_return_count, "source_return_count"),
        )
        object.__setattr__(
            self,
            "positive_return_count",
            _non_negative_int(self.positive_return_count, "positive_return_count"),
        )
        object.__setattr__(
            self,
            "negative_return_count",
            _non_negative_int(self.negative_return_count, "negative_return_count"),
        )
        object.__setattr__(
            self,
            "zero_return_count",
            _non_negative_int(self.zero_return_count, "zero_return_count"),
        )
        object.__setattr__(
            self,
            "min_simple_return",
            _optional_decimal(self.min_simple_return, "min_simple_return"),
        )
        object.__setattr__(
            self,
            "max_simple_return",
            _optional_decimal(self.max_simple_return, "max_simple_return"),
        )
        object.__setattr__(
            self,
            "mean_simple_return",
            _optional_decimal(self.mean_simple_return, "mean_simple_return"),
        )
        object.__setattr__(self, "summary_state", _summary_state(self.summary_state))
        object.__setattr__(self, "source_observation", source_observation)
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _deduped_non_claims(self.non_claims))
        _validate_source_metadata(self, source_observation)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only summary observation metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "return_method": self.return_method,
            "price_basis": self.price_basis,
            "source_return_count": self.source_return_count,
            "positive_return_count": self.positive_return_count,
            "negative_return_count": self.negative_return_count,
            "zero_return_count": self.zero_return_count,
            "min_simple_return": _decimal_payload(self.min_simple_return),
            "max_simple_return": _decimal_payload(self.max_simple_return),
            "mean_simple_return": _decimal_payload(self.mean_simple_return),
            "summary_state": self.summary_state,
            "source_observation": self.source_observation.to_dict(),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_research_return_summary_observation(
    observation: ResearchReturnSeriesObservation,
) -> ResearchReturnSummaryObservation:
    """Build a deterministic summary over a research return observation."""

    source_observation = _require_source_observation(observation)
    (
        source_return_count,
        positive_return_count,
        negative_return_count,
        zero_return_count,
        min_simple_return,
        max_simple_return,
        mean_simple_return,
        summary_state,
    ) = _return_summary(source_observation)

    return ResearchReturnSummaryObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        symbol=source_observation.symbol,
        as_of=source_observation.as_of,
        return_method=source_observation.return_method,
        price_basis=source_observation.price_basis,
        source_return_count=source_return_count,
        positive_return_count=positive_return_count,
        negative_return_count=negative_return_count,
        zero_return_count=zero_return_count,
        min_simple_return=min_simple_return,
        max_simple_return=max_simple_return,
        mean_simple_return=mean_simple_return,
        summary_state=summary_state,
        source_observation=source_observation,
        limitations=_dedupe(source_observation.limitations),
        non_claims=_dedupe(source_observation.non_claims),
    )


def _return_summary(
    observation: ResearchReturnSeriesObservation,
) -> tuple[int, int, int, int, Decimal | None, Decimal | None, Decimal | None, str]:
    if observation.return_count == 0:
        return (0, 0, 0, 0, None, None, None, "insufficient_return_history")

    simple_returns = tuple(return_point.simple_return for return_point in observation.returns)
    positive_return_count = 0
    negative_return_count = 0
    zero_return_count = 0
    for simple_return in simple_returns:
        if simple_return > 0:
            positive_return_count += 1
        elif simple_return < 0:
            negative_return_count += 1
        else:
            zero_return_count += 1

    mean_simple_return = sum(simple_returns, Decimal("0")) / Decimal(
        len(simple_returns)
    )
    return (
        observation.return_count,
        positive_return_count,
        negative_return_count,
        zero_return_count,
        min(simple_returns),
        max(simple_returns),
        mean_simple_return,
        "returns_summarized",
    )


def _require_source_observation(value: object) -> ResearchReturnSeriesObservation:
    if type(value) is not ResearchReturnSeriesObservation:
        raise ValidationError(
            "source_observation must be a ResearchReturnSeriesObservation."
        )

    return value


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly research_return_summary_observation."
        )
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")


def _validate_source_metadata(
    summary: ResearchReturnSummaryObservation,
    observation: ResearchReturnSeriesObservation,
) -> None:
    (
        source_return_count,
        positive_return_count,
        negative_return_count,
        zero_return_count,
        min_simple_return,
        max_simple_return,
        mean_simple_return,
        summary_state,
    ) = _return_summary(observation)

    _validate_matches_source("symbol", summary.symbol, observation.symbol)
    _validate_matches_source("as_of", summary.as_of, observation.as_of)
    _validate_matches_source(
        "return_method",
        summary.return_method,
        observation.return_method,
    )
    _validate_matches_source("price_basis", summary.price_basis, observation.price_basis)
    _validate_matches_source(
        "source_return_count",
        summary.source_return_count,
        source_return_count,
    )
    _validate_matches_source(
        "positive_return_count",
        summary.positive_return_count,
        positive_return_count,
    )
    _validate_matches_source(
        "negative_return_count",
        summary.negative_return_count,
        negative_return_count,
    )
    _validate_matches_source(
        "zero_return_count",
        summary.zero_return_count,
        zero_return_count,
    )
    _validate_matches_source(
        "min_simple_return",
        summary.min_simple_return,
        min_simple_return,
    )
    _validate_matches_source(
        "max_simple_return",
        summary.max_simple_return,
        max_simple_return,
    )
    _validate_matches_source(
        "mean_simple_return",
        summary.mean_simple_return,
        mean_simple_return,
    )
    _validate_matches_source("summary_state", summary.summary_state, summary_state)
    _validate_matches_source(
        "limitations",
        summary.limitations,
        _dedupe(observation.limitations),
    )
    _validate_matches_source(
        "non_claims",
        summary.non_claims,
        _dedupe(observation.non_claims),
    )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source_observation.")


def _summary_state(value: object) -> str:
    state = _required_string(value, "summary_state")
    if state not in RESEARCH_RETURN_SUMMARY_STATES:
        allowed = ", ".join(RESEARCH_RETURN_SUMMARY_STATES)
        raise ValidationError(f"summary_state must be one of: {allowed}.")

    return state


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _advisory_text(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    lowered = text.lower()
    if any(text_fragment in lowered for text_fragment in _FORBIDDEN_TEXT_TOKENS):
        raise ValidationError(f"{field_name} must remain advisory metadata text.")

    return text


def _deduped_advisory_text_tuple(
    values: object,
    field_name: str,
) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, field_name, allow_empty=True))
    for index, value in enumerate(items):
        _advisory_text(value, f"{field_name}[{index}]")

    return items


def _deduped_non_claims(values: object) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, "non_claims", allow_empty=False))
    if not items:
        raise ValidationError("non_claims must contain at least one string.")

    if any(not item.startswith("not ") for item in items):
        raise ValidationError("non_claims entries must be negative statements.")

    return items


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not allow_empty and not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal or None.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _decimal_payload(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)
