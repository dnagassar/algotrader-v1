from __future__ import annotations

import ast
import json
import re
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

import algotrader.research.advisory_operating_brief_content_bundle as bundle_module
from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.candidate_research_brief import CandidateResearchBrief
from algotrader.research.research_queue_brief import (
    ResearchQueueBrief,
    build_research_queue_brief,
)
from algotrader.research.research_queue_brief_item import (
    build_research_queue_brief_item,
)
from algotrader.research.research_queue_brief_section import (
    build_research_queue_brief_section,
)
from algotrader.research.research_queue_status import build_research_queue_status
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
from algotrader.research.sma_research_observation_brief_container import (
    SmaResearchObservationBrief,
)
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
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
    expected_synthetic_candidate_research_brief_dict,
)
from tests.fixtures.research_queue_brief import (
    build_synthetic_research_queue_brief,
    expected_synthetic_research_queue_brief_dict,
)
from tests.fixtures.risk_authority_brief import (
    build_synthetic_risk_authority_brief,
    expected_synthetic_risk_authority_brief_dict,
)
from tests.fixtures.sma_research_observation_brief_container import (
    build_synthetic_sma_research_observation_brief,
    expected_synthetic_sma_research_observation_brief_dict,
)
from tests.fixtures.strategy_eligibility_brief import (
    build_synthetic_strategy_eligibility_brief,
    expected_synthetic_strategy_eligibility_brief_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _combined_expected_values(
    *payloads: dict[str, object],
    field_name: str,
) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for payload in payloads:
        for value in payload[field_name]:
            assert isinstance(value, str)
            if value in seen:
                continue
            values.append(value)
            seen.add(value)

    return tuple(values)


MODULE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_content_bundle.py"
)
_EXPECTED_CANDIDATE_BRIEF_DICT = expected_synthetic_candidate_research_brief_dict()
_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT = (
    expected_synthetic_strategy_eligibility_brief_dict()
)
_EXPECTED_RISK_AUTHORITY_BRIEF_DICT = expected_synthetic_risk_authority_brief_dict()
_EXPECTED_RESEARCH_QUEUE_BRIEF_DICT = expected_synthetic_research_queue_brief_dict()
_EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT = (
    expected_synthetic_sma_research_observation_brief_dict()
)
_EXPECTED_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    field_name="limitations",
)
_EXPECTED_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    field_name="non_claims",
)
_EXPECTED_ALL_FAMILY_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    field_name="limitations",
)
_EXPECTED_ALL_FAMILY_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    field_name="non_claims",
)
_EXPECTED_RESEARCH_QUEUE_FAMILY_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
    field_name="limitations",
)
_EXPECTED_RESEARCH_QUEUE_FAMILY_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
    field_name="non_claims",
)
_EXPECTED_SMA_FAMILY_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
    _EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT,
    field_name="limitations",
)
_EXPECTED_SMA_FAMILY_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
    _EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT,
    field_name="non_claims",
)
_EXPECTED_COMBINED_BUNDLE_DICT = {
    "bundle_type": "advisory_operating_brief_content_bundle",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory operating brief content bundle metadata",
    "summary": (
        "Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 12 limitation(s), and 25 non-claim(s)."
    ),
    "candidate_research_brief_count": 1,
    "strategy_eligibility_brief_count": 1,
    "candidate_research_briefs": [_EXPECTED_CANDIDATE_BRIEF_DICT],
    "strategy_eligibility_briefs": [_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT],
    "limitations": list(_EXPECTED_LIMITATIONS),
    "non_claims": list(_EXPECTED_NON_CLAIMS),
}
_EXPECTED_ALL_FAMILY_BUNDLE_DICT = {
    "bundle_type": "advisory_operating_brief_content_bundle",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory operating brief content bundle metadata",
    "summary": (
        "Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        f"{len(_EXPECTED_ALL_FAMILY_LIMITATIONS)} limitation(s), and "
        f"{len(_EXPECTED_ALL_FAMILY_NON_CLAIMS)} non-claim(s)."
    ),
    "candidate_research_brief_count": 1,
    "strategy_eligibility_brief_count": 1,
    "risk_authority_brief_count": 1,
    "candidate_research_briefs": [_EXPECTED_CANDIDATE_BRIEF_DICT],
    "strategy_eligibility_briefs": [_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT],
    "risk_authority_briefs": [_EXPECTED_RISK_AUTHORITY_BRIEF_DICT],
    "limitations": list(_EXPECTED_ALL_FAMILY_LIMITATIONS),
    "non_claims": list(_EXPECTED_ALL_FAMILY_NON_CLAIMS),
}
_EXPECTED_RESEARCH_QUEUE_FAMILY_BUNDLE_DICT = {
    "bundle_type": "advisory_operating_brief_content_bundle",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory operating brief content bundle metadata",
    "summary": (
        "Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        "1 research queue brief(s), "
        f"{len(_EXPECTED_RESEARCH_QUEUE_FAMILY_LIMITATIONS)} limitation(s), and "
        f"{len(_EXPECTED_RESEARCH_QUEUE_FAMILY_NON_CLAIMS)} non-claim(s)."
    ),
    "candidate_research_brief_count": 1,
    "strategy_eligibility_brief_count": 1,
    "risk_authority_brief_count": 1,
    "research_queue_brief_count": 1,
    "candidate_research_briefs": [_EXPECTED_CANDIDATE_BRIEF_DICT],
    "strategy_eligibility_briefs": [_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT],
    "risk_authority_briefs": [_EXPECTED_RISK_AUTHORITY_BRIEF_DICT],
    "research_queue_briefs": [_EXPECTED_RESEARCH_QUEUE_BRIEF_DICT],
    "limitations": list(_EXPECTED_RESEARCH_QUEUE_FAMILY_LIMITATIONS),
    "non_claims": list(_EXPECTED_RESEARCH_QUEUE_FAMILY_NON_CLAIMS),
}
_EXPECTED_SMA_FAMILY_BUNDLE_DICT = {
    "bundle_type": "advisory_operating_brief_content_bundle",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory operating brief content bundle metadata",
    "summary": (
        "Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        "1 research queue brief(s), 1 SMA research observation brief(s), "
        f"{len(_EXPECTED_SMA_FAMILY_LIMITATIONS)} limitation(s), and "
        f"{len(_EXPECTED_SMA_FAMILY_NON_CLAIMS)} non-claim(s)."
    ),
    "candidate_research_brief_count": 1,
    "strategy_eligibility_brief_count": 1,
    "risk_authority_brief_count": 1,
    "research_queue_brief_count": 1,
    "sma_research_observation_brief_count": 1,
    "candidate_research_briefs": [_EXPECTED_CANDIDATE_BRIEF_DICT],
    "strategy_eligibility_briefs": [_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT],
    "risk_authority_briefs": [_EXPECTED_RISK_AUTHORITY_BRIEF_DICT],
    "research_queue_briefs": [_EXPECTED_RESEARCH_QUEUE_BRIEF_DICT],
    "sma_research_observation_briefs": [_EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT],
    "limitations": list(_EXPECTED_SMA_FAMILY_LIMITATIONS),
    "non_claims": list(_EXPECTED_SMA_FAMILY_NON_CLAIMS),
}
_EXPECTED_COMPACT_JSON = json.dumps(
    _EXPECTED_COMBINED_BUNDLE_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
)
_EXPECTED_ALL_FAMILY_COMPACT_JSON = json.dumps(
    _EXPECTED_ALL_FAMILY_BUNDLE_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
)
_EXPECTED_RESEARCH_QUEUE_FAMILY_COMPACT_JSON = json.dumps(
    _EXPECTED_RESEARCH_QUEUE_FAMILY_BUNDLE_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
)
_EXPECTED_SMA_FAMILY_COMPACT_JSON = json.dumps(
    _EXPECTED_SMA_FAMILY_BUNDLE_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
)
_FORBIDDEN_TEXT_TOKENS = (
    "recommend",
    "recommendation",
    "approval",
    "approved",
    "paper",
    "live",
    "ready",
    "readiness",
    "buy",
    "sell",
    "hold",
    _s("allo", "cation"),
    _s("or", "der"),
    _s("tra", "ding"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.candidate_research_brief",
    "algotrader.research.research_queue_brief",
    "algotrader.research.risk_authority_brief",
    "algotrader.research.sma_research_observation_brief_container",
    "algotrader.research.strategy_eligibility_brief",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
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
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
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
    _s("import_module"),
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


def test_valid_construction_with_synthetic_candidate_research_brief() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=[candidate_brief],
        strategy_eligibility_briefs=[],
    )

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert bundle.candidate_research_briefs == (candidate_brief,)
    assert bundle.candidate_research_briefs[0] is candidate_brief
    assert bundle.strategy_eligibility_briefs == ()
    assert bundle.risk_authority_briefs == ()
    assert bundle.research_queue_briefs == ()
    assert bundle.sma_research_observation_briefs == ()
    assert "risk_authority_briefs" not in bundle.to_dict()
    assert "research_queue_briefs" not in bundle.to_dict()
    assert "sma_research_observation_briefs" not in bundle.to_dict()
    assert bundle.to_dict()["candidate_research_briefs"][0] == (
        expected_synthetic_candidate_research_brief_dict()
    )


def test_valid_construction_with_phase_160_strategy_eligibility_brief() -> None:
    eligibility_brief = build_synthetic_strategy_eligibility_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        strategy_eligibility_briefs=[eligibility_brief],
    )

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert bundle.candidate_research_briefs == ()
    assert bundle.strategy_eligibility_briefs == (eligibility_brief,)
    assert bundle.strategy_eligibility_briefs[0] is eligibility_brief
    assert bundle.risk_authority_briefs == ()
    assert bundle.research_queue_briefs == ()
    assert bundle.sma_research_observation_briefs == ()
    assert "risk_authority_briefs" not in bundle.to_dict()
    assert "research_queue_briefs" not in bundle.to_dict()
    assert "sma_research_observation_briefs" not in bundle.to_dict()
    assert bundle.to_dict()["strategy_eligibility_briefs"][0] == (
        expected_synthetic_strategy_eligibility_brief_dict()
    )


