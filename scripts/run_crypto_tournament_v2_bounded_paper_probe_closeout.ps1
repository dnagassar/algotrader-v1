<#
.SYNOPSIS
Completes the target-scoped post-exit paper evidence chain.

.DESCRIPTION
This dormant shell starts only after an exact filled-exit lifecycle exists. It
runs one target-scoped read-only flat observation in an isolated paper child,
scrubs every paper credential/profile/account/endpoint/network variable from
its own process, then runs capability production, sealed review, and pinned
replay offline. It never invokes lifecycle planning or mutation and accepts no
authorization, account identifier, credential, caller timestamp, or
publication fingerprint.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("BTCUSD", "ETHUSD", "SOLUSD")]
    [string]$TargetSymbol,
    [switch]$IndependentFlatReadAuthorized,
    [switch]$AllowNetwork,
    [string]$ShadowRoot = (
        "runs\crypto_strategy_tournament\v2\forward_shadow\latest"
    ),
    [string]$LifecycleRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_lifecycle"
    ),
    [string]$FlatRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_capabilities"
    ),
    [string]$CapabilityRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_capabilities\latest"
    ),
    [string]$ReviewRoot = (
        "runs\crypto_strategy_tournament\v2\bounded_paper_probe_review\latest"
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (
    Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
).Path
$LifecycleLatest = Join-Path $LifecycleRoot "latest"
$TerminalPath = Join-Path $LifecycleLatest "terminal_evidence.json"
$PlanPath = Join-Path $LifecycleLatest "lifecycle_plan.json"
$LifecycleResultPath = Join-Path $LifecycleLatest "lifecycle_result.json"
$LifecycleManifestPath = Join-Path $LifecycleLatest "manifest.json"
$FlatReceiptPath = Join-Path $FlatRoot "independent_flat_reconciliation.json"
$FlatStatusPath = Join-Path $FlatRoot "latest_status.json"
$FlatManifestPath = Join-Path $FlatRoot "independent_flat_manifest.json"
$SafetyReceiptPath = Join-Path $FlatRoot "safety_certification_receipt.json"
$ReviewLatestManifestPath = Join-Path $ReviewRoot "latest_manifest.json"

function Test-PathUnderRoot {
    param(
        [string]$Path,
        [string]$Root
    )
    try {
        $FullPath = [System.IO.Path]::GetFullPath($Path)
        $FullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
        return (
            $FullPath.Equals(
                $FullRoot,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -or
            $FullPath.StartsWith(
                $FullRoot + [System.IO.Path]::DirectorySeparatorChar,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        )
    }
    catch {
        return $false
    }
}

function Test-ReparsePointFreePath {
    param([string]$Path)
    try {
        $FullPath = [System.IO.Path]::GetFullPath($Path)
        $VolumeRoot = [System.IO.Path]::GetPathRoot($FullPath)
        $RelativePath = $FullPath.Substring($VolumeRoot.Length)
        $CurrentPath = $VolumeRoot
        $Components = $RelativePath.Split(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.StringSplitOptions]::RemoveEmptyEntries
        )
        foreach ($Component in $Components) {
            $CurrentPath = Join-Path $CurrentPath $Component
            if (-not (Test-Path -LiteralPath $CurrentPath)) {
                return $false
            }
            $Info = Get-Item -LiteralPath $CurrentPath -Force
            if (
                [bool](
                    $Info.Attributes -band
                    [System.IO.FileAttributes]::ReparsePoint
                )
            ) {
                return $false
            }
        }
        return $true
    }
    catch {
        return $false
    }
}

$RequiredLifecyclePaths = @(
    $TerminalPath,
    $PlanPath,
    $LifecycleResultPath,
    $LifecycleManifestPath
)
$StopReasons = [System.Collections.Generic.List[string]]::new()
if (-not $IndependentFlatReadAuthorized.IsPresent) {
    $StopReasons.Add("independent_flat_read_switch_required")
}
if (-not $AllowNetwork.IsPresent) {
    $StopReasons.Add("allow_network_switch_required")
}
foreach ($Path in $RequiredLifecyclePaths) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $StopReasons.Add("exact_lifecycle_quartet_required")
        break
    }
}
if ($StopReasons.Count -gt 0) {
    Write-Host "v530_closeout_stop_reasons=$($StopReasons -join ',')"
    exit 2
}

