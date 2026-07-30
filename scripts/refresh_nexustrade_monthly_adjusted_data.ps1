<#
.SYNOPSIS
Refreshes the exact NexusTrade monthly stock universe from Tiingo.

.DESCRIPTION
Runs twelve sequential, independently gated Tiingo EOD GETs through the
repository's existing bounded market-data adapter, then builds the offline
coverage/session/hash manifest and combined canonical CSV. The default mode is
dry_run. Only TIINGO_API_KEY may be loaded by the child adapter. This script
does not read broker state, mutate broker state, submit paper orders, authorize
live trading, print credential values, or copy the dotenv file.
#>

[CmdletBinding()]
param(
    [ValidateSet("dry_run", "live_market_data_fetch")]
    [string]$Mode = "dry_run",
    [string]$DotenvPath = ".env",
    [string]$DataStart = "2019-01-02",
    [string]$ExpectedLatestBarDate = "2025-03-28",
    [string]$OutputRoot = "runs\v5_63_nexustrade_canonical_data",
    [string]$CanonicalRoot = "runs\operator_input",
    [string]$CombinedOutputCsv = "runs\operator_input\multi_etf_adjusted_daily_canonical.csv",
    [switch]$LiveMarketDataFetchAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable(
    "PYTHONPATH",
    "Process"
)
$Symbols = @(
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    "GS",
    "JPM",
    "BRK-B",
    "COST",
    "SPY"
)

$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
if ($AppProfile -eq "live") {
    [Console]::Error.WriteLine("Error: APP_PROFILE is live. This refresh is research-only.")
    exit 2
}
if ($Mode -eq "live_market_data_fetch" -and -not $LiveMarketDataFetchAuthorized) {
    [Console]::Error.WriteLine(
        "Error: live_market_data_fetch requires -LiveMarketDataFetchAuthorized."
    )
    exit 2
}
if ($Mode -eq "dry_run" -and $LiveMarketDataFetchAuthorized) {
    [Console]::Error.WriteLine(
        "Error: -LiveMarketDataFetchAuthorized requires live_market_data_fetch mode."
    )
    exit 2
}

Push-Location -LiteralPath $RepoRoot
try {
    $PythonPathParts = @($RepoSrc)
    if (-not [string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $PythonPathParts += $OriginalPythonPath
    }
    [System.Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        ($PythonPathParts -join [System.IO.Path]::PathSeparator),
        "Process"
    )
    foreach ($Symbol in $Symbols) {
        $FileStem = $Symbol.ToLowerInvariant()
        $CanonicalName = "${FileStem}_daily_tiingo_adjusted_canonical.csv"
        if ($Symbol -eq "SPY") {
            $CanonicalName = "m446_spy_daily_tiingo_adjusted_canonical.csv"
        }
        $CliArgs = @(
            "-m", "algotrader.execution.etf_sma_adjusted_spy_data_refresh",
            "--provider", "tiingo",
            "--expected-latest-bar-date", $ExpectedLatestBarDate,
            "--output-csv", (Join-Path $OutputRoot "${FileStem}_normalized.csv"),
            "--canonical-csv", (Join-Path $CanonicalRoot $CanonicalName),
            "--run-log", (Join-Path $OutputRoot "${FileStem}_refresh_manifest.jsonl"),
            "--symbol", $Symbol,
            "--mode", $Mode,
            "--raw-response-path", (Join-Path $OutputRoot "${FileStem}_raw_tiingo.json"),
            "--start-date", $DataStart,
            "--dotenv-path", $DotenvPath,
            "--format", "json"
        )
        if ($LiveMarketDataFetchAuthorized) {
            $CliArgs += "--live-market-data-fetch-authorized"
        }
        & python @CliArgs
        if ($LASTEXITCODE -ne 0) {
            [Console]::Error.WriteLine("Error: adjusted data refresh failed for $Symbol.")
            exit $LASTEXITCODE
        }
    }

    if ($Mode -eq "dry_run") {
        Write-Output "nexustrade_monthly_adjusted_data_refresh_status=dry_run_complete"
        exit 0
    }

    $ManifestArgs = @(
        "-m", "algotrader.research.nexustrade_monthly_adjusted_data_manifest",
        "--output-manifest", (Join-Path $OutputRoot "canonical_data_manifest.json"),
        "--combined-output-csv", $CombinedOutputCsv,
        "--data-start", $DataStart,
        "--train-start", "2021-12-31",
        "--train-end", "2024-03-24",
        "--oos-start", "2024-03-24",
        "--oos-end", $ExpectedLatestBarDate,
        "--minimum-pretraining-sessions", "365"
    )
    foreach ($Symbol in $Symbols) {
        $FileStem = $Symbol.ToLowerInvariant()
        $CanonicalName = "${FileStem}_daily_tiingo_adjusted_canonical.csv"
        if ($Symbol -eq "SPY") {
            $CanonicalName = "m446_spy_daily_tiingo_adjusted_canonical.csv"
        }
        $ManifestArgs += @(
            "--canonical-path",
            "$Symbol=$(Join-Path $CanonicalRoot $CanonicalName)"
        )
    }
    & python @ManifestArgs
    exit $LASTEXITCODE
}
finally {
    [System.Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        $OriginalPythonPath,
        "Process"
    )
    Pop-Location
}
