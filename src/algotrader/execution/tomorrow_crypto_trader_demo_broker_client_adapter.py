"""Impure broker adapter wrapper for tomorrow_crypto_trader_demo.

This module lives outside the replay closure and contains static references
to Alpaca paper config and Alpaca SDK client.
"""

from __future__ import annotations

from collections.abc import Sequence
import os
from typing import Any

from algotrader.config import AlpacaPaperConfig
from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient

DEFAULT_ALPACA_PAPER_ENDPOINT = "https://paper-api.alpaca.markets"


class _TomorrowBrokerReadClientAdapter:
    """Narrow read-only adapter exposing exact 4 gate read methods and 9 price aliases."""

    def __init__(self, sdk_client: AlpacaSdkClient) -> None:
        self._sdk_client = sdk_client

    def get_account(self) -> Any:
        return self._sdk_client.get_account()

    def get_positions(self) -> Sequence[Any]:
        return self._sdk_client.get_positions()

    def list_assets(self) -> Sequence[Any]:
        return self._sdk_client.list_assets()

    def get_orders(
        self,
        query: Any | None = None,
        *,
        status_filter: str | None = None,
        symbol_filter: str | None = None,
        status: str | None = None,
        symbol: str | None = None,
    ) -> Sequence[Any]:
        if query is not None:
            return self._sdk_client.get_orders(query)
        eff_status = status_filter or status
        eff_symbol = symbol_filter or symbol
        query_obj = AlpacaRecentOrderQuery(
            status_filter=eff_status,
            symbol_filter=eff_symbol,
        )
        return self._sdk_client.get_orders(query_obj)

    def get_crypto_latest_quote(self, symbol: str) -> Any:
        return self._sdk_client.get_crypto_latest_quote(symbol)

    def get_latest_crypto_quote(self, symbol: str) -> Any:
        return self._sdk_client.get_latest_crypto_quote(symbol)

    def get_latest_quote(self, symbol: str) -> Any:
        return self._sdk_client.get_crypto_latest_quote(symbol)

    def get_crypto_latest_trade(self, symbol: str) -> Any:
        return self._sdk_client.get_crypto_latest_trade(symbol)

    def get_latest_crypto_trade(self, symbol: str) -> Any:
        return self._sdk_client.get_latest_crypto_trade(symbol)

    def get_latest_trade(self, symbol: str) -> Any:
        return self._sdk_client.get_crypto_latest_trade(symbol)

    def get_crypto_latest_bar(self, symbol: str) -> Any:
        return self._sdk_client.get_crypto_latest_bar(symbol)

    def get_latest_crypto_bar(self, symbol: str) -> Any:
        return self._sdk_client.get_latest_crypto_bar(symbol)

    def get_latest_bar(self, symbol: str) -> Any:
        return self._sdk_client.get_crypto_latest_bar(symbol)


def build_alpaca_read_client() -> object:
    """Construct a real, protocol-shaped read client adapter."""
    env = os.environ
    config = AlpacaPaperConfig(
        app_profile=env.get("APP_PROFILE", ""),
        alpaca_api_key=env.get("ALPACA_API_KEY") or env.get("APCA_API_KEY_ID"),
        alpaca_secret_key=(
            env.get("ALPACA_SECRET_KEY")
            or env.get("ALPACA_API_SECRET_KEY")
            or env.get("APCA_API_SECRET_KEY")
        ),
        alpaca_paper_base_url=env.get("ALPACA_PAPER_BASE_URL", DEFAULT_ALPACA_PAPER_ENDPOINT),
    )
    sdk_client = AlpacaSdkClient(config)
    return _TomorrowBrokerReadClientAdapter(sdk_client)


def read_paper_environment_from_os() -> dict[str, object]:
    """Return profile/endpoint text and credential-presence booleans. Never return a credential value."""
    names = (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    )
    return {
        name: (
            os.environ.get(name)
            if name
            in {
                "APP_PROFILE",
                "ALPACA_BASE_URL",
                "ALPACA_PAPER_BASE_URL",
                "APCA_API_BASE_URL",
            }
            else bool(os.environ.get(name))
        )
        for name in names
    }
