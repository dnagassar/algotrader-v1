<#
.SYNOPSIS
Runs deterministic offline v2.17 research hypothesis triage.

.DESCRIPTION
Loads existing local strategy challenger and preview review artifacts, explains
why inspected candidates failed, and selects one materially different next
strategy family for offline research. This wrapper does not read a broker,
mutate broker state, submit paper orders, load credentials, fetch market data,
or contact the network. Credential values are never printed.

.PARAMETER OutputRoot
Directory under which research hypothesis triage artifacts are written.

.PARAMETER ChallengerRoot
Directory containing strategy challenger artifacts.

.PARAMETER PreviewReviewRoot
Directory containing preview candidate review artifacts.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\strategy_challengers\research_hypothesis_triage_latest",
    [string]$ChallengerRoot = "runs\strategy_challengers\latest",
    [string]$PreviewReviewRoot = "runs\strategy_challengers\preview_review_latest"
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
Write-Host "Credential values are never printed"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $TiingoApiKeyLoaded -or $PaperIntegrationFlagEnabled) {
    Write-Host "research_hypothesis_triage_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.research.research_hypothesis_triage",
    "--challenger-root", $ChallengerRoot,
    "--preview-review-root", $PreviewReviewRoot,
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
