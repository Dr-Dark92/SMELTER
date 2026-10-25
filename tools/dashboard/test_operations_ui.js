const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

class Node {
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.attributes={};this.classList={add(){}};this.disabled=false;this.text='';}
 append(...nodes){this.children.push(...nodes)}
 set textContent(value){this.text=value;this.children=[]}
 get textContent(){return this.text+this.children.map(x=>x.textContent).join('')}
 setAttribute(key,value){this.attributes[key]=value}
}
const flatten=node=>[node,...node.children.flatMap(flatten)];
function fixture(sandboxConfigured={python_image:null,node_image:null,opencode_image:null,cpp_image:null}){
 const panels=[];const calls=[];const timers=[];let confirmation=true;let failure=null;let serial=0;
 const settings={activate(){},addPanel(id,label,section){section.id=id;panels.push(section);return new Node('button')}};
 const context={module:{exports:{}},SmelterSettings:{current:settings},setTimeout:callback=>timers.push(callback),confirm:()=>confirmation,Date};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'operations_ui.js'),'utf8')+';module.exports=SmelterOperations;',context);
 const api=async(route,method,body)=>{calls.push({route,method,body});if(failure)throw Error(failure);if(route==='/api/sandbox'&&!method)return {configured:sandboxConfigured,reason:'fixture',boundary:'fixture'};return body?.action==='plan'?{plan_id:'plan-'+(++serial),files:1,expires_in_seconds:600}:{removed:1}};
 context.module.exports.mount(api,{createElement:tag=>new Node(tag)});
 const all=panels.flatMap(flatten);const button=label=>all.find(n=>n.tag==='button'&&n.textContent===label);
 const age=all.find(n=>n.attributes['aria-label']==='Retention age in days');age.valueAsNumber=30;
 return {calls,timers,button,age,setConfirmation(value){confirmation=value},fail(value){failure=value}};
}

test('consumed plan stays disabled after the asynchronous button handler finishes',async()=>{
 const f=fixture(),apply=f.button('Apply reviewed retention plan');assert.equal(apply.disabled,true);
 await f.button('Preview retention plan').onclick();assert.equal(apply.disabled,false);
 await apply.onclick();assert.equal(apply.disabled,true);
 await apply.onclick();assert.equal(f.calls.filter(x=>x.body?.action==='prune').length,1);
 await f.button('Preview retention plan').onclick();assert.equal(apply.disabled,false);
});

test('cancellation retains the reviewed plan but ambiguous deletion failure consumes it',async()=>{
 const f=fixture(),apply=f.button('Apply reviewed retention plan');await f.button('Preview retention plan').onclick();
 f.setConfirmation(false);await apply.onclick();assert.equal(apply.disabled,false);assert.equal(f.calls.filter(x=>x.body?.action==='prune').length,0);
 f.setConfirmation(true);f.fail('connection lost');await apply.onclick();assert.equal(apply.disabled,true);
 f.fail(null);await apply.onclick();assert.equal(f.calls.filter(x=>x.body?.action==='prune').length,1);
});

test('editing age or failing to get a new preview invalidates the old plan',async()=>{
 const f=fixture(),apply=f.button('Apply reviewed retention plan'),preview=f.button('Preview retention plan');
 await preview.onclick();f.age.oninput();assert.equal(apply.disabled,true);
 await preview.onclick();f.fail('preview failed');await preview.onclick();assert.equal(apply.disabled,true);
});

test('expiry disables its own plan and cannot invalidate a newer plan',async()=>{
 const f=fixture(),apply=f.button('Apply reviewed retention plan'),preview=f.button('Preview retention plan');
 await preview.onclick();await preview.onclick();f.timers[0]();assert.equal(apply.disabled,false);
 f.timers[1]();assert.equal(apply.disabled,true);
});

test('invalid retention age is rejected before a request',async()=>{
 const f=fixture();for(const value of [NaN,0,1.5,3651]){f.age.valueAsNumber=value;await f.button('Preview retention plan').onclick()}
 assert.equal(f.calls.length,0);assert.equal(f.button('Apply reviewed retention plan').disabled,true);
});

test('new image field is omitted for older backends and saved for updated ones',async()=>{
 for(const supported of [false,true]){
  const config={python_image:null,node_image:null,opencode_image:null,cpp_image:null};
  if(supported)config.engine_image='sha256:'+'a'.repeat(64);
  const f=fixture(config);await f.button('Check confined runner').onclick();
  await f.button('Save confined runner configuration').onclick();
  const saved=f.calls.find(x=>x.body?.action==='save').body.configuration;
  assert.equal('engine_image' in saved,supported);
  if(supported)assert.equal(saved.engine_image,config.engine_image);
 }
});
