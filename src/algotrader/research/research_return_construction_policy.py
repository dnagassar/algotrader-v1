"""Research-only policy contract for future return construction."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError

__all__ = [
    "RESEARCH_RETURN_CONSTRUCTION_POLICY_STATES",
    "ResearchReturnConstructionPolicy",
    "build_research_return_construction_policy",
]

_POLICY_TYPE = "research_return_construction_policy"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_POLICY_SCOPE = "contract_only"
_SELECTED_PERIOD_TREATMENT = "carry_as_source_return_observations_only"
_EXCLUDED_PERIOD_TREATMENT = (
    "remain_excluded_without_zero_cash_or_strategy_mapping"
)
_MISSING_PERIOD_TREATMENT = "remain_missing_without_imputation"
_CASH_PROXY = None
_COSTS_INCLUDED = False
_SLIPPAGE_INCLUDED = False
_COMPOUNDING_ALLOWED = False
_STRATEGY_RETURNS_ALLOWED = False
_PORTFOLIO_RETURNS_ALLOWED = False
_CASH_RETURNS_ALLOWED = False
_EQUITY_CURVE_ALLOWED = False
_BACKTEST_ALLOWED = False
_RESULT_SCOPE = "descriptive_research_only"
RESEARCH_RETURN_CONSTRUCTION_POLICY_STATES = (
    "return_construction_policy_defined",
)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_REQUIRED_LIMITATIONS = (
    "defines a future return-construction policy contract only",
    "does not apply the policy to selected source return observations",
    "does not calculate strategy, portfolio, cash, compounded, or equity-curve returns",
    "excluded periods must remain excluded unless a future contract changes treatment",
    "selected periods may carry source return observations only",
)
_REQUIRED_NON_CLAIMS = (
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
)


@dataclass(frozen=True, slots=True)
class ResearchReturnConstructionPolicy:
    """Advisory-only contract for how future research returns may be built."""

    policy_type: str
    status: str
    authority: str
    capital_authority: bool
    research_scope: str
    policy_scope: str
    selected_period_treatment: str
    excluded_period_treatment: str
    missing_period_treatment: str
    cash_proxy: str | None
    costs_included: bool
    slippage_included: bool
    compounding_allowed: bool
    strategy_returns_allowed: bool
    portfolio_returns_allowed: bool
    cash_returns_allowed: bool
    equity_curve_allowed: bool
    backtest_allowed: bool
    result_scope: str
    policy_state: str
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            self.policy_type,
            self.status,
            self.authority,
            self.capital_authority,
            self.research_scope,
            self.policy_scope,
            self.selected_period_treatment,
            self.excluded_period_treatment,
            self.missing_period_treatment,
            self.cash_proxy,
            self.costs_included,
            self.slippage_included,
            self.compounding_allowed,
            self.strategy_returns_allowed,
            self.portfolio_returns_allowed,
            self.cash_returns_allowed,
            self.equity_curve_allowed,
            self.backtest_allowed,
            self.result_scope,
            self.policy_state,
        )
        object.__setattr__(
            self,
            "limitations",
            _exact_text_tuple(
                self.limitations,
                "limitations",
                _REQUIRED_LIMITATIONS,
            ),
        )
        object.__setattr__(
            self,
            "non_claims",
            _exact_text_tuple(self.non_claims, "non_claims", _REQUIRED_NON_CLAIMS),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only return-construction policy metadata."""

        return {
            "policy_type": self.policy_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "research_scope": self.research_scope,
            "policy_scope": self.policy_scope,
            "selected_period_treatment": self.selected_period_treatment,
            "excluded_period_treatment": self.excluded_period_treatment,
            "missing_period_treatment": self.missing_period_treatment,
            "cash_proxy": self.cash_proxy,
            "costs_included": self.costs_included,
            "slippage_included": self.slippage_included,
            "compounding_allowed": self.compounding_allowed,
            "strategy_returns_allowed": self.strategy_returns_allowed,
            "portfolio_returns_allowed": self.portfolio_returns_allowed,
            "cash_returns_allowed": self.cash_returns_allowed,
            "equity_curve_allowed": self.equity_curve_allowed,
            "backtest_allowed": self.backtest_allowed,
            "result_scope": self.result_scope,
            "policy_state": self.policy_state,
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_research_return_construction_policy() -> ResearchReturnConstructionPolicy:
    """Build the conservative research-only return-construction policy contract."""

    return ResearchReturnConstructionPolicy(
        policy_type=_POLICY_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        policy_scope=_POLICY_SCOPE,
        selected_period_treatment=_SELECTED_PERIOD_TREATMENT,
        excluded_period_treatment=_EXCLUDED_PERIOD_TREATMENT,
        missing_period_treatment=_MISSING_PERIOD_TREATMENT,
        cash_proxy=_CASH_PROXY,
        costs_included=_COSTS_INCLUDED,
        slippage_included=_SLIPPAGE_INCLUDED,
        compounding_allowed=_COMPOUNDING_ALLOWED,
        strategy_returns_allowed=_STRATEGY_RETURNS_ALLOWED,
        portfolio_returns_allowed=_PORTFOLIO_RETURNS_ALLOWED,
        cash_returns_allowed=_CASH_RETURNS_ALLOWED,
        equity_curve_allowed=_EQUITY_CURVE_ALLOWED,
        backtest_allowed=_BACKTEST_ALLOWED,
        result_scope=_RESULT_SCOPE,
        policy_state="return_construction_policy_defined",
        limitations=_REQUIRED_LIMITATIONS,
        non_claims=_REQUIRED_NON_CLAIMS,
    )


def _validate_fixed_metadata(
    policy_type: object,
    status: object,
    authority: object,
    capital_authority: object,
    research_scope: object,
    policy_scope: object,
    selected_period_treatment: object,
    excluded_period_treatment: object,
    missing_period_treatment: object,
    cash_proxy: object,
    costs_included: object,
    slippage_included: object,
    compounding_allowed: object,
    strategy_returns_allowed: object,
    portfolio_returns_allowed: object,
    cash_returns_allowed: object,
    equity_curve_allowed: object,
    backtest_allowed: object,
    result_scope: object,
    policy_state: object,
) -> None:
    _literal(policy_type, "policy_type", _POLICY_TYPE)
    _literal(status, "status", _STATUS)
    _literal(authority, "authority", _AUTHORITY)
    _false_bool(capital_authority, "capital_authority")
    _literal(research_scope, "research_scope", _RESEARCH_SCOPE)
    _literal(policy_scope, "policy_scope", _POLICY_SCOPE)
    _literal(
        selected_period_treatment,
        "selected_period_treatment",
        _SELECTED_PERIOD_TREATMENT,
    )
    _literal(
        excluded_period_treatment,
        "excluded_period_treatment",
        _EXCLUDED_PERIOD_TREATMENT,
    )
    _literal(
        missing_period_treatment,
        "missing_period_treatment",
        _MISSING_PERIOD_TREATMENT,
    )
    if cash_proxy is not None:
        raise ValidationError("cash_proxy must be None.")
    _false_bool(costs_included, "costs_included")
    _false_bool(slippage_included, "slippage_included")
    _false_bool(compounding_allowed, "compounding_allowed")
    _false_bool(strategy_returns_allowed, "strategy_returns_allowed")
    _false_bool(portfolio_returns_allowed, "portfolio_returns_allowed")
    _false_bool(cash_returns_allowed, "cash_returns_allowed")
    _false_bool(equity_curve_allowed, "equity_curve_allowed")
    _false_bool(backtest_allowed, "backtest_allowed")
    _literal(result_scope, "result_scope", _RESULT_SCOPE)
    _policy_state(policy_state)


def _literal(value: object, field_name: str, expected: str) -> None:
    if value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")


def _false_bool(value: object, field_name: str) -> None:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    if value is not False:
        raise ValidationError(f"{field_name} must be False.")


def _policy_state(value: object) -> str:
    state = _required_string(value, "policy_state")
    if state not in RESEARCH_RETURN_CONSTRUCTION_POLICY_STATES:
        allowed = ", ".join(RESEARCH_RETURN_CONSTRUCTION_POLICY_STATES)
        raise ValidationError(f"policy_state must be one of: {allowed}.")

    return state


def _exact_text_tuple(
    values: object,
    field_name: str,
    expected: tuple[str, ...],
) -> tuple[str, ...]:
    items = tuple(dict.fromkeys(_string_tuple(values, field_name)))
    if items != expected:
        raise ValidationError(f"{field_name} must match required policy text.")

    return items


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value
