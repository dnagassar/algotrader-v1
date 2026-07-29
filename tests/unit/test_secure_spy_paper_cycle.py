from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.secure_credential_provider import (
    CredentialFamily,
    CredentialReference,
    lease_from_test_record,
)
from algotrader.execution.paper_autopilot_loop import _account_payload
from algotrader.execution.secure_spy_paper_cycle import (
    SECURE_SPY_PAPER_CYCLE_SCHEMA_VERSION,
    SecureSpyPaperCycleConfig,
    run_secure_spy_paper_cycle,
    secure_spy_paper_cycle_exit_status,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_SCRIPT = PROJECT_ROOT / "scripts" / "run_secure_spy_paper_cycle.ps1"
REGISTER_SCRIPT = (
    PROJECT_ROOT / "scripts" / "register_secure_spy_paper_cycle_task.ps1"
)
TASK_XML = (
    PROJECT_ROOT / "docs" / "design" / "secure_spy_paper_cycle_task.xml"
)
REFERENCE = CredentialReference(
    "wincred:algotrader/v5.35/alpaca-paper-observation/offline-test"
)
KEY = "offline-paper-key-value"
SECRET = "offline-paper-secret-value"
ACCOUNT = "offline-paper-account-value"
OPEN_CLOCK = lambda: datetime(2026, 7, 29, 13, 31, tzinfo=UTC)
OUTSIDE_CLOCK = lambda: datetime(2026, 7, 29, 23, 0, tzinfo=UTC)
NAMESPACE = {"task": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


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


class TwoPhaseOperator:
    def __init__(
        self,
        *,
        preview_kind: str = "mutation",
        execution_kind: str = "reconciled",
    ) -> None:
        self.preview_kind = preview_kind
        self.execution_kind = execution_kind
        self.calls = []

    def __call__(self, config, **kwargs):  # noqa: ANN001
        env = kwargs["env"]
        assert env["APP_PROFILE"] == "paper"
        assert env["APCA_API_KEY_ID"] == KEY
        assert env["APCA_API_SECRET_KEY"] == SECRET
        assert env["ALPACA_EXPECTED_PAPER_ACCOUNT_ID"] == ACCOUNT
        assert env["ALPACA_PAPER_BASE_URL"] == "https://paper-api.alpaca.markets"
        self.calls.append(config)
        if config.no_submit:
            return self._preview(config)
        return self._execution(config)

    def _preview(self, config):  # noqa: ANN001
        if self.preview_kind == "hold":
            return {
                "operator_summary": {
                    "classification": "healthy_hold_noop",
                    "hard_stop": False,
                    "attention_required": False,
                    "operator_exit_code": 0,
                    "execution_plan_action": "hold",
                    "broker_read_performed": True,
                    "broker_state_observed": True,
                    "expected_account_matched": True,
                    "selected_strategy_id": "etf_sma_training_wheel",
                    "paper_submit_performed": False,
                    "broker_mutation_performed": False,
                    "live_mutation_performed": False,
                }
            }
        if self.preview_kind == "blocked":
            return {
                "operator_summary": {
                    "classification": "data_freshness_blocked",
                    "hard_stop": False,
                    "attention_required": True,
                    "operator_exit_code": 1,
                    "blocker_status": "blocked/stale_data_preview_only",
                    "execution_plan_action": "buy",
                    "broker_read_performed": True,
                    "broker_state_observed": True,
                    "expected_account_matched": True,
                    "paper_submit_performed": False,
                    "broker_mutation_performed": False,
                    "live_mutation_performed": False,
                }
            }
        packet_path = Path(config.history_root) / "readiness.json"
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text('{"ready":true}\n', encoding="utf-8")
        return {
            "operator_summary": {
                "classification": "mutation_would_be_required_no_submit_mode",
                "autonomy_status": (
                    "paper_mutation_would_be_required_no_submit_mode"
                ),
                "readiness_status": "readiness_blocked_no_submit_mode",
                "readiness_packet_generated": True,
                "paper_mutation_readiness_packet": str(packet_path),
                "hard_stop": False,
                "attention_required": True,
                "operator_exit_code": 1,
                "blocker_status": (
                    "blocked/mutation_would_be_required_no_submit_mode"
                ),
                "execution_plan_action": "buy",
                "broker_read_performed": True,
                "broker_state_observed": True,
                "expected_account_matched": True,
                "selected_strategy_id": "etf_sma_training_wheel",
                "paper_submit_performed": False,
                "broker_mutation_performed": False,
                "live_mutation_performed": False,
            }
        }

    def _execution(self, config):  # noqa: ANN001
        assert Path(config.readiness_packet_path).is_file()
        if self.execution_kind == "revalidated_hold":
            return {
                "operator_summary": {
                    "classification": "healthy_hold_noop",
                    "hard_stop": False,
                    "attention_required": False,
                    "operator_exit_code": 0,
                    "execution_plan_action": "hold",
                    "broker_read_performed": True,
                    "broker_state_observed": True,
                    "expected_account_matched": True,
                    "paper_submit_performed": False,
                    "broker_mutation_performed": False,
                    "live_mutation_performed": False,
                }
            }
        if self.execution_kind == "unreconciled":
            return {
                "operator_summary": {
                    "classification": "reconciliation_required",
                    "hard_stop": False,
                    "attention_required": True,
                    "operator_exit_code": 1,
                    "blocker_status": "blocked/reconciliation_required",
                    "execution_plan_action": "buy",
                    "broker_read_performed": True,
                    "broker_state_observed": True,
                    "expected_account_matched": True,
                    "paper_submit_performed": True,
                    "broker_mutation_performed": True,
                    "live_mutation_performed": False,
                    "reconciliation_status": "reconciliation_required",
                }
            }
        return {
            "operator_summary": {
                "classification": "healthy_paper_action_reconciled",
                "hard_stop": False,
                "attention_required": False,
                "operator_exit_code": 0,
                "blocker_status": "action/submitted",
                "execution_plan_action": "buy",
                "broker_read_performed": True,
                "broker_state_observed": True,
                "expected_account_matched": True,
                "paper_mutation_readiness_packet_consumed": True,
                "paper_mutation_readiness_gate_status": "passed",
                "paper_submit_performed": True,
                "broker_mutation_performed": True,
                "live_mutation_performed": False,
                "reconciliation_status": "reconciled_terminal_filled",
            }
        }


def _config(
    tmp_path: Path,
    *,
    allow_paper_mutation: bool,
) -> SecureSpyPaperCycleConfig:
    tmp_path.mkdir(parents=True, exist_ok=True)
    bars_csv = tmp_path / "bars.csv"
    bars_csv.write_text("date,symbol,close\n2026-07-28,SPY,100\n", encoding="utf-8")
    return SecureSpyPaperCycleConfig(
        output_root=tmp_path / "out",
        bars_csv=bars_csv,
        order_journal_path=tmp_path / "journal.sqlite3",
        paper_credential_reference=REFERENCE,
        max_notional="25.00",
        allow_paper_mutation=allow_paper_mutation,
    )


def test_config_enforces_fixed_spy_and_finite_25_dollar_cap(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cannot exceed 25.00"):
        SecureSpyPaperCycleConfig(
            output_root=tmp_path,
            bars_csv=tmp_path / "bars.csv",
            order_journal_path=tmp_path / "journal.sqlite3",
            paper_credential_reference=REFERENCE,
            max_notional="25.01",
        )
    with pytest.raises(ValidationError, match="positive and finite"):
        SecureSpyPaperCycleConfig(
            output_root=tmp_path,
            bars_csv=tmp_path / "bars.csv",
            order_journal_path=tmp_path / "journal.sqlite3",
            paper_credential_reference=REFERENCE,
            max_notional=Decimal("NaN"),
        )
    with pytest.raises(ValidationError, match="restricted to SPY"):
        SecureSpyPaperCycleConfig(
            output_root=tmp_path,
            bars_csv=tmp_path / "bars.csv",
            order_journal_path=tmp_path / "journal.sqlite3",
            paper_credential_reference=REFERENCE,
            symbol="AAPL",
        )


def test_native_paper_account_flags_derive_tradable_without_unsafe_default() -> None:
    safe = _account_payload(
        SimpleNamespace(
            status="ACTIVE",
            trading_blocked=False,
            account_blocked=False,
            trade_suspended_by_user=False,
            currency="USD",
            cash="1000",
            buying_power="1000",
            equity="1000",
            last_equity="1000",
        )
    )
    assert safe["tradable"] is True
    assert safe["trading_blocked"] is False

    blocked = _account_payload(
        SimpleNamespace(
            status="ACTIVE",
            trading_blocked=False,
            account_blocked=True,
            trade_suspended_by_user=False,
        )
    )
    assert blocked["tradable"] is None
    assert blocked["trading_blocked"] is True


def test_loaded_process_credentials_block_before_provider_or_operator(
    tmp_path: Path,
) -> None:
    provider = RecordingProvider()
    operator = TwoPhaseOperator()

    receipt = run_secure_spy_paper_cycle(
        _config(tmp_path, allow_paper_mutation=False),
        env={"APCA_API_KEY_ID": "must-not-be-used"},
        credential_provider=provider,
        operator_runner=operator,
        clock=OPEN_CLOCK,
    )

    assert receipt["state"] == "blocked_secure_preflight"
    assert receipt["credential_access_attempted"] is False
    assert provider.opens == 0
    assert operator.calls == []
    assert "must-not-be-used" not in json.dumps(receipt)


def test_visibility_pass_returns_ready_without_mutation_or_secret_persistence(
    tmp_path: Path,
) -> None:
    provider = RecordingProvider()
    operator = TwoPhaseOperator()

    receipt = run_secure_spy_paper_cycle(
        _config(tmp_path, allow_paper_mutation=False),
        env={},
        credential_provider=provider,
        operator_runner=operator,
        clock=OUTSIDE_CLOCK,
    )

    assert receipt["schema_version"] == SECURE_SPY_PAPER_CYCLE_SCHEMA_VERSION
    assert receipt["state"] == "ready_no_submit"
    assert provider.opens == 1
    assert len(operator.calls) == 1
    assert operator.calls[0].no_submit is True
    assert receipt["paper_submit_performed"] is False
    assert receipt["broker_mutation_performed"] is False
    assert receipt["live_authorized"] is False
    serialized = json.dumps(receipt)
    for value in (KEY, SECRET, ACCOUNT):
        assert value not in serialized


def test_explicit_mutation_runs_two_phase_reobservation_and_reconciliation(
    tmp_path: Path,
) -> None:
    provider = RecordingProvider()
    operator = TwoPhaseOperator()

    receipt = run_secure_spy_paper_cycle(
        _config(tmp_path, allow_paper_mutation=True),
        env={},
        credential_provider=provider,
        operator_runner=operator,
        clock=OPEN_CLOCK,
    )

    assert receipt["state"] == "paper_action_reconciled"
    assert provider.opens == 1
    assert len(operator.calls) == 2
    assert operator.calls[0].no_submit is True
    assert operator.calls[1].no_submit is False
    assert receipt["max_orders_per_cycle"] == 1
    assert receipt["max_order_notional"] == "25.00"
    assert receipt["paper_submit_performed"] is True
    assert receipt["broker_mutation_performed"] is True
    assert receipt["reconciliation_status"] == "reconciled_terminal_filled"
    assert receipt["live_mutation_performed"] is False
    assert secure_spy_paper_cycle_exit_status(receipt) == 0


def test_mutation_outside_next_open_window_fails_before_credential_access(
    tmp_path: Path,
) -> None:
    provider = RecordingProvider()
    operator = TwoPhaseOperator()

    receipt = run_secure_spy_paper_cycle(
        _config(tmp_path, allow_paper_mutation=True),
        env={},
        credential_provider=provider,
        operator_runner=operator,
        clock=OUTSIDE_CLOCK,
    )

    assert receipt["state"] == "blocked_execution_window"
    assert receipt["execution_window"]["eligible"] is False
    assert receipt["credential_access_attempted"] is False
    assert provider.opens == 0
    assert operator.calls == []
    assert secure_spy_paper_cycle_exit_status(receipt) == 2


def test_healthy_hold_never_runs_second_pass(tmp_path: Path) -> None:
    provider = RecordingProvider()
    operator = TwoPhaseOperator(preview_kind="hold")

    receipt = run_secure_spy_paper_cycle(
        _config(tmp_path, allow_paper_mutation=True),
        env={},
        credential_provider=provider,
        operator_runner=operator,
        clock=OPEN_CLOCK,
    )

    assert receipt["state"] == "healthy_no_action"
    assert len(operator.calls) == 1
    assert receipt["paper_submit_performed"] is False
    assert receipt["broker_mutation_performed"] is False


def test_blocked_preview_and_unreconciled_submit_fail_closed(tmp_path: Path) -> None:
    blocked_operator = TwoPhaseOperator(preview_kind="blocked")
    blocked = run_secure_spy_paper_cycle(
        _config(tmp_path / "blocked", allow_paper_mutation=True),
        env={},
        credential_provider=RecordingProvider(),
        operator_runner=blocked_operator,
        clock=OPEN_CLOCK,
    )
    assert blocked["state"] == "blocked_preview"
    assert len(blocked_operator.calls) == 1
    assert blocked["paper_submit_performed"] is False

    unreconciled_operator = TwoPhaseOperator(execution_kind="unreconciled")
    unreconciled = run_secure_spy_paper_cycle(
        _config(tmp_path / "unreconciled", allow_paper_mutation=True),
        env={},
        credential_provider=RecordingProvider(),
        operator_runner=unreconciled_operator,
        clock=OPEN_CLOCK,
    )
    assert unreconciled["state"] == "reconciliation_required"
    assert unreconciled["paper_submit_performed"] is True
    assert unreconciled["broker_mutation_performed"] is True
    assert "paper_action_not_terminally_reconciled" in unreconciled["blockers"]
    assert secure_spy_paper_cycle_exit_status(unreconciled) == 2


def test_runner_script_contract_and_argument_forwarding(tmp_path: Path) -> None:
    text = RUNNER_SCRIPT.read_text(encoding="utf-8")
    for fragment in (
        "one secure, bounded SPY paper operating cycle",
        "windows-credential-manager",
        "alpaca-paper-observation/production",
        "[switch]$AllowPaperMutation",
        "--allow-paper-mutation",
        "preflight_max_orders_per_cycle=1",
        "preflight_live_authorized=false",
    ):
        assert fragment in text

    capture = tmp_path / "args.txt"
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo state=ready_no_submit\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )
    env = os.environ.copy()
    for name in (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
        "ALPACA_PAPER_BASE_URL",
    ):
        env.pop(name, None)
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture)
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUNNER_SCRIPT),
            "-AllowPaperMutation",
            "-Format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    args = capture.read_text(encoding="utf-8")
    assert "-m algotrader.execution.secure_spy_paper_cycle" in args
    assert "--allow-paper-mutation" in args
    assert "--max-notional 25.00" in args
    assert "--credential-provider windows-credential-manager" in args


