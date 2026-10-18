# Launch SMELTER Vanilla V1's local web installer (PowerShell 5.1+).
[CmdletBinding()]
param([int]$Port = 8767)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$setup = Join-Path $root 'tools\setup\setup_web.py'
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $setup --port $Port
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $setup --port $Port
} else {
    throw 'Python 3.12+ required before launching SMELTER setup.'
}
if ($LASTEXITCODE -ne 0) { throw "SMELTER setup exited with code $LASTEXITCODE" }
