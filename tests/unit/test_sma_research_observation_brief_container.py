from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.sma_research_observation_brief_container import (
    SmaResearchObservationBrief,
    build_sma_research_observation_brief,
)
from algotrader.research.sma_research_observation_brief_section import (
    SmaResearchObservationBriefSection,
)
from tests.fixtures.sma_research_observation_brief_section import (
    build_synthetic_sma_research_observation_brief_section,
    expected_synthetic_sma_research_observation_brief_section_dict,
)


MODULE_PATH = Path("src/algotrader/research/sma_research_observation_brief_container.py")


def _join(*parts: str) -> str:
    return "".join(parts)


_BRIEF_ID = "sma-research-observation-brief:synthetic:broad-etf-sma"
_TITLE = "Synthetic broad ETF SMA observation brief"
_SUMMARY = "SMA observation brief contains 1 advisory-only synthetic section."
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.sma_research_observation_brief_section",
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


def test_builds_brief_from_phase_200_synthetic_section_fixture() -> None:
    section = build_synthetic_sma_research_observation_brief_section()
    brief = _build_brief(section)

    assert type(brief) is SmaResearchObservationBrief
    assert brief.sections == (section,)
    assert brief.to_dict() == _expected_brief_dict()


def test_preserves_exact_section_identity_and_order() -> None:
    section = build_synthetic_sma_research_observation_brief_section()
    brief = _build_brief(section)

    assert brief.sections[0] is section
    assert brief.to_dict()["sections"][0] == section.to_dict()


def test_rejects_empty_section_list() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        build_sma_research_observation_brief(
            _BRIEF_ID,
            _TITLE,
            _SUMMARY,
            (),
        )


def test_rejects_duplicate_section_identities() -> None:
    section = build_synthetic_sma_research_observation_brief_section()

    with pytest.raises(ValidationError, match="duplicate section identities"):
        build_sma_research_observation_brief(
            _BRIEF_ID,
            _TITLE,
            _SUMMARY,
            (section, section),
        )


def test_rejects_non_sections_lookalikes_and_subclasses() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_sma_research_observation_brief_section_dict()

    class SectionSubclass(SmaResearchObservationBriefSection):
        pass

    source = build_synthetic_sma_research_observation_brief_section()
    subclass = SectionSubclass(
        section_type=source.section_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        section_id=source.section_id,
        title=source.title,
        summary=source.summary,
        items=source.items,
        limitations=source.limitations,
        non_claims=source.non_claims,
    )

    for bad_section in (None, object(), {}, Lookalike(), subclass):
        with pytest.raises(ValidationError, match="sections\\[0\\]"):
            build_sma_research_observation_brief(
                _BRIEF_ID,
                _TITLE,
                _SUMMARY,
                (bad_section,),
            )


def test_requires_non_empty_brief_id_title_and_summary() -> None:
    section = build_synthetic_sma_research_observation_brief_section()

    for brief_id, title, summary in (
        ("", _TITLE, _SUMMARY),
        ("  bad", _TITLE, _SUMMARY),
        (_BRIEF_ID, "", _SUMMARY),
        (_BRIEF_ID, _join("app", "roved title"), _SUMMARY),
        (_BRIEF_ID, _TITLE, ""),
        (_BRIEF_ID, _TITLE, _join("b", "uy summary")),
    ):
        with pytest.raises(ValidationError):
            build_sma_research_observation_brief(
                brief_id,
                title,
                summary,
                (section,),
            )


def test_fixed_advisory_metadata_is_pinned() -> None:
    brief = _build_default_brief()
    payload = brief.to_dict()

    assert brief.brief_type == "sma_research_observation_brief"
    assert brief.status == "candidate_only"
    assert brief.authority == "advisory_only"
    assert brief.capital_authority is False
    assert payload["brief_type"] == "sma_research_observation_brief"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert payload["brief_id"] == _BRIEF_ID
    assert payload["title"] == _TITLE
    assert payload["summary"] == _SUMMARY
    assert payload["section_count"] == 1


def test_limitations_and_non_claims_carry_forward_with_first_seen_dedupe() -> None:
    first = build_synthetic_sma_research_observation_brief_section()
    second = build_synthetic_sma_research_observation_brief_section()
    brief = build_sma_research_observation_brief(
        _BRIEF_ID,
        _TITLE,
        _SUMMARY,
        (first, second),
    )

    assert brief.sections == (first, second)
    assert brief.limitations == first.limitations
    assert brief.non_claims == first.non_claims
    assert brief.to_dict()["limitations"] == list(first.limitations)
    assert brief.to_dict()["non_claims"] == list(first.non_claims)


