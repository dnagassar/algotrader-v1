from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_construction_policy import (
    RESEARCH_RETURN_CONSTRUCTION_POLICY_STATES,
    ResearchReturnConstructionPolicy,
    build_research_return_construction_policy,
)
from tests.fixtures.research_return_construction_policy import (
    build_synthetic_research_return_construction_policy,
    expected_synthetic_research_return_construction_policy_dict,
)


MODULE_PATH = Path(
    "src/algotrader/research/research_return_construction_policy.py"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "duckdb",
    "httpx",
    "numpy",
    "openai",
    "os",
    "pandas",
    "requests",
    "socket",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "build_research_return_summary_observation",
    "build_sma_selected_source_return_series_observation",
    "close_to_close_returns",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "eval",
    "exec",
    "getenv",
    "json.dump",
    "json.load",
    "max",
    "mean",
    "min",
    "open",
    "os.getenv",
    "read_csv",
    "read_text",
    "request",
    "simple_return",
    "sum",
    "time.time",
    "write_text",
}
_FORBIDDEN_REFERENCE_NAMES = {
    "ResearchReturnSeriesObservation",
    "SmaConditionalReturnSelectionObservation",
    "SmaSelectedSourceReturnSeriesObservation",
    "build_research_return_summary_observation",
    "build_sma_selected_source_return_series_observation",
    "close_to_close_returns",
    "simple_return",
}


def test_builds_conservative_research_only_policy_contract() -> None:
    policy = build_research_return_construction_policy()
    expected = expected_synthetic_research_return_construction_policy_dict()

    assert type(policy) is ResearchReturnConstructionPolicy
    assert policy.policy_type == "research_return_construction_policy"
    assert policy.status == "candidate_only"
    assert policy.authority == "advisory_only"
    assert policy.capital_authority is False
    assert policy.research_scope == "research_only"
    assert policy.policy_scope == "contract_only"
    assert (
        policy.selected_period_treatment
        == "carry_as_source_return_observations_only"
    )
    assert (
        policy.excluded_period_treatment
        == "remain_excluded_without_zero_cash_or_strategy_mapping"
    )
    assert policy.missing_period_treatment == "remain_missing_without_imputation"
    assert policy.cash_proxy is None
    assert policy.costs_included is False
    assert policy.slippage_included is False
    assert policy.compounding_allowed is False
    assert policy.strategy_returns_allowed is False
    assert policy.portfolio_returns_allowed is False
    assert policy.cash_returns_allowed is False
    assert policy.equity_curve_allowed is False
    assert policy.backtest_allowed is False
    assert policy.result_scope == "descriptive_research_only"
    assert policy.policy_state == "return_construction_policy_defined"
    assert policy.to_dict() == expected
    assert tuple(policy.to_dict()) == tuple(expected)


def test_policy_states_are_pinned() -> None:
    assert set(RESEARCH_RETURN_CONSTRUCTION_POLICY_STATES) == {
        "return_construction_policy_defined",
    }


