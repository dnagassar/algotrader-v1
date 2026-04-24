"""Shared pytest fixtures for the algotrader test suite."""

from __future__ import annotations

import pytest

from algotrader.config import TradingConfig, load_config


@pytest.fixture
def dev_config(tmp_path) -> TradingConfig:
    return load_config(
        "dev",
        env={
            "ALGOTRADER_DATA_DIR": str(tmp_path),
            "ALGOTRADER_STARTING_CASH": "100000",
        },
    )
