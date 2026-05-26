from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

import tests.fixtures.research_observation_manifest as manifest_fixture
from algotrader.research.research_observation_manifest import (
    build_research_observation_manifest,
)
from tests.fixtures.research_observation_manifest import (
    expected_sma_return_research_pipeline_export_snapshot_manifest_dict,
    expected_sma_return_research_pipeline_export_snapshot_manifest_json,
)


MANIFEST_SOURCE_PATH = Path(
    "src/algotrader/research/research_observation_manifest.py"
)
MANIFEST_FIXTURE_PATH = Path("tests/fixtures/research_observation_manifest.py")
SMA_MANIFEST_INTEGRATION_TEST_PATH = Path(
    "tests/unit/test_research_observation_manifest_with_sma_export_snapshot.py"
)
_GUARDED_PATHS = (
    MANIFEST_SOURCE_PATH,
    MANIFEST_FIXTURE_PATH,
    SMA_MANIFEST_INTEGRATION_TEST_PATH,
)

_ALLOWED_PRODUCTION_MANIFEST_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "hashlib",
    "json",
    "math",
    "algotrader.errors",
}
_ALLOWED_MANIFEST_FIXTURE_IMPORTS = {
    "__future__",
    "json",
    "algotrader.research.research_observation_manifest",
    "tests.fixtures.sma_return_research_pipeline_observation_export",
}
_ALLOWED_INTEGRATION_TEST_IMPORTS = {
    "__future__",
    "hashlib",
    "json",
    "algotrader.research.research_observation_manifest",
    "tests.fixtures.research_observation_manifest",
    "tests.fixtures.sma_return_research_pipeline_observation_export",
}
_FORBIDDEN_RUNTIME_IMPORT_PREFIXES = (
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
_FORBIDDEN_PRODUCTION_SMA_IMPORT_PREFIXES = (
    "algotrader.research.sma_conditional_return_selection_observation",
    "algotrader.research.sma_conditional_return_selection_summary_observation",
    "algotrader.research.sma_research_observation",
    "algotrader.research.sma_return_alignment_observation",
    "algotrader.research.sma_return_alignment_summary_observation",
    "algotrader.research.sma_return_research_pipeline_observation",
    "algotrader.research.sma_return_research_pipeline_observation_export",
    "algotrader.research.sma_selected_source_return_series_observation",
    "algotrader.research.sma_selected_source_return_summary_observation",
)
_FORBIDDEN_SOURCE_TOKENS = (
    "open",
    "Path",
    "os.environ",
    "socket",
    "requests",
    "httpx",
    "pandas",
    "polars",
    "numpy",
    "vectorbt",
    "quantconnect",
    "alpaca",
    "openai",
    "anthropic",
    "google.generativeai",
)
_FORBIDDEN_PRODUCTION_SOURCE_TOKENS = (
    "broker",
    "alpaca",
    "sdk",
    "socket",
    "credential",
    "environ",
    "path",
    "open",
    "cli",
    "package",
    "renderer",
    "runtime",
    "scheduler",
    "portfolio",
    "order",
    "fill",
    "benchmark",
    "backtest",
    "live",
    "paper",
    "readiness",
    "approval",
)
_FORBIDDEN_FIXTURE_AND_INTEGRATION_SOURCE_TOKENS = (
    *_FORBIDDEN_SOURCE_TOKENS,
    "broker",
    "sdk",
    "credential",
    "environ",
    "cli",
    "package",
    "renderer",
    "runtime",
    "scheduler",
    "portfolio",
    "order",
    "fill",
    "benchmark",
    "backtest",
    "live",
    "paper",
    "readiness",
    "approval",
    "vendor",
    "network",
    "storage",
    "file",
    "read",
    "write",
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
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}
_FORBIDDEN_REFERENCE_NAMES = {
    "Path",
    "alpaca",
    "broker",
    "cli",
    "client",
    "credential",
    "environ",
    "execution",
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
    "socket",
    "storage",
    "vendor",
}
_FORBIDDEN_SIGNATURE_PARAMETER_NAMES = {
    "broker",
    "client",
    "config",
    "credential",
    "env",
    "environment",
    "file",
    "network",
    "path",
    "runtime",
    "source",
    "storage",
    "vendor",
}
_FORBIDDEN_MANIFEST_TERMS = {
    "broker",
    "account",
    "order",
    "fill",
    "position",
    "portfolio",
    "cash",
    "equity",
    "pnl",
    "benchmark",
    "backtest",
    "allocation",
    "signal",
    "execution",
    "live",
    "paper",
    "readiness",
    "approval",
}


def test_production_manifest_imports_only_generic_deterministic_contracts() -> None:
    imports = _import_references_from_path(MANIFEST_SOURCE_PATH)

    assert imports == _ALLOWED_PRODUCTION_MANIFEST_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_RUNTIME_IMPORT_PREFIXES) == []
    assert _matching_imports(imports, _FORBIDDEN_PRODUCTION_SMA_IMPORT_PREFIXES) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_manifest_fixture_imports_only_generic_manifest_and_expected_payload() -> None:
    imports = _import_references_from_path(MANIFEST_FIXTURE_PATH)

    assert imports == _ALLOWED_MANIFEST_FIXTURE_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_RUNTIME_IMPORT_PREFIXES) == []
    assert _matching_imports(imports, _FORBIDDEN_PRODUCTION_SMA_IMPORT_PREFIXES) == []
    assert all(
        not module_name.startswith("algotrader.research.sma_")
        for module_name in imports
    )


