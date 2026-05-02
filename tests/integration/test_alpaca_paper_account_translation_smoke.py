import os
from decimal import Decimal
from time import perf_counter

import pytest

from algotrader.config import AlpacaPaperConfig
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.portfolio.state import Account


@pytest.mark.paper_integration
def test_alpaca_paper_account_translation_smoke() -> None:
    config = AlpacaPaperConfig.from_env(os.environ)
    client = AlpacaSdkClient(config)
    adapter = AlpacaClientAdapter(client)

    started_at = perf_counter()
    account = adapter.get_account()
    elapsed = perf_counter() - started_at

    assert elapsed < 10, "account translation exceeded the soft timeout"
    assert isinstance(account, Account)
    assert isinstance(account.cash, Decimal)
    assert account.cash >= Decimal("0")
    assert str(account.currency).strip()
