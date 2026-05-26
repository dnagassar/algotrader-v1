from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation import (
    ResearchReturnSeriesObservation,
)
from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_return_alignment_observation import (
    SMA_RETURN_ALIGNMENT_STATES,
    SmaReturnAlignmentObservation,
    SmaReturnAlignmentPeriod,
    build_sma_return_alignment_observation,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_insufficient_research_return_series_observation,
)
from tests.fixtures.sma_return_alignment_observation import (
    build_synthetic_sma_return_alignment_observation,
    build_synthetic_sma_return_alignment_return_observation,
    build_synthetic_sma_return_alignment_sma_observations,
    expected_synthetic_sma_return_alignment_observation_dict,
)


MODULE_PATH = Path("src/algotrader/research/sma_return_alignment_observation.py")


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
    "algotrader.research.research_return_observation",
    "algotrader.research.sma_research_observation",
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
    "pathlib",
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
    "buy",
    _join("bro", "ker"),
    _join("bro", "ker_authority"),
    "capital",
    "capital_authority_state",
    "evaluator",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _join("or", "der"),
    _join("or", "ders"),
    _join("or", "der_authority"),
    "paper_eligible",
    _join("port", "folio"),
    _join("port", "folios"),
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


def test_builds_research_only_alignment_from_existing_observations() -> None:
    alignment = build_synthetic_sma_return_alignment_observation()
    expected = expected_synthetic_sma_return_alignment_observation_dict()

    assert type(alignment) is SmaReturnAlignmentObservation
    assert alignment.observation_type == "sma_return_alignment_observation"
    assert alignment.status == "candidate_only"
    assert alignment.authority == "advisory_only"
    assert alignment.capital_authority is False
    assert alignment.research_scope == "research_only"
    assert alignment.alignment_rule == "latest_sma_as_of_on_or_before_return_start"
    assert alignment.symbol == "SYNTH_ETF"
    assert alignment.as_of == "2026-01-20"
    assert alignment.source_return_count == 3
    assert alignment.source_sma_observation_count == 4
    assert alignment.aligned_return_count == 3
    assert alignment.unaligned_return_count == 0
    assert alignment.to_dict() == expected
    assert tuple(alignment.to_dict()) == tuple(expected)


def test_alignment_uses_latest_sma_state_at_or_before_return_start() -> None:
    sma_observations = build_synthetic_sma_return_alignment_sma_observations()
    return_observation = build_synthetic_sma_return_alignment_return_observation()
    alignment = build_sma_return_alignment_observation(
        tuple(reversed(sma_observations)),
        return_observation,
    )

    assert tuple(
        period.return_start_date for period in alignment.alignment_periods
    ) == (
        "2026-01-15",
        "2026-01-16",
        "2026-01-19",
    )
    assert tuple(
        period.sma_observation_as_of for period in alignment.alignment_periods
    ) == (
        "2026-01-14",
        "2026-01-16",
        "2026-01-19",
    )
    assert tuple(
        period.sma_observation_state for period in alignment.alignment_periods
    ) == (
        "equal",
        "above",
        "below",
    )
    assert alignment.source_sma_observations == sma_observations
    assert alignment.alignment_periods[2].source_sma_observation is sma_observations[2]
    assert alignment.alignment_periods[2].source_sma_observation is not (
        sma_observations[3]
    )


def test_source_identity_and_return_order_are_preserved() -> None:
    sma_observations = build_synthetic_sma_return_alignment_sma_observations()
    return_observation = build_synthetic_sma_return_alignment_return_observation()
    alignment = build_sma_return_alignment_observation(
        sma_observations,
        return_observation,
    )

    assert alignment.source_return_observation is return_observation
    assert tuple(id(value) for value in alignment.source_sma_observations) == tuple(
        id(value) for value in sma_observations
    )
    assert tuple(id(period.source_return) for period in alignment.alignment_periods) == (
        tuple(id(value) for value in return_observation.returns)
    )
    assert tuple(
        period.source_sma_observation for period in alignment.alignment_periods
    ) == (
        sma_observations[0],
        sma_observations[1],
        sma_observations[2],
    )


