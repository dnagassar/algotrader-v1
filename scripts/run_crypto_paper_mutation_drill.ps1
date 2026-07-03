<#
.SYNOPSIS
Runs the explicit v4.12C bounded BTCUSD Alpaca paper mutation drill.

.DESCRIPTION
This command is paper-only and requires -CryptoPaperMutationAuthorized. It
prints boolean-only preflight state, never credential values, and delegates to
the separate crypto_paper_mutation_drill module. It is not used by normal
pytest or the normal no-submit crypto visibility cycle.
#>

[CmdletBinding()]
param(
    [switch]$CryptoPaperMutationAuthorized,
    [string]$OutputRoot = "runs\crypto_paper_mutation_drill\latest",
    [string]$BarsCsv = "runs\operator_input\crypto_paper_bars.csv",
    [string]$ExpectedPaperAccountId,
    [string]$TargetSymbol = "BTCUSD",
    [string]$SelectedSymbolOverrideReason,
    [string]$MaxDrillNotional = "11.00",
    [string]$AsOfTimestamp,
    [int]$ReconciliationPollAttempts = 3,
    [double]$ReconciliationPollIntervalSeconds = 1.0,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DefaultPaperBaseUrl = "https://paper-api.alpaca.markets"

$CredentialVariableNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
$ExpectedAccountVariableNames = @(
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID"
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

function Get-FirstLoadedExpectedAccount {
    foreach ($Name in $ExpectedAccountVariableNames) {
        $Value = [System.Environment]::GetEnvironmentVariable($Name, "Process")
        if (-not [string]::IsNullOrWhiteSpace($Value)) {
            return $Value
        }
    }
    return ""
}

$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
$AppProfileIsPaper = $AppProfile -eq "paper"
$AppProfileIsLive = $AppProfile -eq "live"
$PaperBaseUrl = [System.Environment]::GetEnvironmentVariable("ALPACA_PAPER_BASE_URL", "Process")
$EffectivePaperBaseUrl = $PaperBaseUrl
if ([string]::IsNullOrWhiteSpace($EffectivePaperBaseUrl)) {
    $EffectivePaperBaseUrl = $DefaultPaperBaseUrl
}
$PaperEndpointExactMatchIndicator = (
    $EffectivePaperBaseUrl.TrimEnd("/").ToLowerInvariant() -eq $DefaultPaperBaseUrl
)
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
if (-not [string]::IsNullOrWhiteSpace($PaperBaseUrl)) {
    $LowerUrl = $PaperBaseUrl.ToLowerInvariant()
    if ($LowerUrl.Contains("alpaca") -and -not $LowerUrl.Contains("paper")) {
        $LiveEndpointIndicator = $true
    }
}
$ApiKeyPresent = (
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_API_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "APCA_API_KEY_ID")
)
$SecretPresent = (
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_SECRET_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_API_SECRET_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "APCA_API_SECRET_KEY")
)
$PaperCredentialsPresent = $ApiKeyPresent -and $SecretPresent
$ExpectedAccountLoaded = -not [string]::IsNullOrWhiteSpace($ExpectedPaperAccountId)
if (-not $ExpectedAccountLoaded) {
    $ExpectedPaperAccountId = Get-FirstLoadedExpectedAccount
    $ExpectedAccountLoaded = -not [string]::IsNullOrWhiteSpace($ExpectedPaperAccountId)
}

Write-Host "crypto_paper_mutation_drill_command=run_crypto_paper_mutation_drill"
Write-Host "crypto_paper_mutation_drill_scope=alpaca_paper_only_btcusd_bounded_limit_buy"
Write-Host "crypto_paper_mutation_authorized=$(Format-Bool $CryptoPaperMutationAuthorized.IsPresent)"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
foreach ($Name in $CredentialVariableNames) {
    Write-Host "preflight_$($Name)_present=$(Format-Bool (Test-ProcessEnvironmentVariableLoaded -Name $Name))"
}
Write-Host "preflight_paper_credentials_present=$(Format-Bool $PaperCredentialsPresent)"
Write-Host "preflight_expected_paper_account_id_loaded=$(Format-Bool $ExpectedAccountLoaded)"
Write-Host "preflight_paper_endpoint_exact_match_indicator=$(Format-Bool $PaperEndpointExactMatchIndicator)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "crypto_paper_mutation_paper_submit_authorized=$(Format-Bool $CryptoPaperMutationAuthorized.IsPresent)"
Write-Host "crypto_paper_mutation_paper_submit_performed=false"
Write-Host "crypto_paper_mutation_broker_mutation_performed=false"
Write-Host "crypto_paper_mutation_live_mutation_performed=false"

if (-not $CryptoPaperMutationAuthorized.IsPresent) {
    Write-Host "crypto_paper_mutation_stop_reason=crypto_paper_mutation_authorization_required"
    exit 2
}
if ($LiveEndpointIndicator) {
    Write-Host "crypto_paper_mutation_stop_reason=live_endpoint_indicator"
    exit 2
}

$CliArgs = @(
    "-m", "algotrader.execution.crypto_paper_mutation_drill",
    "--crypto-paper-mutation-authorized",
    "--output-root", $OutputRoot,
    "--bars-csv", $BarsCsv,
    "--target-symbol", $TargetSymbol,
    "--max-drill-notional", $MaxDrillNotional,
    "--reconciliation-poll-attempts", $ReconciliationPollAttempts.ToString(),
    "--reconciliation-poll-interval-seconds", $ReconciliationPollIntervalSeconds.ToString(),
    "--format", $Format
)

if (-not [string]::IsNullOrWhiteSpace($ExpectedPaperAccountId)) {
    $CliArgs += @("--expected-paper-account-id", $ExpectedPaperAccountId)
}
if (-not [string]::IsNullOrWhiteSpace($SelectedSymbolOverrideReason)) {
    $CliArgs += @("--selected-symbol-override-reason", $SelectedSymbolOverrideReason)
}
if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $CliArgs += @("--timestamp", $AsOfTimestamp)
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
