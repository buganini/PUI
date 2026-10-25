"""Managed erebe/wstunnel reverse TCP tunnel."""
import asyncio
import logging
import os
import re
from urllib.parse import urlsplit, urlunsplit


LOG = logging.getLogger('PUI.web.tunnel')


def prepare(options):
    if (not isinstance(options, dict) or not {'url', 'token'} <= set(options)
            or set(options) - {'url', 'token', 'bind', 'wstunnel'}):
        raise ValueError('wstunnel must be a dict containing url and token, with optional bind and wstunnel')
    url, token = options['url'], options['token']
    if (not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9._~-]+', token)
            or token in ('.', '..')):
        raise ValueError('wstunnel token must be a non-empty URL-safe path segment (letters, digits, . _ ~ -)')
    try:
        parts = urlsplit(url) if isinstance(url, str) else None
        valid = (parts is not None and parts.scheme in ('ws', 'wss') and
                 parts.hostname and not parts.username and not parts.password and
                 re.fullmatch(r'(?:/[A-Za-z0-9._~-]+)*/?', parts.path) and
                 not any(segment in ('.', '..') for segment in parts.path.split('/')) and
                 not parts.fragment and not parts.query and
                 not any(c.isspace() or ord(c) < 32 for c in url))
        if parts is not None:
            parts.port
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('wstunnel must be a ws:// or wss:// server URL with an optional URL-safe path, without credentials, query or fragment')
    bind = options.get('bind', 'tcp://127.0.0.1:0')
    valid_bind = False
    if isinstance(bind, str) and not any(ord(c) < 32 for c in bind):
        if bind.startswith('unix://'):
            # Upstream splits the socket path at the first colon.
            path = bind[len('unix://'):]
            valid_bind = bool(path) and path != '/' and ':' not in path and not path.endswith('/')
        elif bind.startswith('tcp://'):
            try:
                address = urlsplit(bind)
                valid_bind = (bool(address.hostname) and address.port is not None
                              and not address.username and not address.password
                              and not address.path and not address.query and not address.fragment
                              and not any(c.isspace() for c in bind))
            except ValueError:
                pass
    if not valid_bind:
        raise ValueError('wstunnel bind must be tcp://host:port or unix://socket-path')
    executable = options.get('wstunnel', 'wstunnel')
    if not isinstance(executable, str) or not executable or '\0' in executable:
        raise ValueError('wstunnel executable must be a non-empty path or command name')
    prefix = '/'.join(part for part in (parts.path.strip('/'), token) if part)
    # wstunnel builds its request path from the prefix, ignoring the URL path.
    origin = urlunsplit((parts.scheme, parts.netloc, '', '', ''))
    return executable, origin, prefix, bind


def command(config, host, port):
    executable, url, _, bind = config
    host = '[' + host + ']' if ':' in host else host
    # Port zero is allocated on the relay. The actual port appears in its log;
    # wstunnel does not report a bind result back to this client. The relay can
    # also map the requested zero to a fixed port through its restriction file.
    return [executable, 'client', '--tls-verify-certificate',
            '-R', f'{bind}:{host}:{port}', url]


def environment(config=None):
    env = os.environ.copy()
    if config is not None:
        # Override only the child's environment; multiple PUI instances can use
        # different tokens and nginx routes without changing global state.
        env['WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX'] = config[2]
    # wstunnel's CLI parses this as a boolean, unlike the usual NO_COLOR=1.
    if 'NO_COLOR' in env:
        env['NO_COLOR'] = 'true' if env['NO_COLOR'] else 'false'
    return env


def lifecycle(config, host, port):
    async def context(app):
        process = await asyncio.create_subprocess_exec(
            *command(config, host, port), stdin=asyncio.subprocess.DEVNULL, env=environment(config))
        monitor = None
        try:
            async def watch():
                code = await process.wait()
                LOG.error('PUI reverse tunnel stopped (exit code %s); local Web server is still running', code)

            monitor = asyncio.create_task(watch())
            yield
        finally:
            if monitor is not None:
                monitor.cancel()
                await asyncio.gather(monitor, return_exceptions=True)
            if process.returncode is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(process.wait(), 3)
                except asyncio.TimeoutError:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    await process.wait()
    return context
