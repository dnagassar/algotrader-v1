$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ((Get-Location).Path -ne $repoRoot) {
    throw "Run this wrapper from the repository root."
}

$asOfUtc = [DateTimeOffset]::UtcNow.ToString("o")
& python -m algotrader.execution.autonomy_spy_refresh_cycle `
    --as-of $asOfUtc `
    --apply `
    --format json
exit $LASTEXITCODE
