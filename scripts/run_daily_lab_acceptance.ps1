<#
.SYNOPSIS
Runs the safe daily lab acceptance sequence.

.DESCRIPTION
Runs credential prechecks, verify_offline.ps1, daily soak golden check,
and prints an operator acceptance summary.

.PARAMETER StartDate
Start date of the historical range (YYYY-MM-DD).

.PARAMETER EndDate
End date of the historical range (YYYY-MM-DD).

.PARAMETER BarsCsv
Path to the canonical daily bars CSV file.

.PARAMETER ReconciliationStatePath
Path to the offline reconciliation state JSONL file.

.PARAMETER OutputRoot
Directory under which daily runs and soak rollups are stored.

.PARAMETER FullVerify
Pass -Full flag to scripts/verify_offline.ps1.
#>

[CmdletBinding()]
param(
    [string]$StartDate = "2025-06-01",
    [string]$EndDate = "2025-06-10",
    [string]$BarsCsv = "tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
    [string]$ReconciliationStatePath = "tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
    [string]$OutputRoot = "runs/daily_soak",
    [switch]$FullVerify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "==> $Title"
}

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

# 1. Credential/profile precheck with booleans only.
Write-Section "Credential/profile precheck"
$CredentialVariableNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)

function Test-ProcessEnvironmentVariableLoaded {
    param([string]$Name)
    $ProcessEnvironment = [System.Environment]::GetEnvironmentVariables("Process")
    return $ProcessEnvironment.Contains($Name)
}

$AppProfileIsPaper = $env:APP_PROFILE -eq "paper"

Write-Host "APP_PROFILE_is_paper: $AppProfileIsPaper"

$LoadedCredentialVariables = @()
foreach ($Name in $CredentialVariableNames) {
    $Loaded = Test-ProcessEnvironmentVariableLoaded -Name $Name
    Write-Host "${Name}_loaded: $Loaded"
    if ($Loaded) {
        $LoadedCredentialVariables += $Name
    }
}

if ($AppProfileIsPaper) {
    [Console]::Error.WriteLine("Error: APP_PROFILE is paper. Cannot run daily lab acceptance in paper mode.")
    exit 2
}

if ($LoadedCredentialVariables.Count -gt 0) {
    [Console]::Error.WriteLine("Error: broker credential environment variable(s) are loaded. Values were not printed.")
    exit 2
}

# 2. scripts/verify_offline.ps1.
Write-Section "Running offline verification"
$VerifyScript = Join-Path $RepoRoot "scripts/verify_offline.ps1"
$VerifyArgs = @()
if ($FullVerify) {
    $VerifyArgs += "-Full"
}

Push-Location -LiteralPath $RepoRoot
try {
    & $VerifyScript @VerifyArgs
    $VerifyExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $VerifyExitCode) {
    $VerifyExitCode = 0
}

if ($VerifyExitCode -ne 0) {
    [Console]::Error.WriteLine("Error: scripts/verify_offline.ps1 failed with exit code $VerifyExitCode")
    exit $VerifyExitCode
}

# 3. python -m algotrader.cli etf-sma-daily-soak-golden-check.
Write-Section "Running daily soak golden check"
$GoldenCheckArgs = @(
    "etf-sma-daily-soak-golden-check",
    "--start-date", $StartDate,
    "--end-date", $EndDate,
    "--bars-csv", $BarsCsv,
    "--reconciliation-state-path", $ReconciliationStatePath,
    "--output-root", $OutputRoot
)

$GoldenExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    python -m algotrader.cli @GoldenCheckArgs
    $GoldenExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $GoldenExitCode) {
    $GoldenExitCode = 0
}

# 4. Parse or verify the golden-check result.
$JsonlPath = Join-Path $RepoRoot "$OutputRoot/soak_golden_acceptance.jsonl"
if (-not (Test-Path $JsonlPath)) {
    [Console]::Error.WriteLine("Error: Golden check output file not found at $JsonlPath. Exit code was: $GoldenExitCode")
    exit 1
}

$Payload = Get-Content -Raw -Path $JsonlPath | ConvertFrom-Json

# 6. Confirm no generated runs artifacts are staged or tracked.
$TrackedArtifacts = @()
$StagedArtifacts = @()

Push-Location -LiteralPath $RepoRoot
try {
    $TrackedOutput = git ls-files $OutputRoot
    if ($TrackedOutput) {
        $TrackedArtifacts = $TrackedOutput -split "`r?`n" | Where-Object { $_.Trim() -ne "" }
    }
    $StagedOutput = git diff --cached --name-only -- $OutputRoot
    if ($StagedOutput) {
        $StagedArtifacts = $StagedOutput -split "`r?`n" | Where-Object { $_.Trim() -ne "" }
    }
}
finally {
    Pop-Location
}

$GitCheckStatus = "PASS"
if ($TrackedArtifacts.Count -gt 0 -or $StagedArtifacts.Count -gt 0) {
    $GitCheckStatus = "FAIL"
}

# 5. Print a concise operator acceptance summary.
Write-Host ""
Write-Host "=================================================================="
Write-Host "DAILY LAB ACCEPTANCE SUMMARY"
Write-Host "=================================================================="
Write-Host "Verifier Status:              PASS"
Write-Host "Golden Acceptance Status:     $($Payload.golden_acceptance_status.ToUpper())"
Write-Host "Release Gate Status:          $($Payload.release_gate_status.ToUpper())"
Write-Host "Pre-Gate Validation Findings:  $($Payload.artifact_validation_finding_count)"
Write-Host "Post-Gate Validation Findings: $($Payload.post_release_artifact_validation_finding_count)"
Write-Host "Output Root:                  $($Payload.output_root)"
Write-Host ""
Write-Host "Safety Authorization Booleans:"
Write-Host "- live_trading_authorized:      $($Payload.live_trading_authorized)"
Write-Host "- paper_submit_authorized:     $($Payload.paper_submit_authorized)"
Write-Host "- broker_mutation_authorized:   $($Payload.broker_mutation_authorized)"
Write-Host "- paper_broker_reads_authorized: $($Payload.paper_broker_reads_authorized)"
Write-Host "- network_access_authorized:   $($Payload.network_access_authorized)"
Write-Host "- credential_loading_authorized: $($Payload.credential_loading_authorized)"
Write-Host ""
Write-Host "Git Artifact Verification:"
if ($GitCheckStatus -eq "PASS") {
    Write-Host "- Tracked/Staged check:       PASS (No generated runs artifacts are tracked or staged)"
} else {
    Write-Host "- Tracked/Staged check:       FAIL (Generated runs artifacts are tracked or staged!)"
    if ($TrackedArtifacts.Count -gt 0) {
        Write-Host "  Tracked artifacts:"
        foreach ($file in $TrackedArtifacts) {
            Write-Host "    - $file"
        }
    }
    if ($StagedArtifacts.Count -gt 0) {
        Write-Host "  Staged artifacts:"
        foreach ($file in $StagedArtifacts) {
            Write-Host "    - $file"
        }
    }
}
Write-Host ""
Write-Host "Key Output Artifact Paths:"
foreach ($path in $Payload.artifact_paths) {
    Write-Host "- $path"
}
Write-Host "=================================================================="

# Exit with appropriate code if any step failed
if ($GoldenExitCode -ne 0) {
    exit $GoldenExitCode
}

if ($GitCheckStatus -eq "FAIL") {
    [Console]::Error.WriteLine("Error: Daily lab acceptance failed because generated artifacts are tracked or staged in Git.")
    exit 1
}

exit 0
