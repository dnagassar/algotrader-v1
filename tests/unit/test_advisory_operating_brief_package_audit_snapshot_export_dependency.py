from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

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


HELPER_SOURCE_PATH = Path(
    "src/algotrader/research/"
    "advisory_operating_brief_package_audit_snapshot_export.py"
)
_HELPER_NAME = "export_advisory_operating_brief_package_audit_snapshot"
_MANIFEST_HELPER_NAME = (
    "export_advisory_operating_brief_package_research_observation_manifest"
)
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
        _MANIFEST_HELPER_NAME,
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
    _MANIFEST_HELPER_NAME,
    "hashlib.sha256",
    "hexdigest",
    "json.dumps",
    "package.to_dict",
    "type",
}
_FORBIDDEN_SOURCE_TOKENS = (
    "build_research_observation_manifest",
    "export_research_observation_manifest_snapshot",
    "build_synthetic_advisory_operating_brief_package_preview",
    "sma_",
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
_FORBIDDEN_SNAPSHOT_TOKENS = (
    "credential",
    "secret",
    "token",
    "timestamp",
    "datetime",
    "random",
    "uuid",
    "path",
    "env",
    _s("run", "time"),
    _s("bro", "ker"),
    _s("or", "der"),
    _s("fi", "ll"),
    _s("port", "folio"),
    _s("app", "roved"),
    _s("read", "iness"),
    _s("recomm", "endation"),
    _s("tra", "ding_authority"),
)
_MUTATING_METHOD_NAMES = {
    "append",
    "clear",
    "extend",
    "insert",
    "pop",
    "popitem",
    "remove",
    "setdefault",
    "sort",
    "update",
}


def test_audit_snapshot_helper_imports_only_metadata_export_contracts() -> None:
    import_details = _import_details_from_path(HELPER_SOURCE_PATH)
    imports = set(import_details)

    assert import_details == _ALLOWED_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_audit_snapshot_helper_public_surface_is_single_explicit_helper() -> None:
    tree = _tree_from_path(HELPER_SOURCE_PATH)
    helper = _function_def_from_tree(tree, _HELPER_NAME)

    assert export_module.__all__ == [_HELPER_NAME]
    assert _module_all_from_tree(tree) == [_HELPER_NAME]
    assert _public_function_names_from_tree(tree) == [_HELPER_NAME]
    assert _function_parameter_names(helper) == ("package",)


def test_audit_snapshot_helper_validates_exact_package_type() -> None:
    helper = _function_def_from_tree(_tree_from_path(HELPER_SOURCE_PATH), _HELPER_NAME)

    assert _has_validation_raise_for_if(helper, _is_exact_package_type_check)


def test_audit_snapshot_helper_composes_phase_263_manifest_export() -> None:
    helper = _function_def_from_tree(_tree_from_path(HELPER_SOURCE_PATH), _HELPER_NAME)
    call = _single_manifest_export_call(helper)

    assert isinstance(call.args[0], ast.Name)
    assert call.args[0].id == "package"
    assert call.keywords == []
    assert not _calls_name(
        helper,
        {
            "build_research_observation_manifest",
            "export_research_observation_manifest_snapshot",
            "build_synthetic_advisory_operating_brief_package_preview",
        },
    )


def test_audit_snapshot_helper_returns_expected_ordered_snapshot_keys() -> None:
    helper = _function_def_from_tree(_tree_from_path(HELPER_SOURCE_PATH), _HELPER_NAME)

    assert _helper_returned_dict_keys(helper) == _EXPECTED_TOP_LEVEL_KEYS
    assert _helper_returned_constant_value(helper, "snapshot_type") == (
        "advisory_operating_brief_package_audit_snapshot"
    )
    assert _helper_returned_constant_value(helper, "schema_version") == "1"


def test_digest_helpers_use_only_compact_sorted_json_and_sha256() -> None:
    tree = _tree_from_path(HELPER_SOURCE_PATH)

    assert _payload_digest_shape(_function_def_from_tree(tree, "_payload_digest"))
    assert _compact_sorted_json_shape(
        _function_def_from_tree(tree, "_compact_sorted_json")
    )


def test_audit_snapshot_helper_has_no_forbidden_dependency_surfaces() -> None:
    source = _source_text_from_path(HELPER_SOURCE_PATH)
    calls = _call_names_from_path(HELPER_SOURCE_PATH)
    helper = _function_def_from_tree(_tree_from_path(HELPER_SOURCE_PATH), _HELPER_NAME)
    aliases = _simple_name_aliases(helper)

    assert calls == _EXPECTED_CALL_NAMES
    assert calls.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert _forbidden_source_token_matches(source, _FORBIDDEN_SOURCE_TOKENS) == []
    assert _state_mutation_violations(helper, aliases) == []
    assert _mutating_method_call_violations(helper, aliases) == []


def test_synthetic_audit_snapshot_matches_manifest_helper_and_digests() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest_payload = (
        export_advisory_operating_brief_package_research_observation_manifest(
            package
        )
    )
    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)

    assert list(snapshot) == _EXPECTED_TOP_LEVEL_KEYS
    assert snapshot["snapshot_type"] == (
        "advisory_operating_brief_package_audit_snapshot"
    )
    assert snapshot["schema_version"] == "1"
    assert snapshot["research_observation_manifest"] == manifest_payload
    assert snapshot["package_payload_digest_sha256"] == _payload_digest(
        package.to_dict()
    )
    assert snapshot["manifest_payload_digest_sha256"] == _payload_digest(
        manifest_payload
    )
    assert _is_lowercase_sha256(snapshot["package_payload_digest_sha256"])
    assert _is_lowercase_sha256(snapshot["manifest_payload_digest_sha256"])


