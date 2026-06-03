from __future__ import annotations

import ast
from decimal import Decimal
import json
from pathlib import Path

import algotrader.execution.etf_sma_m375_spy_close_preview as m375


def test_ready_payload_previews_exact_m370c_spy_close_intent() -> None:
    broker = FakeM375Broker()

    payload = _run(broker)

    assert payload["ok"] is True
    assert (
        payload["readiness_classification"]
        == m375.READY_FOR_SEPARATE_SPY_CLOSE_SUBMIT_MILESTONE
    )
    assert payload["labels"] == [
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
        "close_preview_only",
    ]
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["submit_authorized"] is False
    assert payload["close_submit_authorized"] is False
    assert payload["broker_mutation_authorized"] is False
    assert payload["account_observation_available"] is True
    assert payload["positions_observation_available"] is True
    assert payload["open_recent_orders_observation_available"] is True
    assert payload["orders_observation_available"] is True
    assert payload["expected_m370c_filled_quantity"] == "0.033172072"
    assert payload["quantity_match_tolerance"] == "0.000000001"
    assert payload["observed_spy_quantity"] == "0.033172072"
    assert payload["observed_spy_average_entry_price"] == "753.646"
    assert payload["observed_spy_quantity_matches_expected"] is True
    assert payload["non_spy_positions_present"] is False
    assert payload["open_orders_present"] is False
    assert payload["spy_position_status"] == "expected_m370c_spy_position_observed"
    assert payload["recent_order_query_metadata_complete"] is True
    assert payload["open_order_count"] == 0
    assert broker.calls == ["get_account", "get_positions", "get_recent_orders"]
    assert broker.queries[0].status_filter == "open"
    assert broker.queries[0].symbol_filter == ""
    assert broker.queries[0].asset_class_filter == ""

    close_intent = payload["close_intent_preview"]
    assert close_intent == {
        "asset_class": "equity",
        "notional": None,
        "order_type": "market",
        "quantity": "0.033172072",
        "required_next_milestone": (
            "M376 - Explicit operator-reviewed SPY paper close submit"
        ),
        "side": "sell",
        "source_position_milestone": "M370C",
        "source_reconciliation_milestone": "M374",
        "submit_authorized": False,
        "symbol": "SPY",
        "time_in_force": "day",
    }


def test_decimal_tolerance_accepts_one_billionth_share_delta() -> None:
    broker = FakeM375Broker(positions=(_position(quantity="0.033172073"),))

    payload = _run(broker)

    assert payload["ok"] is True
    assert payload["observed_spy_quantity_delta"] == "0.000000001"
    assert payload["observed_spy_quantity_matches_expected"] is True


def test_blocks_quantity_mismatch_beyond_decimal_tolerance() -> None:
    broker = FakeM375Broker(positions=(_position(quantity="0.033172074"),))

    payload = _run(broker)

    assert payload["ok"] is False
    assert payload["readiness_classification"] == m375.BLOCKED_SPY_QUANTITY_MISMATCH
    assert payload["observed_spy_quantity_delta"] == "0.000000002"
    assert payload["observed_spy_quantity_matches_expected"] is False
    assert payload["close_intent_preview"] is None


def test_blocks_when_open_orders_are_present() -> None:
    broker = FakeM375Broker(open_orders=(_order("open-order-1"),))

    payload = _run(broker)

    assert payload["ok"] is False
    assert payload["readiness_classification"] == m375.BLOCKED_OPEN_ORDERS_PRESENT
    assert payload["open_orders_present"] is True
    assert payload["open_order_count"] == 1
    assert payload["open_order_symbols"] == ["SPY"]
    assert payload["submitted"] is False
    assert payload["mutated"] is False


