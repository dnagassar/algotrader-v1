from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT_SCRIPT = PROJECT_ROOT / "scripts" / "run_daily_lab_closeout.ps1"


def test_daily_lab_closeout_script_exists() -> None:
    assert CLOSEOUT_SCRIPT.exists()


def test_daily_lab_closeout_script_declares_strict_fail_fast_contract() -> None:
    script = _script_text()

    assert "Set-StrictMode -Version Latest" in script
    assert '$ErrorActionPreference = "Stop"' in script
    assert "$LASTEXITCODE" in script
    assert "exit $FailedExitCode" in script
    assert "$AnyFailed" in script


def test_daily_lab_closeout_script_invokes_closeout_sequence_in_order() -> None:
    script = _script_text()

    expected_sequence = (
        "scripts/run_daily_lab_acceptance.ps1",
        "etf-sma-daily-soak-acceptance-history-index",
        "etf-sma-daily-soak-operator-summary",
        "etf-sma-daily-soak-closeout-packet",
        "etf-sma-daily-soak-closeout-receipt",
        "etf-sma-daily-soak-closeout-bundle-validate",
    )

    positions = [script.index(command) for command in expected_sequence]
    assert positions == sorted(positions)


def test_daily_lab_closeout_script_supports_operator_parameters() -> None:
    script = _script_text()

    for parameter_name in (
        "StartDate",
        "EndDate",
        "BarsCsv",
        "ReconciliationStatePath",
        "DailySoakDir",
        "PythonExecutable",
        "ReceiptOut",
        "ReceiptTextOut",
        "ValidationOut",
        "ValidationTextOut",
    ):
        assert f"${parameter_name}" in script

    assert '[string]$DailySoakDir = "runs/daily_soak"' in script
    assert '[string]$PythonExecutable = "python"' in script
    assert "-StartDate" in script
    assert "-EndDate" in script
    assert "-BarsCsv" in script
    assert "-ReconciliationStatePath" in script
    assert "-OutputRoot" in script


def test_daily_lab_closeout_script_uses_deterministic_artifact_names() -> None:
    script = _script_text()

    for artifact_name in (
        "v3j_daily_soak_acceptance_history_index.jsonl",
        "v3k_daily_soak_operator_summary.jsonl",
        "v3k_daily_soak_operator_summary.md",
        "v3l_daily_soak_closeout_packet.jsonl",
        "v3l_daily_soak_closeout_packet.md",
        "v3n_daily_lab_closeout_run_receipt.jsonl",
        "v3n_daily_lab_closeout_run_receipt.md",
        "v3o_daily_lab_closeout_bundle_validation.jsonl",
        "v3o_daily_lab_closeout_bundle_validation.md",
    ):
        assert artifact_name in script

    assert "--daily-soak-dir" in script
    assert "--history-index" in script
    assert "--operator-summary" in script
    assert "--operator-summary-md" in script
    assert "--text-out" in script
    assert "--steps-json" in script
    assert "--receipt-out" in script
    assert "--receipt-text-out" in script
    assert "--validation-out" in script
    assert "--validation-text-out" in script


def test_daily_lab_closeout_script_suppresses_child_artifact_stdout() -> None:
    script = _script_text()

    assert "Steps" + "Json:" not in script
    assert "Steps " + "count" not in script
    assert "Write-" + "Output" not in script
    assert "Steps" + "Json" not in script
    assert "$StepRecordsJson" in script
    assert script.count("1> $null") == 6
    assert "& $PythonExecutable @ReceiptArgs 1> $null" in script


def test_daily_lab_closeout_script_has_no_credential_loading_or_printing() -> None:
    script = _script_text()
    normalized = script.lower()

    for forbidden in (
        ".env",
        "load_env",
        "alpaca_api_key",
        "alpaca_api_secret_key",
        "alpaca_secret_key",
        "apca_api_key_id",
        "apca_api_secret_key",
        "getenvironmentvariable",
        "getenvironmentvariables",
    ):
        assert forbidden not in normalized


def test_daily_lab_closeout_script_has_no_broker_mutation_tokens() -> None:
    script = _script_text()
    normalized = script.lower()

    for forbidden in (
        "submit_order",
        "cancel_order",
        "replace_order",
        "close_position",
        "close_all",
        "close_all_positions",
        "liquidate",
        "liquidation",
        "delete_order",
        "paper_submit",
        "paper-submit",
        "broker_mutation",
    ):
        assert forbidden not in normalized


def _script_text() -> str:
    return CLOSEOUT_SCRIPT.read_text(encoding="utf-8")
