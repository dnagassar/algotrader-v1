import ast
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.replay_result import SyntheticResearchResult
from algotrader.research.research_return_input_package import (
    build_research_return_input_package,
)
from tests.fixtures import research_return_input_result as fixture_module
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)
from tests.fixtures.research_return_input_result import (
    build_synthetic_return_input_research_result,
    expected_synthetic_return_input_research_result_dict,
)


FIXTURE_PATH = Path("tests/fixtures/research_return_input_result.py")

_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.replay_result",
    "algotrader.research.research_return_input_package",
    "algotrader.research.research_return_input_result_adapter",
    "tests.fixtures.research_return_input",
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
    "benchmarks",
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
)


def test_fixture_builds_synthetic_research_result() -> None:
    result = build_synthetic_return_input_research_result()

    assert isinstance(result, SyntheticResearchResult)
    assert result.snapshot.manifest.fixture_id == (
        "synthetic_return_input_snapshot_fixture_001"
    )


def test_fixture_builds_through_snapshot_package_and_result_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    real_snapshot_builder = (
        fixture_module.build_synthetic_research_return_input_snapshot
    )
    real_package_builder = fixture_module.build_research_return_input_package
    real_result_adapter = (
        fixture_module.build_synthetic_research_result_from_return_input_package
    )

    def recording_snapshot_builder() -> object:
        snapshot = real_snapshot_builder()
        calls.append(("snapshot", snapshot))
        return snapshot

    def recording_package_builder(snapshot: object) -> object:
        package = real_package_builder(snapshot)
        calls.append(("package", package))
        return package

    def recording_result_adapter(package: object) -> SyntheticResearchResult:
        result = real_result_adapter(package)
        calls.append(("result", result))
        return result

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_return_input_snapshot",
        recording_snapshot_builder,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_research_return_input_package",
        recording_package_builder,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_result_from_return_input_package",
        recording_result_adapter,
    )

    result = fixture_module.build_synthetic_return_input_research_result()
    snapshot_arg = calls[0][1]
    package_arg = calls[1][1]

    assert [name for name, _ in calls] == ["snapshot", "package", "result"]
    assert package_arg.snapshot is snapshot_arg
    assert calls[2][1] is result
    assert result.snapshot.manifest.fixture_id == snapshot_arg.snapshot_id


def test_phase_123_fingerprint_is_preserved_as_manifest_checksum() -> None:
    package = package_fixture()

    result = build_synthetic_return_input_research_result()

    assert package.fingerprint == _SYNTHETIC_FIXTURE_DIGEST
    assert result.snapshot.manifest.checksum == f"sha256:{_SYNTHETIC_FIXTURE_DIGEST}"


def test_snapshot_id_is_preserved_as_manifest_fixture_id() -> None:
    package = package_fixture()

    result = build_synthetic_return_input_research_result()

    assert result.snapshot.manifest.fixture_id == package.snapshot.snapshot_id


def test_observation_order_is_preserved() -> None:
    package = package_fixture()

    result = build_synthetic_return_input_research_result()

    assert tuple(
        point.observation.observation_date
        for point in result.snapshot.available_points
    ) == package.snapshot.observation_dates
    assert result.snapshot.to_dict()["available_points"] == [
        {
            "observation_date": "2099-01-03",
            "available_after": "2099-01-03",
            "value": "10.0000",
        },
        {
            "observation_date": "2099-01-04",
            "available_after": "2099-01-04",
            "value": "10.5000",
        },
        {
            "observation_date": "2099-01-07",
            "available_after": "2099-01-07",
            "value": "9.9750",
        },
    ]


def test_stored_close_to_close_returns_are_preserved_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    real_result_adapter = (
        fixture_module.build_synthetic_research_result_from_return_input_package
    )

    def recording_result_adapter(package: object) -> SyntheticResearchResult:
        captured["package"] = package
        return real_result_adapter(package)

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_result_from_return_input_package",
        recording_result_adapter,
    )

    result = fixture_module.build_synthetic_return_input_research_result()
    package = captured["package"]

    assert result.snapshot.returns is package.snapshot.close_to_close_returns
    assert result.snapshot.returns == (Decimal("0.05"), Decimal("-0.05"))
    assert result.snapshot.to_dict()["returns"] == ["0.05", "-0.05"]


def test_expected_primitive_output_matches_stable_result_serialization() -> None:
    result = build_synthetic_return_input_research_result()
    expected = expected_synthetic_return_input_research_result_dict()

    assert result.to_dict() == expected
    assert tuple(expected) == ("snapshot", "summary")
    assert expected["snapshot"] == result.snapshot.to_dict()
    assert expected["summary"] == result.summary.to_dict()
    assert expected is not result.to_dict()
    _assert_primitive_only(expected)


def test_repeated_fixture_calls_are_deterministic() -> None:
    first = build_synthetic_return_input_research_result()
    second = build_synthetic_return_input_research_result()
    first_expected = expected_synthetic_return_input_research_result_dict()
    second_expected = expected_synthetic_return_input_research_result_dict()

    assert first is not second
    assert first.to_dict() == second.to_dict()
    assert first_expected == second_expected == first.to_dict()
    assert _sorted_compact_json(first.to_dict()) == _sorted_compact_json(
        second.to_dict()
    )


def test_fixture_helpers_do_not_mutate_source_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_snapshot = build_synthetic_research_return_input_snapshot()
    source_package = build_research_return_input_package(source_snapshot)
    snapshot_before = source_snapshot.to_dict()
    package_before = source_package.to_dict()
    tuple_ids = (
        id(source_snapshot.observation_dates),
        id(source_snapshot.close_values),
        id(source_snapshot.close_to_close_returns),
        id(source_snapshot.non_claims),
    )

    def snapshot_builder() -> object:
        return source_snapshot

    def package_builder(snapshot: object) -> object:
        assert snapshot is source_snapshot
        return source_package

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_return_input_snapshot",
        snapshot_builder,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_research_return_input_package",
        package_builder,
    )

    result = fixture_module.build_synthetic_return_input_research_result()
    result_before = result.to_dict()
    payload = result.to_dict()
    payload["snapshot"]["available_points"].append(
        {
            "observation_date": "2099-01-08",
            "available_after": "2099-01-08",
            "value": "99.99",
        }
    )
    payload["snapshot"]["returns"].append("9.99")
    payload["summary"]["point_count"] = 99
    expected_payload = (
        fixture_module.expected_synthetic_return_input_research_result_dict()
    )

    assert source_snapshot.to_dict() == snapshot_before
    assert source_package.to_dict() == package_before
    assert (
        id(source_snapshot.observation_dates),
        id(source_snapshot.close_values),
        id(source_snapshot.close_to_close_returns),
        id(source_snapshot.non_claims),
    ) == tuple_ids
    assert result.to_dict() == result_before
    assert expected_payload == result_before


def test_result_payload_adds_no_runtime_trading_or_allocation_fields() -> None:
    result = build_synthetic_return_input_research_result()
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


def test_fixture_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_module_text_has_no_real_world_or_trading_path_concepts() -> None:
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


def package_fixture() -> object:
    return build_research_return_input_package(
        build_synthetic_research_return_input_snapshot()
    )


def _sorted_compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _assert_primitive_only(value: object) -> None:
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
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(FIXTURE_PATH))


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
