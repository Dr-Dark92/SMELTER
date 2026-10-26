const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
class Node{
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.attributes={};this.value='';this.checked=false;this.text=''}
 append(...nodes){this.children.push(...nodes)}replaceChildren(...nodes){this.children=nodes}
 setAttribute(key,value){this.attributes[key]=value}
 set textContent(value){this.text=String(value);this.children=[]}get textContent(){return this.text+this.children.map(n=>n.textContent).join('')}
}
const flatten=node=>[node,...node.children.flatMap(flatten)];
function fixture(unavailable=false){
 const parent=new Node('div'),calls=[];let web={schema_version:1,mode:'docs',domains:['example.com'],cache_seconds:600};let memory={schema_version:1,enabled:true,auto_capture:true,ram_mib:64,context_chars:12000};
 let note={id:'note',title:'<img src=x>',text:'prior finding',sources:['source'],origin:'model',confidence:'unverified',sha256:'oldhash',kind:'note',tags:[]};
 const api=async(route,method,body)=>{calls.push({route,method,body});if(unavailable)throw Error('Endpoint unavailable');
  if(route==='/api/web-access'){if(body)web=body.settings;return {settings:web,revision:'webrev',provider:{status:'ready',version:'pinned'}}}
  if(!body)return {settings:memory,revision:'memrev',notes:note?1:0,file_bytes:100,ram_bytes_estimate:0,recent:note?[note]:[]};
  if(body.action==='save_settings')memory=body.settings;
  if(body.action==='read')return note;
  if(body.action==='remember'){note={...note,...body,origin:'user',confidence:'user_supplied',sha256:'newhash'};return {note}}
  if(body.action==='forget')note=null;
  return {notes:note?[note]:[]};
 };
 const context={module:{exports:{}},URL,SmelterSettings:{current:{addPanel(id,label,section){parent.append(section);return new Node('button')},activate(){}}}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'knowledge_ui.js'),'utf8'),context);
 const knowledge=context.module.exports;const ui=knowledge.mount(api,{createElement:tag=>new Node(tag),createTextNode:text=>{const n=new Node('text');n.textContent=text;return n}});
 const find=label=>flatten(parent).find(n=>n.tag==='button'&&n.textContent===label);
 return {knowledge,ui,parent,calls,find};
}
test('project settings enable capabilities and Off removes the web grant',async()=>{
 const f=fixture();await f.ui.refresh();assert.equal(f.knowledge.collect().web_read,true);assert.equal(f.knowledge.collect().project_memory,true);
 assert.equal(flatten(f.parent).find(n=>n.tag==='select').attributes['aria-label'],'Project access');
 flatten(f.parent).find(n=>n.tag==='select').value='off';await f.find('Save internet settings').onclick();assert.equal(f.knowledge.collect().web_read,undefined);
 const saved=f.calls.find(c=>c.body?.action==='save');assert.equal(saved.body.expected_revision,'webrev');
});
test('old backends receive no new knowledge fields',async()=>{
 const f=fixture(true);await f.ui.refresh();assert.equal(Object.keys(f.knowledge.collect()).length,0);
});
test('memory edit and forget preserve exact note identity/hash',async()=>{
 const f=fixture();await f.ui.refresh();await f.find('<img src=x> · unverified').onclick();await f.find('Save note').onclick();
 const saved=f.calls.find(c=>c.body?.action==='remember').body;assert.equal(saved.id,'note');assert.equal(saved.expected_sha256,'oldhash');assert.equal(saved.origin,undefined);
 await f.find('Forget note').onclick();const forgotten=f.calls.find(c=>c.body?.action==='forget').body;assert.equal(forgotten.expected_sha256,'newhash');
});
test('clear RAM and reindex do not request deletion of notes',async()=>{
 const f=fixture();await f.ui.refresh();await f.find('Clear RAM cache').onclick();await f.find('Rebuild memory index').onclick();
 assert.ok(f.calls.some(c=>c.body?.action==='clear_ram'));assert.ok(f.calls.some(c=>c.body?.action==='reindex'));assert.ok(!f.calls.some(c=>c.body?.action==='forget'));
});
test('source cards accept HTTPS links only and render titles/snippets as text',()=>{
 const f=fixture();const parent=new Node('div');const doc={createElement:tag=>new Node(tag)};
 f.knowledge.sources(parent,[{result:{status:'web_completed',action:'fetch',cached:true,sources:[{url:'javascript:bad()'},{url:'https://user:pass@example.com'},{url:'https://example.com/docs',title:'<script>bad()</script>',snippet:'<img onerror=bad()>'}]}}],doc);
 const nodes=flatten(parent),links=nodes.filter(n=>n.tag==='a');assert.equal(links.length,1);assert.equal(links[0].textContent,'<script>bad()</script>');assert.equal(links[0].rel,'noopener noreferrer');assert.ok(nodes.some(n=>n.textContent.includes('cached')));
});
