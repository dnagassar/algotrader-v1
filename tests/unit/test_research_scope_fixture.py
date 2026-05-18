import ast
from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import re
from types import ModuleType

from algotrader.research.research_scope import (
    REQUIRED_RESEARCH_SCOPE_NON_CLAIMS,
    ResearchBenchmarkCandidate,
    ResearchCashProxyCandidate,
    ResearchDataSourceCandidate,
    ResearchScopeSnapshot,
    ResearchUniverseCandidate,
)
from tests.fixtures.research_scope import (
    build_synthetic_broad_etf_research_scope,
    expected_synthetic_broad_etf_research_scope_dict,
    expected_synthetic_broad_etf_research_scope_json,
)


MODULE_PATH = Path("tests/fixtures/research_scope.py")

_ALLOWED_APPROVAL_STATES = {"candidate_only", "blocked", "deferred"}

_REAL_ETF_TICKERS = (
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "VTI",
    "EFA",
    "EEM",
    "TLT",
    "GLD",
    "AGG",
    "BND",
    "VNQ",
    "XLF",
    "XLK",
    "XLE",
)

_REAL_VENDOR_OR_SOURCE_IDENTIFIERS = (
    "alpaca",
    "alphavantage",
    "alpha_vantage",
    "bloomberg",
    "eodhd",
    "factset",
    "fmp",
    "iex",
    "intrinio",
    "morningstar",
    "nasdaq",
    "polygon",
    "quandl",
    "refinitiv",
    "stooq",
    "tiingo",
    "yahoo",
    "yfinance",
)

_FORBIDDEN_RUNTIME_FIELD_NAMES = {
    "account",
    "account_id",
    "allocation",
    "broker",
    "credential",
    "credentials",
    "execution",
    "fill",
    "order",
    "portfolio",
    "position",
    "runtime",
    "scheduler",
    "target_weight",
}

_FORBIDDEN_SELECTION_FIELD_NAMES = {
    "candidate_discovery",
    "candidate_discovery_fields",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "score",
    "scoring",
}

_FORBIDDEN_RAW_MARKET_FIELD_NAMES = {
    "adjusted_close",
    "adj_close",
    "close",
    "dividend",
    "high",
    "low",
    "ohlc",
    "ohlcv",
    "open",
    "price",
    "prices",
    "split",
    "volume",
}

_FORBIDDEN_CONTENT_TERMS = (
    "account_id",
    "api_key",
    "candidate discovery",
    "candidate_discovery",
    "credential",
    "http://",
    "https://",
    "market data",
    "market-data",
    "password",
    "price",
    "ranking",
    "recommendation",
    "returns",
    "score",
    "scoring",
    "secret",
    "ticker",
    "token",
    "vendor",
)

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.governance",
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
    "csv",
    "database",
    "duckdb",
    "http",
    "httpx",
    "ipynb",
    "langchain",
    "langgraph",
    "llm",
    "market_data",
    "notebook",
    "numpy",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "persistence",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "sqlmodel",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "eval",
    "exec",
    "getenv",
    "import_module",
    "importlib.import_module",
    "open",
    "os.environ.get",
    "os.getenv",
    "Path",
    "post",
    "random",
    "random.random",
    "read",
    "read_csv",
    "read_text",
    "request",
    "rglob",
    "socket.socket",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "write",
    "write_text",
}

_OBJECT_REPR_PATTERN = re.compile(r"<[^>]+ at 0x[0-9a-fA-F]+>")
_MEMORY_ADDRESS_PATTERN = re.compile(r"\b0x[0-9a-fA-F]{6,}\b")


