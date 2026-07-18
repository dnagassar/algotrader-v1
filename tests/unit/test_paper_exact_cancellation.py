from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.execution.order_journal import (
    CancelJournalState,
    OrderJournalState,
    OrderReservation,
    SqliteOrderJournal,
)
from algotrader.execution.paper_exact_cancellation import (
    PAPER_EXACT_CANCELLATION_AUTHORIZATION_PHRASE,
    run_exact_paper_cancellation,
)


NOW = datetime(2026, 7, 13, 22, 30, tzinfo=UTC)
CLIENT_ORDER_ID = "test-exact-paper-cancel-client"
BROKER_ORDER_ID = "test-exact-paper-cancel-broker"
SYMBOL = "SPY"


class FakeExactCancellationGateway:
    def __init__(
        self,
        *,
        status: str = "accepted",
        account_id: str = "expected-paper-account",
        client_order_id: str = CLIENT_ORDER_ID,
        broker_order_id: str = BROKER_ORDER_ID,
        symbol: str = SYMBOL,
        cancel_error: Exception | None = None,
        cancel_mutates_before_error: bool = False,
    ) -> None:
        self.account_id = account_id
        self.order = {
            "id": broker_order_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "status": status,
            "filled_qty": "0",
            "filled_avg_price": None,
        }
        self.cancel_error = cancel_error
        self.cancel_mutates_before_error = cancel_mutates_before_error
        self.calls: list[str] = []

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return {
            "id": self.account_id,
            "status": "ACTIVE",
            "tradable": True,
        }

    def get_order_by_id(self, broker_order_id: str) -> dict[str, object]:
        self.calls.append(f"get_order_by_id:{broker_order_id}")
        return dict(self.order)

    def execute_exact(self, broker_order_id: str) -> None:
        self.calls.append(f"cancel_order_by_id:{broker_order_id}")
        if self.cancel_mutates_before_error:
            self.order["status"] = "canceled"
        if self.cancel_error is not None:
            raise self.cancel_error
        self.order["status"] = "canceled"


def _paper_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "fake-paper-key",
        "ALPACA_SECRET_KEY": "fake-paper-secret",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "expected-paper-account",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
    }


def _seed_journal(path: Path) -> SqliteOrderJournal:
    journal = SqliteOrderJournal(path)
    reserved_at = NOW - timedelta(minutes=3)
    journal.reserve(
        OrderReservation(
            client_order_id=CLIENT_ORDER_ID,
            execution_plan_id="test-paper-cancel-seed-plan",
            run_id="test-paper-cancel-seed-run",
            symbol=SYMBOL,
            side="buy",
            quantity=Decimal("1"),
            notional=None,
        ),
        reserved_at,
    )
    journal.mark_submit_attempted(
        CLIENT_ORDER_ID,
        reserved_at + timedelta(seconds=1),
    )
    journal.record_broker_observation(
        CLIENT_ORDER_ID,
        reserved_at + timedelta(seconds=2),
        broker_order_id=BROKER_ORDER_ID,
        broker_status="accepted",
        filled_quantity="0",
    )
    return journal


def _run(
    tmp_path: Path,
    gateway: FakeExactCancellationGateway,
    **overrides: object,
) -> dict[str, object]:
    journal_path = tmp_path / "journal.sqlite3"
    if not journal_path.exists():
        _seed_journal(journal_path)
    kwargs: dict[str, object] = {
        "target_client_order_id": CLIENT_ORDER_ID,
        "target_broker_order_id": BROKER_ORDER_ID,
        "target_symbol": SYMBOL,
        "paper_cancel_authorized": True,
        "authorization_phrase": (
            PAPER_EXACT_CANCELLATION_AUTHORIZATION_PHRASE
        ),
        "output_path": tmp_path / "result.json",
        "journal_path": journal_path,
        "env": _paper_env(),
        "occurred_at": NOW,
        "broker_factory": lambda _config: gateway,
    }
    kwargs.update(overrides)
    return run_exact_paper_cancellation(**kwargs)


def test_exact_cancel_uses_pipeline_and_calls_broker_once(tmp_path: Path) -> None:
    gateway = FakeExactCancellationGateway()

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "cancellation_confirmed"
    assert result["cancel_attempted"] is True
    assert result["cancel_call_count"] == 1
    assert result["post_cancel_read_count"] == 1
    assert result["post_cancel_observation_persisted"] is True
    assert result["submit_attempted"] is False
    assert result["replace_attempted"] is False
    assert result["close_attempted"] is False
    assert result["liquidate_attempted"] is False
    assert result["live_access_performed"] is False
    assert result["no_retry"] is True
    assert gateway.calls == [
        "get_account",
        f"get_order_by_id:{BROKER_ORDER_ID}",
        f"cancel_order_by_id:{BROKER_ORDER_ID}",
        f"get_order_by_id:{BROKER_ORDER_ID}",
    ]
    assert result["planning"]["status"] == "planned"
    assert result["handoff"]["status"] == "prepared"
    assert result["admission"]["status"] == "admitted"
    assert result["invocation"]["status"] == "observed"
    assert result["invocation"]["reservation_acquired"] is True
    assert result["invocation"]["lease_acquired"] is True
    assert result["invocation"]["lease_released"] is True

    journal = SqliteOrderJournal(tmp_path / "journal.sqlite3")
    order = journal.get(CLIENT_ORDER_ID)
    assert order is not None
    assert order.state is OrderJournalState.CANCELED
    cancel_records = journal.cancel_intents()
    assert len(cancel_records) == 1
    assert cancel_records[0].state is CancelJournalState.CANCELED
    assert cancel_records[0].safe_to_recancel is False


