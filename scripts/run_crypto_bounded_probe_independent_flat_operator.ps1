<#
.SYNOPSIS
Collects one target-scoped, read-only post-exit paper flat observation.

.DESCRIPTION
This command can read the paper account, all positions, and all open orders.
It cannot submit, cancel, replace, close, liquidate, or use a live endpoint.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("BTCUSD", "ETHUSD", "SOLUSD")]
    [string]$TargetSymbol,
    [switch]$IndependentFlatReadAuthorized,
    [switch]$AllowNetwork,
    [string]$LifecyclePath = "runs\crypto_strategy_tournament\v2\bounded_paper_probe_lifecycle\latest\lifecycle_result.json",
    [string]$OutputRoot = "runs\crypto_strategy_tournament\v2\bounded_paper_probe_capabilities",
    [string]$ExpectedPaperAccountId = "",
    [string]$AsOfTimestamp = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DefaultPaperBaseUrl = "https://paper-api.alpaca.markets"

function Test-Loaded([string]$Name) {
    return -not [string]::IsNullOrWhiteSpace(
        [Environment]::GetEnvironmentVariable($Name, "Process")
    )
}
function Format-Bool([bool]$Value) {
    return $Value.ToString().ToLowerInvariant()
}

$AppProfile = [Environment]::GetEnvironmentVariable(
    "APP_PROFILE", "Process"
)
$PaperUrl = [Environment]::GetEnvironmentVariable(
    "ALPACA_PAPER_BASE_URL", "Process"
)
if ([string]::IsNullOrWhiteSpace($PaperUrl)) {
    $PaperUrl = [Environment]::GetEnvironmentVariable(
        "APCA_API_BASE_URL", "Process"
    )
}
$LiveEndpoint = $AppProfile -eq "live"
if (-not [string]::IsNullOrWhiteSpace($PaperUrl)) {
    $LiveEndpoint = $LiveEndpoint -or (
        $PaperUrl.ToLowerInvariant().Contains("api.alpaca.markets") -and
        -not $PaperUrl.ToLowerInvariant().Contains("paper")
    )
}
$PaperEndpointExact = (
    -not [string]::IsNullOrWhiteSpace($PaperUrl) -and
    $PaperUrl.TrimEnd("/").ToLowerInvariant() -eq $DefaultPaperBaseUrl
)

Write-Host "crypto_bounded_probe_independent_flat_target=$TargetSymbol"
Write-Host "crypto_bounded_probe_independent_flat_read_authorized=$(Format-Bool $IndependentFlatReadAuthorized.IsPresent)"
Write-Host "crypto_bounded_probe_independent_flat_network_authorized=$(Format-Bool $AllowNetwork.IsPresent)"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool ($AppProfile -eq 'paper'))"
Write-Host "preflight_paper_endpoint_exact_match=$(Format-Bool $PaperEndpointExact)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpoint)"
foreach ($Name in @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)) {
    Write-Host "preflight_$($Name)_present=$(Format-Bool (Test-Loaded $Name))"
}
Write-Host "credential_values_exposed=false"
Write-Host "broker_mutation_occurred=false"
Write-Host "paper_mutation_occurred=false"
Write-Host "live_endpoint_touched=false"

if (
    -not $IndependentFlatReadAuthorized.IsPresent -or
    -not $AllowNetwork.IsPresent
) {
    throw (
        "Independent flat collection requires both explicit read and " +
        "network switches."
    )
}
if ($LiveEndpoint) {
    throw "Live endpoint indicators are not authorized."
}

$Arguments = @(
    "-m",
    "algotrader.execution.crypto_bounded_probe_independent_flat_operator",
    "--target-symbol",
    $TargetSymbol,
    "--lifecycle-path",
    $LifecyclePath,
    "--output-root",
    $OutputRoot,
    "--independent-flat-read-authorized",
    "--allow-network"
)
if (-not [string]::IsNullOrWhiteSpace($ExpectedPaperAccountId)) {
    $Arguments += @(
        "--expected-paper-account-id",
        $ExpectedPaperAccountId
    )
}
if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $Arguments += @("--timestamp", $AsOfTimestamp)
}

Push-Location -LiteralPath $RepoRoot
try {
    & python @Arguments
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