def test_valid_construction_with_both_families_populated() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=[candidate_brief],
        strategy_eligibility_briefs=[eligibility_brief],
    )

    assert bundle.candidate_research_briefs == (candidate_brief,)
    assert bundle.strategy_eligibility_briefs == (eligibility_brief,)
    assert bundle.risk_authority_briefs == ()
    assert bundle.research_queue_briefs == ()
    assert bundle.sma_research_observation_briefs == ()
    assert bundle.to_dict() == _EXPECTED_COMBINED_BUNDLE_DICT


def test_valid_construction_with_phase_176_risk_authority_brief() -> None:
    risk_brief = build_synthetic_risk_authority_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        risk_authority_briefs=[risk_brief],
    )
    payload = bundle.to_dict()

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert bundle.candidate_research_briefs == ()
    assert bundle.strategy_eligibility_briefs == ()
    assert bundle.risk_authority_briefs == (risk_brief,)
    assert bundle.risk_authority_briefs[0] is risk_brief
    assert bundle.research_queue_briefs == ()
    assert bundle.sma_research_observation_briefs == ()
    assert payload["candidate_research_brief_count"] == 0
    assert payload["strategy_eligibility_brief_count"] == 0
    assert payload["risk_authority_brief_count"] == 1
    assert "research_queue_brief_count" not in payload
    assert "research_queue_briefs" not in payload
    assert "sma_research_observation_brief_count" not in payload
    assert "sma_research_observation_briefs" not in payload
    assert payload["risk_authority_briefs"][0] == (
        expected_synthetic_risk_authority_brief_dict()
    )


def test_valid_construction_with_phase_182_research_queue_brief() -> None:
    research_queue_brief = build_synthetic_research_queue_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        research_queue_briefs=[research_queue_brief],
    )
    payload = bundle.to_dict()

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert bundle.candidate_research_briefs == ()
    assert bundle.strategy_eligibility_briefs == ()
    assert bundle.risk_authority_briefs == ()
    assert bundle.research_queue_briefs == (research_queue_brief,)
    assert bundle.research_queue_briefs[0] is research_queue_brief
    assert bundle.sma_research_observation_briefs == ()
    assert payload["candidate_research_brief_count"] == 0
    assert payload["strategy_eligibility_brief_count"] == 0
    assert "risk_authority_brief_count" not in payload
    assert payload["research_queue_brief_count"] == 1
    assert "sma_research_observation_brief_count" not in payload
    assert payload["research_queue_briefs"][0] == (
        expected_synthetic_research_queue_brief_dict()
    )


def test_valid_construction_with_phase_201_sma_research_observation_brief() -> None:
    sma_brief = build_synthetic_sma_research_observation_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        sma_research_observation_briefs=[sma_brief],
    )
    payload = bundle.to_dict()

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert bundle.candidate_research_briefs == ()
    assert bundle.strategy_eligibility_briefs == ()
    assert bundle.risk_authority_briefs == ()
    assert bundle.research_queue_briefs == ()
    assert bundle.sma_research_observation_briefs == (sma_brief,)
    assert bundle.sma_research_observation_briefs[0] is sma_brief
    assert payload["candidate_research_brief_count"] == 0
    assert payload["strategy_eligibility_brief_count"] == 0
    assert "risk_authority_brief_count" not in payload
    assert "research_queue_brief_count" not in payload
    assert payload["sma_research_observation_brief_count"] == 1
    assert payload["sma_research_observation_briefs"][0] == (
        expected_synthetic_sma_research_observation_brief_dict()
    )


def test_valid_construction_with_all_three_families_populated() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()
    risk_brief = build_synthetic_risk_authority_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=[candidate_brief],
        strategy_eligibility_briefs=[eligibility_brief],
        risk_authority_briefs=[risk_brief],
    )

    assert bundle.candidate_research_briefs == (candidate_brief,)
    assert bundle.strategy_eligibility_briefs == (eligibility_brief,)
    assert bundle.risk_authority_briefs == (risk_brief,)
    assert bundle.research_queue_briefs == ()
    assert bundle.sma_research_observation_briefs == ()
    assert bundle.to_dict() == _EXPECTED_ALL_FAMILY_BUNDLE_DICT


def test_valid_construction_with_all_four_families_populated() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()
    risk_brief = build_synthetic_risk_authority_brief()
    research_queue_brief = build_synthetic_research_queue_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=[candidate_brief],
        strategy_eligibility_briefs=[eligibility_brief],
        risk_authority_briefs=[risk_brief],
        research_queue_briefs=[research_queue_brief],
    )

    assert bundle.candidate_research_briefs == (candidate_brief,)
    assert bundle.strategy_eligibility_briefs == (eligibility_brief,)
    assert bundle.risk_authority_briefs == (risk_brief,)
    assert bundle.research_queue_briefs == (research_queue_brief,)
    assert bundle.sma_research_observation_briefs == ()
    assert bundle.to_dict() == _EXPECTED_RESEARCH_QUEUE_FAMILY_BUNDLE_DICT


