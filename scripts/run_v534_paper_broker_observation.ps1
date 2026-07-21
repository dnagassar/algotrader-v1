<#
.SYNOPSIS
Wrapper for running the crypto paper broker observation for V5.34 R2 evidence.

.DESCRIPTION
Delegates to scripts/run_crypto_paper_broker_observation.ps1 using only the
credentials already present in the invoking process environment. This wrapper
never loads plaintext credential files, never falls back to another
checkout's environment, and never duplicates secrets into alternate variable
names.
#>

[CmdletBinding()]
param(
    [string]$ReceiptRoot = "runs/v5_34_r2_observation/latest",
    [switch]$BrokerObservedReadiness,
    [switch]$AllowAlpacaPaperRead
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$Arguments = @(
    (Join-Path $PSScriptRoot "run_crypto_paper_broker_observation.ps1"),
    "-ReceiptRoot", $ReceiptRoot
)
if ($BrokerObservedReadiness.IsPresent) { $Arguments += "-BrokerObservedReadiness" }
if ($AllowAlpacaPaperRead.IsPresent) { $Arguments += "-AllowAlpacaPaperRead" }

Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    powershell -File @Arguments
}
finally {
    Pop-Location
}
