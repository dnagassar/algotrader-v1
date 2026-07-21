<#
.SYNOPSIS
Runs the bounded Alpaca paper account baseline cleanup wrapper.

.DESCRIPTION
Invokes the exact-order-bound paper account cleanup module using only the
credentials already present in the invoking process environment. This wrapper
never loads plaintext credential files, never falls back to another
checkout's environment, and never duplicates secrets into alternate variable
names.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_34_paper_cleanup\latest",
    [switch]$PaperCleanupAuthorized,
    [switch]$AllowNetwork
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$Arguments = @(
    "-m",
    "algotrader.execution.crypto_paper_account_cleanup",
    "--output-root",
    $OutputRoot
)

if ($PaperCleanupAuthorized.IsPresent) {
    $Arguments += @("--paper-cleanup-authorized")
}
if ($AllowNetwork.IsPresent) {
    $Arguments += @("--allow-network")
}

$ExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    python @Arguments
    $ExitCode = $LASTEXITCODE
}
catch {
    $ExitCode = 1
    throw
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
