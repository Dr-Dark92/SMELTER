#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Request='Find three Skuldafn DDS textures and extract and verify them',
 [string]$Model='qwen3.5:9b',
 [ValidateRange(30,600)][int]$TimeoutSeconds=180
)
$ErrorActionPreference='Stop'
$endpoint='http://127.0.0.1:11434/api/chat'
if($Model -notin @('qwen3.5:9b','qwen3.5:4b')){throw 'Model not allowed'}
if([string]::IsNullOrWhiteSpace($Request) -or $Request.Length -gt 2000){throw 'Request length invalid'}
$tools=@(
 @{type='function';function=@{name='discover_assets';description='Find matching DDS assets in a Skyrim BSA';parameters=@{type='object';properties=@{archive=@{type='string'};pattern=@{type='string'};limit=@{type='integer'}};required=@('archive','pattern','limit')}}},
 @{type='function';function=@{name='extract_asset';description='Extract a specific DDS texture from Skyrim BSA';parameters=@{type='object';properties=@{archive=@{type='string'};asset_path=@{type='string'}};required=@('archive','asset_path')}}},
 @{type='function';function=@{name='run_asset_pipeline';description='Find, extract and verify several DDS textures';parameters=@{type='object';properties=@{archive=@{type='string'};pattern=@{type='string'};count=@{type='integer'}};required=@('archive','pattern','count')}}}
)
$payload=@{model=$Model;stream=$false;think=$false;tools=$tools;messages=@(
 @{role='system';content='You select exactly one SMELTER tool. For Skyrim textures default archive Skyrim - Textures6.bsa, search pattern *skuldafnworld*.dds and count 3. Only choose provided tools. Never output shell commands.'},
 @{role='user';content=$Request}
)}
$id=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$out=Join-Path $Root ('workspace\local-ai\'+$id)
New-Item -ItemType Directory -Path $out -Force | Out-Null
$report=[ordered]@{request=$Request;model=$Model;endpoint=$endpoint;status='not_started';tool=$null;arguments=$null;exit_code=$null;error=$null;output_root=$out}
$reportPath=Join-Path $out 'controller-result.json'
try{
 $body=$payload | ConvertTo-Json -Depth 16 -Compress
 $response=Invoke-RestMethod -Uri $endpoint -Method Post -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec $TimeoutSeconds
 $calls=@($response.message.tool_calls | Where-Object {$null -ne $_})
 if($calls.Count -ne 1){throw "Expected one structured tool call; got $($calls.Count). No tool executed."}
 $call=$calls[0];$name=[string]$call.function.name
 if($name -notin @('discover_assets','extract_asset','run_asset_pipeline')){throw 'Tool not allowlisted'}
 $a=$call.function.arguments
 if($a -is [string]){$a=$a | ConvertFrom-Json}
 if($null -eq $a){throw 'Tool arguments missing'}
 $keys=@($a.PSObject.Properties.Name)
 if($a -is [System.Collections.IDictionary]){$keys=@($a.Keys)}
 $required=switch($name){'discover_assets'{@('archive','pattern','limit')};'extract_asset'{@('archive','asset_path')};'run_asset_pipeline'{@('archive','pattern','count')}}
 foreach($key in $required){if($key -notin $keys){throw "Missing argument $key"}}
 foreach($key in $keys){if($key -notin $required){throw "Unexpected argument $key"}}
 $archive=[string]$a.archive
 if($archive -ne [IO.Path]::GetFileName($archive) -or $archive -match '[:\\/]' -or -not $archive.EndsWith('.bsa',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid archive'}
 if(-not (Test-Path -LiteralPath (Join-Path (Join-Path $GamePath 'Data') $archive) -PathType Leaf)){throw 'Archive not installed'}
 $params=@{Root=$out;GamePath=$GamePath;Archive=$archive}
 if($name -eq 'extract_asset'){
  $asset=([string]$a.asset_path).Replace('/','\')
  if($asset.Length -lt 5 -or $asset.Length -gt 260 -or $asset.StartsWith('\') -or $asset.Contains(':') -or $asset -match '(^|\\)\.\.?($|\\)' -or -not $asset.EndsWith('.dds',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid DDS asset path'}
  $params.AssetPath=$asset
  $tool=Join-Path $Root 'tools\bootstraps\Export-Smelter-SkyrimDDS.ps1'
 }else{
  $pattern=[string]$a.pattern
  if($pattern.Length -lt 5 -or $pattern.Length -gt 160 -or $pattern.Contains(':') -or $pattern.Contains('/') -or $pattern -match '(^|\\)\.\.?($|\\)' -or -not $pattern.EndsWith('.dds',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid DDS pattern'}
  $params.Pattern=$pattern
  if($name -eq 'discover_assets'){
   $n=0;if(-not [int]::TryParse([string]$a.limit,[ref]$n) -or $n -lt 1 -or $n -gt 30){throw 'Limit outside 1-30'}
   $params.Limit=$n;$tool=Join-Path $Root 'tools\bootstraps\Find-Smelter-SkyrimAssets.ps1'
  }else{
   $n=0;if(-not [int]::TryParse([string]$a.count,[ref]$n) -or $n -lt 1 -or $n -gt 3){throw 'Count outside 1-3'}
   $params.Count=$n;$tool=Join-Path $Root 'tools\bootstraps\Invoke-Smelter-SkyrimAssetPipeline.ps1'
  }
 }
 if(-not (Test-Path -LiteralPath $tool -PathType Leaf)){throw 'Approved script missing'}
 $report.tool=$name;$report.arguments=$params;$report.status='executing'
 $report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
 $argsList=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$tool+'"'))
 foreach($key in @($params.Keys | Sort-Object)){$argsList+=('-'+$key);$argsList+=('"'+([string]$params[$key]).Replace('"','')+'"')}
 $stdout=Join-Path $out 'tool-stdout.log';$stderr=Join-Path $out 'tool-stderr.log'
 $process=Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $argsList -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 if(-not $process.WaitForExit($TimeoutSeconds*1000)){try{$process.Kill()}catch{};throw 'Tool timed out'}
 $process.Refresh();$report.exit_code=$process.ExitCode
 if($process.ExitCode -ne 0){throw "Tool failed with exit code $($process.ExitCode). See tool-stderr.log"}
 $report.status='passed'
 Write-Host "Local AI selected: $name"
 Write-Host 'Execution: PASS'
 Write-Host "Artifacts: $out"
}catch{$report.status='failed';$report.error=$_.Exception.Message;Write-Host "Controller stopped: $($report.error)"}
finally{$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8;Write-Host "Audit: $reportPath"}
if($report.status -ne 'passed'){exit 2}
