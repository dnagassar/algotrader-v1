<#
.SYNOPSIS
Builds the offline tournament-v2 forward-shadow readiness packet.

.DESCRIPTION
This command is credential-free, network-free, broker-free, and no-submit.
It preregisters the downstream evidence contract and can bind an activation
only after tournament v2 produces a sealed terminal winner.
#>

[CmdletBinding()]
param(
    [string]$TournamentRoot = "runs\crypto_strategy_tournament\v2\latest",
    [string]$OutputRoot = "runs\crypto_strategy_tournament\v2\forward_shadow\latest",
    [string]$AsOf = ((Get-Date).ToUniversalTime().ToString("o")),
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

$ErrorActionPreference = "Stop"

$CredentialNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)

if ($env:APP_PROFILE -eq "paper") {
    throw "Forward-shadow readiness is offline only; APP_PROFILE=paper is not allowed."
}

foreach ($CredentialName in $CredentialNames) {
    $CredentialValue = [Environment]::GetEnvironmentVariable($CredentialName, "Process")
    if (-not [string]::IsNullOrWhiteSpace($CredentialValue)) {
        throw "Forward-shadow readiness requires a credential-free process."
    }
}

$Arguments = @(
    "-m",
    "algotrader.research.crypto_tournament_v2_forward_shadow",
    "--tournament-root",
    $TournamentRoot,
    "--output-root",
    $OutputRoot,
    "--as-of",
    $AsOf,
    "--format",
    $Format
)

& python @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "Forward-shadow readiness failed with exit code $LASTEXITCODE."
}
