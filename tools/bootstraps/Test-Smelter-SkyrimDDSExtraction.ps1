#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa',
 [int]$MaxStoredBytes=1048576,
 [int]$MaxDecodedBytes=16777216
)
$ErrorActionPreference='Stop'
if($Archive -ne [IO.Path]::GetFileName($Archive)){throw 'Archive must be filename only'}
$path=Join-Path (Join-Path $GamePath 'Data') $Archive
if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Archive missing: $path"}
if($MaxStoredBytes -lt 128 -or $MaxDecodedBytes -lt 128){throw 'Invalid size limits'}
$code=@'
using System;
public static class SmelterLz4 {
 public static byte[] Decode(byte[] src, int start, int length, int expected) {
  if(expected<1 || expected>16777216 || start<0 || length<0 || start>src.Length-length) throw new Exception("LZ4 bounds");
  byte[] dst=new byte[expected]; int ip=start,end=start+length,op=0;
  while(ip<end) {
   int token=src[ip++]; int literals=token>>4;
   if(literals==15){int b; do {if(ip>=end)throw new Exception("LZ4 literal length truncated");b=src[ip++];literals=checked(literals+b);}while(b==255);}
   if(literals>end-ip || literals>expected-op)throw new Exception("LZ4 literal overrun");
   Buffer.BlockCopy(src,ip,dst,op,literals);ip+=literals;op+=literals;
   if(ip==end)break;
   if(end-ip<2)throw new Exception("LZ4 match offset truncated");
   int distance=src[ip]|(src[ip+1]<<8);ip+=2;
   if(distance<1 || distance>op)throw new Exception("LZ4 invalid distance");
   int match=(token&15)+4;
   if((token&15)==15){int b;do{if(ip>=end)throw new Exception("LZ4 match length truncated");b=src[ip++];match=checked(match+b);}while(b==255);}
   if(match>expected-op)throw new Exception("LZ4 match overrun");
   for(int i=0;i<match;i++)dst[op+i]=dst[op-distance+i];
   op+=match;
  }
  if(op!=expected)throw new Exception("LZ4 decoded length mismatch");
  return dst;
 }
}
'@
if(-not ('SmelterLz4' -as [type])){Add-Type -TypeDefinition $code -ErrorAction Stop}
$fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
$br=New-Object IO.BinaryReader($fs)
try {
 $magic=[Text.Encoding]::ASCII.GetString($br.ReadBytes(4));$version=$br.ReadUInt32();$offset=$br.ReadUInt32()
 $flags=$br.ReadUInt32();$folderCount=$br.ReadUInt32();$fileCount=$br.ReadUInt32()
 $folderNameBytes=$br.ReadUInt32();$fileNameBytes=$br.ReadUInt32();$types=$br.ReadUInt32()
 if($magic -ne ("BSA"+[char]0) -or $version -ne 105 -or $offset -ne 36){throw 'Unsupported BSA'}
 if($folderCount -gt 100000 -or $fileCount -gt 2000000 -or $fileNameBytes -gt 100000000){throw 'Unreasonable table size'}
 $counts=New-Object 'System.Collections.Generic.List[uint32]';$sum=[long]0
 for($i=0;$i -lt $folderCount;$i++){
  [void]$br.ReadUInt64();$n=$br.ReadUInt32();[void]$br.ReadUInt32();[void]$br.ReadUInt64()
  $counts.Add($n);$sum+=$n
 }
 if($sum -ne $fileCount){throw 'Count mismatch'}
 $records=New-Object 'System.Collections.Generic.List[object]'
 for($i=0;$i -lt $folderCount;$i++){
  $n=[int]$br.ReadByte()
  if($n -lt 1 -or $fs.Position+$n -gt $fs.Length){throw 'Bad folder name'}
  $raw=$br.ReadBytes($n)
  if($raw.Length -ne $n -or $raw[$n-1] -ne 0){throw 'Bad folder name terminator'}
  $folder=[Text.Encoding]::UTF8.GetString($raw,0,$n-1)
  for($j=0;$j -lt $counts[$i];$j++){
   [void]$br.ReadUInt64();$sizeFlags=$br.ReadUInt32();$dataOffset=$br.ReadUInt32()
   $records.Add([pscustomobject]@{folder=$folder;sizeFlags=$sizeFlags;dataOffset=$dataOffset})
  }
 }
 if($fs.Position + [long]$fileNameBytes -gt $fs.Length){throw 'Bad filename table'}
 $names=$br.ReadBytes([int]$fileNameBytes);$cursor=0
 $candidates=New-Object 'System.Collections.Generic.List[object]'
 for($i=0;$i -lt $records.Count;$i++){
  $start=$cursor
  while($cursor -lt $names.Length -and $names[$cursor] -ne 0){$cursor++}
  if($cursor -ge $names.Length){throw 'Unterminated filename'}
  $name=[Text.Encoding]::UTF8.GetString($names,$start,$cursor-$start);$cursor++
  $r=$records[$i];$size=[int]($r.sizeFlags -band 0x3fffffff)
  $compressed=((($flags -band 4) -ne 0) -xor (($r.sizeFlags -band 0x40000000) -ne 0))
  if($name.EndsWith('.dds',[StringComparison]::OrdinalIgnoreCase) -and $size -ge 128 -and $size -le $MaxStoredBytes -and ([long]$r.dataOffset+$size -le $fs.Length)){
   $candidates.Add([pscustomobject]@{asset=($r.folder+'\'+$name);size=$size;offset=[long]$r.dataOffset;compressed=$compressed})
  }
 }
 if($cursor -ne $fileNameBytes){throw 'Filename table mismatch'}
 $selected=$null;$decoded=$null;$attempted=0;$errors=New-Object System.Collections.ArrayList
 foreach($c in $candidates){
  $attempted++
  try{
   $fs.Position=$c.offset;$stored=$br.ReadBytes($c.size)
   if($stored.Length -ne $c.size){throw 'Truncated stored data'}
   $prefix=0
   if(($flags -band 0x100) -ne 0){
    $prefix=[int]$stored[0]+1
    if($prefix -ge $stored.Length){throw 'Invalid embedded filename'}
   }
   if($c.compressed){
    if($stored.Length-$prefix -lt 5){throw 'Compressed payload too short'}
    $expected=[BitConverter]::ToUInt32($stored,$prefix)
    if($expected -gt $MaxDecodedBytes -or $expected -lt 128){throw "Decoded size outside limit: $expected"}
    $data=[SmelterLz4]::Decode($stored,$prefix+4,$stored.Length-$prefix-4,[int]$expected)
   }else{
    $data=New-Object byte[] ($stored.Length-$prefix)
    [Array]::Copy($stored,$prefix,$data,0,$data.Length)
   }
   if($data.Length -lt 128 -or [Text.Encoding]::ASCII.GetString($data,0,4) -ne 'DDS '){throw 'Not DDS magic'}
   $header=[BitConverter]::ToUInt32($data,4);$height=[BitConverter]::ToUInt32($data,12);$width=[BitConverter]::ToUInt32($data,16)
   if($header -ne 124 -or $height -lt 1 -or $width -lt 1 -or $height -gt 32768 -or $width -gt 32768){throw 'Invalid DDS dimensions/header'}
   $selected=$c;$decoded=$data;break
  }catch{
   if($errors.Count -lt 10){[void]$errors.Add([pscustomobject]@{asset=$c.asset;reason=$_.Exception.Message})}
  }
 }
 $out=Join-Path (Join-Path $Root 'workspace\skyrim-extraction') (Get-Date -Format 'yyyyMMdd-HHmmss')
 New-Item -ItemType Directory -Force -Path $out | Out-Null
 $report=[ordered]@{
  archive=$path;read_only_source=$true;candidate_count=$candidates.Count;attempted=$attempted
  extracted=($null -ne $selected);errors=@($errors)
  note='Bounded LZ4 BSA v105 single DDS probe. No Skyrim files modified. In-game rendering not tested.'
 }
 if($null -ne $selected){
  $dest=Join-Path $out 'sample.dds';[IO.File]::WriteAllBytes($dest,$decoded)
  $report.asset=$selected.asset;$report.compressed=$selected.compressed
  $report.width=$width;$report.height=$height;$report.decoded_bytes=$decoded.Length
  $report.output=$dest;$report.sha256=(Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash
 }
 $json=Join-Path $out 'extraction-result.json'
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $json -Encoding UTF8
 Write-Host "Candidates: $($candidates.Count); attempted: $attempted; extracted: $($report.extracted)"
 Write-Host "Report: $json"
 if(-not $report.extracted){exit 2}
}finally{$br.Dispose();$fs.Dispose()}
