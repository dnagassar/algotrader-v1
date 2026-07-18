<#
.SYNOPSIS
Runs one exact V5.30 bounded Alpaca-paper lifecycle.

.DESCRIPTION
This sealed shell requires explicit paper-mutation and network switches, an
immutable plan, and a path to a separately operator-created exact grant.
The planner's authorization request artifact is never accepted as a grant. The
shell passes the bounded authorization over stdin and prints boolean-only
state and never prints credentials, account identifiers, or the
authorization text. It is not invoked by default tests or offline pipelines.
#>

[CmdletBinding()]
param(
    [switch]$PaperMutationAuthorized,
    [switch]$AllowNetwork,
    [string]$Plan = "",
    [string]$GrantedAuthorizationPath = "",
    [string]$OutputRoot = "runs\crypto_strategy_tournament\v2\bounded_paper_probe_lifecycle",
    [string]$JournalPath = "runs\crypto_strategy_tournament\v2\bounded_paper_probe_lifecycle\lifecycle_orders.sqlite3",
    [string]$SafetyStatePath = "runs\crypto_strategy_tournament\v2\bounded_paper_probe_lifecycle\bounded_probe_safety.sqlite3"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DefaultPaperBaseUrl = "https://paper-api.alpaca.markets"

$CredentialVariableNames = @(
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY"
)
$ExpectedAccountVariableNames = @(
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID"
)
$EndpointVariableNames = @(
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL"
)
$NetworkTestVariableNames = @(
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS"
)

function Get-ProcessValue {
    param([string]$Name)
    return [Environment]::GetEnvironmentVariable($Name, "Process")
}

function Test-Loaded {
    param([string]$Name)
    return -not [string]::IsNullOrWhiteSpace((Get-ProcessValue $Name))
}

function Format-Bool {
    param([bool]$Value)
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

function Get-FirstLoadedValue {
    param([string[]]$Names)
    foreach ($Name in $Names) {
        $Value = Get-ProcessValue $Name
        if (-not [string]::IsNullOrWhiteSpace($Value)) {
            return $Value
        }
    }
    return ""
}

$OperatorGrantRoot = Join-Path (
    [Environment]::GetFolderPath(
        [System.Environment+SpecialFolder]::LocalApplicationData
    )
) "algo_trader\operator_grants"

function Resolve-ExternalOperatorGrant {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ""
    }
    try {
        $LexicalPath = [System.IO.Path]::GetFullPath($Path)
        if (
            -not (Test-PathUnderRoot $LexicalPath $OperatorGrantRoot) -or
            (Test-PathUnderRoot $LexicalPath $RepoRoot) -or
            -not (Test-ReparsePointFreePath $OperatorGrantRoot) -or
            -not (Test-ReparsePointFreePath $LexicalPath) -or
            -not (Test-Path -LiteralPath $LexicalPath -PathType Leaf)
        ) {
            return ""
        }
        $Info = Get-Item -LiteralPath $LexicalPath -Force
        if (
            $Info.PSIsContainer -or
            $Info.Name -ieq "authorization_request.txt" -or
            $Info.Length -le 0 -or
            $Info.Length -gt 4096
        ) {
            return ""
        }
        $ResolvedPath = (Resolve-Path -LiteralPath $LexicalPath).Path
        if (
            -not (Test-PathUnderRoot $ResolvedPath $OperatorGrantRoot) -or
            (Test-PathUnderRoot $ResolvedPath $RepoRoot)
        ) {
            return ""
        }
        return $ResolvedPath
    }
    catch {
        return ""
    }
}

$AppProfile = Get-ProcessValue "APP_PROFILE"
$AppProfileIsPaper = $AppProfile -eq "paper"
$AppProfileIsLive = $AppProfile -eq "live"
$ApiKeyPresent = (
    (Test-Loaded "ALPACA_API_KEY") -or
    (Test-Loaded "APCA_API_KEY_ID")
)
$SecretPresent = (
    (Test-Loaded "ALPACA_SECRET_KEY") -or
    (Test-Loaded "ALPACA_API_SECRET_KEY") -or
    (Test-Loaded "APCA_API_SECRET_KEY")
)
$PaperCredentialsPresent = $ApiKeyPresent -and $SecretPresent

$EffectiveExpectedAccountId = Get-FirstLoadedValue $ExpectedAccountVariableNames
$ExpectedAccountLoaded = -not [string]::IsNullOrWhiteSpace(
    $EffectiveExpectedAccountId
)

$PaperEndpointExact = $true
$LiveEndpointIndicator = $AppProfileIsLive
foreach ($Name in $EndpointVariableNames) {
    $Value = Get-ProcessValue $Name
    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        $Normalized = $Value.TrimEnd("/").ToLowerInvariant()
        if ($Normalized -ne $DefaultPaperBaseUrl) {
            $PaperEndpointExact = $false
        }
        if (
            $Normalized.Contains("api.alpaca.markets") -and
            -not $Normalized.Contains("paper")
        ) {
            $LiveEndpointIndicator = $true
        }
    }
}

