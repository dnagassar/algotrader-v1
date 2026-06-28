<#
.SYNOPSIS
Runs the bounded SPY paper-autopilot operator entrypoint.

.DESCRIPTION
Runs the bounded paper-autopilot loop, updates durable operating history from
latest_status.json, prints a compact operator summary, and exits with the
machine-readable health/anomaly status. Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\paper_autopilot\latest",
    [string]$HistoryRoot = "",
    [string]$BarsCsv = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$RunDate,
    [string]$Symbol = "SPY",
    [int]$SmaFastWindow = 50,
    [int]$SmaSlowWindow = 200,
    [string]$MaxNotional = "25.00",
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

$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
$AppProfileIsPaper = $AppProfile -eq "paper"
$AppProfileIsLive = $AppProfile -eq "live"
$PaperBaseUrl = [System.Environment]::GetEnvironmentVariable("ALPACA_PAPER_BASE_URL", "Process")
$LiveEndpointIndicator = $false
if (-not [string]::IsNullOrEmpty($PaperBaseUrl)) {
    $LowerUrl = $PaperBaseUrl.ToLowerInvariant()
    $LiveEndpointIndicator = $LowerUrl.Contains("api.alpaca.markets") -and -not $LowerUrl.Contains("paper")
}

Write-Host "preflight_APP_PROFILE_is_paper=$($AppProfileIsPaper.ToString().ToLowerInvariant())"
Write-Host "preflight_APP_PROFILE_is_live=$($AppProfileIsLive.ToString().ToLowerInvariant())"
Write-Host "preflight_credential_variables_loaded=$($LoadedCredentialVariables.Count)"
Write-Host "preflight_live_endpoint_indicator=$($LiveEndpointIndicator.ToString().ToLowerInvariant())"

$CliArgs = @(
    "-m", "algotrader.cli",
    "paper-autopilot-operator",
    "--output-root", $OutputRoot,
    "--bars-csv", $BarsCsv,
    "--symbol", $Symbol,
    "--sma-fast-window", $SmaFastWindow.ToString(),
    "--sma-slow-window", $SmaSlowWindow.ToString(),
    "--max-notional", $MaxNotional,
    "--format", $Format
)

if (-not [string]::IsNullOrEmpty($HistoryRoot)) {
    $CliArgs += @("--history-root", $HistoryRoot)
}

if (-not [string]::IsNullOrEmpty($AsOfDate)) {
    $CliArgs += @("--as-of-date", $AsOfDate)
}

if (-not [string]::IsNullOrEmpty($RunDate)) {
    $CliArgs += @("--run-date", $RunDate)
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
