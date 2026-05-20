import ast
import json
from pathlib import Path
import re

import pytest

from tests.helpers.research_planning_guardrails import (
    FORBIDDEN_RAW_MARKET_FIELD_NAMES,
    FORBIDDEN_RUNTIME_FIELD_NAMES,
    FORBIDDEN_SELECTION_FIELD_NAMES,
    REJECTED_PLANNING_STATE_EXAMPLES,
    all_serialized_keys,
    approval_states,
    assert_json_payload_uses_only_primitives,
    assert_no_forbidden_terms,
    assert_no_real_etf_tickers,
    assert_no_real_vendor_or_source_identifiers,
    assert_planning_states_are_non_approved,
    assert_required_non_claims_present,
    scrub_negative_assertions,
)
from tests.fixtures.research_methodology import (
    build_synthetic_broad_etf_methodology_scope,
    expected_synthetic_broad_etf_methodology_scope_json,
)
from tests.fixtures.research_planning import (
    build_synthetic_broad_etf_research_planning_package,
    expected_synthetic_broad_etf_research_planning_package_json,
)
from tests.fixtures.research_scope import (
    build_synthetic_broad_etf_research_scope,
    expected_synthetic_broad_etf_research_scope_json,
)


MODULE_PATH = Path("tests/fixtures/research_planning.py")

_REQUIRED_NON_CLAIMS = {
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not evidence approval",
    "not strategy validation",
    "not signal approval",
    "not evaluator approval",
    "not trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "no real data ingestion",
}

