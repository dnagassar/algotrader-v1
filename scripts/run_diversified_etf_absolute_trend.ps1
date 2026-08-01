<#
.SYNOPSIS
Runs the frozen V5.71 diversified ETF absolute-trend evaluation offline.

.DESCRIPTION
Rejects paper/live profiles and all sensitive process variables, then runs the
receipt-bound local replay. No credential, network, broker, paper, or live
access is permitted.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_71_diversified_etf_absolute_trend\evaluation",
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
$SensitiveAliases = @(
    "ALPACA_API_KEY", "ALPACA_API_KEY_ID", "ALPACA_API_SECRET",
    "ALPACA_API_SECRET_KEY", "ALPACA_SECRET_KEY", "ALPACA_ENDPOINT",
    "APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "APCA_API_BASE_URL",
    "NEXUSTRADE_API_KEY", "NEXUSTRADE_ACCESS_TOKEN",
    "TIINGO_API_KEY", "TIINGO_API_TOKEN"
)
$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
$SensitiveLoaded = $false
foreach ($AliasName in $SensitiveAliases) {
    if (-not [string]::IsNullOrWhiteSpace(
        [System.Environment]::GetEnvironmentVariable($AliasName, "Process")
    )) {
        $SensitiveLoaded = $true
    }
}
Write-Output ("preflight_APP_PROFILE_is_paper=" + ($AppProfile -eq "paper").ToString().ToLowerInvariant())
Write-Output ("preflight_APP_PROFILE_is_live=" + ($AppProfile -eq "live").ToString().ToLowerInvariant())
Write-Output ("preflight_sensitive_variables_loaded=" + $SensitiveLoaded.ToString().ToLowerInvariant())
Write-Output "Credential values are never printed."
if ($AppProfile -in @("paper", "live") -or $SensitiveLoaded) {
    [Console]::Error.WriteLine("diversified_etf_absolute_trend_status=blocked_unsafe_environment")
    exit 2
}

try {
    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $RepoSrc
    } else {
        $RepoSrc + [System.IO.Path]::PathSeparator + $OriginalPythonPath
    }
    & python -m algotrader.research.diversified_etf_absolute_trend `
        --output-root $OutputRoot --format $Format
    exit $LASTEXITCODE
}
finally {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $OriginalPythonPath, "Process")
}
