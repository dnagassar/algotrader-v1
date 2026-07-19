<#
.SYNOPSIS
Registers or unregisters the Windows scheduled task for the tournament-v2 OOS scheduler.

.DESCRIPTION
By default, this script runs in preview mode and does not modify the system.
Use -RegisterTask to create/enable the task, or -UnregisterTask to remove it.
#>

[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [switch]$RegisterTask,
    [switch]$UnregisterTask,
    [string]$TaskName = "crypto-tournament-v2-oos-scheduler"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$ScriptRepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $ResolvedRepoRoot = $ScriptRepoRoot
} else {
    $ResolvedRepoRoot = (Resolve-Path -LiteralPath $RepositoryRoot).Path
}

$TemplatePath = Join-Path $ScriptRepoRoot "docs\design\crypto_tournament_v2_oos_scheduler_task.xml"
if (-not (Test-Path -LiteralPath $TemplatePath -PathType Leaf)) {
    throw "Task XML template is missing at $TemplatePath"
}

# Load and replace repository root
$XmlText = Get-Content -LiteralPath $TemplatePath -Raw
$XmlText = $XmlText.Replace("%REPO_ROOT%", $ResolvedRepoRoot)

# Perform actions
if ($RegisterTask.IsPresent -and $UnregisterTask.IsPresent) {
    throw "Cannot specify both -RegisterTask and -UnregisterTask."
}

if ($RegisterTask.IsPresent) {
    Write-Host "Registering Windows Scheduled Task: $TaskName"
    Write-Host "Repository working directory: $ResolvedRepoRoot"
    
    # Import modules if needed, though they are usually auto-loaded
    Register-ScheduledTask -TaskName $TaskName -Xml $XmlText -Force
    Write-Host "Task successfully registered."
}
elseif ($UnregisterTask.IsPresent) {
    Write-Host "Unregistering Windows Scheduled Task: $TaskName"
    
    # Check if task exists first to avoid unnecessary errors
    $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $Task) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Task successfully unregistered."
    } else {
        Write-Host "Task $TaskName does not exist. No-op."
    }
}
else {
    Write-Host "--- SCHEDULED TASK REGISTRATION PREVIEW ---"
    Write-Host "Task Name: $TaskName"
    Write-Host "Target Repository Root: $ResolvedRepoRoot"
    Write-Host "XML Content to be registered:"
    Write-Host "-------------------------------------------"
    Write-Host $XmlText
    Write-Host "-------------------------------------------"
    Write-Host "Note: No task was registered on the machine. Use -RegisterTask to register."
}
