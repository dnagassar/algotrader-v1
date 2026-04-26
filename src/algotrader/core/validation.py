"""Shared validation helpers for deterministic domain models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from algotrader.errors import ValidationError


def decimal_value(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a decimal value.") from exc


def positive(value: Decimal, field_name: str) -> None:
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")


def non_negative(value: Decimal, field_name: str) -> None:
    if value < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")


def symbol_value(value: str) -> str:
    symbol = value.strip().upper()
    if not symbol:
        raise ValidationError("symbol is required.")
    return symbol


def timestamp_value(value: datetime) -> None:
    if not isinstance(value, datetime):
        raise ValidationError("timestamp must be a datetime.")
