/* Parse JavaScript without executing it. Babel dependencies are development-only.
   node index_javascript.cjs ROOT MANIFEST OUTPUT [BABEL_BUNDLE]
   With no bundle, install @babel/parser and @babel/traverse in your development
   environment. An optional bundle must export babelParse and traverse. */
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const [root,manifestFile,output,bundle]=process.argv.slice(2);
if(!root||!manifestFile||!output)throw Error('Expected ROOT MANIFEST OUTPUT [BABEL_BUNDLE]');
const parse=bundle?(source)=>require(path.resolve(bundle)).babelParse(source,'source.js',true):(source)=>require('@babel/parser').parse(source,{sourceType:'unambiguous'});
const traverse=bundle?require(path.resolve(bundle)).traverse:require('@babel/traverse').default;
const manifest=JSON.parse(fs.readFileSync(manifestFile,'utf8'));
const rows=[],units=[];
for(const file of manifest.files){
 if(/\.(?:js|mjs|cjs)$/.test(file.path))units.push({path:file.path,source:fs.readFileSync(path.join(root,file.path),'utf8'),offset:0});
 if(file.path.endsWith('.py')){
  // Python AST decodes HTML literals correctly; regex on source would misread escapes.
  const script=`import ast,json,sys,re\nt=ast.parse(open(sys.argv[1],encoding='utf-8-sig').read())\nr=[]\nfor n in ast.walk(t):\n if isinstance(n,ast.Constant) and isinstance(n.value,str) and '<script' in n.value:\n  for m in re.finditer(r'<script(?:\\s[^>]*)?>([\\s\\S]*?)</script>',n.value):\n   if m.group(1).strip():r.append({'source':m.group(1),'offset':n.lineno-1+n.value[:m.start(1)].count('\\n')})\nprint(json.dumps(r))`;
  const decoded=JSON.parse(cp.execFileSync(process.env.PYTHON||'python',['-c',script,path.join(root,file.path)],{encoding:'utf8'}));
  decoded.forEach((u,i)=>units.push({...u,path:file.path+' [inline '+(i+1)+']'}));
 }
}
for(const unit of units){
 const tree=parse(unit.source);const byNode=new Map();
 traverse(tree,{Function(p){
  const n=p.node,parent=p.parent;let name=n.id?.name||n.key?.name||n.key?.value;
  if(!name){if(parent.type==='VariableDeclarator')name=parent.id.name;else if(parent.type==='AssignmentExpression')name=unit.source.slice(parent.left.start,parent.left.end);else if(parent.type==='ObjectProperty')name=parent.key.name||parent.key.value;else name='<callback>';}
  const id=unit.path+'::'+name+'@'+n.loc.start.line+':'+n.loc.start.column;
  const record={id,path:unit.path,symbol:name,language:'js',line:n.loc.start.line+unit.offset,end_line:n.loc.end.line+unit.offset,lines:n.loc.end.line-n.loc.start.line+1,complexity_estimate:1,edges:[],unresolved_calls:[],purpose:'Parsed JavaScript function/callback; dynamic member calls may be unresolved.'};rows.push(record);byNode.set(n,record);
 }});
 function owner(p){let cursor=p.parentPath;while(cursor&&!byNode.has(cursor.node))cursor=cursor.parentPath;return cursor?byNode.get(cursor.node):null}
 function target(p){if(p.node.type!=='Identifier')return null;const binding=p.scope.getBinding(p.node.name);if(!binding)return null;const n=binding.path.node;return byNode.get(n)||byNode.get(n.init)||null}
 traverse(tree,{
  'IfStatement|ConditionalExpression|ForStatement|WhileStatement|DoWhileStatement|ForInStatement|ForOfStatement|CatchClause|LogicalExpression|SwitchCase'(p){const from=owner(p);if(from)from.complexity_estimate++;},
  CallExpression(p){const from=owner(p),to=target(p.get('callee'));if(!from)return;
   if(to)from.edges.push({source:from.id,target:to.id,type:'calls',confidence:'js-lexical-binding',line:p.node.loc.start.line+unit.offset});
   else from.unresolved_calls.push({expression:unit.source.slice(p.node.callee.start,p.node.callee.end).slice(0,200),line:p.node.loc.start.line+unit.offset});
  },
  ReferencedIdentifier(p){if(p.parent.type==='CallExpression'&&p.parent.callee===p.node)return;const from=owner(p),to=target(p);if(from&&to)from.edges.push({source:from.id,target:to.id,type:'references',confidence:'js-lexical-binding',line:p.node.loc.start.line+unit.offset});}
 });
}
fs.writeFileSync(output,JSON.stringify(rows));console.log(JSON.stringify({units:units.length,functions:rows.length}));
