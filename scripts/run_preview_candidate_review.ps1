<#
.SYNOPSIS
Runs the deterministic offline preview-only candidate review.

.DESCRIPTION
Loads local strategy challenger artifacts, reviews candidates classified as
preview_only, and writes anti-overfit review artifacts. This wrapper does not
read a broker, mutate broker state, submit paper orders, load credentials, or
contact the network. Credential values are never printed.

.PARAMETER OutputRoot
Directory under which preview candidate review artifacts are written.

.PARAMETER InputRoot
Directory containing strategy challenger artifacts.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [string]$InputRoot = "runs\strategy_challengers\latest"
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

$AppProfile = [Environment]::GetEnvironmentVariable("APP_PROFILE")
$AppProfileIsPaper = ($AppProfile -eq "paper")
$AppProfileIsLive = ($AppProfile -eq "live")
$PaperIntegrationFlagEnabled = ([Environment]::GetEnvironmentVariable("RUN_ALPACA_PAPER_INTEGRATION_TESTS") -eq "1")
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

Write-Host "preflight_APP_PROFILE_is_paper=$($AppProfileIsPaper.ToString().ToLowerInvariant())"
Write-Host "preflight_APP_PROFILE_is_live=$($AppProfileIsLive.ToString().ToLowerInvariant())"
Write-Host "preflight_credential_variables_loaded=$($CredentialVariablesLoaded.ToString().ToLowerInvariant())"
Write-Host "preflight_RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled=$($PaperIntegrationFlagEnabled.ToString().ToLowerInvariant())"
Write-Host "Credential values are never printed"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $PaperIntegrationFlagEnabled) {
    Write-Host "preview_candidate_review_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.research.preview_candidate_review",
    "--input-root", $InputRoot,
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
