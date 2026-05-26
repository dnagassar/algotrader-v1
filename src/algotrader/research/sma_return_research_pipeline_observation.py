"""Research-only composition of SMA return research observations."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.sma_conditional_return_selection_observation import (
    SmaConditionalReturnSelectionObservation,
)
from algotrader.research.sma_conditional_return_selection_summary_observation import (
    SmaConditionalReturnSelectionSummaryObservation,
)
from algotrader.research.sma_return_alignment_observation import (
    SmaReturnAlignmentObservation,
)
from algotrader.research.sma_return_alignment_summary_observation import (
    SmaReturnAlignmentSummaryObservation,
)
from algotrader.research.sma_selected_source_return_series_observation import (
    SmaSelectedSourceReturnSeriesObservation,
)
from algotrader.research.sma_selected_source_return_summary_observation import (
    SmaSelectedSourceReturnSummaryObservation,
)

__all__ = [
    "SMA_RETURN_RESEARCH_PIPELINE_STATES",
    "SmaReturnResearchPipelineObservation",
    "build_sma_return_research_pipeline_observation",
]

_OBSERVATION_TYPE = "sma_return_research_pipeline_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_PIPELINE_RULE = "compose_existing_sma_return_research_artifacts"
_ALIGNMENT_RULE = "latest_sma_as_of_on_or_before_return_start"
_SELECTION_RULE = "include_when_sma_state_is_above"
_SOURCE_RETURN_VALUE_RULE = (
    "collect_source_simple_returns_from_included_selection_periods"
)
_PIPELINE_COMPONENT_COUNT = 6
SMA_RETURN_RESEARCH_PIPELINE_STATES = (
    "sma_return_research_pipeline_composed",
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_DEFAULT_LIMITATIONS = (
    "composes existing SMA return research artifacts only",
    "preserves source artifact identity and derivation chain metadata",
    "does not calculate new return values or performance metrics",
)
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
    _not("selected source return strategy performance result"),
    _not("selected source return port", "folio result"),
    _not("selected source return invested result"),
    _not("selected source return back", "test result"),
    _not("SMA return research pipeline back", "test result"),
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
class SmaReturnResearchPipelineObservation:
    """Advisory-only composition of existing SMA return research artifacts."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    research_scope: str
    pipeline_rule: str
    alignment_rule: str
    selection_rule: str
    source_return_value_rule: str
    symbol: str
    as_of: str
    pipeline_component_count: int
    source_return_count: int
    source_sma_observation_count: int
    alignment_period_count: int
    selection_period_count: int
    included_period_count: int
    excluded_period_count: int
    selected_source_return_count: int
    alignment_summary_state: str
    selection_summary_state: str
    selected_source_return_summary_state: str
    pipeline_state: str
    source_alignment_observation: SmaReturnAlignmentObservation
    source_alignment_summary_observation: SmaReturnAlignmentSummaryObservation
    source_selection_observation: SmaConditionalReturnSelectionObservation
    source_selection_summary_observation: (
        SmaConditionalReturnSelectionSummaryObservation
    )
    source_selected_source_return_series_observation: (
        SmaSelectedSourceReturnSeriesObservation
    )
    source_selected_source_return_summary_observation: (
        SmaSelectedSourceReturnSummaryObservation
    )
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_alignment_observation = _require_source_alignment_observation(
            self.source_alignment_observation
        )
        source_alignment_summary_observation = (
            _require_source_alignment_summary_observation(
                self.source_alignment_summary_observation
            )
        )
        source_selection_observation = _require_source_selection_observation(
            self.source_selection_observation
        )
        source_selection_summary_observation = (
            _require_source_selection_summary_observation(
                self.source_selection_summary_observation
            )
        )
        source_selected_source_return_series_observation = (
            _require_source_selected_source_return_series_observation(
                self.source_selected_source_return_series_observation
            )
        )
        source_selected_source_return_summary_observation = (
            _require_source_selected_source_return_summary_observation(
                self.source_selected_source_return_summary_observation
            )
        )
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
            self.research_scope,
            self.pipeline_rule,
            self.alignment_rule,
            self.selection_rule,
            self.source_return_value_rule,
        )
        object.__setattr__(self, "symbol", _advisory_text(self.symbol, "symbol"))
        object.__setattr__(self, "as_of", _required_string(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "pipeline_component_count",
            _non_negative_int(
                self.pipeline_component_count,
                "pipeline_component_count",
            ),
        )
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
            "excluded_period_count",
            _non_negative_int(self.excluded_period_count, "excluded_period_count"),
        )
        object.__setattr__(
            self,
            "selected_source_return_count",
            _non_negative_int(
                self.selected_source_return_count,
                "selected_source_return_count",
            ),
        )
        object.__setattr__(
            self,
            "alignment_summary_state",
            _required_string(self.alignment_summary_state, "alignment_summary_state"),
        )
        object.__setattr__(
            self,
            "selection_summary_state",
            _required_string(self.selection_summary_state, "selection_summary_state"),
        )
        object.__setattr__(
            self,
            "selected_source_return_summary_state",
            _required_string(
                self.selected_source_return_summary_state,
                "selected_source_return_summary_state",
            ),
        )
        object.__setattr__(self, "pipeline_state", _pipeline_state(self.pipeline_state))
        object.__setattr__(
            self,
            "source_alignment_observation",
            source_alignment_observation,
        )
        object.__setattr__(
            self,
            "source_alignment_summary_observation",
            source_alignment_summary_observation,
        )
        object.__setattr__(
            self,
            "source_selection_observation",
            source_selection_observation,
        )
        object.__setattr__(
            self,
            "source_selection_summary_observation",
            source_selection_summary_observation,
        )
        object.__setattr__(
            self,
            "source_selected_source_return_series_observation",
            source_selected_source_return_series_observation,
        )
        object.__setattr__(
            self,
            "source_selected_source_return_summary_observation",
            source_selected_source_return_summary_observation,
        )
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _deduped_non_claims(self.non_claims))
        _validate_source_pipeline(
            self,
            source_alignment_observation,
            source_alignment_summary_observation,
            source_selection_observation,
            source_selection_summary_observation,
            source_selected_source_return_series_observation,
            source_selected_source_return_summary_observation,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only SMA return pipeline metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "research_scope": self.research_scope,
            "pipeline_rule": self.pipeline_rule,
            "alignment_rule": self.alignment_rule,
            "selection_rule": self.selection_rule,
            "source_return_value_rule": self.source_return_value_rule,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "pipeline_component_count": self.pipeline_component_count,
            "source_return_count": self.source_return_count,
            "source_sma_observation_count": self.source_sma_observation_count,
            "alignment_period_count": self.alignment_period_count,
            "selection_period_count": self.selection_period_count,
            "included_period_count": self.included_period_count,
            "excluded_period_count": self.excluded_period_count,
            "selected_source_return_count": self.selected_source_return_count,
            "alignment_summary_state": self.alignment_summary_state,
            "selection_summary_state": self.selection_summary_state,
            "selected_source_return_summary_state": (
                self.selected_source_return_summary_state
            ),
            "pipeline_state": self.pipeline_state,
            "source_alignment_observation": (
                self.source_alignment_observation.to_dict()
            ),
            "source_alignment_summary_observation": (
                self.source_alignment_summary_observation.to_dict()
            ),
            "source_selection_observation": (
                self.source_selection_observation.to_dict()
            ),
            "source_selection_summary_observation": (
                self.source_selection_summary_observation.to_dict()
            ),
            "source_selected_source_return_series_observation": (
                self.source_selected_source_return_series_observation.to_dict()
            ),
            "source_selected_source_return_summary_observation": (
                self.source_selected_source_return_summary_observation.to_dict()
            ),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_return_research_pipeline_observation(
    alignment_observation: SmaReturnAlignmentObservation,
    alignment_summary_observation: SmaReturnAlignmentSummaryObservation,
    selection_observation: SmaConditionalReturnSelectionObservation,
    selection_summary_observation: SmaConditionalReturnSelectionSummaryObservation,
    selected_source_return_series_observation: (
        SmaSelectedSourceReturnSeriesObservation
    ),
    selected_source_return_summary_observation: (
        SmaSelectedSourceReturnSummaryObservation
    ),
) -> SmaReturnResearchPipelineObservation:
    """Compose existing SMA return research artifacts into one observation."""

    source_alignment_observation = _require_source_alignment_observation(
        alignment_observation
    )
    source_alignment_summary_observation = (
        _require_source_alignment_summary_observation(
            alignment_summary_observation
        )
    )
    source_selection_observation = _require_source_selection_observation(
        selection_observation
    )
    source_selection_summary_observation = (
        _require_source_selection_summary_observation(
            selection_summary_observation
        )
    )
    source_selected_source_return_series_observation = (
        _require_source_selected_source_return_series_observation(
            selected_source_return_series_observation
        )
    )
    source_selected_source_return_summary_observation = (
        _require_source_selected_source_return_summary_observation(
            selected_source_return_summary_observation
        )
    )

    return SmaReturnResearchPipelineObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        pipeline_rule=_PIPELINE_RULE,
        alignment_rule=source_alignment_observation.alignment_rule,
        selection_rule=source_selection_observation.selection_rule,
        source_return_value_rule=(
            source_selected_source_return_series_observation.source_return_value_rule
        ),
        symbol=source_alignment_observation.symbol,
        as_of=source_alignment_observation.as_of,
        pipeline_component_count=_PIPELINE_COMPONENT_COUNT,
        source_return_count=source_alignment_observation.source_return_count,
        source_sma_observation_count=(
            source_alignment_observation.source_sma_observation_count
        ),
        alignment_period_count=source_selection_observation.alignment_period_count,
        selection_period_count=(
            source_selection_summary_observation.selection_period_count
        ),
        included_period_count=source_selection_observation.included_period_count,
        excluded_period_count=source_selection_observation.excluded_period_count,
        selected_source_return_count=(
            source_selected_source_return_series_observation.selected_source_return_count
        ),
        alignment_summary_state=source_alignment_summary_observation.summary_state,
        selection_summary_state=source_selection_summary_observation.summary_state,
        selected_source_return_summary_state=(
            source_selected_source_return_summary_observation.summary_state
        ),
        pipeline_state="sma_return_research_pipeline_composed",
        source_alignment_observation=source_alignment_observation,
        source_alignment_summary_observation=(
            source_alignment_summary_observation
        ),
        source_selection_observation=source_selection_observation,
        source_selection_summary_observation=source_selection_summary_observation,
        source_selected_source_return_series_observation=(
            source_selected_source_return_series_observation
        ),
        source_selected_source_return_summary_observation=(
            source_selected_source_return_summary_observation
        ),
        limitations=_pipeline_limitations(
            source_alignment_observation,
            source_alignment_summary_observation,
            source_selection_observation,
            source_selection_summary_observation,
            source_selected_source_return_series_observation,
            source_selected_source_return_summary_observation,
        ),
        non_claims=_pipeline_non_claims(
            source_alignment_observation,
            source_alignment_summary_observation,
            source_selection_observation,
            source_selection_summary_observation,
            source_selected_source_return_series_observation,
            source_selected_source_return_summary_observation,
        ),
    )


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
    research_scope: object,
    pipeline_rule: object,
    alignment_rule: object,
    selection_rule: object,
    source_return_value_rule: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly "
            "sma_return_research_pipeline_observation."
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
    if pipeline_rule != _PIPELINE_RULE:
        raise ValidationError(
            "pipeline_rule must be exactly "
            "compose_existing_sma_return_research_artifacts."
        )
    if alignment_rule != _ALIGNMENT_RULE:
        raise ValidationError(
            "alignment_rule must be exactly "
            "latest_sma_as_of_on_or_before_return_start."
        )
    if selection_rule != _SELECTION_RULE:
        raise ValidationError(
            "selection_rule must be exactly include_when_sma_state_is_above."
        )
    if source_return_value_rule != _SOURCE_RETURN_VALUE_RULE:
        raise ValidationError(
            "source_return_value_rule must be exactly "
            "collect_source_simple_returns_from_included_selection_periods."
        )


