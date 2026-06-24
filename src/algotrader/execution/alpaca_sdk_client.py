"""File-scoped Alpaca SDK wrapper for future paper integration.

This is the only production module allowed to import alpaca-py. Construction
requires an explicitly valid paper profile and does not perform network calls.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import re
from typing import Any, cast

from algotrader.config import AlpacaPaperConfig, require_paper_profile
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaClient,
    AlpacaOrderResponse,
    AlpacaOrderRequest,
    AlpacaOrderSubmissionResponse,
    AlpacaRecentOrderQuery,
    AlpacaPositionResponse,
)


SdkClientFactory = Callable[[AlpacaPaperConfig], Any]


class AlpacaSdkClientError(RuntimeError):
    """Raised with sanitized SDK submit-boundary diagnostics."""

    def __init__(self, stage: str, request: AlpacaOrderRequest, cause: Exception):
        self.error_stage = stage
        self.cause_type = cause.__class__.__name__
        self.diagnostics = _submit_error_diagnostics(stage, request, cause)
        request_shape = self.diagnostics["request_shape"]
        super().__init__(
            "Alpaca SDK "
            f"{stage}: asset_class={request_shape['asset_class']} "
            f"symbol={request_shape['symbol']} side={request_shape['side']} "
            f"order_type={request_shape['order_type']} "
            f"time_in_force={request_shape['time_in_force']} "
            f"sizing_mode={request_shape['sizing_mode']} "
            f"cause_type={self.cause_type}"
            f"{_diagnostic_message_suffix(self.diagnostics)}."
        )


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

    @property
    def raw_trading_client(self) -> Any:
        """Return the injected SDK trading client for a scoped OMS boundary."""

        return self._sdk_client

    def get_account(self) -> AlpacaAccountResponse:
        return cast(AlpacaAccountResponse, self._sdk_client.get_account())

    def get_positions(self) -> Sequence[AlpacaPositionResponse]:
        if hasattr(self._sdk_client, "get_all_positions"):
            return cast(
                Sequence[AlpacaPositionResponse],
                self._sdk_client.get_all_positions(),
            )

        return cast(Sequence[AlpacaPositionResponse], self._sdk_client.get_positions())

    def get_orders(
        self,
        query: AlpacaRecentOrderQuery | None = None,
    ) -> Sequence[AlpacaOrderResponse]:
        resolved_query = query or AlpacaRecentOrderQuery()
        if self._uses_alpaca_sdk_request_shape:
            sdk_query = _to_sdk_get_orders_request(resolved_query)
            return cast(Sequence[AlpacaOrderResponse], self._sdk_client.get_orders(sdk_query))

        return cast(
            Sequence[AlpacaOrderResponse],
            self._sdk_client.get_orders(resolved_query),
        )

    def submit_order(
        self, request: AlpacaOrderRequest
    ) -> AlpacaOrderSubmissionResponse:
        try:
            sdk_request = (
                _to_sdk_order_request(request)
                if self._uses_alpaca_sdk_request_shape
                else request
            )
        except Exception as exc:
            raise AlpacaSdkClientError(
                "request_construction_failed",
                request,
                exc,
            ) from exc

        try:
            return cast(
                AlpacaOrderSubmissionResponse,
                self._sdk_client.submit_order(sdk_request),
            )
        except Exception as exc:
            raise AlpacaSdkClientError(
                "submit_call_failed_before_response",
                request,
                exc,
            ) from exc


def _create_trading_client(config: AlpacaPaperConfig) -> Any:
    from alpaca.trading.client import TradingClient

    return TradingClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        paper=True,
        url_override=config.alpaca_paper_base_url,
    )


def _to_sdk_order_request(request: AlpacaOrderRequest) -> Any:
    from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
    from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

    time_in_force_by_value = {
        "day": TimeInForce.DAY,
        "gtc": TimeInForce.GTC,
        "ioc": TimeInForce.IOC,
    }
    kwargs: dict[str, Any] = {
        "client_order_id": request.client_order_id,
        "side": OrderSide(request.side),
        "symbol": request.symbol,
        "time_in_force": time_in_force_by_value[request.time_in_force],
        "type": OrderType(request.order_type),
    }
    if request.notional is not None:
        kwargs["notional"] = request.notional
    else:
        kwargs["qty"] = request.qty

    if request.order_type == "limit":
        kwargs["limit_price"] = request.limit_price
        return LimitOrderRequest(**kwargs)

    return MarketOrderRequest(**kwargs)


def _to_sdk_get_orders_request(query: AlpacaRecentOrderQuery) -> Any:
    from alpaca.common.enums import Sort
    from alpaca.trading.enums import OrderSide, QueryOrderStatus
    from alpaca.trading.requests import GetOrdersRequest

    kwargs: dict[str, Any] = {}
    if query.status_filter:
        kwargs["status"] = QueryOrderStatus(query.status_filter)
    if query.limit is not None:
        kwargs["limit"] = query.limit
    if query.after is not None:
        kwargs["after"] = query.after
    if query.until is not None:
        kwargs["until"] = query.until
    if query.direction:
        kwargs["direction"] = Sort(query.direction)
    if query.nested is not None:
        kwargs["nested"] = query.nested
    if query.side_filter:
        kwargs["side"] = OrderSide(query.side_filter)
    if query.symbol_filter:
        kwargs["symbols"] = [query.symbol_filter]

    return GetOrdersRequest(**kwargs)


_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|secret(?:[_-]?key)?|token)\b"
    r"\s*[:=]\s*[^,\s;)]+"
)
_URL_PATTERN = re.compile(r"https?://[^\s)>\]\"']+")
_SAFE_MESSAGE_LIMIT = 240


def _submit_error_diagnostics(
    stage: str,
    request: AlpacaOrderRequest,
    cause: Exception,
) -> dict[str, Any]:
    return {
        "submit_stage": stage,
        "exception_class": cause.__class__.__name__,
        "status_code": _safe_exception_attr(cause, "status_code"),
        "alpaca_error_code": _safe_text(_safe_exception_attr(cause, "code")),
        "sanitized_message": _sanitized_exception_message(cause),
        "request_shape": _request_shape_summary(request),
    }


def _request_shape_summary(request: AlpacaOrderRequest) -> dict[str, str]:
    sizing_mode = "notional" if request.notional is not None else "qty"
    return {
        "asset_class": request.asset_class,
        "symbol": request.symbol,
        "side": request.side,
        "order_type": request.order_type,
        "time_in_force": request.time_in_force,
        "sizing_mode": sizing_mode,
    }


def _diagnostic_message_suffix(diagnostics: dict[str, Any]) -> str:
    parts = []
    if diagnostics.get("status_code") is not None:
        parts.append(f"api_status_code={diagnostics['status_code']}")
    if diagnostics.get("alpaca_error_code"):
        parts.append(f"alpaca_error_code={diagnostics['alpaca_error_code']}")
    if diagnostics.get("sanitized_message"):
        parts.append(f"api_error_message={diagnostics['sanitized_message']}")

    if not parts:
        return ""

    return " " + " ".join(parts)


def _safe_exception_attr(exc: Exception, name: str) -> Any:
    try:
        return getattr(exc, name)
    except Exception:
        return None


def _sanitized_exception_message(exc: Exception) -> str:
    message = _safe_exception_attr(exc, "message")
    if message is None and exc.__class__.__name__ == "APIError":
        message = str(exc)
    if message is None:
        return ""

    return _sanitize_exception_text(str(message))


def _sanitize_exception_text(message: str) -> str:
    sanitized = _URL_PATTERN.sub("<redacted_url>", message)
    sanitized = _BEARER_TOKEN_PATTERN.sub("Bearer <redacted>", sanitized)
    sanitized = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=<redacted>",
        sanitized,
    )
    sanitized = " ".join(sanitized.split())
    if len(sanitized) > _SAFE_MESSAGE_LIMIT:
        return f"{sanitized[:_SAFE_MESSAGE_LIMIT].rstrip()}..."

    return sanitized


def _safe_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value)


__all__ = ["AlpacaSdkClient", "AlpacaSdkClientError"]
