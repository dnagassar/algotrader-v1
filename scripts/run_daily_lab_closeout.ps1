<#
.SYNOPSIS
Runs the safe offline daily lab closeout sequence.

.DESCRIPTION
Composes the existing offline daily lab acceptance launcher, acceptance
history index, operator summary, and closeout packet commands, producing
a deterministic run receipt.

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

.PARAMETER ReceiptOut
Path to write the receipt JSONL record. Defaults to <DailySoakDir>/v3n_daily_lab_closeout_run_receipt.jsonl.

.PARAMETER ReceiptTextOut
Path to write the receipt markdown report. Defaults to <DailySoakDir>/v3n_daily_lab_closeout_run_receipt.md.
#>

[CmdletBinding()]
param(
    [string]$StartDate = "2025-06-01",
    [string]$EndDate = "2025-06-10",
    [string]$BarsCsv = "tests/fixtures/etf_sma_cycle_matrix/spy_daily_bars_200_bullish.csv",
    [string]$ReconciliationStatePath = "tests/fixtures/etf_sma_cycle_matrix/reconciliation_state_flat.jsonl",
    [string]$DailySoakDir = "runs/daily_soak",
    [string]$PythonExecutable = "python",
    [string]$ReceiptOut = "",
    [string]$ReceiptTextOut = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "==> $Title"
}

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$AcceptanceScript = Join-Path $RepoRoot "scripts/run_daily_lab_acceptance.ps1"

$HistoryIndexPath = Join-Path $DailySoakDir "v3j_daily_soak_acceptance_history_index.jsonl"
$OperatorSummaryPath = Join-Path $DailySoakDir "v3k_daily_soak_operator_summary.jsonl"
$OperatorSummaryTextPath = Join-Path $DailySoakDir "v3k_daily_soak_operator_summary.md"
$CloseoutPacketPath = Join-Path $DailySoakDir "v3l_daily_soak_closeout_packet.jsonl"
$CloseoutPacketTextPath = Join-Path $DailySoakDir "v3l_daily_soak_closeout_packet.md"

if ([string]::IsNullOrEmpty($ReceiptOut)) {
    $ReceiptOut = Join-Path $DailySoakDir "v3n_daily_lab_closeout_run_receipt.jsonl"
}
if ([string]::IsNullOrEmpty($ReceiptTextOut)) {
    $ReceiptTextOut = Join-Path $DailySoakDir "v3n_daily_lab_closeout_run_receipt.md"
}

$Steps = @()
$AnyFailed = $false
$FailedExitCode = 0
$ReceiptStatus = "completed"

# Step 1: V3I acceptance launcher
$Step1Name = "V3I daily lab acceptance launcher"
$Step1Cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_daily_lab_acceptance.ps1 -StartDate $StartDate -EndDate $EndDate -BarsCsv $BarsCsv -ReconciliationStatePath $ReconciliationStatePath -OutputRoot $DailySoakDir"

Write-Section $Step1Name
$Step1ExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    & "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $AcceptanceScript, "-StartDate", $StartDate, "-EndDate", $EndDate, "-BarsCsv", $BarsCsv, "-ReconciliationStatePath", $ReconciliationStatePath, "-OutputRoot", $DailySoakDir) 1> $null
    $Step1ExitCode = $LASTEXITCODE
    if ($null -eq $Step1ExitCode) { $Step1ExitCode = 0 }
} catch {
    $Step1ExitCode = 1
} finally {
    Pop-Location
}

if ($Step1ExitCode -ne 0) {
    $AnyFailed = $true
    $FailedExitCode = $Step1ExitCode
    $ReceiptStatus = "failed_acceptance_launcher"
    $Steps += @{
        name = $Step1Name
        command = $Step1Cmd
        status = "failed"
        exit_code = $Step1ExitCode
    }
    [Console]::Error.WriteLine("Error: $Step1Name failed with exit code $Step1ExitCode")
} else {
    $Steps += @{
        name = $Step1Name
        command = $Step1Cmd
        status = "completed"
        exit_code = 0
    }
}

# Step 2: V3J history index
$Step2Name = "Building V3J daily soak acceptance history index"
$Step2Cmd = "$PythonExecutable -m algotrader.cli etf-sma-daily-soak-acceptance-history-index --daily-soak-dir $DailySoakDir --out $HistoryIndexPath"

if ($AnyFailed) {
    $Steps += @{
        name = $Step2Name
        command = $Step2Cmd
        status = "skipped"
        exit_code = $null
    }
} else {
    Write-Section $Step2Name
    $Step2ExitCode = 0
    Push-Location -LiteralPath $RepoRoot
    try {
        & $PythonExecutable @("-m", "algotrader.cli", "etf-sma-daily-soak-acceptance-history-index", "--daily-soak-dir", $DailySoakDir, "--out", $HistoryIndexPath) 1> $null
        $Step2ExitCode = $LASTEXITCODE
        if ($null -eq $Step2ExitCode) { $Step2ExitCode = 0 }
    } catch {
        $Step2ExitCode = 1
    } finally {
        Pop-Location
    }

    if ($Step2ExitCode -ne 0) {
        $AnyFailed = $true
        $FailedExitCode = $Step2ExitCode
        $ReceiptStatus = "failed_history_index"
        $Steps += @{
            name = $Step2Name
            command = $Step2Cmd
            status = "failed"
            exit_code = $Step2ExitCode
        }
        [Console]::Error.WriteLine("Error: $Step2Name failed with exit code $Step2ExitCode")
    } else {
        $Steps += @{
            name = $Step2Name
            command = $Step2Cmd
            status = "completed"
            exit_code = 0
        }
    }
}

