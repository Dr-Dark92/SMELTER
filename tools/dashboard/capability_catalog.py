"""One descriptor vocabulary for GUI, fixed model tools and legacy adapters."""
from pathlib import Path
from tool_registry import schemas
from skills_catalog import catalog_skills


def catalog(root):
    grants={'frontend_workspace':True,'coding_workspace':True,'model_ids':['explicit-attachment-selection-required'],'rea_analysis':True,'melty_read':True,'native_build':True,'inventory_root':'registered-folder-required','write_diagnostics':True,'access_requests':True,'web_read':True,'project_memory':True}
    tools=[]
    from sandbox import status as sandbox_status
    confined=sandbox_status(root)
    from rea_connection import package_status
    rea=package_status(root)
    from ghidra_connection import status as ghidra_status
    ghidra=ghidra_status(root)
    from melty_connection import status as melty_status
    melty=melty_status(root)
    for entry in schemas(grants):
        function=entry['function'];name=function['name']
        tools.append({'id':name,'description':function['description'],'parameters':function['parameters'],
                      'source':'dashboard/tool_registry','adapter':'registered_builtin','transports':['python','smelter-mcp'],
                      'availability':'requires_per_message_grants','authority':'registered locations intersected with adapter contract',
                      'executable':True})
        if name=='web_access':
            from web_access import settings as web_settings,provider_status
            web=web_settings(root);provider=provider_status(root)
            tools[-1].update(availability='blocked' if web['mode']=='off' else 'requires_per_message_grants',read_only=True,mode=web['mode'],search_provider=provider,fetch='public HTTPS text only')
        if name=='project_memory':
            from project_memory import settings as memory_settings
            memory=memory_settings(root)
            tools[-1].update(availability='requires_per_message_grants' if memory['enabled'] else 'blocked',dependency='Project files + builtin SQLite FTS5 + bounded RAM',model_writes='unverified notes only')
        if name.startswith('melty_'):
            tools[-1].update(dependency='Melty HTTPS MCP + host sign-in', reason=melty['reason'], read_only=True)
            if melty['status']!='configured':tools[-1]['availability']='blocked'
        if name=='request_directory_access':
            tools[-1].update(availability='requires_live_gui_task',read_only=True,
                             transports=['Python GUI controller','managed OpenCode MCP bridge'],
                             authority='Human decision for the exact directory; no writes or execution')
        if name == 'universal_modder':
            try:
                from universal_modder import verified_installation
                identity=verified_installation(root)
                tools[-1].update(dependency='Pinned Universal Modder private CLI',revision=identity['revision'],read_only=True)
            except (ValueError,OSError,KeyError):
                tools[-1].update(availability='blocked',dependency='universal_modder setup profile',reason='Install and verify the pinned CLI first')
        if name in ('validate_frontend_workspace','launch_frontend_preview'):
            tools[-1].update(availability='requires_per_message_grants' if confined['ready'] else 'blocked',dependency='confined Docker runner',reason=confined['reason'])
        if name=='launch_frontend_preview':tools[-1]['transports']=['python (dashboard owner)']
        if name=='run_coding_tests':
            profiles={profile:sandbox_status(root,operation='coding_'+profile) for profile in ('python','node','cpp')}
            profiles.update(mods=profiles['python'], lua=profiles['cpp'])
            tools[-1]['profiles']={profile:{'availability':'requires_per_message_grants' if report['ready'] else 'blocked',
                                           'reason':report['reason']} for profile,report in profiles.items()}
            tools[-1]['availability']='requires_per_message_grants' if any(r['ready'] for r in profiles.values()) else 'blocked'
        if name == 'build_native_mod':
            report=sandbox_status(root,operation='coding_cpp')
            tools[-1].update(availability='requires_per_message_grants' if report['ready'] else 'blocked',
                             dependency='confined MinGW-w64 CLI toolchain image (smelter-cpp:2)',reason=report['reason'],host_fallback=False)
        if name == 'inspect_engine_archive':
            report=sandbox_status(root,operation='engine_archive')
            tools[-1].update(availability='requires_per_message_grants' if report['ready'] else 'blocked',
                             dependency='pinned repak, retoc and UnityDataTool image (smelter-engine-cli:1)',
                             reason=report['reason'],read_only=True,host_fallback=False)
        if name.startswith('rea_ghidra_'):
            tools[-1].update(dependency='Ghidra headless + Java', provider='ghidra', reason=ghidra['reason'])
            if ghidra['status']!='installed':tools[-1]['availability']='blocked'
        elif name.startswith('rea_') and rea['status']!='installed':tools[-1].update(availability='blocked',dependency='rea-agents',reason=rea['reason'])
    # These operations are discoverable library adapters, not implicitly executable
    # GUI tools. Their core callers must use explicit trusted registration.
    for module,names in {'smelter_asset_adapter':['inspect_glb','convert_glb_to_obj','validate_obj'],
                         'smelter_blender_adapter':['build','validate'],
                         'smelter_material_adapter':['make_fixture','roundtrip','inspect','compare'],
                         'smelter_integrity_adapter':['fingerprint','compare','negative_mutation']}.items():
        if not (Path(__file__).resolve().parents[1]/'core'/(module+'.py')).is_file():continue
        for name in names:
            tools.append({'id':'core/'+module+'/'+name,'source':'core','adapter':module+'.'+name,
                          'availability':'library_only','dependency':'blender (operation-dependent)','executable':False,
                          'reason':'Use explicit core registration or the scoped Registry.connect_dashboard adapter; arbitrary core host execution is not GUI-exposed'})
    tools.append({'id':'project_contract','adapter':'project_contract.inspect_project','source':'dashboard','availability':'operator_api','executable':False,'endpoint':'/api/project-contract'})
    from skill_runtime import monitor
    return {'schema_version':1,'capabilities':tools,'skills':monitor(root).status()['skills'],
            'note':'Availability describes registered adapters, not permission to execute. Skill text never installs or registers code.'}
