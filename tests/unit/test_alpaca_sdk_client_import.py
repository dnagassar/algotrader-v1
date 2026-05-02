import importlib
import sys


def test_alpaca_sdk_client_import_does_not_load_alpaca() -> None:
    sys.modules.pop("algotrader.execution.alpaca_sdk_client", None)
    sys.modules.pop("alpaca", None)

    importlib.import_module("algotrader.execution.alpaca_sdk_client")

    assert "alpaca" not in sys.modules
