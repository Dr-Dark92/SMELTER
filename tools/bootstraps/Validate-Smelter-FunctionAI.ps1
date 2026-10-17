#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER',[string]$AnalysisDirectory='')
$ErrorActionPreference='Stop'
if(-not $AnalysisDirectory){
 $dirs=@(Get-ChildItem (Join-Path $Root 'workspace\analysis') -Directory | Sort-Object Name -Descending)
 $dir=$dirs | Where-Object {Test-Path (Join-Path $_.FullName 'function-01.json')} | Select-Object -First 1
 if(-not $dir){throw 'No per-function analysis run found'}
 $AnalysisDirectory=$dir.FullName
}
$AnalysisDirectory=(Resolve-Path -LiteralPath $AnalysisDirectory).Path
$metaFile=Join-Path $AnalysisDirectory 'result.json'
if(-not(Test-Path $metaFile)){throw 'Analysis metadata missing'}
$meta=Get-Content $metaFile -Raw | ConvertFrom-Json
$source=[string]$meta.source
if(-not(Test-Path -LiteralPath $source)){throw "Ghidra source missing: $source"}
$raw=Get-Content -LiteralPath $source -Raw
$blocks=[regex]::Matches($raw,'(?ms)^===== FUNCTION ([^\r\n]+) =====\r?\n(.*?)(?=^===== FUNCTION |\z)')
$codeByAddress=@{}
foreach($block in $blocks){
 $tokens=$block.Groups[1].Value.Trim() -split '\s+'
 if($tokens.Count -ge 2){$codeByAddress[$tokens[1].ToLowerInvariant()]=$block.Groups[2].Value.Trim()}
}
$files=@(Get-ChildItem -LiteralPath $AnalysisDirectory -Filter 'function-*.json' -File | Sort-Object Name)
if($files.Count -eq 0){throw 'No function JSON files found'}
$known=@{}
foreach($file in $files){
 $obj=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
 $known[[string]$obj.name]=$true
}
$findings=New-Object System.Collections.ArrayList
$counts=[ordered]@{exact_evidence=0;rejected_evidence=0;unsupported_security_claims=0;cross_function_conflicts=0;unresolved_inferences=0}
foreach($file in $files){
 $obj=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
 $address=[string]$obj.address
 $key=$address.ToLowerInvariant()
 if(-not $codeByAddress.ContainsKey($key)){throw "Source function $address missing"}
 $code=[string]$codeByAddress[$key]
 if(-not $obj.schema_valid){[void]$findings.Add([ordered]@{function=$obj.name;kind='model_output';status='rejected';detail='Invalid model JSON'});continue}
 foreach($obs in @($obj.model_output.observations)){
  $evidence=[string]$obs.evidence
  $exact=($evidence.Length -gt 0 -and $code.Contains($evidence))
  if($exact){$counts.exact_evidence++}else{$counts.rejected_evidence++}
  [void]$findings.Add([ordered]@{function=$obj.name;kind='observation';status=$(if($exact){'exact_quote_verified'}else{'rejected_not_exact'});evidence=$evidence;meaning=[string]$obs.meaning})
 }
 $texts=New-Object System.Collections.ArrayList
 [void]$texts.Add([string]$obj.model_output.summary)
 foreach($inf in @($obj.model_output.inferences)){[void]$texts.Add([string]$inf.claim);[void]$texts.Add([string]$inf.reason)}
 foreach($t in $texts){
  if($t -match '(?i)(security.check.cookie|security validation|security check|no (obvious |direct )?(vulnerabilit|buffer overflow|use.after.free)|not vulnerable|safe from|absence of vulnerabilit)'){
   $counts.unsupported_security_claims++
   [void]$findings.Add([ordered]@{function=$obj.name;kind='claim';status='flagged_for_review';detail=$t;reason='Security conclusion or security-cookie inference requires independent evidence'})
  }
  foreach($callee in $known.Keys){
   if($callee -eq $obj.name){continue}
   if($t.Contains($callee) -and $t -match '(?i)(not decompiled|not analyzed|unknown without (further |additional )?decompilation|not available|not visible|without.*decompilation)'){
    $counts.cross_function_conflicts++
    [void]$findings.Add([ordered]@{function=$obj.name;kind='cross_function';status='conflict';detail=$t;related_function=$callee;reason='Related function is present in this analysis batch'})
   }
  }
 }
 foreach($inf in @($obj.model_output.inferences)){
  $counts.unresolved_inferences++
  [void]$findings.Add([ordered]@{function=$obj.name;kind='inference';status='unverified';detail=[string]$inf.claim;confidence=[string]$inf.confidence})
 }
}
$report=[ordered]@{
 validator_version='1.0';analysis_directory=$AnalysisDirectory;source=$source
 source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
 function_count=$files.Count;counts=$counts;findings=@($findings)
 limitations=@(
 'Exact quote matching confirms only that quoted text appears in the corresponding Ghidra block, not that its interpretation is correct.',
 'Regex security checks are conservative and cannot detect every unsupported conclusion.',
 'Cross-function conflicts are detected by name and wording heuristics, not semantic reasoning.',
 'AI inferences remain unverified even when associated quotes match.',
 'Source blocks may be truncated; validation is against the available selected-decompiled.txt.'
 )
}
$dest=Join-Path $AnalysisDirectory 'evidence-validation.json'
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $dest -Encoding UTF8
$md=New-Object System.Collections.Generic.List[string]
$md.Add('# SMELTER - Evidence validation')
$md.Add('')
$md.Add("Source: $source")
$md.Add("Functions: $($files.Count)")
$md.Add("Exact quote matches: $($counts.exact_evidence)")
$md.Add("Rejected/nonexact quotes: $($counts.rejected_evidence)")
$md.Add("Security claims flagged: $($counts.unsupported_security_claims)")
$md.Add("Cross-function conflicts: $($counts.cross_function_conflicts)")
$md.Add("Unverified inferences: $($counts.unresolved_inferences)")
$md.Add('')
$md.Add('Exact match means text presence only, NOT semantic or security verification.')
$md.Add('')
foreach($f in $findings){
 if($f.status -eq 'exact_quote_verified'){continue}
 $md.Add("## $($f.function) - $($f.kind) [$($f.status)]")
 if($f.evidence){$md.Add("Evidence: $($f.evidence)")}
 if($f.detail){$md.Add("Claim: $($f.detail)")}
 if($f.reason){$md.Add("Reason: $($f.reason)")}
 $md.Add('')
}
$mdPath=Join-Path $AnalysisDirectory 'evidence-validation.md'
[IO.File]::WriteAllLines($mdPath,$md,(New-Object Text.UTF8Encoding($false)))
Write-Host "PASS: Evidence validation completed for $($files.Count) functions"
Write-Host "Exact quotes: $($counts.exact_evidence); rejected quotes: $($counts.rejected_evidence)"
Write-Host "Security flags: $($counts.unsupported_security_claims); cross-function conflicts: $($counts.cross_function_conflicts)"
Write-Host "Report: $mdPath"
Write-Host "JSON: $dest"
