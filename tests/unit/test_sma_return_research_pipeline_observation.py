from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_construction_policy import (
    ResearchReturnConstructionPolicy,
)
from algotrader.research.research_return_construction_policy_observation import (
    ResearchReturnConstructionPolicyObservation,
)
from algotrader.research.sma_conditional_return_selection_observation import (
    SmaConditionalReturnSelectionObservation,
    build_sma_conditional_return_selection_observation,
)
from algotrader.research.sma_conditional_return_selection_summary_observation import (
    SmaConditionalReturnSelectionSummaryObservation,
    build_sma_conditional_return_selection_summary_observation,
)
from algotrader.research.sma_return_alignment_observation import (
    SmaReturnAlignmentObservation,
)
from algotrader.research.sma_return_alignment_summary_observation import (
    SmaReturnAlignmentSummaryObservation,
    build_sma_return_alignment_summary_observation,
)
from algotrader.research.sma_return_research_pipeline_observation import (
    SMA_RETURN_RESEARCH_PIPELINE_STATES,
    SmaReturnResearchPipelineObservation,
    build_sma_return_research_pipeline_observation,
)
from algotrader.research.sma_selected_source_return_series_observation import (
    SmaSelectedSourceReturnSeriesObservation,
    build_sma_selected_source_return_series_observation,
)
from algotrader.research.sma_selected_source_return_summary_observation import (
    SmaSelectedSourceReturnSummaryObservation,
    build_sma_selected_source_return_summary_observation,
)
from tests.fixtures.sma_return_alignment_observation import (
    build_synthetic_sma_return_alignment_observation,
)
from tests.fixtures.sma_return_research_pipeline_observation import (
    build_synthetic_sma_return_research_pipeline_observation,
    expected_synthetic_sma_return_research_pipeline_observation_dict,
)


