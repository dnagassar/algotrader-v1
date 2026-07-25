<#
.SYNOPSIS
Runs the V5.37 offline cross-lane autonomy supervisor.

.DESCRIPTION
Reads only local per-lane evidence artifacts and prints one whole-system
readiness record. The command is credential-free, network-free, broker-free, and
read-only. It refuses to run if a paper/live profile or any Alpaca credential or
network-test variable is loaded so secrets never reach this reporting surface.
No wall clock is read; -AsOf is the only time source, keeping output
deterministic. A lane set with no evidence at all fails closed; pass
-AllowEmptyLab to declare an intentionally empty lab.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunId,
    [Parameter(Mandatory = $true)]
    [string]$AsOf,
    [string]$LanesRoot = "runs",
    [string[]]$Lane = @(),
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
    "-m", "algotrader.cli", "autonomy-supervisor-status",
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
