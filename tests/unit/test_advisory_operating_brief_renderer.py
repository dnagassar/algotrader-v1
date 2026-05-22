from __future__ import annotations

import ast
import re
from dataclasses import replace
from pathlib import Path

import pytest

import algotrader.research as research_package
from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief import AdvisoryOperatingBrief
from algotrader.research.advisory_operating_brief_renderer import (
    render_advisory_operating_brief_text,
)
from tests.fixtures.advisory_operating_brief import (
    build_synthetic_advisory_operating_brief,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/advisory_operating_brief_renderer.py")
_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief",
}


def test_renderer_accepts_phase_143_synthetic_advisory_operating_brief() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    rendered = render_advisory_operating_brief_text(operating_brief)

    assert isinstance(operating_brief, AdvisoryOperatingBrief)
    assert isinstance(rendered, str)
    assert rendered.startswith("Advisory Operating Brief\n")


@pytest.mark.parametrize("value", (object(), None, "not an operating brief"))
def test_renderer_rejects_non_operating_brief_input(value: object) -> None:
    with pytest.raises(ValidationError, match="AdvisoryOperatingBrief"):
        render_advisory_operating_brief_text(value)


def test_output_is_non_empty_and_repeated_renders_are_identical() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    first = render_advisory_operating_brief_text(operating_brief)
    second = render_advisory_operating_brief_text(operating_brief)

    assert first
    assert first.strip() == first
    assert first == second


def test_candidate_section_and_item_sequence_is_preserved_in_rendered_text() -> None:
    operating_brief = _operating_brief_with_visible_sequence()

    rendered = render_advisory_operating_brief_text(operating_brief)

    assert _index(rendered, "title: candidate alpha") < _index(
        rendered,
        "title: candidate beta",
    )
    assert _index(rendered, "title: section alpha") < _index(
        rendered,
        "headline: candidate item alpha",
    )
    assert _index(rendered, "headline: candidate item alpha") < _index(
        rendered,
        "headline: candidate item beta",
    )
    assert _index(rendered, "headline: candidate item beta") < _index(
        rendered,
        "title: candidate beta",
    )
    assert _index(rendered, "title: section beta") < _index(
        rendered,
        "headline: candidate item gamma",
    )


def test_fixed_advisory_type_and_status_values_appear_in_rendered_text() -> None:
    rendered = render_advisory_operating_brief_text(
        build_synthetic_advisory_operating_brief()
    )

    assert "operating_brief_type: advisory_operating_brief" in rendered
    assert "brief_type: candidate_research_brief" in rendered
    assert "section_type: candidate_research_results" in rendered
    assert "item_type: candidate_research_result" in rendered
    assert "status: candidate_only" in rendered


def test_limitations_and_non_claims_appear_in_rendered_text() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    rendered = render_advisory_operating_brief_text(operating_brief)

    for value in operating_brief.limitations:
        assert f"- {value}" in rendered
    for value in operating_brief.non_claims:
        assert f"- {value}" in rendered


def test_phase_123_digest_appears_when_visible_in_nested_payloads() -> None:
    rendered = render_advisory_operating_brief_text(
        build_synthetic_advisory_operating_brief()
    )

    assert f"package_fingerprint: {_SYNTHETIC_FIXTURE_DIGEST}" in rendered


def test_phase_127_141_provenance_convention_appears_when_visible() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    item_payload = _single_item_payload(operating_brief.to_dict())
    rendered = render_advisory_operating_brief_text(operating_brief)

    assert (
        "result_snapshot_manifest_fixture_id: "
        f"{item_payload['result_snapshot_manifest_fixture_id']}"
    ) in rendered
    assert (
        "result_snapshot_manifest_checksum: "
        f"{item_payload['result_snapshot_manifest_checksum']}"
    ) in rendered
    assert item_payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{item_payload['package_fingerprint']}"
    )


def test_renderer_introduces_no_actionable_or_trading_language() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    rendered = render_advisory_operating_brief_text(operating_brief)
    fixed_text = _remove_payload_strings(rendered, operating_brief.to_dict()).lower()

    for term in _blocked_language_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", fixed_text) is None


def test_rendering_does_not_mutate_operating_brief_or_nested_payloads() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    before = operating_brief.to_dict()
    identities = _identity_snapshot(operating_brief)

    render_advisory_operating_brief_text(operating_brief)
    render_advisory_operating_brief_text(operating_brief)

    assert operating_brief.to_dict() == before
    assert _identity_snapshot(operating_brief) == identities


def test_renderer_output_uses_existing_operating_brief_data() -> None:
    base = build_synthetic_advisory_operating_brief()
    alternate = AdvisoryOperatingBrief(
        operating_brief_type=base.operating_brief_type,
        status=base.status,
        title="alternate advisory display title",
        candidate_research_briefs=base.candidate_research_briefs,
        limitations=base.limitations,
        non_claims=base.non_claims,
    )

    rendered = render_advisory_operating_brief_text(alternate)

    assert "title: alternate advisory display title" in rendered
    assert f"title: {base.title}" not in rendered
    for value in _primitive_values(alternate.to_dict()):
        assert str(value) in rendered


def test_renderer_is_not_reexported_from_research_package() -> None:
    assert not hasattr(research_package, "render_advisory_operating_brief_text")


def test_renderer_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_renderer_module_text_has_no_forbidden_literals() -> None:
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


def _operating_brief_with_visible_sequence() -> AdvisoryOperatingBrief:
    base = build_synthetic_advisory_operating_brief()
    candidate = base.candidate_research_briefs[0]
    section = candidate.sections[0]
    item = section.items[0]

    item_alpha = replace(
        item,
        headline="candidate item alpha",
        summary_points=("summary alpha",),
    )
    item_beta = replace(
        item,
        headline="candidate item beta",
        summary_points=("summary beta",),
    )
    section_alpha = replace(
        section,
        title="section alpha",
        items=(item_alpha, item_beta),
    )
    candidate_alpha = replace(
        candidate,
        title="candidate alpha",
        sections=(section_alpha,),
    )

    item_gamma = replace(
        item,
        headline="candidate item gamma",
        summary_points=("summary gamma",),
    )
    section_beta = replace(
        section,
        title="section beta",
        items=(item_gamma,),
    )
    candidate_beta = replace(
        candidate,
        title="candidate beta",
        sections=(section_beta,),
    )

    return AdvisoryOperatingBrief(
        operating_brief_type=base.operating_brief_type,
        status=base.status,
        title=base.title,
        candidate_research_briefs=(candidate_alpha, candidate_beta),
        limitations=base.limitations,
        non_claims=base.non_claims,
    )


def _index(text: str, value: str) -> int:
    return text.index(value)


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


def _identity_snapshot(operating_brief: AdvisoryOperatingBrief) -> tuple[int, ...]:
    candidate = operating_brief.candidate_research_briefs[0]
    section = candidate.sections[0]
    item = section.items[0]
    return (
        id(operating_brief),
        id(operating_brief.candidate_research_briefs),
        id(candidate),
        id(candidate.sections),
        id(section),
        id(section.items),
        id(item),
        id(item.summary_points),
        id(item.limitations),
        id(item.non_claims),
        id(item.dossier),
        id(item.dossier.package),
        id(item.dossier.result),
    )


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


def _primitive_values(value: object) -> tuple[object, ...]:
    if isinstance(value, dict):
        values: list[object] = []
        for nested_value in value.values():
            values.extend(_primitive_values(nested_value))
        return tuple(values)

    if isinstance(value, list):
        values = []
        for nested_value in value:
            values.extend(_primitive_values(nested_value))
        return tuple(values)

    return (value,)


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
