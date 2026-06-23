<#
.SYNOPSIS
Runs the canonical daily paper-lab operating cycle and prints the compact receipt.

.DESCRIPTION
Runs the existing SPY SMA daily paper-lab implementation in operational-only
mode against a supplied local read-only broker snapshot log, then prints the
compact daily status receipt from latest_run.json when an artifact is available.
The command does not read a broker, mutate broker state, submit paper orders,
load credentials, refresh data, or contact the network.

.PARAMETER OutputRoot
Root directory under which the daily paper-lab operating artifacts are written.

.PARAMETER BrokerSnapshotLog
Local read-only paper broker snapshot reconciliation JSONL to consume. The
wrapper sets BrokerStateMode to alpaca_paper_read_only and does not make a
broker call.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [Parameter(Mandatory = $true)]
    [string]$BrokerSnapshotLog,
    [string]$BarsCsv = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$RunDate,
    [string]$Symbol = "SPY",
    [int]$SmaFastWindow = 50,
    [int]$SmaSlowWindow = 200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DailyScript = Join-Path $PSScriptRoot "run_daily_paper_lab.ps1"
$ReceiptScript = Join-Path $PSScriptRoot "show_daily_paper_lab_status.ps1"

$AbsoluteOutputRoot = $OutputRoot
if (-not [System.IO.Path]::IsPathRooted($OutputRoot)) {
    $AbsoluteOutputRoot = Join-Path $RepoRoot $OutputRoot
}

function Get-CurrentPowerShellPath {
    $CurrentProcess = [System.Diagnostics.Process]::GetCurrentProcess()
    if ($null -ne $CurrentProcess.MainModule -and -not [string]::IsNullOrEmpty($CurrentProcess.MainModule.FileName)) {
        return $CurrentProcess.MainModule.FileName
    }
    $PwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($null -ne $PwshCommand) {
        return $PwshCommand.Source
    }
    $WindowsPowerShellCommand = Get-Command powershell -ErrorAction SilentlyContinue
    if ($null -ne $WindowsPowerShellCommand) {
        return $WindowsPowerShellCommand.Source
    }
    throw "Unable to locate a PowerShell executable for the daily paper-lab cycle."
}

$PowerShellExe = Get-CurrentPowerShellPath

$DailyArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $DailyScript,
    "-OutputRoot", $OutputRoot,
    "-BarsCsv", $BarsCsv,
    "-Symbol", $Symbol,
    "-SmaFastWindow", $SmaFastWindow,
    "-SmaSlowWindow", $SmaSlowWindow,
    "-BrokerStateMode", "alpaca_paper_read_only",
    "-BrokerSnapshotLog", $BrokerSnapshotLog,
    "-OperationalOnly",
    "-Format", "json"
)

if (-not [string]::IsNullOrEmpty($AsOfDate)) {
    $DailyArgs += @("-AsOfDate", $AsOfDate)
}

if (-not [string]::IsNullOrEmpty($RunDate)) {
    $DailyArgs += @("-RunDate", $RunDate)
}

Push-Location -LiteralPath $RepoRoot
try {
    $DailyOutput = & $PowerShellExe @DailyArgs 2>&1
    $DailyExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $DailyExitCode) {
    $DailyExitCode = 0
}

$LatestRunPath = Join-Path $AbsoluteOutputRoot "latest_run.json"
if (Test-Path -LiteralPath $LatestRunPath) {
    $ReceiptArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $ReceiptScript,
        "-OutputRoot", $AbsoluteOutputRoot
    )
    Push-Location -LiteralPath $RepoRoot
    try {
        & $PowerShellExe @ReceiptArgs
        $ReceiptExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if ($null -eq $ReceiptExitCode) {
        $ReceiptExitCode = 0
    }
    if ($DailyExitCode -eq 0 -and $ReceiptExitCode -ne 0) {
        exit $ReceiptExitCode
    }
    exit $DailyExitCode
}

if ($DailyOutput) {
    foreach ($Line in $DailyOutput) {
        if ($Line -is [System.Management.Automation.ErrorRecord]) {
            [Console]::Error.WriteLine($Line.ToString())
        }
        else {
            Write-Host $Line
        }
    }
}

exit $DailyExitCode
