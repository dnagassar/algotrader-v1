"""File-scoped Alpaca SDK wrapper for future paper integration.

This is the only production module allowed to import alpaca-py. Construction
requires an explicitly valid paper profile and does not perform network calls.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast

from algotrader.config import AlpacaPaperConfig, require_paper_profile
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaClient,
    AlpacaOrderResponse,
    AlpacaOrderRequest,
    AlpacaOrderSubmissionResponse,
    AlpacaPositionResponse,
)


SdkClientFactory = Callable[[AlpacaPaperConfig], Any]


class AlpacaSdkClient(AlpacaClient):
    """Thin SDK boundary over alpaca-py's trading client.

    This wrapper returns native alpaca-py SDK response objects and does not
    translate SDK response shapes. Translation happens downstream in
    ``algotrader.execution.alpaca_translator``; mapping to internal domain
    models happens downstream in ``algotrader.execution.alpaca_mapper``.
    Any ``cast(...)`` usage here is typing-only and must not be interpreted as
    runtime conversion.
    """

    def __init__(
        self,
        config: AlpacaPaperConfig,
        *,
        sdk_client: Any | None = None,
        sdk_client_factory: SdkClientFactory | None = None,
    ) -> None:
        require_paper_profile(config)

        if sdk_client is not None and sdk_client_factory is not None:
            raise ValueError(
                "Provide either sdk_client or sdk_client_factory, not both."
            )

        self._uses_alpaca_sdk_request_shape = sdk_client is None

        if sdk_client is not None:
            self._sdk_client = sdk_client
            return

        factory = sdk_client_factory or _create_trading_client
        self._sdk_client = factory(config)

    def get_account(self) -> AlpacaAccountResponse:
        return cast(AlpacaAccountResponse, self._sdk_client.get_account())

    def get_positions(self) -> Sequence[AlpacaPositionResponse]:
        if hasattr(self._sdk_client, "get_all_positions"):
            return cast(
                Sequence[AlpacaPositionResponse],
                self._sdk_client.get_all_positions(),
            )

        return cast(Sequence[AlpacaPositionResponse], self._sdk_client.get_positions())

    def get_orders(self) -> Sequence[AlpacaOrderResponse]:
        return cast(Sequence[AlpacaOrderResponse], self._sdk_client.get_orders())

    def submit_order(
        self, request: AlpacaOrderRequest
    ) -> AlpacaOrderSubmissionResponse:
        sdk_request = (
            _to_sdk_order_request(request)
            if self._uses_alpaca_sdk_request_shape
            else request
        )
        return cast(
            AlpacaOrderSubmissionResponse,
            self._sdk_client.submit_order(sdk_request),
        )


def _create_trading_client(config: AlpacaPaperConfig) -> Any:
    from alpaca.trading.client import TradingClient

    return TradingClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        paper=True,
        url_override=config.alpaca_paper_base_url,
    )


def _to_sdk_order_request(request: AlpacaOrderRequest) -> Any:
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    time_in_force_by_value = {
        "day": TimeInForce.DAY,
        "gtc": TimeInForce.GTC,
        "ioc": TimeInForce.IOC,
    }
    kwargs: dict[str, Any] = {
        "client_order_id": request.client_order_id,
        "side": OrderSide.BUY,
        "symbol": request.symbol,
        "time_in_force": time_in_force_by_value[request.time_in_force],
    }
    if request.notional is not None:
        kwargs["notional"] = request.notional
    else:
        kwargs["qty"] = request.qty

    return MarketOrderRequest(**kwargs)


__all__ = ["AlpacaSdkClient"]
