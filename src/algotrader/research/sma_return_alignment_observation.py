"""Research-only no-lookahead alignment of SMA states to return periods."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation import (
    ResearchReturnPoint,
    ResearchReturnSeriesObservation,
)
from algotrader.research.sma_research_observation import SmaResearchObservation

__all__ = [
    "SMA_RETURN_ALIGNMENT_STATES",
    "SmaReturnAlignmentObservation",
    "SmaReturnAlignmentPeriod",
    "build_sma_return_alignment_observation",
]

_OBSERVATION_TYPE = "sma_return_alignment_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_ALIGNMENT_RULE = "latest_sma_as_of_on_or_before_return_start"
SMA_RETURN_ALIGNMENT_STATES = (
    "sma_state_available",
    "sma_state_unavailable",
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_DEFAULT_LIMITATIONS = (
    "aligns existing SMA observation metadata to existing return periods only",
    "uses latest SMA observation with as_of on or before each return start date",
    "does not derive return-adjusted metrics from SMA state",
)
_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("strategy-return computation"),
    _not("equity-curve computation"),
    _not("cost model"),
    _not("bench", "mark comparison"),
    _not("positions"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mutation authority"),
    _not("paper read", "iness"),
    _not("live read", "iness"),
    _not("capital authority"),
    _not("tra", "ding authority"),
)
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
class SmaReturnAlignmentPeriod:
    """One research-only SMA-state alignment for an existing return period."""

    return_start_date: str
    return_end_date: str
    simple_return: Decimal
    alignment_state: str
    sma_observation_as_of: str | None
    sma_observation_state: str | None
    source_return: ResearchReturnPoint
    source_sma_observation: SmaResearchObservation | None

    def __post_init__(self) -> None:
        source_return = _require_return_point(self.source_return)
        source_sma_observation = _optional_sma_observation(
            self.source_sma_observation
        )
        object.__setattr__(
            self,
            "return_start_date",
            _iso_date(self.return_start_date, "return_start_date"),
        )
        object.__setattr__(
            self,
            "return_end_date",
            _iso_date(self.return_end_date, "return_end_date"),
        )
        object.__setattr__(
            self,
            "simple_return",
            _decimal(self.simple_return, "simple_return"),
        )
        object.__setattr__(
            self,
            "alignment_state",
            _alignment_state(self.alignment_state),
        )
        object.__setattr__(
            self,
            "sma_observation_as_of",
            _optional_iso_date(self.sma_observation_as_of, "sma_observation_as_of"),
        )
        object.__setattr__(
            self,
            "sma_observation_state",
            _optional_string(self.sma_observation_state, "sma_observation_state"),
        )
        object.__setattr__(self, "source_return", source_return)
        object.__setattr__(
            self,
            "source_sma_observation",
            source_sma_observation,
        )
        _validate_period_source_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only alignment period metadata."""

        return {
            "return_start_date": self.return_start_date,
            "return_end_date": self.return_end_date,
            "simple_return": str(self.simple_return),
            "alignment_state": self.alignment_state,
            "sma_observation_as_of": self.sma_observation_as_of,
            "sma_observation_state": self.sma_observation_state,
            "source_return": self.source_return.to_dict(),
            "source_sma_observation": (
                None
                if self.source_sma_observation is None
                else self.source_sma_observation.to_dict()
            ),
        }


