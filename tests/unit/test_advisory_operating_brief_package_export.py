from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import inspect
import json
import re

import pytest

from algotrader.errors import ValidationError
from algotrader.research import advisory_operating_brief_package_export as export_module
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_export import (
    AdvisoryOperatingBriefPackageExport,
    export_advisory_operating_brief_package,
)
from algotrader.research.advisory_operating_brief_package_renderer import (
    render_advisory_operating_brief_package_text,
)
from tests.fixtures.advisory_operating_brief_package import (
    build_synthetic_advisory_operating_brief_package,
    expected_synthetic_advisory_operating_brief_package_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_PAYLOAD = expected_synthetic_advisory_operating_brief_package_dict()
_EXPECTED_JSON_TEXT = json.dumps(
    _EXPECTED_PAYLOAD,
    sort_keys=True,
    separators=(",", ":"),
)
_EXPECTED_RENDERED_TEXT = render_advisory_operating_brief_package_text(
    build_synthetic_advisory_operating_brief_package()
)
_EXPECTED_FIELD_NAMES = ("payload", "json_text", "rendered_text")
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "json",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief_package",
    "algotrader.research.advisory_operating_brief_package_renderer",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "argparse",
    _s("algotrader.", "back", "test"),
    _s("algotrader.", "back", "testing"),
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    _s("algotrader.", "dash", "board"),
    _s("algotrader.", "data", "base"),
    "algotrader.execution",
    _s("algotrader.", "l", "lm"),
    _s("algotrader.", "l", "lms"),
    _s("algotrader.", "m", "l"),
    "algotrader.orchestration",
    _s("algotrader.", "persist", "ence"),
    _s("algotrader.", "port", "folio"),
    "algotrader.risk",
    _s("algotrader.", "run", "time"),
    _s("algotrader.", "sche", "duler"),
    "algotrader.screener",
    _s("algotrader.", "sig", "nals"),
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    "anthropic",
    "click",
    _s("cre", "dential"),
    _s("data", "base"),
    "duckdb",
    _s("ht", "tp"),
    "httpx",
    "ipynb",
    "joblib",
    "keras",
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("mas", "sive"),
    _s("net", "work"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    _s("path", "lib"),
    _s("poly", "gon"),
    _s("poly", "gon_a", "pi_client"),
    _s("quant", "connect"),
    _s("re", "quests"),
    _s("sche", "dule"),
    _s("sk", "learn"),
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "xgboost",
    _s("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    "build_parser",
    _s("cli", "ent"),
    _s("con", "nect"),
    _s("create_", "or", "der"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "exists",
    "export_advisory_operating_brief",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    "importlib.import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "main",
    "mkdir",
    _s("op", "en"),
    "os.environ.get",
    "os.getenv",
    "parse_args",
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
    _s("so", "cket", ".", "so", "cket"),
    "stat",
    _s("sub", "mit_", "or", "der"),
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}
_FORBIDDEN_SOURCE_TERMS = (
    _s("acc", "ount"),
    _s("acc", "ounts"),
    _s("ag", "ent"),
    _s("allo", "cation"),
    _s("app", "roval"),
    _s("app", "roved"),
    _s("back", "testing"),
    _s("bro", "ker"),
    _s("cre", "dential"),
    _s("dash", "board"),
    _s("data source app", "roval"),
    _s("exe", "cution read", "iness"),
    _s("fi", "ll"),
    _s("fi", "lls"),
    _s("li", "ve"),
    _s("live_", "authorized"),
    _s("live_", "probe_eligible"),
    _s("l", "lm"),
    _s("m", "l"),
    _s("methodology app", "roval"),
    _s("n", "et", "work"),
    _s("note", "book"),
    _s("or", "der"),
    _s("or", "ders"),
    _s("pa", "per"),
    _s("paper_", "eligible"),
    _s("port", "folio"),
    _s("port", "folio mutation"),
    _s("ran", "king"),
    _s("read", "iness"),
    _s("recomm", "endation"),
    _s("risk app", "roval"),
    _s("run", "time"),
    _s("sche", "duler"),
    _s("sco", "ring"),
    _s("sig", "nal"),
    _s("so", "cket"),
    _s("strategy exe", "cution"),
    _s("tra", "ding authority"),
    _s("tra", "ding_ready"),
    _s("tra", "ding-ready"),
    _s("tra", "ding_authority"),
    _s("ven", "dor"),
)
_AUTHORITY_LANGUAGE_TOKENS = (
    "approval",
    "approved",
    _s("recomm", "end"),
    "ranking",
    "scoring",
    "paper",
    "live",
    "readiness",
    "actionable",
    _s("allo", "cation"),
    _s("or", "der"),
    _s("bro", "ker"),
    "account",
    _s("port", "folio"),
    "capital authority",
    "trading authority",
    "trading ready",
    "trading-ready",
    "trading_ready",
)
_NEGATIVE_TEXT_PREFIXES = (
    "not ",
    "no ",
    "does not ",
    "do not ",
    "without ",
    "non-",
)


def test_export_builder_accepts_phase_189_fixture_and_matches_package_views() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    source_bundle = package.content_bundle
    before_payload = package.to_dict()
    before_bundle_export_payload = _primitive_copy(package.content_bundle_export.payload)
    before_bundle_export_rendered = package.content_bundle_export.rendered_text

    exported = export_advisory_operating_brief_package(package)

    assert type(package) is AdvisoryOperatingBriefPackage
    assert type(exported) is AdvisoryOperatingBriefPackageExport
    assert exported.payload == package.to_dict() == before_payload == _EXPECTED_PAYLOAD
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.json_text == json.dumps(
        exported.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert json.loads(exported.json_text) == exported.payload
    assert exported.rendered_text == _EXPECTED_RENDERED_TEXT
    assert exported.rendered_text == render_advisory_operating_brief_package_text(
        package
    )
    assert package.to_dict() == before_payload
    assert package.content_bundle is source_bundle
    assert package.content_bundle_export.payload == before_bundle_export_payload
    assert package.content_bundle_export.rendered_text == before_bundle_export_rendered


def test_repeated_exports_are_byte_for_byte_deterministic() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    before_payload = package.to_dict()

    first = export_advisory_operating_brief_package(package)
    second = export_advisory_operating_brief_package(package)
    third = export_advisory_operating_brief_package(
        build_synthetic_advisory_operating_brief_package()
    )

    assert first == second == third
    assert first.payload == second.payload == third.payload == _EXPECTED_PAYLOAD
    assert first.json_text == second.json_text == third.json_text == _EXPECTED_JSON_TEXT
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert second.json_text.encode("utf-8") == third.json_text.encode("utf-8")
    assert first.rendered_text == second.rendered_text == third.rendered_text
    assert first.rendered_text.encode("utf-8") == second.rendered_text.encode("utf-8")
    assert second.rendered_text.encode("utf-8") == third.rendered_text.encode("utf-8")
    assert json.dumps(first.payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    ) == json.dumps(second.payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    assert package.to_dict() == before_payload == _EXPECTED_PAYLOAD


def test_export_payload_access_returns_stable_primitive_copies() -> None:
    exported = export_advisory_operating_brief_package(
        build_synthetic_advisory_operating_brief_package()
    )

    first_payload = exported.payload
    second_payload = exported.payload
    _change_payload_copy(first_payload)

    assert first_payload != _EXPECTED_PAYLOAD
    assert second_payload == _EXPECTED_PAYLOAD
    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.payload is not exported.payload
    assert exported.payload is not first_payload
    assert exported.payload is not second_payload
    assert json.loads(exported.json_text) == exported.payload
    assert exported.rendered_text == _EXPECTED_RENDERED_TEXT


def test_direct_construction_validates_copies_and_is_frozen_slotted() -> None:
    payload = _primitive_copy(_EXPECTED_PAYLOAD)
    exported = AdvisoryOperatingBriefPackageExport(
        payload=payload,
        json_text=_EXPECTED_JSON_TEXT,
        rendered_text=_EXPECTED_RENDERED_TEXT,
    )

    payload["title"] = "changed primitive constructor input"

    assert tuple(field.name for field in fields(AdvisoryOperatingBriefPackageExport)) == (
        _EXPECTED_FIELD_NAMES
    )
    assert hasattr(AdvisoryOperatingBriefPackageExport, "__slots__")
    assert not hasattr(exported, "__dict__")
    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.rendered_text == _EXPECTED_RENDERED_TEXT
    with pytest.raises(FrozenInstanceError):
        exported.json_text = "{}"
    with pytest.raises(FrozenInstanceError):
        exported.payload = {}


@pytest.mark.parametrize(
    ("payload", "json_text", "rendered_text", "match"),
    (
        ([], "[]", _EXPECTED_RENDERED_TEXT, "payload"),
        ({}, "{}", _EXPECTED_RENDERED_TEXT, "payload"),
        ({1: "value"}, '{"1":"value"}', _EXPECTED_RENDERED_TEXT, "payload"),
        ({"nested": {"bad": object()}}, "{}", _EXPECTED_RENDERED_TEXT, "primitive"),
        (
            {"nested": ("not", "primitive")},
            '{"nested":["not","primitive"]}',
            _EXPECTED_RENDERED_TEXT,
            "primitive",
        ),
        (_EXPECTED_PAYLOAD, "", _EXPECTED_RENDERED_TEXT, "json_text"),
        (_EXPECTED_PAYLOAD, " {}", _EXPECTED_RENDERED_TEXT, "json_text"),
        (_EXPECTED_PAYLOAD, "not-json", _EXPECTED_RENDERED_TEXT, "json_text"),
        (
            _EXPECTED_PAYLOAD,
            json.dumps(_EXPECTED_PAYLOAD, sort_keys=True),
            _EXPECTED_RENDERED_TEXT,
            "json_text",
        ),
        (_EXPECTED_PAYLOAD, _EXPECTED_JSON_TEXT, "", "rendered_text"),
        (_EXPECTED_PAYLOAD, _EXPECTED_JSON_TEXT, " rendered", "rendered_text"),
        (_EXPECTED_PAYLOAD, _EXPECTED_JSON_TEXT, object(), "rendered_text"),
    ),
    ids=(
        "payload-list",
        "payload-empty",
        "payload-key",
        "payload-object",
        "payload-tuple",
        "json-empty",
        "json-leading-space",
        "json-invalid",
        "json-not-compact",
        "rendered-empty",
        "rendered-leading-space",
        "rendered-object",
    ),
)
def test_direct_construction_rejects_malformed_values(
    payload: object,
    json_text: object,
    rendered_text: object,
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        AdvisoryOperatingBriefPackageExport(
            payload=payload,
            json_text=json_text,
            rendered_text=rendered_text,
        )


@pytest.mark.parametrize(
    "value",
    (
        None,
        {},
        "package-lookalike",
    ),
)
def test_export_builder_rejects_non_package_inputs(value: object) -> None:
    if value == "package-lookalike":
        value = _PackageLookalike()

    with pytest.raises(ValidationError, match="AdvisoryOperatingBriefPackage"):
        export_advisory_operating_brief_package(value)


def test_export_builder_rejects_package_subclass_instances() -> None:
    package = _package_subclass(build_synthetic_advisory_operating_brief_package())

    with pytest.raises(ValidationError, match="AdvisoryOperatingBriefPackage"):
        export_advisory_operating_brief_package(package)


def test_no_from_dict_exists() -> None:
    exported = export_advisory_operating_brief_package(
        build_synthetic_advisory_operating_brief_package()
    )

    assert not hasattr(AdvisoryOperatingBriefPackageExport, "from_dict")
    assert not hasattr(exported, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()
    assert "from_dict" not in _source_text()


def test_exported_text_has_no_positive_actionable_authority_language() -> None:
    exported = export_advisory_operating_brief_package(
        build_synthetic_advisory_operating_brief_package()
    )
    values = (
        *_string_values(exported.payload),
        *exported.rendered_text.splitlines(),
    )

    for value in values:
        lowered = value.lower()
        if any(token in lowered for token in _AUTHORITY_LANGUAGE_TOKENS):
            assert _is_negative_advisory_text(lowered), value
    compact = exported.json_text.lower()
    assert '"approved"' not in compact
    assert '"paper"' not in compact
    assert '"live"' not in compact
    assert "trading-ready" not in compact
    assert "trading_ready" not in compact
    assert "actionable" not in compact


def test_production_export_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_production_export_has_no_forbidden_imports_calls_or_terms() -> None:
    imports = _import_references()
    call_names = _call_names()
    lowered_source = _source_text().lower()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    for term in _FORBIDDEN_SOURCE_TERMS:
        assert (
            re.search(
                rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])",
                lowered_source,
            )
            is None
        )


class PackageSubclass(AdvisoryOperatingBriefPackage):
    pass


class _PackageLookalike:
    def to_dict(self) -> dict[str, object]:
        return _primitive_copy(_EXPECTED_PAYLOAD)


def _package_subclass(
    source: AdvisoryOperatingBriefPackage,
) -> PackageSubclass:
    return PackageSubclass(
        package_type=source.package_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        package_id=source.package_id,
        title=source.title,
        summary=source.summary,
        as_of=source.as_of,
        content_bundle=source.content_bundle,
        content_bundle_export=source.content_bundle_export,
        limitations=source.limitations,
        non_claims=source.non_claims,
    )


def _change_payload_copy(payload: dict[str, object]) -> None:
    content_bundle = _dict(payload["content_bundle"])
    content_bundle_export = _dict(payload["content_bundle_export"])
    nested_export_payload = _dict(content_bundle_export["payload"])

    payload["title"] = "changed primitive export payload copy"
    _list(payload["limitations"]).append("changed primitive export payload copy")
    content_bundle["title"] = "changed primitive export payload copy"
    nested_export_payload["title"] = "changed primitive export payload copy"


def _primitive_copy(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _primitive_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_primitive_copy(item) for item in value]
    return value


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value


def _string_values(value: object) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(value, str):
        values.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            values.extend(_string_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_string_values(item))

    return tuple(values)


def _is_negative_advisory_text(value: str) -> bool:
    text = value[2:] if value.startswith("- ") else value
    return (
        text.startswith(_NEGATIVE_TEXT_PREFIXES)
        or " not " in text
        or " before any " in text
        or " absent" in text
        or " missing" in text
        or " unresolved" in text
    )


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


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
