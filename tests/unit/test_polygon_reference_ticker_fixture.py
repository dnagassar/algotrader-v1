import ast
import json
import re
from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from tests.fixtures.polygon_reference_ticker import (
    build_synthetic_polygon_reference_ticker,
    expected_synthetic_polygon_reference_ticker_dict,
    expected_synthetic_polygon_reference_ticker_json,
)


FIXTURE_PATH = Path("tests/fixtures/polygon_reference_ticker.py")

_EXPECTED_FIELDS = (
    "ticker",
    "name",
    "market",
    "locale",
    "primary_exchange",
    "type",
    "active",
    "currency_name",
    "composite_figi",
    "share_class_figi",
    "cik",
    "last_updated_utc",
    "source_category",
    "official_doc_status",
    "candidate_only",
    "non_claims",
)

_REQUIRED_NON_CLAIMS = {
    "not Polygon approval",
    "not Massive approval",
    "not endpoint approval",
    "not source approval",
    "not data approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not evidence approval",
    "not return-construction approval",
    "not no-lookahead approval",
    "not strategy validation",
    "not trading readiness",
}

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

_FORBIDDEN_DATA_FIELD_TERMS = (
    "adjusted",
    "bar",
    "benchmark",
    "cash_proxy",
    "close",
    "dividend",
    "high",
    "low",
    "ohlc",
    "ohlcv",
    "open",
    "price",
    "quote",
    "return",
    "returns",
    "signal",
    "split",
    "strategy",
    "trade",
    "volume",
    "vwap",
)

_FORBIDDEN_CREDENTIAL_URL_OR_PATH_MARKERS = (
    "://",
    ".com",
    ".csv",
    ".data",
    ".jsonl",
    ".parquet",
    ".zip",
    "api_key",
    "apikey",
    "bearer",
    "client_secret",
    "credential",
    "market-data",
    "market_data",
    "oauth",
    "password",
    "private_key",
    "secret",
    "token",
    "www.",
)

_APPROVAL_STATE_KEYS = (
    "approval_state",
    "approved",
    "source_approval",
    "data_approval",
    "endpoint_approval",
    "universe_approval",
)

_ALLOWED_IMPORTS = {"__future__"}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
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
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_CALL_NAMES = {
    "connect",
    "download",
    "exists",
    "glob",
    "is_file",
    "iterdir",
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
    "socket.socket",
    "stat",
    "submit_order",
    "urlopen",
    "walk",
}

_FORBIDDEN_REFERENCE_NAMES = {
    "Alpaca",
    "broker",
    "httpx",
    "llm",
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


def test_fixture_output_is_deterministic_across_repeated_calls() -> None:
    first = build_synthetic_polygon_reference_ticker()
    second = build_synthetic_polygon_reference_ticker()

    assert first == second
    assert first is not second
    assert first == expected_synthetic_polygon_reference_ticker_dict()
    assert tuple(first) == _EXPECTED_FIELDS
    assert first["non_claims"] is not second["non_claims"]


def test_fixture_dict_output_is_primitive_only() -> None:
    payload = build_synthetic_polygon_reference_ticker()

    _assert_primitive_only(payload)


def test_fixture_json_serialization_is_byte_stable() -> None:
    first = _compact_json_bytes(build_synthetic_polygon_reference_ticker())
    second = _compact_json_bytes(build_synthetic_polygon_reference_ticker())
    expected = expected_synthetic_polygon_reference_ticker_json().encode("utf-8")

    assert first == second
    assert first == expected
    assert json.loads(first.decode("utf-8")) == expected_synthetic_polygon_reference_ticker_dict()


def test_fixture_uses_only_fake_symbol_values_and_no_real_etf_tickers() -> None:
    payload = build_synthetic_polygon_reference_ticker()
    serialized = expected_synthetic_polygon_reference_ticker_json().upper()

    assert payload["ticker"] == "SYNREF001"
    assert payload["name"] == "Synthetic Reference Ticker Placeholder"
    for ticker in _REAL_ETF_TICKERS:
        assert re.search(rf"(?<![A-Z0-9]){ticker}(?![A-Z0-9])", serialized) is None


def test_fixture_has_no_market_data_or_ohlcv_price_return_fields() -> None:
    payload = build_synthetic_polygon_reference_ticker()

    for key in payload:
        lowered = key.lower()
        assert all(term not in lowered for term in _FORBIDDEN_DATA_FIELD_TERMS)
    assert "last_updated_utc" in payload
    assert "market" in payload


def test_fixture_has_no_credentials_urls_paths_or_data_file_markers() -> None:
    serialized = expected_synthetic_polygon_reference_ticker_json().lower()

    for marker in _FORBIDDEN_CREDENTIAL_URL_OR_PATH_MARKERS:
        assert marker not in serialized


def test_fixture_has_candidate_only_flag_without_approval_state_fields() -> None:
    payload = build_synthetic_polygon_reference_ticker()

    assert payload["candidate_only"] is True
    for key in _APPROVAL_STATE_KEYS:
        assert key not in payload
    assert "approved" not in expected_synthetic_polygon_reference_ticker_json().lower()


def test_fixture_includes_required_non_claims_and_implies_no_approvals() -> None:
    payload = build_synthetic_polygon_reference_ticker()
    non_claims = payload["non_claims"]

    assert isinstance(non_claims, list)
    assert set(non_claims) == _REQUIRED_NON_CLAIMS
    assert all(claim.startswith("not ") for claim in non_claims)
    assert {"not source approval", "not data approval", "not endpoint approval"}.issubset(
        non_claims
    )
    assert "not universe approval" in non_claims


def test_fixture_approval_validation_and_trading_terms_are_negative_non_claims() -> None:
    payload = build_synthetic_polygon_reference_ticker()
    controlled_terms = ("approval", "validation", "readiness", "strategy", "trading")

    for field_name, value in _flatten_string_values(payload):
        lowered = value.lower()
        if any(term in lowered for term in controlled_terms):
            assert field_name == "non_claims"
            assert lowered.startswith("not ")


def test_fixture_does_not_mutate_across_repeated_calls() -> None:
    first = build_synthetic_polygon_reference_ticker()
    first["ticker"] = "CHANGED"
    first["non_claims"].append("changed")

    second = build_synthetic_polygon_reference_ticker()

    assert second == expected_synthetic_polygon_reference_ticker_dict()
    assert second["ticker"] == "SYNREF001"
    assert "changed" not in second["non_claims"]


def test_fixture_file_has_no_vendor_network_runtime_file_or_llm_imports() -> None:
    imports = _import_references()

    assert imports <= _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_fixture_file_has_no_file_network_broker_runtime_or_llm_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def _compact_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


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
