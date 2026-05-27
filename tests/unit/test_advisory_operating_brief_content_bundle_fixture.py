from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.candidate_research_brief import CandidateResearchBrief
from algotrader.research.research_return_observation_brief_container import (
    ResearchReturnObservationBrief,
)
from algotrader.research.research_queue_brief import ResearchQueueBrief
from algotrader.research.risk_authority_brief import RiskAuthorityBrief
from algotrader.research.sma_research_observation_brief_container import (
    SmaResearchObservationBrief,
)
from algotrader.research.strategy_eligibility_brief import StrategyEligibilityBrief
from tests.fixtures import advisory_operating_brief_content_bundle as fixture_module
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_risk,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation,
    build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation,
    expected_synthetic_advisory_operating_brief_content_bundle_dict,
    expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict,
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict,
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict,
    expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict,
)
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
    expected_synthetic_candidate_research_brief_dict,
)
from tests.fixtures.research_queue_brief import (
    build_synthetic_research_queue_brief,
    expected_synthetic_research_queue_brief_dict,
)
from tests.fixtures.research_return_observation_brief_container import (
    build_synthetic_research_return_observation_brief,
    expected_synthetic_research_return_observation_brief_dict,
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
    first: dict[str, object],
    second: dict[str, object],
    field_name: str,
    *remaining: dict[str, object],
) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for payload in (first, second, *remaining):
        for value in payload[field_name]:
            assert isinstance(value, str)
            if value in seen:
                continue
            values.append(value)
            seen.add(value)

    return tuple(values)


