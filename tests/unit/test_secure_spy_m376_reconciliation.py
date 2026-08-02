from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from algotrader.execution import secure_spy_m376_reconciliation as secure_m376
from algotrader.execution.secure_credential_provider import (
    CredentialFamily,
    CredentialReference,
    lease_from_test_record,
)
from algotrader.execution.secure_spy_m376_reconciliation import (
    M376_BROKER_ORDER_ID,
    M376_CLIENT_ORDER_ID,
    SCHEMA_VERSION,
    SecureM376ReconciliationConfig,
    exit_status,
    run_secure_m376_reconciliation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "run_secure_spy_m376_reconciliation.ps1"
REFERENCE = CredentialReference(
    "wincred:algotrader/v5.35/alpaca-paper-observation/offline-test"
)
KEY = "offline-m376-key-value"
SECRET = "offline-m376-secret-value"
ACCOUNT = "offline-m376-account-value"
CLOCK = lambda: datetime(2026, 8, 2, 22, 0, tzinfo=UTC)


class RecordingProvider:
    provider_name = "windows-credential-manager"

    def __init__(self) -> None:
        self.opens = 0

    def open(self, reference, *, expected_family):  # noqa: ANN001
        self.opens += 1
        assert str(reference) == str(REFERENCE)
        assert expected_family is CredentialFamily.ALPACA_PAPER_OBSERVATION
        return lease_from_test_record(
            {
                "schema_version": "v5_35_credential_record_v1",
                "family": "alpaca-paper-observation",
                "api_key_id": KEY,
                "api_secret_key": SECRET,
                "expected_account_id": ACCOUNT,
            },
            reference=REFERENCE,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )


class FakeClient:
    def __init__(
        self,
        _config,  # noqa: ANN001
        *,
        status="filled",
        account_id=ACCOUNT,
        open_orders=(),  # noqa: ANN001
    ):
        self.status = status
        self.account_id = account_id
        self.open_orders = tuple(open_orders)
        self.calls: list[str] = []

    def get_account(self):  # noqa: ANN201
        self.calls.append("account")
        return SimpleNamespace(id=self.account_id, status="ACTIVE")

    def get_positions(self):  # noqa: ANN201
        self.calls.append("positions")
        return (SimpleNamespace(symbol="SPY", qty=Decimal("0.033172072")),)

    def get_orders(self, query):  # noqa: ANN001, ANN201
        self.calls.append("open_orders")
        assert query.status_filter == "open"
        assert query.limit == 100
        assert query.symbol_filter == "SPY"
        return self.open_orders

    def get_order_by_id(self, order_id):  # noqa: ANN001, ANN201
        self.calls.append("exact_order")
        assert order_id == M376_BROKER_ORDER_ID
        filled = Decimal("0.033172072") if self.status == "filled" else Decimal("0")
        return SimpleNamespace(
            id=M376_BROKER_ORDER_ID,
            client_order_id=M376_CLIENT_ORDER_ID,
            symbol="SPY",
            side=SimpleNamespace(value="sell"),
            status=SimpleNamespace(value=self.status),
            qty=Decimal("0.033172072"),
            filled_qty=filled,
            filled_avg_price=Decimal("550") if self.status == "filled" else None,
            submitted_at=datetime(2026, 7, 1, 14, 0, tzinfo=UTC),
            filled_at=(
                datetime(2026, 7, 1, 14, 1, tzinfo=UTC)
                if self.status == "filled"
                else None
            ),
        )


def config(tmp_path: Path) -> SecureM376ReconciliationConfig:
    return SecureM376ReconciliationConfig(
        output_root=tmp_path / "receipts",
        reconciliation_log_path=tmp_path / "m376.jsonl",
        paper_credential_reference=REFERENCE,
    )


def test_terminal_exact_order_is_account_bound_and_secret_free(tmp_path: Path) -> None:
    clients: list[FakeClient] = []

    def factory(value):  # noqa: ANN001, ANN202
        client = FakeClient(value)
        clients.append(client)
        return client

    receipt = run_secure_m376_reconciliation(
        config(tmp_path), env={}, credential_provider=RecordingProvider(),
        client_factory=factory, clock=CLOCK,
    )

    assert receipt["schema_version"] == SCHEMA_VERSION
    assert receipt["state"] == "m376_terminal_reconciled"
    assert receipt["expected_account_matched"] is True
    assert receipt["paper_broker_read_attempted"] is True
    assert receipt["paper_broker_read_performed"] is True
    assert receipt["open_spy_order_read_attempted"] is True
    assert receipt["open_spy_order_read_performed"] is True
    assert receipt["paper_submit_performed"] is False
    assert receipt["broker_mutation_performed"] is False
    assert receipt["live_authorized"] is False
    detail = receipt["reconciliation"]
    assert detail["reconciliation_decision"] == "m376_terminal_filled"
    assert detail["terminal_state"] == "terminal"
    assert detail["open_order_count"] == 0
    assert detail["next_spy_submit_blocked"] is False
    assert clients[0].calls == ["account", "positions", "open_orders", "exact_order"]
    assert exit_status(receipt) == 0
    persisted = (tmp_path / "receipts" / "latest_receipt.json").read_text(encoding="utf-8")
    reconciliation = (tmp_path / "m376.jsonl").read_text(encoding="utf-8")
    for value in (KEY, SECRET, ACCOUNT):
        assert value not in json.dumps(receipt)
        assert value not in persisted
        assert value not in reconciliation


def test_default_client_receives_explicit_paper_interlock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def factory(value, *, interlock_env):  # noqa: ANN001, ANN202
        captured["interlock_env"] = dict(interlock_env)
        return FakeClient(value)

    monkeypatch.setattr(secure_m376, "AlpacaSdkClient", factory)
    receipt = run_secure_m376_reconciliation(
        config(tmp_path), env={}, credential_provider=RecordingProvider(),
        clock=CLOCK,
    )

    assert receipt["state"] == "m376_terminal_reconciled"
    interlock = captured["interlock_env"]
    assert isinstance(interlock, dict)
    assert interlock["APP_PROFILE"] == "paper"
    assert interlock["ALPACA_PAPER_BASE_URL"] == "https://paper-api.alpaca.markets"
    assert interlock["EXPECTED_PAPER_ACCOUNT_ID"] == ACCOUNT
    for value in (KEY, SECRET, ACCOUNT):
        assert value not in json.dumps(receipt)


def test_nonterminal_exact_order_remains_blocked(tmp_path: Path) -> None:
    receipt = run_secure_m376_reconciliation(
        config(tmp_path), env={}, credential_provider=RecordingProvider(),
        client_factory=lambda value: FakeClient(value, status="accepted"),
        clock=CLOCK,
    )

    assert receipt["state"] == "m376_nonterminal_blocked"
    assert receipt["reconciliation"]["reconciliation_decision"] == "m376_nonterminal_open"
    assert receipt["reconciliation"]["next_spy_submit_blocked"] is True
    assert "m376_order_nonterminal" in receipt["blockers"]
    assert receipt["paper_submit_performed"] is False
    assert exit_status(receipt) == 2


def test_other_open_spy_order_keeps_context_blocked(tmp_path: Path) -> None:
    other_open = SimpleNamespace(
        id="other-open-order",
        client_order_id="other-open-client-order",
        symbol="SPY",
        side=SimpleNamespace(value="buy"),
        status=SimpleNamespace(value="accepted"),
        qty=Decimal("0.01"),
        filled_qty=Decimal("0"),
        submitted_at=datetime(2026, 8, 2, 21, 59, tzinfo=UTC),
    )
    receipt = run_secure_m376_reconciliation(
        config(tmp_path),
        env={},
        credential_provider=RecordingProvider(),
        client_factory=lambda value: FakeClient(
            value,
            open_orders=(other_open,),
        ),
        clock=CLOCK,
    )

    assert receipt["state"] == "m376_terminal_context_blocked"
    detail = receipt["reconciliation"]
    assert detail["reconciliation_decision"] == "m376_terminal_filled"
    assert detail["open_order_count"] == 1
    assert detail["next_spy_submit_blocked"] is True
    assert "open_order_present" in receipt["blockers"]
    assert exit_status(receipt) == 2

def test_failed_open_order_read_reports_completed_account_read(
    tmp_path: Path,
) -> None:
    clients: list[FakeClient] = []

    class FailingOpenOrdersClient(FakeClient):
        def get_orders(self, query):  # noqa: ANN001, ANN201
            self.calls.append("open_orders")
            assert query.status_filter == "open"
            raise RuntimeError("offline_open_order_read_failure")

    def factory(value):  # noqa: ANN001, ANN202
        client = FailingOpenOrdersClient(value)
        clients.append(client)
        return client

    receipt = run_secure_m376_reconciliation(
        config(tmp_path),
        env={},
        credential_provider=RecordingProvider(),
        client_factory=factory,
        clock=CLOCK,
    )

    assert receipt["state"] == "blocked_paper_read"
    assert receipt["paper_broker_read_attempted"] is True
    assert receipt["paper_broker_read_performed"] is True
    assert receipt["open_spy_order_read_attempted"] is True
    assert receipt["open_spy_order_read_performed"] is False
    assert receipt["blockers"] == ["paper_read_failed:RuntimeError"]
    assert receipt["paper_submit_performed"] is False
    assert receipt["broker_mutation_performed"] is False
    assert clients[0].calls == ["account", "positions", "open_orders"]
    assert exit_status(receipt) == 2
    persisted = (tmp_path / "receipts" / "latest_receipt.json").read_text(
        encoding="utf-8"
    )
    for value in (KEY, SECRET, ACCOUNT):
        assert value not in persisted

def test_account_mismatch_fails_before_order_read(tmp_path: Path) -> None:
    clients: list[FakeClient] = []

    def factory(value):  # noqa: ANN001, ANN202
        client = FakeClient(value, account_id="different-account")
        clients.append(client)
        return client

    receipt = run_secure_m376_reconciliation(
        config(tmp_path), env={}, credential_provider=RecordingProvider(),
        client_factory=factory, clock=CLOCK,
    )

    assert receipt["state"] == "blocked_expected_account"
    assert clients[0].calls == ["account"]
    assert receipt["paper_submit_performed"] is False
    assert ACCOUNT not in json.dumps(receipt)


def test_forbidden_environment_fails_before_credential_access(tmp_path: Path) -> None:
    provider = RecordingProvider()
    receipt = run_secure_m376_reconciliation(
        config(tmp_path), env={"APP_PROFILE": "paper"},
        credential_provider=provider, client_factory=FakeClient, clock=CLOCK,
    )

    assert receipt["state"] == "blocked_secure_preflight"
    assert receipt["credential_access_attempted"] is False
    assert receipt["paper_broker_read_attempted"] is False
    assert receipt["paper_broker_read_performed"] is False
    assert receipt["open_spy_order_read_attempted"] is False
    assert provider.opens == 0


def test_powershell_wrapper_contract_and_forwarding(tmp_path: Path) -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for fragment in (
        "exact account-bound, read-only M376",
        "windows-credential-manager",
        "alpaca-paper-observation/production",
        "preflight_exact_order_id_read=true",
        "preflight_open_spy_order_read=true",
        "preflight_paper_mutation_authorized=false",
        "preflight_live_authorized=false",
        "algotrader.execution.secure_spy_m376_reconciliation",
    ):
        assert fragment in text

    capture = tmp_path / "args.txt"
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n>> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo state=m376_terminal_reconciled\r\nexit /B 0\r\n",
        encoding="utf-8", newline="",
    )
    env = os.environ.copy()
    for name in (
        "APP_PROFILE", "ALPACA_API_KEY", "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY", "ALPACA_SECRET_KEY", "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY", "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
        "ALPACA_PAPER_ACCOUNT_ID", "APCA_EXPECTED_PAPER_ACCOUNT_ID",
        "EXPECTED_PAPER_ACCOUNT_ID",
        "ALPACA_PAPER_BASE_URL", "ALPACA_BASE_URL", "ALPACA_LIVE_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        env.pop(name, None)
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture)
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required for wrapper verification")
    result = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
         "-OutputRoot", str(tmp_path / "receipts"),
         "-ReconciliationLogPath", str(tmp_path / "m376.jsonl"), "-Format", "text"],
        cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "preflight_forbidden_environment_variables_loaded=0" in result.stdout
    assert "preflight_paper_mutation_authorized=false" in result.stdout
    args = capture.read_text(encoding="utf-8")
    assert "-m algotrader.execution.secure_spy_m376_reconciliation" in args
    assert "--output-root" in args
    assert "--reconciliation-log-path" in args