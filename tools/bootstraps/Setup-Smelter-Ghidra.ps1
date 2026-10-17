#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GhidraHome='C:\Tools\Ghidra',
 [switch]$SkipDownload
)
$ErrorActionPreference='Stop'
$logDir=Join-Path $Root 'workspace\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log=Join-Path $logDir ("ghidra-setup-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
Start-Transcript -Path $log | Out-Null
try {
 $headless=Join-Path $GhidraHome 'support\analyzeHeadless.bat'
 if(-not (Test-Path $headless)){
  $candidates=@('C:\Tools','C:\Program Files',$env:USERPROFILE+'\Downloads')
  foreach($base in $candidates){
   if(-not (Test-Path $base)){continue}
   $matches=Get-ChildItem $base -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^ghidra' -and (Test-Path (Join-Path $_.FullName 'support\analyzeHeadless.bat')) }
   if($matches){$GhidraHome=$matches[0].FullName;break}
  }
  $headless=Join-Path $GhidraHome 'support\analyzeHeadless.bat'
 }
 if(-not (Test-Path $headless) -and -not $SkipDownload){
  $release=Invoke-RestMethod -Uri 'https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest' -Headers @{ 'User-Agent'='SMELTER-Setup' }
  $asset=$release.assets | Where-Object { $_.name -match '^ghidra_.*_PUBLIC_.*\.zip$' } | Select-Object -First 1
  if(-not $asset){throw 'No matching official Ghidra release ZIP found.'}
  $temp=Join-Path $env:TEMP $asset.name
  Write-Host "Downloading official Ghidra release $($release.tag_name)"
  Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $temp
  $expected=if($asset.digest -match '^sha256:([a-fA-F0-9]{64})$'){$Matches[1]}else{$null}
  if(-not $expected){throw 'Release asset has no SHA-256 digest in GitHub metadata; refusing extraction.'}
  $actual=(Get-FileHash $temp -Algorithm SHA256).Hash
  if($actual -ine $expected){throw 'Ghidra archive SHA-256 mismatch'}
  $extract=Join-Path $env:TEMP ('smelter-ghidra-'+[guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Force -Path $extract | Out-Null
  Expand-Archive -LiteralPath $temp -DestinationPath $extract
  $found=Get-ChildItem $extract -Directory | Where-Object {Test-Path (Join-Path $_.FullName 'support\analyzeHeadless.bat')} | Select-Object -First 1
  if(-not $found){throw 'Extracted Ghidra archive missing analyzeHeadless.bat'}
  New-Item -ItemType Directory -Force -Path (Split-Path $GhidraHome -Parent) | Out-Null
  if(Test-Path $GhidraHome){throw "Destination already exists: $GhidraHome; refusing overwrite"}
  Move-Item -LiteralPath $found.FullName -Destination $GhidraHome
  $headless=Join-Path $GhidraHome 'support\analyzeHeadless.bat'
 }
 if(-not (Test-Path $headless)){throw 'Ghidra not detected. Download skipped or installation failed.'}
 $jdk=Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory -ErrorAction SilentlyContinue |
  Where-Object Name -match '^jdk-21' | Sort-Object Name -Descending | Select-Object -First 1
 if(-not $jdk){throw 'Temurin JDK 21 not found. Install prerequisites first.'}
 [Environment]::SetEnvironmentVariable('JAVA_HOME',$jdk.FullName,'User')
 [Environment]::SetEnvironmentVariable('GHIDRA_INSTALL_DIR',$GhidraHome,'User')
 [Environment]::SetEnvironmentVariable('REA_ANALYSIS_PROVIDER','ghidra','User')
 $env:JAVA_HOME=$jdk.FullName
 $env:GHIDRA_INSTALL_DIR=$GhidraHome
 $env:REA_ANALYSIS_PROVIDER='ghidra'
 $env:Path=(Join-Path $jdk.FullName 'bin')+';'+$env:Path
 Write-Host "Ghidra ready: $GhidraHome"
 Write-Host "Java: $($jdk.FullName)"
 Write-Host "REA provider: ghidra"
 Write-Host "Log: $log"
} finally {Stop-Transcript | Out-Null}
