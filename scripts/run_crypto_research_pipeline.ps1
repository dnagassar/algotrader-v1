<#
.SYNOPSIS
Runs the deterministic v5.21 crypto research pipeline from local CSV history.

.DESCRIPTION
This runner is offline by default and exposes no network, credential, broker
read, submit, or mutation switch. Refresh local history separately through the
existing explicitly authorized adapters when needed.
#>

[CmdletBinding()]
param(
    [string[]]$InputCsv = @(),
    [string]$AsOfTimestamp = "2026-07-09T16:00:00Z",
    [string]$OutputRoot = "runs\crypto_research_pipeline\latest",
    [string]$Symbols = "BTCUSD,ETHUSD,SOLUSD,ADAUSD",
    [string]$AvailabilityJson = "",
    [string]$DiscoveryCutoff = "2026-07-09T16:00:00Z",
    [string]$ForwardOosStateRoot = "runs\crypto_repair_forward_oos_accrual\latest",
    [string]$ForwardOosDiscoveryHistoryPath = "runs\operator_input\crypto_paper_bars.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Python = (Get-Command python -ErrorAction Stop).Source
$Args = @(
    "-m", "algotrader.orchestration.crypto_research_pipeline",
    "--as-of", $AsOfTimestamp,
    "--output-root", $OutputRoot,
    "--symbols", $Symbols,
    "--discovery-cutoff", $DiscoveryCutoff,
    "--forward-oos-state-root", $ForwardOosStateRoot
)
foreach ($Path in $InputCsv) {
    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        $Args += @("--input-csv", $Path)
    }
}
if (-not [string]::IsNullOrWhiteSpace($AvailabilityJson)) {
    $Args += @("--availability-json", $AvailabilityJson)
}
if (-not [string]::IsNullOrWhiteSpace($ForwardOosDiscoveryHistoryPath)) {
    $Args += @(
        "--forward-oos-discovery-history-path",
        $ForwardOosDiscoveryHistoryPath
    )
}

Push-Location -LiteralPath $RepoRoot
try {
    & $Python @Args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
