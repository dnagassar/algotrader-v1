<#
.SYNOPSIS
Refreshes BTCUSD crypto bars for the no-submit crypto paper visibility lane.

.DESCRIPTION
Runs a read-only Alpaca Market Data crypto bars fetch and deterministic local
intake into runs/operator_input/crypto_paper_bars.csv. Credential values are never printed.
This script does not submit, cancel, replace, close, liquidate, or mutate
paper/live broker state.
#>

[CmdletBinding()]
param(
    [string]$RawResponsePath = "runs\operator_input\crypto_paper_bars_raw.json",
    [string]$CanonicalCsv = "runs\operator_input\crypto_paper_bars.csv",
    [string]$RunLog = "runs\crypto_paper_visibility\latest\crypto_bars_intake_manifest.jsonl",
    [string]$Symbol = "BTCUSD",
    [string]$ApiSymbol = "BTC/USD",
    [string]$Loc = "us",
    [string]$Timeframe = "1Hour",
    [int]$Hours = 80,
    [string]$Start,
    [string]$End,
    [string]$ObservedAt,
    [switch]$MarketDataFetchAuthorized,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$CredentialVariableNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)

function Test-ProcessEnvironmentVariableLoaded {
    param([string]$Name)
    $Value = [System.Environment]::GetEnvironmentVariable($Name, "Process")
    return -not [string]::IsNullOrWhiteSpace($Value)
}

function Format-Bool {
    param([bool]$Value)
    return $Value.ToString().ToLowerInvariant()
}

$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
$AppProfileIsPaper = $AppProfile -eq "paper"
$AppProfileIsLive = $AppProfile -eq "live"
$LiveEndpointIndicator = $AppProfileIsLive
foreach ($EndpointName in @("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL")) {
    $EndpointValue = [System.Environment]::GetEnvironmentVariable($EndpointName, "Process")
    if (-not [string]::IsNullOrWhiteSpace($EndpointValue)) {
        $LowerUrl = $EndpointValue.ToLowerInvariant()
        if ($LowerUrl.Contains("api.alpaca.markets") -and -not $LowerUrl.Contains("paper")) {
            $LiveEndpointIndicator = $true
        }
    }
}

$KeyPresent = (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_API_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_API_KEY_ID") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "APCA_API_KEY_ID")
$SecretPresent = (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_API_SECRET_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_SECRET_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "APCA_API_SECRET_KEY")
$PaperCredentialsPresent = $KeyPresent -and $SecretPresent

Write-Host "crypto_bars_refresh_command=refresh_crypto_paper_bars"
Write-Host "crypto_bars_refresh_read_only_market_data=true"
Write-Host "crypto_bars_refresh_no_submit_enforced=true"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
foreach ($Name in $CredentialVariableNames) {
    Write-Host "preflight_$($Name)_present=$(Format-Bool (Test-ProcessEnvironmentVariableLoaded -Name $Name))"
}
Write-Host "preflight_paper_credentials_present=$(Format-Bool $PaperCredentialsPresent)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "crypto_bars_refresh_paper_submit_performed=false"
Write-Host "crypto_bars_refresh_broker_mutation_performed=false"
Write-Host "crypto_bars_refresh_live_mutation_performed=false"

if ($LiveEndpointIndicator) {
    Write-Host "crypto_bars_refresh_stop_reason=live_endpoint_indicator"
    exit 2
}

if (-not $AppProfileIsPaper) {
    Write-Host "crypto_bars_refresh_stop_reason=paper_profile_required"
    exit 2
}

if (-not $PaperCredentialsPresent) {
    Write-Host "crypto_bars_refresh_stop_reason=paper_credentials_required"
    exit 2
}

if (-not $MarketDataFetchAuthorized) {
    Write-Host "crypto_bars_refresh_stop_reason=market_data_fetch_authorization_required"
    exit 2
}

$CliArgs = @(
    "scripts\research\fetch_alpaca_crypto_bars.py",
    "--raw-response-path", $RawResponsePath,
    "--canonical-csv", $CanonicalCsv,
    "--run-log", $RunLog,
    "--symbol", $Symbol,
    "--api-symbol", $ApiSymbol,
    "--loc", $Loc,
    "--timeframe", $Timeframe,
    "--hours", $Hours.ToString(),
    "--allow-network",
    "--market-data-fetch-authorized",
    "--format", $Format
)

if (-not [string]::IsNullOrWhiteSpace($Start)) {
    $CliArgs += @("--start", $Start)
}

if (-not [string]::IsNullOrWhiteSpace($End)) {
    $CliArgs += @("--end", $End)
}

if (-not [string]::IsNullOrWhiteSpace($ObservedAt)) {
    $CliArgs += @("--observed-at", $ObservedAt)
}

Push-Location -LiteralPath $RepoRoot
try {
    & python @CliArgs
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}

exit $ExitCode
