<#
.SYNOPSIS
Replays one exact immutable V5.26/V5.27 review generation offline.

.DESCRIPTION
Requires an explicit review publication fingerprint. This credential-free,
network-free command never trusts the mutable latest pointer as authorization
input and never grants paper, capital, or live authority.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-fA-F]{64}$")]
    [string]$ExpectedPublicationFingerprint,
    [string]$ReviewRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_review\latest"
    ),
    [string]$TrustedCurrentUtc = (
        (Get-Date).ToUniversalTime().ToString("o")
    )
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
        "Review replay is offline only; " +
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
        throw "Review replay requires a credential-free process."
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
        throw "Review replay rejects network-test flags."
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
        throw "Review replay rejects live endpoint indicators."
    }
}

Write-Host "crypto_tournament_v2_review_replay_offline=true"
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

$Arguments = @(
    "-m",
    (
        "algotrader.certification." +
        "crypto_tournament_v2_bounded_paper_probe_generation_replay"
    ),
    "--review-root",
    $ReviewRoot,
    "--expected-publication-fingerprint",
    $ExpectedPublicationFingerprint.ToLowerInvariant(),
    "--trusted-current-utc",
    $TrustedCurrentUtc
)

Push-Location -LiteralPath $RepoRoot
try {
    & $PythonCommand.Source @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
exit 0
