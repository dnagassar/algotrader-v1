from __future__ import annotations

import ast
import inspect
import json
import sys

from algotrader.research.advisory_operating_brief_export import (
    AdvisoryOperatingBriefExport,
    export_advisory_operating_brief,
)
from algotrader.research.advisory_operating_brief_review import (
    build_advisory_operating_brief_review_checklist,
)
from tests.fixtures.advisory_operating_brief import (
    build_synthetic_advisory_operating_brief,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_SYNTHETIC_FIXTURE_ID = "synthetic_return_input_snapshot_fixture_001"
_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)
_SYNTHETIC_FIXTURE_CHECKSUM = f"sha256:{_SYNTHETIC_FIXTURE_DIGEST}"

_EXPECTED_REVIEW_DICT = {
    "review_type": "advisory_operating_brief_review_checklist",
    "status": "candidate_only",
    "candidate_only": True,
    "advisory_only": True,
    "has_limitations": True,
    "has_non_claims": True,
    "has_fingerprint": True,
    "has_provenance": True,
    "forbidden_capital_authority_fields": [],
    "findings": [],
}
_EXPECTED_REVIEW_JSON = (
    '{"review_type":"advisory_operating_brief_review_checklist",'
    '"status":"candidate_only","candidate_only":true,"advisory_only":true,'
    '"has_limitations":true,"has_non_claims":true,"has_fingerprint":true,'
    '"has_provenance":true,"forbidden_capital_authority_fields":[],'
    '"findings":[]}'
)

_OPERATING_LIMITATIONS = (
    "metadata-only container for existing candidate research briefs",
    "does not create research, compute metrics, or mutate brief payloads",
    "advisory grouping for future operating brief surfaces only",
)
_BRIEF_LIMITATIONS = (
    "metadata-only brief for existing candidate research brief sections",
    "does not create research, compute metrics, or mutate section payloads",
    "advisory container for future queue and brief surfaces only",
)
_SECTION_LIMITATIONS = (
    "metadata-only section for existing candidate brief items",
    "does not create research, compute metrics, or mutate item payloads",
    "advisory grouping for future queue and brief surfaces only",
)
_ITEM_LIMITATIONS = (
    "metadata-only dossier for an already prepared package and matching result",
    "does not run research, fetch inputs, compute metrics, or mutate payloads",
    "advisory candidate summary for future queue and brief surfaces only",
)
_EXPECTED_NON_CLAIMS = (
    _s("not source app", "roval"),
    _s("not da", "ta app", "roval"),
    _s("not endpoint app", "roval"),
    _s("not universe app", "roval"),
    _s("not bench", "mark app", "roval"),
    _s("not ca", "sh proxy app", "roval"),
    _s("not methodology app", "roval"),
    _s("not evidence app", "roval"),
    _s("not return-construction app", "roval"),
    _s("not no-lookahead app", "roval"),
    _s("not stra", "tegy validation"),
    _s("not tra", "ding readiness"),
    "not production use",
    _s("not bro", "ker or run", "time use"),
    _s("not or", "der generation"),
    _s("not port", "folio or allo", "cation auth", "ority"),
)
_EXPECTED_EXPORT_EVIDENCE = {
    "operating_brief_type": "advisory_operating_brief",
    "operating_status": "candidate_only",
    "operating_limitations": [
        *_OPERATING_LIMITATIONS,
        *_BRIEF_LIMITATIONS,
        *_SECTION_LIMITATIONS,
        *_ITEM_LIMITATIONS,
    ],
    "operating_non_claims": [*_EXPECTED_NON_CLAIMS],
    "candidate_research_brief_count": 1,
    "candidate_brief_type": "candidate_research_brief",
    "candidate_brief_status": "candidate_only",
    "candidate_brief_limitations": [
        *_BRIEF_LIMITATIONS,
        *_SECTION_LIMITATIONS,
        *_ITEM_LIMITATIONS,
    ],
    "candidate_brief_non_claims": [*_EXPECTED_NON_CLAIMS],
    "section_count": 1,
    "section_type": "candidate_research_results",
    "section_status": "candidate_only",
    "section_limitations": [*_SECTION_LIMITATIONS, *_ITEM_LIMITATIONS],
    "section_non_claims": [*_EXPECTED_NON_CLAIMS],
    "item_count": 1,
    "item_type": "candidate_research_result",
    "item_status": "candidate_only",
    "item_limitations": [*_ITEM_LIMITATIONS],
    "item_non_claims": [*_EXPECTED_NON_CLAIMS],
    "item_package_fingerprint": _SYNTHETIC_FIXTURE_DIGEST,
    "item_package_snapshot_id": _SYNTHETIC_FIXTURE_ID,
    "item_result_snapshot_manifest_fixture_id": _SYNTHETIC_FIXTURE_ID,
    "item_result_snapshot_manifest_checksum": _SYNTHETIC_FIXTURE_CHECKSUM,
    "item_summary_points": [
        f"package snapshot id: {_SYNTHETIC_FIXTURE_ID}",
        f"package fingerprint: {_SYNTHETIC_FIXTURE_DIGEST}",
        f"result manifest fixture id: {_SYNTHETIC_FIXTURE_ID}",
        f"result manifest checksum: {_SYNTHETIC_FIXTURE_CHECKSUM}",
    ],
}

