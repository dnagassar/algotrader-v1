from __future__ import annotations

import ast
import inspect
import re
import sys

from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_RENDERED_LINES = (
    "Advisory Operating Brief Content Bundle",
    "bundle_type: advisory_operating_brief_content_bundle",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "title: Advisory operating brief content bundle metadata",
    (
        "summary: Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 12 limitation(s), and 25 non-claim(s)."
    ),
    "candidate_research_brief_count: 1",
    "strategy_eligibility_brief_count: 1",
    "",
    "Candidate Research Briefs",
    "",
    "Candidate Research Brief 1",
    "brief_type: candidate_research_brief",
    "status: candidate_only",
    "title: Candidate research brief metadata",
    "section_count: 1",
    "Sections",
    "",
    "Candidate Research Brief 1 Section 1",
    "section_type: candidate_research_results",
    "status: candidate_only",
    "title: Candidate research results metadata",
    "item_count: 1",
    "Items",
    "",
    "Candidate Research Brief 1 Section 1 Item 1",
    "item_type: candidate_research_result",
    "status: candidate_only",
    (
        "headline: Candidate research result metadata for "
        "synthetic_return_input_snapshot_fixture_001"
    ),
    "summary_points:",
    "- package snapshot id: synthetic_return_input_snapshot_fixture_001",
    (
        "- package fingerprint: "
        "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
    ),
    "- result manifest fixture id: synthetic_return_input_snapshot_fixture_001",
    (
        "- result manifest checksum: "
        "sha256:07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
    ),
    (
        "package_fingerprint: "
        "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
    ),
    "package_snapshot_id: synthetic_return_input_snapshot_fixture_001",
    "result_snapshot_manifest_fixture_id: synthetic_return_input_snapshot_fixture_001",
    (
        "result_snapshot_manifest_checksum: "
        "sha256:07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
    ),
    "",
    "Strategy Eligibility Briefs",
    "",
    "Strategy Eligibility Brief 1",
    "brief_type: strategy_eligibility_brief",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "title: Strategy eligibility brief metadata",
    (
        "summary: Advisory brief contains 1 strategy eligibility section(s), "
        "1 candidate item(s), 3 limitation(s), and 9 non-claim(s)."
    ),
    "section_count: 1",
    "Sections",
    "",
    "Strategy Eligibility Brief 1 Section 1",
    "section_type: strategy_eligibility_brief_section",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "title: Strategy eligibility metadata: research_only",
    (
        "summary: Advisory section contains 1 candidate eligibility item(s) "
        "across 1 strategy id(s), state(s): research_only, with 3 limitation(s) "
        "and 9 non-claim(s)."
    ),
    "item_count: 1",
    "Items",
    "",
    "Strategy Eligibility Brief 1 Section 1 Item 1",
    "item_type: strategy_eligibility_brief_item",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "strategy_id: synthetic-strategy-eligibility-001",
    "strategy_name: Synthetic strategy eligibility research fixture",
    "eligibility_state: research_only",
    "headline: Advisory eligibility metadata: research_only.",
    (
        "summary: Candidate metadata records research_only with 2 reason(s), "
        "3 limitation(s), 9 non-claim(s), 2 evidence reference(s), "
        "2 blocker(s), and 2 required next step(s)."
    ),
    "reasons:",
    "- synthetic strategy metadata is scoped to research review",
    "- eligibility status is provided for advisory composition tests",
    "evidence_refs:",
    "- synthetic-evidence-ref-001",
    "- synthetic-advisory-metadata-ref-001",
    "blockers:",
    "- validation review has not been completed",
    "- readiness review has not been completed",
    "required_next_steps:",
    "- complete independent methodology review before any readiness claim",
    "- collect validation evidence before any approval claim",
    "limitations:",
    "- synthetic metadata only",
    "- no profitability evidence is represented",
    "- no approval or readiness decision is represented",
    "non_claims:",
    "- not validation",
    "- not paper readiness",
    "- not live readiness",
    "- not a trading recommendation",
    "- not allocation authority",
    "- not order authority",
    "- not profitability evidence",
    "- not approval",
    "- not capital authority",
    "source_status:",
    "source_status.eligibility_type: strategy_eligibility_status",
    "source_status.authority: advisory_only",
    "source_status.capital_authority: False",
    "",
    "Limitations",
    "- metadata-only brief for existing candidate research brief sections",
    "- does not create research, compute metrics, or mutate section payloads",
    "- advisory container for future queue and brief surfaces only",
    "- metadata-only section for existing candidate brief items",
    "- does not create research, compute metrics, or mutate item payloads",
    "- advisory grouping for future queue and brief surfaces only",
    "- metadata-only dossier for an already prepared package and matching result",
    "- does not run research, fetch inputs, compute metrics, or mutate payloads",
    "- advisory candidate summary for future queue and brief surfaces only",
    "- synthetic metadata only",
    "- no profitability evidence is represented",
    "- no approval or readiness decision is represented",
    "",
    "Non-Claims",
    "- not source approval",
    "- not data approval",
    "- not endpoint approval",
    "- not universe approval",
    "- not benchmark approval",
    "- not cash proxy approval",
    "- not methodology approval",
    "- not evidence approval",
    "- not return-construction approval",
    "- not no-lookahead approval",
    "- not strategy validation",
    "- not trading readiness",
    "- not production use",
    "- not broker or runtime use",
    "- not order generation",
    "- not portfolio or allocation authority",
    "- not validation",
    "- not paper readiness",
    "- not live readiness",
    "- not a trading recommendation",
    "- not allocation authority",
    "- not order authority",
    "- not profitability evidence",
    "- not approval",
    "- not capital authority",
)

