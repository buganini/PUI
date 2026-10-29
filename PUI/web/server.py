"""aiohttp gateway with cookie-owned, process-isolated session workers."""
import asyncio
from collections import OrderedDict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
import inspect
import json
import tempfile
import logging
import math
import time
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
import threading
from urllib.parse import unquote, urlsplit

from aiohttp import web, WSMsgType, WSCloseCode

from .close_codes import AppCloseCode
from ._server import run_app as _run_app
from .ipc import read_packet, queue_packet
from .messages import validate_client_body
from .protocol import Codec, ProtocolError, SUBPROTOCOL
from .sessions import SessionRegistry
from .urls import WebURLs
from .worker import run as run_worker, CAPABILITIES
from .images import image_file, unpack_registry
from .._browser.uploads import UploadStore, limits as normalize_upload_limits, remove

LIFECYCLE_LOG = logging.getLogger('PUI.web.lifecycle')

STATIC = Path(__file__).with_name('static')
COOKIE = 'pui_owner'
LOGIN_COOKIE = 'pui_login'
MAX_LOGIN_ACCOUNTS = 4096
LOGIN_FAILURE_TTL = 900
MAX_ANONYMOUS_OWNERS = 1024
WORKER_START_TIMEOUT = 30
IPC_TIMEOUT = 30
WEBSOCKET_SEND_TIMEOUT = 30


async def _close_socket(ws, transport, *, code=WSCloseCode.TRY_AGAIN_LATER, reason=b'Browser output queue did not drain'):
    try:
        await asyncio.wait_for(ws.close(code=code, message=reason), 1)
    except (ConnectionError, asyncio.TimeoutError):
        # A graceful transport.close() can itself wait for buffered output.
        # Abort the captured connection after its close deadline, not a newer
        # websocket that may have attached to this retained worker meanwhile.
        if transport is not None:
            transport.abort()


async def _reap_process(process, *, grace=.5, reason="Worker stopped"):
    if process.pid is not None:
        await asyncio.to_thread(process.join, grace)
        if process.is_alive():
            LIFECYCLE_LOG.warning("Worker terminating pid=%s reason=%s", process.pid, reason)
            process.terminate()
            await asyncio.to_thread(process.join, 1)
        if process.is_alive():
            LIFECYCLE_LOG.warning("Worker killing pid=%s reason=%s", process.pid, reason)
            process.kill()
            await asyncio.to_thread(process.join, 1)
        if process.is_alive():
            raise RuntimeError('Web worker could not be reaped')
    LIFECYCLE_LOG.info("Worker exited pid=%s exitcode=%s reason=%s",
                       process.pid, process.exitcode, reason)
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
def _unix_listener(path, socket_mode=None):
    # Bind explicitly: asyncio's path-based listener may unlink an existing
    # socket, including a live server. Keep this listener's ownership clear.
    path = os.fspath(path)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(path)
        created = os.lstat(path)
        try:
            if socket_mode is not None:
                os.chmod(path, socket_mode)
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
    uploads: object = None
    downloads: object = None
    drop_targets: dict = field(default_factory=dict)
    file_dialog: object = None
    file_batches: set = field(default_factory=set)
    upload_lock: object = field(default_factory=asyncio.Lock)
    application_task: object = None

    @property
    def pid(self):
        return self.process.pid if self.process is not None else os.getpid()


