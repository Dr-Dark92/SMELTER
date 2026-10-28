"""Exact-origin native lifecycle and receipt adapter for the watchdog, not the trace."""
from contextlib import closing
import base64
import json
import os
from pathlib import Path
import sqlite3
import time
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urlencode

from native_progress import NoRedirect,same_directory,token

RESUMABLE_TOOLS={'read','glob','grep','list','skill','todowrite','todoread','question','webfetch','websearch',
    'smelter_coding_workspace_context','smelter_coding_recovery_context','smelter_prepare_coding_workspace',
    'smelter_list_coding_files','smelter_read_coding_file','smelter_propose_coding_edit','smelter_propose_coding_edits','smelter_propose_coding_patch',
    'smelter_propose_coding_restore','smelter_apply_coding_patch','smelter_run_coding_tests','smelter_finish_coding_task','smelter_review_coding_workspace',
    'smelter_build_native_mod','smelter_project_memory','smelter_web_access','smelter_modding_tool_catalog',
    'smelter_universal_modder','smelter_inventory_directory','smelter_read_inventory_file','smelter_inspect_game_files',
    'smelter_inspect_engine_archive','smelter_write_diagnostic_markdown'}

GUARDED_NATIVE_TOOLS={'bash','edit','write','apply_patch','patch','multiedit','multi_edit','task'}
GUARD_ERROR=('SMELTER guarded task: use scoped read/propose_coding_edits/apply_coding_patch/run_coding_tests tools in the existing workspace. '
             'Native shell, edits and delegated agents bypass its checkpoints and are disabled for this bound task.')


