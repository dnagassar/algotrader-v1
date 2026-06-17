<#
.SYNOPSIS
Runs the daily SPY SMA paper-lab loop.

.DESCRIPTION
Validates safety prechecks, resolves repository root and output root, and
runs the offline-only ETF/SMA daily paper-lab command.

.PARAMETER OutputRoot
Root directory under which the daily paper-lab operating packet is written. Required.

.PARAMETER BarsCsv
Path to the canonical daily bars CSV file. Defaults to runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv.

.PARAMETER AsOfDate
Explicit as-of date (YYYY-MM-DD). If omitted, derived from input bars.

.PARAMETER Symbol
Symbol to evaluate. Defaults to SPY.

.PARAMETER SmaFastWindow
SMA fast window size. Defaults to 50.

.PARAMETER SmaSlowWindow
SMA slow window size. Defaults to 200.

.PARAMETER BrokerStateMode
Broker-state lane mode. Defaults to broker_state_not_observed. alpaca_paper_read_only
is scaffold-only in v1.33 and performs no broker read.

.PARAMETER Format
Output format (text or json). Defaults to text.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [string]$BarsCsv = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$Symbol = "SPY",
    [int]$SmaFastWindow = 50,
    [int]$SmaSlowWindow = 200,
    [ValidateSet("broker_state_not_observed", "offline_fixture", "alpaca_paper_read_only")]
    [string]$BrokerStateMode = "broker_state_not_observed",
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

# Safety Precheck
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
    [Console]::Error.WriteLine("Error: APP_PROFILE is paper. Daily paper-lab assistant must run offline only without paper profile.")
    exit 2
}

if ($LoadedCredentialVariables.Count -gt 0) {
    [Console]::Error.WriteLine("Error: broker credential environment variable(s) are loaded: $($LoadedCredentialVariables -join ', '). Daily paper-lab assistant must run offline only without credentials.")
    exit 2
}

# Resolve OutputRoot parent
$AbsoluteOutputRoot = $OutputRoot
if (-not [System.IO.Path]::IsPathRooted($OutputRoot)) {
    $AbsoluteOutputRoot = Join-Path $RepoRoot $OutputRoot
}

# Ensure OutputRoot exists
if (-not (Test-Path -LiteralPath $AbsoluteOutputRoot)) {
    New-Item -ItemType Directory -Force -Path $AbsoluteOutputRoot | Out-Null
}

$CliArgs = @(
    "-m", "algotrader.cli",
    "etf-sma-daily-paper-lab",
    "--output-root", $AbsoluteOutputRoot,
    "--bars-csv", $BarsCsv,
    "--symbol", $Symbol,
    "--sma-fast-window", $SmaFastWindow,
    "--sma-slow-window", $SmaSlowWindow,
    "--broker-state-mode", $BrokerStateMode,
    "--format", $Format
)

if (-not [string]::IsNullOrEmpty($AsOfDate)) {
    $CliArgs += @("--as-of-date", $AsOfDate)
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
