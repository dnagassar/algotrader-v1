from __future__ import annotations

import ast
import hashlib
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
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.research.advisory_operating_brief_package_cli",
    "algotrader.research.advisory_operating_brief_package_renderer",
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
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    "build_research_observation_manifest",
    "client",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "eval",
    "exec",
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
    "json.load",
    "load",
    "main",
    "mkdir",
    "open",
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
    "build_research_observation_manifest",
    "export_research_observation_manifest_snapshot",
    "algotrader.research.sma",
    "tests.fixtures.sma",
    "alpaca",
    "broker",
    "credential",
    "database",
    "from_dict",
    "httpx",
    "open(",
    "pathlib",
    "read_text",
    "requests",
    "socket",
    "urllib",
    "write",
)
_FORBIDDEN_CLAIM_TOKENS = (
    "approval",
    "approved",
    "readiness",
    "ready",
    "trading_authority",
    "trading authority",
    "trading-authority",
)


def test_fixture_dict_equals_phase_263_export_helper_output() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()

    assert (
        expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
        == export_advisory_operating_brief_package_research_observation_manifest(
            package
        )
    )


def test_fixture_json_equals_compact_sorted_key_json_of_fixture_dict() -> None:
    payload = expected_synthetic_advisory_operating_brief_package_manifest_export_dict()

    assert (
        expected_synthetic_advisory_operating_brief_package_manifest_export_json()
        == _compact_sorted_json(payload)
    )


def test_repeated_fixture_dict_calls_are_equal() -> None:
    assert (
        expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
        == expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
    )


def test_repeated_fixture_json_calls_are_byte_for_byte_identical() -> None:
    first = (
        expected_synthetic_advisory_operating_brief_package_manifest_export_json()
    )
    second = (
        expected_synthetic_advisory_operating_brief_package_manifest_export_json()
    )

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_fixture_payload_is_primitive_json_round_trippable() -> None:
    payload = expected_synthetic_advisory_operating_brief_package_manifest_export_dict()

    _assert_primitive_only(payload)
    assert json.loads(_compact_sorted_json(payload)) == payload


def test_fixture_payload_has_expected_one_entry_manifest_contract() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    observation = package.sma_return_research_pipeline_observation
    payload = expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
    entries = _list(payload["entries"])
    entry = _dict(entries[0])

    assert observation is not None

    observation_payload = observation.to_dict()

    assert payload["manifest_type"] == "research_observation_manifest"
    assert payload["schema_version"] == "1"
    assert payload["advisory_scope"] == "research_observation_metadata_only"
    assert payload["entry_count"] == 1
    assert len(entries) == 1
    assert entry["observation_name"] == _OBSERVATION_NAME
    assert _is_lowercase_sha256(entry["payload_digest_sha256"])
    assert entry["observation_type"] == observation_payload["observation_type"]
    assert entry["payload_key_count"] == len(observation_payload)


def test_fixture_contains_exactly_one_named_manifest_entry() -> None:
    payload = expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
    entries = _list(payload["entries"])

    assert len(entries) == 1
    assert [_dict(entry)["observation_name"] for entry in entries] == [
        _OBSERVATION_NAME
    ]


def test_fixture_digest_matches_included_synthetic_sma_observation_payload() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    observation = package.sma_return_research_pipeline_observation
    payload = expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
    entry = _dict(_list(payload["entries"])[0])

    assert observation is not None

    observation_payload = observation.to_dict()

    assert entry["payload_digest_sha256"] == _payload_digest(observation_payload)


def test_fixture_payload_exposes_no_authority_readiness_or_approval_claims() -> None:
    payload = expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
    flattened = "\n".join(_flatten_strings(payload)).lower()

    for token in _FORBIDDEN_CLAIM_TOKENS:
        assert token not in flattened


def test_fixture_module_imports_are_test_only_and_dependency_bounded() -> None:
    imports = _import_details_from_path(_FIXTURE_SOURCE_PATH)

    assert fixture_module.__name__ == _FIXTURE_MODULE_NAME
    assert fixture_module.__all__ == [_DICT_HELPER_NAME, _JSON_HELPER_NAME]
    assert _public_function_names_from_path(_FIXTURE_SOURCE_PATH) == [
        _DICT_HELPER_NAME,
        _JSON_HELPER_NAME,
    ]
    assert imports == _ALLOWED_IMPORTS
    assert _matching_imports(set(imports), _FORBIDDEN_IMPORT_PREFIXES) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_fixture_module_uses_no_generic_builders_direct_sma_io_or_runtime() -> None:
    source = _source_text_from_path(_FIXTURE_SOURCE_PATH)
    calls = _call_names_from_path(_FIXTURE_SOURCE_PATH)

    assert _forbidden_source_token_matches(source, _FORBIDDEN_SOURCE_TOKENS) == []
    assert calls.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert calls == {
        "build_synthetic_advisory_operating_brief_package_preview",
        "expected_synthetic_advisory_operating_brief_package_manifest_export_dict",
        "export_advisory_operating_brief_package_research_observation_manifest",
        "json.dumps",
    }


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


def _flatten_strings(value: object) -> list[str]:
    if isinstance(value, dict):
        strings: list[str] = []
        for key, item in value.items():
            strings.append(key)
            strings.extend(_flatten_strings(item))
        return strings

    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(_flatten_strings(item))
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


def _public_function_names_from_path(path: Path) -> list[str]:
    tree = _tree_from_path(path)

    if not isinstance(tree, ast.Module):
        return []

    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


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
