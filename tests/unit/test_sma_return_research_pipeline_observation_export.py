from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

import algotrader.research.sma_return_research_pipeline_observation_export as export_module
import tests.fixtures.sma_return_research_pipeline_observation_export as export_fixture
from algotrader.research.sma_return_research_pipeline_observation_export import (
    export_synthetic_sma_return_research_pipeline_observation_snapshot,
)
from tests.fixtures.sma_return_research_pipeline_observation_export import (
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict,
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json,
)
from tests.fixtures.sma_return_research_pipeline_observation import (
    build_synthetic_sma_return_research_pipeline_observation,
    expected_synthetic_sma_return_research_pipeline_observation_dict,
)


EXPORT_SOURCE_PATH = Path(
    "src/algotrader/research/sma_return_research_pipeline_observation_export.py"
)
EXPORT_FIXTURE_PATH = Path(
    "tests/fixtures/sma_return_research_pipeline_observation_export.py"
)
_EXPORT_ALLOWED_IMPORTS = {
    "__future__",
    "decimal",
    "algotrader.research.research_return_observation",
    "algotrader.research.sma_conditional_return_selection_observation",
    "algotrader.research.sma_conditional_return_selection_summary_observation",
    "algotrader.research.sma_research_observation",
    "algotrader.research.sma_return_alignment_observation",
    "algotrader.research.sma_return_alignment_summary_observation",
    "algotrader.research.sma_return_research_pipeline_observation",
    "algotrader.research.sma_selected_source_return_series_observation",
    "algotrader.research.sma_selected_source_return_summary_observation",
}
_FIXTURE_ALLOWED_IMPORTS = {
    "__future__",
    "json",
    "tests.fixtures.sma_return_research_pipeline_observation",
}
_FORBIDDEN_FIELDS = {
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
    "pathlib",
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
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
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
    "mkdir",
    "open",
    "os.environ",
    "os.environ.get",
    "os.getenv",
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


def test_snapshot_returns_canonical_primitive_pipeline_payload() -> None:
    snapshot = export_synthetic_sma_return_research_pipeline_observation_snapshot()
    pipeline = build_synthetic_sma_return_research_pipeline_observation()
    expected = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )

    assert snapshot == expected
    assert snapshot == pipeline.to_dict()
    assert expected == expected_synthetic_sma_return_research_pipeline_observation_dict()
    assert _primitive_only(snapshot)
    assert json.loads(_compact_json(snapshot)) == expected


def test_expected_fixture_json_matches_compact_sorted_payload() -> None:
    first = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    second = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    first_json = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json()
    )
    second_json = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json()
    )

    assert first == second
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert first_json == _compact_json(first)
    assert json.loads(first_json) == first


def test_snapshot_preserves_policy_observation_payload_exactly_once() -> None:
    snapshot = export_synthetic_sma_return_research_pipeline_observation_snapshot()
    pipeline = build_synthetic_sma_return_research_pipeline_observation()
    policy_payload = pipeline.return_construction_policy_observation.to_dict()
    expected = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )

    assert _key_count(snapshot, "return_construction_policy_observation") == 1
    assert _key_count(expected, "return_construction_policy_observation") == 1
    assert snapshot["return_construction_policy_observation"] == policy_payload
    assert expected["return_construction_policy_observation"] == policy_payload
    assert snapshot["return_construction_policy_observation"] == (
        pipeline.to_dict()["return_construction_policy_observation"]
    )


def test_repeated_snapshot_calls_and_json_serialization_are_byte_deterministic() -> None:
    first = export_synthetic_sma_return_research_pipeline_observation_snapshot()
    second = export_synthetic_sma_return_research_pipeline_observation_snapshot()
    first_json = _compact_json(first)
    second_json = _compact_json(second)

    assert first == second
    assert first is not second
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert _compact_json(first) == _compact_json(first)


def test_snapshot_returns_fresh_payload_without_hidden_mutation() -> None:
    first = export_synthetic_sma_return_research_pipeline_observation_snapshot()
    second = export_synthetic_sma_return_research_pipeline_observation_snapshot()

    first["limitations"].append("mutated primitive copy")
    first["source_alignment_observation"]["alignment_periods"].append(
        second["source_alignment_observation"]["alignment_periods"][0]
    )
    first["return_construction_policy_observation"]["source_policy"][
        "limitations"
    ].append("mutated primitive copy")

    assert second == expected_synthetic_sma_return_research_pipeline_observation_dict()
    assert (
        export_synthetic_sma_return_research_pipeline_observation_snapshot()
        == expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )


def test_snapshot_exposes_no_options_and_no_forbidden_payload_fields() -> None:
    snapshot = export_synthetic_sma_return_research_pipeline_observation_snapshot()
    expected = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )

    assert inspect.signature(
        export_synthetic_sma_return_research_pipeline_observation_snapshot
    ).parameters == {}
    assert export_module.__all__ == [
        "export_synthetic_sma_return_research_pipeline_observation_snapshot",
    ]
    assert export_fixture.__all__ == [
        "expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict",
        "expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json",
    ]
    assert _payload_keys(snapshot).isdisjoint(_FORBIDDEN_FIELDS)
    assert _payload_keys(expected).isdisjoint(_FORBIDDEN_FIELDS)


