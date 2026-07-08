<#
.SYNOPSIS
Runs the v5.13 crypto no-submit operating cycle.

.DESCRIPTION
Chains the existing local crypto refresh, opportunity router, qty sizing preview,
Paper OMS handoff, Paper OMS dry-run identity, and v5.12 autonomy cadence packet.
This wrapper does not read a broker, mutate broker state, submit paper orders,
load credentials, or contact the network. Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_no_submit_operating_cycle\latest",
    [string]$CryptoRefreshOutputRoot = "runs\crypto_universe_refresh\paper_read_repair_latest",
    [string]$RouterOutputRoot = "runs\opportunity_router\paper_read_repair_latest",
    [string]$SizingPreviewOutputRoot = "runs\crypto_qty_sizing_preview\latest",
    [string]$HandoffOutputRoot = "runs\crypto_paper_oms_handoff\latest",
    [string]$DryRunOutputRoot = "runs\crypto_paper_oms_dry_run\latest",
    [string]$AutonomyCadenceOutputRoot = "runs\crypto_paper_autonomy_cadence\latest",
    [ValidateSet("local_replay", "offline_fixture")]
    [string]$RefreshMode = "local_replay",
    [string]$BarsCsv = "runs\operator_input\crypto_paper_bars.csv",
    [string]$CryptoVisibilityStatus = "runs\crypto_paper_visibility\latest\latest_status.json",
    [string]$SpyBarsCsv = "",
    [string]$SubmitCancelResultPath = "runs\crypto_paper_submit_cancel_certification\latest\certification_result.json",
    [string]$CertificationIngestionPath = "runs\crypto_paper_certification_ingestion\latest\certification_ingestion.json",
    [string]$FillExitResultPath = "runs\crypto_paper_fill_exit_certification\latest\fill_exit_certification_result.json",
    [string]$FillExitIngestionPath = "runs\crypto_paper_fill_exit_ingestion\latest\fill_exit_ingestion.json",
    [string]$PreviewNotionalCap = "25",
    [string]$ObservedLatestPriceArtifact = "",
    [string]$AsOfTimestamp = "",
    [ValidateSet("text", "json")]
    [string]$Format = "text",
    [switch]$AllowFixtureBacked
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
$NetworkFlagsLoaded = $false
foreach ($Name in @("PYTEST_NETWORK", "NETWORK_TESTS", "ALLOW_NETWORK_TESTS", "ALGO_TRADER_ALLOW_NETWORK_TESTS", "RUN_ALPACA_PAPER_INTEGRATION_TESTS")) {
    if (Test-EnvLoaded -Name $Name) {
        $NetworkFlagsLoaded = $true
    }
}
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

Write-Host "crypto_no_submit_operating_cycle_command=run_crypto_no_submit_operating_cycle"
Write-Host "crypto_no_submit_operating_cycle_mode=offline/no_submit"
Write-Host "crypto_no_submit_operating_cycle_refresh_mode=$RefreshMode"
Write-Host "crypto_no_submit_operating_cycle_no_submit_enforced=true"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
Write-Host "preflight_credential_variables_loaded=$(Format-Bool $CredentialVariablesLoaded)"
Write-Host "preflight_network_flags_loaded=$(Format-Bool $NetworkFlagsLoaded)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "Credential values are never printed"
Write-Host "crypto_no_submit_operating_cycle_broker_read_occurred=false"
Write-Host "crypto_no_submit_operating_cycle_paper_submit_authorized=false"
Write-Host "crypto_no_submit_operating_cycle_paper_submit_occurred=false"
Write-Host "crypto_no_submit_operating_cycle_broker_mutation_occurred=false"
Write-Host "crypto_no_submit_operating_cycle_live_endpoint_touched=false"
Write-Host "crypto_no_submit_operating_cycle_fresh_authorization_required_for_order=true"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $NetworkFlagsLoaded -or $LiveEndpointIndicator) {
    Write-Host "crypto_no_submit_operating_cycle_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.orchestration.crypto_no_submit_operating_cycle",
    "--output-root", $OutputRoot,
    "--crypto-refresh-output-root", $CryptoRefreshOutputRoot,
    "--router-output-root", $RouterOutputRoot,
    "--sizing-preview-output-root", $SizingPreviewOutputRoot,
    "--handoff-output-root", $HandoffOutputRoot,
    "--dry-run-output-root", $DryRunOutputRoot,
    "--autonomy-cadence-output-root", $AutonomyCadenceOutputRoot,
    "--refresh-mode", $RefreshMode,
    "--bars-csv", $BarsCsv,
    "--crypto-visibility-status", $CryptoVisibilityStatus,
    "--submit-cancel-result-path", $SubmitCancelResultPath,
    "--certification-ingestion-path", $CertificationIngestionPath,
    "--fill-exit-result-path", $FillExitResultPath,
    "--fill-exit-ingestion-path", $FillExitIngestionPath,
    "--preview-notional-cap", $PreviewNotionalCap,
    "--format", $Format
)

if (-not [string]::IsNullOrWhiteSpace($SpyBarsCsv)) {
    $Args += @("--spy-bars-csv", $SpyBarsCsv)
}
if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $Args += @("--as-of", $AsOfTimestamp)
}
if (-not [string]::IsNullOrWhiteSpace($ObservedLatestPriceArtifact)) {
    $Args += @("--observed-latest-price-artifact", $ObservedLatestPriceArtifact)
}
if ($AllowFixtureBacked.IsPresent) {
    $Args += @("--allow-fixture-backed")
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
