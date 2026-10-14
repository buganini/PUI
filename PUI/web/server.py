"""aiohttp gateway with cookie-owned, fork-isolated session workers."""
import asyncio
from dataclasses import dataclass
import hashlib
import hmac
from html import escape
from ipaddress import IPv6Address
import multiprocessing
import os
from pathlib import Path
import secrets
import re
import socket
import sys
from urllib.parse import urlsplit

from aiohttp import web, WSMsgType

from .ipc import read_packet, queue_packet
from .messages import validate_client_body
from .protocol import Codec, ProtocolError, SUBPROTOCOL
from .sessions import SessionRegistry
from .urls import WebURLs
from .worker import run as run_worker, CAPABILITIES

STATIC = Path(__file__).with_name('static')
COOKIE = 'pui_owner'
WORKER_START_TIMEOUT = 30
IPC_TIMEOUT = 30


async def _reap_process(process, *, grace=.5):
    if process.pid is not None:
        await asyncio.to_thread(process.join, grace)
        if process.is_alive():
            process.terminate()
            await asyncio.to_thread(process.join, 1)
        if process.is_alive():
            process.kill()
            await asyncio.to_thread(process.join, 1)
        if process.is_alive():
            raise RuntimeError('Web worker could not be reaped')
    process.close()


def _authority(value):
    if (not isinstance(value, str) or not value or
            any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value) or
            any(char in value for char in '/\\?#@%')):
        raise ValueError('Invalid host authority')
    parts = urlsplit('//' + value)
    name, port = parts.hostname, parts.port
    if not name or value.endswith(':'):
        raise ValueError('Invalid host authority')
    if ':' in name:
        if not re.fullmatch(r'\[[0-9a-fA-F:.]+\](?::[0-9]+)?', value):
            raise ValueError('Invalid IPv6 authority')
        name = IPv6Address(name).compressed
    else:
        name = (name[:-1] if name.endswith('.') else name).encode('idna').decode('ascii').lower()
        if len(name) > 253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',
                                                label) for label in name.split('.')):
            raise ValueError('Invalid host name')
    return name, port


def _allowed_hosts(values):
    if values is None:
        values = ('*',)
    elif isinstance(values, str):
        values = (values,)
    result = set()
    for value in values:
        if value == '*':
            result.add('*')
            continue
        name, port = _authority(value)
        if port is not None:
            raise ValueError('allow_hosts entries must be host names without ports')
        result.add(name)
    return frozenset(result)


@dataclass
class Worker:
    process: object
    writer: object
    task: object = None
    websocket: object = None
    stop_task: object = None


class Gateway:
    def __init__(self, factory, *, base_url='/', mount_path=None, allow_hosts=None,
                 session_ttl=900, max_sessions=64):
        if sys.platform != 'linux':
            raise RuntimeError('The initial Web worker server requires Linux')
        if ':' not in factory:
            raise ValueError('Application factory must be module:Class')
        self.factory = factory
        self.urls = WebURLs(base_url, mount_path=mount_path)
        self.allow_hosts = _allowed_hosts(allow_hosts)
        self.sessions = SessionRegistry(session_ttl=session_ttl, max_sessions=max_sessions)
        self.codec = Codec()
        self.workers = {}
        self.reapers = set()
        self.closing = False
        self.secret = secrets.token_bytes(32)
        self.build = hashlib.sha256(b''.join((STATIC / name).read_bytes() for name in
            ('client.js', 'client.css', 'zstd.wasm'))).hexdigest()[:16]
        # forkserver itself imports no PUI/application module and runs one thread.
        # Only its forked children unpickle the worker entry/import application code.
        multiprocessing.set_forkserver_preload([])
        self.context = multiprocessing.get_context('forkserver')
        self.lock = asyncio.Lock()

    @web.middleware
    async def check_host(self, request, handler):
        try:
            if len(request.headers.getall('Host', [])) != 1:
                raise ValueError('Expected one Host header')
            name, _ = _authority(request.headers['Host'])
        except (ValueError, UnicodeError):
            raise web.HTTPBadRequest(text='Invalid Host header')
        if '*' not in self.allow_hosts and name not in self.allow_hosts:
            raise web.HTTPForbidden(text='Host is not allowed')
        return await handler(request)

    def _sign(self, owner):
        return hmac.new(self.secret, owner.encode('ascii'), hashlib.sha256).hexdigest()

    def owner(self, request):
        value = request.cookies.get(COOKIE, '')
        owner, _, signature = value.partition('.')
        if (len(owner) == 43 and owner.isascii() and len(signature) == 64 and signature.isascii() and
                hmac.compare_digest(self._sign(owner), signature)):
            return owner
        return None

    async def index(self, request):
        owner = self.owner(request) or secrets.token_urlsafe(32)
        html = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PUI</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="%s"></head><body>
