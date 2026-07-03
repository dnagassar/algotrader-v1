<#
.SYNOPSIS
Runs the crypto paper visibility cycle in no-submit mode.

.DESCRIPTION
Runs read-only crypto capability discovery and the crypto preview lane without
any paper submit, broker mutation, live mutation, or submit mode.
Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_paper_visibility\latest",
    [string]$BarsCsv = "runs\operator_input\crypto_paper_bars.csv",
    [string]$AsOfTimestamp,
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
if (-not [string]::IsNullOrWhiteSpace($PaperBaseUrl)) {
    $LowerUrl = $PaperBaseUrl.ToLowerInvariant()
    if ($LowerUrl.Contains("alpaca") -and -not $LowerUrl.Contains("paper")) {
        $LiveEndpointIndicator = $true
    }
}

Write-Host "crypto_visibility_command=run_crypto_paper_visibility_cycle"
Write-Host "crypto_visibility_operating_mode=visibility/no_submit"
Write-Host "crypto_visibility_no_submit_enforced=true"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
foreach ($Name in $CredentialVariableNames) {
    Write-Host "preflight_$($Name)_present=$(Format-Bool (Test-ProcessEnvironmentVariableLoaded -Name $Name))"
}
Write-Host "preflight_paper_endpoint_exact_match_indicator=$(Format-Bool $PaperEndpointExactMatchIndicator)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "crypto_visibility_paper_submit_performed=false"
Write-Host "crypto_visibility_broker_mutation_performed=false"
Write-Host "crypto_visibility_live_mutation_performed=false"

if ($LiveEndpointIndicator) {
    Write-Host "crypto_visibility_stop_reason=live_endpoint_indicator"
    exit 2
}

$CliArgs = @(
    "-m", "algotrader.execution.crypto_paper_visibility_operator",
    "--output-root", $OutputRoot,
    "--bars-csv", $BarsCsv,
    "--format", $Format
)

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
