from __future__ import annotations

import json
from decimal import Decimal

import pytest
import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.alpaca_client import AlpacaOrderRequest
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClientError
from algotrader.execution.paper_order_policy import OPTIONS_SUBMIT_DISABLED_REASON
from tests.fakes.alpaca import FakeAlpacaClient


SENSITIVE_API_KEY = "paper-lab-sensitive-api-key"
SENSITIVE_SECRET_KEY = "paper-lab-sensitive-secret-key"
API_ERROR_URL = "https://paper.example.test/v2/orders"


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
        _valid_probe_args(max_notional="10.01"),
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
