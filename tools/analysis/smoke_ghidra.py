"""Real Ghidra and built-in MCP acceptance on a generated, never-executed ELF.

Uses a new isolated checkout/database and retained fixture evidence. Installs
nothing, never opens a game, and never changes production access/settings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from uuid import uuid4

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/dashboard'))
sys.path.insert(0, str(REPO / 'tools/setup'))


def elf_fixture():
    """x86-64: add two arguments; return 42; call add(3,4); return marker pointer."""
    text = bytearray(b'\x90' * 0x38)
    text[:4] = bytes.fromhex('8d0437c3')
    text[0x10:0x16] = bytes.fromhex('b82a000000c3')
    text[0x20:0x30] = bytes.fromhex('bf03000000be04000000e8d1ffffffc3')
    text[0x30:0x38] = bytes.fromhex('488d0519000000c3')
    marker = b'SMELTER_STATIC_FIXTURE\0'
    names = b'\0smelter_add\0smelter_magic\0smelter_entry\0smelter_marker\0'
    section_names = b'\0.text\0.rodata\0.symtab\0.strtab\0.shstrtab\0'
    symbols = bytes(24)
    for name, offset, size in [('smelter_add',0,4),('smelter_magic',0x10,6),
                               ('smelter_entry',0x20,16),('smelter_marker',0x30,8)]:
        symbols += struct.pack('<IBBHQQ', names.index(name.encode()), 0x12, 0, 1, 0x400100+offset, size)
    sym_offset = 0x180
    str_offset = sym_offset + len(symbols)
    shstr_offset = str_offset + len(names)
    sh_offset = (shstr_offset + len(section_names) + 7) & ~7
    total = sh_offset + 6 * 64
    header = struct.pack('<16sHHIQQQIHHHHHH', b'\x7fELF\x02\x01\x01'+bytes(9),
                         2,62,1,0x400120,64,sh_offset,0,64,56,1,64,6,5)
    program = struct.pack('<IIQQQQQQ',1,5,0,0x400000,0x400000,total,total,0x1000)
    result = bytearray(total)
    result[:64] = header; result[64:120] = program
    result[0x100:0x138] = text
    result[0x150:0x150+len(marker)] = marker
    result[sym_offset:sym_offset+len(symbols)] = symbols
    result[str_offset:str_offset+len(names)] = names
    result[shstr_offset:shstr_offset+len(section_names)] = section_names
    sections = [bytes(64)]
    for name, kind, flags, address, offset, size, link, info, alignment, entry in [
        ('.text',1,6,0x400100,0x100,len(text),0,0,16,0),
        ('.rodata',1,2,0x400150,0x150,len(marker),0,0,1,0),
        ('.symtab',2,0,0,sym_offset,len(symbols),4,1,8,24),
        ('.strtab',3,0,0,str_offset,len(names),0,0,1,0),
        ('.shstrtab',3,0,0,shstr_offset,len(section_names),0,0,1,0),
    ]:
        sections.append(struct.pack('<IIQQQQIIQQ', section_names.index(name.encode()),kind,
                                    flags,address,offset,size,link,info,alignment,entry))
    result[sh_offset:] = b''.join(sections)
    return bytes(result)


def smoke(output):
    from access_policy import Policy, defaults
    from config_store import save_config
    from database import select_database
    from ghidra_connection import status
    from install_rea_skill import CONTEXT, SKILL_ID
    from python_tools import ToolSession
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    root = output / 'checkout'; root.mkdir()
    fixtures = output / 'fixtures'; fixtures.mkdir()
    raw = elf_fixture(); (fixtures/'smelter.elf').write_bytes(raw)
    select_database(root, str(output/'data'))
    skill = root/'.smelter/managed-skills/collections'/SKILL_ID
    skill.mkdir(parents=True); (skill/'SKILL.md').write_text(CONTEXT, encoding='utf-8')
    (root/'.smelter/skill-state.json').write_text(json.dumps({SKILL_ID: True}), encoding='utf-8')
    provider = status(root)
    if provider['status'] != 'installed': raise ValueError(provider['reason'])
    value = defaults(root)
    for identity, location, execute in [('fixture',fixtures,False),('ghidra',Path(provider['home']),True)]:
        value['locations'].append({'id':identity,'name':identity,'path':str(location),'read':True,
            'write':False,'execute':execute,'operations':['rea'] if execute else [],'exclusions':[],'enabled':True})
    policy = Policy(value)
    save_config(root,'access_policy.json',policy.value)
    grants = {'rea_analysis':True,'rea_root':str(fixtures)}
    direct = ToolSession(root,grants,policy=policy)
    results = {}
    def call(session, name, arguments):
        print('Checking '+name, flush=True)
        result = session.execute({'function':{'name':name,'arguments':arguments}})
        if result.get('status') != 'rea_completed': raise ValueError(name+': '+str(result))
        results[name] = result
        return result
    analysis = call(direct,'rea_ghidra_analyze',{'relative_path':'smelter.elf'})
    sid = analysis['analysis_id']
    functions = call(direct,'rea_ghidra_functions',{'analysis_id':sid,'query':'smelter_'})
    items = functions['result_preview']['items']
    add = next(item for item in items if item['name']=='smelter_add')
    strings = call(direct,'rea_ghidra_strings',{'analysis_id':sid,'query':'SMELTER_STATIC_FIXTURE'})
    assert strings['result_preview']['items'], 'Fixture string was not found'
    xrefs = call(direct,'rea_ghidra_xrefs',{'analysis_id':sid,'address':add['address']})
    assert xrefs['result_preview']['items'], 'Known call reference was not found'
    mcp = ToolSession(root,{**grants,'transport':'mcp'},policy=policy)
    decompiled = call(mcp,'rea_ghidra_decompile',{'analysis_id':sid,'address':add['address']})
    preview = decompiled['result_preview']
    code = preview.get('pseudocode',preview.get('decompiled',''))
    assert 'smelter_add' in code and '+' in code, 'Known add function did not decompile as expected'
    report = {'status':'PASS','target_executed':False,'live_model':False,'ghidra':provider,
              'fixture_sha256':hashlib.sha256(raw).hexdigest(),'fixture_source':'generated ELF64 machine-code fixture',
              'transports':['python','smelter-mcp'],'results':results}
    (output/'evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','evidence':str(output/'evidence.json'),'target_executed':False}))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=REPO/'.smelter'/('ghidra-smoke-'+uuid4().hex))
    args=parser.parse_args()
    smoke(args.output)
