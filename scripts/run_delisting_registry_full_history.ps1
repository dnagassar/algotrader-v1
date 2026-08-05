<#
.SYNOPSIS
Runs the full-history EDGAR delisting registry.

.DESCRIPTION
Stage A enumerates every Form 25 / 25-NSE filing from EDGAR's quarterly
form.idx archive. Stage B resolves a trading symbol per delisting episode from
cover-page inline XBRL. Both stages are GET-only against two allowlisted SEC
hosts and use no credentials: EDGAR is public, and the pipeline has no code
path that can read an environment variable, dotenv, or credential store.

SEC's fair-access policy requires a User-Agent carrying contact information, so
one is mandatory. Both stages are resumable; rerunning skips recorded work.

No broker, account, order, paper, or live-trading access occurs.
#>

[CmdletBinding()]
param(
    [ValidateSet("a", "b", "summary", "export")]
    [string]$Stage = "a",
    [ValidateSet("dry_run", "live_fetch")]
    [string]$Mode = "dry_run",
    [Parameter(Mandatory = $true)]
    [string]$UserAgent,
    [string]$OutputRoot = "runs\v6_03_full_history_delisting_registry",
    [int]$StartYear = 1993,
    [int]$StartQuarter = 1,
    [int]$EndYear = 0,
    [int]$EndQuarter = 0,
    [string]$ResolveFrom = "2019-01-01",
    [int]$MaxResolutions = 0,
    [double]$RequestIntervalSeconds = 0.1667,
    [switch]$LiveFetchAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")

$AppProfile = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process")
if ($AppProfile -eq "live") {
    [Console]::Error.WriteLine("Error: APP_PROFILE is live. This pipeline is research-only.")
    exit 2
}
if ($Mode -eq "live_fetch" -and -not $LiveFetchAuthorized) {
    [Console]::Error.WriteLine("Error: live fetch requires explicit authorization.")
    exit 2
}
if ($Mode -eq "dry_run" -and $LiveFetchAuthorized) {
    [Console]::Error.WriteLine("Error: authorization flag requires live fetch mode.")
    exit 2
}

Push-Location -LiteralPath $RepoRoot
try {
    $PythonParts = @($RepoSrc)
    if (-not [string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $PythonParts += $OriginalPythonPath
    }
    [System.Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        ($PythonParts -join [System.IO.Path]::PathSeparator),
        "Process"
    )
    $Args = @(
        "-m", "algotrader.execution.edgar_delisting_pipeline",
        "--stage", $Stage,
        "--user-agent", $UserAgent,
        "--output-root", $OutputRoot
    )
    if ($Stage -notin @("summary", "export")) {
        $Args += @(
            "--mode", $Mode,
            "--start-year", $StartYear,
            "--start-quarter", $StartQuarter,
            "--resolve-from", $ResolveFrom,
            "--max-resolutions", $MaxResolutions,
            "--request-interval-seconds", $RequestIntervalSeconds
        )
        if ($EndYear -gt 0 -and $EndQuarter -gt 0) {
            $Args += @("--end-year", $EndYear, "--end-quarter", $EndQuarter)
        }
        if ($LiveFetchAuthorized) {
            $Args += "--live-fetch-authorized"
        }
    }
    & python @Args
    if ($LASTEXITCODE -ne 0) {
        [Console]::Error.WriteLine("Error: delisting registry stage $Stage failed.")
        exit $LASTEXITCODE
    }
    Write-Output "delisting_registry_stage_${Stage}_status=completed"
    exit 0
}
finally {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $OriginalPythonPath, "Process")
    Pop-Location
}
