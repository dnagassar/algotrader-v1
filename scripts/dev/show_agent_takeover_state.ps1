[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location -LiteralPath $RepoRoot
try {
    Write-Output "repository_root=$RepoRoot"
    Write-Output "branch=$(git branch --show-current)"
    Write-Output "head=$(git rev-parse HEAD)"

    Write-Output "recent_commits:"
    git log --oneline -10
    Write-Output "status:"
    git status --short
    Write-Output "staged_files:"
    git diff --cached --name-only
    Write-Output "unstaged_files:"
    git diff --name-only
    Write-Output "untracked_source_test_script_doc_files:"
    git ls-files --others --exclude-standard src tests scripts docs
    Write-Output "tracked_runs_files:"
    git ls-files runs
    Write-Output "active_implementation:"
    Get-Content -LiteralPath "docs\agent_context\active_implementation.md"

    $credentialNames = @(
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY"
    )
    $credentialVariablesPresent = @(
        $credentialNames | Where-Object { Test-Path -LiteralPath ("Env:" + $_) }
    ).Count -gt 0
    $networkTestFlagsPresent = @(
        "ALLOW_NETWORK_TESTS", "NETWORK_TESTS_ENABLED", "ENABLE_NETWORK_TESTS" |
            Where-Object { Test-Path -LiteralPath ("Env:" + $_) }
    ).Count -gt 0
    $paperIntegrationFlagsPresent = @(
        "PAPER_INTEGRATION_TESTS", "ENABLE_PAPER_INTEGRATION_TESTS", "ALLOW_PAPER_INTEGRATION" |
            Where-Object { Test-Path -LiteralPath ("Env:" + $_) }
    ).Count -gt 0
    Write-Output "APP_PROFILE_is_paper=$($env:APP_PROFILE -eq 'paper')"
    Write-Output "APP_PROFILE_is_live=$($env:APP_PROFILE -eq 'live')"
    Write-Output "credential_variables_present=$credentialVariablesPresent"
    Write-Output "network_test_flags_present=$networkTestFlagsPresent"
    Write-Output "paper_integration_flags_present=$paperIntegrationFlagsPresent"
    Write-Output "live_endpoint_indicator_present=$([bool]($env:ALPACA_LIVE_BASE_URL -or $env:APCA_API_BASE_URL -match 'api\.alpaca\.markets'))"
} finally {
    Pop-Location
}