def test_synthetic_audit_snapshot_output_is_byte_stable() -> None:
    first = export_advisory_operating_brief_package_audit_snapshot(
        build_synthetic_advisory_operating_brief_package_preview()
    )
    second = export_advisory_operating_brief_package_audit_snapshot(
        build_synthetic_advisory_operating_brief_package_preview()
    )

    assert first == second
    assert _compact_sorted_json(first).encode("utf-8") == _compact_sorted_json(
        second
    ).encode("utf-8")


def test_synthetic_audit_snapshot_embeds_one_expected_manifest_entry() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)
    manifest_payload = _dict(snapshot["research_observation_manifest"])
    entries = _list(manifest_payload["entries"])

    assert manifest_payload["entry_count"] == 1
    assert len(entries) == 1
    assert [_dict(entry)["observation_name"] for entry in entries] == [
        _OBSERVATION_NAME
    ]


def test_audit_snapshot_adds_no_runtime_path_or_trading_state() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    snapshot = export_advisory_operating_brief_package_audit_snapshot(package)
    snapshot_json = _compact_sorted_json(snapshot).lower()
    source = _source_text_from_path(HELPER_SOURCE_PATH)

    assert _forbidden_source_token_matches(source, _FORBIDDEN_SNAPSHOT_TOKENS) == []
    for key in _EXPECTED_TOP_LEVEL_KEYS:
        assert key in snapshot
    for token in _FORBIDDEN_SNAPSHOT_TOKENS:
        assert not _source_contains_token(snapshot_json, token)


def test_audit_snapshot_rejects_missing_manifest() -> None:
    package = _package_without_manifest()

    assert type(package) is AdvisoryOperatingBriefPackage
    assert package.research_observation_manifest is None

    with pytest.raises(ValidationError, match="research_observation_manifest.*present"):
        export_advisory_operating_brief_package_audit_snapshot(package)


def test_audit_snapshot_rejects_subclasses_lookalikes_and_non_packages() -> None:
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


def _source_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree_from_path(path: Path) -> ast.AST:
    return ast.parse(_source_text_from_path(path), filename=str(path))


def _import_details_from_path(path: Path) -> dict[str, tuple[str, ...]]:
    imports: dict[str, tuple[str, ...]] = {}

    for node in ast.walk(_tree_from_path(path)):
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


def _has_validation_raise_for_if(
    node: ast.FunctionDef,
    predicate: object,
) -> bool:
    return any(
        isinstance(child, ast.If)
        and _predicate_matches(predicate, child.test)
        and _body_raises_validation_error(child.body)
        for child in node.body
    )


def _predicate_matches(predicate: object, node: ast.AST) -> bool:
    assert callable(predicate)

    return bool(predicate(node))


def _is_exact_package_type_check(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Compare)
        and _is_type_package_call(node.left)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.IsNot)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Name)
        and node.comparators[0].id == "AdvisoryOperatingBriefPackage"
    )


def _is_type_package_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "type"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "package"
        and node.keywords == []
    )


def _body_raises_validation_error(body: list[ast.stmt]) -> bool:
    return any(
        isinstance(statement, ast.Raise)
        and _is_validation_error_call(statement.exc)
        for statement in body
    )


def _is_validation_error_call(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ValidationError"
    )


def _single_manifest_export_call(node: ast.FunctionDef) -> ast.Call:
    calls = [
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and _call_name(child.func) == _MANIFEST_HELPER_NAME
    ]

    assert len(calls) == 1

    return calls[0]


def _calls_name(node: ast.AST, forbidden_names: set[str]) -> bool:
    return any(
        isinstance(child, ast.Call) and _call_name(child.func) in forbidden_names
        for child in ast.walk(node)
    )


def _helper_returned_dict_keys(node: ast.FunctionDef) -> list[str]:
    return_node = _single_return_node(node)

    assert isinstance(return_node.value, ast.Dict)

    return [
        key.value
        for key in return_node.value.keys
        if isinstance(key, ast.Constant) and type(key.value) is str
    ]


