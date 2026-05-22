import ast
import json
import re
from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from tests.fixtures.research_market_bar import (
    build_synthetic_research_market_bar,
    build_synthetic_research_market_bar_close_to_close_returns,
    build_synthetic_research_market_bar_close_values,
    build_synthetic_research_market_bar_sequence,
    expected_synthetic_research_market_bar_close_to_close_returns_dict,
    expected_synthetic_research_market_bar_close_to_close_returns_json,
    expected_synthetic_research_market_bar_close_values,
    expected_synthetic_research_market_bar_dict,
    expected_synthetic_research_market_bar_json,
    expected_synthetic_research_market_bar_sequence_dict,
    expected_synthetic_research_market_bar_sequence_json,
)


FIXTURE_PATH = Path("tests/fixtures/research_market_bar.py")

_EXPECTED_FIELDS = (
    "symbol",
    "observation_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "currency",
    "calendar_name",
    "adjustment_policy",
    "return_basis",
    "source_category",
    "synthetic_only",
    "candidate_only",
    "non_claims",
)

_EXPECTED_SEQUENCE_FIELDS = (
    "sequence_id",
    "symbol",
    "bar_count",
    "bars",
    "synthetic_only",
    "candidate_only",
    "non_claims",
)

_EXPECTED_RETURN_CONSUMER_FIELDS = (
    "sequence_id",
    "symbol",
    "bar_count",
    "close_values",
    "return_count",
    "close_to_close_returns",
    "return_basis",
    "synthetic_only",
    "candidate_only",
    "non_claims",
)

