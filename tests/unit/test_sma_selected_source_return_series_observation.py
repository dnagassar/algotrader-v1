from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.sma_conditional_return_selection_observation import (
    SmaConditionalReturnSelectionObservation,
    SmaConditionalReturnSelectionPeriod,
    build_sma_conditional_return_selection_observation,
)
from algotrader.research.sma_research_observation import (
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_return_alignment_observation import (
    build_sma_return_alignment_observation,
)
from algotrader.research.sma_selected_source_return_series_observation import (
    SmaSelectedSourceReturnPoint,
    SmaSelectedSourceReturnSeriesObservation,
    build_sma_selected_source_return_series_observation,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_insufficient_research_return_series_observation,
)
from tests.fixtures.sma_conditional_return_selection_observation import (
    build_synthetic_sma_conditional_return_selection_observation,
)
from tests.fixtures.sma_return_alignment_observation import (
    build_synthetic_sma_return_alignment_return_observation,
)
from tests.fixtures.sma_selected_source_return_series_observation import (
    build_synthetic_sma_selected_source_return_series_observation,
    expected_synthetic_sma_selected_source_return_series_observation_dict,
)


MODULE_PATH = Path(
    "src/algotrader/research/sma_selected_source_return_series_observation.py"
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SYMBOL = "SYNTH_ETF"
_SERIES_LIMITATIONS = (
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
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "decimal",
    "algotrader.errors",
    "algotrader.research.sma_conditional_return_selection_observation",
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
    "benchmark",
    "benchmark_comparison",
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
    "live_authorized",
    "live_probe_eligible",
    _join("or", "der"),
    _join("or", "ders"),
    _join("or", "der_authority"),
    "paper_eligible",
    _join("port", "folio"),
    _join("port", "folios"),
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


def test_builds_research_only_selected_source_return_series_from_selection() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    series = build_sma_selected_source_return_series_observation(selection)
    expected = expected_synthetic_sma_selected_source_return_series_observation_dict()

    assert type(series) is SmaSelectedSourceReturnSeriesObservation
    assert series.source_selection_observation is selection
    assert series.observation_type == "sma_selected_source_return_series_observation"
    assert series.status == "candidate_only"
    assert series.authority == "advisory_only"
    assert series.capital_authority is False
    assert series.research_scope == "research_only"
    assert series.selection_rule == "include_when_sma_state_is_above"
    assert (
        series.source_return_value_rule
        == "collect_source_simple_returns_from_included_selection_periods"
    )
    assert series.symbol == "SYNTH_ETF"
    assert series.as_of == "2026-01-20"
    assert series.source_return_count == 3
    assert series.source_sma_observation_count == 4
    assert series.alignment_period_count == 3
    assert series.selection_period_count == 3
    assert series.included_period_count == 1
    assert series.selected_source_return_count == 1
    assert tuple(
        selected_return.source_simple_return
        for selected_return in series.selected_source_returns
    ) == (Decimal("-0.1"),)
    assert series.to_dict() == expected
    assert tuple(series.to_dict()) == tuple(expected)


def test_extracts_only_included_source_return_values_without_return_math() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    series = build_sma_selected_source_return_series_observation(selection)

    assert tuple(
        period.selection_state for period in selection.selection_periods
    ) == (
        "excluded",
        "included",
        "excluded",
    )
    assert tuple(
        selected_return.return_start_date
        for selected_return in series.selected_source_returns
    ) == ("2026-01-16",)
    assert tuple(
        selected_return.return_end_date
        for selected_return in series.selected_source_returns
    ) == ("2026-01-19",)
    assert tuple(
        selected_return.source_simple_return
        for selected_return in series.selected_source_returns
    ) == (
        selection.selection_periods[1].source_alignment_period.simple_return,
    )
    assert tuple(
        selected_return.source_selection_period
        for selected_return in series.selected_source_returns
    ) == (selection.selection_periods[1],)
    assert tuple(
        period.source_alignment_period.simple_return
        for period in selection.selection_periods
        if period.selection_state == "excluded"
    ) == (Decimal("0.05"), Decimal("0"))
    assert all(
        "strategy_return" not in selected_return.to_dict()
        for selected_return in series.selected_source_returns
    )


def test_empty_and_all_included_selection_shapes_are_deterministic() -> None:
    all_included = build_sma_selected_source_return_series_observation(
        _selection_from_sma_observations((_above_sma_observation("2026-01-14"),))
    )
    all_excluded = build_sma_selected_source_return_series_observation(
        _selection_from_sma_observations(())
    )
    insufficient = build_sma_selected_source_return_series_observation(
        _selection_from_sma_observations(
            (_insufficient_sma_observation("2026-01-14"),)
        )
    )
    empty = build_sma_selected_source_return_series_observation(
        build_sma_conditional_return_selection_observation(
            build_sma_return_alignment_observation(
                (_above_sma_observation("2026-01-16"),),
                build_synthetic_insufficient_research_return_series_observation(),
            )
        )
    )

    assert all_included.included_period_count == 3
    assert all_included.selected_source_return_count == 3
    assert tuple(
        selected_return.source_simple_return
        for selected_return in all_included.selected_source_returns
    ) == (Decimal("0.05"), Decimal("-0.1"), Decimal("0"))
    assert all_excluded.included_period_count == 0
    assert all_excluded.selected_source_return_count == 0
    assert all_excluded.selected_source_returns == ()
    assert _EMPTY_LIMITATION in all_excluded.limitations
    assert insufficient.selected_source_return_count == 0
    assert insufficient.selected_source_returns == ()
    assert _EMPTY_LIMITATION in insufficient.limitations
    assert empty.selection_period_count == 0
    assert empty.included_period_count == 0
    assert empty.selected_source_return_count == 0
    assert empty.selected_source_returns == ()
    assert _EMPTY_LIMITATION in empty.limitations


def test_rejects_lookalikes_subclasses_dicts_and_non_selection_inputs() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_sma_selected_source_return_series_observation_dict()

    class SelectionSubclass(SmaConditionalReturnSelectionObservation):
        pass

    selection = build_synthetic_sma_conditional_return_selection_observation()
    subclass = SelectionSubclass(**_direct_selection_payload(selection))

    for value in (None, object(), {}, Lookalike(), subclass):
        with pytest.raises(ValidationError, match="source_selection_observation"):
            build_sma_selected_source_return_series_observation(value)


def test_source_identity_is_preserved_and_source_is_not_mutated() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    before = selection.to_dict()

    series = build_sma_selected_source_return_series_observation(selection)
    after_build = selection.to_dict()
    payload = series.to_dict()
    after_serialize = selection.to_dict()

    assert series.source_selection_observation is selection
    assert tuple(
        selected_return.source_selection_period
        for selected_return in series.selected_source_returns
    ) == (selection.selection_periods[1],)
    assert after_build == before
    assert payload["source_selection_observation"] == before
    assert after_serialize == before


def test_direct_construction_rejects_mismatched_or_malformed_values() -> None:
    series = build_synthetic_sma_selected_source_return_series_observation()
    payload = _direct_payload(series)

    for field_name, value in (
        ("observation_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("research_scope", "other"),
        ("selection_rule", "other"),
        ("source_return_value_rule", "other"),
        ("symbol", "OTHER"),
        ("as_of", "other"),
        ("source_return_count", 99),
        ("source_sma_observation_count", 99),
        ("alignment_period_count", 99),
        ("selection_period_count", 99),
        ("included_period_count", 99),
        ("selected_source_return_count", 99),
        ("selected_source_returns", (object(),)),
        ("source_selection_observation", object()),
        ("limitations", (_join("action", "able metadata"),)),
        ("non_claims", ("positive claim",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaSelectedSourceReturnSeriesObservation(**mutated)

    stale_selection = build_synthetic_sma_conditional_return_selection_observation()
    stale_point = _point_from_source(stale_selection.selection_periods[1])
    mutated = dict(payload)
    mutated["selected_source_returns"] = (stale_point,)
    with pytest.raises(ValidationError, match="source_selection_period"):
        SmaSelectedSourceReturnSeriesObservation(**mutated)


def test_direct_point_rejects_mismatched_source_fields_or_excluded_periods() -> None:
    series = build_synthetic_sma_selected_source_return_series_observation()
    point = series.selected_source_returns[0]

    for field_name, value in (
        ("return_start_date", "2026-01-01"),
        ("return_end_date", "2026-01-01"),
        ("source_simple_return", Decimal("0.123")),
        ("source_simple_return", "0.123"),
        ("source_selection_period", object()),
    ):
        payload = _direct_point_payload(point)
        payload[field_name] = value
        with pytest.raises(ValidationError):
            SmaSelectedSourceReturnPoint(**payload)

    payload = _direct_point_payload(point)
    payload["source_selection_period"] = (
        series.source_selection_observation.selection_periods[0]
    )
    with pytest.raises(ValidationError, match="included"):
        SmaSelectedSourceReturnPoint(**payload)


def test_limitations_and_non_claims_are_deduped_with_series_defaults_first() -> None:
    source = build_synthetic_sma_selected_source_return_series_observation()
    payload = _direct_payload(source)
    payload["limitations"] = (*source.limitations, source.limitations[0])
    payload["non_claims"] = (*source.non_claims, source.non_claims[0])

    series = SmaSelectedSourceReturnSeriesObservation(**payload)

    assert series.limitations[:3] == _SERIES_LIMITATIONS
    assert series.limitations == source.limitations
    assert set(_REQUIRED_NON_CLAIMS).issubset(set(series.non_claims))
    assert series.non_claims == source.non_claims


def test_to_dict_is_primitive_only_deterministic_and_returns_fresh_lists() -> None:
    first = build_synthetic_sma_selected_source_return_series_observation().to_dict()
    second = build_synthetic_sma_selected_source_return_series_observation().to_dict()
    expected = expected_synthetic_sma_selected_source_return_series_observation_dict()
    first_json = _compact_json(first)
    second_json = _compact_json(second)

    assert first == second == expected
    assert _primitive_only(first)
    assert first_json == second_json
    assert json.loads(first_json) == expected
    assert first["selected_source_returns"] is not second["selected_source_returns"]
    assert first["source_selection_observation"] is not (
        second["source_selection_observation"]
    )
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["selected_source_returns"].append(second["selected_source_returns"][0])
    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")
    first["source_selection_observation"]["selection_periods"].append(
        second["source_selection_observation"]["selection_periods"][0]
    )

    assert second == expected
    assert (
        build_synthetic_sma_selected_source_return_series_observation().to_dict()
        == expected
    )


def test_public_payload_excludes_trading_and_performance_fields() -> None:
    payloads = (
        build_synthetic_sma_selected_source_return_series_observation().to_dict(),
        build_sma_selected_source_return_series_observation(
            _selection_from_sma_observations(())
        ).to_dict(),
    )

    for payload in payloads:
        assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
        assert _capital_authority_values(payload) == [False] * len(
            _capital_authority_values(payload)
        )
        assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))


def test_object_is_frozen_and_slotted() -> None:
    series = build_synthetic_sma_selected_source_return_series_observation()
    point = series.selected_source_returns[0]

    assert hasattr(SmaSelectedSourceReturnSeriesObservation, "__slots__")
    assert hasattr(SmaSelectedSourceReturnPoint, "__slots__")
    assert tuple(
        field.name for field in fields(SmaSelectedSourceReturnSeriesObservation)
    ) == (
        "observation_type",
        "status",
        "authority",
        "capital_authority",
        "research_scope",
        "selection_rule",
        "source_return_value_rule",
        "symbol",
        "as_of",
        "source_return_count",
        "source_sma_observation_count",
        "alignment_period_count",
        "selection_period_count",
        "included_period_count",
        "selected_source_return_count",
        "selected_source_returns",
        "source_selection_observation",
        "limitations",
        "non_claims",
    )
    assert tuple(field.name for field in fields(SmaSelectedSourceReturnPoint)) == (
        "return_start_date",
        "return_end_date",
        "source_simple_return",
        "source_selection_period",
    )
    with pytest.raises(FrozenInstanceError):
        series.symbol = "OTHER"
    with pytest.raises(FrozenInstanceError):
        point.source_simple_return = Decimal("1")
    with pytest.raises((AttributeError, TypeError)):
        series.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    series = build_synthetic_sma_selected_source_return_series_observation()
    point = series.selected_source_returns[0]

    assert not hasattr(SmaSelectedSourceReturnSeriesObservation, "from_dict")
    assert not hasattr(SmaSelectedSourceReturnPoint, "from_dict")
    assert not hasattr(series, "from_dict")
    assert not hasattr(point, "from_dict")
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


def _selection_from_sma_observations(
    sma_observations,
) -> SmaConditionalReturnSelectionObservation:
    return build_sma_conditional_return_selection_observation(
        build_sma_return_alignment_observation(
            sma_observations,
            build_synthetic_sma_return_alignment_return_observation(),
        )
    )


def _above_sma_observation(as_of: str):
    return build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=as_of,
        window=2,
        price_points=(
            _point("2026-01-13", "10.00"),
            _point(as_of, "30.00"),
        ),
    )


def _insufficient_sma_observation(as_of: str):
    return build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=as_of,
        window=3,
        price_points=(
            _point("2026-01-13", "10.00"),
            _point(as_of, "11.00"),
        ),
    )


def _point(value_date: str, close: str) -> SmaResearchPricePoint:
    return SmaResearchPricePoint(value_date, Decimal(close))


def _point_from_source(
    source_selection_period: SmaConditionalReturnSelectionPeriod,
) -> SmaSelectedSourceReturnPoint:
    return SmaSelectedSourceReturnPoint(
        return_start_date=source_selection_period.return_start_date,
        return_end_date=source_selection_period.return_end_date,
        source_simple_return=(
            source_selection_period.source_alignment_period.simple_return
        ),
        source_selection_period=source_selection_period,
    )


def _direct_payload(
    series: SmaSelectedSourceReturnSeriesObservation,
) -> dict[str, object]:
    return {
        "observation_type": series.observation_type,
        "status": series.status,
        "authority": series.authority,
        "capital_authority": series.capital_authority,
        "research_scope": series.research_scope,
        "selection_rule": series.selection_rule,
        "source_return_value_rule": series.source_return_value_rule,
        "symbol": series.symbol,
        "as_of": series.as_of,
        "source_return_count": series.source_return_count,
        "source_sma_observation_count": series.source_sma_observation_count,
        "alignment_period_count": series.alignment_period_count,
        "selection_period_count": series.selection_period_count,
        "included_period_count": series.included_period_count,
        "selected_source_return_count": series.selected_source_return_count,
        "selected_source_returns": series.selected_source_returns,
        "source_selection_observation": series.source_selection_observation,
        "limitations": series.limitations,
        "non_claims": series.non_claims,
    }


def _direct_point_payload(
    point: SmaSelectedSourceReturnPoint,
) -> dict[str, object]:
    return {
        "return_start_date": point.return_start_date,
        "return_end_date": point.return_end_date,
        "source_simple_return": point.source_simple_return,
        "source_selection_period": point.source_selection_period,
    }


def _direct_selection_payload(
    selection: SmaConditionalReturnSelectionObservation,
) -> dict[str, object]:
    return {
        "observation_type": selection.observation_type,
        "status": selection.status,
        "authority": selection.authority,
        "capital_authority": selection.capital_authority,
        "research_scope": selection.research_scope,
        "selection_rule": selection.selection_rule,
        "symbol": selection.symbol,
        "as_of": selection.as_of,
        "source_return_count": selection.source_return_count,
        "source_sma_observation_count": selection.source_sma_observation_count,
        "alignment_period_count": selection.alignment_period_count,
        "included_period_count": selection.included_period_count,
        "excluded_period_count": selection.excluded_period_count,
        "no_prior_sma_state_excluded_count": (
            selection.no_prior_sma_state_excluded_count
        ),
        "insufficient_history_excluded_count": (
            selection.insufficient_history_excluded_count
        ),
        "below_sma_excluded_count": selection.below_sma_excluded_count,
        "equal_sma_excluded_count": selection.equal_sma_excluded_count,
        "selection_periods": selection.selection_periods,
        "source_alignment_observation": selection.source_alignment_observation,
        "limitations": selection.limitations,
        "non_claims": selection.non_claims,
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
