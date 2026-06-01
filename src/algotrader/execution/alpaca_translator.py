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
    filled_quantity: Optional[Decimal] = None
    filled_average_price: Optional[Decimal] = None


@dataclass(frozen=True)
class TranslatedAlpacaOrderObservation:
    symbol: str
    asset_class: str
    side: str
    order_type: str
    time_in_force: str
    quantity: Optional[Decimal]
    notional: Optional[Decimal]
    raw_status: str
    normalized_status: str
    created_at: Any = None
    submitted_at: Any = None
    filled_at: Any = None
    filled_quantity: Optional[Decimal] = None
    filled_average_price: Optional[Decimal] = None
    order_id: str = ""
    client_order_id: str = ""


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
        filled_quantity=_optional_decimal(
            data,
            "filled_qty",
            aliases=("filled_quantity",),
        ),
        filled_average_price=_optional_decimal(
            data,
            "filled_avg_price",
            aliases=("filled_average_price",),
        ),
    )


def translate_alpaca_order_observation(
    response: Any,
) -> TranslatedAlpacaOrderObservation:
    """Translate a fake Alpaca-like recent/open order into an observation DTO."""

    data = _response_data(response)
    raw_status = _optional_text(data, "status", default="") or ""
    return TranslatedAlpacaOrderObservation(
        symbol=(_optional_text(data, "symbol", default="") or "").upper(),
        asset_class=_normalized_optional_enum_text(data, "asset_class"),
        side=_normalized_optional_enum_text(data, "side"),
        order_type=_normalized_optional_enum_text(
            data,
            "order_type",
            aliases=("type",),
        ),
        time_in_force=_normalized_optional_enum_text(data, "time_in_force"),
        quantity=_optional_decimal(data, "qty", aliases=("quantity",)),
        notional=_optional_decimal(data, "notional"),
        raw_status=raw_status,
        normalized_status=normalize_alpaca_order_status(raw_status),
        created_at=_optional_value(data, "created_at", default=None),
        submitted_at=_optional_value(
            data, "submitted_at", aliases=("created_at",), default=None
        ),
        filled_at=_optional_value(data, "filled_at", default=None),
        filled_quantity=_optional_decimal(
            data,
            "filled_qty",
            aliases=("filled_quantity",),
        ),
        filled_average_price=_optional_decimal(
            data,
            "filled_avg_price",
            aliases=("filled_average_price",),
        ),
        order_id=_optional_text(data, "order_id", aliases=("id",), default="") or "",
        client_order_id=_optional_text(data, "client_order_id", default="") or "",
    )


def normalize_alpaca_order_status(value: Any) -> str:
    return _normalize_alpaca_order_status(value)


def _response_data(response: Any) -> dict[str, Any]:
    if isinstance(response, Mapping):
        return dict(response)

    if is_dataclass(response):
        return {field.name: getattr(response, field.name) for field in fields(response)}

    names = (
        "account_id",
        "id",
        "status",
        "asset_class",
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
        "order_type",
        "type",
        "time_in_force",
        "order_id",
        "client_order_id",
        "notional",
        "message",
        "reason",
        "error",
        "reject_reason",
        "created_at",
        "submitted_at",
        "filled_at",
        "filled_qty",
        "filled_quantity",
        "filled_avg_price",
        "filled_average_price",
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


def _normalized_optional_enum_text(
    data: Mapping[str, Any],
    field_name: str,
    aliases: tuple[str, ...] = (),
) -> str:
    value = _optional_value(data, field_name, aliases, default=None)
    if value is None:
        return ""

    enum_value = getattr(value, "value", None)
    text = str(enum_value if enum_value is not None else value).strip().lower()
    if "." in text:
        text = text.rsplit(".", 1)[-1]

    return text.replace("-", "_").replace(" ", "_")


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
    "TranslatedAlpacaOrderObservation",
    "TranslatedAlpacaOrderResult",
    "TranslatedAlpacaPosition",
    "normalize_alpaca_order_status",
    "translate_alpaca_account",
    "translate_alpaca_order_observation",
    "translate_alpaca_order_result",
    "translate_alpaca_position",
]
