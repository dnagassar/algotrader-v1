from __future__ import annotations

import ast
import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_observation_manifest import (
    ResearchObservationManifest,
    ResearchObservationManifestEntry,
    build_research_observation_manifest,
)
from tests.fixtures.sma_return_research_pipeline_observation_export import (
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict,
)


MODULE_PATH = Path("src/algotrader/research/research_observation_manifest.py")

_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "hashlib",
    "json",
    "math",
    "algotrader.errors",
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
    "httpx",
    "ipynb",
    "joblib",
    "keras",
    "langchain",
    "langgraph",
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
    "random",
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


def test_manifest_entry_is_frozen_and_slotted() -> None:
    entry = _single_entry()

    assert hasattr(ResearchObservationManifestEntry, "__slots__")
    assert tuple(field.name for field in fields(ResearchObservationManifestEntry)) == (
        "observation_name",
        "observation_type",
        "payload_key_count",
        "payload_digest_sha256",
    )
    with pytest.raises(FrozenInstanceError):
        entry.observation_name = "other"
    with pytest.raises((AttributeError, TypeError)):
        entry.extra_field = "not allowed"


def test_manifest_object_is_frozen_and_slotted() -> None:
    manifest = build_research_observation_manifest(
        (("alpha", _primitive_observation_payload()),)
    )

    assert hasattr(ResearchObservationManifest, "__slots__")
    assert tuple(field.name for field in fields(ResearchObservationManifest)) == (
        "manifest_type",
        "schema_version",
        "advisory_scope",
        "entry_count",
        "entries",
    )
    with pytest.raises(FrozenInstanceError):
        manifest.entry_count = 2
    with pytest.raises((AttributeError, TypeError)):
        manifest.extra_field = "not allowed"


def test_valid_primitive_payload_builds_deterministic_manifest_entry() -> None:
    payload = _primitive_observation_payload()

    manifest = build_research_observation_manifest((("alpha", payload),))
    entry = manifest.entries[0]

    assert entry == ResearchObservationManifestEntry(
        observation_name="alpha",
        observation_type="synthetic_research_observation",
        payload_key_count=len(payload),
        payload_digest_sha256=_payload_digest(payload),
    )
    assert entry.to_dict() == {
        "observation_name": "alpha",
        "observation_type": "synthetic_research_observation",
        "payload_key_count": len(payload),
        "payload_digest_sha256": _payload_digest(payload),
    }
    assert manifest.entry_count == 1


def test_manifest_preserves_input_entry_ordering() -> None:
    manifest = build_research_observation_manifest(
        (
            {"observation_name": "beta", "payload": {"rank": 2}},
            ("alpha", {"rank": 1}),
            ("gamma", {"rank": 3}),
        )
    )

    assert tuple(entry.observation_name for entry in manifest.entries) == (
        "beta",
        "alpha",
        "gamma",
    )
    assert [
        entry["observation_name"] for entry in manifest.to_dict()["entries"]
    ] == ["beta", "alpha", "gamma"]


def test_duplicate_observation_names_are_rejected() -> None:
    with pytest.raises(ValidationError, match="unique"):
        build_research_observation_manifest(
            (
                ("alpha", {"value": 1}),
                ("alpha", {"value": 2}),
            )
        )


@pytest.mark.parametrize("name", ("", "   "))
def test_empty_observation_names_are_rejected(name: str) -> None:
    with pytest.raises(ValidationError, match="non-empty"):
        build_research_observation_manifest(((name, {"value": 1}),))


def test_non_dict_payloads_are_rejected() -> None:
    with pytest.raises(ValidationError, match="dictionary"):
        build_research_observation_manifest((("alpha", ["not", "a", "dict"]),))


@pytest.mark.parametrize(
    "payload",
    (
        {"value": object()},
        {"value": ("tuple", "is", "not", "json")},
        {"value": float("nan")},
    ),
)
def test_non_primitive_payload_values_are_rejected(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="primitive JSON"):
        build_research_observation_manifest((("alpha", payload),))


def test_payload_key_count_is_deterministic() -> None:
    payload = {
        "c": 3,
        "a": 1,
        "b": 2,
    }

    first = build_research_observation_manifest((("alpha", payload),))
    second = build_research_observation_manifest((("alpha", dict(payload)),))

    assert first.entries[0].payload_key_count == 3
    assert second.entries[0].payload_key_count == 3


def test_payload_digest_matches_compact_sorted_key_json_hashing() -> None:
    payload = {
        "z": [3, 2, 1],
        "a": {"nested": True},
        "observation_type": "digest_fixture",
    }
    expected_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    expected_digest = hashlib.sha256(expected_json.encode("utf-8")).hexdigest()

    manifest = build_research_observation_manifest((("digest", payload),))

    assert manifest.entries[0].payload_digest_sha256 == expected_digest
    assert expected_digest == _payload_digest(payload)


