<#
.SYNOPSIS
Builds the crypto paper-submit approval packet in no-submit mode.

.DESCRIPTION
Consumes a local v5.6 crypto Paper OMS dry-run artifact and writes an
operator-review packet for a possible future bounded paper submit/cancel
certification. This wrapper does not read a broker, mutate broker state,
submit paper orders, load credentials, or contact the network. Credential
values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_paper_submit_approval_packet\latest",
    [string]$DryRunPath = "runs\crypto_paper_oms_dry_run\latest\paper_oms_dry_run.json",
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

Write-Host "crypto_paper_submit_approval_packet_command=run_crypto_paper_submit_approval_packet"
Write-Host "crypto_paper_submit_approval_packet_mode=offline/no_submit_operator_review"
Write-Host "crypto_paper_submit_approval_packet_no_submit_enforced=true"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
Write-Host "preflight_credential_variables_loaded=$(Format-Bool $CredentialVariablesLoaded)"
Write-Host "preflight_network_flags_loaded=$(Format-Bool $NetworkFlagsLoaded)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "Credential values are never printed"
Write-Host "crypto_paper_submit_approval_packet_paper_submit_authorized=false"
Write-Host "crypto_paper_submit_approval_packet_paper_submit_performed=false"
Write-Host "crypto_paper_submit_approval_packet_broker_mutation_performed=false"
Write-Host "crypto_paper_submit_approval_packet_live_mutation_performed=false"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $NetworkFlagsLoaded -or $LiveEndpointIndicator) {
    Write-Host "crypto_paper_submit_approval_packet_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.orchestration.crypto_paper_submit_approval_packet",
    "--output-root", $OutputRoot,
    "--dry-run-path", $DryRunPath,
    "--format", $Format
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
