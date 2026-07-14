<#
.SYNOPSIS
Plans or runs an explicitly gated adjusted ETF daily-bars refresh.

.DESCRIPTION
Builds a deterministic Tiingo adjusted ETF refresh plan, optionally normalizes
an offline fixture, or executes an exact-destination HTTPS GET only when the live
mode and explicit authorization switch are both supplied.  The default mode is
dry_run.  Paper profile and broker variables may coexist, but only TIINGO_API_KEY
can be loaded or sent.  This script does not read broker state, mutate broker
state, submit paper orders, authorize live trading, or print/write token values.
#>

[CmdletBinding()]
param(
    [ValidateSet("tiingo")]
    [string]$Provider = "tiingo",
    [string]$ExpectedLatestBarDate,
    [Parameter(Mandatory = $true)]
    [string]$OutputCsv,
    [Parameter(Mandatory = $true)]
    [string]$CanonicalCsv,
    [Parameter(Mandatory = $true)]
    [string]$RunLog,
    [ValidateSet("SPY", "QQQ", "IWM", "TLT", "GLD")]
    [string]$Symbol = "SPY",
    [ValidateSet("offline_fixture", "dry_run", "live_market_data_fetch")]
    [string]$Mode = "dry_run",
    [string]$FixtureInputPath,
    [string]$RawResponsePath,
    [string]$StartDate = "auto",
    [ValidateRange(1, 31)]
    [int]$RevisionLookbackDays = 10,
    [string]$DotenvPath = ".env",
    [switch]$LiveMarketDataFetchAuthorized,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
if ($AppProfile -eq "live") {
    [Console]::Error.WriteLine("Error: APP_PROFILE is live. This refresh is paper-lab only.")
    exit 2
}

$CliArgs = @(
    "-m", "algotrader.execution.etf_sma_adjusted_spy_data_refresh",
    "--provider", $Provider,
    "--output-csv", $OutputCsv,
    "--canonical-csv", $CanonicalCsv,
    "--run-log", $RunLog,
    "--symbol", $Symbol,
    "--mode", $Mode,
    "--start-date", $StartDate,
    "--revision-lookback-days", $RevisionLookbackDays,
    "--dotenv-path", $DotenvPath,
    "--format", $Format
)

if (-not [string]::IsNullOrEmpty($ExpectedLatestBarDate)) {
    $CliArgs += @("--expected-latest-bar-date", $ExpectedLatestBarDate)
}

if (-not [string]::IsNullOrEmpty($FixtureInputPath)) {
    $CliArgs += @("--fixture-input-path", $FixtureInputPath)
}

if (-not [string]::IsNullOrEmpty($RawResponsePath)) {
    $CliArgs += @("--raw-response-path", $RawResponsePath)
}

if ($LiveMarketDataFetchAuthorized) {
    $CliArgs += @("--live-market-data-fetch-authorized")
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
