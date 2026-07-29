<#
.SYNOPSIS
Previews or registers the secure weekday SMA and RSI sleeve paper-cycle tasks.

.DESCRIPTION
Preview is the default and performs no system mutation. -RegisterTask installs
the exact least-privilege task templates. SMA runs at 09:31 and RSI at 09:38
America/New_York with three 15-minute retries. The shared runtime lease
serializes overlap, while Python independently enforces the NYSE session,
finite caps, sleeve ownership, reconciliation, and the one-hour window.
#>

[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$TaskName = "algo-trader-secure-spy-paper-cycle",
    [string]$RsiTaskName = "algo-trader-secure-spy-rsi-paper-cycle",
    [switch]$RegisterTask
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptRepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $ResolvedRepoRoot = $ScriptRepoRoot
}
else {
    $ResolvedRepoRoot = (Resolve-Path -LiteralPath $RepositoryRoot).Path
}

$TemplatePath = Join-Path $ScriptRepoRoot "docs\design\secure_spy_paper_cycle_task.xml"
$RsiTemplatePath = Join-Path $ScriptRepoRoot "docs\design\secure_spy_rsi_paper_cycle_task.xml"
if (-not (Test-Path -LiteralPath $TemplatePath -PathType Leaf)) {
    throw "Task XML template is missing."
}
if (-not (Test-Path -LiteralPath $RsiTemplatePath -PathType Leaf)) {
    throw "RSI task XML template is missing."
}
$EscapedRepoRoot = [System.Security.SecurityElement]::Escape($ResolvedRepoRoot)
$XmlText = (Get-Content -LiteralPath $TemplatePath -Raw).Replace(
    "%REPO_ROOT%",
    $EscapedRepoRoot
)
$RsiXmlText = (Get-Content -LiteralPath $RsiTemplatePath -Raw).Replace(
    "%REPO_ROOT%",
    $EscapedRepoRoot
)

Write-Host "task_name=$TaskName"
Write-Host "rsi_task_name=$RsiTaskName"
Write-Host "task_repository_root=$ResolvedRepoRoot"
Write-Host "task_schedule=weekdays_09:31_America/New_York_plus_three_15_minute_retries"
Write-Host "task_max_orders_per_cycle=1"
Write-Host "task_max_order_notional=25.00"
Write-Host "task_max_portfolio_notional=60.00"
Write-Host "task_max_sleeve_orders_per_session=2"
Write-Host "task_active_strategy_id=spy_sma_50_200_training_wheel"
Write-Host "rsi_task_schedule=weekdays_09:38_America/New_York_plus_three_15_minute_retries"
Write-Host "rsi_task_active_strategy_id=spy_rsi_14_mean_reversion_paper"
Write-Host "task_live_authorized=false"

if (-not $RegisterTask.IsPresent) {
    Write-Host "task_registration=preview_only"
    Write-Host "task_system_mutation_performed=false"
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Xml $XmlText -Force | Out-Null
Register-ScheduledTask -TaskName $RsiTaskName -Xml $RsiXmlText -Force | Out-Null
Write-Host "task_registration=registered"
Write-Host "registered_task_count=2"
Write-Host "task_system_mutation_performed=true"
