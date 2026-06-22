<#
.SYNOPSIS
Prints a compact read-only receipt from daily paper-lab artifacts.

.DESCRIPTION
Reads the canonical latest_run.json artifact under OutputRoot and prints stable
key=value lines for daily-cycle classification. The command does not refresh
data, read a broker, mutate broker state, submit paper orders, or load
credentials.

.PARAMETER OutputRoot
Daily paper-lab output root containing latest_run.json. Required.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$CliArgs = @(
    "-m", "algotrader.execution.daily_paper_lab_status_receipt",
    "--output-root", $OutputRoot
)

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
