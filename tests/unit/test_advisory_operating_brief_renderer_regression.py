from __future__ import annotations

import ast
import inspect
import re
import sys

from algotrader.research.advisory_operating_brief_renderer import (
    render_advisory_operating_brief_text,
)
from tests.fixtures.advisory_operating_brief import (
    build_synthetic_advisory_operating_brief,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def _bullet(value: str) -> str:
    return f"- {value}"


_SYNTHETIC_FIXTURE_ID = "synthetic_return_input_snapshot_fixture_001"
_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)
_SYNTHETIC_FIXTURE_CHECKSUM = f"sha256:{_SYNTHETIC_FIXTURE_DIGEST}"

_ITEM_LIMITATION_LINES = (
    _bullet("metadata-only dossier for an already prepared package and matching result"),
    _bullet("does not run research, fetch inputs, compute metrics, or mutate payloads"),
    _bullet("advisory candidate summary for future queue and brief surfaces only"),
)
_SECTION_LIMITATION_LINES = (
    _bullet("metadata-only section for existing candidate brief items"),
    _bullet("does not create research, compute metrics, or mutate item payloads"),
    _bullet("advisory grouping for future queue and brief surfaces only"),
    *_ITEM_LIMITATION_LINES,
)
_BRIEF_LIMITATION_LINES = (
    _bullet("metadata-only brief for existing candidate research brief sections"),
    _bullet("does not create research, compute metrics, or mutate section payloads"),
    _bullet("advisory container for future queue and brief surfaces only"),
    *_SECTION_LIMITATION_LINES,
)
_OPERATING_LIMITATION_LINES = (
    _bullet("metadata-only container for existing candidate research briefs"),
    _bullet("does not create research, compute metrics, or mutate brief payloads"),
    _bullet("advisory grouping for future operating brief surfaces only"),
    *_BRIEF_LIMITATION_LINES,
)
_NON_CLAIM_LINES = (
    _bullet(_not("source app", "roval")),
    _bullet(_not("data app", "roval")),
    _bullet(_not("endpoint app", "roval")),
    _bullet(_not("universe app", "roval")),
    _bullet(_not("bench", "mark app", "roval")),
    _bullet(_not("ca", "sh proxy app", "roval")),
    _bullet(_not("methodology app", "roval")),
    _bullet(_not("evidence app", "roval")),
    _bullet(_not("return-construction app", "roval")),
    _bullet(_not("no-lookahead app", "roval")),
    _bullet(_not("stra", "tegy validation")),
    _bullet(_not("tra", "ding readiness")),
    _bullet(_not("production use")),
    _bullet(_not("bro", "ker or run", "time use")),
    _bullet(_not("or", "der generation")),
    _bullet(_not("port", "folio or allo", "cation authority")),
)

_EXPECTED_RENDERED_LINES = (
    "Advisory Operating Brief",
    "operating_brief_type: advisory_operating_brief",
    "status: candidate_only",
    "title: Candidate research operating brief metadata",
    "candidate_research_brief_count: 1",
    "",
    "Limitations",
    *_OPERATING_LIMITATION_LINES,
    "",
    "Non-Claims",
    *_NON_CLAIM_LINES,
    "",
    "Candidate Research Briefs",
    "",
    "Candidate Research Brief 1",
    "brief_type: candidate_research_brief",
    "status: candidate_only",
    "title: Candidate research brief metadata",
    "section_count: 1",
    "Limitations",
    *_BRIEF_LIMITATION_LINES,
    "Non-Claims",
    *_NON_CLAIM_LINES,
    "Sections",
    "",
    "Candidate Research Brief 1 Section 1",
    "section_type: candidate_research_results",
    "status: candidate_only",
    "title: Candidate research results metadata",
    "item_count: 1",
    "Limitations",
    *_SECTION_LIMITATION_LINES,
    "Non-Claims",
    *_NON_CLAIM_LINES,
    "Items",
    "",
    "Candidate Research Brief 1 Section 1 Item 1",
    "item_type: candidate_research_result",
    "status: candidate_only",
    f"headline: Candidate research result metadata for {_SYNTHETIC_FIXTURE_ID}",
    "Summary Points",
    f"- package snapshot id: {_SYNTHETIC_FIXTURE_ID}",
    f"- package fingerprint: {_SYNTHETIC_FIXTURE_DIGEST}",
    f"- result manifest fixture id: {_SYNTHETIC_FIXTURE_ID}",
    f"- result manifest checksum: {_SYNTHETIC_FIXTURE_CHECKSUM}",
    f"package_fingerprint: {_SYNTHETIC_FIXTURE_DIGEST}",
    f"package_snapshot_id: {_SYNTHETIC_FIXTURE_ID}",
    f"result_snapshot_manifest_fixture_id: {_SYNTHETIC_FIXTURE_ID}",
    f"result_snapshot_manifest_checksum: {_SYNTHETIC_FIXTURE_CHECKSUM}",
    "Limitations",
    *_ITEM_LIMITATION_LINES,
    "Non-Claims",
    *_NON_CLAIM_LINES,
)

_ALLOWED_IMPORTS = {
    "__future__",
    "ast",
    "inspect",
    "re",
    "sys",
    "algotrader.research.advisory_operating_brief_renderer",
    "tests.fixtures.advisory_operating_brief",
}


def test_rendered_text_matches_expected_line_tuple() -> None:
    rendered = _render_fixture()

    assert rendered == _expected_rendered_text()
    assert tuple(rendered.splitlines()) == _EXPECTED_RENDERED_LINES


