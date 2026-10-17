#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
$logDir=Join-Path $Root 'workspace\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log=Join-Path $logDir ("integration-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
Start-Transcript -Path $log | Out-Null
try {
 $npmPrefix=(& npm.cmd config get prefix).Trim()
 if($LASTEXITCODE -ne 0){throw 'npm prefix lookup failed'}
 $rea=Join-Path $npmPrefix 'rea.cmd'
 $opencode=Join-Path $npmPrefix 'opencode.cmd'
 if(-not (Test-Path $rea)){throw "REA missing: $rea"}
 if(-not (Test-Path $opencode)){throw "OpenCode missing: $opencode"}
 $ghidra=[Environment]::GetEnvironmentVariable('GHIDRA_INSTALL_DIR','User')
 if(-not $ghidra){$ghidra='C:\Tools\Ghidra'}
 if(-not (Test-Path (Join-Path $ghidra 'support\analyzeHeadless.bat'))){throw "Ghidra headless missing: $ghidra"}
 $jdk=Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory -ErrorAction SilentlyContinue |
  Where-Object Name -match '^jdk-21' | Sort-Object Name -Descending | Select-Object -First 1
 if(-not $jdk){throw 'JDK 21 missing'}
 $env:JAVA_HOME=$jdk.FullName
 $env:Path=(Join-Path $jdk.FullName 'bin')+';'+$npmPrefix+';'+$env:Path
 $env:GHIDRA_INSTALL_DIR=$ghidra
 $env:REA_ANALYSIS_PROVIDER='ghidra'
 [Environment]::SetEnvironmentVariable('GHIDRA_INSTALL_DIR',$ghidra,'User')
 [Environment]::SetEnvironmentVariable('REA_ANALYSIS_PROVIDER','ghidra','User')
 $configPath=Join-Path $Root 'opencode.json'
 if(Test-Path $configPath){
  $raw=Get-Content -LiteralPath $configPath -Raw
  $config=ConvertFrom-Json -InputObject $raw
  if(-not $config){throw 'Existing OpenCode config cannot be parsed'}
  Copy-Item $configPath ($configPath+'.smelter-backup-'+(Get-Date -Format 'yyyyMMddHHmmss'))
 } else {$config=[pscustomobject]@{}}
 if(-not ($config.PSObject.Properties.Name -contains 'provider')){
  $config | Add-Member -NotePropertyName provider -NotePropertyValue ([pscustomobject]@{})
 }
 if($config.provider.PSObject.Properties.Name -contains 'ollama'){
  Write-Host 'Existing Ollama provider preserved'
 }else{
  $provider=[pscustomobject]@{
   npm='@ai-sdk/openai-compatible'
   name='Ollama (local)'
   options=[pscustomobject]@{baseURL='http://127.0.0.1:11434/v1'}
   models=[pscustomobject]@{'qwen3.5:4b'=[pscustomobject]@{name='Qwen 3.5 4B (local)'}}
  }
  $config.provider | Add-Member -NotePropertyName ollama -NotePropertyValue $provider
 }
 if(-not ($config.PSObject.Properties.Name -contains 'model')){
  $config | Add-Member -NotePropertyName model -NotePropertyValue 'ollama/qwen3.5:4b'
 }
 if(-not ($config.PSObject.Properties.Name -contains '$schema')){
  $config | Add-Member -NotePropertyName '$schema' -NotePropertyValue 'https://opencode.ai/config.json'
 }
 $json=ConvertTo-Json $config -Depth 30
 $tmp=$configPath+'.tmp'
 [System.IO.File]::WriteAllText($tmp,$json,(New-Object System.Text.UTF8Encoding($false)))
 Move-Item -LiteralPath $tmp -Destination $configPath -Force
 Write-Host 'OpenCode project-local Ollama config written'
 & $rea setup --client opencode --yes --json
 if($LASTEXITCODE -ne 0){throw 'REA OpenCode registration failed'}
 & $rea doctor --json
 if($LASTEXITCODE -ne 0){Write-Warning 'REA doctor reported issues'}
 & $opencode mcp list
 if($LASTEXITCODE -ne 0){Write-Warning 'OpenCode MCP list failed'}
 $models=& ollama.exe list
 Write-Host $models
 if($models -notmatch 'qwen3\.5:4b'){throw 'Local qwen3.5:4b model not found'}
 Write-Host "Integration stage finished. Log: $log"
} finally {Stop-Transcript | Out-Null}
