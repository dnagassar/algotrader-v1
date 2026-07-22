<#
.SYNOPSIS
Routes one V5.36 bounded Windows-host canary lifecycle operation.

.DESCRIPTION
Only a non-secret, absolute authorization-artifact path crosses this wrapper.
The Python boundary performs the exact authorization, source, identity,
credential-reference, scheduler, timing, and evidence validation. This wrapper
never reads a plaintext credential file or registers/enables a task itself.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "preview",
        "install-disabled",
        "attest-disabled",
        "arm-exact-window",
        "execute",
        "disarm",
        "post-run-attest"
    )]
    [string]$Mode,
    [Parameter(Mandatory = $true)]
    [string]$AuthorizationArtifact,
    [switch]$TaskMutationAuthorized,
    [switch]$CredentialReadAuthorized,
    [switch]$ExecuteAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$ForbiddenEnvironmentNames = @(
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID"
)
$LoadedForbiddenNames = @(
    $ForbiddenEnvironmentNames | Where-Object {
        -not [string]::IsNullOrWhiteSpace(
            [Environment]::GetEnvironmentVariable($_, "Process")
        )
    }
)
if ($LoadedForbiddenNames.Count -ne 0) {
    throw "Credential or profile environment aliases are forbidden; values were not read or printed."
}

if (-not [System.IO.Path]::IsPathRooted($AuthorizationArtifact)) {
    throw "Authorization artifact must be an absolute path."
}
$ArtifactPath = [System.IO.Path]::GetFullPath($AuthorizationArtifact)

$MutationModes = @("install-disabled", "arm-exact-window", "execute", "disarm")
$CredentialModes = @("arm-exact-window", "execute")
if ($Mode -in $MutationModes -and -not $TaskMutationAuthorized.IsPresent) {
    throw "Selected mode requires the explicit task-mutation authorization switch."
}
if ($Mode -in $CredentialModes -and -not $CredentialReadAuthorized.IsPresent) {
    throw "Selected mode requires the explicit credential-read authorization switch."
}
if ($Mode -eq "execute" -and -not $ExecuteAuthorized.IsPresent) {
    throw "Execute mode requires the explicit canary-execution authorization switch."
}

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    throw "Unable to locate python on PATH."
}

$Arguments = @(
    "-m",
    "algotrader.execution.v536_windows_host_canary",
    "--mode",
    $Mode,
    "--authorization-artifact",
    $ArtifactPath
)
if ($TaskMutationAuthorized.IsPresent) {
    $Arguments += "--task-mutation-authorized"
}
if ($CredentialReadAuthorized.IsPresent) {
    $Arguments += "--credential-read-authorized"
}
if ($ExecuteAuthorized.IsPresent) {
    $Arguments += "--execute-authorized"
}

$ExitCode = 1
Push-Location -LiteralPath $RepoRoot
try {
    & $PythonCommand.Source @Arguments
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($null -eq $ExitCode) {
    $ExitCode = 1
}
exit $ExitCode
