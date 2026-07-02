<#
.SYNOPSIS
Runs the official SPY daily visibility cycle in no-submit mode.

.DESCRIPTION
Runs the existing SPY paper supervisor through the accepted daily bars
validation path and enforces visibility/no-submit mode. The command may observe
a verified Alpaca paper profile, but it must not submit paper orders, mutate a
broker, authorize live trading, print credentials, or store credential values.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\spy_daily_visibility\latest",
    [string]$HistoryRoot = "runs\spy_daily_visibility\history",
    [string]$BarsCsv = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$RunDate,
    [string]$Symbol = "SPY",
    [int]$SmaFastWindow = 50,
    [int]$SmaSlowWindow = 200,
    [string]$MaxNotional = "25.00",
    [switch]$NoSubmit,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$SupervisorScript = Join-Path $PSScriptRoot "run_spy_paper_mutation_supervisor.ps1"

function Get-CurrentPowerShellPath {
    $CurrentProcess = [System.Diagnostics.Process]::GetCurrentProcess()
    if ($null -ne $CurrentProcess.MainModule -and -not [string]::IsNullOrEmpty($CurrentProcess.MainModule.FileName)) {
        return $CurrentProcess.MainModule.FileName
    }
    $PwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($null -ne $PwshCommand) {
        return $PwshCommand.Source
    }
    $WindowsPowerShellCommand = Get-Command powershell -ErrorAction SilentlyContinue
    if ($null -ne $WindowsPowerShellCommand) {
        return $WindowsPowerShellCommand.Source
    }
    throw "Unable to locate a PowerShell executable for the SPY daily visibility cycle."
}

Write-Host "visibility_cycle_command=run_spy_daily_visibility_cycle"
Write-Host "visibility_cycle_operating_mode=visibility/no_submit"
Write-Host "visibility_cycle_no_submit_requested=$($NoSubmit.IsPresent.ToString().ToLowerInvariant())"
Write-Host "visibility_cycle_no_submit_enforced=true"
Write-Host "visibility_cycle_data_path=accepted_daily_bars_validation"
Write-Host "visibility_cycle_broker_state_not_observed_blocker=blocked/broker_state_not_observed"
Write-Host "visibility_cycle_broker_state_not_observed_next_operator_action=configure_verified_paper_profile_then_rerun"
Write-Host "visibility_cycle_broker_mutation_performed=false"
Write-Host "visibility_cycle_paper_submit_performed=false"
Write-Host "visibility_cycle_live_mutation_performed=false"

$SupervisorArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $SupervisorScript,
    "-OutputRoot", $OutputRoot,
    "-HistoryRoot", $HistoryRoot,
    "-BarsCsv", $BarsCsv,
    "-Symbol", $Symbol,
    "-SmaFastWindow", $SmaFastWindow.ToString(),
    "-SmaSlowWindow", $SmaSlowWindow.ToString(),
    "-MaxNotional", $MaxNotional,
    "-Format", $Format,
    "-NoSubmit"
)

if (-not [string]::IsNullOrEmpty($AsOfDate)) {
    $SupervisorArgs += @("-AsOfDate", $AsOfDate)
}

if (-not [string]::IsNullOrEmpty($RunDate)) {
    $SupervisorArgs += @("-RunDate", $RunDate)
}

$PowerShellExe = Get-CurrentPowerShellPath

Push-Location -LiteralPath $RepoRoot
try {
    & $PowerShellExe @SupervisorArgs
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}

exit $ExitCode
