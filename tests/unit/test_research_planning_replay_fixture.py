import ast
from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import re
from types import ModuleType

import pytest

import tests.fixtures.research_planning_replay as planning_replay_module
from tests.fixtures.research_planning import (
    build_synthetic_broad_etf_research_planning_package,
)
from tests.fixtures.research_planning_replay import (
    build_synthetic_broad_etf_planning_replay_fixture,
    build_synthetic_broad_etf_planning_replay_package,
)


MODULE_PATH = Path("tests/fixtures/research_planning_replay.py")

_ALLOWED_APPROVAL_STATES = {"candidate_only", "blocked", "deferred"}

_REQUIRED_PHASE_78_NON_CLAIMS = {
    "synthetic fixture output only",
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not evidence approval",
    "not a strategy validation artifact",
    "not trading-ready",
    "not a signal definition",
    "not an evaluator",
    "not candidate discovery",
    "not ranking, scoring, or recommendation",
    "does not create orders, positions, portfolio state, broker calls, or runtime behavior",
    "no real data ingestion",
    "no market-data, network, LLM, credential, paper, or live behavior",
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

_FORBIDDEN_RUNTIME_FIELD_NAMES = {
    "account",
    "account_id",
    "allocation",
    "broker",
    "broker_call",
    "broker_calls",
    "capital_allocation",
    "credential",
    "credentials",
    "execution",
    "execution_intent",
    "fill",
    "live",
    "order",
    "order_intent",
    "paper_eligible",
    "portfolio",
    "position",
    "position_size",
    "position_sizing",
    "runtime",
    "scheduler",
    "target_weight",
    "tradable",
    "trading_action",
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

_FORBIDDEN_CONTENT_TERMS = (
    ".data",
    "account_id",
    "api_key",
    "candidate discovery",
    "candidate-discovery",
    "candidate_discovery",
    "capital allocation",
    "credential",
    "http://",
    "https://",
    "market data",
    "password",
    "paper_eligible",
    "path=",
    "position sizing",
    "price series",
    "ranking",
    "recommendation",
    "real return",
    "real returns",
    "score",
    "scoring",
    "secret",
    "ticker",
    "token",
    "vendor",
)

_SENSITIVE_TEXT_TERMS = (
    "approved",
    "approval",
    "validated",
    "tradable",
    "live",
    "paper_eligible",
    "order",
    "orders",
    "broker",
    "portfolio",
    "position size",
    "position sizing",
    "signal",
    "evaluator",
)

_NEGATIVE_MARKERS = (
    "not ",
    "no ",
    "does not",
    "do not",
    "cannot ",
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


def test_consumer_uses_planning_fixture_and_existing_replay_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    original_builder = planning_replay_module.build_moving_average_replay_package

    def builder_wrapper(*, replay_id, as_of_date, inputs, window):
        input_items = tuple(inputs)
        calls.append(
            {
                "replay_id": replay_id,
                "as_of_date": as_of_date,
                "input_count": len(input_items),
                "window": window,
            }
        )
        return original_builder(
            replay_id=replay_id,
            as_of_date=as_of_date,
            inputs=input_items,
            window=window,
        )

    monkeypatch.setattr(
        planning_replay_module,
        "build_moving_average_replay_package",
        builder_wrapper,
    )

    result = build_synthetic_broad_etf_planning_replay_fixture()
    planning_package = build_synthetic_broad_etf_research_planning_package()
    consumed = result["consumed_planning_metadata"]
    replay_package = result["replay_package"]

    assert calls == [
        {
            "replay_id": "synthetic_broad_etf_planning_replay_candidate",
            "as_of_date": date(2026, 1, 21),
            "input_count": 201,
            "window": 200,
        }
    ]
    assert result["planning_replay_fixture_id"] == (
        "synthetic_broad_etf_planning_replay_fixture_candidate"
    )
    assert result["planning_package"] == planning_package
    assert consumed["planning_package_id"] == planning_package["planning_package_id"]
    assert consumed["moving_average_window"] == 200
    assert replay_package["replay_id"] == (
        "synthetic_broad_etf_planning_replay_candidate"
    )
    assert replay_package["window"] == consumed["moving_average_window"]
    assert replay_package["as_of_date"] == "2026-01-21"
    assert replay_package["inputs"][0] == {
        "observation_date": "2025-07-05",
        "value": "1000",
    }
    assert replay_package["inputs"][-1] == {
        "observation_date": "2026-01-21",
        "value": "1200",
    }


def test_consumer_output_is_deterministic_json_primitive_and_byte_stable() -> None:
    first = build_synthetic_broad_etf_planning_replay_fixture()
    second = build_synthetic_broad_etf_planning_replay_fixture()
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


def test_consumer_keeps_planning_states_candidate_blocked_or_deferred_only() -> None:
    result = build_synthetic_broad_etf_planning_replay_fixture()
    approval_states = tuple(_approval_states(result))

    assert approval_states
    assert set(approval_states) <= _ALLOWED_APPROVAL_STATES
    assert "approved" not in approval_states
    assert set(result["non_claims"]) >= _REQUIRED_PHASE_78_NON_CLAIMS
    _assert_sensitive_terms_are_negative_only(result)


def test_methodology_non_claims_evidence_refs_and_linked_scope_stay_metadata_only() -> None:
    result = build_synthetic_broad_etf_planning_replay_fixture()
    planning_package = result["planning_package"]
    research_scope = planning_package["research_scope"]
    methodology_scope = planning_package["methodology_scope"]
    methodology = methodology_scope["methodology_candidates"][0]
    parameter_set = methodology_scope["parameter_set_candidates"][0]
    consumed = result["consumed_planning_metadata"]

    assert "not evidence approval" in methodology["non_claims"]
    assert "not evidence approval" in parameter_set["non_claims"]
    assert "not evidence approval" in methodology_scope["non_claims"]
    assert consumed["evidence_refs"] == methodology["evidence_refs"]
    assert consumed["linked_scope_ids"] == methodology["linked_scope_ids"]
    assert research_scope["scope_id"] in consumed["linked_scope_ids"]
    assert consumed["research_scope_id"] == research_scope["scope_id"]

    keys = _all_serialized_keys(result)
    assert "evidence_approval" not in keys
    assert "evidence_validated" not in keys
    assert "validated_evidence" not in keys

    scrubbed_json = _scrub_negative_assertions(
        json.dumps(result, separators=(",", ":")).lower(),
        result,
    )
    assert "evidence approval" not in scrubbed_json
    assert "validated evidence" not in scrubbed_json


def test_consumer_does_not_mutate_planning_fixture_or_replay_package_objects() -> None:
    planning_package = build_synthetic_broad_etf_research_planning_package()
    planning_before_json = json.dumps(planning_package, separators=(",", ":"))
    replay_package = build_synthetic_broad_etf_planning_replay_package(
        planning_package
    )
    replay_before_payload = replay_package.to_dict()

    result = build_synthetic_broad_etf_planning_replay_fixture(
        planning_package=planning_package,
        replay_package=replay_package,
    )

    assert json.dumps(planning_package, separators=(",", ":")) == planning_before_json
    assert replay_package.to_dict() == replay_before_payload
    assert result["planning_package"] == planning_package
    assert result["planning_package"] is not planning_package
    assert result["planning_package"]["research_scope"] is not (
        planning_package["research_scope"]
    )
    assert result["replay_package"] == replay_before_payload


def test_replay_shape_is_existing_metadata_only_contract_without_new_metrics() -> None:
    result = build_synthetic_broad_etf_planning_replay_fixture()
    replay_package = result["replay_package"]
    summary = replay_package["summary"]
    keys = _all_serialized_keys(result)
    replay_keys = set(replay_package)
    summary_keys = set(summary)

    assert replay_keys == {
        "replay_id",
        "as_of_date",
        "window",
        "inputs",
        "moving_average_observations",
        "exposure_states",
        "exposure_returns",
        "cumulative_path",
        "summary",
        "limitations",
        "non_claims",
    }
    assert summary_keys == {
        "first_observation_date",
        "last_observation_date",
        "observation_count",
        "available_return_count",
        "unavailable_return_count",
        "final_asset_cumulative_return",
        "final_exposure_cumulative_return",
        "has_available_returns",
        "limitations",
        "non_claims",
    }
    assert keys.isdisjoint(_FORBIDDEN_NEW_REPLAY_METRIC_KEYS)
    assert keys.isdisjoint(_FORBIDDEN_SELECTION_FIELD_NAMES)
    assert keys.isdisjoint(_FORBIDDEN_RUNTIME_FIELD_NAMES)
    assert "benchmark_relative_return" not in keys
    assert "signal_definition" not in keys
    assert "evaluator_result" not in keys
    assert "trading_action" not in keys


def test_false_interpretation_guardrails_are_explicitly_negative() -> None:
    result = build_synthetic_broad_etf_planning_replay_fixture()
    replay_package = result["replay_package"]
    result_non_claims = set(result["non_claims"])
    replay_non_claims = set(replay_package["non_claims"])
    summary_non_claims = set(replay_package["summary"]["non_claims"])

    assert result_non_claims >= _REQUIRED_PHASE_78_NON_CLAIMS
    assert "not validated evidence" in replay_non_claims
    assert "not validated evidence" in summary_non_claims
    assert "not a strategy approval" in replay_non_claims
    assert "not a trading recommendation" in replay_non_claims
    assert "not an approved signal" in replay_non_claims
    assert "not paper/live trading authority" in replay_non_claims
    assert "no broker/order/fill/portfolio/runtime behavior" in replay_non_claims
    assert replay_package["summary"]["has_available_returns"] is True
    assert "not a strategy validation artifact" in result_non_claims
    assert "not trading-ready" in result_non_claims
    assert "not a signal definition" in result_non_claims
    assert "not an evaluator" in result_non_claims
    assert (
        "does not create orders, positions, portfolio state, broker calls, or runtime behavior"
        in result_non_claims
    )

    scrubbed_json = _scrub_negative_assertions(
        json.dumps(result, separators=(",", ":")).lower(),
        result,
    )
    for phrase in (
        "strategy validation artifact",
        "source approval",
        "universe approval",
        "benchmark approval",
        "cash proxy approval",
        "methodology approval",
        "parameter approval",
        "evidence approval",
        "trading-ready",
        "signal definition",
        "evaluator",
        "trading recommendation",
        "paper/live trading authority",
        "broker/order/fill/portfolio/runtime behavior",
    ):
        assert phrase not in scrubbed_json


def test_consumer_introduces_no_real_data_tickers_vendors_paths_or_credentials() -> None:
    result = build_synthetic_broad_etf_planning_replay_fixture()
    compact_json = json.dumps(result, separators=(",", ":"))
    lowered_json = compact_json.lower()
    scrubbed_json = _scrub_negative_assertions(lowered_json, result)
    keys = _all_serialized_keys(result)

    assert keys.isdisjoint(_FORBIDDEN_RAW_MARKET_FIELD_NAMES)
    assert "$" not in compact_json
    assert "://" not in compact_json
    assert "\\.data" not in lowered_json
    assert "/.data" not in lowered_json
    assert "market_data" not in lowered_json

    for forbidden_term in _FORBIDDEN_CONTENT_TERMS:
        assert forbidden_term not in scrubbed_json

    for forbidden_phrase in (
        "adjusted close",
        "daily price",
        "market data path",
        "ohlc",
        "raw market data",
        "real date from market data",
        "real price",
        "return series",
        "third-party",
        "volume",
    ):
        assert forbidden_phrase not in scrubbed_json

    _assert_no_real_etf_tickers(compact_json)
    _assert_no_real_vendor_or_source_identifiers(compact_json)


def test_fixture_module_has_only_allowed_dependencies_and_no_runtime_calls() -> None:
    imports = _import_references()
    imported_datetime_names = {
        alias.name
        for node in ast.walk(_tree())
        if isinstance(node, ast.ImportFrom) and node.module == "datetime"
        for alias in node.names
    }
    imported_decimal_names = {
        alias.name
        for node in ast.walk(_tree())
        if isinstance(node, ast.ImportFrom) and node.module == "decimal"
        for alias in node.names
    }
    imported_moving_average_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "algotrader.research.moving_average"
        )
        for alias in node.names
    }
    imported_replay_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "algotrader.research.moving_average_replay"
        )
        for alias in node.names
    }
    imported_planning_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "tests.fixtures.research_planning"
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
        "datetime",
        "decimal",
        "algotrader.research.moving_average",
        "algotrader.research.moving_average_replay",
        "tests.fixtures.research_planning",
    }
    assert imported_datetime_names == {"date", "timedelta"}
    assert imported_decimal_names == {"Decimal"}
    assert imported_moving_average_names == {"MovingAverageInput"}
    assert imported_replay_names == {
        "MovingAverageReplayPackage",
        "build_moving_average_replay_package",
    }
    assert imported_planning_names == {
        "build_synthetic_broad_etf_research_planning_package",
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


def _all_non_claims_and_limitations(value: object) -> tuple[str, ...]:
    claims: list[str] = []

    if isinstance(value, dict):
        for field_name in ("non_claims", "limitations"):
            field_value = value.get(field_name)
            if isinstance(field_value, list):
                claims.extend(item for item in field_value if isinstance(item, str))
        for item in value.values():
            claims.extend(_all_non_claims_and_limitations(item))
    elif isinstance(value, list):
        for item in value:
            claims.extend(_all_non_claims_and_limitations(item))

    return tuple(claims)


def _scrub_negative_assertions(lowered_json: str, payload: dict[str, object]) -> str:
    scrubbed = lowered_json
    for text in sorted(_all_non_claims_and_limitations(payload), key=len, reverse=True):
        scrubbed = scrubbed.replace(text.lower(), "")
    return scrubbed


def _assert_sensitive_terms_are_negative_only(payload: dict[str, object]) -> None:
    for key in _all_serialized_keys(payload):
        lowered_key = key.lower()
        if "approval" in lowered_key:
            assert lowered_key == "approval_state"
        for forbidden_key in (
            "approved",
            "validated",
            "tradable",
            "paper_eligible",
            "position_sizing",
        ):
            assert forbidden_key not in lowered_key

    for path, text in _string_values(payload):
        lowered = text.lower()
        if not any(term in lowered for term in _SENSITIVE_TEXT_TERMS):
            continue
        assert _is_negative_assertion(path, lowered), (
            ".".join(path),
            text,
        )


def _string_values(
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[tuple[tuple[str, ...], str], ...]:
    values: list[tuple[tuple[str, ...], str]] = []

    if isinstance(value, dict):
        for key, item in value.items():
            values.extend(_string_values(item, (*path, str(key))))
    elif isinstance(value, list):
        field_name = path[-1] if path else "item"
        for item in value:
            values.extend(_string_values(item, (*path, field_name)))
    elif isinstance(value, str):
        values.append((path, value))

    return tuple(values)


def _is_negative_assertion(path: tuple[str, ...], lowered: str) -> bool:
    if path and path[-1] in {"non_claims", "limitations"}:
        return any(marker in lowered for marker in _NEGATIVE_MARKERS)

    return any(marker in lowered for marker in ("does not", "do not"))


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