_EXPECTED_RENDERED_TEXT = chr(10).join(_EXPECTED_RENDERED_LINES)
_EXPECTED_METADATA_PREFIX = _EXPECTED_RENDERED_LINES[:9]
_EXPECTED_ADVISORY_MARKERS = (
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "source_status.authority: advisory_only",
    "source_status.capital_authority: False",
)
_FORBIDDEN_ACTIONABLE_FIELD_NAMES = {
    "account",
    "accounts",
    _s("app", "roved"),
    "buy",
    "sell",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    "paper_eligible",
    _s("allo", "cation"),
    _s("allo", "cations"),
    _s("allo", "cation_authority"),
    _s("or", "der"),
    _s("or", "ders"),
    _s("or", "der_authority"),
    _s("port", "folio"),
    _s("port", "folios"),
    _s("tra", "ding_authority"),
    "trading_ready",
}
_AUTHORITY_PRESENTATION_TERMS = (
    _s("app", "roval"),
    _s("app", "roved"),
    "paper readiness",
    "live readiness",
    "readiness",
    _s("reco", "mmendation"),
    _s("allo", "cation authority"),
    _s("or", "der authority"),
    _s("tra", "ding authority"),
    _s("tra", "ding readiness"),
    "paper_eligible",
    "live_probe_eligible",
    "live_authorized",
    "trading_ready",
    "buy",
    "sell",
    "hold",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "ast",
    "inspect",
    "re",
    "sys",
    "algotrader.research.advisory_operating_brief_content_bundle_renderer",
    "tests.fixtures.advisory_operating_brief_content_bundle",
}
_LEGACY_OPERATING_BRIEF_MODULES = (
    "algotrader.cli",
    "algotrader.research.advisory_operating_brief",
    "algotrader.research.advisory_operating_brief_renderer",
    "algotrader.research.advisory_operating_brief_export",
    "algotrader.research.advisory_operating_brief_cli",
    "algotrader.research.advisory_operating_brief_review",
    "tests.fixtures.advisory_operating_brief",
    "tests.unit.test_advisory_operating_brief_renderer_regression",
    "tests.unit.test_advisory_operating_brief_export_regression",
    "tests.unit.test_advisory_operating_brief_cli_regression",
)
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    *_LEGACY_OPERATING_BRIEF_MODULES,
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
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
    "algotrader.scheduler",
    "algotrader.screener",
    _s("algotrader.", "sig", "nals"),
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    "anthropic",
    _s("data", "base"),
    "duckdb",
    _s("ht", "tp"),
    "httpx",
    "ipynb",
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("mas", "sive"),
    _s("net", "work"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    _s("poly", "gon"),
    _s("poly", "gon_a", "pi_client"),
    _s("quant", "connect"),
    _s("re", "quests"),
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "urllib",
    "vectorbt",
    "xgboost",
    _s("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "build_parser",
    "build_synthetic_advisory_operating_brief",
    _s("cli", "ent"),
    _s("con", "nect"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "export_advisory_operating_brief",
    "exists",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    "importlib.import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "load",
    "loads",
    "main",
    "mkdir",
    _s("op", "en"),
    "os.environ.get",
    "os.getenv",
    "post",
    "print",
    _s("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    "render_advisory_operating_brief_text",
    _s("re", "quest"),
    _s("re", "quests.get"),
    "rglob",
    "save",
    _s("so", "cket.socket"),
    "stat",
    _s("sub", "mit_", "or", "der"),
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}


def test_phase_162_fixture_renders_exact_pinned_text_tuple() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert rendered == _EXPECTED_RENDERED_TEXT
    assert tuple(rendered.splitlines()) == _EXPECTED_RENDERED_LINES


def test_repeated_rendering_is_byte_for_byte_identical() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    first = render_advisory_operating_brief_content_bundle_text(bundle)
    second = render_advisory_operating_brief_content_bundle_text(bundle)

    assert first == _EXPECTED_RENDERED_TEXT
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_rendering_does_not_mutate_source_bundle_to_dict_payload() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    before = bundle.to_dict()

    first = render_advisory_operating_brief_content_bundle_text(bundle)
    second = render_advisory_operating_brief_content_bundle_text(bundle)

    assert first == second == _EXPECTED_RENDERED_TEXT
    assert bundle.to_dict() == before


def test_branch_order_matches_phase_162_source_bundle_order() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    payload = bundle.to_dict()
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    candidate_payload = payload["candidate_research_briefs"][0]
    candidate_section = candidate_payload["sections"][0]
    candidate_item = candidate_section["items"][0]
    eligibility_payload = payload["strategy_eligibility_briefs"][0]
    eligibility_section = eligibility_payload["sections"][0]
    eligibility_item = eligibility_section["items"][0]

    _assert_line_order(
        rendered,
        (
            "Candidate Research Briefs",
            "Candidate Research Brief 1",
            f"title: {candidate_payload['title']}",
            "Candidate Research Brief 1 Section 1",
            f"title: {candidate_section['title']}",
            "Candidate Research Brief 1 Section 1 Item 1",
            f"headline: {candidate_item['headline']}",
            "Strategy Eligibility Briefs",
            "Strategy Eligibility Brief 1",
            f"title: {eligibility_payload['title']}",
            "Strategy Eligibility Brief 1 Section 1",
            f"title: {eligibility_section['title']}",
            "Strategy Eligibility Brief 1 Section 1 Item 1",
            f"strategy_id: {eligibility_item['strategy_id']}",
            f"eligibility_state: {eligibility_item['eligibility_state']}",
        ),
    )


def test_rendered_text_includes_required_advisory_content_markers() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    payload = bundle.to_dict()
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    lines = tuple(rendered.splitlines())
    candidate_item = payload["candidate_research_briefs"][0]["sections"][0]["items"][0]
    eligibility_item = payload["strategy_eligibility_briefs"][0]["sections"][0][
        "items"
    ][0]

    assert lines[:9] == _EXPECTED_METADATA_PREFIX
    assert "Candidate Research Briefs" in lines
    assert f"headline: {candidate_item['headline']}" in lines
    assert f"package_snapshot_id: {candidate_item['package_snapshot_id']}" in lines
    assert "Strategy Eligibility Briefs" in lines
    assert f"strategy_id: {eligibility_item['strategy_id']}" in lines
    assert f"eligibility_state: {eligibility_item['eligibility_state']}" in lines
    assert "Limitations" in lines
    assert "Non-Claims" in lines
    for marker in _EXPECTED_ADVISORY_MARKERS:
        assert marker in lines
    for value in payload["limitations"]:
        assert f"- {value}" in lines
    for value in payload["non_claims"]:
        assert f"- {value}" in lines
    for field_name in (
        "reasons",
        "evidence_refs",
        "blockers",
        "required_next_steps",
        "limitations",
        "non_claims",
    ):
        for value in eligibility_item[field_name]:
            assert f"- {value}" in lines


def test_rendered_text_has_no_actionable_authority_presentation() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    source_cautions = _source_caution_values(bundle.to_dict())
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    authority_lines = _authority_presentation_lines(rendered)

    assert authority_lines
    assert _rendered_field_names(rendered).isdisjoint(
        _FORBIDDEN_ACTIONABLE_FIELD_NAMES
    )
    for line in authority_lines:
        assert line.startswith("- ")
        assert line[2:] in source_cautions
    assert "paper_eligible" not in rendered
    assert "live_probe_eligible" not in rendered
    assert "live_authorized" not in rendered
    assert "trading_ready" not in rendered
    assert _legacy_operating_brief_markers(rendered) == ()


def test_regression_guard_is_test_only_and_isolated_from_legacy_chain() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def _assert_line_order(text: str, expected_values: tuple[str, ...]) -> None:
    previous_index = -1
    for value in expected_values:
        current_index = text.index(value)
        assert previous_index < current_index
        previous_index = current_index


def _rendered_field_names(text: str) -> set[str]:
    field_names: set[str] = set()
    for line in text.splitlines():
        if line.startswith("- ") or ":" not in line:
            continue
        field_names.add(line.split(":", maxsplit=1)[0])

    return field_names


def _authority_presentation_lines(text: str) -> tuple[str, ...]:
    return tuple(
        line
        for line in text.splitlines()
        if any(
            re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", line.lower())
            for term in _AUTHORITY_PRESENTATION_TERMS
        )
    )


def _source_caution_values(payload: object) -> set[str]:
    caution_fields = {
        "blockers",
        "limitations",
        "non_claims",
        "required_next_steps",
    }
    values: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in caution_fields and isinstance(value, list):
                values.update(item for item in value if isinstance(item, str))
            values.update(_source_caution_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.update(_source_caution_values(value))

    return values


def _legacy_operating_brief_markers(text: str) -> tuple[str, ...]:
    legacy_markers = (
        "operating_brief_type: advisory_operating_brief",
        "Candidate research operating brief metadata",
        "advisory-operating-brief-preview",
    )
    return tuple(marker for marker in legacy_markers if marker in text)


def _source_text() -> str:
    return inspect.getsource(sys.modules[__name__])


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
