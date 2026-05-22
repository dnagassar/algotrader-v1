import ast
import json
import re
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
    expected_synthetic_research_return_input_snapshot_dict,
)


FIXTURE_PATH = Path("tests/fixtures/research_return_input.py")

_EXPECTED_FIELDS = (
    "snapshot_id",
    "symbol",
    "observation_dates",
    "close_values",
    "close_to_close_returns",
    "return_basis",
    "adjustment_policy",
    "synthetic_only",
    "candidate_only",
    "non_claims",
)

_REQUIRED_NON_CLAIMS = {
    "not source approval",
    "not data approval",
    "not endpoint approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not evidence approval",
    "not return-construction approval",
    "not no-lookahead approval",
    "not strategy validation",
    "not trading readiness",
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
    "data_source",
    "data-source",
    "market-data",
    "market_data",
)

_APPROVAL_STATE_KEYS = (
    "approval_state",
    "approved",
    "source_approval",
    "data_approval",
    "endpoint_approval",
    "universe_approval",
    "benchmark_approval",
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
    "datetime",
    "decimal",
    "algotrader.research.research_return_input",
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
    "client",
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
    "hash",
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
    "random",
    "random.random",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "requests.get",
    "rglob",
    "socket.socket",
    "stat",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}

_FORBIDDEN_REFERENCE_NAMES = {
    "Alpaca",
    "api_client",
    "broker",
    "client",
    "evaluator",
    "execution",
    "httpx",
    "ingest",
    "loader",
    "market_bar",
    "network",
    "numpy",
    "open",
    "pandas",
    "parser",
    "Path",
    "pathlib",
    "portfolio",
    "QuantConnect",
    "requests",
    "runtime",
    "signal",
    "socket",
    "strategy",
    "trade",
    "vectorbt",
    "vendor",
    "yfinance",
}


def test_fixture_builds_valid_research_return_input_snapshot() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    assert isinstance(snapshot, ResearchReturnInputSnapshot)
    assert is_dataclass(snapshot)
    assert snapshot.snapshot_id == "synthetic_return_input_snapshot_fixture_001"
    assert snapshot.symbol == "SYNRET121X"
    assert snapshot.observation_dates == (
        date(2099, 1, 3),
        date(2099, 1, 4),
        date(2099, 1, 7),
    )
    assert snapshot.close_values == (
        Decimal("10.0000"),
        Decimal("10.5000"),
        Decimal("9.9750"),
    )
    assert snapshot.close_to_close_returns == (
        Decimal("0.05"),
        Decimal("-0.05"),
    )
    assert snapshot.synthetic_only is True
    assert snapshot.candidate_only is True
    assert set(snapshot.non_claims) == _REQUIRED_NON_CLAIMS
    assert tuple(snapshot.to_dict()) == _EXPECTED_FIELDS


def test_fixture_output_is_frozen_and_immutable_through_contract() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    with pytest.raises(FrozenInstanceError):
        snapshot.symbol = "CHANGED"
    with pytest.raises(TypeError):
        snapshot.close_values[0] = Decimal("0")
    with pytest.raises(TypeError):
        snapshot.non_claims[0] = "not changed"


def test_fixture_to_dict_exactly_matches_expected_primitives() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    payload = snapshot.to_dict()

    assert payload == expected_synthetic_research_return_input_snapshot_dict()
    assert payload is not expected_synthetic_research_return_input_snapshot_dict()
    assert payload["non_claims"] is not (
        expected_synthetic_research_return_input_snapshot_dict()["non_claims"]
    )
    _assert_primitive_only(payload)


def test_fixture_json_serialization_is_deterministic_with_sorted_keys() -> None:
    first = _sorted_compact_json(
        build_synthetic_research_return_input_snapshot().to_dict()
    )
    second = _sorted_compact_json(
        build_synthetic_research_return_input_snapshot().to_dict()
    )
    expected = _sorted_compact_json(
        expected_synthetic_research_return_input_snapshot_dict()
    )

    assert first == second == expected
    assert json.loads(first) == expected_synthetic_research_return_input_snapshot_dict()
    assert first.startswith('{"adjustment_policy":')


def test_fixture_from_dict_round_trips_to_same_snapshot() -> None:
    expected = expected_synthetic_research_return_input_snapshot_dict()
    snapshot = build_synthetic_research_return_input_snapshot()
    reloaded = ResearchReturnInputSnapshot.from_dict(expected)

    assert reloaded == snapshot
    assert reloaded is not snapshot
    assert reloaded.to_dict() == expected


def test_fixture_content_contains_no_real_ticker_vendor_path_or_credential_strings() -> None:
    serialized = _sorted_compact_json(
        expected_synthetic_research_return_input_snapshot_dict()
    )
    upper_serialized = serialized.upper()
    lowered = serialized.lower()

    assert "SYNRET121X" in upper_serialized
    for ticker in _REAL_TICKERS:
        assert re.search(rf"(?<![A-Z0-9]){ticker}(?![A-Z0-9])", upper_serialized) is None
    for term in _VENDOR_OR_PROVIDER_TERMS:
        assert term not in lowered
    for term in _CREDENTIAL_TERMS:
        assert term not in lowered
    for marker in _PATH_OR_DATA_SOURCE_MARKERS:
        assert marker not in lowered


def test_fixture_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_fixture_remains_synthetic_only_and_advisory_candidate_only() -> None:
    payload = expected_synthetic_research_return_input_snapshot_dict()
    lowered_json = _sorted_compact_json(payload).lower()
    scrubbed_json = lowered_json

    assert payload["synthetic_only"] is True
    assert payload["candidate_only"] is True
    assert set(payload["non_claims"]) == _REQUIRED_NON_CLAIMS
    assert all(claim.startswith("not ") for claim in payload["non_claims"])
    assert all(key not in _flatten_dict_keys(payload) for key in _APPROVAL_STATE_KEYS)

    for required_non_claim in _REQUIRED_NON_CLAIMS:
        scrubbed_json = scrubbed_json.replace(required_non_claim, "")
    for term in _APPROVAL_VALIDATION_TRADING_TERMS:
        assert term not in scrubbed_json


def _sorted_compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass(value)
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


def _flatten_dict_keys(value: object) -> tuple[str, ...]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_flatten_dict_keys(item))
        return tuple(keys)

    if isinstance(value, list):
        keys = []
        for item in value:
            keys.extend(_flatten_dict_keys(item))
        return tuple(keys)

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
