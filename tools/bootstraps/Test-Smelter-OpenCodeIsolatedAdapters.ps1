#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$out=Join-Path $Root "workspace\integrations\opencode-isolated-$stamp"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$source=Join-Path $Root 'opencode.json'
if(!(Test-Path -LiteralPath $source)){throw "Missing $source"}
$exe=Get-Command opencode.cmd -ErrorAction SilentlyContinue
if(!$exe){$exe=Get-Command opencode -ErrorAction Stop}
$prior=(Get-Location).Path
$old=$env:OPENCODE_CONFIG
$results=@()
try{
 Remove-Item Env:\OPENCODE_CONFIG -ErrorAction SilentlyContinue
 foreach($adapter in @('@ai-sdk/openai-compatible','@ai-sdk/openai')){
  $tag=if($adapter -eq '@ai-sdk/openai'){'openai'}else{'compatible'}
  $dir=Join-Path $out $tag
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  '# SMELTER' | Set-Content -LiteralPath (Join-Path $dir 'README.md') -Encoding UTF8
  $cfg=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
  $cfg.provider.ollama.npm=$adapter
  $cfg | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $dir 'opencode.json') -Encoding UTF8
  Set-Location $dir
  $resolved=(& $exe.Source debug config 2>&1 | Out-String)
  $resolved | Set-Content -LiteralPath (Join-Path $dir 'resolved.json') -Encoding UTF8
  $actual=([regex]::Match($resolved,'"npm"\s*:\s*"([^"]+)"')).Groups[1].Value
  if($actual -ne $adapter){
   $results+= [pscustomobject]@{adapter=$adapter;resolved=$actual;status='NOT_APPLIED';tool_event=$false}
   continue
  }
  $prompt='Use the read tool to read README.md and report its first heading exactly. Do not guess or print a command.'
  $raw=@(& $exe.Source run --format json -m ollama/qwen3.5:9b $prompt 2>&1 | ForEach-Object {$_.ToString()})
  $raw | Set-Content -LiteralPath (Join-Path $dir 'events.jsonl') -Encoding UTF8
  $tools=@()
  foreach($line in $raw){
   try{
    $evt=$line | ConvertFrom-Json -ErrorAction Stop
    if($evt.type -match 'tool' -or ($evt.part -and $evt.part.type -eq 'tool')){$tools+= $evt}
   }catch{}
  }
  $tools | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $dir 'tool-events.json') -Encoding UTF8
  $results+= [pscustomobject]@{adapter=$adapter;resolved=$actual;status=if($tools.Count){'TOOL_EVENT_SEEN'}else{'NO_TOOL_EVENT'};tool_event=($tools.Count -gt 0)}
 }
}finally{
 if($null -eq $old){Remove-Item Env:\OPENCODE_CONFIG -ErrorAction SilentlyContinue}else{$env:OPENCODE_CONFIG=$old}
 Set-Location $prior
}
$results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'summary.json') -Encoding UTF8
$results | Format-Table -AutoSize
Write-Host "Output: $out"
Write-Host 'Original project config untouched. Inspect logs for secrets before sharing.'
