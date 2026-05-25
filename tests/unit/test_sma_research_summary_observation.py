from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_research_summary_observation import (
    SMA_RESEARCH_SUMMARY_STATES,
    SmaResearchSummaryObservation,
    build_sma_research_summary_observation,
)


MODULE_PATH = Path("src/algotrader/research/sma_research_summary_observation.py")


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SYMBOL = "SYN-SMA-SUMMARY"
_AS_OF = "2026-03-20"
_WINDOW = 3
_SUMMARY_LIMITATIONS = (
    "aggregates exact existing SMA research observations only",
    "counts position metadata without altering SMA mechanics",
)
_EMPTY_LIMITATIONS = (
    *_SUMMARY_LIMITATIONS,
    "no SMA research observations were provided",
)
_SUMMARY_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mutation authority"),
    _not("paper read", "iness"),
    _not("live read", "iness"),
    _not("capital authority"),
    _not("tra", "ding authority"),
    _not("ra", "nking"),
    _not("sco", "ring"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
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
    _join("tra", "ding_authority"),
    "trading_ready",
}


def test_builds_from_tuple_of_existing_sma_observations() -> None:
    observations = _source_observations()
    summary = build_sma_research_summary_observation(observations)

    assert type(summary) is SmaResearchSummaryObservation
    assert summary.source_observations is observations
    assert summary.total_observation_count == 4
    assert summary.above_sma_count == 1
    assert summary.below_sma_count == 1
    assert summary.equal_sma_count == 1
    assert summary.insufficient_history_count == 1
    assert summary.summary_state == "observations_summarized"
    assert summary.to_dict() == _expected_summary_dict(observations)


def test_rejects_subclasses_lookalikes_dicts_raw_points_and_non_observations() -> None:
    class Lookalike:
        position_vs_sma = "above"

        def to_dict(self) -> dict[str, object]:
            return _above_observation().to_dict()

    class ObservationSubclass(SmaResearchObservation):
        pass

    observation = _above_observation()
    subclass = ObservationSubclass(**_direct_observation_payload(observation))
    raw_price_point = SmaResearchPricePoint("2026-03-20", Decimal("10"))

    invalid_inputs = (
        None,
        object(),
        {},
        (Lookalike(),),
        (raw_price_point,),
        (subclass,),
        (_direct_observation_payload(observation),),
    )

    for value in invalid_inputs:
        with pytest.raises(ValidationError, match="source_observations"):
            build_sma_research_summary_observation(value)


def test_preserves_source_observation_identity_and_ordering() -> None:
    observations = _source_observations()
    summary = build_sma_research_summary_observation(observations)

    assert summary.source_observations == observations
    assert tuple(id(observation) for observation in summary.source_observations) == tuple(
        id(observation) for observation in observations
    )
    assert tuple(
        observation.position_vs_sma for observation in summary.source_observations
    ) == (
        "above",
        "below",
        "equal",
        "insufficient_history",
    )
    assert summary.to_dict()["source_observations"] == [
        observation.to_dict() for observation in observations
    ]


def test_summary_does_not_mutate_source_observations() -> None:
    observations = _source_observations()
    before_payloads = [observation.to_dict() for observation in observations]

    summary = build_sma_research_summary_observation(observations)
    after_build_payloads = [observation.to_dict() for observation in observations]
    summary.to_dict()
    after_serialize_payloads = [observation.to_dict() for observation in observations]

    assert after_build_payloads == before_payloads
    assert after_serialize_payloads == before_payloads
    assert summary.source_observations is observations


def test_counts_above_below_equal_and_insufficient_history_observations() -> None:
    summary = build_sma_research_summary_observation(_source_observations())

    assert set(SMA_RESEARCH_SUMMARY_STATES) == {
        "observations_summarized",
        "empty_insufficient_observations",
    }
    assert summary.total_observation_count == 4
    assert summary.above_sma_count == 1
    assert summary.below_sma_count == 1
    assert summary.equal_sma_count == 1
    assert summary.insufficient_history_count == 1
    assert summary.to_dict()["above_sma_count"] == 1
    assert summary.to_dict()["insufficient_history_count"] == 1


def test_empty_input_has_explicit_empty_insufficient_summary_state() -> None:
    summary = build_sma_research_summary_observation(())

    assert summary.total_observation_count == 0
    assert summary.above_sma_count == 0
    assert summary.below_sma_count == 0
    assert summary.equal_sma_count == 0
    assert summary.insufficient_history_count == 0
    assert summary.summary_state == "empty_insufficient_observations"
    assert summary.source_observations == ()
    assert summary.to_dict() == _expected_empty_summary_dict()


def test_to_dict_is_primitive_only_and_compact_json_stable() -> None:
    observations = _source_observations()
    summary = build_sma_research_summary_observation(observations)
    first = summary.to_dict()
    second = summary.to_dict()
    first_json = _compact_json(first)
    second_json = _compact_json(second)

    assert first == second == _expected_summary_dict(observations)
    assert tuple(first) == tuple(_expected_summary_dict(observations))
    assert _primitive_only(first)
    assert first_json == second_json
    assert json.loads(first_json) == _expected_summary_dict(observations)
    assert first["source_observations"] is not second["source_observations"]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")
    first["source_observations"].append(_above_observation().to_dict())

    assert second == _expected_summary_dict(observations)
    assert summary.to_dict() == _expected_summary_dict(observations)


