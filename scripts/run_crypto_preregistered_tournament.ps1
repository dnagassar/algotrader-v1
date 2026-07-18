<#
.SYNOPSIS
Runs the preregistered crypto strategy tournament from one local hourly CSV.

.DESCRIPTION
This command is offline, research-only, and no-submit. It exposes no network,
credential, broker, paper-mutation, or live-trading switch. The candidate set,
cost cases, temporal windows, and promotion gates are frozen in Python code.
#>

[CmdletBinding()]
param(
    [string]$InputPath = "runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv",
    [string]$RefreshPacketPath = "runs\crypto_strategy_tournament\v1\refresh\refresh_packet.json",
    [string]$OutputRoot = "runs\crypto_strategy_tournament\v1\latest",
    [Parameter(Mandatory = $true)]
    [string]$AsOfTimestamp,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Python = (Get-Command python -ErrorAction Stop).Source
$OutputJson = Join-Path $OutputRoot "tournament_packet.json"
$OutputMarkdown = Join-Path $OutputRoot "tournament_packet.md"
$Args = @(
    "-m", "algotrader.research.crypto_preregistered_tournament",
    "--input-path", $InputPath,
    "--refresh-packet-path", $RefreshPacketPath,
    "--as-of", $AsOfTimestamp,
    "--output-json", $OutputJson,
    "--output-markdown", $OutputMarkdown,
    "--format", $Format
)

Write-Host "crypto_tournament_command=run_crypto_preregistered_tournament"
Write-Host "crypto_tournament_offline_only=true"
Write-Host "crypto_tournament_no_submit_enforced=true"
Write-Host "crypto_tournament_network_access_attempted=false"
Write-Host "crypto_tournament_broker_read_occurred=false"
Write-Host "crypto_tournament_broker_mutation_occurred=false"
Write-Host "crypto_tournament_live_endpoint_touched=false"

Push-Location -LiteralPath $RepoRoot
try {
    & $Python @Args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
