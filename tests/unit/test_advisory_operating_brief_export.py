from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
import inspect
import json
import re

import pytest

import algotrader.research as research_package
import algotrader.research.advisory_operating_brief_export as export_module
from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_export import (
    AdvisoryOperatingBriefExport,
    export_advisory_operating_brief,
)
from algotrader.research.advisory_operating_brief_renderer import (
    render_advisory_operating_brief_text,
)
from tests.fixtures.advisory_operating_brief import (
    build_synthetic_advisory_operating_brief,
    expected_synthetic_advisory_operating_brief_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_SYNTHETIC_FIXTURE_ID = "synthetic_return_input_snapshot_fixture_001"
_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)
_SYNTHETIC_FIXTURE_CHECKSUM = f"sha256:{_SYNTHETIC_FIXTURE_DIGEST}"

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "json",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief",
    "algotrader.research.advisory_operating_brief_renderer",
}


def test_export_helper_accepts_phase_143_synthetic_advisory_operating_brief() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    exported = export_advisory_operating_brief(operating_brief)

    assert isinstance(exported, AdvisoryOperatingBriefExport)
    assert exported.payload == expected_synthetic_advisory_operating_brief_dict()
    assert isinstance(exported.json_text, str)
    assert isinstance(exported.rendered_text, str)


@pytest.mark.parametrize("value", (object(), None, "not an operating brief"))
def test_export_helper_rejects_non_operating_brief_input(value: object) -> None:
    with pytest.raises(ValidationError, match="AdvisoryOperatingBrief"):
        export_advisory_operating_brief(value)


def test_export_object_is_frozen() -> None:
    exported = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )

    with pytest.raises(FrozenInstanceError):
        exported.rendered_text = "edited"


def test_payload_equals_brief_to_dict() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    exported = export_advisory_operating_brief(operating_brief)

    assert exported.payload == operating_brief.to_dict()
    _assert_primitive_only(exported.payload)


def test_payload_edits_are_isolated_from_source_operating_brief() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    before_payload = operating_brief.to_dict()
    before_rendered = render_advisory_operating_brief_text(operating_brief)
    exported = export_advisory_operating_brief(operating_brief)

    _edit_exported_payload(exported.payload)

    assert exported.payload != before_payload
    assert operating_brief.to_dict() == before_payload
    assert render_advisory_operating_brief_text(operating_brief) == before_rendered
    assert export_advisory_operating_brief(operating_brief).payload == before_payload


def test_json_text_is_byte_stable_across_repeated_calls() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    first = export_advisory_operating_brief(operating_brief).json_text
    second = export_advisory_operating_brief(operating_brief).json_text

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_json_text_uses_sorted_keys_and_compact_separators() -> None:
    exported = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )

    assert exported.json_text == json.dumps(
        exported.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert exported.json_text != json.dumps(exported.payload, sort_keys=True)
    assert exported.json_text.startswith('{"candidate_research_brief_count":')


def test_json_text_loads_back_to_payload() -> None:
    exported = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )

    assert json.loads(exported.json_text) == exported.payload


def test_rendered_text_matches_existing_renderer() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    exported = export_advisory_operating_brief(operating_brief)

    assert exported.rendered_text == render_advisory_operating_brief_text(
        operating_brief
    )


def test_repeated_export_calls_are_deterministic() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    first = export_advisory_operating_brief(operating_brief)
    second = export_advisory_operating_brief(operating_brief)

    assert first == second
    assert first.payload is not second.payload


def test_phase_123_digest_appears_in_json_and_rendered_text() -> None:
    exported = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )

    assert _SYNTHETIC_FIXTURE_DIGEST in exported.json_text
    assert _SYNTHETIC_FIXTURE_DIGEST in exported.rendered_text


def test_phase_127_141_provenance_convention_appears_in_both_views() -> None:
    exported = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )
    item_payload = _single_item_payload(exported.payload)

    assert item_payload["result_snapshot_manifest_fixture_id"] == (
        _SYNTHETIC_FIXTURE_ID
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        _SYNTHETIC_FIXTURE_CHECKSUM
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{item_payload['package_fingerprint']}"
    )
    for value in (
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
        _SYNTHETIC_FIXTURE_ID,
        _SYNTHETIC_FIXTURE_CHECKSUM,
    ):
        assert value in exported.json_text
        assert value in exported.rendered_text


def test_fixed_advisory_type_and_status_values_appear_in_both_views() -> None:
    exported = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )

    for value in (
        "advisory_operating_brief",
        "candidate_research_brief",
        "candidate_research_results",
        "candidate_research_result",
        "candidate_only",
    ):
        assert value in exported.json_text
        assert value in exported.rendered_text


def test_export_module_introduces_no_forbidden_behavior_fields() -> None:
    exported = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )

    assert _payload_keys(exported.payload).isdisjoint(_blocked_field_names())
    assert not hasattr(research_package, "export_advisory_operating_brief")
    assert not hasattr(research_package, "AdvisoryOperatingBriefExport")


def test_export_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_export_module_text_has_no_disallowed_literals() -> None:
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


def _edit_exported_payload(payload: dict[str, object]) -> None:
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
    return inspect.getsource(export_module)


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
        "llm",
        _s("mas", "sive"),
        _s("net", "work"),
        _s("num", "py"),
        _s("op", "en", "ai"),
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


def _blocked_call_names() -> set[str]:
    return {
        "__import__",
        "Path",
        _s("cli", "ent"),
        _s("con", "nect"),
        "date.today",
        "datetime.now",
        "datetime.utcnow",
        _s("down", "load"),
        "eval",
        "exec",
        "exists",
        "from_file",
        "getenv",
        "glob",
        _s("import_module"),
        _s("ing", "est"),
        "is_file",
        "iterdir",
        "json.loads",
        "load",
        "loads",
        "mkdir",
        _s("op", "en"),
        "os.environ.get",
        "os.getenv",
        "post",
        "print",
        _s("re", "ad"),
        "read_bytes",
        "read_csv",
        "read_text",
        _s("re", "quest"),
        _s("re", "quests.get"),
        "rglob",
        "save",
        _s("so", "cket.socket"),
        "stat",
        _s("sub", "mit_", "or", "der"),
        "to_file",
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
        "evaluator",
        "evaluators",
        _s("fi", "ll"),
        _s("fi", "lls"),
        "live_authorized",
        "live_probe_eligible",
        _s("or", "der"),
        _s("or", "ders"),
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