def test_export_and_fixture_modules_add_no_forbidden_dependencies_or_surfaces() -> None:
    imports = _import_references(export_module) | _import_references(export_fixture)
    call_names = _call_names(export_module) | _call_names(export_fixture)

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert [
        module_name
        for module_name in imports
        if module_name.endswith("_cli")
        or module_name.endswith("_renderer")
        or "advisory_operating_brief_package" in module_name
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert call_names.isdisjoint(
        {
            "add_argument",
            "add_parser",
            "render_advisory_operating_brief_package_text",
            "set_defaults",
        }
    )


def test_export_source_imports_only_deterministic_research_contracts() -> None:
    imports = _import_references_from_path(EXPORT_SOURCE_PATH)

    assert imports == _EXPORT_ALLOWED_IMPORTS
    assert all(
        module_name in {"__future__", "decimal"}
        or module_name.startswith("algotrader.research.")
        for module_name in imports
    )
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_export_fixture_imports_only_expected_fixture_helpers() -> None:
    imports = _import_references_from_path(EXPORT_FIXTURE_PATH)

    assert imports == _FIXTURE_ALLOWED_IMPORTS
    assert all(
        module_name in {"__future__", "json"}
        or module_name.startswith("tests.fixtures.")
        for module_name in imports
    )
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_export_source_references_no_forbidden_runtime_or_trading_tokens() -> None:
    source = _source_text_from_path(EXPORT_SOURCE_PATH)
    call_names = _call_names_from_path(EXPORT_SOURCE_PATH)
    reference_names = _reference_names_from_path(EXPORT_SOURCE_PATH)

    assert _forbidden_source_token_matches(
        source,
        _FORBIDDEN_EXPORT_SOURCE_TOKENS,
    ) == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert reference_names.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_export_fixture_references_no_forbidden_runtime_or_vendor_tokens() -> None:
    source = _source_text_from_path(EXPORT_FIXTURE_PATH)
    call_names = _call_names_from_path(EXPORT_FIXTURE_PATH)
    reference_names = _reference_names_from_path(EXPORT_FIXTURE_PATH)

    assert _forbidden_source_token_matches(
        source,
        _FORBIDDEN_FIXTURE_SOURCE_TOKENS,
    ) == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert reference_names.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_export_signature_exposes_no_file_path_env_config_or_network_options() -> None:
    signature = inspect.signature(
        export_synthetic_sma_return_research_pipeline_observation_snapshot
    )
    parameter_names = set(signature.parameters)

    assert parameter_names == set()
    assert parameter_names.isdisjoint(_FORBIDDEN_SIGNATURE_PARAMETER_NAMES)


def test_export_and_fixture_files_add_no_cli_package_or_renderer_surfaces() -> None:
    source = (
        _source_text_from_path(EXPORT_SOURCE_PATH)
        + "\n"
        + _source_text_from_path(EXPORT_FIXTURE_PATH)
    )
    imports = _import_references_from_path(EXPORT_SOURCE_PATH) | (
        _import_references_from_path(EXPORT_FIXTURE_PATH)
    )
    call_names = _call_names_from_path(EXPORT_SOURCE_PATH) | (
        _call_names_from_path(EXPORT_FIXTURE_PATH)
    )

    assert all("advisory_operating_brief_package" not in name for name in imports)
    assert all(not name.endswith("_cli") for name in imports)
    assert all(not name.endswith("_renderer") for name in imports)
    assert _forbidden_source_token_matches(
        source,
        ("cli", "package", "renderer"),
    ) == []
    assert call_names.isdisjoint(_FORBIDDEN_CLI_SURFACE_CALL_NAMES)
    assert "--" not in source


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False


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


def _key_count(value: object, key: str) -> int:
    if isinstance(value, dict):
        return sum(
            (1 if item_key == key else 0) + _key_count(item_value, key)
            for item_key, item_value in value.items()
        )
    if isinstance(value, list):
        return sum(_key_count(item, key) for item in value)
    return 0


def _source_text(module: object) -> str:
    return inspect.getsource(module)


def _tree(module: object) -> ast.AST:
    return ast.parse(_source_text(module))


def _source_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree_from_path(path: Path) -> ast.AST:
    return ast.parse(_source_text_from_path(path), filename=str(path))


def _import_references(module: object) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _import_references_from_path(path: Path) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _call_names(module: object) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree(module))
        if isinstance(node, ast.Call)
    }


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


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


_FORBIDDEN_EXPORT_SOURCE_TOKENS = (
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
_FORBIDDEN_FIXTURE_SOURCE_TOKENS = (
    *_FORBIDDEN_EXPORT_SOURCE_TOKENS,
    "vendor",
    "network",
    "file",
    "env",
    "trading",
)
_FORBIDDEN_REFERENCE_NAMES = {
    "Path",
    "alpaca",
    "broker",
    "cli",
    "credential",
    "environ",
    "execution",
    "fill",
    "open",
    "order",
    "package",
    "path",
    "portfolio",
    "renderer",
    "runtime",
    "scheduler",
    "socket",
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
    "vendor",
}
_FORBIDDEN_CLI_SURFACE_CALL_NAMES = {
    "add_argument",
    "add_parser",
    "build_parser",
    "main",
    "parse_args",
    "render_advisory_operating_brief_package_text",
    "set_defaults",
}
