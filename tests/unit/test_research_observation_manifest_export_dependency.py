from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

from algotrader.research.research_observation_manifest import (
    build_research_observation_manifest,
)
from algotrader.research.research_observation_manifest_export import (
    export_research_observation_manifest_snapshot,
)


EXPORT_SOURCE_PATH = Path(
    "src/algotrader/research/research_observation_manifest_export.py"
)

_ALLOWED_IMPORTS = {
    "__future__": ("annotations",),
    "collections.abc": ("Iterable", "Mapping"),
    "algotrader.research.research_observation_manifest": (
        "build_research_observation_manifest",
    ),
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.cli",
    "algotrader.dashboard",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.package",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "algotrader.vendor",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "google.generativeai",
    "httpx",
    "ipynb",
    "joblib",
    "keras",
    "langchain",
    "langgraph",
    "lightgbm",
    "llm",
    "massive",
    "network",
    "numpy",
    "openai",
    "os",
    "pandas",
    "polars",
    "polygon",
    "QuantConnect",
    "quantconnect",
    "requests",
    "sklearn",
    "socket",
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "xgboost",
    "yfinance",
)
_FORBIDDEN_IMPORT_FRAGMENTS = (
    "_cli",
    "_renderer",
    "advisory_operating_brief_package",
    "package",
    "sma_",
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    "add_argument",
    "add_parser",
    "client",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "eval",
    "exec",
    "exists",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    "ingest",
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "load",
    "main",
    "mkdir",
    "open",
    "os.environ",
    "os.environ.get",
    "os.getenv",
    "parse_args",
    "pathlib.Path",
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "requests.get",
    "rglob",
    "save",
    "set_defaults",
    "socket.create_connection",
    "socket.socket",
    "stat",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}
_ALLOWED_CALL_NAMES = {
    "build_research_observation_manifest",
    "manifest.to_dict",
}
_FORBIDDEN_SOURCE_TOKENS = (
    "advisory",
    "allocation",
    "alpaca",
    "anthropic",
    "approval",
    "backtest",
    "benchmark",
    "broker",
    "cash",
    "cli",
    "credential",
    "environ",
    "evaluator",
    "execution",
    "file",
    "fill",
    "google.generativeai",
    "httpx",
    "live",
    "llm",
    "ml",
    "network",
    "numpy",
    "oms",
    "open",
    "openai",
    "order",
    "package",
    "pandas",
    "paper",
    "path",
    "polars",
    "portfolio",
    "quantconnect",
    "readiness",
    "recommendation",
    "renderer",
    "requests",
    "runtime",
    "scheduler",
    "sdk",
    "signal",
    "sma",
    "socket",
    "storage",
    "strategy",
    "trading",
    "vectorbt",
    "vendor",
)
_FORBIDDEN_REFERENCE_NAMES = {
    "allocation",
    "alpaca",
    "broker",
    "cash",
    "cli",
    "client",
    "credential",
    "environ",
    "execution",
    "file",
    "fill",
    "network",
    "open",
    "order",
    "package",
    "path",
    "portfolio",
    "renderer",
    "runtime",
    "scheduler",
    "signal",
    "socket",
    "storage",
    "vendor",
}
_FORBIDDEN_SIGNATURE_PARAMETER_FRAGMENTS = (
    "broker",
    "client",
    "config",
    "credential",
    "env",
    "file",
    "network",
    "path",
    "runtime",
    "source",
    "storage",
    "vendor",
)


def test_export_module_imports_only_generic_manifest_contract_and_typing() -> None:
    import_details = _import_details_from_path(EXPORT_SOURCE_PATH)
    imports = set(import_details)

    assert import_details == _ALLOWED_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert _fragment_import_matches(imports, _FORBIDDEN_IMPORT_FRAGMENTS) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_export_module_references_no_runtime_io_vendor_sma_or_trading_tokens() -> None:
    source = _source_text_from_path(EXPORT_SOURCE_PATH)
    call_names = _call_names_from_path(EXPORT_SOURCE_PATH)
    reference_names = _reference_names_from_path(EXPORT_SOURCE_PATH)

    assert _forbidden_source_token_matches(source, _FORBIDDEN_SOURCE_TOKENS) == []
    assert call_names == _ALLOWED_CALL_NAMES
    assert call_names.isdisjoint(_lowered(_FORBIDDEN_CALL_NAMES))
    assert reference_names.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_export_helper_signature_exposes_no_io_config_or_network_options() -> None:
    signature = inspect.signature(export_research_observation_manifest_snapshot)

    assert tuple(signature.parameters) == ("entries",)
    assert signature.parameters["entries"].default is inspect.Signature.empty
    assert _signature_parameter_violations(signature) == []


def test_export_helper_returns_manifest_to_dict_unchanged_for_primitives() -> None:
    entries = _generic_primitive_entries()

    snapshot = export_research_observation_manifest_snapshot(entries)
    expected = build_research_observation_manifest(entries).to_dict()

    assert snapshot == expected
    assert tuple(snapshot) == tuple(expected)
    assert snapshot["entries"] == expected["entries"]


def test_export_helper_compact_sorted_key_json_is_byte_deterministic() -> None:
    entries = _generic_primitive_entries()

    first_json = _compact_json(
        export_research_observation_manifest_snapshot(entries)
    )
    second_json = _compact_json(
        export_research_observation_manifest_snapshot(entries)
    )

    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_export_source_adds_no_cli_package_renderer_storage_or_file_io_surface() -> None:
    source = _source_text_from_path(EXPORT_SOURCE_PATH)
    imports = set(_import_details_from_path(EXPORT_SOURCE_PATH))
    call_names = _call_names_from_path(EXPORT_SOURCE_PATH)

    assert "--" not in source
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert _fragment_import_matches(imports, _FORBIDDEN_IMPORT_FRAGMENTS) == []
    assert call_names.isdisjoint(_lowered(_FORBIDDEN_CALL_NAMES))


def _generic_primitive_entries() -> tuple[tuple[str, dict[str, object]], ...]:
    return (
        (
            "alpha",
            {
                "observation_type": "generic_research_observation",
                "active": True,
                "count": 2,
                "ratio": 0.5,
                "note": None,
                "points": [
                    {"label": "a", "value": 1},
                    {"label": "b", "value": 2},
                ],
            },
        ),
        (
            "beta",
            {
                "observation_type": "generic_research_observation",
                "active": False,
                "count": 1,
                "ratio": 1.0,
                "note": "secondary",
                "points": [],
            },
        ),
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


def _call_names_from_path(path: Path) -> set[str]:
    return {
        _call_name(node.func).lower()
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
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())

    return names


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
) -> list[str]:
    lowered_source = source.lower()
    return [
        token
        for token in tokens
        if re.search(
            rf"(?<![a-z0-9]){re.escape(token.lower())}(?![a-z0-9])",
            lowered_source,
        )
    ]


def _signature_parameter_violations(
    signature: inspect.Signature,
) -> list[str]:
    return [
        name
        for name in signature.parameters
        if any(
            fragment in name.lower()
            for fragment in _FORBIDDEN_SIGNATURE_PARAMETER_FRAGMENTS
        )
    ]


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _lowered(values: set[str]) -> set[str]:
    return {value.lower() for value in values}