def test_valid_construction_with_all_five_families_populated() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()
    risk_brief = build_synthetic_risk_authority_brief()
    research_queue_brief = build_synthetic_research_queue_brief()
    sma_brief = build_synthetic_sma_research_observation_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=[candidate_brief],
        strategy_eligibility_briefs=[eligibility_brief],
        risk_authority_briefs=[risk_brief],
        research_queue_briefs=[research_queue_brief],
        sma_research_observation_briefs=[sma_brief],
    )

    assert bundle.candidate_research_briefs == (candidate_brief,)
    assert bundle.strategy_eligibility_briefs == (eligibility_brief,)
    assert bundle.risk_authority_briefs == (risk_brief,)
    assert bundle.research_queue_briefs == (research_queue_brief,)
    assert bundle.sma_research_observation_briefs == (sma_brief,)
    assert bundle.to_dict() == _EXPECTED_SMA_FAMILY_BUNDLE_DICT


def test_empty_candidate_family_is_allowed_when_eligibility_family_is_non_empty() -> (
    None
):
    eligibility_brief = build_synthetic_strategy_eligibility_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(),
        strategy_eligibility_briefs=(eligibility_brief,),
    )

    assert bundle.candidate_research_briefs == ()
    assert bundle.strategy_eligibility_briefs == (eligibility_brief,)
    assert bundle.risk_authority_briefs == ()
    assert bundle.to_dict()["candidate_research_brief_count"] == 0
    assert bundle.to_dict()["strategy_eligibility_brief_count"] == 1
    assert "risk_authority_brief_count" not in bundle.to_dict()
    assert "research_queue_brief_count" not in bundle.to_dict()
    assert "sma_research_observation_brief_count" not in bundle.to_dict()


def test_empty_eligibility_family_is_allowed_when_candidate_family_is_non_empty() -> (
    None
):
    candidate_brief = build_synthetic_candidate_research_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(),
    )

    assert bundle.candidate_research_briefs == (candidate_brief,)
    assert bundle.strategy_eligibility_briefs == ()
    assert bundle.risk_authority_briefs == ()
    assert bundle.to_dict()["candidate_research_brief_count"] == 1
    assert bundle.to_dict()["strategy_eligibility_brief_count"] == 0
    assert "risk_authority_brief_count" not in bundle.to_dict()
    assert "research_queue_brief_count" not in bundle.to_dict()
    assert "sma_research_observation_brief_count" not in bundle.to_dict()


def test_empty_candidate_and_eligibility_families_are_allowed_when_risk_is_non_empty() -> (
    None
):
    risk_brief = build_synthetic_risk_authority_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(),
        strategy_eligibility_briefs=(),
        risk_authority_briefs=(risk_brief,),
    )

    assert bundle.candidate_research_briefs == ()
    assert bundle.strategy_eligibility_briefs == ()
    assert bundle.risk_authority_briefs == (risk_brief,)
    assert bundle.to_dict()["candidate_research_brief_count"] == 0
    assert bundle.to_dict()["strategy_eligibility_brief_count"] == 0
    assert bundle.to_dict()["risk_authority_brief_count"] == 1
    assert "sma_research_observation_brief_count" not in bundle.to_dict()


def test_empty_existing_families_are_allowed_when_research_queue_is_non_empty() -> (
    None
):
    research_queue_brief = build_synthetic_research_queue_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(),
        strategy_eligibility_briefs=(),
        risk_authority_briefs=(),
        research_queue_briefs=(research_queue_brief,),
    )

    assert bundle.candidate_research_briefs == ()
    assert bundle.strategy_eligibility_briefs == ()
    assert bundle.risk_authority_briefs == ()
    assert bundle.research_queue_briefs == (research_queue_brief,)
    assert bundle.to_dict()["candidate_research_brief_count"] == 0
    assert bundle.to_dict()["strategy_eligibility_brief_count"] == 0
    assert "risk_authority_brief_count" not in bundle.to_dict()
    assert bundle.to_dict()["research_queue_brief_count"] == 1
    assert "sma_research_observation_brief_count" not in bundle.to_dict()


def test_empty_existing_families_are_allowed_when_sma_branch_is_non_empty() -> None:
    sma_brief = build_synthetic_sma_research_observation_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(),
        strategy_eligibility_briefs=(),
        risk_authority_briefs=(),
        research_queue_briefs=(),
        sma_research_observation_briefs=(sma_brief,),
    )

    assert bundle.candidate_research_briefs == ()
    assert bundle.strategy_eligibility_briefs == ()
    assert bundle.risk_authority_briefs == ()
    assert bundle.research_queue_briefs == ()
    assert bundle.sma_research_observation_briefs == (sma_brief,)
    assert bundle.to_dict()["candidate_research_brief_count"] == 0
    assert bundle.to_dict()["strategy_eligibility_brief_count"] == 0
    assert "risk_authority_brief_count" not in bundle.to_dict()
    assert "research_queue_brief_count" not in bundle.to_dict()
    assert bundle.to_dict()["sma_research_observation_brief_count"] == 1


def test_all_families_empty_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one supported brief"):
        build_advisory_operating_brief_content_bundle()

    payload = _valid_constructor_payload()
    payload["candidate_research_briefs"] = ()
    payload["strategy_eligibility_briefs"] = ()
    payload["risk_authority_briefs"] = ()
    payload["research_queue_briefs"] = ()
    payload["sma_research_observation_briefs"] = ()
    with pytest.raises(ValidationError, match="at least one supported brief"):
        AdvisoryOperatingBriefContentBundle(**payload)


def test_candidate_family_identity_and_order_are_preserved() -> None:
    first = _candidate_brief_variant("First candidate research bundle metadata")
    second = _candidate_brief_variant("Second candidate research bundle metadata")

    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=[second, first],
    )
    payload = bundle.to_dict()

    assert bundle.candidate_research_briefs == (second, first)
    assert bundle.candidate_research_briefs[0] is second
    assert bundle.candidate_research_briefs[1] is first
    assert payload["candidate_research_briefs"] == [
        second.to_dict(),
        first.to_dict(),
    ]


def test_strategy_eligibility_family_identity_and_order_are_preserved() -> None:
    first = build_synthetic_strategy_eligibility_brief()
    second = _second_strategy_eligibility_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        strategy_eligibility_briefs=[second, first],
    )
    payload = bundle.to_dict()

    assert bundle.strategy_eligibility_briefs == (second, first)
    assert bundle.strategy_eligibility_briefs[0] is second
    assert bundle.strategy_eligibility_briefs[1] is first
    assert payload["strategy_eligibility_briefs"] == [
        second.to_dict(),
        first.to_dict(),
    ]


def test_risk_authority_family_identity_and_order_are_preserved() -> None:
    first = build_synthetic_risk_authority_brief()
    second = _second_risk_authority_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        risk_authority_briefs=[second, first],
    )
    payload = bundle.to_dict()

    assert bundle.risk_authority_briefs == (second, first)
    assert bundle.risk_authority_briefs[0] is second
    assert bundle.risk_authority_briefs[1] is first
    assert payload["risk_authority_briefs"] == [
        second.to_dict(),
        first.to_dict(),
    ]


