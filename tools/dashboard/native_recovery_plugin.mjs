/* OpenCode 1.19.3 local plugin; only its currently bound SMELTER task is guarded. */
import {readFile,stat,realpath} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {NativeRecoveryGuard} from './native_recovery_core.mjs';

export default async function SmelterRecovery({directory},options={}){
 const root=await realpath(options.root);
 const guard=new NativeRecoveryGuard(directory,async()=>{
  try{
   const path=join(root,'.smelter','native-progress','state.json');
   if((await stat(path)).size>2*1024*1024||await realpath(path)!==resolve(path))return null;
   const state=JSON.parse(await readFile(path,'utf8'));
   return resolve(state.source_root)===root?state:null;
  }catch{return null}
 });
 return {
  'chat.message':async input=>guard.reset(input.sessionID),
  'tool.execute.before':async(input,output)=>guard.before(input,output.args),
  'tool.execute.after':async(input,output)=>guard.after(input,output),
  'experimental.chat.system.transform':async(input,output)=>{const text=await guard.guidance(input.sessionID);if(text)output.system.push(text)},
  'experimental.session.compacting':async(input,output)=>{const text=await guard.guidance(input.sessionID);if(text)output.context.push(text)},
 };
}
