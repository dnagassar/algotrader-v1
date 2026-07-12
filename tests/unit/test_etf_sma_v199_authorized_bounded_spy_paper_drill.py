from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import json
from pathlib import Path

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.execution.etf_sma_v195_bounded_paper_drill_approval_packet import (
    APPROVAL_PACKET_READY_NO_MUTATION,
)
from algotrader.execution.etf_sma_v199_authorized_bounded_spy_paper_drill import (
    PAPER_DRILL_BLOCKED_DUPLICATE_CLIENT_ORDER_ID,
    PAPER_DRILL_BLOCKED_LIVE_ENDPOINT_OR_PROFILE,
    PAPER_DRILL_BLOCKED_OPEN_SPY_ORDER_PRESENT,
    PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE,
    PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED,
    PAPER_DRILL_SUBMITTED_FILLED_BEFORE_CANCEL,
    PAPER_DRILL_SUBMITTED_PARTIAL_FILL_THEN_CANCELLED,
    PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME,
    V199_AUTHORIZATION_PHRASE,
    run_v199_authorized_bounded_spy_paper_drill,
)
from algotrader.execution.order_journal import (
    CancelJournalState,
    SqliteOrderJournal,
)


GENERATED_AT = "2026-06-26T14:00:00+00:00"
CLIENT_ORDER_ID = "v192-spy-43fb12a5d4aa5fbf4990aa7a"
EXPECTED_ACCOUNT_ID = "expected-paper-account-id"
EXPECTED_ACCOUNT_NUMBER = "paper-account-number"
PAPER_KEY = "paper-key-value"
PAPER_SECRET = "paper-secret-value"


def test_submit_then_cancel_confirmed_writes_required_artifacts(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV199Client(submit_status="accepted", cancel_status="canceled")
    output_root = tmp_path / "runs" / "paper_lab" / "v199"

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=output_root,
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env=_paper_env(),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_factory(fake_client),
        reconciliation_poll_attempts=1,
        reconciliation_poll_interval_seconds=0,
    )

    assert packet["outcome_classification"] == PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED
    assert packet["blocker"] == "none"
    assert packet["source_approval_classification"] == APPROVAL_PACKET_READY_NO_MUTATION
    assert packet["explicit_authorization_phrase_observed"] is True
    assert packet["pre_submit_observation_classification"] == (
        "paper_observation_eligible_for_separate_drill_authorization"
    )
    assert packet["expected_account_configured"] is True
    assert packet["expected_account_matched"] is True
    assert packet["expected_account_match_mode"] == "account_id"
    assert packet["account_status"] == "ACTIVE"
    assert packet["account_tradable"] is True
    assert packet["open_spy_order_observed"] is False
    assert packet["unexpected_non_spy_position_observed"] is False
    assert packet["duplicate_client_order_id_observed"] is False
    assert packet["submit_attempted"] is True
    assert packet["submit_accepted"] is True
    assert packet["submit_status"] == "accepted"
    assert packet["submit_accepted_rejected_status"] == "accepted"
    assert packet["cancel_attempted"] is True
    assert packet["cancel_confirmed"] is True
    assert packet["fill_status"] == "unfilled"
    assert packet["final_broker_order_status"] == "canceled"
    assert packet["broker_read_performed"] is True
    assert packet["broker_mutation_performed"] is True
    assert packet["paper_submit_performed"] is True
    assert packet["paper_cancel_performed"] is True
    assert packet["live_read_performed"] is False
    assert packet["live_mutation_performed"] is False
    assert packet["live_trading_performed"] is False
    assert packet["actual_submitted_request_fields"] == {
        "asset_class": "equity",
        "client_order_id": CLIENT_ORDER_ID,
        "notional": "25.00",
        "order_type": "market",
        "quantity": "",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders:open:SPY",
        "get_orders:all:SPY",
        "submit_order",
        "get_orders:all:SPY",
        "cancel_order_by_id:paper-order-1",
        "get_orders:all:SPY",
    ]
    _assert_artifacts(output_root, packet)
    _assert_no_sensitive_values(packet)
    cancel_result = packet["cancel_result"]
    assert cancel_result["durable_cancel_reservation_status"] == "reserved"
    assert cancel_result["durable_cancel_status"] == "observed"
    assert cancel_result["durable_cancel_record"]["state"] == "canceled"
    assert cancel_result["durable_cancel_record"]["safe_to_recancel"] is False
    assert cancel_result["durable_cancel_lease_acquired"] is True
    assert cancel_result["durable_cancel_lease_released"] is True
    journal = SqliteOrderJournal(packet["durable_cancel_journal"]["path"])
    records = journal.cancel_intents()
    assert len(records) == 1
    assert records[0].state is CancelJournalState.CANCELED


