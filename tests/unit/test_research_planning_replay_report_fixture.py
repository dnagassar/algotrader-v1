import ast
from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import re
from types import ModuleType

import pytest

from tests.fixtures.research_planning import (
    build_synthetic_broad_etf_research_planning_package,
)
from tests.fixtures.research_planning_replay import (
    build_synthetic_broad_etf_planning_replay_fixture,
    build_synthetic_broad_etf_planning_replay_package,
)
from tests.fixtures.research_planning_replay_report import (
    build_synthetic_broad_etf_planning_replay_report,
)


MODULE_PATH = Path("tests/fixtures/research_planning_replay_report.py")

_ALLOWED_APPROVAL_STATES = {"candidate_only", "blocked", "deferred"}

_TRUE_LABELS = (
    "synthetic_only",
    "advisory_only",
    "evidence_refs_metadata_only",
)

_FALSE_LABELS = (
    "validates_strategy",
    "approves_source",
    "approves_universe",
    "approves_benchmark",
    "approves_cash_proxy",
    "approves_methodology",
    "approves_parameters",
    "approves_evidence",
    "trading_ready",
)

_REQUIRED_NON_CLAIMS = {
    "synthetic report output only",
    "not a strategy validation artifact",
    "not a validated research artifact",
    "not a validated signal definition",
    "not a signal evaluator",
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not evidence approval",
    "not trading-ready",
    "not broker/runtime-facing",
    "not candidate discovery",
    "not ranking, scoring, or recommendation",
    "does not create orders, positions, portfolio state, broker calls, or runtime behavior",
    "no real data ingestion",
    "no market-data, network, LLM, credential, paper, or live behavior",
}

_FORBIDDEN_NEW_REPLAY_METRIC_KEYS = {
    "alpha",
    "benchmark_relative_return",
    "beta",
    "cagr",
    "drawdown",
    "information_ratio",
    "max_drawdown",
    "sharpe",
}

_FORBIDDEN_BEHAVIOR_FIELD_NAMES = {
    "allocation",
    "broker",
    "broker_call",
    "broker_calls",
    "capital_allocation",
    "candidate_discovery",
    "execution_intent",
    "order",
    "order_intent",
    "paper_eligible",
    "portfolio",
    "position_sizing",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "score",
    "scoring",
    "signal",
    "signal_definition",
    "signal_evaluator",
    "target_weight",
    "tradable",
    "trading_action",
}

_FORBIDDEN_INTERPRETATION_TERMS = (
    "approved",
    "validated",
    "tradable",
    "live",
    "paper_eligible",
    "order",
    "broker",
    "portfolio",
    "recommendation",
)

_FORBIDDEN_REPLAY_OR_TRADING_TERMS = (
    "sharpe",
    "cagr",
    "alpha",
    "beta",
    "information ratio",
    "benchmark-relative return",
    "benchmark relative return",
    "ranking",
    "scoring",
    "recommendation",
    "position sizing",
    "capital allocation",
    "order intent",
    "execution intent",
    "trading action",
    "signal",
    "evaluator",
)

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
    "fred",
    "iex",
    "intrinio",
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


def test_report_consumes_phase_78_fixture_and_summarizes_shape_metadata() -> None:
    replay_fixture = build_synthetic_broad_etf_planning_replay_fixture()
    report = build_synthetic_broad_etf_planning_replay_report(replay_fixture)
    consumed = replay_fixture["consumed_planning_metadata"]
    replay_package = replay_fixture["replay_package"]
    replay_metadata = report["replay_package_metadata"]

    assert report["planning_replay_report_id"] == (
        "synthetic_broad_etf_planning_replay_report_candidate"
    )
    assert report["source_planning_replay_fixture_id"] == (
        replay_fixture["planning_replay_fixture_id"]
    )
    assert report["research_scope_id"] == consumed["research_scope_id"]
    assert report["methodology_scope_id"] == consumed["methodology_scope_id"]
    assert report["linked_scope_ids"] == consumed["linked_scope_ids"]
    assert report["evidence_refs"] == consumed["evidence_refs"]
    assert report["evidence_refs_metadata_only"] is True
    assert "not evidence approval" in report["methodology_non_claims"]
    assert report["selected_moving_average_window"] == 200
    assert report["selected_moving_average_window"] == (
        consumed["moving_average_window"]
    )
    assert replay_metadata["replay_id"] == replay_package["replay_id"]
    assert replay_metadata["as_of_date"] == replay_package["as_of_date"]
    assert replay_metadata["window"] == replay_package["window"]
    assert replay_metadata["top_level_keys"] == list(replay_package)
    assert replay_metadata["summary_keys"] == list(replay_package["summary"])
    assert replay_metadata["row_counts"] == {
        "inputs": len(replay_package["inputs"]),
        "moving_average_observations": len(
            replay_package["moving_average_observations"]
        ),
        "exposure_states": len(replay_package["exposure_states"]),
        "exposure_returns": len(replay_package["exposure_returns"]),
        "cumulative_path": len(replay_package["cumulative_path"]),
    }


