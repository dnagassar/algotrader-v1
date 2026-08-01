<#
.SYNOPSIS
Runs the preregistered offline V5.69 relative-momentum confirmation replay.

.DESCRIPTION
Validates the committed V5.69 protocol, frozen V5.64 dependencies and
artifacts, and canonical V5.63 data hashes before replay. The command is
credential-free, network-free, broker-free, no-submit, and not an authentic
replay of the March 2025 NexusTrade historical run.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_69_nexustrade_monthly_relative_momentum_confirmation",
    [string]$DataPath = "runs\operator_input\multi_etf_adjusted_daily_canonical.csv",
    [string]$DataManifestPath = "runs\v5_63_nexustrade_canonical_data\canonical_data_manifest.json",
    [string]$PreregistrationPath = "docs\design\v5_69_nexustrade_monthly_relative_momentum_confirmation.md",
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable(
    "PYTHONPATH",
    "Process"
)
$SensitiveAliases = @(
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "ALPACA_ENDPOINT",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "APCA_API_BASE_URL",
    "NEXUSTRADE_API_KEY",
    "NEXUSTRADE_ACCESS_TOKEN",
    "TIINGO_API_KEY",
    "TIINGO_API_TOKEN"
)
$AppProfile = [System.Environment]::GetEnvironmentVariable(
    "APP_PROFILE",
    "Process"
)
$SensitiveLoaded = $false
foreach ($AliasName in $SensitiveAliases) {
    $AliasValue = [System.Environment]::GetEnvironmentVariable(
        $AliasName,
        "Process"
    )
    if (-not [string]::IsNullOrWhiteSpace($AliasValue)) {
        $SensitiveLoaded = $true
    }
}

Write-Output (
    "preflight_APP_PROFILE_is_paper=" +
    ($AppProfile -eq "paper").ToString().ToLowerInvariant()
)
Write-Output (
    "preflight_APP_PROFILE_is_live=" +
    ($AppProfile -eq "live").ToString().ToLowerInvariant()
)
Write-Output (
    "preflight_sensitive_variables_loaded=" +
    $SensitiveLoaded.ToString().ToLowerInvariant()
)
Write-Output "Credential values are never printed."

if ($AppProfile -in @("paper", "live") -or $SensitiveLoaded) {
    [Console]::Error.WriteLine(
        "nexustrade_monthly_relative_momentum_status=blocked_unsafe_environment"
    )
    exit 2
}

try {
    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $RepoSrc
    }
    else {
        $RepoSrc + [System.IO.Path]::PathSeparator + $OriginalPythonPath
    }
    & python -m algotrader.research.nexustrade_monthly_relative_momentum_confirmation `
        --output-root $OutputRoot `
        --data-path $DataPath `
        --data-manifest-path $DataManifestPath `
        --preregistration-path $PreregistrationPath `
        --format $Format
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    [System.Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        $OriginalPythonPath,
        "Process"
    )
}
