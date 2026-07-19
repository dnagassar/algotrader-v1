[CmdletBinding()]
param(
    [string]$ReceiptPath = "runs\crypto_supervised_readiness_trial\latest\observation_receipt.json",
    [string]$OutputRoot = "runs\crypto_supervised_readiness_trial\latest"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    python -m algotrader.cli crypto-readiness-consume --receipt-path $ReceiptPath --output-root $OutputRoot
}
finally {
    Pop-Location
}
