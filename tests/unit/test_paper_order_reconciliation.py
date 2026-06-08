from __future__ import annotations

from dataclasses import dataclass
import json

import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.execution.paper_order_reconciliation import (
    PAPER_ORDER_RECONCILIATION_LABELS,
    PaperOrderReconciliationConfig,
    reconcile_paper_order,
    write_paper_order_reconciliation_jsonl,
)


CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
QUANTITY = "0.033172072"
M436_CLIENT_ORDER_ID = "paper-order-m435_spy_etf_sma_tiny_buy_submit"
M436_BROKER_ORDER_ID = "4553f69a-748b-4ce4-a7bb-a9bac1ade9fb"
M436_QUANTITY = "0.033695775"
M436_AVG_FILL_PRICE = "741.636"
MUTATION_METHOD_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "liquidate",
    "replace_order",
    "submit_order",
    "submit_order_request",
}


def test_exact_open_accepted_order_is_nonterminal_and_blocks_next_spy_submit() -> None:
    broker = FakeReconciliationBroker(
        positions=[_position()],
        open_orders=[_order(status="accepted")],
        all_orders=[_order(status="accepted")],
    )

    payload = _reconcile(broker)

    assert payload["exact_order_found"] is True
    assert payload["exact_order_source"] == "open"
    assert payload["observed_status"] == "accepted"
    assert payload["observed_qty"] == QUANTITY
    assert payload["terminal_state"] == "nonterminal"
    assert payload["reconciliation_decision"] == "m376_nonterminal_open"
    assert payload["next_spy_submit_blocked"] is True
    assert "m376_order_nonterminal" in payload["blockers"]
    assert "open_order_present" in payload["blockers"]
    assert payload["spy_position_qty"] == QUANTITY
    assert payload["open_order_count"] == 1
    assert broker.mutation_calls == []


def test_exact_filled_order_is_terminal_and_does_not_block_by_itself() -> None:
    broker = FakeReconciliationBroker(
        positions=[],
        open_orders=[],
        all_orders=[
            _order(
                status="filled",
                filled_qty=QUANTITY,
                filled_avg_price="750.12",
                filled_at="2026-06-03T15:31:00+00:00",
            )
        ],
    )

    payload = _reconcile(broker)

    assert payload["exact_order_found"] is True
    assert payload["exact_order_source"] == "all"
    assert payload["terminal_state"] == "terminal"
    assert payload["terminal_reason"] == "status_filled"
    assert payload["reconciliation_decision"] == "m376_terminal_filled"
    assert payload["next_spy_submit_blocked"] is False
    assert payload["blockers"] == []
    assert payload["observed_filled_qty"] == QUANTITY
    assert payload["observed_avg_fill_price"] == "750.12"


def test_m436_filled_notional_spy_buy_with_empty_broker_qty_reconciles() -> None:
    payload = _reconcile_m436_notional(
        positions=[_m436_position()],
        open_orders=[],
        all_orders=[_m436_order()],
    )

    assert payload["expected_sizing_mode"] == "notional"
    assert payload["exact_order_found"] is True
    assert payload["exact_order_source"] == "all"
    assert payload["observed_symbol"] == "SPY"
    assert payload["observed_side"] == "buy"
    assert payload["observed_status"] == "filled"
    assert payload["observed_qty"] == ""
    assert payload["observed_filled_qty"] == M436_QUANTITY
    assert payload["observed_avg_fill_price"] == M436_AVG_FILL_PRICE
    assert payload["terminal_state"] == "terminal"
    assert payload["terminal_reason"] == "status_filled"
    assert payload["reconciliation_decision"] == "m376_terminal_filled"
    assert payload["mismatches"] == []
    assert payload["blockers"] == []
    assert payload["next_spy_submit_blocked"] is False
    assert payload["spy_position_qty"] == M436_QUANTITY
    assert payload["open_order_count"] == 0


