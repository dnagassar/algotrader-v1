from __future__ import annotations

import ast
import inspect
import json
import re
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from algotrader.errors import ValidationError
from algotrader.research import advisory_operating_brief_section as section_module
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_diagnostic_issue import (
    build_advisory_operating_brief_diagnostic_issues,
)
from algotrader.research.advisory_operating_brief_section import (
    AdvisoryOperatingBriefSection,
    build_advisory_operating_brief_sections,
)
from algotrader.research.sma_research_summary_observation import (
    build_sma_research_summary_observation,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation,
)
from tests.fixtures.sma_research_observation import (
    build_synthetic_sma_research_observation,
)


EXPECTED_KEYS = [
    "section_key",
    "section_title",
    "section_state",
    "source_branches",
    "item_count",
    "diagnostic_messages",
    "limitations",
]
EXPECTED_SECTION_KEYS = (
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "risk_authority_briefs",
    "research_queue_briefs",
    "sma_research_observation_briefs",
    "research_return_observation_briefs",
    "research_return_summary_observation_briefs",
    "sma_research_summary_observations",
    "research_data_source_readiness",
    "research_data_source_readiness_summaries",
    "diagnostic_issues",
)
EXPECTED_SECTION_TITLES = {
    "candidate_research_briefs": "Candidate research brief metadata",
    "strategy_eligibility_briefs": "Strategy eligibility brief metadata",
    "risk_authority_briefs": "Risk authority brief metadata",
    "research_queue_briefs": "Research queue brief metadata",
    "sma_research_observation_briefs": "SMA research observation brief metadata",
    "research_return_observation_briefs": (
        "Research return observation brief metadata"
    ),
    "research_return_summary_observation_briefs": (
        "Research return summary observation brief metadata"
    ),
    "sma_research_summary_observations": (
        "SMA research summary observation metadata"
    ),
    "research_data_source_readiness": (
        "Research data-source readiness diagnostic metadata"
    ),
    "research_data_source_readiness_summaries": (
        "Research data-source readiness summary diagnostic metadata"
    ),
    "diagnostic_issues": "Diagnostic issue metadata",
}
EXPECTED_DEFAULT_LIMITATIONS = (
    "metadata-only section record for present advisory content branch",
    "describes branch presence and item count only",
    "does not render content or mutate advisory content bundles",
)
EXPECTED_DIAGNOSTIC_LIMITATIONS = (
    *EXPECTED_DEFAULT_LIMITATIONS,
    "diagnostic messages are copied from existing issue records",
)
EXPECTED_PRODUCTION_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief_content_bundle",
}
FORBIDDEN_FIELD_TERMS = (
    "broker",
    "order",
    "fill",
    "portfolio",
    "backtest",
    "runtime",
    "vendor",
    "network",
    "credential",
)
FORBIDDEN_OUTPUT_TERMS = (
    "approval",
    "approved",
    "authorization",
    "authorized",
    "trade",
    "trading",
    "ranking",
    "scoring",
    "recommendation",
    "allocation",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.agent",
    "algotrader.agents",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.cli",
    "algotrader.config",
    "algotrader.core.config",
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
    "google.generativeai",
    "httpx",
    "joblib",
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
    "subprocess",
    "tensorflow",
    "torch",
    "urllib",
    "vectorbt",
    "yfinance",
)
FORBIDDEN_PRODUCTION_CALL_NAMES = {
    "__import__",
    "add_argument",
    "add_parser",
    "client",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "eval",
    "exec",
    "from_dict",
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
    "parse_args",
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "requests.get",
    "save",
    "socket.create_connection",
    "socket.socket",
    "sorted",
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
FORBIDDEN_PRODUCTION_SOURCE_TOKENS = (
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


def test_builds_sections_from_existing_synthetic_bundle() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    sections = build_advisory_operating_brief_sections(bundle)

    assert tuple(type(section) for section in sections) == (
        AdvisoryOperatingBriefSection,
        AdvisoryOperatingBriefSection,
    )
    assert tuple(section.section_key for section in sections) == (
        "candidate_research_briefs",
        "strategy_eligibility_briefs",
    )
    assert tuple(section.item_count for section in sections) == (1, 1)
    assert sections[0].limitations == EXPECTED_DEFAULT_LIMITATIONS
    assert sections[1].limitations == EXPECTED_DEFAULT_LIMITATIONS


def test_section_ordering_is_deterministic_for_all_present_branches() -> None:
    first = build_advisory_operating_brief_sections(_complete_bundle())
    second = build_advisory_operating_brief_sections(_complete_bundle())

    assert tuple(section.section_key for section in first) == EXPECTED_SECTION_KEYS
    assert tuple(section.section_key for section in first) == tuple(
        section.section_key for section in second
    )
    assert tuple(section.to_dict() for section in first) == tuple(
        section.to_dict() for section in second
    )


def test_sections_describe_branch_presence_and_counts_only() -> None:
    bundle = _complete_bundle()
    sections = build_advisory_operating_brief_sections(bundle)

    for section in sections:
        branch_items = getattr(bundle, section.section_key)
        payload = section.to_dict()
        assert section.source_branches == (section.section_key,)
        assert section.section_title == EXPECTED_SECTION_TITLES[section.section_key]
        assert section.section_state == "candidate_only"
        assert section.item_count == len(branch_items)
        assert list(payload) == EXPECTED_KEYS
        assert "items" not in payload
        assert "source_bundle" not in payload
        assert "branch_objects" not in payload
        assert all(type(value) is not dict for value in payload.values())


def test_diagnostic_issue_counts_and_messages_are_diagnostic_only() -> None:
    source = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    issues = build_advisory_operating_brief_diagnostic_issues(source)
    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        diagnostic_issues=issues,
    )

    sections = build_advisory_operating_brief_sections(bundle)
    diagnostic_section = sections[-1]
    diagnostic_text = _compact_sorted_json(diagnostic_section.to_dict()).lower()

    assert diagnostic_section.section_key == "diagnostic_issues"
    assert diagnostic_section.item_count == 2
    assert diagnostic_section.diagnostic_messages == tuple(
        issue.diagnostic_message for issue in issues
    )
    assert diagnostic_section.limitations == EXPECTED_DIAGNOSTIC_LIMITATIONS
    assert _matching_terms(diagnostic_text, FORBIDDEN_OUTPUT_TERMS) == []


def test_section_records_are_frozen_slotted_and_have_pinned_fields() -> None:
    section = build_advisory_operating_brief_sections(
        build_synthetic_advisory_operating_brief_content_bundle()
    )[0]

    assert is_dataclass(AdvisoryOperatingBriefSection)
    assert AdvisoryOperatingBriefSection.__dataclass_params__.frozen is True
    assert hasattr(AdvisoryOperatingBriefSection, "__slots__")
    assert not hasattr(section, "__dict__")
    assert tuple(field.name for field in fields(AdvisoryOperatingBriefSection)) == (
        "section_key",
        "section_title",
        "section_state",
        "source_branches",
        "item_count",
        "diagnostic_messages",
        "limitations",
    )
    with pytest.raises(FrozenInstanceError):
        section.item_count = 2
    with pytest.raises((AttributeError, TypeError)):
        section.extra_field = "not allowed"


def test_to_dict_is_primitive_only_deterministic_and_copying() -> None:
    section = build_advisory_operating_brief_sections(_complete_bundle())[-1]

    first = section.to_dict()
    second = section.to_dict()

    assert list(first) == EXPECTED_KEYS
    assert first == second
    assert _primitive_only(first)
    assert json.loads(json.dumps(first, sort_keys=True)) == first
    assert first["source_branches"] is not second["source_branches"]
    assert first["diagnostic_messages"] is not second["diagnostic_messages"]
    assert first["limitations"] is not second["limitations"]

    first["source_branches"].append("mutated_copy")
    first["diagnostic_messages"].append("mutated copy")
    first["limitations"].append("mutated copy")
    assert second == section.to_dict()


def test_repeated_builds_are_equal() -> None:
    first_bundle = _complete_bundle()
    second_bundle = _complete_bundle()

    first = build_advisory_operating_brief_sections(first_bundle)
    second = build_advisory_operating_brief_sections(second_bundle)

    assert first == second
    assert first is not second
    assert tuple(section.to_dict() for section in first) == tuple(
        section.to_dict() for section in second
    )
    assert _compact_sorted_json([section.to_dict() for section in first]) == (
        _compact_sorted_json([section.to_dict() for section in second])
    )


def test_builder_does_not_mutate_source_bundle_or_branches() -> None:
    bundle = _complete_bundle()
    before_payload = bundle.to_dict()
    identity_snapshot = _identity_snapshot(bundle)

    sections = build_advisory_operating_brief_sections(bundle)
    section_payload = sections[-1].to_dict()
    section_payload["diagnostic_messages"].append("mutated copy")
    section_payload["limitations"].append("mutated copy")

    assert bundle.to_dict() == before_payload
    assert _identity_snapshot(bundle) == identity_snapshot


def test_subclasses_lookalikes_and_invalid_section_values_are_rejected() -> None:
    class BundleSubclass(AdvisoryOperatingBriefContentBundle):
        pass

    class BundleLookalike:
        candidate_research_briefs = ()
        strategy_eligibility_briefs = ()

    with pytest.raises(ValidationError, match="bundle"):
        build_advisory_operating_brief_sections(object.__new__(BundleSubclass))
    with pytest.raises(ValidationError, match="bundle"):
        build_advisory_operating_brief_sections(BundleLookalike())

    payload = _valid_section_payload()
    for field_name, value in (
        ("section_key", "unsupported_branch"),
        ("section_title", "Other metadata"),
        ("section_state", "approved"),
        ("source_branches", ()),
        ("source_branches", ("candidate_research_briefs", "diagnostic_issues")),
        ("item_count", 0),
        ("item_count", True),
        ("diagnostic_messages", ("message not allowed",)),
        ("limitations", [""]),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            AdvisoryOperatingBriefSection(**mutated)


def test_no_runtime_vendor_or_trading_fields_are_introduced() -> None:
    payload = [
        section.to_dict()
        for section in build_advisory_operating_brief_sections(_complete_bundle())
    ]
    field_names = _payload_keys(payload)

    assert _matching_field_terms(field_names, FORBIDDEN_FIELD_TERMS) == []
    assert "wrapper" not in field_names
    assert "raw_payload" not in field_names


def test_forbidden_approval_trading_ranking_and_scoring_vocabulary_is_absent() -> (
    None
):
    payload = [
        section.to_dict()
        for section in build_advisory_operating_brief_sections(_complete_bundle())
    ]
    text = _compact_sorted_json(payload).lower()

    assert _matching_terms(text, FORBIDDEN_OUTPUT_TERMS) == []


def test_section_module_has_no_runtime_vendor_or_trading_dependencies() -> None:
    imports = _import_references()
    call_names = _call_names()
    source = _source_text()

    assert imports == EXPECTED_PRODUCTION_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(FORBIDDEN_PRODUCTION_CALL_NAMES)
    assert _forbidden_source_token_matches(
        source,
        FORBIDDEN_PRODUCTION_SOURCE_TOKENS,
    ) == []


def test_module_is_not_exposed_through_research_package() -> None:
    import algotrader.research as research_package

    assert not hasattr(research_package, "AdvisoryOperatingBriefSection")
    assert not hasattr(research_package, "build_advisory_operating_brief_sections")


def _complete_bundle() -> AdvisoryOperatingBriefContentBundle:
    content = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation()
    )
    diagnostic_source = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    sma_summary = build_sma_research_summary_observation(
        (build_synthetic_sma_research_observation(),)
    )
    issues = build_advisory_operating_brief_diagnostic_issues(diagnostic_source)
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=content.candidate_research_briefs,
        strategy_eligibility_briefs=content.strategy_eligibility_briefs,
        risk_authority_briefs=content.risk_authority_briefs,
        research_queue_briefs=content.research_queue_briefs,
        sma_research_observation_briefs=content.sma_research_observation_briefs,
        research_return_observation_briefs=(
            content.research_return_observation_briefs
        ),
        research_return_summary_observation_briefs=(
            content.research_return_summary_observation_briefs
        ),
        sma_research_summary_observations=(sma_summary,),
        research_data_source_readiness=(
            diagnostic_source.research_data_source_readiness
        ),
        research_data_source_readiness_summaries=(
            diagnostic_source.research_data_source_readiness_summaries
        ),
        diagnostic_issues=issues,
    )