# Step 3: V3K operator summary
$Step3Name = "Building V3K daily soak operator summary"
$Step3Cmd = "$PythonExecutable -m algotrader.cli etf-sma-daily-soak-operator-summary --history-index $HistoryIndexPath --out $OperatorSummaryPath --text-out $OperatorSummaryTextPath"

if ($AnyFailed) {
    $Steps += @{
        name = $Step3Name
        command = $Step3Cmd
        status = "skipped"
        exit_code = $null
    }
} else {
    Write-Section $Step3Name
    $Step3ExitCode = 0
    Push-Location -LiteralPath $RepoRoot
    try {
        & $PythonExecutable @("-m", "algotrader.cli", "etf-sma-daily-soak-operator-summary", "--history-index", $HistoryIndexPath, "--out", $OperatorSummaryPath, "--text-out", $OperatorSummaryTextPath) 1> $null
        $Step3ExitCode = $LASTEXITCODE
        if ($null -eq $Step3ExitCode) { $Step3ExitCode = 0 }
    } catch {
        $Step3ExitCode = 1
    } finally {
        Pop-Location
    }

    if ($Step3ExitCode -ne 0) {
        $AnyFailed = $true
        $FailedExitCode = $Step3ExitCode
        $ReceiptStatus = "failed_operator_summary"
        $Steps += @{
            name = $Step3Name
            command = $Step3Cmd
            status = "failed"
            exit_code = $Step3ExitCode
        }
        [Console]::Error.WriteLine("Error: $Step3Name failed with exit code $Step3ExitCode")
    } else {
        $Steps += @{
            name = $Step3Name
            command = $Step3Cmd
            status = "completed"
            exit_code = 0
        }
    }
}

# Step 4: V3L closeout packet
$Step4Name = "Building V3L daily soak closeout packet"
$Step4Cmd = "$PythonExecutable -m algotrader.cli etf-sma-daily-soak-closeout-packet --history-index $HistoryIndexPath --operator-summary $OperatorSummaryPath --operator-summary-md $OperatorSummaryTextPath --out $CloseoutPacketPath --text-out $CloseoutPacketTextPath"

if ($AnyFailed) {
    $Steps += @{
        name = $Step4Name
        command = $Step4Cmd
        status = "skipped"
        exit_code = $null
    }
} else {
    Write-Section $Step4Name
    $Step4ExitCode = 0
    Push-Location -LiteralPath $RepoRoot
    try {
        & $PythonExecutable @("-m", "algotrader.cli", "etf-sma-daily-soak-closeout-packet", "--history-index", $HistoryIndexPath, "--operator-summary", $OperatorSummaryPath, "--operator-summary-md", $OperatorSummaryTextPath, "--out", $CloseoutPacketPath, "--text-out", $CloseoutPacketTextPath) 1> $null
        $Step4ExitCode = $LASTEXITCODE
        if ($null -eq $Step4ExitCode) { $Step4ExitCode = 0 }
    } catch {
        $Step4ExitCode = 1
    } finally {
        Pop-Location
    }

    if ($Step4ExitCode -ne 0) {
        $AnyFailed = $true
        $FailedExitCode = $Step4ExitCode
        $ReceiptStatus = "failed_closeout_packet"
        $Steps += @{
            name = $Step4Name
            command = $Step4Cmd
            status = "failed"
            exit_code = $Step4ExitCode
        }
        [Console]::Error.WriteLine("Error: $Step4Name failed with exit code $Step4ExitCode")
    } else {
        $Steps += @{
            name = $Step4Name
            command = $Step4Cmd
            status = "completed"
            exit_code = 0
        }
    }
}

# Now build the receipt!
Write-Section "Building V3N daily lab closeout run receipt"
$StepRecordsJson = ConvertTo-Json -InputObject $Steps -Compress

$StepsTempPath = Join-Path $DailySoakDir "v3n_steps_temp.json"
$StepRecordsJson | Out-File -FilePath $StepsTempPath -Encoding utf8 -Force

Push-Location -LiteralPath $RepoRoot
try {
    $ReceiptArgs = @(
        "-m", "algotrader.cli", "etf-sma-daily-soak-closeout-receipt",
        "--start-date", $StartDate,
        "--end-date", $EndDate,
        "--bars-csv", $BarsCsv,
        "--reconciliation-state-path", $ReconciliationStatePath,
        "--daily-soak-dir", $DailySoakDir,
        "--status", $ReceiptStatus,
        "--steps-json", $StepsTempPath,
        "--receipt-out", $ReceiptOut,
        "--receipt-text-out", $ReceiptTextOut
    )

    & $PythonExecutable @ReceiptArgs 1> $null
    $ReceiptExitCode = $LASTEXITCODE
    if ($null -eq $ReceiptExitCode) { $ReceiptExitCode = 0 }

    if ($ReceiptExitCode -ne 0) {
        [Console]::Error.WriteLine("Error: Receipt generation failed with exit code $ReceiptExitCode")
        $AnyFailed = $true
        if ($FailedExitCode -eq 0) {
            $FailedExitCode = $ReceiptExitCode
        }
    }
} finally {
    if (Test-Path $StepsTempPath) {
        Remove-Item $StepsTempPath -Force
    }
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
Write-Host "V3N Receipt JSONL:    $ReceiptOut"
Write-Host "V3N Receipt Markdown: $ReceiptTextOut"
Write-Host "=================================================================="

if ($AnyFailed) {
    if ($FailedExitCode -ne 0) {
        exit $FailedExitCode
    }
    exit 1
}

exit 0
