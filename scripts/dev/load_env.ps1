<#
.SYNOPSIS
Loads repo-root .env values into the current PowerShell process.

.DESCRIPTION
This helper reads simple KEY=VALUE entries from a local .env file and sets
process-scoped environment variables without printing variable values. It is
for local development shells only; it does not change production code or load
.env automatically.

.PARAMETER Path
Optional path to a dotenv-style file. Defaults to the repo-root .env file.

.PARAMETER Quiet
Suppresses the count-only success message.

.EXAMPLE
. .\scripts\dev\load_env.ps1
#>

[CmdletBinding()]
param(
    [string]$Path = (Join-Path (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")) ".env"),
    [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$envPath = (Resolve-Path -LiteralPath $Path).Path
$loadedCount = 0
$lineNumber = 0

foreach ($line in [System.IO.File]::ReadLines($envPath)) {
    $lineNumber += 1
    $entry = $line.Trim()

    if ($entry.Length -eq 0 -or $entry.StartsWith("#")) {
        continue
    }

    if ($entry.StartsWith("export ")) {
        $entry = $entry.Substring(7).TrimStart()
    }

    $equalsIndex = $entry.IndexOf("=")
    if ($equalsIndex -lt 1) {
        throw "Invalid .env entry at line $lineNumber. Expected KEY=VALUE."
    }

    $name = $entry.Substring(0, $equalsIndex).Trim()
    if ($name -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
        throw "Invalid .env variable name at line $lineNumber."
    }

    $value = $entry.Substring($equalsIndex + 1).Trim()
    if (
        $value.Length -ge 2 -and (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        )
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    Set-Item -Path "Env:$name" -Value $value
    $loadedCount += 1
}

if (-not $Quiet) {
    Write-Host "Loaded $loadedCount local environment variable(s) into this PowerShell process."
}
