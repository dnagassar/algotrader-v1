<#
.SYNOPSIS
Runs one V5.35 secure unattended read-only cycle.

.DESCRIPTION
This wrapper accepts only non-secret credential references. It never loads a
plaintext environment file and rejects inherited credential aliases before
starting Python. It does not register or enable a scheduled task.
#>

[CmdletBinding()]
param(
    [ValidateSet("run_once")]
    [string]$Mode = "run_once",
    [string]$OutputRoot = "runs\v5_35_unattended_readonly",
    [string]$AdmissionDbPath = "",
    [string]$AsOf = "",
    [string]$MarketDataCredentialReference = "wincred:algotrader/v5.35/alpaca-market-data/production",
    [string]$PaperCredentialReference = "wincred:algotrader/v5.35/alpaca-paper-observation/production",
    [switch]$SchedulerEnabled,
    [switch]$MarketDataReadAuthorized,
    [switch]$PaperBrokerReadAuthorized,
    [switch]$AllowNetwork
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

if (
    -not $SchedulerEnabled.IsPresent -or
    -not $MarketDataReadAuthorized.IsPresent -or
    -not $PaperBrokerReadAuthorized.IsPresent -or
    -not $AllowNetwork.IsPresent
) {
    throw "run_once requires every explicit read-only authorization switch."
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

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    throw "Unable to locate python on PATH."
}

$Arguments = @(
    "-m",
    "algotrader.execution.v535_unattended_readonly",
    "--output-root",
    $OutputRoot,
    "--credential-provider",
    "windows-credential-manager",
    "--market-data-credential-reference",
    $MarketDataCredentialReference,
    "--paper-credential-reference",
    $PaperCredentialReference,
    "--app-profile",
    "paper",
    "--paper-endpoint",
    "https://paper-api.alpaca.markets",
    "--market-data-endpoint",
    "https://data.alpaca.markets",
    "--scheduler-enabled",
    "--market-data-read-authorized",
    "--paper-broker-read-authorized",
    "--allow-network"
)
if (-not [string]::IsNullOrWhiteSpace($AdmissionDbPath)) {
    $Arguments += @("--admission-db-path", $AdmissionDbPath)
}
if (-not [string]::IsNullOrWhiteSpace($AsOf)) {
    $Arguments += @("--as-of", $AsOf)
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