def test_research_queue_family_identity_and_order_are_preserved() -> None:
    first = build_synthetic_research_queue_brief()
    second = _second_research_queue_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        research_queue_briefs=[second, first],
    )
    payload = bundle.to_dict()

    assert bundle.research_queue_briefs == (second, first)
    assert bundle.research_queue_briefs[0] is second
    assert bundle.research_queue_briefs[1] is first
    assert payload["research_queue_briefs"] == [
        second.to_dict(),
        first.to_dict(),
    ]


def test_sma_research_observation_family_identity_and_order_are_preserved() -> None:
    first = build_synthetic_sma_research_observation_brief()
    second = _second_sma_research_observation_brief()

    bundle = build_advisory_operating_brief_content_bundle(
        sma_research_observation_briefs=[second, first],
    )
    payload = bundle.to_dict()

    assert bundle.sma_research_observation_briefs == (second, first)
    assert bundle.sma_research_observation_briefs[0] is second
    assert bundle.sma_research_observation_briefs[1] is first
    assert payload["sma_research_observation_briefs"] == [
        second.to_dict(),
        first.to_dict(),
    ]


def test_brief_collections_are_converted_to_immutable_tuples() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()
    risk_brief = build_synthetic_risk_authority_brief()
    research_queue_brief = build_synthetic_research_queue_brief()
    sma_brief = build_synthetic_sma_research_observation_brief()
    payload = _valid_constructor_payload(
        candidate_brief,
        eligibility_brief,
        risk_brief,
        research_queue_brief,
        sma_brief,
    )
    payload["candidate_research_briefs"] = [candidate_brief]
    payload["strategy_eligibility_briefs"] = [eligibility_brief]
    payload["risk_authority_briefs"] = [risk_brief]
    payload["research_queue_briefs"] = [research_queue_brief]
    payload["sma_research_observation_briefs"] = [sma_brief]

    bundle = AdvisoryOperatingBriefContentBundle(**payload)

    assert isinstance(bundle.candidate_research_briefs, tuple)
    assert isinstance(bundle.strategy_eligibility_briefs, tuple)
    assert isinstance(bundle.risk_authority_briefs, tuple)
    assert isinstance(bundle.research_queue_briefs, tuple)
    assert isinstance(bundle.sma_research_observation_briefs, tuple)
    assert bundle.candidate_research_briefs == (candidate_brief,)
    assert bundle.strategy_eligibility_briefs == (eligibility_brief,)
    assert bundle.risk_authority_briefs == (risk_brief,)
    assert bundle.research_queue_briefs == (research_queue_brief,)
    assert bundle.sma_research_observation_briefs == (sma_brief,)


def test_duplicate_object_identities_are_rejected() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()
    risk_brief = build_synthetic_risk_authority_brief()
    research_queue_brief = build_synthetic_research_queue_brief()
    sma_brief = build_synthetic_sma_research_observation_brief()

    with pytest.raises(ValidationError, match="duplicate brief identities"):
        build_advisory_operating_brief_content_bundle(
            candidate_research_briefs=[candidate_brief, candidate_brief],
        )

    with pytest.raises(ValidationError, match="duplicate brief identities"):
        build_advisory_operating_brief_content_bundle(
            strategy_eligibility_briefs=[eligibility_brief, eligibility_brief],
        )

    with pytest.raises(ValidationError, match="duplicate brief identities"):
        build_advisory_operating_brief_content_bundle(
            risk_authority_briefs=[risk_brief, risk_brief],
        )

    with pytest.raises(ValidationError, match="duplicate brief identities"):
        build_advisory_operating_brief_content_bundle(
            research_queue_briefs=[research_queue_brief, research_queue_brief],
        )

    with pytest.raises(ValidationError, match="duplicate brief identities"):
        build_advisory_operating_brief_content_bundle(
            sma_research_observation_briefs=[sma_brief, sma_brief],
        )

    with pytest.raises(ValidationError, match="duplicate brief identities"):
        _validate_unique_brief_identities_for_test(
            (candidate_brief,),
            (),
            (),
            (candidate_brief,),  # type: ignore[arg-type]
            (),
        )

    with pytest.raises(ValidationError, match="duplicate brief identities"):
        _validate_unique_brief_identities_for_test(
            (candidate_brief,),
            (),
            (),
            (),
            (candidate_brief,),  # type: ignore[arg-type]
        )


def test_duplicate_guard_uses_both_supported_collections() -> None:
    function = _function_def("_validate_unique_brief_identities")
    loaded_names = {
        node.id
        for node in ast.walk(function)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }

    assert "candidate_research_briefs" in loaded_names
    assert "strategy_eligibility_briefs" in loaded_names
    assert "risk_authority_briefs" in loaded_names
    assert "research_queue_briefs" in loaded_names
    assert "sma_research_observation_briefs" in loaded_names
    assert "seen_identities" in loaded_names


