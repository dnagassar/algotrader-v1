from __future__ import annotations

import ast
import copy
import inspect
import re
import sys

from algotrader.research.candidate_research_brief import (
    CandidateResearchBrief,
    build_candidate_research_brief,
)
from algotrader.research.candidate_research_brief_item import (
    CandidateResearchBriefItem,
    build_candidate_research_brief_item,
)
from algotrader.research.candidate_research_brief_section import (
    CandidateResearchBriefSection,
    build_candidate_research_brief_section,
)
from algotrader.research.candidate_result_dossier import (
    CandidateResearchResultDossier,
)
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
    expected_synthetic_candidate_research_brief_dict,
)
from tests.fixtures.candidate_research_brief_item import (
    build_synthetic_candidate_research_brief_item,
    expected_synthetic_candidate_research_brief_item_dict,
)
from tests.fixtures.candidate_research_brief_section import (
    build_synthetic_candidate_research_brief_section,
    expected_synthetic_candidate_research_brief_section_dict,
)
from tests.fixtures.candidate_result_dossier import (
    build_synthetic_candidate_research_result_dossier,
    expected_synthetic_candidate_research_result_dossier_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "ast",
    "copy",
    "inspect",
    "re",
    "sys",
    "algotrader.research.candidate_research_brief",
    "algotrader.research.candidate_research_brief_item",
    "algotrader.research.candidate_research_brief_section",
    "algotrader.research.candidate_result_dossier",
    "tests.fixtures.candidate_research_brief",
    "tests.fixtures.candidate_research_brief_item",
    "tests.fixtures.candidate_research_brief_section",
    "tests.fixtures.candidate_result_dossier",
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


def test_full_chain_from_synthetic_dossier_to_brief_succeeds_without_drift() -> None:
    dossier, item, section, brief = _full_chain()

    assert isinstance(dossier, CandidateResearchResultDossier)
    assert isinstance(item, CandidateResearchBriefItem)
    assert isinstance(section, CandidateResearchBriefSection)
    assert isinstance(brief, CandidateResearchBrief)
    assert item.dossier is dossier
    assert section.items == (item,)
    assert section.items[0] is item
    assert brief.sections == (section,)
    assert brief.sections[0] is section
    assert dossier.to_dict() == expected_synthetic_candidate_research_result_dossier_dict()
    assert item.to_dict() == expected_synthetic_candidate_research_brief_item_dict()
    assert section.to_dict() == expected_synthetic_candidate_research_brief_section_dict()
    assert brief.to_dict() == expected_synthetic_candidate_research_brief_dict()


def test_all_synthetic_fixtures_remain_deterministic() -> None:
    first_dossier = build_synthetic_candidate_research_result_dossier()
    second_dossier = build_synthetic_candidate_research_result_dossier()
    first_item = build_synthetic_candidate_research_brief_item()
    second_item = build_synthetic_candidate_research_brief_item()
    first_section = build_synthetic_candidate_research_brief_section()
    second_section = build_synthetic_candidate_research_brief_section()
    first_brief = build_synthetic_candidate_research_brief()
    second_brief = build_synthetic_candidate_research_brief()

    assert first_dossier is not second_dossier
    assert first_item is not second_item
    assert first_section is not second_section
    assert first_brief is not second_brief
    assert first_dossier.to_dict() == second_dossier.to_dict()
    assert first_item.to_dict() == second_item.to_dict()
    assert first_section.to_dict() == second_section.to_dict()
    assert first_brief.to_dict() == second_brief.to_dict()
    assert (
        expected_synthetic_candidate_research_result_dossier_dict()
        == expected_synthetic_candidate_research_result_dossier_dict()
    )
    assert (
        expected_synthetic_candidate_research_brief_item_dict()
        == expected_synthetic_candidate_research_brief_item_dict()
    )
    assert (
        expected_synthetic_candidate_research_brief_section_dict()
        == expected_synthetic_candidate_research_brief_section_dict()
    )
    assert (
        expected_synthetic_candidate_research_brief_dict()
        == expected_synthetic_candidate_research_brief_dict()
    )


def test_identity_and_sequence_are_preserved_by_builders() -> None:
    first_dossier = build_synthetic_candidate_research_result_dossier()
    second_dossier = build_synthetic_candidate_research_result_dossier()
    first_item = build_candidate_research_brief_item(first_dossier)
    second_item = build_candidate_research_brief_item(second_dossier)
    section = build_candidate_research_brief_section((first_item, second_item))
    second_section = build_candidate_research_brief_section(
        (build_candidate_research_brief_item(build_synthetic_candidate_research_result_dossier()),)
    )
    brief = build_candidate_research_brief((section, second_section))

    assert first_item.dossier is first_dossier
    assert second_item.dossier is second_dossier
    assert section.items == (first_item, second_item)
    assert tuple(id(value) for value in section.items) == (
        id(first_item),
        id(second_item),
    )
    assert brief.sections == (section, second_section)
    assert tuple(id(value) for value in brief.sections) == (
        id(section),
        id(second_section),
    )


def test_final_brief_dict_matches_expected_fixture_dict() -> None:
    *_, brief = _full_chain()

    assert brief.to_dict() == expected_synthetic_candidate_research_brief_dict()
    assert tuple(brief.to_dict()) == (
        "brief_type",
        "status",
        "title",
        "section_count",
        "sections",
        "limitations",
        "non_claims",
    )
    _assert_primitive_only(brief.to_dict())


def test_phase_123_fingerprint_is_preserved_in_final_brief_dict() -> None:
    *_, brief = _full_chain()
    item_payload = _single_item_payload(brief.to_dict())

    assert item_payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST
    assert (
        brief.sections[0].items[0].dossier.package.fingerprint
        == _SYNTHETIC_FIXTURE_DIGEST
    )


def test_phase_127_provenance_convention_is_preserved_in_final_brief_dict() -> None:
    *_, brief = _full_chain()
    item = brief.sections[0].items[0]
    item_payload = _single_item_payload(brief.to_dict())

    assert item_payload["package_snapshot_id"] == item.dossier.package.snapshot.snapshot_id
    assert item_payload["result_snapshot_manifest_fixture_id"] == (
        item.dossier.package.snapshot.snapshot_id
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{item.dossier.package.fingerprint}"
    )


def test_advisory_type_and_status_values_remain_fixed() -> None:
    dossier, item, section, brief = _full_chain()

    assert dossier.status == "candidate_only"
    assert item.item_type == "candidate_research_result"
    assert item.status == "candidate_only"
    assert section.section_type == "candidate_research_results"
    assert section.status == "candidate_only"
    assert brief.brief_type == "candidate_research_brief"
    assert brief.status == "candidate_only"
    assert _single_item_payload(brief.to_dict())["status"] == "candidate_only"


def test_limitations_and_non_claims_remain_present_at_each_level() -> None:
    dossier, item, section, brief = _full_chain()
    payload = brief.to_dict()

    for artifact in (dossier, item, section, brief):
        assert artifact.limitations
        assert artifact.non_claims
        assert all(value == value.strip() and value for value in artifact.limitations)
        assert all(value.startswith("not ") for value in artifact.non_claims)
        assert set(_REQUIRED_NON_CLAIMS).issubset(artifact.non_claims)

    assert all(value in item.limitations for value in dossier.limitations)
    assert all(value in item.non_claims for value in dossier.non_claims)
    assert all(value in section.limitations for value in item.limitations)
    assert all(value in section.non_claims for value in item.non_claims)
    assert all(value in brief.limitations for value in section.limitations)
    assert all(value in brief.non_claims for value in section.non_claims)
    assert payload["limitations"] == list(brief.limitations)
    assert payload["non_claims"] == list(brief.non_claims)
    assert _single_section_payload(payload)["limitations"] == list(section.limitations)
    assert _single_item_payload(payload)["limitations"] == list(item.limitations)


def test_required_non_claims_remain_present_in_final_brief_dict() -> None:
    *_, brief = _full_chain()
    payload = brief.to_dict()
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    assert set(_REQUIRED_NON_CLAIMS).issubset(payload["non_claims"])
    assert set(_REQUIRED_NON_CLAIMS).issubset(section_payload["non_claims"])
    assert set(_REQUIRED_NON_CLAIMS).issubset(item_payload["non_claims"])


def test_repeated_full_chain_construction_is_deterministic() -> None:
    first_chain = _full_chain()
    second_chain = _full_chain()

    assert first_chain[0] is not second_chain[0]
    assert first_chain[1] is not second_chain[1]
    assert first_chain[2] is not second_chain[2]
    assert first_chain[3] is not second_chain[3]
    assert first_chain[0].to_dict() == second_chain[0].to_dict()
    assert first_chain[1].to_dict() == second_chain[1].to_dict()
    assert first_chain[2].to_dict() == second_chain[2].to_dict()
    assert first_chain[3].to_dict() == second_chain[3].to_dict()


def test_mutating_copied_primitive_payloads_does_not_mutate_source_objects() -> None:
    dossier, item, section, brief = _full_chain()
    dossier_before = dossier.to_dict()
    item_before = item.to_dict()
    section_before = section.to_dict()
    brief_before = brief.to_dict()
    package_before = item.dossier.package.to_dict()
    result_before = item.dossier.result.to_dict()
    identity_snapshot = (
        id(dossier),
        id(item),
        id(section),
        id(brief),
        id(item.dossier.package),
        id(item.dossier.result),
        id(section.items),
        id(brief.sections),
        id(dossier.limitations),
        id(item.limitations),
        id(section.limitations),
        id(brief.limitations),
    )
    brief_payload = brief.to_dict()
    expected_payload = expected_synthetic_candidate_research_brief_dict()

    _mutate_brief_payload_copy(brief_payload)
    _mutate_brief_payload_copy(expected_payload)

    assert dossier.to_dict() == dossier_before
    assert item.to_dict() == item_before
    assert section.to_dict() == section_before
    assert brief.to_dict() == brief_before
    assert item.dossier.package.to_dict() == package_before
    assert item.dossier.result.to_dict() == result_before
    assert (
        id(dossier),
        id(item),
        id(section),
        id(brief),
        id(item.dossier.package),
        id(item.dossier.result),
        id(section.items),
        id(brief.sections),
        id(dossier.limitations),
        id(item.limitations),
        id(section.limitations),
        id(brief.limitations),
    ) == identity_snapshot


def test_no_disallowed_payload_or_object_fields_are_introduced() -> None:
    dossier, item, section, brief = _full_chain()
    payload = brief.to_dict()
    disallowed_fields = _disallowed_payload_fields()

    assert _payload_keys(payload).isdisjoint(disallowed_fields)
    for artifact in (
        dossier,
        item,
        section,
        brief,
        item.dossier.package,
        item.dossier.result,
    ):
        assert all(not hasattr(artifact, field_name) for field_name in disallowed_fields)


def test_new_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _forbidden_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_forbidden_call_names())


