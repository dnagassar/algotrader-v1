<#
.SYNOPSIS
Runs the daily SPY SMA paper-lab loop.

.DESCRIPTION
Validates safety prechecks, resolves repository root and output root, and
runs the offline-only ETF/SMA daily paper-lab command.

.PARAMETER OutputRoot
Root directory under which the daily paper-lab operating packet is written. Required.

.PARAMETER BarsCsv
Path to the canonical daily bars CSV file. Defaults to runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv.

.PARAMETER AsOfDate
Explicit market-data/signal as-of date (YYYY-MM-DD). If omitted, derived from input bars.

.PARAMETER RunDate
Optional deterministic operating run date (YYYY-MM-DD) used for freshness and
controller routing. Distinct from AsOfDate.

.PARAMETER Symbol
Symbol to evaluate. Defaults to SPY.

.PARAMETER SmaFastWindow
SMA fast window size. Defaults to 50.

.PARAMETER SmaSlowWindow
SMA slow window size. Defaults to 200.

.PARAMETER BrokerStateMode
Broker-state lane mode. Defaults to broker_state_not_observed. alpaca_paper_read_only
consumes a local read-only broker snapshot log when BrokerSnapshotLog is supplied;
the daily lab command itself performs no broker read.

.PARAMETER BrokerSnapshotLog
Optional local read-only paper broker snapshot reconciliation JSONL to consume
when BrokerStateMode is alpaca_paper_read_only.

.PARAMETER BrokerSnapshotRoots
Optional local read-only paper broker snapshot files or directories to scan
when BrokerStateMode is alpaca_paper_read_only. Accepts normal PowerShell
arrays or semicolon-separated entries. Discovery is local-only and performs no
broker read.

.PARAMETER PostDrillGuardPacketPath
Optional local v2.00 post-drill guard packet JSON to display in Mission Control.
This is read-only and grants no paper submit or cancel authority.

.PARAMETER OperationalOnly
Produce only the active daily operating artifacts and suppress secondary
candidate-research and agent work-order materialization. This is the default
unless FullResearchPacket is supplied.

.PARAMETER FullResearchPacket
Explicitly produce the full research packet, including secondary candidate
research and agent work-order artifacts.

.PARAMETER Format
Output format (text or json). Defaults to text.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [string]$BarsCsv = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$AsOfDate,
    [string]$RunDate,
    [string]$Symbol = "SPY",
    [int]$SmaFastWindow = 50,
    [int]$SmaSlowWindow = 200,
    [ValidateSet("broker_state_not_observed", "offline_fixture", "alpaca_paper_read_only")]
    [string]$BrokerStateMode = "broker_state_not_observed",
    [string]$BrokerSnapshotLog,
    [string[]]$BrokerSnapshotRoots = @(),
    [string]$PostDrillGuardPacketPath = "runs/paper_lab/v200_post_drill_operating_guard/post_drill_guard_packet.json",
    [switch]$OperationalOnly,
    [switch]$FullResearchPacket,
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

# Safety Precheck
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

$LoadedCredentialVariables = @()
foreach ($Name in $CredentialVariableNames) {
    if (Test-ProcessEnvironmentVariableLoaded -Name $Name) {
        $LoadedCredentialVariables += $Name
    }
}

$AppProfileIsPaper = [System.Environment]::GetEnvironmentVariable("APP_PROFILE", "Process") -eq "paper"
if ($AppProfileIsPaper) {
    [Console]::Error.WriteLine("Error: APP_PROFILE is paper. Daily paper-lab assistant must run offline only without paper profile.")
    exit 2
}

if ($LoadedCredentialVariables.Count -gt 0) {
    [Console]::Error.WriteLine("Error: broker credential environment variable(s) are loaded: $($LoadedCredentialVariables -join ', '). Daily paper-lab assistant must run offline only without credentials.")
    exit 2
}

if ($OperationalOnly -and $FullResearchPacket) {
    [Console]::Error.WriteLine("Error: OperationalOnly and FullResearchPacket are mutually exclusive.")
    exit 2
}

$UseOperationalOnly = $OperationalOnly -or (-not $FullResearchPacket)

# Resolve OutputRoot parent
$AbsoluteOutputRoot = $OutputRoot
if (-not [System.IO.Path]::IsPathRooted($OutputRoot)) {
    $AbsoluteOutputRoot = Join-Path $RepoRoot $OutputRoot
}

# Ensure OutputRoot exists
if (-not (Test-Path -LiteralPath $AbsoluteOutputRoot)) {
    New-Item -ItemType Directory -Force -Path $AbsoluteOutputRoot | Out-Null
}

$CliArgs = @(
    "-m", "algotrader.cli",
    "etf-sma-daily-paper-lab",
    "--output-root", $AbsoluteOutputRoot,
    "--bars-csv", $BarsCsv,
    "--symbol", $Symbol,
    "--sma-fast-window", $SmaFastWindow,
    "--sma-slow-window", $SmaSlowWindow,
    "--broker-state-mode", $BrokerStateMode,
    "--format", $Format
)

