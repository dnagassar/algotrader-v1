from __future__ import annotations

import ast
import hashlib
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
from tests.fixtures.sma_return_research_pipeline_observation_export import (
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict,
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json,
)


FIXTURE_PATH = Path("tests/fixtures/research_observation_manifest.py")
MANIFEST_SOURCE_PATH = Path(
    "src/algotrader/research/research_observation_manifest.py"
)
OBSERVATION_NAME = "sma_return_research_pipeline_observation_export_snapshot"

_ALLOWED_FIXTURE_IMPORTS = {
    "__future__",
    "json",
    "algotrader.research.research_observation_manifest",
    "tests.fixtures.sma_return_research_pipeline_observation_export",
}
_FORBIDDEN_OPTION_NAMES = {
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
_FORBIDDEN_SOURCE_TOKENS = (
    "alpaca",
    "broker",
    "credential",
    "dashboard",
    "environ",
    "file",
    "getenv",
    "network",
    "notebook",
    "open",
    "package",
    "path",
    "persist",
    "read",
    "renderer",
    "runtime",
    "scheduler",
    "socket",
    "storage",
    "vectorbt",
    "write",
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "add_argument",
    "add_parser",
    "connect",
    "create_order",
    "dump",
    "eval",
    "exec",
    "exists",
    "getenv",
    "glob",
    "import_module",
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "load",
    "mkdir",
    "open",
    "Path",
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "rglob",
    "save",
    "set_defaults",
    "socket.socket",
    "stat",
    "submit_order",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}


def test_sma_export_snapshot_manifest_fixture_builds_one_stable_entry() -> None:
    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    manifest = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    entry = manifest["entries"][0]

    assert manifest["manifest_type"] == "research_observation_manifest"
    assert manifest["schema_version"] == "1"
    assert manifest["advisory_scope"] == "research_observation_metadata_only"
    assert manifest["entry_count"] == 1
    assert len(manifest["entries"]) == 1
    assert entry["observation_name"] == OBSERVATION_NAME
    assert entry["observation_type"] == payload["observation_type"]
    assert entry["payload_key_count"] == len(payload)


def test_sma_export_snapshot_manifest_digest_matches_payload_hash() -> None:
    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    manifest = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    entry = manifest["entries"][0]

    assert entry["payload_digest_sha256"] == _payload_digest(payload)


def test_sma_manifest_fixture_matches_generic_manifest_to_dict_output() -> None:
    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    expected_manifest = build_research_observation_manifest(
        ((OBSERVATION_NAME, payload),)
    )

    assert (
        expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
        == expected_manifest.to_dict()
    )


def test_sma_manifest_fixture_json_is_compact_sorted_and_round_trippable() -> None:
    manifest = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    manifest_json = (
        expected_sma_return_research_pipeline_export_snapshot_manifest_json()
    )

    assert manifest_json == _compact_json(manifest)
    assert json.loads(manifest_json) == manifest
    assert _primitive_only(manifest)


def test_sma_manifest_fixture_repeated_calls_are_deterministic() -> None:
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


def test_sma_export_snapshot_expected_payload_remains_unchanged() -> None:
    before = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    before_json = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json()
    )

    expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    expected_sma_return_research_pipeline_export_snapshot_manifest_json()

    after = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    after_json = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json()
    )

    assert before == after
    assert before_json == after_json
    assert before_json == _compact_json(before)
    assert json.loads(before_json) == before


def test_manifest_fixture_helpers_expose_no_options_or_forbidden_fields() -> None:
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
        assert set(signature.parameters).isdisjoint(_FORBIDDEN_OPTION_NAMES)

    manifest = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()

    assert [
        term
        for term in _manifest_terms(manifest)
        if _contains_forbidden_fragment(term)
    ] == []


def test_manifest_fixture_imports_only_generic_manifest_and_expected_payload() -> None:
    imports = _import_references_from_path(FIXTURE_PATH)

    assert imports == _ALLOWED_FIXTURE_IMPORTS
    assert all(
        "sma_return_research_pipeline_observation_export" not in module_name
        or module_name.startswith("tests.fixtures.")
        for module_name in imports
    )


def test_production_manifest_source_remains_generic() -> None:
    imports = _import_references_from_path(MANIFEST_SOURCE_PATH)

    assert all(
        "sma_return_research_pipeline_observation_export" not in module_name
        for module_name in imports
    )
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_manifest_fixture_adds_no_cli_renderer_storage_or_runtime_surface() -> None:
    source = _source_text_from_path(FIXTURE_PATH)
    call_names = _call_names_from_path(FIXTURE_PATH)

    assert "--" not in source
    assert _forbidden_source_token_matches(source, _FORBIDDEN_SOURCE_TOKENS) == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def _payload_digest(payload: dict[str, object]) -> str:
    serialized = _compact_json(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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


def _contains_forbidden_fragment(term: str) -> bool:
    lowered = term.lower()
    return any(fragment in lowered for fragment in _FORBIDDEN_FIELDS)


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