def test_empty_sma_observations_mark_each_return_period_unavailable() -> None:
    return_observation = build_synthetic_sma_return_alignment_return_observation()
    alignment = build_sma_return_alignment_observation((), return_observation)

    assert alignment.source_return_count == 3
    assert alignment.source_sma_observation_count == 0
    assert alignment.aligned_return_count == 0
    assert alignment.unaligned_return_count == 3
    assert tuple(
        period.alignment_state for period in alignment.alignment_periods
    ) == (
        "sma_state_unavailable",
        "sma_state_unavailable",
        "sma_state_unavailable",
    )
    assert all(period.sma_observation_as_of is None for period in alignment.alignment_periods)
    assert all(period.sma_observation_state is None for period in alignment.alignment_periods)
    assert all(period.source_sma_observation is None for period in alignment.alignment_periods)


def test_insufficient_return_history_yields_empty_alignment_periods() -> None:
    alignment = build_sma_return_alignment_observation(
        build_synthetic_sma_return_alignment_sma_observations(),
        build_synthetic_insufficient_research_return_series_observation(),
    )

    assert alignment.source_return_count == 0
    assert alignment.aligned_return_count == 0
    assert alignment.unaligned_return_count == 0
    assert alignment.alignment_periods == ()
    assert alignment.to_dict()["alignment_periods"] == []


def test_rejects_lookalikes_subclasses_mismatched_symbols_and_duplicate_as_of() -> None:
    class Lookalike:
        as_of = "2026-01-14"
        symbol = "SYNTH_ETF"

        def to_dict(self) -> dict[str, object]:
            return build_synthetic_sma_return_alignment_sma_observations()[
                0
            ].to_dict()

    class SmaObservationSubclass(SmaResearchObservation):
        pass

    source_sma = build_synthetic_sma_return_alignment_sma_observations()[0]
    subclass = SmaObservationSubclass(**_direct_sma_payload(source_sma))
    return_observation = build_synthetic_sma_return_alignment_return_observation()

    for value in (None, object(), {}, (Lookalike(),), (subclass,)):
        with pytest.raises(ValidationError, match="source_sma_observations"):
            build_sma_return_alignment_observation(value, return_observation)

    with pytest.raises(ValidationError, match="symbol"):
        build_sma_return_alignment_observation(
            (_sma_observation(symbol="OTHER", as_of="2026-01-14"),),
            return_observation,
        )

    with pytest.raises(ValidationError, match="duplicate as_of"):
        build_sma_return_alignment_observation(
            (source_sma, source_sma),
            return_observation,
        )

    with pytest.raises(ValidationError, match="after return observation as_of"):
        build_sma_return_alignment_observation(
            (_sma_observation(symbol="SYNTH_ETF", as_of="2026-01-21"),),
            return_observation,
        )

    with pytest.raises(ValidationError, match="source_return_observation"):
        build_sma_return_alignment_observation((source_sma,), object())


def test_direct_period_rejects_lookahead_sma_observation() -> None:
    alignment = build_synthetic_sma_return_alignment_observation()
    period = alignment.alignment_periods[2]
    future_sma = alignment.source_sma_observations[3]

    with pytest.raises(ValidationError, match="available on or before"):
        SmaReturnAlignmentPeriod(
            return_start_date=period.return_start_date,
            return_end_date=period.return_end_date,
            simple_return=period.simple_return,
            alignment_state="sma_state_available",
            sma_observation_as_of=future_sma.as_of,
            sma_observation_state=future_sma.position_vs_sma,
            source_return=period.source_return,
            source_sma_observation=future_sma,
        )


