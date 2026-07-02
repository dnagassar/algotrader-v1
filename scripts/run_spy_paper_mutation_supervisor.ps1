<#
.SYNOPSIS
Runs the SPY paper-only mutation supervisor.

.DESCRIPTION
Runs the bounded SPY SMA paper-autopilot operator. The operator runs the daily
SPY paper-lab loop, observes verified Alpaca paper broker state, creates a
broker-aware ExecutionPlan, and performs at most one bounded paper-only submit
when the plan requires action unless -NoSubmit is set. Credential values are
never printed or loaded by this launcher. Credential values are never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\paper_mutation_supervisor\latest",
    [string]$HistoryRoot = "runs\paper_mutation_supervisor\history",
    [string]$BarsCsv = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$RunDate,
    [string]$Symbol = "SPY",
    [int]$SmaFastWindow = 50,
    [int]$SmaSlowWindow = 200,
    [string]$MaxNotional = "25.00",
    [switch]$NoSubmit,
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
$ExpectedAccountLoaded = Test-ProcessEnvironmentVariableLoaded -Name "ALPACA_EXPECTED_PAPER_ACCOUNT_ID"
$PaperBaseUrl = [System.Environment]::GetEnvironmentVariable("ALPACA_PAPER_BASE_URL", "Process")
$LiveEndpointIndicator = $false
if (-not [string]::IsNullOrEmpty($PaperBaseUrl)) {
    $LowerUrl = $PaperBaseUrl.ToLowerInvariant()
    $LiveEndpointIndicator = $LowerUrl.Contains("api.alpaca.markets") -and -not $LowerUrl.Contains("paper")
}
$OperatingMode = "bounded_paper_mutation"
if ($NoSubmit.IsPresent) {
    $OperatingMode = "visibility/no_submit"
}

Write-Host "preflight_APP_PROFILE_is_paper=$($AppProfileIsPaper.ToString().ToLowerInvariant())"
Write-Host "preflight_APP_PROFILE_is_live=$($AppProfileIsLive.ToString().ToLowerInvariant())"
Write-Host "preflight_credential_variables_loaded=$($LoadedCredentialVariables.Count)"
Write-Host "preflight_expected_account_id_loaded=$($ExpectedAccountLoaded.ToString().ToLowerInvariant())"
Write-Host "preflight_live_endpoint_indicator=$($LiveEndpointIndicator.ToString().ToLowerInvariant())"
Write-Host "preflight_no_submit_mode=$($NoSubmit.IsPresent.ToString().ToLowerInvariant())"
Write-Host "preflight_operating_mode=$OperatingMode"
Write-Host "preflight_paper_submit_authorization_scope=bounded_supervisor_run_only"
Write-Host "preflight_live_authorized=false"

$CliArgs = @(
    "-m", "algotrader.cli",
    "paper-autopilot-operator",
    "--output-root", $OutputRoot,
    "--history-root", $HistoryRoot,
    "--bars-csv", $BarsCsv,
    "--symbol", $Symbol,
    "--sma-fast-window", $SmaFastWindow.ToString(),
    "--sma-slow-window", $SmaSlowWindow.ToString(),
    "--max-notional", $MaxNotional,
    "--format", $Format
)

if (-not [string]::IsNullOrEmpty($AsOfDate)) {
    $CliArgs += @("--as-of-date", $AsOfDate)
}

if (-not [string]::IsNullOrEmpty($RunDate)) {
    $CliArgs += @("--run-date", $RunDate)
}

if ($NoSubmit.IsPresent) {
    $CliArgs += @("--no-submit")
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
