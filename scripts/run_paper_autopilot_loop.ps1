<#
.SYNOPSIS
Runs the bounded SPY SMA paper-autopilot operating loop.

.DESCRIPTION
Runs the daily SPY SMA paper-lab cycle, observes verified Alpaca paper broker
state, creates an immutable ExecutionPlan, performs at most one bounded
paper-only action when the plan permits, reconciles, and writes operating
artifacts. Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\paper_autopilot\latest",
    [string]$BarsCsv = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$RunDate,
    [string]$Symbol = "SPY",
    [int]$SmaFastWindow = 50,
    [int]$SmaSlowWindow = 200,
    [string]$MaxNotional = "25.00",
    [string]$ReadinessPacketPath,
    [string]$OrderJournalPath = "runs\paper_autopilot\state\order_journal.sqlite3",
    [switch]$NoSubmit,
    [switch]$OperatorPaused,
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
    "paper-autopilot-loop",
    "--output-root", $OutputRoot,
    "--bars-csv", $BarsCsv,
    "--symbol", $Symbol,
    "--sma-fast-window", $SmaFastWindow.ToString(),
    "--sma-slow-window", $SmaSlowWindow.ToString(),
    "--max-notional", $MaxNotional,
    "--order-journal-path", $OrderJournalPath,
    "--format", $Format
)

if (-not [string]::IsNullOrEmpty($ReadinessPacketPath)) {
    $CliArgs += @("--readiness-packet", $ReadinessPacketPath)
}

if ($NoSubmit.IsPresent) {
    $CliArgs += @("--no-submit")
}

if ($OperatorPaused.IsPresent) {
    $CliArgs += @("--operator-paused")
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
