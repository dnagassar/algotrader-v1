from __future__ import annotations

import ast
from pathlib import Path

from algotrader.research.options_feasibility_gate import (
    DEFINED_RISK_OPTION_STRUCTURES,
    FORBIDDEN_OPTION_STRUCTURES,
    OPTIONS_FEASIBILITY_REQUIRED_CONTROLS,
    OptionsFeasibilityInput,
    evaluate_options_feasibility,
)


MODULE_PATH = Path("src/algotrader/research/options_feasibility_gate.py")


def test_options_feasibility_gate_defaults_to_blocked() -> None:
    decision = evaluate_options_feasibility()

    assert decision.classification == "blocked"
    assert decision.blocked is True
    assert decision.minimum_controls_satisfied is False
    assert decision.paper_preview_candidate is False
    assert decision.paper_mutation_candidate is False
    assert decision.broker_mutation_allowed is False
    assert decision.live_options_trading_allowed is False
    assert {
        "options_not_authorized",
        "feasibility_only",
        "data_requirements_missing",
        "broker_capability_unverified",
        "risk_model_missing",
        "approval_required_before_preview",
        "mutation_forbidden",
        "live_options_trading_forbidden",
        "separate_options_adapter_required",
    } <= set(decision.statuses)


def test_undefined_risk_and_naked_structures_are_rejected() -> None:
    for structure in FORBIDDEN_OPTION_STRUCTURES:
        decision = evaluate_options_feasibility(
            _complete_input(structure_category=structure)
        )

        assert decision.classification == "blocked"
        assert decision.blocked is True
        assert decision.defined_risk_structure is False
        assert "defined_risk_required" in decision.statuses
        assert f"forbidden_structure:{structure}" in decision.blockers
        assert decision.paper_preview_candidate is False
        assert decision.paper_mutation_candidate is False


def test_defined_risk_structures_remain_feasibility_only_when_inputs_are_missing() -> None:
    for structure in DEFINED_RISK_OPTION_STRUCTURES:
        decision = evaluate_options_feasibility(
            OptionsFeasibilityInput(
                structure_category=structure,
                explicit_user_authorization=True,
            )
        )

        assert decision.classification == "blocked"
        assert decision.defined_risk_structure is True
        assert "feasibility_only" in decision.statuses
        assert "data_requirements_missing" in decision.statuses
        assert "risk_model_missing" in decision.statuses
        assert decision.minimum_controls_satisfied is False
        assert decision.paper_preview_candidate is False
        assert decision.paper_mutation_candidate is False


def test_defined_risk_controls_can_be_satisfied_without_creating_trading_authority() -> None:
    decision = evaluate_options_feasibility(_complete_input())

    assert decision.classification == "feasibility_only"
    assert decision.blocked is False
    assert decision.minimum_controls_satisfied is True
    assert decision.missing_controls == ()
    assert decision.statuses == (
        "mutation_forbidden",
        "live_options_trading_forbidden",
        "feasibility_only",
    )
    assert decision.paper_preview_candidate is False
    assert decision.paper_mutation_candidate is False
    assert decision.broker_mutation_allowed is False
    assert decision.live_options_trading_allowed is False


def test_action_requests_remain_forbidden_even_with_complete_controls() -> None:
    decision = evaluate_options_feasibility(
        _complete_input(
            paper_action_requested=True,
            broker_mutation_requested=True,
            live_action_requested=True,
        )
    )

    assert decision.classification == "blocked"
    assert decision.blocked is True
    assert "mutation_forbidden" in decision.statuses
    assert "live_options_trading_forbidden" in decision.statuses
    assert "options_action_request_forbidden" in decision.blockers
    assert decision.paper_preview_candidate is False
    assert decision.paper_mutation_candidate is False


def test_required_controls_cover_data_pricing_risk_approval_and_broker_boundaries() -> None:
    decision = evaluate_options_feasibility()

    assert decision.required_controls == OPTIONS_FEASIBILITY_REQUIRED_CONTROLS
    assert {
        "explicit_user_authorization",
        "verified_options_market_data_source",
        "deterministic_contract_selection_rules",
        "max_loss_calculation",
        "liquidity_check",
        "spread_check",
        "open_interest_check",
        "assignment_exercise_risk_handling",
        "broker_capability_verification",
        "separate_options_adapter_registry",
        "live_options_trading_prohibited",
    } == set(decision.required_controls)
    assert decision.defined_risk_structures == DEFINED_RISK_OPTION_STRUCTURES
    assert decision.forbidden_structures == FORBIDDEN_OPTION_STRUCTURES


def test_options_feasibility_code_imports_no_broker_network_or_credentials() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    forbidden_prefixes = (
        "algotrader.execution",
        "algotrader.orchestration",
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "os",
        "requests",
        "socket",
        "urllib",
    )
    credential_terms = (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    )
    import_modules = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]
    import_modules.extend(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in import_modules
        for prefix in forbidden_prefixes
    )
    assert all(term not in text for term in credential_terms)
    assert "submit_order" not in text


def _complete_input(**overrides: object) -> OptionsFeasibilityInput:
    values = {
        "structure_category": "defined_risk_spread",
        "explicit_user_authorization": True,
        "verified_options_market_data_source": True,
        "deterministic_contract_selection_rules": True,
        "max_loss_calculation": True,
        "liquidity_check": True,
        "spread_check": True,
        "open_interest_check": True,
        "assignment_exercise_risk_handling": True,
        "broker_capability_verification": True,
        "separate_options_adapter_registry": True,
        "live_options_trading_prohibited": True,
        "paper_action_requested": False,
        "broker_mutation_requested": False,
        "live_action_requested": False,
    }
    values.update(overrides)
    return OptionsFeasibilityInput(**values)
