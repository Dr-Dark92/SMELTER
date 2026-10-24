<#
.SYNOPSIS
  Install the SMELTER tools and setup steps that are not done yet.

.DESCRIPTION
  Reads system-requirements.json at the repository root. Part 1 installs
  missing tools that declare a "winget" package ID or a version-pinned "npm"
  package. Part 2 checks each setup step (MCP SDK, Ollama model, Docker
  images, pinned npm tooling, Playwright Chromium) and runs the ones that are
  not done. Shows the exact plan and asks before changing anything.
  Agreements are not auto-accepted. Run from an administrator PowerShell so
  WSL and Docker Desktop can install.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1 -DryRun
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1 -Profile opencode_agent
#>
param(
    [string[]]$Only,
    [Alias('Profile')][string[]]$ProfileName,
    [switch]$DryRun,
    [switch]$Yes,
    [string]$Python,
    # low | medium | high | extreme | custom; default: detected from the GPU and RAM.
    [string]$HardwareProfile
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root
$catalog = Get-Content (Join-Path $root 'system-requirements.json') -Raw | ConvertFrom-Json
# Windows PowerShell 5.1 turns native stderr (winget/docker/npm progress) into
# terminating errors under 'Stop'. Native results are judged by exit code instead.
$ErrorActionPreference = 'Continue'

# Read-only probes get a timeout: a half-started Docker engine can hang
# "docker image inspect" indefinitely. Returns $null on timeout.
function Test-Native([string]$exe, [string[]]$argv, [int]$seconds = 20) {
    $info = New-Object System.Diagnostics.ProcessStartInfo $exe
    $info.Arguments = ($argv | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' }) -join ' '
    $info.UseShellExecute = $false; $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
    $proc = [System.Diagnostics.Process]::Start($info)
    $proc.StandardOutput.ReadToEndAsync() | Out-Null; $proc.StandardError.ReadToEndAsync() | Out-Null
    if (-not $proc.WaitForExit($seconds * 1000)) { try { $proc.Kill() } catch {}; return $null }
    return ($proc.ExitCode -eq 0)
}

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

# Tools installed earlier in this session may not be on this window's PATH yet.
function Find-Exe($name) {
    # Prefer npm.cmd: npm.ps1 can be blocked by the execution policy.
    $cmd = Get-Command "$name.cmd", $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { return $cmd.Source }
    $known = @{
        docker = "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe"
        ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
        node   = "$env:ProgramFiles\nodejs\node.exe"
        npm    = "$env:ProgramFiles\nodejs\npm.cmd"
    }
    if ($known.ContainsKey($name) -and (Test-Path $known[$name])) { return $known[$name] }
    return $null
}

$python = Find-Python
$selectedTools = @($catalog.tools.PSObject.Properties.Name)
$selectedSetup = @($catalog.setup.PSObject.Properties.Name)
if ($ProfileName) {
    $selectedTools = @(); $selectedSetup = @()
    foreach ($p in $ProfileName) {
        $entry = $catalog.profiles.$p
        if (-not $entry) { throw "Unknown profile '$p'. Known: $($catalog.profiles.PSObject.Properties.Name -join ', ')" }
        $selectedTools += @($entry.requires); $selectedSetup += @($entry.setup)
    }
}
if ($Only) {
    $selectedTools = @($selectedTools | Where-Object { $Only -contains $_ })
    $selectedSetup = @($selectedSetup | Where-Object { $Only -contains $_ })
}
# Keep file order so "after" dependencies (image_node before image_opencode) hold.
$selectedSetup = @($catalog.setup.PSObject.Properties.Name | Where-Object { $selectedSetup -contains $_ })

# ---- Part 1: tools ---------------------------------------------------------
$scan = (& $python (Join-Path $root 'tools\setup\check_requirements.py') --json | Out-String | ConvertFrom-Json)
$status = @{}
foreach ($t in $scan.tools) { $status[$t.name] = $t.status }

$toolPlan = [ordered]@{}
$manual = @()
foreach ($name in $selectedTools | Select-Object -Unique) {
    $tool = $catalog.tools.$name
    if ($status[$name] -eq 'installed') { continue }
    # npm shims are reported unverified rather than executed; the shim existing is enough.
    if ($status[$name] -eq 'detected_unverified' -and $tool.npm) { continue }
    if ($tool.winget) { $key = "winget:$($tool.winget)" }
    elseif ($tool.npm) { $key = "npm:$($tool.npm)" }
    else { $manual += $name; continue }
    if (-not $toolPlan.Contains($key)) { $toolPlan[$key] = @() }
    $toolPlan[$key] += $name
}

# ---- Part 2: setup steps ---------------------------------------------------
$dockerExe = Find-Exe 'docker'
$dockerUp = $false
if ($dockerExe) { $dockerUp = (Test-Native $dockerExe @('info', '--format', '{{.ServerVersion}}')) -eq $true }
$ollamaModels = $null
try { $ollamaModels = @((Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3).models | ForEach-Object { $_.name }) } catch {}
$nodeExe = Find-Exe 'node'
$npmExe = Find-Exe 'npm'

function Get-NpmName($package) { return ($package -replace '(?<=.)@[^@]+$', '') }

function Get-SetupState($id, $step) {
    switch ($step.kind) {
        'pip' {
            $v = & $python -c "from importlib.metadata import version as v; print(v('$($step.package)'))" 2>$null
            if ("$v".Trim() -eq $step.version) { return @{state='done'} }
            return @{state='todo'; argv=@($python, '-m', 'pip', 'install', '-r', $step.requirements)}
        }
        'ollama_pull' {
            if ($null -eq $ollamaModels) { return @{state='blocked'; why='Ollama is not running; start it and re-run'} }
            # "hardware": the model defaults.hardware_profiles picks for this GPU.
            if ($step.model -eq 'hardware') {
                $profileArgs = if ($HardwareProfile) { @('--profile', $HardwareProfile) } else { @() }
                $wanted = "$(& $python (Join-Path $root 'tools\setup\configure_defaults.py') --show-model @profileArgs 2>$null)".Trim()
                if (-not $wanted -and $HardwareProfile -eq 'custom') { return @{state='done'; note='custom profile: choose the model in the dashboard'} }
                if (-not $wanted) { return @{state='blocked'; why='Could not choose a model for this hardware'} }
                if ($ollamaModels -contains $wanted) { return @{state='done'; note="has $wanted (chosen for this GPU)"} }
                return @{state='todo'; argv=@((Find-Exe 'ollama'), 'pull', $wanted)}
            }
            $ok = @(@($step.model) + @($step.alternatives) | Where-Object { $ollamaModels -contains $_ })
            if ($ok.Count) { return @{state='done'; note="has $($ok[0])"} }
            return @{state='todo'; argv=@((Find-Exe 'ollama'), 'pull', $step.model)}
        }
        { $_ -in 'docker_pull', 'docker_build' } {
            if (-not $dockerExe) { return @{state='blocked'; why='Docker is not installed'} }
            if (-not $dockerUp) { return @{state='blocked'; why='Docker engine is not running; start Docker Desktop and re-run'} }
            $present = Test-Native $dockerExe @('image', 'inspect', $step.image)
            if ($null -eq $present) { return @{state='blocked'; why='Docker did not answer within 20 s; wait for Docker Desktop to finish starting'} }
            if ($present) { return @{state='done'} }
            if ($step.kind -eq 'docker_pull') { return @{state='todo'; argv=@($dockerExe, 'pull', $step.image)} }
            return @{state='todo'; argv=@($dockerExe, 'build', '-f', $step.dockerfile, '-t', $step.image, '.')}
        }
        'npm_prefix' {
            if (-not $npmExe) { return @{state='blocked'; why='npm is not installed (install Node.js first)'} }
            $name = Get-NpmName $step.package
            $manifest = Join-Path $root "$($step.prefix)\node_modules\$name\package.json"
            $want = $step.package.Substring($name.Length + 1)
            if ((Test-Path $manifest) -and ((Get-Content $manifest -Raw | ConvertFrom-Json).version -eq $want)) { return @{state='done'} }
            return @{state='todo'; argv=@($npmExe, 'install', '--prefix', $step.prefix, '--save-exact') + @($step.flags | Where-Object { $_ }) + @($step.package)}
        }
        'wsl_platform' {
            # wsl --status exits 0 even when WSL 2 cannot start, so read the
            # Windows feature state, firmware flag and pending restart instead.
            $vmp = Get-CimInstance Win32_OptionalFeature -Filter "Name='VirtualMachinePlatform'" -ErrorAction SilentlyContinue
            if (-not $vmp -or $vmp.InstallState -ne 1) {
                return @{state='todo'; argv=@('wsl.exe', '--install', '--no-distribution'); note='then restart Windows'}
            }
            # Once the Windows hypervisor runs, Win32_Processor reports
            # VirtualizationFirmwareEnabled as False, so only trust it without one.
            $hypervisor = (Get-CimInstance Win32_ComputerSystem).HypervisorPresent
            $firmware = @(Get-CimInstance Win32_Processor | ForEach-Object { $_.VirtualizationFirmwareEnabled })
            if (-not $hypervisor -and $firmware -contains $false) { return @{state='blocked'; why='Virtualization is off in the BIOS/UEFI; turn it on, then restart'} }
            if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') {
                return @{state='blocked'; why='Virtual Machine Platform is enabled but Windows needs a restart to activate it'}
            }
            return @{state='done'}
        }
        'powershell_script' {
            # check_path is relative to the tool's home: the user's saved env var, else default_home.
            $homes = @()
            if ($step.home_env) { $homes += [Environment]::GetEnvironmentVariable($step.home_env, 'User') }
            $homes += $step.default_home
            $found = @($homes | Where-Object { $_ } | Where-Object { Test-Path (Join-Path $_ $step.check_path) })
            if ($found.Count) { return @{state='done'; note="found in $($found[0])"} }
            $needs = @($step.needs) | Where-Object { $_ -and $status[$_] -ne 'installed' }
            if ($needs) { return @{state='blocked'; why="needs $($needs -join ', ') installed first"} }
            $shell = (Get-Command powershell -CommandType Application | Select-Object -First 1).Source
            return @{state='todo'; argv=@($shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $step.script, '-Root', $root)}
        }
        'playwright_browser' {
            if (-not $nodeExe) { return @{state='blocked'; why='Node.js is not installed'} }
            if (Get-ChildItem "$env:LOCALAPPDATA\ms-playwright\$($step.browser)-*" -Directory -ErrorAction SilentlyContinue) { return @{state='done'} }
            $cli = '.smelter/tooling/browser/node_modules/playwright/cli.js'
            return @{state='todo'; argv=@($nodeExe, $cli, 'install', $step.browser)}
        }
    }
}

$setupPlan = [ordered]@{}
$setupReport = @()
foreach ($id in $selectedSetup) {
    $step = $catalog.setup.$id
    $s = Get-SetupState $id $step
    $setupReport += [pscustomobject]@{Step=$id; State=$s.state; Detail=$(if ($s.why) { $s.why } elseif ($s.note) { $s.note } else { $step.purpose })}
    if ($s.state -eq 'todo') { $setupPlan[$id] = $s.argv }
}

# ---- Plan ------------------------------------------------------------------
Write-Host 'SMELTER install plan (from system-requirements.json)' -ForegroundColor Cyan
Write-Host 'Tools:' -ForegroundColor Cyan
if ($toolPlan.Count -eq 0) { Write-Host '  all selected tools are installed' }
foreach ($key in $toolPlan.Keys) {
    $kind, $package = $key -split ':', 2
    if ($kind -eq 'winget') { $cmd = "winget install --id $package --exact --source winget" }
    else { $cmd = "npm install --global --allow-scripts=$(Get-NpmName $package) $package" }
    Write-Host ("  {0,-16} {1}" -f ($toolPlan[$key] -join ','), $cmd)
}
foreach ($name in $manual) { Write-Host ("  {0,-16} manual: {1}" -f $name, $catalog.tools.$name.manual) -ForegroundColor Yellow }
Write-Host 'Setup steps:' -ForegroundColor Cyan
foreach ($r in $setupReport) {
    $color = @{done='Green'; todo='White'; blocked='Yellow'}[$r.State]
    $line = "  {0,-16} {1,-8} " -f $r.Step, $r.State
    if ($r.State -eq 'todo') { $line += ((@($setupPlan[$r.Step]) | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -join ' ') }
    else { $line += $r.Detail }
    Write-Host $line -ForegroundColor $color
}
# Dashboard first-run values from this machine (only used for settings never saved).
function Write-DeploymentDefaults([switch]$Preview) {
    Write-Host "`nDashboard defaults" -ForegroundColor Cyan
    $arguments = @((Join-Path $root 'tools\setup\configure_defaults.py')) + $(if ($Preview) { @('--dry-run') } else { @() }) +
        $(if ($HardwareProfile) { @('--profile', $HardwareProfile) } else { @() })
    & $python @arguments
}

if ($DryRun -or ($toolPlan.Count -eq 0 -and $setupPlan.Count -eq 0)) {
    if ($setupReport | Where-Object State -eq 'blocked') { Write-Host 'Fix the blocked items above, then run this script again.' -ForegroundColor Yellow }
    Write-DeploymentDefaults -Preview:$DryRun
    exit 0
}

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin -and $toolPlan.Count) { Write-Host 'Not running as administrator: WSL and Docker Desktop may fail or ask for elevation.' -ForegroundColor Yellow }
if (-not $Yes) {
    $answer = Read-Host 'Run this plan now? Type yes to continue'
    if ($answer -ne 'yes') { Write-Host 'Cancelled. Nothing was changed.'; exit 1 }
}

# ---- Run -------------------------------------------------------------------
$results = @()
foreach ($key in $toolPlan.Keys) {
    $kind, $package = $key -split ':', 2
    $names = $toolPlan[$key] -join ','
    Write-Host "`n==> $names ($package)" -ForegroundColor Cyan
    if ($kind -eq 'winget') {
        & winget install --id $package --exact --source winget
    } else {
        if (-not $npmExe) { $results += [pscustomobject]@{Item=$names; Result='skipped: npm not found (install Node.js first)'}; continue }
        & $npmExe install --global "--allow-scripts=$(Get-NpmName $package)" $package
    }
    # 0x8A15002B (-1978335189): winget found it already installed, nothing to upgrade.
    if ($LASTEXITCODE -eq 0) { $r = 'installed' }
    elseif ($LASTEXITCODE -eq -1978335189) { $r = 'already installed' }
    else { $r = "failed (exit $LASTEXITCODE)" }
    $results += [pscustomobject]@{Item=$names; Result=$r}
}
$failedSetup = @()
foreach ($id in $setupPlan.Keys) {
    $after = @($catalog.setup.$id.after) | Where-Object { $_ -and $failedSetup -contains $_ }
    if ($after) { $results += [pscustomobject]@{Item=$id; Result="skipped: $($after -join ',') failed"}; $failedSetup += $id; continue }
    $argv = @($setupPlan[$id])
    Write-Host "`n==> $id" -ForegroundColor Cyan
    & $argv[0] $argv[1..($argv.Count - 1)]
    if ($LASTEXITCODE -eq 0) { $r = 'done' } else { $r = "failed (exit $LASTEXITCODE)"; $failedSetup += $id }
    $results += [pscustomobject]@{Item=$id; Result=$r}
}

Write-Host "`nSummary" -ForegroundColor Cyan
$results | Format-Table -AutoSize | Out-String | Write-Host
if ($catalog.setup.image_opencode -and $dockerUp) {
    $id = & $dockerExe image inspect $catalog.setup.image_opencode.image --format '{{.Id}}' 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "OpenCode image ID for Settings > Confined execution: $id" }
}
if ($toolPlan.Count) {
    Write-Host 'Restart Windows after installing WSL, start Docker Desktop once, then open a new PowerShell window'
    Write-Host 'and run this script again to finish the setup steps that needed the new tools.'
}
Write-DeploymentDefaults
if ($results | Where-Object { $_.Result -like 'failed*' }) { exit 1 }
