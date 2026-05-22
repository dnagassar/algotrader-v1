import ast
import hashlib
import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import research_return_input_fingerprint as module
from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.research_return_input_fingerprint import (
    research_return_input_snapshot_fingerprint,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)


MODULE_PATH = Path("src/algotrader/research/research_return_input_fingerprint.py")

_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "hashlib",
    "json",
    "algotrader.research.research_return_input",
    "algotrader.research.research_return_input_consistency",
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


def test_phase_121_fixture_produces_stable_sha256_hex_digest() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    digest = research_return_input_snapshot_fingerprint(snapshot)

    assert digest == _SYNTHETIC_FIXTURE_DIGEST
    assert re.fullmatch(r"[0-9a-f]{64}", digest) is not None


def test_repeated_calls_return_same_digest() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()

    first = research_return_input_snapshot_fingerprint(snapshot)
    second = research_return_input_snapshot_fingerprint(snapshot)

    assert first == second == _SYNTHETIC_FIXTURE_DIGEST


def test_round_tripped_snapshot_produces_same_digest() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    round_tripped = ResearchReturnInputSnapshot.from_dict(snapshot.to_dict())

    assert research_return_input_snapshot_fingerprint(round_tripped) == (
        research_return_input_snapshot_fingerprint(snapshot)
    )


@pytest.mark.parametrize(
    "field_name,index,mutated_value,expected",
    (
        ("observation_dates", 0, "2099-01-02", "digest_changes"),
        ("close_values", 1, "10.6000", "fingerprint_rejects"),
        ("close_to_close_returns", 0, "0.0501", "fingerprint_rejects"),
        ("non_claims", 0, "not altered source approval", "from_dict_rejects"),
    ),
)
def test_mutating_one_primitive_payload_value_changes_digest_or_fails_validation(
    field_name: str,
    index: int,
    mutated_value: str,
    expected: str,
) -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    original_digest = research_return_input_snapshot_fingerprint(snapshot)
    payload = snapshot.to_dict()
    payload[field_name][index] = mutated_value

    if expected == "from_dict_rejects":
        with pytest.raises(ValidationError):
            ResearchReturnInputSnapshot.from_dict(payload)
        return

    mutated_snapshot = ResearchReturnInputSnapshot.from_dict(payload)
    if expected == "fingerprint_rejects":
        with pytest.raises(ValidationError, match="close_to_close_returns"):
            research_return_input_snapshot_fingerprint(mutated_snapshot)
        return

    assert research_return_input_snapshot_fingerprint(mutated_snapshot) != original_digest


def test_different_valid_synthetic_snapshot_content_changes_digest() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    variant = replace(
        snapshot,
        close_values=(Decimal("10.0000"), Decimal("12.0000"), Decimal("9.6000")),
        close_to_close_returns=(Decimal("0.2"), Decimal("-0.2")),
    )

    assert research_return_input_snapshot_fingerprint(variant) != (
        research_return_input_snapshot_fingerprint(snapshot)
    )


def test_inconsistent_snapshot_is_rejected_by_consistency_checker() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    inconsistent = replace(
        snapshot,
        close_to_close_returns=(Decimal("0.05"), Decimal("-0.049")),
    )

    with pytest.raises(ValidationError, match="close_to_close_returns"):
        research_return_input_snapshot_fingerprint(inconsistent)


def test_shape_valid_arithmetic_inconsistent_snapshot_is_rejected_before_hashing() -> None:
    payload = build_synthetic_research_return_input_snapshot().to_dict()
    payload["close_values"][1] = "10.6000"
    inconsistent = ResearchReturnInputSnapshot.from_dict(payload)

    with pytest.raises(ValidationError, match="close_to_close_returns"):
        research_return_input_snapshot_fingerprint(inconsistent)


def test_non_snapshot_input_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ResearchReturnInputSnapshot"):
        research_return_input_snapshot_fingerprint(object())


def test_snapshot_is_not_mutated() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    before = snapshot.to_dict()
    tuple_ids = (
        id(snapshot.observation_dates),
        id(snapshot.close_values),
        id(snapshot.close_to_close_returns),
        id(snapshot.non_claims),
    )

    research_return_input_snapshot_fingerprint(snapshot)

    assert snapshot.to_dict() == before
    assert (
        id(snapshot.observation_dates),
        id(snapshot.close_values),
        id(snapshot.close_to_close_returns),
        id(snapshot.non_claims),
    ) == tuple_ids


def test_deterministic_json_settings_are_pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    calls: list[dict[str, object]] = []
    original_dumps = json.dumps

    def recording_dumps(payload: object, *args: object, **kwargs: object) -> str:
        calls.append(dict(kwargs))
        return original_dumps(payload, *args, **kwargs)

    monkeypatch.setattr(module.json, "dumps", recording_dumps)

    digest = research_return_input_snapshot_fingerprint(snapshot)

    serialized = original_dumps(
        snapshot.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    assert calls == [{"sort_keys": True, "separators": (",", ":")}]
    assert digest == hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    assert digest == _SYNTHETIC_FIXTURE_DIGEST


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