def test_non_brief_and_malformed_brief_like_inputs_are_rejected() -> None:
    class CandidateBriefLike:
        brief_type = "candidate_research_brief"
        status = "candidate_only"
        title = "Candidate research brief metadata"
        limitations = ("synthetic metadata only",)
        non_claims = ("not synthetic claim",)

        def to_dict(self) -> dict[str, object]:
            return {"brief_type": self.brief_type}

    class StrategyEligibilityBriefLike:
        brief_type = "strategy_eligibility_brief"
        status = "candidate_only"
        authority = "advisory_only"
        capital_authority = False
        title = "Strategy eligibility brief metadata"
        summary = "Advisory brief contains synthetic metadata."
        limitations = ("synthetic metadata only",)
        non_claims = ("not synthetic claim",)

        def to_dict(self) -> dict[str, object]:
            return {"brief_type": self.brief_type}

    class RiskAuthorityBriefLike:
        brief_type = "risk_authority_brief"
        status = "candidate_only"
        authority = "advisory_only"
        capital_authority = False
        title = "Advisory risk metadata brief: 1 section"
        summary = "Advisory brief contains synthetic risk metadata."
        limitations = ("synthetic metadata only",)
        non_claims = ("not synthetic claim",)

        def to_dict(self) -> dict[str, object]:
            return {"brief_type": self.brief_type}

    class ResearchQueueBriefLike:
        brief_type = "research_queue_brief"
        status = "candidate_only"
        authority = "advisory_only"
        capital_authority = False
        title = "Research queue brief: 1 section"
        summary = "Research queue brief contains synthetic metadata."
        limitations = ("synthetic metadata only",)
        non_claims = ("not synthetic claim",)

        def to_dict(self) -> dict[str, object]:
            return {"brief_type": self.brief_type}

    class SmaResearchObservationBriefLike:
        brief_type = "sma_research_observation_brief"
        status = "candidate_only"
        authority = "advisory_only"
        capital_authority = False
        title = "SMA research observation brief metadata"
        summary = "SMA research observation brief contains synthetic metadata."
        limitations = ("synthetic metadata only",)
        non_claims = ("not synthetic claim",)

        def to_dict(self) -> dict[str, object]:
            return {"brief_type": self.brief_type}

    class DerivedRiskAuthorityBrief(RiskAuthorityBrief):
        pass

    class DerivedResearchQueueBrief(ResearchQueueBrief):
        pass

    class DerivedSmaResearchObservationBrief(SmaResearchObservationBrief):
        pass

    source_risk = build_synthetic_risk_authority_brief()
    subclass_risk = DerivedRiskAuthorityBrief(
        brief_type=source_risk.brief_type,
        status=source_risk.status,
        authority=source_risk.authority,
        capital_authority=source_risk.capital_authority,
        title=source_risk.title,
        summary=source_risk.summary,
        sections=source_risk.sections,
        limitations=source_risk.limitations,
        non_claims=source_risk.non_claims,
    )
    source_research_queue = build_synthetic_research_queue_brief()
    subclass_research_queue = DerivedResearchQueueBrief(
        brief_type=source_research_queue.brief_type,
        status=source_research_queue.status,
        authority=source_research_queue.authority,
        capital_authority=source_research_queue.capital_authority,
        title=source_research_queue.title,
        summary=source_research_queue.summary,
        sections=source_research_queue.sections,
        limitations=source_research_queue.limitations,
        non_claims=source_research_queue.non_claims,
    )
    source_sma = build_synthetic_sma_research_observation_brief()
    subclass_sma = DerivedSmaResearchObservationBrief(
        brief_type=source_sma.brief_type,
        status=source_sma.status,
        authority=source_sma.authority,
        capital_authority=source_sma.capital_authority,
        brief_id=source_sma.brief_id,
        title=source_sma.title,
        summary=source_sma.summary,
        sections=source_sma.sections,
        limitations=source_sma.limitations,
        non_claims=source_sma.non_claims,
    )

    with pytest.raises(ValidationError, match="CandidateResearchBrief"):
        build_advisory_operating_brief_content_bundle(
            candidate_research_briefs=[object()],
        )

    with pytest.raises(ValidationError, match="CandidateResearchBrief"):
        build_advisory_operating_brief_content_bundle(
            candidate_research_briefs=[CandidateBriefLike()],
        )

    with pytest.raises(ValidationError, match="StrategyEligibilityBrief"):
        build_advisory_operating_brief_content_bundle(
            strategy_eligibility_briefs=[object()],
        )

    with pytest.raises(ValidationError, match="StrategyEligibilityBrief"):
        build_advisory_operating_brief_content_bundle(
            strategy_eligibility_briefs=[StrategyEligibilityBriefLike()],
        )

    with pytest.raises(ValidationError, match="RiskAuthorityBrief"):
        build_advisory_operating_brief_content_bundle(
            risk_authority_briefs=[object()],
        )

    with pytest.raises(ValidationError, match="RiskAuthorityBrief"):
        build_advisory_operating_brief_content_bundle(
            risk_authority_briefs=[RiskAuthorityBriefLike()],
        )

    with pytest.raises(ValidationError, match="RiskAuthorityBrief"):
        build_advisory_operating_brief_content_bundle(
            risk_authority_briefs=[subclass_risk],
        )

    with pytest.raises(ValidationError, match="RiskAuthorityBrief"):
        build_advisory_operating_brief_content_bundle(
            risk_authority_briefs=[build_synthetic_candidate_research_brief()],
        )

    with pytest.raises(ValidationError, match="ResearchQueueBrief"):
        build_advisory_operating_brief_content_bundle(
            research_queue_briefs=[object()],
        )

    with pytest.raises(ValidationError, match="ResearchQueueBrief"):
        build_advisory_operating_brief_content_bundle(
            research_queue_briefs=[ResearchQueueBriefLike()],
        )

    with pytest.raises(ValidationError, match="ResearchQueueBrief"):
        build_advisory_operating_brief_content_bundle(
            research_queue_briefs=[subclass_research_queue],
        )

    with pytest.raises(ValidationError, match="ResearchQueueBrief"):
        build_advisory_operating_brief_content_bundle(
            research_queue_briefs=[build_synthetic_candidate_research_brief()],
        )

    with pytest.raises(ValidationError, match="SmaResearchObservationBrief"):
        build_advisory_operating_brief_content_bundle(
            sma_research_observation_briefs=[object()],
        )

    with pytest.raises(ValidationError, match="SmaResearchObservationBrief"):
        build_advisory_operating_brief_content_bundle(
            sma_research_observation_briefs=[SmaResearchObservationBriefLike()],
        )

    with pytest.raises(ValidationError, match="SmaResearchObservationBrief"):
        build_advisory_operating_brief_content_bundle(
            sma_research_observation_briefs=[subclass_sma],
        )

    with pytest.raises(ValidationError, match="SmaResearchObservationBrief"):
        build_advisory_operating_brief_content_bundle(
            sma_research_observation_briefs=[build_synthetic_candidate_research_brief()],
        )

    with pytest.raises(ValidationError, match="iterable"):
        build_advisory_operating_brief_content_bundle(
            candidate_research_briefs=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError, match="iterable"):
        build_advisory_operating_brief_content_bundle(
            strategy_eligibility_briefs=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError, match="iterable"):
        build_advisory_operating_brief_content_bundle(
            risk_authority_briefs=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError, match="iterable"):
        build_advisory_operating_brief_content_bundle(
            research_queue_briefs=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError, match="iterable"):
        build_advisory_operating_brief_content_bundle(
            sma_research_observation_briefs=object(),  # type: ignore[arg-type]
        )


def test_fixed_bundle_metadata_values_are_pinned() -> None:
    bundle = _combined_bundle()
    all_family_bundle = _all_family_bundle()
    payload = bundle.to_dict()
    all_family_payload = all_family_bundle.to_dict()

    assert bundle.bundle_type == "advisory_operating_brief_content_bundle"
    assert bundle.status == "candidate_only"
    assert bundle.authority == "advisory_only"
    assert bundle.capital_authority is False
    assert payload["bundle_type"] == "advisory_operating_brief_content_bundle"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert all_family_payload["bundle_type"] == (
        "advisory_operating_brief_content_bundle"
    )
    assert all_family_payload["status"] == "candidate_only"
    assert all_family_payload["authority"] == "advisory_only"
    assert all_family_payload["capital_authority"] is False

    for field_name, value in (
        ("bundle_type", "advisory_operating_brief"),
        ("status", "research_only"),
        ("authority", "capital_authority"),
        ("capital_authority", True),
    ):
        constructor_payload = _valid_constructor_payload()
        constructor_payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            AdvisoryOperatingBriefContentBundle(**constructor_payload)


def test_title_and_summary_are_deterministic_and_advisory_only() -> None:
    first = _combined_bundle()
    second = _combined_bundle()
    all_family = _all_family_bundle()
    research_queue_family = _research_queue_family_bundle()
    sma_family = _sma_family_bundle()

    assert first.title == second.title == _EXPECTED_COMBINED_BUNDLE_DICT["title"]
    assert first.summary == second.summary == _EXPECTED_COMBINED_BUNDLE_DICT["summary"]
    assert all_family.title == _EXPECTED_ALL_FAMILY_BUNDLE_DICT["title"]
    assert all_family.summary == _EXPECTED_ALL_FAMILY_BUNDLE_DICT["summary"]
    assert research_queue_family.title == (
        _EXPECTED_RESEARCH_QUEUE_FAMILY_BUNDLE_DICT["title"]
    )
    assert research_queue_family.summary == (
        _EXPECTED_RESEARCH_QUEUE_FAMILY_BUNDLE_DICT["summary"]
    )
    assert sma_family.title == _EXPECTED_SMA_FAMILY_BUNDLE_DICT["title"]
    assert sma_family.summary == _EXPECTED_SMA_FAMILY_BUNDLE_DICT["summary"]
    for text in (
        first.title,
        first.summary,
        all_family.title,
        all_family.summary,
        research_queue_family.title,
        research_queue_family.summary,
        sma_family.title,
        sma_family.summary,
    ):
        lowered = text.lower()
        for token in _FORBIDDEN_TEXT_TOKENS:
            assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", lowered) is None

    for field_name, value in (
        ("title", "Candidate metadata"),
        ("summary", "Candidate metadata"),
    ):
        constructor_payload = _valid_constructor_payload()
        constructor_payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            AdvisoryOperatingBriefContentBundle(**constructor_payload)


