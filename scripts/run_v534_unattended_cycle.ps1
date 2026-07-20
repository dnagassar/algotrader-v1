<#
.SYNOPSIS
Runs the V5.34 unattended paper-observed OOS operating cycle wrapper.

.DESCRIPTION
Loads process-scoped local environment variables via scripts/dev/load_env.ps1
and invokes the V5.34 autonomous cycle CLI command.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_34_operating_cycle\latest",
    [string]$SchedulerOutputRoot = "runs\crypto_strategy_tournament\v2\latest",
    [string]$DiscoverySourcePath = "runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv",
    [string]$DiscoveryReceiptPath = "runs\crypto_strategy_tournament\v1\refresh\refresh_packet.json",
    [string]$DbPath = "",
    [switch]$SchedulerEnabled,
    [switch]$MarketDataReadAuthorized,
    [switch]$PaperBrokerReadAuthorized,
    [switch]$AllowNetwork,
    [string]$AsOf = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

# Load process-scoped environment quietly if local or primary .env exists
$EnvFile = Join-Path $RepoRoot ".env"
if (-not (Test-Path -LiteralPath $EnvFile)) {
    $PrimaryEnv = "C:\Users\danie\Desktop\algo_trader\.env"
    if (Test-Path -LiteralPath $PrimaryEnv) {
        $EnvFile = $PrimaryEnv
    }
}
if (Test-Path -LiteralPath $EnvFile) {
    . (Join-Path $PSScriptRoot "dev\load_env.ps1") -Path $EnvFile -Quiet
}

$env:APP_PROFILE = "paper"
if (-not $env:ALPACA_PAPER_BASE_URL) {
    $env:ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"
}
if (-not $env:ALPACA_API_KEY) {
    if ($env:ALPACA_API_KEY_ID) { $env:ALPACA_API_KEY = $env:ALPACA_API_KEY_ID }
    elseif ($env:APCA_API_KEY_ID) { $env:ALPACA_API_KEY = $env:APCA_API_KEY_ID }
}
if (-not $env:ALPACA_SECRET_KEY) {
    if ($env:ALPACA_API_SECRET_KEY) { $env:ALPACA_SECRET_KEY = $env:ALPACA_API_SECRET_KEY }
    elseif ($env:APCA_API_SECRET_KEY) { $env:ALPACA_SECRET_KEY = $env:APCA_API_SECRET_KEY }
}

$Arguments = @(
    "-m",
    "algotrader.cli",
    "v534-unattended-cycle",
    "--output-root",
    $OutputRoot,
    "--scheduler-output-root",
    $SchedulerOutputRoot,
    "--discovery-source",
    $DiscoverySourcePath,
    "--discovery-receipt",
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
if ($PaperBrokerReadAuthorized.IsPresent) {
    $Arguments += @("--paper-broker-read-authorized")
}
if ($AllowNetwork.IsPresent) {
    $Arguments += @("--allow-network")
}

$ExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    python @Arguments
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
