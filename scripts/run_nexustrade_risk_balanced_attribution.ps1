<#
.SYNOPSIS
Runs the preregistered offline V5.68 risk-balanced attribution diagnostic.

.DESCRIPTION
Validates the committed V5.68 protocol, frozen V5.64/V5.67 dependencies and
artifacts, and canonical V5.63 data before producing attribution-only output.
The command is credential-free, network-free, broker-free, no-submit, and
creates no candidate or route.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_68_nexustrade_risk_balanced_attribution",
    [string]$DataPath = "runs\operator_input\multi_etf_adjusted_daily_canonical.csv",
    [string]$DataManifestPath = "runs\v5_63_nexustrade_canonical_data\canonical_data_manifest.json",
    [string]$PreregistrationPath = "docs\design\v5_68_nexustrade_risk_balanced_attribution.md",
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
        "nexustrade_risk_balanced_attribution_status=blocked_unsafe_environment"
    )
    exit 2
}

Push-Location -LiteralPath $RepoRoot
try {
    $PythonPathParts = @($RepoSrc)
    if (-not [string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $PythonPathParts += $OriginalPythonPath
    }
    [System.Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        ($PythonPathParts -join [System.IO.Path]::PathSeparator),
        "Process"
    )
    & python -m algotrader.research.nexustrade_risk_balanced_attribution `
        --output-root $OutputRoot `
        --data-path $DataPath `
        --data-manifest-path $DataManifestPath `
        --preregistration-path $PreregistrationPath `
        --format $Format
    exit $LASTEXITCODE
}
finally {
    [System.Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        $OriginalPythonPath,
        "Process"
    )
    Pop-Location
}
