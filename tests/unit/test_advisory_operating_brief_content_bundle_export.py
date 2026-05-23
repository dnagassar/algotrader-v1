from __future__ import annotations

import ast
import json
import re
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

import algotrader.research as research_package
from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    AdvisoryOperatingBriefContentBundleExport,
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
    expected_synthetic_advisory_operating_brief_content_bundle_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_content_bundle_export.py"
)
_EXPECTED_PAYLOAD = expected_synthetic_advisory_operating_brief_content_bundle_dict()
_EXPECTED_JSON_TEXT = json.dumps(
    _EXPECTED_PAYLOAD,
    sort_keys=True,
    separators=(",", ":"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "json",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief_content_bundle",
    "algotrader.research.advisory_operating_brief_content_bundle_renderer",
}
_ALLOWED_CALL_NAMES = {
    "AdvisoryOperatingBriefContentBundleExport",
    "ValidationError",
    "bundle.to_dict",
    "dataclass",
    "json.dumps",
    "render_advisory_operating_brief_content_bundle_text",
    "type",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "argparse",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.dashboard",
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
    "click",
    _s("data", "base"),
    "duckdb",
    _s("ht", "tp"),
    "httpx",
    "ipynb",
    "joblib",
    "langchain",
    "langgraph",
    _s("l", "lm"),
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
    _s("sche", "dule"),
    "sklearn",
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
    "json.load",
    "json.loads",
    "load",
    "loads",
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
    "render_advisory_operating_brief_text",
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
_FORBIDDEN_AUTHORITY_FIELDS = {
    "account",
    "accounts",
    "approved",
    _s("bro", "ker"),
    _s("bro", "kers"),
    "buy",
    "sell",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _s("or", "der"),
    _s("or", "ders"),
    "paper_eligible",
    _s("port", "folio"),
    _s("port", "folios"),
    _s("allo", "cation"),
    _s("allo", "cations"),
    _s("allo", "cation_authority"),
    _s("or", "der_authority"),
    _s("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_EXACT_LITERALS = {
    "account",
    "accounts",
    "approved",
    "buy",
    "sell",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    "paper_eligible",
    _s("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_SOURCE_TOKENS = (
    "paper_eligible",
    "live_probe_eligible",
    "live_authorized",
    "trading_ready",
    "approved",
    "buy",
    "sell",
    "hold",
    _s("allo", "cation"),
    _s("or", "der"),
    _s("bro", "ker"),
    "account",
    _s("port", "folio"),
    _s("tra", "ding_authority"),
)
_FORBIDDEN_STATE_TEXT_TOKENS = (
    "paper_eligible",
    "live_probe_eligible",
    "live_authorized",
    "trading_ready",
    "approved",
    "buy",
    "sell",
    "hold",
)


def test_valid_export_from_phase_162_synthetic_content_bundle_fixture() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    exported = export_advisory_operating_brief_content_bundle(bundle)

    assert isinstance(exported, AdvisoryOperatingBriefContentBundleExport)
    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.rendered_text == (
        render_advisory_operating_brief_content_bundle_text(bundle)
    )


def test_export_object_is_frozen_slotted_and_has_no_from_dict() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    assert hasattr(AdvisoryOperatingBriefContentBundleExport, "__slots__")
    assert tuple(AdvisoryOperatingBriefContentBundleExport.__slots__) == (
        "payload",
        "json_text",
        "rendered_text",
    )
    assert not hasattr(exported, "__dict__")
    assert not hasattr(AdvisoryOperatingBriefContentBundleExport, "from_dict")
    assert "from_dict" not in _function_names()
    with pytest.raises(FrozenInstanceError):
        exported.rendered_text = "edited"


def test_export_fields_are_metadata_only_and_pinned() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    assert tuple(field.name for field in fields(AdvisoryOperatingBriefContentBundleExport)) == (
        "payload",
        "json_text",
        "rendered_text",
    )
    assert tuple(exported.payload) == tuple(_EXPECTED_PAYLOAD)
    assert exported.payload == _EXPECTED_PAYLOAD
    assert _export_ast_fields() == {"payload", "json_text", "rendered_text"}
    assert _export_return_keyword_names() == {"payload", "json_text", "rendered_text"}


def test_payload_equals_bundle_to_dict_and_is_primitive_only() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    exported = export_advisory_operating_brief_content_bundle(bundle)

    assert exported.payload == bundle.to_dict()
    assert exported.payload == _EXPECTED_PAYLOAD
    _assert_primitive_only(exported.payload)


def test_exact_compact_json_text_is_pinned_and_round_trips_to_payload() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.json_text == json.dumps(
        exported.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert exported.json_text != json.dumps(exported.payload, sort_keys=True)
    assert exported.json_text.startswith('{"authority":"advisory_only"')
    assert json.loads(exported.json_text) == exported.payload


def test_rendered_text_matches_phase_163_renderer_output() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    exported = export_advisory_operating_brief_content_bundle(bundle)
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert exported.rendered_text == rendered
    assert exported.rendered_text.startswith("Advisory Operating Brief Content Bundle")
    assert tuple(exported.rendered_text.splitlines()) == tuple(rendered.splitlines())


def test_repeated_export_is_byte_for_byte_deterministic() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    first = export_advisory_operating_brief_content_bundle(bundle)
    second = export_advisory_operating_brief_content_bundle(bundle)

    assert first == second
    assert first.payload is not second.payload
    assert first.json_text == second.json_text == _EXPECTED_JSON_TEXT
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert first.rendered_text == second.rendered_text
    assert first.rendered_text.encode("utf-8") == second.rendered_text.encode("utf-8")


def test_payload_is_isolated_from_caller_payload_mutation() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    caller_payload = bundle.to_dict()

    exported = export_advisory_operating_brief_content_bundle(bundle)
    _edit_payload(caller_payload)

    assert caller_payload != _EXPECTED_PAYLOAD
    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.json_text == _EXPECTED_JSON_TEXT


def test_export_payload_mutation_does_not_mutate_source_bundle() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    before_payload = bundle.to_dict()
    before_rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    exported = export_advisory_operating_brief_content_bundle(bundle)

    _edit_payload(exported.payload)

    assert exported.payload != before_payload
    assert bundle.to_dict() == before_payload
    assert render_advisory_operating_brief_content_bundle_text(bundle) == before_rendered
    assert export_advisory_operating_brief_content_bundle(bundle).payload == (
        before_payload
    )


def test_source_bundle_to_dict_before_and_after_export_is_unchanged() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    before = bundle.to_dict()

    export_advisory_operating_brief_content_bundle(bundle)
    export_advisory_operating_brief_content_bundle(bundle)

    assert bundle.to_dict() == before


@pytest.mark.parametrize("value", (object(), None, "not a bundle"))
def test_non_bundle_inputs_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError, match="AdvisoryOperatingBriefContentBundle"):
        export_advisory_operating_brief_content_bundle(value)


def test_malformed_bundle_like_objects_are_rejected() -> None:
    class BundleLike:
        bundle_type = "advisory_operating_brief_content_bundle"
        status = "candidate_only"
        authority = "advisory_only"
        capital_authority = False

        def to_dict(self) -> dict[str, object]:
            return {"bundle_type": self.bundle_type}

    with pytest.raises(ValidationError, match="exactly"):
        export_advisory_operating_brief_content_bundle(BundleLike())


def test_subclass_inputs_are_rejected() -> None:
    class BundleSubclass(AdvisoryOperatingBriefContentBundle):
        pass

    source = build_synthetic_advisory_operating_brief_content_bundle()
    subclass_bundle = BundleSubclass(
        bundle_type=source.bundle_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        title=source.title,
        summary=source.summary,
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        limitations=source.limitations,
        non_claims=source.non_claims,
    )

    with pytest.raises(ValidationError, match="exactly"):
        export_advisory_operating_brief_content_bundle(subclass_bundle)


def test_export_does_not_expose_restricted_states_as_authority() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )
    authority_values = _authority_values(exported.payload)
    rendered_authority_lines = _rendered_authority_lines(exported.rendered_text)

    assert authority_values
    assert set(authority_values.values()) == {"advisory_only", False}
    assert rendered_authority_lines
    assert set(rendered_authority_lines) == {
        "authority: advisory_only",
        "capital_authority: False",
        "source_status.authority: advisory_only",
        "source_status.capital_authority: False",
    }
    assert _payload_keys(exported.payload).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _rendered_field_names(exported.rendered_text).isdisjoint(
        _FORBIDDEN_AUTHORITY_FIELDS
    )
    for token in _FORBIDDEN_STATE_TEXT_TOKENS:
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", exported.json_text) is None
        assert re.search(
            rf"(?<![a-z0-9_]){token}(?![a-z0-9_])",
            exported.rendered_text.lower(),
        ) is None


def test_export_module_is_not_added_to_research_package_surface() -> None:
    assert not hasattr(
        research_package,
        "export_advisory_operating_brief_content_bundle",
    )
    assert not hasattr(research_package, "AdvisoryOperatingBriefContentBundleExport")


def test_export_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names <= _ALLOWED_CALL_NAMES
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_export_module_literals_add_no_actionable_authority_fields() -> None:
    literals = _string_literals()
    lowered_source = _source_text().lower()

    assert literals.isdisjoint(_FORBIDDEN_EXACT_LITERALS)
    assert _export_ast_fields().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _export_return_keyword_names().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    for token in _FORBIDDEN_SOURCE_TOKENS:
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", lowered_source) is None


def _edit_payload(payload: dict[str, object]) -> None:
    candidate_payload = payload["candidate_research_briefs"][0]
    eligibility_payload = payload["strategy_eligibility_briefs"][0]

    assert isinstance(candidate_payload, dict)
    assert isinstance(eligibility_payload, dict)
    payload["title"] = "edited copied payload"
    payload["limitations"].append("edited copied payload")
    candidate_payload["title"] = "edited copied payload"
    candidate_payload["limitations"].append("edited copied payload")
    eligibility_payload["title"] = "edited copied payload"
    eligibility_payload["non_claims"].append("not edited copied payload claim")


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


def _authority_values(value: object, prefix: str = "") -> dict[str, object]:
    if isinstance(value, dict):
        values: dict[str, object] = {}
        for key, nested_value in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key in {"authority", "capital_authority"}:
                values[path] = nested_value
            values.update(_authority_values(nested_value, path))
        return values

    if isinstance(value, list):
        values = {}
        for index, nested_value in enumerate(value):
            values.update(_authority_values(nested_value, f"{prefix}[{index}]"))
        return values

    return {}


def _rendered_authority_lines(text: str) -> tuple[str, ...]:
    return tuple(
        line
        for line in text.splitlines()
        if line.startswith("authority:")
        or line.startswith("capital_authority:")
        or line.startswith("source_status.authority:")
        or line.startswith("source_status.capital_authority:")
    )


def _rendered_field_names(text: str) -> set[str]:
    field_names: set[str] = set()
    for line in text.splitlines():
        if line.startswith("- ") or ":" not in line:
            continue
        field_names.add(line.split(":", maxsplit=1)[0])

    return field_names


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


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


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _export_ast_fields() -> set[str]:
    for node in ast.walk(_tree()):
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "AdvisoryOperatingBriefContentBundleExport"
        ):
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("AdvisoryOperatingBriefContentBundleExport was not found.")


def _export_return_keyword_names() -> set[str]:
    keyword_names: set[str] = set()

    for node in ast.walk(_tree()):
        if (
            isinstance(node, ast.Call)
            and _call_name(node.func) == "AdvisoryOperatingBriefContentBundleExport"
        ):
            keyword_names.update(
                keyword.arg for keyword in node.keywords if keyword.arg is not None
            )

    return keyword_names


def _string_literals() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
