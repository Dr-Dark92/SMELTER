#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$GamePath='D:\Games\Magicka 2',
 [ValidateRange(1,64)][int]$MaxOutputMiB=16,
 [ValidateRange(1,16)][int]$MaxInputMiB=4
)
$ErrorActionPreference='Stop'
$data=Join-Path $GamePath 'data'
if(-not (Test-Path -LiteralPath $data -PathType Container)){throw "Game data missing: $data"}
$id=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$out=Join-Path $Root ('workspace\magicka2-zlib\'+$id)
New-Item -ItemType Directory -Path $out -Force | Out-Null
$report=[ordered]@{source=$data;read_only_source=$true;game_modified=$false;status='not_started';sample=$null;database=$null;error=$null}
try{
 $dbPath=Join-Path $data 'bundle_database.data'
 if(Test-Path -LiteralPath $dbPath -PathType Leaf){
  $db=[IO.File]::ReadAllBytes($dbPath)
  $strings=New-Object 'System.Collections.Generic.List[string]'
  $builder=New-Object Text.StringBuilder
  foreach($b in $db){
   if($b -ge 32 -and $b -le 126){[void]$builder.Append([char]$b)}
   else{if($builder.Length -ge 5){$strings.Add($builder.ToString())};[void]$builder.Clear()}
  }
  if($builder.Length -ge 5){$strings.Add($builder.ToString())}
  $report.database=[ordered]@{bytes=$db.Length;strings=@($strings | Select-Object -First 200);first64_hex=[BitConverter]::ToString($db,0,[Math]::Min(64,$db.Length))}
 }
 $candidate=$null
 foreach($f in @(Get-ChildItem -LiteralPath $data -File | Where-Object {$_.Name -match '^[a-f0-9]{16}$' -and $_.Length -le ($MaxInputMiB*1MB) -and $_.Length -ge 22} | Sort-Object Length)){
  $s=[IO.File]::OpenRead($f.FullName)
  try{$head=New-Object byte[] 18;[void]$s.Read($head,0,18)}finally{$s.Dispose()}
  if($head[0] -eq 4 -and $head[1] -eq 0 -and $head[2] -eq 0 -and $head[3] -eq 240 -and $head[16] -eq 120 -and $head[17] -eq 156){$candidate=$f;break}
 }
 if($null -eq $candidate){throw 'No suitably small wrapped zlib sample found'}
 $input=[IO.File]::ReadAllBytes($candidate.FullName)
 $expected=[BitConverter]::ToUInt32($input,4)
 if($expected -gt ($MaxOutputMiB*1MB)){throw "Sample declared size $expected exceeds limit"}
 $payloadLength=$input.Length-16-2-4
 if($payloadLength -le 0){throw 'Zlib payload too short'}
 $memory=New-Object IO.MemoryStream(,$input)
 $memory.Position=18
 $bounded=New-Object IO.MemoryStream
 $deflate=New-Object IO.Compression.DeflateStream($memory,[IO.Compression.CompressionMode]::Decompress,$true)
 $buffer=New-Object byte[] 65536
 $total=0
 try{
  while(($n=$deflate.Read($buffer,0,$buffer.Length)) -gt 0){
   $total+=$n
   if($total -gt ($MaxOutputMiB*1MB)){throw 'Decompressed sample exceeded limit'}
   $bounded.Write($buffer,0,$n)
  }
 }finally{$deflate.Dispose();$memory.Dispose()}
 $bytes=$bounded.ToArray();$bounded.Dispose()
 $preview=if($bytes.Length){[BitConverter]::ToString($bytes,0,[Math]::Min(96,$bytes.Length))}else{''}
 $ascii=if($bytes.Length){-join ($bytes[0..([Math]::Min(96,$bytes.Length)-1)] | ForEach-Object {if($_ -ge 32 -and $_ -le 126){[char]$_}else{'.'}})}else{''}
 $report.sample=[ordered]@{file=$candidate.Name;input_bytes=$input.Length;declared_size=$expected;decompressed_bytes=$bytes.Length;size_matches=($expected -eq $bytes.Length);first96_hex=$preview;first96_ascii=$ascii;sha256=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create().ComputeHash($bytes))).Replace('-',''))}
 $report.status=if($bytes.Length -gt 0 -and $expected -eq $bytes.Length){'passed'}else{'needs_review'}
}catch{$report.status='failed';$report.error=$_.Exception.Message}
$path=Join-Path $out 'magicka2-zlib-result.json'
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding UTF8
Write-Host "Status: $($report.status)"
if($report.sample){Write-Host "Sample: $($report.sample.file); decoded: $($report.sample.decompressed_bytes) bytes"}
if($report.error){Write-Host "Error: $($report.error)"}
Write-Host "Report: $path"
if($report.status -eq 'failed'){exit 2}
