<#
.SYNOPSIS
Runs the V5.39 gated offline autonomy executor.

.DESCRIPTION
Executes only the offline-runnable, allowlisted subset of the V5.38 autonomy
plan. It is dry-run by default; pass -Apply to actually run the eligible
allowlisted offline commands. The SPY daily-cycle seed/refresh becomes eligible
only when -ValidatedAt and -DailyBarsCsv are supplied together; its child outputs
remain pinned to the canonical supervised runs paths. The executor and this
wrapper both refuse to run under a loaded paper/live profile or any Alpaca
credential/network-test variable, so secrets never reach the execution surface.
No wall clock is read; -AsOf is the only supervisory time source. It performs no
broker/submit/mutation/live action and writes one deterministic local action
ledger.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunId,
    [Parameter(Mandatory = $true)]
    [string]$AsOf,
    [string]$LanesRoot = "runs",
    [string[]]$Lane = @(),
    [switch]$Apply,
    [string]$ValidatedAt,
    [string]$DailyBarsCsv,
    [string]$RunLog,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$HasValidatedAt = -not [string]::IsNullOrWhiteSpace($ValidatedAt)
$HasDailyBarsCsv = -not [string]::IsNullOrWhiteSpace($DailyBarsCsv)
if ($HasValidatedAt -xor $HasDailyBarsCsv) {
    Write-Error "-ValidatedAt and -DailyBarsCsv must be supplied together."
    exit 2
}

function Test-EnvLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    return -not [string]::IsNullOrWhiteSpace($Value)
}

$Profile = [Environment]::GetEnvironmentVariable("APP_PROFILE")
if ($Profile -eq "paper" -or $Profile -eq "live") {
    Write-Error "Refusing to run: APP_PROFILE is '$Profile'. Use a credential-free shell."
    exit 2
}

foreach ($Name in @(
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS"
    )) {
    if (Test-EnvLoaded -Name $Name) {
        Write-Error "Refusing to run: '$Name' is loaded. Use a credential-free, network-free shell."
        exit 2
    }
}

$Arguments = @(
    "-m", "algotrader.cli", "autonomy-apply-plan",
    "--run-id", $RunId,
    "--as-of", $AsOf,
    "--lanes-root", $LanesRoot,
    "--format", $Format
)
foreach ($Override in $Lane) {
    if (-not [string]::IsNullOrWhiteSpace($Override)) {
        $Arguments += @("--lane", $Override)
    }
}
if ($Apply.IsPresent) {
    $Arguments += "--apply"
}
if ($HasValidatedAt) {
    $Arguments += @("--validated-at", $ValidatedAt)
    $Arguments += @("--daily-bars-csv", $DailyBarsCsv)
}
if (-not [string]::IsNullOrWhiteSpace($RunLog)) {
    $Arguments += @("--run-log", $RunLog)
}

$env:PYTHONPATH = (Join-Path $RepoRoot "src")
Push-Location $RepoRoot
try {
    & python @Arguments
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $ExitCode
