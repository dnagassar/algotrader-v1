import ast
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.replay import SyntheticReplaySnapshot
from algotrader.research.research_return_input_package import (
    ResearchReturnInputPackage,
    build_research_return_input_package,
)
from algotrader.research.research_return_input_replay_adapter import (
    build_synthetic_replay_snapshot_from_return_input_package,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)


MODULE_PATH = Path("src/algotrader/research/research_return_input_replay_adapter.py")

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.errors",
    "algotrader.research.asof",
    "algotrader.research.fixture_manifest",
    "algotrader.research.replay",
    "algotrader.research.research_return_input_package",
    "algotrader.research.research_return_input_provenance",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
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
    "polygon_api_client",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "build_synthetic_replay_snapshot",
    "client",
    "close_to_close_returns",
    "connect",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "eval",
    "exec",
    "exists",
    "getenv",
    "glob",
    "import_module",
    "importlib.import_module",
    "ingest",
    "is_file",
    "iterdir",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "parse",
    "Path",
    "persist",
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "requests.get",
    "rglob",
    "simple_return",
    "socket.socket",
    "stat",
    "submit_order",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}

_FORBIDDEN_PAYLOAD_FIELDS = {
    "account",
    "benchmark",
    "broker",
    "cash",
    "cash_returns",
    "cost",
    "costs",
    "fill",
    "fills",
    "order",
    "orders",
    "portfolio",
    "position",
    "positions",
    "signal",
    "signals",
    "strategy",
    "trade",
    "trades",
}

_REAL_TICKERS = (
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

_VENDOR_OR_PROVIDER_TERMS = (
    "alpaca",
    "alpha vantage",
    "bloomberg",
    "factset",
    "finnhub",
    "fred",
    "interactive brokers",
    "massive",
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

_PATH_OR_DATA_SOURCE_MARKERS = (
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
)

_FORBIDDEN_SOURCE_WORDS = (
    "benchmark",
    "broker",
    "cash",
    "cost",
    "costs",
    "endpoint",
    "fill",
    "fills",
    "order",
    "orders",
    "portfolio",
    "position",
    "positions",
    "strategy",
    "trading",
)


def test_phase_121_fixture_package_adapts_to_synthetic_replay_snapshot() -> None:
    package = package_fixture()

    snapshot = build_synthetic_replay_snapshot_from_return_input_package(package)

    assert isinstance(snapshot, SyntheticReplaySnapshot)
    assert snapshot.asof_date == package.snapshot.observation_dates[-1]
    assert len(snapshot.available_points) == len(package.snapshot.observation_dates)
    assert len(snapshot.returns) == len(package.snapshot.close_to_close_returns)


def test_package_fingerprint_and_snapshot_id_are_manifest_provenance() -> None:
    package = package_fixture()

    snapshot = build_synthetic_replay_snapshot_from_return_input_package(package)

    assert snapshot.manifest.fixture_id == package.snapshot.snapshot_id
    assert snapshot.manifest.checksum == f"sha256:{package.fingerprint}"
    assert snapshot.manifest.fixture_kind == "derived"
    assert snapshot.manifest.source_type == "synthetic"
    assert snapshot.manifest.data_start == package.snapshot.observation_dates[0]
    assert snapshot.manifest.data_end == package.snapshot.observation_dates[-1]
    assert snapshot.manifest.non_claims == package.snapshot.non_claims


def test_observation_sequence_and_values_are_preserved() -> None:
    package = package_fixture()

    snapshot = build_synthetic_replay_snapshot_from_return_input_package(package)

    assert tuple(
        point.observation.observation_date for point in snapshot.available_points
    ) == package.snapshot.observation_dates
    assert tuple(
        point.observation.available_after for point in snapshot.available_points
    ) == package.snapshot.observation_dates
    assert tuple(point.value for point in snapshot.available_points) == (
        package.snapshot.close_values
    )
    assert all(
        point.value is close_value
        for point, close_value in zip(
            snapshot.available_points,
            package.snapshot.close_values,
        )
    )


def test_return_values_are_preserved_as_existing_decimal_tuple() -> None:
    package = package_fixture()

    snapshot = build_synthetic_replay_snapshot_from_return_input_package(package)

    assert snapshot.returns is package.snapshot.close_to_close_returns
    assert snapshot.returns == (Decimal("0.05"), Decimal("-0.05"))
    assert all(isinstance(value, Decimal) for value in snapshot.returns)


@pytest.mark.parametrize("value", (object(), None, "not a package"))
def test_adapter_rejects_non_package_input(value: object) -> None:
    with pytest.raises(ValidationError, match="ResearchReturnInputPackage"):
        build_synthetic_replay_snapshot_from_return_input_package(value)


def test_inconsistent_or_mismatched_packages_are_rejected_before_adaptation() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    inconsistent = replace(
        snapshot,
        close_to_close_returns=(Decimal("0.05"), Decimal("-0.049")),
    )

    with pytest.raises(ValidationError, match="close_to_close_returns"):
        build_research_return_input_package(inconsistent)

    with pytest.raises(ValidationError, match="match snapshot"):
        ResearchReturnInputPackage(snapshot=snapshot, fingerprint="0" * 64)


def test_adapter_does_not_mutate_package_or_source_snapshot() -> None:
    package = package_fixture()
    before_payload = package.to_dict()
    before_tuple_ids = (
        id(package.snapshot.observation_dates),
        id(package.snapshot.close_values),
        id(package.snapshot.close_to_close_returns),
        id(package.snapshot.non_claims),
    )

    snapshot = build_synthetic_replay_snapshot_from_return_input_package(package)
    snapshot.to_dict()

    assert package.to_dict() == before_payload
    assert (
        id(package.snapshot.observation_dates),
        id(package.snapshot.close_values),
        id(package.snapshot.close_to_close_returns),
        id(package.snapshot.non_claims),
    ) == before_tuple_ids


def test_adapter_output_adds_no_trading_or_allocation_fields() -> None:
    snapshot = build_synthetic_replay_snapshot_from_return_input_package(package_fixture())
    payload = snapshot.to_dict()

    assert tuple(payload) == (
        "manifest",
        "asof_date",
        "available_points",
        "returns",
    )
    assert all(
        tuple(point_payload) == ("observation_date", "available_after", "value")
        for point_payload in payload["available_points"]
    )
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_PAYLOAD_FIELDS)
    assert all(
        not hasattr(snapshot, field_name) for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )


def test_module_imports_no_forbidden_vendor_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_recompute_or_runtime_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_text_has_no_real_world_or_trading_concepts() -> None:
    source = _source_text()
    upper_source = source.upper()
    lowered = source.lower()

    for ticker in _REAL_TICKERS:
        assert re.search(rf"(?<![A-Z0-9]){ticker}(?![A-Z0-9])", upper_source) is None
    for term in _VENDOR_OR_PROVIDER_TERMS:
        assert term not in lowered
    for term in _CREDENTIAL_TERMS:
        assert term not in lowered
    for marker in _PATH_OR_DATA_SOURCE_MARKERS:
        assert marker not in lowered
    for word in _FORBIDDEN_SOURCE_WORDS:
        assert re.search(rf"(?<![a-z0-9_]){word}(?![a-z0-9_])", lowered) is None


def package_fixture() -> ResearchReturnInputPackage:
    return build_research_return_input_package(
        build_synthetic_research_return_input_snapshot()
    )


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set()
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


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            elif node.level > 0:
                imports.add("__future__")

    return imports


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