$NetworkTestFlagEnabled = $false
foreach ($Name in $NetworkTestVariableNames) {
    $Value = Get-ProcessValue $Name
    if (
        -not [string]::IsNullOrWhiteSpace($Value) -and
        $Value.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
    ) {
        $NetworkTestFlagEnabled = $true
    }
}
$PytestAddopts = Get-ProcessValue "PYTEST_ADDOPTS"
if (
    -not [string]::IsNullOrWhiteSpace($PytestAddopts) -and
    $PytestAddopts.Contains("--allow-network")
) {
    $NetworkTestFlagEnabled = $true
}

$PlanProvided = -not [string]::IsNullOrWhiteSpace($Plan)
$PlanExists = $PlanProvided -and (
    Test-Path -LiteralPath $Plan -PathType Leaf
)
$AuthorizationPathProvided = -not [string]::IsNullOrWhiteSpace(
    $GrantedAuthorizationPath
)
$AuthorizationResolvedPath = ""
if ($AuthorizationPathProvided) {
    $AuthorizationResolvedPath = Resolve-ExternalOperatorGrant (
        $GrantedAuthorizationPath
    )
}
$AuthorizationProvided = -not [string]::IsNullOrWhiteSpace(
    $AuthorizationResolvedPath
)

Write-Host "v530_paper_mutation_authorized=$(Format-Bool $PaperMutationAuthorized.IsPresent)"
Write-Host "v530_network_authorized=$(Format-Bool $AllowNetwork.IsPresent)"
Write-Host "v530_plan_provided=$(Format-Bool $PlanProvided)"
Write-Host "v530_plan_exists=$(Format-Bool $PlanExists)"
Write-Host "v530_exact_operation_authorization_provided=$(Format-Bool $AuthorizationProvided)"
Write-Host "preflight_APP_PROFILE_is_paper=$(Format-Bool $AppProfileIsPaper)"
Write-Host "preflight_APP_PROFILE_is_live=$(Format-Bool $AppProfileIsLive)"
foreach ($Name in $CredentialVariableNames) {
    Write-Host "preflight_$($Name)_present=$(Format-Bool (Test-Loaded $Name))"
}
Write-Host "preflight_paper_credentials_present=$(Format-Bool $PaperCredentialsPresent)"
Write-Host "preflight_expected_paper_account_id_loaded=$(Format-Bool $ExpectedAccountLoaded)"
Write-Host "preflight_paper_endpoint_exact_match_indicator=$(Format-Bool $PaperEndpointExact)"
Write-Host "preflight_live_endpoint_indicator=$(Format-Bool $LiveEndpointIndicator)"
Write-Host "preflight_network_test_flag_enabled=$(Format-Bool $NetworkTestFlagEnabled)"
Write-Host "credential_values_exposed=false"
Write-Host "live_endpoint_touched=false"

