import os
from decimal import Decimal
from time import perf_counter

import pytest

from algotrader.config import AlpacaPaperConfig
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.portfolio.state import Position


@pytest.mark.paper_integration
def test_alpaca_paper_positions_translation_smoke() -> None:
    config = AlpacaPaperConfig.from_env(os.environ)
    client = AlpacaSdkClient(config)
    adapter = AlpacaClientAdapter(client)

    started_at = perf_counter()
    positions = adapter.list_positions()
    elapsed = perf_counter() - started_at

    assert elapsed < 10, "positions translation exceeded the soft timeout"
    assert isinstance(positions, tuple)

    for position in positions:
        assert isinstance(position, Position)
        assert str(position.symbol).strip()
        assert isinstance(position.quantity, Decimal)
        assert position.quantity >= Decimal("0")
