"""Deterministic synthetic research return-construction policy fixtures."""

from __future__ import annotations

from algotrader.research.research_return_construction_policy import (
    ResearchReturnConstructionPolicy,
    build_research_return_construction_policy,
)

__all__ = [
    "build_synthetic_research_return_construction_policy",
    "expected_synthetic_research_return_construction_policy_dict",
]


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def build_synthetic_research_return_construction_policy() -> (
    ResearchReturnConstructionPolicy
):
    """Return the deterministic conservative return-construction policy."""

    return build_research_return_construction_policy()


def expected_synthetic_research_return_construction_policy_dict() -> dict[str, object]:
    """Return the exact primitive synthetic return-construction policy payload."""

    return {
        "policy_type": "research_return_construction_policy",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "research_scope": "research_only",
        "policy_scope": "contract_only",
        "selected_period_treatment": "carry_as_source_return_observations_only",
        "excluded_period_treatment": (
            "remain_excluded_without_zero_cash_or_strategy_mapping"
        ),
        "missing_period_treatment": "remain_missing_without_imputation",
        "cash_proxy": None,
        "costs_included": False,
        "slippage_included": False,
        "compounding_allowed": False,
        "strategy_returns_allowed": False,
        "portfolio_returns_allowed": False,
        "cash_returns_allowed": False,
        "equity_curve_allowed": False,
        "backtest_allowed": False,
        "result_scope": "descriptive_research_only",
        "policy_state": "return_construction_policy_defined",
        "limitations": [
            "defines a future return-construction policy contract only",
            "does not apply the policy to selected source return observations",
            (
                "does not calculate strategy, portfolio, cash, compounded, "
                "or equity-curve returns"
            ),
            (
                "excluded periods must remain excluded unless a future contract "
                "changes treatment"
            ),
            "selected periods may carry source return observations only",
        ],
        "non_claims": [
            _not("strategy-return computation"),
            _not("portfolio-return computation"),
            _not("cash-return computation"),
            _not("equity-curve computation"),
            _not("compounded-return computation"),
            _not("cost model"),
            _not("slippage model"),
            _not("cash proxy"),
            _not("zero-fill of excluded periods"),
            _not("missing-return imputation"),
            _not("strategy performance result"),
            _not("portfolio performance result"),
            _not("invested performance result"),
            _not("backtest result"),
            _not("allocation or order authority"),
            _not("broker authority"),
            _not("capital authority"),
            _not("trading authority"),
        ],
    }
