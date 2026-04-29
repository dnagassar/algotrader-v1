"""Fake-only Alpaca client adapter wiring.

This adapter connects an injected Alpaca-like client boundary to the pure
translation helpers. It intentionally does not import alpaca-py, read
credentials, instantiate clients, or perform network calls.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from algotrader.core.types import ProposedOrder, Quote
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position
from algotrader.risk.state import RiskVerdict

from .alpaca_client import AlpacaOrderRequest
from .alpaca_mapper import (
    map_translated_account_to_account,
    map_translated_order_result_to_broker_result,
    map_translated_position_to_position,
)
from .alpaca_translator import (
    translate_alpaca_account,
    translate_alpaca_order_result,
    translate_alpaca_position,
)


class AlpacaAdapterError(RuntimeError):
    """Raised when the injected Alpaca-like client cannot be used."""


class AlpacaClientAdapter:
    """Thin adapter around an injected fake Alpaca-like client."""

    def __init__(
        self,
        client: Any,
        *,
        require_risk_approval: bool = True,
        order_id_prefix: str = "alpaca-paper-order",
    ) -> None:
        if client is None:
            raise AlpacaAdapterError("An injected Alpaca-like client is required.")

        self._client = client
        self._require_risk_approval = require_risk_approval
        self._order_id_prefix = order_id_prefix
        self._next_order_number = 1
        self._seen_order_ids: set[str] = set()

    def get_account(self) -> Account:
        response = self._call_client("get_account")
        translated = translate_alpaca_account(response)
        return map_translated_account_to_account(translated)

    def list_positions(self) -> tuple[Position, ...]:
        method_name = self._positions_method_name()
        responses = self._call_client(method_name)

        if responses is None:
            return ()

        if not isinstance(responses, Iterable):
            raise AlpacaAdapterError(
                "Injected Alpaca-like client returned non-iterable positions."
            )

        return tuple(
            map_translated_position_to_position(translate_alpaca_position(response))
            for response in responses
        )

    def submit_order(
        self,
        order: ProposedOrder,
        quote: Quote,
        risk_verdict: RiskVerdict | None = None,
        order_id: str | None = None,
    ) -> BrokerOrderResult:
        if self._require_risk_approval and risk_verdict is None:
            return BrokerOrderResult(
                accepted=False,
                reason="risk_approval_required",
            )

        if risk_verdict is not None and not risk_verdict.allowed:
            return BrokerOrderResult(
                accepted=False,
                reason=risk_verdict.reason or "risk_rejected",
            )

        request = self._order_request(order, order_id)
        if request.client_order_id in self._seen_order_ids:
            return BrokerOrderResult(
                accepted=False,
                reason="duplicate_order_id",
            )

        self._seen_order_ids.add(request.client_order_id)
        response = self._call_client("submit_order", request)
        translated = translate_alpaca_order_result(response)
        return map_translated_order_result_to_broker_result(translated)

    def _order_request(
        self,
        order: ProposedOrder,
        order_id: str | None = None,
    ) -> AlpacaOrderRequest:
        return AlpacaOrderRequest(
            client_order_id=order_id or self._next_order_id(),
            symbol=order.symbol,
            side=order.side.value,
            qty=order.quantity,
            order_type=order.order_type.value,
            limit_price=order.limit_price,
        )

    def _next_order_id(self) -> str:
        order_id = f"{self._order_id_prefix}-{self._next_order_number}"
        self._next_order_number += 1
        return order_id

    def _positions_method_name(self) -> str:
        if hasattr(self._client, "get_positions"):
            return "get_positions"

        if hasattr(self._client, "get_all_positions"):
            return "get_all_positions"

        raise AlpacaAdapterError(
            "Injected Alpaca-like client must define get_positions() "
            "or get_all_positions()."
        )

    def _call_client(self, method_name: str, *args: Any) -> Any:
        method = getattr(self._client, method_name, None)
        if method is None or not callable(method):
            raise AlpacaAdapterError(
                f"Injected Alpaca-like client is missing {method_name}()."
            )

        try:
            return method(*args)
        except Exception as exc:
            raise AlpacaAdapterError(
                f"Injected Alpaca-like client call failed: {method_name}()."
            ) from exc


__all__ = [
    "AlpacaAdapterError",
    "AlpacaClientAdapter",
]