def test_report_output_is_deterministic_json_primitive_and_byte_stable() -> None:
    first = build_synthetic_broad_etf_planning_replay_report()
    second = build_synthetic_broad_etf_planning_replay_report()
    first_json = json.dumps(first, separators=(",", ":"))
    second_json = json.dumps(second, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(first_json), separators=(",", ":"))

    assert first == second
    assert first_json == second_json
    assert round_tripped == first_json
    _assert_json_payload_safe(first)
    assert " at 0x" not in first_json
    assert "Decimal(" not in first_json
    assert "datetime." not in first_json
    assert "MovingAverage" not in first_json


def test_report_does_not_mutate_planning_fixture_or_replay_package_objects() -> None:
    planning_package = build_synthetic_broad_etf_research_planning_package()
    planning_before_json = json.dumps(planning_package, separators=(",", ":"))
    replay_package = build_synthetic_broad_etf_planning_replay_package(
        planning_package
    )
    replay_before_payload = replay_package.to_dict()
    replay_fixture = build_synthetic_broad_etf_planning_replay_fixture(
        planning_package=planning_package,
        replay_package=replay_package,
    )
    fixture_before_json = json.dumps(replay_fixture, separators=(",", ":"))

    report = build_synthetic_broad_etf_planning_replay_report(replay_fixture)

    assert json.dumps(planning_package, separators=(",", ":")) == planning_before_json
    assert replay_package.to_dict() == replay_before_payload
    assert json.dumps(replay_fixture, separators=(",", ":")) == fixture_before_json
    assert report["linked_scope_ids"] == (
        replay_fixture["consumed_planning_metadata"]["linked_scope_ids"]
    )
    assert report["evidence_refs"] == (
        replay_fixture["consumed_planning_metadata"]["evidence_refs"]
    )
    assert report["replay_package_metadata"]["row_counts"]["inputs"] == len(
        replay_before_payload["inputs"]
    )


def test_report_keeps_planning_approval_states_candidate_blocked_or_deferred() -> None:
    report = build_synthetic_broad_etf_planning_replay_report()
    approval_states = tuple(report["planning_approval_states"])

    assert approval_states
    assert set(approval_states) <= _ALLOWED_APPROVAL_STATES
    assert "approved" not in approval_states


def test_report_rejects_planning_approval_states_outside_the_allowed_set() -> None:
    replay_fixture = json.loads(
        json.dumps(
            build_synthetic_broad_etf_planning_replay_fixture(),
            separators=(",", ":"),
        )
    )
    replay_fixture["planning_package"]["research_scope"]["approval_state"] = (
        "approved"
    )

    with pytest.raises(ValueError, match="non-approved"):
        build_synthetic_broad_etf_planning_replay_report(replay_fixture)


def test_report_preserves_linked_scope_ids_and_evidence_refs_as_metadata_only() -> None:
    replay_fixture = build_synthetic_broad_etf_planning_replay_fixture()
    report = build_synthetic_broad_etf_planning_replay_report(replay_fixture)
    consumed = replay_fixture["consumed_planning_metadata"]
    compact_json = json.dumps(report, separators=(",", ":")).lower()
    scrubbed_json = _scrub_negative_assertions(compact_json, report)

    assert report["linked_scope_ids"] == consumed["linked_scope_ids"]
    assert report["research_scope_id"] in report["linked_scope_ids"]
    assert report["evidence_refs"] == consumed["evidence_refs"]
    assert report["evidence_refs_metadata_only"] is True
    assert "not evidence approval" in report["methodology_non_claims"]
    assert "not evidence approval" in report["non_claims"]
    assert "evidence approval" not in scrubbed_json
    assert "validated evidence" not in scrubbed_json
    assert "approved evidence" not in scrubbed_json


