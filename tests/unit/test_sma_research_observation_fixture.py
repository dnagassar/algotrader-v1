from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path

from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
)
from tests.fixtures.sma_research_observation import (
    build_synthetic_insufficient_history_sma_research_observation,
    build_synthetic_sma_research_observation,
    build_synthetic_sma_research_price_points,
    expected_synthetic_insufficient_history_sma_research_observation_dict,
    expected_synthetic_sma_research_observation_dict,
    expected_synthetic_sma_research_price_point_dicts,
)


MODULE_PATH = Path("tests/fixtures/sma_research_observation.py")


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_REQUIRED_LIMITATIONS = (
    "synthetic broad ETF close series for fixture mechanics only",
    "fixed date samples with later samples ignored by the builder",
    "candidate-only advisory research metadata with no system connection",
)
_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("meth", "odology app", "roval"),
    _not("predict", "ive validity"),
    _not("prof", "itability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evalu", "ator behavior"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mut", "ation authority"),
    _not("pa", "per read", "iness"),
    _not("li", "ve read", "iness"),
    _not("capital ", "authority"),
    _not("tra", "ding authority"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "decimal",
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
_FORBIDDEN_SOURCE_TOKENS = (
    _join("app", "roved"),
    _join("app", "roval"),
    _join("author", "ized"),
    _join("bro", "ker"),
    "account",
    _join("or", "der"),
    "fill",
    _join("allo", "cation"),
    _join("port", "folio"),
    _join("mut", "ation"),
    "paper_ready",
    "paper-ready",
    "live_ready",
    "live-ready",
    "trading_ready",
    "trading-ready",
    "actionable",
    _join("file", "_io"),
    _join("net", "work"),
    _join("so", "cket"),
    "vendor",
    _join("cre", "dential"),
    _join("run", "time"),
    _join("sche", "duler"),
    "dashboard",
    "notebook",
    _join("l", "lm"),
    "agent",
    "ranking",
    "scoring",
    _join("recomm", "endation"),
    _join("tra", "ding authority"),
)
_FORBIDDEN_PAYLOAD_KEYS = {
    "account",
    "accounts",
    "actionable",
    _join("allo", "cation"),
    _join("allo", "cations"),
    _join("allo", "cation_authority"),
    "approved",
    _join("bro", "ker"),
    _join("bro", "ker_authority"),
    "capital_authority_state",
    "evaluator",
    "fill",
    "fills",
    "live_authorized",
    "live_probe_eligible",
    _join("or", "der"),
    _join("or", "ders"),
    _join("or", "der_authority"),
    "paper_eligible",
    _join("port", "folio"),
    _join("port", "folios"),
    "ranking",
    _join("recomm", "endation"),
    "readiness",
    "score",
    "scoring",
    "signal",
    _join("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_POSITIVE_STATE_TEXT = (
    _join("app", "roved"),
    "paper_ready",
    "paper-ready",
    "live_ready",
    "live-ready",
    "trading_ready",
    "trading-ready",
    "actionable",
)


def test_fixture_builders_return_exact_phase_195_production_types() -> None:
    price_points = build_synthetic_sma_research_price_points()
    observation = build_synthetic_sma_research_observation()
    insufficient = build_synthetic_insufficient_history_sma_research_observation()

    assert type(price_points) is tuple
    assert all(type(point) is SmaResearchPricePoint for point in price_points)
    assert type(observation) is SmaResearchObservation
    assert type(insufficient) is SmaResearchObservation


def test_expected_dict_helpers_match_to_dict_exactly() -> None:
    price_points = build_synthetic_sma_research_price_points()
    observation = build_synthetic_sma_research_observation()
    insufficient = build_synthetic_insufficient_history_sma_research_observation()

    assert [point.to_dict() for point in price_points] == (
        expected_synthetic_sma_research_price_point_dicts()
    )
    assert observation.to_dict() == expected_synthetic_sma_research_observation_dict()
    assert insufficient.to_dict() == (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )


def test_expected_dict_helpers_return_fresh_mutable_primitive_copies() -> None:
    first_points = expected_synthetic_sma_research_price_point_dicts()
    second_points = expected_synthetic_sma_research_price_point_dicts()
    first_observation = expected_synthetic_sma_research_observation_dict()
    second_observation = expected_synthetic_sma_research_observation_dict()
    first_insufficient = (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )
    second_insufficient = (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )

    assert _primitive_only(first_points)
    assert _primitive_only(first_observation)
    assert _primitive_only(first_insufficient)
    assert first_points is not second_points
    assert first_points[0] is not second_points[0]
    assert first_observation["limitations"] is not second_observation["limitations"]
    assert first_observation["non_claims"] is not second_observation["non_claims"]
    assert first_insufficient["limitations"] is not second_insufficient["limitations"]
    assert first_insufficient["non_claims"] is not second_insufficient["non_claims"]

    first_points[0]["close"] = "0.00"
    first_observation["limitations"].append("mutated copy")
    first_observation["non_claims"].append("not mutated copy")
    first_insufficient["limitations"].append("mutated copy")
    first_insufficient["non_claims"].append("not mutated copy")

    assert second_points == expected_synthetic_sma_research_price_point_dicts()
    assert second_observation == build_synthetic_sma_research_observation().to_dict()
    assert second_insufficient == (
        build_synthetic_insufficient_history_sma_research_observation().to_dict()
    )


def test_repeated_construction_is_deterministic() -> None:
    first_points = build_synthetic_sma_research_price_points()
    second_points = build_synthetic_sma_research_price_points()
    first_observation = build_synthetic_sma_research_observation()
    second_observation = build_synthetic_sma_research_observation()
    first_insufficient = build_synthetic_insufficient_history_sma_research_observation()
    second_insufficient = (
        build_synthetic_insufficient_history_sma_research_observation()
    )

    assert first_points == second_points
    assert first_points is not second_points
    assert first_points[0] is not second_points[0]
    assert first_observation == second_observation
    assert first_observation is not second_observation
    assert first_insufficient == second_insufficient
    assert first_insufficient is not second_insufficient
    assert first_observation.to_dict() == second_observation.to_dict()
    assert first_insufficient.to_dict() == second_insufficient.to_dict()


def test_compact_json_bytes_are_deterministic() -> None:
    first_primary = _compact_json_bytes(build_synthetic_sma_research_observation())
    second_primary = _compact_json_bytes(build_synthetic_sma_research_observation())
    first_insufficient = _compact_json_bytes(
        build_synthetic_insufficient_history_sma_research_observation()
    )
    second_insufficient = _compact_json_bytes(
        build_synthetic_insufficient_history_sma_research_observation()
    )

    assert first_primary == second_primary
    assert first_insufficient == second_insufficient
    assert b", " not in first_primary
    assert b": " not in first_primary
    assert b", " not in first_insufficient
    assert b": " not in first_insufficient
    assert json.loads(first_primary.decode("utf-8")) == (
        expected_synthetic_sma_research_observation_dict()
    )
    assert json.loads(first_insufficient.decode("utf-8")) == (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )


def test_future_sample_count_is_pinned_and_primary_fixture_is_above_sma() -> None:
    observation = build_synthetic_sma_research_observation()
    payload = observation.to_dict()

    assert observation.symbol == "SYNTH_ETF"
    assert observation.as_of == "2026-01-20"
    assert observation.window == 3
    assert observation.sample_count == 4
    assert observation.eligible_sample_count == 3
    assert observation.ignored_future_sample_count == 1
    assert observation.latest_close == Decimal("110.00")
    assert observation.sma_value == Decimal("100.00")
    assert observation.distance_from_sma == Decimal("10.00")
    assert observation.distance_from_sma_pct == Decimal("0.1")
    assert observation.position_vs_sma == "above"
    assert payload["ignored_future_sample_count"] == 1
    assert payload["position_vs_sma"] == "above"


def test_insufficient_history_fixture_has_no_sma_or_distance_values() -> None:
    observation = build_synthetic_insufficient_history_sma_research_observation()
    payload = observation.to_dict()

    assert observation.sample_count == 3
    assert observation.eligible_sample_count == 2
    assert observation.ignored_future_sample_count == 1
    assert observation.latest_close == Decimal("101.00")
    assert observation.sma_value is None
    assert observation.distance_from_sma is None
    assert observation.distance_from_sma_pct is None
    assert observation.position_vs_sma == "insufficient_history"
    assert payload["latest_close"] == "101.00"
    assert payload["sma_value"] is None
    assert payload["distance_from_sma"] is None
    assert payload["distance_from_sma_pct"] is None


def test_fixed_advisory_metadata_limitations_and_non_claims_are_pinned() -> None:
    payloads = (
        build_synthetic_sma_research_observation().to_dict(),
        build_synthetic_insufficient_history_sma_research_observation().to_dict(),
    )

    for payload in payloads:
        assert payload["observation_type"] == "sma_research_observation"
        assert payload["status"] == "candidate_only"
        assert payload["authority"] == "advisory_only"
        assert payload["capital_authority"] is False
        assert tuple(payload["limitations"]) == _REQUIRED_LIMITATIONS
        assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))
        assert payload["non_claims"].count(_not("meth", "odology app", "roval")) == 1


def test_payload_has_no_positive_action_or_authority_states() -> None:
    payloads = (
        build_synthetic_sma_research_observation().to_dict(),
        build_synthetic_insufficient_history_sma_research_observation().to_dict(),
    )

    for payload in payloads:
        assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
        for text in _string_values(payload):
            lowered = text.lower()
            if lowered.startswith("not "):
                continue
            assert not any(
                token in lowered for token in _FORBIDDEN_POSITIVE_STATE_TEXT
            )


def test_fixture_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert "from_dict" not in _function_names()
    assert "from_dict" not in call_names


def test_fixture_module_has_no_forbidden_source_literals() -> None:
    lowered = _source_text().lower()

    assert [
        token for token in _FORBIDDEN_SOURCE_TOKENS if token in lowered
    ] == []


def _compact_json_bytes(observation: SmaResearchObservation) -> bytes:
    return json.dumps(
        observation.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(type(key) is str and _primitive_only(item) for key, item in value.items())

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


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        strings: list[str] = []
        for nested_value in value.values():
            strings.extend(_string_values(nested_value))
        return tuple(strings)
    if isinstance(value, list):
        strings = []
        for nested_value in value:
            strings.extend(_string_values(nested_value))
        return tuple(strings)

    return ()


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


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
