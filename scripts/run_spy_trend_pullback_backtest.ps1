<#
.SYNOPSIS
Runs the deterministic fixed-parameter SPY trend-pullback backtest gate.

.DESCRIPTION
Evaluates the SPY trend-pullback shadow challenger against buy-and-hold SPY,
the SMA50/200 training-wheel baseline, and the rejected RSI-14 comparator using
local adjusted daily bars only. This wrapper does not read a broker, mutate broker state,
submit paper orders, load credentials, or contact the network.
Credential values are never printed.

.PARAMETER OutputRoot
Directory under which ignored trend-pullback artifacts are written.

.PARAMETER BarsCsv
Local strict SPY daily-bars CSV to evaluate.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\strategy_challengers\trend_pullback\latest",
    [string]$BarsCsv = "runs\operator_input\m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$RunId = "v3_9_spy_trend_pullback_fixed_parameter_backtest",
    [string]$InitialEquity = "10000",
    [string]$FeeBps = "0",
    [string]$SlippageBps = "1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Test-EnvLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    return -not [string]::IsNullOrEmpty($Value)
}

function Get-PythonCommand {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $PythonCommand) {
        return $PythonCommand.Source
    }
    throw "Unable to locate python on PATH."
}

$AppProfile = [Environment]::GetEnvironmentVariable("APP_PROFILE")
$AppProfileIsPaper = ($AppProfile -eq "paper")
$AppProfileIsLive = ($AppProfile -eq "live")
$CredentialNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
$CredentialVariablesLoaded = $false
foreach ($Name in $CredentialNames) {
    if (Test-EnvLoaded -Name $Name) {
        $CredentialVariablesLoaded = $true
    }
}

Write-Host "preflight_APP_PROFILE_is_paper=$($AppProfileIsPaper.ToString().ToLowerInvariant())"
Write-Host "preflight_APP_PROFILE_is_live=$($AppProfileIsLive.ToString().ToLowerInvariant())"
Write-Host "preflight_credential_variables_loaded=$($CredentialVariablesLoaded.ToString().ToLowerInvariant())"
Write-Host "Credential values are never printed"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded) {
    Write-Host "spy_trend_pullback_backtest_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.research.spy_trend_pullback_backtest",
    "--output-root", $OutputRoot,
    "--daily-bars-csv", $BarsCsv,
    "--run-id", $RunId,
    "--initial-equity", $InitialEquity,
    "--fee-bps", $FeeBps,
    "--slippage-bps", $SlippageBps
)

if (-not [string]::IsNullOrEmpty($AsOfDate)) {
    $Args += @("--as-of-date", $AsOfDate)
}

Push-Location -LiteralPath $RepoRoot
try {
    & $Python @Args
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
