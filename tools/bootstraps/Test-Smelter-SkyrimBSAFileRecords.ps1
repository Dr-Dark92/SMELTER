#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa'
)
$ErrorActionPreference='Stop'
if($Archive -ne [IO.Path]::GetFileName($Archive)){throw 'Archive must be filename only'}
$path=Join-Path (Join-Path $GamePath 'Data') $Archive
if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Missing archive: $path"}
$fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
$br=New-Object IO.BinaryReader($fs)
try {
 $magic=[Text.Encoding]::ASCII.GetString($br.ReadBytes(4))
 $ver=$br.ReadUInt32();$offset=$br.ReadUInt32();$flags=$br.ReadUInt32()
 $folders=$br.ReadUInt32();$files=$br.ReadUInt32()
 $folderNameBytes=$br.ReadUInt32();$fileNameBytes=$br.ReadUInt32();$types=$br.ReadUInt32()
 if($magic -ne ("BSA"+[char]0) -or $ver -ne 105 -or $offset -ne 36){throw 'Unsupported BSA header'}
 if($folders -gt 100000 -or $files -gt 2000000){throw 'Unreasonable counts'}
 $folderTable=New-Object System.Collections.ArrayList
 for($i=0;$i -lt $folders;$i++){
  $h=$br.ReadUInt64();$n=$br.ReadUInt32();$u=$br.ReadUInt32();$o=$br.ReadUInt64()
  [void]$folderTable.Add([pscustomobject]@{index=$i;count=$n;offset=$o})
 }
 $recordRegionStart=$fs.Position
 $samples=New-Object System.Collections.ArrayList
 $seen=[long]0
 $invalidOffsets=0
 $invalidNames=0
 $firstData=[long]::MaxValue
 $sampleLimit=40
 for($i=0;$i -lt $folderTable.Count;$i++){
  $folder=$folderTable[$i]
  if($fs.Position -ge $fs.Length){throw "Folder region truncated at $i"}
  $nameLength=[int]$br.ReadByte()
  if($nameLength -lt 1 -or $nameLength -gt 255){$invalidNames++}
  if($fs.Position + $nameLength + ([long]$folder.count * 16) -gt $fs.Length){throw "Folder $i records exceed archive"}
  $nameBytes=$br.ReadBytes($nameLength)
  $folderName=[Text.Encoding]::UTF8.GetString($nameBytes).TrimEnd([char]0)
  if($nameBytes.Length -eq 0 -or $nameBytes[$nameBytes.Length-1] -ne 0){$invalidNames++}
  for($j=0;$j -lt $folder.count;$j++){
   $hash=$br.ReadUInt64();$sizeFlags=$br.ReadUInt32();$dataOffset=$br.ReadUInt32()
   $seen++
   $size=($sizeFlags -band 0x3fffffff)
   if(([long]$dataOffset -ge $fs.Length) -or ($size -gt 0 -and ([long]$dataOffset + $size -gt $fs.Length))){$invalidOffsets++}
   if([long]$dataOffset -lt $firstData){$firstData=[long]$dataOffset}
   if($samples.Count -lt $sampleLimit){
    [void]$samples.Add([pscustomobject]@{folder=$folderName;file_hash=('{0:X16}' -f $hash);size_flags=$sizeFlags;stored_size=$size;data_offset=$dataOffset})
   }
  }
 }
 $regionEnd=$fs.Position
 $expectedFileNameEnd=$regionEnd + [long]$fileNameBytes
 $fileNameTableFits=($expectedFileNameEnd -le $fs.Length -and $expectedFileNameEnd -le $firstData)
 $report=[ordered]@{
  archive=$path;read_only=$true;version=$ver;folders=$folders;files_expected=$files
  file_records_parsed=$seen;folder_record_region_start=$recordRegionStart
  folder_record_region_end=$regionEnd;folder_name_bytes_header=$folderNameBytes
  file_name_bytes_header=$fileNameBytes;first_data_offset=$firstData
  file_name_table_fits_before_data=$fileNameTableFits
  invalid_folder_names=$invalidNames;invalid_data_bounds=$invalidOffsets
  sample_file_records=@($samples)
  note='Read-only structural probe. File names, compression, file hashes, and extracted content are not validated.'
 }
 $dir=Join-Path (Join-Path $Root 'workspace\skyrim-bsa') (Get-Date -Format 'yyyyMMdd-HHmmss')
 New-Item -ItemType Directory -Force -Path $dir | Out-Null
 $dest=Join-Path $dir 'file-record-probe.json'
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $dest -Encoding UTF8
 Write-Host "Parsed file records: $seen/$files; invalid offsets: $invalidOffsets; invalid names: $invalidNames"
 Write-Host "Filename table fits before data: $fileNameTableFits"
 Write-Host "Report: $dest"
 if($seen -ne $files -or $invalidOffsets -gt 0 -or $invalidNames -gt 0 -or -not $fileNameTableFits){exit 2}
}finally{$br.Dispose();$fs.Dispose()}
