from __future__ import annotations

from pathlib import Path

import algotrader.cli as cli_module


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
        "OutputRoot",
        "PythonExecutable",
        "ReceiptOut",
        "ReceiptTextOut",
        "ValidationOut",
        "ValidationTextOut",
    ):
        assert f"${parameter_name}" in script

    assert '[string]$DailySoakDir = "runs/daily_soak"' in script
    assert '[string]$OutputRoot = ""' in script
    assert '[string]$PythonExecutable = "python"' in script
    assert "-StartDate" in script
    assert "-EndDate" in script
    assert "-BarsCsv" in script
    assert "-ReconciliationStatePath" in script
    assert "-OutputRoot" in script


def test_daily_lab_closeout_script_preserves_default_paths_and_output_root_override() -> None:
    script = _script_text()

    assert '[string]$DailySoakDir = "runs/daily_soak"' in script
    assert '[string]$OutputRoot = ""' in script
    assert 'if (-not [string]::IsNullOrWhiteSpace($OutputRoot))' in script
    assert "$DailySoakDir = $OutputRoot" in script

    for artifact_variable in (
        "$HistoryIndexPath",
        "$OperatorSummaryPath",
        "$OperatorSummaryTextPath",
        "$CloseoutPacketPath",
        "$CloseoutPacketTextPath",
        "$ReceiptOut",
        "$ReceiptTextOut",
        "$ValidationOut",
        "$ValidationTextOut",
    ):
        assert artifact_variable in script

    assert 'Join-Path $DailySoakDir "v3j_daily_soak_acceptance_history_index.jsonl"' in script
    assert 'Join-Path $DailySoakDir "v3k_daily_soak_operator_summary.jsonl"' in script
    assert 'Join-Path $DailySoakDir "v3k_daily_soak_operator_summary.md"' in script
    assert 'Join-Path $DailySoakDir "v3l_daily_soak_closeout_packet.jsonl"' in script
    assert 'Join-Path $DailySoakDir "v3l_daily_soak_closeout_packet.md"' in script
    assert 'Join-Path $DailySoakDir "v3n_daily_lab_closeout_run_receipt.jsonl"' in script
    assert 'Join-Path $DailySoakDir "v3n_daily_lab_closeout_run_receipt.md"' in script
    assert 'Join-Path $DailySoakDir "v3o_daily_lab_closeout_bundle_validation.jsonl"' in script
    assert 'Join-Path $DailySoakDir "v3o_daily_lab_closeout_bundle_validation.md"' in script


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


def test_daily_lab_closeout_script_preserves_fail_fast_but_attempts_receipt_and_validation() -> None:
    script = _script_text()

    assert "$AnyFailed = $true" in script
    assert 'status = "skipped"' in script
    assert script.index("# Step 2: V3J history index") < script.index(
        "# Now build the receipt!"
    )
    assert script.index("# Now build the receipt!") < script.index(
        "# Now run the bundle validator!"
    )
    assert "New-Item -ItemType Directory -Path $DailySoakDirFsPath -Force | Out-Null" in script
    assert "exit $FailedExitCode" in script


def test_standalone_closeout_cli_default_paths_are_preserved() -> None:
    parser = cli_module.build_parser()

    golden_args = parser.parse_args(["etf-sma-daily-soak-golden-check"])
    assert golden_args.output_root == "runs/daily_soak"
    assert golden_args.output_jsonl == "runs/daily_soak/soak_golden_acceptance.jsonl"
    assert golden_args.output_text == "runs/daily_soak/soak_golden_acceptance.txt"

    history_args = parser.parse_args(["etf-sma-daily-soak-acceptance-history-index"])
    assert history_args.daily_soak_dir == "runs/daily_soak"
    assert history_args.out == "runs/daily_soak/v3j_daily_soak_acceptance_history_index.jsonl"

    summary_args = parser.parse_args(["etf-sma-daily-soak-operator-summary"])
    assert summary_args.history_index == (
        "runs/daily_soak/v3j_daily_soak_acceptance_history_index.jsonl"
    )
    assert summary_args.out == "runs/daily_soak/v3k_daily_soak_operator_summary.jsonl"

    packet_args = parser.parse_args(["etf-sma-daily-soak-closeout-packet"])
    assert packet_args.history_index == (
        "runs/daily_soak/v3j_daily_soak_acceptance_history_index.jsonl"
    )
    assert packet_args.operator_summary == (
        "runs/daily_soak/v3k_daily_soak_operator_summary.jsonl"
    )
    assert packet_args.operator_summary_md == (
        "runs/daily_soak/v3k_daily_soak_operator_summary.md"
    )
    assert packet_args.out == "runs/daily_soak/v3l_daily_soak_closeout_packet.jsonl"
    assert packet_args.text_out == "runs/daily_soak/v3l_daily_soak_closeout_packet.md"

    validation_args = parser.parse_args(
        ["etf-sma-daily-soak-closeout-bundle-validate"]
    )
    assert validation_args.daily_soak_dir == "runs/daily_soak"
    assert validation_args.validation_out == (
        "runs/daily_soak/v3o_daily_lab_closeout_bundle_validation.jsonl"
    )
    assert validation_args.validation_text_out == (
        "runs/daily_soak/v3o_daily_lab_closeout_bundle_validation.md"
    )


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
