from __future__ import annotations

import ast
import json
import re
from dataclasses import fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.candidate_research_brief import (
    CandidateResearchBrief,
    build_candidate_research_brief,
)
from algotrader.research.candidate_research_brief_section import (
    CandidateResearchBriefSection,
)
from tests.fixtures.candidate_research_brief_section import (
    build_synthetic_candidate_research_brief_section,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


MODULE_PATH = Path("src/algotrader/research/candidate_research_brief.py")

_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.candidate_research_brief_section",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    _s("algotrader.", "persist", "ence"),
    _s("algotrader.", "port", "folio"),
    "algotrader.risk",
    _s("algotrader.", "run", "time"),
    "algotrader.scheduler",
    "algotrader.screener",
    _s("algotrader.", "sig", "nals"),
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    "anthropic",
    _s("data", "base"),
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    _s("mas", "sive"),
    _s("net", "work"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    "pathlib",
    _s("poly", "gon"),
    _s("poly", "gon_a", "pi_client"),
    _s("quant", "connect"),
    _s("re", "quests"),
    _s("so", "cket"),
    "sqlmodel",
    "urllib",
    "vectorbt",
    _s("y", "finance"),
)

_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "client",
    _s("con", "nect"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "exists",
    "getenv",
    "glob",
    "import_module",
    "importlib.import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "parse",
    "Path",
    _s("persist"),
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    _s("re", "quest"),
    _s("re", "quests.get"),
    "rglob",
    _s("so", "cket.socket"),
    "stat",
    _s("submit_", "or", "der"),
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}

_REQUIRED_NON_CLAIMS = (
    _not("source approval"),
    _not("data approval"),
    _not("endpoint approval"),
    _not("universe approval"),
    _not("bench", "mark approval"),
    _not("ca", "sh proxy approval"),
    _not("methodology approval"),
    _not("evidence approval"),
    _not("return-construction approval"),
    _not("no-lookahead approval"),
    _not("stra", "tegy validation"),
    _not("tra", "ding readiness"),
    _not("production use"),
    _not("bro", "ker or run", "time use"),
    _not("or", "der generation"),
    _not("port", "folio or allo", "cation authority"),
)


def test_builds_brief_from_phase_137_synthetic_section_fixture() -> None:
    section = build_synthetic_candidate_research_brief_section()

    brief = build_candidate_research_brief((section,))

    assert isinstance(brief, CandidateResearchBrief)
    assert brief.sections == (section,)
    assert isinstance(brief.sections[0], CandidateResearchBriefSection)


def test_builder_preserves_section_identity_and_input_order() -> None:
    first = _section_variant("Candidate research results metadata one")
    second = _section_variant("Candidate research results metadata two")

    brief = build_candidate_research_brief((first, second))

    assert brief.sections[0] is first
    assert brief.sections[1] is second
    assert tuple(section.title for section in brief.sections) == (
        first.title,
        second.title,
    )
    assert [
        section_payload["title"] for section_payload in brief.to_dict()["sections"]
    ] == [
        first.title,
        second.title,
    ]


def test_brief_type_status_title_limitations_and_non_claims_are_deterministic() -> None:
    first = build_candidate_research_brief(
        (build_synthetic_candidate_research_brief_section(),)
    )
    second = build_candidate_research_brief(
        (build_synthetic_candidate_research_brief_section(),)
    )

    assert first.brief_type == second.brief_type == "candidate_research_brief"
    assert first.status == second.status == "candidate_only"
    assert first.title == second.title == "Candidate research brief metadata"
    assert _is_clean_string(first.title)
    _assert_non_actionable((first.title,))
    assert first.limitations == second.limitations
    assert first.non_claims == second.non_claims
    assert first.limitations
    assert first.non_claims


def test_limitations_non_claims_and_required_non_claims_are_carried_forward() -> None:
    section = build_synthetic_candidate_research_brief_section()
    brief = build_candidate_research_brief((section,))
    payload = brief.to_dict()

    assert all(value in brief.limitations for value in section.limitations)
    assert all(value in brief.non_claims for value in section.non_claims)
    assert payload["limitations"] == list(brief.limitations)
    assert payload["non_claims"] == list(brief.non_claims)
    assert set(_REQUIRED_NON_CLAIMS).issubset(brief.non_claims)
    assert all(value.startswith("not ") for value in brief.non_claims)


def test_direct_construction_accepts_valid_brief_payload() -> None:
    payload = _valid_constructor_payload()

    brief = CandidateResearchBrief(**payload)

    assert brief.brief_type == "candidate_research_brief"
    assert brief.status == "candidate_only"
    assert brief.sections == payload["sections"]


def test_builder_and_direct_construction_reject_empty_sections() -> None:
    with pytest.raises(ValidationError, match="sections"):
        build_candidate_research_brief(())

    payload = _valid_constructor_payload()
    payload["sections"] = ()
    with pytest.raises(ValidationError, match="sections"):
        CandidateResearchBrief(**payload)


@pytest.mark.parametrize("value", (object(), None, "not a brief section"))
def test_direct_construction_rejects_non_section_input(value: object) -> None:
    payload = _valid_constructor_payload()
    payload["sections"] = (value,)

    with pytest.raises(ValidationError, match="CandidateResearchBriefSection"):
        CandidateResearchBrief(**payload)


def test_direct_construction_rejects_mutable_section_collections() -> None:
    section = build_synthetic_candidate_research_brief_section()
    payload = _valid_constructor_payload((section,))
    payload["sections"] = [section]

    with pytest.raises(ValidationError, match="sections"):
        CandidateResearchBrief(**payload)


@pytest.mark.parametrize(
    "brief_type",
    (
        "",
        "candidate_research_results",
        "candidate_research_brief_preview",
        "validated_candidate_research_brief",
    ),
)
def test_direct_construction_rejects_forbidden_brief_types(brief_type: str) -> None:
    payload = _valid_constructor_payload()
    payload["brief_type"] = brief_type

    with pytest.raises(ValidationError, match="brief_type"):
        CandidateResearchBrief(**payload)


@pytest.mark.parametrize(
    "status",
    (
        "",
        "validated",
        "approved",
        "tradable",
        "ready",
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
    ),
)
def test_direct_construction_rejects_approval_like_statuses(status: str) -> None:
    payload = _valid_constructor_payload()
    payload["status"] = status

    with pytest.raises(ValidationError, match="status"):
        CandidateResearchBrief(**payload)


def test_direct_construction_rejects_duplicate_section_identities() -> None:
    section = build_synthetic_candidate_research_brief_section()
    payload = _valid_constructor_payload((section,))
    payload["sections"] = (section, section)

    with pytest.raises(ValidationError, match="duplicate"):
        CandidateResearchBrief(**payload)


@pytest.mark.parametrize("title", ("", " ", " title", "title ", None, 3))
def test_direct_construction_rejects_empty_or_malformed_title(title: object) -> None:
    payload = _valid_constructor_payload()
    payload["title"] = title

    with pytest.raises(ValidationError, match="title"):
        CandidateResearchBrief(**payload)


def test_direct_construction_rejects_empty_or_malformed_limitations() -> None:
    section = build_synthetic_candidate_research_brief_section()

    for limitations in (
        (),
        list(section.limitations),
        "limitation",
        ("valid", ""),
        ("valid", " "),
        ("valid", " trailing "),
        ("valid", 1),
        ("metadata-only brief for existing candidate research brief sections",),
        None,
    ):
        payload = _valid_constructor_payload((section,))
        payload["limitations"] = limitations
        with pytest.raises(ValidationError, match="limitations"):
            CandidateResearchBrief(**payload)


def test_direct_construction_rejects_empty_or_malformed_non_claims() -> None:
    section = build_synthetic_candidate_research_brief_section()

    for non_claims in (
        (),
        list(section.non_claims),
        "non-claim",
        ("not valid", ""),
        ("not valid", " "),
        ("not valid", " trailing "),
        ("not valid", 1),
        section.non_claims[:-1],
        section.non_claims + ("positive candidate claim",),
        None,
    ):
        payload = _valid_constructor_payload((section,))
        payload["non_claims"] = non_claims
        with pytest.raises(ValidationError, match="non_claims|negative"):
            CandidateResearchBrief(**payload)


def test_to_dict_is_primitive_only_deterministic_and_does_not_alias_lists() -> None:
    section = build_synthetic_candidate_research_brief_section()
    brief = build_candidate_research_brief((section,))

    payload = brief.to_dict()

    assert not hasattr(CandidateResearchBrief, "from_dict")
    assert payload == brief.to_dict()
    assert payload == {
        "brief_type": "candidate_research_brief",
        "status": "candidate_only",
        "title": brief.title,
        "section_count": 1,
        "sections": [section.to_dict()],
        "limitations": list(brief.limitations),
        "non_claims": list(brief.non_claims),
    }
    _assert_primitive_only(payload)
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload

    payload["sections"].append(section.to_dict())
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("mutated primitive copy")

    assert brief.to_dict()["sections"] == [section.to_dict()]
    assert brief.to_dict()["limitations"] == list(brief.limitations)
    assert brief.to_dict()["non_claims"] == list(brief.non_claims)


def test_repeated_builder_calls_are_deterministic() -> None:
    section = build_synthetic_candidate_research_brief_section()

    first = build_candidate_research_brief((section,))
    second = build_candidate_research_brief((section,))
    third = build_candidate_research_brief(
        (build_synthetic_candidate_research_brief_section(),)
    )

    assert first is not second
    assert first.sections[0] is second.sections[0] is section
    assert first.to_dict() == second.to_dict() == third.to_dict()
    assert _sorted_compact_json(first.to_dict()) == _sorted_compact_json(
        second.to_dict()
    )


def test_builder_and_serialization_do_not_mutate_sections_or_nested_payloads() -> None:
    section = build_synthetic_candidate_research_brief_section()
    section_payload = section.to_dict()
    item_payload = section.items[0].to_dict()
    identity_snapshot = (
        id(section),
        id(section.items),
        id(section.items[0]),
        id(section.items[0].dossier),
        id(section.limitations),
        id(section.non_claims),
    )

    brief = build_candidate_research_brief((section,))
    brief_payload = brief.to_dict()
    brief_payload["sections"].append(section.to_dict())
    brief_payload["limitations"].append("mutated primitive copy")
    brief_payload["non_claims"].append("mutated primitive copy")

    assert section.to_dict() == section_payload
    assert section.items[0].to_dict() == item_payload
    assert (
        id(section),
        id(section.items),
        id(section.items[0]),
        id(section.items[0].dossier),
        id(section.limitations),
        id(section.non_claims),
    ) == identity_snapshot


def test_brief_introduces_no_disallowed_fields() -> None:
    brief = build_candidate_research_brief(
        (build_synthetic_candidate_research_brief_section(),)
    )
    payload = brief.to_dict()
    forbidden_fields = _forbidden_payload_fields()

    assert tuple(field.name for field in fields(CandidateResearchBrief)) == (
        "brief_type",
        "status",
        "title",
        "sections",
        "limitations",
        "non_claims",
    )
    assert tuple(payload) == (
        "brief_type",
        "status",
        "title",
        "section_count",
        "sections",
        "limitations",
        "non_claims",
    )
    assert _payload_keys(payload).isdisjoint(forbidden_fields)
    assert all(not hasattr(brief, field_name) for field_name in forbidden_fields)


def test_module_imports_no_forbidden_vendor_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_persistence_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_text_has_no_real_world_path_secret_or_trading_literals() -> None:
    source = _source_text()
    lowered = source.lower()
    upper_source = source.upper()

    for code_points in _real_symbol_codes():
        symbol = "".join(chr(code_point) for code_point in code_points)
        assert re.search(rf"(?<![A-Z0-9]){symbol}(?![A-Z0-9])", upper_source) is None
    for term in _vendor_or_provider_terms():
        assert term not in lowered
    for term in _credential_terms():
        assert term not in lowered
    for marker in _path_or_data_source_markers():
        assert marker not in lowered
    for word in _forbidden_source_words():
        assert re.search(rf"(?<![a-z0-9_]){word}(?![a-z0-9_])", lowered) is None


def _section_variant(title: str) -> CandidateResearchBriefSection:
    section = build_synthetic_candidate_research_brief_section()
    return CandidateResearchBriefSection(
        section_type=section.section_type,
        status=section.status,
        title=title,
        items=section.items,
        limitations=section.limitations,
        non_claims=section.non_claims,
    )


def _valid_constructor_payload(
    sections: tuple[CandidateResearchBriefSection, ...] | None = None,
) -> dict[str, object]:
    checked_sections = sections or (build_synthetic_candidate_research_brief_section(),)
    brief = build_candidate_research_brief(checked_sections)
    return {
        "brief_type": brief.brief_type,
        "status": brief.status,
        "title": brief.title,
        "sections": brief.sections,
        "limitations": brief.limitations,
        "non_claims": brief.non_claims,
    }


def _is_clean_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _assert_non_actionable(values: tuple[str, ...]) -> None:
    lowered_values = tuple(value.lower() for value in values)

    for term in _actionable_terms():
        assert all(
            re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", value) is None
            for value in lowered_values
        )


def _actionable_terms() -> tuple[str, ...]:
    return (
        _s("action"),
        _s("actions"),
        _s("approval"),
        _s("approved"),
        "buy",
        "enter",
        "exit",
        "hold",
        _s("or", "der"),
        _s("recommend"),
        _s("recommendation"),
        _s("sell"),
        _s("size"),
        "tradable",
        _s("tra", "de"),
        _s("tra", "ding"),
        "validated",
    )


def _sorted_compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _assert_primitive_only(value: object) -> None:
    assert not isinstance(value, (tuple, set))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_only(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_primitive_only(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


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


def _forbidden_payload_fields() -> set[str]:
    return {
        "account",
        _s("action"),
        _s("actions"),
        _s("approval"),
        _s("approved"),
        _s("bench", "mark"),
        _s("bench", "marks"),
        _s("bro", "ker"),
        _s("bro", "kers"),
        _s("ca", "sh"),
        _s("ca", "sh_return"),
        _s("ca", "sh_returns"),
        _s("co", "st"),
        _s("co", "sts"),
        "evaluator",
        "evaluators",
        _s("fi", "ll"),
        _s("fi", "lls"),
        "live_authorized",
        "live_probe_eligible",
        _s("or", "der"),
        _s("or", "ders"),
        "paper_eligible",
        _s("port", "folio"),
        _s("port", "folios"),
        _s("allo", "cation"),
        _s("allo", "cations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        "priority",
        "prioritized",
        "rank",
        "ranking",
        _s("recommendation"),
        _s("recommendations"),
        "ready",
        _s("run", "time"),
        _s("run", "times"),
        "score",
        "scoring",
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("stra", "tegy_state"),
        "tradable",
        _s("tra", "de"),
        _s("tra", "des"),
        _s("tra", "ding_readiness"),
        "validated",
    }


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            elif node.level > 0:
                imports.add("__future__")

    return imports


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


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


def _real_symbol_codes() -> tuple[tuple[int, ...], ...]:
    return (
        (83, 80, 89),
        (73, 86, 86),
        (86, 79, 79),
        (81, 81, 81),
        (86, 84, 73),
        (73, 87, 77),
        (68, 73, 65),
        (65, 71, 71),
        (66, 78, 68),
        (84, 76, 84),
        (71, 76, 68),
        (69, 70, 65),
        (69, 69, 77),
        (88, 76, 75),
        (88, 76, 70),
        (88, 76, 69),
        (88, 76, 86),
        (88, 76, 85),
        (88, 76, 73),
        (88, 76, 89),
        (88, 76, 80),
        (88, 76, 82, 69),
    )


def _vendor_or_provider_terms() -> set[str]:
    return {
        _s("al", "paca"),
        "alpha vantage",
        "bloomberg",
        "factset",
        "finnhub",
        "fred",
        _s("interactive ", "bro", "kers"),
        _s("mas", "sive"),
        "morningstar",
        "nasdaq",
        _s("poly", "gon"),
        _s("quant", "connect"),
        "quandl",
        "refinitiv",
        "stooq",
        "tiingo",
        "yahoo",
        _s("y", "finance"),
    }


def _credential_terms() -> set[str]:
    return {
        _s("a", "pi_key"),
        _s("a", "pikey"),
        "bearer",
        _s("client_", "sec", "ret"),
        "credential",
        "oauth",
        "password",
        _s("private_key"),
        _s("sec", "ret"),
        "token",
    }


def _path_or_data_source_markers() -> set[str]:
    return {
        _s(":", chr(47), chr(47)),
        "http:",
        "https:",
        "www.",
        ".com",
        _s(".data"),
        ".csv",
        ".jsonl",
        ".parquet",
        ".zip",
        chr(47),
        chr(92),
    }


def _forbidden_source_words() -> set[str]:
    return {
        _s("bench", "mark"),
        _s("bro", "ker"),
        _s("bro", "kers"),
        _s("ca", "sh"),
        _s("co", "st"),
        _s("co", "sts"),
        _s("fi", "ll"),
        _s("fi", "lls"),
        _s("or", "der"),
        _s("or", "ders"),
        _s("port", "folio"),
        _s("port", "folios"),
        _s("allo", "cation"),
        _s("allo", "cations"),
        _s("recommendation"),
        _s("recommendations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        "rank",
        "ranking",
        _s("run", "time"),
        "score",
        "scoring",
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("tra", "ding"),
        _s("tra", "de"),
        _s("tra", "des"),
    }