def test_to_dict_exact_output_and_compact_json_are_pinned_for_combined_case() -> None:
    bundle = _combined_bundle()
    payload = bundle.to_dict()
    compact_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert payload == _EXPECTED_COMBINED_BUNDLE_DICT
    assert tuple(payload) == tuple(_EXPECTED_COMBINED_BUNDLE_DICT)
    assert "research_queue_brief_count" not in payload
    assert "research_queue_briefs" not in payload
    assert compact_json == _EXPECTED_COMPACT_JSON
    assert json.loads(compact_json) == payload
    _assert_primitive_only(payload)

    payload["candidate_research_briefs"][0]["limitations"].append(
        "mutated primitive copy"
    )
    payload["strategy_eligibility_briefs"][0]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive copy")

    assert bundle.to_dict() == _EXPECTED_COMBINED_BUNDLE_DICT


def test_to_dict_exact_output_and_compact_json_are_pinned_for_all_family_case() -> None:
    bundle = _all_family_bundle()
    payload = bundle.to_dict()
    compact_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert payload == _EXPECTED_ALL_FAMILY_BUNDLE_DICT
    assert tuple(payload) == tuple(_EXPECTED_ALL_FAMILY_BUNDLE_DICT)
    assert "research_queue_brief_count" not in payload
    assert "research_queue_briefs" not in payload
    assert compact_json == _EXPECTED_ALL_FAMILY_COMPACT_JSON
    assert json.loads(compact_json) == payload
    assert payload["risk_authority_briefs"][0] == (
        expected_synthetic_risk_authority_brief_dict()
    )
    _assert_primitive_only(payload)

    payload["risk_authority_briefs"][0]["sections"][0]["limitations"].append(
        "mutated primitive copy"
    )
    payload["risk_authority_briefs"][0]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive copy")

    assert bundle.to_dict() == _EXPECTED_ALL_FAMILY_BUNDLE_DICT


def test_to_dict_exact_output_and_compact_json_are_pinned_for_research_queue_case() -> (
    None
):
    bundle = _research_queue_family_bundle()
    payload = bundle.to_dict()
    compact_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert payload == _EXPECTED_RESEARCH_QUEUE_FAMILY_BUNDLE_DICT
    assert tuple(payload) == tuple(_EXPECTED_RESEARCH_QUEUE_FAMILY_BUNDLE_DICT)
    assert compact_json == _EXPECTED_RESEARCH_QUEUE_FAMILY_COMPACT_JSON
    assert json.loads(compact_json) == payload
    assert payload["research_queue_briefs"][0] == (
        expected_synthetic_research_queue_brief_dict()
    )
    _assert_primitive_only(payload)

    payload["research_queue_briefs"][0]["sections"][0]["limitations"].append(
        "mutated primitive copy"
    )
    payload["research_queue_briefs"][0]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive copy")

    assert bundle.to_dict() == _EXPECTED_RESEARCH_QUEUE_FAMILY_BUNDLE_DICT


def test_to_dict_exact_output_and_compact_json_are_pinned_for_sma_case() -> None:
    bundle = _sma_family_bundle()
    payload = bundle.to_dict()
    compact_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert payload == _EXPECTED_SMA_FAMILY_BUNDLE_DICT
    assert tuple(payload) == tuple(_EXPECTED_SMA_FAMILY_BUNDLE_DICT)
    assert compact_json == _EXPECTED_SMA_FAMILY_COMPACT_JSON
    assert json.loads(compact_json) == payload
    assert payload["sma_research_observation_briefs"][0] == (
        expected_synthetic_sma_research_observation_brief_dict()
    )
    _assert_primitive_only(payload)

    payload["sma_research_observation_briefs"][0]["sections"][0][
        "limitations"
    ].append("mutated primitive copy")
    payload["sma_research_observation_briefs"][0]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive copy")

    assert bundle.to_dict() == _EXPECTED_SMA_FAMILY_BUNDLE_DICT


def test_repeated_construction_is_deterministic() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()
    risk_brief = build_synthetic_risk_authority_brief()
    research_queue_brief = build_synthetic_research_queue_brief()
    sma_brief = build_synthetic_sma_research_observation_brief()

    first = build_advisory_operating_brief_content_bundle(
        [candidate_brief],
        [eligibility_brief],
        [risk_brief],
        [research_queue_brief],
        [sma_brief],
    )
    second = build_advisory_operating_brief_content_bundle(
        [candidate_brief],
        [eligibility_brief],
        [risk_brief],
        [research_queue_brief],
        [sma_brief],
    )
    third = _sma_family_bundle()
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_json = json.dumps(first_payload, ensure_ascii=True, separators=(",", ":"))
    second_json = json.dumps(second_payload, ensure_ascii=True, separators=(",", ":"))

    assert first is not second
    assert first.candidate_research_briefs[0] is second.candidate_research_briefs[0]
    assert first.strategy_eligibility_briefs[0] is (
        second.strategy_eligibility_briefs[0]
    )
    assert first.risk_authority_briefs[0] is second.risk_authority_briefs[0]
    assert first.research_queue_briefs[0] is second.research_queue_briefs[0]
    assert first.sma_research_observation_briefs[0] is (
        second.sma_research_observation_briefs[0]
    )
    assert first_payload == second_payload == third.to_dict()
    assert first_json == second_json == _EXPECTED_SMA_FAMILY_COMPACT_JSON


def test_source_briefs_are_not_mutated() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()
    risk_brief = build_synthetic_risk_authority_brief()
    research_queue_brief = build_synthetic_research_queue_brief()
    sma_brief = build_synthetic_sma_research_observation_brief()
    candidate_before = candidate_brief.to_dict()
    eligibility_before = eligibility_brief.to_dict()
    risk_before = risk_brief.to_dict()
    research_queue_before = research_queue_brief.to_dict()
    sma_before = sma_brief.to_dict()
    identity_snapshot = (
        id(candidate_brief),
        id(candidate_brief.sections),
        id(candidate_brief.limitations),
        id(candidate_brief.non_claims),
        id(eligibility_brief),
        id(eligibility_brief.sections),
        id(eligibility_brief.limitations),
        id(eligibility_brief.non_claims),
        id(risk_brief),
        id(risk_brief.sections),
        id(risk_brief.limitations),
        id(risk_brief.non_claims),
        id(research_queue_brief),
        id(research_queue_brief.sections),
        id(research_queue_brief.limitations),
        id(research_queue_brief.non_claims),
        id(sma_brief),
        id(sma_brief.sections),
        id(sma_brief.limitations),
        id(sma_brief.non_claims),
    )

    bundle = build_advisory_operating_brief_content_bundle(
        [candidate_brief],
        [eligibility_brief],
        [risk_brief],
        [research_queue_brief],
        [sma_brief],
    )
    payload = bundle.to_dict()

    payload["candidate_research_briefs"][0]["sections"][0]["limitations"].append(
        "mutated primitive copy"
    )
    payload["strategy_eligibility_briefs"][0]["sections"][0]["items"][0][
        "source_status"
    ]["non_claims"].append("not mutated primitive copy")
    payload["risk_authority_briefs"][0]["sections"][0]["items"][0][
        "source_status"
    ]["non_claims"].append("not mutated primitive copy")
    payload["research_queue_briefs"][0]["sections"][0]["items"][0][
        "source_status"
    ]["non_claims"].append("not mutated primitive copy")
    payload["sma_research_observation_briefs"][0]["sections"][0]["items"][0][
        "source_observation"
    ]["non_claims"].append("not mutated primitive copy")
    payload["limitations"].append("mutated primitive copy")

    assert candidate_brief.to_dict() == candidate_before
    assert eligibility_brief.to_dict() == eligibility_before
    assert risk_brief.to_dict() == risk_before
    assert research_queue_brief.to_dict() == research_queue_before
    assert sma_brief.to_dict() == sma_before
    assert (
        id(candidate_brief),
        id(candidate_brief.sections),
        id(candidate_brief.limitations),
        id(candidate_brief.non_claims),
        id(eligibility_brief),
        id(eligibility_brief.sections),
        id(eligibility_brief.limitations),
        id(eligibility_brief.non_claims),
        id(risk_brief),
        id(risk_brief.sections),
        id(risk_brief.limitations),
        id(risk_brief.non_claims),
        id(research_queue_brief),
        id(research_queue_brief.sections),
        id(research_queue_brief.limitations),
        id(research_queue_brief.non_claims),
        id(sma_brief),
        id(sma_brief.sections),
        id(sma_brief.limitations),
        id(sma_brief.non_claims),
    ) == identity_snapshot
    assert bundle.candidate_research_briefs[0] is candidate_brief
    assert bundle.strategy_eligibility_briefs[0] is eligibility_brief
    assert bundle.risk_authority_briefs[0] is risk_brief
    assert bundle.research_queue_briefs[0] is research_queue_brief
    assert bundle.sma_research_observation_briefs[0] is sma_brief


