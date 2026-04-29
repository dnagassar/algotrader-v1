"""Pure Alpaca response translators for future paper broker integration.

The functions in this module accept fake Alpaca-like dict or dataclass-style
objects only. They return pinned translated DTOs and intentionally do not
import alpaca-py, instantiate clients, read credentials, perform network calls,
or construct internal domain models.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


class AlpacaTranslationError(ValueError):
    """Raised when a fake Alpaca-like response cannot be translated safely."""


@dataclass(frozen=True)
class TranslatedAlpacaAccount:
    account_id: str
    status: str
    cash: Decimal
    buying_power: Decimal
    equity: Decimal
    currency: str = "USD"


@dataclass(frozen=True)
class TranslatedAlpacaPosition:
    symbol: str
    quantity: Decimal
    market_value: Decimal
    average_entry_price: Decimal
    side: str = "long"


@dataclass(frozen=True)
class TranslatedAlpacaOrderResult:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: Decimal
    status: str
    accepted: bool
    message: Optional[str] = None
    submitted_at: Optional[datetime] = None


def translate_alpaca_account(response: Any) -> TranslatedAlpacaAccount:
    """Translate a fake Alpaca-like account response into a pinned DTO."""

    data = _response_data(response)
    return TranslatedAlpacaAccount(
        account_id=_required_text(data, "account_id", aliases=("id",)),
        status=_required_text(data, "status"),
        cash=_required_decimal(data, "cash"),
        buying_power=_required_decimal(data, "buying_power"),
        equity=_required_decimal(data, "equity", aliases=("portfolio_value",)),
        currency=_optional_text(data, "currency", default="USD") or "USD",
    )


def translate_alpaca_position(response: Any) -> TranslatedAlpacaPosition:
    """Translate a fake Alpaca-like position response into a pinned DTO."""

    data = _response_data(response)
    return TranslatedAlpacaPosition(
        symbol=_required_text(data, "symbol").upper(),
        quantity=_required_decimal(data, "qty", aliases=("quantity",)),
        market_value=_required_decimal(data, "market_value"),
        average_entry_price=_required_decimal(
            data,
            "average_entry_price",
            aliases=("avg_entry_price", "avg_price", "average_price"),
        ),
        side=_optional_text(data, "side", default="long") or "long",
    )


def translate_alpaca_order_result(response: Any) -> TranslatedAlpacaOrderResult:
    """Translate a fake Alpaca-like order response into a pinned DTO."""

    data = _response_data(response)
    status = _required_text(data, "status").lower()
    accepted = status in {
        "accepted",
        "new",
        "submitted",
        "pending_new",
        "filled",
        "partially_filled",
    }

    return TranslatedAlpacaOrderResult(
        order_id=_optional_text(data, "order_id", aliases=("id",), default="") or "",
        client_order_id=_optional_text(data, "client_order_id", default="") or "",
        symbol=_required_text(data, "symbol").upper(),
        side=_required_text(data, "side").lower(),
        quantity=_required_decimal(data, "qty", aliases=("quantity",)),
        status=status,
        accepted=accepted,
        message=_optional_text(
            data,
            "message",
            aliases=("reason", "error", "reject_reason"),
            default=None,
        ),
        submitted_at=_optional_value(
            data, "submitted_at", aliases=("created_at",), default=None
        ),
    )


def _response_data(response: Any) -> dict[str, Any]:
    if isinstance(response, Mapping):
        return dict(response)

    if is_dataclass(response):
        return {field.name: getattr(response, field.name) for field in fields(response)}

    names = (
        "account_id",
        "id",
        "status",
        "cash",
        "buying_power",
        "equity",
        "portfolio_value",
        "currency",
        "symbol",
        "qty",
        "quantity",
        "market_value",
        "average_entry_price",
        "avg_entry_price",
        "avg_price",
        "average_price",
        "side",
        "order_id",
        "client_order_id",
        "message",
        "reason",
        "error",
        "reject_reason",
        "submitted_at",
        "created_at",
    )
    return {
        name: getattr(response, name)
        for name in names
        if hasattr(response, name)
    }


def _required_decimal(
    data: Mapping[str, Any],
    field_name: str,
    aliases: tuple[str, ...] = (),
) -> Decimal:
    value = _required_value(data, field_name, aliases)

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise AlpacaTranslationError(
            f"Invalid decimal field in Alpaca response: {field_name}."
        ) from None


def _required_text(
    data: Mapping[str, Any],
    field_name: str,
    aliases: tuple[str, ...] = (),
) -> str:
    value = _required_value(data, field_name, aliases)
    text = str(value).strip()

    if not text:
        raise AlpacaTranslationError(
            f"Invalid text field in Alpaca response: {field_name}."
        )

    return text


def _optional_text(
    data: Mapping[str, Any],
    field_name: str,
    aliases: tuple[str, ...] = (),
    default: Optional[str] = None,
) -> Optional[str]:
    value = _optional_value(data, field_name, aliases, default)
    if value is None:
        return None

    text = str(value).strip()
    return text if text else default


def _optional_value(
    data: Mapping[str, Any],
    field_name: str,
    aliases: tuple[str, ...] = (),
    default: Any = None,
) -> Any:
    for name in (field_name, *aliases):
        if name in data and data[name] is not None:
            return data[name]

    return default


def _required_value(
    data: Mapping[str, Any],
    field_name: str,
    aliases: tuple[str, ...] = (),
) -> Any:
    value = _optional_value(data, field_name, aliases)
    if value is None:
        choices = ", ".join((field_name, *aliases))
        raise AlpacaTranslationError(
            f"Missing required field in Alpaca response: {choices}."
        )

    return value


__all__ = [
    "AlpacaTranslationError",
    "TranslatedAlpacaAccount",
    "TranslatedAlpacaOrderResult",
    "TranslatedAlpacaPosition",
    "translate_alpaca_account",
    "translate_alpaca_order_result",
    "translate_alpaca_position",
]
