from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_DEVELOPMENT_AUTOPILOT_SCRIPT = (
    PROJECT_ROOT / "scripts" / "run_development_autopilot.ps1"
)


def test_run_development_autopilot_script_preserves_launcher_contract() -> None:
    script = RUN_DEVELOPMENT_AUTOPILOT_SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "[string]$OutputRoot = \"runs/development_autopilot\"",
        "[string]$WorkOrderPath",
        "[string]$ExpectedHead",
        "[string]$AgentRoute = \"codex\"",
        "[string]$AgentCommand",
        "[ValidateSet(\"verify_only\", \"commit_only\", \"commit_and_push\")]",
        "[string]$GitMode = \"verify_only\"",
        "[ValidateRange(1, 7200)]",
        "[int]$CommandTimeoutSeconds = 1800",
        "[ValidateSet(\"always\", \"changed_files_only\")]",
        "[string]$FullPytestPolicy = \"always\"",
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "Test-ProcessEnvironmentVariableLoaded",
        "Development autopilot must run offline only without paper profile",
        "\"-m\", \"algotrader.cli\"",
        "\"development-autopilot\"",
        "\"--output-root\", $AbsoluteOutputRoot",
        "\"--work-order-path\", $WorkOrderPath",
        "\"--expected-head\", $ExpectedHead",
        "\"--agent-route\", $AgentRoute",
        "\"--agent-command\", $AgentCommand",
        "\"--git-mode\", $GitMode",
        "\"--command-timeout-seconds\", $CommandTimeoutSeconds.ToString()",
        "\"--full-pytest-policy\", $FullPytestPolicy",
        "Development autopilot completed.",
        "Latest run summary: $LatestRunPath",
        "Report: $ReportPath",
        "Next action packet: $NextActionPath",
        "Verify-only default: true",
        "Paper submit authorized: false",
        "Live authorized: false",
        "Broker read performed: false",
        "Broker mutation performed: false",
    )
    for fragment in expected_fragments:
        assert fragment in script


def test_run_development_autopilot_script_propagates_python_exit_code() -> None:
    script = RUN_DEVELOPMENT_AUTOPILOT_SCRIPT.read_text(encoding="utf-8")

    python_call_index = script.index("& python @CliArgs")
    capture_index = script.index("$ExitCode = $LASTEXITCODE")
    final_exit_index = script.rindex("exit $ExitCode")

    assert python_call_index < capture_index < final_exit_index
    assert "exit 0" not in script
