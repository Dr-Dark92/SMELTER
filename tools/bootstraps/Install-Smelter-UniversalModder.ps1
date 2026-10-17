#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER',[string]$Ref='main',[switch]$Refresh)
$ErrorActionPreference='Stop'
$repo='https://github.com/rehan-remade/universal-modder.git'
$base=Join-Path $Root 'tools\third-party'
$target=Join-Path $base 'universal-modder'
$reportDir=Join-Path $Root 'workspace\integrations'
New-Item -ItemType Directory -Force -Path $base,$reportDir | Out-Null
if(-not (Get-Command git -ErrorAction SilentlyContinue)){throw 'Git not found'}
if(-not (Test-Path -LiteralPath (Join-Path $Root '.git'))){throw "SMELTER checkout missing: $Root"}
if(-not (Test-Path -LiteralPath $target)){
 & git clone --filter=blob:none --no-checkout -- $repo $target
 if($LASTEXITCODE -ne 0){throw 'Clone failed'}
}else{
 if(-not (Test-Path -LiteralPath (Join-Path $target '.git'))){throw 'Existing integration directory is not a Git checkout; refusing overwrite'}
 $remote=(& git -C $target remote get-url origin 2>$null)
 if($LASTEXITCODE -ne 0 -or ($remote -ne $repo -and $remote -ne 'https://github.com/rehan-remade/universal-modder')){throw "Unexpected origin: $remote"}
}
if($Refresh -or -not (Test-Path -LiteralPath (Join-Path $target 'README.md'))){
 & git -C $target fetch --depth 1 origin $Ref
 if($LASTEXITCODE -ne 0){throw 'Fetch failed'}
 & git -C $target checkout --detach FETCH_HEAD
 if($LASTEXITCODE -ne 0){throw 'Checkout failed'}
}
$sha=(& git -C $target rev-parse HEAD).Trim()
$skills=Join-Path $target 'skills'
$expected=@('mod-any-game','game-recon','reverse-engineering','asset-pipeline','game-automation','mashup-mods','publish-mod')
$found=@();$missing=@()
foreach($name in $expected){
 if(Test-Path -LiteralPath (Join-Path (Join-Path $skills $name) 'SKILL.md')){$found+= $name}else{$missing+= $name}
}
$report=[ordered]@{
 source=$repo;commit=$sha;location=$target
 skills_present=$found;skills_missing=$missing
 local_ai_policy='No fal MCP, cloud credentials, plugin hooks or external agent configuration installed'
 scope='Read-only source checkout; no execution of upstream scripts; no changes to game directories'
 note='SMELTER bootstrap integrates upstream sources for inspection. Skills are not automatically registered with OpenCode/Codex.'
}
$reportPath=Join-Path $reportDir 'universal-modder.json'
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Universal Modder checkout: $target"
Write-Host "Pinned commit: $sha"
Write-Host "Skills found: $($found.Count)/$($expected.Count)"
Write-Host "Report: $reportPath"
if($missing.Count){throw "Missing skills: $($missing -join ', ')"}