def test_direct_construction_rejects_metadata_mismatches() -> None:
    payload = _direct_payload()

    for field_name, value in (
        ("brief_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("limitations", ("synthetic broad ETF close series for fixture mechanics only",)),
        ("non_claims", ("not unrelated",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaResearchObservationBrief(**mutated)


def test_to_dict_is_primitive_only_and_deterministic() -> None:
    first = _build_default_brief().to_dict()
    second = _build_default_brief().to_dict()

    assert first == second == _expected_brief_dict()
    assert tuple(first) == tuple(_expected_brief_dict())
    assert _primitive_only(first)
    assert first["sections"] is not second["sections"]
    assert first["sections"][0] is not second["sections"][0]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["sections"][0]["limitations"].append("mutated primitive copy")
    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == _expected_brief_dict()


def test_repeated_construction_is_byte_for_byte_deterministic_under_compact_json() -> None:
    first = _build_default_brief()
    second = _build_default_brief()
    first_json = _compact_json_bytes(first)
    second_json = _compact_json_bytes(second)

    assert first == second
    assert first is not second
    assert first_json == second_json
    assert first_json == json.dumps(
        _expected_brief_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert json.loads(first_json.decode("utf-8")) == _expected_brief_dict()


def test_source_section_to_dict_output_is_unchanged() -> None:
    section = build_synthetic_sma_research_observation_brief_section()
    before = section.to_dict()
    brief = _build_brief(section)
    after_build = section.to_dict()
    payload = brief.to_dict()
    after_serialize = section.to_dict()

    assert before == expected_synthetic_sma_research_observation_brief_section_dict()
    assert after_build == before
    assert payload["sections"] == [before]
    assert after_serialize == before


def test_object_is_frozen_and_slotted() -> None:
    brief = _build_default_brief()

    assert hasattr(SmaResearchObservationBrief, "__slots__")
    assert tuple(field.name for field in fields(SmaResearchObservationBrief)) == (
        "brief_type",
        "status",
        "authority",
        "capital_authority",
        "brief_id",
        "title",
        "summary",
        "sections",
        "limitations",
        "non_claims",
    )
    with pytest.raises(FrozenInstanceError):
        brief.title = "other"
    with pytest.raises((AttributeError, TypeError)):
        brief.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    brief = _build_default_brief()

    assert not hasattr(SmaResearchObservationBrief, "from_dict")
    assert not hasattr(brief, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_public_payload_keys_contain_no_action_or_trading_authority_fields() -> None:
    payload = _build_default_brief().to_dict()

    assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))


def test_production_module_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_production_module_has_no_forbidden_imports_calls_or_literals() -> None:
    imports = _import_references()
    call_names = _call_names()
    lowered = _source_text().lower()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert [
        token for token in _FORBIDDEN_SOURCE_TOKENS if token in lowered
    ] == []


def _build_default_brief() -> SmaResearchObservationBrief:
    return _build_brief(build_synthetic_sma_research_observation_brief_section())


def _build_brief(
    section: SmaResearchObservationBriefSection,
) -> SmaResearchObservationBrief:
    return build_sma_research_observation_brief(
        _BRIEF_ID,
        _TITLE,
        _SUMMARY,
        (section,),
    )


def _expected_brief_dict() -> dict[str, object]:
    section = expected_synthetic_sma_research_observation_brief_section_dict()
    return {
        "brief_type": "sma_research_observation_brief",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "brief_id": _BRIEF_ID,
        "title": _TITLE,
        "summary": _SUMMARY,
        "section_count": 1,
        "sections": [section],
        "limitations": list(section["limitations"]),
        "non_claims": list(section["non_claims"]),
    }


def _direct_payload() -> dict[str, object]:
    brief = _build_default_brief()
    return {
        "brief_type": brief.brief_type,
        "status": brief.status,
        "authority": brief.authority,
        "capital_authority": brief.capital_authority,
        "brief_id": brief.brief_id,
        "title": brief.title,
        "summary": brief.summary,
        "sections": brief.sections,
        "limitations": brief.limitations,
        "non_claims": brief.non_claims,
    }


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