FIXTURE_PATH = Path("tests/fixtures/advisory_operating_brief_content_bundle.py")
_EXPECTED_CANDIDATE_BRIEF_DICT = expected_synthetic_candidate_research_brief_dict()
_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT = (
    expected_synthetic_strategy_eligibility_brief_dict()
)
_EXPECTED_RISK_AUTHORITY_BRIEF_DICT = expected_synthetic_risk_authority_brief_dict()
_EXPECTED_RESEARCH_QUEUE_BRIEF_DICT = expected_synthetic_research_queue_brief_dict()
_EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT = (
    expected_synthetic_sma_research_observation_brief_dict()
)
_EXPECTED_RESEARCH_RETURN_OBSERVATION_BRIEF_DICT = (
    expected_synthetic_research_return_observation_brief_dict()
)
_EXPECTED_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "limitations",
)
_EXPECTED_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "non_claims",
)
_EXPECTED_WITH_RISK_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "limitations",
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
)
_EXPECTED_WITH_RISK_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "non_claims",
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
)
_EXPECTED_WITH_RESEARCH_QUEUE_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "limitations",
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
)
_EXPECTED_WITH_RESEARCH_QUEUE_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "non_claims",
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
)
_EXPECTED_WITH_SMA_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "limitations",
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
    _EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT,
)
_EXPECTED_WITH_SMA_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "non_claims",
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
    _EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT,
)
_EXPECTED_WITH_RESEARCH_RETURN_LIMITATIONS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "limitations",
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
    _EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT,
    _EXPECTED_RESEARCH_RETURN_OBSERVATION_BRIEF_DICT,
)
_EXPECTED_WITH_RESEARCH_RETURN_NON_CLAIMS = _combined_expected_values(
    _EXPECTED_CANDIDATE_BRIEF_DICT,
    _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT,
    "non_claims",
    _EXPECTED_RISK_AUTHORITY_BRIEF_DICT,
    _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT,
    _EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT,
    _EXPECTED_RESEARCH_RETURN_OBSERVATION_BRIEF_DICT,
)
_EXPECTED_DICT = {
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
_EXPECTED_WITH_RISK_DICT = {
    "bundle_type": "advisory_operating_brief_content_bundle",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory operating brief content bundle metadata",
    "summary": (
        "Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        f"{len(_EXPECTED_WITH_RISK_LIMITATIONS)} limitation(s), and "
        f"{len(_EXPECTED_WITH_RISK_NON_CLAIMS)} non-claim(s)."
    ),
    "candidate_research_brief_count": 1,
    "strategy_eligibility_brief_count": 1,
    "risk_authority_brief_count": 1,
    "candidate_research_briefs": [_EXPECTED_CANDIDATE_BRIEF_DICT],
    "strategy_eligibility_briefs": [_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT],
    "risk_authority_briefs": [_EXPECTED_RISK_AUTHORITY_BRIEF_DICT],
    "limitations": list(_EXPECTED_WITH_RISK_LIMITATIONS),
    "non_claims": list(_EXPECTED_WITH_RISK_NON_CLAIMS),
}
_EXPECTED_WITH_RESEARCH_QUEUE_DICT = {
    "bundle_type": "advisory_operating_brief_content_bundle",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory operating brief content bundle metadata",
    "summary": (
        "Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        "1 research queue brief(s), "
        f"{len(_EXPECTED_WITH_RESEARCH_QUEUE_LIMITATIONS)} limitation(s), and "
        f"{len(_EXPECTED_WITH_RESEARCH_QUEUE_NON_CLAIMS)} non-claim(s)."
    ),
    "candidate_research_brief_count": 1,
    "strategy_eligibility_brief_count": 1,
    "risk_authority_brief_count": 1,
    "research_queue_brief_count": 1,
    "candidate_research_briefs": [_EXPECTED_CANDIDATE_BRIEF_DICT],
    "strategy_eligibility_briefs": [_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT],
    "risk_authority_briefs": [_EXPECTED_RISK_AUTHORITY_BRIEF_DICT],
    "research_queue_briefs": [_EXPECTED_RESEARCH_QUEUE_BRIEF_DICT],
    "limitations": list(_EXPECTED_WITH_RESEARCH_QUEUE_LIMITATIONS),
    "non_claims": list(_EXPECTED_WITH_RESEARCH_QUEUE_NON_CLAIMS),
}
_EXPECTED_WITH_SMA_DICT = {
    "bundle_type": "advisory_operating_brief_content_bundle",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory operating brief content bundle metadata",
    "summary": (
        "Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        "1 research queue brief(s), 1 SMA research observation brief(s), "
        f"{len(_EXPECTED_WITH_SMA_LIMITATIONS)} limitation(s), and "
        f"{len(_EXPECTED_WITH_SMA_NON_CLAIMS)} non-claim(s)."
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
    "limitations": list(_EXPECTED_WITH_SMA_LIMITATIONS),
    "non_claims": list(_EXPECTED_WITH_SMA_NON_CLAIMS),
}
_EXPECTED_WITH_RESEARCH_RETURN_DICT = {
    "bundle_type": "advisory_operating_brief_content_bundle",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory operating brief content bundle metadata",
    "summary": (
        "Advisory content bundle contains 1 candidate research brief(s), "
        "1 strategy eligibility brief(s), 1 risk authority brief(s), "
        "1 research queue brief(s), 1 SMA research observation brief(s), "
        "1 research return observation brief(s), "
        f"{len(_EXPECTED_WITH_RESEARCH_RETURN_LIMITATIONS)} limitation(s), and "
        f"{len(_EXPECTED_WITH_RESEARCH_RETURN_NON_CLAIMS)} non-claim(s)."
    ),
    "candidate_research_brief_count": 1,
    "strategy_eligibility_brief_count": 1,
    "risk_authority_brief_count": 1,
    "research_queue_brief_count": 1,
    "sma_research_observation_brief_count": 1,
    "research_return_observation_brief_count": 1,
    "candidate_research_briefs": [_EXPECTED_CANDIDATE_BRIEF_DICT],
    "strategy_eligibility_briefs": [_EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT],
    "risk_authority_briefs": [_EXPECTED_RISK_AUTHORITY_BRIEF_DICT],
    "research_queue_briefs": [_EXPECTED_RESEARCH_QUEUE_BRIEF_DICT],
    "sma_research_observation_briefs": [_EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT],
    "research_return_observation_briefs": [
        _EXPECTED_RESEARCH_RETURN_OBSERVATION_BRIEF_DICT
    ],
    "limitations": list(_EXPECTED_WITH_RESEARCH_RETURN_LIMITATIONS),
    "non_claims": list(_EXPECTED_WITH_RESEARCH_RETURN_NON_CLAIMS),
}
_EXPECTED_COMPACT_JSON_BYTES = json.dumps(
    _EXPECTED_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
).encode("ascii")
_EXPECTED_WITH_RESEARCH_QUEUE_COMPACT_JSON_BYTES = json.dumps(
    _EXPECTED_WITH_RESEARCH_QUEUE_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
).encode("ascii")
_EXPECTED_WITH_SMA_COMPACT_JSON_BYTES = json.dumps(
    _EXPECTED_WITH_SMA_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
).encode("ascii")
_EXPECTED_WITH_RESEARCH_RETURN_COMPACT_JSON_BYTES = json.dumps(
    _EXPECTED_WITH_RESEARCH_RETURN_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
).encode("ascii")
_TUPLE_FIELDS = ("limitations", "non_claims")
_FORBIDDEN_TEXT_TOKENS = (
    "profitability",
    "approval",
    "approved",
    "recommend",
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
    "algotrader.research.advisory_operating_brief_content_bundle",
    "tests.fixtures.candidate_research_brief",
    "tests.fixtures.research_data_source_readiness",
    "tests.fixtures.strategy_eligibility_brief",
}
_ALLOWED_CALL_NAMES = {
    "_combined_expected_values",
    "build_advisory_operating_brief_content_bundle",
    "build_synthetic_candidate_research_brief",
    "build_synthetic_strategy_eligibility_brief",
    "expected_synthetic_candidate_research_brief_dict",
    "expected_synthetic_research_data_source_readiness",
    "expected_synthetic_research_data_source_readiness_dict",
    "expected_synthetic_strategy_eligibility_brief_dict",
    "values.append",
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
_FORBIDDEN_LITERAL_SUBSTRINGS = (
    _s("bro", "ker"),
    _s("port", "folio"),
    _s("allo", "cation"),
)
_FORBIDDEN_SOURCE_TOKENS = (
    "paper_eligible",
    "live_probe_eligible",
    "live_authorized",
    "trading_ready",
    "approved",
    "buy",
    "sell",
    "hold",
    _s("or", "der"),
    _s("bro", "ker"),
    "account",
    _s("port", "folio"),
    _s("allo", "cation"),
    _s("tra", "ding_authority"),
)


def test_fixture_builds_advisory_operating_brief_content_bundle() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert len(bundle.candidate_research_briefs) == 1
    assert len(bundle.strategy_eligibility_briefs) == 1
    assert bundle.risk_authority_briefs == ()
    assert bundle.research_queue_briefs == ()
    assert bundle.sma_research_observation_briefs == ()
    assert isinstance(bundle.candidate_research_briefs[0], CandidateResearchBrief)
    assert isinstance(bundle.strategy_eligibility_briefs[0], StrategyEligibilityBrief)


def test_fixture_uses_existing_fixtures_and_phase_161_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_candidate = build_synthetic_candidate_research_brief()
    source_strategy = build_synthetic_strategy_eligibility_brief()

    assert fixture_module.build_synthetic_candidate_research_brief is (
        build_synthetic_candidate_research_brief
    )
    assert fixture_module.build_synthetic_strategy_eligibility_brief is (
        build_synthetic_strategy_eligibility_brief
    )
    assert fixture_module.build_advisory_operating_brief_content_bundle is (
        build_advisory_operating_brief_content_bundle
    )

    def recording_candidate_fixture() -> CandidateResearchBrief:
        calls.append(("candidate_fixture", source_candidate))
        return source_candidate

    def recording_strategy_fixture() -> StrategyEligibilityBrief:
        calls.append(("strategy_fixture", source_strategy))
        return source_strategy

    def recording_bundle_builder(
        candidate_research_briefs: tuple[CandidateResearchBrief, ...],
        strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
    ) -> AdvisoryOperatingBriefContentBundle:
        candidate_tuple = tuple(candidate_research_briefs)
        strategy_tuple = tuple(strategy_eligibility_briefs)
        calls.append(("bundle_builder", (candidate_tuple, strategy_tuple)))
        return build_advisory_operating_brief_content_bundle(
            candidate_research_briefs=candidate_tuple,
            strategy_eligibility_briefs=strategy_tuple,
        )

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief",
        recording_candidate_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_strategy_eligibility_brief",
        recording_strategy_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_advisory_operating_brief_content_bundle",
        recording_bundle_builder,
    )

    bundle = fixture_module.build_synthetic_advisory_operating_brief_content_bundle()

    assert [name for name, _ in calls] == [
        "candidate_fixture",
        "strategy_fixture",
        "bundle_builder",
    ]
    assert calls[0][1] is source_candidate
    assert calls[1][1] is source_strategy
    assert calls[2][1] == ((source_candidate,), (source_strategy,))
    assert bundle.candidate_research_briefs == (source_candidate,)
    assert bundle.strategy_eligibility_briefs == (source_strategy,)


def test_expected_helper_uses_existing_nested_expected_dictionaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    source_candidate_expected = expected_synthetic_candidate_research_brief_dict()
    source_strategy_expected = expected_synthetic_strategy_eligibility_brief_dict()

    def recording_expected_candidate() -> dict[str, object]:
        calls.append("candidate_expected")
        return source_candidate_expected

    def recording_expected_strategy() -> dict[str, object]:
        calls.append("strategy_expected")
        return source_strategy_expected

    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_candidate_research_brief_dict",
        recording_expected_candidate,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_strategy_eligibility_brief_dict",
        recording_expected_strategy,
    )

    expected = (
        fixture_module.expected_synthetic_advisory_operating_brief_content_bundle_dict()
    )

    assert calls == ["candidate_expected", "strategy_expected"]
    assert expected["candidate_research_briefs"][0] is source_candidate_expected
    assert expected["strategy_eligibility_briefs"][0] is source_strategy_expected
    assert expected["limitations"] == list(_EXPECTED_LIMITATIONS)
    assert expected["non_claims"] == list(_EXPECTED_NON_CLAIMS)
    assert expected["limitations"] is not source_candidate_expected["limitations"]
    assert expected["limitations"] is not source_strategy_expected["limitations"]
    assert expected["non_claims"] is not source_candidate_expected["non_claims"]
    assert expected["non_claims"] is not source_strategy_expected["non_claims"]


def test_fixture_output_matches_expected_dictionary_exactly() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    payload = bundle.to_dict()
    expected = expected_synthetic_advisory_operating_brief_content_bundle_dict()

    assert expected == _EXPECTED_DICT
    assert payload == expected
    assert tuple(payload) == tuple(_EXPECTED_DICT)
    assert "risk_authority_brief_count" not in payload
    assert "risk_authority_briefs" not in payload
    assert "research_queue_brief_count" not in payload
    assert "research_queue_briefs" not in payload
    assert "sma_research_observation_brief_count" not in payload
    assert "sma_research_observation_briefs" not in payload
    assert payload["candidate_research_briefs"][0] == _EXPECTED_CANDIDATE_BRIEF_DICT
    assert payload["strategy_eligibility_briefs"][0] == (
        _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT
    )
    _assert_primitive_only(payload)
    _assert_primitive_only(expected)


def test_risk_fixture_output_remains_exactly_unchanged() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    payload = bundle.to_dict()
    expected = expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict()

    assert expected == _EXPECTED_WITH_RISK_DICT
    assert payload == expected
    assert tuple(payload) == tuple(_EXPECTED_WITH_RISK_DICT)
    assert payload["risk_authority_briefs"][0] == _EXPECTED_RISK_AUTHORITY_BRIEF_DICT
    assert "research_queue_brief_count" not in payload
    assert "research_queue_briefs" not in payload
    assert "sma_research_observation_brief_count" not in payload
    assert "sma_research_observation_briefs" not in payload
    _assert_primitive_only(payload)
    _assert_primitive_only(expected)


def test_research_queue_fixture_builds_content_bundle_with_four_branches() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert len(bundle.candidate_research_briefs) == 1
    assert len(bundle.strategy_eligibility_briefs) == 1
    assert len(bundle.risk_authority_briefs) == 1
    assert len(bundle.research_queue_briefs) == 1
    assert bundle.sma_research_observation_briefs == ()
    assert isinstance(bundle.candidate_research_briefs[0], CandidateResearchBrief)
    assert isinstance(bundle.strategy_eligibility_briefs[0], StrategyEligibilityBrief)
    assert isinstance(bundle.risk_authority_briefs[0], RiskAuthorityBrief)
    assert isinstance(bundle.research_queue_briefs[0], ResearchQueueBrief)


def test_sma_fixture_builds_content_bundle_with_five_branches() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert len(bundle.candidate_research_briefs) == 1
    assert len(bundle.strategy_eligibility_briefs) == 1
    assert len(bundle.risk_authority_briefs) == 1
    assert len(bundle.research_queue_briefs) == 1
    assert len(bundle.sma_research_observation_briefs) == 1
    assert isinstance(bundle.candidate_research_briefs[0], CandidateResearchBrief)
    assert isinstance(bundle.strategy_eligibility_briefs[0], StrategyEligibilityBrief)
    assert isinstance(bundle.risk_authority_briefs[0], RiskAuthorityBrief)
    assert isinstance(bundle.research_queue_briefs[0], ResearchQueueBrief)
    assert isinstance(
        bundle.sma_research_observation_briefs[0],
        SmaResearchObservationBrief,
    )


def test_research_return_fixture_builds_content_bundle_with_six_branches() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation()
    )

    assert isinstance(bundle, AdvisoryOperatingBriefContentBundle)
    assert len(bundle.candidate_research_briefs) == 1
    assert len(bundle.strategy_eligibility_briefs) == 1
    assert len(bundle.risk_authority_briefs) == 1
    assert len(bundle.research_queue_briefs) == 1
    assert len(bundle.sma_research_observation_briefs) == 1
    assert len(bundle.research_return_observation_briefs) == 1
    assert isinstance(bundle.candidate_research_briefs[0], CandidateResearchBrief)
    assert isinstance(bundle.strategy_eligibility_briefs[0], StrategyEligibilityBrief)
    assert isinstance(bundle.risk_authority_briefs[0], RiskAuthorityBrief)
    assert isinstance(bundle.research_queue_briefs[0], ResearchQueueBrief)
    assert isinstance(
        bundle.sma_research_observation_briefs[0],
        SmaResearchObservationBrief,
    )
    assert isinstance(
        bundle.research_return_observation_briefs[0],
        ResearchReturnObservationBrief,
    )


