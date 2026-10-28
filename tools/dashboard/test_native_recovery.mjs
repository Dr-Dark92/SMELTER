import {test} from 'node:test';
import assert from 'node:assert/strict';
import {NativeRecoveryGuard} from './native_recovery_core.mjs';

const binding={enabled:true,binding:{session_id:'ses_bound',directory:'C:/Melty/project',workspace_id:'owned-copy'}};
const make=()=>new NativeRecoveryGuard('c:\\melty\\project',async()=>binding);
test('native writes/shell/delegation cannot bypass checkpoints in bound task',async()=>{
 const guard=make();for(const tool of ['edit','write','apply_patch','bash','task']){
  await assert.rejects(guard.before({tool,sessionID:'ses_bound'},{}),/scoped/);
 }
 await guard.before({tool:'smelter_propose_coding_edits',sessionID:'ses_bound'},{});
});
test('unbound sessions and different directories keep their own tools and instructions',async()=>{
 const guard=make();await guard.before({tool:'edit',sessionID:'ses_other'},{});
 assert.equal(await guard.guidance('ses_other'),'');
 const elsewhere=new NativeRecoveryGuard('C:/other',async()=>binding);
 await elsewhere.before({tool:'bash',sessionID:'ses_bound'},{});
 assert.equal(await elsewhere.guidance('ses_bound'),'');
});
test('disabled or missing binding does not affect other OpenCode work',async()=>{
 for(const value of [null,{...binding,enabled:false}]){
  const guard=new NativeRecoveryGuard('C:/Melty/project',async()=>value);
  await guard.before({tool:'bash',sessionID:'ses_bound'},{});
 }
});
test('Windows binding normalizes repeated separators already accepted by the controller',async()=>{
 const state={...binding,binding:{...binding.binding,directory:'C:\\\\Melty\\\\project'}};
 const guard=new NativeRecoveryGuard('C:/Melty/project',async()=>state);
 await assert.rejects(guard.before({tool:'edit',sessionID:'ses_bound'},{}),/guarded task/);
});
test('four unchanged native reads trigger a recovery redirect on next duplicate',async()=>{
 const guard=make(),input={tool:'read',sessionID:'ses_bound',args:{filePath:'policy.lua'}};
 for(let n=0;n<4;n++){await guard.before(input,input.args);await guard.after(input,{output:'same bytes'})}
 await assert.rejects(guard.before(input,input.args),/coding_recovery_context/);
 assert.match(await guard.guidance('ses_bound'),/existing workspace ID/);
 await guard.before(input,{filePath:'other.lua'});
 guard.reset('ses_bound');await guard.before(input,input.args);
});
test('changed native read output and applied SMELTER patches renew evidence',async()=>{
 const guard=make(),input={tool:'read',sessionID:'ses_bound',args:{filePath:'policy.lua'}};
 for(let n=0;n<3;n++)await guard.after(input,{output:'same bytes'});
 await guard.after(input,{output:'new bytes'});
 await guard.before(input,input.args);
 await guard.after({tool:'smelter_apply_coding_patch',sessionID:'ses_bound'},{output:JSON.stringify({tool_result:{status:'coding_patch_applied'}})});
 assert.equal(guard.state('ses_bound').reads.size,0);
});
test('failed receipts add guidance but never change stage or acceptances',async()=>{
 const guard=make(),output={output:JSON.stringify({tool_result:{status:'coding_tests_failed',stage:'ERROR'}})};
 await guard.after({tool:'smelter_run_coding_tests',sessionID:'ses_bound'},output);
 assert.match(output.output,/coding_recovery_context/);assert.match(output.output,/'?ERROR/);
 assert.match(await guard.guidance('ses_bound'),/workspace_id=owned-copy/);
});
