<#
.SYNOPSIS
Validates the v6.1 crypto SimBroker operating-loop artifact packet.

.DESCRIPTION
Checks required JSON/JSONL/Markdown artifacts, safety labels, SimBroker mode
flags, selected-candidate gate consistency, state ledger continuity, tracked
runs status, and credential sentinel exposure. This validator does not read
brokers, mutate brokers, load credentials, or contact the network.
#>

[CmdletBinding()]
param(
    [string]$OutputRoot = "runs\crypto_trader_demo\latest",
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Get-PythonCommand {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $PythonCommand) {
        return $PythonCommand.Source
    }
    throw "Unable to locate python on PATH."
}

Write-Host "tomorrow_crypto_trader_demo_validator_command=validate_tomorrow_crypto_trader_demo"
Write-Host "tomorrow_crypto_trader_demo_validator_network_used=false"
Write-Host "tomorrow_crypto_trader_demo_validator_broker_read_occurred=false"
Write-Host "tomorrow_crypto_trader_demo_validator_broker_mutation_occurred=false"
Write-Host "Credential values are never printed"

$Python = Get-PythonCommand
$Args = @(
    "-m", "algotrader.execution.tomorrow_crypto_trader_demo",
    "--validate-only",
    "--output-root", $OutputRoot,
    "--format", $Format
)

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