def test_nested_strategy_eligibility_brief_dictionary_matches_phase_160_helper() -> (
    None
):
    bundle = _combined_bundle()

    assert bundle.to_dict()["strategy_eligibility_briefs"][0] == (
        expected_synthetic_strategy_eligibility_brief_dict()
    )


def test_nested_risk_authority_brief_dictionary_matches_phase_176_helper() -> None:
    bundle = _all_family_bundle()

    assert bundle.to_dict()["risk_authority_briefs"][0] == (
        expected_synthetic_risk_authority_brief_dict()
    )


def test_nested_research_queue_brief_dictionary_matches_phase_183_helper() -> None:
    bundle = _research_queue_family_bundle()

    assert bundle.to_dict()["research_queue_briefs"][0] == (
        expected_synthetic_research_queue_brief_dict()
    )


def test_nested_sma_research_observation_brief_dictionary_matches_phase_202_helper() -> (
    None
):
    bundle = _sma_family_bundle()

    assert bundle.to_dict()["sma_research_observation_briefs"][0] == (
        expected_synthetic_sma_research_observation_brief_dict()
    )


def test_nested_candidate_research_brief_dictionary_matches_existing_helper() -> None:
    bundle = _combined_bundle()

    assert bundle.to_dict()["candidate_research_briefs"][0] == (
        expected_synthetic_candidate_research_brief_dict()
    )


def test_limitations_and_non_claims_are_carried_forward_in_order() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    eligibility_brief = build_synthetic_strategy_eligibility_brief()
    risk_brief = build_synthetic_risk_authority_brief()
    research_queue_brief = build_synthetic_research_queue_brief()
    sma_brief = build_synthetic_sma_research_observation_brief()
    bundle = build_advisory_operating_brief_content_bundle(
        [candidate_brief],
        [eligibility_brief],
        [risk_brief],
        [research_queue_brief],
        [sma_brief],
    )

    assert bundle.limitations == _EXPECTED_SMA_FAMILY_LIMITATIONS
    assert bundle.non_claims == _EXPECTED_SMA_FAMILY_NON_CLAIMS
    assert all(value in bundle.limitations for value in candidate_brief.limitations)
    assert all(value in bundle.limitations for value in eligibility_brief.limitations)
    assert all(value in bundle.limitations for value in risk_brief.limitations)
    assert all(
        value in bundle.limitations for value in research_queue_brief.limitations
    )
    assert all(value in bundle.limitations for value in sma_brief.limitations)
    assert all(value in bundle.non_claims for value in candidate_brief.non_claims)
    assert all(value in bundle.non_claims for value in eligibility_brief.non_claims)
    assert all(value in bundle.non_claims for value in risk_brief.non_claims)
    assert all(
        value in bundle.non_claims for value in research_queue_brief.non_claims
    )
    assert all(value in bundle.non_claims for value in sma_brief.non_claims)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("status", "paper_eligible"),
        ("status", "live_probe_eligible"),
        ("status", "live_authorized"),
        ("status", "trading_ready"),
        ("status", "approved"),
        ("title", "paper_eligible"),
        ("title", "live_probe_eligible"),
        ("title", "live_authorized"),
        ("title", "trading_ready"),
        ("title", "approved"),
        ("summary", "paper_eligible"),
        ("summary", "live_probe_eligible"),
        ("summary", "live_authorized"),
        ("summary", "trading_ready"),
        ("summary", "approved"),
    ),
)
def test_paper_live_approved_and_trading_ready_states_remain_impossible(
    field_name: str,
    value: str,
) -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        AdvisoryOperatingBriefContentBundle(**constructor_payload)


def test_bundle_is_frozen_slotted_and_has_no_from_dict() -> None:
    bundle = _combined_bundle()

    assert hasattr(AdvisoryOperatingBriefContentBundle, "__slots__")
    assert not hasattr(bundle, "__dict__")
    assert not hasattr(AdvisoryOperatingBriefContentBundle, "from_dict")
    assert "from_dict" not in _function_names()
    with pytest.raises(FrozenInstanceError):
        bundle.summary = "changed"


