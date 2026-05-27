from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re

import pytest

from algotrader.errors import ValidationError
from algotrader.research import (
    advisory_operating_brief_package_manifest_export as export_module,
)
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
    build_advisory_operating_brief_package,
)
from algotrader.research.advisory_operating_brief_package_manifest_export import (
    export_advisory_operating_brief_package_research_observation_manifest,
)
from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_HELPER_NAME = (
    "export_advisory_operating_brief_package_research_observation_manifest"
)
_OBSERVATION_NAME = "sma_return_research_pipeline_observation"
_ALLOWED_IMPORTS = {
    "__future__": ("annotations",),
    "algotrader.errors": ("ValidationError",),
    "algotrader.research.advisory_operating_brief_package": (
        "AdvisoryOperatingBriefPackage",
    ),
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.agent",
    "algotrader.agents",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.config",
    "algotrader.core.config",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    _s("algotrader.", "persist", "ence"),
    _s("algotrader.", "port", "folio"),
    "algotrader.research.advisory_operating_brief_package_renderer",
    "algotrader.research.advisory_operating_brief_package_synthetic",
    "algotrader.research.research_observation_manifest",
    "algotrader.research.research_observation_manifest_export",
    "algotrader.research.sma",
    "algotrader.risk",
    _s("algotrader.", "run", "time"),
    _s("algotrader.", "sche", "duler"),
    "algotrader.screener",
    _s("algotrader.", "sig", "nals"),
    "algotrader.storage",
    "algotrader.vendor",
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    "anthropic",
    "click",
    _s("data", "base"),
    "duckdb",
    "google.generativeai",
    "httpx",
    "joblib",
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("net", "work"),
    "openai",
    "os",
    _s("path", "lib"),
    _s("re", "quests"),
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    "add_argument",
    "add_parser",
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
    "export_research_observation_manifest_snapshot",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "load",
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
    "set_defaults",
    _s("so", "cket.create_", "con", "nection"),
    _s("so", "cket.", "so", "cket"),
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
_FORBIDDEN_SOURCE_TOKENS = (
    "aiohttp",
    _s("app", "roval"),
    _s("app", "roved"),
    _s("bro", "ker"),
    _s("cli"),
    "credential",
    "config",
    _s("fi", "ll"),
    "from_dict",
    "hashlib",
    "httpx",
    "json",
    _s("net", "work"),
    _s("or", "der"),
    "os.",
    _s("path"),
    _s("path", "lib"),
    _s("persist", "ence"),
    _s("port", "folio"),
    _s("read", "iness"),
    _s("recomm", "end"),
    _s("render", "er"),
    _s("re", "quests"),
    _s("run", "time"),
    _s("so", "cket"),
    "storage",
    "synthetic",
    _s("tra", "ding"),
    "urllib",
    "vendor",
)


def test_export_accepts_synthetic_preview_manifest_payload() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest = package.research_observation_manifest

    assert manifest is not None

    exported = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )

    assert exported == package.research_observation_manifest.to_dict()
    assert exported == manifest.to_dict()


def test_export_preserves_manifest_payload_unchanged() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest = package.research_observation_manifest

    assert manifest is not None

    before_payload = manifest.to_dict()
    exported = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )
    exported["entry_count"] = 99

    assert before_payload["entry_count"] == 1
    assert exported != before_payload
    assert manifest.to_dict() == before_payload
    assert package.research_observation_manifest is manifest


def test_export_does_not_rebuild_or_mutate_package_or_manifest() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest = package.research_observation_manifest

    assert manifest is not None

    package_identity = id(package)
    manifest_identity = id(manifest)
    before_package_payload = package.to_dict()
    before_manifest_payload = manifest.to_dict()

    exported = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )

    assert id(package) == package_identity
    assert id(package.research_observation_manifest) == manifest_identity
    assert package.research_observation_manifest is manifest
    assert package.to_dict() == before_package_payload
    assert manifest.to_dict() == before_manifest_payload
    assert exported == before_manifest_payload


def test_export_rejects_package_without_manifest() -> None:
    package = _package_without_manifest()

    assert type(package) is AdvisoryOperatingBriefPackage
    assert package.research_observation_manifest is None

    with pytest.raises(ValidationError, match="research_observation_manifest.*present"):
        export_advisory_operating_brief_package_research_observation_manifest(
            package
        )


