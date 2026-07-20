<#
.SYNOPSIS
Wrapper for running crypto paper broker observation with process-scoped env loading.
#>

[CmdletBinding()]
param(
    [string]$ReceiptRoot = "runs/v5_34_r2_observation/latest",
    [switch]$BrokerObservedReadiness,
    [switch]$AllowAlpacaPaperRead
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
    (Join-Path $PSScriptRoot "run_crypto_paper_broker_observation.ps1"),
    "-ReceiptRoot", $ReceiptRoot
)
if ($BrokerObservedReadiness.IsPresent) { $Arguments += "-BrokerObservedReadiness" }
if ($AllowAlpacaPaperRead.IsPresent) { $Arguments += "-AllowAlpacaPaperRead" }

Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    powershell -File @Arguments
}
finally {
    Pop-Location
}
