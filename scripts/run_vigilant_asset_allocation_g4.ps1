[CmdletBinding()]
param([string]$OutputRoot="runs\v5_74_vigilant_asset_allocation_g4\evaluation",[ValidateSet("text","json")][string]$Format="text")
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$UnsafeNames=@("ALPACA_API_KEY","ALPACA_API_SECRET","APCA_API_KEY_ID","APCA_API_SECRET_KEY","TIINGO_API_KEY","TIINGO_API_TOKEN","NEXUSTRADE_ACCESS_TOKEN","NEXUSTRADE_REFRESH_TOKEN")
$Unsafe=[System.Environment]::GetEnvironmentVariable("APP_PROFILE","Process") -eq "paper"
foreach($Name in $UnsafeNames){if(-not [string]::IsNullOrWhiteSpace([System.Environment]::GetEnvironmentVariable($Name,"Process"))){$Unsafe=$true}}
if($Unsafe){[Console]::Error.WriteLine("vigilant_asset_allocation_g4_status=blocked_unsafe_environment");exit 2}
$RepoRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$OriginalPythonPath=[System.Environment]::GetEnvironmentVariable("PYTHONPATH","Process")
Push-Location -LiteralPath $RepoRoot
try{$Parts=@(Join-Path $RepoRoot "src");if(-not [string]::IsNullOrWhiteSpace($OriginalPythonPath)){$Parts+=$OriginalPythonPath};[System.Environment]::SetEnvironmentVariable("PYTHONPATH",($Parts -join [System.IO.Path]::PathSeparator),"Process");& python -m algotrader.research.vigilant_asset_allocation_g4 --output-root $OutputRoot --format $Format;exit $LASTEXITCODE}
finally{[System.Environment]::SetEnvironmentVariable("PYTHONPATH",$OriginalPythonPath,"Process");Pop-Location}
