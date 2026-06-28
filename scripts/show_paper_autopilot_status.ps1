<#
.SYNOPSIS
Shows the latest bounded SPY paper-autopilot operating status.

.DESCRIPTION
Consumes runs\paper_autopilot\latest\latest_status.json, appends the durable
operating history, writes latest_rollup.json and operating_summary.md, and
prints a compact key=value status receipt. This script does not load
credentials, contact the network, or operate a broker.
#>

[CmdletBinding()]
param(
    [string]$LatestStatusPath = "runs\paper_autopilot\latest\latest_status.json",
    [string]$HistoryRoot = "runs\paper_autopilot\history",
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$CliArgs = @(
    "-m", "algotrader.cli",
    "paper-autopilot-history",
    "--latest-status-path", $LatestStatusPath,
    "--history-root", $HistoryRoot,
    "--format", $Format
)

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
