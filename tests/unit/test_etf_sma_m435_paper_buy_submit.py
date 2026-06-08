from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

from algotrader.execution.alpaca_mapper import (
    AlpacaOrderReason,
    AlpacaOrderReceiptExecution,
)
from algotrader.execution.broker_base import BrokerOrderResult
import algotrader.execution.etf_sma_m435_paper_buy_submit as m435


MODULE_PATH = Path("src/algotrader/execution/etf_sma_m435_paper_buy_submit.py")
SENSITIVE_API_KEY = "m435-sensitive-api-key"
SENSITIVE_SECRET_KEY = "m435-sensitive-secret-key"
AS_OF = "2026-06-02T14:04:00+00:00"
SESSION_OBSERVED_AT = "2026-06-02T10:00:00-04:00"
RECONCILIATION_OBSERVED_AT = "2026-06-02T14:02:00+00:00"


def test_fails_closed_without_exact_operator_approval(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    factory_calls: list[str] = []

    payload = _run(
        tmp_path,
        source_path=source_path,
        operator_approval="APPROVE",
        broker_factory=lambda: factory_calls.append("called"),
    )

    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["submit_call_count"] == 0
    assert "operator_approval_gate_failed" in payload["blockers"]
    assert factory_calls == []


def test_fails_closed_when_m434_approval_packet_is_not_ready(tmp_path) -> None:
    source_path = _write_source(
        tmp_path,
        _record_with(("approval_decision",), "blocked_m433_not_ready"),
    )

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert "m434_approval_decision_invalid" in payload["blockers"]


def test_fails_closed_when_m434_source_contains_blockers(tmp_path) -> None:
    source_path = _write_source(
        tmp_path,
        _record_with(("blockers",), ["source_m433_blockers_present"]),
    )

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m434_blockers_present" in payload["blockers"]


def test_fails_closed_when_m434_source_records_prior_mutation(tmp_path) -> None:
    record = _record_with(("submitted",), True)
    record["mutated"] = True
    record["broker_action_performed"] = True
    source_path = _write_source(tmp_path, record)

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m434_submitted_not_false" in payload["blockers"]
    assert "m434_mutated_not_false" in payload["blockers"]
    assert "m434_broker_action_performed_not_false" in payload["blockers"]


def test_fails_closed_when_market_session_is_unavailable_or_closed(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    for status in ("unavailable", "closed"):
        broker = FakeM435Broker()
        factory_calls: list[str] = []

        payload = _run(
            tmp_path,
            source_path=source_path,
            broker_factory=lambda broker=broker: factory_calls.append("called")
            or broker,
            session=m435.M435EquitySessionStatus(
                status=status,
                source="unit_test_market_clock",
                observed_at=SESSION_OBSERVED_AT,
            ),
        )

        assert payload["submitted"] is False
        assert payload["mutated"] is False
        assert payload["ok"] is False
        assert broker.submit_count == 0
        assert broker.calls == []
        assert factory_calls == []
        assert "market_session_not_open" in payload["blockers"]


def test_fails_closed_when_evaluated_at_is_invalid_before_broker_construction(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    factory_calls: list[str] = []

    payload = _run(
        tmp_path,
        source_path=source_path,
        evaluated_at="not-a-timestamp",
        broker_factory=lambda: factory_calls.append("called") or FakeM435Broker(),
    )

    assert payload["submitted"] is False
    assert "evaluation_clock_invalid" in payload["blockers"]
    assert factory_calls == []


def test_fails_closed_when_fresh_reconciliation_has_any_position(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    broker = FakeM435Broker(positions=(_position("SPY", "0.05"),))

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "fresh_position_count_not_zero" in payload["blockers"]
    assert "fresh_spy_position_not_absent_or_zero" in payload["blockers"]


def test_fails_closed_when_fresh_reconciliation_has_open_orders(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    broker = FakeM435Broker(open_orders=(_order("other-open-order"),))

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "fresh_open_orders_present" in payload["blockers"]


def test_fails_closed_when_duplicate_client_order_id_exists(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    broker = FakeM435Broker(recent_orders=(_order(m435.M435_CLIENT_ORDER_ID),))

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "fresh_duplicate_m435_client_order_id_found" in payload["blockers"]


def test_fails_closed_when_cash_is_insufficient(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    broker = FakeM435Broker(cash="24.99")

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "fresh_cash_insufficient_for_25_notional" in payload["blockers"]


def test_succeeds_with_fake_broker_by_calling_submit_exactly_once(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    broker = FakeM435Broker(
        post_open_orders=(_order(m435.M435_CLIENT_ORDER_ID, status="accepted"),),
        post_recent_orders=(_order(m435.M435_CLIENT_ORDER_ID, status="accepted"),),
    )

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["ok"] is True
    assert payload["submitted"] is True
    assert payload["mutated"] is True
    assert payload["broker_action_performed"] is True
    assert payload["submit_call_count"] == 1
    assert payload["broker_order_id"] == "broker-m435-order-1"
    assert payload["broker_status"] == "accepted"
    assert payload["client_order_id"] == m435.M435_CLIENT_ORDER_ID
    assert payload["evaluated_at"] == AS_OF
    assert payload["pre_submit_reconciliation"]["observed_at"] == (
        RECONCILIATION_OBSERVED_AT
    )
    assert payload["post_submit_reconciliation"]["observed_at"] == (
        RECONCILIATION_OBSERVED_AT
    )
    assert payload["post_submit_matching_order_found"] is True
    assert broker.calls == [
        "get_account",
        "get_positions",
        "get_orders",
        "get_orders",
        "submit_order",
        "get_account",
        "get_positions",
        "get_orders",
        "get_orders",
    ]
    assert len(broker.submitted_requests) == 1
    request = broker.submitted_requests[0]
    assert request.symbol == "SPY"
    assert request.side == "buy"
    assert request.asset_class == "equity"
    assert request.order_type == "market"
    assert request.time_in_force == "day"
    assert request.notional == Decimal("25.00")
    assert request.qty is None


def test_ambiguous_submit_exception_sets_submitted_mutated_and_no_retry(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    broker = FakeM435Broker(
        submit_exception=RuntimeError(f"ambiguous {SENSITIVE_SECRET_KEY}"),
    )

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        redactor=lambda value: value.replace(SENSITIVE_SECRET_KEY, "<redacted>"),
    )

    assert payload["ok"] is False
    assert payload["submitted"] is True
    assert payload["mutated"] is True
    assert payload["broker_error"] is True
    assert payload["broker_action_performed"] is True
    assert payload["submit_call_count"] == 1
    assert payload["error"] == "m435_submit_ambiguous_after_single_call"
    assert payload["state"] == "ambiguous_after_single_submit_stop_no_retry"
    assert payload["redacted_exception_message"] == "ambiguous <redacted>"
    assert payload["post_submit_reconciliation"]["read_only_broker_observation"] is True
    assert broker.submit_count == 1
    assert broker.calls.count("submit_order") == 1


def test_does_not_call_submit_order_when_prior_m435_submit_exists(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    output_path = tmp_path / "m435.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "client_order_id": m435.M435_CLIENT_ORDER_ID,
                "submitted": True,
                "submit_call_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    broker = FakeM435Broker()

    payload = m435.run_m435_tiny_spy_paper_buy_submit(
        source_m434_artifact_path=source_path,
        output_artifact_path=output_path,
        run_id=m435.M435_DEFAULT_RUN_ID,
        operator_approval=m435.M435_APPROVAL_PHRASE,
        equity_session_status=_open_session(),
        paper_profile_gate_passed=True,
        evaluated_at=AS_OF,
        paper_profile_gate_detail="paper_profile_ready",
        broker_factory=lambda: broker,
    )

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "m435_prior_submit_or_submit_call_detected" in payload["blockers"]


def test_artifact_redacts_credentials_and_approval_phrase(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    broker = FakeM435Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        redactor=lambda value: value.replace(SENSITIVE_SECRET_KEY, "<redacted>"),
    )
    rendered = m435.render_m435_paper_buy_submit_json(payload)

    assert payload["credentials_redacted"] is True
    assert payload["profit_claim"] == "none"
    assert "not_live_authorized" in payload["labels"]
    assert m435.M435_APPROVAL_PHRASE not in rendered
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_write_artifact_appends_one_jsonl_record(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m434_record())
    broker = FakeM435Broker()
    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)
    output_path = tmp_path / "runs" / "paper_lab" / "m435.jsonl"

    result = m435.write_m435_paper_buy_submit_artifact(payload, output_path)

    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert result["record_count"] == 1
    assert result["newline_terminated"] is True
    assert records == [payload]


def test_cli_m435_submit_path_reaches_fake_submit_gate(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    import algotrader.cli as cli

    source_path = _write_source(tmp_path, _ready_m434_record())
    output_path = tmp_path / "m435-cli-valid.jsonl"
    broker = FakeM435Broker(
        post_open_orders=(_order(m435.M435_CLIENT_ORDER_ID, status="accepted"),),
        post_recent_orders=(_order(m435.M435_CLIENT_ORDER_ID, status="accepted"),),
    )
    _configure_paper_cli_env(monkeypatch)
    monkeypatch.setattr(cli, "_build_paper_broker", lambda paper_config: broker)
    monkeypatch.setattr(
        m435,
        "_system_utc_now",
        lambda: datetime(2026, 6, 2, 14, 2, tzinfo=timezone.utc),
    )

    exit_code = cli.main(
        (
            "etf-sma-m435-paper-buy-submit",
            "--source-m434-artifact",
            str(source_path),
            "--operator-approval",
            m435.M435_APPROVAL_PHRASE,
            "--equity-session-status",
            "open",
            "--equity-session-source",
            "unit_test_market_clock",
            "--equity-session-observed-at",
            "2026-06-02T10:00:00-04:00",
            "--evaluated-at",
            AS_OF,
            "--run-log",
            str(output_path),
            "--format",
            "json",
        )
    )

    rendered = capsys.readouterr().out
    payload = json.loads(rendered)
    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["submitted"] is True
    assert payload["mutated"] is True
    assert payload["submit_call_count"] == 1
    assert broker.submit_count == 1
    assert records == [payload]
    assert m435.M435_APPROVAL_PHRASE not in rendered
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_m435_module_introduces_no_disallowed_broker_mutation_calls() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden = {
        "cancel_order",
        "replace_order",
        "close_position",
        "close_all_positions",
        "liquidate",
        "liquidation",
        "delete",
    }
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert call_names.isdisjoint(forbidden)


class FakeM435Broker:
    def __init__(
        self,
        *,
        cash: str = "1999.81",
        currency: str = "USD",
        positions=(),  # noqa: ANN001
        open_orders=(),  # noqa: ANN001
        recent_orders=(),  # noqa: ANN001
        post_open_orders=(),  # noqa: ANN001
        post_recent_orders=(),  # noqa: ANN001
        result: BrokerOrderResult | None = None,
        submit_exception: Exception | None = None,
    ) -> None:
        self.cash = cash
        self.currency = currency
        self.positions = tuple(positions)
        self.open_orders = tuple(open_orders)
        self.recent_orders = tuple(recent_orders)
        self.post_open_orders = tuple(post_open_orders)
        self.post_recent_orders = tuple(post_recent_orders)
        self.result = result or _accepted_result()
        self.submit_exception = submit_exception
        self.calls: list[str] = []
        self.submitted_requests = []
        self.submit_count = 0

    def get_account(self):
        self.calls.append("get_account")
        return {
            "account_id": "fake-account",
            "buying_power": self.cash,
            "cash": self.cash,
            "currency": self.currency,
            "equity": self.cash,
            "status": "ACTIVE",
        }

    def get_positions(self):
        self.calls.append("get_positions")
        return self.positions

    def get_recent_orders(self, query=None):
        self.calls.append("get_orders")
        status_filter = getattr(query, "status_filter", "open")
        if status_filter == "open":
            return self.post_open_orders if self.submit_count else self.open_orders
        return self.post_recent_orders if self.submit_count else self.recent_orders

    def submit_order_request(self, request, risk_verdict=None):
        self.calls.append("submit_order")
        self.submit_count += 1
        self.submitted_requests.append(request)
        assert risk_verdict is not None
        assert risk_verdict.allowed is True
        if self.submit_exception is not None:
            raise self.submit_exception
        return self.result


def _run(
    tmp_path,
    *,
    source_path,
    operator_approval: str = m435.M435_APPROVAL_PHRASE,
    broker_factory,
    session: m435.M435EquitySessionStatus | None = None,
    evaluated_at: str = AS_OF,
    pre_submit_reconciliation_observed_at: str = RECONCILIATION_OBSERVED_AT,
    redactor=lambda value: value,
) -> dict[str, object]:
    return m435.run_m435_tiny_spy_paper_buy_submit(
        source_m434_artifact_path=source_path,
        output_artifact_path=tmp_path / "m435-output.jsonl",
        run_id=m435.M435_DEFAULT_RUN_ID,
        operator_approval=operator_approval,
        equity_session_status=session or _open_session(),
        paper_profile_gate_passed=True,
        evaluated_at=evaluated_at,
        pre_submit_reconciliation_observed_at=pre_submit_reconciliation_observed_at,
        paper_profile_gate_detail="paper_profile_ready",
        halt_gate_passed=True,
        halt_gate_detail="halt_not_set",
        reconciliation_clock=lambda: pre_submit_reconciliation_observed_at,
        broker_factory=broker_factory,
        redactor=redactor,
    )


def _open_session() -> m435.M435EquitySessionStatus:
    return m435.M435EquitySessionStatus(
        status="open",
        source="unit_test_market_clock",
        observed_at=SESSION_OBSERVED_AT,
    )


def _forbidden_factory():
    raise AssertionError("broker must not be built")


def _configure_paper_cli_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_API_KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SENSITIVE_SECRET_KEY)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper.example.test")
    monkeypatch.delenv("ALGOTRADER_PAPER_HALT", raising=False)


def _write_source(tmp_path, record: dict[str, object]) -> Path:
    path = tmp_path / "m434.jsonl"
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _ready_m434_record() -> dict[str, object]:
    return {
        "approval_decision": "ready_for_explicit_operator_authorization",
        "approval_scope": "offline_paper_buy_submit_approval_packet",
        "asset_class": "equity",
        "blockers": [],
        "broker_action_performed": False,
        "broker_read_only": False,
        "command": "etf-sma-m434-offline-buy-submit-approval-packet",
        "credential_access_attempted": False,
        "intended_order_type": "market",
        "intended_time_in_force": "day",
        "labels": [
            "paper_lab_only",
            "offline_paper_buy_submit_approval_packet",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "live_authorized": False,
        "milestone": "M434",
        "mutated": False,
        "network_access_attempted": False,
        "next_required_milestone": "M435_operator_authorized_tiny_spy_paper_buy_submit",
        "operator_approval_required": True,
        "paper_lab_only": True,
        "paper_only": True,
        "profit_claim": "none",
        "record_type": "etf_sma_m434_offline_paper_buy_submit_approval_packet",
        "required_single_attempt_submit": True,
        "run_id": "m434_offline_paper_buy_submit_approval_packet",
        "schema_version": "1",
        "side": "buy",
        "source_m433_artifact": "runs/paper_lab/m433_offline_operator_review_packet.jsonl",
        "source_m433_readiness_decision": (
            "ready_for_separate_operator_authorized_paper_buy_submit_milestone"
        ),
        "submit_authorized": False,
        "submitted": False,
        "symbol": "SPY",
        "trade_recommendation": "none",
    }


def _record_with(path: tuple[str, ...], value: object) -> dict[str, object]:
    record = deepcopy(_ready_m434_record())
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return record


def _position(symbol: str, quantity: str) -> dict[str, str]:
    return {
        "average_price": "500",
        "quantity": quantity,
        "symbol": symbol,
    }


def _order(client_order_id: str, *, status: str = "open") -> dict[str, str]:
    return {
        "asset_class": "equity",
        "client_order_id": client_order_id,
        "filled_at": "",
        "normalized_status": status,
        "notional": "25.00",
        "order_id": f"broker-{client_order_id}",
        "order_type": "market",
        "quantity": "",
        "raw_status": status,
        "side": "buy",
        "submitted_at": "2026-06-02T10:01:00-04:00",
        "symbol": "SPY",
        "time_in_force": "day",
    }


def _accepted_result() -> BrokerOrderResult:
    return BrokerOrderResult(
        accepted=True,
        execution=AlpacaOrderReceiptExecution(filled=False),
        reason=AlpacaOrderReason(
            "",
            client_order_id=m435.M435_CLIENT_ORDER_ID,
            filled_average_price="",
            filled_quantity="",
            normalized_status="accepted",
            order_id="broker-m435-order-1",
            quantity="",
            raw_reason="",
            raw_status="accepted",
        ),
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
