[CmdletBinding()]
param([string]$Root='C:\SMELTER',[switch]$Fetch)
$ErrorActionPreference='Stop'
if (-not (Test-Path (Join-Path $Root '.git'))) { throw "Not a Git repository: $Root" }
Push-Location $Root
try {
 if ($Fetch) { & git fetch --prune; if ($LASTEXITCODE -ne 0) { throw 'git fetch failed' } }
 $branch=(& git branch --show-current).Trim()
 $remote=(& git remote get-url origin 2>$null)
 $dirty=@(& git status --porcelain).Count -gt 0
 $upstream=(& git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>$null)
 $ahead=$null; $behind=$null
 if ($LASTEXITCODE -eq 0 -and $upstream) {
  $counts=((& git rev-list --left-right --count "HEAD...$upstream").Trim() -split '\s+')
  if ($counts.Count -eq 2) { $ahead=[int]$counts[0]; $behind=[int]$counts[1] }
 }
 $state=[ordered]@{
  timestamp=(Get-Date).ToUniversalTime().ToString('o')
  local_node=[ordered]@{path=(Resolve-Path .).Path;branch=$branch;dirty=$dirty;head=((& git rev-parse HEAD).Trim())}
  github_node=[ordered]@{remote=$remote;upstream=$upstream;reachable=($Fetch -and $LASTEXITCODE -eq 0)}
  relation=[ordered]@{ahead=$ahead;behind=$behind;push_required=($ahead -gt 0);pull_required=($behind -gt 0)}
 }
 $state | ConvertTo-Json -Depth 5
} finally { Pop-Location }
