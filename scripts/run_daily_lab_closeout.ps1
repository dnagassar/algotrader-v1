<#
.SYNOPSIS
Runs the safe offline daily lab closeout sequence.

.DESCRIPTION
Composes the existing offline daily lab acceptance launcher, acceptance
history index, operator summary, and closeout packet commands.

.PARAMETER StartDate
Start date of the historical range (YYYY-MM-DD).

.PARAMETER EndDate
End date of the historical range (YYYY-MM-DD).

.PARAMETER BarsCsv
Path to the canonical daily bars CSV file.

.PARAMETER ReconciliationStatePath
Path to the offline reconciliation state JSONL file.

.PARAMETER DailySoakDir
Directory under which daily soak artifacts are stored.

.PARAMETER PythonExecutable
Python executable used for algotrader CLI commands.
#>

[CmdletBinding()]
param(
    [string]$StartDate = "2025-06-01",
    [string]$EndDate = "2025-06-10",
    [string]$BarsCsv = "tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
    [string]$ReconciliationStatePath = "tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
    [string]$DailySoakDir = "runs/daily_soak",
    [string]$PythonExecutable = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "==> $Title"
}

function Invoke-CheckedExternalCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Description,

        [Parameter(Mandatory = $true)]
        [string]$Command,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Write-Section $Description
    & $Command @Arguments
    $ExitCode = $LASTEXITCODE

    if ($null -eq $ExitCode) {
        $ExitCode = 0
    }

    if ($ExitCode -ne 0) {
        [Console]::Error.WriteLine("Error: $Description failed with exit code $ExitCode")
        exit $ExitCode
    }
}

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$AcceptanceScript = Join-Path $RepoRoot "scripts/run_daily_lab_acceptance.ps1"

$HistoryIndexPath = Join-Path $DailySoakDir "v3j_daily_soak_acceptance_history_index.jsonl"
$OperatorSummaryPath = Join-Path $DailySoakDir "v3k_daily_soak_operator_summary.jsonl"
$OperatorSummaryTextPath = Join-Path $DailySoakDir "v3k_daily_soak_operator_summary.md"
$CloseoutPacketPath = Join-Path $DailySoakDir "v3l_daily_soak_closeout_packet.jsonl"
$CloseoutPacketTextPath = Join-Path $DailySoakDir "v3l_daily_soak_closeout_packet.md"

Push-Location -LiteralPath $RepoRoot
try {
    Invoke-CheckedExternalCommand `
        -Description "Running V3I daily lab acceptance launcher" `
        -Command "powershell" `
        -Arguments @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $AcceptanceScript,
            "-StartDate",
            $StartDate,
            "-EndDate",
            $EndDate,
            "-BarsCsv",
            $BarsCsv,
            "-ReconciliationStatePath",
            $ReconciliationStatePath,
            "-OutputRoot",
            $DailySoakDir
        )

    Invoke-CheckedExternalCommand `
        -Description "Building V3J daily soak acceptance history index" `
        -Command $PythonExecutable `
        -Arguments @(
            "-m",
            "algotrader.cli",
            "etf-sma-daily-soak-acceptance-history-index",
            "--daily-soak-dir",
            $DailySoakDir,
            "--out",
            $HistoryIndexPath
        )

    Invoke-CheckedExternalCommand `
        -Description "Building V3K daily soak operator summary" `
        -Command $PythonExecutable `
        -Arguments @(
            "-m",
            "algotrader.cli",
            "etf-sma-daily-soak-operator-summary",
            "--history-index",
            $HistoryIndexPath,
            "--out",
            $OperatorSummaryPath,
            "--text-out",
            $OperatorSummaryTextPath
        )

    Invoke-CheckedExternalCommand `
        -Description "Building V3L daily soak closeout packet" `
        -Command $PythonExecutable `
        -Arguments @(
            "-m",
            "algotrader.cli",
            "etf-sma-daily-soak-closeout-packet",
            "--history-index",
            $HistoryIndexPath,
            "--operator-summary",
            $OperatorSummaryPath,
            "--operator-summary-md",
            $OperatorSummaryTextPath,
            "--out",
            $CloseoutPacketPath,
            "--text-out",
            $CloseoutPacketTextPath
        )
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "=================================================================="
Write-Host "DAILY LAB CLOSEOUT ARTIFACTS"
Write-Host "=================================================================="
Write-Host "Daily Soak Directory: $DailySoakDir"
Write-Host "V3J History Index:    $HistoryIndexPath"
Write-Host "V3K Summary JSONL:    $OperatorSummaryPath"
Write-Host "V3K Summary Markdown: $OperatorSummaryTextPath"
Write-Host "V3L Packet JSONL:     $CloseoutPacketPath"
Write-Host "V3L Packet Markdown:  $CloseoutPacketTextPath"
Write-Host "=================================================================="

exit 0
