#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa',
 [int]$Samples=8
)
$ErrorActionPreference='Stop'
if($Archive -ne [IO.Path]::GetFileName($Archive)){throw 'Archive must be filename only'}
if($Samples -lt 1 -or $Samples -gt 20){throw 'Samples must be 1..20'}
$path=Join-Path (Join-Path $GamePath 'Data') $Archive
$fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
$br=New-Object IO.BinaryReader($fs)
try{
 $magic=[Text.Encoding]::ASCII.GetString($br.ReadBytes(4))
 $version=$br.ReadUInt32();$offset=$br.ReadUInt32();$flags=$br.ReadUInt32()
 $folders=$br.ReadUInt32();$files=$br.ReadUInt32()
 $folderNameBytes=$br.ReadUInt32();$filenameBytes=$br.ReadUInt32();$types=$br.ReadUInt32()
 if($magic -ne ("BSA"+[char]0) -or $version -ne 105 -or $offset -ne 36){throw 'Unsupported BSA header'}
 if($folders -gt 100000 -or $files -gt 2000000 -or $filenameBytes -gt 100000000){throw 'Unreasonable table sizes'}
 $counts=@();$sum=[long]0
 for($i=0;$i -lt $folders;$i++){
  [void]$br.ReadUInt64();$count=$br.ReadUInt32();[void]$br.ReadUInt32();[void]$br.ReadUInt64()
  $counts+= $count;$sum+=$count
 }
 if($sum -ne $files){throw 'File count mismatch'}
 $records=New-Object System.Collections.ArrayList
 for($i=0;$i -lt $folders;$i++){
  $n=[int]$br.ReadByte()
  if($n -lt 1 -or $n -gt 255 -or $fs.Position+$n -gt $fs.Length){throw 'Bad folder name'}
  $raw=$br.ReadBytes($n)
  if($raw[$n-1] -ne 0){throw 'Folder name not terminated'}
  $folder=[Text.Encoding]::UTF8.GetString($raw,0,$n-1)
  for($j=0;$j -lt $counts[$i];$j++){
   [void]$br.ReadUInt64();$sizeFlags=$br.ReadUInt32();$dataOffset=$br.ReadUInt32()
   [void]$records.Add([pscustomobject]@{folder=$folder;sizeFlags=$sizeFlags;dataOffset=$dataOffset})
  }
 }
 $names=$br.ReadBytes([int]$filenameBytes);$cursor=0
 $samplesOut=New-Object System.Collections.ArrayList
 for($i=0;$i -lt $records.Count -and $samplesOut.Count -lt $Samples;$i++){
  $start=$cursor
  while($cursor -lt $names.Length -and $names[$cursor] -ne 0){$cursor++}
  if($cursor -ge $names.Length){throw 'Bad filename table'}
  $name=[Text.Encoding]::UTF8.GetString($names,$start,$cursor-$start);$cursor++
  $r=$records[$i];$size=[int]($r.sizeFlags -band 0x3fffffff)
  $compressed=((($flags -band 4) -ne 0) -xor (($r.sizeFlags -band 0x40000000) -ne 0))
  if(-not $name.EndsWith('.dds',[StringComparison]::OrdinalIgnoreCase) -or $size -lt 32 -or $size -gt 1048576 -or -not $compressed){continue}
  if([long]$r.dataOffset+$size -gt $fs.Length){continue}
  $fs.Position=$r.dataOffset
  $head=$br.ReadBytes([Math]::Min(64,$size))
  $prefix=0
  if(($flags -band 0x100) -ne 0){$prefix=[int]$head[0]+1}
  $expected=$null;$payloadHex=$null;$possibleMagic=$null
  if($prefix+4 -le $head.Length){
   $expected=[BitConverter]::ToUInt32($head,$prefix)
   $p=$prefix+4
   if($p -lt $head.Length){
    $len=[Math]::Min(24,$head.Length-$p)
    $payloadHex=[BitConverter]::ToString($head,$p,$len)
    if($len -ge 4){$possibleMagic=[BitConverter]::ToString($head,$p,4)}
   }
  }
  [void]$samplesOut.Add([pscustomobject]@{
   asset=($r.folder+'\'+$name);stored_size=$size;data_offset=$r.dataOffset
   size_flags=('0x{0:X8}' -f $r.sizeFlags);compressed=$compressed
   first_bytes_hex=[BitConverter]::ToString($head)
   embedded_name_prefix_bytes=$prefix;expected_decoded_bytes=$expected
   compressed_payload_first_bytes_hex=$payloadHex;compressed_payload_magic=$possibleMagic
  })
 }
 if($samplesOut.Count -eq 0){throw 'No bounded compressed DDS samples found'}
 $out=Join-Path (Join-Path $Root 'workspace\skyrim-extraction') ('header-probe-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
 New-Item -ItemType Directory -Force -Path $out | Out-Null
 $report=[ordered]@{
  archive=$path;archive_version=$version;archive_flags=('0x{0:X8}' -f $flags)
  folder_count=$folders;file_count=$files
  samples=@($samplesOut);read_only_source=$true
  note='Header-only diagnostics; no decompression, extraction or archive modifications.'
 }
 $dest=Join-Path $out 'compression-headers.json'
 $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $dest -Encoding UTF8
 Write-Host "Inspected $($samplesOut.Count) compressed DDS headers"
 Write-Host "Report: $dest"
}finally{$br.Dispose();$fs.Dispose()}
