<#
.SYNOPSIS
    Host script wrapper for the unattended SPY read-only market-data refresh seam.
.DESCRIPTION
    Captures current UTC time once and invokes the in-process Python executor seam.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$currentDir = (Get-Location).Path

if ($repoRoot -ne $currentDir -or -not (Test-Path (Join-Path $repoRoot "pyproject.toml"))) {
    Write-Error "Must run from canonical repository root: $repoRoot"
    exit 2
}

$asOfUtc = [DateTimeOffset]::UtcNow.ToUniversalTime().ToString('o', [System.Globalization.CultureInfo]::InvariantCulture)

python -m algotrader.execution.autonomy_read_only_network_executor --as-of "$asOfUtc" --apply --format json
$exitCode = $LASTEXITCODE

exit $exitCode