def _valid_section_payload() -> dict[str, object]:
    section = build_advisory_operating_brief_sections(
        build_synthetic_advisory_operating_brief_content_bundle()
    )[0]
    return {
        "section_key": section.section_key,
        "section_title": section.section_title,
        "section_state": section.section_state,
        "source_branches": section.source_branches,
        "item_count": section.item_count,
        "diagnostic_messages": section.diagnostic_messages,
        "limitations": section.limitations,
    }


def _identity_snapshot(
    bundle: AdvisoryOperatingBriefContentBundle,
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(id(item) for item in getattr(bundle, section_key))
        for section_key in EXPECTED_SECTION_KEYS
    )


def _compact_sorted_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


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


def _matching_field_terms(
    field_names: set[str],
    forbidden_terms: tuple[str, ...],
) -> list[str]:
    matches: list[str] = []
    for field_name in sorted(field_names):
        for term in forbidden_terms:
            if term in field_name.lower():
                matches.append(field_name)
                break

    return matches


def _matching_terms(text: str, forbidden_terms: tuple[str, ...]) -> list[str]:
    return [term for term in forbidden_terms if term in text]


def _source_text() -> str:
    return inspect.getsource(section_module)


def _tree() -> ast.AST:
    return ast.parse(_source_text())


def _import_references() -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


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
    forbidden_terms: tuple[str, ...],
) -> list[str]:
    return [
        term for term in forbidden_terms if _source_contains_token(source, term)
    ]


def _source_contains_token(source: str, token: str) -> bool:
    lowered_token = token.lower()

    for line in source.splitlines():
        if _line_contains_token(line.lower(), lowered_token):
            return True

    return False


def _line_contains_token(lowered_line: str, token: str) -> bool:
    if re.match(r"^[a-z0-9_]+$", token):
        return re.search(
            rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])",
            lowered_line,
        ) is not None

    return token in lowered_line