_EXPECTED_RETURN_ROW_FIELDS = (
    "observation_date",
    "previous_observation_date",
    "previous_close",
    "close",
    "simple_return",
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

_REAL_VENDOR_OR_PROVIDER_TERMS = (
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

_APPROVAL_STATE_KEYS = (
    "approval_state",
    "approved",
    "source_approval",
    "data_approval",
    "endpoint_approval",
    "universe_approval",
)

_FORBIDDEN_TRADING_FIELD_TERMS = (
    "evaluator",
    "portfolio",
    "signal",
    "strategy",
    "trade",
    "trading",
)

_FORBIDDEN_METRIC_FIELD_TERMS = (
    "alpha",
    "beta",
    "cagr",
    "drawdown",
    "rank",
    "recommend",
    "score",
    "sharpe",
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
    "algotrader.research.return_construction",
    "decimal",
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
    "client",
    "connect",
    "download",
    "exists",
    "glob",
    "ingest",
    "is_file",
    "iterdir",
    "mkdir",
    "open",
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
    "socket.socket",
    "stat",
    "submit_order",
    "urlopen",
    "walk",
}

_FORBIDDEN_REFERENCE_NAMES = {
    "Alpaca",
    "api_client",
    "broker",
    "client",
    "evaluator",
    "httpx",
    "ingest",
    "llm",
    "market_data",
    "network",
    "numpy",
    "os",
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
    "trading",
    "vectorbt",
    "yfinance",
}


def test_fixture_output_is_deterministic_across_repeated_calls() -> None:
    first = build_synthetic_research_market_bar()
    second = build_synthetic_research_market_bar()

    assert first == second
    assert first is not second
    assert first == expected_synthetic_research_market_bar_dict()
    assert tuple(first) == _EXPECTED_FIELDS
    assert first["non_claims"] is not second["non_claims"]


def test_sequence_fixture_output_is_deterministic_across_repeated_calls() -> None:
    first = build_synthetic_research_market_bar_sequence()
    second = build_synthetic_research_market_bar_sequence()

    assert first == second
    assert first is not second
    assert first == expected_synthetic_research_market_bar_sequence_dict()
    assert tuple(first) == _EXPECTED_SEQUENCE_FIELDS
    assert first["bars"] is not second["bars"]
    assert first["bars"][0] is not second["bars"][0]
    assert first["non_claims"] is not second["non_claims"]
    assert first["bars"][0]["non_claims"] is not second["bars"][0]["non_claims"]


def test_sequence_close_values_are_extracted_deterministically() -> None:
    first = build_synthetic_research_market_bar_close_values()
    second = build_synthetic_research_market_bar_close_values()
    sequence = build_synthetic_research_market_bar_sequence()

    assert first == second
    assert first is not second
    assert first == expected_synthetic_research_market_bar_close_values()
    assert first == [bar["close"] for bar in sequence["bars"]]


def test_close_to_close_return_consumer_is_deterministic_across_repeated_calls() -> None:
    first = build_synthetic_research_market_bar_close_to_close_returns()
    second = build_synthetic_research_market_bar_close_to_close_returns()

    assert first == second
    assert first is not second
    assert first == expected_synthetic_research_market_bar_close_to_close_returns_dict()
    assert tuple(first) == _EXPECTED_RETURN_CONSUMER_FIELDS
    assert first["close_values"] is not second["close_values"]
    assert first["close_to_close_returns"] is not second["close_to_close_returns"]
    assert first["close_to_close_returns"][0] is not second["close_to_close_returns"][0]
    assert first["non_claims"] is not second["non_claims"]
    assert all(
        tuple(return_row) == _EXPECTED_RETURN_ROW_FIELDS
        for return_row in first["close_to_close_returns"]
    )


def test_fixture_dict_output_is_primitive_only() -> None:
    payload = build_synthetic_research_market_bar()

    _assert_primitive_only(payload)


def test_sequence_fixture_dict_output_is_primitive_only() -> None:
    payload = build_synthetic_research_market_bar_sequence()

    _assert_primitive_only(payload)


def test_close_to_close_return_consumer_output_is_primitive_only() -> None:
    payload = build_synthetic_research_market_bar_close_to_close_returns()

    _assert_primitive_only(payload)


def test_fixture_json_serialization_is_byte_stable() -> None:
    first = _compact_json_bytes(build_synthetic_research_market_bar())
    second = _compact_json_bytes(build_synthetic_research_market_bar())
    expected = expected_synthetic_research_market_bar_json().encode("utf-8")

    assert first == second
    assert first == expected
    assert json.loads(first.decode("utf-8")) == expected_synthetic_research_market_bar_dict()


def test_sequence_fixture_json_serialization_is_byte_stable() -> None:
    first = _compact_json_bytes(build_synthetic_research_market_bar_sequence())
    second = _compact_json_bytes(build_synthetic_research_market_bar_sequence())
    expected = expected_synthetic_research_market_bar_sequence_json().encode("utf-8")

    assert first == second
    assert first == expected
    assert (
        json.loads(first.decode("utf-8"))
        == expected_synthetic_research_market_bar_sequence_dict()
    )


def test_close_to_close_return_consumer_json_serialization_is_byte_stable() -> None:
    first = _compact_json_bytes(
        build_synthetic_research_market_bar_close_to_close_returns()
    )
    second = _compact_json_bytes(
        build_synthetic_research_market_bar_close_to_close_returns()
    )
    expected = expected_synthetic_research_market_bar_close_to_close_returns_json().encode(
        "utf-8"
    )

    assert first == second
    assert first == expected
    assert (
        json.loads(first.decode("utf-8"))
        == expected_synthetic_research_market_bar_close_to_close_returns_dict()
    )


def test_sequence_bars_are_ordered_unique_and_share_one_synthetic_symbol() -> None:
    payload = build_synthetic_research_market_bar_sequence()
    bars = payload["bars"]
    observation_dates = [bar["observation_date"] for bar in bars]
    symbols = {bar["symbol"] for bar in bars}

    assert payload["bar_count"] == 3
    assert len(bars) == payload["bar_count"]
    assert observation_dates == sorted(observation_dates)
    assert len(observation_dates) == len(set(observation_dates))
    assert symbols == {payload["symbol"]}
    assert symbols == {"SYNBARSEQ001"}
    assert all(tuple(bar) == _EXPECTED_FIELDS for bar in bars)


def test_close_to_close_return_count_matches_bar_count_minus_one() -> None:
    payload = build_synthetic_research_market_bar_close_to_close_returns()
    sequence = build_synthetic_research_market_bar_sequence()

    assert payload["bar_count"] == len(payload["close_values"])
    assert payload["return_count"] == payload["bar_count"] - 1
    assert len(payload["close_to_close_returns"]) == payload["return_count"]
    assert [row["observation_date"] for row in payload["close_to_close_returns"]] == [
        bar["observation_date"] for bar in sequence["bars"][1:]
    ]


def test_fixture_uses_only_fake_symbol_values_and_no_real_tickers() -> None:
    payload = build_synthetic_research_market_bar()
    sequence = build_synthetic_research_market_bar_sequence()
    returns = build_synthetic_research_market_bar_close_to_close_returns()
    serialized = _all_expected_fixture_json().upper()

    assert payload["symbol"] == "SYNBAR001"
    assert sequence["symbol"] == "SYNBARSEQ001"
    assert returns["symbol"] == "SYNBARSEQ001"
    for ticker in _REAL_TICKERS:
        assert re.search(rf"(?<![A-Z0-9]){ticker}(?![A-Z0-9])", serialized) is None


def test_fixture_contains_no_vendor_names_credentials_urls_or_data_paths() -> None:
    serialized = _all_expected_fixture_json()
    lowered = serialized.lower()

    for term in _REAL_VENDOR_OR_PROVIDER_TERMS:
        assert term not in lowered
    for term in _CREDENTIAL_TERMS:
        assert term not in lowered
    for marker in _URL_OR_PATH_MARKERS:
        assert marker not in lowered


def test_fixture_has_candidate_and_synthetic_flags_without_approval_state() -> None:
    payloads = (
        build_synthetic_research_market_bar(),
        build_synthetic_research_market_bar_sequence(),
        build_synthetic_research_market_bar_close_to_close_returns(),
    )

    for payload in payloads:
        assert payload["synthetic_only"] is True
        assert payload["candidate_only"] is True
        for key in _APPROVAL_STATE_KEYS:
            assert key not in _flatten_dict_keys(payload)
    assert (
        "approved"
        not in _all_expected_fixture_json().lower()
    )


def test_fixture_has_no_signal_evaluator_portfolio_or_trading_fields() -> None:
    payloads = (
        build_synthetic_research_market_bar(),
        build_synthetic_research_market_bar_sequence(),
        build_synthetic_research_market_bar_close_to_close_returns(),
    )

    for payload in payloads:
        for key in _flatten_dict_keys(payload):
            lowered = key.lower()
            assert all(term not in lowered for term in _FORBIDDEN_TRADING_FIELD_TERMS)


def test_fixture_has_no_metric_ranking_recommendation_fields() -> None:
    payloads = (
        build_synthetic_research_market_bar(),
        build_synthetic_research_market_bar_sequence(),
        build_synthetic_research_market_bar_close_to_close_returns(),
    )

    for payload in payloads:
        for key in _flatten_dict_keys(payload):
            lowered = key.lower()
            assert all(term not in lowered for term in _FORBIDDEN_METRIC_FIELD_TERMS)


def test_fixture_includes_required_non_claims_and_no_extra_claims() -> None:
    payloads = (
        build_synthetic_research_market_bar(),
        build_synthetic_research_market_bar_sequence(),
        build_synthetic_research_market_bar_close_to_close_returns(),
    )

    for payload in payloads:
        non_claims = payload["non_claims"]
        assert isinstance(non_claims, list)
        assert set(non_claims) == _REQUIRED_NON_CLAIMS
        assert all(claim.startswith("not ") for claim in non_claims)

    for bar in build_synthetic_research_market_bar_sequence()["bars"]:
        non_claims = bar["non_claims"]
        assert isinstance(non_claims, list)
        assert set(non_claims) == _REQUIRED_NON_CLAIMS
        assert all(claim.startswith("not ") for claim in non_claims)


def test_fixture_approval_validation_and_trading_terms_are_negative_non_claims() -> None:
    payloads = (
        build_synthetic_research_market_bar(),
        build_synthetic_research_market_bar_sequence(),
        build_synthetic_research_market_bar_close_to_close_returns(),
    )

    for payload in payloads:
        for field_name, value in _flatten_string_values(payload):
            lowered = value.lower()
            if any(term in lowered for term in _APPROVAL_VALIDATION_TRADING_TERMS):
                assert field_name == "non_claims"
                assert lowered.startswith("not ")


def test_fixture_does_not_mutate_across_repeated_calls() -> None:
    first = build_synthetic_research_market_bar()
    first["symbol"] = "CHANGED"
    first["non_claims"].append("changed")

    second = build_synthetic_research_market_bar()

    assert second == expected_synthetic_research_market_bar_dict()
    assert second["symbol"] == "SYNBAR001"
    assert "changed" not in second["non_claims"]


def test_sequence_fixture_does_not_mutate_across_repeated_calls() -> None:
    first = build_synthetic_research_market_bar_sequence()
    first["symbol"] = "CHANGED"
    first["bars"][0]["symbol"] = "CHANGED"
    first["bars"][0]["non_claims"].append("changed")
    first["non_claims"].append("changed")

    second = build_synthetic_research_market_bar_sequence()

    assert second == expected_synthetic_research_market_bar_sequence_dict()
    assert second["symbol"] == "SYNBARSEQ001"
    assert second["bars"][0]["symbol"] == "SYNBARSEQ001"
    assert "changed" not in second["non_claims"]
    assert "changed" not in second["bars"][0]["non_claims"]


def test_close_to_close_return_consumer_does_not_mutate_sequence_fixture() -> None:
    sequence_before = build_synthetic_research_market_bar_sequence()
    first = build_synthetic_research_market_bar_close_to_close_returns()
    first["close_values"][0] = 999.0
    first["close_to_close_returns"][0]["simple_return"] = "changed"
    first["non_claims"].append("changed")

    sequence_after = build_synthetic_research_market_bar_sequence()
    second = build_synthetic_research_market_bar_close_to_close_returns()

    assert sequence_before == expected_synthetic_research_market_bar_sequence_dict()
    assert sequence_after == sequence_before
    assert second == expected_synthetic_research_market_bar_close_to_close_returns_dict()
    assert "changed" not in second["non_claims"]
    assert second["close_to_close_returns"][0]["simple_return"] != "changed"


def test_fixture_file_has_no_vendor_network_runtime_file_or_llm_imports() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_fixture_file_has_no_file_network_production_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def _compact_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _all_expected_fixture_json() -> str:
    return (
        expected_synthetic_research_market_bar_json()
        + expected_synthetic_research_market_bar_sequence_json()
        + expected_synthetic_research_market_bar_close_to_close_returns_json()
    )


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
