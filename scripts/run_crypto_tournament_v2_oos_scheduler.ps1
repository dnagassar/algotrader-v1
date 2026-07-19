<#
.SYNOPSIS
Runs the deterministic tournament-v2 forward-OOS scheduler.

.DESCRIPTION
Supports preview, run_once, status, and recover_stale modes.
It scrubs credentials and other sensitive environment variables for credential-free modes.
#>

[CmdletBinding()]
param(
    [ValidateSet("preview", "run_once", "status", "recover_stale", "reset_failed")]
    [string]$Mode = "preview",
    [string]$OutputRoot = "runs\crypto_strategy_tournament\v2\latest",
    [string]$DiscoverySourcePath = "runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv",
    [string]$DiscoveryReceiptPath = "runs\crypto_strategy_tournament\v1\refresh\refresh_packet.json",
    [string]$DbPath = "",
    [switch]$SchedulerEnabled,
    [switch]$MarketDataReadAuthorized,
    [switch]$AllowNetwork,
    [string]$AsOf = "",
    [string]$JobId = "",
    [switch]$ResetAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

# Validate Mode-specific flag bounds
if ($Mode -eq "run_once") {
    if (-not $SchedulerEnabled.IsPresent -or -not $MarketDataReadAuthorized.IsPresent -or -not $AllowNetwork.IsPresent) {
        throw "Mode run_once requires -SchedulerEnabled, -MarketDataReadAuthorized, and -AllowNetwork switches."
    }
} elseif ($Mode -eq "reset_failed") {
    if ([string]::IsNullOrWhiteSpace($JobId)) {
        throw "Mode reset_failed requires -JobId."
    }
    if (-not $ResetAuthorized.IsPresent) {
        throw "Mode reset_failed requires -ResetAuthorized switch."
    }
} else {
    if ($SchedulerEnabled.IsPresent -or $MarketDataReadAuthorized.IsPresent -or $AllowNetwork.IsPresent -or $ResetAuthorized.IsPresent) {
        throw "Authorization switches require Mode run_once or reset_failed."
    }
}

# Env scrubbing for credential-free modes
if ($Mode -ne "run_once") {
    $ScrubbedVariableNames = @(
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
        "ALPACA_PAPER_ACCOUNT_ID",
        "APCA_EXPECTED_PAPER_ACCOUNT_ID",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "PYTEST_ADDOPTS",
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONINSPECT",
        "PYTHONUSERBASE",
        "PYTHONBREAKPOINT",
        "PYTHONPYCACHEPREFIX"
    )
    foreach ($Name in $ScrubbedVariableNames) {
        [Environment]::SetEnvironmentVariable($Name, $null, "Process")
    }
}

# Resolve python
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    throw "Unable to locate python on PATH."
}

$Arguments = @(
    "-m",
    "algotrader.orchestration.crypto_tournament_v2_oos_scheduler",
    "--mode",
    $Mode,
    "--output-root",
    $OutputRoot,
    "--discovery-source-path",
    $DiscoverySourcePath,
    "--discovery-receipt-path",
    $DiscoveryReceiptPath
)

if (-not [string]::IsNullOrWhiteSpace($DbPath)) {
    $Arguments += @("--db-path", $DbPath)
}
if (-not [string]::IsNullOrWhiteSpace($AsOf)) {
    $Arguments += @("--as-of", $AsOf)
}
if ($SchedulerEnabled.IsPresent) {
    $Arguments += @("--scheduler-enabled")
}
if ($MarketDataReadAuthorized.IsPresent) {
    $Arguments += @("--market-data-read-authorized")
}
if ($AllowNetwork.IsPresent) {
    $Arguments += @("--allow-network")
}
if (-not [string]::IsNullOrWhiteSpace($JobId)) {
    $Arguments += @("--job-id", $JobId)
}
if ($ResetAuthorized.IsPresent) {
    $Arguments += @("--reset-authorized")
}

$ExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    & $PythonCommand.Source @Arguments
    $ExitCode = $LASTEXITCODE
}
catch {
    $ExitCode = 1
    throw
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
