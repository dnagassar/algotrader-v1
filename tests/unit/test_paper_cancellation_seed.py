from __future__ import annotations

import ast
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

import pytest

from algotrader.execution.order_journal import SqliteOrderJournal
from algotrader.execution.paper_cancellation_seed import (
    PAPER_CANCELLATION_SEED_AUTHORIZATION_PHRASE,
    PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID,
    PAPER_CANCELLATION_SEED_LIMIT_PRICE,
    PAPER_CANCELLATION_SEED_QUANTITY,
    run_paper_cancellation_seed,
)


OCCURRED_AT = datetime(2026, 7, 13, 16, 0, tzinfo=UTC)
BROKER_ORDER_ID = "paper-broker-seed-order-1"


def _env(**overrides: str) -> dict[str, str]:
    values = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "sensitive-paper-key",
        "ALPACA_SECRET_KEY": "sensitive-paper-secret",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "paper-account-expected",
    }
    values.update(overrides)
    return values


def _run(tmp_path: Path, gateway: object, **overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "paper_submit_authorized": True,
        "authorization_phrase": PAPER_CANCELLATION_SEED_AUTHORIZATION_PHRASE,
        "output_path": tmp_path / "seed" / "result.json",
        "journal_path": tmp_path / "state" / "orders.sqlite3",
        "env": _env(),
        "occurred_at": OCCURRED_AT,
        "broker_factory": lambda _config: gateway,
    }
    kwargs.update(overrides)
    return run_paper_cancellation_seed(**kwargs)


def test_exact_submit_is_durably_journaled_and_observed_once(tmp_path: Path) -> None:
    gateway = FakeGateway(status="new")

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "target_ready_for_exact_cancellation"
    assert result["broker_order_id"] == BROKER_ORDER_ID
    assert result["broker_status"] == "new"
    assert result["paper_submit_performed"] is True
    assert result["submit_call_count"] == 1
    assert result["post_submit_read_succeeded"] is True
    assert result["lease_released"] is True
    assert result["cancel_attempted"] is False
    assert result["paper_cancel_performed"] is False
    assert result["replace_attempted"] is False
    assert result["close_attempted"] is False
    assert result["liquidate_attempted"] is False
    assert len(gateway.submit_requests) == 1
    request = gateway.submit_requests[0]
    assert request.client_order_id == PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID
    assert request.symbol == "SPY"
    assert request.side == "buy"
    assert request.asset_class == "equity"
    assert request.qty == PAPER_CANCELLATION_SEED_QUANTITY
    assert request.notional is None
    assert request.order_type == "limit"
    assert request.time_in_force == "day"
    assert request.limit_price == PAPER_CANCELLATION_SEED_LIMIT_PRICE
    assert gateway.lookup_count == 1

    record = SqliteOrderJournal(tmp_path / "state" / "orders.sqlite3").get(
        PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID
    )
    assert record is not None
    assert record.broker_order_id == BROKER_ORDER_ID
    assert record.broker_status == "new"


@pytest.mark.parametrize(
    ("overrides", "expected_blocker"),
    (
        ({"paper_submit_authorized": False}, "paper_submit_not_authorized"),
        ({"authorization_phrase": "wrong"}, "authorization_phrase_mismatch"),
        ({"env": _env(APP_PROFILE="dev")}, "paper_profile_required"),
        ({"env": _env(ALPACA_API_KEY="")}, "paper_api_key_required"),
        ({"env": _env(ALPACA_SECRET_KEY="")}, "paper_secret_key_required"),
        (
            {"env": _env(ALPACA_EXPECTED_PAPER_ACCOUNT_ID="")},
            "expected_paper_account_required",
        ),
        (
            {"env": _env(ALPACA_PAPER_BASE_URL="https://api.alpaca.markets")},
            "exact_paper_endpoint_required",
        ),
        (
            {"env": _env(ALPACA_BASE_URL="https://api.alpaca.markets")},
            "live_endpoint_detected:ALPACA_BASE_URL",
        ),
    ),
)
def test_configuration_blocks_before_broker_access(
    tmp_path: Path,
    overrides: dict[str, object],
    expected_blocker: str,
) -> None:
    gateway_factory_calls = 0

    def factory(_config):  # noqa: ANN001
        nonlocal gateway_factory_calls
        gateway_factory_calls += 1
        return FakeGateway()

    result = _run(
        tmp_path,
        FakeGateway(),
        broker_factory=factory,
        **overrides,
    )

    assert result["outcome"] == "blocked_before_broker_access"
    assert expected_blocker in result["blockers"]
    assert result["broker_access_performed"] is False
    assert result["paper_submit_performed"] is False
    assert gateway_factory_calls == 0


def test_account_mismatch_blocks_after_read_without_submit(tmp_path: Path) -> None:
    gateway = FakeGateway(account_id="different-paper-account")

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "blocked_after_read_only_observation"
    assert result["blocker"] == "expected_paper_account_mismatch"
    assert result["broker_access_performed"] is True
    assert result["paper_submit_performed"] is False
    assert gateway.submit_requests == []


