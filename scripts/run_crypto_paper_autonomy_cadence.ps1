<#
.SYNOPSIS
Runs the supervised crypto paper autonomy cadence controller in no-submit mode.

.DESCRIPTION
Consumes local router, sizing, handoff, dry-run, and certification-ingestion
artifacts to produce a recurring no-submit operating packet. This wrapper does
not read a broker, mutate broker state, submit paper orders, load credentials,
or contact the network. Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_paper_autonomy_cadence\latest",
    [string]$SubmitCancelResultPath = "runs\crypto_paper_submit_cancel_certification\latest\certification_result.json",
    [string]$CertificationIngestionPath = "runs\crypto_paper_certification_ingestion\latest\certification_ingestion.json",
    [string]$FillExitResultPath = "runs\crypto_paper_fill_exit_certification\latest\fill_exit_certification_result.json",
    [string]$FillExitIngestionPath = "runs\crypto_paper_fill_exit_ingestion\latest\fill_exit_ingestion.json",
    [string]$RouterDecisionPath = "runs\opportunity_router\paper_read_repair_latest\router_decision.json",
    [string]$SizingPreviewPath = "runs\crypto_qty_sizing_preview\latest\sizing_preview.json",
    [string]$HandoffPath = "runs\crypto_paper_oms_handoff\latest\paper_oms_handoff.json",
    [string]$DryRunPath = "runs\crypto_paper_oms_dry_run\latest\paper_oms_dry_run.json",
    [string]$AsOfTimestamp = "",
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

Write-Host "crypto_paper_autonomy_cadence_command=run_crypto_paper_autonomy_cadence"
Write-Host "crypto_paper_autonomy_cadence_mode=offline/no_submit"
Write-Host "crypto_paper_autonomy_cadence_no_submit_enforced=true"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
Write-Host "preflight_credential_variables_loaded=$(Format-Bool $CredentialVariablesLoaded)"
Write-Host "preflight_network_flags_loaded=$(Format-Bool $NetworkFlagsLoaded)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "Credential values are never printed"
Write-Host "crypto_paper_autonomy_cadence_paper_submit_authorized=false"
Write-Host "crypto_paper_autonomy_cadence_paper_submit_performed=false"
Write-Host "crypto_paper_autonomy_cadence_broker_read_performed=false"
Write-Host "crypto_paper_autonomy_cadence_broker_mutation_performed=false"
Write-Host "crypto_paper_autonomy_cadence_live_mutation_performed=false"
Write-Host "crypto_paper_autonomy_cadence_fresh_authorization_required_for_order=true"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $NetworkFlagsLoaded -or $LiveEndpointIndicator) {
    Write-Host "crypto_paper_autonomy_cadence_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.orchestration.crypto_paper_autonomy_cadence",
    "--output-root", $OutputRoot,
    "--submit-cancel-result-path", $SubmitCancelResultPath,
    "--certification-ingestion-path", $CertificationIngestionPath,
    "--fill-exit-result-path", $FillExitResultPath,
    "--fill-exit-ingestion-path", $FillExitIngestionPath,
    "--router-decision-path", $RouterDecisionPath,
    "--sizing-preview-path", $SizingPreviewPath,
    "--handoff-path", $HandoffPath,
    "--dry-run-path", $DryRunPath,
    "--format", $Format
)

if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $Args += @("--as-of", $AsOfTimestamp)
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