def test_blocks_when_non_spy_positions_are_present() -> None:
    broker = FakeM375Broker(
        positions=(
            _position(),
            _position(symbol="MSFT", quantity="1", average_price="420"),
        )
    )

    payload = _run(broker)

    assert payload["ok"] is False
    assert (
        payload["readiness_classification"]
        == m375.BLOCKED_UNEXPECTED_NON_SPY_POSITIONS
    )
    assert payload["non_spy_positions_present"] is True
    assert payload["non_spy_position_symbols"] == ["MSFT"]


def test_blocks_when_spy_position_is_absent_or_zero() -> None:
    absent = _run(FakeM375Broker(positions=()))
    zero = _run(FakeM375Broker(positions=(_position(quantity="0"),)))

    assert absent["readiness_classification"] == (
        m375.BLOCKED_SPY_POSITION_ABSENT_OR_ZERO
    )
    assert absent["spy_position_observed"] is False
    assert zero["readiness_classification"] == m375.BLOCKED_SPY_POSITION_ABSENT_OR_ZERO
    assert zero["spy_position_observed"] is True
    assert zero["spy_position_status"] == "absent_or_zero"


def test_profile_gate_fails_before_broker_construction() -> None:
    called = False

    def forbidden_factory():
        nonlocal called
        called = True
        raise AssertionError("broker should not be constructed")

    payload = m375.run_m375_spy_close_preview(
        paper_profile_gate_passed=False,
        paper_profile_gate_detail="paper_profile_required",
        broker_factory=forbidden_factory,
    )

    assert called is False
    assert payload["ok"] is False
    assert payload["readiness_classification"] == m375.BLOCKED_PROFILE_GATE_FAILED
    assert payload["submitted"] is False
    assert payload["mutated"] is False


def test_observation_unavailable_blocks_and_redacts_exception_message() -> None:
    broker = FakeM375Broker(account_exception=RuntimeError("secret-token failed"))

    payload = m375.run_m375_spy_close_preview(
        paper_profile_gate_passed=True,
        paper_profile_gate_detail="paper_profile_ready",
        broker_factory=lambda: broker,
        redactor=lambda value: value.replace("secret-token", "<redacted>"),
    )

    assert payload["ok"] is False
    assert (
        payload["readiness_classification"]
        == m375.BLOCKED_BROKER_OBSERVATION_UNAVAILABLE
    )
    assert payload["unavailable_observations"] == ["account"]
    reason = payload["unavailable_reasons"]["account"]
    assert reason["message"] == "<redacted> failed"
    assert "secret-token" not in m375.render_m375_spy_close_preview_json(payload)


def test_incomplete_order_query_metadata_blocks_as_ambiguous(monkeypatch) -> None:
    original = m375.recent_order_query_payload

    def incomplete_query_payload(query):
        payload = original(query)
        return {
            **payload,
            "recent_order_query_metadata_complete": False,
            "recent_order_query_metadata_missing_fields": [
                "recent_order_query_source",
            ],
        }

    monkeypatch.setattr(m375, "recent_order_query_payload", incomplete_query_payload)

    payload = _run(FakeM375Broker())

    assert payload["ok"] is False
    assert (
        payload["readiness_classification"]
        == m375.BLOCKED_AMBIGUOUS_BROKER_RESPONSE
    )
    assert payload["blockers"] == ["recent_order_query_source"]


def test_artifact_writer_appends_one_deterministic_jsonl_record(tmp_path) -> None:
    output_path = tmp_path / "runs" / "paper_lab" / "m375.jsonl"
    payload = _run(FakeM375Broker())

    result = m375.write_m375_spy_close_preview_artifact(payload, output_path)
    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]

    assert result["record_count"] == 1
    assert result["newline_terminated"] is True
    assert records == [json.loads(m375.render_m375_spy_close_preview_json(payload))]


