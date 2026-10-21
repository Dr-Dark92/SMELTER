/* Bounded stdio MCP transport inside the no-network agent container.
 * Descriptors are host-owned; tool actions return through the existing queue.
 * No shell, host paths, network connections or model-supplied grants here.
 */
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const args=process.argv.slice(2);
if(args.length && (args.length!==4 || args[0]!=='--manifest' || args[2]!=='--queue')) process.exit(2);
const manifestPath=args[1]||path.join(path.dirname(fileURLToPath(import.meta.url)),'tools.json');
const queue=args[3]||'/run/model-queue';
if(fs.statSync(manifestPath).size>128*1024) process.exit(2);
const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
if(!Array.isArray(manifest.tools)||manifest.tools.length>32) process.exit(2);
const tools=manifest.tools;
const timeout=Math.min(900,Math.max(1,Number(manifest.timeout_seconds)||300))*1000;
const maximum=2*1024*1024;
const active=new Set();
let buffer='',chain=Promise.resolve();

function reply(id,result,error){
  const value={jsonrpc:'2.0',id,...(error?{error}:{result})};
  const line=JSON.stringify(value);
  if(Buffer.byteLength(line)>maximum) process.exit(2);
  process.stdout.write(line+'\n');
}
function cleanup(){for(const item of active){for(const file of item)try{fs.unlinkSync(file)}catch{}}active.clear()}
process.on('SIGTERM',()=>{cleanup();process.exit(0)});
process.on('SIGINT',()=>{cleanup();process.exit(0)});

async function call(name,argumentsValue){
  if(!tools.some(t=>t.name===name)) throw Error('Tool is not approved for this task');
  if(!argumentsValue||typeof argumentsValue!=='object'||Array.isArray(argumentsValue)) throw Error('Tool arguments must be an object');
  const id=randomUUID(),input=path.join(queue,id+'.request'),output=path.join(queue,id+'.response');
  const files=[input,output];active.add(files);
  try{
    const raw=JSON.stringify({id,kind:'mcp',name,arguments:argumentsValue});
    if(Buffer.byteLength(raw)>maximum) throw Error('Tool arguments exceed budget');
    const pending=input+'.pending';
    fs.writeFileSync(pending,raw,{flag:'wx'});fs.renameSync(pending,input);
    const fixed=manifest.tool_timeouts?.[name];
    const operationTimeout=Number.isInteger(fixed)&&fixed>0&&fixed<=440?fixed*1000:timeout;
    const end=Date.now()+operationTimeout;
    while(Date.now()<end){
      if(fs.existsSync(output)){
        if(fs.statSync(output).size>maximum) throw Error('Tool result exceeds budget');
        const response=JSON.parse(fs.readFileSync(output,'utf8'));
        if(!response.mcp_result) throw Error('Invalid tool relay response');
        return response.mcp_result;
      }
      await new Promise(resolve=>setTimeout(resolve,50));
    }
    throw Error('Tool relay timed out; inspect controller receipts before retrying');
  }finally{for(const file of files)try{fs.unlinkSync(file)}catch{}active.delete(files)}
}

async function handle(line){
  let request;
  try{request=JSON.parse(line)}catch{reply(null,null,{code:-32700,message:'Invalid JSON'});return}
  if(!request||typeof request!=='object'||request.jsonrpc!=='2.0') {reply(null,null,{code:-32600,message:'Invalid request'});return}
  if(!Object.hasOwn(request,'id')) return;
  try{
    if(request.method==='initialize'){
      const versions=['2025-11-25','2025-06-18','2025-03-26','2024-11-05'];
      const requested=request.params?.protocolVersion;
      reply(request.id,{protocolVersion:versions.includes(requested)?requested:'2025-06-18',capabilities:{tools:{}},serverInfo:{name:'smelter-task-bridge',version:'1.0.0'}});
    }else if(request.method==='ping') reply(request.id,{});
    else if(request.method==='tools/list') reply(request.id,{tools});
    else if(request.method==='tools/call'){
      let result;
      try{result=await call(request.params?.name,request.params?.arguments??{})}
      catch(error){result={content:[{type:'text',text:String(error.message).slice(0,1000)}],isError:true}}
      reply(request.id,result);
    }else reply(request.id,null,{code:-32601,message:'Method not supported'});
  }catch{reply(request.id,null,{code:-32603,message:'MCP bridge failure'})}
}

process.stdin.setEncoding('utf8');
process.stdin.on('data',chunk=>{
  buffer+=chunk;
  if(Buffer.byteLength(buffer)>maximum) {cleanup();process.exit(2)}
  let newline;
  while((newline=buffer.indexOf('\n'))>=0){
    const line=buffer.slice(0,newline);buffer=buffer.slice(newline+1);
    if(line.trim()) chain=chain.then(()=>handle(line)).catch(()=>process.exit(2));
  }
});
process.stdin.on('end',()=>{chain.finally(()=>{cleanup();process.exit(0)})});
