#Requires -Version 5.1
[CmdletBinding()]
param([switch]$SkipModels)
$ErrorActionPreference='Stop'
$npm=Get-Command npm.cmd -ErrorAction SilentlyContinue
if(-not $npm){throw 'npm.cmd not found. Reopen PowerShell after Node.js installation.'}
& npm.cmd install --global rea-agents opencode-ai
if($LASTEXITCODE -ne 0){throw 'npm install failed.'}
if(-not $SkipModels){
 $ollama=Get-Command ollama.exe -ErrorAction SilentlyContinue
 if(-not $ollama){Write-Warning 'Ollama missing from PATH; reopen PowerShell and retry.'}
 else{
  & ollama.exe pull qwen3.5:4b
  if($LASTEXITCODE -ne 0){Write-Warning 'Model download failed. Retry: ollama pull qwen3.5:4b'}
 }
}
Write-Host 'Next: run Configure-Smelter.ps1 and rea setup; configure OpenCode for local Ollama.'
