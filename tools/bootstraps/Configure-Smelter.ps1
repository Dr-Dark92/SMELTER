#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
Write-Host 'SMELTER environment configuration'
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$tools=@('git.exe','gh.exe','node.exe','npm.cmd','python.exe','java.exe','ollama.exe','rea.cmd','opencode.cmd')
foreach($tool in $tools) {
 $found=Get-Command $tool -ErrorAction SilentlyContinue
 Write-Host ("{0}: {1}" -f $tool,$(if($found){$found.Source}else{'NOT FOUND'}))
}
$jdk=Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory -ErrorAction SilentlyContinue |
 Where-Object Name -match '^jdk-21' | Select-Object -First 1
if($jdk) {
 [Environment]::SetEnvironmentVariable('JAVA_HOME',$jdk.FullName,'User')
 $env:JAVA_HOME=$jdk.FullName
}
$ghidra='C:\Tools\Ghidra'
if(Test-Path (Join-Path $ghidra 'support\analyzeHeadless.bat')) {
 [Environment]::SetEnvironmentVariable('GHIDRA_INSTALL_DIR',$ghidra,'User')
 $env:GHIDRA_INSTALL_DIR=$ghidra
}
[Environment]::SetEnvironmentVariable('SMELTER_HOME',$Root,'User')
[Environment]::SetEnvironmentVariable('REA_ANALYSIS_PROVIDER','ghidra','User')
Write-Host 'Configuration complete. Reopen PowerShell to load user environment variables.'
Write-Host 'Install missing tools separately and rerun this script.'