_FORBIDDEN_CONTENT_TERMS = (
    "account_id",
    "api_key",
    "candidate discovery",
    "candidate-discovery",
    "candidate_discovery",
    "credential",
    "http://",
    "https://",
    "market data",
    "market-data",
    "password",
    "price",
    "prices",
    "ranking",
    "recommendation",
    "returns",
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


def test_combined_fixture_construction_uses_existing_synthetic_scopes() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    research_scope = build_synthetic_broad_etf_research_scope()
    methodology_scope = build_synthetic_broad_etf_methodology_scope()
    methodology = package["methodology_scope"]["methodology_candidates"][0]

    assert type(package) is dict
    assert tuple(package) == (
        "planning_package_id",
        "as_of_date",
        "research_scope",
        "methodology_scope",
        "limitations",
        "non_claims",
    )
    assert package["planning_package_id"] == (
        "synthetic_broad_etf_research_planning_package_candidate"
    )
    assert package["as_of_date"] == "2026-01-20"
    assert type(package["research_scope"]) is dict
    assert type(package["methodology_scope"]) is dict
    assert package["research_scope"] == research_scope.to_dict()
    assert package["methodology_scope"] == methodology_scope.to_dict()
    assert package["research_scope"]["as_of_date"] == "2026-01-18"
    assert package["methodology_scope"]["as_of_date"] == "2026-01-19"
    assert package["research_scope"]["approval_state"] == "candidate_only"
    assert package["methodology_scope"]["approval_state"] == "candidate_only"
    assert research_scope.scope_id in methodology["linked_scope_ids"]
    _assert_methodology_scope_links_research_scope(package)


def test_combined_fixture_linked_scope_assertion_fails_loudly_for_mismatch() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    methodology_scope = dict(package["methodology_scope"])
    methodology_candidates = list(methodology_scope["methodology_candidates"])
    methodology = dict(methodology_candidates[0])
    methodology["linked_scope_ids"] = ["synthetic_unpaired_scope_candidate"]
    methodology_candidates[0] = methodology
    methodology_scope["methodology_candidates"] = methodology_candidates
    broken_package = dict(package)
    broken_package["methodology_scope"] = methodology_scope

    with pytest.raises(AssertionError, match="linked_scope_ids"):
        _assert_methodology_scope_links_research_scope(broken_package)


def test_combined_fixture_keeps_all_embedded_candidates_non_approved() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    planning_states = approval_states(package)

    assert_planning_states_are_non_approved(
        planning_states,
        context="planning package embedded approval states",
    )
    assert_required_non_claims_present(
        package["non_claims"],
        _REQUIRED_NON_CLAIMS,
        context="planning package non_claims",
    )

    compact_json = json.dumps(package, separators=(",", ":"))
    scrubbed_json = scrub_negative_assertions(compact_json.lower(), package)

    for phrase in (
        "source approval",
        "universe approval",
        "benchmark approval",
        "cash proxy approval",
        "methodology approval",
        "parameter approval",
        "evidence approval",
        "strategy validation",
        "signal approval",
        "evaluator approval",
        "trading authority",
        "real data ingestion",
    ):
        assert phrase not in scrubbed_json


def test_combined_fixture_allowed_state_guardrail_rejects_approval_labels() -> None:
    for approval_state in REJECTED_PLANNING_STATE_EXAMPLES:
        with pytest.raises(AssertionError, match="approval"):
            assert_planning_states_are_non_approved(
                (approval_state,),
                context="planning approval state",
            )


def test_combined_fixture_serialization_is_primitive_and_byte_stable() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    compact_json = json.dumps(package, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(compact_json), separators=(",", ":"))

    assert compact_json == expected_synthetic_broad_etf_research_planning_package_json()
    assert round_tripped == compact_json
    assert json.dumps(package["research_scope"], separators=(",", ":")) == (
        expected_synthetic_broad_etf_research_scope_json()
    )
    assert json.dumps(package["methodology_scope"], separators=(",", ":")) == (
        expected_synthetic_broad_etf_methodology_scope_json()
    )
    assert_json_payload_uses_only_primitives(
        package,
        context="planning package payload",
    )
    assert " at 0x" not in compact_json
    assert "Research" not in compact_json
    assert "Decimal(" not in compact_json
    assert "datetime." not in compact_json


def test_combined_fixture_contains_no_real_data_or_trading_surface() -> None:
    package = build_synthetic_broad_etf_research_planning_package()
    keys = all_serialized_keys(package)
    compact_json = json.dumps(package, separators=(",", ":"))
    lowered_json = compact_json.lower()
    scrubbed_json = scrub_negative_assertions(lowered_json, package)

    assert keys.isdisjoint(FORBIDDEN_RUNTIME_FIELD_NAMES)
    assert keys.isdisjoint(FORBIDDEN_SELECTION_FIELD_NAMES)
    assert keys.isdisjoint(FORBIDDEN_RAW_MARKET_FIELD_NAMES)
    assert '"approval_state":"approved"' not in lowered_json
    assert '"approval_state":"candidate_only"' in lowered_json
    assert "$" not in compact_json
    assert "://" not in compact_json
    assert not re.search(r"\b\d+\.\d+\b", compact_json)

    assert_no_forbidden_terms(
        lowered_json,
        _FORBIDDEN_CONTENT_TERMS,
        context="planning package JSON",
    )
    assert_no_forbidden_terms(
        scrubbed_json,
        (
            "adjusted close",
            "daily return",
            "market data",
            "ohlc",
            "return series",
            "real data ingestion",
            "volume",
        ),
        context="planning package scrubbed JSON",
    )

    assert_no_real_etf_tickers(compact_json, context="planning package JSON")
    assert_no_real_vendor_or_source_identifiers(
        compact_json,
        context="planning package JSON",
    )


def test_fixture_module_has_only_allowed_dependencies_and_no_runtime_calls() -> None:
    imports = _import_references()
    imported_research_scope_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "tests.fixtures.research_scope"
        )
        for alias in node.names
    }
    imported_methodology_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "tests.fixtures.research_methodology"
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
        "tests.fixtures.research_methodology",
        "tests.fixtures.research_scope",
    }
    assert imported_research_scope_names == {
        "build_synthetic_broad_etf_research_scope",
        "expected_synthetic_broad_etf_research_scope_json",
    }
    assert imported_methodology_names == {
        "build_synthetic_broad_etf_methodology_scope",
        "expected_synthetic_broad_etf_methodology_scope_json",
    }
    assert violations == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _assert_methodology_scope_links_research_scope(
    package: dict[str, object],
) -> None:
    research_scope = package["research_scope"]
    methodology_scope = package["methodology_scope"]
    assert isinstance(research_scope, dict)
    assert isinstance(methodology_scope, dict)
    research_scope_id = research_scope["scope_id"]

    for methodology in methodology_scope["methodology_candidates"]:
        assert isinstance(methodology, dict)
        linked_scope_ids = methodology["linked_scope_ids"]
        assert research_scope_id in linked_scope_ids, (
                "linked_scope_ids must reference the paired research scope id"
        )


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
