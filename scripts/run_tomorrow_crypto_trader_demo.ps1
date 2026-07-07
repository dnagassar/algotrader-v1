<#
.SYNOPSIS
Runs the v6.2 crypto SimBroker operating loop with a no-submit paper-readiness packet.

.DESCRIPTION
Default SimBroker mode is fully offline and uses a deterministic local
simulation broker with persisted local state. AlpacaPaper mode is optional and
refuses to proceed unless the operator passes -Mode AlpacaPaper
-AllowAlpacaPaperMutation in a dedicated paper shell. Credential values are
never printed.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_trader_demo\latest",
    [ValidateSet("SimBroker", "AlpacaPaper")]
    [string]$Mode = "SimBroker",
    [switch]$AllowAlpacaPaperMutation,
    [string]$StateRoot = "",
    [Alias("AsOf")]
    [string]$AsOfTimestamp = "",
    [ValidateSet("risk_on", "risk_off", "all_blocked", "bad_data")]
    [string]$Scenario = "risk_on",
    [switch]$ResetState,
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

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
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $PythonCommand) {
        return $PythonCommand.Source
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
foreach ($Name in @("PYTEST_NETWORK", "NETWORK_TESTS", "ALLOW_NETWORK_TESTS", "ALGO_TRADER_ALLOW_NETWORK_TESTS", "RUN_ALPACA_PAPER_INTEGRATION_TESTS")) {
    if (Test-EnvLoaded -Name $Name) {
        $NetworkFlagsLoaded = $true
    }
}
$PaperEndpointExactMatchIndicator = $false
$LiveEndpointIndicator = $AppProfileIsLive
foreach ($EndpointName in @("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL")) {
    $EndpointValue = [Environment]::GetEnvironmentVariable($EndpointName)
    if (-not [string]::IsNullOrWhiteSpace($EndpointValue)) {
        $LowerUrl = $EndpointValue.ToLowerInvariant()
        if ($LowerUrl -eq "https://paper-api.alpaca.markets") {
            $PaperEndpointExactMatchIndicator = $true
        }
        if ($LowerUrl.Contains("api.alpaca.markets") -and -not $LowerUrl.Contains("paper-api")) {
            $LiveEndpointIndicator = $true
        }
    }
}

Write-Host "tomorrow_crypto_trader_demo_command=run_tomorrow_crypto_trader_demo"
Write-Host "tomorrow_crypto_trader_demo_mode=$Mode"
Write-Host "tomorrow_crypto_trader_demo_scenario=$Scenario"
Write-Host "tomorrow_crypto_trader_demo_default_simbroker_offline=$((Format-Bool ($Mode -eq 'SimBroker')))"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
Write-Host "preflight_credential_variables_loaded=$(Format-Bool $CredentialVariablesLoaded)"
Write-Host "preflight_network_flags_loaded=$(Format-Bool $NetworkFlagsLoaded)"
Write-Host "preflight_paper_endpoint_exact_match_indicator=$(Format-Bool $PaperEndpointExactMatchIndicator)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "Credential values are never printed"
Write-Host "tomorrow_crypto_trader_demo_live_authorized=false"

if ($LiveEndpointIndicator) {
    Write-Host "tomorrow_crypto_trader_demo_status=blocked_live_endpoint_indicator"
    exit 2
}

if ($Mode -eq "SimBroker") {
    Write-Host "tomorrow_crypto_trader_demo_broker_mode=simulation_broker"
    Write-Host "tomorrow_crypto_trader_demo_network_used=false"
    Write-Host "tomorrow_crypto_trader_demo_broker_read_occurred=false"
    Write-Host "tomorrow_crypto_trader_demo_paper_submit_authorized=false"
    Write-Host "tomorrow_crypto_trader_demo_broker_mutation_authorized=false"
    if ($AppProfileIsPaper -or $AppProfileIsLive -or $CredentialVariablesLoaded -or $NetworkFlagsLoaded) {
        Write-Host "tomorrow_crypto_trader_demo_status=blocked_unsafe_simbroker_environment"
        exit 2
    }
}
else {
    Write-Host "tomorrow_crypto_trader_demo_broker_mode=alpaca_paper"
    if (-not $AllowAlpacaPaperMutation.IsPresent) {
        Write-Host "tomorrow_crypto_trader_demo_status=blocked_not_authorized"
        exit 2
    }
    if (-not $AppProfileIsPaper) {
        Write-Host "tomorrow_crypto_trader_demo_status=blocked_not_paper_profile"
        exit 2
    }
    if (-not $CredentialVariablesLoaded) {
        Write-Host "tomorrow_crypto_trader_demo_status=blocked_credentials_not_loaded"
        exit 2
    }
    if ($NetworkFlagsLoaded) {
        Write-Host "tomorrow_crypto_trader_demo_status=blocked_network_test_flag_loaded"
        exit 2
    }
}

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.execution.tomorrow_crypto_trader_demo",
    "--output-root", $OutputRoot,
    "--mode", $Mode,
    "--scenario", $Scenario,
    "--format", $Format
)

if (-not [string]::IsNullOrWhiteSpace($StateRoot)) {
    $Args += @("--state-root", $StateRoot)
}
if (-not [string]::IsNullOrWhiteSpace($AsOfTimestamp)) {
    $Args += @("--as-of", $AsOfTimestamp)
}
if ($ResetState.IsPresent) {
    $Args += @("--reset-state")
}
if ($AllowAlpacaPaperMutation.IsPresent) {
    $Args += @("--allow-alpaca-paper-mutation")
}

$ExitCode = 0
Push-Location -LiteralPath $RepoRoot
try {
    & $Python @Args
    $ExitCode = $LASTEXITCODE
}
catch {
    if ($null -ne $LASTEXITCODE) {
        $ExitCode = $LASTEXITCODE
    }
    else {
        $ExitCode = 1
    }
}
finally {
    Pop-Location
}

if ($null -eq $ExitCode) {
    $ExitCode = 0
}
exit $ExitCode
