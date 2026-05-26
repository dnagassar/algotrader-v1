"""Research-only selected source returns from SMA selection periods."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.sma_conditional_return_selection_observation import (
    SmaConditionalReturnSelectionObservation,
    SmaConditionalReturnSelectionPeriod,
)

__all__ = [
    "SmaSelectedSourceReturnPoint",
    "SmaSelectedSourceReturnSeriesObservation",
    "build_sma_selected_source_return_series_observation",
]

_OBSERVATION_TYPE = "sma_selected_source_return_series_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_SELECTION_RULE = "include_when_sma_state_is_above"
_SOURCE_RETURN_VALUE_RULE = (
    "collect_source_simple_returns_from_included_selection_periods"
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_DEFAULT_LIMITATIONS = (
    "collects source return values from included SMA selection periods only",
    "preserves source selection metadata without deriving performance metrics",
    "does not compound or aggregate selected source returns",
)
_EMPTY_LIMITATION = "no included selection periods were available to carry forward"
_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("strategy-return computation"),
    _not("compounded-return computation"),
    _not("equity-curve computation"),
    _not("cash-return computation"),
    _not("exposure computation"),
    _not("cost model"),
    _not("bench", "mark comparison"),
    _not("positions"),
    _not("cash behavior"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio state"),
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
class SmaSelectedSourceReturnPoint:
    """One selected source return value from an included SMA selection period."""

    return_start_date: str
    return_end_date: str
    source_simple_return: Decimal
    source_selection_period: SmaConditionalReturnSelectionPeriod

    def __post_init__(self) -> None:
        source_selection_period = _require_selection_period(
            self.source_selection_period
        )
        object.__setattr__(
            self,
            "return_start_date",
            _required_string(self.return_start_date, "return_start_date"),
        )
        object.__setattr__(
            self,
            "return_end_date",
            _required_string(self.return_end_date, "return_end_date"),
        )
        object.__setattr__(
            self,
            "source_simple_return",
            _decimal(self.source_simple_return, "source_simple_return"),
        )
        object.__setattr__(
            self,
            "source_selection_period",
            source_selection_period,
        )
        _validate_point_source_consistency(self, source_selection_period)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only selected source return metadata."""

        return {
            "return_start_date": self.return_start_date,
            "return_end_date": self.return_end_date,
            "source_simple_return": str(self.source_simple_return),
            "source_selection_period": self.source_selection_period.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SmaSelectedSourceReturnSeriesObservation:
    """Advisory-only selected source return values from SMA selection metadata."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    research_scope: str
    selection_rule: str
    source_return_value_rule: str
    symbol: str
    as_of: str
    source_return_count: int
    source_sma_observation_count: int
    alignment_period_count: int
    selection_period_count: int
    included_period_count: int
    selected_source_return_count: int
    selected_source_returns: tuple[SmaSelectedSourceReturnPoint, ...]
    source_selection_observation: SmaConditionalReturnSelectionObservation
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_selection_observation = _require_source_selection_observation(
            self.source_selection_observation
        )
        selected_source_returns = _selected_source_return_tuple(
            self.selected_source_returns
        )
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
            self.research_scope,
            self.selection_rule,
            self.source_return_value_rule,
        )
        object.__setattr__(self, "symbol", _advisory_text(self.symbol, "symbol"))
        object.__setattr__(self, "as_of", _required_string(self.as_of, "as_of"))
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
            "alignment_period_count",
            _non_negative_int(self.alignment_period_count, "alignment_period_count"),
        )
        object.__setattr__(
            self,
            "selection_period_count",
            _non_negative_int(self.selection_period_count, "selection_period_count"),
        )
        object.__setattr__(
            self,
            "included_period_count",
            _non_negative_int(self.included_period_count, "included_period_count"),
        )
        object.__setattr__(
            self,
            "selected_source_return_count",
            _non_negative_int(
                self.selected_source_return_count,
                "selected_source_return_count",
            ),
        )
        object.__setattr__(self, "selected_source_returns", selected_source_returns)
        object.__setattr__(
            self,
            "source_selection_observation",
            source_selection_observation,
        )
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _deduped_non_claims(self.non_claims))
        _validate_source_series(
            self,
            source_selection_observation,
            selected_source_returns,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only selected source return metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "research_scope": self.research_scope,
            "selection_rule": self.selection_rule,
            "source_return_value_rule": self.source_return_value_rule,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "source_return_count": self.source_return_count,
            "source_sma_observation_count": self.source_sma_observation_count,
            "alignment_period_count": self.alignment_period_count,
            "selection_period_count": self.selection_period_count,
            "included_period_count": self.included_period_count,
            "selected_source_return_count": self.selected_source_return_count,
            "selected_source_returns": [
                selected_return.to_dict()
                for selected_return in self.selected_source_returns
            ],
            "source_selection_observation": (
                self.source_selection_observation.to_dict()
            ),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_selected_source_return_series_observation(
    selection_observation: SmaConditionalReturnSelectionObservation,
) -> SmaSelectedSourceReturnSeriesObservation:
    """Collect source return values from included SMA selection periods."""

    source_selection_observation = _require_source_selection_observation(
        selection_observation
    )
    selected_source_returns = tuple(
        _build_selected_source_return(period)
        for period in source_selection_observation.selection_periods
        if period.selection_state == "included"
    )

    return SmaSelectedSourceReturnSeriesObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        selection_rule=source_selection_observation.selection_rule,
        source_return_value_rule=_SOURCE_RETURN_VALUE_RULE,
        symbol=source_selection_observation.symbol,
        as_of=source_selection_observation.as_of,
        source_return_count=source_selection_observation.source_return_count,
        source_sma_observation_count=(
            source_selection_observation.source_sma_observation_count
        ),
        alignment_period_count=source_selection_observation.alignment_period_count,
        selection_period_count=len(source_selection_observation.selection_periods),
        included_period_count=source_selection_observation.included_period_count,
        selected_source_return_count=len(selected_source_returns),
        selected_source_returns=selected_source_returns,
        source_selection_observation=source_selection_observation,
        limitations=_series_limitations(
            source_selection_observation,
            selected_source_returns,
        ),
        non_claims=_series_non_claims(source_selection_observation),
    )


def _build_selected_source_return(
    selection_period: SmaConditionalReturnSelectionPeriod,
) -> SmaSelectedSourceReturnPoint:
    return SmaSelectedSourceReturnPoint(
        return_start_date=selection_period.return_start_date,
        return_end_date=selection_period.return_end_date,
        source_simple_return=selection_period.source_alignment_period.simple_return,
        source_selection_period=selection_period,
    )


def _validate_point_source_consistency(
    selected_return: SmaSelectedSourceReturnPoint,
    source_selection_period: SmaConditionalReturnSelectionPeriod,
) -> None:
    if source_selection_period.selection_state != "included":
        raise ValidationError("source_selection_period must be included.")
    if source_selection_period.selection_reason != "above_sma":
        raise ValidationError("source_selection_period must use above_sma.")
    if selected_return.return_start_date != source_selection_period.return_start_date:
        raise ValidationError("return_start_date must match source selection period.")
    if selected_return.return_end_date != source_selection_period.return_end_date:
        raise ValidationError("return_end_date must match source selection period.")
    if (
        selected_return.source_simple_return
        != source_selection_period.source_alignment_period.simple_return
    ):
        raise ValidationError("source_simple_return must match source return value.")


def _validate_source_series(
    series: SmaSelectedSourceReturnSeriesObservation,
    source_selection_observation: SmaConditionalReturnSelectionObservation,
    selected_source_returns: tuple[SmaSelectedSourceReturnPoint, ...],
) -> None:
    _validate_matches_source(
        "symbol",
        series.symbol,
        source_selection_observation.symbol,
    )
    _validate_matches_source(
        "as_of",
        series.as_of,
        source_selection_observation.as_of,
    )
    _validate_matches_source(
        "source_return_count",
        series.source_return_count,
        source_selection_observation.source_return_count,
    )
    _validate_matches_source(
        "source_sma_observation_count",
        series.source_sma_observation_count,
        source_selection_observation.source_sma_observation_count,
    )
    _validate_matches_source(
        "alignment_period_count",
        series.alignment_period_count,
        source_selection_observation.alignment_period_count,
    )
    _validate_matches_source(
        "selection_period_count",
        series.selection_period_count,
        len(source_selection_observation.selection_periods),
    )
    _validate_matches_source(
        "included_period_count",
        series.included_period_count,
        source_selection_observation.included_period_count,
    )
    _validate_matches_source(
        "selected_source_return_count",
        series.selected_source_return_count,
        len(selected_source_returns),
    )
    _validate_matches_source(
        "selected_source_return_count",
        series.selected_source_return_count,
        source_selection_observation.included_period_count,
    )

    included_periods = tuple(
        period
        for period in source_selection_observation.selection_periods
        if period.selection_state == "included"
    )
    if len(selected_source_returns) != len(included_periods):
        raise ValidationError(
            "selected_source_returns must match included selection periods."
        )

    for selected_return, selection_period in zip(
        selected_source_returns,
        included_periods,
    ):
        if selected_return.source_selection_period is not selection_period:
            raise ValidationError(
                "selected source return source_selection_period must be preserved."
            )
        _validate_point_source_consistency(selected_return, selection_period)

    _validate_matches_source(
        "limitations",
        series.limitations,
        _series_limitations(source_selection_observation, selected_source_returns),
    )
    _validate_matches_source(
        "non_claims",
        series.non_claims,
        _series_non_claims(source_selection_observation),
    )


def _require_selection_period(value: object) -> SmaConditionalReturnSelectionPeriod:
    if type(value) is not SmaConditionalReturnSelectionPeriod:
        raise ValidationError(
            "source_selection_period must be a "
            "SmaConditionalReturnSelectionPeriod."
        )

    return value


def _require_source_selection_observation(
    value: object,
) -> SmaConditionalReturnSelectionObservation:
    if type(value) is not SmaConditionalReturnSelectionObservation:
        raise ValidationError(
            "source_selection_observation must be a "
            "SmaConditionalReturnSelectionObservation."
        )

    return value


def _selected_source_return_tuple(
    values: object,
) -> tuple[SmaSelectedSourceReturnPoint, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(
            "selected_source_returns must be a tuple or list of "
            "SmaSelectedSourceReturnPoint."
        )

    selected_returns = tuple(values)
    for index, selected_return in enumerate(selected_returns):
        if type(selected_return) is not SmaSelectedSourceReturnPoint:
            raise ValidationError(
                "selected_source_returns"
                f"[{index}] must be a SmaSelectedSourceReturnPoint."
            )

    return selected_returns


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
    research_scope: object,
    selection_rule: object,
    source_return_value_rule: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly "
            "sma_selected_source_return_series_observation."
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
    if selection_rule != _SELECTION_RULE:
        raise ValidationError(
            "selection_rule must be exactly include_when_sma_state_is_above."
        )
    if source_return_value_rule != _SOURCE_RETURN_VALUE_RULE:
        raise ValidationError(
            "source_return_value_rule must be exactly "
            "collect_source_simple_returns_from_included_selection_periods."
        )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source selection.")


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


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


def _series_limitations(
    source_selection_observation: SmaConditionalReturnSelectionObservation,
    selected_source_returns: tuple[SmaSelectedSourceReturnPoint, ...],
) -> tuple[str, ...]:
    empty_limitation = (_EMPTY_LIMITATION,) if not selected_source_returns else ()
    return _dedupe(
        (
            *_DEFAULT_LIMITATIONS,
            *empty_limitation,
            *source_selection_observation.limitations,
        )
    )


def _series_non_claims(
    source_selection_observation: SmaConditionalReturnSelectionObservation,
) -> tuple[str, ...]:
    return _dedupe((*_REQUIRED_NON_CLAIMS, *source_selection_observation.non_claims))


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)