class Gateway:
    def __init__(self, factory, *, mount_path=None, allow_hosts=None, trusted_proxies=None,
                 session_ttl=900, max_sessions=64, auth=None, auth_prompt='', title='',
                 auth_idle_timeout=4200, auth_max_age=86400, landlock=None, codex=None, claude=None, upload_limits=None, webroot=None, passthru=False, permissive_takeover=False):
        if type(passthru) is not bool:
            raise ValueError('passthru must be a boolean')
        if passthru and any(value is not None for value in (landlock, codex, claude)):
            raise ValueError('passthru does not support landlock or AI worker restart')
        if type(permissive_takeover) is not bool:
            raise ValueError('permissive_takeover must be a boolean')
        if permissive_takeover and not passthru:
            raise ValueError('permissive_takeover requires passthru=True')
        self.permissive_takeover = permissive_takeover
        self.passthru = passthru
        from .._landlock import prepare
        self.landlock = prepare(landlock)
        if not (passthru and callable(factory)) and (not isinstance(factory, str) or ':' not in factory):
            raise ValueError('Application factory must be module:Class')
        self.upload_limits = normalize_upload_limits(upload_limits)
        self.upload_root = None
        self.download_root = None
        from .files import resolve_webroot
        self.webroot = resolve_webroot(webroot)
        self.file_start = self.webroot or str(Path.cwd().resolve())
        self.factory = factory
        if not isinstance(title, str):
            raise ValueError('title must be a string')
        self.title = title
        if auth is not None and not callable(auth):
            raise ValueError('auth must be a callable accepting username and password, or None')
        self.auth = auth
        for name, value in (('auth_idle_timeout', auth_idle_timeout), ('auth_max_age', auth_max_age)):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(name + ' must be a finite positive number of seconds')
        self.auth_idle_timeout, self.auth_max_age = auth_idle_timeout, auth_max_age
        self.login_attempts = {}
        self.login_sources = {}
        self.auth_tasks = set()
        if auth_prompt is not None and not isinstance(auth_prompt, str):
            raise ValueError('auth_prompt must be a string or None')
        self.auth_prompt = auth_prompt
        self.urls = WebURLs(mount_path=mount_path)
        self.allow_hosts = _allowed_hosts(allow_hosts)
        self.trusted_proxies = _trusted_proxies(trusted_proxies)
        self.sessions = SessionRegistry(session_ttl=0 if passthru else session_ttl,
                                        max_sessions=1 if passthru else max_sessions)
        self.codec = Codec()
        self.workers = {}
        self.reapers = set()
        self.closing = False
        self.secret = secrets.token_bytes(32)
        # Token -> server-side authentication and AI permissions. Anonymous owners without a reserved/live
        # worker form a bounded LRU; authenticated owners require logout.
        self.owners = OrderedDict()
        self.build = hashlib.sha256(b''.join((STATIC / name).read_bytes() for name in
            ('client.js', 'client.css', 'zstd.wasm'))).hexdigest()[:16]
        if passthru:
            self.context = None
        elif sys.platform == 'linux':
            # Keep application imports/threads outside the clean fork supervisor.
            multiprocessing.set_forkserver_preload([])
            self.context = multiprocessing.get_context('forkserver')
        else:
            # macOS must not fork a potentially threaded framework process;
            # Windows has no forkserver. Both use fresh Python interpreters.
            self.context = multiprocessing.get_context('spawn')
        self.lock = asyncio.Lock()
        from ..ai import enabled_providers
        from .ai import Conversations
        credentials = enabled_providers(codex, claude)
        self.ai = Conversations(self, credentials) if credentials else None

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

    def login_source(self, request):
        peer = request.transport.get_extra_info('peername') if request.transport else None
        sock = request.transport.get_extra_info('socket') if request.transport else None
        unix = sock is not None and getattr(sock, 'family', None) == getattr(socket, 'AF_UNIX', None)
        try:
            address = ip_address(peer[0]) if isinstance(peer, tuple) and peer else None
        except ValueError:
            address = None
        def trusted(address):
            return any(address in network for network in self.trusted_proxies if network != 'unix')
        source = str(address) if address is not None else ('unix' if unix else 'unknown')
        if (unix and 'unix' in self.trusted_proxies) or (address is not None and trusted(address)):
            values = request.headers.getall('X-Forwarded-For', [])
            if values:
                try:
                    chain = [ip_address(value.strip()) for value in ','.join(values).split(',')]
                except ValueError:
                    return source  # Malformed forwarding never creates arbitrary rate-limit keys.
                for candidate in reversed(chain):
                    source = str(candidate)
                    if not trusted(candidate):
                        break
        return source

    def admit_login_source(self, request):
        now = time.monotonic()
        for key, attempts in list(self.login_sources.items()):
            while attempts and attempts[0] <= now - 60:
                attempts.popleft()
            if not attempts:
                del self.login_sources[key]
        key = self.login_source(request)
        attempts = self.login_sources.get(key)
        if attempts is None:
            if len(self.login_sources) >= 4096:
                return 60
            attempts = self.login_sources[key] = deque()
        if len(attempts) >= 10:
            return max(1, math.ceil(attempts[0] + 60 - now))
        attempts.append(now)
        return 0

    def _sign(self, token, purpose=COOKIE):
        return hmac.new(self.secret, (purpose + ':' + token).encode('ascii'), hashlib.sha256).hexdigest()

    def _cookie_token(self, request, name):
        # Browsers can send the same name from multiple cookie paths. aiohttp's
        # mapping keeps only the last value, so an old / cookie can hide the
        # current /pui/ login. Inspect all values, accepting only our signed format.
        tokens = set()
        for header in request.headers.getall('Cookie', []):
            for pair in header.split(';'):
                key, separator, value = pair.strip().partition('=')
                if key != name or not separator:
                    continue
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                match = re.fullmatch(r'([A-Za-z0-9_-]{43})\.([0-9a-f]{64})', value)
                if match is not None:
                    token, signature = match.groups()
                    if hmac.compare_digest(self._sign(token, name), signature):
                        tokens.add(token)
        # Never choose an identity by header order when two valid tokens disagree.
        return next(iter(tokens)) if len(tokens) == 1 else None

    def owner(self, request):
        token = self._cookie_token(request, COOKIE)
        if not self.owner_valid(token):
            return None
        self.owners.move_to_end(token)
        return token

    def owner_valid(self, token):
        entry = self.owners.get(token)
        if entry is None:
            return False
        if self.auth is None:
            return True
        now = time.monotonic()
        return (entry['auth'] and not entry['expired'] and
                now - entry['created'] < self.auth_max_age and
                now - entry['active'] < self.auth_idle_timeout)

    def touch_owner(self, token):
        if self.owner_valid(token):
            self.owners[token]['active'] = time.monotonic()

    def _new_owner(self, *, authenticated=False, ai=False, username=None):
        token = secrets.token_urlsafe(32)
        self.owners[token] = {'auth': authenticated, 'ai': authenticated and ai,
                              'username': username, 'created': time.monotonic(),
                              'active': time.monotonic(), 'expired': False,
                              'resume_marker': self._sign(token, 'resume-owner')}
        self._prune_owners()
        return token

    def ai_allowed(self, owner):
        permissions = self.owners.get(owner)
        return self.owner_valid(owner) and (self.auth is None or
            (permissions['auth'] and permissions['ai']))

    def _prune_owners(self):
        if len(self.owners) <= MAX_ANONYMOUS_OWNERS:
            return
        # Reservations protect admission while _spawn() awaits IPC setup.
        # Workers also protect owners during asynchronous process teardown.
        protected = self.sessions.owners() | {worker.owner for worker in self.workers.values()}
        if self.ai is not None:
            protected |= {entry['owner'] for entry in self.ai.entries.values()}
        idle = [token for token, permissions in self.owners.items()
                if not permissions['auth'] and token not in protected]
        for token in idle[:-MAX_ANONYMOUS_OWNERS]:
            del self.owners[token]

    def _set_cookie(self, response, request, name, token):
        response.set_cookie(name, token + '.' + self._sign(token, name), httponly=True,
            secure=request.secure,
            samesite='Lax', path=self.urls.mount_path)

    def _origin(self, request):
        return request.scheme + '://' + request.host

    def login_page(self, request, *, error='', status=200):
        # Failed login renders at pui/login rather than the entry directory.
        entry = '../' if request.path == unquote(self.urls.route('pui/login')) else './'
        token = self._cookie_token(request, LOGIN_COOKIE) or secrets.token_urlsafe(32)
        title = escape(self.title or 'PUI')
        prompt = '<p class="pui-auth-prompt">%s</p>' % escape(self.auth_prompt) if self.auth_prompt else ''
        html = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Sign in · %s</title>
