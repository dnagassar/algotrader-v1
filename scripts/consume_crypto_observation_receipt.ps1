[CmdletBinding()]
param(
    [string]$ReceiptRoot = "runs\crypto_supervised_readiness_trial\latest",
    [string]$OutputRoot = "runs\crypto_supervised_readiness_trial\latest"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    python -m algotrader.cli crypto-readiness-consume --receipt-root $ReceiptRoot --output-root $OutputRoot
}
finally {
    Pop-Location
}
