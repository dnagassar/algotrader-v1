<#
.SYNOPSIS
Runs the canonical daily paper-lab operating cycle and prints the compact receipt.

.DESCRIPTION
Runs the existing SPY SMA daily paper-lab implementation in operational-only
mode and then prints the compact daily status receipt from latest_run.json when
an artifact is available.  The default command does not read a broker, mutate
broker state, submit paper orders, load credentials, refresh data, or contact the network.  The optional AutoRefreshAdjustedData switch defaults to a local
dry-run refresh plan; live market-data refresh requires both the live mode and
the explicit LiveMarketDataFetchAuthorized switch.

.PARAMETER OutputRoot
Root directory under which the daily paper-lab operating artifacts are written.

.PARAMETER BrokerSnapshotLog
Local read-only paper broker snapshot reconciliation JSONL to consume. The
wrapper does not make a broker call.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [string]$BrokerSnapshotLog,
    [string]$BarsCsv = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$RunDate,
    [string]$Symbol = "SPY",
    [int]$SmaFastWindow = 50,
    [int]$SmaSlowWindow = 200,
    [ValidateSet("broker_state_not_observed", "offline_fixture", "alpaca_paper_read_only")]
    [string]$BrokerStateMode = "broker_state_not_observed",
    [switch]$AutoRefreshAdjustedData,
    [ValidateSet("dry_run", "live_market_data_fetch")]
    [string]$DataRefreshMode = "dry_run",
    [switch]$LiveMarketDataFetchAuthorized,
    [string]$DataRefreshExpectedLatestBarDate,
    [string]$DataRefreshOutputCsv = ".data\operator_inputs\spy_tiingo_adjusted_refresh_latest.csv",
    [string]$DataRefreshRunLog = "runs\paper_lab\m446_adjusted_spy_bars_refresh_manifest.jsonl",
    [string]$DataRefreshRawResponsePath = "runs\paper_lab\tiingo_spy_adjusted_raw_latest.json",
    [string]$DataRefreshStartDate = "auto",
    [string]$DataRefreshDotenvPath = ".env"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DailyScript = Join-Path $PSScriptRoot "run_daily_paper_lab.ps1"
$ReceiptScript = Join-Path $PSScriptRoot "show_daily_paper_lab_status.ps1"
$RefreshScript = Join-Path $PSScriptRoot "refresh_spy_adjusted_data.ps1"

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

function Get-PropertyText {
    param(
        [object]$Object,
        [string]$Name
    )
    if ($null -eq $Object) {
        return ""
    }
    $Property = $Object.PSObject.Properties[$Name]
    if ($null -eq $Property -or $null -eq $Property.Value) {
        return ""
    }
    return [string]$Property.Value
}

function Get-NestedPropertyText {
    param(
        [object]$Object,
        [string]$Section,
        [string]$Name
    )
    $Nested = Get-PropertyText -Object $Object -Name $Section
    if ([string]::IsNullOrEmpty($Nested)) {
        return ""
    }
    return Get-PropertyText -Object $Object.PSObject.Properties[$Section].Value -Name $Name
}

function Get-RefreshExpectedLatestBarDate {
    param([object]$LatestRun)
    if (-not [string]::IsNullOrEmpty($DataRefreshExpectedLatestBarDate)) {
        return $DataRefreshExpectedLatestBarDate
    }

    $Candidates = @(
        (Get-PropertyText -Object $LatestRun -Name "expected_latest_bar_date"),
        (Get-NestedPropertyText -Object $LatestRun -Section "daily_decision_summary" -Name "expected_latest_bar_date"),
        (Get-PropertyText -Object $LatestRun -Name "latest_completed_session_date"),
        (Get-NestedPropertyText -Object $LatestRun -Section "daily_decision_summary" -Name "latest_completed_session_date")
    )
    foreach ($Candidate in $Candidates) {
        if (-not [string]::IsNullOrEmpty($Candidate)) {
            return $Candidate
        }
    }
    return ""
}

function Test-AdjustedDataRefreshRequired {
    param([object]$LatestRun)
    $Freshness = Get-PropertyText -Object $LatestRun -Name "data_freshness_status"
    if ([string]::IsNullOrEmpty($Freshness)) {
        $Freshness = Get-NestedPropertyText -Object $LatestRun -Section "daily_decision_summary" -Name "data_freshness_status"
    }

    $NextSafeAction = Get-PropertyText -Object $LatestRun -Name "next_safe_action"
    if ([string]::IsNullOrEmpty($NextSafeAction)) {
        $NextSafeAction = Get-NestedPropertyText -Object $LatestRun -Section "daily_autopilot_controller" -Name "next_safe_action"
    }

    return (
        $Freshness -eq "stale_data_preview_only" -or
        $NextSafeAction -eq "refresh_or_intake_adjusted_spy_data"
    )
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
    "-BrokerStateMode", $BrokerStateMode,
    "-OperationalOnly",
    "-Format", "json"
)

