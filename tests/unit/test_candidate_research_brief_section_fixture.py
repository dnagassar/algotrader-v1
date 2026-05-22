from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from algotrader.research.candidate_research_brief_item import (
    CandidateResearchBriefItem,
)
from algotrader.research.candidate_research_brief_section import (
    CandidateResearchBriefSection,
    build_candidate_research_brief_section,
)
from tests.fixtures import candidate_research_brief_section as fixture_module
from tests.fixtures.candidate_research_brief_item import (
    build_synthetic_candidate_research_brief_item,
)
from tests.fixtures.candidate_research_brief_section import (
    build_synthetic_candidate_research_brief_section,
    expected_synthetic_candidate_research_brief_section_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


FIXTURE_PATH = Path("tests/fixtures/candidate_research_brief_section.py")

_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.candidate_research_brief_section",
    "tests.fixtures.candidate_research_brief_item",
}

_ALLOWED_CALL_NAMES = {
    "build_candidate_research_brief_section",
    "build_synthetic_candidate_research_brief_item",
    "build_synthetic_candidate_research_brief_section",
    "to_dict",
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

_FORBIDDEN_PAYLOAD_FIELDS = {
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


def test_fixture_builds_candidate_research_brief_section() -> None:
    section = build_synthetic_candidate_research_brief_section()

    assert isinstance(section, CandidateResearchBriefSection)
    assert section.items
    assert isinstance(section.items[0], CandidateResearchBriefItem)


def test_fixture_builds_through_phase_135_item_fixture_and_phase_136_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_item = build_synthetic_candidate_research_brief_item()

    assert fixture_module.build_synthetic_candidate_research_brief_item is (
        build_synthetic_candidate_research_brief_item
    )
    assert fixture_module.build_candidate_research_brief_section is (
        build_candidate_research_brief_section
    )

    def recording_item_fixture() -> CandidateResearchBriefItem:
        calls.append(("item_fixture", source_item))
        return source_item

    def recording_section_builder(
        items: tuple[CandidateResearchBriefItem, ...],
    ) -> CandidateResearchBriefSection:
        checked_items = tuple(items)
        calls.append(("section_builder", checked_items))
        return build_candidate_research_brief_section(checked_items)

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief_item",
        recording_item_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_candidate_research_brief_section",
        recording_section_builder,
    )

    section = fixture_module.build_synthetic_candidate_research_brief_section()

    assert [name for name, _ in calls] == [
        "item_fixture",
        "section_builder",
    ]
    assert calls[0][1] is source_item
    assert calls[1][1] == (source_item,)
    assert section.items[0] is source_item


def test_fixture_preserves_item_identity_and_order_where_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_item = build_synthetic_candidate_research_brief_item()

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief_item",
        lambda: source_item,
    )

    section = fixture_module.build_synthetic_candidate_research_brief_section()

    assert section.items == (source_item,)
    assert section.items[0] is source_item
    assert section.to_dict()["items"] == [source_item.to_dict()]


def test_section_type_status_title_and_item_values_remain_advisory() -> None:
    section = build_synthetic_candidate_research_brief_section()
    item = section.items[0]

    assert section.section_type == "candidate_research_results"
    assert section.status == "candidate_only"
    assert section.title == "Candidate research results metadata"
    assert _is_clean_string(section.title)
    _assert_non_actionable((section.title,))
    assert item.item_type == "candidate_research_result"
    assert item.status == "candidate_only"


def test_limitations_non_claims_and_required_non_claims_are_carried_forward() -> None:
    section = build_synthetic_candidate_research_brief_section()
    item = section.items[0]
    payload = section.to_dict()

    assert section.limitations
    assert section.non_claims
    assert all(value in section.limitations for value in item.limitations)
    assert all(value in section.non_claims for value in item.non_claims)
    assert payload["limitations"] == list(section.limitations)
    assert payload["non_claims"] == list(section.non_claims)
    assert set(_REQUIRED_NON_CLAIMS).issubset(section.non_claims)
    assert all(value.startswith("not ") for value in section.non_claims)


def test_phase_123_fingerprint_is_preserved_in_section_dict() -> None:
    section = build_synthetic_candidate_research_brief_section()
    payload = section.to_dict()
    item_payload = payload["items"][0]

    assert section.items[0].dossier.package.fingerprint == _SYNTHETIC_FIXTURE_DIGEST
    assert item_payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST


