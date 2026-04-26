import pytest

from algotrader.errors import ValidationError
from algotrader.orchestration.scenarios import SCENARIO_NAMES, run_scenario


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
