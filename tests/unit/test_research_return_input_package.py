import ast
import re
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_input_fingerprint import (
    research_return_input_snapshot_fingerprint,
)
from algotrader.research.research_return_input_package import (
    ResearchReturnInputPackage,
    build_research_return_input_package,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)


MODULE_PATH = Path("src/algotrader/research/research_return_input_package.py")

_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.research_return_input",
    "algotrader.research.research_return_input_consistency",
    "algotrader.research.research_return_input_fingerprint",
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

_FORBIDDEN_SOURCE_TERMS = (
    "alpaca",
    "alpha vantage",
    "api",
    "api_key",
    "apikey",
    "bearer",
    "benchmark",
    "broker",
    "client_secret",
    "credential",
    "endpoint",
    "fill",
    "order",
    "password",
    "portfolio",
    "position",
    "private_key",
    "refinitiv",
    "request",
    "secret",
    "socket",
    "token",
    "vendor",
    ".data",
)

_FORBIDDEN_SOURCE_MARKERS = (
    "://",
    "http:",
    "https:",
    "www.",
    ".com",
    ".csv",
    ".jsonl",
    ".parquet",
    ".zip",
    "/",
    "\\",
)


def test_phase_121_fixture_builds_valid_package() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    package = build_research_return_input_package(snapshot)

    assert isinstance(package, ResearchReturnInputPackage)
    assert package.snapshot == snapshot
    assert package.fingerprint == research_return_input_snapshot_fingerprint(snapshot)


def test_package_preserves_snapshot_object_identity() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    package = build_research_return_input_package(snapshot)

    assert package.snapshot is snapshot


def test_package_fingerprint_matches_phase_123_pinned_fixture_digest() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    package = build_research_return_input_package(snapshot)

    assert package.fingerprint == _SYNTHETIC_FIXTURE_DIGEST


def test_package_instances_are_frozen() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    package = build_research_return_input_package(snapshot)

    with pytest.raises(FrozenInstanceError):
        package.fingerprint = _SYNTHETIC_FIXTURE_DIGEST


def test_direct_construction_accepts_matching_snapshot_fingerprint_pair() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    fingerprint = research_return_input_snapshot_fingerprint(snapshot)

    package = ResearchReturnInputPackage(
        snapshot=snapshot,
        fingerprint=fingerprint,
    )

    assert package.snapshot is snapshot
    assert package.fingerprint == fingerprint


@pytest.mark.parametrize(
    "fingerprint",
    (
        "",
        "0" * 63,
        "0" * 65,
        "G" + ("0" * 63),
        "A" + ("0" * 63),
        object(),
    ),
)
def test_direct_construction_rejects_malformed_fingerprint(
    fingerprint: object,
) -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    with pytest.raises(ValidationError, match="64-character lowercase"):
        ResearchReturnInputPackage(snapshot=snapshot, fingerprint=fingerprint)


def test_direct_construction_rejects_fingerprint_that_does_not_match_snapshot() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    mismatched_fingerprint = "0" * 64

    with pytest.raises(ValidationError, match="match snapshot"):
        ResearchReturnInputPackage(
            snapshot=snapshot,
            fingerprint=mismatched_fingerprint,
        )


def test_inconsistent_snapshots_are_rejected_before_packaging() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    inconsistent = replace(
        snapshot,
        close_to_close_returns=(Decimal("0.05"), Decimal("-0.049")),
    )

    with pytest.raises(ValidationError, match="close_to_close_returns"):
        build_research_return_input_package(inconsistent)


def test_non_snapshot_input_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ResearchReturnInputSnapshot"):
        build_research_return_input_package(object())

    with pytest.raises(ValidationError, match="ResearchReturnInputSnapshot"):
        ResearchReturnInputPackage(snapshot=object(), fingerprint="0" * 64)


def test_to_dict_is_primitive_only_and_deterministic() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    package = build_research_return_input_package(snapshot)

    first = package.to_dict()
    second = package.to_dict()

    assert first == second
    assert list(first) == ["snapshot", "fingerprint"]
    assert first == {
        "snapshot": snapshot.to_dict(),
        "fingerprint": _SYNTHETIC_FIXTURE_DIGEST,
    }
    assert _is_primitive_payload(first)


def test_packaging_does_not_mutate_snapshot() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    before = snapshot.to_dict()
    tuple_ids = (
        id(snapshot.observation_dates),
        id(snapshot.close_values),
        id(snapshot.close_to_close_returns),
        id(snapshot.non_claims),
    )

    package = build_research_return_input_package(snapshot)
    package.to_dict()

    assert package.snapshot is snapshot
    assert snapshot.to_dict() == before
    assert (
        id(snapshot.observation_dates),
        id(snapshot.close_values),
        id(snapshot.close_to_close_returns),
        id(snapshot.non_claims),
    ) == tuple_ids


def test_module_imports_no_forbidden_vendor_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        name
        for name in imports
        if _matches_forbidden_prefix(name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_forbidden_io_network_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_text_has_no_real_world_or_trading_concepts() -> None:
    source = _source_text()
    upper_source = source.upper()
    lowered = source.lower()

    for ticker in _REAL_TICKERS:
        assert re.search(rf"(?<![A-Z0-9]){ticker}(?![A-Z0-9])", upper_source) is None
    for term in _FORBIDDEN_SOURCE_TERMS:
        assert term not in lowered
    for marker in _FORBIDDEN_SOURCE_MARKERS:
        assert marker not in lowered


def _is_primitive_payload(value: object) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True

    if isinstance(value, list):
        return all(_is_primitive_payload(item) for item in value)

    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_primitive_payload(item)
            for key, item in value.items()
        )

    return False


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


def _matches_forbidden_prefix(module_name: str, forbidden_prefixes: tuple[str, ...]) -> bool:
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
