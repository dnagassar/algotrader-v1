<#
.SYNOPSIS
Builds one sealed, authority-free V5.30 lifecycle plan.

.DESCRIPTION
This command is credential-free, network-free, broker-free, and mutation-free.
It exports terminal evidence at most once, pins those exact bytes, and writes a
compact canonical lifecycle plan plus a non-authorizing request artifact.
#>

[CmdletBinding()]
param(
    [string]$ShadowRoot = (
        "runs\crypto_strategy_tournament\v2\forward_shadow\latest"
    ),
    [string]$OutputRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_lifecycle"
    ),
    [string]$VenueOrderabilityPath = (
        "runs\crypto_universe_refresh\paper_read_latest\crypto_orderability_metadata.json"
    ),
    [string]$VenueRuntimeVisibilityPath = (
        "runs\crypto_paper_visibility\latest\latest_status.json"
    ),
    [string]$SafetyKernelSourcePath = (
        "src\algotrader\execution\crypto_bounded_probe_safety.py"
    ),
    [string]$SafetyCertifierSourcePath = (
        "src\algotrader\execution\crypto_bounded_probe_safety_certification.py"
    ),
    [string]$SafetyFocusedTestSourcePath = (
        "tests\unit\test_crypto_bounded_probe_safety.py"
    ),
    [string]$SafetyCertificationReceiptPath = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_capabilities\safety_certification_receipt.json"
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Test-ProcessEnvironmentVariableLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name, "Process")
    return -not [string]::IsNullOrWhiteSpace($Value)
}

$AppProfile = [Environment]::GetEnvironmentVariable(
    "APP_PROFILE",
    "Process"
)
if (-not [string]::IsNullOrWhiteSpace($AppProfile)) {
    $NormalizedProfile = $AppProfile.Trim().ToLowerInvariant()
    if ($NormalizedProfile -in @("paper", "live")) {
        throw (
            "Sealed lifecycle planning is offline only; " +
            "APP_PROFILE=paper or live is not allowed."
        )
    }
}

foreach ($Name in @(
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)) {
    if (Test-ProcessEnvironmentVariableLoaded -Name $Name) {
        throw "Sealed lifecycle planning requires a credential-free process."
    }
}

foreach ($Name in @(
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS"
)) {
    if (Test-ProcessEnvironmentVariableLoaded -Name $Name) {
        throw "Sealed lifecycle planning rejects network-test flags."
    }
}

foreach ($Name in @(
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL"
)) {
    $Endpoint = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (
        -not [string]::IsNullOrWhiteSpace($Endpoint) -and
        $Endpoint.ToLowerInvariant().Contains("api.alpaca.markets") -and
        -not $Endpoint.ToLowerInvariant().Contains("paper")
    ) {
        throw "Sealed lifecycle planning rejects live endpoint indicators."
    }
}

Write-Host "crypto_tournament_v2_lifecycle_planner_offline=true"
Write-Host "credential_values_exposed=false"
Write-Host "network_access_attempted=false"
Write-Host "broker_read_occurred=false"
Write-Host "broker_mutation_occurred=false"
Write-Host "paper_mutation_authorized=false"
Write-Host "capital_allocation_authorized=false"
Write-Host "live_authorized=false"

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    throw "Unable to locate python on PATH."
}
$RepoRoot = (
    Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
).Path
$Arguments = @(
    "-m",
    (
        "algotrader.orchestration." +
        "crypto_tournament_v2_bounded_paper_probe_lifecycle"
    ),
    "--shadow-root",
    $ShadowRoot,
    "--output-root",
    $OutputRoot,
    "--venue-orderability-path",
    $VenueOrderabilityPath,
    "--venue-runtime-visibility-path",
    $VenueRuntimeVisibilityPath,
    "--safety-kernel-source-path",
    $SafetyKernelSourcePath,
    "--safety-certifier-source-path",
    $SafetyCertifierSourcePath,
    "--safety-focused-test-source-path",
    $SafetyFocusedTestSourcePath,
    "--safety-certification-receipt-path",
    $SafetyCertificationReceiptPath
)

Push-Location -LiteralPath $RepoRoot
try {
    & $PythonCommand.Source @Arguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