def test_cli_writes_ready_artifact_with_fake_read_only_broker(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    import algotrader.cli as cli

    broker = FakeM375Broker()
    output_path = tmp_path / "m375_cli.jsonl"
    _configure_paper_env(monkeypatch)
    monkeypatch.setattr(cli, "_build_paper_broker", lambda paper_config: broker)

    exit_code = cli.main(
        (
            "--profile",
            "paper",
            "etf-sma-m375-spy-close-preview",
            "--run-log",
            str(output_path),
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]

    assert exit_code == 0
    assert captured.err == ""
    assert payload["readiness_classification"] == (
        m375.READY_FOR_SEPARATE_SPY_CLOSE_SUBMIT_MILESTONE
    )
    assert records == [payload]
    assert broker.calls == ["get_account", "get_positions", "get_recent_orders"]


def test_cli_profile_gate_failure_writes_blocked_artifact_without_broker(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    import algotrader.cli as cli

    output_path = tmp_path / "m375_blocked.jsonl"
    monkeypatch.delenv("APP_PROFILE", raising=False)
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.setattr(
        cli,
        "_build_paper_broker",
        lambda paper_config: (_ for _ in ()).throw(
            AssertionError("broker should not be constructed")
        ),
    )

    exit_code = cli.main(
        (
            "etf-sma-m375-spy-close-preview",
            "--run-log",
            str(output_path),
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 2
    assert captured.err == ""
    assert payload["readiness_classification"] == m375.BLOCKED_PROFILE_GATE_FAILED
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload


def test_m375_module_introduces_no_broker_mutation_calls() -> None:
    tree = ast.parse(Path(m375.__file__).read_text(encoding="utf-8"))
    forbidden = {
        "cancel_order",
        "close_all_positions",
        "close_position",
        "delete",
        "liquidate",
        "replace_order",
        "submit_order",
        "submit_order_request",
    }
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert call_names.isdisjoint(forbidden)


class FakeM375Broker:
    def __init__(
        self,
        *,
        positions=None,  # noqa: ANN001
        open_orders=(),  # noqa: ANN001
        account_exception: Exception | None = None,
        positions_exception: Exception | None = None,
        orders_exception: Exception | None = None,
    ) -> None:
        self.positions = (_position(),) if positions is None else tuple(positions)
        self.open_orders = tuple(open_orders)
        self.account_exception = account_exception
        self.positions_exception = positions_exception
        self.orders_exception = orders_exception
        self.calls: list[str] = []
        self.queries = []

    def get_account(self):
        self.calls.append("get_account")
        if self.account_exception is not None:
            raise self.account_exception
        return {
            "account_id": "paper-account-1",
            "buying_power": "1974.8",
            "cash": "1974.8",
            "currency": "USD",
            "equity": "1999.8",
            "status": "ACTIVE",
        }

    def get_positions(self):
        self.calls.append("get_positions")
        if self.positions_exception is not None:
            raise self.positions_exception
        return self.positions

    def get_recent_orders(self, query=None):
        self.calls.append("get_recent_orders")
        self.queries.append(query)
        if self.orders_exception is not None:
            raise self.orders_exception
        return self.open_orders


def _run(broker: FakeM375Broker) -> dict[str, object]:
    return m375.run_m375_spy_close_preview(
        paper_profile_gate_passed=True,
        paper_profile_gate_detail="paper_profile_ready",
        broker_factory=lambda: broker,
    )


def _position(
    *,
    symbol: str = "SPY",
    quantity: str = "0.033172072",
    average_price: str = "753.646",
) -> dict[str, str]:
    return {
        "average_price": average_price,
        "quantity": quantity,
        "symbol": symbol,
    }


def _order(client_order_id: str, *, symbol: str = "SPY") -> dict[str, str]:
    return {
        "asset_class": "equity",
        "client_order_id": client_order_id,
        "filled_at": "",
        "normalized_status": "accepted",
        "notional": "",
        "order_id": f"broker-{client_order_id}",
        "order_type": "market",
        "quantity": "0.033172072",
        "raw_status": "accepted",
        "side": "sell",
        "submitted_at": "2026-06-03T16:42:36.996386+00:00",
        "symbol": symbol,
        "time_in_force": "day",
    }


def _configure_paper_env(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "m375-api-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "m375-secret-key")


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""