@dataclass(frozen=True, slots=True)
class SmaReturnAlignmentObservation:
    """Research-only no-lookahead alignment of SMA states to return periods."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    research_scope: str
    alignment_rule: str
    symbol: str
    as_of: str
    source_return_count: int
    source_sma_observation_count: int
    aligned_return_count: int
    unaligned_return_count: int
    alignment_periods: tuple[SmaReturnAlignmentPeriod, ...]
    source_return_observation: ResearchReturnSeriesObservation
    source_sma_observations: tuple[SmaResearchObservation, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_return_observation = _require_return_observation(
            self.source_return_observation
        )
        source_sma_observations = _sma_observation_tuple(
            self.source_sma_observations
        )
        alignment_periods = _alignment_period_tuple(self.alignment_periods)
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
            self.research_scope,
            self.alignment_rule,
        )
        object.__setattr__(self, "symbol", _advisory_text(self.symbol, "symbol"))
        object.__setattr__(self, "as_of", _iso_date(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "source_return_count",
            _non_negative_int(self.source_return_count, "source_return_count"),
        )
        object.__setattr__(
            self,
            "source_sma_observation_count",
            _non_negative_int(
                self.source_sma_observation_count,
                "source_sma_observation_count",
            ),
        )
        object.__setattr__(
            self,
            "aligned_return_count",
            _non_negative_int(self.aligned_return_count, "aligned_return_count"),
        )
        object.__setattr__(
            self,
            "unaligned_return_count",
            _non_negative_int(self.unaligned_return_count, "unaligned_return_count"),
        )
        object.__setattr__(self, "alignment_periods", alignment_periods)
        object.__setattr__(
            self,
            "source_return_observation",
            source_return_observation,
        )
        object.__setattr__(
            self,
            "source_sma_observations",
            source_sma_observations,
        )
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _deduped_non_claims(self.non_claims))
        _validate_alignment_consistency(
            self,
            source_return_observation,
            source_sma_observations,
            alignment_periods,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only SMA-return alignment metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "research_scope": self.research_scope,
            "alignment_rule": self.alignment_rule,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "source_return_count": self.source_return_count,
            "source_sma_observation_count": self.source_sma_observation_count,
            "aligned_return_count": self.aligned_return_count,
            "unaligned_return_count": self.unaligned_return_count,
            "alignment_periods": [
                period.to_dict() for period in self.alignment_periods
            ],
            "source_return_observation": self.source_return_observation.to_dict(),
            "source_sma_observations": [
                observation.to_dict() for observation in self.source_sma_observations
            ],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_return_alignment_observation(
    sma_observations: tuple[SmaResearchObservation, ...] | list[SmaResearchObservation],
    return_observation: ResearchReturnSeriesObservation,
) -> SmaReturnAlignmentObservation:
    """Build research-only no-lookahead SMA-state alignment rows."""

    source_return_observation = _require_return_observation(return_observation)
    source_sma_observations = _sma_observation_tuple(sma_observations)
    _validate_source_symbols(source_return_observation, source_sma_observations)
    _validate_source_as_of(source_return_observation, source_sma_observations)
    alignment_periods = tuple(
        _build_alignment_period(return_point, source_sma_observations)
        for return_point in source_return_observation.returns
    )
    aligned_return_count = sum(
        1
        for period in alignment_periods
        if period.alignment_state == "sma_state_available"
    )
    unaligned_return_count = len(alignment_periods) - aligned_return_count

    return SmaReturnAlignmentObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        alignment_rule=_ALIGNMENT_RULE,
        symbol=source_return_observation.symbol,
        as_of=source_return_observation.as_of,
        source_return_count=source_return_observation.return_count,
        source_sma_observation_count=len(source_sma_observations),
        aligned_return_count=aligned_return_count,
        unaligned_return_count=unaligned_return_count,
        alignment_periods=alignment_periods,
        source_return_observation=source_return_observation,
        source_sma_observations=source_sma_observations,
        limitations=_alignment_limitations(
            source_return_observation,
            source_sma_observations,
        ),
        non_claims=_alignment_non_claims(
            source_return_observation,
            source_sma_observations,
        ),
    )


def _build_alignment_period(
    return_point: ResearchReturnPoint,
    source_sma_observations: tuple[SmaResearchObservation, ...],
) -> SmaReturnAlignmentPeriod:
    source_sma_observation = _latest_sma_observation(
        return_point.start_date,
        source_sma_observations,
    )
    if source_sma_observation is None:
        return SmaReturnAlignmentPeriod(
            return_start_date=return_point.start_date,
            return_end_date=return_point.end_date,
            simple_return=return_point.simple_return,
            alignment_state="sma_state_unavailable",
            sma_observation_as_of=None,
            sma_observation_state=None,
            source_return=return_point,
            source_sma_observation=None,
        )

    return SmaReturnAlignmentPeriod(
        return_start_date=return_point.start_date,
        return_end_date=return_point.end_date,
        simple_return=return_point.simple_return,
        alignment_state="sma_state_available",
        sma_observation_as_of=source_sma_observation.as_of,
        sma_observation_state=source_sma_observation.position_vs_sma,
        source_return=return_point,
        source_sma_observation=source_sma_observation,
    )


def _latest_sma_observation(
    return_start_date: str,
    source_sma_observations: tuple[SmaResearchObservation, ...],
) -> SmaResearchObservation | None:
    latest: SmaResearchObservation | None = None
    for observation in source_sma_observations:
        if observation.as_of > return_start_date:
            break
        latest = observation

    return latest


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
    research_scope: object,
    alignment_rule: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly sma_return_alignment_observation."
        )
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")
    if research_scope != _RESEARCH_SCOPE:
        raise ValidationError("research_scope must be exactly research_only.")
    if alignment_rule != _ALIGNMENT_RULE:
        raise ValidationError(
            "alignment_rule must be exactly "
            "latest_sma_as_of_on_or_before_return_start."
        )


def _validate_period_source_consistency(
    period: SmaReturnAlignmentPeriod,
) -> None:
    if period.return_start_date != period.source_return.start_date:
        raise ValidationError("return_start_date must match source_return.")
    if period.return_end_date != period.source_return.end_date:
        raise ValidationError("return_end_date must match source_return.")
    if period.simple_return != period.source_return.simple_return:
        raise ValidationError("simple_return must match source_return.")

    if period.source_sma_observation is None:
        if period.alignment_state != "sma_state_unavailable":
            raise ValidationError(
                "alignment_state must be unavailable without a source SMA observation."
            )
        if (
            period.sma_observation_as_of is not None
            or period.sma_observation_state is not None
        ):
            raise ValidationError(
                "SMA observation fields must be None when alignment is unavailable."
            )
        return

    if period.alignment_state != "sma_state_available":
        raise ValidationError(
            "alignment_state must be available with a source SMA observation."
        )
    if period.sma_observation_as_of != period.source_sma_observation.as_of:
        raise ValidationError("sma_observation_as_of must match source_sma_observation.")
    if period.sma_observation_state != period.source_sma_observation.position_vs_sma:
        raise ValidationError(
            "sma_observation_state must match source_sma_observation."
        )
    if period.source_sma_observation.as_of > period.return_start_date:
        raise ValidationError(
            "source_sma_observation must be available on or before return_start_date."
        )


def _validate_alignment_consistency(
    alignment: SmaReturnAlignmentObservation,
    source_return_observation: ResearchReturnSeriesObservation,
    source_sma_observations: tuple[SmaResearchObservation, ...],
    alignment_periods: tuple[SmaReturnAlignmentPeriod, ...],
) -> None:
    _validate_source_symbols(source_return_observation, source_sma_observations)
    _validate_source_as_of(source_return_observation, source_sma_observations)
    _validate_matches_source("symbol", alignment.symbol, source_return_observation.symbol)
    _validate_matches_source("as_of", alignment.as_of, source_return_observation.as_of)
    _validate_matches_source(
        "source_return_count",
        alignment.source_return_count,
        source_return_observation.return_count,
    )
    _validate_matches_source(
        "source_sma_observation_count",
        alignment.source_sma_observation_count,
        len(source_sma_observations),
    )
    if len(alignment_periods) != source_return_observation.return_count:
        raise ValidationError(
            "alignment_periods must match source_return_observation returns."
        )

    source_sma_ids = {id(observation) for observation in source_sma_observations}
    aligned_return_count = 0
    for period, return_point in zip(
        alignment_periods,
        source_return_observation.returns,
    ):
        if period.source_return is not return_point:
            raise ValidationError("alignment period source_return must be preserved.")

        expected_sma = _latest_sma_observation(
            period.return_start_date,
            source_sma_observations,
        )
        if expected_sma is None:
            if period.source_sma_observation is not None:
                raise ValidationError(
                    "alignment period must not use unavailable SMA observations."
                )
            continue

        if period.source_sma_observation is not expected_sma:
            raise ValidationError(
                "alignment period must use the latest available SMA observation."
            )
        if id(period.source_sma_observation) not in source_sma_ids:
            raise ValidationError(
                "alignment period source_sma_observation must be preserved."
            )
        aligned_return_count += 1

    unaligned_return_count = len(alignment_periods) - aligned_return_count
    _validate_matches_source(
        "aligned_return_count",
        alignment.aligned_return_count,
        aligned_return_count,
    )
    _validate_matches_source(
        "unaligned_return_count",
        alignment.unaligned_return_count,
        unaligned_return_count,
    )


def _validate_source_symbols(
    source_return_observation: ResearchReturnSeriesObservation,
    source_sma_observations: tuple[SmaResearchObservation, ...],
) -> None:
    for observation in source_sma_observations:
        if observation.symbol != source_return_observation.symbol:
            raise ValidationError(
                "source_sma_observations must match return observation symbol."
            )


def _validate_source_as_of(
    source_return_observation: ResearchReturnSeriesObservation,
    source_sma_observations: tuple[SmaResearchObservation, ...],
) -> None:
    for observation in source_sma_observations:
        if observation.as_of > source_return_observation.as_of:
            raise ValidationError(
                "source_sma_observations must not be after return observation as_of."
            )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source observations.")


def _require_return_point(value: object) -> ResearchReturnPoint:
    if type(value) is not ResearchReturnPoint:
        raise ValidationError("source_return must be a ResearchReturnPoint.")

    return value


def _require_return_observation(value: object) -> ResearchReturnSeriesObservation:
    if type(value) is not ResearchReturnSeriesObservation:
        raise ValidationError(
            "source_return_observation must be a ResearchReturnSeriesObservation."
        )

    return value


def _optional_sma_observation(value: object) -> SmaResearchObservation | None:
    if value is None:
        return None
    if type(value) is not SmaResearchObservation:
        raise ValidationError(
            "source_sma_observation must be a SmaResearchObservation or None."
        )

    return value


def _sma_observation_tuple(
    values: object,
) -> tuple[SmaResearchObservation, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(
            "source_sma_observations must be a tuple or list of SmaResearchObservation."
        )

    observations = tuple(values)
    seen_as_of: set[str] = set()
    for index, observation in enumerate(observations):
        if type(observation) is not SmaResearchObservation:
            raise ValidationError(
                "source_sma_observations"
                f"[{index}] must be a SmaResearchObservation."
            )
        if observation.as_of in seen_as_of:
            raise ValidationError(
                "source_sma_observations must not contain duplicate as_of dates."
            )
        seen_as_of.add(observation.as_of)

    return tuple(sorted(observations, key=lambda observation: observation.as_of))


def _alignment_period_tuple(
    values: object,
) -> tuple[SmaReturnAlignmentPeriod, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(
            "alignment_periods must be a tuple or list of SmaReturnAlignmentPeriod."
        )

    periods = tuple(values)
    for index, period in enumerate(periods):
        if type(period) is not SmaReturnAlignmentPeriod:
            raise ValidationError(
                f"alignment_periods[{index}] must be a SmaReturnAlignmentPeriod."
            )

    return periods


def _alignment_state(value: object) -> str:
    state = _required_string(value, "alignment_state")
    if state not in SMA_RETURN_ALIGNMENT_STATES:
        allowed = ", ".join(SMA_RETURN_ALIGNMENT_STATES)
        raise ValidationError(f"alignment_state must be one of: {allowed}.")

    return state


def _iso_date(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO YYYY-MM-DD date string."
        ) from exc

    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")

    return value


def _optional_iso_date(value: object, field_name: str) -> str | None:
    if value is None:
        return None

    return _iso_date(value, field_name)


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None

    return _required_string(value, field_name)


def _advisory_text(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    lowered = text.lower()
    if any(fragment in lowered for fragment in _FORBIDDEN_TEXT_TOKENS):
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

    missing = tuple(claim for claim in _REQUIRED_NON_CLAIMS if claim not in items)
    if missing:
        raise ValidationError(
            "non_claims must include required advisory research non-claims."
        )

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


def _decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _alignment_limitations(
    source_return_observation: ResearchReturnSeriesObservation,
    source_sma_observations: tuple[SmaResearchObservation, ...],
) -> tuple[str, ...]:
    source_limitations = tuple(
        limitation
        for observation in source_sma_observations
        for limitation in observation.limitations
    )
    return _dedupe(
        (
            *_DEFAULT_LIMITATIONS,
            *source_return_observation.limitations,
            *source_limitations,
        )
    )


def _alignment_non_claims(
    source_return_observation: ResearchReturnSeriesObservation,
    source_sma_observations: tuple[SmaResearchObservation, ...],
) -> tuple[str, ...]:
    source_non_claims = tuple(
        non_claim
        for observation in source_sma_observations
        for non_claim in observation.non_claims
    )
    return _dedupe(
        (
            *_REQUIRED_NON_CLAIMS,
            *source_return_observation.non_claims,
            *source_non_claims,
        )
    )


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)
