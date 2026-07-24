from __future__ import annotations

import ast
from pathlib import Path
import pytest

from algotrader.execution.crypto_history_refresh_adapter import (
    CryptoHistoryRefreshConfig,
    CryptoHistoryRefreshError,
    run_crypto_history_refresh,
)
from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    EXPECTED_PAPER_ENDPOINT,
    PreflightCheckError,
    validate_preflight_gates,
)
from algotrader.execution.live_capital_interlock import LiveCapitalGateError

MODULE_PATH = Path("src/algotrader/execution/crypto_history_refresh_adapter.py")

FORBIDDEN_MUTATION_CALLS = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "create_order",
    "liquidate",
    "replace_order",
    "submit_order",
    "submit_order_request",
}


def _paper_env(**extra: str) -> dict[str, str]:
    env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "paper-key",
        "ALPACA_SECRET_KEY": "paper-secret",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
        "APCA_API_BASE_URL": "https://paper-api.alpaca.markets",
    }
    env.update(extra)
    return env


def test_history_refresh_market_data_fetch_refuses_under_live_signal() -> None:
    env = _paper_env(ALLOW_LIVE_TRADING="true")
    config = CryptoHistoryRefreshConfig(
        mode="market_data_fetch",
        symbols=("BTCUSD",),
        market_data_fetch_authorized=True,
        allow_network=True,
    )
    with pytest.raises(LiveCapitalGateError):
        run_crypto_history_refresh(config, env=env)


def test_history_refresh_market_data_fetch_refuses_under_live_profile() -> None:
    env = _paper_env(APP_PROFILE="live")
    config = CryptoHistoryRefreshConfig(
        mode="market_data_fetch",
        symbols=("BTCUSD",),
        market_data_fetch_authorized=True,
        allow_network=True,
    )
    packet = run_crypto_history_refresh(config, env=env)
    assert packet["classification"] == "rejected_live_endpoint_risk"
    assert packet["market_data_fetch_occurred"] is False


def test_observation_adapter_preflight_refuses_under_live_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "true")
    with pytest.raises(PreflightCheckError, match="preflight_failed_live_signal_detected"):
        validate_preflight_gates(
            app_profile="paper",
            endpoint=EXPECTED_PAPER_ENDPOINT,
            key_id="key",
            secret_key="secret",
            expected_account_id="PA123",
            paper_broker_read_authorized=True,
            allow_network=True,
        )


def test_stage2_modules_have_no_order_mutation_calls() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in FORBIDDEN_MUTATION_CALLS, func.id
            elif isinstance(func, ast.Attribute):
                assert func.attr not in FORBIDDEN_MUTATION_CALLS, func.attr