def test_cancel_ambiguity_is_durable_unknown_and_redacted(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV199Client(cancel_raises=True)
    output_root = tmp_path / "runs" / "paper_lab" / "v199"

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=output_root,
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env=_paper_env(),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_factory(fake_client),
        reconciliation_poll_attempts=1,
        reconciliation_poll_interval_seconds=0,
    )

    assert packet["outcome_classification"] == PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME
    assert packet["cancel_attempted"] is True
    assert packet["cancel_ambiguous"] is True
    assert fake_client.calls.count("submit_order") == 1
    assert fake_client.calls.count("cancel_order_by_id:paper-order-1") == 1
    cancel_result = packet["cancel_result"]
    assert cancel_result["durable_cancel_status"] == "ambiguous"
    assert cancel_result["durable_cancel_record"]["state"] == "unknown"
    serialized = json.dumps(packet, sort_keys=True)
    assert PAPER_SECRET not in serialized
    assert "https://paper.example.test" not in serialized
    journal = SqliteOrderJournal(packet["durable_cancel_journal"]["path"])
    record = journal.cancel_intents()[0]
    assert record.state is CancelJournalState.UNKNOWN
    assert record.safe_to_recancel is False


def test_cancel_ambiguity_rerun_cannot_submit_or_cancel_again(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV199Client(cancel_raises=True)
    output_root = tmp_path / "runs" / "paper_lab" / "v199"
    kwargs = {
        "approval_packet_path": approval_path,
        "output_root": output_root,
        "timestamp": GENERATED_AT,
        "authorization_phrase": V199_AUTHORIZATION_PHRASE,
        "env": _paper_env(),
        "expected_paper_account_id": EXPECTED_ACCOUNT_ID,
        "broker_client_factory": _factory(fake_client),
        "reconciliation_poll_attempts": 1,
        "reconciliation_poll_interval_seconds": 0,
    }

    first = run_v199_authorized_bounded_spy_paper_drill(**kwargs)
    second = run_v199_authorized_bounded_spy_paper_drill(**kwargs)

    assert first["outcome_classification"] == PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME
    assert second["outcome_classification"] == PAPER_DRILL_BLOCKED_OPEN_SPY_ORDER_PRESENT
    assert fake_client.calls.count("submit_order") == 1
    assert fake_client.calls.count("cancel_order_by_id:paper-order-1") == 1
    journal = SqliteOrderJournal(first["durable_cancel_journal"]["path"])
    records = journal.cancel_intents()
    assert len(records) == 1
    assert records[0].state is CancelJournalState.UNKNOWN
    assert records[0].safe_to_recancel is False


def test_cancel_requires_fresh_same_order_snapshot(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV199Client(hide_current_order_from_reads=True)

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v199",
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env=_paper_env(),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_factory(fake_client),
        reconciliation_poll_attempts=1,
        reconciliation_poll_interval_seconds=0,
    )

    assert packet["outcome_classification"] == PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME
    assert packet["blocker"] == "required_snapshot_not_fresh"
    assert packet["submit_attempted"] is True
    assert packet["cancel_attempted"] is False
    assert "cancel_order_by_id:paper-order-1" not in fake_client.calls
    cancel_result = packet["cancel_result"]
    assert cancel_result["durable_cancel_status"] == "blocked"
    assert cancel_result["durable_cancel_blocker"] == "required_snapshot_not_fresh"
    assert cancel_result["durable_cancel_record"]["state"] == "reserved"


def test_unavailable_cancel_journal_blocks_before_broker_access(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    output_root = tmp_path / "runs" / "paper_lab" / "v199"
    state_root = output_root / ".state"
    state_root.mkdir(parents=True)
    (state_root / "durable_cancel_journal.sqlite3").write_bytes(
        b"not-a-sqlite-database"
    )

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=output_root,
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env=_paper_env(),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_forbidden_factory,
    )

    assert packet["outcome_classification"] == PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE
    assert packet["blocker"] == "durable_cancel_journal_unavailable_before_submit"
    assert packet["durable_cancel_journal"]["initialized"] is False
    assert packet["broker_read_performed"] is False
    assert packet["submit_attempted"] is False
    assert packet["cancel_attempted"] is False


def test_filled_before_cancel_does_not_attempt_cancel(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV199Client(submit_status="filled", filled_quantity="0.041")

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v199",
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env=_paper_env(),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_factory(fake_client),
    )

    assert packet["outcome_classification"] == PAPER_DRILL_SUBMITTED_FILLED_BEFORE_CANCEL
    assert packet["submit_attempted"] is True
    assert packet["cancel_attempted"] is False
    assert packet["paper_cancel_performed"] is False
    assert packet["fill_status"] == "filled"
    assert packet["final_broker_order_status"] == "filled"
    assert "cancel_order_by_id:paper-order-1" not in fake_client.calls
    _assert_no_sensitive_values(packet)


def test_partial_fill_then_cancelled_is_classified(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV199Client(
        submit_status="partially_filled",
        filled_quantity="0.005",
        cancel_status="canceled",
    )

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v199",
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env=_paper_env(),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_factory(fake_client),
        reconciliation_poll_attempts=1,
        reconciliation_poll_interval_seconds=0,
    )

    assert packet["outcome_classification"] == (
        PAPER_DRILL_SUBMITTED_PARTIAL_FILL_THEN_CANCELLED
    )
    assert packet["cancel_attempted"] is True
    assert packet["cancel_confirmed"] is True
    assert packet["fill_status"] == "partial_fill"
    assert packet["final_broker_order_status"] == "canceled"
    _assert_no_sensitive_values(packet)


def test_duplicate_client_order_id_blocks_before_submit(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV199Client(
        recent_orders=(
            {
                "id": "prior-paper-order",
                "client_order_id": CLIENT_ORDER_ID,
                "symbol": "SPY",
                "side": "buy",
                "status": "filled",
                "type": "market",
                "time_in_force": "day",
            },
        ),
    )

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v199",
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env=_paper_env(),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_factory(fake_client),
    )

    assert packet["outcome_classification"] == (
        PAPER_DRILL_BLOCKED_DUPLICATE_CLIENT_ORDER_ID
    )
    assert packet["blocker"] == "duplicate_client_order_id"
    assert packet["submit_attempted"] is False
    assert packet["broker_mutation_performed"] is False
    assert "submit_order" not in fake_client.calls
    _assert_no_sensitive_values(packet)


def test_live_profile_blocks_before_broker_build(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v199",
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env={
            **_paper_env(),
            "APP_PROFILE": "live",
            "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
        },
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_forbidden_factory,
    )

    assert packet["outcome_classification"] == (
        PAPER_DRILL_BLOCKED_LIVE_ENDPOINT_OR_PROFILE
    )
    assert packet["blocker"] == "app_profile_not_paper"
    assert packet["submit_attempted"] is False
    assert packet["broker_read_performed"] is False
    assert packet["broker_mutation_performed"] is False
    _assert_no_sensitive_values(packet)


def test_projected_request_above_cap_blocks_before_broker_build(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path, notional="30.00", cap="25.00")

    packet = run_v199_authorized_bounded_spy_paper_drill(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v199",
        timestamp=GENERATED_AT,
        authorization_phrase=V199_AUTHORIZATION_PHRASE,
        env=_paper_env(),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        broker_client_factory=_forbidden_factory,
    )

    assert packet["outcome_classification"] == PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE
    assert packet["blocker"] == "projected_notional_exceeds_v195_cap"
    assert packet["submit_attempted"] is False
    assert packet["broker_read_performed"] is False
    assert packet["broker_mutation_performed"] is False
    _assert_no_sensitive_values(packet)


class FakeV199Client:
    def __init__(
        self,
        *,
        submit_status: str = "accepted",
        cancel_status: str = "canceled",
        filled_quantity: str = "0",
        account: dict[str, object] | None = None,
        positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        recent_orders: tuple[dict[str, object], ...] = (),
        cancel_raises: bool = False,
        hide_current_order_from_reads: bool = False,
    ) -> None:
        self.account = {
            "account_id": EXPECTED_ACCOUNT_ID,
            "account_number": EXPECTED_ACCOUNT_NUMBER,
            "status": "ACTIVE",
            "trading_blocked": False,
            "account_blocked": False,
            "trade_suspended_by_user": False,
            **(account or {}),
        }
        self.positions = positions
        self.open_orders = list(open_orders)
        self.recent_orders = list(recent_orders)
        self.submit_status = submit_status
        self.cancel_status = cancel_status
        self.filled_quantity = filled_quantity
        self.cancel_raises = cancel_raises
        self.hide_current_order_from_reads = hide_current_order_from_reads
        self.current_order: dict[str, object] | None = None
        self.calls: list[str] = []

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return self.account

    def get_positions(self) -> tuple[dict[str, object], ...]:
        self.calls.append("get_positions")
        return self.positions

    def get_orders(self, query) -> tuple[dict[str, object], ...]:  # noqa: ANN001
        self.calls.append(f"get_orders:{query.status_filter}:{query.symbol_filter}")
        rows = list(self.recent_orders)
        if query.status_filter == "open":
            rows = list(self.open_orders)
            if (
                self.current_order
                and not self.hide_current_order_from_reads
                and self.current_order["status"] not in {
                    "canceled",
                    "cancelled",
                    "expired",
                    "filled",
                    "rejected",
                }
            ):
                rows.append(self.current_order)
        elif self.current_order is not None and not self.hide_current_order_from_reads:
            rows.append(self.current_order)
        if query.symbol_filter:
            rows = [
                row
                for row in rows
                if str(row.get("symbol", "")).upper() == query.symbol_filter
            ]
        return tuple(rows)

    def submit_order(self, request) -> dict[str, object]:  # noqa: ANN001
        self.calls.append("submit_order")
        self.current_order = {
            "id": "paper-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "side": request.side,
            "type": request.order_type,
            "time_in_force": request.time_in_force,
            "notional": request.notional,
            "qty": request.qty,
            "status": self.submit_status,
            "filled_qty": Decimal(self.filled_quantity),
            "filled_avg_price": Decimal("600.00")
            if Decimal(self.filled_quantity) > Decimal("0")
            else Decimal("0"),
            "submitted_at": datetime(2026, 6, 26, 14, 0, tzinfo=UTC),
            "filled_at": datetime(2026, 6, 26, 14, 0, 1, tzinfo=UTC)
            if self.submit_status == "filled"
            else "",
        }
        return self.current_order

    def cancel_order_by_id(self, order_id: str) -> dict[str, object]:
        self.calls.append(f"cancel_order_by_id:{order_id}")
        if self.cancel_raises:
            raise RuntimeError(
                f"cancel failed token={PAPER_SECRET} at https://paper.example.test"
            )
        assert self.current_order is not None
        assert self.current_order["id"] == order_id
        self.current_order = {
            **self.current_order,
            "status": self.cancel_status,
            "canceled_at": datetime(2026, 6, 26, 14, 0, 2, tzinfo=UTC),
        }
        return {"id": order_id, "status": self.cancel_status}


def _write_approval_packet(
    root: Path,
    *,
    notional: str = "25.00",
    cap: str = "25.00",
) -> Path:
    packet = {
        "packet_version": "v195_bounded_paper_drill_approval_packet_v1",
        "run_id": "v195_bounded_paper_drill_approval_packet_smoke",
        "created_at": GENERATED_AT,
        "approval_packet_classification": APPROVAL_PACKET_READY_NO_MUTATION,
        "approval_packet_is_authorization": False,
        "symbol": "SPY",
        "order_side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": notional,
        "quantity": "",
        "deterministic_client_order_id": CLIENT_ORDER_ID,
        "client_order_id": CLIENT_ORDER_ID,
        "maximum_notional_cap": cap,
        "maximum_quantity_cap": "",
        "maximum_notional_or_quantity_cap": cap,
        "maximum_notional_or_quantity_cap_kind": "notional",
        "maximum_notional_or_quantity_cap_source": "paper_order_policy.equity.max_notional_cap",
        "projected_broker_request_fields": {
            "asset_class": "equity",
            "symbol": "SPY",
            "side": "buy",
            "order_type": "market",
            "time_in_force": "day",
            "notional": notional,
            "quantity": "",
            "client_order_id": CLIENT_ORDER_ID,
        },
    }
    path = root / "runs" / "paper_lab" / "v195" / "approval_packet.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, sort_keys=True), encoding="utf-8")
    return path


def _paper_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": PAPER_KEY,
        "APCA_API_SECRET_KEY": PAPER_SECRET,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }


