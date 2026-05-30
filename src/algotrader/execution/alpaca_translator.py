"""Pure Alpaca response translators for future paper broker integration.

The functions in this module accept fake Alpaca-like dict or dataclass-style
objects only. They return pinned translated DTOs and intentionally do not
import alpaca-py, instantiate clients, read credentials, perform network calls,
or construct internal domain models.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
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
    quantity: Optional[Decimal]
    status: str
    accepted: bool
    raw_status: str = field(default="", compare=False)
    filled: bool = field(default=False, compare=False)
    notional: Optional[Decimal] = None
    message: Optional[str] = None
    raw_reason: Optional[str] = field(default=None, compare=False)
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
    quantity, notional = _order_receipt_sizing(data)
    raw_status = _required_text(data, "status")
    status = _normalize_alpaca_order_status(_required_value(data, "status"))
    filled = status == "filled"
    accepted = status in {
        "accepted",
        "new",
        "submitted",
        "pending_new",
        "filled",
        "partially_filled",
    }
    raw_reason = _optional_text(
        data,
        "message",
        aliases=("reason", "error", "reject_reason"),
        default=None,
    )

    return TranslatedAlpacaOrderResult(
        order_id=_optional_text(data, "order_id", aliases=("id",), default="") or "",
        client_order_id=_optional_text(data, "client_order_id", default="") or "",
        symbol=_required_text(data, "symbol").upper(),
        side=_required_text(data, "side").lower(),
        quantity=quantity,
        status=status,
        raw_status=raw_status,
        accepted=accepted,
        filled=filled,
        notional=notional,
        message=raw_reason,
        raw_reason=raw_reason,
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
        "notional",
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


def _order_receipt_sizing(
    data: Mapping[str, Any],
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    quantity = _optional_decimal(data, "qty", aliases=("quantity",))
    notional = _optional_decimal(data, "notional")
    if quantity is None and notional is None:
        raise AlpacaTranslationError(
            "Missing required field in Alpaca response: qty, quantity, notional."
        )

    return quantity, notional


def _normalize_alpaca_order_status(value: Any) -> str:
    candidates = []
    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        candidates.append(enum_value)
    candidates.append(value)

    for candidate in candidates:
        text = str(candidate).strip()
        if not text:
            continue

        normalized = text.lower()
        if "." in normalized:
            normalized = normalized.rsplit(".", 1)[-1]
        return normalized.replace("-", "_").replace(" ", "_")

    return ""


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


def _optional_decimal(
    data: Mapping[str, Any],
    field_name: str,
    aliases: tuple[str, ...] = (),
) -> Optional[Decimal]:
    for name in (field_name, *aliases):
        if name not in data or data[name] is None:
            continue

        value = data[name]
        if isinstance(value, str) and not value.strip():
            continue

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise AlpacaTranslationError(
                f"Invalid decimal field in Alpaca response: {name}."
            ) from None

    return None


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