def test_report_false_interpretation_guardrails_are_explicitly_negative() -> None:
    report = build_synthetic_broad_etf_planning_replay_report()
    non_claims = set(report["non_claims"])
    compact_json = json.dumps(report, separators=(",", ":")).lower()
    scrubbed_json = _scrub_negative_assertions(compact_json, report)

    for label in _TRUE_LABELS:
        assert report[label] is True
    for label in _FALSE_LABELS:
        assert report[label] is False

    assert non_claims >= _REQUIRED_NON_CLAIMS
    for phrase in (
        "not a strategy validation artifact",
        "not a validated research artifact",
        "not a validated signal definition",
        "not a signal evaluator",
        "not source approval",
        "not universe approval",
        "not benchmark approval",
        "not cash proxy approval",
        "not methodology approval",
        "not parameter approval",
        "not evidence approval",
        "not trading-ready",
        "not broker/runtime-facing",
    ):
        assert phrase in non_claims

    for term in _FORBIDDEN_INTERPRETATION_TERMS:
        assert term not in scrubbed_json


def test_report_does_not_add_replay_metrics_or_trading_behavior_fields() -> None:
    report = build_synthetic_broad_etf_planning_replay_report()
    keys = _all_serialized_keys(report)
    compact_json = json.dumps(report, separators=(",", ":")).lower()
    scrubbed_json = _scrub_negative_assertions(compact_json, report)

    assert keys.isdisjoint(_FORBIDDEN_NEW_REPLAY_METRIC_KEYS)
    assert keys.isdisjoint(_FORBIDDEN_BEHAVIOR_FIELD_NAMES)
    assert "benchmark_relative_return" not in keys
    assert "signal_definition" not in keys
    assert "signal_evaluator" not in keys
    assert "trading_action" not in keys

    for term in _FORBIDDEN_REPLAY_OR_TRADING_TERMS:
        assert term not in scrubbed_json


def test_report_introduces_no_real_data_tickers_vendors_paths_or_credentials() -> None:
    report = build_synthetic_broad_etf_planning_replay_report()
    compact_json = json.dumps(report, separators=(",", ":"))
    lowered_json = compact_json.lower()
    scrubbed_json = _scrub_negative_assertions(lowered_json, report)

    assert "$" not in compact_json
    assert "://" not in compact_json
    assert "\\.data" not in lowered_json
    assert "/.data" not in lowered_json
    assert "market_data" not in lowered_json

    for forbidden_term in (
        ".data",
        "account_id",
        "api_key",
        "credential",
        "http://",
        "https://",
        "market data",
        "password",
        "path=",
        "price series",
        "real return",
        "real returns",
        "secret",
        "ticker",
        "token",
        "vendor",
    ):
        assert forbidden_term not in scrubbed_json

    _assert_no_real_etf_tickers(compact_json)
    _assert_no_real_vendor_or_source_identifiers(compact_json)


def test_report_fixture_module_has_only_allowed_dependencies_and_no_runtime_calls() -> None:
    imports = _import_references()
    imported_planning_replay_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "tests.fixtures.research_planning_replay"
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
        "tests.fixtures.research_planning_replay",
    }
    assert imported_planning_replay_names == {
        "build_synthetic_broad_etf_planning_replay_fixture",
    }
    assert violations == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


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


def _all_negative_assertion_values(
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    values: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            values.extend(_all_negative_assertion_values(item, (*path, str(key))))
    elif isinstance(value, list):
        field_name = path[-1] if path else "item"
        for item in value:
            values.extend(_all_negative_assertion_values(item, (*path, field_name)))
    elif isinstance(value, str) and path and path[-1] in {
        "methodology_non_claims",
        "non_claims",
    }:
        values.append(value)

    return tuple(values)


def _scrub_negative_assertions(lowered_json: str, payload: dict[str, object]) -> str:
    scrubbed = lowered_json
    for text in sorted(_all_negative_assertion_values(payload), key=len, reverse=True):
        scrubbed = scrubbed.replace(text.lower(), "")
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
