// Fixed SMELTER headless evidence exporter. Never executes the analyzed target.
// @category SMELTER
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public class SmelterAnalysis extends GhidraScript {
    static final int SCAN_LIMIT = 200000;
    String quote(String value) {
        StringBuilder out = new StringBuilder("\"");
        for (char c : value.toCharArray()) {
            if (c == '\\' || c == '"') out.append('\\').append(c);
            else if (c < 32) out.append(String.format("\\u%04x", (int)c));
            else out.append(c);
        }
        return out.append('"').toString();
    }
    String trim(String text, int maximum) { return text.length() > maximum ? text.substring(0, maximum) : text; }
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 5 || currentProgram == null) throw new Exception("Invalid fixed exporter arguments");
        String operation=args[0], selector=args[2];
        int offset=Integer.parseInt(args[3]), limit=Integer.parseInt(args[4]);
        if (offset<0 || offset>SCAN_LIMIT || limit<1 || limit>100) throw new Exception("Invalid bounds");
        String body;
        if (operation.equals("analyze")) {
            body="\"name\":"+quote(currentProgram.getName())+",\"language\":"+quote(currentProgram.getLanguageID().toString())+
                 ",\"format\":"+quote(currentProgram.getExecutableFormat())+",\"image_base\":"+quote(currentProgram.getImageBase().toString())+
                 ",\"function_count\":"+currentProgram.getFunctionManager().getFunctionCount();
        } else if (operation.equals("functions") || operation.equals("strings")) {
            String query=selector.equals("-")?"":new String(Base64.getDecoder().decode(selector),StandardCharsets.UTF_8).toLowerCase(Locale.ROOT);
            List<String> rows=new ArrayList<>(); int scanned=0,matched=0;
            if (operation.equals("functions")) {
                FunctionIterator items=currentProgram.getFunctionManager().getFunctions(true);
                while(items.hasNext() && scanned<SCAN_LIMIT) {
                    monitor.checkCancelled(); Function function=items.next(); scanned++;
                    if(!function.getName().toLowerCase(Locale.ROOT).contains(query))continue;
                    if(matched++>=offset && rows.size()<limit)
                        rows.add("{\"address\":"+quote(function.getEntryPoint().toString())+",\"name\":"+quote(trim(function.getName(),512))+
                                 ",\"size_bytes\":"+function.getBody().getNumAddresses()+",\"external\":"+function.isExternal()+"}");
                }
            } else {
                DataIterator items=currentProgram.getListing().getDefinedData(true);
                while(items.hasNext() && scanned<SCAN_LIMIT) {
                    monitor.checkCancelled(); Data data=items.next(); scanned++;
                    if(!data.hasStringValue())continue;
                    Object value=data.getValue(); if(!(value instanceof String))continue;
                    String text=(String)value;
                    if(!text.toLowerCase(Locale.ROOT).contains(query))continue;
                    if(matched++>=offset && rows.size()<limit)
                        rows.add("{\"address\":"+quote(data.getAddress().toString())+",\"text\":"+quote(trim(text,512))+",\"text_truncated\":"+(text.length()>512)+"}");
                }
            }
            body="\"items\":["+String.join(",",rows)+"],\"offset\":"+offset+",\"returned\":"+rows.size()+
                 ",\"matching_scanned\":"+matched+",\"records_scanned\":"+scanned+",\"scan_truncated\":"+(scanned>=SCAN_LIMIT)+
                 ",\"has_more\":"+(matched>offset+rows.size());
        } else {
            Address address=currentProgram.getAddressFactory().getAddress(selector);
            if(address==null)throw new Exception("Address does not exist");
            if(operation.equals("decompile")) {
                Function function=currentProgram.getFunctionManager().getFunctionAt(address);
                if(function==null)throw new Exception("Choose an exact function entry address");
                DecompInterface decompiler=new DecompInterface();
                try {
                    if(!decompiler.openProgram(currentProgram))throw new Exception("Decompiler unavailable");
                    DecompileResults result=decompiler.decompileFunction(function,30,monitor);
                    if(result==null || !result.decompileCompleted() || result.getDecompiledFunction()==null)throw new Exception("Decompilation did not complete");
                    String text=result.getDecompiledFunction().getC();
                    body="\"address\":"+quote(address.toString())+",\"name\":"+quote(trim(function.getName(),512))+
                         ",\"pseudocode\":"+quote(trim(text,24000))+",\"truncated\":"+(text.length()>24000);
                } finally {decompiler.dispose();}
            } else if(operation.equals("xrefs")) {
                ReferenceIterator references=currentProgram.getReferenceManager().getReferencesTo(address);
                List<String> rows=new ArrayList<>();int scanned=0;
                while(references.hasNext() && scanned<10000) {
                    monitor.checkCancelled();Reference ref=references.next();scanned++;
                    if(rows.size()>=limit)continue;
                    Function function=currentProgram.getFunctionManager().getFunctionContaining(ref.getFromAddress());
                    rows.add("{\"from\":"+quote(ref.getFromAddress().toString())+",\"to\":"+quote(ref.getToAddress().toString())+
                             ",\"type\":"+quote(ref.getReferenceType().toString())+",\"function\":"+(function==null?"null":quote(trim(function.getName(),512)))+"}");
                }
                body="\"address\":"+quote(address.toString())+",\"items\":["+String.join(",",rows)+"],\"references_scanned\":"+scanned+
                     ",\"truncated\":"+(scanned>rows.size() || references.hasNext());
            } else throw new Exception("Operation not allowed");
        }
        String result="{\"schema_version\":1,\"ok\":true,\"operation\":"+quote(operation)+","+body+"}";
        if(result.getBytes(StandardCharsets.UTF_8).length>512*1024)throw new Exception("Result exceeds evidence budget");
        Files.writeString(Path.of(args[1]),result,StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW);
    }
}
