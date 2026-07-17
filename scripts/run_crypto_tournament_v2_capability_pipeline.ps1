<#
.SYNOPSIS
Refreshes V5.27 safety certification and candidate-deferred capabilities.

.DESCRIPTION
This single command is credential-free, network-free, broker-free, no-submit,
and no-mutation. It executes the all-symbol local safety certification, then
publishes one immutable capability-production generation. It never authorizes
a paper probe, capital allocation, a live endpoint, or live trading.
#>

[CmdletBinding()]
param(
    [string]$ShadowRoot = (
        "runs\crypto_strategy_tournament\v2\forward_shadow\latest"
    ),
    [string]$CapabilityRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_capabilities\latest"
    ),
    [string]$SafetyReceiptPath = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_capabilities\safety_certification_receipt.json"
    ),
    [string]$AsOf = ((Get-Date).ToUniversalTime().ToString("o"))
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (
    Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
).Path

function Test-EnvLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name, "Process")
    return -not [string]::IsNullOrWhiteSpace($Value)
}

$AppProfile = [Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
$AppProfileNormalized = ""
if (-not [string]::IsNullOrWhiteSpace($AppProfile)) {
    $AppProfileNormalized = $AppProfile.Trim().ToLowerInvariant()
}
if ($AppProfileNormalized -in @("paper", "live")) {
    throw (
        "V5.27 capability pipeline is offline only; " +
        "APP_PROFILE=paper or live is not allowed."
    )
}

foreach ($Name in @(
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)) {
    if (Test-EnvLoaded -Name $Name) {
        throw "V5.27 capability pipeline requires a credential-free process."
    }
}

foreach ($Name in @(
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS"
)) {
    if (Test-EnvLoaded -Name $Name) {
        throw "V5.27 capability pipeline rejects network-test flags."
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
        throw "V5.27 capability pipeline rejects live endpoint indicators."
    }
}

Write-Host "crypto_tournament_v2_capability_pipeline_offline=true"
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

$CertificationArguments = @(
    "-m",
    (
        "algotrader.execution." +
        "crypto_bounded_probe_safety_certification"
    ),
    "--output-path",
    $SafetyReceiptPath,
    "--as-of",
    $AsOf
)
$ProductionArguments = @(
    "-m",
    (
        "algotrader.orchestration." +
        "crypto_tournament_v2_bounded_paper_probe_capability_producer"
    ),
    "--shadow-root",
    $ShadowRoot,
    "--output-root",
    $CapabilityRoot,
    "--safety-certification-receipt-path",
    $SafetyReceiptPath,
    "--as-of",
    $AsOf
)

Push-Location -LiteralPath $RepoRoot
try {
    & $PythonCommand.Source @CertificationArguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    & $PythonCommand.Source @ProductionArguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
exit 0
