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
from tests.fixtures import (
    advisory_operating_brief_package_manifest_export as fixture_module,
)
from tests.fixtures.advisory_operating_brief_package_manifest_export import (
    expected_synthetic_advisory_operating_brief_package_manifest_export_dict,
    expected_synthetic_advisory_operating_brief_package_manifest_export_json,
)


_FIXTURE_SOURCE_PATH = Path(
    "tests/fixtures/advisory_operating_brief_package_manifest_export.py"
)
_FIXTURE_MODULE_NAME = (
    "tests.fixtures.advisory_operating_brief_package_manifest_export"
)
_DICT_HELPER_NAME = (
    "expected_synthetic_advisory_operating_brief_package_manifest_export_dict"
)
_JSON_HELPER_NAME = (
    "expected_synthetic_advisory_operating_brief_package_manifest_export_json"
)
_OBSERVATION_NAME = "sma_return_research_pipeline_observation"
_EXPECTED_ALL = [_DICT_HELPER_NAME, _JSON_HELPER_NAME]
_ALLOWED_IMPORTS = {
    "__future__": ("annotations",),
    "json": (),
    "algotrader.research.advisory_operating_brief_package_manifest_export": (
        "export_advisory_operating_brief_package_research_observation_manifest",
    ),
    "algotrader.research.advisory_operating_brief_package_synthetic": (
        "build_synthetic_advisory_operating_brief_package_preview",
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
    "algotrader.network",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.research.research_observation_manifest",
    "algotrader.research.research_observation_manifest_export",
    "algotrader.research.sma",
    "algotrader.research.sma_",
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
    "tensorflow",
    "torch",
    "typer",
    "urllib",
)
_FORBIDDEN_IMPORT_FRAGMENTS = (
    "_cli",
    "_renderer",
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    "build_research_observation_manifest",
    "client",
    "connect",
    "create_order",
    "eval",
    "exec",
    "export_research_observation_manifest_snapshot",
    "from_dict",
    "getenv",
    "hashlib.sha256",
    "import_module",
    "json.dump",
    "json.load",
    "load",
    "main",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "read",
    "read_bytes",
    "read_text",
    "request",
    "requests.get",
    "sha256",
    "socket.create_connection",
    "socket.socket",
    "submit_order",
    "to_file",
    "to_sql",
    "urlopen",
    "write",
    "write_text",
}
_EXPECTED_CALL_NAMES = {
    "build_synthetic_advisory_operating_brief_package_preview",
    "expected_synthetic_advisory_operating_brief_package_manifest_export_dict",
    "export_advisory_operating_brief_package_research_observation_manifest",
    "json.dumps",
}
_FORBIDDEN_SOURCE_TOKENS = (
    "build_research_observation_manifest",
    "export_research_observation_manifest_snapshot",
    "algotrader.research.research_observation_manifest",
    "algotrader.research.research_observation_manifest_export",
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
    "open(",
    "write",
    "read_text",
    "from_dict",
    "approved",
    "readiness",
    "recommendation",
    "trading_authority",
    "capital_authority=True",
    "hashlib",
    "pathlib",
    "os",
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "sha256",
)
_SOURCE_TOKEN_ALLOWLIST = {
    "sma_": (_OBSERVATION_NAME,),
}


def test_fixture_imports_are_pinned_and_public_surface_is_explicit() -> None:
    tree = _tree_from_path(_FIXTURE_SOURCE_PATH)
    import_details = _import_details_from_path(_FIXTURE_SOURCE_PATH)
    imports = set(import_details)

    assert fixture_module.__name__ == _FIXTURE_MODULE_NAME
    assert fixture_module.__all__ == _EXPECTED_ALL
    assert _module_all_from_tree(tree) == _EXPECTED_ALL
    assert _public_function_names_from_tree(tree) == _EXPECTED_ALL
    assert import_details == _ALLOWED_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert _fragment_import_matches(imports, _FORBIDDEN_IMPORT_FRAGMENTS) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_fixture_helpers_remain_thin_synthetic_export_wrappers() -> None:
    tree = _tree_from_path(_FIXTURE_SOURCE_PATH)
    dict_helper = _function_def_from_tree(tree, _DICT_HELPER_NAME)
    json_helper = _function_def_from_tree(tree, _JSON_HELPER_NAME)
    calls = _call_names_from_tree(tree)

    assert _dict_helper_returns_phase_263_export_of_synthetic_package(dict_helper)
    assert _json_helper_serializes_dict_helper_with_compact_sorted_keys(json_helper)
    assert calls == _EXPECTED_CALL_NAMES
    assert calls.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_source_has_no_forbidden_direct_dependencies_or_tokens() -> None:
    source = _source_text_from_path(_FIXTURE_SOURCE_PATH)

    assert (
        _forbidden_source_token_matches(
            source,
            _FORBIDDEN_SOURCE_TOKENS,
            _SOURCE_TOKEN_ALLOWLIST,
        )
        == []
    )


def test_fixture_output_matches_helper_and_remains_byte_deterministic() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    expected_payload = (
        export_advisory_operating_brief_package_research_observation_manifest(
            package
        )
    )
    fixture_payload = (
        expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
    )
    fixture_json = (
        expected_synthetic_advisory_operating_brief_package_manifest_export_json()
    )
    repeated_json = (
        expected_synthetic_advisory_operating_brief_package_manifest_export_json()
    )
    entries = _list(fixture_payload["entries"])

    assert fixture_payload == expected_payload
    assert fixture_json == json.dumps(
        fixture_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert fixture_json == repeated_json
    assert fixture_json.encode("utf-8") == repeated_json.encode("utf-8")
    assert len(entries) == 1
    assert [_dict(entry)["observation_name"] for entry in entries] == [
        _OBSERVATION_NAME
    ]


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


def _dict_helper_returns_phase_263_export_of_synthetic_package(
    node: ast.FunctionDef,
) -> bool:
    aliases = _simple_name_aliases(node)
    package_expr = aliases.get("package")
    return_node = _single_return_node(node)

    return (
        _is_call_name(
            package_expr,
            "build_synthetic_advisory_operating_brief_package_preview",
        )
        and isinstance(return_node.value, ast.Call)
        and _call_name(return_node.value.func)
        == "export_advisory_operating_brief_package_research_observation_manifest"
        and len(return_node.value.args) == 1
        and isinstance(return_node.value.args[0], ast.Name)
        and return_node.value.args[0].id == "package"
        and return_node.value.keywords == []
    )


def _json_helper_serializes_dict_helper_with_compact_sorted_keys(
    node: ast.FunctionDef,
) -> bool:
    aliases = _simple_name_aliases(node)
    payload_expr = aliases.get("payload")
    return_node = _single_return_node(node)

    return (
        _is_call_name(payload_expr, _DICT_HELPER_NAME)
        and _is_json_dumps_compact_sorted_payload(return_node.value)
    )


def _is_json_dumps_compact_sorted_payload(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Call):
        return False

    keywords = {keyword.arg: keyword.value for keyword in node.keywords}

    return (
        _call_name(node.func) == "json.dumps"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "payload"
        and set(keywords) == {"sort_keys", "separators"}
        and isinstance(keywords["sort_keys"], ast.Constant)
        and keywords["sort_keys"].value is True
        and _is_separator_tuple(keywords["separators"])
    )


def _is_separator_tuple(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Tuple)
        and len(node.elts) == 2
        and all(isinstance(item, ast.Constant) for item in node.elts)
        and [item.value for item in node.elts] == [",", ":"]
    )


def _simple_name_aliases(node: ast.FunctionDef) -> dict[str, ast.AST]:
    aliases: dict[str, ast.AST] = {}

    for child in node.body:
        if not isinstance(child, ast.Assign):
            continue
        if len(child.targets) != 1 or not isinstance(child.targets[0], ast.Name):
            continue
        aliases[child.targets[0].id] = child.value

    return aliases


def _single_return_node(node: ast.FunctionDef) -> ast.Return:
    return_nodes = [
        statement for statement in node.body if isinstance(statement, ast.Return)
    ]

    assert len(return_nodes) == 1

    return return_nodes[0]


def _is_call_name(node: ast.AST | None, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and _call_name(node.func) == name
        and node.args == []
        and node.keywords == []
    )


def _call_names_from_tree(tree: ast.AST) -> set[str]:
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
        or (
            forbidden_prefix.endswith("_")
            and module_name.startswith(forbidden_prefix)
        )
        for forbidden_prefix in forbidden_prefixes
    )


