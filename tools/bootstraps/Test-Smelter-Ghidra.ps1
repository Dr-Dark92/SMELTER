#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root='C:\SMELTER',[string]$Target='C:\Windows\System32\where.exe',[int]$TimeoutSeconds=240)
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$work=Join-Path $Root "workspace\ghidra-smoke\$stamp"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$log=Join-Path $work 'test.log'
Start-Transcript -Path $log | Out-Null
try {
 if(-not(Test-Path -LiteralPath $Target)){throw "Target not found: $Target"}
 $headless='C:\Tools\Ghidra\support\analyzeHeadless.bat'
 if(-not(Test-Path -LiteralPath $headless)){throw "Ghidra headless launcher not found: $headless"}
 $jdk=Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory -ErrorAction SilentlyContinue | Where-Object Name -Match '^jdk-21' | Sort-Object Name -Descending | Select-Object -First 1
 if(-not $jdk){throw 'JDK21 missing'}
 $env:JAVA_HOME=$jdk.FullName
 $env:PATH=(Join-Path $jdk.FullName 'bin')+';'+$env:PATH
 $scripts=Join-Path $work 'scripts'
 New-Item -ItemType Directory -Force -Path $scripts | Out-Null
 $java=@'
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.File;
import java.io.PrintWriter;
public class SmelterSmoke extends ghidra.app.script.GhidraScript {
 public void run() throws Exception {
  File out = new File(getScriptArgs()[0]);
  int functions = 0;
  int decompiled = 0;
  DecompInterface dec = new DecompInterface();
  if (!dec.openProgram(currentProgram)) throw new Exception("Decompiler could not open program");
  try (PrintWriter w = new PrintWriter(out, "UTF-8")) {
   w.println("binary=" + currentProgram.getExecutablePath());
   w.println("language=" + currentProgram.getLanguageID());
   FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
   while (it.hasNext()) {
    Function f = it.next();
    functions++;
    if (f.isExternal() || decompiled >= 3) continue;
    DecompileResults result = dec.decompileFunction(f, 30, monitor);
    if (result != null && result.decompileCompleted() && result.getDecompiledFunction() != null) {
     w.println("FUNCTION " + f.getName() + " " + f.getEntryPoint());
     w.println(result.getDecompiledFunction().getC());
     decompiled++;
    }
   }
   w.println("FUNCTION_COUNT=" + functions);
   w.println("DECOMPILED_COUNT=" + decompiled);
  } finally { dec.dispose(); }
  if (functions < 1 || decompiled < 1) throw new Exception("No native functions decompiled");
 }
}
'@
 $script=Join-Path $scripts 'SmelterSmoke.java'
 [System.IO.File]::WriteAllText($script,$java,(New-Object System.Text.UTF8Encoding($false)))
 $out=Join-Path $work 'decompiled.txt'
 $stdout=Join-Path $work 'ghidra.stdout.log'
 $stderr=Join-Path $work 'ghidra.stderr.log'
 $project=Join-Path $work 'project'
 New-Item -ItemType Directory -Force -Path $project | Out-Null
 $args=@('/d','/s','/c',('""'+$headless+'" "'+$project+'" Smoke -import "'+$Target+'" -scriptPath "'+$scripts+'" -postScript SmelterSmoke.java "'+$out+'" -deleteProject"'))
 Write-Host "Analyzing: $Target"
 $proc=Start-Process -FilePath $env:ComSpec -ArgumentList $args -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 if($null -eq $proc.ExitCode){throw 'Ghidra exit code unavailable'}
 if($proc.ExitCode -ne 0){throw "Ghidra failed (exit $($proc.ExitCode)). Logs: $stdout $stderr"}
 if(-not(Test-Path $out)){throw "Ghidra produced no decompilation report. Inspect $stdout"}
 $result=Get-Content $out -Raw
 if($result -notmatch 'DECOMPILED_COUNT=([1-9][0-9]*)'){throw "Ghidra did not decompile a function. Report: $out"}
 Write-Host "PASS: Ghidra analyzed and decompiled a real Windows executable"
 Write-Host "Report: $out"
 Write-Host "Log: $log"
} finally {Stop-Transcript | Out-Null}
