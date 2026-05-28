from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from algotrader.research.advisory_operating_brief_view import (
    AdvisoryOperatingBriefView,
    build_advisory_operating_brief_view,
)
from tests.fixtures import advisory_operating_brief_view as fixture_module
from tests.fixtures.advisory_operating_brief_section import (
    build_synthetic_advisory_operating_brief_sections,
)
from tests.fixtures.advisory_operating_brief_view import (
    build_synthetic_advisory_operating_brief_view,
    expected_synthetic_advisory_operating_brief_view_dict,
    expected_synthetic_advisory_operating_brief_view_export_snapshot_dict,
    expected_synthetic_advisory_operating_brief_view_export_snapshot_json,
    expected_synthetic_advisory_operating_brief_view_json,
)


FIXTURE_PATH = Path("tests/fixtures/advisory_operating_brief_view.py")
EXPECTED_VIEW_KEYS = [
    "view_key",
    "view_title",
    "view_state",
    "section_count",
    "section_keys",
    "summary_lines",
    "diagnostic_messages",
    "limitations",
]
EXPECTED_SECTION_KEYS = [
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "research_data_source_readiness",
    "research_data_source_readiness_summaries",
    "diagnostic_issues",
]
EXPECTED_SUMMARY_LINES = [
    "candidate_research_briefs: Candidate research brief metadata; "
    "state=candidate_only; count=1",
    "strategy_eligibility_briefs: Strategy eligibility brief metadata; "
    "state=candidate_only; count=1",
    "research_data_source_readiness: Research data-source readiness diagnostic "
    "metadata; state=candidate_only; count=1",
    "research_data_source_readiness_summaries: Research data-source readiness "
    "summary diagnostic metadata; state=candidate_only; count=1",
    "diagnostic_issues: Diagnostic issue metadata; state=candidate_only; count=2",
]
EXPECTED_DIAGNOSTIC_MESSAGES = [
    "Readiness branch reports missing diagnostic controls.",
    "Readiness summary branch reports missing diagnostic controls.",
]
EXPECTED_LIMITATIONS = [
    "metadata-only view over supplied advisory section records",
    "describes section keys, titles, states, counts, and diagnostics only",
    "does not render section content or change section records",
]
FORBIDDEN_SNAPSHOT_KEYS = {
    "allocation",
    "approval",
    "approved",
    "authorization",
    "authorized",
    "backtest",
    "broker",
    "created_at",
    "credential",
    "dashboard",
    "digest",
    "fill",
    "generated_at",
    "order",
    "portfolio",
    "priority",
    "rank",
    "ranking",
    "raw_data",
    "raw_payload",
    "recommendation",
    "runtime",
    "score",
    "severity",
    "socket",
    "timestamp",
    "usable_for_backtest",
    "validated_for_trading",
    "vendor",
    "wrapper",
}
FORBIDDEN_TEXT_TERMS = (
    "approval",
    "approved",
    "authorization",
    "authorized",
    "priority",
    "ranking",
    "ready_to_trade",
    "recommendation",
    "scoring",
    "severity",
    "validated_for_trading",
    "usable_for_backtest",
)
FORBIDDEN_SECTION_KEYS = {
    "risk_authority_briefs",
    "research_queue_briefs",
    "sma_research_observation_briefs",
    "research_return_observation_briefs",
    "research_return_summary_observation_briefs",
    "sma_research_summary_observations",
}
EXPECTED_FIXTURE_IMPORTS = {
    "__future__": ("annotations",),
    "json": (),
    "algotrader.research.advisory_operating_brief_view": (
        "AdvisoryOperatingBriefView",
        "build_advisory_operating_brief_view",
    ),
    "tests.fixtures.advisory_operating_brief_section": (
        "build_synthetic_advisory_operating_brief_sections",
    ),
}
EXPECTED_FIXTURE_CALLS = {
    "build_advisory_operating_brief_view",
    "build_synthetic_advisory_operating_brief_sections",
    "build_synthetic_advisory_operating_brief_view",
    "expected_synthetic_advisory_operating_brief_view_dict",
    "expected_synthetic_advisory_operating_brief_view_export_snapshot_dict",
    "json.dumps",
    "view.to_dict",
}
FORBIDDEN_FIXTURE_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.agent",
    "algotrader.agents",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.cli",
    "algotrader.config",
    "algotrader.dashboard",
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
    "algotrader.storage",
    "algotrader.vendor",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "network",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "polars",
    "requests",
    "sklearn",
    "socket",
    "sqlmodel",
    "urllib",
    "vectorbt",
    "yfinance",
)
FORBIDDEN_FIXTURE_CALLS = {
    "__import__",
    "client",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "eval",
    "exec",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    "ingest",
    "json.dump",
    "json.load",
    "load",
    "main",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "requests.get",
    "save",
    "socket.socket",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}
