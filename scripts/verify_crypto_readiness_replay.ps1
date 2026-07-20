[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_supervised_readiness_trial\latest",
    [int]$CycleCount = 24
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Push-Location -LiteralPath $RepoRoot
try {
    $env:PYTHONPATH = "src"
    python -m algotrader.cli crypto-readiness-verify --output-root $OutputRoot --cycle-count $CycleCount
}
finally {
    Pop-Location
}
