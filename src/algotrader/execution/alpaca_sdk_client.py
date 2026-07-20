"""File-scoped Alpaca SDK wrapper for future paper integration.

This is the only production module allowed to import alpaca-py. Construction
requires an explicitly valid paper profile and does not perform network calls.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
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
CryptoDataClientFactory = Callable[[AlpacaPaperConfig], Any]


@dataclass(frozen=True, slots=True)
class CryptoMarketDataSymbolNormalization:
    input_symbol: str
    compact_symbol: str
    provider_symbol: str
    status: str
    blocker_code: str = ""


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


class AlpacaSdkClientReadError(RuntimeError):
    """Raised with sanitized SDK read-boundary diagnostics."""

    def __init__(self, stage: str, cause: Exception):
        self.error_stage = stage
        self.cause_type = cause.__class__.__name__
        self.sanitized_message = _sanitized_exception_message(cause)
        super().__init__(
            f"Alpaca SDK {stage}: cause_type={self.cause_type}"
            f"{_read_diagnostic_message_suffix(self.sanitized_message)}."
        )


class AlpacaCryptoSymbolNormalizationError(ValueError):
    """Raised when a crypto market-data symbol cannot be safely normalized."""

    def __init__(self, normalization: CryptoMarketDataSymbolNormalization):
        self.input_symbol = normalization.input_symbol
        self.status = normalization.status
        self.blocker_code = normalization.blocker_code
        super().__init__(
            "Alpaca crypto market-data symbol normalization failed: "
            f"input_symbol={self.input_symbol!r} "
            f"status={self.status} blocker_code={self.blocker_code}"
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
        sdk_crypto_data_client: Any | None = None,
        sdk_crypto_data_client_factory: CryptoDataClientFactory | None = None,
    ) -> None:
        require_paper_profile(config)

        if sdk_client is not None and sdk_client_factory is not None:
            raise ValueError(
                "Provide either sdk_client or sdk_client_factory, not both."
            )
        if (
            sdk_crypto_data_client is not None
            and sdk_crypto_data_client_factory is not None
        ):
            raise ValueError(
                "Provide either sdk_crypto_data_client or "
                "sdk_crypto_data_client_factory, not both."
            )

        self._config = config
        self._uses_alpaca_sdk_request_shape = sdk_client is None
        self._sdk_crypto_data_client = sdk_crypto_data_client
        self._sdk_crypto_data_client_factory = sdk_crypto_data_client_factory

        if sdk_client is not None:
            self._sdk_client = sdk_client
            return

        factory = sdk_client_factory or _create_trading_client
        self._sdk_client = factory(config)

    @property
    def raw_trading_client(self) -> Any:
        """Return the injected SDK trading client for a scoped OMS boundary."""

        return self._sdk_client

    @property
    def raw_crypto_data_client(self) -> Any:
        """Return or lazily construct the injected SDK crypto data client."""

        return self._crypto_data_client()

    def get_account(self) -> AlpacaAccountResponse:
        return cast(AlpacaAccountResponse, self._sdk_client.get_account())

    def list_assets(self) -> Sequence[Any]:
        if hasattr(self._sdk_client, "get_all_assets"):
            return cast(Sequence[Any], self._sdk_client.get_all_assets())

        return cast(Sequence[Any], self._sdk_client.get_assets())

    def get_asset(self, symbol: str) -> Any:
        return self._sdk_client.get_asset(symbol)

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

    def get_order_by_id(self, broker_order_id: str) -> AlpacaOrderResponse:
        normalized_order_id = str(broker_order_id).strip()
        if not normalized_order_id:
            raise ValueError("broker_order_id is required.")
        try:
            return cast(
                AlpacaOrderResponse,
                self._sdk_client.get_order_by_id(normalized_order_id),
            )
        except Exception as exc:
            raise AlpacaSdkClientReadError(
                "get_order_by_id_failed",
                exc,
            ) from exc

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

    def get_crypto_latest_quote(self, symbol: str) -> Any:
        request = _to_sdk_crypto_latest_quote_request(symbol)
        try:
            return self._crypto_data_client().get_crypto_latest_quote(request)
        except Exception as exc:
            raise AlpacaSdkClientReadError(
                "get_crypto_latest_quote_failed",
                exc,
            ) from exc

    def get_latest_crypto_quote(self, symbol: str) -> Any:
        return self.get_crypto_latest_quote(symbol)

    def get_crypto_latest_trade(self, symbol: str) -> Any:
        request = _to_sdk_crypto_latest_trade_request(symbol)
        try:
            return self._crypto_data_client().get_crypto_latest_trade(request)
        except Exception as exc:
            raise AlpacaSdkClientReadError(
                "get_crypto_latest_trade_failed",
                exc,
            ) from exc

    def get_latest_crypto_trade(self, symbol: str) -> Any:
        return self.get_crypto_latest_trade(symbol)

    def get_crypto_latest_bar(self, symbol: str) -> Any:
        request = _to_sdk_crypto_latest_bar_request(symbol)
        try:
            return self._crypto_data_client().get_crypto_latest_bar(request)
        except Exception as exc:
            raise AlpacaSdkClientReadError(
                "get_crypto_latest_bar_failed",
                exc,
            ) from exc

    def get_latest_crypto_bar(self, symbol: str) -> Any:
        return self.get_crypto_latest_bar(symbol)

    def _crypto_data_client(self) -> Any:
        if self._sdk_crypto_data_client is None:
            factory = self._sdk_crypto_data_client_factory or _create_crypto_data_client
            self._sdk_crypto_data_client = factory(self._config)

        return self._sdk_crypto_data_client


def _create_trading_client(config: AlpacaPaperConfig) -> Any:
    from alpaca.trading.client import TradingClient

    return TradingClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
        paper=True,
        url_override=config.alpaca_paper_base_url,
    )


def _create_crypto_data_client(config: AlpacaPaperConfig) -> Any:
    from alpaca.data.historical import CryptoHistoricalDataClient

    return CryptoHistoricalDataClient(
        api_key=config.alpaca_api_key,
        secret_key=config.alpaca_secret_key,
    )


SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES = ("USD",)
_CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN = re.compile(r"^[A-Z0-9]+$")


def crypto_market_data_symbol_normalization(
    symbol: str,
) -> CryptoMarketDataSymbolNormalization:
    raw_symbol = "" if symbol is None else str(symbol).strip()
    upper_symbol = raw_symbol.upper()
    if not upper_symbol:
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol="",
            provider_symbol="",
            status="failed",
            blocker_code="broker_price_symbol_normalization_failed",
        )

    if "/" in upper_symbol:
        parts = tuple(part.strip() for part in upper_symbol.split("/"))
        if (
            len(parts) != 2
            or not parts[0]
            or not parts[1]
            or parts[1] not in SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES
            or not _CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN.fullmatch(parts[0])
        ):
            return CryptoMarketDataSymbolNormalization(
                input_symbol=raw_symbol,
                compact_symbol="".join(parts),
                provider_symbol="",
                status="failed",
                blocker_code="broker_price_symbol_normalization_failed",
            )
        if parts[0] in SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES:
            return CryptoMarketDataSymbolNormalization(
                input_symbol=raw_symbol,
                compact_symbol="".join(parts),
                provider_symbol="",
                status="ambiguous",
                blocker_code="broker_price_symbol_ambiguous",
            )
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol="".join(parts),
            provider_symbol=f"{parts[0]}/{parts[1]}",
            status="already_normalized",
        )

    if not _CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN.fullmatch(upper_symbol):
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol=upper_symbol,
            provider_symbol="",
            status="failed",
            blocker_code="broker_price_symbol_normalization_failed",
        )

    matches: list[tuple[str, str]] = []
    for quote in SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES:
        if upper_symbol.endswith(quote) and upper_symbol != quote:
            base = upper_symbol[: -len(quote)]
            if base:
                matches.append((base, quote))

    if not matches:
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol=upper_symbol,
            provider_symbol="",
            status="failed",
            blocker_code="broker_price_symbol_normalization_failed",
        )
    if len(matches) != 1 or matches[0][0] in SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES:
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol=upper_symbol,
            provider_symbol="",
            status="ambiguous",
            blocker_code="broker_price_symbol_ambiguous",
        )

    base, quote = matches[0]
    return CryptoMarketDataSymbolNormalization(
        input_symbol=raw_symbol,
        compact_symbol=upper_symbol,
        provider_symbol=f"{base}/{quote}",
        status="normalized",
    )


def normalize_crypto_market_data_symbol(symbol: str) -> str:
    normalization = crypto_market_data_symbol_normalization(symbol)
    if normalization.blocker_code:
        raise AlpacaCryptoSymbolNormalizationError(normalization)
    return normalization.provider_symbol


def _to_sdk_crypto_latest_quote_request(symbol: str) -> Any:
    provider_symbol = normalize_crypto_market_data_symbol(symbol)

    from alpaca.data.requests import CryptoLatestQuoteRequest

    return CryptoLatestQuoteRequest(symbol_or_symbols=provider_symbol)


def _to_sdk_crypto_latest_trade_request(symbol: str) -> Any:
    provider_symbol = normalize_crypto_market_data_symbol(symbol)

    from alpaca.data.requests import CryptoLatestTradeRequest

    return CryptoLatestTradeRequest(symbol_or_symbols=provider_symbol)


def _to_sdk_crypto_latest_bar_request(symbol: str) -> Any:
    provider_symbol = normalize_crypto_market_data_symbol(symbol)

    from alpaca.data.requests import CryptoLatestBarRequest

    return CryptoLatestBarRequest(symbol_or_symbols=provider_symbol)



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


def _read_diagnostic_message_suffix(sanitized_message: str) -> str:
    if not sanitized_message:
        return ""

    return f" api_error_message={sanitized_message}"


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


__all__ = [
    "AlpacaCryptoSymbolNormalizationError",
    "AlpacaSdkClient",
    "AlpacaSdkClientError",
    "AlpacaSdkClientReadError",
    "CryptoMarketDataSymbolNormalization",
    "crypto_market_data_symbol_normalization",
    "normalize_crypto_market_data_symbol",
]
