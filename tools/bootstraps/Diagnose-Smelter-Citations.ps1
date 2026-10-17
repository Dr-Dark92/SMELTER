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
$repairs=New-Object System.Collections.ArrayList
foreach($finding in $results){
 if($finding.status -in @('substring','not_found')){
  $n=[int]$finding.claimed_line
  $lines=$blocks[[string]$finding.function]
  if($n -lt 1 -or $n -gt $lines.Count){continue}
  $sourceLine=[string]$lines[$n-1]
  $kind=if($finding.status -eq 'substring'){'partial_statement'}else{'multiline_or_mismatch'}
  [void]$repairs.Add([pscustomobject]@{function=$finding.function;line=$n;issue=$kind;model_quote=$finding.quote;original_source_line=$sourceLine;status='requires_review'})
 }
}
$repairPath=Join-Path $d.FullName 'citation-repair-candidates.json'
@{source=$m.source;auto_approved=0;review_required=$repairs.Count;candidates=@($repairs)} | ConvertTo-Json -Depth 8 | Set-Content $repairPath -Encoding UTF8
Write-Host "Review-required citation candidates: $($repairs.Count); no evidence automatically altered"
Write-Host "Candidates: $repairPath"
$resolved=New-Object System.Collections.ArrayList
foreach($finding in $results){
 $lines=$blocks[[string]$finding.function]
 $n=0
 if(-not [int]::TryParse([string]$finding.claimed_line,[ref]$n)){continue}
 if($n -lt 1 -or $n -gt $lines.Count){continue}
 $original=[string]$lines[$n-1]
 $kind=[string]$finding.status
 if($kind -eq 'edge_whitespace' -and $finding.quote.Trim() -ceq $original.Trim()){
  [void]$resolved.Add([pscustomobject]@{function=$finding.function;line=$n;status='verified_whitespace_only';source_evidence=$original;model_evidence=$finding.quote})
 }elseif($kind -eq 'substring' -and $original.Trim().StartsWith($finding.quote.Trim(),[StringComparison]::Ordinal)){
  [void]$resolved.Add([pscustomobject]@{function=$finding.function;line=$n;status='partial_prefix_source_confirmed';source_evidence=$original;model_evidence=$finding.quote})
 }elseif($kind -eq 'not_found'){
  [void]$resolved.Add([pscustomobject]@{function=$finding.function;line=$n;status='unverified_multiline_requires_context';source_evidence=$original;model_evidence=$finding.quote})
 }
}
foreach($finding in $results){
 if($finding.status -ne 'edge_whitespace'){continue}
 $already=@($resolved | Where-Object {$_.function -eq $finding.function -and $_.line -eq [int]$finding.claimed_line})
 if($already.Count){continue}
 $lines=$blocks[[string]$finding.function]
 $locations=@(for($i=0;$i -lt $lines.Count;$i++){if($finding.quote.Trim() -ceq ([string]$lines[$i]).Trim()){$i+1}})
 [void]$resolved.Add([pscustomobject]@{function=$finding.function;line=[int]$finding.claimed_line;status='quote_found_but_claimed_line_mismatch';source_evidence=[string]$finding.source_at_claimed_line;model_evidence=$finding.quote;matching_source_lines=@($locations)})
}
$path=Join-Path $d.FullName 'source-grounded-evidence.json'
@{source=$m.source;analysis=$d.FullName;items=@($resolved);note='This artifact never overwrites model output. Prefix matches do not verify the complete statement or interpretation.'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding UTF8
Write-Host "Source-grounded evidence: $path"
$results | Group-Object status | Select-Object Name,Count | Format-Table -AutoSize
$accepted=@($results | Where-Object {$_.status -in @('exact_numbered','exact_wrong_number','edge_whitespace','internal_whitespace')})
$unresolved=@($results | Where-Object {$_.status -notin @('exact_numbered','exact_wrong_number','edge_whitespace','internal_whitespace')})
$review=Join-Path $d.FullName 'citation-review.md'
$report=New-Object System.Collections.Generic.List[string]
$report.Add('# SMELTER - Offline evidence review')
$report.Add("Source: $($m.source)")
$report.Add("Total observations: $($results.Count)")
$report.Add("Textually supported (exact or whitespace-normalized): $($accepted.Count)")
$report.Add("Unresolved/partial: $($unresolved.Count)")
$report.Add('Textual support verifies source quotation only, not the model interpretation.')
foreach($finding in $unresolved){
 $report.Add('')
 $report.Add("## $($finding.function), claimed line $($finding.claimed_line)")
 $report.Add("Status: $($finding.status)")
 $report.Add("Model quotation: $($finding.quote)")
 $report.Add("Actual source at claimed line: $($finding.source_at_claimed_line)")
}
[IO.File]::WriteAllLines($review,$report,(New-Object System.Text.UTF8Encoding($false)))
Write-Host "Supported quotations: $($accepted.Count)/$($results.Count)"
Write-Host "Unresolved quotations: $($unresolved.Count)"
Write-Host "Review: $review"
Write-Host "Offline only. Report: $out"
