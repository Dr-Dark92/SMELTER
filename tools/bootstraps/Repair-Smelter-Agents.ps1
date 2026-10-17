#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER',[switch]$SkipModelDownload)
$ErrorActionPreference='Stop'
$logDir=Join-Path $Root 'workspace\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log=Join-Path $logDir ("agent-repair-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
Start-Transcript -Path $log | Out-Null
try {
 Write-Host 'SMELTER agent installation and verification'
 $npm=Get-Command npm.cmd -ErrorAction SilentlyContinue
 if(-not $npm){throw 'npm.cmd is missing. Install Node.js and rerun the prerequisites script.'}
 $prefix=(& npm.cmd config get prefix).Trim()
 if($LASTEXITCODE -ne 0 -or -not (Test-Path $prefix)){throw "Invalid npm prefix: $prefix"}
 $env:Path="$prefix;$env:Path"
 $userPath=[Environment]::GetEnvironmentVariable('Path','User')
 if(($userPath -split ';') -notcontains $prefix){
  $newUserPath=(@($userPath -split ';' | Where-Object { $_ }) + $prefix) -join ';'
  [Environment]::SetEnvironmentVariable('Path',$newUserPath,'User')
 }
 & npm.cmd install --global rea-agents opencode-ai
 if($LASTEXITCODE -ne 0){throw "npm agent installation failed: $LASTEXITCODE"}
 foreach($name in @('rea','opencode')){
  $exe=Join-Path $prefix "$name.cmd"
  if(-not (Test-Path $exe)){throw "Expected agent missing: $exe"}
  & $exe --version
  if($LASTEXITCODE -ne 0){throw "$name version check failed"}
 }
 $ghidra=Join-Path $env:SystemDrive 'Tools\Ghidra'
 if(Test-Path (Join-Path $ghidra 'support\analyzeHeadless.bat')){
  [Environment]::SetEnvironmentVariable('GHIDRA_INSTALL_DIR',$ghidra,'User')
  $env:GHIDRA_INSTALL_DIR=$ghidra
  Write-Host "Ghidra detected: $ghidra"
 }else{Write-Warning 'Ghidra not detected at C:\Tools\Ghidra; REA Ghidra integration needs configuration.'}
 if(-not $SkipModelDownload){
  $ollama=Get-Command ollama.exe -ErrorAction SilentlyContinue
  if($ollama){
   & ollama.exe pull qwen3.5:4b
   if($LASTEXITCODE -ne 0){throw 'Ollama model download failed'}
  }else{Write-Warning 'Ollama missing from PATH; model download skipped.'}
 }
 Write-Host "Agent stage complete. Log: $log"
 Write-Host 'REA setup and OpenCode provider selection require separate integration verification.'
} finally {Stop-Transcript | Out-Null}
