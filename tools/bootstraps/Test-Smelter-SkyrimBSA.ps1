#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition'
)
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $GamePath -PathType Container)){throw "Game directory missing: $GamePath"}
$game=(Resolve-Path -LiteralPath $GamePath).Path
$data=Join-Path $game 'Data'
if(-not (Test-Path -LiteralPath $data -PathType Container)){throw "Data directory missing: $data"}
$out=Join-Path (Join-Path $Root 'workspace\skyrim-bsa') (Get-Date -Format 'yyyyMMdd-HHmmss')
New-Item -ItemType Directory -Force -Path $out | Out-Null
$rows=New-Object System.Collections.ArrayList
foreach($file in @(Get-ChildItem -LiteralPath $data -Filter '*.bsa' -File)){
 $stream=[IO.File]::Open($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 try{
  if($stream.Length -lt 36){throw 'Header shorter than 36 bytes'}
  $reader=New-Object IO.BinaryReader($stream)
  try{
   $magic=[Text.Encoding]::ASCII.GetString($reader.ReadBytes(4))
   $version=$reader.ReadUInt32()
   $offset=$reader.ReadUInt32()
   $flags=$reader.ReadUInt32()
   $folders=$reader.ReadUInt32()
   $files=$reader.ReadUInt32()
   $folderNames=$reader.ReadUInt32()
   $fileNames=$reader.ReadUInt32()
   $types=$reader.ReadUInt32()
  }finally{$reader.Dispose()}
  $valid=($magic -eq "BSA"+[char]0 -and $version -eq 105 -and $offset -ge 36 -and $offset -lt $file.Length -and $folders -le 1000000 -and $files -le 10000000)
  [void]$rows.Add([pscustomobject]@{
   name=$file.Name;size_bytes=[long]$file.Length;magic=$magic.TrimEnd([char]0);version=$version
   folder_records_offset=$offset;archive_flags=$flags;folder_count=$folders;file_count=$files
   folder_name_bytes=$folderNames;file_name_bytes=$fileNames;file_flags=$types
   header_plausible=$valid
  })
 }catch{
  [void]$rows.Add([pscustomobject]@{name=$file.Name;size_bytes=[long]$file.Length;header_plausible=$false;error=$_.Exception.Message})
 }finally{$stream.Dispose()}
}
$pass=@($rows | Where-Object {$_.header_plausible -eq $true}).Count
$report=[ordered]@{game_path=$game;read_only=$true;archive_count=$rows.Count;plausible_headers=$pass;archives=@($rows);note='Header-only inspection; no archive extraction, checksum validation, or file-table parsing.'}
$path=Join-Path $out 'bsa-headers.json'
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $path -Encoding UTF8
$rows | Export-Csv -LiteralPath (Join-Path $out 'bsa-headers.csv') -NoTypeInformation -Encoding UTF8
Write-Host "BSA headers plausible: $pass/$($rows.Count)"
Write-Host "Report: $path"
if($pass -ne $rows.Count){exit 2}
