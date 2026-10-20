"""Static source inventory, lexical Python relationships, and review metrics.

No repository modules are imported and no analyzed code is executed. Dynamic
calls are retained as unresolved expressions rather than guessed edges.
"""
import argparse
import ast
import builtins
import hashlib
import json
import re
from pathlib import Path

EXTENSIONS = {'.py', '.js', '.ps1', '.sh'}


def is_test(path):
    return Path(path).name.lower().startswith(('test_', 'test-'))


def owned_walk(node):
    """Walk one lexical body, excluding bodies of nested definitions."""
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            yield from owned_walk(child)


def build(root, paths, revision, js_index=None):
    files, symbols, edges, unresolved = [], [], [], []
    trees, lookup, modules, by_file = {}, {}, {}, {}
    paths=sorted(set(paths))
    for path in paths:
        source=(root/path).read_text(encoding='utf-8-sig')
        raw=(root/path).read_bytes()
        file={'id':path,'path':path,'kind':'file','language':Path(path).suffix[1:],
              'test':is_test(path),'lines':len(source.splitlines()),'sha256':hashlib.sha256(raw).hexdigest()}
        files.append(file);by_file[path]=[]
        modules.setdefault(Path(path).stem,[]).append(path)
        if path.endswith('.py'):
            tree=ast.parse(source);trees[path]=tree
            file['purpose']=(ast.get_docstring(tree) or '').split('\n')[0]
            def visit(node, scope=(), cls=None):
                for item in ast.iter_child_nodes(node):
                    if isinstance(item,ast.ClassDef):visit(item,scope+(item.name,),item.name)
                    elif isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)):
                        name='.'.join(scope+(item.name,));sid=path+'::'+name
                        body=list(owned_walk(item))
                        decisions=sum(isinstance(n,(ast.If,ast.IfExp,ast.For,ast.AsyncFor,ast.While,ast.ExceptHandler,ast.comprehension)) for n in body)
                        decisions+=sum(len(n.values)-1 for n in body if isinstance(n,ast.BoolOp))
                        decisions+=sum(max(0,len(n.cases)-1) for n in body if isinstance(n,ast.Match))
                        record={'id':sid,'kind':'function','path':path,'symbol':name,'language':'py','test':is_test(path),
                                'line':item.lineno,'end_line':item.end_lineno,'lines':item.end_lineno-item.lineno+1,
                                'complexity_estimate':1+decisions,'class':cls,'scope':list(scope),
                                'signature':ast.unparse(item.args),'purpose':(ast.get_docstring(item) or '').split('\n')[0],
                                'decorators':[ast.unparse(d) for d in item.decorator_list]}
                        symbols.append(record);by_file[path].append(record);lookup[(path,name)]=(record,item)
                        visit(item,scope+(item.name,),cls)
                    else:visit(item,scope,cls)
            visit(tree)
        elif path.endswith('.ps1'):
            for m in re.finditer(r'(?im)^[ \t]*function[ \t]+([\w-]+)[ \t]*(?:\([^)]*\)[ \t]*)?\{',source):
                name=m.group(1);symbols.append({'id':path+'::'+name,'kind':'function','path':path,'symbol':name,
                      'language':'ps1','test':is_test(path),'line':source[:m.start()].count('\n')+1,
                      'lines':None,'complexity_estimate':None,'purpose':'Declaration indexed; PowerShell control flow not parsed.'})
    def module_path(path,name):
        candidates=modules.get(name.split('.')[0],[])
        local=[p for p in candidates if Path(p).parent==Path(path).parent]
        return local[0] if len(local)==1 else candidates[0] if len(candidates)==1 else None
    aliases={}
    for path,tree in trees.items():
        aliases[path]={}
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom) and n.module:
                target=module_path(path,n.module)
                for a in n.names:
                    aliases[path].setdefault(a.asname or a.name,set()).add((target,a.name))
            elif isinstance(n,ast.Import):
                for a in n.names:aliases[path].setdefault(a.asname or a.name,set()).add((module_path(path,a.name),''))
            else:continue
            for target in ([module_path(path,n.module)] if isinstance(n,ast.ImportFrom) else [module_path(path,a.name) for a in n.names]):
                if not target:continue
                edges.append({'source':path,'target':target,'type':'imports','confidence':'static-module','line':n.lineno})
    edge_keys=set()
    def add(source,target,kind,line,confidence):
        key=(source,target,kind,line)
        if key not in edge_keys:
            edge_keys.add(key);edges.append({'source':source,'target':target,'type':kind,'line':line,'confidence':confidence})
    for path,tree in trees.items():
        contexts=[(path,tree,None)] + [(r['id'],n,r) for (p,_),(r,n) in lookup.items() if p==path]
        for caller,node,record in contexts:
            # Module definitions themselves are not calls. Function bodies are
            # analyzed separately so nested callbacks do not inflate parents.
            body=list(owned_walk(node))
            params={a.arg for a in (node.args.posonlyargs+node.args.args+node.args.kwonlyargs)} if record else set()
            bindings=set(params)
            for n in body:
                if isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Del)):bindings.add(n.id)
            def resolve(expression):
                if isinstance(expression,ast.Name):
                    name=expression.id
                    # Lexical nested and same-module function resolution first.
                    scope=record['scope'] if record else []
                    for i in range(len(scope),-1,-1):
                        key=(path,'.'.join(scope[:i]+[name]))
                        if key in lookup and name not in bindings:return lookup[key][0]['id'],'lexical'
                    options=aliases[path].get(name,set())
                    resolved={p+'::'+s for p,s in options if p and (p,s) in lookup}
                    if len(resolved)==1 and name not in bindings:return next(iter(resolved)),'import-alias-candidate'
                elif isinstance(expression,ast.Attribute):
                    if isinstance(expression.value,ast.Name):
                        base=expression.value.id
                        if base in ('self','cls') and record and record['class']:
                            cls_scope=record['scope'][:record['scope'].index(record['class'])+1]
                            key=(path,'.'.join(cls_scope+[expression.attr]))
                            if key in lookup:return lookup[key][0]['id'],'same-class'
                        options=aliases[path].get(base,set())
                        resolved={p+'::'+expression.attr for p,s in options if p and not s and (p,expression.attr) in lookup}
                        if len(resolved)==1 and base not in bindings:return next(iter(resolved)),'module-alias-candidate'
                return None,None
            callees={id(n.func) for n in body if isinstance(n,ast.Call)}
            for n in body:
                if isinstance(n,ast.Call):
                    target,confidence=resolve(n.func)
                    if target:add(caller,target,'calls',n.lineno,confidence)
                    else:
                        text=ast.unparse(n.func)
                        if not isinstance(n.func,ast.Name) or text not in vars(builtins):
                            unresolved.append({'source':caller,'expression':text,'line':n.lineno})
                elif isinstance(n,(ast.Name,ast.Attribute)) and isinstance(n.ctx,ast.Load) and id(n) not in callees:
                    target,confidence=resolve(n)
                    if target:add(caller,target,'references',n.lineno,confidence)
    if js_index:
        for row in js_index:
            record=dict(row);record['test']=is_test(record['path'].split(' [inline')[0]);record['kind']='function'
            symbols.append(record)
            unresolved.extend({'source':record['id'],'expression':c['expression'],'line':c['line'],'language':'js'} for c in record.pop('unresolved_calls',[]))
            edges.extend(record.pop('edges',[]))
    # Remove duplicate imports, preserve call-site evidence.
    unique={json.dumps(e,sort_keys=True):e for e in edges};edges=list(unique.values())
    incoming={r['id']:[] for r in symbols}
    for edge in edges:
        if edge['target'] in incoming:incoming[edge['target']].append(edge)
    for record in symbols:
        refs=incoming[record['id']]
        record['static_callers']=sorted({e['source'] for e in refs if e['type']=='calls'})
        record['static_references']=sorted({e['source'] for e in refs if e['type']=='references'})
        # No-caller means review candidate only. Entry points, callbacks,
        # framework hooks and string dispatch are not proven dead code.
        record['no_static_incoming']=not refs
    return {'schema_version':1,'revision':revision,
            'method':'Python AST lexical/module/self calls; JS parser index; PowerShell declarations. Static candidates, not runtime proof.',
            'limitations':['Import aliases are file-scoped candidate mappings, not Python whole-program type analysis.',
                          'Instance dispatch, dynamic imports, decorators, string routes, injected callbacks and external callers may be unresolved.',
                          'No static incoming references does not prove a function is unused.',
                          'Branch-count complexity estimate is a prioritization metric, not formal McCabe complexity.',
                          'Inline JavaScript line numbers are approximate relative to the Python HTML literal.'],
            'files':files,'symbols':symbols,'edges':edges,'unresolved_calls':unresolved,
            'counts':{'files':len(files),'symbols':len(symbols),'relationships':len(edges),'unresolved_calls':len(unresolved)}}


