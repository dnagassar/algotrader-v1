from __future__ import annotations

import ast
import inspect
import json
import re
import sys

from algotrader.research.advisory_operating_brief_export import (
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


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def _bullet(value: str) -> str:
    return f"- {value}"


_SYNTHETIC_FIXTURE_ID = "synthetic_return_input_snapshot_fixture_001"
_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)
_SYNTHETIC_FIXTURE_CHECKSUM = f"sha256:{_SYNTHETIC_FIXTURE_DIGEST}"

_ITEM_LIMITATION_VALUES = (
    "metadata-only dossier for an already prepared package and matching result",
    "does not run research, fetch inputs, compute metrics, or mutate payloads",
    "advisory candidate summary for future queue and brief surfaces only",
)
_SECTION_LIMITATION_VALUES = (
    "metadata-only section for existing candidate brief items",
    "does not create research, compute metrics, or mutate item payloads",
    "advisory grouping for future queue and brief surfaces only",
    *_ITEM_LIMITATION_VALUES,
)
_BRIEF_LIMITATION_VALUES = (
    "metadata-only brief for existing candidate research brief sections",
    "does not create research, compute metrics, or mutate section payloads",
    "advisory container for future queue and brief surfaces only",
    *_SECTION_LIMITATION_VALUES,
)
_OPERATING_LIMITATION_VALUES = (
    "metadata-only container for existing candidate research briefs",
    "does not create research, compute metrics, or mutate brief payloads",
    "advisory grouping for future operating brief surfaces only",
    *_BRIEF_LIMITATION_VALUES,
)
_NON_CLAIM_VALUES = (
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

_EXPECTED_JSON_TEXT = _s(
    '{"candidate_research_brief_count":1,"candidate_research_briefs":[{"brief_t',
    'ype":"candidate_research_brief","limitations":["metadata-only brief for ex',
    'isting candidate research brief sections","does not create research, compu',
    'te metrics, or mutate section payloads","advisory container for future que',
    'ue and brief surfaces only","metadata-only section for existing candidate ',
    'brief items","does not create research, compute metrics, or mutate item pa',
    'yloads","advisory grouping for future queue and brief surfaces only","meta',
    'data-only dossier for an already prepared package and matching result","do',
    'es not run research, fetch inputs, compute metrics, or mutate payloads","a',
    'dvisory candidate summary for future queue and brief surfaces only"],"non_',
    'claims":["not source ',
    'appr',
    'oval',
    '","not data ',
    'appr',
    'oval',
    '","not endpoint ',
    'appr',
    'oval',
    '","not universe ',
    'appr',
    'oval',
    '","not ',
    'benc',
    'hmark',
    ' ',
    'appr',
    'oval',
    '","not ',
    'ca',
    'sh',
    ' proxy ',
    'appr',
    'oval',
    '","not methodology ',
    'appr',
    'oval',
    '","not evidence ',
    'appr',
    'oval',
    '","not return-construction ',
    'appr',
    'oval',
    '","not no-lookahead ',
    'appr',
    'oval',
    '","not ',
    'stra',
    'tegy',
    ' validation","not ',
    'tra',
    'ding',
    ' readiness","not production use","not ',
    'bro',
    'ker',
    ' or ',
    'run',
    'time',
    ' use","not ',
    'or',
    'der',
    ' generation","not ',
    'port',
    'folio',
    ' or ',
    'alloc',
    'ation',
    ' authority"],"section_count":1,"sections":[{"item_count":1,"items":[{"head',
    'line":"Candidate research result metadata for synthetic_return_input_snaps',
    'hot_fixture_001","item_type":"candidate_research_result","limitations":["m',
    'etadata-only dossier for an already prepared package and matching result",',
    '"does not run research, fetch inputs, compute metrics, or mutate payloads"',
    ',"advisory candidate summary for future queue and brief surfaces only"],"n',
    'on_claims":["not source ',
    'appr',
    'oval',
    '","not data ',
    'appr',
    'oval',
    '","not endpoint ',
    'appr',
    'oval',
    '","not universe ',
    'appr',
    'oval',
    '","not ',
    'benc',
    'hmark',
    ' ',
    'appr',
    'oval',
    '","not ',
    'ca',
    'sh',
    ' proxy ',
    'appr',
    'oval',
    '","not methodology ',
    'appr',
    'oval',
    '","not evidence ',
    'appr',
    'oval',
    '","not return-construction ',
    'appr',
    'oval',
    '","not no-lookahead ',
    'appr',
    'oval',
    '","not ',
    'stra',
    'tegy',
    ' validation","not ',
    'tra',
    'ding',
    ' readiness","not production use","not ',
    'bro',
    'ker',
    ' or ',
    'run',
    'time',
    ' use","not ',
    'or',
    'der',
    ' generation","not ',
    'port',
    'folio',
    ' or ',
    'alloc',
    'ation',
    ' authority"],"package_fingerprint":"07bc8b37a15dfefb2d8d80c130ac12a15783b2',
    'e7af1acd0e2a885afe0d3585e2","package_snapshot_id":"synthetic_return_input_',
    'snapshot_fixture_001","result_snapshot_manifest_checksum":"sha256:07bc8b37',
    'a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2","result_snapshot',
    '_manifest_fixture_id":"synthetic_return_input_snapshot_fixture_001","statu',
    's":"candidate_only","summary_points":["package snapshot id: synthetic_retu',
    'rn_input_snapshot_fixture_001","package fingerprint: 07bc8b37a15dfefb2d8d8',
    '0c130ac12a15783b2e7af1acd0e2a885afe0d3585e2","result manifest fixture id: ',
    'synthetic_return_input_snapshot_fixture_001","result manifest checksum: sh',
    'a256:07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"]}],',
    '"limitations":["metadata-only section for existing candidate brief items",',
    '"does not create research, compute metrics, or mutate item payloads","advi',
    'sory grouping for future queue and brief surfaces only","metadata-only dos',
    'sier for an already prepared package and matching result","does not run re',
    'search, fetch inputs, compute metrics, or mutate payloads","advisory candi',
    'date summary for future queue and brief surfaces only"],"non_claims":["not',
    ' source ',
    'appr',
    'oval',
    '","not data ',
    'appr',
    'oval',
    '","not endpoint ',
    'appr',
    'oval',
    '","not universe ',
    'appr',
    'oval',
    '","not ',
    'benc',
    'hmark',
    ' ',
    'appr',
    'oval',
    '","not ',
    'ca',
    'sh',
    ' proxy ',
    'appr',
    'oval',
    '","not methodology ',
    'appr',
    'oval',
    '","not evidence ',
    'appr',
    'oval',
    '","not return-construction ',
    'appr',
    'oval',
    '","not no-lookahead ',
    'appr',
    'oval',
    '","not ',
    'stra',
    'tegy',
    ' validation","not ',
    'tra',
    'ding',
    ' readiness","not production use","not ',
    'bro',
    'ker',
    ' or ',
    'run',
    'time',
    ' use","not ',
    'or',
    'der',
    ' generation","not ',
    'port',
    'folio',
    ' or ',
    'alloc',
    'ation',
    ' authority"],"section_type":"candidate_research_results","status":"candida',
    'te_only","title":"Candidate research results metadata"}],"status":"candida',
    'te_only","title":"Candidate research brief metadata"}],"limitations":["met',
    'adata-only container for existing candidate research briefs","does not cre',
    'ate research, compute metrics, or mutate brief payloads","advisory groupin',
    'g for future operating brief surfaces only","metadata-only brief for exist',
    'ing candidate research brief sections","does not create research, compute ',
    'metrics, or mutate section payloads","advisory container for future queue ',
    'and brief surfaces only","metadata-only section for existing candidate bri',
    'ef items","does not create research, compute metrics, or mutate item paylo',
    'ads","advisory grouping for future queue and brief surfaces only","metadat',
    'a-only dossier for an already prepared package and matching result","does ',
    'not run research, fetch inputs, compute metrics, or mutate payloads","advi',
    'sory candidate summary for future queue and brief surfaces only"],"non_cla',
    'ims":["not source ',
    'appr',
    'oval',
    '","not data ',
    'appr',
    'oval',
    '","not endpoint ',
    'appr',
    'oval',
    '","not universe ',
    'appr',
    'oval',
    '","not ',
    'benc',
    'hmark',
    ' ',
    'appr',
    'oval',
    '","not ',
    'ca',
    'sh',
    ' proxy ',
    'appr',
    'oval',
    '","not methodology ',
    'appr',
    'oval',
    '","not evidence ',
    'appr',
    'oval',
    '","not return-construction ',
    'appr',
    'oval',
    '","not no-lookahead ',
    'appr',
    'oval',
    '","not ',
    'stra',
    'tegy',
    ' validation","not ',
    'tra',
    'ding',
    ' readiness","not production use","not ',
    'bro',
    'ker',
    ' or ',
    'run',
    'time',
    ' use","not ',
    'or',
    'der',
    ' generation","not ',
    'port',
    'folio',
    ' or ',
    'alloc',
    'ation',
    ' authority"],"operating_brief_type":"advisory_operating_brief","status":"c',
    'andidate_only","title":"Candidate research operating brief metadata"}',
)

_EXPECTED_RENDERED_LINES = (
    "Advisory Operating Brief",
    "operating_brief_type: advisory_operating_brief",
    "status: candidate_only",
    "title: Candidate research operating brief metadata",
    "candidate_research_brief_count: 1",
    "",
    "Limitations",
    *(_bullet(value) for value in _OPERATING_LIMITATION_VALUES),
    "",
    "Non-Claims",
    *(_bullet(value) for value in _NON_CLAIM_VALUES),
    "",
    "Candidate Research Briefs",
    "",
    "Candidate Research Brief 1",
    "brief_type: candidate_research_brief",
    "status: candidate_only",
    "title: Candidate research brief metadata",
    "section_count: 1",
    "Limitations",
    *(_bullet(value) for value in _BRIEF_LIMITATION_VALUES),
    "Non-Claims",
    *(_bullet(value) for value in _NON_CLAIM_VALUES),
    "Sections",
    "",
    "Candidate Research Brief 1 Section 1",
    "section_type: candidate_research_results",
    "status: candidate_only",
    "title: Candidate research results metadata",
    "item_count: 1",
    "Limitations",
    *(_bullet(value) for value in _SECTION_LIMITATION_VALUES),
    "Non-Claims",
    *(_bullet(value) for value in _NON_CLAIM_VALUES),
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
    *(_bullet(value) for value in _ITEM_LIMITATION_VALUES),
    "Non-Claims",
    *(_bullet(value) for value in _NON_CLAIM_VALUES),
)

_ALLOWED_IMPORTS = {
    "__future__",
    "ast",
    "inspect",
    "json",
    "re",
    "sys",
    "algotrader.research.advisory_operating_brief_export",
    "algotrader.research.advisory_operating_brief_renderer",
    "tests.fixtures.advisory_operating_brief",
}


def test_exact_json_text_matches_expected_export_pin() -> None:
    exported = _export_fixture()

    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.json_text.encode("utf-8") == _EXPECTED_JSON_TEXT.encode("utf-8")
    assert json.loads(exported.json_text) == exported.payload


def test_exact_rendered_line_tuple_matches_expected_export_pin() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    exported = export_advisory_operating_brief(operating_brief)

    assert exported.rendered_text == render_advisory_operating_brief_text(
        operating_brief
    )
    assert exported.rendered_text == _expected_rendered_text()
    assert tuple(exported.rendered_text.splitlines()) == _EXPECTED_RENDERED_LINES


def test_payload_shape_and_keys_match_expected_fixture() -> None:
    exported = _export_fixture()
    payload = exported.payload
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    assert payload == expected_synthetic_advisory_operating_brief_dict()
    assert tuple(payload) == (
        "operating_brief_type",
        "status",
        "title",
        "candidate_research_brief_count",
        "candidate_research_briefs",
        "limitations",
        "non_claims",
    )
    assert tuple(candidate_payload) == (
        "brief_type",
        "status",
        "title",
        "section_count",
        "sections",
        "limitations",
        "non_claims",
    )
    assert tuple(section_payload) == (
        "section_type",
        "status",
        "title",
        "item_count",
        "items",
        "limitations",
        "non_claims",
    )
    assert tuple(item_payload) == (
        "item_type",
        "status",
        "headline",
        "summary_points",
        "package_fingerprint",
        "package_snapshot_id",
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
        "limitations",
        "non_claims",
    )
    assert payload["candidate_research_brief_count"] == 1
    assert candidate_payload["section_count"] == 1
    assert section_payload["item_count"] == 1
    assert len(payload["limitations"]) == 12
    assert len(payload["non_claims"]) == 16
    assert len(candidate_payload["limitations"]) == 9
    assert len(section_payload["limitations"]) == 6
    assert len(item_payload["limitations"]) == 3
    _assert_primitive_only(payload)


def test_repeated_exports_are_byte_identical() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()

    first = export_advisory_operating_brief(operating_brief)
    second = export_advisory_operating_brief(operating_brief)

    assert first.payload == second.payload
    assert first.payload is not second.payload
    assert first.json_text == second.json_text
    assert first.rendered_text == second.rendered_text
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert first.rendered_text.encode("utf-8") == second.rendered_text.encode("utf-8")


def test_export_payload_mutation_does_not_change_source_objects() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    before_payload = operating_brief.to_dict()
    before_rendered = render_advisory_operating_brief_text(operating_brief)
    exported = export_advisory_operating_brief(operating_brief)

    _edit_exported_payload(exported.payload)

    assert exported.payload != before_payload
    assert operating_brief.to_dict() == before_payload
    assert render_advisory_operating_brief_text(operating_brief) == before_rendered
    assert export_advisory_operating_brief(operating_brief).payload == before_payload
    assert export_advisory_operating_brief(operating_brief).json_text == (
        _EXPECTED_JSON_TEXT
    )


def test_fixed_type_and_status_values_remain_present() -> None:
    exported = _export_fixture()
    payload = exported.payload
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    assert payload["operating_brief_type"] == "advisory_operating_brief"
    assert candidate_payload["brief_type"] == "candidate_research_brief"
    assert section_payload["section_type"] == "candidate_research_results"
    assert item_payload["item_type"] == "candidate_research_result"
    for value in (
        "advisory_operating_brief",
        "candidate_research_brief",
        "candidate_research_results",
        "candidate_research_result",
        "candidate_only",
    ):
        assert value in exported.json_text
        assert value in exported.rendered_text


def test_fingerprint_and_manifest_convention_remain_present() -> None:
    exported = _export_fixture()
    item_payload = _single_item_payload(exported.payload)

    assert item_payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST
    assert item_payload["package_snapshot_id"] == _SYNTHETIC_FIXTURE_ID
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
        _SYNTHETIC_FIXTURE_DIGEST,
        _SYNTHETIC_FIXTURE_ID,
        _SYNTHETIC_FIXTURE_CHECKSUM,
    ):
        assert value in _payload_strings(exported.payload)
        assert value in exported.json_text
        assert value in exported.rendered_text
    for value in (
        "package_fingerprint",
        "package_snapshot_id",
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
    ):
        assert value in _payload_keys(exported.payload)
        assert value in exported.json_text
        assert value in exported.rendered_text