def test_research_queue_fixture_uses_existing_fixtures_and_phase_184_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_candidate = build_synthetic_candidate_research_brief()
    source_strategy = build_synthetic_strategy_eligibility_brief()
    source_risk = build_synthetic_risk_authority_brief()
    source_research_queue = build_synthetic_research_queue_brief()

    def recording_candidate_fixture() -> CandidateResearchBrief:
        calls.append(("candidate_fixture", source_candidate))
        return source_candidate

    def recording_strategy_fixture() -> StrategyEligibilityBrief:
        calls.append(("strategy_fixture", source_strategy))
        return source_strategy

    def recording_risk_fixture() -> RiskAuthorityBrief:
        calls.append(("risk_fixture", source_risk))
        return source_risk

    def recording_research_queue_fixture() -> ResearchQueueBrief:
        calls.append(("research_queue_fixture", source_research_queue))
        return source_research_queue

    def recording_bundle_builder(
        candidate_research_briefs: tuple[CandidateResearchBrief, ...],
        strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
        risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
        research_queue_briefs: tuple[ResearchQueueBrief, ...],
    ) -> AdvisoryOperatingBriefContentBundle:
        candidate_tuple = tuple(candidate_research_briefs)
        strategy_tuple = tuple(strategy_eligibility_briefs)
        risk_tuple = tuple(risk_authority_briefs)
        research_queue_tuple = tuple(research_queue_briefs)
        calls.append(
            (
                "bundle_builder",
                (candidate_tuple, strategy_tuple, risk_tuple, research_queue_tuple),
            )
        )
        return build_advisory_operating_brief_content_bundle(
            candidate_research_briefs=candidate_tuple,
            strategy_eligibility_briefs=strategy_tuple,
            risk_authority_briefs=risk_tuple,
            research_queue_briefs=research_queue_tuple,
        )

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief",
        recording_candidate_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_strategy_eligibility_brief",
        recording_strategy_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_risk_authority_brief",
        recording_risk_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_queue_brief",
        recording_research_queue_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_advisory_operating_brief_content_bundle",
        recording_bundle_builder,
    )

    bundle = (
        fixture_module
        .build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    )

    assert [name for name, _ in calls] == [
        "candidate_fixture",
        "strategy_fixture",
        "risk_fixture",
        "research_queue_fixture",
        "bundle_builder",
    ]
    assert calls[0][1] is source_candidate
    assert calls[1][1] is source_strategy
    assert calls[2][1] is source_risk
    assert calls[3][1] is source_research_queue
    assert calls[4][1] == (
        (source_candidate,),
        (source_strategy,),
        (source_risk,),
        (source_research_queue,),
    )
    assert bundle.candidate_research_briefs == (source_candidate,)
    assert bundle.strategy_eligibility_briefs == (source_strategy,)
    assert bundle.risk_authority_briefs == (source_risk,)
    assert bundle.research_queue_briefs == (source_research_queue,)


def test_sma_fixture_uses_existing_fixtures_and_phase_205_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_candidate = build_synthetic_candidate_research_brief()
    source_strategy = build_synthetic_strategy_eligibility_brief()
    source_risk = build_synthetic_risk_authority_brief()
    source_research_queue = build_synthetic_research_queue_brief()
    source_sma = build_synthetic_sma_research_observation_brief()

    def recording_candidate_fixture() -> CandidateResearchBrief:
        calls.append(("candidate_fixture", source_candidate))
        return source_candidate

    def recording_strategy_fixture() -> StrategyEligibilityBrief:
        calls.append(("strategy_fixture", source_strategy))
        return source_strategy

    def recording_risk_fixture() -> RiskAuthorityBrief:
        calls.append(("risk_fixture", source_risk))
        return source_risk

    def recording_research_queue_fixture() -> ResearchQueueBrief:
        calls.append(("research_queue_fixture", source_research_queue))
        return source_research_queue

    def recording_sma_fixture() -> SmaResearchObservationBrief:
        calls.append(("sma_fixture", source_sma))
        return source_sma

    def recording_bundle_builder(
        candidate_research_briefs: tuple[CandidateResearchBrief, ...],
        strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
        risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
        research_queue_briefs: tuple[ResearchQueueBrief, ...],
        sma_research_observation_briefs: tuple[SmaResearchObservationBrief, ...],
    ) -> AdvisoryOperatingBriefContentBundle:
        candidate_tuple = tuple(candidate_research_briefs)
        strategy_tuple = tuple(strategy_eligibility_briefs)
        risk_tuple = tuple(risk_authority_briefs)
        research_queue_tuple = tuple(research_queue_briefs)
        sma_tuple = tuple(sma_research_observation_briefs)
        calls.append(
            (
                "bundle_builder",
                (
                    candidate_tuple,
                    strategy_tuple,
                    risk_tuple,
                    research_queue_tuple,
                    sma_tuple,
                ),
            )
        )
        return build_advisory_operating_brief_content_bundle(
            candidate_research_briefs=candidate_tuple,
            strategy_eligibility_briefs=strategy_tuple,
            risk_authority_briefs=risk_tuple,
            research_queue_briefs=research_queue_tuple,
            sma_research_observation_briefs=sma_tuple,
        )

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief",
        recording_candidate_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_strategy_eligibility_brief",
        recording_strategy_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_risk_authority_brief",
        recording_risk_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_queue_brief",
        recording_research_queue_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_sma_research_observation_brief",
        recording_sma_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_advisory_operating_brief_content_bundle",
        recording_bundle_builder,
    )

    bundle = (
        fixture_module
        .build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )

    assert [name for name, _ in calls] == [
        "candidate_fixture",
        "strategy_fixture",
        "risk_fixture",
        "research_queue_fixture",
        "sma_fixture",
        "bundle_builder",
    ]
    assert calls[0][1] is source_candidate
    assert calls[1][1] is source_strategy
    assert calls[2][1] is source_risk
    assert calls[3][1] is source_research_queue
    assert calls[4][1] is source_sma
    assert calls[5][1] == (
        (source_candidate,),
        (source_strategy,),
        (source_risk,),
        (source_research_queue,),
        (source_sma,),
    )
    assert bundle.candidate_research_briefs == (source_candidate,)
    assert bundle.strategy_eligibility_briefs == (source_strategy,)
    assert bundle.risk_authority_briefs == (source_risk,)
    assert bundle.research_queue_briefs == (source_research_queue,)
    assert bundle.sma_research_observation_briefs == (source_sma,)


