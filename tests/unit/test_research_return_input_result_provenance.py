import ast
import re
from dataclasses import replace
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_input_package import (
    ResearchReturnInputPackage,
    build_research_return_input_package,
)
from algotrader.research.research_return_input_result_adapter import (
    build_synthetic_research_result_from_return_input_package,
)
from algotrader.research.research_return_input_result_provenance import (
    validate_research_result_matches_return_input_package,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)
from tests.fixtures.research_return_input_result import (
    build_synthetic_return_input_research_result,
)


MODULE_PATH = Path(
    "src/algotrader/research/research_return_input_result_provenance.py"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.errors",
    "algotrader.research.replay_result",
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
    "build_synthetic_replay_snapshot_from_return_input_package",
    "build_synthetic_research_result",
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
    "summarize_synthetic_replay_snapshot",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}

_FORBIDDEN_PAYLOAD_FIELDS = {
    "account",
    "benchmark",
    "benchmarks",
    "broker",
    "brokers",
    "cash",
    "cash_return",
    "cash_returns",
    "cost",
    "costs",
    "evaluator",
    "evaluators",
    "fill",
    "fills",
    "order",
    "orders",
    "portfolio",
    "portfolios",
    "position",
    "positions",
    "runtime",
    "runtimes",
    "signal",
    "signals",
    "strategy",
    "strategy_state",
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
    "brokers",
    "cash",
    "cost",
    "costs",
    "fill",
    "fills",
    "order",
    "orders",
    "portfolio",
    "portfolios",
    "position",
    "positions",
    "signal",
    "signals",
)


def test_phase_129_fixture_result_matches_package_used_to_derive_it() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    verified = validate_research_result_matches_return_input_package(
        package,
        result,
    )

    assert verified is result
    assert result.snapshot.manifest.fixture_id == package.snapshot.snapshot_id
    assert result.snapshot.manifest.checksum == f"sha256:{package.fingerprint}"


def test_phase_129_fixture_result_matches_equivalent_package() -> None:
    package = package_fixture()
    result = build_synthetic_return_input_research_result()

    verified = validate_research_result_matches_return_input_package(
        package,
        result,
    )

    assert verified is result


def test_verifier_returns_same_result_object_on_success() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    verified = validate_research_result_matches_return_input_package(
        package,
        result,
    )

    assert verified is result
    assert verified.snapshot is result.snapshot
    assert verified.summary is result.summary


def test_mismatched_fixture_id_is_rejected() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)
    bad_manifest = replace(
        result.snapshot.manifest,
        fixture_id="synthetic_return_input_snapshot_fixture_002",
    )
    bad_result = replace(
        result,
        snapshot=replace(result.snapshot, manifest=bad_manifest),
    )

    with pytest.raises(ValidationError, match="fixture_id"):
        validate_research_result_matches_return_input_package(package, bad_result)


def test_mismatched_checksum_is_rejected() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)
    bad_manifest = replace(
        result.snapshot.manifest,
        checksum=f"sha256:{'0' * 64}",
    )
    bad_result = replace(
        result,
        snapshot=replace(result.snapshot, manifest=bad_manifest),
    )

    with pytest.raises(ValidationError, match="checksum"):
        validate_research_result_matches_return_input_package(package, bad_result)


@pytest.mark.parametrize("value", (object(), None, "not a package"))
def test_non_package_input_is_rejected(value: object) -> None:
    result = build_synthetic_return_input_research_result()

    with pytest.raises(ValidationError, match="ResearchReturnInputPackage"):
        validate_research_result_matches_return_input_package(value, result)


@pytest.mark.parametrize("value", (object(), None, "not a result"))
def test_non_result_input_is_rejected(value: object) -> None:
    package = package_fixture()

    with pytest.raises(ValidationError, match="SyntheticResearchResult"):
        validate_research_result_matches_return_input_package(package, value)


def test_verifier_does_not_mutate_package_or_result() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)
    package_payload = package.to_dict()
    result_payload = result.to_dict()
    identity_snapshot = (
        id(package.snapshot),
        id(package.snapshot.observation_dates),
        id(package.snapshot.close_values),
        id(package.snapshot.close_to_close_returns),
        id(result.snapshot),
        id(result.snapshot.manifest),
        id(result.snapshot.available_points),
        id(result.snapshot.returns),
        id(result.summary),
    )

    validate_research_result_matches_return_input_package(package, result)

    assert package.to_dict() == package_payload
    assert result.to_dict() == result_payload
    assert (
        id(package.snapshot),
        id(package.snapshot.observation_dates),
        id(package.snapshot.close_values),
        id(package.snapshot.close_to_close_returns),
        id(result.snapshot),
        id(result.snapshot.manifest),
        id(result.snapshot.available_points),
        id(result.snapshot.returns),
        id(result.summary),
    ) == identity_snapshot


def test_verifier_does_not_rebuild_or_alter_metrics_or_results() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)
    summary_before = result.summary
    snapshot_before = result.snapshot
    payload_before = result.to_dict()

    verified = validate_research_result_matches_return_input_package(
        package,
        result,
    )

    assert verified is result
    assert result.snapshot is snapshot_before
    assert result.summary is summary_before
    assert result.to_dict() == payload_before
    assert _call_names().isdisjoint(
        {
            "build_synthetic_replay_snapshot_from_return_input_package",
            "build_synthetic_research_result",
            "summarize_synthetic_replay_snapshot",
        }
    )


def test_verifier_introduces_no_trading_runtime_or_allocation_fields() -> None:
    package = package_fixture()
    result = validate_research_result_matches_return_input_package(
        package,
        build_synthetic_research_result_from_return_input_package(package),
    )
    payload = result.to_dict()

    assert tuple(payload) == ("snapshot", "summary")
    assert tuple(payload["snapshot"]) == (
        "manifest",
        "asof_date",
        "available_points",
        "returns",
    )
    assert tuple(payload["summary"]) == (
        "point_count",
        "return_count",
        "starting_value",
        "ending_value",
        "cumulative_simple_return",
        "min_return",
        "max_return",
        "mean_return",
    )
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_PAYLOAD_FIELDS)
    assert all(
        not hasattr(result, field_name) for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )
    assert all(
        not hasattr(result.snapshot, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )
    assert all(
        not hasattr(result.summary, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )


def test_module_imports_no_forbidden_vendor_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_persistence_runtime_or_rebuild_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_text_has_no_real_world_or_trading_path_concepts() -> None:
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
