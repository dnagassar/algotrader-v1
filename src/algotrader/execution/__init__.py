"""Deterministic execution simulators."""

from typing import TYPE_CHECKING

from .broker_base import Broker, BrokerOrderResult
from .ledger import InMemoryLedger, JsonlLedger, LedgerEvent, LedgerEventType
from .local_broker import LocalBroker
from .reconciler import (
    ReconciliationMismatch,
    ReconciliationReport,
    reconcile_portfolio,
)
from .simulator import ExecutionResult, simulate_order

if TYPE_CHECKING:
    from .alpaca_broker import AlpacaPaperBroker, BrokerNotImplementedError


def __getattr__(name: str) -> object:
    if name in ("AlpacaPaperBroker", "BrokerNotImplementedError"):
        from .alpaca_broker import (
            AlpacaPaperBroker,
            BrokerNotImplementedError,
        )
        if name == "AlpacaPaperBroker":
            return AlpacaPaperBroker
        return BrokerNotImplementedError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "AlpacaPaperBroker",
    "Broker",
    "BrokerNotImplementedError",
    "BrokerOrderResult",
    "ExecutionResult",
    "InMemoryLedger",
    "JsonlLedger",
    "LedgerEvent",
    "LedgerEventType",
    "LocalBroker",
    "ReconciliationMismatch",
    "ReconciliationReport",
    "reconcile_portfolio",
    "simulate_order",
]