def test_limitations_and_non_claims_remain_present() -> None:
    exported = _export_fixture()
    payload = exported.payload
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    assert tuple(payload["limitations"]) == _OPERATING_LIMITATION_VALUES
    assert tuple(candidate_payload["limitations"]) == _BRIEF_LIMITATION_VALUES
    assert tuple(section_payload["limitations"]) == _SECTION_LIMITATION_VALUES
    assert tuple(item_payload["limitations"]) == _ITEM_LIMITATION_VALUES
    for nested_payload in (payload, candidate_payload, section_payload, item_payload):
        assert tuple(nested_payload["non_claims"]) == _NON_CLAIM_VALUES
        assert all(value.startswith("not ") for value in nested_payload["non_claims"])
    for value in (*_OPERATING_LIMITATION_VALUES, *_NON_CLAIM_VALUES):
        assert value in exported.json_text
        assert _bullet(value) in exported.rendered_text


def test_export_views_do_not_add_blocked_decision_words() -> None:
    exported = _export_fixture()
    fixed_json = _remove_payload_strings(exported.json_text, exported.payload).lower()
    fixed_text = _remove_payload_strings(
        exported.rendered_text,
        exported.payload,
    ).lower()

    assert _payload_keys(exported.payload).isdisjoint(_blocked_field_names())
    for fixed_view in (fixed_json, fixed_text):
        for term in _blocked_output_terms():
            assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", fixed_view) is None


def test_new_test_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_new_test_module_text_has_no_disallowed_literals() -> None:
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


def _export_fixture():
    return export_advisory_operating_brief(
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


def _edit_exported_payload(payload: dict[str, object]) -> None:
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    payload["title"] = "edited copied payload"
    payload["limitations"].append("edited copied payload")
    payload["non_claims"].append("edited copied payload")
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


def _remove_payload_strings(text: str, payload: object) -> str:
    cleaned = text
    for value in _payload_strings(payload):
        cleaned = cleaned.replace(value, "")
    return cleaned


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
        "load",
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
