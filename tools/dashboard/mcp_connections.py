"""Optional MCP stdio client. Only operator-configured local processes are launched."""
import asyncio
import hashlib
import importlib.metadata
import json
import re
import sys
from datetime import timedelta
from pathlib import Path
from python_tools import _plain_path

SDK_VERSION = '1.30.0'
CONFIG_LIMIT = 32768
RESULT_LIMIT = 256 * 1024


def sdk_status():
    try:
        version = importlib.metadata.version('mcp')
    except importlib.metadata.PackageNotFoundError:
        return {'status': 'missing', 'required_version': SDK_VERSION}
    return {'status': 'installed' if version == SDK_VERSION else 'incompatible',
            'version': version, 'required_version': SDK_VERSION}


def validate_config(data):
    if not isinstance(data, dict) or set(data) != {'schema_version', 'servers'} or type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('MCP config requires schema_version=1 and servers')
    servers = data['servers']
    if not isinstance(servers, list) or len(servers) > 12:
        raise ValueError('Configure up to 12 MCP servers')
    seen = set()
    for server in servers:
        if not isinstance(server, dict) or set(server) != {'id', 'command', 'args', 'cwd', 'enabled', 'allowed_tools'}:
            raise ValueError('Each MCP server requires id, command, args, cwd, enabled, allowed_tools')
        sid = server['id']
        if not isinstance(sid, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', sid) or sid == 'smelter' or sid in seen:
            raise ValueError('Choose a unique MCP server id; smelter is reserved')
        seen.add(sid)
        if type(server['enabled']) is not bool:
            raise ValueError('MCP enabled must be boolean')
        for key in ('command', 'cwd'):
            value = server[key]
            if not isinstance(value, str) or not value or len(value) > 1000 or value.startswith(('\\\\', '//')) or any(ord(c) < 32 for c in value):
                raise ValueError('MCP paths must be plain absolute paths')
            path = Path(value)
            if not path.is_absolute() or '..' in path.parts:
                raise ValueError('MCP paths must be absolute without traversal')
            _plain_path(path)
            if not (path.is_file() if key == 'command' else path.is_dir()):
                raise ValueError('MCP command or working directory is missing')
        if not isinstance(server['args'], list) or len(server['args']) > 32 or any(not isinstance(x, str) or len(x) > 2000 or '\x00' in x for x in server['args']):
            raise ValueError('MCP args must be up to 32 strings')
        allowed = server['allowed_tools']
        if not isinstance(allowed, list) or len(allowed) > 128 or any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', x) for x in allowed) or len(set(allowed)) != len(allowed):
            raise ValueError('MCP allowed_tools must list unique exact tool names')
    return data


def config_path(root):
    return _plain_path(Path(root) / '.smelter/mcp-servers.json')


def load_config(root):
    path = config_path(root)
    if not path.exists():
        return {'schema_version': 1, 'servers': []}
    if path.stat().st_size > CONFIG_LIMIT:
        raise ValueError('MCP config exceeds 32 KiB')
    return validate_config(json.loads(path.read_text(encoding='utf-8')))


def save_config(root, data):
    validate_config(data)
    raw = json.dumps(data, indent=2)
    if len(raw.encode()) > CONFIG_LIMIT:
        raise ValueError('MCP config exceeds 32 KiB')
    path = config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Serialized by the HTTP configuration lock. No process starts on save.
    temporary = _plain_path(path.with_suffix('.json.tmp'))
    temporary.write_text(raw + '\n', encoding='utf-8')
    temporary.replace(path)
    return status(root)


def status(root):
    return {'sdk': sdk_status(), 'transport': 'stdio', 'builtin': 'smelter', 'config': load_config(root),
            'config_path': str(config_path(root)), 'running': False,
            'lifecycle': 'A fresh process per discovery or call; closed when that operation finishes',
            'limits': 'Local stdio only. No network MCP, automatic installation, shell wrapping, or OS sandbox.'}


def _server(root, sid, grants):
    if sid == 'smelter':
        from skill_runtime import export_snapshot
        from access_policy import _active
        return {'id': sid, 'command': sys.executable,
                'args': [str(Path(__file__).with_name('mcp_server.py').resolve()), '--root', str(Path(root).resolve())],
                'cwd': str(Path(root).resolve()), 'enabled': True, 'allowed_tools': None,
                'env': {'SMELTER_MCP_GRANTS': json.dumps(grants), 'SMELTER_SKILL_SNAPSHOT': export_snapshot(root), 'SMELTER_ACCESS_POLICY': json.dumps(_active.get().value) if _active.get() else ''}}
    config = load_config(root)
    server = next((s for s in config['servers'] if s['id'] == sid and s['enabled']), None)
    if not server:
        raise ValueError('MCP server is missing or disabled')
    return server


def fingerprint(server):
    return hashlib.sha256(json.dumps(server, sort_keys=True).encode()).hexdigest()


def alias(sid, name):
    return 'mcp_' + hashlib.sha256((sid + ':' + name).encode()).hexdigest()[:20]


async def _exchange(server, name=None, arguments=None, expected_schema=None, timeout=120):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    parameters = StdioServerParameters(command=server['command'], args=server['args'], cwd=server['cwd'], env=server.get('env'))
    # SDK owns child-process termination on normal completion, error and timeout.
    async with asyncio.timeout(timeout):
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=timeout)) as session:
                initialized = await session.initialize()
                found, cursor = [], None
                for _ in range(8):
                    page = await session.list_tools(cursor=cursor)
                    found.extend(page.tools)
                    cursor = page.nextCursor
                    if len(found) > 128:
                        raise ValueError('MCP server exposes more than 128 tools')
                    if not cursor:
                        break
                if cursor:
                    raise ValueError('MCP tool pagination exceeds limit')
                tools = []
                for tool in found:
                    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', tool.name) or len(json.dumps(tool.inputSchema)) > 16384:
                        raise ValueError('MCP tool name or schema exceeds limits')
                    if any(x['name'] == tool.name for x in tools):
                        raise ValueError('MCP server returned duplicate tool names')
                    tools.append({'name': tool.name, 'description': (tool.description or '')[:2000],
                                  'input_schema': tool.inputSchema,
                                  'allowed': server['allowed_tools'] is None or tool.name in server['allowed_tools']})
                if name is None:
                    return {'server': server['id'], 'status': 'connected', 'protocol_version': initialized.protocolVersion,
                            'server_info': initialized.serverInfo.model_dump(mode='json'), 'tools': tools,
                            'config_fingerprint': fingerprint(server)}
                descriptor = next((t for t in tools if t['name'] == name and t['allowed']), None)
                if descriptor is None:
                    raise ValueError('MCP tool is missing or not in the operator allowlist')
                if expected_schema is not None and descriptor != expected_schema:
                    raise ValueError('MCP tool definition changed; discover and approve it again')
                result = await session.call_tool(name, arguments or {})
                value = result.model_dump(mode='json', by_alias=True, exclude_none=True)
                if len(json.dumps(value).encode()) > RESULT_LIMIT:
                    raise ValueError('MCP result exceeds 256 KiB; action may already have completed')
                return value


