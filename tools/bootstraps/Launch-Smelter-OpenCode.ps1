#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $Root
$prefixOutput=@(& npm.cmd config get prefix 2>&1)
if($LASTEXITCODE -ne 0){throw "Cannot determine npm global prefix: $($prefixOutput -join ' ')"}
$prefix=([string]($prefixOutput | Select-Object -Last 1)).Trim()
$exe=Join-Path $prefix 'opencode.cmd'
if(-not (Test-Path -LiteralPath $exe)){throw "OpenCode is not installed at expected path: $exe"}
Write-Host "Launching OpenCode from: $exe"
# Run the installed executable directly; no PATH modification is necessary.
& $exe
if($LASTEXITCODE -ne 0){throw "OpenCode exited with code $LASTEXITCODE"}
