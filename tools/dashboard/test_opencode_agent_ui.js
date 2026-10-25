const {test}=require('node:test');
const assert=require('node:assert/strict');
const opencode=require('./opencode_agent_ui.js');

function fixture(value='opencode', response={status:'ready',tasks:0}, options={}) {
  const calls=[];
  const listeners={};
  const engine={value,addEventListener(name,handler){listeners[name]=handler}};
  const chip={hidden:true,firstChild:{textContent:''},dataset:{},attributes:{},
    setAttribute(name,value){this.attributes[name]=value}};
  const approval={checked:false};
  const unrelatedGrant={checked:false};
  const doc={dispatchEvent(){},getElementById(id){
    if(id==='opencodeAgentApprove')return approval;
    return null;
  }};
  const api=async(...args)=>{
    calls.push(args);
    if(response instanceof Error)throw response;
    return response;
  };
  const session=opencode.session(api,{engine,chip,approval,...options},doc);
  return {calls,engine,chip,approval,unrelatedGrant,session,
    async change(value){engine.value=value;await listeners.change();}};
}

const settle=()=>new Promise(resolve=>setImmediate(resolve));

test('saved OpenCode engine starts with the GUI and authorizes its engine session',async()=>{
  const view=fixture();
  await settle();
  assert.deepEqual(view.calls,[['/api/opencode/session','POST',{action:'start'}]]);
  assert.equal(view.approval.checked,true);
  assert.equal(view.chip.hidden,false);
  assert.match(view.chip.firstChild.textContent,/ready/);
  assert.equal(view.chip.dataset.state,'granted');
  assert.equal(view.unrelatedGrant.checked,false,'starting an engine must not grant task tools');
});

test('direct chat startup does not start or approve OpenCode',async()=>{
  const view=fixture('ollama');
  await settle();
  assert.deepEqual(view.calls,[]);
  assert.equal(view.approval.checked,false);
  assert.equal(view.chip.hidden,true);
});

test('selecting OpenCode starts and approves it without a second checkbox step',async()=>{
  const view=fixture('ollama');
  await view.change('opencode');
  assert.deepEqual(view.calls,[['/api/opencode/session','POST',{action:'start'}]]);
  assert.equal(view.approval.checked,true);
  assert.equal(view.chip.hidden,false);
  assert.match(view.chip.firstChild.textContent,/ready/);
});

test('switching to direct chat clears engine approval and hides its session chip',async()=>{
  const view=fixture();
  await settle();
  view.unrelatedGrant.checked=true;
  await view.change('ollama');
  assert.equal(view.approval.checked,false);
  assert.equal(view.chip.hidden,true);
  assert.equal(view.calls.length,1,'switching away must not issue another startup request');
  assert.equal(view.unrelatedGrant.checked,true,'engine choice must preserve explicit task grants');
});

test('automatic startup failure is shown with its reason and can be retried',async()=>{
  const view=fixture('opencode',new Error('Docker is not running'));
  await settle();
  assert.equal(view.chip.hidden,false);
  assert.match(view.chip.firstChild.textContent,/failed/);
  assert.equal(view.chip.dataset.state,'warning');
  assert.match(view.chip.title,/Docker is not running/);
  assert.match(view.chip.attributes['aria-label'],/Docker is not running/);
  await view.chip.onclick();
  assert.equal(view.calls.length,2);
});

test('saved OpenCode waits for authenticated database startup before warming',async()=>{
  let ready=false;
  const view=fixture('opencode',{status:'ready',tasks:0},{ready:()=>ready});
  await settle();
  assert.deepEqual(view.calls,[]);
  assert.equal(view.approval.checked,true,'the saved engine selection is already authorized');
  ready=true;
  await view.session.start();
  assert.deepEqual(view.calls,[['/api/opencode/session','POST',{action:'start'}]]);
  assert.match(view.chip.firstChild.textContent,/ready/);
});

test('a late startup reply cannot show or approve OpenCode after switching away',async()=>{
  let finish;
  const response=new Promise(resolve=>finish=resolve);
  const view=fixture('opencode',response);
  assert.equal(view.calls.length,1);
  assert.equal(view.approval.checked,true);
  await view.change('ollama');
  finish({status:'ready',tasks:0});
  await settle();
  assert.equal(view.engine.value,'ollama');
  assert.equal(view.approval.checked,false);
  assert.equal(view.chip.hidden,true);
  assert.equal(view.calls.length,1);
});

test('duplicate startup triggers share the pending request',async()=>{
  let finish;
  const view=fixture('opencode',new Promise(resolve=>finish=resolve));
  const retry=view.session.start();
  assert.equal(view.calls.length,1);
  finish({status:'ready',tasks:0});
  await retry;
  assert.equal(view.calls.length,1);
  assert.equal(view.chip.hidden,false);
  assert.equal(view.approval.checked,true);
});
