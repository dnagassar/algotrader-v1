from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

import pytest

import algotrader.research.research_observation_manifest_export as export_module
from algotrader.errors import ValidationError
from algotrader.research.research_observation_manifest import (
    build_research_observation_manifest,
)
from algotrader.research.research_observation_manifest_export import (
    export_research_observation_manifest_snapshot,
)
from tests.fixtures.sma_return_research_pipeline_observation_export import (
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict,
)


EXPORT_SOURCE_PATH = Path(
    "src/algotrader/research/research_observation_manifest_export.py"
)
OBSERVATION_NAME = "sma_return_research_pipeline_observation_export_snapshot"
_ALLOWED_EXPORT_IMPORTS = {
    "__future__",
    "collections.abc",
    "algotrader.research.research_observation_manifest",
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
_FORBIDDEN_SOURCE_TOKENS = (
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
    "allocation",
    "signal",
    "execution",
    "live",
    "paper",
    "readiness",
    "approval",
    "vendor",
    "network",
    "storage",
    "file",
    "trading",
)
_FORBIDDEN_REFERENCE_NAMES = {
    "Path",
    "alpaca",
    "allocation",
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
    "signal",
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


def test_export_helper_returns_manifest_to_dict_unchanged() -> None:
    entries = (
        ("alpha", _primitive_observation_payload()),
        ("beta", {"observation_type": "other_observation", "value": 2}),
    )
    expected = build_research_observation_manifest(entries).to_dict()

    snapshot = export_research_observation_manifest_snapshot(entries)

    assert snapshot == expected
    assert tuple(snapshot) == tuple(expected)
    assert snapshot["entries"] == expected["entries"]


def test_export_helper_accepts_valid_primitive_observation_entries() -> None:
    payload = _primitive_observation_payload()

    snapshot = export_research_observation_manifest_snapshot(
        (
            {"observation_name": "alpha", "payload": payload},
            ("beta", {"value": 2}),
        )
    )

    assert snapshot["entry_count"] == 2
    assert [entry["observation_name"] for entry in snapshot["entries"]] == [
        "alpha",
        "beta",
    ]
    assert snapshot["entries"][0]["observation_type"] == (
        "synthetic_research_observation"
    )
    assert snapshot["entries"][0]["payload_key_count"] == len(payload)


@pytest.mark.parametrize(
    ("entries", "match"),
    (
        ((("alpha", {"value": 1}), ("alpha", {"value": 2})), "unique"),
        ((("", {"value": 1}),), "non-empty"),
        ((("alpha", ["not", "a", "dict"]),), "dictionary"),
        ((("alpha", {"value": object()}),), "primitive JSON"),
    ),
)
def test_export_helper_rejects_invalid_entries_through_manifest_builder(
    entries: tuple[object, ...],
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        export_research_observation_manifest_snapshot(entries)


def test_export_source_does_not_duplicate_manifest_validation_logic() -> None:
    source = _source_text_from_path(EXPORT_SOURCE_PATH)

    assert "ValidationError" not in source
    assert "raise " not in source


def test_export_helper_output_is_primitive_only_and_json_round_trippable() -> None:
    snapshot = export_research_observation_manifest_snapshot(
        (("alpha", _primitive_observation_payload()),)
    )
    snapshot_json = _compact_json(snapshot)

    assert _primitive_only(snapshot)
    assert json.loads(snapshot_json) == snapshot


def test_repeated_export_helper_calls_produce_equal_dicts() -> None:
    entries = (
        ("alpha", _primitive_observation_payload()),
        ("beta", {"observation_type": "other_observation", "value": 2}),
    )

    first = export_research_observation_manifest_snapshot(entries)
    second = export_research_observation_manifest_snapshot(entries)

    assert first == second
    assert first is not second


def test_repeated_compact_sorted_key_json_is_byte_deterministic() -> None:
    entries = (
        ("alpha", _primitive_observation_payload()),
        ("beta", {"observation_type": "other_observation", "value": 2}),
    )

    first_json = _compact_json(
        export_research_observation_manifest_snapshot(entries)
    )
    second_json = _compact_json(
        export_research_observation_manifest_snapshot(entries)
    )

    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert first_json == _compact_json(
        export_research_observation_manifest_snapshot(entries)
    )


def test_export_helper_entry_ordering_matches_manifest_builder_contract() -> None:
    entries = (
        {"observation_name": "beta", "payload": {"rank": 2}},
        ("alpha", {"rank": 1}),
        ("gamma", {"rank": 3}),
    )

    snapshot = export_research_observation_manifest_snapshot(entries)
    expected = build_research_observation_manifest(entries).to_dict()

    assert snapshot == expected
    assert [
        entry["observation_name"] for entry in snapshot["entries"]
    ] == ["beta", "alpha", "gamma"]


def test_export_helper_describes_sma_export_snapshot_from_test_fixture_only() -> None:
    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )

    snapshot = export_research_observation_manifest_snapshot(
        ((OBSERVATION_NAME, payload),)
    )
    expected = build_research_observation_manifest(
        ((OBSERVATION_NAME, payload),)
    ).to_dict()

    assert snapshot == expected
    assert snapshot["entry_count"] == 1
    assert snapshot["entries"][0]["observation_name"] == OBSERVATION_NAME
    assert snapshot["entries"][0]["observation_type"] == payload["observation_type"]
    assert snapshot["entries"][0]["payload_key_count"] == len(payload)


def test_export_source_imports_only_generic_manifest_contracts() -> None:
    imports = _import_references_from_path(EXPORT_SOURCE_PATH)

    assert imports == _ALLOWED_EXPORT_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert _matching_imports(
        imports,
        _FORBIDDEN_PRODUCTION_SMA_IMPORT_PREFIXES,
    ) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)
    assert all(not module_name.startswith("algotrader.research.sma_") for module_name in imports)
    assert all(not module_name.endswith("_cli") for module_name in imports)
    assert all(not module_name.endswith("_renderer") for module_name in imports)
    assert all("advisory_operating_brief_package" not in name for name in imports)


def test_export_helper_signature_exposes_no_file_path_env_config_network_options() -> None:
    signature = inspect.signature(export_research_observation_manifest_snapshot)
    parameter_names = set(signature.parameters)

    assert tuple(signature.parameters) == ("entries",)
    assert signature.parameters["entries"].default is inspect.Signature.empty
    assert parameter_names.isdisjoint(_FORBIDDEN_SIGNATURE_PARAMETER_NAMES)
    assert export_module.__all__ == [
        "export_research_observation_manifest_snapshot",
    ]


def test_no_forbidden_fields_appear_in_exported_manifest_snapshots() -> None:
    generic_snapshot = export_research_observation_manifest_snapshot(
        (("alpha", _primitive_observation_payload()),)
    )
    sma_payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    sma_snapshot = export_research_observation_manifest_snapshot(
        ((OBSERVATION_NAME, sma_payload),)
    )

    for snapshot in (generic_snapshot, sma_snapshot):
        assert [
            term
            for term in _manifest_terms(snapshot)
            if _contains_forbidden_manifest_term(term)
        ] == []


def test_export_source_adds_no_cli_package_renderer_storage_file_io_or_trading() -> None:
    source = _source_text_from_path(EXPORT_SOURCE_PATH)
    imports = _import_references_from_path(EXPORT_SOURCE_PATH)
    call_names = _call_names_from_path(EXPORT_SOURCE_PATH)
    reference_names = _reference_names_from_path(EXPORT_SOURCE_PATH)

    assert "--" not in source
    assert _forbidden_source_token_matches(
        source,
        _FORBIDDEN_SOURCE_TOKENS,
    ) == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert reference_names.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)
    assert all("package" not in name for name in imports)
    assert all(not name.endswith("_cli") for name in imports)
    assert all(not name.endswith("_renderer") for name in imports)


def _primitive_observation_payload() -> dict[str, object]:
    return {
        "observation_type": "synthetic_research_observation",
        "status": "candidate_only",
        "count": 2,
        "ratio": 0.5,
        "active": False,
        "note": None,
        "points": [
            {"label": "a", "value": 1},
            {"label": "b", "value": 2},
        ],
    }


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool, float):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False


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
