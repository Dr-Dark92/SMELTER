# SMELTER Vanilla V1 setup (Windows PowerShell 5.1+)
# No admin rights, downloads, optional tool installation, or global pip modifications.
[CmdletBinding()]
param(
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

$py = Get-Command py -ErrorAction SilentlyContinue
$python = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    $base = @('py', '-3')
} elseif ($python) {
    $base = @('python')
} else {
    throw 'Python 3.12+ not found. Install Python first, then rerun setup.'
}

$version = & $base[0] @($base[1..($base.Count - 1)] | Where-Object { $_ }) -c 'import sys; print(".".join(map(str,sys.version_info[:3])))'
if ($LASTEXITCODE -ne 0 -or -not $version) { throw 'Unable to query Python version.' }
$parts = $version.Trim().Split('.')
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 12)) {
    throw "Python $version is below the minimum supported 3.12."
}

$venv = Join-Path $root '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating isolated Python environment using $version..."
    if ($base.Count -eq 2) { & $base[0] $base[1] -m venv $venv }
    else { & $base[0] -m venv $venv }
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create virtual environment.' }
}
Write-Host 'Checking declared Python dependencies...'
# requirements.txt intentionally contains comments only for Vanilla V1.
# Do not invoke pip until there are actual third-party requirements to install.
$requirements = Join-Path $root 'requirements.txt'
if (-not (Test-Path $requirements)) { throw 'requirements.txt is missing.' }
$packages = @(Get-Content $requirements | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })
if ($packages.Count -gt 0) {
    Write-Host 'Third-party requirements found. Review requirements.txt before installation.'
    throw 'Automatic dependency installation is disabled in this Vanilla bootstrap.'
}

Write-Host 'Running read-only requirements scanner...'
& $venvPython (Join-Path $root 'tools\setup\check_requirements.py')
if ($LASTEXITCODE -ne 0) { throw 'Requirements scan failed.' }
if (-not $SkipTests) {
    Write-Host 'Running setup unit tests...'
    & $venvPython -m unittest discover -s (Join-Path $root 'tools\setup') -p 'test_check_requirements.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Setup tests failed.' }
}
Write-Host 'SMELTER Vanilla bootstrap completed. Optional tools were not installed.'
