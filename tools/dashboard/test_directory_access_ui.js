const {test}=require('node:test');
const assert=require('node:assert/strict');
const {mount,permissions}=require('./directory_access_ui.js');
class Node{
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.attributes={};this.textContent='';this.hidden=false;this.disabled=false}
 append(...nodes){this.children.push(...nodes)}
 setAttribute(key,value){this.attributes[key]=value}
}
const flatten=node=>[node,...node.children.flatMap(flatten)];
const request={id:'request-one',job_id:'same-job',directory:'D:\\games\\Example',reason:'Inspect the game archives',policy_revision:'revision'};
function fixture(api){const parent=new Node('div');const ui=mount(parent,api,{createElement:tag=>new Node(tag)});const nodes=flatten(parent);return {ui,box:parent.children[0],nodes,button:label=>nodes.find(n=>n.tag==='button'&&n.textContent===label)}}
const show=(f,r=request)=>f.ui.render({state:'running',pending_access:r});

test('older backends receive no unsupported permission field',()=>{
 assert.deepEqual(permissions(undefined),{});assert.deepEqual(permissions(false),{});
 assert.deepEqual(permissions(true),{access_requests:true});
});

test('request is inline plain text, scoped read-only and survives polling',()=>{
 const f=fixture(async()=>{});assert.equal(f.box.hidden,true);
 show(f,{...request,reason:'<img src=x onerror=bad()>',directory:'D:\\games\\<unsafe>'});
 assert.equal(f.box.hidden,false);assert.equal(f.nodes.find(n=>n.tag==='pre').textContent,'D:\\games\\<unsafe>');
 assert.ok(f.nodes.some(n=>n.textContent==='<img src=x onerror=bad()>'));
 assert.ok(f.nodes.some(n=>n.textContent.includes('Read only')));show(f);assert.equal(f.box.hidden,false);
});
test('allow resumes the exact pending job without starting a new request',async()=>{
 const calls=[];const f=fixture(async(...args)=>{calls.push(args);return {status:'access_granted'}});show(f);
 await f.button('Allow for this task').onclick();assert.equal(f.box.hidden,true);
 assert.deepEqual(calls,[['/api/access-requests','POST',{job_id:'same-job',request_id:'request-one',decision:'allow_task',expected_revision:'revision'}]]);
});
test('remember and deny use distinct decisions and never stop a job',async()=>{
 for(const [label,decision] of [['Remember for this project','allow_project'],['Deny','deny']]){
  const calls=[];const f=fixture(async(...args)=>{calls.push(args);return {status:decision==='deny'?'access_denied':'access_granted'}});show(f);
  await f.button(label).onclick();assert.equal(calls.length,1);assert.equal(calls[0][2].decision,decision);
  assert.equal(calls[0][0],'/api/access-requests');
 }
});
test('duplicate clicks are suppressed while a human decision is being saved',async()=>{
 let finish;let calls=0;const f=fixture(()=>{calls++;return new Promise(resolve=>finish=resolve)});show(f);
 const first=f.button('Allow for this task').onclick();await f.button('Allow for this task').onclick();assert.equal(calls,1);
 assert.equal(f.button('Deny').disabled,true);finish({status:'access_granted'});await first;
});
test('failed API decision keeps the card retryable and terminal jobs clear it',async()=>{
 const f=fixture(async()=>{throw Error('Policy changed')});show(f);await f.button('Allow for this task').onclick();
 assert.equal(f.box.hidden,false);assert.equal(f.button('Allow for this task').disabled,false);assert.ok(f.nodes.some(n=>n.textContent==='Policy changed'));
 f.ui.render({state:'cancelled',pending_access:request});assert.equal(f.box.hidden,true);
});
test('an old response cannot hide the next request',async()=>{
 let finish;const f=fixture(()=>new Promise(resolve=>finish=resolve));show(f);
 const pending=f.button('Allow for this task').onclick();show(f,{...request,id:'request-two',directory:'D:\\next'});
 finish({status:'access_granted'});await pending;
 assert.equal(f.box.hidden,false);assert.equal(f.nodes.find(n=>n.tag==='pre').textContent,'D:\\next');
});
