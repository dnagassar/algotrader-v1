from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re

import pytest

from algotrader.errors import ValidationError
from algotrader.research import (
    advisory_operating_brief_package_audit_snapshot_export as export_module,
)
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
    build_advisory_operating_brief_package,
)
from algotrader.research.advisory_operating_brief_package_audit_snapshot_export import (
    export_advisory_operating_brief_package_audit_snapshot,
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


_HELPER_NAME = "export_advisory_operating_brief_package_audit_snapshot"
_OBSERVATION_NAME = "sma_return_research_pipeline_observation"
_EXPECTED_TOP_LEVEL_KEYS = [
    "snapshot_type",
    "schema_version",
    "package_type",
    "status",
    "authority",
    "capital_authority",
    "package_id",
    "as_of",
    "package_payload_digest_sha256",
    "manifest_payload_digest_sha256",
    "research_observation_manifest",
]
_ALLOWED_IMPORTS = {
    "__future__": ("annotations",),
    "hashlib": (),
    "json": (),
    "algotrader.errors": ("ValidationError",),
    "algotrader.research.advisory_operating_brief_package": (
        "AdvisoryOperatingBriefPackage",
    ),
    "algotrader.research.advisory_operating_brief_package_manifest_export": (
        "export_advisory_operating_brief_package_research_observation_manifest",
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
    "algotrader.data",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    _s("algotrader.", "persist", "ence"),
    _s("algotrader.", "port", "folio"),
    "algotrader.research.advisory_operating_brief_package_cli",
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
    "build_research_observation_manifest",
    "build_synthetic_advisory_operating_brief_package_preview",
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
    "time.monotonic",
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}
_EXPECTED_CALL_NAMES = {
    "ValidationError",
    "_compact_sorted_json",
    "_payload_digest",
    "encode",
    "export_advisory_operating_brief_package_research_observation_manifest",
    "hashlib.sha256",
    "hexdigest",
    "json.dumps",
    "package.to_dict",
    "type",
}
_FORBIDDEN_SOURCE_TOKENS = (
    "build_research_observation_manifest",
    "export_research_observation_manifest_snapshot",
    "algotrader.research.advisory_operating_brief_package_synthetic",
    "algotrader.research.research_observation_manifest",
    "algotrader.research.research_observation_manifest_export",
    "algotrader.research.sma",
    _s("al", "paca"),
    _s("bro", "ker"),
    _s("or", "der"),
    _s("fi", "ll"),
    _s("port", "folio"),
    "account",
    "credential",
    "secret",
    "token",
    _s("so", "cket"),
    _s("re", "quests"),
    "urllib",
    "httpx",
    "aiohttp",
    _s("path", "lib"),
    _s("op", "en("),
    _s("wri", "te"),
    "read_text",
    "from_dict",
    _s("app", "roved"),
    _s("read", "iness"),
    _s("recomm", "endation"),
    _s("tra", "ding_authority"),
    "capital_authority=True",
)
_FORBIDDEN_SNAPSHOT_VALUE_TOKENS = (
    _s("app", "roval"),
    _s("app", "roved"),
    _s("read", "iness"),
    _s("recomm", "end"),
    _s("tra", "ding_authority"),
    _s("tra", "ding authority"),
    _s("allo", "cation"),
    _s("or", "der"),
    _s("fi", "ll"),
    _s("bro", "ker"),
    _s("port", "folio"),
    "benchmark",
    "backtest",
)


def test_synthetic_package_preview_audit_snapshot_exports_successfully() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)

    assert list(snapshot) == _EXPECTED_TOP_LEVEL_KEYS
    assert snapshot["snapshot_type"] == (
        "advisory_operating_brief_package_audit_snapshot"
    )
    assert snapshot["schema_version"] == "1"
    assert snapshot["package_type"] == package.package_type
    assert snapshot["status"] == package.status
    assert snapshot["authority"] == package.authority
    assert snapshot["capital_authority"] == package.capital_authority
    assert snapshot["package_id"] == package.package_id
    assert snapshot["as_of"] == package.as_of


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
            export_advisory_operating_brief_package_audit_snapshot(value)


def test_export_rejects_package_without_research_observation_manifest() -> None:
    package = _package_without_manifest()

    assert type(package) is AdvisoryOperatingBriefPackage
    assert package.research_observation_manifest is None

    with pytest.raises(ValidationError, match="research_observation_manifest.*present"):
        export_advisory_operating_brief_package_audit_snapshot(package)


def test_snapshot_manifest_and_digests_match_recomputed_payloads() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest_payload = (
        export_advisory_operating_brief_package_research_observation_manifest(
            package
        )
    )
    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)

    assert snapshot["research_observation_manifest"] == manifest_payload
    assert snapshot["package_payload_digest_sha256"] == _payload_digest(
        package.to_dict()
    )
    assert snapshot["manifest_payload_digest_sha256"] == _payload_digest(
        manifest_payload
    )
    assert _is_lowercase_sha256(snapshot["package_payload_digest_sha256"])
    assert _is_lowercase_sha256(snapshot["manifest_payload_digest_sha256"])


def test_snapshot_output_is_primitive_json_round_trippable() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)

    _assert_primitive_only(snapshot)
    assert json.loads(_compact_sorted_json(snapshot)) == snapshot


