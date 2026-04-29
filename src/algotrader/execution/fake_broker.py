"""Backward-compatible import path for ``LocalBroker``.

The implementation now lives in ``algotrader.execution.local_broker``.
"""

from __future__ import annotations

from algotrader.execution.local_broker import LocalBroker

__all__ = ["LocalBroker"]
