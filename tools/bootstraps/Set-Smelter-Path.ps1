#Requires -Version 5.1
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$machine = [Environment]::GetEnvironmentVariable('Path','Machine')
$user = [Environment]::GetEnvironmentVariable('Path','User')
$extra = @(
  (Join-Path $env:APPDATA 'npm'),
  (Join-Path $env:ProgramFiles 'nodejs'),
  (Join-Path $env:LOCALAPPDATA 'Programs\Ollama'),
  (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links')
)
$parts = @($machine -split ';') + @($user -split ';') + $extra
$seen = @{}
$valid = foreach($part in $parts) {
 $p = [Environment]::ExpandEnvironmentVariables($part.Trim().Trim('"'))
 if($p -and (Test-Path $p) -and -not $seen.ContainsKey($p.ToLowerInvariant())) {
  $seen[$p.ToLowerInvariant()] = $true
  $p
 }
}
$env:Path = $valid -join ';'
$npm = Join-Path $env:APPDATA 'npm'
if((Test-Path $npm) -and (($user -split ';') -notcontains $npm)) {
 [Environment]::SetEnvironmentVariable('Path',(($user.TrimEnd(';')+';'+$npm).TrimStart(';')),'User')
}
$jdk = Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory -ErrorAction SilentlyContinue |
 Where-Object Name -match '^jdk-21' | Sort-Object Name -Descending | Select-Object -First 1
if($jdk) {
 [Environment]::SetEnvironmentVariable('JAVA_HOME',$jdk.FullName,'User')
 $env:JAVA_HOME = $jdk.FullName
 $env:Path = (Join-Path $jdk.FullName 'bin') + ';' + $env:Path
 Write-Host "Java 21 selected for this session: $($jdk.FullName)"
} else {
 Write-Warning 'JDK 21 not detected. Check the winget installation.'
}
foreach($cmd in @('git.exe','gh.exe','node.exe','npm.cmd','java.exe','ollama.exe')) {
 $found = Get-Command $cmd -ErrorAction SilentlyContinue
 Write-Host ("{0}: {1}" -f $cmd,$(if($found){$found.Source}else{'NOT FOUND'}))
}
Write-Host 'PATH refreshed for this PowerShell process. To persist JAVA_HOME, open a new shell.'
