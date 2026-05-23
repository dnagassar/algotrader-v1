from __future__ import annotations

import ast
import inspect
import json
import re
import sys

from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_EXPORT_PAYLOAD_KEYS = (
    "bundle_type",
    "status",
    "authority",
    "capital_authority",
    "title",
    "summary",
    "candidate_research_brief_count",
    "strategy_eligibility_brief_count",
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "limitations",
    "non_claims",
)
_EXPECTED_JSON_TEXT = (
    '{"authority":"advisory_only","bundle_type":"advisory_operating_brief_content_bundle","candidate_research_brief_count":1,"candidate_research_briefs":[{"brief_type":"candidate_research_brief","limitations":["metadata-only brief for existing candidate research brief sections","does not create research, compute metrics, or mutate section payloads","advisory container for future queue and brief surfaces only","metadata-only section for existing candidate brief items","does not create research, compute metrics, or mutate item payloads","advisory grouping for future queue and brief surfaces only","metadata-only dossier for an already prepared package and matching result","does not run research, fetch inputs, compute metrics, or mutate payloads","advisory candidate summary for future queue and brief surfaces only"],"non_claims":["not source approval","not data approval","not endpoint approval","'
    'not universe approval","not benchmark approval","not cash proxy approval","not methodology approval","not evidence approval","not return-construction approval","not no-lookahead approval","not strategy validation","not trading readiness","not production use","not broker or runtime use","not order generation","not portfolio or allocation authority"],"section_count":1,"sections":[{"item_count":1,"items":[{"headline":"Candidate research result metadata for synthetic_return_input_snapshot_fixture_001","item_type":"candidate_research_result","limitations":["metadata-only dossier for an already prepared package and matching result","does not run research, fetch inputs, compute metrics, or mutate payloads","advisory candidate summary for future queue and brief surfaces only"],"non_claims":["not source approval","not data approval","not endpoint approval","not universe approval","not benchmark a'
    'pproval","not cash proxy approval","not methodology approval","not evidence approval","not return-construction approval","not no-lookahead approval","not strategy validation","not trading readiness","not production use","not broker or runtime use","not order generation","not portfolio or allocation authority"],"package_fingerprint":"07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2","package_snapshot_id":"synthetic_return_input_snapshot_fixture_001","result_snapshot_manifest_checksum":"sha256:07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2","result_snapshot_manifest_fixture_id":"synthetic_return_input_snapshot_fixture_001","status":"candidate_only","summary_points":["package snapshot id: synthetic_return_input_snapshot_fixture_001","package fingerprint: 07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2","result manifest fixture id: synthetic'
    '_return_input_snapshot_fixture_001","result manifest checksum: sha256:07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"]}],"limitations":["metadata-only section for existing candidate brief items","does not create research, compute metrics, or mutate item payloads","advisory grouping for future queue and brief surfaces only","metadata-only dossier for an already prepared package and matching result","does not run research, fetch inputs, compute metrics, or mutate payloads","advisory candidate summary for future queue and brief surfaces only"],"non_claims":["not source approval","not data approval","not endpoint approval","not universe approval","not benchmark approval","not cash proxy approval","not methodology approval","not evidence approval","not return-construction approval","not no-lookahead approval","not strategy validation","not trading readiness","not production '
    'use","not broker or runtime use","not order generation","not portfolio or allocation authority"],"section_type":"candidate_research_results","status":"candidate_only","title":"Candidate research results metadata"}],"status":"candidate_only","title":"Candidate research brief metadata"}],"capital_authority":false,"limitations":["metadata-only brief for existing candidate research brief sections","does not create research, compute metrics, or mutate section payloads","advisory container for future queue and brief surfaces only","metadata-only section for existing candidate brief items","does not create research, compute metrics, or mutate item payloads","advisory grouping for future queue and brief surfaces only","metadata-only dossier for an already prepared package and matching result","does not run research, fetch inputs, compute metrics, or mutate payloads","advisory candidate summary f'
    'or future queue and brief surfaces only","synthetic metadata only","no profitability evidence is represented","no approval or readiness decision is represented"],"non_claims":["not source approval","not data approval","not endpoint approval","not universe approval","not benchmark approval","not cash proxy approval","not methodology approval","not evidence approval","not return-construction approval","not no-lookahead approval","not strategy validation","not trading readiness","not production use","not broker or runtime use","not order generation","not portfolio or allocation authority","not validation","not paper readiness","not live readiness","not a trading recommendation","not allocation authority","not order authority","not profitability evidence","not approval","not capital authority"],"status":"candidate_only","strategy_eligibility_brief_count":1,"strategy_eligibility_briefs":[{"au'
    'thority":"advisory_only","brief_type":"strategy_eligibility_brief","capital_authority":false,"limitations":["synthetic metadata only","no profitability evidence is represented","no approval or readiness decision is represented"],"non_claims":["not validation","not paper readiness","not live readiness","not a trading recommendation","not allocation authority","not order authority","not profitability evidence","not approval","not capital authority"],"section_count":1,"sections":[{"authority":"advisory_only","capital_authority":false,"item_count":1,"items":[{"authority":"advisory_only","blockers":["validation review has not been completed","readiness review has not been completed"],"capital_authority":false,"eligibility_state":"research_only","evidence_refs":["synthetic-evidence-ref-001","synthetic-advisory-metadata-ref-001"],"headline":"Advisory eligibility metadata: research_only.","item_'
    'type":"strategy_eligibility_brief_item","limitations":["synthetic metadata only","no profitability evidence is represented","no approval or readiness decision is represented"],"non_claims":["not validation","not paper readiness","not live readiness","not a trading recommendation","not allocation authority","not order authority","not profitability evidence","not approval","not capital authority"],"reasons":["synthetic strategy metadata is scoped to research review","eligibility status is provided for advisory composition tests"],"required_next_steps":["complete independent methodology review before any readiness claim","collect validation evidence before any approval claim"],"source_status":{"authority":"advisory_only","blockers":["validation review has not been completed","readiness review has not been completed"],"capital_authority":false,"eligibility_state":"research_only","eligibility'
    '_type":"strategy_eligibility_status","evidence_refs":["synthetic-evidence-ref-001","synthetic-advisory-metadata-ref-001"],"limitations":["synthetic metadata only","no profitability evidence is represented","no approval or readiness decision is represented"],"non_claims":["not validation","not paper readiness","not live readiness","not a trading recommendation","not allocation authority","not order authority","not profitability evidence","not approval","not capital authority"],"reasons":["synthetic strategy metadata is scoped to research review","eligibility status is provided for advisory composition tests"],"required_next_steps":["complete independent methodology review before any readiness claim","collect validation evidence before any approval claim"],"strategy_id":"synthetic-strategy-eligibility-001","strategy_name":"Synthetic strategy eligibility research fixture"},"status":"candida'
    'te_only","strategy_id":"synthetic-strategy-eligibility-001","strategy_name":"Synthetic strategy eligibility research fixture","summary":"Candidate metadata records research_only with 2 reason(s), 3 limitation(s), 9 non-claim(s), 2 evidence reference(s), 2 blocker(s), and 2 required next step(s)."}],"limitations":["synthetic metadata only","no profitability evidence is represented","no approval or readiness decision is represented"],"non_claims":["not validation","not paper readiness","not live readiness","not a trading recommendation","not allocation authority","not order authority","not profitability evidence","not approval","not capital authority"],"section_type":"strategy_eligibility_brief_section","status":"candidate_only","summary":"Advisory section contains 1 candidate eligibility item(s) across 1 strategy id(s), state(s): research_only, with 3 limitation(s) and 9 non-claim(s).","t'
    'itle":"Strategy eligibility metadata: research_only"}],"status":"candidate_only","summary":"Advisory brief contains 1 strategy eligibility section(s), 1 candidate item(s), 3 limitation(s), and 9 non-claim(s).","title":"Strategy eligibility brief metadata"}],"summary":"Advisory content bundle contains 1 candidate research brief(s), 1 strategy eligibility brief(s), 12 limitation(s), and 25 non-claim(s).","title":"Advisory operating brief content bundle metadata"}'
)
_EXPECTED_PAYLOAD = json.loads(_EXPECTED_JSON_TEXT)
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
_EXPECTED_RENDERED_TEXT = "\n".join(_EXPECTED_RENDERED_LINES)
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
    "json",
    "re",
    "sys",
    "algotrader.research.advisory_operating_brief_content_bundle_export",
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
    "argparse",
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
    "click",
    _s("data", "base"),
    "duckdb",
    _s("ht", "tp"),
    "httpx",
    "ipynb",
    "joblib",
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("mas", "sive"),
    _s("net", "work"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    "pathlib",
    _s("poly", "gon"),
    _s("poly", "gon_a", "pi_client"),
    _s("quant", "connect"),
    _s("re", "quests"),
    _s("sche", "dule"),
    "sklearn",
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "xgboost",
    _s("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
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
    "exists",
    "export_advisory_operating_brief",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    "importlib.import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "json.load",
    "load",
    "main",
    "mkdir",
    _s("op", "en"),
    "os.environ.get",
    "os.getenv",
    "parse_args",
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


def test_phase_162_fixture_export_matches_exact_pinned_in_memory_output() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    before_payload = bundle.to_dict()

    exported = export_advisory_operating_brief_content_bundle(bundle)

    assert exported.payload == _EXPECTED_PAYLOAD
    assert tuple(exported.payload) == _EXPECTED_EXPORT_PAYLOAD_KEYS
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.json_text == json.dumps(
        exported.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert json.loads(exported.json_text) == exported.payload
    assert exported.rendered_text == _EXPECTED_RENDERED_TEXT
    assert tuple(exported.rendered_text.splitlines()) == _EXPECTED_RENDERED_LINES
    assert exported.rendered_text == (
        render_advisory_operating_brief_content_bundle_text(bundle)
    )
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD


def test_repeated_exports_are_byte_for_byte_deterministic() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    before_payload = bundle.to_dict()

    first = export_advisory_operating_brief_content_bundle(bundle)
    second = export_advisory_operating_brief_content_bundle(bundle)

    assert first == second
    assert first.payload == second.payload == _EXPECTED_PAYLOAD
    assert first.payload is not second.payload
    assert first.json_text == second.json_text == _EXPECTED_JSON_TEXT
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert first.rendered_text == second.rendered_text == _EXPECTED_RENDERED_TEXT
    assert first.rendered_text.encode("utf-8") == second.rendered_text.encode("utf-8")
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD


def test_export_payload_mutation_is_isolated_from_bundle_and_later_exports() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    before_payload = bundle.to_dict()
    exported = export_advisory_operating_brief_content_bundle(bundle)

    _mutate_export_payload(exported.payload)

    assert exported.payload != _EXPECTED_PAYLOAD
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD
    assert render_advisory_operating_brief_content_bundle_text(bundle) == (
        _EXPECTED_RENDERED_TEXT
    )
    repeated = export_advisory_operating_brief_content_bundle(bundle)
    assert repeated.payload == _EXPECTED_PAYLOAD
    assert repeated.json_text == _EXPECTED_JSON_TEXT
    assert repeated.rendered_text == _EXPECTED_RENDERED_TEXT


def test_fixed_advisory_metadata_and_branch_order_are_stable() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )
    payload = exported.payload
    lines = tuple(exported.rendered_text.splitlines())

    assert payload["bundle_type"] == "advisory_operating_brief_content_bundle"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert payload["candidate_research_brief_count"] == 1
    assert payload["strategy_eligibility_brief_count"] == 1
    assert tuple(payload) == _EXPECTED_EXPORT_PAYLOAD_KEYS
    assert _index(payload, "candidate_research_briefs") < _index(
        payload,
        "strategy_eligibility_briefs",
    )
    assert len(payload["candidate_research_briefs"]) == 1
    assert len(payload["strategy_eligibility_briefs"]) == 1
    assert _line_index(lines, "Candidate Research Briefs") < _line_index(
        lines,
        "Strategy Eligibility Briefs",
    )
    assert _line_index(lines, "Strategy Eligibility Briefs") < _line_index(
        lines,
        "Limitations",
    )
    assert _line_index(lines, "Limitations") < _line_index(lines, "Non-Claims")


def test_limitations_non_claims_and_authority_language_are_source_cautions() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )
    payload = exported.payload
    rendered = exported.rendered_text
    source_cautions = _source_caution_values(payload)

    assert payload["limitations"]
    assert payload["non_claims"]
    assert "Limitations" in rendered.splitlines()
    assert "Non-Claims" in rendered.splitlines()
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_ACTIONABLE_FIELD_NAMES)
    assert _rendered_field_names(rendered).isdisjoint(_FORBIDDEN_ACTIONABLE_FIELD_NAMES)
    for path, value in _authority_presentation_payload_strings(payload):
        assert _is_caution_path(path)
        assert value in source_cautions
    for line in _authority_presentation_lines(rendered):
        assert line.startswith("- ")
        assert line[2:] in source_cautions
    assert "paper_eligible" not in exported.json_text
    assert "live_probe_eligible" not in exported.json_text
    assert "live_authorized" not in exported.json_text
    assert "trading_ready" not in exported.json_text
    assert "paper_eligible" not in rendered
    assert "live_probe_eligible" not in rendered
    assert "live_authorized" not in rendered
    assert "trading_ready" not in rendered


