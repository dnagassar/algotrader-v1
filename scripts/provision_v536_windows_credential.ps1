<#
.SYNOPSIS
Invokes the separately authorized no-echo V5.36 credential provisioner.

.DESCRIPTION
Secret values are requested by Python through an interactive no-echo input
boundary. They are never accepted as PowerShell parameters, command arguments,
environment variables, files, or pipeline input.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AuthorizationArtifact,
    [switch]$ProvisionAuthorized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

if (-not $ProvisionAuthorized.IsPresent) {
    throw "Credential provisioning requires a separate explicit write authorization."
}

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
    throw "Provisioning authorization artifact must be an absolute path."
}
$ArtifactPath = [System.IO.Path]::GetFullPath($AuthorizationArtifact)

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    throw "Unable to locate python on PATH."
}

Push-Location -LiteralPath $RepoRoot
try {
    & $PythonCommand.Source `
        -m algotrader.execution.v536_credential_provisioning `
        --authorization-artifact $ArtifactPath `
        --provision-authorized
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($null -eq $ExitCode) {
    $ExitCode = 1
}
exit $ExitCode
