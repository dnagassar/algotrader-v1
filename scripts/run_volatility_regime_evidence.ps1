<#
.SYNOPSIS
Runs deterministic offline v2.18 volatility-regime evidence.

.DESCRIPTION
Loads existing local ETF adjusted daily bars and local v2.16/v2.17 research
artifacts, computes a fixed no-lookahead realized-volatility regime diagnostic,
and writes JSON/markdown artifacts under ignored runs/. This wrapper does not read a broker,
mutate broker state, submit paper orders, load credentials, fetch market data,
or contact the network. Credential values are never printed.

.PARAMETER OutputRoot
Directory under which volatility-regime evidence artifacts are written.

.PARAMETER DataManifest
Existing local multi-ETF adjusted data manifest.

.PARAMETER ChallengerResultsPath
Existing local strategy challenger results JSON.

.PARAMETER PreviewReviewPath
Existing local preview candidate review JSON.

.PARAMETER TriagePath
Existing local v2.17 research hypothesis triage JSON.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\strategy_challengers\volatility_regime_evidence_latest",
    [string]$DataManifest = "runs\operator_input\multi_etf_adjusted_data_manifest.json",
    [string]$ChallengerResultsPath = "runs\strategy_challengers\latest\challenger_results.json",
    [string]$PreviewReviewPath = "runs\strategy_challengers\preview_review_latest\preview_candidate_review.json",
    [string]$TriagePath = "runs\strategy_challengers\research_hypothesis_triage_latest\research_hypothesis_triage.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Test-EnvLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    return -not [string]::IsNullOrEmpty($Value)
}

function Get-PythonCommand {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $PythonCommand) {
        return $PythonCommand.Source
    }
    throw "Unable to locate python on PATH."
}

function Test-FlagEnabled {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    return ($Value -eq "1" -or $Value -eq "true")
}

$AppProfile = [Environment]::GetEnvironmentVariable("APP_PROFILE")
$AppProfileIsPaper = ($AppProfile -eq "paper")
$AppProfileIsLive = ($AppProfile -eq "live")
$PaperIntegrationFlagEnabled = Test-FlagEnabled -Name "RUN_ALPACA_PAPER_INTEGRATION_TESTS"
$NetworkTestsFlagEnabled = Test-FlagEnabled -Name "ALGO_TRADER_ALLOW_NETWORK_TESTS"
$CredentialNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
$CredentialVariablesLoaded = $false
foreach ($Name in $CredentialNames) {
    if (Test-EnvLoaded -Name $Name) {
        $CredentialVariablesLoaded = $true
    }
}
$TiingoApiKeyLoaded = Test-EnvLoaded -Name "TIINGO_API_KEY"

Write-Host "preflight_APP_PROFILE_is_paper=$($AppProfileIsPaper.ToString().ToLowerInvariant())"
Write-Host "preflight_APP_PROFILE_is_live=$($AppProfileIsLive.ToString().ToLowerInvariant())"
Write-Host "preflight_ALPACA_API_KEY_loaded=$((Test-EnvLoaded -Name "ALPACA_API_KEY").ToString().ToLowerInvariant())"
Write-Host "preflight_ALPACA_API_SECRET_KEY_loaded=$((Test-EnvLoaded -Name "ALPACA_API_SECRET_KEY").ToString().ToLowerInvariant())"
Write-Host "preflight_ALPACA_SECRET_KEY_loaded=$((Test-EnvLoaded -Name "ALPACA_SECRET_KEY").ToString().ToLowerInvariant())"
Write-Host "preflight_APCA_API_KEY_ID_loaded=$((Test-EnvLoaded -Name "APCA_API_KEY_ID").ToString().ToLowerInvariant())"
Write-Host "preflight_APCA_API_SECRET_KEY_loaded=$((Test-EnvLoaded -Name "APCA_API_SECRET_KEY").ToString().ToLowerInvariant())"
Write-Host "preflight_TIINGO_API_KEY_loaded=$($TiingoApiKeyLoaded.ToString().ToLowerInvariant())"
Write-Host "preflight_credential_variables_loaded=$($CredentialVariablesLoaded.ToString().ToLowerInvariant())"
Write-Host "preflight_RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled=$($PaperIntegrationFlagEnabled.ToString().ToLowerInvariant())"
Write-Host "preflight_ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled=$($NetworkTestsFlagEnabled.ToString().ToLowerInvariant())"
Write-Host "Credential values are never printed"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $TiingoApiKeyLoaded -or $PaperIntegrationFlagEnabled -or $NetworkTestsFlagEnabled) {
    Write-Host "volatility_regime_evidence_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.research.volatility_regime_evidence",
    "--data-manifest", $DataManifest,
    "--challenger-results-path", $ChallengerResultsPath,
    "--preview-review-path", $PreviewReviewPath,
    "--triage-path", $TriagePath,
    "--output-root", $OutputRoot
)

Push-Location -LiteralPath $RepoRoot
try {
    & $Python @Args
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
