<#
.SYNOPSIS
Runs the bounded Alpaca paper account baseline cleanup wrapper.

.DESCRIPTION
Loads process-scoped local environment variables via scripts/dev/load_env.ps1
and invokes the paper account cleanup module.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_34_paper_cleanup\latest",
    [switch]$PaperCleanupAuthorized,
    [switch]$AllowNetwork
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
    "algotrader.execution.crypto_paper_account_cleanup",
    "--output-root",
    $OutputRoot
)

if ($PaperCleanupAuthorized.IsPresent) {
    $Arguments += @("--paper-cleanup-authorized")
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
