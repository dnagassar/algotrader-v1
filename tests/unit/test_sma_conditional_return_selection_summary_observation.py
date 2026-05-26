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
    build_sma_conditional_return_selection_observation,
)
from algotrader.research.sma_conditional_return_selection_summary_observation import (
    SMA_CONDITIONAL_RETURN_SELECTION_SUMMARY_STATES,
    SmaConditionalReturnSelectionSummaryObservation,
    build_sma_conditional_return_selection_summary_observation,
)
from algotrader.research.sma_research_observation import (
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_return_alignment_observation import (
    build_sma_return_alignment_observation,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_insufficient_research_return_series_observation,
)
from tests.fixtures.sma_conditional_return_selection_observation import (
    build_synthetic_sma_conditional_return_selection_observation,
)
from tests.fixtures.sma_conditional_return_selection_summary_observation import (
    build_synthetic_sma_conditional_return_selection_summary_observation,
    expected_synthetic_sma_conditional_return_selection_summary_observation_dict,
)
from tests.fixtures.sma_return_alignment_observation import (
    build_synthetic_sma_return_alignment_return_observation,
)


MODULE_PATH = Path(
    "src/algotrader/research/sma_conditional_return_selection_summary_observation.py"
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SYMBOL = "SYNTH_ETF"
_SUMMARY_LIMITATIONS = (
    "summarizes existing SMA conditional return-selection metadata only",
    "counts include and exclude classifications without return math",
    "preserves source selection metadata without deriving performance metrics",
)
_EMPTY_LIMITATION = "no selection periods were available to summarize"
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


def test_builds_research_only_summary_from_selection_observation() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    summary = build_sma_conditional_return_selection_summary_observation(selection)
    expected = (
        expected_synthetic_sma_conditional_return_selection_summary_observation_dict()
    )

    assert type(summary) is SmaConditionalReturnSelectionSummaryObservation
    assert summary.source_selection_observation is selection
    assert (
        summary.observation_type
        == "sma_conditional_return_selection_summary_observation"
    )
    assert summary.status == "candidate_only"
    assert summary.authority == "advisory_only"
    assert summary.capital_authority is False
    assert summary.research_scope == "research_only"
    assert summary.selection_rule == "include_when_sma_state_is_above"
    assert summary.symbol == "SYNTH_ETF"
    assert summary.as_of == "2026-01-20"
    assert summary.source_return_count == 3
    assert summary.source_sma_observation_count == 4
    assert summary.alignment_period_count == 3
    assert summary.selection_period_count == 3
    assert summary.included_period_count == 1
    assert summary.excluded_period_count == 2
    assert summary.no_prior_sma_state_excluded_count == 0
    assert summary.insufficient_history_excluded_count == 0
    assert summary.below_sma_excluded_count == 1
    assert summary.equal_sma_excluded_count == 1
    assert summary.summary_state == "mixed_selection_classifications"
    assert summary.to_dict() == expected
    assert tuple(summary.to_dict()) == tuple(expected)


def test_summary_states_are_pinned_to_classification_counts() -> None:
    assert set(SMA_CONDITIONAL_RETURN_SELECTION_SUMMARY_STATES) == {
        "mixed_selection_classifications",
        "all_periods_included",
        "all_periods_excluded",
        "empty_selection_periods",
    }

    mixed = build_synthetic_sma_conditional_return_selection_summary_observation()
    all_included = build_sma_conditional_return_selection_summary_observation(
        _selection_from_sma_observations((_above_sma_observation("2026-01-14"),))
    )
    all_excluded = build_sma_conditional_return_selection_summary_observation(
        _selection_from_sma_observations(())
    )
    empty = build_sma_conditional_return_selection_summary_observation(
        build_sma_conditional_return_selection_observation(
            build_sma_return_alignment_observation(
                (_above_sma_observation("2026-01-16"),),
                build_synthetic_insufficient_research_return_series_observation(),
            )
        )
    )

    assert mixed.summary_state == "mixed_selection_classifications"
    assert all_included.summary_state == "all_periods_included"
    assert all_included.selection_period_count == 3
    assert all_included.included_period_count == 3
    assert all_included.excluded_period_count == 0
    assert all_excluded.summary_state == "all_periods_excluded"
    assert all_excluded.included_period_count == 0
    assert all_excluded.excluded_period_count == 3
    assert all_excluded.no_prior_sma_state_excluded_count == 3
    assert empty.summary_state == "empty_selection_periods"
    assert empty.selection_period_count == 0
    assert _EMPTY_LIMITATION in empty.limitations


def test_exclusion_reason_counts_are_recomputed_from_selection_periods() -> None:
    insufficient = build_sma_conditional_return_selection_summary_observation(
        _selection_from_sma_observations((_insufficient_sma_observation("2026-01-14"),))
    )

    assert insufficient.summary_state == "all_periods_excluded"
    assert insufficient.selection_period_count == 3
    assert insufficient.included_period_count == 0
    assert insufficient.excluded_period_count == 3
    assert insufficient.no_prior_sma_state_excluded_count == 0
    assert insufficient.insufficient_history_excluded_count == 3
    assert insufficient.below_sma_excluded_count == 0
    assert insufficient.equal_sma_excluded_count == 0


def test_rejects_lookalikes_subclasses_dicts_and_non_selection_inputs() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return (
                expected_synthetic_sma_conditional_return_selection_summary_observation_dict()
            )

    class SelectionSubclass(SmaConditionalReturnSelectionObservation):
        pass

    selection = build_synthetic_sma_conditional_return_selection_observation()
    subclass = SelectionSubclass(**_direct_selection_payload(selection))

    for value in (None, object(), {}, Lookalike(), subclass):
        with pytest.raises(ValidationError, match="source_selection_observation"):
            build_sma_conditional_return_selection_summary_observation(value)


def test_source_identity_is_preserved_and_source_is_not_mutated() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    before = selection.to_dict()

    summary = build_sma_conditional_return_selection_summary_observation(selection)
    after_build = selection.to_dict()
    payload = summary.to_dict()
    after_serialize = selection.to_dict()

    assert summary.source_selection_observation is selection
    assert after_build == before
    assert payload["source_selection_observation"] == before
    assert after_serialize == before


def test_direct_construction_rejects_mismatched_or_malformed_values() -> None:
    summary = build_synthetic_sma_conditional_return_selection_summary_observation()
    payload = _direct_payload(summary)

    for field_name, value in (
        ("observation_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("research_scope", "other"),
        ("selection_rule", "other"),
        ("symbol", "OTHER"),
        ("as_of", "other"),
        ("source_return_count", 99),
        ("source_sma_observation_count", 99),
        ("alignment_period_count", 99),
        ("selection_period_count", 99),
        ("included_period_count", 99),
        ("excluded_period_count", 99),
        ("no_prior_sma_state_excluded_count", 99),
        ("insufficient_history_excluded_count", 99),
        ("below_sma_excluded_count", 99),
        ("equal_sma_excluded_count", 99),
        ("summary_state", "other"),
        ("source_selection_observation", object()),
        ("limitations", (_join("action", "able metadata"),)),
        ("non_claims", ("positive claim",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaConditionalReturnSelectionSummaryObservation(**mutated)


def test_limitations_and_non_claims_are_deduped_with_summary_defaults_first() -> None:
    source = build_synthetic_sma_conditional_return_selection_summary_observation()
    payload = _direct_payload(source)
    payload["limitations"] = (*source.limitations, source.limitations[0])
    payload["non_claims"] = (*source.non_claims, source.non_claims[0])

    summary = SmaConditionalReturnSelectionSummaryObservation(**payload)

    assert summary.limitations[:3] == _SUMMARY_LIMITATIONS
    assert summary.limitations == source.limitations
    assert set(_REQUIRED_NON_CLAIMS).issubset(set(summary.non_claims))
    assert summary.non_claims == source.non_claims


def test_to_dict_is_primitive_only_deterministic_and_returns_fresh_lists() -> None:
    first = (
        build_synthetic_sma_conditional_return_selection_summary_observation().to_dict()
    )
    second = (
        build_synthetic_sma_conditional_return_selection_summary_observation().to_dict()
    )
    expected = (
        expected_synthetic_sma_conditional_return_selection_summary_observation_dict()
    )
    first_json = _compact_json(first)
    second_json = _compact_json(second)

    assert first == second == expected
    assert _primitive_only(first)
    assert first_json == second_json
    assert json.loads(first_json) == expected
    assert first["source_selection_observation"] is not (
        second["source_selection_observation"]
    )
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")
    first["source_selection_observation"]["selection_periods"].append(
        second["source_selection_observation"]["selection_periods"][0]
    )

    assert second == expected
    assert (
        build_synthetic_sma_conditional_return_selection_summary_observation().to_dict()
        == expected
    )


def test_public_payload_excludes_trading_and_performance_fields() -> None:
    payloads = (
        build_synthetic_sma_conditional_return_selection_summary_observation().to_dict(),
        build_sma_conditional_return_selection_summary_observation(
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
    summary = build_synthetic_sma_conditional_return_selection_summary_observation()

    assert hasattr(SmaConditionalReturnSelectionSummaryObservation, "__slots__")
    assert tuple(
        field.name
        for field in fields(SmaConditionalReturnSelectionSummaryObservation)
    ) == (
        "observation_type",
        "status",
        "authority",
        "capital_authority",
        "research_scope",
        "selection_rule",
        "symbol",
        "as_of",
        "source_return_count",
        "source_sma_observation_count",
        "alignment_period_count",
        "selection_period_count",
        "included_period_count",
        "excluded_period_count",
        "no_prior_sma_state_excluded_count",
        "insufficient_history_excluded_count",
        "below_sma_excluded_count",
        "equal_sma_excluded_count",
        "summary_state",
        "source_selection_observation",
        "limitations",
        "non_claims",
    )
    with pytest.raises(FrozenInstanceError):
        summary.symbol = "OTHER"
    with pytest.raises((AttributeError, TypeError)):
        summary.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    summary = build_synthetic_sma_conditional_return_selection_summary_observation()

    assert not hasattr(SmaConditionalReturnSelectionSummaryObservation, "from_dict")
    assert not hasattr(summary, "from_dict")
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


def _direct_payload(
    summary: SmaConditionalReturnSelectionSummaryObservation,
) -> dict[str, object]:
    return {
        "observation_type": summary.observation_type,
        "status": summary.status,
        "authority": summary.authority,
        "capital_authority": summary.capital_authority,
        "research_scope": summary.research_scope,
        "selection_rule": summary.selection_rule,
        "symbol": summary.symbol,
        "as_of": summary.as_of,
        "source_return_count": summary.source_return_count,
        "source_sma_observation_count": summary.source_sma_observation_count,
        "alignment_period_count": summary.alignment_period_count,
        "selection_period_count": summary.selection_period_count,
        "included_period_count": summary.included_period_count,
        "excluded_period_count": summary.excluded_period_count,
        "no_prior_sma_state_excluded_count": (
            summary.no_prior_sma_state_excluded_count
        ),
        "insufficient_history_excluded_count": (
            summary.insufficient_history_excluded_count
        ),
        "below_sma_excluded_count": summary.below_sma_excluded_count,
        "equal_sma_excluded_count": summary.equal_sma_excluded_count,
        "summary_state": summary.summary_state,
        "source_selection_observation": summary.source_selection_observation,
        "limitations": summary.limitations,
        "non_claims": summary.non_claims,
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
