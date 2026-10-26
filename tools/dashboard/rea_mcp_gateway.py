"""Expose REA tools on demand instead of putting its entire catalog in each prompt.

Uses the already installed MCP SDK. The launcher supplies the fixed upstream
command after --; model arguments cannot change that command or its environment.
"""
import argparse
import asyncio
from contextlib import suppress
from datetime import timedelta
import json
import os
import re
import sys


MAX_SCHEMA_CHARS = 24000
MAX_ARGUMENT_CHARS = 1000000
INSTRUCTIONS = (
    'REA is available through three compact tools. For reverse engineering only, '
    'search_tools finds operations, describe_tool returns the exact input schema, '
    'and call_tool invokes the operation with arguments_json containing a JSON object. '
    'Use these gateway tools instead of old direct rea_<operation> names. '
    'Large schemas return a navigable JSON-pointer index, never a silently cut schema. '
    'The original REA backend, Ghidra configuration and host access remain in effect. '
    'These are analysis capabilities, not evidence that the requested task is complete. '
    'Continue the concrete task already given in the conversation.'
)


def definitions():
    def tool(name, description, properties, required=()):
        return {'name': name, 'description': description, 'inputSchema': {
            'type': 'object', 'properties': properties, 'required': list(required),
            'additionalProperties': False}}
    return [
        tool('search_tools', 'Find REA operations by task, name or backend; then describe the chosen operation.', {
            'query': {'type': 'string', 'maxLength': 500},
            'offset': {'type': 'integer', 'minimum': 0, 'maximum': 100000},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 30},
            'refresh': {'type': 'boolean'}}),
        tool('describe_tool', 'Read a REA operation input schema. If large, follow returned JSON pointers to inspect its parts.', {
            'name': {'type': 'string'}, 'pointer': {'type': 'string', 'maxLength': 1000},
            'max_chars': {'type': 'integer', 'minimum': 1000, 'maximum': MAX_SCHEMA_CHARS},
            'offset': {'type': 'integer', 'minimum': 0, 'maximum': 100000}}, ('name',)),
        tool('call_tool', 'Invoke a discovered REA operation. arguments_json must be a JSON object matching its input schema. Returns the original result/error.', {
            'name': {'type': 'string'},
            'arguments_json': {'type': 'string', 'maxLength': MAX_ARGUMENT_CHARS}}, ('name', 'arguments_json')),
    ]


