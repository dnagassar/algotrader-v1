from __future__ import annotations

import ast
import json
from pathlib import Path

from algotrader.research.sma_research_observation_brief_container import (
    SmaResearchObservationBrief,
    build_sma_research_observation_brief,
)
from algotrader.research.sma_research_observation_brief_section import (
    SmaResearchObservationBriefSection,
)
from tests.fixtures.sma_research_observation_brief_container import (
    build_synthetic_sma_research_observation_brief,
    expected_synthetic_sma_research_observation_brief_dict,
)
from tests.fixtures.sma_research_observation_brief_section import (
    expected_synthetic_sma_research_observation_brief_section_dict,
)


MODULE_PATH = Path("tests/fixtures/sma_research_observation_brief_container.py")


def _join(*parts: str) -> str:
    return "".join(parts)


_BRIEF_ID = "sma-research-observation-brief:synthetic:broad-etf-sma"
_TITLE = "Synthetic broad ETF SMA research observation brief"
_SUMMARY = (
    "Brief is advisory-only synthetic SMA observation content for broad ETF "
    "SMA mechanics."
)
_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.sma_research_observation_brief_container",
    "tests.fixtures.sma_research_observation_brief_section",
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
    _join("recomm", "end"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("bro", "ker"),
    "account",
    _join("or", "der"),
    "fill",
    _join("allo", "cation"),
    _join("port", "folio"),
    _join("mut", "ation"),
    _join("pa", "per"),
    _join("li", "ve"),
    _join("read", "iness"),
    "paper_ready",
    "paper-ready",
    "live_ready",
    "live-ready",
    "trading_ready",
    "trading-ready",
    _join("action", "able"),
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
    _join("capital ", "authority"),
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
    "buy",
    _join("bro", "ker"),
    _join("bro", "ker_authority"),
    "evaluator",
    "fill",
    "fills",
    "hold",
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
    "sell",
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
    _join("action", "able"),
)


def test_fixture_builder_returns_exact_phase_201_production_type() -> None:
    brief = build_synthetic_sma_research_observation_brief()

    assert type(brief) is SmaResearchObservationBrief
    assert all(type(section) is SmaResearchObservationBriefSection for section in brief.sections)


def test_expected_dict_helper_matches_to_dict_exactly() -> None:
    brief = build_synthetic_sma_research_observation_brief()

    assert brief.to_dict() == expected_synthetic_sma_research_observation_brief_dict()


def test_expected_dict_helper_returns_fresh_mutable_primitive_copies() -> None:
    first = expected_synthetic_sma_research_observation_brief_dict()
    second = expected_synthetic_sma_research_observation_brief_dict()

    assert _primitive_only(first)
    assert first is not second
    assert first["sections"] is not second["sections"]
    assert first["sections"][0] is not second["sections"][0]
    assert first["sections"][0]["items"] is not second["sections"][0]["items"]
    assert first["sections"][0]["items"][0] is not second["sections"][0]["items"][0]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["sections"][0]["items"][0]["limitations"].append("mutated primitive copy")
    first["sections"][0]["limitations"].append("mutated section copy")
    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == build_synthetic_sma_research_observation_brief().to_dict()


def test_repeated_construction_is_deterministic() -> None:
    first = build_synthetic_sma_research_observation_brief()
    second = build_synthetic_sma_research_observation_brief()

    assert first == second
    assert first is not second
    assert first.sections == second.sections
    assert first.sections[0] is not second.sections[0]
    assert first.to_dict() == second.to_dict()


def test_compact_json_bytes_are_deterministic() -> None:
    first = _compact_json_bytes(build_synthetic_sma_research_observation_brief())
    second = _compact_json_bytes(build_synthetic_sma_research_observation_brief())

    assert first == second
    assert first == json.dumps(
        expected_synthetic_sma_research_observation_brief_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert json.loads(first.decode("utf-8")) == (
        expected_synthetic_sma_research_observation_brief_dict()
    )


def test_brief_contains_exactly_one_section_in_expected_order() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    payload = brief.to_dict()
    expected_section = expected_synthetic_sma_research_observation_brief_section_dict()

    assert brief.brief_id == _BRIEF_ID
    assert brief.title == _TITLE
    assert brief.summary == _SUMMARY
    assert len(brief.sections) == 1
    assert payload["section_count"] == 1
    assert [section.section_id for section in brief.sections] == [
        expected_section["section_id"],
    ]
    assert [section["section_id"] for section in payload["sections"]] == [
        expected_section["section_id"],
    ]


def test_nested_section_payload_matches_phase_200_expected_dict() -> None:
    brief = build_synthetic_sma_research_observation_brief()

    assert brief.to_dict()["sections"] == [
        expected_synthetic_sma_research_observation_brief_section_dict(),
    ]


def test_section_object_identity_is_preserved() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    rebuilt = build_sma_research_observation_brief(
        brief_id=brief.brief_id,
        title=brief.title,
        summary=brief.summary,
        sections=brief.sections,
    )

    assert rebuilt.sections[0] is brief.sections[0]
    assert rebuilt.to_dict() == brief.to_dict()


def test_limitations_and_non_claims_carry_forward() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    section = brief.sections[0]

    assert brief.limitations == section.limitations
    assert brief.non_claims == section.non_claims
    assert brief.to_dict()["limitations"] == list(section.limitations)
    assert brief.to_dict()["non_claims"] == list(section.non_claims)


def test_no_from_dict_exists() -> None:
    brief = build_synthetic_sma_research_observation_brief()

    assert not hasattr(SmaResearchObservationBrief, "from_dict")
    assert not hasattr(brief, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_no_positive_action_or_authority_states_appear() -> None:
    payload = build_synthetic_sma_research_observation_brief().to_dict()

    assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
    for text in _string_values(payload):
        lowered = text.lower()
        if lowered.startswith("not "):
            continue
        assert not any(token in lowered for token in _FORBIDDEN_POSITIVE_STATE_TEXT)


def test_fixture_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_module_has_no_forbidden_source_literals() -> None:
    lowered = _source_text().lower()

    assert [
        token for token in _FORBIDDEN_SOURCE_TOKENS if token in lowered
    ] == []


def _compact_json_bytes(brief: SmaResearchObservationBrief) -> bytes:
    return json.dumps(
        brief.to_dict(),
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
