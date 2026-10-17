#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
$upstream=Join-Path $Root 'tools\third-party\universal-modder'
$source=Join-Path $upstream 'skills'
$agentRoot=Join-Path $Root '.agents\skills'
$reportDir=Join-Path $Root 'workspace\integrations'
if(-not (Test-Path -LiteralPath (Join-Path $upstream '.git'))){throw 'Universal Modder checkout missing. Run Install-Smelter-UniversalModder.ps1 first.'}
if(-not (Test-Path -LiteralPath (Join-Path $source 'mod-any-game\SKILL.md'))){throw 'Upstream skills missing'}
$names=@('mod-any-game','game-recon','reverse-engineering','asset-pipeline','game-automation','mashup-mods','publish-mod')
New-Item -ItemType Directory -Force -Path $agentRoot,$reportDir | Out-Null
$items=New-Object System.Collections.ArrayList
foreach($name in $names){
 $origin=Join-Path $source $name
 $dest=Join-Path $agentRoot ('universal-modder-'+$name)
 if(Test-Path -LiteralPath $dest){
  [void]$items.Add([pscustomobject]@{skill=$name;status='existing_not_overwritten';path=$dest})
  continue
 }
 # A directory junction keeps the upstream skill self-contained without copying its assets.
 # Junction creation uses mklink /J via cmd; no administrator privilege normally required.
 $command='mklink /J "'+$dest+'" "'+$origin+'"'
 $output= & cmd.exe /d /c $command 2>&1
 if($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $dest 'SKILL.md'))){throw "Could not link $name : $output"}
 [void]$items.Add([pscustomobject]@{skill=$name;status='linked';path=$dest})
}
$sha=(& git -C $upstream rev-parse HEAD).Trim()
$report=[ordered]@{
 upstream_commit=$sha
 linked_skill_count=@($items | Where-Object {$_.status -eq 'linked'}).Count
 existing_skill_count=@($items | Where-Object {$_.status -eq 'existing_not_overwritten'}).Count
 skills=@($items)
 policy='Only skill discovery links. No cloud MCP, fal credentials, external agent hooks, or game modifications.'
 warning='Skill documents may reference optional cloud tools; SMELTER local-only policy takes precedence. Agent discovery requires a fresh agent session.'
}
$destReport=Join-Path $reportDir 'universal-modder-agent-skills.json'
$report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $destReport -Encoding UTF8
Write-Host "Linked: $($report.linked_skill_count); existing: $($report.existing_skill_count)"
Write-Host "Report: $destReport"
