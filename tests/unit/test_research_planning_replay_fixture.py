import ast
from datetime import date
import json
from pathlib import Path

import pytest

from tests.helpers.research_planning_guardrails import (
    FORBIDDEN_NEW_REPLAY_METRIC_KEYS,
    FORBIDDEN_RAW_MARKET_FIELD_NAMES,
    FORBIDDEN_RUNTIME_FIELD_NAMES,
    FORBIDDEN_SELECTION_FIELD_NAMES,
    all_serialized_keys,
    approval_states,
    assert_json_payload_uses_only_primitives,
    assert_no_evidence_approval_fields,
    assert_no_forbidden_terms,
    assert_no_real_etf_tickers,
    assert_no_real_vendor_or_source_identifiers,
    assert_non_claims_include_not_evidence_approval,
    assert_planning_states_are_non_approved,
    assert_required_non_claims_present,
    assert_sensitive_terms_are_negative_only,
    scrub_negative_assertions,
)
import tests.fixtures.research_planning_replay as planning_replay_module
from tests.fixtures.research_planning import (
    build_synthetic_broad_etf_research_planning_package,
)
from tests.fixtures.research_planning_replay import (
    build_synthetic_broad_etf_planning_replay_fixture,
    build_synthetic_broad_etf_planning_replay_package,
)


MODULE_PATH = Path("tests/fixtures/research_planning_replay.py")

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
    assert_json_payload_uses_only_primitives(
        first,
        context="planning replay fixture payload",
    )
    assert " at 0x" not in first_json
    assert "Decimal(" not in first_json
    assert "datetime." not in first_json
    assert "MovingAverage" not in first_json


def test_consumer_keeps_planning_states_candidate_blocked_or_deferred_only() -> None:
    result = build_synthetic_broad_etf_planning_replay_fixture()
    planning_states = approval_states(result)

    assert_planning_states_are_non_approved(
        planning_states,
        context="planning replay fixture approval states",
    )
    assert_required_non_claims_present(
        result["non_claims"],
        _REQUIRED_PHASE_78_NON_CLAIMS,
        context="planning replay fixture non_claims",
    )
    assert_sensitive_terms_are_negative_only(
        result,
        context="planning replay fixture",
    )


def test_methodology_non_claims_evidence_refs_and_linked_scope_stay_metadata_only() -> None:
    result = build_synthetic_broad_etf_planning_replay_fixture()
    planning_package = result["planning_package"]
    research_scope = planning_package["research_scope"]
    methodology_scope = planning_package["methodology_scope"]
    methodology = methodology_scope["methodology_candidates"][0]
    parameter_set = methodology_scope["parameter_set_candidates"][0]
    consumed = result["consumed_planning_metadata"]

    assert_non_claims_include_not_evidence_approval(
        methodology["non_claims"],
        context="methodology candidate non_claims",
    )
    assert_non_claims_include_not_evidence_approval(
        parameter_set["non_claims"],
        context="parameter set non_claims",
    )
    assert_non_claims_include_not_evidence_approval(
        methodology_scope["non_claims"],
        context="methodology scope non_claims",
    )
    assert consumed["evidence_refs"] == methodology["evidence_refs"]
    assert consumed["linked_scope_ids"] == methodology["linked_scope_ids"]
    assert research_scope["scope_id"] in consumed["linked_scope_ids"]
    assert consumed["research_scope_id"] == research_scope["scope_id"]

    assert_no_evidence_approval_fields(
        result,
        context="planning replay fixture",
    )

    scrubbed_json = scrub_negative_assertions(
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
    keys = all_serialized_keys(result)
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
    assert keys.isdisjoint(FORBIDDEN_NEW_REPLAY_METRIC_KEYS)
    assert keys.isdisjoint(FORBIDDEN_SELECTION_FIELD_NAMES)
    assert keys.isdisjoint(FORBIDDEN_RUNTIME_FIELD_NAMES)
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

    assert_required_non_claims_present(
        result_non_claims,
        _REQUIRED_PHASE_78_NON_CLAIMS,
        context="planning replay fixture non_claims",
    )
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

    scrubbed_json = scrub_negative_assertions(
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
    scrubbed_json = scrub_negative_assertions(lowered_json, result)
    keys = all_serialized_keys(result)

    assert keys.isdisjoint(FORBIDDEN_RAW_MARKET_FIELD_NAMES)
    assert "$" not in compact_json
    assert "://" not in compact_json
    assert "\\.data" not in lowered_json
    assert "/.data" not in lowered_json
    assert "market_data" not in lowered_json

    assert_no_forbidden_terms(
        scrubbed_json,
        _FORBIDDEN_CONTENT_TERMS,
        context="planning replay fixture scrubbed JSON",
    )
    assert_no_forbidden_terms(
        scrubbed_json,
        (
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
        ),
        context="planning replay fixture scrubbed JSON",
    )

    assert_no_real_etf_tickers(compact_json, context="planning replay fixture JSON")
    assert_no_real_vendor_or_source_identifiers(
        compact_json,
        context="planning replay fixture JSON",
    )


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
