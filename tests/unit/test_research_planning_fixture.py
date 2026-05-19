import ast
from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import re
from types import ModuleType

from tests.fixtures.research_methodology import (
    build_synthetic_broad_etf_methodology_scope,
    expected_synthetic_broad_etf_methodology_scope_json,
)
from tests.fixtures.research_planning import (
    build_synthetic_broad_etf_research_planning_package,
    expected_synthetic_broad_etf_research_planning_package_json,
)
from tests.fixtures.research_scope import (
    build_synthetic_broad_etf_research_scope,
    expected_synthetic_broad_etf_research_scope_json,
)


MODULE_PATH = Path("tests/fixtures/research_planning.py")

_ALLOWED_APPROVAL_STATES = {"candidate_only", "blocked", "deferred"}

_REQUIRED_NON_CLAIMS = {
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not strategy validation",
    "not signal approval",
    "not evaluator approval",
    "not trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "no real data ingestion",
}

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
    "IVV",
    "VOO",
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
    "candidate-discovery",
    "candidate_discovery",
    "credential",
    "http://",
    "https://",
    "market data",
    "market-data",
    "password",
    "price",
    "prices",
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


def test_combined_fixture_construction_uses_existing_synthetic_scopes() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    research_scope = build_synthetic_broad_etf_research_scope()
    methodology_scope = build_synthetic_broad_etf_methodology_scope()
    methodology = package["methodology_scope"]["methodology_candidates"][0]

    assert type(package) is dict
    assert tuple(package) == (
        "planning_package_id",
        "as_of_date",
        "research_scope",
        "methodology_scope",
        "limitations",
        "non_claims",
    )
    assert package["planning_package_id"] == (
        "synthetic_broad_etf_research_planning_package_candidate"
    )
    assert package["as_of_date"] == "2026-01-20"
    assert type(package["research_scope"]) is dict
    assert type(package["methodology_scope"]) is dict
    assert package["research_scope"] == research_scope.to_dict()
    assert package["methodology_scope"] == methodology_scope.to_dict()
    assert package["research_scope"]["as_of_date"] == "2026-01-18"
    assert package["methodology_scope"]["as_of_date"] == "2026-01-19"
    assert package["research_scope"]["approval_state"] == "candidate_only"
    assert package["methodology_scope"]["approval_state"] == "candidate_only"
    assert research_scope.scope_id in methodology["linked_scope_ids"]


def test_combined_fixture_keeps_all_embedded_candidates_non_approved() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    approval_states = tuple(_approval_states(package))

    assert set(approval_states) <= _ALLOWED_APPROVAL_STATES
    assert "approved" not in approval_states
    assert set(package["non_claims"]) >= _REQUIRED_NON_CLAIMS

    compact_json = json.dumps(package, separators=(",", ":"))
    scrubbed_json = _scrub_non_claims(compact_json.lower(), package)

    for phrase in (
        "source approval",
        "universe approval",
        "benchmark approval",
        "cash proxy approval",
        "methodology approval",
        "parameter approval",
        "strategy validation",
        "signal approval",
        "evaluator approval",
        "trading authority",
        "real data ingestion",
    ):
        assert phrase not in scrubbed_json


def test_combined_fixture_serialization_is_primitive_and_byte_stable() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    compact_json = json.dumps(package, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(compact_json), separators=(",", ":"))

    assert compact_json == expected_synthetic_broad_etf_research_planning_package_json()
    assert round_tripped == compact_json
    assert json.dumps(package["research_scope"], separators=(",", ":")) == (
        expected_synthetic_broad_etf_research_scope_json()
    )
    assert json.dumps(package["methodology_scope"], separators=(",", ":")) == (
        expected_synthetic_broad_etf_methodology_scope_json()
    )
    _assert_json_payload_safe(package)
    assert " at 0x" not in compact_json
    assert "Research" not in compact_json
    assert "Decimal(" not in compact_json
    assert "datetime." not in compact_json


def test_combined_fixture_contains_no_real_data_or_trading_surface() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    keys = _all_serialized_keys(package)
    compact_json = json.dumps(package, separators=(",", ":"))
    lowered_json = compact_json.lower()
    scrubbed_json = _scrub_non_claims(lowered_json, package)

    assert keys.isdisjoint(_FORBIDDEN_RUNTIME_FIELD_NAMES)
    assert keys.isdisjoint(_FORBIDDEN_SELECTION_FIELD_NAMES)
    assert keys.isdisjoint(_FORBIDDEN_RAW_MARKET_FIELD_NAMES)
    assert '"approval_state":"approved"' not in lowered_json
    assert '"approval_state":"candidate_only"' in lowered_json
    assert "$" not in compact_json
    assert "://" not in compact_json
    assert not re.search(r"\b\d+\.\d+\b", compact_json)

    for forbidden_term in _FORBIDDEN_CONTENT_TERMS:
        assert forbidden_term not in lowered_json
    for forbidden_term in (
        "adjusted close",
        "daily return",
        "market data",
        "ohlc",
        "return series",
        "real data ingestion",
        "volume",
    ):
        assert forbidden_term not in scrubbed_json

    _assert_no_real_etf_tickers(compact_json)
    _assert_no_real_vendor_or_source_identifiers(compact_json)


def test_fixture_module_has_only_allowed_dependencies_and_no_runtime_calls() -> None:
    imports = _import_references()
    imported_research_scope_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "tests.fixtures.research_scope"
        )
        for alias in node.names
    }
    imported_methodology_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "tests.fixtures.research_methodology"
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
        "tests.fixtures.research_methodology",
        "tests.fixtures.research_scope",
    }
    assert imported_research_scope_names == {
        "build_synthetic_broad_etf_research_scope",
        "expected_synthetic_broad_etf_research_scope_json",
    }
    assert imported_methodology_names == {
        "build_synthetic_broad_etf_methodology_scope",
        "expected_synthetic_broad_etf_methodology_scope_json",
    }
    assert violations == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _approval_states(value: object) -> tuple[str, ...]:
    states: list[str] = []

    if isinstance(value, dict):
        approval_state = value.get("approval_state")
        if isinstance(approval_state, str):
            states.append(approval_state)
        for item in value.values():
            states.extend(_approval_states(item))
    elif isinstance(value, list):
        for item in value:
            states.extend(_approval_states(item))

    return tuple(states)


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


def _all_non_claims(value: object) -> tuple[str, ...]:
    claims: list[str] = []

    if isinstance(value, dict):
        non_claims = value.get("non_claims")
        if isinstance(non_claims, list):
            claims.extend(item for item in non_claims if isinstance(item, str))
        for item in value.values():
            claims.extend(_all_non_claims(item))
    elif isinstance(value, list):
        for item in value:
            claims.extend(_all_non_claims(item))

    return tuple(claims)


def _scrub_non_claims(lowered_json: str, payload: dict[str, object]) -> str:
    scrubbed = lowered_json
    for non_claim in sorted(_all_non_claims(payload), key=len, reverse=True):
        scrubbed = scrubbed.replace(non_claim.lower(), "")
    return scrubbed


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
