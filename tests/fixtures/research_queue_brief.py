"""Synthetic advisory-only research queue brief fixture."""

from __future__ import annotations

from algotrader.research.research_queue_brief import (
    ResearchQueueBrief,
    build_research_queue_brief,
)
from algotrader.research.research_queue_brief_item import (
    ResearchQueueBriefItem,
    build_research_queue_brief_item,
)
from algotrader.research.research_queue_brief_section import (
    ResearchQueueBriefSection,
    build_research_queue_brief_section,
)
from algotrader.research.research_queue_status import (
    ResearchQueueStatus,
    build_research_queue_status,
)

__all__ = [
    "build_synthetic_research_queue_status",
    "expected_synthetic_research_queue_status_dict",
    "build_synthetic_research_queue_brief_item",
    "expected_synthetic_research_queue_brief_item_dict",
    "build_synthetic_research_queue_brief_section",
    "expected_synthetic_research_queue_brief_section_dict",
    "build_synthetic_research_queue_brief",
    "expected_synthetic_research_queue_brief_dict",
]

_QUEUE_ID = "research-queue:broad-etf-sma:candidate"
_TITLE = "Broad ETF SMA trend-following research queue item"
_RESEARCH_STATE = "needs_evidence"
_PRIORITY_BUCKET = "medium"
_TOPIC = "broad_etf_sma_trend_following"
_HYPOTHESIS = (
    "broad ETF SMA trend-following remains a pipeline-validation candidate only"
)
_BLOCKERS = (
    "source data clearance is unresolved",
    "ETF universe definition is unresolved",
    "benchmark and cash proxy policy is unresolved",
    "return policy is unresolved",
    "no-lookahead protocol is unresolved",
    "survivorship policy is unresolved",
    "reproduction protocol is unresolved",
    "validation evidence is missing",
)
_REQUIRED_NEXT_STEPS = (
    "validate deterministic fixture shape for broad ETF SMA inputs",
    "confirm source provenance boundaries before real data use",
    "scope methodology before any research claim",
    "construct no-lookahead returns from fixture inputs only",
)
_EVIDENCE_GAPS = (
    "real data provenance evidence is absent",
    "benchmark and cash handling evidence is absent",
    "survivorship treatment evidence is absent",
    "cost and slippage assumptions are absent",
    "out-of-sample robustness evidence is absent",
    "reproduction evidence is absent",
)
_RELATED_STRATEGY_IDS = (
    "synthetic-advisory:broad-etf-sma",
    "research-queue:broad-etf-sma",
)
_EVIDENCE_REFS = (
    "phase-182-research-queue-status-contract",
    "phase-182-research-queue-brief-contract",
    "advisory-operating-brief-synthetic-foundation",
)
_LIMITATIONS = (
    "synthetic metadata-only unresolved research queue fixture",
    "broad ETF SMA remains pipeline-validation metadata only",
    "fixture output is not connected to real data or runtime state",
)
_NON_CLAIMS = (
    "not a recommendation",
    "not allocation authority",
    "not order authority",
    "not paper readiness",
    "not live readiness",
    "not broker authority",
    "not account authority",
    "not portfolio mutation authority",
    "not capital authority",
    "not trading authority",
    "not strategy approval",
    "not data source approval",
    "not methodology approval",
    "not profitability evidence",
    "not research conclusion",
    "not backtest readiness",
    "not execution readiness",
    "not allocation guidance",
    "not order placement",
    "not ranking or scoring output",
)
_ITEM_HEADLINE = (
    "Research queue item research-queue:broad-etf-sma:candidate: needs_evidence."
)
_ITEM_SUMMARY = (
    "Research queue metadata records needs_evidence work in the medium "
    "priority bucket with 8 blocker(s), 4 required next step(s), "
    "6 evidence gap(s), 3 evidence reference(s), 2 related strategy id(s), "
    "3 limitation(s), and 20 non-claim(s)."
)
_SECTION_TITLE = "Research queue metadata: needs_evidence"
_SECTION_SUMMARY = (
    "Research queue section contains 1 candidate metadata item(s) across "
    "2 related strategy id(s), state(s): needs_evidence, priority bucket(s): "
    "medium, with 3 limitation(s) and 20 non-claim(s)."
)
_BRIEF_TITLE = "Research queue brief: 1 section"
_BRIEF_SUMMARY = (
    "Research queue brief contains 1 candidate metadata section(s) with "
    "1 item(s), 3 limitation(s), and 20 non-claim(s)."
)


