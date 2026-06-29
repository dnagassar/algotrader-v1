<#
.SYNOPSIS
Runs the deterministic offline strategy challenger factory.

.DESCRIPTION
Evaluates a small controlled SPY challenger set against the current SPY SMA
50/200 paper baseline using local adjusted daily bars only. This wrapper does not read
a broker, mutate broker state, submit paper orders, load credentials, or contact
the network. Credential values are never printed.

.PARAMETER OutputRoot
Directory under which challenger factory artifacts are written.

.PARAMETER BarsCsv
Local strict daily-bars CSV to evaluate.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [string]$BarsCsv = "runs\operator_input\m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$Symbol = "SPY",
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
    Write-Host "strategy_challenger_factory_status=blocked_unsafe_environment"
    exit 2
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.research.strategy_challenger_factory",
    "--output-root", $OutputRoot,
    "--data-path", $BarsCsv,
    "--symbol", $Symbol,
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
