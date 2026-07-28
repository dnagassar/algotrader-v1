param(
    [ValidateSet("next_session_open", "market_close")]
    [string]$ExecutionWindow = "next_session_open",
    [string]$MarketDataCredentialReference = "wincred:algotrader/v5.35/alpaca-market-data/production"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ((Get-Location).Path -ne $repoRoot) {
    throw "Run this wrapper from the repository root."
}

$asOfUtc = [DateTimeOffset]::UtcNow.ToString("o")
& python -m algotrader.execution.spy_decision_time_shadow `
    --mode capture `
    --as-of $asOfUtc `
    --apply `
    --execution-window $ExecutionWindow `
    --credential-reference $MarketDataCredentialReference
exit $LASTEXITCODE
