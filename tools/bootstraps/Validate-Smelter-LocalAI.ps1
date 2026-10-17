#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
$logDir=Join-Path $Root 'workspace\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log=Join-Path $logDir ("local-ai-validation-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
Start-Transcript -Path $log | Out-Null
try {
 $prefix=(& npm.cmd config get prefix).Trim()
 if($LASTEXITCODE -ne 0){throw 'npm prefix lookup failed'}
 $rea=Join-Path $prefix 'rea.cmd'
 $opencode=Join-Path $prefix 'opencode.cmd'
 foreach($exe in @($rea,$opencode)){if(-not(Test-Path $exe)){throw "Missing executable: $exe"}}
 $ghidra=[Environment]::GetEnvironmentVariable('GHIDRA_INSTALL_DIR','User')
 if(-not $ghidra){$ghidra='C:\Tools\Ghidra'}
 if(-not(Test-Path (Join-Path $ghidra 'support\analyzeHeadless.bat'))){throw 'Ghidra headless launcher missing'}
 $env:GHIDRA_INSTALL_DIR=$ghidra
 $env:REA_ANALYSIS_PROVIDER='ghidra'
 $jdk=Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory -ErrorAction SilentlyContinue | Where-Object Name -match '^jdk-21' | Sort-Object Name -Descending | Select-Object -First 1
 if(-not $jdk){throw 'JDK 21 not found'}
 $env:JAVA_HOME=$jdk.FullName
 $env:Path=(Join-Path $jdk.FullName 'bin')+';'+$prefix+';'+$env:Path
 $modelRows=@(& ollama.exe list 2>&1 | ForEach-Object { [string]$_ })
 if($LASTEXITCODE -ne 0){throw 'ollama list failed'}
 $modelPresent= @($modelRows | Where-Object {$_ -match '^qwen3\.5:4b\s'}).Count -gt 0
 if(-not $modelPresent){throw 'qwen3.5:4b not found in Ollama model list'}
 Write-Host 'PASS: qwen3.5:4b installed'
 $mcpRows=@(& $opencode mcp list 2>&1 | ForEach-Object { [string]$_ })
 if($LASTEXITCODE -ne 0){throw 'OpenCode MCP listing failed'}
 if(-not (@($mcpRows | Where-Object {$_ -match 'rea connected'}).Count -gt 0)){throw 'REA not connected in OpenCode MCP list'}
 Write-Host 'PASS: OpenCode REA MCP connected'
 $doctorRaw=(& $rea doctor --json 2>&1 | Out-String)
 try{$doctor=$doctorRaw | ConvertFrom-Json}catch{throw 'REA doctor did not return valid JSON'}
 $provider=@($doctor.providerInspections | Where-Object { $_.id -eq 'ghidra' }) | Select-Object -First 1
 if(-not $provider -or -not $provider.available){throw 'REA Ghidra provider unavailable'}
 Write-Host 'PASS: REA Ghidra provider available'
 $projectConfig=Join-Path $Root 'opencode.json'
 if(-not(Test-Path $projectConfig)){throw 'Project-local OpenCode configuration missing'}
 $cfg=Get-Content $projectConfig -Raw | ConvertFrom-Json
 if(-not $cfg.provider.ollama.models.'qwen3.5:4b'){throw 'Project-local Ollama model configuration missing'}
 Write-Host 'PASS: OpenCode Ollama model configuration present'
 Write-Host 'PASS: Local AI static validation complete. Runtime inference test still required.'
 Write-Host "Log: $log"
} finally {Stop-Transcript | Out-Null}