def test_export_rejects_subclasses_lookalikes_and_non_package_objects() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()

    for value in (
        _package_subclass(package),
        _PackageLookalike(package),
        None,
        {},
        object(),
    ):
        with pytest.raises(ValidationError, match="AdvisoryOperatingBriefPackage"):
            export_advisory_operating_brief_package_research_observation_manifest(
                value
            )


def test_export_output_is_primitive_json_round_trippable() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    payload = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )

    _assert_primitive_only(payload)
    assert json.loads(_compact_sorted_json(payload)) == payload


def test_repeated_export_calls_are_byte_for_byte_deterministic() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    first_payload = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )
    second_payload = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )
    third_payload = export_advisory_operating_brief_package_research_observation_manifest(
        build_synthetic_advisory_operating_brief_package_preview()
    )

    first_json = _compact_sorted_json(first_payload)
    second_json = _compact_sorted_json(second_payload)
    third_json = _compact_sorted_json(third_payload)

    assert first_payload == second_payload == third_payload
    assert first_json == second_json == third_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert second_json.encode("utf-8") == third_json.encode("utf-8")


def test_exported_manifest_has_one_named_sma_pipeline_observation() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    payload = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )
    entries = _list(payload["entries"])

    assert payload["entry_count"] == 1
    assert len(entries) == 1
    assert _dict(entries[0])["observation_name"] == _OBSERVATION_NAME


def test_exported_manifest_digest_matches_included_sma_observation_payload() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    observation = package.sma_return_research_pipeline_observation
    payload = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )
    entry = _dict(_list(payload["entries"])[0])

    assert observation is not None

    observation_payload = observation.to_dict()

    assert entry["observation_name"] == _OBSERVATION_NAME
    assert entry["observation_type"] == observation_payload["observation_type"]
    assert entry["payload_key_count"] == len(observation_payload)
    assert entry["payload_digest_sha256"] == _payload_digest(observation_payload)


def test_module_exposes_only_one_public_helper_with_allowed_imports() -> None:
    imports = _import_details()

    assert export_module.__all__ == [_HELPER_NAME]
    assert _function_names() == {_HELPER_NAME}
    assert imports == _ALLOWED_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert all(not module_name.startswith("tests") for module_name in imports)


def test_module_has_no_forbidden_calls_tokens_or_import_fragments() -> None:
    source = _source_text()
    lowered_source = source.lower()

    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    for token in _FORBIDDEN_SOURCE_TOKENS:
        assert (
            re.search(
                rf"(?<![a-z0-9_]){re.escape(token.lower())}(?![a-z0-9_])",
                lowered_source,
            )
            is None
        )


class PackageSubclass(AdvisoryOperatingBriefPackage):
    pass


class _PackageLookalike:
    def __init__(self, source: AdvisoryOperatingBriefPackage) -> None:
        self.package_type = source.package_type
        self.research_observation_manifest = source.research_observation_manifest

    def to_dict(self) -> dict[str, object]:
        return {}


def _package_without_manifest() -> AdvisoryOperatingBriefPackage:
    return build_advisory_operating_brief_package(
        package_id="synthetic-advisory-operating-brief-package-001",
        title="Synthetic advisory operating brief package",
        summary="Synthetic metadata bundle for a future morning brief handoff",
        as_of="2026-05-24",
        content_bundle=build_synthetic_advisory_operating_brief_content_bundle_with_research_queue(),
    )


def _package_subclass(source: AdvisoryOperatingBriefPackage) -> PackageSubclass:
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
        sma_return_research_pipeline_observation=(
            source.sma_return_research_pipeline_observation
        ),
        research_observation_manifest=source.research_observation_manifest,
    )


def _payload_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        _compact_sorted_json(payload).encode("utf-8")
    ).hexdigest()


def _compact_sorted_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


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


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value


def _source_text() -> str:
    return inspect.getsource(export_module)


def _tree() -> ast.AST:
    return ast.parse(_source_text())


def _import_details() -> dict[str, tuple[str, ...]]:
    imports: dict[str, tuple[str, ...]] = {}

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.name] = ()
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports[node.module] = tuple(alias.name for alias in node.names)

    return imports


def _matching_imports(
    imports: dict[str, tuple[str, ...]],
    forbidden_prefixes: tuple[str, ...],
) -> list[str]:
    return [
        module_name
        for module_name in sorted(imports)
        if _matches_forbidden_prefix(module_name, forbidden_prefixes)
    ]


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
