#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa',
 [string]$Pattern='*skuldafnworld*.dds',
 [ValidateRange(1,10)][int]$Count=3
)
$ErrorActionPreference='Stop'
$discovery=Join-Path $Root 'tools\bootstraps\Find-Smelter-SkyrimAssets.ps1'
$extractor=Join-Path $Root 'tools\bootstraps\Export-Smelter-SkyrimDDS.ps1'
foreach($script in @($discovery,$extractor)){if(-not (Test-Path -LiteralPath $script -PathType Leaf)){throw "Missing script: $script"}}
$runId=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$out=Join-Path $Root ('workspace\skyrim-pipeline\'+$runId)
New-Item -ItemType Directory -Path $out -Force | Out-Null
$discoveryRoot=Join-Path $out 'discovery'
& $discovery -Root $discoveryRoot -GamePath $GamePath -Archive $Archive -Pattern $Pattern -Limit $Count
if($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Discovery failed with exit code $LASTEXITCODE"}
$discoveryReports=@(Get-ChildItem -LiteralPath (Join-Path $discoveryRoot 'workspace\skyrim-discovery') -Filter 'discovery-result.json' -Recurse -File)
if($discoveryReports.Count -ne 1){throw "Expected one discovery report, found $($discoveryReports.Count)"}
$found=Get-Content -LiteralPath $discoveryReports[0].FullName -Raw | ConvertFrom-Json
$results=New-Object 'System.Collections.Generic.List[object]'
$selected=@($found.matches | Where-Object {$_.within_archive -eq $true -and $_.asset.EndsWith('.dds',[StringComparison]::OrdinalIgnoreCase)} | Select-Object -First $Count)
foreach($entry in $selected){
 $index=$results.Count+1
 $itemRoot=Join-Path $out ('asset-'+$index)
 $status='failed';$reason=$null;$output=$null;$sha=$null;$bytes=0
 try{
  & $extractor -Root $itemRoot -GamePath $GamePath -Archive $Archive -AssetPath $entry.asset
  if($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0){throw "Extractor returned exit code $LASTEXITCODE"}
  $reports=@(Get-ChildItem -LiteralPath (Join-Path $itemRoot 'workspace\skyrim-extraction') -Filter 'extraction-result.json' -Recurse -File)
  if($reports.Count -ne 1){throw "Expected one extraction report, found $($reports.Count)"}
  $result=Get-Content -LiteralPath $reports[0].FullName -Raw | ConvertFrom-Json
  if(-not $result.extracted -or $result.asset -ne $entry.asset){throw 'Extraction report asset mismatch'}
  if(-not (Test-Path -LiteralPath $result.output -PathType Leaf)){throw 'Extracted file missing'}
  $output=$result.output
  $bytes=(Get-Item -LiteralPath $output).Length
  $sha=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
  if($sha -ne $result.sha256 -or $bytes -ne $result.decoded_bytes){throw 'Output hash/size mismatch'}
  $stream=[IO.File]::OpenRead($output)
  try{$signature=New-Object byte[] 4;[void]$stream.Read($signature,0,4)}finally{$stream.Dispose()}
  if([Text.Encoding]::ASCII.GetString($signature) -ne 'DDS '){throw 'DDS signature mismatch'}
  $status='passed'
 }catch{$reason=$_.Exception.Message}
 $results.Add([pscustomobject]@{asset=$entry.asset;status=$status;reason=$reason;output=$output;sha256=$sha;decoded_bytes=$bytes})
 Write-Host "$status : $($entry.asset)"
}
$passed=@($results | Where-Object status -eq 'passed').Count
$summary=[ordered]@{
 archive=$Archive;pattern=$Pattern;requested=$Count;discovered_total=$found.total_matches
 selected=$selected.Count;passed=$passed;failed=($results.Count-$passed)
 read_only_source=$true;game_modified=$false;results=@($results.ToArray())
 note='Read-only discovery and DDS extraction with output hash, length and magic verification. In-game rendering not tested.'
}
$summaryPath=Join-Path $out 'pipeline-result.json'
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
Write-Host "Pipeline passed: $passed/$($results.Count)"
Write-Host "Report: $summaryPath"
if($selected.Count -ne $Count -or $passed -ne $Count){exit 2}