def test_to_dict_is_primitive_only_and_json_round_trippable() -> None:
    manifest = build_research_observation_manifest(
        (("alpha", _primitive_observation_payload()),)
    )
    payload = manifest.to_dict()

    assert payload == {
        "manifest_type": "research_observation_manifest",
        "schema_version": "1",
        "advisory_scope": "research_observation_metadata_only",
        "entry_count": 1,
        "entries": [_single_entry().to_dict()],
    }
    assert tuple(payload) == (
        "manifest_type",
        "schema_version",
        "advisory_scope",
        "entry_count",
        "entries",
    )
    assert _primitive_only(payload)
    assert json.loads(_compact_json(payload)) == payload


def test_repeated_builds_and_serialization_are_byte_for_byte_deterministic() -> None:
    entries = (
        ("alpha", _primitive_observation_payload()),
        ("beta", {"observation_type": "other_observation", "value": 2}),
    )

    first = build_research_observation_manifest(entries)
    second = build_research_observation_manifest(entries)
    first_json = _compact_json(first.to_dict())
    second_json = _compact_json(second.to_dict())

    assert first == second
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert _compact_json(first.to_dict()) == _compact_json(first.to_dict())


def test_malformed_lookalike_entries_are_rejected() -> None:
    for entry in (
        {"observation_name": "alpha"},
        {"payload": {"value": 1}},
        {"observation_name": "alpha", "payload": {"value": 1}, "extra": True},
        ["alpha", {"value": 1}],
    ):
        with pytest.raises(ValidationError):
            build_research_observation_manifest((entry,))


def test_manifest_describes_expected_sma_export_snapshot_payload() -> None:
    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )

    manifest = build_research_observation_manifest(
        (("canonical_sma_return_pipeline", payload),)
    )
    entry = manifest.entries[0]

    assert entry.observation_name == "canonical_sma_return_pipeline"
    assert entry.observation_type == "sma_return_research_pipeline_observation"
    assert entry.payload_key_count == len(payload)
    assert entry.payload_digest_sha256 == _payload_digest(payload)


def test_sma_export_snapshot_payload_metadata_is_stable_across_fixture_calls() -> None:
    first_payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    second_payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )

    first = build_research_observation_manifest(
        (("canonical_sma_return_pipeline", first_payload),)
    )
    second = build_research_observation_manifest(
        (("canonical_sma_return_pipeline", second_payload),)
    )

    assert first_payload == second_payload
    assert _payload_digest(first_payload) == _payload_digest(second_payload)
    assert first.entries[0].payload_digest_sha256 == (
        second.entries[0].payload_digest_sha256
    )
    assert first.entries[0].payload_key_count == second.entries[0].payload_key_count
    assert _compact_json(first.to_dict()) == _compact_json(second.to_dict())


def test_builder_signature_exposes_no_file_path_env_network_or_config_options() -> None:
    signature = inspect.signature(build_research_observation_manifest)
    parameter_names = set(signature.parameters)

    assert tuple(signature.parameters) == ("entries",)
    assert parameter_names.isdisjoint(_FORBIDDEN_SIGNATURE_PARAMETER_NAMES)


def test_no_forbidden_fields_appear_in_dataclass_fields_or_serialized_output() -> None:
    manifest = build_research_observation_manifest(
        (("alpha", _primitive_observation_payload()),)
    )
    field_names = {
        field.name
        for field in fields(ResearchObservationManifestEntry)
        + fields(ResearchObservationManifest)
    }
    payload_keys = _payload_keys(manifest.to_dict())

    for name in field_names | payload_keys:
        assert not _contains_forbidden_fragment(name)


def test_source_file_imports_no_forbidden_dependencies() -> None:
    imports = _import_references_from_path(MODULE_PATH)

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert all("sma_return_research_pipeline_observation_export" not in name for name in imports)
    assert all(not module_name.startswith("tests") for module_name in imports)


def test_source_file_has_no_forbidden_runtime_io_or_trading_calls() -> None:
    call_names = _call_names_from_path(MODULE_PATH)

    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


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


def _single_entry() -> ResearchObservationManifestEntry:
    payload = _primitive_observation_payload()
    return ResearchObservationManifestEntry(
        observation_name="alpha",
        observation_type="synthetic_research_observation",
        payload_key_count=len(payload),
        payload_digest_sha256=_payload_digest(payload),
    )


def _payload_digest(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
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


def _contains_forbidden_fragment(name: str) -> bool:
    return any(fragment in name for fragment in _FORBIDDEN_FIELDS)


def _source_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree_from_path(path: Path) -> ast.AST:
    return ast.parse(_source_text_from_path(path), filename=str(path))


def _import_references_from_path(path: Path) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            elif node.level > 0:
                imports.add("__future__")

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


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
