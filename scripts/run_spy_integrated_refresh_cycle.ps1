$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ((Get-Location).Path -ne $repoRoot) {
    throw "Run this wrapper from the repository root."
}

$ambientProfile = [System.Environment]::GetEnvironmentVariable(
    "APP_PROFILE",
    "Process"
)
if (
    -not [string]::IsNullOrWhiteSpace($ambientProfile) -and
    $ambientProfile -ne "paper"
) {
    throw "Refusing non-paper APP_PROFILE."
}
$ambientPaperUrl = [System.Environment]::GetEnvironmentVariable(
    "ALPACA_PAPER_BASE_URL",
    "Process"
)
if (
    -not [string]::IsNullOrWhiteSpace($ambientPaperUrl) -and
    $ambientPaperUrl.TrimEnd("/") -ne "https://paper-api.alpaca.markets"
) {
    throw "Refusing noncanonical paper endpoint."
}
$brokerCredentialNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
$processEnvironment = [System.Environment]::GetEnvironmentVariables("Process")
$loadedBrokerCredentialNames = @(
    $brokerCredentialNames |
        Where-Object { $processEnvironment.Contains($_) }
)
if ($loadedBrokerCredentialNames.Count -ne 0) {
    throw "Refusing broker credential aliases in the read-only refresh process."
}

$env:APP_PROFILE = "paper"
$env:ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"
$asOfUtc = [DateTimeOffset]::UtcNow.ToString("o")
& python -m algotrader.execution.autonomy_spy_refresh_cycle `
    --as-of $asOfUtc `
    --apply `
    --format json
exit $LASTEXITCODE