def test_existing_open_order_blocks_without_submit(tmp_path: Path) -> None:
    gateway = FakeGateway(
        open_orders=(
            SimpleNamespace(
                id="another-paper-order",
                client_order_id="another-client-order",
                status="new",
            ),
        )
    )

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "blocked_after_read_only_observation"
    assert result["blocker"] == "existing_open_order_present"
    assert result["paper_submit_performed"] is False
    assert gateway.submit_requests == []


def test_duplicate_seed_identity_blocks_without_submit(tmp_path: Path) -> None:
    gateway = FakeGateway(
        all_orders=(
            SimpleNamespace(
                id="prior-paper-order",
                client_order_id=PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID,
                status="rejected",
            ),
        )
    )

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "blocked_after_read_only_observation"
    assert result["blocker"] == "duplicate_seed_client_order_id_present"
    assert gateway.submit_requests == []


def test_ambiguous_submit_is_not_retried_on_rerun(tmp_path: Path) -> None:
    gateway = FakeGateway(submit_error=RuntimeError("sensitive-response"))

    first = _run(tmp_path, gateway)
    second = _run(tmp_path, gateway)

    assert first["outcome"] == "stopped_submit_ambiguous_no_retry"
    assert first["submit_call_count"] == 1
    assert first["error_type"] == "RuntimeError"
    assert "sensitive-response" not in str(first)
    assert second["outcome"] == "blocked_durable_reservation"
    assert second["paper_submit_performed"] is False
    assert len(gateway.submit_requests) == 1


def test_filled_seed_stops_without_post_read_or_cancel(tmp_path: Path) -> None:
    gateway = FakeGateway(status="filled", filled_qty="1", filled_avg_price="1.00")

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "stopped_filled_no_cancel"
    assert result["post_submit_read_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["paper_cancel_performed"] is False
    assert len(gateway.submit_requests) == 1


def test_real_sdk_style_enum_values_are_normalized(tmp_path: Path) -> None:
    class AccountStatus(Enum):
        ACTIVE = "ACTIVE"

    class OrderStatus(Enum):
        NEW = "new"

    gateway = FakeGateway(status=OrderStatus.NEW)
    gateway.account.status = AccountStatus.ACTIVE

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "target_ready_for_exact_cancellation"
    assert result["broker_status"] == "new"


def test_source_contains_one_submit_call_and_no_cancel_dispatch() -> None:
    path = Path("src/algotrader/execution/paper_cancellation_seed.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]

    assert calls.count("submit_order") == 1
    assert "cancel_order" not in calls
    assert "cancel_order_by_id" not in calls
    assert "replace_order" not in calls
    assert "close_position" not in calls
    assert "close_all_positions" not in calls


def test_seed_send_callback_is_owned_by_durable_submit_coordinator() -> None:
    path = Path("src/algotrader/execution/paper_cancellation_seed.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    submit_once = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_submit_once"
    )
    execute_calls = [
        node
        for node in ast.walk(submit_once)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "coordinator"
        and node.func.attr == "execute"
    ]

    assert len(execute_calls) == 1
    submit_keyword = next(
        keyword for keyword in execute_calls[0].keywords if keyword.arg == "submit"
    )
    assert isinstance(submit_keyword.value, ast.Lambda)
    send_calls = [
        node
        for node in ast.walk(submit_keyword.value)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "send"
    ]
    assert len(send_calls) == 1


class FakeGateway:
    def __init__(
        self,
        *,
        account_id: str = "paper-account-expected",
        open_orders: tuple[object, ...] = (),
        all_orders: tuple[object, ...] = (),
        status: object = "new",
        filled_qty: str = "0",
        filled_avg_price: str | None = None,
        submit_error: Exception | None = None,
    ) -> None:
        self.account = SimpleNamespace(
            id=account_id,
            account_number="paper-account-number",
            status="active",
            tradable=True,
        )
        self.asset = SimpleNamespace(symbol="SPY", tradable=True)
        self.open_orders = open_orders
        self.all_orders = all_orders
        self.status = status
        self.filled_qty = filled_qty
        self.filled_avg_price = filled_avg_price
        self.submit_error = submit_error
        self.submit_requests: list[object] = []
        self.lookup_count = 0
        self.response: object | None = None

    def get_account(self) -> object:
        return self.account

    def get_asset(self, symbol: str) -> object:
        assert symbol == "SPY"
        return self.asset

    def get_orders(self, query) -> tuple[object, ...]:  # noqa: ANN001
        if query.status_filter == "open":
            return self.open_orders
        return self.all_orders

    def send(self, request) -> object:  # noqa: ANN001
        self.submit_requests.append(request)
        if self.submit_error is not None:
            raise self.submit_error
        self.response = SimpleNamespace(
            id=BROKER_ORDER_ID,
            client_order_id=request.client_order_id,
            status=self.status,
            filled_qty=self.filled_qty,
            filled_avg_price=self.filled_avg_price,
        )
        return self.response

    def lookup_order_by_client_order_id(self, client_order_id: str) -> object | None:
        self.lookup_count += 1
        assert client_order_id == PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID
        return self.response
