#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='',
 [int]$MaxFiles=150000
)
$ErrorActionPreference='Stop'
if(-not $GamePath){$GamePath=Read-Host 'Enter installed game directory (read-only inventory)'}
if(-not (Test-Path -LiteralPath $GamePath -PathType Container)){throw "Game directory not found: $GamePath"}
$game=(Resolve-Path -LiteralPath $GamePath).Path
$workspace=Join-Path $Root 'workspace\game-inventory'
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$out=Join-Path $workspace $stamp
New-Item -ItemType Directory -Force -Path $out | Out-Null
$extensions=@{}
$sample=New-Object System.Collections.ArrayList
$warnings=New-Object System.Collections.ArrayList
$total=[long]0;$bytes=[long]0;$truncated=$false
$known=@('.pak','.ucas','.utoc','.uasset','.uexp','.ubulk','.vpk','.vpk_c','.vpk_s','.bundle','.assets','.resource','.ress','.bank','.wem','.bnk','.bsa','.ba2','.arc','.cpk','.wad','.pck','.pfs','.dat','.bin','.exe','.dll','.zip','.7z','.rar','.fbx','.glb','.gltf','.dds','.ktx','.ktx2','.png','.wem','.fsb')
$queue=New-Object 'System.Collections.Generic.Queue[string]'
$queue.Enqueue($game)
while($queue.Count -gt 0 -and -not $truncated){
 $dir=$queue.Dequeue()
 try{$items=Get-ChildItem -LiteralPath $dir -Force -ErrorAction Stop}catch{[void]$warnings.Add("Unreadable directory: $dir");continue}
 foreach($item in $items){
  if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){continue}
  if($item.PSIsContainer){$queue.Enqueue($item.FullName);continue}
  $total++
  $bytes += [long]$item.Length
  $ext=[string]$item.Extension.ToLowerInvariant()
  if(-not $ext){$ext='[no extension]'}
  if(-not $extensions.ContainsKey($ext)){$extensions[$ext]=[pscustomobject]@{extension=$ext;count=0;bytes=[long]0}}
  $extensions[$ext].count++
  $extensions[$ext].bytes += [long]$item.Length
  if($known -contains $ext){
   $relative=$item.FullName.Substring($game.Length).TrimStart('\')
   $signature='not_inspected'
   if($item.Length -ge 4){
    try{
     $fs=[IO.File]::Open($item.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
     try{$buffer=New-Object byte[] 16;$read=$fs.Read($buffer,0,16)}finally{$fs.Dispose()}
     $hex=([BitConverter]::ToString($buffer,0,[Math]::Min($read,8))).Replace('-','')
     if($hex.StartsWith('4D5A')){$signature='PE_MZ'}
     elseif($hex.StartsWith('504B0304')){$signature='ZIP'}
     elseif($hex.StartsWith('377ABCAF271C')){$signature='7Z'}
     elseif($hex.StartsWith('C1832A9E')){$signature='Unreal_PAK_header_candidate'}
     else{$signature="hex:$hex"}
    }catch{$signature='unreadable'}
   }
   [void]$sample.Add([pscustomobject]@{relative_path=$relative;extension=$ext;size_bytes=[long]$item.Length;signature=$signature})
  }
  if($total -ge $MaxFiles){$truncated=$true;[void]$warnings.Add("Stopped at MaxFiles=$MaxFiles");break}
 }
}
$extRows=@($extensions.Values | Sort-Object count -Descending)
$inventory=[ordered]@{
 schema_version=1;game_path=$game;generated_at=(Get-Date).ToString('o')
 read_only=$true;total_files_scanned=$total;total_bytes_scanned=$bytes
 truncated=$truncated;extensions=$extRows;interesting_files=@($sample)
 warnings=@($warnings)
 note='Extension and magic-byte inventory only. Does not prove engine, compatibility, or extractability.'
}
$json=Join-Path $out 'inventory.json'
$inventory | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $json -Encoding UTF8
$extRows | Export-Csv -LiteralPath (Join-Path $out 'extensions.csv') -NoTypeInformation -Encoding UTF8
$sample | Export-Csv -LiteralPath (Join-Path $out 'interesting-files.csv') -NoTypeInformation -Encoding UTF8
Write-Host "PASS: read-only game inventory"
Write-Host "Files scanned: $total | Interesting files: $($sample.Count) | Truncated: $truncated"
Write-Host "Report: $json"
Write-Host 'No game files modified. No extraction or engine claims made.'
