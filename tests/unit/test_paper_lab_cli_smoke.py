from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaOrderResponse,
    AlpacaOrderRequest,
    AlpacaRecentOrderQuery,
    AlpacaPositionResponse,
)
from algotrader.execution.alpaca_sdk_client import (
    AlpacaSdkClientError,
    _to_sdk_order_request,
)
from algotrader.execution.order_journal import OrderJournalState, SqliteOrderJournal
from algotrader.execution.paper_lab_observation_log import (
    PAPER_CLOSE_PREVIEW_DESIGNED,
    make_paper_close_preview_events,
)
from algotrader.execution.paper_order_policy import (
    OPTIONS_SUBMIT_DISABLED_REASON,
    build_btcusd_paper_close_preview_contract,
)
from tests.fakes.alpaca import FakeAlpacaClient


SENSITIVE_API_KEY = "paper-lab-sensitive-api-key"
SENSITIVE_SECRET_KEY = "paper-lab-sensitive-secret-key"
API_ERROR_URL = "https://paper.example.test/v2/orders"
M355_SPY_CLOSE_CLIENT_ORDER_ID = "paper-order-close-m355_spy_paper_close_submit"
M355_SPY_CLOSE_QUANTITY = "0.032905647"
M376_SPY_CLOSE_CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
M376_SPY_CLOSE_QUANTITY = "0.033172072"