def test_payload_excludes_action_trading_keys_and_capital_authority_stays_false() -> None:
    payloads = (
        build_sma_research_summary_observation(_source_observations()).to_dict(),
        build_sma_research_summary_observation(()).to_dict(),
    )

    for payload in payloads:
        assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
        assert _capital_authority_values(payload) == [False] * len(
            _capital_authority_values(payload)
        )
        assert set(_SUMMARY_NON_CLAIMS).issubset(set(payload["non_claims"]))


def test_fixed_candidate_research_only_advisory_metadata_is_pinned() -> None:
    summary = build_sma_research_summary_observation(_source_observations())

    assert summary.observation_type == "sma_research_summary_observation"
    assert summary.status == "candidate_only"
    assert summary.authority == "advisory_only"
    assert summary.capital_authority is False
    assert summary.research_scope == "research_only"
    assert summary.to_dict()["observation_type"] == "sma_research_summary_observation"
    assert summary.to_dict()["status"] == "candidate_only"
    assert summary.to_dict()["authority"] == "advisory_only"
    assert summary.to_dict()["capital_authority"] is False
    assert summary.to_dict()["research_scope"] == "research_only"


def test_direct_construction_rejects_mismatched_or_malformed_values() -> None:
    observations = _source_observations()
    payload = _direct_payload(observations)

    for field_name, value in (
        ("observation_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("research_scope", "other"),
        ("total_observation_count", 99),
        ("above_sma_count", 99),
        ("below_sma_count", 99),
        ("equal_sma_count", 99),
        ("insufficient_history_count", 99),
        ("summary_state", "other"),
        ("source_observations", (object(),)),
        ("limitations", (_join("action", "able metadata"),)),
        ("non_claims", ("positive claim",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaResearchSummaryObservation(**mutated)


def test_object_is_frozen_and_slotted() -> None:
    summary = build_sma_research_summary_observation(_source_observations())

    assert hasattr(SmaResearchSummaryObservation, "__slots__")
    assert tuple(field.name for field in fields(SmaResearchSummaryObservation)) == (
        "observation_type",
        "status",
        "authority",
        "capital_authority",
        "research_scope",
        "total_observation_count",
        "above_sma_count",
        "below_sma_count",
        "equal_sma_count",
        "insufficient_history_count",
        "summary_state",
        "source_observations",
        "limitations",
        "non_claims",
    )
    with pytest.raises(FrozenInstanceError):
        summary.research_scope = "other"
    with pytest.raises((AttributeError, TypeError)):
        summary.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    summary = build_sma_research_summary_observation(_source_observations())

    assert not hasattr(SmaResearchSummaryObservation, "from_dict")
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


def _source_observations() -> tuple[SmaResearchObservation, ...]:
    return (
        _above_observation(),
        _below_observation(),
        _equal_observation(),
        _insufficient_observation(),
    )


def _above_observation() -> SmaResearchObservation:
    return build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-03-18", "9"),
            _point("2026-03-19", "10"),
            _point("2026-03-20", "11"),
        ),
    )


def _below_observation() -> SmaResearchObservation:
    return build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-03-18", "11"),
            _point("2026-03-19", "10"),
            _point("2026-03-20", "9"),
        ),
    )


def _equal_observation() -> SmaResearchObservation:
    return build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-03-18", "10"),
            _point("2026-03-19", "10"),
            _point("2026-03-20", "10"),
        ),
    )


def _insufficient_observation() -> SmaResearchObservation:
    return build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-03-19", "9"),
            _point("2026-03-20", "10"),
            _point("2026-03-21", "99"),
        ),
    )


def _point(value_date: str, close: str) -> SmaResearchPricePoint:
    return SmaResearchPricePoint(value_date, Decimal(close))


def _expected_summary_dict(
    observations: tuple[SmaResearchObservation, ...],
) -> dict[str, object]:
    return {
        "observation_type": "sma_research_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "total_observation_count": 4,
        "above_sma_count": 1,
        "below_sma_count": 1,
        "equal_sma_count": 1,
        "insufficient_history_count": 1,
        "summary_state": "observations_summarized",
        "source_observations": [
            observation.to_dict() for observation in observations
        ],
        "limitations": list(_SUMMARY_LIMITATIONS),
        "non_claims": list(_SUMMARY_NON_CLAIMS),
    }


def _expected_empty_summary_dict() -> dict[str, object]:
    return {
        "observation_type": "sma_research_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "total_observation_count": 0,
        "above_sma_count": 0,
        "below_sma_count": 0,
        "equal_sma_count": 0,
        "insufficient_history_count": 0,
        "summary_state": "empty_insufficient_observations",
        "source_observations": [],
        "limitations": list(_EMPTY_LIMITATIONS),
        "non_claims": list(_SUMMARY_NON_CLAIMS),
    }


def _direct_payload(
    observations: tuple[SmaResearchObservation, ...],
) -> dict[str, object]:
    return {
        "observation_type": "sma_research_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "total_observation_count": 4,
        "above_sma_count": 1,
        "below_sma_count": 1,
        "equal_sma_count": 1,
        "insufficient_history_count": 1,
        "summary_state": "observations_summarized",
        "source_observations": observations,
        "limitations": _SUMMARY_LIMITATIONS,
        "non_claims": _SUMMARY_NON_CLAIMS,
    }


def _direct_observation_payload(
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
