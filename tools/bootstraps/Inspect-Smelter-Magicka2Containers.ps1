#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='D:\Games\Magicka 2',
 [ValidateRange(1,256)][int]$MaxFiles=160,
 [ValidateRange(64,65536)][int]$SampleBytes=4096
)
$ErrorActionPreference='Stop'
$data=Join-Path $GamePath 'data'
if(-not (Test-Path -LiteralPath $data -PathType Container)){throw "Missing game data directory: $data"}
$id=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$out=Join-Path $Root ('workspace\magicka2-format\'+$id)
New-Item -ItemType Directory -Path $out -Force | Out-Null
$files=@(Get-ChildItem -LiteralPath $data -File | Sort-Object Name | Select-Object -First $MaxFiles)
$records=New-Object 'System.Collections.Generic.List[object]'
foreach($f in $files){
 $n=[int][Math]::Min([long]$SampleBytes,$f.Length)
 $buf=New-Object byte[] $n
 $stream=[IO.File]::Open($f.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 try{$read=$stream.Read($buf,0,$n)}finally{$stream.Dispose()}
 $hex=if($read){[BitConverter]::ToString($buf,0,[Math]::Min($read,64))}else{''}
 $prefix=if($read -ge 4){[BitConverter]::ToString($buf,0,4)}else{''}
 $strings=New-Object 'System.Collections.Generic.List[string]'
 $current=New-Object Text.StringBuilder
 for($i=0;$i -lt $read;$i++){
  $v=$buf[$i]
  if($v -ge 32 -and $v -le 126){[void]$current.Append([char]$v)}
  else{
   if($current.Length -ge 5){$strings.Add($current.ToString())}
   [void]$current.Clear()
  }
 }
 if($current.Length -ge 5){$strings.Add($current.ToString())}
 $tokens=@($strings | Select-Object -First 20)
 $possibleMarkers=@('DDS ','glTF','OggS','RIFF','PK'+[char]3+[char]4,'UnityFS','MESH','FSB5','PNG')
 $markerHits=New-Object 'System.Collections.Generic.List[object]'
 foreach($marker in $possibleMarkers){
  $needle=[Text.Encoding]::ASCII.GetBytes($marker)
  for($j=0;$j -le $read-$needle.Length;$j++){
   $match=$true
   for($k=0;$k -lt $needle.Length;$k++){if($buf[$j+$k] -ne $needle[$k]){$match=$false;break}}
   if($match){$markerHits.Add([pscustomobject]@{marker=$marker;offset=$j});break}
  }
 }
 $records.Add([pscustomobject]@{
  file=$f.Name;bytes=$f.Length;extension=$f.Extension;header64_hex=$hex
  prefix4=$prefix;sampled_bytes=$read;ascii_strings=$tokens;embedded_signatures=@($markerHits.ToArray())
 })
}
$groups=@($records | Group-Object prefix4 | Sort-Object Count -Descending | ForEach-Object {[pscustomobject]@{prefix4=$_.Name;count=$_.Count}})
$report=[ordered]@{
 source=$data;read_only=$true;game_modified=$false
 sampled_files=$records.Count;sample_bytes_per_file=$SampleBytes
 prefix_groups=$groups;files=@($records.ToArray())
 note='Read-only header and limited string/signature survey. Header patterns do not establish format or compression. No files unpacked.'
}
$path=Join-Path $out 'magicka2-format.json'
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $path -Encoding UTF8
Write-Host "Files sampled: $($records.Count)"
$groups | Select-Object -First 10 | Format-Table -AutoSize | Out-String | Write-Host
Write-Host "Report: $path"