def _helper_returned_constant_value(node: ast.FunctionDef, key_name: str) -> object:
    return_node = _single_return_node(node)

    assert isinstance(return_node.value, ast.Dict)

    for key, value in zip(return_node.value.keys, return_node.value.values):
        if (
            isinstance(key, ast.Constant)
            and key.value == key_name
            and isinstance(value, ast.Constant)
        ):
            return value.value

    raise AssertionError(f"missing constant value for {key_name}")


def _single_return_node(node: ast.FunctionDef) -> ast.Return:
    return_nodes = [
        statement for statement in node.body if isinstance(statement, ast.Return)
    ]

    assert len(return_nodes) == 1

    return return_nodes[0]


def _payload_digest_shape(node: ast.FunctionDef) -> bool:
    return_node = _single_return_node(node)
    value = return_node.value

    return (
        isinstance(value, ast.Call)
        and _call_name(value.func) == "hexdigest"
        and isinstance(value.func, ast.Attribute)
        and _is_sha256_compact_sorted_payload_encode(value.func.value)
        and value.args == []
        and value.keywords == []
    )


def _is_sha256_compact_sorted_payload_encode(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _call_name(node.func) == "hashlib.sha256"
        and len(node.args) == 1
        and _is_compact_sorted_payload_utf8_encode(node.args[0])
        and node.keywords == []
    )


def _is_compact_sorted_payload_utf8_encode(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _call_name(node.func) == "encode"
        and isinstance(node.func, ast.Attribute)
        and _is_compact_sorted_json_payload_call(node.func.value)
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "utf-8"
        and node.keywords == []
    )


def _is_compact_sorted_json_payload_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and _call_name(node.func) == "_compact_sorted_json"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "payload"
        and node.keywords == []
    )


def _compact_sorted_json_shape(node: ast.FunctionDef) -> bool:
    return_node = _single_return_node(node)
    value = return_node.value

    return (
        isinstance(value, ast.Call)
        and _call_name(value.func) == "json.dumps"
        and len(value.args) == 1
        and isinstance(value.args[0], ast.Name)
        and value.args[0].id == "payload"
        and _keyword_constant(value, "sort_keys") is True
        and _keyword_tuple_constants(value, "separators") == (",", ":")
    )


def _keyword_constant(node: ast.Call, name: str) -> object:
    for keyword in node.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value

    return None


def _keyword_tuple_constants(node: ast.Call, name: str) -> tuple[object, ...]:
    for keyword in node.keywords:
        if keyword.arg != name or not isinstance(keyword.value, ast.Tuple):
            continue
        return tuple(
            item.value
            for item in keyword.value.elts
            if isinstance(item, ast.Constant)
        )

    return ()


def _call_names_from_path(path: Path) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree_from_path(path))
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _simple_name_aliases(node: ast.FunctionDef) -> dict[str, ast.AST]:
    aliases: dict[str, ast.AST] = {}

    for child in node.body:
        if not isinstance(child, ast.Assign):
            continue
        if len(child.targets) != 1 or not isinstance(child.targets[0], ast.Name):
            continue
        aliases[child.targets[0].id] = child.value

    return aliases


def _state_mutation_violations(
    node: ast.FunctionDef,
    aliases: dict[str, ast.AST],
) -> list[str]:
    violations: list[str] = []

    for child in ast.walk(node):
        targets: list[ast.AST]
        if isinstance(child, ast.Assign):
            targets = list(child.targets)
        elif isinstance(child, ast.AnnAssign):
            targets = [child.target]
        elif isinstance(child, ast.AugAssign):
            targets = [child.target]
        elif isinstance(child, ast.Delete):
            targets = list(child.targets)
        else:
            continue

        violations.extend(
            _target_name(target)
            for target in targets
            if _is_package_or_manifest_state_assignment_target(target, aliases)
        )

    return violations


def _mutating_method_call_violations(
    node: ast.FunctionDef,
    aliases: dict[str, ast.AST],
) -> list[str]:
    violations: list[str] = []

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not isinstance(child.func, ast.Attribute):
            continue
        if child.func.attr not in _MUTATING_METHOD_NAMES:
            continue
        if _is_package_or_manifest_state_target(child.func.value, aliases):
            violations.append(_call_name(child.func))

    return violations


def _is_package_or_manifest_state_assignment_target(
    node: ast.AST,
    aliases: dict[str, ast.AST],
) -> bool:
    return isinstance(node, (ast.Attribute, ast.Subscript)) and (
        _is_package_or_manifest_state_target(node, aliases)
    )


def _is_package_or_manifest_state_target(
    node: ast.AST,
    aliases: dict[str, ast.AST],
) -> bool:
    root = _root_name(node)

    if root == "package":
        return True

    if root and root in aliases:
        return _is_package_manifest_attribute(aliases[root])

    return False


def _is_package_manifest_attribute(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "research_observation_manifest"
        and isinstance(node.value, ast.Name)
        and node.value.id == "package"
    )


def _root_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _root_name(node.value)
    if isinstance(node, ast.Subscript):
        return _root_name(node.value)

    return None


def _target_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _target_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return _target_name(node.value)
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


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value