def test_no_actionable_trading_authority_fields_are_exposed() -> None:
    bundle = _all_family_bundle()
    payload = bundle.to_dict()
    field_names = {field.name for field in fields(AdvisoryOperatingBriefContentBundle)}
    ast_fields = _bundle_ast_fields()
    ast_dict_keys = _to_dict_string_keys()
    top_level_payload_keys = set(payload)

    assert tuple(field.name for field in fields(AdvisoryOperatingBriefContentBundle)) == (
        "bundle_type",
        "status",
        "authority",
        "capital_authority",
        "title",
        "summary",
        "candidate_research_briefs",
        "strategy_eligibility_briefs",
        "limitations",
        "non_claims",
        "risk_authority_briefs",
        "research_queue_briefs",
        "sma_research_observation_briefs",
    )
    assert tuple(payload) == tuple(_EXPECTED_ALL_FAMILY_BUNDLE_DICT)
    assert field_names.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_fields.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_dict_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert top_level_payload_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert all(
        not hasattr(bundle, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert bundle.status == "candidate_only"
    assert bundle.authority == "advisory_only"
    assert bundle.capital_authority is False


def test_module_imports_no_forbidden_vendor_network_runtime_or_trading_modules() -> (
    None
):
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_persistence_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_literals_do_not_add_actionable_authority_states() -> None:
    literals = _string_literals()
    lowered_source = _source_text().lower()

    assert literals.isdisjoint(_FORBIDDEN_EXACT_LITERALS)
    for token in _FORBIDDEN_SOURCE_TOKENS:
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", lowered_source) is None


def _combined_bundle() -> AdvisoryOperatingBriefContentBundle:
    return build_advisory_operating_brief_content_bundle(
        [build_synthetic_candidate_research_brief()],
        [build_synthetic_strategy_eligibility_brief()],
    )


def _all_family_bundle() -> AdvisoryOperatingBriefContentBundle:
    return build_advisory_operating_brief_content_bundle(
        [build_synthetic_candidate_research_brief()],
        [build_synthetic_strategy_eligibility_brief()],
        [build_synthetic_risk_authority_brief()],
    )


def _research_queue_family_bundle() -> AdvisoryOperatingBriefContentBundle:
    return build_advisory_operating_brief_content_bundle(
        [build_synthetic_candidate_research_brief()],
        [build_synthetic_strategy_eligibility_brief()],
        [build_synthetic_risk_authority_brief()],
        [build_synthetic_research_queue_brief()],
    )


def _sma_family_bundle() -> AdvisoryOperatingBriefContentBundle:
    return build_advisory_operating_brief_content_bundle(
        [build_synthetic_candidate_research_brief()],
        [build_synthetic_strategy_eligibility_brief()],
        [build_synthetic_risk_authority_brief()],
        [build_synthetic_research_queue_brief()],
        [build_synthetic_sma_research_observation_brief()],
    )


def _valid_constructor_payload(
    candidate_brief: CandidateResearchBrief | None = None,
    eligibility_brief: StrategyEligibilityBrief | None = None,
    risk_brief: RiskAuthorityBrief | None = None,
    research_queue_brief: ResearchQueueBrief | None = None,
    sma_brief: SmaResearchObservationBrief | None = None,
) -> dict[str, object]:
    source_candidate = candidate_brief or build_synthetic_candidate_research_brief()
    source_eligibility = eligibility_brief or build_synthetic_strategy_eligibility_brief()
    source_risk = risk_brief or build_synthetic_risk_authority_brief()
    source_research_queue = (
        research_queue_brief or build_synthetic_research_queue_brief()
    )
    source_sma = sma_brief or build_synthetic_sma_research_observation_brief()
    bundle = build_advisory_operating_brief_content_bundle(
        [source_candidate],
        [source_eligibility],
        [source_risk],
        [source_research_queue],
        [source_sma],
    )
    return {
        "bundle_type": bundle.bundle_type,
        "status": bundle.status,
        "authority": bundle.authority,
        "capital_authority": bundle.capital_authority,
        "title": bundle.title,
        "summary": bundle.summary,
        "candidate_research_briefs": bundle.candidate_research_briefs,
        "strategy_eligibility_briefs": bundle.strategy_eligibility_briefs,
        "limitations": bundle.limitations,
        "non_claims": bundle.non_claims,
        "risk_authority_briefs": bundle.risk_authority_briefs,
        "research_queue_briefs": bundle.research_queue_briefs,
        "sma_research_observation_briefs": bundle.sma_research_observation_briefs,
    }


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
        strategy_id="synthetic-strategy-eligibility-bundle-002",
        strategy_name="Secondary synthetic bundle strategy metadata",
        eligibility_state="watchlist_only",
        reasons=("secondary strategy metadata is scoped to advisory display",),
        limitations=("synthetic metadata only", "secondary bundle metadata only"),
        non_claims=(
            "not validation",
            "not paper readiness",
            "not live readiness",
            _s("not a tra", "ding recommendation"),
            _s("not allo", "cation authority"),
            _s("not or", "der authority"),
            "not secondary bundle metadata claim",
        ),
        evidence_refs=("synthetic-bundle-evidence-ref-002",),
        required_next_steps=("complete secondary metadata review before any claim",),
    )
    item = build_strategy_eligibility_brief_item(status)
    section = build_strategy_eligibility_brief_section((item,))
    return build_strategy_eligibility_brief((section,))


def _second_risk_authority_brief() -> RiskAuthorityBrief:
    status = build_risk_authority_status(
        authority_state="blocked",
        reasons=("secondary risk authority metadata is scoped to advisory display",),
        blockers=("secondary risk review is incomplete",),
        required_next_steps=("complete secondary risk metadata review",),
        limitations=("synthetic metadata only", "secondary risk bundle metadata only"),
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
            "not secondary risk metadata claim",
        ),
        evidence_refs=("synthetic-secondary-risk-authority-evidence-ref-001",),
        related_strategy_ids=("synthetic-risk-authority-strategy-002",),
    )
    item = build_risk_authority_brief_item(status)
    section = build_risk_authority_brief_section((item,))
    return build_risk_authority_brief((section,))


def _second_research_queue_brief() -> ResearchQueueBrief:
    status = build_research_queue_status(
        queue_id="research-queue:secondary:candidate",
        title="Secondary research queue bundle metadata",
        research_state="ready_for_scoping",
        priority_bucket="low",
        topic="secondary_research_queue_metadata",
        hypothesis="secondary research queue metadata remains candidate only",
        blockers=("secondary evidence is unresolved",),
        required_next_steps=("complete secondary metadata scoping",),
        evidence_gaps=("secondary evidence gap remains unresolved",),
        limitations=(
            "synthetic metadata only",
            "secondary research queue bundle metadata only",
        ),
        non_claims=(
            "not a recommendation",
            _s("not allo", "cation authority"),
            _s("not or", "der authority"),
            "not paper readiness",
            "not live readiness",
            _s("not bro", "ker authority"),
            _s("not ac", "count authority"),
            _s("not port", "folio mutation authority"),
            "not capital authority",
            "not trading authority",
            "not secondary research queue metadata claim",
        ),
        evidence_refs=("synthetic-secondary-research-queue-evidence-ref-001",),
        related_strategy_ids=("synthetic-research-queue-strategy-002",),
    )
    item = build_research_queue_brief_item(status)
    section = build_research_queue_brief_section((item,))
    return build_research_queue_brief((section,))


def _second_sma_research_observation_brief() -> SmaResearchObservationBrief:
    brief = build_synthetic_sma_research_observation_brief()
    return SmaResearchObservationBrief(
        brief_type=brief.brief_type,
        status=brief.status,
        authority=brief.authority,
        capital_authority=brief.capital_authority,
        brief_id="sma-research-observation-brief:synthetic:secondary",
        title="Secondary synthetic SMA observation brief",
        summary="Secondary synthetic SMA observation metadata.",
        sections=brief.sections,
        limitations=brief.limitations,
        non_claims=brief.non_claims,
    )


def _validate_unique_brief_identities_for_test(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...],
    strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
    research_queue_briefs: tuple[ResearchQueueBrief, ...],
    sma_research_observation_briefs: tuple[SmaResearchObservationBrief, ...],
) -> None:
    bundle_module._validate_unique_brief_identities(
        candidate_research_briefs,
        strategy_eligibility_briefs,
        risk_authority_briefs,
        research_queue_briefs,
        sma_research_observation_briefs,
    )


def _assert_primitive_only(value: object) -> None:
    assert not isinstance(value, (tuple, set))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_only(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_primitive_only(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


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


def _bundle_ast_fields() -> set[str]:
    for node in ast.walk(_tree()):
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "AdvisoryOperatingBriefContentBundle"
        ):
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("AdvisoryOperatingBriefContentBundle class was not found.")


def _to_dict_string_keys() -> set[str]:
    keys: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == "to_dict":
            for nested in ast.walk(node):
                if isinstance(nested, ast.Dict):
                    for key in nested.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            keys.add(key.value)

    return keys


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _function_def(name: str) -> ast.FunctionDef:
    for node in ast.walk(_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node

    raise AssertionError(f"{name} function was not found.")


def _string_literals() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