def test_repeated_exports_from_equivalent_synthetic_packages_are_byte_stable() -> None:
    first = export_advisory_operating_brief_package_audit_snapshot(
        build_synthetic_advisory_operating_brief_package_preview()
    )
    second = export_advisory_operating_brief_package_audit_snapshot(
        build_synthetic_advisory_operating_brief_package_preview()
    )
    first_json = _compact_sorted_json(first)
    second_json = _compact_sorted_json(second)

    assert first == second
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_export_does_not_mutate_package_or_manifest() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest = package.research_observation_manifest

    assert manifest is not None

    package_identity = id(package)
    manifest_identity = id(manifest)
    before_package_payload = package.to_dict()
    before_manifest_payload = manifest.to_dict()

    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)

    assert id(package) == package_identity
    assert id(package.research_observation_manifest) == manifest_identity
    assert package.research_observation_manifest is manifest
    assert package.to_dict() == before_package_payload
    assert manifest.to_dict() == before_manifest_payload
    assert snapshot["research_observation_manifest"] == before_manifest_payload


def test_snapshot_includes_one_named_manifest_entry() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)
    manifest_payload = _dict(snapshot["research_observation_manifest"])
    entries = _list(manifest_payload["entries"])

    assert manifest_payload["entry_count"] == 1
    assert len(entries) == 1
    assert [_dict(entry)["observation_name"] for entry in entries] == [
        _OBSERVATION_NAME
    ]


def test_snapshot_does_not_imply_recommendation_readiness_or_trading_behavior() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)
    flattened_values = "\n".join(_flatten_string_values(snapshot)).lower()

    assert snapshot["authority"] == "advisory_only"
    assert snapshot["capital_authority"] is False
    for token in _FORBIDDEN_SNAPSHOT_VALUE_TOKENS:
        assert token not in flattened_values


def test_module_exposes_one_public_helper_with_allowed_imports() -> None:
    tree = _tree()
    imports = _import_details()

    assert export_module.__all__ == [_HELPER_NAME]
    assert _module_all_from_tree(tree) == [_HELPER_NAME]
    assert _public_function_names_from_tree(tree) == [_HELPER_NAME]
    assert _function_parameter_names(_function_def_from_tree(tree, _HELPER_NAME)) == (
        "package",
    )
    assert imports == _ALLOWED_IMPORTS
    assert _matching_imports(set(imports), _FORBIDDEN_IMPORT_PREFIXES) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_module_uses_phase_263_helper_and_no_forbidden_dependency_surfaces() -> None:
    source = _source_text()
    calls = _call_names()

    assert calls == _EXPECTED_CALL_NAMES
    assert calls.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert _forbidden_source_token_matches(source, _FORBIDDEN_SOURCE_TOKENS) == []
    assert _helper_returns_snapshot_with_expected_keys(
        _function_def_from_tree(_tree(), _HELPER_NAME)
    )


class PackageSubclass(AdvisoryOperatingBriefPackage):
    pass


class _PackageLookalike:
    def __init__(self, source: AdvisoryOperatingBriefPackage) -> None:
        self.package_type = source.package_type
        self.status = source.status
        self.authority = source.authority
        self.capital_authority = source.capital_authority
        self.package_id = source.package_id
        self.as_of = source.as_of
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


def _is_lowercase_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


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


def _flatten_string_values(value: object) -> list[str]:
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_flatten_string_values(item))
        return strings

    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(_flatten_string_values(item))
        return strings

    if isinstance(value, str):
        return [value]

    return []


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


def _module_all_from_tree(tree: ast.AST) -> list[str]:
    for node in tree.body if isinstance(tree, ast.Module) else ():
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return []
        return [
            item.value
            for item in node.value.elts
            if isinstance(item, ast.Constant) and type(item.value) is str
        ]

    return []


def _public_function_names_from_tree(tree: ast.AST) -> list[str]:
    if not isinstance(tree, ast.Module):
        return []

    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _function_def_from_tree(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node

    raise AssertionError(f"missing function {name}")


def _function_parameter_names(node: ast.FunctionDef) -> tuple[str, ...]:
    args = node.args

    assert args.posonlyargs == []
    assert args.defaults == []
    assert args.vararg is None
    assert args.kwonlyargs == []
    assert args.kw_defaults == []
    assert args.kwarg is None

    return tuple(arg.arg for arg in args.args)


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


def _matching_imports(
    imports: set[str],
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


def _forbidden_source_token_matches(
    source: str,
    tokens: tuple[str, ...],
) -> list[str]:
    matches: list[str] = []

    for token in tokens:
        if _source_contains_token(source, token):
            matches.append(token)

    return matches


def _source_contains_token(source: str, token: str) -> bool:
    lowered_token = token.lower()

    for line in source.splitlines():
        lowered_line = line.lower()
        if _line_contains_token(lowered_line, lowered_token):
            return True

    return False


def _line_contains_token(lowered_line: str, token: str) -> bool:
    if re.match(r"^[a-z0-9_]+$", token):
        return re.search(
            rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])",
            lowered_line,
        ) is not None

    return token in lowered_line


def _helper_returns_snapshot_with_expected_keys(node: ast.FunctionDef) -> bool:
    return_node = _single_return_node(node)

    return (
        isinstance(return_node.value, ast.Dict)
        and [
            key.value
            for key in return_node.value.keys
            if isinstance(key, ast.Constant) and type(key.value) is str
        ]
        == _EXPECTED_TOP_LEVEL_KEYS
    )


def _single_return_node(node: ast.FunctionDef) -> ast.Return:
    return_nodes = [
        statement for statement in node.body if isinstance(statement, ast.Return)
    ]

    assert len(return_nodes) == 1

    return return_nodes[0]
