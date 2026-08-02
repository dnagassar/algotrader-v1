<#
.SYNOPSIS
Acquires the exact V5.84 nine-ETF adjusted-daily dataset.

.DESCRIPTION
Runs nine sequential allowlisted Tiingo EOD GETs through the existing secure
adapter and builds an outcome-blind exact common-session manifest. Only
TIINGO_API_KEY may be loaded by the child adapter. No broker, account, order,
paper, or live-trading access occurs.
#>

[CmdletBinding()]
param(
    [ValidateSet("dry_run", "live_market_data_fetch")]
    [string]$Mode = "dry_run",
    [string]$DotenvPath = ".env",
    [string]$DataStart = "2011-05-05",
    [string]$ExpectedLatestBarDate = "2026-07-31",
    [string]$OutputRoot = "runs\v5_84_factor_momentum_style_proxy",
    [switch]$LiveMarketDataFetchAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
$Symbols = @("IWD", "IWF", "RSP", "VBR", "VIG", "SPLV", "SHY", "SPY", "IEF")

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
    $CanonicalRoot = Join-Path $OutputRoot "canonical_symbols"
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
            [Console]::Error.WriteLine("Error: adjusted data refresh failed for $Symbol.")
            exit $LASTEXITCODE
        }
    }
    if ($Mode -eq "dry_run") {
        Write-Output "v584_factor_momentum_data_refresh_status=dry_run_complete"
        exit 0
    }
    & python -m algotrader.research.factor_momentum_style_data_manifest `
        --output-manifest (Join-Path $OutputRoot "canonical_data_manifest.json") `
        --combined-output-csv (Join-Path $OutputRoot "canonical_data.csv") `
        --canonical-root $CanonicalRoot `
        --acquisition-root $AcquisitionRoot
    exit $LASTEXITCODE
}
finally {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $OriginalPythonPath, "Process")
    Pop-Location
}
