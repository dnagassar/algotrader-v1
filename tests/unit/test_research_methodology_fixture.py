import ast
from datetime import date
import json
from pathlib import Path
import re

from algotrader.research.research_methodology import (
    REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS,
    ResearchMethodologyCandidate,
    ResearchMethodologyScopeSnapshot,
    ResearchParameterSetCandidate,
)
from tests.fixtures.research_methodology import (
    build_synthetic_broad_etf_methodology_scope,
    expected_synthetic_broad_etf_methodology_scope_dict,
    expected_synthetic_broad_etf_methodology_scope_json,
)
from tests.fixtures.research_scope import build_synthetic_broad_etf_research_scope
from tests.helpers.research_planning_guardrails import (
    FORBIDDEN_RAW_MARKET_FIELD_NAMES,
    FORBIDDEN_RUNTIME_FIELD_NAMES,
    FORBIDDEN_SELECTION_FIELD_NAMES,
    all_serialized_keys,
    assert_json_payload_uses_only_primitives,
    assert_no_forbidden_terms,
    assert_no_raw_market_data_surface,
    assert_no_real_etf_tickers,
    assert_no_real_vendor_or_source_identifiers,
    assert_planning_states_are_non_approved,
)


MODULE_PATH = Path("tests/fixtures/research_methodology.py")

_FORBIDDEN_CONTENT_TERMS = (
    "account_id",
    "api_key",
    "candidate discovery",
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


def test_fixture_construction_returns_expected_candidate_contracts() -> None:
    scope = build_synthetic_broad_etf_methodology_scope()
    methodology = scope.methodology_candidates[0]
    parameter_set = scope.parameter_set_candidates[0]
    linked_research_scope = build_synthetic_broad_etf_research_scope()

    assert isinstance(scope, ResearchMethodologyScopeSnapshot)
    assert isinstance(methodology, ResearchMethodologyCandidate)
    assert isinstance(parameter_set, ResearchParameterSetCandidate)
    assert scope.as_of_date == date(2026, 1, 19)
    assert scope.approval_state == "candidate_only"
    assert len(scope.methodology_candidates) == 1
    assert len(scope.parameter_set_candidates) == 1
    assert methodology.methodology_type == "moving_average_trend_candidate"
    assert parameter_set.parameter_type == "single_window_candidate"
    assert parameter_set.moving_average_windows == (200,)
    assert parameter_set.methodology_id == methodology.methodology_id
    assert methodology.linked_scope_ids == (linked_research_scope.scope_id,)

    assert_planning_states_are_non_approved(
        _approval_states(scope),
        context="research methodology fixture approval states",
    )

    for item in _scope_and_candidates(scope):
        assert item.blockers
        assert item.limitations
        assert item.required_follow_up
        assert item.non_claims == REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS

    serialized = json.dumps(scope.to_dict(), separators=(",", ":"))
    assert_no_real_etf_tickers(serialized, context="research methodology fixture JSON")
    assert_no_real_vendor_or_source_identifiers(
        serialized,
        context="research methodology fixture JSON",
    )
    assert_no_raw_market_data_surface(
        scope.to_dict(),
        serialized,
        context="research methodology fixture JSON",
    )


def test_fixture_serialization_matches_expected_primitives_and_compact_json() -> None:
    scope = build_synthetic_broad_etf_methodology_scope()
    payload = scope.to_dict()
    compact_json = json.dumps(payload, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(compact_json), separators=(",", ":"))

    assert payload == expected_synthetic_broad_etf_methodology_scope_dict()
    assert compact_json == expected_synthetic_broad_etf_methodology_scope_json()
    assert round_tripped == compact_json
    assert_json_payload_uses_only_primitives(
        payload,
        context="research methodology fixture payload",
    )
    assert " at 0x" not in compact_json
    assert "Research" not in compact_json
    assert "Decimal(" not in compact_json
    assert "datetime." not in compact_json


def test_fixture_construction_and_serialization_are_deterministic() -> None:
    first_scope = build_synthetic_broad_etf_methodology_scope()
    second_scope = build_synthetic_broad_etf_methodology_scope()

    assert first_scope == second_scope
    assert first_scope is not second_scope
    assert first_scope.methodology_candidates[0] is not second_scope.methodology_candidates[0]
    assert first_scope.parameter_set_candidates[0] is not (
        second_scope.parameter_set_candidates[0]
    )

    first_payload = first_scope.to_dict()
    second_payload = first_scope.to_dict()
    third_payload = second_scope.to_dict()
    first_json = json.dumps(first_payload, separators=(",", ":"))
    second_json = json.dumps(second_payload, separators=(",", ":"))
    third_json = json.dumps(third_payload, separators=(",", ":"))

    assert first_payload == second_payload == third_payload
    assert first_json == second_json == third_json
    assert first_json == expected_synthetic_broad_etf_methodology_scope_json()


def test_fixture_output_contains_no_runtime_selection_or_approval_claim_surface() -> None:
    payload = build_synthetic_broad_etf_methodology_scope().to_dict()
    keys = all_serialized_keys(payload)
    compact_json = json.dumps(payload, separators=(",", ":"))
    lowered_json = compact_json.lower()

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
        context="research methodology fixture JSON",
    )

    assert_no_real_etf_tickers(
        compact_json,
        context="research methodology fixture JSON",
    )
    assert_no_real_vendor_or_source_identifiers(
        compact_json,
        context="research methodology fixture JSON",
    )
    _assert_no_affirmative_approval_claims(lowered_json)