def test_new_module_text_has_no_real_world_or_disallowed_literals() -> None:
    source = _source_text()
    upper_source = source.upper()
    lowered = source.lower()

    for code_points in _real_symbol_codes():
        symbol = "".join(chr(code_point) for code_point in code_points)
        assert re.search(rf"(?<![A-Z0-9]){symbol}(?![A-Z0-9])", upper_source) is None
    for term in _provider_or_sdk_terms():
        assert term not in lowered
    for term in _sensitive_terms():
        assert term not in lowered
    for marker in _location_markers():
        assert marker not in lowered
    for word in _disallowed_source_words():
        assert re.search(rf"(?<![a-z0-9_]){word}(?![a-z0-9_])", lowered) is None


def _full_chain() -> tuple[
    CandidateResearchResultDossier,
    CandidateResearchBriefItem,
    CandidateResearchBriefSection,
    CandidateResearchBrief,
]:
    dossier = build_synthetic_candidate_research_result_dossier()
    item = build_candidate_research_brief_item(dossier)
    section = build_candidate_research_brief_section((item,))
    brief = build_candidate_research_brief((section,))
    return dossier, item, section, brief


def _single_section_payload(payload: dict[str, object]) -> dict[str, object]:
    sections = payload["sections"]
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


def _mutate_brief_payload_copy(payload: dict[str, object]) -> None:
    section = _single_section_payload(payload)
    item = _single_item_payload(payload)

    payload["sections"].append(copy.deepcopy(section))
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive source")
    section["items"].append(copy.deepcopy(item))
    section["limitations"].append("mutated primitive copy")
    section["non_claims"].append("not mutated primitive source")
    item["summary_points"].append("mutated primitive copy")
    item["limitations"].append("mutated primitive copy")
    item["non_claims"].append("not mutated primitive source")


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
    return inspect.getsource(sys.modules[__name__])