def write_index(graph, destination):
    lines=['# Function and script index\n\nPinned application source: `'+graph['revision']+'`. '+str(graph['counts']['files'])+' scripts and '+str(graph['counts']['symbols'])+' function/callback declarations. Python AST and JavaScript parser inventory; PowerShell declarations only. Inline JavaScript line locations are approximate. Callers/references are static candidates, not execution coverage or proof of dead code. Generated/embedded Python programs are not independently parsed. Analysis utilities added with these documents are outside the pinned application snapshot.\n\n']
    for file in graph['files']:
        path=file['path'];functions=[s for s in graph['symbols'] if s['path'].split(' [inline')[0]==path]
        lines+=['## '+path+'\n\n'+(file.get('purpose') or 'Script/module inventory; inspect pinned source for complete behavior.')+'\n\n']
        if not functions:lines+=['No named declarations indexed; inspect top-level script flow.\n\n'];continue
        lines+=['| Function / callback | Source line | Span | Branch estimate | Callers / references |\n| --- | ---: | ---: | ---: | ---: |\n']
        for s in functions:
            name=s['symbol'].replace('|','\\|').replace('`','\\`')
            lines+=[f"| `{name}` | [L{s['line']}](../{path}#L{s['line']}) | {s.get('lines') or '—'} | {s.get('complexity_estimate') if s.get('complexity_estimate') is not None else '—'} | {len(s['static_callers'])} / {len(s['static_references'])} |\n"]
        lines+=['\n']
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(''.join(lines),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--manifest',type=Path,help='Optional pinned JSON {commit,files:[{path,sha}]} source inventory')
    parser.add_argument('--revision',default='working-tree')
    parser.add_argument('--js-index',type=Path)
    parser.add_argument('--runtime-links',type=Path)
    parser.add_argument('--index-output',type=Path)
    parser.add_argument('--output',type=Path,default=Path('docs/graph/system-graph.json'))
    args=parser.parse_args();root=args.root.resolve()
    if args.manifest:
        manifest=json.loads(args.manifest.read_text());paths=[r['path'] for r in manifest['files'] if Path(r['path']).suffix in EXTENSIONS];revision=manifest['commit']
        for row in manifest['files']:
            if row['path'] not in paths:continue
            raw=(root/row['path']).read_bytes();actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if actual!=row['sha']:raise ValueError('Pinned source mismatch: '+row['path'])
    else:
        paths=[p.relative_to(root).as_posix() for base in ('tools','automation') for p in (root/base).rglob('*') if p.is_file() and p.suffix in EXTENSIONS and '__pycache__' not in p.parts and 'analysis' not in p.relative_to(root).parts];revision=args.revision
    graph=build(root,paths,revision,json.loads(args.js_index.read_text()) if args.js_index else None)
    if args.runtime_links:
        graph['runtime_links']=json.loads(args.runtime_links.read_text())
    if args.index_output:
        write_index(graph,args.index_output)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(graph,separators=(',',':')),encoding='utf-8')
    print(json.dumps(graph['counts']))


if __name__=='__main__':main()
