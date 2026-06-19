<#
.SYNOPSIS
Runs one repo-local development-autopilot cycle.

.DESCRIPTION
Thin launcher for the Python development-autopilot command. It blocks paper or
credential-bearing shells, resolves the repository root, passes parameters
through to the CLI, and propagates the Python exit code.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs/development_autopilot",
    [string]$WorkOrderPath,
    [string]$ExpectedHead,
    [string]$AgentRoute = "codex",
    [string]$AgentCommand,
    [ValidateSet("verify_only", "commit_only", "commit_and_push")]
    [string]$GitMode = "verify_only",
    [ValidateRange(1, 7200)]
    [int]$CommandTimeoutSeconds = 1800,
    [ValidateSet("always", "changed_files_only")]
    [string]$FullPytestPolicy = "always"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

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
    [Console]::Error.WriteLine("Error: APP_PROFILE is paper. Development autopilot must run offline only without paper profile.")
    exit 2
}

if ($LoadedCredentialVariables.Count -gt 0) {
    [Console]::Error.WriteLine("Error: broker credential environment variable(s) are loaded: $($LoadedCredentialVariables -join ', '). Values were not printed.")
    exit 2
}

$AbsoluteOutputRoot = $OutputRoot
if (-not [System.IO.Path]::IsPathRooted($OutputRoot)) {
    $AbsoluteOutputRoot = Join-Path $RepoRoot $OutputRoot
}

$CliArgs = @(
    "-m", "algotrader.cli",
    "development-autopilot",
    "--output-root", $AbsoluteOutputRoot,
    "--agent-route", $AgentRoute,
    "--git-mode", $GitMode,
    "--command-timeout-seconds", $CommandTimeoutSeconds.ToString(),
    "--full-pytest-policy", $FullPytestPolicy
)

if (-not [string]::IsNullOrEmpty($WorkOrderPath)) {
    $CliArgs += @("--work-order-path", $WorkOrderPath)
}

if (-not [string]::IsNullOrEmpty($ExpectedHead)) {
    $CliArgs += @("--expected-head", $ExpectedHead)
}

if (-not [string]::IsNullOrEmpty($AgentCommand)) {
    $CliArgs += @("--agent-command", $AgentCommand)
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

if ($ExitCode -eq 0) {
    $LatestRunPath = Join-Path $AbsoluteOutputRoot "development_autopilot_latest.json"
    $ReportPath = Join-Path $AbsoluteOutputRoot "development_autopilot_report.md"
    $NextActionPath = Join-Path $AbsoluteOutputRoot "next_action_packet.json"

    Write-Host ""
    Write-Host "Development autopilot completed."
    Write-Host "Latest run summary: $LatestRunPath"
    Write-Host "Report: $ReportPath"
    Write-Host "Next action packet: $NextActionPath"
    Write-Host "Verify-only default: true"
    Write-Host "Paper submit authorized: false"
    Write-Host "Live authorized: false"
    Write-Host "Broker read performed: false"
    Write-Host "Broker mutation performed: false"
}

exit $ExitCode
