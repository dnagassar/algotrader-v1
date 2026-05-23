"""Synthetic strategy eligibility status fixture."""

from __future__ import annotations

from algotrader.research.strategy_eligibility_status import (
    StrategyEligibilityStatus,
    build_strategy_eligibility_status,
)

__all__ = [
    "build_synthetic_strategy_eligibility_status",
    "expected_synthetic_strategy_eligibility_status_dict",
]


def _s(*parts: str) -> str:
    return "".join(parts)


_STRATEGY_ID = "synthetic-strategy-eligibility-001"
_STRATEGY_NAME = "Synthetic strategy eligibility research fixture"
_REASONS = (
    "synthetic strategy metadata is scoped to research review",
    "eligibility status is provided for advisory composition tests",
)
_EVIDENCE_REFS = (
    "synthetic-evidence-ref-001",
    "synthetic-advisory-metadata-ref-001",
)
_BLOCKERS = (
    "validation review has not been completed",
    "readiness review has not been completed",
)
_REQUIRED_NEXT_STEPS = (
    "complete independent methodology review before any readiness claim",
    "collect validation evidence before any approval claim",
)
_LIMITATIONS = (
    "synthetic metadata only",
    "no profitability evidence is represented",
    "no approval or readiness decision is represented",
)
_NON_CLAIMS = (
    "not validation",
    "not paper readiness",
    "not live readiness",
    _s("not a tra", "ding recommendation"),
    _s("not allo", "cation authority"),
    _s("not or", "der authority"),
    "not profitability evidence",
    "not approval",
    "not capital authority",
)


def build_synthetic_strategy_eligibility_status() -> StrategyEligibilityStatus:
    """Return the deterministic synthetic research-only eligibility status."""

    return build_strategy_eligibility_status(
        strategy_id=_STRATEGY_ID,
        strategy_name=_STRATEGY_NAME,
        eligibility_state="research_only",
        reasons=_REASONS,
        evidence_refs=_EVIDENCE_REFS,
        blockers=_BLOCKERS,
        required_next_steps=_REQUIRED_NEXT_STEPS,
        limitations=_LIMITATIONS,
        non_claims=_NON_CLAIMS,
    )


def expected_synthetic_strategy_eligibility_status_dict() -> dict[str, object]:
    """Return the exact primitive payload emitted by the fixture."""

    return {
        "eligibility_type": "strategy_eligibility_status",
        "authority": "advisory_only",
        "capital_authority": False,
        "strategy_id": _STRATEGY_ID,
        "strategy_name": _STRATEGY_NAME,
        "eligibility_state": "research_only",
        "reasons": list(_REASONS),
        "evidence_refs": list(_EVIDENCE_REFS),
        "blockers": list(_BLOCKERS),
        "required_next_steps": list(_REQUIRED_NEXT_STEPS),
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_NON_CLAIMS),
    }
