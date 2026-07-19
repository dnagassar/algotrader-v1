<#
.SYNOPSIS
Runs the V5.32 deterministic supervised crypto readiness trial.

.DESCRIPTION
The default command is credential-free, network-free, broker-free, and
no-submit. A separately requested read-only paper observation requires both
-BrokerObservedReadiness and -AllowAlpacaPaperRead in an exact paper shell.
Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_supervised_readiness_trial\latest",
    [string]$DecisionStart = "2026-07-19T12:00:00Z",
    [ValidateRange(8, 24)]
    [int]$CycleCount = 24,
    [switch]$BrokerObservedReadiness,
    [switch]$AllowAlpacaPaperRead,
    [switch]$ValidateOnly,
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

$Profile = [Environment]::GetEnvironmentVariable("APP_PROFILE")
$ProfilePaper = $Profile -eq "paper"
$ProfileLive = $Profile -eq "live"
$CredentialsPresent = $false
foreach ($Name in @("ALPACA_API_KEY", "ALPACA_API_SECRET_KEY", "ALPACA_SECRET_KEY", "APCA_API_KEY_ID", "APCA_API_SECRET_KEY")) {
    if (Test-EnvLoaded -Name $Name) { $CredentialsPresent = $true }
}
$NetworkFlagsPresent = $false
foreach ($Name in @("ALGO_TRADER_ALLOW_NETWORK_TESTS", "RUN_ALPACA_PAPER_INTEGRATION_TESTS", "PYTEST_NETWORK", "NETWORK_TESTS")) {
    if (Test-EnvLoaded -Name $Name) { $NetworkFlagsPresent = $true }
}
$PaperEndpointExact = $false
$LiveEndpointIndicator = $ProfileLive
foreach ($Name in @("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL")) {
    $Value = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        $Lower = $Value.ToLowerInvariant().TrimEnd("/")
        if ($Lower -eq "https://paper-api.alpaca.markets") { $PaperEndpointExact = $true }
        if ($Lower.Contains("api.alpaca.markets") -and -not $Lower.Contains("paper-api")) { $LiveEndpointIndicator = $true }
    }
}

Write-Host "v5_32_preflight_APP_PROFILE_is_paper=$(Format-Bool $ProfilePaper)"
Write-Host "v5_32_preflight_APP_PROFILE_is_live=$(Format-Bool $ProfileLive)"
Write-Host "v5_32_preflight_credentials_present=$(Format-Bool $CredentialsPresent)"
Write-Host "v5_32_preflight_network_flags_present=$(Format-Bool $NetworkFlagsPresent)"
Write-Host "v5_32_preflight_paper_endpoint_exact=$(Format-Bool $PaperEndpointExact)"
Write-Host "v5_32_preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "Credential values are never printed"

if ($LiveEndpointIndicator) {
    Write-Host "v5_32_status=blocked_live_endpoint_indicator"
    exit 2
}
if ($AllowAlpacaPaperRead.IsPresent -and -not $BrokerObservedReadiness.IsPresent) {
    Write-Host "v5_32_status=blocked_read_permission_without_request"
    exit 2
}
if (-not $BrokerObservedReadiness.IsPresent -and ($ProfilePaper -or $CredentialsPresent -or $NetworkFlagsPresent)) {
    Write-Host "v5_32_status=blocked_unsafe_offline_environment"
    exit 2
}
if ($AllowAlpacaPaperRead.IsPresent -and (-not $ProfilePaper -or -not $CredentialsPresent -or -not $PaperEndpointExact)) {
    Write-Host "v5_32_status=broker_read_preconditions_unavailable_offline_trial_continues"
}

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) { throw "Unable to locate python on PATH." }
$Arguments = @(
    "-m", "algotrader.execution.crypto_supervised_readiness_trial",
    "--output-root", $OutputRoot,
    "--decision-start", $DecisionStart,
    "--cycle-count", $CycleCount,
    "--format", $Format
)
if ($BrokerObservedReadiness.IsPresent) { $Arguments += "--broker-observed-readiness" }
if ($AllowAlpacaPaperRead.IsPresent) { $Arguments += "--allow-alpaca-paper-read" }
if ($ValidateOnly.IsPresent) { $Arguments += "--validate-only" }

Push-Location -LiteralPath $RepoRoot
try {
    & $PythonCommand.Source @Arguments
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($null -eq $ExitCode) { $ExitCode = 0 }
exit $ExitCode