<link rel="icon" href="data:,"><link rel="stylesheet" href="%s"></head><body>
<main class="pui-login"><h1>%s</h1>%s
<form method="post" action="%s" onsubmit="this.action = this.action.split('#')[0] + location.hash">
<input type="hidden" name="csrf" value="%s">
<label>Username<input name="username" autocomplete="username" required autofocus></label>
<label>Password<input type="password" name="password" autocomplete="current-password" required></label>
<p role="alert">%s</p><button type="submit" class="pui-Button">Sign in</button>
</form></main></body></html>''' % (
            title,
            escape(entry + self.urls.asset(self.build, 'client.css'), quote=True),
            title, prompt,
            escape(entry + self.urls.public('pui/login'), quote=True), token, escape(error))
        response = web.Response(text=html, content_type='text/html', status=status,
                                headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'same-origin',
                                         'Content-Security-Policy': "frame-ancestors 'none'",
                                         'X-Frame-Options': 'DENY'})
        self._set_cookie(response, request, LOGIN_COOKIE, token)
        return response

    async def login(self, request):
        if self.auth is None:
            raise web.HTTPNotFound()
        if request.headers.getall('Origin', []) not in ([], [self._origin(request)]):
            raise web.HTTPForbidden(text='Invalid login origin')
        if self.owner(request) is not None:
            raise web.HTTPSeeOther('../')
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
        # Key by exact account text: auth callbacks define their own normalization.
        username = fields['username']
        now = time.monotonic()
        for key, entry in list(self.login_attempts.items()):
            if not entry['busy'] and now - entry['updated'] >= LOGIN_FAILURE_TTL:
                del self.login_attempts[key]
        entry = self.login_attempts.get(username)
        if entry is not None and (entry['busy'] or entry['until'] > now):
            seconds = max(1, math.ceil(entry['until'] - now))
            response = self.login_page(request, error=f'Please wait {seconds} seconds before trying again.', status=429)
            response.headers['Retry-After'] = str(seconds)
            return response
        retry = self.admit_login_source(request)
        if retry:
            response = self.login_page(request, error=f'Too many sign-in attempts. Try again in {retry} seconds.', status=429)
            response.headers['Retry-After'] = str(retry)
            return response
        if entry is None:
            if len(self.login_attempts) >= MAX_LOGIN_ACCOUNTS:
                response = self.login_page(request, error='Sign-in is temporarily unavailable.', status=503)
                response.headers['Retry-After'] = '30'
                return response
            entry = dict(failures=0, until=0, updated=now, busy=False)
            self.login_attempts[username] = entry
        entry['busy'] = True

        async def authenticate():
            try:
                accepted = await asyncio.to_thread(self.auth, username, fields['password'])
                if inspect.isawaitable(accepted):
                    accepted = await accepted
                if (not isinstance(accepted, dict) or
                        any(type(accepted.get(key, False)) is not bool for key in ('auth', 'ai'))):
                    accepted = {'auth': False, 'ai': False}
                else:
                    accepted = {key: accepted.get(key, False) for key in ('auth', 'ai')}
                if accepted['auth']:
                    self.login_attempts.pop(username, None)
                else:
                    entry['failures'] = min(entry['failures'] + 1, 6)
                    entry['until'] = time.monotonic() + min(2 ** (entry['failures'] - 1), 30)
                return accepted
            finally:
                entry['busy'] = False
                entry['updated'] = time.monotonic()

        # A disconnected client must not unlock an auth callback still running in a thread.
        task = asyncio.create_task(authenticate())
        self.auth_tasks.add(task)
        def finished(task):
            self.auth_tasks.discard(task)
            if not task.cancelled():
                task.exception()  # Retrieve failures even if the HTTP caller disconnected.
        task.add_done_callback(finished)
        try:
            accepted = await asyncio.shield(task)
        except Exception as error:
            # Callback exceptions may contain credentials: do not log their text.
            logging.getLogger(__name__).warning('Web authentication callback failed (%s)', type(error).__name__)
            return self.login_page(request, error='Sign-in is temporarily unavailable.', status=503)
        if not accepted['auth']:
            seconds = min(2 ** (entry['failures'] - 1), 30)
            response = self.login_page(request, error=f'Invalid username or password. Please wait {seconds} seconds before trying again.')
            response.headers['Retry-After'] = str(seconds)
            return response
        response = web.HTTPSeeOther('../', headers={'Cache-Control': 'no-store'})
        old_owner = self._cookie_token(request, COOKIE)
        old = self.owners.get(old_owner)
        new_owner = self._new_owner(authenticated=True, ai=accepted['ai'], username=username)
        if old is not None and old['username'] == username and not self.owner_valid(old_owner):
            # Detach first so a new connection can resume immediately after login.
            await self._expire_owner(old_owner)
            async with self.lock:
                self.owners[new_owner]['resume_marker'] = old['resume_marker']
                for session in self.sessions._sessions.values():
                    if session.owner == old_owner:
                        session.owner = new_owner
                for worker in self.workers.values():
                    if worker.owner == old_owner:
                        worker.owner = new_owner
                self.owners.pop(old_owner, None)
        self._set_cookie(response, request, COOKIE, new_owner)
        response.del_cookie(LOGIN_COOKIE, path=self.urls.mount_path)
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
                self.owners.pop(owner, None)
                owned = [key for key, worker in self.workers.items() if worker.owner == owner]
                for key in owned:
                    self.sessions.remove(key)
            await asyncio.gather(*(self._stop(key, code=AppCloseCode.LOGGED_OUT, reason=b'Logged out') for key in owned))
            if self.ai is not None:
                await self.ai.drop_owner(owner)
        response = web.HTTPSeeOther('../', headers={'Cache-Control': 'no-store'})
        for name in (COOKIE, LOGIN_COOKIE):
            response.del_cookie(name, path=self.urls.mount_path)
        raise response

    async def renew(self, request):
        if request.headers.getall('Origin', []) not in ([], [self._origin(request)]):
            raise web.HTTPForbidden(text='Invalid renew origin')
        owner = self.owner(request)
        if owner is None:
            raise web.HTTPForbidden(text='Invalid browser owner')
        if request.content_type != 'application/x-www-form-urlencoded':
            raise web.HTTPUnsupportedMediaType()
        try:
            fields = await request.clone(client_max_size=1024).post()
        except (UnicodeError, LookupError, ValueError):
            raise web.HTTPBadRequest(text='Invalid renew form') from None
        if set(fields) != {'csrf', 'resume_id'} or any(len(fields.getall(k)) != 1 for k in fields):
            raise web.HTTPBadRequest(text='Invalid renew form')
        token = fields['csrf']
        if not token.isascii() or not hmac.compare_digest(token, self._sign(owner, 'renew')):
            raise web.HTTPForbidden(text='Invalid renew form token')
        async with self.lock:
            if not self.owner_valid(owner):
                raise web.HTTPForbidden(text='Invalid browser owner')
            worker = self.workers.get(fields['resume_id'])
            if worker is not None and worker.owner != owner:
                raise web.HTTPForbidden(text='Session belongs to another browser')
            try:
                self.sessions.remove(fields['resume_id'], owner=owner)
            except ProtocolError:
                raise web.HTTPForbidden(text='Session belongs to another browser') from None
        if worker is not None:
            await self._stop(fields['resume_id'], code=AppCloseCode.SESSION_RENEWED, reason=b'Session renewed')
        # Keep the owner cookie and its login; the redirected page starts a fresh worker.
        raise web.HTTPSeeOther('../', headers={'Cache-Control': 'no-store'})

    async def index(self, request):
        if self.auth is not None and self.owner(request) is None:
            return self.login_page(request)
        owner = self.owner(request) or self._new_owner()
        session_actions = '' if self.passthru else (
            ' data-logout="%s" data-logout-token="%s" data-renew="%s" data-renew-token="%s"' % (
                escape(self.urls.public('pui/logout'), quote=True), self._sign(owner, 'logout'),
                escape(self.urls.public('pui/renew'), quote=True), self._sign(owner, 'renew')))
        html = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="%s"></head><body>
<p id="pui-status" role="status">Connecting…</p>
<main id="pui-root" data-ws="%s" data-build="%s" data-entry="%s" data-passthru="%s"%s data-resume-owner="%s" data-auth-required="%s" data-ai="%s" data-upload="%s" data-upload-token="%s" data-downloads="%s"></main>
<script type="module" src="%s"></script></body></html>''' % (
            escape(self.title or 'PUI'),
            escape(self.urls.asset(self.build, 'client.css'), quote=True),
            escape(self.urls.websocket(), quote=True), self.build,
            './', 'true' if self.passthru else 'false',
            session_actions, self.owners[owner]['resume_marker'],
            'true' if self.auth is not None else 'false',
            escape(self.urls.public('pui/ai') if self.ai and self.ai_allowed(owner) else '', quote=True),
            escape(self.urls.public('pui/upload'), quote=True), self._sign(owner, 'upload'),
            escape(self.urls.public('pui/downloads'), quote=True),
            escape(self.urls.asset(self.build, 'client.js'), quote=True))
        response = web.Response(text=html, content_type='text/html', headers={
            'Cache-Control': 'no-store', 'Content-Security-Policy': "frame-ancestors 'none'",
            'X-Frame-Options': 'DENY'})
        self._set_cookie(response, request, COOKIE, owner)
        return response

    async def redirect(self, request):
        raise web.HTTPPermanentRedirect(self.urls.mount_path.rstrip('/').rsplit('/', 1)[-1] + '/')

    async def asset(self, request):
        name = request.match_info['name']
        if request.match_info['build'] != self.build or name not in (
                'client.js', 'client.css', 'zstd.wasm', 'THIRD_PARTY_LICENSES.txt'):
            raise web.HTTPNotFound()
        response = web.FileResponse(STATIC / name, headers={'Cache-Control': 'public, max-age=31536000, immutable'})
        if name.endswith('.wasm'):
            response.content_type = 'application/wasm'
        return response

    def _downloads(self, session):
        from .files import DownloadStore
        if self.download_root is None:
            self.download_root = tempfile.TemporaryDirectory(prefix='pui-download-')
        return DownloadStore(Path(self.download_root.name) / session.resume_id)

    async def _spawn(self, session):
        if self.passthru:
            from .passthru import spawn
            return await spawn(self, session)
        if self.upload_root is None:
            self.upload_root = tempfile.TemporaryDirectory(prefix='pui-upload-')
        uploads = UploadStore(Path(self.upload_root.name) / session.resume_id, self.upload_limits)
        uploads.root.mkdir(mode=0o700)
        downloads = self._downloads(session)
        parent, child = socket.socketpair()
        process = self.context.Process(target=run_worker,
                                       args=(child, self.factory, self.build, self.urls.public('pui/images'), self.title, self.landlock, str(uploads.root), self.upload_limits, str(downloads.root), self.webroot, self.file_start),
                                       name='pui-web-worker')
        try:
            process.start()
            LIFECYCLE_LOG.info("Worker started pid=%s", process.pid)
            child.close()
            parent.setblocking(False)
            reader, writer = await asyncio.open_connection(sock=parent)
        except BaseException as error:
            LIFECYCLE_LOG.warning("Worker startup failed pid=%s error=%s",
                                  process.pid, type(error).__name__)
            uploads.close()
            downloads.close()
            parent.close()
            child.close()
            self.sessions.remove(session.resume_id)
            self._prune_owners()
            # Cancellation cannot leave a started child outside the registry.
            reaper = asyncio.create_task(_reap_process(process, grace=0, reason="Startup failed"))
            self.reapers.add(reaper)
            reaper.add_done_callback(self.reapers.discard)
            await asyncio.shield(reaper)
            raise
        worker = Worker(process, writer, owner=session.owner, uploads=uploads, downloads=downloads)
        self.workers[session.resume_id] = worker
        worker.task = asyncio.create_task(self._relay(session, worker, reader))
        return worker

    def _clear_file_dialog(self, worker):
        worker.file_dialog = None
        for key in worker.file_batches:
            folder = worker.uploads.directory(key)
            if key in worker.uploads.active or (folder / 'manifest.json').exists():
                worker.uploads.discard(key)
        worker.file_batches.clear()

    async def _relay(self, session, worker, reader):
        stop_reason = b"Worker relay cancelled"
        try:
            loop = asyncio.get_running_loop()
            startup_deadline = loop.time() + WORKER_START_TIMEOUT
            while True:
                if startup_deadline is None:
                    packet = await read_packet(reader)
                else:
                    packet = await asyncio.wait_for(read_packet(reader), max(0, startup_deadline - loop.time()))
                if packet == b'S\0':
                    LIFECYCLE_LOG.info("Worker ready pid=%s", worker.pid)
                    startup_deadline = None
                    continue
                if packet.startswith(b'U\0'):
                    if session.epoch is not None and packet[2:].decode('ascii') == session.epoch:
                        self.touch_owner(worker.owner)
                    continue
                if packet.startswith(b'F\0'):
                    self._clear_file_dialog(worker)
                    record = json.loads(packet[2:])
                    if record is not None and record['epoch'] == session.epoch:
                        worker.file_dialog = record
                    continue
                if packet.startswith(b'T\0'):
                    worker.drop_targets = json.loads(packet[2:])
                    continue
                if packet.startswith(b'I\0'):
                    worker.images = unpack_registry(packet[2:])
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
        except (asyncio.IncompleteReadError, ConnectionError, ValueError, asyncio.TimeoutError) as error:
            stop_reason = (b"Worker startup timeout" if isinstance(error, asyncio.TimeoutError)
                           else b"Worker IPC closed" if isinstance(error, asyncio.IncompleteReadError)
                           else b"Worker IPC error")
            LIFECYCLE_LOG.warning("Worker relay ended pid=%s reason=%s error=%s",
                                  worker.pid, stop_reason.decode(), type(error).__name__)
        finally:
            await self._stop(session.resume_id, cancel_relay=False, reason=stop_reason)

    async def _stop(self, resume_id, *, cancel_relay=True, code=WSCloseCode.INTERNAL_ERROR, reason=b'Worker stopped'):
        worker = self.workers.get(resume_id)
        if worker is None:
            return
        if worker.stop_task is None:
            LIFECYCLE_LOG.info("Worker stopping pid=%s reason=%s",
                               worker.pid, reason.decode("utf-8", errors="replace"))
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
        if worker.application_task is not None:
            worker.application_task.cancel()
            await asyncio.gather(worker.application_task, return_exceptions=True)
        else:
            await _reap_process(worker.process, reason=reason.decode("utf-8", errors="replace"))
        if worker.uploads is not None:
            worker.uploads.close()
        if worker.downloads is not None:
            worker.downloads.close()
        if worker.websocket is not None:
            await _close_socket(worker.websocket, worker.transport, code=code, reason=reason)
        self.workers.pop(resume_id, None)
        self._prune_owners()

    async def _expire_owner(self, owner):
        entry = self.owners.get(owner)
        if entry is None:
            return
        entry['expired'] = True
        for key, worker in list(self.workers.items()):
            if worker.owner != owner:
                continue
            session = self.sessions._sessions.get(key)
            ws, transport = worker.websocket, worker.transport
            if session is not None and session.epoch is not None:
                await self._detach(session, session.epoch, worker)
            if ws is not None:
                await _close_socket(ws, transport, code=AppCloseCode.AUTH_EXPIRED, reason=b'Authentication expired')
        if self.ai is not None:
            await self.ai.drop_owner(owner)

    async def _expire(self):
        for owner, entry in list(self.owners.items()):
            if entry['auth'] and not entry['expired'] and not self.owner_valid(owner):
                await self._expire_owner(owner)
        # Keep slow process cleanup outside the admission/attachment lock.
        async with self.lock:
            expired = self.sessions.expire()
        await asyncio.gather(*(self._stop(session.resume_id, reason=b"Session TTL expired") for session in expired))

    async def _drain(self, worker):
        try:
            await asyncio.wait_for(worker.writer.drain(), IPC_TIMEOUT)
        except asyncio.TimeoutError as error:
            raise ProtocolError('OVERLOADED', 'Worker input queue did not drain') from error

    async def _detach(self, session, epoch, worker):
        queued = False
        async with self.lock:
            if self.sessions.detach(session.resume_id, epoch):
                LIFECYCLE_LOG.info("Worker detached pid=%s session_ttl=%s",
                                   worker.pid, self.sessions.session_ttl)
                self._clear_file_dialog(worker)
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
        superseded = (None, None)
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
                if not self.owner_valid(owner):
                    raise ProtocolError('UNAUTHORIZED', 'Logged out')
                entry = self.owners[owner]
                principal = ('user', entry['username']) if self.auth is not None else ('owner', owner)
                # The browser's resume ID is a hint, never authority to another user's worker.
                # Only the server's explicit passthru policy permits cross-identity attachment.
                requested = self.sessions._sessions.get(body['resume_id'])
                if requested is not None and requested.principal != principal and not self.permissive_takeover:
                    raise ProtocolError('BAD_SESSION', 'Session belongs to another user')
                session = next((item for item in self.sessions._sessions.values()
                                if item.principal == principal or self.permissive_takeover), None)
                resumed = session is not None
                if session is None:
                    if len(self.workers) >= self.sessions.max_sessions:
                        raise ProtocolError('OVERLOADED', 'Session capacity reached')
                    session = self.sessions.create(owner)
                    session.principal = principal
                    worker = await self._spawn(session)
                else:
                    worker = self.workers[session.resume_id]
                    superseded = (worker.websocket, worker.transport)
                    if session.epoch is not None:
                        self.sessions.detach(session.resume_id, session.epoch)
                        queue_packet(worker.writer, b'D')
                    self._clear_file_dialog(worker)
                    session.principal = principal
                    session.owner = worker.owner = owner
                    session = self.sessions.resume(owner, session.resume_id)
                LIFECYCLE_LOG.info("Worker %s pid=%s",
                                   "taken over" if superseded[0] is not None else "resumed" if resumed else "attached",
                                   worker.pid)
                epoch = session.epoch
                worker.websocket = ws
                worker.transport = transport
                control = {'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                    'body': {'epoch': epoch, 'hello': body, 'resume_id': session.resume_id,
                             'resumed': resumed, 'session_ttl': self.sessions.session_ttl}}
                queue_packet(worker.writer, b'A' + self.codec.encode(control))
            if superseded[0] is not None:
                await _close_socket(*superseded, code=AppCloseCode.SESSION_TAKEN_OVER, reason=b'Session taken over')
            await self._drain(worker)
            async for message in ws:
                if session.epoch != epoch or worker.websocket is not ws:
                    break
                if not self.owner_valid(owner):
                    raise ProtocolError('UNAUTHORIZED', 'Logged out')
                if message.type == WSMsgType.BINARY:
                    queue_packet(worker.writer, b'M' + message.data)
                    await self._drain(worker)
                elif message.type == WSMsgType.TEXT:
                    raise ProtocolError('BAD_FRAME', 'Only binary messages are accepted')
                elif message.type == WSMsgType.ERROR:
                    break
        except (ProtocolError, asyncio.TimeoutError, ConnectionError) as error:
            if isinstance(error, ProtocolError) and error.code == 'UNAUTHORIZED':
                code = AppCloseCode.AUTH_EXPIRED if owner in self.owners else AppCloseCode.LOGGED_OUT
            else:
                code = WSCloseCode.POLICY_VIOLATION
            await _close_socket(ws, transport, code=code, reason=str(error).encode('utf-8')[:120])
            if worker is not None and session.epoch == epoch and isinstance(error, ProtocolError) and error.code == 'OVERLOADED':
                await self._stop(session.resume_id, reason=b"Worker input overloaded")
        finally:
            if session is not None and epoch is not None:
                try:
                    await self._detach(session, epoch, worker)
                except (ProtocolError, ConnectionError):
                    if session.epoch is None or session.epoch == epoch:
                        await self._stop(session.resume_id, reason=b"Worker detach failed")
            await _close_socket(ws, transport, code=WSCloseCode.OK, reason=b'')
        return ws

    async def lifecycle(self, app):
        async def expire():
            while True:
                await asyncio.sleep(min(1, max(.05, self.sessions.session_ttl or 1)))
                await self._expire()
        timer = asyncio.create_task(expire()) if self.sessions.session_ttl or self.auth is not None else None
        yield
        if timer is not None:
            timer.cancel()
            await asyncio.gather(timer, return_exceptions=True)
        await self.shutdown(app)
        await asyncio.gather(*list(self.reapers))

    async def shutdown(self, app):
        self.closing = True
        if self.ai is not None:
            await self.ai.close()
        workers = list(self.workers.values())
        await asyncio.gather(*(self._stop(key, code=WSCloseCode.GOING_AWAY, reason=b'Server shutdown')
                              for key in list(self.workers)))
        await asyncio.gather(*(worker.task for worker in workers if worker.task is not None),
                             return_exceptions=True)
        self.owners.clear()
        if self.upload_root is not None:
            self.upload_root.cleanup()
        if self.download_root is not None:
            self.download_root.cleanup()

    def application(self):
        app = web.Application(client_max_size=self.codec.limits.max_wire_bytes,
                              middlewares=[self.check_host, self.proxy_scheme])
        if self.passthru:
            from .passthru import lifecycle
            app.cleanup_ctx.append(lifecycle)
        app.cleanup_ctx.append(self.lifecycle)
        app.on_shutdown.append(self.shutdown)
        if self.urls.mount_path != '/':
            app.router.add_get(self.urls.mount_path.rstrip('/'), self.redirect)
        app.router.add_get(self.urls.mount_path, self.index)
        app.router.add_post(self.urls.route('pui/login'), self.login)
        if not self.passthru:
            app.router.add_post(self.urls.route('pui/logout'), self.logout)
            app.router.add_post(self.urls.route('pui/renew'), self.renew)
        app.router.add_post(self.urls.route('pui/upload'), self.upload)
        app.router.add_get(self.urls.route('pui/downloads'), self.download_list)
        app.router.add_post(self.urls.route('pui/downloads'), self.download_list)
        app.router.add_get(self.urls.route('pui/downloads') + '/{download_id}', self.download)
        app.router.add_get(self.urls.route('assets') + '/{build}/{name}', self.asset)
        app.router.add_get(self.urls.route('pui/ws'), self.websocket)
        if self.ai is not None:
            app.router.add_get(self.urls.route('pui/ai'), self.ai.websocket)
        app.router.add_get(self.urls.route('pui/images') + '/{resource_id}', self.image)
        return app

    async def download_list(self, request):
        owner = self.owner(request)
        worker = self.workers.get(request.headers.get('X-PUI-Session', ''))
        if owner is None or worker is None or worker.owner != owner or worker.stop_task is not None:
            raise web.HTTPForbidden(text='Download session is not available')
        if request.method == 'POST':
            try:
                keys = await request.json()
            except (ValueError, UnicodeError):
                raise web.HTTPBadRequest(text='Invalid download list') from None
            if (not isinstance(keys, list) or len(keys) > 4096 or
                    any(not isinstance(key, str) or not re.fullmatch('[0-9a-f]{32}', key) for key in keys)):
                raise web.HTTPBadRequest(text='Invalid download IDs')
            entries = await asyncio.to_thread(worker.downloads.entries, keys, True)
        else:
            # Discovery reads metadata only. Size polling is explicitly scoped to
            # the IDs the browser still displays; dismissed files are not opened.
            entries = await asyncio.to_thread(worker.downloads.entries, None, False)
        return web.json_response(entries, headers={'Cache-Control': 'no-store'})

    async def download(self, request):
        owner = self.owner(request)
        if owner is None:
            raise web.HTTPForbidden(text='Download session is not available')
        key = request.match_info['download_id']
        opened = None
        for worker in list(self.workers.values()):
            if worker.owner != owner or worker.stop_task is not None or worker.downloads is None:
                continue
            try:
                opened = await asyncio.to_thread(worker.downloads.open, key)
                break
            except (OSError, ValueError, KeyError, TypeError):
                continue
        if opened is None:
            raise web.HTTPNotFound(text='Download is not available')
        record, stream, size = opened
        from urllib.parse import quote
        # Deliver the size observed at open, even if the writer appends more data.
        # SaveFile has no completion signal; a link is not a claim of completion.
        response = web.StreamResponse(headers={
            'Content-Type': 'application/octet-stream', 'Content-Length': str(size),
            'Content-Disposition': "attachment; filename*=UTF-8''" + quote(record['name'], safe=''),
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
        try:
            await response.prepare(request)
            remaining = size
            while remaining and request.method != 'HEAD':
                chunk = await asyncio.to_thread(stream.read, min(65536, remaining))
                if not chunk:
                    # The application truncated/deleted data while downloading.
                    response.force_close()
                    break
                remaining -= len(chunk)
                await response.write(chunk)
            await response.write_eof()
        finally:
            stream.close()
        return response

    async def upload(self, request):
        owner = self.owner(request)
        token = request.headers.get('X-PUI-Upload', '')
        if (owner is None or request.headers.get('Origin') != self._origin(request) or
                not token.isascii() or not hmac.compare_digest(token, self._sign(owner, 'upload'))):
            raise web.HTTPForbidden(text='Invalid upload owner or token')
        key = request.headers.get('X-PUI-Session', '')
        epoch = request.headers.get('X-PUI-Epoch', '')
        node = request.headers.get('X-PUI-Node', '')
        target_token = request.headers.get('X-PUI-Target', '')
        selection = request.headers.get('X-PUI-Dialog', '')
        worker = self.workers.get(key)
        def target():
            session = self.sessions._sessions.get(key)
            record = (worker.file_dialog if selection else worker.drop_targets.get(node)) if worker else None
            if (worker is None or worker.owner != owner or owner not in self.owners or
                    worker.stop_task is not None or worker.websocket is None or
                    session is None or session.epoch != epoch or record is None or
                    record['token'] != (selection or target_token) or
                    (selection and record.get('epoch') != epoch)):
                raise web.HTTPConflict(text='Drop target or session is no longer available')
            return record
        record = target()
        if request.content_type != 'multipart/form-data':
            raise web.HTTPUnsupportedMediaType()
        # One receiving batch per session: file writes and quota checks are serial.
        if worker.upload_lock.locked():
            raise web.HTTPConflict(text='Another upload is in progress')
        async with worker.upload_lock:
            batch = worker.uploads.begin()
            if selection:
                worker.file_batches.add(batch)
            complete = False
            try:
                async def receive():
                    reader = await request.multipart()
                    while True:
                        part = await reader.next()
                        if part is None:
                            break
                        target()
                        if part.name != 'files' or part.filename is None:
                            raise ValueError('Expected file parts')
                        if selection:
                            fid = worker.uploads.add_selection(batch, part.filename, record['mode'], record['patterns'], selection)
                        else:
                            fid = worker.uploads.add(batch, part.filename, record['extensions'])
                        while True:
                            data = await part.read_chunk(64 * 1024)
                            if not data:
                                break
                            target()
                            worker.uploads.write(batch, fid, data)
                await asyncio.wait_for(receive(), 120)
                target()
                worker.uploads.finish(batch)
                complete = True
                return web.json_response({'upload_id': batch}, headers={'Cache-Control': 'no-store'})
            except (ValueError, KeyError) as error:
                raise web.HTTPBadRequest(text=str(error)) from None
            except OSError:
                raise web.HTTPBadRequest(text='Unable to store uploaded files') from None
            except asyncio.TimeoutError:
                raise web.HTTPRequestTimeout(text='Upload timed out') from None
            finally:
                if not complete:
                    worker.uploads.discard(batch)

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


def serve(factory, *, bind='127.0.0.1:8000', mount_path=None, allow_hosts=None,
          trusted_proxies=None, session_ttl=900, max_sessions=64, auth=None, auth_prompt='', title='',
          auth_idle_timeout=4200, auth_max_age=86400,
          socket_mode=None, landlock=None, codex=None, claude=None, upload_limits=None, passthru=False, permissive_takeover=False, wstunnel=None, webroot=None, _server=None):
    if socket_mode is not None and (type(socket_mode) is not int or not 0 <= socket_mode <= 0o7777):
        raise ValueError('socket_mode must be None or an integer between 0 and 0o7777')
    if not LIFECYCLE_LOG.hasHandlers():
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
        LIFECYCLE_LOG.addHandler(handler)
        if LIFECYCLE_LOG.level == logging.NOTSET:
            LIFECYCLE_LOG.setLevel(logging.INFO)
    target = _bind_target(bind)
    if wstunnel is not None and 'path' in target:
        raise ValueError('wstunnel requires a TCP bind, not a Unix socket')
    gateway = Gateway(factory, mount_path=mount_path, allow_hosts=allow_hosts,
                      trusted_proxies=trusted_proxies, session_ttl=session_ttl, max_sessions=max_sessions,
                      auth=auth, auth_prompt=auth_prompt, title=title, auth_idle_timeout=auth_idle_timeout, auth_max_age=auth_max_age, landlock=landlock, codex=codex, claude=claude, upload_limits=upload_limits, webroot=webroot, passthru=passthru, permissive_takeover=permissive_takeover)
    run_options = {'shutdown_timeout': 3, 'server': _server, 'mount_path': gateway.urls.mount_path}
    if threading.current_thread() is not threading.main_thread():
        run_options['handle_signals'] = False
    if wstunnel is not None:
        from .tunnel import lifecycle
        # Bind once and pass the same socket to aiohttp, including with port 0.
        # A wildcard listener is reached through the matching loopback address.
        family, _, _, _, address = socket.getaddrinfo(
            target['host'], target['port'], type=socket.SOCK_STREAM)[0]
        with socket.create_server(address[:2], family=family) as listener:
            host, port = listener.getsockname()[:2]
            tunnel_host = {'0.0.0.0': '127.0.0.1', '::': '::1'}.get(host, host)
            app = gateway.application()
            app.cleanup_ctx.append(lifecycle(wstunnel, tunnel_host, port))
            _run_app(app, sock=listener, **run_options)
        return
    if 'path' in target:
        with _unix_listener(target['path'], socket_mode=socket_mode) as listener:
            _run_app(gateway.application(), sock=listener, **run_options)
        return
    _run_app(gateway.application(), **target, **run_options)