class APIError(Exception):
    """Fake Alpaca APIError shape for offline paper-lab diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 422,
        code: str = "42210000",
    ) -> None:
        super().__init__(message)
        self._message = message
        self._status_code = status_code
        self._code = code

    @property
    def message(self) -> str:
        return self._message

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def code(self) -> str:
        return self._code


def test_notional_order_request_accepts_positive_notional() -> None:
    request = AlpacaOrderRequest(
        client_order_id="deterministic-notional-order",
        symbol="spy",
        side="buy",
        notional=Decimal("5"),
    )

    assert request.symbol == "SPY"
    assert request.qty is None
    assert request.notional == Decimal("5")
    assert request.order_type == "market"
    assert request.time_in_force == "day"
    assert request.asset_class == "equity"


def test_crypto_order_request_accepts_asset_specific_time_in_force() -> None:
    request = AlpacaOrderRequest(
        client_order_id="deterministic-crypto-preview",
        symbol="btcusd",
        side="buy",
        asset_class="crypto",
        notional=Decimal("5"),
        time_in_force="gtc",
    )

    assert request.asset_class == "crypto"
    assert request.symbol == "BTCUSD"
    assert request.time_in_force == "gtc"


def test_btcusd_close_order_request_accepts_sell_quantity_sdk_shape() -> None:
    request = AlpacaOrderRequest(
        client_order_id="deterministic-btcusd-close",
        symbol="btcusd",
        side="sell",
        asset_class="crypto",
        qty=Decimal("0.000132386"),
        time_in_force="gtc",
    )

    sdk_request = _to_sdk_order_request(request)

    assert request.asset_class == "crypto"
    assert request.symbol == "BTCUSD"
    assert request.side == "sell"
    assert request.qty == Decimal("0.000132386")
    assert request.notional is None
    assert sdk_request.side.value == "sell"
    assert sdk_request.symbol == "BTCUSD"
    assert Decimal(str(sdk_request.qty)) == Decimal("0.000132386")
    assert sdk_request.notional is None
    assert sdk_request.time_in_force.value == "gtc"


def test_equity_order_request_rejects_crypto_time_in_force() -> None:
    with pytest.raises(ValueError, match="asset-class-specific time_in_force"):
        AlpacaOrderRequest(
            client_order_id="bad-equity-time-in-force",
            symbol="SPY",
            side="buy",
            asset_class="equity",
            notional=Decimal("5"),
            time_in_force="gtc",
        )


def test_notional_order_request_rejects_both_qty_and_notional() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        AlpacaOrderRequest(
            client_order_id="bad-order",
            symbol="SPY",
            side="buy",
            qty=Decimal("1"),
            notional=Decimal("5"),
        )


def test_notional_order_request_rejects_neither_qty_nor_notional() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        AlpacaOrderRequest(
            client_order_id="bad-order",
            symbol="SPY",
            side="buy",
        )


def test_notional_order_request_rejects_non_positive_notional() -> None:
    with pytest.raises(ValueError, match="notional must be positive"):
        AlpacaOrderRequest(
            client_order_id="bad-order",
            symbol="SPY",
            side="buy",
            notional=Decimal("0"),
        )


def test_account_smoke_refuses_non_paper_profile(monkeypatch, capsys) -> None:
    _set_env(monkeypatch, profile="dev")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        ("paper-account-smoke", "--format", "json"),
        capsys,
    )

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error"] == "paper_profile_required"
    assert payload["gates"]["profile_gate"]["passed"] is False
    assert payload["submitted"] is False


def test_account_smoke_is_read_only_and_does_not_submit(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch)

    exit_code, payload = _run_json(
        ("paper-account-smoke", "--format", "json"),
        capsys,
    )

    assert exit_code == 0
    assert fake_client.calls == ["get_account", "get_positions"]
    assert fake_client.submitted_requests == []
    assert payload["account"] == {"cash": "100000", "currency": "USD"}
    assert payload["position_count"] == 1
    assert payload["positions"] == [
        {"average_price": "100.10", "quantity": "3", "symbol": "MSFT"}
    ]
    assert payload["submitted"] is False


def test_account_smoke_writes_observation_log_when_requested(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch)
    run_log = tmp_path / "runs" / "paper_lab" / "smoke.jsonl"

    exit_code, payload = _run_json(
        (
            "paper-account-smoke",
            "--format",
            "json",
            "--run-log",
            str(run_log),
            "--run-id",
            "account-smoke-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 0
    assert fake_client.calls == ["get_account", "get_positions"]
    assert [record["event_type"] for record in records] == [
        "paper_account_observed",
        "paper_positions_observed",
    ]
    assert records[0]["run_id"] == "account-smoke-run"
    assert records[0]["command"] == "paper-account-smoke"
    assert records[0]["account"] == payload["account"]
    assert records[1]["positions"] == payload["positions"]
    assert records[1]["submitted"] is False


def test_account_smoke_does_not_write_without_run_log(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _install_fake_broker(monkeypatch)
    unexpected_log = tmp_path / "runs" / "paper_lab" / "smoke.jsonl"

    exit_code, payload = _run_json(
        ("paper-account-smoke", "--format", "json"),
        capsys,
    )

    assert exit_code == 0
    assert payload["submitted"] is False
    assert not unexpected_log.exists()


def test_account_smoke_json_is_deterministic_and_credential_free(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _install_fake_broker(monkeypatch)

    first = _run_raw_json(("paper-account-smoke", "--format", "json"), capsys)
    second = _run_raw_json(("paper-account-smoke", "--format", "json"), capsys)

    assert first == second
    assert SENSITIVE_API_KEY not in first
    assert SENSITIVE_SECRET_KEY not in first
    assert json.loads(first)["redaction"] == "credentials_redacted"


def test_order_traceability_review_reads_spy_all_and_closed_orders_only(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeTraceabilityAlpacaClient())
    source_order_log, source_snapshot_log = _write_traceability_source_logs(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "traceability.jsonl"

    exit_code, payload = _run_json(
        (
            "paper-lab-order-traceability-review",
            "--source-order-run-log",
            str(source_order_log),
            "--source-snapshot-run-log",
            str(source_snapshot_log),
            "--run-log",
            str(run_log),
            "--run-id",
            "traceability-run",
            "--format",
            "json",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 0
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders",
        "get_orders",
        "get_orders",
    ]
    assert fake_client.submitted_requests == []
    assert [query.status_filter for query in fake_client.recent_order_queries] == [
        "open",
        "all",
        "closed",
    ]
    assert {query.symbol_filter for query in fake_client.recent_order_queries} == {
        "SPY"
    }
    assert {query.side_filter for query in fake_client.recent_order_queries} == {
        "buy"
    }
    assert payload["ok"] is True
    assert payload["review_state"] == "ready_for_spy_paper_cleanup_preview_milestone"
    assert payload["mutated"] is False
    assert payload["submitted"] is False
    assert payload["redaction"] == "credentials_redacted"
    assert payload["spy_position_observed"] is True
    assert payload["spy_quantity"] == "0.032905647"
    assert payload["spy_average_price"] == "759.748"
    assert payload["recent_open_order_count"] == 0
    assert payload["recent_all_order_count"] == 1
    assert payload["recent_closed_order_count"] == 1
    assert payload["recent_filled_order_count"] == 1
    assert payload["recent_order_query_metadata_complete"] is True
    assert payload["filled_spy_order_found"] is True
    assert payload["broker_order_id_exposed"] is True
    assert payload["client_order_id_exposed"] is True
    assert payload["m351_correlation_basis"] == "client_order_id"
    assert records == [
        {
            **payload,
            "event_type": "paper_lab_order_traceability_reviewed",
            "run_id": "traceability-run",
        }
    ]


def test_spy_close_preview_reads_open_orders_and_writes_readiness_artifact(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeSpyClosePreviewAlpacaClient(),
    )
    source_traceability_log = _write_m353_traceability_log(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m354.jsonl"

    exit_code, payload = _run_json(
        (
            "paper-lab-spy-close-preview",
            "--source-traceability-run-log",
            str(source_traceability_log),
            "--run-log",
            str(run_log),
            "--run-id",
            "m354_spy_cleanup_close_preview",
            "--format",
            "json",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 0
    assert fake_client.calls == ["get_account", "get_positions", "get_orders"]
    assert fake_client.submitted_requests == []
    assert len(fake_client.recent_order_queries) == 1
    assert fake_client.recent_order_queries[0].status_filter == "open"
    assert fake_client.recent_order_queries[0].symbol_filter == "SPY"
    assert fake_client.recent_order_queries[0].side_filter == ""
    assert payload["run_id"] == "m354_spy_cleanup_close_preview"
    assert payload["state"] == "ready_for_separate_spy_paper_close_submit_milestone"
    assert payload["ok"] is True
    assert payload["mutated"] is False
    assert payload["submitted"] is False
    assert payload["broker_action_performed"] is False
    assert payload["close_order_submitted"] is False
    assert payload["live_authorized"] is False
    assert payload["asset_class"] == "equity"
    assert payload["symbol"] == "SPY"
    assert payload["side"] == "sell"
    assert payload["order_type"] == "market"
    assert payload["time_in_force"] == "day"
    assert payload["quantity"] == "0.032905647"
    assert payload["preview_quantity"] == "0.032905647"
    assert payload["observed_spy_quantity"] == "0.032905647"
    assert payload["observed_spy_average_price"] == "759.748"
    assert payload["account_cash"] == "1974.9"
    assert payload["account_currency"] == "USD"
    assert payload["recent_open_order_count"] == 0
    assert payload["m353_evidence_available"] is True
    assert payload["m353_ready"] is True
    assert payload["m353_traceability_summary"][
        "recent_all_spy_buy_order_count"
    ] == 1
    assert payload["m353_traceability_summary"][
        "recent_closed_spy_buy_order_count"
    ] == 1
    assert payload["m353_traceability_summary"][
        "recent_filled_spy_buy_order_count"
    ] == 1
    assert payload["m351_correlation_basis"] == "client_order_id"
    assert (
        payload["m351_client_order_id"]
        == "paper-order-probe-m351_spy_tiny_paper_probe"
    )
    assert payload["max_cleanup_quantity"] == "0.032905647"
    assert payload["allowlist_result"]["passed"] is True
    assert payload["paper_profile_gate_result"]["passed"] is True
    assert payload["notional_quantity_validation_result"] == {
        "notional_used": False,
        "observed_quantity": "0.032905647",
        "quantity_positive": True,
        "quantity_within_observed_position": True,
        "requested_quantity": "0.032905647",
        "sizing_mode": "quantity",
        "would_short": False,
    }
    assert payload["stale_evidence_blockers"] == []
    assert payload["open_order_blockers"] == []
    assert payload["unexpected_position_blockers"] == []
    assert payload["unavailable_observation_blockers"] == []
    assert payload["blockers"] == []
    assert payload["final_operator_instruction"] == (
        "Review only. Do not submit in M354. Use M355 for explicit close "
        "submit if approved."
    )
    assert records == [
        {
            **payload,
            "event_type": "paper_lab_spy_close_preview_reviewed",
            "run_id": "m354_spy_cleanup_close_preview",
        }
    ]


def test_spy_close_preview_blocks_missing_m353_evidence(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeSpyClosePreviewAlpacaClient(),
    )

    exit_code, payload = _run_json(
        (
            "paper-lab-spy-close-preview",
            "--source-traceability-run-log",
            str(tmp_path / "missing_m353.jsonl"),
            "--run-id",
            "m354_spy_cleanup_close_preview",
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 1
    assert fake_client.submitted_requests == []
    assert payload["state"] == "blocked_from_spy_paper_close_submit_milestone"
    assert payload["quantity"] == ""
    assert payload["m353_evidence_available"] is False
    assert payload["m353_ready"] is False
    assert payload["stale_evidence_blockers"] == [
        "m353_traceability_evidence_missing"
    ]
    assert "source_traceability_gate_failed:m353_traceability_must_be_ready" in (
        payload["blockers"]
    )


def test_spy_close_preview_blocks_open_spy_orders(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeSpyClosePreviewAlpacaClient(open_order_count=1),
    )
    source_traceability_log = _write_m353_traceability_log(tmp_path)

    exit_code, payload = _run_json(
        (
            "paper-lab-spy-close-preview",
            "--source-traceability-run-log",
            str(source_traceability_log),
            "--run-id",
            "m354_spy_cleanup_close_preview",
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 1
    assert fake_client.submitted_requests == []
    assert payload["state"] == "blocked_from_spy_paper_close_submit_milestone"
    assert payload["quantity"] == ""
    assert payload["recent_open_order_count"] == 1
    assert payload["open_order_blockers"] == ["recent_open_spy_order_count_nonzero"]
    assert "recent_open_order_gate_failed:recent_open_spy_orders_must_be_zero" in (
        payload["blockers"]
    )


@pytest.mark.parametrize(
    "extra_flags",
    (
        (),
        ("--submit",),
        ("--i-mean-it",),
    ),
)
def test_spy_close_submit_requires_explicit_submit_confirmation(
    monkeypatch,
    capsys,
    tmp_path,
    extra_flags: tuple[str, ...],
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    close_preview_log = _write_m375c_spy_close_preview_log(tmp_path)

    exit_code, payload = _run_json(
        (
            "paper-lab-spy-close-submit",
            "--close-preview-run-log",
            str(close_preview_log),
            "--run-id",
            "m376_spy_position_close_submit",
            *extra_flags,
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["submit_attempt_count"] == 0
    assert payload["broker_action_performed"] is False
    assert payload["close_order_submitted"] is False
    assert payload["error"] == "submit_confirmation_gate_failed"
    assert payload["client_order_id"] == M376_SPY_CLOSE_CLIENT_ORDER_ID
    assert payload["requested_close_quantity"] == M376_SPY_CLOSE_QUANTITY


def test_spy_close_submit_blocks_non_ready_close_preview_without_broker_call(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    close_preview_log = _write_m375c_spy_close_preview_log(
        tmp_path,
        ok=False,
        readiness_classification="blocked_from_spy_paper_close_submit_milestone",
    )

    exit_code, payload = _run_json(
        (
            "paper-lab-spy-close-submit",
            "--close-preview-run-log",
            str(close_preview_log),
            "--submit",
            "--i-mean-it",
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["submit_attempt_count"] == 0
    assert payload["broker_action_performed"] is False
    assert payload["m354_ok"] is False
    assert payload["error"] == "m354_state_gate_failed"


def test_spy_close_submit_blocks_stale_m354_preview_without_broker_call(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    stale_m354_log = _write_m354_spy_close_preview_log(tmp_path)

    exit_code, payload = _run_json(
        (
            "paper-lab-spy-close-submit",
            "--close-preview-run-log",
            str(stale_m354_log),
            "--submit",
            "--i-mean-it",
            "--run-id",
            "m376_spy_position_close_submit",
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["submit_attempt_count"] == 0
    assert payload["broker_action_performed"] is False
    assert payload["close_preview_fresh_source"] is False
    assert payload["m354_state"] == "stale_close_preview_source"
    assert payload["requested_close_quantity"] == ""
    assert payload["client_order_id"] == M376_SPY_CLOSE_CLIENT_ORDER_ID
    assert payload["proposed_order_request"] is None


def test_spy_close_submit_blocks_fresh_open_order_gate(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeSpyCloseSubmitAlpacaClient(
            pre_orders={
                "open": (_spy_close_order_response("other-open-spy-order"),),
            },
        ),
    )
    close_preview_log = _write_m375c_spy_close_preview_log(tmp_path)

    exit_code, payload = _run_json(
        _valid_spy_close_submit_args(close_preview_log, submit=True),
        capsys,
    )

    assert exit_code == 2
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders",
        "get_orders",
        "get_orders",
    ]
    assert fake_client.submitted_requests == []
    assert payload["submitted"] is False
    assert payload["submit_attempt_count"] == 0
    assert payload["recent_open_spy_order_count"] == 1
    assert payload["error"] == "recent_open_order_gate_failed"


def test_spy_close_submit_blocks_duplicate_m376_client_order_id(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeSpyCloseSubmitAlpacaClient(
            pre_orders={
                "all": (
                    _spy_close_order_response(
                        M376_SPY_CLOSE_CLIENT_ORDER_ID
                    ),
                ),
            },
        ),
    )
    close_preview_log = _write_m375c_spy_close_preview_log(tmp_path)

    exit_code, payload = _run_json(
        _valid_spy_close_submit_args(close_preview_log, submit=True),
        capsys,
    )

    assert exit_code == 2
    assert fake_client.submitted_requests == []
    assert payload["submitted"] is False
    assert payload["duplicate_client_order_id_found"] is True
    assert payload["duplicate_m355_client_order_id_found"] is True
    assert payload["error"] == "duplicate_client_order_id_gate_failed"


def test_spy_close_submit_accepts_m376_evidence_and_builds_fresh_request(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeSpyCloseSubmitAlpacaClient(),
    )
    close_preview_log = _write_m375c_spy_close_preview_log(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m376.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_spy_close_submit_args(close_preview_log, submit=True),
            "--run-log",
            str(run_log),
            "--run-id",
            "m376_spy_position_close_submit",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    assert exit_code == 0
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders",
        "get_orders",
        "get_orders",
        "submit_order",
        "get_account",
        "get_positions",
        "get_orders",
        "get_orders",
        "get_orders",
    ]
    assert len(fake_client.submitted_requests) == 1
    request = fake_client.submitted_requests[0]
    assert request.client_order_id == M376_SPY_CLOSE_CLIENT_ORDER_ID
    assert request.client_order_id != M355_SPY_CLOSE_CLIENT_ORDER_ID
    assert request.asset_class == "equity"
    assert request.symbol == "SPY"
    assert request.side == "sell"
    assert request.qty == Decimal(M376_SPY_CLOSE_QUANTITY)
    assert request.qty != Decimal(M355_SPY_CLOSE_QUANTITY)
    assert request.notional is None
    assert request.order_type == "market"
    assert request.time_in_force == "day"
    assert "notional_cap_gate" not in payload["gates"]
    assert payload["proposed_order_request"]["client_order_id"] == (
        M376_SPY_CLOSE_CLIENT_ORDER_ID
    )
    assert payload["proposed_order_request"]["qty"] == M376_SPY_CLOSE_QUANTITY
    assert payload["proposed_order_request"]["notional"] == ""
    assert payload["state"] == "close_submit_accepted_pending_reconciliation"
    assert payload["submitted"] is True
    assert payload["mutated"] is True
    assert payload["broker_action_performed"] is True
    assert payload["close_order_submitted"] is True
    assert payload["live_authorized"] is False
    assert payload["paper_only"] is True
    assert payload["submit_attempt_count"] == 1
    assert payload["broker_result_classification"] == "accepted"
    assert payload["broker_order_id"] == "broker-spy-close-order-1"
    assert payload["accepted"] is True
    assert payload["order_journal_claimed"] is True
    assert payload["order_journal_state"] == OrderJournalState.ACCEPTED.value
    assert payload["order_journal_lease_released"] is True
    assert payload["filled"] is False
    assert payload["normalized_status"] == "accepted"
    assert payload["account_cash"] == "1974.9"
    assert payload["account_currency"] == "USD"
    assert payload["spy_quantity"] == M376_SPY_CLOSE_QUANTITY
    assert payload["recent_open_spy_order_count"] == 0
    assert payload["post_submit_account_cash"] == "1974.9"
    assert payload["post_close_remaining_quantity"] == M376_SPY_CLOSE_QUANTITY
    assert payload["post_submit_recent_open_spy_order_count"] == 1
    assert payload["post_submit_matching_recent_order_found"] is True
    assert [record["event_type"] for record in records] == [
        "paper_lab_spy_close_submit_observed"
    ]
    assert records[0]["command"] == "paper-lab-spy-close-submit"
    assert records[0]["submit_attempt_count"] == 1
    assert records[0]["submitted"] is True
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_spy_close_submit_does_not_retry_after_submit_exception(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeSpyCloseSubmitAlpacaClient(raise_on_submit=True),
    )
    close_preview_log = _write_m375c_spy_close_preview_log(tmp_path)

    exit_code, payload = _run_json(
        _valid_spy_close_submit_args(close_preview_log, submit=True),
        capsys,
    )

    rendered = json.dumps(payload, sort_keys=True)
    assert exit_code == 1
    assert fake_client.calls.count("submit_order") == 1
    assert len(fake_client.submitted_requests) == 1
    assert payload["state"] == "ambiguous_after_single_submit_stop_no_retry"
    assert payload["submitted"] is True
    assert payload["broker_action_performed"] is True
    assert payload["close_order_submitted"] is True
    assert payload["submit_attempt_count"] == 1
    assert payload["broker_result_classification"] == "ambiguous"
    assert payload["broker_error"] is True
    assert payload["order_journal_state"] == OrderJournalState.UNKNOWN.value
    assert payload["order_journal_lease_released"] is True
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_spy_close_submit_durable_claim_blocks_crash_rerun(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    close_preview_log = _write_m375c_spy_close_preview_log(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m376-rerun.jsonl"
    args = (
        *_valid_spy_close_submit_args(close_preview_log, submit=True),
        "--run-log",
        str(run_log),
    )
    first_client = _install_fake_broker(
        monkeypatch,
        FakeSpyCloseSubmitAlpacaClient(),
    )

    first_exit, first = _run_json(args, capsys)

    second_client = _install_fake_broker(
        monkeypatch,
        FakeSpyCloseSubmitAlpacaClient(),
    )
    second_exit, second = _run_json(args, capsys)

    assert first_exit == 0
    assert first["submit_attempt_count"] == 1
    assert first_client.calls.count("submit_order") == 1
    assert second_exit == 2
    assert second["submitted"] is False
    assert second["submit_attempt_count"] == 0
    assert "durable_submit_already_reserved" in second["blockers"]
    assert second_client.calls.count("submit_order") == 0
    journal = SqliteOrderJournal(first["order_journal_path"])
    record = journal.get(M376_SPY_CLOSE_CLIENT_ORDER_ID)
    assert record is not None
    assert record.side == "sell"
    assert record.quantity == Decimal(M376_SPY_CLOSE_QUANTITY)
    assert record.safe_to_resubmit is False


def test_spy_close_submit_journal_unavailable_leaves_submit_untouched(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    import algotrader.execution.order_journal as order_journal

    _set_env(monkeypatch)
    close_preview_log = _write_m375c_spy_close_preview_log(tmp_path)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeSpyCloseSubmitAlpacaClient(),
    )

    class UnavailableJournal:
        def __init__(self, path) -> None:  # noqa: ANN001, ARG002
            raise OSError("journal unavailable")

    monkeypatch.setattr(order_journal, "SqliteOrderJournal", UnavailableJournal)

    exit_code, payload = _run_json(
        _valid_spy_close_submit_args(close_preview_log, submit=True),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["submit_attempt_count"] == 0
    assert payload["order_journal_error"] == "OSError"
    assert "durable_submit_journal_unavailable" in payload["blockers"]
    assert fake_client.calls.count("submit_order") == 0


def test_order_probe_defaults_to_preview_and_does_not_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(_valid_probe_args(), capsys)

    assert exit_code == 0
    assert payload["asset_class"] == "equity"
    assert payload["ok"] is True
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["proposed_order_request"] == {
        "asset_class": "equity",
        "client_order_id": "paper-order-probe-notional-1",
        "limit_price": "",
        "notional": "",
        "order_type": "market",
        "qty": "1",
        "request_model": "AlpacaOrderRequest",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }


def test_order_probe_notional_preview_does_not_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(_valid_notional_probe_args(), capsys)

    assert exit_code == 0
    assert payload["asset_class"] == "equity"
    assert payload["ok"] is True
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["requested_notional"] == "5"
    assert payload["max_notional"] == "10"
    assert payload["proposed_order_request"] == {
        "asset_class": "equity",
        "client_order_id": "paper-order-probe-notional-1",
        "limit_price": "",
        "notional": "5",
        "order_type": "market",
        "qty": "",
        "request_model": "AlpacaOrderRequest",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }


def test_order_probe_accepts_explicit_m351_spy_notional_cap(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        _valid_notional_probe_args(notional="25.00", max_notional="25.00"),
        capsys,
    )

    assert exit_code == 0
    assert payload["asset_class"] == "equity"
    assert payload["symbol"] == "SPY"
    assert payload["side"] == "buy"
    assert payload["order_type"] == "market"
    assert payload["time_in_force"] == "day"
    assert payload["requested_notional"] == "25.00"
    assert payload["max_notional"] == "25.00"
    assert payload["submitted"] is False
    assert payload["gates"]["notional_cap_gate"] == {
        "detail": "notional_within_max_notional",
        "passed": True,
    }
    assert payload["proposed_order_request"]["notional"] == "25.00"


def test_order_probe_run_id_scopes_client_order_id_without_submitting(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            *_valid_notional_probe_args(),
            "--run-id",
            "m306-logged-paper-probe",
        ),
        capsys,
    )

    assert exit_code == 0
    assert payload["submitted"] is False
    assert payload["proposed_order_request"]["client_order_id"] == (
        "paper-order-probe-m306-logged-paper-probe"
    )


def test_order_probe_preview_writes_run_log_with_gates_and_no_submit(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    run_log = tmp_path / "runs" / "paper_lab" / "probe.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_notional_probe_args(),
            "--run-log",
            str(run_log),
            "--run-id",
            "preview-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 0
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed"
    ]
    preview = records[0]
    assert preview["run_id"] == "preview-run"
    assert preview["asset_class"] == "equity"
    assert preview["symbol"] == "SPY"
    assert preview["side"] == "buy"
    assert preview["sizing_mode"] == "notional"
    assert preview["notional"] == "5"
    assert preview["qty"] == ""
    assert set(preview["gate_summary"]) == set(payload["gates"])
    assert preview["submit_requested"] is False
    assert preview["submit_attempted"] is False
    assert preview["broker_response_received"] is False
    assert preview["broker_response_parsed"] is False
    assert preview["submitted"] is False
    assert preview["accepted"] is None
    assert preview["filled"] is None


def test_order_probe_submit_flag_without_i_mean_it_rejects_notional_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (*_valid_notional_probe_args(), "--submit"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "submit_confirmation_gate_failed"
    assert payload["gates"]["submit_confirmation_gate"] == {
        "detail": "submit_requires_submit_and_i_mean_it",
        "passed": False,
    }


def test_order_probe_i_mean_it_without_submit_rejects_notional_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (*_valid_notional_probe_args(), "--i-mean-it"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "submit_confirmation_gate_failed"
    assert payload["gates"]["submit_confirmation_gate"]["passed"] is False


def test_order_probe_halt_blocks_submit(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    monkeypatch.setenv("ALGOTRADER_PAPER_HALT", "1")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (*_valid_notional_probe_args(), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "halt_gate_failed"
    assert payload["gates"]["halt_gate"] == {
        "detail": "ALGOTRADER_PAPER_HALT=1",
        "passed": False,
    }


def test_order_probe_rejects_live_profile(monkeypatch, capsys) -> None:
    _set_env(monkeypatch, profile="live")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(_valid_notional_probe_args(), capsys)

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "profile_gate_failed"
    assert payload["gates"]["profile_gate"]["passed"] is False


def test_order_probe_rejects_non_allowlisted_symbol(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        _valid_notional_probe_args(symbol="AAPL"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "allowlist_gate_failed"
    assert payload["gates"]["allowlist_gate"] == {
        "detail": "symbol_not_allowlisted",
        "passed": False,
    }


def test_order_probe_rejects_sell_side(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(_valid_notional_probe_args(side="sell"), capsys)

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "side_gate_failed"
    assert payload["gates"]["side_gate"] == {
        "detail": "side_must_be_buy",
        "passed": False,
    }


def test_order_probe_rejects_notional_above_milestone_cap(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        _valid_probe_args(max_notional="25.01"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "notional_cap_gate_failed"
    assert payload["gates"]["notional_cap_gate"] == {
        "detail": "max_notional_cap_exceeded",
        "passed": False,
    }


def test_order_probe_rejects_notional_greater_than_max_notional(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        _valid_notional_probe_args(notional="5.01", max_notional="5"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "notional_cap_gate_failed"
    assert payload["gates"]["notional_cap_gate"] == {
        "detail": "notional_exceeds_max_notional",
        "passed": False,
    }


def test_order_probe_fake_successful_notional_submit_is_redacted_and_deterministic(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeNotionalAlpacaClient())

    first = _run_raw_json(
        (*_valid_notional_probe_args(notional="5"), "--submit", "--i-mean-it"),
        capsys,
    )
    first_payload = json.loads(first)

    fake_client = _install_fake_broker(monkeypatch, FakeNotionalAlpacaClient())
    second = _run_raw_json(
        (*_valid_notional_probe_args(notional="5"), "--submit", "--i-mean-it"),
        capsys,
    )

    assert first == second
    assert _LAST_EXIT_CODE == 0
    assert SENSITIVE_API_KEY not in first
    assert SENSITIVE_SECRET_KEY not in first
    assert fake_client.calls == ["submit_order"]
    assert fake_client.submitted_requests[0].qty is None
    assert fake_client.submitted_requests[0].notional == Decimal("5")
    assert fake_client.submitted_requests[0].asset_class == "equity"
    assert first_payload["asset_class"] == "equity"
    assert first_payload["preview_only"] is False
    assert first_payload["submit_requested"] is True
    assert first_payload["submit_attempted"] is True
    assert first_payload["broker_response_received"] is True
    assert first_payload["broker_response_parsed"] is True
    assert first_payload["submitted"] is True
    assert first_payload["accepted"] is True
    assert first_payload["filled"] is False
    assert first_payload["broker_result"] == _expected_broker_result("accepted")
    assert first_payload["broker_normalized_status"] == "accepted"
    assert first_payload["broker_raw_status"] == "accepted"
    assert first_payload["broker_raw_reason"] == ""
    assert first_payload["market_session_note"] == cli_module._PAPER_MARKET_SESSION_NOTE


def test_order_probe_fake_submit_accepts_explicit_m351_spy_payload(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeNotionalAlpacaClient())

    exit_code, payload = _run_json(
        (
            *_valid_notional_probe_args(notional="25.00", max_notional="25.00"),
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 0
    assert fake_client.calls == ["submit_order"]
    assert len(fake_client.submitted_requests) == 1
    request = fake_client.submitted_requests[0]
    assert request.asset_class == "equity"
    assert request.symbol == "SPY"
    assert request.side == "buy"
    assert request.order_type == "market"
    assert request.time_in_force == "day"
    assert request.qty is None
    assert request.notional == Decimal("25.00")
    assert payload["submitted"] is True
    assert payload["accepted"] is True
    assert payload["notional"] == "25.00"
    assert payload["max_notional"] == "25.00"


@pytest.mark.parametrize(
    ("raw_status", "normalized_status"),
    (
        ("orderstatus.accepted", "accepted"),
        ("OrderStatus.ACCEPTED", "accepted"),
        ("new", "new"),
        ("pending_new", "pending_new"),
    ),
)
def test_order_probe_normalizes_active_broker_status_as_accepted(
    monkeypatch,
    capsys,
    raw_status: str,
    normalized_status: str,
) -> None:
    _set_env(monkeypatch)
    _install_fake_broker(monkeypatch, FakeNotionalAlpacaClient(raw_status))

    exit_code, payload = _run_json(
        (*_valid_notional_probe_args(notional="5"), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["error"] == ""
    assert payload["submitted"] is True
    assert payload["accepted"] is True
    assert payload["filled"] is False
    assert payload["broker_result"] == _expected_broker_result(
        normalized_status,
        raw_status=raw_status,
    )


def test_order_probe_filled_broker_status_reports_filled(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _install_fake_broker(monkeypatch, FakeNotionalAlpacaClient("filled"))

    exit_code, payload = _run_json(
        (*_valid_notional_probe_args(notional="5"), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["accepted"] is True
    assert payload["filled"] is True
    assert payload["broker_result"] == _expected_broker_result("filled")


def test_order_probe_rejected_broker_status_reports_rejection(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _install_fake_broker(
        monkeypatch,
        FakeNotionalAlpacaClient(
            "rejected",
            reject_reason="insufficient buying power",
        ),
    )

    exit_code, payload = _run_json(
        (*_valid_notional_probe_args(notional="5"), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error"] == "paper_order_probe_rejected"
    assert payload["submitted"] is True
    assert payload["accepted"] is False
    assert payload["filled"] is False
    assert payload["broker_result"] == _expected_broker_result(
        "rejected",
        accepted=False,
        raw_reason="insufficient buying power",
        reason="insufficient buying power",
    )


def test_order_probe_fake_successful_submit_writes_attempt_and_receipt_records(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeNotionalAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "submit.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_notional_probe_args(notional="5"),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "submit-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 0
    assert fake_client.calls == ["submit_order", "get_account", "get_positions"]
    assert fake_client.submitted_requests[0].client_order_id == (
        "paper-order-probe-submit-run"
    )
    assert payload["submitted"] is True
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
        "paper_order_submit_attempted",
        "paper_order_receipt_observed",
        "paper_order_post_submit_account_observed",
    ]
    attempted = records[2]
    receipt = records[3]
    post_submit = records[4]
    assert attempted["submit_attempted"] is True
    assert attempted["submitted"] is True
    assert receipt["broker_response_received"] is True
    assert receipt["broker_response_parsed"] is True
    assert receipt["accepted"] is True
    assert receipt["filled"] is False
    assert receipt["broker_result"] == _expected_broker_result("accepted")
    assert receipt["broker_normalized_status"] == "accepted"
    assert receipt["broker_raw_status"] == "accepted"
    assert receipt["broker_raw_reason"] == ""
    assert receipt["market_session_note"] == cli_module._PAPER_MARKET_SESSION_NOTE
    assert post_submit["account"] == {"cash": "100000", "currency": "USD"}
    assert post_submit["position_count"] == 1
    assert post_submit["positions"] == [
        {"average_price": "100.10", "quantity": "3", "symbol": "MSFT"}
    ]


def test_order_probe_parse_failure_reports_attempted_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeMalformedAlpacaClient())

    exit_code, payload = _run_json(
        (*_valid_notional_probe_args(notional="5"), "--submit", "--i-mean-it"),
        capsys,
    )

    rendered = json.dumps(payload, sort_keys=True)
    assert exit_code == 1
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered
    assert fake_client.calls == ["submit_order"]
    assert fake_client.submitted_requests[0].qty is None
    assert fake_client.submitted_requests[0].notional == Decimal("5")
    assert payload["ok"] is False
    assert payload["broker_error"] is True
    assert payload["error"] == "broker_response_parse_failed"
    assert payload["error_type"] == "AlpacaTranslationError"
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is True
    assert payload["broker_response_received"] is True
    assert payload["broker_response_parsed"] is False
    assert payload["submitted"] is True
    assert payload["accepted"] is None
    assert payload["filled"] is None
    assert (
        payload["redacted_exception_message"]
        == "Missing required field in Alpaca response: qty, quantity, notional."
    )


def test_order_probe_adapter_failure_before_response_does_not_report_submitted(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FailingSubmitAlpacaClient())

    exit_code, payload = _run_json(
        (*_valid_notional_probe_args(notional="5"), "--submit", "--i-mean-it"),
        capsys,
    )

    rendered = json.dumps(payload, sort_keys=True)
    assert exit_code == 1
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered
    assert fake_client.calls == ["submit_order"]
    assert payload["ok"] is False
    assert payload["broker_error"] is True
    assert payload["error"] == "paper_order_probe_submit_failed"
    assert payload["error_type"] == "AlpacaAdapterError"
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is True
    assert payload["broker_response_received"] is False
    assert payload["broker_response_parsed"] is False
    assert payload["submitted"] is None
    assert payload["accepted"] is None
    assert payload["filled"] is None
    assert payload["redacted_exception_message"] == (
        "Injected Alpaca-like client call failed before response: "
        "submit_order(); cause_type=RuntimeError."
    )


def test_order_probe_parse_failure_writes_parse_failure_observation(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeMalformedAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "parse_failure.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_notional_probe_args(notional="5"),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "parse-failure-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    parse_failure = next(
        record
        for record in records
        if record["event_type"] == "paper_order_response_parse_failed"
    )
    post_submit = records[-1]
    assert exit_code == 1
    assert fake_client.calls == ["submit_order", "get_account", "get_positions"]
    assert payload["error"] == "broker_response_parse_failed"
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
        "paper_order_submit_attempted",
        "paper_order_response_parse_failed",
        "paper_order_post_submit_account_observed",
    ]
    assert parse_failure["submit_attempted"] is True
    assert parse_failure["broker_response_received"] is True
    assert parse_failure["broker_response_parsed"] is False
    assert parse_failure["submitted"] is True
    assert parse_failure["accepted"] is None
    assert parse_failure["filled"] is None
    assert post_submit["account"] == {"cash": "100000", "currency": "USD"}
    assert post_submit["position_count"] == 1


def test_order_probe_adapter_failure_writes_failure_log_without_receipt(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FailingSubmitAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "adapter_failure.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_notional_probe_args(notional="5"),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "adapter-failure-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    rendered_log = run_log.read_text(encoding="utf-8")
    failure = records[-1]
    assert exit_code == 1
    assert fake_client.calls == ["submit_order"]
    assert fake_client.submitted_requests[0].client_order_id == (
        "paper-order-probe-adapter-failure-run"
    )
    assert payload["submitted"] is None
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
        "paper_order_submit_attempted",
        "paper_order_submit_failed",
    ]
    assert "paper_order_receipt_observed" not in {
        record["event_type"] for record in records
    }
    assert failure["submit_attempted"] is True
    assert failure["broker_response_received"] is False
    assert failure["broker_response_parsed"] is False
    assert failure["submitted"] is None
    assert failure["accepted"] is None
    assert failure["filled"] is None
    assert failure["redacted_exception_message"] == (
        "Injected Alpaca-like client call failed before response: "
        "submit_order(); cause_type=RuntimeError."
    )
    assert SENSITIVE_API_KEY not in rendered_log
    assert SENSITIVE_SECRET_KEY not in rendered_log


def test_order_probe_qty_submit_remains_disabled_without_quote_cap(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (*_valid_probe_args(), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "submit_confirmation_gate_failed"
    assert payload["gates"]["submit_confirmation_gate"] == {
        "detail": "qty_submission_disabled_until_quote_based_cap_is_supported",
        "passed": False,
    }
    assert (
        payload["submission_disabled_reason"]
        == "qty_submission_disabled_until_quote_based_cap_is_supported"
    )


def test_crypto_order_probe_preview_uses_crypto_policy_without_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(_valid_crypto_notional_probe_args(), capsys)

    request = payload["proposed_order_request"]
    assert exit_code == 0
    assert payload["asset_class"] == "crypto"
    assert payload["ok"] is True
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["submission_disabled_reason"] == ""
    assert payload["symbol"] == "BTCUSD"
    assert payload["side"] == "buy"
    assert payload["notional"] == "10.00"
    assert payload["min_notional"] == "10.00"
    assert payload["max_notional"] == "10.00"
    assert payload["order_type"] == "market"
    assert payload["time_in_force"] == "gtc"
    assert payload["market_session_note"].startswith("Crypto paper observations")
    assert payload["gates"]["quantity_gate"] == {
        "detail": "not_applicable_for_notional",
        "passed": True,
    }
    assert request["asset_class"] == "crypto"
    assert request["symbol"] == "BTCUSD"
    assert request["side"] == "buy"
    assert request["qty"] == ""
    assert request["notional"] == "10.00"
    assert request["order_type"] == "market"
    assert request["time_in_force"] == "gtc"
    assert request["time_in_force"] != "day"


def test_crypto_order_probe_blocks_btcusd_below_min_notional_before_submit(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    run_log = tmp_path / "runs" / "paper_lab" / "crypto_min_notional.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(
                notional="1.00",
                max_notional="5.00",
            ),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "crypto-min-notional-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 2
    assert payload["asset_class"] == "crypto"
    assert payload["ok"] is False
    assert payload["error"] == "notional_min_gate_failed"
    assert payload["notional"] == "1.00"
    assert payload["min_notional"] == "10.00"
    assert payload["max_notional"] == "5.00"
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["broker_response_received"] is False
    assert payload["broker_response_parsed"] is False
    assert payload["submitted"] is False
    assert payload["accepted"] is None
    assert payload["filled"] is None
    assert "broker_result" not in payload
    assert payload["gates"]["notional_min_gate"] == {
        "detail": "notional_below_crypto_min_notional",
        "passed": False,
    }
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
    ]
    assert {record["submit_attempted"] for record in records} == {False}
    assert {record["broker_response_received"] for record in records} == {False}
    assert {record["min_notional"] for record in records} == {"10.00"}
    assert records[-1]["gate_summary"]["notional_min_gate"] == {
        "detail": "notional_below_crypto_min_notional",
        "passed": False,
    }
    assert "paper_order_submit_attempted" not in {
        record["event_type"] for record in records
    }
    assert "paper_order_receipt_observed" not in {
        record["event_type"] for record in records
    }


def test_crypto_order_probe_fake_successful_submit_writes_attempt_and_receipt_records(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeNotionalAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "crypto_submit.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "crypto-submit-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    assert exit_code == 0
    assert fake_client.calls == ["submit_order", "get_account", "get_positions"]
    assert fake_client.submitted_requests[0].asset_class == "crypto"
    assert fake_client.submitted_requests[0].symbol == "BTCUSD"
    assert fake_client.submitted_requests[0].qty is None
    assert fake_client.submitted_requests[0].notional == Decimal("10.00")
    assert fake_client.submitted_requests[0].order_type == "market"
    assert fake_client.submitted_requests[0].time_in_force == "gtc"
    assert payload["asset_class"] == "crypto"
    assert payload["submitted"] is True
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is True
    assert payload["preview_only"] is False
    assert payload["broker_response_received"] is True
    assert payload["broker_response_parsed"] is True
    assert payload["accepted"] is True
    assert payload["filled"] is False
    assert payload["broker_result"] == _expected_broker_result("accepted")
    assert payload["normalized_status"] == "accepted"
    assert payload["raw_status"] == "accepted"
    assert payload["raw_reason"] == ""
    assert payload["broker_normalized_status"] == "accepted"
    assert payload["broker_raw_status"] == "accepted"
    assert payload["broker_raw_reason"] == ""
    assert payload["submission_disabled_reason"] == ""
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
        "paper_order_submit_attempted",
        "paper_order_receipt_observed",
        "paper_order_post_submit_account_observed",
    ]
    assert {record["asset_class"] for record in records} == {"crypto"}
    receipt = records[3]
    assert receipt["symbol"] == "BTCUSD"
    assert receipt["notional"] == "10.00"
    assert receipt["min_notional"] == "10.00"
    assert receipt["max_notional"] == "10.00"
    assert receipt["order_type"] == "market"
    assert receipt["time_in_force"] == "gtc"
    assert receipt["submit_attempted"] is True
    assert receipt["submitted"] is True
    assert receipt["broker_response_received"] is True
    assert receipt["broker_response_parsed"] is True
    assert receipt["normalized_status"] == "accepted"
    assert receipt["raw_status"] == "accepted"
    assert receipt["raw_reason"] == ""
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_crypto_order_probe_adapter_failure_reports_unknown_submission(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FailingSubmitAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "crypto_adapter_failure.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "crypto-adapter-failure-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    assert exit_code == 1
    assert fake_client.calls == ["submit_order"]
    assert fake_client.submitted_requests[0].asset_class == "crypto"
    assert fake_client.submitted_requests[0].symbol == "BTCUSD"
    assert fake_client.submitted_requests[0].qty is None
    assert fake_client.submitted_requests[0].notional == Decimal("10.00")
    assert fake_client.submitted_requests[0].order_type == "market"
    assert fake_client.submitted_requests[0].time_in_force == "gtc"
    assert payload["asset_class"] == "crypto"
    assert payload["ok"] is False
    assert payload["broker_error"] is True
    assert payload["error"] == "paper_order_probe_submit_failed"
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is True
    assert payload["broker_response_received"] is False
    assert payload["broker_response_parsed"] is False
    assert payload["submitted"] is None
    assert payload["accepted"] is None
    assert payload["filled"] is None
    assert payload["redacted_exception_message"] == (
        "Injected Alpaca-like client call failed before response: "
        "submit_order(); cause_type=RuntimeError."
    )
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
        "paper_order_submit_attempted",
        "paper_order_submit_failed",
    ]
    failure = records[-1]
    assert failure["asset_class"] == "crypto"
    assert failure["submit_attempted"] is True
    assert failure["broker_response_received"] is False
    assert failure["broker_response_parsed"] is False
    assert failure["submitted"] is None
    assert failure["accepted"] is None
    assert failure["filled"] is None
    assert failure["redacted_exception_message"] == (
        "Injected Alpaca-like client call failed before response: "
        "submit_order(); cause_type=RuntimeError."
    )
    assert "paper_order_receipt_observed" not in {
        record["event_type"] for record in records
    }
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_crypto_order_probe_api_error_reports_sanitized_submit_diagnostics(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FailingApiErrorAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "crypto_api_error.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "crypto-api-error-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    failure = records[-1]
    expected_shape = {
        "asset_class": "crypto",
        "symbol": "BTCUSD",
        "side": "buy",
        "order_type": "market",
        "time_in_force": "gtc",
        "sizing_mode": "notional",
    }
    assert exit_code == 1
    assert fake_client.calls == ["submit_order"]
    assert payload["ok"] is False
    assert payload["broker_error"] is True
    assert payload["error"] == "paper_order_probe_submit_failed"
    assert payload["error_type"] == "AlpacaAdapterError"
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is True
    assert payload["broker_response_received"] is False
    assert payload["broker_response_parsed"] is False
    assert payload["submitted"] is None
    assert payload["accepted"] is None
    assert payload["filled"] is None
    assert payload["submit_error_stage"] == "submit_call_failed_before_response"
    assert payload["submit_error_exception_class"] == "APIError"
    assert payload["submit_error_status_code"] == 422
    assert payload["submit_error_code"] == "42210000"
    assert payload["submit_error_message"] == (
        "invalid crypto order at <redacted_url> token=<redacted>"
    )
    assert payload["submit_error_request_shape"] == expected_shape
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
        "paper_order_submit_attempted",
        "paper_order_submit_failed",
    ]
    assert failure["submit_attempted"] is True
    assert failure["broker_response_received"] is False
    assert failure["broker_response_parsed"] is False
    assert failure["submitted"] is None
    assert failure["accepted"] is None
    assert failure["filled"] is None
    assert failure["submit_error_stage"] == "submit_call_failed_before_response"
    assert failure["submit_error_exception_class"] == "APIError"
    assert failure["submit_error_status_code"] == 422
    assert failure["submit_error_code"] == "42210000"
    assert failure["submit_error_message"] == (
        "invalid crypto order at <redacted_url> token=<redacted>"
    )
    assert failure["submit_error_request_shape"] == expected_shape
    assert "paper_order_receipt_observed" not in {
        record["event_type"] for record in records
    }
    assert API_ERROR_URL not in rendered
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_crypto_order_probe_rejects_live_profile_before_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch, profile="live")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(),
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["asset_class"] == "crypto"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "profile_gate_failed"
    assert payload["gates"]["profile_gate"]["passed"] is False


def test_crypto_order_probe_rejects_live_base_url_before_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://api.alpaca.markets")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(),
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["asset_class"] == "crypto"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "profile_gate_failed"
    assert payload["gates"]["profile_gate"] == {
        "detail": (
            "Alpaca paper operations require ALPACA_PAPER_BASE_URL to point "
            "to a paper endpoint."
        ),
        "passed": False,
    }


def test_crypto_order_probe_rejects_non_allowlisted_symbol(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(symbol="ETHUSD"),
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["asset_class"] == "crypto"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "allowlist_gate_failed"
    assert payload["gates"]["allowlist_gate"] == {
        "detail": "symbol_not_allowlisted",
        "passed": False,
    }


def test_crypto_order_probe_rejects_max_notional_above_crypto_cap(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(max_notional="10.01"),
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["asset_class"] == "crypto"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "notional_cap_gate_failed"
    assert payload["gates"]["notional_cap_gate"] == {
        "detail": "max_notional_cap_exceeded",
        "passed": False,
    }


def test_crypto_order_probe_rejects_notional_above_max_notional(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(notional="10.01", max_notional="10"),
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["asset_class"] == "crypto"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "notional_cap_gate_failed"
    assert payload["gates"]["notional_cap_gate"] == {
        "detail": "notional_exceeds_max_notional",
        "passed": False,
    }


def test_crypto_order_probe_rejects_qty_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            "paper-order-probe",
            "--asset-class",
            "crypto",
            "--symbol",
            "BTCUSD",
            "--side",
            "buy",
            "--qty",
            "1",
            "--max-notional",
            "5",
            "--format",
            "json",
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["asset_class"] == "crypto"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "sizing_gate_failed"
    assert payload["gates"]["sizing_gate"] == {
        "detail": "crypto_notional_required",
        "passed": False,
    }
    assert (
        payload["submission_disabled_reason"]
        == "qty_submission_disabled_until_quote_based_cap_is_supported"
    )


def test_crypto_order_probe_rejects_sell_side(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            *_valid_crypto_notional_probe_args(side="sell"),
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["asset_class"] == "crypto"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "side_gate_failed"
    assert payload["gates"]["side_gate"] == {
        "detail": "side_must_be_buy",
        "passed": False,
    }


def test_paper_close_probe_requires_submit_and_i_mean_it_before_broker_build(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (*_valid_close_probe_args(), "--submit"),
        capsys,
    )

    assert exit_code == 2
    assert payload["command"] == "paper-close-probe"
    assert payload["asset_class"] == "crypto"
    assert payload["symbol"] == "BTCUSD"
    assert payload["side"] == "sell"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is False
    assert payload["submit_attempted"] is False
    assert payload["error"] == "submit_confirmation_gate_failed"
    assert payload["gates"]["submit_confirmation_gate"] == {
        "detail": "submit_requires_submit_and_i_mean_it",
        "passed": False,
    }


def test_paper_close_probe_rejects_live_profile_before_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch, profile="live")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (*_valid_close_probe_args(), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "profile_gate_failed"
    assert payload["gates"]["profile_gate"]["passed"] is False


def test_paper_close_probe_rejects_live_base_url_before_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://api.alpaca.markets")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (*_valid_close_probe_args(), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["error"] == "profile_gate_failed"
    assert payload["gates"]["profile_gate"]["passed"] is False


def test_paper_close_probe_rejects_quantity_above_max_before_broker_build(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        (
            *_valid_close_probe_args(max_quantity="0.000132385"),
            "--submit",
            "--i-mean-it",
        ),
        capsys,
    )

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["submit_attempted"] is False
    assert payload["error"] == "quantity_within_max_gate_failed"
    assert payload["gates"]["quantity_within_max_gate"] == {
        "detail": "quantity_exceeds_max_quantity",
        "passed": False,
    }


def test_paper_close_probe_rejects_quantity_above_observed_position(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeCloseAlpacaClient(position_qty="0.000132385"),
    )

    exit_code, payload = _run_json(
        (*_valid_close_probe_args(), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 2
    assert fake_client.calls == ["get_account", "get_positions", "get_orders"]
    assert fake_client.submitted_requests == []
    assert payload["submitted"] is False
    assert payload["submit_attempted"] is False
    assert payload["target_position_observed"] is True
    assert payload["target_position_quantity"] == "0.000132385"
    assert payload["error"] == "observed_position_quantity_gate_failed"
    assert payload["gates"]["observed_position_quantity_gate"] == {
        "detail": "observed_BTCUSD_quantity_must_equal_max_quantity",
        "passed": False,
    }
    assert payload["gates"]["no_shorting_gate"]["passed"] is False


def test_paper_close_probe_rejects_open_orders_before_submit(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeCloseAlpacaClient(
            orders=(
                {
                    "asset_class": "crypto",
                    "client_order_id": "other-open-order",
                    "order_id": "open-order-1",
                    "order_type": "market",
                    "qty": "0.000132386",
                    "side": "sell",
                    "status": "accepted",
                    "symbol": "BTCUSD",
                    "time_in_force": "gtc",
                },
            )
        ),
    )

    exit_code, payload = _run_json(
        (*_valid_close_probe_args(), "--submit", "--i-mean-it"),
        capsys,
    )

    assert exit_code == 2
    assert fake_client.calls == ["get_account", "get_positions", "get_orders"]
    assert fake_client.submitted_requests == []
    assert payload["submitted"] is False
    assert payload["submit_attempted"] is False
    assert payload["recent_order_count"] == 1
    assert payload["recent_order_query_metadata_complete"] is True
    assert payload["error"] == "recent_open_order_gate_failed"
    assert payload["gates"]["recent_open_order_gate"] == {
        "detail": "recent_open_orders_must_be_zero",
        "passed": False,
    }


def test_paper_close_probe_fake_successful_submit_writes_one_attempt(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(monkeypatch, FakeCloseAlpacaClient())
    run_log = tmp_path / "runs" / "paper_lab" / "close_submit.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_close_probe_args(),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "close-submit-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    assert exit_code == 0
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders",
        "submit_order",
        "get_account",
        "get_positions",
    ]
    assert len(fake_client.submitted_requests) == 1
    request = fake_client.submitted_requests[0]
    assert request.client_order_id == "paper-close-probe-close-submit-run"
    assert request.asset_class == "crypto"
    assert request.symbol == "BTCUSD"
    assert request.side == "sell"
    assert request.qty == Decimal("0.000132386")
    assert request.notional is None
    assert request.order_type == "market"
    assert request.time_in_force == "gtc"
    assert payload["submitted"] is True
    assert payload["mutated"] is True
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is True
    assert payload["preview_only"] is False
    assert payload["broker_response_received"] is True
    assert payload["broker_response_parsed"] is True
    assert payload["broker_result_classification"] == "accepted"
    assert payload["accepted"] is True
    assert payload["filled"] is False
    assert payload["normalized_status"] == "accepted"
    assert payload["target_position_observed"] is True
    assert payload["target_position_quantity"] == "0.000132386"
    assert payload["recent_order_count"] == 0
    assert payload["recent_order_query_metadata_complete"] is True
    assert payload["unavailable_observations"] == []
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
        "paper_order_submit_attempted",
        "paper_order_receipt_observed",
        "paper_order_post_submit_account_observed",
    ]
    assert {record["command"] for record in records} == {"paper-close-probe"}
    receipt = records[3]
    assert receipt["asset_class"] == "crypto"
    assert receipt["symbol"] == "BTCUSD"
    assert receipt["side"] == "sell"
    assert receipt["qty"] == "0.000132386"
    assert receipt["max_quantity"] == "0.000132386"
    assert receipt["target_position_quantity"] == "0.000132386"
    assert receipt["recent_order_count"] == 0
    assert receipt["recent_order_query_metadata_complete"] is True
    assert receipt["submitted"] is True
    assert receipt["submit_attempted"] is True
    assert receipt["broker_response_received"] is True
    assert receipt["broker_response_parsed"] is True
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered


def test_options_order_probe_branch_is_disabled(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(_valid_option_probe_args(), capsys)

    request = payload["proposed_order_request"]
    assert exit_code == 2
    assert payload["asset_class"] == "option"
    assert payload["submitted"] is False
    assert payload["submit_attempted"] is False
    assert payload["error"] == "submit_confirmation_gate_failed"
    assert payload["gates"]["submit_confirmation_gate"] == {
        "detail": OPTIONS_SUBMIT_DISABLED_REASON,
        "passed": False,
    }
    assert payload["submission_disabled_reason"] == OPTIONS_SUBMIT_DISABLED_REASON
    assert request["symbol"] == "SPY260117C00600000"
    assert request["qty"] == "1"
    assert request["notional"] == ""


def test_options_order_probe_submit_performs_no_broker_call_or_receipt_log(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    run_log = tmp_path / "runs" / "paper_lab" / "options_disabled.jsonl"

    exit_code, payload = _run_json(
        (
            *_valid_option_probe_args(),
            "--submit",
            "--i-mean-it",
            "--run-log",
            str(run_log),
            "--run-id",
            "options-disabled-run",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 2
    assert payload["asset_class"] == "option"
    assert payload["submitted"] is False
    assert payload["submit_requested"] is True
    assert payload["submit_attempted"] is False
    assert payload["submission_disabled_reason"] == OPTIONS_SUBMIT_DISABLED_REASON
    assert [record["event_type"] for record in records] == [
        "paper_order_previewed",
        "paper_order_submit_requested",
    ]
    assert {record["asset_class"] for record in records} == {"option"}
    assert "paper_order_receipt_observed" not in {
        record["event_type"] for record in records
    }


def test_account_smoke_redacts_credentials_from_failures(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)

    def failing_build(paper_config):  # noqa: ANN001
        raise RuntimeError(f"{SENSITIVE_API_KEY} {SENSITIVE_SECRET_KEY}")

    monkeypatch.setattr(cli_module, "_build_paper_broker", failing_build)

    exit_code, payload = _run_json(
        ("paper-account-smoke", "--format", "json"),
        capsys,
    )

    rendered = json.dumps(payload, sort_keys=True)
    assert exit_code == 1
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered
    assert payload["message"] == "<redacted> <redacted>"


def test_order_probe_json_output_is_deterministic(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    first = _run_raw_json(_valid_probe_args(), capsys)
    second = _run_raw_json(_valid_probe_args(), capsys)

    assert first == second
    assert json.loads(first)["preview_only"] is True
    assert json.loads(first)["submitted"] is False


def test_run_log_records_are_credential_and_env_value_free(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    run_log = tmp_path / "probe.jsonl"

    _run_raw_json(
        (
            *_valid_notional_probe_args(),
            "--run-log",
            str(run_log),
            "--run-id",
            "redaction-run",
        ),
        capsys,
    )

    rendered = run_log.read_text(encoding="utf-8")
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered
    assert "https://paper.example.test" not in rendered
    assert "credentials_redacted" in rendered


def test_run_log_is_byte_identical_for_repeated_deterministic_inputs(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    first_log = tmp_path / "first.jsonl"
    second_log = tmp_path / "second.jsonl"

    _run_raw_json(
        (
            *_valid_notional_probe_args(),
            "--run-log",
            str(first_log),
            "--run-id",
            "deterministic-run",
        ),
        capsys,
    )
    _run_raw_json(
        (
            *_valid_notional_probe_args(),
            "--run-log",
            str(second_log),
            "--run-id",
            "deterministic-run",
        ),
        capsys,
    )

    assert first_log.read_bytes() == second_log.read_bytes()


def test_revalidation_brief_cli_reads_local_log_without_runtime_config(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    run_log = tmp_path / "runs" / "paper_lab" / "snapshot.jsonl"
    run_log.parent.mkdir(parents=True)
    _write_revalidation_snapshot_run_log(run_log)

    def forbidden_config_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("revalidation brief must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config_load)
    _forbid_broker_build(monkeypatch)

    exit_code = main(
        (
            "paper-lab-revalidation-brief",
            "--run-log",
            str(run_log),
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert payload["state"] == "usable_for_manual_review"
    assert payload["usable_for_manual_review"] is True
    assert payload["selected_run_id"] == "snapshot-run"
    assert payload["account"] == {
        "cash": "100000",
        "currency": "USD",
        "observed": True,
    }
    assert payload["fresh_snapshot_operator_checklist"]["status"] == (
        "blocked_query_metadata_incomplete"
    )
    assert payload["fresh_snapshot_operator_checklist"][
        "fresh_snapshot_command_template"
    ] == (
        "python -m algotrader paper-lab-snapshot --run-log "
        "runs/paper_lab/<fresh_id>.jsonl --run-id <fresh_id> --format json"
    )
    assert payload["close_action_eligibility_checklist"]["status"] == (
        "blocked_query_metadata_incomplete"
    )
    assert (
        payload["close_action_eligibility_checklist"][
            "eligible_for_future_close_probe_consideration"
        ]
        is False
    )
    assert payload["future_close_probe_preparation"]["manual_review_only"] is True
    assert (
        payload["future_close_probe_preparation"]["broker_action_performed"]
        is False
    )
    assert (
        payload["future_close_probe_preparation"]["close_order_submitted"]
        is False
    )
    assert (
        payload["future_close_probe_preparation"][
            "ready_for_future_prompt_generation"
        ]
        is False
    )


@pytest.mark.parametrize(
    ("include_close_preview", "output_format", "expected_ready"),
    (
        (True, "json", True),
        (False, "json", False),
        (True, "text", True),
        (False, "text", False),
    ),
)
def test_revalidation_brief_cli_reports_explicit_close_probe_prompt_review(
    monkeypatch,
    capsys,
    tmp_path,
    include_close_preview: bool,
    output_format: str,
    expected_ready: bool,
) -> None:
    run_log = tmp_path / "runs" / "paper_lab" / "m328.jsonl"
    run_log.parent.mkdir(parents=True)
    _write_close_preview_fresh_snapshot_run_log(run_log)
    if include_close_preview:
        _append_jsonl_records(run_log, _revalidation_close_preview_records())

    def forbidden_config_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("revalidation brief must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config_load)
    _forbid_broker_build(monkeypatch)

    exit_code = main(
        (
            "paper-lab-revalidation-brief",
            "--run-log",
            str(run_log),
            "--run-id",
            "m324-fresh-read-only",
            "--format",
            output_format,
        )
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    if output_format == "json":
        payload = json.loads(captured.out)
        prompt_review = payload["explicit_close_probe_prompt_review"]
        assert prompt_review["manual_review_only"] is True
        assert prompt_review["broker_action_performed"] is False
        assert prompt_review["close_order_submitted"] is False
        assert (
            prompt_review["prompt_ready_for_operator_review"]
            is expected_ready
        )
        assert "--submit" not in prompt_review[
            "future_command_template_review_only"
        ]
    else:
        assert "explicit_close_probe_prompt_review:" in captured.out
        assert "review_only_label: operator_review_only" in captured.out
        assert (
            f"prompt_ready_for_operator_review: {str(expected_ready).lower()}"
            in captured.out
        )
        command_lines = [
            line
            for line in captured.out.splitlines()
            if "future_command_template_review_only:" in line
        ]
        assert command_lines
        assert all("--submit" not in line for line in command_lines)


def test_revalidation_brief_cli_reports_submit_receipt_observation(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    run_log = tmp_path / "runs" / "paper_lab" / "m319.jsonl"
    run_log.parent.mkdir(parents=True)
    _write_revalidation_m319_submit_run_log(run_log)

    def forbidden_config_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("revalidation brief must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config_load)
    _forbid_broker_build(monkeypatch)

    exit_code = main(
        (
            "paper-lab-revalidation-brief",
            "--run-log",
            str(run_log),
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert payload["state"] == "receipt_and_position_observed_with_order_list_gap"
    assert payload["usable_for_manual_review"] is True
    assert payload["submit_observation"]["submit_attempt_count"] == 1
    assert payload["submit_observation"]["cash_delta"] == "-9.81"
    assert payload["submit_observation"]["order_list_observation_gap"] is True
    assert (
        payload["submit_observation"]["order_list_gap_reason"]
        == "recent_order_query_returned_empty"
    )
    assert payload["post_receipt_reconciliation"]["reconciliation_confidence"] == (
        "medium_receipt_position_observed_order_gap"
    )
    assert payload["post_receipt_reconciliation"][
        "recommended_next_operator_action"
    ] == "read_only_fresh_snapshot_before_any_close_probe"
    assert payload["fresh_snapshot_operator_checklist"][
        "recommended_next_operator_action"
    ] == "read_only_fresh_snapshot_before_any_close_probe"


def test_revalidation_brief_cli_text_renders_post_receipt_reconciliation(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    run_log = tmp_path / "runs" / "paper_lab" / "m319.jsonl"
    run_log.parent.mkdir(parents=True)
    _write_revalidation_m319_submit_run_log(run_log)

    def forbidden_config_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("revalidation brief must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config_load)
    _forbid_broker_build(monkeypatch)

    exit_code = main(
        (
            "paper-lab-revalidation-brief",
            "--run-log",
            str(run_log),
            "--format",
            "text",
        )
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert "post_receipt_reconciliation:" in captured.out
    assert (
        "reconciliation_confidence: medium_receipt_position_observed_order_gap"
        in captured.out
    )
    assert (
        "recommended_next_operator_action: "
        "read_only_fresh_snapshot_before_any_close_probe"
        in captured.out
    )
    assert "fresh_snapshot_operator_checklist:" in captured.out
    assert "close_action_eligibility_checklist:" in captured.out
    assert "future_close_probe_preparation:" in captured.out
    assert (
        "fresh_snapshot_command_template: "
        "python -m algotrader paper-lab-snapshot --run-log "
        "runs/paper_lab/<fresh_id>.jsonl --run-id <fresh_id> --format json"
        in captured.out
    )


def test_paper_close_preview_cli_reads_local_snapshot_without_runtime_config(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    run_log = tmp_path / "runs" / "paper_lab" / "m324.jsonl"
    run_log.parent.mkdir(parents=True)
    _write_close_preview_fresh_snapshot_run_log(run_log)

    def forbidden_config_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("paper close preview must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config_load)
    _forbid_broker_build(monkeypatch)

    exit_code = main(
        (
            "paper-close-preview",
            "--run-log",
            str(run_log),
            "--symbol",
            "BTCUSD",
            "--quantity",
            "0.000132386",
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert payload["command"] == "paper-close-preview"
    assert payload["ok"] is True
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["paper_lab_only"] is True
    assert payload["not_live_authorized"] is True
    assert payload["profit_claim"] == "none"
    assert payload["manual_review_required"] is True
    assert payload["asset_class"] == "crypto"
    assert payload["symbol"] == "BTCUSD"
    assert payload["side"] == "sell"
    assert payload["order_type"] == "market"
    assert payload["time_in_force"] == "gtc"
    assert payload["observed_position_quantity"] == "0.000132386"
    assert payload["requested_close_quantity"] == "0.000132386"
    assert payload["remaining_quantity_after_preview"] == "0"
    assert payload["close_quantity_within_observed_position"] is True
    assert payload["no_shorting_gate"] == "passed"
    assert payload["fresh_snapshot_required"] is True
    assert payload["fresh_snapshot_status"] == (
        "read_only_snapshot_completed_for_manual_review"
    )
    assert payload["recent_order_query_metadata_complete"] is True
    assert "broker_result" not in payload
    assert payload["source_selected_run_id"] == "m324-fresh-read-only"


def test_paper_close_preview_cli_appends_durable_event_without_runtime_config(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    run_log = tmp_path / "runs" / "paper_lab" / "m324_combined.jsonl"
    run_log.parent.mkdir(parents=True)
    _write_close_preview_fresh_snapshot_run_log(run_log)

    def forbidden_config_load(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("paper close preview must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config_load)
    _forbid_broker_build(monkeypatch)

    exit_code = main(
        (
            "paper-close-preview",
            "--run-log",
            str(run_log),
            "--run-id",
            "m324-fresh-read-only",
            "--symbol",
            "BTCUSD",
            "--quantity",
            "0.000132386",
            "--output-run-log",
            str(run_log),
            "--output-run-id",
            "m329a-close-preview",
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    records = [
        json.loads(line)
        for line in run_log.read_text(encoding="utf-8").splitlines()
    ]
    preview_events = [
        record
        for record in records
        if record["event_type"] == PAPER_CLOSE_PREVIEW_DESIGNED
    ]

    assert exit_code == 0
    assert captured.err == ""
    assert payload["output_run_log"] == str(run_log)
    assert payload["output_run_id"] == "m329a-close-preview"
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["close_order_submitted"] is False
    assert [event["run_id"] for event in preview_events] == [
        "m329a-close-preview"
    ]
    event = preview_events[0]
    assert event["command"] == "paper-close-preview"
    assert event["preview_only"] is True
    assert event["asset_class"] == "crypto"
    assert event["symbol"] == "BTCUSD"
    assert event["side"] == "sell"
    assert event["quantity"] == "0.000132386"
    assert event["max_quantity"] == "0.000132386"
    assert event["observed_position_quantity"] == "0.000132386"
    assert event["remaining_quantity_after_preview"] == "0"
    assert event["no_shorting_gate"] == "passed"
    assert event["submitted"] is False
    assert event["mutated"] is False
    assert event["broker_action_performed"] is False
    assert event["close_order_submitted"] is False
    assert "broker_result" not in event


def test_invalid_run_log_path_reports_cleanly(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)
    directory_path = tmp_path / "not-a-file"
    directory_path.mkdir()

    exit_code = main(
        (
            *_valid_notional_probe_args(),
            "--run-log",
            str(directory_path),
            "--run-id",
            "bad-path-run",
        )
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "paper_lab_run_log_write_failed:" in captured.err
    assert "Traceback" not in captured.err
    assert SENSITIVE_API_KEY not in captured.err
    assert SENSITIVE_SECRET_KEY not in captured.err
    assert "https://paper.example.test" not in captured.err


def _valid_probe_args(
    *,
    symbol: str = "SPY",
    side: str = "buy",
    qty: str = "1",
    max_notional: str = "10",
) -> tuple[str, ...]:
    return (
        "paper-order-probe",
        "--symbol",
        symbol,
        "--side",
        side,
        "--qty",
        qty,
        "--max-notional",
        max_notional,
        "--format",
        "json",
    )


def _valid_notional_probe_args(
    *,
    symbol: str = "SPY",
    side: str = "buy",
    notional: str = "5",
    max_notional: str = "10",
) -> tuple[str, ...]:
    return (
        "paper-order-probe",
        "--symbol",
        symbol,
        "--side",
        side,
        "--notional",
        notional,
        "--max-notional",
        max_notional,
        "--format",
        "json",
    )


def _valid_crypto_notional_probe_args(
    *,
    symbol: str = "BTCUSD",
    side: str = "buy",
    notional: str = "10.00",
    max_notional: str = "10.00",
) -> tuple[str, ...]:
    return (
        "paper-order-probe",
        "--asset-class",
        "crypto",
        "--symbol",
        symbol,
        "--side",
        side,
        "--notional",
        notional,
        "--max-notional",
        max_notional,
        "--format",
        "json",
    )


def _valid_close_probe_args(
    *,
    asset_class: str = "crypto",
    symbol: str = "BTCUSD",
    side: str = "sell",
    quantity: str = "0.000132386",
    max_quantity: str = "0.000132386",
) -> tuple[str, ...]:
    return (
        "paper-close-probe",
        "--asset-class",
        asset_class,
        "--symbol",
        symbol,
        "--side",
        side,
        "--quantity",
        quantity,
        "--max-quantity",
        max_quantity,
        "--format",
        "json",
    )


def _valid_spy_close_submit_args(
    close_preview_run_log,  # noqa: ANN001
    *,
    submit: bool = False,
) -> tuple[str, ...]:
    args = (
        "paper-lab-spy-close-submit",
        "--close-preview-run-log",
        str(close_preview_run_log),
        "--run-id",
        "m376_spy_position_close_submit",
        "--format",
        "json",
    )
    if submit:
        return (*args, "--submit", "--i-mean-it")

    return args


def _valid_option_probe_args(
    *,
    symbol: str = "SPY260117C00600000",
    side: str = "buy",
    qty: str = "1",
    max_notional: str = "1",
) -> tuple[str, ...]:
    return (
        "paper-order-probe",
        "--asset-class",
        "option",
        "--symbol",
        symbol,
        "--side",
        side,
        "--qty",
        qty,
        "--max-notional",
        max_notional,
        "--format",
        "json",
    )


def _set_env(monkeypatch, *, profile: str = "paper") -> None:
    monkeypatch.setenv("APP_PROFILE", profile)
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_API_KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SENSITIVE_SECRET_KEY)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper.example.test")
    monkeypatch.delenv("ALGOTRADER_PAPER_HALT", raising=False)


class FakeNotionalAlpacaClient(FakeAlpacaClient):
    def __init__(
        self,
        status: str = "accepted",
        *,
        reject_reason: str = "",
    ) -> None:
        super().__init__()
        self.status = status
        self.reject_reason = reject_reason

    def submit_order(self, request):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        response = {
            "order_id": "broker-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "side": request.side,
            "notional": str(request.notional),
            "status": self.status,
        }
        if self.reject_reason:
            response["reject_reason"] = self.reject_reason
        return response


class FakeCloseAlpacaClient(FakeAlpacaClient):
    def __init__(
        self,
        *,
        position_qty: str = "0.000132386",
        orders: tuple[dict[str, object], ...] = (),
        status: str = "accepted",
        post_position_qty: str = "",
    ) -> None:
        super().__init__()
        self.position_qty = position_qty
        self.orders = orders
        self.status = status
        self.post_position_qty = post_position_qty

    def get_positions(self) -> list[AlpacaPositionResponse]:
        self.calls.append("get_positions")
        qty = self.post_position_qty if self.submitted_requests else self.position_qty
        if not qty:
            return []
        return [
            AlpacaPositionResponse(
                symbol="BTCUSD",
                qty=Decimal(qty),
                market_value=Decimal("9.78"),
                average_entry_price=Decimal("73886.11"),
            )
        ]

    def get_orders(self, query=None):  # noqa: ANN001
        self.calls.append("get_orders")
        return list(self.orders)

    def submit_order(self, request):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        return {
            "order_id": "broker-close-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "side": request.side,
            "qty": str(request.qty),
            "status": self.status,
        }


class FakeTraceabilityAlpacaClient(FakeAlpacaClient):
    def __init__(self) -> None:
        super().__init__()
        self.recent_order_queries: list[AlpacaRecentOrderQuery] = []

    def get_positions(self) -> list[AlpacaPositionResponse]:
        self.calls.append("get_positions")
        return [
            AlpacaPositionResponse(
                symbol="SPY",
                qty=Decimal("0.032905647"),
                market_value=Decimal("25.00"),
                average_entry_price=Decimal("759.748"),
            )
        ]

    def get_orders(
        self,
        query: AlpacaRecentOrderQuery,
    ) -> list[AlpacaOrderResponse]:
        self.calls.append("get_orders")
        self.recent_order_queries.append(query)
        if query.status_filter == "open":
            return []

        observed_at = datetime(2026, 6, 1, 18, 30, tzinfo=UTC)
        return [
            AlpacaOrderResponse(
                order_id="broker-spy-order-1",
                client_order_id="paper-order-probe-m351_spy_tiny_paper_probe",
                symbol="SPY",
                side="buy",
                status="OrderStatus.FILLED",
                qty=Decimal("0.032905647"),
                notional=Decimal("25.00"),
                asset_class="equity",
                order_type="market",
                time_in_force="day",
                created_at=observed_at,
                submitted_at=observed_at,
                filled_at=observed_at,
                filled_qty=Decimal("0.032905647"),
                filled_avg_price=Decimal("759.748"),
            )
        ]


class FakeSpyClosePreviewAlpacaClient(FakeAlpacaClient):
    def __init__(self, *, open_order_count: int = 0) -> None:
        super().__init__()
        self.open_order_count = open_order_count
        self.recent_order_queries: list[AlpacaRecentOrderQuery] = []

    def get_account(self) -> AlpacaAccountResponse:
        self.calls.append("get_account")
        return AlpacaAccountResponse(
            account_id="paper-account-1",
            status="ACTIVE",
            cash=Decimal("1974.9"),
            buying_power=Decimal("1974.9"),
            equity=Decimal("1999.9"),
        )

    def get_positions(self) -> list[AlpacaPositionResponse]:
        self.calls.append("get_positions")
        return [
            AlpacaPositionResponse(
                symbol="SPY",
                qty=Decimal("0.032905647"),
                market_value=Decimal("25.00"),
                average_entry_price=Decimal("759.748"),
            )
        ]

    def get_orders(
        self,
        query: AlpacaRecentOrderQuery,
    ) -> list[AlpacaOrderResponse]:
        self.calls.append("get_orders")
        self.recent_order_queries.append(query)
        if self.open_order_count == 0:
            return []

        observed_at = datetime(2026, 6, 1, 19, 30, tzinfo=UTC)
        return [
            AlpacaOrderResponse(
                order_id=f"open-spy-order-{index}",
                client_order_id=f"open-spy-order-{index}",
                symbol="SPY",
                side="sell",
                status="OrderStatus.ACCEPTED",
                qty=Decimal("0.032905647"),
                asset_class="equity",
                order_type="market",
                time_in_force="day",
                created_at=observed_at,
                submitted_at=observed_at,
            )
            for index in range(self.open_order_count)
        ]


class FakeSpyCloseSubmitAlpacaClient(FakeAlpacaClient):
    def __init__(
        self,
        *,
        position_qty: str = M376_SPY_CLOSE_QUANTITY,
        post_position_qty: str = M376_SPY_CLOSE_QUANTITY,
        pre_orders: dict[str, tuple[AlpacaOrderResponse, ...]] | None = None,
        status: str = "accepted",
        raise_on_submit: bool = False,
    ) -> None:
        super().__init__()
        self.position_qty = position_qty
        self.post_position_qty = post_position_qty
        self.pre_orders = pre_orders or {}
        self.status = status
        self.raise_on_submit = raise_on_submit
        self.recent_order_queries: list[AlpacaRecentOrderQuery] = []

    def get_account(self) -> AlpacaAccountResponse:
        self.calls.append("get_account")
        return AlpacaAccountResponse(
            account_id="paper-account-1",
            status="ACTIVE",
            cash=Decimal("1974.9"),
            buying_power=Decimal("1974.9"),
            equity=Decimal("1999.9"),
        )

    def get_positions(self) -> list[AlpacaPositionResponse]:
        self.calls.append("get_positions")
        qty = self.post_position_qty if self.submitted_requests else self.position_qty
        if not qty:
            return []
        return [
            AlpacaPositionResponse(
                symbol="SPY",
                qty=Decimal(qty),
                market_value=Decimal("25.00"),
                average_entry_price=Decimal("753.646"),
            )
        ]

    def get_orders(
        self,
        query: AlpacaRecentOrderQuery,
    ) -> list[AlpacaOrderResponse]:
        self.calls.append("get_orders")
        self.recent_order_queries.append(query)
        if not self.submitted_requests:
            return list(self.pre_orders.get(query.status_filter, ()))

        order = _spy_close_order_response(
            M376_SPY_CLOSE_CLIENT_ORDER_ID,
            order_id="broker-spy-close-order-1",
            side="sell",
            status=self.status,
        )
        if query.status_filter == "open" and self.status != "filled":
            return [order]
        if query.status_filter == "closed" and self.status == "filled":
            return [order]
        if query.status_filter == "all":
            return [order]
        return []

    def submit_order(self, request):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        if self.raise_on_submit:
            raise RuntimeError(f"{SENSITIVE_API_KEY} submit failed locally")
        return {
            "order_id": "broker-spy-close-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "side": request.side,
            "qty": str(request.qty),
            "status": self.status,
        }


class FakeMalformedAlpacaClient(FakeAlpacaClient):
    def submit_order(self, request):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        return {
            "order_id": "broker-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "side": request.side,
            "status": "accepted",
        }


class FailingSubmitAlpacaClient(FakeAlpacaClient):
    def submit_order(self, request):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        raise RuntimeError(f"{SENSITIVE_API_KEY} submit failed locally")


class FailingApiErrorAlpacaClient(FakeAlpacaClient):
    def submit_order(self, request):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        raise AlpacaSdkClientError(
            "submit_call_failed_before_response",
            request,
            APIError(
                f"invalid crypto order at {API_ERROR_URL} "
                f"token={SENSITIVE_SECRET_KEY}"
            ),
        )


def _install_fake_broker(
    monkeypatch,
    fake_client: FakeAlpacaClient | None = None,
) -> FakeAlpacaClient:
    fake_client = fake_client or FakeAlpacaClient()

    def build_broker(paper_config):  # noqa: ANN001
        return AlpacaPaperBroker(
            adapter=AlpacaClientAdapter(fake_client),
            config=paper_config,
        )

    monkeypatch.setattr(cli_module, "_build_paper_broker", build_broker)
    return fake_client


def _expected_broker_result(
    normalized_status: str,
    *,
    accepted: bool = True,
    raw_reason: str = "",
    raw_status: str | None = None,
    reason: str = "",
) -> dict[str, object]:
    return {
        "accepted": accepted,
        "normalized_status": normalized_status,
        "raw_reason": raw_reason,
        "raw_status": raw_status if raw_status is not None else normalized_status,
        "reason": reason,
    }


def _forbid_broker_build(monkeypatch) -> None:
    def forbidden_build(paper_config):  # noqa: ANN001
        raise AssertionError("paper order preview must not build a broker")

    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_build)


def _run_json(argv: tuple[str, ...], capsys) -> tuple[int, dict[str, object]]:
    output = _run_raw_json(argv, capsys)
    return _LAST_EXIT_CODE, json.loads(output)


def _run_raw_json(argv: tuple[str, ...], capsys) -> str:
    global _LAST_EXIT_CODE
    _LAST_EXIT_CODE = main(argv)
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out.strip()


def _read_jsonl(path) -> list[dict[str, object]]:  # noqa: ANN001
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_m353_traceability_log(tmp_path):  # noqa: ANN001
    source_traceability_log = tmp_path / "m353_spy_order_traceability_review.jsonl"
    record = {
        "account": {"cash": "1974.9", "currency": "USD"},
        "account_observation_available": True,
        "asset_class": "equity",
        "broker_order_id_exposed": True,
        "client_order_id_exposed": True,
        "command": "paper-lab-order-traceability-review",
        "error": "",
        "event_type": "paper_lab_order_traceability_reviewed",
        "filled_spy_order": {
            "asset_class": "us_equity",
            "client_order_id": "paper-order-probe-m351_spy_tiny_paper_probe",
            "filled_at": "2026-06-01T18:48:14.890443+00:00",
            "normalized_status": "filled",
            "order_id": "broker-spy-order-1",
            "order_type": "market",
            "side": "buy",
            "symbol": "SPY",
            "time_in_force": "day",
        },
        "filled_spy_order_found": True,
        "m351_correlation_basis": "client_order_id",
        "mutated": False,
        "ok": True,
        "order_traceability_observation_available": True,
        "position_count": 1,
        "position_symbols": ["SPY"],
        "positions": [
            {
                "average_price": "759.748",
                "quantity": "0.032905647",
                "symbol": "SPY",
            }
        ],
        "positions_observation_available": True,
        "recent_all_order_count": 1,
        "recent_closed_order_count": 1,
        "recent_filled_order_count": 1,
        "recent_open_order_count": 0,
        "recent_order_query_metadata_complete": True,
        "redaction": "credentials_redacted",
        "review_state": "ready_for_spy_paper_cleanup_preview_milestone",
        "run_id": "m353_spy_order_traceability_review",
        "side": "buy",
        "source_m351_evidence_available": True,
        "source_m351_reference": {
            "client_order_id": "paper-order-probe-m351_spy_tiny_paper_probe",
            "submitted": True,
        },
        "source_m352_evidence_available": True,
        "spy_average_price": "759.748",
        "spy_position_observed": True,
        "spy_quantity": "0.032905647",
        "submitted": False,
        "symbol": "SPY",
        "traceability_gap": "",
    }
    source_traceability_log.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return source_traceability_log


def _write_m354_spy_close_preview_log(tmp_path, **overrides):  # noqa: ANN001
    m354_log = tmp_path / "m354_spy_cleanup_close_preview.jsonl"
    record = {
        "asset_class": "equity",
        "broker_action_performed": False,
        "close_order_submitted": False,
        "command": "paper-lab-spy-close-preview",
        "event_type": "paper_lab_spy_close_preview_reviewed",
        "live_authorized": False,
        "mutated": False,
        "ok": True,
        "order_type": "market",
        "paper_lab_only": True,
        "preview_only": True,
        "requested_close_quantity": "0.032905647",
        "run_id": "m354_spy_cleanup_close_preview",
        "side": "sell",
        "state": "ready_for_separate_spy_paper_close_submit_milestone",
        "submitted": False,
        "symbol": "SPY",
        "time_in_force": "day",
    }
    record.update(overrides)
    m354_log.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return m354_log


def _write_m375c_spy_close_preview_log(tmp_path, **overrides):  # noqa: ANN001
    close_preview_log = (
        tmp_path / "m375c_spy_position_close_preview_fresh_paper.jsonl"
    )
    record = {
        "account": {"cash": "1974.8", "currency": "USD"},
        "account_observation_available": True,
        "asset_class": "equity",
        "blockers": [],
        "broker_action_performed": False,
        "broker_mutation_authorized": False,
        "close_intent_preview": {
            "asset_class": "equity",
            "notional": None,
            "order_type": "market",
            "quantity": M376_SPY_CLOSE_QUANTITY,
            "required_next_milestone": (
                "M376 - Explicit operator-reviewed SPY paper close submit"
            ),
            "side": "sell",
            "source_position_milestone": "M370C",
            "source_reconciliation_milestone": "M374",
            "submit_authorized": False,
            "symbol": "SPY",
            "time_in_force": "day",
        },
        "close_intent_preview_available": True,
        "close_order_submitted": False,
        "close_preview_only": True,
        "close_submit_authorized": False,
        "command": "etf-sma-m375-spy-close-preview",
        "expected_m370c_filled_quantity": M376_SPY_CLOSE_QUANTITY,
        "live_authorized": False,
        "milestone": "M375",
        "mutated": False,
        "not_live_authorized": True,
        "observed_spy_quantity": M376_SPY_CLOSE_QUANTITY,
        "ok": True,
        "order_type": "market",
        "paper_lab_only": True,
        "paper_only": True,
        "preview_only": True,
        "profit_claim": "none",
        "readiness_classification": (
            "ready_for_separate_spy_close_submit_milestone"
        ),
        "run_id": "m375c_spy_position_close_preview_fresh_paper",
        "side": "sell",
        "source_position_milestone": "M370C",
        "source_reconciliation_milestone": "M374",
        "submitted": False,
        "symbol": "SPY",
        "time_in_force": "day",
    }
    record.update(overrides)
    close_preview_log.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return close_preview_log


def _spy_close_order_response(
    client_order_id: str,
    *,
    order_id: str = "broker-spy-order-1",
    side: str = "sell",
    status: str = "accepted",
) -> AlpacaOrderResponse:
    observed_at = datetime(2026, 6, 1, 20, 30, tzinfo=UTC)
    return AlpacaOrderResponse(
        order_id=order_id,
        client_order_id=client_order_id,
        symbol="SPY",
        side=side,
        status=status,
        qty=Decimal(M376_SPY_CLOSE_QUANTITY),
        asset_class="equity",
        order_type="market",
        time_in_force="day",
        created_at=observed_at,
        submitted_at=observed_at,
        filled_at=observed_at if status == "filled" else None,
        filled_qty=Decimal(M376_SPY_CLOSE_QUANTITY) if status == "filled" else None,
        filled_avg_price=Decimal("753.646") if status == "filled" else None,
    )


def _write_traceability_source_logs(tmp_path):  # noqa: ANN001
    source_order_log = tmp_path / "m351_spy_tiny_paper_probe.jsonl"
    source_snapshot_log = tmp_path / "m352_spy_settlement_review_snapshot.jsonl"
    m351_record = {
        "accepted": True,
        "asset_class": "equity",
        "client_order_id": "paper-order-probe-m351_spy_tiny_paper_probe",
        "command": "paper-order-probe",
        "event_type": "paper_order_receipt_observed",
        "filled": False,
        "normalized_status": "pending_new",
        "notional": "25.00",
        "order_type": "market",
        "raw_status": "OrderStatus.PENDING_NEW",
        "redaction": "credentials_redacted",
        "run_id": "m351_spy_tiny_paper_probe",
        "side": "buy",
        "submitted": True,
        "symbol": "SPY",
        "time_in_force": "day",
    }
    m352_positions = {
        "command": "paper-lab-snapshot",
        "event_type": "paper_lab_snapshot_positions_observed",
        "mutated": False,
        "position_count": 1,
        "position_symbols": ["SPY"],
        "positions": [
            {
                "average_price": "759.748",
                "quantity": "0.032905647",
                "symbol": "SPY",
            }
        ],
        "redaction": "credentials_redacted",
        "run_id": "m352_spy_settlement_review_snapshot",
        "submitted": False,
    }
    m352_orders = {
        "command": "paper-lab-snapshot",
        "event_type": "paper_lab_snapshot_orders_observed",
        "mutated": False,
        "recent_order_count": 0,
        "recent_orders": [],
        "redaction": "credentials_redacted",
        "run_id": "m352_spy_settlement_review_snapshot",
        "submitted": False,
    }
    source_order_log.write_text(
        json.dumps(m351_record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    source_snapshot_log.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in (m352_positions, m352_orders)
        ),
        encoding="utf-8",
    )
    return source_order_log, source_snapshot_log


def _write_revalidation_snapshot_run_log(path) -> None:  # noqa: ANN001
    records = [
        {
            "command": "paper-lab-snapshot",
            "event_type": "paper_lab_snapshot_requested",
            "redaction": "credentials_redacted",
            "run_id": "snapshot-run",
        },
        {
            "account": {"cash": "100000", "currency": "USD"},
            "command": "paper-lab-snapshot",
            "event_type": "paper_lab_snapshot_account_observed",
            "redaction": "credentials_redacted",
            "run_id": "snapshot-run",
        },
        {
            "command": "paper-lab-snapshot",
            "event_type": "paper_lab_snapshot_positions_observed",
            "position_count": 1,
            "position_symbols": ["MSFT"],
            "redaction": "credentials_redacted",
            "run_id": "snapshot-run",
        },
        {
            "command": "paper-lab-snapshot",
            "event_type": "paper_lab_snapshot_orders_observed",
            "recent_order_count": 1,
            "recent_orders": [
                {
                    "asset_class": "equity",
                    "normalized_status": "accepted",
                    "raw_status": "OrderStatus.ACCEPTED",
                    "side": "buy",
                    "symbol": "SPY",
                }
            ],
            "redaction": "credentials_redacted",
            "run_id": "snapshot-run",
        },
    ]
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _write_revalidation_m319_submit_run_log(path) -> None:  # noqa: ANN001
    order_fields = {
        "accepted": True,
        "asset_class": "crypto",
        "broker_response_parsed": True,
        "broker_response_received": True,
        "client_order_id": "paper-order-probe-m319",
        "command": "paper-order-probe",
        "filled": False,
        "max_notional": "10.00",
        "min_notional": "10.00",
        "normalized_status": "pending_new",
        "notional": "10.00",
        "order_type": "market",
        "raw_reason": "",
        "raw_status": "OrderStatus.PENDING_NEW",
        "redaction": "credentials_redacted",
        "side": "buy",
        "submitted": True,
        "submit_requested": True,
        "symbol": "BTCUSD",
        "time_in_force": "gtc",
    }
    position = {
        "average_price": "73886.11",
        "quantity": "0.000132386",
        "symbol": "BTCUSD",
    }
    records = [
        *_revalidation_snapshot_records(
            run_id="m319-pre-submit",
            cash="2000",
            position_count=0,
            position_symbols=[],
            positions=[],
            recent_order_count=0,
            recent_orders=[],
        ),
        {
            **order_fields,
            "event_type": "paper_order_submit_attempted",
            "run_id": "m319-probe",
            "submit_attempted": True,
        },
        {
            **order_fields,
            "event_type": "paper_order_receipt_observed",
            "run_id": "m319-probe",
            "submit_attempted": True,
        },
        {
            **order_fields,
            "account": {"cash": "1990.19", "currency": "USD"},
            "event_type": "paper_order_post_submit_account_observed",
            "position_count": 1,
            "positions": [position],
            "run_id": "m319-probe",
            "submit_attempted": True,
        },
        *_revalidation_snapshot_records(
            run_id="m319-post-submit",
            cash="1990.19",
            position_count=1,
            position_symbols=["BTCUSD"],
            positions=[position],
            recent_order_count=0,
            recent_orders=[],
        ),
    ]
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _write_close_preview_fresh_snapshot_run_log(path) -> None:  # noqa: ANN001
    position = {
        "average_price": "73886.11",
        "quantity": "0.000132386",
        "symbol": "BTCUSD",
    }
    base = {
        "account_observation_available": True,
        "command": "paper-lab-snapshot",
        "gate_summary": {
            "profile_gate": {"detail": "paper_profile_ready", "passed": True}
        },
        "mutated": False,
        "ok": True,
        "orders_observation_available": True,
        "positions_observation_available": True,
        "redaction": "credentials_redacted",
        "run_id": "m324-fresh-read-only",
        "submitted": False,
        "unavailable_observations": [],
        "unavailable_reasons": {},
        "recent_order_query_after": None,
        "recent_order_query_asset_class_filter": "",
        "recent_order_query_attempted": True,
        "recent_order_query_available": True,
        "recent_order_query_contract_version": "paper_recent_order_query_v1",
        "recent_order_query_direction": "desc",
        "recent_order_query_limit": 100,
        "recent_order_query_metadata_complete": True,
        "recent_order_query_metadata_missing_fields": [],
        "recent_order_query_nested": False,
        "recent_order_query_returned_count": 0,
        "recent_order_query_side_filter": "",
        "recent_order_query_sort": "",
        "recent_order_query_source": "alpaca_sdk_client.get_orders",
        "recent_order_query_status_filter": "open",
        "recent_order_query_symbol_filter": "",
        "recent_order_query_until": None,
    }
    records = [
        {
            **base,
            "event_type": "paper_lab_snapshot_requested",
        },
        {
            **base,
            "account": {"cash": "1990.19", "currency": "USD"},
            "event_type": "paper_lab_snapshot_account_observed",
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_positions_observed",
            "position_count": 1,
            "position_symbols": ["BTCUSD"],
            "positions": [position],
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_orders_observed",
            "recent_order_count": 0,
            "recent_orders": [],
        },
    ]
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _append_jsonl_records(
    path,  # noqa: ANN001
    records: tuple[dict[str, object], ...],
) -> None:
    with path.open("a", encoding="utf-8") as stream:
        for record in records:
            stream.write(
                json.dumps(record, sort_keys=True, separators=(",", ":"))
                + "\n"
            )


def _revalidation_close_preview_records() -> tuple[dict[str, object], ...]:
    payload = build_btcusd_paper_close_preview_contract(
        observed_position_quantity="0.000132386",
        requested_close_quantity="0.000132386",
        fresh_snapshot_status="read_only_snapshot_completed_for_manual_review",
        recent_order_query_metadata_complete=True,
        source_mutated=False,
        source_submitted=False,
    ).to_payload()
    return make_paper_close_preview_events(
        run_id="m325-close-preview",
        payload=payload,
    )


def _revalidation_snapshot_records(
    *,
    run_id: str,
    cash: str,
    position_count: int,
    position_symbols: list[str],
    positions: list[dict[str, object]],
    recent_order_count: int,
    recent_orders: list[dict[str, object]],
) -> tuple[dict[str, object], ...]:
    base = {
        "command": "paper-lab-snapshot",
        "redaction": "credentials_redacted",
        "run_id": run_id,
    }
    return (
        {
            **base,
            "event_type": "paper_lab_snapshot_requested",
        },
        {
            **base,
            "account": {"cash": cash, "currency": "USD"},
            "event_type": "paper_lab_snapshot_account_observed",
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_positions_observed",
            "position_count": position_count,
            "position_symbols": position_symbols,
            "positions": positions,
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_orders_observed",
            "recent_order_count": recent_order_count,
            "recent_orders": recent_orders,
        },
    )


_LAST_EXIT_CODE = 0
