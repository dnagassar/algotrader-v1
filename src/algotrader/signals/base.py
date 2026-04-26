"""Small interface for deterministic signal generation."""

from __future__ import annotations

from typing import Protocol

from algotrader.core.types import Bar, ProposedOrder, Quote


class SignalGenerator(Protocol):
    """Protocol for pure signal generators."""

    def generate_order(
        self,
        previous_bar: Bar,
        quote: Quote,
    ) -> ProposedOrder | None:
        """Return a proposed order when a deterministic signal is present."""