if (-not [string]::IsNullOrEmpty($AsOfDate)) {
    $CliArgs += @("--as-of-date", $AsOfDate)
}

if (-not [string]::IsNullOrEmpty($RunDate)) {
    $CliArgs += @("--run-date", $RunDate)
}

if (-not [string]::IsNullOrEmpty($BrokerSnapshotLog)) {
    $CliArgs += @("--broker-snapshot-log", $BrokerSnapshotLog)
}

foreach ($BrokerSnapshotRootValue in $BrokerSnapshotRoots) {
    foreach ($BrokerSnapshotRoot in ($BrokerSnapshotRootValue -split ";")) {
        if (-not [string]::IsNullOrWhiteSpace($BrokerSnapshotRoot)) {
            $CliArgs += @("--broker-snapshot-root", $BrokerSnapshotRoot)
        }
    }
}

if (-not [string]::IsNullOrEmpty($PostDrillGuardPacketPath)) {
    $CliArgs += @("--post-drill-guard-packet-path", $PostDrillGuardPacketPath)
}

if ($UseOperationalOnly) {
    $CliArgs += @("--operational-only")
}

Push-Location -LiteralPath $RepoRoot
try {
    & python @CliArgs
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}

if ($ExitCode -eq 0 -and $Format -eq "text") {
    $IndexPath = Join-Path $AbsoluteOutputRoot "index.html"
    $OperatorReviewPath = Join-Path $AbsoluteOutputRoot "operator_review.md"
    $LatestRunPath = Join-Path $AbsoluteOutputRoot "latest_run.json"
    $ValidationPath = Join-Path $AbsoluteOutputRoot "mission_control_validation.json"
    $DataRefreshBridgePath = Join-Path $AbsoluteOutputRoot "data_refresh_bridge.json"
    $DataRefreshDryRunPath = Join-Path $AbsoluteOutputRoot "data_refresh_dry_run.json"
    $DataRefreshChecklistPath = Join-Path $AbsoluteOutputRoot "data_refresh_operator_checklist.md"
    $BrokerStateModeText = $BrokerStateMode
    $DataRefreshDryRunStatusText = "unknown"
    $DataRefreshInputCsvPresentText = "unknown"
    $DataRefreshIngestPerformedText = "false"
    $ExactNextOperatorActionText = "unknown"
    $ForwardSignalEvidenceLedgerStatusText = "unknown"
    $BrokerSnapshotHandoffStatusText = "broker_state_not_observed"
    $BrokerSnapshotCurrentTruthClaimedText = "false"
    $BrokerSnapshotPacketFreshnessStatusText = "not_observed"
    $BrokerSnapshotObservationTimestampText = ""
    $BrokerSnapshotSourcePacketPathText = ""
    $BrokerSnapshotSelectionStatusText = "not_requested"
    $BrokerSnapshotSelectedPathText = ""
    $BrokerSnapshotDisplayedCandidatePathText = ""
    $BrokerSnapshotCandidateCountText = "0"
    $PostDrillGuardStatusText = "post_drill_guard_not_available"
    $PostDrillGuardClassificationText = "mission_control_post_drill_guard_missing"
    $PostDrillGuardAuthorizationConsumedText = "false"

    if (Test-Path -LiteralPath $LatestRunPath) {
        try {
            $LatestRun = Get-Content -LiteralPath $LatestRunPath -Raw | ConvertFrom-Json
            if ($LatestRun.broker_state_mode) {
                $BrokerStateModeText = [string]$LatestRun.broker_state_mode
            }
            if ($LatestRun.data_refresh_dry_run_status) {
                $DataRefreshDryRunStatusText = [string]$LatestRun.data_refresh_dry_run_status
            }
            if ($null -ne $LatestRun.data_refresh_input_csv_present) {
                $DataRefreshInputCsvPresentText = ([string]$LatestRun.data_refresh_input_csv_present).ToLowerInvariant()
            }
            if ($null -ne $LatestRun.data_refresh_ingest_performed) {
                $DataRefreshIngestPerformedText = ([string]$LatestRun.data_refresh_ingest_performed).ToLowerInvariant()
            }
            if ($LatestRun.exact_next_operator_action) {
                $ExactNextOperatorActionText = [string]$LatestRun.exact_next_operator_action
            }
            if ($LatestRun.forward_signal_evidence_ledger_status) {
                $ForwardSignalEvidenceLedgerStatusText = [string]$LatestRun.forward_signal_evidence_ledger_status
            }
            if ($LatestRun.broker_snapshot_handoff_status) {
                $BrokerSnapshotHandoffStatusText = [string]$LatestRun.broker_snapshot_handoff_status
            }
            if ($null -ne $LatestRun.broker_snapshot_current_broker_truth_claimed) {
                $BrokerSnapshotCurrentTruthClaimedText = ([string]$LatestRun.broker_snapshot_current_broker_truth_claimed).ToLowerInvariant()
            }
            if ($LatestRun.broker_snapshot_packet_freshness_status) {
                $BrokerSnapshotPacketFreshnessStatusText = [string]$LatestRun.broker_snapshot_packet_freshness_status
            }
            if ($LatestRun.broker_snapshot_observation_timestamp) {
                $BrokerSnapshotObservationTimestampText = [string]$LatestRun.broker_snapshot_observation_timestamp
            }
            if ($LatestRun.broker_snapshot_source_packet_path) {
                $BrokerSnapshotSourcePacketPathText = [string]$LatestRun.broker_snapshot_source_packet_path
            }
            if ($LatestRun.broker_snapshot_selection_status) {
                $BrokerSnapshotSelectionStatusText = [string]$LatestRun.broker_snapshot_selection_status
            }
            if ($LatestRun.broker_snapshot_selected_path) {
                $BrokerSnapshotSelectedPathText = [string]$LatestRun.broker_snapshot_selected_path
            }
            if ($LatestRun.broker_snapshot_displayed_candidate_path) {
                $BrokerSnapshotDisplayedCandidatePathText = [string]$LatestRun.broker_snapshot_displayed_candidate_path
            }
            if ($null -ne $LatestRun.broker_snapshot_candidate_count) {
                $BrokerSnapshotCandidateCountText = [string]$LatestRun.broker_snapshot_candidate_count
            }
            if ($LatestRun.post_drill_guard_status) {
                $PostDrillGuardStatusText = [string]$LatestRun.post_drill_guard_status
            }
            if ($LatestRun.post_drill_guard_classification) {
                $PostDrillGuardClassificationText = [string]$LatestRun.post_drill_guard_classification
            }
            if ($null -ne $LatestRun.post_drill_guard_authorization_consumed) {
                $PostDrillGuardAuthorizationConsumedText = ([string]$LatestRun.post_drill_guard_authorization_consumed).ToLowerInvariant()
            }
        }
        catch {
            $BrokerStateModeText = $BrokerStateMode
        }
    }

    Write-Host ""
    Write-Host "Mission Control generated."
    Write-Host "Open first: $IndexPath"
    Write-Host "Operator review: $OperatorReviewPath"
    Write-Host "Latest run summary: $LatestRunPath"
    Write-Host "Validation: $ValidationPath"
    Write-Host "Data refresh bridge: $DataRefreshBridgePath"
    Write-Host "Data refresh dry run: $DataRefreshDryRunPath"
    Write-Host "Data refresh dry-run status: $DataRefreshDryRunStatusText"
    Write-Host "Data refresh CSV present: $DataRefreshInputCsvPresentText"
    Write-Host "Data refresh ingest performed: $DataRefreshIngestPerformedText"
    Write-Host "Data refresh checklist: $DataRefreshChecklistPath"
    Write-Host "Paper submit authorized: false"
    Write-Host "Live authorized: false"
    Write-Host "Broker read performed: false"
    Write-Host "Broker mutation performed: false"
    Write-Host "Broker-state mode: $BrokerStateModeText"
    Write-Host "Broker snapshot handoff status: $BrokerSnapshotHandoffStatusText"
    Write-Host "Broker snapshot current broker truth claimed: $BrokerSnapshotCurrentTruthClaimedText"
    Write-Host "Broker snapshot packet freshness: $BrokerSnapshotPacketFreshnessStatusText"
    Write-Host "Broker snapshot observation timestamp: $BrokerSnapshotObservationTimestampText"
    Write-Host "Broker snapshot source packet: $BrokerSnapshotSourcePacketPathText"
    Write-Host "Broker snapshot selection status: $BrokerSnapshotSelectionStatusText"
    Write-Host "Broker snapshot selected path: $BrokerSnapshotSelectedPathText"
    Write-Host "Broker snapshot displayed candidate path: $BrokerSnapshotDisplayedCandidatePathText"
    Write-Host "Broker snapshot candidate count: $BrokerSnapshotCandidateCountText"
    Write-Host "Broker snapshot paper submit authorized: false"
    Write-Host "Broker snapshot paper cancel authorized: false"
    Write-Host "Forward signal evidence ledger status: $ForwardSignalEvidenceLedgerStatusText"
    Write-Host "Post-drill guard status: $PostDrillGuardStatusText"
    Write-Host "Post-drill guard classification: $PostDrillGuardClassificationText"
    Write-Host "Post-drill guard authorization consumed: $PostDrillGuardAuthorizationConsumedText"
    Write-Host "Post-drill guard paper submit authorized: false"
    Write-Host "Post-drill guard paper cancel authorized: false"
    Write-Host "Post-drill guard next paper action requires new authorization: true"
    Write-Host "Exact next operator action: $ExactNextOperatorActionText"
}

exit $ExitCode
