#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa',
 [int]$SampleLimit=30
)
$ErrorActionPreference='Stop'
if($Archive -ne [IO.Path]::GetFileName($Archive)){throw 'Archive must be a filename only'}
if($SampleLimit -lt 1 -or $SampleLimit -gt 1000){throw 'SampleLimit must be between 1 and 1000'}
$path=Join-Path (Join-Path $GamePath 'Data') $Archive
if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Archive missing: $path"}
$fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
$br=New-Object IO.BinaryReader($fs)
try{
 $magic=[Text.Encoding]::ASCII.GetString($br.ReadBytes(4))
 $version=$br.ReadUInt32();$offset=$br.ReadUInt32();$flags=$br.ReadUInt32()
 $folderCount=$br.ReadUInt32();$fileCount=$br.ReadUInt32()
 $folderNameBytes=$br.ReadUInt32();$fileNameBytes=$br.ReadUInt32();$types=$br.ReadUInt32()
 if($magic -ne ("BSA"+[char]0) -or $version -ne 105 -or $offset -ne 36){throw 'Unsupported archive header'}
 if($folderCount -gt 100000 -or $fileCount -gt 2000000 -or $fileNameBytes -gt 100000000){throw 'Unreasonable counts'}
 $counts=New-Object 'System.Collections.Generic.List[uint32]'
 $total=[long]0
 for($i=0;$i -lt $folderCount;$i++){
  [void]$br.ReadUInt64();$count=$br.ReadUInt32();[void]$br.ReadUInt32();[void]$br.ReadUInt64()
  $counts.Add($count);$total += $count
 }
 if($total -ne $fileCount){throw "Folder count mismatch $total / $fileCount"}
 $records=New-Object 'System.Collections.Generic.List[object]'
 $folderBytesSeen=[long]0
 for($i=0;$i -lt $folderCount;$i++){
  $n=[int]$br.ReadByte()
  if($n -lt 1 -or $fs.Position+$n -gt $fs.Length){throw "Invalid folder name at index $i"}
  $raw=$br.ReadBytes($n)
  if($raw.Length -ne $n -or $raw[$n-1] -ne 0){throw "Unterminated folder name at $i"}
  $folderBytesSeen += $n
  $folder=[Text.Encoding]::UTF8.GetString($raw,0,$n-1)
  for($j=0;$j -lt $counts[$i];$j++){
   $hash=$br.ReadUInt64();$sizeFlags=$br.ReadUInt32();$dataOffset=$br.ReadUInt32()
   $records.Add([pscustomobject]@{folder=$folder;hash=('{0:X16}' -f $hash);stored_size=($sizeFlags -band 0x3fffffff);data_offset=$dataOffset})
  }
 }
 $fileNameStart=$fs.Position
 if($fileNameStart + [long]$fileNameBytes -gt $fs.Length){throw 'Filename table extends past archive'}
 $nameTable=$br.ReadBytes([int]$fileNameBytes)
 if($nameTable.Length -ne $fileNameBytes){throw 'Filename table truncated'}
 $cursor=0;$invalid=0;$samples=New-Object System.Collections.ArrayList
 foreach($rec in $records){
  $start=$cursor
  while($cursor -lt $nameTable.Length -and $nameTable[$cursor] -ne 0){$cursor++}
  if($cursor -ge $nameTable.Length){throw "Missing filename terminator at record $($samples.Count)"}
  $name=[Text.Encoding]::UTF8.GetString($nameTable,$start,$cursor-$start)
  $cursor++
  if([string]::IsNullOrWhiteSpace($name) -or $name.Contains('/') -or $name.Contains('\') -or $name -eq '.' -or $name -eq '..'){$invalid++}
  if($samples.Count -lt $SampleLimit){
   [void]$samples.Add([pscustomobject]@{path=($rec.folder+'\'+$name);hash=$rec.hash;stored_size=$rec.stored_size;data_offset=$rec.data_offset})
  }
 }
 $report=[ordered]@{
  archive=$path;read_only=$true;version=$version;folder_count=$folderCount
  expected_files=$fileCount;named_files=$records.Count;folder_name_bytes_reported=$folderNameBytes
  folder_name_bytes_observed=$folderBytesSeen;file_name_bytes_reported=$fileNameBytes
  file_name_bytes_consumed=$cursor;filename_table_start=$fileNameStart
  filename_table_end=($fileNameStart+$fileNameBytes);invalid_names=$invalid
  exact_filename_table_consumption=($cursor -eq $fileNameBytes)
  sample_paths=@($samples)
  note='Read-only filename mapping; compression, hash correctness and extracted asset bytes remain unverified.'
 }
 $out=Join-Path (Join-Path $Root 'workspace\skyrim-bsa') (Get-Date -Format 'yyyyMMdd-HHmmss')
 New-Item -ItemType Directory -Force -Path $out | Out-Null
 $dest=Join-Path $out 'filename-table.json'
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $dest -Encoding UTF8
 Write-Host "Mapped: $($records.Count)/$fileCount; invalid names: $invalid; filename bytes: $cursor/$fileNameBytes"
 Write-Host "Report: $dest"
 if($records.Count -ne $fileCount -or $invalid -gt 0 -or $cursor -ne $fileNameBytes){exit 2}
}finally{$br.Dispose();$fs.Dispose()}
