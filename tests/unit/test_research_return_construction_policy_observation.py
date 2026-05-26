from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_construction_policy import (
    ResearchReturnConstructionPolicy,
    build_research_return_construction_policy,
)
from algotrader.research.research_return_construction_policy_observation import (
    ResearchReturnConstructionPolicyObservation,
    build_research_return_construction_policy_observation,
)
from tests.fixtures.research_return_construction_policy import (
    expected_synthetic_research_return_construction_policy_dict,
)


MODULE_PATH = Path(
    "src/algotrader/research/research_return_construction_policy_observation.py"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.research_return_construction_policy",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "duckdb",
    "httpx",
    "numpy",
    "openai",
    "os",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
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
    "open",
    "os.getenv",
    "read_csv",
    "read_text",
    "request",
    "simple_return",
    "time.time",
    "write_text",
}
_FORBIDDEN_FIELD_FRAGMENTS = (
    "broker",
    "account",
    "order",
    "fill",
    "position",
    "portfolio",
    "cash",
    "equity",
    "pnl",
    "return_series",
    "backtest",
    "benchmark",
    "allocation",
    "signal",
    "execution",
    "live",
    "paper",
    "readiness",
    "approval",
)


def test_builds_policy_observation_for_exact_phase_247_policy() -> None:
    policy_result_or_policy = build_research_return_construction_policy()

    observation = build_research_return_construction_policy_observation(
        policy_result_or_policy
    )

    assert type(policy_result_or_policy) is ResearchReturnConstructionPolicy
    assert type(observation) is ResearchReturnConstructionPolicyObservation
    assert observation.source_policy is policy_result_or_policy
    assert observation.observation_type == (
        "research_return_construction_policy_observation"
    )
    assert observation.advisory_scope == "policy_contract_observation_only"
    assert observation.policy_state == "return_construction_policy_defined"


def test_builder_rejects_lookalikes_unrelated_objects_and_subclasses() -> None:
    class PolicyLookalike:
        policy_state = "return_construction_policy_defined"

        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_research_return_construction_policy_dict()

    class DerivedPolicy(ResearchReturnConstructionPolicy):
        pass

    policy = build_research_return_construction_policy()
    subclass_policy = DerivedPolicy(**_policy_payload(policy))

    for value in (object(), PolicyLookalike(), subclass_policy):
        with pytest.raises(ValidationError, match="ResearchReturnConstructionPolicy"):
            build_research_return_construction_policy_observation(value)  # type: ignore[arg-type]


def test_source_policy_identity_is_preserved() -> None:
    policy = build_research_return_construction_policy()

    first = build_research_return_construction_policy_observation(policy)
    second = build_research_return_construction_policy_observation(policy)

    assert first.source_policy is policy
    assert second.source_policy is policy
    assert first.source_policy is second.source_policy


def test_period_and_source_return_counts_are_deterministic_zeros() -> None:
    policy = build_research_return_construction_policy()
    observation = build_research_return_construction_policy_observation(policy)

    assert observation.selected_period_count == 0
    assert observation.excluded_period_count == 0
    assert observation.source_return_observation_count == 0
    assert observation.forbidden_output_count == 0

    payload = observation.to_dict()
    assert payload["selected_period_count"] == 0
    assert payload["excluded_period_count"] == 0
    assert payload["source_return_observation_count"] == 0
    assert payload["forbidden_output_count"] == 0


def test_empty_selected_periods_serialize_deterministically() -> None:
    observation = build_research_return_construction_policy_observation(
        build_research_return_construction_policy()
    )
    first = observation.to_dict()
    second = observation.to_dict()

    assert first["selected_period_count"] == second["selected_period_count"] == 0
    assert "selected_periods" not in first
    assert _compact_json(first) == _compact_json(second)


def test_empty_excluded_periods_serialize_deterministically() -> None:
    observation = build_research_return_construction_policy_observation(
        build_research_return_construction_policy()
    )
    first = observation.to_dict()
    second = observation.to_dict()

    assert first["excluded_period_count"] == second["excluded_period_count"] == 0
    assert "excluded_periods" not in first
    assert _compact_json(first) == _compact_json(second)