def _validate_source_pipeline(
    pipeline: SmaReturnResearchPipelineObservation,
    alignment: SmaReturnAlignmentObservation,
    alignment_summary: SmaReturnAlignmentSummaryObservation,
    selection: SmaConditionalReturnSelectionObservation,
    selection_summary: SmaConditionalReturnSelectionSummaryObservation,
    selected_series: SmaSelectedSourceReturnSeriesObservation,
    selected_summary: SmaSelectedSourceReturnSummaryObservation,
) -> None:
    if alignment_summary.source_alignment_observation is not alignment:
        raise ValidationError(
            "source_alignment_summary_observation source alignment must be preserved."
        )
    if selection.source_alignment_observation is not alignment:
        raise ValidationError(
            "source_selection_observation source alignment must be preserved."
        )
    if selection_summary.source_selection_observation is not selection:
        raise ValidationError(
            "source_selection_summary_observation source selection must be preserved."
        )
    if selected_series.source_selection_observation is not selection:
        raise ValidationError(
            "source_selected_source_return_series_observation source selection "
            "must be preserved."
        )
    if (
        selected_summary.source_selected_source_return_series_observation
        is not selected_series
    ):
        raise ValidationError(
            "source_selected_source_return_summary_observation source series "
            "must be preserved."
        )

    for field_name, value, expected in _source_metadata_checks(
        pipeline,
        alignment,
        alignment_summary,
        selection,
        selection_summary,
        selected_series,
        selected_summary,
    ):
        _validate_matches_source(field_name, value, expected)

    _validate_matches_source(
        "limitations",
        pipeline.limitations,
        _pipeline_limitations(
            alignment,
            alignment_summary,
            selection,
            selection_summary,
            selected_series,
            selected_summary,
        ),
    )
    _validate_matches_source(
        "non_claims",
        pipeline.non_claims,
        _pipeline_non_claims(
            alignment,
            alignment_summary,
            selection,
            selection_summary,
            selected_series,
            selected_summary,
        ),
    )