def test_research_return_fixture_uses_existing_fixtures_and_phase_220_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_candidate = build_synthetic_candidate_research_brief()
    source_strategy = build_synthetic_strategy_eligibility_brief()
    source_risk = build_synthetic_risk_authority_brief()
    source_research_queue = build_synthetic_research_queue_brief()
    source_sma = build_synthetic_sma_research_observation_brief()
    source_research_return = build_synthetic_research_return_observation_brief()

    def recording_candidate_fixture() -> CandidateResearchBrief:
        calls.append(("candidate_fixture", source_candidate))
        return source_candidate

    def recording_strategy_fixture() -> StrategyEligibilityBrief:
        calls.append(("strategy_fixture", source_strategy))
        return source_strategy

    def recording_risk_fixture() -> RiskAuthorityBrief:
        calls.append(("risk_fixture", source_risk))
        return source_risk

    def recording_research_queue_fixture() -> ResearchQueueBrief:
        calls.append(("research_queue_fixture", source_research_queue))
        return source_research_queue

    def recording_sma_fixture() -> SmaResearchObservationBrief:
        calls.append(("sma_fixture", source_sma))
        return source_sma

    def recording_research_return_fixture() -> ResearchReturnObservationBrief:
        calls.append(("research_return_fixture", source_research_return))
        return source_research_return

    def recording_bundle_builder(
        candidate_research_briefs: tuple[CandidateResearchBrief, ...],
        strategy_eligibility_briefs: tuple[StrategyEligibilityBrief, ...],
        risk_authority_briefs: tuple[RiskAuthorityBrief, ...],
        research_queue_briefs: tuple[ResearchQueueBrief, ...],
        sma_research_observation_briefs: tuple[SmaResearchObservationBrief, ...],
        research_return_observation_briefs: tuple[
            ResearchReturnObservationBrief, ...
        ],
    ) -> AdvisoryOperatingBriefContentBundle:
        candidate_tuple = tuple(candidate_research_briefs)
        strategy_tuple = tuple(strategy_eligibility_briefs)
        risk_tuple = tuple(risk_authority_briefs)
        research_queue_tuple = tuple(research_queue_briefs)
        sma_tuple = tuple(sma_research_observation_briefs)
        research_return_tuple = tuple(research_return_observation_briefs)
        calls.append(
            (
                "bundle_builder",
                (
                    candidate_tuple,
                    strategy_tuple,
                    risk_tuple,
                    research_queue_tuple,
                    sma_tuple,
                    research_return_tuple,
                ),
            )
        )
        return build_advisory_operating_brief_content_bundle(
            candidate_research_briefs=candidate_tuple,
            strategy_eligibility_briefs=strategy_tuple,
            risk_authority_briefs=risk_tuple,
            research_queue_briefs=research_queue_tuple,
            sma_research_observation_briefs=sma_tuple,
            research_return_observation_briefs=research_return_tuple,
        )

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief",
        recording_candidate_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_strategy_eligibility_brief",
        recording_strategy_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_risk_authority_brief",
        recording_risk_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_queue_brief",
        recording_research_queue_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_sma_research_observation_brief",
        recording_sma_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_research_return_observation_brief",
        recording_research_return_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_advisory_operating_brief_content_bundle",
        recording_bundle_builder,
    )

    bundle = (
        fixture_module
        .build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation()
    )

    assert [name for name, _ in calls] == [
        "candidate_fixture",
        "strategy_fixture",
        "risk_fixture",
        "research_queue_fixture",
        "sma_fixture",
        "research_return_fixture",
        "bundle_builder",
    ]
    assert calls[0][1] is source_candidate
    assert calls[1][1] is source_strategy
    assert calls[2][1] is source_risk
    assert calls[3][1] is source_research_queue
    assert calls[4][1] is source_sma
    assert calls[5][1] is source_research_return
    assert calls[6][1] == (
        (source_candidate,),
        (source_strategy,),
        (source_risk,),
        (source_research_queue,),
        (source_sma,),
        (source_research_return,),
    )
    assert bundle.candidate_research_briefs == (source_candidate,)
    assert bundle.strategy_eligibility_briefs == (source_strategy,)
    assert bundle.risk_authority_briefs == (source_risk,)
    assert bundle.research_queue_briefs == (source_research_queue,)
    assert bundle.sma_research_observation_briefs == (source_sma,)
    assert bundle.research_return_observation_briefs == (source_research_return,)


def test_research_queue_expected_helper_uses_all_nested_expected_dictionaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    source_candidate_expected = expected_synthetic_candidate_research_brief_dict()
    source_strategy_expected = expected_synthetic_strategy_eligibility_brief_dict()
    source_risk_expected = expected_synthetic_risk_authority_brief_dict()
    source_research_queue_expected = expected_synthetic_research_queue_brief_dict()

    def recording_expected_candidate() -> dict[str, object]:
        calls.append("candidate_expected")
        return source_candidate_expected

    def recording_expected_strategy() -> dict[str, object]:
        calls.append("strategy_expected")
        return source_strategy_expected

    def recording_expected_risk() -> dict[str, object]:
        calls.append("risk_expected")
        return source_risk_expected

    def recording_expected_research_queue() -> dict[str, object]:
        calls.append("research_queue_expected")
        return source_research_queue_expected

    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_candidate_research_brief_dict",
        recording_expected_candidate,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_strategy_eligibility_brief_dict",
        recording_expected_strategy,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_risk_authority_brief_dict",
        recording_expected_risk,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_research_queue_brief_dict",
        recording_expected_research_queue,
    )

    expected = (
        fixture_module
        .expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()
    )

    assert calls == [
        "candidate_expected",
        "strategy_expected",
        "risk_expected",
        "research_queue_expected",
    ]
    assert expected["candidate_research_briefs"][0] is source_candidate_expected
    assert expected["strategy_eligibility_briefs"][0] is source_strategy_expected
    assert expected["risk_authority_briefs"][0] is source_risk_expected
    assert expected["research_queue_briefs"][0] is source_research_queue_expected
    assert expected["limitations"] == list(_EXPECTED_WITH_RESEARCH_QUEUE_LIMITATIONS)
    assert expected["non_claims"] == list(_EXPECTED_WITH_RESEARCH_QUEUE_NON_CLAIMS)


def test_sma_expected_helper_uses_all_nested_expected_dictionaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    source_candidate_expected = expected_synthetic_candidate_research_brief_dict()
    source_strategy_expected = expected_synthetic_strategy_eligibility_brief_dict()
    source_risk_expected = expected_synthetic_risk_authority_brief_dict()
    source_research_queue_expected = expected_synthetic_research_queue_brief_dict()
    source_sma_expected = expected_synthetic_sma_research_observation_brief_dict()

    def recording_expected_candidate() -> dict[str, object]:
        calls.append("candidate_expected")
        return source_candidate_expected

    def recording_expected_strategy() -> dict[str, object]:
        calls.append("strategy_expected")
        return source_strategy_expected

    def recording_expected_risk() -> dict[str, object]:
        calls.append("risk_expected")
        return source_risk_expected

    def recording_expected_research_queue() -> dict[str, object]:
        calls.append("research_queue_expected")
        return source_research_queue_expected

    def recording_expected_sma() -> dict[str, object]:
        calls.append("sma_expected")
        return source_sma_expected

    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_candidate_research_brief_dict",
        recording_expected_candidate,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_strategy_eligibility_brief_dict",
        recording_expected_strategy,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_risk_authority_brief_dict",
        recording_expected_risk,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_research_queue_brief_dict",
        recording_expected_research_queue,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_sma_research_observation_brief_dict",
        recording_expected_sma,
    )

    expected = (
        fixture_module
        .expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict()
    )

    assert calls == [
        "candidate_expected",
        "strategy_expected",
        "risk_expected",
        "research_queue_expected",
        "sma_expected",
    ]
    assert expected["candidate_research_briefs"][0] is source_candidate_expected
    assert expected["strategy_eligibility_briefs"][0] is source_strategy_expected
    assert expected["risk_authority_briefs"][0] is source_risk_expected
    assert expected["research_queue_briefs"][0] is source_research_queue_expected
    assert expected["sma_research_observation_briefs"][0] is source_sma_expected
    assert expected["limitations"] == list(_EXPECTED_WITH_SMA_LIMITATIONS)
    assert expected["non_claims"] == list(_EXPECTED_WITH_SMA_NON_CLAIMS)