if (-not [string]::IsNullOrEmpty($BrokerSnapshotLog)) {
    $DailyArgs += @("-BrokerSnapshotLog", $BrokerSnapshotLog)
}

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
$AutoRefreshExitCode = 0
if ($AutoRefreshAdjustedData) {
    if (-not (Test-Path -LiteralPath $LatestRunPath)) {
        Write-Host "auto_refresh_adjusted_data_status=latest_run_missing"
        $AutoRefreshExitCode = 2
    }
    else {
        try {
            $LatestRunForRefresh = Get-Content -LiteralPath $LatestRunPath -Raw | ConvertFrom-Json
            if (Test-AdjustedDataRefreshRequired -LatestRun $LatestRunForRefresh) {
                $RefreshExpectedLatestBarDate = Get-RefreshExpectedLatestBarDate -LatestRun $LatestRunForRefresh
                if ([string]::IsNullOrEmpty($RefreshExpectedLatestBarDate) -and $DataRefreshMode -eq "dry_run") {
                    Write-Host "auto_refresh_adjusted_data_status=expected_latest_bar_date_required"
                    $AutoRefreshExitCode = 2
                }
                elseif ($DataRefreshMode -eq "live_market_data_fetch" -and -not $LiveMarketDataFetchAuthorized) {
                    Write-Host "auto_refresh_adjusted_data_status=live_market_data_fetch_not_authorized"
                    Write-Host "auto_refresh_adjusted_data_next_safe_action=request_explicit_live_market_data_fetch_authorization"
                    $AutoRefreshExitCode = 2
                }
                else {
                    $RefreshArgs = @(
                        "-NoProfile",
                        "-ExecutionPolicy", "Bypass",
                        "-File", $RefreshScript,
                        "-Provider", "tiingo",
                        "-OutputCsv", $DataRefreshOutputCsv,
                        "-CanonicalCsv", $BarsCsv,
                        "-RunLog", $DataRefreshRunLog,
                        "-Mode", $DataRefreshMode,
                        "-StartDate", $DataRefreshStartDate,
                        "-DotenvPath", $DataRefreshDotenvPath
                    )
                    if (-not [string]::IsNullOrEmpty($RefreshExpectedLatestBarDate)) {
                        $RefreshArgs += @("-ExpectedLatestBarDate", $RefreshExpectedLatestBarDate)
                    }
                    if ($DataRefreshMode -eq "live_market_data_fetch") {
                        $RefreshArgs += @(
                            "-RawResponsePath", $DataRefreshRawResponsePath,
                            "-Format", "json"
                        )
                    }
                    if ($LiveMarketDataFetchAuthorized) {
                        $RefreshArgs += @("-LiveMarketDataFetchAuthorized")
                    }
                    Push-Location -LiteralPath $RepoRoot
                    try {
                        & $PowerShellExe @RefreshArgs
                        $RefreshExitCode = $LASTEXITCODE
                    }
                    finally {
                        Pop-Location
                    }
                    if ($null -eq $RefreshExitCode) {
                        $RefreshExitCode = 0
                    }
                    if ($DataRefreshMode -eq "dry_run") {
                        Write-Host "auto_refresh_adjusted_data_status=live_market_data_fetch_not_authorized"
                        Write-Host "auto_refresh_adjusted_data_next_safe_action=request_explicit_live_market_data_fetch_authorization"
                        $AutoRefreshExitCode = 2
                        if ($RefreshExitCode -ne 0) {
                            $AutoRefreshExitCode = $RefreshExitCode
                        }
                    }
                    elseif ($RefreshExitCode -ne 0) {
                        Write-Host "auto_refresh_adjusted_data_status=live_market_data_fetch_failed"
                        $AutoRefreshExitCode = $RefreshExitCode
                    }
                    else {
                        Write-Host "auto_refresh_adjusted_data_status=accepted_and_daily_cycle_rerun"
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
                        $AutoRefreshExitCode = $DailyExitCode
                    }
                }
            }
            else {
                Write-Host "auto_refresh_adjusted_data_status=no_refresh_required"
            }
        }
        catch {
            Write-Host "auto_refresh_adjusted_data_status=latest_run_unreadable"
            $AutoRefreshExitCode = 2
        }
    }
}

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
    if ($DailyExitCode -eq 0 -and $AutoRefreshExitCode -ne 0) {
        exit $AutoRefreshExitCode
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

if ($DailyExitCode -eq 0 -and $AutoRefreshExitCode -ne 0) {
    exit $AutoRefreshExitCode
}

exit $DailyExitCode
