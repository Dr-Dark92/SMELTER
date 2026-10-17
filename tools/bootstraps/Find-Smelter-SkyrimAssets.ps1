#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa',
 [string]$Pattern='*skuldafnworld*.dds',
 [ValidateRange(1,1000)][int]$Limit=30
)
$ErrorActionPreference='Stop'
if($Archive -ne [IO.Path]::GetFileName($Archive) -or -not $Archive.EndsWith('.bsa',[StringComparison]::OrdinalIgnoreCase)){throw 'Archive must be a BSA filename'}
$path=Join-Path (Join-Path $GamePath 'Data') $Archive
if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Archive not found: $path"}
$fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
$br=New-Object IO.BinaryReader($fs)
try{
 $magic=[Text.Encoding]::ASCII.GetString($br.ReadBytes(4))
 $version=$br.ReadUInt32();$offset=$br.ReadUInt32()
 $flags=$br.ReadUInt32();$folders=$br.ReadUInt32();$files=$br.ReadUInt32()
 $folderNameBytes=$br.ReadUInt32();$filenameBytes=$br.ReadUInt32();[void]$br.ReadUInt32()
 if($magic -ne ("BSA"+[char]0) -or $version -ne 105 -or $offset -ne 36){throw 'Only BSA v105 supported'}
 if($folders -gt 100000 -or $files -gt 2000000 -or $filenameBytes -gt 100000000){throw 'Unreasonable table sizes'}
 $counts=New-Object 'System.Collections.Generic.List[uint32]'
 [long]$sum=0
 for($i=0;$i -lt $folders;$i++){
  [void]$br.ReadUInt64();$n=$br.ReadUInt32();[void]$br.ReadUInt32();[void]$br.ReadUInt64()
  $counts.Add($n);$sum+=$n
 }
 if($sum -ne $files){throw 'Folder/file count mismatch'}
 $records=New-Object 'System.Collections.Generic.List[object]'
 for($i=0;$i -lt $folders;$i++){
  $len=[int]$br.ReadByte()
  if($len -lt 1 -or $fs.Position+$len -gt $fs.Length){throw 'Invalid folder name length'}
  $raw=$br.ReadBytes($len)
  if($raw.Length -ne $len -or $raw[$len-1] -ne 0){throw 'Invalid folder name'}
  $folder=[Text.Encoding]::UTF8.GetString($raw,0,$len-1)
  for($j=0;$j -lt $counts[$i];$j++){
   [void]$br.ReadUInt64();$sizeFlags=$br.ReadUInt32();$dataOffset=$br.ReadUInt32()
   $records.Add([pscustomobject]@{folder=$folder;sizeFlags=$sizeFlags;dataOffset=$dataOffset})
  }
 }
 if($fs.Position+[long]$filenameBytes -gt $fs.Length){throw 'Filename table exceeds archive'}
 $names=$br.ReadBytes([int]$filenameBytes);$cursor=0
 $matches=New-Object 'System.Collections.Generic.List[object]'
 [long]$totalMatches=0
 $wildcard=New-Object System.Management.Automation.WildcardPattern($Pattern,[System.Management.Automation.WildcardOptions]::IgnoreCase)
 for($i=0;$i -lt $records.Count;$i++){
  $start=$cursor
  while($cursor -lt $names.Length -and $names[$cursor] -ne 0){$cursor++}
  if($cursor -ge $names.Length){throw 'Unterminated filename table'}
  $name=[Text.Encoding]::UTF8.GetString($names,$start,$cursor-$start);$cursor++
  $r=$records[$i];$asset=$r.folder+'\'+$name
  if($wildcard.IsMatch($asset)){
   $totalMatches++
   if($matches.Count -lt $Limit){
    $size=[long]($r.sizeFlags -band 0x3fffffff)
    $compressed=((($flags -band 4) -ne 0) -xor (($r.sizeFlags -band 0x40000000) -ne 0))
    $matches.Add([pscustomobject]@{asset=$asset;stored_bytes=$size;compressed=$compressed;within_archive=([long]$r.dataOffset+$size -le $fs.Length)})
   }
  }
 }
 if($cursor -ne $names.Length){throw 'Filename table not fully consumed'}
 $out=Join-Path (Join-Path $Root 'workspace\skyrim-discovery') (Get-Date -Format 'yyyyMMdd-HHmmss')
 New-Item -ItemType Directory -Force -Path $out | Out-Null
 $report=[ordered]@{
  archive=$path;read_only_source=$true;bsa_version=$version;total_files=$files
  pattern=$Pattern;total_matches=$totalMatches;returned=$matches.Count;limit=$Limit
  matches=@($matches.ToArray())
  note='BSA v105 filename discovery only. No extraction or game modifications.'
 }
 $json=Join-Path $out 'discovery-result.json'
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $json -Encoding UTF8
 Write-Host "Indexed: $files; matching: $totalMatches; returned: $($matches.Count)"
 foreach($m in $matches){Write-Host $m.asset}
 Write-Host "Report: $json"
}finally{$br.Dispose();$fs.Dispose()}
