"""Shared fake Alpaca-like clients for deterministic tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaOrderRequest,
    AlpacaOrderSubmissionResponse,
    AlpacaPositionResponse,
)


NOW = datetime(2026, 4, 28, tzinfo=UTC)


class FakeAlpacaClient:
    def __init__(self, order_status: str = "accepted") -> None:
        self.order_status = order_status
        self.calls: list[str] = []
        self.submitted_requests: list[AlpacaOrderRequest] = []

    def get_account(self) -> AlpacaAccountResponse:
        self.calls.append("get_account")
        return AlpacaAccountResponse(
            account_id="paper-account-1",
            status="ACTIVE",
            cash=Decimal("100000"),
            buying_power=Decimal("200000"),
            equity=Decimal("100000"),
        )

    def get_positions(self) -> list[AlpacaPositionResponse]:
        self.calls.append("get_positions")
        return [
            AlpacaPositionResponse(
                symbol="msft",
                qty=Decimal("3"),
                market_value=Decimal("300.30"),
                average_entry_price=Decimal("100.10"),
            )
        ]

    def submit_order(self, request: AlpacaOrderRequest):
        self.calls.append("submit_order")
        self.submitted_requests.append(request)

        if self.order_status == "rejected":
            return {
                "order_id": "broker-order-2",
                "client_order_id": request.client_order_id,
                "symbol": request.symbol,
                "side": request.side,
                "qty": str(request.qty),
                "status": "rejected",
                "reject_reason": "insufficient buying power",
            }

        return AlpacaOrderSubmissionResponse(
            order_id="broker-order-1",
            client_order_id=request.client_order_id,
            symbol=request.symbol,
            side=request.side,
            qty=request.qty,
            status="accepted",
            submitted_at=NOW,
        )


class RejectingFakeAlpacaClient(FakeAlpacaClient):
    def __init__(self) -> None:
        super().__init__(order_status="rejected")


class FailingFakeAlpacaClient(FakeAlpacaClient):
    def get_account(self) -> AlpacaAccountResponse:
        self.calls.append("get_account")
        raise RuntimeError("fake client failed")