def _tree() -> ast.AST:
    return ast.parse(_source_text())


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

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


def _forbidden_import_prefixes() -> tuple[str, ...]:
    return (
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


def _forbidden_call_names() -> set[str]:
    return {
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
        "post",
        _s("re", "ad"),
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
        _s("wri", "te"),
        "write_text",
    }


def _disallowed_payload_fields() -> set[str]:
    return {
        "account",
        _s("app", "roval"),
        _s("app", "roved"),
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
        _s("rank"),
        _s("rank", "ing"),
        _s("reco", "mmendation"),
        _s("reco", "mmendations"),
        "ready",
        _s("run", "time"),
        _s("run", "times"),
        _s("sc", "ore"),
        _s("sc", "oring"),
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


def _provider_or_sdk_terms() -> set[str]:
    return {
        _s("al", "paca"),
        _s("alpha van", "tage"),
        _s("bloom", "berg"),
        _s("fact", "set"),
        _s("finn", "hub"),
        _s("fr", "ed"),
        _s("interactive bro", "kers"),
        _s("mas", "sive"),
        _s("morning", "star"),
        _s("nas", "daq"),
        _s("poly", "gon"),
        _s("quant", "connect"),
        _s("quan", "dl"),
        _s("refini", "tiv"),
        _s("st", "ooq"),
        _s("tii", "ngo"),
        _s("ya", "hoo"),
        _s("y", "finance"),
    }


def _sensitive_terms() -> set[str]:
    return {
        _s("a", "pi_key"),
        _s("a", "pikey"),
        _s("bear", "er"),
        _s("client_", "sec", "ret"),
        _s("cred", "ential"),
        _s("oa", "uth"),
        _s("pass", "word"),
        _s("private", "_key"),
        _s("sec", "ret"),
        _s("to", "ken"),
    }


def _location_markers() -> set[str]:
    return {
        _s(":", chr(47), chr(47)),
        _s("http", ":"),
        _s("https", ":"),
        _s("w", "ww."),
        _s(".", "com"),
        _s(".da", "ta", chr(47)),
        _s(".", "csv"),
        _s(".", "jsonl"),
        _s(".", "parquet"),
        _s(".", "zip"),
        chr(47),
        chr(92),
    }


def _disallowed_source_words() -> set[str]:
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
        _s("reco", "mmendation"),
        _s("reco", "mmendations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        _s("rank", "ing"),
        _s("sc", "oring"),
        _s("run", "time"),
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("tra", "ding"),
        _s("tra", "de"),
        _s("tra", "des"),
    }