_ALLOWED_IMPORTS = {
    "__future__",
    "ast",
    "inspect",
    "json",
    "sys",
    "algotrader.research.advisory_operating_brief_export",
    "algotrader.research.advisory_operating_brief_review",
    "tests.fixtures.advisory_operating_brief",
}


def test_synthetic_export_review_pin_matches_existing_chain() -> None:
    exported = _export_fixture()
    before_payload = _freeze(exported.payload)
    before_json_text = exported.json_text
    before_rendered_text = exported.rendered_text

    checklist = build_advisory_operating_brief_review_checklist(exported)

    assert checklist.to_dict() == _EXPECTED_REVIEW_DICT
    assert _export_evidence(exported.payload) == _EXPECTED_EXPORT_EVIDENCE
    assert _freeze(exported.payload) == before_payload
    assert exported.json_text == before_json_text
    assert exported.rendered_text == before_rendered_text


def test_repeated_review_construction_is_dict_and_byte_identical() -> None:
    exported = _export_fixture()

    first = build_advisory_operating_brief_review_checklist(exported).to_dict()
    second = build_advisory_operating_brief_review_checklist(exported).to_dict()
    first_json = json.dumps(first, separators=(",", ":"))
    second_json = json.dumps(second, separators=(",", ":"))

    assert first == second == _EXPECTED_REVIEW_DICT
    assert first_json == second_json == _EXPECTED_REVIEW_JSON
    assert first_json.encode("utf-8") == _EXPECTED_REVIEW_JSON.encode("utf-8")
    assert tuple(first) == tuple(_EXPECTED_REVIEW_DICT)


def test_review_serialization_stays_primitive_and_list_based() -> None:
    exported = _export_fixture()
    checklist = build_advisory_operating_brief_review_checklist(exported)
    payload = checklist.to_dict()

    assert isinstance(checklist.forbidden_capital_authority_fields, tuple)
    assert isinstance(checklist.findings, tuple)
    assert isinstance(payload["forbidden_capital_authority_fields"], list)
    assert isinstance(payload["findings"], list)
    assert payload["forbidden_capital_authority_fields"] == []
    assert payload["findings"] == []
    _assert_primitive_only(payload)
    _assert_primitive_only(exported.payload)