def test_to_dict_is_primitive_only_json_round_trippable_and_nests_policy() -> None:
    policy = build_research_return_construction_policy()
    observation = build_research_return_construction_policy_observation(policy)
    payload = observation.to_dict()
    expected_policy = expected_synthetic_research_return_construction_policy_dict()

    assert payload == {
        "observation_type": "research_return_construction_policy_observation",
        "advisory_scope": "policy_contract_observation_only",
        "policy_state": "return_construction_policy_defined",
        "selected_period_count": 0,
        "excluded_period_count": 0,
        "source_return_observation_count": 0,
        "forbidden_output_count": 0,
        "source_policy": expected_policy,
    }
    assert tuple(payload) == (
        "observation_type",
        "advisory_scope",
        "policy_state",
        "selected_period_count",
        "excluded_period_count",
        "source_return_observation_count",
        "forbidden_output_count",
        "source_policy",
    )
    assert _primitive_only(payload)
    assert json.loads(_compact_json(payload)) == payload
    assert payload["source_policy"] == policy.to_dict()


def test_repeated_builds_and_to_dict_calls_are_byte_for_byte_deterministic() -> None:
    policy = build_research_return_construction_policy()

    first = build_research_return_construction_policy_observation(policy)
    second = build_research_return_construction_policy_observation(policy)

    first_payload = first.to_dict()
    second_payload = second.to_dict()

    assert first_payload == second_payload
    assert _compact_json(first_payload) == _compact_json(second_payload)
    assert _compact_json(first.to_dict()) == _compact_json(first.to_dict())


def test_direct_construction_validates_source_policy_and_zero_counts() -> None:
    policy = build_research_return_construction_policy()
    payload = _observation_payload(policy)

    for field_name, value in (
        ("observation_type", "other"),
        ("advisory_scope", "other"),
        ("policy_state", "other"),
        ("selected_period_count", 1),
        ("excluded_period_count", 1),
        ("source_return_observation_count", 1),
        ("forbidden_output_count", 1),
        ("source_policy", object()),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            ResearchReturnConstructionPolicyObservation(**mutated)


def test_count_fields_reject_bool_and_non_integer_values() -> None:
    policy = build_research_return_construction_policy()
    payload = _observation_payload(policy)

    for field_name in (
        "selected_period_count",
        "excluded_period_count",
        "source_return_observation_count",
        "forbidden_output_count",
    ):
        for value in (False, "0"):
            mutated = dict(payload)
            mutated[field_name] = value
            with pytest.raises(ValidationError, match=field_name):
                ResearchReturnConstructionPolicyObservation(**mutated)


def test_object_is_frozen_and_slotted() -> None:
    policy = build_research_return_construction_policy()
    observation = build_research_return_construction_policy_observation(policy)

    assert hasattr(ResearchReturnConstructionPolicyObservation, "__slots__")
    assert tuple(
        field.name for field in fields(ResearchReturnConstructionPolicyObservation)
    ) == (
        "observation_type",
        "advisory_scope",
        "policy_state",
        "selected_period_count",
        "excluded_period_count",
        "source_return_observation_count",
        "forbidden_output_count",
        "source_policy",
    )
    with pytest.raises(FrozenInstanceError):
        observation.policy_state = "other"
    with pytest.raises((AttributeError, TypeError)):
        observation.extra_field = "not allowed"


def test_no_forbidden_top_level_fields_or_outputs_are_exposed() -> None:
    policy = build_research_return_construction_policy()
    observation = build_research_return_construction_policy_observation(policy)
    field_names = {
        field.name for field in fields(ResearchReturnConstructionPolicyObservation)
    }
    top_level_payload_keys = set(observation.to_dict())

    for name in field_names | top_level_payload_keys:
        assert not _contains_forbidden_fragment(name)

    assert observation.to_dict()["source_policy"] == policy.to_dict()


def test_module_imports_no_forbidden_dependencies() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert all(not module_name.startswith("tests") for module_name in imports)


def test_module_has_no_forbidden_runtime_or_return_construction_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def _policy_payload(policy: ResearchReturnConstructionPolicy) -> dict[str, object]:
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


def _observation_payload(
    policy: ResearchReturnConstructionPolicy,
) -> dict[str, object]:
    return {
        "observation_type": "research_return_construction_policy_observation",
        "advisory_scope": "policy_contract_observation_only",
        "policy_state": policy.policy_state,
        "selected_period_count": 0,
        "excluded_period_count": 0,
        "source_return_observation_count": 0,
        "forbidden_output_count": 0,
        "source_policy": policy,
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


def _contains_forbidden_fragment(name: str) -> bool:
    return any(fragment in name for fragment in _FORBIDDEN_FIELD_FRAGMENTS)


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


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


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
