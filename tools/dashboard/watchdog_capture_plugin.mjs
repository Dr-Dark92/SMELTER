/* Private prompt capture only. A separate controller owns reservations/retries. */
import {readFile,stat,realpath} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {spawn} from 'node:child_process';

export default async function SmelterWatchdog({directory,serverUrl},options={}){
 const root=await realpath(options.root);
 let started=null;
 const key=value=>String(value||'').replaceAll('\\','/').replace(/\/+/g,'/').replace(/\/$/,'').toLowerCase();
 async function bound(sessionID){
  try{
   const path=join(root,'.smelter','native-progress','state.json');if((await stat(path)).size>2*1024*1024||await realpath(path)!==resolve(path))return false;
   const state=JSON.parse(await readFile(path,'utf8'));
   return resolve(state.source_root)===root&&state.enabled&&state.binding?.session_id===sessionID&&key(state.binding.directory)===key(directory);
  }catch{return false}
 }
 async function runtime(){
  const path=join(root,'.smelter','watchdog','runtime.json');
  if((await stat(path)).size>4096||await realpath(path)!==resolve(path))throw new Error('Watchdog state unavailable');
  const value=JSON.parse(await readFile(path,'utf8'));
  if(resolve(value.source_root)!==root||!Number.isInteger(value.port)||value.port<1||value.port>65535||typeof value.credential!=='string')throw new Error('Watchdog identity mismatch');
  return value;
 }
 async function ensureService(){
  if(typeof options.python!=='string')return;
  const path=join(root,'.smelter','watchdog','config.json');
  if((await stat(path)).size>4096)return;
  const value=JSON.parse(await readFile(path,'utf8'));
  if(value.enabled!==true||resolve(value.source_root)!==root)return;
  if(!started)started=new Promise(resolveStart=>{
   const child=spawn(options.python,[join(root,'tools','setup','manage_task_watchdog.py'),'start','--root',root],
    {cwd:root,stdio:'ignore',windowsHide:true,shell:false});
   const timer=setTimeout(()=>resolveStart(),6000);timer.unref();
   child.once('error',()=>{clearTimeout(timer);resolveStart()});child.once('exit',()=>{clearTimeout(timer);resolveStart()});
  });
  try{await started}finally{started=null}
 }
 async function post(route,value){
  const active=await runtime();
  const response=await fetch('http://127.0.0.1:'+active.port+route,{method:'POST',redirect:'error',signal:AbortSignal.timeout(3000),
   headers:{'Content-Type':'application/json',Authorization:'Bearer '+active.credential},body:JSON.stringify(value)});
  if(!response.ok)throw new Error('Watchdog capture/admission rejected');
  return response.json();
 }
 return {
  'chat.message':async(input,output)=>{
   const messageID=output.message?.id||input.messageID;
   const retry=String(messageID||'').startsWith('msg_smelter_wd_');
   if(!await bound(input.sessionID)){if(retry)throw new Error('SMELTER watchdog task is no longer bound');return}
   const parts=output.parts||[];
   if(!retry&&!parts.some(p=>p.type==='text'&&!p.synthetic))return;
   try{
    await ensureService();
    const endpoint=new URL(serverUrl);
    if(endpoint.protocol!=='http:'||!['localhost','127.0.0.1'].includes(endpoint.hostname))return;
    const requestOptions={};for(const name of ['tools','system','format'])if(output.message?.[name]!==undefined)requestOptions[name]=output.message[name];
    await post('/capture',{session_id:input.sessionID,message_id:messageID,directory,request_options:requestOptions,
      created_ms:output.message?.time?.created,text:parts.filter(p=>p.type==='text'&&!p.synthetic).map(p=>p.text).join('\n'),
      has_attachments:parts.some(p=>p.type==='file'||p.type==='subtask'),model:input.model||output.message?.model,
      agent:input.agent||output.message?.agent,variant:input.variant||output.message?.variant,
      server_port:Number(endpoint.port||80),native_pid:process.pid});
   }catch(error){started=null;if(retry)throw new Error('SMELTER watchdog continuation is no longer admitted');}
  },
  event:async({event})=>{
   if(event.type==='session.error'&&event.properties?.error?.name==='MessageAbortedError'){
    if(!await bound(event.properties.sessionID))return;
    try{await post('/cancel',{session_id:event.properties.sessionID})}catch{}
   }
  },
 };
}
