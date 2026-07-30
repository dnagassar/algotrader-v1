<#
.SYNOPSIS
Runs the preregistered offline V5.64 independent replication.

.DESCRIPTION
Validates the committed preregistration and canonical V5.63 data hashes, then
runs the standalone and genuine SPY-regime-filtered composite with no network,
credential, broker, paper, or live access. This is not an authentic replay of
the March 2025 NexusTrade historical run and cannot authorize submission.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_64_nexustrade_monthly_independent_replication",
    [string]$DataPath = "runs\operator_input\multi_etf_adjusted_daily_canonical.csv",
    [string]$DataManifestPath = "runs\v5_63_nexustrade_canonical_data\canonical_data_manifest.json",
    [string]$PreregistrationPath = "docs\design\v5_64_nexustrade_monthly_independent_replication.md",
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
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "NEXUSTRADE_API_KEY",
    "TIINGO_API_KEY"
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
        "nexustrade_monthly_independent_replication_status=blocked_unsafe_environment"
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
    & python -m algotrader.research.nexustrade_monthly_independent_replication `
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
