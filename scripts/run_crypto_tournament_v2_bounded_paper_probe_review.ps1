<#
.SYNOPSIS
Builds the offline tournament-v2 bounded-paper-probe review packet.

.DESCRIPTION
This command is credential-free, network-free, broker-free, no-submit, and
no-mutation. Its strongest result is eligibility for a separate exact operator
review; it never authorizes a paper probe, capital allocation, or live trading.
#>

[CmdletBinding()]
param(
    [string]$ShadowRoot = (
        "runs\crypto_strategy_tournament\v2\forward_shadow\latest"
    ),
    [string]$CapabilityRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_capabilities\latest"
    ),
    [string]$OutputRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_review\latest"
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

function Format-Bool {
    param([bool]$Value)
    return $Value.ToString().ToLowerInvariant()
}

$AppProfile = [Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
$AppProfileNormalized = ""
if (-not [string]::IsNullOrWhiteSpace($AppProfile)) {
    $AppProfileNormalized = $AppProfile.Trim().ToLowerInvariant()
}
if ($AppProfileNormalized -in @("paper", "live")) {
    throw (
        "Bounded-paper-probe review is offline only; " +
        "APP_PROFILE=paper or live is not allowed."
    )
}

$CredentialNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
foreach ($Name in $CredentialNames) {
    if (Test-EnvLoaded -Name $Name) {
        throw "Bounded-paper-probe review requires a credential-free process."
    }
}

$NetworkFlagNames = @(
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS"
)
foreach ($Name in $NetworkFlagNames) {
    if (Test-EnvLoaded -Name $Name) {
        throw "Bounded-paper-probe review rejects network-test flags."
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
        throw "Bounded-paper-probe review rejects live endpoint indicators."
    }
}

Write-Host "crypto_tournament_v2_bounded_paper_probe_review_offline=true"
Write-Host "credential_values_exposed=false"
Write-Host "network_access_attempted=false"
Write-Host "broker_read_occurred=false"
Write-Host "broker_mutation_occurred=false"
Write-Host "paper_probe_authorized=false"
Write-Host "capital_allocation_authorized=false"
Write-Host "live_authorized=false"
Write-Host "network_test_flags_loaded=false"
Write-Host "live_endpoint_indicator=false"
Write-Host (
    "APP_PROFILE_is_paper=" +
    (Format-Bool ($AppProfileNormalized -eq "paper"))
)

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    throw "Unable to locate python on PATH."
}

$Arguments = @(
    "-m",
    (
        "algotrader.orchestration." +
        "crypto_tournament_v2_bounded_paper_probe_review"
    ),
    "--shadow-root",
    $ShadowRoot,
    "--capability-root",
    $CapabilityRoot,
    "--output-root",
    $OutputRoot,
    "--as-of",
    $AsOf
)

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
