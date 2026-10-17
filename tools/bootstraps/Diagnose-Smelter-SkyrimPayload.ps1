#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa'
)
$ErrorActionPreference='Stop'
if($Archive -ne [IO.Path]::GetFileName($Archive)){throw 'Archive must be a filename'}
$path=Join-Path (Join-Path $GamePath 'Data') $Archive
$fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
$br=[IO.BinaryReader]::new($fs)
try{
 $magic=[Text.Encoding]::ASCII.GetString($br.ReadBytes(4));$version=$br.ReadUInt32()
 $offset=$br.ReadUInt32();$flags=$br.ReadUInt32();$folderCount=$br.ReadUInt32()
 $fileCount=$br.ReadUInt32();[void]$br.ReadUInt32();$filenameBytes=$br.ReadUInt32();[void]$br.ReadUInt32()
 if($magic -ne ("BSA"+[char]0) -or $version -ne 105 -or $offset -ne 36){throw 'Unsupported archive'}
 if($folderCount -gt 100000 -or $fileCount -gt 2000000){throw 'Unreasonable counts'}
 $counts=@();$sum=[long]0
 for($i=0;$i -lt $folderCount;$i++){
  [void]$br.ReadUInt64();$n=$br.ReadUInt32();[void]$br.ReadUInt32();[void]$br.ReadUInt64()
  $counts+= $n;$sum+=$n
 }
 if($sum -ne $fileCount){throw 'Count mismatch'}
 $records=New-Object System.Collections.ArrayList
 for($i=0;$i -lt $folderCount;$i++){
  $n=[int]$br.ReadByte();if($n -lt 1 -or $fs.Position+$n -gt $fs.Length){throw 'Invalid folder'}
  $raw=$br.ReadBytes($n);if($raw[$n-1] -ne 0){throw 'Folder terminator invalid'}
  $folder=[Text.Encoding]::UTF8.GetString($raw,0,$n-1)
  for($j=0;$j -lt $counts[$i];$j++){
   [void]$br.ReadUInt64();$sf=$br.ReadUInt32();$do=$br.ReadUInt32()
   [void]$records.Add([pscustomobject]@{folder=$folder;sf=$sf;dataOffset=$do})
  }
 }
 $names=$br.ReadBytes([int]$filenameBytes);$cursor=0;$samples=New-Object System.Collections.ArrayList
 for($i=0;$i -lt $records.Count -and $samples.Count -lt 4;$i++){
  $start=$cursor
  while($cursor -lt $names.Length -and $names[$cursor] -ne 0){$cursor++}
  if($cursor -ge $names.Length){throw 'Invalid filename table'}
  $name=[Text.Encoding]::UTF8.GetString($names,$start,$cursor-$start);$cursor++
  $r=$records[$i];$size=[int]($r.sf -band 0x3fffffff)
  $compressed=((($flags -band 4) -ne 0) -xor (($r.sf -band 0x40000000) -ne 0))
  if(!$compressed -or !$name.EndsWith('.dds',[StringComparison]::OrdinalIgnoreCase) -or $size -lt 128 -or $size -gt 1048576){continue}
  if([long]$r.dataOffset+$size -gt $fs.Length){continue}
  $fs.Position=$r.dataOffset
  $stored=$br.ReadBytes($size)
  $prefix=0
  if(($flags -band 0x100) -ne 0){$prefix=[int]$stored[0]+1}
  if($prefix+4 -ge $stored.Length){continue}
  $expected=[BitConverter]::ToUInt32($stored,$prefix)
  $payloadStart=$prefix+4
  $len=[Math]::Min(96,$stored.Length-$payloadStart)
  $bytes=[byte[]]::new($len)
  [Array]::Copy($stored,$payloadStart,$bytes,0,$len)
  [void]$samples.Add([pscustomobject]@{
   asset=($r.folder+'\'+$name);offset=$r.dataOffset;stored_size=$size
   embedded_filename_prefix_bytes=$prefix;decoded_size=$expected
   payload_offset_in_entry=$payloadStart;payload_length=($size-$payloadStart)
   payload_first_96_bytes_hex=[BitConverter]::ToString($bytes)
   first_byte_decimal=[int]$stored[$payloadStart]
  })
 }
 $out=Join-Path (Join-Path $Root 'workspace\skyrim-extraction') ('payload-probe-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
 New-Item -ItemType Directory -Force -Path $out | Out-Null
 $report=[ordered]@{archive=$path;archive_flags=('0x{0:X8}' -f $flags);samples=@($samples);read_only_source=$true;note='Reads bounded stored bytes; no decompression, extraction or game modification'}
 $dest=Join-Path $out 'payload-probe.json'
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $dest -Encoding UTF8
 Write-Host "Inspected $($samples.Count) compressed payloads. Report: $dest"
}finally{$br.Dispose();$fs.Dispose()}
