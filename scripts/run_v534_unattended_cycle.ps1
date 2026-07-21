<#
.SYNOPSIS
Runs the V5.34 unattended paper-observed OOS operating cycle wrapper.

.DESCRIPTION
Invokes the V5.34 autonomous cycle CLI command using only the credentials
already present in the invoking process environment. This wrapper never loads
plaintext credential files, never falls back to another checkout's
environment, and never duplicates secrets into alternate variable names.
Until an explicitly selected non-plaintext unattended credential mechanism is
configured, scheduled activation remains classified as
blocked_unattended_secret_loading.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_34_operating_cycle\latest",
    [string]$SchedulerOutputRoot = "runs\crypto_strategy_tournament\v2\latest",
    [string]$DiscoverySourcePath = "runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv",
    [string]$DiscoveryReceiptPath = "runs\crypto_strategy_tournament\v1\refresh\refresh_packet.json",
    [string]$DbPath = "",
    [switch]$SchedulerEnabled,
    [switch]$MarketDataReadAuthorized,
    [switch]$PaperBrokerReadAuthorized,
    [switch]$AllowNetwork,
    [string]$AsOf = "",
    [ValidateSet("manual", "scheduled")]
    [string]$InvocationSource = "manual"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$Arguments = @(
    "-m",
    "algotrader.cli",
    "v534-unattended-cycle",
    "--output-root",
    $OutputRoot,
    "--scheduler-output-root",
    $SchedulerOutputRoot,
    "--discovery-source",
    $DiscoverySourcePath,
    "--discovery-receipt",
    $DiscoveryReceiptPath,
    "--invocation-source",
    $InvocationSource
)

if (-not [string]::IsNullOrWhiteSpace($DbPath)) {
    $Arguments += @("--db-path", $DbPath)
}
if (-not [string]::IsNullOrWhiteSpace($AsOf)) {
    $Arguments += @("--as-of", $AsOf)
}
if ($SchedulerEnabled.IsPresent) {
    $Arguments += @("--scheduler-enabled")
}
if ($MarketDataReadAuthorized.IsPresent) {
    $Arguments += @("--market-data-read-authorized")
}
if ($PaperBrokerReadAuthorized.IsPresent) {
    $Arguments += @("--paper-broker-read-authorized")
}
if ($AllowNetwork.IsPresent) {
    $Arguments += @("--allow-network")
}

$ExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    python @Arguments
    $ExitCode = $LASTEXITCODE
}
catch {
    $ExitCode = 1
    throw
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