def test_injected_blocked_metadata_is_reported_only_as_review_findings() -> None:
    exported = _export_fixture()
    exported.payload[_s("port", "folio_authority")] = True
    exported.payload["review_note"] = _s("or", "der authority")
    before_payload = _freeze(exported.payload)

    checklist = build_advisory_operating_brief_review_checklist(exported)

    assert checklist.to_dict() == {
        **_EXPECTED_REVIEW_DICT,
        "advisory_only": False,
        "forbidden_capital_authority_fields": [
            _s("field:payload.port", "folio_authority"),
            "language:payload.review_note",
        ],
        "findings": [
            "advisory_only:false",
            _s(
                "forbidden_capital_authority_fields:field:payload.port",
                "folio_authority",
            ),
            "forbidden_capital_authority_fields:language:payload.review_note",
        ],
    }
    assert _freeze(exported.payload) == before_payload


def test_payload_non_claim_terms_are_negative_and_metadata_only() -> None:
    exported = _export_fixture()
    non_claim_lists = _non_claim_lists(exported.payload)
    blocked_field_paths = _blocked_payload_field_paths(exported.payload, "payload")
    blocked_strings = _blocked_payload_strings(exported.payload, "payload")

    assert non_claim_lists == (
        [*_EXPECTED_NON_CLAIMS],
        [*_EXPECTED_NON_CLAIMS],
        [*_EXPECTED_NON_CLAIMS],
        [*_EXPECTED_NON_CLAIMS],
    )
    assert blocked_field_paths == ()
    for path, value in blocked_strings:
        assert ".non_claims[" in path or path.startswith("payload.non_claims[")
        assert value.startswith("not ")


def test_regression_module_has_guarded_imports_and_calls() -> None:
    imports = _import_references(_tree())
    call_names = _call_names(_tree())

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_regression_module_literals_have_no_unasserted_scope_terms() -> None:
    allowed_literals = {
        "forbidden_capital_authority_fields",
        "forbidden_capital_authority_fields:language:payload.review_note",
    }

    for literal in _string_literals(_tree()):
        if literal in allowed_literals:
            continue
        for term in _blocked_literal_terms():
            assert not _contains_term(literal.lower(), term)


def _export_fixture() -> AdvisoryOperatingBriefExport:
    return export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )


def _export_evidence(payload: dict[str, object]) -> dict[str, object]:
    candidate_brief = _single_candidate_brief_payload(payload)
    section = _single_section_payload(payload)
    item = _single_item_payload(payload)

    return {
        "operating_brief_type": payload["operating_brief_type"],
        "operating_status": payload["status"],
        "operating_limitations": payload["limitations"],
        "operating_non_claims": payload["non_claims"],
        "candidate_research_brief_count": payload["candidate_research_brief_count"],
        "candidate_brief_type": candidate_brief["brief_type"],
        "candidate_brief_status": candidate_brief["status"],
        "candidate_brief_limitations": candidate_brief["limitations"],
        "candidate_brief_non_claims": candidate_brief["non_claims"],
        "section_count": candidate_brief["section_count"],
        "section_type": section["section_type"],
        "section_status": section["status"],
        "section_limitations": section["limitations"],
        "section_non_claims": section["non_claims"],
        "item_count": section["item_count"],
        "item_type": item["item_type"],
        "item_status": item["status"],
        "item_limitations": item["limitations"],
        "item_non_claims": item["non_claims"],
        "item_package_fingerprint": item["package_fingerprint"],
        "item_package_snapshot_id": item["package_snapshot_id"],
        "item_result_snapshot_manifest_fixture_id": (
            item["result_snapshot_manifest_fixture_id"]
        ),
        "item_result_snapshot_manifest_checksum": (
            item["result_snapshot_manifest_checksum"]
        ),
        "item_summary_points": item["summary_points"],
    }


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


def _non_claim_lists(value: object) -> tuple[list[object], ...]:
    values: list[list[object]] = []
    if isinstance(value, dict):
        non_claims = value.get("non_claims")
        if isinstance(non_claims, list):
            values.append(non_claims)
        for nested_value in value.values():
            values.extend(_non_claim_lists(nested_value))
    elif isinstance(value, list):
        for nested_value in value:
            values.extend(_non_claim_lists(nested_value))
    return tuple(values)


