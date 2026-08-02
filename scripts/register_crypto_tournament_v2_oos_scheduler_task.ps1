<#
.SYNOPSIS
Registers or unregisters the Windows scheduled task for the tournament-v2 OOS scheduler.

.DESCRIPTION
By default, this script previews a disabled task and does not modify the system.
Use -RegisterTask to create it disabled, add -ActivateTask to enable both the
task and hourly trigger, or use -UnregisterTask to remove it.
#>

[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [switch]$RegisterTask,
    [switch]$ActivateTask,
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

if ($ActivateTask.IsPresent -and -not $RegisterTask.IsPresent) {
    throw "ActivateTask requires RegisterTask."
}

[xml]$TaskXml = $XmlText
$NamespaceManager = New-Object System.Xml.XmlNamespaceManager(
    $TaskXml.NameTable
)
$NamespaceManager.AddNamespace(
    "task",
    "http://schemas.microsoft.com/windows/2004/02/mit/task"
)
$TaskEnabledNodes = @($TaskXml.SelectNodes(
    "/task:Task/task:Settings/task:Enabled",
    $NamespaceManager
))
$TriggerEnabledNodes = @($TaskXml.SelectNodes(
    "/task:Task/task:Triggers/task:TimeTrigger/task:Enabled",
    $NamespaceManager
))
if ($TaskEnabledNodes.Count -ne 1 -or $TriggerEnabledNodes.Count -ne 1) {
    throw "Task XML activation contract requires exact enabled nodes."
}

if ($ActivateTask.IsPresent) {
    if (
        $TaskEnabledNodes[0].InnerText -ne "false" -or
        $TriggerEnabledNodes[0].InnerText -ne "false"
    ) {
        throw "Task XML activation requires disabled task and trigger nodes."
    }
    $TaskEnabledNodes[0].InnerText = "true"
    $TriggerEnabledNodes[0].InnerText = "true"
    $XmlText = $TaskXml.OuterXml
}

if ($RegisterTask.IsPresent) {
    Write-Host "Registering Windows Scheduled Task: $TaskName"
    Write-Host "Repository working directory: $ResolvedRepoRoot"
    Write-Host "Task activation requested: $($ActivateTask.IsPresent.ToString().ToLowerInvariant())"
    
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
    Write-Host "Activation requested: false"
    Write-Host "XML Content to be registered:"
    Write-Host "-------------------------------------------"
    Write-Host $XmlText
    Write-Host "-------------------------------------------"
    Write-Host "Note: No task was registered on the machine. Use -RegisterTask to register."
}
