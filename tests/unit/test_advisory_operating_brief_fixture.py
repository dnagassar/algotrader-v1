from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from algotrader.research.advisory_operating_brief import (
    AdvisoryOperatingBrief,
    build_advisory_operating_brief,
)
from algotrader.research.candidate_research_brief import CandidateResearchBrief
from algotrader.research.candidate_research_brief_item import (
    CandidateResearchBriefItem,
)
from algotrader.research.candidate_research_brief_section import (
    CandidateResearchBriefSection,
)
from tests.fixtures import advisory_operating_brief as fixture_module
from tests.fixtures.advisory_operating_brief import (
    build_synthetic_advisory_operating_brief,
    expected_synthetic_advisory_operating_brief_dict,
)
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


FIXTURE_PATH = Path("tests/fixtures/advisory_operating_brief.py")

_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.advisory_operating_brief",
    "tests.fixtures.candidate_research_brief",
}

_ALLOWED_CALL_NAMES = {
    "build_advisory_operating_brief",
    "build_synthetic_advisory_operating_brief",
    "build_synthetic_candidate_research_brief",
    "to_dict",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
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
    "http",
    "httpx",
    "ipynb",
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
    "subprocess",
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


def test_fixture_builds_advisory_operating_brief() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    assert isinstance(operating_brief, AdvisoryOperatingBrief)
    assert operating_brief.candidate_research_briefs
    assert isinstance(
        operating_brief.candidate_research_briefs[0],
        CandidateResearchBrief,
    )


def test_fixture_builds_through_phase_139_fixture_and_phase_142_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_brief = build_synthetic_candidate_research_brief()

    assert fixture_module.build_synthetic_candidate_research_brief is (
        build_synthetic_candidate_research_brief
    )
    assert fixture_module.build_advisory_operating_brief is (
        build_advisory_operating_brief
    )

    def recording_candidate_fixture() -> CandidateResearchBrief:
        calls.append(("candidate_fixture", source_brief))
        return source_brief

    def recording_operating_builder(
        candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    ) -> AdvisoryOperatingBrief:
        checked_briefs = tuple(candidate_research_briefs)
        calls.append(("operating_builder", checked_briefs))
        return build_advisory_operating_brief(checked_briefs)

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief",
        recording_candidate_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_advisory_operating_brief",
        recording_operating_builder,
    )

    operating_brief = fixture_module.build_synthetic_advisory_operating_brief()

    assert [name for name, _ in calls] == [
        "candidate_fixture",
        "operating_builder",
    ]
    assert calls[0][1] is source_brief
    assert calls[1][1] == (source_brief,)
    assert operating_brief.candidate_research_briefs[0] is source_brief


def test_fixture_preserves_candidate_brief_identity_and_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_brief = build_synthetic_candidate_research_brief()

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief",
        lambda: source_brief,
    )

    operating_brief = fixture_module.build_synthetic_advisory_operating_brief()

    assert operating_brief.candidate_research_briefs == (source_brief,)
    assert operating_brief.candidate_research_briefs[0] is source_brief
    assert operating_brief.to_dict()["candidate_research_briefs"] == [
        source_brief.to_dict()
    ]


def test_operating_type_status_title_and_nested_advisory_values_are_fixed() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    candidate_brief = operating_brief.candidate_research_briefs[0]
    section = candidate_brief.sections[0]
    item = section.items[0]

    assert operating_brief.operating_brief_type == "advisory_operating_brief"
    assert operating_brief.status == "candidate_only"
    assert operating_brief.title == "Candidate research operating brief metadata"
    assert _is_clean_string(operating_brief.title)
    _assert_non_actionable((operating_brief.title,))
    assert candidate_brief.brief_type == "candidate_research_brief"
    assert candidate_brief.status == "candidate_only"
    assert section.section_type == "candidate_research_results"
    assert section.status == "candidate_only"
    assert item.item_type == "candidate_research_result"
    assert item.status == "candidate_only"
    assert isinstance(section, CandidateResearchBriefSection)
    assert isinstance(item, CandidateResearchBriefItem)


def test_limitations_non_claims_and_required_non_claims_are_carried_forward() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    candidate_brief = operating_brief.candidate_research_briefs[0]
    payload = operating_brief.to_dict()

    assert operating_brief.limitations
    assert operating_brief.non_claims
    assert all(
        value in operating_brief.limitations
        for value in candidate_brief.limitations
    )
    assert all(value in operating_brief.non_claims for value in candidate_brief.non_claims)
    assert payload["limitations"] == list(operating_brief.limitations)
    assert payload["non_claims"] == list(operating_brief.non_claims)
    assert set(_REQUIRED_NON_CLAIMS).issubset(operating_brief.non_claims)
    assert all(value.startswith("not ") for value in operating_brief.non_claims)


def test_phase_123_fingerprint_is_preserved_in_nested_payloads() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    item = operating_brief.candidate_research_briefs[0].sections[0].items[0]
    item_payload = _single_item_payload(operating_brief.to_dict())

    assert item.dossier.package.fingerprint == _SYNTHETIC_FIXTURE_DIGEST
    assert item_payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST


def test_phase_127_141_provenance_convention_is_preserved_in_nested_payloads() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    item = operating_brief.candidate_research_briefs[0].sections[0].items[0]
    item_payload = _single_item_payload(operating_brief.to_dict())

    assert item_payload["package_snapshot_id"] == item.dossier.package.snapshot.snapshot_id
    assert item_payload["result_snapshot_manifest_fixture_id"] == (
        item.dossier.package.snapshot.snapshot_id
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{item.dossier.package.fingerprint}"
    )


