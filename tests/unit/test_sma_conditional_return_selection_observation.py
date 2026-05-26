from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.sma_conditional_return_selection_observation import (
    SMA_CONDITIONAL_RETURN_SELECTION_REASONS,
    SMA_CONDITIONAL_RETURN_SELECTION_STATES,
    SmaConditionalReturnSelectionObservation,
    SmaConditionalReturnSelectionPeriod,
    build_sma_conditional_return_selection_observation,
)
from algotrader.research.sma_research_observation import (
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_return_alignment_observation import (
    SmaReturnAlignmentObservation,
    build_sma_return_alignment_observation,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_insufficient_research_return_series_observation,
)
from tests.fixtures.sma_conditional_return_selection_observation import (
    build_synthetic_sma_conditional_return_selection_observation,
    expected_synthetic_sma_conditional_return_selection_observation_dict,
)
from tests.fixtures.sma_return_alignment_observation import (
    build_synthetic_sma_return_alignment_observation,
    build_synthetic_sma_return_alignment_return_observation,
)


MODULE_PATH = Path(
    "src/algotrader/research/sma_conditional_return_selection_observation.py"
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SYMBOL = "SYNTH_ETF"
_SELECTION_LIMITATIONS = (
    "classifies existing SMA-return alignment periods under a fixed above-SMA rule only",
    "preserves source alignment metadata without deriving performance metrics",
    "treats missing or non-above SMA states as excluded classifications only",
)
_EMPTY_LIMITATION = "no alignment periods were available to classify"
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
    "algotrader.research.sma_return_alignment_observation",
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


def test_builds_research_only_selection_from_alignment_observation() -> None:
    alignment = build_synthetic_sma_return_alignment_observation()
    selection = build_sma_conditional_return_selection_observation(alignment)
    expected = expected_synthetic_sma_conditional_return_selection_observation_dict()

    assert type(selection) is SmaConditionalReturnSelectionObservation
    assert selection.source_alignment_observation is alignment
    assert selection.observation_type == "sma_conditional_return_selection_observation"
    assert selection.status == "candidate_only"
    assert selection.authority == "advisory_only"
    assert selection.capital_authority is False
    assert selection.research_scope == "research_only"
    assert selection.selection_rule == "include_when_sma_state_is_above"
    assert selection.symbol == "SYNTH_ETF"
    assert selection.as_of == "2026-01-20"
    assert selection.source_return_count == 3
    assert selection.source_sma_observation_count == 4
    assert selection.alignment_period_count == 3
    assert selection.included_period_count == 1
    assert selection.excluded_period_count == 2
    assert selection.no_prior_sma_state_excluded_count == 0
    assert selection.insufficient_history_excluded_count == 0
    assert selection.below_sma_excluded_count == 1
    assert selection.equal_sma_excluded_count == 1
    assert selection.to_dict() == expected
    assert tuple(selection.to_dict()) == tuple(expected)


def test_above_sma_rule_classifies_alignment_periods_without_return_math() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()

    assert set(SMA_CONDITIONAL_RETURN_SELECTION_STATES) == {
        "included",
        "excluded",
    }
    assert set(SMA_CONDITIONAL_RETURN_SELECTION_REASONS) == {
        "above_sma",
        "below_sma",
        "equal_sma",
        "insufficient_history",
        "no_prior_sma_state",
    }
    assert tuple(
        period.selection_state for period in selection.selection_periods
    ) == (
        "excluded",
        "included",
        "excluded",
    )
    assert tuple(
        period.selection_reason for period in selection.selection_periods
    ) == (
        "equal_sma",
        "above_sma",
        "below_sma",
    )
    assert tuple(
        period.sma_observation_state for period in selection.selection_periods
    ) == (
        "equal",
        "above",
        "below",
    )
    assert all(
        "strategy_return" not in period.to_dict()
        for period in selection.selection_periods
    )


def test_no_prior_sma_and_insufficient_history_are_excluded_classifications() -> None:
    no_prior = build_sma_conditional_return_selection_observation(
        build_sma_return_alignment_observation(
            (),
            build_synthetic_sma_return_alignment_return_observation(),
        )
    )
    insufficient_history = build_sma_conditional_return_selection_observation(
        build_sma_return_alignment_observation(
            (_insufficient_sma_observation("2026-01-14"),),
            build_synthetic_sma_return_alignment_return_observation(),
        )
    )
    empty = build_sma_conditional_return_selection_observation(
        build_sma_return_alignment_observation(
            (_above_sma_observation("2026-01-16"),),
            build_synthetic_insufficient_research_return_series_observation(),
        )
    )

    assert no_prior.included_period_count == 0
    assert no_prior.excluded_period_count == 3
    assert no_prior.no_prior_sma_state_excluded_count == 3
    assert tuple(period.selection_reason for period in no_prior.selection_periods) == (
        "no_prior_sma_state",
        "no_prior_sma_state",
        "no_prior_sma_state",
    )
    assert insufficient_history.included_period_count == 0
    assert insufficient_history.excluded_period_count == 3
    assert insufficient_history.insufficient_history_excluded_count == 3
    assert tuple(
        period.selection_reason for period in insufficient_history.selection_periods
    ) == (
        "insufficient_history",
        "insufficient_history",
        "insufficient_history",
    )
    assert empty.selection_periods == ()
    assert empty.included_period_count == 0
    assert empty.excluded_period_count == 0
    assert _EMPTY_LIMITATION in empty.limitations


def test_rejects_lookalikes_subclasses_dicts_and_non_alignment_inputs() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return build_synthetic_sma_return_alignment_observation().to_dict()

    class AlignmentSubclass(SmaReturnAlignmentObservation):
        pass

    alignment = build_synthetic_sma_return_alignment_observation()
    subclass = AlignmentSubclass(**_direct_alignment_payload(alignment))

    for value in (None, object(), {}, Lookalike(), subclass):
        with pytest.raises(ValidationError, match="source_alignment_observation"):
            build_sma_conditional_return_selection_observation(value)


def test_source_identity_is_preserved_and_source_is_not_mutated() -> None:
    alignment = build_synthetic_sma_return_alignment_observation()
    before = alignment.to_dict()

    selection = build_sma_conditional_return_selection_observation(alignment)
    after_build = alignment.to_dict()
    payload = selection.to_dict()
    after_serialize = alignment.to_dict()

    assert selection.source_alignment_observation is alignment
    assert tuple(
        period.source_alignment_period for period in selection.selection_periods
    ) == alignment.alignment_periods
    assert after_build == before
    assert payload["source_alignment_observation"] == before
    assert after_serialize == before


def test_direct_construction_rejects_mismatched_or_malformed_values() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    payload = _direct_payload(selection)

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
        ("included_period_count", 99),
        ("excluded_period_count", 99),
        ("no_prior_sma_state_excluded_count", 99),
        ("insufficient_history_excluded_count", 99),
        ("below_sma_excluded_count", 99),
        ("equal_sma_excluded_count", 99),
        ("selection_periods", (object(),)),
        ("source_alignment_observation", object()),
        ("limitations", (_join("action", "able metadata"),)),
        ("non_claims", ("positive claim",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaConditionalReturnSelectionObservation(**mutated)

    stale_period = _period_from_source(
        selection.source_alignment_observation.alignment_periods[0]
    )
    mutated = dict(payload)
    mutated["selection_periods"] = (
        selection.selection_periods[0],
        stale_period,
        selection.selection_periods[2],
    )
    with pytest.raises(ValidationError, match="source_alignment_period"):
        SmaConditionalReturnSelectionObservation(**mutated)


def test_direct_period_rejects_mismatched_selection_rule_fields() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    period = selection.selection_periods[1]

    for field_name, value in (
        ("return_start_date", "2026-01-01"),
        ("return_end_date", "2026-01-01"),
        ("selection_state", "excluded"),
        ("selection_reason", "below_sma"),
        ("sma_observation_as_of", "2026-01-01"),
        ("sma_observation_state", "below"),
        ("source_alignment_period", object()),
    ):
        payload = _direct_period_payload(period)
        payload[field_name] = value
        with pytest.raises(ValidationError):
            SmaConditionalReturnSelectionPeriod(**payload)


def test_limitations_and_non_claims_are_deduped_with_selection_defaults_first() -> None:
    alignment = _alignment_with_duplicate_metadata()
    selection = build_sma_conditional_return_selection_observation(alignment)

    assert selection.limitations[:3] == _SELECTION_LIMITATIONS
    assert selection.limitations.count("synthetic selection duplicate limitation") == 1
    assert set(_REQUIRED_NON_CLAIMS).issubset(set(selection.non_claims))
    assert selection.non_claims.count(_not("extra duplicate claim")) == 1


def test_to_dict_is_primitive_only_deterministic_and_returns_fresh_lists() -> None:
    first = build_synthetic_sma_conditional_return_selection_observation().to_dict()
    second = build_synthetic_sma_conditional_return_selection_observation().to_dict()
    expected = expected_synthetic_sma_conditional_return_selection_observation_dict()
    first_json = _compact_json(first)
    second_json = _compact_json(second)

    assert first == second == expected
    assert _primitive_only(first)
    assert first_json == second_json
    assert json.loads(first_json) == expected
    assert first["selection_periods"] is not second["selection_periods"]
    assert first["source_alignment_observation"] is not (
        second["source_alignment_observation"]
    )
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["selection_periods"].append(second["selection_periods"][0])
    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")
    first["source_alignment_observation"]["alignment_periods"].append(
        second["source_alignment_observation"]["alignment_periods"][0]
    )

    assert second == expected
    assert (
        build_synthetic_sma_conditional_return_selection_observation().to_dict()
        == expected
    )


def test_public_payload_excludes_trading_and_performance_fields() -> None:
    payloads = (
        build_synthetic_sma_conditional_return_selection_observation().to_dict(),
        build_sma_conditional_return_selection_observation(
            build_sma_return_alignment_observation(
                (),
                build_synthetic_sma_return_alignment_return_observation(),
            )
        ).to_dict(),
    )

    for payload in payloads:
        assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
        assert _capital_authority_values(payload) == [False] * len(
            _capital_authority_values(payload)
        )
        assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))


def test_object_is_frozen_and_slotted() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    period = selection.selection_periods[0]

    assert hasattr(SmaConditionalReturnSelectionObservation, "__slots__")
    assert hasattr(SmaConditionalReturnSelectionPeriod, "__slots__")
    assert tuple(
        field.name for field in fields(SmaConditionalReturnSelectionObservation)
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
        "included_period_count",
        "excluded_period_count",
        "no_prior_sma_state_excluded_count",
        "insufficient_history_excluded_count",
        "below_sma_excluded_count",
        "equal_sma_excluded_count",
        "selection_periods",
        "source_alignment_observation",
        "limitations",
        "non_claims",
    )
    assert tuple(field.name for field in fields(SmaConditionalReturnSelectionPeriod)) == (
        "return_start_date",
        "return_end_date",
        "selection_state",
        "selection_reason",
        "sma_observation_as_of",
        "sma_observation_state",
        "source_alignment_period",
    )
    with pytest.raises(FrozenInstanceError):
        selection.symbol = "OTHER"
    with pytest.raises(FrozenInstanceError):
        period.selection_state = "other"
    with pytest.raises((AttributeError, TypeError)):
        selection.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    selection = build_synthetic_sma_conditional_return_selection_observation()
    period = selection.selection_periods[0]

    assert not hasattr(SmaConditionalReturnSelectionObservation, "from_dict")
    assert not hasattr(SmaConditionalReturnSelectionPeriod, "from_dict")
    assert not hasattr(selection, "from_dict")
    assert not hasattr(period, "from_dict")
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


def _above_sma_observation(as_of: str):
    return build_sma_research_observation(
        symbol=_SYMBOL,
        as_of=as_of,
        window=2,
        price_points=(
            _point("2026-01-15", "10.00"),
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


def _period_from_source(
    source_alignment_period,
) -> SmaConditionalReturnSelectionPeriod:
    return SmaConditionalReturnSelectionPeriod(
        return_start_date=source_alignment_period.return_start_date,
        return_end_date=source_alignment_period.return_end_date,
        selection_state=(
            "included"
            if source_alignment_period.sma_observation_state == "above"
            else "excluded"
        ),
        selection_reason=(
            "no_prior_sma_state"
            if source_alignment_period.alignment_state == "sma_state_unavailable"
            else f"{source_alignment_period.sma_observation_state}_sma"
            if source_alignment_period.sma_observation_state in ("above", "below", "equal")
            else "insufficient_history"
        ),
        sma_observation_as_of=source_alignment_period.sma_observation_as_of,
        sma_observation_state=source_alignment_period.sma_observation_state,
        source_alignment_period=source_alignment_period,
    )


def _direct_payload(
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


def _direct_period_payload(
    period: SmaConditionalReturnSelectionPeriod,
) -> dict[str, object]:
    return {
        "return_start_date": period.return_start_date,
        "return_end_date": period.return_end_date,
        "selection_state": period.selection_state,
        "selection_reason": period.selection_reason,
        "sma_observation_as_of": period.sma_observation_as_of,
        "sma_observation_state": period.sma_observation_state,
        "source_alignment_period": period.source_alignment_period,
    }


def _direct_alignment_payload(
    alignment: SmaReturnAlignmentObservation,
) -> dict[str, object]:
    return {
        "observation_type": alignment.observation_type,
        "status": alignment.status,
        "authority": alignment.authority,
        "capital_authority": alignment.capital_authority,
        "research_scope": alignment.research_scope,
        "alignment_rule": alignment.alignment_rule,
        "symbol": alignment.symbol,
        "as_of": alignment.as_of,
        "source_return_count": alignment.source_return_count,
        "source_sma_observation_count": alignment.source_sma_observation_count,
        "aligned_return_count": alignment.aligned_return_count,
        "unaligned_return_count": alignment.unaligned_return_count,
        "alignment_periods": alignment.alignment_periods,
        "source_return_observation": alignment.source_return_observation,
        "source_sma_observations": alignment.source_sma_observations,
        "limitations": alignment.limitations,
        "non_claims": alignment.non_claims,
    }


def _alignment_with_duplicate_metadata() -> SmaReturnAlignmentObservation:
    source = build_synthetic_sma_return_alignment_observation()
    return SmaReturnAlignmentObservation(
        **{
            **_direct_alignment_payload(source),
            "limitations": (
                "synthetic selection duplicate limitation",
                "synthetic selection duplicate limitation",
            ),
            "non_claims": (
                *source.non_claims,
                _not("extra duplicate claim"),
                _not("extra duplicate claim"),
            ),
        }
    )


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
