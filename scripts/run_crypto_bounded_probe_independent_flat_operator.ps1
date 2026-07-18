<#
.SYNOPSIS
Collects one target-scoped, read-only post-exit paper flat observation.

.DESCRIPTION
This command can read the paper account, all positions, and all open orders.
It cannot submit, cancel, replace, close, liquidate, or use a live endpoint.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("BTCUSD", "ETHUSD", "SOLUSD")]
    [string]$TargetSymbol,
    [switch]$IndependentFlatReadAuthorized,
    [switch]$AllowNetwork,
    [string]$LifecyclePath = "runs\crypto_strategy_tournament\v2\bounded_paper_probe_lifecycle\latest\lifecycle_result.json",
    [string]$OutputRoot = "runs\crypto_strategy_tournament\v2\bounded_paper_probe_capabilities"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DefaultPaperBaseUrl = "https://paper-api.alpaca.markets"

function Test-Loaded([string]$Name) {
    return -not [string]::IsNullOrWhiteSpace(
        [Environment]::GetEnvironmentVariable($Name, "Process")
    )
}
function Format-Bool([bool]$Value) {
    return $Value.ToString().ToLowerInvariant()
}

function Test-PathUnderRoot {
    param(
        [string]$Path,
        [string]$Root
    )
    try {
        $FullPath = [System.IO.Path]::GetFullPath($Path)
        $FullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.IO.Path]::AltDirectorySeparatorChar
        )
        return (
            $FullPath.Equals(
                $FullRoot,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -or
            $FullPath.StartsWith(
                $FullRoot + [System.IO.Path]::DirectorySeparatorChar,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        )
    }
    catch {
        return $false
    }
}

function Test-ReparsePointFreePath {
    param([string]$Path)
    try {
        $FullPath = [System.IO.Path]::GetFullPath($Path)
        $VolumeRoot = [System.IO.Path]::GetPathRoot($FullPath)
        $RelativePath = $FullPath.Substring($VolumeRoot.Length)
        $CurrentPath = $VolumeRoot
        $Components = $RelativePath.Split(
            [System.IO.Path]::DirectorySeparatorChar,
            [System.StringSplitOptions]::RemoveEmptyEntries
        )
        foreach ($Component in $Components) {
            $CurrentPath = Join-Path $CurrentPath $Component
            if (-not (Test-Path -LiteralPath $CurrentPath)) {
                return $false
            }
            $Info = Get-Item -LiteralPath $CurrentPath -Force
            if (
                [bool](
                    $Info.Attributes -band
                    [System.IO.FileAttributes]::ReparsePoint
                )
            ) {
                return $false
            }
        }
        return $true
    }
    catch {
        return $false
    }
}

function Get-RegisteredPythonCandidates {
    $Candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($RegistryRoot in @(
        "Registry::HKEY_CURRENT_USER\Software\Python\PythonCore",
        "Registry::HKEY_LOCAL_MACHINE\Software\Python\PythonCore",
        "Registry::HKEY_LOCAL_MACHINE\Software\WOW6432Node\Python\PythonCore"
    )) {
        if (-not (Test-Path -LiteralPath $RegistryRoot)) {
            continue
        }
        foreach ($VersionKey in (
            Get-ChildItem -LiteralPath $RegistryRoot -ErrorAction SilentlyContinue
        )) {
            $InstallPathKey = Join-Path $VersionKey.PSPath "InstallPath"
            if (-not (Test-Path -LiteralPath $InstallPathKey)) {
                continue
            }
            try {
                $InstallRoot = [string](
                    Get-Item -LiteralPath $InstallPathKey
                ).GetValue("")
            }
            catch {
                continue
            }
            if (-not [string]::IsNullOrWhiteSpace($InstallRoot)) {
                $Candidates.Add((Join-Path $InstallRoot "python.exe"))
            }
        }
    }
    return $Candidates.ToArray()
}

function Resolve-TrustedPythonExecutable {
    foreach ($Candidate in (
        (Get-RegisteredPythonCandidates) |
            Sort-Object -Unique -Descending
    )) {
        try {
            $FullPath = [System.IO.Path]::GetFullPath($Candidate)
            if (
                -not [System.IO.Path]::IsPathRooted($FullPath) -or
                -not (Test-Path -LiteralPath $FullPath -PathType Leaf) -or
                -not (Test-ReparsePointFreePath $FullPath) -or
                (Test-PathUnderRoot $FullPath $RepoRoot)
            ) {
                continue
            }
            $Info = Get-Item -LiteralPath $FullPath -Force
            if ($Info.VersionInfo.ProductName -notmatch "(?i)python") {
                continue
            }
            $Signature = Get-AuthenticodeSignature -LiteralPath $FullPath
            if (
                $Signature.Status -ne "Valid" -or
                $null -eq $Signature.SignerCertificate -or
                $Signature.SignerCertificate.Subject -notlike (
                    "*Python Software Foundation*"
                )
            ) {
                continue
            }
            return $FullPath
        }
        catch {
            continue
        }
    }
    throw "A trusted registered Python executable is required."
}

