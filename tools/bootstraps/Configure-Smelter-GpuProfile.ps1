#Requires -Version 5.1
[CmdletBinding()]
param(
 [ValidateSet('Safe','Fast','Heavy')][string]$Profile='Fast',
 [string]$Root='C:\SMELTER',
 [switch]$SkipPull
)
$ErrorActionPreference='Stop'
$logs=Join-Path $Root 'workspace\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$log=Join-Path $logs ('gpu-profile-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
Start-Transcript -Path $log | Out-Null
try {
 $smi=(Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
 if(-not $smi){
  $smi='C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe'
  if(-not(Test-Path $smi)){throw 'nvidia-smi not found; no GPU limits changed'}
 }
 function Read-Gpu {
  $lines=@(& $smi '--query-gpu=index,name,memory.total,memory.used,power.default_limit,power.min_limit,power.max_limit,power.limit,temperature.gpu' '--format=csv,noheader,nounits' 2>&1)
  if($LASTEXITCODE -ne 0){throw "NVIDIA query failed: $($lines -join ' ')"}
  $rows=@($lines | Where-Object {$_ -match '^\s*\d+\s*,'})
  if($rows.Count -ne 1){throw "Expected exactly one GPU, found $($rows.Count). Refusing ambiguous power change."}
  $fields=@(([string]$rows[0]).Split(',') | ForEach-Object {$_.Trim()})
  if($fields.Count -ne 9){throw "Unexpected NVIDIA output: $($rows[0])"}
  return $fields
 }
 $gpu=Read-Gpu
 if($gpu[1] -notmatch 'RTX 5080'){throw "Expected RTX 5080, detected $($gpu[1]); refusing power change"}
 $total=[double]::Parse($gpu[2],[Globalization.CultureInfo]::InvariantCulture)
 $default=[double]::Parse($gpu[4],[Globalization.CultureInfo]::InvariantCulture)
 $min=[double]::Parse($gpu[5],[Globalization.CultureInfo]::InvariantCulture)
 $max=[double]::Parse($gpu[6],[Globalization.CultureInfo]::InvariantCulture)
 $watts=[int][Math]::Floor($default*0.75)
 if($watts -lt $min -or $watts -gt $max){throw "75% target $watts W outside supported [$min,$max] W; no changes made"}
 Write-Host "GPU: $($gpu[1]); VRAM: $total MiB; default power: $default W; target: $watts W"
 $set=@(& $smi '-i' '0' '-pl' ([string]$watts) 2>&1)
 $setExit=$LASTEXITCODE
 Write-Host ($set -join [Environment]::NewLine)
 if($setExit -ne 0){throw "NVIDIA driver refused power limit (exit $setExit). Do not assume it is enforced. Run with appropriate privileges or use vendor-supported controls."}
 $gpu=Read-Gpu
 $actual=[double]::Parse($gpu[7],[Globalization.CultureInfo]::InvariantCulture)
 if([Math]::Abs($actual-$watts) -gt 1.0){throw "Power-limit verification failed: requested $watts W, actual $actual W"}
 Write-Host "PASS: Verified GPU power limit $actual W"
 $budget=[Math]::Floor($total*0.75)
 Write-Host "VRAM soft budget: $budget MiB (not a hardware cap)"
 $model=switch($Profile){
  Safe {'qwen3.5:4b'}
  Fast {'qwen3.5:9b'}
  Heavy {'qwen3.5:27b'}
 }
 if(-not $SkipPull){
  Write-Host "Pulling local model $model (Heavy may require significant RAM and disk space)"
  & ollama.exe pull $model
  if($LASTEXITCODE -ne 0){throw "Ollama pull failed for $model"}
 }
 $listed=@(& ollama.exe list)
 if($LASTEXITCODE -ne 0 -or -not (@($listed | Where-Object {$_ -match ('^'+[regex]::Escape($model)+'\s')}).Count -gt 0)){
  throw "Model $model not installed. Rerun without -SkipPull."
 }
 $configPath=Join-Path $Root 'opencode.json'
 if(-not(Test-Path $configPath)){throw "Missing OpenCode config: $configPath"}
 $config=Get-Content $configPath -Raw | ConvertFrom-Json
 if(-not $config.provider -or -not $config.provider.ollama){throw 'Missing local Ollama provider; refusing configuration change'}
 if(-not $config.provider.ollama.models){$config.provider.ollama | Add-Member -NotePropertyName models -NotePropertyValue ([pscustomobject]@{}) -Force}
 if(-not ($config.provider.ollama.models.PSObject.Properties.Name -contains $model)){
  $config.provider.ollama.models | Add-Member -NotePropertyName $model -NotePropertyValue ([pscustomobject]@{name="SMELTER $model local"})
 }
 $config.model='ollama/'+$model
 Copy-Item -LiteralPath $configPath -Destination ($configPath+'.backup-'+(Get-Date -Format 'yyyyMMddHHmmss'))
 $tmp=$configPath+'.tmp'
 [IO.File]::WriteAllText($tmp,($config | ConvertTo-Json -Depth 40),(New-Object Text.UTF8Encoding($false)))
 Move-Item $tmp $configPath -Force
 # These settings apply to a newly started Ollama server, not one already running.
 foreach($entry in @(@('OLLAMA_MAX_LOADED_MODELS','1'),@('OLLAMA_NUM_PARALLEL','1'),@('OLLAMA_CONTEXT_LENGTH','8192'))){
  [Environment]::SetEnvironmentVariable($entry[0],$entry[1],'User')
 }
 $profileDir=Join-Path $Root 'workspace\gpu-profiles'
 New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
 $report=[ordered]@{
  profile=$Profile;model=$model;gpu=$gpu[1];power_limit_watts=$actual;
  power_default_watts=$default;vram_total_mib=$total;vram_soft_budget_mib=$budget;
  note='VRAM budget is advisory, not enforced by Ollama. Existing Ollama server must restart for environment settings. GPU power limit may reset after reboot.'
  timestamp=(Get-Date).ToString('o')
 }
 $reportPath=Join-Path $profileDir 'active.json'
 $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
 Write-Host "PASS: $Profile profile configured with $model"
 Write-Host "Profile: $reportPath"
 Write-Warning 'VRAM is a soft budget only. Do not run large models concurrently. Restart Ollama for concurrency/context settings to take effect. GPU power limit may reset after reboot.'
 Write-Host "Log: $log"
} finally {Stop-Transcript | Out-Null}
