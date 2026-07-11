<#
.SYNOPSIS
Accrues frozen ADA repair forward-OOS evidence through the existing crypto
history refresh adapter without authorizing broker reads, mutations, or submits.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_repair_forward_oos_accrual\latest",
    [Alias("DiscoveryHistoryPath")]
    [string]$DiscoveryRecoverySourcePath = "",
    [string]$AsOfTimestamp = "",
    [ValidateSet("none", "dry_run", "offline_fixture", "market_data_fetch")]
    [string]$RefreshMode = "none",
    [string]$RefreshOutputPath = "",
    [string]$RefreshPacketPath = "",
    [string]$RefreshRawResponsePath = "",
    [string]$RefreshStart = "",
    [string]$RefreshEnd = "",
    [switch]$MarketDataFetchAuthorized,
    [switch]$InvalidateFrozenCandidateState,
    [string]$InvalidationReason = "",
    [string]$InvalidationArchivePath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Python = (Get-Command python -ErrorAction Stop).Source
$ResolvedRefreshOutputPath = $RefreshOutputPath
if ([string]::IsNullOrWhiteSpace($ResolvedRefreshOutputPath)) {
    $ResolvedRefreshOutputPath = Join-Path $OutputRoot "refresh\forward_oos_delta.csv"
}
$ResolvedRefreshPacketPath = $RefreshPacketPath
if ([string]::IsNullOrWhiteSpace($ResolvedRefreshPacketPath)) {
    $ResolvedRefreshPacketPath = Join-Path $OutputRoot "refresh\refresh_packet.json"
}
$ResolvedRefreshRawResponsePath = $RefreshRawResponsePath
if ([string]::IsNullOrWhiteSpace($ResolvedRefreshRawResponsePath)) {
    $ResolvedRefreshRawResponsePath = Join-Path $OutputRoot "refresh\raw_crypto_bars.json"
}
$Args = @(
    "-m", "algotrader.orchestration.crypto_repair_forward_oos_accrual",
    "--output-root", $OutputRoot,
    "--refresh-mode", $RefreshMode,
    "--refresh-output-path", $ResolvedRefreshOutputPath,
    "--refresh-packet-path", $ResolvedRefreshPacketPath,
    "--refresh-raw-response-path", $ResolvedRefreshRawResponsePath
)
if (-not [string]::IsNullOrWhiteSpace($DiscoveryRecoverySourcePath)) {
    $Args += @(
        "--discovery-recovery-source-path",
        $DiscoveryRecoverySourcePath
    )
}
if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $Args += @("--as-of", $AsOfTimestamp)
}
if (-not [string]::IsNullOrWhiteSpace($RefreshStart)) {
    $Args += @("--refresh-start", $RefreshStart)
}
if (-not [string]::IsNullOrWhiteSpace($RefreshEnd)) {
    $Args += @("--refresh-end", $RefreshEnd)
}
if ($RefreshMode -eq "market_data_fetch" -and $MarketDataFetchAuthorized.IsPresent) {
    $Args += @("--market-data-fetch-authorized", "--allow-network")
}
if ($InvalidateFrozenCandidateState.IsPresent) {
    $Args += @("--invalidate-frozen-candidate-state")
    if (-not [string]::IsNullOrWhiteSpace($InvalidationReason)) {
        $Args += @("--invalidation-reason", $InvalidationReason)
    }
    if (-not [string]::IsNullOrWhiteSpace($InvalidationArchivePath)) {
        $Args += @("--invalidation-archive-path", $InvalidationArchivePath)
    }
}

Push-Location -LiteralPath $RepoRoot
try {
    & $Python @Args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
