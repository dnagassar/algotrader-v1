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
import algotrader.execution.etf_sma_m370_paper_submit as m370


MODULE_PATH = Path("src/algotrader/execution/etf_sma_m370_paper_submit.py")
SENSITIVE_API_KEY = "m370-sensitive-api-key"
SENSITIVE_SECRET_KEY = "m370-sensitive-secret-key"
AS_OF = "2026-06-02T14:04:00+00:00"
SESSION_OBSERVED_AT = "2026-06-02T10:00:00-04:00"
SNAPSHOT_OBSERVED_AT = "2026-06-02T14:02:00+00:00"


def test_fails_closed_without_exact_operator_approval(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    factory_calls: list[str] = []

    payload = _run(
        tmp_path,
        source_path=source_path,
        operator_approval="APPROVE",
        broker_factory=lambda: factory_calls.append("called"),
    )

    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["submit_call_count"] == 0
    assert "operator_approval_gate_failed" in payload["blockers"]
    assert factory_calls == []


def test_fails_closed_when_m369_decision_is_not_ready(tmp_path) -> None:
    record = _record_with(("decision",), "blocked")
    source_path = _write_source(tmp_path, record)

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m369_decision_not_ready" in payload["blockers"]


def test_fails_closed_when_m369_blockers_exist(tmp_path) -> None:
    source_path = _write_source(tmp_path, _record_with(("blockers",), ["stale"]))

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m369_blockers_present" in payload["blockers"]


def test_fails_closed_when_source_preview_is_not_spy(tmp_path) -> None:
    source_path = _write_source(
        tmp_path,
        _record_with(("proposed_order", "symbol"), "IVV"),
    )

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m369_proposed_order_symbol_invalid" in payload["blockers"]


def test_fails_closed_when_source_preview_is_sell(tmp_path) -> None:
    source_path = _write_source(
        tmp_path,
        _record_with(("proposed_order", "side"), "sell"),
    )

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m369_proposed_order_side_invalid" in payload["blockers"]


def test_fails_closed_when_source_notional_cap_exceeds_25(tmp_path) -> None:
    source_path = _write_source(
        tmp_path,
        _record_with(("proposed_order", "notional"), "25.01"),
    )

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m369_proposed_order_notional_above_25" in payload["blockers"]


def test_fails_closed_when_source_snapshot_is_not_flat(tmp_path) -> None:
    record = _record_with(("snapshot_summary", "position_count"), 1)
    record["snapshot_summary"]["position_symbols"] = ["SPY"]
    source_path = _write_source(tmp_path, record)

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m369_snapshot_position_count_not_zero" in payload["blockers"]
    assert "m369_snapshot_position_symbols_present" in payload["blockers"]


def test_fails_closed_when_source_evidence_is_already_submitted_or_mutated(tmp_path) -> None:
    record = _record_with(("submitted",), True)
    record["mutated"] = True
    source_path = _write_source(tmp_path, record)

    payload = _run(tmp_path, source_path=source_path, broker_factory=_forbidden_factory)

    assert payload["submitted"] is False
    assert "m369_submitted_not_false" in payload["blockers"]
    assert "m369_mutated_not_false" in payload["blockers"]


def test_fails_closed_when_fresh_snapshot_has_any_position(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker(positions=(_position("SPY", "0.05"),))

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "fresh_position_count_not_zero" in payload["blockers"]
    assert "fresh_spy_position_not_absent_or_zero" in payload["blockers"]


def test_fails_closed_when_fresh_snapshot_has_open_orders(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker(open_orders=(_order("other-open-order"),))

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "fresh_open_orders_present" in payload["blockers"]


def test_fails_closed_when_cash_is_insufficient(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker(cash="24.99")

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "fresh_cash_insufficient_for_25_notional" in payload["blockers"]


def test_fails_closed_when_market_session_is_unavailable_or_closed(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    for status in ("unavailable", "closed"):
        broker = FakeM370Broker()
        factory_calls: list[str] = []

        payload = _run(
            tmp_path,
            source_path=source_path,
            broker_factory=lambda broker=broker: factory_calls.append("called") or broker,
            session=m370.M370EquitySessionStatus(
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
    source_path = _write_source(tmp_path, _ready_m369_record())
    factory_calls: list[str] = []

    payload = _run(
        tmp_path,
        source_path=source_path,
        evaluated_at="not-a-timestamp",
        broker_factory=lambda: factory_calls.append("called") or FakeM370Broker(),
    )

    _assert_freshness_blocked(payload, "evaluation_clock_invalid")
    assert factory_calls == []


def test_fails_closed_when_evaluated_at_is_timezone_naive_before_broker_construction(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    factory_calls: list[str] = []

    payload = _run(
        tmp_path,
        source_path=source_path,
        evaluated_at="2026-06-02T14:04:00",
        broker_factory=lambda: factory_calls.append("called") or FakeM370Broker(),
    )

    _assert_freshness_blocked(payload, "evaluation_clock_timezone_naive")
    assert factory_calls == []


def test_fails_closed_when_market_session_observed_at_is_missing(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()
    factory_calls: list[str] = []

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: factory_calls.append("called") or broker,
        session=m370.M370EquitySessionStatus(
            status="open",
            source="unit_test_market_clock",
        ),
    )

    _assert_freshness_blocked(payload, "market_session_observed_at_missing")
    assert broker.calls == []
    assert factory_calls == []


def test_fails_closed_when_market_session_observed_at_is_timezone_naive(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        session=m370.M370EquitySessionStatus(
            status="open",
            source="unit_test_market_clock",
            observed_at="2026-06-02T10:00:00",
        ),
    )

    _assert_freshness_blocked(
        payload,
        "market_session_observed_at_timezone_naive",
    )
    assert broker.calls == []


def test_fails_closed_when_market_session_observed_at_is_invalid_before_broker_construction(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    factory_calls: list[str] = []

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: factory_calls.append("called") or FakeM370Broker(),
        session=m370.M370EquitySessionStatus(
            status="open",
            source="unit_test_market_clock",
            observed_at="not-a-timestamp",
        ),
    )

    _assert_freshness_blocked(payload, "market_session_observed_at_invalid")
    assert factory_calls == []


def test_fails_closed_when_market_session_observed_at_is_stale(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        session=m370.M370EquitySessionStatus(
            status="open",
            source="unit_test_market_clock",
            observed_at="2026-06-02T13:48:59+00:00",
        ),
    )

    _assert_freshness_blocked(payload, "market_session_status_stale")
    assert broker.calls == []


def test_fails_closed_when_market_session_observed_at_is_future_dated(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        session=m370.M370EquitySessionStatus(
            status="open",
            source="unit_test_market_clock",
            observed_at="2026-06-02T14:05:01+00:00",
        ),
    )

    _assert_freshness_blocked(payload, "market_session_status_future_dated")
    assert broker.calls == []


def test_fails_closed_when_pre_submit_snapshot_observed_at_is_missing(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        pre_submit_snapshot_observed_at="",
    )

    _assert_freshness_blocked(payload, "pre_submit_snapshot_observed_at_missing")
    assert broker.submit_count == 0
    assert "submit_order" not in broker.calls


def test_fails_closed_when_pre_submit_snapshot_observed_at_is_timezone_naive(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        pre_submit_snapshot_observed_at="2026-06-02T14:02:00",
    )

    _assert_freshness_blocked(
        payload,
        "pre_submit_snapshot_observed_at_timezone_naive",
    )
    assert broker.submit_count == 0
    assert "submit_order" not in broker.calls


def test_fails_closed_when_pre_submit_snapshot_observed_at_is_invalid_before_submit(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()
    factory_calls: list[str] = []

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: factory_calls.append("called") or broker,
        pre_submit_snapshot_observed_at="not-a-timestamp",
    )

    _assert_freshness_blocked(payload, "pre_submit_snapshot_observed_at_invalid")
    assert factory_calls == ["called"]
    assert broker.submit_count == 0
    assert "submit_order" not in broker.calls


def test_fails_closed_when_pre_submit_snapshot_observed_at_is_stale(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        pre_submit_snapshot_observed_at="2026-06-02T13:58:59+00:00",
    )

    _assert_freshness_blocked(payload, "pre_submit_snapshot_stale")
    assert broker.submit_count == 0
    assert "submit_order" not in broker.calls


def test_fails_closed_when_pre_submit_snapshot_observed_at_is_future_dated(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        pre_submit_snapshot_observed_at="2026-06-02T14:05:01+00:00",
    )

    _assert_freshness_blocked(payload, "pre_submit_snapshot_future_dated")
    assert broker.submit_count == 0
    assert "submit_order" not in broker.calls


def test_command_owned_pre_submit_observed_at_cannot_be_masked_by_explicit_timestamp(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()
    command_owned_observed_at = "2026-06-02T13:58:59+00:00"

    payload = m370.run_m370_tiny_spy_paper_submit(
        source_m369_artifact_path=source_path,
        output_artifact_path=tmp_path / "m370-command-owned-stale.jsonl",
        run_id=m370.M370_DEFAULT_RUN_ID,
        operator_approval=m370.M370_APPROVAL_PHRASE,
        equity_session_status=_open_session(),
        paper_profile_gate_passed=True,
        evaluated_at=AS_OF,
        pre_submit_snapshot_observed_at=SNAPSHOT_OBSERVED_AT,
        paper_profile_gate_detail="paper_profile_ready",
        halt_gate_passed=True,
        halt_gate_detail="halt_not_set",
        snapshot_clock=lambda: command_owned_observed_at,
        broker_factory=lambda: broker,
    )

    _assert_freshness_blocked(payload, "pre_submit_snapshot_stale")
    assert payload["pre_submit_snapshot"]["observed_at"] == command_owned_observed_at
    assert broker.submit_count == 0
    assert "submit_order" not in broker.calls


def test_explicit_pre_submit_observed_at_is_validated_without_overriding_snapshot(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = m370.run_m370_tiny_spy_paper_submit(
        source_m369_artifact_path=source_path,
        output_artifact_path=tmp_path / "m370-explicit-naive.jsonl",
        run_id=m370.M370_DEFAULT_RUN_ID,
        operator_approval=m370.M370_APPROVAL_PHRASE,
        equity_session_status=_open_session(),
        paper_profile_gate_passed=True,
        evaluated_at=AS_OF,
        pre_submit_snapshot_observed_at="2026-06-02T14:02:00",
        paper_profile_gate_detail="paper_profile_ready",
        halt_gate_passed=True,
        halt_gate_detail="halt_not_set",
        snapshot_clock=lambda: SNAPSHOT_OBSERVED_AT,
        broker_factory=lambda: broker,
    )

    _assert_freshness_blocked(
        payload,
        "pre_submit_snapshot_observed_at_timezone_naive",
    )
    assert payload["pre_submit_snapshot"]["observed_at"] == SNAPSHOT_OBSERVED_AT
    assert broker.submit_count == 0
    assert "submit_order" not in broker.calls


def test_succeeds_with_fake_broker_by_calling_submit_exactly_once(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker(
        post_open_orders=(_order(m370.M370_CLIENT_ORDER_ID, status="accepted"),),
        post_recent_orders=(_order(m370.M370_CLIENT_ORDER_ID, status="accepted"),),
    )

    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    assert payload["ok"] is True
    assert payload["submitted"] is True
    assert payload["mutated"] is True
    assert payload["submit_call_count"] == 1
    assert payload["broker_order_id"] == "broker-m370-order-1"
    assert payload["broker_status"] == "accepted"
    assert payload["client_order_id"] == m370.M370_CLIENT_ORDER_ID
    assert payload["evaluated_at"] == AS_OF
    assert payload["pre_submit_snapshot"]["observed_at"] == SNAPSHOT_OBSERVED_AT
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


def test_render_text_includes_utc_normalized_timestamp_evidence(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()
    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)

    rendered = m370.render_m370_paper_submit_text(payload)

    assert f"evaluated_at: {AS_OF}" in rendered
    assert "market_session_observed_at: 2026-06-02T14:00:00+00:00" in rendered
    assert f"pre_submit_snapshot_observed_at: {SNAPSHOT_OBSERVED_AT}" in rendered


def test_ambiguous_submit_exception_sets_submitted_mutated_and_no_retry(
    tmp_path,
) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker(
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
    assert payload["submit_call_count"] == 1
    assert payload["error"] == "m370_submit_ambiguous_after_single_call"
    assert payload["state"] == "ambiguous_after_single_submit_stop_no_retry"
    assert payload["redacted_exception_message"] == "ambiguous <redacted>"
    assert broker.submit_count == 1
    assert broker.calls.count("submit_order") == 1


def test_does_not_call_submit_order_when_prior_m370_submit_exists(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    output_path = tmp_path / "m370.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "client_order_id": m370.M370_CLIENT_ORDER_ID,
                "submitted": True,
                "submit_call_count": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    broker = FakeM370Broker()

    payload = m370.run_m370_tiny_spy_paper_submit(
        source_m369_artifact_path=source_path,
        output_artifact_path=output_path,
        run_id=m370.M370_DEFAULT_RUN_ID,
        operator_approval=m370.M370_APPROVAL_PHRASE,
        equity_session_status=_open_session(),
        paper_profile_gate_passed=True,
        evaluated_at=AS_OF,
        pre_submit_snapshot_observed_at=SNAPSHOT_OBSERVED_AT,
        paper_profile_gate_detail="paper_profile_ready",
        broker_factory=lambda: broker,
    )

    assert payload["submitted"] is False
    assert broker.submit_count == 0
    assert "m370_prior_submit_or_submit_call_detected" in payload["blockers"]


def test_artifact_redacts_credentials_and_approval_phrase(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()

    payload = _run(
        tmp_path,
        source_path=source_path,
        broker_factory=lambda: broker,
        redactor=lambda value: value.replace(SENSITIVE_SECRET_KEY, "<redacted>"),
    )
    rendered = m370.render_m370_paper_submit_json(payload)

    assert payload["credentials_redacted"] is True
    assert payload["profit_claim"] == "none"
    assert "not_live_authorized" in payload["labels"]
    assert m370.M370_APPROVAL_PHRASE not in rendered
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_write_artifact_appends_one_jsonl_record(tmp_path) -> None:
    source_path = _write_source(tmp_path, _ready_m369_record())
    broker = FakeM370Broker()
    payload = _run(tmp_path, source_path=source_path, broker_factory=lambda: broker)
    output_path = tmp_path / "runs" / "paper_lab" / "m370.jsonl"

    result = m370.write_m370_paper_submit_artifact(payload, output_path)

    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert result["record_count"] == 1
    assert result["newline_terminated"] is True
    assert records == [payload]


def test_cli_m370_submit_path_fails_closed_without_evaluation_clock_and_redacts(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    import algotrader.cli as cli

    source_path = _write_source(tmp_path, _ready_m369_record())
    output_path = tmp_path / "m370-cli.jsonl"
    broker = FakeM370Broker()
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_API_KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SENSITIVE_SECRET_KEY)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper.example.test")
    monkeypatch.delenv("ALGOTRADER_PAPER_HALT", raising=False)
    factory_calls: list[str] = []
    monkeypatch.setattr(
        cli,
        "_build_paper_broker",
        lambda paper_config: factory_calls.append("called") or broker,
    )

    exit_code = cli.main(
        (
            "etf-sma-m370-paper-submit",
            "--source-m369-artifact",
            str(source_path),
            "--operator-approval",
            m370.M370_APPROVAL_PHRASE,
            "--equity-session-status",
            "open",
            "--equity-session-source",
            "unit_test_market_clock",
            "--equity-session-observed-at",
            "2026-06-02T10:00:00-04:00",
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
    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert "evaluation_clock_missing" in payload["blockers"]
    assert broker.submit_count == 0
    assert broker.calls == []
    assert factory_calls == []
    assert records == [payload]
    assert m370.M370_APPROVAL_PHRASE not in rendered
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_cli_m370_submit_path_fails_closed_with_invalid_evaluation_clock_before_broker_construction(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    import algotrader.cli as cli

    source_path = _write_source(tmp_path, _ready_m369_record())
    output_path = tmp_path / "m370-cli-invalid.jsonl"
    broker = FakeM370Broker()
    factory_calls: list[str] = []
    _configure_paper_cli_env(monkeypatch)
    monkeypatch.setattr(
        cli,
        "_build_paper_broker",
        lambda paper_config: factory_calls.append("called") or broker,
    )

    exit_code = cli.main(
        _m370_cli_args(
            source_path=source_path,
            output_path=output_path,
            evaluated_at="not-a-timestamp",
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["submit_call_count"] == 0
    assert "evaluation_clock_invalid" in payload["blockers"]
    assert broker.calls == []
    assert factory_calls == []


def test_cli_m370_submit_path_fails_closed_with_naive_evaluation_clock_before_broker_construction(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    import algotrader.cli as cli

    source_path = _write_source(tmp_path, _ready_m369_record())
    output_path = tmp_path / "m370-cli-naive.jsonl"
    broker = FakeM370Broker()
    factory_calls: list[str] = []
    _configure_paper_cli_env(monkeypatch)
    monkeypatch.setattr(
        cli,
        "_build_paper_broker",
        lambda paper_config: factory_calls.append("called") or broker,
    )

    exit_code = cli.main(
        _m370_cli_args(
            source_path=source_path,
            output_path=output_path,
            evaluated_at="2026-06-02T14:04:00",
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["submit_call_count"] == 0
    assert "evaluation_clock_timezone_naive" in payload["blockers"]
    assert broker.calls == []
    assert factory_calls == []


def test_cli_m370_submit_path_accepts_evaluated_at_and_reaches_fake_submit_gate(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    import algotrader.cli as cli

    source_path = _write_source(tmp_path, _ready_m369_record())
    output_path = tmp_path / "m370-cli-valid.jsonl"
    broker = FakeM370Broker(
        post_open_orders=(_order(m370.M370_CLIENT_ORDER_ID, status="accepted"),),
        post_recent_orders=(_order(m370.M370_CLIENT_ORDER_ID, status="accepted"),),
    )
    _configure_paper_cli_env(monkeypatch)
    monkeypatch.setattr(cli, "_build_paper_broker", lambda paper_config: broker)
    monkeypatch.setattr(
        m370,
        "_system_utc_now",
        lambda: datetime(2026, 6, 2, 14, 2, tzinfo=timezone.utc),
    )

    exit_code = cli.main(
        _m370_cli_args(
            source_path=source_path,
            output_path=output_path,
            evaluated_at=AS_OF,
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
    assert payload["evaluated_at"] == AS_OF
    assert payload["market_session"]["observed_at"] == SESSION_OBSERVED_AT
    assert payload["pre_submit_snapshot"]["observed_at"] == SNAPSHOT_OBSERVED_AT
    assert "evaluation_clock_missing" not in payload["blockers"]
    assert "evaluation_clock_invalid" not in payload["blockers"]
    assert "evaluation_clock_timezone_naive" not in payload["blockers"]
    assert broker.submit_count == 1
    assert records == [payload]


def test_m370_module_introduces_no_disallowed_broker_mutation_calls() -> None:
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


class FakeM370Broker:
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
    operator_approval: str = m370.M370_APPROVAL_PHRASE,
    broker_factory,
    session: m370.M370EquitySessionStatus | None = None,
    evaluated_at: str = AS_OF,
    pre_submit_snapshot_observed_at: str = SNAPSHOT_OBSERVED_AT,
    redactor=lambda value: value,
) -> dict[str, object]:
    return m370.run_m370_tiny_spy_paper_submit(
        source_m369_artifact_path=source_path,
        output_artifact_path=tmp_path / "m370-output.jsonl",
        run_id=m370.M370_DEFAULT_RUN_ID,
        operator_approval=operator_approval,
        equity_session_status=session or _open_session(),
        paper_profile_gate_passed=True,
        evaluated_at=evaluated_at,
        paper_profile_gate_detail="paper_profile_ready",
        halt_gate_passed=True,
        halt_gate_detail="halt_not_set",
        snapshot_clock=lambda: pre_submit_snapshot_observed_at,
        broker_factory=broker_factory,
        redactor=redactor,
    )


def _assert_freshness_blocked(payload: dict[str, object], blocker: str) -> None:
    assert payload["ok"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["submit_call_count"] == 0
    assert blocker in payload["blockers"]


def _open_session() -> m370.M370EquitySessionStatus:
    return m370.M370EquitySessionStatus(
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


def _m370_cli_args(
    *,
    source_path: Path,
    output_path: Path,
    evaluated_at: str | None = None,
) -> tuple[str, ...]:
    args = [
        "etf-sma-m370-paper-submit",
        "--source-m369-artifact",
        str(source_path),
        "--operator-approval",
        m370.M370_APPROVAL_PHRASE,
        "--equity-session-status",
        "open",
        "--equity-session-source",
        "unit_test_market_clock",
        "--equity-session-observed-at",
        "2026-06-02T10:00:00-04:00",
        "--run-log",
        str(output_path),
        "--format",
        "json",
    ]
    if evaluated_at is not None:
        args.extend(("--evaluated-at", evaluated_at))
    return tuple(args)


def _write_source(tmp_path, record: dict[str, object]) -> Path:
    path = tmp_path / "m369.jsonl"
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _ready_m369_record() -> dict[str, object]:
    return {
        "blockers": [],
        "checklist": [
            {"evidence": "ok", "item": "M368A ready evidence present", "passed": True},
            {"evidence": "ok", "item": "M368B fresh snapshot flat/clean", "passed": True},
            {"evidence": "ok", "item": "M368B preview ready", "passed": True},
            {"evidence": "ok", "item": "SPY-only scope", "passed": True},
            {"evidence": "ok", "item": "cap <= 25.00", "passed": True},
            {"evidence": "ok", "item": "no open orders", "passed": True},
            {"evidence": "ok", "item": "no positions", "passed": True},
            {"evidence": "ok", "item": "no broker mutation", "passed": True},
            {
                "evidence": "ok",
                "item": "no submit authorization in this milestone",
                "passed": True,
            },
            {
                "evidence": "ok",
                "item": "separate submit milestone required",
                "passed": True,
            },
        ],
        "decision": "ready_for_separate_tiny_spy_paper_submit_milestone",
        "labels": [
            "paper_lab_only",
            "operator_review_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "live_authorized": False,
        "mutated": False,
        "operator_review_ready": True,
        "profit_claim": "none",
        "proposed_order": {
            "asset_class": "equity",
            "notional": "25.00",
            "order_type": "market",
            "side": "buy",
            "symbol": "SPY",
            "time_in_force": "day",
        },
        "record_type": "etf_sma_m369_tiny_spy_paper_submit_operator_review",
        "required_next_milestone": (
            "M370 - Tiny SPY paper submit only after explicit operator approval"
        ),
        "run_id": "m369_tiny_spy_paper_submit_operator_review",
        "snapshot_summary": {
            "account_observed": True,
            "blockers": [],
            "cash": "1999.81",
            "credentials_redacted_present": True,
            "currency": "USD",
            "mutated": False,
            "open_order_count": 0,
            "orders_observed": True,
            "position_count": 0,
            "position_symbols": [],
            "positions_observed": True,
            "recent_order_count": 0,
            "recent_order_query_metadata_complete": True,
            "records_observed": True,
            "submitted": False,
            "unavailable_observations": [],
        },
        "source_m368a_evidence_ids": [
            "m366_fresh_paper_lab_reset_snapshot",
            "m368a_offline_spy_etf_sma_fixture_signal",
        ],
        "source_m368a_signal_caveat": (
            "M368A actionable SMA evidence was deterministic fixture evidence, "
            "not live market data, not profitability evidence, and not live "
            "trading authorization."
        ),
        "source_m368a_signal_evidence_id": (
            "m368a_offline_spy_etf_sma_fixture_signal"
        ),
        "source_m368b_preview_path": (
            "runs/paper_lab/m368b_spy_etf_sma_broker_preview_only.jsonl"
        ),
        "source_m368b_preview_run_id": "m368b_spy_etf_sma_broker_preview_only",
        "source_m368b_snapshot_path": (
            "runs/paper_lab/m368b_fresh_read_only_paper_snapshot.jsonl"
        ),
        "source_m368b_snapshot_run_id": "m368b_fresh_read_only_paper_snapshot",
        "submit_authorized": False,
        "submitted": False,
    }


def _record_with(path: tuple[str, ...], value: object) -> dict[str, object]:
    record = deepcopy(_ready_m369_record())
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
            client_order_id=m370.M370_CLIENT_ORDER_ID,
            filled_average_price="",
            filled_quantity="",
            normalized_status="accepted",
            order_id="broker-m370-order-1",
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
