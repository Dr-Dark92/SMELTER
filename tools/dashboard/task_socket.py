"""Same-origin authenticated read-only WebSocket snapshots (RFC 6455).

No client commands, compression or fragmented messages. Client control frames
are masked and bounded; observers cannot start/abort tasks or grant access.
"""
import base64
import hashlib
import json
import select
import socket
import struct
import threading
import time

PROTOCOL = 'smelter.trace.v1'
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
_slots = threading.BoundedSemaphore(8)


def credential(headers, origin):
    protocols = [p.strip() for p in headers.get('Sec-WebSocket-Protocol', '').split(',')]
    if headers.get('Origin') != origin or len(protocols) != 2 or PROTOCOL not in protocols:
        return ''
    auth = next((p[len('smelter.auth.'):] for p in protocols if p.startswith('smelter.auth.')), '')
    return auth if auth.isascii() and 8 <= len(auth) <= 128 else ''


def frame(payload, opcode=1):
    if len(payload) > 1024 * 1024: raise ValueError('Trace frame exceeds 1 MiB')
    size = len(payload)
    prefix = bytes([0x80 | opcode, size if size < 126 else 126 if size < 65536 else 127])
    return prefix + (b'' if size < 126 else struct.pack('!H', size) if size < 65536 else struct.pack('!Q', size)) + payload


def control(stream):
    def exact(size):
        value = stream.read(size)
        if len(value) != size: raise EOFError()
        return value
    first, second = exact(2)
    opcode, size = first & 15, second & 127
    if first & 0x70 or not first & 0x80 or not second & 0x80 or opcode not in (8, 9, 10) or size > 125:
        raise ValueError('Only masked, final control frames are accepted')
    mask, payload = exact(4), exact(size)
    payload = bytes(v ^ mask[i % 4] for i, v in enumerate(payload))
    if opcode == 8:
        if len(payload) == 1: raise ValueError('Invalid close payload')
        if payload:
            code = struct.unpack('!H', payload[:2])[0]
            if code < 1000 or code >= 5000 or code in (1004, 1005, 1006, 1015) or 1016 <= code < 3000:
                raise ValueError('Invalid close code')
            payload[2:].decode('utf-8')
    return opcode, payload


def serve(handler, source=None, stopping=None):
    from task_trace import manager
    key = handler.headers.get('Sec-WebSocket-Key', '')
    try: valid_key = len(base64.b64decode(key, validate=True)) == 16
    except (ValueError, TypeError): valid_key = False
    if (handler.headers.get('Upgrade', '').lower() != 'websocket' or
        'upgrade' not in [p.strip().lower() for p in handler.headers.get('Connection', '').split(',')] or
        handler.headers.get('Sec-WebSocket-Version') != '13' or not valid_key):
        return handler.reply(400, {'error': 'A version 13 WebSocket upgrade is required'})
    if not _slots.acquire(blocking=False): return handler.reply(503, {'error': 'Eight trace observers are already connected'})
    upgraded = False
    try:
        handler.protocol_version = 'HTTP/1.1'
        handler.send_response(101)
        handler.send_header('Upgrade', 'websocket'); handler.send_header('Connection', 'Upgrade')
        handler.send_header('Sec-WebSocket-Accept', base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode())
        handler.send_header('Sec-WebSocket-Protocol', PROTOCOL); handler.end_headers()
        handler.wfile.flush(); handler.close_connection = True; upgraded = True
        handler.connection.settimeout(3)
        provider = source or manager(handler.app.ROOT).view
        last_send, last_ping, last_pong = 0, time.monotonic(), time.monotonic()
        while not (stopping and stopping.is_set()):
            tick = time.monotonic()
            if tick - last_pong > 60: break
            if tick - last_send >= 2:
                try: value = provider()
                except (OSError, ValueError, TypeError): value = {'available': False, 'reason': 'Trace unavailable; reconnect or review access.'}
                handler.wfile.write(frame(json.dumps({'type': 'task.snapshot', 'trace': value}).encode()))
                handler.wfile.flush(); last_send = tick
            if tick - last_ping >= 20:
                handler.wfile.write(frame(b'', 9)); handler.wfile.flush(); last_ping = tick
            ready, _, _ = select.select([handler.connection], [], [], .25)
            if ready:
                opcode, payload = control(handler.rfile)
                if opcode == 8:
                    handler.wfile.write(frame(payload, 8)); handler.wfile.flush(); break
                if opcode == 9:
                    handler.wfile.write(frame(payload, 10)); handler.wfile.flush()
                if opcode == 10: last_pong = tick
    except (EOFError, OSError, ValueError, UnicodeError):
        if upgraded:
            try: handler.wfile.write(frame(struct.pack('!H', 1002), 8)); handler.wfile.flush()
            except OSError: pass
    finally:
        _slots.release()
