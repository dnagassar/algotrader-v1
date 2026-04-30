"""Shared pytest fixtures for the algotrader test suite."""

from __future__ import annotations

from collections.abc import Mapping
import os

import pytest

from algotrader.config import TradingConfig, load_config


PAPER_INTEGRATION_FLAG = "RUN_ALPACA_PAPER_INTEGRATION_TESTS"
REQUIRED_PAPER_INTEGRATION_ENV = (
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "ALPACA_PAPER_BASE_URL",
)


def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers",
        "paper_integration: opt-in Alpaca paper integration tests skipped by default",
    )


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


@pytest.fixture
def dev_config(tmp_path) -> TradingConfig:
    return load_config(
        "dev",
        env={
            "ALGOTRADER_DATA_DIR": str(tmp_path),
            "ALGOTRADER_STARTING_CASH": "100000",
        },
    )
