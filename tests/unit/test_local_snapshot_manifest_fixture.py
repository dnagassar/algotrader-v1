import ast
import json
import re
from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.local_snapshot_manifest import (
    REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS,
    LocalSnapshotManifest,
)
from tests.fixtures.local_snapshot_manifest import (
    build_synthetic_local_snapshot_manifest,
    build_synthetic_local_snapshot_manifest_dict,
    build_synthetic_local_snapshot_manifest_json_bytes,
)


FIXTURE_PATH = Path("tests/fixtures/local_snapshot_manifest.py")

_REAL_ETF_TICKERS = (
    "SPY",
    "IVV",
    "VOO",
    "QQQ",
    "VTI",
    "IWM",
    "DIA",
    "AGG",
    "BND",
    "TLT",
    "GLD",
    "EFA",
    "EEM",
    "XLK",
    "XLF",
    "XLE",
    "XLV",
    "XLU",
    "XLI",
    "XLY",
    "XLP",
    "XLRE",
)

_REAL_VENDOR_OR_PROVIDER_TERMS = (
    "alpaca",
    "alpha vantage",
    "bloomberg",
    "factset",
    "finnhub",
    "interactive brokers",
    "morningstar",
    "nasdaq",
    "polygon",
    "quantconnect",
    "quandl",
    "refinitiv",
    "stooq",
    "tiingo",
    "yahoo",
    "yfinance",
)

_CREDENTIAL_TERMS = (
    "api_key",
    "apikey",
    "bearer",
    "client_secret",
    "credential",
    "oauth",
    "password",
    "private_key",
    "secret",
    "token",
)

_URL_OR_PATH_MARKERS = (
    "://",
    "http:",
    "https:",
    "www.",
    ".com",
    ".data",
    ".csv",
    ".jsonl",
    ".parquet",
    ".zip",
    "/",
    "\\",
    "market-data",
    "market_data",
)

