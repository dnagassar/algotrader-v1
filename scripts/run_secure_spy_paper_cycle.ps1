<#
.SYNOPSIS
Runs one secure, bounded SPY paper operating cycle.

.DESCRIPTION
Loads one account-bound paper credential through Windows Credential Manager,
runs a no-submit visibility pass, and revalidates the generated readiness
packet before permitting at most one $25 paper-only action. The mutation pass
is disabled unless -AllowPaperMutation is explicit. Credential values are
never placed in this process environment, command arguments, or output.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\paper_autopilot\secure_spy_paper_cycle",
    [string]$BarsCsv = "runs\operator_input\m446_spy_daily_tiingo_adjusted_canonical.csv",
    [string]$OrderJournalPath = "runs\paper_autopilot\state\order_journal.sqlite3",
    [string]$StrategySleeveLedgerPath = "runs\paper_autopilot\state\strategy_sleeves.sqlite3",
    [string]$PaperCredentialReference = "wincred:algotrader/v5.35/alpaca-paper-observation/production",
    [string]$MaxNotional = "25.00",
    [string]$MaxPortfolioNotional = "60.00",
    [ValidateRange(1, 2)]
    [int]$MaxSleeveOrdersPerSession = 2,
    [ValidateSet(
        "spy_sma_50_200_training_wheel",
        "spy_rsi_14_mean_reversion_paper"
    )]
    [string]$ActiveStrategyId = "spy_sma_50_200_training_wheel",
    [switch]$AllowPaperMutation,
    [switch]$AdoptExistingPositionToActiveSleeve,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
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
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_BASE_URL",
    "ALPACA_BASE_URL",
    "ALPACA_LIVE_BASE_URL",
    "APCA_API_BASE_URL"
)
$ProcessEnvironment = [System.Environment]::GetEnvironmentVariables("Process")
$LoadedForbiddenVariables = @(
    $ForbiddenEnvironmentNames |
        Where-Object { $ProcessEnvironment.Contains($_) }
)

Write-Host "preflight_forbidden_environment_variables_loaded=$($LoadedForbiddenVariables.Count)"
Write-Host "preflight_secure_credential_provider=windows-credential-manager"
Write-Host "preflight_paper_endpoint=https://paper-api.alpaca.markets"
Write-Host "preflight_allow_paper_mutation=$($AllowPaperMutation.IsPresent.ToString().ToLowerInvariant())"
Write-Host "preflight_max_orders_per_cycle=1"
Write-Host "preflight_max_order_notional=$MaxNotional"
Write-Host "preflight_max_portfolio_notional=$MaxPortfolioNotional"
Write-Host "preflight_max_sleeve_orders_per_session=$MaxSleeveOrdersPerSession"
Write-Host "preflight_active_strategy_id=$ActiveStrategyId"
Write-Host "preflight_adopt_existing_position_to_active_sleeve=$($AdoptExistingPositionToActiveSleeve.IsPresent.ToString().ToLowerInvariant())"
Write-Host "preflight_live_authorized=false"

$CliArgs = @(
    "-m", "algotrader.execution.secure_spy_paper_cycle",
    "--output-root", $OutputRoot,
    "--bars-csv", $BarsCsv,
    "--order-journal-path", $OrderJournalPath,
    "--strategy-sleeve-ledger-path", $StrategySleeveLedgerPath,
    "--credential-provider", "windows-credential-manager",
    "--paper-credential-reference", $PaperCredentialReference,
    "--max-notional", $MaxNotional,
    "--max-portfolio-notional", $MaxPortfolioNotional,
    "--max-sleeve-orders-per-session", $MaxSleeveOrdersPerSession,
    "--active-strategy-id", $ActiveStrategyId,
    "--format", $Format
)
if ($AllowPaperMutation.IsPresent) {
    $CliArgs += "--allow-paper-mutation"
}
if ($AdoptExistingPositionToActiveSleeve.IsPresent) {
    $CliArgs += "--adopt-existing-position-to-active-sleeve"
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
exit $ExitCode