def test_empty_broker_qty_still_blocks_share_quantity_orders() -> None:
    payload = _reconcile(
        FakeReconciliationBroker(
            positions=[_position()],
            open_orders=[],
            all_orders=[
                _order(
                    qty="",
                    status="filled",
                    filled_qty=QUANTITY,
                    filled_at="2026-06-03T15:31:00+00:00",
                )
            ],
        )
    )

    assert payload["exact_order_found"] is False
    assert payload["terminal_state"] == "unknown"
    assert payload["reconciliation_decision"] == "m376_ambiguous"
    assert "qty_mismatch" in payload["mismatches"]
    assert "order_identity_mismatch" in payload["blockers"]


def test_m436_notional_mismatched_filled_qty_blocks() -> None:
    payload = _reconcile_m436_notional(
        positions=[_m436_position()],
        open_orders=[],
        all_orders=[_m436_order(filled_qty="0.01")],
    )

    assert payload["exact_order_found"] is False
    assert payload["terminal_state"] == "unknown"
    assert payload["reconciliation_decision"] == "m376_ambiguous"
    assert "filled_qty_mismatch" in payload["mismatches"]
    assert "order_identity_mismatch" in payload["blockers"]


def test_m436_notional_identity_shape_mismatches_still_block() -> None:
    cases = (
        (_m436_order(symbol="QQQ"), "symbol_mismatch"),
        (_m436_order(side="sell"), "side_mismatch"),
        (_m436_order(client_order_id="other-client"), "client_order_id_mismatch"),
        (_m436_order(order_id="other-broker"), "broker_order_id_mismatch"),
    )

    for order, expected_mismatch in cases:
        payload = _reconcile_m436_notional(
            positions=[_m436_position()],
            open_orders=[],
            all_orders=[order],
        )

        assert payload["exact_order_found"] is False
        assert payload["terminal_state"] == "unknown"
        assert payload["reconciliation_decision"] == "m376_ambiguous"
        assert expected_mismatch in payload["mismatches"]
        assert "order_identity_mismatch" in payload["blockers"]


def test_m436_notional_nonterminal_status_blocks_clean_reconciliation() -> None:
    payload = _reconcile_m436_notional(
        positions=[_m436_position()],
        open_orders=[],
        all_orders=[_m436_order(status="accepted", filled_at="")],
    )

    assert payload["exact_order_found"] is True
    assert payload["terminal_state"] == "nonterminal"
    assert payload["terminal_reason"] == "status_accepted_active"
    assert payload["reconciliation_decision"] == "m376_nonterminal_open"
    assert "m376_order_nonterminal" in payload["blockers"]
    assert payload["next_spy_submit_blocked"] is True


def test_m436_notional_open_spy_order_remains_blocker() -> None:
    payload = _reconcile_m436_notional(
        positions=[_m436_position()],
        open_orders=[
            _m436_order(
                client_order_id="open-spy-client",
                order_id="open-spy-broker",
                status="accepted",
                filled_qty="0",
                filled_at="",
            )
        ],
        all_orders=[_m436_order()],
    )

    assert payload["exact_order_found"] is True
    assert payload["terminal_state"] == "terminal"
    assert payload["reconciliation_decision"] == "m376_terminal_filled"
    assert payload["open_order_count"] == 1
    assert "open_order_present" in payload["blockers"]
    assert payload["next_spy_submit_blocked"] is True


def test_m436_notional_unexpected_non_spy_position_remains_blocker() -> None:
    payload = _reconcile_m436_notional(
        positions=[_m436_position(), _position(symbol="QQQ", quantity="1")],
        open_orders=[],
        all_orders=[_m436_order()],
    )

    assert payload["exact_order_found"] is True
    assert payload["terminal_state"] == "terminal"
    assert payload["reconciliation_decision"] == "m376_terminal_filled"
    assert payload["non_spy_positions"] == ["QQQ"]
    assert payload["unexpected_non_spy_position_present"] is True
    assert "unexpected_non_spy_position" in payload["blockers"]
    assert payload["next_spy_submit_blocked"] is True