<p id="pui-status" role="status">Connecting…</p>
<main id="pui-root" data-ws="%s" data-build="%s"></main>
<script type="module" src="%s"></script></body></html>''' % (
            escape(self.urls.asset(self.build, 'client.css'), quote=True),
            escape(self.urls.websocket(), quote=True), self.build,
            escape(self.urls.asset(self.build, 'client.js'), quote=True))
        response = web.Response(text=html, content_type='text/html', headers={'Cache-Control': 'no-store'})
        response.set_cookie(COOKIE, owner + '.' + self._sign(owner), httponly=True,
            secure=request.secure or urlsplit(self.urls.base_url).scheme == 'https',
            samesite='Lax', path=self.urls.public_path)
        return response

    async def redirect(self, request):
        raise web.HTTPPermanentRedirect(self.urls.base_url)

    async def asset(self, request):
        name = request.match_info['name']
        if request.match_info['build'] != self.build or name not in (
                'client.js', 'client.css', 'zstd.wasm', 'THIRD_PARTY_LICENSES.txt'):
            raise web.HTTPNotFound()
        response = web.FileResponse(STATIC / name, headers={'Cache-Control': 'public, max-age=31536000, immutable'})
        if name.endswith('.wasm'):
            response.content_type = 'application/wasm'
        return response

    async def _spawn(self, session):
        parent, child = socket.socketpair()
        process = self.context.Process(target=run_worker, args=(child, self.factory, self.build),
                                       name='pui-web-worker')
        try:
            process.start()
            child.close()
            parent.setblocking(False)
            reader, writer = await asyncio.open_connection(sock=parent)
        except BaseException:
            parent.close()
            child.close()
            self.sessions.remove(session.resume_id)
            # Cancellation cannot leave a started child outside the registry.
            reaper = asyncio.create_task(_reap_process(process, grace=0))
            self.reapers.add(reaper)
            reaper.add_done_callback(self.reapers.discard)
            await asyncio.shield(reaper)
            raise
        worker = Worker(process, writer)
        self.workers[session.resume_id] = worker
        worker.task = asyncio.create_task(self._relay(session, worker, reader))
        return worker

    async def _relay(self, session, worker, reader):
        try:
            packet = await asyncio.wait_for(read_packet(reader), WORKER_START_TIMEOUT)
            while True:
                epoch, separator, payload = packet.partition(b'\0')
                if not separator:
                    raise ValueError('Invalid worker packet')
                ws = worker.websocket
                if ws is not None and not ws.closed and epoch.decode('ascii') == session.epoch:
                    try:
                        if payload:
                            await asyncio.wait_for(ws.send_bytes(payload), 30)
                        else:
                            await asyncio.wait_for(ws.close(code=1013,
                                message=b'Render acknowledgement timeout'), 1)
                    except (ConnectionError, asyncio.TimeoutError):
                        # Browser loss does not mean worker loss: retain its State
                        # under the same disconnect TTL as an idle connection.
                        await ws.close()
                packet = await read_packet(reader)
        except (asyncio.IncompleteReadError, ConnectionError, ValueError, asyncio.TimeoutError):
            pass
        finally:
            await self._stop(session.resume_id, cancel_relay=False)

    async def _stop(self, resume_id, *, cancel_relay=True, code=1011, reason=b'Worker stopped'):
        worker = self.workers.get(resume_id)
        if worker is None:
            return
        if worker.stop_task is None:
            self.sessions.remove(resume_id)
            worker.stop_task = asyncio.create_task(
                self._reap(resume_id, worker, cancel_relay=cancel_relay, code=code, reason=reason))
            self.reapers.add(worker.stop_task)
            worker.stop_task.add_done_callback(self.reapers.discard)
        await asyncio.shield(worker.stop_task)

    async def _reap(self, resume_id, worker, *, cancel_relay, code, reason):
        if cancel_relay and worker.task is not None:
            worker.task.cancel()
        worker.writer.close()
        try:
            await asyncio.wait_for(worker.writer.wait_closed(), .25)
        except (ConnectionError, asyncio.TimeoutError):
            worker.writer.transport.abort()
        await _reap_process(worker.process)
        if worker.websocket is not None:
            try:
                await asyncio.wait_for(worker.websocket.close(code=code, message=reason), 1)
            except (ConnectionError, asyncio.TimeoutError):
                pass
        self.workers.pop(resume_id, None)

    async def _expire(self):
        # Keep slow process cleanup outside the admission/attachment lock.
        async with self.lock:
            expired = self.sessions.expire()
        await asyncio.gather(*(self._stop(session.resume_id) for session in expired))

    async def _drain(self, worker):
        try:
            await asyncio.wait_for(worker.writer.drain(), IPC_TIMEOUT)
        except asyncio.TimeoutError as error:
            raise ProtocolError('OVERLOADED', 'Worker input queue did not drain') from error

    async def _detach(self, session, epoch, worker):
        queued = False
        async with self.lock:
            if self.sessions.detach(session.resume_id, epoch):
                worker.websocket = None
                queue_packet(worker.writer, b'D')
                queued = True
        if queued:
            await self._drain(worker)

    async def websocket(self, request):
        owner = self.owner(request)
        parts = urlsplit(self.urls.base_url)
        origin = (parts.scheme + '://' + parts.netloc) if parts.scheme else request.scheme + '://' + request.host
        if owner is None or request.headers.get('Origin') != origin:
            raise web.HTTPForbidden()
        if SUBPROTOCOL not in request.headers.get('Sec-WebSocket-Protocol', '').split(','):
            raise web.HTTPBadRequest(text='Required WebSocket subprotocol missing')
        ws = web.WebSocketResponse(protocols=[SUBPROTOCOL], compress=False,
                                   max_msg_size=self.codec.limits.max_wire_bytes, heartbeat=20)
        await ws.prepare(request)
        session = worker = epoch = None
        try:
            first = await asyncio.wait_for(ws.receive(), 10)
            if first.type != WSMsgType.BINARY:
                raise ProtocolError('BAD_FRAME', 'Expected binary hello')
            hello = self.codec.decode(first.data)
            body = hello['body']
            if hello['type'] != 'hello' or hello['seq'] != 1:
                raise ProtocolError('BAD_FRAME', 'Invalid hello')
            validate_client_body('hello', body)
            if body['client_build'] != self.build:
                raise ProtocolError('VERSION_MISMATCH', 'Reload the page')
            if not set(CAPABILITIES) <= set(body['capabilities']):
                raise ProtocolError('UNSUPPORTED_CAPABILITY', 'Missing required capabilities')
            await self._expire()
            async with self.lock:
                if self.closing:
                    raise ProtocolError('OVERLOADED', 'Server is stopping')
                session = self.sessions.resume(owner, body['resume_id'])
                resumed = session is not None
                if session is None:
                    if len(self.workers) >= self.sessions.max_sessions:
                        raise ProtocolError('OVERLOADED', 'Session capacity reached')
                    session = self.sessions.create(owner)
                    worker = await self._spawn(session)
                else:
                    worker = self.workers[session.resume_id]
                epoch = session.epoch
                worker.websocket = ws
                control = {'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                    'body': {'epoch': epoch, 'hello': body, 'resume_id': session.resume_id,
                             'resumed': resumed, 'session_ttl': self.sessions.session_ttl}}
                queue_packet(worker.writer, b'A' + self.codec.encode(control))
            await self._drain(worker)
            async for message in ws:
                if message.type == WSMsgType.BINARY:
                    queue_packet(worker.writer, b'M' + message.data)
                    await self._drain(worker)
                elif message.type == WSMsgType.TEXT:
                    raise ProtocolError('BAD_FRAME', 'Only binary messages are accepted')
                elif message.type == WSMsgType.ERROR:
                    break
        except (ProtocolError, asyncio.TimeoutError, ConnectionError) as error:
            await ws.close(code=1008, message=str(error).encode('utf-8')[:120])
            if worker is not None and isinstance(error, ProtocolError) and error.code == 'OVERLOADED':
                await self._stop(session.resume_id)
        finally:
            if session is not None and epoch is not None:
                try:
                    await self._detach(session, epoch, worker)
                except (ProtocolError, ConnectionError):
                    if session.epoch is None or session.epoch == epoch:
                        await self._stop(session.resume_id)
            await ws.close()
        return ws

    async def lifecycle(self, app):
        async def expire():
            while True:
                await asyncio.sleep(min(1, max(.05, self.sessions.session_ttl)))
                await self._expire()
        timer = asyncio.create_task(expire())
        yield
        timer.cancel()
        await asyncio.gather(timer, return_exceptions=True)
        await self.shutdown(app)
        await asyncio.gather(*list(self.reapers))

    async def shutdown(self, app):
        self.closing = True
        workers = list(self.workers.values())
        await asyncio.gather(*(self._stop(key, code=1001, reason=b'Server shutdown')
                              for key in list(self.workers)))
        await asyncio.gather(*(worker.task for worker in workers if worker.task is not None),
                             return_exceptions=True)

    def application(self):
        app = web.Application(client_max_size=self.codec.limits.max_wire_bytes,
                              middlewares=[self.check_host])
        app.cleanup_ctx.append(self.lifecycle)
        app.on_shutdown.append(self.shutdown)
        if self.urls.mount_path != '/':
            app.router.add_get(self.urls.mount_path.rstrip('/'), self.redirect)
        app.router.add_get(self.urls.mount_path, self.index)
        app.router.add_get(self.urls.route('assets') + '/{build}/{name}', self.asset)
        app.router.add_get(self.urls.route('pui/ws'), self.websocket)
        return app


def serve(factory, *, host='127.0.0.1', port=8000, base_url='/', mount_path=None, allow_hosts=None,
          session_ttl=900, max_sessions=64):
    gateway = Gateway(factory, base_url=base_url, mount_path=mount_path, allow_hosts=allow_hosts,
                      session_ttl=session_ttl, max_sessions=max_sessions)
    public_url = gateway.urls.base_url
    if not urlsplit(public_url).scheme:
        public_url = 'http://%s:%s%s' % (host, port, public_url)
    print('PUI Web: ' + public_url, flush=True)
    web.run_app(gateway.application(), host=host, port=port, shutdown_timeout=3)
