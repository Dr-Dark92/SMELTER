#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER',[int]$TimeoutSeconds=180)
$ErrorActionPreference='Stop'
$logs=Join-Path $Root 'workspace\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$log=Join-Path $logs "inference-$stamp.log"
Start-Transcript -Path $log | Out-Null
try {
 $prefix=(& npm.cmd config get prefix).Trim()
 if($LASTEXITCODE -ne 0){throw 'npm prefix unavailable'}
 $openCode=Join-Path $prefix 'opencode.cmd'
 if(-not(Test-Path $openCode)){throw "OpenCode executable missing: $openCode"}
 $config=Join-Path $Root 'opencode.json'
 if(-not(Test-Path $config)){throw "Project config missing: $config"}
 $cfg=Get-Content $config -Raw | ConvertFrom-Json
 if($cfg.model -ne 'ollama/qwen3.5:4b'){throw "Unexpected model: $($cfg.model)"}
 $uri='http://127.0.0.1:11434/api/generate'
 $payload=@{model='qwen3.5:4b';prompt='Reply with exactly: SMELTER_READY';stream=$false;options=@{num_predict=48}} | ConvertTo-Json -Depth 6
 Write-Host 'Testing local Ollama inference...'
 try {
  $reply=Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $payload -TimeoutSec $TimeoutSeconds
 } catch {throw "Ollama inference failed: $($_.Exception.Message)"}
 if([string]::IsNullOrWhiteSpace([string]$reply.response)){throw 'Ollama returned empty response'}
 Write-Host "Ollama response: $($reply.response)"
 Write-Host 'PASS: Ollama produced a nonempty response'
 # Test OpenCode in a temporary directory so no project-specific files are created.
 $testDir=Join-Path $env:TEMP ('smelter-opencode-test-'+[guid]::NewGuid().ToString('N'))
 New-Item -ItemType Directory -Force -Path $testDir | Out-Null
 $stdout=Join-Path $logs "opencode-$stamp.stdout.log"
 $stderr=Join-Path $logs "opencode-$stamp.stderr.log"
 try {
  Write-Host 'Testing OpenCode local model invocation...'
  $env:OPENCODE_CONFIG=$config
  $args=@('run','--model','ollama/qwen3.5:4b','Reply with exactly SMELTER_READY. Do not use tools.')
  $proc=Start-Process -FilePath $openCode -ArgumentList $args -WorkingDirectory $testDir -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  if(-not $proc.WaitForExit($TimeoutSeconds*1000)){
   try{$proc.Kill()}catch{}
   throw "OpenCode timed out after $TimeoutSeconds seconds"
  }
  $proc.Refresh()
  $out=if(Test-Path $stdout){Get-Content $stdout -Raw}else{''}
  $err=if(Test-Path $stderr){Get-Content $stderr -Raw}else{''}
  Write-Host "OpenCode exit code: $($proc.ExitCode)"
  Write-Host "OpenCode stdout: $out"
  if($err){Write-Host "OpenCode stderr: $err"}
  if($proc.ExitCode -ne 0){throw 'OpenCode inference returned nonzero exit code'}
  if([string]::IsNullOrWhiteSpace($out)){throw 'OpenCode inference returned empty stdout'}
  Write-Host 'PASS: OpenCode produced a nonempty response using local model'
 } finally {
  Remove-Item -LiteralPath $testDir -Force -Recurse -ErrorAction SilentlyContinue
 }
 Write-Host 'PASS: Local inference smoke test complete'
 Write-Host "Log: $log"
} finally {Stop-Transcript | Out-Null}