def test_exact_order_not_found_is_conservative_without_complete_history() -> None:
    broker = FakeReconciliationBroker(
        positions=[_position()],
        open_orders=[],
        all_orders=[_order(client_order_id="other-client", order_id="other-broker")],
        closed_orders=[],
    )

    payload = _reconcile(broker)

    assert payload["exact_order_found"] is False
    assert payload["exact_order_source"] == "not_found"
    assert payload["terminal_state"] == "unknown"
    assert payload["reconciliation_decision"] == "m376_not_found"
    assert payload["next_spy_submit_blocked"] is True
    assert "exact_order_not_found" in payload["blockers"]
    assert "order_history_coverage_incomplete" in payload["blockers"]


def test_mismatched_exact_identifier_or_order_shape_blocks() -> None:
    cases = (
        (_order(client_order_id="other-client"), "client_order_id_mismatch"),
        (_order(order_id="other-broker"), "broker_order_id_mismatch"),
        (_order(symbol="QQQ"), "symbol_mismatch"),
        (_order(side="buy"), "side_mismatch"),
        (_order(qty="0.01"), "qty_mismatch"),
    )

    for order, expected_mismatch in cases:
        broker = FakeReconciliationBroker(
            positions=[_position()],
            open_orders=[],
            all_orders=[order],
            closed_orders=[],
        )

        payload = _reconcile(broker)

        assert payload["exact_order_found"] is False
        assert payload["exact_order_source"] == "ambiguous"
        assert payload["terminal_state"] == "unknown"
        assert payload["reconciliation_decision"] == "m376_ambiguous"
        assert payload["next_spy_submit_blocked"] is True
        assert expected_mismatch in payload["mismatches"]
        assert "order_identity_mismatch" in payload["blockers"]


def test_multiple_conflicting_matches_are_ambiguous_and_blocking() -> None:
    broker = FakeReconciliationBroker(
        positions=[_position()],
        open_orders=[_order(status="accepted")],
        all_orders=[
            _order(
                status="filled",
                filled_qty=QUANTITY,
                filled_at="2026-06-03T15:31:00+00:00",
            )
        ],
    )

    payload = _reconcile(broker)

    assert payload["exact_order_found"] is False
    assert payload["exact_order_source"] == "ambiguous"
    assert payload["terminal_state"] == "unknown"
    assert payload["terminal_reason"] == "multiple_conflicting_matches"
    assert payload["reconciliation_decision"] == "m376_ambiguous"
    assert "multiple_conflicting_matches" in payload["blockers"]
    assert payload["next_spy_submit_blocked"] is True


def test_broker_unavailable_never_marks_submit_or_mutation_flags() -> None:
    payload = reconcile_paper_order(
        _config(),
        broker=None,
        query_factory=_query_factory,
    )

    assert payload["reconciliation_decision"] == "broker_unavailable"
    assert payload["order_observation_available"] is False
    assert payload["exact_order_source"] == "unavailable"
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["live_authorized"] is False


def test_artifact_always_includes_safety_flags_and_labels(tmp_path) -> None:  # noqa: ANN001
    broker = FakeReconciliationBroker(
        positions=[],
        open_orders=[],
        all_orders=[_order(status="filled", filled_qty=QUANTITY)],
    )
    payload = _reconcile(broker)
    output_path = tmp_path / "runs" / "paper_lab" / "reconcile.jsonl"

    result = write_paper_order_reconciliation_jsonl(payload, output_path)
    records = _read_jsonl(output_path)

    assert result.record_count == 1
    assert records[0]["submitted"] is False
    assert records[0]["mutated"] is False
    assert records[0]["broker_action_performed"] is False
    assert records[0]["live_authorized"] is False
    assert records[0]["labels"] == list(PAPER_ORDER_RECONCILIATION_LABELS)
    assert records[0]["credentials_redacted"] is True


