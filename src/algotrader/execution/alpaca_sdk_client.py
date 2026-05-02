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
    AlpacaOrderRequest,
    AlpacaOrderSubmissionResponse,
    AlpacaPositionResponse,
)


SdkClientFactory = Callable[[AlpacaPaperConfig], Any]


class AlpacaSdkClient(AlpacaClient):
    """Minimal adapter over alpaca-py's trading client.

    This wrapper does not translate SDK response shapes. Real SDK responses pass
    through to the existing adapter/translator/mapper boundary, where shape
    normalization belongs to ``alpaca_translator`` and ``alpaca_mapper``. The
    casts below are local protocol typing hints, not response conversion.
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

    def submit_order(
        self, request: AlpacaOrderRequest
    ) -> AlpacaOrderSubmissionResponse:
        return cast(
            AlpacaOrderSubmissionResponse,
            self._sdk_client.submit_order(request),
        )


def _create_trading_client(config: AlpacaPaperConfig) -> Any:
    from alpaca.trading.client import TradingClient

    return TradingClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        paper=True,
        url_override=config.alpaca_paper_base_url,
    )


__all__ = ["AlpacaSdkClient"]
