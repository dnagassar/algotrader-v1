from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path

from algotrader.research.research_return_observation import (
    ResearchReturnPoint,
    ResearchReturnPricePoint,
    ResearchReturnSeriesObservation,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_insufficient_research_return_series_observation,
    build_synthetic_research_return_price_points,
    build_synthetic_research_return_series_observation,
    expected_synthetic_insufficient_research_return_series_observation_dict,
    expected_synthetic_research_return_price_point_dicts,
    expected_synthetic_research_return_series_observation_dict,
)


MODULE_PATH = Path("tests/fixtures/research_return_observation.py")


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_REQUIRED_LIMITATIONS = (
    "synthetic broad ETF close series for return mechanics only",
    "fixed close samples with later samples ignored by the builder",
    "candidate-only advisory research metadata with no system connection",
)
_REQUIRED_NON_CLAIMS = (
    _not("sour", "ce/data app", "roval"),
    _not("adjusted-close/corporate-action completeness"),
    _not("predict", "ive validity"),
    _not("prof", "itability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evalu", "ator behavior"),
    _not("back", "testing validation"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mut", "ation authority"),
    _not("pa", "per read", "iness"),
    _not("li", "ve read", "iness"),
    _not("capital ", "authority"),
    _not("tra", "ding authority"),
    _not("meth", "odology app", "roval"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "decimal",
    "algotrader.research.research_return_observation",
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
_FORBIDDEN_SOURCE_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
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
    _join("read", "iness"),
    _join("tra", "ding authority"),
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
    _join("ra", "nking"),
    _join("sco", "ring"),
    _join("recomm", "endation"),
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
    _join("ra", "nking"),
    _join("recomm", "endation"),
    "readiness",
    _join("sco", "re"),
    _join("sco", "ring"),
    "signal",
    _join("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_POSITIVE_STATE_TEXT = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("read", "iness"),
    _join("tra", "ding authority"),
    "paper_ready",
    "paper-ready",
    "live_ready",
    "live-ready",
    "trading_ready",
    "trading-ready",
    "actionable",
)


def test_fixture_builders_return_exact_phase_210_production_types() -> None:
    price_points = build_synthetic_research_return_price_points()
    observation = build_synthetic_research_return_series_observation()
    insufficient = build_synthetic_insufficient_research_return_series_observation()

    assert type(price_points) is tuple
    assert all(type(point) is ResearchReturnPricePoint for point in price_points)
    assert type(observation) is ResearchReturnSeriesObservation
    assert all(type(point) is ResearchReturnPoint for point in observation.returns)
    assert type(insufficient) is ResearchReturnSeriesObservation
    assert insufficient.returns == ()


def test_expected_dict_helpers_match_to_dict_exactly() -> None:
    price_points = build_synthetic_research_return_price_points()
    observation = build_synthetic_research_return_series_observation()
    insufficient = build_synthetic_insufficient_research_return_series_observation()

    assert [point.to_dict() for point in price_points] == (
        expected_synthetic_research_return_price_point_dicts()
    )
    assert observation.to_dict() == (
        expected_synthetic_research_return_series_observation_dict()
    )
    assert insufficient.to_dict() == (
        expected_synthetic_insufficient_research_return_series_observation_dict()
    )


def test_expected_dict_helpers_return_fresh_mutable_primitive_copies() -> None:
    first_points = expected_synthetic_research_return_price_point_dicts()
    second_points = expected_synthetic_research_return_price_point_dicts()
    first_observation = expected_synthetic_research_return_series_observation_dict()
    second_observation = expected_synthetic_research_return_series_observation_dict()
    first_insufficient = (
        expected_synthetic_insufficient_research_return_series_observation_dict()
    )
    second_insufficient = (
        expected_synthetic_insufficient_research_return_series_observation_dict()
    )

    assert _primitive_only(first_points)
    assert _primitive_only(first_observation)
    assert _primitive_only(first_insufficient)
    assert first_points is not second_points
    assert first_points[0] is not second_points[0]
    assert first_observation["returns"] is not second_observation["returns"]
    assert first_observation["returns"][0] is not second_observation["returns"][0]
    assert first_observation["limitations"] is not second_observation["limitations"]
    assert first_observation["non_claims"] is not second_observation["non_claims"]
    assert first_insufficient["returns"] is not second_insufficient["returns"]
    assert first_insufficient["limitations"] is not second_insufficient["limitations"]
    assert first_insufficient["non_claims"] is not second_insufficient["non_claims"]

    first_points[0]["close"] = "0.00"
    first_observation["returns"][0]["simple_return"] = "mutated"
    first_observation["limitations"].append("mutated copy")
    first_observation["non_claims"].append("not mutated copy")
    first_insufficient["returns"].append({"mutated": "copy"})
    first_insufficient["limitations"].append("mutated copy")
    first_insufficient["non_claims"].append("not mutated copy")

    assert second_points == expected_synthetic_research_return_price_point_dicts()
    assert second_observation == (
        build_synthetic_research_return_series_observation().to_dict()
    )
    assert second_insufficient == (
        build_synthetic_insufficient_research_return_series_observation().to_dict()
    )


def test_repeated_construction_is_deterministic() -> None:
    first_points = build_synthetic_research_return_price_points()
    second_points = build_synthetic_research_return_price_points()
    first_observation = build_synthetic_research_return_series_observation()
    second_observation = build_synthetic_research_return_series_observation()
    first_insufficient = build_synthetic_insufficient_research_return_series_observation()
    second_insufficient = (
        build_synthetic_insufficient_research_return_series_observation()
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
    first_primary = _compact_json_bytes(
        build_synthetic_research_return_series_observation()
    )
    second_primary = _compact_json_bytes(
        build_synthetic_research_return_series_observation()
    )
    first_insufficient = _compact_json_bytes(
        build_synthetic_insufficient_research_return_series_observation()
    )
    second_insufficient = _compact_json_bytes(
        build_synthetic_insufficient_research_return_series_observation()
    )

    assert first_primary == second_primary
    assert first_insufficient == second_insufficient
    assert b", " not in first_primary
    assert b": " not in first_primary
    assert b", " not in first_insufficient
    assert b": " not in first_insufficient
    assert json.loads(first_primary.decode("utf-8")) == (
        expected_synthetic_research_return_series_observation_dict()
    )
    assert json.loads(first_insufficient.decode("utf-8")) == (
        expected_synthetic_insufficient_research_return_series_observation_dict()
    )


def test_primary_fixture_has_positive_negative_and_zero_returns() -> None:
    observation = build_synthetic_research_return_series_observation()

    assert tuple(point.simple_return for point in observation.returns) == (
        Decimal("0.05"),
        Decimal("-0.1"),
        Decimal("0"),
    )
    assert any(point.simple_return > Decimal("0") for point in observation.returns)
    assert any(point.simple_return < Decimal("0") for point in observation.returns)
    assert any(point.simple_return == Decimal("0") for point in observation.returns)


def test_future_sample_count_is_pinned() -> None:
    observation = build_synthetic_research_return_series_observation()
    payload = observation.to_dict()

    assert observation.symbol == "SYNTH_ETF"
    assert observation.as_of == "2026-01-20"
    assert observation.sample_count == 5
    assert observation.eligible_sample_count == 4
    assert observation.ignored_future_sample_count == 1
    assert observation.return_count == 3
    assert payload["ignored_future_sample_count"] == 1
    assert "2026-01-21" not in _compact_json(observation)


def test_primary_returns_are_consecutive_eligible_close_to_close_returns() -> None:
    observation = build_synthetic_research_return_series_observation()
    eligible_points = tuple(
        point
        for point in build_synthetic_research_return_price_points()
        if point.date <= observation.as_of
    )

    assert len(observation.returns) == len(eligible_points) - 1
    for return_point, start_point, end_point in zip(
        observation.returns,
        eligible_points,
        eligible_points[1:],
    ):
        assert return_point.start_date == start_point.date
        assert return_point.end_date == end_point.date
        assert return_point.start_close == start_point.close
        assert return_point.end_close == end_point.close
        assert return_point.simple_return == (
            (end_point.close / start_point.close) - Decimal("1")
        )


def test_insufficient_fixture_has_zero_returns() -> None:
    observation = build_synthetic_insufficient_research_return_series_observation()
    payload = observation.to_dict()

    assert observation.sample_count == 2
    assert observation.eligible_sample_count == 1
    assert observation.ignored_future_sample_count == 1
    assert observation.return_count == 0
    assert observation.returns == ()
    assert payload["returns"] == []
    assert payload["return_count"] == 0


def test_fixed_advisory_metadata_limitations_and_non_claims_are_pinned() -> None:
    payloads = (
        build_synthetic_research_return_series_observation().to_dict(),
        build_synthetic_insufficient_research_return_series_observation().to_dict(),
    )

    for payload in payloads:
        assert payload["observation_type"] == "research_return_series_observation"
        assert payload["status"] == "candidate_only"
        assert payload["authority"] == "advisory_only"
        assert payload["capital_authority"] is False
        assert payload["return_method"] == "close_to_close_simple_return"
        assert payload["price_basis"] == "synthetic_close"
        assert tuple(payload["limitations"]) == _REQUIRED_LIMITATIONS
        assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))
        assert payload["non_claims"].count(_not("meth", "odology app", "roval")) == 1


def test_payload_has_no_positive_action_or_authority_states() -> None:
    payloads = (
        build_synthetic_research_return_series_observation().to_dict(),
        build_synthetic_insufficient_research_return_series_observation().to_dict(),
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


def test_no_from_dict_exists() -> None:
    observation = build_synthetic_research_return_series_observation()
    insufficient = build_synthetic_insufficient_research_return_series_observation()
    price_point = build_synthetic_research_return_price_points()[0]
    return_point = observation.returns[0]

    assert not hasattr(ResearchReturnSeriesObservation, "from_dict")
    assert not hasattr(ResearchReturnPricePoint, "from_dict")
    assert not hasattr(ResearchReturnPoint, "from_dict")
    assert not hasattr(observation, "from_dict")
    assert not hasattr(insufficient, "from_dict")
    assert not hasattr(price_point, "from_dict")
    assert not hasattr(return_point, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


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


def _compact_json_bytes(observation: ResearchReturnSeriesObservation) -> bytes:
    return _compact_json(observation).encode("utf-8")


def _compact_json(observation: ResearchReturnSeriesObservation) -> str:
    return json.dumps(
        observation.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )


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
