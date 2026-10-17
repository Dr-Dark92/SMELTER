#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER',[int]$TimeoutSeconds=240)
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$dir=Join-Path $Root "workspace\gpu-tests\$stamp"
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$log=Join-Path $dir 'run.log'
Start-Transcript -Path $log | Out-Null
try {
 $profilePath=Join-Path $Root 'workspace\gpu-profiles\active.json'
 if(-not(Test-Path $profilePath)){throw 'Active GPU profile missing'}
 $profile=Get-Content $profilePath -Raw | ConvertFrom-Json
 if($profile.profile -ne 'Fast' -or $profile.model -ne 'qwen3.5:9b'){throw "Expected Fast qwen3.5:9b; found $($profile.profile) $($profile.model)"}
 $smi=(Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
 if(-not $smi){$smi='C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe'}
 if(-not(Test-Path $smi)){throw 'nvidia-smi missing'}
 function Read-Gpu {
  $lines=@(& $smi '--query-gpu=name,memory.total,memory.used,power.limit,temperature.gpu' '--format=csv,noheader,nounits' 2>&1)
  if($LASTEXITCODE -ne 0){throw "nvidia-smi failed: $($lines -join ' ')"}
  $rows=@($lines | Where-Object {$_ -match '^NVIDIA '})
  if($rows.Count -ne 1){throw "Expected one NVIDIA GPU, found $($rows.Count)"}
  $values=@($rows[0].Split(',') | ForEach-Object {$_.Trim()})
  return $values
 }
 $gpu=Read-Gpu
 if($gpu[0] -notmatch 'RTX 5080'){throw "Unexpected GPU: $($gpu[0])"}
 $culture=[Globalization.CultureInfo]::InvariantCulture
 $power=[double]::Parse($gpu[3],$culture)
 if([Math]::Abs($power-270) -gt 1){throw "Power limit $power W is not 270 W. Refusing GPU load test. Reapply Fast profile first."}
 Write-Host "PASS: GPU power limit $power W"
 $total=[int]$gpu[1]
 $budget=[int][Math]::Floor($total*0.75)
 $before=[int]$gpu[2]
 Write-Host "VRAM before: $before / $total MiB; budget $budget MiB"
 if($before -ge $budget){throw 'VRAM already exceeds budget. Close other GPU workloads before testing.'}
 # Do not kill a running Ollama server or interrupt other sessions.
 # The new environment settings only apply when the server is restarted by its owner.
 $env:OLLAMA_MAX_LOADED_MODELS='1'
 $env:OLLAMA_NUM_PARALLEL='1'
 $env:OLLAMA_CONTEXT_LENGTH='8192'
 $models=@(& ollama.exe list 2>&1)
 if($LASTEXITCODE -ne 0 -or -not (@($models | Where-Object {$_ -match '^qwen3\.5:9b\s'}).Count -gt 0)){throw 'qwen3.5:9b missing'}
 $payload=@{model='qwen3.5:9b';prompt='Reply with exactly SMELTER_GPU_READY';stream=$false;think=$false;options=@{num_predict=128;num_ctx=8192}} | ConvertTo-Json -Depth 6
 Write-Host 'Running real local Qwen 9B inference...'
 $job=Start-Job -ScriptBlock {
  param($body,$timeout)
  Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/generate' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec $timeout
 } -ArgumentList $payload,$TimeoutSeconds
 $peak=$before
 $peakTemp=[int]$gpu[4]
 try {
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  while($job.State -eq 'Running'){
   if((Get-Date) -gt $deadline){Stop-Job $job;throw "Inference timed out after $TimeoutSeconds seconds"}
   Start-Sleep -Seconds 2
   $reading=Read-Gpu
   $used=[int]$reading[2]
   $temp=[int]$reading[4]
   if($used -gt $peak){$peak=$used}
   if($temp -gt $peakTemp){$peakTemp=$temp}
   Write-Host "GPU: $used MiB, $temp C"
   if($used -gt $budget){Stop-Job $job;throw "VRAM soft budget exceeded: $used > $budget MiB. Inference job stopped; Ollama may retain model in VRAM."}
   if($temp -ge 80){Stop-Job $job;throw "GPU temperature reached $temp C. Inference job stopped."}
  }
  if($job.State -ne 'Completed'){throw "Inference job state: $($job.State). $($job.ChildJobs[0].JobStateInfo.Reason)"}
  $reply=Receive-Job $job -ErrorAction Stop
 } finally {Remove-Job $job -Force -ErrorAction SilentlyContinue}
 if([string]::IsNullOrWhiteSpace([string]$reply.response)){throw "Empty model response. done_reason=$($reply.done_reason)"}
 Write-Host "Model response: $($reply.response)"
 $gpu=Read-Gpu
 $used=[int]$gpu[2]
 if($used -gt $peak){$peak=$used}
 if($used -gt $budget){throw "VRAM budget exceeded after inference: $used MiB"}
 Write-Host "PASS: Qwen 9B inference; peak observed VRAM $peak MiB / $budget MiB budget; peak temperature $peakTemp C"
 $report=[ordered]@{model=$profile.model;power_limit_watts=$power;vram_total_mib=$total;vram_budget_mib=$budget;vram_peak_observed_mib=$peak;temperature_peak_observed_c=$peakTemp;response=[string]$reply.response;timestamp=(Get-Date).ToString('o');note='2-second sampling can miss short spikes. Ollama environment changes require restarting the server to apply.'}
 $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $dir 'result.json') -Encoding UTF8
 Write-Host "Report: $(Join-Path $dir 'result.json')"
 Write-Warning 'Existing Ollama server was not restarted; its concurrency and default context settings may still be the previous values.'
} finally {Stop-Transcript | Out-Null}
