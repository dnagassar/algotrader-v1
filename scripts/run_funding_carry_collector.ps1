<#
.SYNOPSIS
Collects the V6.05 continuously-held funding carry canonical series.

.DESCRIPTION
Fetches Deribit funding and perpetual marks through the existing audited
perp_funding_refresh_adapter and writes the four canonical daily series the
V6.05 forward shadow reads: BTCCARRY, ETHCARRY, SOLCARRY and USDCASH.

GET-only against a single allowlisted public venue. Deribit's public endpoints
require no authentication and the collector has no code path that can read an
environment variable, dotenv, or credential store.

It does not append to the shadow ledger. Collection and observation are separate
acts on purpose: a collector that also recorded observations could re-record a
session after seeing how it turned out.

No broker, account, order, paper, or live-trading access occurs.
#>

[CmdletBinding()]
param(
    [ValidateSet("dry_run", "live_market_data_fetch")]
    [string]$Mode = "dry_run",
    [string]$OutputRoot = "runs\v6_05_funding_carry_collection",
    [string]$CanonicalCsv = "runs\v6_05_funding_carry_collection\canonical\carry_daily_bars.csv",
    [int]$LookbackDays = 14,
    [switch]$LiveMarketDataFetchAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")

$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
if ($AppProfile -eq "live") {
    [Console]::Error.WriteLine("Error: APP_PROFILE is live. This collector is research-only.")
    exit 2
}
if ($Mode -eq "live_market_data_fetch" -and -not $LiveMarketDataFetchAuthorized) {
    [Console]::Error.WriteLine("Error: live fetch requires explicit authorization.")
    exit 2
}
if ($Mode -eq "dry_run" -and $LiveMarketDataFetchAuthorized) {
    [Console]::Error.WriteLine("Error: authorization flag requires live fetch mode.")
    exit 2
}

Push-Location -LiteralPath $RepoRoot
try {
    $PythonParts = @($RepoSrc)
    if (-not [string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $PythonParts += $OriginalPythonPath
    }
    [System.Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        ($PythonParts -join [System.IO.Path]::PathSeparator),
        "Process"
    )
    $Args = @(
        "-m", "algotrader.execution.funding_carry_collector",
        "--output-root", $OutputRoot,
        "--canonical-csv", $CanonicalCsv,
        "--mode", $Mode,
        "--lookback-days", $LookbackDays
    )
    if ($LiveMarketDataFetchAuthorized) {
        $Args += "--live-market-data-fetch-authorized"
    }
    & python @Args
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -ne 0) {
        [Console]::Error.WriteLine("Error: funding carry collection did not complete.")
        exit $ExitCode
    }
    Write-Output "funding_carry_collection_status=completed"
    exit 0
}
finally {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $OriginalPythonPath, "Process")
    Pop-Location
}