FORBIDDEN_FIXTURE_SOURCE_TOKENS = (
    "account",
    "allocation",
    "alpaca",
    "approval",
    "approved",
    "authorization",
    "authorized",
    "backtest",
    "broker",
    "credential",
    "dashboard",
    "digest",
    "fill",
    "generated_at",
    "llm",
    "network",
    "notebook",
    "openai",
    "order",
    "portfolio",
    "priority",
    "ranking",
    "raw_payload",
    "recommendation",
    "runtime",
    "scheduler",
    "scoring",
    "severity",
    "socket",
    "timestamp",
    "trading",
    "vendor",
    "wrapper",
)


def test_fixture_builds_deterministic_view_from_synthetic_sections() -> None:
    sections = build_synthetic_advisory_operating_brief_sections()
    direct_view = build_advisory_operating_brief_view(sections)
    fixture_view = build_synthetic_advisory_operating_brief_view()

    assert type(fixture_view) is AdvisoryOperatingBriefView
    assert fixture_view == direct_view
    assert fixture_view.to_dict() == direct_view.to_dict()


def test_snapshot_payload_equals_view_to_dict() -> None:
    view = build_synthetic_advisory_operating_brief_view()
    snapshot = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()

    assert snapshot == view.to_dict()
    assert snapshot == expected_synthetic_advisory_operating_brief_view_dict()
    assert list(snapshot) == EXPECTED_VIEW_KEYS


def test_snapshot_json_is_compact_sorted_and_deterministic() -> None:
    payload = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()
    first_json = (
        expected_synthetic_advisory_operating_brief_view_export_snapshot_json()
    )
    second_json = (
        expected_synthetic_advisory_operating_brief_view_export_snapshot_json()
    )
    expected_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    assert first_json == second_json == expected_json
    assert first_json == expected_synthetic_advisory_operating_brief_view_json()
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert json.loads(first_json) == payload
    assert "\n" not in first_json
    assert first_json != json.dumps(payload, sort_keys=True)


def test_snapshot_contains_expected_view_fields() -> None:
    snapshot = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()

    assert snapshot["view_key"] == "advisory_operating_brief_section_view"
    assert snapshot["view_title"] == "Advisory operating brief section view"
    assert snapshot["view_state"] == "candidate_only"
    assert snapshot["section_count"] == 5
    assert snapshot["section_keys"] == EXPECTED_SECTION_KEYS
    assert snapshot["summary_lines"] == EXPECTED_SUMMARY_LINES
    assert snapshot["diagnostic_messages"] == EXPECTED_DIAGNOSTIC_MESSAGES
    assert snapshot["limitations"] == EXPECTED_LIMITATIONS


def test_snapshot_preserves_present_sections_only_and_builder_order() -> None:
    snapshot = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()
    section_keys = _list(snapshot["section_keys"])

    assert section_keys == EXPECTED_SECTION_KEYS
    assert set(section_keys).isdisjoint(FORBIDDEN_SECTION_KEYS)
    assert snapshot["section_count"] == len(section_keys)
    assert "severity" not in _payload_keys(snapshot)
    assert "priority" not in _payload_keys(snapshot)
    assert "rank" not in _payload_keys(snapshot)


def test_snapshot_excludes_raw_timestamps_digest_wrappers_and_operating_fields() -> (
    None
):
    snapshot = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()
    snapshot_keys = _payload_keys(snapshot)
    snapshot_text = json.dumps(snapshot, sort_keys=True).lower()

    assert FORBIDDEN_SNAPSHOT_KEYS.isdisjoint(snapshot_keys)
    assert all(term not in snapshot_text for term in FORBIDDEN_TEXT_TERMS)


def test_repeated_fixture_builds_and_snapshots_are_equal() -> None:
    first_view = build_synthetic_advisory_operating_brief_view()
    second_view = build_synthetic_advisory_operating_brief_view()
    first_snapshot = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()
    second_snapshot = (
        expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()
    )

    assert first_view == second_view
    assert first_view is not second_view
    assert first_view.to_dict() == second_view.to_dict()
    assert first_snapshot == second_snapshot
    assert first_snapshot is not second_snapshot