class Native:
    def __init__(self,root,path=None,ports=None):
        self.root=Path(root).resolve()
        base=Path(os.environ['XDG_DATA_HOME']) if os.environ.get('XDG_DATA_HOME') else Path.home()/'.local/share'
        self.path=Path(path) if path else base/'opencode/opencode.db'
        from task_trace import LocalInspector
        self.inspector=LocalInspector();self.ports=ports or self.inspector.ports_now
        self.opener=build_opener(ProxyHandler({}),NoRedirect())

    def rpc(self,task,route,body=None):
        from watchdog_store import process_running
        if not process_running(task['native_pid'],task['native_identity']):raise ValueError('Originating native process ended or changed')
        if task['server_port'] not in self.ports():raise ValueError('Originating ACP listener unavailable')
        sid=token(task['session_id'],'ses')
        if route not in ('/session/status','/permission','/question','/session/'+sid,'/session/'+sid+'/prompt_async'):raise ValueError('Unsupported watchdog native route')
        if body is not None and route!='/session/'+sid+'/prompt_async':raise ValueError('Only same-session continuation may write')
        headers={'Accept':'application/json'}
        if os.environ.get('OPENCODE_SERVER_PASSWORD'):
            auth=os.environ.get('OPENCODE_SERVER_USERNAME','opencode')+':'+os.environ['OPENCODE_SERVER_PASSWORD']
            headers['Authorization']='Basic '+base64.b64encode(auth.encode()).decode()
        if body is not None:headers['Content-Type']='application/json'
        url='http://127.0.0.1:'+str(task['server_port'])+route+'?'+urlencode({'directory':task['directory']})
        request=Request(url,data=None if body is None else json.dumps(body).encode('utf-8'),headers=headers,method='GET' if body is None else 'POST')
        with self.opener.open(request,timeout=15 if body is not None else 3) as response:raw=response.read(256*1024+1)
        if len(raw)>256*1024:raise ValueError('Watchdog native response exceeds bound')
        return json.loads(raw) if raw.strip() else None

    def metadata(self,task,attempts):
        from python_tools import _plain_path
        path=_plain_path(self.path)
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
            db.execute('PRAGMA query_only=ON')
            owner=db.execute('SELECT directory FROM session WHERE id=?',(task['session_id'],)).fetchone()
            if not owner or not same_directory(owner[0],task['directory']):raise ValueError('Native session owner mismatch')
            origin=db.execute('SELECT time_created FROM message WHERE id=? AND session_id=?',(task['origin_id'],task['session_id'])).fetchone()
            if not origin:return {'available':False,'reason':'original_message_not_persisted'}
            since=origin[0];allowed={task['origin_id']}|{a['message_id'] for a in attempts}
            latest_user=db.execute("""SELECT m.id,m.time_created FROM message m WHERE m.session_id=? AND json_extract(m.data,'$.role')='user'
                AND EXISTS(SELECT 1 FROM part p WHERE p.message_id=m.id AND
                  ((json_extract(p.data,'$.type')='text' AND coalesce(json_extract(p.data,'$.synthetic'),0)=0) OR json_extract(p.data,'$.type')='file'))
                ORDER BY m.time_created DESC,m.id DESC LIMIT 1""",(task['session_id'],)).fetchone()
            assistant=db.execute("""SELECT time_created,time_updated,json_extract(data,'$.time.completed'),json_extract(data,'$.finish'),
                json_extract(data,'$.error.name') FROM message WHERE session_id=? AND time_created>=?
                AND json_extract(data,'$.role')='assistant' ORDER BY time_created DESC,id DESC LIMIT 1""",(task['session_id'],since)).fetchone()
            sessions=db.execute('''WITH RECURSIVE c(id,directory,depth) AS (SELECT id,directory,0 FROM session WHERE id=? UNION ALL
                SELECT s.id,s.directory,c.depth+1 FROM session s JOIN c ON s.parent_id=c.id WHERE s.time_created>=? AND c.depth<8)
                SELECT id,directory FROM c LIMIT 17''',(task['session_id'],since)).fetchall()
            ids=[sid for sid,directory in sessions if same_directory(directory,task['directory'])][:16]
            marks=','.join('?' for _ in ids)
            active=db.execute(f"SELECT COUNT(*) FROM part WHERE session_id IN ({marks}) AND time_updated>=? AND json_extract(data,'$.type')='tool' AND json_extract(data,'$.state.status') IN ('pending','running')",(*ids,since)).fetchone()[0]
            names=db.execute(f"""SELECT DISTINCT json_extract(data,'$.tool'),json_extract(data,'$.state.status'),
                instr(coalesce(json_extract(data,'$.state.error'),''),?) IN (1,8)
                FROM part WHERE session_id IN ({marks}) AND time_created>=? AND json_extract(data,'$.type')='tool' LIMIT 128""",(GUARD_ERROR,*ids,since)).fetchall()
            progress=db.execute(f'SELECT MAX(time_updated) FROM part WHERE session_id IN ({marks}) AND time_updated>=?',(*ids,since)).fetchone()[0] or since
            # Named error classes only: no prompts, rejected code or tool bodies
            # leave SQLite. A protocol failure is not a transient model stall.
            protocol=db.execute(f"""SELECT sum(bad),count(*) FROM (
                SELECT CASE WHEN json_extract(data,'$.state.status')='error' AND (
                  json_extract(CASE WHEN json_valid(json_extract(data,'$.state.error')) THEN json_extract(data,'$.state.error') ELSE '{{}}' END,'$.tool_result.code') IN ('input_contract_error','recovery_required')
                  OR instr(coalesce(json_extract(data,'$.state.error'),''),'Input validation error:')>0
                  OR instr(coalesce(json_extract(data,'$.state.error'),''),'Duplicate/case-colliding patch path')>0
                  OR instr(coalesce(json_extract(data,'$.state.error'),''),'Likely snippet-as-file replacement rejected')>0
                  OR instr(coalesce(json_extract(data,'$.state.error'),''),'Choose line pagination OR character offset/limit')>0
                ) THEN 1 ELSE 0 END AS bad FROM part
                WHERE session_id IN ({marks}) AND time_created>=? AND json_extract(data,'$.type')='tool'
                ORDER BY time_created DESC LIMIT 12)""",(*ids,since)).fetchone()
            receipts=db.execute("""SELECT time_updated,json_extract(data,'$.state.input.workspace_id'),json_extract(data,'$.state.input.profile'),
              coalesce(json_extract(CASE WHEN json_valid(json_extract(data,'$.state.output')) THEN json_extract(data,'$.state.output') ELSE '{}' END,'$.tool_result.evidence_path'),
                       json_extract(CASE WHEN json_valid(json_extract(data,'$.state.error')) THEN json_extract(data,'$.state.error') ELSE '{}' END,'$.tool_result.evidence_path'))
              FROM part WHERE session_id=? AND time_created>=? AND json_extract(data,'$.type')='tool'
              AND json_extract(data,'$.tool')='smelter_run_coding_tests' AND json_extract(data,'$.state.status') IN ('completed','error')
              ORDER BY time_updated DESC LIMIT 16""",(task['session_id'],since)).fetchall()
            endings=db.execute("""SELECT time_updated,json_extract(data,'$.state.input.workspace_id'),
                json_extract(data,'$.state.input.outcome'),json_extract(data,'$.state.input.profiles'),
                json_extract(CASE WHEN json_valid(json_extract(data,'$.state.output')) THEN json_extract(data,'$.state.output') ELSE '{}' END,'$.tool_result.status'),
                json_extract(CASE WHEN json_valid(json_extract(data,'$.state.output')) THEN json_extract(data,'$.state.output') ELSE '{}' END,'$.tool_result.outcome'),
                json_extract(CASE WHEN json_valid(json_extract(data,'$.state.output')) THEN json_extract(data,'$.state.output') ELSE '{}' END,'$.tool_result.tree_sha256'),
                json_extract(CASE WHEN json_valid(json_extract(data,'$.state.output')) THEN json_extract(data,'$.state.output') ELSE '{}' END,'$.tool_result.profiles'),
                json_extract(CASE WHEN json_valid(json_extract(data,'$.state.output')) THEN json_extract(data,'$.state.output') ELSE '{}' END,'$.tool_result.receipts')
                FROM part WHERE session_id=? AND time_created>=? AND json_extract(data,'$.type')='tool'
                AND json_extract(data,'$.tool')='smelter_finish_coding_task' AND json_extract(data,'$.state.status')='completed'
                ORDER BY time_updated DESC LIMIT 8""",(task['session_id'],since)).fetchall()
            delivered={a['message_id'] for a in attempts if db.execute('SELECT 1 FROM message WHERE session_id=? AND id=?',(task['session_id'],a['message_id'])).fetchone()}
        return {'available':True,'superseded':bool(latest_user and latest_user[0] not in allowed),
                'cancelled':bool(assistant and assistant[4]=='MessageAbortedError'),
                'assistant_seen':bool(assistant),
                'turn_ended':bool(assistant and assistant[2] and assistant[3]!='tool-calls' and (not latest_user or assistant[0]>=latest_user[1])),
                'active_tools':active,'last_progress':max(progress,assistant[1] if assistant else since)/1000,
                'unrecognized_tool_domain':any(name not in RESUMABLE_TOOLS and not (name in GUARDED_NATIVE_TOOLS and status=='error' and blocked) for name,status,blocked in names),
                'protocol_errors':protocol[0] or 0,'protocol_error_burst':(protocol[0] or 0)>=3,
                'receipts':receipts,'endings':endings,'delivered':delivered,'sessions_truncated':len(sessions)>16,'session_ids':ids}

    def snapshot(self,task,attempts):
        result=self.metadata(task,attempts)
        if not result.get('available') or result.get('cancelled') or result.get('superseded'):return result
        owner=self.rpc(task,'/session/'+task['session_id'])
        if owner.get('id')!=task['session_id'] or not same_directory(owner.get('directory',''),task['directory']):raise ValueError('Native endpoint identity mismatch')
        states=self.rpc(task,'/session/status');sid=task['session_id']
        state=states.get(sid,{'type':'idle'})
        result['native_phase']=state.get('type','unknown')
        related=set(result['session_ids'])
        if any(s.get('type')!='idle' for i,s in states.items() if i in related and i!=sid):result['native_phase']='busy_child'
        result['pending_access']=any(p.get('sessionID') in related for p in self.rpc(task,'/permission'))
        result['pending_question']=any(p.get('sessionID') in related for p in self.rpc(task,'/question'))
        if result['sessions_truncated']:result['active_tools']=max(1,result['active_tools'])
        if result['turn_ended'] and result['native_phase']=='idle' and not result['active_tools']:
            flag=self.end_flag(task,result['receipts'],result['endings'])
            if flag:result.update(flag=flag['flag'],flag_receipt=flag['receipt'])
            result['validation_progress']=self.validation_progress(task,result['receipts'])
        return result

    def validation_progress(self,task,records):
        """Historical frozen results can identify churn, never establish GREEN."""
        import coding_workspace as cw
        from acceptance_contracts import load as contracts,fresh
        from python_tools import _plain_path
        with cw.locked(self.root):
            _,target=cw.load(self.root,task['workspace_id']);registered=contracts(self.root,task['workspace_id'],target)
            if not registered:return None  # Editable test counts are not a stable contract.
            expected={}
            for contract in registered:
                expected.setdefault(contract['profile'],set()).add((contract['id'],contract['subject_path'],contract['verifier_sha256']))
            base=cw.base_path(self.root)/task['workspace_id']/'test-runs';groups={}
            for _,workspace,profile,raw_path in records:
                if workspace!=task['workspace_id'] or not raw_path:continue
                path=_plain_path(Path(raw_path))
                if path.parent.resolve()!=base.resolve() or path.suffix!='.json' or not path.is_file() or path.stat().st_size>3*1024*1024:continue
                value=json.loads(path.read_text(encoding='utf-8'));acceptance=value.get('acceptance',{})
                if value.get('workspace_id')!=workspace or value.get('profile')!=profile or acceptance.get('stage')!='RED':continue
                if not fresh(self.root,workspace,target,profile,{'acceptance_revision':acceptance.get('contracts_revision')}):continue
                items=acceptance.get('contracts',[])
                if {(c.get('id'),c.get('subject_path'),c.get('verifier_sha256')) for c in items}!=expected.get(profile,set()):continue
                if not items or any(type(c.get('counts',{}).get('failures')) is not int or type(c.get('counts',{}).get('checks')) is not int
                                    or not 0<=c['counts']['failures']<=c['counts']['checks'] for c in items):continue
                log=_plain_path(path.with_suffix('.log'))
                if not log.is_file() or log.stat().st_size>3*1024*1024 or cw.digest(log.read_bytes())!=value.get('log_sha256'):continue
                key=(profile,acceptance.get('contracts_revision'),tuple(sorted((c['id'],c['counts']['checks']) for c in items)))
                group=groups.setdefault(key,[])
                if path.stem not in {r[0] for r in group}:group.append((path.stem,sum(c['counts']['failures'] for c in items)))
                if len(group)==3 and group[0][1]>=min(group[1][1],group[2][1]):
                    return {'stalled':True,'profile':profile,'failures_newest_first':[r[1] for r in group],
                            'receipts':[r[0] for r in group],'scope':'same frozen verifier revision and check counts'}
        return None

    def end_flag(self,task,records,endings=()):
        """Intent AND current evidence are required; ordinary TDD RED is not final."""
        from coding_finish import verify_receipts,PROFILES
        for updated,workspace,outcome,profiles,status,saved_outcome,tree,saved_profiles,receipts in endings:
            if workspace!=task['workspace_id'] or status!='coding_task_end_flag' or outcome not in ('RED','GREEN') or saved_outcome!=outcome:
                continue
            requested=json.loads(profiles or 'null')
            if not isinstance(requested,list) or not requested or any(not isinstance(p,str) or p not in PROFILES for p in requested):continue
            # A later validation invalidates the earlier completion declaration.
            if any(stamp>updated for stamp,w,_,_ in records if w==workspace):continue
            proof=verify_receipts(self.root,workspace,records,requested)
            if (proof and proof['flag']==outcome and proof['tree_sha256']==tree
                    and proof['profiles']==json.loads(saved_profiles or 'null') and proof['receipts']==json.loads(receipts or 'null')):
                return proof
        return None

    def send(self,task,attempt):
        # The original objective is retained, but checkpoints guide continuation.
        text=(f"SMELTER watchdog recovery {attempt['number']}/3 for original task {task['origin_id']}.\n"
              f"Continue the SAME session and workspace {task['workspace_id']}. A newer human instruction takes priority.\n"
              "Call coding_recovery_context first. Inspect saved changes and receipts; do not recreate the workspace or repeat already-applied actions. "
              "Prefer smelter_propose_coding_edit: one file, one replacement, five flat string arguments; review then apply its proposal. "
              "Preserve frozen acceptance. Finish the original objective and run its relevant validation. "
              "An intermediate RED is not completion. When actually finished, call smelter_finish_coding_task with the existing workspace ID, "
              "all relevant test profiles and outcome GREEN or final unsuccessful RED. Report the actual receipts.\n\n"
              "Original user request:\n"+task['prompt'])
        body={'messageID':attempt['message_id'],'model':json.loads(task['model']),'parts':[{'type':'text','text':text}]}
        body.update(json.loads(task.get('request_options') or '{}'))
        for key in ('agent','variant'):
            if task.get(key):body[key]=task[key]
        return self.rpc(task,'/session/'+task['session_id']+'/prompt_async',body)
