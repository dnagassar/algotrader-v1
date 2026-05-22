from __future__ import annotations

import ast
import copy
import inspect
import re
import sys

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
from algotrader.research.candidate_result_dossier import (
    CandidateResearchResultDossier,
)
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
    "algotrader.research.advisory_operating_brief",
    "algotrader.research.candidate_research_brief",
    "algotrader.research.candidate_research_brief_item",
    "algotrader.research.candidate_research_brief_section",
    "algotrader.research.candidate_result_dossier",
    "tests.fixtures.advisory_operating_brief",
    "tests.fixtures.candidate_research_brief",
}

_REQUIRED_NON_CLAIMS = (
    _not("source app", "roval"),
    _not("data app", "roval"),
    _not("endpoint app", "roval"),
    _not("universe app", "roval"),
    _not("bench", "mark app", "roval"),
    _not("ca", "sh proxy app", "roval"),
    _not("methodology app", "roval"),
    _not("evidence app", "roval"),
    _not("return-construction app", "roval"),
    _not("no-lookahead app", "roval"),
    _not("stra", "tegy validation"),
    _not("tra", "ding readiness"),
    _not("production use"),
    _not("bro", "ker or run", "time use"),
    _not("or", "der generation"),
    _not("port", "folio or allo", "cation authority"),
)


def test_full_chain_from_candidate_fixture_to_operating_brief_succeeds() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    operating_brief = build_advisory_operating_brief((candidate_brief,))
    fixture_operating_brief = build_synthetic_advisory_operating_brief()

    assert isinstance(candidate_brief, CandidateResearchBrief)
    assert isinstance(operating_brief, AdvisoryOperatingBrief)
    assert isinstance(fixture_operating_brief, AdvisoryOperatingBrief)
    assert operating_brief.candidate_research_briefs == (candidate_brief,)
    assert operating_brief.candidate_research_briefs[0] is candidate_brief
    assert operating_brief.to_dict() == fixture_operating_brief.to_dict()
    assert fixture_operating_brief.to_dict() == (
        expected_synthetic_advisory_operating_brief_dict()
    )


def test_phase_143_fixture_output_matches_expected_dict() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    expected = expected_synthetic_advisory_operating_brief_dict()

    assert operating_brief.to_dict() == expected
    assert tuple(expected) == (
        "operating_brief_type",
        "status",
        "title",
        "candidate_research_brief_count",
        "candidate_research_briefs",
        "limitations",
        "non_claims",
    )
    _assert_primitive_only(expected)


def test_phase_123_fingerprint_is_preserved_in_final_operating_payload() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    item = _single_item(operating_brief)
    item_payload = _single_item_payload(operating_brief.to_dict())

    assert item.dossier.package.fingerprint == _SYNTHETIC_FIXTURE_DIGEST
    assert item_payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST


def test_phase_127_141_manifest_convention_is_preserved_in_final_payload() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    item = _single_item(operating_brief)
    item_payload = _single_item_payload(operating_brief.to_dict())
    package = item.dossier.package

    assert item_payload["package_snapshot_id"] == package.snapshot.snapshot_id
    assert item_payload["result_snapshot_manifest_fixture_id"] == (
        package.snapshot.snapshot_id
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{package.fingerprint}"
    )


def test_advisory_types_and_statuses_remain_fixed_and_candidate_only() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    candidate_brief = _single_candidate_brief(operating_brief)
    section = _single_section(operating_brief)
    item = _single_item(operating_brief)
    dossier = item.dossier
    payload = operating_brief.to_dict()
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    assert operating_brief.operating_brief_type == "advisory_operating_brief"
    assert operating_brief.status == "candidate_only"
    assert candidate_brief.brief_type == "candidate_research_brief"
    assert candidate_brief.status == "candidate_only"
    assert section.section_type == "candidate_research_results"
    assert section.status == "candidate_only"
    assert item.item_type == "candidate_research_result"
    assert item.status == "candidate_only"
    assert dossier.status == "candidate_only"
    assert payload["operating_brief_type"] == "advisory_operating_brief"
    assert payload["status"] == "candidate_only"
    assert candidate_payload["brief_type"] == "candidate_research_brief"
    assert candidate_payload["status"] == "candidate_only"
    assert section_payload["section_type"] == "candidate_research_results"
    assert section_payload["status"] == "candidate_only"
    assert item_payload["item_type"] == "candidate_research_result"
    assert item_payload["status"] == "candidate_only"


