import ast
import json
import re
from pathlib import Path

import pytest

from algotrader.research.candidate_result_dossier import (
    CandidateResearchResultDossier,
)
from algotrader.research.replay_result import SyntheticResearchResult
from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.research_return_input_package import (
    ResearchReturnInputPackage,
    build_research_return_input_package,
)
from algotrader.research.research_return_input_result_adapter import (
    build_synthetic_research_result_from_return_input_package,
)
from tests.fixtures import candidate_result_dossier as fixture_module
from tests.fixtures.candidate_result_dossier import (
    build_synthetic_candidate_research_result_dossier,
    expected_synthetic_candidate_research_result_dossier_dict,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)


FIXTURE_PATH = Path("tests/fixtures/candidate_result_dossier.py")

_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.candidate_result_dossier",
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
    "allocation",
    "allocations",
    "approval",
    "approved",
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
    "trading_readiness",
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
    "runtime",
    "runtimes",
    "signal",
    "signals",
    "strategy",
    "trading",
    "trade",
    "trades",
)


def test_fixture_builds_candidate_research_result_dossier() -> None:
    dossier = build_synthetic_candidate_research_result_dossier()

    assert isinstance(dossier, CandidateResearchResultDossier)
    assert dossier.status == "candidate_only"


def test_fixture_builds_through_snapshot_package_result_and_dossier_chain(
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
    real_dossier_builder = fixture_module.build_candidate_research_result_dossier

    def recording_snapshot_builder() -> ResearchReturnInputSnapshot:
        snapshot = real_snapshot_builder()
        calls.append(("snapshot", snapshot))
        return snapshot

    def recording_package_builder(
        snapshot: ResearchReturnInputSnapshot,
    ) -> ResearchReturnInputPackage:
        package = real_package_builder(snapshot)
        calls.append(("package", package))
        return package

    def recording_result_adapter(
        package: ResearchReturnInputPackage,
    ) -> SyntheticResearchResult:
        result = real_result_adapter(package)
        calls.append(("result", result))
        return result

    def recording_dossier_builder(
        package: ResearchReturnInputPackage,
        result: SyntheticResearchResult,
    ) -> CandidateResearchResultDossier:
        dossier = real_dossier_builder(package, result)
        calls.append(("dossier", dossier))
        return dossier

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
    monkeypatch.setattr(
        fixture_module,
        "build_candidate_research_result_dossier",
        recording_dossier_builder,
    )

    dossier = fixture_module.build_synthetic_candidate_research_result_dossier()
    snapshot_arg = calls[0][1]
    package_arg = calls[1][1]
    result_arg = calls[2][1]

    assert [name for name, _ in calls] == [
        "snapshot",
        "package",
        "result",
        "dossier",
    ]
    assert package_arg.snapshot is snapshot_arg
    assert result_arg.snapshot.manifest.fixture_id == snapshot_arg.snapshot_id
    assert dossier is calls[3][1]
    assert dossier.package is package_arg
    assert dossier.result is result_arg


def test_fixture_preserves_package_and_result_identity() -> None:
    dossier = build_synthetic_candidate_research_result_dossier()

    assert isinstance(dossier.package, ResearchReturnInputPackage)
    assert isinstance(dossier.result, SyntheticResearchResult)
    assert dossier.package.snapshot is not None
    assert dossier.result.snapshot is not None
    assert dossier.to_dict()["package_fingerprint"] == dossier.package.fingerprint


def test_limitations_and_non_claims_are_present_and_deterministic() -> None:
    first = build_synthetic_candidate_research_result_dossier()
    second = build_synthetic_candidate_research_result_dossier()

    assert isinstance(first.limitations, tuple)
    assert isinstance(first.non_claims, tuple)
    assert first.limitations
    assert first.non_claims
    assert first.limitations == second.limitations
    assert first.non_claims == second.non_claims
    assert first.to_dict()["limitations"] == list(first.limitations)
    assert first.to_dict()["non_claims"] == list(first.non_claims)
    assert all(_is_clean_string(value) for value in first.limitations)
    assert all(_is_clean_string(value) for value in first.non_claims)
    assert all(value.startswith("not ") for value in first.non_claims)


def test_phase_123_fingerprint_is_preserved_in_dossier_dict() -> None:
    dossier = build_synthetic_candidate_research_result_dossier()
    payload = dossier.to_dict()

    assert dossier.package.fingerprint == _SYNTHETIC_FIXTURE_DIGEST
    assert payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST


def test_phase_127_provenance_convention_is_preserved_in_dossier_dict() -> None:
    dossier = build_synthetic_candidate_research_result_dossier()
    payload = dossier.to_dict()

    assert payload["package_snapshot_id"] == dossier.package.snapshot.snapshot_id
    assert payload["result_snapshot_manifest_fixture_id"] == (
        dossier.package.snapshot.snapshot_id
    )
    assert payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{dossier.package.fingerprint}"
    )


