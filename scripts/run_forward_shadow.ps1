[CmdletBinding()]
param(
    [ValidateSet("policy", "status", "vault")]
    [string]$Command = "status",
    [string]$Root,
    [string]$AsOf,
    [string[]]$Symbol = @(),
    [ValidateSet("json", "text")]
    [string]$Format = "text"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoSrc = Join-Path $RepoRoot "src"
$OriginalPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
$UnsafeNames = @(
    "APP_PROFILE", "ALPACA_API_KEY", "ALPACA_API_SECRET", "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY", "TIINGO_API_KEY", "TIINGO_API_TOKEN",
    "NEXUSTRADE_ACCESS_TOKEN", "NEXUSTRADE_REFRESH_TOKEN"
)
foreach ($Name in $UnsafeNames) {
    if (-not [string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($Name, "Process"))) {
        [Console]::Error.WriteLine("forward_shadow_status=blocked_unsafe_environment")
        exit 2
    }
}
if ($Command -eq "status") {
    if ([string]::IsNullOrWhiteSpace($Root) -or [string]::IsNullOrWhiteSpace($AsOf)) {
        [Console]::Error.WriteLine("forward_shadow_status=blocked_missing_root_or_as_of")
        exit 2
    }
}
# pwsh -File passes array parameters as a single string, so accept either
# repeated values or one comma-separated value and normalize both.
$Symbols = @()
foreach ($Item in $Symbol) {
    foreach ($Part in ($Item -split ",")) {
        $Trimmed = $Part.Trim()
        if (-not [string]::IsNullOrWhiteSpace($Trimmed)) {
            $Symbols += $Trimmed
        }
    }
}
if ($Command -eq "vault" -and $Symbols.Count -eq 0) {
    [Console]::Error.WriteLine("forward_shadow_status=blocked_missing_symbol")
    exit 2
}
Push-Location -LiteralPath $RepoRoot
try {
    $Parts = @($RepoSrc)
    if (-not [string]::IsNullOrWhiteSpace($OriginalPythonPath)) {
        $Parts += $OriginalPythonPath
    }
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", ($Parts -join [System.IO.Path]::PathSeparator), "Process")
    if ($Command -eq "policy") {
        & python -m algotrader.research.forward_shadow_registry policy
    }
    elseif ($Command -eq "vault") {
        $VaultArgs = @("-m", "algotrader.research.forward_shadow_vault", "--format", $Format)
        foreach ($Item in $Symbols) {
            $VaultArgs += @("--symbol", $Item)
        }
        & python @VaultArgs
    }
    else {
        & python -m algotrader.research.forward_shadow_registry status --root $Root --as-of $AsOf --format $Format
    }
    exit $LASTEXITCODE
}
finally {
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $OriginalPythonPath, "Process")
    Pop-Location
}
