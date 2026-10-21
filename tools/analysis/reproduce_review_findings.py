"""Opt-in, fixture-only evidence for documented review findings; no real model.

Prints observations rather than asserting buggy behavior as a future contract.
Uses temporary files and a local mocked OpenCode HTTP client.
"""
import base64
import json
import sqlite3
import struct
import sys
import tempfile
from pathlib import Path


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--revision',required=True)
    revision=parser.parse_args().revision
    repo=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repo/'tools/dashboard'))
    from database import select_database, chosen_database
    from chats import create_chat, delete_chat, read_chat
    from model_assets import attach_model, model_path
    from test_opencode_runtime import Fixture
    from opencode_runtime import ask
    from chat_jobs import Control
    from runtime_settings import save_runtime
    from chat_inference import ask as direct_ask
    import io
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)/'SMELTER';root.mkdir();root.with_name('SMELTERV2').mkdir()
        select_database(root,str(Path(temp)/'data'));cid=create_chat(root,'Fixture')['id']
        document=json.dumps({'asset':{'version':'2.0'},'meshes':[],'nodes':[],'animations':[]}).encode();document+=b' '*(-len(document)%4)
        raw=struct.pack('<4sIIII',b'glTF',2,len(document)+20,len(document),0x4e4f534a)+document
        asset=attach_model(root,{'conversation_id':cid,'filename':'fixture.glb','base64':base64.b64encode(raw).decode()})
        path=model_path(root,asset['id']);delete_chat(root,cid)
        orphan={'chat_deleted':True,'asset_file_still_exists':path.exists()}
        cid=create_chat(root,'Cancellation fixture')['id'];client=Fixture(root.with_name('SMELTERV2'));control=Control();request=client.request
        def cancelled_at_final(path,*args,**kwargs):
            result=request(path,*args,**kwargs)
            if path.endswith('/message?limit=50'):control.cancel()
            return result
        client.request=cancelled_at_final
        result=ask(root,cid,'Read README',model_key='local/qwen3.5:9b',approval=True,client=client,control=control)
        record=read_chat(root,cid)['messages'][-1]['execution']
        cancellation={'control_cancelled':control.cancelled.is_set(),'worker_status':result['status'],'stored_cancelled':record['cancelled']}
        save_runtime(root,{'context_tokens':32768,'max_output_tokens':128,'timeout_seconds':30,'thinking':False})
        requests=[]
        def opener(req,timeout):requests.append(json.loads(req.data));return io.BytesIO(b'{"message":{"content":"fixture"}}')
        direct_ask(root,cid,'Show workspace information',opener=opener,tool_permissions={'frontend_workspace':True})
        override={'saved_output_tokens':128,'actual_num_predict':requests[0]['options']['num_predict']}
        print(json.dumps({'source_revision':revision,
                         'glb_lifecycle':orphan,'opencode_completion_cancel_race':cancellation,'frontend_runtime_override':override},indent=2))


if __name__=='__main__':main()
