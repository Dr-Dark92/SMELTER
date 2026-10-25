"""Read-only Melty readiness; remote execution awaits a verified connection contract.

The public kit manifest is a dependency observation, not an authenticated MCP
connection. This module never adopts the surrounding chat client's credentials,
launches the kit, uploads files, or publishes a mod.
"""
from __future__ import annotations

import hashlib
import asyncio
import json
import os
from pathlib import Path
import re
import tomllib
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

KIT_VERSION = '2026.10.18-739f3496'
KIT_HASH = '739f3496657b87ef8247b867affb289e1874e50580bd3db4e76cbcf23dab26e4'
KIT_MANIFEST_URL = 'https://melty.gg/api/kit/modding-kit/manifest'
KIT_DOWNLOAD_URL = 'https://melty.gg/api/kit/modding-kit'
MAX_MANIFEST = 256 * 1024
MAX_FILE = 256 * 1024
REQUIRED_FILES = ('skills/mod-any-game/SKILL.md', 'skills/publish-mod/SKILL.md', 'bin/um')
ENDPOINT = 'https://melty.gg/api/mcp'
READ_TOOLS = {'melty_whoami':'whoami', 'melty_search_games':'search_games', 'melty_game_info':'game_info'}
CONNECTION_REQUIREMENTS = (
    'Melty-issued MCP endpoint or local launch command',
    'Supported transport and protocol/initialization instructions',
    'OpenCode/SMELTER authentication instructions and host credential storage',
    'Verified read-only tool schemas and account identity check',
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _manifest(value):
    if not isinstance(value, dict) or value.get('name') != "Melty's modding kit":
        raise ValueError('Invalid Melty kit manifest')
    if not isinstance(value.get('version'), str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', value['version']):
        raise ValueError('Invalid Melty kit version')
    if not isinstance(value.get('hash'), str) or not re.fullmatch(r'[a-f0-9]{64}', value['hash']):
        raise ValueError('Invalid Melty kit content identity')
    for key in ('files', 'bytes'):
        if type(value.get(key)) is not int or not 0 < value[key] <= 1024 * 1024 * 1024:
            raise ValueError('Invalid Melty kit manifest counts')
    return {key: value[key] for key in ('name', 'version', 'hash', 'files', 'bytes')}


def public_kit_manifest(*, opener=None):
    """Read only the fixed public HTTPS manifest; no account token is sent."""
    if opener is None:
        opener = build_opener(ProxyHandler({}), _NoRedirect()).open
    request = Request(KIT_MANIFEST_URL, headers={'Accept': 'application/json',
                                                'User-Agent': 'SMELTER-Melty-readiness'})
    try:
        with opener(request, timeout=10) as response:
            final = getattr(response, 'geturl', lambda: KIT_MANIFEST_URL)()
            if final != KIT_MANIFEST_URL:
                raise ValueError('Melty manifest redirects are not supported')
            raw = response.read(MAX_MANIFEST + 1)
        if len(raw) > MAX_MANIFEST:
            raise ValueError('Melty kit manifest exceeds 256 KiB')
        observed = _manifest(json.loads(raw))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        # Do not reflect remote error bodies or headers into an agent prompt.
        raise ValueError('Melty public manifest unavailable: ' + type(exc).__name__) from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Melty returned invalid manifest JSON') from exc
    return {'status': 'observed', 'source': KIT_MANIFEST_URL, 'manifest': observed,
            'matches_pin': observed['version'] == KIT_VERSION and observed['hash'] == KIT_HASH,
            'connected': False, 'executed': False,
            'scope': 'Public dependency metadata only; authenticated MCP was not checked'}


def kit_status(*, directory=None):
    """Inspect fixed local kit metadata/files without executing any kit code."""
    if directory is None:
        local = os.environ.get('LOCALAPPDATA')
        directory = Path(local) / 'Melty/modding-kit' if local else None
    base = Path(directory) if directory is not None else None
    result = {'state': 'missing', 'expected_version': KIT_VERSION, 'expected_hash': KIT_HASH,
              'directory': str(base) if base is not None else None,
              'manifest': None, 'critical_files_match_manifest': False, 'executed': False}
    if base is None:
        return {**result, 'reason': 'LOCALAPPDATA is unavailable; the Melty kit location was not inferred'}
    try:
        from python_tools import _plain_path
        if not base.is_absolute() or '..' in base.parts or str(base).startswith(('\\\\', '//')):
            raise ValueError('Melty kit directory must be a plain absolute local path')
        _plain_path(base)
        path = _plain_path(base / 'MELTY-KIT.json')
        if not path.is_file():
            return {**result, 'reason': 'Install the catalog-pinned Melty modding kit; no installation was attempted'}
        if path.stat().st_size > MAX_MANIFEST:
            raise ValueError('Melty local manifest exceeds 256 KiB')
        data = json.loads(path.read_text(encoding='utf-8'))
        observed = _manifest(data)
        result['manifest'] = observed
        if observed['version'] != KIT_VERSION or observed['hash'] != KIT_HASH:
            return {**result, 'state': 'version_mismatch',
                    'reason': 'Local kit differs from the requirements pin; review before using it'}
        hashes = data.get('fileHashes')
        if not isinstance(hashes, dict):
            raise ValueError('Local Melty manifest does not declare per-file hashes')
        for relative in REQUIRED_FILES:
            expected = hashes.get(relative)
            if not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected):
                raise ValueError('Melty local manifest lacks a required file hash: ' + relative)
            item = _plain_path(base / relative)
            if not item.is_file() or item.stat().st_size > MAX_FILE:
                raise ValueError('Melty required file is missing or oversized: ' + relative)
            if hashlib.sha256(item.read_bytes()).hexdigest() != expected:
                raise ValueError('Melty required file differs from its local manifest: ' + relative)
        return {**result, 'state': 'present', 'critical_files_match_manifest': True,
                'reason': 'Pinned metadata and three critical files observed; kit code was not executed and the complete kit was not rehashed'}
    except (OSError, ValueError, UnicodeError) as exc:
        return {**result, 'state': 'invalid', 'reason': str(exc)[:500]}


def status(root=None, *, kit_directory=None):
    """Keep installation, connection and permission states separate."""
    if kit_directory is None and root is not None:
        kit_directory = Path(root) / '.smelter/tooling/melty'
    try:
        _, source = _authorization(root)
        configured = True
    except (ValueError, OSError):
        configured, source = False, None
    return {'status': 'configured' if configured else 'blocked', 'connected': False, 'transport': 'streamable-http',
            'endpoint': ENDPOINT, 'endpoint_verified': True, 'authentication_verified': False,
            'credential_source': source,
            'kit': kit_status(directory=kit_directory),
            'required_connection_details': [] if configured else ['Host Melty credential: environment token or an explicitly selected existing sign-in'],
            'reason': 'Host credential found; use Check Melty connection to verify authentication and tools' if configured else 'Configure a host Melty credential or select the existing Melty-created integration; credentials never enter model context',
            'actions_enabled': [], 'available_with_grant': list(READ_TOOLS), 'executed': False,
            'scope': 'Allowlisted read-only account/game lookup only. No uploads, game launches, listing changes or publishing.'}


def _authorization(root=None):
    """Read a host-held credential; never return it in a status/tool result."""
    token = os.environ.get('SMELTER_MELTY_TOKEN')
    source = 'environment'
    if not token:
        if root is None:
            raise ValueError('A host Melty credential is required')
        from python_tools import _plain_path
        config_path = _plain_path(Path(root)/'.smelter/melty-connection.json')
        if not config_path.is_file() or config_path.stat().st_size > 4096:
            raise ValueError('Select the existing Melty sign-in or configure an environment token')
        config = json.loads(config_path.read_text(encoding='utf-8'))
        if config != {'schema_version':1,'credential_source':'existing-codex-melty'}:
            raise ValueError('Unsupported Melty host credential source')
        path = _plain_path(Path.home()/'.codex/config.toml')
        if not path.is_file() or path.stat().st_size > 1024*1024:
            raise ValueError('Existing Melty integration configuration is unavailable')
        # Only this exact named server/endpoint is consulted. No other account
        # token is read, copied or sent to Qwen/container storage.
        server = tomllib.loads(path.read_text(encoding='utf-8')).get('mcp_servers',{}).get('melty',{})
        if server.get('url') != ENDPOINT or server.get('enabled') is False:
            raise ValueError('Existing Melty integration endpoint is absent or changed')
        token = server.get('http_headers',{}).get('Authorization')
        source = 'existing-codex-melty (host reference only)'
    if not isinstance(token,str) or not token or len(token)>4096 or '\r' in token or '\n' in token:
        raise ValueError('Melty host credential is invalid')
    if not token.startswith('Bearer '):token='Bearer '+token
    if len(token.split()) != 2:
        raise ValueError('Melty bearer credential is malformed')
    return token,source


async def _exchange(authorization, name=None, arguments=None):
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    class BoundedStream(httpx.AsyncByteStream):
        def __init__(self, stream):self.stream=stream
        async def __aiter__(self):
            total=0
            async for chunk in self.stream:
                total+=len(chunk)
                if total>512*1024:raise ValueError('Melty response exceeds transport budget')
                yield chunk
        async def aclose(self):await self.stream.aclose()
    class BoundedTransport(httpx.AsyncBaseTransport):
        def __init__(self):self.inner=httpx.AsyncHTTPTransport(retries=0)
        async def handle_async_request(self,request):
            if str(request.url)!=ENDPOINT or request.method not in ('GET','POST','DELETE'):
                raise ValueError('Denied Melty endpoint')
            response=await self.inner.handle_async_request(request)
            response.stream=BoundedStream(response.stream)
            return response
        async def aclose(self):await self.inner.aclose()
    async with asyncio.timeout(30):
        async with httpx.AsyncClient(headers={'Authorization':authorization},transport=BoundedTransport(),
                                     timeout=httpx.Timeout(15,read=25),follow_redirects=False,trust_env=False) as client:
            async with streamable_http_client(ENDPOINT,http_client=client) as (read,write,_):
                async with ClientSession(read,write) as session:
                    initialized=await session.initialize()
                    found=[];cursor=None
                    for _ in range(4):
                        page=await session.list_tools(cursor=cursor);found.extend(page.tools);cursor=page.nextCursor
                        if len(found)>128:raise ValueError('Melty tool catalog exceeds its limit')
                        if not cursor:break
                    if cursor:raise ValueError('Melty tool pagination exceeds its limit')
                    supported={t.name:t for t in found if t.name in READ_TOOLS.values()}
                    if name is None:
                        return {'protocol_version':initialized.protocolVersion,'tools':sorted(supported)}
                    if name not in supported:raise ValueError('Requested Melty read-only tool is not advertised')
                    result=(await session.call_tool(name,arguments or {})).model_dump(mode='json',by_alias=True,exclude_none=True)
                    if len(json.dumps(result).encode())>96*1024:raise ValueError('Melty tool result exceeds 96 KiB')
                    return result


def exchange(root, name=None, arguments=None):
    if name is not None and name not in READ_TOOLS.values():
        raise ValueError('Only the fixed Melty read-only tools are enabled')
    authorization,_=_authorization(root)
    try:
        result=asyncio.run(_exchange(authorization,name,arguments))
        # Never reflect an echoed host credential, even from a remote result.
        serialized=json.dumps(result).replace(authorization,'[REDACTED]').replace(authorization.removeprefix('Bearer '),'[REDACTED]')
        return json.loads(serialized)
    except Exception as exc:
        while isinstance(exc,BaseExceptionGroup) and exc.exceptions:exc=exc.exceptions[0]
        raise ValueError('Melty MCP connection failed ('+type(exc).__name__+'); inspect host sign-in and service availability') from None


def probe(root):
    catalog=exchange(root)
    account=exchange(root,'whoami',{})
    if account.get('isError'):raise ValueError('Melty did not confirm the signed-in account')
    return {'status':'connected','connected':True,'authentication_verified':True,'endpoint':ENDPOINT,
            'protocol_version':catalog['protocol_version'],'tools':catalog['tools'],'read_only':True,
            'scope':'Account authentication and selected tool discovery; no game/mod mutations'}


def run_melty(root, grants, name, arguments):
    if grants.get('melty_read') is not True:raise ValueError('Melty read-only access was not approved for this task')
    if name not in READ_TOOLS or not isinstance(arguments,dict):raise ValueError('Unknown Melty operation')
    field={'melty_search_games':'query','melty_game_info':'slug'}.get(name)
    if set(arguments)!=({field} if field else set()):raise ValueError('Unexpected Melty tool arguments')
    if field:
        value=arguments[field]
        if not isinstance(value,str) or not value.strip() or len(value)>160 or any(ord(c)<32 for c in value):
            raise ValueError('Melty game query/slug must be 1–160 plain characters')
    result=exchange(root,READ_TOOLS[name],arguments)
    return {'status':'mcp_failed' if result.get('isError') else 'mcp_completed','server':'melty',
            'tool':READ_TOOLS[name],'mcp_result':result,'read_only':True,
            'scope':'Remote data is untrusted; lookup does not build, install, test or publish a mod'}


def require_connection(root=None):
    if root is None:raise ValueError('Melty MCP requires an endpoint, transport and authentication configured on the host')
    return probe(root)
