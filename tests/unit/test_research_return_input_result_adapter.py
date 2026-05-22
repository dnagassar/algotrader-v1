import ast
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import research_return_input_result_adapter as module
from algotrader.research.replay_result import (
    SyntheticResearchResult,
    build_synthetic_research_result,
)
from algotrader.research.research_return_input_package import (
    ResearchReturnInputPackage,
    build_research_return_input_package,
)
from algotrader.research.research_return_input_replay_adapter import (
    build_synthetic_replay_snapshot_from_return_input_package,
)
from algotrader.research.research_return_input_result_adapter import (
    build_synthetic_research_result_from_return_input_package,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)


MODULE_PATH = Path("src/algotrader/research/research_return_input_result_adapter.py")

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.errors",
    "algotrader.research.replay_result",
    "algotrader.research.research_return_input_package",
    "algotrader.research.research_return_input_replay_adapter",
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
    "socket.socket",
    "stat",
    "submit_order",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}

_FORBIDDEN_METRIC_CALL_NAMES = {
    "SyntheticReplaySummary",
    "max",
    "min",
    "sum",
    "summarize_synthetic_replay_snapshot",
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
    "cash",
    "cost",
    "costs",
    "fill",
    "fills",
    "order",
    "orders",
    "portfolio",
    "position",
    "positions",
)


def test_phase_121_fixture_package_adapts_to_synthetic_research_result() -> None:
    package = package_fixture()

    result = build_synthetic_research_result_from_return_input_package(package)

    assert isinstance(result, SyntheticResearchResult)
    assert result.snapshot.asof_date == package.snapshot.observation_dates[-1]
    assert len(result.snapshot.available_points) == len(
        package.snapshot.observation_dates
    )
    assert len(result.snapshot.returns) == len(
        package.snapshot.close_to_close_returns
    )


def test_result_contains_replay_snapshot_derived_from_package() -> None:
    package = package_fixture()
    expected_snapshot = build_synthetic_replay_snapshot_from_return_input_package(
        package
    )

    result = build_synthetic_research_result_from_return_input_package(package)

    assert result.snapshot == expected_snapshot
    assert result.snapshot.manifest.fixture_id == package.snapshot.snapshot_id
    assert tuple(point.value for point in result.snapshot.available_points) == (
        package.snapshot.close_values
    )


def test_package_fingerprint_and_snapshot_id_remain_manifest_provenance() -> None:
    package = package_fixture()

    result = build_synthetic_research_result_from_return_input_package(package)
    manifest = result.snapshot.manifest

    assert manifest.fixture_id == package.snapshot.snapshot_id
    assert manifest.checksum == f"sha256:{package.fingerprint}"
    assert manifest.fixture_kind == "derived"
    assert manifest.source_type == "synthetic"
    assert manifest.data_start == package.snapshot.observation_dates[0]
    assert manifest.data_end == package.snapshot.observation_dates[-1]
    assert manifest.non_claims == package.snapshot.non_claims


def test_observation_sequence_and_values_are_preserved() -> None:
    package = package_fixture()

    result = build_synthetic_research_result_from_return_input_package(package)

    assert tuple(
        point.observation.observation_date
        for point in result.snapshot.available_points
    ) == package.snapshot.observation_dates
    assert tuple(
        point.observation.available_after for point in result.snapshot.available_points
    ) == package.snapshot.observation_dates
    assert tuple(point.value for point in result.snapshot.available_points) == (
        package.snapshot.close_values
    )
    assert all(
        point.value is close_value
        for point, close_value in zip(
            result.snapshot.available_points,
            package.snapshot.close_values,
        )
    )


def test_return_values_are_preserved_as_existing_decimal_tuple() -> None:
    package = package_fixture()

    result = build_synthetic_research_result_from_return_input_package(package)

    assert result.snapshot.returns is package.snapshot.close_to_close_returns
    assert result.snapshot.returns == (Decimal("0.05"), Decimal("-0.05"))
    assert all(isinstance(value, Decimal) for value in result.snapshot.returns)


def test_summary_metrics_come_from_existing_result_builder(monkeypatch: object) -> None:
    package = package_fixture()
    calls: list[tuple[str, object]] = []
    real_replay_adapter = module.build_synthetic_replay_snapshot_from_return_input_package
    real_result_builder = module.build_synthetic_research_result

    def recording_replay_adapter(value: ResearchReturnInputPackage) -> object:
        calls.append(("replay", value))
        return real_replay_adapter(value)

    def recording_result_builder(snapshot: object) -> SyntheticResearchResult:
        calls.append(("result", snapshot))
        return real_result_builder(snapshot)

    monkeypatch.setattr(
        module,
        "build_synthetic_replay_snapshot_from_return_input_package",
        recording_replay_adapter,
    )
    monkeypatch.setattr(
        module,
        "build_synthetic_research_result",
        recording_result_builder,
    )

    result = module.build_synthetic_research_result_from_return_input_package(package)
    expected_result = build_synthetic_research_result(
        build_synthetic_replay_snapshot_from_return_input_package(package)
    )

    assert calls == [("replay", package), ("result", result.snapshot)]
    assert result == expected_result
    assert _call_names().isdisjoint(_FORBIDDEN_METRIC_CALL_NAMES)


@pytest.mark.parametrize("value", (object(), None, "not a package"))
def test_adapter_rejects_non_package_input(value: object) -> None:
    with pytest.raises(ValidationError, match="ResearchReturnInputPackage"):
        build_synthetic_research_result_from_return_input_package(value)


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


def test_adapter_does_not_mutate_package_source_snapshot_or_result() -> None:
    package = package_fixture()
    before_payload = package.to_dict()
    before_tuple_ids = (
        id(package.snapshot.observation_dates),
        id(package.snapshot.close_values),
        id(package.snapshot.close_to_close_returns),
        id(package.snapshot.non_claims),
    )

    result = build_synthetic_research_result_from_return_input_package(package)
    payload = result.to_dict()
    payload["snapshot"]["returns"].append("9.99")
    payload["summary"]["point_count"] = 99

    assert package.to_dict() == before_payload
    assert (
        id(package.snapshot.observation_dates),
        id(package.snapshot.close_values),
        id(package.snapshot.close_to_close_returns),
        id(package.snapshot.non_claims),
    ) == before_tuple_ids
    assert result.snapshot.returns == package.snapshot.close_to_close_returns
    assert result.summary.point_count == len(package.snapshot.observation_dates)


def test_adapter_output_adds_no_trading_runtime_or_allocation_fields() -> None:
    result = build_synthetic_research_result_from_return_input_package(
        package_fixture()
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


def test_module_imports_no_forbidden_vendor_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_persistence_or_runtime_calls() -> None:
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