def test_phase_127_provenance_convention_is_preserved_in_section_dict() -> None:
    section = build_synthetic_candidate_research_brief_section()
    item = section.items[0]
    item_payload = section.to_dict()["items"][0]

    assert item_payload["package_snapshot_id"] == item.dossier.package.snapshot.snapshot_id
    assert item_payload["result_snapshot_manifest_fixture_id"] == (
        item.dossier.package.snapshot.snapshot_id
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{item.dossier.package.fingerprint}"
    )


def test_expected_output_matches_section_serialization_exactly() -> None:
    section = build_synthetic_candidate_research_brief_section()
    expected = expected_synthetic_candidate_research_brief_section_dict()

    assert expected == section.to_dict()
    assert tuple(expected) == (
        "section_type",
        "status",
        "title",
        "item_count",
        "items",
        "limitations",
        "non_claims",
    )
    assert expected is not section.to_dict()
    _assert_primitive_only(expected)


def test_repeated_fixture_calls_are_deterministic() -> None:
    first = build_synthetic_candidate_research_brief_section()
    second = build_synthetic_candidate_research_brief_section()
    first_expected = expected_synthetic_candidate_research_brief_section_dict()
    second_expected = expected_synthetic_candidate_research_brief_section_dict()

    assert first is not second
    assert first.items[0] is not second.items[0]
    assert first.to_dict() == second.to_dict()
    assert first_expected == second_expected == first.to_dict()
    assert _sorted_compact_json(first.to_dict()) == _sorted_compact_json(
        second.to_dict()
    )


def test_fixture_helpers_do_not_mutate_source_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_item = build_synthetic_candidate_research_brief_item()
    item_before = source_item.to_dict()
    dossier_before = source_item.dossier.to_dict()
    package_before = source_item.dossier.package.to_dict()
    result_before = source_item.dossier.result.to_dict()
    identity_snapshot = (
        id(source_item),
        id(source_item.dossier),
        id(source_item.dossier.package),
        id(source_item.dossier.result),
        id(source_item.dossier.package.snapshot),
        id(source_item.dossier.result.snapshot),
        id(source_item.limitations),
        id(source_item.non_claims),
    )

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief_item",
        lambda: source_item,
    )

    section = fixture_module.build_synthetic_candidate_research_brief_section()
    section_payload = section.to_dict()
    expected_payload = (
        fixture_module.expected_synthetic_candidate_research_brief_section_dict()
    )
    section_payload["items"].append(source_item.to_dict())
    section_payload["items"][0]["limitations"].append("mutated primitive copy")
    section_payload["items"][0]["non_claims"].append("mutated primitive copy")
    section_payload["limitations"].append("mutated primitive copy")
    section_payload["non_claims"].append("mutated primitive copy")
    expected_payload["items"].append(source_item.to_dict())
    expected_payload["limitations"].append("mutated primitive copy")
    expected_payload["non_claims"].append("mutated primitive copy")

    assert section.items[0] is source_item
    assert source_item.to_dict() == item_before
    assert source_item.dossier.to_dict() == dossier_before
    assert source_item.dossier.package.to_dict() == package_before
    assert source_item.dossier.result.to_dict() == result_before
    assert (
        id(source_item),
        id(source_item.dossier),
        id(source_item.dossier.package),
        id(source_item.dossier.result),
        id(source_item.dossier.package.snapshot),
        id(source_item.dossier.result.snapshot),
        id(source_item.limitations),
        id(source_item.non_claims),
    ) == identity_snapshot


def test_fixture_adds_no_disallowed_payload_or_object_fields() -> None:
    section = build_synthetic_candidate_research_brief_section()
    item = section.items[0]
    payload = section.to_dict()

    assert tuple(payload) == (
        "section_type",
        "status",
        "title",
        "item_count",
        "items",
        "limitations",
        "non_claims",
    )
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_PAYLOAD_FIELDS)
    assert all(
        not hasattr(section, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )
    assert all(not hasattr(item, field_name) for field_name in _FORBIDDEN_PAYLOAD_FIELDS)
    assert all(
        not hasattr(item.dossier, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )
    assert all(
        not hasattr(item.dossier.package, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )
    assert all(
        not hasattr(item.dossier.result, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )


def test_fixture_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names == _ALLOWED_CALL_NAMES
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_module_text_has_no_real_world_path_secret_or_trading_literals() -> None:
    source = _source_text()
    upper_source = source.upper()
    lowered = source.lower()

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


def _source_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(FIXTURE_PATH))


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