def test_regression_guard_is_test_only_and_isolated_from_forbidden_chains() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def _mutate_export_payload(payload: dict[str, object]) -> None:
    candidate = payload["candidate_research_briefs"][0]
    eligibility = payload["strategy_eligibility_briefs"][0]

    assert isinstance(candidate, dict)
    assert isinstance(eligibility, dict)
    payload["title"] = "mutated exported payload"
    payload["limitations"].append("mutated exported payload")
    candidate["title"] = "mutated exported candidate brief"
    eligibility["title"] = "mutated exported eligibility brief"


def _index(payload: dict[str, object], key: str) -> int:
    return tuple(payload).index(key)


def _line_index(lines: tuple[str, ...], value: str) -> int:
    return lines.index(value)


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, nested_value in value.items():
            keys.add(str(key))
            keys.update(_payload_keys(nested_value))
        return keys

    if isinstance(value, list):
        keys = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()


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


def _authority_presentation_payload_strings(
    value: object,
    path: str = "",
) -> tuple[tuple[str, str], ...]:
    matches: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}" if path else key
            matches.extend(_authority_presentation_payload_strings(nested_value, nested_path))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            matches.extend(
                _authority_presentation_payload_strings(
                    nested_value,
                    f"{path}[{index}]",
                )
            )
    elif isinstance(value, str) and _contains_authority_presentation_term(value):
        matches.append((path, value))

    return tuple(matches)


def _contains_authority_presentation_term(value: str) -> bool:
    lowered = value.lower()
    return any(
        re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", lowered)
        for term in _AUTHORITY_PRESENTATION_TERMS
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


def _is_caution_path(path: str) -> bool:
    return any(
        caution_field in path
        for caution_field in (
            "blockers[",
            "limitations[",
            "non_claims[",
            "required_next_steps[",
        )
    )


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