def encoded(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def pointer_get(value, pointer):
    if not pointer:
        return value
    if not pointer.startswith('/') or re.search(r'~(?![01])', pointer):
        raise ValueError('pointer must be an RFC 6901 JSON pointer relative to inputSchema')
    try:
        for part in pointer[1:].split('/'):
            key = part.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if not re.fullmatch(r'0|[1-9][0-9]*', key):
                    raise ValueError('Invalid array index in pointer')
                value = value[int(key)]
            else:
                value = value[key]
        return value
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError('Schema pointer does not exist') from error


class Catalog:
    def __init__(self, upstream):
        self.upstream = upstream
        self.tools = {}

    async def refresh(self):
        tools, seen, cursor = {}, set(), None
        for _ in range(1000):
            result = await self.upstream.list_tools(cursor=cursor)
            for tool in result.tools:
                if tool.name in tools:
                    raise ValueError('Duplicate REA tool name: ' + tool.name)
                tools[tool.name] = tool
            cursor = result.nextCursor
            if cursor is None:
                self.tools = tools
                return
            if cursor in seen:
                raise ValueError('REA returned a repeated catalog cursor')
            seen.add(cursor)
        raise ValueError('REA catalog exceeded 1000 pages')

    def lookup(self, name):
        if name not in self.tools:
            raise ValueError('Unknown REA operation; use search_tools first')
        return self.tools[name]

    async def search(self, query='', offset=0, limit=15, refresh=False):
        if refresh:
            await self.refresh()
        words = query.casefold().split()
        matches = []
        for item in self.tools.values():
            description = item.description or ''
            haystack = (item.name + ' ' + description).casefold()
            score = sum(5 * (word in item.name.casefold()) + (word in haystack) for word in words)
            if not words or score:
                matches.append((score, item.name, description))
        matches.sort(key=lambda row: (-row[0], row[1]))
        selected = matches[offset:offset + limit]
        return {'catalog_count': len(self.tools), 'matches': len(matches), 'offset': offset,
                'next_offset': offset + limit if offset + limit < len(matches) else None,
                'tools': [{'name': name, 'description_preview': description[:300]} for _, name, description in selected]}

    def describe(self, name, pointer='', max_chars=16000, offset=0):
        item = self.lookup(name)
        node = pointer_get(item.inputSchema, pointer)
        size = len(encoded(node))
        result = {'name': name, 'description_preview': (item.description or '')[:1000],
                  'pointer': pointer, 'schema_chars': size, 'complete': size <= max_chars}
        if size <= max_chars:
            return {**result, 'schema': node}
        children = list(node.items()) if isinstance(node, dict) else list(enumerate(node)) if isinstance(node, list) else []
        result.update(child_count=len(children), next_offset=offset + 30 if offset + 30 < len(children) else None,
                      children=[{'pointer': pointer + '/' + str(key).replace('~', '~0').replace('/', '~1'),
                                 'chars': len(encoded(value))} for key, value in children[offset:offset + 30]],
                      guidance='Follow child pointers. Resolve $ref paths against the full inputSchema root. No schema was truncated.')
        if not children:
            result['guidance'] = 'This single schema value exceeds the response budget; increase max_chars up to 24000 or inspect the upstream source.'
        return result

    async def invoke(self, name, arguments_json, progress=None):
        import jsonschema
        item = self.lookup(name)
        if len(arguments_json) > MAX_ARGUMENT_CHARS:
            raise ValueError('REA argument JSON exceeds the gateway limit')
        def invalid_constant(value):
            raise ValueError('Non-finite JSON value: ' + value)
        arguments = json.loads(arguments_json, parse_constant=invalid_constant)
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json must decode to a JSON object')
        validator = jsonschema.validators.validator_for(item.inputSchema)
        try:
            validator(item.inputSchema).validate(arguments)
        except jsonschema.ValidationError as error:
            raise ValueError('Invalid REA arguments: ' + error.message[:1000]) from error
        return await self.upstream.call_tool(name, arguments,
            read_timeout_seconds=timedelta(seconds=900), progress_callback=progress)


def cancellable_session_class():
    import anyio
    import mcp.types as types
    from mcp import ClientSession, McpError

    class CancellableSession(ClientSession):
        async def send_request(self, request, result_type, **kwargs):
            # SDK 1.30.0 allocates this ID synchronously before its first await,
            # but does not notify the server when the local waiter is cancelled.
            request_id = self._request_id
            try:
                return await super().send_request(request, result_type, **kwargs)
            except BaseException as error:
                cancelled = isinstance(error, asyncio.CancelledError)
                timed_out = isinstance(error, McpError) and error.error.code == 408
                if isinstance(request.root, types.CallToolRequest) and (cancelled or timed_out):
                    with anyio.CancelScope(shield=True), anyio.move_on_after(2), suppress(Exception):
                        await self.send_notification(types.ClientNotification(types.CancelledNotification(
                            params=types.CancelledNotificationParams(requestId=request_id, reason='Gateway caller cancelled or timed out'))))
                raise

    return CancellableSession


async def serve(command):
    import mcp.types as types
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.server.lowlevel import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server

    server = Server('smelter-rea-gateway', instructions=INSTRUCTIONS)
    downstream = [None]

    async def roots(context):
        if downstream[0] is None:
            return types.ListRootsResult(roots=[])
        return await downstream[0].list_roots()

    async with stdio_client(StdioServerParameters(command=command[0], args=command[1:], env=dict(os.environ))) as (read, write):
        async with cancellable_session_class()(read, write, list_roots_callback=roots,
                                 read_timeout_seconds=timedelta(seconds=60)) as upstream:
            initialized = await upstream.initialize()
            catalog = Catalog(upstream)
            await catalog.refresh()
            instructions = INSTRUCTIONS + '\nOriginal REA instructions:\n' + (initialized.instructions or '')

            @server.list_tools()
            async def list_tools():
                return [types.Tool(**item) for item in definitions()]

            @server.call_tool()
            async def call_tool(name, arguments):
                downstream[0] = server.request_context.session
                if name == 'search_tools':
                    return await catalog.search(**arguments)
                if name == 'describe_tool':
                    return catalog.describe(**arguments)
                if name != 'call_tool':
                    raise ValueError('Unknown gateway tool')
                context = server.request_context
                token = context.meta.progressToken if context.meta else None
                async def progress(value, total=None, message=None):
                    if token is not None:
                        await context.session.send_progress_notification(token, value, total, message)
                return await catalog.invoke(**arguments, progress=progress)

            async with stdio_server() as (incoming, outgoing):
                await server.run(incoming, outgoing, InitializationOptions(
                    server_name='smelter-rea-gateway', server_version='0.1.0', instructions=instructions,
                    capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={})))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('Supply the existing REA command after --')
    asyncio.run(serve(command))


if __name__ == '__main__':
    main()
