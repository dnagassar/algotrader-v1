<#
.SYNOPSIS
Runs the V5.38 offline autonomy next-action planner.

.DESCRIPTION
Builds the V5.37 cross-lane supervisor report from local per-lane evidence and
classifies each lane's recommended next action into a concrete offline plan: the
exact offline command to run (when one exists), the operator-supplied inputs it
still needs, and — when no offline path exists — the operator gate that blocks
autonomous progress. It is credential-free, network-free, broker-free, and
strictly read-only: it plans commands and never executes them. It refuses to run
if a paper/live profile or any Alpaca credential or network-test variable is
loaded so secrets never reach this reporting surface. No wall clock is read;
-AsOf is the only time source, keeping output deterministic.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunId,
    [Parameter(Mandatory = $true)]
    [string]$AsOf,
    [string]$LanesRoot = "runs",
    [string[]]$Lane = @(),
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
    "-m", "algotrader.cli", "autonomy-next-plan",
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
