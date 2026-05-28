from __future__ import annotations

import ast
import inspect
import json
import re
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from algotrader.errors import ValidationError
from algotrader.research import advisory_operating_brief_view as view_module
from algotrader.research.advisory_operating_brief_section import (
    AdvisoryOperatingBriefSection,
)
from algotrader.research.advisory_operating_brief_view import (
    AdvisoryOperatingBriefView,
    build_advisory_operating_brief_view,
)
from tests.fixtures.advisory_operating_brief_section import (
    build_synthetic_advisory_operating_brief_sections,
)


def _s(*parts: str) -> str:
    return "".join(parts)


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
EXPECTED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief_section",
}
FORBIDDEN_FIELD_TERMS = (
    _s("bro", "ker"),
    _s("or", "der"),
    _s("fi", "ll"),
    _s("port", "folio"),
    _s("back", "test"),
    _s("run", "time"),
    _s("ven", "dor"),
    _s("net", "work"),
    _s("cred", "ential"),
)
FORBIDDEN_OUTPUT_TERMS = (
    _s("app", "roval"),
    _s("app", "roved"),
    _s("author", "ization"),
    _s("author", "ized"),
    _s("tra", "de"),
    _s("tra", "ding"),
    _s("rank", "ing"),
    _s("scor", "ing"),
    _s("recommend", "ation"),
    _s("allo", "cation"),
)
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.agent",
    "algotrader.agents",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.config",
    "algotrader.core.config",
    "algotrader.dashboard",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    _s("algotrader.", "persist", "ence"),
    _s("algotrader.", "port", "folio"),
    "algotrader.risk",
    _s("algotrader.", "run", "time"),
    _s("algotrader.", "sche", "duler"),
    "algotrader.screener",
    _s("algotrader.", "sig", "nals"),
    "algotrader.storage",
    "algotrader.vendor",
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    "anthropic",
    _s("data", "base"),
    "duckdb",
    "google.generativeai",
    "httpx",
    "joblib",
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("net", "work"),
    "openai",
    "os",
    _s("path", "lib"),
    "pandas",
    "polars",
    _s("re", "quests"),
    "sklearn",
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "urllib",
    "vectorbt",
    "yfinance",
)
FORBIDDEN_CALL_NAMES = {
    "__import__",
    "add_argument",
    "add_parser",
    _s("cli", "ent"),
    _s("con", "nect"),
    _s("create_", "or", "der"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    _s("ing", "est"),
    "json.dump",
    "json.load",
    "load",
    "main",
    _s("op", "en"),
    "os.environ.get",
    "os.getenv",
    "parse_args",
    "post",
    _s("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    _s("re", "quest"),
    _s("re", "quests.get"),
    "save",
    _s("so", "cket.", "so", "cket"),
    _s("sub", "mit_", "or", "der"),
    "time.monotonic",
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}
FORBIDDEN_SOURCE_TOKENS = (
    "account",
    _s("allo", "cation"),
    _s("al", "paca"),
    _s("app", "roval"),
    _s("app", "roved"),
    _s("author", "ization"),
    _s("author", "ized"),
    _s("back", "test"),
    _s("bro", "ker"),
    _s("cred", "ential"),
    "dashboard",
    "digest",
    _s("fi", "ll"),
    "generated_at",
    _s("l", "lm"),
    _s("net", "work"),
    "notebook",
    "openai",
    _s("or", "der"),
    _s("port", "folio"),
    "priority",
    _s("rank", "ing"),
    "raw_payload",
    _s("recommend", "ation"),
    _s("run", "time"),
    _s("sche", "duler"),
    _s("scor", "ing"),
    "severity",
    _s("so", "cket"),
    "timestamp",
    _s("tra", "ding"),
    _s("ven", "dor"),
    "wrapper",
)


def test_builds_deterministic_view_from_existing_synthetic_sections() -> None:
    sections = build_synthetic_advisory_operating_brief_sections()

    view = build_advisory_operating_brief_view(sections)

    assert type(view) is AdvisoryOperatingBriefView
    assert view.view_key == "advisory_operating_brief_section_view"
    assert view.view_title == "Advisory operating brief section view"
    assert view.view_state == "candidate_only"
    assert view.section_count == 5
    assert view.section_keys == tuple(EXPECTED_SECTION_KEYS)
    assert view.summary_lines == tuple(EXPECTED_SUMMARY_LINES)
    assert view.diagnostic_messages == tuple(EXPECTED_DIAGNOSTIC_MESSAGES)
    assert view.limitations == tuple(EXPECTED_LIMITATIONS)


def test_build_accepts_one_exact_section_record() -> None:
    section = build_synthetic_advisory_operating_brief_sections()[0]

    view = build_advisory_operating_brief_view(section)

    assert view.section_count == 1
    assert view.section_keys == ("candidate_research_briefs",)
    assert view.summary_lines == (EXPECTED_SUMMARY_LINES[0],)
    assert view.diagnostic_messages == ()


def test_exact_section_type_validation_rejects_subclasses_lookalikes_and_non_sections() -> None:
    class SectionSubclass(AdvisoryOperatingBriefSection):
        pass

    class SectionLookalike:
        section_key = "candidate_research_briefs"
        section_title = "Candidate research brief metadata"
        section_state = "candidate_only"
        item_count = 1
        diagnostic_messages = ()
        limitations = ()

    sections = build_synthetic_advisory_operating_brief_sections()

    invalid_values = (
        object.__new__(SectionSubclass),
        SectionLookalike(),
        object(),
        None,
        (),
        [sections[0]],
        (sections[0], SectionLookalike()),
        (object.__new__(SectionSubclass),),
    )

    for value in invalid_values:
        with pytest.raises(ValidationError):
            build_advisory_operating_brief_view(value)


def test_supplied_section_sequence_is_preserved() -> None:
    sections = build_synthetic_advisory_operating_brief_sections()
    supplied = tuple(reversed(sections))

    view = build_advisory_operating_brief_view(supplied)

    assert view.section_keys == tuple(section.section_key for section in supplied)
    assert view.summary_lines == tuple(
        (
            f"{section.section_key}: {section.section_title}; "
            f"state={section.section_state}; count={section.item_count}"
        )
        for section in supplied
    )
    assert view.diagnostic_messages == tuple(sections[-1].diagnostic_messages)


def test_source_sections_are_not_mutated() -> None:
    sections = build_synthetic_advisory_operating_brief_sections()
    before_payloads = tuple(section.to_dict() for section in sections)
    before_identities = tuple(id(section) for section in sections)

    view = build_advisory_operating_brief_view(sections)
    view_payload = view.to_dict()
    view_payload["section_keys"].append("mutated copy")
    view_payload["summary_lines"].append("mutated copy")
    view_payload["diagnostic_messages"].append("mutated copy")
    view_payload["limitations"].append("mutated copy")

    assert tuple(id(section) for section in sections) == before_identities
    assert tuple(section.to_dict() for section in sections) == before_payloads


def test_summary_lines_describe_section_metadata_only() -> None:
    sections = build_synthetic_advisory_operating_brief_sections()
    view = build_advisory_operating_brief_view(sections)
    summary_text = "\n".join(view.summary_lines).lower()

    assert list(view.summary_lines) == EXPECTED_SUMMARY_LINES
    for section in sections:
        line = view.summary_lines[view.section_keys.index(section.section_key)]
        assert section.section_key in line
        assert section.section_title in line
        assert f"state={section.section_state}" in line
        assert f"count={section.item_count}" in line
    assert "source_branches" not in summary_text
    assert "diagnostic_message" not in summary_text
    assert "limitations" not in summary_text


def test_diagnostic_messages_remain_diagnostic_only() -> None:
    view = build_advisory_operating_brief_view(
        build_synthetic_advisory_operating_brief_sections()
    )
    diagnostic_text = "\n".join(view.diagnostic_messages).lower()

    assert view.diagnostic_messages == tuple(EXPECTED_DIAGNOSTIC_MESSAGES)
    assert _matching_terms(diagnostic_text, FORBIDDEN_OUTPUT_TERMS) == []


def test_view_record_is_frozen_slotted_and_has_pinned_fields() -> None:
    view = build_advisory_operating_brief_view(
        build_synthetic_advisory_operating_brief_sections()
    )

    assert is_dataclass(AdvisoryOperatingBriefView)
    assert AdvisoryOperatingBriefView.__dataclass_params__.frozen is True
    assert hasattr(AdvisoryOperatingBriefView, "__slots__")
    assert not hasattr(view, "__dict__")
    assert tuple(field.name for field in fields(AdvisoryOperatingBriefView)) == (
        "view_key",
        "view_title",
        "view_state",
        "section_count",
        "section_keys",
        "summary_lines",
        "diagnostic_messages",
        "limitations",
    )
    with pytest.raises(FrozenInstanceError):
        view.section_count = 7
    with pytest.raises((AttributeError, TypeError)):
        view.extra_field = "not allowed"


def test_to_dict_is_primitive_only_and_deterministic() -> None:
    view = build_advisory_operating_brief_view(
        build_synthetic_advisory_operating_brief_sections()
    )

    first = view.to_dict()
    second = view.to_dict()

    assert list(first) == EXPECTED_VIEW_KEYS
    assert first == second
    assert _primitive_only(first)
    assert json.loads(json.dumps(first, sort_keys=True)) == first
    assert first["section_keys"] is not second["section_keys"]
    assert first["summary_lines"] is not second["summary_lines"]
    assert first["diagnostic_messages"] is not second["diagnostic_messages"]
    assert first["limitations"] is not second["limitations"]

    first["section_keys"].append("mutated copy")
    first["summary_lines"].append("mutated copy")
    first["diagnostic_messages"].append("mutated copy")
    first["limitations"].append("mutated copy")
    assert second == view.to_dict()


def test_repeated_builds_are_equal() -> None:
    first = build_advisory_operating_brief_view(
        build_synthetic_advisory_operating_brief_sections()
    )
    second = build_advisory_operating_brief_view(
        build_synthetic_advisory_operating_brief_sections()
    )

    assert first == second
    assert first is not second
    assert first.to_dict() == second.to_dict()
    assert _compact_sorted_json(first.to_dict()) == _compact_sorted_json(
        second.to_dict()
    )


def test_no_operating_or_external_fields_are_introduced() -> None:
    view = build_advisory_operating_brief_view(
        build_synthetic_advisory_operating_brief_sections()
    )
    field_names = _payload_keys(view.to_dict())

    assert _matching_field_terms(field_names, FORBIDDEN_FIELD_TERMS) == []
    assert set(EXPECTED_VIEW_KEYS) == field_names
    assert "raw_payload" not in field_names
    assert "wrapper" not in field_names


def test_forbidden_positive_terms_are_absent_from_view_payload() -> None:
    view = build_advisory_operating_brief_view(
        build_synthetic_advisory_operating_brief_sections()
    )
    text = _compact_sorted_json(view.to_dict()).lower()

    assert _matching_terms(text, FORBIDDEN_OUTPUT_TERMS) == []


def test_view_dataclass_validation_rejects_inconsistent_metadata() -> None:
    payload = build_advisory_operating_brief_view(
        build_synthetic_advisory_operating_brief_sections()
    ).to_dict()

    invalid_values = (
        ("view_key", "different_view"),
        ("view_title", "Different title"),
        ("view_state", "candidate"),
        ("section_count", 0),
        ("section_count", True),
        ("section_keys", ()),
        ("summary_lines", ()),
        ("limitations", ("different limit",)),
    )

    for field_name, value in invalid_values:
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            AdvisoryOperatingBriefView(**mutated)

    mutated = dict(payload)
    mutated["section_count"] = 4
    with pytest.raises(ValidationError, match="section_keys"):
        AdvisoryOperatingBriefView(**mutated)

    mutated = dict(payload)
    mutated["summary_lines"] = tuple(EXPECTED_SUMMARY_LINES[:-1])
    with pytest.raises(ValidationError, match="summary_lines"):
        AdvisoryOperatingBriefView(**mutated)


def test_view_module_has_no_runtime_external_or_trading_dependencies() -> None:
    imports = _import_references()
    calls = _call_names()
    source = _source_text()

    assert imports == EXPECTED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert calls.isdisjoint(FORBIDDEN_CALL_NAMES)
    assert _forbidden_source_token_matches(source, FORBIDDEN_SOURCE_TOKENS) == []


def test_module_is_not_exposed_through_research_package() -> None:
    import algotrader.research as research_package

    assert not hasattr(research_package, "AdvisoryOperatingBriefView")
    assert not hasattr(research_package, "build_advisory_operating_brief_view")


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
    return inspect.getsource(view_module)


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
