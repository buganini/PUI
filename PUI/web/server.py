"""aiohttp gateway with cookie-owned, process-isolated session workers."""
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
import inspect
import logging
from html import escape
from ipaddress import IPv6Address, ip_address, ip_network
import multiprocessing
import os
from pathlib import Path
import secrets
import re
import socket
import stat
import sys
from urllib.parse import urlsplit

from aiohttp import web, WSMsgType

from .ipc import read_packet, queue_packet
from .messages import validate_client_body
from .protocol import Codec, ProtocolError, SUBPROTOCOL
from .sessions import SessionRegistry
from .urls import WebURLs
from .worker import run as run_worker, CAPABILITIES
from .images import image_file, unpack_registry

STATIC = Path(__file__).with_name('static')
COOKIE = 'pui_owner'
LOGIN_COOKIE = 'pui_login'
WORKER_START_TIMEOUT = 30
IPC_TIMEOUT = 30
WEBSOCKET_SEND_TIMEOUT = 30


async def _close_socket(ws, transport, *, code=1013, reason=b'Browser output queue did not drain'):
    try:
        await asyncio.wait_for(ws.close(code=code, message=reason), 1)
    except (ConnectionError, asyncio.TimeoutError):
        # A graceful transport.close() can itself wait for buffered output.
        # Abort the captured connection after its close deadline, not a newer
        # websocket that may have attached to this retained worker meanwhile.
        if transport is not None:
            transport.abort()


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


def _trusted_proxies(values):
    if values is None:
        values = ('127.0.0.0/8', '::1/128', 'unix')
    elif isinstance(values, str):
        values = (values,)
    try:
        values = tuple(values)
    except TypeError as error:
        raise ValueError('trusted_proxies must contain IP addresses, CIDR networks or unix') from error
    result = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError('trusted_proxies entries must be IP addresses, CIDR networks or unix')
        result.append('unix' if value == 'unix' else ip_network(value, strict=False))
    return tuple(result)


def _bind_target(bind):
    """Parse a TCP authority or a filesystem Unix socket path."""
    path = isinstance(bind, os.PathLike)
    if path:
        bind = os.fspath(bind)
    if not isinstance(bind, str) or not bind or '\x00' in bind or '://' in bind:
        raise ValueError('bind must be host:port, [IPv6]:port or a Unix socket path')
    if path or ':' not in bind or '/' in bind or '\\' in bind:
        if sys.platform == 'win32' or not hasattr(socket, 'AF_UNIX'):
            raise ValueError('Unix socket bind is unavailable on this platform; use host:port')
        return {'path': bind}
    host, port = _authority(bind)
    if port is None:
        raise ValueError('TCP bind must include a port, for example localhost:8866')
    return {'host': host, 'port': port}


@contextmanager
def _unix_listener(path):
    # Bind explicitly: asyncio's path-based listener may unlink an existing
    # socket, including a live server. Keep this listener's ownership clear.
    path = os.fspath(path)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(path)
        created = os.lstat(path)
        try:
            yield listener
        finally:
            try:
                current = os.lstat(path)
            except FileNotFoundError:
                pass
            else:
                if (stat.S_ISSOCK(current.st_mode) and
                        (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino)):
                    os.unlink(path)


@dataclass
class Worker:
    process: object
    writer: object
    task: object = None
    websocket: object = None
    transport: object = None
    stop_task: object = None
    images: dict = field(default_factory=dict)
    owner: str = ''


