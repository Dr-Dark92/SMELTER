#Requires -Version 5.1
param([string]$Root='C:\SMELTER')
$ErrorActionPreference='Stop'
$d=Get-ChildItem (Join-Path $Root 'workspace\analysis') -Directory | Sort-Object Name -Descending | Where-Object {Test-Path (Join-Path $_.FullName 'function-01.json')} | Select-Object -First 1
if(-not $d){throw 'No existing function analysis'}
$m=Get-Content (Join-Path $d.FullName 'result.json') -Raw | ConvertFrom-Json
$raw=Get-Content -LiteralPath $m.source -Raw
$blocks=@{}
foreach($b in [regex]::Matches($raw,'(?ms)^===== FUNCTION ([^\r\n]+) =====\r?\n(.*?)(?=^===== FUNCTION |\z)')){
 $name=($b.Groups[1].Value.Trim() -split '\s+')[0]
 $code=$b.Groups[2].Value.Trim()
 if($code.Length -gt 14000){$code=$code.Substring(0,14000)}
 $blocks[$name]=@($code -split '\r?\n')
}
$results=New-Object System.Collections.ArrayList
foreach($f in @(Get-ChildItem $d.FullName -Filter 'function-*.json' -File)){
 $obj=Get-Content $f.FullName -Raw | ConvertFrom-Json
 $lines=$blocks[[string]$obj.name]
 if(-not $lines){throw "Source block missing: $($obj.name)"}
 foreach($o in @($obj.model_output.observations)){
  $quote=[string]$o.evidence
  $n=0;$hasNumber=[int]::TryParse([string]$o.line_number,[ref]$n)
  $matches=@(for($j=0;$j -lt $lines.Count;$j++){if($quote -ceq ([string]$lines[$j])){$j+1}})
  $trim=@(for($j=0;$j -lt $lines.Count;$j++){if($quote.Trim() -ceq ([string]$lines[$j]).Trim()){$j+1}})
  $normalized=($quote -replace '\s+',' ').Trim()
  $norm=@(for($j=0;$j -lt $lines.Count;$j++){if($normalized.Length -gt 0 -and $normalized -ceq (([string]$lines[$j] -replace '\s+',' ').Trim())){$j+1}})
  $status=if($hasNumber -and $n -ge 1 -and $n -le $lines.Count -and $quote -ceq ([string]$lines[$n-1])){'exact_numbered'}elseif($matches.Count -eq 1){'exact_wrong_number'}elseif($matches.Count -gt 1){'duplicate_exact'}elseif($trim.Count){'edge_whitespace'}elseif($norm.Count){'internal_whitespace'}elseif($quote.Length -gt 0 -and ($lines -join [Environment]::NewLine).Contains($quote)){'substring'}else{'not_found'}
  $sourceLine=if($hasNumber -and $n -ge 1 -and $n -le $lines.Count){[string]$lines[$n-1]}else{''}
  [void]$results.Add([pscustomobject]@{function=$obj.name;claimed_line=$o.line_number;status=$status;actual_exact_lines=@($matches);quote=$quote;source_at_claimed_line=$sourceLine})
 }
}
$out=Join-Path $d.FullName 'citation-diagnostics.json'
@{analysis=$d.FullName;count=$results.Count;findings=@($results)} | ConvertTo-Json -Depth 8 | Set-Content $out -Encoding UTF8
$results | Group-Object status | Select-Object Name,Count | Format-Table -AutoSize
Write-Host "Offline only. Report: $out"
