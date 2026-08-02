<#
.SYNOPSIS
Runs the frozen V5.72 primary-source alpha tournament offline.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_72_primary_source_alpha_tournament\evaluation",
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$UnsafeNames = @(
    "ALPACA_API_KEY", "ALPACA_API_SECRET", "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY", "TIINGO_API_KEY", "TIINGO_API_TOKEN",
    "NEXUSTRADE_ACCESS_TOKEN", "NEXUSTRADE_REFRESH_TOKEN"
)
$Unsafe = $false
if ([System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process") -eq "paper") {
    $Unsafe = $true
}
foreach ($Name in $UnsafeNames) {
    if (-not [string]::IsNullOrWhiteSpace(
        [System.Environment]::GetEnvironmentVariable($Name, "Process")
    )) {
        $Unsafe = $true
    }
}
if ($Unsafe) {
    [Console]::Error.WriteLine("primary_source_alpha_tournament_status=blocked_unsafe_environment")
    exit 2
}

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
Push-Location -LiteralPath $RepoRoot
try {
    $Parts = @($RepoSrc)
    if (-not [string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $Parts += $OriginalPythonPath
    }
    [System.Environment]::SetEnvironmentVariable(
        "PYTHONPATH", ($Parts -join [System.IO.Path]::PathSeparator), "Process"
    )
    & python -m algotrader.research.primary_source_alpha_tournament `
        --output-root $OutputRoot --format $Format
    exit $LASTEXITCODE
}
finally {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $OriginalPythonPath, "Process")
    Pop-Location
}
