from decimal import Decimal

import pytest

from algotrader.errors import ValidationError
from algotrader.orchestration.scenarios import (
    BROKER_SCENARIO_NAMES,
    SCENARIO_NAMES,
    run_broker_scenario,
    run_scenario,
)


@pytest.mark.parametrize("scenario_name", SCENARIO_NAMES)
def test_each_scenario_runs(scenario_name: str) -> None:
    scenario = run_scenario(scenario_name)

    assert scenario.name == scenario_name
    assert scenario.result.status in {"no_signal", "rejected", "open", "filled"}


def test_approved_and_filled_scenario() -> None:
    scenario = run_scenario("approved_and_filled")

    assert scenario.result.status == "filled"
    assert scenario.result.execution.filled is True
    assert scenario.result.valuation is not None


def test_rejected_insufficient_cash_scenario() -> None:
    scenario = run_scenario("rejected_insufficient_cash")

    assert scenario.result.status == "rejected"
    assert scenario.result.trade_flow.risk.reason == "insufficient_cash"
    assert scenario.result.execution is None


def test_no_signal_scenario() -> None:
    scenario = run_scenario("no_signal")

    assert scenario.result.status == "no_signal"
    assert scenario.result.order is None
    assert scenario.result.execution is None


def test_unfilled_limit_order_scenario() -> None:
    scenario = run_scenario("unfilled_limit_order")

    assert scenario.result.status == "open"
    assert scenario.result.order is not None
    assert scenario.result.execution.fill is None


def test_unknown_scenario_is_rejected_clearly() -> None:
    with pytest.raises(ValidationError):
        run_scenario("unknown")


@pytest.mark.parametrize("scenario_name", BROKER_SCENARIO_NAMES)
def test_each_broker_scenario_runs(scenario_name: str) -> None:
    scenario = run_broker_scenario(scenario_name)

    assert scenario.name == scenario_name
    assert scenario.status in {"rejected", "open", "filled"}


def test_broker_approved_order_fills_through_local_broker() -> None:
    scenario = run_broker_scenario("broker_approved_and_filled")

    assert scenario.status == "filled"
    assert scenario.submitted is True
    assert scenario.risk.allowed is True
    assert scenario.broker_result.accepted is True
    assert scenario.broker_result.filled is True
    assert scenario.portfolio.position("MSFT").quantity == Decimal("1")
    assert scenario.valuation.total_market_value == Decimal("999.99")


def test_broker_rejected_order_is_not_submitted() -> None:
    scenario = run_broker_scenario("broker_rejected_insufficient_cash")

    assert scenario.status == "rejected"
    assert scenario.submitted is False
    assert scenario.risk.allowed is False
    assert scenario.risk.reason == "insufficient_cash"
    assert scenario.broker_result is None
    assert scenario.portfolio.positions == ()


def test_broker_unfilled_limit_order_does_not_mutate_portfolio() -> None:
    scenario = run_broker_scenario("broker_unfilled_limit_order")

    assert scenario.status == "open"
    assert scenario.submitted is True
    assert scenario.broker_result.accepted is True
    assert scenario.broker_result.filled is False
    assert scenario.broker_result.execution.fill is None
    assert scenario.portfolio.positions == ()


def test_broker_scenarios_are_not_in_default_cli_scenarios() -> None:
    for scenario_name in BROKER_SCENARIO_NAMES:
        assert scenario_name not in SCENARIO_NAMES


def test_unknown_broker_scenario_is_rejected_clearly() -> None:
    with pytest.raises(ValidationError):
        run_broker_scenario("unknown")
