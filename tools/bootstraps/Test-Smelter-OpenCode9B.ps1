#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER',[int]$TimeoutSeconds=240)
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$dir=Join-Path $Root "workspace\gpu-tests\opencode-$stamp"
New-Item -ItemType Directory -Path $dir -Force | Out-Null
Start-Transcript -Path (Join-Path $dir 'run.log') | Out-Null
try {
 $profile=Get-Content (Join-Path $Root 'workspace\gpu-profiles\active.json') -Raw | ConvertFrom-Json
 if($profile.profile -ne 'Fast' -or $profile.model -ne 'qwen3.5:9b'){throw 'Fast 9B profile not active'}
 $cfgPath=Join-Path $Root 'opencode.json'
 $cfg=Get-Content $cfgPath -Raw | ConvertFrom-Json
 if($cfg.model -ne 'ollama/qwen3.5:9b'){throw "OpenCode default model is $($cfg.model), not 9B"}
 $prefix=(& npm.cmd config get prefix).Trim()
 if($LASTEXITCODE -ne 0){throw 'npm prefix lookup failed'}
 $opencode=Join-Path $prefix 'opencode.cmd'
 if(-not(Test-Path $opencode)){throw 'OpenCode executable missing'}
 $smi=(Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
 if(-not $smi){$smi='C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe'}
 if(-not(Test-Path $smi)){throw 'nvidia-smi unavailable'}
 function Sample-Gpu {
  $raw=@(& $smi '--query-gpu=name,memory.total,memory.used,power.limit,temperature.gpu' '--format=csv,noheader,nounits' 2>&1)
  if($LASTEXITCODE -ne 0){throw 'GPU telemetry unavailable'}
  $lines=@($raw | Where-Object {$_ -match '^NVIDIA '})
  if($lines.Count -ne 1){throw 'Expected exactly one NVIDIA GPU'}
  return @($lines[0].Split(',') | ForEach-Object {$_.Trim()})
 }
 $g=Sample-Gpu
 if($g[0] -notmatch 'RTX 5080'){throw 'Unexpected GPU'}
 $watts=[double]::Parse($g[3],[Globalization.CultureInfo]::InvariantCulture)
 if([Math]::Abs($watts-270) -gt 1){throw "GPU power limit is $watts W, not 270 W"}
 $budget=[int][Math]::Floor(([int]$g[1])*0.75)
 $peak=[int]$g[2]
 $tempPeak=[int]$g[4]
 if($peak -gt $budget){throw 'GPU already exceeds VRAM budget'}
 $stdout=Join-Path $dir 'stdout.txt'
 $stderr=Join-Path $dir 'stderr.txt'
 $temp=Join-Path $env:TEMP ('smelter-ai-'+[guid]::NewGuid().ToString('N'))
 New-Item -ItemType Directory -Path $temp -Force | Out-Null
 $oldConfig=$env:OPENCODE_CONFIG
 try {
  $env:OPENCODE_CONFIG=$cfgPath
  $arguments=@('run','--model','ollama/qwen3.5:9b','Reply with exactly SMELTER_OPENCODE_9B_READY. Do not use tools.')
  Write-Host 'Running OpenCode with local Qwen 9B...'
  $p=Start-Process -FilePath $opencode -ArgumentList $arguments -WorkingDirectory $temp -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  while(-not $p.HasExited){
   if((Get-Date) -gt $deadline){try{$p.Kill()}catch{};throw 'OpenCode inference timed out'}
   Start-Sleep -Seconds 2
   $g=Sample-Gpu
   $used=[int]$g[2];$temperature=[int]$g[4]
   if($used -gt $peak){$peak=$used}
   if($temperature -gt $tempPeak){$tempPeak=$temperature}
   Write-Host "GPU: $used MiB, $temperature C"
   if($used -gt $budget){try{$p.Kill()}catch{};throw "VRAM budget exceeded: $used > $budget MiB"}
   if($temperature -ge 80){try{$p.Kill()}catch{};throw "Temperature threshold reached: $temperature C"}
  }
  $p.WaitForExit()
  $exit=$p.ExitCode
  $out=if(Test-Path $stdout){Get-Content $stdout -Raw}else{''}
  $err=if(Test-Path $stderr){Get-Content $stderr -Raw}else{''}
  Write-Host "OpenCode exit: $exit"
  Write-Host "OpenCode stdout: $out"
  Write-Host "OpenCode stderr: $err"
  if($null -eq $exit -or $exit -ne 0){throw "OpenCode process failed: $exit"}
  if($out -notmatch 'SMELTER_OPENCODE_9B_READY'){throw 'OpenCode response did not contain expected marker'}
  $g=Sample-Gpu
  if([int]$g[2] -gt $peak){$peak=[int]$g[2]}
  if($peak -gt $budget){throw "VRAM budget exceeded: $peak MiB"}
  $result=[ordered]@{model='qwen3.5:9b';power_limit_watts=$watts;vram_peak_observed_mib=$peak;vram_budget_mib=$budget;temperature_peak_observed_c=$tempPeak;opencode_exit_code=$exit;timestamp=(Get-Date).ToString('o')}
  $result | ConvertTo-Json | Set-Content (Join-Path $dir 'result.json') -Encoding UTF8
  Write-Host "PASS: OpenCode 9B local inference; peak VRAM $peak MiB; peak temperature $tempPeak C"
  Write-Host "Report: $(Join-Path $dir 'result.json')"
 } finally {
  $env:OPENCODE_CONFIG=$oldConfig
  try{if([IO.Directory]::Exists($temp)){[IO.Directory]::Delete($temp,$true)}}catch{Write-Warning "Temp cleanup skipped: $($_.Exception.Message)"}
 }
} finally {Stop-Transcript | Out-Null}
