from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from algotrader.research.advisory_operating_brief_content_bundle import (
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_section import (
    AdvisoryOperatingBriefSection,
    build_advisory_operating_brief_sections,
)
from tests.fixtures import advisory_operating_brief_section as fixture_module
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary,
)
from tests.fixtures.advisory_operating_brief_diagnostic_issue import (
    build_synthetic_advisory_operating_brief_diagnostic_issues,
)
from tests.fixtures.advisory_operating_brief_section import (
    build_synthetic_advisory_operating_brief_sections,
    expected_synthetic_advisory_operating_brief_section_dicts,
    expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts,
    expected_synthetic_advisory_operating_brief_section_export_snapshot_json,
    expected_synthetic_advisory_operating_brief_section_json,
)


FIXTURE_PATH = Path("tests/fixtures/advisory_operating_brief_section.py")
EXPECTED_SECTION_KEYS = [
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "research_data_source_readiness",
    "research_data_source_readiness_summaries",
    "diagnostic_issues",
]
EXPECTED_ITEM_COUNTS = [1, 1, 1, 1, 2]
EXPECTED_SECTION_PAYLOAD_KEYS = [
    "section_key",
    "section_title",
    "section_state",
    "source_branches",
    "item_count",
    "diagnostic_messages",
    "limitations",
]
EXPECTED_SECTION_TITLES = {
    "candidate_research_briefs": "Candidate research brief metadata",
    "strategy_eligibility_briefs": "Strategy eligibility brief metadata",
    "research_data_source_readiness": (
        "Research data-source readiness diagnostic metadata"
    ),
    "research_data_source_readiness_summaries": (
        "Research data-source readiness summary diagnostic metadata"
    ),
    "diagnostic_issues": "Diagnostic issue metadata",
}
EXPECTED_DIAGNOSTIC_MESSAGES = [
    "Readiness branch reports missing diagnostic controls.",
    "Readiness summary branch reports missing diagnostic controls.",
]
EXPECTED_DEFAULT_LIMITATIONS = [
    "metadata-only section record for present advisory content branch",
    "describes branch presence and item count only",
    "does not render content or mutate advisory content bundles",
]
EXPECTED_DIAGNOSTIC_LIMITATIONS = [
    *EXPECTED_DEFAULT_LIMITATIONS,
    "diagnostic messages are copied from existing issue records",
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
FORBIDDEN_BRANCHES = {
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
    "algotrader.research.advisory_operating_brief_content_bundle": (
        "build_advisory_operating_brief_content_bundle",
    ),
    "algotrader.research.advisory_operating_brief_section": (
        "AdvisoryOperatingBriefSection",
        "build_advisory_operating_brief_sections",
    ),
    "tests.fixtures.advisory_operating_brief_content_bundle": (
        "build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary",
    ),
    "tests.fixtures.advisory_operating_brief_diagnostic_issue": (
        "build_synthetic_advisory_operating_brief_diagnostic_issues",
    ),
}
EXPECTED_FIXTURE_CALLS = {
    "build_advisory_operating_brief_content_bundle",
    "build_advisory_operating_brief_sections",
    "build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary",
    "build_synthetic_advisory_operating_brief_sections",
    "build_synthetic_advisory_operating_brief_diagnostic_issues",
    "expected_synthetic_advisory_operating_brief_section_dicts",
    "expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts",
    "json.dumps",
    "section.to_dict",
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


def test_fixture_builds_deterministic_sections_from_synthetic_bundle() -> None:
    direct_sections = build_advisory_operating_brief_sections(
        _synthetic_section_source_bundle()
    )
    fixture_sections = build_synthetic_advisory_operating_brief_sections()

    assert fixture_sections == direct_sections
    assert tuple(type(section) for section in fixture_sections) == (
        AdvisoryOperatingBriefSection,
        AdvisoryOperatingBriefSection,
        AdvisoryOperatingBriefSection,
        AdvisoryOperatingBriefSection,
        AdvisoryOperatingBriefSection,
    )
    assert [section.section_key for section in fixture_sections] == (
        EXPECTED_SECTION_KEYS
    )
    assert [section.item_count for section in fixture_sections] == (
        EXPECTED_ITEM_COUNTS
    )
    assert fixture_sections[-1].diagnostic_messages == tuple(
        EXPECTED_DIAGNOSTIC_MESSAGES
    )


def test_snapshot_dicts_equal_each_section_to_dict_payload() -> None:
    sections = build_synthetic_advisory_operating_brief_sections()
    snapshot = expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()

    assert snapshot == [section.to_dict() for section in sections]
    assert snapshot == expected_synthetic_advisory_operating_brief_section_dicts()
    assert [list(section_payload) for section_payload in snapshot] == [
        EXPECTED_SECTION_PAYLOAD_KEYS,
        EXPECTED_SECTION_PAYLOAD_KEYS,
        EXPECTED_SECTION_PAYLOAD_KEYS,
        EXPECTED_SECTION_PAYLOAD_KEYS,
        EXPECTED_SECTION_PAYLOAD_KEYS,
    ]


def test_snapshot_json_is_compact_sorted_and_deterministic() -> None:
    payload = expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()
    first_json = expected_synthetic_advisory_operating_brief_section_export_snapshot_json()
    second_json = expected_synthetic_advisory_operating_brief_section_export_snapshot_json()
    expected_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    assert first_json == second_json == expected_json
    assert first_json == expected_synthetic_advisory_operating_brief_section_json()
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert json.loads(first_json) == payload
    assert "\n" not in first_json
    assert ": " not in first_json
    assert first_json != json.dumps(payload, sort_keys=True)


def test_snapshot_contains_expected_section_fields() -> None:
    snapshot = expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()

    assert len(snapshot) == 5
    assert [section["section_key"] for section in snapshot] == EXPECTED_SECTION_KEYS
    assert [section["section_title"] for section in snapshot] == [
        EXPECTED_SECTION_TITLES[section_key]
        for section_key in EXPECTED_SECTION_KEYS
    ]
    assert [section["section_state"] for section in snapshot] == [
        "candidate_only",
        "candidate_only",
        "candidate_only",
        "candidate_only",
        "candidate_only",
    ]
    assert [section["source_branches"] for section in snapshot] == [
        [section_key] for section_key in EXPECTED_SECTION_KEYS
    ]
    assert [section["item_count"] for section in snapshot] == EXPECTED_ITEM_COUNTS
    assert snapshot[-1]["diagnostic_messages"] == EXPECTED_DIAGNOSTIC_MESSAGES
    assert [section["diagnostic_messages"] for section in snapshot[:-1]] == [
        [],
        [],
        [],
        [],
    ]
    assert [section["limitations"] for section in snapshot[:-1]] == [
        EXPECTED_DEFAULT_LIMITATIONS,
        EXPECTED_DEFAULT_LIMITATIONS,
        EXPECTED_DEFAULT_LIMITATIONS,
        EXPECTED_DEFAULT_LIMITATIONS,
    ]
    assert snapshot[-1]["limitations"] == EXPECTED_DIAGNOSTIC_LIMITATIONS


def test_snapshot_preserves_present_branches_only_and_builder_order() -> None:
    snapshot = expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()
    snapshot_keys = [section["section_key"] for section in snapshot]

    assert snapshot_keys == EXPECTED_SECTION_KEYS
    assert set(snapshot_keys).isdisjoint(FORBIDDEN_BRANCHES)
    assert "severity" not in _payload_keys(snapshot)
    assert "priority" not in _payload_keys(snapshot)
    assert "rank" not in _payload_keys(snapshot)


def test_snapshot_excludes_raw_timestamps_digest_wrappers_and_operating_fields() -> (
    None
):
    snapshot = expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()
    snapshot_keys = _payload_keys(snapshot)
    snapshot_text = json.dumps(snapshot, sort_keys=True).lower()

    assert FORBIDDEN_SNAPSHOT_KEYS.isdisjoint(snapshot_keys)
    assert all(term not in snapshot_text for term in FORBIDDEN_TEXT_TERMS)


def test_repeated_fixture_builds_and_snapshots_are_equal() -> None:
    first_sections = build_synthetic_advisory_operating_brief_sections()
    second_sections = build_synthetic_advisory_operating_brief_sections()
    first_snapshot = expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()
    second_snapshot = (
        expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()
    )

    assert first_sections == second_sections
    assert first_sections is not second_sections
    assert first_snapshot == second_snapshot
    assert first_snapshot is not second_snapshot


def test_snapshot_payloads_are_primitive_round_trippable_fresh_copies() -> None:
    first = expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()
    second = expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()
    compact_json = expected_synthetic_advisory_operating_brief_section_export_snapshot_json()

    assert _primitive_only(first)
    assert json.loads(compact_json) == first
    assert first[0]["source_branches"] is not second[0]["source_branches"]
    assert first[0]["limitations"] is not second[0]["limitations"]
    assert first[-1]["diagnostic_messages"] is not second[-1]["diagnostic_messages"]

    first[0]["source_branches"].append("mutated primitive copy")
    first[0]["limitations"].append("mutated primitive copy")
    first[-1]["diagnostic_messages"].append("mutated primitive copy")

    assert second[0]["source_branches"] == [EXPECTED_SECTION_KEYS[0]]
    assert second[0]["limitations"] == EXPECTED_DEFAULT_LIMITATIONS
    assert second[-1]["diagnostic_messages"] == EXPECTED_DIAGNOSTIC_MESSAGES


def test_fixture_module_imports_are_test_only_and_dependency_bounded() -> None:
    imports = _import_details_from_path(FIXTURE_PATH)

    assert fixture_module.__all__ == [
        "build_synthetic_advisory_operating_brief_sections",
        "expected_synthetic_advisory_operating_brief_section_dicts",
        "expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts",
        "expected_synthetic_advisory_operating_brief_section_export_snapshot_json",
        "expected_synthetic_advisory_operating_brief_section_json",
    ]
    assert _public_function_names_from_path(FIXTURE_PATH) == [
        "build_synthetic_advisory_operating_brief_sections",
        "expected_synthetic_advisory_operating_brief_section_dicts",
        "expected_synthetic_advisory_operating_brief_section_json",
        "expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts",
        "expected_synthetic_advisory_operating_brief_section_export_snapshot_json",
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


def _synthetic_section_source_bundle() -> object:
    source = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    issues = build_synthetic_advisory_operating_brief_diagnostic_issues()

    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        research_data_source_readiness=source.research_data_source_readiness,
        research_data_source_readiness_summaries=(
            source.research_data_source_readiness_summaries
        ),
        diagnostic_issues=issues,
    )


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