def test_sma_manifest_integration_imports_no_runtime_broker_vendor_or_cli() -> None:
    imports = _import_references_from_path(SMA_MANIFEST_INTEGRATION_TEST_PATH)

    assert imports == _ALLOWED_INTEGRATION_TEST_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_RUNTIME_IMPORT_PREFIXES) == []
    assert _matching_imports(imports, _FORBIDDEN_PRODUCTION_SMA_IMPORT_PREFIXES) == []


def test_production_manifest_references_no_runtime_io_or_trading_tokens() -> None:
    source = _source_text_from_path(MANIFEST_SOURCE_PATH)

    assert (
        _forbidden_source_token_matches(
            source,
            _FORBIDDEN_SOURCE_TOKENS + _FORBIDDEN_PRODUCTION_SOURCE_TOKENS,
        )
        == []
    )
    assert _call_names_from_path(MANIFEST_SOURCE_PATH).isdisjoint(
        _FORBIDDEN_CALL_NAMES
    )
    assert _reference_names_from_path(MANIFEST_SOURCE_PATH).isdisjoint(
        _FORBIDDEN_REFERENCE_NAMES
    )


def test_fixture_and_integration_reference_no_runtime_broker_vendor_or_storage() -> None:
    for path in (MANIFEST_FIXTURE_PATH, SMA_MANIFEST_INTEGRATION_TEST_PATH):
        source = _source_text_from_path(path)

        assert (
            _forbidden_source_token_matches(
                source,
                _FORBIDDEN_FIXTURE_AND_INTEGRATION_SOURCE_TOKENS,
            )
            == []
        )
        assert _call_names_from_path(path).isdisjoint(_FORBIDDEN_CALL_NAMES)
        assert _reference_names_from_path(path).isdisjoint(
            _FORBIDDEN_REFERENCE_NAMES
        )


def test_public_helpers_expose_no_file_path_env_config_or_network_options() -> None:
    builder_signature = inspect.signature(build_research_observation_manifest)

    assert tuple(builder_signature.parameters) == ("entries",)
    assert set(builder_signature.parameters).isdisjoint(
        _FORBIDDEN_SIGNATURE_PARAMETER_NAMES
    )
    assert manifest_fixture.__all__ == [
        "expected_sma_return_research_pipeline_export_snapshot_manifest_dict",
        "expected_sma_return_research_pipeline_export_snapshot_manifest_json",
    ]

    for helper in (
        expected_sma_return_research_pipeline_export_snapshot_manifest_dict,
        expected_sma_return_research_pipeline_export_snapshot_manifest_json,
    ):
        signature = inspect.signature(helper)

        assert signature.parameters == {}
        assert set(signature.parameters).isdisjoint(
            _FORBIDDEN_SIGNATURE_PARAMETER_NAMES
        )


def test_manifest_fixture_output_keeps_metadata_only_terms() -> None:
    manifest = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()

    assert [
        term
        for term in _manifest_terms(manifest)
        if _contains_forbidden_manifest_term(term)
    ] == []


def test_sma_export_snapshot_manifest_fixture_json_is_byte_deterministic() -> None:
    first = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    second = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    first_json = (
        expected_sma_return_research_pipeline_export_snapshot_manifest_json()
    )
    second_json = (
        expected_sma_return_research_pipeline_export_snapshot_manifest_json()
    )

    assert first == second
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert first_json == _compact_json(first)
    assert second_json == _compact_json(second)


def test_guarded_files_add_no_cli_flags_package_renderer_storage_or_file_io() -> None:
    for path in _GUARDED_PATHS:
        source = _source_text_from_path(path)

        assert "--" not in source
        assert _call_names_from_path(path).isdisjoint(_FORBIDDEN_CALL_NAMES)


def _source_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree_from_path(path: Path) -> ast.AST:
    return ast.parse(_source_text_from_path(path), filename=str(path))


def _import_references_from_path(path: Path) -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


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
    lowered_source = source.lower()
    return [
        token
        for token in tokens
        if re.search(
            rf"(?<![a-z0-9_]){re.escape(token.lower())}(?![a-z0-9_])",
            lowered_source,
        )
    ]


def _manifest_terms(value: object) -> set[str]:
    if isinstance(value, dict):
        terms: set[str] = set()
        for key, item in value.items():
            terms.add(str(key))
            terms.update(_manifest_terms(item))
        return terms
    if isinstance(value, list):
        terms = set()
        for item in value:
            terms.update(_manifest_terms(item))
        return terms
    if isinstance(value, str):
        return {value}

    return set()


def _contains_forbidden_manifest_term(term: str) -> bool:
    lowered = term.lower()
    return any(fragment in lowered for fragment in _FORBIDDEN_MANIFEST_TERMS)


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
