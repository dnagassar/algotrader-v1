from __future__ import annotations

import json
from decimal import Decimal

import pytest
import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.alpaca_client import AlpacaOrderRequest
from tests.fakes.alpaca import FakeAlpacaClient


SENSITIVE_API_KEY = "paper-lab-sensitive-api-key"
SENSITIVE_SECRET_KEY = "paper-lab-sensitive-secret-key"


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
    assert payload["ok"] is True
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["proposed_order_request"] == {
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
    assert payload["ok"] is True
    assert payload["preview_only"] is True
    assert payload["submitted"] is False
    assert payload["requested_notional"] == "5"
    assert payload["max_notional"] == "10"
    assert payload["proposed_order_request"] == {
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
    assert first_payload["preview_only"] is False
    assert first_payload["submit_requested"] is True
    assert first_payload["submit_attempted"] is True
    assert first_payload["broker_response_received"] is True
    assert first_payload["broker_response_parsed"] is True
    assert first_payload["submitted"] is True
    assert first_payload["accepted"] is True
    assert first_payload["filled"] is False
    assert first_payload["broker_result"] == {"accepted": True, "reason": ""}


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


def _set_env(monkeypatch, *, profile: str = "paper") -> None:
    monkeypatch.setenv("APP_PROFILE", profile)
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_API_KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SENSITIVE_SECRET_KEY)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper.example.test")
    monkeypatch.delenv("ALGOTRADER_PAPER_HALT", raising=False)


class FakeNotionalAlpacaClient(FakeAlpacaClient):
    def submit_order(self, request):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        return {
            "order_id": "broker-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "side": request.side,
            "notional": str(request.notional),
            "status": "accepted",
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


_LAST_EXIT_CODE = 0