def test_direct_construction_rejects_hidden_return_assumptions() -> None:
    policy = build_synthetic_research_return_construction_policy()
    payload = _direct_payload(policy)

    for field_name, value in (
        ("policy_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("research_scope", "other"),
        ("policy_scope", "applied"),
        ("selected_period_treatment", "strategy_return"),
        ("excluded_period_treatment", "zero_fill"),
        ("missing_period_treatment", "cash_imputation"),
        ("cash_proxy", "BIL"),
        ("costs_included", True),
        ("slippage_included", True),
        ("compounding_allowed", True),
        ("strategy_returns_allowed", True),
        ("portfolio_returns_allowed", True),
        ("cash_returns_allowed", True),
        ("equity_curve_allowed", True),
        ("backtest_allowed", True),
        ("result_scope", "strategy_performance"),
        ("policy_state", "other"),
        ("limitations", ("defines a future return-construction policy contract only",)),
        ("non_claims", ("not strategy-return computation",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            ResearchReturnConstructionPolicy(**mutated)


def test_bool_fields_reject_non_bool_falsey_values() -> None:
    policy = build_synthetic_research_return_construction_policy()
    payload = _direct_payload(policy)

    for field_name in (
        "capital_authority",
        "costs_included",
        "slippage_included",
        "compounding_allowed",
        "strategy_returns_allowed",
        "portfolio_returns_allowed",
        "cash_returns_allowed",
        "equity_curve_allowed",
        "backtest_allowed",
    ):
        mutated = dict(payload)
        mutated[field_name] = 0
        with pytest.raises(ValidationError, match=field_name):
            ResearchReturnConstructionPolicy(**mutated)


def test_limitations_and_non_claims_are_required_and_deduped() -> None:
    policy = build_synthetic_research_return_construction_policy()
    payload = _direct_payload(policy)
    payload["limitations"] = (*policy.limitations, policy.limitations[0])
    payload["non_claims"] = (*policy.non_claims, policy.non_claims[0])

    reconstructed = ResearchReturnConstructionPolicy(**payload)

    assert reconstructed.limitations == policy.limitations
    assert reconstructed.non_claims == policy.non_claims


def test_to_dict_is_primitive_only_deterministic_and_returns_fresh_lists() -> None:
    first = build_synthetic_research_return_construction_policy().to_dict()
    second = build_synthetic_research_return_construction_policy().to_dict()
    expected = expected_synthetic_research_return_construction_policy_dict()
    first_json = _compact_json(first)
    second_json = _compact_json(second)

    assert first == second == expected
    assert _primitive_only(first)
    assert first_json == second_json
    assert json.loads(first_json) == expected
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == expected
    assert build_synthetic_research_return_construction_policy().to_dict() == expected


def test_object_is_frozen_and_slotted() -> None:
    policy = build_synthetic_research_return_construction_policy()

    assert hasattr(ResearchReturnConstructionPolicy, "__slots__")
    assert tuple(field.name for field in fields(ResearchReturnConstructionPolicy)) == (
        "policy_type",
        "status",
        "authority",
        "capital_authority",
        "research_scope",
        "policy_scope",
        "selected_period_treatment",
        "excluded_period_treatment",
        "missing_period_treatment",
        "cash_proxy",
        "costs_included",
        "slippage_included",
        "compounding_allowed",
        "strategy_returns_allowed",
        "portfolio_returns_allowed",
        "cash_returns_allowed",
        "equity_curve_allowed",
        "backtest_allowed",
        "result_scope",
        "policy_state",
        "limitations",
        "non_claims",
    )
    with pytest.raises(FrozenInstanceError):
        policy.result_scope = "strategy_performance"
    with pytest.raises((AttributeError, TypeError)):
        policy.extra_field = "not allowed"


def test_no_from_dict_apply_or_return_calculation_api_exists() -> None:
    policy = build_synthetic_research_return_construction_policy()
    function_names = _function_names()

    assert not hasattr(ResearchReturnConstructionPolicy, "from_dict")
    assert not hasattr(policy, "from_dict")
    assert "from_dict" not in function_names
    assert "from_dict" not in _call_names()
    assert [
        name
        for name in function_names
        if name.startswith(("apply_", "calculate_", "compound_", "backtest_"))
    ] == []


def test_module_imports_no_source_artifacts_trading_paths_or_data_libraries() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert all(not module_name.startswith("tests") for module_name in imports)


def test_module_references_no_source_artifacts_or_return_construction_math() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert _operator_nodes() == []


def _direct_payload(
    policy: ResearchReturnConstructionPolicy,
) -> dict[str, object]:
    return {
        "policy_type": policy.policy_type,
        "status": policy.status,
        "authority": policy.authority,
        "capital_authority": policy.capital_authority,
        "research_scope": policy.research_scope,
        "policy_scope": policy.policy_scope,
        "selected_period_treatment": policy.selected_period_treatment,
        "excluded_period_treatment": policy.excluded_period_treatment,
        "missing_period_treatment": policy.missing_period_treatment,
        "cash_proxy": policy.cash_proxy,
        "costs_included": policy.costs_included,
        "slippage_included": policy.slippage_included,
        "compounding_allowed": policy.compounding_allowed,
        "strategy_returns_allowed": policy.strategy_returns_allowed,
        "portfolio_returns_allowed": policy.portfolio_returns_allowed,
        "cash_returns_allowed": policy.cash_returns_allowed,
        "equity_curve_allowed": policy.equity_curve_allowed,
        "backtest_allowed": policy.backtest_allowed,
        "result_scope": policy.result_scope,
        "policy_state": policy.policy_state,
        "limitations": policy.limitations,
        "non_claims": policy.non_claims,
    }


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _referenced_names() -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _operator_nodes() -> list[str]:
    return [
        type(node).__name__
        for node in ast.walk(_tree())
        if isinstance(node, ast.AugAssign)
        or (isinstance(node, ast.BinOp) and not isinstance(node.op, ast.BitOr))
    ]


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
