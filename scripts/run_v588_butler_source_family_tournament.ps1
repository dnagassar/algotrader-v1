[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\v5_88_butler_exhibit3_4_source_family\evaluation"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
$UnsafeNames = @(
    "APP_PROFILE", "ALPACA_API_KEY", "ALPACA_API_SECRET", "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY", "TIINGO_API_KEY", "TIINGO_API_TOKEN",
    "NEXUSTRADE_ACCESS_TOKEN", "NEXUSTRADE_REFRESH_TOKEN"
)
foreach ($Name in $UnsafeNames) {
    if (-not [string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($Name, "Process"))) {
        [Console]::Error.WriteLine("butler_source_family_tournament_status=blocked_unsafe_environment")
        exit 2
    }
}
Push-Location -LiteralPath $RepoRoot
try {
    $Parts = @($RepoSrc)
    if (-not [string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $Parts += $OriginalPythonPath
    }
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", ($Parts -join [System.IO.Path]::PathSeparator), "Process")
    & python -m algotrader.research.butler_source_family_tournament --output-root $OutputRoot
    exit $LASTEXITCODE
}
finally {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $OriginalPythonPath, "Process")
    Pop-Location
}
