"""Build a Git-pinned source graph in CI; never import analyzed application code."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emit-base64',action='store_true',help='Emit only generated documentation files for a trusted review client')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    raw=subprocess.check_output(['git','ls-tree','-r','-z','HEAD'],cwd=root)
    rows=[]
    for entry in raw.split(b'\0'):
        if not entry:continue
        metadata,encoded=entry.split(b'\t',1);mode,kind,sha=metadata.decode().split()
        name=encoded.decode('utf-8')
        if kind!='blob' or not name.startswith(('tools/','automation/')) or Path(name).suffix not in {'.py','.js','.mjs','.cjs','.ps1','.sh'}:continue
        rows.append({'path':name,'sha':sha})
    manifest=root/'docs/graph/source-manifest.json'
    manifest.write_text(json.dumps({'commit':revision,'repository':'Dr-Dark92/SMELTER','files':rows},indent=2)+'\n',encoding='utf-8')
    playwright=os.environ.get('SMELTER_TEST_PLAYWRIGHT')
    if not playwright:raise ValueError('Provide the explicit development Playwright module for the Babel bundle')
    bundle=Path(playwright)/'lib/transform/babelBundle.js'
    if not bundle.is_file():raise ValueError('Development Babel bundle is missing')
    def run(*command):subprocess.run(command,cwd=root,check=True)
    with tempfile.TemporaryDirectory(prefix='smelter-graph-') as temporary:
        js=Path(temporary)/'javascript.json'
        run('node','tools/analysis/index_javascript.cjs',str(root),str(manifest),str(js),str(bundle))
        run(sys.executable,'tools/analysis/build_system_graph.py','--manifest',str(manifest),'--js-index',str(js),'--runtime-links','docs/graph/runtime-links.json','--index-output','docs/FUNCTION_INDEX.md')
    run(sys.executable,'tools/analysis/render_system_graph.py','docs/graph/system-graph.json','docs/graph/system-graph.html')
    graph=json.loads((root/'docs/graph/system-graph.json').read_text(encoding='utf-8'))
    meta={'revision':revision,'counts':graph['counts'],'runtime_links':len(graph['runtime_links'])}
    print('SMELTER_GRAPH_META|'+json.dumps(meta),flush=True)
    if args.emit_base64:
        for name in ('docs/graph/source-manifest.json','docs/FUNCTION_INDEX.md','docs/graph/system-graph.json','docs/graph/system-graph.html'):
            encoded=base64.b64encode((root/name).read_bytes()).decode()
            chunks=[encoded[i:i+8192] for i in range(0,len(encoded),8192)]
            for index,chunk in enumerate(chunks):
                print('SMELTER_GRAPH|'+name+'|'+str(index)+'|'+str(len(chunks))+'|'+chunk,flush=True)

if __name__=='__main__':main()
