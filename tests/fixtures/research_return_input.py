"""Synthetic ResearchReturnInputSnapshot fixture."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from algotrader.research.research_return_input import ResearchReturnInputSnapshot

__all__ = [
    "build_synthetic_research_return_input_snapshot",
    "expected_synthetic_research_return_input_snapshot_dict",
]


_NON_CLAIMS = (
    "not source approval",
    "not data approval",
    "not endpoint approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not evidence approval",
    "not return-construction approval",
    "not no-lookahead approval",
    "not strategy validation",
    "not trading readiness",
)


def build_synthetic_research_return_input_snapshot() -> ResearchReturnInputSnapshot:
    """Return a deterministic synthetic-only return-input snapshot."""

    return ResearchReturnInputSnapshot(
        snapshot_id="synthetic_return_input_snapshot_fixture_001",
        symbol="SYNRET121X",
        observation_dates=(
            date(2099, 1, 3),
            date(2099, 1, 4),
            date(2099, 1, 7),
        ),
        close_values=(
            Decimal("10.0000"),
            Decimal("10.5000"),
            Decimal("9.9750"),
        ),
        close_to_close_returns=(
            Decimal("0.05"),
            Decimal("-0.05"),
        ),
        return_basis="synthetic_prepared_close_to_close_simple_return_input",
        adjustment_policy="synthetic_prepared_values_no_external_adjustments",
        synthetic_only=True,
        candidate_only=True,
        non_claims=_NON_CLAIMS,
    )


def expected_synthetic_research_return_input_snapshot_dict() -> dict[str, object]:
    """Return the pinned primitive payload for the synthetic snapshot fixture."""

    return {
        "snapshot_id": "synthetic_return_input_snapshot_fixture_001",
        "symbol": "SYNRET121X",
        "observation_dates": ["2099-01-03", "2099-01-04", "2099-01-07"],
        "close_values": ["10.0000", "10.5000", "9.9750"],
        "close_to_close_returns": ["0.05", "-0.05"],
        "return_basis": "synthetic_prepared_close_to_close_simple_return_input",
        "adjustment_policy": "synthetic_prepared_values_no_external_adjustments",
        "synthetic_only": True,
        "candidate_only": True,
        "non_claims": list(_NON_CLAIMS),
    }
