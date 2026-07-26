"""Unit tests for tomorrow_crypto_trader_demo_cli and broker adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter import (
    _TomorrowBrokerReadClientAdapter,
    build_alpaca_read_client,
    read_paper_environment_from_os,
)
from algotrader.execution.tomorrow_crypto_trader_demo_cli import main


def test_broker_adapter_exposes_thirteen_read_methods_and_no_mutations() -> None:
    fake_sdk = MagicMock()
    fake_sdk.get_account.return_value = {"account": "ok"}
    fake_sdk.get_positions.return_value = [{"symbol": "BTCUSD"}]
    fake_sdk.list_assets.return_value = [{"symbol": "BTCUSD"}]
    fake_sdk.get_orders.return_value = []
    fake_sdk.get_crypto_latest_quote.return_value = {"price": "100"}
    fake_sdk.get_latest_crypto_quote.return_value = {"price": "100"}
    fake_sdk.get_crypto_latest_trade.return_value = {"price": "100"}
    fake_sdk.get_latest_crypto_trade.return_value = {"price": "100"}
    fake_sdk.get_crypto_latest_bar.return_value = {"close": "100"}
    fake_sdk.get_latest_crypto_bar.return_value = {"close": "100"}

    adapter = _TomorrowBrokerReadClientAdapter(fake_sdk)

    # Core 4 methods
    assert adapter.get_account() == {"account": "ok"}
    assert adapter.get_positions() == [{"symbol": "BTCUSD"}]
    assert adapter.list_assets() == [{"symbol": "BTCUSD"}]
    assert adapter.get_orders(status_filter="open", symbol_filter="BTCUSD") == []

    # 9 Price alias methods
    assert adapter.get_crypto_latest_quote("BTCUSD") == {"price": "100"}
    assert adapter.get_latest_crypto_quote("BTCUSD") == {"price": "100"}
    assert adapter.get_latest_quote("BTCUSD") == {"price": "100"}

    assert adapter.get_crypto_latest_trade("BTCUSD") == {"price": "100"}
    assert adapter.get_latest_crypto_trade("BTCUSD") == {"price": "100"}
    assert adapter.get_latest_trade("BTCUSD") == {"price": "100"}

    assert adapter.get_crypto_latest_bar("BTCUSD") == {"close": "100"}
    assert adapter.get_latest_crypto_bar("BTCUSD") == {"close": "100"}
    assert adapter.get_latest_bar("BTCUSD") == {"close": "100"}

    fake_sdk.get_account.assert_called_once_with()
    fake_sdk.get_positions.assert_called_once_with()
    fake_sdk.list_assets.assert_called_once_with()
    order_query = fake_sdk.get_orders.call_args.args[0]
    assert order_query.status_filter == "open"
    assert order_query.symbol_filter == "BTCUSD"
    fake_sdk.get_crypto_latest_quote.assert_has_calls(
        [call("BTCUSD"), call("BTCUSD")]
    )
    fake_sdk.get_latest_crypto_quote.assert_called_once_with("BTCUSD")
    fake_sdk.get_crypto_latest_trade.assert_has_calls(
        [call("BTCUSD"), call("BTCUSD")]
    )
    fake_sdk.get_latest_crypto_trade.assert_called_once_with("BTCUSD")
    fake_sdk.get_crypto_latest_bar.assert_has_calls(
        [call("BTCUSD"), call("BTCUSD")]
    )
    fake_sdk.get_latest_crypto_bar.assert_called_once_with("BTCUSD")

    # Mutation methods must not exist on adapter
    for mutation in (
        "submit_order",
        "cancel_order",
        "cancel_orders",
        "replace_order",
        "close_position",
        "close_all_positions",
        "liquidate",
        "liquidate_position",
    ):
        assert not hasattr(adapter, mutation), f"Mutation method {mutation} should not be exposed"


def test_read_paper_environment_from_os_does_not_expose_credentials() -> None:
    with patch.dict(
        "os.environ",
        {
            "APP_PROFILE": "paper",
            "ALPACA_API_KEY": "SECRET_KEY_VALUE_123",
            "ALPACA_SECRET_KEY": "SUPER_SECRET_VALUE_456",
            "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
        },
        clear=True,
    ):
        env = read_paper_environment_from_os()
        assert env["APP_PROFILE"] == "paper"
        assert env["ALPACA_PAPER_BASE_URL"] == "https://paper-api.alpaca.markets"
        assert env["ALPACA_API_KEY"] is True
        assert env["ALPACA_SECRET_KEY"] is True
        assert "SECRET_KEY_VALUE_123" not in env.values()
        assert "SUPER_SECRET_VALUE_456" not in env.values()


def test_tomorrow_crypto_trader_demo_cli_validate_only(tmp_path: Path) -> None:
    output_root = tmp_path / "demo_output"
    # First run demo to write output
    ret = main(["--output-root", str(output_root)])
    assert ret == 0

    # Validate output
    ret_val = main(["--output-root", str(output_root), "--validate-only"])
    assert ret_val == 0


def test_cli_two_flag_factory_wiring(tmp_path: Path) -> None:
    output_root = tmp_path / "two_flag_output"

    for omitted_combination in (
        (),
        ("--broker-observed-readiness",),
        ("--allow-alpaca-paper-read",),
    ):
        with (
            patch(
                "algotrader.execution.tomorrow_crypto_trader_demo_cli."
                "run_tomorrow_crypto_trader_demo"
            ) as mock_run,
            patch(
                "algotrader.execution.tomorrow_crypto_trader_demo_cli."
                "build_alpaca_read_client"
            ) as mock_builder,
        ):
            mock_run.return_value = {"decision": "blocked", "safety": {}}
            exit_code = main(
                ["--output-root", str(output_root), *omitted_combination]
            )
            assert exit_code == 0
            mock_run.assert_called_once()
            assert (
                mock_run.call_args.kwargs.get(
                    "broker_observed_client_factory"
                )
                is None
            )
            mock_builder.assert_not_called()

    # Both flags provided: factory wired
    with (
        patch(
            "algotrader.execution.tomorrow_crypto_trader_demo_cli."
            "run_tomorrow_crypto_trader_demo"
        ) as mock_run,
        patch(
            "algotrader.execution.tomorrow_crypto_trader_demo_cli."
            "build_alpaca_read_client"
        ) as mock_builder,
    ):
        mock_run.return_value = {
            "decision": "offline_simulated_trade_only",
            "safety": {},
        }
        exit_code = main(
            [
                "--output-root",
                str(output_root),
                "--broker-observed-readiness",
                "--allow-alpaca-paper-read",
            ]
        )
        assert exit_code == 0
        mock_run.assert_called_once()
        assert (
            mock_run.call_args.kwargs.get("broker_observed_client_factory")
            is mock_builder
        )
        mock_builder.assert_not_called()