def _factory(fake_client: FakeV199Client):
    def build(_config):  # noqa: ANN001
        return fake_client

    return build


def _forbidden_factory(_config):  # noqa: ANN001
    raise AssertionError("broker factory must not be called")


def _assert_artifacts(output_root: Path, packet: dict[str, object]) -> None:
    paths = packet["artifact_paths"]
    for artifact_path in paths.values():
        assert Path(artifact_path).exists()
    assert json.loads(Path(paths["paper_drill_packet"]).read_text()) == packet
    assert [json.loads(line) for line in Path(paths["paper_drill_record"]).read_text().splitlines()] == [packet]
    assert json.loads(Path(paths["pre_submit_broker_observation_packet"]).read_text())[
        "eligibility_classification"
    ] == "paper_observation_eligible_for_separate_drill_authorization"
    snapshot = json.loads(Path(paths["approval_packet_snapshot"]).read_text())
    assert snapshot["approval_packet_classification"] == APPROVAL_PACKET_READY_NO_MUTATION


def _assert_no_sensitive_values(packet: dict[str, object]) -> None:
    rendered = json.dumps(packet, sort_keys=True)
    for value in (
        EXPECTED_ACCOUNT_ID,
        EXPECTED_ACCOUNT_NUMBER,
        PAPER_KEY,
        PAPER_SECRET,
    ):
        assert value not in rendered
    assert packet["credential_values_exposed"] is False
    assert packet["account_identifiers_serialized"] is False
