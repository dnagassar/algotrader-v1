from __future__ import annotations

import json

import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from tests.fakes.alpaca import FakeAlpacaClient


SENSITIVE_API_KEY = "paper-lab-sensitive-api-key"
SENSITIVE_SECRET_KEY = "paper-lab-sensitive-secret-key"


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
        "client_order_id": "paper-order-probe-preview-only",
        "limit_price": "",
        "order_type": "market",
        "qty": "1",
        "request_model": "AlpacaOrderRequest",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }


def test_order_probe_submit_flag_refuses_until_true_notional_cap_support_exists(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json((*_valid_probe_args(), "--submit"), capsys)

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "submit_confirmation_gate_failed"
    assert payload["gates"]["submit_confirmation_gate"] == {
        "detail": "submission_disabled_until_true_notional_cap_is_supported",
        "passed": False,
    }
    assert (
        payload["submission_disabled_reason"]
        == "submission_disabled_until_true_notional_cap_is_supported"
    )


def test_order_probe_i_mean_it_flag_refuses_without_submission(
    monkeypatch,
    capsys,
) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json((*_valid_probe_args(), "--i-mean-it"), capsys)

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "submit_confirmation_gate_failed"
    assert payload["gates"]["submit_confirmation_gate"]["passed"] is False


def test_order_probe_halt_blocks_preview(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    monkeypatch.setenv("ALGOTRADER_PAPER_HALT", "1")
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(_valid_probe_args(), capsys)

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

    exit_code, payload = _run_json(_valid_probe_args(), capsys)

    assert exit_code == 2
    assert payload["submitted"] is False
    assert payload["error"] == "profile_gate_failed"
    assert payload["gates"]["profile_gate"]["passed"] is False


def test_order_probe_rejects_non_allowlisted_symbol(monkeypatch, capsys) -> None:
    _set_env(monkeypatch)
    _forbid_broker_build(monkeypatch)

    exit_code, payload = _run_json(
        _valid_probe_args(symbol="AAPL"),
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

    exit_code, payload = _run_json(_valid_probe_args(side="sell"), capsys)

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


def _set_env(monkeypatch, *, profile: str = "paper") -> None:
    monkeypatch.setenv("APP_PROFILE", profile)
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_API_KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SENSITIVE_SECRET_KEY)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper.example.test")
    monkeypatch.delenv("ALGOTRADER_PAPER_HALT", raising=False)


def _install_fake_broker(monkeypatch) -> FakeAlpacaClient:
    fake_client = FakeAlpacaClient()

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