def test_return_construction_policy_key_does_not_hide_real_returns_content() -> None:
    payload = build_synthetic_broad_etf_methodology_scope().to_dict()
    methodology = payload["methodology_candidates"][0]
    compact_json = json.dumps(payload, separators=(",", ":")).lower()

    assert methodology["return_construction_policy"] == (
        "synthetic convention placeholder with no calculation selected"
    )
    assert "return_construction_policy" in compact_json

    scrubbed_json = compact_json.replace("return_construction_policy", "")
    for forbidden_phrase in (
        "real return",
        "real returns",
        "daily return",
        "return series",
        "price series",
        "market data",
        "performance result",
        "performance results",
    ):
        assert forbidden_phrase not in scrubbed_json


def test_fixture_module_has_only_allowed_imports_and_no_io_network_clock_calls() -> None:
    imports = _import_references()
    imported_datetime_names = {
        alias.name
        for node in ast.walk(_tree())
        if isinstance(node, ast.ImportFrom) and node.module == "datetime"
        for alias in node.names
    }
    imported_contract_names = {
        alias.name
        for node in ast.walk(_tree())
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "algotrader.research.research_methodology"
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
        "algotrader.research.research_methodology",
    }
    assert imported_datetime_names == {"date"}
    assert imported_contract_names == {
        "ResearchMethodologyCandidate",
        "ResearchMethodologyScopeSnapshot",
        "ResearchParameterSetCandidate",
    }
    assert violations == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _approval_states(scope: ResearchMethodologyScopeSnapshot) -> tuple[str, ...]:
    return tuple(item.approval_state for item in _scope_and_candidates(scope))


def _scope_and_candidates(
    scope: ResearchMethodologyScopeSnapshot,
) -> tuple[object, ...]:
    return (
        scope,
        *scope.methodology_candidates,
        *scope.parameter_set_candidates,
    )


def _assert_no_affirmative_approval_claims(lowered_json: str) -> None:
    scrubbed = lowered_json
    for required_non_claim in REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS:
        scrubbed = scrubbed.replace(required_non_claim, "")

    for phrase in (
        "methodology approval",
        "parameter approval",
        "evidence approval",
        "source approval",
        "universe approval",
        "benchmark approval",
        "cash proxy approval",
        "strategy validation",
        "signal approval",
        "evaluator approval",
        "trading authority",
        "real data ingestion",
    ):
        assert phrase not in scrubbed


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
