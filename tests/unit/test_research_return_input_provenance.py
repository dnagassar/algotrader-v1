import ast
import re
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_input_package import (
    ResearchReturnInputPackage,
    build_research_return_input_package,
)
from algotrader.research.research_return_input_provenance import (
    ResearchReturnInputProvenance,
    build_research_return_input_provenance,
    validate_research_return_input_provenance_matches_package,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)


MODULE_PATH = Path("src/algotrader/research/research_return_input_provenance.py")

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.research_return_input_package",
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
    "allocation",
    "benchmark",
    "broker",
    "cash",
    "endpoint",
    "fill",
    "fills",
    "order",
    "orders",
    "portfolio",
    "position",
    "positions",
    "ranking",
    "recommendation",
    "recommendations",
    "score",
    "scoring",
    "strategy",
    "trading",
)


def test_provenance_builds_from_phase_125_package_fixture() -> None:
    package = package_fixture()

    provenance = build_research_return_input_provenance(package)

    assert isinstance(provenance, ResearchReturnInputProvenance)
    assert provenance.snapshot_id == package.snapshot.snapshot_id
    assert provenance.fingerprint == package.fingerprint
    assert provenance.manifest_fixture_id == package.snapshot.snapshot_id
    assert provenance.manifest_checksum == f"sha256:{package.fingerprint}"


def test_provenance_is_frozen() -> None:
    provenance = build_research_return_input_provenance(package_fixture())

    with pytest.raises(FrozenInstanceError):
        provenance.snapshot_id = "changed"


def test_direct_construction_accepts_valid_payload() -> None:
    package = package_fixture()

    provenance = ResearchReturnInputProvenance(
        snapshot_id=package.snapshot.snapshot_id,
        fingerprint=package.fingerprint,
        manifest_fixture_id=package.snapshot.snapshot_id,
        manifest_checksum=f"sha256:{package.fingerprint}",
    )

    assert provenance.snapshot_id == package.snapshot.snapshot_id
    assert provenance.fingerprint == package.fingerprint
    assert provenance.manifest_fixture_id == provenance.snapshot_id
    assert provenance.manifest_checksum == f"sha256:{provenance.fingerprint}"


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("snapshot_id", ""),
        ("snapshot_id", " synthetic_return_input_snapshot_fixture_001"),
        ("snapshot_id", object()),
        ("manifest_fixture_id", ""),
        ("manifest_fixture_id", "synthetic_return_input_snapshot_fixture_001 "),
        ("manifest_fixture_id", object()),
        ("manifest_checksum", ""),
        ("manifest_checksum", " sha256:1111111111111111111111111111111111111111111111111111111111111111"),
        ("manifest_checksum", object()),
    ),
)
def test_direct_construction_rejects_non_exact_string_fields(
    field_name: str,
    value: object,
) -> None:
    payload = {
        "snapshot_id": "synthetic_return_input_snapshot_fixture_001",
        "fingerprint": "1" * 64,
        "manifest_fixture_id": "synthetic_return_input_snapshot_fixture_001",
        "manifest_checksum": f"sha256:{'1' * 64}",
    }
    payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        ResearchReturnInputProvenance(**payload)


@pytest.mark.parametrize(
    "fingerprint",
    (
        "",
        "0" * 63,
        "0" * 65,
        "A" * 64,
        "g" * 64,
        object(),
    ),
)
def test_direct_construction_rejects_malformed_fingerprint_values(
    fingerprint: object,
) -> None:
    with pytest.raises(ValidationError, match="fingerprint"):
        ResearchReturnInputProvenance(
            snapshot_id="synthetic_return_input_snapshot_fixture_001",
            fingerprint=fingerprint,
            manifest_fixture_id="synthetic_return_input_snapshot_fixture_001",
            manifest_checksum=f"sha256:{fingerprint}",
        )


