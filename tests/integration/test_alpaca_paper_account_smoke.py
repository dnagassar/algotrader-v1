import os
from decimal import Decimal, InvalidOperation
from time import perf_counter

import pytest

from algotrader.config import AlpacaPaperConfig
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient


@pytest.mark.paper_integration
def test_alpaca_paper_get_account_smoke() -> None:
    config = AlpacaPaperConfig.from_env(os.environ)
    client = AlpacaSdkClient(config)

    started_at = perf_counter()
    account = client.get_account()
    elapsed = perf_counter() - started_at

    assert elapsed < 10, "get_account call exceeded the soft timeout"

    account_id = getattr(account, "account_id", None)
    if not str(account_id or "").strip():
        account_id = getattr(account, "id", None)
    assert str(account_id or "").strip(), "account id field is required"

    status = getattr(account, "status", None)
    assert str(status or "").strip(), "account status field is required"

    cash = getattr(account, "cash", None)
    assert cash is not None, "account cash field is required"
    try:
        cash_value = Decimal(str(cash))
    except (InvalidOperation, ValueError):
        pytest.fail("account cash field must be decimal-compatible")

    assert cash_value >= Decimal("0"), "account cash field must be non-negative"