def test_expected_output_matches_dossier_serialization_exactly() -> None:
    dossier = build_synthetic_candidate_research_result_dossier()
    expected = expected_synthetic_candidate_research_result_dossier_dict()

    assert expected == dossier.to_dict()
    assert tuple(expected) == (
        "package_fingerprint",
        "package_snapshot_id",
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
        "status",
        "limitations",
        "non_claims",
    )
    assert expected is not dossier.to_dict()
    _assert_primitive_only(expected)


def test_repeated_fixture_calls_are_deterministic() -> None:
    first = build_synthetic_candidate_research_result_dossier()
    second = build_synthetic_candidate_research_result_dossier()
    first_expected = expected_synthetic_candidate_research_result_dossier_dict()
    second_expected = expected_synthetic_candidate_research_result_dossier_dict()

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
    source_result = build_synthetic_research_result_from_return_input_package(
        source_package
    )
    snapshot_before = source_snapshot.to_dict()
    package_before = source_package.to_dict()
    result_before = source_result.to_dict()
    tuple_ids = (
        id(source_snapshot.observation_dates),
        id(source_snapshot.close_values),
        id(source_snapshot.close_to_close_returns),
        id(source_snapshot.non_claims),
        id(source_result.snapshot.available_points),
        id(source_result.snapshot.returns),
        id(source_result.summary),
    )

    def snapshot_builder() -> ResearchReturnInputSnapshot:
        return source_snapshot

    def package_builder(
        snapshot: ResearchReturnInputSnapshot,
    ) -> ResearchReturnInputPackage:
        assert snapshot is source_snapshot
        return source_package

    def result_adapter(
        package: ResearchReturnInputPackage,
    ) -> SyntheticResearchResult:
        assert package is source_package
        return source_result

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
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_result_from_return_input_package",
        result_adapter,
    )

    dossier = fixture_module.build_synthetic_candidate_research_result_dossier()
    dossier_before = dossier.to_dict()
    payload = fixture_module.expected_synthetic_candidate_research_result_dossier_dict()
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("mutated primitive copy")

    assert source_snapshot.to_dict() == snapshot_before
    assert source_package.to_dict() == package_before
    assert source_result.to_dict() == result_before
    assert (
        id(source_snapshot.observation_dates),
        id(source_snapshot.close_values),
        id(source_snapshot.close_to_close_returns),
        id(source_snapshot.non_claims),
        id(source_result.snapshot.available_points),
        id(source_result.snapshot.returns),
        id(source_result.summary),
    ) == tuple_ids
    assert dossier.to_dict() == dossier_before


def test_dossier_fixture_adds_no_disallowed_payload_or_object_fields() -> None:
    dossier = build_synthetic_candidate_research_result_dossier()
    payload = dossier.to_dict()

    assert tuple(payload) == (
        "package_fingerprint",
        "package_snapshot_id",
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
        "status",
        "limitations",
        "non_claims",
    )
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_PAYLOAD_FIELDS)
    assert all(
        not hasattr(dossier, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )
    assert all(
        not hasattr(dossier.package, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )
    assert all(
        not hasattr(dossier.result, field_name)
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


def test_fixture_module_text_has_no_real_world_path_secret_or_trading_literals() -> None:
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


def _is_clean_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _sorted_compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _assert_primitive_only(value: object) -> None:
    assert not isinstance(value, (tuple, set))
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