_APPROVAL_VALIDATION_TRADING_TERMS = (
    "approval",
    "approved",
    "readiness",
    "ready",
    "strategy",
    "trading",
    "validated",
    "validation",
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.local_snapshot_manifest",
    "datetime",
    "json",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.market_data",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.runtime",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "hashlib",
    "httpx",
    "market_data",
    "numpy",
    "os",
    "pandas",
    "pathlib",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_CALL_NAMES = {
    "connect",
    "create_order",
    "download",
    "exists",
    "glob",
    "hashlib.sha256",
    "is_file",
    "iterdir",
    "load",
    "loads",
    "mkdir",
    "open",
    "Path",
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "requests.get",
    "rglob",
    "sha256",
    "socket.socket",
    "stat",
    "submit_order",
    "urlopen",
    "walk",
}

_FORBIDDEN_REFERENCE_NAMES = {
    "Alpaca",
    "broker",
    "hash_file",
    "hashlib",
    "httpx",
    "market_data",
    "network",
    "numpy",
    "os",
    "pandas",
    "Path",
    "pathlib",
    "portfolio",
    "QuantConnect",
    "requests",
    "runtime",
    "socket",
    "vectorbt",
    "yfinance",
}


def test_fixture_builds_valid_local_snapshot_manifest() -> None:
    item = build_synthetic_local_snapshot_manifest()

    assert isinstance(item, LocalSnapshotManifest)
    assert item.snapshot_id == "synthetic-local-snapshot-manifest-001"
    assert item.source_type == "manual_local_snapshot"
    assert item.adjustment_policy == "unknown"
    assert item.return_basis == "unknown"
    assert item.normal_pytest_eligible is False


def test_fixture_output_is_deterministic_across_repeated_calls() -> None:
    first = build_synthetic_local_snapshot_manifest()
    second = build_synthetic_local_snapshot_manifest()

    assert first == second
    assert first is not second
    assert first.to_dict() == second.to_dict()
    assert build_synthetic_local_snapshot_manifest_dict() == first.to_dict()


def test_fixture_to_dict_output_is_primitive_only() -> None:
    payload = build_synthetic_local_snapshot_manifest_dict()

    _assert_primitive_only(payload)


def test_fixture_json_serialization_is_deterministic_and_byte_stable() -> None:
    first = build_synthetic_local_snapshot_manifest_json_bytes()
    second = build_synthetic_local_snapshot_manifest_json_bytes()
    expected = json.dumps(
        build_synthetic_local_snapshot_manifest_dict(),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")

    assert first == second
    assert first == expected
    assert json.loads(first.decode("utf-8")) == build_synthetic_local_snapshot_manifest_dict()


def test_fixture_from_dict_round_trips_to_same_manifest() -> None:
    original = build_synthetic_local_snapshot_manifest()

    restored = LocalSnapshotManifest.from_dict(
        build_synthetic_local_snapshot_manifest_dict()
    )

    assert restored == original


def test_fixture_tuple_fields_are_immutable() -> None:
    item = build_synthetic_local_snapshot_manifest()

    assert isinstance(item.fields, tuple)
    assert isinstance(item.limitations, tuple)
    assert isinstance(item.non_claims, tuple)
    with pytest.raises(TypeError):
        item.fields[0] = "changed"
    with pytest.raises(TypeError):
        item.limitations[0] = "changed"
    with pytest.raises(TypeError):
        item.non_claims[0] = "changed"


def test_fixture_is_not_normal_pytest_eligible() -> None:
    assert build_synthetic_local_snapshot_manifest().normal_pytest_eligible is False
    assert build_synthetic_local_snapshot_manifest_dict()["normal_pytest_eligible"] is False


def test_fixture_includes_all_required_non_claims() -> None:
    item = build_synthetic_local_snapshot_manifest()

    assert item.non_claims == REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS
    assert set(REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS).issubset(item.non_claims)


def test_fixture_contains_no_real_tickers_vendors_credentials_urls_or_paths() -> None:
    serialized = build_synthetic_local_snapshot_manifest_json_bytes().decode("utf-8")
    lowered = serialized.lower()

    for ticker in _REAL_ETF_TICKERS:
        assert re.search(rf"(?<![A-Z0-9]){ticker}(?![A-Z0-9])", serialized.upper()) is None
    for term in _REAL_VENDOR_OR_PROVIDER_TERMS:
        assert term not in lowered
    for term in _CREDENTIAL_TERMS:
        assert term not in lowered
    for marker in _URL_OR_PATH_MARKERS:
        assert marker not in lowered


def test_fixture_approval_validation_and_trading_terms_are_negative_non_claims() -> None:
    payload = build_synthetic_local_snapshot_manifest_dict()

    for field_name, value in _flatten_string_values(payload):
        lowered = value.lower()
        if any(term in lowered for term in _APPROVAL_VALIDATION_TRADING_TERMS):
            assert field_name == "non_claims"
            assert lowered.startswith("not ")


def test_fixture_file_imports_only_date_json_and_manifest_contract() -> None:
    imports = _import_references()

    assert imports <= _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_fixture_file_adds_no_file_path_hash_network_or_runtime_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass_instance(value)
    assert not isinstance(value, (tuple, set, Decimal, date, datetime))
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


def is_dataclass_instance(value: object) -> bool:
    return is_dataclass(value) and not isinstance(value, type)


def _flatten_string_values(value: object, field_name: str = "") -> tuple[tuple[str, str], ...]:
    if isinstance(value, dict):
        flattened: list[tuple[str, str]] = []
        for key, item in value.items():
            flattened.extend(_flatten_string_values(item, str(key)))
        return tuple(flattened)

    if isinstance(value, list):
        flattened = []
        for item in value:
            flattened.extend(_flatten_string_values(item, field_name))
        return tuple(flattened)

    if isinstance(value, str):
        return ((field_name, value),)

    return ()


def _tree() -> ast.AST:
    return ast.parse(FIXTURE_PATH.read_text(encoding="utf-8"), filename=str(FIXTURE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
