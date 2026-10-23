#Requires -Version 5.1
[CmdletBinding()]
param(
 [string]$Root='C:\SMELTER',
 [string]$Target='C:\Windows\System32\where.exe',
 [int]$Top=12,
 [int]$TimeoutSeconds=600
)
$ErrorActionPreference='Stop'
if($Top -lt 1 -or $Top -gt 50){throw 'Top must be 1..50'}
if(-not(Test-Path -LiteralPath $Target -PathType Leaf)){throw "Target missing: $Target"}
$targetItem=Get-Item -LiteralPath $Target
if($targetItem.Length -gt 100MB){throw 'Safety limit: input binary exceeds 100 MiB'}
$headless='C:\Tools\Ghidra\support\analyzeHeadless.bat'
if(-not(Test-Path -LiteralPath $headless)){throw 'Ghidra headless not installed'}
$jdk=Get-ChildItem 'C:\Program Files\Eclipse Adoptium','C:\Program Files\Microsoft' -Directory -ErrorAction SilentlyContinue | Where-Object Name -Match '^jdk-21' | Sort-Object Name -Descending | Select-Object -First 1
if(-not $jdk){throw 'JDK21 not found'}
$env:JAVA_HOME=$jdk.FullName
$env:PATH=(Join-Path $jdk.FullName 'bin')+';'+$env:PATH
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$work=Join-Path $Root "workspace\function-discovery\$stamp"
$scripts=Join-Path $work 'scripts'
$project=Join-Path $work 'project'
New-Item -ItemType Directory -Force -Path $scripts,$project | Out-Null
Start-Transcript -Path (Join-Path $work 'run.log') | Out-Null
try {
 $java=@'
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.File;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
public class SmelterDiscover extends GhidraScript {
 static class Candidate {
  Function f; long size; int callers; int score; int searchApiHits; int helperApiHits; String name;
  Candidate(Function f) { this.f=f; name=f.getName(); size=f.getBody().getNumAddresses(); }
 }
 boolean runtime(String s) {
  String n=s.toLowerCase();
  return n.startsWith("_") || n.startsWith("crt") || n.startsWith("thunk") ||
    n.contains("security_cookie") || n.contains("guard_") ||
    n.contains("initterm") || n.contains("scrt") || n.contains("mingw") ||
    n.contains("onexit") || n.contains("maincrtstartup");
 }
 public void run() throws Exception {
  String[] args=getScriptArgs();
  File csv=new File(args[0]), output=new File(args[1]);
  int top=Integer.parseInt(args[2]);
  List<Candidate> items=new ArrayList<>();
  String[] searchApis={"findfirstfile","findnextfile","findclose","getfullpathname","getfileattributes","getenvironmentvariable","getlongpathname","getshortpathname","pathmatchspec","searchpath"};
  String[] helperApis={"writeconsole","formatmessage","widechartomultibyte","fprintf","fflush"};
  FunctionIterator it=currentProgram.getFunctionManager().getFunctions(true);
  while(it.hasNext()) {
   Function f=it.next();
   if(f.isExternal() || f.isThunk()) continue;
   Candidate c=new Candidate(f);
   ReferenceIterator refs=currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
   while(refs.hasNext()) { Reference r=refs.next(); if(r.getReferenceType().isCall()) c.callers++; }
   // Resolve call targets to imported/thunk symbols when Ghidra exposes them.
   // This is a heuristic: indirect calls and unresolved imports may be missed.
   InstructionIterator instructions=currentProgram.getListing().getInstructions(f.getBody(),true);
   int inspected=0;
   while(instructions.hasNext() && inspected++<10000) {
    Instruction ins=instructions.next();
    for(Reference ref:ins.getReferencesFrom()) {
     if(!ref.getReferenceType().isCall())continue;
     String target="";
     Symbol sym=currentProgram.getSymbolTable().getPrimarySymbol(ref.getToAddress());
     if(sym!=null)target=sym.getName().toLowerCase();
     Function callee=currentProgram.getFunctionManager().getFunctionAt(ref.getToAddress());
     if(callee!=null)target=target+" "+callee.getName().toLowerCase();
     for(String api:searchApis)if(target.contains(api)){c.searchApiHits++;break;}
     for(String api:helperApis)if(target.contains(api)){c.helperApiHits++;break;}
    }
   }
   // Prefer behavioral API evidence over frequently called formatting helpers.
   c.score=(int)Math.min(35,c.size/25)+Math.min(12,c.callers*2);
   if(!runtime(c.name))c.score+=10;
   if(c.name.toLowerCase().contains("main"))c.score+=20;
   c.score+=Math.min(80,c.searchApiHits*20);
   c.score-=Math.min(45,c.helperApiHits*15);
   if(c.size<20)c.score-=20;
   items.add(c);
  }
  Collections.sort(items,new Comparator<Candidate>() {
   public int compare(Candidate a,Candidate b) {
    int x=Integer.compare(b.score,a.score);
    if(x!=0)return x;
    return a.f.getEntryPoint().compareTo(b.f.getEntryPoint());
   }
  });
  try(PrintWriter w=new PrintWriter(csv,"UTF-8")) {
   w.println("rank,address,name,size_bytes_approx,call_references,score,runtime_name_heuristic,search_api_hits,helper_api_hits");
   int rank=0;
   for(Candidate c:items) {
    String safe=c.name.replace(",","_").replace("\n","_").replace("\r","_");
    w.println((++rank)+","+c.f.getEntryPoint()+","+safe+","+c.size+","+c.callers+","+c.score+","+runtime(c.name)+","+c.searchApiHits+","+c.helperApiHits);
   }
  }
  DecompInterface dec=new DecompInterface();
  if(!dec.openProgram(currentProgram))throw new Exception("Decompiler open failed");
  int done=0;
  try(PrintWriter w=new PrintWriter(output,"UTF-8")) {
   w.println("binary="+currentProgram.getExecutablePath());
   w.println("language="+currentProgram.getLanguageID());
   w.println("CANDIDATE_COUNT="+items.size());
   for(Candidate c:items) {
    if(done>=top)break;
    DecompileResults result=dec.decompileFunction(c.f,30,monitor);
    if(result==null || !result.decompileCompleted() || result.getDecompiledFunction()==null)continue;
    w.println("\n===== FUNCTION "+c.f.getName()+" "+c.f.getEntryPoint()+" score="+c.score+" =====");
    w.println(result.getDecompiledFunction().getC());
    done++;
   }
   w.println("DECOMPILED_COUNT="+done);
  } finally {dec.dispose();}
  if(done==0)throw new Exception("No candidate functions decompiled");
 }
}
'@
 $javaPath=Join-Path $scripts 'SmelterDiscover.java'
 [IO.File]::WriteAllText($javaPath,$java,(New-Object Text.UTF8Encoding($false)))
 $csv=Join-Path $work 'functions.csv'
 $out=Join-Path $work 'selected-decompiled.txt'
 $stdout=Join-Path $work 'ghidra.stdout.log'
 $stderr=Join-Path $work 'ghidra.stderr.log'
 $args=@('/d','/s','/c',('""'+$headless+'" "'+$project+'" Discovery -import "'+$targetItem.FullName+'" -scriptPath "'+$scripts+'" -postScript SmelterDiscover.java "'+$csv+'" "'+$out+'" '+$Top+' -deleteProject"'))
 Write-Host "Discovering functions: $($targetItem.FullName)"
 $proc=Start-Process -FilePath $env:ComSpec -ArgumentList $args -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 try {
  if(-not $proc.WaitForExit($TimeoutSeconds*1000)){
   & taskkill.exe /PID $proc.Id /T /F | Out-Null
   throw "Ghidra timed out after $TimeoutSeconds seconds"
  }
  $proc.WaitForExit()
  $proc.Refresh()
  $exitCode=$null
  try {$exitCode=$proc.ExitCode} catch {}
  if($null -ne $exitCode -and $exitCode -ne 0){
   throw "Ghidra failed (exit $exitCode); inspect $stdout and $stderr"
  }
  if($null -eq $exitCode){
   Write-Warning 'Ghidra process exit code unavailable; validating generated artifacts instead.'
  }
 } finally {$proc.Dispose()}
 if(-not(Test-Path $csv) -or -not(Test-Path $out)){
  $tail=@()
  if(Test-Path $stdout){$tail+=@(Get-Content $stdout -Tail 25)}
  if(Test-Path $stderr){$tail+=@(Get-Content $stderr -Tail 25)}
  throw "Ghidra output missing. Logs: $stdout $stderr`n$($tail -join [Environment]::NewLine)"
 }
 $body=Get-Content $out -Raw
 if($body -notmatch 'DECOMPILED_COUNT=([1-9][0-9]*)'){throw 'No successfully decompiled candidates'}
 $hash=(Get-FileHash -LiteralPath $targetItem.FullName -Algorithm SHA256).Hash
 $metadata=[ordered]@{
  target=$targetItem.FullName;sha256=$hash;selection='heuristic: call-target API categories, function size, call references, names';requested_top=$Top
  decompiled_count=[int]$Matches[1];timestamp=(Get-Date).ToString('o')
  ghidra_exit_code=$exitCode;exit_code_verified=($null -ne $exitCode)
  note='Function rankings are heuristics; inspect code before drawing conclusions. No AI inference in this phase.'
 }
 $metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $work 'result.json') -Encoding UTF8
 Write-Host "PASS: Selected and decompiled $($metadata.decompiled_count) ranked functions"
 if($null -eq $exitCode){Write-Warning "Artifacts verified; Ghidra exit status remains unverified."}
 Write-Host "Function index: $csv"
 Write-Host "Decompilation: $out"
 Write-Host "Metadata: $(Join-Path $work 'result.json')"
} finally {Stop-Transcript | Out-Null}
