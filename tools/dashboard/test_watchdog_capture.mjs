import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,realpath,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createServer} from 'node:http';
import capturePlugin from './watchdog_capture_plugin.mjs';

async function fixture(t){
 const created=await mkdtemp(join(tmpdir(),'smelter-watchdog-')),root=await realpath(created);
 // Only remove the exact task-created temporary directory.
 t.after(async()=>{assert.equal(await realpath(created),root);await rm(root,{recursive:true,force:true})});
 await mkdir(join(root,'.smelter','native-progress'),{recursive:true});await mkdir(join(root,'.smelter','watchdog'));
 const directory='C:/Melty/bound',requests=[];let reject=false;
 const server=createServer((req,res)=>{let raw='';req.on('data',s=>raw+=s);req.on('end',()=>{requests.push({path:req.url,auth:req.headers.authorization,body:JSON.parse(raw)});res.writeHead(reject?409:200,{'Content-Type':'application/json'});res.end(JSON.stringify({status:'captured'}))})});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>server.close(resolve)));
 await writeFile(join(root,'.smelter','native-progress','state.json'),JSON.stringify({source_root:root,enabled:true,binding:{session_id:'ses_bound',directory}}));
 await writeFile(join(root,'.smelter','watchdog','runtime.json'),JSON.stringify({source_root:root,port:server.address().port,credential:'fixture-private-key'}));
 const hooks=await capturePlugin({directory,serverUrl:new URL('http://127.0.0.1:58344')},{root});
 return {hooks,requests,reject(){reject=true},input:{sessionID:'ses_bound',agent:'build',model:{providerID:'ollama',modelID:'qwen-fixture'},variant:'smelter-tools'},
  output:{message:{id:'msg_human',time:{created:Date.now()}},parts:[{type:'text',text:'Continue my existing task.'}]}};
}

test('bound human prompt is captured privately with exact originating process/model',async t=>{
 const f=await fixture(t);await f.hooks['chat.message'](f.input,f.output);
 assert.equal(f.requests.length,1);const {body,auth}=f.requests[0];assert.equal(auth,'Bearer fixture-private-key');
 assert.equal(body.text,'Continue my existing task.');assert.equal(body.native_pid,process.pid);assert.equal(body.server_port,58344);
 assert.deepEqual(body.model,f.input.model);assert.equal(body.variant,'smelter-tools');
});
test('other sessions and synthetic compaction messages never transmit prompt text',async t=>{
 const f=await fixture(t);await f.hooks['chat.message']({...f.input,sessionID:'ses_other'},f.output);
 await f.hooks['chat.message'](f.input,{...f.output,parts:[{type:'text',text:'synthetic summary',synthetic:true}]});
 assert.equal(f.requests.length,0);
});
test('a rejected watchdog continuation is blocked, while a human prompt can proceed',async t=>{
 const f=await fixture(t);f.reject();await f.hooks['chat.message'](f.input,f.output);
 await assert.rejects(f.hooks['chat.message'](f.input,{...f.output,message:{id:'msg_smelter_wd_reserved'}}),/no longer admitted/);
});
test('attachments are explicitly declared, not silently omitted from recovery',async t=>{
 const f=await fixture(t);await f.hooks['chat.message'](f.input,{...f.output,parts:[...f.output.parts,{type:'file',url:'opaque-local-asset'}]});
 assert.equal(f.requests[0].body.has_attachments,true);
});
