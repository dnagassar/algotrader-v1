<#
.SYNOPSIS
Accrues frozen ADA repair forward-OOS evidence through the existing crypto
history refresh adapter without authorizing broker reads, mutations, or submits.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_repair_forward_oos_accrual\latest",
    [string]$DiscoveryHistoryPath = "runs\operator_input\crypto_paper_bars.csv",
    [string]$AsOfTimestamp = "",
    [ValidateSet("none", "dry_run", "offline_fixture", "market_data_fetch")]
    [string]$RefreshMode = "none",
    [string]$RefreshOutputPath = "runs\operator_input\crypto_paper_bars.csv",
    [switch]$MarketDataFetchAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Python = (Get-Command python -ErrorAction Stop).Source
$Args = @(
    "-m", "algotrader.orchestration.crypto_repair_forward_oos_accrual",
    "--output-root", $OutputRoot,
    "--discovery-history-path", $DiscoveryHistoryPath,
    "--refresh-mode", $RefreshMode,
    "--refresh-output-path", $RefreshOutputPath
)
if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $Args += @("--as-of", $AsOfTimestamp)
}
if ($RefreshMode -eq "market_data_fetch" -and $MarketDataFetchAuthorized.IsPresent) {
    $Args += @("--market-data-fetch-authorized", "--allow-network")
}

Push-Location -LiteralPath $RepoRoot
try {
    & $Python @Args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
