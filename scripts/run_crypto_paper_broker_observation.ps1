[CmdletBinding()]
param(
    [string]$ReceiptRoot = "runs\crypto_supervised_readiness_trial\latest",
    [switch]$BrokerObservedReadiness,
    [switch]$AllowAlpacaPaperRead
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Arguments = @("crypto-paper-broker-observation", "--receipt-root", $ReceiptRoot)
if ($BrokerObservedReadiness.IsPresent) { $Arguments += "--broker-observed-readiness" }
if ($AllowAlpacaPaperRead.IsPresent) { $Arguments += "--allow-alpaca-paper-read" }

Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    python -m algotrader.cli @Arguments
}
finally {
    Pop-Location
}