def build_synthetic_research_queue_status() -> ResearchQueueStatus:
    """Return the deterministic synthetic research queue status."""

    return build_research_queue_status(
        queue_id=_QUEUE_ID,
        title=_TITLE,
        research_state=_RESEARCH_STATE,
        priority_bucket=_PRIORITY_BUCKET,
        topic=_TOPIC,
        hypothesis=_HYPOTHESIS,
        blockers=_BLOCKERS,
        required_next_steps=_REQUIRED_NEXT_STEPS,
        evidence_gaps=_EVIDENCE_GAPS,
        related_strategy_ids=_RELATED_STRATEGY_IDS,
        evidence_refs=_EVIDENCE_REFS,
        limitations=_LIMITATIONS,
        non_claims=_NON_CLAIMS,
    )


def expected_synthetic_research_queue_status_dict() -> dict[str, object]:
    """Return the exact primitive research queue status payload."""

    return {
        "queue_type": "research_queue_status",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "queue_id": _QUEUE_ID,
        "title": _TITLE,
        "research_state": _RESEARCH_STATE,
        "priority_bucket": _PRIORITY_BUCKET,
        "topic": _TOPIC,
        "hypothesis": _HYPOTHESIS,
        "blockers": list(_BLOCKERS),
        "required_next_steps": list(_REQUIRED_NEXT_STEPS),
        "evidence_gaps": list(_EVIDENCE_GAPS),
        "related_strategy_ids": list(_RELATED_STRATEGY_IDS),
        "evidence_refs": list(_EVIDENCE_REFS),
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_NON_CLAIMS),
    }


def build_synthetic_research_queue_brief_item() -> ResearchQueueBriefItem:
    """Return the deterministic synthetic research queue brief item."""

    status = build_synthetic_research_queue_status()
    return build_research_queue_brief_item(status)


def expected_synthetic_research_queue_brief_item_dict() -> dict[str, object]:
    """Return the exact primitive research queue brief item payload."""

    source_status = expected_synthetic_research_queue_status_dict()
    return {
        "item_type": "research_queue_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "queue_id": source_status["queue_id"],
        "title": source_status["title"],
        "research_state": source_status["research_state"],
        "priority_bucket": source_status["priority_bucket"],
        "topic": source_status["topic"],
        "headline": _ITEM_HEADLINE,
        "summary": _ITEM_SUMMARY,
        "hypothesis": source_status["hypothesis"],
        "blockers": list(source_status["blockers"]),
        "required_next_steps": list(source_status["required_next_steps"]),
        "evidence_gaps": list(source_status["evidence_gaps"]),
        "related_strategy_ids": list(source_status["related_strategy_ids"]),
        "evidence_refs": list(source_status["evidence_refs"]),
        "limitations": list(source_status["limitations"]),
        "non_claims": list(source_status["non_claims"]),
        "source_status": source_status,
    }


def build_synthetic_research_queue_brief_section() -> ResearchQueueBriefSection:
    """Return the deterministic synthetic research queue brief section."""

    item = build_synthetic_research_queue_brief_item()
    return build_research_queue_brief_section((item,))


def expected_synthetic_research_queue_brief_section_dict() -> dict[str, object]:
    """Return the exact primitive research queue brief section payload."""

    item = expected_synthetic_research_queue_brief_item_dict()
    return {
        "section_type": "research_queue_brief_section",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _SECTION_TITLE,
        "summary": _SECTION_SUMMARY,
        "item_count": 1,
        "items": [item],
        "limitations": list(item["limitations"]),
        "non_claims": list(item["non_claims"]),
    }


def build_synthetic_research_queue_brief() -> ResearchQueueBrief:
    """Return the deterministic synthetic research queue brief."""

    section = build_synthetic_research_queue_brief_section()
    return build_research_queue_brief((section,))


def expected_synthetic_research_queue_brief_dict() -> dict[str, object]:
    """Return the exact primitive research queue brief payload."""

    section = expected_synthetic_research_queue_brief_section_dict()
    return {
        "brief_type": "research_queue_brief",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _BRIEF_TITLE,
        "summary": _BRIEF_SUMMARY,
        "section_count": 1,
        "sections": [section],
        "limitations": list(section["limitations"]),
        "non_claims": list(section["non_claims"]),
    }