def exchange(root, sid='smelter', grants=None, name=None, arguments=None, expected=None, timeout=120):
    if sdk_status()['status'] != 'installed':
        raise ValueError('Install the optional MCP dependency with this dashboard Python: python -m pip install -r tools/dashboard/requirements-mcp.txt')
    server = _server(root, sid, grants or {})
    if expected and fingerprint(server) != expected['config_fingerprint']:
        raise ValueError('MCP connection changed; discover and approve it again')
    try:
        return asyncio.run(_exchange(server, name, arguments, expected.get('descriptor') if expected else None, timeout))
    except Exception as exc:
        # ExceptionGroup from SDK task groups often hides the useful leaf error.
        while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
            exc = exc.exceptions[0]
        detail = ('Timed out; an active tool may already have completed' if isinstance(exc, TimeoutError)
                  else str(exc) or type(exc).__name__)
        raise ValueError('MCP operation failed: ' + detail[:1000]) from exc


def approved_tools(root, selected):
    if not isinstance(selected, list) or len(selected) > 16:
        raise ValueError('Approve up to 16 external MCP tools per message')
    connections, descriptors = {}, {}
    for entry in selected:
        if not isinstance(entry, dict) or set(entry) != {'server', 'name'} or not isinstance(entry['server'], str) or not isinstance(entry['name'], str) or entry['server'] == 'smelter':
            raise ValueError('Invalid external MCP tool selection')
        sid, name = entry['server'], entry['name']
        if sid not in connections:
            connections[sid] = exchange(root, sid, timeout=20)
        connection = connections[sid]
        tool = next((x for x in connection['tools'] if x['name'] == name and x['allowed']), None)
        if not tool:
            raise ValueError('Selected MCP tool is unavailable or not allowlisted')
        descriptors[alias(sid, name)] = {'server': sid, 'name': name, 'descriptor': tool,
                                       'config_fingerprint': connection['config_fingerprint']}
    return descriptors


def call(root, grants, name, arguments, external=None):
    result = exchange(root, external['server'] if external else 'smelter', grants,
                      external['name'] if external else name, arguments, expected=external)
    if external:
        return {'status': 'mcp_failed' if result.get('isError') else 'mcp_completed',
                'server': external['server'], 'tool': external['name'], 'mcp_result': result}
    envelope = result.get('structuredContent')
    if not isinstance(envelope, dict) or not isinstance(envelope.get('tool_result'), dict):
        raise ValueError('SMELTER MCP server returned no structured tool result')
    return {**envelope['tool_result'], 'mcp_audit_path': envelope.get('audit_path')}
