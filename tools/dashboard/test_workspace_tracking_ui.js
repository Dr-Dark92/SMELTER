const {test}=require('node:test');
const assert=require('node:assert/strict');
const {render,renderGraph}=require('./workspace_tracking_ui.js');
class Node {
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.style={};}
 set textContent(x){this.text=x;this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(x=>x.textContent).join('');}
 append(...x){this.children.push(...x);}
 replaceChildren(...x){this.children=[...x];}
 setAttribute(k,v){this.attrs[k]=v;}
}
const doc={createElement:tag=>new Node(tag),createElementNS:(_ns,tag)=>new Node(tag)};
const flatten=n=>[n,...n.children.flatMap(flatten)];
const value=()=>({workspace_root:'C:\\SMELTERV2\\coding\\task',source_root:'C:\\SMELTER',storage:'host_directory',tests_use:'read-only Docker snapshots',updated_at:'now',operation:'patch applied',revision:'a'.repeat(64),matching_files:1,total_files:1,has_more:false,files:[{relative_path:'mods/<script>.lua',physical_path:'C:\\coding\\mods\\<script>.lua',sha256:'b'.repeat(64),status:'modified'}],tests:[{profile:'lua',stage:'GREEN',current:false}],history:[],graph:{scope:'Static imports are not behavior coverage.',nodes:[{id:'workspace',kind:'workspace',label:'copy'},{id:'f1',kind:'file',label:'<img onerror=alert(1)>',sha256:'b'.repeat(64)}],edges:[{source:'workspace',target:'f1',kind:'contains',confidence:'observed'}]},mermaid:'flowchart LR\n'});
test('renders exact locations, full hashes and stale receipts as text',()=>{const host=new Node('section');render(value(),host,doc);assert.match(host.textContent,/C:\\SMELTERV2/);assert.match(host.textContent,/b{64}/);assert.match(host.textContent,/stale tree/);assert.equal(flatten(host).filter(n=>['script','img'].includes(n.tag)).length,0);render({...value(),indexed:false},host,doc);assert.match(host.textContent,/No index yet/);assert.equal(flatten(host).filter(n=>n.tag==='table').length,0)});
test('SVG relations keep scope, safe labels and portable Mermaid source',()=>{const host=new Node('section');renderGraph(value(),host,doc);const nodes=flatten(host);assert.equal(nodes.filter(n=>n.tag==='svg').length,1);assert.match(host.textContent,/not behavior coverage/);assert.match(host.textContent,/<img onerror/);assert.equal(nodes.find(n=>n.tag==='textarea').value,'flowchart LR\n');assert.equal(nodes.filter(n=>n.tag==='path'&&n.attrs['marker-end']).length,1);assert.equal(nodes.filter(n=>n.tag==='marker').length,3)});
