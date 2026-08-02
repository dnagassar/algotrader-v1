<#
.SYNOPSIS
Runs the no-submit crypto tournament v2 forward-OOS state machine.

.DESCRIPTION
Initialize, status, and readiness modes are offline. market_data_fetch is the
only network-capable mode and requires both explicit switches. It delegates to
the guarded crypto bars adapter for BTCUSD, ETHUSD, and SOLUSD only. The script
cannot submit, cancel, replace, close, liquidate, or mutate paper/live state.
#>

[CmdletBinding()]
param(
    [ValidateSet(
        "initialize",
        "status",
        "readiness",
        "market_data_fetch"
    )]
    [string]$Mode = "status",
    [string]$OutputRoot = (
        "runs\crypto_strategy_tournament\v2\latest"
    ),
    [string]$AsOf = "",
    [string]$DiscoverySourcePath = (
        "runs\crypto_strategy_tournament\v1\input\crypto_1h_1y.csv"
    ),
    [string]$DiscoveryReceiptPath = (
        "runs\crypto_strategy_tournament\v1\refresh\refresh_packet.json"
    ),
    [string]$CredentialProvider = "windows-credential-manager",
    [string]$CredentialReference = (
        "wincred:algotrader/v5.35/alpaca-market-data/production"
    ),
    [string]$AppProfile = "paper",
    [string]$PaperEndpoint = "https://paper-api.alpaca.markets",
    [string]$MarketDataEndpoint = "https://data.alpaca.markets",
    [switch]$MarketDataFetchAuthorized,
    [switch]$AllowNetwork
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (
    Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
).Path

function Test-EnvLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    return -not [string]::IsNullOrWhiteSpace($Value)
}

function Format-Bool {
    param([bool]$Value)
    return $Value.ToString().ToLowerInvariant()
}

$CredentialAliasNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
$ExplicitSecureParameters = @(
    @(
        "CredentialProvider",
        "CredentialReference",
        "AppProfile",
        "PaperEndpoint",
        "MarketDataEndpoint"
    ) | Where-Object { $PSBoundParameters.ContainsKey($_) }
)

if ($Mode -eq "market_data_fetch") {
    if (
        -not $MarketDataFetchAuthorized.IsPresent -or
        -not $AllowNetwork.IsPresent
    ) {
        throw (
            "market_data_fetch requires " +
            "-MarketDataFetchAuthorized and -AllowNetwork."
        )
    }
    foreach ($RequiredValue in @(
        $CredentialProvider,
        $CredentialReference,
        $AppProfile,
        $PaperEndpoint,
        $MarketDataEndpoint
    )) {
        if ([string]::IsNullOrWhiteSpace($RequiredValue)) {
            throw "market_data_fetch secure parameters cannot be blank."
        }
    }
    foreach ($CredentialAliasName in $CredentialAliasNames) {
        if (Test-EnvLoaded -Name $CredentialAliasName) {
            throw (
                "market_data_fetch rejects ambient credential aliases; " +
                "use the opaque secure credential reference."
            )
        }
    }
}
elseif (
    $MarketDataFetchAuthorized.IsPresent -or
    $AllowNetwork.IsPresent -or
    $ExplicitSecureParameters.Count -gt 0
) {
    throw (
        "Network authorization or secure credential parameters require " +
        "-Mode market_data_fetch."
    )
}

Write-Host "crypto_tournament_v2_mode=$Mode"
Write-Host "crypto_tournament_v2_symbols=BTCUSD,ETHUSD,SOLUSD"
Write-Host "crypto_tournament_v2_no_submit=true"
Write-Host "crypto_tournament_v2_paper_mutation_authorized=false"
Write-Host (
    "APP_PROFILE_is_paper=" +
    (Format-Bool (
        [Environment]::GetEnvironmentVariable("APP_PROFILE") -eq "paper"
    ))
)
foreach ($Name in $CredentialAliasNames) {
    Write-Host (
        $Name + "_loaded=" +
        (Format-Bool (Test-EnvLoaded -Name $Name))
    )
}
Write-Host "credential_values_exposed=false"
Write-Host "broker_read_occurred=false"
Write-Host "broker_mutation_occurred=false"
Write-Host "paper_submit_occurred=false"
Write-Host "live_endpoint_touched=false"

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $PythonCommand) {
    throw "Unable to locate python on PATH."
}

$Arguments = @(
    "-m",
    "algotrader.orchestration.crypto_tournament_v2_forward_oos",
    "--mode",
    $Mode,
    "--output-root",
    $OutputRoot,
    "--discovery-source-path",
    $DiscoverySourcePath,
    "--discovery-receipt-path",
    $DiscoveryReceiptPath
)
if (-not [string]::IsNullOrWhiteSpace($AsOf)) {
    $Arguments += @("--as-of", $AsOf)
}
if ($Mode -eq "market_data_fetch") {
    $Arguments += @(
        "--market-data-fetch-authorized",
        "--allow-network",
        "--credential-provider", $CredentialProvider,
        "--credential-reference", $CredentialReference,
        "--app-profile", $AppProfile,
        "--paper-endpoint", $PaperEndpoint,
        "--market-data-endpoint", $MarketDataEndpoint
    )
}

$ExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    & $PythonCommand.Source @Arguments
    $ExitCode = $LASTEXITCODE
}
catch {
    $ExitCode = 1
    throw
}
finally {
    Pop-Location
}
if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