def _blocked_payload_field_paths(value: object, path: str) -> tuple[str, ...]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}"
            if _has_blocked_term(key, _blocked_field_terms()):
                paths.append(nested_path)
            paths.extend(_blocked_payload_field_paths(nested_value, nested_path))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            paths.extend(
                _blocked_payload_field_paths(nested_value, f"{path}[{index}]")
            )
    return tuple(paths)


def _blocked_payload_strings(
    value: object,
    path: str,
) -> tuple[tuple[str, str], ...]:
    strings: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            strings.extend(_blocked_payload_strings(nested_value, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            strings.extend(_blocked_payload_strings(nested_value, f"{path}[{index}]"))
    elif isinstance(value, str) and _has_blocked_term(value, _blocked_literal_terms()):
        strings.append((path, value))
    return tuple(strings)


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return tuple((key, _freeze(nested_value)) for key, nested_value in value.items())
    if isinstance(value, list):
        return tuple(_freeze(nested_value) for nested_value in value)
    return value


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


def _source_text() -> str:
    return inspect.getsource(sys.modules[__name__])


def _tree() -> ast.AST:
    return ast.parse(_source_text())


def _import_references(tree: ast.AST) -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(tree):
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


def _call_names(tree: ast.AST) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _string_literals(tree: ast.AST) -> tuple[str, ...]:
    return tuple(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )


def _has_blocked_term(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(_contains_term(lowered, term) for term in terms)


def _contains_term(text: str, term: str) -> bool:
    start = 0
    while True:
        index = text.find(term, start)
        if index < 0:
            return False

        before_index = index - 1
        after_index = index + len(term)
        before = text[before_index] if before_index >= 0 else ""
        after = text[after_index] if after_index < len(text) else ""
        if not _is_name_character(before) and not _is_name_character(after):
            return True

        start = index + 1


def _is_name_character(value: str) -> bool:
    return value.isalnum()


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
        _s("al", "paca_", "tra", "de_a", "pi"),
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


def _blocked_field_terms() -> tuple[str, ...]:
    return (
        _s("acc", "ount"),
        _s("act", "ion"),
        _s("app", "roval"),
        _s("app", "roved"),
        _s("bench", "mark"),
        _s("bro", "ker"),
        _s("ca", "sh"),
        _s("fi", "ll"),
        _s("live", "_authorized"),
        _s("live", "_probe", "_eligible"),
        _s("or", "der"),
        _s("port", "folio"),
        _s("allo", "cation"),
        _s("po", "sition"),
        _s("prior", "ity"),
        _s("prior", "itized"),
        _s("ra", "nk"),
        _s("reco", "mmendation"),
        _s("rea", "dy"),
        _s("run", "time"),
        _s("sco", "re"),
        _s("sig", "nal"),
        _s("stra", "tegy"),
        _s("trad", "able"),
        _s("tra", "de"),
        _s("tra", "ding", "_readiness"),
    )


def _blocked_literal_terms() -> tuple[str, ...]:
    return (
        _s("act", "ion"),
        _s("app", "roval"),
        _s("app", "roved"),
        _s("bench", "mark"),
        _s("bro", "ker"),
        _s("ca", "sh"),
        _s("co", "st"),
        _s("fi", "ll"),
        _s("or", "der"),
        _s("port", "folio"),
        _s("allo", "cation"),
        _s("po", "sition"),
        _s("prior", "itize"),
        _s("prior", "itized"),
        _s("ra", "nk"),
        _s("reco", "mmend"),
        _s("run", "time"),
        _s("sco", "re"),
        _s("sig", "nal"),
        _s("stra", "tegy"),
        _s("tra", "ding"),
        _s("tra", "ding auth", "ority"),
        _s("tra", "de"),
    )
