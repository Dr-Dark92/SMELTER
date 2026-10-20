const {test} = require('node:test');
const assert = require('node:assert/strict');
const {mount} = require('./file_activity.js');

class Node {
  constructor(tag) { this.tag = tag; this.children = []; this.value = ''; this.dataset = {}; this.attrs = {}; this.scrollTop = 0; this.scrollHeight = 100; this.clientHeight = 100; }
  set textContent(value) { this.text = value; this.children = []; }
  get textContent() { return (this.text || '') + this.children.map(x=>x.textContent).join(''); }
  append(...nodes) { this.children.push(...nodes); }
  setAttribute(key, value) { this.attrs[key] = value; }
}
const doc = {createElement: tag => new Node(tag)};
const flatten = n => [n, ...n.children.flatMap(flatten)];
const file = (id, status='read') => ({id, path:id, area:'destination', status, before:'<script>old()</script>', after:null, draft:''});

test('six files render six expandable originals and read-only code boxes', () => {
  const root = new Node('section'); const view = mount(root, doc);
  view.update(Array.from({length:6}, (_,i)=>file('file'+i)));
  const nodes = flatten(root);
  assert.equal(nodes.filter(n=>n.tag==='article').length, 6);
  assert.equal(nodes.filter(n=>n.tag==='textarea' && n.readOnly).length, 6);
  assert.equal(nodes.filter(n=>n.tag==='details').length, 12);
  assert.ok(!nodes.some(n=>n.tag==='script'));
  assert.match(root.textContent, /6 files/);
});

test('updates reuse the card, preserve disclosure and separate draft from saved code', () => {
  const root = new Node('section'); const view = mount(root, doc);
  view.update([file('app.py')]);
  const original = flatten(root).find(n=>n.tag==='details'); original.open = true;
  view.update([{...file('app.py','writing'),draft:'<img onerror=alert(1)>'}]);
  let nodes = flatten(root);
  assert.equal(nodes.filter(n=>n.tag==='article').length,1);
  assert.equal(nodes.find(n=>n.tag==='details'),original);
  assert.equal(original.open,true);
  assert.match(root.textContent,/not confirmed saved/);
  assert.equal(nodes.find(n=>n.tag==='textarea').value,'<img onerror=alert(1)>');
  assert.ok(!nodes.some(n=>n.tag==='img'));
  view.update([{...file('app.py','saved'),after:'saved code'}]);
  assert.equal(flatten(root).find(n=>n.tag==='textarea').value,'saved code');
  assert.match(root.textContent,/Updated file · saved/);
  view.update([{...file('app.py','error'),after:'saved code',draft:'failed draft',error:'Hash mismatch'}]);
  assert.equal(flatten(root).find(n=>n.tag==='textarea').value,'failed draft');
  assert.match(root.textContent,/Hash mismatch/);
  assert.match(root.textContent,/Last confirmed saved version/);
});
