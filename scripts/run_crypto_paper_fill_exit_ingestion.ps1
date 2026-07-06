<#
.SYNOPSIS
Ingests the v5.10 BTCUSD paper fill/exit certification artifact.

.DESCRIPTION
Builds v5.11 no-submit certification artifacts and a prepared read-only
BTCUSD flat-reconciliation request. This script does not perform a broker read
or any broker mutation. Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$CertificationResultPath = "runs\crypto_paper_fill_exit_certification\latest\fill_exit_certification_result.json",
    [string]$OutputRoot = "runs\crypto_paper_fill_exit_ingestion\latest",
    [string]$MaxNotional = "25",
    [string]$AsOfTimestamp = "",
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

$KeyPresent = (
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_API_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "APCA_API_KEY_ID")
)
$SecretPresent = (
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_SECRET_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_API_SECRET_KEY") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "APCA_API_SECRET_KEY")
)
$PaperCredentialsPresent = $KeyPresent -and $SecretPresent
$ExpectedAccountLoaded = (
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_EXPECTED_PAPER_ACCOUNT_ID") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_PAPER_ACCOUNT_ID") -or
    (Test-ProcessEnvironmentVariableLoaded -Name "APCA_EXPECTED_PAPER_ACCOUNT_ID")
)
$NetworkFlagEnabled = (
    [System.Environment]::GetEnvironmentVariable("ALGO_TRADER_ALLOW_NETWORK_TESTS", "Process") -eq "1" -or
    [System.Environment]::GetEnvironmentVariable("RUN_ALPACA_PAPER_INTEGRATION_TESTS", "Process") -eq "1"
)

Write-Host "crypto_paper_fill_exit_ingestion_command=run_crypto_paper_fill_exit_ingestion"
Write-Host "crypto_paper_fill_exit_ingestion_scope=local_v5_10_result_ingestion_only"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
foreach ($Name in $CredentialVariableNames) {
    Write-Host "preflight_$($Name)_present=$(Format-Bool (Test-ProcessEnvironmentVariableLoaded -Name $Name))"
}
Write-Host "preflight_expected_paper_account_id_loaded=$(Format-Bool $ExpectedAccountLoaded)"
Write-Host "preflight_paper_credentials_present=$(Format-Bool $PaperCredentialsPresent)"
Write-Host "preflight_paper_endpoint_exact_match_indicator=$(Format-Bool $PaperEndpointExactMatchIndicator)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "preflight_network_flag_enabled=$(Format-Bool $NetworkFlagEnabled)"
Write-Host "broker_read_performed_current_run=false"
Write-Host "broker_mutation_performed_current_run=false"
Write-Host "paper_submit_performed_current_run=false"
Write-Host "paper_cancel_performed_current_run=false"
Write-Host "paper_replace_performed_current_run=false"
Write-Host "paper_close_performed_current_run=false"
Write-Host "paper_liquidate_performed_current_run=false"
Write-Host "live_endpoint_touched_current_run=false"
Write-Host "credential_values_exposed=false"

if ($LiveEndpointIndicator) {
    Write-Host "crypto_paper_fill_exit_ingestion_stop_reason=live_endpoint_indicator"
    exit 2
}

if (-not ($AppProfileIsPaper -and $PaperCredentialsPresent -and $ExpectedAccountLoaded -and $PaperEndpointExactMatchIndicator)) {
    Write-Host "read_only_reconciliation_status=blocked_paper_shell_required_prepare_only"
    Write-Host "read_only_reconciliation_operator_command=pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_crypto_paper_fill_exit_ingestion.ps1 -CertificationResultPath `"$CertificationResultPath`" -OutputRoot `"$OutputRoot`" -Format $Format"
}
else {
    Write-Host "read_only_reconciliation_status=paper_shell_detected_request_still_prepare_only"
}

$PythonArgs = @(
    "-m",
    "algotrader.orchestration.crypto_paper_fill_exit_ingestion",
    "--certification-result-path",
    $CertificationResultPath,
    "--output-root",
    $OutputRoot,
    "--max-notional",
    $MaxNotional,
    "--format",
    $Format
)

if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $PythonArgs += @("--as-of", $AsOfTimestamp)
}

Push-Location -LiteralPath $RepoRoot
try {
    & python @PythonArgs
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}

exit $ExitCode
