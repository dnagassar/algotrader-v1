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
is scaffold-only and performs no broker read.

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

if ($ExitCode -eq 0 -and $Format -eq "text") {
    $IndexPath = Join-Path $AbsoluteOutputRoot "index.html"
    $OperatorReviewPath = Join-Path $AbsoluteOutputRoot "operator_review.md"
    $LatestRunPath = Join-Path $AbsoluteOutputRoot "latest_run.json"
    $ValidationPath = Join-Path $AbsoluteOutputRoot "mission_control_validation.json"
    $BrokerStateModeText = $BrokerStateMode

    if (Test-Path -LiteralPath $LatestRunPath) {
        try {
            $LatestRun = Get-Content -LiteralPath $LatestRunPath -Raw | ConvertFrom-Json
            if ($LatestRun.broker_state_mode) {
                $BrokerStateModeText = [string]$LatestRun.broker_state_mode
            }
        }
        catch {
            $BrokerStateModeText = $BrokerStateMode
        }
    }

    Write-Host ""
    Write-Host "Mission Control generated."
    Write-Host "Open first: $IndexPath"
    Write-Host "Operator review: $OperatorReviewPath"
    Write-Host "Latest run summary: $LatestRunPath"
    Write-Host "Validation: $ValidationPath"
    Write-Host "Paper submit authorized: false"
    Write-Host "Live authorized: false"
    Write-Host "Broker read performed: false"
    Write-Host "Broker mutation performed: false"
    Write-Host "Broker-state mode: $BrokerStateModeText"
}

exit $ExitCode