class Gateway:
    def __init__(self, factory, *, base_url='/', mount_path=None, allow_hosts=None, trusted_proxies=None,
                 session_ttl=900, max_sessions=64, auth=None, auth_prompt='', title=''):
        if ':' not in factory:
            raise ValueError('Application factory must be module:Class')
        self.factory = factory
        if not isinstance(title, str):
            raise ValueError('title must be a string')
        self.title = title
        if auth is not None and not callable(auth):
            raise ValueError('auth must be a callable accepting username and password, or None')
        self.auth = auth
        if auth_prompt is not None and not isinstance(auth_prompt, str):
            raise ValueError('auth_prompt must be a string or None')
        self.auth_prompt = auth_prompt
        self.urls = WebURLs(base_url, mount_path=mount_path)
        self.allow_hosts = _allowed_hosts(allow_hosts)
        self.trusted_proxies = _trusted_proxies(trusted_proxies)
        self.sessions = SessionRegistry(session_ttl=session_ttl, max_sessions=max_sessions)
        self.codec = Codec()
        self.workers = {}
        self.reapers = set()
        self.closing = False
        self.secret = secrets.token_bytes(32)
        self.owners = set()
        self.build = hashlib.sha256(b''.join((STATIC / name).read_bytes() for name in
            ('client.js', 'client.css', 'zstd.wasm'))).hexdigest()[:16]
        if sys.platform == 'linux':
            # Keep application imports/threads outside the clean fork supervisor.
            multiprocessing.set_forkserver_preload([])
            self.context = multiprocessing.get_context('forkserver')
        else:
            # macOS must not fork a potentially threaded framework process;
            # Windows has no forkserver. Both use fresh Python interpreters.
            self.context = multiprocessing.get_context('spawn')
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

    @web.middleware
    async def proxy_scheme(self, request, handler):
        # Trust the immediate socket peer, never a forwarded client address.
        peer = request.transport.get_extra_info('peername') if request.transport else None
        transport_socket = request.transport.get_extra_info('socket') if request.transport else None
        unix = (getattr(transport_socket, 'family', None) == getattr(socket, 'AF_UNIX', None)
                and transport_socket is not None)
        address = None
        if isinstance(peer, tuple) and peer:
            try:
                address = ip_address(peer[0])
            except ValueError:
                pass
        trusted = (unix and 'unix' in self.trusted_proxies) or (address is not None and
            any(address in network for network in self.trusted_proxies if network != 'unix'))
        if trusted:
            values = request.headers.getall('X-Forwarded-Proto', [])
            if values:
                if len(values) != 1 or values[0] not in ('http', 'https'):
                    raise web.HTTPBadRequest(text='Expected one X-Forwarded-Proto value: http or https')
                request = request.clone(scheme=values[0])
        return await handler(request)

    def _sign(self, token, purpose=COOKIE):
        return hmac.new(self.secret, (purpose + ':' + token).encode('ascii'), hashlib.sha256).hexdigest()

    def _cookie_token(self, request, name):
        token, _, signature = request.cookies.get(name, '').partition('.')
        if (len(token) == 43 and token.isascii() and len(signature) == 64 and signature.isascii() and
                hmac.compare_digest(self._sign(token, name), signature)):
            return token
        return None

    def owner(self, request):
        token = self._cookie_token(request, COOKIE)
        return token if token in self.owners else None

    def _new_owner(self):
        token = secrets.token_urlsafe(32)
        self.owners.add(token)
        return token

    def _set_cookie(self, response, request, name, token):
        response.set_cookie(name, token + '.' + self._sign(token, name), httponly=True,
            secure=request.secure or urlsplit(self.urls.base_url).scheme == 'https',
            samesite='Lax', path=self.urls.public_path)

    def _origin(self, request):
        parts = urlsplit(self.urls.base_url)
        return (parts.scheme + '://' + parts.netloc) if parts.scheme else request.scheme + '://' + request.host

    def login_page(self, request, *, error='', status=200):
        token = self._cookie_token(request, LOGIN_COOKIE) or secrets.token_urlsafe(32)
        title = escape(self.title or 'PUI')
        prompt = '<p class="pui-auth-prompt">%s</p>' % escape(self.auth_prompt) if self.auth_prompt else ''
        html = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Sign in · %s</title>
