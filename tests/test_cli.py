from algotrader.cli import main


def test_cli_config_command_returns_zero() -> None:
    assert main(["--profile", "dev", "config"]) == 0