def test_expected_output_matches_operating_brief_serialization_exactly() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    expected = expected_synthetic_advisory_operating_brief_dict()

    assert expected == operating_brief.to_dict()
    assert tuple(expected) == (
        "operating_brief_type",
        "status",
        "title",
        "candidate_research_brief_count",
        "candidate_research_briefs",
        "limitations",
        "non_claims",
    )
    assert expected is not operating_brief.to_dict()
    _assert_primitive_only(expected)


def test_repeated_fixture_calls_are_deterministic() -> None:
    first = build_synthetic_advisory_operating_brief()
    second = build_synthetic_advisory_operating_brief()
    first_expected = expected_synthetic_advisory_operating_brief_dict()
    second_expected = expected_synthetic_advisory_operating_brief_dict()

    assert first is not second
    assert first.candidate_research_briefs[0] is not second.candidate_research_briefs[0]
    assert first.to_dict() == second.to_dict()
    assert first_expected == second_expected == first.to_dict()
    assert _sorted_compact_json(first.to_dict()) == _sorted_compact_json(
        second.to_dict()
    )


def test_fixture_helpers_do_not_mutate_source_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_brief = build_synthetic_candidate_research_brief()
    source_section = source_brief.sections[0]
    source_item = source_section.items[0]
    brief_before = source_brief.to_dict()
    section_before = source_section.to_dict()
    item_before = source_item.to_dict()
    dossier_before = source_item.dossier.to_dict()
    package_before = source_item.dossier.package.to_dict()
    result_before = source_item.dossier.result.to_dict()
    identity_snapshot = (
        id(source_brief),
        id(source_brief.sections),
        id(source_section),
        id(source_section.items),
        id(source_item),
        id(source_item.dossier),
        id(source_item.dossier.package),
        id(source_item.dossier.result),
        id(source_item.dossier.package.snapshot),
        id(source_item.dossier.result.snapshot),
        id(source_brief.limitations),
        id(source_brief.non_claims),
    )

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief",
        lambda: source_brief,
    )

    operating_brief = fixture_module.build_synthetic_advisory_operating_brief()
    operating_payload = operating_brief.to_dict()
    expected_payload = fixture_module.expected_synthetic_advisory_operating_brief_dict()
    operating_payload["candidate_research_briefs"].append(source_brief.to_dict())
    operating_payload["limitations"].append("mutated primitive copy")
    operating_payload["non_claims"].append("mutated primitive copy")
    expected_payload["candidate_research_briefs"].append(source_brief.to_dict())
    expected_payload["limitations"].append("mutated primitive copy")
    expected_payload["non_claims"].append("mutated primitive copy")

    assert operating_brief.candidate_research_briefs[0] is source_brief
    assert source_brief.to_dict() == brief_before
    assert source_section.to_dict() == section_before
    assert source_item.to_dict() == item_before
    assert source_item.dossier.to_dict() == dossier_before
    assert source_item.dossier.package.to_dict() == package_before
    assert source_item.dossier.result.to_dict() == result_before
    assert (
        id(source_brief),
        id(source_brief.sections),
        id(source_section),
        id(source_section.items),
        id(source_item),
        id(source_item.dossier),
        id(source_item.dossier.package),
        id(source_item.dossier.result),
        id(source_item.dossier.package.snapshot),
        id(source_item.dossier.result.snapshot),
        id(source_brief.limitations),
        id(source_brief.non_claims),
    ) == identity_snapshot


def test_fixture_adds_no_disallowed_payload_or_object_fields() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    candidate_brief = operating_brief.candidate_research_briefs[0]
    section = candidate_brief.sections[0]
    item = section.items[0]
    payload = operating_brief.to_dict()

    assert tuple(payload) == (
        "operating_brief_type",
        "status",
        "title",
        "candidate_research_brief_count",
        "candidate_research_briefs",
        "limitations",
        "non_claims",
    )
    assert _payload_keys(payload).isdisjoint(_forbidden_payload_fields())
    for value in (
        operating_brief,
        candidate_brief,
        section,
        item,
        item.dossier,
        item.dossier.package,
        item.dossier.result,
    ):
        assert all(
            not hasattr(value, field_name)
            for field_name in _forbidden_payload_fields()
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


def _single_candidate_brief_payload(payload: dict[str, object]) -> dict[str, object]:
    candidate_briefs = payload["candidate_research_briefs"]
    assert isinstance(candidate_briefs, list)
    assert len(candidate_briefs) == 1
    candidate_brief = candidate_briefs[0]
    assert isinstance(candidate_brief, dict)
    return candidate_brief


def _single_section_payload(payload: dict[str, object]) -> dict[str, object]:
    candidate_brief = _single_candidate_brief_payload(payload)
    sections = candidate_brief["sections"]
    assert isinstance(sections, list)
    assert len(sections) == 1
    section = sections[0]
    assert isinstance(section, dict)
    return section


def _single_item_payload(payload: dict[str, object]) -> dict[str, object]:
    section = _single_section_payload(payload)
    items = section["items"]
    assert isinstance(items, list)
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, dict)
    return item


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
        "sell",
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
        _s("bench", "marks"),
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
        _s("recommend"),
        _s("recommendation"),
        _s("recommendations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        "prioritize",
        "prioritized",
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