$AppProfile = [Environment]::GetEnvironmentVariable(
    "APP_PROFILE", "Process"
)
$PaperUrl = [Environment]::GetEnvironmentVariable(
    "ALPACA_PAPER_BASE_URL", "Process"
)
if ([string]::IsNullOrWhiteSpace($PaperUrl)) {
    $PaperUrl = [Environment]::GetEnvironmentVariable(
        "APCA_API_BASE_URL", "Process"
    )
}
$LiveEndpoint = $AppProfile -eq "live"
if (-not [string]::IsNullOrWhiteSpace($PaperUrl)) {
    $LiveEndpoint = $LiveEndpoint -or (
        $PaperUrl.ToLowerInvariant().Contains("api.alpaca.markets") -and
        -not $PaperUrl.ToLowerInvariant().Contains("paper")
    )
}
$PaperEndpointExact = (
    -not [string]::IsNullOrWhiteSpace($PaperUrl) -and
    $PaperUrl.TrimEnd("/").ToLowerInvariant() -eq $DefaultPaperBaseUrl
)

Write-Host "crypto_bounded_probe_independent_flat_target=$TargetSymbol"
Write-Host "crypto_bounded_probe_independent_flat_read_authorized=$(Format-Bool $IndependentFlatReadAuthorized.IsPresent)"
Write-Host "crypto_bounded_probe_independent_flat_network_authorized=$(Format-Bool $AllowNetwork.IsPresent)"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool ($AppProfile -eq 'paper'))"
Write-Host "preflight_paper_endpoint_exact_match=$(Format-Bool $PaperEndpointExact)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpoint)"
foreach ($Name in @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)) {
    Write-Host "preflight_$($Name)_present=$(Format-Bool (Test-Loaded $Name))"
}
Write-Host "credential_values_exposed=false"
Write-Host "broker_mutation_occurred=false"
Write-Host "paper_mutation_occurred=false"
Write-Host "live_endpoint_touched=false"

if (
    -not $IndependentFlatReadAuthorized.IsPresent -or
    -not $AllowNetwork.IsPresent
) {
    throw (
        "Independent flat collection requires both explicit read and " +
        "network switches."
    )
}
if ($LiveEndpoint) {
    throw "Live endpoint indicators are not authorized."
}

$TrustedPythonPath = Resolve-TrustedPythonExecutable

$Arguments = @(
    "-I",
    "-m",
    "algotrader.execution.crypto_bounded_probe_independent_flat_operator",
    "--target-symbol",
    $TargetSymbol,
    "--lifecycle-path",
    $LifecyclePath,
    "--output-root",
    $OutputRoot,
    "--independent-flat-read-authorized",
    "--allow-network"
)

$ProcessInfo = [System.Diagnostics.ProcessStartInfo]::new()
$ProcessInfo.FileName = $TrustedPythonPath
$ProcessInfo.WorkingDirectory = $RepoRoot
$ProcessInfo.UseShellExecute = $false
$ProcessInfo.RedirectStandardOutput = $true
$ProcessInfo.RedirectStandardError = $true
$ProcessInfo.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ProcessInfo.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)
foreach ($Name in @(
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONINSPECT",
    "PYTHONUSERBASE",
    "PYTHONBREAKPOINT",
    "PYTHONPYCACHEPREFIX"
)) {
    [void]$ProcessInfo.Environment.Remove($Name)
}
foreach ($Argument in $Arguments) {
    [void]$ProcessInfo.ArgumentList.Add([string]$Argument)
}

$Process = [System.Diagnostics.Process]::new()
$Process.StartInfo = $ProcessInfo
try {
    if (-not $Process.Start()) {
        throw "Unable to start independent flat operator."
    }
    $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
    $StderrTask = $Process.StandardError.ReadToEndAsync()
    $Process.WaitForExit()
    [System.Threading.Tasks.Task]::WaitAll(
        [System.Threading.Tasks.Task[]]@($StdoutTask, $StderrTask)
    )
    if (-not [string]::IsNullOrEmpty($StdoutTask.Result)) {
        [Console]::Out.Write($StdoutTask.Result)
    }
    if (-not [string]::IsNullOrEmpty($StderrTask.Result)) {
        [Console]::Error.Write($StderrTask.Result)
    }
    $ExitCode = $Process.ExitCode
}
finally {
    $Process.Dispose()
}
exit $ExitCode