def _source_metadata_checks(
    pipeline: SmaReturnResearchPipelineObservation,
    alignment: SmaReturnAlignmentObservation,
    alignment_summary: SmaReturnAlignmentSummaryObservation,
    selection: SmaConditionalReturnSelectionObservation,
    selection_summary: SmaConditionalReturnSelectionSummaryObservation,
    selected_series: SmaSelectedSourceReturnSeriesObservation,
    selected_summary: SmaSelectedSourceReturnSummaryObservation,
) -> tuple[tuple[str, object, object], ...]:
    return (
        ("symbol", pipeline.symbol, alignment.symbol),
        ("symbol", pipeline.symbol, alignment_summary.symbol),
        ("symbol", pipeline.symbol, selection.symbol),
        ("symbol", pipeline.symbol, selection_summary.symbol),
        ("symbol", pipeline.symbol, selected_series.symbol),
        ("symbol", pipeline.symbol, selected_summary.symbol),
        ("as_of", pipeline.as_of, alignment.as_of),
        ("as_of", pipeline.as_of, alignment_summary.as_of),
        ("as_of", pipeline.as_of, selection.as_of),
        ("as_of", pipeline.as_of, selection_summary.as_of),
        ("as_of", pipeline.as_of, selected_series.as_of),
        ("as_of", pipeline.as_of, selected_summary.as_of),
        (
            "pipeline_component_count",
            pipeline.pipeline_component_count,
            _PIPELINE_COMPONENT_COUNT,
        ),
        ("alignment_rule", pipeline.alignment_rule, alignment.alignment_rule),
        (
            "alignment_rule",
            pipeline.alignment_rule,
            alignment_summary.alignment_rule,
        ),
        ("selection_rule", pipeline.selection_rule, selection.selection_rule),
        (
            "selection_rule",
            pipeline.selection_rule,
            selection_summary.selection_rule,
        ),
        ("selection_rule", pipeline.selection_rule, selected_series.selection_rule),
        ("selection_rule", pipeline.selection_rule, selected_summary.selection_rule),
        (
            "source_return_value_rule",
            pipeline.source_return_value_rule,
            selected_series.source_return_value_rule,
        ),
        (
            "source_return_value_rule",
            pipeline.source_return_value_rule,
            selected_summary.source_return_value_rule,
        ),
        (
            "source_return_count",
            pipeline.source_return_count,
            alignment.source_return_count,
        ),
        (
            "source_return_count",
            pipeline.source_return_count,
            alignment_summary.source_return_count,
        ),
        (
            "source_return_count",
            pipeline.source_return_count,
            selection.source_return_count,
        ),
        (
            "source_return_count",
            pipeline.source_return_count,
            selection_summary.source_return_count,
        ),
        (
            "source_return_count",
            pipeline.source_return_count,
            selected_series.source_return_count,
        ),
        (
            "source_return_count",
            pipeline.source_return_count,
            selected_summary.source_return_count,
        ),
        (
            "source_sma_observation_count",
            pipeline.source_sma_observation_count,
            alignment.source_sma_observation_count,
        ),
        (
            "source_sma_observation_count",
            pipeline.source_sma_observation_count,
            alignment_summary.source_sma_observation_count,
        ),
        (
            "source_sma_observation_count",
            pipeline.source_sma_observation_count,
            selection.source_sma_observation_count,
        ),
        (
            "source_sma_observation_count",
            pipeline.source_sma_observation_count,
            selection_summary.source_sma_observation_count,
        ),
        (
            "source_sma_observation_count",
            pipeline.source_sma_observation_count,
            selected_series.source_sma_observation_count,
        ),
        (
            "source_sma_observation_count",
            pipeline.source_sma_observation_count,
            selected_summary.source_sma_observation_count,
        ),
        (
            "alignment_period_count",
            pipeline.alignment_period_count,
            alignment_summary.alignment_period_count,
        ),
        (
            "alignment_period_count",
            pipeline.alignment_period_count,
            selection.alignment_period_count,
        ),
        (
            "alignment_period_count",
            pipeline.alignment_period_count,
            selection_summary.alignment_period_count,
        ),
        (
            "alignment_period_count",
            pipeline.alignment_period_count,
            selected_series.alignment_period_count,
        ),
        (
            "alignment_period_count",
            pipeline.alignment_period_count,
            selected_summary.alignment_period_count,
        ),
        (
            "selection_period_count",
            pipeline.selection_period_count,
            selection_summary.selection_period_count,
        ),
        (
            "selection_period_count",
            pipeline.selection_period_count,
            selected_series.selection_period_count,
        ),
        (
            "selection_period_count",
            pipeline.selection_period_count,
            selected_summary.selection_period_count,
        ),
        (
            "included_period_count",
            pipeline.included_period_count,
            selection.included_period_count,
        ),
        (
            "included_period_count",
            pipeline.included_period_count,
            selection_summary.included_period_count,
        ),
        (
            "included_period_count",
            pipeline.included_period_count,
            selected_series.included_period_count,
        ),
        (
            "included_period_count",
            pipeline.included_period_count,
            selected_summary.included_period_count,
        ),
        (
            "excluded_period_count",
            pipeline.excluded_period_count,
            selection.excluded_period_count,
        ),
        (
            "excluded_period_count",
            pipeline.excluded_period_count,
            selection_summary.excluded_period_count,
        ),
        (
            "selected_source_return_count",
            pipeline.selected_source_return_count,
            selected_series.selected_source_return_count,
        ),
        (
            "selected_source_return_count",
            pipeline.selected_source_return_count,
            selected_summary.selected_source_return_count,
        ),
        (
            "alignment_summary_state",
            pipeline.alignment_summary_state,
            alignment_summary.summary_state,
        ),
        (
            "selection_summary_state",
            pipeline.selection_summary_state,
            selection_summary.summary_state,
        ),
        (
            "selected_source_return_summary_state",
            pipeline.selected_source_return_summary_state,
            selected_summary.summary_state,
        ),
        (
            "pipeline_state",
            pipeline.pipeline_state,
            "sma_return_research_pipeline_composed",
        ),
    )


