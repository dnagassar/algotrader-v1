<#
.SYNOPSIS
Runs the selected-winner no-submit crypto tournament-v2 forward shadow cycle.

.DESCRIPTION
Initialize, status, and readiness are offline. market_data_fetch is the only
network-capable mode and requires both explicit switches plus a paper profile.
The selected symbol and exact hourly window are derived from frozen state; no
symbol input, broker read, order, paper mutation, or live path is exposed.
#>

[CmdletBinding()]
param(
    [ValidateSet(
        "initialize",
        "status",
        "readiness",
        "market_data_fetch"
    )]
    [string]$Mode = "status",
    [string]$TournamentRoot = (
        "runs\crypto_strategy_tournament\v2\latest"
    ),
    [string]$OutputRoot = (
        "runs\crypto_strategy_tournament\v2\forward_shadow\latest"
    ),
    [string]$AsOf = "",
    [switch]$MarketDataFetchAuthorized,
    [switch]$AllowNetwork
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (
    Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
).Path

function Test-EnvLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    return -not [string]::IsNullOrWhiteSpace($Value)
}

function Format-Bool {
    param([bool]$Value)
    return $Value.ToString().ToLowerInvariant()
}

$AppProfile = [Environment]::GetEnvironmentVariable("APP_PROFILE")
$ApiBaseUrl = [Environment]::GetEnvironmentVariable("APCA_API_BASE_URL")
$LiveEndpointIndicator = (
    $AppProfile -eq "live" -or
    (
        -not [string]::IsNullOrWhiteSpace($ApiBaseUrl) -and
        $ApiBaseUrl.ToLowerInvariant().Contains("api.alpaca.markets") -and
        -not $ApiBaseUrl.ToLowerInvariant().Contains("paper")
    )
)

if ($Mode -eq "market_data_fetch") {
    if (
        -not $MarketDataFetchAuthorized.IsPresent -or
        -not $AllowNetwork.IsPresent
    ) {
        throw (
            "market_data_fetch requires " +
            "-MarketDataFetchAuthorized and -AllowNetwork."
        )
    }
    if ($LiveEndpointIndicator) {
        throw "Live profile or endpoint indicator blocks market-data fetch."
    }
    if ($AppProfile -ne "paper") {
        throw "market_data_fetch requires APP_PROFILE=paper."
    }
}
elseif (
    $MarketDataFetchAuthorized.IsPresent -or
    $AllowNetwork.IsPresent
) {
    throw (
        "Network authorization switches require " +
        "-Mode market_data_fetch."
    )
}

Write-Host "crypto_tournament_v2_forward_shadow_mode=$Mode"
Write-Host "selected_symbol_source=frozen_shadow_state"
Write-Host "crypto_tournament_v2_forward_shadow_no_submit=true"
Write-Host "paper_mutation_authorized=false"
Write-Host (
    "APP_PROFILE_is_paper=" +
    (Format-Bool ($AppProfile -eq "paper"))
)
Write-Host (
    "live_endpoint_indicator=" +
    (Format-Bool $LiveEndpointIndicator)
)
foreach ($Name in @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)) {
    Write-Host (
        $Name + "_loaded=" +
        (Format-Bool (Test-EnvLoaded -Name $Name))
    )
}
Write-Host "credential_values_exposed=false"
Write-Host "broker_read_occurred=false"
Write-Host "broker_mutation_occurred=false"
Write-Host "paper_submit_occurred=false"
Write-Host "live_endpoint_touched=false"

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    throw "Unable to locate python on PATH."
}

$Arguments = @(
    "-m",
    "algotrader.orchestration.crypto_tournament_v2_forward_shadow",
    "--mode",
    $Mode,
    "--tournament-root",
    $TournamentRoot,
    "--output-root",
    $OutputRoot
)
if (-not [string]::IsNullOrWhiteSpace($AsOf)) {
    $Arguments += @("--as-of", $AsOf)
}
if ($Mode -eq "market_data_fetch") {
    $Arguments += @(
        "--market-data-fetch-authorized",
        "--allow-network"
    )
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
