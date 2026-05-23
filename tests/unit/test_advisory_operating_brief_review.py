from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import inspect
import json
import re
import sys

import pytest

import algotrader.research as research_package
import algotrader.research.advisory_operating_brief_cli as preview_module
import algotrader.research.advisory_operating_brief_review as review_module
from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_export import (
    AdvisoryOperatingBriefExport,
    export_advisory_operating_brief,
)
from algotrader.research.advisory_operating_brief_review import (
    AdvisoryOperatingBriefReviewChecklist,
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
_EXPECTED_VALID_DICT = {
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

_ALLOWED_MODULE_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief_export",
}
_ALLOWED_TEST_IMPORTS = {
    "__future__",
    "ast",
    "dataclasses",
    "inspect",
    "json",
    "re",
    "sys",
    "pytest",
    "algotrader.research",
    "algotrader.research.advisory_operating_brief_cli",
    "algotrader.research.advisory_operating_brief_export",
    "algotrader.research.advisory_operating_brief_review",
    "algotrader.errors",
    "tests.fixtures.advisory_operating_brief",
}


def test_valid_export_builds_review_checklist() -> None:
    exported = _export_fixture()

    checklist = build_advisory_operating_brief_review_checklist(exported)

    assert isinstance(checklist, AdvisoryOperatingBriefReviewChecklist)
    assert checklist.to_dict() == _EXPECTED_VALID_DICT


@pytest.mark.parametrize("value", (object(), None, "not an export", {}))
def test_builder_rejects_non_export_inputs(value: object) -> None:
    with pytest.raises(ValidationError, match="AdvisoryOperatingBriefExport"):
        build_advisory_operating_brief_review_checklist(value)


@pytest.mark.parametrize(
    "exported, message",
    (
        (
            AdvisoryOperatingBriefExport(
                payload=[],
                json_text="{}",
                rendered_text="text",
            ),
            "payload",
        ),
        (
            AdvisoryOperatingBriefExport(
                payload={"status": object()},
                json_text="{}",
                rendered_text="text",
            ),
            "primitive",
        ),
        (
            AdvisoryOperatingBriefExport(
                payload={"status": "candidate_only"},
                json_text="",
                rendered_text="text",
            ),
            "json_text",
        ),
        (
            AdvisoryOperatingBriefExport(
                payload={"status": "candidate_only"},
                json_text="{}",
                rendered_text="",
            ),
            "rendered_text",
        ),
    ),
)
def test_builder_rejects_malformed_export_inputs(
    exported: AdvisoryOperatingBriefExport,
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        build_advisory_operating_brief_review_checklist(exported)


def test_checklist_has_fixed_review_type_and_status() -> None:
    checklist = _review_fixture()

    assert checklist.review_type == "advisory_operating_brief_review_checklist"
    assert checklist.status == "candidate_only"
    with pytest.raises(ValidationError, match="review_type"):
        AdvisoryOperatingBriefReviewChecklist(
            review_type="changed",
            status="candidate_only",
            candidate_only=True,
            advisory_only=True,
            has_limitations=True,
            has_non_claims=True,
            has_fingerprint=True,
            has_provenance=True,
            forbidden_capital_authority_fields=(),
            findings=(),
        )
    with pytest.raises(ValidationError, match="status"):
        AdvisoryOperatingBriefReviewChecklist(
            review_type="advisory_operating_brief_review_checklist",
            status="changed",
            candidate_only=True,
            advisory_only=True,
            has_limitations=True,
            has_non_claims=True,
            has_fingerprint=True,
            has_provenance=True,
            forbidden_capital_authority_fields=(),
            findings=(),
        )


def test_checklist_detects_candidate_only_and_advisory_only_status() -> None:
    checklist = _review_fixture()

    assert checklist.candidate_only is True
    assert checklist.advisory_only is True

    exported = _export_fixture()
    exported.payload["status"] = "changed"
    changed = build_advisory_operating_brief_review_checklist(exported)

    assert changed.status == "candidate_only"
    assert changed.candidate_only is False
    assert "candidate_only:false" in changed.findings


def test_checklist_detects_limitations_and_non_claims() -> None:
    checklist = _review_fixture()

    assert checklist.has_limitations is True
    assert checklist.has_non_claims is True

    exported = _export_fixture()
    exported.payload["limitations"] = []
    exported.payload["non_claims"] = ["changed"]
    changed = build_advisory_operating_brief_review_checklist(exported)

    assert changed.has_limitations is False
    assert changed.has_non_claims is False
    assert "has_limitations:false" in changed.findings
    assert "has_non_claims:false" in changed.findings


def test_checklist_detects_phase_123_fingerprint() -> None:
    exported = _export_fixture()
    checklist = build_advisory_operating_brief_review_checklist(exported)

    assert checklist.has_fingerprint is True
    assert _SYNTHETIC_FIXTURE_DIGEST in _payload_strings(exported.payload)


def test_checklist_detects_phase_127_141_provenance_convention() -> None:
    exported = _export_fixture()
    checklist = build_advisory_operating_brief_review_checklist(exported)
    item_payload = _single_item_payload(exported.payload)

    assert checklist.has_provenance is True
    assert item_payload["result_snapshot_manifest_fixture_id"] == (
        _SYNTHETIC_FIXTURE_ID
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        _SYNTHETIC_FIXTURE_CHECKSUM
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{item_payload['package_fingerprint']}"
    )


def test_synthetic_preview_export_reports_no_forbidden_capital_authority_fields() -> None:
    checklist = _review_fixture()

    assert checklist.forbidden_capital_authority_fields == ()
    assert checklist.findings == ()


def test_injected_capital_authority_metadata_is_reported_as_findings_only() -> None:
    exported = _export_fixture()
    exported.payload[_s("port", "folio_authority")] = True
    exported.payload["review_note"] = _s("or", "der authority")
    before_payload = _freeze(exported.payload)

    checklist = build_advisory_operating_brief_review_checklist(exported)

    assert checklist.status == "candidate_only"
    assert checklist.advisory_only is False
    assert checklist.forbidden_capital_authority_fields == (
        _s("field:payload.port", "folio_authority"),
        "language:payload.review_note",
    )
    assert checklist.findings == (
        "advisory_only:false",
        _s(
            "forbidden_capital_authority_fields:field:payload.port",
            "folio_authority",
        ),
        "forbidden_capital_authority_fields:language:payload.review_note",
    )
    assert _freeze(exported.payload) == before_payload


def test_source_export_identity_is_preserved_if_referenced() -> None:
    exported = _export_fixture()
    checklist = build_advisory_operating_brief_review_checklist(exported)

    if hasattr(checklist, "source_export"):
        assert checklist.source_export is exported
    else:
        assert tuple(field.name for field in fields(checklist)) == (
            "review_type",
            "status",
            "candidate_only",
            "advisory_only",
            "has_limitations",
            "has_non_claims",
            "has_fingerprint",
            "has_provenance",
            "forbidden_capital_authority_fields",
            "findings",
        )


def test_builder_does_not_mutate_source_export_payload() -> None:
    exported = _export_fixture()
    before_payload = _freeze(exported.payload)

    build_advisory_operating_brief_review_checklist(exported)

    assert _freeze(exported.payload) == before_payload


def test_tuple_fields_are_immutable() -> None:
    checklist = _review_fixture()

    assert isinstance(checklist.forbidden_capital_authority_fields, tuple)
    assert isinstance(checklist.findings, tuple)
    with pytest.raises(AttributeError):
        checklist.findings.append("changed")
    with pytest.raises(FrozenInstanceError):
        checklist.status = "changed"


def test_to_dict_is_deterministic_and_primitive_only() -> None:
    checklist = _review_fixture()

    payload = checklist.to_dict()

    assert payload == _EXPECTED_VALID_DICT
    assert tuple(payload) == (
        "review_type",
        "status",
        "candidate_only",
        "advisory_only",
        "has_limitations",
        "has_non_claims",
        "has_fingerprint",
        "has_provenance",
        "forbidden_capital_authority_fields",
        "findings",
    )
    _assert_primitive_only(payload)
    assert json.dumps(payload, sort_keys=True, separators=(",", ":")) == json.dumps(
        _EXPECTED_VALID_DICT,
        sort_keys=True,
        separators=(",", ":"),
    )


def test_repeated_construction_produces_identical_dictionaries() -> None:
    exported = _export_fixture()

    first = build_advisory_operating_brief_review_checklist(exported).to_dict()
    second = build_advisory_operating_brief_review_checklist(exported).to_dict()

    assert first == second


def test_review_contract_does_not_change_cli_preview_behavior() -> None:
    before_text = preview_module.render_advisory_operating_brief_preview("text")
    before_json = preview_module.render_advisory_operating_brief_preview("json")

    build_advisory_operating_brief_review_checklist(_export_fixture())

    assert preview_module.render_advisory_operating_brief_preview("text") == before_text
    assert preview_module.render_advisory_operating_brief_preview("json") == before_json


def test_review_module_is_not_reexported_from_research_package() -> None:
    assert not hasattr(research_package, "AdvisoryOperatingBriefReviewChecklist")
    assert not hasattr(
        research_package,
        "build_advisory_operating_brief_review_checklist",
    )


def test_review_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references(_module_tree())
    call_names = _call_names(_module_tree())

    assert imports == _ALLOWED_MODULE_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_review_module_text_has_no_disallowed_literals() -> None:
    _assert_source_has_no_disallowed_literals(_module_source_text())


def test_review_test_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references(_test_tree())
    call_names = _call_names(_test_tree())

    assert imports == _ALLOWED_TEST_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_review_test_module_text_has_no_disallowed_literals() -> None:
    _assert_source_has_no_disallowed_literals(_test_source_text())


def _review_fixture() -> AdvisoryOperatingBriefReviewChecklist:
    return build_advisory_operating_brief_review_checklist(_export_fixture())


def _export_fixture() -> AdvisoryOperatingBriefExport:
    return export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )


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


def _module_source_text() -> str:
    return inspect.getsource(review_module)


def _test_source_text() -> str:
    return inspect.getsource(sys.modules[__name__])


def _module_tree() -> ast.AST:
    return ast.parse(_module_source_text())


def _test_tree() -> ast.AST:
    return ast.parse(_test_source_text())


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


def _assert_source_has_no_disallowed_literals(source: str) -> None:
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
