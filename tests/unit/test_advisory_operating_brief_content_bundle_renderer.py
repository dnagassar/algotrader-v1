from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from algotrader.research.candidate_research_brief import CandidateResearchBrief
from algotrader.research.risk_authority_brief import (
    RiskAuthorityBrief,
    build_risk_authority_brief,
)
from algotrader.research.risk_authority_brief_item import (
    build_risk_authority_brief_item,
)
from algotrader.research.risk_authority_brief_section import (
    build_risk_authority_brief_section,
)
from algotrader.research.risk_authority_status import build_risk_authority_status
from algotrader.research.strategy_eligibility_brief import (
    StrategyEligibilityBrief,
    build_strategy_eligibility_brief,
)
from algotrader.research.strategy_eligibility_brief_item import (
    build_strategy_eligibility_brief_item,
)
from algotrader.research.strategy_eligibility_brief_section import (
    build_strategy_eligibility_brief_section,
)
from algotrader.research.strategy_eligibility_status import (
    build_strategy_eligibility_status,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_risk,
    expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict,
)
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
    expected_synthetic_candidate_research_brief_dict,
)
from tests.fixtures.strategy_eligibility_brief import (
    build_synthetic_strategy_eligibility_brief,
    expected_synthetic_strategy_eligibility_brief_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py"
)
_EXPECTED_SYNTHETIC_LINES = (
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
_EXPECTED_SYNTHETIC_TEXT = "\n".join(_EXPECTED_SYNTHETIC_LINES)
_EXPECTED_RISK_AUTHORITY_BRANCH_LINES = (
    "Risk Authority Briefs",
    "",
    "Risk Authority Brief 1",
    "brief_type: risk_authority_brief",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "title: Advisory risk metadata brief: 1 section",
    (
        "summary: Advisory brief contains 1 candidate risk metadata section(s) "
        "with 1 item(s), 3 limitation(s), and 13 non-claim(s)."
    ),
    "section_count: 1",
    "Sections",
    "",
    "Risk Authority Brief 1 Section 1",
    "section_type: risk_authority_brief_section",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "title: Advisory risk metadata: not_authorized",
    (
        "summary: Advisory section contains 1 candidate risk metadata item(s) "
        "across 1 related strategy id(s), state(s): not_authorized, with "
        "3 limitation(s) and 13 non-claim(s)."
    ),
    "item_count: 1",
    "Items",
    "",
    "Risk Authority Brief 1 Section 1 Item 1",
    "item_type: risk_authority_brief_item",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "authority_state: not_authorized",
    "headline: Advisory risk metadata: not_authorized.",
    (
        "summary: Advisory risk metadata records not_authorized with "
        "2 reason(s), 3 limitation(s), 13 non-claim(s), 2 evidence "
        "reference(s), 2 blocker(s), 2 required next step(s), and "
        "1 related strategy id(s)."
    ),
    "reasons:",
    "- synthetic risk authority status is scoped to advisory composition tests",
    "- risk-capital authority remains absent for this synthetic candidate",
    "evidence_refs:",
    "- synthetic-risk-authority-status-evidence-001",
    "- phase-169-risk-authority-status-contract",
    "blockers:",
    "- external risk review has not been completed",
    "- capital authorization path is not represented",
    "required_next_steps:",
    "- complete independent risk governance review before any authority change",
    "- record advisory-only evidence before composing downstream briefs",
    "related_strategy_ids:",
    "- synthetic-risk-authority-strategy-001",
    "limitations:",
    "- synthetic metadata only",
    (
        "- no approval, readiness, recommendation, allocation, order placement, "
        "broker access, portfolio mutation, capital authority, or trading "
        "authority is represented"
    ),
    "- fixture output is not connected to runtime or account state",
    "non_claims:",
    "- not risk approval",
    "- not allocation authority",
    "- not order authority",
    "- not paper readiness",
    "- not live readiness",
    "- not broker authority",
    "- not portfolio mutation authority",
    "- not capital authority",
    "- not trading authority",
    "- not a trading recommendation",
    "- not order placement",
    "- not broker access",
    "- not portfolio mutation",
    "source_status:",
    "source_status.authority_type: risk_authority_status",
    "source_status.authority: advisory_only",
    "source_status.capital_authority: False",
    "source_status.authority_state: not_authorized",
)
_EXPECTED_RISK_INCLUSIVE_LIMITATION_LINES = (
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
    (
        "- no approval, readiness, recommendation, allocation, order placement, "
        "broker access, portfolio mutation, capital authority, or trading "
        "authority is represented"
    ),
    "- fixture output is not connected to runtime or account state",
)
_EXPECTED_RISK_INCLUSIVE_NON_CLAIM_LINES = (
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
    "- not risk approval",
    "- not broker authority",
    "- not portfolio mutation authority",
    "- not trading authority",
    "- not order placement",
    "- not broker access",
    "- not portfolio mutation",
)
_EXPECTED_RISK_INCLUSIVE_LINES = (
    *_EXPECTED_SYNTHETIC_LINES[:6],
    (
        "summary: Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        "14 limitation(s), and 32 non-claim(s)."
    ),
    "candidate_research_brief_count: 1",
    "strategy_eligibility_brief_count: 1",
    "risk_authority_brief_count: 1",
    *_EXPECTED_SYNTHETIC_LINES[9:103],
    *_EXPECTED_RISK_AUTHORITY_BRANCH_LINES,
    "",
    "Limitations",
    *_EXPECTED_RISK_INCLUSIVE_LIMITATION_LINES,
    "",
    "Non-Claims",
    *_EXPECTED_RISK_INCLUSIVE_NON_CLAIM_LINES,
)
_EXPECTED_RISK_INCLUSIVE_TEXT = "\n".join(_EXPECTED_RISK_INCLUSIVE_LINES)
_AUTHORITY_SENSITIVE_RENDER_TERMS = (
    _s("app", "roval"),
    _s("app", "roved"),
    "paper readiness",
    "live readiness",
    _s("allo", "cation authority"),
    _s("or", "der authority"),
    _s("bro", "ker authority"),
    _s("port", "folio mutation authority"),
    _s("tra", "ding authority"),
    _s("or", "der placement"),
    _s("bro", "ker access"),
    _s("port", "folio mutation"),
    "account state",
    "paper_eligible",
    "live_probe_eligible",
    "live_authorized",
    "trading_ready",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief_content_bundle",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
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
    "Path",
    _s("cli", "ent"),
    _s("con", "nect"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
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
_FORBIDDEN_AUTHORITY_FIELDS = {
    "account",
    "accounts",
    "approved",
    _s("bro", "ker"),
    _s("bro", "kers"),
    "buy",
    "sell",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _s("or", "der"),
    _s("or", "ders"),
    "paper_eligible",
    _s("port", "folio"),
    _s("port", "folios"),
    _s("allo", "cation"),
    _s("allo", "cations"),
    _s("allo", "cation_authority"),
    _s("or", "der_authority"),
    _s("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_EXACT_LITERALS = {
    "account",
    "accounts",
    "approved",
    "buy",
    "sell",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    "paper_eligible",
    _s("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_SOURCE_TOKENS = (
    "paper_eligible",
    "live_probe_eligible",
    "live_authorized",
    "trading_ready",
    "approved",
    "buy",
    "sell",
    "hold",
    _s("allo", "cation"),
    _s("or", "der"),
    _s("bro", "ker"),
    "account",
    _s("port", "folio"),
    _s("tra", "ding_authority"),
)


def test_valid_rendering_from_phase_162_synthetic_content_bundle_fixture() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert isinstance(rendered, str)
    assert rendered == _EXPECTED_SYNTHETIC_TEXT
    assert tuple(rendered.splitlines()) == _EXPECTED_SYNTHETIC_LINES


def test_valid_rendering_from_phase_178_risk_inclusive_fixture() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()

    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert bundle.to_dict() == (
        expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict()
    )
    assert rendered == _EXPECTED_RISK_INCLUSIVE_TEXT
    assert tuple(rendered.splitlines()) == _EXPECTED_RISK_INCLUSIVE_LINES


def test_repeated_rendering_is_byte_for_byte_deterministic() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    first = render_advisory_operating_brief_content_bundle_text(bundle)
    second = render_advisory_operating_brief_content_bundle_text(bundle)

    assert first
    assert first.strip() == first
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_repeated_risk_inclusive_rendering_is_byte_for_byte_deterministic() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()

    first = render_advisory_operating_brief_content_bundle_text(bundle)
    second = render_advisory_operating_brief_content_bundle_text(bundle)

    assert first == _EXPECTED_RISK_INCLUSIVE_TEXT
    assert first.strip() == first
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_candidate_research_branch_sequence_is_preserved() -> None:
    first = _candidate_brief_variant("candidate branch alpha")
    second = _candidate_brief_variant("candidate branch beta")
    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(second, first),
    )

    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert _index(rendered, "title: candidate branch beta") < _index(
        rendered,
        "title: candidate branch alpha",
    )


def test_strategy_eligibility_branch_sequence_is_preserved() -> None:
    first = build_synthetic_strategy_eligibility_brief()
    second = _second_strategy_eligibility_brief()
    bundle = build_advisory_operating_brief_content_bundle(
        strategy_eligibility_briefs=(second, first),
    )

    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert _index(
        rendered,
        "strategy_id: synthetic-strategy-eligibility-renderer-002",
    ) < _index(rendered, "strategy_id: synthetic-strategy-eligibility-001")
    assert _index(rendered, "eligibility_state: watchlist_only") < _index(
        rendered,
        "eligibility_state: research_only",
    )


def test_risk_authority_branch_sequence_is_preserved() -> None:
    first = (
        build_synthetic_advisory_operating_brief_content_bundle_with_risk()
        .risk_authority_briefs[0]
    )
    second = _second_risk_authority_brief()
    bundle = build_advisory_operating_brief_content_bundle(
        risk_authority_briefs=(second, first),
    )

    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert _index(rendered, "authority_state: blocked") < _index(
        rendered,
        "authority_state: not_authorized",
    )
    assert _index(
        rendered,
        "synthetic-risk-authority-renderer-strategy-002",
    ) < _index(rendered, "synthetic-risk-authority-strategy-001")


def test_fixed_advisory_metadata_is_present() -> None:
    rendered = render_advisory_operating_brief_content_bundle_text(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    assert "bundle_type: advisory_operating_brief_content_bundle" in rendered
    assert "status: candidate_only" in rendered
    assert "authority: advisory_only" in rendered
    assert "capital_authority: False" in rendered
    assert "title: Advisory operating brief content bundle metadata" in rendered
    assert (
        "summary: Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 12 limitation(s), and 25 non-claim(s)."
    ) in rendered


def test_fixed_advisory_metadata_is_present_for_risk_inclusive_bundle() -> None:
    rendered = render_advisory_operating_brief_content_bundle_text(
        build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    )

    assert "bundle_type: advisory_operating_brief_content_bundle" in rendered
    assert "status: candidate_only" in rendered
    assert "authority: advisory_only" in rendered
    assert "capital_authority: False" in rendered
    assert "title: Advisory operating brief content bundle metadata" in rendered
    assert "risk_authority_brief_count: 1" in rendered
    assert (
        "summary: Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        "14 limitation(s), and 32 non-claim(s)."
    ) in rendered


def test_phase_160_strategy_eligibility_payload_content_is_represented() -> None:
    expected = expected_synthetic_strategy_eligibility_brief_dict()
    item = expected["sections"][0]["items"][0]
    source_status = item["source_status"]
    rendered = render_advisory_operating_brief_content_bundle_text(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    assert f"title: {expected['title']}" in rendered
    assert f"summary: {expected['summary']}" in rendered
    assert f"eligibility_state: {item['eligibility_state']}" in rendered
    assert f"source_status.eligibility_type: {source_status['eligibility_type']}" in (
        rendered
    )
    for field_name in (
        "reasons",
        "evidence_refs",
        "blockers",
        "required_next_steps",
        "limitations",
        "non_claims",
    ):
        for value in item[field_name]:
            assert f"- {value}" in rendered


def test_existing_candidate_research_payload_content_is_represented() -> None:
    expected = expected_synthetic_candidate_research_brief_dict()
    section = expected["sections"][0]
    item = section["items"][0]
    rendered = render_advisory_operating_brief_content_bundle_text(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    assert f"title: {expected['title']}" in rendered
    assert f"title: {section['title']}" in rendered
    assert f"headline: {item['headline']}" in rendered
    assert f"package_fingerprint: {item['package_fingerprint']}" in rendered
    assert f"package_snapshot_id: {item['package_snapshot_id']}" in rendered
    for value in item["summary_points"]:
        assert f"- {value}" in rendered


def test_phase_178_risk_authority_payload_content_is_represented() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    expected = bundle.to_dict()["risk_authority_briefs"][0]
    section = expected["sections"][0]
    item = section["items"][0]
    source_status = item["source_status"]
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert f"title: {expected['title']}" in rendered
    assert f"summary: {expected['summary']}" in rendered
    assert f"title: {section['title']}" in rendered
    assert f"summary: {section['summary']}" in rendered
    assert f"authority_state: {item['authority_state']}" in rendered
    assert f"headline: {item['headline']}" in rendered
    assert f"summary: {item['summary']}" in rendered
    assert f"source_status.authority_type: {source_status['authority_type']}" in (
        rendered
    )
    assert f"source_status.authority_state: {source_status['authority_state']}" in (
        rendered
    )
    for field_name in (
        "reasons",
        "evidence_refs",
        "blockers",
        "required_next_steps",
        "related_strategy_ids",
        "limitations",
        "non_claims",
    ):
        for value in item[field_name]:
            assert f"- {value}" in rendered


def test_limitations_and_non_claims_are_represented() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    for value in bundle.limitations:
        assert f"- {value}" in rendered
    for value in bundle.non_claims:
        assert f"- {value}" in rendered


def test_limitations_and_non_claims_from_all_branches_are_represented_with_risk() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    branch_payloads = (
        *bundle.to_dict()["candidate_research_briefs"],
        *bundle.to_dict()["strategy_eligibility_briefs"],
        *bundle.to_dict()["risk_authority_briefs"],
    )

    for branch_payload in branch_payloads:
        for value in branch_payload["limitations"]:
            assert f"- {value}" in rendered
        for value in branch_payload["non_claims"]:
            assert f"- {value}" in rendered
    for value in bundle.limitations:
        assert f"- {value}" in rendered
    for value in bundle.non_claims:
        assert f"- {value}" in rendered


def test_rendering_does_not_mutate_source_bundle_payload() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    before = bundle.to_dict()

    render_advisory_operating_brief_content_bundle_text(bundle)
    render_advisory_operating_brief_content_bundle_text(bundle)

    assert bundle.to_dict() == before


def test_risk_inclusive_rendering_does_not_mutate_source_bundle_payload() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    before = bundle.to_dict()

    render_advisory_operating_brief_content_bundle_text(bundle)
    render_advisory_operating_brief_content_bundle_text(bundle)

    assert bundle.to_dict() == before


@pytest.mark.parametrize("value", (object(), None, "not a bundle"))
def test_non_bundle_inputs_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError, match="AdvisoryOperatingBriefContentBundle"):
        render_advisory_operating_brief_content_bundle_text(value)


def test_malformed_bundle_like_objects_are_rejected() -> None:
    class BundleLike:
        bundle_type = "advisory_operating_brief_content_bundle"
        status = "candidate_only"
        authority = "advisory_only"
        capital_authority = False

        def to_dict(self) -> dict[str, object]:
            return {"bundle_type": self.bundle_type}

    with pytest.raises(ValidationError, match="exactly"):
        render_advisory_operating_brief_content_bundle_text(BundleLike())


def test_subclasses_are_rejected_to_require_exact_bundle_input() -> None:
    class BundleSubclass(AdvisoryOperatingBriefContentBundle):
        pass

    source = build_synthetic_advisory_operating_brief_content_bundle()
    subclass_bundle = BundleSubclass(
        bundle_type=source.bundle_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        title=source.title,
        summary=source.summary,
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        limitations=source.limitations,
        non_claims=source.non_claims,
    )

    with pytest.raises(ValidationError, match="exactly"):
        render_advisory_operating_brief_content_bundle_text(subclass_bundle)


def test_renderer_does_not_expose_restricted_states_as_authority() -> None:
    rendered = render_advisory_operating_brief_content_bundle_text(
        build_synthetic_advisory_operating_brief_content_bundle()
    )
    authority_lines = tuple(
        line
        for line in rendered.splitlines()
        if line.startswith("authority:")
        or line.startswith("capital_authority:")
        or line.startswith("source_status.authority:")
        or line.startswith("source_status.capital_authority:")
    )

    assert authority_lines
    assert set(authority_lines) == {
        "authority: advisory_only",
        "capital_authority: False",
        "source_status.authority: advisory_only",
        "source_status.capital_authority: False",
    }
    assert _rendered_field_names(rendered).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    for token in (
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
        "trading_ready",
        "approved",
    ):
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", rendered) is None


def test_risk_inclusive_renderer_exposes_authority_terms_only_as_cautions() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    source_cautions = _source_caution_values(bundle.to_dict())

    assert _rendered_field_names(rendered).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    for line in _authority_sensitive_lines(rendered):
        assert line.startswith("- ")
        assert line[2:] in source_cautions
    for token in (
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
        "trading_ready",
    ):
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", rendered) is None


def test_renderer_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_renderer_module_literals_add_no_actionable_authority_fields() -> None:
    literals = _string_literals()
    lowered_source = _source_text().lower()

    assert literals.isdisjoint(_FORBIDDEN_EXACT_LITERALS)
    for token in _FORBIDDEN_SOURCE_TOKENS:
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", lowered_source) is None


def _candidate_brief_variant(title: str) -> CandidateResearchBrief:
    brief = build_synthetic_candidate_research_brief()
    return CandidateResearchBrief(
        brief_type=brief.brief_type,
        status=brief.status,
        title=title,
        sections=brief.sections,
        limitations=brief.limitations,
        non_claims=brief.non_claims,
    )


def _second_strategy_eligibility_brief() -> StrategyEligibilityBrief:
    status = build_strategy_eligibility_status(
        strategy_id="synthetic-strategy-eligibility-renderer-002",
        strategy_name="Renderer secondary synthetic strategy metadata",
        eligibility_state="watchlist_only",
        reasons=("secondary renderer metadata is scoped to advisory display",),
        limitations=("synthetic metadata only", "secondary renderer metadata only"),
        non_claims=(
            "not validation",
            "not paper readiness",
            "not live readiness",
            _s("not a tra", "ding recommendation"),
            _s("not allo", "cation authority"),
            _s("not or", "der authority"),
            "not secondary renderer metadata claim",
        ),
        evidence_refs=("synthetic-renderer-evidence-ref-002",),
        blockers=("secondary renderer review has not been completed",),
        required_next_steps=("complete secondary renderer review before any claim",),
    )
    item = build_strategy_eligibility_brief_item(status)
    section = build_strategy_eligibility_brief_section((item,))
    return build_strategy_eligibility_brief((section,))


def _second_risk_authority_brief() -> RiskAuthorityBrief:
    status = build_risk_authority_status(
        authority_state="blocked",
        reasons=("secondary risk metadata is scoped to advisory display",),
        blockers=("secondary risk governance review has not been completed",),
        required_next_steps=(
            "complete secondary risk governance review before any claim",
        ),
        limitations=("synthetic metadata only", "secondary risk renderer only"),
        non_claims=(
            "not risk approval",
            _s("not allo", "cation authority"),
            _s("not or", "der authority"),
            "not paper readiness",
            "not live readiness",
            _s("not bro", "ker authority"),
            _s("not port", "folio mutation authority"),
            "not capital authority",
            "not trading authority",
            _s("not a tra", "ding recommendation"),
            "not secondary risk renderer claim",
        ),
        evidence_refs=("synthetic-risk-renderer-evidence-ref-002",),
        related_strategy_ids=("synthetic-risk-authority-renderer-strategy-002",),
    )
    item = build_risk_authority_brief_item(status)
    section = build_risk_authority_brief_section((item,))
    return build_risk_authority_brief((section,))


def _index(text: str, value: str) -> int:
    return text.index(value)


def _rendered_field_names(text: str) -> set[str]:
    field_names: set[str] = set()
    for line in text.splitlines():
        if line.startswith("- ") or ":" not in line:
            continue
        field_names.add(line.split(":", maxsplit=1)[0])

    return field_names


def _authority_sensitive_lines(text: str) -> tuple[str, ...]:
    return tuple(
        line
        for line in text.splitlines()
        if any(
            re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", line.lower())
            for term in _AUTHORITY_SENSITIVE_RENDER_TERMS
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


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            elif node.level > 0:
                imports.add("__future__")

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


def _string_literals() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