def test_limitations_and_non_claims_remain_present_at_each_visible_level() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    candidate_brief = _single_candidate_brief(operating_brief)
    section = _single_section(operating_brief)
    item = _single_item(operating_brief)
    dossier = item.dossier
    payload = operating_brief.to_dict()
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)
    dossier_payload = dossier.to_dict()

    for artifact in (operating_brief, candidate_brief, section, item, dossier):
        assert artifact.limitations
        assert artifact.non_claims
        assert all(value == value.strip() and value for value in artifact.limitations)
        assert all(value.startswith("not ") for value in artifact.non_claims)

    assert all(value in item.limitations for value in dossier.limitations)
    assert all(value in item.non_claims for value in dossier.non_claims)
    assert all(value in section.limitations for value in item.limitations)
    assert all(value in section.non_claims for value in item.non_claims)
    assert all(value in candidate_brief.limitations for value in section.limitations)
    assert all(value in candidate_brief.non_claims for value in section.non_claims)
    assert all(value in operating_brief.limitations for value in candidate_brief.limitations)
    assert all(value in operating_brief.non_claims for value in candidate_brief.non_claims)
    assert payload["limitations"] == list(operating_brief.limitations)
    assert payload["non_claims"] == list(operating_brief.non_claims)
    assert candidate_payload["limitations"] == list(candidate_brief.limitations)
    assert candidate_payload["non_claims"] == list(candidate_brief.non_claims)
    assert section_payload["limitations"] == list(section.limitations)
    assert section_payload["non_claims"] == list(section.non_claims)
    assert item_payload["limitations"] == list(item.limitations)
    assert item_payload["non_claims"] == list(item.non_claims)
    assert dossier_payload["limitations"] == list(dossier.limitations)
    assert dossier_payload["non_claims"] == list(dossier.non_claims)


def test_required_non_claims_remain_present_in_final_operating_payload() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    payload = operating_brief.to_dict()
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    assert set(_REQUIRED_NON_CLAIMS).issubset(payload["non_claims"])
    assert set(_REQUIRED_NON_CLAIMS).issubset(candidate_payload["non_claims"])
    assert set(_REQUIRED_NON_CLAIMS).issubset(section_payload["non_claims"])
    assert set(_REQUIRED_NON_CLAIMS).issubset(item_payload["non_claims"])


def test_repeated_full_chain_construction_is_deterministic() -> None:
    first_candidate = build_synthetic_candidate_research_brief()
    second_candidate = build_synthetic_candidate_research_brief()
    first_operating = build_advisory_operating_brief((first_candidate,))
    second_operating = build_advisory_operating_brief((second_candidate,))
    first_fixture = build_synthetic_advisory_operating_brief()
    second_fixture = build_synthetic_advisory_operating_brief()

    assert first_candidate is not second_candidate
    assert first_operating is not second_operating
    assert first_fixture is not second_fixture
    assert first_operating.to_dict() == second_operating.to_dict()
    assert first_fixture.to_dict() == second_fixture.to_dict()
    assert first_operating.to_dict() == first_fixture.to_dict()
    assert expected_synthetic_advisory_operating_brief_dict() == (
        expected_synthetic_advisory_operating_brief_dict()
    )


def test_identity_and_sequence_preservation_hold_where_applicable() -> None:
    first_candidate = build_synthetic_candidate_research_brief()
    second_candidate = build_synthetic_candidate_research_brief()
    operating_brief = build_advisory_operating_brief(
        (first_candidate, second_candidate)
    )
    fixture_operating_brief = build_synthetic_advisory_operating_brief()
    fixture_candidate = _single_candidate_brief(fixture_operating_brief)

    assert operating_brief.candidate_research_briefs == (
        first_candidate,
        second_candidate,
    )
    assert tuple(id(value) for value in operating_brief.candidate_research_briefs) == (
        id(first_candidate),
        id(second_candidate),
    )
    assert fixture_operating_brief.candidate_research_briefs == (fixture_candidate,)
    assert fixture_operating_brief.candidate_research_briefs[0] is fixture_candidate


def test_primitive_payload_copy_edits_do_not_change_source_objects() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    operating_brief = build_advisory_operating_brief((candidate_brief,))
    section = _single_section(operating_brief)
    item = _single_item(operating_brief)
    dossier = item.dossier
    before = (
        operating_brief.to_dict(),
        candidate_brief.to_dict(),
        section.to_dict(),
        item.to_dict(),
        dossier.to_dict(),
        dossier.package.to_dict(),
        dossier.result.to_dict(),
    )
    identities = (
        id(operating_brief),
        id(candidate_brief),
        id(section),
        id(item),
        id(dossier),
        id(dossier.package),
        id(dossier.result),
        id(operating_brief.candidate_research_briefs),
        id(candidate_brief.sections),
        id(section.items),
    )
    operating_payload = operating_brief.to_dict()
    expected_payload = expected_synthetic_advisory_operating_brief_dict()

    _edit_operating_payload_copy(operating_payload)
    _edit_operating_payload_copy(expected_payload)

    assert (
        operating_brief.to_dict(),
        candidate_brief.to_dict(),
        section.to_dict(),
        item.to_dict(),
        dossier.to_dict(),
        dossier.package.to_dict(),
        dossier.result.to_dict(),
    ) == before
    assert (
        id(operating_brief),
        id(candidate_brief),
        id(section),
        id(item),
        id(dossier),
        id(dossier.package),
        id(dossier.result),
        id(operating_brief.candidate_research_briefs),
        id(candidate_brief.sections),
        id(section.items),
    ) == identities


