import importlib
import sys

from algotrader.config import AlpacaPaperConfig


def _clear_alpaca_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "alpaca" or module_name.startswith("alpaca."):
            sys.modules.pop(module_name, None)


def test_alpaca_sdk_client_import_does_not_load_alpaca() -> None:
    sys.modules.pop("algotrader.execution.alpaca_sdk_client", None)
    _clear_alpaca_modules()

    importlib.import_module("algotrader.execution.alpaca_sdk_client")

    assert "alpaca" not in sys.modules


def test_fake_injected_alpaca_sdk_client_construction_does_not_load_alpaca() -> None:
    sys.modules.pop("algotrader.execution.alpaca_sdk_client", None)
    _clear_alpaca_modules()

    module = importlib.import_module("algotrader.execution.alpaca_sdk_client")
    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="test-api-key",
        alpaca_secret_key="test-secret-key",
        alpaca_paper_base_url="https://paper.example.test",
    )

    module.AlpacaSdkClient(config, sdk_client=object())

    assert not any(
        module_name == "alpaca" or module_name.startswith("alpaca.")
        for module_name in sys.modules
    )