def test_research_return_expected_helper_uses_all_nested_expected_dictionaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    source_candidate_expected = expected_synthetic_candidate_research_brief_dict()
    source_strategy_expected = expected_synthetic_strategy_eligibility_brief_dict()
    source_risk_expected = expected_synthetic_risk_authority_brief_dict()
    source_research_queue_expected = expected_synthetic_research_queue_brief_dict()
    source_sma_expected = expected_synthetic_sma_research_observation_brief_dict()
    source_research_return_expected = (
        expected_synthetic_research_return_observation_brief_dict()
    )

    def recording_expected_candidate() -> dict[str, object]:
        calls.append("candidate_expected")
        return source_candidate_expected

    def recording_expected_strategy() -> dict[str, object]:
        calls.append("strategy_expected")
        return source_strategy_expected

    def recording_expected_risk() -> dict[str, object]:
        calls.append("risk_expected")
        return source_risk_expected

    def recording_expected_research_queue() -> dict[str, object]:
        calls.append("research_queue_expected")
        return source_research_queue_expected

    def recording_expected_sma() -> dict[str, object]:
        calls.append("sma_expected")
        return source_sma_expected

    def recording_expected_research_return() -> dict[str, object]:
        calls.append("research_return_expected")
        return source_research_return_expected

    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_candidate_research_brief_dict",
        recording_expected_candidate,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_strategy_eligibility_brief_dict",
        recording_expected_strategy,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_risk_authority_brief_dict",
        recording_expected_risk,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_research_queue_brief_dict",
        recording_expected_research_queue,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_sma_research_observation_brief_dict",
        recording_expected_sma,
    )
    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_research_return_observation_brief_dict",
        recording_expected_research_return,
    )

    expected = (
        fixture_module
        .expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict()
    )

    assert calls == [
        "candidate_expected",
        "strategy_expected",
        "risk_expected",
        "research_queue_expected",
        "sma_expected",
        "research_return_expected",
    ]
    assert expected["candidate_research_briefs"][0] is source_candidate_expected
    assert expected["strategy_eligibility_briefs"][0] is source_strategy_expected
    assert expected["risk_authority_briefs"][0] is source_risk_expected
    assert expected["research_queue_briefs"][0] is source_research_queue_expected
    assert expected["sma_research_observation_briefs"][0] is source_sma_expected
    assert expected["research_return_observation_briefs"][0] is (
        source_research_return_expected
    )
    assert expected["limitations"] == list(_EXPECTED_WITH_RESEARCH_RETURN_LIMITATIONS)
    assert expected["non_claims"] == list(_EXPECTED_WITH_RESEARCH_RETURN_NON_CLAIMS)


def test_research_queue_fixture_output_matches_expected_dictionary_exactly() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    payload = bundle.to_dict()
    expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()
    )

    assert expected == _EXPECTED_WITH_RESEARCH_QUEUE_DICT
    assert payload == expected
    assert tuple(payload) == tuple(_EXPECTED_WITH_RESEARCH_QUEUE_DICT)
    assert payload["candidate_research_briefs"][0] == _EXPECTED_CANDIDATE_BRIEF_DICT
    assert payload["strategy_eligibility_briefs"][0] == (
        _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT
    )
    assert payload["risk_authority_briefs"][0] == _EXPECTED_RISK_AUTHORITY_BRIEF_DICT
    assert payload["research_queue_briefs"][0] == _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT
    assert "sma_research_observation_brief_count" not in payload
    assert "sma_research_observation_briefs" not in payload
    _assert_primitive_only(payload)
    _assert_primitive_only(expected)


def test_sma_fixture_output_matches_expected_dictionary_exactly() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    payload = bundle.to_dict()
    expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict()
    )

    assert expected == _EXPECTED_WITH_SMA_DICT
    assert payload == expected
    assert tuple(payload) == tuple(_EXPECTED_WITH_SMA_DICT)
    assert payload["sma_research_observation_brief_count"] == 1
    assert payload["candidate_research_briefs"][0] == _EXPECTED_CANDIDATE_BRIEF_DICT
    assert payload["strategy_eligibility_briefs"][0] == (
        _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT
    )
    assert payload["risk_authority_briefs"][0] == _EXPECTED_RISK_AUTHORITY_BRIEF_DICT
    assert payload["research_queue_briefs"][0] == _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT
    assert payload["sma_research_observation_briefs"][0] == (
        _EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT
    )
    _assert_primitive_only(payload)
    _assert_primitive_only(expected)


def test_research_return_fixture_output_matches_expected_dictionary_exactly() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation()
    )
    payload = bundle.to_dict()
    expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict()
    )

    assert expected == _EXPECTED_WITH_RESEARCH_RETURN_DICT
    assert payload == expected
    assert tuple(payload) == tuple(_EXPECTED_WITH_RESEARCH_RETURN_DICT)
    assert payload["research_return_observation_brief_count"] == 1
    assert payload["candidate_research_briefs"][0] == _EXPECTED_CANDIDATE_BRIEF_DICT
    assert payload["strategy_eligibility_briefs"][0] == (
        _EXPECTED_STRATEGY_ELIGIBILITY_BRIEF_DICT
    )
    assert payload["risk_authority_briefs"][0] == _EXPECTED_RISK_AUTHORITY_BRIEF_DICT
    assert payload["research_queue_briefs"][0] == _EXPECTED_RESEARCH_QUEUE_BRIEF_DICT
    assert payload["sma_research_observation_briefs"][0] == (
        _EXPECTED_SMA_RESEARCH_OBSERVATION_BRIEF_DICT
    )
    assert payload["research_return_observation_briefs"][0] == (
        _EXPECTED_RESEARCH_RETURN_OBSERVATION_BRIEF_DICT
    )
    _assert_primitive_only(payload)
    _assert_primitive_only(expected)


def test_nested_strategy_eligibility_brief_matches_phase_160_helper() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    payload = bundle.to_dict()

    assert payload["strategy_eligibility_briefs"][0] == (
        expected_synthetic_strategy_eligibility_brief_dict()
    )


def test_nested_candidate_research_brief_matches_existing_helper() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    payload = bundle.to_dict()

    assert payload["candidate_research_briefs"][0] == (
        expected_synthetic_candidate_research_brief_dict()
    )


def test_nested_sma_research_observation_brief_matches_phase_202_helper() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    payload = bundle.to_dict()

    assert payload["sma_research_observation_briefs"][0] == (
        expected_synthetic_sma_research_observation_brief_dict()
    )


def test_nested_research_return_observation_brief_matches_phase_216_helper() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation()
    )
    payload = bundle.to_dict()

    assert payload["research_return_observation_briefs"][0] == (
        expected_synthetic_research_return_observation_brief_dict()
    )


def test_nested_research_return_payload_contains_return_construction_metadata() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation()
    )
    research_return_payload = bundle.to_dict()["research_return_observation_briefs"][0]
    section = research_return_payload["sections"][0]
    constructed_item = section["items"][0]
    insufficient_item = section["items"][1]
    constructed_observation = constructed_item["source_observation"]
    insufficient_observation = insufficient_item["source_observation"]

    assert constructed_item["mechanical_state"] == "returns_constructed"
    assert insufficient_item["mechanical_state"] == "insufficient_return_history"
    assert constructed_item["positive_return_count"] == 1
    assert constructed_item["negative_return_count"] == 1
    assert constructed_item["zero_return_count"] == 1
    assert insufficient_item["positive_return_count"] == 0
    assert insufficient_item["negative_return_count"] == 0
    assert insufficient_item["zero_return_count"] == 0
    assert constructed_observation["return_method"] == "close_to_close_simple_return"
    assert constructed_observation["price_basis"] == "synthetic_close"
    assert constructed_observation["ignored_future_sample_count"] == 1
    assert constructed_observation["return_count"] == 3
    assert constructed_observation["returns"] == [
        {
            "start_date": "2026-01-15",
            "end_date": "2026-01-16",
            "start_close": "100.00",
            "end_close": "105.00",
            "simple_return": "0.05",
        },
        {
            "start_date": "2026-01-16",
            "end_date": "2026-01-19",
            "start_close": "105.00",
            "end_close": "94.50",
            "simple_return": "-0.1",
        },
        {
            "start_date": "2026-01-19",
            "end_date": "2026-01-20",
            "start_close": "94.50",
            "end_close": "94.50",
            "simple_return": "0",
        },
    ]
    assert insufficient_observation["return_method"] == "close_to_close_simple_return"
    assert insufficient_observation["price_basis"] == "synthetic_close"
    assert insufficient_observation["ignored_future_sample_count"] == 1
    assert insufficient_observation["return_count"] == 0
    assert insufficient_observation["returns"] == []


