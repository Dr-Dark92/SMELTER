#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$out=Join-Path $Root "workspace\integrations\opencode-adapter-$stamp"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$originalConfig=$env:OPENCODE_CONFIG
$originalCwd=(Get-Location).Path
$source=Join-Path $Root 'opencode.json'
if(-not(Test-Path -LiteralPath $source)){throw "Missing $source"}
Copy-Item -LiteralPath $source -Destination (Join-Path $out 'original-opencode.json')
$base=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
$exe=Get-Command opencode.cmd -ErrorAction SilentlyContinue
if(-not $exe){$exe=Get-Command opencode -ErrorAction Stop}
$results=@()
try{
 Set-Location $Root
 foreach($adapter in @('@ai-sdk/openai-compatible','@ai-sdk/openai')){
  $tag=if($adapter -eq '@ai-sdk/openai'){'openai'}else{'compatible'}
  $config=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
  $config.provider.ollama.npm=$adapter
  $configFile=Join-Path $out "$tag-config.json"
  $config | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $configFile -Encoding UTF8
  $env:OPENCODE_CONFIG=$configFile
  $resolvedPath=Join-Path $out "$tag-resolved.json"
  $resolvedText=(& $exe.Source debug config 2>&1 | Out-String)
  $resolvedText | Set-Content -LiteralPath $resolvedPath -Encoding UTF8
  $resolvedAdapter=''
  try{$resolvedAdapter=([regex]::Match($resolvedText,'"npm"\s*:\s*"([^"]+)"')).Groups[1].Value}catch{}
  if($resolvedAdapter -ne $adapter){
   $results+= [pscustomobject]@{adapter=$adapter;status='CONFIG_NOT_APPLIED';tool_event=$false;details="Resolved adapter: $resolvedAdapter"}
   continue
  }
  $eventsFile=Join-Path $out "$tag-events.jsonl"
  $stderrFile=Join-Path $out "$tag-stderr.log"
  $prompt='Use the OpenCode read tool to read README.md and quote the first heading exactly. Do not guess or print a command.'
  $args=@('run','--format','json','-m','ollama/qwen3.5:9b',$prompt)
  $raw=@(& $exe.Source @args 2>&1 | ForEach-Object { $_.ToString() })
  $raw | Set-Content -LiteralPath $eventsFile -Encoding UTF8
  $toolEvents=@()
  foreach($line in $raw){
   try{
    $evt=$line | ConvertFrom-Json -ErrorAction Stop
    if($evt.type -match 'tool' -or ($evt.part -and $evt.part.type -eq 'tool')){$toolEvents+= $evt}
   }catch{}
  }
  $toolEvents | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $out "$tag-tool-events.json") -Encoding UTF8
  $results+= [pscustomobject]@{adapter=$adapter;status=if($toolEvents.Count){'TOOL_EVENT_SEEN'}else{'NO_TOOL_EVENT'};tool_event=($toolEvents.Count -gt 0);details="Captured $($raw.Count) output lines; $($toolEvents.Count) tool events"}
 }
}finally{
 $env:OPENCODE_CONFIG=$originalConfig
 Set-Location $originalCwd
}
$results | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'summary.json') -Encoding UTF8
$results | Format-Table -AutoSize
Write-Host "Diagnostic artifacts: $out"
Write-Host 'Original opencode.json was not modified. Inspect logs for secrets before sharing.'
