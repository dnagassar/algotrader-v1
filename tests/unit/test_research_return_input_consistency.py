import ast
import re
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.research_return_input_consistency import (
    validate_research_return_input_snapshot_consistency,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)


MODULE_PATH = Path("src/algotrader/research/research_return_input_consistency.py")

_NON_CLAIMS = (
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
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.errors",
    "algotrader.research.research_return_input",
    "algotrader.research.return_construction",
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


def test_phase_121_fixture_passes_consistency_validation() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    assert validate_research_return_input_snapshot_consistency(snapshot) == snapshot


def test_returns_same_snapshot_object_on_success() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    result = validate_research_return_input_snapshot_consistency(snapshot)

    assert result is snapshot


def test_mismatched_stored_returns_are_rejected() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    mismatched = replace(
        snapshot,
        close_to_close_returns=(Decimal("0.05"), Decimal("-0.049999999999999999")),
    )

    with pytest.raises(ValidationError, match="close_to_close_returns"):
        validate_research_return_input_snapshot_consistency(mismatched)


def test_reversed_return_values_are_rejected_by_consistency_function() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    reversed_returns = replace(
        snapshot,
        close_to_close_returns=tuple(reversed(snapshot.close_to_close_returns)),
    )

    with pytest.raises(ValidationError, match="close_to_close_returns"):
        validate_research_return_input_snapshot_consistency(reversed_returns)


@pytest.mark.parametrize(
    "returns",
    (
        (Decimal("0.05"),),
        (Decimal("0.05"), Decimal("-0.05"), Decimal("0")),
        (Decimal("0.05"), "not-decimal"),
    ),
)
def test_missing_extra_or_malformed_return_values_are_rejected_by_snapshot_contract(
    returns: tuple[object, ...],
) -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    with pytest.raises(ValidationError):
        replace(snapshot, close_to_close_returns=returns)


def test_non_snapshot_input_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ResearchReturnInputSnapshot"):
        validate_research_return_input_snapshot_consistency(object())


def test_no_rounding_or_tolerance_behavior_is_introduced() -> None:
    exact = _snapshot(
        close_values=(Decimal("100.0000"), Decimal("100.0050")),
        close_to_close_returns=(Decimal("0.00005"),),
    )
    rounded = replace(exact, close_to_close_returns=(Decimal("0.0001"),))

    assert validate_research_return_input_snapshot_consistency(exact) is exact
    with pytest.raises(ValidationError, match="close_to_close_returns"):
        validate_research_return_input_snapshot_consistency(rounded)


def test_non_positive_prior_close_value_is_rejected_by_return_mechanics() -> None:
    snapshot = _snapshot(
        close_values=(Decimal("0"), Decimal("1")),
        close_to_close_returns=(Decimal("0"),),
    )

    with pytest.raises(ValidationError, match="previous_value"):
        validate_research_return_input_snapshot_consistency(snapshot)


def test_no_mutation_occurs() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    before = snapshot.to_dict()
    tuple_ids = (
        id(snapshot.observation_dates),
        id(snapshot.close_values),
        id(snapshot.close_to_close_returns),
        id(snapshot.non_claims),
    )

    validate_research_return_input_snapshot_consistency(snapshot)

    assert snapshot.to_dict() == before
    assert (
        id(snapshot.observation_dates),
        id(snapshot.close_values),
        id(snapshot.close_to_close_returns),
        id(snapshot.non_claims),
    ) == tuple_ids


def test_module_imports_no_forbidden_vendor_data_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_forbidden_io_network_vendor_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_references_no_forbidden_io_network_runtime_or_trading_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_function_source_has_no_real_world_or_trading_concepts() -> None:
    source = _source_text()
    upper_source = source.upper()
    lowered = source.lower()

    for ticker in _REAL_TICKERS:
        assert re.search(rf"(?<![A-Z0-9]){ticker}(?![A-Z0-9])", upper_source) is None
    for term in _FORBIDDEN_SOURCE_TERMS:
        assert term not in lowered
    for marker in _FORBIDDEN_SOURCE_MARKERS:
        assert marker not in lowered


def _snapshot(
    *,
    close_values: tuple[Decimal, ...],
    close_to_close_returns: tuple[Decimal, ...],
) -> ResearchReturnInputSnapshot:
    return ResearchReturnInputSnapshot(
        snapshot_id="synthetic_return_input_consistency_001",
        symbol="SYNRET122X",
        observation_dates=tuple(
            date(2099, 2, day) for day in range(1, len(close_values) + 1)
        ),
        close_values=close_values,
        close_to_close_returns=close_to_close_returns,
        return_basis="synthetic_prepared_close_to_close_simple_return_input",
        adjustment_policy="synthetic_prepared_values_no_external_adjustments",
        synthetic_only=True,
        candidate_only=True,
        non_claims=_NON_CLAIMS,
    )


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


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
