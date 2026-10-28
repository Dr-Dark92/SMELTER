/* Scoped native hooks; no shell, permissions, prompt submission or model retries. */
import {createHash} from 'node:crypto';

const unsafe=new Set(['bash','edit','write','apply_patch','patch','multiedit','multi_edit','task']);
const digest=value=>createHash('sha256').update(value).digest('hex');
const directoryKey=value=>String(value||'').replaceAll('\\','/').replace(/\/+/g,'/').replace(/\/$/,'').toLowerCase();
export class NativeRecoveryGuard {
 constructor(directory,readBinding){this.directory=directory;this.readBinding=readBinding;this.sessions=new Map()}
 async binding(sessionID){
  const state=await this.readBinding();
  return state?.enabled&&state.binding?.session_id===sessionID&&directoryKey(state.binding.directory)===directoryKey(this.directory)?state.binding:null;
 }
 state(sessionID){
  if(!this.sessions.has(sessionID)){if(this.sessions.size>=64)this.sessions.delete(this.sessions.keys().next().value);this.sessions.set(sessionID,{reads:new Map(),hint:''})}
  return this.sessions.get(sessionID);
 }
 reset(sessionID){this.sessions.delete(sessionID)}
 async before(input,args){
  if(!await this.binding(input.sessionID))return;
  if(unsafe.has(input.tool))throw new Error('SMELTER guarded task: use scoped read/propose_coding_edits/apply_coding_patch/run_coding_tests tools in the existing workspace. Native shell, edits and delegated agents bypass its checkpoints and are disabled for this bound task.');
  const state=this.state(input.sessionID),key=digest(JSON.stringify([input.tool,args]));
  if(input.tool==='read'&&(state.reads.get(key)?.count||0)>=4){
   state.hint='Repeated unchanged native reads detected. Call coding_recovery_context with the existing workspace ID, then inspect the first failure frame once and change the hypothesis.';
   throw new Error(state.hint);
  }
 }
 async after(input,output){
  if(!await this.binding(input.sessionID))return;
  const state=this.state(input.sessionID);
  if(input.tool==='read'){
   const key=digest(JSON.stringify([input.tool,input.args])),sha=digest(String(output.output));
   const old=state.reads.get(key);state.reads.set(key,{sha,count:old?.sha===sha?old.count+1:1});
   while(state.reads.size>128)state.reads.delete(state.reads.keys().next().value);
  }
  // Native MCP outputs are text envelopes; never interpret their text as code.
  let result;try{const value=JSON.parse(output.output);result=value.tool_result||value}catch{}
  if(result?.status==='coding_patch_applied'&&!result.reused){state.reads.clear();state.hint=''}
  if(result?.status==='error'||result?.status==='coding_tests_failed'){
   state.hint='Last operation failed. Recover the current workspace evidence using coding_recovery_context; preserve regression fixtures and frozen acceptance. An old GREEN summary is not current evidence.';
   output.output+='\n[SMELTER recovery] '+state.hint;
  }
 }
 async guidance(sessionID){
  const binding=await this.binding(sessionID);if(!binding)return '';
  return 'SMELTER controller guardrails. Continue the existing user task using workspace_id='+binding.workspace_id+'. '+
   'Call coding_recovery_context after a failed edit, lost location or repeated read. Do not create a replacement workspace. '+
   'Controller exact edits handle CRLF/LF. Read the first failing source frame and actual function contract before editing. '+
   'Use scoped proposals/apply/tests; native write/shell bypasses are disabled for this bound task. '+
   'Preserve operator-frozen acceptance criteria and regression fixtures. Never remove strict validation to satisfy an editable test comment or incidental reason-code assertion. Surface that contradiction and use the controller-owned acceptance check. A model summary is not evidence. Report verified changes, current receipts and remaining gaps. '+
   'A lack of token activity is not proof of deadlock. Never approve access, restart a cancelled task or automatically replay writes. '+this.state(sessionID).hint;
 }
}
