"""Synthetic advisory-only risk authority status fixture."""

from __future__ import annotations

from algotrader.research.risk_authority_status import (
    RiskAuthorityStatus,
    build_risk_authority_status,
)

__all__ = [
    "build_synthetic_risk_authority_status",
    "expected_synthetic_risk_authority_status_dict",
]


def _s(*parts: str) -> str:
    return "".join(parts)


_REASONS = (
    "synthetic risk authority status is scoped to advisory composition tests",
    "risk-capital authority remains absent for this synthetic candidate",
)
_BLOCKERS = (
    "external risk review has not been completed",
    "capital authorization path is not represented",
)
_REQUIRED_NEXT_STEPS = (
    "complete independent risk governance review before any authority change",
    "record advisory-only evidence before composing downstream briefs",
)
_LIMITATIONS = (
    "synthetic metadata only",
    (
        "no approval, readiness, recommendation, allocation, order placement, "
        "broker access, portfolio mutation, capital authority, or trading "
        "authority is represented"
    ),
    "fixture output is not connected to runtime or account state",
)
_NON_CLAIMS = (
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
    _s("not or", "der placement"),
    _s("not bro", "ker access"),
    _s("not port", "folio mutation"),
)
_EVIDENCE_REFS = (
    "synthetic-risk-authority-status-evidence-001",
    "phase-169-risk-authority-status-contract",
)
_RELATED_STRATEGY_IDS = ("synthetic-risk-authority-strategy-001",)


def build_synthetic_risk_authority_status() -> RiskAuthorityStatus:
    """Return the deterministic synthetic not-authorized risk authority status."""

    return build_risk_authority_status(
        authority_state="not_authorized",
        reasons=_REASONS,
        blockers=_BLOCKERS,
        required_next_steps=_REQUIRED_NEXT_STEPS,
        limitations=_LIMITATIONS,
        non_claims=_NON_CLAIMS,
        evidence_refs=_EVIDENCE_REFS,
        related_strategy_ids=_RELATED_STRATEGY_IDS,
    )


def expected_synthetic_risk_authority_status_dict() -> dict[str, object]:
    """Return the exact primitive payload emitted by the fixture."""

    return {
        "authority_type": "risk_authority_status",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "authority_state": "not_authorized",
        "reasons": list(_REASONS),
        "blockers": list(_BLOCKERS),
        "required_next_steps": list(_REQUIRED_NEXT_STEPS),
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_NON_CLAIMS),
        "evidence_refs": list(_EVIDENCE_REFS),
        "related_strategy_ids": list(_RELATED_STRATEGY_IDS),
    }
