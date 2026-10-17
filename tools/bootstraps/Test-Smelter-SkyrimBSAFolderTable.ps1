#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition',
 [string]$Archive='Skyrim - Textures6.bsa'
)
$ErrorActionPreference='Stop'
if($Archive -ne [IO.Path]::GetFileName($Archive)){throw 'Archive must be a filename only'}
$path=Join-Path (Join-Path $GamePath 'Data') $Archive
if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Archive missing: $path"}
$stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
$reader=New-Object IO.BinaryReader($stream)
try{
 $magic=[Text.Encoding]::ASCII.GetString($reader.ReadBytes(4))
 $version=$reader.ReadUInt32();$offset=$reader.ReadUInt32();$flags=$reader.ReadUInt32()
 $folderCount=$reader.ReadUInt32();$fileCount=$reader.ReadUInt32()
 $folderNamesBytes=$reader.ReadUInt32();$fileNamesBytes=$reader.ReadUInt32();$fileFlags=$reader.ReadUInt32()
 if($magic -ne ("BSA"+[char]0) -or $version -ne 105){throw 'Not Skyrim SE BSA v105'}
 if($folderCount -gt 100000 -or $fileCount -gt 2000000){throw 'Unreasonable record counts'}
 if($offset -ne 36){throw "Unexpected folder record offset $offset"}
 # BSA v105 folder records are 24 bytes (hash 8, file count 4, unknown 4, offset 8).
 $folderRecords=New-Object System.Collections.ArrayList
 for($i=0;$i -lt $folderCount;$i++){
  $hash=$reader.ReadUInt64();$count=$reader.ReadUInt32();$unknown=$reader.ReadUInt32();$position=$reader.ReadUInt64()
  [void]$folderRecords.Add([pscustomobject]@{index=$i;hash=('{0:X16}' -f $hash);file_count=$count;unknown=$unknown;offset=$position})
 }
 $sum=[long]0
 foreach($f in $folderRecords){$sum += [long]$f.file_count}
 if($sum -ne $fileCount){throw "Folder file count sum $sum does not match header $fileCount"}
 $tableEnd=$stream.Position
 $out=Join-Path (Join-Path $Root 'workspace\skyrim-bsa') (Get-Date -Format 'yyyyMMdd-HHmmss')
 New-Item -ItemType Directory -Force -Path $out | Out-Null
 $report=[ordered]@{
  archive=$path;version=$version;read_only=$true;header_file_count=$fileCount
  header_folder_count=$folderCount;folder_file_count_sum=$sum;folder_records_end=$tableEnd
  archive_flags=$flags;file_flags=$fileFlags;folder_name_bytes=$folderNamesBytes;file_name_bytes=$fileNamesBytes
  folder_records=@($folderRecords)
  note='Folder table only. Folder offsets and file contents have not been validated; no extraction attempted.'
 }
 $json=Join-Path $out 'folder-table.json'
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $json -Encoding UTF8
 $folderRecords | Export-Csv -LiteralPath (Join-Path $out 'folder-table.csv') -NoTypeInformation -Encoding UTF8
 Write-Host "PASS: $folderCount folder records, $fileCount files (sum verified)"
 Write-Host "Report: $json"
}finally{$reader.Dispose();$stream.Dispose()}
