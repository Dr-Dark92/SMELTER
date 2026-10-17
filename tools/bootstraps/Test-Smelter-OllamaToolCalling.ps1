#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER',[string]$Model='qwen3.5:9b')
$ErrorActionPreference='Stop'
$out=Join-Path $Root 'workspace\integrations'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$payload=@{
 model=$Model;stream=$false;think=$false
 messages=@(@{role='user';content='Call the read_file tool to read C:\SMELTER\README.md. Do not invent file contents.'})
 tools=@(@{type='function';function=@{name='read_file';description='Read a local file';parameters=@{type='object';properties=@{path=@{type='string'}};required=@('path')}}})
 options=@{temperature=0;num_predict=256}
} | ConvertTo-Json -Depth 12
try{
 $response=Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/chat' -Method Post -Body $payload -ContentType 'application/json' -TimeoutSec 120
 $calls=@($response.message.tool_calls)
 $ok=$calls.Count -gt 0 -and @($calls | Where-Object {$_.function.name -eq 'read_file'}).Count -gt 0
 $result=[ordered]@{model=$Model;native_tool_call_detected=$ok;tool_call_count=$calls.Count;tool_names=@($calls | ForEach-Object {$_.function.name});assistant_content=$response.message.content;note='This only tests Ollama structured tool-call emission. No filesystem read is performed.'}
 $file=Join-Path $out 'ollama-native-tools.json'
 $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $file -Encoding UTF8
 Write-Host "Native tool-call emitted: $ok"
 Write-Host "Report: $file"
 if(-not $ok){exit 2}
}catch{
 Write-Error $_
 exit 1
}