<link rel="icon" href="data:,"><link rel="stylesheet" href="%s"></head><body>
<main class="pui-login"><h1>%s</h1>%s
<form method="post" action="%s">
<input type="hidden" name="csrf" value="%s">
<label>Username<input name="username" autocomplete="username" required autofocus></label>
<label>Password<input type="password" name="password" autocomplete="current-password" required></label>
<p role="alert">%s</p><button type="submit" class="pui-Button">Sign in</button>
</form></main></body></html>''' % (
            title,
            escape(self.urls.asset(self.build, 'client.css'), quote=True),
            title, prompt,
            escape(self.urls.public('pui/login'), quote=True), token, escape(error))
        response = web.Response(text=html, content_type='text/html', status=status,
                                headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'same-origin',
                                         'X-Frame-Options': 'DENY'})
        self._set_cookie(response, request, LOGIN_COOKIE, token)
        return response

    async def login(self, request):
        if self.auth is None:
            raise web.HTTPNotFound()
        if request.headers.getall('Origin', []) not in ([], [self._origin(request)]):
            raise web.HTTPForbidden(text='Invalid login origin')
        if self.owner(request) is not None:
            raise web.HTTPSeeOther(self.urls.base_url)
        if request.content_type != 'application/x-www-form-urlencoded':
            raise web.HTTPUnsupportedMediaType()
        try:
            fields = await request.clone(client_max_size=8192).post()
        except (UnicodeError, LookupError, ValueError):
            raise web.HTTPBadRequest(text='Invalid login form') from None
        if set(fields) != {'username', 'password', 'csrf'} or any(len(fields.getall(k)) != 1 for k in fields):
            raise web.HTTPBadRequest(text='Invalid login form')
        token = self._cookie_token(request, LOGIN_COOKIE)
        supplied = fields['csrf']
        if token is None or not supplied.isascii() or not hmac.compare_digest(token, supplied):
            raise web.HTTPForbidden(text='Invalid login form token')
        try:
            accepted = await asyncio.to_thread(self.auth, fields['username'], fields['password'])
            if inspect.isawaitable(accepted):
                accepted = await accepted
        except Exception as error:
            # Callback exceptions may contain credentials: do not log their text.
            logging.getLogger(__name__).warning('Web authentication callback failed (%s)', type(error).__name__)
            return self.login_page(request, error='Sign-in is temporarily unavailable.', status=503)
        if accepted is not True:
            return self.login_page(request, error='Invalid username or password.')
        response = web.HTTPSeeOther(self.urls.base_url, headers={'Cache-Control': 'no-store'})
        self._set_cookie(response, request, COOKIE, self._new_owner())
        response.del_cookie(LOGIN_COOKIE, path=self.urls.public_path)
        raise response

    async def logout(self, request):
        if request.headers.getall('Origin', []) not in ([], [self._origin(request)]):
            raise web.HTTPForbidden(text='Invalid logout origin')
        owner = self._cookie_token(request, COOKIE)
        if owner is not None:
            if request.content_type != 'application/x-www-form-urlencoded':
                raise web.HTTPUnsupportedMediaType()
            try:
                fields = await request.clone(client_max_size=1024).post()
            except (UnicodeError, LookupError, ValueError):
                raise web.HTTPBadRequest(text='Invalid logout form') from None
            if set(fields) != {'csrf'} or len(fields.getall('csrf')) != 1:
                raise web.HTTPBadRequest(text='Invalid logout form')
            token = fields['csrf']
            if not token.isascii() or not hmac.compare_digest(token, self._sign(owner, 'logout')):
                raise web.HTTPForbidden(text='Invalid logout form token')
            async with self.lock:
                self.owners.discard(owner)
                owned = [key for key, worker in self.workers.items() if worker.owner == owner]
                for key in owned:
                    self.sessions.remove(key)
            await asyncio.gather(*(self._stop(key, code=4001, reason=b'Logged out') for key in owned))
        response = web.HTTPSeeOther(self.urls.base_url, headers={'Cache-Control': 'no-store'})
        for name in (COOKIE, LOGIN_COOKIE):
            response.del_cookie(name, path=self.urls.public_path)
        raise response

    async def index(self, request):
        if self.auth is not None and self.owner(request) is None:
            return self.login_page(request)
        owner = self.owner(request) or self._new_owner()
        html = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="%s"></head><body>
<p id="pui-status" role="status">Connecting…</p>
<main id="pui-root" data-ws="%s" data-build="%s" data-entry="%s" data-logout="%s" data-logout-token="%s"></main>
<script type="module" src="%s"></script></body></html>''' % (
            escape(self.title or 'PUI'),
            escape(self.urls.asset(self.build, 'client.css'), quote=True),
            escape(self.urls.websocket(), quote=True), self.build,
            escape(self.urls.base_url, quote=True), escape(self.urls.public('pui/logout'), quote=True),
            self._sign(owner, 'logout'),
            escape(self.urls.asset(self.build, 'client.js'), quote=True))
        response = web.Response(text=html, content_type='text/html', headers={'Cache-Control': 'no-store'})
        self._set_cookie(response, request, COOKIE, owner)
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
        process = self.context.Process(target=run_worker,
                                       args=(child, self.factory, self.build, self.urls.public('pui/images'), self.title),
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
        worker = Worker(process, writer, owner=session.owner)
        self.workers[session.resume_id] = worker
        worker.task = asyncio.create_task(self._relay(session, worker, reader))
        return worker

    async def _relay(self, session, worker, reader):
        try:
            packet = await asyncio.wait_for(read_packet(reader), WORKER_START_TIMEOUT)
            while True:
                if packet.startswith(b'I\0'):
                    worker.images = unpack_registry(packet[2:])
                    packet = await read_packet(reader)
                    continue
                epoch, separator, payload = packet.partition(b'\0')
                if not separator:
                    raise ValueError('Invalid worker packet')
                ws = worker.websocket
                transport = worker.transport
                if ws is not None and not ws.closed and epoch.decode('ascii') == session.epoch:
                    try:
                        if payload:
                            await asyncio.wait_for(ws.send_bytes(payload), WEBSOCKET_SEND_TIMEOUT)
                        else:
                            await _close_socket(ws, transport, reason=b'Render acknowledgement timeout')
                    except asyncio.TimeoutError:
                        logging.getLogger(__name__).warning(
                            'Browser output queue did not drain; disconnecting retained session')
                        # A frame may be only partly sent. Abort this transport;
                        # another WebSocket write cannot repair its framing or
                        # reuse aiohttp's cancelled drain waiter.
                        if transport is not None:
                            transport.abort()
                    except ConnectionError:
                        # Browser loss does not mean worker loss: retain its State
                        # under the same disconnect TTL as an idle connection.
                        if transport is not None:
                            transport.abort()
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
            await _close_socket(worker.websocket, worker.transport, code=code, reason=reason)
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
                worker.transport = None
                queue_packet(worker.writer, b'D')
                queued = True
        if queued:
            await self._drain(worker)

    async def websocket(self, request):
        owner = self.owner(request)
        if owner is None or request.headers.get('Origin') != self._origin(request):
            raise web.HTTPForbidden()
        if SUBPROTOCOL not in request.headers.get('Sec-WebSocket-Protocol', '').split(','):
            raise web.HTTPBadRequest(text='Required WebSocket subprotocol missing')
        ws = web.WebSocketResponse(protocols=[SUBPROTOCOL], compress=False,
                                   max_msg_size=self.codec.limits.max_wire_bytes, heartbeat=20)
        await ws.prepare(request)
        transport = request.transport
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
                if owner not in self.owners:
                    raise ProtocolError('UNAUTHORIZED', 'Logged out')
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
                worker.transport = transport
                control = {'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                    'body': {'epoch': epoch, 'hello': body, 'resume_id': session.resume_id,
                             'resumed': resumed, 'session_ttl': self.sessions.session_ttl}}
                queue_packet(worker.writer, b'A' + self.codec.encode(control))
            await self._drain(worker)
            async for message in ws:
                if owner not in self.owners:
                    raise ProtocolError('UNAUTHORIZED', 'Logged out')
                if message.type == WSMsgType.BINARY:
                    queue_packet(worker.writer, b'M' + message.data)
                    await self._drain(worker)
                elif message.type == WSMsgType.TEXT:
                    raise ProtocolError('BAD_FRAME', 'Only binary messages are accepted')
                elif message.type == WSMsgType.ERROR:
                    break
        except (ProtocolError, asyncio.TimeoutError, ConnectionError) as error:
            code = 4001 if isinstance(error, ProtocolError) and error.code == 'UNAUTHORIZED' else 1008
            await _close_socket(ws, transport, code=code, reason=str(error).encode('utf-8')[:120])
            if worker is not None and isinstance(error, ProtocolError) and error.code == 'OVERLOADED':
                await self._stop(session.resume_id)
        finally:
            if session is not None and epoch is not None:
                try:
                    await self._detach(session, epoch, worker)
                except (ProtocolError, ConnectionError):
                    if session.epoch is None or session.epoch == epoch:
                        await self._stop(session.resume_id)
            await _close_socket(ws, transport, code=1000, reason=b'')
        return ws

    async def lifecycle(self, app):
        async def expire():
            while True:
                await asyncio.sleep(min(1, max(.05, self.sessions.session_ttl)))
                await self._expire()
        timer = asyncio.create_task(expire()) if self.sessions.session_ttl else None
        yield
        if timer is not None:
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
        self.owners.clear()

    def application(self):
        app = web.Application(client_max_size=self.codec.limits.max_wire_bytes,
                              middlewares=[self.check_host, self.proxy_scheme])
        app.cleanup_ctx.append(self.lifecycle)
        app.on_shutdown.append(self.shutdown)
        if self.urls.mount_path != '/':
            app.router.add_get(self.urls.mount_path.rstrip('/'), self.redirect)
        app.router.add_get(self.urls.mount_path, self.index)
        app.router.add_post(self.urls.route('pui/login'), self.login)
        app.router.add_post(self.urls.route('pui/logout'), self.logout)
        app.router.add_get(self.urls.route('assets') + '/{build}/{name}', self.asset)
        app.router.add_get(self.urls.route('pui/ws'), self.websocket)
        app.router.add_get(self.urls.route('pui/images') + '/{resource_id}', self.image)
        return app

    async def image(self, request):
        owner = self.owner(request)
        key = request.match_info['resource_id']
        record = next((w.images[key] for w in self.workers.values()
                       if w.owner == owner and w.stop_task is None and key in w.images), None)
        if owner is None or record is None:
            raise web.HTTPNotFound(headers={'Cache-Control': 'no-store'})
        try:
            path, stat, mime = await asyncio.to_thread(image_file, record['path'])
        except (OSError, ValueError):
            raise web.HTTPNotFound(headers={'Cache-Control': 'no-store'})
        if request.query.getall('mtime', []) != [str(stat.st_mtime_ns)]:
            raise web.HTTPConflict(text='Image changed; redraw to load its current URL', headers={'Cache-Control': 'no-store'})
        return web.FileResponse(path, headers={'Content-Type': mime,
            'Cache-Control': 'private, no-cache', 'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "sandbox; script-src 'none'"})


def serve(factory, *, bind='127.0.0.1:8000', base_url='/', mount_path=None, allow_hosts=None,
          trusted_proxies=None, session_ttl=900, max_sessions=64, auth=None, auth_prompt='', title=''):
    target = _bind_target(bind)
    gateway = Gateway(factory, base_url=base_url, mount_path=mount_path, allow_hosts=allow_hosts,
                      trusted_proxies=trusted_proxies, session_ttl=session_ttl, max_sessions=max_sessions,
                      auth=auth, auth_prompt=auth_prompt, title=title)
    public_url = gateway.urls.base_url
    if 'path' in target:
        print('PUI Web: %s (Unix socket %s)' % (public_url, target['path']), flush=True)
        with _unix_listener(target['path']) as listener:
            web.run_app(gateway.application(), sock=listener, shutdown_timeout=3)
        return
    if not urlsplit(public_url).scheme:
        host = target['host']
        public_url = 'http://%s:%s%s' % ('[' + host + ']' if ':' in host else host, target['port'], public_url)
    print('PUI Web: ' + public_url, flush=True)
    web.run_app(gateway.application(), **target, shutdown_timeout=3)