def _fragment_import_matches(
    imports: set[str],
    forbidden_fragments: tuple[str, ...],
) -> list[str]:
    return [
        module_name
        for module_name in sorted(imports)
        if any(fragment in module_name for fragment in forbidden_fragments)
    ]


def _forbidden_source_token_matches(
    source: str,
    tokens: tuple[str, ...],
    allowlist: dict[str, tuple[str, ...]],
) -> list[str]:
    matches: list[str] = []

    for token in tokens:
        if _source_token_has_unallowed_match(source, token, allowlist.get(token, ())):
            matches.append(token)

    return matches


def _source_token_has_unallowed_match(
    source: str,
    token: str,
    allowed_fragments: tuple[str, ...],
) -> bool:
    lowered_fragments = tuple(fragment.lower() for fragment in allowed_fragments)

    for line in source.splitlines():
        lowered_line = line.lower()
        if not _line_contains_token(lowered_line, token.lower()):
            continue
        if any(fragment in lowered_line for fragment in lowered_fragments):
            continue
        return True

    return False


def _line_contains_token(lowered_line: str, token: str) -> bool:
    if token.endswith("_"):
        return token in lowered_line

    if re.match(r"^[a-z0-9_]+$", token):
        return re.search(
            rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])",
            lowered_line,
        ) is not None

    return token in lowered_line


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value