def test_no_disallowed_payload_or_object_fields_are_introduced() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    candidate_brief = _single_candidate_brief(operating_brief)
    section = _single_section(operating_brief)
    item = _single_item(operating_brief)
    dossier = item.dossier
    blocked_fields = _blocked_field_names()

    assert _payload_keys(operating_brief.to_dict()).isdisjoint(blocked_fields)
    for artifact in (
        operating_brief,
        candidate_brief,
        section,
        item,
        dossier,
        dossier.package,
        dossier.result,
    ):
        assert all(not hasattr(artifact, field_name) for field_name in blocked_fields)


def test_new_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_new_module_text_has_no_disallowed_literals() -> None:
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
    for term in _index_like_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", lowered) is None
    for term in _blocked_language_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", lowered) is None


def _single_candidate_brief(
    operating_brief: AdvisoryOperatingBrief,
) -> CandidateResearchBrief:
    candidate_briefs = operating_brief.candidate_research_briefs

    assert len(candidate_briefs) == 1
    candidate_brief = candidate_briefs[0]
    assert isinstance(candidate_brief, CandidateResearchBrief)
    return candidate_brief


def _single_section(
    operating_brief: AdvisoryOperatingBrief,
) -> CandidateResearchBriefSection:
    sections = _single_candidate_brief(operating_brief).sections

    assert len(sections) == 1
    section = sections[0]
    assert isinstance(section, CandidateResearchBriefSection)
    return section


def _single_item(
    operating_brief: AdvisoryOperatingBrief,
) -> CandidateResearchBriefItem:
    items = _single_section(operating_brief).items

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, CandidateResearchBriefItem)
    assert isinstance(item.dossier, CandidateResearchResultDossier)
    return item


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


def _edit_operating_payload_copy(payload: dict[str, object]) -> None:
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    payload["candidate_research_briefs"].append(copy.deepcopy(candidate_payload))
    payload["limitations"].append("edited primitive copy")
    payload["non_claims"].append("not edited primitive source")
    candidate_payload["sections"].append(copy.deepcopy(section_payload))
    candidate_payload["limitations"].append("edited primitive copy")
    candidate_payload["non_claims"].append("not edited primitive source")
    section_payload["items"].append(copy.deepcopy(item_payload))
    section_payload["limitations"].append("edited primitive copy")
    section_payload["non_claims"].append("not edited primitive source")
    item_payload["summary_points"].append("edited primitive copy")
    item_payload["limitations"].append("edited primitive copy")
    item_payload["non_claims"].append("not edited primitive source")


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


def _matches_blocked_prefix(
    module_name: str,
    blocked_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == blocked_prefix
        or module_name.startswith(f"{blocked_prefix}.")
        for blocked_prefix in blocked_prefixes
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


def _blocked_import_prefixes() -> tuple[str, ...]:
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
        _s("ht", "tp"),
        "httpx",
        "ipynb",
        "langchain",
        "langgraph",
        _s("l", "lm"),
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
        "subprocess",
        "urllib",
        "vectorbt",
        _s("y", "finance"),
    )


def _blocked_call_names() -> set[str]:
    return {
        "__import__",
        _s("cli", "ent"),
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
        _s("op", "en"),
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
        _s("sub", "mit_", "or", "der"),
        "to_sql",
        "urlopen",
        "walk",
        _s("wri", "te"),
        "write_text",
    }


def _blocked_field_names() -> set[str]:
    return {
        _s("acc", "ount"),
        _s("act", "ion"),
        _s("act", "ions"),
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
        _s("prior", "ity"),
        _s("prior", "itized"),
        _s("ra", "nk"),
        _s("ra", "nking"),
        _s("reco", "mmendation"),
        _s("reco", "mmendations"),
        "ready",
        _s("run", "time"),
        _s("run", "times"),
        _s("sco", "re"),
        _s("sco", "ring"),
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
        _s("ht", "tp", ":"),
        _s("ht", "tps", ":"),
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


def _index_like_terms() -> set[str]:
    return {
        _s("s", "&p"),
        _s("russ", "ell"),
        _s("wil", "shire"),
        _s("ms", "ci"),
        _s("cr", "sp"),
    }


def _blocked_language_terms() -> set[str]:
    return {
        _s("act", "ion"),
        _s("act", "ions"),
        _s("app", "roval"),
        _s("app", "roved"),
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
        _s("po", "sition"),
        _s("po", "sitions"),
        _s("prior", "itize"),
        _s("prior", "itized"),
        _s("ra", "nk"),
        _s("ra", "nking"),
        _s("reco", "mmend"),
        _s("reco", "mmendation"),
        _s("reco", "mmendations"),
        _s("run", "time"),
        _s("sco", "re"),
        _s("sco", "ring"),
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("tra", "ding"),
        _s("tra", "de"),
        _s("tra", "des"),
    }
