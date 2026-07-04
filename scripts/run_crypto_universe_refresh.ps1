<#
Runs the deterministic crypto universe/history/orderability refresh packet.

Default mode is offline_fixture and never requires network, broker, credentials,
or APP_PROFILE=paper. local_replay consumes existing local artifacts only.
paper_read_only is explicitly gated and delegates the broker-facing read to the
existing no-submit crypto visibility cycle before normalizing its local output.
Credential values are never printed.
#>

[CmdletBinding()]
param(
    [ValidateSet("offline_fixture", "local_replay", "paper_read_only")]
    [string]$Mode = "offline_fixture",
    [string]$OutputRoot = "runs\crypto_universe_refresh\latest",
    [string]$BarsCsv = "runs\operator_input\crypto_paper_bars.csv",
    [string]$CryptoVisibilityStatus = "runs\crypto_paper_visibility\latest\latest_status.json",
    [string]$PaperVisibilityOutputRoot = "runs\crypto_paper_visibility\latest",
    [string]$AsOfTimestamp,
    [ValidateSet("text", "json")]
    [string]$Format = "text",
    [switch]$PaperReadOnlyAuthorized
)

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DefaultPaperBaseUrl = "https://paper-api.alpaca.markets"

function Test-EnvLoaded {
    param([string]$Name)
    $Value = [Environment]::GetEnvironmentVariable($Name)
    return -not [string]::IsNullOrWhiteSpace($Value)
}

function Format-Bool {
    param([bool]$Value)
    return $Value.ToString().ToLowerInvariant()
}

function Get-PythonCommand {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $Python) {
        return $Python.Source
    }
    throw "Unable to locate python on PATH."
}

$AppProfile = [Environment]::GetEnvironmentVariable("APP_PROFILE")
$AppProfileIsPaper = ($AppProfile -eq "paper")
$AppProfileIsLive = ($AppProfile -eq "live")
$CredentialNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
$CredentialVariablesLoaded = $false
foreach ($Name in $CredentialNames) {
    if (Test-EnvLoaded -Name $Name) {
        $CredentialVariablesLoaded = $true
    }
}
$NetworkFlagsLoaded = $false
foreach ($Name in @("ALGO_TRADER_ALLOW_NETWORK_TESTS", "RUN_ALPACA_PAPER_INTEGRATION_TESTS")) {
    if (Test-EnvLoaded -Name $Name) {
        $NetworkFlagsLoaded = $true
    }
}
$PaperBaseUrl = [Environment]::GetEnvironmentVariable("ALPACA_PAPER_BASE_URL")
if ([string]::IsNullOrWhiteSpace($PaperBaseUrl)) {
    $PaperBaseUrl = $DefaultPaperBaseUrl
}
$PaperEndpointExactMatchIndicator = (
    $PaperBaseUrl.TrimEnd("/").ToLowerInvariant() -eq $DefaultPaperBaseUrl
)
$LiveEndpointIndicator = $AppProfileIsLive
foreach ($EndpointName in @("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL")) {
    $EndpointValue = [Environment]::GetEnvironmentVariable($EndpointName)
    if (-not [string]::IsNullOrWhiteSpace($EndpointValue)) {
        $LowerUrl = $EndpointValue.ToLowerInvariant()
        if ($LowerUrl.Contains("api.alpaca.markets") -and -not $LowerUrl.Contains("paper")) {
            $LiveEndpointIndicator = $true
        }
    }
}

Write-Host "crypto_universe_refresh_command=run_crypto_universe_refresh"
Write-Host "crypto_universe_refresh_mode=$Mode"
Write-Host "crypto_universe_refresh_no_submit_enforced=true"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
Write-Host "preflight_credential_variables_loaded=$(Format-Bool $CredentialVariablesLoaded)"
Write-Host "preflight_network_flags_loaded=$(Format-Bool $NetworkFlagsLoaded)"
Write-Host "preflight_paper_endpoint_exact_match_indicator=$(Format-Bool $PaperEndpointExactMatchIndicator)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "Credential values are never printed"
Write-Host "crypto_universe_refresh_paper_submit_authorized=false"
Write-Host "crypto_universe_refresh_paper_submit_performed=false"
Write-Host "crypto_universe_refresh_broker_mutation_performed=false"
Write-Host "crypto_universe_refresh_live_mutation_performed=false"

if ($Mode -ne "paper_read_only") {
    if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $NetworkFlagsLoaded -or $LiveEndpointIndicator) {
        Write-Host "crypto_universe_refresh_status=blocked_unsafe_environment"
        exit 2
    }
} else {
    if (-not $PaperReadOnlyAuthorized.IsPresent) {
        Write-Host "crypto_universe_refresh_status=blocked_paper_read_only_authorization_required"
        exit 2
    }
    if ((-not $AppProfileIsPaper) -or $AppProfileIsLive -or (-not $CredentialVariablesLoaded) -or $NetworkFlagsLoaded -or (-not $PaperEndpointExactMatchIndicator) -or $LiveEndpointIndicator) {
        Write-Host "crypto_universe_refresh_status=blocked_paper_read_only_preflight"
        exit 2
    }
    & (Join-Path $PSScriptRoot "run_crypto_paper_visibility_cycle.ps1") `
        -OutputRoot $PaperVisibilityOutputRoot `
        -BarsCsv $BarsCsv `
        -Format "json"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "crypto_universe_refresh_status=blocked_paper_visibility_cycle_failed"
        exit $LASTEXITCODE
    }
    $CryptoVisibilityStatus = Join-Path $PaperVisibilityOutputRoot "latest_status.json"
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.orchestration.crypto_universe_refresh",
    "--mode", $Mode,
    "--output-root", $OutputRoot,
    "--bars-csv", $BarsCsv,
    "--crypto-visibility-status", $CryptoVisibilityStatus,
    "--format", $Format
)
if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $Args += @("--as-of", $AsOfTimestamp)
}

Push-Location $RepoRoot
try {
    & $Python @Args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
