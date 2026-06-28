<#
.SYNOPSIS
Runs the repo's offline-safe verification checks.

.DESCRIPTION
This helper performs local repository hygiene checks, prints only boolean
credential/profile state, blocks unsafe paper/credential environments, and runs
the default offline safety guard tests. Use -Full to include the full pytest
suite after the targeted guard tests.

.PARAMETER Full
Run the full pytest suite after the targeted offline safety guard tests.

.EXAMPLE
pwsh ./scripts/verify_offline.ps1

.EXAMPLE
pwsh ./scripts/verify_offline.ps1 -Full
#>

[CmdletBinding()]
param(
    [switch]$Full
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$CredentialVariableNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
$GuardTestPaths = @(
    "tests/unit/test_dependency_direction.py",
    "tests/unit/test_broker_mutation_surface_invariant.py",
    "tests/unit/test_default_pytest_network_guard.py",
    "tests/unit/test_strategy_challenger_factory.py"
)

function Write-Section {
    param([string]$Title)

    Write-Host ""
    Write-Host "==> $Title"
}

function Format-Command {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    if ($Arguments.Count -eq 0) {
        return $FilePath
    }

    return "$FilePath $($Arguments -join ' ')"
}

function Invoke-CheckedCommand {
    param(
        [string]$Title,
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    Write-Section $Title
    Write-Host "+ $(Format-Command -FilePath $FilePath -Arguments $Arguments)"

    Push-Location -LiteralPath $RepoRoot
    try {
        & $FilePath @Arguments
        $ExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if ($null -eq $ExitCode) {
        $ExitCode = 0
    }

    if ($ExitCode -ne 0) {
        throw "Command failed with exit code ${ExitCode}: $(Format-Command -FilePath $FilePath -Arguments $Arguments)"
    }
}

function Test-ProcessEnvironmentVariableLoaded {
    param([string]$Name)

    $ProcessEnvironment = [System.Environment]::GetEnvironmentVariables("Process")
    return $ProcessEnvironment.Contains($Name)
}

function Stop-OfflineVerification {
    param([string]$Message)

    [Console]::Error.WriteLine($Message)
    exit 2
}

function Invoke-HygienePrecheck {
    Write-Section "Repository hygiene precheck"
    Invoke-CheckedCommand "git status" "git" @("status", "--short")
    Invoke-CheckedCommand "git branch" "git" @("branch", "--show-current")
    Invoke-CheckedCommand "git log" "git" @("log", "--oneline", "-3")
    Invoke-CheckedCommand "git HEAD" "git" @("rev-parse", "HEAD")
    Invoke-CheckedCommand "git origin/main" "git" @("rev-parse", "origin/main")
    Invoke-CheckedCommand "tracked runs/daily" "git" @("ls-files", "runs/daily")
    Invoke-CheckedCommand "tracked runs/daily_soak" "git" @("ls-files", "runs/daily_soak")
    Invoke-CheckedCommand "tracked runs/paper_autopilot" "git" @("ls-files", "runs/paper_autopilot")
    Invoke-CheckedCommand "tracked runs/strategy_challengers" "git" @("ls-files", "runs/strategy_challengers")
}

function Invoke-CredentialProfilePrecheck {
    Write-Section "Credential/profile precheck"

    $AppProfileIsPaper = $env:APP_PROFILE -eq "paper"
    $NetworkTestsFlagEnabled = $env:ALGO_TRADER_ALLOW_NETWORK_TESTS -eq "1"
    $PaperIntegrationFlagEnabled = $env:RUN_ALPACA_PAPER_INTEGRATION_TESTS -eq "1"
    $PytestAddopts = [System.Environment]::GetEnvironmentVariable("PYTEST_ADDOPTS", "Process")
    $PytestAllowNetworkEnabled = $PytestAddopts -match "(^|\s)--allow-network(\s|$)"

    Write-Host "APP_PROFILE_is_paper: $AppProfileIsPaper"

    $LoadedCredentialVariables = @()
    foreach ($Name in $CredentialVariableNames) {
        $Loaded = Test-ProcessEnvironmentVariableLoaded -Name $Name
        Write-Host "${Name}_loaded: $Loaded"
        if ($Loaded) {
            $LoadedCredentialVariables += $Name
        }
    }

    Write-Host "ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled: $NetworkTestsFlagEnabled"
    Write-Host "PYTEST_ADDOPTS_allow_network: $PytestAllowNetworkEnabled"
    Write-Host "RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled: $PaperIntegrationFlagEnabled"

    if ($AppProfileIsPaper) {
        Stop-OfflineVerification "Offline verification blocked: APP_PROFILE is paper. Unset APP_PROFILE or use a non-paper profile before running pytest."
    }

    if ($LoadedCredentialVariables.Count -gt 0) {
        Stop-OfflineVerification "Offline verification blocked: broker credential environment variable(s) are loaded: $($LoadedCredentialVariables -join ', '). Values were not printed."
    }

    if ($NetworkTestsFlagEnabled -or $PytestAllowNetworkEnabled) {
        Stop-OfflineVerification "Offline verification blocked: network test escape hatch is enabled. Disable ALGO_TRADER_ALLOW_NETWORK_TESTS and PYTEST_ADDOPTS --allow-network before running pytest."
    }

    if ($PaperIntegrationFlagEnabled) {
        Stop-OfflineVerification "Offline verification blocked: paper integration test flag is enabled. Disable RUN_ALPACA_PAPER_INTEGRATION_TESTS before running pytest."
    }
}

function Invoke-OfflineTestChecks {
    Invoke-CheckedCommand "targeted offline safety guard tests" "python" (@("-m", "pytest") + $GuardTestPaths)

    if ($Full) {
        Invoke-CheckedCommand "full offline pytest suite" "python" @("-m", "pytest")
    }
    else {
        Write-Section "full pytest"
        Write-Host "Skipped. Re-run with -Full to execute python -m pytest."
    }
}

function Invoke-FinalHygieneCheck {
    Write-Section "Repository hygiene final check"
    Invoke-CheckedCommand "git diff whitespace check" "git" @("diff", "--check")
    Invoke-CheckedCommand "git status" "git" @("status", "--short")
    Invoke-CheckedCommand "staged files" "git" @("diff", "--cached", "--name-only")
    Invoke-CheckedCommand "changed src files" "git" @("diff", "--name-only", "HEAD", "--", "src")
    Invoke-CheckedCommand "untracked src/tests files" "git" @("ls-files", "--others", "--exclude-standard", "src", "tests")
    Invoke-CheckedCommand "tracked runs/daily" "git" @("ls-files", "runs/daily")
    Invoke-CheckedCommand "tracked runs/daily_soak" "git" @("ls-files", "runs/daily_soak")
    Invoke-CheckedCommand "tracked runs/paper_autopilot" "git" @("ls-files", "runs/paper_autopilot")
    Invoke-CheckedCommand "tracked runs/strategy_challengers" "git" @("ls-files", "runs/strategy_challengers")
}

try {
    Invoke-HygienePrecheck
    Invoke-CredentialProfilePrecheck
    Invoke-OfflineTestChecks
    Invoke-FinalHygieneCheck

    Write-Section "offline verification result"
    Write-Host "PASS"
}
catch {
    Write-Error $_
    exit 1
}