def test_cli_dev_reconcile_does_not_construct_real_broker(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_dev_env(monkeypatch)

    def forbidden_build(paper_config):  # noqa: ANN001
        raise AssertionError("normal pytest must not build a paper broker")

    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_build)
    run_log = tmp_path / "runs" / "paper_lab" / "reconcile.jsonl"

    exit_code, payload = _run_json(
        (
            "paper-order-reconcile",
            "--symbol",
            "SPY",
            "--client-order-id",
            CLIENT_ORDER_ID,
            "--broker-order-id",
            BROKER_ORDER_ID,
            "--expected-side",
            "sell",
            "--expected-qty",
            QUANTITY,
            "--run-log",
            str(run_log),
            "--run-id",
            "m379_m376_spy_close_order_reconciliation",
            "--format",
            "json",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 0
    assert payload["reconciliation_decision"] == "broker_unavailable"
    assert payload["paper_profile_ready"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert records == [payload]


def test_cli_paper_reconcile_uses_read_only_order_queries(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_paper_env(monkeypatch)
    fake_broker = FakeReconciliationBroker(
        positions=[_position()],
        open_orders=[_order(status="accepted")],
        all_orders=[_order(status="accepted")],
    )
    monkeypatch.setattr(
        cli_module,
        "_build_paper_broker",
        lambda paper_config: fake_broker,
    )
    run_log = tmp_path / "runs" / "paper_lab" / "reconcile.jsonl"

    exit_code, payload = _run_json(
        (
            "paper-order-reconcile",
            "--symbol",
            "SPY",
            "--client-order-id",
            CLIENT_ORDER_ID,
            "--broker-order-id",
            BROKER_ORDER_ID,
            "--expected-side",
            "sell",
            "--expected-qty",
            QUANTITY,
            "--run-log",
            str(run_log),
            "--run-id",
            "m379_m376_spy_close_order_reconciliation",
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 0
    assert payload["exact_order_source"] == "open"
    assert fake_broker.calls == [
        "get_account",
        "get_positions",
        "get_recent_orders",
        "get_recent_orders",
        "get_recent_orders",
    ]
    assert [query.status_filter for query in fake_broker.order_queries] == [
        "open",
        "all",
        "closed",
    ]
    assert fake_broker.mutation_calls == []


@dataclass(frozen=True)
class FakeOrderQuery:
    status_filter: str


class FakeReconciliationBroker:
    def __init__(
        self,
        *,
        positions: list[dict[str, object]] | None = None,
        open_orders: list[dict[str, object]] | None = None,
        all_orders: list[dict[str, object]] | None = None,
        closed_orders: list[dict[str, object]] | None = None,
    ) -> None:
        self.positions = positions or []
        self.orders = {
            "open": open_orders or [],
            "all": all_orders or [],
            "closed": closed_orders or [],
        }
        self.calls: list[str] = []
        self.order_queries: list[object] = []
        self.mutation_calls: list[str] = []

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return {"cash": "1000", "currency": "USD"}

    def get_positions(self) -> list[dict[str, object]]:
        self.calls.append("get_positions")
        return list(self.positions)

    def get_recent_orders(self, query) -> list[dict[str, object]]:  # noqa: ANN001
        self.calls.append("get_recent_orders")
        self.order_queries.append(query)
        return list(self.orders.get(query.status_filter, []))

    def __getattr__(self, name: str):  # noqa: ANN204
        if name in MUTATION_METHOD_NAMES:
            self.mutation_calls.append(name)
            raise AssertionError(f"mutation method must not be accessed: {name}")
        raise AttributeError(name)


def _reconcile(
    broker: FakeReconciliationBroker,
    **config_overrides: object,
) -> dict[str, object]:
    return reconcile_paper_order(
        _config(**config_overrides),
        broker=broker,
        query_factory=_query_factory,
    )


def _reconcile_m436_notional(
    *,
    positions: list[dict[str, object]],
    open_orders: list[dict[str, object]],
    all_orders: list[dict[str, object]],
) -> dict[str, object]:
    return _reconcile(
        FakeReconciliationBroker(
            positions=positions,
            open_orders=open_orders,
            all_orders=all_orders,
        ),
        run_id="m438_m436_spy_buy_read_only_reconciliation_repaired",
        client_order_id=M436_CLIENT_ORDER_ID,
        broker_order_id=M436_BROKER_ORDER_ID,
        expected_side="buy",
        expected_qty=M436_QUANTITY,
        expected_sizing_mode="notional",
    )


def _config(**overrides: object) -> PaperOrderReconciliationConfig:
    values = {
        "run_id": "m379_m376_spy_close_order_reconciliation",
        "symbol": "SPY",
        "client_order_id": CLIENT_ORDER_ID,
        "broker_order_id": BROKER_ORDER_ID,
        "expected_side": "sell",
        "expected_qty": QUANTITY,
        "profile_gate_passed": True,
        "profile_gate_detail": "",
        "paper_profile_ready": True,
        "live_url_detected": False,
    }
    values.update(overrides)
    return PaperOrderReconciliationConfig(**values)


def _query_factory(status_filter: str) -> FakeOrderQuery:
    return FakeOrderQuery(status_filter=status_filter)


def _order(
    *,
    client_order_id: str = CLIENT_ORDER_ID,
    order_id: str = BROKER_ORDER_ID,
    symbol: str = "SPY",
    side: str = "sell",
    qty: str = QUANTITY,
    status: str = "accepted",
    filled_qty: str = "0",
    filled_avg_price: str = "",
    submitted_at: str = "2026-06-03T15:30:00+00:00",
    filled_at: str = "",
) -> dict[str, object]:
    return {
        "client_order_id": client_order_id,
        "filled_at": filled_at,
        "filled_avg_price": filled_avg_price,
        "filled_qty": filled_qty,
        "order_id": order_id,
        "qty": qty,
        "side": side,
        "status": status,
        "submitted_at": submitted_at,
        "symbol": symbol,
    }


def _m436_order(
    *,
    client_order_id: str = M436_CLIENT_ORDER_ID,
    order_id: str = M436_BROKER_ORDER_ID,
    symbol: str = "SPY",
    side: str = "buy",
    qty: str = "",
    status: str = "filled",
    filled_qty: str = M436_QUANTITY,
    filled_avg_price: str = M436_AVG_FILL_PRICE,
    submitted_at: str = "2026-06-04T15:30:00+00:00",
    filled_at: str = "2026-06-04T15:30:03+00:00",
) -> dict[str, object]:
    return _order(
        client_order_id=client_order_id,
        order_id=order_id,
        symbol=symbol,
        side=side,
        qty=qty,
        status=status,
        filled_qty=filled_qty,
        filled_avg_price=filled_avg_price,
        submitted_at=submitted_at,
        filled_at=filled_at,
    )


def _position(
    *,
    symbol: str = "SPY",
    quantity: str = QUANTITY,
    average_price: str = "753.646",
) -> dict[str, object]:
    return {
        "average_price": average_price,
        "quantity": quantity,
        "symbol": symbol,
    }


def _m436_position() -> dict[str, object]:
    return _position(quantity=M436_QUANTITY, average_price=M436_AVG_FILL_PRICE)


def _set_dev_env(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("APP_PROFILE", "dev")
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def _set_paper_env(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "paper-key-for-test")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "paper-secret-for-test")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper.example.test")


def _run_json(argv: tuple[str, ...], capsys) -> tuple[int, dict[str, object]]:  # noqa: ANN001
    exit_code = main(argv)
    captured = capsys.readouterr()
    assert captured.err == ""
    return exit_code, json.loads(captured.out.strip())


def _read_jsonl(path) -> list[dict[str, object]]:  # noqa: ANN001
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
