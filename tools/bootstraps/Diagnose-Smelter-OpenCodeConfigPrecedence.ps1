#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$out=Join-Path $Root "workspace\integrations\opencode-adapter-isolated-$stamp"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$source=Join-Path $Root 'opencode.json'
if(!(Test-Path -LiteralPath $source)){throw "Missing $source"}
$exe=Get-Command opencode.cmd -ErrorAction SilentlyContinue
if(!$exe){$exe=Get-Command opencode -ErrorAction Stop}
$prior=(Get-Location).Path
$old=$env:OPENCODE_CONFIG
$results=@()
try {
 Set-Location $Root
 foreach($adapter in @('@ai-sdk/openai-compatible','@ai-sdk/openai')){
  $tag=if($adapter -eq '@ai-sdk/openai'){'openai'}else{'compatible'}
  $cfg=Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
  $cfg.provider.ollama.npm=$adapter
  $configPath=Join-Path $out "$tag-config.json"
  $cfg | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $configPath -Encoding UTF8
  $env:OPENCODE_CONFIG=$configPath
  $resolved=(& $exe.Source debug config 2>&1 | Out-String)
  $resolved | Set-Content -LiteralPath (Join-Path $out "$tag-resolved.json") -Encoding UTF8
  $actual=''
  try{$actual=(([regex]::Match($resolved,'"npm"\s*:\s*"([^"]+)"')).Groups[1].Value)}catch{}
  $results+= [pscustomobject]@{adapter=$adapter;resolved=$actual;status=if($actual -eq $adapter){'OVERRIDE_APPLIED'}else{'OVERRIDE_NOT_APPLIED'}}
 }
}finally{
 $env:OPENCODE_CONFIG=$old
 Set-Location $prior
}
$results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'summary.json') -Encoding UTF8
$results | Format-Table -AutoSize
Write-Host "Output: $out"
Write-Host 'No project configuration was modified.'