def test_second_run_stops_locally_without_broker_or_retry(tmp_path: Path) -> None:
    gateway = FakeExactCancellationGateway()
    first = _run(tmp_path, gateway)
    first_call_count = len(gateway.calls)

    second = _run(tmp_path, gateway)

    assert first["outcome"] == "cancellation_confirmed"
    assert second["outcome"] == "blocked_local_target_not_cancel_ready"
    assert second["blocker"] == "local_target_terminal"
    assert second["broker_access_performed"] is False
    assert second["cancel_call_count"] == 0
    assert len(gateway.calls) == first_call_count


def test_terminal_pre_observation_stops_without_cancel(tmp_path: Path) -> None:
    gateway = FakeExactCancellationGateway(status="filled")

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "stopped_target_already_terminal"
    assert result["blocker"] == "target_already_terminal:filled"
    assert result["cancel_call_count"] == 0
    assert gateway.calls == [
        "get_account",
        f"get_order_by_id:{BROKER_ORDER_ID}",
    ]
    journal = SqliteOrderJournal(tmp_path / "journal.sqlite3")
    assert journal.cancel_intents() == ()


def test_mismatched_exact_identity_stops_without_cancel(tmp_path: Path) -> None:
    gateway = FakeExactCancellationGateway(client_order_id="different-client")

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "stopped_exact_target_missing_or_mismatched"
    assert result["blocker"] == "client_order_id_mismatch"
    assert result["cancel_call_count"] == 0
    assert all(not call.startswith("cancel_order") for call in gateway.calls)


def test_expected_account_mismatch_stops_without_cancel(tmp_path: Path) -> None:
    gateway = FakeExactCancellationGateway(account_id="different-paper-account")

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "stopped_expected_paper_account_mismatch"
    assert result["cancel_call_count"] == 0
    assert gateway.calls == [
        "get_account",
        f"get_order_by_id:{BROKER_ORDER_ID}",
    ]


def test_missing_authorization_blocks_before_broker_construction(
    tmp_path: Path,
) -> None:
    gateway = FakeExactCancellationGateway()
    factory_calls = 0

    def factory(_config: object) -> FakeExactCancellationGateway:
        nonlocal factory_calls
        factory_calls += 1
        return gateway

    result = _run(
        tmp_path,
        gateway,
        paper_cancel_authorized=False,
        broker_factory=factory,
    )

    assert result["outcome"] == "blocked_before_broker_access"
    assert result["blocker"] == "paper_cancel_not_authorized"
    assert result["cancel_call_count"] == 0
    assert factory_calls == 0
    assert gateway.calls == []


def test_live_endpoint_indicator_blocks_before_broker_construction(
    tmp_path: Path,
) -> None:
    gateway = FakeExactCancellationGateway()
    env = _paper_env()
    env["ALPACA_BASE_URL"] = "https://api.alpaca.markets"

    result = _run(tmp_path, gateway, env=env)

    assert result["outcome"] == "blocked_before_broker_access"
    assert result["blocker"] == "live_endpoint_detected:ALPACA_BASE_URL"
    assert result["live_access_performed"] is False
    assert gateway.calls == []


def test_ambiguous_cancel_is_observed_once_and_never_retried(
    tmp_path: Path,
) -> None:
    gateway = FakeExactCancellationGateway(
        cancel_error=TimeoutError("unsafe broker details"),
        cancel_mutates_before_error=True,
    )

    result = _run(tmp_path, gateway)

    assert result["outcome"] == "cancellation_confirmed"
    assert result["invocation"]["status"] == "ambiguous"
    assert result["invocation"]["safe_error_message"] == "TimeoutError"
    assert "unsafe broker details" not in str(result)
    assert result["cancel_call_count"] == 1
    assert result["post_cancel_read_count"] == 1
    assert result["post_cancel_observation_persisted"] is True
    assert gateway.calls.count(f"cancel_order_by_id:{BROKER_ORDER_ID}") == 1
    assert gateway.calls.count(f"get_order_by_id:{BROKER_ORDER_ID}") == 2
    journal = SqliteOrderJournal(tmp_path / "journal.sqlite3")
    assert journal.cancel_intents()[0].state is CancelJournalState.CANCELED


def test_module_has_one_cancel_call_and_no_other_mutation_surface() -> None:
    path = Path("src/algotrader/execution/paper_exact_cancellation.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert calls.count("cancel_order_by_id") == 1
    assert all(
        name not in calls
        for name in (
            "submit_order",
            "submit_order_request",
            "replace_order",
            "close_position",
            "close_all_positions",
            "liquidate",
        )
    )
    assert "algotrader.cli" not in imports
    assert "algotrader.execution.paper_mutation_oms" not in imports
    assert "algotrader.execution.paper_cancellation_invocation" in imports