def test_direct_construction_rejects_mismatched_manifest_fixture_id() -> None:
    fingerprint = "1" * 64

    with pytest.raises(ValidationError, match="manifest_fixture_id"):
        ResearchReturnInputProvenance(
            snapshot_id="synthetic_return_input_snapshot_fixture_001",
            fingerprint=fingerprint,
            manifest_fixture_id="synthetic_return_input_snapshot_fixture_002",
            manifest_checksum=f"sha256:{fingerprint}",
        )


def test_direct_construction_rejects_mismatched_manifest_checksum() -> None:
    with pytest.raises(ValidationError, match="manifest_checksum"):
        ResearchReturnInputProvenance(
            snapshot_id="synthetic_return_input_snapshot_fixture_001",
            fingerprint="1" * 64,
            manifest_fixture_id="synthetic_return_input_snapshot_fixture_001",
            manifest_checksum=f"sha256:{'2' * 64}",
        )


def test_verifier_returns_same_provenance_object_on_success() -> None:
    package = package_fixture()
    provenance = build_research_return_input_provenance(package)

    verified = validate_research_return_input_provenance_matches_package(
        package,
        provenance,
    )

    assert verified is provenance


def test_verifier_rejects_mismatched_package_snapshot_id() -> None:
    package = package_fixture()
    provenance = ResearchReturnInputProvenance(
        snapshot_id="synthetic_return_input_snapshot_fixture_002",
        fingerprint=package.fingerprint,
        manifest_fixture_id="synthetic_return_input_snapshot_fixture_002",
        manifest_checksum=f"sha256:{package.fingerprint}",
    )

    with pytest.raises(ValidationError, match="snapshot_id"):
        validate_research_return_input_provenance_matches_package(
            package,
            provenance,
        )


def test_verifier_rejects_mismatched_package_fingerprint() -> None:
    package = package_fixture()
    fingerprint = "1" * 64
    provenance = ResearchReturnInputProvenance(
        snapshot_id=package.snapshot.snapshot_id,
        fingerprint=fingerprint,
        manifest_fixture_id=package.snapshot.snapshot_id,
        manifest_checksum=f"sha256:{fingerprint}",
    )

    with pytest.raises(ValidationError, match="fingerprint"):
        validate_research_return_input_provenance_matches_package(
            package,
            provenance,
        )


@pytest.mark.parametrize("value", (object(), None, "not a package"))
def test_builder_rejects_non_package_input(value: object) -> None:
    with pytest.raises(ValidationError, match="ResearchReturnInputPackage"):
        build_research_return_input_provenance(value)


@pytest.mark.parametrize("value", (object(), None, "not provenance"))
def test_verifier_rejects_non_provenance_input(value: object) -> None:
    with pytest.raises(ValidationError, match="ResearchReturnInputProvenance"):
        validate_research_return_input_provenance_matches_package(
            package_fixture(),
            value,
        )


def test_provenance_verification_does_not_mutate_package_or_provenance() -> None:
    package = package_fixture()
    provenance = build_research_return_input_provenance(package)
    package_payload = package.to_dict()
    provenance_fields = (
        provenance.snapshot_id,
        provenance.fingerprint,
        provenance.manifest_fixture_id,
        provenance.manifest_checksum,
    )

    verified = validate_research_return_input_provenance_matches_package(
        package,
        provenance,
    )

    assert verified is provenance
    assert package.to_dict() == package_payload
    assert (
        provenance.snapshot_id,
        provenance.fingerprint,
        provenance.manifest_fixture_id,
        provenance.manifest_checksum,
    ) == provenance_fields


def test_package_payload_shape_is_unchanged_by_provenance_building() -> None:
    package = package_fixture()
    payload_before = package.to_dict()

    build_research_return_input_provenance(package)

    assert package.to_dict() == payload_before
    assert tuple(payload_before) == ("snapshot", "fingerprint")
    assert not hasattr(ResearchReturnInputProvenance, "from_dict")
    assert not hasattr(build_research_return_input_provenance(package), "to_dict")


def test_module_imports_no_forbidden_vendor_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_persistence_or_runtime_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_text_has_no_real_world_runtime_or_trading_literals() -> None:
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
