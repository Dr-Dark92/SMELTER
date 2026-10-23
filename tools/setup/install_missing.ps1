<#
.SYNOPSIS
  Install the SMELTER tools that the requirements scan reports as missing.

.DESCRIPTION
  Reads system-requirements.json at the repository root, runs the read-only
  requirements scanner, and installs each missing tool that declares a
  "winget" package ID or a version-pinned "npm" package. Shows the exact plan
  and asks before installing. Agreements are not auto-accepted: winget and
  each installer show their own prompts. Run from an administrator
  PowerShell so WSL and Docker Desktop can install.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1 -DryRun
#>
param(
    [string[]]$Only,
    [switch]$DryRun,
    [switch]$Yes,
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$catalog = Get-Content (Join-Path $root 'system-requirements.json') -Raw | ConvertFrom-Json

function Find-Python {
    if ($Python) { return $Python }
    foreach ($name in 'python', 'py') {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notlike '*\WindowsApps\*') { return $cmd.Source }
    }
    $found = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($found) { return $found.FullName }
    throw 'Python 3.12+ was not found. Pass -Python C:\path\to\python.exe'
}

function Get-Scan($python) {
    $json = & $python (Join-Path $root 'tools\setup\check_requirements.py') --json
    if ($LASTEXITCODE -ne 0 -and -not $json) { throw 'Requirements scan failed.' }
    return ($json | Out-String | ConvertFrom-Json)
}

$python = Find-Python
$scan = Get-Scan $python
$status = @{}
foreach ($t in $scan.tools) { $status[$t.name] = $t.status }

# Build the plan from the requirements file: one entry per package, so tools
# sharing a package (java and javac) install once.
$plan = [ordered]@{}
$manual = @()
foreach ($prop in $catalog.tools.PSObject.Properties) {
    $name = $prop.Name; $tool = $prop.Value
    if ($Only -and $Only -notcontains $name) { continue }
    if ($status[$name] -eq 'installed') { continue }
    if ($tool.winget) { $key = "winget:$($tool.winget)" }
    elseif ($tool.npm) { $key = "npm:$($tool.npm)" }
    else { $manual += $name; continue }
    if (-not $plan.Contains($key)) { $plan[$key] = @() }
    $plan[$key] += $name
}

Write-Host "SMELTER missing tools (from system-requirements.json)" -ForegroundColor Cyan
if ($plan.Count -eq 0) { Write-Host 'Nothing to install.' }
foreach ($key in $plan.Keys) {
    $kind, $package = $key -split ':', 2
    if ($kind -eq 'winget') { $cmd = "winget install --id $package --exact --source winget" }
    else { $cmd = "npm install --global --allow-scripts=$($package -replace '@[^@]+$','') $package" }
    Write-Host ("  {0,-14} {1}" -f ($plan[$key] -join ','), $cmd)
}
foreach ($name in $manual) { Write-Host ("  {0,-14} manual: {1}" -f $name, $catalog.tools.$name.manual) -ForegroundColor Yellow }
if ($DryRun -or $plan.Count -eq 0) { exit 0 }

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Host 'Not running as administrator: WSL and Docker Desktop may fail or ask for elevation.' -ForegroundColor Yellow }
if (-not $Yes) {
    $answer = Read-Host 'Install these now? Type yes to continue'
    if ($answer -ne 'yes') { Write-Host 'Cancelled. Nothing was installed.'; exit 1 }
}

$results = @()
foreach ($key in $plan.Keys) {
    $kind, $package = $key -split ':', 2
    $names = $plan[$key] -join ','
    Write-Host "`n==> $names ($package)" -ForegroundColor Cyan
    if ($kind -eq 'winget') {
        & winget install --id $package --exact --source winget
    } else {
        $npm = Get-Command npm -ErrorAction SilentlyContinue
        if (-not $npm) { $results += [pscustomobject]@{Tool=$names; Result='skipped: npm not found (install Node.js first)'}; continue }
        & npm install --global "--allow-scripts=$($package -replace '@[^@]+$','')" $package
    }
    # 0x8A15002B (-1978335189): winget found it already installed, nothing to upgrade.
    if ($LASTEXITCODE -eq 0) { $r = 'installed' }
    elseif ($LASTEXITCODE -eq -1978335189) { $r = 'already installed' }
    else { $r = "failed (exit $LASTEXITCODE)" }
    $results += [pscustomobject]@{Tool=$names; Result=$r}
}

Write-Host "`nSummary" -ForegroundColor Cyan
$results | Format-Table -AutoSize | Out-String | Write-Host
Write-Host 'Restart Windows after installing WSL, then start Docker Desktop once and accept its terms.'
Write-Host 'Open a new PowerShell window and re-run the scan so PATH changes are picked up:'
Write-Host "  & `"$python`" tools\setup\check_requirements.py"
if ($results | Where-Object { $_.Result -like 'failed*' }) { exit 1 }
