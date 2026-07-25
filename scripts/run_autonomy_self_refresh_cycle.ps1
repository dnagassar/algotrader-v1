<#
.SYNOPSIS
Runs the V5.42 offline autonomy self-refresh cycle.

.DESCRIPTION
Runs one observe->decide->act->re-observe cycle over the local autonomy lanes: it
builds the cross-lane supervisor report, plans the next actions, runs the gated
offline executor over the plan, then rebuilds the supervisor report and reports
whether the system converged. It is dry-run by default; pass -Apply to actually
execute the eligible allowlisted offline refresh actions. It is credential-free,
network-free, broker-free: the only side effects are the executor's frozen-
allowlist offline commands, run behind a credential/profile preflight. It refuses
to run if a paper/live profile or any Alpaca credential/network-test variable is
loaded. No wall clock is read; -AsOf is the only time source.
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
    [switch]$AllowEmptyLab,
    [string]$RunLog,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

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
    "-m", "algotrader.cli", "autonomy-self-refresh-cycle",
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
if ($AllowEmptyLab.IsPresent) {
    $Arguments += "--allow-empty-lab"
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
