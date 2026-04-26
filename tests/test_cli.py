import pytest

from algotrader.cli import main
from algotrader.orchestration.scenarios import SCENARIO_NAMES


def test_cli_config_command_returns_zero() -> None:
    assert main(["--profile", "dev", "config"]) == 0


def test_cli_demo_core_returns_zero_and_prints_summary(capsys) -> None:
    assert main(["demo-core"]) == 0

    output = capsys.readouterr().out.lower()
    assert "scenario" in output
    assert "signal" in output
    assert "risk" in output
    assert "execution" in output
    assert "fill" in output
    assert "valuation" in output
    assert "final_outcome" in output


def test_cli_demo_core_scenario_selection(capsys) -> None:
    assert main(["demo-core", "--scenario", "no_signal"]) == 0

    output = capsys.readouterr().out.lower()
    assert "scenario: no_signal" in output
    assert "signal: none" in output
    assert "execution: not_run" in output


def test_cli_demo_core_lists_scenarios(capsys) -> None:
    assert main(["demo-core", "--list-scenarios"]) == 0

    output = capsys.readouterr().out
    for scenario_name in SCENARIO_NAMES:
        assert scenario_name in output


@pytest.mark.parametrize("scenario_name", SCENARIO_NAMES)
def test_cli_demo_core_runs_each_scenario(scenario_name: str, capsys) -> None:
    assert main(["demo-core", "--scenario", scenario_name]) == 0

    output = capsys.readouterr().out
    assert f"scenario: {scenario_name}" in output
    assert "final_outcome:" in output


def test_cli_demo_core_invalid_scenario_fails_clearly(capsys) -> None:
    assert main(["demo-core", "--scenario", "unknown"]) == 2

    error = capsys.readouterr().err.lower()
    assert "unknown scenario" in error
    assert "available scenarios" in error
