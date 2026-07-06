<#
.SYNOPSIS
Runs the v5.14 crypto router input refresh packet.

.DESCRIPTION
Inventories local crypto router inputs, repairs only from local or deterministic
fixture-backed sources, and reruns the v5.13 no-submit operating cycle. This
wrapper does not read a broker, mutate broker state, submit paper orders, load
credentials, or contact the network. Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_router_input_refresh_packet\latest",
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
    [string]$AsOfTimestamp = "",
    [bool]$AllowFixtureRepair = $true,
    [switch]$RequestPaperReadRepair,
    [switch]$RequestMarketDataRefresh,
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

Write-Host "crypto_router_input_refresh_packet_command=run_crypto_router_input_refresh_packet"
Write-Host "crypto_router_input_refresh_packet_mode=offline/no_submit"
Write-Host "crypto_router_input_refresh_packet_refresh_mode=$RefreshMode"
Write-Host "crypto_router_input_refresh_packet_allow_fixture_repair=$(Format-Bool $AllowFixtureRepair)"
Write-Host "crypto_router_input_refresh_packet_no_submit_enforced=true"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
Write-Host "preflight_credential_variables_loaded=$(Format-Bool $CredentialVariablesLoaded)"
Write-Host "preflight_network_flags_loaded=$(Format-Bool $NetworkFlagsLoaded)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "Credential values are never printed"
Write-Host "crypto_router_input_refresh_packet_broker_read_occurred=false"
Write-Host "crypto_router_input_refresh_packet_paper_submit_authorized=false"
Write-Host "crypto_router_input_refresh_packet_paper_submit_occurred=false"
Write-Host "crypto_router_input_refresh_packet_broker_mutation_occurred=false"
Write-Host "crypto_router_input_refresh_packet_live_endpoint_touched=false"
Write-Host "crypto_router_input_refresh_packet_fresh_authorization_required_for_order=true"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $NetworkFlagsLoaded -or $LiveEndpointIndicator) {
    Write-Host "crypto_router_input_refresh_packet_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.orchestration.crypto_router_input_refresh_packet",
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
if ($AllowFixtureRepair) {
    $Args += @("--allow-fixture-repair")
}
if ($RequestPaperReadRepair.IsPresent) {
    $Args += @("--request-paper-read-repair")
}
if ($RequestMarketDataRefresh.IsPresent) {
    $Args += @("--request-market-data-refresh")
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