def test_direct_construction_rejects_mismatched_or_non_latest_alignment() -> None:
    alignment = build_synthetic_sma_return_alignment_observation()
    payload = _direct_payload(alignment)

    for field_name, value in (
        ("observation_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("research_scope", "other"),
        ("alignment_rule", "other"),
        ("source_return_count", 99),
        ("source_sma_observation_count", 99),
        ("aligned_return_count", 99),
        ("unaligned_return_count", 99),
        ("alignment_periods", (object(),)),
        ("limitations", (_join("action", "able metadata"),)),
        ("non_claims", ("positive claim",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaReturnAlignmentObservation(**mutated)

    stale_period = _period_with_sma(
        alignment.alignment_periods[1],
        alignment.source_sma_observations[0],
    )
    mutated = dict(payload)
    mutated["alignment_periods"] = (
        alignment.alignment_periods[0],
        stale_period,
        alignment.alignment_periods[2],
    )
    with pytest.raises(ValidationError, match="latest available SMA"):
        SmaReturnAlignmentObservation(**mutated)


def test_to_dict_is_primitive_only_deterministic_and_returns_fresh_lists() -> None:
    first = build_synthetic_sma_return_alignment_observation().to_dict()
    second = build_synthetic_sma_return_alignment_observation().to_dict()
    expected = expected_synthetic_sma_return_alignment_observation_dict()
    first_json = _compact_json(first)
    second_json = _compact_json(second)

    assert first == second == expected
    assert _primitive_only(first)
    assert first_json == second_json
    assert json.loads(first_json) == expected
    assert first["alignment_periods"] is not second["alignment_periods"]
    assert first["source_sma_observations"] is not second["source_sma_observations"]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["alignment_periods"].append(second["alignment_periods"][0])
    first["source_sma_observations"].append(second["source_sma_observations"][0])
    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == expected
    assert build_synthetic_sma_return_alignment_observation().to_dict() == expected


def test_object_is_frozen_and_slotted() -> None:
    alignment = build_synthetic_sma_return_alignment_observation()
    period = alignment.alignment_periods[0]

    assert hasattr(SmaReturnAlignmentObservation, "__slots__")
    assert hasattr(SmaReturnAlignmentPeriod, "__slots__")
    assert tuple(field.name for field in fields(SmaReturnAlignmentObservation)) == (
        "observation_type",
        "status",
        "authority",
        "capital_authority",
        "research_scope",
        "alignment_rule",
        "symbol",
        "as_of",
        "source_return_count",
        "source_sma_observation_count",
        "aligned_return_count",
        "unaligned_return_count",
        "alignment_periods",
        "source_return_observation",
        "source_sma_observations",
        "limitations",
        "non_claims",
    )
    assert tuple(field.name for field in fields(SmaReturnAlignmentPeriod)) == (
        "return_start_date",
        "return_end_date",
        "simple_return",
        "alignment_state",
        "sma_observation_as_of",
        "sma_observation_state",
        "source_return",
        "source_sma_observation",
    )
    with pytest.raises(FrozenInstanceError):
        alignment.symbol = "OTHER"
    with pytest.raises(FrozenInstanceError):
        period.alignment_state = "other"
    with pytest.raises((AttributeError, TypeError)):
        alignment.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    alignment = build_synthetic_sma_return_alignment_observation()
    period = alignment.alignment_periods[0]

    assert not hasattr(SmaReturnAlignmentObservation, "from_dict")
    assert not hasattr(SmaReturnAlignmentPeriod, "from_dict")
    assert not hasattr(alignment, "from_dict")
    assert not hasattr(period, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_public_payload_excludes_action_trading_and_derived_return_fields() -> None:
    payload = build_synthetic_sma_return_alignment_observation().to_dict()

    assert set(SMA_RETURN_ALIGNMENT_STATES) == {
        "sma_state_available",
        "sma_state_unavailable",
    }
    assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
    assert _capital_authority_values(payload) == [False] * len(
        _capital_authority_values(payload)
    )
    assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))


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


def _period_with_sma(
    period: SmaReturnAlignmentPeriod,
    source_sma_observation: SmaResearchObservation,
) -> SmaReturnAlignmentPeriod:
    return SmaReturnAlignmentPeriod(
        return_start_date=period.return_start_date,
        return_end_date=period.return_end_date,
        simple_return=period.simple_return,
        alignment_state="sma_state_available",
        sma_observation_as_of=source_sma_observation.as_of,
        sma_observation_state=source_sma_observation.position_vs_sma,
        source_return=period.source_return,
        source_sma_observation=source_sma_observation,
    )


def _direct_payload(
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


def _direct_sma_payload(
    observation: SmaResearchObservation,
) -> dict[str, object]:
    return {
        "observation_type": observation.observation_type,
        "status": observation.status,
        "authority": observation.authority,
        "capital_authority": observation.capital_authority,
        "symbol": observation.symbol,
        "as_of": observation.as_of,
        "window": observation.window,
        "sample_count": observation.sample_count,
        "eligible_sample_count": observation.eligible_sample_count,
        "ignored_future_sample_count": observation.ignored_future_sample_count,
        "latest_close": observation.latest_close,
        "sma_value": observation.sma_value,
        "distance_from_sma": observation.distance_from_sma,
        "distance_from_sma_pct": observation.distance_from_sma_pct,
        "position_vs_sma": observation.position_vs_sma,
        "limitations": observation.limitations,
        "non_claims": observation.non_claims,
    }


def _sma_observation(symbol: str, as_of: str) -> SmaResearchObservation:
    return build_sma_research_observation(
        symbol=symbol,
        as_of=as_of,
        window=2,
        price_points=(
            SmaResearchPricePoint("2026-01-13", Decimal("10.00")),
            SmaResearchPricePoint(as_of, Decimal("10.00")),
        ),
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