def test_fixture_construction_returns_expected_candidate_contracts() -> None:
    scope = build_synthetic_broad_etf_research_scope()

    assert isinstance(scope, ResearchScopeSnapshot)
    assert scope.as_of_date == date(2026, 1, 18)
    assert scope.approval_state == "candidate_only"
    assert len(scope.source_candidates) == 1
    assert len(scope.universe_candidates) == 1
    assert len(scope.benchmark_candidates) == 1
    assert len(scope.cash_proxy_candidates) == 1
    assert isinstance(scope.source_candidates[0], ResearchDataSourceCandidate)
    assert isinstance(scope.universe_candidates[0], ResearchUniverseCandidate)
    assert isinstance(scope.benchmark_candidates[0], ResearchBenchmarkCandidate)
    assert isinstance(scope.cash_proxy_candidates[0], ResearchCashProxyCandidate)
    assert scope.universe_candidates[0].asset_ids == (
        "synthetic_us_equity_etf_candidate",
        "synthetic_developed_ex_us_etf_candidate",
        "synthetic_emerging_market_etf_candidate",
        "synthetic_treasury_duration_etf_candidate",
    )

    approval_states = _approval_states(scope)
    assert set(approval_states) <= _ALLOWED_APPROVAL_STATES
    assert "approved" not in approval_states

    for item in _scope_and_candidates(scope):
        assert item.blockers
        assert item.limitations
        assert item.required_follow_up
        assert item.non_claims == REQUIRED_RESEARCH_SCOPE_NON_CLAIMS

    serialized = json.dumps(scope.to_dict(), separators=(",", ":"))
    _assert_no_real_etf_tickers(serialized)
    _assert_no_real_vendor_or_source_identifiers(serialized)
    _assert_no_raw_market_data(scope.to_dict(), serialized)


def test_fixture_serialization_matches_expected_primitives_and_compact_json() -> None:
    scope = build_synthetic_broad_etf_research_scope()
    payload = scope.to_dict()
    compact_json = json.dumps(payload, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(compact_json), separators=(",", ":"))

    assert payload == expected_synthetic_broad_etf_research_scope_dict()
    assert compact_json == expected_synthetic_broad_etf_research_scope_json()
    assert round_tripped == compact_json
    _assert_json_payload_safe(payload)
    assert " at 0x" not in compact_json
    assert "Research" not in compact_json
    assert "Decimal(" not in compact_json
    assert "datetime." not in compact_json


def test_fixture_construction_and_serialization_are_deterministic() -> None:
    first_scope = build_synthetic_broad_etf_research_scope()
    second_scope = build_synthetic_broad_etf_research_scope()

    assert first_scope == second_scope
    assert first_scope is not second_scope
    assert first_scope.source_candidates[0] is not second_scope.source_candidates[0]

    first_payload = first_scope.to_dict()
    second_payload = first_scope.to_dict()
    third_payload = second_scope.to_dict()
    first_json = json.dumps(first_payload, separators=(",", ":"))
    second_json = json.dumps(second_payload, separators=(",", ":"))
    third_json = json.dumps(third_payload, separators=(",", ":"))

    assert first_payload == second_payload == third_payload
    assert first_json == second_json == third_json
    assert first_json == expected_synthetic_broad_etf_research_scope_json()


def test_fixture_output_contains_no_runtime_selection_or_affirmative_approval_surface() -> None:
    payload = build_synthetic_broad_etf_research_scope().to_dict()
    keys = _all_serialized_keys(payload)
    compact_json = json.dumps(payload, separators=(",", ":"))
    lowered_json = compact_json.lower()

    assert keys.isdisjoint(_FORBIDDEN_RUNTIME_FIELD_NAMES)
    assert keys.isdisjoint(_FORBIDDEN_SELECTION_FIELD_NAMES)
    assert keys.isdisjoint(_FORBIDDEN_RAW_MARKET_FIELD_NAMES)
    assert '"approval_state":"approved"' not in lowered_json
    assert '"approval_state":"candidate_only"' in lowered_json
    assert "approved" not in lowered_json
    assert "$" not in compact_json
    assert "://" not in compact_json
    assert not re.search(r"\b\d+\.\d+\b", compact_json)
    for forbidden_term in _FORBIDDEN_CONTENT_TERMS:
        assert forbidden_term not in lowered_json

    _assert_no_real_etf_tickers(compact_json)
    _assert_no_real_vendor_or_source_identifiers(compact_json)
    _assert_no_affirmative_approval_claims(lowered_json)


