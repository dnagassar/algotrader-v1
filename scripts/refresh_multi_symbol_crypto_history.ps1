<#
.SYNOPSIS
Builds a guarded multi-symbol crypto OHLC history refresh packet.

.DESCRIPTION
Default mode is dry_run. offline_fixture mode writes deterministic local CSV
history for parser and coverage-gate rehearsal only. market_data_fetch mode is
read-only and requires APP_PROFILE=paper, credentials, a non-live endpoint
check, and explicit -MarketDataFetchAuthorized. Credential values are never
printed. This wrapper does not submit, cancel, replace, close, liquidate, or
mutate broker state.
#>

[CmdletBinding()]
param(
    [ValidateSet("dry_run", "offline_fixture", "market_data_fetch")]
    [string]$Mode = "dry_run",
    [string]$Symbols = "BTCUSD,ETHUSD,SOLUSD,ADAUSD",
    [string]$OutputPath = "runs\operator_input\crypto_paper_bars.csv",
    [string]$PacketPath = "runs\crypto_history_refresh\latest\refresh_packet.json",
    [string]$RawResponsePath = "runs\crypto_history_refresh\latest\raw_crypto_bars.json",
    [string]$FixtureInputPath = "",
    [string]$AsOfTimestamp = "",
    [string]$Start = "",
    [string]$End = "",
    [int]$Hours = 240,
    [string]$Timeframe = "1Hour",
    [string]$Loc = "us",
    [switch]$MarketDataFetchAuthorized,
    [switch]$DataIntakeOnly,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Test-EnvLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    return -not [string]::IsNullOrWhiteSpace($Value)
}

function Format-Bool {
    param([bool]$Value)
    return $Value.ToString().ToLowerInvariant()
}

function Get-PythonCommand {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $PythonCommand) {
        return $PythonCommand.Source
    }
    throw "Unable to locate python on PATH."
}

$AppProfile = [Environment]::GetEnvironmentVariable("APP_PROFILE")
$AppProfileIsPaper = ($AppProfile -eq "paper")
$AppProfileIsLive = ($AppProfile -eq "live")
$ApcaApiBaseUrl = [Environment]::GetEnvironmentVariable("APCA_API_BASE_URL")
$ApcaApiBaseUrlLower = ""
if (-not [string]::IsNullOrWhiteSpace($ApcaApiBaseUrl)) {
    $ApcaApiBaseUrlLower = $ApcaApiBaseUrl.ToLowerInvariant()
}
$ApcaApiBaseUrlIsLive = (
    -not [string]::IsNullOrWhiteSpace($ApcaApiBaseUrlLower) -and
    $ApcaApiBaseUrlLower.Contains("api.alpaca.markets") -and
    -not $ApcaApiBaseUrlLower.Contains("paper")
)
$ApcaApiBaseUrlIsPaper = (
    -not [string]::IsNullOrWhiteSpace($ApcaApiBaseUrlLower) -and
    $ApcaApiBaseUrlLower.Contains("paper-api.alpaca.markets")
)
$LiveEndpointIndicator = $AppProfileIsLive
foreach ($EndpointName in @("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL")) {
    $EndpointValue = [Environment]::GetEnvironmentVariable($EndpointName)
    if (-not [string]::IsNullOrWhiteSpace($EndpointValue)) {
        $LowerUrl = $EndpointValue.ToLowerInvariant()
        if ($LowerUrl.Contains("api.alpaca.markets") -and -not $LowerUrl.Contains("paper")) {
            $LiveEndpointIndicator = $true
        }
    }
}

Write-Host "crypto_history_refresh_command=refresh_multi_symbol_crypto_history"
Write-Host "crypto_history_refresh_mode=$Mode"
Write-Host "crypto_history_refresh_read_only_market_data=true"
Write-Host "crypto_history_refresh_data_intake_only=$(Format-Bool $DataIntakeOnly.IsPresent)"
Write-Host "crypto_history_refresh_no_submit_enforced=true"
Write-Host "APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "ALPACA_API_KEY_loaded=$(Format-Bool (Test-EnvLoaded -Name "ALPACA_API_KEY"))"
Write-Host "ALPACA_API_SECRET_KEY_loaded=$(Format-Bool (Test-EnvLoaded -Name "ALPACA_API_SECRET_KEY"))"
Write-Host "ALPACA_SECRET_KEY_loaded=$(Format-Bool (Test-EnvLoaded -Name "ALPACA_SECRET_KEY"))"
Write-Host "APCA_API_KEY_ID_loaded=$(Format-Bool (Test-EnvLoaded -Name "APCA_API_KEY_ID"))"
Write-Host "APCA_API_SECRET_KEY_loaded=$(Format-Bool (Test-EnvLoaded -Name "APCA_API_SECRET_KEY"))"
Write-Host "APCA_API_BASE_URL_is_live=$(Format-Bool $ApcaApiBaseUrlIsLive)"
Write-Host "APCA_API_BASE_URL_is_paper=$(Format-Bool $ApcaApiBaseUrlIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "Credential values are never printed"
Write-Host "crypto_history_refresh_broker_read_occurred=false"
Write-Host "crypto_history_refresh_market_data_fetch_occurred=false"
Write-Host "crypto_history_refresh_paper_submit_occurred=false"
Write-Host "crypto_history_refresh_broker_mutation_occurred=false"
Write-Host "crypto_history_refresh_live_endpoint_touched=false"

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.execution.crypto_history_refresh_adapter",
    "--mode", $Mode,
    "--symbols", $Symbols,
    "--output-path", $OutputPath,
    "--packet-path", $PacketPath,
    "--raw-response-path", $RawResponsePath,
    "--hours", $Hours.ToString(),
    "--timeframe", $Timeframe,
    "--loc", $Loc,
    "--format", $Format
)

if (-not [string]::IsNullOrWhiteSpace($FixtureInputPath)) {
    $Args += @("--fixture-input-path", $FixtureInputPath)
}
if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $Args += @("--as-of", $AsOfTimestamp)
}
if (-not [string]::IsNullOrWhiteSpace($Start)) {
    $Args += @("--start", $Start)
}
if (-not [string]::IsNullOrWhiteSpace($End)) {
    $Args += @("--end", $End)
}
if ($DataIntakeOnly.IsPresent) {
    $Args += "--data-intake-only"
}
if ($Mode -eq "market_data_fetch" -and $MarketDataFetchAuthorized.IsPresent) {
    $Args += @("--allow-network", "--market-data-fetch-authorized")
}

$ExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    & $Python @Args
    $ExitCode = $LASTEXITCODE
}
catch {
    if ($null -ne $LASTEXITCODE) {
        $ExitCode = $LASTEXITCODE
    }
    else {
        $ExitCode = 1
    }
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
