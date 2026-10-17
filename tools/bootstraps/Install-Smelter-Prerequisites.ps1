#Requires -Version 5.1
[CmdletBinding()]
param([switch]$SkipModels)
$ErrorActionPreference='Stop'
$packages=@(
 @{Name='GitHub CLI';Id='GitHub.cli'},
 @{Name='Node.js LTS';Id='OpenJS.NodeJS.LTS'},
 @{Name='Java 21';Id='EclipseAdoptium.Temurin.21.JDK'},
 @{Name='Ollama';Id='Ollama.Ollama'}
)
$winget=Get-Command winget.exe -ErrorAction SilentlyContinue
if(-not $winget){throw 'winget not found. Install Microsoft App Installer first.'}
foreach($p in $packages){
 Write-Host ("Installing or updating {0}..." -f $p.Name)
 & winget.exe install --id $p.Id --exact --source winget --accept-source-agreements --accept-package-agreements
 if($LASTEXITCODE -ne 0){Write-Warning ("Check {0}: winget exit {1}" -f $p.Name,$LASTEXITCODE)}
}
Write-Host 'Close and reopen PowerShell, then run Install-Smelter-Agents.ps1.'
