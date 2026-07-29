<#
.SYNOPSIS
Previews or registers the secure weekday SPY paper-cycle task.

.DESCRIPTION
Preview is the default and performs no system mutation. -RegisterTask installs
the exact least-privilege task template. The task runs at 09:31 America/New_York
with three 15-minute retries, while the Python boundary independently enforces
the NYSE session and one-hour execution window.
#>

[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [string]$TaskName = "algo-trader-secure-spy-paper-cycle",
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
if (-not (Test-Path -LiteralPath $TemplatePath -PathType Leaf)) {
    throw "Task XML template is missing."
}
$EscapedRepoRoot = [System.Security.SecurityElement]::Escape($ResolvedRepoRoot)
$XmlText = (Get-Content -LiteralPath $TemplatePath -Raw).Replace(
    "%REPO_ROOT%",
    $EscapedRepoRoot
)

Write-Host "task_name=$TaskName"
Write-Host "task_repository_root=$ResolvedRepoRoot"
Write-Host "task_schedule=weekdays_09:31_America/New_York_plus_three_15_minute_retries"
Write-Host "task_max_orders_per_cycle=1"
Write-Host "task_max_order_notional=25.00"
Write-Host "task_active_strategy_id=spy_sma_50_200_training_wheel"
Write-Host "task_live_authorized=false"

if (-not $RegisterTask.IsPresent) {
    Write-Host "task_registration=preview_only"
    Write-Host "task_system_mutation_performed=false"
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Xml $XmlText -Force | Out-Null
Write-Host "task_registration=registered"
Write-Host "task_system_mutation_performed=true"
