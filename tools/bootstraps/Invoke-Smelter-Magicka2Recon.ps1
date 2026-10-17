#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='D:\Games\Magicka 2',
 [ValidateRange(1,100)][int]$SampleLimit=30
)
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $GamePath -PathType Container)){throw "Magicka 2 folder not found: $GamePath"}
$run=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$out=Join-Path $Root ('workspace\magicka2-recon\'+$run)
New-Item -ItemType Directory -Path $out -Force | Out-Null
$all=Get-ChildItem -LiteralPath $GamePath -Recurse -File -ErrorAction Stop
$extGroups=@($all | Group-Object Extension | Sort-Object Count -Descending | ForEach-Object {
 [pscustomobject]@{extension=if($_.Name){$_.Name}else{'(none)'};count=$_.Count;bytes=[long](($_.Group | Measure-Object Length -Sum).Sum)}
})
$containers=@('.bundle','.pak','.vpk','.vfs','.arc','.dat','.bin','.zip','.7z','.pck','.wad','.assets','.resource','.resS','.fsb','.bank','.xnb','.hfs','.sdat')
$models=@('.fbx','.obj','.dae','.gltf','.glb','.nif','.mesh','.model','.mdl','.hkx','.skel','.skeleton')
$textures=@('.dds','.png','.tga','.jpg','.jpeg','.ktx','.ktx2','.bmp','.tex')
$interesting=@($all | Where-Object {
 $e=$_.Extension.ToLowerInvariant()
 ($e -in $containers) -or ($e -in $models) -or ($e -in $textures) -or ($_.Name -match '(?i)wizard|robe|hood|character|avatar|asset|content|archive')
} | Select-Object -First 400 | ForEach-Object {
 [pscustomobject]@{path=$_.FullName.Substring($GamePath.TrimEnd('\').Length).TrimStart('\');bytes=$_.Length;extension=$_.Extension}
})
$largest=@($all | Sort-Object Length -Descending | Select-Object -First $SampleLimit | ForEach-Object {
 [pscustomobject]@{path=$_.FullName.Substring($GamePath.TrimEnd('\').Length).TrimStart('\');bytes=$_.Length;extension=$_.Extension}
})
$signatures=New-Object 'System.Collections.Generic.List[object]'
foreach($file in @($all | Sort-Object Length -Descending | Select-Object -First $SampleLimit)){
 $bytes=New-Object byte[] 32
 $stream=[IO.File]::Open($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 try{$read=$stream.Read($bytes,0,32)}finally{$stream.Dispose()}
 $hex=if($read -gt 0){[BitConverter]::ToString($bytes,0,[Math]::Min($read,16))}else{''}
 $ascii=if($read -gt 0){-join ($bytes[0..([Math]::Min($read,16)-1)] | ForEach-Object {if($_ -ge 32 -and $_ -le 126){[char]$_}else{'.'}})}else{''}
 $signatures.Add([pscustomobject]@{path=$file.FullName.Substring($GamePath.TrimEnd('\').Length).TrimStart('\');bytes=$file.Length;first16_hex=$hex;first16_ascii=$ascii})
}
$report=[ordered]@{
 game='Magicka 2';source=$GamePath;read_only=$true;game_modified=$false
 files_scanned=@($all).Count;total_bytes=[long](($all | Measure-Object Length -Sum).Sum)
 extension_groups=$extGroups;interesting_files=$interesting;largest_files=$largest;largest_file_headers=@($signatures.ToArray())
 note='Inventory and magic-byte samples only. No extraction, decryption, format assumptions, or modification performed.'
}
$path=Join-Path $out 'magicka2-recon.json'
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding UTF8
Write-Host "Magicka 2 files: $($report.files_scanned)"
Write-Host "Total bytes: $($report.total_bytes)"
Write-Host 'Top file extensions:'
$extGroups | Select-Object -First 15 | Format-Table -AutoSize | Out-String | Write-Host
Write-Host "Report: $path"