def test_task_template_is_bounded_next_open_paper_only() -> None:
    root = ET.parse(TASK_XML).getroot()

    assert _xml_text(root, ".//task:URI") == (
        "\\algo-trader-secure-spy-paper-cycle"
    )
    assert _xml_text(root, ".//task:StartBoundary").endswith("09:31:00")
    assert _xml_text(root, ".//task:Interval") == "PT15M"
    assert _xml_text(root, ".//task:Duration") == "PT45M"
    assert _xml_text(root, ".//task:MultipleInstancesPolicy") == "IgnoreNew"
    assert _xml_text(root, ".//task:RunOnlyIfNetworkAvailable") == "true"
    assert _xml_text(root, ".//task:StartWhenAvailable") == "false"
    assert _xml_text(root, ".//task:AllowStartOnDemand") == "false"
    assert _xml_text(root, ".//task:ExecutionTimeLimit") == "PT10M"
    arguments = _xml_text(root, ".//task:Arguments")
    assert "run_secure_spy_paper_cycle.ps1" in arguments
    assert "-AllowPaperMutation" in arguments
    assert '-MaxNotional "25.00"' in arguments
    assert "ALPACA_API_KEY" not in arguments
    assert "ALPACA_SECRET_KEY" not in arguments


def test_registration_helper_defaults_to_non_mutating_preview() -> None:
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REGISTER_SCRIPT),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "task_registration=preview_only" in result.stdout
    assert "task_system_mutation_performed=false" in result.stdout
    assert "task_max_orders_per_cycle=1" in result.stdout
    assert "task_live_authorized=false" in result.stdout


def _xml_text(root: ET.Element, path: str) -> str:
    element = root.find(path, NAMESPACE)
    assert element is not None
    return element.text or ""


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required for wrapper contract verification.")
    return powershell