$PowerShellPath = (
    [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
)
$PowerShellName = [System.IO.Path]::GetFileName(
    $PowerShellPath
).ToLowerInvariant()
if (
    -not [System.IO.Path]::IsPathRooted($PowerShellPath) -or
    -not (Test-Path -LiteralPath $PowerShellPath -PathType Leaf) -or
    -not (Test-ReparsePointFreePath $PowerShellPath) -or
    (Test-PathUnderRoot $PowerShellPath $RepoRoot) -or
    $PowerShellName -notin @("pwsh.exe", "powershell.exe")
) {
    throw "The current trusted PowerShell executable is required."
}

function Invoke-CloseoutStage {
    param(
        [string]$Stage,
        [string]$ScriptPath,
        [string[]]$Arguments
    )
    Write-Host "v530_closeout_stage=$Stage"
    & $PowerShellPath -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments
    $Code = $LASTEXITCODE
    if ($null -eq $Code) {
        $Code = 0
    }
    if ($Code -ne 0) {
        Write-Host "v530_closeout_failed_stage=$Stage"
        Write-Host "v530_closeout_child_exit_code=$Code"
        exit $Code
    }
}

$FlatArguments = @(
    "-TargetSymbol",
    $TargetSymbol,
    "-IndependentFlatReadAuthorized",
    "-AllowNetwork",
    "-LifecyclePath",
    $LifecycleResultPath,
    "-OutputRoot",
    $FlatRoot
)
Invoke-CloseoutStage -Stage "independent_flat" -ScriptPath (Join-Path $PSScriptRoot "run_crypto_bounded_probe_independent_flat_operator.ps1") -Arguments $FlatArguments

$ScrubbedVariableNames = @(
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL",
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    "PYTEST_ADDOPTS",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONINSPECT",
    "PYTHONUSERBASE",
    "PYTHONBREAKPOINT",
    "PYTHONPYCACHEPREFIX"
)
foreach ($Name in $ScrubbedVariableNames) {
    [Environment]::SetEnvironmentVariable($Name, $null, "Process")
}
$ScrubFailed = $false
foreach ($Name in $ScrubbedVariableNames) {
    if (
        -not [string]::IsNullOrWhiteSpace(
            [Environment]::GetEnvironmentVariable($Name, "Process")
        )
    ) {
        $ScrubFailed = $true
    }
}
if ($ScrubFailed) {
    throw "Credential and paper-process environment scrubbing failed."
}
Write-Host "v530_closeout_sensitive_environment_scrubbed=true"

$CapabilityTimestamp = [DateTimeOffset]::UtcNow.ToString("o")
$CapabilityArguments = @(
    "-InputFamily",
    "target",
    "-ShadowRoot",
    $ShadowRoot,
    "-CapabilityRoot",
    $CapabilityRoot,
    "-SafetyReceiptPath",
    $SafetyReceiptPath,
    "-TargetTerminalEvidencePath",
    $TerminalPath,
    "-TargetLifecyclePlanPath",
    $PlanPath,
    "-TargetLifecycleReceiptPath",
    $LifecycleResultPath,
    "-TargetLifecycleManifestPath",
    $LifecycleManifestPath,
    "-IndependentFlatReconciliationPath",
    $FlatReceiptPath,
    "-IndependentFlatStatusPath",
    $FlatStatusPath,
    "-IndependentFlatManifestPath",
    $FlatManifestPath,
    "-AsOf",
    $CapabilityTimestamp
)
Invoke-CloseoutStage -Stage "capability_production" -ScriptPath (Join-Path $PSScriptRoot "run_crypto_tournament_v2_capability_pipeline.ps1") -Arguments $CapabilityArguments

$ReviewTimestamp = [DateTimeOffset]::UtcNow.ToString("o")
$ReviewArguments = @(
    "-ShadowRoot",
    $ShadowRoot,
    "-CapabilityRoot",
    $CapabilityRoot,
    "-OutputRoot",
    $ReviewRoot,
    "-AsOf",
    $ReviewTimestamp
)
Invoke-CloseoutStage -Stage "sealed_review" -ScriptPath (Join-Path $PSScriptRoot "run_crypto_tournament_v2_bounded_paper_probe_review.ps1") -Arguments $ReviewArguments

if (-not (Test-Path -LiteralPath $ReviewLatestManifestPath -PathType Leaf)) {
    Write-Host "v530_closeout_failed_stage=review_manifest"
    exit 2
}
$ReviewManifestInfo = Get-Item -LiteralPath $ReviewLatestManifestPath
if (
    [bool](
        $ReviewManifestInfo.Attributes -band
        [System.IO.FileAttributes]::ReparsePoint
    ) -or
    $ReviewManifestInfo.Length -le 0 -or
    $ReviewManifestInfo.Length -gt 65536
) {
    Write-Host "v530_closeout_failed_stage=review_manifest"
    exit 2
}
try {
    $ReviewLatest = Get-Content -LiteralPath $ReviewLatestManifestPath -Raw | ConvertFrom-Json
    $PublicationFingerprint = [string](
        $ReviewLatest.publication_fingerprint
    )
}
catch {
    Write-Host "v530_closeout_failed_stage=review_manifest"
    exit 2
}
if ($PublicationFingerprint -cnotmatch "^[0-9a-f]{64}$") {
    Write-Host "v530_closeout_failed_stage=review_manifest"
    exit 2
}

$ReplayTimestamp = [DateTimeOffset]::UtcNow.ToString("o")
$ReplayArguments = @(
    "-ExpectedPublicationFingerprint",
    $PublicationFingerprint,
    "-ReviewRoot",
    $ReviewRoot,
    "-TrustedCurrentUtc",
    $ReplayTimestamp
)
Invoke-CloseoutStage -Stage "pinned_replay" -ScriptPath (Join-Path $PSScriptRoot "replay_crypto_tournament_v2_bounded_paper_probe_review.ps1") -Arguments $ReplayArguments

$PublicationFingerprint = $null
Write-Host "v530_closeout_complete=true"
Write-Host "credential_values_exposed=false"
Write-Host "broker_mutation_occurred=false"
Write-Host "paper_mutation_occurred=false"
Write-Host "live_endpoint_touched=false"
exit 0

