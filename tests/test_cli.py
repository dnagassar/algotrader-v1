from algotrader.cli import main


def test_cli_config_command_returns_zero() -> None:
    assert main(["--profile", "dev", "config"]) == 0


def test_cli_demo_core_returns_zero_and_prints_summary(capsys) -> None:
    assert main(["demo-core"]) == 0

    output = capsys.readouterr().out.lower()
    assert "signal" in output
    assert "risk" in output
    assert "execution" in output
    assert "valuation" in output


def test_cli_demo_core_scenario_selection(capsys) -> None:
    assert main(["demo-core", "--scenario", "no_signal"]) == 0

    output = capsys.readouterr().out.lower()
    assert "scenario: no_signal" in output
    assert "signal: none" in output
    assert "execution: not_run" in output
