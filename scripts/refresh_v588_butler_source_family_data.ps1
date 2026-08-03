<#
.SYNOPSIS
Acquires the five missing V5.88 author-disclosed ETF histories.

.DESCRIPTION
Runs exactly five sequential allowlisted Tiingo EOD GETs through the existing
secure adapter. Only TIINGO_API_KEY may be loaded by the child adapter. No
broker, account, order, paper, or live-trading access occurs.
#>

[CmdletBinding()]
param(
    [ValidateSet("dry_run", "live_market_data_fetch")]
    [string]$Mode = "dry_run",
    [string]$DotenvPath = ".env",
    [string]$DataStart = "2007-07-26",
    [string]$ExpectedLatestBarDate = "2026-07-31",
    [string]$OutputRoot = "runs\v5_88_butler_exhibit3_4_source_family",
    [switch]$LiveMarketDataFetchAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
$Symbols = @("EEM", "EWJ", "ICF", "RWX", "VGK")

$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
if ($AppProfile -eq "live") {
    [Console]::Error.WriteLine("Error: APP_PROFILE is live. This refresh is research-only.")
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
    $CanonicalRoot = Join-Path $OutputRoot "canonical"
    $AcquisitionRoot = Join-Path $OutputRoot "data_acquisition"
    foreach ($Symbol in $Symbols) {
        $Stem = $Symbol.ToLowerInvariant()
        $Args = @(
            "-m", "algotrader.execution.etf_sma_adjusted_spy_data_refresh",
            "--provider", "tiingo",
            "--expected-latest-bar-date", $ExpectedLatestBarDate,
            "--output-csv", (Join-Path $AcquisitionRoot "${Stem}_normalized.csv"),
            "--canonical-csv", (Join-Path $CanonicalRoot "${Stem}_daily_tiingo_adjusted_canonical.csv"),
            "--run-log", (Join-Path $AcquisitionRoot "${Stem}_refresh_manifest.jsonl"),
            "--symbol", $Symbol,
            "--mode", $Mode,
            "--raw-response-path", (Join-Path $AcquisitionRoot "${Stem}_raw_tiingo.json"),
            "--start-date", $DataStart,
            "--dotenv-path", $DotenvPath,
            "--format", "json"
        )
        if ($LiveMarketDataFetchAuthorized) {
            $Args += "--live-market-data-fetch-authorized"
        }
        & python @Args
        if ($LASTEXITCODE -ne 0) {
            [Console]::Error.WriteLine("Error: V5.88 adjusted data refresh failed for $Symbol.")
            exit $LASTEXITCODE
        }
    }
    if ($Mode -eq "dry_run") {
        Write-Output "v588_butler_data_refresh_status=dry_run_complete"
    }
    else {
        Write-Output "v588_butler_data_refresh_status=completed"
    }
    exit 0
}
finally {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $OriginalPythonPath, "Process")
    Pop-Location
}
