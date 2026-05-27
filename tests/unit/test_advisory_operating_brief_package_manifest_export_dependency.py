from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from algotrader.research.advisory_operating_brief_package_manifest_export import (
    export_advisory_operating_brief_package_research_observation_manifest,
)
from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)


HELPER_SOURCE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_package_manifest_export.py"
)
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
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.cli",
    "algotrader.config",
    "algotrader.core.config",
    "algotrader.data",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.research.advisory_operating_brief_package_cli",
    "algotrader.research.advisory_operating_brief_package_renderer",
    "algotrader.research.advisory_operating_brief_package_synthetic",
    "algotrader.research.research_observation_manifest",
    "algotrader.research.research_observation_manifest_export",
    "algotrader.research.sma",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "algotrader.storage",
    "algotrader.vendor",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "click",
    "database",
    "duckdb",
    "google.generativeai",
    "hashlib",
    "httpx",
    "joblib",
    "json",
    "langchain",
    "langgraph",
    "llm",
    "network",
    "openai",
    "os",
    "pathlib",
    "requests",
    "sklearn",
    "socket",
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
    "build_research_observation_manifest",
    "build_synthetic_advisory_operating_brief_package_preview",
    "client",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "eval",
    "exec",
    "exists",
    "export_research_observation_manifest_snapshot",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "hashlib.sha256",
    "import_module",
    "is_file",
    "iterdir",
    "json.dump",
    "json.dumps",
    "json.load",
    "main",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "pathlib.Path",
    "post",
    "read",
    "read_bytes",
    "read_text",
    "request",
    "requests.get",
    "rglob",
    "set_defaults",
    "socket.create_connection",
    "socket.socket",
    "stat",
    "submit_order",
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}
_FORBIDDEN_REFERENCE_NAMES = {
    "account",
    "aiohttp",
    "alpaca",
    "broker",
    "capital_authority",
    "client",
    "config",
    "credential",
    "env",
    "environ",
    "fill",
    "from_dict",
    "hashlib",
    "httpx",
    "json",
    "network",
    "open",
    "order",
    "os",
    "path",
    "pathlib",
    "portfolio",
    "read_text",
    "readiness",
    "recommendation",
    "requests",
    "runtime",
    "secret",
    "socket",
    "storage",
    "token",
    "trading_authority",
    "urllib",
    "vendor",
    "write",
}
_FORBIDDEN_SOURCE_TOKENS = (
    "build_research_observation_manifest",
    "export_research_observation_manifest_snapshot",
    "build_synthetic_advisory_operating_brief_package_preview",
    "sma_",
    "alpaca",
    "broker",
    "order",
    "fill",
    "portfolio",
    "account",
    "credential",
    "secret",
    "token",
    "socket",
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "pathlib",
    "open(",
    "write",
    "read_text",
    "from_dict",
    "approved",
    "readiness",
    "recommendation",
    "trading_authority",
    "capital_authority=True",
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


def test_export_helper_imports_only_package_audit_contracts() -> None:
    import_details = _import_details_from_path(HELPER_SOURCE_PATH)
    imports = set(import_details)

    assert import_details == _ALLOWED_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_export_helper_public_surface_is_single_explicit_helper() -> None:
    tree = _tree_from_path(HELPER_SOURCE_PATH)
    helper = _function_def_from_path(HELPER_SOURCE_PATH, _HELPER_NAME)

    assert _module_all_from_tree(tree) == [_HELPER_NAME]
    assert _public_function_names_from_tree(tree) == [_HELPER_NAME]
    assert _function_parameter_names(helper) == ("package",)


def test_export_helper_validates_exact_package_and_attached_manifest() -> None:
    helper = _function_def_from_path(HELPER_SOURCE_PATH, _HELPER_NAME)
    aliases = _simple_name_aliases(helper)

    assert _has_validation_raise_for_if(helper, _is_exact_package_type_check)
    assert _has_validation_raise_for_if(
        helper,
        lambda node: _is_attached_manifest_none_check(node, aliases),
    )
    assert _helper_returns_attached_manifest_to_dict(helper, aliases)


def test_export_helper_uses_no_builders_io_runtime_or_state_mutation() -> None:
    source = _source_text_from_path(HELPER_SOURCE_PATH)
    calls = _call_names_from_path(HELPER_SOURCE_PATH)
    references = _reference_names_from_path(HELPER_SOURCE_PATH)
    helper = _function_def_from_path(HELPER_SOURCE_PATH, _HELPER_NAME)
    aliases = _simple_name_aliases(helper)

    assert _forbidden_source_token_matches(source, _FORBIDDEN_SOURCE_TOKENS) == []
    assert calls.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert references.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)
    assert _state_mutation_violations(helper, aliases) == []
    assert _mutating_method_call_violations(helper, aliases) == []


def test_exported_synthetic_manifest_is_attached_payload_and_deterministic() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest = package.research_observation_manifest

    assert manifest is not None

    first_payload = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )
    second_payload = export_advisory_operating_brief_package_research_observation_manifest(
        package
    )
    first_json = _compact_sorted_json(first_payload)
    second_json = _compact_sorted_json(second_payload)
    entries = _list(first_payload["entries"])

    assert first_payload == manifest.to_dict()
    assert second_payload == manifest.to_dict()
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert first_payload["entry_count"] == 1
    assert len(entries) == 1
    assert _dict(entries[0])["observation_name"] == _OBSERVATION_NAME


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
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
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


def _function_def_from_path(path: Path, name: str) -> ast.FunctionDef:
    for node in ast.walk(_tree_from_path(path)):
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


def _simple_name_aliases(node: ast.FunctionDef) -> dict[str, ast.AST]:
    aliases: dict[str, ast.AST] = {}

    for child in node.body:
        if not isinstance(child, ast.Assign):
            continue
        if len(child.targets) != 1 or not isinstance(child.targets[0], ast.Name):
            continue
        aliases[child.targets[0].id] = child.value

    return aliases


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


def _is_attached_manifest_none_check(
    node: ast.AST,
    aliases: dict[str, ast.AST],
) -> bool:
    return (
        isinstance(node, ast.Compare)
        and _is_attached_manifest_expr(node.left, aliases)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Is)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value is None
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


def _helper_returns_attached_manifest_to_dict(
    node: ast.FunctionDef,
    aliases: dict[str, ast.AST],
) -> bool:
    return_nodes = [
        statement for statement in node.body if isinstance(statement, ast.Return)
    ]

    return (
        len(return_nodes) == 1
        and _is_attached_manifest_to_dict_call(return_nodes[0].value, aliases)
    )


def _is_attached_manifest_to_dict_call(
    node: ast.AST | None,
    aliases: dict[str, ast.AST],
) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "to_dict"
        and node.args == []
        and node.keywords == []
        and _is_attached_manifest_expr(node.func.value, aliases)
    )


def _is_attached_manifest_expr(
    node: ast.AST,
    aliases: dict[str, ast.AST],
) -> bool:
    if _is_package_manifest_attribute(node):
        return True

    if isinstance(node, ast.Name) and node.id in aliases:
        return _is_package_manifest_attribute(aliases[node.id])

    return False


def _is_package_manifest_attribute(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "research_observation_manifest"
        and isinstance(node.value, ast.Name)
        and node.value.id == "package"
    )


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


def _reference_names_from_path(path: Path) -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


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
        return _is_attached_manifest_expr(ast.Name(id=root, ctx=ast.Load()), aliases)

    return False


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


def _compact_sorted_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value
