#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa',
 [int]$MaxStoredBytes=1048576
)
$ErrorActionPreference='Stop'
if($Archive -ne [IO.Path]::GetFileName($Archive)){throw 'Archive must be a filename only'}
$path=Join-Path (Join-Path $GamePath 'Data') $Archive
if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Archive missing: $path"}
$fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
$br=New-Object IO.BinaryReader($fs)
try{
 $magic=[Text.Encoding]::ASCII.GetString($br.ReadBytes(4))
 $version=$br.ReadUInt32();$offset=$br.ReadUInt32();$flags=$br.ReadUInt32()
 $folderCount=$br.ReadUInt32();$fileCount=$br.ReadUInt32()
 $folderNameBytes=$br.ReadUInt32();$fileNameBytes=$br.ReadUInt32();$types=$br.ReadUInt32()
 if($magic -ne ("BSA"+[char]0) -or $version -ne 105 -or $offset -ne 36){throw 'Unsupported BSA header'}
 if($folderCount -gt 100000 -or $fileCount -gt 2000000 -or $fileNameBytes -gt 100000000){throw 'Unreasonable archive counts'}
 $counts=New-Object 'System.Collections.Generic.List[uint32]'
 $sum=[long]0
 for($i=0;$i -lt $folderCount;$i++){
  [void]$br.ReadUInt64();$count=$br.ReadUInt32();[void]$br.ReadUInt32();[void]$br.ReadUInt64()
  $counts.Add($count);$sum += $count
 }
 if($sum -ne $fileCount){throw 'Folder record count mismatch'}
 $records=New-Object 'System.Collections.Generic.List[object]'
 for($i=0;$i -lt $folderCount;$i++){
  $n=[int]$br.ReadByte()
  if($n -lt 1 -or $fs.Position+$n -gt $fs.Length){throw 'Invalid folder name length'}
  $raw=$br.ReadBytes($n)
  if($raw[$n-1] -ne 0){throw 'Invalid folder name termination'}
  $folder=[Text.Encoding]::UTF8.GetString($raw,0,$n-1)
  for($j=0;$j -lt $counts[$i];$j++){
   $hash=$br.ReadUInt64();$sizeFlags=$br.ReadUInt32();$dataOffset=$br.ReadUInt32()
   $records.Add([pscustomobject]@{folder=$folder;sizeFlags=$sizeFlags;dataOffset=$dataOffset})
  }
 }
 if($fs.Position + [long]$fileNameBytes -gt $fs.Length){throw 'Filename table truncated'}
 $names=$br.ReadBytes([int]$fileNameBytes)
 $cursor=0;$selected=$null
 for($i=0;$i -lt $records.Count;$i++){
  $start=$cursor
  while($cursor -lt $names.Length -and $names[$cursor] -ne 0){$cursor++}
  if($cursor -ge $names.Length){throw 'Unterminated filename'}
  $name=[Text.Encoding]::UTF8.GetString($names,$start,$cursor-$start)
  $cursor++
  $r=$records[$i]
  $size=[int]($r.sizeFlags -band 0x3fffffff)
  $flip=(($r.sizeFlags -band 0x40000000) -ne 0)
  $compressed=((($flags -band 4) -ne 0) -xor $flip)
  if($null -eq $selected -and $name.EndsWith('.dds',[StringComparison]::OrdinalIgnoreCase) -and $size -ge 128 -and $size -le $MaxStoredBytes -and -not $compressed -and ([long]$r.dataOffset+$size -le $fs.Length)){
   $selected=[pscustomobject]@{path=($r.folder+'\'+$name);size=$size;offset=[long]$r.dataOffset;compressed=$compressed}
  }
 }
 if($cursor -ne $names.Length){throw 'Filename table length mismatch'}
 if($null -eq $selected){throw 'No uncompressed DDS candidate found within size limit; no extraction attempted'}
 $fs.Position=$selected.offset
 $bytes=$br.ReadBytes($selected.size)
 if($bytes.Length -ne $selected.size){throw 'Payload truncated'}
 # BSA embedded filename prefixes are indicated by archive flag 0x100.
 $prefixBytes=0
 if(($flags -band 0x100) -ne 0){
  $prefixBytes=[int]$bytes[0]+1
  if($prefixBytes -ge $bytes.Length){throw 'Invalid embedded name prefix'}
 }
 if($bytes.Length - $prefixBytes -lt 128){throw 'Payload too small for DDS header'}
 $sig=[Text.Encoding]::ASCII.GetString($bytes,$prefixBytes,4)
 if($sig -ne 'DDS '){throw "Candidate does not contain DDS magic at expected offset; got $sig"}
 $headerSize=[BitConverter]::ToUInt32($bytes,$prefixBytes+4)
 $height=[BitConverter]::ToUInt32($bytes,$prefixBytes+12)
 $width=[BitConverter]::ToUInt32($bytes,$prefixBytes+16)
 if($headerSize -ne 124 -or $width -lt 1 -or $height -lt 1 -or $width -gt 32768 -or $height -gt 32768){throw 'Invalid DDS header fields'}
 $out=Join-Path (Join-Path $Root 'workspace\skyrim-extraction') (Get-Date -Format 'yyyyMMdd-HHmmss')
 New-Item -ItemType Directory -Force -Path $out | Out-Null
 $file=Join-Path $out 'sample.dds'
 $payload=New-Object byte[] ($bytes.Length-$prefixBytes)
 [Array]::Copy($bytes,$prefixBytes,$payload,0,$payload.Length)
 [IO.File]::WriteAllBytes($file,$payload)
 $sha=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
 $report=[ordered]@{archive=$path;source_asset=$selected.path;read_only_source=$true;compressed=$false;dds_width=$width;dds_height=$height;dds_header_size=$headerSize;extracted_file=$file;sha256=$sha;note='Single uncompressed DDS extracted to workspace only. DDS format and in-game rendering not fully validated.'}
 $json=Join-Path $out 'extraction-result.json'
 $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $json -Encoding UTF8
 Write-Host "PASS: DDS $width x $height, SHA256 $sha"
 Write-Host "Report: $json"
}finally{$br.Dispose();$fs.Dispose()}