def test_repeated_rendering_is_byte_identical() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    first = render_advisory_operating_brief_text(operating_brief)
    second = render_advisory_operating_brief_text(operating_brief)

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_advisory_type_and_status_values_are_rendered() -> None:
    rendered = _render_fixture()

    assert "operating_brief_type: advisory_operating_brief" in rendered
    assert "brief_type: candidate_research_brief" in rendered
    assert "section_type: candidate_research_results" in rendered
    assert "item_type: candidate_research_result" in rendered
    assert "status: candidate_only" in rendered


def test_nested_sequence_matches_fixture_shape() -> None:
    lines = tuple(_render_fixture().splitlines())

    assert lines.index("Candidate Research Brief 1") < lines.index(
        "Candidate Research Brief 1 Section 1"
    )
    assert lines.index("Candidate Research Brief 1 Section 1") < lines.index(
        "Candidate Research Brief 1 Section 1 Item 1"
    )
    assert lines.index("brief_type: candidate_research_brief") < lines.index(
        "section_type: candidate_research_results"
    )
    assert lines.index("section_type: candidate_research_results") < lines.index(
        "item_type: candidate_research_result"
    )
    assert lines.index(f"package_snapshot_id: {_SYNTHETIC_FIXTURE_ID}") < lines.index(
        f"result_snapshot_manifest_fixture_id: {_SYNTHETIC_FIXTURE_ID}"
    )
    assert lines.index(
        f"result_snapshot_manifest_fixture_id: {_SYNTHETIC_FIXTURE_ID}"
    ) < lines.index(
        f"result_snapshot_manifest_checksum: {_SYNTHETIC_FIXTURE_CHECKSUM}"
    )


def test_fingerprint_and_manifest_fields_are_rendered() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    item_payload = _single_item_payload(operating_brief.to_dict())
    rendered = render_advisory_operating_brief_text(operating_brief)

    assert f"package_fingerprint: {_SYNTHETIC_FIXTURE_DIGEST}" in rendered
    assert f"package_snapshot_id: {_SYNTHETIC_FIXTURE_ID}" in rendered
    assert f"result_snapshot_manifest_fixture_id: {_SYNTHETIC_FIXTURE_ID}" in rendered
    assert f"result_snapshot_manifest_checksum: {_SYNTHETIC_FIXTURE_CHECKSUM}" in rendered
    assert item_payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST
    assert item_payload["package_snapshot_id"] == _SYNTHETIC_FIXTURE_ID
    assert item_payload["result_snapshot_manifest_fixture_id"] == _SYNTHETIC_FIXTURE_ID
    assert item_payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{item_payload['package_fingerprint']}"
    )


def test_limitations_and_non_claims_are_rendered() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    candidate_payload = _single_candidate_brief_payload(operating_brief.to_dict())
    section_payload = _single_section_payload(operating_brief.to_dict())
    item_payload = _single_item_payload(operating_brief.to_dict())
    rendered = render_advisory_operating_brief_text(operating_brief)

    for value in operating_brief.limitations:
        assert _bullet(value) in rendered
    for value in operating_brief.non_claims:
        assert _bullet(value) in rendered
    for payload in (candidate_payload, section_payload, item_payload):
        for value in payload["limitations"]:
            assert _bullet(value) in rendered
        for value in payload["non_claims"]:
            assert _bullet(value) in rendered


def test_renderer_scaffold_adds_no_blocked_terms() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    rendered = render_advisory_operating_brief_text(operating_brief)
    fixed_text = _remove_payload_strings(rendered, operating_brief.to_dict()).lower()

    for term in _blocked_output_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", fixed_text) is None


def test_copied_text_and_payload_edits_do_not_change_source_objects() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    before_payload = operating_brief.to_dict()
    before_rendered = render_advisory_operating_brief_text(operating_brief)
    copied_lines = before_rendered.splitlines()
    copied_payload = operating_brief.to_dict()

    copied_lines[0] = "edited copied text"
    _edit_copied_payload(copied_payload)

    assert chr(10).join(copied_lines) != before_rendered
    assert copied_payload != before_payload
    assert operating_brief.to_dict() == before_payload
    assert render_advisory_operating_brief_text(operating_brief) == before_rendered


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
    for term in _blocked_output_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", lowered) is None


def _render_fixture() -> str:
    return render_advisory_operating_brief_text(
        build_synthetic_advisory_operating_brief()
    )


def _expected_rendered_text() -> str:
    return chr(10).join(_EXPECTED_RENDERED_LINES)


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


def _edit_copied_payload(payload: dict[str, object]) -> None:
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    payload["title"] = "edited copied payload"
    payload["limitations"].append("edited copied payload")
    candidate_payload["title"] = "edited copied payload"
    candidate_payload["limitations"].append("edited copied payload")
    section_payload["title"] = "edited copied payload"
    section_payload["limitations"].append("edited copied payload")
    item_payload["headline"] = "edited copied payload"
    item_payload["summary_points"].append("edited copied payload")


def _remove_payload_strings(text: str, payload: object) -> str:
    cleaned = text
    for value in _payload_strings(payload):
        cleaned = cleaned.replace(value, "")
    return cleaned


def _payload_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, dict):
        strings: list[str] = []
        for nested_value in value.values():
            strings.extend(_payload_strings(nested_value))
        return tuple(strings)

    if isinstance(value, list):
        strings = []
        for nested_value in value:
            strings.extend(_payload_strings(nested_value))
        return tuple(strings)

    if isinstance(value, str):
        return (value,)

    return ()


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
        _s("algotrader.", "l", "lm"),
        _s("algotrader.", "l", "lms"),
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
        _s("an", "thropic"),
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
        _s("op", "en", "ai"),
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


def _blocked_output_terms() -> set[str]:
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