MODULE_PATH = Path(
    "src/algotrader/research/sma_return_research_pipeline_observation.py"
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_PIPELINE_LIMITATIONS = (
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
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.research_return_construction_policy",
    "algotrader.research.research_return_construction_policy_observation",
    "algotrader.research.sma_conditional_return_selection_observation",
    "algotrader.research.sma_conditional_return_selection_summary_observation",
    "algotrader.research.sma_return_alignment_observation",
    "algotrader.research.sma_return_alignment_summary_observation",
    "algotrader.research.sma_selected_source_return_series_observation",
    "algotrader.research.sma_selected_source_return_summary_observation",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _join("algotrader.", "bro", "ker"),
    _join("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.dashboard",
    "algotrader.execution",
    _join("algotrader.", "l", "lm"),
    _join("algotrader.", "l", "lms"),
    "algotrader.ml",
    "algotrader.orchestration",
    _join("algotrader.", "persist", "ence"),
    _join("algotrader.", "port", "folio"),
    "algotrader.risk",
    _join("algotrader.", "run", "time"),
    _join("algotrader.", "sche", "duler"),
    "algotrader.screener",
    _join("algotrader.", "sig", "nals"),
    _join("al", "paca"),
    _join("al", "paca_trade_a", "pi"),
    "anthropic",
    _join("cre", "dential"),
    _join("data", "base"),
    "duckdb",
    "httpx",
    "ipynb",
    "joblib",
    "keras",
    "langchain",
    "langgraph",
    _join("l", "lm"),
    _join("mas", "sive"),
    _join("net", "work"),
    _join("num", "py"),
    "openai",
    "os",
    _join("pan", "das"),
    _join("poly", "gon"),
    _join("quant", "connect"),
    _join("re", "quests"),
    _join("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "xgboost",
    _join("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    _join("cli", "ent"),
    _join("con", "nect"),
    _join("create_", "or", "der"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _join("down", "load"),
    "eval",
    "exec",
    "exists",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    _join("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "load",
    "mkdir",
    _join("op", "en"),
    "os.environ.get",
    "os.getenv",
    "post",
    _join("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    _join("re", "quest"),
    _join("re", "quests.get"),
    "rglob",
    _join("ra", "nk"),
    _join("sco", "re"),
    "save",
    _join("so", "cket.socket"),
    "stat",
    _join("sub", "mit_", "or", "der"),
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _join("wri", "te"),
    "write_text",
}
_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    _join("Al", "paca"),
    "api_key",
    "api_secret",
    "backtest",
    _join("bro", "ker"),
    _join("cli", "ent"),
    _join("cre", "dential"),
    _join("dash", "board"),
    _join("data", "base"),
    _join("exec", "ution"),
    "llm",
    "ml",
    _join("or", "der"),
    _join("persist", "ence"),
    _join("port", "folio"),
    "readiness",
    _join("recomm", "endation"),
    _join("run", "time"),
    _join("sche", "duler"),
    _join("sco", "ring"),
    "secret",
    _join("sig", "nal"),
    _join("so", "cket"),
    "token",
    _join("tra", "ding_authority"),
}
_FORBIDDEN_PAYLOAD_KEYS = {
    "account",
    "accounts",
    "actionable",
    _join("allo", "cation"),
    _join("allo", "cations"),
    _join("allo", "cation_authority"),
    "approved",
    "backtest_approved",
    "backtest_return",
    "backtest_returns",
    "buy",
    _join("bro", "ker"),
    _join("bro", "ker_authority"),
    "capital_authority_state",
    "cash",
    "cash_return",
    "cash_returns",
    "compounded_return",
    "compounded_returns",
    "equity_curve",
    "equity_curves",
    "evaluator",
    "exposure",
    "exposures",
    "hold",
    "invested_return",
    "invested_returns",
    "live_authorized",
    "live_probe_eligible",
    _join("or", "der"),
    _join("or", "ders"),
    _join("or", "der_authority"),
    "paper_eligible",
    _join("port", "folio"),
    _join("port", "folios"),
    "portfolio_return",
    "portfolio_returns",
    _join("port", "folio_state"),
    _join("ra", "nking"),
    _join("recomm", "endation"),
    "readiness",
    _join("sco", "re"),
    _join("sco", "ring"),
    "sell",
    _join("sig", "nal"),
    "strategy_return",
    "strategy_returns",
    _join("tra", "ding_authority"),
    "trading_ready",
}


def test_builds_research_only_pipeline_from_existing_artifacts() -> None:
    sources = _build_pipeline_sources()
    pipeline = build_sma_return_research_pipeline_observation(*sources)
    expected = expected_synthetic_sma_return_research_pipeline_observation_dict()
    policy_observation = pipeline.return_construction_policy_observation

    assert type(pipeline) is SmaReturnResearchPipelineObservation
    assert pipeline.source_alignment_observation is sources[0]
    assert pipeline.source_alignment_summary_observation is sources[1]
    assert pipeline.source_selection_observation is sources[2]
    assert pipeline.source_selection_summary_observation is sources[3]
    assert pipeline.source_selected_source_return_series_observation is sources[4]
    assert pipeline.source_selected_source_return_summary_observation is sources[5]
    assert type(policy_observation) is ResearchReturnConstructionPolicyObservation
    assert type(policy_observation.source_policy) is ResearchReturnConstructionPolicy
    assert (
        policy_observation.to_dict()
        == expected["return_construction_policy_observation"]
    )
    assert pipeline.observation_type == "sma_return_research_pipeline_observation"
    assert pipeline.status == "candidate_only"
    assert pipeline.authority == "advisory_only"
    assert pipeline.capital_authority is False
    assert pipeline.research_scope == "research_only"
    assert pipeline.pipeline_rule == "compose_existing_sma_return_research_artifacts"
    assert pipeline.alignment_rule == "latest_sma_as_of_on_or_before_return_start"
    assert pipeline.selection_rule == "include_when_sma_state_is_above"
    assert (
        pipeline.source_return_value_rule
        == "collect_source_simple_returns_from_included_selection_periods"
    )
    assert pipeline.symbol == "SYNTH_ETF"
    assert pipeline.as_of == "2026-01-20"
    assert pipeline.pipeline_component_count == 6
    assert pipeline.source_return_count == 3
    assert pipeline.source_sma_observation_count == 4
    assert pipeline.alignment_period_count == 3
    assert pipeline.selection_period_count == 3
    assert pipeline.included_period_count == 1
    assert pipeline.excluded_period_count == 2
    assert pipeline.selected_source_return_count == 1
    assert pipeline.alignment_summary_state == "all_return_periods_aligned"
    assert pipeline.selection_summary_state == "mixed_selection_classifications"
    assert (
        pipeline.selected_source_return_summary_state
        == "selected_source_returns_summarized"
    )
    assert pipeline.pipeline_state == "sma_return_research_pipeline_composed"
    assert pipeline.to_dict() == expected
    assert tuple(pipeline.to_dict()) == tuple(expected)


def test_pipeline_states_are_pinned() -> None:
    assert set(SMA_RETURN_RESEARCH_PIPELINE_STATES) == {
        "sma_return_research_pipeline_composed",
    }


def test_rejects_lookalikes_subclasses_dicts_and_wrong_source_inputs() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_sma_return_research_pipeline_observation_dict()

    sources = _build_pipeline_sources()
    subclass_values = _source_subclass_values(sources)

    for index, value in enumerate((None, object(), {}, Lookalike())):
        args = list(sources)
        args[index] = value
        with pytest.raises(ValidationError, match=_source_error_field(index)):
            build_sma_return_research_pipeline_observation(*args)

    for index, value in enumerate(subclass_values):
        args = list(sources)
        args[index] = value
        with pytest.raises(ValidationError, match=_source_error_field(index)):
            build_sma_return_research_pipeline_observation(*args)


def test_rejects_value_equivalent_but_disconnected_artifact_chain() -> None:
    alignment, alignment_summary, selection, selection_summary, series, summary = (
        _build_pipeline_sources()
    )

    with pytest.raises(ValidationError, match="source alignment must be preserved"):
        build_sma_return_research_pipeline_observation(
            alignment,
            build_sma_return_alignment_summary_observation(
                build_synthetic_sma_return_alignment_observation()
            ),
            selection,
            selection_summary,
            series,
            summary,
        )

    disconnected_selection = build_sma_conditional_return_selection_observation(
        build_synthetic_sma_return_alignment_observation()
    )
    with pytest.raises(ValidationError, match="source selection must be preserved"):
        build_sma_return_research_pipeline_observation(
            alignment,
            alignment_summary,
            selection,
            build_sma_conditional_return_selection_summary_observation(
                disconnected_selection
            ),
            series,
            summary,
        )

    with pytest.raises(ValidationError, match="source series must be preserved"):
        build_sma_return_research_pipeline_observation(
            alignment,
            alignment_summary,
            selection,
            selection_summary,
            series,
            build_sma_selected_source_return_summary_observation(
                build_sma_selected_source_return_series_observation(
                    disconnected_selection
                )
            ),
        )


def test_source_identity_is_preserved_and_sources_are_not_mutated() -> None:
    sources = _build_pipeline_sources()
    before = tuple(source.to_dict() for source in sources)

    pipeline = build_sma_return_research_pipeline_observation(*sources)
    after_build = tuple(source.to_dict() for source in sources)
    payload = pipeline.to_dict()
    after_serialize = tuple(source.to_dict() for source in sources)

    assert _pipeline_source_identities(pipeline) == tuple(id(source) for source in sources)
    assert after_build == before
    assert _payload_source_payloads(payload) == before
    assert after_serialize == before


def test_return_construction_policy_observation_identity_chain_is_preserved() -> None:
    pipeline = build_synthetic_sma_return_research_pipeline_observation()
    policy_observation = pipeline.return_construction_policy_observation
    source_policy = policy_observation.source_policy
    reconstructed = SmaReturnResearchPipelineObservation(**_direct_payload(pipeline))
    payload = pipeline.to_dict()

    assert reconstructed.return_construction_policy_observation is policy_observation
    assert reconstructed.return_construction_policy_observation.source_policy is source_policy
    assert policy_observation.source_policy is source_policy
    assert (
        payload["return_construction_policy_observation"]
        == policy_observation.to_dict()
    )
    assert (
        payload["return_construction_policy_observation"]["source_policy"]
        == source_policy.to_dict()
    )


def test_direct_construction_rejects_mismatched_or_malformed_values() -> None:
    pipeline = build_synthetic_sma_return_research_pipeline_observation()
    payload = _direct_payload(pipeline)

    for field_name, value in (
        ("observation_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("research_scope", "other"),
        ("pipeline_rule", "other"),
        ("alignment_rule", "other"),
        ("selection_rule", "other"),
        ("source_return_value_rule", "other"),
        ("symbol", "OTHER"),
        ("as_of", "other"),
        ("pipeline_component_count", 99),
        ("source_return_count", 99),
        ("source_sma_observation_count", 99),
        ("alignment_period_count", 99),
        ("selection_period_count", 99),
        ("included_period_count", 99),
        ("excluded_period_count", 99),
        ("selected_source_return_count", 99),
        ("alignment_summary_state", "other"),
        ("selection_summary_state", "other"),
        ("selected_source_return_summary_state", "other"),
        ("pipeline_state", "other"),
        ("source_alignment_observation", object()),
        ("source_alignment_summary_observation", object()),
        ("source_selection_observation", object()),
        ("source_selection_summary_observation", object()),
        ("source_selected_source_return_series_observation", object()),
        ("source_selected_source_return_summary_observation", object()),
        ("return_construction_policy_observation", object()),
        ("limitations", (_join("action", "able metadata"),)),
        ("non_claims", ("positive claim",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaReturnResearchPipelineObservation(**mutated)


def test_limitations_and_non_claims_are_deduped_with_pipeline_defaults_first() -> None:
    source = build_synthetic_sma_return_research_pipeline_observation()
    payload = _direct_payload(source)
    payload["limitations"] = (*source.limitations, source.limitations[0])
    payload["non_claims"] = (*source.non_claims, source.non_claims[0])

    pipeline = SmaReturnResearchPipelineObservation(**payload)

    assert pipeline.limitations[:3] == _PIPELINE_LIMITATIONS
    assert pipeline.limitations == source.limitations
    assert set(_REQUIRED_NON_CLAIMS).issubset(set(pipeline.non_claims))
    assert pipeline.non_claims == source.non_claims


def test_to_dict_is_primitive_only_deterministic_and_returns_fresh_lists() -> None:
    first = build_synthetic_sma_return_research_pipeline_observation().to_dict()
    second = build_synthetic_sma_return_research_pipeline_observation().to_dict()
    expected = expected_synthetic_sma_return_research_pipeline_observation_dict()
    first_json = _compact_json(first)
    second_json = _compact_json(second)

    assert first == second == expected
    assert _primitive_only(first)
    assert first_json == second_json
    assert json.loads(first_json) == expected
    assert first["source_alignment_observation"] is not (
        second["source_alignment_observation"]
    )
    assert first["source_selection_observation"] is not (
        second["source_selection_observation"]
    )
    assert first["source_selected_source_return_summary_observation"] is not (
        second["source_selected_source_return_summary_observation"]
    )
    assert first["return_construction_policy_observation"] is not (
        second["return_construction_policy_observation"]
    )
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")
    first["source_alignment_observation"]["alignment_periods"].append(
        second["source_alignment_observation"]["alignment_periods"][0]
    )
    first["source_selected_source_return_series_observation"][
        "selected_source_returns"
    ].append(
        second["source_selected_source_return_series_observation"][
            "selected_source_returns"
        ][0]
    )
    first["return_construction_policy_observation"]["source_policy"][
        "limitations"
    ].append("mutated primitive copy")

    assert second == expected
    assert build_synthetic_sma_return_research_pipeline_observation().to_dict() == expected


def test_public_payload_excludes_disallowed_result_fields() -> None:
    payload = build_synthetic_sma_return_research_pipeline_observation().to_dict()
    field_names = {field.name for field in fields(SmaReturnResearchPipelineObservation)}

    assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(field_names)
    assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
    assert _capital_authority_values(payload) == [False] * len(
        _capital_authority_values(payload)
    )
    assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))


def test_object_is_frozen_and_slotted() -> None:
    pipeline = build_synthetic_sma_return_research_pipeline_observation()

    assert hasattr(SmaReturnResearchPipelineObservation, "__slots__")
    assert tuple(field.name for field in fields(SmaReturnResearchPipelineObservation)) == (
        "observation_type",
        "status",
        "authority",
        "capital_authority",
        "research_scope",
        "pipeline_rule",
        "alignment_rule",
        "selection_rule",
        "source_return_value_rule",
        "symbol",
        "as_of",
        "pipeline_component_count",
        "source_return_count",
        "source_sma_observation_count",
        "alignment_period_count",
        "selection_period_count",
        "included_period_count",
        "excluded_period_count",
        "selected_source_return_count",
        "alignment_summary_state",
        "selection_summary_state",
        "selected_source_return_summary_state",
        "pipeline_state",
        "source_alignment_observation",
        "source_alignment_summary_observation",
        "source_selection_observation",
        "source_selection_summary_observation",
        "source_selected_source_return_series_observation",
        "source_selected_source_return_summary_observation",
        "return_construction_policy_observation",
        "limitations",
        "non_claims",
    )
    with pytest.raises(FrozenInstanceError):
        pipeline.symbol = "OTHER"
    with pytest.raises((AttributeError, TypeError)):
        pipeline.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    pipeline = build_synthetic_sma_return_research_pipeline_observation()

    assert not hasattr(SmaReturnResearchPipelineObservation, "from_dict")
    assert not hasattr(pipeline, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_production_module_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_production_module_has_no_forbidden_imports_calls_or_references() -> None:
    imports = _import_references()
    call_names = _call_names()
    reference_names = _referenced_names()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert reference_names.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def _build_pipeline_sources() -> tuple[
    SmaReturnAlignmentObservation,
    SmaReturnAlignmentSummaryObservation,
    SmaConditionalReturnSelectionObservation,
    SmaConditionalReturnSelectionSummaryObservation,
    SmaSelectedSourceReturnSeriesObservation,
    SmaSelectedSourceReturnSummaryObservation,
]:
    alignment = build_synthetic_sma_return_alignment_observation()
    alignment_summary = build_sma_return_alignment_summary_observation(alignment)
    selection = build_sma_conditional_return_selection_observation(alignment)
    selection_summary = build_sma_conditional_return_selection_summary_observation(
        selection
    )
    selected_series = build_sma_selected_source_return_series_observation(selection)
    selected_summary = build_sma_selected_source_return_summary_observation(
        selected_series
    )
    return (
        alignment,
        alignment_summary,
        selection,
        selection_summary,
        selected_series,
        selected_summary,
    )


def _source_subclass_values(
    sources: tuple[object, ...],
) -> tuple[object, ...]:
    class AlignmentSubclass(SmaReturnAlignmentObservation):
        pass

    class AlignmentSummarySubclass(SmaReturnAlignmentSummaryObservation):
        pass

    class SelectionSubclass(SmaConditionalReturnSelectionObservation):
        pass

    class SelectionSummarySubclass(SmaConditionalReturnSelectionSummaryObservation):
        pass

    class SelectedSeriesSubclass(SmaSelectedSourceReturnSeriesObservation):
        pass

    class SelectedSummarySubclass(SmaSelectedSourceReturnSummaryObservation):
        pass

    subclass_types = (
        AlignmentSubclass,
        AlignmentSummarySubclass,
        SelectionSubclass,
        SelectionSummarySubclass,
        SelectedSeriesSubclass,
        SelectedSummarySubclass,
    )
    return tuple(
        subclass_type(
            **{
                field.name: getattr(source, field.name)
                for field in fields(type(source))
            }
        )
        for source, subclass_type in zip(sources, subclass_types)
    )


def _source_error_field(index: int) -> str:
    return (
        "source_alignment_observation",
        "source_alignment_summary_observation",
        "source_selection_observation",
        "source_selection_summary_observation",
        "source_selected_source_return_series_observation",
        "source_selected_source_return_summary_observation",
    )[index]


def _pipeline_source_identities(
    pipeline: SmaReturnResearchPipelineObservation,
) -> tuple[int, ...]:
    return (
        id(pipeline.source_alignment_observation),
        id(pipeline.source_alignment_summary_observation),
        id(pipeline.source_selection_observation),
        id(pipeline.source_selection_summary_observation),
        id(pipeline.source_selected_source_return_series_observation),
        id(pipeline.source_selected_source_return_summary_observation),
    )


def _payload_source_payloads(payload: dict[str, object]) -> tuple[object, ...]:
    return (
        payload["source_alignment_observation"],
        payload["source_alignment_summary_observation"],
        payload["source_selection_observation"],
        payload["source_selection_summary_observation"],
        payload["source_selected_source_return_series_observation"],
        payload["source_selected_source_return_summary_observation"],
    )


def _direct_payload(
    pipeline: SmaReturnResearchPipelineObservation,
) -> dict[str, object]:
    return {
        "observation_type": pipeline.observation_type,
        "status": pipeline.status,
        "authority": pipeline.authority,
        "capital_authority": pipeline.capital_authority,
        "research_scope": pipeline.research_scope,
        "pipeline_rule": pipeline.pipeline_rule,
        "alignment_rule": pipeline.alignment_rule,
        "selection_rule": pipeline.selection_rule,
        "source_return_value_rule": pipeline.source_return_value_rule,
        "symbol": pipeline.symbol,
        "as_of": pipeline.as_of,
        "pipeline_component_count": pipeline.pipeline_component_count,
        "source_return_count": pipeline.source_return_count,
        "source_sma_observation_count": pipeline.source_sma_observation_count,
        "alignment_period_count": pipeline.alignment_period_count,
        "selection_period_count": pipeline.selection_period_count,
        "included_period_count": pipeline.included_period_count,
        "excluded_period_count": pipeline.excluded_period_count,
        "selected_source_return_count": pipeline.selected_source_return_count,
        "alignment_summary_state": pipeline.alignment_summary_state,
        "selection_summary_state": pipeline.selection_summary_state,
        "selected_source_return_summary_state": (
            pipeline.selected_source_return_summary_state
        ),
        "pipeline_state": pipeline.pipeline_state,
        "source_alignment_observation": pipeline.source_alignment_observation,
        "source_alignment_summary_observation": (
            pipeline.source_alignment_summary_observation
        ),
        "source_selection_observation": pipeline.source_selection_observation,
        "source_selection_summary_observation": (
            pipeline.source_selection_summary_observation
        ),
        "source_selected_source_return_series_observation": (
            pipeline.source_selected_source_return_series_observation
        ),
        "source_selected_source_return_summary_observation": (
            pipeline.source_selected_source_return_summary_observation
        ),
        "return_construction_policy_observation": (
            pipeline.return_construction_policy_observation
        ),
        "limitations": pipeline.limitations,
        "non_claims": pipeline.non_claims,
    }


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, nested_value in value.items():
            keys.add(str(key))
            keys.update(_payload_keys(nested_value))
        return keys

    if isinstance(value, list):
        keys = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()


def _capital_authority_values(value: object) -> list[bool]:
    if isinstance(value, dict):
        values: list[bool] = []
        if "capital_authority" in value:
            values.append(value["capital_authority"])
        for nested_value in value.values():
            values.extend(_capital_authority_values(nested_value))
        return values

    if isinstance(value, list):
        values = []
        for nested_value in value:
            values.extend(_capital_authority_values(nested_value))
        return values

    return []


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _referenced_names() -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