$StopReasons = [System.Collections.Generic.List[string]]::new()
if (-not $PaperMutationAuthorized.IsPresent) {
    $StopReasons.Add("paper_mutation_switch_required")
}
if (-not $AllowNetwork.IsPresent) {
    $StopReasons.Add("network_switch_required")
}
if (-not $PlanExists) {
    $StopReasons.Add("existing_plan_required")
}
if (-not $AuthorizationProvided) {
    $StopReasons.Add("exact_operation_authorization_required")
}
if (-not $AppProfileIsPaper) {
    $StopReasons.Add("paper_profile_required")
}
if ($AppProfileIsLive) {
    $StopReasons.Add("live_profile_forbidden")
}
if (-not $PaperCredentialsPresent) {
    $StopReasons.Add("paper_credentials_required")
}
if (-not $ExpectedAccountLoaded) {
    $StopReasons.Add("expected_paper_account_required")
}
if (-not $PaperEndpointExact) {
    $StopReasons.Add("exact_paper_endpoint_required")
}
if ($LiveEndpointIndicator) {
    $StopReasons.Add("live_endpoint_forbidden")
}
if ($NetworkTestFlagEnabled) {
    $StopReasons.Add("network_test_flag_forbidden")
}
if ($StopReasons.Count -gt 0) {
    Write-Host "v530_stop_reasons=$($StopReasons -join ',')"
    exit 2
}

try {
    $TrustedPythonPath = Resolve-TrustedPythonExecutable
}
catch {
    Write-Host "v530_stop_reasons=trusted_python_required"
    exit 2
}

$StrictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
try {
    $AuthorizationText = [System.IO.File]::ReadAllText(
        $AuthorizationResolvedPath,
        $StrictUtf8
    ).Trim()
}
catch {
    Write-Host "v530_stop_reasons=exact_operation_authorization_required"
    exit 2
}
if (
    [string]::IsNullOrWhiteSpace($AuthorizationText) -or
    $AuthorizationText.Contains([char]0) -or
    $StrictUtf8.GetByteCount($AuthorizationText) -gt 4096
) {
    $AuthorizationText = $null
    Write-Host "v530_stop_reasons=exact_operation_authorization_required"
    exit 2
}

$CliArgs = @(
    "-I",
    "-m",
    "algotrader.execution.crypto_tournament_v2_bounded_paper_probe_lifecycle_operator",
    "--plan",
    $Plan,
    "--output-root",
    $OutputRoot,
    "--journal-path",
    $JournalPath,
    "--safety-state-path",
    $SafetyStatePath,
    "--exact-operation-authorization-stdin",
    "--paper-mutation-authorized",
    "--allow-network"
)

$ProcessInfo = [System.Diagnostics.ProcessStartInfo]::new()
$ProcessInfo.FileName = $TrustedPythonPath
$ProcessInfo.WorkingDirectory = $RepoRoot
$ProcessInfo.UseShellExecute = $false
$ProcessInfo.RedirectStandardInput = $true
$ProcessInfo.RedirectStandardOutput = $true
$ProcessInfo.RedirectStandardError = $true
$ProcessInfo.StandardInputEncoding = [System.Text.UTF8Encoding]::new($false)
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
foreach ($Argument in $CliArgs) {
    [void]$ProcessInfo.ArgumentList.Add([string]$Argument)
}

$Process = [System.Diagnostics.Process]::new()
$Process.StartInfo = $ProcessInfo
try {
    if (-not $Process.Start()) {
        throw "Unable to start lifecycle operator."
    }
    $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
    $StderrTask = $Process.StandardError.ReadToEndAsync()
    $Process.StandardInput.Write($AuthorizationText)
    $Process.StandardInput.Close()
    $AuthorizationText = $null
    $Process.WaitForExit()
    [System.Threading.Tasks.Task]::WaitAll(
        [System.Threading.Tasks.Task[]]@($StdoutTask, $StderrTask)
    )
    $ChildStdout = $StdoutTask.Result
    $ChildStderr = $StderrTask.Result
    if (-not [string]::IsNullOrEmpty($ChildStdout)) {
        [Console]::Out.Write($ChildStdout)
    }
    if (-not [string]::IsNullOrEmpty($ChildStderr)) {
        [Console]::Error.Write($ChildStderr)
    }
    $ExitCode = $Process.ExitCode
}
finally {
    $AuthorizationText = $null
    $Process.Dispose()
}
exit $ExitCode
