<#
.SYNOPSIS
Runs the exact account-bound, read-only M376 SPY order reconciliation.

.DESCRIPTION
Loads one opaque Alpaca paper-observation credential from Windows Credential
Manager and performs only account, position, bounded open-SPY order, and exact
order-ID reads. It has no submit, cancel, replace, close, liquidation,
paper-mutation, or live path.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\paper_lab\secure_m376_reconciliation",
    [string]$ReconciliationLogPath = "runs\paper_lab\m432_m376_read_only_reconciliation_refresh.jsonl",
    [string]$PaperCredentialReference = "wincred:algotrader/v5.35/alpaca-paper-observation/production",
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$ForbiddenEnvironmentNames = @(
    "APP_PROFILE", "ALPACA_API_KEY", "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY", "ALPACA_SECRET_KEY", "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY", "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID", "APCA_EXPECTED_PAPER_ACCOUNT_ID",
    "EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_BASE_URL", "ALPACA_BASE_URL", "ALPACA_LIVE_BASE_URL",
    "APCA_API_BASE_URL"
)
$ProcessEnvironment = [Environment]::GetEnvironmentVariables("Process")
$LoadedForbidden = @(
    $ForbiddenEnvironmentNames | Where-Object { $ProcessEnvironment.Contains($_) }
)

Write-Host "preflight_forbidden_environment_variables_loaded=$($LoadedForbidden.Count)"
Write-Host "preflight_secure_credential_provider=windows-credential-manager"
Write-Host "preflight_paper_endpoint=https://paper-api.alpaca.markets"
Write-Host "preflight_exact_order_id_read=true"
Write-Host "preflight_open_spy_order_read=true"
Write-Host "preflight_paper_mutation_authorized=false"
Write-Host "preflight_live_authorized=false"

$Arguments = @(
    "-m", "algotrader.execution.secure_spy_m376_reconciliation",
    "--output-root", $OutputRoot,
    "--reconciliation-log-path", $ReconciliationLogPath,
    "--paper-credential-reference", $PaperCredentialReference,
    "--format", $Format
)

Push-Location -LiteralPath $RepoRoot
try {
    & python @Arguments
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($null -eq $ExitCode) { $ExitCode = 1 }
exit $ExitCode