def _require_source_alignment_observation(
    value: object,
) -> SmaReturnAlignmentObservation:
    if type(value) is not SmaReturnAlignmentObservation:
        raise ValidationError(
            "source_alignment_observation must be a "
            "SmaReturnAlignmentObservation."
        )

    return value


def _require_source_alignment_summary_observation(
    value: object,
) -> SmaReturnAlignmentSummaryObservation:
    if type(value) is not SmaReturnAlignmentSummaryObservation:
        raise ValidationError(
            "source_alignment_summary_observation must be a "
            "SmaReturnAlignmentSummaryObservation."
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


def _require_source_selection_summary_observation(
    value: object,
) -> SmaConditionalReturnSelectionSummaryObservation:
    if type(value) is not SmaConditionalReturnSelectionSummaryObservation:
        raise ValidationError(
            "source_selection_summary_observation must be a "
            "SmaConditionalReturnSelectionSummaryObservation."
        )

    return value


def _require_source_selected_source_return_series_observation(
    value: object,
) -> SmaSelectedSourceReturnSeriesObservation:
    if type(value) is not SmaSelectedSourceReturnSeriesObservation:
        raise ValidationError(
            "source_selected_source_return_series_observation must be a "
            "SmaSelectedSourceReturnSeriesObservation."
        )

    return value


def _require_source_selected_source_return_summary_observation(
    value: object,
) -> SmaSelectedSourceReturnSummaryObservation:
    if type(value) is not SmaSelectedSourceReturnSummaryObservation:
        raise ValidationError(
            "source_selected_source_return_summary_observation must be a "
            "SmaSelectedSourceReturnSummaryObservation."
        )

    return value


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source pipeline artifacts.")


def _pipeline_state(value: object) -> str:
    state = _required_string(value, "pipeline_state")
    if state not in SMA_RETURN_RESEARCH_PIPELINE_STATES:
        allowed = ", ".join(SMA_RETURN_RESEARCH_PIPELINE_STATES)
        raise ValidationError(f"pipeline_state must be one of: {allowed}.")

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


def _pipeline_limitations(
    alignment: SmaReturnAlignmentObservation,
    alignment_summary: SmaReturnAlignmentSummaryObservation,
    selection: SmaConditionalReturnSelectionObservation,
    selection_summary: SmaConditionalReturnSelectionSummaryObservation,
    selected_series: SmaSelectedSourceReturnSeriesObservation,
    selected_summary: SmaSelectedSourceReturnSummaryObservation,
) -> tuple[str, ...]:
    return _dedupe(
        (
            *_DEFAULT_LIMITATIONS,
            *alignment.limitations,
            *alignment_summary.limitations,
            *selection.limitations,
            *selection_summary.limitations,
            *selected_series.limitations,
            *selected_summary.limitations,
        )
    )


def _pipeline_non_claims(
    alignment: SmaReturnAlignmentObservation,
    alignment_summary: SmaReturnAlignmentSummaryObservation,
    selection: SmaConditionalReturnSelectionObservation,
    selection_summary: SmaConditionalReturnSelectionSummaryObservation,
    selected_series: SmaSelectedSourceReturnSeriesObservation,
    selected_summary: SmaSelectedSourceReturnSummaryObservation,
) -> tuple[str, ...]:
    return _dedupe(
        (
            *_REQUIRED_NON_CLAIMS,
            *alignment.non_claims,
            *alignment_summary.non_claims,
            *selection.non_claims,
            *selection_summary.non_claims,
            *selected_series.non_claims,
            *selected_summary.non_claims,
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