def test_fixture_module_has_only_allowed_imports_and_no_io_network_clock_calls() -> None:
    imports = _import_references()
    imported_datetime_names = {
        alias.name
        for node in ast.walk(_tree())
        if isinstance(node, ast.ImportFrom) and node.module == "datetime"
        for alias in node.names
    }
    imported_contract_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "algotrader.research.research_scope"
        )
        for alias in node.names
    }
    violations = [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert imports == {
        "__future__",
        "datetime",
        "algotrader.research.research_scope",
    }
    assert imported_datetime_names == {"date"}
    assert imported_contract_names == {
        "ResearchBenchmarkCandidate",
        "ResearchCashProxyCandidate",
        "ResearchDataSourceCandidate",
        "ResearchScopeSnapshot",
        "ResearchUniverseCandidate",
    }
    assert violations == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _approval_states(scope: ResearchScopeSnapshot) -> tuple[str, ...]:
    return tuple(item.approval_state for item in _scope_and_candidates(scope))


def _scope_and_candidates(scope: ResearchScopeSnapshot) -> tuple[object, ...]:
    return (
        scope,
        *scope.source_candidates,
        *scope.universe_candidates,
        *scope.benchmark_candidates,
        *scope.cash_proxy_candidates,
    )


def _assert_json_payload_safe(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, tuple)
    assert not isinstance(value, set)
    assert not isinstance(value, Decimal)
    assert not isinstance(value, (date, datetime))
    assert not callable(value)
    assert not isinstance(value, ModuleType)

    if value is None or type(value) in (str, bool, int, float):
        if type(value) is str:
            assert not _OBJECT_REPR_PATTERN.search(value)
            assert not _MEMORY_ADDRESS_PATTERN.search(value)
        return

    if type(value) is list:
        for item in value:
            _assert_json_payload_safe(item)
        return

    if type(value) is dict:
        for key, item in value.items():
            assert type(key) is str
            assert not _OBJECT_REPR_PATTERN.search(key)
            assert not _MEMORY_ADDRESS_PATTERN.search(key)
            _assert_json_payload_safe(item)
        return

    raise AssertionError(f"non-primitive serialized value: {type(value)!r}")


def _all_serialized_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_serialized_keys(item))
        return keys

    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_serialized_keys(item))
        return keys

    return set()


def _assert_no_real_etf_tickers(serialized: str) -> None:
    for ticker in _REAL_ETF_TICKERS:
        assert not re.search(
            rf"(?<![A-Z0-9_]){re.escape(ticker)}(?![A-Z0-9_])",
            serialized,
        )


def _assert_no_real_vendor_or_source_identifiers(serialized: str) -> None:
    lowered = serialized.lower()
    for identifier in _REAL_VENDOR_OR_SOURCE_IDENTIFIERS:
        assert identifier not in lowered


def _assert_no_raw_market_data(payload: dict[str, object], serialized: str) -> None:
    assert _all_serialized_keys(payload).isdisjoint(_FORBIDDEN_RAW_MARKET_FIELD_NAMES)
    lowered = serialized.lower()
    assert "adjusted close" not in lowered
    assert "daily return" not in lowered
    assert "return series" not in lowered
    assert "ohlc" not in lowered
    assert "volume" not in lowered
    assert "$" not in serialized


def _assert_no_affirmative_approval_claims(lowered_json: str) -> None:
    scrubbed = lowered_json
    for required_non_claim in REQUIRED_RESEARCH_SCOPE_NON_CLAIMS:
        scrubbed = scrubbed.replace(required_non_claim, "")

    for phrase in (
        "source approval",
        "universe approval",
        "benchmark approval",
        "cash proxy approval",
        "strategy validation",
        "signal approval",
        "trading authority",
    ):
        assert phrase not in scrubbed


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


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


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