def test_repeated_fixture_construction_is_dict_and_byte_deterministic() -> None:
    first = build_synthetic_advisory_operating_brief_content_bundle()
    second = build_synthetic_advisory_operating_brief_content_bundle()
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_expected = expected_synthetic_advisory_operating_brief_content_bundle_dict()
    second_expected = expected_synthetic_advisory_operating_brief_content_bundle_dict()
    first_json_bytes = _compact_json_bytes(first_payload)
    second_json_bytes = _compact_json_bytes(second_payload)

    assert first is not second
    assert first.candidate_research_briefs[0] is not second.candidate_research_briefs[0]
    assert first.strategy_eligibility_briefs[0] is not (
        second.strategy_eligibility_briefs[0]
    )
    assert first_payload == second_payload == first_expected == second_expected
    assert first_payload == _EXPECTED_DICT
    assert first_json_bytes == second_json_bytes == _EXPECTED_COMPACT_JSON_BYTES
    assert json.loads(first_json_bytes.decode("ascii")) == first_payload


def test_repeated_research_queue_fixture_construction_is_deterministic() -> None:
    first = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    second = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    )
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()
    )
    second_expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()
    )
    first_json_bytes = _compact_json_bytes(first_payload)
    second_json_bytes = _compact_json_bytes(second_payload)

    assert first is not second
    assert first.candidate_research_briefs[0] is not second.candidate_research_briefs[0]
    assert first.strategy_eligibility_briefs[0] is not (
        second.strategy_eligibility_briefs[0]
    )
    assert first.risk_authority_briefs[0] is not second.risk_authority_briefs[0]
    assert first.research_queue_briefs[0] is not second.research_queue_briefs[0]
    assert first_payload == second_payload == first_expected == second_expected
    assert first_payload == _EXPECTED_WITH_RESEARCH_QUEUE_DICT
    assert (
        first_json_bytes
        == second_json_bytes
        == _EXPECTED_WITH_RESEARCH_QUEUE_COMPACT_JSON_BYTES
    )
    assert json.loads(first_json_bytes.decode("ascii")) == first_payload


def test_repeated_sma_fixture_construction_is_deterministic() -> None:
    first = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    second = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict()
    )
    second_expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict()
    )
    first_json_bytes = _compact_json_bytes(first_payload)
    second_json_bytes = _compact_json_bytes(second_payload)

    assert first is not second
    assert first.candidate_research_briefs[0] is not second.candidate_research_briefs[0]
    assert first.strategy_eligibility_briefs[0] is not (
        second.strategy_eligibility_briefs[0]
    )
    assert first.risk_authority_briefs[0] is not second.risk_authority_briefs[0]
    assert first.research_queue_briefs[0] is not second.research_queue_briefs[0]
    assert first.sma_research_observation_briefs[0] is not (
        second.sma_research_observation_briefs[0]
    )
    assert first_payload == second_payload == first_expected == second_expected
    assert first_payload == _EXPECTED_WITH_SMA_DICT
    assert (
        first_json_bytes
        == second_json_bytes
        == _EXPECTED_WITH_SMA_COMPACT_JSON_BYTES
    )
    assert json.loads(first_json_bytes.decode("ascii")) == first_payload


def test_repeated_research_return_fixture_construction_is_deterministic() -> None:
    first = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation()
    )
    second = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation()
    )
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict()
    )
    second_expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict()
    )
    first_json_bytes = _compact_json_bytes(first_payload)
    second_json_bytes = _compact_json_bytes(second_payload)

    assert first is not second
    assert first.candidate_research_briefs[0] is not second.candidate_research_briefs[0]
    assert first.strategy_eligibility_briefs[0] is not (
        second.strategy_eligibility_briefs[0]
    )
    assert first.risk_authority_briefs[0] is not second.risk_authority_briefs[0]
    assert first.research_queue_briefs[0] is not second.research_queue_briefs[0]
    assert first.sma_research_observation_briefs[0] is not (
        second.sma_research_observation_briefs[0]
    )
    assert first.research_return_observation_briefs[0] is not (
        second.research_return_observation_briefs[0]
    )
    assert first_payload == second_payload == first_expected == second_expected
    assert first_payload == _EXPECTED_WITH_RESEARCH_RETURN_DICT
    assert (
        first_json_bytes
        == second_json_bytes
        == _EXPECTED_WITH_RESEARCH_RETURN_COMPACT_JSON_BYTES
    )
    assert json.loads(first_json_bytes.decode("ascii")) == first_payload


def test_fixed_advisory_metadata_is_pinned() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    payload = bundle.to_dict()

    assert bundle.bundle_type == "advisory_operating_brief_content_bundle"
    assert bundle.status == "candidate_only"
    assert bundle.authority == "advisory_only"
    assert bundle.capital_authority is False
    assert payload["bundle_type"] == "advisory_operating_brief_content_bundle"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert payload["candidate_research_brief_count"] == 1
    assert payload["strategy_eligibility_brief_count"] == 1
    assert "research_queue_brief_count" not in payload
    assert "sma_research_observation_brief_count" not in payload


def test_title_and_summary_are_pinned_and_advisory_only() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    payload = bundle.to_dict()

    assert bundle.title == _EXPECTED_DICT["title"]
    assert bundle.summary == _EXPECTED_DICT["summary"]
    assert payload["title"] == _EXPECTED_DICT["title"]
    assert payload["summary"] == _EXPECTED_DICT["summary"]

    for text in (bundle.title, bundle.summary):
        lowered = text.lower()
        for token in _FORBIDDEN_TEXT_TOKENS:
            assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", lowered) is None


def test_tuple_storage_and_list_serialization_are_pinned() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    candidate_brief = bundle.candidate_research_briefs[0]
    strategy_brief = bundle.strategy_eligibility_briefs[0]
    payload = bundle.to_dict()

    assert isinstance(bundle.candidate_research_briefs, tuple)
    assert isinstance(bundle.strategy_eligibility_briefs, tuple)
    assert bundle.candidate_research_briefs == (candidate_brief,)
    assert bundle.strategy_eligibility_briefs == (strategy_brief,)
    assert isinstance(payload["candidate_research_briefs"], list)
    assert isinstance(payload["strategy_eligibility_briefs"], list)
    assert payload["candidate_research_briefs"] == [candidate_brief.to_dict()]
    assert payload["strategy_eligibility_briefs"] == [strategy_brief.to_dict()]

    for field_name in _TUPLE_FIELDS:
        bundle_value = getattr(bundle, field_name)
        serialized = payload[field_name]

        assert isinstance(bundle_value, tuple)
        assert isinstance(serialized, list)
        assert serialized == list(bundle_value)
        assert serialized is not getattr(bundle, field_name)
        assert serialized is not payload["candidate_research_briefs"][0][field_name]
        assert serialized is not payload["strategy_eligibility_briefs"][0][field_name]

    payload["candidate_research_briefs"].append(candidate_brief.to_dict())
    payload["strategy_eligibility_briefs"].append(strategy_brief.to_dict())
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive copy")
    payload["candidate_research_briefs"][0]["limitations"].append(
        "mutated nested primitive copy"
    )
    payload["strategy_eligibility_briefs"][0]["non_claims"].append(
        "not mutated nested primitive copy"
    )

    assert bundle.to_dict() == _EXPECTED_DICT


