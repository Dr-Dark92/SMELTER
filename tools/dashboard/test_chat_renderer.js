const {test} = require('node:test');
const assert = require('node:assert/strict');
const {parseBlocks, render} = require('./chat_renderer.js');
const {toolState} = require('./chat_renderer.js');

test('coding errors, expected RED and stale review have distinct visual states', () => {
  assert.equal(toolState({status:'coding_tests_failed',stage:'ERROR'}),'error');
  assert.equal(toolState({status:'coding_tests_failed',stage:'RED'}),'warning');
  assert.equal(toolState({status:'coding_workspace_reviewed',all_current_tests_passed:false}),'warning');
  assert.equal(toolState({status:'coding_tests_passed',stage:'GREEN'}),'success');
});

// Tiny inert DOM: HTML assignments are intentionally unsupported.
class Node {
  constructor(tag = '#text', text = '') {
    this.tag = tag; this.children = []; this.value = text;
    this.classList = {add() {}};
  }
  set textContent(value) { this.value = value; this.children = []; }
  get textContent() { return this.value + this.children.map(x => x.textContent).join(''); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; this.value = ''; }
  setAttribute() {}
}
const doc = {createElement: tag => new Node(tag), createTextNode: text => new Node('#text', text)};
const flatten = node => [node, ...node.children.flatMap(flatten)];

test('code fences preserve code and delimit separate paragraphs', () => {
  const blocks = parseBlocks('Before\n\n```fish\nprintf "hello"\n  echo end\n```\nAfter');
  assert.deepEqual(blocks.map(x => x.type), ['paragraph', 'code', 'paragraph']);
  assert.equal(blocks[1].language, 'fish');
  assert.equal(blocks[1].text, 'printf "hello"\n  echo end');
});

test('unterminated fence remains a literal code block', () => {
  assert.equal(parseBlocks('~~~python\nprint("fixture")')[0].text, 'print("fixture")');
});

test('raw HTML, script URLs and event handlers never become markup', () => {
  const root = new Node('div');
  const text = '<script>alert(1)</script>\n<img src=x onerror=alert(2)>\n[link](javascript:alert(3))';
  render(text, root, doc);
  assert.equal(root.textContent, text);
  assert.ok(flatten(root).every(x => !['script', 'img', 'a', 'iframe'].includes(x.tag)));
});

test('heading, lists, inline code and bold use fixed elements', () => {
  const root = new Node('div');
  render('# Title\n\n- **First**\n- `second`\n\n1. Ordered', root, doc);
  const tags = flatten(root).map(x => x.tag);
  for (const tag of ['h3', 'ul', 'ol', 'strong', 'code']) assert.ok(tags.includes(tag));
});

test('code markup is displayed literally and a copy control is provided', () => {
  const root = new Node('div');
  render('```html\n<img src=x onerror=alert(1)>\n```', root, doc);
  const nodes = flatten(root);
  assert.equal(nodes.find(x => x.tag === 'pre').textContent, '<img src=x onerror=alert(1)>');
  assert.equal(nodes.find(x => x.tag === 'button').textContent, 'Copy code');
  assert.ok(!nodes.some(x => x.tag === 'img'));
});
