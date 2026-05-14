"""Shared pytest fixtures for the algotrader test suite."""

from __future__ import annotations

from collections.abc import Mapping
import os
import socket

import pytest

from algotrader.config import TradingConfig, load_config


PAPER_INTEGRATION_FLAG = "RUN_ALPACA_PAPER_INTEGRATION_TESTS"
NETWORK_TESTS_FLAG = "ALGO_TRADER_ALLOW_NETWORK_TESTS"
REQUIRED_PAPER_INTEGRATION_ENV = (
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "ALPACA_PAPER_BASE_URL",
)
NETWORK_BLOCK_MESSAGE = (
    "Normal pytest for algo_trader is offline and credential-free; "
    "network access is blocked. Use --allow-network or "
    "ALGO_TRADER_ALLOW_NETWORK_TESTS=1 only for explicitly gated integration tests."
)
_ORIGINAL_SOCKET = socket.socket
_NETWORK_GUARD_INSTALLED = False


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--allow-network",
        action="store_true",
        default=False,
        help=(
            "Allow socket/network access for explicitly gated integration tests. "
            "Normal pytest remains offline and credential-free by default."
        ),
    )


def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers",
        "paper_integration: opt-in Alpaca paper integration tests skipped by default",
    )
    config.addinivalue_line(
        "markers",
        "network_integration: opt-in network tests blocked by default",
    )
    if not _network_tests_allowed(config, os.environ):
        _install_default_network_guard()


def pytest_collection_modifyitems(config, items) -> None:
    if _paper_integration_enabled(os.environ):
        return

    skip_paper = pytest.mark.skip(
        reason=(
            "paper_integration tests require RUN_ALPACA_PAPER_INTEGRATION_TESTS=1, "
            "APP_PROFILE=paper, and non-empty ALPACA_* paper settings"
        )
    )
    for item in items:
        if "paper_integration" in item.keywords:
            item.add_marker(skip_paper)


def _paper_integration_enabled(env: Mapping[str, str]) -> bool:
    return (
        env.get(PAPER_INTEGRATION_FLAG) == "1"
        and env.get("APP_PROFILE") == "paper"
        and all(env.get(name, "").strip() for name in REQUIRED_PAPER_INTEGRATION_ENV)
    )


def _network_tests_allowed(config: object, env: Mapping[str, str]) -> bool:
    return _allow_network_option_enabled(config) or env.get(NETWORK_TESTS_FLAG) == "1"


def _allow_network_option_enabled(config: object) -> bool:
    getoption = getattr(config, "getoption", None)
    if getoption is None:
        return False

    return bool(getoption("allow_network", default=False))


def _install_default_network_guard() -> None:
    global _NETWORK_GUARD_INSTALLED
    if _NETWORK_GUARD_INSTALLED:
        return

    socket.socket = _BlockedSocket
    socket.create_connection = _blocked_network_access
    _NETWORK_GUARD_INSTALLED = True


class _BlockedSocket(_ORIGINAL_SOCKET):
    def __new__(cls, *args: object, **kwargs: object) -> "_BlockedSocket":
        raise RuntimeError(NETWORK_BLOCK_MESSAGE)


def _blocked_network_access(*args: object, **kwargs: object) -> None:
    raise RuntimeError(NETWORK_BLOCK_MESSAGE)


@pytest.fixture
def dev_config(tmp_path) -> TradingConfig:
    return load_config(
        "dev",
        env={
            "ALGOTRADER_DATA_DIR": str(tmp_path),
            "ALGOTRADER_STARTING_CASH": "100000",
        },
    )