def test_limitations_and_non_claims_are_carried_forward_from_both_branches() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    candidate_brief = bundle.candidate_research_briefs[0]
    strategy_brief = bundle.strategy_eligibility_briefs[0]
    payload = bundle.to_dict()

    assert candidate_brief.limitations
    assert candidate_brief.non_claims
    assert strategy_brief.limitations
    assert strategy_brief.non_claims
    assert bundle.limitations == _EXPECTED_LIMITATIONS
    assert bundle.non_claims == _EXPECTED_NON_CLAIMS
    assert payload["limitations"] == list(_EXPECTED_LIMITATIONS)
    assert payload["non_claims"] == list(_EXPECTED_NON_CLAIMS)
    assert len(bundle.limitations) == len(set(bundle.limitations))
    assert len(bundle.non_claims) == len(set(bundle.non_claims))
    assert all(value in bundle.limitations for value in candidate_brief.limitations)
    assert all(value in bundle.limitations for value in strategy_brief.limitations)
    assert all(value in bundle.non_claims for value in candidate_brief.non_claims)
    assert all(value in bundle.non_claims for value in strategy_brief.non_claims)


def test_research_queue_limitations_and_non_claims_are_carried_forward() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    candidate_brief = bundle.candidate_research_briefs[0]
    strategy_brief = bundle.strategy_eligibility_briefs[0]
    risk_brief = bundle.risk_authority_briefs[0]
    research_queue_brief = bundle.research_queue_briefs[0]
    payload = bundle.to_dict()

    assert risk_brief.limitations
    assert risk_brief.non_claims
    assert research_queue_brief.limitations
    assert research_queue_brief.non_claims
    assert bundle.limitations == _EXPECTED_WITH_RESEARCH_QUEUE_LIMITATIONS
    assert bundle.non_claims == _EXPECTED_WITH_RESEARCH_QUEUE_NON_CLAIMS
    assert payload["limitations"] == list(_EXPECTED_WITH_RESEARCH_QUEUE_LIMITATIONS)
    assert payload["non_claims"] == list(_EXPECTED_WITH_RESEARCH_QUEUE_NON_CLAIMS)
    assert len(bundle.limitations) == len(set(bundle.limitations))
    assert len(bundle.non_claims) == len(set(bundle.non_claims))
    assert all(value in bundle.limitations for value in candidate_brief.limitations)
    assert all(value in bundle.limitations for value in strategy_brief.limitations)
    assert all(value in bundle.limitations for value in risk_brief.limitations)
    assert all(
        value in bundle.limitations for value in research_queue_brief.limitations
    )
    assert all(value in bundle.non_claims for value in candidate_brief.non_claims)
    assert all(value in bundle.non_claims for value in strategy_brief.non_claims)
    assert all(value in bundle.non_claims for value in risk_brief.non_claims)
    assert all(
        value in bundle.non_claims for value in research_queue_brief.non_claims
    )


def test_sma_limitations_and_non_claims_are_carried_forward() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    candidate_brief = bundle.candidate_research_briefs[0]
    strategy_brief = bundle.strategy_eligibility_briefs[0]
    risk_brief = bundle.risk_authority_briefs[0]
    research_queue_brief = bundle.research_queue_briefs[0]
    sma_brief = bundle.sma_research_observation_briefs[0]
    payload = bundle.to_dict()

    assert sma_brief.limitations
    assert sma_brief.non_claims
    assert bundle.limitations == _EXPECTED_WITH_SMA_LIMITATIONS
    assert bundle.non_claims == _EXPECTED_WITH_SMA_NON_CLAIMS
    assert payload["limitations"] == list(_EXPECTED_WITH_SMA_LIMITATIONS)
    assert payload["non_claims"] == list(_EXPECTED_WITH_SMA_NON_CLAIMS)
    assert len(bundle.limitations) == len(set(bundle.limitations))
    assert len(bundle.non_claims) == len(set(bundle.non_claims))
    assert all(value in bundle.limitations for value in candidate_brief.limitations)
    assert all(value in bundle.limitations for value in strategy_brief.limitations)
    assert all(value in bundle.limitations for value in risk_brief.limitations)
    assert all(
        value in bundle.limitations for value in research_queue_brief.limitations
    )
    assert all(value in bundle.limitations for value in sma_brief.limitations)
    assert all(value in bundle.non_claims for value in candidate_brief.non_claims)
    assert all(value in bundle.non_claims for value in strategy_brief.non_claims)
    assert all(value in bundle.non_claims for value in risk_brief.non_claims)
    assert all(
        value in bundle.non_claims for value in research_queue_brief.non_claims
    )
    assert all(value in bundle.non_claims for value in sma_brief.non_claims)


def test_research_return_limitations_and_non_claims_are_carried_forward() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation()
    )
    candidate_brief = bundle.candidate_research_briefs[0]
    strategy_brief = bundle.strategy_eligibility_briefs[0]
    risk_brief = bundle.risk_authority_briefs[0]
    research_queue_brief = bundle.research_queue_briefs[0]
    sma_brief = bundle.sma_research_observation_briefs[0]
    research_return_brief = bundle.research_return_observation_briefs[0]
    payload = bundle.to_dict()

    assert research_return_brief.limitations
    assert research_return_brief.non_claims
    assert bundle.limitations == _EXPECTED_WITH_RESEARCH_RETURN_LIMITATIONS
    assert bundle.non_claims == _EXPECTED_WITH_RESEARCH_RETURN_NON_CLAIMS
    assert payload["limitations"] == list(_EXPECTED_WITH_RESEARCH_RETURN_LIMITATIONS)
    assert payload["non_claims"] == list(_EXPECTED_WITH_RESEARCH_RETURN_NON_CLAIMS)
    assert len(bundle.limitations) == len(set(bundle.limitations))
    assert len(bundle.non_claims) == len(set(bundle.non_claims))
    assert all(value in bundle.limitations for value in candidate_brief.limitations)
    assert all(value in bundle.limitations for value in strategy_brief.limitations)
    assert all(value in bundle.limitations for value in risk_brief.limitations)
    assert all(
        value in bundle.limitations for value in research_queue_brief.limitations
    )
    assert all(value in bundle.limitations for value in sma_brief.limitations)
    assert all(
        value in bundle.limitations for value in research_return_brief.limitations
    )
    assert all(value in bundle.non_claims for value in candidate_brief.non_claims)
    assert all(value in bundle.non_claims for value in strategy_brief.non_claims)
    assert all(value in bundle.non_claims for value in risk_brief.non_claims)
    assert all(
        value in bundle.non_claims for value in research_queue_brief.non_claims
    )
    assert all(value in bundle.non_claims for value in sma_brief.non_claims)
    assert all(
        value in bundle.non_claims for value in research_return_brief.non_claims
    )


def test_research_queue_expected_helper_returns_fresh_mutable_copies() -> None:
    first = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()
    )
    second = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()
    )

    assert first is not second
    assert first["candidate_research_briefs"] is not second["candidate_research_briefs"]
    assert first["strategy_eligibility_briefs"] is not (
        second["strategy_eligibility_briefs"]
    )
    assert first["risk_authority_briefs"] is not second["risk_authority_briefs"]
    assert first["research_queue_briefs"] is not second["research_queue_briefs"]
    assert first["candidate_research_briefs"][0] is not (
        second["candidate_research_briefs"][0]
    )
    assert first["strategy_eligibility_briefs"][0] is not (
        second["strategy_eligibility_briefs"][0]
    )
    assert first["risk_authority_briefs"][0] is not (
        second["risk_authority_briefs"][0]
    )
    assert first["research_queue_briefs"][0] is not (
        second["research_queue_briefs"][0]
    )
    for field_name in _TUPLE_FIELDS:
        assert first[field_name] is not second[field_name]
        assert first[field_name] is not (
            first["candidate_research_briefs"][0][field_name]
        )
        assert first[field_name] is not (
            first["strategy_eligibility_briefs"][0][field_name]
        )
        assert first[field_name] is not first["risk_authority_briefs"][0][field_name]
        assert first[field_name] is not first["research_queue_briefs"][0][field_name]

    first["limitations"].append("mutated primitive copy")
    first["research_queue_briefs"][0]["limitations"].append(
        "mutated research queue expected copy"
    )
    first["non_claims"].append("not mutated expected copy")

    assert second == _EXPECTED_WITH_RESEARCH_QUEUE_DICT
    assert (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()
        == _EXPECTED_WITH_RESEARCH_QUEUE_DICT
    )


