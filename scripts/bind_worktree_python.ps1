<#
.SYNOPSIS
Bind the trusted system Python's editable `algotrader` install to THIS worktree.

.DESCRIPTION
The offline verification suite includes subprocess wrappers (the V5.30 bounded
paper-probe lifecycle and the V5.29/V5.30 independent-flat operator) that
deliberately resolve a trusted, signed, *registered* Python Software Foundation
interpreter from the Windows registry and strip PYTHONPATH/PYTHONHOME from the
child environment. That is a V5.30/V5.35 credential-boundary hardening, so those
wrappers import `algotrader` from the system interpreter's site-packages -- not
from a virtual environment and not from PYTHONPATH.

Because there is a single registered interpreter, its editable `algotrader`
install always resolves to whichever worktree it was last pointed at, and it
dangles (ModuleNotFoundError in the subprocess wrappers) when that worktree is
deleted -- while every in-process test still passes because pytest's
`pythonpath=["src"]` shadows the broken install. A per-worktree venv cannot fix
those wrappers because they ignore the venv by design.

Run this after switching worktrees and before `.\scripts\verify_offline.ps1
-Full` to point the system interpreter's editable install at the current
worktree, so both in-process and subprocess/isolated tests exercise this
worktree's code.

This script performs package management only. It loads no credentials and makes
no broker, paper, network-trading, or Task Scheduler call.

.PARAMETER Interpreter
Optional explicit path to the registered interpreter to bind. Defaults to the
`py -3` launcher target, falling back to `python` on PATH.

.PARAMETER WithDependencies
Also resolve and install dependencies (use for a first-time machine setup). The
default rebinds the editable pointer only (`--no-deps`) for a fast switch.

.EXAMPLE
.\scripts\bind_worktree_python.ps1

.EXAMPLE
.\scripts\bind_worktree_python.ps1 -WithDependencies
#>
[CmdletBinding()]
param(
    [string]$Interpreter,
    [switch]$WithDependencies
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Resolve-RegisteredInterpreter {
    param([string]$Explicit)

    if (-not [string]::IsNullOrWhiteSpace($Explicit)) {
        if (-not (Test-Path -LiteralPath $Explicit)) {
            throw "Interpreter not found: $Explicit"
        }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }

    try {
        $ViaLauncher = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($ViaLauncher)) {
            return $ViaLauncher.Trim()
        }
    }
    catch {
        # The py launcher is optional; fall back to PATH below.
    }

    $OnPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ([string]::IsNullOrWhiteSpace($OnPath)) {
        throw "No registered Python interpreter found (tried 'py -3' and 'python')."
    }
    return $OnPath
}

$Python = Resolve-RegisteredInterpreter -Explicit $Interpreter
Write-Host "Registered interpreter : $Python"
Write-Host "Binding editable install: $RepoRoot"

$InstallArgs = @("-m", "pip", "install", "-e", $RepoRoot, "--quiet")
if (-not $WithDependencies) {
    $InstallArgs += "--no-deps"
}

& $Python @InstallArgs
if ($LASTEXITCODE -ne 0) {
    throw "pip install -e failed (exit $LASTEXITCODE). For a first-time machine setup, re-run with -WithDependencies."
}

$Editable = & $Python -m pip show algotrader 2>$null |
    Select-String -Pattern "Editable project location"
if ($null -eq $Editable) {
    throw "algotrader is not editable-installed after binding; re-run with -WithDependencies."
}

Write-Host $Editable.ToString().Trim()
Write-Host "Bound. Offline verification (in-process and subprocess wrappers) will use this worktree."
