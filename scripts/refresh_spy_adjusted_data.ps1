<#
.SYNOPSIS
Plans or runs an explicitly gated adjusted SPY daily-bars refresh.

.DESCRIPTION
Builds a deterministic Tiingo adjusted SPY refresh plan, optionally normalizes
an offline fixture, or executes a live market-data fetch only when the live mode
and explicit authorization switch are both supplied.  The default mode is
dry_run.  This script does not read broker state, mutate broker state, submit
paper orders, authorize live trading, or print/write token values.
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
    [ValidateSet("offline_fixture", "dry_run", "live_market_data_fetch")]
    [string]$Mode = "dry_run",
    [string]$FixtureInputPath,
    [string]$RawResponsePath,
    [string]$StartDate = "auto",
    [string]$DotenvPath = ".env",
    [switch]$LiveMarketDataFetchAuthorized,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$CredentialVariableNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)

function Test-ProcessEnvironmentVariableLoaded {
    param([string]$Name)
    $ProcessEnvironment = [System.Environment]::GetEnvironmentVariables("Process")
    return $ProcessEnvironment.Contains($Name)
}

$LoadedCredentialVariables = @()
foreach ($Name in $CredentialVariableNames) {
    if (Test-ProcessEnvironmentVariableLoaded -Name $Name) {
        $LoadedCredentialVariables += $Name
    }
}

$AppProfileIsPaper = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process") -eq "paper"
if ($AppProfileIsPaper) {
    [Console]::Error.WriteLine("Error: APP_PROFILE is paper. Market-data refresh must run without paper profile.")
    exit 2
}

if ($LoadedCredentialVariables.Count -gt 0) {
    [Console]::Error.WriteLine("Error: broker credential environment variable(s) are loaded: $($LoadedCredentialVariables -join ', '). Market-data refresh must run without broker credentials.")
    exit 2
}

$CliArgs = @(
    "-m", "algotrader.execution.etf_sma_adjusted_spy_data_refresh",
    "--provider", $Provider,
    "--output-csv", $OutputCsv,
    "--canonical-csv", $CanonicalCsv,
    "--run-log", $RunLog,
    "--mode", $Mode,
    "--start-date", $StartDate,
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