def test_sma_expected_helper_returns_fresh_mutable_copies() -> None:
    first = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict()
    )
    second = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict()
    )

    assert first is not second
    assert first["candidate_research_briefs"] is not second["candidate_research_briefs"]
    assert first["strategy_eligibility_briefs"] is not (
        second["strategy_eligibility_briefs"]
    )
    assert first["risk_authority_briefs"] is not second["risk_authority_briefs"]
    assert first["research_queue_briefs"] is not second["research_queue_briefs"]
    assert first["sma_research_observation_briefs"] is not (
        second["sma_research_observation_briefs"]
    )
    assert first["candidate_research_briefs"][0] is not (
        second["candidate_research_briefs"][0]
    )
    assert first["strategy_eligibility_briefs"][0] is not (
        second["strategy_eligibility_briefs"][0]
    )
    assert first["risk_authority_briefs"][0] is not (
        second["risk_authority_briefs"][0]
    )
    assert first["research_queue_briefs"][0] is not (
        second["research_queue_briefs"][0]
    )
    assert first["sma_research_observation_briefs"][0] is not (
        second["sma_research_observation_briefs"][0]
    )
    for field_name in _TUPLE_FIELDS:
        assert first[field_name] is not second[field_name]
        assert first[field_name] is not (
            first["candidate_research_briefs"][0][field_name]
        )
        assert first[field_name] is not (
            first["strategy_eligibility_briefs"][0][field_name]
        )
        assert first[field_name] is not first["risk_authority_briefs"][0][field_name]
        assert first[field_name] is not first["research_queue_briefs"][0][field_name]
        assert first[field_name] is not (
            first["sma_research_observation_briefs"][0][field_name]
        )

    first["limitations"].append("mutated primitive copy")
    first["sma_research_observation_briefs"][0]["limitations"].append(
        "mutated SMA expected copy"
    )
    first["sma_research_observation_briefs"][0]["sections"][0]["items"][0][
        "source_observation"
    ]["limitations"].append("mutated nested SMA expected copy")
    first["non_claims"].append("not mutated expected copy")

    assert second == _EXPECTED_WITH_SMA_DICT
    assert (
        expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict()
        == _EXPECTED_WITH_SMA_DICT
    )


def test_research_return_expected_helper_returns_fresh_mutable_copies() -> None:
    first = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict()
    )
    second = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict()
    )

    assert first is not second
    assert first["candidate_research_briefs"] is not second["candidate_research_briefs"]
    assert first["strategy_eligibility_briefs"] is not (
        second["strategy_eligibility_briefs"]
    )
    assert first["risk_authority_briefs"] is not second["risk_authority_briefs"]
    assert first["research_queue_briefs"] is not second["research_queue_briefs"]
    assert first["sma_research_observation_briefs"] is not (
        second["sma_research_observation_briefs"]
    )
    assert first["research_return_observation_briefs"] is not (
        second["research_return_observation_briefs"]
    )
    assert first["candidate_research_briefs"][0] is not (
        second["candidate_research_briefs"][0]
    )
    assert first["strategy_eligibility_briefs"][0] is not (
        second["strategy_eligibility_briefs"][0]
    )
    assert first["risk_authority_briefs"][0] is not (
        second["risk_authority_briefs"][0]
    )
    assert first["research_queue_briefs"][0] is not (
        second["research_queue_briefs"][0]
    )
    assert first["sma_research_observation_briefs"][0] is not (
        second["sma_research_observation_briefs"][0]
    )
    assert first["research_return_observation_briefs"][0] is not (
        second["research_return_observation_briefs"][0]
    )
    for field_name in _TUPLE_FIELDS:
        assert first[field_name] is not second[field_name]
        assert first[field_name] is not (
            first["candidate_research_briefs"][0][field_name]
        )
        assert first[field_name] is not (
            first["strategy_eligibility_briefs"][0][field_name]
        )
        assert first[field_name] is not first["risk_authority_briefs"][0][field_name]
        assert first[field_name] is not first["research_queue_briefs"][0][field_name]
        assert first[field_name] is not (
            first["sma_research_observation_briefs"][0][field_name]
        )
        assert first[field_name] is not (
            first["research_return_observation_briefs"][0][field_name]
        )

    first["limitations"].append("mutated primitive copy")
    first["research_return_observation_briefs"][0]["limitations"].append(
        "mutated return expected copy"
    )
    first["research_return_observation_briefs"][0]["sections"][0]["items"][0][
        "source_observation"
    ]["limitations"].append("mutated nested return expected copy")
    first["non_claims"].append("not mutated expected copy")

    assert second == _EXPECTED_WITH_RESEARCH_RETURN_DICT
    assert (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation_dict()
        == _EXPECTED_WITH_RESEARCH_RETURN_DICT
    )


def test_fixture_helpers_do_not_mutate_sources_or_share_mutable_payload_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_candidate = build_synthetic_candidate_research_brief()
    source_strategy = build_synthetic_strategy_eligibility_brief()
    candidate_before = source_candidate.to_dict()
    strategy_before = source_strategy.to_dict()

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_brief",
        lambda: source_candidate,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_strategy_eligibility_brief",
        lambda: source_strategy,
    )

    bundle = fixture_module.build_synthetic_advisory_operating_brief_content_bundle()
    payload = bundle.to_dict()
    first_expected = expected_synthetic_advisory_operating_brief_content_bundle_dict()
    second_expected = expected_synthetic_advisory_operating_brief_content_bundle_dict()

    assert first_expected is not second_expected
    assert first_expected["candidate_research_briefs"] is not (
        second_expected["candidate_research_briefs"]
    )
    assert first_expected["strategy_eligibility_briefs"] is not (
        second_expected["strategy_eligibility_briefs"]
    )
    assert first_expected["candidate_research_briefs"][0] is not (
        second_expected["candidate_research_briefs"][0]
    )
    assert first_expected["strategy_eligibility_briefs"][0] is not (
        second_expected["strategy_eligibility_briefs"][0]
    )
    for field_name in _TUPLE_FIELDS:
        assert first_expected[field_name] is not second_expected[field_name]
        assert first_expected[field_name] is not (
            first_expected["candidate_research_briefs"][0][field_name]
        )
        assert first_expected[field_name] is not (
            first_expected["strategy_eligibility_briefs"][0][field_name]
        )

    payload["candidate_research_briefs"][0]["limitations"].append(
        "mutated primitive copy"
    )
    payload["strategy_eligibility_briefs"][0]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")
    first_expected["candidate_research_briefs"][0]["non_claims"].append(
        "not mutated expected copy"
    )
    first_expected["non_claims"].append("not mutated expected copy")

    assert bundle.candidate_research_briefs[0] is source_candidate
    assert bundle.strategy_eligibility_briefs[0] is source_strategy
    assert source_candidate.to_dict() == candidate_before
    assert source_strategy.to_dict() == strategy_before
    assert bundle.to_dict() == _EXPECTED_DICT
    assert second_expected == _EXPECTED_DICT
    assert expected_synthetic_advisory_operating_brief_content_bundle_dict() == (
        _EXPECTED_DICT
    )


def test_fixture_exposes_no_forbidden_authority_payload_or_object_fields() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle()
    candidate_brief = bundle.candidate_research_briefs[0]
    strategy_brief = bundle.strategy_eligibility_briefs[0]
    payload = bundle.to_dict()

    assert tuple(payload) == tuple(_EXPECTED_DICT)
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _ast_dict_string_keys().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _call_keyword_names().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert all(
        not hasattr(bundle, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert all(
        not hasattr(candidate_brief, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert all(
        not hasattr(strategy_brief, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert bundle.status == "candidate_only"
    assert bundle.authority == "advisory_only"
    assert bundle.capital_authority is False


def test_fixture_module_imports_no_forbidden_trading_or_runtime_paths() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_fixture_module_makes_no_io_network_or_authority_calls() -> None:
    call_names = _call_names()

    assert call_names == _ALLOWED_CALL_NAMES
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_literals_do_not_add_forbidden_authority_states() -> None:
    literals = _string_literals()
    lowered_source = _source_text().lower()

    assert literals.isdisjoint(_FORBIDDEN_EXACT_LITERALS)
    for substring in _FORBIDDEN_LITERAL_SUBSTRINGS:
        assert substring not in lowered_source
    for token in _FORBIDDEN_SOURCE_TOKENS:
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", lowered_source) is None


def _compact_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode(
        "ascii"
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


def _source_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(FIXTURE_PATH))


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


def _ast_dict_string_keys() -> set[str]:
    keys: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)

    return keys


def _call_keyword_names() -> set[str]:
    return {
        keyword.arg
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg is not None
    }


def _string_literals() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