def test_snapshot_payload_is_primitive_round_trippable_fresh_copy() -> None:
    first = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()
    second = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()
    compact_json = (
        expected_synthetic_advisory_operating_brief_view_export_snapshot_json()
    )

    assert _primitive_only(first)
    assert json.loads(compact_json) == first
    assert first["section_keys"] is not second["section_keys"]
    assert first["summary_lines"] is not second["summary_lines"]
    assert first["diagnostic_messages"] is not second["diagnostic_messages"]
    assert first["limitations"] is not second["limitations"]

    _list(first["section_keys"]).append("mutated primitive copy")
    _list(first["summary_lines"]).append("mutated primitive copy")
    _list(first["diagnostic_messages"]).append("mutated primitive copy")
    _list(first["limitations"]).append("mutated primitive copy")

    assert second["section_keys"] == EXPECTED_SECTION_KEYS
    assert second["summary_lines"] == EXPECTED_SUMMARY_LINES
    assert second["diagnostic_messages"] == EXPECTED_DIAGNOSTIC_MESSAGES
    assert second["limitations"] == EXPECTED_LIMITATIONS


def test_fixture_module_imports_are_test_only_and_dependency_bounded() -> None:
    imports = _import_details_from_path(FIXTURE_PATH)

    assert fixture_module.__all__ == [
        "build_synthetic_advisory_operating_brief_view",
        "expected_synthetic_advisory_operating_brief_view_dict",
        "expected_synthetic_advisory_operating_brief_view_export_snapshot_dict",
        "expected_synthetic_advisory_operating_brief_view_export_snapshot_json",
        "expected_synthetic_advisory_operating_brief_view_json",
    ]
    assert _public_function_names_from_path(FIXTURE_PATH) == [
        "build_synthetic_advisory_operating_brief_view",
        "expected_synthetic_advisory_operating_brief_view_dict",
        "expected_synthetic_advisory_operating_brief_view_json",
        "expected_synthetic_advisory_operating_brief_view_export_snapshot_dict",
        "expected_synthetic_advisory_operating_brief_view_export_snapshot_json",
    ]
    assert imports == EXPECTED_FIXTURE_IMPORTS
    assert _matching_imports(set(imports), FORBIDDEN_FIXTURE_IMPORT_PREFIXES) == []


def test_fixture_module_uses_no_runtime_io_or_trading_calls() -> None:
    source = _source_text_from_path(FIXTURE_PATH)
    calls = _call_names_from_path(FIXTURE_PATH)

    assert calls == EXPECTED_FIXTURE_CALLS
    assert calls.isdisjoint(FORBIDDEN_FIXTURE_CALLS)
    assert _forbidden_source_token_matches(
        source,
        FORBIDDEN_FIXTURE_SOURCE_TOKENS,
    ) == []


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (bool, int, float, str):
        return True
    if type(value) is list:
        return all(_primitive_only(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False


def _payload_keys(value: object) -> set[str]:
    if type(value) is dict:
        keys: set[str] = set()
        for key, nested_value in value.items():
            keys.add(key)
            keys.update(_payload_keys(nested_value))
        return keys

    if type(value) is list:
        keys: set[str] = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()


def _source_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree_from_path(path: Path) -> ast.AST:
    return ast.parse(_source_text_from_path(path), filename=str(path))


def _import_details_from_path(path: Path) -> dict[str, tuple[str, ...]]:
    imports: dict[str, tuple[str, ...]] = {}

    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.name] = ()
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports[node.module] = tuple(alias.name for alias in node.names)

    return imports


def _public_function_names_from_path(path: Path) -> list[str]:
    tree = _tree_from_path(path)

    if not isinstance(tree, ast.Module):
        return []

    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _call_names_from_path(path: Path) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree_from_path(path))
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _matching_imports(
    imports: set[str],
    forbidden_prefixes: tuple[str, ...],
) -> list[str]:
    return [
        module_name
        for module_name in sorted(imports)
        if _matches_forbidden_prefix(module_name, forbidden_prefixes)
    ]


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _forbidden_source_token_matches(
    source: str,
    tokens: tuple[str, ...],
) -> list[str]:
    matches: list[str] = []

    for token in tokens:
        if _source_contains_token(source, token):
            matches.append(token)

    return matches


def _source_contains_token(source: str, token: str) -> bool:
    lowered_token = token.lower()

    for line in source.splitlines():
        lowered_line = line.lower()
        if _line_contains_token(lowered_line, lowered_token):
            return True

    return False


def _line_contains_token(lowered_line: str, token: str) -> bool:
    if re.match(r"^[a-z0-9_]+$", token):
        return re.search(
            rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])",
            lowered_line,
        ) is not None

    return token in lowered_line


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value
