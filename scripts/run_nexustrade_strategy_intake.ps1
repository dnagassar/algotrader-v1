<#
.SYNOPSIS
Runs the offline NexusTrade strategy-intake and local-replay lane.

.DESCRIPTION
Consumes a bounded local JSON capture of NexusTrade strategy definitions and
source backtest metadata. Eligible daily candidates are routed into the
existing deterministic challenger factory. The wrapper does not contact
NexusTrade, read a broker, load credentials, submit orders, or authorize paper
or live trading. Credential values are never printed.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [string]$BarsCsv = "runs\operator_input\multi_etf_adjusted_daily_canonical.csv",
    [string]$AsOfDate,
    [string]$InitialEquity = "10000",
    [string]$FeeBps = "0",
    [string]$SlippageBps = "0"
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
$SensitiveNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "NEXUSTRADE_API_KEY"
)
$SensitiveVariablesLoaded = $false
foreach ($Name in $SensitiveNames) {
    if (Test-EnvLoaded -Name $Name) {
        $SensitiveVariablesLoaded = $true
    }
}

Write-Host "preflight_APP_PROFILE_is_paper=$($AppProfileIsPaper.ToString().ToLowerInvariant())"
Write-Host "preflight_APP_PROFILE_is_live=$($AppProfileIsLive.ToString().ToLowerInvariant())"
Write-Host "preflight_sensitive_variables_loaded=$($SensitiveVariablesLoaded.ToString().ToLowerInvariant())"
Write-Host "Credential values are never printed"

if ($AppProfileIsPaper -or $AppProfileIsLive -or $SensitiveVariablesLoaded) {
    Write-Host "nexustrade_strategy_intake_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.research.nexustrade_strategy_intake",
    "--input-path", $InputPath,
    "--output-root", $OutputRoot,
    "--data-path", $BarsCsv,
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
